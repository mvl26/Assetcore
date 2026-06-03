# Copyright (c) 2026, AssetCore Team
"""Permission query conditions + has_permission hooks for AssetCore DocTypes.

Two-layer scope enforcement (closes AUTH-01 + AUTH-10):

1. `*_query` (list/search) — wired through `permission_query_conditions` in hooks.py.
   Frappe injects the WHERE clause when running `frappe.get_list / get_all` (list
   endpoints, dashboards, autocomplete).

2. `*_has_permission` (detail/read/write by name) — wired through `has_permission`
   in hooks.py. Frappe calls it when resolving `frappe.has_permission(doctype, ptype,
   doc=...)` which is what `frappe.get_doc()` invokes internally, AND on direct
   URL access to a specific record. This is the IDOR (AUTH-10) gate.

Scope strategy chosen (matches `docs/res/rbac/user-scope-filter-analysis.md` §3,
option closest to "scope by role assignment + record link"):

- Senior roles (Super Admin + module Managers) → unrestricted.
- Vendor Engineer (KTV NCC) → only records where they are the assigned actor
  (`assigned_to`, `responsible_technician`, or `vendor_engineer_name`). Closes
  AUTH-01 (vendor isolation at BE detail/API, not just FE).
- Domain User (PM User / Repair User) → only their assigned records.
- Auditor → unrestricted READ; writes blocked by DocPerm.

Why query + has_permission (both) — frappe.has_permission() does NOT auto-apply
permission_query_conditions. Without has_permission gate, a vendor can still hit
`/assets/<other-dept-asset>` directly even though list filter would hide it.
"""
from __future__ import annotations

import frappe

# Senior roles bypass scope (umbrella managers + Super Admin).
_SENIOR_ROLES = frozenset({
    "AssetCore Super Admin",
    "Commissioning Manager", "Compliance Manager",
    "PM Manager", "Repair Manager", "Calibration Manager",
    "Corrective Manager", "Inventory Manager", "Document Manager",
    "Procurement Manager", "Spec Manager", "Needs Manager",
    "Data Manager", "Training Manager",
    # Frappe core admin umbrella
    "System Manager", "Administrator",
})
# Auditor is read-only — unrestricted READ, blocked at DocPerm for write.
_AUDITOR_ROLE = "AssetCore Auditor"
_VENDOR_ROLE = "Vendor Engineer"
# Domain technician role names — scoped to their own assigned/reported records.
# Corrective User added 2026-05-28: was reading Incident Report unrestricted because
# missing from this set (smoke S-13 found the dead permission_query).
_TECHNICIAN_ROLES = frozenset({"PM User", "Repair User", "Calibration User", "Corrective User"})


def _user_roles(user: str | None) -> set[str]:
    return set(frappe.get_roles(user or frappe.session.user))


def _is_senior(roles: set[str]) -> bool:
    return bool(roles & _SENIOR_ROLES)


def _esc(value: str) -> str:
    """Strip the surrounding quotes that frappe.db.escape() adds — we splice
    the literal into a static SQL fragment, not a parameter slot."""
    return frappe.db.escape(value)[1:-1]


# ─── permission_query_conditions (list/search filter) ─────────────────────────

def ac_asset_query(user: str | None = None) -> str:
    user = user or frappe.session.user
    roles = _user_roles(user)
    if _is_senior(roles) or _AUDITOR_ROLE in roles:
        return ""
    safe = _esc(user)
    if _VENDOR_ROLE in roles:
        # Vendor sees only assets where they are responsible_technician.
        return f"(`tabAC Asset`.responsible_technician = '{safe}')"
    if roles & _TECHNICIAN_ROLES:
        return f"(`tabAC Asset`.responsible_technician = '{safe}')"
    return ""


def incident_report_query(user: str | None = None) -> str:
    user = user or frappe.session.user
    roles = _user_roles(user)
    if _is_senior(roles) or _AUDITOR_ROLE in roles:
        return ""
    safe = _esc(user)
    if _VENDOR_ROLE in roles:
        # Vendor sees only incidents on assets they are responsible for.
        # 2026-05-28 fix: field is `asset`, not `asset_ref` (Incident Report
        # DocType has no `asset_ref` column → filter was a no-op).
        return (
            "(`tabIncident Report`.asset IN "
            f"(SELECT name FROM `tabAC Asset` WHERE responsible_technician = '{safe}'))"
        )
    if roles & _TECHNICIAN_ROLES:
        return f"(`tabIncident Report`.reported_by = '{safe}')"
    return ""


def asset_repair_query(user: str | None = None) -> str:
    user = user or frappe.session.user
    roles = _user_roles(user)
    if _is_senior(roles) or _AUDITOR_ROLE in roles:
        return ""
    safe = _esc(user)
    if _VENDOR_ROLE in roles or (roles & _TECHNICIAN_ROLES):
        return f"(`tabAsset Repair`.assigned_to = '{safe}')"
    return ""


