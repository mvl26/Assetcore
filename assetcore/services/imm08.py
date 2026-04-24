# Copyright (c) 2026, AssetCore Team
# IMM-08 Preventive Maintenance — Tier 2 Business Service Layer.

from __future__ import annotations

import calendar

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, getdate, nowdate

from assetcore.repositories.asset_repo import AssetRepo
from assetcore.repositories.pm_repo import (
    PMChecklistTemplateRepo,
    PMScheduleRepo,
    PMTaskLogRepo,
    PMWorkOrderRepo,
)
from assetcore.repositories.repair_repo import RepairRepo
from assetcore.services.shared import AssetStatus, ErrorCode, ServiceError
from assetcore.utils.helpers import _get_role_emails, _safe_sendmail

_DT_PM_WO = "PM Work Order"
_DT_AC_ASSET = "AC Asset"


def _transition_asset(asset_ref: str, to_status: str, wo_name: str) -> None:
    """Cập nhật lifecycle_status + audit trail qua imm00 service (lazy import tránh circular)."""
    from assetcore.services.imm00 import transition_asset_status  # noqa: PLC0415
    transition_asset_status(
        asset_name=asset_ref,
        to_status=to_status,
        actor=frappe.session.user,
        root_doctype=_DT_PM_WO,
        root_record=wo_name,
    )


# ─── Constants ────────────────────────────────────────────────────────────────

class PMStatus:
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    OVERDUE = "Overdue"
    CANCELLED = "Cancelled"
    HALTED_MAJOR = "Halted–Major Failure"
    PENDING_BUSY = "Pending–Device Busy"


class PMScheduleStatus:
    ACTIVE = "Active"
    PAUSED = "Paused"
    SUSPENDED = "Suspended"

    ALLOWED = (ACTIVE, PAUSED, SUSPENDED)


_LEGACY_ROLE_WORKSHOP = "Workshop Head"
_LEGACY_ROLE_PTP = "VP Block2"

_MEASUREMENT_PASS_FAIL = "Pass/Fail"

_OP_TOKENS = ("in", "not in", "between", "like", "=", "!=", "<", ">", "<=", ">=")


def _normalize_filters(f: dict | None) -> dict:
    out: dict = {}
    for k, v in (f or {}).items():
        if isinstance(v, list) and v and not (len(v) == 2 and v[0] in _OP_TOKENS):
            out[k] = ["in", v]
        else:
            out[k] = v
    return out


def _month_range(year: int, month: int) -> tuple[str, str, int]:
    _, last_day = calendar.monthrange(year, month)
    return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last_day:02d}", last_day


# ─── Scheduler jobs ───────────────────────────────────────────────────────────

def generate_pm_work_orders_from_schedule() -> dict:
    """Scheduler daily: tạo PM WO cho mọi lịch Active đến hạn."""
    today = getdate(nowdate())
    created, skipped, errors = [], [], []

    schedules, _ = PMScheduleRepo.list(
        filters={"status": PMScheduleStatus.ACTIVE},
        fields=["name", "asset_ref", "pm_type", "checklist_template",
                "next_due_date", "alert_days_before", "responsible_technician"],
        page_size=10_000,
    )
    for sched in schedules:
        if not sched.get("next_due_date"):
            skipped.append(f"{sched['name']}: next_due_date trống")
            continue
        if not frappe.db.exists(_DT_AC_ASSET, sched.get("asset_ref")):
            skipped.append(f"{sched['name']}: thiết bị '{sched.get('asset_ref')}' không tồn tại")
            continue
        alert_days = sched.get("alert_days_before") or 7
        trigger_date = add_days(today, alert_days)
        if getdate(sched["next_due_date"]) > getdate(trigger_date):
            continue
        if PMWorkOrderRepo.exists({
            "pm_schedule": sched["name"],
            "status": ["not in", [PMStatus.COMPLETED, PMStatus.CANCELLED]],
        }):
            skipped.append(f"{sched['name']}: có WO chưa đóng")
            continue
        try:
            wo_name = _create_wo_from_schedule(sched)
            created.append(wo_name)
        except Exception as exc:
            frappe.log_error(frappe.get_traceback(), f"IMM-08 auto WO failed: {sched['name']}")
            errors.append(f"{sched['name']}: {exc}")

    frappe.db.commit()
    result = {"created": len(created), "skipped": len(skipped), "errors": len(errors), "names": created}
    frappe.logger().info(f"IMM-08 generate_pm_work_orders: {result}")
    return result


