# Copyright (c) 2026, AssetCore Team
# IMM-16 Compliance Monitoring & CAPA — API Layer.
from __future__ import annotations

import json

import frappe

from assetcore.services import imm16 as svc
from assetcore.services.shared import ErrorCode, ServiceError
from assetcore.utils.helpers import _err, _ok


def _parse_json(raw, *, field_name: str, default=None):
    if not raw:
        return default if default is not None else {}
    if not isinstance(raw, str):
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


@frappe.whitelist()
def list_compliance_rules(filters: str = "{}", page: int = 1,
                           page_size: int = 20) -> dict:
    try:
        f = _parse_json(filters, field_name="filters")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.list_compliance_rules, f, page=int(page),
                   page_size=int(page_size))


@frappe.whitelist(methods=["POST"])
def create_compliance_rule(data: str = "{}") -> dict:
    try:
        d = _parse_json(data, field_name="data")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.create_compliance_rule, d)


@frappe.whitelist()
def list_compliance_findings(filters: str = "{}", page: int = 1,
                              page_size: int = 20) -> dict:
    try:
        f = _parse_json(filters, field_name="filters")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.list_compliance_findings, f, page=int(page),
                   page_size=int(page_size))


@frappe.whitelist(methods=["POST"])
def create_finding(rule_ref: str, asset_ref: str = "",
                   work_order_ref: str = "", severity: str = "Medium",
                   description: str = "",
                   evaluation_date: str = "") -> dict:
    return _handle(svc.create_finding, rule_ref, asset_ref, work_order_ref,
                   severity, description, evaluation_date)


@frappe.whitelist(methods=["POST"])
def close_finding(finding_name: str, capa_ref: str = "",
                  resolution_note: str = "") -> dict:
    return _handle(svc.close_finding, finding_name, capa_ref, resolution_note)


@frappe.whitelist()
def list_internal_audits(filters: str = "{}", page: int = 1,
                          page_size: int = 20) -> dict:
    try:
        f = _parse_json(filters, field_name="filters")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.list_internal_audits, f, page=int(page),
                   page_size=int(page_size))


@frappe.whitelist(methods=["POST"])
def create_internal_audit(data: str = "{}") -> dict:
    try:
        d = _parse_json(data, field_name="data")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.create_internal_audit, d)


@frappe.whitelist(methods=["POST"])
def submit_audit_findings(audit_name: str,
                           findings: str = "[]") -> dict:
    try:
        findings_list = _parse_json(findings, field_name="findings", default=[])
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.submit_audit_findings, audit_name, findings_list)


@frappe.whitelist(methods=["POST"])
def close_internal_audit(audit_name: str) -> dict:
    return _handle(svc.close_internal_audit, audit_name)


@frappe.whitelist(methods=["POST"])
def generate_scorecard(module_ref: str = "", period: str = "") -> dict:
    if not period:
        from frappe.utils import nowdate
        today = nowdate()
        period = today[:7]  # YYYY-MM
    return _handle(svc.generate_scorecard, module_ref, period)


@frappe.whitelist()
def check_asset_compliance(asset: str) -> dict:
    return _handle(svc.check_asset_compliance_status, asset)


@frappe.whitelist(methods=["POST"])
def run_compliance_evaluation() -> dict:
    try:
        svc.evaluate_all_compliance_rules()
        return _ok({"message": "Evaluation completed"})
    except Exception as exc:
        return _err(str(exc), ErrorCode.INTERNAL)
