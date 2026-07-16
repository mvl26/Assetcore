"""TC-MOB-PROFILE — thin `mobile.v1` account wrappers (get / update / change_password).

Feature Spec `docs/features/16-tai-khoan-ho-so.md §8` · HANDOFF-account-profile-FOR-BACKEND.

100% mock (session + delegate `auth`/`user`) ⇒ XANH KHÔNG cần migrate/DB — đồng pattern
nhóm LOGIC của `test_mobile_device_token.py`. Kiểm hợp đồng:
  - PROJECTION GESLIM: `get_my_profile` chỉ trả 6 trường + `role_labels`, LOẠI web-only
    (permissions/hr_docname/imm_approval_status/profile/user_image).
  - DELEGATE: update → `auth.update_my_profile` (allowlist) + re-project (Q-C);
    change → `user.change_my_password` (single decision-maker) → map field-error + reauth.
  - CHỐNG SPOOF (§6.2): signature KHÔNG nhận `user`; `**_ignore` nuốt kwargs lạ (KHÔNG raise).
  - reauth_required (Q-A) == False.

Run: bench --site miyano run-tests --module assetcore.tests.test_mobile_profile
"""
from __future__ import annotations

import inspect
import unittest
from unittest import mock

import assetcore.api.mobile.v1.profile as prof

_SESSION_USER = "ktv@benhvien.vn"

# Web-shape envelope mà `auth.get_user_profile` trả (delegate field-gathering) — có ĐỦ
# field web-only để chứng minh wrapper LOẠI chúng khỏi MyProfile.
_WEB_ENVELOPE = {
    "success": True,
    "data": {
        "user": {
            "name": _SESSION_USER,
            "full_name": "Nguyễn Văn A",
            "email": _SESSION_USER,
            "user_image": "/files/a.png",
        },
        "roles": ["IMM Technician"],
        "profile": {
            "user": _SESSION_USER,
            "full_name": "Nguyễn Văn A",
            "email": _SESSION_USER,
            "phone": "0901234567",
            "user_image": "/files/a.png",
            "ac_department": "ER",
            "department_name": "Khoa Cấp cứu",
            "imm_approval_status": "Approved",
            "designation": "Kỹ thuật viên",
            "hr_docname": "HR-EMP-0001",
        },
        "permissions": {"is_admin": False, "can_approve": True},
    },
}

_MY_PROFILE_KEYS = {
    "full_name", "email", "phone", "roles", "role_labels", "department", "department_name",
}
_WEB_ONLY_FORBIDDEN = {
    "permissions", "hr_docname", "imm_approval_status", "designation", "user_image", "profile",
}


def _session(user=_SESSION_USER):
    """Context-manager patch `profile.frappe.session.user`."""
    m = mock.patch.object(prof.frappe, "session")
    started = m.start()
    started.user = user
    return m


class TestGetMyProfileProjection(unittest.TestCase):
    """get_my_profile — GESLIM projection + anti web-only leak."""

    def test_projects_exact_myprofile_keys(self) -> None:
        m = _session()
        try:
            with mock.patch.object(prof._auth, "get_user_profile", return_value=_WEB_ENVELOPE):
                body = prof.get_my_profile()
        finally:
            m.stop()
        self.assertTrue(body["success"])
        data = body["data"]
        self.assertEqual(set(data.keys()), _MY_PROFILE_KEYS,
                         "MyProfile phải ĐÚNG 6 trường + role_labels (KHÔNG dư/thiếu)")
        # Anti-leak: KHÔNG rò field web-only.
        for k in _WEB_ONLY_FORBIDDEN:
            self.assertNotIn(k, data, f"web-only field `{k}` KHÔNG được rò ra MyProfile")

    def test_field_mapping_and_role_labels(self) -> None:
        m = _session()
        try:
            with mock.patch.object(prof._auth, "get_user_profile", return_value=_WEB_ENVELOPE):
                data = prof.get_my_profile()["data"]
        finally:
            m.stop()
        self.assertEqual(data["full_name"], "Nguyễn Văn A")
        self.assertEqual(data["email"], _SESSION_USER)
        self.assertEqual(data["phone"], "0901234567", "phone ← User.phone (KHÔNG mobile_no)")
        self.assertEqual(data["roles"], ["IMM Technician"], "roles = IMM-prefixed máy")
        self.assertEqual(data["department"], "ER", "department ← User.ac_department (Link id)")
        self.assertEqual(data["department_name"], "Khoa Cấp cứu")
        # role_labels = nhãn VN song song roles[] (KHÔNG hard-code map ở mobile).
        self.assertEqual(len(data["role_labels"]), len(data["roles"]))
        self.assertTrue(all(isinstance(x, str) and x for x in data["role_labels"]))
        self.assertEqual(data["role_labels"], [prof._role_label("IMM Technician")])

    def test_null_fields_preserved(self) -> None:
        """phone/department/department_name None + roles rỗng → giữ null + role_labels=[]."""
        env = {
            "success": True,
            "data": {
                "user": {"full_name": "Điều Dưỡng B", "email": "dd@bv.vn"},
                "roles": [],
                "profile": {"phone": None, "ac_department": None, "department_name": None},
            },
        }
        m = _session()
        try:
            with mock.patch.object(prof._auth, "get_user_profile", return_value=env):
                data = prof.get_my_profile()["data"]
        finally:
            m.stop()
        self.assertIsNone(data["phone"])
        self.assertIsNone(data["department"])
        self.assertIsNone(data["department_name"])
        self.assertEqual(data["roles"], [])
        self.assertEqual(data["role_labels"], [])

    def test_guest_returns_unauthorized(self) -> None:
        m = _session(user="Guest")
        try:
            body = prof.get_my_profile()
        finally:
            m.stop()
        self.assertFalse(body["success"])
        self.assertEqual(body["code"], "UNAUTHORIZED")
        self.assertEqual(body["http_status"], 401)


