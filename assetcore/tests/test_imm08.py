"""IMM-08 Preventive Maintenance — test suite.

Run: bench --site miyano run-tests --module assetcore.tests.test_imm08
"""
from __future__ import annotations

import unittest

import frappe
from frappe.utils import add_days, nowdate

from assetcore.services.imm08 import (
    create_adhoc_work_order,
    create_schedule,
    create_template,
    set_schedule_status,
)
from assetcore.services.shared import ErrorCode, ServiceError
from assetcore.services.imm08 import PMScheduleStatus


# ─── Fixture helpers ──────────────────────────────────────────────────────────

def _ensure_cat(name: str = "_TestCatIMM08") -> str:
    if not frappe.db.exists("AC Asset Category", name):
        frappe.get_doc({"doctype": "AC Asset Category", "category_name": name}).insert(
            ignore_permissions=True
        )
    return name


def _make_asset(suffix: str = "") -> object:
    import time
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    tag = suffix.lstrip("-") or "001"
    sn = f"SN-08-{tag}-{int(time.time()) % 100000}"
    try:
        return frappe.get_doc({
            "doctype": "AC Asset",
            "asset_name": f"_Test Asset IMM08{suffix}",
            "asset_category": _ensure_cat(),
            "manufacturer_sn": sn,
            "lifecycle_status": "Active",
            "is_pm_required": 1,
            "pm_interval_days": 90,
        }).insert(ignore_permissions=True)
    finally:
        frappe.flags.in_install = prev


def _make_template(cat: str, pm_type: str = "Quarterly") -> dict:
    return create_template({
        "template_name": f"_Test Template {pm_type}",
        "asset_category": cat,
        "pm_type": pm_type,
        "checklist_items": [
            {"description": "_Test check item 1", "measurement_type": "Pass/Fail", "is_critical": 1},
            {"description": "_Test check item 2", "measurement_type": "Pass/Fail"},
        ],
    })


def _make_schedule(asset_ref: str, template_name: str) -> dict:
    return create_schedule({
        "asset_ref": asset_ref,
        "pm_type": "Quarterly",
        "pm_interval_days": 90,
        "checklist_template": template_name,
        "status": "Active",
    })


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestPMChecklistTemplate(unittest.TestCase):
    """BR-08-T1: Template creation + validation."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = _ensure_cat()

    @classmethod
    def tearDownClass(cls):
        for t in frappe.get_all(
            "PM Checklist Template",
            filters={"template_name": ("like", "_Test Template%")},
            fields=["name"],
        ):
            frappe.delete_doc("PM Checklist Template", t.name, force=True, ignore_permissions=True)
        if frappe.db.exists("AC Asset Category", "_TestCatIMM08"):
            frappe.delete_doc(
                "AC Asset Category", "_TestCatIMM08", force=True, ignore_permissions=True
            )

    def setUp(self):
        frappe.set_user("Administrator")

    def test_missing_required_fields_raises_validation(self):
        with self.assertRaises(ServiceError) as cm:
            create_template({"pm_type": "Preventive"})
        self.assertEqual(cm.exception.code, ErrorCode.VALIDATION)

    def test_create_template_succeeds(self):
        result = _make_template(self.cat)
        self.assertIn("name", result)
        self.assertEqual(result["items_count"], 2)

    def test_template_naming_series(self):
        result = _make_template(self.cat, pm_type="Annual")
        doc = frappe.get_doc("PM Checklist Template", result["name"])
        self.assertTrue(frappe.db.exists("PM Checklist Template", result["name"]))
        self.assertEqual(doc.pm_type, "Annual")


class TestPMSchedule(unittest.TestCase):
    """BR-08-S1: Schedule creation + status transitions."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = _ensure_cat()
        cls.asset = _make_asset("-sched")
        tmpl = _make_template(cls.cat)
        cls.template_name = tmpl["name"]
        cls.sched = _make_schedule(cls.asset.name, cls.template_name)

    @classmethod
    def tearDownClass(cls):
        for s in frappe.get_all(
            "PM Schedule", filters={"asset_ref": cls.asset.name}, fields=["name"]
        ):
            frappe.delete_doc("PM Schedule", s.name, force=True, ignore_permissions=True)
        frappe.delete_doc(
            "PM Checklist Template", cls.template_name, force=True, ignore_permissions=True
        )
        frappe.delete_doc("AC Asset", cls.asset.name, force=True, ignore_permissions=True)

    def setUp(self):
        frappe.set_user("Administrator")
        set_schedule_status(self.sched["name"], "Active")

    def test_missing_required_raises_validation(self):
        with self.assertRaises(ServiceError) as cm:
            create_schedule({"asset_ref": self.asset.name})
        self.assertEqual(cm.exception.code, ErrorCode.VALIDATION)

    def test_create_schedule_succeeds(self):
        self.assertIn("name", self.sched)
        self.assertEqual(self.sched["status"], "Active")

    def test_set_schedule_paused(self):
        result = set_schedule_status(self.sched["name"], "Paused")
        self.assertEqual(result["status"], "Paused")

    def test_invalid_status_raises_validation(self):
        with self.assertRaises(ServiceError) as cm:
            set_schedule_status(self.sched["name"], "InvalidStatus")
        self.assertEqual(cm.exception.code, ErrorCode.VALIDATION)