def _create_wo_from_schedule(sched: dict) -> str:
    wo = frappe.new_doc(PMWorkOrderRepo.DOCTYPE)
    wo.asset_ref = sched["asset_ref"]
    wo.pm_schedule = sched["name"]
    wo.pm_type = sched["pm_type"]
    wo.wo_type = "Preventive"
    wo.status = PMStatus.OPEN
    wo.due_date = sched["next_due_date"]
    wo.scheduled_date = sched["next_due_date"]
    wo.assigned_to = sched.get("responsible_technician")
    if sched.get("checklist_template"):
        _populate_checklist(wo, sched["checklist_template"])
    wo.insert(ignore_permissions=True)
    return wo.name


def _populate_checklist(wo, template_name: str) -> None:
    tpl = PMChecklistTemplateRepo.get(template_name)
    if not tpl or not getattr(tpl, "checklist_items", None):
        return
    for idx, item in enumerate(tpl.checklist_items, start=1):
        wo.append("checklist_results", {
            "checklist_item_idx": idx,
            "description": getattr(item, "description", None) or getattr(item, "task_description", ""),
            "measurement_type": getattr(item, "measurement_type", _MEASUREMENT_PASS_FAIL),
            "unit": getattr(item, "unit", ""),
            "result": "",
        })


def update_pm_schedule_after_completion(pm_schedule_name: str, completion_date: str) -> None:
    """Gọi từ PM Work Order controller khi status → Completed."""
    sched = PMScheduleRepo.get(pm_schedule_name)
    if not sched:
        return
    sched.last_pm_date = completion_date
    interval = sched.pm_interval_days or 90
    sched.next_due_date = add_days(getdate(completion_date), interval)
    PMScheduleRepo.save(sched)


# ─── Business operations — Work Order ────────────────────────────────────────

def list_work_orders(filters: dict, *, page: int = 1, page_size: int = 20) -> dict:
    rows, pg = PMWorkOrderRepo.list(
        filters=_normalize_filters(filters),
        fields=["name", "asset_ref", "pm_type", "wo_type", "status",
                "due_date", "completion_date", "assigned_to",
                "overall_result", "is_late", "source_pm_wo"],
        order_by="due_date asc",
        page=page, page_size=page_size,
    )
    asset_ids = {r["asset_ref"] for r in rows if r.get("asset_ref")}
    user_ids = {r["assigned_to"] for r in rows if r.get("assigned_to")}
    if asset_ids:
        asset_rows = frappe.get_all(
            _DT_AC_ASSET, filters={"name": ["in", list(asset_ids)]},
            fields=["name", "asset_name"])
        asset_map = {a.name: a.asset_name for a in asset_rows}
    else:
        asset_map = {}
    if user_ids:
        user_rows = frappe.get_all(
            "User", filters={"name": ["in", list(user_ids)]},
            fields=["name", "full_name"])
        user_map = {u.name: u.full_name for u in user_rows}
    else:
        user_map = {}
    for r in rows:
        r["asset_name"] = asset_map.get(r.get("asset_ref"), r.get("asset_ref") or "")
        r["assigned_to_name"] = user_map.get(r.get("assigned_to"), r.get("assigned_to") or "")
    return {"data": rows, "pagination": pg}


