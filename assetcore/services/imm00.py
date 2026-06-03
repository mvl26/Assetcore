# Copyright (c) 2026, AssetCore Team
"""IMM-00 Foundation Service Layer — v3.0.0

Nguyên tắc: controllers chỉ gọi service; business logic tập trung ở đây.
"""
import frappe
from frappe import _
from frappe.utils import add_days, nowdate

from assetcore.utils.lifecycle import (
    log_audit_event as _log_audit_event,
    create_lifecycle_event as _create_lifecycle_event,
    verify_audit_chain as _verify_audit_chain,
)
from assetcore.utils.email import get_role_emails, safe_sendmail
from assetcore.services.shared import AssetStatus
from assetcore.services.shared import rbac


_DOCTYPE_ASSET = "AC Asset"
_DOCTYPE_CAPA = "IMM CAPA Record"

_STATUS_DRAFT             = AssetStatus.DRAFT
_STATUS_COMMISSIONED      = AssetStatus.COMMISSIONED
_STATUS_ACTIVE            = AssetStatus.ACTIVE
_STATUS_UNDER_MAINTENANCE = AssetStatus.UNDER_MAINTENANCE
_STATUS_UNDER_REPAIR      = AssetStatus.UNDER_REPAIR
_STATUS_CALIBRATING       = AssetStatus.CALIBRATING
_STATUS_OUT_OF_SERVICE    = AssetStatus.OUT_OF_SERVICE
_STATUS_DECOMMISSIONED    = AssetStatus.DECOMMISSIONED
_BLOCKED_STATUSES  = AssetStatus.BLOCKED_FOR_WO
_DOWNTIME_STATUSES = AssetStatus.DOWNTIME
_DOWNTIME_REASON_MAP = {
    AssetStatus.UNDER_MAINTENANCE: "Bảo trì",
    AssetStatus.UNDER_REPAIR:      "Sửa chữa",
    AssetStatus.CALIBRATING:       "Hiệu chuẩn",
    AssetStatus.OUT_OF_SERVICE:    "Hỏng hóc",
}
_DT_DOWNTIME_LOG = "AC Asset Downtime Log"

_ROLE_DEPT_HEAD  = "Commissioning Manager"
_ROLE_OPS_MANAGER = "Commissioning Manager"

# ────────────────────────────────────────────
# Asset Lifecycle State Machine (BR-00-02)
# ────────────────────────────────────────────
# Định nghĩa các transition hợp lệ. KHÔNG có entry trong dict = trạng thái cuối.
# Sửa ở đây = sửa luôn workflow JSON: assetcore/workflow/ac_asset_lifecycle_workflow.json
_VALID_ASSET_TRANSITIONS: dict[str, set[str]] = {
    _STATUS_DRAFT:            {_STATUS_COMMISSIONED, _STATUS_DECOMMISSIONED},
    _STATUS_COMMISSIONED:     {_STATUS_ACTIVE, _STATUS_OUT_OF_SERVICE, _STATUS_DECOMMISSIONED},
    _STATUS_ACTIVE:           {_STATUS_UNDER_MAINTENANCE, _STATUS_UNDER_REPAIR,
                               _STATUS_CALIBRATING, _STATUS_OUT_OF_SERVICE,
                               _STATUS_DECOMMISSIONED},
    _STATUS_UNDER_MAINTENANCE:{_STATUS_ACTIVE, _STATUS_UNDER_REPAIR,
                               _STATUS_OUT_OF_SERVICE, _STATUS_DECOMMISSIONED},
    _STATUS_UNDER_REPAIR:     {_STATUS_ACTIVE, _STATUS_OUT_OF_SERVICE, _STATUS_DECOMMISSIONED},
    _STATUS_CALIBRATING:      {_STATUS_ACTIVE, _STATUS_OUT_OF_SERVICE, _STATUS_DECOMMISSIONED},
    _STATUS_OUT_OF_SERVICE:   {_STATUS_ACTIVE, _STATUS_UNDER_REPAIR, _STATUS_DECOMMISSIONED},
    _STATUS_DECOMMISSIONED:   set(),  # terminal
}


class InvalidAssetTransition(Exception):
    """Raised khi transition không nằm trong _VALID_ASSET_TRANSITIONS."""


# ────────────────────────────────────────────
# Audit + Lifecycle (re-export from utils)
# ────────────────────────────────────────────

def log_audit_event(**kwargs) -> str:
    """Re-export: ghi 1 entry vào IMM Audit Trail (SHA-256 chain). Xem utils.lifecycle."""
    return _log_audit_event(**kwargs)


def create_lifecycle_event(**kwargs) -> str:
    """Re-export: ghi 1 row Asset Lifecycle Event (append-only). Xem utils.lifecycle."""
    return _create_lifecycle_event(**kwargs)


def verify_audit_chain(asset: str) -> dict:
    """Re-export: xác minh toàn bộ hash chain của audit trail cho 1 asset."""
    return _verify_audit_chain(asset)


# ────────────────────────────────────────────
# Asset status transitions (BR-00-02, 04, 05, 10)
# ────────────────────────────────────────────

