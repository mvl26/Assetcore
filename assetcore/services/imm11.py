# Copyright (c) 2026, AssetCore Team
# IMM-11 Calibration — Tier 2 Business Service Layer.
#
# KHÔNG gọi frappe.db.* / frappe.get_doc trực tiếp — đi qua repository.
# Raise ServiceError thay vì trả dict; API layer sẽ catch và format envelope.

from __future__ import annotations

from typing import Optional

import frappe
from frappe.utils import nowdate, add_days, getdate, date_diff

from assetcore.services.imm00 import (
    transition_asset_status,
    create_capa,
    log_audit_event,
    create_lifecycle_event,
)
from assetcore.services.shared import (
    AssetStatus,
    CalibrationResult,
    CalibrationStatus,
    ErrorCode,
    ServiceError,
)
from assetcore.repositories.asset_repo import AssetRepo, DeviceModelRepo, CapaRepo
from assetcore.repositories.calibration_repo import CalibrationRepo, CalibrationScheduleRepo

_DEFAULT_INTERVAL_DAYS = 365
_NOT_DECOMMISSIONED = ("not in", [AssetStatus.DECOMMISSIONED])
_CAPA_OPEN_STATUSES = ("in", ["Open", "In Progress", "In Review"])
_LOOKBACK_IN_PROGRESS = "In Progress"


# ─── Hooks từ module khác ─────────────────────────────────────────────────────

def create_calibration_schedule_from_commissioning(commissioning_doc) -> Optional[str]:
    """Hook: IMM-04 Commissioning on_submit."""
    asset = commissioning_doc.asset
    device_model = AssetRepo.get_value(asset, "device_model")
    if not device_model:
        return None
    model = DeviceModelRepo.get_value(
        device_model,
        ["calibration_required", "calibration_interval_days", "calibration_type_default"],
        as_dict=True,
    ) or {}
    if not model.get("calibration_required"):
        return None
    interval = model.get("calibration_interval_days") or _DEFAULT_INTERVAL_DAYS
    cal_type = model.get("calibration_type_default") or "External"
    base_date = commissioning_doc.commissioning_date or nowdate()

    sched = CalibrationScheduleRepo.create({
        "asset": asset,
        "device_model": device_model,
        "calibration_type": cal_type,
        "interval_days": interval,
        "last_calibration_date": base_date,
        "next_due_date": add_days(base_date, interval),
        "is_active": 1,
    })
    log_audit_event(
        asset=asset, event_type="Calibration Schedule Created",
        actor=frappe.session.user, ref_doctype=CalibrationScheduleRepo.DOCTYPE,
        ref_name=sched.name,
        change_summary=f"Auto from commissioning {commissioning_doc.name}",
    )
    return sched.name


def create_post_repair_calibration(asset_name: str) -> Optional[str]:
    """Hook: IMM-09 Repair completed → tái cal nếu thiết bị có Schedule."""
    sched = CalibrationScheduleRepo.find_one(
        {"asset": asset_name, "is_active": 1},
        fields=["name", "calibration_type"],
    )
    if not sched:
        return None
    cal = CalibrationRepo.create({
        "calibration_schedule": sched["name"],
        "asset": asset_name,
        "calibration_type": sched["calibration_type"],
        "scheduled_date": nowdate(),
        "status": CalibrationResult.SCHEDULED,
        "is_recalibration": 1,
        "technician": frappe.session.user,
    })
    return cal.name


# ─── Scheduler jobs ───────────────────────────────────────────────────────────

