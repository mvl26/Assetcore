# Copyright (c) 2026, AssetCore Team
"""Standard API response envelope.

Convention BE → API → FE:

Success:
    {"success": True, "data": <payload>}

Error (extended for Notification Framework — Phase 1):
    {
        "success": False,
        "error": "<human message>",
        "code": "<MACHINE_CODE>",      # ErrorCode enum (semantic bucket)
        "http_status": <int>,
        "fields": {<field>: <msg>, ...},
        # Notification framework extension — optional ↓
        "message_code": "MSG-XXX-001",  # Lookup key vào registry (utils/messages.py)
        "context": {<key>: <value>, ...},  # Biến để FE render template
        "action_hint": "<gợi ý hành động>",
        "severity": "error|warning|info|success|critical",
        "title": "<tiêu đề ngắn>",
    }

- `code` (ErrorCode): bucket lỗi cho FE phân nhánh UX coarse-grained (toast vs modal,
  redirect vs giữ form).
- `message_code` (MSG.XXX): khoá lookup vào registry — FE render lại template với
  `context` để hỗ trợ đa ngôn ngữ và edit live (Phase 2 doctype-driven).

Backwards-compat: `_err(msg, code=400)` cũ trả `code` là HTTP int — vẫn hoạt động.
Khi gọi `_err(msg, code=ErrorCode.X)` (chuỗi), helper sẽ tự map sang HTTP status.
"""
from __future__ import annotations

from typing import Any, Optional


class ErrorCode:
    """Machine-readable error codes — FE phân nhánh UX dựa vào đây.

    SOURCE OF TRUTH — `services/shared/constants.py:ErrorCode` re-export từ đây.
    Mọi value phải đồng bộ với `frontend/src/api/errors.ts:ErrorCode`.
    """
    VALIDATION = "VALIDATION"                       # 422 — input không hợp lệ (field-level)
    VALIDATION_ERROR = "VALIDATION_ERROR"           # 400 — input format / parse error
    BUSINESS_RULE = "BUSINESS_RULE"                 # 422 — vi phạm nghiệp vụ (workflow, state, ...)
    UNAUTHORIZED = "UNAUTHORIZED"                   # 401 — chưa đăng nhập / session hết hạn
    FORBIDDEN = "FORBIDDEN"                         # 403 — đã đăng nhập nhưng thiếu quyền
    NOT_FOUND = "NOT_FOUND"                         # 404 — tài nguyên không tồn tại
    CONFLICT = "CONFLICT"                           # 409 — trùng lặp / state conflict
    BAD_STATE = "BAD_STATE"                         # 409 — sai trạng thái workflow
    DUPLICATE = "DUPLICATE"                         # 409 — chỉ riêng case duplicate key
    INVALID_PARAMS = "INVALID_PARAMS"               # 400 — params malformed (JSON parse, …)
    RATE_LIMITED = "RATE_LIMITED"                   # 429 — quá ngưỡng request
    COMPLIANCE_BLOCKED = "COMPLIANCE_BLOCKED"       # 422 — IMM-16 gate: critical CAPA/finding mở
    INTERNAL = "INTERNAL"                           # 500 — lỗi server không lường trước
    INTERNAL_ERROR = "INTERNAL_ERROR"               # 500 — alias cho INTERNAL (giữ legacy)


_HTTP_FOR_CODE = {
    ErrorCode.VALIDATION: 422,
    ErrorCode.VALIDATION_ERROR: 400,
    ErrorCode.BUSINESS_RULE: 422,
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.CONFLICT: 409,
    ErrorCode.BAD_STATE: 409,
    ErrorCode.DUPLICATE: 409,
    ErrorCode.INVALID_PARAMS: 400,
    ErrorCode.RATE_LIMITED: 429,
    ErrorCode.COMPLIANCE_BLOCKED: 422,
    ErrorCode.INTERNAL: 500,
    ErrorCode.INTERNAL_ERROR: 500,
}


def _ok(data: Any = None) -> dict:
    """Chuẩn trả về thành công.

    Args:
        data: payload tuỳ ý (dict, list, scalar, ...).

    Note (Phase 1 notification framework):
        Caller có thể bổ sung `notify` key trong data nếu muốn ép FE hiển thị
        message cụ thể, vd:
            return _ok({"work_order": wo.name,
                        "notify": {"code": "IMM04-SENT", "context": {"count": 5}}})
        FE composable `useNotify.fromOk(resp)` sẽ tự pickup `data.notify`.
    """
    return {"success": True, "data": data}


def _err(
    msg: str,
    code: Any = 400,
    fields: Optional[dict] = None,
    http_status: Optional[int] = None,
    extra: Optional[dict] = None,
    *,
    message_code: Optional[str] = None,
    context: Optional[dict] = None,
    action_hint: Optional[str] = None,
    severity: Optional[str] = None,
    title: Optional[str] = None,
) -> dict:
    """Trả error envelope chuẩn.

    Args:
        msg: thông điệp tiếng Việt cho user (đã render template với context).
        code: HTTP int (legacy) HOẶC chuỗi từ ErrorCode (recommended).
        fields: dict {field_name: error_message} — cho form validation.
        http_status: override HTTP code khi cần (rare).
        extra: dict các key bổ sung (vd: existing_user khi conflict 409) để FE
            render UX phong phú hơn (link "xem bản ghi đã tồn tại", ...).
        message_code: MSG.XXX key vào registry (utils/messages.py) — FE tra cứu
            để render lại template hoặc i18n.
        context: dict biến cho template — FE format lại nếu muốn.
        action_hint: gợi ý hành động kế tiếp cho user (string ngắn).
        severity: 'error' | 'warning' | 'info' | 'success' | 'critical' — FE phân
            nhánh UI (toast màu / modal blocking).
        title: tiêu đề ngắn cho dialog/toast (vd: 'Không thể xuất hoá đơn').
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
    # Notification framework extension fields — chỉ append nếu có giá trị (giảm noise).
    if message_code:
        payload["message_code"] = message_code
    if context:
        payload["context"] = context
    if action_hint:
        payload["action_hint"] = action_hint
    if severity:
        payload["severity"] = severity
    if title:
        payload["title"] = title
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
    429: ErrorCode.RATE_LIMITED,
    500: ErrorCode.INTERNAL_ERROR,
}
