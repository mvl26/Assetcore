# Copyright (c) 2026, AssetCore Team
"""IMM-02 REST API — Wave 2.

Tier 1 — parse HTTP input → gọi services.imm02 → _ok / _err envelope.
"""
from __future__ import annotations

import json

import frappe
from frappe import _

from assetcore.services import imm02 as svc
from assetcore.services.shared import ErrorCode, ServiceError
from assetcore.utils.helpers import _ok, _err

_DT_TS = "IMM Tech Spec"
_DT_MB = "IMM Market Benchmark"
_DT_LR = "IMM Lock-in Risk Assessment"


def _parse_json(raw, *, default=None):
    if not raw: return default if default is not None else {}
    if not isinstance(raw, str): return raw
    try: return json.loads(raw)
    except (ValueError, TypeError) as e:
        raise ServiceError(ErrorCode.INVALID_PARAMS, f"JSON không hợp lệ: {e}")


def _handle(fn, *args, **kwargs) -> dict:
    try:
        return _ok(fn(*args, **kwargs))
    except ServiceError as e:
        return _err(e.message, e.code)
    except frappe.DoesNotExistError as e:
        return _err(str(e), ErrorCode.NOT_FOUND)
    except frappe.PermissionError as e:
        return _err(str(e), ErrorCode.FORBIDDEN)
    except frappe.ValidationError as e:
        return _err(str(e), ErrorCode.VALIDATION)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"IMM-02 {fn.__name__}")
        return _err(str(e), ErrorCode.INTERNAL)


# ─── Tech Spec ────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_tech_specs(filters: str = "{}", page: int = 1, page_size: int = 20) -> dict:
    return _handle(_list_tech_specs, filters, int(page), int(page_size))


def _list_tech_specs(filters: str, page: int, page_size: int) -> dict:
    f = _parse_json(filters)
    fields = ["name", "device_model_ref", "version", "candidate_count",
              "lock_in_score", "workflow_state", "source_plan", "source_needs_request",
              "draft_date", "total_mandatory"]
    page_size = max(1, min(page_size, 100))
    start = (max(1, page) - 1) * page_size
    items = frappe.get_list(_DT_TS, filters=f or None, fields=fields,
                             order_by="draft_date desc", start=start, page_length=page_size)
    return {"items": items, "total": frappe.db.count(_DT_TS, filters=f or None),
            "page": page, "page_size": page_size}


@frappe.whitelist()
def get_tech_spec(name: str) -> dict:
    return _handle(lambda n: frappe.get_doc(_DT_TS, n).as_dict(), name)


@frappe.whitelist(methods=["POST"])
def create_tech_spec(payload: str = "{}") -> dict:
    return _handle(_create_tech_spec, payload)


def _create_tech_spec(payload: str) -> dict:
    data = _parse_json(payload)
    if not data:
        raise ServiceError(ErrorCode.INVALID_PARAMS, _("payload trống"))
    doc = frappe.new_doc(_DT_TS)
    for k, v in data.items():
        if k in ("requirements", "documents", "infra_compat"):
            for row in v or []:
                doc.append(k, row)
        else:
            setattr(doc, k, v)
    doc.insert()
    return {"name": doc.name, "workflow_state": doc.workflow_state, "version": doc.version}


@frappe.whitelist(methods=["POST"])
def draft_from_plan(plan: str, plan_lines: str = "[]") -> dict:
    return _handle(_draft_from_plan, plan, plan_lines)


