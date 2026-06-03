# Copyright (c) 2026, AssetCore Team
# IMM-08 Preventive Maintenance — Tier 2 Business Service Layer.

from __future__ import annotations

import calendar

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, getdate, nowdate

from assetcore.repositories.asset_repo import AssetRepo, DeviceModelRepo
from assetcore.repositories.pm_repo import (
    PMChecklistTemplateRepo,
    PMScheduleRepo,
    PMTaskLogRepo,
    PMWorkOrderRepo,
)
from assetcore.repositories.repair_repo import RepairRepo
from assetcore.services.shared import AssetStatus, ErrorCode, ServiceError
from assetcore.utils.helpers import _get_role_emails, _safe_sendmail
from assetcore.utils.messages import MSG
from assetcore.utils.notify import nthrow, nthrow_in_hook

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


# SoT (BR-08-11): tập status nguồn mà cron được phép flip → Overdue. Các status
# còn lại (Completed, Cancelled, Halted–Major Failure, Overdue) là TERMINAL/đã-set,
# KHÔNG flip lại. Pending–Device Busy PHẢI nằm trong tập (WO bị hoãn vẫn quá hạn).
# is_pm_overdue ↔ cron (tasks.check_pm_overdue) ↔ counter (count_overdue_pm) đều
# suy từ hằng này — KHÔNG 3 nơi tự định nghĩa lại điều kiện quá hạn.
OVERDUE_SOURCE_STATES = frozenset({
    PMStatus.OPEN,
    PMStatus.IN_PROGRESS,
    PMStatus.PENDING_BUSY,
})
# Backward-compat alias (tên cũ dạng tuple — giữ cho callers hiện hữu).
OVERDUE_SOURCE_STATUSES = tuple(OVERDUE_SOURCE_STATES)


def is_pm_overdue(status: str, due_date, ref_date=None) -> bool:
    """SoT predicate (BR-08-11): 1 PM WO là 'quá hạn' khi NÀO?

    Định nghĩa duy nhất dùng chung cho: cron setter (``tasks.check_pm_overdue``),
    counter KPI/dashboard (``count_overdue_pm``) và drill-down list
    (``_normalize_filters(overdue=1)``) — KHÔNG 3 nơi tự định nghĩa lại.

    Boundary CHỐT: ``due_date < ref_date`` là quá hạn; ``due_date == ref_date``
    CHƯA quá hạn (đồng nhất giữa cron ``<`` và mọi consumer).

    Args:
        status: trạng thái PM Work Order hiện tại.
        due_date: ngày đến hạn (str/date) — None ⇒ không quá hạn.
        ref_date: mốc so sánh (mặc định hôm nay).

    Returns:
        True nếu WO ở status thuộc OVERDUE_SOURCE_STATES và due_date < ref_date.
    """
    if not due_date:
        return False
    if status not in OVERDUE_SOURCE_STATES:
        return False
    ref = getdate(ref_date) if ref_date else getdate(nowdate())
    return getdate(due_date) < ref


# SoT (BR-08-12): cửa-sổ "PM đến hạn (due-soon)". 1 hằng (KHÔNG hardcode "7"
# rải rác) + 1 helper filter dùng CHUNG bởi KPI count (dashboard.pm_due_next7)
# và drill list (_normalize_filters(due_before)). Đặt ngay cạnh OVERDUE SoT để
# 2 predicate (overdue/due-soon) ở cùng SoT block.
PM_DUE_SOON_WINDOW_DAYS = 7


