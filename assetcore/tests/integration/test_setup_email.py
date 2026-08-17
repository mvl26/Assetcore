# Copyright (c) 2026, AssetCore Team
"""IMM-00 — ISS-002: cấu hình Email Account gửi đi từ .env.

Khoá hành vi của assetcore.setup.email:
  - _load_env parse KEY=VALUE, bỏ comment/blank/quote.
  - _read_smtp_config: thiếu key bắt buộc → None; strip khoảng trắng trong App
    Password (Gmail nhập 4 nhóm cách nhau).
  - configure_outgoing_email: upsert Email Account default_outgoing DUY NHẤT;
    idempotent; .env thiếu → skipped (an toàn cho CI/env khác).

DB test dùng TÊN ACCOUNT throwaway (monkeypatch _ACCOUNT_NAME) → KHÔNG đụng
account 'AssetCore Notifications' thật.

Run:
    bench --site miyano run-tests --app assetcore \
        --module assetcore.tests.integration.test_setup_email
"""
from __future__ import annotations

import inspect
import os
import tempfile
import time
import unittest

import frappe

import assetcore.setup.email as ac_email
import assetcore.setup.install as ac_install
from frappe.tests.utils import FrappeTestCase


_UID = str(int(time.time()) % 100000)

# Email Account có UNIQUE index trên `email_id` → test PHẢI dùng địa chỉ
# throwaway, KHÔNG được trùng account gửi THẬT của site (nếu không, insert
# account test sẽ đụng Duplicate entry và test đỏ vì dữ liệu thật).
_TEST_EMAIL = f"ac-smtp-{_UID}@assetcore.test"

_TEST_ENV = {
    "ASSETCORE_SMTP_SERVER": "smtp.gmail.com",
    "ASSETCORE_SMTP_PORT": "587",
    "ASSETCORE_SMTP_USE_TLS": "1",
    "ASSETCORE_SMTP_LOGIN": _TEST_EMAIL,
    "ASSETCORE_SMTP_PASSWORD": "abcd efgh ijkl mnop",
    "ASSETCORE_SMTP_SENDER": _TEST_EMAIL,
}


def setUpModule():
    frappe.set_user("Administrator")


class TestEnvParsing(FrappeTestCase):
    def test_load_env_parses_and_ignores_noise(self):
        content = (
            "# comment line\n"
            "\n"
            'ASSETCORE_SMTP_SERVER="smtp.gmail.com"\n'
            "ASSETCORE_SMTP_LOGIN=snonamevx@gmail.com\n"
            "NO_EQUALS_LINE_IGNORED\n"
        )
        fd, path = tempfile.mkstemp(suffix=".env")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(content)
            env = ac_email._load_env(path)
        finally:
            os.remove(path)
        self.assertEqual(env.get("ASSETCORE_SMTP_SERVER"), "smtp.gmail.com")
        self.assertEqual(env.get("ASSETCORE_SMTP_LOGIN"), "snonamevx@gmail.com")
        self.assertNotIn("NO_EQUALS_LINE_IGNORED", env)

    def test_load_env_missing_file_returns_empty(self):
        self.assertEqual(ac_email._load_env("/nonexistent/path/.env"), {})

    def test_read_config_strips_app_password_spaces(self):
        cfg = ac_email._read_smtp_config(dict(_TEST_ENV))
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg["password"], "abcdefghijklmnop",
                         "Gmail App Password phải bỏ khoảng trắng cho smtplib")
        self.assertEqual(cfg["use_tls"], 1)
        self.assertEqual(cfg["smtp_server"], "smtp.gmail.com")

    def test_read_config_missing_required_returns_none(self):
        self.assertIsNone(ac_email._read_smtp_config({"ASSETCORE_SMTP_SERVER": "smtp.gmail.com"}))
        self.assertIsNone(ac_email._read_smtp_config({}))


