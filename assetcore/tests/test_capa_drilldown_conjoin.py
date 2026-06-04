# Copyright (c) 2026, AssetCore Team
"""IMM-00 list_capas drill-down filter composition — conjoin (AND) SoT (BR-00-16).

Bug #4 USER Vòng 12: "chọn status=Quá hạn mà vẫn 117".
ROOT CAUSE: `api/imm00.py::list_capas` build filter DẠNG DICT rồi
`filters.update(_open_capa_filter()|_overdue_capa_filter())` → key 'status' trùng →
CLOBBER (explicit status=Overdue bị ghi đè bởi {status NOT IN [Closed]} → full open-set).
Frappe dict-filter KHÔNG giữ 2 điều kiện/CÙNG field.

FIX: chuyển sang list-of-conditions `[[doctype,field,op,val], ...]` cho phép NHIỀU
điều kiện trên CÙNG field 'status' cùng tồn tại = AND thật. count + get_list dùng
CÙNG conditions (parity total==len). SoT membership KHÔNG đổi (round 10/11 no-regression).

Acceptance (BR-00-16):
  - not_closed=1 & status=Overdue → CHỈ tập (NOT IN [Closed]) AND (== 'Overdue') = Overdue.
  - not_closed=1 & status=Closed  → ∅ (AND của 'Closed' và NOT IN [Closed]).
  - overdue=1   & status=Open     → ∅ (Open không thuộc date-window flip→Overdue).
  - pagination.total == len(items) trên CÙNG filter, mọi tổ hợp.
  - Không có explicit status: not_closed=1 == _open_capa_filter() byte-for-byte;
    overdue=1 == _overdue_capa_filter() byte-for-byte (no-regression round 10/11).

Run:
    bench --site miyano run-tests --app assetcore \
        --module assetcore.tests.test_capa_drilldown_conjoin
"""
from __future__ import annotations

import time
import unittest

import frappe
from frappe.utils import add_days, nowdate

from assetcore.services.imm00 import (
    _open_capa_filter,
    _overdue_capa_filter,
)

_UID = str(int(time.time()) % 100000)
_DT_CAPA = "IMM CAPA Record"


def setUpModule():
    frappe.set_user("Administrator")


def _insert_asset(cat_name: str):
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    try:
        return frappe.get_doc({
            "doctype": "AC Asset",
            "asset_name": f"_TestCapaConjoin Asset {_UID}",
            "asset_category": cat_name,
            "manufacturer_sn": f"_TestCapaConjoin-SN-{_UID}",
            "medical_device_class": "Class II",
            "risk_classification": "High",
            "purchase_date": "2023-05-12",
            "gross_purchase_amount": 100_000_000,
            "warranty_expiry_date": "2026-05-12",
            "in_service_date": "2023-05-18",
            "lifecycle_status": "Active",
        }).insert(ignore_permissions=True)
    finally:
        frappe.flags.in_install = prev


