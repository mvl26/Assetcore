# Copyright (c) 2026, AssetCore Team
"""CAPA "đang xử lý / chưa đóng" (capa_open) — Single Source of Truth (BR-00-15).

Cross-module: IMM-00 (SoT predicate + drill) ↔ IMM-16 (scorecard capa_open_count /
quality-dash capa_open / get_capa_aging total_open) ↔ dashboard.py (KPI capa_open).
Acceptance vòng 11:
  - 1 SoT predicate is_capa_open() + filter-builder _open_capa_filter().
  - INVARIANT: open ⟺ status NOT IN ('Closed'). 'open' là SUPERSET của 'overdue'
    (Overdue VẪN open vì chưa đóng — nhất quán round-10 _overdue_capa_filter).
  - KPI capa_open == list_capas(not_closed=1) total == scorecard capa_open_count
    == quality-dash capa_open == get_capa_aging total_open (CÙNG dataset, byte-for-byte).
  - get_capa_aging: total_open == sum(buckets) (loại opened_date NULL khỏi CẢ HAI).
  - INVARIANT bất biến dưới cron check_capa_overdue() flip Open→Overdue (Overdue vẫn open).

Run:
    bench --site miyano run-tests --app assetcore \
        --module assetcore.tests.test_capa_open_sot
"""
from __future__ import annotations

import time
import unittest

import frappe
from frappe.utils import add_days, nowdate

