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
    # Tạo role mới (nếu chưa có) trước khi apply matrix
    _ensure_roles([
        "IMM System Admin",
        "IMM Operations Manager",
        "IMM Department Head",
        "IMM Deputy Department Head",
        "IMM Workshop Lead",
        "IMM QA Officer",
        "IMM Biomed Technician",
        "IMM Technician",
        "IMM Document Officer",
        "IMM Storekeeper",
        "IMM Clinical User",
        "IMM Auditor",
    ])

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
