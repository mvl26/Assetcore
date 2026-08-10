# Copyright (c) 2026, AssetCore Team
"""Đồ thị liên kết của IMM Asset Calibration (phiếu hiệu chuẩn) — SSoT Desk + Vue.

Phiếu hiệu chuẩn là doctype LÁ: không bản ghi nào trỏ ngược về nó. Vì vậy toàn bộ đồ thị
là liên kết XUÔI (`internal_links`) — vẫn có giá trị thật với người dùng: từ phiếu hiệu
chuẩn mở thẳng sang thiết bị, lịch hiệu chuẩn, đơn vị hiệu chuẩn, phiếu bảo trì nguồn và
hồ sơ CAPA nếu kết quả không đạt.
"""
from __future__ import annotations

from frappe import _


def get_data() -> dict:
    return {
        "internal_links": {
            "AC Asset": "asset",
            "IMM Device Model": "device_model",
            "IMM Calibration Schedule": "calibration_schedule",
            "AC Supplier": "lab_supplier",
            "PM Work Order": "pm_work_order",
            "IMM CAPA Record": "capa_record",
        },
        "transactions": [
            {"label": _("Thiết bị"), "items": ["AC Asset", "IMM Device Model"]},
            {
                "label": _("Kế hoạch & Đơn vị hiệu chuẩn"),
                "items": ["IMM Calibration Schedule", "AC Supplier"],
            },
            {"label": _("Liên quan"), "items": ["PM Work Order", "IMM CAPA Record"]},
        ],
    }