class TestUpdateMyProfile(unittest.TestCase):
    """update_my_profile — delegate + re-project ĐẦY ĐỦ (Q-C) + spoof-ignored."""

    def test_happy_returns_full_myprofile(self) -> None:
        """Delegate success → trả LẠI MyProfile đầy đủ (KHÔNG chỉ updated_fields)."""
        m = _session()
        try:
            with mock.patch.object(prof._auth, "update_my_profile",
                                   return_value={"success": True, "data": {"updated_fields": ["phone"]}}) as mupd, \
                    mock.patch.object(prof._auth, "get_user_profile", return_value=_WEB_ENVELOPE):
                body = prof.update_my_profile(full_name="Nguyễn Văn A", phone="0900000000")
        finally:
            m.stop()
        self.assertTrue(mupd.called, "PHẢI delegate auth.update_my_profile (KHÔNG reimplement)")
        self.assertTrue(body["success"])
        self.assertEqual(set(body["data"].keys()), _MY_PROFILE_KEYS,
                         "success trả MyProfile đầy đủ (Q-C) cùng shape get_my_profile")

    def test_spoof_kwargs_ignored_no_raise(self) -> None:
        """Nhồi `user`/`department`/`roles` lạ → **_ignore nuốt, KHÔNG raise; target = session."""
        m = _session()
        try:
            with mock.patch.object(prof._auth, "update_my_profile",
                                   return_value={"success": True, "data": {}}), \
                    mock.patch.object(prof._auth, "get_user_profile", return_value=_WEB_ENVELOPE):
                # kwargs lạ KHÔNG được gây TypeError.
                body = prof.update_my_profile(
                    full_name="X", phone="Y",
                    user="victim@evil.com", department="HACK", roles=["IMM Super Admin"],
                )
        finally:
            m.stop()
        self.assertTrue(body["success"])
        # Re-project theo session user (đã ép) — email == session envelope, KHÔNG victim.
        self.assertEqual(body["data"]["email"], _SESSION_USER)

    def test_delegate_business_error_becomes_validation(self) -> None:
        """Delegate trả success:false (vd không có trường) → chuẩn hoá VALIDATION."""
        m = _session()
        try:
            with mock.patch.object(
                prof._auth, "update_my_profile",
                return_value={"success": False, "error": "Không có trường nào được cập nhật",
                              "code": "VALIDATION_ERROR", "http_status": 400},
            ):
                body = prof.update_my_profile()
        finally:
            m.stop()
        self.assertFalse(body["success"])
        self.assertEqual(body["code"], "VALIDATION")
        self.assertEqual(body["http_status"], 422)

    def test_doctype_validation_error_surfaced_inline(self) -> None:
        """Doctype raise ValidationError → _err(VALIDATION) inline (KHÔNG lưu im lặng BR-FIX-09)."""
        import frappe
        m = _session()
        try:
            with mock.patch.object(prof._auth, "update_my_profile",
                                   side_effect=frappe.ValidationError("Số điện thoại không hợp lệ")):
                body = prof.update_my_profile(phone="abc")
        finally:
            m.stop()
        self.assertFalse(body["success"])
        self.assertEqual(body["code"], "VALIDATION")
        self.assertIn("phone", body.get("fields", {}), "message nhắc 'điện thoại' → gán ô phone")


