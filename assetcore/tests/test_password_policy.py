# Copyright (c) 2026, AssetCore Team
"""IMM-00 — Thông điệp mật khẩu yếu phải là tiếng Việt, KHÔNG phải HTML của Frappe.

Bug (user báo 2026-07-22, màn ``/user-profiles/new``): nhập mật khẩu dễ đoán →
UI hiện nguyên khối HTML tiếng Anh do Frappe dựng
(``frappe/core/doctype/user/user.py:1207 handle_password_test_fail``)::

    <div class="alert alert-warning" role="alert">This is a top-100 common
    password.</div><ul style="margin: 0; padding-left: 1em;"><li>All-uppercase
    is almost as easy to guess as all-lowercase.</li></ul>

Nguyên nhân: ``create_system_user`` chỉ kiểm tra ĐỘ DÀI rồi gán ``new_password``
và ``insert()`` → chính Frappe throw thông điệp thô. Ngoài ra
``auth._validate_new_password`` tuy có câu tiếng Việt nhưng vẫn NỐI THÊM chuỗi
gợi ý tiếng Anh của zxcvbn.

Khoá 3 bất biến (áp cho MỌI đường đặt mật khẩu):
  - KHÔNG có thẻ HTML trong thông điệp trả về API.
  - KHÔNG lọt chuỗi tiếng Anh của zxcvbn (tập 24 chuỗi đóng của Frappe).
  - Mật khẩu yếu bị từ chối TRƯỚC khi tạo user (không tạo user nửa vời).

Run:
    bench --site miyano run-tests --app assetcore \
        --module assetcore.tests.test_password_policy
"""
from __future__ import annotations

import re
import time
import unittest

import frappe

import assetcore.api.auth as auth_api
import assetcore.api.user as user_api
from assetcore.utils import password_policy

_UID = str(int(time.time()) % 100000)

#: Mật khẩu chắc chắn trượt chính sách (top-10 common + ALL CAPS).
_WEAK = "PASSWORD"
_STRONG = "Kt#Bv2026$Ngoc"

_HTML_TAG = re.compile(r"<[a-zA-Z/][^>]*>")

#: Toàn bộ chuỗi phản hồi zxcvbn của Frappe (frappe/utils/password_strength.py).
#: Không chuỗi nào trong số này được phép xuất hiện nguyên văn trong API response.
_FRAPPE_EN_STRINGS = [
    "Add numbers or special characters.",
    "All-uppercase is almost as easy to guess as all-lowercase.",
    "Avoid dates and years that are associated with you.",
    "Avoid sequences like abc or 6543 as they are easy to guess",
    "Avoid years that are associated with you.",
    "A word by itself is easy to guess.",
    "Better add a few more letters or another word",
    "Capitalization doesn't help very much.",
    "Common names and surnames are easy to guess.",
    "Common words are easy to guess.",
    "Dates are often easy to guess.",
    "Let's avoid repeated words and characters",
    "Make use of longer keyboard patterns",
    "Names and surnames by themselves are easy to guess.",
    "Predictable substitutions like '@' instead of 'a' don't help very much.",
    "Recent years are easy to guess.",
    "Short keyboard patterns are easy to guess",
    "Straight rows of keys are easy to guess",
    "This is a top-100 common password.",
    "This is a top-10 common password.",
    "This is a very common password.",
    "This is similar to a commonly used password.",
    "Try to avoid repeated words and characters",
    "Try to use a longer keyboard pattern with more turns",
]


def setUpModule():
    frappe.set_user("Administrator")


def _assert_clean_vi(case: unittest.TestCase, msg: str, where: str) -> None:
    """Thông điệp phải: có nội dung, không HTML, không lọt tiếng Anh zxcvbn."""
    case.assertTrue(msg, f"{where}: phải có thông điệp lỗi")
    case.assertIsNone(
        _HTML_TAG.search(msg),
        f"{where}: KHÔNG được trả HTML thô cho FE — nhận: {msg!r}",
    )
    for en in _FRAPPE_EN_STRINGS:
        case.assertNotIn(
            en, msg, f"{where}: lọt chuỗi tiếng Anh của Frappe: {en!r}"
        )


