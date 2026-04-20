# Copyright (c) 2026, AssetCore Team
"""IMM-12 — Incident & CAPA API endpoints.

Incident workflow: Open → Under Investigation → Resolved → Closed
CAPA endpoints: delegate to imm00 (create_capa, list_capa, get_capa, close_capa).

Base URL: /api/method/assetcore.api.imm12
"""
from __future__ import annotations

import frappe
from frappe import _

from assetcore.utils.response import _ok, _err
from assetcore.services.imm12 import (
    IncidentError,
    report_incident as svc_report,
    cancel_incident as svc_cancel,
    acknowledge_incident as svc_acknowledge,
    resolve_incident as svc_resolve,
    close_incident as svc_close,
    create_rca as svc_create_rca,
    get_rca as svc_get_rca,
    submit_rca as svc_submit_rca,
    list_incidents as svc_list,
    get_incident_detail as svc_get,
    get_incident_stats as svc_stats,
    get_asset_incident_history as svc_asset_history,
    get_chronic_failures as svc_chronic,
    get_dashboard as svc_dashboard,
)

_ROLES_INVESTIGATE = {"IMM Workshop Lead", "IMM Technician", "IMM QA Officer", "System Manager"}
_ROLES_CLOSE = {"IMM Workshop Lead", "IMM QA Officer", "System Manager"}

_MSG_UNAUTHENTICATED = "Chưa đăng nhập"
_MSG_SERVER_ERROR = "Lỗi server"
_MSG_FORBIDDEN = "Không có quyền thực hiện hành động này"


def _has_role(*roles: str) -> bool:
    user_roles = set(frappe.get_roles())
    return bool(user_roles & set(roles))


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
):
    """POST /api/method/assetcore.api.imm12.report_incident"""
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)
    try:
        return _ok(svc_report(
            asset=asset, incident_type=incident_type, severity=severity,
            description=description, fault_code=fault_code,
            workaround_applied=int(workaround_applied), clinical_impact=clinical_impact,
            patient_affected=int(patient_affected),
            patient_impact_description=patient_impact_description,
            immediate_action=immediate_action, linked_repair_wo=linked_repair_wo,
        ))
    except IncidentError as e:
        return _err(_(e.message), e.code)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-12 report_incident")
        return _err(_(_MSG_SERVER_ERROR), 500)


@frappe.whitelist(methods=["POST"])
def cancel_incident(name: str, reason: str):
    """POST /api/method/assetcore.api.imm12.cancel_incident"""
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)
    if not _has_role(*_ROLES_INVESTIGATE):
        return _err(_(_MSG_FORBIDDEN), 403)
    if not reason or not reason.strip():
        return _err(_("Bắt buộc nhập lý do hủy"), 422)
    try:
        return _ok(svc_cancel(name, reason=reason))
    except IncidentError as e:
        return _err(_(e.message), e.code)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-12 cancel_incident")
        return _err(_(_MSG_SERVER_ERROR), 500)


@frappe.whitelist(methods=["POST"])
def create_rca(incident_name: str, rca_method: str = "5-Why"):
    """POST /api/method/assetcore.api.imm12.create_rca"""
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)
    if not _has_role(*_ROLES_INVESTIGATE):
        return _err(_("Không có quyền tạo RCA"), 403)
    try:
        return _ok(svc_create_rca(incident_name, rca_method=rca_method))
    except IncidentError as e:
        return _err(_(e.message), e.code)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-12 create_rca")
        return _err(_(_MSG_SERVER_ERROR), 500)


@frappe.whitelist()
def get_rca(name: str):
    """GET /api/method/assetcore.api.imm12.get_rca"""
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)
    try:
        return _ok(svc_get_rca(name))
    except IncidentError as e:
        return _err(_(e.message), e.code)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-12 get_rca")
        return _err(_(_MSG_SERVER_ERROR), 500)


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
    if not _has_role(*_ROLES_INVESTIGATE):
        return _err(_("Không có quyền submit RCA"), 403)
    if not root_cause or not root_cause.strip():
        return _err(_("Bắt buộc nhập root_cause"), 422)
    if not corrective_action or not corrective_action.strip():
        return _err(_("Bắt buộc nhập corrective_action"), 422)
    try:
        import json
        steps = json.loads(five_why_steps) if isinstance(five_why_steps, str) else five_why_steps
    except Exception:
        steps = []
    try:
        return _ok(svc_submit_rca(
            name, root_cause=root_cause, corrective_action=corrective_action,
            preventive_action=preventive_action, five_why_steps=steps, rca_notes=rca_notes,
        ))
    except IncidentError as e:
        return _err(_(e.message), e.code)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-12 submit_rca")
        return _err(_(_MSG_SERVER_ERROR), 500)


