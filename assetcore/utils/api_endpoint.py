# Copyright (c) 2026, AssetCore Team
"""@api_endpoint decorator — chuẩn hóa exception → error envelope.

Sử dụng:

    @frappe.whitelist()
    @api_endpoint
    def my_handler(name: str):
        doc = frappe.get_doc("AC Asset", name)  # raise DoesNotExistError nếu thiếu
        if doc.locked:
            frappe.throw(_("Tài sản đang bị khóa"))  # → BUSINESS_RULE
        ...
        return _ok(doc.as_dict())

Decorator catch các exception phổ biến và map sang code chuẩn:
    DoesNotExistError       → NOT_FOUND        (404)
    PermissionError         → FORBIDDEN        (403)
    DuplicateEntryError     → CONFLICT         (409)
    ValidationError         → BUSINESS_RULE    (422) — frappe.throw / DocType validate
    LinkValidationError     → VALIDATION_ERROR (400) — link field broken
    Exception khác          → INTERNAL_ERROR   (500) — log full trace
"""
from __future__ import annotations

import functools
from typing import Callable

import frappe

from assetcore.utils.response import _err, ErrorCode


def api_endpoint(fn: Callable) -> Callable:
    """Wrap handler — catch exception, map sang error envelope."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except frappe.DoesNotExistError as e:
            return _err(_extract_msg(e, "Không tìm thấy bản ghi"), ErrorCode.NOT_FOUND)
        except frappe.PermissionError as e:
            return _err(_extract_msg(e, "Bạn không có quyền thực hiện thao tác này"),
                        ErrorCode.FORBIDDEN)
        except frappe.DuplicateEntryError as e:
            return _err(_extract_msg(e, "Bản ghi đã tồn tại"), ErrorCode.CONFLICT)
        except frappe.LinkValidationError as e:
            return _err(_extract_msg(e, "Tham chiếu không hợp lệ"),
                        ErrorCode.VALIDATION_ERROR)
        except frappe.ValidationError as e:
            # frappe.throw → ValidationError. Đây là vi phạm nghiệp vụ chứ không
            # phải lỗi system. Trả 422 + code BUSINESS_RULE.
            return _err(_extract_msg(e, "Dữ liệu không hợp lệ"), ErrorCode.BUSINESS_RULE)
        except Exception as e:  # pragma: no cover — fallback
            frappe.log_error(title=f"API error: {fn.__module__}.{fn.__name__}",
                             message=frappe.get_traceback())
            return _err(_extract_msg(e, "Lỗi hệ thống"), ErrorCode.INTERNAL_ERROR)

    return wrapper


def _extract_msg(exc: BaseException, fallback: str) -> str:
    """Frappe đẩy thông điệp qua _server_messages; lấy ưu tiên đó, fallback str(exc)."""
    try:
        msgs = frappe.local.message_log or []
        if msgs:
            last = msgs[-1]
            if isinstance(last, dict):
                return str(last.get("message") or fallback)
            return str(last)
    except Exception:
        pass
    txt = str(exc).strip()
    return txt if txt and txt != "None" else fallback
