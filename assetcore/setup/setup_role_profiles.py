# Copyright (c) 2026, AssetCore Team
"""
Seed Role Profile (Frappe core DocType) cho các persona nghiệp vụ AssetCore.

Role Profile là concept native của Frappe — gom nhiều Role thành 1 bundle.
Khi gán Role Profile cho User (field `User.role_profile_name`), Frappe tự động
sync các Role trong profile vào user.roles.

Idempotent: chạy lại nhiều lần sẽ update, không duplicate.

Chạy:
    bench --site <site> execute assetcore.setup.setup_role_profiles.run
"""
from __future__ import annotations

import frappe
from assetcore.services.shared.constants import Roles

# ── Persona → Role bundle ─────────────────────────────────────────────────────
# Tên profile dùng prefix "IMM - " để dễ nhận biết; mô tả ngắn gọn nghiệp vụ.
#
# Lưu ý: mỗi User chỉ gán 1 Role Profile (Frappe single Link field), nên các
# persona cần bao gồm đầy đủ role mà vai trò đó thực sự cần. Ví dụ Workshop Lead
# vừa cần Lead role vừa cần Technician role để tự thao tác khi cần.

_PROFILES: list[tuple[str, list[str]]] = [
    ("IMM - Quản trị hệ thống", [
        Roles.SYS_ADMIN,
        Roles.OPS_MANAGER,
    ]),
    ("IMM - Trưởng phòng TBYT", [
        Roles.OPS_MANAGER,
    ]),
    ("IMM - Trưởng khoa", [
        Roles.DEPT_HEAD,
        Roles.CLINICAL,
    ]),
    ("IMM - Phó khoa", [
        Roles.DEPT_DEPUTY,
        Roles.CLINICAL,
    ]),
    ("IMM - Tổ trưởng xưởng", [
        Roles.WORKSHOP,
        Roles.BIOMED,
    ]),
    ("IMM - Cán bộ QLCL", [
        Roles.QA,
    ]),
    ("IMM - Nhân viên kỹ thuật", [
        Roles.BIOMED,
    ]),
    ("IMM - Cán bộ hồ sơ", [
        Roles.DOC_OFFICER,
    ]),
    ("IMM - Thủ kho", [
        Roles.STOREKEEPER,
    ]),
    ("IMM - Bác sĩ / Điều dưỡng", [
        Roles.CLINICAL,
    ]),
    ("IMM - Kiểm toán viên", [
        Roles.AUDITOR,
    ]),
]


def _upsert_role_profile(profile_name: str, role_names: list[str]) -> str:
    """Tạo mới hoặc cập nhật Role Profile với danh sách role.

    Dùng frappe.get_doc trên DocType core — không modify core.
    Returns: 'inserted' | 'updated' | 'skipped'.
    """
    # Chỉ giữ role thực sự tồn tại
    valid_roles = [r for r in role_names if frappe.db.exists("Role", r)]
    if not valid_roles:
        return "skipped"

    if frappe.db.exists("Role Profile", profile_name):
        doc = frappe.get_doc("Role Profile", profile_name)
        current = {r.role for r in doc.roles}
        target = set(valid_roles)
        if current == target:
            return "skipped"
        doc.roles = []
        for role in valid_roles:
            doc.append("roles", {"role": role})
        doc.flags.ignore_permissions = True
        doc.save()
        return "updated"

    doc = frappe.new_doc("Role Profile")
    doc.role_profile = profile_name
    for role in valid_roles:
        doc.append("roles", {"role": role})
    doc.flags.ignore_permissions = True
    doc.insert()
    return "inserted"


def run() -> None:
    """Seed/update toàn bộ Role Profile. Idempotent."""
    stats = {"inserted": 0, "updated": 0, "skipped": 0}
    for profile_name, role_names in _PROFILES:
        result = _upsert_role_profile(profile_name, role_names)
        stats[result] += 1

    frappe.db.commit()
    print(
        f"[AssetCore] Role Profiles: {stats['inserted']} tạo mới, "
        f"{stats['updated']} cập nhật, {stats['skipped']} bỏ qua."
    )
