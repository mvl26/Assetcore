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
                   description: str = "", evaluation_date: str = "",
                   actual_value: str = "", threshold_value: str = "") -> dict:
    return _handle(svc.create_finding, rule_ref, asset_ref, work_order_ref,
                   severity, description, evaluation_date, actual_value, threshold_value)


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
    """DEPRECATED legacy alias — kept as a thin shim for backward-compat only.

    Canonical compliance-gate endpoint is ``check_asset_compliance_status``
    (the path FE client `imm16.ts` targets, mirrors `svc.check_asset_compliance_status`).
    This shim delegates to the canonical API fn so there is exactly ONE def that
    delegates to ``svc.check_asset_compliance_status`` (the gate SoT). Do NOT add
    new callers — use ``check_asset_compliance_status`` directly.
    """
    return check_asset_compliance_status(asset)


@frappe.whitelist(methods=["POST"])
def run_compliance_evaluation() -> dict:
    try:
        svc.evaluate_all_compliance_rules()
        return _ok({"message": "Evaluation completed"})
    except Exception as exc:
        return _err(str(exc), ErrorCode.INTERNAL)


# ════════════════════════════════════════════════════════════════════════════
# Canonical IMM-16 endpoints (docs/imm-16/05_API_Specification.md)
# ════════════════════════════════════════════════════════════════════════════

# ─── Rule ─────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_rules(filters: str = "{}", page: int = 1, page_size: int = 20) -> dict:
    return list_compliance_rules(filters=filters, page=page, page_size=page_size)


@frappe.whitelist()
def get_rule(name: str) -> dict:
    return _handle(svc.get_rule, name)


@frappe.whitelist(methods=["POST"])
def create_rule(rule_data: str = "{}") -> dict:
    try:
        d = _parse_json(rule_data, field_name="rule_data")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.create_compliance_rule, d)


@frappe.whitelist(methods=["POST"])
def update_rule(name: str, rule_data: str = "{}",
                change_summary: str = "") -> dict:
    try:
        d = _parse_json(rule_data, field_name="rule_data")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.update_rule, name, d, change_summary)


@frappe.whitelist(methods=["POST"])
def deactivate_rule(name: str) -> dict:
    return _handle(svc.deactivate_rule, name)


@frappe.whitelist(methods=["POST"])
def reactivate_rule(name: str) -> dict:
    return _handle(svc.reactivate_rule, name)


@frappe.whitelist()
def get_record_history(ref_doctype: str, ref_name: str,
                       limit: int = 50) -> dict:
    return _handle(svc.get_record_history, ref_doctype, ref_name,
                   int(limit))


# ─── Finding ──────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_findings(filters: str = "{}", page: int = 1, page_size: int = 20) -> dict:
    return list_compliance_findings(filters=filters, page=page, page_size=page_size)


@frappe.whitelist()
def get_finding(name: str) -> dict:
    return _handle(svc.get_finding, name)


@frappe.whitelist(methods=["POST"])
def start_review(name: str, reviewer_note: str = "") -> dict:
    """CR-WF-16-FIND (round 14): Open → Under Review ("Bắt đầu xem xét")."""
    return _handle(svc.start_review, name, reviewer_note)


@frappe.whitelist(methods=["POST"])
def confirm_finding(name: str, reviewer_note: str = "") -> dict:
    return _handle(svc.confirm_finding, name, reviewer_note)


@frappe.whitelist(methods=["POST"])
def mark_false_positive(name: str, reason: str) -> dict:
    return _handle(svc.mark_false_positive, name, reason)


@frappe.whitelist(methods=["POST"])
def waive_finding(name: str, waiver_reason: str,
                  waiver_evidence: str = "",
                  waiver_expiry: str = "") -> dict:
    return _handle(svc.waive_finding, name, waiver_reason,
                   waiver_evidence, waiver_expiry)


@frappe.whitelist(methods=["POST"])
def link_to_capa(name: str, capa_ref: str) -> dict:
    return _handle(svc.link_finding_to_capa, name, capa_ref)


# ─── Audit ────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_audits(filters: str = "{}", page: int = 1, page_size: int = 20) -> dict:
    return list_internal_audits(filters=filters, page=page, page_size=page_size)


@frappe.whitelist()
def get_audit(name: str) -> dict:
    return _handle(svc.get_audit, name)


@frappe.whitelist(methods=["POST"])
def create_audit(audit_data: str = "{}") -> dict:
    try:
        d = _parse_json(audit_data, field_name="audit_data")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.create_audit, d)


@frappe.whitelist(methods=["POST"])
def start_audit(name: str) -> dict:
    return _handle(svc.start_audit, name)


@frappe.whitelist(methods=["POST"])
def complete_audit_checklist(audit_name: str, items: str = "[]") -> dict:
    try:
        items_list = _parse_json(items, field_name="items", default=[])
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.complete_audit_checklist, audit_name, items_list)


