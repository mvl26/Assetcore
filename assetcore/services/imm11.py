# Copyright (c) 2026, AssetCore Team
# IMM-11 Calibration — Tier 2 Business Service Layer.
#
# KHÔNG gọi frappe.db.* / frappe.get_doc trực tiếp — đi qua repository.
# Raise lỗi nghiệp vụ qua nthrow(MSG.IMM11_*); api_handler.handle() hydrate envelope.

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
)
from assetcore.services.shared.filters import pop_search
from assetcore.repositories.asset_repo import (
    AssetRepo, DeviceModelRepo, CapaRepo, LifecycleEventRepo,
)
from assetcore.repositories.calibration_repo import CalibrationRepo, CalibrationScheduleRepo
from assetcore.utils.notify import nthrow, MSG

_DEFAULT_INTERVAL_DAYS = 365
_NOT_DECOMMISSIONED = ("not in", [AssetStatus.DECOMMISSIONED])
_CAPA_OPEN_STATUSES = ("in", ["Open", "In Progress", "In Review"])
_LOOKBACK_IN_PROGRESS = "In Progress"
_DT_CAL = "IMM Asset Calibration"
_CALIBRATING_TRIGGER_STATUSES = {CalibrationResult.IN_PROGRESS, CalibrationResult.SENT_TO_LAB}
_ORDER_NEXT_CAL_ASC = "next_calibration_date asc"
_DT_CAL_SCHEDULE = "IMM Calibration Schedule"


# ─── SoT: server-driven CTA — tập trạng-thái-kế hợp lệ per status (R3/R21/R22 mirror) ─
#
# Map TẬP TRUNG cho server-driven CTA màn calibration-detail: get_calibration emit
# `allowed_transitions = _CAL_VALID_TRANSITIONS.get(doc.status, [])` để FE render nút
# workflow theo SERVER (KHÔNG hardcode status→button client-side = anti-pattern
# dead-gate/RBAC drift). Mirror IncidentDetail (imm12.py:778, R3) + PmWorkOrderDetail
# (imm08.py:651, R21) + RepairWorkOrderDetail (imm09.py:773, R22) — đây là thành viên
# THỨ TƯ & CUỐI có allowed_transitions[], ĐÓNG KÍN ASYMMETRY R3 (cả 4/4 *Detail emit).
#
# Keyed BẰNG CalibrationResult.* constants (KHÔNG literal) — codomain GROUNDED
# edge-by-edge `imm_11_calibration_workflow.json` transitions[] (8 state / 13 transition
# raw = 12 cạnh unique; `Failed→Conditionally Passed` khai 2 lần — Compliance Manager +
# System Manager, cùng next_state). Terminal Passed/Conditionally Passed/Cancelled → []
# (0 outgoing). Guard test (test_imm11.TestCalibrationAllowedTransitions +
# test_mobile_oas.TestMobileCalibrationAllowedTransitionsContract) chốt SSoT-divergence
# map↔workflow JSON theo SET (codomain dedup) + codomain ⊆ CalibrationResult enum.
_CAL_VALID_TRANSITIONS: dict[str, list[str]] = {
    CalibrationResult.SCHEDULED: [
        CalibrationResult.IN_PROGRESS,
        CalibrationResult.SENT_TO_LAB,
        CalibrationResult.CANCELLED,
    ],
    CalibrationResult.IN_PROGRESS: [
        CalibrationResult.PASSED,
        CalibrationResult.FAILED,
        CalibrationResult.COND_PASSED,
        CalibrationResult.CANCELLED,
    ],
    CalibrationResult.SENT_TO_LAB: [CalibrationResult.CERT_RECEIVED],
    CalibrationResult.CERT_RECEIVED: [
        CalibrationResult.PASSED,
        CalibrationResult.FAILED,
        CalibrationResult.COND_PASSED,
    ],
    CalibrationResult.FAILED: [CalibrationResult.COND_PASSED],
    CalibrationResult.PASSED: [],
    CalibrationResult.COND_PASSED: [],
    CalibrationResult.CANCELLED: [],
}


# ════════════════════════════════════════════════════════════════════════════
#  SoT — "calibration due / overdue" predicate  (BR-11-08 / BR-11-09)
#  docs/imm-11/04_Backend_Design.md §4.1
#
#  ONE predicate + ONE date-field + ONE filter set, dùng chung MỌI consumer:
#  - date-field authoritative = IMM Calibration Schedule.next_due_date (is_active=1)
#  - AC Asset.calibration_status từ nay CHỈ là rollup cache (không là nguồn đếm)
#  - filter chung: schedule is_active=1 + asset NOT decommissioned; de-dup theo asset
# ════════════════════════════════════════════════════════════════════════════

CAL_DUE_SOON_WINDOW_DAYS = 30  # 1 hằng dùng chung — KHÔNG hardcode "30" rải rác
_CAL_AUTH_DATE_FIELD = "next_due_date"  # authoritative date = Schedule.next_due_date


def is_calibration_overdue(next_due, ref_date=None) -> bool:
    """OVERDUE ⟺ next_due < today (strict <). None → False (chưa có hạn = không quá hạn)."""
    if not next_due:
        return False
    ref = getdate(ref_date) if ref_date else getdate(nowdate())
    return getdate(next_due) < ref


def is_calibration_due_soon(next_due, ref_date=None) -> bool:
    """DUE_SOON ⟺ today <= next_due <= today + CAL_DUE_SOON_WINDOW_DAYS (2 biên inclusive).

    Overdue ưu tiên (next_due < today bị loại bởi biên dưới). None → False.
    """
    if not next_due:
        return False
    ref = getdate(ref_date) if ref_date else getdate(nowdate())
    nd = getdate(next_due)
    return ref <= nd <= add_days(ref, CAL_DUE_SOON_WINDOW_DAYS)


def _overdue_asset_ids(ref_date=None) -> set[str]:
    """SoT: tập DISTINCT asset có >=1 active schedule overdue, asset không decommissioned.

    De-dup theo asset (BR-11-09): 1 asset nhiều schedule overdue đếm 1 lần.
    """
    ref = ref_date or nowdate()
    rows = frappe.db.sql(
        """
        SELECT DISTINCT s.asset
        FROM `tabIMM Calibration Schedule` s
        JOIN `tabAC Asset` a ON a.name = s.asset
        WHERE s.is_active = 1
          AND s.next_due_date IS NOT NULL
          AND s.next_due_date < %(ref)s
          AND a.lifecycle_status != %(decom)s
        """,
        {"ref": ref, "decom": AssetStatus.DECOMMISSIONED},
        as_dict=True,
    )
    return {r["asset"] for r in rows}


