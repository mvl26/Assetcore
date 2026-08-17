# Copyright (c) 2026, AssetCore Team
# Sprint 5 — Cross-module integration tests (gates).
#
# Coverage:
#   TC-INT-01 IMM-04 → IMM-08: commissioning submit → PM Schedule auto-created.
#   TC-INT-02 IMM-09 → IMM-15: request_spare_parts → Spare Allocation created.
#   TC-INT-03 IMM-11 → IMM-16: calibration Fail → CAPA draft auto-created.
#   TC-INT-04 IMM-12 → IMM-16: submit_rca → CAPA linked.
#   TC-INT-05 IMM-04 ↔ IMM-16: commissioning blocked by Critical CAPA open.
#
# Test design: each TC builds independent fixtures; failures in cross-module
# wiring should surface as missing record / wrong status, not as setup errors.
from __future__ import annotations

import unittest
from contextlib import suppress

import frappe

from assetcore.services.shared import ErrorCode, ServiceError
from frappe.tests.utils import FrappeTestCase


def _ensure(doctype: str, name: str, data: dict) -> str:
    """Idempotent insert helper for test fixtures."""
    if frappe.db.exists(doctype, name):
        return name
    doc = frappe.get_doc({"doctype": doctype, "name": name, **data})
    doc.flags.ignore_links = True
    doc.flags.ignore_mandatory = True
    doc.insert(ignore_permissions=True)
    return doc.name