class TestChangeMyPassword(unittest.TestCase):
    """change_my_password — delegate user.change_my_password + map field-error + reauth."""

    def test_happy_reauth_false(self) -> None:
        """Delegate success → {reauth_required: False} (Q-A: sid hiện tại còn hợp lệ)."""
        m = _session()
        try:
            with mock.patch.object(prof._user, "change_my_password",
                                   return_value={"success": True, "data": {"user": _SESSION_USER}}) as mdel:
                body = prof.change_my_password(old_password="OldPass123", new_password="NewPass123")
        finally:
            m.stop()
        self.assertTrue(mdel.called, "PHẢI delegate user.change_my_password")
        self.assertTrue(body["success"])
        self.assertEqual(body["data"], {"reauth_required": False})

    def test_wrong_old_password_routes_old_field(self) -> None:
        """Delegate fail + len(new)≥8 + old≠new → fields.old_password (sai mật khẩu cũ)."""
        m = _session()
        try:
            with mock.patch.object(
                prof._user, "change_my_password",
                return_value={"success": False, "error": "Mật khẩu hiện tại không đúng",
                              "code": "VALIDATION_ERROR", "http_status": 400},
            ):
                body = prof.change_my_password(old_password="WrongOld1", new_password="NewPass123")
        finally:
            m.stop()
        self.assertFalse(body["success"])
        self.assertEqual(body["code"], "VALIDATION")
        self.assertEqual(body["http_status"], 422)
        self.assertEqual(body["fields"], {"old_password": prof._MSG_WRONG_OLD})

    def test_weak_new_password_routes_new_field(self) -> None:
        """len(new)<8 + delegate fail → fields.new_password (mật khẩu yếu)."""
        m = _session()
        try:
            with mock.patch.object(
                prof._user, "change_my_password",
                return_value={"success": False, "error": "Mật khẩu mới phải tối thiểu 8 ký tự",
                              "code": "VALIDATION_ERROR", "http_status": 400},
            ):
                body = prof.change_my_password(old_password="OldPass123", new_password="short")
        finally:
            m.stop()
        self.assertEqual(body["fields"], {"new_password": prof._MSG_WEAK})

    def test_same_new_password_routes_new_field(self) -> None:
        """old==new (len≥8) + delegate fail → fields.new_password (trùng cũ)."""
        m = _session()
        try:
            with mock.patch.object(
                prof._user, "change_my_password",
                return_value={"success": False, "error": "Mật khẩu mới phải khác mật khẩu cũ",
                              "code": "VALIDATION_ERROR", "http_status": 400},
            ):
                body = prof.change_my_password(old_password="SamePass123", new_password="SamePass123")
        finally:
            m.stop()
        self.assertEqual(body["fields"], {"new_password": prof._MSG_SAME})

    def test_spoof_kwargs_ignored_no_raise(self) -> None:
        """Nhồi `user` lạ → **_ignore nuốt, KHÔNG raise; delegate vẫn chạy trên session."""
        m = _session()
        try:
            with mock.patch.object(prof._user, "change_my_password",
                                   return_value={"success": True, "data": {}}):
                body = prof.change_my_password(
                    old_password="OldPass123", new_password="NewPass123",
                    user="victim@evil.com",
                )
        finally:
            m.stop()
        self.assertTrue(body["success"])

    def test_password_not_echoed_in_response(self) -> None:
        """Response KHÔNG chứa old/new password (§7 KHÔNG echo/persist)."""
        m = _session()
        try:
            with mock.patch.object(prof._user, "change_my_password",
                                   return_value={"success": True, "data": {}}):
                body = prof.change_my_password(old_password="OldPass123", new_password="Secret789")
        finally:
            m.stop()
        blob = str(body)
        self.assertNotIn("Secret789", blob, "new_password KHÔNG được echo ra response")
        self.assertNotIn("OldPass123", blob, "old_password KHÔNG được echo ra response")

    def test_guest_returns_unauthorized(self) -> None:
        m = _session(user="Guest")
        try:
            body = prof.change_my_password(old_password="x", new_password="y")
        finally:
            m.stop()
        self.assertFalse(body["success"])
        self.assertEqual(body["code"], "UNAUTHORIZED")


class TestAntiSpoofSignatures(unittest.TestCase):
    """§6.2 — signature 3 wrapper KHÔNG nhận `user` (ép frappe.session.user)."""

    def test_no_user_param_in_any_signature(self) -> None:
        for fn in (prof.get_my_profile, prof.update_my_profile, prof.change_my_password):
            sig = inspect.signature(fn)
            self.assertNotIn(
                "user", sig.parameters,
                f"{fn.__name__} KHÔNG được nhận tham số `user` (chống spoof §6.2)",
            )

    def test_write_wrappers_swallow_unknown_kwargs(self) -> None:
        """update/change có **_ignore (VAR_KEYWORD) — nuốt kwargs lạ, KHÔNG TypeError."""
        for fn in (prof.update_my_profile, prof.change_my_password):
            kinds = {p.kind for p in inspect.signature(fn).parameters.values()}
            self.assertIn(inspect.Parameter.VAR_KEYWORD, kinds,
                          f"{fn.__name__} phải có **_ignore (nuốt kwargs lạ)")


if __name__ == "__main__":
    unittest.main()
