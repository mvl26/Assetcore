# Copyright (c) 2026, AssetCore Team
"""
Custom DocPerm cho Frappe core DocType — đảm bảo IMM-only user dùng được desk
mà không cần thêm role System Manager hay role Frappe gốc khác.

Không modify core JSON. Dùng `Custom DocPerm` (override layer native của Frappe).

Idempotent: chạy lại không duplicate row. Wire vào hooks.after_install /
hooks.after_migrate.

Chạy thủ công:
    bench --site <site> execute assetcore.setup.setup_core_permissions.run
"""
from __future__ import annotations

import frappe
from assetcore.services.shared.constants import Roles

# ─── Permission profiles ──────────────────────────────────────────────────────
def _p(*flags: str) -> dict:
    """Build permission dict. Flags: R W C D S M A (submit/cancel/amend ignored
    nếu DocType không submittable)."""
    s = set(flags)
    return {
        "permlevel": 0,
        "read":   1 if "R" in s else 0,
        "write":  1 if "W" in s else 0,
        "create": 1 if "C" in s else 0,
        "delete": 1 if "D" in s else 0,
        "submit": 1 if "S" in s else 0,
        "cancel": 1 if "M" in s else 0,
        "amend":  1 if "A" in s else 0,
        "report": 1 if "R" in s else 0,
        "export": 1 if "R" in s else 0,
        "print":  1 if "R" in s else 0,
        "email":  1 if "R" in s else 0,
        "share":  1 if "R" in s else 0,
        "if_owner": 0,
    }


# ─── Role groups ──────────────────────────────────────────────────────────────
_ALL_DESK_ROLES = list(Roles.ALL_IMM)        # 13 roles incl. Vendor Engineer
_ALL_INTERNAL = [r for r in Roles.ALL_IMM if r != Roles.VENDOR_ENGINEER]
_GOVERNANCE = [Roles.SYS_ADMIN, Roles.OPS_MANAGER, Roles.QA, Roles.AUDITOR]
_ADMIN_OPS = [Roles.SYS_ADMIN, Roles.OPS_MANAGER]
_VENDOR_MGMT = [Roles.SYS_ADMIN, Roles.OPS_MANAGER, Roles.STOREKEEPER]


# ─── Matrix: (DocType, [(role, perm_dict), ...]) ──────────────────────────────
# Logic theo tier (xem docstring cho chi tiết)
_CORE_MATRIX: list[tuple[str, list[tuple[str, dict]]]] = [
    # ── Tier 1: Desk essentials — mọi IMM role (kể cả Vendor) đều cần ─────────
    ("File",              [(r, _p("R", "W", "C", "D")) for r in _ALL_DESK_ROLES]),
    ("ToDo",              [(r, _p("R", "W", "C", "D")) for r in _ALL_DESK_ROLES]),
    ("Comment",           [(r, _p("R", "W", "C", "D")) for r in _ALL_DESK_ROLES]),
    ("Tag",               [(r, _p("R", "W", "C")) for r in _ALL_DESK_ROLES]),
    ("Tag Link",          [(r, _p("R", "W", "C", "D")) for r in _ALL_DESK_ROLES]),
    ("Communication",     [(r, _p("R", "W", "C")) for r in _ALL_DESK_ROLES]),
    ("Notification Log",  [(r, _p("R", "W")) for r in _ALL_DESK_ROLES]),
    ("Workflow Action",   [(r, _p("R", "W")) for r in _ALL_DESK_ROLES]),
    ("Workspace",         [(r, _p("R")) for r in _ALL_DESK_ROLES]),
    ("Page",              [(r, _p("R")) for r in _ALL_DESK_ROLES]),
    ("Module Def",        [(r, _p("R")) for r in _ALL_DESK_ROLES]),
    ("Print Format",      [(r, _p("R")) for r in _ALL_DESK_ROLES]),
    ("Letter Head",       [(r, _p("R")) for r in _ALL_DESK_ROLES]),
    ("Currency",          [(r, _p("R")) for r in _ALL_DESK_ROLES]),
    ("Country",           [(r, _p("R")) for r in _ALL_DESK_ROLES]),
    ("Web Form",          [(r, _p("R")) for r in _ALL_DESK_ROLES]),
    ("Web Page",          [(r, _p("R")) for r in _ALL_DESK_ROLES]),
    ("Dashboard",         [(r, _p("R")) for r in _ALL_DESK_ROLES]),
    ("Dashboard Chart",   [(r, _p("R")) for r in _ALL_DESK_ROLES]),
    ("Number Card",       [(r, _p("R")) for r in _ALL_DESK_ROLES]),
    ("Report",            [(r, _p("R")) for r in _ALL_DESK_ROLES]),
    ("Notification Settings", [(r, _p("R", "W")) for r in _ALL_DESK_ROLES]),
    ("DocShare",          [(r, _p("R", "W", "C", "D")) for r in _ALL_INTERNAL]),

    # ── Tier 2: Audit visibility (Admin + QA + Auditor) ───────────────────────
    ("Version",       [(r, _p("R")) for r in _GOVERNANCE]),
    ("Activity Log",  [(r, _p("R")) for r in _GOVERNANCE]),
    ("View Log",      [(r, _p("R")) for r in _GOVERNANCE]),
    ("Error Log",     [(r, _p("R", "D")) for r in _ADMIN_OPS]),
    ("Access Log",    [(r, _p("R")) for r in _ADMIN_OPS]),
    ("Scheduled Job Log", [(r, _p("R")) for r in _ADMIN_OPS]),

    # ── Tier 3: User & role management (Admin + Ops Manager) ──────────────────
    # User: read cho tất cả internal role (mention, assignment, autocomplete);
    # Admin + Ops thêm W+C để tạo/sửa user qua trang user-profiles.
    ("User",            [(r, _p("R")) for r in _ALL_INTERNAL if r not in _ADMIN_OPS]),
    ("User",            [(r, _p("R", "W", "C")) for r in _ADMIN_OPS]),
    ("Role",            [(r, _p("R")) for r in _ADMIN_OPS]),
    ("Has Role",        [(r, _p("R", "W", "C", "D")) for r in _ADMIN_OPS]),
    ("Role Profile",    [(r, _p("R")) for r in _ADMIN_OPS]),
    ("DocType",         [(r, _p("R")) for r in _ALL_INTERNAL]),  # read meta để render form
    ("Custom Field",    [(r, _p("R", "W", "C", "D")) for r in [Roles.SYS_ADMIN]]),
    ("Custom DocPerm",  [(r, _p("R", "W", "C", "D")) for r in [Roles.SYS_ADMIN]]),
    ("Property Setter", [(r, _p("R", "W", "C", "D")) for r in [Roles.SYS_ADMIN]]),
    ("Workflow",        [(r, _p("R")) for r in _ALL_INTERNAL]),
    ("Workflow State",  [(r, _p("R")) for r in _ALL_INTERNAL]),
    ("Workflow Action Master", [(r, _p("R")) for r in _ALL_INTERNAL]),

    # ── Tier 4: Notification & email config (Admin + Ops + QA) ────────────────
    ("Notification",    [(r, _p("R", "W", "C", "D")) for r in [Roles.SYS_ADMIN, Roles.OPS_MANAGER, Roles.QA]]),
    ("Email Template",  [(r, _p("R", "W", "C", "D")) for r in [Roles.SYS_ADMIN, Roles.OPS_MANAGER, Roles.QA, Roles.DOC_OFFICER]]),
    ("Email Queue",     [(r, _p("R")) for r in _ALL_INTERNAL]),

    # ── Tier 5: Address / Contact (vendor management) ─────────────────────────
    ("Address",         [(r, _p("R", "W", "C", "D")) for r in _VENDOR_MGMT]),
    ("Contact",         [(r, _p("R", "W", "C", "D")) for r in _VENDOR_MGMT]),
    ("Dynamic Link",    [(r, _p("R", "W", "C", "D")) for r in _VENDOR_MGMT]),
    # Read-only Address/Contact cho roles còn lại (vendor info trên Asset/Service Contract)
    ("Address",         [(r, _p("R")) for r in _ALL_DESK_ROLES if r not in _VENDOR_MGMT]),
    ("Contact",         [(r, _p("R")) for r in _ALL_DESK_ROLES if r not in _VENDOR_MGMT]),
]


