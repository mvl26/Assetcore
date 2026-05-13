# Copyright (c) 2026, AssetCore Team
"""IMM-03 REST API — Wave 2."""
from __future__ import annotations

import json

import frappe
from frappe import _

from assetcore.services import imm03 as svc
from assetcore.services.shared import ErrorCode, ServiceError
from assetcore.utils.helpers import _ok, _err
from assetcore.utils.lifecycle import log_audit_event as _audit

_DT_VE  = "IMM Vendor Evaluation"
_DT_PD  = "IMM Procurement Decision"
_DT_AVL = "IMM AVL Entry"
_DT_VS  = "IMM Vendor Scorecard"
_DT_SA  = "IMM Supplier Audit"


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
        frappe.log_error(frappe.get_traceback(), f"IMM-03 {fn.__name__}")
        return _err(str(e), ErrorCode.INTERNAL)


# ─── Vendor Profile (BE-03-01) ────────────────────────────────────────────────

_DT_SUPPLIER = "AC Supplier"


@frappe.whitelist()
def list_vendor_profiles(filters: str = "{}", page: int = 1, page_size: int = 20) -> dict:
    """Docs §3.1 — List AC Supplier kèm IMM AVL/audit fields & cert counts.

    Data contract (BE-DC-03-01): trả supplier_name, cert_count, cert_expiring_soon.
    """
    return _handle(_list_vendor_profiles, filters, int(page), int(page_size))


def _list_vendor_profiles(filters: str, page: int, page_size: int) -> dict:
    f = _parse_json(filters) or {}
    page_size = max(1, min(page_size, 100))
    start = (max(1, page) - 1) * page_size

    # Filters mapping
    db_filters: dict = {}
    if f.get("avl_status"):
        db_filters["imm_avl_status"] = f["avl_status"]
    if f.get("device_category"):
        db_filters["imm_avl_categories"] = ["like", f"%{f['device_category']}%"]
    if f.get("min_score") is not None:
        db_filters["imm_overall_score"] = [">=", float(f["min_score"])]

    fields = [
        "name", "supplier_name", "imm_avl_status", "imm_avl_categories",
        "imm_overall_score", "imm_last_audit_date", "imm_next_audit_date",
    ]
    items = frappe.get_list(
        _DT_SUPPLIER, filters=db_filters or None, fields=fields,
        order_by="supplier_name asc", start=start, page_length=page_size,
    )

    # Audit overdue filter (post-query — DB doesn't have computed flag)
    if f.get("audit_overdue"):
        today_d = frappe.utils.getdate(frappe.utils.today())
        items = [it for it in items
                 if it.get("imm_next_audit_date")
                 and frappe.utils.getdate(it["imm_next_audit_date"]) < today_d]

    # Cert counts (batch)
    _enrich_vendor_cert_counts(items)

    total = frappe.db.count(_DT_SUPPLIER, db_filters or None)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def _enrich_vendor_cert_counts(items: list[dict]) -> None:
    if not items:
        return
    parent_names = [it["name"] for it in items]
    rows = frappe.get_all(
        "Vendor Cert", filters={"parent": ["in", parent_names]},
        fields=["parent", "status", "expiry_date"], ignore_permissions=True,
    ) if frappe.db.exists("DocType", "Vendor Cert") else []
    today_d = frappe.utils.getdate(frappe.utils.today())
    counts: dict = {p: {"total": 0, "expiring": 0} for p in parent_names}
    for r in rows:
        counts[r["parent"]]["total"] += 1
        exp = r.get("expiry_date")
        if exp:
            try:
                days = (frappe.utils.getdate(exp) - today_d).days
                if 0 <= days <= 60:
                    counts[r["parent"]]["expiring"] += 1
            except Exception:
                pass
    for it in items:
        c = counts.get(it["name"], {"total": 0, "expiring": 0})
        it["cert_count"]         = c["total"]
        it["cert_expiring_soon"] = c["expiring"]