def transition_asset_status(
    asset_name: str,
    to_status: str,
    actor: str | None = None,
    reason: str = "",
    root_doctype: str | None = None,
    root_record: str | None = None,
) -> None:
    """Chuyển lifecycle_status của AC Asset theo state machine (BR-00-02).

    Ghi lifecycle event + audit trail + mở/đóng downtime log tự động.
    Raises InvalidAssetTransition nếu transition không hợp lệ.
    """
    prev_status = frappe.db.get_value(_DOCTYPE_ASSET, asset_name, "lifecycle_status") or ""
    if prev_status == to_status:
        return

    # State machine guard — chỉ cho phép transition đã định nghĩa.
    # Nếu prev_status rỗng (asset mới insert), không validate (asset chưa đi vào lifecycle).
    if prev_status:
        allowed = _VALID_ASSET_TRANSITIONS.get(prev_status, set())
        if to_status not in allowed:
            allowed_str = ", ".join(sorted(allowed)) or "(không có)"
            raise InvalidAssetTransition(
                f"Không thể chuyển '{asset_name}' từ '{prev_status}' → '{to_status}'. "
                f"Trạng thái cho phép từ '{prev_status}': {allowed_str}"
            )

    # NEG-09: chặn "Thanh lý" (Decommission) khi thiết bị đang trong dây chuyền
    # bảo trì/hiệu chuẩn/sửa chữa. Bắt buộc đóng phiếu PM/CM/Cal hoặc đưa về
    # Active trước khi thanh lý — tránh treo Work Order mồ côi.
    _BLOCK_DECOM_FROM = {
        _STATUS_UNDER_MAINTENANCE: "Bảo trì",
        _STATUS_UNDER_REPAIR:      "Sửa chữa",
        _STATUS_CALIBRATING:       "Hiệu chuẩn",
    }
    if to_status == _STATUS_DECOMMISSIONED and prev_status in _BLOCK_DECOM_FROM:
        flow = _BLOCK_DECOM_FROM[prev_status]
        raise InvalidAssetTransition(
            f"NEG-09: Không thể thanh lý '{asset_name}' khi đang ở trạng thái "
            f"'{prev_status}' ({flow}). Vui lòng đóng/hoàn tất phiếu {flow} hoặc "
            f"đưa thiết bị về 'Active' trước khi thanh lý."
        )

    frappe.db.set_value(_DOCTYPE_ASSET, asset_name, "lifecycle_status", to_status)

    create_lifecycle_event(
        asset=asset_name,
        event_type=_lifecycle_event_for(to_status),
        actor=actor or frappe.session.user,
        from_status=prev_status,
        to_status=to_status,
        root_doctype=root_doctype,
        root_record=root_record,
        notes=reason,
    )
    log_audit_event(
        asset=asset_name,
        event_type="State Change",
        actor=actor or frappe.session.user,
        ref_doctype=root_doctype or _DOCTYPE_ASSET,
        ref_name=root_record or asset_name,
        change_summary=f"lifecycle_status: {prev_status} -> {to_status}. {reason}",
        from_status=prev_status,
        to_status=to_status,
    )

    _sync_downtime_log(
        asset=asset_name, prev=prev_status, nxt=to_status,
        root_doctype=root_doctype, root_record=root_record, reason_note=reason,
    )

    if to_status == _STATUS_DECOMMISSIONED:
        _suspend_all_schedules(asset_name)


def _sync_downtime_log(*, asset: str, prev: str, nxt: str,
                        root_doctype: str | None, root_record: str | None,
                        reason_note: str) -> None:
    """Tự động open/close AC Asset Downtime Log theo transition.
    - Vào downtime status → open log mới
    - Ra khỏi downtime status → close log đang mở
    - Downtime → Downtime (vd: Under Repair → Out of Service) → close log cũ + open log mới
    """
    was_down = prev in _DOWNTIME_STATUSES
    is_down = nxt in _DOWNTIME_STATUSES
    if was_down:
        _close_open_downtime_log(asset)
    if is_down:
        _open_downtime_log(
            asset=asset, reason=_DOWNTIME_REASON_MAP.get(nxt, "Khác"),
            ref_dt=root_doctype, ref_name=root_record, note=reason_note,
        )


def _open_downtime_log(*, asset: str, reason: str, ref_dt: str | None,
                        ref_name: str | None, note: str) -> str:
    doc = frappe.get_doc({
        "doctype": _DT_DOWNTIME_LOG,
        "asset": asset,
        "reason": reason,
        "reference_doctype": ref_dt,
        "reference_name": ref_name,
        "start_time": frappe.utils.now_datetime(),
        "is_open": 1,
        "notes": note or "",
    })
    doc.insert(ignore_permissions=True)
    return doc.name


def _close_open_downtime_log(asset: str) -> None:
    rows = frappe.get_all(
        _DT_DOWNTIME_LOG,
        filters={"asset": asset, "is_open": 1},
        fields=["name"], limit=5,
    )
    if not rows:
        return
    now_dt = frappe.utils.now_datetime()
    for r in rows:
        doc = frappe.get_doc(_DT_DOWNTIME_LOG, r["name"])
        doc.end_time = now_dt
        doc.is_open = 0
        doc.save(ignore_permissions=True)


def _lifecycle_event_for(to_status: str) -> str:
    return {
        "Active": "activated",
        "Commissioned": "commissioned",
        "Under Maintenance": "pm_started",
        "Under Repair": "repair_opened",
        "Calibrating": "calibration_started",
        "Out of Service": "out_of_service",
        "Decommissioned": "decommissioned",
    }.get(to_status, "restored")


def _suspend_all_schedules(asset_name: str) -> None:
    """BR-00-04: Decommissioned -> tat co PM/Cal tren AC Asset."""
    frappe.db.set_value(_DOCTYPE_ASSET, asset_name, {
        "is_pm_required": 0,
        "is_calibration_required": 0,
        "next_pm_date": None,
        "next_calibration_date": None,
    })


def validate_asset_for_operations(asset_name: str) -> None:
    """BR-00-05: Out of Service / Decommissioned -> block tao Work Order."""
    status = frappe.db.get_value(_DOCTYPE_ASSET, asset_name, "lifecycle_status")
    if status in _BLOCKED_STATUSES:
        frappe.throw(_("Không thể tạo Work Order — thiết bị đang ở trạng thái '{0}' (BR-00-05).").format(status))


# ────────────────────────────────────────────
# SLA Policy lookup (BR-00-07)
# ────────────────────────────────────────────

def get_sla_policy(priority: str, risk_class: str | None = None) -> dict:
    """Trả về SLA Policy phù hợp theo (priority, risk_class).

    Fallback: nếu không có policy theo risk_class, dùng is_default=1 cho priority đó.
    Trả dict rỗng {} nếu không tìm thấy policy nào.
    """
    rows = frappe.db.get_all(
        "IMM SLA Policy",
        filters={"priority": priority, "risk_class": risk_class, "is_active": 1},
        fields=["name", "response_time_minutes", "resolution_time_hours",
                "escalation_l1_user", "escalation_l2_user"],
        limit=1,
    )
    if rows:
        return rows[0]
    rows = frappe.db.get_all(
        "IMM SLA Policy",
        filters={"priority": priority, "is_default": 1, "is_active": 1},
        fields=["name", "response_time_minutes", "resolution_time_hours",
                "escalation_l1_user", "escalation_l2_user"],
        limit=1,
    )
    return rows[0] if rows else {}


# ────────────────────────────────────────────
# CAPA lifecycle
# ────────────────────────────────────────────

