"""IMM-00 list endpoints — server-side filter + pagination guards.

Chống tái phát bug "lọc CLIENT-SIDE trên trang bị cắt" (FirmwareCr / DocumentRequest /
PmSchedule list): param lọc FE gửi PHẢI áp SERVER-SIDE (narrow cả `total`), KHÔNG bị
Frappe get_newargs nuốt câm và KHÔNG chỉ lọc trang đầu. Cùng lớp bug list_transfers
thiếu transfer_type.

Run: bench --site miyano run-tests --module assetcore.tests.imm00.test_imm00_list_filters
"""
from __future__ import annotations

import time
import unittest

import frappe
from frappe.utils import nowdate

from assetcore.api.imm00 import (
    list_document_requests,
    list_firmware_crs,
    list_pm_schedules,
)
from assetcore.services.imm08 import create_schedule, create_template
from assetcore.tests._helpers._asset_cleanup import purge_asset
from frappe.tests.utils import FrappeTestCase

_CAT = "_TestCatListFilter"


def _ensure_cat() -> str:
    existing = frappe.db.get_value("AC Asset Category", {"category_name": _CAT}, "name")
    if existing:
        return existing
    return frappe.get_doc(
        {"doctype": "AC Asset Category", "category_name": _CAT}
    ).insert(ignore_permissions=True).name


def _make_asset(name: str) -> object:
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    try:
        return frappe.get_doc({
            "doctype": "AC Asset",
            "asset_name": name,
            "asset_category": _ensure_cat(),
            "manufacturer_sn": f"SN-LF-{int(time.time() * 1000) % 10_000_000}",
            "lifecycle_status": "Active",
            "is_pm_required": 1,
            "pm_interval_days": 90,
        }).insert(ignore_permissions=True)
    finally:
        frappe.flags.in_install = prev


def _cleanup_cat():
    cat = frappe.db.get_value("AC Asset Category", {"category_name": _CAT}, "name")
    if cat and not frappe.db.exists("AC Asset", {"asset_category": cat}):
        frappe.delete_doc("AC Asset Category", cat, force=True, ignore_permissions=True)