def due_soon_filter(window_end, ref_date=None) -> dict:
    """SoT (BR-08-12): filter dict cho 'PM đến hạn (due-soon)'.

    Cửa sổ = ``[ref_date, window_end]`` (cả 2 biên inclusive). status NOT IN
    [Completed, Cancelled] (đến hạn ⇒ chưa hoàn tất). WO quá hạn
    (``due_date < ref_date``) NẰM NGOÀI — thuộc tập overdue (BR-08-11,
    ``is_pm_overdue``) → due-soon ∩ overdue = ∅ (disjoint by construction).

    INVARIANT: KPI ``dashboard.pm_due_next7`` (count) và drill
    ``_normalize_filters(due_before)`` (list) gọi CÙNG helper này → card ==
    drill byte-for-byte. Cận dưới = ref_date (mặc định hôm nay) — KHÔNG còn
    ``due_date <= window_end`` thiếu cận dưới (cũ làm WO quá hạn leak vào drill).

    Args:
        window_end: cận trên cửa sổ (str/date) — KPI truyền
            ``today + PM_DUE_SOON_WINDOW_DAYS``; drill truyền ``due_before``
            verbatim từ query.
        ref_date: cận dưới = mốc hôm nay (mặc định ``nowdate()``).

    Returns:
        dict: ``{"due_date": ["between", [ref, window_end]],
        "status": ["not in", [PMStatus.COMPLETED, PMStatus.CANCELLED]]}``
    """
    ref = ref_date or nowdate()
    return {
        "due_date": ["between", [ref, window_end]],
        "status": ["not in", [PMStatus.COMPLETED, PMStatus.CANCELLED]],
    }


class PMScheduleStatus:
    ACTIVE = "Active"
    PAUSED = "Paused"
    SUSPENDED = "Suspended"

    ALLOWED = (ACTIVE, PAUSED, SUSPENDED)


_LEGACY_ROLE_WORKSHOP = "PM Manager"
_LEGACY_ROLE_PTP = "Commissioning Manager"


# ─── KPI helper (RC-10 NextRound — single source of truth) ───────────────────
# Cả launcher widget VÀ /pm/dashboard VÀ /api/method/...dashboard.get_overview
# đều phải gọi hàm này để tránh dual-source (trước đây launcher đếm global,
# /pm/dashboard đếm theo month window → 1 vs 0).
def count_overdue_pm(user: str | None = None) -> int:
    """Đếm số PM Work Order đang ở trạng thái Overdue.

    SoT (BR-08-11): status Overdue do cron ``check_pm_overdue`` set qua predicate
    ``is_pm_overdue``. Counter này đếm đúng tập đó (status == Overdue) → KPI ==
    drill-down ``_normalize_filters(overdue=1)``, KHÔNG divergence.

    Args:
        user: nếu set, chỉ đếm các WO assigned cho user đó. None = global.

    Returns:
        int — count toàn hệ thống (hoặc theo user nếu cung cấp).
    """
    filters: dict = {"status": PMStatus.OVERDUE}
    if user:
        filters["assigned_to"] = user
    return PMWorkOrderRepo.count(filters)

_MEASUREMENT_PASS_FAIL = "Pass/Fail"

_OP_TOKENS = ("in", "not in", "between", "like", "=", "!=", "<", ">", "<=", ">=")


def _normalize_filters(f: dict | None) -> dict:
    out: dict = {}
    due_before = None
    overdue = False
    for k, v in (f or {}).items():
        # R6 §9.4.3 — virtual date-window keys cho drill-down từ KPI pm_due_7d.
        # due_before → cửa-sổ due-soon [today, X] (SoT due_soon_filter, BR-08-12 —
        # KHÔNG còn `<= X` thiếu cận dưới); overdue → status == Overdue (SSOT:
        # cron check_pm_overdue set status, WO là operational record duy nhất —
        # CLAUDE.md §11, dashboard.py §RC-10).
        if k == "due_before":
            due_before = v
            continue
        if k == "overdue":
            overdue = str(v) in ("1", "true", "True", "yes")
            continue
        if isinstance(v, list) and v and not (len(v) == 2 and v[0] in _OP_TOKENS):
            out[k] = ["in", v]
        else:
            out[k] = v
    if overdue:
        out["status"] = PMStatus.OVERDUE
    elif due_before:
        # BR-08-12: cửa-sổ due-soon [today, due_before] dùng CHUNG SoT helper với
        # KPI pm_due_next7 → card == drill (cận dưới = today, KHÔNG `<=`). Explicit
        # status từ query (nếu có) THẮNG status từ helper (setdefault).
        window = due_soon_filter(due_before)
        out["due_date"] = window["due_date"]
        out.setdefault("status", window["status"])
    return out


def _month_range(year: int, month: int) -> tuple[str, str, int]:
    _, last_day = calendar.monthrange(year, month)
    return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last_day:02d}", last_day


# ─── DocType controller delegates ────────────────────────────────────────────