def get_work_order(name: str) -> dict:
    wo = PMWorkOrderRepo.get(name)
    if not wo:
        raise ServiceError(ErrorCode.NOT_FOUND, f"PM Work Order '{name}' không tồn tại")

    asset = AssetRepo.get_value(
        wo.asset_ref,
        ["asset_name", "asset_category", "risk_classification", "location"],
        as_dict=True,
    ) or {}

    checklist = [
        {
            "idx": r.idx,
            "checklist_item_idx": r.checklist_item_idx,
            "description": r.description,
            "measurement_type": r.measurement_type,
            "unit": r.unit,
            "result": r.result,
            "measured_value": r.measured_value,
            "notes": r.notes,
            "photo": r.photo,
        }
        for r in (wo.checklist_results or [])
    ]

    return {
        "name": wo.name,
        "asset_ref": wo.asset_ref,
        "asset_name": asset.get("asset_name", ""),
        "asset_category": asset.get("asset_category", ""),
        "risk_class": asset.get("risk_classification", ""),
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
    }


def assign_technician(name: str, *, technician: str, scheduled_date: str | None = None) -> dict:
    wo = PMWorkOrderRepo.get(name)
    if not wo:
        raise ServiceError(ErrorCode.NOT_FOUND, f"PM Work Order '{name}' không tồn tại")
    if wo.status not in (PMStatus.OPEN, PMStatus.OVERDUE):
        raise ServiceError(ErrorCode.BAD_STATE,
                           f"Không thể phân công khi WO ở trạng thái '{wo.status}'")
    if wo.asset_ref and not frappe.db.exists(_DT_AC_ASSET, wo.asset_ref):
        raise ServiceError(
            ErrorCode.VALIDATION,
            f"Thiết bị '{wo.asset_ref}' đã bị xóa. Phiếu này cần được hủy."
        )
    if wo.pm_schedule and not frappe.db.exists("PM Schedule", wo.pm_schedule):
        raise ServiceError(
            ErrorCode.VALIDATION,
            f"Lịch PM '{wo.pm_schedule}' đã bị xóa. Phiếu này cần được hủy."
        )
    wo.assigned_to = technician
    wo.assigned_by = frappe.session.user
    if scheduled_date:
        wo.scheduled_date = scheduled_date
    wo.status = PMStatus.IN_PROGRESS
    PMWorkOrderRepo.save(wo)
    _transition_asset(wo.asset_ref, AssetStatus.UNDER_MAINTENANCE, wo.name)
    return {"name": wo.name, "status": wo.status, "assigned_to": wo.assigned_to}


def submit_result(name: str, *, checklist_results: list[dict], overall_result: str,
                  technician_notes: str = "", pm_sticker_attached: int = 0,
                  duration_minutes: int = 0) -> dict:
    wo = PMWorkOrderRepo.get(name)
    if not wo:
        raise ServiceError(ErrorCode.NOT_FOUND, f"PM Work Order '{name}' không tồn tại")
    if wo.docstatus == 1:
        raise ServiceError(ErrorCode.CONFLICT, "PM Work Order đã được Submit")

    result_map = {r["idx"]: r for r in checklist_results if "idx" in r}
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
    wo.status = PMStatus.COMPLETED
    wo.completion_date = nowdate()
    PMWorkOrderRepo.save(wo)

    try:
        wo.submit()
    except Exception as e:
        raise ServiceError(ErrorCode.INTERNAL, str(e)) from e

    # Khôi phục trạng thái thiết bị → Active sau khi PM hoàn thành
    _transition_asset(wo.asset_ref, AssetStatus.ACTIVE, wo.name)

    sched_interval = PMScheduleRepo.get_value(wo.pm_schedule, "pm_interval_days") or 0
    next_pm_date = add_days(nowdate(), sched_interval)
    cm_wo = PMWorkOrderRepo.find_one(
        {"source_pm_wo": name, "wo_type": "Corrective"},
        fields=["name"],
    )

    return {
        "name": wo.name,
        "new_status": wo.status,
        "is_late": bool(wo.is_late),
        "next_pm_date": str(next_pm_date),
        "cm_wo_created": cm_wo["name"] if cm_wo else None,
    }