def _due_soon_asset_ids(ref_date=None) -> set[str]:
    """SoT: tập DISTINCT asset có >=1 active schedule due trong [today, today+30],
    LOẠI những asset đã overdue (overdue ưu tiên — không double-tally)."""
    ref = ref_date or nowdate()
    window_end = add_days(ref, CAL_DUE_SOON_WINDOW_DAYS)
    rows = frappe.db.sql(
        """
        SELECT DISTINCT s.asset
        FROM `tabIMM Calibration Schedule` s
        JOIN `tabAC Asset` a ON a.name = s.asset
        WHERE s.is_active = 1
          AND s.next_due_date IS NOT NULL
          AND s.next_due_date >= %(ref)s AND s.next_due_date <= %(end)s
          AND a.lifecycle_status != %(decom)s
        """,
        {"ref": ref, "end": window_end, "decom": AssetStatus.DECOMMISSIONED},
        as_dict=True,
    )
    return {r["asset"] for r in rows} - _overdue_asset_ids(ref_date)


def _decommissioned_asset_ids() -> set[str]:
    """Tập asset Decommissioned — dùng để loại khỏi drill due_before (cutoff tùy ý)."""
    rows = frappe.db.sql(
        "SELECT name FROM `tabAC Asset` WHERE lifecycle_status = %(decom)s",
        {"decom": AssetStatus.DECOMMISSIONED},
        as_dict=True,
    )
    return {r["name"] for r in rows}


def _calibration_status_asset_ids(ref_date=None) -> dict[str, str]:
    """Rollup map asset → CalibrationStatus derive TỪ SoT schedule.

    OVERDUE > DUE_SOON > ON_SCHEDULE. Chỉ asset không-decommissioned có >=1
    active schedule. Dùng cho check_calibration_expiry (rollup cache).
    """
    overdue = _overdue_asset_ids(ref_date)
    due_soon = _due_soon_asset_ids(ref_date)
    ref = ref_date or nowdate()
    on_sched_rows = frappe.db.sql(
        """
        SELECT DISTINCT s.asset
        FROM `tabIMM Calibration Schedule` s
        JOIN `tabAC Asset` a ON a.name = s.asset
        WHERE s.is_active = 1
          AND s.next_due_date IS NOT NULL
          AND s.next_due_date > %(end)s
          AND a.lifecycle_status != %(decom)s
        """,
        {"end": add_days(ref, CAL_DUE_SOON_WINDOW_DAYS),
         "decom": AssetStatus.DECOMMISSIONED},
        as_dict=True,
    )
    result: dict[str, str] = {}
    for an in {r["asset"] for r in on_sched_rows}:
        result[an] = CalibrationStatus.ON_SCHEDULE
    for an in due_soon:
        result[an] = CalibrationStatus.DUE_SOON
    for an in overdue:  # overdue ưu tiên cuối cùng (ghi đè)
        result[an] = CalibrationStatus.OVERDUE
    return result


def _top_assets_by_schedule(asset_ids: set[str], *, limit: int = 10) -> list[dict]:
    """Dashboard list: hydrate asset display rows cho 1 tập asset SoT,
    order by earliest active-schedule next_due_date asc (sớm nhất lên đầu).

    `next_calibration_date` trong return = `next_due_date` SoT của schedule
    (KHÔNG đọc field cache trên AC Asset) để FE render nhất quán với count.
    """
    if not asset_ids:
        return []
    placeholders = ", ".join(["%s"] * len(asset_ids))
    rows = frappe.db.sql(
        f"""
        SELECT a.name, a.asset_name, a.device_model, a.location,
               MIN(s.next_due_date) AS next_calibration_date
        FROM `tabAC Asset` a
        JOIN `tabIMM Calibration Schedule` s ON s.asset = a.name AND s.is_active = 1
        WHERE a.name IN ({placeholders})
        GROUP BY a.name, a.asset_name, a.device_model, a.location
        ORDER BY next_calibration_date ASC
        LIMIT %s
        """,
        (*asset_ids, int(limit)),
        as_dict=True,
    )
    return rows


def _transition_asset(asset_ref: str, to_status: str, cal_name: str, reason: str = "") -> None:
    transition_asset_status(
        asset_name=asset_ref, to_status=to_status,
        actor=frappe.session.user,
        root_doctype=_DT_CAL, root_record=cal_name,
        reason=reason,
    )


# ─── Hooks từ module khác ─────────────────────────────────────────────────────

def create_calibration_schedule_from_commissioning(commissioning_doc) -> Optional[str]:
    """Hook: IMM-04 Commissioning on_submit."""
    asset = commissioning_doc.asset
    device_model = AssetRepo.get_value(asset, "device_model")
    if not device_model:
        return None
    model = DeviceModelRepo.get_value(
        device_model,
        ["is_calibration_required", "calibration_interval_days", "default_calibration_type"],
        as_dict=True,
    ) or {}
    if not model.get("is_calibration_required"):
        return None
    interval = model.get("calibration_interval_days") or _DEFAULT_INTERVAL_DAYS
    cal_type = model.get("default_calibration_type") or "External"
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


