"""
clean_uom_and_master_data.py
Chuẩn hóa UOM và dữ liệu master cho thiết bị y tế.

Usage:
    bench --site <site> execute assetcore.tests.clean_uom_and_master_data.run
"""

import frappe
from frappe.utils import now

# ── Ánh xạ UOM ERPNext mặc định → tên tiếng Việt y tế ──────────────────────
_UOM_MAP: dict[str, str] = {
    # ERPNext defaults → Vietnamese medical terms
    "Nos":    "Hệ thống",
    "Unit":   "Hệ thống",
    "Pcs":    "Cái",
    "Piece":  "Cái",
    "Set":    "Bộ",
    "Box":    "Hộp",
    "Pack":   "Gói",
    "Packet": "Gói",
    "Bottle": "Lọ",
    "Tube":   "Ống",
    "Kit":    "Bộ kit",
    "Pair":   "Cặp",
    "Roll":   "Cuộn",
}

# UOM dành riêng cho thiết bị (asset) — nếu chưa tồn tại sẽ tạo mới
_MEDICAL_UOMS: list[dict] = [
    {"uom_name": "Hệ thống", "description": "Thiết bị/hệ thống hoàn chỉnh"},
    {"uom_name": "Máy",      "description": "Máy móc thiết bị đơn lẻ"},
    {"uom_name": "Bộ",       "description": "Bộ thiết bị gồm nhiều thành phần"},
    {"uom_name": "Cái",      "description": "Đơn vị tính thiết bị đơn"},
    {"uom_name": "Lọ",       "description": "Lọ/chai hoá chất hoặc sinh phẩm"},
    {"uom_name": "Hộp",      "description": "Hộp vật tư tiêu hao"},
    {"uom_name": "Gói",      "description": "Gói vật tư đóng gói sẵn"},
    {"uom_name": "Ống",      "description": "Ống hoá chất hoặc sinh phẩm"},
    {"uom_name": "Bộ kit",   "description": "Bộ kit xét nghiệm/thử nghiệm"},
    {"uom_name": "Cặp",      "description": "Cặp phụ kiện đi kèm"},
    {"uom_name": "Cuộn",     "description": "Cuộn vật tư (băng, dây...)"},
]

# Ánh xạ UOM → tên thiết bị y tế thường dùng (heuristic theo keyword)
_ASSET_UOM_RULES: list[tuple[list[str], str]] = [
    (["máy", "hệ thống", "thiết bị", "monitor", "máy thở", "x-quang",
      "siêu âm", "nội soi", "xét nghiệm", "lọc máu", "icu", "ct", "mri",
      "laser", "điện tim", "điện não", "defibrillator", "infusion"],  "Máy"),
    (["bộ", "set", "tủ", "giường", "xe", "rack"],                     "Bộ"),
    (["phụ kiện", "cảm biến", "đầu dò", "probe", "transducer"],       "Cái"),
]


def _ensure_medical_uoms() -> None:
    """Đảm bảo tất cả UOM y tế tồn tại trong hệ thống."""
    for uom in _MEDICAL_UOMS:
        if not frappe.db.exists("UOM", uom["uom_name"]):
            doc = frappe.get_doc({"doctype": "UOM", **uom})
            doc.insert(ignore_permissions=True)
            frappe.db.commit()
            print(f"  ✓ Tạo UOM: {uom['uom_name']}")


def _rename_existing_uoms() -> dict[str, str]:
    """
    Đổi tên UOM ERPNext mặc định → tiếng Việt y tế.
    Trả về dict {tên_cũ: tên_mới} cho các bản ghi đã đổi thành công.
    """
    renamed: dict[str, str] = {}
    for old_name, new_name in _UOM_MAP.items():
        if not frappe.db.exists("UOM", old_name):
            continue
        if frappe.db.exists("UOM", new_name):
            # Đích đã tồn tại → chỉ ghi nhận để update references
            renamed[old_name] = new_name
            continue
        try:
            frappe.rename_doc("UOM", old_name, new_name, force=True, ignore_permissions=True)
            frappe.db.commit()
            renamed[old_name] = new_name
            print(f"  ✓ Đổi tên UOM: {old_name!r} → {new_name!r}")
        except Exception as exc:
            print(f"  ✗ Lỗi đổi tên {old_name!r}: {exc}")
    return renamed