def create_due_calibration_wos() -> int:
    """Scheduler daily — tạo CAL WO cho Schedule due ≤ 30 ngày."""
    threshold = add_days(nowdate(), 30)
    schedules, _ = CalibrationScheduleRepo.list(
        filters={"is_active": 1, "next_due_date": ("<=", threshold)},
        fields=["name", "asset", "device_model", "calibration_type",
                "interval_days", "next_due_date", "preferred_lab"],
        page_size=500,
    )
    created = 0
    for s in schedules:
        if CalibrationRepo.exists({
            "calibration_schedule": s["name"],
            "status": ("in", list(CalibrationResult.ACTIVE_STATUSES)),
        }):
            continue
        asset_status = AssetRepo.get_value(s["asset"], "lifecycle_status")
        if asset_status in AssetStatus.BLOCKED_FOR_WO:
            continue
        CalibrationRepo.create({
            "calibration_schedule": s["name"],
            "asset": s["asset"],
            "device_model": s["device_model"],
            "calibration_type": s["calibration_type"],
            "scheduled_date": s["next_due_date"],
            "lab_supplier": s["preferred_lab"],
            "status": CalibrationResult.SCHEDULED,
            "technician": AssetRepo.get_value(s["asset"], "responsible_technician") or frappe.session.user,
        })
        created += 1
    return created


def check_calibration_expiry() -> None:
    """Scheduler daily — update calibration_status trên AC Asset."""
    today = getdate(nowdate())
    assets, _ = AssetRepo.list(
        filters={
            "lifecycle_status": _NOT_DECOMMISSIONED,
            "next_calibration_date": ("is", "set"),
        },
        fields=["name", "next_calibration_date"],
        page_size=10_000,
    )
    for a in assets:
        days_left = date_diff(a["next_calibration_date"], today)
        if days_left < 0:
            status = CalibrationStatus.OVERDUE
        elif days_left <= 30:
            status = CalibrationStatus.DUE_SOON
        else:
            status = CalibrationStatus.ON_SCHEDULE
        AssetRepo.set_values(a["name"], {"calibration_status": status})


# ─── Submit handlers (gọi từ Controller on_submit) ────────────────────────────

def handle_calibration_pass(cal_doc) -> None:
    """on_submit Pass: cập nhật lịch + lifecycle event."""
    interval = None
    if cal_doc.calibration_schedule:
        interval = CalibrationScheduleRepo.get_value(
            cal_doc.calibration_schedule, "interval_days")
    if not interval:
        interval = DeviceModelRepo.get_value(
            cal_doc.device_model, "calibration_interval_days") or _DEFAULT_INTERVAL_DAYS

    basis_date = cal_doc.certificate_date or cal_doc.actual_date or nowdate()
    next_date = add_days(str(basis_date), interval)

    AssetRepo.set_values(cal_doc.asset, {
        "last_calibration_date": basis_date,
        "next_calibration_date": next_date,
        "calibration_status": CalibrationStatus.ON_SCHEDULE,
    })
    CalibrationRepo.set_values(cal_doc.name, {"next_calibration_date": next_date})

    if cal_doc.calibration_schedule:
        CalibrationScheduleRepo.set_values(cal_doc.calibration_schedule, {
            "last_calibration_date": basis_date,
            "next_due_date": next_date,
        })

    current_status = AssetRepo.get_value(cal_doc.asset, "lifecycle_status")
    create_lifecycle_event(
        asset=cal_doc.asset, event_type="calibration_passed",
        actor=frappe.session.user,
        from_status=current_status, to_status=current_status,
        root_doctype=CalibrationRepo.DOCTYPE, root_record=cal_doc.name,
        notes=f"Result: {cal_doc.overall_result}; next due: {next_date}",
    )

    if cal_doc.is_recalibration and current_status == AssetStatus.OUT_OF_SERVICE:
        transition_asset_status(
            asset_name=cal_doc.asset, to_status=AssetStatus.ACTIVE,
            root_doctype=CalibrationRepo.DOCTYPE, root_record=cal_doc.name,
            reason="Recalibration Pass after CAPA",
        )