def _draft_from_plan(plan: str, plan_lines: str) -> dict:
    """Tạo Tech Spec drafts từ plan_items — 1 spec / NR."""
    line_names = _parse_json(plan_lines, default=[])
    pp = frappe.get_doc("IMM Procurement Plan", plan)
    created = []
    for it in pp.plan_items or []:
        if line_names and it.name not in line_names:
            continue
        # Tránh tạo trùng
        if frappe.db.exists(_DT_TS, {"source_needs_request": it.needs_request, "docstatus": ["<", 2]}):
            continue
        nr = frappe.get_doc("IMM Needs Request", it.needs_request)
        ts = frappe.new_doc(_DT_TS)
        ts.source_plan          = plan
        ts.source_plan_line     = it.name
        ts.source_needs_request = nr.name
        ts.device_model_ref     = nr.device_model_ref
        ts.quantity             = nr.quantity
        ts.draft_date           = frappe.utils.today()
        ts.version              = "1.0"
        ts.insert(ignore_permissions=True)
        created.append(ts.name)
    return {"created": created}


@frappe.whitelist(methods=["POST"])
def update_tech_spec(name: str, payload: str = "{}") -> dict:
    return _handle(_update_tech_spec, name, payload)


def _update_tech_spec(name: str, payload: str) -> dict:
    data = _parse_json(payload)
    doc = frappe.get_doc(_DT_TS, name)
    if doc.docstatus != 0:
        raise ServiceError(ErrorCode.BAD_STATE, _("Spec đã submit/cancel — không sửa được"))
    for k, v in data.items():
        if k in ("requirements", "documents", "infra_compat"):
            doc.set(k, [])
            for row in v or []:
                doc.append(k, row)
        else:
            setattr(doc, k, v)
    doc.save()
    return {"name": doc.name, "workflow_state": doc.workflow_state}


@frappe.whitelist(methods=["POST"])
def transition_workflow(name: str, action: str) -> dict:
    """Áp dụng 1 workflow transition lên Tech Spec."""
    return _handle(_transition_workflow, name, action)


def _transition_workflow(name: str, action: str) -> dict:
    from frappe.model.workflow import apply_workflow
    apply_workflow(frappe.get_doc(_DT_TS, name), action)
    doc = frappe.get_doc(_DT_TS, name)
    return {"name": doc.name, "workflow_state": doc.workflow_state, "docstatus": doc.docstatus}


@frappe.whitelist()
def get_market_benchmark(name: str) -> dict:
    return _handle(lambda n: frappe.get_doc(_DT_MB, n).as_dict(), name)


@frappe.whitelist()
def get_lock_in_assessment(name: str) -> dict:
    return _handle(lambda n: frappe.get_doc(_DT_LR, n).as_dict(), name)


@frappe.whitelist(methods=["POST"])
def lock_spec(name: str, approver: str, remarks: str = "") -> dict:
    return _handle(_lock_spec, name, approver, remarks)


def _lock_spec(name: str, approver: str, remarks: str) -> dict:
    doc = frappe.get_doc(_DT_TS, name)
    if doc.workflow_state != "Pending Approval":
        raise ServiceError(
            ErrorCode.BAD_STATE,
            _("Chỉ spec ở 'Pending Approval' mới Lock được (hiện: {0})")
            .format(doc.workflow_state),
        )
    doc.approver = approver
    doc.workflow_state = "Locked"
    doc.submit()
    return {"name": doc.name, "workflow_state": "Locked"}


@frappe.whitelist(methods=["POST"])
def withdraw_spec(name: str, withdrawal_reason: str) -> dict:
    return _handle(_withdraw_spec, name, withdrawal_reason)


def _withdraw_spec(name: str, withdrawal_reason: str) -> dict:
    if not (withdrawal_reason or "").strip():
        raise ServiceError(ErrorCode.VALIDATION, _("Phải nhập withdrawal_reason"))
    doc = frappe.get_doc(_DT_TS, name)
    if doc.workflow_state not in ("Pending Approval", "Locked"):
        raise ServiceError(
            ErrorCode.BAD_STATE,
            _("Chỉ Pending Approval / Locked mới withdraw được (hiện: {0})")
            .format(doc.workflow_state),
        )
    doc.withdrawal_reason = withdrawal_reason
    doc.workflow_state = "Withdrawn"
    if doc.docstatus == 0:
        doc.submit()
    return {"name": doc.name, "workflow_state": "Withdrawn"}


