# Copyright (c) 2026, AssetCore Team
"""Seed 8 Role Profile (tên VI) + dọn Role Profile legacy.

Core Doc: docs/architecture/FE_Persona_Navigation.md §7.quinquies (BE = Role
Profile + Role Permission chuẩn Frappe; "persona" là khái niệm FE-only).

`run()`:
  1. seed_assetcore_role_profiles() — tạo/cập nhật 8 Role Profile (tên VI thuần),
     mỗi profile chứa đúng bộ role catalog (role_profile_catalog.py). Idempotent.
  2. dọn Role Profile legacy ("IMM - *", "AssetCore — *") nếu còn sót — KHÔNG đụng
     8 profile mới vì tên VI thuần không trùng danh sách legacy.

Catalog SSOT ở `assetcore.setup.role_profile_catalog` — KHÔNG hardcode role ở đây.

Chạy thủ công:
    bench --site <site> execute assetcore.setup.setup_role_profiles.run
"""
from __future__ import annotations

import frappe

from assetcore.setup.role_profile_catalog import (
    PROFILE_NAMES,
    profile_name_to_roles,
)

_DT_ROLE_PROFILE = "Role Profile"

# Role Profile legacy cần xoá nếu còn sót (Vietnamese "IMM - *" + AssetCore-branded
# "AssetCore — *"). 8 profile mới dùng tên VI thuần -> KHÔNG nằm trong list này.
_LEGACY_PROFILES: list[str] = [
    "IMM - Quản trị hệ thống", "IMM - Trưởng phòng TBYT", "IMM - Trưởng khoa",
    "IMM - Phó khoa", "IMM - Tổ trưởng xưởng", "IMM - Cán bộ QLCL",
    "IMM - Nhân viên kỹ thuật", "IMM - Cán bộ hồ sơ", "IMM - Thủ kho",
    "IMM - Bác sĩ / Điều dưỡng", "IMM - Kiểm toán viên",
    "IMM - Biomed Technician", "IMM - Board Approver", "IMM - Clinical User",
    "IMM - Department Head", "IMM - Deputy Department Head", "IMM - Document Officer",
    "IMM - Field Technician", "IMM - Finance Officer", "IMM - HTM Engineer",
    "IMM - Internal Auditor", "IMM - Operations Manager", "IMM - Planning Officer",
    "IMM - Procurement Officer", "IMM - QA Officer", "IMM - Risk Officer",
    "IMM - Storekeeper", "IMM - System Administrator", "IMM - Training Officer",
    "IMM - Vendor Engineer", "IMM - Workshop Lead",
    "AssetCore — System Admin", "AssetCore — Operations Manager",
    "AssetCore — Department Head", "AssetCore — Department Deputy",
    "AssetCore — Workshop Lead", "AssetCore — Biomed Technician",
    "AssetCore — Technician", "AssetCore — Clinical User", "AssetCore — QA Officer",
    "AssetCore — Auditor", "AssetCore — Storekeeper", "AssetCore — Document Officer",
    "AssetCore — Planning Officer", "AssetCore — Procurement Officer",
    "AssetCore — Vendor Engineer", "AssetCore — Training Officer",
]


def _upsert_role_profile(name: str, roles: list[str]) -> str:
    """Tạo/cập nhật 1 Role Profile với đúng bộ role. Trả 'created'|'updated'|'unchanged'."""
    # Chỉ gán role thực sự tồn tại (fail-safe nếu role chưa migrate).
    valid_roles = [r for r in roles if frappe.db.exists("Role", r)]

    if not frappe.db.exists(_DT_ROLE_PROFILE, name):
        doc = frappe.new_doc(_DT_ROLE_PROFILE)
        doc.role_profile = name
        for r in valid_roles:
            doc.append("roles", {"role": r})
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)
        return "created"

    doc = frappe.get_doc(_DT_ROLE_PROFILE, name)
    current = {row.role for row in doc.roles}
    target = set(valid_roles)
    if current == target:
        return "unchanged"
    # Set lại đúng bộ role (clear + re-append) — idempotent, không nhân đôi.
    doc.set("roles", [])
    for r in valid_roles:
        doc.append("roles", {"role": r})
    doc.flags.ignore_permissions = True
    doc.save(ignore_permissions=True)
    return "updated"


def seed_assetcore_role_profiles() -> dict[str, str]:
    """Tạo/cập nhật 8 Role Profile. Idempotent. Trả {name: outcome}."""
    results: dict[str, str] = {}
    for name, roles in profile_name_to_roles().items():
        results[name] = _upsert_role_profile(name, roles)
    frappe.db.commit()
    return results


def _delete_legacy_profiles() -> int:
    """Xoá Role Profile legacy + bỏ tham chiếu User.role_profile_name."""
    deleted = 0
    for name in _LEGACY_PROFILES:
        if name in PROFILE_NAMES:
            continue  # never delete a current profile
        if not frappe.db.exists(_DT_ROLE_PROFILE, name):
            continue
        frappe.db.set_value("User", {"role_profile_name": name}, "role_profile_name", None)
        frappe.db.delete("Has Role", {"parenttype": _DT_ROLE_PROFILE, "parent": name})
        try:
            frappe.delete_doc(_DT_ROLE_PROFILE, name, ignore_permissions=True, force=True)
            deleted += 1
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"Delete legacy Role Profile {name} failed")
    return deleted


def run() -> dict:
    """Seed 8 Role Profile + dọn legacy. Idempotent."""
    seeded = seed_assetcore_role_profiles()
    legacy_deleted = _delete_legacy_profiles()
    frappe.db.commit()
    created = sum(1 for v in seeded.values() if v == "created")
    updated = sum(1 for v in seeded.values() if v == "updated")
    print(
        f"[AssetCore] Role Profile seed: {created} created, {updated} updated, "
        f"{len(seeded) - created - updated} unchanged; {legacy_deleted} legacy xoá."
    )
    return {"seeded": seeded, "legacy_deleted": legacy_deleted}
