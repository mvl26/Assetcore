# Copyright (c) 2026, AssetCore Team
# IMM-08 Preventive Maintenance — Tier 2 Business Service Layer.

from __future__ import annotations

import calendar

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, getdate, nowdate
from PIL import UnidentifiedImageError

from assetcore.repositories.asset_repo import AssetRepo, DeviceModelRepo
from assetcore.repositories.pm_repo import (
    PMChecklistTemplateRepo,
    PMScheduleRepo,
    PMTaskLogRepo,
    PMWorkOrderRepo,
)
from assetcore.repositories.repair_repo import RepairRepo
from assetcore.services.shared import AssetStatus, ErrorCode, ServiceError
from assetcore.services.shared.errors import validation
from assetcore.utils.idempotency import resolve_idempotency_key
from assetcore.services.shared.filters import pop_search
from assetcore.utils.helpers import _get_role_emails, _safe_sendmail
from assetcore.utils.messages import MSG
from assetcore.utils.notify import nthrow, nthrow_in_hook
from assetcore.utils.pagination import _MAX_PAGE_SIZE, paginate

_DT_PM_WO = "PM Work Order"
_DT_AC_ASSET = "AC Asset"
_DT_PM_CHECKLIST_ROW = "PM Checklist Result"
_DT_FILE = "File"

# BR-08-14 (mobile CR-14/G6): đính ảnh bằng chứng theo TỪNG mục checklist PM (NĐ98
# Class C/D). ĐỐI XỨNG attach_incident_photo (imm12) — KHÁC module/doctype/field.
# Field `pm_checklist_result.photo` là Attach ĐƠN ⇒ đúng 1 ảnh / mục checklist; SoT
# đếm max = row.photo (CÙNG field get_work_order hiển thị) ⇒ invariant count==nguồn-
# liệt-kê (KHÔNG lệch, mirror _scene_photos Vòng 1). Content-type allowlist JPG/PNG;
# size cap 10 MB (parity mobile + attach_incident_photo).
MAX_PM_CHECKLIST_PHOTOS = 1
MAX_PM_CHECKLIST_PHOTO_BYTES = 10 * 1024 * 1024
_PM_PHOTO_CONTENT_TYPES = ("image/jpeg", "image/jpg", "image/png")
_EVENT_PM_CHECKLIST_PHOTO_ATTACHED = "pm_checklist_photo_attached"

# Field-level validation messages (VN) — nhánh reject Decision-B (fields.file). Hằng
# số hiển thị (đối xứng _MSG_PHOTO_* imm12); KHÔNG leak raw cap/stack.
_MSG_PM_PHOTO_MISSING = "Thiếu tệp ảnh"
_MSG_PM_PHOTO_NOT_IMAGE = "Tệp phải là ảnh JPG hoặc PNG"
_MSG_PM_PHOTO_TOO_LARGE = "Ảnh vượt quá dung lượng cho phép (tối đa 10 MB)"
_MSG_PM_PHOTO_MAX = "Mỗi mục checklist chỉ đính 1 ảnh"
_MSG_PM_PHOTO_FORBIDDEN = "Không có quyền đính ảnh cho lệnh bảo trì định kỳ này"
_MSG_PM_PHOTO_IDX_NOT_FOUND = "Không tìm thấy mục checklist trong lệnh bảo trì này"
# Ảnh HỎNG/ĐỨT TRUYỀN: content-type hợp lệ nhưng bytes không giải mã được (KTV chụp
# hiện trường wifi/4G chập chờn) → PIL ném UnidentifiedImageError/OSError khi strip EXIF.
_MSG_PM_PHOTO_CORRUPT = "Tệp ảnh bị lỗi hoặc không đọc được, vui lòng chụp/chọn lại."


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


# ─── State machine (server-driven CTA) ─────────────────────────────────────────
# SSoT trạng-thái-kế-hợp-lệ cho PM Work Order — GROUNDED CHÍNH XÁC
# assetcore/assetcore/workflow/imm_08_pm_workflow.json (7 state / 13 transition).
# Mỗi value = tập next_state hợp lệ từ key-state (đọc thẳng từ field `next_state`
# của khối `transitions` trong workflow JSON). get_work_order emit field này vào
# detail dict → màn PM-detail mobile RENDER nút workflow theo server (server-driven
# CTA) THAY VÌ hardcode status→button phía client (anti-pattern RBAC/lifecycle
# dead-gate — memory factory_rounds_1_25). MIRROR imm12._VALID_TRANSITIONS (R3).
#
# Terminal Completed (doc_status=1) / Cancelled → [] (rỗng): KHÔNG transition ra.
# KHÔNG bịa state ngoài enum PMStatus + workflow JSON. Parity-guard (test) chốt:
#   (1) mọi giá trị sinh ra ∈ PMStatus enum (chống typo state);
#   (2) map == next_state trong imm_08_pm_workflow.json (chống drift map↔workflow).
_PM_VALID_TRANSITIONS: dict[str, list[str]] = {
    PMStatus.OPEN: [PMStatus.IN_PROGRESS, PMStatus.OVERDUE, PMStatus.CANCELLED],
    PMStatus.OVERDUE: [PMStatus.IN_PROGRESS, PMStatus.CANCELLED],
    PMStatus.IN_PROGRESS: [
        PMStatus.COMPLETED,
        PMStatus.HALTED_MAJOR,
        PMStatus.PENDING_BUSY,
        PMStatus.CANCELLED,
    ],
    PMStatus.PENDING_BUSY: [PMStatus.IN_PROGRESS, PMStatus.CANCELLED],
    PMStatus.HALTED_MAJOR: [PMStatus.IN_PROGRESS, PMStatus.CANCELLED],
    PMStatus.COMPLETED: [],
    PMStatus.CANCELLED: [],
}


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


# SoT (BR-08-03): "Ngày PM kế tiếp" (next_pm_date / next_due_date). 1 hằng default
# + 1 helper pure dùng CHUNG bởi MỌI write-site (update_pm_schedule_after_completion
# → PM Schedule.next_due_date; handle_work_order_submit → AC Asset.next_pm_date +
# PM Task Log.next_pm_date; submit_result → field API trả về). KHÔNG 3+ nơi tự
# inline add_days(...) (trước đây trôi thành 3 bản phân kỳ: anchor nowdate-vs-
# completion + default or-0-vs-or-90).
PM_DEFAULT_INTERVAL_DAYS = 90