def create_calibration_schedule_from_asset(asset_doc, method: str | None = None) -> Optional[str]:
    """Hook: AC Asset after_insert → tạo Calibration Schedule nếu user tick
    `is_calibration_required` (RC-07).

    Tham số ``method`` để tương thích chữ ký doc-event của Frappe
    (``after_insert`` truyền ``(doc, method)``); không dùng trong logic.

    Cho phép tạo lịch hiệu chuẩn NGAY khi tạo tài sản trực tiếp (không bắt buộc
    qua luồng Commissioning). Điều kiện:
        - asset_doc.is_calibration_required = 1
        - Chưa tồn tại Schedule active cho asset (idempotent).
        - Có interval (asset.calibration_interval_days hoặc fallback từ device_model,
          cuối cùng mặc định 365 ngày).

    KHÔNG fail asset creation nếu schedule fail — log P0 và tiếp tục.
    """
    if not getattr(asset_doc, "is_calibration_required", 0):
        return None

    asset_name = asset_doc.name

    # Idempotent guard
    if CalibrationScheduleRepo.exists({"asset": asset_name, "is_active": 1}):
        return None

    # Resolve interval: asset → device_model → default
    interval = int(asset_doc.get("calibration_interval_days") or 0)
    device_model = asset_doc.get("device_model") or ""
    cal_type = "External"
    if device_model:
        model_data = DeviceModelRepo.get_value(
            device_model,
            ["calibration_interval_days", "default_calibration_type"],
            as_dict=True,
        ) or {}
        if interval <= 0:
            interval = int(model_data.get("calibration_interval_days") or 0)
        cal_type = model_data.get("default_calibration_type") or cal_type
    if interval <= 0:
        interval = _DEFAULT_INTERVAL_DAYS

    base_date = (
        asset_doc.get("last_calibration_date")
        or asset_doc.get("commissioning_date")
        or asset_doc.get("purchase_date")
        or nowdate()
    )

    try:
        sched = CalibrationScheduleRepo.create({
            "asset": asset_name,
            "device_model": device_model or None,
            "calibration_type": cal_type,
            "interval_days": interval,
            "last_calibration_date": base_date,
            "next_due_date": add_days(base_date, interval),
            "is_active": 1,
        })
    except Exception:
        # P0 alert — KHÔNG vỡ asset creation
        frappe.log_error(
            frappe.get_traceback(),
            f"IMM-11 create_calibration_schedule_from_asset failed: {asset_name}",
        )
        return None

    try:
        log_audit_event(
            asset=asset_name, event_type="Calibration Schedule Created",
            actor=frappe.session.user,
            ref_doctype=CalibrationScheduleRepo.DOCTYPE,
            ref_name=sched.name,
            change_summary=(
                f"Calibration Schedule {sched.name} auto từ tạo tài sản "
                f"(is_calibration_required) — {cal_type}, mỗi {interval} ngày"
            ),
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         "IMM-11 create_calibration_schedule_from_asset audit")

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
    """Scheduler daily — rollup cache `AC Asset.calibration_status` TỪ SoT schedule,
    reconcile FULL-SET (BR-11-10 stale-clear + BR-11-11 FAILED-preserve).

    BR-11-08 (§4.1.3): KHÔNG còn đọc `AC Asset.next_calibration_date` làm nguồn
    đếm. Status derive từ `IMM Calibration Schedule.next_due_date` (is_active=1)
    qua `_calibration_status_asset_ids` (SoT). `calibration_status` từ nay CHỈ là
    cache hiển thị nhanh (KPI/drill/dashboard đọc SoT trực tiếp).

    Phạm vi reconcile = UNION(asset có ≥1 active schedule, asset có
    calibration_status != ''). Iterate TOÀN tập → không cache row nào bị bỏ sót:
      - BR-11-10 stale-clear: asset hết active schedule (rời khỏi rollup map) →
        reset neutral NOT_REQUIRED (chống badge ma 'Overdue'/'Due Soon' vĩnh viễn).
      - BR-11-11 FAILED-preserve: terminal `Calibration Failed` khi
        lifecycle_status == Out of Service → KHÔNG bị rollup ghi đè.

    Idempotent: chạy 2× cho kết quả như nhau (chỉ ghi khi giá trị THỰC SỰ khác
    cache hiện tại). E4: phát `notify_calibration_due` CHỈ khi status đổi (anti-spam,
    chỉ chuyển VÀO Due Soon/Overdue). Xem docs/imm-00/04_Backend_Design.md §III.1b-2
    + docs/imm-11/04_Backend_Design.md §4.1.3.
    """
    from assetcore.services import notifications  # lazy import — tránh circular

    rollup = _calibration_status_asset_ids()   # map: asset -> derived (CHỈ active-sched)
    cached = _nonempty_cache_asset_ids()       # set: asset có calibration_status != ''
    for asset_name in (set(rollup) | cached):  # UNION — không bỏ sót cache row nào
        old_status = AssetRepo.get_value(asset_name, "calibration_status") or ""
        new_status = _reconcile_calibration_status(
            asset_name, old_status, rollup.get(asset_name))
        if new_status == old_status:
            continue  # idempotent — không ghi, không notify lại (anti-spam)
        AssetRepo.set_values(asset_name, {"calibration_status": new_status})
        # E4 — báo người phụ trách khi vừa chuyển VÀO Due Soon/Overdue.
        # Bọc per-asset: 1 asset lỗi không dừng cả batch.
        try:
            notifications.notify_calibration_due(asset_name, old_status, new_status)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "imm11 notify_calibration_due")


def _reconcile_calibration_status(
        asset_name: str, old: str, derived: str | None) -> str:
    """Quyết định giá trị cache mới cho 1 asset (§4.1.3 decision table).

    - ``derived`` = giá trị SoT rollup (None nếu asset KHÔNG còn active schedule).
    - BR-11-11 FAILED-preserve: old == FAILED ∧ asset Out of Service → giữ FAILED
      (terminal). Recal Pass (`handle_calibration_pass`) đưa asset rời Out of
      Service là CON ĐƯỜNG DUY NHẤT để rollup tiếp quản FAILED.
    - derived có giá trị (còn active schedule) → dùng derived (Overdue/DueSoon/OnSchedule).
    - derived None (BR-11-10 stale-clear): hết active schedule →
        · old != '' → reset neutral NOT_REQUIRED (xoá badge ma);
        · old == '' → giữ rỗng (không có gì để clear → no-op upstream).
    """
    if old == CalibrationStatus.FAILED:
        lifecycle = AssetRepo.get_value(asset_name, "lifecycle_status")
        if lifecycle == AssetStatus.OUT_OF_SERVICE:
            return CalibrationStatus.FAILED        # BR-11-11 preserve terminal
    if derived is not None:
        return derived                             # còn active schedule → SoT rollup
    if old:
        return CalibrationStatus.NOT_REQUIRED      # BR-11-10 stale-clear → neutral
    return old                                     # '' → giữ rỗng (no-op)


def _nonempty_cache_asset_ids() -> set[str]:
    """Tập asset có `calibration_status != ''` (cache khác rỗng) — để reconcile
    thăm CẢ asset không-còn-trong-rollup (lịch deactivate/xóa) → stale-clear
    (BR-11-10). Đây là cache write-path SCOPE, KHÔNG phải count SoT."""
    rows = frappe.db.sql(
        "SELECT name FROM `tabAC Asset` "
        "WHERE calibration_status IS NOT NULL AND calibration_status != ''",
        as_dict=True,
    )
    return {r["name"] for r in rows}


# ─── BR-11-12: Recalibration OoS-restore governance guard ─────────────────────
# docs/imm-11/02_Analysis_Design.md §BR-11-12 + 04_Backend_Design.md §4.1.5
#
# `Out of Service` là lifecycle_status DÙNG CHUNG nhiều module (cal-fail IMM-11,
# incident IMM-12, repair IMM-09, PM-finding IMM-08). Recalibration Pass CHỈ được
# khôi phục OoS → Active khi (1) chính chuỗi hiệu chuẩn đặt hold (ALE mới nhất vào
# OoS có root_doctype='IMM Asset Calibration') VÀ (2) KHÔNG còn governance hold
# khác mở. Mọi nhánh ép-Active-từ-OoS PHẢI đi qua `_can_restore_from_oos` (grep-
# guard SoT). Pure read-only; KHÔNG raise → on_submit Pass luôn đóng được.

_DT_INCIDENT = "Incident Report"
_DT_REPAIR = "Asset Repair"
_DT_PM_WO = "PM Work Order"
# PM WO "đang mở" (OoS-finding chưa xử lý) = status NOT IN terminal.
_PM_WO_TERMINAL = ("Completed", "Cancelled")

# Map root_doctype hold → nhãn VI cho hold-note (de-conflict liên-module).
_HOLD_SOURCE_LABELS = {
    _DT_INCIDENT: "Sự cố (IMM-12)",
    _DT_REPAIR: "Sửa chữa (IMM-09)",
    _DT_PM_WO: "Bảo trì (IMM-08)",
    _DT_CAL: "hiệu chuẩn (còn hold khác)",
}