def validate_work_order(doc) -> None:
    """Validate PM Work Order — called from controller.validate().

    BR-08-08: all checklist items need results before completion.
    BR-08-06: high-risk devices require photo attachments.
    BR-08-02: corrective WO must reference an originating PM WO.
    """
    if doc.status in ("Completed", "Halted–Major Failure"):
        for item in (doc.checklist_results or []):
            if not item.result:
                # BR-08-08
                nthrow_in_hook(MSG.IMM08_CHECKLIST_INCOMPLETE, item=item.description)
        # BR-08-09: thời gian thực hiện phải > 0 phút khi hoàn thành PM.
        if not doc.duration_minutes or doc.duration_minutes <= 0:
            nthrow_in_hook(MSG.IMM08_DURATION_REQUIRED)
        # BR-08-10: phải gắn tem bảo trì trước khi hoàn thành PM.
        if not doc.pm_sticker_attached:
            nthrow_in_hook(MSG.IMM08_STICKER_REQUIRED)

    risk_class = AssetRepo.get_value(doc.asset_ref, "risk_classification") if doc.asset_ref else None
    # BR-08-06: dùng doc.get() — `attachments` (Attach Multiple) không được
    # new_doc khởi tạo như attribute, truy cập trực tiếp gây AttributeError.
    if risk_class in ("High", "Critical") and not doc.get("attachments"):
        # BR-08-06
        nthrow_in_hook(MSG.IMM08_PHOTO_REQUIRED, risk_class=risk_class)

    if doc.wo_type == "Corrective" and not doc.source_pm_wo:
        # BR-08-02
        nthrow_in_hook(MSG.IMM08_SOURCE_PM_REQUIRED)


def handle_work_order_submit(doc) -> None:
    """Execute post-submit lifecycle actions — called from controller.on_submit().

    Sets completion date/late flag, advances PM Schedule, syncs AC Asset fields,
    creates immutable PM Task Log, auto-creates CM WO and handles major failure.
    """
    from frappe.utils import date_diff as _date_diff, add_days as _add_days, nowdate as _nowdate

    doc.completion_date = _nowdate()
    if doc.due_date:
        doc.is_late = 1 if _date_diff(doc.completion_date, doc.due_date) > 0 else 0

    update_pm_schedule_after_completion(doc.pm_schedule, doc.completion_date)

    sched_interval = PMScheduleRepo.get_value(doc.pm_schedule, "pm_interval_days") or 0 if doc.pm_schedule else 0
    AssetRepo.set_values(doc.asset_ref, {
        "last_pm_date": doc.completion_date,
        "next_pm_date": _add_days(doc.completion_date, sched_interval),
    })

    days_late = _date_diff(doc.completion_date, doc.due_date) if doc.is_late else 0
    PMTaskLogRepo.create({
        "asset_ref": doc.asset_ref,
        "pm_work_order": doc.name,
        "pm_type": doc.pm_type,
        "completion_date": doc.completion_date,
        "technician": doc.assigned_to or frappe.session.user,
        "overall_result": doc.overall_result,
        "is_late": doc.is_late,
        "days_late": days_late,
        "next_pm_date": _add_days(doc.completion_date, sched_interval),
        "summary": doc.technician_notes or "",
    })

    has_minor = any(r.result == "Fail–Minor" for r in (doc.checklist_results or []))
    has_major = any(r.result == "Fail–Major" for r in (doc.checklist_results or []))

    if has_major:
        _create_cm_wo_from_failure(doc, priority="Critical")
        _transition_asset(doc.asset_ref, AssetStatus.OUT_OF_SERVICE, doc.name)
        PMWorkOrderRepo.set_values(doc.name, {"status": PMStatus.HALTED_MAJOR})
    elif has_minor:
        _create_cm_wo_from_failure(doc, priority="Medium")


def _create_cm_wo_from_failure(doc, priority: str) -> None:
    """Insert a Corrective PM Work Order referencing a failed PM WO."""
    from frappe.utils import nowdate as _nowdate
    failure_items = [
        r.description for r in (doc.checklist_results or [])
        if r.result in ("Fail–Minor", "Fail–Major")
    ]
    PMWorkOrderRepo.create({
        "asset_ref": doc.asset_ref,
        "pm_schedule": doc.pm_schedule,
        "pm_type": doc.pm_type,
        "wo_type": "Corrective",
        "source_pm_wo": doc.name,
        "status": PMStatus.OPEN,
        "due_date": _nowdate(),
        "technician_notes": "Tạo tự động từ PM failure. Lỗi: " + "; ".join(failure_items),
    })


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


