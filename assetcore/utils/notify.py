# Copyright (c) 2026, AssetCore Team
"""Notification helpers — entrypoint duy nhất cho service layer raise lỗi
nghiệp vụ và gửi notification chuẩn hoá.

API công khai:
    nthrow(MSG.XXX, **context)
        → raise ServiceError với message đã render + context + message_code.
        API layer (`utils/api_handler.handle`) sẽ pickup và emit envelope đầy đủ.

    nthrow_in_hook(MSG.XXX, **context)
        → dành cho Frappe DocType hook (validate/on_submit/...) — convert sang
        `frappe.ValidationError` để Frappe tự handle (HTTP 417). Đây là adapter
        cho code chạy ngoài API layer.

    format(MSG.XXX, **context) → (title, message, entry)
        → render template không raise. Dùng cho composer email/sms/notification
        record.

Phase 1 nguyên tắc:
    - Service code KHÔNG gọi `frappe.throw()` trực tiếp.
    - Service code KHÔNG hardcode tiếng Việt trong raise/log message hiển thị
      cho user — luôn qua MSG.XXX.
"""
from __future__ import annotations

from typing import Any

from assetcore.utils.errors import ServiceError
from assetcore.utils.messages import MESSAGES, MSG, MessageEntry, format_message, lookup_message
from assetcore.utils.response import ErrorCode

# ─────────────────────────────────────────────────────────────────────────────
# HTTP-STATUS → ErrorCode BUCKET MAPPING
# Service raise nthrow(MSG.XXX) — chỉ cần MSG; bucket suy ra từ entry.http_status.
# ─────────────────────────────────────────────────────────────────────────────

_HTTP_TO_BUCKET = {
    400: ErrorCode.INVALID_PARAMS,
    401: ErrorCode.UNAUTHORIZED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    409: ErrorCode.CONFLICT,
    422: ErrorCode.BUSINESS_RULE,
    429: ErrorCode.RATE_LIMITED,
    500: ErrorCode.INTERNAL,
}


def _bucket_for(entry: MessageEntry, override: str | None = None) -> str:
    """Suy ra ErrorCode bucket từ http_status của entry, hoặc dùng override."""
    if override:
        return override
    return _HTTP_TO_BUCKET.get(entry["http_status"], ErrorCode.VALIDATION)


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────


def nthrow(message_code: str, *, error_code: str | None = None,
           fields: dict | None = None, **context: Any) -> None:
    """Raise ServiceError chuẩn — entrypoint cho service layer.

    Args:
        message_code: MSG.XXX từ registry. Nếu code không tồn tại → fallback SYS-500.
        error_code: override ErrorCode bucket (rare — dùng khi mapping HTTP→bucket
            mặc định không khớp với UX mong muốn của caller).
        fields: dict {khoá ô nhập: câu tiếng Việt} — lỗi FIELD-LEVEL (AC-CR-83).
            Truyền thẳng xuống `ServiceError(fields=…)`; `utils/api_handler.handle`
            đẩy vào envelope `fields` (chỉ khi truthy) → FE neo thông điệp dưới
            ĐÚNG control. Khoá dùng TÊN THAM SỐ GHI của endpoint (ADR-IMM12-14),
            KHÔNG dùng tên field DocType để đọc.
            ⚠️ `fields` là TÊN DÀNH RIÊNG — không dùng được làm biến template
            `{fields}` (hiện 0 entry registry dùng biến đó).
        **context: biến cho template `{var}` placeholder. Sẽ:
            - render vào message (str.format)
            - propagate xuống FE qua envelope `context` field để i18n hoá

    Raises:
        ServiceError: luôn luôn — đây là entrypoint raise.

    Example:
        nthrow(MSG.IMM04_VENDOR_NOT_ASSIGNED, asset="AC-0001")
        nthrow(MSG.VAL_REQUIRED, field="Ngày sinh")
    """
    title, message, entry = format_message(message_code, context)
    bucket = _bucket_for(entry, error_code)
    raise ServiceError(
        code=bucket,
        message=message,
        http_status=entry["http_status"],
        context=context,
        message_code=message_code,
        fields=fields,
    )


def nthrow_in_hook(message_code: str, **context: Any) -> None:
    """Raise lỗi từ Frappe DocType hook (validate/on_submit/before_insert/...).

    Frappe hook KHÔNG đi qua API `_handle` decorator nên `ServiceError` sẽ propagate
    thành HTTP 500. Adapter này convert sang `frappe.ValidationError` (HTTP 417)
    để Frappe tự handle envelope theo legacy convention. FE axios interceptor đã
    parse `_server_messages` cho 417/422 → toast vẫn hiển thị đúng.

    KHÔNG dùng trong service / API layer thông thường — chỉ DocType hook.
    """
    import frappe

    title, message, _entry = format_message(message_code, context)
    # Frappe sẽ throw ValidationError → HTTP 417 → axios interceptor → ApiError.
    # Đính kèm message_code vào response để FE có thể hydrate lại registry.
    if hasattr(frappe.local, "response") and frappe.local.response is not None:
        frappe.local.response["message_code"] = message_code
        frappe.local.response["context"] = context
    frappe.throw(msg=message, title=title, exc=frappe.ValidationError)


def render(message_code: str, **context: Any) -> tuple[str, str, MessageEntry]:
    """Render template không raise — dùng cho email/sms composer.

    Returns: (title, rendered_message, entry).
    """
    return format_message(message_code, context)


__all__ = [
    "MSG",
    "MESSAGES",
    "MessageEntry",
    "lookup_message",
    "nthrow",
    "nthrow_in_hook",
    "render",
]
