# Copyright (c) 2026, AssetCore Team
"""AUTH subsystem audit — end-to-end gate & RBAC regression.

Phủ luồng THẬT mà FE gọi (api/auth.py + api/user.py). Dead-code cũ
services/auth_service.py đã được xoá (G2/G3). Khoá các invariant bảo mật:

  - Self-signup qua API → enabled=0 + Pending (gate THẬT chặn login).
  - Approve → enabled=1 + Approved (mở gate).
  - Reject → giữ enabled=0 (gate vẫn đóng).
  - approve_registration / create_system_user / set_user_roles BẮT BUỘC admin
    (chống leo quyền — non-admin gọi phải 403).
  - Re-register email đã Rejected → CHO PHÉP (reset về Pending, G4). Email
    Pending/Approved vẫn bị chặn DUPLICATE.
  - Approve → tự gửi email kích hoạt cho user (G1, idempotent + robust).
  - check_account_status (allow_guest) NON-ENUMERABLE — luôn 'unknown', không
    leak tồn tại/trạng thái (BR-00-USR-02, security 2026-06-01).
  - account_state (allow_guest, password-gated) chỉ lộ pending/rejected/disabled/
    active SAU khi mật khẩu đúng; sai mật khẩu / email không tồn tại → đồng nhất
    'invalid_credentials' (chống user enumeration).

Run:
    bench --site miyano run-tests --app assetcore \
        --module assetcore.tests.auth.test_auth_subsystem
"""
from __future__ import annotations

import time
import unittest

import frappe
from frappe.tests.utils import FrappeTestCase


_UID = str(int(time.time()) % 100000)


def setUpModule():
    frappe.set_user("Administrator")


def _form(**kw) -> None:
    frappe.local.form_dict = frappe._dict(kw)


