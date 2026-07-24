# Copyright (c) 2026, AssetCore Team
"""Đồ thị liên kết của Incident Report (sự cố) — SSoT dùng chung Desk + Vue.

Sự cố là ĐIỂM KHỞI PHÁT của chuỗi khắc phục, nên ưu tiên chiều NGƯỢC: hiển thị những gì
đã được mở ra TỪ sự cố này (phiếu sửa chữa, phân tích nguyên nhân, hồ sơ CAPA) — đó là
câu hỏi người dùng thực sự đặt ra khi mở một sự cố. Thiết bị là liên kết xuôi duy nhất.
"""
from __future__ import annotations

from frappe import _


def get_data() -> dict:
    return {
        "fieldname": "incident_report",
        "non_standard_fieldnames": {
            "IMM CAPA Record": "linked_incident",
        },
        "internal_links": {
            "AC Asset": "asset",
        },
        "transactions": [
            {"label": _("Thiết bị"), "items": ["AC Asset"]},
            {
                "label": _("Xử lý & Khắc phục"),
                "items": ["Asset Repair", "IMM RCA Record", "IMM CAPA Record"],
            },
        ],
    }
