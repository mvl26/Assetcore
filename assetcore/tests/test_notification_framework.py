# Copyright (c) 2026, AssetCore Team
"""Notification Framework — unit tests.

Run: bench --site miyano run-tests --module assetcore.tests.test_notification_framework

Covers:
- `utils/messages.py` registry: MSG constants, MESSAGES dict, lookup_message,
  format_message (template render, missing context fallback).
- `utils/notify.py`: nthrow() raises ServiceError với resolved message,
  message_code, context, http_status.
- `utils/response.py:_err()`: envelope mở rộng có message_code, context,
  action_hint, severity, title khi truyền các kwargs mới.
- Integration: ServiceError → _handle (shared api_handler) → envelope đầy đủ.

Triết lý: viết FAILING TEST trước — implementation chưa có sẽ ImportError → TDD
đúng quy trình CLAUDE.md §17.
"""
from __future__ import annotations

import unittest

# ─── Tier 1: Registry (utils/messages.py) ─────────────────────────────────────


class TestMessageRegistry(unittest.TestCase):
    """Registry phải cung cấp MSG constants + MESSAGES dict + lookup helpers."""

    def test_msg_class_exposes_constants(self):
        from assetcore.utils.messages import MSG
        # Bắt buộc có ít nhất các code system + validation cơ bản.
        self.assertTrue(hasattr(MSG, "SYS_500"))
        self.assertTrue(hasattr(MSG, "VAL_REQUIRED"))
        self.assertEqual(MSG.SYS_500, "SYS-500")

    def test_messages_dict_has_required_fields(self):
        """Mọi entry trong MESSAGES phải đầy đủ keys: title, template,
        action_hint (có thể empty), severity, http_status."""
        from assetcore.utils.messages import MESSAGES
        self.assertGreater(len(MESSAGES), 0, "MESSAGES dict rỗng")
        valid_severities = {"error", "warning", "info", "success", "critical"}
        valid_http = {200, 400, 401, 403, 404, 409, 422, 429, 500}
        for code, entry in MESSAGES.items():
            with self.subTest(code=code):
                self.assertIn("title", entry)
                self.assertIn("template", entry)
                self.assertIn("severity", entry)
                self.assertIn("http_status", entry)
                self.assertTrue(entry["title"], f"{code}: title empty")
                self.assertTrue(entry["template"], f"{code}: template empty")
                self.assertIn(entry["severity"], valid_severities,
                              f"{code}: invalid severity {entry['severity']!r}")
                self.assertIn(entry["http_status"], valid_http,
                              f"{code}: invalid http_status {entry['http_status']}")

    def test_lookup_message_returns_template(self):
        from assetcore.utils.messages import MSG, lookup_message
        entry = lookup_message(MSG.SYS_500)
        self.assertEqual(entry["http_status"], 500)
        self.assertEqual(entry["severity"], "error")

    def test_lookup_message_unknown_code_falls_back_to_sys_500(self):
        from assetcore.utils.messages import MESSAGES, MSG, lookup_message
        entry = lookup_message("NONEXISTENT-XYZ-999")
        # Fallback an toàn — không leak code lạ
        self.assertEqual(entry, MESSAGES[MSG.SYS_500])

    def test_format_message_renders_template_with_context(self):
        from assetcore.utils.messages import MSG, format_message
        title, message, entry = format_message(MSG.VAL_REQUIRED, {"field": "Ngày sinh"})
        self.assertIn("Ngày sinh", message)
        self.assertEqual(entry["severity"], "warning")

    def test_format_message_missing_context_key_does_not_crash(self):
        """Khi template có {var} mà context thiếu — KHÔNG được crash flow."""
        from assetcore.utils.messages import MSG, format_message
        # VAL_REQUIRED expects {field} → truyền context rỗng
        title, message, _entry = format_message(MSG.VAL_REQUIRED, {})
        # Phải vẫn trả về string (raw template hoặc placeholder), không raise.
        self.assertIsInstance(message, str)
        self.assertTrue(message)


# ─── Tier 2: ServiceError + nthrow (utils/notify.py) ──────────────────────────


class TestNthrow(unittest.TestCase):
    """nthrow(code, **ctx) phải raise ServiceError đã render message + carry
    message_code/context cho API layer pickup."""

    def test_nthrow_raises_service_error(self):
        from assetcore.services.shared import ServiceError
        from assetcore.utils.messages import MSG
        from assetcore.utils.notify import nthrow
        with self.assertRaises(ServiceError) as cm:
            nthrow(MSG.VAL_REQUIRED, field="Ngày sinh")
        e = cm.exception
        self.assertIn("Ngày sinh", e.message)
        self.assertEqual(e.message_code, MSG.VAL_REQUIRED)
        self.assertEqual(e.context, {"field": "Ngày sinh"})
        self.assertEqual(e.http_status, 422)

    def test_nthrow_unknown_code_falls_back_to_sys_500(self):
        from assetcore.services.shared import ServiceError
        from assetcore.utils.notify import nthrow
        with self.assertRaises(ServiceError) as cm:
            nthrow("DOES-NOT-EXIST")
        # Fallback → SYS-500 → http 500
        self.assertEqual(cm.exception.http_status, 500)


