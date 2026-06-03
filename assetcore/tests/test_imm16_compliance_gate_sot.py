# Copyright (c) 2026, AssetCore Team
"""IMM-16 Critical-CAPA-open ENFORCEMENT gate — SoT parity (BR-16-09 round 12).

Cross-module: IMM-00 (SoT predicate `is_capa_open` / filter `_open_capa_filter`)
↔ IMM-16 (`check_asset_compliance_status` ENFORCEMENT consumer + `gate_wo_submit`
doc-event) ↔ IMM-04 (commissioning gate, same fn).

Acceptance vòng 12 (UNIFY gate predicate về SoT):
  - `check_asset_compliance_status` KHÔNG còn inline literal
    `status IN [Open, In Progress, Pending Verification]` (bỏ sót 'Overdue').
  - Gate membership = SoT `_open_capa_filter()` → status NOT IN ('Closed');
    'Overdue' NẰM TRONG tập block.
  - INVARIANT dưới cron: 1 Critical CAPA mở trên asset → gate.blocked == True
    TRƯỚC cron (status Open) VÀ SAU khi check_capa_overdue() flip → 'Overdue'
    (byte-for-byte cùng tập, count không rỗng đi).
  - `gate_wo_submit` chặn submit Work Order (frappe.throw) khi asset có Critical
    CAPA status='Overdue' (lỗ cũ: KHÔNG chặn).
  - Closed Critical CAPA KHÔNG block (true-negative).
  - Non-Critical (High/...) CAPA KHÔNG block dù Overdue (filter Critical giữ nguyên).
  - reasons[].status trả đúng 'Overdue' cho CAPA overdue đang block.
  - Parity SoT: tập crit_capas của gate == frappe.get_all(CAPA, {asset, imm_risk_level
    'Critical', **_open_capa_filter()}) byte-for-byte.

Run:
    bench --site miyano run-tests --app assetcore \
        --module assetcore.tests.test_imm16_compliance_gate_sot
"""
from __future__ import annotations

import time
import unittest

import frappe
from frappe.utils import add_days, nowdate

from assetcore.services import imm16 as svc
from assetcore.services.imm00 import _open_capa_filter, check_capa_overdue

_UID = str(int(time.time()) % 100000)
_DT_CAPA = "IMM CAPA Record"


def setUpModule():
    frappe.set_user("Administrator")