def report_major_failure(pm_wo_name: str, *, failure_description: str) -> dict:
    wo = PMWorkOrderRepo.get(pm_wo_name)
    if not wo:
        raise ServiceError(ErrorCode.NOT_FOUND, f"PM Work Order '{pm_wo_name}' không tồn tại")

    PMWorkOrderRepo.set_values(pm_wo_name, {"status": PMStatus.HALTED_MAJOR})
    _transition_asset(wo.asset_ref, AssetStatus.OUT_OF_SERVICE, pm_wo_name)

    cm_wo = RepairRepo.create({
        "asset_ref": wo.asset_ref,
        "source_pm_wo": pm_wo_name,
        "repair_type": "Emergency",
        "priority": "Emergency",
        "status": "Open",
        "technician_notes": f"[MAJOR FAILURE từ PM] {failure_description}",
    })

    recipients = _get_role_emails([_LEGACY_ROLE_WORKSHOP, _LEGACY_ROLE_PTP])
    asset_name = AssetRepo.get_value(wo.asset_ref, "asset_name") or wo.asset_ref
    if recipients:
        _safe_sendmail(
            recipients=recipients,
            subject=f"[KHẨN] Major Failure PM: {wo.name} — {asset_name}",
            message=(
                f"<p>⚠️ <strong>LỖI NGHIÊM TRỌNG</strong> phát hiện trong quá trình PM.</p>"
                f"<ul>"
                f"<li>PM WO: {wo.name}</li>"
                f"<li>Thiết bị: {asset_name} ({wo.asset_ref})</li>"
                f"<li>Mô tả lỗi: {failure_description}</li>"
                f"<li>CM WO khẩn: {cm_wo.name}</li>"
                f"</ul>"
                f"<p>Thiết bị đã được đặt về <strong>Out of Service</strong>.</p>"
            ),
        )
    try:
        from assetcore.services.imm12 import report_incident as _report_incident_12  # noqa: PLC0415
        _report_incident_12(
            asset=wo.asset_ref,
            incident_type="Malfunction",
            severity="High",
            description=f"Phát hiện lỗi nghiêm trọng trong PM — {wo.name}. {failure_description}",
            fault_code="PM_MAJOR_FAIL",
            linked_repair_wo=cm_wo.name,
            reported_by=frappe.session.user,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-08 → IMM-12 major failure incident")

    return {
        "pm_wo": pm_wo_name,
        "new_status": PMStatus.HALTED_MAJOR,
        "cm_wo_created": cm_wo.name,
        "asset_status": AssetStatus.OUT_OF_SERVICE,
    }


def reschedule(name: str, *, new_date: str, reason: str) -> dict:
    if not reason or len(reason.strip()) < 5:
        raise ServiceError(ErrorCode.VALIDATION,
                           "Lý do hoãn lịch là bắt buộc (tối thiểu 5 ký tự)")
    wo = PMWorkOrderRepo.get(name)
    if not wo:
        raise ServiceError(ErrorCode.NOT_FOUND, f"PM Work Order '{name}' không tồn tại")
    was_in_progress = wo.status == PMStatus.IN_PROGRESS
    old_date = str(wo.due_date)
    wo.due_date = new_date
    wo.status = PMStatus.PENDING_BUSY
    wo.technician_notes = (wo.technician_notes or "") + f"\n[Hoãn lịch {old_date} → {new_date}]: {reason}"
    PMWorkOrderRepo.save(wo)
    # Nếu đang thực hiện (In Progress) → WO bị hoãn → khôi phục asset về Active
    if was_in_progress:
        _transition_asset(wo.asset_ref, AssetStatus.ACTIVE, wo.name)
    return {"name": wo.name, "old_date": old_date, "new_date": new_date, "status": wo.status}


def create_adhoc_work_order(data: dict) -> dict:
    required = ("asset_ref", "pm_schedule", "due_date")
    missing = [f for f in required if not data.get(f)]
    if missing:
        raise ServiceError(ErrorCode.VALIDATION,
                           f"Thiếu trường bắt buộc: {', '.join(missing)}")

    sched = PMScheduleRepo.get_value(
        data["pm_schedule"],
        ["asset_ref", "pm_type", "checklist_template", "status"],
        as_dict=True,
    )
    if not sched:
        raise ServiceError(ErrorCode.NOT_FOUND,
                           f"PM Schedule '{data['pm_schedule']}' không tồn tại")
    if sched["asset_ref"] != data["asset_ref"]:
        raise ServiceError(
            ErrorCode.VALIDATION,
            f"PM Schedule thuộc asset '{sched['asset_ref']}', không khớp '{data['asset_ref']}'",
        )
    if sched["status"] != PMScheduleStatus.ACTIVE:
        raise ServiceError(
            ErrorCode.BAD_STATE,
            f"PM Schedule đang ở trạng thái '{sched['status']}', không tạo WO được",
        )

    from assetcore.services.imm00 import validate_asset_for_operations
    try:
        validate_asset_for_operations(data["asset_ref"])
    except frappe.exceptions.ValidationError as e:
        raise ServiceError(ErrorCode.BAD_STATE, str(e)) from e

    doc = frappe.new_doc(PMWorkOrderRepo.DOCTYPE)
    doc.asset_ref = data["asset_ref"]
    doc.pm_schedule = data["pm_schedule"]
    doc.pm_type = data.get("pm_type") or sched["pm_type"]
    doc.wo_type = data.get("wo_type", "Preventive")
    doc.status = PMStatus.OPEN
    doc.due_date = data["due_date"]
    if data.get("assigned_to"):
        doc.assigned_to = data["assigned_to"]
        doc.assigned_by = frappe.session.user
    if data.get("technician_notes"):
        doc.technician_notes = data["technician_notes"]

    _populate_checklist(doc, sched.get("checklist_template") or "")
    doc.insert(ignore_permissions=False)
    frappe.db.commit()
    return {
        "name": doc.name,
        "status": doc.status,
        "checklist_items_count": len(doc.checklist_results or []),
    }


# ─── Calendar & Dashboard ────────────────────────────────────────────────────

def get_calendar(*, year: int, month: int,
                 asset_ref: str | None = None,
                 technician: str | None = None) -> dict:
    start_date, end_date, _ld = _month_range(year, month)
    filters = {"due_date": ["between", [start_date, end_date]]}
    if asset_ref:
        filters["asset_ref"] = asset_ref
    if technician:
        filters["assigned_to"] = technician

    wos, _ = PMWorkOrderRepo.list(
        filters=filters,
        fields=["name", "asset_ref", "pm_type", "due_date", "status", "assigned_to", "is_late"],
        order_by="due_date asc",
        page_size=5000,
    )
    asset_ids = {w["asset_ref"] for w in wos if w.get("asset_ref")}
    asset_map = {}
    if asset_ids:
        rows = frappe.get_all(_DT_AC_ASSET, filters={"name": ["in", list(asset_ids)]},
                               fields=["name", "asset_name"])
        asset_map = {a.name: a.asset_name for a in rows}
    events = [
        {**w, "asset_name": asset_map.get(w.get("asset_ref")) or w.get("asset_ref") or "", "due_date": str(w["due_date"])}
        for w in wos
    ]
    total = len(events)
    completed = sum(1 for e in events if e["status"] == PMStatus.COMPLETED)
    overdue = sum(1 for e in events if e["status"] == PMStatus.OVERDUE)
    return {
        "month": f"{year:04d}-{month:02d}",
        "events": events,
        "summary": {
            "total": total, "completed": completed, "overdue": overdue,
            "pending": total - completed - overdue,
        },
    }


def get_dashboard_stats(*, year: int, month: int) -> dict:
    start_date, end_date, _ld = _month_range(year, month)
    wos, _ = PMWorkOrderRepo.list(
        filters={"due_date": ["between", [start_date, end_date]]},
        fields=["name", "status", "is_late", "completion_date", "due_date"],
        page_size=5000,
    )
    total = len(wos)
    completed = [w for w in wos if w["status"] == PMStatus.COMPLETED]
    on_time = [w for w in completed if not w["is_late"]]
    overdue = [w for w in wos if w["status"] == PMStatus.OVERDUE]
    late_days = [
        date_diff(str(w["completion_date"]), str(w["due_date"]))
        for w in completed if w["is_late"] and w["completion_date"]
    ]
    compliance_rate = round(len(on_time) / total * 100, 1) if total else 0.0
    avg_days_late = round(sum(late_days) / len(late_days), 1) if late_days else 0.0

    trend = []
    for i in range(5, -1, -1):
        m = month - i
        y = year
        while m <= 0:
            m += 12
            y -= 1
        s, e, _ = _month_range(y, m)
        month_wos, _ = PMWorkOrderRepo.list(
            filters={"due_date": ["between", [s, e]]},
            fields=["status", "is_late"],
            page_size=5000,
        )
        t = len(month_wos)
        c_on = sum(1 for w in month_wos if w["status"] == PMStatus.COMPLETED and not w["is_late"])
        trend.append({
            "month": f"{y:04d}-{m:02d}", "total": t, "on_time": c_on,
            "rate": round(c_on / t * 100, 1) if t else 0.0,
        })
    return {
        "kpis": {
            "compliance_rate_pct": compliance_rate,
            "total_scheduled": total,
            "completed_on_time": len(on_time),
            "overdue": len(overdue),
            "avg_days_late": avg_days_late,
        },
        "trend_6months": trend,
    }


def get_asset_history(asset_ref: str, *, limit: int = 10) -> dict:
    logs, _ = PMTaskLogRepo.list(
        filters={"asset_ref": asset_ref},
        fields=["name", "pm_work_order", "pm_type", "completion_date",
                "technician", "overall_result", "is_late", "days_late",
                "next_pm_date", "summary"],
        order_by="completion_date desc",
        page_size=int(limit),
    )
    return {"asset_ref": asset_ref, "history": logs}


# ─── PM Schedule CRUD ─────────────────────────────────────────────────────────

def list_schedules(*, asset_ref: str | None = None, status: str | None = None,
                   page: int = 1, page_size: int = 20) -> dict:
    filters: dict = {}
    if asset_ref:
        filters["asset_ref"] = asset_ref
    if status:
        filters["status"] = status
    rows, pg = PMScheduleRepo.list(
        filters=filters,
        fields=["name", "asset_ref", "pm_type", "status", "pm_interval_days",
                "checklist_template", "responsible_technician",
                "last_pm_date", "next_due_date", "alert_days_before"],
        order_by="next_due_date asc",
        page=page, page_size=page_size,
    )
    for r in rows:
        r["asset_name"] = AssetRepo.get_value(r["asset_ref"], "asset_name") or ""
    return {"data": rows, "pagination": pg}


def get_schedule(name: str) -> dict:
    doc = PMScheduleRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"PM Schedule '{name}' không tồn tại")
    return doc.as_dict()


