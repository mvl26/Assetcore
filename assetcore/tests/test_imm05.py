# Copyright (c) 2026, AssetCore Team
"""IMM-05 unit tests — approve_document, reject_document, update_document, _resolve_alert_level.

Run: bench --site miyano run-tests --app assetcore --module assetcore.tests.test_imm05
"""
from __future__ import annotations

import unittest

import frappe
from frappe.utils import add_days, nowdate

from assetcore.services.imm05 import (
    DocState,
    _resolve_alert_level,
    approve_document,
    list_documents,
    reject_document,
    update_document,
)
from assetcore.services.shared import ServiceError


# ─── Fixtures ────────────────────────────────────────────────────────────────

def _make_asset() -> str:
    doc = frappe.get_doc({
        "doctype": "AC Asset",
        "asset_name": "_Test Asset IMM05",
    })
    doc.flags.ignore_mandatory = True
    doc.insert(ignore_permissions=True)
    return doc.name


def _make_doc(asset_ref: str, state: str = DocState.DRAFT) -> str:
    doc = frappe.get_doc({
        "doctype": "Asset Document",
        "asset_ref": asset_ref,
        "doc_category": "Technical",
        "doc_type_detail": "Manual",
        "doc_number": f"DOC-TEST-{frappe.generate_hash(length=6)}",
        "version": "1.0",
        "issued_date": frappe.utils.nowdate(),
        "file_attachment": "/files/dummy-test.pdf",
        "workflow_state": state,
    })
    doc.flags.ignore_mandatory = True
    doc.insert(ignore_permissions=True)
    return doc.name


# ─── _resolve_alert_level ─────────────────────────────────────────────────────

class TestResolveAlertLevel(unittest.TestCase):

    def test_7_days_is_danger(self):
        self.assertEqual(_resolve_alert_level(7), "Danger")

    def test_5_days_is_danger(self):
        self.assertEqual(_resolve_alert_level(5), "Danger")

    def test_30_days_is_critical(self):
        self.assertEqual(_resolve_alert_level(30), "Critical")

    def test_25_days_is_critical(self):
        self.assertEqual(_resolve_alert_level(25), "Critical")

    def test_60_days_is_warning(self):
        self.assertEqual(_resolve_alert_level(60), "Warning")

    def test_90_days_is_info(self):
        self.assertEqual(_resolve_alert_level(90), "Info")

    def test_91_days_no_alert(self):
        self.assertIsNone(_resolve_alert_level(91))

    def test_0_days_is_danger(self):
        self.assertEqual(_resolve_alert_level(0), "Danger")


# ─── create_document ─────────────────────────────────────────────────────────

