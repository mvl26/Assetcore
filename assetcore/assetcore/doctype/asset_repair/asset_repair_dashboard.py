# Copyright (c) 2026, AssetCore Team
"""Đồ thị liên kết của Asset Repair (phiếu sửa chữa) — SSoT dùng chung Desk + Vue.

`Incident Report` và `Firmware Change Request` đều có liên kết HAI CHIỀU với phiếu sửa
chữa. Mỗi doctype chỉ được xuất hiện MỘT lần trong đồ thị (guard chặn trùng), nên chọn
chiều phản ánh đúng câu hỏi người dùng đặt ra khi mở phiếu sửa: "phiếu này bắt nguồn từ
đâu" ⇒ dùng chiều XUÔI (`internal_links`) cho cả hai.
"""
from __future__ import annotations

from frappe import _


def get_data() -> dict:
    return {
        "fieldname": "asset_repair_wo",
        "internal_links": {
            "AC Asset": "asset_ref",
            "Incident Report": "incident_report",
            "PM Work Order": "source_pm_wo",
            "Firmware Change Request": "firmware_change_request",
        },
        "transactions": [
            {"label": _("Thiết bị"), "items": ["AC Asset"]},
            {
                "label": _("Nguồn gốc phiếu"),
                "items": ["Incident Report", "PM Work Order", "Firmware Change Request"],
            },
        ],
    }