def _oos_hold_source(asset_name: str) -> Optional[str]:
    """SoT — root_doctype của ALE mới nhất đưa asset VÀO 'Out of Service'.

    = "ai đang giữ hold Ngừng hoạt động". Order by timestamp desc → lấy hold hiện
    hành (gần nhất). None nếu chưa từng có ALE vào OoS (an toàn: coi như không xác
    định nguồn → không restore). Read-only.
    """
    # find_one không nhận order_by → dùng list(page_size=1, order_by) cho "mới nhất".
    rows, _ = LifecycleEventRepo.list(
        filters={"asset": asset_name, "to_status": AssetStatus.OUT_OF_SERVICE},
        fields=["root_doctype"],
        order_by="timestamp desc, creation desc",
        page_size=1,
    )
    return (rows[0].get("root_doctype") if rows else None)


def _hold_source_label(asset_name: str) -> str:
    """Nhãn VI nguồn hold OoS cho hold-note (BR-11-12)."""
    src = _oos_hold_source(asset_name)
    return _HOLD_SOURCE_LABELS.get(src, "hạng mục khác")


def _oos_hold_note(asset_name: str, source_label: str) -> str:
    """Note VI cho ALE giữ-OoS: nêu rõ nguồn hold còn lại (traceability)."""
    return f"Recalibration Pass — giữ Ngừng hoạt động do hạng mục khác ({source_label})"


def _has_other_governance_hold(asset_name: str) -> bool:
    """True nếu CÒN ≥1 governance hold khác mở (Incident IMM-12 / Repair IMM-09 /
    PM-finding IMM-08). Mỗi loại đúng 1 db.count (không query thừa). Lazy-import
    open-filter của module khác để tránh circular import (Pattern B)."""
    # IMM-12 — Incident mở (SoT open_incident_filter)
    from assetcore.services.imm12 import open_incident_filter  # noqa: PLC0415
    if frappe.db.count(_DT_INCIDENT, open_incident_filter({"asset": asset_name})):
        return True
    # IMM-09 — Repair WO mở (SoT open_repair_filter)
    from assetcore.services.imm09 import open_repair_filter  # noqa: PLC0415
    if frappe.db.count(_DT_REPAIR, open_repair_filter({"asset_ref": asset_name})):
        return True
    # IMM-08 — PM WO OoS-finding mở (status NOT IN terminal).
    if frappe.db.count(_DT_PM_WO, {
        "asset_ref": asset_name,
        "status": ("not in", list(_PM_WO_TERMINAL)),
    }):
        return True
    return False


def _can_restore_from_oos(asset_name: str, cal_doc) -> bool:
    """BR-11-12 — True ⟺ recal Pass được phép đưa asset Out of Service → Active.

    Điều kiện AND:
      1. Chủ-hold OoS == chuỗi hiệu chuẩn: ALE mới nhất đưa asset VÀO
         'Out of Service' có root_doctype == 'IMM Asset Calibration'.
      2. KHÔNG còn governance hold khác mở (Incident / Repair / PM-finding).
    Pure read-only; KHÔNG raise. Bất kỳ điều kiện fail → False (giữ OoS).
    MỌI nhánh ép Active-từ-OoS trong handle_calibration_pass PHẢI đi qua đây
    (grep-guard SoT, AC-11-18).
    """
    if _oos_hold_source(asset_name) != _DT_CAL:
        return False
    return not _has_other_governance_hold(asset_name)


# ─── Submit handlers (gọi từ Controller on_submit) ────────────────────────────

def _calibration_basis_date(cal_doc) -> str:
    """SoT ngày cơ sở của 1 phiếu hiệu chuẩn — DÙNG CHUNG cho PASS (advance =
    basis + interval) và FAIL (set = basis, due-now). 1 nguồn → pass/fail KHÔNG
    drift (BR-11-08b, §4.1.6). Ưu tiên certificate_date, rồi actual_date, rồi
    nowdate(); luôn trả str (yyyy-mm-dd)."""
    return str(cal_doc.certificate_date or cal_doc.actual_date or nowdate())


# ─── BR-11-13: PASS → Asset-cache ROLLUP đa-lịch (worst-of-all + MIN next_due) ─
# docs/imm-11/02_Analysis_Design.md §BR-11-13 + 04_Backend_Design.md §4.1.7
#
# RC-PASS-ROLLUP (mirror BR-11-08b): handle_calibration_pass GHI ASSET-cache
# {calibration_status: ON_SCHEDULE hardcode, next_calibration_date: basis+interval}
# = trạng-thái/hạn của CHỈ schedule vừa Pass — bỏ qua active schedule KHÁC.
# check_calibration_expiry rollup từ MỌI active schedule (_calibration_status_asset_ids).
# → 2 write-path 1 cache field, 2 logic ≠ = divergence (badge "Đúng lịch" vs SoT
# Overdue + asset rớt khỏi get_due_calibrations). FIX: cache PASS phải DÙNG CÙNG
# SoT _calibration_status_asset_ids + MIN(next_due_date) → ROLLUP-CONSISTENCY.

def _asset_min_next_due(asset_name: str) -> Optional[str]:
    """MIN(next_due_date) trên MỌI active schedule của asset (1 aggregate query,
    bounded). None nếu asset không còn active schedule có next_due_date.

    = hạn-gần-nhất THẬT của asset (KHÔNG phải next của 1 lịch vừa Pass) → cache
    `AC Asset.next_calibration_date` để `get_due_calibrations` filter đúng (asset
    còn lịch sớm hơn KHÔNG bị rớt). BR-11-13, §4.1.7.
    """
    row = frappe.db.sql(
        """
        SELECT MIN(next_due_date) AS min_due
        FROM `tabIMM Calibration Schedule`
        WHERE asset = %(a)s AND is_active = 1 AND next_due_date IS NOT NULL
        """,
        {"a": asset_name}, as_dict=True,
    )
    min_due = row[0]["min_due"] if row and row[0]["min_due"] else None
    return str(min_due) if min_due else None