def create_capa(asset: str, source_type: str, source_ref: str, severity: str,
                description: str, responsible: str, due_days: int = 30) -> str:
    """Tạo IMM CAPA Record và ghi audit trail. Trả về name của bản ghi mới."""
    doc = frappe.get_doc({
        "doctype": _DOCTYPE_CAPA,
        "asset": asset,
        "source_type": source_type,
        "source_ref": source_ref,
        "severity": severity,
        "description": description,
        "responsible": responsible,
        "opened_date": nowdate(),
        "due_date": add_days(nowdate(), due_days),
        "status": "Open",
    }).insert(ignore_permissions=True)
    # B-IMM16-3 (2026-05-26): Vietnamese severity label trong audit summary
    _SEVERITY_VI = {
        "Minor": "Nhỏ", "Major": "Nghiêm trọng",
        "Critical": "Khẩn cấp", "Catastrophic": "Thảm khốc",
        "Low": "Thấp", "Medium": "Trung bình", "High": "Cao",
    }
    severity_vi = _SEVERITY_VI.get(severity, severity)
    log_audit_event(
        asset=asset, event_type="CAPA", actor=frappe.session.user,
        ref_doctype=_DOCTYPE_CAPA, ref_name=doc.name,
        change_summary=_("Đã mở CAPA: mức {0}").format(severity_vi),
    )
    return doc.name


def close_capa(capa_name: str, root_cause: str, corrective_action: str,
               preventive_action: str, effectiveness_check: str | None = None,
               actor: str | None = None) -> None:
    """Submit và đóng CAPA Record với kết quả khắc phục. Ghi audit trail."""
    doc = frappe.get_doc(_DOCTYPE_CAPA, capa_name)
    doc.root_cause = root_cause
    doc.corrective_action = corrective_action
    doc.preventive_action = preventive_action
    if effectiveness_check:
        doc.effectiveness_check = effectiveness_check
    doc.status = "Closed"
    doc.closed_date = nowdate()
    doc.submit()
    log_audit_event(
        asset=doc.asset, event_type="CAPA", actor=actor or frappe.session.user,
        ref_doctype=_DOCTYPE_CAPA, ref_name=capa_name,
        change_summary="CAPA closed",
    )


# ────────────────────────────────────────────
# CAPA "quá hạn" — Single Source of Truth (BR-00-09)
# ────────────────────────────────────────────
# INVARIANT (authoritative, bất biến dưới cron status-flip):
#   overdue  ⟺  status NOT IN ('Closed')
#               AND due_date IS NOT NULL
#               AND due_date < ref_date           (strict <; due_date == today CHƯA quá hạn)
#
# Hệ quả thiết kế:
#   - 'Overdue'-status CAPA VẪN được đếm là overdue (vì 'Overdue' NOT IN 'Closed') →
#     count KHÔNG tụt sau khi check_capa_overdue() flip status Open/In Progress/Pending
#     Verification → 'Overdue'. Đây là điều kiện "invariant under cron".
#   - due_date IS NULL KHÔNG BAO GIỜ là overdue (loại tường minh ở cả predicate lẫn SQL).
#   - MỌI consumer (KPI dashboard, scorecard, quality-dash, drill list, get_overdue_actions)
#     PHẢI gọi _overdue_capa_filter() — KHÔNG inline {status NOT IN Closed + due_date<today}.

_CAPA_TERMINAL_STATUSES: tuple[str, ...] = ("Closed",)
# Source-states cron có thể flip → 'Overdue': mọi state non-terminal mà KPI ĐẾM
# nhưng chưa phải 'Overdue'. (Open, In Progress, Pending Verification.)
_CAPA_FLIPPABLE_STATUSES: tuple[str, ...] = ("Open", "In Progress", "Pending Verification")


# ────────────────────────────────────────────
# CAPA "đang xử lý / chưa đóng" (capa_open) — Single Source of Truth (BR-00-15)
# ────────────────────────────────────────────
# INVARIANT (authoritative, bất biến dưới cron status-flip):
#   open  ⟺  status NOT IN ('Closed')
#
# 'open' là SUPERSET của 'overdue' (round-10): mọi CAPA quá hạn vẫn là CAPA đang mở,
# vì 'Overdue' NOT IN 'Closed'. Hệ quả:
#   - Cron check_capa_overdue() flip Open/In Progress/Pending Verification → 'Overdue'
#     KHÔNG làm capa_open count thay đổi ('Overdue' vẫn NOT IN 'Closed').
#   - MỌI consumer (KPI dashboard, scorecard capa_open_count, quality-dash capa_open,
#     drill list_capas not_closed, get_capa_aging total_open) PHẢI gọi _open_capa_filter()
#     — KHÔNG inline {status IN [Open, In Progress, ...]} (bỏ sót Overdue/Pending Verification).


def is_capa_open(status: str | None) -> bool:
    """Predicate thuần SoT: 1 CAPA có đang mở (chưa đóng) không?

    open ⟺ status NOT IN ('Closed'). 'open' là superset của 'overdue' — CAPA
    'Overdue' VẪN đang mở (chưa được đóng). status None/rỗng → coi như mở (chưa đóng).
    """
    return status not in _CAPA_TERMINAL_STATUSES


def _open_capa_filter() -> dict:
    """Filter-builder SoT cho frappe.db.count / get_all / get_list.

    Trả dict filter khớp byte-for-byte INVARIANT: status NOT IN ('Closed').
    Đây là superset của _overdue_capa_filter() (overdue = open ∩ due_date<today).
    """
    return {"status": ["not in", list(_CAPA_TERMINAL_STATUSES)]}


def is_capa_overdue(status: str | None, due_date, ref_date=None) -> bool:
    """Predicate thuần SoT: 1 CAPA có quá hạn tại ref_date không?

    overdue ⟺ status NOT IN ('Closed') AND due_date IS NOT NULL AND due_date < ref_date.
    ref_date mặc định = nowdate() (hôm nay). due_date == ref_date → CHƯA quá hạn (strict <).
    """
    if due_date is None or due_date == "":
        return False
    if status in _CAPA_TERMINAL_STATUSES:
        return False
    from frappe.utils import getdate
    ref = getdate(ref_date) if ref_date else getdate(nowdate())
    return getdate(due_date) < ref


_CAPA_DUE_DATE_FLOOR = "1000-01-01"  # MariaDB DATE min — null-guard sentinel cho 'between'