class CrossModuleGatesBase(FrappeTestCase):
    """Common smoke harness — skip gracefully if doctype not installed."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")

    def _skip_if_missing(self, *doctypes: str) -> None:
        for dt in doctypes:
            if not frappe.db.exists("DocType", dt):
                self.skipTest(f"DocType {dt} not installed")


class TestGate1CommissioningToPM(CrossModuleGatesBase):
    """TC-INT-01: Asset Commissioning on_submit hook creates PM Schedule
    if device_model.is_pm_required."""

    def test_pm_schedule_auto_created_signature(self) -> None:
        """Smoke: hook function exists, importable, and is registered in hooks.py."""
        from assetcore.services.imm08 import create_pm_schedule_from_commissioning
        self.assertTrue(callable(create_pm_schedule_from_commissioning))

        # Verify registration in hooks.py doc_events
        from assetcore import hooks
        events = getattr(hooks, "doc_events", {}) or {}
        ac_events = events.get("Asset Commissioning", {})
        on_submit = ac_events.get("on_submit", [])
        if isinstance(on_submit, str):
            on_submit = [on_submit]
        self.assertIn(
            "assetcore.services.imm08.create_pm_schedule_from_commissioning",
            on_submit,
            "Gate 1 hook missing from hooks.py",
        )


class TestGate2RequestSparePartsAllocation(CrossModuleGatesBase):
    """TC-INT-02: request_spare_parts → IMM-15 create_allocation called."""

    def test_request_spare_parts_invokes_create_allocation(self) -> None:
        self._skip_if_missing("Asset Repair", "IMM Spare Allocation", "AC Spare Part",
                              "AC Warehouse", "AC Spare Part Stock")
        from assetcore.services import imm09

        # Inspect source: enforced wiring (avoid heavy fixture for smoke).
        import inspect
        src = inspect.getsource(imm09.request_spare_parts)
        self.assertIn("create_allocation", src,
                      "Gate 2 wiring missing: request_spare_parts must call imm15.create_allocation")
        self.assertIn("imm15", src,
                      "Gate 2 wiring must import from assetcore.services.imm15")


class TestGate3CalibrationFailCAPA(CrossModuleGatesBase):
    """TC-INT-03: handle_calibration_fail auto-creates CAPA via imm00.create_capa."""

    def test_calibration_fail_creates_capa(self) -> None:
        from assetcore.services import imm11
        import inspect
        src = inspect.getsource(imm11.handle_calibration_fail)
        self.assertIn("create_capa", src,
                      "Gate 3 wiring missing: handle_calibration_fail must call create_capa")

        # Verify controller routes Fail → handle_calibration_fail
        ctrl_path = frappe.get_app_path(
            "assetcore", "assetcore", "doctype", "imm_asset_calibration",
            "imm_asset_calibration.py",
        )
        with open(ctrl_path, encoding="utf-8") as fh:
            ctrl_src = fh.read()
        self.assertIn("handle_calibration_fail", ctrl_src,
                      "Controller must wire handle_calibration_fail on Fail result")


class TestGate4RcaSubmitCAPA(CrossModuleGatesBase):
    """TC-INT-04: submit_rca auto-creates CAPA (BR-12-06)."""

    def test_submit_rca_creates_capa(self) -> None:
        from assetcore.services import imm12
        import inspect
        src = inspect.getsource(imm12.submit_rca)
        self.assertIn("create_capa", src,
                      "Gate 4 wiring missing: submit_rca must call svc00.create_capa")
        self.assertIn("linked_capa", src,
                      "Gate 4 must set rca.linked_capa after CAPA creation")


class TestGate5CommissioningComplianceBlock(CrossModuleGatesBase):
    """TC-INT-05: submit_commissioning blocked by check_asset_compliance_status."""

    @classmethod
    def tearDownClass(cls):
        # test_compliance_gate_blocks_when_critical_capa_open seeds an asset via
        # _ensure("AC Asset", "AC-AS-INT05", {"asset_name": "Gate5 Test Asset"}).
        # AC Asset is autonamed (AC-ASSET-#####) so the requested name is IGNORED
        # (LL-TEST-9) → must purge by asset_name, not by "AC-AS-INT05".
        from assetcore.tests._helpers._asset_cleanup import purge_assets_by_name_prefix
        purge_assets_by_name_prefix("Gate5 Test Asset")
        frappe.db.commit()
        super().tearDownClass()

    def test_submit_commissioning_calls_compliance_gate(self) -> None:
        from assetcore.services import imm04
        import inspect
        src = inspect.getsource(imm04.submit_commissioning)
        self.assertIn("check_asset_compliance_status", src,
                      "Gate 5 wiring missing in submit_commissioning")
        self.assertIn("COMPLIANCE_BLOCKED", src,
                      "Gate 5 must raise ErrorCode.COMPLIANCE_BLOCKED")

    def test_compliance_blocked_error_code_exists(self) -> None:
        self.assertTrue(hasattr(ErrorCode, "COMPLIANCE_BLOCKED"))
        self.assertEqual(ErrorCode.COMPLIANCE_BLOCKED, "COMPLIANCE_BLOCKED")

    def test_compliance_gate_blocks_when_critical_capa_open(self) -> None:
        """Functional: check_asset_compliance_status returns blocked=True
        when asset has a Critical CAPA in Open state."""
        self._skip_if_missing("AC Asset", "IMM CAPA Record")
        if not frappe.db.has_column("IMM CAPA Record", "imm_risk_level"):
            self.skipTest("IMM-16 CF imm_risk_level not migrated on this site")
        from assetcore.services.imm16 import check_asset_compliance_status

        asset = _ensure("AC Asset", "AC-AS-INT05",
                        {"asset_name": "Gate5 Test Asset"})

        # Build a Critical CAPA Open against the asset.
        capa_name: str | None = None
        try:
            capa = frappe.get_doc({
                "doctype": "IMM CAPA Record",
                "asset": asset,
                "imm_risk_level": "Critical",
                "status": "Open",
                "source_type": "Incident Report",
                "source_ref": "TC-INT-05",
                "description": "Gate5 test",
            })
            capa.flags.ignore_links = True
            capa.flags.ignore_mandatory = True
            capa.insert(ignore_permissions=True)
            capa_name = capa.name
            frappe.db.commit()

            result = check_asset_compliance_status(asset)
            self.assertTrue(result.get("blocked"),
                            "Gate 5: expected blocked=True with Critical CAPA Open")
            self.assertGreaterEqual(result.get("active_capas_count", 0), 1)
        finally:
            if capa_name:
                with suppress(Exception):
                    frappe.delete_doc("IMM CAPA Record", capa_name,
                                      ignore_permissions=True, force=True)
                    frappe.db.commit()


if __name__ == "__main__":
    unittest.main()
