# Copyright (c) 2026, AssetCore Team
"""
Seed Role Profile (Frappe core DocType) — persona AssetCore.

Tên profile dùng prefix "IMM - " (English) để khớp fixtures/role_profile.json
và tránh phụ thuộc encoding tiếng Việt khi import/export giữa môi trường.

Idempotent: chạy lại sẽ update bundle role; xóa profile legacy (Vietnamese cũ
hoặc obsolete) và disable role legacy.

Chạy thủ công:
    bench --site <site> execute assetcore.setup.setup_role_profiles.run
Tự chạy: hooks.after_install / hooks.after_migrate
"""
from __future__ import annotations

import frappe
from assetcore.services.shared.constants import Roles

# ── Canonical persona matrix (khớp fixtures/role_profile.json) ────────────────
_PROFILES: list[tuple[str, list[str]]] = [
    ("IMM - System Administrator",   [Roles.SYS_ADMIN]),
    ("IMM - Operations Manager",     [Roles.OPS_MANAGER]),
    ("IMM - Department Head",        [Roles.DEPT_HEAD]),
    ("IMM - Deputy Department Head", [Roles.DEPT_DEPUTY]),
    ("IMM - Workshop Lead",          [Roles.WORKSHOP, Roles.BIOMED]),
    ("IMM - Biomed Technician",      [Roles.BIOMED, Roles.TECHNICIAN]),
    ("IMM - Field Technician",       [Roles.TECHNICIAN]),
    ("IMM - QA Officer",             [Roles.QA, Roles.AUDITOR]),
    ("IMM - Internal Auditor",       [Roles.AUDITOR]),
    ("IMM - Storekeeper",            [Roles.STOREKEEPER]),
    ("IMM - Document Officer",       [Roles.DOC_OFFICER]),
    ("IMM - Clinical User",          [Roles.CLINICAL]),
    ("IMM - Vendor Engineer",        [Roles.VENDOR_ENGINEER]),
]

# Profile cũ (tiếng Việt từ phiên bản trước) — sẽ xóa nếu tồn tại
_LEGACY_PROFILES: list[str] = [
    "IMM - Quản trị hệ thống",
    "IMM - Trưởng phòng TBYT",
    "IMM - Trưởng khoa",
    "IMM - Phó khoa",
    "IMM - Tổ trưởng xưởng",
    "IMM - Cán bộ QLCL",
    "IMM - Nhân viên kỹ thuật",
    "IMM - Cán bộ hồ sơ",
    "IMM - Thủ kho",
    "IMM - Bác sĩ / Điều dưỡng",
    "IMM - Kiểm toán viên",
]

# Role legacy (sẽ disabled — không xóa để khỏi vỡ Has Role rows lịch sử)
_LEGACY_ROLES: list[str] = [
    "IMM Manager", "Kho vật tư", "Workshop Manager", "Clinical Head",
    "CMMS Admin", "Tổ HC-QLCL", "QA Risk Team", "HTM Technician",
    "VP Block2", "Workshop Head", "Biomed Engineer",
]


def _upsert_role_profile(profile_name: str, role_names: list[str]) -> str:
    """Tạo/cập nhật Role Profile. Returns: inserted | updated | skipped."""
    valid_roles = [r for r in role_names if frappe.db.exists("Role", r)]
    if not valid_roles:
        return "skipped"

    if frappe.db.exists("Role Profile", profile_name):
        doc = frappe.get_doc("Role Profile", profile_name)
        current = {r.role for r in doc.roles}
        if current == set(valid_roles):
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


def _delete_legacy_profiles() -> int:
    """Xóa Role Profile cũ (Vietnamese names). Trước khi xóa, bỏ tham chiếu
    `User.role_profile_name` để tránh foreign-key error."""
    deleted = 0
    for name in _LEGACY_PROFILES:
        if not frappe.db.exists("Role Profile", name):
            continue
        # Bỏ tham chiếu trên User trước khi xóa profile
        frappe.db.set_value(
            "User",
            {"role_profile_name": name},
            "role_profile_name",
            None,
        )
        try:
            frappe.delete_doc("Role Profile", name, ignore_permissions=True, force=True)
            deleted += 1
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"Delete legacy Role Profile {name} failed",
            )
    return deleted


def _disable_legacy_roles() -> int:
    """Disable role legacy — không delete để giữ Has Role rows lịch sử,
    nhưng đảm bảo role không còn tác dụng + ẩn khỏi UI gán role."""
    disabled = 0
    for name in _LEGACY_ROLES:
        if not frappe.db.exists("Role", name):
            continue
        if frappe.db.get_value("Role", name, "disabled"):
            continue
        frappe.db.set_value("Role", name, "disabled", 1)
        disabled += 1
    return disabled


def run() -> None:
    """Seed/update Role Profile + cleanup legacy. Idempotent."""
    stats = {"inserted": 0, "updated": 0, "skipped": 0}
    for profile_name, role_names in _PROFILES:
        stats[_upsert_role_profile(profile_name, role_names)] += 1

    legacy_deleted = _delete_legacy_profiles()
    roles_disabled = _disable_legacy_roles()
    frappe.db.commit()

    print(
        f"[AssetCore] Role Profiles: {stats['inserted']} tạo mới, "
        f"{stats['updated']} cập nhật, {stats['skipped']} bỏ qua. "
        f"Legacy: {legacy_deleted} profile xóa, {roles_disabled} role disabled."
    )
