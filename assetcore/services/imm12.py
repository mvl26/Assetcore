# Copyright (c) 2026, AssetCore Team
"""IMM-12 — Incident & CAPA orchestration service.

State machine Incident (khớp imm_12_incident_workflow.json + _VALID_TRANSITIONS):
  Open → Acknowledged → In Progress → Resolved → Closed
                                     ↘ (auto when High/Critical)
                                      RCA Required → [RCA flow] → Closed
  Open / Acknowledged / In Progress → Cancelled (false alarm)

  D3: "Tiếp nhận" (acknowledge: Open→Acknowledged) tách khỏi "Bắt đầu xử lý"
  (start_work: Acknowledged→In Progress). Triage/phân công ≠ bắt đầu xử lý.

State machine RCA:
  RCA Required → RCA In Progress → Completed (→ auto CAPA)
               ↘ Cancelled

Business Rules:
  BR-12-01  Critical → clinical_impact bắt buộc
  BR-12-02  Major/Critical Closed → rca phải Completed
  BR-12-03  ≥3 incidents/fault_code/90 ngày → auto tạo RCA Chronic
  BR-12-04  Critical → auto asset Out of Service
  BR-12-05  Mọi transition → IMM Audit Trail
  BR-12-06  RCA Submit → auto imm00.create_capa()
  BR-12-07  RCA root_cause + corrective_action bắt buộc trước Submit
"""
from __future__ import annotations

import frappe
from frappe.utils import add_days, get_datetime, now_datetime, nowdate, today
from PIL import UnidentifiedImageError

from assetcore.repositories.repair_repo import IncidentRepo, RCARepo
from assetcore.services import imm00 as svc00
from assetcore.services.shared import ServiceError, ErrorCode, rbac
from assetcore.utils.idempotency import resolve_idempotency_key
from assetcore.utils.notify import nthrow, nthrow_in_hook
from assetcore.utils.messages import MSG

_DT_INCIDENT = "Incident Report"
_DT_RCA = "IMM RCA Record"
_DT_CAPA = "IMM CAPA Record"
_DT_ASSET = "AC Asset"
_DT_FILE = "File"

# BR-12-17 (mobile CR-17/G6): đính ảnh bằng chứng hiện trường (NĐ98) vào Incident
# Report. MAX_INCIDENT_PHOTOS khớp mobile (contract parity). Content-type allowlist
# = JPG/PNG (ảnh hiện trường). Size cap 10 MB (chốt parity mobile — 05 §2 #15).
MAX_INCIDENT_PHOTOS = 5
MAX_INCIDENT_PHOTO_BYTES = 10 * 1024 * 1024
_INCIDENT_PHOTO_CONTENT_TYPES = ("image/jpeg", "image/jpg", "image/png")
_INCIDENT_PHOTO_EXTENSIONS = (".jpg", ".jpeg", ".png")
_EVENT_INCIDENT_PHOTO_ATTACHED = "incident_photo_attached"

# Field-level validation messages (VN) — nhánh reject Decision-B (fields.file). Hằng
# số hiển thị (đối xứng _MSG_* trong api/imm12.py); KHÔNG leak raw cap/stack.
_MSG_PHOTO_MISSING = "Thiếu tệp ảnh"
_MSG_PHOTO_NOT_IMAGE = "Tệp phải là ảnh JPG hoặc PNG"
_MSG_PHOTO_TOO_LARGE = "Ảnh vượt quá dung lượng cho phép (tối đa 10 MB)"
_MSG_PHOTO_MAX = "Tối đa 5 ảnh"
_MSG_PHOTO_FORBIDDEN = "Không có quyền đính ảnh cho phiếu sự cố này"
# Ảnh HỎNG/ĐỨT TRUYỀN: content-type hợp lệ nhưng bytes không giải mã được (KTV chụp
# hiện trường wifi/4G chập chờn) → PIL ném UnidentifiedImageError/OSError khi strip EXIF.
_MSG_PHOTO_CORRUPT = "Tệp ảnh bị lỗi hoặc không đọc được, vui lòng chụp/chọn lại."

_STATUS_OPEN = "Open"
_STATUS_ACKNOWLEDGED = "Acknowledged"
_STATUS_INVESTIGATING = "In Progress"
_STATUS_RESOLVED = "Resolved"
_STATUS_CLOSED = "Closed"
_STATUS_CANCELLED = "Cancelled"

_RCA_REQUIRED = "RCA Required"
_RCA_IN_PROGRESS = "RCA In Progress"
_RCA_COMPLETED = "Completed"
_RCA_CANCELLED = "Cancelled"

# ─── SSoT: RCA state machine (GATE-8 / LL-FE-51) ────────────────────────────────
# Mirror imm_12_rca_workflow.json (next_state khớp verbatim) và đối xứng
# _PM_VALID_TRANSITIONS/_REPAIR_VALID_TRANSITIONS. get_rca emit
# allowed_transitions = _RCA_VALID_TRANSITIONS[status] → FE render CTA theo
# (can_manage_rca && đích ∈ allowed), KHÔNG hardcode `rca.status === 'X'`. Terminal
# (Completed/Cancelled) → [] → 0 CTA.
_RCA_VALID_TRANSITIONS: dict[str, list[str]] = {
    _RCA_REQUIRED: [_RCA_IN_PROGRESS, _RCA_CANCELLED],
    _RCA_IN_PROGRESS: [_RCA_COMPLETED, _RCA_CANCELLED],
    _RCA_COMPLETED: [],
    _RCA_CANCELLED: [],
}

# Capability gate transition RCA (cap-SSoT rbac.py — KHÔNG hardcode role-name, chống
# RBAC dead-gate). ADR-IMM12-RCA-CTA D2: gate CẢ 3 (start/submit/cancel) bằng 1 cap
# corrective.write = (Incident Report,"write") → roles có write (Corrective User/
# Manager, Super Admin) quản được RCA; base AssetCore System User KHÔNG. 1 cap = FE
# can_manage_rca (cùng corrective.write) ⟺ nút hiện == nút bấm-được (không dead-gate).
# Đồng bộ: fixtures/workflow.json "Hủy RCA" += Corrective User/Manager (desk-allowed
# == endpoint-allowed).
_CAP_RCA_MANAGE = "corrective.write"

# Inline VN (Decision-B) — guard trạng thái/quyền RCA. Đối xứng _MSG_PHOTO_*
# (module-constant, KHÔNG leak raw state/cap). BAD_STATE → 409; FORBIDDEN → 403.
_MSG_RCA_START_BAD_STATE = (
    "Chỉ có thể bắt đầu phân tích khi phiếu ở trạng thái Cần phân tích")
_MSG_RCA_SUBMIT_BAD_STATE = (
    "Chỉ có thể hoàn thành khi phiếu đang ở trạng thái Đang phân tích "
    "(cần bắt đầu phân tích trước, không thể bỏ qua bước này)")
_MSG_RCA_CANCEL_BAD_STATE = (
    "Chỉ có thể hủy khi phiếu đang hoạt động (Cần phân tích hoặc Đang phân tích)")
_MSG_RCA_FORBIDDEN = (
    "Không có quyền thực hiện thao tác này trên phân tích nguyên nhân gốc")

# ─── SoT: "incident đang mở" (Single Source of Truth) ───────────────────────────
# Positive-state predicate DUY NHẤT cho mọi consumer (dashboard KPI/donut/persona,
# SLA engine, drill-down list). Cancelled là terminal state (transition map :63-66
# KHÔNG có outgoing) → KHÔNG được tính là mở; Resolved/Closed cũng terminal-ish
# (đã rời open-set). Dùng POSITIVE list thay negative-list 'NOT IN [Closed, Resolved]'
# để khỏi vô tình đếm Cancelled là mở (drift đã gặp ở api/dashboard.py).
INCIDENT_OPEN_STATES = (
    _STATUS_OPEN, _STATUS_ACKNOWLEDGED, _STATUS_INVESTIGATING, _RCA_REQUIRED,
)


def open_incident_filter(extra: dict | None = None) -> dict:
    """Filter dict SoT cho "incident đang mở".

    Trả `{"status": ["in", INCIDENT_OPEN_STATES], **extra}`. Mọi consumer (dashboard
    KPI/donut/persona, SLA engine, list drill-down) dùng CHUNG helper này → count
    card/donut == số dòng list sau drill (invariant count==drill), không drift.
    """
    f: dict = {"status": ["in", list(INCIDENT_OPEN_STATES)]}
    if extra:
        f.update(extra)
    return f


# ─── SoT: SLA-breach LIVE predicate (BR-12-09 / BR-12-13) ───────────────────────
# "Đang vi phạm SLA" = state user/QA hành động NGAY (NĐ98 Điều 67 cửa-sổ luật-định),
# KHÔNG đợi scheduler hourly stamp cờ. Predicate SoT = (cờ-lịch-sử=1) OR (đang-mở ∧
# quá-hạn-live). 2 cờ response_breached/resolution_breached chỉ do scheduler
# check_incident_sla_breach() hoặc write-path acknowledge/resolve stamp → đếm cờ
# thuần undercount cửa-sổ-trễ-scheduler (incident vừa quá hạn 1-59' chưa kịp quét).
#
# sla_breach_filter() định nghĩa DUY NHẤT nhánh LIVE-OVERDUE (tái dùng
# open_incident_filter() → terminal Cancelled/Closed/Resolved loại tự nhiên,
# INV-SLA-6). KHÔNG nhúng nhánh cờ=1 vào filter — sla_breach_count() ghép 2 nhánh
# mutually-exclusive (cờ=1 vs cờ=0∧live) để né OR trong frappe.db.count + chống
# double-count. Đây là điểm SoT duy nhất; KHÔNG re-implement predicate ở 2 chỗ.


def sla_breach_filter(kind: str) -> dict:
    """SoT predicate cho nhánh LIVE-OVERDUE của SLA breach (BR-12-09).

    Trả filter dict: `open_incident_filter()` ∧ `<kind>_due_at < now()`
    (+ kind=='response': `acknowledged_at` unset — chưa tiếp nhận). KHÔNG gồm nhánh
    cờ=1 (đếm tách trong `sla_breach_count` để né OR trong frappe.db.count).
    Terminal Cancelled/Closed/Resolved bị loại tự nhiên (không thuộc
    INCIDENT_OPEN_STATES) → INV-SLA-6 (no phantom-count thiết bị đã đóng đúng hạn).
    """
    now = now_datetime()
    if kind == "response":
        return open_incident_filter({
            "acknowledged_at": ("is", "not set"),
            "response_due_at": ("<", now),
        })
    return open_incident_filter({
        "resolution_due_at": ("<", now),
    })


def sla_breach_count(kind: str) -> int:
    """SoT count cho KPI SLA-breach (BR-12-09) = (cờ=1) OR (đang-mở ∧ quá-hạn-live).

    Cộng 2 nhánh mutually-exclusive → KHÔNG double-count:
      A. cờ lịch sử `<kind>_breached == 1` (gồm cả terminal Closed/Resolved đã breach).
      B. live-overdue ∧ cờ == 0 (`sla_breach_filter(kind)` ∧ `<flag> == 0`).
    Idempotent vs scheduler (INV-SLA-4): trước stamp incident vào nhánh B (live, cờ=0);
    sau stamp rơi vào nhánh A (cờ=1) → tổng KHÔNG đổi. `frappe.db.count` không hỗ trợ
    OR top-level nên tách 2 count; 2 nhánh phân biệt theo giá trị cờ ⇒ không giao nhau.
    """
    flag = "response_breached" if kind == "response" else "resolution_breached"
    flagged = frappe.db.count(_DT_INCIDENT, filters={flag: 1})
    live_filter = dict(sla_breach_filter(kind))
    live_filter[flag] = 0
    live_unflagged = frappe.db.count(_DT_INCIDENT, filters=live_filter)
    return flagged + live_unflagged


def _row_is_breached(row: dict, kind: str, now=None) -> int:
    """Derive live SLA-breach cho 1 row đã fetch (CÙNG predicate sla_breach_filter,
    in-Python — KHÔNG query thêm per-row). Trả 0|1 cho FE badge.

    = (cờ=1) OR (status ∈ open-set ∧ <kind>_due_at < now [∧ response: chưa ack]).
    Terminal status → chỉ qua nhánh cờ=1 (INV-SLA-6). Cùng SoT với tile count.
    """
    flag_field = "response_breached" if kind == "response" else "resolution_breached"
    if row.get(flag_field):
        return 1
    if row.get("status") not in INCIDENT_OPEN_STATES:
        return 0  # terminal → KHÔNG live-overdue
    if now is None:
        now = now_datetime()
    due_field = "response_due_at" if kind == "response" else "resolution_due_at"
    due = row.get(due_field)
    if not due or now <= frappe.utils.get_datetime(due):
        return 0
    if kind == "response" and row.get("acknowledged_at"):
        return 0  # đã tiếp nhận → response không còn live-overdue
    return 1


