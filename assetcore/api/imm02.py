"""IMM-02 — Procurement Plan API.

Thin HTTP wrapper: parse params → call services.imm02 → _ok / _err envelope.
"""
from __future__ import annotations

import frappe
from assetcore.services import imm02 as svc
from assetcore.utils.helpers import _err, _ok
from assetcore.utils.email import send_approval_request


def _handle(fn, *args, **kwargs) -> dict:
    try:
        result = fn(*args, **kwargs)
        if hasattr(result, "as_dict"):
            return _ok(result.as_dict())
        return _ok(result)
    except frappe.ValidationError as exc:
        return _err(str(exc), "VALIDATION_ERROR")
    except frappe.PermissionError as exc:
        return _err(str(exc), "PERMISSION_ERROR")
    except Exception as exc:
        frappe.log_error(frappe.get_traceback(), f"IMM-02 {fn.__name__}")
        return _err(str(exc), "SERVER_ERROR")


@frappe.whitelist()
def create_procurement_plan(plan_year: int, approved_budget: float) -> dict:
    """Create a new Procurement Plan Draft."""
    return _handle(svc.create_procurement_plan, int(plan_year), float(approved_budget))


@frappe.whitelist()
def get_procurement_plan(name: str) -> dict:
    """Fetch a single Procurement Plan by name."""
    if not frappe.db.exists("Procurement Plan", name):
        return _err(f"Không tìm thấy kế hoạch {name}", "NOT_FOUND")
    return _ok(frappe.get_doc("Procurement Plan", name).as_dict())


@frappe.whitelist()
def list_procurement_plans(
    status: str = "",
    year: str = "",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List Procurement Plans with optional filters."""
    filters: dict = {}
    if status:
        filters["status"] = status
    if year:
        filters["plan_year"] = int(year)
    total = frappe.db.count("Procurement Plan", filters)
    items = frappe.get_list(
        "Procurement Plan",
        filters=filters,
        fields=["name", "plan_year", "approved_budget", "allocated_budget",
                "remaining_budget", "status"],
        order_by="plan_year desc",
        start=(int(page) - 1) * int(page_size),
        page_length=int(page_size),
    )
    return _ok({"items": items, "total": total, "page": int(page)})


@frappe.whitelist()
def add_na_to_plan(
    plan_name: str,
    needs_assessment: str,
    planned_quarter: str = "",
    estimated_unit_cost: float = 0,
) -> dict:
    """Gắn Needs Assessment đã duyệt vào Procurement Plan."""
    return _handle(
        svc.add_na_to_plan,
        plan_name, needs_assessment, planned_quarter,
        float(estimated_unit_cost) if estimated_unit_cost else 0,
    )


@frappe.whitelist()
def submit_plan_for_review(name: str, approver: str = "") -> dict:
    """Transition Procurement Plan Draft → Under Review, notify approver."""
    if not approver:
        return _err("Vui lòng chọn người phê duyệt", "VALIDATION_ERROR")
    try:
        doc = svc.submit_plan_for_review(name)
        frappe.db.set_value("Procurement Plan", doc.name, "approver", approver)
        send_approval_request(
            doctype="Procurement Plan",
            doc_name=doc.name,
            approver_user=approver,
            submitted_by=frappe.session.user,
            extra_info=f"Năm kế hoạch: {doc.plan_year}",
        )
        return _ok({"name": doc.name, "status": doc.status})
    except frappe.ValidationError as exc:
        return _err(str(exc), "VALIDATION_ERROR")
    except Exception as exc:
        frappe.log_error(frappe.get_traceback(), "IMM-02 submit_plan_for_review")
        return _err(str(exc), "SERVER_ERROR")


@frappe.whitelist()
def approve_plan(name: str, notes: str = "") -> dict:
    """Approve a Procurement Plan: Under Review → Approved."""
    return _handle(svc.approve_plan, name, notes)


@frappe.whitelist()
def lock_budget(name: str) -> dict:
    """Lock PP budget: Approved → Budget Locked. Triggers PP Item → PO Raised, NA → Planned."""
    return _handle(svc.lock_budget, name)


@frappe.whitelist()
def get_approved_nas_for_plan(year: int) -> dict:
    """Return Needs Assessments approved in the given year, available to add to a Plan."""
    return _handle(svc.get_approved_nas_for_plan, int(year))


@frappe.whitelist()
def get_planning_dashboard_data(year: str = "") -> dict:
    """Return IMM-01/02/03 planning KPI dashboard data."""
    from assetcore.services import imm03 as svc03
    return _handle(svc03.get_planning_dashboard_data, year)