def _insert_asset(cat_name: str, suffix: str):
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    try:
        return frappe.get_doc({
            "doctype": "AC Asset",
            "asset_name": f"_TestGateSoT Asset {_UID}-{suffix}",
            "asset_category": cat_name,
            "manufacturer_sn": f"_TestGateSoT-SN-{_UID}-{suffix}",
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


class TestComplianceGateSoT(unittest.TestCase):
    """ENFORCEMENT gate dùng cùng SoT membership với capa_open (invariant cron)."""

    @classmethod
    def setUpClass(cls):
        cls._cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_code": f"_TestGateSoTCat-{_UID}",
            "category_name": f"Gate SoT cat {_UID}",
        }).insert(ignore_permissions=True)
        # Asset A: carries Critical CAPA fixtures (flippable by cron).
        cls._asset = _insert_asset(cls._cat.name, "A")
        # Asset B: isolated true-negative / non-Critical scenarios.
        cls._asset_b = _insert_asset(cls._cat.name, "B")
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
        for a in (cls._asset, cls._asset_b):
            frappe.db.sql("DELETE FROM `tabIMM Audit Trail` WHERE asset=%s", (a.name,))
            frappe.delete_doc("AC Asset", a.name, force=True, ignore_permissions=True)
        frappe.delete_doc("AC Asset Category", cls._cat.name, force=True,
                          ignore_permissions=True)
        frappe.db.commit()

    def _mk_capa(self, asset: str, status: str, risk: str = "Critical",
                 due_date=None) -> str:
        """CAPA docstatus=0 với status / imm_risk_level / due_date tuỳ ý."""
        seed_due = due_date if due_date else add_days(nowdate(), 30)
        doc = frappe.get_doc({
            "doctype": _DT_CAPA,
            "asset": asset,
            "source_type": "Non-Conformance",
            "source_ref": "",
            "severity": "Critical",
            "imm_risk_level": risk,
            "description": f"Gate SoT fixture {status} {risk} {due_date}",
            "responsible": "Administrator",
            "opened_date": add_days(nowdate(), -10),
            "due_date": seed_due,
            "status": status,
        }).insert(ignore_permissions=True)
        self._names.append(doc.name)
        frappe.db.commit()
        return doc.name

    def _purge_asset_capas(self, asset: str) -> None:
        """Xoá toàn bộ CAPA của 1 asset để cô lập từng scenario."""
        for n in frappe.get_all(_DT_CAPA, filters={"asset": asset}, pluck="name"):
            if frappe.db.exists(_DT_CAPA, n):
                frappe.delete_doc(_DT_CAPA, n, force=True, ignore_permissions=True,
                                  delete_permanently=True)
        frappe.db.commit()

    # ── Baseline: Critical CAPA 'Open' → blocked ──────────────────────────────
    def test_critical_open_blocks(self):
        self._purge_asset_capas(self._asset.name)
        self._mk_capa(self._asset.name, "Open", "Critical")
        res = svc.check_asset_compliance_status(self._asset.name)
        self.assertTrue(res["blocked"], "Critical CAPA Open phải block (baseline)")
        self.assertEqual(res["active_capas_count"], 1)

    # ── INVARIANT cron-flip: Open → Overdue VẪN block (RED với code cũ) ────────
    def test_invariant_under_cron_flip_to_overdue(self):
        self._purge_asset_capas(self._asset.name)
        # 1 Critical CAPA Open quá hạn (due < today) → cron sẽ flip → 'Overdue'.
        self._mk_capa(self._asset.name, "Open", "Critical",
                      due_date=add_days(nowdate(), -3))

        before = svc.check_asset_compliance_status(self._asset.name)
        self.assertTrue(before["blocked"], "trước cron: Open quá hạn vẫn block")

        check_capa_overdue()   # flip Open quá hạn → 'Overdue'
        frappe.db.commit()

        after = svc.check_asset_compliance_status(self._asset.name)
        self.assertTrue(after["blocked"],
                        "sau cron flip → 'Overdue' gate VẪN block (INVARIANT SoT)")
        self.assertEqual(after["active_capas_count"], 1,
                         "count không rỗng đi sau cron flip")
        self.assertEqual(after["reasons"][0]["status"], "Overdue",
                         "reasons[].status trả 'Overdue' thật (không nuốt lý do)")

    # ── gate_wo_submit chặn WO khi Critical CAPA 'Overdue' (lỗ cũ) ────────────
    def test_gate_wo_submit_blocks_when_overdue(self):
        self._purge_asset_capas(self._asset.name)
        self._mk_capa(self._asset.name, "Overdue", "Critical",
                      due_date=add_days(nowdate(), -5))

        class _FakeWO:
            asset_ref = self._asset.name

        with self.assertRaises(frappe.ValidationError) as ctx:
            svc.gate_wo_submit(_FakeWO())
        self.assertIn("BR-16-09", str(ctx.exception),
                      "message phải chứa BR-16-09")

    def test_gate_wo_submit_passes_when_closed(self):
        self._purge_asset_capas(self._asset.name)
        self._mk_capa(self._asset.name, "Closed", "Critical")

        class _FakeWO:
            asset_ref = self._asset.name

        # Không throw — true-negative (Closed không block).
        svc.gate_wo_submit(_FakeWO())

    # ── true-negative: Closed Critical CAPA KHÔNG block ───────────────────────
    def test_closed_critical_not_blocked(self):
        self._purge_asset_capas(self._asset_b.name)
        self._mk_capa(self._asset_b.name, "Closed", "Critical")
        res = svc.check_asset_compliance_status(self._asset_b.name)
        self.assertFalse(res["blocked"], "Closed Critical KHÔNG block (true-negative)")
        self.assertEqual(res["active_capas_count"], 0)

    # ── non-Critical 'Overdue' KHÔNG block (filter Critical giữ nguyên) ────────
    def test_high_severity_overdue_not_blocked(self):
        self._purge_asset_capas(self._asset_b.name)
        self._mk_capa(self._asset_b.name, "Overdue", "High",
                      due_date=add_days(nowdate(), -5))
        res = svc.check_asset_compliance_status(self._asset_b.name)
        self.assertFalse(res["blocked"],
                         "High-severity Overdue KHÔNG block (imm_risk_level filter)")
        self.assertEqual(res["active_capas_count"], 0)

    # ── parity SoT: gate crit_capas == get_all(..., **_open_capa_filter()) ────
    def test_gate_parity_with_sot_filter(self):
        self._purge_asset_capas(self._asset.name)
        # Mix: Open / In Progress / Pending Verification / Overdue / Closed.
        self._mk_capa(self._asset.name, "Open", "Critical")
        self._mk_capa(self._asset.name, "In Progress", "Critical")
        self._mk_capa(self._asset.name, "Pending Verification", "Critical")
        self._mk_capa(self._asset.name, "Overdue", "Critical",
                      due_date=add_days(nowdate(), -2))
        self._mk_capa(self._asset.name, "Closed", "Critical")

        res = svc.check_asset_compliance_status(self._asset.name)
        sot = frappe.get_all(
            _DT_CAPA,
            filters={"asset": self._asset.name, "imm_risk_level": "Critical",
                     **_open_capa_filter()},
            pluck="name",
        )
        gate_refs = sorted(r["ref"] for r in res["reasons"]
                           if r["type"] == "CAPA_CRITICAL_OPEN")
        self.assertEqual(gate_refs, sorted(sot),
                         "gate crit_capas == SoT _open_capa_filter (byte-for-byte)")
        self.assertEqual(res["active_capas_count"], 4,
                         "4 mở (Open/In Progress/Pending Verification/Overdue), Closed loại")
        self.assertTrue(res["blocked"])