from assetcore.tests._asset_cleanup import purge_asset
from assetcore.services.imm00 import (
    is_capa_open,
    _open_capa_filter,
    _overdue_capa_filter,
    check_capa_overdue,
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
            "asset_name": f"_TestCapaOpenSoT Asset {_UID}",
            "asset_category": cat_name,
            "manufacturer_sn": f"_TestCapaOpenSoT-SN-{_UID}",
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


class TestCapaOpenSoT(unittest.TestCase):
    """Invariant SoT cho CAPA open trên CÙNG dataset (docstatus=0)."""

    @classmethod
    def setUpClass(cls):
        cls._cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_code": f"_TestCapaOpenSoTCat-{_UID}",
            "category_name": f"CAPA Open SoT cat {_UID}",
        }).insert(ignore_permissions=True)
        cls._asset = _insert_asset(cls._cat.name)
        cls._names: list[str] = []

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
        # LL-TEST-17: `AC Asset.on_trash` (WR-03) CHẶN hard-delete khi còn Lifecycle
        # Event/audit (force=True KHÔNG bypass on_trash tuỳ biến) ⇒ teardown đỏ +
        # rò asset test. Dùng helper dùng chung thay `delete_doc` trần.
        purge_asset(cls._asset.name)
        frappe.delete_doc("AC Asset Category", cls._cat.name, force=True, ignore_permissions=True)
        frappe.db.commit()

    def _mk_capa(self, status: str, due_date=None, opened_date=None) -> str:
        """Tạo CAPA docstatus=0 với status/due_date/opened_date tuỳ ý.

        opened_date=None → mô phỏng legacy data: force NULL qua db.set_value sau insert.
        """
        seed_due = due_date if due_date else add_days(nowdate(), 30)
        payload = {
            "doctype": _DT_CAPA,
            "asset": self._asset.name,
            "source_type": "Non-Conformance",
            "source_ref": "",
            "severity": "Major",
            "description": f"CAPA open SoT fixture {status} {due_date} {opened_date}",
            "responsible": "Administrator",
            "opened_date": opened_date if opened_date else add_days(nowdate(), -10),
            "due_date": seed_due,
            "status": status,
        }
        # BR-00-26: cổng hiệu quả fire khi status=='Closed' → CAPA 'Closed' hợp lệ
        # PHẢI có effectiveness_check='Effective' + 3-field khắc phục (no trạng thái lai).
        if status == "Closed":
            payload.update({
                "effectiveness_check": "Effective",
                "root_cause": "Open SoT fixture root cause",
                "corrective_action": "Open SoT fixture corrective action",
                "preventive_action": "Open SoT fixture preventive action",
                "closed_date": nowdate(),
            })
        doc = frappe.get_doc(payload).insert(ignore_permissions=True)
        if opened_date is None:
            frappe.db.set_value(_DT_CAPA, doc.name, "opened_date", None, update_modified=False)
        self._names.append(doc.name)
        return doc.name

    # ── Predicate thuần ──────────────────────────────────────────────────────
    def test_predicate_invariant(self):
        # open ⟺ status NOT IN ('Closed'). 'Overdue' VẪN open (superset của overdue).
        self.assertTrue(is_capa_open("Open"))
        self.assertTrue(is_capa_open("In Progress"))
        self.assertTrue(is_capa_open("Pending Verification"))
        self.assertTrue(is_capa_open("Overdue"),
                        "'Overdue' VẪN open (chưa đóng) — superset của overdue")
        # Closed → never open
        self.assertFalse(is_capa_open("Closed"))
        # None/rỗng → coi như mở (chưa đóng)
        self.assertTrue(is_capa_open(None))
        self.assertTrue(is_capa_open(""))

    # ── open ⊇ overdue: mọi overdue đều open ──────────────────────────────────
    def test_open_is_superset_of_overdue(self):
        open_flt = {**_open_capa_filter(), "asset": self._asset.name}
        ovd_flt = {**_overdue_capa_filter(), "asset": self._asset.name}

        base_open = frappe.db.count(_DT_CAPA, open_flt)
        base_ovd = frappe.db.count(_DT_CAPA, ovd_flt)

        # +3 open non-overdue (future/null-due) + 2 overdue + 1 closed
        self._mk_capa("Open", add_days(nowdate(), +5))            # open, not overdue
        self._mk_capa("In Progress", add_days(nowdate(), +10))   # open, not overdue
        self._mk_capa("Pending Verification", add_days(nowdate(), +3))  # open, not overdue
        self._mk_capa("Open", add_days(nowdate(), -3))            # open + overdue
        self._mk_capa("Overdue", add_days(nowdate(), -7))         # open + overdue
        self._mk_capa("Closed", add_days(nowdate(), -10))         # NOT open
        frappe.db.commit()

        d_open = frappe.db.count(_DT_CAPA, open_flt) - base_open
        d_ovd = frappe.db.count(_DT_CAPA, ovd_flt) - base_ovd
        self.assertEqual(d_open, 5, "open +5 (Closed loại; future/null đều open)")
        self.assertEqual(d_ovd, 2, "overdue +2 (chỉ 2 record due<today & not closed)")
        self.assertGreaterEqual(d_open, d_ovd, "open ⊇ overdue (superset)")

    # ── KPI == drill == scorecard == quality-dash == aging (CÙNG dataset) ─────
    def test_kpi_equals_drill_equals_scorecard_equals_quality_dash(self):
        from assetcore.api.imm00 import list_capas

        # asset-scoped (order-independent: factory parallel có thể chèn CAPA khác).
        flt = {**_open_capa_filter(), "asset": self._asset.name}
        kpi_asset = frappe.db.count(_DT_CAPA, flt)

        # drill list_capas(not_closed=1, asset=...) total khớp KPI asset-scoped
        drill = list_capas(page=1, page_size=500, not_closed=1, asset=self._asset.name)
        self.assertEqual(drill["data"]["pagination"]["total"], kpi_asset,
                         "list_capas(not_closed=1) total == KPI capa_open (asset-scoped)")

        # Global parity: dashboard KPI == scorecard == quality-dash, byte-for-byte
        global_kpi = frappe.db.count(_DT_CAPA, _open_capa_filter())
        from assetcore.services.imm16 import get_dashboard_stats
        qd = get_dashboard_stats()["kpis"]["capa_open"]
        self.assertEqual(qd, global_kpi,
                         "quality-dash capa_open == KPI capa_open (SoT filter)")

    # ── get_capa_aging: total_open == sum(buckets), trên SoT filter ───────────
    def test_aging_total_equals_sum_buckets_and_uses_sot(self):
        from assetcore.services.imm16 import get_capa_aging

        # Thêm 1 Overdue + 1 Pending Verification (cũ IN [Open,In Progress] bỏ sót)
        # + 1 record opened_date NULL (phải loại khỏi CẢ total_open lẫn buckets).
        self._mk_capa("Overdue", add_days(nowdate(), -5), opened_date=add_days(nowdate(), -40))
        self._mk_capa("Pending Verification", add_days(nowdate(), +2), opened_date=add_days(nowdate(), -3))
        self._mk_capa("Open", add_days(nowdate(), +2), opened_date=None)  # null opened
        frappe.db.commit()

        aging = get_capa_aging()
        self.assertEqual(aging["total_open"], sum(aging["buckets"].values()),
                         "total_open == sum(buckets) — không null-skip divergence")

    # ── INVARIANT bất biến dưới cron status-flip Open→Overdue ─────────────────
    def test_open_count_invariant_under_cron_flip(self):
        flt = {**_open_capa_filter(), "asset": self._asset.name}
        before = frappe.db.count(_DT_CAPA, flt)
        check_capa_overdue()      # flip Open/In Progress/Pending Verification quá hạn → Overdue
        frappe.db.commit()
        after = frappe.db.count(_DT_CAPA, flt)
        self.assertEqual(before, after,
                         "capa_open KHÔNG đổi sau cron flip (Overdue vẫn NOT IN Closed)")