def handle_calibration_fail(cal_doc) -> None:
    """on_submit Fail: transition → Out of Service + CAPA + lookback."""
    AssetRepo.set_values(cal_doc.asset, {"calibration_status": CalibrationStatus.FAILED})

    failed_params = _failed_params(cal_doc)
    capa_name = create_capa(
        asset=cal_doc.asset,
        source_type=CalibrationRepo.DOCTYPE,
        source_ref=cal_doc.name,
        severity="Major",
        description=f"Calibration failed; out-of-tolerance parameters: {failed_params}",
        responsible=frappe.session.user, due_days=30,
    )
    CalibrationRepo.set_values(cal_doc.name, {"capa_record": capa_name})

    lookback = perform_lookback_assessment(cal_doc.device_model, cal_doc.asset)
    CapaRepo.set_values(capa_name, {
        "lookback_required": 1,
        "lookback_status": _LOOKBACK_IN_PROGRESS if lookback else "Cleared",
        "lookback_assets": ", ".join(lookback),
    })

    transition_asset_status(
        asset_name=cal_doc.asset, to_status=AssetStatus.OUT_OF_SERVICE,
        root_doctype=CalibrationRepo.DOCTYPE, root_record=cal_doc.name,
        reason=f"Calibration failed — {cal_doc.name}; CAPA: {capa_name}; lookback {len(lookback)} assets",
    )


def perform_lookback_assessment(device_model: str, exclude_asset: str) -> list[str]:
    """BR-11-03 — assets cùng device_model đang Active."""
    rows, _ = AssetRepo.list(
        filters={
            "device_model": device_model,
            "lifecycle_status": AssetStatus.ACTIVE,
            "name": ("!=", exclude_asset),
        },
        fields=["name"],
        page_size=10_000,
    )
    return [r["name"] for r in rows]


# ─── Business operations gọi từ API (Tier 1) ─────────────────────────────────

def list_schedules(filters: dict | None = None, *, page: int = 1, page_size: int = 20) -> dict:
    rows, pg = CalibrationScheduleRepo.list(
        filters=filters,
        fields=["name", "asset", "device_model", "calibration_type",
                "interval_days", "last_calibration_date", "next_due_date",
                "preferred_lab", "is_active"],
        order_by="next_due_date asc",
        page=page, page_size=page_size,
    )
    return {"data": rows, "pagination": pg}


def get_schedule(name: str) -> dict:
    doc = CalibrationScheduleRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy Schedule '{name}'")
    return doc.as_dict()


def create_schedule(*, asset: str, calibration_type: str, interval_days: int,
                    preferred_lab: str | None = None,
                    next_due_date: str | None = None) -> dict:
    if not AssetRepo.exists(asset):
        raise ServiceError(ErrorCode.NOT_FOUND, "Thiết bị không tồn tại")
    device_model = AssetRepo.get_value(asset, "device_model")
    doc = CalibrationScheduleRepo.create({
        "asset": asset,
        "device_model": device_model,
        "calibration_type": calibration_type,
        "interval_days": int(interval_days),
        "next_due_date": next_due_date or add_days(nowdate(), int(interval_days)),
        "preferred_lab": preferred_lab,
        "is_active": 1,
    })
    return {"name": doc.name, "next_due_date": doc.next_due_date}


def update_schedule(name: str, patch: dict) -> dict:
    allowed = {"calibration_type", "interval_days", "preferred_lab", "next_due_date", "is_active"}
    if not CalibrationScheduleRepo.exists(name):
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy Schedule '{name}'")
    clean_patch = {k: v for k, v in patch.items() if k in allowed}
    if not clean_patch:
        raise ServiceError(ErrorCode.VALIDATION, "Không có trường nào được cập nhật")
    doc = CalibrationScheduleRepo.update_fields(name, clean_patch)
    return {"name": doc.name}


