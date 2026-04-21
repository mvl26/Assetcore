# Copyright (c) 2026, AssetCore Team
"""Unified dashboard overview across all IMM modules.

Trả về tổng hợp KPI, phân bổ trạng thái, và các danh sách gần đây cho toàn bộ
lifecycle HTM (IMM-00, 04, 05, 08, 09, 11) — phục vụ trang /dashboard.
"""
import frappe
from frappe.utils import today, add_days, now_datetime

from assetcore.utils.response import _ok, _err

# ─── Shared constants ────────────────────────────────────────────────────────
_DT_ASSET = "AC Asset"
_DT_COMM = "Asset Commissioning"
_STATUS_UNDER_REPAIR = "Under Repair"
_STATUS_OUT_OF_SERVICE = "Out of Service"
_OP_NOT_IN = "not in"


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
        assets_total = _count(_DT_ASSET)
        assets_active = _count(_DT_ASSET, {"lifecycle_status": "Active"})
        assets_repair = _count(_DT_ASSET, {"lifecycle_status": _STATUS_UNDER_REPAIR})
        assets_calibrating = _count(_DT_ASSET, {"lifecycle_status": "Calibrating"})
        assets_out = _count(_DT_ASSET, {"lifecycle_status": _STATUS_OUT_OF_SERVICE})
        assets_decommissioned = _count(_DT_ASSET, {"lifecycle_status": "Decommissioned"})
        assets_byt_expiring = _count(_DT_ASSET, {"byt_reg_expiry": ["between", [today_str, next30]]})
        assets_byt_expired = _count(_DT_ASSET, {"byt_reg_expiry": ["<", today_str]})

        # ── IMM-04: Tiếp nhận ─────────────────────────────────────────────────
        comm_pending = _count(_DT_COMM, {"workflow_state": [_OP_NOT_IN, ["Clinical_Release", "Return_To_Vendor"]], "docstatus": ["!=", 2]})
        comm_released = _count(_DT_COMM, {"workflow_state": "Clinical_Release"})
        comm_hold = _count(_DT_COMM, {"workflow_state": "Clinical_Hold"})
        comm_open_nc = _count("Asset QA Non Conformance", {"status": ["!=", "Closed"]})

        # ── IMM-05: Hồ sơ ────────────────────────────────────────────────────
        doc_total = _count("Asset Document")
        doc_expiring = _count("Asset Document", {"expiry_date": ["between", [today_str, next30]]})
        doc_expired = _count("Asset Document", {"expiry_date": ["<", today_str]})
        doc_requests_open = _count("Document Request", {"status": [_OP_NOT_IN, ["Closed", "Fulfilled"]]})

        # ── IMM-08: PM ────────────────────────────────────────────────────────
        pm_open = _count("PM Work Order", {"status": [_OP_NOT_IN, ["Completed", "Cancelled"]]})
        pm_overdue = _count("PM Work Order", {"status": [_OP_NOT_IN, ["Completed", "Cancelled"]], "due_date": ["<", today_str]})
        pm_due_next7 = _count("PM Work Order", {"status": [_OP_NOT_IN, ["Completed", "Cancelled"]], "due_date": ["between", [today_str, next7]]})
        pm_completed_30d = _count("PM Work Order", {"status": "Completed", "completion_date": [">=", add_days(today_str, -30)]})

        # ── IMM-09: CM / Sửa chữa ────────────────────────────────────────────
        cm_open = _count("Asset Repair", {"status": [_OP_NOT_IN, ["Completed", "Closed", "Cancelled"]]})
        cm_sla_breached = _count("Asset Repair", {"sla_breached": 1, "status": [_OP_NOT_IN, ["Completed", "Closed"]]})
        cm_repeat_failure = _count("Asset Repair", {"is_repeat_failure": 1})
        cm_completed_30d = _count("Asset Repair", {"status": "Completed", "completion_datetime": [">=", add_days(today_str, -30)]})

        # ── IMM-11: Hiệu chuẩn ───────────────────────────────────────────────
        calib_due = _count("IMM Calibration Schedule", {"next_calibration_date": ["between", [today_str, next30]]})
        calib_overdue = _count("IMM Calibration Schedule", {"next_calibration_date": ["<", today_str]})

        # ── Incident / CAPA ──────────────────────────────────────────────────
        incidents_open = _count("Incident Report", {"status": [_OP_NOT_IN, ["Closed", "Resolved"]]})
        incidents_critical = _count("Incident Report", {"severity": "Critical", "status": [_OP_NOT_IN, ["Closed", "Resolved"]]})
        capa_open = _count("IMM CAPA Record", {"status": [_OP_NOT_IN, ["Closed"]]})
        capa_overdue = _count("IMM CAPA Record", {"status": [_OP_NOT_IN, ["Closed"]], "due_date": ["<", today_str]})

        # ── Phân bổ lifecycle cho biểu đồ ──────────────────────────────────
        lifecycle_breakdown = [
            {"state": "Commissioned", "count": _count(_DT_ASSET, {"lifecycle_status": "Commissioned"})},
            {"state": "Active", "count": assets_active},
            {"state": _STATUS_UNDER_REPAIR, "count": assets_repair},
            {"state": "Calibrating", "count": assets_calibrating},
            {"state": _STATUS_OUT_OF_SERVICE, "count": assets_out},
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
            amap = {a.name: a.asset_name for a in frappe.get_all(_DT_ASSET, filters={"name": ["in", list(asset_ids)]}, fields=["name", "asset_name"])}
            for r in recent_incidents:
                r["asset_name"] = amap.get(r.get("asset"), r.get("asset") or "")

        recent_pm = _recent(
            "PM Work Order",
            ["name", "asset_ref", "pm_type", "status", "due_date", "is_late"],
            limit=5, order_by="due_date asc",
            filters={"status": [_OP_NOT_IN, ["Completed", "Cancelled"]]},
        )
        pm_asset_ids = {r.get("asset_ref") for r in recent_pm if r.get("asset_ref")}
        if pm_asset_ids:
            amap = {a.name: a.asset_name for a in frappe.get_all(_DT_ASSET, filters={"name": ["in", list(pm_asset_ids)]}, fields=["name", "asset_name"])}
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


# ─────────────────────────────────────────────────────────────────────────────
# HTM Command Center — API gộp 4 phần cho trang /dashboard (v2)
# ─────────────────────────────────────────────────────────────────────────────

_STATUS_LABELS_VI = {
    "Active": "Đang hoạt động",
    _STATUS_UNDER_REPAIR: "Đang sửa chữa",
    "Under Maintenance": "Đang bảo trì",
    "Calibrating": "Đang hiệu chuẩn",
    _STATUS_OUT_OF_SERVICE: "Ngừng hoạt động",
    "Commissioned": "Mới tiếp nhận",
    "Decommissioned": "Đã thanh lý",
}

_STATUS_COLORS = {
    "Đang hoạt động":    "#10b981",
    "Đang sửa chữa":     "#ef4444",
    "Đang bảo trì":      "#f59e0b",
    "Đang hiệu chuẩn":   "#8b5cf6",
    "Ngừng hoạt động":   "#64748b",
    "Mới tiếp nhận":     "#3b82f6",
    "Đã thanh lý":       "#94a3b8",
}


@frappe.whitelist()
def get_dashboard_data() -> dict:
    """GET /api/method/assetcore.api.dashboard.get_dashboard_data

    Trả về payload gộp 4 phần: KPI cards, donut chart, upcoming maintenance,
    active repairs — phục vụ trang HTM Command Center.
    """
    try:
        today_str = today()
        next30 = add_days(today_str, 30)

        # ── 1. KPI Metrics ────────────────────────────────────────────────────
        kpi_metrics = {
            "total_assets":        _count(_DT_ASSET, {"docstatus": ["!=", 2]}),
            "under_repair":        _count(_DT_ASSET, {"lifecycle_status": _STATUS_UNDER_REPAIR}),
            "under_maintenance":   _count(_DT_ASSET, {"lifecycle_status": "Under Maintenance"}),
            "pending_commissioning": _count(
                _DT_COMM,
                {
                    "workflow_state": [_OP_NOT_IN, ["Clinical Release", "Return To Vendor", "Clinical_Release", "Return_To_Vendor"]],
                    "docstatus": ["!=", 2],
                },
            ),
        }

        # ── 2. Donut chart: phân bổ trạng thái ───────────────────────────────
        status_rows = frappe.db.sql(
            """
            SELECT COALESCE(lifecycle_status, 'Chưa xác định') AS status, COUNT(*) AS cnt
            FROM `tabAC Asset`
            WHERE docstatus != 2
            GROUP BY lifecycle_status
            ORDER BY cnt DESC
            """,
            as_dict=True,
        ) or []
        labels, series, colors = [], [], []
        for row in status_rows:
            label = _STATUS_LABELS_VI.get(row["status"], row["status"])
            labels.append(label)
            series.append(int(row["cnt"] or 0))
            colors.append(_STATUS_COLORS.get(label, "#94a3b8"))
        asset_status_chart = {"labels": labels, "series": series, "colors": colors}

        # ── 3. Upcoming maintenance (PM + Calibration, ≤30 ngày) ────────────
        upcoming_rows = frappe.db.sql(
            """
            (SELECT s.asset_ref AS asset, a.asset_name, a.department,
                    s.next_due_date AS due_date, 'PM' AS kind, s.pm_type AS detail
             FROM `tabPM Schedule` s
             JOIN `tabAC Asset` a ON a.name = s.asset_ref
             WHERE s.status = 'Active'
               AND s.next_due_date BETWEEN %(today)s AND %(next30)s)
            UNION ALL
            (SELECT c.asset AS asset, a.asset_name, a.department,
                    c.next_due_date AS due_date, 'Hiệu chuẩn' AS kind, c.calibration_type AS detail
             FROM `tabIMM Calibration Schedule` c
             JOIN `tabAC Asset` a ON a.name = c.asset
             WHERE c.is_active = 1
               AND c.next_due_date BETWEEN %(today)s AND %(next30)s)
            ORDER BY due_date ASC
            LIMIT 10
            """,
            {"today": today_str, "next30": next30},
            as_dict=True,
        ) or []
        for r in upcoming_rows:
            d = r.get("due_date")
            r["due_date"] = str(d) if d else ""
            r["days_until"] = (d - frappe.utils.getdate(today_str)).days if d else None

        # ── 4. Active repairs (đang sửa chữa) ──────────────────────────────
        repair_rows = frappe.db.sql(
            """
            SELECT r.name, r.asset_ref AS asset, a.asset_name, a.department,
                   r.status, r.priority, r.open_datetime,
                   TIMESTAMPDIFF(DAY, r.open_datetime, NOW()) AS downtime_days
            FROM `tabAsset Repair` r
            LEFT JOIN `tabAC Asset` a ON a.name = r.asset_ref
            WHERE r.status NOT IN ('Completed', 'Closed', 'Cancelled', 'Cannot Repair')
            ORDER BY r.open_datetime ASC
            LIMIT 20
            """,
            as_dict=True,
        ) or []
        for r in repair_rows:
            r["open_datetime"] = str(r["open_datetime"]) if r.get("open_datetime") else ""
            r["downtime_days"] = int(r["downtime_days"] or 0)

        return _ok({
            "generated_at":        str(now_datetime()),
            "kpi_metrics":         kpi_metrics,
            "asset_status_chart":  asset_status_chart,
            "upcoming_maintenance": upcoming_rows,
            "active_repairs":      repair_rows,
        })
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "get_dashboard_data error")
        return _err(str(e))
