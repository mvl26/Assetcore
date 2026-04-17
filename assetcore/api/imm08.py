# Copyright (c) 2026, AssetCore Team and contributors
# REST API cho Module IMM-08 — Preventive Maintenance

import json
from math import ceil
import frappe
from frappe import _
from frappe.utils import nowdate, add_days, date_diff, getdate


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

_DOCTYPE_WO = "PM Work Order"
_DOCTYPE_SCHED = "PM Schedule"
_DOCTYPE_LOG = "PM Task Log"
_DOCTYPE_TPL = "PM Checklist Template"

_ROLE_WORKSHOP = "Workshop Head"
_ROLE_KTV = "HTM Technician"
_ROLE_PTP = "VP Block2"
_ROLE_ADMIN = "CMMS Admin"


def _ok(data: dict | list) -> dict:
    return {"success": True, "data": data}


def _err(message: str, code: str = "GENERIC_ERROR") -> dict:
    return {"success": False, "error": message, "code": code}


def _get_role_emails(roles: list[str]) -> list[str]:
    emails = []
    for role in roles:
        users = frappe.db.get_all("Has Role", filters={"role": role, "parenttype": "User"}, fields=["parent"])
        for u in users:
            email = frappe.db.get_value("User", u.parent, "email")
            if email and email not in emails:
                emails.append(email)
    return emails


# ─────────────────────────────────────────────────────────────────────────────
# 1. LIST PM WORK ORDERS
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_pm_work_orders(filters: str = "{}", page: int = 1, page_size: int = 20) -> dict:
    """
    Danh sách PM Work Order với phân trang.
    GET /api/method/assetcore.api.imm08.list_pm_work_orders
    """
    try:
        page = int(page)
        page_size = int(page_size)
        parsed = json.loads(filters) if isinstance(filters, str) else filters
    except (ValueError, json.JSONDecodeError) as e:
        return _err(f"Tham số không hợp lệ: {e}", "INVALID_PARAMS")

    total = frappe.db.count(_DOCTYPE_WO, filters=parsed)
    rows = frappe.db.get_all(
        _DOCTYPE_WO,
        filters=parsed,
        fields=[
            "name", "asset_ref", "pm_type", "wo_type", "status",
            "due_date", "completion_date", "assigned_to",
            "overall_result", "is_late", "source_pm_wo",
        ],
        order_by="due_date asc",
        limit=page_size,
        start=(page - 1) * page_size,
    )

    # Enrich với asset_name
    for row in rows:
        row["asset_name"] = frappe.db.get_value("Asset", row["asset_ref"], "asset_name") or ""

    return _ok({
        "data": rows,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": ceil(total / page_size) if total else 0,
        },
    })


# ─────────────────────────────────────────────────────────────────────────────
# 2. GET PM WORK ORDER DETAIL
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_pm_work_order(name: str) -> dict:
    """
    Chi tiết PM Work Order kèm checklist items.
    GET /api/method/assetcore.api.imm08.get_pm_work_order
    """
    try:
        wo = frappe.get_doc(_DOCTYPE_WO, name)
    except frappe.DoesNotExistError:
        return _err(f"PM Work Order '{name}' không tồn tại", "NOT_FOUND")

    asset = frappe.db.get_value(
        "Asset", wo.asset_ref,
        ["asset_name", "asset_category", "custom_risk_class", "location"],
        as_dict=True,
    ) or {}

    checklist = []
    for r in (wo.checklist_results or []):
        checklist.append({
            "idx": r.idx,
            "checklist_item_idx": r.checklist_item_idx,
            "description": r.description,
            "measurement_type": r.measurement_type,
            "unit": r.unit,
            "result": r.result,
            "measured_value": r.measured_value,
            "notes": r.notes,
            "photo": r.photo,
        })

    return _ok({
        "name": wo.name,
        "asset_ref": wo.asset_ref,
        "asset_name": asset.get("asset_name", ""),
        "asset_category": asset.get("asset_category", ""),
        "risk_class": asset.get("custom_risk_class", ""),
        "pm_type": wo.pm_type,
        "wo_type": wo.wo_type,
        "status": wo.status,
        "due_date": str(wo.due_date) if wo.due_date else None,
        "scheduled_date": str(wo.scheduled_date) if wo.scheduled_date else None,
        "completion_date": str(wo.completion_date) if wo.completion_date else None,
        "assigned_to": wo.assigned_to,
        "overall_result": wo.overall_result,
        "technician_notes": wo.technician_notes,
        "pm_sticker_attached": bool(wo.pm_sticker_attached),
        "is_late": bool(wo.is_late),
        "duration_minutes": wo.duration_minutes,
        "source_pm_wo": wo.source_pm_wo,
        "checklist_results": checklist,
    })


