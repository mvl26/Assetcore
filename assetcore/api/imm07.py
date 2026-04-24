# Copyright (c) 2026, AssetCore Team
# REST API cho Module IMM-07 — Vận hành hàng ngày.
# Tier 1 — parse HTTP input → gọi services.imm07 → _ok / _err envelope.

from __future__ import annotations

import frappe

from assetcore.services import imm07 as svc
from assetcore.services.shared import ServiceError
from assetcore.utils.helpers import _err, _ok


def _handle(fn, *args, **kwargs) -> dict:
    """Execute service function and wrap result in _ok/_err envelope."""
    try:
        return _ok(fn(*args, **kwargs))
    except ServiceError as e:
        return _err(e.message, e.code)
    except frappe.ValidationError as e:
        return _err(str(e), "VALIDATION_ERROR")
    except frappe.DoesNotExistError as e:
        return _err(str(e), "NOT_FOUND")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"IMM-07 {fn.__name__}")
        return _err(str(e), "SYSTEM_ERROR")


# ─── Read Endpoints ───────────────────────────────────────────────────────────

@frappe.whitelist()
def get_daily_log(name: str) -> dict:
    """Lấy chi tiết Daily Operation Log."""
    return _handle(svc.get_daily_log, name)


@frappe.whitelist()
def list_daily_logs(
    asset: str = "",
    dept: str = "",
    date_from: str = "",
    date_to: str = "",
    operational_status: str = "",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Danh sách Daily Logs với filter và pagination."""
    return _handle(
        svc.list_daily_logs,
        asset or None, dept or None,
        date_from or None, date_to or None,
        operational_status or None,
        int(page), int(page_size),
    )


@frappe.whitelist()
def get_asset_operation_summary(asset_name: str, days: int = 30) -> dict:
    """Tổng hợp vận hành thiết bị trong N ngày qua."""
    return _handle(svc.get_asset_operation_summary, asset_name, int(days))


@frappe.whitelist()
def get_dashboard_stats(dept: str = "") -> dict:
    """Tổng quan trạng thái thiết bị hôm nay theo khoa."""
    return _handle(svc.get_dashboard_stats, dept or None)


# ─── Write Endpoints ──────────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def create_daily_log(
    asset: str,
    log_date: str,
    shift: str,
    operated_by: str,
    operational_status: str,
    start_meter_hours: float = 0.0,
    end_meter_hours: float = 0.0,
    usage_cycles: int = 0,
    anomaly_detected: int = 0,
    anomaly_type: str = "None",
    anomaly_description: str = "",
) -> dict:
    """Tạo nhật ký ca vận hành mới."""
    return _handle(
        svc.create_daily_log,
        asset, log_date, shift, operated_by, operational_status,
        float(start_meter_hours), float(end_meter_hours),
        int(usage_cycles), int(anomaly_detected),
        anomaly_type, anomaly_description,
    )


@frappe.whitelist(methods=["POST"])
def submit_log(name: str) -> dict:
    """Nộp nhật ký ca (Open → Logged)."""
    return _handle(svc.submit_log, name)


@frappe.whitelist(methods=["POST"])
def review_log(name: str, reviewer_notes: str = "") -> dict:
    """Phê duyệt nhật ký ca bởi Trưởng khoa / HTM Technician."""
    return _handle(svc.review_log, name, reviewer_notes)


@frappe.whitelist(methods=["POST"])
def report_anomaly_from_log(
    log_name: str,
    severity: str,
    description: str,
) -> dict:
    """Tạo Incident Report thủ công từ nhật ký ca."""
    return _handle(svc.report_anomaly_from_log, log_name, severity, description)
