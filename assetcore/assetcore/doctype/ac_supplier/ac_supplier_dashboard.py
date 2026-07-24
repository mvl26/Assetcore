# Copyright (c) 2026, AssetCore Team
"""Đồ thị liên kết của AC Supplier (nhà cung cấp) — SSoT Desk + Vue."""
from __future__ import annotations

from frappe import _


def get_data() -> dict:
    return {
        "fieldname": "supplier",
        "non_standard_fieldnames": {
            "AC Spare Part": "preferred_supplier",
            "Asset Commissioning": "vendor",
            "IMM Asset Calibration": "lab_supplier",
            "IMM Calibration Schedule": "preferred_lab",
            "IMM Procurement Decision": "winner_supplier",
        },
        "transactions": [
            {"label": _("Mua sắm & Hợp đồng"), "items": [
                "AC Purchase", "IMM Procurement Decision", "Service Contract", "IMM AVL Entry",
            ]},
            {"label": _("Cung ứng"), "items": ["AC Asset", "AC Spare Part", "AC Stock Movement"]},
            {"label": _("Dịch vụ hiệu chuẩn"), "items": [
                "IMM Asset Calibration", "IMM Calibration Schedule",
            ]},
            {"label": _("Đánh giá nhà cung cấp"), "items": [
                "IMM Supplier Audit", "IMM Vendor Scorecard",
            ]},
        ],
    }
