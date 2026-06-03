# Copyright (c) 2026, AssetCore Team
# Shared helper utilities — dùng chung cho toàn bộ API modules.
#
# DEPRECATED (Phase 0 of notification framework rollout):
#   `_ok` / `_err` đã được hợp nhất về `assetcore.utils.response` —
#   nguồn duy nhất cho API envelope. File này chỉ re-export để giữ backwards-compat
#   cho ~14 module hiện đang `from assetcore.utils.helpers import _err, _ok`.
#   Sẽ xoá block re-export ở Phase 6 sau khi migrate hết callers.

import json

import frappe

# Re-export canonical helpers — KHÔNG redefine ở đây.
from assetcore.utils.response import _err, _ok  # noqa: F401 (re-export for legacy callers)


# ─────────────────────────────────────────────────────────────────────────────
# API RESPONSE HELPERS — JSON PARSING (giữ tại đây vì không thuộc envelope)
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
