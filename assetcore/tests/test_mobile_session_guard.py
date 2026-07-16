"""TC-MOB-SESSION-GUARD — ``before_request`` nâng phiên mobile hết hạn 403 → 401.

Đóng dead-end mobile B1: interceptor axios CHỈ logout khi HTTP **401**, nhưng ``sid``
hết hạn → Frappe hạ Guest → dispatcher ``is_whitelisted`` ném ``PermissionError`` (403)
KHÔNG phân biệt được với "thiếu quyền/role". Guard ``enforce_authenticated_session``
(``assetcore/api/session_guard.py``) nâng 403→401 CHỈ cho phiên-hết-hạn trên
``assetcore.api.*``, KHÔNG đụng: user còn phiên thiếu quyền · guest thật · allow_guest.

100% mock môi trường request (``frappe.local``/``session``/``get_attr``/``guest_methods``)
⇒ XANH KHÔNG cần DB — đồng pattern nhóm LOGIC ``test_mobile_profile.py``.

Run: bench --site miyano run-tests --module assetcore.tests.test_mobile_session_guard
"""
from __future__ import annotations

import types
import unittest
from unittest import mock

import frappe

import assetcore.api.session_guard as sg

_PROTECTED = "/api/method/assetcore.api.mobile.v1.get_my_profile"
_ALLOW_GUEST = "/api/method/assetcore.api.auth.login"

# Sentinel "hàm" đại diện cho method resolve được (identity so khớp guest_methods).
_FN = object()


def _run(
    path: str,
    *,
    user: str,
    session_expired: bool,
    method: str = "GET",
    resolves_to=_FN,
    guest_methods=(),
):
    """Chạy guard với môi trường request giả; trả về (hoặc raise SessionExpired).

    CHỈ override ``request``/``response`` trên ``frappe.local`` THẬT (giữ ``cache``/``lang``
    để ``_()`` translation trong nhánh raise vẫn chạy) rồi khôi phục ở ``finally``.
    """
    real_local = frappe.local
    saved_request = getattr(real_local, "request", None)
    saved_response = getattr(real_local, "response", None)
    real_local.request = types.SimpleNamespace(path=path, method=method)
    real_local.response = {"session_expired": 1} if session_expired else {}
    fake_session = types.SimpleNamespace(user=user)

    def _get_attr(_dotted):
        if resolves_to is None:
            raise AttributeError(_dotted)
        return resolves_to

    try:
        with mock.patch.object(sg.frappe, "session", fake_session), mock.patch.object(
            sg.frappe, "get_attr", _get_attr
        ), mock.patch.object(sg.frappe, "guest_methods", list(guest_methods)):
            return sg.enforce_authenticated_session()
    finally:
        real_local.request = saved_request
        real_local.response = saved_response


class TestSessionGuardRaises401(unittest.TestCase):
    def test_expired_session_protected_method_raises_session_expired(self):
        """sid hết hạn (Guest + session_expired) trên endpoint bảo vệ → 401."""
        with self.assertRaises(frappe.SessionExpired) as ctx:
            _run(_PROTECTED, user="Guest", session_expired=True, guest_methods=[])
        # SessionExpired map sang HTTP 401 (frappe/exceptions.py).
        self.assertEqual(ctx.exception.http_status_code, 401)


class TestSessionGuardLeavesUntouched(unittest.TestCase):
    def test_authenticated_but_forbidden_not_logged_out(self):
        """User CÒN phiên nhưng thiếu quyền/role (user != Guest) → guard im lặng → vẫn 403."""
        self.assertIsNone(
            _run(_PROTECTED, user="ktv@benhvien.vn", session_expired=False, guest_methods=[])
        )
        # Ngay cả khi (giả định biên) có cờ session_expired mà user vẫn hợp lệ → không đụng.
        self.assertIsNone(
            _run(_PROTECTED, user="ktv@benhvien.vn", session_expired=True, guest_methods=[])
        )

    def test_genuine_guest_without_expired_flag_not_touched(self):
        """Guest THẬT (không gửi cookie → không có cờ session_expired) → luồng dispatcher cũ (403)."""
        self.assertIsNone(
            _run(_PROTECTED, user="Guest", session_expired=False, guest_methods=[])
        )

    def test_allow_guest_method_not_touched_even_with_stale_cookie(self):
        """Endpoint allow_guest (login/probe phiên) + sid cũ → KHÔNG ép 401 (giữ login page work)."""
        self.assertIsNone(
            _run(
                _ALLOW_GUEST,
                user="Guest",
                session_expired=True,
                resolves_to=_FN,
                guest_methods=[_FN],  # _FN ∈ guest_methods ⇒ allow_guest
            )
        )

    def test_non_assetcore_api_path_not_touched(self):
        """Method ngoài `assetcore.api.*` (vd frappe core) → không thuộc phạm vi guard."""
        self.assertIsNone(
            _run(
                "/api/method/frappe.client.get_list",
                user="Guest",
                session_expired=True,
                guest_methods=[],
            )
        )

    def test_options_preflight_not_touched(self):
        """CORS preflight OPTIONS → bỏ qua (không có phiên vẫn hợp lệ)."""
        self.assertIsNone(
            _run(_PROTECTED, user="Guest", session_expired=True, method="OPTIONS", guest_methods=[])
        )

    def test_unresolvable_method_not_forced_to_401(self):
        """Method không resolve được → thận trọng KHÔNG ép 401 (nhường dispatcher xử)."""
        self.assertIsNone(
            _run(_PROTECTED, user="Guest", session_expired=True, resolves_to=None, guest_methods=[])
        )


class TestSessionGuardHelpers(unittest.TestCase):
    def test_method_allows_guest_true_for_guest_method(self):
        with mock.patch.object(sg.frappe, "get_attr", lambda _p: _FN), mock.patch.object(
            sg.frappe, "guest_methods", [_FN]
        ):
            self.assertTrue(sg._method_allows_guest("assetcore.api.auth.login"))

    def test_method_allows_guest_false_for_protected_method(self):
        with mock.patch.object(sg.frappe, "get_attr", lambda _p: _FN), mock.patch.object(
            sg.frappe, "guest_methods", []
        ):
            self.assertFalse(
                sg._method_allows_guest("assetcore.api.mobile.v1.get_my_profile")
            )

    def test_method_allows_guest_true_when_unresolvable(self):
        def _boom(_p):
            raise AttributeError(_p)

        with mock.patch.object(sg.frappe, "get_attr", _boom):
            self.assertTrue(sg._method_allows_guest("assetcore.api.does.not.exist"))


class TestSessionGuardHookRegistered(unittest.TestCase):
    def test_before_request_hook_wired(self):
        """hooks.py phải đăng ký guard vào `before_request` để app.py gọi thật."""
        self.assertIn(
            "assetcore.api.session_guard.enforce_authenticated_session",
            frappe.get_hooks("before_request"),
        )


if __name__ == "__main__":
    unittest.main()
