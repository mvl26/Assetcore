# Copyright (c) 2026, AssetCore Team
"""IMM-06 — Training & Competency API endpoints.

Base URL: /api/method/assetcore.api.imm06
"""
from __future__ import annotations

import json

import frappe

from assetcore.services import imm06 as svc
from assetcore.services.shared import ErrorCode, ServiceError
from assetcore.utils.helpers import _err, _ok

_MSG_GUEST = "Chưa đăng nhập"


def _guard() -> None:
    if frappe.session.user == "Guest":
        raise ServiceError(ErrorCode.UNAUTHORIZED, _MSG_GUEST)


def _parse(raw: str, *, field: str, default=None):
    if not raw:
        return default if default is not None else {}
    if not isinstance(raw, str):
        return raw
    try:
        return json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise ServiceError(ErrorCode.INVALID_PARAMS,
                           f"{field} không phải JSON hợp lệ") from exc


def _run(fn, *args, **kwargs) -> dict:
    try:
        _guard()
        return _ok(fn(*args, **kwargs))
    except ServiceError as e:
        return _err(e.message, e.code)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-06 API error")
        return _err("Lỗi server", ErrorCode.INTERNAL)


# ─── Group A: Training Program ────────────────────────────────────────────────

@frappe.whitelist()
def list_programs(filters: str = "{}", page: int = 1, page_size: int = 20) -> dict:
    """GET /api/method/assetcore.api.imm06.list_programs"""
    try:
        f = _parse(filters, field="filters")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _run(svc.list_programs, f, int(page), int(page_size))


@frappe.whitelist()
def get_program(name: str) -> dict:
    """GET /api/method/assetcore.api.imm06.get_program"""
    return _run(svc.get_program, name)


@frappe.whitelist(methods=["POST"])
def create_program(program_data: str = "{}") -> dict:
    """POST /api/method/assetcore.api.imm06.create_program"""
    try:
        data = _parse(program_data, field="program_data")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _run(svc.create_program, data)


@frappe.whitelist(methods=["POST"])
def update_program(name: str, program_data: str = "{}") -> dict:
    """POST /api/method/assetcore.api.imm06.update_program"""
    try:
        data = _parse(program_data, field="program_data")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _run(svc.update_program, name, data)


# ─── Group B: Training Session ────────────────────────────────────────────────

@frappe.whitelist()
def list_sessions(filters: str = "{}", page: int = 1, page_size: int = 20) -> dict:
    """GET /api/method/assetcore.api.imm06.list_sessions"""
    try:
        f = _parse(filters, field="filters")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _run(svc.list_sessions, f, int(page), int(page_size))


@frappe.whitelist()
def get_session(name: str) -> dict:
    """GET /api/method/assetcore.api.imm06.get_session"""
    return _run(svc.get_session, name)


@frappe.whitelist(methods=["POST"])
def create_session(session_data: str = "{}") -> dict:
    """POST /api/method/assetcore.api.imm06.create_session"""
    try:
        data = _parse(session_data, field="session_data")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _run(svc.create_session, data)


@frappe.whitelist(methods=["POST"])
def confirm_session(name: str) -> dict:
    """POST /api/method/assetcore.api.imm06.confirm_session"""
    return _run(svc.confirm_session, name)


@frappe.whitelist(methods=["POST"])
def start_session(name: str) -> dict:
    """POST /api/method/assetcore.api.imm06.start_session"""
    return _run(svc.start_training_session, name)


@frappe.whitelist(methods=["POST"])
def enroll_participants(name: str, participants: str = "[]") -> dict:
    """POST /api/method/assetcore.api.imm06.enroll_participants

    Slide 19: thêm học viên vào buổi học (FE add/create trainee).
    `participants` là JSON list[{user|external_name, department?, role_at_session?}].
    """
    try:
        rows = _parse(participants, field="participants", default=[])
    except ServiceError as e:
        return _err(e.message, e.code)
    return _run(svc.enroll_participants, name, rows)


