# Copyright (c) 2026, AssetCore Team
# Patch 002: Migrate AC Spare Part UOM from hardcoded Select → Link → ERPNext UOM

import frappe

_DT_SPARE = "AC Spare Part"

# Map giá trị cũ (Select) → UOM name trong ERPNext
_SELECT_TO_UOM: dict[str, str] = {
    "Nos":   "Nos",
    "Pcs":   "Nos",    # Pcs = Nos trong ERPNext
    "Set":   "Set",
    "Box":   "Box",
    "Meter": "Meter",
    "Liter": "Nos",    # sẽ được thay bằng L sau khi seed
    "Kg":    "Kg",
}

_CHILD_TABLES = [
    ("AC Stock Movement Item", "spare_part"),
    ("AC Spare Part Stock",    "spare_part"),
    ("AC Purchase Item",       "spare_part"),
]


def execute():
    _seed_uoms()
    _migrate_spare_part_column()
    _backfill_child_tables()
    print("Patch 002 complete: UOM migration done.")


def _seed_uoms() -> None:
    from assetcore.services.uom import seed_medical_uoms
    created = seed_medical_uoms()
    if created:
        frappe.db.commit()
        print(f"  Seeded {len(created)} medical UOMs: {', '.join(created)}")


def _migrate_spare_part_column() -> None:
    """Copy uom → stock_uom với mapping, hoặc gán mặc định nếu cột cũ đã xóa."""
    has_old = frappe.db.has_column(_DT_SPARE, "uom")
    has_new = frappe.db.has_column(_DT_SPARE, "stock_uom")

    if has_old and has_new:
        parts = frappe.db.sql(
            "SELECT name, uom FROM `tabAC Spare Part` WHERE stock_uom IS NULL OR stock_uom = ''",
            as_dict=True,
        )
        for p in parts:
            old_val = (p.get("uom") or "Nos").strip()
            new_val = _SELECT_TO_UOM.get(old_val, "Nos")
            frappe.db.set_value(_DT_SPARE, p["name"], "stock_uom", new_val, update_modified=False)
        if parts:
            frappe.db.commit()
            print(f"  Migrated uom → stock_uom for {len(parts)} spare parts")
        return

    if has_new and not has_old:
        frappe.db.sql(
            "UPDATE `tabAC Spare Part` SET stock_uom = 'Nos' WHERE stock_uom IS NULL OR stock_uom = ''"
        )
        frappe.db.commit()
        print("  Set default stock_uom = Nos for spare parts without value")


def _backfill_child_tables() -> None:
    """Propagate stock_uom vào các child table (chỉ chạy khi cột đã tồn tại)."""
    if not frappe.db.has_column(_DT_SPARE, "stock_uom"):
        print("  Skipped child table update (stock_uom column not yet available)")
        return

    for child_dt, parent_field in _CHILD_TABLES:
        if frappe.db.has_column(child_dt, "uom"):
            frappe.db.sql(f"""
                UPDATE `tab{child_dt}` c
                JOIN `tabAC Spare Part` p ON p.name = c.{parent_field}
                SET c.uom = p.stock_uom
                WHERE (c.uom IS NULL OR c.uom = '')
                  AND p.stock_uom IS NOT NULL
            """)
    frappe.db.commit()
    print("  Updated uom on child tables from spare_part.stock_uom")
