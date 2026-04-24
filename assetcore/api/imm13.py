# Copyright (c) 2026, AssetCore Team
# REST API cho Module IMM-13 — Suspension & Transfer Gateway (v2.0).
# Tier 1 — parse HTTP input → gọi services.imm13 → _ok / _err envelope.

from __future__ import annotations

import frappe
from frappe.utils import nowdate

from assetcore.services import imm13 as svc
from assetcore.services.shared.errors import ServiceError
from assetcore.utils.helpers import _err, _ok


def _handle(fn, *args, **kwargs) -> dict:
    """Wrapper bắt ServiceError và Exception, trả _ok / _err envelope."""
    try:
        return _ok(fn(*args, **kwargs))
    except ServiceError as e:
        return _err(e.message, e.code)
    except frappe.ValidationError as e:
        return _err(str(e), "VALIDATION_ERROR")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"IMM-13 {getattr(fn, '__name__', 'unknown')}")
        return _err(str(e), "SYSTEM_ERROR")


# ─── Read Endpoints ───────────────────────────────────────────────────────────

@frappe.whitelist()
def get_decommission_request(name: str) -> dict:
    """Lấy chi tiết Decommission Request."""
    def _get(n):
        doc = frappe.get_doc("Decommission Request", n)
        return doc.as_dict()
    return _handle(_get, name)


