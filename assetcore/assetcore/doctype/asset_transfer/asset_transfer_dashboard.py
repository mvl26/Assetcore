# Copyright (c) 2026, AssetCore Team
"""Đồ thị liên kết của Asset Transfer (điều chuyển thiết bị) — SSoT Desk + Vue.

Phiếu điều chuyển là doctype LÁ (không bản ghi nào trỏ ngược về nó), nên đồ thị hoàn
toàn là liên kết XUÔI: thiết bị được chuyển và hai đầu khoa/phòng — đủ để đi tiếp sang
ngữ cảnh mà người dùng cần khi xem một phiếu điều chuyển.
"""
from __future__ import annotations

from frappe import _


def get_data() -> dict:
    return {
        "internal_links": {
            "AC Asset": "asset",
            "AC Department": "to_department",
            "AC Location": "to_location",
        },
        "transactions": [
            {"label": _("Thiết bị"), "items": ["AC Asset"]},
            {"label": _("Nơi tiếp nhận"), "items": ["AC Department", "AC Location"]},
        ],
    }
