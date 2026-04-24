"""IMM-03 — Technical Specification / Vendor Evaluation / Purchase Order Request API.

Thin HTTP wrapper: parse params → call services.imm03 → _ok / _err envelope.
"""
from __future__ import annotations

import frappe
from assetcore.services import imm03 as svc
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
        frappe.log_error(frappe.get_traceback(), f"IMM-03 {fn.__name__}")
        return _err(str(exc), "SERVER_ERROR")


# ─── Technical Specification ──────────────────────────────────────────────────

@frappe.whitelist()
def create_technical_spec(
    equipment_description: str,
    performance_requirements: str,
    safety_standards: str,
    regulatory_class: str,
    needs_assessment: str = "",
    device_model: str = "",
    accessories_included: str = "",
    warranty_terms: str = "",
    expected_delivery_weeks: int = 0,
    installation_requirements: str = "",
    training_requirements: str = "",
    mdd_class: str = "",
    reference_standard: str = "",
    procurement_method: str = "",
    required_by_date: str = "",
    delivery_location: str = "",
    reference_price_estimate: float = 0,
    site_requirements: str = "",
    lifetime_support_requirements: str = "",
    device_evaluation_ref: str = "",
) -> dict:
    """Create a Technical Specification Draft (IMM-03), linked to a Needs Assessment."""
    return _handle(
        svc.create_technical_spec,
        needs_assessment=needs_assessment,
        equipment_description=equipment_description,
        performance_requirements=performance_requirements,
        safety_standards=safety_standards,
        regulatory_class=regulatory_class,
        device_model=device_model,
        accessories_included=accessories_included,
        warranty_terms=warranty_terms,
        expected_delivery_weeks=int(expected_delivery_weeks) if expected_delivery_weeks else 0,
        installation_requirements=installation_requirements,
        training_requirements=training_requirements,
        mdd_class=mdd_class,
        reference_standard=reference_standard,
        procurement_method=procurement_method,
        required_by_date=required_by_date,
        delivery_location=delivery_location,
        reference_price_estimate=float(reference_price_estimate) if reference_price_estimate else 0,
        site_requirements=site_requirements,
        lifetime_support_requirements=lifetime_support_requirements,
        device_evaluation_ref=device_evaluation_ref,
    )


@frappe.whitelist()
def get_technical_spec(name: str) -> dict:
    """Fetch a single Technical Specification."""
    if not frappe.db.exists("Technical Specification", name):
        return _err(f"Không tìm thấy đặc tả {name}", "NOT_FOUND")
    return _ok(frappe.get_doc("Technical Specification", name).as_dict())