@frappe.whitelist()
def get_asset_incident_history(asset: str, limit: int = 10):
    """GET /api/method/assetcore.api.imm12.get_asset_incident_history"""
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)
    try:
        return _ok(svc_asset_history(asset, limit=int(limit)))
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-12 get_asset_incident_history")
        return _err(_(_MSG_SERVER_ERROR), 500)


@frappe.whitelist()
def get_chronic_failures():
    """GET /api/method/assetcore.api.imm12.get_chronic_failures"""
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)
    try:
        return _ok(svc_chronic())
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-12 get_chronic_failures")
        return _err(_(_MSG_SERVER_ERROR), 500)


@frappe.whitelist()
def get_dashboard():
    """GET /api/method/assetcore.api.imm12.get_dashboard"""
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)
    try:
        return _ok(svc_dashboard())
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-12 get_dashboard")
        return _err(_(_MSG_SERVER_ERROR), 500)


@frappe.whitelist()
def list_incidents(
    status: str = "",
    severity: str = "",
    asset: str = "",
    page: int = 1,
    page_size: int = 20,
):
    """GET /api/method/assetcore.api.imm12.list_incidents"""
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)
    try:
        result = svc_list(
            status=status, severity=severity, asset=asset,
            page=int(page), page_size=int(page_size),
        )
        return _ok(result)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-12 list_incidents")
        return _err(_("Lỗi khi lấy danh sách incident"), 500)


@frappe.whitelist()
def get_incident(name: str):
    """GET /api/method/assetcore.api.imm12.get_incident"""
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)
    try:
        return _ok(svc_get(name))
    except IncidentError as e:
        return _err(_(e.message), e.code)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-12 get_incident")
        return _err(_(_MSG_SERVER_ERROR), 500)


@frappe.whitelist(methods=["POST"])
def acknowledge_incident(name: str, notes: str = "", assigned_to: str = ""):
    """POST /api/method/assetcore.api.imm12.acknowledge_incident
    Open → Under Investigation.
    """
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)
    if not _has_role(*_ROLES_INVESTIGATE):
        return _err(_(_MSG_FORBIDDEN), 403)
    try:
        return _ok(svc_acknowledge(name, notes=notes, assigned_to=assigned_to))
    except IncidentError as e:
        return _err(_(e.message), e.code)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-12 acknowledge_incident")
        return _err(_(_MSG_SERVER_ERROR), 500)


@frappe.whitelist(methods=["POST"])
def resolve_incident(name: str, resolution_notes: str, root_cause: str = ""):
    """POST /api/method/assetcore.api.imm12.resolve_incident
    Under Investigation → Resolved. Auto-creates CAPA if High/Critical.
    """
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)
    if not _has_role(*_ROLES_INVESTIGATE):
        return _err(_(_MSG_FORBIDDEN), 403)
    if not resolution_notes or not resolution_notes.strip():
        return _err(_("Bắt buộc nhập ghi chú giải quyết"), 422)
    try:
        return _ok(svc_resolve(name, resolution_notes=resolution_notes, root_cause=root_cause))
    except IncidentError as e:
        return _err(_(e.message), e.code)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-12 resolve_incident")
        return _err(_(_MSG_SERVER_ERROR), 500)


@frappe.whitelist(methods=["POST"])
def close_incident(name: str, verification_notes: str = ""):
    """POST /api/method/assetcore.api.imm12.close_incident
    Resolved → Closed. Requires Workshop Lead or QA Officer.
    """
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)
    if not _has_role(*_ROLES_CLOSE):
        return _err(_("Không có quyền đóng Incident (cần Workshop Lead hoặc QA Officer)"), 403)
    try:
        return _ok(svc_close(name, verification_notes=verification_notes))
    except IncidentError as e:
        return _err(_(e.message), e.code)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-12 close_incident")
        return _err(_(_MSG_SERVER_ERROR), 500)


@frappe.whitelist()
def get_incident_stats():
    """GET /api/method/assetcore.api.imm12.get_incident_stats — KPI tổng quan."""
    if frappe.session.user == "Guest":
        return _err(_(_MSG_UNAUTHENTICATED), 401)
    try:
        def _count(filters: dict) -> int:
            try:
                return frappe.db.count("Incident Report", filters=filters)
            except Exception:
                return 0

        return _ok({
            "open": _count({"status": "Open"}),
            "investigating": _count({"status": "Under Investigation"}),
            "resolved": _count({"status": "Resolved"}),
            "closed": _count({"status": "Closed"}),
            "critical_open": _count({"status": ["in", ["Open", "Under Investigation"]], "severity": "Critical"}),
            "high_open": _count({"status": ["in", ["Open", "Under Investigation"]], "severity": "High"}),
        })
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-12 get_incident_stats")
        return _err(_(_MSG_SERVER_ERROR), 500)
