# Copyright (c) 2026, AssetCore Team
"""Đồ thị liên kết của AC Spare Part (phụ tùng) — SSoT Desk + Vue.

Phần lớn bản ghi tiêu thụ phụ tùng nằm ở BẢNG CON (dòng phiếu xuất/nhập, dòng kiểm kê,
dòng cấp phát) — Frappe không lọc ngược được từ bảng con lên phiếu cha, nên đồ thị chỉ
liệt kê những doctype trỏ TRỰC TIẾP tới phụ tùng. Liệt kê doctype cha ở đây sẽ cho ra
số đếm luôn bằng 0, tức là một liên kết câm.
"""
from __future__ import annotations

from frappe import _


def get_data() -> dict:
    return {
        "fieldname": "spare_part",
        "internal_links": {"AC Supplier": "preferred_supplier"},
        "transactions": [
            {"label": _("Tồn kho & Lô hàng"), "items": ["AC Spare Part Stock", "IMM Spare Batch"]},
            {"label": _("Theo dõi vật tư trọng yếu"), "items": ["IMM Critical Spare Watchlist"]},
            {"label": _("Nhà cung cấp"), "items": ["AC Supplier"]},
        ],
    }
