# Copyright (c) 2026, AssetCore Team
"""IMM-12 — Incident & CAPA API endpoints.

Incident workflow: Open → Acknowledged → In Progress → Resolved → Closed
CAPA endpoints: delegate to imm00 (create_capa, list_capa, get_capa, close_capa).

Base URL: /api/method/assetcore.api.imm12
"""
from __future__ import annotations

import frappe
from frappe import _

from assetcore.utils.response import _err
from assetcore.utils.api_handler import handle, parse_json
from assetcore.services.shared import rbac
from assetcore.services.shared.scope import assert_vendor_can_access
from assetcore.services.imm12 import (
    report_incident as svc_report,
    cancel_incident as svc_cancel,
    acknowledge_incident as svc_acknowledge,
    start_work as svc_start_work,
    resolve_incident as svc_resolve,
    reopen_incident as svc_reopen,
    request_rca as svc_request_rca,
    list_rcas as svc_list_rcas,
    close_incident as svc_close,
    create_rca as svc_create_rca,
    get_rca as svc_get_rca,
    start_rca as svc_start_rca,
    submit_rca as svc_submit_rca,
    cancel_rca as svc_cancel_rca,
    list_incidents as svc_list,
    get_incident_detail as svc_get,
    attach_incident_photo as svc_attach_photo,
    get_asset_incident_history as svc_asset_history,
    get_chronic_failures as svc_chronic,
    get_dashboard as svc_dashboard,
    get_incident_stats as svc_stats,
    _CAP_INVESTIGATE,
    _CAP_CLOSE,
)

_MSG_UNAUTHENTICATED = "Chưa đăng nhập"
_MSG_SERVER_ERROR = "Lỗi server"
_MSG_FORBIDDEN = "Không có quyền thực hiện hành động này"

# R16 FIX: gate IMM-12 theo CAPABILITY THẬT (DocPerm trên Incident Report) — KHÔNG
# hardcode role-name bịa. _CAP_INVESTIGATE/_CAP_CLOSE nay là SSoT DÙNG CHUNG với
# service builder (_build_incident_available_actions) — IMPORT từ services.imm12 ở
# trên (1 nguồn hằng số, chống drift cap "gate nói dối"). Capability resolve qua
# frappe.has_permission → tôn trọng Role Profile thật + granular (write =
# triage/work/resolve/RCA; submit = close). Cùng pattern IMM-09.
# V4-GATE BÁO-HỎNG (ADR-IMM12-REPORT-FAILURE D1): gate report_incident bằng CÙNG cap
# 'corrective.create' với route-guard FE (router/index.ts:450 IncidentCreate) +
# scan-action SSoT (services/imm00.py _SCAN_ACTION_SPECS report_failure) → parity
# 3-tier, đóng lỗ leo quyền P1 (user corrective.read-only KHÔNG tạo được Incident).
# DÙNG rbac.can + _err(_MSG_FORBIDDEN,403) — KHÔNG rbac.require (require leak raw cap
# 'corrective.create' vào message, vi phạm AC1 no-leak — rbac.py:156-162).
_CAP_REPORT = "corrective.create"          # → ("Incident Report", "create")
# BR-12-24 (CR-WF-12-RCA-ENTRY): "Yêu cầu phân tích RCA" (Resolved → RCA Required).
# Cap `compliance.submit` = ("IMM CAPA Record","submit") → role-set {Compliance
# Manager, AssetCore Super Admin} ⊆ workflow "Yêu cầu RCA" allowed {Compliance
# Manager, System Manager, AssetCore Super Admin} ⇒ KHÔNG false-clickable (cap ⊆
# workflow). Residual: pure-System Manager ∉ compliance.submit → nút ẩn/cap-403 trên
# SPA (an toàn, phủ qua Super Admin + desk admin-override). DÙNG rbac.can +
# _MSG_FORBIDDEN (KHÔNG rbac.require — require leak raw cap vào message).
_CAP_REQUEST_RCA = "compliance.submit"     # → ("IMM CAPA Record", "submit")


def _can_investigate() -> bool:
    return rbac.can(_CAP_INVESTIGATE)


def _can_report() -> bool:
    return rbac.can(_CAP_REPORT)


def _can_close() -> bool:
    return rbac.can(_CAP_CLOSE)


def _can_request_rca() -> bool:
    return rbac.can(_CAP_REQUEST_RCA)


