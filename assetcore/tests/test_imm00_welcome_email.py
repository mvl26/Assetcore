# Copyright (c) 2026, AssetCore Team
"""IMM-00 — ISS-002: email chào mừng khi admin tạo user mới.

Khoá tiêu chí nghiệm thu của phiếu lỗi ISS-002:
  - Tick "Gửi email chào mừng" + tạo thành công → gửi ĐÚNG 01 email.
  - Không tick → KHÔNG gửi email.
  - Email tới đúng địa chỉ, gửi now=True, chứa URL /login + link tự đặt mật khẩu,
    KHÔNG chứa mật khẩu dạng plaintext.
  - Gửi lỗi → user vẫn được tạo + response báo welcome_email_sent=False (truy vết).
  - Tạo trùng (409) → KHÔNG phát sinh email thứ 2.

Run:
    bench --site miyano run-tests --app assetcore \
        --module assetcore.tests.test_imm00_welcome_email
"""
from __future__ import annotations

import time
import unittest

import frappe

import assetcore.api.user as user_api


_UID = str(int(time.time()) % 100000)
_PLAINTEXT_PW = "MatKhauTam@2026"


def setUpModule():
    frappe.set_user("Administrator")


def _form(**kw) -> None:
    frappe.local.form_dict = frappe._dict(kw)


class _WelcomeBase(unittest.TestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._emails: list[str] = []
        self._orig_sendmail = user_api._safe_sendmail
        self.sent: list[dict] = []

    def tearDown(self):
        user_api._safe_sendmail = self._orig_sendmail
        frappe.set_user("Administrator")
        for email in self._emails:
            if frappe.db.exists("User", email):
                frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        frappe.db.commit()

    def _track(self, email: str) -> str:
        self._emails.append(email)
        return email

    def _capture_ok(self):
        """Patch _safe_sendmail: ghi lại kwargs, trả True (giả lập gửi thành công)."""
        def _cap(**kw):
            self.sent.append(kw)
            return True
        user_api._safe_sendmail = _cap

    def _capture_fail(self):
        """Patch _safe_sendmail: ghi lại kwargs, trả False (giả lập gửi thất bại)."""
        def _cap(**kw):
            self.sent.append(kw)
            return False
        user_api._safe_sendmail = _cap

    def _create(self, email: str, **extra) -> dict:
        payload = {
            "email": email,
            "first_name": "Trần Thị",
            "last_name": "Kỹ Thuật",
            "password": _PLAINTEXT_PW,
        }
        payload.update(extra)
        _form(**payload)
        return user_api.create_system_user()


class TestWelcomeEmailSent(_WelcomeBase):
    def test_sent_exactly_once_with_correct_content(self):
        self._capture_ok()
        email = self._track(f"_test_welcome_ok_{_UID}@example.com")
        res = self._create(email, send_welcome_email=1)

        self.assertTrue(res.get("success"), res)
        self.assertEqual(len(self.sent), 1, "Phải gửi ĐÚNG 01 email chào mừng")
        kw = self.sent[0]

        recip = kw.get("recipients")
        recip = recip if isinstance(recip, list) else [recip]
        self.assertIn(email, recip, "Email chào mừng phải gửi đúng địa chỉ user")
        self.assertTrue(kw.get("now"), "Welcome mail phải gửi now=True (không phụ thuộc scheduler)")

        msg = kw.get("message") or ""
        # Link PHẢI trỏ vào UI AssetCore (SPA mount tại /assetcore), KHÔNG trỏ
        # form desk của Frappe (/update-password) — người dùng cuối chỉ biết
        # giao diện AssetCore.
        self.assertIn("/assetcore/login", msg, "Email phải chứa URL đăng nhập của UI AssetCore")
        self.assertIn("/assetcore/set-password?key=", msg,
                      "Email phải chứa link đặt mật khẩu trên UI AssetCore")
        self.assertNotIn("/update-password", msg,
                         "KHÔNG được dùng form /update-password của Frappe desk")
        self.assertIn(email, msg, "Email phải hiển thị tên đăng nhập")
        self.assertNotIn(_PLAINTEXT_PW, msg,
                         "KHÔNG được gửi mật khẩu dạng plaintext (tiêu chí bảo mật ISS-002)")

        self.assertIs(res["data"].get("welcome_email_sent"), True)

    def test_reset_key_persisted_for_set_password_link(self):
        """Link tự đặt mật khẩu phải khớp reset_password_key lưu trên User."""
        self._capture_ok()
        email = self._track(f"_test_welcome_key_{_UID}@example.com")
        self._create(email, send_welcome_email=1)
        key_hash = frappe.db.get_value("User", email, "reset_password_key")
        self.assertTrue(key_hash, "create_system_user + welcome phải sinh reset_password_key")


class TestWelcomeEmailNotSent(_WelcomeBase):
    def test_no_email_when_option_unchecked(self):
        self._capture_ok()
        email = self._track(f"_test_welcome_off_{_UID}@example.com")
        res = self._create(email, send_welcome_email=0)

        self.assertTrue(res.get("success"), res)
        self.assertEqual(len(self.sent), 0, "Không tick → KHÔNG gửi email")
        self.assertNotIn("welcome_email_sent", res["data"])

    def test_duplicate_create_sends_no_second_email(self):
        self._capture_ok()
        email = self._track(f"_test_welcome_dup_{_UID}@example.com")
        self._create(email, send_welcome_email=1)
        self.assertEqual(len(self.sent), 1)

        # Tạo lại cùng email → 409, KHÔNG gửi email lần 2.
        res2 = self._create(email, send_welcome_email=1)
        self.assertFalse(res2.get("success"), "Email trùng phải bị chặn (409)")
        self.assertEqual(len(self.sent), 1, "Tạo trùng KHÔNG được phát sinh email thứ 2")


class TestWelcomeEmailFailureTraceable(_WelcomeBase):
    def test_failure_reported_but_user_created(self):
        self._capture_fail()
        email = self._track(f"_test_welcome_fail_{_UID}@example.com")
        res = self._create(email, send_welcome_email=1)

        self.assertTrue(res.get("success"),
                        "Lỗi gửi mail KHÔNG được làm fail việc tạo user")
        self.assertEqual(int(frappe.db.get_value("User", email, "enabled")), 1,
                         "User vẫn được tạo & enabled dù email lỗi")
        self.assertIs(res["data"].get("welcome_email_sent"), False)
        self.assertIn("welcome_email_error", res["data"],
                      "Gửi lỗi phải trả thông báo cho admin (truy vết)")

    def test_sendmail_exception_is_swallowed(self):
        """_safe_sendmail raise → _send_welcome_email không được raise, trả False."""
        def _boom(**kw):
            raise RuntimeError("SMTP down")

        user_api._safe_sendmail = _boom
        email = self._track(f"_test_welcome_boom_{_UID}@example.com")
        res = self._create(email, send_welcome_email=1)
        self.assertTrue(res.get("success"))
        self.assertIs(res["data"].get("welcome_email_sent"), False)


if __name__ == "__main__":
    unittest.main()