class TestConfigureOutgoingEmail(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._orig_name = ac_email._ACCOUNT_NAME
        self._acct = f"_Test AC Email {_UID}"
        self._foreign_acct = f"_Test AC Email Foreign {_UID}"
        ac_email._ACCOUNT_NAME = self._acct
        # Snapshot các account default_outgoing thật để KHÔI PHỤC ở tearDown.
        self._pre_defaults = frappe.get_all(
            "Email Account", filters={"default_outgoing": 1}, pluck="name"
        )

    def tearDown(self):
        ac_email._ACCOUNT_NAME = self._orig_name
        for acct in (self._acct, self._foreign_acct):
            if frappe.db.exists("Email Account", acct):
                frappe.delete_doc("Email Account", acct, force=True, ignore_permissions=True)
        for name in self._pre_defaults:
            if frappe.db.exists("Email Account", name):
                frappe.db.set_value("Email Account", name, "default_outgoing", 1)
        frappe.db.commit()

    def test_skipped_when_env_missing(self):
        res = ac_email.configure_outgoing_email(env={})
        self.assertTrue(res.get("skipped"))
        self.assertFalse(frappe.db.exists("Email Account", self._acct),
                         "env thiếu → KHÔNG được tạo Email Account")

    def test_creates_single_default_outgoing_account(self):
        res = ac_email.configure_outgoing_email(env=dict(_TEST_ENV))
        self.assertTrue(res.get("configured"), res)
        self.assertTrue(frappe.db.exists("Email Account", self._acct))

        doc = frappe.get_doc("Email Account", self._acct)
        self.assertEqual(int(doc.default_outgoing), 1)
        self.assertEqual(int(doc.enable_outgoing), 1)
        self.assertEqual(int(doc.enable_incoming), 0)
        self.assertEqual(doc.smtp_server, "smtp.gmail.com")
        self.assertEqual(str(doc.smtp_port), "587")
        self.assertEqual(int(doc.use_tls), 1)

        defaults = frappe.get_all(
            "Email Account", filters={"default_outgoing": 1}, pluck="name"
        )
        self.assertEqual(defaults, [self._acct],
                         "Chỉ được có DUY NHẤT 1 Email Account default_outgoing")

    def test_idempotent_second_call(self):
        ac_email.configure_outgoing_email(env=dict(_TEST_ENV))
        res2 = ac_email.configure_outgoing_email(env=dict(_TEST_ENV))
        self.assertTrue(res2.get("configured"), res2)
        accts = frappe.get_all("Email Account", filters={"email_account_name": self._acct})
        self.assertEqual(len(accts), 1, "Chạy lại KHÔNG được tạo account trùng")

    def test_adopts_existing_account_with_same_email_id(self):
        """Site đã có Email Account CÙNG địa chỉ nhưng KHÁC tên (admin tự tạo tay).

        `email_id` là UNIQUE index → nếu upsert chỉ tra theo TÊN account, lần
        chạy setup sẽ nổ ``UniqueValidationError`` thay vì cấu hình được.
        Hành vi đúng: NHẬN account sẵn có và cập nhật vào đó.
        """
        foreign = frappe.new_doc("Email Account")
        foreign.email_account_name = self._foreign_acct
        foreign.email_id = _TEST_EMAIL
        foreign.smtp_server = "smtp.old.example.com"
        foreign.enable_outgoing = 1
        foreign.enable_incoming = 0
        foreign.insert(ignore_permissions=True)
        frappe.db.commit()

        res = ac_email.configure_outgoing_email(env=dict(_TEST_ENV))
        self.assertTrue(res.get("configured"), res)

        owners = frappe.get_all("Email Account", filters={"email_id": _TEST_EMAIL}, pluck="name")
        self.assertEqual(len(owners), 1, "KHÔNG được tạo account trùng địa chỉ gửi")
        doc = frappe.get_doc("Email Account", owners[0])
        self.assertEqual(doc.smtp_server, "smtp.gmail.com", "Phải cập nhật account sẵn có")
        self.assertEqual(int(doc.default_outgoing), 1)


class TestAfterMigrateWiring(FrappeTestCase):
    """ISS-002: site mới/migrate lại phải TỰ có Email Account gửi đi (nếu có .env)."""

    def test_after_migrate_configures_outgoing_email(self):
        src = inspect.getsource(ac_install.after_migrate)
        self.assertIn(
            "_configure_email()", src,
            "after_migrate PHẢI gọi _configure_email() để cấu hình Email Account từ .env",
        )

    def test_configure_email_never_breaks_migrate(self):
        """Lỗi cấu hình email KHÔNG được phép làm hỏng cả `bench migrate`."""
        orig = ac_email.configure_outgoing_email

        def _boom(*args, **kwargs):
            raise RuntimeError("SMTP config exploded")

        ac_email.configure_outgoing_email = _boom
        try:
            ac_install._configure_email()  # KHÔNG raise
        finally:
            ac_email.configure_outgoing_email = orig

    def test_configure_email_delegates_to_setup_module(self):
        calls: list[bool] = []
        orig = ac_email.configure_outgoing_email

        def _spy(*args, **kwargs):
            calls.append(True)
            return {"skipped": True, "reason": "test"}

        ac_email.configure_outgoing_email = _spy
        try:
            ac_install._configure_email()
        finally:
            ac_email.configure_outgoing_email = orig
        self.assertEqual(len(calls), 1, "phải gọi configure_outgoing_email đúng 1 lần")


if __name__ == "__main__":
    unittest.main()