def backfill_pm_schedules_for_due_assets() -> dict:
    """Scheduler daily: tạo PM Schedule cho AC Asset có next_pm_date đến hạn
    nhưng chưa có lịch PM Active (slide 08c — vá lỗ hổng auto-gen).

    Pipeline sẵn có (``generate_pm_work_orders_from_schedule``) chỉ lặp trên
    PM Schedule, bỏ sót thiết bị đã set ``next_pm_date`` mà chưa có lịch.
    Hàm này tạo PM Schedule (qua ``create_pm_schedule_from_asset``) để pipeline
    đang chạy nhặt tiếp ở lượt sau.

    Returns:
        dict thống kê ``{"created", "skipped", "errors", "names"}``.
    """
    today = getdate(nowdate())
    created, skipped, errors = [], [], []

    candidates = frappe.get_all(
        _DT_AC_ASSET,
        filters=[
            [_DT_AC_ASSET, "next_pm_date", "is", "set"],
            [_DT_AC_ASSET, "next_pm_date", "<=", str(today)],
        ],
        fields=["name"],
        limit_page_length=0,
    )

    for row in candidates:
        asset_name = row["name"]
        if PMScheduleRepo.exists({
            "asset_ref": asset_name,
            "status": PMScheduleStatus.ACTIVE,
        }):
            skipped.append(f"{asset_name}: đã có PM Schedule Active")
            continue
        try:
            asset_doc = frappe.get_doc(_DT_AC_ASSET, asset_name)
            sched_name = create_pm_schedule_from_asset(asset_doc)
            if sched_name:
                created.append(sched_name)
                from assetcore.services.imm00 import log_audit_event  # noqa: PLC0415
                log_audit_event(
                    asset=asset_name,
                    event_type="Maintenance",
                    actor=frappe.session.user,
                    ref_doctype=PMScheduleRepo.DOCTYPE,
                    ref_name=sched_name,
                    change_summary=(
                        f"PM Schedule {sched_name} auto backfill — thiết bị có "
                        "next_pm_date đến hạn nhưng chưa có lịch PM (slide 08c)"
                    ),
                )
            else:
                skipped.append(f"{asset_name}: không đủ điều kiện tạo lịch")
        except Exception as exc:  # noqa: BLE001
            frappe.log_error(
                frappe.get_traceback(),
                f"IMM-08 backfill PM Schedule failed: {asset_name}",
            )
            errors.append(f"{asset_name}: {exc}")

    frappe.db.commit()
    result = {
        "created": len(created),
        "skipped": len(skipped),
        "errors": len(errors),
        "names": created,
    }
    frappe.logger().info(f"IMM-08 backfill_pm_schedules_for_due_assets: {result}")
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
                "due_date", "completion_date", "assigned_to", "supervisor",
                "overall_result", "is_late", "source_pm_wo"],
        order_by="due_date asc",
        page=page, page_size=page_size,
    )
    asset_ids = {r["asset_ref"] for r in rows if r.get("asset_ref")}
    user_ids = {r["assigned_to"] for r in rows if r.get("assigned_to")}
    user_ids |= {r["supervisor"] for r in rows if r.get("supervisor")}
    if asset_ids:
        asset_rows = frappe.get_all(
            _DT_AC_ASSET, filters={"name": ["in", list(asset_ids)]},
            fields=["name", "asset_name", "location"])
        asset_map = {a.name: a for a in asset_rows}
        loc_ids = {a.get("location") for a in asset_rows if a.get("location")}
        if loc_ids:
            loc_rows = frappe.get_all(
                "AC Location", filters={"name": ["in", list(loc_ids)]},
                fields=["name", "location_name"])
            loc_map = {l.name: l.location_name for l in loc_rows}
        else:
            loc_map = {}
    else:
        asset_map = {}
        loc_map = {}
    if user_ids:
        user_rows = frappe.get_all(
            "User", filters={"name": ["in", list(user_ids)]},
            fields=["name", "full_name"])
        user_map = {u.name: u.full_name for u in user_rows}
    else:
        user_map = {}
    for r in rows:
        a = asset_map.get(r.get("asset_ref"))
        r["asset_name"] = (a.asset_name if a else None) or r.get("asset_ref") or ""
        r["location_name"] = (loc_map.get(a.location) if a and a.get("location") else "") or ""
        r["assigned_to_name"] = user_map.get(r.get("assigned_to"), r.get("assigned_to") or "")
        r["supervisor_name"] = user_map.get(r.get("supervisor"), r.get("supervisor") or "")
    return {"data": rows, "pagination": pg}