def _overdue_capa_filter(ref_date: str | None = None) -> dict:
    """Filter-builder SoT cho frappe.db.count / get_all / get_list.

    Trả dict filter khớp byte-for-byte INVARIANT ở trên:
        status NOT IN ('Closed') AND due_date IS NOT NULL AND due_date < ref_date.
    Dùng 'between' [FLOOR, ref-1]: cận trên = ref-1 (inclusive) ⟺ due_date < ref (strict);
    cận dưới = MariaDB DATE min → due_date IS NULL/rỗng bị loại TƯỜNG MINH (null-guard,
    không phụ thuộc hành vi NULL-comparison của SQL).
    """
    ref = ref_date or nowdate()
    return {
        "status": ["not in", list(_CAPA_TERMINAL_STATUSES)],
        "due_date": ["between", [_CAPA_DUE_DATE_FLOOR, add_days(ref, -1)]],
    }


# ────────────────────────────────────────────
# Filter-composition (conjoin) — list-of-conditions adapter (BR-00-16)
# ────────────────────────────────────────────
# Frappe dict-filter giữ TỐI ĐA 1 predicate / field → KHÔNG thể conjoin 2 ràng buộc
# trên CÙNG field (vd explicit `status == 'Overdue'` AND virtual `status NOT IN [Closed]`).
# Dạng list-of-conditions `[[doctype, field, op, value], ...]` cho phép NHIỀU điều kiện
# trên cùng field, AND với nhau. _as_conditions() là 1 SoT adapter: biến CHÍNH các dict
# SoT (_open_capa_filter / _overdue_capa_filter) thành list-form — KHÔNG nhân bản literal
# predicate (tránh 2 chân lý). Membership KHÔNG đổi (round 10/11/12 no-regression).

def _as_conditions(filt: dict, doctype: str) -> list[list]:
    """Biến dict-filter SoT → list-of-conditions `[[doctype, field, op, value], ...]`.

    Quy ước (khớp shape của _open_capa_filter / _overdue_capa_filter):
      - `{field: [op, value]}`  → `[doctype, field, op, value]`  (vd ["not in", [...]]).
      - `{field: value}`        → `[doctype, field, "=", value]` (scalar shorthand).

    Cho phép gọi-bên append thêm condition trên CÙNG field (vd explicit status) →
    conjoin AND thật. count + get_list nhận CÙNG list → parity total == len(items).
    """
    conditions: list[list] = []
    for field, spec in filt.items():
        if isinstance(spec, (list, tuple)) and len(spec) == 2 and isinstance(spec[0], str):
            # [op, value] — vd ["not in", ["Closed"]] hoặc ["between", [lo, hi]].
            conditions.append([doctype, field, spec[0], spec[1]])
        else:
            # Scalar shorthand: bằng nhau.
            conditions.append([doctype, field, "=", spec])
    return conditions


def _open_capa_conditions(doctype: str) -> list[list]:
    """SoT-adjacent: _open_capa_filter() ở dạng list-of-conditions (1 SoT, dict+list)."""
    return _as_conditions(_open_capa_filter(), doctype)


def _overdue_capa_conditions(doctype: str, ref_date: str | None = None) -> list[list]:
    """SoT-adjacent: _overdue_capa_filter() ở dạng list-of-conditions (1 SoT, dict+list)."""
    return _as_conditions(_overdue_capa_filter(ref_date), doctype)


# ────────────────────────────────────────────
# Scheduler jobs
# ────────────────────────────────────────────

def check_capa_overdue() -> None:
    """Scheduler daily (BR-00-09): flip CAPA quá hạn → 'Overdue', email cảnh báo QA.

    Source-states = _CAPA_FLIPPABLE_STATUSES (Open/In Progress/Pending Verification) —
    mọi state non-terminal mà KPI ĐẾM nhưng chưa là 'Overdue'. Idempotent: KHÔNG re-flip
    CAPA đã 'Overdue', KHÔNG động 'Closed'. Cùng INVARIANT với _overdue_capa_filter()
    (NOT IN Closed AND due_date IS NOT NULL AND due_date < today) → count bất biến.
    """
    placeholders = ", ".join(["%s"] * len(_CAPA_FLIPPABLE_STATUSES))
    rows = frappe.db.sql(
        f"""
        SELECT name, asset, responsible, due_date
        FROM `tabIMM CAPA Record`
        WHERE status IN ({placeholders})
          AND due_date IS NOT NULL
          AND due_date < %s
        """,
        (*_CAPA_FLIPPABLE_STATUSES, nowdate()),
        as_dict=True,
    )
    if not rows:
        return
    names = [r.name for r in rows]
    frappe.db.sql(
        f"UPDATE `tabIMM CAPA Record` SET status = 'Overdue' WHERE name IN ({', '.join(['%s'] * len(names))})",
        names,
    )
    recipients = set(get_role_emails(["Compliance Manager"]))
    recipients.update([r.responsible for r in rows if r.responsible])
    recipients.discard("")
    if recipients:
        body = "\n".join(f"- {r.name} | {r.asset} | due {r.due_date}" for r in rows)
        safe_sendmail(list(recipients), f"[AssetCore] {len(rows)} CAPA overdue",
                      f"Cac CAPA sau da qua han:\n\n{body}")


def check_vendor_contract_expiry() -> None:
    """Scheduler daily: cảnh báo hợp đồng nhà cung cấp sắp hết hạn (90/60/30 ngày)."""
    thresholds = [90, 60, 30]
    recipients = get_role_emails([_ROLE_DEPT_HEAD])
    if not recipients:
        return
    for d in thresholds:
        target = add_days(nowdate(), d)
        rows = frappe.db.get_all(
            "AC Supplier",
            filters={"contract_end": target, "is_active": 1},
            fields=["name", "supplier_name", "contract_end"],
        )
        if rows:
            body = "\n".join(f"- {r.name} | {r.supplier_name} | ket thuc {r.contract_end}" for r in rows)
            safe_sendmail(recipients, f"[AssetCore] HD NCC con {d} ngay",
                          f"{len(rows)} hop dong NCC sap het han trong {d} ngay:\n\n{body}")


def check_registration_expiry() -> None:
    """Scheduler daily: cảnh báo đăng ký BYT sắp hết hạn (90/60/30/7 ngày)."""
    thresholds = [90, 60, 30, 7]
    recipients = get_role_emails([_ROLE_DEPT_HEAD])
    if not recipients:
        return
    for d in thresholds:
        target = add_days(nowdate(), d)
        rows = frappe.db.get_all(
            _DOCTYPE_ASSET,
            filters={
                "byt_reg_expiry": target,
                "lifecycle_status": ("!=", _STATUS_DECOMMISSIONED),
            },
            fields=["name", "asset_name", "byt_reg_no", "byt_reg_expiry"],
        )
        if rows:
            body = "\n".join(f"- {r.name} | {r.asset_name} | BYT {r.byt_reg_no} | {r.byt_reg_expiry}" for r in rows)
            safe_sendmail(recipients, f"[AssetCore] Dang ky BYT con {d} ngay",
                          f"{len(rows)} thiet bi co dang ky BYT sap het han trong {d} ngay:\n\n{body}")


