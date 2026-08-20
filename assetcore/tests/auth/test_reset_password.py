# Copyright (c) 2026, AssetCore Team
"""Unit tests — assetcore.api.user.reset_user_password

Run: bench --site miyano run-tests --module assetcore.tests.auth.test_reset_password
"""
from __future__ import annotations
import time
import unittest
import frappe
from frappe.utils.password import check_password
from frappe.tests.utils import FrappeTestCase


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_test_user(tag: str) -> str:
    """Tạo user tạm cho test — prefix _Test để Frappe nhận diện fixture."""
    email = f"_test.{tag}.{int(time.time()) % 100000}@assetcore-test.internal"
    if frappe.db.exists("User", email):
        return email
    doc = frappe.get_doc({
        "doctype": "User",
        "email": email,
        "first_name": f"_TestUser {tag}",
        "new_password": "InitialPass@2026",
        "send_welcome_email": 0,
        "enabled": 1,
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return email


def _ensure_role(user_email: str, role: str) -> None:
    user_doc = frappe.get_doc("User", user_email)
    existing = {r.role for r in user_doc.roles}
    if role not in existing:
        user_doc.append("roles", {"role": role})
        user_doc.save(ignore_permissions=True)
        frappe.db.commit()


def _delete_user(email: str) -> None:
    if frappe.db.exists("User", email):
        frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        frappe.db.commit()


# ── test class ───────────────────────────────────────────────────────────────

class TestResetUserPassword(FrappeTestCase):
    """BR: AssetCore Super Admin được reset mật khẩu user khác; non-admin thì không."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        ts = int(time.time()) % 100000
        cls.target   = _make_test_user(f"target-{ts}")
        cls.admin    = _make_test_user(f"admin-{ts}")
        _ensure_role(cls.admin, "AssetCore Super Admin")
        cls.nonadmin = _make_test_user(f"nonadmin-{ts}")

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for u in (cls.target, cls.admin, cls.nonadmin):
            _delete_user(u)

    def setUp(self):
        frappe.set_user("Administrator")

    # ── happy path ────────────────────────────────────────────────────────────

    def test_admin_can_reset_password(self):
        """Admin gọi reset_user_password → password được cập nhật trong DB."""
        from assetcore.api.user import reset_user_password
        frappe.set_user(self.admin)
        new_pwd = "BenhVienABC@2026!"
        result = reset_user_password(user=self.target, new_password=new_pwd)
        self.assertTrue(result.get("success"), msg=result)
        self.assertEqual(result["data"]["user"], self.target)
        # Xác minh mật khẩu thực sự cập nhật trong DB
        try:
            check_password(self.target, new_pwd)
        except frappe.AuthenticationError:
            self.fail("Mật khẩu không được cập nhật sau khi admin reset")

    def test_reset_returns_actor_in_response(self):
        """Response phải chứa reset_by = user đang thực hiện reset."""
        from assetcore.api.user import reset_user_password
        frappe.set_user(self.admin)
        result = reset_user_password(user=self.target, new_password="DrägerMedical@2026")
        self.assertTrue(result.get("success"), msg=result)
        self.assertEqual(result["data"]["reset_by"], self.admin)

    # ── validation ────────────────────────────────────────────────────────────

    def test_password_too_short_rejected(self):
        """Mật khẩu < 10 ký tự → trả lỗi 400."""
        from assetcore.api.user import reset_user_password
        frappe.set_user(self.admin)
        result = reset_user_password(user=self.target, new_password="Short1!")
        self.assertFalse(result.get("success"), msg=result)
        self.assertEqual(result.get("http_status"), 400)

    def test_password_exactly_10_chars_accepted(self):
        """Mật khẩu đúng 10 ký tự → hợp lệ."""
        from assetcore.api.user import reset_user_password
        frappe.set_user(self.admin)
        result = reset_user_password(user=self.target, new_password="Abc@123456")
        self.assertTrue(result.get("success"), msg=result)

    def test_nonexistent_user_rejected(self):
        """User không tồn tại → trả lỗi 404."""
        from assetcore.api.user import reset_user_password
        frappe.set_user(self.admin)
        result = reset_user_password(user="ghost@nowhere.com", new_password="ValidPass@2026")
        self.assertFalse(result.get("success"), msg=result)
        self.assertEqual(result.get("http_status"), 404)

    # ── permission ────────────────────────────────────────────────────────────

    def test_non_admin_cannot_reset(self):
        """User không có role admin → bị từ chối với 403."""
        from assetcore.api.user import reset_user_password
        frappe.set_user(self.nonadmin)
        result = reset_user_password(user=self.target, new_password="ValidPass@2026")
        self.assertFalse(result.get("success"), msg=result)
        self.assertEqual(result.get("http_status"), 403)

    def test_guest_cannot_reset(self):
        """Guest (chưa login) → bị từ chối."""
        from assetcore.api.user import reset_user_password
        frappe.set_user("Guest")
        result = reset_user_password(user=self.target, new_password="ValidPass@2026")
        self.assertFalse(result.get("success"), msg=result)
        self.assertIn(result.get("http_status"), (401, 403))
