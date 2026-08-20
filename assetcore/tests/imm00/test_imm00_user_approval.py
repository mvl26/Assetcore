# Copyright (c) 2026, AssetCore Team
"""IMM-00 User Account & Approval — invariant regression.

Source: docs/imm-00/04_Backend_Design.md §II.10 (BR-00-USR-01).

Root-cause được phủ ở đây: Custom Field `imm_approval_status` từng có
default='Pending' khiến mọi User tạo ngoài luồng self-signup (enabled=1) bị
gán Pending giả. Test khoá invariant: Pending ⟺ enabled=0.

Run:
    bench --site miyano run-tests --app assetcore \
        --module assetcore.tests.imm00.test_imm00_user_approval
"""
from __future__ import annotations

import time
import unittest

import frappe
from frappe.tests.utils import FrappeTestCase


_UID = str(int(time.time()) % 100000)


def setUpModule():
    frappe.set_user("Administrator")


class TestUserApprovalInvariant(FrappeTestCase):
    """BR-00-USR-01: enabled=1 ⇒ KHÔNG được Pending."""

    def setUp(self):
        self._emails: list[str] = []

    def tearDown(self):
        for email in self._emails:
            if frappe.db.exists("User", email):
                frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        frappe.db.commit()

    def _new_user(self, suffix: str, enabled: int) -> str:
        email = f"_test_appr_{suffix}_{_UID}@example.com"
        self._emails.append(email)
        doc = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": f"Appr {suffix}",
            "enabled": enabled,
            "user_type": "System User",
            "send_welcome_email": 0,
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return email

    def test_custom_field_default_not_pending(self):
        """Custom Field default phải rỗng — KHÔNG 'Pending'."""
        cf = frappe.db.exists(
            "Custom Field", {"dt": "User", "fieldname": "imm_approval_status"})
        self.assertTrue(cf, "Custom Field imm_approval_status phải tồn tại")
        default = frappe.db.get_value("Custom Field", cf, "default")
        self.assertNotEqual(
            default, "Pending",
            "default='Pending' gây badge 'Chờ duyệt' giả cho user enabled=1")

    def test_enabled_user_created_directly_not_pending(self):
        """User enabled=1 tạo trực tiếp KHÔNG được mang status 'Pending'."""
        email = self._new_user("direct", enabled=1)
        status = frappe.db.get_value("User", email, "imm_approval_status")
        self.assertNotEqual(
            status, "Pending",
            "enabled=1 mà Pending = badge giả, không có gate thật")

    def test_admin_create_system_user_is_approved(self):
        """create_system_user (admin) → enabled=1 + Approved ngay."""
        from assetcore.api.user import create_system_user

        email = f"_test_appr_sysuser_{_UID}@example.com"
        self._emails.append(email)
        frappe.local.form_dict = frappe._dict({
            "email": email,
            "first_name": "Sys",
            "imm_roles": "[]",
        })
        res = create_system_user()
        # Endpoint trả về envelope chuẩn {success, data:{user,...}}.
        self.assertTrue(res.get("success"), res)
        self.assertEqual(res["data"]["user"], email)
        status = frappe.db.get_value("User", email, "imm_approval_status")
        enabled = frappe.db.get_value("User", email, "enabled")
        self.assertEqual(status, "Approved")
        self.assertEqual(int(enabled), 1)

    def test_self_signup_is_pending_and_disabled(self):
        """register_user (self-signup) → enabled=0 + Pending (gate thật)."""
        from assetcore.api.auth import register_user

        email = f"_test_appr_signup_{_UID}@example.com"
        self._emails.append(email)
        register_user(
            email=email, full_name="Signup User", password="Test@12345")
        status = frappe.db.get_value("User", email, "imm_approval_status")
        enabled = frappe.db.get_value("User", email, "enabled")
        self.assertEqual(status, "Pending")
        self.assertEqual(int(enabled), 0,
                         "Pending phải đi kèm enabled=0 (BR-00-USR-01)")