# ─────────────────────────────────────────────────────────────────────────────
# 3. ASSIGN TECHNICIAN
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def assign_technician(name: str, technician: str, scheduled_date: str = None) -> dict:
    """
    Phân công KTV thực hiện PM WO.
    POST /api/method/assetcore.api.imm08.assign_technician
    """
    try:
        wo = frappe.get_doc(_DOCTYPE_WO, name)
    except frappe.DoesNotExistError:
        return _err(f"PM Work Order '{name}' không tồn tại", "NOT_FOUND")

    if wo.status not in ("Open", "Overdue"):
        return _err(f"Không thể phân công khi WO ở trạng thái '{wo.status}'", "INVALID_STATE")

    wo.assigned_to = technician
    wo.assigned_by = frappe.session.user
    if scheduled_date:
        wo.scheduled_date = scheduled_date
    wo.status = "In Progress"
    wo.save(ignore_permissions=True)

    return _ok({"name": wo.name, "status": wo.status, "assigned_to": wo.assigned_to})


# ─────────────────────────────────────────────────────────────────────────────
# 4. SUBMIT PM RESULT
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def submit_pm_result(
    name: str,
    checklist_results: str = "[]",
    overall_result: str = "Pass",
    technician_notes: str = "",
    pm_sticker_attached: int = 0,
    duration_minutes: int = 0,
) -> dict:
    """
    KTV nộp kết quả PM — submit WO.
    POST /api/method/assetcore.api.imm08.submit_pm_result
    """
    try:
        results = json.loads(checklist_results) if isinstance(checklist_results, str) else checklist_results
    except json.JSONDecodeError:
        return _err("checklist_results không hợp lệ", "INVALID_PARAMS")

    try:
        wo = frappe.get_doc(_DOCTYPE_WO, name)
    except frappe.DoesNotExistError:
        return _err(f"PM Work Order '{name}' không tồn tại", "NOT_FOUND")

    if wo.docstatus == 1:
        return _err("PM Work Order đã được Submit", "ALREADY_SUBMITTED")

    # Cập nhật checklist results
    result_map = {r["idx"]: r for r in results}
    for row in (wo.checklist_results or []):
        if row.idx in result_map:
            r = result_map[row.idx]
            row.result = r.get("result")
            row.measured_value = r.get("measured_value")
            row.notes = r.get("notes", "")

    wo.overall_result = overall_result
    wo.technician_notes = technician_notes
    wo.pm_sticker_attached = pm_sticker_attached
    wo.duration_minutes = duration_minutes
    wo.status = "Completed"
    wo.completion_date = nowdate()
    wo.save(ignore_permissions=True)

    try:
        wo.submit()
    except Exception as e:
        return _err(str(e), "SUBMIT_ERROR")

    # Tính next_pm_date
    sched_interval = frappe.db.get_value(_DOCTYPE_SCHED, wo.pm_schedule, "pm_interval_days") or 0
    next_pm_date = add_days(nowdate(), sched_interval)

    # Check có tạo CM WO không
    cm_wo = frappe.db.get_value(
        _DOCTYPE_WO,
        {"source_pm_wo": name, "wo_type": "Corrective"},
        "name",
    )

    return _ok({
        "name": wo.name,
        "new_status": wo.status,
        "is_late": bool(wo.is_late),
        "next_pm_date": str(next_pm_date),
        "cm_wo_created": cm_wo,
    })


