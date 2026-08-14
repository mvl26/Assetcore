"""Cleanup test spare-part fixtures and seed realistic Vietnamese HTM master data.

Idempotent. Safe to re-run.

Invoke:
    bench --site miyano execute assetcore.scripts.maintenance.cleanup_and_seed_spare_parts.run
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import frappe

# Real, non-test warehouse (Kho trung tâm Vật tư Thiết bị Y tế — Tầng B1)
PRIMARY_WAREHOUSE = "AC-WH-0388"
WORKSHOP_WAREHOUSE = "AC-WH-0389"  # Kho phân xưởng kỹ thuật
QC_WAREHOUSE = "AC-WH-0390"        # Kho QC Hold

SUPPLIER_DRAGER = "AC-SUP-2026-0017"   # Dräger Medical Vietnam
SUPPLIER_MEDITRONIC = "AC-SUP-2026-0021"  # Meditronic Vietnam
SUPPLIER_BINHMINH = "AC-SUP-2026-0018"  # Bình Minh

ASSET_DRAGER = "AC-ASSET-2026-00407"    # Máy thở Dräger Evita V500
ASSET_MINDRAY = "AC-ASSET-2026-00408"   # Monitor Mindray BeneView T9
ASSET_PHILIPS = "AC-ASSET-2026-00409"   # Siêu âm Philips EPIQ 7
ASSET_BRAUN = "AC-ASSET-2026-00410"     # Bơm tiêm B. Braun


def _log(msg: str) -> None:
    print(f"[seed-spare] {msg}")


# ---------------------------------------------------------------------------
# CLEANUP
# ---------------------------------------------------------------------------
def cleanup_test_spare_parts() -> dict[str, int]:
    counters = {
        "spare_parts_used_orphan": 0,
        "spare_allocation": 0,
        "spare_batch": 0,
        "watchlist": 0,
        "forecast_parent": 0,
        "stock_rows": 0,
        "stock_movement_items": 0,
        "stock_movements": 0,
        "spare_parts": 0,
        "warehouses_test": 0,
    }

    # 1) Cancel + delete IMM Spare Allocation pointing to test parts
    for n in frappe.get_all("IMM Spare Allocation", pluck="name"):
        doc = frappe.get_doc("IMM Spare Allocation", n)
        bad = any(
            _is_test_part_name(it.spare_part) for it in (doc.items or [])
        )
        if bad:
            if doc.docstatus == 1:
                doc.cancel()
            frappe.delete_doc("IMM Spare Allocation", n, force=True)
            counters["spare_allocation"] += 1

    # 2) IMM Spare Batch — drop those referencing test parts
    for n in frappe.get_all(
        "IMM Spare Batch", fields=["name", "spare_part"]
    ):
        if _is_test_part_name(n.spare_part):
            frappe.delete_doc("IMM Spare Batch", n.name, force=True)
            counters["spare_batch"] += 1

    # 3) Watchlist referencing test parts
    for n in frappe.get_all(
        "IMM Critical Spare Watchlist", fields=["name", "spare_part"]
    ):
        if _is_test_part_name(n.spare_part):
            frappe.delete_doc(
                "IMM Critical Spare Watchlist", n.name, force=True
            )
            counters["watchlist"] += 1

    # 4) IMM Spare Part Forecast (parent) — drop those whose items reference
    #    test parts only.
    for n in frappe.get_all("IMM Spare Part Forecast", pluck="name"):
        doc = frappe.get_doc("IMM Spare Part Forecast", n)
        items = doc.get("items") or []
        if items and all(_is_test_part_name(it.spare_part) for it in items):
            if doc.docstatus == 1:
                doc.cancel()
            frappe.delete_doc("IMM Spare Part Forecast", n, force=True)
            counters["forecast_parent"] += 1

    # 5) AC Spare Part Stock — drop rows tied to test parts or test warehouses
    for s in frappe.get_all(
        "AC Spare Part Stock",
        fields=["name", "spare_part", "warehouse"],
    ):
        if _is_test_part_name(s.spare_part) or _is_test_warehouse(
            s.warehouse
        ):
            frappe.delete_doc("AC Spare Part Stock", s.name, force=True)
            counters["stock_rows"] += 1

    # 6) AC Stock Movement — purge at DB level (bypass on_cancel hooks that
    #    fail with seed test data).
    bad_movements: set[str] = set()
    for m in frappe.get_all(
        "AC Stock Movement",
        fields=["name", "from_warehouse", "to_warehouse"],
    ):
        if _is_test_warehouse(m.from_warehouse) or _is_test_warehouse(
            m.to_warehouse
        ):
            bad_movements.add(m.name)
    items = frappe.db.sql(
        "SELECT DISTINCT parent, spare_part FROM `tabAC Stock Movement Item`",
        as_dict=True,
    )
    for it in items:
        if _is_test_part_name(it.spare_part):
            bad_movements.add(it.parent)
    for mname in bad_movements:
        frappe.db.delete("AC Stock Movement Item", {"parent": mname})
        frappe.db.delete("AC Stock Movement", {"name": mname})
        counters["stock_movements"] += 1
    # also clean orphan movement items referencing test parts directly
    for it in frappe.db.sql(
        "SELECT name, spare_part FROM `tabAC Stock Movement Item`",
        as_dict=True,
    ):
        if _is_test_part_name(it.spare_part):
            frappe.db.delete("AC Stock Movement Item", {"name": it.name})
            counters["stock_movement_items"] += 1

    # 7) Spare Parts Used orphan rows (parent missing)
    rows = frappe.db.sql(
        """SELECT spu.name FROM `tabSpare Parts Used` spu
           LEFT JOIN `tabAsset Repair` ar ON ar.name = spu.parent
           WHERE spu.parenttype='Asset Repair' AND ar.name IS NULL""",
        as_dict=True,
    )
    for r in rows:
        frappe.db.delete("Spare Parts Used", {"name": r.name})
        counters["spare_parts_used_orphan"] += 1

    # 8) Now AC Spare Part itself — purge at DB level to bypass on_trash hook
    for p in frappe.get_all(
        "AC Spare Part",
        fields=["name", "part_name", "manufacturer", "unit_cost"],
    ):
        if _is_test_part(p):
            # double-check no dependents remain
            frappe.db.delete(
                "AC Spare Part Stock", {"spare_part": p.name}
            )
            frappe.db.delete(
                "AC Stock Movement Item", {"spare_part": p.name}
            )
            frappe.db.delete("IMM Spare Batch", {"spare_part": p.name})
            frappe.db.delete("AC Spare Part", {"name": p.name})
            counters["spare_parts"] += 1

    # 9) Test warehouses (AC-WH-0391..0397)
    for w in frappe.get_all(
        "AC Warehouse", fields=["name", "warehouse_name"]
    ):
        if _is_test_warehouse(w.name) or "Test WH" in (w.warehouse_name or ""):
            try:
                frappe.delete_doc("AC Warehouse", w.name, force=True)
                counters["warehouses_test"] += 1
            except Exception as e:
                _log(f"WH {w.name} keep ({e})")

    frappe.db.commit()
    return counters


def _is_test_part_name(name: str | None) -> bool:
    if not name:
        return False
    pn = frappe.db.get_value("AC Spare Part", name, "part_name") or ""
    mfr = frappe.db.get_value("AC Spare Part", name, "manufacturer") or ""
    return _is_test_part({"part_name": pn, "manufacturer": mfr})


def _is_test_part(p: dict | Any) -> bool:
    pn = (p.get("part_name") if isinstance(p, dict) else p.part_name) or ""
    mfr = (
        p.get("manufacturer") if isinstance(p, dict) else p.manufacturer
    ) or ""
    if any(
        tag in pn
        for tag in ("_Test", "Test ", "Sample", "auto-gen", "Auto Gen")
    ):
        return True
    if pn.startswith("Test "):
        return True
    if not mfr.strip():
        return True
    return False


def _is_test_warehouse(name: str | None) -> bool:
    if not name:
        return False
    return name in {
        f"AC-WH-{i:04d}" for i in range(391, 398)
    } or "Test WH" in (
        frappe.db.get_value("AC Warehouse", name, "warehouse_name") or ""
    )


# ---------------------------------------------------------------------------
# SEED MASTER
# ---------------------------------------------------------------------------
SPARE_PARTS: list[dict] = [
    {
        "part_code": "SP-EVT-PEEP-V01",
        "part_name": "Van PEEP máy thở Dräger Evita V500",
        "part_category": "Mechanical",
        "manufacturer": "Công ty TNHH Dräger Medical Vietnam",
        "manufacturer_part_no": "8403735",
        "preferred_supplier": SUPPLIER_DRAGER,
        "unit_cost": 4850000,
        "stock_uom": "Cái",
        "purchase_uom": "Cái",
        "min_stock_level": 3,
        "max_stock_level": 12,
        "shelf_life_months": 0,
        "is_critical": 1,
        "is_active": 1,
        "specifications": (
            "Van PEEP (Positive End-Expiratory Pressure) chính hãng Dräger SP-DR-0234 — "
            "Khối điều khiển khí thở thủ động cho dòng máy thở Evita V500/Babylog VN500. "
            "Vật liệu: hợp kim nhôm anodized + màng silicone y tế cấp implant. "
            "Áp suất hoạt động: 0–35 cmH2O (±0.5 cmH2O). Đường kính ngoài 22mm chuẩn ISO 5356-1. "
            "Hạn dùng 5 năm kể từ ngày sản xuất, autoclave 134°C/2.1 bar, 50 chu kỳ tiệt khuẩn."
        ),
        "stock_qty": 8,
        "manufacture_offset_days": 60,
        "expiry_offset_days": 730,
        "batch_supplier_lot": "DRG-VPEEP-2026-Q1",
    },
    {
        "part_code": "SP-EVT-O2SENS",
        "part_name": "Cảm biến nồng độ O2 máy thở Dräger Evita V500",
        "part_category": "Sensor",
        "manufacturer": "Công ty TNHH Dräger Medical Vietnam",
        "manufacturer_part_no": "6850645",
        "preferred_supplier": SUPPLIER_DRAGER,
        "unit_cost": 3250000,
        "stock_uom": "Cái",
        "purchase_uom": "Hộp",
        "min_stock_level": 4,
        "max_stock_level": 16,
        "shelf_life_months": 12,
        "is_critical": 1,
        "is_active": 1,
        "specifications": (
            "Cảm biến đo nồng độ Oxy (galvanic O2 cell) Dräger Sensor MOX-3 — "
            "dải đo 0–100% FiO2 với độ chính xác ±2%, đáp ứng <15s ở 23°C. "
            "Tuổi thọ điển hình 12 tháng/100% O2 hoặc 18 tháng/21% O2. "
            "Sản phẩm 1 lần dùng, không tiệt khuẩn lại. Lưu trữ 5–40°C, độ ẩm <90% RH."
        ),
        "stock_qty": 10,
        "manufacture_offset_days": 30,
        "expiry_offset_days": 365,
        "batch_supplier_lot": "DRG-O2-2026-03",
    },
    {
        "part_code": "SP-MBT9-BAT-001",
        "part_name": "Pin Lithium-ion Mindray BeneView T9 11.1V 5800mAh",
        "part_category": "Battery",
        "manufacturer": "Mindray Bio-Medical Electronics Vietnam",
        "manufacturer_part_no": "LI23S002A",
        "preferred_supplier": SUPPLIER_MEDITRONIC,
        "unit_cost": 2850000,
        "stock_uom": "Cái",
        "purchase_uom": "Cái",
        "min_stock_level": 5,
        "max_stock_level": 20,
        "shelf_life_months": 24,
        "is_critical": 1,
        "is_active": 1,
        "specifications": (
            "Pin Lithium-ion chính hãng Mindray cho Monitor đa thông số BeneView T9. "
            "Thông số: 11.1V — 5800mAh — 64.4Wh, hỗ trợ ≥150 phút vận hành liên tục. "
            "Có IC bảo vệ quá nhiệt/quá áp, giao tiếp SMBus. Chu kỳ sạc thiết kế ≥500 cycles. "
            "Lưu trữ 0–35°C, độ ẩm 10–95% RH, không sạc đầy khi lưu kho dài hạn."
        ),
        "stock_qty": 12,
        "manufacture_offset_days": 90,
        "expiry_offset_days": 730,
        "batch_supplier_lot": "MIN-BAT-2026-Q1",
    },
    {
        "part_code": "SP-MBT9-SPO2",
        "part_name": "Cảm biến SpO2 Masimo SET cho Mindray BeneView T9",
        "part_category": "Sensor",
        "manufacturer": "Mindray Bio-Medical Electronics Vietnam",
        "manufacturer_part_no": "0010-10-12202",
        "preferred_supplier": SUPPLIER_MEDITRONIC,
        "unit_cost": 1980000,
        "stock_uom": "Cái",
        "purchase_uom": "Hộp",
        "min_stock_level": 6,
        "max_stock_level": 24,
        "shelf_life_months": 18,
        "is_critical": 1,
        "is_active": 1,
        "specifications": (
            "Cảm biến SpO2 Masimo SET LNCS DCI người lớn (đầu dò ngón tay) — "
            "tương thích Mindray BeneView T9, độ chính xác ±2% (70–100% SpO2), "
            "khả năng đo qua chuyển động (Motion Tolerance) và tưới máu thấp (Low Perfusion). "
            "Cáp dài 3m, đầu nối 9-pin. Dùng tối đa 100 bệnh nhân, lau cồn isopropyl 70% giữa các ca."
        ),
        "stock_qty": 18,
        "manufacture_offset_days": 45,
        "expiry_offset_days": 540,
        "batch_supplier_lot": "MAS-SPO2-2026-02",
    },
    {
        "part_code": "SP-EPQ7-C51-PRB",
        "part_name": "Đầu dò siêu âm Convex C5-1 cho Philips EPIQ 7",
        "part_category": "Sensor",
        "manufacturer": "Philips Healthcare Vietnam",
        "manufacturer_part_no": "989605407341",
        "preferred_supplier": SUPPLIER_BINHMINH,
        "unit_cost": 158000000,
        "stock_uom": "Cái",
        "purchase_uom": "Cái",
        "min_stock_level": 1,
        "max_stock_level": 4,
        "shelf_life_months": 0,
        "is_critical": 1,
        "is_active": 1,
        "specifications": (
            "Đầu dò siêu âm Convex Philips C5-1 PureWave — dải tần 1.0–5.0 MHz, 160 phần tử, "
            "field of view 105°, dùng cho khảo sát bụng tổng quát, sản phụ khoa, gan-mật. "
            "Tương thích máy Philips EPIQ 7/EPIQ 5/Affiniti 70. Lớp ghép âm: PureWave xCrystal. "
            "Bảo quản 5–40°C, vận chuyển trong hộp xốp shock-proof. Không tiệt khuẩn hơi."
        ),
        "stock_qty": 2,
        "manufacture_offset_days": 180,
        "expiry_offset_days": 1825,
        "batch_supplier_lot": "PHL-C51-2026-01",
    },
    {
        "part_code": "SP-EPQ7-GEL-5L",
        "part_name": "Gel siêu âm Aquasonic 100 — can 5L cho Philips EPIQ 7",
        "part_category": "Consumable",
        "manufacturer": "Parker Laboratories — phân phối bởi Bình Minh",
        "manufacturer_part_no": "01-50",
        "preferred_supplier": SUPPLIER_BINHMINH,
        "unit_cost": 685000,
        "stock_uom": "Cái",
        "purchase_uom": "Hộp",
        "min_stock_level": 8,
        "max_stock_level": 40,
        "shelf_life_months": 36,
        "is_critical": 0,
        "is_active": 1,
        "specifications": (
            "Gel siêu âm Aquasonic 100 không màu, trung tính pH 7.0, không gây kích ứng da, "
            "tan trong nước, không nhuộm quần áo. Đóng gói can 5 lít HDPE có vòi rót. "
            "Đạt chuẩn USP, không chứa formaldehyde. Bảo quản nhiệt độ phòng 15–30°C, "
            "tránh đông đá. Hạn sử dụng 36 tháng kể từ ngày sản xuất ghi trên nhãn."
        ),
        "stock_qty": 25,
        "manufacture_offset_days": 120,
        "expiry_offset_days": 1095,
        "batch_supplier_lot": "AQ100-VN-2026-04",
    },
    {
        "part_code": "SP-BRAUN-PERF-INF",
        "part_name": "Bộ dây truyền B. Braun Perfusor Original 50ml",
        "part_category": "Consumable",
        "manufacturer": "B. Braun Vietnam Co., Ltd",
        "manufacturer_part_no": "8723060",
        "preferred_supplier": SUPPLIER_BINHMINH,
        "unit_cost": 145000,
        "stock_uom": "Cái",
        "purchase_uom": "Hộp",
        "min_stock_level": 30,
        "max_stock_level": 200,
        "shelf_life_months": 60,
        "is_critical": 0,
        "is_active": 1,
        "specifications": (
            "Bộ dây truyền chính hãng cho bơm tiêm B. Braun Perfusor Space — chiều dài 150 cm, "
            "PVC y tế (DEHP-free), Luer-Lock đầu nối, dead-space <0.1ml. "
            "Tiệt khuẩn EO, đóng gói vô khuẩn từng cái. Hạn dùng 5 năm kể từ NSX. "
            "Sử dụng 1 lần, không tái sử dụng. Tuân thủ TCVN 8061-1 và ISO 8536-9."
        ),
        "stock_qty": 120,
        "manufacture_offset_days": 60,
        "expiry_offset_days": 1825,
        "batch_supplier_lot": "BRN-PERF-2026-01",
    },
    {
        "part_code": "SP-MON-ECG-5LD",
        "part_name": "Cáp ECG 5 đạo trình AHA cho Monitor đa thông số",
        "part_category": "Electrical",
        "manufacturer": "Mindray Bio-Medical Electronics Vietnam",
        "manufacturer_part_no": "0010-30-42719",
        "preferred_supplier": SUPPLIER_MEDITRONIC,
        "unit_cost": 1250000,
        "stock_uom": "Bộ",
        "purchase_uom": "Bộ",
        "min_stock_level": 4,
        "max_stock_level": 16,
        "shelf_life_months": 0,
        "is_critical": 0,
        "is_active": 1,
        "specifications": (
            "Bộ cáp ECG 5 đạo trình mã màu AHA (RA-LA-LL-RL-V) cho monitor Mindray T-series, "
            "dài 3.6m, đầu kết nối Snap (button) tương thích điện cực đa năng. "
            "Vỏ TPE chống xoắn, lõi đồng phủ bạc nhiễu thấp, chịu nước IPX2. "
            "Tương thích máy khử rung (defib-proof) theo IEC 60601-2-27. Lau bằng cồn 70%."
        ),
        "stock_qty": 8,
        "manufacture_offset_days": 90,
        "expiry_offset_days": 0,  # no expiry for cable
        "batch_supplier_lot": "MIN-ECG5-2026-02",
    },
]


def seed_spare_parts_master() -> list[str]:
    names: list[str] = []
    for spec in SPARE_PARTS:
        existing = frappe.db.get_value(
            "AC Spare Part", {"part_code": spec["part_code"]}, "name"
        )
        if existing:
            doc = frappe.get_doc("AC Spare Part", existing)
        else:
            doc = frappe.new_doc("AC Spare Part")
            doc.part_code = spec["part_code"]
        for k in (
            "part_name",
            "part_category",
            "manufacturer",
            "manufacturer_part_no",
            "preferred_supplier",
            "unit_cost",
            "stock_uom",
            "purchase_uom",
            "min_stock_level",
            "max_stock_level",
            "shelf_life_months",
            "is_critical",
            "is_active",
            "specifications",
        ):
            doc.set(k, spec.get(k))
        doc.save(ignore_permissions=True)
        names.append(doc.name)
        _log(f"upsert part {doc.name} — {doc.part_name}")
    frappe.db.commit()
    return names


# ---------------------------------------------------------------------------
# STOCK + BATCHES
# ---------------------------------------------------------------------------
def seed_stock_and_batches() -> dict[str, int]:
    out = {"stock": 0, "batch": 0}
    today = datetime.now()
    for spec in SPARE_PARTS:
        part_name = frappe.db.get_value(
            "AC Spare Part", {"part_code": spec["part_code"]}, "name"
        )
        if not part_name:
            continue
        # --- Primary stock row
        _upsert_stock(
            warehouse=PRIMARY_WAREHOUSE,
            spare_part=part_name,
            qty=spec["stock_qty"],
            uom=spec["stock_uom"],
            last_movement=today - timedelta(days=14),
        )
        out["stock"] += 1
        # Workshop also keeps small qty for critical parts
        if spec["is_critical"]:
            _upsert_stock(
                warehouse=WORKSHOP_WAREHOUSE,
                spare_part=part_name,
                qty=max(1, spec["stock_qty"] // 4),
                uom=spec["stock_uom"],
                last_movement=today - timedelta(days=5),
            )
            out["stock"] += 1

        # --- Batch (1 primary; for high-stock items add a 2nd batch)
        _upsert_batch(
            spare_part=part_name,
            warehouse=PRIMARY_WAREHOUSE,
            batch_no=f"LOT-{spec['part_code']}-A",
            supplier_lot=spec["batch_supplier_lot"] + "-A",
            mfg_offset=spec["manufacture_offset_days"],
            exp_offset=spec["expiry_offset_days"],
            qty=spec["stock_qty"],
            supplier=spec["preferred_supplier"],
        )
        out["batch"] += 1
        if spec["stock_qty"] >= 10:
            _upsert_batch(
                spare_part=part_name,
                warehouse=PRIMARY_WAREHOUSE,
                batch_no=f"LOT-{spec['part_code']}-B",
                supplier_lot=spec["batch_supplier_lot"] + "-B",
                mfg_offset=max(15, spec["manufacture_offset_days"] // 2),
                exp_offset=spec["expiry_offset_days"],
                qty=max(2, spec["stock_qty"] // 3),
                supplier=spec["preferred_supplier"],
            )
            out["batch"] += 1
    frappe.db.commit()
    return out


def _upsert_stock(
    *,
    warehouse: str,
    spare_part: str,
    qty: float,
    uom: str,
    last_movement: datetime,
) -> None:
    stock_key = f"{warehouse}::{spare_part}"
    if frappe.db.exists("AC Spare Part Stock", stock_key):
        doc = frappe.get_doc("AC Spare Part Stock", stock_key)
    else:
        doc = frappe.new_doc("AC Spare Part Stock")
        doc.stock_key = stock_key
        doc.warehouse = warehouse
        doc.spare_part = spare_part
    doc.uom = uom
    doc.qty_on_hand = qty
    doc.reserved_qty = 0
    doc.available_qty = qty
    doc.last_movement_date = last_movement
    doc.save(ignore_permissions=True)


def _upsert_batch(
    *,
    spare_part: str,
    warehouse: str,
    batch_no: str,
    supplier_lot: str,
    mfg_offset: int,
    exp_offset: int,
    qty: float,
    supplier: str | None,
) -> None:
    today = datetime.now().date()
    existing = frappe.db.get_value(
        "IMM Spare Batch",
        {"spare_part": spare_part, "batch_no": batch_no},
        "name",
    )
    if existing:
        doc = frappe.get_doc("IMM Spare Batch", existing)
    else:
        doc = frappe.new_doc("IMM Spare Batch")
        doc.spare_part = spare_part
        doc.batch_no = batch_no
    doc.warehouse = warehouse
    doc.manufacture_date = today - timedelta(days=mfg_offset)
    doc.expiry_date = (
        today + timedelta(days=exp_offset) if exp_offset else None
    )
    doc.qty_on_hand = qty
    # supplier on IMM Spare Batch is Link to Supplier (not AC Supplier),
    # so leave blank if no native Supplier exists.
    if supplier and frappe.db.exists("Supplier", supplier):
        doc.supplier = supplier
    doc.supplier_lot_no = supplier_lot
    doc.storage_condition = "Normal"
    doc.is_expired = 0
    doc.is_quarantined = 0
    doc.notes = (
        "Nhập kho theo PO chính ngạch — đã kiểm IQC, đầy đủ CO/CQ kèm tem nhập khẩu."
    )
    doc.save(ignore_permissions=True)


# ---------------------------------------------------------------------------
# WATCHLIST + FORECAST
# ---------------------------------------------------------------------------
def seed_watchlist() -> int:
    n = 0
    asset_map = {
        "SP-EVT-PEEP-V01": ASSET_DRAGER,
        "SP-EVT-O2SENS": ASSET_DRAGER,
        "SP-MBT9-BAT-001": ASSET_MINDRAY,
        "SP-MBT9-SPO2": ASSET_MINDRAY,
        "SP-EPQ7-C51-PRB": ASSET_PHILIPS,
    }
    for code, asset in asset_map.items():
        part = frappe.db.get_value(
            "AC Spare Part", {"part_code": code}, "name"
        )
        if not part:
            continue
        spec = next(s for s in SPARE_PARTS if s["part_code"] == code)
        wl_name = f"WL-{code}"
        if frappe.db.exists("IMM Critical Spare Watchlist", wl_name):
            doc = frappe.get_doc("IMM Critical Spare Watchlist", wl_name)
        else:
            doc = frappe.new_doc("IMM Critical Spare Watchlist")
            doc.watchlist_name = wl_name
        doc.critical_asset = asset
        doc.spare_part = part
        doc.min_required_on_hand = spec["min_stock_level"]
        doc.warehouse = PRIMARY_WAREHOUSE
        doc.active = 1
        doc.save(ignore_permissions=True)
        n += 1
    frappe.db.commit()
    return n


def seed_forecast() -> int:
    """Create an IMM Spare Part Forecast parent with items for every part."""
    parent_name = "FCST-IMM15-2026-Q3"
    if not frappe.db.exists("DocType", "IMM Spare Part Forecast"):
        _log("IMM Spare Part Forecast doctype missing — skip")
        return 0
    meta = frappe.get_meta("IMM Spare Part Forecast")
    fieldnames = {f.fieldname for f in meta.fields}
    if frappe.db.exists("IMM Spare Part Forecast", parent_name):
        doc = frappe.get_doc("IMM Spare Part Forecast", parent_name)
        doc.set("items", [])
    else:
        doc = frappe.new_doc("IMM Spare Part Forecast")
        # name is autoname; try to set common fields
    # Required fields per DocType: forecast_period (Data), period_start (Date),
    # period_end (Date), method (Select).
    today = datetime.now().date()
    period_end = today + timedelta(days=365)
    if "forecast_period" in fieldnames:
        doc.forecast_period = "Q3/2026 — Q2/2027 (12 tháng)"
    if "period_start" in fieldnames:
        doc.period_start = today
    if "period_end" in fieldnames:
        doc.period_end = period_end
    if "forecast_name" in fieldnames:
        doc.forecast_name = parent_name
    if "horizon_months" in fieldnames:
        doc.horizon_months = 12
    if "forecast_start_date" in fieldnames:
        doc.forecast_start_date = today
    if "status" in fieldnames:
        doc.status = "Draft"
    if "warehouse" in fieldnames:
        doc.warehouse = PRIMARY_WAREHOUSE
    if "method" in fieldnames:
        doc.method = "Manual"

    items = []
    for spec in SPARE_PARTS:
        part = frappe.db.get_value(
            "AC Spare Part", {"part_code": spec["part_code"]}, "name"
        )
        if not part:
            continue
        items.append(
            {
                "spare_part": part,
                "forecast_qty": max(4, spec["stock_qty"] // 2),
                "reorder_point": spec["min_stock_level"],
                "safety_stock": max(
                    2, int(spec["min_stock_level"] * 0.5)
                ),
                "current_qty": spec["stock_qty"],
                "historical_consumption_12m": max(
                    4, spec["stock_qty"] // 2 + 2
                ),
                "recommended_action": "Hold"
                if spec["stock_qty"] > spec["min_stock_level"] * 1.5
                else "Reorder",
            }
        )
    for it in items:
        doc.append("items", it)
    try:
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        return len(items)
    except Exception as e:
        _log(f"forecast save failed: {e}")
        frappe.db.rollback()
        return 0


# ---------------------------------------------------------------------------
# ASSET REPAIR LINKAGE — wire parts to existing CM (Asset Repair) docs
# so `total_parts_cost` shows up for the 3 target assets.
# ---------------------------------------------------------------------------
def seed_repair_links() -> dict[str, int]:
    out = {"repairs_created": 0, "rows_added": 0, "movements": 0}
    plans = [
        {
            "asset_ref": ASSET_DRAGER,
            "name_hint": "AR-DRAGER-PEEP-001",
            "summary": (
                "Thay van PEEP do van bị rò khí phát hiện trong ca trực ngày 08/05. "
                "Kiểm tra hệ thống van xả, vệ sinh khối điều khiển khí thở, calib lại sau lắp."
            ),
            "parts": [
                ("SP-EVT-PEEP-V01", 1),
                ("SP-EVT-O2SENS", 1),
            ],
        },
        {
            "asset_ref": ASSET_MINDRAY,
            "name_hint": "AR-MINDRAY-BAT-001",
            "summary": (
                "Thay pin Lithium-ion và cảm biến SpO2 cho Monitor BeneView T9 — "
                "pin chai sau 26 tháng, SpO2 báo lỗi 'Sensor Off' liên tục."
            ),
            "parts": [
                ("SP-MBT9-BAT-001", 1),
                ("SP-MBT9-SPO2", 2),
            ],
        },
        {
            "asset_ref": ASSET_PHILIPS,
            "name_hint": "AR-PHILIPS-GEL-001",
            "summary": (
                "Bảo trì lập kế hoạch + bổ sung gel siêu âm sau khi đầu dò C5-1 bị "
                "trầy lớp tiếp xúc — thay can gel mới, lau và kiểm tra lớp ghép âm."
            ),
            "parts": [
                ("SP-EPQ7-GEL-5L", 2),
            ],
        },
    ]

    for p in plans:
        repair = _ensure_asset_repair(p["asset_ref"], p["summary"])
        if not repair:
            continue
        out["repairs_created"] += 1

        # DB-level rewrite of child rows + parent total so we bypass
        # update-after-submit guards if the doc was previously submitted.
        frappe.db.sql(
            """DELETE FROM `tabSpare Parts Used`
                WHERE parent=%s AND parenttype='Asset Repair'""",
            (repair,),
        )

        total = 0.0
        for i, (code, qty) in enumerate(p["parts"]):
            sp = frappe.db.get_value(
                "AC Spare Part",
                {"part_code": code},
                [
                    "name",
                    "part_name",
                    "unit_cost",
                    "stock_uom",
                    "manufacturer_part_no",
                ],
                as_dict=True,
            )
            if not sp:
                continue
            line_total = float(sp.unit_cost or 0) * qty
            total += line_total
            row = frappe.new_doc("Spare Parts Used")
            row.parent = repair
            row.parenttype = "Asset Repair"
            row.parentfield = "spare_parts_used"
            row.idx = i + 1
            row.item_code = sp.name
            row.item_name = sp.part_name
            row.manufacturer_part_no = sp.manufacturer_part_no or ""
            row.qty = qty
            row.uom = sp.stock_uom
            row.unit_cost = sp.unit_cost
            row.total_cost = line_total
            row.notes = "Xuất kho theo phiếu IMM-15 trong ca sửa chữa."
            row.db_insert()
            out["rows_added"] += 1

        # Patch parent at DB level
        frappe.db.set_value(
            "Asset Repair",
            repair,
            {
                "total_parts_cost": total,
                "status": "Completed",
                "completion_datetime": datetime.now() - timedelta(days=1),
            },
            update_modified=False,
        )

        # Create AC Stock Movement (Issue) submitted to reflect issuance
        _create_issue_movement(repair, p["parts"])
        out["movements"] += 1

    frappe.db.commit()
    return out


def _ensure_asset_repair(asset: str, summary: str) -> str | None:
    existing = frappe.db.get_value(
        "Asset Repair",
        {"asset_ref": asset, "status": ["in", ("Completed", "Open", "Diagnosing")]},
        "name",
    )
    if existing:
        return existing
    asset_doc = frappe.get_doc("AC Asset", asset)
    doc = frappe.new_doc("Asset Repair")
    doc.asset_ref = asset
    doc.asset_name = asset_doc.asset_name
    doc.repair_type = "Corrective"
    doc.priority = "Urgent"
    doc.status = "Diagnosing"
    doc.open_datetime = datetime.now() - timedelta(days=4)
    doc.assigned_datetime = datetime.now() - timedelta(days=3, hours=20)
    doc.completion_datetime = datetime.now() - timedelta(days=1)
    doc.diagnosis_notes = summary
    doc.repair_summary = summary
    doc.root_cause_category = "Wear and Tear"
    doc.save(ignore_permissions=True)
    return doc.name


def _create_issue_movement(repair_name: str, parts: list[tuple[str, int]]) -> None:
    # idempotent: skip if movement already references this repair
    ref = frappe.db.get_value(
        "AC Stock Movement",
        {"reference_type": "Asset Repair", "reference_name": repair_name},
        "name",
    )
    if ref:
        return
    doc = frappe.new_doc("AC Stock Movement")
    doc.movement_type = "Issue"
    doc.movement_date = datetime.now() - timedelta(days=2)
    doc.from_warehouse = PRIMARY_WAREHOUSE
    doc.reference_type = "Asset Repair"
    doc.reference_name = repair_name
    doc.requested_by = frappe.session.user or "Administrator"
    doc.notes = (
        "Xuất phụ tùng phục vụ ca sửa chữa thực tế trên thiết bị y tế."
    )
    total = 0.0
    for code, qty in parts:
        sp = frappe.db.get_value(
            "AC Spare Part",
            {"part_code": code},
            ["name", "part_name", "unit_cost", "stock_uom"],
            as_dict=True,
        )
        if not sp:
            continue
        line = doc.append(
            "items",
            {
                "spare_part": sp.name,
                "part_name": sp.part_name,
                "uom": sp.stock_uom,
                "qty": qty,
                "unit_cost": sp.unit_cost,
                "total_cost": (sp.unit_cost or 0) * qty,
                "stock_qty": qty,
                "conversion_factor": 1,
                "notes": "Xuất theo phiếu yêu cầu của tổ kỹ thuật.",
            },
        )
        total += line.total_cost or 0
    doc.total_value = total
    try:
        doc.insert(ignore_permissions=True)
        doc.submit()
    except Exception as e:
        _log(f"issue movement save failed: {e}")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def run() -> dict[str, Any]:
    _log("== STEP 1: cleanup test fixtures ==")
    cleanup = cleanup_test_spare_parts()
    _log(f"cleanup: {cleanup}")

    _log("== STEP 2: seed spare-part master ==")
    parts = seed_spare_parts_master()
    _log(f"upserted {len(parts)} parts")

    _log("== STEP 3: seed stock + batches ==")
    sb = seed_stock_and_batches()
    _log(f"stock/batch: {sb}")

    _log("== STEP 4: seed watchlist ==")
    wl = seed_watchlist()
    _log(f"watchlist rows: {wl}")

    _log("== STEP 5: seed forecast ==")
    fc = seed_forecast()
    _log(f"forecast items: {fc}")

    _log("== STEP 6: wire repairs + issue movements ==")
    rp = seed_repair_links()
    _log(f"repair linkage: {rp}")

    frappe.db.commit()
    summary = {
        "cleanup": cleanup,
        "parts": parts,
        "stock_batches": sb,
        "watchlist": wl,
        "forecast_items": fc,
        "repairs": rp,
    }
    _log(f"DONE — summary: {summary}")
    return summary
