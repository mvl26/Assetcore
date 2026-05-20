# Copyright (c) 2026, AssetCore Team
"""
Custom DocPerm cho Frappe core DocType — đảm bảo các role mới (RBAC
module-based) dùng được desk mà không cần System Manager.

`AssetCore Super Admin` đã được umbrella hook (role_hooks.sync_umbrella) tự gán
kèm `System Manager` → bỏ qua Super Admin trong matrix này (System Manager đã
đủ).

Mục tiêu: cấp permission tối thiểu cho `AssetCore System User` (baseline) +
`AssetCore Auditor` + `Vendor Engineer` để dùng desk (File, ToDo, Notification,
Workflow Action, Workspace, Report ...).

Không modify core JSON. Dùng `Custom DocPerm` (override layer). Idempotent.

Chạy thủ công:
    bench --site <site> execute assetcore.setup.setup_core_permissions.run
"""
from __future__ import annotations

import frappe

from assetcore.services.shared.constants import Roles

# ─── Permission profiles ──────────────────────────────────────────────────────
def _p(*flags: str) -> dict:
    """Build permission dict. Flags: R W C D S M A."""
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


# ─── Role groups (RBAC module-based) ──────────────────────────────────────────
# Baseline role nền — mọi user nội bộ phải có
_BASELINE = Roles.SYSTEM_USER
# Vendor — cô lập
_VENDOR = Roles.VENDOR
# Auditor — chỉ đọc
_AUDITOR = Roles.AUDITOR
# Mọi domain user (manager + user) — cũng cần desk
_DOMAIN_ROLES: list[str] = list(Roles.DOMAIN_ROLES)
# Mọi role nội bộ (system_user + domain) — không gồm vendor để giữ isolation
_ALL_INTERNAL = [_BASELINE, _AUDITOR] + _DOMAIN_ROLES
# Mọi role có thể vào desk (gồm vendor để vendor xem File trên WO)
_ALL_DESK = _ALL_INTERNAL + [_VENDOR]


# ─── Matrix: (DocType, [(role, perm_dict), ...]) ──────────────────────────────
# Logic: capability layer (rbac.py) là chốt chặn cho nghiệp vụ; matrix này chỉ
# cấp quyền Frappe-core để desk render được + workflow chạy được.
_CORE_MATRIX: list[tuple[str, list[tuple[str, dict]]]] = [
    # ── Tier 1: Desk essentials — mọi role dùng desk đều cần ─────────────────
    ("File",              [(r, _p("R", "W", "C", "D")) for r in _ALL_DESK]),
    ("ToDo",              [(r, _p("R", "W", "C", "D")) for r in _ALL_DESK]),
    ("Comment",           [(r, _p("R", "W", "C", "D")) for r in _ALL_DESK]),
    ("Tag",               [(r, _p("R", "W", "C")) for r in _ALL_DESK]),
    ("Tag Link",          [(r, _p("R", "W", "C", "D")) for r in _ALL_DESK]),
    ("Communication",     [(r, _p("R", "W", "C")) for r in _ALL_DESK]),
    ("Notification Log",  [(r, _p("R", "W")) for r in _ALL_DESK]),
    ("Workflow Action",   [(r, _p("R", "W")) for r in _ALL_DESK]),
    ("Workspace",         [(r, _p("R")) for r in _ALL_DESK]),
    ("Page",              [(r, _p("R")) for r in _ALL_DESK]),
    ("Module Def",        [(r, _p("R")) for r in _ALL_DESK]),
    ("Print Format",      [(r, _p("R")) for r in _ALL_DESK]),
    ("Letter Head",       [(r, _p("R")) for r in _ALL_DESK]),
    ("Currency",          [(r, _p("R")) for r in _ALL_DESK]),
    ("Country",           [(r, _p("R")) for r in _ALL_DESK]),
    ("Web Form",          [(r, _p("R")) for r in _ALL_DESK]),
    ("Web Page",          [(r, _p("R")) for r in _ALL_DESK]),
    ("Dashboard",         [(r, _p("R")) for r in _ALL_DESK]),
    ("Dashboard Chart",   [(r, _p("R")) for r in _ALL_DESK]),
    ("Number Card",       [(r, _p("R")) for r in _ALL_DESK]),
    ("Report",            [(r, _p("R")) for r in _ALL_DESK]),
    ("Notification Settings", [(r, _p("R", "W")) for r in _ALL_DESK]),
    ("DocShare",          [(r, _p("R", "W", "C", "D")) for r in _ALL_INTERNAL]),

    # ── Tier 2: Audit visibility (Auditor read everything) ────────────────────
    ("Version",       [(_AUDITOR, _p("R"))]),
    ("Activity Log",  [(_AUDITOR, _p("R"))]),
    ("View Log",      [(_AUDITOR, _p("R"))]),

    # ── Tier 3: Workflow meta — mọi role cần đọc để render ────────────────────
    ("DocType",         [(r, _p("R")) for r in _ALL_INTERNAL]),
    ("Workflow",        [(r, _p("R")) for r in _ALL_INTERNAL]),
    ("Workflow State",  [(r, _p("R")) for r in _ALL_INTERNAL]),
    ("Workflow Action Master", [(r, _p("R")) for r in _ALL_INTERNAL]),
    ("Role",            [(r, _p("R")) for r in _ALL_INTERNAL]),
    ("User",            [(r, _p("R")) for r in _ALL_INTERNAL]),

    # ── Tier 4: Email queue (mọi role thấy notification của mình) ─────────────
    ("Email Queue",     [(r, _p("R")) for r in _ALL_INTERNAL]),

    # ── Tier 5: Address / Contact (vendor management) ─────────────────────────
    # Domain Manager của Procurement / Data / Inventory được quản
    ("Address",  [(r, _p("R", "W", "C", "D")) for r in [
        "Procurement Manager", "Data Manager", "Inventory Manager",
    ]]),
    ("Contact",  [(r, _p("R", "W", "C", "D")) for r in [
        "Procurement Manager", "Data Manager", "Inventory Manager",
    ]]),
    ("Dynamic Link", [(r, _p("R", "W", "C", "D")) for r in [
        "Procurement Manager", "Data Manager", "Inventory Manager",
    ]]),
    # Mọi role còn lại đọc-only
    ("Address",  [(r, _p("R")) for r in _ALL_DESK
        if r not in ("Procurement Manager", "Data Manager", "Inventory Manager")]),
    ("Contact",  [(r, _p("R")) for r in _ALL_DESK
        if r not in ("Procurement Manager", "Data Manager", "Inventory Manager")]),
]