def get_work_order(name: str) -> dict:
    wo = PMWorkOrderRepo.get(name)
    if not wo:
        nthrow(MSG.IMM08_WO_NOT_FOUND, name=name)

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
        "assigned_to_name": frappe.db.get_value("User", wo.assigned_to, "full_name") if wo.assigned_to else "",
        "supervisor": wo.supervisor,
        "supervisor_name": frappe.db.get_value("User", wo.supervisor, "full_name") if wo.supervisor else "",
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
        nthrow(MSG.IMM08_WO_NOT_FOUND, name=name)
    if wo.status not in (PMStatus.OPEN, PMStatus.OVERDUE):
        nthrow(MSG.IMM08_BAD_STATE, state=wo.status)
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
        nthrow(MSG.IMM08_WO_NOT_FOUND, name=name)
    if wo.docstatus == 1:
        nthrow(MSG.IMM08_ALREADY_SUBMITTED)

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
    try:
        PMWorkOrderRepo.save(wo)
    except frappe.ValidationError as e:
        # BR-08-08/09/10 completion gate raised in controller.validate()
        raise ServiceError(ErrorCode.VALIDATION, str(e)) from e

    try:
        wo.submit()
    except ServiceError:
        raise
    except frappe.ValidationError as e:
        raise ServiceError(ErrorCode.VALIDATION, str(e)) from e
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
        nthrow(MSG.IMM08_WO_NOT_FOUND, name=pm_wo_name)

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
        nthrow(MSG.IMM08_WO_NOT_FOUND, name=name)
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
        nthrow(MSG.IMM08_SCHEDULE_NOT_FOUND, name=data["pm_schedule"])
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
    if data.get("supervisor"):
        doc.supervisor = data["supervisor"]
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
    # RC-10 (NextRound): KPI "Quá hạn" trên /pm/dashboard phải là count global
    # (status == "Overdue") khớp với launcher widget — tránh dual-source.
    # Trước đây chỉ đếm trong window tháng đang xem nên launcher (global) báo 1,
    # /pm/dashboard (month-bound) báo 0 cho WO quá hạn từ tháng trước.
    # Single source of truth: count_overdue_pm() (cùng hàm launcher gọi).
    overdue_count = count_overdue_pm()
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
            # RC-10: dùng count global (status == Overdue) thay vì len(overdue)
            # bị bó trong window tháng đang xem.
            "overdue": overdue_count,
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
        nthrow(MSG.IMM08_SCHEDULE_NOT_FOUND, name=name)
    return doc.as_dict()


def create_schedule(data: dict) -> dict:
    required = ("asset_ref", "pm_type", "pm_interval_days", "checklist_template")
    missing = [f for f in required if not data.get(f)]
    if missing:
        raise ServiceError(ErrorCode.VALIDATION,
                           f"Thiếu trường bắt buộc: {', '.join(missing)}")

    # NEG-10: chặn tạo PM Schedule cho thiết bị đã thanh lý / ngừng sử dụng.
    # `validate_asset_for_operations` raise frappe.ValidationError nếu asset ở
    # `Decommissioned` hoặc `Out of Service` (BR-00-05).
    from assetcore.services.imm00 import validate_asset_for_operations
    try:
        validate_asset_for_operations(data["asset_ref"])
    except frappe.exceptions.ValidationError as e:
        raise ServiceError(
            ErrorCode.BAD_STATE,
            f"NEG-10: Không thể tạo lịch bảo trì cho thiết bị '{data['asset_ref']}': {e}",
        ) from e

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
        nthrow(MSG.IMM08_SCHEDULE_NOT_FOUND, name=name)
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
        nthrow(MSG.IMM08_SCHEDULE_NOT_FOUND, name=name)
    PMScheduleRepo.set_values(name, {"status": status})
    frappe.db.commit()
    return {"name": name, "status": status}


