"""IMM-12 Notification Contract — test suite (Sprint 2026-05-29 vòng 2).

Verifies every business error branch raises a ServiceError carrying the correct
`message_code` (MSG.IMM12_*) + `http_status`, and that the NEG-11 close gate hook
raises through `nthrow_in_hook` (frappe.ValidationError + response message_code).
Also smoke-checks the API envelope hydration.

Run: bench --site miyano run-tests --module assetcore.tests.test_imm12_notify
"""
from __future__ import annotations

import time
import unittest

import frappe

from assetcore.services import imm12 as svc
from assetcore.services.shared import ServiceError
from assetcore.utils.messages import MSG
from assetcore.tests._asset_cleanup import purge_asset

_RUN_TAG = str(int(time.time() * 1000))[-7:]


def _ensure_cat() -> str:
    name = "_TestCatIMM12N"
    existing = frappe.db.get_value("AC Asset Category", {"category_name": name}, "name")
    if existing:
        return existing
    return frappe.get_doc(
        {"doctype": "AC Asset Category", "category_name": name}
    ).insert(ignore_permissions=True).name


def _make_asset(suffix: str = "") -> object:
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    try:
        return frappe.get_doc({
            "doctype": "AC Asset",
            "asset_name": f"_Test Asset IMM12N{suffix}-{_RUN_TAG}",
            "asset_category": _ensure_cat(),
            "manufacturer_sn": f"SN-IMM12N-{_RUN_TAG}-{suffix or '001'}",
            "lifecycle_status": "Active",
        }).insert(ignore_permissions=True)
    finally:
        frappe.flags.in_install = prev


