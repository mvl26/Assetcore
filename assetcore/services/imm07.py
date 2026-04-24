# Copyright (c) 2026, AssetCore Team
# Service layer cho Module IMM-07 — Vận hành hàng ngày.
# Controller gọi vào đây; không có business logic trong controller.

from __future__ import annotations

import math

import frappe
from frappe import _
from frappe.utils import nowdate, now_datetime, getdate


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def _paginate(doctype: str, filters: dict, fields: list[str],
              page: int, page_size: int) -> dict:
    """Generic paginated query helper."""
    total = frappe.db.count(doctype, filters)
    items = frappe.db.get_all(
        doctype,
        filters=filters,
        fields=fields,
        limit_page_length=page_size,
        limit_start=(page - 1) * page_size,
        order_by="log_date desc, shift asc",
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, math.ceil(total / page_size)),
    }


# ─── READ ─────────────────────────────────────────────────────────────────────

def get_daily_log(name: str) -> dict:
    """Return Daily Operation Log detail.

    Args:
        name: Daily Operation Log name.

    Returns:
        dict: Log document as dict.
    """
    doc = frappe.get_doc("Daily Operation Log", name)
    return doc.as_dict()


def list_daily_logs(
    asset: str | None = None,
    dept: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    operational_status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List Daily Operation Logs with filters and pagination.

    Args:
        asset: Filter by asset.
        dept: Filter by department.
        date_from: Start date YYYY-MM-DD.
        date_to: End date YYYY-MM-DD.
        operational_status: Filter by status.
        page: Page number.
        page_size: Items per page.

    Returns:
        dict: Paginated result.
    """
    filters: dict = {"docstatus": ("!=", 2)}
    if asset:
        filters["asset"] = asset
    if dept:
        filters["dept"] = dept
    if date_from and date_to:
        filters["log_date"] = ["between", [date_from, date_to]]
    elif date_from:
        filters["log_date"] = [">=", date_from]
    elif date_to:
        filters["log_date"] = ["<=", date_to]
    if operational_status:
        filters["operational_status"] = operational_status

    fields = ["name", "asset", "log_date", "shift", "operated_by",
              "operational_status", "runtime_hours", "anomaly_detected",
              "anomaly_type", "workflow_state", "modified"]
    return _paginate("Daily Operation Log", filters, fields, int(page), int(page_size))


def get_asset_operation_summary(asset_name: str, days: int = 30) -> dict:
    """Return operational summary for an asset over the past N days.

    Args:
        asset_name: AC Asset name.
        days: Number of days to look back.

    Returns:
        dict: Summary stats including runtime, uptime, anomaly counts.
    """
    from_date = frappe.utils.add_days(nowdate(), -int(days))

    rows = frappe.db.get_all(
        "Daily Operation Log",
        filters={
            "asset": asset_name,
            "log_date": [">=", from_date],
            "docstatus": ("!=", 2),
        },
        fields=["log_date", "shift", "operational_status",
                "runtime_hours", "anomaly_detected", "anomaly_type"],
    )

    total_runtime = sum(r.runtime_hours or 0 for r in rows)
    anomaly_count = sum(1 for r in rows if r.anomaly_detected)
    fault_days = len(set(r.log_date for r in rows if r.operational_status == "Fault"))
    running_days = len(set(r.log_date for r in rows if r.operational_status == "Running"))
    uptime_pct = round((running_days / max(1, int(days))) * 100, 1)

    by_shift: dict[str, float] = {}
    status_breakdown: dict[str, int] = {}
    for r in rows:
        by_shift[r.shift] = round(by_shift.get(r.shift, 0) + (r.runtime_hours or 0), 2)
        status_breakdown[r.operational_status] = status_breakdown.get(r.operational_status, 0) + 1

    return {
        "asset": asset_name,
        "period_days": days,
        "total_runtime_hours": round(total_runtime, 2),
        "uptime_pct": uptime_pct,
        "anomaly_count": anomaly_count,
        "fault_days": fault_days,
        "by_shift": by_shift,
        "status_breakdown": status_breakdown,
    }


def get_dashboard_stats(dept: str | None = None) -> dict:
    """Return today's operational status summary for dashboard.

    Args:
        dept: Optional AC Department filter.

    Returns:
        dict: Counts by operational status + runtime total.
    """
    today = nowdate()
    filters: dict = {
        "log_date": today,
        "docstatus": ("!=", 2),
    }
    if dept:
        filters["dept"] = dept

    rows = frappe.db.get_all(
        "Daily Operation Log",
        filters=filters,
        fields=["asset", "operational_status", "runtime_hours", "anomaly_detected"],
    )

    counts: dict[str, int] = {
        "Running": 0, "Standby": 0, "Fault": 0,
        "Under Maintenance": 0, "Not Used": 0,
    }
    total_runtime = 0.0
    anomaly_today = 0
    assets_by_status = []

    for r in rows:
        status = r.operational_status or "Not Used"
        counts[status] = counts.get(status, 0) + 1
        total_runtime += r.runtime_hours or 0
        if r.anomaly_detected:
            anomaly_today += 1
        asset_name = frappe.db.get_value("AC Asset", r.asset, "asset_name") or r.asset
        assets_by_status.append({
            "asset": r.asset,
            "name": asset_name,
            "status": status,
        })

    return {
        "date": today,
        "dept": dept or "all",
        "total_assets": len(rows),
        "running": counts["Running"],
        "standby": counts["Standby"],
        "fault": counts["Fault"],
        "under_maintenance": counts["Under Maintenance"],
        "not_used": counts["Not Used"],
        "total_runtime_hours_today": round(total_runtime, 2),
        "anomaly_count_today": anomaly_today,
        "assets_by_status": assets_by_status,
    }


# ─── WRITE ───────────────────────────────────────────────────────────────────

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
    """Create a new Daily Operation Log.

    Args:
        asset: AC Asset name.
        log_date: Date string YYYY-MM-DD.
        shift: Morning 06-14 / Afternoon 14-22 / Night 22-06.
        operated_by: User email.
        operational_status: Running/Standby/Fault/Under Maintenance/Not Used.
        start_meter_hours: Meter reading at start of shift.
        end_meter_hours: Meter reading at end of shift.
        usage_cycles: Number of usage cycles.
        anomaly_detected: 1 if anomaly present.
        anomaly_type: None/Minor/Major/Critical.
        anomaly_description: Description of anomaly.

    Returns:
        dict: Created log fields.
    """
    doc = frappe.get_doc({
        "doctype": "Daily Operation Log",
        "asset": asset,
        "log_date": log_date,
        "shift": shift,
        "operated_by": operated_by,
        "operational_status": operational_status,
        "start_meter_hours": float(start_meter_hours),
        "end_meter_hours": float(end_meter_hours),
        "usage_cycles": int(usage_cycles),
        "anomaly_detected": int(anomaly_detected),
        "anomaly_type": anomaly_type if anomaly_detected else "None",
        "anomaly_description": anomaly_description,
    })
    doc.insert(ignore_permissions=False)
    return {
        "name": doc.name,
        "asset": doc.asset,
        "log_date": str(doc.log_date),
        "shift": doc.shift,
        "operational_status": doc.operational_status,
        "runtime_hours": doc.runtime_hours,
        "workflow_state": doc.workflow_state,
    }


def submit_log(name: str) -> dict:
    """Submit a Daily Operation Log (Open → Logged).

    Args:
        name: Daily Operation Log name.

    Returns:
        dict: Updated record info.
    """
    doc = frappe.get_doc("Daily Operation Log", name)
    doc.submit()
    return {
        "name": doc.name,
        "workflow_state": doc.workflow_state,
        "docstatus": doc.docstatus,
        "linked_incident": doc.linked_incident,
    }


def review_log(name: str, reviewer_notes: str = "") -> dict:
    """Mark a Daily Operation Log as Reviewed.

    Args:
        name: Daily Operation Log name.
        reviewer_notes: Optional review notes.

    Returns:
        dict: Updated record info.
    """
    doc = frappe.get_doc("Daily Operation Log", name)
    doc.reviewed_by = frappe.session.user
    doc.review_date = nowdate()
    if reviewer_notes:
        # Append reviewer notes to anomaly_description if available
        doc.anomaly_description = (doc.anomaly_description or "") + (
            f"\n[Review] {reviewer_notes}" if reviewer_notes else ""
        )
    doc.workflow_state = "Reviewed"
    doc.save(ignore_permissions=False)
    doc.submit()
    return {
        "name": doc.name,
        "workflow_state": "Reviewed",
        "docstatus": doc.docstatus,
        "reviewed_by": doc.reviewed_by,
        "review_date": str(doc.review_date),
    }


def report_anomaly_from_log(
    log_name: str,
    severity: str,
    description: str,
) -> dict:
    """Create an Incident Report from a Daily Operation Log anomaly.

    Args:
        log_name: Daily Operation Log name.
        severity: Minor / Major / Critical.
        description: Anomaly description.

    Returns:
        dict: Created incident reference.
    """
    if not frappe.db.table_exists("Incident Report"):
        frappe.throw(_("Module Báo cáo Sự cố chưa được triển khai."))

    log = frappe.get_doc("Daily Operation Log", log_name)
    incident = frappe.get_doc({
        "doctype": "Incident Report",
        "asset": log.asset,
        "reported_by": frappe.session.user,
        "report_date": log.log_date,
        "severity": severity,
        "description": description,
        "source_module": "IMM-07",
        "source_log": log_name,
    })
    incident.insert(ignore_permissions=False)

    # Update log's linked_incident
    log.db_set("linked_incident", incident.name, commit=True)

    return {
        "incident": incident.name,
        "log": log_name,
        "severity": severity,
    }