def compute_next_pm_date(completion_date, interval: int | None = None) -> str:
    """SoT DUY NHẤT (BR-08-03): ngày PM kế tiếp = completion_date + interval hiệu lực.

    INVARIANT anchor: LUÔN dùng ``completion_date`` (mốc hoàn thành thực tế của WO),
    KHÔNG bao giờ ``nowdate()``. Khi PM hoàn thành trễ/backdated
    (``completion_date != today``), giá trị này phải bằng nhau byte-for-byte ở MỌI
    nơi: ``PM Schedule.next_due_date`` (persist), ``AC Asset.next_pm_date``,
    ``PM Task Log.next_pm_date``, và field ``next_pm_date`` mà ``submit_result`` trả
    về API.

    INVARIANT default: interval hiệu lực = ``interval`` nếu ``interval and
    interval > 0``, else ``PM_DEFAULT_INTERVAL_DAYS`` (=90). Khi ``pm_interval_days``
    rỗng/0/None, schedule — asset — API CÙNG nhảy +90 ngày → asset KHÔNG còn lập tức
    bị scheduler coi là PM-overdue giả trong khi schedule báo còn 90 ngày.

    Args:
        completion_date: mốc hoàn thành WO (str/date) — anchor BẮT BUỘC.
        interval: ``pm_interval_days`` THÔ từ PM Schedule (có thể rỗng/0/None) —
            việc chọn default 90 nằm DUY NHẤT trong hàm này, KHÔNG ở call-site.

    Returns:
        str: ngày PM kế tiếp (``add_days(getdate(completion_date), effective)``).
    """
    effective = interval if interval and interval > 0 else PM_DEFAULT_INTERVAL_DAYS
    # str() để honor contract `-> str` (FE render verbatim) + đảm bảo parity
    # byte-for-byte: AssetRepo/PMTaskLog persist Date, DB get_value trả date →
    # str() đồng nhất một kiểu chuỗi ISO ở MỌI write-site/đọc.
    return str(add_days(getdate(completion_date), effective))


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


def _pm_scheduled(rows: list[dict]) -> list[dict]:
    """SoT (BR-08-14 / INV-PM-KPI-6): MẪU tuân thủ = WO trong cửa-sổ tháng có
    ``status != Cancelled``.

    1 predicate DUY NHẤT dùng CHUNG bởi tile-tháng (``get_dashboard_stats`` khối
    THÁNG) VÀ ``trend_6months[*].rate`` → cùng SoT, KHÔNG 2 nơi tự định nghĩa lại
    (tránh trend lệch chuẩn so với tile compliance).

    Vì sao loại Cancelled: WO ``Cancelled`` = nghĩa vụ bảo trì bị VOID hành chính
    (hủy chủ động, hết nghĩa vụ thực hiện) — nhất quán với ``count_overdue_pm`` đã
    loại ``[Completed, Cancelled]`` và ``due_soon_filter`` đã loại Cancelled. Để
    Cancelled trong mẫu sẽ (a) phình mẫu → kéo ``compliance_rate_pct`` giả tụt;
    (b) đẩy Cancelled vào ``pending_in_month`` thành phantom 'chưa xong'.

    RANH GIỚI: CHỈ ``Cancelled`` bị loại. ``Halted–Major Failure`` GIỮ counted
    (kết cục PM non-compliant THẬT — thiết bị hỏng nặng, nghĩa vụ KHÔNG bị void).

    Args:
        rows: list WO dict (cần khóa ``status``) trong cửa-sổ tháng.

    Returns:
        list[dict]: subset rows với ``status != PMStatus.CANCELLED``.
    """
    return [w for w in rows if w["status"] != PMStatus.CANCELLED]


# ─── DocType controller delegates ────────────────────────────────────────────