@frappe.whitelist(methods=["POST"])
def report_incident(
    asset: str,
    incident_type: str,
    severity: str,
    description: str,
    fault_code: str = "",
    workaround_applied: int = 0,
    clinical_impact: str = "",
    patient_affected: int = 0,
    patient_impact_description: str = "",
    immediate_action: str = "",
    linked_repair_wo: str = "",
    occurred_datetime: str = "",
    source: str = "manual",
    client_request_id: str = "",
):
    """POST /api/method/assetcore.api.imm12.report_incident

    `source` (ADR-IMM12-REPORT-FAILURE D2): provenance nguồn báo hỏng — 'qr-scan'
    khi đến từ màn quét QR, 'manual' (mặc định) khi tạo thủ công. str='manual'
    (KHÔNG str|None → tránh HTTP 417 pydantic-coercion).

    `client_request_id` (CR-24 idempotency): khoá do client (mobile write-outbox)
    sinh — CÙNG khoá gọi 2 lần chỉ tạo 1 phiếu; call trùng trả `name` phiếu đã tạo
    (KHÔNG insert/audit lần 2 → chống làm bẩn vết audit NĐ98). Nguồn khoá (HANDOFF
    §2.1 header-parity, parity imm09/imm00/imm11): body param THẮNG header
    `X-Idempotency-Key` / alias `Idempotency-Key`; cả hai vắng ⇒ NO-OP dedup, tạo mới
    bình thường (backward-compat 100%). str='' (KHÔNG str|None → tránh HTTP 417).
    """
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)
    # D1: cap-gate 'corrective.create' (parity 3-tier) TRƯỚC handle — đóng đường
    # curl/REST bypass. KHÔNG leak raw cap (rbac.can + _MSG_FORBIDDEN VI hằng số).
    if not _can_report():
        return _err(_(_MSG_FORBIDDEN), 403)
    return handle(
        svc_report,
        asset=asset, incident_type=incident_type, severity=severity,
        description=description, fault_code=fault_code,
        workaround_applied=int(workaround_applied), clinical_impact=clinical_impact,
        patient_affected=int(patient_affected),
        patient_impact_description=patient_impact_description,
        immediate_action=immediate_action, linked_repair_wo=linked_repair_wo,
        occurred_datetime=occurred_datetime,
        source=source,
        client_request_id=client_request_id,
    )


@frappe.whitelist(methods=["POST"])
def cancel_incident(name: str, reason: str):
    """POST /api/method/assetcore.api.imm12.cancel_incident"""
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)
    if not _can_investigate():
        return _err(_(_MSG_FORBIDDEN), 403)
    return handle(svc_cancel, name, reason=reason)


@frappe.whitelist(methods=["POST"])
def create_rca(incident_name: str, rca_method: str = "5-Why"):
    """POST /api/method/assetcore.api.imm12.create_rca"""
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)
    if not _can_investigate():
        return _err(_("Không có quyền tạo RCA"), 403)
    return handle(svc_create_rca, incident_name, rca_method=rca_method)


@frappe.whitelist()
def get_rca(name: str):
    """GET /api/method/assetcore.api.imm12.get_rca

    Emit `allowed_transitions` (SSoT _RCA_VALID_TRANSITIONS) + `can_manage_rca`
    (int 0/1) cho server-driven CTA ở RCADetailView (GATE-8/LL-FE-51).
    """
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)
    return handle(svc_get_rca, name)


@frappe.whitelist(methods=["POST"])
def start_rca(name: str):
    """POST /api/method/assetcore.api.imm12.start_rca

    "Bắt đầu phân tích": 'RCA Required' → 'RCA In Progress'. Cap-gate corrective.write
    ở SERVICE → ServiceError(FORBIDDEN) Decision-B khi thiếu quyền (KHÔNG dispatcher
    403 thô). Sai trạng thái → BAD_STATE inline VN.
    """
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)
    return handle(svc_start_rca, name)


@frappe.whitelist()
def list_rcas(method: str = "", status: str = "", asset: str = "",
              page: int = 1, page_size: int = 20):
    """GET /api/method/assetcore.api.imm12.list_rcas — danh sách RCA cho /rca."""
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)
    return handle(
        svc_list_rcas,
        method=method, status=status, asset=asset,
        page=int(page), page_size=int(page_size),
    )


@frappe.whitelist(methods=["POST"])
def submit_rca(
    name: str,
    root_cause: str,
    corrective_action: str,
    preventive_action: str = "",
    five_why_steps: str = "[]",
    rca_notes: str = "",
):
    """POST /api/method/assetcore.api.imm12.submit_rca"""
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)
    if not _can_investigate():
        return _err(_("Không có quyền submit RCA"), 403)
    steps = parse_json(five_why_steps, field_name="five_why_steps", default=[])
    return handle(
        svc_submit_rca,
        name, root_cause=root_cause, corrective_action=corrective_action,
        preventive_action=preventive_action, five_why_steps=steps, rca_notes=rca_notes,
    )


