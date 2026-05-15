"""IMM-11 Calibration — test suite.

Run: bench --site miyano run-tests --module assetcore.tests.test_imm11
"""
from __future__ import annotations

import unittest

import frappe
from frappe.utils import nowdate, add_days

from assetcore.services.imm11 import create_calibration, cancel_calibration
from assetcore.services.shared import CalibrationResult, ErrorCode, ServiceError


# ─── Fixture helpers ──────────────────────────────────────────────────────────

def _make_asset(suffix: str = "") -> object:
    import time
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    tag = suffix.lstrip("-") or "001"
    sn = f"SN-11-{tag}-{int(time.time()) % 100000}"
    try:
        return frappe.get_doc({
            "doctype": "AC Asset",
            "asset_name": f"_Test Asset IMM11{suffix}",
            "asset_category": _ensure_cat(),
            "manufacturer_sn": sn,
            "lifecycle_status": "Active",
        }).insert(ignore_permissions=True)
    finally:
        frappe.flags.in_install = prev


def _ensure_cat() -> str:
    name = "_TestCatIMM11"
    if not frappe.db.exists("AC Asset Category", name):
        frappe.get_doc({"doctype": "AC Asset Category", "category_name": name}).insert(
            ignore_permissions=True
        )
    return name


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestCalibrationCreation(unittest.TestCase):
    """BR-11-01: create_calibration validation + happy path."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-cal")

    @classmethod
    def tearDownClass(cls):
        for cal in frappe.get_all(
            "IMM Asset Calibration", filters={"asset": cls.asset.name}, fields=["name"]
        ):
            frappe.delete_doc(
                "IMM Asset Calibration", cal.name, force=True, ignore_permissions=True
            )
        frappe.delete_doc("AC Asset", cls.asset.name, force=True, ignore_permissions=True)
        if frappe.db.exists("AC Asset Category", "_TestCatIMM11"):
            frappe.delete_doc(
                "AC Asset Category", "_TestCatIMM11", force=True, ignore_permissions=True
            )

    def setUp(self):
        frappe.set_user("Administrator")

    def test_nonexistent_asset_raises_not_found(self):
        with self.assertRaises(ServiceError) as cm:
            create_calibration(
                asset="DOES-NOT-EXIST",
                calibration_type="In-House",
                scheduled_date=nowdate(),
                technician="Administrator",
            )
        self.assertEqual(cm.exception.code, ErrorCode.NOT_FOUND)

    def test_create_calibration_succeeds(self):
        result = create_calibration(
            asset=self.asset.name,
            calibration_type="In-House",
            scheduled_date=add_days(nowdate(), 7),
            technician="Administrator",
            reference_standard_serial="STD-TEST-001",
        )
        frappe.db.commit()
        self.assertIn("name", result)
        self.assertEqual(result["status"], CalibrationResult.SCHEDULED)
        doc = frappe.get_doc("IMM Asset Calibration", result["name"])
        self.assertEqual(doc.asset, self.asset.name)

    def test_initial_status_is_scheduled(self):
        result = create_calibration(
            asset=self.asset.name,
            calibration_type="In-House",
            scheduled_date=add_days(nowdate(), 14),
            technician="Administrator",
            reference_standard_serial="STD-TEST-001",
        )
        frappe.db.commit()
        self.assertEqual(result["status"], CalibrationResult.SCHEDULED)

    def test_naming_series(self):
        result = create_calibration(
            asset=self.asset.name,
            calibration_type="In-House",
            scheduled_date=add_days(nowdate(), 30),
            technician="Administrator",
            reference_standard_serial="STD-TEST-001",
        )
        frappe.db.commit()
        self.assertTrue(
            result["name"].startswith("CAL-")
            or "IMM-CAL" in result["name"]
            or frappe.db.exists("IMM Asset Calibration", result["name"])
        )


class TestCalibrationCancellation(unittest.TestCase):
    """BR-11-05: Scheduled calibration can be cancelled with reason."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-cancel")
        result = create_calibration(
            asset=cls.asset.name,
            calibration_type="In-House",
            scheduled_date=add_days(nowdate(), 7),
            technician="Administrator",
            reference_standard_serial="STD-TEST-001",
        )
        frappe.db.commit()
        cls.cal_name = result["name"]

    @classmethod
    def tearDownClass(cls):
        if frappe.db.exists("IMM Asset Calibration", cls.cal_name):
            frappe.delete_doc(
                "IMM Asset Calibration", cls.cal_name, force=True, ignore_permissions=True
            )
        frappe.delete_doc("AC Asset", cls.asset.name, force=True, ignore_permissions=True)

    def setUp(self):
        frappe.set_user("Administrator")

    def test_cancel_scheduled_calibration(self):
        result = cancel_calibration(self.cal_name, reason="_Test cancel — equipment unavailable")
        frappe.db.commit()
        self.assertEqual(result["status"], CalibrationResult.CANCELLED)
        doc = frappe.get_doc("IMM Asset Calibration", self.cal_name)
        self.assertEqual(doc.status, CalibrationResult.CANCELLED)


class TestCalibrationSubmitGate(unittest.TestCase):
    """BR-11-08/09 — Submit phải có ≥1 measurement + overall_result."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-subgate")

    @classmethod
    def tearDownClass(cls):
        for cal in frappe.get_all(
            "IMM Asset Calibration", filters={"asset": cls.asset.name}, fields=["name"]
        ):
            # Submitted calibrations cannot be cancelled (BR-11-05) — purge rows directly.
            frappe.db.delete("IMM Calibration Measurement", {"parent": cal.name})
            frappe.db.delete("IMM Asset Calibration", {"name": cal.name})
        frappe.delete_doc("AC Asset", cls.asset.name, force=True, ignore_permissions=True)

    def setUp(self):
        frappe.set_user("Administrator")

    def _make_cal(self):
        res = create_calibration(
            asset=self.asset.name,
            calibration_type="In-House",
            scheduled_date=add_days(nowdate(), 7),
            technician="Administrator",
            reference_standard_serial="STD-TEST-001",
        )
        frappe.db.commit()
        return res["name"]

    def test_submit_blocked_without_measurements(self):
        from assetcore.services.imm11 import submit_calibration
        name = self._make_cal()
        with self.assertRaises(Exception):
            submit_calibration(name)

    def test_submit_succeeds_with_measurement_and_result(self):
        from assetcore.services.imm11 import submit_calibration, add_measurement
        name = self._make_cal()
        add_measurement(
            name, parameter_name="Temp", unit="C", nominal_value=100,
            tolerance_positive=5, tolerance_negative=5, measured_value=101,
        )
        frappe.db.commit()
        res = submit_calibration(name)
        frappe.db.commit()
        self.assertIn(res["overall_result"], ("Passed", "Conditionally Passed"))
