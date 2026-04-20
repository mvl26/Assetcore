# Copyright (c) 2026, AssetCore Team
"""Unified dashboard overview across all IMM modules.

Trả về tổng hợp KPI, phân bổ trạng thái, và các danh sách gần đây cho toàn bộ
lifecycle HTM (IMM-00, 04, 05, 08, 09, 11) — phục vụ trang /dashboard.
"""
import frappe
from frappe.utils import today, add_days, now_datetime

from assetcore.utils.response import _ok, _err


def _count(doctype: str, filters: dict = None) -> int:
    try:
        return frappe.db.count(doctype, filters=filters or {})
    except Exception:
        return 0


def _recent(doctype: str, fields: list[str], limit: int = 5, order_by: str = "modified desc", filters: dict = None) -> list[dict]:
    try:
        return frappe.get_all(doctype, filters=filters or {}, fields=fields, limit=limit, order_by=order_by) or []
    except Exception:
        return []


def _status_breakdown(doctype: str, status_field: str, values: list[str]) -> list[dict]:
    out = []
    for v in values:
        out.append({"state": v, "count": _count(doctype, {status_field: v})})
    return out


@frappe.whitelist()
def get_overview() -> dict:
    """GET /api/method/assetcore.api.dashboard.get_overview — Tổng quan toàn hệ thống."""
    try:
        today_str = today()
        next7 = add_days(today_str, 7)
        next30 = add_days(today_str, 30)

        # ── IMM-00: Thiết bị ─────────────────────────────────────────────────
        assets_total = _count("AC Asset")
        assets_active = _count("AC Asset", {"lifecycle_status": "Active"})
        assets_repair = _count("AC Asset", {"lifecycle_status": "Under Repair"})
        assets_calibrating = _count("AC Asset", {"lifecycle_status": "Calibrating"})
        assets_out = _count("AC Asset", {"lifecycle_status": "Out of Service"})
        assets_decommissioned = _count("AC Asset", {"lifecycle_status": "Decommissioned"})
        assets_byt_expiring = _count("AC Asset", {"byt_reg_expiry": ["between", [today_str, next30]]})
        assets_byt_expired = _count("AC Asset", {"byt_reg_expiry": ["<", today_str]})

        # ── IMM-04: Tiếp nhận ─────────────────────────────────────────────────
        comm_pending = _count("Asset Commissioning", {"workflow_state": ["not in", ["Clinical_Release", "Return_To_Vendor"]], "docstatus": ["!=", 2]})
        comm_released = _count("Asset Commissioning", {"workflow_state": "Clinical_Release"})
        comm_hold = _count("Asset Commissioning", {"workflow_state": "Clinical_Hold"})
        comm_open_nc = _count("Asset QA Non Conformance", {"status": ["!=", "Closed"]})

        # ── IMM-05: Hồ sơ ────────────────────────────────────────────────────
        doc_total = _count("Asset Document")
        doc_expiring = _count("Asset Document", {"expiry_date": ["between", [today_str, next30]]})
        doc_expired = _count("Asset Document", {"expiry_date": ["<", today_str]})
        doc_requests_open = _count("Document Request", {"status": ["not in", ["Closed", "Fulfilled"]]})

        # ── IMM-08: PM ────────────────────────────────────────────────────────
        pm_open = _count("PM Work Order", {"status": ["not in", ["Completed", "Cancelled"]]})
        pm_overdue = _count("PM Work Order", {"status": ["not in", ["Completed", "Cancelled"]], "due_date": ["<", today_str]})
        pm_due_next7 = _count("PM Work Order", {"status": ["not in", ["Completed", "Cancelled"]], "due_date": ["between", [today_str, next7]]})
        pm_completed_30d = _count("PM Work Order", {"status": "Completed", "completion_date": [">=", add_days(today_str, -30)]})

        # ── IMM-09: CM / Sửa chữa ────────────────────────────────────────────
        cm_open = _count("Asset Repair", {"status": ["not in", ["Completed", "Closed", "Cancelled"]]})
        cm_sla_breached = _count("Asset Repair", {"sla_breached": 1, "status": ["not in", ["Completed", "Closed"]]})
        cm_repeat_failure = _count("Asset Repair", {"is_repeat_failure": 1})
        cm_completed_30d = _count("Asset Repair", {"status": "Completed", "completion_datetime": [">=", add_days(today_str, -30)]})

        # ── IMM-11: Hiệu chuẩn ───────────────────────────────────────────────
        calib_due = _count("IMM Calibration Schedule", {"next_calibration_date": ["between", [today_str, next30]]})
        calib_overdue = _count("IMM Calibration Schedule", {"next_calibration_date": ["<", today_str]})

        # ── Incident / CAPA ──────────────────────────────────────────────────
        incidents_open = _count("Incident Report", {"status": ["not in", ["Closed", "Resolved"]]})
        incidents_critical = _count("Incident Report", {"severity": "Critical", "status": ["not in", ["Closed", "Resolved"]]})
        capa_open = _count("IMM CAPA Record", {"status": ["not in", ["Closed"]]})
        capa_overdue = _count("IMM CAPA Record", {"status": ["not in", ["Closed"]], "due_date": ["<", today_str]})

        # ── Phân bổ lifecycle cho biểu đồ ──────────────────────────────────
        lifecycle_breakdown = [
            {"state": "Commissioned", "count": _count("AC Asset", {"lifecycle_status": "Commissioned"})},
            {"state": "Active", "count": assets_active},
            {"state": "Under Repair", "count": assets_repair},
            {"state": "Calibrating", "count": assets_calibrating},
            {"state": "Out of Service", "count": assets_out},
            {"state": "Decommissioned", "count": assets_decommissioned},
        ]

        # ── Các danh sách gần đây ────────────────────────────────────────────
        recent_incidents = _recent(
            "Incident Report",
            ["name", "asset", "severity", "status", "description", "reported_at"],
            limit=5, order_by="reported_at desc",
        )
        asset_ids = {r.get("asset") for r in recent_incidents if r.get("asset")}
        if asset_ids:
            amap = {a.name: a.asset_name for a in frappe.get_all("AC Asset", filters={"name": ["in", list(asset_ids)]}, fields=["name", "asset_name"])}
            for r in recent_incidents:
                r["asset_name"] = amap.get(r.get("asset"), r.get("asset") or "")

        recent_pm = _recent(
            "PM Work Order",
            ["name", "asset_ref", "pm_type", "status", "due_date", "is_late"],
            limit=5, order_by="due_date asc",
            filters={"status": ["not in", ["Completed", "Cancelled"]]},
        )
        pm_asset_ids = {r.get("asset_ref") for r in recent_pm if r.get("asset_ref")}
        if pm_asset_ids:
            amap = {a.name: a.asset_name for a in frappe.get_all("AC Asset", filters={"name": ["in", list(pm_asset_ids)]}, fields=["name", "asset_name"])}
            for r in recent_pm:
                r["asset_name"] = amap.get(r.get("asset_ref"), r.get("asset_ref") or "")

        return _ok({
            "generated_at": str(now_datetime()),
            "assets": {
                "total": assets_total,
                "active": assets_active,
                "under_repair": assets_repair,
                "calibrating": assets_calibrating,
                "out_of_service": assets_out,
                "decommissioned": assets_decommissioned,
                "byt_expiring_30d": assets_byt_expiring,
                "byt_expired": assets_byt_expired,
            },
            "commissioning": {
                "pending": comm_pending,
                "released": comm_released,
                "hold": comm_hold,
                "open_nc": comm_open_nc,
            },
            "documents": {
                "total": doc_total,
                "expiring_30d": doc_expiring,
                "expired": doc_expired,
                "requests_open": doc_requests_open,
            },
            "pm": {
                "open": pm_open,
                "overdue": pm_overdue,
                "due_next_7d": pm_due_next7,
                "completed_30d": pm_completed_30d,
            },
            "cm": {
                "open": cm_open,
                "sla_breached": cm_sla_breached,
                "repeat_failure": cm_repeat_failure,
                "completed_30d": cm_completed_30d,
            },
            "calibration": {
                "due_30d": calib_due,
                "overdue": calib_overdue,
            },
            "incidents": {
                "open": incidents_open,
                "critical_open": incidents_critical,
            },
            "capa": {
                "open": capa_open,
                "overdue": capa_overdue,
            },
            "lifecycle_breakdown": lifecycle_breakdown,
            "recent_incidents": recent_incidents,
            "recent_pm": recent_pm,
        })
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Dashboard get_overview error")
        return _err(str(e))
