# Copyright (c) 2026, AssetCore Team
"""
IMM-00 Setup — tạo Custom Fields bổ sung cho Frappe User DocType.

Chạy sau khi install/migrate:
  bench --site <site> migrate
  (after_install và after_migrate hooks tự gọi hàm này)
"""
from __future__ import annotations

import frappe

# ── Custom fields cần thêm vào tabUser ────────────────────────────────────────
_USER_CUSTOM_FIELDS: list[dict] = [
    {
        "fieldname": "imm_section",
        "fieldtype": "Section Break",
        "label": "IMM AssetCore",
        "insert_after": "enabled",
    },
    {
        "fieldname": "imm_approval_status",
        "fieldtype": "Select",
        "label": "Trạng thái duyệt IMM",
        "options": "Pending\nApproved\nRejected",
        "default": "Pending",
        "insert_after": "imm_section",
        "in_list_view": 0,
    },
    {
        "fieldname": "imm_approved_by",
        "fieldtype": "Link",
        "label": "Duyệt bởi",
        "options": "User",
        "insert_after": "imm_approval_status",
        "read_only": 1,
    },
    {
        "fieldname": "imm_approved_at",
        "fieldtype": "Datetime",
        "label": "Thời điểm duyệt",
        "insert_after": "imm_approved_by",
        "read_only": 1,
    },
    {
        "fieldname": "imm_rejection_reason",
        "fieldtype": "Small Text",
        "label": "Lý do từ chối",
        "insert_after": "imm_approved_at",
    },
    {
        "fieldname": "ac_department",
        "fieldtype": "Link",
        "label": "Khoa / Phòng (AssetCore)",
        "options": "AC Department",
        "insert_after": "imm_rejection_reason",
    },
]


def _ensure_custom_field(dt: str, fieldname: str, definition: dict) -> None:
    """Tạo Custom Field nếu chưa tồn tại."""
    existing = frappe.db.exists("Custom Field", {"dt": dt, "fieldname": fieldname})
    if existing:
        return
    cf = frappe.new_doc("Custom Field")
    cf.dt = dt
    cf.fieldname = fieldname
    for k, v in definition.items():
        if k != "fieldname":
            cf.set(k, v)
    cf.flags.ignore_permissions = True
    cf.insert(ignore_if_duplicate=True)


def create_user_custom_fields() -> None:
    """Tạo toàn bộ custom fields cho User nếu chưa có."""
    for field_def in _USER_CUSTOM_FIELDS:
        fieldname = field_def["fieldname"]
        if fieldname.endswith("_section"):
            # Section Break không cần check column
            _ensure_custom_field("User", fieldname, field_def)
        else:
            if not frappe.db.has_column("User", fieldname):
                _ensure_custom_field("User", fieldname, field_def)

    frappe.db.commit()


def after_install() -> None:
    create_user_custom_fields()
    _apply_rbac_matrix()
    _seed_role_profiles()
    _apply_core_permissions()


def after_migrate() -> None:
    create_user_custom_fields()
    _apply_rbac_matrix()
    _seed_role_profiles()
    _apply_core_permissions()
    _install_notifications()


def _install_notifications() -> None:
    """Sync 7 IMM Notification rules — idempotent."""
    try:
        from assetcore.notifications.setup import install_notifications
        result = install_notifications()
        print(f"[AssetCore] Notifications: {result['count']} rule(s) đã sync.")
    except Exception as e:
        print(f"[AssetCore] Notification install failed: {e}")


def _apply_rbac_matrix() -> None:
    """Cleanup legacy DocPerm/Has Role. Import locally để tránh circular."""
    try:
        from assetcore.setup.setup_permissions import run as apply_permissions
        apply_permissions()
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "AssetCore RBAC: setup_permissions.run failed",
        )


def _seed_role_profiles() -> None:
    """Tạo Role Profile cho các persona AssetCore + cleanup legacy."""
    try:
        from assetcore.setup.setup_role_profiles import run as seed
        seed()
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "AssetCore Role Profiles: setup_role_profiles.run failed",
        )


def _apply_core_permissions() -> None:
    """Custom DocPerm cho Frappe core DocType — IMM role tự đủ quyền dùng desk."""
    try:
        from assetcore.setup.setup_core_permissions import run as apply_core
        apply_core()
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "AssetCore Core Permissions: setup_core_permissions.run failed",
        )