# ─────────────────────────────────────────────────────────────────────────────
# 5. REPORT MAJOR FAILURE
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def report_major_failure(pm_wo_name: str, failure_description: str, failed_item_indexes: str = "[]") -> dict:
    """
    Dừng PM và tạo CM WO khẩn khi phát hiện lỗi Major.
    POST /api/method/assetcore.api.imm08.report_major_failure
    """
    try:
        wo = frappe.get_doc(_DOCTYPE_WO, pm_wo_name)
    except frappe.DoesNotExistError:
        return _err(f"PM Work Order '{pm_wo_name}' không tồn tại", "NOT_FOUND")

    # Set asset Out of Service (BR-08-04)
    frappe.db.set_value("Asset", wo.asset_ref, "status", "Out of Service")
    frappe.db.set_value(_DOCTYPE_WO, pm_wo_name, "status", "Halted–Major Failure")

    # Tạo CM WO khẩn
    cm_wo = frappe.get_doc({
        "doctype": _DOCTYPE_WO,
        "asset_ref": wo.asset_ref,
        "pm_schedule": wo.pm_schedule,
        "pm_type": wo.pm_type,
        "wo_type": "Corrective",
        "source_pm_wo": pm_wo_name,
        "status": "Open",
        "due_date": nowdate(),
        "technician_notes": f"[MAJOR FAILURE] {failure_description}",
    })
    cm_wo.insert(ignore_permissions=True)

    # Alert recipients
    recipients = _get_role_emails([_ROLE_WORKSHOP, _ROLE_PTP])
    asset_name = frappe.db.get_value("Asset", wo.asset_ref, "asset_name") or wo.asset_ref
    if recipients:
        frappe.sendmail(
            recipients=recipients,
            subject=f"[KHẨN] Major Failure PM: {wo.name} — {asset_name}",
            message=f"""
            <p>⚠️ <strong>LỖI NGHIÊM TRỌNG</strong> phát hiện trong quá trình PM.</p>
            <ul>
                <li>PM WO: <a href="/app/pm-work-order/{wo.name}">{wo.name}</a></li>
                <li>Thiết bị: {asset_name} ({wo.asset_ref})</li>
                <li>Mô tả lỗi: {failure_description}</li>
                <li>CM WO khẩn: <a href="/app/pm-work-order/{cm_wo.name}">{cm_wo.name}</a></li>
            </ul>
            <p>Thiết bị đã được đặt về <strong>Out of Service</strong>.</p>
            """,
        )

    return _ok({
        "pm_wo": pm_wo_name,
        "new_status": "Halted–Major Failure",
        "cm_wo_created": cm_wo.name,
        "asset_status": "Out of Service",
    })


# ─────────────────────────────────────────────────────────────────────────────
# 6. GET PM CALENDAR
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_pm_calendar(year: int, month: int, asset_ref: str = None, technician: str = None) -> dict:
    """
    Lịch PM theo tháng cho Calendar View.
    GET /api/method/assetcore.api.imm08.get_pm_calendar
    """
    year, month = int(year), int(month)
    import calendar
    _, last_day = calendar.monthrange(year, month)
    start_date = f"{year:04d}-{month:02d}-01"
    end_date = f"{year:04d}-{month:02d}-{last_day:02d}"

    filters = {
        "due_date": ["between", [start_date, end_date]],
    }
    if asset_ref:
        filters["asset_ref"] = asset_ref
    if technician:
        filters["assigned_to"] = technician

    wos = frappe.db.get_all(
        _DOCTYPE_WO,
        filters=filters,
        fields=["name", "asset_ref", "pm_type", "due_date", "status", "assigned_to", "is_late"],
        order_by="due_date asc",
    )

    events = []
    for wo in wos:
        asset_name = frappe.db.get_value("Asset", wo["asset_ref"], "asset_name") or ""
        events.append({**wo, "asset_name": asset_name, "due_date": str(wo["due_date"])})

    total = len(events)
    completed = sum(1 for e in events if e["status"] == "Completed")
    overdue = sum(1 for e in events if e["status"] == "Overdue")

    return _ok({
        "month": f"{year:04d}-{month:02d}",
        "events": events,
        "summary": {
            "total": total,
            "completed": completed,
            "overdue": overdue,
            "pending": total - completed - overdue,
        },
    })