def delete_schedule(name: str) -> dict:
    if not PMScheduleRepo.exists(name):
        nthrow(MSG.IMM08_SCHEDULE_NOT_FOUND, name=name)
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
    # Enrich: map asset_category (slug = AC Asset Category.name) → category_name (display).
    # Tránh FE hiển thị slug "Thiet-bi-Chan-doan-Hinh-anh" thay vì "Thiết bị chẩn đoán hình ảnh".
    cat_slugs = {r.get("asset_category") for r in rows if r.get("asset_category")}
    if cat_slugs:
        cat_map = dict(frappe.get_all(
            "AC Asset Category",
            filters={"name": ["in", list(cat_slugs)]},
            fields=["name", "category_name"],
            as_list=True,
        ))
        for r in rows:
            slug = r.get("asset_category")
            r["category_name"] = cat_map.get(slug) or slug or ""
    # BUG-014 fix: if stored template_name still contains the slug (e.g. seed data
    # "Checklist PM Quý — Thiet-bi-Chan-doan-Hinh-anh"), substitute the trailing
    # slug segment with the category display name for presentation purposes.
    for r in rows:
        tn = r.get("template_name") or ""
        slug = r.get("asset_category") or ""
        cat_display = r.get("category_name") or slug
        if slug and cat_display and slug != cat_display and tn.endswith(slug):
            r["display_template_name"] = tn[: -len(slug)] + cat_display
        else:
            r["display_template_name"] = tn
    return {"data": rows, "pagination": pg}


def get_template(name: str) -> dict:
    doc = PMChecklistTemplateRepo.get(name)
    if not doc:
        nthrow(MSG.IMM08_TEMPLATE_NOT_FOUND, name=name)
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
        nthrow(MSG.IMM08_TEMPLATE_NOT_FOUND, name=name)
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
        nthrow(MSG.IMM08_TEMPLATE_NOT_FOUND, name=name)
    PMChecklistTemplateRepo.set_values(name, {"approved_by": frappe.session.user})
    frappe.db.commit()
    return {"name": name, "approved_by": frappe.session.user}


def version_template(source_name: str, new_version: str) -> dict:
    src = PMChecklistTemplateRepo.get(source_name)
    if not src:
        nthrow(MSG.IMM08_TEMPLATE_NOT_FOUND, name=source_name)
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


def apply_template_to_category_assets(template_name: str) -> dict:
    """Bulk-tạo PM Schedule cho mọi AC Asset thuộc danh mục của template.

    Logic:
        - Bỏ qua asset đã Decommissioned/Disposed.
        - Bỏ qua asset đã có PM Schedule cùng pm_type (giữ nguyên lịch hiện hữu).
        - Lấy pm_interval_days từ AC Asset Category.default_pm_interval_days
          (fallback 180 nếu trống).
        - PM Schedule mới sẽ tự kích hoạt on_update → tạo WO nếu đến hạn.
    """
    template = PMChecklistTemplateRepo.get(template_name)
    if not template:
        nthrow(MSG.IMM08_TEMPLATE_NOT_FOUND, name=template_name)
    if not template.asset_category:
        raise ServiceError(ErrorCode.VALIDATION,
                           "Template chưa gán Danh mục tài sản")
    category_defaults = frappe.db.get_value(
        "AC Asset Category", template.asset_category,
        ["default_pm_required", "default_pm_interval_days"],
        as_dict=True,
    ) or {}
    interval = int(category_defaults.get("default_pm_interval_days") or 180)

    assets = frappe.get_all(
        "AC Asset",
        filters={
            "asset_category": template.asset_category,
            "lifecycle_status": ["not in", ["Decommissioned", "Disposed"]],
        },
        fields=["name", "commissioning_date"],
        limit_page_length=10_000,
    )
    created, skipped, errors = [], [], []
    for asset in assets:
        if PMScheduleRepo.exists({"asset_ref": asset["name"], "pm_type": template.pm_type}):
            skipped.append(asset["name"])
            continue
        try:
            base_date = asset.get("commissioning_date") or nowdate()
            payload = {
                "asset_ref": asset["name"],
                "pm_type": template.pm_type,
                "pm_interval_days": interval,
                "checklist_template": template.name,
                "alert_days_before": 7,
                "status": PMScheduleStatus.ACTIVE,
                "last_pm_date": base_date,
                "next_due_date": add_days(getdate(base_date), interval),
            }
            doc = PMScheduleRepo.create(payload, ignore_permissions=True)
            created.append(doc.name)
        except Exception as exc:
            frappe.log_error(frappe.get_traceback(),
                             f"apply_template_to_category_assets {asset['name']}")
            errors.append(f"{asset['name']}: {exc}")
    frappe.db.commit()
    return {
        "template": template.name,
        "asset_category": template.asset_category,
        "total_assets": len(assets),
        "created": len(created),
        "skipped_existing": len(skipped),
        "errors": len(errors),
    }


