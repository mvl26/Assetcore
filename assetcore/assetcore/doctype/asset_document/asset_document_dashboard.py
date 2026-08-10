# Copyright (c) 2026, AssetCore Team
"""Đồ thị liên kết của Asset Document (hồ sơ thiết bị) — SSoT Desk + Vue."""
from __future__ import annotations

from frappe import _


def get_data() -> dict:
    return {
        "non_standard_fieldnames": {
            "Document Request": "fulfilled_by",
            "Expiry Alert Log": "asset_document",
            "IMM Training Program": "qms_doc_ref",
            "IMM User Competency": "certificate_file",
        },
        "internal_links": {
            "AC Asset": "asset_ref",
            "IMM Device Model": "model_ref",
            "Asset Commissioning": "source_commissioning",
        },
        "transactions": [
            {
                "label": _("Đối tượng hồ sơ"),
                "items": ["AC Asset", "IMM Device Model", "Asset Commissioning"],
            },
            {
                "label": _("Sử dụng & Cảnh báo"),
                "items": [
                    "Document Request",
                    "Expiry Alert Log",
                    "IMM Training Program",
                    "IMM User Competency",
                ],
            },
        ],
    }
