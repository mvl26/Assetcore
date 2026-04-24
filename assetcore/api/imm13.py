# Copyright (c) 2026, AssetCore Team
# REST API cho Module IMM-13 — Decommissioning & Disposal.
# Tier 1 — parse HTTP input → gọi services.imm13 → _ok / _err envelope.

from __future__ import annotations

import frappe

from assetcore.services import imm13 as svc
from assetcore.services.shared.errors import ServiceError
from assetcore.utils.helpers import _err, _ok


def _handle(fn, *args, **kwargs) -> dict:
    """Wrapper bắt ServiceError và Exception, trả _ok / _err."""
    try:
        return _ok(fn(*args, **kwargs))
    except ServiceError as e:
        return _err(e.message, e.code)
    except frappe.ValidationError as e:
        return _err(str(e), "VALIDATION_ERROR")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"IMM-13 {fn.__name__}")
        return _err(str(e), "SYSTEM_ERROR")


# ─── Read Endpoints ───────────────────────────────────────────────────────────

@frappe.whitelist()
def get_decommission_request(name: str) -> dict:
    """Lấy chi tiết Decommission Request."""
    def _get(n):
        doc = frappe.get_doc("Decommission Request", n)
        result = doc.as_dict()
        return result
    return _handle(_get, name)


@frappe.whitelist()
def list_decommission_requests(status: str = "", asset: str = "", year: str = "",
                                page: int = 1, page_size: int = 20) -> dict:
    """Danh sách Decommission Requests với filter."""
    def _list(s, a, y, pg, ps):
        filters: dict = {}
        if s:
            filters["status"] = s
        if a:
            filters["asset"] = a
        if y:
            filters["creation"] = ("like", f"{y}%")

        total = frappe.db.count("Decommission Request", filters)
        rows = frappe.db.get_all(
            "Decommission Request",
            filters=filters,
            fields=["name", "asset", "asset_name", "decommission_reason",
                    "disposal_method", "current_book_value", "status",
                    "workflow_state", "creation", "modified"],
            order_by="modified desc",
            limit_page_length=int(ps),
            limit_start=(int(pg) - 1) * int(ps),
        )
        return {"rows": rows, "total": total, "page": int(pg), "page_size": int(ps)}

    return _handle(_list, status, asset, year, page, page_size)


@frappe.whitelist()
def get_asset_decommission_eligibility(asset_name: str) -> dict:
    """Kiểm tra thiết bị có đủ điều kiện thanh lý."""
    return _handle(svc.get_asset_decommission_eligibility, asset_name)


@frappe.whitelist()
def get_dashboard_stats() -> dict:
    """Dashboard KPIs cho IMM-13."""
    return _handle(svc.get_dashboard_stats)


# ─── Write Endpoints ──────────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def create_decommission_request(asset: str, decommission_reason: str, reason_details: str,
                                 condition_at_decommission: str = "",
                                 current_book_value: float = 0,
                                 estimated_disposal_value: float = 0,
                                 disposal_method: str = "Scrap") -> dict:
    """Tạo Decommission Request mới."""
    def _create(ast, reason, details, condition, book_val, disposal_val, method):
        doc = frappe.get_doc({
            "doctype": "Decommission Request",
            "asset": ast,
            "decommission_reason": reason,
            "reason_details": details,
            "condition_at_decommission": condition,
            "current_book_value": book_val,
            "estimated_disposal_value": disposal_val,
            "disposal_method": method,
            "status": "Draft",
        })
        doc.insert(ignore_permissions=True)
        return {"name": doc.name, "asset": doc.asset, "status": doc.status, "creation": str(doc.creation)}

    return _handle(_create, asset, decommission_reason, reason_details,
                   condition_at_decommission, current_book_value, estimated_disposal_value, disposal_method)


@frappe.whitelist(methods=["POST"])
def submit_technical_review(name: str, reviewer: str, review_notes: str,
                             approved: bool = True) -> dict:
    """Hoàn thành đánh giá kỹ thuật."""
    def _review(n, rev, notes, appr):
        doc = frappe.get_doc("Decommission Request", n)
        new_status = "Financial Valuation" if appr else "Rejected"
        doc.technical_reviewer = rev
        doc.technical_review_notes = notes
        from frappe.utils import nowdate
        doc.technical_review_date = nowdate()
        doc.status = new_status
        doc.workflow_state = new_status
        doc.save(ignore_permissions=True)
        svc.log_lifecycle_event(doc, "technical_review_completed" if appr else "technical_review_rejected",
                                "Technical Review", new_status, notes)
        return {"name": n, "status": new_status}

    return _handle(_review, name, reviewer, review_notes, approved)


