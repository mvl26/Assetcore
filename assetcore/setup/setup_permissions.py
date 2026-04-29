# Copyright (c) 2026, AssetCore Team
"""
AssetCore RBAC cleanup helper.

Source of truth cho permissions: block `permissions` trong từng DocType JSON
(`assetcore/doctype/<dt>/<dt>.json`). Frappe tự sync vào tabDocPerm khi chạy
`bench migrate` hoặc `bench install-app`.

File này chỉ chịu trách nhiệm:
  1. Xóa DocPerm của role legacy (HTM Technician, Workshop Manager, ...) còn
     sót lại từ phiên bản trước.
  2. Disable Role legacy để không ai gán nhầm.

Wire vào hooks.after_install / hooks.after_migrate.

Chạy thủ công:
    bench --site <site> execute assetcore.setup.setup_permissions.run
"""
from __future__ import annotations

import frappe

# Role legacy đã được thay thế bằng các role IMM canonical.
# Giữ ở đây làm SOT cho cleanup — đồng bộ với setup_role_profiles._LEGACY_ROLES.
_LEGACY_ROLES: tuple[str, ...] = (
    "IMM Manager",
    "Kho vật tư",
    "Workshop Manager",
    "Clinical Head",
    "CMMS Admin",
    "Tổ HC-QLCL",
    "QA Risk Team",
    "HTM Technician",
    "VP Block2",
    "Workshop Head",
    "Biomed Engineer",
)


def _delete_legacy_docperms() -> int:
    """Xóa các DocPerm row tham chiếu role legacy. Đảm bảo không tồn tại
    permission đè vào DocType từ thời JSON cũ."""
    rows = frappe.get_all(
        "DocPerm",
        filters={"role": ("in", list(_LEGACY_ROLES))},
        fields=["name"],
    )
    for r in rows:
        try:
            frappe.delete_doc("DocPerm", r["name"], ignore_permissions=True, force=True)
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"Delete legacy DocPerm {r['name']} failed",
            )
    # Custom DocPerm (override layer) — cũng dọn để chắc chắn
    custom_rows = frappe.get_all(
        "Custom DocPerm",
        filters={"role": ("in", list(_LEGACY_ROLES))},
        fields=["name"],
    )
    for r in custom_rows:
        try:
            frappe.delete_doc("Custom DocPerm", r["name"], ignore_permissions=True, force=True)
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"Delete legacy Custom DocPerm {r['name']} failed",
            )
    return len(rows) + len(custom_rows)


def _strip_legacy_has_role() -> int:
    """Bỏ Has Role rows trên User trỏ tới role legacy."""
    rows = frappe.get_all(
        "Has Role",
        filters={
            "parenttype": "User",
            "role": ("in", list(_LEGACY_ROLES)),
        },
        fields=["name"],
    )
    for r in rows:
        try:
            frappe.delete_doc("Has Role", r["name"], ignore_permissions=True, force=True)
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"Delete legacy Has Role {r['name']} failed",
            )
    return len(rows)


def run() -> None:
    """Cleanup legacy role DocPerm + Has Role. Idempotent."""
    deleted_perms = _delete_legacy_docperms()
    stripped = _strip_legacy_has_role()
    frappe.db.commit()
    print(
        f"[AssetCore] RBAC cleanup: {deleted_perms} legacy DocPerm xóa, "
        f"{stripped} Has Role row gỡ khỏi User."
    )