def delete_template(name: str) -> dict:
    if not PMChecklistTemplateRepo.exists(name):
        nthrow(MSG.IMM08_TEMPLATE_NOT_FOUND, name=name)
    try:
        PMChecklistTemplateRepo.delete(name, ignore_permissions=False)
        frappe.db.commit()
    except (frappe.ValidationError, frappe.LinkExistsError) as e:
        raise ServiceError(ErrorCode.CONFLICT, str(e)) from e
    return {"name": name, "deleted": True}


# ─── Hook từ IMM-04 Commissioning ────────────────────────────────────────────

_PM_TYPE_FROM_INTERVAL = [(91, "Quarterly"), (183, "Semi-Annual"), (366, "Annual")]


def _resolve_checklist_template(asset_category: str | None, pm_type: str) -> str | None:
    """Tìm PM Checklist Template khớp danh mục — ưu tiên đúng pm_type, fallback
    bất kỳ template cùng danh mục."""
    if not asset_category:
        return None
    return (
        frappe.db.get_value(
            "PM Checklist Template",
            {"asset_category": asset_category, "pm_type": pm_type},
            "name",
        )
        or frappe.db.get_value(
            "PM Checklist Template", {"asset_category": asset_category}, "name"
        )
    )


def create_pm_schedule_from_asset(asset_doc, method: str | None = None) -> str | None:
    """Hook: AC Asset after_insert → tạo PM Schedule nếu user tick `is_pm_required`.

    Tham số ``method`` để tương thích chữ ký doc-event của Frappe
    (``after_insert`` truyền ``(doc, method)``); không dùng trong logic.

    Cho phép tạo lịch bảo trì NGAY khi tạo tài sản trực tiếp (không bắt buộc
    qua luồng Commissioning). Điều kiện:
        - asset_doc.is_pm_required = 1
        - Có PM Checklist Template cho asset_category (nếu chưa có → bỏ qua,
          KHÔNG throw để tránh vỡ thao tác tạo asset).
        - Chưa tồn tại PM Schedule cùng pm_type cho asset (tránh trùng).
    """
    if not getattr(asset_doc, "is_pm_required", 0):
        return None

    interval = int(asset_doc.get("pm_interval_days") or 0)
    if interval <= 0:
        # Fallback từ Device Model nếu asset chưa nhập chu kỳ.
        device_model = asset_doc.get("device_model")
        if device_model:
            interval = int(
                DeviceModelRepo.get_value(device_model, "pm_interval_days") or 0
            )
    if interval <= 0:
        interval = 365  # mặc định an toàn — 1 năm

    pm_type = next((t for days, t in _PM_TYPE_FROM_INTERVAL if interval <= days), "Annual")

    if PMScheduleRepo.exists({"asset_ref": asset_doc.name, "pm_type": pm_type}):
        return None

    checklist_template = _resolve_checklist_template(
        asset_doc.get("asset_category"), pm_type
    )
    if not checklist_template:
        frappe.logger().warning(
            f"IMM-08: bỏ qua tạo PM Schedule cho {asset_doc.name} — chưa có PM "
            f"Checklist Template cho danh mục '{asset_doc.get('asset_category')}'."
        )
        return None

    base_date = (
        asset_doc.get("last_pm_date")
        or asset_doc.get("commissioning_date")
        or asset_doc.get("purchase_date")
        or nowdate()
    )
    try:
        sched = PMScheduleRepo.create({
            "asset_ref": asset_doc.name,
            "pm_type": pm_type,
            "pm_interval_days": interval,
            "alert_days_before": 7,
            "checklist_template": checklist_template,
            "status": PMScheduleStatus.ACTIVE,
            "last_pm_date": base_date,
            "next_due_date": add_days(getdate(base_date), interval),
        }, ignore_permissions=True)
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            f"IMM-08 create_pm_schedule_from_asset failed: {asset_doc.name}",
        )
        return None

    from assetcore.services.imm00 import log_audit_event  # noqa: PLC0415
    log_audit_event(
        asset=asset_doc.name, event_type="Maintenance",
        actor=frappe.session.user,
        ref_doctype=PMScheduleRepo.DOCTYPE, ref_name=sched.name,
        change_summary=f"PM Schedule {sched.name} auto từ tạo tài sản (is_pm_required) — {pm_type}, {interval} ngày",
    )
    frappe.logger().info(
        f"IMM-08 PM Schedule {sched.name} tạo tự động từ AC Asset {asset_doc.name}"
    )
    return sched.name


