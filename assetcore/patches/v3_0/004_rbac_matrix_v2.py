# Copyright (c) 2026, AssetCore Team
"""
Patch 004 — RBAC Matrix v2

Áp dụng ma trận phân quyền mới cho AssetCore với 11 role nghiệp vụ tách biệt:
Admin, Operations Manager, Department Head, Deputy Department Head,
Workshop Lead, QA Officer, Biomed Technician, Document Officer,
Storekeeper, Clinical User, Auditor.

Idempotent — có thể chạy lại nhiều lần. Không xóa role legacy (IMM Technician,
IMM System Admin, IMM Workshop Lead, IMM Operations Manager, IMM Biomed Technician, IMM QA Officer, IMM Department Head)
để tránh vỡ các user/workflow đang dùng.
"""
from __future__ import annotations

import frappe


def execute() -> None:
    # ── DEPRECATED ──
    # Mô hình RBAC mới (RBAC module-based, xem patches/v3_2/001) đã bỏ 19
    # persona role này. Patch v3_2/001 chạy SAU patch này sẽ xóa hẳn các role
    # legacy. Trên môi trường mới, patch này không cần tạo role (Roles do
    # fixtures/role.json sinh + patch v3_2/001 dọn legacy).
    # Giữ patch để Patch Log không lỗi; thực thi no-op.
    from assetcore.setup.setup_permissions import run as apply_permissions
    apply_permissions()


def _ensure_roles(roles: list[str]) -> None:
    for role_name in roles:
        if frappe.db.exists("Role", role_name):
            continue
        frappe.get_doc({
            "doctype": "Role",
            "role_name": role_name,
            "desk_access": 1,
            "disabled": 0,
        }).insert(ignore_permissions=True)
    frappe.db.commit()
