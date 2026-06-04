# Copyright (c) 2026, AssetCore Team
"""CAPA "quá hạn" — Single Source of Truth invariant (BR-00-09).

Cross-module: IMM-00 (setter + drill) ↔ IMM-16 (scorecard/quality-dash/overdue-actions)
↔ dashboard.py (KPI). Acceptance vòng 10:
  - 1 SoT predicate is_capa_overdue() + filter-builder _overdue_capa_filter().
  - INVARIANT: overdue ⟺ status NOT IN ('Closed') AND due_date IS NOT NULL AND due_date < today.
  - KPI count == drill rows == imm16 get_overdue_actions overdue_capas (CÙNG dataset).
  - Cron check_capa_overdue() flip {Open, In Progress, Pending Verification} quá hạn → 'Overdue';
    count BẤT BIẾN sau flip; idempotent; null-guard.

Run:
    bench --site miyano run-tests --app assetcore \
        --module assetcore.tests.test_capa_overdue_sot
"""
from __future__ import annotations

import time
import unittest

import frappe
from frappe.utils import add_days, nowdate

from assetcore.services.imm00 import (
    is_capa_overdue,
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
            "asset_name": f"_TestCapaSoT Asset {_UID}",
            "asset_category": cat_name,
            "manufacturer_sn": f"_TestCapaSoT-SN-{_UID}",
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


class TestCapaOverdueSoT(unittest.TestCase):
    """Invariant SoT cho CAPA overdue trên CÙNG dataset (docstatus=0)."""

    @classmethod
    def setUpClass(cls):
        cls._cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_code": f"_TestCapaSoTCat-{_UID}",
            "category_name": f"CAPA SoT cat {_UID}",
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
        frappe.delete_doc("AC Asset", cls._asset.name, force=True, ignore_permissions=True)
        frappe.delete_doc("AC Asset Category", cls._cat.name, force=True, ignore_permissions=True)
        frappe.db.commit()

    def _mk_capa(self, status: str, due_date) -> str:
        """Tạo CAPA docstatus=0 với status/due_date tuỳ ý (bypass create_capa due math).

        due_date=None → mô phỏng legacy data: insert với due hợp lệ rồi force NULL qua
        db.set_value (due_date là reqd=1 nên không insert thẳng NULL được).
        """
        seed_due = due_date if due_date else add_days(nowdate(), 30)
        payload = {
            "doctype": _DT_CAPA,
            "asset": self._asset.name,
            "source_type": "Non-Conformance",
            "source_ref": "",
            "severity": "Major",
            "description": f"CAPA SoT fixture {status} {due_date}",
            "responsible": "Administrator",
            "opened_date": add_days(nowdate(), -60),
            "due_date": seed_due,
            "status": status,
        }
        # BR-00-26: cổng hiệu quả fire khi status=='Closed' → seed effectiveness hợp lệ.
        if status == "Closed":
            payload.update({
                "effectiveness_check": "Effective",
                "root_cause": "Overdue SoT fixture root cause",
                "corrective_action": "Overdue SoT fixture corrective action",
                "preventive_action": "Overdue SoT fixture preventive action",
                "closed_date": nowdate(),
            })
        doc = frappe.get_doc(payload).insert(ignore_permissions=True)
        if due_date is None:
            frappe.db.set_value(_DT_CAPA, doc.name, "due_date", None, update_modified=False)
        self._names.append(doc.name)
        return doc.name

    # ── Predicate thuần ──────────────────────────────────────────────────────
    def test_predicate_invariant(self):
        today = nowdate()
        y = add_days(today, -1)
        t = add_days(today, +1)
        # overdue ⟺ NOT Closed AND due_date NOT NULL AND due_date < today (strict)
        self.assertTrue(is_capa_overdue("Open", y, today))
        self.assertTrue(is_capa_overdue("In Progress", y, today))
        self.assertTrue(is_capa_overdue("Pending Verification", y, today))
        self.assertTrue(is_capa_overdue("Overdue", y, today),
                        "'Overdue'-status CAPA VẪN đếm là overdue (NOT IN Closed)")
        # Closed → never overdue
        self.assertFalse(is_capa_overdue("Closed", y, today))
        # strict < : due == today CHƯA quá hạn
        self.assertFalse(is_capa_overdue("Open", today, today))
        # future due
        self.assertFalse(is_capa_overdue("Open", t, today))
        # null-guard
        self.assertFalse(is_capa_overdue("Open", None, today))
        self.assertFalse(is_capa_overdue("Open", "", today))

    # ── KPI == drill == get_overdue_actions trên CÙNG dataset ────────────────
    def test_kpi_equals_drill_equals_overdue_actions(self):
        from assetcore.api.imm00 import list_overdue_capas
        from assetcore.services.imm16 import get_overdue_actions

        # baseline asset-scoped (order-independent: class-scoped fixture có thể chứa
        # CAPA từ test khác → so DELTA, không so absolute).
        flt = {**_overdue_capa_filter(), "asset": self._asset.name}
        base = frappe.db.count(_DT_CAPA, flt)

        # +3 overdue (mỗi non-terminal state) + 1 future + 1 closed + 1 null-due
        self._mk_capa("Open", add_days(nowdate(), -3))
        self._mk_capa("In Progress", add_days(nowdate(), -2))
        self._mk_capa("Pending Verification", add_days(nowdate(), -1))
        self._mk_capa("Open", add_days(nowdate(), +5))          # future → not overdue
        self._mk_capa("Open", None)                              # null → not overdue
        self._mk_capa("Closed", add_days(nowdate(), -10))        # Closed → not overdue
        frappe.db.commit()

        kpi = frappe.db.count(_DT_CAPA, flt)
        self.assertEqual(kpi - base, 3,
                         "KPI capa_overdue (asset-scoped) phải +3 (future/null/closed loại)")

        # drill list (toàn cục) ⊇ overdue của asset test → so trên subset asset
        drill = list_overdue_capas(page=1, page_size=500)["data"]["items"]
        drill_asset = [r for r in drill if r["asset"] == self._asset.name]
        self.assertEqual(len(drill_asset), kpi,
                         "drill rows (asset-scoped) == KPI count")

        # get_overdue_actions overdue_capas (toàn cục) → subset asset
        actions = get_overdue_actions()["overdue_capas"]
        actions_asset = [r for r in actions if r["asset"] == self._asset.name]
        self.assertEqual(len(actions_asset), kpi,
                         "get_overdue_actions overdue_capas (asset-scoped) == KPI count")

    # ── Invariant under cron status-flip ─────────────────────────────────────
    def test_count_invariant_under_cron_flip(self):
        flt = {**_overdue_capa_filter(), "asset": self._asset.name}
        before = frappe.db.count(_DT_CAPA, flt)
        check_capa_overdue()       # flip Open/In Progress/Pending Verification → Overdue
        frappe.db.commit()
        after = frappe.db.count(_DT_CAPA, flt)
        self.assertEqual(before, after,
                         "count KHÔNG được tụt sau cron flip (Overdue NOT IN Closed)")

        # Idempotent: chạy lại không đổi count, không tạo record mới
        check_capa_overdue()
        frappe.db.commit()
        self.assertEqual(frappe.db.count(_DT_CAPA, flt), after,
                         "check_capa_overdue idempotent")

    # ── Cron mở rộng tới Pending Verification ────────────────────────────────
    def test_cron_flips_pending_verification(self):
        pv = self._mk_capa("Pending Verification", add_days(nowdate(), -4))
        frappe.db.commit()
        check_capa_overdue()
        frappe.db.commit()
        self.assertEqual(frappe.db.get_value(_DT_CAPA, pv, "status"), "Overdue",
                         "cron PHẢI flip 'Pending Verification' quá hạn → 'Overdue'")

    def test_cron_null_due_not_flipped(self):
        nd = self._mk_capa("Open", None)
        frappe.db.commit()
        check_capa_overdue()
        frappe.db.commit()
        self.assertEqual(frappe.db.get_value(_DT_CAPA, nd, "status"), "Open",
                         "due_date NULL KHÔNG bao giờ flip → Overdue (null-guard)")
