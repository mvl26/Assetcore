# Copyright (c) 2026, AssetCore Team
"""Tier 3 — Repository cho KPI Notification Delivery (Notification Framework vòng 5).

Đếm raw từ dữ liệu hệ thống Frappe core (KHÔNG DocType mới):
  - `Email Queue` — vết email đã gửi (status Sent / Not Sent + error).
  - `User` + `Notification Settings` — opt-out email.

Repository CHỈ đếm raw (sent/failed/total/opted_out) — KHÔNG tính tỷ lệ, KHÔNG gắn
ngưỡng màu (đó là việc của service, xem `services/notifications.py::get_delivery_kpi`).

Spec: docs/imm-00/04_Backend_Design.md §III.1b-4.
"""
from __future__ import annotations

import frappe
from frappe.utils import add_days, now_datetime


def count_email_delivery(ref_doctypes: frozenset[str], days: int) -> dict[str, int]:
    """Đếm email AssetCore đã gửi thành công vs thất bại trong cửa sổ `days` ngày.

    Chỉ tính Email Queue record có `reference_doctype ∈ ref_doctypes` (tách email
    AssetCore khỏi email hệ thống khác — xem audit-linkage §III.1b-4) và
    `creation >= now - days`.

    Phân loại (Frappe core):
      - `sent`   = `status = 'Sent'`.
      - `failed` = `status = 'Not Sent' AND error IS NOT NULL AND error != ''`
        (Frappe ghi lỗi gửi vào field `error`, status vẫn 'Not Sent').
      - 'Not Sent' chưa có error = đang chờ queue → KHÔNG tính (tránh hạ tỷ lệ giả).

    Args:
        ref_doctypes: tập reference_doctype của email AssetCore cần đo.
        days: số ngày cửa sổ tính ngược từ hiện tại (caller đã clamp >= 1).

    Returns:
        {"sent": int, "failed": int} — raw count, KHÔNG tính tỷ lệ.
    """
    if not ref_doctypes:
        return {"sent": 0, "failed": 0}

    cutoff = add_days(now_datetime(), -days)
    placeholders = ", ".join(["%s"] * len(ref_doctypes))
    params = list(ref_doctypes) + [cutoff]
    row = frappe.db.sql(
        f"""
        SELECT
            SUM(CASE WHEN status = 'Sent' THEN 1 ELSE 0 END) AS sent,
            SUM(CASE WHEN status = 'Not Sent'
                      AND error IS NOT NULL AND error != '' THEN 1 ELSE 0 END) AS failed
        FROM `tabEmail Queue`
        WHERE reference_doctype IN ({placeholders})
          AND creation >= %s
        """,
        params,
        as_dict=True,
    )
    sent = int((row[0].get("sent") if row else 0) or 0)
    failed = int((row[0].get("failed") if row else 0) or 0)
    return {"sent": sent, "failed": failed}


def count_email_opt_out() -> dict[str, int]:
    """Đếm tổng user nhận email vs số đã opt-out email (toàn hệ thống).

    `total_users` = user AssetCore (base role — SSoT `services.shared.ac_users`)
    đang hoạt động. KHÔNG đếm thô `tabUser`: user của ERPNext/CRM trên site dùng
    chung không nhận thông báo AssetCore, tính vào mẫu số sẽ dìm tỷ lệ opt-out.

    `opted_out` = trong số đó, user có `Notification Settings` với
    `enable_email_notifications = 0` OR `enabled = 0` (tắt toàn bộ notification).
    User CHƯA có Notification Settings = mặc định nhận email (Frappe default bật)
    → KHÔNG tính opt-out.

    Returns:
        {"total_users": int, "opted_out": int} — raw count, KHÔNG tính tỷ lệ.
    """
    from assetcore.services.shared.ac_users import ac_user_names

    names = sorted(ac_user_names())
    if not names:
        return {"total_users": 0, "opted_out": 0}

    total = int(frappe.db.count(
        "User", {"name": ["in", names], "enabled": 1, "user_type": "System User"}
    ))
    if total == 0:
        return {"total_users": 0, "opted_out": 0}

    row = frappe.db.sql(
        """
        SELECT COUNT(*) AS opted_out
        FROM `tabUser` u
        INNER JOIN `tabNotification Settings` ns ON ns.name = u.name
        WHERE u.enabled = 1
          AND u.user_type = 'System User'
          AND u.name IN %(names)s
          AND (ns.enable_email_notifications = 0 OR ns.enabled = 0)
        """,
        {"names": names},
        as_dict=True,
    )
    opted_out = int((row[0].get("opted_out") if row else 0) or 0)
    return {"total_users": total, "opted_out": opted_out}