def create_schedule(data: dict) -> dict:
    required = ("asset_ref", "pm_type", "pm_interval_days", "checklist_template")
    missing = [f for f in required if not data.get(f)]
    if missing:
        raise ServiceError(ErrorCode.VALIDATION,
                           f"Thiếu trường bắt buộc: {', '.join(missing)}")
    payload = {k: v for k, v in data.items() if k not in ("cmd", "doctype")}
    if "status" not in payload:
        payload["status"] = PMScheduleStatus.ACTIVE
    try:
        doc = PMScheduleRepo.create(payload, ignore_permissions=False)
        frappe.db.commit()
    except frappe.ValidationError as e:
        raise ServiceError(ErrorCode.VALIDATION, str(e)) from e
    return {"name": doc.name, "status": doc.status}


def update_schedule(name: str, data: dict) -> dict:
    if not PMScheduleRepo.exists(name):
        raise ServiceError(ErrorCode.NOT_FOUND, f"PM Schedule '{name}' không tồn tại")
    payload = {k: v for k, v in data.items() if k not in ("cmd", "name", "doctype")}
    try:
        doc = PMScheduleRepo.update_fields(name, payload, ignore_permissions=False)
        frappe.db.commit()
    except frappe.ValidationError as e:
        raise ServiceError(ErrorCode.VALIDATION, str(e)) from e
    return {"name": doc.name}