@frappe.whitelist(methods=["POST"])
def remove_participant(name: str, row_name: str) -> dict:
    """POST /api/method/assetcore.api.imm06.remove_participant

    Xóa 1 dòng học viên (row name của IMM Training Participant) khỏi buổi học.
    """
    return _run(svc.remove_participant, name, row_name)


@frappe.whitelist(methods=["POST"])
def complete_session(name: str, participants_results: str = "[]") -> dict:
    """POST /api/method/assetcore.api.imm06.complete_session"""
    try:
        results = _parse(participants_results, field="participants_results", default=[])
    except ServiceError as e:
        return _err(e.message, e.code)
    return _run(svc.complete_session, name, results)


@frappe.whitelist(methods=["POST"])
def cancel_session(name: str, cancel_reason: str = "") -> dict:
    """POST /api/method/assetcore.api.imm06.cancel_session"""
    return _run(svc.cancel_session, name, cancel_reason)


@frappe.whitelist(methods=["POST"])
def verify_session(name: str) -> dict:
    """POST /api/method/assetcore.api.imm06.verify_session"""
    return _run(svc.verify_session, name)


@frappe.whitelist(methods=["POST"])
def close_session(name: str) -> dict:
    """POST /api/method/assetcore.api.imm06.close_session"""
    return _run(svc.close_session, name)


# ─── Group C: User Competency ─────────────────────────────────────────────────

@frappe.whitelist()
def list_competencies(filters: str = "{}", page: int = 1, page_size: int = 20) -> dict:
    """GET /api/method/assetcore.api.imm06.list_competencies"""
    try:
        f = _parse(filters, field="filters")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _run(svc.list_competencies, f, int(page), int(page_size))


@frappe.whitelist()
def get_user_competencies(user: str = "") -> dict:
    """GET /api/method/assetcore.api.imm06.get_user_competencies"""
    return _run(svc.get_user_competencies, user or frappe.session.user)


@frappe.whitelist()
def get_competency(name: str) -> dict:
    """GET /api/method/assetcore.api.imm06.get_competency

    GATE-8 / LL-FE-51: trả hồ sơ năng lực + ``allowed_transitions`` (server-driven,
    phái sinh từ SSoT ``_COMPETENCY_VALID_TRANSITIONS``) + cờ can_signoff/can_revoke/
    can_recertify/can_suspend/can_restore đã lọc theo capability caller. FE gate 5 CTA
    (Sign-off / Tạm ngưng / Khôi phục / Thu hồi / Tái chứng nhận) theo đây, KHÔNG hardcode
    ``workflow_state === 'X'``.
    """
    return _run(svc.get_competency, name)


@frappe.whitelist(methods=["POST"])
def signoff_competency(name: str) -> dict:
    """POST /api/method/assetcore.api.imm06.signoff_competency

    BE-06-01: Chỉ supervisor (Training Manager / PM Manager / Compliance Manager
    / Super Admin) được phép sign-off. Gate qua capability `training.submit`.
    Side-effect: chuyển workflow_state PENDING → ACTIVE và update IMM User
    Competency row.
    """
    from assetcore.services.shared import rbac
    if not rbac.can("training.submit"):
        return _err(
            "Chỉ Training Manager / Super Admin được sign-off",
            ErrorCode.FORBIDDEN,
        )
    return _run(svc.signoff_competency_by_name, name)


@frappe.whitelist(methods=["POST"])
def revoke_competency(name: str, reason: str, capa_ref: str = "") -> dict:
    """POST /api/method/assetcore.api.imm06.revoke_competency

    VÁ lỗ RBAC (parity signoff_competency): thu hồi năng lực là thao tác vòng đời
    HUỶ hiệu lực operator (NĐ98) → chỉ Training Manager / Super Admin (capability
    ``training.submit``) được phép. Thiếu quyền → FORBIDDEN, KHÔNG đổi workflow_state.
    """
    from assetcore.services.shared import rbac
    if not rbac.can("training.submit"):
        return _err(
            "Chỉ Training Manager / Super Admin được thu hồi năng lực",
            ErrorCode.FORBIDDEN,
        )
    return _run(svc.revoke_competency_with_capa, name, reason, capa_ref)


