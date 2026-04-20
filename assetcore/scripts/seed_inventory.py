# Copyright (c) 2026, AssetCore Team
# Seed inventory test data: 3 warehouses + 10 spare parts + initial stock.
import frappe


def _ensure_warehouse(code: str, name: str, dept: str | None = None) -> str:
    existing = frappe.db.exists("AC Warehouse", {"warehouse_code": code})
    if existing:
        return existing
    doc = frappe.get_doc({
        "doctype": "AC Warehouse",
        "warehouse_code": code,
        "warehouse_name": name,
        "department": dept,
        "is_active": 1,
    }).insert(ignore_permissions=True)
    return doc.name


def _ensure_part(code: str, name: str, **kwargs) -> str:
    existing = frappe.db.exists("AC Spare Part", {"part_code": code})
    if existing:
        return existing
    doc = frappe.get_doc({
        "doctype": "AC Spare Part",
        "part_code": code,
        "part_name": name,
        "is_active": 1,
        **kwargs,
    }).insert(ignore_permissions=True)
    if not doc.part_code:
        doc.db_set("part_code", code)
    return doc.name


def run():
    frappe.set_user("Administrator")

    # ── Warehouses ──────────────────────────────────────────────────────────
    wh_xuong   = _ensure_warehouse("WH-XUONG-01",  "Kho xưởng bảo trì chính")
    wh_icu     = _ensure_warehouse("WH-ICU",       "Kho trực ICU")
    wh_central = _ensure_warehouse("WH-CENTRAL",   "Kho trung tâm")

    print(f"Warehouses: {wh_xuong}, {wh_icu}, {wh_central}")

    # ── Spare Parts ─────────────────────────────────────────────────────────
    parts_spec = [
        ("SP-BAT-001", "Pin lithium máy thở Drager",      "Battery",    "Drager",   "BAT-DR-2400", 1_500_000, "Pcs", 5, 20, 1),
        ("SP-FLT-001", "Bộ lọc HEPA máy thở",             "Filter",     "3M",       "HEPA-3M-V50", 450_000,   "Pcs", 10, 50, 0),
        ("SP-SEN-001", "Cảm biến oxy máy thở",            "Sensor",     "Envitec",  "OOM202",      2_800_000, "Pcs", 4, 12, 1),
        ("SP-ELE-001", "Bo mạch điều khiển máy X-quang",  "Electrical", "Philips",  "PCB-XR-100",  18_500_000, "Pcs", 1, 3,  1),
        ("SP-CON-001", "Ống dẫn khí silicone",            "Consumable", "Generic",  "TUBE-SIL-8",  85_000,    "Meter", 50, 200, 0),
        ("SP-CON-002", "Găng tay sạch size M",            "Consumable", "Ansell",   "GLV-M-100",   320_000,   "Box", 30, 100, 0),
        ("SP-MEC-001", "Vòng bi trục bơm tiêm",           "Mechanical", "SKF",      "BRG-6204",    180_000,   "Pcs", 8, 30, 0),
        ("SP-BAT-002", "Pin máy đo huyết áp di động",     "Battery",    "Panasonic","LR6-AA-PACK", 45_000,    "Pcs", 20, 100, 0),
        ("SP-SEN-002", "Cảm biến SpO2 đầu ngón tay",      "Sensor",     "Nellcor",  "DS100A-1",    1_200_000, "Pcs", 6, 20, 1),
        ("SP-ELE-002", "Cáp nguồn IEC C13",               "Electrical", "Generic",  "CBL-C13-1M",  95_000,    "Pcs", 15, 50, 0),
    ]

    part_ids = []
    for code, name, cat, mfr, mpn, cost, uom, min_stk, max_stk, critical in parts_spec:
        pid = _ensure_part(
            code, name,
            part_category=cat, manufacturer=mfr, manufacturer_part_no=mpn,
            unit_cost=cost, uom=uom,
            min_stock_level=min_stk, max_stock_level=max_stk,
            is_critical=critical,
        )
        part_ids.append(pid)

    print(f"Created {len(part_ids)} spare parts")

    # ── Initial Stock (tạo Stock Movement "Receipt" cho tất cả parts vào WH-XUONG) ─
    # Movement 1: Nhập đầy kho xưởng
    from assetcore.assetcore.doctype.ac_stock_movement.ac_stock_movement import ACStockMovement
    init_items = [
        {"spare_part": part_ids[i], "qty": qty, "unit_cost": parts_spec[i][5]}
        for i, qty in enumerate([8, 30, 6, 2, 120, 60, 15, 50, 10, 25])
    ]

    mov1 = frappe.get_doc({
        "doctype": "AC Stock Movement",
        "movement_type": "Receipt",
        "to_warehouse": wh_xuong,
        "reference_type": "Purchase",
        "notes": "Nhập kho đầu kỳ — seed data",
        "items": init_items,
    })
    mov1.insert(ignore_permissions=True)
    mov1.submit()
    print(f"Movement 1 (Receipt to {wh_xuong}): {mov1.name}")

    # Movement 2: Chuyển 1 phần sang kho ICU (parts critical)
    transfer_items = [
        {"spare_part": part_ids[0], "qty": 2, "unit_cost": parts_spec[0][5]},  # Pin máy thở
        {"spare_part": part_ids[2], "qty": 1, "unit_cost": parts_spec[2][5]},  # Sensor oxy
        {"spare_part": part_ids[8], "qty": 3, "unit_cost": parts_spec[8][5]},  # SpO2
    ]
    mov2 = frappe.get_doc({
        "doctype": "AC Stock Movement",
        "movement_type": "Transfer",
        "from_warehouse": wh_xuong,
        "to_warehouse": wh_icu,
        "notes": "Phân bổ dự trữ cho ICU",
        "items": transfer_items,
    })
    mov2.insert(ignore_permissions=True)
    mov2.submit()
    print(f"Movement 2 (Transfer → {wh_icu}): {mov2.name}")

    # Movement 3: Issue cho 1 sửa chữa mẫu
    issue_items = [
        {"spare_part": part_ids[1], "qty": 2, "unit_cost": parts_spec[1][5]},  # Filter
        {"spare_part": part_ids[5], "qty": 5, "unit_cost": parts_spec[5][5]},  # Găng tay
    ]
    mov3 = frappe.get_doc({
        "doctype": "AC Stock Movement",
        "movement_type": "Issue",
        "from_warehouse": wh_xuong,
        "reference_type": "Asset Repair",
        "notes": "Xuất cho sửa chữa máy thở ICU-02",
        "items": issue_items,
    })
    mov3.insert(ignore_permissions=True)
    mov3.submit()
    print(f"Movement 3 (Issue from {wh_xuong}): {mov3.name}")

    frappe.db.commit()
    print("\n🎉 Seed inventory hoàn tất.")