@frappe.whitelist()
def list_decommission_requests(
    workflow_state: str = "",
    asset: str = "",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Danh sách Decommission Requests với filter."""
    def _list(ws, a, pg, ps):
        filters: dict = {}
        if ws:
            filters["workflow_state"] = ws
        if a:
            filters["asset"] = ("like", f"%{a}%")

        total = frappe.db.count("Decommission Request", filters)
        rows = frappe.db.get_all(
            "Decommission Request",
            filters=filters,
            fields=["name", "asset", "asset_name", "suspension_reason", "outcome",
                    "workflow_state", "current_book_value", "creation", "modified"],
            order_by="modified desc",
            limit_page_length=int(ps),
            limit_start=(int(pg) - 1) * int(ps),
        )
        return {"rows": rows, "total": total, "page": int(pg), "page_size": int(ps)}

    return _handle(_list, workflow_state, asset, page, page_size)


@frappe.whitelist()
def get_asset_suspension_eligibility(asset_name: str) -> dict:
    """Kiểm tra thiết bị có đủ điều kiện tạo Phiếu Ngừng sử dụng."""
    return _handle(svc.get_asset_suspension_eligibility, asset_name)


@frappe.whitelist()
def get_retirement_candidates() -> dict:
    """Lấy danh sách thiết bị đề xuất thanh lý."""
    return _handle(svc.get_retirement_candidates)


@frappe.whitelist()
def get_dashboard_metrics() -> dict:
    """Dashboard KPIs cho IMM-13."""
    return _handle(svc.get_dashboard_metrics)


# ─── Write Endpoints ──────────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def create_decommission_request(
    asset: str,
    suspension_reason: str,
    reason_details: str = "",
    condition_at_suspension: str = "",
    current_book_value: float = 0,
    biological_hazard: int = 0,
    data_destruction_required: int = 0,
    regulatory_clearance_required: int = 0,
) -> dict:
    """Tạo Decommission Request (Phiếu Ngừng sử dụng) mới."""
    def _create(ast, reason, details, condition, book_val, bio_haz, data_destr, reg_clear):
        doc = frappe.get_doc({
            "doctype": "Decommission Request",
            "asset": ast,
            "suspension_reason": reason,
            "reason_details": details,
            "condition_at_suspension": condition,
            "current_book_value": float(book_val),
            "biological_hazard": int(bio_haz),
            "data_destruction_required": int(data_destr),
            "regulatory_clearance_required": int(reg_clear),
            "workflow_state": "Draft",
        })
        doc.insert(ignore_permissions=True)
        return {
            "name": doc.name,
            "asset": doc.asset,
            "workflow_state": doc.workflow_state,
            "creation": str(doc.creation),
        }

    return _handle(
        _create,
        asset, suspension_reason, reason_details,
        condition_at_suspension, current_book_value,
        biological_hazard, data_destruction_required, regulatory_clearance_required,
    )


@frappe.whitelist(methods=["POST"])
def submit_tech_review(
    name: str,
    technical_reviewer: str = "",
    tech_review_notes: str = "",
    residual_risk_level: str = "",
    residual_risk_notes: str = "",
    estimated_remaining_life: int = 0,
) -> dict:
    """Gửi đánh giá kỹ thuật (Draft → Pending Tech Review)."""
    def _submit(n, reviewer, notes, risk_level, risk_notes, remaining_life):
        doc = frappe.get_doc("Decommission Request", n)
        doc.technical_reviewer = reviewer or frappe.session.user
        doc.tech_review_notes = notes
        doc.residual_risk_level = risk_level
        doc.residual_risk_notes = risk_notes
        if remaining_life:
            doc.estimated_remaining_life = int(remaining_life)
        doc.workflow_state = "Pending Tech Review"
        doc.save(ignore_permissions=True)
        svc.log_lifecycle_event(doc, "tech_review_submitted", "Draft", "Pending Tech Review", notes)
        return {"name": n, "workflow_state": "Pending Tech Review"}

    return _handle(_submit, name, technical_reviewer, tech_review_notes,
                   residual_risk_level, residual_risk_notes, estimated_remaining_life)


@frappe.whitelist(methods=["POST"])
def complete_tech_review(
    name: str,
    technical_reviewer: str = "",
    tech_review_notes: str = "",
    residual_risk_level: str = "",
    residual_risk_notes: str = "",
) -> dict:
    """Hoàn thành đánh giá kỹ thuật (Pending Tech Review → Under Replacement Review)."""
    def _complete(n, reviewer, notes, risk_level, risk_notes):
        doc = frappe.get_doc("Decommission Request", n)
        doc.technical_reviewer = reviewer or doc.technical_reviewer or frappe.session.user
        doc.tech_review_notes = notes or doc.tech_review_notes
        doc.residual_risk_level = risk_level or doc.residual_risk_level
        doc.residual_risk_notes = risk_notes or doc.residual_risk_notes
        doc.tech_review_date = nowdate()
        doc.workflow_state = "Under Replacement Review"
        doc.save(ignore_permissions=True)
        svc.log_lifecycle_event(doc, "tech_review_completed", "Pending Tech Review",
                                "Under Replacement Review", notes)
        return {"name": n, "workflow_state": "Under Replacement Review"}

    return _handle(_complete, name, technical_reviewer, tech_review_notes,
                   residual_risk_level, residual_risk_notes)


@frappe.whitelist(methods=["POST"])
def set_replacement_decision(
    name: str,
    outcome: str = "",
    replacement_needed: int = 0,
    transfer_to_location: str = "",
    receiving_officer: str = "",
    transfer_to_department: str = "",
    economic_justification: str = "",
) -> dict:
    """Quyết định kết quả: Transfer / Suspend / Retire."""
    def _decide(n, oc, rep_needed, loc, officer, dept, justification):
        doc = frappe.get_doc("Decommission Request", n)
        doc.outcome = oc
        doc.replacement_needed = int(rep_needed)
        if loc:
            doc.transfer_to_location = loc
        if officer:
            doc.receiving_officer = officer
        if dept:
            doc.transfer_to_department = dept
        if justification:
            doc.economic_justification = justification

        # Route workflow_state based on outcome
        if oc == "Transfer":
            doc.workflow_state = "Approved for Transfer"
        else:
            doc.workflow_state = "Pending Decommission"

        doc.save(ignore_permissions=True)
        svc.log_lifecycle_event(doc, "replacement_decision_set", "Under Replacement Review",
                                doc.workflow_state, f"Kết quả: {oc}")
        return {"name": n, "workflow_state": doc.workflow_state, "outcome": oc}

    return _handle(_decide, name, outcome, replacement_needed,
                   transfer_to_location, receiving_officer, transfer_to_department, economic_justification)


@frappe.whitelist(methods=["POST"])
def approve_suspension(
    name: str,
    approved_by: str = "",
    approval_notes: str = "",
) -> dict:
    """Phê duyệt Phiếu Ngừng sử dụng / Thanh lý."""
    def _approve(n, appr, notes):
        doc = frappe.get_doc("Decommission Request", n)
        doc.approved = 1
        doc.approved_by = appr or frappe.session.user
        doc.approval_date = nowdate()
        doc.approval_notes = notes
        doc.save(ignore_permissions=True)
        svc.log_lifecycle_event(doc, "suspension_approved", doc.workflow_state,
                                doc.workflow_state, f"Phê duyệt bởi {doc.approved_by}. {notes}")
        return {"name": n, "approved": True, "approved_by": doc.approved_by}

    return _handle(_approve, name, approved_by, approval_notes)


@frappe.whitelist(methods=["POST"])
def reject_suspension(name: str, rejection_reason: str = "") -> dict:
    """Từ chối Phiếu Ngừng sử dụng."""
    def _reject(n, reason):
        doc = frappe.get_doc("Decommission Request", n)
        prev_state = doc.workflow_state
        doc.workflow_state = "Cancelled"
        doc.rejection_reason = reason
        doc.save(ignore_permissions=True)
        svc.log_lifecycle_event(doc, "suspension_rejected", prev_state, "Cancelled", reason)
        return {"name": n, "workflow_state": "Cancelled"}

    return _handle(_reject, name, rejection_reason)


@frappe.whitelist(methods=["POST"])
def start_transfer(name: str) -> dict:
    """Bắt đầu thực hiện điều chuyển (Approved for Transfer → Transfer In Progress)."""
    def _start(n):
        doc = frappe.get_doc("Decommission Request", n)
        doc.workflow_state = "Transfer In Progress"
        doc.transfer_start_date = nowdate()
        doc.save(ignore_permissions=True)
        svc.log_lifecycle_event(doc, "transfer_started", "Approved for Transfer",
                                "Transfer In Progress", "Bắt đầu thực hiện điều chuyển")
        return {"name": n, "workflow_state": "Transfer In Progress"}

    return _handle(_start, name)


@frappe.whitelist(methods=["POST"])
def complete_transfer(name: str) -> dict:
    """Hoàn thành điều chuyển — submit document."""
    def _complete(n):
        doc = frappe.get_doc("Decommission Request", n)
        doc.submit()
        return {"name": n, "workflow_state": doc.workflow_state, "asset": doc.asset}

    return _handle(_complete, name)


@frappe.whitelist(methods=["POST"])
def complete_checklist_item(name: str, checklist_item_idx: int, notes: str = "") -> dict:
    """Đánh dấu checklist item là hoàn thành."""
    def _complete(n, idx, nt):
        doc = frappe.get_doc("Decommission Request", n)
        idx = int(idx)
        for item in doc.suspension_checklist:
            if item.idx == idx:
                item.completed = 1
                item.completion_date = nowdate()
                if nt:
                    item.notes = nt
                break
        else:
            frappe.throw(_("Không tìm thấy checklist item idx={0}").format(idx))
        doc.save(ignore_permissions=True)
        return {"name": n, "checklist_item_idx": idx, "completed": True}

    return _handle(_complete, name, checklist_item_idx, notes)