def delete_schedule(name: str) -> dict:
    if not CalibrationScheduleRepo.exists(name):
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy Schedule '{name}'")
    if CalibrationRepo.exists({"calibration_schedule": name, "docstatus": 1}):
        raise ServiceError(ErrorCode.CONFLICT,
                           "Không thể xóa Schedule đã có Phiếu đã Submit")
    CalibrationScheduleRepo.delete(name)
    return {"name": name, "deleted": True}


def list_calibrations(filters: dict | None = None, *, page: int = 1, page_size: int = 20) -> dict:
    rows, pg = CalibrationRepo.list(
        filters=_normalize_list_filters(filters),
        fields=["name", "asset", "device_model", "calibration_type", "status",
                "scheduled_date", "actual_date", "technician", "overall_result",
                "next_calibration_date", "lab_supplier", "is_recalibration"],
        order_by="scheduled_date desc",
        page=page, page_size=page_size,
    )
    asset_ids = {r.get("asset") for r in rows if r.get("asset")}
    if asset_ids:
        asset_rows, _ = AssetRepo.list(
            filters={"name": ("in", list(asset_ids))},
            fields=["name", "asset_name"],
            page_size=len(asset_ids),
        )
        asset_map = {a["name"]: a.get("asset_name") for a in asset_rows}
        for r in rows:
            r["asset_name"] = asset_map.get(r.get("asset"), r.get("asset") or "")
    return {"data": rows, "pagination": pg}


def get_calibration(name: str) -> dict:
    doc = CalibrationRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy '{name}'")
    return doc.as_dict()


def create_calibration(*, asset: str, calibration_type: str, scheduled_date: str,
                        technician: str, calibration_schedule: str | None = None,
                        lab_supplier: str | None = None,
                        is_recalibration: int = 0,
                        reference_standard_serial: str | None = None,
                        traceability_reference: str | None = None) -> dict:
    if not AssetRepo.exists(asset):
        raise ServiceError(ErrorCode.NOT_FOUND, "Thiết bị không tồn tại")
    asset_status = AssetRepo.get_value(asset, "lifecycle_status")
    if asset_status in AssetStatus.BLOCKED_FOR_WO and not int(is_recalibration):
        raise ServiceError(ErrorCode.BAD_STATE,
                           "Thiết bị không thể tạo Calibration WO (CAL-008)")
    doc = CalibrationRepo.create({
        "asset": asset,
        "calibration_type": calibration_type,
        "scheduled_date": scheduled_date,
        "technician": technician,
        "calibration_schedule": calibration_schedule,
        "lab_supplier": lab_supplier,
        "is_recalibration": int(is_recalibration),
        "reference_standard_serial": reference_standard_serial,
        "traceability_reference": traceability_reference,
        "status": CalibrationResult.SCHEDULED,
    })
    return {"name": doc.name, "status": doc.status}


_UPDATE_ALLOWED = {
    "status", "actual_date", "lab_supplier", "lab_accreditation_number",
    "lab_contract_ref", "sent_date", "sent_by", "certificate_file",
    "certificate_date", "certificate_number", "reference_standard_serial",
    "traceability_reference", "technician_notes", "calibration_sticker_attached",
    "sticker_photo", "pm_work_order", "amendment_reason",
}


def update_calibration(name: str, patch: dict) -> dict:
    doc = CalibrationRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy '{name}'")
    if doc.docstatus == 1:
        raise ServiceError(ErrorCode.BAD_STATE,
                           "Phiếu đã Submit — không thể chỉnh sửa (dùng Amend)")
    clean_patch = {k: v for k, v in patch.items() if k in _UPDATE_ALLOWED}
    if not clean_patch:
        raise ServiceError(ErrorCode.VALIDATION, "Không có trường nào được cập nhật")
    doc = CalibrationRepo.update_fields(name, clean_patch)
    return {"name": doc.name, "status": doc.status}