@frappe.whitelist()
def get_vendor_profile(name: str) -> dict:
    """Docs §3.2 — Chi tiết vendor profile kèm certs, AVL entries, scorecard history."""
    return _handle(_get_vendor_profile, name)


def _get_vendor_profile(name: str) -> dict:
    if not frappe.db.exists(_DT_SUPPLIER, name):
        raise ServiceError(ErrorCode.NOT_FOUND,
                            _("Vendor {0} không tồn tại").format(name))
    sup = frappe.get_doc(_DT_SUPPLIER, name)
    data = sup.as_dict()
    # AVL entries
    data["avl_entries"] = frappe.get_all(
        _DT_AVL, filters={"supplier": name},
        fields=["name", "device_category", "workflow_state as status", "valid_from", "valid_to"],
        order_by="valid_to desc",
    )
    # Scorecard history
    data["scorecard_history"] = frappe.get_all(
        _DT_VS, filters={"supplier": name},
        fields=["name", "period_year", "period_quarter", "overall_score"],
        order_by="period_year desc, period_quarter desc",
    )
    return data


@frappe.whitelist(methods=["POST"])
def create_vendor_profile(payload: str = "{}") -> dict:
    """Docs §3.3 — Tạo/cập nhật vendor profile (extension trên AC Supplier).

    Nếu `supplier` đã tồn tại → update fields. Nếu chưa → tạo mới AC Supplier.
    """
    return _handle(_create_vendor_profile, payload)


def _create_vendor_profile(payload: str) -> dict:
    data = _parse_json(payload)
    if not data:
        raise ServiceError(ErrorCode.INVALID_PARAMS, _("payload trống"))
    supplier_name = data.get("supplier") or data.get("supplier_name") or data.get("name")
    if not supplier_name:
        raise ServiceError(ErrorCode.VALIDATION, _("Thiếu supplier"))

    certs = data.pop("certifications", []) or []
    if not certs:
        raise ServiceError(
            ErrorCode.VALIDATION,
            _("VR-03-XX: Thiếu certifications — cần ≥ 1 chứng chỉ ISO 9001 hoặc ISO 13485"),
        )

    # Get or create
    if frappe.db.exists(_DT_SUPPLIER, supplier_name):
        doc = frappe.get_doc(_DT_SUPPLIER, supplier_name)
    else:
        doc = frappe.new_doc(_DT_SUPPLIER)
        doc.supplier_name = supplier_name

    for k, v in data.items():
        if k in ("supplier", "name"):
            continue
        try:
            setattr(doc, k, v)
        except Exception:
            pass

    # Set defaults
    if not doc.get("imm_avl_status"):
        doc.imm_avl_status = "Not Applicable"

    # Replace certs
    if hasattr(doc, "imm_certifications"):
        doc.set("imm_certifications", [])
        for c in certs:
            row = doc.append("imm_certifications", c)
            if not row.get("status"):
                row.status = "Active"

    if doc.is_new():
        doc.insert(ignore_permissions=True)
    else:
        doc.save(ignore_permissions=True)

    return {"name": doc.name, "supplier": doc.supplier_name}


@frappe.whitelist(methods=["POST"])
def add_vendor_cert(supplier: str, cert_type: str, cert_number: str,
                     issued_by: str = "", issued_date: str = "",
                     expiry_date: str = "", attachment: str = "") -> dict:
    """Docs §3.18 — Thêm 1 cert vào AC Supplier.imm_certifications.

    Side effect: tạo lifecycle event `vendor_cert_added` (BE-03-02).
    """
    return _handle(_add_vendor_cert, supplier, cert_type, cert_number,
                    issued_by, issued_date, expiry_date, attachment)