def set_schedule_status(name: str, status: str) -> dict:
    if status not in PMScheduleStatus.ALLOWED:
        raise ServiceError(ErrorCode.VALIDATION, "status phải là Active | Paused | Suspended")
    if not PMScheduleRepo.exists(name):
        raise ServiceError(ErrorCode.NOT_FOUND, f"PM Schedule '{name}' không tồn tại")
    PMScheduleRepo.set_values(name, {"status": status})
    frappe.db.commit()
    return {"name": name, "status": status}


def delete_schedule(name: str) -> dict:
    if not PMScheduleRepo.exists(name):
        raise ServiceError(ErrorCode.NOT_FOUND, f"PM Schedule '{name}' không tồn tại")
    try:
        PMScheduleRepo.delete(name, ignore_permissions=False)
        frappe.db.commit()
    except (frappe.ValidationError, frappe.LinkExistsError) as e:
        raise ServiceError(ErrorCode.CONFLICT, str(e)) from e
    return {"name": name, "deleted": True}


# ─── PM Checklist Template CRUD ───────────────────────────────────────────────

def list_templates(*, asset_category: str | None = None, pm_type: str | None = None,
                   page: int = 1, page_size: int = 20) -> dict:
    filters: dict = {}
    if asset_category:
        filters["asset_category"] = asset_category
    if pm_type:
        filters["pm_type"] = pm_type
    rows, pg = PMChecklistTemplateRepo.list(
        filters=filters,
        fields=["name", "template_name", "asset_category", "pm_type",
                "version", "effective_date", "approved_by"],
        order_by="template_name asc",
        page=page, page_size=page_size,
    )
    return {"data": rows, "pagination": pg}