@frappe.whitelist(methods=["POST"])
def cancel_rca(name: str, reason: str = ""):
    """POST /api/method/assetcore.api.imm12.cancel_rca

    "Hủy RCA": 'RCA Required'|'RCA In Progress' → 'Cancelled'. Cap-gate
    corrective.submit ở SERVICE (thao tác đề-cao) → ServiceError(FORBIDDEN)
    Decision-B khi thiếu quyền. Sai trạng thái (Completed/Cancelled) → BAD_STATE
    inline VN. `reason` optional (str="" — tránh 417).
    """
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)
    return handle(svc_cancel_rca, name, reason=reason)


@frappe.whitelist()
def get_asset_incident_history(asset: str, limit: int = 10):
    """GET /api/method/assetcore.api.imm12.get_asset_incident_history"""
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)
    return handle(svc_asset_history, asset, limit=int(limit))


@frappe.whitelist()
def get_chronic_failures():
    """GET /api/method/assetcore.api.imm12.get_chronic_failures"""
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)
    return handle(svc_chronic)


@frappe.whitelist()
def get_dashboard():
    """GET /api/method/assetcore.api.imm12.get_dashboard"""
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)
    return handle(svc_dashboard)


@frappe.whitelist()
def list_incidents(
    status: str = "",
    severity: str = "",
    asset: str = "",
    open: int = 0,
    mine: int = 0,
    page: int = 1,
    page_size: int = 20,
):
    """GET /api/method/assetcore.api.imm12.list_incidents

    `open=1` áp SoT open_incident_filter() (incident đang mở) cho drill-down từ
    dashboard donut/card → count == số dòng list. `status` đơn lẻ ưu tiên hơn open.
    `mine=1` scope reported_by == session.user (tab "Báo hỏng của tôi" MVP-5c —
    ADR-IMM12-05 / ADR-MOBILE-015); mine=0/absent = list permission-aware UNCHANGED
    (web-FE IncidentListView KHÔNG đổi). Forward int — session resolve ở service-layer.
    """
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)
    return handle(
        svc_list,
        status=status, severity=severity, asset=asset, open=int(open or 0),
        mine=int(mine or 0), page=int(page), page_size=int(page_size),
    )


@frappe.whitelist()
def get_incident(name: str):
    """GET /api/method/assetcore.api.imm12.get_incident"""
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)

    def _run():
        # AUTH-10: IDOR guard — vendor user can't read incident outside scope.
        assert_vendor_can_access("Incident Report", name)
        return svc_get(name)

    return handle(_run)


@frappe.whitelist(methods=["POST"])
def attach_incident_photo(incident_name: str = "", client_request_id: str = "",
                          **_ignore):
    """POST (multipart) /api/method/assetcore.api.imm12.attach_incident_photo

    BR-12-17/18 (mobile CR-17/G6): đính ảnh bằng chứng hiện trường (NĐ98) vào 1
    Incident Report → File private + đúng 1 lifecycle `incident_photo_attached`.
    Single-step multipart: server đọc `frappe.request.files["file"]`, tự validate +
    tạo + link File (robust, KHÔNG orphan như 2-bước upload→file_url).

    `client_request_id` (CR-24 phần dư · B-rel-3 / BR-12-26 idempotency): khoá per-ảnh
    do client (mobile write-outbox PHA-2) sinh, ổn định qua mọi re-drain của CÙNG ảnh.
    Non-empty + cùng incident gọi lặp ⇒ trả File ĐÃ đính (KHÔNG File/event trùng —
    dedupe service ADR-IMM12-10). Rỗng/thiếu ⇒ hành vi at-least-once cũ. Param TƯỜNG
    MINH (multipart form part — KHÔNG còn bị `**_ignore` nuốt câm); default `""`
    (KHÔNG None — tránh HTTP-417 coercion).

    `**_ignore` nuốt kwargs spoof KHÁC (đối xứng register_device_token). Guest/no-session
    → dispatcher-403 (POST @whitelist không allow_guest); permission (reporter OR
    incident.write) + validation ở service → Decision-B HTTP-200 qua `handle`.
    """
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)
    files = frappe.request.files if getattr(frappe, "request", None) else None
    upload = files.get("file") if files else None
    # File present check nằm ở service (sau permission — thứ tự spec §15): truyền
    # filedata=None khi thiếu file → service raise VALIDATION 'Thiếu tệp ảnh'.
    if upload is not None:
        filedata = upload.stream.read()
        filename = upload.filename or ""
        content_type = upload.content_type or ""
    else:
        filedata, filename, content_type = None, "", ""
    return handle(
        svc_attach_photo,
        incident_name,
        filedata=filedata,
        filename=filename,
        content_type=content_type,
        client_request_id=client_request_id,
    )


