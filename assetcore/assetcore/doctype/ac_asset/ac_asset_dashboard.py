# Copyright (c) 2026, AssetCore Team
"""Đồ thị liên kết của AC Asset — SSoT DUY NHẤT cho "bản ghi liên quan".

Đọc bởi:
  - **Desk**: ``frappe.model.meta.Meta.get_dashboard_data`` nạp module suffix
    ``_dashboard`` rồi gọi ``get_data`` ⇒ tab Connections hiện ra, không cần code thêm.
  - **Vue FE**: ``assetcore.api.connections.get_connections`` đọc CHÍNH hàm này ⇒ hai
    tầng hiển thị không bao giờ lệch nhau.

FE **KHÔNG** được khai lại danh sách này ở bất kỳ đâu (SPEC §3 P1).

Mọi doctype trong ``items`` phải phân giải được về một Link field THẬT trỏ về AC Asset —
mặc định field ``asset``, ngoại lệ khai trong ``non_standard_fieldnames``. Sai tên field
thì Desk chỉ hiện badge 0 (trông như "chưa có dữ liệu") chứ không báo lỗi, nên invariant
này được khoá bằng ``tests/test_doctype_connectivity.py``.

Ghi chú thiết kế: ``Asset QA Non Conformance`` **không** nằm trong nhóm "Sự cố & Chất
lượng" dù về nghiệp vụ có liên quan — doctype đó chỉ trỏ tới ``Asset Commissioning``
(``ref_commissioning``), KHÔNG có Link nào về AC Asset, nên đưa vào sẽ thành liên kết câm.
Nó xuất hiện đúng chỗ trong đồ thị của Asset Commissioning.
"""
from __future__ import annotations

from frappe import _


def get_data() -> dict:
    """Nhóm bản ghi liên quan của một tài sản, theo trục vòng đời WHO HTM."""
    return {
        "fieldname": "asset",
        "non_standard_fieldnames": {
            "PM Work Order": "asset_ref",
            "PM Schedule": "asset_ref",
            "Asset Repair": "asset_ref",
            "Asset Document": "asset_ref",
            "Document Request": "asset_ref",
            "Firmware Change Request": "asset_ref",
            "Asset Commissioning": "final_asset",
            "IMM Critical Spare Watchlist": "critical_asset",
        },
        "transactions": [
            {
                "label": _("Bảo trì & Sửa chữa"),
                "items": [
                    "PM Work Order",
                    "PM Schedule",
                    "Asset Repair",
                    "AC Asset Downtime Log",
                ],
            },
            {
                "label": _("Hiệu chuẩn"),
                "items": ["IMM Asset Calibration", "IMM Calibration Schedule"],
            },
            {
                "label": _("Sự cố & Chất lượng"),
                "items": [
                    "Incident Report",
                    "IMM RCA Record",
                    "IMM CAPA Record",
                    "IMM Compliance Finding",
                ],
            },
            {
                "label": _("Hồ sơ & Vòng đời"),
                "items": [
                    "Asset Document",
                    "Document Request",
                    "Asset Commissioning",
                    "Asset Transfer",
                    "Asset Decommission",
                    "Asset Lifecycle Event",
                ],
            },
            {
                "label": _("Vật tư & Phần mềm thiết bị"),
                "items": [
                    "IMM Spare Allocation",
                    "IMM Critical Spare Watchlist",
                    "Firmware Change Request",
                ],
            },
        ],
    }
