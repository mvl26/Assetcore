# Copyright (c) 2026, AssetCore Team
"""
Ma trận phân quyền (RBAC) cho AssetCore.

Chạy một lần sau khi cài app hoặc khi thay đổi matrix:
    bench --site <site> execute assetcore.setup.setup_permissions.run

Đã wire vào after_migrate trong hooks.py.

Thiết kế (11 role nghiệp vụ):

    Role (Frappe)                │ Vai trò nghiệp vụ
    ─────────────────────────────┼────────────────────────────────────────
    IMM System Admin             │ Quản trị hệ thống — toàn quyền
    IMM Operations Manager       │ Trưởng phòng TBYT — duyệt cuối
    IMM Department Head          │ Trưởng khoa — duyệt cấp khoa
    IMM Deputy Department Head   │ Phó khoa — hỗ trợ duyệt (không cancel)
    IMM Workshop Lead            │ Tổ trưởng xưởng — phân công/duyệt WO
    IMM QA Officer               │ Cán bộ QLCL — CAPA, QA NC, RCA
    IMM Biomed Technician        │ Nhân viên kỹ thuật — thực hiện WO
    IMM Document Officer         │ Cán bộ hồ sơ — IMM-05 documents
    IMM Storekeeper              │ Thủ kho — kho vật tư
    IMM Clinical User            │ Bác sĩ/điều dưỡng — xem + báo hỏng
    IMM Auditor                  │ Kiểm toán viên — read-only toàn bộ

Ký hiệu cột DocPerm:
    r=read  w=write  c=create  d=delete  s=submit  x=cancel  a=amend
"""
from __future__ import annotations

import frappe

# ─── Permission profiles ──────────────────────────────────────────────────────

_READ     = {"r": 1, "w": 0, "c": 0, "d": 0, "s": 0, "x": 0, "a": 0}
_RC       = {"r": 1, "w": 0, "c": 1, "d": 0, "s": 0, "x": 0, "a": 0}
_RW       = {"r": 1, "w": 1, "c": 1, "d": 0, "s": 0, "x": 0, "a": 0}
_RWS      = {"r": 1, "w": 1, "c": 1, "d": 0, "s": 1, "x": 0, "a": 0}
_RWSX     = {"r": 1, "w": 1, "c": 1, "d": 0, "s": 1, "x": 1, "a": 0}
_APPROVE  = {"r": 1, "w": 1, "c": 0, "d": 0, "s": 1, "x": 1, "a": 1}  # duyệt + hủy + amend
_DEPUTY   = {"r": 1, "w": 1, "c": 0, "d": 0, "s": 1, "x": 0, "a": 0}  # phó: duyệt, không hủy
_FULL     = {"r": 1, "w": 1, "c": 1, "d": 1, "s": 1, "x": 1, "a": 1}

# ─── Role constants ───────────────────────────────────────────────────────────

ADMIN       = "IMM System Admin"
OPS_MGR     = "IMM Operations Manager"
DEPT_HEAD   = "IMM Department Head"
DEPT_DEPUTY = "IMM Deputy Department Head"
WORKSHOP    = "IMM Workshop Lead"
QA          = "IMM QA Officer"
BIOMED      = "IMM Biomed Technician"
DOC_OFF     = "IMM Document Officer"
STORE       = "IMM Storekeeper"
CLINICAL    = "IMM Clinical User"
AUDITOR     = "IMM Auditor"

# ─── Permission matrix ────────────────────────────────────────────────────────
# Mỗi entry: (DocType, [(Role, perm_profile), ...])
# Chỉ liệt kê parent DocType. Child DocType (is_table=1) thừa kế từ parent tự động.