# ────────────────────────────────────────────
# Số đăng ký lưu hành BYT "sắp/đã hết hạn" — Single Source of Truth (BR-00-17, NĐ98)
# ────────────────────────────────────────────
# Bối cảnh NĐ98/2021: thiết bị y tế lưu hành tại VN phải có "Số đăng ký lưu hành"
# (byt_reg_expiry). Khi số ĐK sắp/đã hết hạn → rủi ro pháp lý (không được sử dụng /
# phải gia hạn). KPI quản trị cần nổi 2 chỉ tiêu này, click drill xuống danh sách
# thiết bị tương ứng — count KPI PHẢI bằng số dòng list (INVARIANT count==drill).
#
# INVARIANT (authoritative, dùng CHUNG cho KPI count + list drill):
#   'expiring' ⟺ byt_reg_expiry BETWEEN [today, today + BYT_EXPIRY_SOON_DAYS]
#   'expired'  ⟺ byt_reg_expiry < today  (strict; expiry == today CHƯA hết hạn)
# Cả 2 bucket LOẠI bản ghi byt_reg_expiry IS NULL / '' (chưa khai báo số ĐK
# KHÔNG phải "hết hạn" — không đếm, không leak vào danh sách rủi ro). Null-guard
# tường minh qua cận dưới 'between' = MariaDB DATE min (không phụ thuộc hành vi
# NULL-comparison của SQL).
#
# MỌI consumer (KPI dashboard get_overview, list_assets drill, scheduler) PHẢI
# gọi byt_expiry_filter() — KHÔNG inline literal window 'byt_reg_expiry'.
BYT_EXPIRY_SOON_DAYS = 30
_BYT_EXPIRY_DATE_FLOOR = "1000-01-01"  # MariaDB DATE min — null-guard sentinel cho 'between'
_BYT_EXPIRY_BUCKETS: tuple[str, ...] = ("expiring", "expired")


def byt_expiry_filter(bucket: str, ref_date: str | None = None) -> dict:
    """Filter-builder SoT cho số ĐK lưu hành BYT sắp/đã hết hạn (NĐ98).

    Args:
        bucket: ``"expiring"`` (trong [today, today+BYT_EXPIRY_SOON_DAYS]) hoặc
            ``"expired"`` (byt_reg_expiry < today). Giá trị khác → ``{}`` (no-op,
            KHÔNG raise) để caller (list_assets) bỏ qua an toàn.
        ref_date: mốc "hôm nay" (mặc định ``nowdate()``). Test bơm ngày cố định.

    Returns:
        dict — filter dict cho ``frappe.db.count`` / ``get_list``. Mọi bucket hợp
        lệ ĐỀU loại byt_reg_expiry IS NULL/'' (chưa khai báo số ĐK ≠ "hết hạn") qua
        cận dưới 'between' = MariaDB DATE min (null-guard tường minh).

    Invariant (NĐ98): KPI count == số dòng list khi dùng CHUNG filter này — không
    inline literal window. 'expiring' và 'expired' rời nhau (disjoint).
    """
    ref = ref_date or nowdate()
    if bucket == "expiring":
        return {"byt_reg_expiry": ["between", [ref, add_days(ref, BYT_EXPIRY_SOON_DAYS)]]}
    if bucket == "expired":
        # between [FLOOR, ref-1]: cận trên = ref-1 (inclusive) ⟺ expiry < ref (strict);
        # cận dưới = DATE min → NULL/'' bị loại tường minh (null-guard).
        return {"byt_reg_expiry": ["between", [_BYT_EXPIRY_DATE_FLOOR, add_days(ref, -1)]]}
    return {}  # bucket không hợp lệ → no-op


_DT_TRANSFER = "Asset Transfer"
_TRANSFER_APPROVE_CAP = "commissioning.submit"
_ERR_TRANSFER_NOT_FOUND = "Phiếu luân chuyển '{0}' không tồn tại"
_TRANSFER_STATUS_PENDING   = "Pending Approval"
_TRANSFER_STATUS_APPROVED  = "Approved"
_TRANSFER_STATUS_REJECTED  = "Rejected"
_TRANSFER_STATUS_RECEIVED  = "Received"
_TRANSFER_STATUS_CANCELLED = "Cancelled"


def create_transfer_request(data: dict) -> dict:
    """Tạo phiếu yêu cầu luân chuyển thiết bị (status = Pending Approval).

    data: asset, transfer_type, to_location, reason
          [to_department, to_custodian, expected_return_date, notes]
    """
    required = ("asset", "transfer_type", "to_location", "reason")
    missing = [f for f in required if not data.get(f)]
    if missing:
        frappe.throw(_("Thiếu trường bắt buộc: {0}").format(", ".join(missing)))

    asset_name = data["asset"]
    if not frappe.db.exists(_DOCTYPE_ASSET, asset_name):
        frappe.throw(_("Thiết bị '{0}' không tồn tại").format(asset_name))

    prev = frappe.db.get_value(
        _DOCTYPE_ASSET, asset_name,
        ["location", "department", "custodian"], as_dict=True,
    ) or {}

    doc = frappe.new_doc(_DT_TRANSFER)
    doc.asset          = asset_name
    doc.transfer_date  = data.get("transfer_date") or nowdate()
    doc.transfer_type  = data["transfer_type"]
    doc.from_location  = prev.get("location")
    doc.from_department= prev.get("department")
    doc.from_custodian = prev.get("custodian")
    doc.to_location    = data["to_location"]
    doc.to_department  = data.get("to_department")
    doc.to_custodian   = data.get("to_custodian")
    doc.expected_return_date = data.get("expected_return_date")
    doc.reason         = data["reason"]
    doc.notes          = data.get("notes")
    doc.status         = _TRANSFER_STATUS_PENDING
    doc.insert(ignore_permissions=False)

    _notify_transfer_approvers(doc)
    log_audit_event(
        asset=asset_name, event_type="Transfer",
        actor=frappe.session.user,
        ref_doctype=_DT_TRANSFER, ref_name=doc.name,
        change_summary=f"Yêu cầu luân chuyển đến {data['to_location']}",
    )
    frappe.db.commit()
    return {"name": doc.name, "status": doc.status}