def _apply_asset_calibration_rollup(asset_name: str, basis: str) -> None:
    """Ghi ASSET-cache 3 field theo ROLLUP đa-lịch (BR-11-13). Gọi SAU khi schedule
    vừa Pass đã advance next_due_date (để rollup đọc được date mới — nếu chạy
    TRƯỚC, rollup thấy date cũ → sai happy-path 1-lịch).

    - `calibration_status` = `_calibration_status_asset_ids().get(asset, ON_SCHEDULE)`
      — CÙNG hàm SoT mà `check_calibration_expiry` dùng (worst-of OVERDUE>DUE_SOON>
      ON_SCHEDULE) → ROLLUP-CONSISTENCY: giá trị PASS-cache == scheduler-cache →
      scheduler ngay sau Pass idempotent (no flip-flop badge). Fallback ON_SCHEDULE
      CHỈ khi asset không-còn trong map (mọi schedule next_due > today+30).
    - `next_calibration_date` = `_asset_min_next_due(asset)` (MIN, KHÔNG next 1-lịch).
    - `last_calibration_date` = basis (ngày phiếu vừa Pass — GIỮ như cũ).

    Bounded query (≤4: 3 set-query toàn-tập của `_calibration_status_asset_ids`
    đã có sẵn — KHÔNG per-asset loop — + 1 aggregate MIN). KHÔNG N+1. §4.1.7.
    """
    status = _calibration_status_asset_ids().get(
        asset_name, CalibrationStatus.ON_SCHEDULE)
    min_due = _asset_min_next_due(asset_name)
    AssetRepo.set_values(asset_name, {
        "last_calibration_date": basis,
        "next_calibration_date": min_due,
        "calibration_status": status,
    })


def handle_calibration_pass(cal_doc) -> None:
    """on_submit Pass: cập nhật lịch + lifecycle event."""
    interval = None
    if cal_doc.calibration_schedule:
        interval = CalibrationScheduleRepo.get_value(
            cal_doc.calibration_schedule, "interval_days")
    if not interval:
        interval = DeviceModelRepo.get_value(
            cal_doc.device_model, "calibration_interval_days") or _DEFAULT_INTERVAL_DAYS

    basis_date = _calibration_basis_date(cal_doc)
    next_date = add_days(basis_date, interval)

    # Phiếu (CalibrationRepo.next_calibration_date) — GIỮ (BR-11-04, không đổi).
    CalibrationRepo.set_values(cal_doc.name, {"next_calibration_date": next_date})

    # Schedule vừa Pass advance next_due_date = basis + interval (BR-11-04).
    # PHẢI chạy TRƯỚC rollup để _apply_asset_calibration_rollup đọc date mới.
    if cal_doc.calibration_schedule:
        CalibrationScheduleRepo.set_values(cal_doc.calibration_schedule, {
            "last_calibration_date": basis_date,
            "next_due_date": next_date,
        })

    # BR-11-13 — ASSET-cache ghi theo ROLLUP đa-lịch (worst-of-all + MIN next_due),
    # CÙNG SoT _calibration_status_asset_ids mà check_calibration_expiry dùng →
    # ROLLUP-CONSISTENCY (KHÔNG hardcode ON_SCHEDULE 1-lịch). §4.1.7.
    _apply_asset_calibration_rollup(cal_doc.asset, basis_date)

    current_status = AssetRepo.get_value(cal_doc.asset, "lifecycle_status")

    # BR-11-12 restore-guard liên-module. 3 nhánh + audit 1 ALE 'calibration_passed':
    #  (A) prev=Calibrating          → restore Active (transition tự ghi ALE 'activated').
    #  (B) prev=OoS ∧ can_restore     → restore Active (chủ-hold cal ∧ 0 hold khác).
    #  (C) prev=OoS ∧ ¬can_restore    → GIỮ OoS, ghi 1 ALE giữ-trạng-thái + hold-note.
    #  (terminal/khác)               → no-op, ALE 'calibration_passed' from=to đủ audit.
    # MỌI ép-Active-từ-OoS đi qua _can_restore_from_oos (grep-guard SoT, AC-11-18).
    keep_oos_note = ""
    if (current_status == AssetStatus.OUT_OF_SERVICE
            and not _can_restore_from_oos(cal_doc.asset, cal_doc)):
        # Nhánh C — note hold còn lại nhồi vào ALE 'calibration_passed' (1 ALE).
        keep_oos_note = _oos_hold_note(
            cal_doc.asset, _hold_source_label(cal_doc.asset))

    base_note = f"Result: {cal_doc.overall_result}; next due: {next_date}"
    create_lifecycle_event(
        asset=cal_doc.asset, event_type="calibration_passed",
        actor=frappe.session.user,
        from_status=current_status, to_status=current_status,
        root_doctype=CalibrationRepo.DOCTYPE, root_record=cal_doc.name,
        notes=f"{base_note}. {keep_oos_note}".strip() if keep_oos_note else base_note,
    )

    if current_status == AssetStatus.CALIBRATING:
        # Nhánh A — GIỮ NGUYÊN: Calibrating → Active (BR đúng, không gate).
        _transition_asset(cal_doc.asset, AssetStatus.ACTIVE, cal_doc.name,
                          reason=f"Calibration passed — {cal_doc.name}")
    elif current_status == AssetStatus.OUT_OF_SERVICE:
        # Nhánh B — restore CÓ ĐIỀU KIỆN. _transition_asset OoS→Active là transition
        # hợp lệ (state machine) → không raise; idempotent prev==to no-op (imm00:105).
        if _can_restore_from_oos(cal_doc.asset, cal_doc):
            _transition_asset(
                cal_doc.asset, AssetStatus.ACTIVE, cal_doc.name,
                reason=f"Recalibration Pass — hold hiệu chuẩn giải toả, "
                       f"không hold khác — {cal_doc.name}")
        # else: nhánh C — đã ghi hold-note vào ALE trên; GIỮ OoS (no transition).
    # else: terminal (Decommissioned)/khác → KHÔNG ép Active (no-raise, AC-11-18).