# ─── Tier 3: Envelope shape (_err) ────────────────────────────────────────────


class TestErrorEnvelope(unittest.TestCase):
    """_err() phải accept các kwargs notification framework và include vào payload."""

    def test_err_envelope_includes_notification_fields(self):
        from assetcore.utils.response import ErrorCode, _err
        payload = _err(
            "Trường Ngày sinh chưa được điền.",
            ErrorCode.VALIDATION,
            message_code="VAL-REQUIRED",
            context={"field": "Ngày sinh"},
            action_hint="Vui lòng điền đầy đủ trước khi lưu.",
            severity="warning",
            title="Thiếu thông tin bắt buộc",
        )
        self.assertEqual(payload["success"], False)
        self.assertEqual(payload["code"], ErrorCode.VALIDATION)
        self.assertEqual(payload["http_status"], 422)
        self.assertEqual(payload["message_code"], "VAL-REQUIRED")
        self.assertEqual(payload["context"], {"field": "Ngày sinh"})
        self.assertEqual(payload["action_hint"], "Vui lòng điền đầy đủ trước khi lưu.")
        self.assertEqual(payload["severity"], "warning")
        self.assertEqual(payload["title"], "Thiếu thông tin bắt buộc")

    def test_err_legacy_signature_still_works(self):
        """Backwards-compat: gọi _err(msg, http_int) vẫn trả envelope hợp lệ."""
        from assetcore.utils.response import _err
        payload = _err("Đã có lỗi", 400)
        self.assertEqual(payload["success"], False)
        self.assertEqual(payload["http_status"], 400)
        # Không có notification fields → không xuất hiện trong payload
        self.assertNotIn("message_code", payload)
        self.assertNotIn("context", payload)


# ─── Tier 4: end-to-end demo — IMM-04 nthrow() reaches FE envelope ──────────


class TestImm04DemoIntegration(unittest.TestCase):
    """Verify Phase 1 demo wire: IMM-04 service raise nthrow → api _handle hydrate
    envelope đầy đủ (message_code, context, action_hint, severity, title)."""

    def test_get_form_context_not_found_returns_full_envelope(self):
        from assetcore.api.imm04 import get_form_context
        from assetcore.utils.messages import MSG, lookup_message
        # Gọi với name không tồn tại → service raise nthrow(MSG.IMM04_NOT_FOUND)
        resp = get_form_context("ASSET-COMMISSIONING-NONEXISTENT-XYZ-999")
        self.assertFalse(resp["success"])
        self.assertEqual(resp["message_code"], MSG.IMM04_NOT_FOUND)
        self.assertEqual(resp["context"], {"name": "ASSET-COMMISSIONING-NONEXISTENT-XYZ-999"})
        entry = lookup_message(MSG.IMM04_NOT_FOUND)
        self.assertEqual(resp["severity"], entry["severity"])
        self.assertEqual(resp["title"], entry["title"])
        self.assertEqual(resp["action_hint"], entry["action_hint"])
        self.assertIn("ASSET-COMMISSIONING-NONEXISTENT-XYZ-999", resp["error"])


# ─── Tier 5: api_handler integration ──────────────────────────────────────────


class TestApiHandler(unittest.TestCase):
    """Shared handle() phải resolve ServiceError → envelope đầy đủ khi có
    message_code (look up từ registry để get action_hint, severity, title)."""

    def test_handle_resolves_message_code_to_full_envelope(self):
        from assetcore.utils.api_handler import handle
        from assetcore.utils.messages import MSG
        from assetcore.utils.notify import nthrow

        def fn():
            nthrow(MSG.VAL_REQUIRED, field="Email")

        payload = handle(fn)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["message_code"], MSG.VAL_REQUIRED)
        self.assertEqual(payload["context"], {"field": "Email"})
        self.assertIn("Email", payload["error"])
        # severity/title/action_hint resolved từ registry, không phải caller truyền
        self.assertEqual(payload["severity"], "warning")
        self.assertTrue(payload["action_hint"])
        self.assertTrue(payload["title"])

    def test_handle_ok_path_returns_envelope(self):
        from assetcore.utils.api_handler import handle
        payload = handle(lambda: {"x": 1})
        self.assertTrue(payload["success"])
        self.assertEqual(payload["data"], {"x": 1})

    def test_handle_legacy_service_error_without_message_code(self):
        """ServiceError raised theo cách cũ (không có message_code) vẫn trả
        envelope hợp lệ — chỉ thiếu trường notification."""
        from assetcore.services.shared import ErrorCode, ServiceError
        from assetcore.utils.api_handler import handle

        def fn():
            raise ServiceError(ErrorCode.NOT_FOUND, "Không tìm thấy", http_status=404)

        payload = handle(fn)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["code"], ErrorCode.NOT_FOUND)
        self.assertEqual(payload["http_status"], 404)
        self.assertEqual(payload["error"], "Không tìm thấy")
        self.assertNotIn("message_code", payload)