class TestFeedbackTranslation(unittest.TestCase):
    """Bảng dịch phải phủ HẾT tập chuỗi đóng của Frappe."""

    def test_every_frappe_string_has_vietnamese(self):
        missing = [en for en in _FRAPPE_EN_STRINGS if en not in password_policy.FEEDBACK_VI]
        self.assertEqual(
            missing, [], f"Thiếu bản dịch tiếng Việt cho {len(missing)} chuỗi: {missing}"
        )

    def test_translation_never_returns_english(self):
        for en in _FRAPPE_EN_STRINGS:
            vi = password_policy.FEEDBACK_VI[en]
            self.assertNotEqual(vi, en, f"Chưa dịch: {en!r}")
            self.assertIsNone(_HTML_TAG.search(vi), f"Bản dịch chứa HTML: {vi!r}")

    def test_unknown_feedback_falls_back_to_vietnamese(self):
        """Frappe nâng cấp thêm chuỗi mới → KHÔNG được lọt nguyên văn ra UI."""
        msg = password_policy.describe_feedback({
            "warning": "Some brand new english warning from a future version",
            "suggestions": ["Another unmapped english suggestion"],
        })
        _assert_clean_vi(self, msg, "describe_feedback(chuỗi lạ)")
        self.assertNotIn("brand new english", msg)

    def test_describe_feedback_empty_still_returns_vietnamese(self):
        msg = password_policy.describe_feedback({})
        _assert_clean_vi(self, msg, "describe_feedback({})")


class TestCreateSystemUserRejectsWeakPassword(unittest.TestCase):
    """Đường đi user BÁO LỖI: màn `/user-profiles/new`."""

    def setUp(self):
        frappe.set_user("Administrator")
        self.email = f"_test_pwpolicy_{_UID}@example.com"

    def tearDown(self):
        frappe.set_user("Administrator")
        if frappe.db.exists("User", self.email):
            frappe.delete_doc("User", self.email, force=True, ignore_permissions=True)
        frappe.db.commit()

    def _create(self, password: str) -> dict:
        frappe.local.form_dict = frappe._dict({
            "email": self.email,
            "first_name": "Nguyễn Văn",
            "last_name": "Yếu",
            "password": password,
        })
        return user_api.create_system_user()

    def test_weak_password_rejected_with_vietnamese_message(self):
        res = self._create(_WEAK)
        self.assertFalse(res.get("success"), f"Mật khẩu dễ đoán phải bị từ chối: {res}")
        _assert_clean_vi(self, res.get("error") or "", "create_system_user")

    def test_weak_password_does_not_create_user(self):
        self._create(_WEAK)
        self.assertFalse(
            frappe.db.exists("User", self.email),
            "Từ chối mật khẩu KHÔNG được để lại user nửa vời",
        )

    def test_field_level_error_points_at_password(self):
        res = self._create(_WEAK)
        fields = res.get("fields") or {}
        self.assertIn("password", fields,
                      "FE cần biết lỗi thuộc ô mật khẩu để highlight đúng chỗ")
        _assert_clean_vi(self, fields.get("password") or "", "fields.password")

    def test_strong_password_still_accepted(self):
        res = self._create(_STRONG)
        self.assertTrue(res.get("success"), f"Mật khẩu mạnh phải qua: {res}")


class TestOtherPasswordPathsAreVietnamese(unittest.TestCase):
    """Mọi đường đặt/đổi mật khẩu khác cũng phải sạch."""

    def setUp(self):
        frappe.set_user("Administrator")
        self.email = f"_test_pwpath_{_UID}@example.com"
        doc = frappe.new_doc("User")
        doc.email = self.email
        doc.first_name = "Trần"
        doc.last_name = "Đổi"
        doc.user_type = "System User"
        doc.enabled = 1
        doc.flags.no_welcome_mail = True
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

    def tearDown(self):
        frappe.set_user("Administrator")
        if frappe.db.exists("User", self.email):
            frappe.delete_doc("User", self.email, force=True, ignore_permissions=True)
        frappe.db.commit()

    def test_set_password_with_key_weak_is_vietnamese(self):
        key = user_api._make_set_password_link(self.email).split("key=", 1)[1]
        res = auth_api.set_password_with_key(key, _WEAK)
        self.assertFalse(res.get("success"))
        _assert_clean_vi(self, res.get("error") or "", "set_password_with_key")

    def test_reset_user_password_weak_is_vietnamese(self):
        res = user_api.reset_user_password(self.email, _WEAK)
        self.assertFalse(res.get("success"), "Admin đặt lại mật khẩu yếu phải bị chặn")
        _assert_clean_vi(self, res.get("error") or "", "reset_user_password")


if __name__ == "__main__":
    unittest.main()
