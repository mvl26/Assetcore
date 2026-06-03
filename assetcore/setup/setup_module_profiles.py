# Copyright (c) 2026, AssetCore Team
"""
Legacy Module Profile cleanup — mô hình RBAC mới KHÔNG dùng Module Profile.

Mô hình trước có 3 Module Profile (`IMM - Admin`, `IMM - Standard`, `IMM - Vendor`).
RBAC module-based bỏ Module Profile — Workspace/module visibility được kiểm soát
bằng vai trò của Workspace (`Workspace.roles`) + sidebar FE đọc capability từ
`rbac.get_capabilities()`.

File này chỉ giữ logic dọn legacy Module Profile khỏi DB. Idempotent.

Chạy thủ công:
    bench --site <site> execute assetcore.setup.setup_module_profiles.run
"""
from __future__ import annotations

import frappe

_LEGACY_MODULE_PROFILES: list[str] = [
    "IMM - Admin",
    "IMM - Standard",
    "IMM - Vendor",
]


def _delete_legacy_module_profiles() -> int:
    deleted = 0
    for name in _LEGACY_MODULE_PROFILES:
        if not frappe.db.exists("Module Profile", name):
            continue
        # Bỏ tham chiếu trên User trước khi xóa profile
        frappe.db.set_value(
            "User",
            {"module_profile": name},
            "module_profile",
            None,
        )
        try:
            frappe.delete_doc(
                "Module Profile", name,
                ignore_permissions=True, force=True,
            )
            deleted += 1
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"Delete legacy Module Profile {name} failed",
            )
    return deleted


def run() -> None:
    """Cleanup legacy Module Profile. Idempotent."""
    deleted = _delete_legacy_module_profiles()
    frappe.db.commit()
    print(f"[AssetCore] Legacy Module Profile cleanup: {deleted} xóa.")
