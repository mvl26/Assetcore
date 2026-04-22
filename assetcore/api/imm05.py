# Copyright (c) 2026, AssetCore Team
# REST API cho Module IMM-05 — Asset Document Repository.
# Tier 1 — parse HTTP input → gọi services.imm05 → _ok / _err envelope.

from __future__ import annotations

import json

import frappe

from assetcore.services import imm05 as svc
from assetcore.services.shared import ErrorCode, ServiceError
from assetcore.utils.helpers import _err, _ok


def _parse_json(raw: str | dict | None, *, field_name: str) -> dict:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except (ValueError, TypeError) as e:
        raise ServiceError(ErrorCode.INVALID_PARAMS,
                           f"{field_name} không phải JSON hợp lệ") from e


def _handle(fn, *args, **kwargs) -> dict:
    try:
        return _ok(fn(*args, **kwargs))
    except ServiceError as e:
        return _err(e.message, e.code)


# ─── Documents ───────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_documents(filters: str = "{}", page: int = 1, page_size: int = 20) -> dict:
    try:
        f = _parse_json(filters, field_name="filters")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.list_documents, f, page=int(page), page_size=int(page_size))


@frappe.whitelist()
def get_document(name: str) -> dict:
    return _handle(svc.get_document, name)


@frappe.whitelist()
def create_document(doc_data: str = "{}") -> dict:
    try:
        data = _parse_json(doc_data, field_name="doc_data")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.create_document, data)


@frappe.whitelist()
def update_document(name: str, doc_data: str = "{}") -> dict:
    try:
        data = _parse_json(doc_data, field_name="doc_data")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.update_document, name, data)


@frappe.whitelist()
def approve_document(name: str) -> dict:
    return _handle(svc.approve_document, name)


@frappe.whitelist()
def reject_document(name: str, rejection_reason: str = "") -> dict:
    return _handle(svc.reject_document, name, rejection_reason)


# ─── Asset-centric ────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_asset_documents(asset: str) -> dict:
    return _handle(svc.get_asset_documents, asset)


# ─── Dashboards ───────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_dashboard_stats() -> dict:
    return _handle(svc.get_dashboard_stats)


@frappe.whitelist()
def get_expiring_documents(days: int = 90) -> dict:
    return _handle(svc.get_expiring_documents, int(days))


@frappe.whitelist()
def get_compliance_by_dept() -> dict:
    return _handle(svc.get_compliance_by_dept)


# ─── History ──────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_document_history(name: str) -> dict:
    return _handle(svc.get_document_history, name)


# ─── Document Requests ────────────────────────────────────────────────────────

@frappe.whitelist()
def create_document_request(
    asset_ref: str,
    doc_type_required: str,
    doc_category: str = "Legal",
    assigned_to: str = "",
    due_date: str = "",
    priority: str = "Medium",
    request_note: str = "",
    source_type: str = "Manual",
) -> dict:
    return _handle(
        svc.create_document_request,
        asset_ref=asset_ref, doc_type_required=doc_type_required,
        doc_category=doc_category, assigned_to=assigned_to or None,
        due_date=due_date or None, priority=priority,
        request_note=request_note, source_type=source_type,
    )


@frappe.whitelist()
def get_document_requests(asset_ref: str = "", status: str = "") -> dict:
    return _handle(svc.get_document_requests, asset_ref, status)


# ─── Exempt ───────────────────────────────────────────────────────────────────

@frappe.whitelist()
def mark_exempt(asset_ref: str, doc_type_detail: str,
                exempt_reason: str, exempt_proof: str) -> dict:
    return _handle(
        svc.mark_exempt,
        asset_ref=asset_ref, doc_type_detail=doc_type_detail,
        exempt_reason=exempt_reason, exempt_proof=exempt_proof,
    )