# ─── Engine ───────────────────────────────────────────────────────────────────

def _doctype_exists(dt: str) -> bool:
    return bool(frappe.db.exists("DocType", dt))


def _role_exists(role: str) -> bool:
    return bool(frappe.db.exists("Role", role))


def _ensure_standard_cloned(parent: str, _cache: set[str] = set()) -> None:
    """Đảm bảo standard DocPerm đã được clone sang Custom DocPerm cho `parent`.

    Frappe quy tắc: khi `tabCustom DocPerm` có BẤT KỲ row nào cho 1 DocType,
    Frappe IGNORE toàn bộ standard DocPerm. → Phải clone trước, không thì
    System Manager permlevel=1 (và các permission gốc khác) bị shadow.

    Idempotent: `setup_custom_perms` chỉ copy khi Custom DocPerm chưa có row.
    """
    if parent in _cache:
        return
    from frappe.permissions import setup_custom_perms
    setup_custom_perms(parent)
    _cache.add(parent)


def _upsert_custom_docperm(parent: str, role: str, perm: dict) -> str:
    """Tạo/cập nhật Custom DocPerm row. Returns: inserted | updated | skipped."""
    _ensure_standard_cloned(parent)
    existing_name = frappe.db.get_value(
        "Custom DocPerm",
        {"parent": parent, "role": role, "permlevel": perm["permlevel"]},
        "name",
    )
    if existing_name:
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


_PERM_FLAGS = (
    "read", "write", "create", "delete", "submit", "cancel", "amend",
    "report", "export", "print", "email", "share",
)


def _merge_matrix() -> dict[tuple[str, str, int], dict]:
    """Coalesce nhiều entry cùng (parent, role, permlevel) bằng OR-merge."""
    merged: dict[tuple[str, str, int], dict] = {}
    for parent, role_perms in _CORE_MATRIX:
        for role, perm in role_perms:
            key = (parent, role, perm["permlevel"])
            if key not in merged:
                merged[key] = dict(perm)
                continue
            cur = merged[key]
            for flag in _PERM_FLAGS:
                if perm.get(flag):
                    cur[flag] = 1
    return merged


def run() -> None:
    """Apply Custom DocPerm matrix cho Frappe core DocType. Idempotent."""
    stats = {"inserted": 0, "updated": 0, "skipped": 0, "missing_dt": 0, "missing_role": 0}

    for (parent, role, _permlevel), perm in _merge_matrix().items():
        if not _doctype_exists(parent):
            stats["missing_dt"] += 1
            continue
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
    frappe.clear_cache()
    print(
        f"[AssetCore] Core DocPerm: {stats['inserted']} insert, "
        f"{stats['updated']} update, {stats['skipped']} skip "
        f"({stats['missing_dt']} DocType bỏ qua, {stats['missing_role']} role bỏ qua)."
    )
