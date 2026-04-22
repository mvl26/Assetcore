# Copyright (c) 2026, AssetCore Team
"""IMM-00 foundation test suite.

Run: bench --site miyano run-tests --app assetcore --module assetcore.tests.test_imm00
"""
import unittest
import frappe
from frappe.utils import nowdate, add_days


class TestACAssetCategory(unittest.TestCase):
    def setUp(self):
        self.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "_Test Category IMM00",
            "default_pm_interval_days": 90,
            "default_calibration_interval_days": 365,
        }).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.delete_doc("AC Asset Category", self.cat.name, force=True, ignore_permissions=True)

    def test_category_created(self):
        self.assertTrue(frappe.db.exists("AC Asset Category", self.cat.name))

    def test_category_fields(self):
        doc = frappe.get_doc("AC Asset Category", self.cat.name)
        self.assertEqual(doc.default_pm_interval_days, 90)
        self.assertEqual(doc.default_calibration_interval_days, 365)


class TestACDepartment(unittest.TestCase):
    def setUp(self):
        self.dept = frappe.get_doc({
            "doctype": "AC Department",
            "department_name": "_Test Dept IMM00",
        }).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.delete_doc("AC Department", self.dept.name, force=True, ignore_permissions=True)

    def test_department_created(self):
        self.assertTrue(frappe.db.exists("AC Department", self.dept.name))

    def test_naming_series(self):
        self.assertTrue(self.dept.name.startswith("AC-DEPT-"))


class TestACLocation(unittest.TestCase):
    def setUp(self):
        self.loc = frappe.get_doc({
            "doctype": "AC Location",
            "location_name": "_Test Location IMM00",
            "location_type": "Floor",
        }).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.delete_doc("AC Location", self.loc.name, force=True, ignore_permissions=True)

    def test_location_created(self):
        self.assertTrue(frappe.db.exists("AC Location", self.loc.name))

    def test_naming_series(self):
        self.assertTrue(self.loc.name.startswith("AC-LOC-"))


class TestACSupplier(unittest.TestCase):
    def setUp(self):
        self.sup = frappe.get_doc({
            "doctype": "AC Supplier",
            "supplier_name": "_Test Supplier IMM00",
            "supplier_type": "Manufacturer",
            "country": "Vietnam",
        }).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.delete_doc("AC Supplier", self.sup.name, force=True, ignore_permissions=True)

    def test_supplier_created(self):
        self.assertTrue(frappe.db.exists("AC Supplier", self.sup.name))

    def test_naming_series(self):
        self.assertTrue(self.sup.name.startswith("AC-SUP-"))


class TestIMMDeviceModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "_TestCatModel",
        }).insert(ignore_permissions=True)

    @classmethod
    def tearDownClass(cls):
        frappe.delete_doc("AC Asset Category", cls._cat.name, force=True, ignore_permissions=True)

    def setUp(self):
        self.model = frappe.get_doc({
            "doctype": "IMM Device Model",
            "model_name": "_Test Model IMM00",
            "model_number": "MDL-TEST-001",
            "manufacturer": "TestMfg",
            "medical_device_class": "Class II",
            "asset_category": self._cat.name,
        }).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.delete_doc("IMM Device Model", self.model.name, force=True, ignore_permissions=True)

    def test_model_created(self):
        self.assertTrue(frappe.db.exists("IMM Device Model", self.model.name))


class TestIMSLAPolicy(unittest.TestCase):
    def test_sla_policies_loaded(self):
        """Fixture SLA policies must exist after bench migrate."""
        count = frappe.db.count("IMM SLA Policy", {"is_active": 1})
        self.assertGreaterEqual(count, 6, "Expected at least 6 active SLA policies from fixtures")

    def test_resolve_default_policy(self):
        from assetcore.services.imm00 import get_sla_policy
        policy = get_sla_policy("P1 Critical", "Critical")
        self.assertIsNotNone(policy)
        self.assertEqual(policy.get("response_time_minutes"), 15)

    def test_resolve_fallback_to_default(self):
        from assetcore.services.imm00 import get_sla_policy
        # Non-existent combo → fallback to is_default for that priority
        policy = get_sla_policy("P3", "Critical")
        self.assertIsNotNone(policy)