def _infer_asset_uom(asset_name: str) -> str:
    """Suy luận UOM phù hợp cho thiết bị từ tên thiết bị."""
    lower = asset_name.lower()
    for keywords, uom in _ASSET_UOM_RULES:
        if any(kw in lower for kw in keywords):
            return uom
    return "Hệ thống"


def _update_asset_uom() -> int:
    """Cập nhật trường uom trên AC Asset theo tên thiết bị."""
    assets = frappe.get_all(
        "AC Asset",
        filters={"docstatus": ["!=", 2]},
        fields=["name", "asset_name", "uom"],
        limit=None,
    )
    updated = 0
    for a in assets:
        target_uom = _infer_asset_uom(a["asset_name"])
        if a.get("uom") == target_uom:
            continue
        try:
            frappe.db.set_value("AC Asset", a["name"], "uom", target_uom,
                                update_modified=False)
            updated += 1
        except Exception as exc:
            print(f"  ✗ {a['name']}: {exc}")
    frappe.db.commit()
    print(f"  ✓ Đã cập nhật uom cho {updated} thiết bị")
    return updated


def _update_spare_part_uom() -> int:
    """Cập nhật unit trên IMM Device Spare Part child table."""
    parts = frappe.db.sql(
        """
        SELECT name, part_name, unit
        FROM `tabIMM Device Spare Part`
        WHERE ifnull(unit,'') = '' OR unit IN %(old_names)s
        """,
        {"old_names": tuple(_UOM_MAP.keys()) or ("__none__",)},
        as_dict=True,
    )
    updated = 0
    for p in parts:
        if not p.get("unit") or p["unit"] in _UOM_MAP:
            new_unit = _UOM_MAP.get(p.get("unit", ""), "Cái")
            frappe.db.set_value("IMM Device Spare Part", p["name"], "unit", new_unit,
                                update_modified=False)
            updated += 1
    frappe.db.commit()
    print(f"  ✓ Đã cập nhật unit cho {updated} spare part")
    return updated


def _update_item_uom() -> int:
    """Cập nhật stock_uom trên Item liên kết với thiết bị y tế."""
    items = frappe.db.sql(
        """
        SELECT name, item_name, stock_uom
        FROM `tabItem`
        WHERE item_group LIKE '%Medical%'
           OR item_group LIKE '%Thiết bị%'
           OR item_group LIKE '%Equipment%'
        """,
        as_dict=True,
    )
    updated = 0
    for item in items:
        old_uom = item.get("stock_uom", "")
        if old_uom in _UOM_MAP:
            new_uom = _UOM_MAP[old_uom]
            frappe.db.set_value("Item", item["name"], "stock_uom", new_uom,
                                update_modified=False)
            updated += 1
    frappe.db.commit()
    print(f"  ✓ Đã cập nhật stock_uom cho {updated} Item y tế")
    return updated


def run() -> None:
    """Entry point chính — chạy toàn bộ pipeline chuẩn hóa UOM."""
    print("\n=== CHUẨN HÓA UOM THIẾT BỊ Y TẾ ===")
    print(f"Thời gian: {now()}\n")

    print("--- Bước 1: Tạo UOM y tế thiếu ---")
    _ensure_medical_uoms()

    print("\n--- Bước 2: Đổi tên UOM ERPNext → tiếng Việt ---")
    _rename_existing_uoms()

    print("\n--- Bước 3: Cập nhật UOM trên AC Asset ---")
    _update_asset_uom()

    print("\n--- Bước 4: Cập nhật unit trên Spare Part ---")
    _update_spare_part_uom()

    print("\n--- Bước 5: Cập nhật stock_uom trên Item y tế ---")
    _update_item_uom()

    print("\n=== HOÀN THÀNH ===\n")
