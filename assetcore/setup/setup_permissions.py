# Copyright (c) 2026, AssetCore Team
"""
Ma trận phân quyền (RBAC) cho AssetCore.

Chạy một lần sau khi cài app:
    bench --site [site] execute assetcore.setup.setup_permissions.run

Hoặc thêm vào after_migrate trong hooks.py:
    after_migrate = ["assetcore.setup.install.after_migrate",
                     "assetcore.setup.setup_permissions.run"]
"""
from __future__ import annotations

import frappe

# ── Mapping vai trò ────────────────────────────────────────────────────────────
#
#  Role name (Frappe)       │ Vai trò nghiệp vụ
#  ─────────────────────────┼──────────────────────────────────────
#  IMM System Admin         │ AssetCore Admin — toàn quyền
#  Tổ HC-QLCL               │ Phòng QLCL — quản lý hồ sơ, kế hoạch
#  IMM Technician           │ Kỹ thuật viên — thực hiện work orders
#  IMM Clinical User        │ Bác sĩ / Khoa lâm sàng — chỉ xem + báo hỏng
#
# ── Ký hiệu cột ───────────────────────────────────────────────────────────────
#  r=read  w=write  c=create  d=delete  s=submit  x=cancel  a=amend

_FULL = dict(r=1, w=1, c=1, d=1, s=1, x=1, a=1)
_RW   = dict(r=1, w=1, c=1, d=0, s=0, x=0, a=0)
_RWS  = dict(r=1, w=1, c=1, d=0, s=1, x=0, a=0)
_RWSX = dict(r=1, w=1, c=1, d=0, s=1, x=1, a=0)
_READ = dict(r=1, w=0, c=0, d=0, s=0, x=0, a=0)
_RC   = dict(r=1, w=0, c=1, d=0, s=0, x=0, a=0)

ADMIN = "IMM System Admin"
QLCL  = "Tổ HC-QLCL"
KTV   = "IMM Technician"
BS    = "IMM Clinical User"

# ── Ma trận quyền ─────────────────────────────────────────────────────────────
# Mỗi phần tử: (DocType, Role, quyền_dict)
#
# Quy tắc:
#   ADMIN: toàn quyền trên mọi DocType AssetCore
#   QLCL:  quản lý hồ sơ kỹ thuật, hợp đồng, CAPA, lịch bảo trì
#   KTV:   thực hiện work order PM/CM/Calibration, nhập liệu kho
#   BS:    chỉ xem thiết bị (+ User Permission giới hạn khoa), tạo báo hỏng