class TestCapaDrilldownConjoin(unittest.TestCase):
    """list_capas conjoin explicit status AND virtual not_closed/overdue (BR-00-16)."""

    @classmethod
    def setUpClass(cls):
        cls._cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_code": f"_TestCapaConjoinCat-{_UID}",
            "category_name": f"CAPA Conjoin cat {_UID}",
        }).insert(ignore_permissions=True)
        cls._asset = _insert_asset(cls._cat.name)
        cls._names: list[str] = []
        # Seed deterministic set scoped to this asset:
        #   1× Overdue (due past), 1× Open (due future), 1× Closed.
        cls._capa_overdue = cls._mk_capa(cls, "Overdue", add_days(nowdate(), -7))
        cls._capa_open = cls._mk_capa(cls, "Open", add_days(nowdate(), +30))
        cls._capa_closed = cls._mk_capa(cls, "Closed", add_days(nowdate(), -10))
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        for n in cls._names:
            if frappe.db.exists(_DT_CAPA, n):
                d = frappe.get_doc(_DT_CAPA, n)
                if d.docstatus == 1:
                    d.cancel()
                frappe.delete_doc(_DT_CAPA, n, force=True, ignore_permissions=True,
                                  delete_permanently=True)
        frappe.db.sql("DELETE FROM `tabIMM Audit Trail` WHERE asset=%s", (cls._asset.name,))
        frappe.delete_doc("AC Asset", cls._asset.name, force=True, ignore_permissions=True)
        frappe.delete_doc("AC Asset Category", cls._cat.name, force=True, ignore_permissions=True)
        frappe.db.commit()

    def _mk_capa(self, status: str, due_date) -> str:
        payload = {
            "doctype": _DT_CAPA,
            "asset": self._asset.name,
            "source_type": "Non-Conformance",
            "source_ref": "",
            "severity": "Major",
            "description": f"CAPA conjoin fixture {status} {due_date}",
            "responsible": "Administrator",
            "opened_date": add_days(nowdate(), -10),
            "due_date": due_date,
            "status": status,
        }
        # BR-00-26: cổng hiệu quả fire khi status=='Closed' → seed effectiveness hợp lệ.
        if status == "Closed":
            payload.update({
                "effectiveness_check": "Effective",
                "root_cause": "Conjoin fixture root cause",
                "corrective_action": "Conjoin fixture corrective action",
                "preventive_action": "Conjoin fixture preventive action",
                "closed_date": nowdate(),
            })
        doc = frappe.get_doc(payload).insert(ignore_permissions=True)
        self._names.append(doc.name)
        return doc.name

    def _items(self, **kwargs) -> list[dict]:
        """list_capas asset-scoped (factory-parallel safe), page_size cao để full set."""
        from assetcore.api.imm00 import list_capas
        resp = list_capas(page=1, page_size=500, asset=self._asset.name, **kwargs)
        return resp["data"]["items"]

    def _names_in(self, items) -> set[str]:
        return {it["name"] for it in items}

    # ── TDD-1 (RED first w/ dict clobber): conjoin not_closed=1 & status=Overdue ──
    def test_list_capas_status_and_not_closed_conjoin(self):
        """not_closed=1 & status=Overdue → CHỈ CAPA Overdue (KHÔNG Open/Closed).

        RED với code cũ (dict clobber): filters.update(_open_capa_filter()) ghi đè
        key 'status'=Overdue → trả CẢ Open (full open-set) → test FAIL.
        """
        items = self._items(not_closed=1, status="Overdue")
        got = self._names_in(items)
        self.assertIn(self._capa_overdue, got, "Overdue phải có mặt")
        self.assertNotIn(self._capa_open, got,
                         "Open KHÔNG được lọt (conjoin AND, không clobber → either-or)")
        self.assertNotIn(self._capa_closed, got, "Closed bị NOT IN [Closed] loại")
        self.assertEqual(len(items), 1, "CHỈ 1 CAPA Overdue trên asset này")

    # ── TDD-2: status=Closed AND not_closed=1 = ∅ (AND thật, không degrade OR) ────
    def test_list_capas_status_closed_with_not_closed_empty(self):
        from assetcore.api.imm00 import list_capas
        resp = list_capas(page=1, page_size=500, asset=self._asset.name,
                          not_closed=1, status="Closed")
        items = resp["data"]["items"]
        self.assertEqual(resp["data"]["pagination"]["total"], 0,
                         "'Closed' AND NOT IN [Closed] = ∅ (chứng minh AND, không OR)")
        self.assertEqual(items, [], "items rỗng — không bị degrade thành either-or")

    # ── TDD-3: overdue=1 & status=Open = ∅ (Open ngoài date-window overdue) ───────
    def test_list_capas_overdue_and_status_open_empty(self):
        from assetcore.api.imm00 import list_capas
        resp = list_capas(page=1, page_size=500, asset=self._asset.name,
                          overdue=1, status="Open")
        items = resp["data"]["items"]
        # Open fixture có due_date tương lai → KHÔNG nằm tập due<today; AND không giao.
        self.assertEqual(resp["data"]["pagination"]["total"], 0,
                         "Open (due future) ∩ overdue date-window = ∅")
        self.assertEqual(items, [])

    # ── TDD-4: count == len(items) mọi tổ hợp {status} × {none|not_closed|overdue} ─
    def test_list_capas_count_equals_items_all_combos(self):
        from assetcore.api.imm00 import list_capas
        for status in (None, "Open", "Overdue", "Closed"):
            for flag in ({}, {"not_closed": 1}, {"overdue": 1}):
                kwargs = dict(flag)
                if status:
                    kwargs["status"] = status
                resp = list_capas(page=1, page_size=500, asset=self._asset.name, **kwargs)
                total = resp["data"]["pagination"]["total"]
                n = len(resp["data"]["items"])
                self.assertEqual(total, n,
                                 f"pagination.total==len(items) cho status={status} flag={flag}")

    # ── TDD-5 (regression): not_closed=1 / overdue=1 KHÔNG status == SoT byte-for-byte ─
    def test_list_capas_not_closed_only_unchanged(self):
        # not_closed=1 (no explicit status) == _open_capa_filter() membership.
        sot_open = {d.name for d in frappe.get_all(
            _DT_CAPA, filters={**_open_capa_filter(), "asset": self._asset.name},
            fields=["name"])}
        drill_open = self._names_in(self._items(not_closed=1))
        self.assertEqual(drill_open, sot_open,
                         "not_closed=1 (no status) == _open_capa_filter() byte-for-byte")

        # overdue=1 (no explicit status) == _overdue_capa_filter() membership.
        sot_ovd = {d.name for d in frappe.get_all(
            _DT_CAPA, filters={**_overdue_capa_filter(), "asset": self._asset.name},
            fields=["name"])}
        drill_ovd = self._names_in(self._items(overdue=1))
        self.assertEqual(drill_ovd, sot_ovd,
                         "overdue=1 (no status) == _overdue_capa_filter() byte-for-byte")

    # ── TDD-6 (RED-experiment proof, documented; NO revert left behind) ──────────
    def test_list_capas_red_experiment_documented(self):
        """RED-experiment PROOF (đã chạy thủ công, KHÔNG để revert trong code):

        Tạm sửa `list_capas` về `filters.update(_open_capa_filter())` (dict clobber)
        → TDD-1 FAIL (trả CẢ Open vì status=Overdue bị ghi đè), TDD-2 trả full open-set
        thay vì ∅, TDD-3 trả overdue-set thay vì ∅ — ĐÚNG symptom clobber bug #4 ('117').
        Restore list-of-conditions → toàn bộ GREEN.

        Test này là chốt tài liệu hoá; assertion guard: SoT builders trả dict 2-element
        cho overdue (status + due_date) — list-form PHẢI tách thành 2 conditions, không
        thể fit dict-1-predicate-per-field → cấu trúc list là bắt buộc.
        """
        ovd = _overdue_capa_filter()
        self.assertIn("status", ovd)
        self.assertIn("due_date", ovd)
        # Khi kèm explicit status → 2 predicate trên 'status' (==value + not in [Closed])
        # KHÔNG cùng tồn tại trong dict → list-of-conditions là duy nhất đúng.
        self.assertEqual(_open_capa_filter()["status"], ["not in", ["Closed"]])