class TestACAsset(unittest.TestCase):
    """Full asset lifecycle: create → transition → validate."""

    @classmethod
    def setUpClass(cls):
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "_TestCatAsset",
            "default_pm_interval_days": 30,
        }).insert(ignore_permissions=True)

        cls.dept = frappe.get_doc({
            "doctype": "AC Department",
            "department_name": "_TestDeptAsset",
        }).insert(ignore_permissions=True)

        cls.loc = frappe.get_doc({
            "doctype": "AC Location",
            "location_name": "_TestLocAsset",
            "location_type": "Room",
        }).insert(ignore_permissions=True)

        cls.sup = frappe.get_doc({
            "doctype": "AC Supplier",
            "supplier_name": "_TestSupAsset",
            "supplier_type": "Distributor",
        }).insert(ignore_permissions=True)

    @classmethod
    def tearDownClass(cls):
        for dt, name in [
            ("AC Asset Category", cls.cat.name),
            ("AC Department", cls.dept.name),
            ("AC Location", cls.loc.name),
            ("AC Supplier", cls.sup.name),
        ]:
            frappe.delete_doc(dt, name, force=True, ignore_permissions=True)

    def _make_asset(self, suffix=""):
        return frappe.get_doc({
            "doctype": "AC Asset",
            "asset_name": f"_Test Asset IMM00{suffix}",
            "asset_category": self.cat.name,
            "department": self.dept.name,
            "location": self.loc.name,
            "supplier": self.sup.name,
            "purchase_date": nowdate(),
            "gross_purchase_amount": 50000000,
            "manufacturer_sn": f"SN-TEST-{suffix or '001'}",
            "lifecycle_status": "Commissioned",
            "is_pm_required": 1,
            "pm_interval_days": 30,
        }).insert(ignore_permissions=True)

    def test_asset_created_with_naming_series(self):
        asset = self._make_asset("-create")
        try:
            self.assertTrue(asset.name.startswith("AC-ASSET-"))
            self.assertEqual(asset.lifecycle_status, "Commissioned")
        finally:
            frappe.delete_doc("AC Asset", asset.name, force=True, ignore_permissions=True)

    def test_transition_status_commissioned_to_active(self):
        from assetcore.services.imm00 import transition_asset_status
        asset = self._make_asset("-trans")
        try:
            transition_asset_status(asset.name, "Active", actor="Administrator", reason="Smoke test")
            frappe.db.commit()
            asset.reload()
            self.assertEqual(asset.lifecycle_status, "Active")
        finally:
            frappe.delete_doc("AC Asset", asset.name, force=True, ignore_permissions=True)

    def test_transition_creates_lifecycle_event(self):
        from assetcore.services.imm00 import transition_asset_status
        asset = self._make_asset("-event")
        try:
            before = frappe.db.count("Asset Lifecycle Event", {"asset": asset.name})
            transition_asset_status(asset.name, "Active", actor="Administrator")
            frappe.db.commit()
            after = frappe.db.count("Asset Lifecycle Event", {"asset": asset.name})
            self.assertGreater(after, before)
        finally:
            frappe.delete_doc("AC Asset", asset.name, force=True, ignore_permissions=True)

    def test_cannot_operate_decommissioned_asset(self):
        from assetcore.services.imm00 import transition_asset_status, validate_asset_for_operations
        asset = self._make_asset("-decom")
        try:
            transition_asset_status(asset.name, "Decommissioned", actor="Administrator", reason="EOL")
            frappe.db.commit()
            with self.assertRaises(frappe.ValidationError):
                validate_asset_for_operations(asset.name)
        finally:
            frappe.delete_doc("AC Asset", asset.name, force=True, ignore_permissions=True)

    def test_decommission_suspends_pm_schedule(self):
        from assetcore.services.imm00 import transition_asset_status
        asset = self._make_asset("-pm")
        try:
            transition_asset_status(asset.name, "Decommissioned", actor="Administrator")
            frappe.db.commit()
            asset.reload()
            self.assertEqual(asset.is_pm_required, 0)
        finally:
            frappe.delete_doc("AC Asset", asset.name, force=True, ignore_permissions=True)