@frappe.whitelist()
def list_technical_specs(
    status: str = "",
    year: str = "",
    regulatory_class: str = "",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List Technical Specifications with optional filters."""
    filters: dict = {}
    if status:
        filters["status"] = status
    if regulatory_class:
        filters["regulatory_class"] = regulatory_class
    if year:
        filters["creation"] = ["between", [f"{year}-01-01", f"{year}-12-31"]]
    total = frappe.db.count("Technical Specification", filters)
    items = frappe.get_list(
        "Technical Specification",
        filters=filters,
        fields=["name", "equipment_description", "regulatory_class",
                "needs_assessment", "status", "creation"],
        order_by="creation desc",
        start=(int(page) - 1) * int(page_size),
        page_length=int(page_size),
    )
    return _ok({"items": items, "total": total, "page": int(page)})


@frappe.whitelist()
def submit_ts_for_review(name: str, approver: str = "") -> dict:
    """Submit Technical Specification for review: Draft → Under Review, notify approver."""
    if not approver:
        return _err("Vui lòng chọn người phê duyệt", "VALIDATION_ERROR")
    try:
        doc = svc.submit_ts_for_review(name)
        frappe.db.set_value("Technical Specification", doc.name, "approver", approver)
        send_approval_request(
            doctype="Technical Specification",
            doc_name=doc.name,
            approver_user=approver,
            submitted_by=frappe.session.user,
            extra_info=doc.equipment_description,
        )
        return _ok({"name": doc.name, "status": doc.status})
    except frappe.ValidationError as exc:
        return _err(str(exc), "VALIDATION_ERROR")
    except Exception as exc:
        frappe.log_error(frappe.get_traceback(), "IMM-03 submit_ts_for_review")
        return _err(str(exc), "SERVER_ERROR")


@frappe.whitelist()
def approve_technical_spec(name: str, review_notes: str = "") -> dict:
    """Approve Technical Specification: Under Review → Approved."""
    return _handle(svc.approve_technical_spec, name, review_notes)


@frappe.whitelist()
def resubmit_technical_spec(name: str) -> dict:
    """Resubmit after revision: Revised → Under Review (MINOR-01)."""
    return _handle(svc.resubmit_technical_spec, name)


# ─── Vendor Evaluation ────────────────────────────────────────────────────────

@frappe.whitelist()
def get_locked_plans() -> dict:
    """Trả về danh sách Procurement Plans có status=Budget Locked, dùng để tạo VE."""
    plans = frappe.get_all(
        "Procurement Plan",
        filters={"status": "Budget Locked"},
        fields=["name", "plan_year", "approved_budget"],
        order_by="creation desc",
    )
    return _ok(plans)


@frappe.whitelist()
def create_vendor_evaluation(
    linked_plan: str,
    evaluation_date: str = "",
    bid_issue_date: str = "",
    bid_closing_date: str = "",
    bid_opening_date: str = "",
    linked_technical_spec: str = "",
) -> dict:
    """Create a Vendor Evaluation Draft linked to a Budget Locked Procurement Plan."""
    return _handle(
        svc.create_vendor_evaluation,
        linked_plan=linked_plan,
        evaluation_date=evaluation_date,
        bid_issue_date=bid_issue_date,
        bid_closing_date=bid_closing_date,
        bid_opening_date=bid_opening_date,
        linked_technical_spec=linked_technical_spec,
    )


@frappe.whitelist()
def add_vendor_to_evaluation(
    ve_name: str,
    vendor: str,
    technical_score: float,
    financial_score: float,
    profile_score: float,
    risk_score: float,
    quoted_price: float = 0,
    compliant_with_ts: int = 0,
    has_nd98_registration: int = 0,
    notes: str = "",
    bid_compliant: int = 1,
    quoted_delivery_weeks: int = 0,
    offered_payment_terms: str = "",
) -> dict:
    """Add a vendor with scores to a Vendor Evaluation."""
    return _handle(
        svc.add_vendor_to_evaluation,
        ve_name=ve_name,
        vendor=vendor,
        technical_score=float(technical_score),
        financial_score=float(financial_score),
        profile_score=float(profile_score),
        risk_score=float(risk_score),
        quoted_price=float(quoted_price) if quoted_price else 0,
        compliant_with_ts=int(compliant_with_ts),
        has_nd98_registration=int(has_nd98_registration),
        notes=notes,
        bid_compliant=int(bid_compliant),
        quoted_delivery_weeks=int(quoted_delivery_weeks) if quoted_delivery_weeks else 0,
        offered_payment_terms=offered_payment_terms,
    )


@frappe.whitelist()
def approve_ve_technical(name: str, notes: str = "") -> dict:
    """Step 1 of 2-step VE approval: In Progress → Tech Reviewed (Technical Reviewer)."""
    return _handle(svc.approve_ve_technical, name, notes)


@frappe.whitelist()
def approve_ve_financial(
    name: str,
    recommended_vendor: str,
    selection_justification: str = "",
    committee_members: str = "",
) -> dict:
    """Step 2 of 2-step VE approval: Tech Reviewed → Approved. Auto-creates PORs."""
    try:
        result = svc.approve_ve_financial(name, recommended_vendor, selection_justification, committee_members)
        doc = result["doc"]
        created_pors = result["created_pors"]
        return _ok({
            "name": doc.name,
            "status": doc.status,
            "recommended_vendor": doc.recommended_vendor,
            "created_pors": created_pors,
        })
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "approve_ve_financial")
        return _err(str(e))


# ─── Purchase Order Request ───────────────────────────────────────────────────

@frappe.whitelist()
def create_purchase_order_request(
    linked_plan_item: str,
    linked_evaluation: str,
    vendor: str,
    equipment_description: str,
    quantity: int,
    unit_price: float,
    linked_technical_spec: str = "",
    delivery_terms: str = "",
    payment_terms: str = "",
    expected_delivery_date: str = "",
    warranty_period_months: int = 0,
    incoterms: str = "",
    payment_schedule_notes: str = "",
) -> dict:
    """Create a Purchase Order Request Draft."""
    return _handle(
        svc.create_purchase_order_request,
        linked_plan_item=linked_plan_item,
        linked_evaluation=linked_evaluation,
        linked_technical_spec=linked_technical_spec,
        vendor=vendor,
        equipment_description=equipment_description,
        quantity=int(quantity),
        unit_price=float(unit_price),
        delivery_terms=delivery_terms,
        payment_terms=payment_terms,
        expected_delivery_date=expected_delivery_date,
        warranty_period_months=int(warranty_period_months) if warranty_period_months else 0,
        incoterms=incoterms,
        payment_schedule_notes=payment_schedule_notes,
    )


@frappe.whitelist()
def submit_por_for_review(name: str, approver: str = "") -> dict:
    """Submit POR for approval: Draft → Under Review, notify approver."""
    if not approver:
        return _err("Vui lòng chọn người phê duyệt", "VALIDATION_ERROR")
    try:
        doc = svc.submit_por_for_review(name)
        frappe.db.set_value("Purchase Order Request", doc.name, "approver", approver)
        send_approval_request(
            doctype="Purchase Order Request",
            doc_name=doc.name,
            approver_user=approver,
            submitted_by=frappe.session.user,
            extra_info=doc.equipment_description,
        )
        return _ok({"name": doc.name, "status": doc.status})
    except frappe.ValidationError as exc:
        return _err(str(exc), "VALIDATION_ERROR")
    except Exception as exc:
        frappe.log_error(frappe.get_traceback(), "IMM-03 submit_por_for_review")
        return _err(str(exc), "SERVER_ERROR")


@frappe.whitelist()
def approve_por(name: str, notes: str = "") -> dict:
    """Approve POR: Under Review → Approved."""
    return _handle(svc.approve_por, name)


@frappe.whitelist()
def release_por(name: str) -> dict:
    """Release POR: Approved → Released. Updates PP Item → Ordered, enqueues IMM-04 notify."""
    return _handle(svc.release_por, name)


@frappe.whitelist()
def confirm_por_delivery(name: str, delivery_notes: str = "") -> dict:
    """Storekeeper confirms delivery: Released → Fulfilled. PP Item → Delivered (PATCH-05)."""
    return _handle(svc.confirm_por_delivery, name, delivery_notes)


@frappe.whitelist()
def get_vendor_evaluation(name: str) -> dict:
    """Fetch a single Vendor Evaluation by name."""
    if not frappe.db.exists("Vendor Evaluation", name):
        return _err(f"Không tìm thấy phiếu đánh giá {name}", "NOT_FOUND")
    return _ok(frappe.get_doc("Vendor Evaluation", name).as_dict())


@frappe.whitelist()
def list_vendor_evaluations(
    status: str = "",
    year: str = "",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List Vendor Evaluations with optional filters."""
    filters: dict = {}
    if status:
        filters["status"] = status
    if year:
        filters["creation"] = ["between", [f"{year}-01-01", f"{year}-12-31"]]
    total = frappe.db.count("Vendor Evaluation", filters)
    items = frappe.get_list(
        "Vendor Evaluation",
        filters=filters,
        fields=["name", "linked_plan", "linked_technical_spec",
                "evaluation_date", "recommended_vendor", "status", "creation"],
        order_by="creation desc",
        start=(int(page) - 1) * int(page_size),
        page_length=int(page_size),
    )
    return _ok({"items": items, "total": total, "page": int(page)})


@frappe.whitelist()
def get_pp_items_for_plan(plan_name: str, page: int = 1, page_size: int = 10) -> dict:
    """Trả về hạng mục kế hoạch mua sắm có phân trang, dùng để hiển thị trong POR Detail."""
    if not frappe.db.exists("Procurement Plan", plan_name):
        return _err(f"Không tìm thấy kế hoạch {plan_name}", "NOT_FOUND")
    page     = int(page)
    per_page = int(page_size)
    total    = frappe.db.count("Procurement Plan Item", {"parent": plan_name})
    items    = frappe.get_all(
        "Procurement Plan Item",
        filters={"parent": plan_name},
        fields=["name", "equipment_description", "quantity", "total_cost",
                "status", "needs_assessment", "por_reference"],
        order_by="idx asc",
        start=(page - 1) * per_page,
        page_length=per_page,
    )
    return _ok({"items": items, "total": total, "page": page, "page_size": per_page})


@frappe.whitelist()
def get_pp_items_for_ve(ve_name: str) -> dict:
    """Trả về PP items (Pending) từ kế hoạch liên kết với VE, kèm NCC đề xuất và báo giá."""
    if not frappe.db.exists("Vendor Evaluation", ve_name):
        return _err(f"Không tìm thấy phiếu đánh giá {ve_name}", "NOT_FOUND")
    ve = frappe.get_doc("Vendor Evaluation", ve_name)
    if not ve.linked_plan:
        return _ok({"linked_plan": None, "recommended_vendor": None, "quoted_price": 0, "pp_items": []})

    quoted_price = 0.0
    if ve.recommended_vendor:
        for item in (ve.items or []):
            if item.vendor == ve.recommended_vendor and item.quoted_price:
                quoted_price = float(item.quoted_price)
                break

    pp_items = frappe.get_all(
        "Procurement Plan Item",
        filters={"parent": ve.linked_plan},
        fields=["name", "equipment_description", "quantity", "total_cost",
                "status", "needs_assessment", "por_reference"],
        order_by="idx asc",
    )
    return _ok({
        "linked_plan": ve.linked_plan,
        "recommended_vendor": ve.recommended_vendor,
        "quoted_price": quoted_price,
        "pp_items": pp_items,
    })


@frappe.whitelist()
def get_approved_ves(plan_name: str = "") -> dict:
    """Return Approved Vendor Evaluations, optionally filtered by linked_plan."""
    filters: dict = {"status": "Approved"}
    if plan_name:
        filters["linked_plan"] = plan_name
    items = frappe.get_list(
        "Vendor Evaluation",
        filters=filters,
        fields=["name", "linked_plan", "linked_technical_spec", "recommended_vendor", "evaluation_date"],
        limit=200,
    )
    return _ok(items)


@frappe.whitelist()
def get_purchase_order_request(name: str) -> dict:
    """Fetch a single Purchase Order Request by name."""
    if not frappe.db.exists("Purchase Order Request", name):
        return _err(f"Không tìm thấy POR {name}", "NOT_FOUND")
    return _ok(frappe.get_doc("Purchase Order Request", name).as_dict())


@frappe.whitelist()
def list_purchase_order_requests(
    status: str = "",
    year: str = "",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List Purchase Order Requests with optional filters."""
    filters: dict = {}
    if status:
        filters["status"] = status
    if year:
        filters["creation"] = ["between", [f"{year}-01-01", f"{year}-12-31"]]
    total = frappe.db.count("Purchase Order Request", filters)
    items = frappe.get_list(
        "Purchase Order Request",
        filters=filters,
        fields=["name", "equipment_description", "vendor", "vendor_name",
                "total_amount", "requires_director_approval", "status",
                "release_date", "creation"],
        order_by="creation desc",
        start=(int(page) - 1) * int(page_size),
        page_length=int(page_size),
    )
    return _ok({"items": items, "total": total, "page": int(page)})


@frappe.whitelist()
def get_planning_dashboard_data(year: str = "") -> dict:
    """Return IMM-01/02/03 planning KPI dashboard data."""
    return _handle(svc.get_planning_dashboard_data, year)