_MATRIX: list[tuple[str, list[tuple[str, dict]]]] = [

    # ══════════ Master Data — IMM-00 ═════════════════════════════════════════
    ("AC Asset", [
        (ADMIN, _FULL), (OPS_MGR, _RWSX), (DEPT_HEAD, _RW),
        (DEPT_DEPUTY, _RW), (WORKSHOP, _RW), (QA, _READ),
        (BIOMED, _READ), (STORE, _READ), (CLINICAL, _READ),
        (DOC_OFF, _READ), (AUDITOR, _READ),
    ]),
    ("AC Asset Category", [
        (ADMIN, _FULL), (OPS_MGR, _RW), (QA, _READ),
        (DEPT_HEAD, _READ), (BIOMED, _READ), (AUDITOR, _READ),
    ]),
    ("AC Department", [
        (ADMIN, _FULL), (OPS_MGR, _RW), (DEPT_HEAD, _READ),
        (DEPT_DEPUTY, _READ), (WORKSHOP, _READ), (QA, _READ),
        (BIOMED, _READ), (STORE, _READ), (CLINICAL, _READ),
        (DOC_OFF, _READ), (AUDITOR, _READ),
    ]),
    ("AC Location", [
        (ADMIN, _FULL), (OPS_MGR, _RW), (DEPT_HEAD, _RW),
        (WORKSHOP, _READ), (BIOMED, _READ), (STORE, _READ),
        (CLINICAL, _READ), (AUDITOR, _READ),
    ]),
    ("AC Supplier", [
        (ADMIN, _FULL), (OPS_MGR, _RWSX), (DEPT_HEAD, _RW),
        (STORE, _READ), (DOC_OFF, _READ), (AUDITOR, _READ),
    ]),
    ("AC Warehouse", [
        (ADMIN, _FULL), (OPS_MGR, _RW), (STORE, _RW),
        (BIOMED, _READ), (AUDITOR, _READ),
    ]),
    ("AC UOM", [
        (ADMIN, _FULL), (OPS_MGR, _RW), (STORE, _READ),
        (BIOMED, _READ), (AUDITOR, _READ),
    ]),
    ("IMM Device Model", [
        (ADMIN, _FULL), (OPS_MGR, _RW), (DEPT_HEAD, _READ),
        (WORKSHOP, _RW), (QA, _READ), (BIOMED, _READ),
        (DOC_OFF, _READ), (STORE, _READ), (AUDITOR, _READ),
    ]),
    ("IMM SLA Policy", [
        (ADMIN, _FULL), (OPS_MGR, _RWSX), (QA, _RW),
        (DEPT_HEAD, _READ), (WORKSHOP, _READ), (AUDITOR, _READ),
    ]),
    ("AC Authorized Technician", [
        (ADMIN, _FULL), (OPS_MGR, _RW), (WORKSHOP, _RW),
        (DEPT_HEAD, _READ), (AUDITOR, _READ),
    ]),

    # ══════════ Inventory / Purchasing ═══════════════════════════════════════
    ("AC Spare Part", [
        (ADMIN, _FULL), (OPS_MGR, _RW), (STORE, _RWSX),
        (WORKSHOP, _RW), (BIOMED, _READ), (AUDITOR, _READ),
    ]),
    ("AC Spare Part Stock", [
        (ADMIN, _FULL), (OPS_MGR, _READ), (STORE, _RW),
        (WORKSHOP, _READ), (BIOMED, _READ), (AUDITOR, _READ),
    ]),
    ("AC Stock Movement", [
        (ADMIN, _FULL), (OPS_MGR, _READ), (STORE, _RWSX),
        (WORKSHOP, _READ), (BIOMED, _RC), (AUDITOR, _READ),
    ]),
    ("AC Purchase", [
        (ADMIN, _FULL), (OPS_MGR, _APPROVE), (DEPT_HEAD, _DEPUTY),
        (DEPT_DEPUTY, _DEPUTY), (STORE, _RWS), (DOC_OFF, _READ),
        (AUDITOR, _READ),
    ]),

    # ══════════ Commissioning — IMM-04 ═══════════════════════════════════════
    ("Asset Commissioning", [
        (ADMIN, _FULL), (OPS_MGR, _APPROVE), (DEPT_HEAD, _APPROVE),
        (DEPT_DEPUTY, _DEPUTY), (WORKSHOP, _RWS), (QA, _RW),
        (BIOMED, _RW), (DOC_OFF, _RW), (CLINICAL, _READ),
        (AUDITOR, _READ),
    ]),
    ("Asset QA Non Conformance", [
        (ADMIN, _FULL), (OPS_MGR, _RWSX), (QA, _RWSX),
        (DEPT_HEAD, _RW), (WORKSHOP, _RW), (BIOMED, _RC),
        (AUDITOR, _READ),
    ]),
    ("Required Document Type", [
        (ADMIN, _FULL), (OPS_MGR, _RW), (DOC_OFF, _RW),
        (QA, _READ), (AUDITOR, _READ),
    ]),

    # ══════════ Documents — IMM-05 ═══════════════════════════════════════════
    ("Asset Document", [
        (ADMIN, _FULL), (OPS_MGR, _READ), (DEPT_HEAD, _READ),
        (DOC_OFF, _RWSX), (QA, _RW), (WORKSHOP, _READ),
        (BIOMED, _READ), (CLINICAL, _READ), (AUDITOR, _READ),
    ]),
    ("Document Request", [
        (ADMIN, _FULL), (OPS_MGR, _READ), (DOC_OFF, _RWSX),
        (QA, _RW), (WORKSHOP, _RC), (BIOMED, _RC),
        (CLINICAL, _RC), (AUDITOR, _READ),
    ]),

    # ══════════ Preventive Maintenance — IMM-08 ══════════════════════════════
    ("PM Schedule", [
        (ADMIN, _FULL), (OPS_MGR, _RW), (WORKSHOP, _RWSX),
        (QA, _READ), (BIOMED, _READ), (DEPT_HEAD, _READ),
        (AUDITOR, _READ),
    ]),
    ("PM Work Order", [
        (ADMIN, _FULL), (OPS_MGR, _READ), (WORKSHOP, _APPROVE),
        (DEPT_HEAD, _READ), (QA, _READ), (BIOMED, _RWS),
        (STORE, _READ), (AUDITOR, _READ),
    ]),
    ("PM Checklist Template", [
        (ADMIN, _FULL), (OPS_MGR, _RW), (WORKSHOP, _RW),
        (QA, _RW), (BIOMED, _READ), (AUDITOR, _READ),
    ]),
    ("PM Task Log", [
        (ADMIN, _FULL), (OPS_MGR, _READ), (WORKSHOP, _READ),
        (BIOMED, _RC), (AUDITOR, _READ),
    ]),

    # ══════════ Corrective Maintenance — IMM-09 ══════════════════════════════
    ("Asset Repair", [
        (ADMIN, _FULL), (OPS_MGR, _READ), (WORKSHOP, _APPROVE),
        (DEPT_HEAD, _READ), (QA, _READ), (BIOMED, _RWS),
        (STORE, _READ), (CLINICAL, _READ), (AUDITOR, _READ),
    ]),
    ("Firmware Change Request", [
        (ADMIN, _FULL), (OPS_MGR, _APPROVE), (WORKSHOP, _RWS),
        (QA, _RW), (BIOMED, _RC), (AUDITOR, _READ),
    ]),

    # ══════════ Calibration — IMM-11 ═════════════════════════════════════════
    ("IMM Calibration Schedule", [
        (ADMIN, _FULL), (OPS_MGR, _RW), (WORKSHOP, _RWSX),
        (QA, _RW), (BIOMED, _READ), (AUDITOR, _READ),
    ]),
    ("IMM Asset Calibration", [
        (ADMIN, _FULL), (OPS_MGR, _READ), (WORKSHOP, _APPROVE),
        (QA, _RW), (BIOMED, _RWS), (AUDITOR, _READ),
    ]),

    # ══════════ Incidents / QMS — IMM-12 ═════════════════════════════════════
    ("Incident Report", [
        (ADMIN, _FULL), (OPS_MGR, _RWSX), (DEPT_HEAD, _RWS),
        (DEPT_DEPUTY, _RWS), (WORKSHOP, _RWS), (QA, _RWSX),
        (BIOMED, _RWS), (CLINICAL, _RWS), (DOC_OFF, _READ),
        (AUDITOR, _READ),
    ]),
    ("IMM CAPA Record", [
        (ADMIN, _FULL), (OPS_MGR, _APPROVE), (QA, _RWSX),
        (DEPT_HEAD, _RW), (WORKSHOP, _RW), (BIOMED, _READ),
        (AUDITOR, _READ),
    ]),
    ("IMM RCA Record", [
        (ADMIN, _FULL), (OPS_MGR, _RW), (QA, _RWSX),
        (WORKSHOP, _RW), (BIOMED, _RW), (AUDITOR, _READ),
    ]),

    # ══════════ Asset Operations ═════════════════════════════════════════════
    ("Asset Transfer", [
        (ADMIN, _FULL), (OPS_MGR, _APPROVE), (DEPT_HEAD, _APPROVE),
        (DEPT_DEPUTY, _DEPUTY), (WORKSHOP, _RWS), (BIOMED, _RC),
        (CLINICAL, _RC), (STORE, _READ), (AUDITOR, _READ),
    ]),
    ("Asset Lifecycle Event", [
        (ADMIN, _FULL), (OPS_MGR, _READ), (DEPT_HEAD, _READ),
        (WORKSHOP, _RC), (QA, _READ), (BIOMED, _RC),
        (DOC_OFF, _READ), (CLINICAL, _READ), (AUDITOR, _READ),
    ]),
    ("AC Asset Downtime Log", [
        (ADMIN, _FULL), (OPS_MGR, _READ), (WORKSHOP, _RW),
        (QA, _READ), (BIOMED, _RC), (AUDITOR, _READ),
    ]),
    ("Expiry Alert Log", [
        (ADMIN, _FULL), (OPS_MGR, _READ), (DEPT_HEAD, _READ),
        (QA, _READ), (DOC_OFF, _READ), (AUDITOR, _READ),
    ]),

    # ══════════ Contracts ════════════════════════════════════════════════════
    ("Service Contract", [
        (ADMIN, _FULL), (OPS_MGR, _APPROVE), (DEPT_HEAD, _DEPUTY),
        (DOC_OFF, _RW), (QA, _READ), (WORKSHOP, _READ),
        (AUDITOR, _READ),
    ]),

    # ══════════ Audit Trail (immutable, read-only tất cả) ════════════════════
    ("IMM Audit Trail", [
        (ADMIN, _READ),       # Admin cũng không được sửa
        (OPS_MGR, _READ), (DEPT_HEAD, _READ), (QA, _READ),
        (WORKSHOP, _READ), (BIOMED, _READ), (DOC_OFF, _READ),
        (STORE, _READ), (CLINICAL, _READ), (AUDITOR, _READ),
    ]),
]