def submit_calibration(name: str) -> dict:
    doc = CalibrationRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy '{name}'")
    if doc.docstatus == 1:
        raise ServiceError(ErrorCode.CONFLICT, "Phiếu đã Submit")
    doc = CalibrationRepo.submit(name)
    return {
        "name": doc.name,
        "status": doc.status,
        "overall_result": doc.overall_result,
        "next_calibration_date": str(doc.next_calibration_date or ""),
    }


def add_measurement(name: str, *, parameter_name: str, unit: str, nominal_value: float,
                    tolerance_positive: float, tolerance_negative: float,
                    measured_value: float | None = None) -> dict:
    doc = CalibrationRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy '{name}'")
    if doc.docstatus == 1:
        raise ServiceError(ErrorCode.BAD_STATE,
                           "Không thể thêm tham số vào Phiếu đã Submit")
    doc.append("measurements", {
        "parameter_name": parameter_name,
        "unit": unit,
        "nominal_value": float(nominal_value),
        "tolerance_positive": float(tolerance_positive),
        "tolerance_negative": float(tolerance_negative),
        "measured_value": float(measured_value) if measured_value is not None else None,
    })
    CalibrationRepo.save(doc)
    return {"name": doc.name, "measurement_count": len(doc.measurements)}


def get_kpis(year: int, month: int) -> dict:
    import calendar as _calendar
    start = f"{year}-{month:02d}-01"
    end = f"{year}-{month:02d}-{_calendar.monthrange(year, month)[1]:02d}"
    between = ("between", [start, end])

    total = CalibrationRepo.count({"scheduled_date": between})
    completed = CalibrationRepo.count({
        "scheduled_date": between,
        "status": ("in", [CalibrationResult.PASSED, CalibrationResult.COND_PASSED]),
    })
    failed = CalibrationRepo.count({
        "scheduled_date": between,
        "status": CalibrationResult.FAILED,
    })
    overdue_assets = AssetRepo.count({"calibration_status": CalibrationStatus.OVERDUE})
    due_soon = AssetRepo.count({"calibration_status": CalibrationStatus.DUE_SOON})
    pass_rate = round((completed / total * 100), 1) if total else 0.0

    return {
        "kpis": {
            "total_this_month": total,
            "completed": completed,
            "failed": failed,
            "pass_rate_pct": pass_rate,
            "overdue_assets": overdue_assets,
            "due_soon_assets": due_soon,
        }
    }