@frappe.whitelist(methods=["POST"])
def recertify_competency(name: str, new_session: str) -> dict:
    """POST /api/method/assetcore.api.imm06.recertify_competency

    VÁ lỗ RBAC (parity signoff_competency): tái chứng nhận cấp lại hiệu lực operator
    → chỉ Training Manager / Super Admin (capability ``training.submit``) được phép.
    Thiếu quyền → FORBIDDEN, KHÔNG đổi workflow_state.
    """
    from assetcore.services.shared import rbac
    if not rbac.can("training.submit"):
        return _err(
            "Chỉ Training Manager / Super Admin được tái chứng nhận năng lực",
            ErrorCode.FORBIDDEN,
        )
    return _run(svc.recertify_competency, name, new_session)


@frappe.whitelist(methods=["POST"])
def suspend_competency(name: str, reason: str = "") -> dict:
    """POST /api/method/assetcore.api.imm06.suspend_competency

    CR-WF-06-COMP (parity revoke/recertify): Tạm ngưng năng lực Active → Suspended.
    Chỉ Training Manager / Super Admin (capability ``training.submit``) được phép.
    Thiếu quyền → FORBIDDEN, KHÔNG đổi workflow_state. ``reason`` bắt buộc (rỗng →
    service raise VALIDATION); nguồn ≠ Active → BAD_STATE.
    """
    from assetcore.services.shared import rbac
    if not rbac.can("training.submit"):
        return _err(
            "Chỉ Training Manager / Super Admin được tạm ngưng năng lực",
            ErrorCode.FORBIDDEN,
        )
    return _run(svc.suspend_competency, name, reason)


@frappe.whitelist(methods=["POST"])
def restore_competency(name: str) -> dict:
    """POST /api/method/assetcore.api.imm06.restore_competency

    CR-WF-06-COMP (parity revoke/recertify): Khôi phục năng lực Suspended → Active.
    Chỉ Training Manager / Super Admin (capability ``training.submit``) được phép.
    Thiếu quyền → FORBIDDEN, KHÔNG đổi workflow_state; nguồn ≠ Suspended → BAD_STATE.
    """
    from assetcore.services.shared import rbac
    if not rbac.can("training.submit"):
        return _err(
            "Chỉ Training Manager / Super Admin được khôi phục năng lực",
            ErrorCode.FORBIDDEN,
        )
    return _run(svc.restore_competency, name)


# ─── Group D: Dashboard & Analytics ──────────────────────────────────────────

@frappe.whitelist()
def get_dashboard_stats() -> dict:
    """GET /api/method/assetcore.api.imm06.get_dashboard_stats"""
    return _run(svc.get_dashboard_stats)


@frappe.whitelist()
def get_competency_gaps_by_dept() -> dict:
    """GET /api/method/assetcore.api.imm06.get_competency_gaps_by_dept"""
    return _run(svc.get_competency_gaps_by_dept)


@frappe.whitelist()
def get_expiring_competencies(days: int = 60) -> dict:
    """GET /api/method/assetcore.api.imm06.get_expiring_competencies"""
    return _run(svc.get_expiring_competencies, int(days))


# ─── Cross-module gate (used by IMM-04 service) ───────────────────────────────

@frappe.whitelist()
def check_user_authorization(user: str, asset_name: str) -> dict:
    """GET — check if user has Active competency for given asset's device model."""
    return _run(svc.validate_user_authorized_for_asset, user, asset_name)


@frappe.whitelist()
def get_asset_operator_coverage(asset: str) -> dict:
    """GET /api/method/assetcore.api.imm06.get_asset_operator_coverage

    Docs §C.3 — Coverage operator cho 1 asset (BE-06-02).
    Dùng bởi IMM-04 Clinical Release validate gate.
    """
    return _run(svc.get_asset_operator_coverage, asset)
