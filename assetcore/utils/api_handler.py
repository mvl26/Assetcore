# Copyright (c) 2026, AssetCore Team
"""Shared API handler — wraps service calls vào envelope chuẩn.

Trước Phase 1, mỗi `assetcore/api/immXX.py` duplicate cùng một `_handle()`
function. File này consolidate logic vào một chỗ duy nhất, đồng thời thêm
notification framework hydration: khi ServiceError carry `message_code`, handler
tự tra `lookup_message()` để bổ sung `action_hint`, `severity`, `title` vào
envelope.

Usage trong `api/immXX.py`:

    from assetcore.utils.api_handler import handle, parse_json

    @frappe.whitelist()
    def list_work_orders(filters: str = "{}", page: int = 1, page_size: int = 20):
        f = parse_json(filters, default={})
        return handle(svc.list_work_orders, f, page=int(page), page_size=int(page_size))

Backwards-compat:
    Mọi `_handle(...)` định nghĩa cục bộ trong api/*.py vẫn hoạt động — file
    này KHÔNG ép migrate. Migration tới `handle()` shared sẽ xảy ra dần (Phase 4).
"""
from __future__ import annotations

import json
from typing import Any, Callable

from assetcore.utils.errors import ServiceError
from assetcore.utils.response import ErrorCode
from assetcore.utils.messages import lookup_message
from assetcore.utils.response import _err, _ok


def handle(fn: Callable, *args: Any, **kwargs: Any) -> dict:
    """Chạy service `fn(*args, **kwargs)` → wrap kết quả vào envelope chuẩn.

    Behavior:
        - Success → `_ok(<return value>)`.
        - ServiceError → `_err(message, code, http_status=..., message_code=...,
          context=..., action_hint=..., severity=..., title=...)`.
          Notification fields được auto-resolve từ `lookup_message()` khi
          ServiceError có `message_code`.

    KHÔNG bắt Exception chung — non-ServiceError exception bubble lên để Frappe
    xử lý (hoặc test framework bắt). Đây là design intent: chỉ business error
    được handle gracefully; system error phải đi qua Frappe global handler để
    log + return 500 đúng cách.
    """
    try:
        return _ok(fn(*args, **kwargs))
    except ServiceError as e:
        return _service_error_to_envelope(e)


def _service_error_to_envelope(e: ServiceError) -> dict:
    """Convert ServiceError → error envelope, hydrate notification fields từ registry."""
    # Field-level validation errors (vd upload) → envelope `fields` cho FE hiển thị
    # lỗi dưới đúng control. Rỗng → `_err` bỏ qua (không noise).
    fields = getattr(e, "fields", None) or None
    if e.message_code:
        entry = lookup_message(e.message_code)
        return _err(
            e.message,
            e.code,
            fields=fields,
            http_status=e.http_status,
            message_code=e.message_code,
            context=e.context if e.context else None,
            action_hint=entry.get("action_hint") or None,
            severity=entry.get("severity"),
            title=entry.get("title"),
        )
    # Legacy ServiceError không có message_code → envelope tối thiểu
    return _err(e.message, e.code, fields=fields, http_status=e.http_status)


# ─────────────────────────────────────────────────────────────────────────────
# parse_json — canonical version, replaces ad-hoc `_parse_json` per api file
# ─────────────────────────────────────────────────────────────────────────────


def parse_json(raw: Any, *, default: Any = None, field_name: str = "params") -> Any:
    """Parse JSON string từ query/body — raise ServiceError nếu malformed.

    Args:
        raw: input (string, dict, list, None).
        default: trả về khi `raw` là falsy.
        field_name: tên trường (cho error message dễ debug).

    Raises:
        ServiceError(INVALID_PARAMS): khi raw là str nhưng không parse được.
    """
    if not raw:
        return default if default is not None else {}
    if not isinstance(raw, str):
        return raw
    try:
        return json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise ServiceError(
            ErrorCode.INVALID_PARAMS,
            f"Tham số {field_name} không phải JSON hợp lệ",
            http_status=400,
        ) from exc
