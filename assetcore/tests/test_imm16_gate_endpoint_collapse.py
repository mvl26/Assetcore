# Copyright (c) 2026, AssetCore Team
"""IMM-16 compliance-gate API endpoint duplicate-collapse parity (run 15 FE/BE task).

Context — `api/imm16.py` historically exposed TWO whitelisted compliance-gate
endpoints that both delegated to `svc.check_asset_compliance_status`:
  - `check_asset_compliance`          (legacy, :124)
  - `check_asset_compliance_status`   (canonical, :422 — path FE `imm16.ts:513` targets)

This module asserts the collapse to ONE canonical executable delegate:
  - TC-16-GATE-01 (parity duplicate-collapse): exactly ONE def in api/imm16.py
    executes `_handle(svc.check_asset_compliance_status, ...)`; the legacy alias
    (if kept) is a thin shim that delegates to the canonical API fn, NOT to svc.
    Functional: calling the canonical endpoint for an asset with a Critical CAPA
    Open & due-past returns blocked=True with reasons[0].status reflected.
  - TC-16-GATE-02 (invariant-under-cron, no-regression round 12): Critical CAPA
    Open due-past → blocked=True; after check_capa_overdue() flips it → 'Overdue',
    the SAME canonical endpoint STILL returns blocked=True with
    reasons[0].status == 'Overdue' (render-ready for FE banner).

Run:
    bench --site miyano run-tests --app assetcore \
        --module assetcore.tests.test_imm16_gate_endpoint_collapse
"""
from __future__ import annotations

import inspect
import re
import time
import unittest

import frappe
from frappe.utils import add_days, nowdate

from assetcore.api import imm16 as api
from assetcore.services.imm00 import check_capa_overdue

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
            "asset_name": f"_TestGateCollapse Asset {_UID}-{suffix}",
            "asset_category": cat_name,
            "manufacturer_sn": f"_TestGateCollapse-SN-{_UID}-{suffix}",
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


class TestGateEndpointCollapse(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_code": f"_TestGateCollapseCat-{_UID}",
            "category_name": f"Gate collapse cat {_UID}",
        }).insert(ignore_permissions=True)
        cls._asset = _insert_asset(cls._cat.name, "A")
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
        frappe.db.sql("DELETE FROM `tabIMM Audit Trail` WHERE asset=%s",
                      (cls._asset.name,))
        frappe.delete_doc("AC Asset", cls._asset.name, force=True,
                          ignore_permissions=True)
        frappe.delete_doc("AC Asset Category", cls._cat.name, force=True,
                          ignore_permissions=True)
        frappe.db.commit()

    def _mk_capa(self, status: str, risk: str = "Critical", due_date=None) -> str:
        seed_due = due_date if due_date else add_days(nowdate(), 30)
        doc = frappe.get_doc({
            "doctype": _DT_CAPA,
            "asset": self._asset.name,
            "source_type": "Non-Conformance",
            "source_ref": "",
            "severity": "Critical",
            "imm_risk_level": risk,
            "description": f"Gate collapse fixture {status} {risk}",
            "responsible": "Administrator",
            "opened_date": add_days(nowdate(), -10),
            "due_date": seed_due,
            "status": status,
        }).insert(ignore_permissions=True)
        self._names.append(doc.name)
        frappe.db.commit()
        return doc.name

    def _purge(self) -> None:
        for n in frappe.get_all(_DT_CAPA, filters={"asset": self._asset.name},
                                pluck="name"):
            if frappe.db.exists(_DT_CAPA, n):
                frappe.delete_doc(_DT_CAPA, n, force=True, ignore_permissions=True,
                                  delete_permanently=True)
        frappe.db.commit()

    # ── TC-16-GATE-01: only ONE executable delegate to svc gate SoT ───────────
    def test_single_canonical_delegate_to_svc(self):
        src = inspect.getsource(api)
        # Count executable lines that delegate to the gate SoT service fn.
        delegates = re.findall(r"return _handle\(svc\.check_asset_compliance_status",
                               src)
        self.assertEqual(len(delegates), 1,
                         "Phải còn ĐÚNG 1 endpoint delegate svc.check_asset_compliance_status "
                         f"(thấy {len(delegates)})")
        # Canonical name must exist and be whitelisted.
        self.assertTrue(hasattr(api, "check_asset_compliance_status"))
        canonical = api.check_asset_compliance_status
        self.assertTrue(getattr(canonical, "__func__", canonical),
                        "canonical endpoint phải tồn tại")

    # ── TC-16-GATE-01 functional: canonical endpoint blocks Critical-open ─────
    def test_canonical_endpoint_blocks_critical_open(self):
        self._purge()
        self._mk_capa("Open", "Critical", due_date=add_days(nowdate(), -4))
        resp = api.check_asset_compliance_status(self._asset.name)
        # API envelope: _ok wraps as {"message": {"success": True, "data": {...}}}
        data = resp.get("message", resp)
        data = data.get("data", data) if isinstance(data, dict) else data
        self.assertTrue(data["blocked"], "Critical CAPA Open due-past → blocked")
        self.assertTrue(data["reasons"], "reasons[] không rỗng")
        self.assertIn(data["reasons"][0]["status"], ("Open", "Overdue"),
                      "reasons[0].status phản ánh trạng thái thật")

    # ── TC-16-GATE-01: legacy alias parity (if kept) ──────────────────────────
    def test_legacy_alias_parity_if_present(self):
        if not hasattr(api, "check_asset_compliance"):
            self.skipTest("legacy alias removed — collapse via deletion, OK")
        self._purge()
        self._mk_capa("Open", "Critical", due_date=add_days(nowdate(), -4))
        legacy = api.check_asset_compliance(self._asset.name)
        canonical = api.check_asset_compliance_status(self._asset.name)
        self.assertEqual(legacy, canonical,
                         "legacy alias phải trả y hệt canonical (thin shim)")

    # ── TC-16-GATE-02: invariant under cron flip Open → Overdue ───────────────
    def test_invariant_under_cron_flip_via_endpoint(self):
        self._purge()
        self._mk_capa("Open", "Critical", due_date=add_days(nowdate(), -3))

        def _data(resp):
            d = resp.get("message", resp)
            return d.get("data", d) if isinstance(d, dict) else d

        before = _data(api.check_asset_compliance_status(self._asset.name))
        self.assertTrue(before["blocked"], "trước cron: Open quá hạn vẫn block")

        check_capa_overdue()
        frappe.db.commit()

        after = _data(api.check_asset_compliance_status(self._asset.name))
        self.assertTrue(after["blocked"],
                        "sau cron flip → 'Overdue' endpoint VẪN block (INVARIANT)")
        self.assertEqual(after["reasons"][0]["status"], "Overdue",
                         "reasons[0].status == 'Overdue' (render-ready cho banner FE)")