def _enrich_sla_breach(rows: list, now=None) -> None:
    """Gán `is_response_breached`/`is_resolution_breached` (0|1, derived LIVE) cho mỗi
    row — badge FE đọc field derived thay cờ thô (INV-SLA-5: badge live == tile)."""
    if now is None:
        now = now_datetime()
    for r in rows:
        r["is_response_breached"] = _row_is_breached(r, "response", now)
        r["is_resolution_breached"] = _row_is_breached(r, "resolution", now)


_SEV_HIGH = "High"
_SEV_CRITICAL = "Critical"
_HIGH_SEVERITY = (_SEV_HIGH, _SEV_CRITICAL)

_ASSET_OUT_OF_SERVICE = "Out of Service"
_ASSET_ACTIVE = "Active"

# ─── SSoT: Incident state machine (CR-WF-12 / INV-1+INV-2) ──────────────────────
# _VALID_TRANSITIONS là SSoT sinh `allowed_transitions` (get_incident_detail:1084) →
# điều khiển render CTA FE (IncidentDetailView gate status===X && allowed.includes(Y)).
# PHẢI đối soát edge-by-edge với imm_12_incident_workflow.json (guard
# TestIncidentAllowedTransitions):
#   INV-1 (SVC ⊆ WF): mọi cạnh ở đây PHẢI là cạnh THẬT của workflow (chặn nút
#     dead/bypass). Vì thế `In Progress` KHÔNG có `RCA Required` — workflow không có
#     cạnh này; Incident vào 'RCA Required' CHỈ qua desk action "Yêu cầu RCA"
#     (Resolved→RCA Required). resolve_incident() set status='Resolved' rồi auto-tạo
#     RCA Record (DocType khác), KHÔNG set Incident.status='RCA Required'.
#   INV-2 (WF ⊆ SVC ∪ EXCEPTION): mọi cạnh workflow HOẶC là CTA ở đây HOẶC là
#     EXCEPTION_EDGE có rationale. `Resolved → In Progress` ("Mở lại điều tra",
#     BR-12-23) surface thành CTA reopen_incident(). `RCA Required → Closed` là
#     EXCEPTION_EDGE (auto-advance _advance_incident_after_rca sau RCA — không CTA).
# D3: Open chỉ đi Acknowledged/Cancelled (KHÔNG nhảy thẳng In Progress).
_VALID_TRANSITIONS: dict[str, list[str]] = {
    _STATUS_OPEN: [_STATUS_ACKNOWLEDGED, _STATUS_CANCELLED],
    _STATUS_ACKNOWLEDGED: [_STATUS_INVESTIGATING, _STATUS_CANCELLED],
    _STATUS_INVESTIGATING: [_STATUS_RESOLVED, _STATUS_CANCELLED],
    # Round 12: THÊM 'In Progress' (Mở lại điều tra, BR-12-23) — surface cạnh workflow
    # 'Resolved→In Progress' thành CTA reopen_incident (drift a). 'RCA Required' GIỮ
    # (cạnh workflow THẬT 'Yêu cầu RCA'; FE hiện chưa render nút → không dead-button;
    # surface CTA request_rca là backlog).
    _STATUS_RESOLVED: [_STATUS_CLOSED, _RCA_REQUIRED, _STATUS_INVESTIGATING],
}

# ─── SSoT: Incident write-path capabilities (DÙNG CHUNG api ↔ service builder) ───
# 1 NGUỒN hằng số cho CẢ api/imm12.py (gate endpoint ghi _can_investigate/_can_close)
# LẪN _build_incident_available_actions (has_cap của 6 CTA). api/imm12.py IMPORT từ
# ĐÂY — KHÔNG copy literal cap thứ 2 (drift cap = "gate nói dối"). R16: cap THẬT
# (DocPerm Incident Report), KHÔNG role-name bịa:
#   incident.acknowledge → ("Incident Report","write")  = triage/work/resolve/cancel
#   incident.close       → ("Incident Report","submit") = close/reopen
_CAP_INVESTIGATE = "incident.acknowledge"
_CAP_CLOSE = "incident.close"

# ─── SSoT: 6 CTA vòng đời phiếu (available_actions server-driven — CR-39) ─────────
# Mirror imm00._build_available_actions(:762). Thứ tự CỐ ĐỊNH = thứ tự render FE
# (IncidentDetailView). Mỗi spec: {key, label(VI = nhãn nút FE), target(status đích),
# from(tuple status nguồn hợp lệ), cap}. `from` KHỬ VA CHẠM start_work↔reopen (cùng
# đích 'In Progress'): _VALID_TRANSITIONS[status] cho biết đích hợp lệ nhưng KHÔNG
# phân biệt CTA nào (Acknowledged→In Progress = start_work; Resolved→In Progress =
# reopen). Khớp disambiguation FE incidentDetailCtaGating.test.ts. cap ánh xạ ĐÚNG
# predicate endpoint ghi: 'investigate'=_CAP_INVESTIGATE (ack/start/resolve/cancel),
# 'close'=_CAP_CLOSE (close/reopen) — KHÔNG hardcode literal cap khác.
_CTA_INVESTIGATE = "investigate"
_CTA_CLOSE = "close"
_INCIDENT_ACTION_SPECS: tuple[dict, ...] = (
    {"key": "acknowledge", "label": "Tiếp nhận", "target": _STATUS_ACKNOWLEDGED,
     "from": (_STATUS_OPEN,), "cap": _CTA_INVESTIGATE},
    {"key": "start_work", "label": "Bắt đầu xử lý", "target": _STATUS_INVESTIGATING,
     "from": (_STATUS_ACKNOWLEDGED,), "cap": _CTA_INVESTIGATE},
    {"key": "resolve", "label": "Đánh dấu đã giải quyết", "target": _STATUS_RESOLVED,
     "from": (_STATUS_INVESTIGATING,), "cap": _CTA_INVESTIGATE},
    {"key": "close", "label": "Đóng sự cố", "target": _STATUS_CLOSED,
     "from": (_STATUS_RESOLVED,), "cap": _CTA_CLOSE},
    {"key": "reopen", "label": "Mở lại điều tra", "target": _STATUS_INVESTIGATING,
     "from": (_STATUS_RESOLVED,), "cap": _CTA_CLOSE},
    {"key": "cancel", "label": "Hủy (báo nhầm)", "target": _STATUS_CANCELLED,
     "from": (_STATUS_OPEN, _STATUS_ACKNOWLEDGED, _STATUS_INVESTIGATING),
     "cap": _CTA_INVESTIGATE},
)

# Reason VI (CHỈ khi enabled=False) — 3 bậc ưu tiên transition > capability >
# business-gate (D9, parity imm00 no-EN-leak). Bậc transition phủ luôn nhánh status
# rỗng/lạ (transition_allowed=False cho MỌI CTA vì target ∉ []) ⇒ enabled False LUÔN
# có reason (bất biến D9).
_ACTION_REASON_TRANSITION = (
    "Không thể thực hiện thao tác này ở trạng thái hiện tại của phiếu")
_ACTION_REASON_CAPABILITY = "Bạn không có quyền thực hiện thao tác này"
_ACTION_REASON_RCA_GATE = (
    "Cần hoàn thành phân tích nguyên nhân gốc (RCA) trước khi đóng phiếu sự cố")

_CHRONIC_WINDOW_DAYS = 90
_CHRONIC_MIN_COUNT = 3
_RCA_DUE_MAJOR = 7
_RCA_DUE_CHRONIC = 14

_ORDER_REPORTED_AT = "reported_at desc"

# V4-GATE BÁO-HỎNG (ADR-IMM12-REPORT-FAILURE D2): canonical lifecycle event +
# provenance source. `incident_reported` là option HỢP LỆ của Select
# Asset Lifecycle Event.event_type (verified) — KHÔNG dùng 'failure_reported'
# (KHÔNG có trong Select → throw schema). `source` enum {manual, qr-scan},
# default 'manual'; giá trị lạ → coerce 'manual' (provenance KHÔNG phải security gate).
_EVENT_INCIDENT_REPORTED = "incident_reported"
_SOURCE_QR_SCAN = "qr-scan"
_SOURCE_MANUAL = "manual"
_VALID_SOURCES = frozenset({_SOURCE_MANUAL, _SOURCE_QR_SCAN})


def _source_label(source: str) -> str:
    """SSoT provenance label — chỉ 'qr-scan' hợp lệ thì giữ, mọi giá trị khác → 'manual'."""
    return _SOURCE_QR_SCAN if source == _SOURCE_QR_SCAN else _SOURCE_MANUAL


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_incident(name: str) -> "frappe.Document":
    doc = IncidentRepo.get(name)
    if not doc:
        nthrow(MSG.IMM12_INCIDENT_NOT_FOUND, name=name)
    return doc


def _get_rca(name: str) -> "frappe.Document":
    doc = RCARepo.get(name)
    if not doc:
        nthrow(MSG.IMM12_RCA_NOT_FOUND, name=name)
    return doc


def _assert_transition(doc: "frappe.Document", to_status: str) -> None:
    allowed = _VALID_TRANSITIONS.get(doc.status, [])
    if to_status not in allowed:
        nthrow(MSG.IMM12_BAD_STATE, from_state=doc.status, to_state=to_status)


