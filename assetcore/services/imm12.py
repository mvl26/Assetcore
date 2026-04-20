# Copyright (c) 2026, AssetCore Team
"""IMM-12 — Incident & CAPA orchestration service.

Thin orchestration layer: delegates audit + lifecycle to imm00 services.
All state transitions enforce the Incident Report status machine:
  Open → Under Investigation → Resolved → Closed

No direct DocType logic here — callers (api/imm12.py) pass validated inputs.
"""
from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime, today

from assetcore.services import imm00 as svc00

_DT_INCIDENT = "Incident Report"
_DT_CAPA = "IMM CAPA Record"
_DT_ASSET = "AC Asset"

_STATUS_OPEN = "Open"
_STATUS_INVESTIGATING = "Under Investigation"
_STATUS_RESOLVED = "Resolved"
_STATUS_CLOSED = "Closed"

_HIGH_SEVERITY = ("High", "Critical")
_ASSET_OUT_OF_SERVICE = "Out of Service"
_ASSET_ACTIVE = "Active"

_VALID_TRANSITIONS: dict[str, list[str]] = {
    _STATUS_OPEN: [_STATUS_INVESTIGATING],
    _STATUS_INVESTIGATING: [_STATUS_RESOLVED],
    _STATUS_RESOLVED: [_STATUS_CLOSED],
}


class IncidentError(Exception):
    def __init__(self, message: str, code: int = 422) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def _get_incident(name: str) -> "frappe.Document":
    if not frappe.db.exists(_DT_INCIDENT, name):
        raise IncidentError(_("Không tìm thấy Incident Report: {0}").format(name), 404)
    return frappe.get_doc(_DT_INCIDENT, name)


def _assert_transition(doc: "frappe.Document", to_status: str) -> None:
    allowed = _VALID_TRANSITIONS.get(doc.status, [])
    if to_status not in allowed:
        raise IncidentError(
            _("Không thể chuyển từ '{0}' sang '{1}'").format(doc.status, to_status), 409,
        )


def _log(name: str, asset: str, summary: str, from_status: str, to_status: str) -> None:
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


def acknowledge_incident(name: str, notes: str = "", assigned_to: str = "") -> dict:
    """Open → Under Investigation. Ghi nhận người phụ trách và bắt đầu điều tra."""
    doc = _get_incident(name)
    _assert_transition(doc, _STATUS_INVESTIGATING)

    prev = doc.status
    doc.status = _STATUS_INVESTIGATING
    if notes:
        doc.immediate_action = (doc.immediate_action or "") + f"\n[Acknowledged] {notes}"
    if assigned_to:
        doc.resolution_notes = (doc.resolution_notes or "") + f"\nAssigned to: {assigned_to}"
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()

    _log(name, doc.asset, f"Incident acknowledged — {notes or 'đang điều tra'}", prev, _STATUS_INVESTIGATING)

    if doc.asset and doc.severity in _HIGH_SEVERITY:
        cur = frappe.db.get_value(_DT_ASSET, doc.asset, "lifecycle_status")
        if cur and cur not in (_ASSET_OUT_OF_SERVICE, "Decommissioned"):
            svc00.transition_asset_status(
                asset_name=doc.asset, to_status=_ASSET_OUT_OF_SERVICE,
                actor=frappe.session.user,
                root_doctype=_DT_INCIDENT, root_record=name,
                reason=f"Incident {doc.severity} — {name}",
            )

    return {"name": name, "status": doc.status}


