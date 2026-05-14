# Copyright (c) 2026, AssetCore Team
"""Standard API response envelope.

Convention BE → API → FE:

Success:
    {"success": True, "data": <payload>}

Error:
    {"success": False, "error": "<human message>", "code": "<MACHINE_CODE>",
     "http_status": <int>, "fields": {<field>: <msg>, ...}}

- `code`: machine-readable enum (xem ErrorCode). FE dùng để phân nhánh UX.
- `http_status`: HTTP status thực tế trả về (FE đọc qua axios cũng có nhưng đặt trong
  body để client gọi thủ công vẫn truy được).
- `fields`: lỗi field-level cho form (FE map vào input).

Backwards-compat: `_err(msg, code=400)` cũ trả `code` là HTTP int — vẫn hoạt động.
Khi gọi `_err(msg, code=ErrorCode.X)` (chuỗi), helper sẽ tự map sang HTTP status.
"""
from __future__ import annotations

from typing import Any, Optional


class ErrorCode:
    """Machine-readable error codes — FE phân nhánh UX dựa vào đây."""
    VALIDATION_ERROR = "VALIDATION_ERROR"           # 400 — input không hợp lệ (field-level)
    BUSINESS_RULE = "BUSINESS_RULE_VIOLATION"       # 422 — vi phạm nghiệp vụ (workflow, state, ...)
    UNAUTHORIZED = "UNAUTHORIZED"                   # 401 — chưa đăng nhập / session hết hạn
    FORBIDDEN = "FORBIDDEN"                         # 403 — đã đăng nhập nhưng thiếu quyền
    NOT_FOUND = "NOT_FOUND"                         # 404 — tài nguyên không tồn tại
    CONFLICT = "CONFLICT"                           # 409 — trùng lặp / state conflict
    INTERNAL_ERROR = "INTERNAL_ERROR"               # 500 — lỗi server không lường trước


_HTTP_FOR_CODE = {
    ErrorCode.VALIDATION_ERROR: 400,
    ErrorCode.BUSINESS_RULE: 422,
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.CONFLICT: 409,
    ErrorCode.INTERNAL_ERROR: 500,
}


def _ok(data: Any = None) -> dict:
    return {"success": True, "data": data}


def _err(
    msg: str,
    code: Any = 400,
    fields: Optional[dict] = None,
    http_status: Optional[int] = None,
    extra: Optional[dict] = None,
) -> dict:
    """
    Trả error envelope chuẩn.

    Args:
        msg: thông điệp tiếng Việt cho user.
        code: HTTP int (legacy) HOẶC chuỗi từ ErrorCode (recommended).
        fields: dict {field_name: error_message} — cho form validation.
        http_status: override HTTP code khi cần (rare).
        extra: dict các key bổ sung (vd: existing_user khi conflict 409) để FE
            render UX phong phú hơn (link "xem bản ghi đã tồn tại", ...).
    """
    if isinstance(code, int):
        # Legacy: code là HTTP status. Suy ngược ra error_code chuỗi.
        http = http_status or code
        error_code = _HTTP_TO_CODE.get(http, ErrorCode.VALIDATION_ERROR)
    else:
        error_code = str(code)
        http = http_status or _HTTP_FOR_CODE.get(error_code, 400)

    payload: dict = {
        "success": False,
        "error": msg,
        "code": error_code,
        "http_status": http,
    }
    if fields:
        payload["fields"] = fields
    if extra:
        payload.update(extra)
    return payload


_HTTP_TO_CODE = {
    400: ErrorCode.VALIDATION_ERROR,
    401: ErrorCode.UNAUTHORIZED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    409: ErrorCode.CONFLICT,
    417: ErrorCode.BUSINESS_RULE,
    422: ErrorCode.BUSINESS_RULE,
    500: ErrorCode.INTERNAL_ERROR,
}