@frappe.whitelist(methods=["POST"])
def reissue_spec(from_spec: str) -> dict:
    return _handle(_reissue_spec, from_spec)


def _reissue_spec(from_spec: str) -> dict:
    src = frappe.get_doc(_DT_TS, from_spec)
    if src.workflow_state != "Withdrawn":
        raise ServiceError(
            ErrorCode.BAD_STATE,
            _("Chỉ Withdrawn spec mới reissue (hiện: {0})").format(src.workflow_state),
        )
    new = frappe.copy_doc(src, ignore_no_copy=False)
    new.parent_spec = src.name
    # Bump version
    try:
        major = int((src.version or "1.0").split(".")[0])
        new.version = f"{major + 1}.0"
    except Exception:
        new.version = "2.0"
    new.workflow_state = "Draft"
    new.amended_from   = None
    new.approver       = None
    new.approval_date  = None
    new.withdrawal_reason = None
    new.insert()
    return {"name": new.name, "version": new.version, "parent_spec": src.name}


# ─── Market Benchmark ─────────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def submit_benchmark(spec_ref: str, candidates: str = "[]",
                      weighting_scheme: str = "{}") -> dict:
    return _handle(_submit_benchmark, spec_ref, candidates, weighting_scheme)


def _submit_benchmark(spec_ref: str, candidates: str, weighting_scheme: str) -> dict:
    cands = _parse_json(candidates, default=[])
    weights = _parse_json(weighting_scheme, default={})
    mb = frappe.new_doc(_DT_MB)
    mb.spec_ref = spec_ref
    if weights:
        mb.weighting_scheme = json.dumps(weights)
    for c in cands:
        mb.append("candidates", c)
    mb.insert()
    return {"name": mb.name, "recommended": mb.recommended_candidate}


# ─── Lock-in Risk ─────────────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def submit_lock_in_assessment(spec_ref: str, items: str = "[]",
                               threshold: float | None = None,
                               mitigation_plan: str = "",
                               mitigation_evidence: str = "") -> dict:
    return _handle(_submit_lock_in_assessment, spec_ref, items, threshold,
                    mitigation_plan, mitigation_evidence)


def _submit_lock_in_assessment(spec_ref: str, items: str, threshold,
                                 mitigation_plan: str, mitigation_evidence: str) -> dict:
    item_rows = _parse_json(items, default=[])
    lr = frappe.new_doc(_DT_LR)
    lr.spec_ref = spec_ref
    if threshold is not None:
        lr.threshold_used = float(threshold)
    if mitigation_plan:
        lr.mitigation_plan = mitigation_plan
    if mitigation_evidence:
        lr.mitigation_evidence = mitigation_evidence
    for it in item_rows:
        lr.append("items", it)
    lr.insert()
    return {"name": lr.name, "lock_in_score": lr.lock_in_score, "threshold": lr.threshold_used}


# ─── Dashboard ────────────────────────────────────────────────────────────────

@frappe.whitelist()
def dashboard_kpis() -> dict:
    return _handle(_dashboard_kpis)


def _dashboard_kpis() -> dict:
    by_state = dict(frappe.db.sql(
        f"""SELECT workflow_state, COUNT(*) FROM `tab{_DT_TS}` WHERE docstatus < 2
            GROUP BY workflow_state""",
    ))
    avg_lock_in = frappe.db.sql(
        f"SELECT COALESCE(AVG(lock_in_score), 0) FROM `tab{_DT_TS}` WHERE docstatus = 1"
    )[0][0]
    return {
        "by_state": by_state,
        "avg_lock_in_score": round(float(avg_lock_in or 0), 4),
        "backlog_over_30d": frappe.db.sql(
            f"""SELECT COUNT(*) FROM `tab{_DT_TS}`
                WHERE docstatus=0 AND workflow_state IN ('Draft','Reviewing','Benchmarked')
                  AND DATEDIFF(CURDATE(), draft_date) > 30"""
        )[0][0],
    }
