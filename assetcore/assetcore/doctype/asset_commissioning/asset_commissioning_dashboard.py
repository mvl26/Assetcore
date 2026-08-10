# Copyright (c) 2026, AssetCore Team
"""Đồ thị liên kết của Asset Commissioning (nghiệm thu lắp đặt) — SSoT Desk + Vue."""
from __future__ import annotations

from frappe import _


def get_data() -> dict:
    return {
        "non_standard_fieldnames": {
            "Asset Document": "source_commissioning",
            "Asset QA Non Conformance": "ref_commissioning",
            "PM Schedule": "created_from_commissioning",
        },
        "internal_links": {
            "AC Asset": "final_asset",
            "IMM Device Model": "master_item",
            "AC Supplier": "vendor",
            "AC Purchase": "po_reference",
        },
        "transactions": [
            {
                "label": _("Thiết bị & Nguồn cung"),
                "items": ["AC Asset", "IMM Device Model", "AC Supplier", "AC Purchase"],
            },
            {
                "label": _("Phát sinh từ nghiệm thu"),
                "items": ["Asset Document", "Asset QA Non Conformance", "PM Schedule"],
            },
        ],
    }