_MATRIX: list[tuple[str, str, dict]] = [

    # ── Master data ────────────────────────────────────────────────────────────
    ("AC Asset",           ADMIN, _FULL),
    ("AC Asset",           QLCL,  _READ),
    ("AC Asset",           KTV,   _READ),
    ("AC Asset",           BS,    _READ),   # giới hạn thêm bằng User Permission

    ("AC Asset Category",  ADMIN, _FULL),
    ("AC Asset Category",  QLCL,  _READ),
    ("AC Asset Category",  KTV,   _READ),

    ("AC Department",      ADMIN, _FULL),
    ("AC Department",      QLCL,  _READ),
    ("AC Department",      KTV,   _READ),
    ("AC Department",      BS,    _READ),

    ("AC Location",        ADMIN, _FULL),
    ("AC Location",        QLCL,  _READ),
    ("AC Location",        KTV,   _READ),

    ("AC Supplier",        ADMIN, _FULL),
    ("AC Supplier",        QLCL,  _READ),

    ("IMM Device Model",   ADMIN, _FULL),
    ("IMM Device Model",   QLCL,  _READ),
    ("IMM Device Model",   KTV,   _READ),

    ("IMM SLA Policy",     ADMIN, _FULL),
    ("IMM SLA Policy",     QLCL,  _RW),

    # ── Vòng đời thiết bị ─────────────────────────────────────────────────────
    ("Asset Commissioning",    ADMIN, _FULL),
    ("Asset Commissioning",    QLCL,  _RWSX),
    ("Asset Commissioning",    KTV,   _READ),

    ("Asset Lifecycle Event",  ADMIN, _FULL),
    ("Asset Lifecycle Event",  QLCL,  _READ),
    ("Asset Lifecycle Event",  KTV,   _RC),

    ("Asset Transfer",         ADMIN, _FULL),
    ("Asset Transfer",         QLCL,  _RW),
    ("Asset Transfer",         KTV,   _READ),

    # ── Bảo trì định kỳ (PM) ──────────────────────────────────────────────────
    ("PM Schedule",         ADMIN, _FULL),
    ("PM Schedule",         QLCL,  _RW),
    ("PM Schedule",         KTV,   _READ),

    ("PM Work Order",       ADMIN, _FULL),
    ("PM Work Order",       QLCL,  _READ),
    ("PM Work Order",       KTV,   _RWSX),

    # ── Sửa chữa (CM) ─────────────────────────────────────────────────────────
    ("Asset Repair",        ADMIN, _FULL),
    ("Asset Repair",        QLCL,  _READ),
    ("Asset Repair",        KTV,   _RWSX),

    # ── Sự cố / báo hỏng ──────────────────────────────────────────────────────
    ("Incident Report",     ADMIN, _FULL),
    ("Incident Report",     QLCL,  _READ),
    ("Incident Report",     KTV,   _RWSX),
    ("Incident Report",     BS,    _RWS),   # Bác sĩ tạo + submit báo hỏng

    # ── Hiệu chuẩn ────────────────────────────────────────────────────────────
    ("IMM Calibration Schedule", ADMIN, _FULL),
    ("IMM Calibration Schedule", QLCL,  _RW),
    ("IMM Calibration Schedule", KTV,   _READ),

    ("IMM Asset Calibration",    ADMIN, _FULL),
    ("IMM Asset Calibration",    QLCL,  _READ),
    ("IMM Asset Calibration",    KTV,   _RWSX),

    # ── Hồ sơ kỹ thuật (IMM-05) ───────────────────────────────────────────────
    ("Asset Document",      ADMIN, _FULL),
    ("Asset Document",      QLCL,  _RW),
    ("Asset Document",      KTV,   _READ),

    ("Document Request",    ADMIN, _FULL),
    ("Document Request",    QLCL,  _RW),
    ("Document Request",    KTV,   _RC),

    # ── Hợp đồng dịch vụ ──────────────────────────────────────────────────────
    ("Service Contract",    ADMIN, _FULL),
    ("Service Contract",    QLCL,  _RWSX),
    ("Service Contract",    KTV,   _READ),

    # ── QMS / CAPA / RCA ──────────────────────────────────────────────────────
    ("IMM CAPA Record",           ADMIN, _FULL),
    ("IMM CAPA Record",           QLCL,  _RWSX),
    ("IMM CAPA Record",           KTV,   _READ),

    ("IMM RCA Record",            ADMIN, _FULL),
    ("IMM RCA Record",            QLCL,  _RW),
    ("IMM RCA Record",            KTV,   _READ),

    ("Asset QA Non Conformance",  ADMIN, _FULL),
    ("Asset QA Non Conformance",  QLCL,  _RW),

    ("Asset Downtime Log",        ADMIN, _FULL),
    ("Asset Downtime Log",        QLCL,  _READ),
    ("Asset Downtime Log",        KTV,   _RC),

    # ── Firmware / thay đổi cấu hình ──────────────────────────────────────────
    ("Firmware Change Request",  ADMIN, _FULL),
    ("Firmware Change Request",  QLCL,  _RWSX),
    ("Firmware Change Request",  KTV,   _READ),

    # ── Kho phụ tùng ──────────────────────────────────────────────────────────
    ("AC Spare Part",       ADMIN, _FULL),
    ("AC Spare Part",       QLCL,  _READ),
    ("AC Spare Part",       KTV,   _RW),

    ("AC Warehouse",        ADMIN, _FULL),
    ("AC Warehouse",        QLCL,  _READ),
    ("AC Warehouse",        KTV,   _READ),

    ("AC Stock Movement",   ADMIN, _FULL),
    ("AC Stock Movement",   QLCL,  _READ),
    ("AC Stock Movement",   KTV,   _RW),

    ("AC Spare Part Stock", ADMIN, _FULL),
    ("AC Spare Part Stock", QLCL,  _READ),
    ("AC Spare Part Stock", KTV,   _READ),

    # ── Audit Trail (read-only cho mọi người có quyền) ────────────────────────
    ("IMM Audit Trail",     ADMIN, _FULL),
    ("IMM Audit Trail",     QLCL,  _READ),
    ("IMM Audit Trail",     KTV,   _READ),
]


# ── Engine ─────────────────────────────────────────────────────────────────────

def _doctype_exists(doctype: str) -> bool:
    return frappe.db.exists("DocType", doctype) is not None


def _upsert_perm(doctype: str, role: str, perms: dict) -> None:
    """Tạo mới hoặc cập nhật một dòng DocPerm (permlevel=0)."""
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
    }

    if existing:
        frappe.db.set_value("DocPerm", existing, fields)
    else:
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


def run() -> None:
    """Điểm vào chính — chạy qua bench execute."""
    frappe.flags.in_install = True

    inserted = updated = skipped = 0

    for doctype, role, perms in _MATRIX:
        if not _doctype_exists(doctype):
            frappe.logger().warning(f"setup_permissions: DocType '{doctype}' không tồn tại — bỏ qua")
            skipped += 1
            continue

        existing = frappe.db.get_value(
            "DocPerm",
            {"parent": doctype, "parenttype": "DocType", "role": role, "permlevel": 0},
            "name",
        )
        _upsert_perm(doctype, role, perms)

        if existing:
            updated += 1
        else:
            inserted += 1

    frappe.db.commit()

    frappe.logger().info(
        f"setup_permissions: inserted={inserted}, updated={updated}, skipped={skipped}"
    )
    print(f"[AssetCore] Permissions: {inserted} tạo mới, {updated} cập nhật, {skipped} bỏ qua.")