def validate_work_order(doc) -> None:
    """Validate PM Work Order — called from controller.validate().

    BR-08-08: all checklist items need results before completion.
    BR-08-06: high-risk devices require photo attachments.
    BR-08-02: corrective WO must reference an originating PM WO.
    """
    if doc.status in ("Completed", "Halted–Major Failure"):
        # BR-08-08 (fix chính): bảng kiểm RỖNG → chặn nghiệm-thu-giả. Guard PHẢI đứng
        # TRƯỚC vòng for — trên list rỗng vòng for là VACUOUS (không kiểm gì) nên WO
        # template-less (0 checklist row) sẽ hoàn thành GIẢ (Completed + PM Task Log
        # không có bằng chứng công việc). Đây là lưới an toàn SSoT: mọi path save
        # status=Completed đều qua validate() → không cần ép template ở create.
        if not (doc.checklist_results or []):
            nthrow_in_hook(MSG.IMM08_CHECKLIST_EMPTY)
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
    from frappe.utils import date_diff as _date_diff, nowdate as _nowdate

    doc.completion_date = _nowdate()
    if doc.due_date:
        doc.is_late = 1 if _date_diff(doc.completion_date, doc.due_date) > 0 else 0

    update_pm_schedule_after_completion(doc.pm_schedule, doc.completion_date)

    # BR-08-03: pm_interval_days THÔ (có thể rỗng/0/None) → SoT compute_next_pm_date
    # chọn default. KHÔNG fallback-literal ở call-site (việc chọn default nằm trong helper).
    sched_interval = PMScheduleRepo.get_value(doc.pm_schedule, "pm_interval_days") if doc.pm_schedule else None
    next_pm_date = compute_next_pm_date(doc.completion_date, sched_interval)
    AssetRepo.set_values(doc.asset_ref, {
        "last_pm_date": doc.completion_date,
        "next_pm_date": next_pm_date,
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
        "next_pm_date": next_pm_date,
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
    # BR-08-03: dùng SoT compute_next_pm_date (anchor=completion_date, default trong
    # helper). Đây là path ĐÚNG sẵn — qua SoT để dedup, KHÔNG inline add_days nữa.
    sched.next_due_date = compute_next_pm_date(completion_date, sched.pm_interval_days)
    PMScheduleRepo.save(sched)


# ─── Business operations — Work Order ────────────────────────────────────────

# Fields fetch cho list PM Work Order — SoT DUY NHẤT (path chính + filter LIVE
# `_list_pm_overdue_live` dùng CHUNG). Gồm cột predicate overdue (`status`/
# `due_date`) để `_enrich_pm_overdue` derive `is_overdue` in-Python (no N+1).
# 1 nguồn ⇒ 2 path enrich khớp byte-for-byte.
_PM_LIST_FIELDS = [
    "name", "asset_ref", "pm_type", "wo_type", "status",
    "due_date", "completion_date", "assigned_to", "supervisor",
    "overall_result", "is_late", "source_pm_wo",
]


def _enrich_pm_list_rows(rows: list[dict]) -> None:
    """Enrich list PM WO rows với asset_name/location_name/assigned_to_name/
    supervisor_name (dùng CHUNG path chính + filter LIVE `overdue_live`). Extract
    nguyên khối enrich cũ của ``list_work_orders`` → 2 path trả cùng shape row."""
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


def _enrich_pm_overdue(rows: list[dict], ref_date=None) -> None:
    """SoT (BR-08-11) LIVE badge: gán ``is_overdue`` (bool) cho mỗi row list PM WO.

    ``is_overdue = (status == Overdue)`` [cron nightly ĐÃ stamp — giữ superset
    monotonic, KHÔNG mất phiếu chip cũ] ``OR is_pm_overdue(status, due_date, ref)``
    [LIVE: ``due_date < today`` ∧ ``status ∈ OVERDUE_SOURCE_STATES``]. REUSE SoT
    predicate ``is_pm_overdue`` (KHÔNG fork định nghĩa quá hạn).

    Áp trên CẢ 2 path (list thường + filter LIVE) ⇒ badge FE đọc field derived
    ``is_overdue`` khớp membership filter ``overdue_live`` mọi path (cron-independent).
    ``ref`` tính 1 lần (KHÔNG nowdate() lặp per-row)."""
    ref = getdate(ref_date) if ref_date else getdate(nowdate())
    for r in rows:
        status = r.get("status")
        r["is_overdue"] = bool(
            status == PMStatus.OVERDUE
            or is_pm_overdue(status, r.get("due_date"), ref)
        )


def _fetch_all_pm_rows(filters: dict, *, or_filters: list | None = None) -> list[dict]:
    """Fetch TOÀN tập PM Work Order khớp ``filters`` (+ ``or_filters`` free-text
    search) — UNCLAMPED (loop-paginate qua từng trang ``_MAX_PAGE_SIZE`` tới hết
    tập).

    CR-18: ``or_filters`` (search OR-LIKE) truyền xuống ``PMWorkOrderRepo.list``
    ⇒ membership LIVE (chip 'Quá hạn') vẫn AND với search — count==rows giữ
    (``count_with_or`` + ``get_all`` dùng CÙNG ``or_filters``). ``None`` ⇒ nhánh
    cũ byte-identical.

    ⚠ KHÔNG truyền ``page_size`` khổng lồ 1 lần (bị ``paginate`` clamp im lặng về
    ``_MAX_PAGE_SIZE=100`` = BUG scale imm09 R2: membership < badge khi >100 phiếu
    quá hạn). Loop tích luỹ + termination theo ``pg["total_pages"]`` (từ total đã
    đếm ở tầng Repo) ⇒ predicate LIVE áp trên TOÀN tập permission/vendor-scoped
    (scope nằm trong ``filters`` — đã ``_normalize_filters`` ở call-site). Order
    ``due_date asc`` khớp path chính ``list_work_orders``."""
    all_rows: list[dict] = []
    page = 1
    total_pages = 1
    while page <= total_pages:
        rows, pg = PMWorkOrderRepo.list(
            filters=filters,
            or_filters=or_filters,
            fields=_PM_LIST_FIELDS,
            order_by="due_date asc",
            page=page, page_size=_MAX_PAGE_SIZE,
        )
        all_rows.extend(rows)
        total_pages = pg["total_pages"]
        page += 1
    return all_rows


def _list_pm_overdue_live(base_filters: dict, *, or_filters: list | None = None,
                          page: int = 1, page_size: int = 20) -> dict:
    """BR-08-11 LIVE membership filter cho chip mobile 'Quá hạn' PM.

    Trả CHỈ PM WO có ``is_overdue == True`` — DERIVED LIVE: (``status == Overdue``,
    cron ĐÃ stamp) OR ``is_pm_overdue(status, due_date, today)`` (``due_date <
    hôm nay`` ∧ ``status ∈ OVERDUE_SOURCE_STATES``). CÙNG predicate
    ``_enrich_pm_overdue`` (badge row). INVARIANT: membership filter == badge —
    chip lọc PHẢI khớp badge, KHÔNG lọc theo cột STORED ``status == Overdue`` đơn
    thuần (cron nightly stamp trễ ⇒ WO ``due_date < today`` mà status vẫn Open/In
    Progress MISS filter nhưng badge HIỆN = mismatch phá niềm tin KTV).

    ``is_overdue`` KHÔNG phải cột DB (derived in-Python) ⇒ KHÔNG filter được ở SQL
    → fetch UNCLAMPED TOÀN tập permission-scoped (``_fetch_all_pm_rows`` loop-
    paginate — GIỮ vendor-scope + ``mine`` + ``status`` base filters qua
    ``_normalize_filters``) → enrich → filter LIVE → paginate IN-PYTHON trên tập ĐÃ
    LỌC (``pagination.total`` == số overdue thực, KHÔNG cap 100). Order ``due_date
    asc`` như path chính."""
    all_rows = _fetch_all_pm_rows(_normalize_filters(base_filters), or_filters=or_filters)
    _enrich_pm_overdue(all_rows)
    overdue = [r for r in all_rows if r.get("is_overdue")]
    pg = paginate(len(overdue), page, page_size)
    page_rows = overdue[pg["offset"]:pg["offset"] + pg["page_size"]]
    _enrich_pm_list_rows(page_rows)
    return {"data": page_rows, "pagination": pg}


def list_work_orders(filters: dict, *, page: int = 1, page_size: int = 20) -> dict:
    # POP cờ ảo `overdue_live` TRƯỚC _normalize_filters (mirror imm09
    # list_work_orders POP `sla_breached_live`) — tránh đẩy 1 cột KHÔNG tồn tại
    # (`overdue_live`) vào frappe.get_all. Truthy → nhánh membership LIVE (chip
    # 'Quá hạn' PM); absent/falsy → path CŨ byte-identical baseline.
    base = dict(filters or {})
    want_overdue_live = base.pop("overdue_live", None)
    # CR-18: free-text search server-side. POP cờ ảo `search` → OR-LIKE trên
    # (name = mã phiếu / asset_ref = mã thiết bị) + link_search asset_name (AC
    # Asset). Chạy SAU pop overdue_live ⇒ AND với column-filters + vendor-scope +
    # mine (đã là cột thật trong `base`). count_with_or (qua Repo.list) dùng CÙNG
    # or_filters ⇒ bất biến count==rows GIỮ. search absent/rỗng ⇒ or_filters=None
    # ⇒ path CŨ byte-identical baseline. Wildcard %/_ escape-literal (pop_search).
    base, or_filters = pop_search(
        base,
        ["name", "asset_ref"],
        link_search={"asset_ref": ("AC Asset", "asset_name")},
        escape_wildcards=True,   # CR-18: %/_ user gõ = literal (chống match-all/DoS)
    )
    if str(want_overdue_live) in ("1", "True", "true", "yes"):
        return _list_pm_overdue_live(base, or_filters=or_filters, page=page, page_size=page_size)
    rows, pg = PMWorkOrderRepo.list(
        filters=_normalize_filters(base),
        or_filters=or_filters,
        fields=_PM_LIST_FIELDS,
        order_by="due_date asc",
        page=page, page_size=page_size,
    )
    _enrich_pm_list_rows(rows)
    # BR-08-11 LIVE: derive per-row `is_overdue` (status==Overdue OR live-overdue)
    # ⇒ drill/list hiển thị badge 'Quá hạn' LIVE khớp filter overdue_live
    # (badge == membership mọi path, cron-independent). In-Python, KHÔNG query thêm.
    _enrich_pm_overdue(rows)
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

    # CR-37 (mobile parity list↔detail, cận an-toàn người bệnh): phơi cờ LIVE
    # `is_overdue` (Python bool) BÊN CẠNH `is_late` (STORED) — badge 'Quá hạn' màn
    # PM-detail KHÔNG trễ 1 nhịp cron `check_pm_overdue`. DÙNG CHUNG SoT predicate
    # `_enrich_pm_overdue` với list-item (status==Overdue OR is_pm_overdue LIVE) ⇒
    # cờ detail == cờ list-item cùng record (INVARIANT). Predicate đọc ĐÚNG 2 field
    # {status, due_date} → dựng 1 row rồi enrich (KHÔNG fork định nghĩa quá hạn).
    _ovd_row = {"status": wo.status, "due_date": wo.due_date}
    _enrich_pm_overdue([_ovd_row])

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
        # CR-37: cờ LIVE quá-hạn (Python bool, CÙNG predicate _enrich_pm_overdue của
        # list-item). GIỮ is_late (STORED) nguyên — 2 cờ khác nghĩa (trễ-hoàn-thành
        # vs chưa-xong-quá-hạn).
        "is_overdue": _ovd_row["is_overdue"],
        "duration_minutes": wo.duration_minutes,
        "source_pm_wo": wo.source_pm_wo,
        # Server-driven CTA (mirror imm12.get_incident_detail:778) — màn PM-detail
        # render nút workflow theo tập này, KHÔNG hardcode status→button client-side.
        "allowed_transitions": _PM_VALID_TRANSITIONS.get(wo.status, []),
        "checklist_results": checklist,
    }


def _find_checklist_row(wo, checklist_item_idx: int):
    """Trả row `PM Checklist Result` khớp `checklist_item_idx` (STT mục — field domain,
    KHÔNG phải Frappe child `idx`). None nếu không tồn tại → nhánh reject VALIDATION.
    Nguồn = wo.checklist_results (đã load 1 lần) ⇒ KHÔNG N+1."""
    for row in (wo.checklist_results or []):
        if int(row.checklist_item_idx or 0) == int(checklist_item_idx):
            return row
    return None


def _checklist_item_photos(row) -> list:
    """SoT DUY NHẤT ảnh/mục checklist (BR-08-14) — đọc `row.photo` (Attach ĐƠN).

    Trả `[{file_url}]` khi đã có ảnh, `[]` khi chưa. CÙNG nguồn mà get_work_order
    hiển thị (`checklist_results[].photo`) VỪA đếm max-count ⇒ invariant count==nguồn-
    liệt-kê (số chặn ảnh-thứ-2 == số hiển thị, mirror _scene_photos imm12)."""
    return [{"file_url": row.photo}] if row.photo else []


def _assert_can_attach_pm_photo(wo) -> None:
    """BR-08-14 permission: KTV được giao (`assigned_to`) HOẶC `pm.write` trên chính WO.

    `frappe.has_permission(doc=...)` áp CẢ role-DocPerm write LẪN row-level hook ⇒ tái
    dùng vendor/scope guard. KTV assignee luôn đính được ảnh phiếu của mình (bằng chứng
    hiện trường do chính họ thực hiện) — đối xứng reporter trong attach_incident_photo."""
    user = frappe.session.user
    if wo.assigned_to and wo.assigned_to == user:
        return
    if frappe.has_permission(_DT_PM_WO, ptype="write", doc=wo, user=user):
        return
    raise ServiceError(ErrorCode.FORBIDDEN, _MSG_PM_PHOTO_FORBIDDEN, http_status=403)


def _pm_photo_validation_error(msg: str) -> ServiceError:
    """VALIDATION Decision-B với fields.file (FE hiển thị lỗi dưới control upload)."""
    return ServiceError(ErrorCode.VALIDATION, msg, http_status=422, fields={"file": msg})


def _pm_photo_envelope(file_url: str, file_name: str, checklist_item_idx) -> dict:
    """Envelope success DUY NHẤT của attach_pm_checklist_photo (EXACT 3-key OAS closed).

    Dùng CHUNG cho insert-path THẬT, dedupe-replay (pre-check HIT) VÀ race-winner
    re-read ⇒ shape byte-đối-byte KHÔNG lệch (mirror winner-reread imm12)."""
    return {
        "file_url": file_url,
        "file_name": file_name,
        "checklist_item_idx": int(checklist_item_idx),
    }


def attach_pm_checklist_photo(
    work_order_name: str,
    checklist_item_idx: int,
    filedata: bytes | None = None,
    filename: str = "",
    content_type: str = "",
    client_request_id: str = "",
) -> dict:
    """BR-08-14 (mobile CR-14/G6): đính ảnh bằng chứng cho MỘT mục checklist PM (NĐ98).

    ĐỐI XỨNG VERBATIM thứ tự reject-before-insert của `attach_incident_photo` (imm12) —
    KHÁC module/doctype/field. Mọi nhánh reject TRƯỚC `File.insert`:
    exists(WO) NOT_FOUND → permission (assignee/pm.write) FORBIDDEN → idx hợp lệ (row
    tồn tại trong wo.checklist_results) VALIDATION → file present → content-type ∈
    {jpg,png} → size ≤ cap → max-count/mục → `File.insert(is_private=1, attached_to=
    'PM Work Order'/WO)` → set `row.photo=file_url` (`frappe.db.set_value` — KHÔNG
    `wo.save()` re-run validate() gate hoàn-thành BR-08-06/08 giữa lúc đính ảnh) →
    lifecycle `pm_checklist_photo_attached` (hard-req, KHÔNG swallow) → `commit`.
    Nếu event throw → File.insert + set_value rollback (chưa commit) ⇒ KHÔNG orphan File,
    KHÔNG silent (đối xứng incident_photo_attached).

    BR-08-14-IDEMP (CR-24 §4 photo-level closure · mirror ADR-IMM12-10): `client_request_id`
    non-empty → dedupe theo composite scoped key `f"{wo}::{idx}::{key}"` trên Custom Field
    `File.ac_client_request_id` (unique NULL-store): lớp-1 pre-check SAU permission+idx-
    validation / TRƯỚC validation ladder (replay ảnh đã đính phải trả success kể cả khi mục
    đã đủ MAX=1 ảnh) — trúng ⇒ early-return envelope File ĐÃ đính (0 insert / 0 lifecycle);
    lớp-2 race-handler `UniqueValidationError` → re-read winner (kẻ thua raise TRƯỚC set_value
    + emit ⇒ 0 event trùng). Scope namespace theo record+mục: cùng key KHÁC wo/idx → composite
    KHÁC → KHÔNG dedupe chéo. Rỗng/thiếu → mỗi call 1 File mới (at-least-once CŨ, field NULL).

    Args:
        work_order_name: PM Work Order đang mở.
        checklist_item_idx: STT mục checklist (`pm_checklist_result.checklist_item_idx`).
        filedata: bytes ảnh (API đọc `frappe.request.files["file"].stream.read()`).
        filename: tên tệp gốc (File.file_name).
        content_type: MIME client gửi (validate jpg/png).
        client_request_id: idempotency key per-ảnh (mobile write-outbox re-drain);
            rỗng → behavior at-least-once cũ nguyên vẹn.

    Returns: `{"file_url", "file_name", "checklist_item_idx"}`.
    Raises: ServiceError NOT_FOUND | FORBIDDEN | VALIDATION (Decision-B qua API tier).
    """
    wo = PMWorkOrderRepo.get(work_order_name)
    if not wo:
        nthrow(MSG.IMM08_WO_NOT_FOUND, name=work_order_name)   # NOT_FOUND nếu thiếu
    _assert_can_attach_pm_photo(wo)                            # FORBIDDEN nếu ngoài quyền
    row = _find_checklist_row(wo, checklist_item_idx)
    if row is None:
        raise _pm_photo_validation_error(_MSG_PM_PHOTO_IDX_NOT_FOUND)
    # BR-08-14-IDEMP lớp-1: dedupe pre-check — SAU permission+idx / TRƯỚC validation ladder.
    scoped_key = (
        f"{work_order_name}::{int(checklist_item_idx)}::{client_request_id}"
        if client_request_id else ""
    )
    if scoped_key:
        existing = frappe.db.get_value(
            _DT_FILE, {"ac_client_request_id": scoped_key},
            ["file_url", "file_name"], as_dict=True)
        if existing:
            return _pm_photo_envelope(
                existing.file_url, existing.file_name, checklist_item_idx)
    if not filedata:
        raise _pm_photo_validation_error(_MSG_PM_PHOTO_MISSING)
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct not in _PM_PHOTO_CONTENT_TYPES:
        raise _pm_photo_validation_error(_MSG_PM_PHOTO_NOT_IMAGE)
    if len(filedata) > MAX_PM_CHECKLIST_PHOTO_BYTES:
        raise _pm_photo_validation_error(_MSG_PM_PHOTO_TOO_LARGE)
    if len(_checklist_item_photos(row)) >= MAX_PM_CHECKLIST_PHOTOS:
        raise _pm_photo_validation_error(_MSG_PM_PHOTO_MAX)

    file_payload = {
        "doctype": _DT_FILE,
        "file_name": filename,
        "attached_to_doctype": _DT_PM_WO,
        "attached_to_name": work_order_name,
        "is_private": 1,
        "content": filedata,
        "decode": False,
    }
    # BR-08-14-IDEMP: persist scoped key CHỈ khi truthy (NULL-store — File thường lưu NULL,
    # MariaDB unique index cho phép nhiều NULL ⇒ backward-compat nguyên vẹn).
    if scoped_key:
        file_payload["ac_client_request_id"] = scoped_key
    try:
        file_doc = frappe.get_doc(file_payload).insert(ignore_permissions=True)
    except frappe.UniqueValidationError:
        # BR-08-14-IDEMP lớp-2 race: request re-drain concurrent đã insert CÙNG scoped_key
        # giữa pre-check và insert này (unique index tabFile chặn kẻ thua). Kẻ thua raise
        # TRƯỚC set_value + create_lifecycle_event ⇒ 0 event trùng. Dọn msgprint "must be
        # unique" thừa, re-read winner rồi return idempotent (parity attach_incident_photo).
        frappe.clear_last_message()
        winner = frappe.db.get_value(
            _DT_FILE, {"ac_client_request_id": scoped_key},
            ["file_url", "file_name"], as_dict=True)
        if winner:
            return _pm_photo_envelope(
                winner.file_url, winner.file_name, checklist_item_idx)
        raise
    except (UnidentifiedImageError, OSError) as exc:
        # ẢNH HỎNG/ĐỨT TRUYỀN: bytes không giải mã được dù content-type hợp lệ. Frappe
        # File.before_insert → strip_exif → PIL.Image.open ném UnidentifiedImageError
        # (thân rác) hoặc OSError('Truncated File Read') (cắt cụt), bọc CẢ xử lý ảnh
        # phát sinh. PIL fail TRONG before_insert — TRƯỚC db_insert + write_file (đĩa) +
        # set row.photo ⇒ KHÔNG orphan File (DB lẫn đĩa), row.photo CHƯA set. Chuyển
        # thành lỗi VALIDATION Decision-B (fields.file) thay vì để HTTP-500 → bằng chứng
        # NĐ98 mất. (Đối xứng attach_incident_photo imm12.)
        frappe.logger("imm08").warning(
            f"pm_checklist_photo_corrupt wo={work_order_name} err={type(exc).__name__}"
        )
        raise _pm_photo_validation_error(_MSG_PM_PHOTO_CORRUPT) from exc

    # SoT ảnh/mục = row.photo (CÙNG field get_work_order hiển thị) → count==nguồn-liệt-kê.
    # frappe.db.set_value trên child row (anti-pattern #10: KHÔNG doc.save trên WO
    # workflow-managed — tránh re-run gate hoàn-thành khi đang đính ảnh dở phiếu).
    frappe.db.set_value(
        _DT_PM_CHECKLIST_ROW, row.name, "photo", file_doc.file_url,
        update_modified=False,
    )

    # BR-08-14 evidence trail NĐ98 — hard-req, KHÔNG try/except-swallow. Event throw →
    # File.insert + set_value rollback (chưa commit) ⇒ không orphan, không silent.
    from assetcore.services import imm00 as svc00  # lazy — tránh circular import
    svc00.create_lifecycle_event(
        asset=wo.asset_ref,
        event_type=_EVENT_PM_CHECKLIST_PHOTO_ATTACHED,
        actor=frappe.session.user,
        root_doctype=_DT_PM_WO,
        root_record=work_order_name,
        notes=f"Đính ảnh bằng chứng mục #{checklist_item_idx}: {filename}",
    )
    frappe.db.commit()
    return _pm_photo_envelope(file_doc.file_url, file_doc.file_name, checklist_item_idx)


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


# CR-24-PM (mobile write-outbox idempotency): submit_result là write KHÔNG idempotent
#   (WO→Completed + advance PM Schedule + PM Task Log + escalate CM WO). Mobile re-drain
#   write-outbox có thể gọi LẠI cùng phiếu ⇒ cần khoá idempotency. Mirror CR-24 imm12
#   _dedupe_lookup + winner-reread (services/imm12.py:450/557) NHƯNG store = frappe.cache()
#   thay DocField ⇒ KHÔNG field mới, KHÔNG bench migrate. Key scoped (wo_name,
#   client_request_id) ⇒ 2 WO / 2 key độc lập. TTL 24h = cửa sổ re-drain write-outbox.
_PM_SUBMIT_IDEMPOTENCY_TTL = 86400  # giây (24h)


def _pm_submit_cache_key(wo_name: str, client_request_id: str) -> str:
    """Khoá cache idempotency submit_result — scoped theo (wo_name, client_request_id)."""
    return f"pm_submit_result::{wo_name}::{client_request_id}"


def _pm_submit_cache_get(cache_key: str) -> dict | None:
    """Đọc payload đã cache cho khoá idempotency (None = chưa có / MISS).

    Seam nội-bộ (KHÔNG inline frappe.cache().get_value) để test race winner-reread
    ép được pre-check MISS đúng-1-lần mà KHÔNG đụng cache dùng chung bởi rbac caps.

    BẮT BUỘC `expires=True`: get_value mặc-định (expires=False) ghi kết-quả vào
    `frappe.local.cache` (request-local); một pre-check MISS sẽ nhét None vào layer
    local, còn set_value(expires_in_sec) CHỈ ghi Redis (KHÔNG cập nhật local) ⇒ lần
    get sau TRONG CÙNG request/process trả None-cũ (shadow) dù Redis đã có. Prod tách
    request nên vô hại, nhưng re-drain cùng process / test sẽ vỡ idempotency. `expires=
    True` bỏ qua layer local → luôn đọc Redis (mirror api/openapi.py:1379).
    """
    return frappe.cache().get_value(cache_key, expires=True)


def _pm_submit_cache_set(cache_key: str, payload: dict) -> None:
    frappe.cache().set_value(cache_key, payload, expires_in_sec=_PM_SUBMIT_IDEMPOTENCY_TTL)


def submit_result(name: str, *, checklist_results: list[dict], overall_result: str,
                  technician_notes: str = "", pm_sticker_attached: int = 0,
                  duration_minutes: int = 0, client_request_id: str = "") -> dict:
    # CR-24-PM idempotency (HANDOFF §2.1 header-parity): resolve khoá qua shared
    #   resolve_idempotency_key — body param `client_request_id` THẮNG header
    #   X-Idempotency-Key / alias Idempotency-Key (parity imm09/imm00/imm11); cả hai vắng
    #   ⇒ "" ⇒ cache_key=None ⇒ NO-OP dedup (legacy path y nguyên, NULL-semantics).
    #   Truthy → dedupe qua cache: HIT trả payload cũ VERBATIM (KHÔNG mutate/submit lần 2
    #   ⇒ WO Completed 1 lần, next_pm_date KHÔNG drift, CM WO KHÔNG double).
    resolved_key = resolve_idempotency_key(client_request_id)
    cache_key = _pm_submit_cache_key(name, resolved_key) if resolved_key else None
    if cache_key:
        cached = _pm_submit_cache_get(cache_key)
        if cached is not None:
            return cached

    wo = PMWorkOrderRepo.get(name)
    if not wo:
        nthrow(MSG.IMM08_WO_NOT_FOUND, name=name)
    if wo.docstatus == 1:
        # Race re-drain: winner concurrent CÙNG key đã submit + set cache GIỮA pre-check
        #   và đây → re-read cache khớp ⇒ trả idempotent thay vì ALREADY_SUBMITTED. KHÔNG
        #   khớp key ⇒ người khác đã đóng phiếu (không cùng key) → giữ lỗi cũ (đúng nghĩa).
        if cache_key:
            cached = _pm_submit_cache_get(cache_key)
            if cached is not None:
                return cached
        nthrow(MSG.IMM08_ALREADY_SUBMITTED)

    result_map = {r["idx"]: r for r in checklist_results if "idx" in r}
    # BE-3 (chống drop âm thầm): payload có thể chứa idx KHÔNG tồn tại trong child
    #   (client stale / drift). Nếu update-loop chỉ khớp theo idx thì idx phantom bị
    #   BỎ QUA CÂM → khi các idx hợp lệ còn lại đã rated, WO complete GIẢ (drop 1 mục
    #   mà vẫn báo thành công). Chặn: idx phantom = lỗi VALIDATION rõ ràng, KHÔNG nuốt.
    valid_idx = {row.idx for row in (wo.checklist_results or [])}
    unknown_idx = sorted(set(result_map) - valid_idx)
    if unknown_idx:
        frappe.logger("imm08").warning(
            "pm_submit_result.checklist_idx_unknown",
            extra={
                "work_order": name,
                "unknown_idx": unknown_idx,
                "valid_idx_count": len(valid_idx),
                "payload_idx_count": len(result_map),
            },
        )
        nthrow(MSG.IMM08_CHECKLIST_IDX_UNKNOWN, bad_idx=", ".join(str(i) for i in unknown_idx))
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

    # BR-08-03 FIX CHÍNH: anchor = wo.completion_date (đã set = nowdate() trong
    # handle_work_order_submit qua wo.submit()), KHÔNG nowdate() độc lập. Khi PM
    # backdated/late, field này == PM Schedule.next_due_date đã persist ==
    # AC Asset.next_pm_date == PM Task Log.next_pm_date (byte-for-byte, 1 SoT).
    # pm_interval_days THÔ — default 90 nằm DUY NHẤT trong compute_next_pm_date.
    sched_interval = PMScheduleRepo.get_value(wo.pm_schedule, "pm_interval_days")
    next_pm_date = compute_next_pm_date(wo.completion_date, sched_interval)
    cm_wo = PMWorkOrderRepo.find_one(
        {"source_pm_wo": name, "wo_type": "Corrective"},
        fields=["name"],
    )

    payload = {
        "name": wo.name,
        "new_status": wo.status,
        "is_late": bool(wo.is_late),
        "next_pm_date": str(next_pm_date),
        "cm_wo_created": cm_wo["name"] if cm_wo else None,
    }
    # CR-24-PM: lưu payload SAU mọi side-effect → re-drain trả VERBATIM (không drift).
    #   Shape 5-key GIỮ NGUYÊN (Hyrum's Law — mobile/FE phụ thuộc; OAS PmSubmitResultResponse
    #   closed). client_request_id CHỈ điều khiển dedup, KHÔNG lọt payload.
    if cache_key:
        _pm_submit_cache_set(cache_key, payload)
    return payload


def report_major_failure(pm_wo_name: str, *, failure_description: str) -> dict:
    wo = PMWorkOrderRepo.get(pm_wo_name)
    if not wo:
        nthrow(MSG.IMM08_WO_NOT_FOUND, name=pm_wo_name)

    PMWorkOrderRepo.set_values(pm_wo_name, {"status": PMStatus.HALTED_MAJOR})
    _transition_asset(wo.asset_ref, AssetStatus.OUT_OF_SERVICE, pm_wo_name)

    cm_wo = RepairRepo.create({
        "asset_ref": wo.asset_ref,
        "source_pm_wo": pm_wo_name,
        # Asset Repair.failure_description = mandatory (asset_repair.json reqd:1) — BẮT BUỘC set,
        # KHÔNG chỉ nhét vào technician_notes (nếu thiếu → MandatoryError khi insert ⇒ escalation 500).
        # Mirror imm09.create_repair_work_order:840 (failure_description là field gốc của CM WO).
        "failure_description": failure_description,
        # repair_type ∈ {Corrective, Breakdown, Warranty Repair} (asset_repair.json) — "Emergency" KHÔNG
        # hợp lệ (Select-validation → ValidationError). Lỗi nặng giữa PM = "Breakdown" (hỏng đột xuất);
        # độ-khẩn nằm ở priority="Emergency" (∈ {Normal, Urgent, Emergency}).
        "repair_type": "Breakdown",
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
        # RECONCILED (ADR-MOBILE-014 / spec §0.1.3): helper validation() → http_status=422
        # theo canonical SSoT _HTTP_FOR_CODE[ErrorCode.VALIDATION]=422 (utils/response.py:61).
        # ATOMIC: chỉ endpoint này dùng validation()=422; KHÔNG đổi default ServiceError.__init__.
        raise validation("Lý do hoãn lịch là bắt buộc (tối thiểu 5 ký tự)")
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
    # BR-08-14 / INV-PM-KPI-6: MẪU tuân thủ = WO không-Cancelled (SoT _pm_scheduled).
    # WO Cancelled (nghĩa vụ bị VOID hành chính) bị loại khỏi total_scheduled & MỌI
    # bucket THÁNG (completed/overdue/pending) → diệt (a) compliance giả tụt vì mẫu
    # phình; (b) phantom 'chưa xong' ở pending. Halted–Major Failure GIỮ counted.
    scheduled = _pm_scheduled(wos)
    total = len(scheduled)
    completed = [w for w in scheduled if w["status"] == PMStatus.COMPLETED]
    on_time = [w for w in completed if not w["is_late"]]
    # RC-10 (NextRound): KPI "Quá hạn" trên /pm/dashboard phải là count global
    # (status == "Overdue") khớp với launcher widget — tránh dual-source.
    # Trước đây chỉ đếm trong window tháng đang xem nên launcher (global) báo 1,
    # /pm/dashboard (month-bound) báo 0 cho WO quá hạn từ tháng trước.
    # Single source of truth: count_overdue_pm() (cùng hàm launcher gọi).
    # → field `overdue` = GLOBAL (toàn hệ thống) — KHÔNG đổi giá trị/ngữ nghĩa
    #   (INV-PM-KPI-2 / RC-10): khớp launcher widget + drill ?overdue=1.
    overdue_count = count_overdue_pm()
    # INV-PM-KPI-1/4: tile "Quá hạn trong tháng" phải đối-soát được với tổng-lịch
    # tháng. overdue_in_month = WO status==Overdue VÀ due_date thuộc [start,end] của
    # tháng đang xem (subset của scheduled) → KHÔNG bao giờ > total_scheduled. Đếm
    # trên `scheduled` (Overdue != Cancelled nên giá trị KHÔNG đổi — giữ nhất quán
    # mẫu, KHÔNG còn rủi ro Cancelled lọt bucket nào).
    overdue_in_month = sum(1 for w in scheduled if w["status"] == PMStatus.OVERDUE)
    # pending_in_month = các WO trong tháng CHƯA hoàn thành VÀ CHƯA quá hạn
    # (còn lại sau khi trừ completed + overdue trên MẪU không-Cancelled) — để strip
    # tháng hòa hợp số học: total_scheduled >= completed_on_time + overdue_in_month
    # + pending_in_month. Vì total=len(scheduled), Cancelled KHÔNG còn rơi vào pending.
    completed_in_month = len(completed)
    pending_in_month = total - completed_in_month - overdue_in_month
    late_days = [
        date_diff(str(w["completion_date"]), str(w["due_date"]))
        for w in completed if w["is_late"] and w["completion_date"]
    ]
    # INV-PM-KPI-3/6: compliance population-consistent — CẢ tử (completed_on_time)
    # & mẫu (total_scheduled = WO không-Cancelled) cùng phạm-vi-tháng. total==0 →
    # None (KHÔNG 0.0 gây hiểu nhầm "không tuân thủ"); FE render '—'/N-A. Tháng
    # chỉ-Cancelled ⇒ total==0 ⇒ None.
    compliance_rate = round(len(on_time) / total * 100, 1) if total else None
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
        # INV-PM-KPI-6 (trend SoT): CÙNG predicate loại-Cancelled với tile-tháng
        # (helper _pm_scheduled) → trend KHÔNG lệch chuẩn so với compliance tháng
        # hiện tại. t = số WO không-Cancelled; rate = c_on/t.
        month_scheduled = _pm_scheduled(month_wos)
        t = len(month_scheduled)
        c_on = sum(1 for w in month_scheduled if w["status"] == PMStatus.COMPLETED and not w["is_late"])
        trend.append({
            "month": f"{y:04d}-{m:02d}", "total": t, "on_time": c_on,
            "rate": round(c_on / t * 100, 1) if t else 0.0,
        })
    return {
        "kpis": {
            # Phạm-vi-tháng (đối-soát được, INV-PM-KPI-1/3/5):
            "compliance_rate_pct": compliance_rate,  # None khi total_scheduled==0
            "total_scheduled": total,
            "completed_on_time": len(on_time),
            "overdue_in_month": overdue_in_month,    # Overdue ∧ due_date ∈ tháng
            "pending_in_month": pending_in_month,    # chưa xong, chưa quá hạn
            # Toàn-hệ-thống (INV-PM-KPI-2 / RC-10): count global status==Overdue,
            # khớp launcher widget + drill ?overdue=1. KHÔNG bó trong tháng.
            "overdue": overdue_count,
            "avg_days_late": avg_days_late,
        },
        "trend_6months": trend,
        # CR-36 (Mobile-BE Dashboard KPI / IMM-07): ECHO kỳ báo-cáo server-resolve
        # (year/month keyword-only) → FE/mobile render header kỳ KHÔNG client-clock.
        # Đối-xứng imm09.get_kpis + imm11.get_kpis (đã có period @imm11.py:1295).
        "period": {"year": year, "month": month},
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


def get_due_pm_schedules(days: int = 30, limit: int = 50) -> dict:
    """Danh sách PM Schedule due_soon/overdue (≤ N ngày) — màn "Nhắc việc" (mobile F8).

    ĐỐI XỨNG ``get_due_calibrations`` (services/imm11.py:1393) — KHÁC NGUỒN: nửa PM
    dùng ``PM Schedule.next_due_date`` (KHÔNG AC Asset.next_calibration_date của
    nửa hiệu chuẩn; CR-28b explicit — PM Schedule có responsible_technician/
    alert_days_before phục vụ nhắc việc). Rows-key trả về = ``items`` (ĐỐI XỨNG
    get_due_calibrations; KHÁC list_schedules dùng ``data`` + pagination).

    CHỈ trả lịch ``status == 'Active'`` (LOẠI Paused/Suspended) CÓ ``next_due_date``
    đã set (có lịch PM thật). Guard ``is set`` BẮT BUỘC: Frappe query-builder render
    ``<= threshold`` thành ``ifnull(next_due_date, '0001-01-01') <= threshold`` ⇒ nếu
    KHÔNG loại NULL, mọi lịch chưa-có-ngày (next_due_date NULL) bị coerce
    '0001-01-01' và LỌT filter, sort ASC lên đầu, lấp kín ``limit`` → đẩy lịch
    quá-hạn thật khỏi due-list (sai KPI 'sắp đến hạn' + drill). Lịch chưa-có-ngày
    KHÔNG phải 'đến hạn'.

    ``days_left = date_diff(next_due_date, today)`` signed int (ÂM = quá hạn) —
    server-derived (client KHÔNG re-derive / so ngày client-clock).
    """
    today = nowdate()
    threshold = add_days(today, int(days))
    rows, _ = PMScheduleRepo.list(
        filters=[
            ["status", "=", PMScheduleStatus.ACTIVE],
            ["next_due_date", "is", "set"],
            ["next_due_date", "<=", threshold],
        ],
        fields=["name", "asset_ref", "pm_type", "status",
                "next_due_date", "last_pm_date", "responsible_technician"],
        order_by="next_due_date asc",
        page_size=int(limit),
    )
    today_d = getdate(today)
    for r in rows:
        r["asset_name"] = AssetRepo.get_value(r["asset_ref"], "asset_name") or ""
        nd = r.get("next_due_date")
        r["days_left"] = date_diff(nd, today_d) if nd else None
    return {"items": rows, "threshold_days": int(days)}


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
