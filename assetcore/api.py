# Copyright (c) 2026, AssetCore Team and contributors
# Legacy REST endpoints — được re-export từ api/imm04.py để giữ backward compatibility

import frappe
from frappe import _
from assetcore.utils.helpers import _ok, _err

_DOCTYPE = "Asset Commissioning"
_TERMINAL_STATES = {"Clinical_Release", "Return_To_Vendor"}


@frappe.whitelist()
def get_commissioning_by_barcode(qr_code: str) -> dict:
    """
    GET /api/method/assetcore.api.get_commissioning_by_barcode?qr_code=BV-ICU-2026-001

    Trả về lịch sử khai sinh của thiết bị từ mã QR.
    Dùng cho ứng dụng Scanner của KTV.
    """
    if not qr_code:
        return _err("Thiếu tham số qr_code", "MISSING_PARAM")

    record = frappe.db.get_value(
        _DOCTYPE,
        {"internal_tag_qr": qr_code},
        ["name", "workflow_state", "master_item", "vendor",
         "installation_date", "final_asset", "clinical_dept"],
        as_dict=True,
    ) or frappe.db.get_value(
        _DOCTYPE,
        {"vendor_serial_no": qr_code},
        ["name", "workflow_state", "master_item", "vendor",
         "installation_date", "final_asset", "clinical_dept"],
        as_dict=True,
    )

    if not record:
        return _err(f"Không tìm thấy thiết bị với mã '{qr_code}'", "NOT_FOUND")

    doc = frappe.get_doc(_DOCTYPE, record.name)
    baseline_summary = [
        {"parameter": r.parameter, "measured_val": r.measured_val,
         "unit": r.unit, "test_result": r.test_result}
        for r in doc.baseline_tests
    ]

    return _ok({
        "commissioning_id": record.name,
        "current_state": record.workflow_state,
        "asset_id": record.final_asset,
        "device": {
            "model": record.master_item,
            "vendor": record.vendor,
            "location": record.clinical_dept,
            "installation_date": str(record.installation_date or ""),
        },
        "baseline_tests": baseline_summary,
        "is_released": record.workflow_state == "Clinical_Release",
    })


@frappe.whitelist()
def get_dashboard_stats() -> dict:
    """
    GET /api/method/assetcore.api.get_dashboard_stats

    Số liệu tổng hợp cho Dashboard IMM-04.
    Được re-export từ api/imm04.py::get_dashboard_stats.
    """
    from assetcore.api.imm04 import get_dashboard_stats as _impl
    return _impl()
