# Copyright (c) 2026, AssetCore Team
"""Permission query conditions for AssetCore DocTypes.

IMM Technician has a restricted view — senior roles see everything.
"""
import frappe

_SENIOR_ROLES = frozenset({
    "IMM System Admin", "IMM Department Head",
    "IMM Operations Manager", "IMM QA Officer", "IMM Workshop Lead",
})
_TECHNICIAN_ROLE = "IMM Technician"


def _is_senior(roles: set) -> bool:
    return bool(roles & _SENIOR_ROLES)


def ac_asset_query(user: str = None) -> str:
    """Restrict IMM Technician to assets where they are responsible_technician."""
    user = user or frappe.session.user
    roles = set(frappe.get_roles(user))
    if _is_senior(roles):
        return ""
    if _TECHNICIAN_ROLE in roles:
        safe = frappe.db.escape(user)[1:-1]
        return f"(`tabAC Asset`.responsible_technician = '{safe}')"
    return ""


def incident_report_query(user: str = None) -> str:
    """Restrict IMM Technician to incidents they reported or are on their asset."""
    user = user or frappe.session.user
    roles = set(frappe.get_roles(user))
    if _is_senior(roles):
        return ""
    if _TECHNICIAN_ROLE in roles:
        safe = frappe.db.escape(user)[1:-1]
        return f"(`tabIncident Report`.reported_by = '{safe}')"
    return ""


def asset_repair_query(user: str = None) -> str:
    """Restrict IMM Technician to repair work orders assigned to them."""
    user = user or frappe.session.user
    roles = set(frappe.get_roles(user))
    if _is_senior(roles):
        return ""
    if _TECHNICIAN_ROLE in roles:
        safe = frappe.db.escape(user)[1:-1]
        return f"(`tabAsset Repair`.assigned_to = '{safe}')"
    return ""


def pm_work_order_query(user: str = None) -> str:
    """Restrict IMM Technician to PM work orders assigned to them."""
    user = user or frappe.session.user
    roles = set(frappe.get_roles(user))
    if _is_senior(roles):
        return ""
    if _TECHNICIAN_ROLE in roles:
        safe = frappe.db.escape(user)[1:-1]
        return f"(`tabPM Work Order`.assigned_to = '{safe}')"
    return ""