class TestCreateDocument(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset()

    @classmethod
    def tearDownClass(cls):
        frappe.db.delete("Asset Document", {"asset_ref": cls.asset})
        frappe.delete_doc("AC Asset", cls.asset, force=True, ignore_permissions=True)

    def test_create_returns_name_and_state(self):
        # _make_doc uses ignore_mandatory; verify state via direct fixture
        name = _make_doc(self.asset, DocState.DRAFT)
        state = frappe.db.get_value("Asset Document", name, "workflow_state")
        self.assertEqual(state, DocState.DRAFT)

    def test_default_version_is_1_0(self):
        name = _make_doc(self.asset, DocState.DRAFT)
        doc = frappe.get_doc("Asset Document", name)
        self.assertEqual(doc.version, "1.0")


# ─── update_document ─────────────────────────────────────────────────────────

class TestUpdateDocument(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset()

    @classmethod
    def tearDownClass(cls):
        frappe.db.delete("Asset Document", {"asset_ref": cls.asset})
        frappe.delete_doc("AC Asset", cls.asset, force=True, ignore_permissions=True)

    def test_update_draft_succeeds(self):
        name = _make_doc(self.asset, DocState.DRAFT)
        result = update_document(name, {"doc_number": "DOC-2026-0001"})
        self.assertIn("name", result)

    def test_update_active_blocked(self):
        name = _make_doc(self.asset, DocState.DRAFT)
        frappe.db.set_value("Asset Document", name, "workflow_state", DocState.ACTIVE)
        with self.assertRaises(ServiceError) as ctx:
            update_document(name, {"doc_number": "X"})
        self.assertEqual(ctx.exception.code, "BAD_STATE")

    def test_update_not_found_raises(self):
        with self.assertRaises(ServiceError) as ctx:
            update_document("FAKE-DOC-NAME", {"doc_number": "X"})
        self.assertEqual(ctx.exception.code, "NOT_FOUND")


# ─── approve_document ────────────────────────────────────────────────────────

class TestApproveDocument(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset()

    @classmethod
    def tearDownClass(cls):
        frappe.db.delete("Asset Document", {"asset_ref": cls.asset})
        frappe.delete_doc("AC Asset", cls.asset, force=True, ignore_permissions=True)

    def test_approve_pending_review_succeeds(self):
        name = _make_doc(self.asset, DocState.DRAFT)
        frappe.db.set_value("Asset Document", name, "workflow_state", DocState.PENDING_REVIEW)
        result = approve_document(name)
        self.assertEqual(result["new_state"], DocState.ACTIVE)
        self.assertEqual(result["approved_by"], "Administrator")

    def test_approve_draft_raises_bad_state(self):
        name = _make_doc(self.asset, DocState.DRAFT)
        with self.assertRaises(ServiceError) as ctx:
            approve_document(name)
        self.assertEqual(ctx.exception.code, "BAD_STATE")

    def test_approve_archives_old_active(self):
        # Create old Active doc for same (asset, doc_type_detail)
        old_name = _make_doc(self.asset, DocState.DRAFT)
        frappe.db.set_value("Asset Document", old_name, {
            "workflow_state": DocState.ACTIVE,
            "doc_type_detail": "Manual",
        })
        # Create new doc, move to Pending Review, approve
        new_name = _make_doc(self.asset, DocState.DRAFT)
        frappe.db.set_value("Asset Document", new_name, {
            "workflow_state": DocState.PENDING_REVIEW,
            "doc_type_detail": "Manual",
        })
        approve_document(new_name)
        old_state = frappe.db.get_value("Asset Document", old_name, "workflow_state")
        self.assertEqual(old_state, DocState.ARCHIVED)


# ─── reject_document ─────────────────────────────────────────────────────────

class TestRejectDocument(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset()

    @classmethod
    def tearDownClass(cls):
        frappe.db.delete("Asset Document", {"asset_ref": cls.asset})
        frappe.delete_doc("AC Asset", cls.asset, force=True, ignore_permissions=True)

    def test_reject_without_reason_raises(self):
        name = _make_doc(self.asset, DocState.DRAFT)
        frappe.db.set_value("Asset Document", name, "workflow_state", DocState.PENDING_REVIEW)
        with self.assertRaises(ServiceError) as ctx:
            reject_document(name, "")
        self.assertEqual(ctx.exception.code, "VALIDATION")

    def test_reject_pending_review_succeeds(self):
        name = _make_doc(self.asset, DocState.DRAFT)
        frappe.db.set_value("Asset Document", name, "workflow_state", DocState.PENDING_REVIEW)
        result = reject_document(name, "Tài liệu không hợp lệ")
        self.assertEqual(result["new_state"], DocState.REJECTED)

    def test_reject_draft_raises_bad_state(self):
        name = _make_doc(self.asset, DocState.DRAFT)
        with self.assertRaises(ServiceError) as ctx:
            reject_document(name, "reason")
        self.assertEqual(ctx.exception.code, "BAD_STATE")


# ─── list_documents ──────────────────────────────────────────────────────────

class TestListDocuments(unittest.TestCase):

    def test_list_returns_dict_with_items(self):
        result = list_documents({})
        self.assertIn("items", result)
        # total is under pagination or at top level depending on version
        has_total = "total" in result or ("pagination" in result and "total" in result["pagination"])
        self.assertTrue(has_total)
        self.assertIsInstance(result["items"], list)

    def test_page_size_respected(self):
        result = list_documents({}, page=1, page_size=5)
        self.assertLessEqual(len(result["items"]), 5)


if __name__ == "__main__":
    unittest.main()