def get_dashboard() -> dict:
    """Dashboard IMM-11 — theo docs/imm-11/IMM-11_UI_UX_Guide.md §3.3.

    Trả về: compliance_pct, oot_pct, capa_open, avg_days_to_cert +
    danh sách overdue / due_soon (top 10) + CAPA open (top 5).
    """
    import calendar as _calendar
    now = nowdate()
    year = getdate(now).year
    month = getdate(now).month
    start = f"{year}-{month:02d}-01"
    end = f"{year}-{month:02d}-{_calendar.monthrange(year, month)[1]:02d}"
    between = ("between", [start, end])

    total = CalibrationRepo.count({"scheduled_date": between})
    completed = CalibrationRepo.count({
        "scheduled_date": between,
        "status": ("in", [CalibrationResult.PASSED, CalibrationResult.COND_PASSED]),
    })
    failed = CalibrationRepo.count({"scheduled_date": between,
                                     "status": CalibrationResult.FAILED})
    compliance_pct = round((completed / total * 100), 1) if total else 0.0

    # OOT across measurements (raw SQL — repo không có join helper)
    oot_row = frappe.db.sql("""
        SELECT COALESCE(SUM(CASE WHEN m.out_of_tolerance=1 THEN 1 ELSE 0 END),0) AS oot,
               COUNT(m.name) AS total_m
        FROM `tabIMM Asset Calibration` c
        INNER JOIN `tabIMM Calibration Measurement` m ON m.parent = c.name
        WHERE c.docstatus = 1 AND c.scheduled_date BETWEEN %s AND %s
    """, (start, end), as_dict=True)
    oot = (oot_row[0] if oot_row else {"oot": 0, "total_m": 0})
    oot_pct = round((oot["oot"] / oot["total_m"] * 100), 1) if oot.get("total_m") else 0.0

    capa_open = CapaRepo.count({
        "status": _CAPA_OPEN_STATUSES,
        "source_type": CalibrationRepo.DOCTYPE,
    })

    # Overdue / Due Soon (top 10)
    overdue_assets, _ = AssetRepo.list(
        filters={"calibration_status": CalibrationStatus.OVERDUE,
                 "lifecycle_status": _NOT_DECOMMISSIONED},
        fields=["name", "asset_name", "device_model", "next_calibration_date", "location"],
        order_by="next_calibration_date asc", page_size=10,
    )
    due_soon_assets, _ = AssetRepo.list(
        filters={"calibration_status": CalibrationStatus.DUE_SOON,
                 "lifecycle_status": _NOT_DECOMMISSIONED},
        fields=["name", "asset_name", "device_model", "next_calibration_date", "location"],
        order_by="next_calibration_date asc", page_size=10,
    )

    # CAPA open list (top 5)
    capa_rows, _ = CapaRepo.list(
        filters={"status": _CAPA_OPEN_STATUSES,
                 "source_type": CalibrationRepo.DOCTYPE},
        fields=["name", "asset", "source_ref", "severity",
                "opened_date", "due_date", "status", "lookback_status"],
        order_by="due_date asc", page_size=5,
    )

    # Avg days sent → cert received (external, tháng này)
    avg_row = frappe.db.sql("""
        SELECT AVG(DATEDIFF(c.certificate_date, c.sent_date)) AS avg_d
        FROM `tabIMM Asset Calibration` c
        WHERE c.docstatus = 1 AND c.calibration_type = 'External'
          AND c.sent_date IS NOT NULL AND c.certificate_date IS NOT NULL
          AND c.scheduled_date BETWEEN %s AND %s
    """, (start, end))
    avg_days_val = round(avg_row[0][0], 1) if (avg_row and avg_row[0][0] is not None) else 0

    return {
        "kpis": {
            "compliance_pct": compliance_pct,
            "total_scheduled": total,
            "completed": completed,
            "failed": failed,
            "oot_pct": oot_pct,
            "oot_count": oot.get("oot", 0),
            "measurements_total": oot.get("total_m", 0),
            "capa_open": capa_open,
            "avg_days_to_cert": avg_days_val,
            "overdue_count": len(overdue_assets),
            "due_soon_count": len(due_soon_assets),
        },
        "overdue_assets": overdue_assets,
        "due_soon_assets": due_soon_assets,
        "capa_open_list": capa_rows,
        "period": {"year": year, "month": month, "start": start, "end": end},
    }


def get_asset_history(asset: str, limit: int = 10) -> dict:
    rows, _ = CalibrationRepo.list(
        filters={"asset": asset},
        fields=["name", "calibration_type", "status", "scheduled_date",
                "actual_date", "overall_result", "next_calibration_date",
                "lab_supplier", "technician"],
        order_by="scheduled_date desc",
        page_size=int(limit),
    )
    return {"asset": asset, "history": rows}


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _normalize_list_filters(f: dict | None) -> dict:
    """Chuyển list literal thành ('in', list) để Frappe filter hiểu."""
    if not f:
        return {}
    op_tokens = ("in", "not in", "between", "like", "=", "!=", "<", ">", "<=", ">=")
    out: dict = {}
    for k, v in f.items():
        if isinstance(v, list) and v and not (len(v) == 2 and v[0] in op_tokens):
            out[k] = ["in", v]
        else:
            out[k] = v
    return out


def _failed_params(cal_doc) -> str:
    failed = [m.parameter_name for m in (cal_doc.measurements or []) if m.pass_fail == "Fail"]
    return ", ".join(failed) if failed else "unknown"
