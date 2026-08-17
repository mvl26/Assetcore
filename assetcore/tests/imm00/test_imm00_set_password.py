# Copyright (c) 2026, AssetCore Team
"""IMM-00 — ISS-002 (nối tiếp): API tự đặt mật khẩu của AssetCore.

Người dùng mới bấm link trong email chào mừng → mở màn hình AssetCore
(``/assetcore/set-password``), KHÔNG dùng form ``/update-password`` của Frappe
desk. Hai endpoint guest phục vụ màn hình đó:

  - ``verify_password_key``   : kiểm tra link còn hiệu lực (để render tên user).
  - ``set_password_with_key`` : đặt mật khẩu lần đầu bằng key trong link.

Khoá các bất biến bảo mật:
  - Key sai/đã dùng/hết hạn → từ chối, thông điệp KHÔNG phân biệt user tồn tại.
  - Key dùng MỘT LẦN (đặt xong là vô hiệu).
  - Mật khẩu yếu bị từ chối và KHÔNG tiêu key.
  - Tài khoản bị vô hiệu hoá không được đặt mật khẩu.

Run:
    bench --site miyano run-tests --app assetcore \
        --module assetcore.tests.imm00.test_imm00_set_password
"""
from __future__ import annotations

import time
import unittest
from datetime import timedelta

import frappe
from frappe.utils import now_datetime

import assetcore.api.auth as auth_api
import assetcore.api.user as user_api
from frappe.tests.utils import FrappeTestCase


_UID = str(int(time.time()) % 100000)
_STRONG_PW = "Kt#Bv2026$Ngoc"


def setUpModule():
    frappe.set_user("Administrator")


def _key_from_link(link: str) -> str:
    """Tách key thô khỏi URL đặt mật khẩu (chỉ key thô mới verify được)."""
    return link.split("key=", 1)[1]


class _SetPasswordBase(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.email = f"_test_setpw_{_UID}_{id(self)}@assetcore.test"
        doc = frappe.new_doc("User")
        doc.email = self.email
        doc.first_name = "Nguyễn Văn"
        doc.last_name = "Đặt"
        doc.user_type = "System User"
        doc.enabled = 1
        doc.flags.no_welcome_mail = True
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        self.key = _key_from_link(user_api._make_set_password_link(self.email))

    def tearDown(self):
        frappe.set_user("Administrator")
        if frappe.db.exists("User", self.email):
            frappe.delete_doc("User", self.email, force=True, ignore_permissions=True)
        frappe.db.commit()


class TestVerifyPasswordKey(_SetPasswordBase):
    def test_valid_key_returns_user_identity(self):
        res = auth_api.verify_password_key(self.key)
        self.assertTrue(res.get("success"), res)
        self.assertEqual(res["data"]["user"], self.email)
        self.assertIn("Nguyễn Văn", res["data"]["full_name"])

    def test_invalid_key_rejected_without_enumeration(self):
        res = auth_api.verify_password_key("khong-phai-key-that")
        self.assertFalse(res.get("success"))
        self.assertNotIn(self.email, res.get("error", ""),
                         "Thông điệp lỗi KHÔNG được lộ tài khoản nào")

    def test_empty_key_rejected(self):
        self.assertFalse(auth_api.verify_password_key("").get("success"))

    def test_expired_key_rejected(self):
        expiry = frappe.db.get_single_value("System Settings",
                                            "reset_password_link_expiry_duration") or 1200
        frappe.db.set_value(
            "User", self.email,
            "last_reset_password_key_generated_on",
            now_datetime() - timedelta(seconds=int(expiry) + 600),
            update_modified=False,
        )
        res = auth_api.verify_password_key(self.key)
        self.assertFalse(res.get("success"))
        self.assertIn("hết hạn", res.get("error", "").lower())


class TestSetPasswordWithKey(_SetPasswordBase):
    def test_sets_password_and_consumes_key(self):
        from frappe.utils.password import check_password

        res = auth_api.set_password_with_key(self.key, _STRONG_PW)
        self.assertTrue(res.get("success"), res)
        self.assertEqual(res["data"]["user"], self.email)

        check_password(self.email, _STRONG_PW, delete_tracker_cache=False)
        self.assertFalse(
            frappe.db.get_value("User", self.email, "reset_password_key"),
            "Key phải bị xoá sau khi dùng (một lần duy nhất)",
        )

    def test_key_cannot_be_replayed(self):
        self.assertTrue(auth_api.set_password_with_key(self.key, _STRONG_PW).get("success"))
        res2 = auth_api.set_password_with_key(self.key, "Kt#Bv2026$Khac")
        self.assertFalse(res2.get("success"), "Key đã dùng KHÔNG được dùng lại")

    def test_weak_password_rejected_and_key_preserved(self):
        res = auth_api.set_password_with_key(self.key, "123")
        self.assertFalse(res.get("success"))
        self.assertTrue(
            frappe.db.get_value("User", self.email, "reset_password_key"),
            "Mật khẩu không hợp lệ KHÔNG được tiêu key (user phải thử lại được)",
        )
        # Thử lại với mật khẩu mạnh trên CÙNG key → phải thành công.
        self.assertTrue(auth_api.set_password_with_key(self.key, _STRONG_PW).get("success"))

    def test_invalid_key_rejected(self):
        self.assertFalse(auth_api.set_password_with_key("sai-key", _STRONG_PW).get("success"))

    def test_disabled_user_cannot_set_password(self):
        frappe.db.set_value("User", self.email, "enabled", 0, update_modified=False)
        frappe.db.commit()
        res = auth_api.set_password_with_key(self.key, _STRONG_PW)
        self.assertFalse(res.get("success"),
                         "Tài khoản bị vô hiệu hoá KHÔNG được đặt mật khẩu")


class TestWhitelistContract(FrappeTestCase):
    """User CHƯA đăng nhập được mới đặt được mật khẩu → phải allow_guest + POST."""

    def test_endpoints_are_guest_accessible_post_only(self):
        for fn in (auth_api.verify_password_key, auth_api.set_password_with_key):
            target = getattr(fn, "__func__", fn)
            self.assertIn(target, frappe.whitelisted, f"{fn.__name__} phải được whitelist")
            self.assertIn(target, frappe.guest_methods,
                          f"{fn.__name__} phải allow_guest (user chưa đăng nhập)")
            self.assertEqual(
                frappe.allowed_http_methods_for_whitelisted_func.get(target), ["POST"],
                f"{fn.__name__} chỉ được nhận POST (không đặt key/mật khẩu qua URL GET)",
            )


if __name__ == "__main__":
    unittest.main()
