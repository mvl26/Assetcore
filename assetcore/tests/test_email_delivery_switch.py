# Copyright (c) 2026, AssetCore Team
"""IMM-00 — Công tắc BẬT/TẮT gửi email của AssetCore (tạm dừng, không xoá code).

Bối cảnh (2026-07-22): tài khoản Gmail dùng để gửi đã chạm hạn mức ngày
(``550 5.4.5 Daily user sending limit exceeded``) → mọi email chào mừng/kích hoạt
đều lỗi và làm bẩn Error Log. Cần TẮT TẠM việc gửi mà **giữ nguyên toàn bộ code**
để bật lại bất cứ lúc nào.

Thiết kế: cờ ở **default của site** (DB), KHÔNG phải ``site_config.json`` (đổi
site_config cần restart + là thao tác của người vận hành) và KHÔNG phải xoá/bình
luận code. ``_safe_sendmail`` — cửa duy nhất mọi email AssetCore đi qua — tôn
trọng cờ này và trả ``False`` gọn gàng (không raise, không rác Error Log).

Khoá bất biến:
  - Tắt → KHÔNG gọi ``frappe.sendmail``, trả ``False``, không raise.
  - Bật lại → gửi bình thường (đảo ngược hoàn toàn).
  - Idempotent cả hai chiều.
  - Nghiệp vụ KHÔNG gãy khi tắt: tạo user vẫn thành công, chỉ báo chưa gửi được.

Run:
    bench --site miyano run-tests --app assetcore \
        --module assetcore.tests.test_email_delivery_switch
"""
from __future__ import annotations

import time
import unittest

import frappe

import assetcore.api.user as user_api
from assetcore.setup import email as email_setup
from assetcore.utils import helpers

_UID = str(int(time.time()) % 100000)


def setUpModule():
    frappe.set_user("Administrator")


class _SwitchBase(unittest.TestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._orig = email_setup.is_email_delivery_disabled()

    def tearDown(self):
        email_setup.set_email_delivery(enabled=not self._orig)
        frappe.set_user("Administrator")
        frappe.db.commit()


class TestDeliverySwitch(_SwitchBase):
    def test_disable_blocks_sendmail_without_raising(self):
        sent: list = []
        orig = frappe.sendmail
        frappe.sendmail = lambda **kw: sent.append(kw)
        try:
            email_setup.set_email_delivery(enabled=False)
            ok = helpers._safe_sendmail(
                recipients=["ai@assetcore.test"], subject="x", message="<p>x</p>"
            )
        finally:
            frappe.sendmail = orig

        self.assertFalse(ok, "Đang TẮT thì _safe_sendmail phải trả False")
        self.assertEqual(sent, [], "Đang TẮT thì KHÔNG được gọi frappe.sendmail")

    def test_enable_restores_sending(self):
        sent: list = []
        orig = frappe.sendmail
        frappe.sendmail = lambda **kw: sent.append(kw)
        try:
            email_setup.set_email_delivery(enabled=False)
            email_setup.set_email_delivery(enabled=True)
            ok = helpers._safe_sendmail(
                recipients=["ai@assetcore.test"], subject="x", message="<p>x</p>"
            )
        finally:
            frappe.sendmail = orig

        self.assertTrue(ok, "Bật lại thì phải gửi được (đảo ngược hoàn toàn)")
        self.assertEqual(len(sent), 1)

    def test_is_disabled_reflects_switch(self):
        email_setup.set_email_delivery(enabled=False)
        self.assertTrue(email_setup.is_email_delivery_disabled())
        email_setup.set_email_delivery(enabled=True)
        self.assertFalse(email_setup.is_email_delivery_disabled())

    def test_idempotent_both_directions(self):
        email_setup.set_email_delivery(enabled=False)
        again = email_setup.set_email_delivery(enabled=False)
        self.assertFalse(again.get("changed"), "Tắt 2 lần → lần 2 không đổi gì")
        email_setup.set_email_delivery(enabled=True)
        again2 = email_setup.set_email_delivery(enabled=True)
        self.assertFalse(again2.get("changed"), "Bật 2 lần → lần 2 không đổi gì")

    def test_result_reports_state(self):
        res = email_setup.set_email_delivery(enabled=False)
        self.assertIs(res.get("enabled"), False)
        self.assertIn("changed", res)


class TestBusinessFlowSurvivesDisabledEmail(_SwitchBase):
    """Tắt email KHÔNG được làm gãy nghiệp vụ — chỉ báo 'chưa gửi được'."""

    def setUp(self):
        super().setUp()
        self.email = f"_test_mailoff_{_UID}@example.com"

    def tearDown(self):
        if frappe.db.exists("User", self.email):
            frappe.delete_doc("User", self.email, force=True, ignore_permissions=True)
        super().tearDown()

    def test_create_user_still_succeeds_when_delivery_off(self):
        email_setup.set_email_delivery(enabled=False)
        frappe.local.form_dict = frappe._dict({
            "email": self.email,
            "first_name": "Nguyễn",
            "last_name": "Tắt Mail",
            "password": "MatKhauTam@2026",
            "send_welcome_email": 1,
        })
        res = user_api.create_system_user()

        self.assertTrue(res.get("success"), f"Tắt email KHÔNG được chặn tạo user: {res}")
        self.assertIs(res["data"].get("welcome_email_sent"), False)
        self.assertIn("welcome_email_error", res["data"],
                      "Phải báo cho admin biết email chưa gửi (truy vết)")
        self.assertEqual(int(frappe.db.get_value("User", self.email, "enabled")), 1)


if __name__ == "__main__":
    unittest.main()