class TestPMWorkOrder(unittest.TestCase):
    """BR-08-W1: Adhoc PM WO creation."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = _ensure_cat()
        cls.asset = _make_asset("-wo")
        tmpl = _make_template(cls.cat)
        cls.template_name = tmpl["name"]
        sched = _make_schedule(cls.asset.name, cls.template_name)
        cls.schedule_name = sched["name"]

    @classmethod
    def tearDownClass(cls):
        for wo in frappe.get_all(
            "PM Work Order", filters={"asset_ref": cls.asset.name}, fields=["name"]
        ):
            frappe.delete_doc("PM Work Order", wo.name, force=True, ignore_permissions=True)
        frappe.delete_doc("PM Schedule", cls.schedule_name, force=True, ignore_permissions=True)
        frappe.delete_doc(
            "PM Checklist Template", cls.template_name, force=True, ignore_permissions=True
        )
        frappe.delete_doc("AC Asset", cls.asset.name, force=True, ignore_permissions=True)

    def setUp(self):
        frappe.set_user("Administrator")

    def test_missing_required_raises_validation(self):
        with self.assertRaises(ServiceError) as cm:
            create_adhoc_work_order({"asset_ref": self.asset.name})
        self.assertEqual(cm.exception.code, ErrorCode.VALIDATION)

    def test_nonexistent_schedule_raises_not_found(self):
        with self.assertRaises(ServiceError) as cm:
            create_adhoc_work_order({
                "asset_ref": self.asset.name,
                "pm_schedule": "DOES-NOT-EXIST",
                "due_date": add_days(nowdate(), 7),
            })
        self.assertEqual(cm.exception.code, ErrorCode.NOT_FOUND)

    def test_asset_mismatch_raises_validation(self):
        other_asset = _make_asset("-other")
        try:
            with self.assertRaises(ServiceError) as cm:
                create_adhoc_work_order({
                    "asset_ref": other_asset.name,
                    "pm_schedule": self.schedule_name,
                    "due_date": add_days(nowdate(), 7),
                })
            self.assertEqual(cm.exception.code, ErrorCode.VALIDATION)
        finally:
            frappe.delete_doc("AC Asset", other_asset.name, force=True, ignore_permissions=True)

    def test_create_pm_work_order_succeeds(self):
        result = create_adhoc_work_order({
            "asset_ref": self.asset.name,
            "pm_schedule": self.schedule_name,
            "due_date": add_days(nowdate(), 7),
            "assigned_to": "Administrator",
        })
        frappe.db.commit()
        self.assertIn("name", result)
        self.assertEqual(result["status"], "Open")
        self.assertGreaterEqual(result["checklist_items_count"], 0)

    def test_paused_schedule_blocks_wo_creation(self):
        set_schedule_status(self.schedule_name, "Paused")
        try:
            with self.assertRaises(ServiceError) as cm:
                create_adhoc_work_order({
                    "asset_ref": self.asset.name,
                    "pm_schedule": self.schedule_name,
                    "due_date": add_days(nowdate(), 7),
                })
            self.assertEqual(cm.exception.code, ErrorCode.BAD_STATE)
        finally:
            set_schedule_status(self.schedule_name, "Active")
