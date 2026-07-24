# Copyright (c) 2026, AssetCore Team
"""IMM-00 — ISS-002 (nối tiếp): email của AssetCore phải mang thương hiệu AssetCore.

Bằng chứng lỗi (Email Queue ``casu13ge1s``, site ``miyano``, 2026-07-21 17:07 —
email THẬT người dùng đã nhận): nội dung tiếng Việt của AssetCore nhưng bị
Frappe bọc thêm chân trang quảng cáo ``Sent via ERPNext`` (hook
``default_mail_footer`` của ERPNext) và không có bất kỳ nhận diện AssetCore nào
(logo/tiêu đề/màu thương hiệu). Người dùng cuối chỉ biết AssetCore → email lẫn
form đều phải là của AssetCore.

Khoá 2 nhóm bất biến:
  A. ``utils/email_template.render_email`` — khung email chuẩn AssetCore
     (header thương hiệu + nút CTA + chân trang tiếng Việt), tự chứa CSS inline,
     escape dữ liệu người dùng, KHÔNG nhắc tới Frappe/ERPNext.
  B. Mọi email giao dịch của AssetCore (chào mừng / kích hoạt / báo đăng ký mới)
     đều đi qua khung đó, và chân trang quảng cáo của ERPNext bị tắt ở site.

Run:
    bench --site miyano run-tests --app assetcore \
        --module assetcore.tests.test_email_branding
"""
from __future__ import annotations

import time
import unittest

import frappe

import assetcore.api.auth as auth_api
import assetcore.api.user as user_api
from assetcore.setup import email as email_setup
from assetcore.utils import email_template

_UID = str(int(time.time()) % 100000)
_PLAINTEXT_PW = "MatKhauTam@2026"

# Dấu hiệu "email này do AssetCore dựng" — dùng để khẳng định caller không tự
# nối chuỗi HTML rời rạc mà đi qua khung chung.
_MARKER = email_template.EMAIL_MARKER

_FRAPPE_WORDS = ("erpnext", "frappe")


def setUpModule():
    frappe.set_user("Administrator")


def _assert_no_frappe_branding(case: unittest.TestCase, html: str, where: str) -> None:
    low = (html or "").lower()
    for word in _FRAPPE_WORDS:
        case.assertNotIn(
            word, low, f"{where}: KHÔNG được lộ thương hiệu '{word}' trong email AssetCore"
        )


# ─────────────────────────────────────────────────────────────────────────────
# A. Khung email chuẩn AssetCore
# ─────────────────────────────────────────────────────────────────────────────


