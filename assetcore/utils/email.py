# Copyright (c) 2026, AssetCore Team
"""Email helpers shared across schedulers and services."""
from typing import Iterable
import frappe


def get_role_emails(roles: Iterable[str]) -> list:
    roles = [r for r in roles if r]
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
        list(roles),
        as_dict=True,
    )
    return [r.email for r in rows]


def safe_sendmail(recipients, subject: str, message: str) -> None:
    if not recipients:
        return
    try:
        frappe.sendmail(recipients=recipients, subject=subject, message=message)
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"safe_sendmail failed: {subject}")