class TestIMMCAPARecord(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "_TestCatCAPA",
        }).insert(ignore_permissions=True)
        cls.asset = frappe.get_doc({
            "doctype": "AC Asset",
            "asset_name": "_Test Asset CAPA",
            "asset_category": cls.cat.name,
            "manufacturer_sn": "SN-CAPA-001",
            "lifecycle_status": "Active",
        }).insert(ignore_permissions=True)

    @classmethod
    def tearDownClass(cls):
        frappe.delete_doc("AC Asset", cls.asset.name, force=True, ignore_permissions=True)
        frappe.delete_doc("AC Asset Category", cls.cat.name, force=True, ignore_permissions=True)

    def test_create_capa(self):
        from assetcore.services.imm00 import create_capa
        name = create_capa(
            asset=self.asset.name,
            source_type="Nonconformance",
            source_ref="",
            severity="Minor",
            description="Root cause test — action taken — prevention plan",
            responsible="Administrator",
            due_days=30,
        )
        frappe.db.commit()
        self.assertTrue(frappe.db.exists("IMM CAPA Record", name))
        frappe.delete_doc("IMM CAPA Record", name, force=True, ignore_permissions=True)

    def test_close_capa(self):
        from assetcore.services.imm00 import create_capa, close_capa
        name = create_capa(
            asset=self.asset.name,
            source_type="Nonconformance",
            source_ref="",
            severity="Minor",
            description="CAPA close test",
            responsible="Administrator",
            due_days=7,
        )
        frappe.db.commit()
        close_capa(
            capa_name=name,
            root_cause="Root cause identified",
            corrective_action="Action taken",
            preventive_action="Prevention plan",
        )
        frappe.db.commit()
        doc = frappe.get_doc("IMM CAPA Record", name)
        self.assertEqual(doc.status, "Closed")
        doc.cancel()
        frappe.delete_doc("IMM CAPA Record", name, force=True, ignore_permissions=True)


class TestIMMauditTrail(unittest.TestCase):
    """Audit trail immutability and hash chain."""

    @classmethod
    def setUpClass(cls):
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "_TestCatAudit",
        }).insert(ignore_permissions=True)
        cls.asset = frappe.get_doc({
            "doctype": "AC Asset",
            "asset_name": "_Test Asset Audit",
            "asset_category": cls.cat.name,
            "manufacturer_sn": "SN-AUDIT-001",
            "lifecycle_status": "Commissioned",
        }).insert(ignore_permissions=True)

    @classmethod
    def tearDownClass(cls):
        frappe.delete_doc("AC Asset", cls.asset.name, force=True, ignore_permissions=True)
        frappe.delete_doc("AC Asset Category", cls.cat.name, force=True, ignore_permissions=True)

    def test_audit_trail_created_on_transition(self):
        from assetcore.services.imm00 import transition_asset_status
        before = frappe.db.count("IMM Audit Trail", {"asset": self.asset.name})
        transition_asset_status(self.asset.name, "Active", actor="Administrator", reason="Audit test")
        frappe.db.commit()
        after = frappe.db.count("IMM Audit Trail", {"asset": self.asset.name})
        self.assertGreater(after, before)

    def test_audit_trail_cannot_be_deleted(self):
        entries = frappe.get_list("IMM Audit Trail", filters={"asset": self.asset.name}, fields=["name"])
        if not entries:
            self.skipTest("No audit trail entries to test deletion block")
        with self.assertRaises(frappe.ValidationError):
            frappe.delete_doc("IMM Audit Trail", entries[0]["name"], ignore_permissions=True)

    def test_verify_chain_valid(self):
        from assetcore.services.imm00 import verify_audit_chain
        result = verify_audit_chain(self.asset.name)
        self.assertTrue(result.get("valid"), f"Chain invalid: {result}")


class TestIncidentReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "_TestCatIR",
        }).insert(ignore_permissions=True)
        cls.asset = frappe.get_doc({
            "doctype": "AC Asset",
            "asset_name": "_Test Asset IR",
            "asset_category": cls.cat.name,
            "manufacturer_sn": "SN-IR-001",
            "lifecycle_status": "Active",
        }).insert(ignore_permissions=True)

    @classmethod
    def tearDownClass(cls):
        frappe.delete_doc("AC Asset", cls.asset.name, force=True, ignore_permissions=True)
        frappe.delete_doc("AC Asset Category", cls.cat.name, force=True, ignore_permissions=True)

    def test_create_incident(self):
        ir = frappe.get_doc({
            "doctype": "Incident Report",
            "asset": self.asset.name,
            "severity": "Medium",
            "incident_title": "_Test Incident",
            "incident_datetime": nowdate(),
            "description": "Test incident description",
            "patient_affected": 0,
        }).insert(ignore_permissions=True)
        self.assertTrue(ir.name.startswith("IR-"))
        frappe.delete_doc("Incident Report", ir.name, force=True, ignore_permissions=True)

    def test_patient_impact_required_when_patient_affected(self):
        doc = frappe.new_doc("Incident Report")
        doc.update({
            "asset": self.asset.name,
            "severity": "Critical",
            "incident_title": "_Test Incident Patient",
            "incident_datetime": nowdate(),
            "description": "Critical with patient",
            "patient_affected": 1,
            "patient_impact": "",  # missing — should fail
        })
        with self.assertRaises(frappe.ValidationError):
            doc.insert(ignore_permissions=True)


def run_all():
    """Convenience runner for bench console."""
    suite = unittest.TestLoader().loadTestsFromModule(__import__(__name__))
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
