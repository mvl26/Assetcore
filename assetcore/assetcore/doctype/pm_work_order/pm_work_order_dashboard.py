# Copyright (c) 2026, AssetCore Team
"""Đồ thị liên kết của PM Work Order (phiếu bảo trì định kỳ) — SSoT dùng chung Desk + Vue.

Xem `ac_asset_dashboard.py` để biết cơ chế. Phiếu bảo trì nằm giữa chuỗi nghiệp vụ nên
có cả liên kết NGƯỢC (bản ghi sinh ra TỪ phiếu này) lẫn liên kết XUÔI (nguồn gốc của
phiếu) — hai loại khai khác nhau: ngược qua `fieldname`/`non_standard_fieldnames`,
xuôi qua `internal_links`.
"""
from __future__ import annotations

from frappe import _


def get_data() -> dict:
    return {
        "fieldname": "pm_work_order",
        "non_standard_fieldnames": {
            "Asset Repair": "source_pm_wo",
        },
        "internal_links": {
            "AC Asset": "asset_ref",
            "PM Schedule": "pm_schedule",
        },
        "transactions": [
            {"label": _("Thiết bị & Lịch bảo trì"), "items": ["AC Asset", "PM Schedule"]},
            {
                "label": _("Phát sinh từ phiếu này"),
                "items": ["PM Task Log", "Asset Repair", "IMM Asset Calibration"],
            },
        ],
    }