class TestRenderEmail(unittest.TestCase):
    def test_renders_assetcore_brand_header_and_marker(self):
        html = email_template.render_email(
            title="Chào mừng bạn",
            body_html="<p>Nội dung</p>",
        )
        self.assertIn(_MARKER, html, "Khung email phải gắn dấu nhận diện AssetCore")
        self.assertIn(email_template.BRAND_NAME, html, "Phải có tên thương hiệu AssetCore")
        self.assertIn(email_template.BRAND_TAGLINE, html, "Phải có mô tả hệ thống (tiếng Việt)")
        self.assertIn("Chào mừng bạn", html, "Phải render tiêu đề email")
        self.assertIn("<p>Nội dung</p>", html, "Phải render phần thân do caller dựng")
        _assert_no_frappe_branding(self, html, "render_email")

    def test_renders_cta_button_as_anchor(self):
        url = "https://benhvien.vn/assetcore/set-password?key=abc123"
        html = email_template.render_email(
            title="Đặt mật khẩu",
            body_html="<p>x</p>",
            cta_label="Đặt mật khẩu",
            cta_url=url,
        )
        self.assertIn(f'href="{url}"', html, "Nút CTA phải là thẻ <a> trỏ đúng URL")
        self.assertIn("Đặt mật khẩu", html)

    def test_no_cta_when_url_missing(self):
        html = email_template.render_email(title="Thông báo", body_html="<p>x</p>")
        self.assertNotIn("ac-email-cta", html, "Không có URL thì KHÔNG render nút CTA")

    def test_escapes_untrusted_text_fields(self):
        html = email_template.render_email(
            title='Xin chào <script>alert("xss")</script>',
            body_html="<p>an toàn</p>",
            greeting='<img src=x onerror="alert(1)">',
        )
        # Escape đúng = KHÔNG còn thẻ thực thi được; chuỗi "onerror=" vẫn xuất
        # hiện nhưng đã vô hại vì nằm trong text đã escape (&lt;img ...&gt;).
        self.assertNotIn("<script>", html, "Tiêu đề phải được escape (chống XSS/HTML injection)")
        self.assertNotIn("<img", html, "Lời chào phải được escape (không sinh thẻ thật)")
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("&lt;img", html)

    def test_is_self_contained_html_document(self):
        """Email client không tải CSS ngoài → khung phải tự chứa (inline style)."""
        html = email_template.render_email(title="T", body_html="<p>x</p>")
        self.assertIn("<html", html.lower())
        self.assertNotIn("<link", html.lower(), "KHÔNG được tham chiếu stylesheet ngoài")
        self.assertNotIn("/assets/frappe/", html, "KHÔNG dùng asset của Frappe desk")

    def test_footer_is_vietnamese_and_assetcore(self):
        html = email_template.render_email(title="T", body_html="<p>x</p>")
        self.assertIn("không trả lời", html.lower(), "Chân trang tiếng Việt của AssetCore")
        _assert_no_frappe_branding(self, html, "footer")


# ─────────────────────────────────────────────────────────────────────────────
# B. Email giao dịch dùng khung chung
# ─────────────────────────────────────────────────────────────────────────────


class _MailCaptureBase(unittest.TestCase):
    """Bắt kwargs của ``_safe_sendmail`` tại ĐÚNG module gọi nó."""

    module = user_api

    def setUp(self):
        frappe.set_user("Administrator")
        self.sent: list[dict] = []
        self._orig = self.module._safe_sendmail
        self._emails: list[str] = []

        def _cap(**kw):
            self.sent.append(kw)
            return True

        self.module._safe_sendmail = _cap

    def tearDown(self):
        self.module._safe_sendmail = self._orig
        frappe.set_user("Administrator")
        for email in self._emails:
            if frappe.db.exists("User", email):
                frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        frappe.db.commit()

    def _track(self, email: str) -> str:
        self._emails.append(email)
        return email


class TestWelcomeEmailUsesAssetCoreTemplate(_MailCaptureBase):
    def _create(self, email: str, **extra) -> dict:
        payload = {
            "email": email,
            "first_name": "Trần Thị",
            "last_name": "Kỹ Thuật",
            "password": _PLAINTEXT_PW,
            "send_welcome_email": 1,
        }
        payload.update(extra)
        frappe.local.form_dict = frappe._dict(payload)
        return user_api.create_system_user()

    def test_welcome_email_is_assetcore_branded(self):
        email = self._track(f"_test_brand_welcome_{_UID}@example.com")
        res = self._create(email)
        self.assertTrue(res.get("success"), res)
        self.assertEqual(len(self.sent), 1)
        msg = self.sent[0].get("message") or ""

        self.assertIn(_MARKER, msg, "Email chào mừng phải dùng khung email AssetCore")
        self.assertIn(email_template.BRAND_NAME, msg)
        _assert_no_frappe_branding(self, msg, "welcome email")

        # Không đánh mất các bất biến ISS-002 đã khoá trước đó.
        self.assertIn("/assetcore/set-password?key=", msg)
        self.assertIn("/assetcore/login", msg)
        self.assertNotIn("/update-password", msg)
        self.assertNotIn(_PLAINTEXT_PW, msg)

    def test_welcome_email_escapes_user_full_name(self):
        email = self._track(f"_test_brand_xss_{_UID}@example.com")
        self._create(email, first_name='<script>alert("x")</script>', last_name="Nguy")
        msg = self.sent[0].get("message") or ""
        self.assertNotIn("<script>", msg, "Tên người dùng phải được escape trong email")