@frappe.whitelist(methods=["POST"])
def acknowledge_incident(name: str, notes: str = "", assigned_to: str = ""):
    """POST /api/method/assetcore.api.imm12.acknowledge_incident
    "Tiếp nhận": Open → Acknowledged.
    """
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)
    if not _can_investigate():
        return _err(_(_MSG_FORBIDDEN), 403)
    return handle(svc_acknowledge, name, notes=notes, assigned_to=assigned_to)


@frappe.whitelist(methods=["POST"])
def start_work(name: str, notes: str = ""):
    """POST /api/method/assetcore.api.imm12.start_work
    "Bắt đầu xử lý": Acknowledged → In Progress.
    """
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)
    if not _can_investigate():
        return _err(_(_MSG_FORBIDDEN), 403)
    return handle(svc_start_work, name, notes=notes)


@frappe.whitelist(methods=["POST"])
def resolve_incident(name: str, resolution_notes: str, root_cause: str = ""):
    """POST /api/method/assetcore.api.imm12.resolve_incident
    In Progress → Resolved. Auto-creates CAPA if High/Critical.
    """
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)
    if not _can_investigate():
        return _err(_(_MSG_FORBIDDEN), 403)
    return handle(svc_resolve, name, resolution_notes=resolution_notes,
                  root_cause=root_cause)


@frappe.whitelist(methods=["POST"])
def close_incident(name: str, verification_notes: str = ""):
    """POST /api/method/assetcore.api.imm12.close_incident
    Resolved → Closed. Requires Workshop Lead or QA Officer.
    """
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)
    if not _can_close():
        return _err(_("Không có quyền đóng Incident (cần Workshop Lead hoặc QA Officer)"), 403)
    return handle(svc_close, name, verification_notes=verification_notes)


@frappe.whitelist(methods=["POST"])
def reopen_incident(name: str, reason: str):
    """POST /api/method/assetcore.api.imm12.reopen_incident
    "Mở lại điều tra": Resolved → In Progress (BR-12-23, CR-WF-12).

    Cap `incident.close` (parity Close — cùng role-set workflow {System Manager,
    AssetCore Super Admin}). Lỗi nghiệp vụ (reason rỗng → IMM12_REOPEN_REASON_REQUIRED;
    status≠Resolved → IMM12_BAD_STATE) trả in-handler HTTP-200 + Error envelope qua
    handle() — KHÔNG raise HTTP-4xx.
    """
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)
    if not _can_close():
        return _err(_(_MSG_FORBIDDEN), 403)
    return handle(svc_reopen, name, reason=reason)


@frappe.whitelist(methods=["POST"])
def request_rca(name: str, rca_reason: str):
    """POST /api/method/assetcore.api.imm12.request_rca
    "Yêu cầu phân tích RCA": Resolved → RCA Required (BR-12-24, CR-WF-12-RCA-ENTRY).

    Cap `compliance.submit` (rbac.can + `_MSG_FORBIDDEN`, parity ack/close — KHÔNG
    rbac.require leak raw cap). Lỗi nghiệp vụ (rca_reason blank →
    IMM12_RCA_REASON_REQUIRED; status≠Resolved → IMM12_REQUEST_RCA_BAD_STATE, cả 2 =
    422 bucket) trả in-handler HTTP-200 + Error envelope qua handle() — KHÔNG raise
    HTTP-4xx. Cap ⊆ workflow "Yêu cầu RCA" ⇒ nút hiện == nút bấm-được (KHÔNG dead-gate).
    """
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)
    if not _can_request_rca():
        return _err(_(_MSG_FORBIDDEN), 403)
    return handle(svc_request_rca, name, rca_reason=rca_reason)


@frappe.whitelist()
def get_incident_stats():
    """GET /api/method/assetcore.api.imm12.get_incident_stats — KPI tổng quan.

    Forward verbatim svc_stats (services/imm12.get_incident_stats) — SoT DUY NHẤT
    cho mọi count. KHÔNG re-compute ở API (trước fix dùng status 'Under Investigation'
    KHÔNG tồn tại → open/investigating sai; thiếu open_total). Service đã chuẩn hoá
    open_total = count(open_incident_filter()) + per-state breakdown.
    """
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)
    return handle(svc_stats)