def _log(name: str, asset: str, summary: str, from_status: str, to_status: str) -> None:
    try:
        svc00.log_audit_event(
            asset=asset,
            event_type="Incident",
            actor=frappe.session.user,
            ref_doctype=_DT_INCIDENT,
            ref_name=name,
            change_summary=summary,
            from_status=from_status,
            to_status=to_status,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-12 _log audit")


def _require_rca_cap(cap: str) -> None:
    """Cap-gate transition RCA ở SERVICE (đường DUY NHẤT — API/curl/test đều qua).

    Trả ServiceError(FORBIDDEN) Decision-B (KHÔNG `rbac.require` — require raise
    PermissionError thô ngoài envelope + leak raw cap vào message). Base AssetCore
    System User (không cap corrective) → 403; Super Admin → pass (AC5 axis-A).
    """
    if not rbac.can(cap):
        raise ServiceError(ErrorCode.FORBIDDEN, _MSG_RCA_FORBIDDEN, http_status=403)


def _log_rca(rca, summary: str, from_status: str, to_status: str) -> None:
    """Audit trail cho transition RCA — IMM Audit Trail (cơ chế nghiệp vụ sẵn có,
    KHÔNG mở rộng enum Asset Lifecycle Event ngoài scope). ref = RCA record; đếm được
    theo (ref_doctype='IMM RCA Record', ref_name, to_status): rca_started→'RCA In
    Progress', rca_completed→'Completed', rca_cancelled→'Cancelled'."""
    try:
        svc00.log_audit_event(
            asset=rca.asset or "",
            event_type="Incident",
            actor=frappe.session.user,
            ref_doctype=_DT_RCA,
            ref_name=rca.name,
            change_summary=summary,
            from_status=from_status,
            to_status=to_status,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-12 _log_rca audit")


def _map_severity(severity: str) -> str:
    return {
        "Low": "Minor", "Medium": "Minor",
        "High": "Major", "Critical": "Critical",
    }.get(severity, "Minor")


# BR-12-08: IMM SLA Policy.priority dùng thang P1–P4; Incident dùng severity.
_SEVERITY_TO_SLA_PRIORITY = {
    "Critical": "P1", "High": "P2", "Medium": "P3", "Low": "P4",
}


def _severity_to_sla_priority(severity: str) -> str:
    return _SEVERITY_TO_SLA_PRIORITY.get(severity, "P4")


def _apply_sla_policy(doc) -> None:
    """BR-12-08: resolve IMM SLA Policy theo severity và set due-time trên doc.

    Đọc response/resolution time TỪ policy (không hardcode). Không có policy khớp
    → bỏ qua (không chặn report). Gọi TRƯỚC insert/save để due-time được lưu.
    """
    from frappe.utils import add_to_date

    priority = _severity_to_sla_priority(doc.severity)
    policy = svc00.get_sla_policy(priority)
    if not policy:
        return
    base = doc.reported_at or now_datetime()
    doc.sla_policy = policy.get("name")
    resp_min = policy.get("response_time_minutes")
    res_hr = policy.get("resolution_time_hours")
    if resp_min:
        doc.response_due_at = add_to_date(base, minutes=int(resp_min))
    if res_hr:
        doc.resolution_due_at = add_to_date(base, hours=int(res_hr))


def _needs_rca(severity: str) -> bool:
    return severity in _HIGH_SEVERITY


def _enrich_asset_names(rows: list) -> None:
    asset_ids = {r["asset"] for r in rows if r.get("asset")}
    if asset_ids:
        asset_map = {a.name: a.asset_name for a in frappe.get_all(
            _DT_ASSET, filters={"name": ["in", list(asset_ids)]}, fields=["name", "asset_name"],
        )}
        for r in rows:
            r["asset_name"] = asset_map.get(r.get("asset"), r.get("asset") or "")

    # Enrich user fields (Data Contract Wave 1: reporter_name, assigned_to_name)
    user_ids: set = set()
    for r in rows:
        if r.get("reported_by"):
            user_ids.add(r["reported_by"])
        if r.get("assigned_to"):
            user_ids.add(r["assigned_to"])
    if user_ids:
        user_map = {u.name: u.full_name for u in frappe.get_all(
            "User", filters={"name": ["in", list(user_ids)]},
            fields=["name", "full_name"],
        )}
        for r in rows:
            if r.get("reported_by"):
                r["reporter_name"] = user_map.get(r["reported_by"], r["reported_by"])
            if r.get("assigned_to"):
                r["assigned_to_name"] = user_map.get(r["assigned_to"], r["assigned_to"])


def _build_incident_filters(
    status: str, severity: str, asset: str, open_only: bool = False,
    reported_by: str = "",
) -> dict:
    """Build filter dict cho list_incidents.

    `open_only` (param `open=1` từ FE drill) áp SoT open_incident_filter() để
    count card/donut == số dòng list. `status` đơn lẻ ƯU TIÊN hơn `open`
    (mutually-exclusive): nếu user chọn status cụ thể (vd Cancelled) thì bỏ qua
    open-set → status filter hoạt động độc lập.

    `reported_by` (BR-12-14 / ADR-IMM12-05 / ADR-MOBILE-015 — tab "Báo hỏng của
    tôi" MVP-5c): khi non-empty → seed extra["reported_by"] **TRƯỚC** khi rẽ nhánh
    ⇒ AND vào CẢ 3 nhánh (kể cả `status` return-sớm). mine=0/absent truyền
    reported_by="" ⇒ filters BYTE-IDENTICAL hành vi cũ (backward-compat web-FE).
    """
    extra: dict = {}
    if severity:
        extra["severity"] = severity
    if asset:
        extra["asset"] = asset
    # mine self-scope: seed TRƯỚC nhánh status return-sớm ⇒ phủ cả 3 nhánh.
    if reported_by:
        extra["reported_by"] = reported_by
    # status đơn lẻ ưu tiên hơn open (mutually-exclusive).
    if status:
        extra["status"] = status
        return extra
    if open_only:
        return open_incident_filter(extra)
    return extra


# ─── Incident lifecycle ────────────────────────────────────────────────────────

def _dedupe_lookup(client_request_id: str) -> dict | None:
    """CR-24: tra phiếu sự cố đã tạo theo idempotency key `client_request_id`.

    Index-seek O(1) (cột unique @incident_report.json — KHÔNG full-table scan).
    Trả về shape ĐỒNG NHẤT create-response {name, status, severity} khi tồn tại,
    None khi chưa có. GLOBAL theo key (client sinh UUID collision-free — ADR D-c/d).
    """
    if not client_request_id:
        return None
    row = frappe.db.get_value(
        _DT_INCIDENT, {"client_request_id": client_request_id},
        ["name", "status", "severity"], as_dict=True,
    )
    if not row:
        return None
    return {"name": row.name, "status": row.status, "severity": row.severity}


def report_incident(
    asset: str,
    incident_type: str,
    severity: str,
    description: str,
    *,
    fault_code: str = "",
    workaround_applied: int = 0,
    clinical_impact: str = "",
    patient_affected: int = 0,
    patient_impact_description: str = "",
    immediate_action: str = "",
    linked_repair_wo: str = "",
    reported_by: str = "",
    occurred_datetime: str = "",
    source: str = _SOURCE_MANUAL,
    client_request_id: str = "",
) -> dict:
    """Tạo Incident Report. BR-12-01: Critical → clinical_impact bắt buộc.

    D2 (ADR-IMM12-REPORT-FAILURE): sau insert emit canonical lifecycle event
    `incident_reported` (trục §10) + provenance `source` (qr-scan|manual) trong
    notes(lifecycle)/change_summary(audit). source lạ → coerce 'manual'.

    CR-24 (ADR-MOBILE idempotency): khoá idempotency đóng cửa sổ re-drain tạo phiếu TRÙNG
    (NĐ98 audit-integrity). Nguồn khoá resolve qua shared `resolve_idempotency_key`
    (HANDOFF §2.1 header-parity): body param `client_request_id` non-empty THẮNG header
    `X-Idempotency-Key` / alias `Idempotency-Key` (parity imm09/imm00/imm11); cả hai vắng
    ⇒ "" ⇒ NO-OP dedup (mỗi call = 1 phiếu, legacy web-desk/client-cũ 100% backward-compat).
    Khoá ĐÃ RESOLVE (không phải raw body) là cái dùng để lookup + PERSIST vào
    Incident.client_request_id ⇒ header-only re-drain khớp đúng row cũ. Truthy → dedupe
    TRƯỚC khối tạo: tồn tại thì return phiếu cũ (shape create-response) KHÔNG
    insert/lifecycle/audit lần 2. Insert bọc try/except UniqueValidationError (race
    concurrent re-drain) → re-read theo khoá resolve → return existing.
    """
    # CR-24 (HANDOFF §2.1): resolve khoá — body param THẮNG header X-Idempotency-Key/
    # Idempotency-Key; cả hai vắng ⇒ "" ⇒ NO-OP dedup (legacy y nguyên).
    resolved_key = resolve_idempotency_key(client_request_id)
    # CR-24: dedupe idempotent — khoá đã tạo phiếu thì trả phiếu cũ, KHÔNG tạo mới.
    existing = _dedupe_lookup(resolved_key)
    if existing:
        return existing

    if severity == _SEV_CRITICAL and not clinical_impact.strip():
        nthrow(MSG.IMM12_CLINICAL_IMPACT_REQUIRED)
    if not frappe.db.exists(_DT_ASSET, asset):
        nthrow(MSG.IMM12_ASSET_NOT_FOUND, asset=asset)

    source_label = _source_label(source)
    asset_status_before = frappe.db.get_value(_DT_ASSET, asset, "lifecycle_status") or ""
    actor = reported_by or frappe.session.user
    doc = frappe.new_doc(_DT_INCIDENT)
    doc.asset = asset
    doc.incident_type = incident_type
    doc.severity = severity
    doc.description = description
    doc.reported_by = actor
    doc.reported_at = now_datetime()
    # G1 (BR-FIX-12 / DM-FIX-03): occurred_datetime = thời điểm sự cố THỰC SỰ xảy ra
    # (có thể TRƯỚC lúc báo). Bắt buộc không ở tương lai; rỗng → fallback reported_at.
    if occurred_datetime:
        occurred_dt = get_datetime(occurred_datetime)
        if occurred_dt and occurred_dt > now_datetime():
            nthrow(MSG.IMM12_OCCURRED_DATETIME_FUTURE)
        doc.occurred_datetime = occurred_dt
    else:
        doc.occurred_datetime = doc.reported_at
    doc.status = _STATUS_OPEN
    if fault_code:
        doc.fault_code = fault_code
    doc.workaround_applied = workaround_applied
    if clinical_impact:
        doc.clinical_impact = clinical_impact
    doc.patient_affected = patient_affected
    if patient_impact_description:
        doc.patient_impact_description = patient_impact_description
    if immediate_action:
        doc.immediate_action = immediate_action
    if linked_repair_wo:
        doc.linked_repair_wo = linked_repair_wo
    doc.rca_required = 1 if _needs_rca(severity) else 0
    # CR-24: persist khoá ĐÃ RESOLVE (không raw body — header-only re-drain phải khớp
    # đúng row cũ). Only khi truthy → NULL cho phiếu không khoá; MariaDB unique index cho
    # phép nhiều NULL → backward-compat nguyên vẹn.
    if resolved_key:
        doc.client_request_id = resolved_key
    # BR-12-08: SLA due-times từ IMM SLA Policy (sau khi reported_at đã set).
    _apply_sla_policy(doc)
    doc.flags.ignore_permissions = True
    try:
        doc.insert()
    except frappe.UniqueValidationError:
        # CR-24 race: một request re-drain concurrent đã insert CÙNG client_request_id
        # giữa dedupe pre-check và insert này (unique constraint DB chặn). Dọn msgprint
        # "must be unique" thừa, re-read winner rồi return idempotent — KHÔNG tạo phiếu
        # trùng, KHÔNG emit lifecycle/audit lần 2.
        frappe.clear_last_message()
        winner = _dedupe_lookup(resolved_key)
        if winner:
            return winner
        raise

    # BR-12-04: Critical → auto Out of Service
    if severity == _SEV_CRITICAL:
        _try_transition_asset(asset, _ASSET_OUT_OF_SERVICE, doc.name, actor)

    frappe.db.commit()
    # D2: provenance trong audit change_summary (hash-chain GIỮ — chỉ đổi text row mới).
    _log(doc.name, asset,
         f"Incident reported ({source_label}) — {severity} — {incident_type}",
         "", _STATUS_OPEN)
    # D2: canonical lifecycle event 'incident_reported' (trục §10) — root_doctype BẮT
    # BUỘC kèm root_record (Dynamic Link) nếu không event bị nuốt. Wrap try/except —
    # lifecycle là side-effect audit, KHÔNG fail report. from→to status = trạng thái
    # asset trước/sau report (Critical → Out of Service do BR-12-04).
    _emit_incident_reported_event(
        asset=asset, incident_name=doc.name, actor=actor,
        from_status=asset_status_before, severity=severity,
        incident_type=incident_type, source_label=source_label,
    )
    return {"name": doc.name, "status": doc.status, "severity": severity}


def _emit_incident_reported_event(
    *, asset: str, incident_name: str, actor: str, from_status: str,
    severity: str, incident_type: str, source_label: str,
) -> None:
    """D2: ghi Asset Lifecycle Event canonical `incident_reported` + provenance source.

    root_doctype=_DT_INCIDENT BẮT BUỘC cùng root_record (Dynamic Link) — pattern
    IMM-09 _log_lifecycle_event (F10). to_status = trạng thái asset SAU report (đọc
    lại live: Critical → Out of Service do BR-12-04). Side-effect — KHÔNG fail report.
    """
    try:
        to_status = frappe.db.get_value(_DT_ASSET, asset, "lifecycle_status") or from_status
        svc00.create_lifecycle_event(
            asset=asset,
            event_type=_EVENT_INCIDENT_REPORTED,
            actor=actor,
            from_status=from_status,
            to_status=to_status,
            root_doctype=_DT_INCIDENT,
            root_record=incident_name,
            notes=f"Báo hỏng ({source_label}) — {severity} — {incident_type}",
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-12 incident_reported lifecycle event")


def acknowledge_incident(name: str, notes: str = "", assigned_to: str = "") -> dict:
    """"Tiếp nhận": Open → Acknowledged. Triage + phân công.

    D3 fix: KHÔNG nhảy thẳng In Progress (đó là start_work()). BR-12-04 extended:
    High/Critical → auto Out of Service ngay khi tiếp nhận (thiết bị nguy hiểm
    không tiếp tục vận hành trong lúc chờ xử lý).
    """
    doc = _get_incident(name)
    _assert_transition(doc, _STATUS_ACKNOWLEDGED)

    actor = frappe.session.user
    prev = doc.status
    doc.status = _STATUS_ACKNOWLEDGED
    doc.acknowledged_by = actor
    doc.acknowledged_at = now_datetime()
    # BR-12-08: response SLA breach nếu tiếp nhận sau response_due_at.
    if doc.response_due_at and doc.acknowledged_at > frappe.utils.get_datetime(doc.response_due_at):
        doc.response_breached = 1
    if assigned_to:
        doc.assigned_to = assigned_to
    if notes:
        doc.immediate_action = ((doc.immediate_action or "") + f"\n[Ack] {notes}").strip()
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()
    _log(name, doc.asset, f"Tiếp nhận — {notes or 'đã phân công'}", prev, _STATUS_ACKNOWLEDGED)

    if doc.severity in _HIGH_SEVERITY:
        _try_transition_asset(doc.asset, _ASSET_OUT_OF_SERVICE, name, actor)

    return {"name": name, "status": doc.status}


def start_work(name: str, notes: str = "") -> dict:
    """"Bắt đầu xử lý": Acknowledged → In Progress.

    D3: KTV bắt đầu thực sự can thiệp thiết bị (tách khỏi triage ở acknowledge).
    """
    doc = _get_incident(name)
    _assert_transition(doc, _STATUS_INVESTIGATING)

    actor = frappe.session.user
    prev = doc.status
    doc.status = _STATUS_INVESTIGATING
    if not doc.assigned_to:
        doc.assigned_to = actor
    if notes:
        doc.immediate_action = ((doc.immediate_action or "") + f"\n[Start] {notes}").strip()
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()
    _log(name, doc.asset, f"Bắt đầu xử lý — {notes or 'đang xử lý'}", prev, _STATUS_INVESTIGATING)
    return {"name": name, "status": doc.status}


def resolve_incident(name: str, resolution_notes: str, root_cause: str = "") -> dict:
    """In Progress → Resolved. Auto-tạo RCA nếu High/Critical (không block)."""
    doc = _get_incident(name)
    _assert_transition(doc, _STATUS_RESOLVED)

    if not resolution_notes.strip():
        nthrow(MSG.IMM12_RESOLUTION_NOTES_REQUIRED)

    actor = frappe.session.user
    prev = doc.status
    doc.status = _STATUS_RESOLVED
    doc.resolved_by = actor
    doc.resolved_at = now_datetime()
    # BR-12-08: resolution SLA breach nếu xử lý xong sau resolution_due_at.
    if doc.resolution_due_at and doc.resolved_at > frappe.utils.get_datetime(doc.resolution_due_at):
        doc.resolution_breached = 1
    doc.resolution_notes = resolution_notes
    if root_cause:
        doc.root_cause_summary = root_cause
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()
    _log(name, doc.asset, f"Resolved — {resolution_notes[:120]}", prev, _STATUS_RESOLVED)

    # Auto-create RCA cho High/Critical nếu chưa có
    rca_name: str | None = None
    if _needs_rca(doc.severity) and not doc.rca_record:
        try:
            rca_name = _auto_create_rca(doc)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "IMM-12 auto_rca on resolve")

    # Auto-CAPA cho High/Critical nếu không có RCA flow (fallback)
    if doc.severity in _HIGH_SEVERITY and not doc.linked_capa and not rca_name:
        _auto_create_capa(doc)

    return {"name": name, "status": doc.status, "rca_created": rca_name}


def close_incident(name: str, verification_notes: str = "") -> dict:
    """Resolved → Closed.

    BR-12-02 (non-waivable): High/Critical → phải có RCA Completed trước khi
    Close. Gate enforce theo LIVE `_needs_rca(doc.severity)` (SSoT = severity),
    KHÔNG phụ thuộc cờ STORED `rca_required` — cờ có thể stale sau escalation
    Medium→Critical. rca_required nay = derived(severity) re-sync mọi save (xem
    IncidentReport._resync_rca_required); gate đọc severity trực tiếp để bất biến
    kể cả trên hàng chưa re-save. Ref: memory server-flag-SSoT / derive-live.
    """
    doc = _get_incident(name)
    _assert_transition(doc, _STATUS_CLOSED)

    # BR-12-02: enforce theo LIVE severity (không AND cờ stored rca_required —
    # escalation Medium→Critical với cờ stale=0 sẽ lọt ⇒ đóng-giả).
    if _needs_rca(doc.severity):
        rca_name = frappe.db.get_value(_DT_INCIDENT, name, "rca_record")
        if rca_name:
            rca_status = frappe.db.get_value(_DT_RCA, rca_name, "status")
            if rca_status != _RCA_COMPLETED:
                nthrow(MSG.IMM12_CLOSE_RCA_INCOMPLETE,
                       severity=doc.severity, rca=rca_name)
        else:
            nthrow(MSG.IMM12_CLOSE_RCA_REQUIRED, severity=doc.severity)

    actor = frappe.session.user
    prev = doc.status
    doc.status = _STATUS_CLOSED
    doc.closed_by = actor
    doc.closed_date = today()
    if verification_notes:
        doc.resolution_notes = ((doc.resolution_notes or "") + f"\n[Closed] {verification_notes}").strip()
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()
    _log(name, doc.asset, f"Closed — {verification_notes or 'verified'}", prev, _STATUS_CLOSED)

    # Khôi phục asset về Active nếu đang Out of Service do incident này
    if doc.asset:
        cur = frappe.db.get_value(_DT_ASSET, doc.asset, "lifecycle_status") or ""
        if cur == _ASSET_OUT_OF_SERVICE:
            _try_transition_asset(doc.asset, _ASSET_ACTIVE, name, actor)

    return {"name": name, "status": doc.status, "closed_date": doc.closed_date}


def cancel_incident(name: str, reason: str) -> dict:
    """Open / Acknowledged / In Progress → Cancelled (false alarm)."""
    doc = _get_incident(name)
    _assert_transition(doc, _STATUS_CANCELLED)
    if not reason.strip():
        nthrow(MSG.IMM12_CANCEL_REASON_REQUIRED)

    prev = doc.status
    doc.status = _STATUS_CANCELLED
    doc.resolution_notes = ((doc.resolution_notes or "") + f"\n[Cancelled] {reason}").strip()
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()
    _log(name, doc.asset, f"Cancelled — {reason[:120]}", prev, _STATUS_CANCELLED)
    return {"name": name, "status": doc.status}


def reopen_incident(name: str, reason: str) -> dict:
    """"Mở lại điều tra": Resolved → In Progress (BR-12-23, CR-WF-12).

    Surface CTA cho cạnh workflow THẬT `Resolved → In Progress` (∈
    _VALID_TRANSITIONS[Resolved]). `reason` bắt buộc. Audit IMM Audit Trail
    (Resolved→In Progress, đối xứng 5 sibling — BR-12-05). KHÔNG đổi asset
    `lifecycle_status`: Resolved chưa restore asset (chỉ Close mới restore), nên nếu
    Critical/OOS thì asset vẫn Out of Service sau reopen — KHÔNG cần Asset Lifecycle
    Event mới (ADR-IMM12-INCIDENT-CTA).
    """
    doc = _get_incident(name)
    _assert_transition(doc, _STATUS_INVESTIGATING)
    if not reason.strip():
        nthrow(MSG.IMM12_REOPEN_REASON_REQUIRED)

    prev = doc.status
    doc.status = _STATUS_INVESTIGATING
    doc.resolution_notes = (
        (doc.resolution_notes or "") + f"\n[Reopen] {reason}").strip()
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()
    _log(name, doc.asset, f"Mở lại điều tra — {reason[:120]}", prev, _STATUS_INVESTIGATING)
    return {"name": name, "status": doc.status}


def _has_live_rca(doc: "frappe.Document") -> bool:
    """CR-55: True nếu Incident đang trỏ hồ sơ RCA CÒN SỐNG (tồn tại ∧ status != Cancelled).

    Vị từ DÙNG CHUNG cho create_rca (guard IMM12_RCA_ALREADY_EXISTS) và request_rca
    (idempotent reuse) — 2 call-site KHÔNG lệch vị từ (chống drift). Hồ sơ RCA đã
    Cancelled KHÔNG chặn tạo mới ⇒ gỡ deadlock phiếu High/Critical bị khoá vĩnh viễn
    khi hồ sơ RCA duy nhất bị huỷ. frappe.db.get_value trả None khi rca_record trỏ hồ
    sơ đã xoá (orphan FK) ⇒ coi như không có RCA sống (LL-BE-18 null-guard dangling FK).
    """
    if not doc.rca_record:
        return False
    status = frappe.db.get_value(_DT_RCA, doc.rca_record, "status")
    return status is not None and status != _RCA_CANCELLED


def request_rca(name: str, rca_reason: str) -> dict:
    """"Yêu cầu phân tích RCA": Resolved → RCA Required (BR-12-24, CR-WF-12-RCA-ENTRY).

    Surface cạnh workflow THẬT `Resolved → RCA Required` ("Yêu cầu RCA") thành CTA
    server-driven — cấp DRIVER cho `allowed_transitions['RCA Required']` (∈
    _VALID_TRANSITIONS[Resolved] từ Round 12) đang advertise-mà-câm. ENTRY của nhánh
    RCA Required; EXIT = `_advance_incident_after_rca` (auto-close sau RCA Completed).

    Precondition đọc `doc.status` (domain SSoT, KHÔNG `workflow_state` — sibling dùng
    `doc.save` ⇒ workflow_state có thể lệch): `status != Resolved` →
    IMM12_REQUEST_RCA_BAD_STATE (422 MỚI, KHÔNG `_assert_transition`/IMM12_BAD_STATE=409),
    KHÔNG đổi status. `rca_reason` blank → IMM12_RCA_REASON_REQUIRED (422).

    RCA idempotent reuse (CR-55): chỉ `create_rca` khi CHƯA có rca_record CÒN SỐNG
    (`_has_live_rca` — tồn tại ∧ status != Cancelled). rca_record trỏ hồ sơ đã Cancelled
    ⇒ tạo hồ sơ RCA MỚI (KHÔNG tái dùng hồ sơ huỷ); RCA còn sống ⇒ `create_rca` raise
    409 (KHÔNG tạo trùng). CÙNG vị từ `_has_live_rca` với create_rca (chống drift). Transition qua
    `apply_workflow("Yêu cầu RCA")` (giữ Frappe workflow consistency, mirror
    `_advance_incident_after_rca`, KHÔNG `db.set_value` cho state) + sync `status`
    Select. Fallback `db.set_value({workflow_state, status})` khi apply_workflow từ chối
    (điều kiện workflow `severity ∉ (High,Critical) ∧ requires_rca != 1`, hoặc thiếu
    write DocPerm) — CTA governance áp cho MỌI Resolved (allowed_transitions tĩnh),
    KHÔNG chỉ High/Critical. Audit IMM Audit Trail (Resolved→RCA Required, BR-12-05) —
    KHÔNG thêm option Select event_type (precedent reopen D4). Cap-gate compliance.submit
    ở API tier.
    """
    doc = _get_incident(name)
    if doc.status != _STATUS_RESOLVED:
        nthrow(MSG.IMM12_REQUEST_RCA_BAD_STATE)
    if not (rca_reason or "").strip():
        nthrow(MSG.IMM12_RCA_REASON_REQUIRED)

    # Idempotent (CR-55): chỉ tạo khi CHƯA có rca_record CÒN SỐNG. rca_record trỏ hồ sơ
    # đã Cancelled ⇒ _has_live_rca=False ⇒ create_rca tạo hồ sơ MỚI (KHÔNG tái dùng hồ
    # sơ huỷ); create_rca guard 409 CHỈ khi RCA còn sống (CÙNG vị từ _has_live_rca —
    # chống drift 2 call-site).
    if not _has_live_rca(doc):
        create_rca(name)
    rca_record = frappe.db.get_value(_DT_INCIDENT, name, "rca_record")

    from frappe.model.workflow import apply_workflow

    inc = frappe.get_doc(_DT_INCIDENT, name)
    try:
        apply_workflow(inc, _ACTION_REQUEST_RCA)
        # apply_workflow chỉ flip workflow_state → sync status (Select) để list filter
        # status='RCA Required' còn đúng (dual-track).
        frappe.db.set_value(_DT_INCIDENT, name, {"status": _RCA_REQUIRED},
                            update_modified=False)
    except Exception:
        # Fallback (KHÔNG error — path bình thường cho non-High/Critical): điều kiện
        # workflow chặn (severity ∉ High/Critical ∧ requires_rca != 1) hoặc user thiếu
        # write DocPerm. db.set_value CẢ workflow_state+status để downstream
        # apply_workflow('RCA hoàn tất - đóng sự cố') còn khớp state (auto-close).
        frappe.logger("imm12").info(
            f"request_rca fallback incident={name} severity={doc.severity} "
            f"(workflow condition/permission — db.set_value sync dual-track)"
        )
        frappe.db.set_value(
            _DT_INCIDENT, name,
            {"workflow_state": _RCA_REQUIRED, "status": _RCA_REQUIRED},
            update_modified=False)
    frappe.db.commit()
    _log(name, doc.asset, f"Yêu cầu RCA — {rca_reason[:120]}",
         _STATUS_RESOLVED, _RCA_REQUIRED)
    return {"name": name, "status": _RCA_REQUIRED, "rca_record": rca_record}


# ─── RCA orchestration ────────────────────────────────────────────────────────

def create_rca(incident_name: str, rca_method: str = "5-Why") -> dict:
    """Tạo RCA Record liên kết Incident. Idempotent — raise 409 nếu đã có RCA CÒN SỐNG.

    CR-55: nếu rca_record cũ = Cancelled (hoặc orphan) → BỎ QUA guard, tạo hồ sơ MỚI
    (gỡ deadlock phiếu High/Critical bị khoá vĩnh viễn). Hồ sơ cũ GIỮ NGUYÊN
    status=Cancelled làm vết audit NĐ98 (KHÔNG mutate/xoá). set_value(rca_record) cuối
    hàm tự cập nhật Incident sang tên mới. Vị từ _has_live_rca dùng chung với
    request_rca (chống drift).
    """
    doc = _get_incident(incident_name)
    if _has_live_rca(doc):
        nthrow(MSG.IMM12_RCA_ALREADY_EXISTS, rca=doc.rca_record)

    trigger = "Critical Incident" if doc.severity == _SEV_CRITICAL else "Major Incident"
    due_days = _RCA_DUE_MAJOR

    rca = frappe.new_doc(_DT_RCA)
    rca.incident_report = incident_name
    rca.asset = doc.asset
    rca.rca_method = rca_method or "5-Why"
    rca.trigger_type = trigger
    rca.status = _RCA_REQUIRED
    rca.assigned_to = frappe.session.user
    rca.due_date = add_days(nowdate(), due_days)
    for i in range(1, 6):
        rca.append("five_why_steps", {"why_number": i, "why_question": f"Why {i}?", "why_answer": ""})
    rca.flags.ignore_permissions = True
    rca.insert()

    frappe.db.set_value(_DT_INCIDENT, incident_name, {
        "rca_record": rca.name,
        "rca_required": 1,
    })
    frappe.db.commit()
    return {"name": rca.name, "status": rca.status, "due_date": str(rca.due_date)}


def get_rca(name: str) -> dict:
    doc = _get_rca(name)
    data = doc.as_dict()
    if doc.incident_report:
        data["incident_severity"] = frappe.db.get_value(
            _DT_INCIDENT, doc.incident_report, "severity")
    # AC1 (parity get_work_order imm09.py): server-driven CTA. FE render nút theo
    # (can_manage_rca && đích ∈ allowed_transitions), KHÔNG hardcode status===.
    data["allowed_transitions"] = _RCA_VALID_TRANSITIONS.get(doc.status, [])
    data["can_manage_rca"] = 1 if rbac.can(_CAP_RCA_MANAGE) else 0
    return data


def start_rca(name: str) -> dict:
    """AC2: 'RCA Required' → 'RCA In Progress'. Sinh audit 'rca_started'.

    frappe.db.set_value (KHÔNG doc.save()): save() re-run RCA validate()
    (_validate_five_why_when_method_5why yêu cầu 5 bước đầy đủ khi status='In
    Progress') → chặn NGAY lúc mới bắt đầu (whys chưa điền) = sai nghiệp vụ.
    workflow_state đồng bộ để tránh dual-track drift.
    """
    _require_rca_cap(_CAP_RCA_MANAGE)
    rca = _get_rca(name)
    if rca.status != _RCA_REQUIRED:
        raise ServiceError(
            ErrorCode.BAD_STATE, _MSG_RCA_START_BAD_STATE, http_status=409)
    frappe.db.set_value(
        _DT_RCA, name,
        {"status": _RCA_IN_PROGRESS, "workflow_state": _RCA_IN_PROGRESS},
        update_modified=False)
    frappe.db.commit()
    _log_rca(rca, "Bắt đầu phân tích nguyên nhân gốc", _RCA_REQUIRED, _RCA_IN_PROGRESS)
    return {"name": name, "status": _RCA_IN_PROGRESS}


def list_rcas(
    method: str = "",
    status: str = "",
    asset: str = "",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Danh sách RCA Record cho RCAListView (route /rca). Read-safe, enrich names."""
    f: dict = {}
    if method:
        f["rca_method"] = method
    if status:
        f["status"] = status
    if asset:
        f["asset"] = asset
    total = frappe.db.count(_DT_RCA, filters=f)
    offset = (page - 1) * page_size
    rows = frappe.get_all(
        _DT_RCA,
        filters=f,
        fields=["name", "incident_report", "asset", "rca_method", "trigger_type",
                "status", "assigned_to", "due_date", "linked_capa", "completed_date"],
        order_by="creation desc",
        limit_start=offset,
        limit_page_length=page_size,
    )
    _enrich_asset_names(rows)
    # Enrich owner (assigned_to) display name
    user_ids = {r["assigned_to"] for r in rows if r.get("assigned_to")}
    if user_ids:
        user_map = {u.name: u.full_name for u in frappe.get_all(
            "User", filters={"name": ["in", list(user_ids)]}, fields=["name", "full_name"],
        )}
        for r in rows:
            if r.get("assigned_to"):
                r["assigned_to_name"] = user_map.get(r["assigned_to"], r["assigned_to"])
    return {
        "pagination": {
            "total": total, "page": page, "page_size": page_size,
            "total_pages": max(1, -(-total // page_size)), "offset": offset,
        },
        "items": rows,
    }


def submit_rca(
    name: str,
    root_cause: str,
    corrective_action: str,
    preventive_action: str = "",
    five_why_steps: list | None = None,
    rca_notes: str = "",
) -> dict:
    """Hoàn thành RCA → auto tạo CAPA. BR-12-07.

    AC3: CHỈ hoàn thành từ 'RCA In Progress' — chặn nhảy-cóc từ 'RCA Required'
    (bỏ qua bước phân tích = bug). Đã Completed → giữ thông điệp already-completed.
    """
    _require_rca_cap(_CAP_RCA_MANAGE)
    rca = _get_rca(name)
    if rca.status != _RCA_IN_PROGRESS:
        if rca.status == _RCA_COMPLETED:
            nthrow(MSG.IMM12_RCA_ALREADY_COMPLETED)
        raise ServiceError(
            ErrorCode.BAD_STATE, _MSG_RCA_SUBMIT_BAD_STATE, http_status=409)
    if not root_cause.strip():
        nthrow(MSG.IMM12_RCA_ROOT_CAUSE_REQUIRED)
    if not corrective_action.strip():
        nthrow(MSG.IMM12_RCA_CORRECTIVE_REQUIRED)

    actor = frappe.session.user
    rca.status = _RCA_COMPLETED
    rca.root_cause = root_cause
    rca.corrective_action_summary = corrective_action
    rca.preventive_action_summary = preventive_action or rca.preventive_action_summary
    rca.rca_notes = rca_notes or rca.rca_notes
    rca.completed_by = actor
    rca.completed_date = today()
    if five_why_steps:
        rca.set("five_why_steps", [])
        for step in five_why_steps:
            rca.append("five_why_steps", step)
    rca.flags.ignore_permissions = True
    rca.save()

    # BR-12-06: auto CAPA via IMM-16 canonical helper (RC-03 fix)
    capa_name: str | None = None
    if rca.incident_report:
        try:
            from assetcore.services.imm16 import create_capa_from_incident
            result = create_capa_from_incident(
                incident_name=rca.incident_report,
                rca_name=rca.name,
                responsible=actor,
            )
            capa_name = result.get("capa_name")
            # Refresh in-memory rca.linked_capa nếu vừa set qua db
            if capa_name and not rca.linked_capa:
                rca.linked_capa = capa_name
        except Exception:
            frappe.log_error(frappe.get_traceback(), "IMM-12 submit_rca auto_capa")

    frappe.db.commit()
    _log_rca(rca, f"Hoàn thành phân tích nguyên nhân gốc — {root_cause[:80]}",
             _RCA_IN_PROGRESS, _RCA_COMPLETED)

    # RC-04: push incident workflow forward sau khi RCA hoàn tất
    if rca.incident_report:
        _advance_incident_after_rca(rca.incident_report)

    return {"name": rca.name, "status": rca.status, "linked_capa": capa_name}


def cancel_rca(name: str, reason: str = "") -> dict:
    """AC4: hủy RCA đang hoạt động ('RCA Required'|'RCA In Progress') → 'Cancelled'.

    Sinh audit 'rca_cancelled'. Gate corrective.write (ADR-IMM12-RCA-CTA D2).
    'Completed'/'Cancelled' → BAD_STATE inline VN. `reason` bắt buộc (BR-12-22) →
    append vào rca_notes (bất biến bằng chứng) + change_summary audit.
    """
    _require_rca_cap(_CAP_RCA_MANAGE)
    rca = _get_rca(name)
    if rca.status not in (_RCA_REQUIRED, _RCA_IN_PROGRESS):
        raise ServiceError(
            ErrorCode.BAD_STATE, _MSG_RCA_CANCEL_BAD_STATE, http_status=409)
    if not (reason or "").strip():
        nthrow(MSG.IMM12_CANCEL_REASON_REQUIRED)
    prev = rca.status
    reason = (reason or "").strip()
    updates = {"status": _RCA_CANCELLED, "workflow_state": _RCA_CANCELLED}
    if reason:
        updates["rca_notes"] = ((rca.rca_notes or "") + f"\n[Hủy RCA] {reason}").strip()
    frappe.db.set_value(_DT_RCA, name, updates, update_modified=False)
    frappe.db.commit()
    summary = (f"Hủy phân tích nguyên nhân gốc — {reason[:80]}"
               if reason else "Hủy phân tích nguyên nhân gốc")
    _log_rca(rca, summary, prev, _RCA_CANCELLED)
    return {"name": name, "status": _RCA_CANCELLED}


# ─── Queries ──────────────────────────────────────────────────────────────────

def list_incidents(
    status: str = "",
    severity: str = "",
    asset: str = "",
    open: int = 0,
    mine: int = 0,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    # mine=1 (tab "Báo hỏng của tôi" MVP-5c) → resolve session ở service-layer rồi
    # seed reported_by vào CÙNG filters dict (count==rows giữ). mine=0/absent → "".
    reported_by = frappe.session.user if int(mine or 0) else ""
    filters = _build_incident_filters(
        status, severity, asset, open_only=bool(int(open or 0)),
        reported_by=reported_by,
    )
    total = frappe.db.count(_DT_INCIDENT, filters=filters)
    offset = (page - 1) * page_size
    rows = frappe.get_all(
        _DT_INCIDENT,
        filters=filters,
        fields=["name", "asset", "incident_type", "severity", "status", "fault_code",
                "reported_by", "reported_at", "description", "linked_capa", "linked_repair_wo",
                "rca_required", "rca_record", "chronic_failure_flag", "patient_affected",
                "closed_date", "assigned_to", "acknowledged_at", "resolved_at",
                # BR-12-09: cờ thô (giữ backward-compat) + due_at để derive LIVE badge.
                "response_breached", "resolution_breached",
                "response_due_at", "resolution_due_at"],
        order_by=_ORDER_REPORTED_AT,
        limit_start=offset,
        limit_page_length=page_size,
    )
    _enrich_asset_names(rows)
    # BR-12-09 LIVE: badge đọc is_*_breached (derived) thay cờ thô → khớp tile (INV-SLA-5).
    _enrich_sla_breach(rows)
    return {
        "pagination": {
            "total": total, "page": page, "page_size": page_size,
            "total_pages": max(1, -(-total // page_size)), "offset": offset,
        },
        "items": rows,
    }


def _scene_photos(incident_name: str) -> list:
    """SoT DUY NHẤT cho ảnh hiện trường của 1 Incident (BR-12-18 / ADR-IMM12-06).

    Query `File` private đính vào phiếu, lọc đuôi ảnh (.jpg/.jpeg/.png), trả
    `[{file_url, file_name}]` theo `creation asc` (thứ tự ổn định). CHÍNH helper này
    vừa liệt kê `scene_photos` trong `get_incident_detail` VỪA đếm max-count trong
    `attach_incident_photo` ⇒ invariant **count==rows** (số chặn ảnh-thứ-6 == số
    hiển thị). 1 query duy nhất — KHÔNG N+1.
    """
    rows = frappe.get_all(
        _DT_FILE,
        filters={
            "attached_to_doctype": _DT_INCIDENT,
            "attached_to_name": incident_name,
            "is_private": 1,
        },
        fields=["file_url", "file_name"],
        order_by="creation asc",
    )
    return [
        {"file_url": r.get("file_url"), "file_name": r.get("file_name")}
        for r in rows
        if (r.get("file_name") or "").lower().endswith(_INCIDENT_PHOTO_EXTENSIONS)
    ]


def _assert_can_attach_photo(incident: "frappe.Document") -> None:
    """BR-12-17 permission: reporter HOẶC `incident.write` trên chính phiếu đó.

    `frappe.has_permission(doc=...)` áp CẢ role-DocPerm write LẪN row-level
    `has_permission` hook (vendor isolation) ⇒ tái dùng IDOR-guard AUTH-10. Reporter
    luôn được đính ảnh phiếu của mình (bằng chứng do KTV báo hỏng cung cấp).
    """
    user = frappe.session.user
    if incident.reported_by == user:
        return
    if frappe.has_permission(_DT_INCIDENT, ptype="write", doc=incident, user=user):
        return
    raise ServiceError(ErrorCode.FORBIDDEN, _MSG_PHOTO_FORBIDDEN, http_status=403)


def _photo_validation_error(msg: str) -> ServiceError:
    """VALIDATION Decision-B với fields.file (FE hiển thị lỗi dưới control upload)."""
    return ServiceError(ErrorCode.VALIDATION, msg, http_status=422, fields={"file": msg})


def attach_incident_photo(
    incident_name: str,
    filedata: bytes | None = None,
    filename: str = "",
    content_type: str = "",
    client_request_id: str = "",
) -> dict:
    """BR-12-17/18 (mobile CR-17/G6): đính ảnh bằng chứng hiện trường (NĐ98).

    Thứ tự BẮT BUỘC (mọi nhánh reject TRƯỚC `File.insert`): exists(incident) →
    permission (reporter/write) → **dedupe pre-check (BR-12-26)** → file present →
    content-type → size → max-count → `File.insert(is_private=1)` → lifecycle event
    `incident_photo_attached` (hard-req, KHÔNG swallow) → `commit`. Nếu event throw
    → File.insert rollback (chưa commit) ⇒ không orphan, không silent (khác
    `incident_reported` best-effort).

    BR-12-26 (CR-24 phần dư · B-rel-3 / ADR-IMM12-10): `client_request_id` non-empty
    → dedupe 2 lớp theo composite scoped key `f"{incident}::{key}"` trên Custom Field
    `File.ac_client_request_id` (unique NULL-store): lớp-1 pre-check SAU permission
    (chống probe key leak file_url) / TRƯỚC validation (replay ảnh đã đính phải trả
    success kể cả khi phiếu đã đủ 5 ảnh) — trúng ⇒ early-return `{file_url,file_name}`
    File ĐÃ đính, 0 insert / 0 event lần 2; lớp-2 race-handler `UniqueValidationError`
    → re-read winner (kẻ thua raise TRƯỚC emit ⇒ 0 event trùng). Rỗng/thiếu → mỗi
    call 1 File mới (at-least-once CŨ, field NULL). Cùng key KHÁC incident → composite
    KHÁC → KHÔNG dedupe chéo.

    Args:
        incident_name: Incident Report đang mở.
        filedata: bytes ảnh (API đọc `frappe.request.files["file"].stream.read()`).
        filename: tên tệp gốc (dùng cho File.file_name + lọc đuôi ảnh).
        content_type: MIME type client gửi (validate jpg/png).
        client_request_id: idempotency key per-ảnh (mobile write-outbox re-drain);
            rỗng → behavior at-least-once cũ nguyên vẹn.

    Returns: `{"file_url", "file_name"}`.
    Raises: ServiceError NOT_FOUND | FORBIDDEN | VALIDATION (Decision-B qua API tier).
    """
    incident = _get_incident(incident_name)               # NOT_FOUND nếu thiếu
    _assert_can_attach_photo(incident)                    # FORBIDDEN nếu ngoài quyền
    # BR-12-26 lớp-1: dedupe pre-check — SAU permission / TRƯỚC validation ladder.
    scoped_key = f"{incident_name}::{client_request_id}" if client_request_id else ""
    if scoped_key:
        existing = frappe.db.get_value(
            _DT_FILE, {"ac_client_request_id": scoped_key},
            ["file_url", "file_name"], as_dict=True)
        if existing:
            return {"file_url": existing.file_url, "file_name": existing.file_name}
    if not filedata:
        raise _photo_validation_error(_MSG_PHOTO_MISSING)
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct not in _INCIDENT_PHOTO_CONTENT_TYPES:
        raise _photo_validation_error(_MSG_PHOTO_NOT_IMAGE)
    if len(filedata) > MAX_INCIDENT_PHOTO_BYTES:
        raise _photo_validation_error(_MSG_PHOTO_TOO_LARGE)
    if len(_scene_photos(incident_name)) >= MAX_INCIDENT_PHOTOS:
        raise _photo_validation_error(_MSG_PHOTO_MAX)

    file_payload = {
        "doctype": _DT_FILE,
        "file_name": filename,
        "attached_to_doctype": _DT_INCIDENT,
        "attached_to_name": incident_name,
        "is_private": 1,
        "content": filedata,
        "decode": False,
    }
    # BR-12-26: persist scoped key CHỈ khi truthy (NULL-store — File thường lưu NULL,
    # MariaDB unique index cho phép nhiều NULL ⇒ backward-compat nguyên vẹn).
    if scoped_key:
        file_payload["ac_client_request_id"] = scoped_key
    try:
        file_doc = frappe.get_doc(file_payload).insert(ignore_permissions=True)
    except frappe.UniqueValidationError:
        # BR-12-26 lớp-2 race: request re-drain concurrent đã insert CÙNG scoped_key
        # giữa pre-check và insert này (unique index tabFile chặn kẻ thua). Kẻ thua
        # raise TRƯỚC create_lifecycle_event ⇒ 0 event trùng. Dọn msgprint "must be
        # unique" thừa, re-read winner rồi return idempotent (parity report_incident).
        frappe.clear_last_message()
        winner = frappe.db.get_value(
            _DT_FILE, {"ac_client_request_id": scoped_key},
            ["file_url", "file_name"], as_dict=True)
        if winner:
            return {"file_url": winner.file_url, "file_name": winner.file_name}
        raise
    except (UnidentifiedImageError, OSError) as exc:
        # ẢNH HỎNG/ĐỨT TRUYỀN: bytes không giải mã được dù content-type hợp lệ. Frappe
        # File.before_insert → strip_exif → PIL.Image.open ném UnidentifiedImageError
        # (thân rác) hoặc OSError('Truncated File Read') (cắt cụt), bọc CẢ xử lý ảnh
        # phát sinh. PIL fail TRONG before_insert — TRƯỚC db_insert + write_file (đĩa) +
        # after_rollback.add ⇒ KHÔNG orphan File (DB lẫn đĩa); không cần rollback thủ
        # công (rollback toàn cục sẽ revert phiếu chưa commit khác). Chuyển thành lỗi
        # VALIDATION Decision-B (fields.file) thay vì để HTTP-500 → bằng chứng NĐ98 mất.
        frappe.logger("imm12").warning(
            f"incident_photo_corrupt incident={incident_name} err={type(exc).__name__}"
        )
        raise _photo_validation_error(_MSG_PHOTO_CORRUPT) from exc

    # BR-12-18 (ADR-IMM12-07): evidence trail NĐ98 — hard-requirement, KHÔNG
    # try/except-swallow. Event throw → File.insert rollback (chưa commit).
    svc00.create_lifecycle_event(
        asset=incident.asset,
        event_type=_EVENT_INCIDENT_PHOTO_ATTACHED,
        actor=frappe.session.user,
        root_doctype=_DT_INCIDENT,
        root_record=incident_name,
        notes=f"Đính ảnh bằng chứng: {filename}",
    )
    frappe.db.commit()
    return {"file_url": file_doc.file_url, "file_name": file_doc.file_name}


def _build_incident_available_actions(doc, rca_status: str) -> list[dict]:
    """Derive available_actions (CR-39) = transition_allowed ∩ has_cap ∩ business_gate.

    Mirror imm00._build_available_actions(:762). Lặp SSoT ``_INCIDENT_ACTION_SPECS``
    (6 CTA, thứ tự cố định = thứ tự render FE). Mỗi CTA:
      - ``transition_allowed`` = ``spec['target'] ∈ _VALID_TRANSITIONS[doc.status]``
        ∧ ``doc.status ∈ spec['from']`` (``from`` khử va chạm start_work↔reopen cùng
        đích 'In Progress' — target-membership đơn thuần KHÔNG phân biệt được: cả 2
        đều nhận 'In Progress' làm đích hợp lệ tại Acknowledged/Resolved).
      - ``has_cap`` = ``rbac.can(cap)`` qua ĐÚNG cap-SSoT endpoint ghi
        (``_CAP_INVESTIGATE`` cho ack/start/resolve/cancel, ``_CAP_CLOSE`` cho
        close/reopen) — KHÔNG hardcode literal cap khác (drift = gate nói dối).
      - ``business_gate``: CHỈ 'close' áp BR-12-02 — ``_needs_rca(doc.severity)`` ⇒
        ``rca_status`` phải ``Completed`` (rỗng/chưa Completed → chặn). CTA khác True.
      - ``enabled`` = 3 điều kiện.
      - ``reason`` (CHỈ khi disabled): 3 bậc ưu tiên transition > capability >
        business-gate. Bậc transition phủ luôn status rỗng/lạ (target ∉ []).
    BẤT BIẾN ĐO ĐƯỢC (D9, parity imm00): ``enabled is False ⟹ reason != ""`` với MỌI
    status (kể cả '' và mã LẠ); ``enabled is True ⟹ reason == ""``. Shape phần tử =
    AvailableAction ``{key, label, route, enabled, reason}`` với ``route=""`` (CTA
    nằm TRONG màn Chi tiết, KHÔNG deep-link). READ-ONLY (chỉ rbac.can + đọc
    status/severity — KHÔNG I/O ghi).
    """
    status = doc.status or ""
    valid_targets = _VALID_TRANSITIONS.get(status, [])
    needs_rca = _needs_rca(doc.severity)
    actions: list[dict] = []
    for spec in _INCIDENT_ACTION_SPECS:
        transition_ok = spec["target"] in valid_targets and status in spec["from"]
        cap = _CAP_INVESTIGATE if spec["cap"] == _CTA_INVESTIGATE else _CAP_CLOSE
        has_cap = rbac.can(cap)
        business_ok = True
        if spec["key"] == "close" and needs_rca:
            business_ok = rca_status == _RCA_COMPLETED
        enabled = bool(transition_ok and has_cap and business_ok)
        if enabled:
            reason = ""
        elif not transition_ok:
            reason = _ACTION_REASON_TRANSITION
        elif not has_cap:
            reason = _ACTION_REASON_CAPABILITY
        else:  # business-gate chặn (chỉ 'close')
            reason = _ACTION_REASON_RCA_GATE
        actions.append({
            "key": spec["key"],
            "label": spec["label"],
            "route": "",
            "enabled": enabled,
            "reason": reason,
        })
    return actions


def get_incident_detail(name: str) -> dict:
    """Chi tiết 1 Incident Report (màn Chi tiết web + mobile).

    Ngoài field gốc (`doc.as_dict()`) response còn THÊM:
    - `is_response_breached` / `is_resolution_breached` (0|1, DERIVED LIVE qua
      `_enrich_sla_breach` — CÙNG SoT với `list_incidents`/`get_dashboard`, INV-SLA-5)
      ⇒ badge màn Chi tiết == badge danh sách/dashboard TẠI CÙNG `now`, KHÔNG
      stale-divergence. Consumer đọc cờ derived thay cờ thô `response_breached`/
      `resolution_breached` (có thể chưa được scheduler stamp → stale). Terminal
      (Closed/Cancelled/Resolved) chỉ breach qua nhánh cờ=1 (INV-SLA-6, KHÔNG
      live-overdue dù due đã quá hạn).
    - `asset_name`, `allowed_transitions`, `rca` (nếu có `rca_record`), `scene_photos`.
    - CR-40 (additive/optional — REUSE khuôn user-enrich list_incidents, migrate-free):
      * `reporter_name` = `User.full_name` của `reported_by` (fallback raw id khi thiếu
        full_name) — chỉ có mặt khi `reported_by` set; KHÔNG rò email thô (U7/UI-FIX-05).
      * `assigned_to_name` = `full_name` của `assigned_to` (fallback raw id) — chỉ có mặt
        khi `assigned_to` set.
      * `asset_lifecycle_status` = `AC Asset.lifecycle_status` của `doc.asset` (SONG SONG
        `asset_name`); '' khi phiếu KHÔNG gắn asset. KTV rút máy khỏi vận hành thấy trạng
        thái thiết bị LIVE (U1 / BR-12-04: acknowledge High/Critical → Out of Service).
    """
    doc = _get_incident(name)
    data = doc.as_dict()
    if doc.asset:
        data["asset_name"] = frappe.db.get_value(_DT_ASSET, doc.asset, "asset_name")
        # CR-40: trạng thái vòng đời thiết bị (SONG SONG asset_name) — KTV rút máy khỏi
        # vận hành THẤY trạng thái LIVE (U1 🔴 / BR-12-04: acknowledge High/Critical đẩy
        # asset → Out of Service). READ-ONLY, additive/optional.
        data["asset_lifecycle_status"] = frappe.db.get_value(
            _DT_ASSET, doc.asset, "lifecycle_status")
    else:
        data["asset_lifecycle_status"] = ""
    data["allowed_transitions"] = _VALID_TRANSITIONS.get(doc.status, [])
    # BR-12-09 LIVE (INV-SLA-5): badge màn Chi tiết đọc is_*_breached (derived) thay cờ
    # thô → khớp danh sách/dashboard (CÙNG SoT _enrich_sla_breach, KHÔNG re-implement
    # predicate). Terminal chỉ breach qua nhánh cờ=1 (INV-SLA-6). Surface đúng 2 field
    # mobile cần (không rò field web-only khác).
    _enrich_sla_breach([data])
    # CR-40: bồi tên hiển thị người báo/người xử lý (U7 / UI-FIX-05: chấm dứt rò email
    # thô trên màn Chi tiết sự cố). REUSE nguyên khuôn user-enrich list_incidents
    # (_enrich_asset_names:444-461) — 1 get_all User cho {reported_by, assigned_to},
    # fallback raw id KHI thiếu full_name (KHÔNG rò rỗng). Chỉ set khi field nguồn có
    # giá trị ⇒ additive/optional (consumer cũ bất biến; key vắng khi field trống).
    user_ids = {u for u in (doc.reported_by, doc.assigned_to) if u}
    if user_ids:
        user_map = {u.name: u.full_name for u in frappe.get_all(
            "User", filters={"name": ["in", list(user_ids)]},
            fields=["name", "full_name"],
        )}
        if doc.reported_by:
            data["reporter_name"] = user_map.get(doc.reported_by) or doc.reported_by
        if doc.assigned_to:
            data["assigned_to_name"] = user_map.get(doc.assigned_to) or doc.assigned_to
    rca_status = ""
    if doc.rca_record:
        rca = RCARepo.get(doc.rca_record)
        if rca:
            rca_status = rca.status or ""
            data["rca"] = {
                "name": rca.name,
                "status": rca.status,
                "root_cause": rca.root_cause,
                "due_date": str(rca.due_date) if rca.due_date else None,
                "trigger_type": rca.trigger_type,
            }
    # CR-39: 6 CTA vòng đời server-driven (available_actions[]) — thay predicate-mirror
    # client-side (FE gate nút theo enabled/reason, KHÔNG tự chế nút ⇒ khử "403 sau khi
    # bấm"). rca_status = trạng thái RCA hiện tại (đã tính ở block trên cho gate
    # BR-12-02 close). SSoT _build_incident_available_actions. READ-ONLY (KHÔNG
    # audit/lifecycle/modify doc).
    data["available_actions"] = _build_incident_available_actions(doc, rca_status)
    # BR-12-18: parity chi tiết mobile+web — liệt kê ảnh bằng chứng hiện trường
    # (derive read-time từ File, KHÔNG denormalize → không drift). [] khi chưa có.
    # CÙNG SoT _scene_photos với max-count của attach_incident_photo (count==rows).
    data["scene_photos"] = _scene_photos(name)
    return data


def get_incident_stats() -> dict:
    def _count(f: dict) -> int:
        try:
            return frappe.db.count(_DT_INCIDENT, filters=f)
        except Exception:
            return 0

    return {
        "total": _count({}),
        # SoT "đang mở": MỌI open-state (Open+Acknowledged+In Progress+RCA Required)
        # qua open_incident_filter() → card 'đang mở' == số dòng drill list (invariant).
        # KHÔNG dùng status==Open (bỏ sót Acknowledged/RCA Required).
        "open_total": _count(open_incident_filter()),
        # Per-state breakdown (backward-compat: consumer khác đọc từng state).
        "open": _count({"status": _STATUS_OPEN}),
        "investigating": _count({"status": _STATUS_INVESTIGATING}),
        "resolved": _count({"status": _STATUS_RESOLVED}),
        "closed": _count({"status": _STATUS_CLOSED}),
        "cancelled": _count({"status": _STATUS_CANCELLED}),
        "critical": _count({"severity": _SEV_CRITICAL}),
        "high": _count({"severity": _SEV_HIGH}),
        # Open-set severity (KPI strip worklist): đếm theo SoT open_incident_filter()
        # (∧ severity) — KHÔNG global. Loại Closed/Cancelled/Resolved → strip khớp số
        # dòng severity trong bảng khi drill ?open=1. critical_open<=critical luôn đúng.
        # KHÔNG inline negative-list mới: dùng lại 1 SoT open_incident_filter() (round-18).
        "critical_open": _count(open_incident_filter({"severity": _SEV_CRITICAL})),
        "high_open": _count(open_incident_filter({"severity": _SEV_HIGH})),
        "rca_pending": _count({"rca_required": 1, "rca_record": ("is", "not set")}),
        # BR-12-12: KPI 'chronic' = số NHÓM (asset, fault_code) chronic LIVE
        # (rolling-window 90d, SoT chronic_failure_count == len(get_chronic_failures())).
        # KHÔNG đếm cờ stale chronic_failure_flag (monotone, không giảm khi aged-out →
        # divergence tile-vs-panel). Cờ giữ riêng cho badge per-row (lifecycle BR-12-03).
        "chronic": chronic_failure_count(),
        # BR-12-09 (LIVE SoT): số incident vi phạm SLA = sla_breach_count() =
        # (cờ-lịch-sử=1) OR (đang-mở ∧ quá-hạn-live). KHÔNG đếm cờ thuần
        # _count({..._breached:1}) — sẽ undercount cửa-sổ-trễ-scheduler (incident vừa
        # quá hạn chưa kịp stamp). 1 SoT sla_breach_filter → badge per-row khớp tile.
        "sla_response_breached": sla_breach_count("response"),
        "sla_resolution_breached": sla_breach_count("resolution"),
    }


def get_asset_incident_history(asset: str, limit: int = 10) -> dict:
    rows = frappe.get_all(
        _DT_INCIDENT,
        filters={"asset": asset},
        fields=["name", "incident_type", "severity", "status", "reported_at",
                "fault_code", "closed_date", "linked_capa", "rca_record"],
        order_by=_ORDER_REPORTED_AT,
        limit_page_length=limit,
    )
    return {"asset": asset, "items": rows}


def get_chronic_failures() -> list:
    """Asset có ≥3 sự cố cùng fault_code trong 90 ngày."""
    cutoff = add_days(nowdate(), -_CHRONIC_WINDOW_DAYS)
    return frappe.db.sql("""
        SELECT asset, fault_code, COUNT(*) AS count, MAX(reported_at) AS last_reported
        FROM `tabIncident Report`
        WHERE fault_code IS NOT NULL AND fault_code != ''
          AND reported_at >= %s
          AND status != 'Cancelled'
        GROUP BY asset, fault_code
        HAVING count >= %s
        ORDER BY count DESC
    """, (cutoff, _CHRONIC_MIN_COUNT), as_dict=True)


def chronic_failure_count() -> int:
    """BR-12-12 SoT helper — số NHÓM (asset, fault_code) đang chronic LIVE.

    Cùng predicate get_chronic_failures() (GROUP BY (asset, fault_code) HAVING
    COUNT(*) >= _CHRONIC_MIN_COUNT trong cửa sổ rolling _CHRONIC_WINDOW_DAYS,
    status != Cancelled, fault_code non-empty). Phái sinh TRỰC TIẾP từ
    get_chronic_failures() — KHÔNG re-implement SQL (1 SoT, anti-drift).

    Nguồn DUY NHẤT cho KPI tile 'chronic' (get_incident_stats) — KHÔNG đếm cờ
    bền vững chronic_failure_flag (cờ là dấu lifecycle BR-12-03, monotone-stale,
    không giảm khi cụm aged-out > 90 ngày → divergence tile-vs-panel nếu đếm cờ).
    """
    return len(get_chronic_failures())


def get_dashboard() -> dict:
    stats = get_incident_stats()
    # SoT: dùng CHÍNH open_incident_filter() — KHÔNG tuple open-set cục bộ (chống
    # drift với stats.open_total/list). +Acknowledged +RCA Required (filter cũ
    # [Open, In Progress] bỏ sót). Số dòng (trước limit) khớp open_total.
    recent = frappe.get_all(
        _DT_INCIDENT,
        filters=open_incident_filter(),
        fields=["name", "asset", "severity", "status", "reported_at", "fault_code",
                # BR-12-09: cờ thô + acknowledged_at/due_at để derive LIVE badge.
                "response_breached", "resolution_breached", "acknowledged_at",
                "response_due_at", "resolution_due_at"],
        order_by=_ORDER_REPORTED_AT,
        limit_page_length=10,
    )
    _enrich_asset_names(recent)
    # BR-12-09 LIVE: badge dashboard "Sự cố đang xử lý" đọc is_*_breached (INV-SLA-5).
    _enrich_sla_breach(recent)
    rca_open = frappe.get_all(
        _DT_RCA,
        filters={"status": ["in", [_RCA_REQUIRED, _RCA_IN_PROGRESS]]},
        fields=["name", "incident_report", "asset", "status", "trigger_type", "due_date"],
        order_by="due_date asc",
        limit_page_length=10,
    )
    chronic = get_chronic_failures()[:5]
    return {
        "stats": stats,
        "active_incidents": recent,
        "open_rcas": rca_open,
        "chronic_failures": chronic,
    }


# ─── Scheduler ────────────────────────────────────────────────────────────────

def detect_chronic_failures() -> dict:
    """Daily scheduler — BR-12-03: flag mãn tính + tạo RCA tự động."""
    chronic_groups = get_chronic_failures()
    flagged = 0
    rca_created = 0
    for row in chronic_groups:
        n_flagged, created = _process_chronic_group(row["asset"], row["fault_code"])
        flagged += n_flagged
        rca_created += created
    if flagged or rca_created:
        frappe.db.commit()
    frappe.logger().info(
        f"IMM-12 detect_chronic_failures: {flagged} flagged, {rca_created} RCA created"
    )
    return {"flagged": flagged, "rca_created": rca_created, "groups": len(chronic_groups)}


def check_incident_sla_breach() -> dict:
    """Hourly scheduler — BR-12-08/09/10: đánh dấu SLA breach cho incident CHƯA đóng
    đã quá hạn (response/resolution), ghi audit-trail (BR-12-05) VÀ ESCALATE thông báo
    (in-app + email) tới người phụ trách + escalation user (IMM SLA Policy) + role gate
    NĐ98 (Critical/High → QA Officer + Ops Manager).

    Idempotent (anti-spam): cờ response_breached/resolution_breached là khoá DB bền
    vững. Mỗi loại CHỈ escalate khi cờ tương ứng đang 0 VÀ điều kiện quá hạn đúng
    (set cờ + bắn trong cùng nhánh). Lần quét kế cờ đã =1 → KHÔNG bắn lại.

    Per-incident try/except (batch resilience): 1 incident lỗi (thiếu policy/recipient)
    KHÔNG dừng cả batch. Recipient rỗng → set cờ + audit phát hiện như cũ, KHÔNG bắn rỗng.
    """
    from assetcore.services import notifications as notif

    now = now_datetime()
    # SoT: dùng CHÍNH open_incident_filter() — KHÔNG tuple open_states cục bộ (chống
    # drift với dashboard/list). Cancelled là terminal → KHÔNG vào tập candidate.
    candidates = frappe.get_all(
        _DT_INCIDENT,
        filters=open_incident_filter(),
        # BR-12-09: thêm severity + assigned_to + reported_by để route recipient escalation.
        fields=["name", "asset", "status", "severity", "assigned_to", "reported_by",
                "response_due_at", "resolution_due_at",
                "response_breached", "resolution_breached", "acknowledged_at"],
    )
    resp_flagged = 0
    res_flagged = 0
    escalated = 0
    for row in candidates:
        try:
            updates: dict = {}
            # kinds vừa chuyển 0→1 trong lần quét NÀY (khoá idempotent cho escalation).
            new_kinds: list[str] = []
            # Response breach: chưa tiếp nhận và đã quá response_due_at.
            if (not row.get("response_breached") and not row.get("acknowledged_at")
                    and row.get("response_due_at")
                    and now > frappe.utils.get_datetime(row["response_due_at"])):
                updates["response_breached"] = 1
                new_kinds.append("response")
                resp_flagged += 1
            # Resolution breach: chưa đóng và đã quá resolution_due_at.
            if (not row.get("resolution_breached") and row.get("resolution_due_at")
                    and now > frappe.utils.get_datetime(row["resolution_due_at"])):
                updates["resolution_breached"] = 1
                new_kinds.append("resolution")
                res_flagged += 1
            if not updates:
                continue

            # 1) Set cờ (khoá idempotent) + ghi audit PHÁT HIỆN (BR-12-05, giữ như cũ).
            frappe.db.set_value(_DT_INCIDENT, row["name"], updates, update_modified=False)
            kinds_label = "+".join(new_kinds)
            _log(row["name"], row.get("asset"),
                 f"SLA breach ({kinds_label}) phát hiện bởi scheduler",
                 row["status"], row["status"])

            # 2) ESCALATE: resolve policy escalation user (IMM SLA Policy) + dispatch.
            severity = row.get("severity") or "Low"
            policy = svc00.get_sla_policy(_severity_to_sla_priority(severity)) or {}
            incident_ctx = dict(row)
            incident_ctx["escalation_l1_user"] = policy.get("escalation_l1_user")
            incident_ctx["escalation_l2_user"] = policy.get("escalation_l2_user")

            sent_any = False
            for kind in new_kinds:
                due = row.get("resolution_due_at" if kind == "resolution"
                              else "response_due_at")
                over_h = round(
                    (now - frappe.utils.get_datetime(due)).total_seconds() / 3600.0, 1
                ) if due else 0.0
                if notif._emit_incident_sla_notification(
                    incident_ctx, kind, over_h, severity
                ):
                    sent_any = True

            # 3) Audit ESCALATED (BR-12-05, THÊM entry — KHÔNG thay entry phát hiện).
            if sent_any:
                recipients = notif._incident_sla_recipients(incident_ctx, severity)
                _log(row["name"], row.get("asset"),
                     f"SLA breach escalated → {', '.join(recipients)}",
                     row["status"], row["status"])
                escalated += 1
        except Exception:
            # Per-incident an toàn: 1 incident lỗi KHÔNG dừng batch scheduler.
            frappe.log_error(frappe.get_traceback(), "IMM-12 check_incident_sla_breach")
            continue

    if resp_flagged or res_flagged:
        frappe.db.commit()
    frappe.logger().info(
        f"IMM-12 check_incident_sla_breach: response={resp_flagged}, "
        f"resolution={res_flagged}, escalated={escalated}"
    )
    return {
        "response_breached": resp_flagged,
        "resolution_breached": res_flagged,
        "escalated": escalated,
    }


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _process_chronic_group(asset: str, fault_code: str) -> tuple[int, int]:
    """Flag incidents + create chronic RCA for one (asset, fault_code) group."""
    cutoff = add_days(nowdate(), -_CHRONIC_WINDOW_DAYS)
    ir_list = frappe.get_all(
        _DT_INCIDENT,
        filters={
            "asset": asset, "fault_code": fault_code,
            "status": ["!=", _STATUS_CANCELLED],
            "reported_at": [">=", cutoff],
        },
        fields=["name", "chronic_failure_flag"],
    )
    flagged = 0
    for ir in ir_list:
        if not ir.get("chronic_failure_flag"):
            frappe.db.set_value(_DT_INCIDENT, ir["name"], {"chronic_failure_flag": 1, "rca_required": 1})
            flagged += 1
    existing_rca = frappe.db.exists(_DT_RCA, {
        "asset": asset, "trigger_type": "Chronic Failure",
        "status": ["in", [_RCA_REQUIRED, _RCA_IN_PROGRESS]],
    })
    if existing_rca:
        return flagged, 0
    try:
        rca = frappe.new_doc(_DT_RCA)
        rca.asset = asset
        rca.trigger_type = "Chronic Failure"
        rca.rca_method = "5-Why"
        rca.status = _RCA_REQUIRED
        rca.due_date = add_days(nowdate(), _RCA_DUE_CHRONIC)
        rca.incident_count = len(ir_list)
        for ir_item in ir_list:
            rca.append("related_incidents", {"incident_report": ir_item["name"]})
        for i in range(1, 6):
            rca.append("five_why_steps", {"why_number": i, "why_question": f"Why {i}?", "why_answer": ""})
        rca.flags.ignore_permissions = True
        rca.insert()
        if ir_list:
            frappe.db.set_value(_DT_INCIDENT, ir_list[0]["name"], "rca_record", rca.name)
        if frappe.db.has_column(_DT_ASSET, "chronic_failure_flag"):
            frappe.db.set_value(_DT_ASSET, asset, "chronic_failure_flag", 1)
        svc00.log_audit_event(
            asset=asset, event_type="chronic_failure_detected", actor="Administrator",
            ref_doctype=_DT_RCA, ref_name=rca.name,
            change_summary=f"{len(ir_list)} incidents same fault_code '{fault_code}' in 90 days",
        )
        return flagged, 1
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"IMM-12 chronic RCA create {asset}/{fault_code}")
        return flagged, 0

def _auto_create_rca(doc: "frappe.Document") -> str:
    """Auto-tạo RCA sau resolve cho High/Critical."""
    trigger = "Critical Incident" if doc.severity == _SEV_CRITICAL else "Major Incident"
    rca = frappe.new_doc(_DT_RCA)
    rca.incident_report = doc.name
    rca.asset = doc.asset
    rca.rca_method = "5-Why"
    rca.trigger_type = trigger
    rca.status = _RCA_REQUIRED
    rca.assigned_to = frappe.session.user
    rca.due_date = add_days(nowdate(), _RCA_DUE_MAJOR)
    for i in range(1, 6):
        rca.append("five_why_steps", {"why_number": i, "why_question": f"Why {i}?", "why_answer": ""})
    rca.flags.ignore_permissions = True
    rca.insert()
    frappe.db.set_value(_DT_INCIDENT, doc.name, {
        "rca_record": rca.name,
        "rca_required": 1,
    })
    frappe.db.commit()
    return rca.name


def _auto_create_capa(doc: "frappe.Document") -> None:
    try:
        capa_name = svc00.create_capa(
            asset=doc.asset,
            source_type=_DT_INCIDENT,
            source_ref=doc.name,
            severity=_map_severity(doc.severity),
            description=f"Auto-CAPA từ Incident {doc.name}: {(doc.description or '')[:200]}",
            responsible=frappe.session.user,
        )
        frappe.db.set_value(_DT_INCIDENT, doc.name, "linked_capa", capa_name)
        frappe.db.commit()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-12 _auto_create_capa")


# ─── RCA → Incident chain (RC-03 + RC-04) ─────────────────────────────────────

_WORKFLOW_NAME_INCIDENT = "IMM-12 Incident Workflow"
_ACTION_RCA_DONE_CLOSE = "RCA hoàn tất - đóng sự cố"
# BR-12-24: action workflow "Yêu cầu RCA" (Resolved → RCA Required). Verbatim khớp
# imm_12_incident_workflow.json.transitions[].action (chống drift tên action).
_ACTION_REQUEST_RCA = "Yêu cầu RCA"


def on_rca_completed(incident_name: str, rca_name: str) -> dict:
    """Hook RCA Record on_submit → ensure CAPA + advance Incident workflow.

    Idempotent — re-uses existing linked_capa, skips workflow apply nếu state đã Closed.
    Wrap mọi side-effect trong try/except — KHÔNG fail RCA submit nếu chain lỗi.
    """
    out: dict = {"incident": incident_name, "rca": rca_name,
                 "capa_name": None, "workflow_advanced": False}
    if not incident_name or not frappe.db.exists(_DT_INCIDENT, incident_name):
        return out

    # 1. CAPA chain (RC-03)
    try:
        from assetcore.services.imm16 import create_capa_from_incident
        result = create_capa_from_incident(
            incident_name=incident_name,
            rca_name=rca_name or "",
            responsible=frappe.session.user,
        )
        out["capa_name"] = result.get("capa_name")
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-12 on_rca_completed CAPA chain")

    # 2. Incident workflow auto-advance (RC-04)
    try:
        out["workflow_advanced"] = _advance_incident_after_rca(incident_name)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-12 on_rca_completed workflow")

    return out


def _advance_incident_after_rca(incident_name: str) -> bool:
    """Đẩy Incident từ 'RCA Required' → 'Closed' qua action workflow chuẩn.

    Frappe Workflow KHÔNG cho phép gán workflow_state tùy ý — phải đi qua
    apply_workflow(action). Nếu incident không ở 'RCA Required' (đã closed
    rồi, hoặc workflow chưa tới đó), no-op an toàn.
    """
    from frappe.model.workflow import apply_workflow

    inc = frappe.get_doc(_DT_INCIDENT, incident_name)
    current_state = inc.get("workflow_state") or inc.get("status") or ""
    if current_state == _STATUS_CLOSED:
        return False  # đã đóng — không làm gì
    if current_state != "RCA Required":
        # Workflow chưa tới RCA Required (vd RCA tạo từ chronic, incident vẫn ở Resolved)
        # KHÔNG ép — log để observability.
        frappe.logger().info(
            f"IMM-12 _advance_incident_after_rca: incident {incident_name} "
            f"đang ở '{current_state}', skip apply_workflow"
        )
        return False

    try:
        apply_workflow(inc, _ACTION_RCA_DONE_CLOSE)
        # Workflow chỉ flip workflow_state field — sync status (Select) +
        # closed_by/closed_date để truy vấn list filter status="Closed" còn đúng.
        frappe.db.set_value(
            _DT_INCIDENT, incident_name,
            {
                "status": _STATUS_CLOSED,
                "closed_by": frappe.session.user,
                "closed_date": today(),
            },
            update_modified=False,
        )
        frappe.db.commit()
        _log(incident_name, inc.asset or "",
             "Auto-closed sau khi RCA hoàn tất",
             "RCA Required", _STATUS_CLOSED)
        return True
    except Exception as e:
        # Có thể fail vì permission (RCA submitter không có System Manager).
        # Thử fallback bằng cách close trực tiếp qua service close_incident()
        # với ignore_permissions — vì RCA đã đảm bảo gate BR-12-02 đạt.
        frappe.log_error(
            f"apply_workflow failed for {incident_name}: {e}",
            "IMM-12 _advance_incident_after_rca"
        )
        try:
            # Bypass workflow engine — direct field set + audit
            prev = inc.workflow_state or inc.status
            frappe.db.set_value(
                _DT_INCIDENT, incident_name,
                {
                    "workflow_state": _STATUS_CLOSED,
                    "status": _STATUS_CLOSED,
                    "closed_by": frappe.session.user,
                    "closed_date": today(),
                },
            )
            frappe.db.commit()
            _log(incident_name, inc.asset or "",
                 "Auto-closed (fallback direct) sau RCA hoàn tất",
                 prev, _STATUS_CLOSED)
            return True
        except Exception:
            frappe.log_error(frappe.get_traceback(),
                             "IMM-12 _advance_incident_after_rca fallback")
            return False


def validate_incident_close_gate(doc, method: str | None = None) -> None:
    """NEG-11: Hook 'Incident Report.validate' — chặn đóng High/Critical
    khi chưa có RCA Completed (đường desk / apply_workflow / doc.save trực tiếp,
    song song gate service close_incident:711 — CÙNG SSoT = LIVE severity).

    BR-12-02 (non-waivable): High/Critical = RCA bắt buộc, KHÔNG waiver bằng cờ.
    Gate chỉ đọc LIVE `severity` (SSoT). ĐÃ BỎ nhánh bypass theo `rca_required`
    (read_only mirror-của-severity, KHÔNG phải lever admin) — bypass cũ khiến
    escalation Medium→Critical với cờ stale=0 đóng-giả qua desk path. INV:
    rca_required = derived(severity) re-sync mọi save
    (IncidentReport._resync_rca_required) chạy TRƯỚC hook này trong chuỗi validate.
    Ref: memory server-flag-SSoT / derive-live.

    Áp dụng khi workflow_state hoặc status đang chuyển sang Closed.
    """
    target_state = (doc.get("workflow_state") or "") or (doc.get("status") or "")
    if target_state != _STATUS_CLOSED:
        return
    severity = doc.get("severity") or ""
    if severity not in _HIGH_SEVERITY:
        return
    rca_name = doc.get("rca_record")
    if not rca_name:
        nthrow_in_hook(MSG.IMM12_CLOSE_RCA_REQUIRED, severity=severity)
    rca_status = frappe.db.get_value(_DT_RCA, rca_name, "status")
    if rca_status != _RCA_COMPLETED:
        nthrow_in_hook(MSG.IMM12_CLOSE_RCA_INCOMPLETE,
                       severity=severity, rca=rca_name)


def _try_transition_asset(
    asset: str, to_status: str, incident_name: str, actor: str,
) -> None:
    cur = frappe.db.get_value(_DT_ASSET, asset, "lifecycle_status") or ""
    if cur in (to_status, "Decommissioned"):
        return
    try:
        svc00.transition_asset_status(
            asset_name=asset, to_status=to_status,
            actor=actor,
            root_doctype=_DT_INCIDENT, root_record=incident_name,
            reason=f"Incident {incident_name} → {to_status}",
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"IMM-12 asset transition {asset}→{to_status}")