# ─────────────────────────────────────────────────────────────────────────────
# 7. GET PM DASHBOARD STATS
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_pm_dashboard_stats(year: int = None, month: int = None) -> dict:
    """
    KPI dashboard cho PTP / Workshop Manager.
    GET /api/method/assetcore.api.imm08.get_pm_dashboard_stats
    """
    today = getdate(nowdate())
    year = int(year) if year else today.year
    month = int(month) if month else today.month

    import calendar
    _, last_day = calendar.monthrange(year, month)
    start_date = f"{year:04d}-{month:02d}-01"
    end_date = f"{year:04d}-{month:02d}-{last_day:02d}"

    wos = frappe.db.get_all(
        _DOCTYPE_WO,
        filters={"due_date": ["between", [start_date, end_date]]},
        fields=["name", "status", "is_late", "completion_date", "due_date"],
    )

    total = len(wos)
    completed = [w for w in wos if w["status"] == "Completed"]
    on_time = [w for w in completed if not w["is_late"]]
    overdue = [w for w in wos if w["status"] == "Overdue"]
    late_days = [
        date_diff(str(w["completion_date"]), str(w["due_date"]))
        for w in completed if w["is_late"] and w["completion_date"]
    ]

    compliance_rate = round(len(on_time) / total * 100, 1) if total else 0.0
    avg_days_late = round(sum(late_days) / len(late_days), 1) if late_days else 0.0

    # Trend 6 tháng
    trend = []
    for i in range(5, -1, -1):
        m = month - i
        y = year
        while m <= 0:
            m += 12
            y -= 1
        _, ld = calendar.monthrange(y, m)
        s, e = f"{y:04d}-{m:02d}-01", f"{y:04d}-{m:02d}-{ld:02d}"
        month_wos = frappe.db.get_all(
            _DOCTYPE_WO,
            filters={"due_date": ["between", [s, e]]},
            fields=["status", "is_late"],
        )
        t = len(month_wos)
        c_on = sum(1 for w in month_wos if w["status"] == "Completed" and not w["is_late"])
        trend.append({
            "month": f"{y:04d}-{m:02d}",
            "total": t,
            "on_time": c_on,
            "rate": round(c_on / t * 100, 1) if t else 0.0,
        })

    return _ok({
        "kpis": {
            "compliance_rate_pct": compliance_rate,
            "total_scheduled": total,
            "completed_on_time": len(on_time),
            "overdue": len(overdue),
            "avg_days_late": avg_days_late,
        },
        "trend_6months": trend,
    })


# ─────────────────────────────────────────────────────────────────────────────
# 8. RESCHEDULE PM
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def reschedule_pm(name: str, new_date: str, reason: str) -> dict:
    """
    Workshop Manager hoãn lịch PM.
    POST /api/method/assetcore.api.imm08.reschedule_pm
    """
    if not reason or len(reason.strip()) < 5:
        return _err("Lý do hoãn lịch là bắt buộc (tối thiểu 5 ký tự)", "MISSING_REASON")

    try:
        wo = frappe.get_doc(_DOCTYPE_WO, name)
    except frappe.DoesNotExistError:
        return _err(f"PM Work Order '{name}' không tồn tại", "NOT_FOUND")

    old_date = str(wo.due_date)
    wo.due_date = new_date
    wo.status = "Pending–Device Busy"
    wo.technician_notes = (wo.technician_notes or "") + f"\n[Hoãn lịch {old_date} → {new_date}]: {reason}"
    wo.save(ignore_permissions=True)

    return _ok({"name": wo.name, "old_date": old_date, "new_date": new_date, "status": wo.status})


# ─────────────────────────────────────────────────────────────────────────────
# 9. GET ASSET PM HISTORY
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_asset_pm_history(asset_ref: str, limit: int = 10) -> dict:
    """
    Lịch sử PM của một thiết bị (PM Task Log).
    GET /api/method/assetcore.api.imm08.get_asset_pm_history
    """
    logs = frappe.db.get_all(
        _DOCTYPE_LOG,
        filters={"asset_ref": asset_ref},
        fields=[
            "name", "pm_work_order", "pm_type", "completion_date",
            "technician", "overall_result", "is_late", "days_late",
            "next_pm_date", "summary",
        ],
        order_by="completion_date desc",
        limit=int(limit),
    )
    return _ok({"asset_ref": asset_ref, "history": logs})
