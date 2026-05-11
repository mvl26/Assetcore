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


@frappe.whitelist(methods=["POST"])
def signoff_competency(name: str) -> dict:
    """POST /api/method/assetcore.api.imm06.signoff_competency"""
    return _run(svc.signoff_competency_by_name, name)


@frappe.whitelist(methods=["POST"])
def revoke_competency(name: str, reason: str, capa_ref: str = "") -> dict:
    """POST /api/method/assetcore.api.imm06.revoke_competency"""
    return _run(svc.revoke_competency_with_capa, name, reason, capa_ref)


@frappe.whitelist(methods=["POST"])
def recertify_competency(name: str, new_session: str) -> dict:
    """POST /api/method/assetcore.api.imm06.recertify_competency"""
    return _run(svc.recertify_competency, name, new_session)


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
