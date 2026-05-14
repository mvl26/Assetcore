# Copyright (c) 2026, AssetCore Team
# Shared helper utilities — dùng chung cho toàn bộ API modules

import json

import frappe


# ─────────────────────────────────────────────────────────────────────────────
# API RESPONSE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _parse_json(raw, default):
    """Parse a JSON string; return default on failure or non-string input."""
    if not raw:
        return default
    if not isinstance(raw, str):
        return raw
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return default


def _ok(data: dict | list) -> dict:
    """Chuẩn trả về thành công."""
    return {"success": True, "data": data}


def _err(message: str, code: int | str = "GENERIC_ERROR") -> dict:
    """Chuẩn trả về lỗi — KHÔNG set HTTP status code, luôn trả 200."""
    return {"success": False, "error": message, "code": code}


# ─────────────────────────────────────────────────────────────────────────────
# EMAIL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_role_emails(roles: list[str]) -> list[str]:
    """Lấy danh sách email của users thuộc các role (dùng SQL cho hiệu năng)."""
    if not roles:
        return []
    placeholders = ", ".join(["%s"] * len(roles))
    rows = frappe.db.sql(
        f"""
        SELECT DISTINCT u.email
        FROM `tabHas Role` hr
        JOIN `tabUser` u ON u.name = hr.parent
        WHERE hr.role IN ({placeholders})
          AND hr.parenttype = 'User'
          AND u.enabled = 1
          AND u.email IS NOT NULL AND u.email != ''
        """,
        roles,
        as_dict=True,
    )
    return [r.email for r in rows]


def _safe_sendmail(**kwargs) -> None:
    """Wrapper quanh frappe.sendmail — bỏ qua nếu email chưa cấu hình."""
    try:
        if not frappe.flags.mute_emails:
            frappe.sendmail(**kwargs)
    except Exception:
        pass
