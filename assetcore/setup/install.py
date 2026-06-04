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
        # Empty option đầu = "chưa thuộc luồng duyệt IMM" (vd: Administrator, user
        # ERPNext gốc). KHÔNG để default "Pending": default cũ khiến MỌI user tạo
        # ngoài luồng self-signup (test fixture, desk, bench, import) bị gán Pending
        # dù enabled=1 → badge "Chờ duyệt" giả, không có gate thật phía sau.
        # Invariant: Pending ⟺ enabled=0 (chờ admin). enabled=1 ⇒ Approved/empty.
        "options": "\nPending\nApproved\nRejected",
        "default": "",
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

    _reconcile_approval_status_field()
    frappe.db.commit()


def _reconcile_approval_status_field() -> None:
    """Idempotent: gỡ default 'Pending' lệch trên Custom Field đã tồn tại.

    Site cũ đã insert Custom Field với default='Pending'. Đổi định nghĩa trong
    _USER_CUSTOM_FIELDS không tự cập nhật record đã có (ensure chỉ insert-if-missing).
    Hàm này ép default về '' và options về '\\nPending\\nApproved\\nRejected' để mọi
    user mới tạo ngoài luồng IMM không bị gán 'Pending' giả.
    """
    cf = frappe.db.exists("Custom Field", {"dt": "User", "fieldname": "imm_approval_status"})
    if not cf:
        return
    current_default = frappe.db.get_value("Custom Field", cf, "default")
    if current_default == "Pending":
        frappe.db.set_value(
            "Custom Field", cf,
            {"default": "", "options": "\nPending\nApproved\nRejected"},
        )


def after_install() -> None:
    _sync_workflows()
    _seed_uoms()
    create_user_custom_fields()
    _apply_erpnext_asset_custom_fields()
    _apply_rbac_matrix()
    _seed_role_profiles()
    _seed_module_profiles()
    _apply_core_permissions()
    _build_frontend(force=True)


def before_migrate() -> None:
    """Xóa Has Role orphan rows thuộc AssetCore Role Profiles trước khi fixture sync.
    Ngăn lỗi 'already has the role' khi Frappe delete+reinsert Role Profile fixture."""
    _clear_role_profile_has_role_rows()


def after_migrate() -> None:
    _sync_workflows()
    _seed_uoms()
    create_user_custom_fields()
    _apply_erpnext_asset_custom_fields()
    _apply_rbac_matrix()
    _seed_role_profiles()
    _seed_module_profiles()
    _apply_core_permissions()
    _install_notifications()
    _bust_capability_cache()
    _build_frontend(force=False)


def _bust_capability_cache() -> None:
    """BE-2 (USER REWORK IMM-14): sau khi DocPerm/Role/Role Profile da sync
    (rbac matrix + role profiles + core perms), bust toan bo cache Redis
    `ac_caps::*` → cap moi (vd decommission.*) toi FE NGAY lan goi
    get_capabilities dau tien sau deploy, KHONG doi TTL 1h.

    Idempotent + best-effort: loi cache KHONG duoc chan migrate."""
    try:
        from assetcore.services.shared import rbac

        rbac.invalidate_capabilities()
        print(f"[AssetCore] ac_caps::* busted (cap-set {rbac.CAP_SET_VERSION})")
    except Exception as e:  # noqa: BLE001
        frappe.log_error(
            f"_bust_capability_cache failed: {e}", "AssetCore after_migrate"
        )


def _seed_uoms() -> None:
    """Seed AC UOM master data (idempotent).

    AC Asset.uom mặc định là "Cái"; nếu master UOM chưa tồn tại thì mọi insert
    AC Asset sẽ throw LinkValidationError. Seed ở đây để fresh site / site drift
    luôn có bộ UOM chuẩn — không phụ thuộc one-time patch v3_0.
    """
    try:
        from assetcore.services.uom import seed_ac_uoms

        created = seed_ac_uoms()
        if created:
            print(f"[AssetCore] AC UOM seeded: {created}")
    except Exception as e:  # noqa: BLE001 — không chặn migrate vì UOM seed lỗi
        print(f"[AssetCore] AC UOM seed error: {e}")


def _import_workflow_file(fpath: str) -> set[str]:
    """Import một workflow JSON, trả về tập states tìm thấy."""
    import json as _json
    from frappe.modules.import_file import import_doc as _import_doc

    with open(fpath) as f:
        docdict = _json.load(f)
    _import_doc(docdict, path=fpath)
    states = {row["state"] for row in (docdict.get("states") or []) if row.get("state")}
    print(f"[AssetCore] Workflow synced: {docdict.get('workflow_name') or fpath}")
    return states