def pm_work_order_query(user: str | None = None) -> str:
    user = user or frappe.session.user
    roles = _user_roles(user)
    if _is_senior(roles) or _AUDITOR_ROLE in roles:
        return ""
    safe = _esc(user)
    if _VENDOR_ROLE in roles or (roles & _TECHNICIAN_ROLES):
        return f"(`tabPM Work Order`.assigned_to = '{safe}')"
    return ""


def asset_commissioning_query(user: str | None = None) -> str:
    user = user or frappe.session.user
    roles = _user_roles(user)
    if _is_senior(roles) or _AUDITOR_ROLE in roles:
        return ""
    safe = _esc(user)
    if _VENDOR_ROLE in roles:
        # Vendor only sees commissioning records they are wired into.
        return (
            "(`tabAsset Commissioning`.vendor_engineer_name = "
            f"'{safe}' OR `tabAsset Commissioning`.owner = '{safe}')"
        )
    return ""


# ─── has_permission (detail / IDOR gate) ──────────────────────────────────────
#
# Frappe calls this on EVERY `frappe.has_permission(dt, ptype, doc=...)` —
# including the implicit call inside `frappe.get_doc()`. Returning False blocks
# direct URL access (the AUTH-10 IDOR case).
#
# Contract: return True → allow, False → deny. None / no return → defer to
# Frappe's DocPerm chain (do not return None here; explicit bool).

def _scope_check_assigned(doc, user: str, *fields: str) -> bool:
    """True if the doc has user in any of the given actor fields."""
    for f in fields:
        if doc.get(f) == user:
            return True
    return False


def ac_asset_has_permission(doc, ptype: str = "read", user: str | None = None, **_kw) -> bool:
    user = user or frappe.session.user
    roles = _user_roles(user)
    if _is_senior(roles):
        return True
    if _AUDITOR_ROLE in roles and ptype in ("read", "print", "email", "export"):
        return True
    if _VENDOR_ROLE in roles:
        # Vendor: only assets they are responsible for. Block ANY ptype on
        # other assets, including read (IDOR).
        return _scope_check_assigned(doc, user, "responsible_technician")
    if roles & _TECHNICIAN_ROLES:
        if ptype == "read":
            return _scope_check_assigned(doc, user, "responsible_technician")
        # technicians cannot mutate AC Asset directly — let DocPerm decide.
        return False
    # Other roles → DocPerm chain decides (return True to defer, Frappe still
    # applies DocPerm role/permission rules).
    return True


def incident_report_has_permission(doc, ptype: str = "read", user: str | None = None, **_kw) -> bool:
    user = user or frappe.session.user
    roles = _user_roles(user)
    if _is_senior(roles):
        return True
    if _AUDITOR_ROLE in roles and ptype in ("read", "print", "email", "export"):
        return True
    if _VENDOR_ROLE in roles:
        # Vendor sees only incidents on assets they are responsible for.
        # 2026-05-28 fix: field is `asset`, not `asset_ref`.
        asset_name = doc.get("asset")
        if not asset_name:
            return False
        tech = frappe.db.get_value("AC Asset", asset_name, "responsible_technician")
        return tech == user
    if roles & _TECHNICIAN_ROLES:
        return _scope_check_assigned(doc, user, "reported_by", "assigned_to")
    return True


def asset_repair_has_permission(doc, ptype: str = "read", user: str | None = None, **_kw) -> bool:
    user = user or frappe.session.user
    roles = _user_roles(user)
    if _is_senior(roles):
        return True
    if _AUDITOR_ROLE in roles and ptype in ("read", "print", "email", "export"):
        return True
    if _VENDOR_ROLE in roles or (roles & _TECHNICIAN_ROLES):
        return _scope_check_assigned(doc, user, "assigned_to")
    return True


def pm_work_order_has_permission(doc, ptype: str = "read", user: str | None = None, **_kw) -> bool:
    user = user or frappe.session.user
    roles = _user_roles(user)
    if _is_senior(roles):
        return True
    if _AUDITOR_ROLE in roles and ptype in ("read", "print", "email", "export"):
        return True
    if _VENDOR_ROLE in roles or (roles & _TECHNICIAN_ROLES):
        return _scope_check_assigned(doc, user, "assigned_to", "supervisor")
    return True


def asset_commissioning_has_permission(doc, ptype: str = "read", user: str | None = None, **_kw) -> bool:
    user = user or frappe.session.user
    roles = _user_roles(user)
    if _is_senior(roles):
        return True
    if _AUDITOR_ROLE in roles and ptype in ("read", "print", "email", "export"):
        return True
    if _VENDOR_ROLE in roles:
        return _scope_check_assigned(doc, user, "vendor_engineer_name", "owner")
    return True
