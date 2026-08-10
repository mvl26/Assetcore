# Copyright (c) 2026, AssetCore Team
"""Đồ thị liên kết của IMM Device Model (mẫu máy) — SSoT Desk + Vue.

Cố ý KHÔNG liệt kê ``IMM Recall Notice`` dù doctype đó có Link ``device_model``: nó
thuộc nhánh IMM-10 đang dở của phiên khác (chưa commit). Thêm vào đây sẽ tạo phụ thuộc
chéo lô — bổ sung khi nhánh IMM-10 land.
"""
from __future__ import annotations

from frappe import _


def get_data() -> dict:
    return {
        "fieldname": "device_model",
        "non_standard_fieldnames": {
            "Asset Commissioning": "master_item",
            "Asset Document": "model_ref",
            "IMM Needs Request": "device_model_ref",
            "IMM Tech Spec": "device_model_ref",
            "IMM Training Program": "target_device_model",
        },
        "transactions": [
            {"label": _("Thiết bị đang dùng"), "items": ["AC Asset", "Asset Commissioning"]},
            {"label": _("Hồ sơ & Tiêu chuẩn kỹ thuật"), "items": [
                "Asset Document", "IMM Tech Spec", "IMM Needs Request",
            ]},
            {"label": _("Bảo trì & Hiệu chuẩn"), "items": [
                "IMM Asset Calibration", "IMM Calibration Schedule",
            ]},
            {"label": _("Đào tạo & Năng lực"), "items": [
                "IMM Training Program", "IMM User Competency",
            ]},
        ],
    }