def get_template(name: str) -> dict:
    doc = PMChecklistTemplateRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND,
                           f"PM Checklist Template '{name}' không tồn tại")
    return doc.as_dict()


def create_template(data: dict) -> dict:
    required = ("template_name", "asset_category", "pm_type")
    missing = [f for f in required if not data.get(f)]
    if missing:
        raise ServiceError(ErrorCode.VALIDATION,
                           f"Thiếu trường bắt buộc: {', '.join(missing)}")
    items = data.get("checklist_items") or []
    try:
        doc = frappe.new_doc(PMChecklistTemplateRepo.DOCTYPE)
        doc.template_name = data["template_name"]
        doc.asset_category = data["asset_category"]
        doc.pm_type = data["pm_type"]
        doc.version = data.get("version", "1.0")
        doc.effective_date = data.get("effective_date") or nowdate()
        for it in items:
            doc.append("checklist_items", {
                "description": it.get("description"),
                "measurement_type": it.get("measurement_type", _MEASUREMENT_PASS_FAIL),
                "unit": it.get("unit"),
                "expected_min": it.get("expected_min"),
                "expected_max": it.get("expected_max"),
                "is_critical": 1 if it.get("is_critical") else 0,
                "reference_section": it.get("reference_section"),
            })
        doc.insert(ignore_permissions=False)
        frappe.db.commit()
    except frappe.ValidationError as e:
        raise ServiceError(ErrorCode.VALIDATION, str(e)) from e
    return {"name": doc.name, "items_count": len(doc.checklist_items or [])}


def update_template(name: str, data: dict) -> dict:
    doc = PMChecklistTemplateRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND,
                           f"PM Checklist Template '{name}' không tồn tại")
    for k in ("template_name", "asset_category", "pm_type", "version",
              "effective_date", "approved_by"):
        if k in data:
            setattr(doc, k, data[k])
    if "checklist_items" in data:
        items = data.get("checklist_items") or []
        doc.checklist_items = []
        for it in items:
            doc.append("checklist_items", {
                "description": it.get("description"),
                "measurement_type": it.get("measurement_type", _MEASUREMENT_PASS_FAIL),
                "unit": it.get("unit"),
                "expected_min": it.get("expected_min"),
                "expected_max": it.get("expected_max"),
                "is_critical": 1 if it.get("is_critical") else 0,
                "reference_section": it.get("reference_section"),
            })
    try:
        PMChecklistTemplateRepo.save(doc, ignore_permissions=False)
        frappe.db.commit()
    except frappe.ValidationError as e:
        raise ServiceError(ErrorCode.VALIDATION, str(e)) from e
    return {"name": doc.name}