def create_pm_schedule_from_commissioning(
    commissioning_doc, method: str | None = None
) -> str | None:
    """Hook: Asset Commissioning on_submit → tạo PM Schedule nếu thiết bị yêu cầu PM.

    ``method`` để tương thích chữ ký doc-event Frappe ``(doc, method)``.
    """
    asset = commissioning_doc.final_asset
    if not asset:
        return None
    device_model = AssetRepo.get_value(asset, "device_model")
    if not device_model:
        return None
    model = DeviceModelRepo.get_value(
        device_model,
        ["is_pm_required", "pm_interval_days", "pm_alert_days"],
        as_dict=True,
    )
    if not model or not model.get("is_pm_required"):
        return None
    interval = int(model.get("pm_interval_days") or 365)
    alert_days = int(model.get("pm_alert_days") or 7)
    pm_type = next((t for days, t in _PM_TYPE_FROM_INTERVAL if interval <= days), "Annual")
    base_date = commissioning_doc.commissioning_date or nowdate()

    # checklist_template là BẮT BUỘC (PMSchedule.validate throw nếu trống) — phải
    # tìm template khớp asset_category + pm_type, nếu không có thì bỏ qua lịch
    # thay vì để exception làm vỡ on_submit của Asset Commissioning.
    asset_category = AssetRepo.get_value(asset, "asset_category")
    checklist_template = None
    if asset_category:
        checklist_template = (
            frappe.db.get_value(
                "PM Checklist Template",
                {"asset_category": asset_category, "pm_type": pm_type},
                "name",
            )
            or frappe.db.get_value(
                "PM Checklist Template", {"asset_category": asset_category}, "name"
            )
        )
    if not checklist_template:
        frappe.logger().warning(
            f"IMM-08: bỏ qua tạo PM Schedule cho {asset} — chưa có PM Checklist "
            f"Template cho danh mục '{asset_category}'."
        )
        return None

    sched = PMScheduleRepo.create({
        "asset_ref": asset,
        "pm_type": pm_type,
        "pm_interval_days": interval,
        "alert_days_before": alert_days,
        "checklist_template": checklist_template,
        "status": PMScheduleStatus.ACTIVE,
        "last_pm_date": base_date,
        "next_due_date": add_days(base_date, interval),
        "created_from_commissioning": commissioning_doc.name,
    })
    from assetcore.services.imm00 import log_audit_event  # noqa: PLC0415
    log_audit_event(
        asset=asset, event_type="Maintenance",
        actor=frappe.session.user,
        ref_doctype=PMScheduleRepo.DOCTYPE, ref_name=sched.name,
        change_summary=f"PM Schedule {sched.name} auto từ commissioning {commissioning_doc.name}",
    )
    frappe.logger().info(f"IMM-08 PM Schedule {sched.name} tạo từ commissioning {commissioning_doc.name}")
    return sched.name