def approve_transfer_request(name: str) -> dict:
    """Phê duyệt phiếu luân chuyển: cập nhật vị trí thiết bị ngay."""
    if not frappe.db.exists(_DT_TRANSFER, name):
        frappe.throw(_(_ERR_TRANSFER_NOT_FOUND).format(name))

    rbac.require(_TRANSFER_APPROVE_CAP)

    doc = frappe.get_doc(_DT_TRANSFER, name)
    if doc.status != _TRANSFER_STATUS_PENDING:
        frappe.throw(_("Phiếu đang ở trạng thái '{0}', không thể phê duyệt").format(doc.status))

    frappe.db.set_value(_DT_TRANSFER, name, {
        "status":        _TRANSFER_STATUS_APPROVED,
        "approved_by":   frappe.session.user,
        "approval_date": nowdate(),
    })

    transfer_asset(
        asset_name=doc.asset,
        to_location=doc.to_location,
        to_department=doc.to_department,
        to_custodian=doc.to_custodian,
        transfer_doc=name,
        actor=frappe.session.user,
    )

    _notify_transfer_requester(doc, approved=True)
    frappe.db.commit()
    return {"name": name, "status": _TRANSFER_STATUS_APPROVED}


def reject_transfer_request(name: str, rejection_reason: str) -> dict:
    """Từ chối phiếu luân chuyển."""
    if not frappe.db.exists(_DT_TRANSFER, name):
        frappe.throw(_(_ERR_TRANSFER_NOT_FOUND).format(name))

    rbac.require(_TRANSFER_APPROVE_CAP)

    if not rejection_reason or len(rejection_reason.strip()) < 5:
        frappe.throw(_("Lý do từ chối là bắt buộc (tối thiểu 5 ký tự)"))

    doc = frappe.get_doc(_DT_TRANSFER, name)
    if doc.status != _TRANSFER_STATUS_PENDING:
        frappe.throw(_("Phiếu đang ở trạng thái '{0}', không thể từ chối").format(doc.status))

    frappe.db.set_value(_DT_TRANSFER, name, {
        "status":           _TRANSFER_STATUS_REJECTED,
        "rejected_by":      frappe.session.user,
        "rejection_reason": rejection_reason.strip(),
    })

    log_audit_event(
        asset=doc.asset, event_type="Transfer",
        actor=frappe.session.user,
        ref_doctype=_DT_TRANSFER, ref_name=name,
        change_summary=f"Từ chối: {rejection_reason}",
    )
    _notify_transfer_requester(doc, approved=False)
    frappe.db.commit()
    return {"name": name, "status": _TRANSFER_STATUS_REJECTED}


def confirm_receipt(name: str, handover_notes: str = "") -> dict:
    """Bên nhận xác nhận đã tiếp nhận thiết bị (status → Received)."""
    if not frappe.db.exists(_DT_TRANSFER, name):
        frappe.throw(_(_ERR_TRANSFER_NOT_FOUND).format(name))

    doc = frappe.get_doc(_DT_TRANSFER, name)
    if doc.status != _TRANSFER_STATUS_APPROVED:
        frappe.throw(_("Phiếu phải ở trạng thái 'Approved' trước khi xác nhận tiếp nhận"))

    updates: dict = {
        "status":        _TRANSFER_STATUS_RECEIVED,
        "received_by":   frappe.session.user,
        "received_date": nowdate(),
    }
    if handover_notes:
        updates["handover_notes"] = handover_notes
    frappe.db.set_value(_DT_TRANSFER, name, updates)

    log_audit_event(
        asset=doc.asset, event_type="Transfer",
        actor=frappe.session.user,
        ref_doctype=_DT_TRANSFER, ref_name=name,
        change_summary=f"Tiếp nhận tại {doc.to_location}",
    )
    create_lifecycle_event(
        asset=doc.asset, event_type="transferred",
        actor=frappe.session.user,
        root_doctype=_DT_TRANSFER, root_record=name,
        notes=f"Tiếp nhận hoàn tất bởi {frappe.session.user}",
    )
    frappe.db.commit()
    return {"name": name, "status": _TRANSFER_STATUS_RECEIVED, "received_by": frappe.session.user}


def cancel_transfer_request(name: str) -> dict:
    """Hủy phiếu luân chuyển (chỉ khi đang Pending Approval)."""
    if not frappe.db.exists(_DT_TRANSFER, name):
        frappe.throw(_(_ERR_TRANSFER_NOT_FOUND).format(name))

    current_status = frappe.db.get_value(_DT_TRANSFER, name, "status")
    if current_status not in (_TRANSFER_STATUS_PENDING, _TRANSFER_STATUS_REJECTED):
        frappe.throw(_("Chỉ có thể hủy phiếu đang Pending Approval hoặc Rejected"))

    frappe.db.set_value(_DT_TRANSFER, name, "status", _TRANSFER_STATUS_CANCELLED)
    frappe.db.commit()
    return {"name": name, "status": _TRANSFER_STATUS_CANCELLED}


def _notify_transfer_approvers(doc: "frappe.model.document.Document") -> None:
    """Email các approver (Department Head / Ops Manager / System Admin) khi có yêu cầu luân chuyển mới."""
    recipients = get_role_emails(["Commissioning Manager"])
    if not recipients:
        return
    asset_name = frappe.db.get_value(_DOCTYPE_ASSET, doc.asset, "asset_name") or doc.asset
    safe_sendmail(
        recipients=recipients,
        subject=f"[Yêu cầu phê duyệt] Luân chuyển thiết bị: {asset_name}",
        message=(
            f"<p>Có yêu cầu luân chuyển thiết bị mới cần phê duyệt.</p>"
            f"<ul>"
            f"<li>Phiếu: <strong>{doc.name}</strong></li>"
            f"<li>Thiết bị: {asset_name} ({doc.asset})</li>"
            f"<li>Loại: {doc.transfer_type}</li>"
            f"<li>Từ: {doc.from_location or '—'} → Đến: {doc.to_location}</li>"
            f"<li>Lý do: {doc.reason}</li>"
            f"<li>Người yêu cầu: {frappe.session.user}</li>"
            f"</ul>"
            f"<p>Vui lòng vào hệ thống để phê duyệt hoặc từ chối.</p>"
        ),
    )