def approve_template(name: str) -> dict:
    if not PMChecklistTemplateRepo.exists(name):
        raise ServiceError(ErrorCode.NOT_FOUND,
                           f"PM Checklist Template '{name}' không tồn tại")
    PMChecklistTemplateRepo.set_values(name, {"approved_by": frappe.session.user})
    frappe.db.commit()
    return {"name": name, "approved_by": frappe.session.user}


def version_template(source_name: str, new_version: str) -> dict:
    src = PMChecklistTemplateRepo.get(source_name)
    if not src:
        raise ServiceError(ErrorCode.NOT_FOUND,
                           f"PM Checklist Template '{source_name}' không tồn tại")
    try:
        new_doc = frappe.copy_doc(src)
        new_doc.version = new_version
        new_doc.approved_by = None
        new_doc.effective_date = nowdate()
        new_doc.template_name = f"{src.template_name} v{new_version}"
        new_doc.insert(ignore_permissions=False)
        frappe.db.commit()
    except frappe.ValidationError as e:
        raise ServiceError(ErrorCode.VALIDATION, str(e)) from e
    return {"name": new_doc.name, "version": new_version}


def delete_template(name: str) -> dict:
    if not PMChecklistTemplateRepo.exists(name):
        raise ServiceError(ErrorCode.NOT_FOUND,
                           f"PM Checklist Template '{name}' không tồn tại")
    try:
        PMChecklistTemplateRepo.delete(name, ignore_permissions=False)
        frappe.db.commit()
    except (frappe.ValidationError, frappe.LinkExistsError) as e:
        raise ServiceError(ErrorCode.CONFLICT, str(e)) from e
    return {"name": name, "deleted": True}


# ─── Hook từ IMM-04 Commissioning ────────────────────────────────────────────

_PM_TYPE_FROM_INTERVAL = [(91, "Quarterly"), (183, "Semi-Annual"), (366, "Annual")]


def create_pm_schedule_from_commissioning(commissioning_doc) -> str | None:
    """Hook: Asset Commissioning on_submit → tạo PM Schedule nếu thiết bị yêu cầu PM."""
    asset = commissioning_doc.final_asset
    if not asset:
        return None
    device_model = frappe.db.get_value(_DT_AC_ASSET, asset, "device_model")
    if not device_model:
        return None
    model = frappe.db.get_value(
        "IMM Device Model", device_model,
        ["is_pm_required", "pm_interval_days", "pm_alert_days"],
        as_dict=True,
    )
    if not model or not model.get("is_pm_required"):
        return None
    interval = int(model.get("pm_interval_days") or 365)
    alert_days = int(model.get("pm_alert_days") or 7)
    pm_type = next((t for days, t in _PM_TYPE_FROM_INTERVAL if interval <= days), "Annual")
    base_date = commissioning_doc.commissioning_date or nowdate()
    sched = PMScheduleRepo.create({
        "asset_ref": asset,
        "pm_type": pm_type,
        "pm_interval_days": interval,
        "alert_days_before": alert_days,
        "status": PMScheduleStatus.ACTIVE,
        "next_due_date": add_days(base_date, interval),
        "created_from_commissioning": commissioning_doc.name,
    })
    from assetcore.services.imm00 import log_audit_event  # noqa: PLC0415
    log_audit_event(
        asset=asset, event_type="PM Schedule Created",
        actor=frappe.session.user,
        ref_doctype=PMScheduleRepo.DOCTYPE, ref_name=sched.name,
        change_summary=f"Auto từ commissioning {commissioning_doc.name}",
    )
    frappe.logger().info(f"IMM-08 PM Schedule {sched.name} tạo từ commissioning {commissioning_doc.name}")
    return sched.name
