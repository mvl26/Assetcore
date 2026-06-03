# Copyright (c) 2026, AssetCore Team
# Notification Framework (Wave N1) — Tier 1 API Layer.
#
# Endpoint cho per-user email toggle. In-app (chuông) dùng API Frappe core sẵn
# có (Notification Log) — không cần endpoint riêng ở đây.
#
# Spec: docs/imm-00/05_API_Specification.md §III.21.

from __future__ import annotations

import frappe

from assetcore.services import notifications as svc
from assetcore.utils.api_handler import handle


@frappe.whitelist()
def get_notification_preferences(user: str = "") -> dict:
    """Đọc tùy chọn nhận email của user hiện tại (System Manager có thể truyền user).

    Returns envelope: {"success": true, "data": {"email_enabled": bool}}
    """
    return handle(svc.get_notification_preferences, user or None)


@frappe.whitelist(methods=["POST"])
def set_email_enabled(enabled: bool = True, user: str = "") -> dict:
    """Bật/tắt nhận email cho user hiện tại.

    Body: {"enabled": false}. Returns: {"success": true, "data": {"email_enabled": bool}}
    """
    # Frappe parse JSON body bool đúng kiểu; cast phòng trường hợp truyền string.
    if isinstance(enabled, str):
        enabled = enabled.strip().lower() in ("1", "true", "yes")
    return handle(svc.set_email_enabled, bool(enabled), user or None)


@frappe.whitelist()
def get_delivery_kpi(days: str = "30") -> dict:
    """KPI độ phủ thông báo (System Manager only): delivery rate + opt-out rate.

    Query: `days` (cửa sổ Email Queue, mặc định 30). Cast str→int an toàn (tránh
    HTTP 417 do type-hint `int` trên GET param — LL-BE-1).

    Returns envelope: {"success": true, "data": {delivery_rate, opt_out_rate, ...}}.
    Spec: docs/imm-00/05_API_Specification.md §III.21.
    """
    try:
        days_int = int(days)
    except (TypeError, ValueError):
        days_int = 30
    return handle(svc.get_delivery_kpi, days_int)