# ─── Engine ───────────────────────────────────────────────────────────────────

_MANAGED_ROLES = frozenset({
    ADMIN, OPS_MGR, DEPT_HEAD, DEPT_DEPUTY, WORKSHOP, QA,
    BIOMED, DOC_OFF, STORE, CLINICAL, AUDITOR,
})


def _doctype_exists(doctype: str) -> bool:
    return bool(frappe.db.exists("DocType", doctype))


def _role_exists(role: str) -> bool:
    return bool(frappe.db.exists("Role", role))


def _upsert_perm(doctype: str, role: str, perms: dict) -> str:
    """Tạo mới hoặc cập nhật DocPerm (permlevel=0). Trả 'inserted' hoặc 'updated'."""
    existing = frappe.db.get_value(
        "DocPerm",
        {"parent": doctype, "parenttype": "DocType", "role": role, "permlevel": 0},
        "name",
    )

    fields = {
        "read":   perms.get("r", 0),
        "write":  perms.get("w", 0),
        "create": perms.get("c", 0),
        "delete": perms.get("d", 0),
        "submit": perms.get("s", 0),
        "cancel": perms.get("x", 0),
        "amend":  perms.get("a", 0),
        "report": 1 if perms.get("r") else 0,
        "export": 1 if perms.get("r") else 0,
        "print":  1 if perms.get("r") else 0,
        "email":  1 if perms.get("r") else 0,
        "share":  1 if perms.get("r") else 0,
    }

    if existing:
        for k, v in fields.items():
            frappe.db.set_value("DocPerm", existing, k, v)
        return "updated"

    doc = frappe.get_doc({
        "doctype": "DocPerm",
        "parent": doctype,
        "parenttype": "DocType",
        "parentfield": "permissions",
        "role": role,
        "permlevel": 0,
        **fields,
    })
    doc.flags.ignore_permissions = True
    doc.insert()
    return "inserted"