def _notify_transfer_requester(doc: "frappe.model.document.Document", approved: bool) -> None:
    """Email người tạo phiếu thông báo kết quả phê duyệt (approved=True) hoặc từ chối."""
    owner = frappe.db.get_value(_DT_TRANSFER, doc.name, "owner")
    if not owner:
        return
    asset_name = frappe.db.get_value(_DOCTYPE_ASSET, doc.asset, "asset_name") or doc.asset
    action = "được phê duyệt" if approved else "bị từ chối"
    body = (
        f"<p>Yêu cầu luân chuyển thiết bị <strong>{asset_name}</strong> đã {action}.</p>"
        f"<ul><li>Phiếu: {doc.name}</li>"
        f"<li>Người xử lý: {frappe.session.user}</li>"
    )
    if not approved and doc.rejection_reason:
        body += f"<li>Lý do từ chối: {doc.rejection_reason}</li>"
    body += "</ul>"
    safe_sendmail(
        recipients=[owner],
        subject=f"[Luân chuyển thiết bị] Phiếu {doc.name} {action}",
        message=body,
    )


def transfer_asset(
    asset_name: str,
    to_location: str,
    to_department: str | None = None,
    to_custodian: str | None = None,
    transfer_doc: str | None = None,
    actor: str | None = None,
) -> None:
    """Cập nhật vị trí / phòng ban / phụ trách AC Asset và ghi audit trail."""
    prev = frappe.db.get_value(
        _DOCTYPE_ASSET, asset_name,
        ["location", "department", "custodian"], as_dict=True,
    ) or {}
    frappe.db.set_value(_DOCTYPE_ASSET, asset_name, {
        "location": to_location,
        "department": to_department,
        "custodian": to_custodian,
    })
    summary = (
        f"Luân chuyển: vị trí {prev.get('location')} → {to_location}"
        + (f", phòng ban {prev.get('department')} → {to_department}" if to_department else "")
        + (f", phụ trách {prev.get('custodian')} → {to_custodian}" if to_custodian else "")
    )
    create_lifecycle_event(
        asset=asset_name,
        event_type="transferred",
        actor=actor or frappe.session.user,
        root_doctype=_DT_TRANSFER,
        root_record=transfer_doc,
        notes=summary,
    )
    log_audit_event(
        asset=asset_name,
        event_type="Transfer",
        actor=actor or frappe.session.user,
        ref_doctype=_DT_TRANSFER,
        ref_name=transfer_doc,
        change_summary=summary,
    )


def check_insurance_expiry() -> None:
    """Scheduler daily: cảnh báo bảo hiểm thiết bị sắp hết hạn (90/60/30/7 ngày)."""
    thresholds = [90, 60, 30, 7]
    recipients = get_role_emails([_ROLE_DEPT_HEAD, _ROLE_OPS_MANAGER])
    if not recipients:
        return
    for d in thresholds:
        target = add_days(nowdate(), d)
        rows = frappe.db.get_all(
            _DOCTYPE_ASSET,
            filters={
                "insurance_end_date": target,
                "lifecycle_status": ("!=", _STATUS_DECOMMISSIONED),
            },
            fields=["name", "asset_name", "insurance_policy_no", "insurer_name", "insurance_end_date"],
        )
        if rows:
            body = "\n".join(
                f"- {r.name} | {r.asset_name} | HĐ {r.insurance_policy_no or '?'} | {r.insurer_name or '?'} | {r.insurance_end_date}"
                for r in rows
            )
            safe_sendmail(
                recipients,
                f"[AssetCore] Bảo hiểm thiết bị còn {d} ngày",
                f"{len(rows)} thiết bị có bảo hiểm sắp hết hạn trong {d} ngày:\n\n{body}",
            )


def check_service_contract_expiry() -> None:
    """Scheduler daily: cảnh báo hợp đồng dịch vụ sắp hết hạn (90/60/30 ngày)."""
    thresholds = [90, 60, 30]
    recipients = get_role_emails([_ROLE_DEPT_HEAD, _ROLE_OPS_MANAGER])
    if not recipients:
        return
    for d in thresholds:
        target = add_days(nowdate(), d)
        rows = frappe.db.get_all(
            "Service Contract",
            filters={"contract_end": target, "docstatus": 1},
            fields=["name", "contract_title", "supplier", "contract_end"],
        )
        if rows:
            body = "\n".join(
                f"- {r.name} | {r.contract_title} | NCC {r.supplier} | {r.contract_end}"
                for r in rows
            )
            safe_sendmail(
                recipients,
                f"[AssetCore] Hợp đồng dịch vụ còn {d} ngày",
                f"{len(rows)} hợp đồng dịch vụ sắp hết hạn trong {d} ngày:\n\n{body}",
            )


# ─── KPI helpers — single source of truth (RC-09 NextRound) ────────────────
# Cả Dashboard widget (DashboardView/Launcher) VÀ /approvals/pending phải gọi
# cùng 1 function này để tránh KPI mismatch giữa 2 trang. Mỗi caller pick
# scope đúng theo ngữ cảnh: "mine" cho cá nhân, "all" cho admin overview.
_DT_COMMISSIONING = "Asset Commissioning"


def count_pending_approvals(user: str | None = None, scope: str = "mine") -> int:
    """Đếm số Asset Commissioning đang chờ duyệt.

    Args:
        user: user để filter (default = ``frappe.session.user``).
        scope:
            ``"mine"`` (default) — chỉ phiếu mà ``pending_approver == user``
            (khớp với danh sách /approvals/pending — list_my_pending_approvals).
            ``"all"`` — toàn hệ thống (admin overview); yêu cầu role
            ``System Manager`` / ``Commissioning Manager`` / ``AssetCore Auditor``.

    Returns:
        int — số phiếu chờ duyệt theo scope đã chọn.
    """
    if scope == "all":
        # Admin/auditor mới được dùng scope all
        # R21: "IMM Auditor" KHÔNG tồn tại -> auditor bị loại sai khỏi scope=all.
        # Dùng role THẬT "AssetCore Auditor".
        allowed = {"System Manager", "Administrator", "Commissioning Manager", "AssetCore Auditor"}
        roles = set(frappe.get_roles(user or frappe.session.user))
        if not (allowed & roles):
            # Fallback an toàn: nếu thiếu quyền vẫn trả "mine" — UI không vỡ.
            scope = "mine"

    if scope == "all":
        # Cùng định nghĩa "đang chờ" như list_my_pending_approvals: docstatus != 2
        # và pending_approver != NULL (đã ở vòng duyệt nào đó).
        return frappe.db.count(
            _DT_COMMISSIONING,
            filters={
                "pending_approver": ["is", "set"],
                "docstatus": ["!=", 2],
            },
        )

    # scope == "mine"
    target_user = user or frappe.session.user
    return frappe.db.count(
        _DT_COMMISSIONING,
        filters={
            "pending_approver": target_user,
            "docstatus": ["!=", 2],
        },
    )


