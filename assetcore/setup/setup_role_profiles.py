# Copyright (c) 2026, AssetCore Team
"""
Legacy Role Profile cleanup — mô hình RBAC mới KHÔNG dùng Role Profile.

Sau khi chuyển sang RBAC module-based (4 System + 26 Domain roles, xem
`assetcore.services.shared.constants.Roles` + `services.shared.rbac`):

  - **Không tạo** Role Profile / Module Profile.
  - Gán role trực tiếp qua `Has Role` (Frappe User form HOẶC trang FE
    `/admin/roles`).

File này chỉ giữ logic dọn legacy Role Profile (Vietnamese & "IMM - *" English),
**xóa hẳn** persona Role + AssetCore-branded Role Profile cũ. Idempotent.

Hooks: chạy ở after_install / after_migrate để dọn sạch site cũ.

Chạy thủ công:
    bench --site <site> execute assetcore.setup.setup_role_profiles.run
"""
from __future__ import annotations

import frappe

# Mọi Role Profile cần xóa nếu còn sót — gồm:
#  (a) legacy Vietnamese & "IMM - *" English (đã có patch v3_1/005 nhưng đảm
#      bảo nếu admin tạo lại bằng tên cũ vẫn được dọn);
#  (b) AssetCore-branded persona catalog cũ (mô hình mới bỏ Role Profile).
_LEGACY_PROFILES: list[str] = [
    # ── (a) Vietnamese (rất cũ) ─────────────────────────────────────────
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
    # ── (a) English "IMM - *" — thay thế bởi AssetCore — *, giờ cũng bỏ ──
    "IMM - Biomed Technician",
    "IMM - Board Approver",
    "IMM - Clinical User",
    "IMM - Department Head",
    "IMM - Deputy Department Head",
    "IMM - Document Officer",
    "IMM - Field Technician",
    "IMM - Finance Officer",
    "IMM - HTM Engineer",
    "IMM - Internal Auditor",
    "IMM - Operations Manager",
    "IMM - Planning Officer",
    "IMM - Procurement Officer",
    "IMM - QA Officer",
    "IMM - Risk Officer",
    "IMM - Storekeeper",
    "IMM - System Administrator",
    "IMM - Training Officer",
    "IMM - Vendor Engineer",
    "IMM - Workshop Lead",
    # ── (b) AssetCore-branded persona catalog cũ ────────────────────────
    "AssetCore — System Admin",
    "AssetCore — Operations Manager",
    "AssetCore — Department Head",
    "AssetCore — Department Deputy",
    "AssetCore — Workshop Lead",
    "AssetCore — Biomed Technician",
    "AssetCore — Technician",
    "AssetCore — Clinical User",
    "AssetCore — QA Officer",
    "AssetCore — Auditor",
    "AssetCore — Storekeeper",
    "AssetCore — Document Officer",
    "AssetCore — Planning Officer",
    "AssetCore — Procurement Officer",
    "AssetCore — Vendor Engineer",
    "AssetCore — Training Officer",
]

# Role legacy (xóa hẳn — phần lớn đã được patch v3_2/001 detach + delete; ở đây
# chỉ dọn vớt nếu sót, idempotent). Mở rộng theo plan §4.1 Step 3c (19 persona
# + 11 legacy).
_LEGACY_ROLES: tuple[str, ...] = (
    # ── (a) 11 legacy cũ (đã được disable trước đó) ─────────────────────
    "IMM Manager", "Kho vật tư", "Workshop Manager", "Clinical Head",
    "CMMS Admin", "Tổ HC-QLCL", "QA Risk Team", "HTM Technician",
    "VP Block2", "Workshop Head", "Biomed Engineer",
    # ── (b) 19 persona "IMM *" cũ ───────────────────────────────────────
    "IMM System Admin", "IMM Operations Manager", "IMM Department Head",
    "IMM Deputy Department Head", "IMM Workshop Lead", "IMM QA Officer",
    "IMM Biomed Technician", "IMM Technician", "IMM Document Officer",
    "IMM Storekeeper", "IMM Clinical User", "IMM Auditor",
    "IMM Planning Officer", "IMM Finance Officer", "IMM HTM Engineer",
    "IMM Procurement Officer", "IMM Risk Officer", "IMM Board Approver",
    "IMM Training Officer",
)


def _delete_legacy_profiles() -> int:
    """Xóa Role Profile cũ + bỏ tham chiếu User.role_profile_name."""
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
        # Xóa Has Role rows con
        frappe.db.delete(
            "Has Role",
            {"parenttype": "Role Profile", "parent": name},
        )
        try:
            frappe.delete_doc(
                "Role Profile", name,
                ignore_permissions=True, force=True,
            )
            deleted += 1
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"Delete legacy Role Profile {name} failed",
            )
    return deleted


def _delete_legacy_roles() -> int:
    """Xóa hẳn role legacy + persona "IMM *" cũ. KHÔNG đụng tới role do app
    khác / Frappe core sở hữu (`System Manager`, `Internal Auditor`,
    `Norm Manager` ...). Idempotent."""
    deleted = 0
    for name in _LEGACY_ROLES:
        if not frappe.db.exists("Role", name):
            continue
        # Detach khỏi mọi user trước khi xóa
        frappe.db.delete("Has Role", {"role": name})
        # Dọn DocPerm / Custom DocPerm còn sót
        frappe.db.delete("DocPerm", {"role": name})
        frappe.db.delete("Custom DocPerm", {"role": name})
        try:
            frappe.delete_doc(
                "Role", name,
                ignore_permissions=True, force=True,
            )
            deleted += 1
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"Delete legacy Role {name} failed",
            )
    return deleted


def run() -> None:
    """Cleanup legacy Role Profile + persona Role. Idempotent."""
    legacy_profiles_deleted = _delete_legacy_profiles()
    legacy_roles_deleted = _delete_legacy_roles()
    frappe.db.commit()
    print(
        f"[AssetCore] Legacy cleanup: "
        f"{legacy_profiles_deleted} Role Profile xóa, "
        f"{legacy_roles_deleted} Role legacy xóa."
    )