def handle_calibration_fail(cal_doc) -> None:
    """on_submit Fail: transition → Out of Service + CAPA + lookback + Incident."""
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

    # BR-11-08b (§4.1.6): hạ MỌI active schedule của asset về due-now (basis <=
    # today) → asset rơi vào _overdue_asset_ids() (basis<today) ∪
    # _due_soon_asset_ids() (basis==today), KHÔNG còn mask ON_SCHEDULE trong KPI
    # SoT (BR-11-08 đếm theo Schedule.next_due_date, KHÔNG đọc cache FAILED).
    # SoT-WRITE NOTE: đây là DUY NHẤT nơi set next_due_date về quá-khứ/today;
    # mọi nơi khác (handle_calibration_pass, create_*) advance về tương lai.
    # Theo ASSET (không chỉ cal_doc.calibration_schedule) — asset Class B+ có thể
    # có nhiều loại calibration → nhiều schedule active; tất cả phải due-now.
    # 1 query list + loop set_values (no N+1 trên list). Null-safe: 0 active
    # schedule → loop rỗng → no-op, KHÔNG raise (CAPA/Incident/lookback bất biến).
    # Idempotent: basis cố định theo phiếu → re-apply giữ next_due_date == basis.
    basis = _calibration_basis_date(cal_doc)
    active_scheds, _ = CalibrationScheduleRepo.list(
        filters={"asset": cal_doc.asset, "is_active": 1},
        fields=["name"], page_size=10_000,
    )
    for s in active_scheds:
        CalibrationScheduleRepo.set_values(s["name"], {"next_due_date": basis})

    # IMM-12 cross-module: auto-report incident for failed calibration
    try:
        from assetcore.services.imm12 import report_incident as _report_incident
        _report_incident(
            asset=cal_doc.asset,
            incident_type="Malfunction",
            severity="High",
            description=f"Thiết bị không đạt hiệu chuẩn — {cal_doc.name}. Thông số lỗi: {failed_params}",
            fault_code="CAL_FAIL",
            linked_repair_wo=cal_doc.name,
            reported_by=frappe.session.user,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-11 → IMM-12 incident on cal_fail")


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

def _normalize_schedule_filters(f: dict | None) -> dict:
    """R6 §9.4.3 + BR-11-08 (§4.1.2) — dịch virtual filter date-window sang điều
    kiện next_due_date, ÁP CÙNG tập filter SoT với KPI/dashboard.

    3 virtual key, 3 ngữ nghĩa PHÂN BIỆT (KHÔNG tái dùng nhầm):

    - ``overdue`` (truthy) → card calib_overdue: next_due_date < today, is_active=1,
      asset IN _overdue_asset_ids() (de-dup theo asset, NOT decommissioned).
    - ``due_soon`` (truthy) → card calib_due "Hiệu chuẩn đến hạn": cửa-sổ-2-biên
      [today, today+CAL_DUE_SOON_WINDOW_DAYS], is_active=1, asset IN
      _due_soon_asset_ids() (đã LOẠI overdue-set → KHÔNG lẫn overdue rows). Drill
      tái lập CHÍNH XÁC tập KPI: số asset distinct == calib_due, KHÔNG cần
      post-filter Python ``next_due_date >= today``.
    - ``due_before`` → cutoff-tùy-ý LEGACY (tập-BAO): next_due_date <= X, is_active=1,
      chỉ loại asset thanh lý. KHÔNG khoá theo SoT window (có thể vượt 30, gồm cả
      overdue) — giữ cho caller cũ, KHÔNG dùng cho card due-soon nữa.

    Khi drill SoT (overdue / due_soon), enforce CÙNG filter KPI (inject
    ``asset IN [SoT id-set]``) → drill-list count khớp KPI. Một nguồn sự thật.
    """
    if not f:
        return {}
    out: dict = {}
    due_before = None
    overdue = False
    due_soon = False
    _truthy = ("1", "true", "True", "yes")
    for k, v in f.items():
        if k == "due_before":
            due_before = v
        elif k == "overdue":
            overdue = str(v) in _truthy
        elif k == "due_soon":
            due_soon = str(v) in _truthy
        else:
            out[k] = v
    # Vendor-scope an toàn: nếu caller (apply_vendor_scope) đã inject `asset IN
    # [allowed]`, KHÔNG được CLOBBER khi drill — phải GIAO (intersect) với tập
    # SoT, nếu không vendor sẽ thấy asset ngoài phạm vi. Pop ra để inject lại
    # sau khi đã giao.
    caller_asset_in = _extract_asset_in_scope(out.pop("asset", None))
    if overdue:
        out["next_due_date"] = ["<", nowdate()]
        out["is_active"] = 1
        # asset NOT decommissioned — chỉ schedule thuộc tập SoT overdue asset.
        out["asset"] = ("in", _scoped_asset_list(_overdue_asset_ids(), caller_asset_in))
    elif due_soon:
        # Card "Hiệu chuẩn đến hạn" — CÙNG cửa-sổ-2-biên + CÙNG asset-set với KPI
        # calib_due (=_due_soon_asset_ids, đã loại overdue). Overdue rows rơi RA.
        ref = nowdate()
        out["next_due_date"] = ["between", [ref, add_days(ref, CAL_DUE_SOON_WINDOW_DAYS)]]
        out["is_active"] = 1
        out["asset"] = ("in", _scoped_asset_list(_due_soon_asset_ids(), caller_asset_in))
    elif due_before:
        out["next_due_date"] = ["<=", due_before]
        out["is_active"] = 1
        # KHÔNG decommissioned. due_before là tập-bao (cutoff tùy ý, có thể vượt
        # window 30) → KHÔNG khoá theo SoT window; chỉ loại asset thanh lý.
        decom = _decommissioned_asset_ids()
        if caller_asset_in is not None:
            # Giữ vendor-scope: chỉ asset trong scope VÀ không decommissioned.
            allowed = [a for a in caller_asset_in if a not in decom]
            out["asset"] = ("in", allowed or [""])
        elif decom:
            out["asset"] = ("not in", list(decom))
    elif caller_asset_in is not None:
        # Không drill virtual nhưng caller có asset-scope → trả lại nguyên vẹn.
        out["asset"] = ("in", caller_asset_in)
    return _normalize_list_filters(out)


def _extract_asset_in_scope(asset_filter) -> list[str] | None:
    """Trích danh sách asset từ caller-filter `asset` dạng IN-list (vendor-scope).

    Hỗ trợ 2 shape Frappe: ``["in", [...]]`` / ``("in", [...])`` và list literal
    thuần ``[...]`` (sẽ được normalize thành IN). Shape khác (vd ('=', x)) →
    None (không can thiệp). Trả None nếu không có scope.
    """
    if asset_filter is None:
        return None
    if isinstance(asset_filter, (list, tuple)) and len(asset_filter) == 2 \
            and str(asset_filter[0]).lower() == "in" and isinstance(asset_filter[1], (list, tuple)):
        return [str(x) for x in asset_filter[1]]
    if isinstance(asset_filter, (list, tuple)) and not (
        len(asset_filter) == 2 and str(asset_filter[0]).lower() in (
            "in", "not in", "between", "like", "=", "!=", "<", ">", "<=", ">=")
    ):
        return [str(x) for x in asset_filter]
    return None


def _scoped_asset_list(sot_ids: set[str], caller_asset_in: list[str] | None) -> list[str]:
    """Giao tập SoT với caller-scope (nếu có). [""] khi rỗng để Frappe IN không
    match-all (tránh leak toàn bộ khi giao rỗng)."""
    if caller_asset_in is not None:
        sot_ids = sot_ids & set(caller_asset_in)
    return list(sot_ids) or [""]


def list_schedules(filters: dict | None = None, *, page: int = 1, page_size: int = 20) -> dict:
    # Server-side free-text search: pop the FE `search` key into an OR-LIKE
    # clause over name/asset (parent columns) + asset_name (linked AC Asset
    # display). pop_search runs AFTER the column filters (calibration_type /
    # is_active) and virtual keys (overdue / due_before) have been normalised
    # so search ANDs with them. apply_vendor_scope already injected the
    # `asset IN [...]` AND filter upstream — that survives because search only
    # adds an OR clause; scope is never bypassed.
    norm = _normalize_schedule_filters(filters)
    norm, or_filters = pop_search(
        norm,
        ["name", "asset"],
        link_search={"asset": ("AC Asset", "asset_name")},
    )
    # BaseRepository.list now counts via count_with_or when or_filters is set,
    # so pagination.total reflects the OR-search (no divergence vs rows).
    rows, pg = CalibrationScheduleRepo.list(
        filters=norm,
        or_filters=or_filters,
        fields=["name", "asset", "device_model", "calibration_type",
                "interval_days", "last_calibration_date", "next_due_date",
                "preferred_lab", "is_active"],
        order_by="next_due_date asc",
        page=page, page_size=page_size,
    )
    asset_ids = {r.get("asset") for r in rows if r.get("asset")}
    if asset_ids:
        asset_rows, _ = AssetRepo.list(
            filters={"name": ("in", list(asset_ids))},
            fields=["name", "asset_name"],
            page_size=len(asset_ids),
        )
        amap = {a["name"]: a.get("asset_name") for a in asset_rows}
        for r in rows:
            r["asset_name"] = amap.get(r.get("asset"), "")
    return {"data": rows, "pagination": pg}


def get_schedule(name: str) -> dict:
    doc = CalibrationScheduleRepo.get(name)
    if not doc:
        nthrow(MSG.IMM11_SCHEDULE_NOT_FOUND, name=name)
    return doc.as_dict()


def create_schedule(*, asset: str, calibration_type: str, interval_days: int,
                    preferred_lab: str | None = None,
                    next_due_date: str | None = None) -> dict:
    if not AssetRepo.exists(asset):
        nthrow(MSG.IMM11_ASSET_NOT_FOUND)
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
        nthrow(MSG.IMM11_SCHEDULE_NOT_FOUND, name=name)
    clean_patch = {k: v for k, v in patch.items() if k in allowed}
    if not clean_patch:
        nthrow(MSG.IMM11_NO_FIELDS)
    doc = CalibrationScheduleRepo.update_fields(name, clean_patch)
    return {"name": doc.name}


def delete_schedule(name: str) -> dict:
    if not CalibrationScheduleRepo.exists(name):
        nthrow(MSG.IMM11_SCHEDULE_NOT_FOUND, name=name)
    if CalibrationRepo.exists({"calibration_schedule": name, "docstatus": 1}):
        nthrow(MSG.IMM11_SCHEDULE_HAS_SUBMITTED)
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
    lab_ids = {r.get("lab_supplier") for r in rows if r.get("lab_supplier")}
    tech_ids = {r.get("technician") for r in rows if r.get("technician")}
    asset_map: dict = {}
    if asset_ids:
        asset_rows, _ = AssetRepo.list(
            filters={"name": ("in", list(asset_ids))},
            fields=["name", "asset_name"],
            page_size=len(asset_ids),
        )
        asset_map = {a["name"]: a.get("asset_name") for a in asset_rows}
    lab_map: dict = {}
    if lab_ids:
        lab_rows = frappe.get_all(
            "AC Supplier", filters={"name": ("in", list(lab_ids))},
            fields=["name", "supplier_name"],
        )
        lab_map = {l.name: l.supplier_name for l in lab_rows}
    tech_map: dict = {}
    if tech_ids:
        tech_rows = frappe.get_all(
            "User", filters={"name": ("in", list(tech_ids))},
            fields=["name", "full_name"],
        )
        tech_map = {t.name: t.full_name for t in tech_rows}
    for r in rows:
        r["asset_name"] = asset_map.get(r.get("asset"), r.get("asset") or "")
        r["lab_name"] = lab_map.get(r.get("lab_supplier"), r.get("lab_supplier") or "")
        r["technician_name"] = tech_map.get(r.get("technician"), r.get("technician") or "")
    return {"data": rows, "pagination": pg}


def get_calibration(name: str) -> dict:
    doc = CalibrationRepo.get(name)
    if not doc:
        nthrow(MSG.IMM11_CAL_NOT_FOUND, name=name)
    data = doc.as_dict()
    if data.get("asset"):
        data["asset_name"] = frappe.db.get_value("AC Asset", data["asset"], "asset_name") or ""
    tech = data.get("technician")
    data["technician_name"] = (
        frappe.db.get_value("User", tech, "full_name") or tech or ""
    ) if tech else ""
    # Server-driven CTA (mirror imm12.py:778 R3 + imm08.py:651 R21 + imm09.py:773 R22):
    # client render nút workflow trên màn calibration-detail theo SERVER (KHÔNG hardcode
    # status→button). Thành viên THỨ TƯ & CUỐI — ĐÓNG KÍN ASYMMETRY R3 (4/4 *Detail emit).
    data["allowed_transitions"] = _CAL_VALID_TRANSITIONS.get(doc.status, [])
    return data


def create_calibration(*, asset: str, calibration_type: str, scheduled_date: str,
                        technician: str, calibration_schedule: str | None = None,
                        lab_supplier: str | None = None,
                        is_recalibration: int = 0,
                        reference_standard_serial: str | None = None,
                        traceability_reference: str | None = None) -> dict:
    if not AssetRepo.exists(asset):
        nthrow(MSG.IMM11_ASSET_NOT_FOUND)
    asset_status = AssetRepo.get_value(asset, "lifecycle_status")
    if asset_status in AssetStatus.BLOCKED_FOR_WO and not int(is_recalibration):
        nthrow(MSG.IMM11_ASSET_BLOCKED)
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
        nthrow(MSG.IMM11_CAL_NOT_FOUND, name=name)
    if doc.docstatus == 1:
        nthrow(MSG.IMM11_ALREADY_SUBMITTED)
    clean_patch = {k: v for k, v in patch.items() if k in _UPDATE_ALLOWED}
    if not clean_patch:
        nthrow(MSG.IMM11_NO_FIELDS)
    old_status = doc.status
    doc = CalibrationRepo.update_fields(name, clean_patch)
    new_status = clean_patch.get("status", old_status)
    if new_status in _CALIBRATING_TRIGGER_STATUSES and old_status not in _CALIBRATING_TRIGGER_STATUSES:
        asset_status = AssetRepo.get_value(doc.asset, "lifecycle_status")
        if asset_status == AssetStatus.ACTIVE:
            _transition_asset(doc.asset, AssetStatus.CALIBRATING, name,
                              reason=f"Calibration {new_status} — {name}")
    return {"name": doc.name, "status": doc.status}


def submit_calibration(name: str) -> dict:
    doc = CalibrationRepo.get(name)
    if not doc:
        nthrow(MSG.IMM11_CAL_NOT_FOUND, name=name)
    if doc.docstatus == 1:
        nthrow(MSG.IMM11_ALREADY_SUBMITTED)
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
        nthrow(MSG.IMM11_CAL_NOT_FOUND, name=name)
    if doc.docstatus == 1:
        nthrow(MSG.IMM11_ALREADY_SUBMITTED)
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
    # BR-11-08: đếm theo SoT schedule (de-dup theo asset), KHÔNG đọc
    # AC Asset.calibration_status (cache) — loại gap asset minted chưa rollup.
    overdue_assets = len(_overdue_asset_ids())
    due_soon = len(_due_soon_asset_ids())
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

    # Overdue / Due Soon (top 10) — BR-11-08: theo cùng tập asset SoT (schedule
    # next_due_date), de-dup theo asset, order by next_due_date asc. KHÔNG đọc
    # AC Asset.calibration_status (cache) để khớp count KPI == drill == dashboard.
    overdue_assets = _top_assets_by_schedule(_overdue_asset_ids(), limit=10)
    due_soon_assets = _top_assets_by_schedule(_due_soon_asset_ids(), limit=10)

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


def send_to_lab(name: str, *, sent_date: str | None = None,
                lab_supplier: str | None = None,
                lab_contract_ref: str | None = None) -> dict:
    """External cal: In Progress/Scheduled → Sent To Lab."""
    doc = CalibrationRepo.get(name)
    if not doc:
        nthrow(MSG.IMM11_CAL_NOT_FOUND, name=name)
    if doc.docstatus == 1:
        nthrow(MSG.IMM11_ALREADY_SUBMITTED)
    if (doc.calibration_type or "") != "External":
        nthrow(MSG.IMM11_NOT_EXTERNAL)
    if doc.status not in (CalibrationResult.SCHEDULED, CalibrationResult.IN_PROGRESS):
        nthrow(MSG.IMM11_SEND_LAB_BAD_STATE, state=doc.status)

    patch: dict = {
        "status": CalibrationResult.SENT_TO_LAB,
        "sent_date": sent_date or nowdate(),
        "sent_by": frappe.session.user,
    }
    if lab_supplier:
        patch["lab_supplier"] = lab_supplier
    if lab_contract_ref:
        patch["lab_contract_ref"] = lab_contract_ref
    CalibrationRepo.update_fields(name, patch)

    cur = AssetRepo.get_value(doc.asset, "lifecycle_status")
    if cur == AssetStatus.ACTIVE:
        _transition_asset(doc.asset, AssetStatus.CALIBRATING, name,
                          reason=f"Sent to lab — {name}")
    log_audit_event(
        asset=doc.asset, event_type="Calibration Sent To Lab",
        actor=frappe.session.user, ref_doctype=_DT_CAL, ref_name=name,
        change_summary=f"Lab: {patch.get('lab_supplier') or doc.lab_supplier or ''}",
    )
    return {"name": name, "status": patch["status"], "sent_date": patch["sent_date"]}


def receive_certificate(name: str, *, certificate_file: str,
                        certificate_number: str,
                        certificate_date: str,
                        traceability_reference: str | None = None,
                        reference_standard_serial: str | None = None) -> dict:
    """External: Sent To Lab → In Progress (chờ kỹ thuật nhập measurement + submit)."""
    doc = CalibrationRepo.get(name)
    if not doc:
        nthrow(MSG.IMM11_CAL_NOT_FOUND, name=name)
    if doc.docstatus == 1:
        nthrow(MSG.IMM11_ALREADY_SUBMITTED)
    if doc.status != CalibrationResult.SENT_TO_LAB:
        nthrow(MSG.IMM11_RECEIVE_CERT_BAD_STATE)
    if not certificate_file or not certificate_number or not certificate_date:
        nthrow(MSG.IMM11_CERT_FIELDS_REQUIRED)

    patch: dict = {
        "certificate_file": certificate_file,
        "certificate_number": certificate_number,
        "certificate_date": certificate_date,
        "status": CalibrationResult.IN_PROGRESS,
    }
    if traceability_reference:
        patch["traceability_reference"] = traceability_reference
    if reference_standard_serial:
        patch["reference_standard_serial"] = reference_standard_serial
    CalibrationRepo.update_fields(name, patch)
    log_audit_event(
        asset=doc.asset, event_type="Calibration Certificate Received",
        actor=frappe.session.user, ref_doctype=_DT_CAL, ref_name=name,
        change_summary=f"Cert #{certificate_number} ngày {certificate_date}",
    )
    return {"name": name, "status": patch["status"],
            "certificate_number": certificate_number}


def cancel_calibration(name: str, reason: str) -> dict:
    """Hủy phiếu trước submit (BR-11-08 false-alarm / thiết bị decommissioned)."""
    doc = CalibrationRepo.get(name)
    if not doc:
        nthrow(MSG.IMM11_CAL_NOT_FOUND, name=name)
    if doc.docstatus == 1:
        nthrow(MSG.IMM11_CANCEL_SUBMITTED)
    if doc.status == CalibrationResult.CANCELLED:
        nthrow(MSG.IMM11_ALREADY_CANCELLED)
    if not reason or not reason.strip():
        nthrow(MSG.IMM11_CANCEL_REASON_REQUIRED)

    CalibrationRepo.update_fields(name, {
        "status": CalibrationResult.CANCELLED,
        "amendment_reason": f"[Cancelled] {reason}",
    })
    cur = AssetRepo.get_value(doc.asset, "lifecycle_status")
    if cur == AssetStatus.CALIBRATING:
        _transition_asset(doc.asset, AssetStatus.ACTIVE, name,
                          reason=f"Calibration cancelled — {name}")
    log_audit_event(
        asset=doc.asset, event_type="Calibration",
        actor=frappe.session.user, ref_doctype=_DT_CAL, ref_name=name,
        change_summary=reason[:200],
    )
    return {"name": name, "status": CalibrationResult.CANCELLED}


def get_due_calibrations(days: int = 30, limit: int = 50) -> dict:
    """Danh sách asset due_soon/overdue (≤ N ngày).

    CHỈ trả asset CÓ ``next_calibration_date`` đã set (có lịch hiệu chuẩn thật).
    Guard ``is set`` BẮT BUỘC: Frappe query-builder render ``<= threshold`` thành
    ``ifnull(next_calibration_date, '0001-01-01') <= threshold`` ⇒ nếu KHÔNG loại
    NULL, mọi asset chưa-có-lịch (next_calibration_date NULL) bị coerce
    '0001-01-01' và LỌT filter, sort ASC lên đầu, lấp kín ``limit`` → đẩy asset
    overdue thật khỏi due-list (sai KPI 'sắp đến hạn' + drill). Asset chưa-có-lịch
    KHÔNG phải 'đến hạn'.
    """
    today = nowdate()
    threshold = add_days(today, int(days))
    rows, _ = AssetRepo.list(
        filters=[
            ["lifecycle_status", "not in", [AssetStatus.DECOMMISSIONED]],
            ["next_calibration_date", "is", "set"],
            ["next_calibration_date", "<=", threshold],
        ],
        fields=["name", "asset_name", "device_model", "location",
                "next_calibration_date", "calibration_status"],
        order_by=_ORDER_NEXT_CAL_ASC,
        page_size=int(limit),
    )
    today_d = getdate(today)
    for r in rows:
        nd = r.get("next_calibration_date")
        r["days_left"] = date_diff(nd, today_d) if nd else None
    return {"items": rows, "threshold_days": int(days)}


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