class TestListPmScheduleFilters(FrappeTestCase):
    """pm_type + search áp server-side; total phản ánh tập đã lọc (không phải trang)."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = _ensure_cat()
        cls.asset = _make_asset("_Test Asset ListFilter PM")
        for pm, interval in (("Quarterly", 90), ("Annual", 365)):
            det = f"PMCT-{cls.cat}-{pm}"
            if not frappe.db.exists("PM Checklist Template", det):
                create_template({
                    "template_name": f"_Test Tpl {pm}",
                    "asset_category": cls.cat,
                    "pm_type": pm,
                    "checklist_items": [
                        {"description": "chk", "measurement_type": "Pass/Fail", "is_critical": 1},
                    ],
                })
            create_schedule({
                "asset_ref": cls.asset.name,
                "pm_type": pm,
                "pm_interval_days": interval,
                "checklist_template": det,
                "status": "Active",
            })
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for sc in frappe.get_all("PM Schedule", filters={"asset_ref": cls.asset.name}, pluck="name"):
            frappe.delete_doc("PM Schedule", sc, force=True, ignore_permissions=True)
        for pm in ("Quarterly", "Annual"):
            det = f"PMCT-{cls.cat}-{pm}"
            if frappe.db.exists("PM Checklist Template", det):
                frappe.delete_doc("PM Checklist Template", det, force=True, ignore_permissions=True)
        purge_asset(cls.asset.name)
        _cleanup_cat()
        frappe.db.commit()

    def test_pm_type_filter_narrows_server_side(self):
        env = list_pm_schedules(asset=self.asset.name, pm_type="Annual", page_size=50)
        self.assertTrue(env["success"])
        data = env["data"]
        self.assertEqual(data["total"], 1, "pm_type='Annual' phải loại lịch Quarterly")
        self.assertTrue(all(r["pm_type"] == "Annual" for r in data["items"]))

    def test_pm_search_narrows_server_side(self):
        # search khớp mã lịch + checklist_template chứa 'Quarterly' → chỉ 1 lịch
        env = list_pm_schedules(asset=self.asset.name, search="Quarterly", page_size=50)
        data = env["data"]
        self.assertEqual(data["total"], 1)
        self.assertIn("Quarterly", data["items"][0]["name"])

    def test_no_filter_returns_both(self):
        env = list_pm_schedules(asset=self.asset.name, page_size=50)
        self.assertEqual(env["data"]["total"], 2)

    def test_pagination_total_is_server_side(self):
        # page_size=1 nhưng total vẫn = 2 (server-computed, KHÔNG phải len trang)
        env = list_pm_schedules(asset=self.asset.name, page_size=1)
        self.assertEqual(env["data"]["total"], 2)
        self.assertEqual(len(env["data"]["items"]), 1)


class TestListDocRequestFilters(FrappeTestCase):
    """priority + search áp server-side."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = _ensure_cat()
        cls.asset = _make_asset("_Test Asset ListFilter Doc")
        cls.docs = []
        for prio, dtype in (("Low", "Ho so CE"), ("High", "Giay phep NK")):
            d = frappe.get_doc({
                "doctype": "Document Request",
                "asset_ref": cls.asset.name,
                "doc_type_required": dtype,
                "doc_category": "Legal",
                "status": "Open",
                "priority": prio,
                "assigned_to": "Administrator",
                "due_date": nowdate(),
            }).insert(ignore_permissions=True)
            cls.docs.append(d.name)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for n in cls.docs:
            if frappe.db.exists("Document Request", n):
                frappe.delete_doc("Document Request", n, force=True, ignore_permissions=True)
        purge_asset(cls.asset.name)
        _cleanup_cat()
        frappe.db.commit()

    def test_priority_filter_narrows_server_side(self):
        env = list_document_requests(asset=self.asset.name, priority="High", page_size=50)
        data = env["data"]
        self.assertEqual(data["total"], 1, "priority='High' phải loại phiếu Low")
        self.assertTrue(all(r["priority"] == "High" for r in data["items"]))

    def test_doc_search_narrows_server_side(self):
        env = list_document_requests(asset=self.asset.name, search="NK", page_size=50)
        data = env["data"]
        self.assertEqual(data["total"], 1)
        self.assertIn("NK", data["items"][0]["doc_type_required"])

    def test_no_filter_returns_both(self):
        env = list_document_requests(asset=self.asset.name, page_size=50)
        self.assertEqual(env["data"]["total"], 2)


class TestListFirmwareCrFilters(FrappeTestCase):
    """search áp server-side (version/mã)."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = _ensure_cat()
        cls.asset = _make_asset("_Test Asset ListFilter FCR")
        cls.fcrs = []
        for vb, va in (("1.0.0", "1.1.0"), ("2.0.0", "9.9.9")):
            d = frappe.get_doc({
                "doctype": "Firmware Change Request",
                "asset_ref": cls.asset.name,
                "version_before": vb,
                "version_after": va,
                "change_notes": "test",
            }).insert(ignore_permissions=True)
            cls.fcrs.append(d.name)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for n in cls.fcrs:
            if frappe.db.exists("Firmware Change Request", n):
                frappe.delete_doc("Firmware Change Request", n, force=True, ignore_permissions=True)
        purge_asset(cls.asset.name)
        _cleanup_cat()
        frappe.db.commit()

    def test_fcr_search_narrows_server_side(self):
        env = list_firmware_crs(asset=self.asset.name, search="9.9.9", page_size=50)
        data = env["data"]
        self.assertEqual(data["total"], 1, "search '9.9.9' chỉ khớp 1 FCR")
        self.assertEqual(data["items"][0]["version_after"], "9.9.9")

    def test_no_filter_returns_both(self):
        env = list_firmware_crs(asset=self.asset.name, page_size=50)
        self.assertEqual(env["data"]["total"], 2)