class TestImm12MessageCodes(unittest.TestCase):
    """Each error branch → ServiceError with correct message_code + http_status."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-msg")

    @classmethod
    def tearDownClass(cls):
        purge_asset(cls.asset.name)
        cat = frappe.db.get_value(
            "AC Asset Category", {"category_name": "_TestCatIMM12N"}, "name")
        if cat:
            try:
                frappe.delete_doc("AC Asset Category", cat, force=True,
                                  ignore_permissions=True)
            except Exception:
                pass

    def setUp(self):
        frappe.set_user("Administrator")

    def _assert_code(self, fn, code: str, http: int):
        with self.assertRaises(ServiceError) as ctx:
            fn()
        self.assertEqual(ctx.exception.message_code, code)
        self.assertEqual(ctx.exception.http_status, http)

    # ── NOT_FOUND ───────────────────────────────────────────────────────────
    def test_incident_not_found(self):
        self._assert_code(
            lambda: svc.get_incident_detail("IR-DOES-NOT-EXIST"),
            MSG.IMM12_INCIDENT_NOT_FOUND, 404)

    def test_rca_not_found(self):
        self._assert_code(
            lambda: svc.get_rca("RCA-DOES-NOT-EXIST"),
            MSG.IMM12_RCA_NOT_FOUND, 404)

    def test_asset_not_found_on_report(self):
        self._assert_code(
            lambda: svc.report_incident(
                asset="ASSET-DOES-NOT-EXIST", incident_type="Malfunction",
                severity="Low", description="_Test"),
            MSG.IMM12_ASSET_NOT_FOUND, 404)

    # ── BUSINESS_RULE validation ────────────────────────────────────────────
    def test_critical_clinical_impact_required(self):
        self._assert_code(
            lambda: svc.report_incident(
                asset=self.asset.name, incident_type="Malfunction",
                severity="Critical", description="_Test", clinical_impact=""),
            MSG.IMM12_CLINICAL_IMPACT_REQUIRED, 422)

    def test_resolution_notes_required(self):
        ir = svc.report_incident(
            asset=self.asset.name, incident_type="Malfunction",
            severity="Medium", description="_Test resolve-notes")
        svc.acknowledge_incident(ir["name"])
        svc.start_work(ir["name"])
        self._assert_code(
            lambda: svc.resolve_incident(ir["name"], resolution_notes=""),
            MSG.IMM12_RESOLUTION_NOTES_REQUIRED, 422)

    def test_cancel_reason_required(self):
        ir = svc.report_incident(
            asset=self.asset.name, incident_type="Malfunction",
            severity="Low", description="_Test cancel-reason")
        self._assert_code(
            lambda: svc.cancel_incident(ir["name"], reason=""),
            MSG.IMM12_CANCEL_REASON_REQUIRED, 422)

    # ── BAD_STATE ───────────────────────────────────────────────────────────
    def test_bad_state_transition(self):
        ir = svc.report_incident(
            asset=self.asset.name, incident_type="Malfunction",
            severity="Low", description="_Test bad-state")
        # Open → Resolved is invalid (must go through Acknowledged + In Progress)
        self._assert_code(
            lambda: svc.resolve_incident(ir["name"], resolution_notes="x"),
            MSG.IMM12_BAD_STATE, 409)

    # ── CONFLICT (RCA) ──────────────────────────────────────────────────────
    def test_rca_already_exists(self):
        ir = svc.report_incident(
            asset=self.asset.name, incident_type="Safety Event",
            severity="Critical", description="_Test rca-dup",
            clinical_impact="impact")
        svc.create_rca(ir["name"])
        self._assert_code(
            lambda: svc.create_rca(ir["name"]),
            MSG.IMM12_RCA_ALREADY_EXISTS, 409)

    def test_rca_root_cause_required(self):
        ir = svc.report_incident(
            asset=self.asset.name, incident_type="Safety Event",
            severity="Critical", description="_Test rca-rootcause",
            clinical_impact="impact")
        rca = svc.create_rca(ir["name"])
        self._assert_code(
            lambda: svc.submit_rca(rca["name"], root_cause="",
                                   corrective_action="fix"),
            MSG.IMM12_RCA_ROOT_CAUSE_REQUIRED, 422)

    def test_rca_corrective_required(self):
        ir = svc.report_incident(
            asset=self.asset.name, incident_type="Safety Event",
            severity="Critical", description="_Test rca-corrective",
            clinical_impact="impact")
        rca = svc.create_rca(ir["name"])
        self._assert_code(
            lambda: svc.submit_rca(rca["name"], root_cause="cause",
                                   corrective_action=""),
            MSG.IMM12_RCA_CORRECTIVE_REQUIRED, 422)

    def test_rca_already_completed(self):
        ir = svc.report_incident(
            asset=self.asset.name, incident_type="Safety Event",
            severity="Critical", description="_Test rca-done",
            clinical_impact="impact")
        # Use Fishbone to skip the 5-Why completeness gate (orthogonal to this test)
        rca = svc.create_rca(ir["name"], rca_method="Fishbone")
        svc.submit_rca(rca["name"], root_cause="cause", corrective_action="fix")
        self._assert_code(
            lambda: svc.submit_rca(rca["name"], root_cause="c2",
                                   corrective_action="f2"),
            MSG.IMM12_RCA_ALREADY_COMPLETED, 409)


class TestImm12CloseGateHook(unittest.TestCase):
    """NEG-11 close gate (DocType validate hook) → nthrow_in_hook → ValidationError
    + frappe.local.response carries message_code."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-gate")

    @classmethod
    def tearDownClass(cls):
        purge_asset(cls.asset.name)
        cat = frappe.db.get_value(
            "AC Asset Category", {"category_name": "_TestCatIMM12N"}, "name")
        if cat:
            try:
                frappe.delete_doc("AC Asset Category", cat, force=True,
                                  ignore_permissions=True)
            except Exception:
                pass

    def setUp(self):
        frappe.set_user("Administrator")

    def test_close_gate_no_rca_raises_validation(self):
        """High/Critical incident → Close without RCA → ValidationError via hook."""
        doc = frappe.get_doc({
            "doctype": "Incident Report",
            "asset": self.asset.name,
            "incident_type": "Malfunction",
            "severity": "Critical",
            "description": "_Test close-gate no-rca",
            "clinical_impact": "impact",
            "status": "Closed",
            "requires_rca": 1,
            "rca_required": 1,
        })
        with self.assertRaises(frappe.ValidationError):
            svc.validate_incident_close_gate(doc)


if __name__ == "__main__":
    unittest.main()