def _ensure_workflow_state(state_name: str) -> None:
    if frappe.db.exists("Workflow State", state_name):
        return
    try:
        ws = frappe.new_doc("Workflow State")
        ws.workflow_state_name = state_name
        ws.flags.ignore_permissions = True
        ws.insert(ignore_if_duplicate=True)
    except Exception as e:
        print(f"[AssetCore] Workflow State create error ({state_name!r}): {e}")


def _sync_workflows() -> None:
    """Import all AssetCore workflow JSON files and ensure Workflow State master records exist."""
    import os

    workflow_dir = frappe.get_app_path("assetcore", "assetcore", "workflow")
    if not os.path.exists(workflow_dir):
        return

    all_states: set[str] = set()
    for fname in sorted(os.listdir(workflow_dir)):
        if not fname.endswith(".json"):
            continue
        try:
            all_states |= _import_workflow_file(os.path.join(workflow_dir, fname))
        except Exception as e:
            print(f"[AssetCore] Workflow sync error ({fname}): {e}")

    for state_name in sorted(all_states):
        _ensure_workflow_state(state_name)

    frappe.db.commit()


def _apply_erpnext_asset_custom_fields() -> None:
    """Áp dụng custom fields HTM lên ERPNext Asset — chỉ khi ERPNext đã cài."""
    import json as _json
    import os
    from frappe.modules.import_file import import_doc as _import_doc

    if not frappe.db.exists("DocType", "Asset"):
        return

    json_path = frappe.get_app_path(
        "assetcore", "assetcore", "config", "erpnext_integration", "asset_custom_fields.json"
    )
    if not os.path.exists(json_path):
        return

    try:
        with open(json_path) as f:
            docs = _json.load(f)
        for doc in docs:
            _import_doc(doc, path=json_path)
        frappe.db.commit()
        print(f"[AssetCore] ERPNext Asset custom fields applied ({len(docs)} fields).")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "AssetCore: apply ERPNext Asset custom fields failed")
        print(f"[AssetCore] ERPNext Asset custom fields warning: {e}")


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
    """Tạo 8 Role Profile AssetCore (bộ role chọn sẵn) + cleanup legacy."""
    try:
        from assetcore.setup.setup_role_profiles import run as seed
        seed()
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "AssetCore Role Profiles: setup_role_profiles.run failed",
        )


def _seed_module_profiles() -> None:
    """Tạo Module Profile kiểm soát sidebar visibility cho từng nhóm user."""
    try:
        from assetcore.setup.setup_module_profiles import run as seed
        seed()
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "AssetCore Module Profiles: setup_module_profiles.run failed",
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


def _build_frontend(force: bool = False) -> None:
    """Wrapper — build Vue SPA, không raise exception để không block install."""
    try:
        from assetcore.setup.setup_frontend import build_frontend
        build_frontend(force=force)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "AssetCore FE build failed")


def _clear_role_profile_has_role_rows() -> None:
    """Xóa Has Role rows thuộc AssetCore Role Profiles khỏi DB.

    Frappe fixture import (delete_old_doc → frappe.delete_doc with for_reload=True)
    không xóa được child Has Role rows khi chạy migrate. Nếu after_migrate đã chạy
    lần trước (thêm rows qua setup_role_profiles.run), lần migrate kế tiếp sẽ fail
    với ValidationError 'already has the role'. Hook before_migrate gọi hàm này để
    làm sạch trước khi fixture sync bắt đầu.
    """
    try:
        from assetcore.setup.role_profile_catalog import PROFILE_NAMES
        # Dọn Has Role rows của 8 Role Profile hiện hành (tên VI) + legacy
        # "AssetCore — %" còn sót, trước khi fixture sync re-insert.
        deleted = frappe.db.delete(
            "Has Role",
            {
                "parenttype": "Role Profile",
                "parent": ["in", PROFILE_NAMES],
            },
        )
        deleted += frappe.db.delete(
            "Has Role",
            {"parenttype": "Role Profile", "parent": ["like", "AssetCore — %"]},
        )
        if deleted:
            frappe.db.commit()
            print(f"[AssetCore] before_migrate: cleared {deleted} Has Role rows (Role Profile).")
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "AssetCore before_migrate: _clear_role_profile_has_role_rows failed",
        )
