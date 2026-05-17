"""IMM-09 Corrective Maintenance — test suite.

Run: bench --site miyano run-tests --module assetcore.tests.test_imm09
"""
from __future__ import annotations

import unittest

import frappe
from frappe.utils import nowdate

from assetcore.services.imm09 import create_work_order, get_sla_target
from assetcore.services.shared import ErrorCode, ServiceError


# ─── Shared fixture helpers ───────────────────────────────────────────────────

def _make_asset(suffix: str = "") -> object:
    import time
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    tag = suffix.lstrip("-") or "001"
    sn = f"SN-09-{tag}-{int(time.time()) % 100000}"
    try:
        return frappe.get_doc({
            "doctype": "AC Asset",
            "asset_name": f"_Test Asset IMM09{suffix}",
            "asset_category": _ensure_cat(),
            "manufacturer_sn": sn,
            "lifecycle_status": "Active",
        }).insert(ignore_permissions=True)
    finally:
        frappe.flags.in_install = prev


def _ensure_cat() -> str:
    name = "_TestCatIMM09"
    if not frappe.db.exists("AC Asset Category", name):
        frappe.get_doc({"doctype": "AC Asset Category", "category_name": name}).insert(
            ignore_permissions=True
        )
    return name


def _make_incident(asset: str) -> str:
    doc = frappe.get_doc({
        "doctype": "Incident Report",
        "asset": asset,
        "incident_type": "Malfunction",
        "severity": "Medium",
        "description": "_Test incident for IMM09 repair WO",
        "reported_by": "Administrator",
        "status": "Open",
    }).insert(ignore_permissions=True)
    return doc.name


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestSlaMatrix(unittest.TestCase):
    """BR-09-05: SLA target derives from risk class × priority."""

    def test_class_iii_emergency_is_4h(self):
        self.assertEqual(get_sla_target("Class III", "Emergency"), 4.0)

    def test_class_ii_urgent_is_48h(self):
        self.assertEqual(get_sla_target("Class II", "Urgent"), 48.0)

    def test_class_i_normal_is_480h(self):
        self.assertEqual(get_sla_target("Class I", "Normal"), 480.0)

    def test_unknown_combo_falls_back_to_default(self):
        self.assertEqual(get_sla_target("Unknown Class", "Unknown"), 480.0)


class TestRepairWOCreation(unittest.TestCase):
    """BR-09-01/02: create_work_order validation + happy path."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-create")
        cls.ir = _make_incident(cls.asset.name)

    @classmethod
    def tearDownClass(cls):
        for wo in frappe.get_all(
            "Asset Repair",
            filters={"asset_ref": cls.asset.name},
            fields=["name", "docstatus"],
        ):
            doc = frappe.get_doc("Asset Repair", wo.name)
            if doc.docstatus == 1:
                doc.cancel()
            frappe.delete_doc("Asset Repair", wo.name, force=True, ignore_permissions=True)
        if frappe.db.exists("Incident Report", cls.ir):
            frappe.delete_doc("Incident Report", cls.ir, force=True, ignore_permissions=True)
        frappe.delete_doc("AC Asset", cls.asset.name, force=True, ignore_permissions=True)
        if frappe.db.exists("AC Asset Category", "_TestCatIMM09"):
            frappe.delete_doc(
                "AC Asset Category", "_TestCatIMM09", force=True, ignore_permissions=True
            )

    def setUp(self):
        frappe.set_user("Administrator")
        # Ensure no open WO left from a previous sub-test
        for wo in frappe.get_all(
            "Asset Repair",
            filters={"asset_ref": self.asset.name, "docstatus": ["!=", 2]},
            fields=["name"],
        ):
            frappe.db.set_value("Asset Repair", wo.name, "status", "Completed")
            frappe.db.set_value("Asset Repair", wo.name, "docstatus", 1)

    def test_standalone_create_succeeds(self):
        """Slide 24b: standalone repair WO (no incident/PM) is allowed."""
        result = create_work_order(
            asset_ref=self.asset.name,
            repair_type="Corrective",
            priority="Normal",
            failure_description="Standalone repair — no linked source",
        )
        self.assertIn("name", result)
        doc = frappe.get_doc("Asset Repair", result["name"])
        self.assertFalse(doc.incident_report)
        self.assertFalse(doc.source_pm_wo)
        frappe.db.commit()

    def test_requested_by_is_session_user(self):
        """Slide 24a/26: requested_by auto = session user."""
        frappe.set_user("Administrator")
        result = create_work_order(
            asset_ref=self.asset.name,
            repair_type="Corrective",
            priority="Normal",
            failure_description="Check requested_by auto-set",
        )
        doc = frappe.get_doc("Asset Repair", result["name"])
        self.assertEqual(doc.requested_by, "Administrator")
        frappe.db.commit()

    def test_failure_description_persisted(self):
        """Slide 24a: failure_description persisted on the doc."""
        desc = "Persisted failure description for assertion"
        result = create_work_order(
            asset_ref=self.asset.name,
            repair_type="Corrective",
            priority="Normal",
            failure_description=desc,
        )
        doc = frappe.get_doc("Asset Repair", result["name"])
        self.assertEqual(doc.failure_description, desc)
        frappe.db.commit()

    def test_nonexistent_asset_raises_not_found(self):
        with self.assertRaises(ServiceError) as cm:
            create_work_order(
                asset_ref="DOES-NOT-EXIST",
                repair_type="Corrective",
                priority="Normal",
                failure_description="Test failure",
                incident_report="IR-DUMMY",
            )
        self.assertEqual(cm.exception.code, ErrorCode.NOT_FOUND)

    def test_create_with_incident_report_succeeds(self):
        result = create_work_order(
            asset_ref=self.asset.name,
            repair_type="Corrective",
            priority="Normal",
            failure_description="_Test failure description — at least 10 chars",
            incident_report=self.ir,
        )
        self.assertIn("name", result)
        self.assertTrue(result["name"].startswith("WO-CM-") or result["name"].startswith("CM-"))
        frappe.db.commit()

    def test_sla_is_set_on_wo(self):
        result = create_work_order(
            asset_ref=self.asset.name,
            repair_type="Corrective",
            priority="Normal",
            failure_description="_Test SLA check — enough chars here",
            incident_report=self.ir,
        )
        doc = frappe.get_doc("Asset Repair", result["name"])
        self.assertIsNotNone(doc.sla_target_hours)
        self.assertGreater(float(doc.sla_target_hours), 0)
        frappe.db.commit()

    def test_duplicate_open_wo_raises_conflict(self):
        create_work_order(
            asset_ref=self.asset.name,
            repair_type="Corrective",
            priority="Normal",
            failure_description="_Test duplicate WO block — at least 10 chars",
            incident_report=self.ir,
        )
        frappe.db.commit()
        with self.assertRaises(ServiceError) as cm:
            create_work_order(
                asset_ref=self.asset.name,
                repair_type="Corrective",
                priority="Normal",
                failure_description="_Test duplicate WO block — second attempt",
                incident_report=self.ir,
            )
        self.assertEqual(cm.exception.code, ErrorCode.CONFLICT)