def rollup_asset_kpi() -> None:
    """Monthly 1st 06:00: rollup KPI (MTTR avg, uptime_pct) cho tung thiet bi."""
    # MTTR: avg of last 12 completed repairs per asset
    repair_rows = frappe.db.sql(
        """
        SELECT asset_ref, AVG(mttr_hours) AS avg_mttr, COUNT(*) AS repair_count
        FROM (
            SELECT asset_ref, mttr_hours,
                   ROW_NUMBER() OVER (PARTITION BY asset_ref ORDER BY completion_datetime DESC) AS rn
            FROM `tabAsset Repair`
            WHERE docstatus = 1 AND status = 'Completed' AND mttr_hours IS NOT NULL
        ) ranked
        WHERE rn <= 12
        GROUP BY asset_ref
        """,
        as_dict=True,
    )
    for r in repair_rows:
        if frappe.db.exists(_DOCTYPE_ASSET, r.asset_ref):
            frappe.db.set_value(_DOCTYPE_ASSET, r.asset_ref, "mttr_hours", round(r.avg_mttr, 2))

    # Uptime: (days_in_month - days_in_repair) / days_in_month * 100
    from frappe.utils import get_first_day, get_last_day, date_diff
    month_start = get_first_day(nowdate())
    month_end = get_last_day(nowdate())
    days_in_month = date_diff(month_end, month_start) + 1

    downtime_rows = frappe.db.sql(
        """
        SELECT asset_ref, SUM(mttr_hours) AS total_downtime_h
        FROM `tabAsset Repair`
        WHERE docstatus = 1 AND status = 'Completed'
          AND completion_datetime >= %s AND completion_datetime <= %s
        GROUP BY asset_ref
        """,
        (str(month_start), str(month_end)),
        as_dict=True,
    )
    for r in downtime_rows:
        if not frappe.db.exists(_DOCTYPE_ASSET, r.asset_ref):
            continue
        downtime_days = (r.total_downtime_h or 0) / 24.0
        uptime_pct = round(max(0, (days_in_month - downtime_days) / days_in_month * 100), 2)
        frappe.db.set_value(_DOCTYPE_ASSET, r.asset_ref, "uptime_pct", uptime_pct)


# ──────────────────────────────────────────────
# GMDN P3 Hybrid — Category → Model → Asset cascade
# Ref: docs/res/plans/2026-05-19-gmdn-code-sync-strategy.md §5/§6 (C4/C5)
# ──────────────────────────────────────────────
_DOCTYPE_DEVICE_MODEL = "IMM Device Model"


def resync_assets_gmdn_from_model(model_name: str, new_code: str) -> int:
    """C5 — Re-sync gmdn_code của mọi AC Asset thuộc `model_name` về `new_code`.

    Tái dùng cho cả manual realign lẫn cascade. Mỗi Asset thực sự đổi giá trị
    được ghi 1 dòng IMM Audit Trail (asset = chính nó), KHÔNG đổi
    lifecycle_status (gmdn_code là data field thường — KHÔNG dùng
    transition_asset_status). Idempotent: Asset đã đúng giá trị → bỏ qua.

    Returns: số Asset thực sự được cập nhật.
    """
    assets = frappe.get_all(
        _DOCTYPE_ASSET,
        filters={"device_model": model_name},
        fields=["name", "gmdn_code"],
    )
    changed = 0
    for a in assets:
        old = a.get("gmdn_code") or ""
        if old == (new_code or ""):
            continue
        frappe.db.set_value(_DOCTYPE_ASSET, a["name"], "gmdn_code", new_code)
        _log_audit_event(
            asset=a["name"],
            event_type="System",
            ref_doctype=_DOCTYPE_DEVICE_MODEL,
            ref_name=model_name,
            change_summary=f"GMDN cascade: gmdn_code {old or '(rỗng)'} → {new_code or '(rỗng)'} (đồng bộ từ Danh mục qua Model)",
        )
        changed += 1
    return changed


def cascade_category_gmdn(category_name: str, old_code: str, new_code: str) -> dict:
    """C4 — Lan truyền gmdn_code của AC Asset Category xuống Model + Asset.

    Chính sách P3 Hybrid:
      - CHỈ cascade tới Model có gmdn_inherited = 1 (kế thừa).
      - Model gmdn_inherited = 0 (override cố ý) → BỎ QUA (giữ nguyên).
      - Mỗi Model được cascade → re-sync Asset của Model đó + audit.

    Idempotent: chỉ ghi audit khi giá trị thực sự đổi. Listener gọi hàm này
    KHÔNG save lại Category (tránh đệ quy vô hạn).

    Returns: {"models": [...], "assets_changed": int, "skipped_overrides": [...]}
    """
    inherited = frappe.get_all(
        _DOCTYPE_DEVICE_MODEL,
        filters={"asset_category": category_name, "gmdn_inherited": 1},
        fields=["name", "gmdn_code"],
    )
    skipped = frappe.get_all(
        _DOCTYPE_DEVICE_MODEL,
        filters={"asset_category": category_name, "gmdn_inherited": 0},
        pluck="name",
    )
    cascaded_models: list[str] = []
    assets_changed = 0
    for m in inherited:
        m_old = m.get("gmdn_code") or ""
        if m_old != (new_code or ""):
            frappe.db.set_value(_DOCTYPE_DEVICE_MODEL, m["name"], "gmdn_code", new_code)
            cascaded_models.append(m["name"])
        assets_changed += resync_assets_gmdn_from_model(m["name"], new_code)

    if skipped:
        frappe.logger("assetcore").info(
            "GMDN cascade %s (%s→%s): bỏ qua %d Model override: %s",
            category_name, old_code or "(rỗng)", new_code or "(rỗng)",
            len(skipped), ", ".join(skipped),
        )
    return {
        "models": cascaded_models,
        "assets_changed": assets_changed,
        "skipped_overrides": skipped,
    }
