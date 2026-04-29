# Copyright (c) 2026, AssetCore Team
# UOM Service — tra cứu và quy đổi đơn vị tính cho phụ tùng AssetCore.
#
# Design principle:
#   - Mỗi AC Spare Part có một stock_uom (đơn vị tồn kho cơ bản).
#   - Bảng uom_conversions trên spare part lưu "1 [uom] = X [stock_uom]".
#   - Mọi giao dịch (mua, xuất, nhập) phải quy về stock_uom trước khi cập nhật tồn.

from __future__ import annotations

import frappe
from frappe import _

_DT_UOM  = "AC UOM"
_DT_CONV = "AC UOM Conversion"


# ─── Exceptions ─────────────────────────────────────────────────────────────

class UOMConversionNotFound(Exception):
    pass


# ─── Core lookup ────────────────────────────────────────────────────────────

def get_stock_uom(spare_part: str) -> str:
    """Trả về stock_uom của phụ tùng. Raises nếu spare part không tồn tại."""
    uom = frappe.db.get_value("AC Spare Part", spare_part, "stock_uom")
    if not uom:
        frappe.throw(_("Không tìm thấy phụ tùng hoặc chưa thiết lập stock UOM: {0}").format(spare_part))
    return uom


def get_conversion_factor(spare_part: str, from_uom: str, to_uom: str) -> float:
    """Trả về hệ số quy đổi: 1 [from_uom] = ? [to_uom].

    Lookup order:
    1. Nếu from_uom == to_uom → 1.0
    2. Tìm trong bảng uom_conversions của spare part (from_uom → stock_uom)
    3. Tìm chiều ngược (to_uom → stock_uom, rồi đảo)
    4. Tìm cross-conversion qua stock_uom
    5. Raise UOMConversionNotFound
    """
    if from_uom == to_uom:
        return 1.0

    stock_uom = get_stock_uom(spare_part)

    conversions: list[dict] = frappe.get_all(
        _DT_CONV,
        filters={"parent": spare_part, "parenttype": "AC Spare Part"},
        fields=["uom", "conversion_factor"],
    )
    conv_map = {row["uom"]: float(row["conversion_factor"]) for row in conversions}

    if to_uom == stock_uom and from_uom in conv_map:
        return conv_map[from_uom]

    if from_uom == stock_uom and to_uom in conv_map:
        return 1.0 / conv_map[to_uom]

    if from_uom in conv_map and to_uom in conv_map:
        return conv_map[from_uom] / conv_map[to_uom]

    raise UOMConversionNotFound(
        _("Không tìm thấy hệ số quy đổi: {0} → {1} cho phụ tùng {2}").format(from_uom, to_uom, spare_part)
    )


def convert_qty(spare_part: str, qty: float, from_uom: str, to_uom: str) -> float:
    """Quy đổi số lượng từ from_uom sang to_uom."""
    return qty * get_conversion_factor(spare_part, from_uom, to_uom)


def convert_to_stock_qty(spare_part: str, qty: float, from_uom: str) -> float:
    """Quy đổi số lượng về stock_uom của phụ tùng."""
    return convert_qty(spare_part, qty, from_uom, get_stock_uom(spare_part))


# ─── Info ────────────────────────────────────────────────────────────────────

def get_spare_part_uom_info(spare_part: str) -> dict:
    """Trả về toàn bộ thông tin UOM + bảng quy đổi của một phụ tùng."""
    doc = frappe.get_value(
        "AC Spare Part",
        spare_part,
        ["stock_uom", "purchase_uom", "part_name"],
        as_dict=True,
    )
    if not doc:
        frappe.throw(_("Không tìm thấy phụ tùng: {0}").format(spare_part))

    conversions = frappe.get_all(
        _DT_CONV,
        filters={"parent": spare_part, "parenttype": "AC Spare Part"},
        fields=["uom", "conversion_factor", "is_purchase_uom", "is_issue_uom"],
        order_by="idx asc",
    )

    rows = [{"uom": doc.stock_uom, "conversion_factor": 1.0, "is_stock_uom": True}]
    for c in conversions:
        rows.append({
            "uom": c.uom,
            "conversion_factor": float(c.conversion_factor),
            "is_purchase_uom": bool(c.is_purchase_uom),
            "is_issue_uom": bool(c.is_issue_uom),
            "is_stock_uom": False,
        })

    return {
        "spare_part": spare_part,
        "part_name": doc.part_name,
        "stock_uom": doc.stock_uom,
        "purchase_uom": doc.purchase_uom or doc.stock_uom,
        "conversions": rows,
    }


# ─── Seed ────────────────────────────────────────────────────────────────────

def seed_ac_uoms() -> list[str]:
    """Tạo các AC UOM y tế chuẩn Việt Nam nếu chưa tồn tại."""
    entries = [
        # Đơn vị đếm tiếng Việt — "Cái" là mặc định khi không chọn
        {"uom_name": "Cái",    "symbol": "cái",  "must_be_whole_number": 1, "description": "Đơn vị mặc định"},
        {"uom_name": "Hộp",    "symbol": "hộp",  "must_be_whole_number": 1},
        {"uom_name": "Thùng",  "symbol": "thùng","must_be_whole_number": 1},
        {"uom_name": "Bộ",     "symbol": "bộ",   "must_be_whole_number": 1},
        {"uom_name": "Viên",   "symbol": "viên", "must_be_whole_number": 1},
        {"uom_name": "Ống",    "symbol": "ống",  "must_be_whole_number": 1},
        {"uom_name": "Lọ",     "symbol": "lọ",   "must_be_whole_number": 1},
        {"uom_name": "Gói",    "symbol": "gói",  "must_be_whole_number": 1},
        {"uom_name": "Tấm",    "symbol": "tấm",  "must_be_whole_number": 1},
        {"uom_name": "Cuộn",   "symbol": "cuộn", "must_be_whole_number": 1},
        {"uom_name": "Cặp",    "symbol": "cặp",  "must_be_whole_number": 1},
        {"uom_name": "Máy",    "symbol": "máy",  "must_be_whole_number": 1},
        {"uom_name": "Bình",   "symbol": "bình", "must_be_whole_number": 1},
        {"uom_name": "Chai",   "symbol": "chai", "must_be_whole_number": 1},
    ]
    created = []
    for item in entries:
        if not frappe.db.exists(_DT_UOM, item["uom_name"]):
            frappe.get_doc({"doctype": _DT_UOM, **item}).insert(ignore_permissions=True)
            created.append(item["uom_name"])
    return created