def _clear_stale_managed_perms(doctype: str, current_roles: set[str]) -> int:
    """Xóa DocPerm của các managed role không còn trong matrix cho DocType này.

    Tránh quyền rớt lại khi đã đổi matrix (ví dụ: đổi role của một DocType).
    CHỈ đụng vào managed roles — không xóa legacy roles hoặc System Manager.
    """
    to_remove = (_MANAGED_ROLES - current_roles)
    if not to_remove:
        return 0
    stale = frappe.db.get_all(
        "DocPerm",
        filters={
            "parent": doctype,
            "parenttype": "DocType",
            "role": ("in", list(to_remove)),
            "permlevel": 0,
        },
        pluck="name",
    )
    for name in stale:
        frappe.delete_doc("DocPerm", name, ignore_permissions=True, force=True)
    return len(stale)


def run() -> None:
    """Điểm vào chính — chạy qua bench execute hoặc after_migrate."""
    frappe.flags.in_install = True

    inserted = updated = removed = skipped_dt = skipped_role = 0

    for doctype, role_perms in _MATRIX:
        if not _doctype_exists(doctype):
            frappe.logger().warning(
                f"setup_permissions: DocType '{doctype}' không tồn tại — bỏ qua"
            )
            skipped_dt += 1
            continue

        current_roles = {r for r, _ in role_perms}

        for role, perms in role_perms:
            if not _role_exists(role):
                frappe.logger().warning(
                    f"setup_permissions: Role '{role}' chưa tồn tại — bỏ qua {doctype}"
                )
                skipped_role += 1
                continue

            result = _upsert_perm(doctype, role, perms)
            if result == "inserted":
                inserted += 1
            else:
                updated += 1

        # Xóa quyền cũ của managed role không còn trong matrix
        removed += _clear_stale_managed_perms(doctype, current_roles)

    frappe.db.commit()
    frappe.clear_cache()

    summary = (
        f"[AssetCore] RBAC: {inserted} tạo mới, {updated} cập nhật, "
        f"{removed} xóa stale, {skipped_dt} DocType bỏ qua, {skipped_role} Role bỏ qua."
    )
    frappe.logger().info(summary)
    print(summary)
