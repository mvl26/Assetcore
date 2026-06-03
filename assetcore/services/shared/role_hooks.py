# Copyright (c) 2026, AssetCore Team
"""Has Role hooks: umbrella Super Admin + invalidate capability cache.

`AssetCore Super Admin` là umbrella role — gắn cho user thì tự thêm
`System Manager` (idempotent); gỡ thì gỡ kèm. Tự động qua hook
`Has Role.after_insert/on_trash` (wire trong `hooks.py::doc_events`).

Cũng dọn cache capability của user khi `Has Role` / `Custom DocPerm` / `User`
thay đổi (Sai lầm #3 — cache stale).
"""
from __future__ import annotations

import frappe

from assetcore.services.shared import rbac

_SUPER = "AssetCore Super Admin"
_FRAPPE_ADMIN = "System Manager"


def _user_of(doc) -> str | None:
    """Lấy username thuộc về doc trigger hook (Has Role / User)."""
    if doc.doctype == "Has Role" and getattr(doc, "parenttype", None) == "User":
        return doc.parent
    if doc.doctype == "User":
        return doc.name
    return None


def sync_umbrella(doc, method: str | None = None) -> None:
    """Khi gán/gỡ Super Admin -> tự kèm/gỡ System Manager. Idempotent."""
    if doc.doctype != "Has Role" or getattr(doc, "parenttype", None) != "User":
        return
    if doc.role != _SUPER:
        return
    if not frappe.db.exists("User", doc.parent):
        return
    user = frappe.get_doc("User", doc.parent)
    has_roles = {r.role for r in user.roles}

    if method in ("after_insert", "on_update"):
        if _FRAPPE_ADMIN not in has_roles:
            try:
                user.append("roles", {"role": _FRAPPE_ADMIN})
                user.flags.ignore_permissions = True
                user.save()
            except Exception:
                frappe.log_error(
                    frappe.get_traceback(),
                    f"sync_umbrella: add System Manager for {doc.parent}",
                )
    elif method == "on_trash":
        # Gỡ System Manager nếu user không còn Super Admin nguồn khác
        # (giảm rủi ro mất quyền do admin gỡ Super Admin nhưng còn role khác)
        remaining_super = any(
            r.role == _SUPER and r.name != getattr(doc, "name", None)
            for r in user.roles
        )
        if not remaining_super and _FRAPPE_ADMIN in has_roles:
            try:
                user.set("roles",
                         [r for r in user.roles if r.role != _FRAPPE_ADMIN])
                user.flags.ignore_permissions = True
                user.save()
            except Exception:
                frappe.log_error(
                    frappe.get_traceback(),
                    f"sync_umbrella: remove System Manager for {doc.parent}",
                )


def invalidate_caps(doc, method: str | None = None) -> None:
    """Dọn cache capability sau khi role/permission của user thay đổi."""
    try:
        u = _user_of(doc)
        rbac.invalidate_capabilities(u)
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "invalidate_caps failed",
        )