class TestActivationEmailUsesAssetCoreTemplate(_MailCaptureBase):
    def test_activation_email_is_assetcore_branded(self):
        email = self._track(f"_test_brand_activate_{_UID}@example.com")
        doc = frappe.new_doc("User")
        doc.email = email
        doc.first_name = "Lê Văn"
        doc.last_name = "Kích Hoạt"
        doc.user_type = "System User"
        doc.enabled = 1
        doc.flags.no_welcome_mail = True
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        user_api._send_activation_email(email)
        self.assertEqual(len(self.sent), 1)
        msg = self.sent[0].get("message") or ""
        self.assertIn(_MARKER, msg, "Email kích hoạt phải dùng khung email AssetCore")
        self.assertIn("/assetcore/login", msg)
        _assert_no_frappe_branding(self, msg, "activation email")


class TestRegistrationNoticeUsesAssetCoreTemplate(_MailCaptureBase):
    module = auth_api

    def test_admin_registration_notice_is_assetcore_branded(self):
        orig = auth_api._get_role_emails
        auth_api._get_role_emails = lambda roles: ["qtv@assetcore.test"]
        try:
            auth_api._notify_admins_registration(
                "moi@assetcore.test", "Người Mới", "Khoa Xét nghiệm"
            )
        finally:
            auth_api._get_role_emails = orig

        self.assertEqual(len(self.sent), 1)
        msg = self.sent[0].get("message") or ""
        self.assertIn(_MARKER, msg, "Email báo đăng ký mới phải dùng khung email AssetCore")
        _assert_no_frappe_branding(self, msg, "registration notice")


# ─────────────────────────────────────────────────────────────────────────────
# C. Tắt chân trang quảng cáo của ERPNext ở tầng site
# ─────────────────────────────────────────────────────────────────────────────


class TestDisableFrappeEmailBranding(unittest.TestCase):
    """``Sent via ERPNext`` do Frappe nối THÊM lúc gửi (hook ``default_mail_footer``)
    — khung email của AssetCore không kiểm soát được, phải tắt bằng default của site.
    """

    _DEFAULT_KEY = "disable_standard_email_footer"

    def setUp(self):
        frappe.set_user("Administrator")
        self._orig = frappe.db.get_default(self._DEFAULT_KEY)

    def tearDown(self):
        # Trả site về nguyên trạng — việc bật thật do `setup_assetcore_email` làm.
        frappe.db.set_default(self._DEFAULT_KEY, self._orig if self._orig is not None else 0)
        frappe.db.commit()
        frappe.set_user("Administrator")

    def test_disable_removes_erpnext_footer_from_real_frappe_builder(self):
        from frappe.email.email_body import get_footer

        frappe.db.set_default(self._DEFAULT_KEY, 0)
        frappe.db.commit()
        self.assertIn(
            "erpnext",
            (get_footer(None) or "").lower(),
            "Tiền đề: chưa tắt thì Frappe VẪN nối chân trang ERPNext",
        )

        res = email_setup.disable_frappe_email_branding()
        self.assertTrue(res.get("disabled"))
        _assert_no_frappe_branding(
            self, get_footer(None) or "", "frappe get_footer sau khi tắt"
        )

    def test_disable_is_idempotent(self):
        email_setup.disable_frappe_email_branding()
        again = email_setup.disable_frappe_email_branding()
        self.assertTrue(again.get("disabled"))
        self.assertFalse(again.get("changed"), "Chạy lại KHÔNG được đổi gì (idempotent)")

    def test_setup_assetcore_email_applies_branding_switch(self):
        frappe.db.set_default(self._DEFAULT_KEY, 0)
        frappe.db.commit()
        res = email_setup.setup_assetcore_email(quarantine_stale=False)
        self.assertIn("branding", res, "setup_assetcore_email phải áp cả bước tắt branding")
        self.assertTrue(res["branding"].get("disabled"))


if __name__ == "__main__":
    unittest.main()