def resolve_incident(name: str, resolution_notes: str, root_cause: str = "") -> dict:
    """Under Investigation → Resolved. Ghi nhận kết quả xử lý và nguyên nhân."""
    doc = _get_incident(name)
    _assert_transition(doc, _STATUS_RESOLVED)

    if not resolution_notes.strip():
        raise IncidentError(_("Bắt buộc nhập ghi chú giải quyết (resolution_notes)."), 422)

    prev = doc.status
    doc.status = _STATUS_RESOLVED
    doc.resolution_notes = resolution_notes
    if root_cause:
        doc.root_cause_summary = root_cause
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()

    _log(name, doc.asset, f"Incident resolved — {resolution_notes[:120]}", prev, _STATUS_RESOLVED)

    if doc.severity in ("High", "Critical") and not doc.linked_capa:
        _auto_create_capa(doc)

    return {"name": name, "status": doc.status, "linked_capa": doc.linked_capa}


def close_incident(name: str, verification_notes: str = "") -> dict:
    """Resolved → Closed. Xác nhận xử lý hoàn tất."""
    doc = _get_incident(name)
    _assert_transition(doc, _STATUS_CLOSED)

    prev = doc.status
    doc.status = _STATUS_CLOSED
    doc.closed_date = today()
    if verification_notes:
        doc.resolution_notes = (doc.resolution_notes or "") + f"\n[Closed] {verification_notes}"
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()

    _log(name, doc.asset, f"Incident closed — {verification_notes or 'verified'}", prev, _STATUS_CLOSED)

    if doc.asset:
        cur = frappe.db.get_value(_DT_ASSET, doc.asset, "lifecycle_status")
        if cur == _ASSET_OUT_OF_SERVICE:
            svc00.transition_asset_status(
                asset_name=doc.asset, to_status=_ASSET_ACTIVE,
                actor=frappe.session.user,
                root_doctype=_DT_INCIDENT, root_record=name,
                reason=f"Incident {name} closed — verified",
            )

    return {"name": name, "status": doc.status, "closed_date": doc.closed_date}


def _auto_create_capa(doc: "frappe.Document") -> None:
    """Tự động tạo CAPA cho Incident có mức độ High/Critical khi Resolved."""
    try:
        capa_name = svc00.create_capa(
            asset=doc.asset,
            source_type=_DT_INCIDENT,
            source_ref=doc.name,
            severity=_map_severity(doc.severity),
            description=f"Auto-CAPA từ Incident {doc.name}: {doc.description or ''}",
            responsible=frappe.session.user,
        )
        frappe.db.set_value(_DT_INCIDENT, doc.name, "linked_capa", capa_name)
        frappe.db.commit()
        doc.linked_capa = capa_name
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-12 auto_create_capa")


def _map_severity(severity: str) -> str:
    return {"Low": "Minor", "Medium": "Minor", "High": "Major", "Critical": "Critical"}.get(severity, "Minor")


def list_incidents(
    status: str = "",
    severity: str = "",
    asset: str = "",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Danh sách Incident Reports với filter + pagination."""
    filters: dict = {}
    if status:
        filters["status"] = status
    if severity:
        filters["severity"] = severity
    if asset:
        filters["asset"] = asset

    total = frappe.db.count(_DT_INCIDENT, filters=filters)
    offset = (page - 1) * page_size
    rows = frappe.get_all(
        _DT_INCIDENT,
        filters=filters,
        fields=["name", "asset", "incident_type", "severity", "status",
                "reported_by", "reported_at", "description", "linked_capa", "linked_repair_wo",
                "patient_affected", "closed_date"],
        order_by="reported_at desc",
        limit_start=offset,
        limit_page_length=page_size,
    )
    return {
        "pagination": {"total": total, "page": page, "page_size": page_size,
                       "total_pages": max(1, -(-total // page_size)), "offset": offset},
        "items": rows,
    }


def get_incident_detail(name: str) -> dict:
    """Chi tiết một Incident Report."""
    doc = _get_incident(name)
    data = doc.as_dict()
    asset_name = frappe.db.get_value("AC Asset", doc.asset, "asset_name") if doc.asset else None
    if asset_name:
        data["asset_name"] = asset_name
    data["allowed_transitions"] = _VALID_TRANSITIONS.get(doc.status, [])
    return data