class _AuthBase(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._emails: list[str] = []

    def tearDown(self):
        frappe.set_user("Administrator")
        for email in self._emails:
            if frappe.db.exists("User", email):
                frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        frappe.db.commit()

    def _track(self, email: str) -> str:
        self._emails.append(email)
        return email


class TestSignupGate(_AuthBase):
    """Luồng self-signup THẬT (api/auth.register_user)."""

    def test_api_signup_creates_disabled_pending(self):
        from assetcore.api.auth import register_user

        email = self._track(f"_test_auth_signup_{_UID}@example.com")
        res = register_user(email=email, full_name="Sign Up", password="Test@12345")
        self.assertTrue(res.get("success"), res)
        self.assertEqual(int(frappe.db.get_value("User", email, "enabled")), 0,
                         "Self-signup PHẢI enabled=0 — gate thật chặn login")
        self.assertEqual(
            frappe.db.get_value("User", email, "imm_approval_status"), "Pending")

    def test_api_signup_rejects_duplicate(self):
        from assetcore.api.auth import register_user

        email = self._track(f"_test_auth_dup_{_UID}@example.com")
        register_user(email=email, full_name="Dup", password="Test@12345")
        res2 = register_user(email=email, full_name="Dup2", password="Test@12345")
        self.assertFalse(res2.get("success"), "Email trùng phải bị chặn")

    def test_reregister_after_reject_resets_to_pending(self):
        """G4: Email đã Rejected → CHO PHÉP đăng ký lại (reset về Pending).

        Security review #3: đăng ký lại PHẢI nhập đúng mật khẩu gốc để chứng
        minh quyền sở hữu (mật khẩu KHÔNG đổi). Cập nhật full_name/phone/dept;
        clear imm_rejection_reason; enabled vẫn 0 (chờ duyệt lại).
        """
        from assetcore.api.auth import register_user
        from assetcore.api.user import approve_registration

        email = self._track(f"_test_auth_rereg_{_UID}@example.com")
        register_user(email=email, full_name="Re Reg", password="Test@12345")
        _form(user=email, action="reject", rejection_reason="spam")
        approve_registration()
        self.assertEqual(int(frappe.db.get_value("User", email, "enabled")), 0)
        self.assertEqual(
            frappe.db.get_value("User", email, "imm_approval_status"), "Rejected")

        # Sai mật khẩu gốc → KHÔNG cho ghi đè, trả nhãn 'đã tồn tại' (không lộ Rejected).
        res_wrong = register_user(email=email, full_name="Hijacker",
                                  password="WrongOld@999", phone="0900000000")
        self.assertFalse(res_wrong.get("success"),
                         "Đăng ký lại với mật khẩu gốc SAI phải bị từ chối (review #3)")
        self.assertEqual(
            frappe.db.get_value("User", email, "imm_approval_status"), "Rejected",
            "Sai mật khẩu gốc → KHÔNG được reset Rejected→Pending")
        self.assertEqual(
            frappe.db.get_value("User", email, "first_name"), "Re Reg",
            "Sai mật khẩu gốc → danh tính KHÔNG bị ghi đè")

        # Đúng mật khẩu gốc → cho đăng ký lại (mật khẩu giữ nguyên).
        res = register_user(email=email, full_name="Re Reg V2",
                            password="Test@12345", phone="0911222333")
        self.assertTrue(res.get("success"),
                        "Email Rejected + đúng mật khẩu gốc PHẢI được đăng ký lại (G4)")
        self.assertEqual(
            frappe.db.get_value("User", email, "imm_approval_status"), "Pending",
            "Re-register Rejected → status reset về Pending")
        self.assertEqual(int(frappe.db.get_value("User", email, "enabled")), 0,
                         "Re-register vẫn enabled=0 — chờ duyệt lại")
        self.assertIn(
            frappe.db.get_value("User", email, "imm_rejection_reason") or "", ("", None),
            "rejection_reason phải được clear khi đăng ký lại")
        # Không tạo record trùng — vẫn đúng 1 User
        self.assertEqual(
            frappe.db.count("User", {"email": email}), 1,
            "Re-register KHÔNG được tạo record trùng")

    def test_reregister_blocked_when_approved(self):
        """G4 ranh giới: email Approved (enabled=1) vẫn bị chặn DUPLICATE."""
        from assetcore.api.auth import register_user
        from assetcore.api.user import approve_registration

        email = self._track(f"_test_auth_appr_dup_{_UID}@example.com")
        register_user(email=email, full_name="Appr Dup", password="Test@12345")
        _form(user=email, action="approve", roles="[]")
        approve_registration()
        self.assertEqual(int(frappe.db.get_value("User", email, "enabled")), 1)

        res = register_user(email=email, full_name="Hacker", password="Test@12345")
        self.assertFalse(res.get("success"),
                         "Email Approved vẫn phải bị chặn 'đã tồn tại'")

    def test_reregister_blocked_when_pending(self):
        """G4 ranh giới: email đang Pending vẫn bị chặn (chưa bị từ chối)."""
        from assetcore.api.auth import register_user

        email = self._track(f"_test_auth_pend_dup_{_UID}@example.com")
        register_user(email=email, full_name="Pend", password="Test@12345")
        res = register_user(email=email, full_name="Pend2", password="Test@12345")
        self.assertFalse(res.get("success"),
                         "Email đang Pending chưa bị từ chối → vẫn chặn duplicate")


class TestApprovalGate(_AuthBase):
    """api/user.approve_registration — approve/reject đổi đúng enabled."""

    def _signup(self, suffix: str) -> str:
        from assetcore.api.auth import register_user
        email = self._track(f"_test_auth_{suffix}_{_UID}@example.com")
        register_user(email=email, full_name=f"User {suffix}", password="Test@12345")
        return email

    def test_approve_enables_user(self):
        from assetcore.api.user import approve_registration

        email = self._signup("approve")
        _form(user=email, action="approve", roles="[]")
        res = approve_registration()
        self.assertTrue(res.get("success"), res)
        self.assertEqual(int(frappe.db.get_value("User", email, "enabled")), 1,
                         "Approve PHẢI enabled=1 — mở gate login")
        self.assertEqual(
            frappe.db.get_value("User", email, "imm_approval_status"), "Approved")

    def test_reject_keeps_disabled(self):
        from assetcore.api.user import approve_registration

        email = self._signup("reject")
        _form(user=email, action="reject", rejection_reason="thiếu giấy tờ")
        res = approve_registration()
        self.assertTrue(res.get("success"), res)
        self.assertEqual(int(frappe.db.get_value("User", email, "enabled")), 0,
                         "Reject PHẢI giữ enabled=0 — gate vẫn đóng")
        self.assertEqual(
            frappe.db.get_value("User", email, "imm_approval_status"), "Rejected")
        self.assertEqual(
            frappe.db.get_value("User", email, "imm_rejection_reason"),
            "thiếu giấy tờ")


class TestApproveActivationEmail(_AuthBase):
    """G1: approve gửi email kích hoạt cho user — idempotent + robust."""

    def _signup(self, suffix: str) -> str:
        from assetcore.api.auth import register_user
        email = self._track(f"_test_auth_{suffix}_{_UID}@example.com")
        register_user(email=email, full_name=f"User {suffix}", password="Test@12345")
        return email

    def test_approve_sends_activation_email(self):
        import assetcore.api.user as user_api

        email = self._signup("mail")
        sent: list[dict] = []
        orig = user_api._safe_sendmail
        user_api._safe_sendmail = lambda **kw: sent.append(kw)
        try:
            _form(user=email, action="approve", roles="[]")
            res = user_api.approve_registration()
        finally:
            user_api._safe_sendmail = orig

        self.assertTrue(res.get("success"), res)
        self.assertEqual(len(sent), 1, "Approve phải gửi đúng 1 email kích hoạt")
        recip = sent[0].get("recipients")
        recip = recip if isinstance(recip, list) else [recip]
        self.assertIn(email, recip, "Email kích hoạt phải gửi tới chính user")

    def test_approve_email_failure_does_not_break_approve(self):
        """Sendmail raise → approve vẫn thành công (robust)."""
        import assetcore.api.user as user_api

        email = self._signup("mailfail")

        def _boom(**kw):
            raise RuntimeError("SMTP down")

        orig = user_api._safe_sendmail
        user_api._safe_sendmail = _boom
        try:
            _form(user=email, action="approve", roles="[]")
            res = user_api.approve_registration()
        finally:
            user_api._safe_sendmail = orig

        self.assertTrue(res.get("success"),
                        "Lỗi gửi mail KHÔNG được làm fail transaction approve")
        self.assertEqual(int(frappe.db.get_value("User", email, "enabled")), 1)

    def test_approve_already_approved_is_idempotent_no_email(self):
        """Approve lại user đã Approved → KHÔNG gửi mail lần 2."""
        import assetcore.api.user as user_api

        email = self._signup("idem")
        _form(user=email, action="approve", roles="[]")
        user_api.approve_registration()

        sent: list[dict] = []
        orig = user_api._safe_sendmail
        user_api._safe_sendmail = lambda **kw: sent.append(kw)
        try:
            _form(user=email, action="approve", roles="[]")
            user_api.approve_registration()
        finally:
            user_api._safe_sendmail = orig
        self.assertEqual(len(sent), 0,
                         "Đã Approved sẵn → approve lại KHÔNG gửi mail (idempotent)")

    def test_reject_sends_no_activation_email(self):
        import assetcore.api.user as user_api

        email = self._signup("rejmail")
        sent: list[dict] = []
        orig = user_api._safe_sendmail
        user_api._safe_sendmail = lambda **kw: sent.append(kw)
        try:
            _form(user=email, action="reject", rejection_reason="x")
            user_api.approve_registration()
        finally:
            user_api._safe_sendmail = orig
        self.assertEqual(len(sent), 0, "Reject KHÔNG gửi email kích hoạt")


class TestCheckAccountStatusNonEnumerable(_AuthBase):
    """BR-00-USR-02: endpoint guest `check_account_status` KHÔNG được leak
    tồn tại/trạng thái — chống user enumeration (security finding 2026-06-01).

    Mọi email (không tồn tại / pending / rejected / disabled / active) PHẢI
    nhận CÙNG một nhãn `unknown` → guest không phân biệt được gì.
    """

    def _signup(self, suffix: str) -> str:
        from assetcore.api.auth import register_user
        email = self._track(f"_test_auth_{suffix}_{_UID}@example.com")
        register_user(email=email, full_name=f"User {suffix}", password="Test@12345")
        return email

    def test_not_found_returns_unknown(self):
        from assetcore.api.auth import check_account_status

        res = check_account_status(email=f"_nope_{_UID}@example.com")
        self.assertTrue(res.get("success"), res)
        self.assertEqual(res["data"]["status"], "unknown",
                         "Email không tồn tại PHẢI trả 'unknown' — không leak")

    def test_pending_returns_unknown(self):
        from assetcore.api.auth import check_account_status

        email = self._signup("cspend")
        res = check_account_status(email=email)
        self.assertEqual(res["data"]["status"], "unknown",
                         "Pending KHÔNG được lộ cho guest")

    def test_rejected_returns_unknown(self):
        from assetcore.api.auth import check_account_status
        from assetcore.api.user import approve_registration

        email = self._signup("csrej")
        _form(user=email, action="reject", rejection_reason="x")
        approve_registration()
        res = check_account_status(email=email)
        self.assertEqual(res["data"]["status"], "unknown",
                         "Rejected KHÔNG được lộ cho guest")

    def test_active_returns_unknown(self):
        from assetcore.api.auth import check_account_status
        from assetcore.api.user import approve_registration

        email = self._signup("csact")
        _form(user=email, action="approve", roles="[]")
        approve_registration()
        res = check_account_status(email=email)
        self.assertEqual(res["data"]["status"], "unknown",
                         "Active KHÔNG được lộ cho guest")

    def test_enumeration_closed_all_states_identical(self):
        """Bằng chứng đóng enumeration: email tồn tại và không tồn tại trả CÙNG response."""
        from assetcore.api.auth import check_account_status

        active = self._signup("csenum")
        from assetcore.api.user import approve_registration
        _form(user=active, action="approve", roles="[]")
        approve_registration()

        r_active = check_account_status(email=active)
        r_missing = check_account_status(email=f"_ghost_{_UID}@example.com")
        self.assertEqual(r_active["data"], r_missing["data"],
                         "Active và not-found PHẢI giống hệt nhau (enumeration đã đóng)")


class TestAccountStatePasswordGated(_AuthBase):
    """BR-00-USR-02: endpoint `account_state(usr, pwd)` chỉ lộ trạng thái nhạy
    cảm SAU KHI mật khẩu đúng. Sai mật khẩu / email không tồn tại → đồng nhất
    `invalid_credentials` (không enumeration).
    """

    _PWD = "Test@12345"

    def _signup(self, suffix: str) -> str:
        from assetcore.api.auth import register_user
        email = self._track(f"_test_auth_{suffix}_{_UID}@example.com")
        register_user(email=email, full_name=f"User {suffix}", password=self._PWD)
        return email

    def test_wrong_password_returns_invalid_credentials(self):
        from assetcore.api.auth import account_state

        email = self._signup("aswrong")
        # Pending user nhưng mật khẩu SAI → KHÔNG lộ 'pending', chỉ invalid_credentials.
        res = account_state(usr=email, pwd="WrongPass@999")
        self.assertTrue(res.get("success"), res)
        self.assertEqual(res["data"]["status"], "invalid_credentials",
                         "Sai mật khẩu KHÔNG được lộ trạng thái pending")

    def test_nonexistent_email_returns_invalid_credentials(self):
        from assetcore.api.auth import account_state

        res = account_state(usr=f"_nope2_{_UID}@example.com", pwd="whatever123")
        self.assertEqual(res["data"]["status"], "invalid_credentials",
                         "Email không tồn tại = sai mật khẩu (đồng nhất, không leak)")

    def test_pending_revealed_only_after_correct_password(self):
        from assetcore.api.auth import account_state

        email = self._signup("aspend")
        res = account_state(usr=email, pwd=self._PWD)
        self.assertEqual(res["data"]["status"], "pending",
                         "Mật khẩu đúng + Pending → lộ 'pending' (đúng UX)")

    def test_rejected_revealed_only_after_correct_password(self):
        from assetcore.api.auth import account_state
        from assetcore.api.user import approve_registration

        email = self._signup("asrej")
        _form(user=email, action="reject", rejection_reason="x")
        approve_registration()
        res = account_state(usr=email, pwd=self._PWD)
        self.assertEqual(res["data"]["status"], "rejected")

    def test_active_after_correct_password(self):
        from assetcore.api.auth import account_state
        from assetcore.api.user import approve_registration

        email = self._signup("asact")
        _form(user=email, action="approve", roles="[]")
        approve_registration()
        # approve_registration set enabled=1 nhưng giữ password cũ → check_password OK.
        res = account_state(usr=email, pwd=self._PWD)
        self.assertEqual(res["data"]["status"], "active")

    def test_missing_params(self):
        from assetcore.api.auth import account_state

        res = account_state(usr="", pwd="")
        self.assertFalse(res.get("success"), "Thiếu usr/pwd → lỗi 400")


class TestAuthRbac(_AuthBase):
    """Chống leo quyền: endpoint quản trị PHẢI từ chối non-admin."""

    _seq = 0

    def _make_plain_user(self) -> str:
        TestAuthRbac._seq += 1
        email = self._track(f"_test_auth_plain_{_UID}_{TestAuthRbac._seq}@example.com")
        doc = frappe.get_doc({
            "doctype": "User", "email": email, "first_name": "Plain",
            "enabled": 1, "user_type": "System User", "send_welcome_email": 0,
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return email

    def test_approve_registration_blocks_non_admin(self):
        from assetcore.api.user import approve_registration

        victim = self._make_plain_user()
        actor = self._make_plain_user()
        frappe.set_user(actor)
        _form(user=victim, action="approve", roles='["AssetCore Super Admin"]')
        res = approve_registration()
        self.assertFalse(res.get("success"),
                         "Non-admin KHÔNG được duyệt/cấp role (leo quyền)")

    def test_create_system_user_blocks_non_admin(self):
        from assetcore.api.user import create_system_user

        actor = self._make_plain_user()
        frappe.set_user(actor)
        _form(email=f"_test_auth_evil_{_UID}@example.com", first_name="Evil",
              imm_roles="[]")
        res = create_system_user()
        self.assertFalse(res.get("success"),
                         "Non-admin KHÔNG được tạo system user")

    def test_set_user_roles_blocks_self_escalation(self):
        """User KHÔNG tự gán Super Admin cho chính mình (P1 cũ — không tái phát)."""
        from assetcore.api.user import set_user_roles

        actor = self._make_plain_user()
        frappe.set_user(actor)
        with self.assertRaises(frappe.PermissionError):
            set_user_roles(actor, ["AssetCore Super Admin"])
        frappe.set_user("Administrator")
        roles = [r.role for r in frappe.get_doc("User", actor).roles]
        self.assertNotIn("AssetCore Super Admin", roles,
                         "Self-escalation KHÔNG được phép")
