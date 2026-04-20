# Copyright (c) 2026, AssetCore Team
"""Migration v2 -> v3: drop sidecar DocTypes, drop custom_imm_* fields on tabAsset.

V2 dùng 3 sidecar DocTypes (IMM Asset Profile, IMM Vendor Profile, IMM Location Ext)
link 1:1 với ERPNext Asset/Supplier/Location + 16 Custom Fields trên tabAsset.

V3 bỏ cả hai hướng: data HTM nằm first-class trên AC Asset (không phụ thuộc ERPNext).

Patch này:
1. Drop Custom Fields có fieldname khớp 'custom_imm%' trên DocType Asset (nếu còn).
2. Drop 3 sidecar DocTypes v2 nếu còn trong DB.
3. Drop bảng legacy IMM Authorized Technician (đã đổi sang AC Authorized Technician).

KHÔNG migrate data v2 — site test, "break clean" theo quyết định architect.
"""
import frappe


_V2_SIDECAR_DOCTYPES = [
    "IMM Asset Profile",
    "IMM Vendor Profile",
    "IMM Location Ext",
    "IMM Authorized Technician",
]


def execute():
    _drop_custom_fields_on_asset()
    _drop_sidecar_doctypes()
    frappe.db.commit()


def _drop_custom_fields_on_asset():
    rows = frappe.db.sql(
        """
        SELECT name FROM `tabCustom Field`
        WHERE fieldname LIKE 'custom_imm%%'
          AND dt = 'Asset'
        """,
        as_dict=True,
    )
    for r in rows:
        try:
            frappe.delete_doc("Custom Field", r.name, force=True, ignore_permissions=True)
            print(f"[v3 patch] Dropped Custom Field: {r.name}")
        except Exception as e:
            print(f"[v3 patch] Skip {r.name}: {e}")


def _drop_sidecar_doctypes():
    for dt in _V2_SIDECAR_DOCTYPES:
        if not frappe.db.exists("DocType", dt):
            continue
        try:
            frappe.delete_doc("DocType", dt, force=True, ignore_permissions=True, ignore_missing=True)
            print(f"[v3 patch] Dropped DocType: {dt}")
        except Exception as e:
            print(f"[v3 patch] Skip DocType {dt}: {e}")
        # Drop underlying table if still exists
        table = f"tab{dt}"
        try:
            frappe.db.sql(f"DROP TABLE IF EXISTS `{table}`")
            print(f"[v3 patch] Dropped table: {table}")
        except Exception as e:
            print(f"[v3 patch] Skip drop table {table}: {e}")