@frappe.whitelist(methods=["POST"])
def submit_financial_valuation(name: str, reviewer: str, final_book_value: float,
                                estimated_disposal_value: float, review_notes: str = "") -> dict:
    """Hoàn thành định giá tài chính."""
    def _finance(n, rev, bv, dv, notes):
        doc = frappe.get_doc("Decommission Request", n)
        from frappe.utils import nowdate
        doc.finance_reviewer = rev
        doc.finance_review_date = nowdate()
        doc.finance_review_notes = notes
        doc.current_book_value = bv
        doc.estimated_disposal_value = dv
        doc.status = "Pending Approval"
        doc.workflow_state = "Pending Approval"
        doc.save(ignore_permissions=True)
        svc.log_lifecycle_event(doc, "financial_valuation_completed", "Financial Valuation", "Pending Approval", notes)
        return {"name": n, "status": "Pending Approval"}

    return _handle(_finance, name, reviewer, final_book_value, estimated_disposal_value, review_notes)


@frappe.whitelist(methods=["POST"])
def request_approval(name: str) -> dict:
    """Gửi thông báo phê duyệt cho VP Block2."""
    def _request(n):
        doc = frappe.get_doc("Decommission Request", n)
        svc.log_lifecycle_event(doc, "approval_requested", doc.status or "Pending Approval",
                                "Pending Approval", "Gửi yêu cầu phê duyệt")
        return {"name": n, "status": doc.status}

    return _handle(_request, name)


@frappe.whitelist(methods=["POST"])
def approve_decommission(name: str, approver: str, approval_notes: str = "") -> dict:
    """Phê duyệt Decommission Request."""
    def _approve(n, appr, notes):
        doc = frappe.get_doc("Decommission Request", n)
        from frappe.utils import nowdate
        doc.approved_by = appr
        doc.approval_date = nowdate()
        doc.approval_notes = notes
        doc.status = "Board Approved"
        doc.workflow_state = "Board Approved"
        doc.save(ignore_permissions=True)
        svc.log_lifecycle_event(doc, "decommission_approved", "Pending Approval", "Board Approved", notes)
        return {"name": n, "status": "Board Approved"}

    return _handle(_approve, name, approver, approval_notes)


@frappe.whitelist(methods=["POST"])
def reject_decommission(name: str, reason: str) -> dict:
    """Từ chối Decommission Request."""
    def _reject(n, r):
        doc = frappe.get_doc("Decommission Request", n)
        prev_status = doc.status
        doc.status = "Rejected"
        doc.workflow_state = "Rejected"
        doc.approval_notes = r
        doc.save(ignore_permissions=True)
        svc.log_lifecycle_event(doc, "decommission_rejected", prev_status, "Rejected", r)
        return {"name": n, "status": "Rejected"}

    return _handle(_reject, name, reason)


@frappe.whitelist(methods=["POST"])
def execute_decommission(name: str, executor: str, execution_date: str,
                          execution_notes: str = "") -> dict:
    """Bắt đầu thực thi thanh lý."""
    def _execute(n, exec_by, exec_date, notes):
        doc = frappe.get_doc("Decommission Request", n)
        doc.executed_by = exec_by
        doc.execution_date = exec_date
        doc.execution_notes = notes
        doc.status = "Execution"
        doc.workflow_state = "Execution"
        doc.save(ignore_permissions=True)
        svc.log_lifecycle_event(doc, "decommission_execution_started", "Board Approved", "Execution", notes)
        return {"name": n, "status": "Execution"}

    return _handle(_execute, name, executor, execution_date, execution_notes)


@frappe.whitelist(methods=["POST"])
def complete_checklist_item(name: str, checklist_item_idx: int, notes: str = "") -> dict:
    """Đánh dấu checklist item là hoàn thành."""
    def _complete(n, idx, nt):
        doc = frappe.get_doc("Decommission Request", n)
        from frappe.utils import nowdate
        idx = int(idx)
        for item in doc.checklist:
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