# ─── Engine ───────────────────────────────────────────────────────────────────

def _doctype_exists(dt: str) -> bool:
    return bool(frappe.db.exists("DocType", dt))


def _role_exists(role: str) -> bool:
    return bool(frappe.db.exists("Role", role))


def _upsert_custom_docperm(parent: str, role: str, perm: dict) -> str:
    """Tạo/cập nhật Custom DocPerm row. Returns: inserted | updated | skipped."""
    existing_name = frappe.db.get_value(
        "Custom DocPerm",
        {"parent": parent, "role": role, "permlevel": perm["permlevel"]},
        "name",
    )
    if existing_name:
        # Compare và update nếu khác
        existing = frappe.db.get_value(
            "Custom DocPerm", existing_name,
            list(perm.keys()),
            as_dict=True,
        )
        if existing and all(int(existing.get(k) or 0) == int(perm[k]) for k in perm):
            return "skipped"
        for k, v in perm.items():
            frappe.db.set_value("Custom DocPerm", existing_name, k, v)
        return "updated"

    doc = frappe.new_doc("Custom DocPerm")
    doc.parent = parent
    doc.parenttype = "DocType"
    doc.parentfield = "permissions"
    doc.role = role
    for k, v in perm.items():
        doc.set(k, v)
    doc.flags.ignore_permissions = True
    doc.insert()
    return "inserted"


def run() -> None:
    """Apply Custom DocPerm matrix cho Frappe core DocType. Idempotent."""
    stats = {"inserted": 0, "updated": 0, "skipped": 0, "missing_dt": 0, "missing_role": 0}

    for parent, role_perms in _CORE_MATRIX:
        if not _doctype_exists(parent):
            stats["missing_dt"] += 1
            continue
        for role, perm in role_perms:
            if not _role_exists(role):
                stats["missing_role"] += 1
                continue
            try:
                stats[_upsert_custom_docperm(parent, role, perm)] += 1
            except Exception:
                frappe.log_error(
                    frappe.get_traceback(),
                    f"setup_core_permissions: {parent} / {role}",
                )

    frappe.db.commit()
    # Clear cache để Frappe reload permissions
    frappe.clear_cache()
    print(
        f"[AssetCore] Core DocPerm: {stats['inserted']} insert, "
        f"{stats['updated']} update, {stats['skipped']} skip "
        f"({stats['missing_dt']} DocType bỏ qua, {stats['missing_role']} role bỏ qua)."
    )
