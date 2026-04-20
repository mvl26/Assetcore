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
    acknowledge_incident as svc_acknowledge,
    resolve_incident as svc_resolve,
    close_incident as svc_close,
    list_incidents as svc_list,
    get_incident_detail as svc_get,
)

_ROLES_INVESTIGATE = {"IMM Workshop Lead", "IMM Technician", "IMM QA Officer", "System Manager"}
_ROLES_CLOSE = {"IMM Workshop Lead", "IMM QA Officer", "System Manager"}


def _has_role(*roles: str) -> bool:
    user_roles = set(frappe.get_roles())
    return bool(user_roles & set(roles))


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
        return _err(_("Chưa đăng nhập"), 401)
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
        return _err(_("Chưa đăng nhập"), 401)
    try:
        return _ok(svc_get(name))
    except IncidentError as e:
        return _err(_(e.message), e.code)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-12 get_incident")
        return _err(_("Lỗi server"), 500)


@frappe.whitelist(methods=["POST"])
def acknowledge_incident(name: str, notes: str = "", assigned_to: str = ""):
    """POST /api/method/assetcore.api.imm12.acknowledge_incident
    Open → Under Investigation.
    """
    if frappe.session.user == "Guest":
        return _err(_("Chưa đăng nhập"), 401)
    if not _has_role(*_ROLES_INVESTIGATE):
        return _err(_("Không có quyền thực hiện hành động này"), 403)
    try:
        return _ok(svc_acknowledge(name, notes=notes, assigned_to=assigned_to))
    except IncidentError as e:
        return _err(_(e.message), e.code)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-12 acknowledge_incident")
        return _err(_("Lỗi server"), 500)


@frappe.whitelist(methods=["POST"])
def resolve_incident(name: str, resolution_notes: str, root_cause: str = ""):
    """POST /api/method/assetcore.api.imm12.resolve_incident
    Under Investigation → Resolved. Auto-creates CAPA if High/Critical.
    """
    if frappe.session.user == "Guest":
        return _err(_("Chưa đăng nhập"), 401)
    if not _has_role(*_ROLES_INVESTIGATE):
        return _err(_("Không có quyền thực hiện hành động này"), 403)
    if not resolution_notes or not resolution_notes.strip():
        return _err(_("Bắt buộc nhập ghi chú giải quyết"), 422)
    try:
        return _ok(svc_resolve(name, resolution_notes=resolution_notes, root_cause=root_cause))
    except IncidentError as e:
        return _err(_(e.message), e.code)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-12 resolve_incident")
        return _err(_("Lỗi server"), 500)


@frappe.whitelist(methods=["POST"])
def close_incident(name: str, verification_notes: str = ""):
    """POST /api/method/assetcore.api.imm12.close_incident
    Resolved → Closed. Requires Workshop Lead or QA Officer.
    """
    if frappe.session.user == "Guest":
        return _err(_("Chưa đăng nhập"), 401)
    if not _has_role(*_ROLES_CLOSE):
        return _err(_("Không có quyền đóng Incident (cần Workshop Lead hoặc QA Officer)"), 403)
    try:
        return _ok(svc_close(name, verification_notes=verification_notes))
    except IncidentError as e:
        return _err(_(e.message), e.code)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-12 close_incident")
        return _err(_("Lỗi server"), 500)


@frappe.whitelist()
def get_incident_stats():
    """GET /api/method/assetcore.api.imm12.get_incident_stats — KPI tổng quan."""
    if frappe.session.user == "Guest":
        return _err(_("Chưa đăng nhập"), 401)
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
        return _err(_("Lỗi server"), 500)