@frappe.whitelist(methods=["POST"])
def close_audit(name: str, audit_report: str = "") -> dict:
    return _handle(svc.close_audit, name, audit_report)


# ─── CAPA ─────────────────────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def create_capa_from_finding(finding_name: str,
                              imm_risk_level: str = "Medium",
                              imm_root_cause_method: str = "",
                              responsible: str = "",
                              due_date: str = "") -> dict:
    return _handle(svc.create_capa_from_finding, finding_name,
                   imm_risk_level, imm_root_cause_method,
                   responsible, due_date)


@frappe.whitelist()
def get_capa(name: str) -> dict:
    return _handle(svc.get_capa, name)


@frappe.whitelist(methods=["POST"])
def update_capa_fields(name: str, data: str = "{}") -> dict:
    try:
        d = _parse_json(data, field_name="data")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.update_capa_fields, name, d)


@frappe.whitelist(methods=["POST"])
def advance_capa_state(name: str, target_state: str,
                       payload: str = "{}") -> dict:
    try:
        p = _parse_json(payload, field_name="payload")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.advance_capa_state, name, target_state, p)


@frappe.whitelist(methods=["POST"])
def perform_effectiveness_check(name: str, result: str,
                                 effectiveness_evidence: str = "") -> dict:
    return _handle(svc.perform_effectiveness_check, name, result,
                   effectiveness_evidence)


@frappe.whitelist(methods=["POST"])
def reopen_capa(name: str, reason: str = "") -> dict:
    return _handle(svc.reopen_capa, name, reason)


# ─── Scorecard ────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_scorecards(filters: str = "{}", page: int = 1,
                    page_size: int = 20) -> dict:
    try:
        f = _parse_json(filters, field_name="filters")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.list_scorecards, f, page=int(page),
                   page_size=int(page_size))


@frappe.whitelist()
def get_current_scorecard(scope: str = "Hospital") -> dict:
    return _handle(svc.get_current_scorecard, scope)


@frappe.whitelist()
def get_scorecard_by_period(year: int, month: int,
                             scope: str = "Hospital") -> dict:
    return _handle(svc.get_scorecard_by_period, int(year), int(month), scope)


@frappe.whitelist(methods=["POST"])
def publish_scorecard(name: str) -> dict:
    return _handle(svc.publish_scorecard, name)


# ─── Management Review ────────────────────────────────────────────────────────

@frappe.whitelist()
def list_management_reviews(filters: str = "{}", page: int = 1,
                             page_size: int = 20) -> dict:
    try:
        f = _parse_json(filters, field_name="filters")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.list_management_reviews, f, page=int(page),
                   page_size=int(page_size))


@frappe.whitelist()
def get_management_review(name: str) -> dict:
    return _handle(svc.get_management_review, name)


@frappe.whitelist(methods=["POST"])
def create_management_review(data: str = "{}") -> dict:
    try:
        d = _parse_json(data, field_name="data")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.create_management_review, d)


@frappe.whitelist(methods=["POST"])
def update_management_review(name: str, data: str = "{}") -> dict:
    try:
        d = _parse_json(data, field_name="data")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.update_management_review, name, d)


@frappe.whitelist(methods=["POST"])
def advance_mr_state(name: str, target_state: str) -> dict:
    return _handle(svc.advance_mr_state, name, target_state)


@frappe.whitelist(methods=["POST"])
def finalize_management_review(name: str, minutes_doc: str = "",
                                output_actions: str = "[]") -> dict:
    try:
        actions = _parse_json(output_actions,
                              field_name="output_actions", default=[])
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.finalize_management_review, name, minutes_doc, actions)


# ─── Dashboard / Reports ──────────────────────────────────────────────────────

@frappe.whitelist()
def get_dashboard_stats() -> dict:
    return _handle(svc.get_dashboard_stats)


@frappe.whitelist()
def get_compliance_heatmap(period_year: int = 0,
                            period_month: int = 0) -> dict:
    # D-PRECOND OpenAPI: param đổi union-optional sang `int=0`. `0` (falsy) ≡ None-cũ
    # → `py/pm=None` (không lọc theo kỳ) — hành vi bất biến (year/month 0 không hợp lệ).
    py = int(period_year) if period_year else None
    pm = int(period_month) if period_month else None
    return _handle(svc.get_compliance_heatmap, py, pm)


@frappe.whitelist()
def get_capa_aging() -> dict:
    return _handle(svc.get_capa_aging)


@frappe.whitelist()
def get_overdue_actions() -> dict:
    return _handle(svc.get_overdue_actions)


# ─── Cross-module gate ────────────────────────────────────────────────────────

@frappe.whitelist()
def check_asset_compliance_status(asset: str) -> dict:
    return _handle(svc.check_asset_compliance_status, asset)