def _add_vendor_cert(supplier: str, cert_type: str, cert_number: str,
                      issued_by: str, issued_date: str, expiry_date: str,
                      attachment: str) -> dict:
    if not frappe.db.exists(_DT_SUPPLIER, supplier):
        raise ServiceError(ErrorCode.NOT_FOUND,
                            _("Vendor {0} không tồn tại").format(supplier))
    if not cert_type or not cert_number:
        raise ServiceError(ErrorCode.VALIDATION, _("cert_type và cert_number bắt buộc"))

    doc = frappe.get_doc(_DT_SUPPLIER, supplier)
    row_data = {
        "cert_type": cert_type, "cert_number": cert_number,
        "issued_by": issued_by or None,
        "issued_date": issued_date or None,
        "expiry_date": expiry_date or None,
        "attachment": attachment or None,
        "status": "Active",
    }
    row = doc.append("imm_certifications", row_data)
    doc.save(ignore_permissions=True)

    try:
        _audit(
            asset=doc.name,
            event_type="vendor_cert_added",
            ref_doctype=_DT_SUPPLIER,
            ref_name=doc.name,
            change_summary=f"IMM-03 cert added: {cert_type} {cert_number}",
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-03 vendor_cert_added audit failed")

    return {"cert_row": row.name, "cert_type": cert_type, "status": "Active"}


# ─── Vendor Evaluation ────────────────────────────────────────────────────────

@frappe.whitelist()
def list_evaluations(filters: str = "{}", page: int = 1, page_size: int = 20) -> dict:
    return _handle(_list_evaluations, filters, int(page), int(page_size))


def _list_evaluations(filters, page, page_size):
    """List Vendor Evaluation kèm display names (BE-DC-03-01)."""
    f = _parse_json(filters)
    page_size = max(1, min(page_size, 100))
    start = (max(1, page) - 1) * page_size
    fields = ["name", "spec_ref", "draft_date", "workflow_state", "recommended_candidate"]
    items = frappe.get_list(_DT_VE, filters=f or None, fields=fields,
                             order_by="draft_date desc", start=start, page_length=page_size)
    _enrich_eval_display_names(items)
    return {"items": items, "total": frappe.db.count(_DT_VE, filters=f or None)}


def _enrich_eval_display_names(items: list[dict]) -> None:
    if not items:
        return
    spec_ids = {it.get("spec_ref") for it in items if it.get("spec_ref")}
    sup_ids  = {it.get("recommended_candidate") for it in items if it.get("recommended_candidate")}
    spec_map = _fetch_display("IMM Tech Spec",  spec_ids, "device_model_ref")
    sup_map  = _fetch_display(_DT_SUPPLIER,     sup_ids,  "supplier_name")
    for it in items:
        it["tech_spec_ref_name"] = spec_map.get(it.get("spec_ref"))
        it["vendor_name"]        = sup_map.get(it.get("recommended_candidate"))


def _fetch_display(doctype: str, ids: set, field: str) -> dict:
    if not ids:
        return {}
    try:
        rows = frappe.get_all(
            doctype, filters={"name": ["in", list(ids)]},
            fields=["name", field], ignore_permissions=True,
        )
        return {r["name"]: r.get(field) for r in rows}
    except Exception:
        return {}


@frappe.whitelist(methods=["POST"])
def create_evaluation(spec_ref: str, weighting_scheme: str = "{}") -> dict:
    return _handle(_create_evaluation, spec_ref, weighting_scheme)


def _create_evaluation(spec_ref, weighting_scheme):
    weights = _parse_json(weighting_scheme, default={})
    ve = frappe.new_doc(_DT_VE)
    ve.spec_ref = spec_ref
    if weights:
        ve.weighting_scheme = json.dumps(weights)
    ve.insert()
    return {"name": ve.name, "workflow_state": ve.workflow_state}


@frappe.whitelist(methods=["POST"])
def add_candidate(name: str, supplier: str, sign_off_non_avl: str = "") -> dict:
    return _handle(_add_candidate, name, supplier, sign_off_non_avl)


def _add_candidate(name, supplier, sign_off_non_avl):
    ve = frappe.get_doc(_DT_VE, name)
    if ve.docstatus != 0:
        raise ServiceError(ErrorCode.BAD_STATE, _("Eval đã submit"))
    in_avl = svc._is_supplier_in_avl(
        supplier, frappe.db.get_value("IMM Tech Spec", ve.spec_ref, "device_category")
    )
    ve.append("candidates", {
        "supplier": supplier, "in_avl": in_avl,
        "sign_off_non_avl": sign_off_non_avl or None,
    })
    ve.save()
    warn = None
    if not in_avl:
        warn = "Vendor non-AVL — cần sign-off IMM Board Approver"
    return {"row_count": len(ve.candidates), "in_avl": in_avl, "warning": warn}


@frappe.whitelist(methods=["POST"])
def submit_quotations(name: str, quotations: str = "[]") -> dict:
    return _handle(_submit_quotations, name, quotations)


def _submit_quotations(name, quotations):
    rows = _parse_json(quotations, default=[])
    ve = frappe.get_doc(_DT_VE, name)
    if ve.docstatus != 0:
        raise ServiceError(ErrorCode.BAD_STATE, _("Eval đã submit"))
    for q in rows:
        ve.append("quotations", q)
    ve.save()
    return {"quotations_count": len(ve.quotations)}


@frappe.whitelist(methods=["POST"])
def score_evaluation(name: str, scorer_role: str, scores_by_supplier: str = "{}") -> dict:
    return _handle(_score_evaluation, name, scorer_role, scores_by_supplier)


def _score_evaluation(name, scorer_role, scores_by_supplier):
    """scores_by_supplier = {supplier_name: {criterion_name: score, ...}, ...}"""
    scores_map = _parse_json(scores_by_supplier, default={})
    ve = frappe.get_doc(_DT_VE, name)
    if ve.docstatus != 0:
        raise ServiceError(ErrorCode.BAD_STATE, _("Eval đã submit"))
    for cand in ve.candidates or []:
        if cand.supplier in scores_map:
            existing = svc._parse_json_field(cand.scores) or {}
            existing.update(scores_map[cand.supplier])
            cand.scores = json.dumps(existing)
    ve.save()
    return {
        "weighted_scores": {c.supplier: c.weighted_score for c in ve.candidates},
        "recommended": ve.recommended_candidate,
    }


# ─── AVL ──────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_avl(filters: str = "{}") -> dict:
    return _handle(_list_avl, filters)


def _list_avl(filters):
    f = _parse_json(filters)
    items = frappe.get_list(_DT_AVL, filters=f or None,
                            fields=["name", "supplier", "device_category", "workflow_state",
                                    "valid_from", "valid_to"],
                            order_by="valid_to asc", page_length=100)
    # BE-DC-03-01: kèm vendor_name
    sup_ids = {it.get("supplier") for it in items if it.get("supplier")}
    sup_map = _fetch_display(_DT_SUPPLIER, sup_ids, "supplier_name")
    for it in items:
        it["vendor_name"] = sup_map.get(it.get("supplier"))
    return {"items": items}


@frappe.whitelist(methods=["POST"])
def create_avl_entry(supplier: str, device_category: str,
                       validity_years: int = 2, valid_from: str = "") -> dict:
    return _handle(_create_avl_entry, supplier, device_category, int(validity_years), valid_from)


def _create_avl_entry(supplier, device_category, validity_years, valid_from):
    avl = frappe.new_doc(_DT_AVL)
    avl.supplier = supplier
    avl.device_category = device_category
    avl.validity_years = validity_years
    avl.valid_from = valid_from or frappe.utils.today()
    avl.workflow_state = "Draft"
    avl.insert()
    return {"name": avl.name, "valid_to": avl.valid_to}


@frappe.whitelist(methods=["POST"])
def approve_avl(name: str, approver: str, approval_doc: str = "") -> dict:
    return _handle(_approve_avl, name, approver, approval_doc)


def _approve_avl(name, approver, approval_doc):
    avl = frappe.get_doc(_DT_AVL, name)
    if avl.workflow_state == "Draft":
        avl.workflow_state = "Approved"
        avl.approver = approver
        avl.approval_doc = approval_doc or None
        avl.submit()
    elif avl.workflow_state in ("Conditional", "Suspended"):
        avl.workflow_state = "Approved"
        avl.save()
        svc._sync_supplier_avl_status(avl.supplier)
    else:
        raise ServiceError(ErrorCode.BAD_STATE,
                            _("AVL ở state {0} không thể Approve").format(avl.workflow_state))
    return {"name": avl.name, "workflow_state": "Approved"}


@frappe.whitelist(methods=["POST"])
def suspend_avl(name: str, suspension_reason: str) -> dict:
    return _handle(_suspend_avl, name, suspension_reason)


def _suspend_avl(name, suspension_reason):
    if not (suspension_reason or "").strip():
        raise ServiceError(ErrorCode.VALIDATION, _("Phải nhập suspension_reason"))
    avl = frappe.get_doc(_DT_AVL, name)
    avl.workflow_state = "Suspended"
    avl.suspension_reason = suspension_reason
    if avl.docstatus == 0:
        avl.submit()
    else:
        avl.save()
    svc._sync_supplier_avl_status(avl.supplier)
    return {"name": avl.name, "workflow_state": "Suspended"}


# ─── Procurement Decision ─────────────────────────────────────────────────────

@frappe.whitelist()
def get_evaluation(name: str) -> dict:
    def _get(n):
        doc = frappe.get_doc(_DT_VE, n).as_dict()
        candidates = doc.get("candidates") or []
        quotations = doc.get("quotations") or []
        all_sup_ids = (
            {c.get("supplier") for c in candidates if c.get("supplier")}
            | {q.get("candidate_supplier") for q in quotations if q.get("candidate_supplier")}
        )
        if all_sup_ids:
            sup_map = _fetch_display(_DT_SUPPLIER, all_sup_ids, "supplier_name")
            for c in candidates:
                c["supplier_name"] = sup_map.get(c.get("supplier")) or c.get("supplier") or ""
            for q in quotations:
                q["candidate_supplier_name"] = sup_map.get(q.get("candidate_supplier")) or q.get("candidate_supplier") or ""
        return doc
    return _handle(_get, name)


@frappe.whitelist()
def get_decision(name: str) -> dict:
    def _get(n):
        doc = frappe.get_doc(_DT_PD, n).as_dict()
        candidates = doc.get("candidates") or []
        winner = doc.get("winner_supplier")
        sup_ids = {c.get("supplier") for c in candidates if c.get("supplier")}
        if winner:
            sup_ids.add(winner)
        if sup_ids:
            sup_map = _fetch_display(_DT_SUPPLIER, sup_ids, "supplier_name")
            for c in candidates:
                c["supplier_name"] = sup_map.get(c.get("supplier")) or c.get("supplier") or ""
            if winner:
                doc["winner_supplier_name"] = sup_map.get(winner) or winner
        return doc
    return _handle(_get, name)


@frappe.whitelist()
def get_avl(name: str) -> dict:
    return _handle(lambda n: frappe.get_doc(_DT_AVL, n).as_dict(), name)


@frappe.whitelist()
def list_decisions(filters: str = "{}", page: int = 1, page_size: int = 20) -> dict:
    return _handle(_list_decisions, filters, int(page), int(page_size))


def _list_decisions(filters, page, page_size):
    f = _parse_json(filters)
    page_size = max(1, min(page_size, 100))
    start = (max(1, page) - 1) * page_size
    items = frappe.get_list(_DT_PD, filters=f or None, fields=[
        "name", "spec_ref", "winner_supplier", "awarded_price",
        "envelope_check_pct", "workflow_state", "ac_purchase_ref", "creation",
    ], order_by="creation desc", start=start, page_length=page_size)
    # BE-DC-03-01: kèm vendor_name + tech_spec_ref_name
    sup_ids  = {it.get("winner_supplier") for it in items if it.get("winner_supplier")}
    spec_ids = {it.get("spec_ref")        for it in items if it.get("spec_ref")}
    sup_map  = _fetch_display(_DT_SUPPLIER,    sup_ids,  "supplier_name")
    spec_map = _fetch_display("IMM Tech Spec", spec_ids, "device_model_ref")
    for it in items:
        it["vendor_name"]        = sup_map.get(it.get("winner_supplier"))
        it["tech_spec_ref_name"] = spec_map.get(it.get("spec_ref"))
    return {"items": items, "total": frappe.db.count(_DT_PD, filters=f or None)}


@frappe.whitelist(methods=["POST"])
def transition_eval_workflow(name: str, action: str) -> dict:
    return _handle(_transition_eval_workflow, name, action)


def _transition_eval_workflow(name, action):
    from frappe.model.workflow import apply_workflow
    doc_before = frappe.get_doc(_DT_VE, name)
    prev_state = doc_before.workflow_state or "Draft"
    apply_workflow(doc_before, action)
    doc = frappe.get_doc(_DT_VE, name)
    try:
        _audit(
            asset=doc.name,
            event_type="imm03_eval_workflow_transition",
            ref_doctype=_DT_VE,
            ref_name=doc.name,
            change_summary=f"IMM-03 Eval [{action}]: {prev_state} → {doc.workflow_state}",
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-03 audit trail failed")
    return {"name": doc.name, "workflow_state": doc.workflow_state, "docstatus": doc.docstatus}


@frappe.whitelist(methods=["POST"])
def transition_decision_workflow(name: str, action: str) -> dict:
    return _handle(_transition_decision_workflow, name, action)


def _transition_decision_workflow(name, action):
    from frappe.model.workflow import apply_workflow
    doc_before = frappe.get_doc(_DT_PD, name)
    prev_state = doc_before.workflow_state or "Draft"
    apply_workflow(doc_before, action)
    doc = frappe.get_doc(_DT_PD, name)
    try:
        _audit(
            asset=doc.name,
            event_type="imm03_decision_workflow_transition",
            ref_doctype=_DT_PD,
            ref_name=doc.name,
            change_summary=f"IMM-03 Decision [{action}]: {prev_state} → {doc.workflow_state}",
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-03 audit trail failed")
    return {"name": doc.name, "workflow_state": doc.workflow_state, "docstatus": doc.docstatus}


@frappe.whitelist(methods=["POST"])
def create_decision(evaluation_ref: str, procurement_method: str,
                     method_legal_basis: str = "") -> dict:
    return _handle(_create_decision, evaluation_ref, procurement_method, method_legal_basis)


def _create_decision(evaluation_ref, procurement_method, method_legal_basis):
    ve = frappe.get_doc(_DT_VE, evaluation_ref)
    pd = frappe.new_doc(_DT_PD)
    pd.spec_ref           = ve.spec_ref
    pd.evaluation_ref     = ve.name
    pd.procurement_method = procurement_method
    pd.method_legal_basis = method_legal_basis or None
    if ve.spec_ref:
        ts = frappe.get_doc("IMM Tech Spec", ve.spec_ref)
        pd.plan_ref  = ts.source_plan
        pd.plan_line = ts.source_plan_line
        pd.quantity  = ts.quantity
    pd.insert()
    return {"name": pd.name, "workflow_state": pd.workflow_state}


@frappe.whitelist(methods=["POST"])
def award_decision(name: str, winner_supplier: str, awarded_price: float,
                    funding_source: str, board_approver: str,
                    contract_doc: str = "", remarks: str = "") -> dict:
    return _handle(_award_decision, name, winner_supplier, float(awarded_price),
                    funding_source, board_approver, contract_doc, remarks)


def _award_decision(name, winner_supplier, awarded_price, funding_source,
                     board_approver, contract_doc, remarks):
    pd = frappe.get_doc(_DT_PD, name)
    if pd.docstatus != 0:
        raise ServiceError(ErrorCode.BAD_STATE, _("Decision đã submit"))
    pd.winner_supplier = winner_supplier
    pd.awarded_price   = awarded_price
    pd.funding_source  = funding_source
    pd.board_approver  = board_approver
    if contract_doc:
        pd.contract_doc = contract_doc
    pd.workflow_state  = "Awarded"
    pd.submit()
    try:
        _audit(
            asset=pd.name,
            event_type="imm03_decision_awarded",
            ref_doctype=_DT_PD,
            ref_name=pd.name,
            change_summary=f"IMM-03 Decision awarded to {winner_supplier}. Board approver: {board_approver}. {remarks}",
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-03 audit trail failed")
    return {
        "name":            pd.name,
        "workflow_state":  pd.workflow_state,
        "ac_purchase_ref": pd.ac_purchase_ref,
        "envelope_check_pct": pd.envelope_check_pct,
    }


@frappe.whitelist(methods=["POST"])
def record_contract(name: str, contract_no: str, contract_doc: str = "",
                     signed_date: str = "") -> dict:
    return _handle(_record_contract, name, contract_no, contract_doc, signed_date)


def _record_contract(name, contract_no, contract_doc, signed_date):
    from frappe.model.workflow import apply_workflow
    pd = frappe.get_doc(_DT_PD, name)
    if pd.docstatus != 1:
        raise ServiceError(ErrorCode.BAD_STATE, _("Decision phải đã submit (Awarded)"))
    # Update contract fields via DB set_value (safe on submitted docs)
    updates = {"contract_no": contract_no}
    if contract_doc:
        updates["contract_doc"] = contract_doc
    # contract_signed_date not in DocType schema — skip
    frappe.db.set_value(_DT_PD, name, updates)
    # Advance workflow state using apply_workflow
    apply_workflow(pd, "Ký HĐ")
    try:
        _audit(
            asset=pd.name,
            event_type="imm03_contract_signed",
            ref_doctype=_DT_PD,
            ref_name=pd.name,
            change_summary=f"IMM-03 Contract signed. No: {contract_no}.",
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "IMM-03 audit trail failed")
    return {"name": pd.name, "workflow_state": "Contract Signed"}


# ─── Scorecard & Dashboard ────────────────────────────────────────────────────

@frappe.whitelist()
def get_vendor_scorecard(supplier: str, year: int, quarter: int) -> dict:
    return _handle(_get_vendor_scorecard, supplier, int(year), int(quarter))


def _get_vendor_scorecard(supplier, year, quarter):
    name = frappe.db.get_value(_DT_VS, {
        "supplier": supplier, "period_year": year, "period_quarter": quarter,
    })
    if not name:
        raise ServiceError(ErrorCode.NOT_FOUND,
                            _("Chưa có Scorecard cho {0} {1}-Q{2}").format(supplier, year, quarter))
    return frappe.get_doc(_DT_VS, name).as_dict()


@frappe.whitelist()
def dashboard_kpis() -> dict:
    return _handle(_dashboard_kpis)


def _dashboard_kpis():
    # Funnel state
    eval_states = dict(frappe.db.sql(
        f"SELECT workflow_state, COUNT(*) FROM `tab{_DT_VE}` WHERE docstatus<2 GROUP BY workflow_state"
    ))
    decision_states = dict(frappe.db.sql(
        f"SELECT workflow_state, COUNT(*) FROM `tab{_DT_PD}` WHERE docstatus<2 GROUP BY workflow_state"
    ))
    avl_active = frappe.db.count(_DT_AVL, {"docstatus": 1, "workflow_state": ["in", ["Approved","Conditional"]]})
    return {
        "eval_states":     eval_states,
        "decision_states": decision_states,
        "avl_active":      avl_active,
        "avl_expiring_30d": frappe.db.sql(
            f"""SELECT COUNT(*) FROM `tab{_DT_AVL}`
                WHERE docstatus=1 AND workflow_state IN ('Approved','Conditional')
                  AND DATEDIFF(valid_to, CURDATE()) BETWEEN 0 AND 30"""
        )[0][0],
    }
