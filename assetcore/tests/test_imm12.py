"""IMM-12 Incident Report — test suite.

Run: bench --site miyano run-tests --module assetcore.tests.test_imm12
"""
from __future__ import annotations

import unittest

import frappe

from assetcore.services.imm12 import (
    report_incident,
    acknowledge_incident,
    resolve_incident,
    close_incident,
    cancel_incident,
)
from assetcore.services.shared import ServiceError, ErrorCode


# ─── Fixture helpers ──────────────────────────────────────────────────────────

def _make_asset(suffix: str = "") -> object:
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    try:
        cat = _ensure_cat()
        return frappe.get_doc({
            "doctype": "AC Asset",
            "asset_name": f"_Test Asset IMM12{suffix}",
            "asset_category": cat,
            "manufacturer_sn": f"SN-IMM12-{suffix or '001'}",
            "lifecycle_status": "Active",
        }).insert(ignore_permissions=True)
    finally:
        frappe.flags.in_install = prev


def _ensure_cat() -> str:
    name = "_TestCatIMM12"
    if not frappe.db.exists("AC Asset Category", name):
        frappe.get_doc({"doctype": "AC Asset Category", "category_name": name}).insert(
            ignore_permissions=True
        )
    return name


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestIncidentCreation(unittest.TestCase):
    """BR-12-01/02: Validation + happy path for report_incident."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-ir")

    @classmethod
    def tearDownClass(cls):
        for ir in frappe.get_all(
            "Incident Report", filters={"asset": cls.asset.name}, fields=["name"]
        ):
            frappe.delete_doc("Incident Report", ir.name, force=True, ignore_permissions=True)
        frappe.delete_doc("AC Asset", cls.asset.name, force=True, ignore_permissions=True)
        if frappe.db.exists("AC Asset Category", "_TestCatIMM12"):
            frappe.delete_doc(
                "AC Asset Category", "_TestCatIMM12", force=True, ignore_permissions=True
            )

    def setUp(self):
        frappe.set_user("Administrator")

    def test_nonexistent_asset_raises_error(self):
        with self.assertRaises(Exception):
            report_incident(
                asset="DOES-NOT-EXIST",
                incident_type="Malfunction",
                severity="Low",
                description="_Test incident with nonexistent asset",
            )

    def test_critical_without_clinical_impact_raises_error(self):
        with self.assertRaises(Exception):
            report_incident(
                asset=self.asset.name,
                incident_type="Malfunction",
                severity="Critical",
                description="_Test critical incident without clinical_impact",
                clinical_impact="",
            )

    def test_create_medium_severity_incident(self):
        result = report_incident(
            asset=self.asset.name,
            incident_type="Malfunction",
            severity="Medium",
            description="_Test incident creation IMM-12 happy path",
        )
        frappe.db.commit()
        self.assertIn("name", result)
        doc = frappe.get_doc("Incident Report", result["name"])
        self.assertEqual(doc.status, "Open")
        self.assertEqual(doc.severity, "Medium")

    def test_create_critical_with_clinical_impact_succeeds(self):
        result = report_incident(
            asset=self.asset.name,
            incident_type="Safety Event",
            severity="Critical",
            description="_Test critical incident with clinical impact",
            clinical_impact="Patient monitoring interrupted",
        )
        frappe.db.commit()
        self.assertIn("name", result)
        doc = frappe.get_doc("Incident Report", result["name"])
        self.assertEqual(doc.severity, "Critical")


class TestIncidentWorkflow(unittest.TestCase):
    """BR-12-03: Full workflow Open → Under Investigation → Resolved → Closed in one test."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-wf")

    @classmethod
    def tearDownClass(cls):
        for ir in frappe.get_all(
            "Incident Report", filters={"asset": cls.asset.name}, fields=["name"]
        ):
            frappe.delete_doc("Incident Report", ir.name, force=True, ignore_permissions=True)
        frappe.delete_doc("AC Asset", cls.asset.name, force=True, ignore_permissions=True)

    def setUp(self):
        frappe.set_user("Administrator")

    def test_full_workflow_open_to_closed(self):
        result = report_incident(
            asset=self.asset.name,
            incident_type="Malfunction",
            severity="Low",
            description="_Test workflow incident — enough chars for description",
        )
        frappe.db.commit()
        ir_name = result["name"]

        doc = frappe.get_doc("Incident Report", ir_name)
        self.assertEqual(doc.status, "Open")

        acknowledge_incident(ir_name, notes="_Test acknowledge")
        frappe.db.commit()
        doc.reload()
        self.assertEqual(doc.status, "In Progress")

        resolve_incident(
            ir_name,
            resolution_notes="_Test resolution notes",
            root_cause="Component failure",
        )
        frappe.db.commit()
        doc.reload()
        self.assertEqual(doc.status, "Resolved")

        close_incident(ir_name, verification_notes="_Test verified closed")
        frappe.db.commit()
        doc.reload()
        self.assertEqual(doc.status, "Closed")


class TestIncidentCancellation(unittest.TestCase):
    """BR-12-04: Open incident can be cancelled."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-cancel")
        result = report_incident(
            asset=cls.asset.name,
            incident_type="Malfunction",
            severity="Low",
            description="_Test cancel flow — incident description here",
        )
        frappe.db.commit()
        cls.ir_name = result["name"]

    @classmethod
    def tearDownClass(cls):
        if frappe.db.exists("Incident Report", cls.ir_name):
            frappe.delete_doc(
                "Incident Report", cls.ir_name, force=True, ignore_permissions=True
            )
        frappe.delete_doc("AC Asset", cls.asset.name, force=True, ignore_permissions=True)

    def test_cancel_from_open(self):
        cancel_incident(self.ir_name, reason="_Test cancel reason")
        frappe.db.commit()
        doc = frappe.get_doc("Incident Report", self.ir_name)
        self.assertEqual(doc.status, "Cancelled")
