"""IMM-03 — Technical Spec / Vendor Evaluation / POR service layer."""
from __future__ import annotations
import frappe
from frappe import _


# ─── Technical Specification ─────────────────────────────────────────────────

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
) -> Document:
    """Tạo Technical Specification Draft, liên kết với Needs Assessment."""
    if not regulatory_class:
        frappe.throw(_("VR-03-02: Phân loại NĐ98 là bắt buộc"))

    # Auto-fill equipment_description from NA if not provided
    if not equipment_description and needs_assessment:
        equipment_description = frappe.db.get_value(
            "Needs Assessment", needs_assessment, "equipment_type"
        ) or equipment_description

    doc = frappe.get_doc({
        "doctype": "Technical Specification",
        "needs_assessment": needs_assessment or None,
        "equipment_description": equipment_description,
        "performance_requirements": performance_requirements,
        "safety_standards": safety_standards,
        "regulatory_class": regulatory_class,
        "device_model": device_model or None,
        "accessories_included": accessories_included or None,
        "warranty_terms": warranty_terms or None,
        "expected_delivery_weeks": int(expected_delivery_weeks) if expected_delivery_weeks else None,
        "installation_requirements": installation_requirements or None,
        "training_requirements": training_requirements or None,
        "mdd_class": mdd_class or None,
        "reference_standard": reference_standard or None,
        "procurement_method": procurement_method or None,
        "required_by_date": required_by_date or None,
        "delivery_location": delivery_location or None,
        "reference_price_estimate": float(reference_price_estimate) if reference_price_estimate else None,
        "site_requirements": site_requirements or None,
        "lifetime_support_requirements": lifetime_support_requirements or None,
        "device_evaluation_ref": device_evaluation_ref or None,
        "status": "Draft",
    })
    doc.insert(ignore_permissions=False)

    # Link back to NA
    if needs_assessment:
        frappe.db.set_value("Needs Assessment", needs_assessment, "technical_specification", doc.name)

    return doc


def approve_technical_spec(ts_name: str, notes: str = "") -> Document:
    """Under Review → Approved."""
    doc = frappe.get_doc("Technical Specification", ts_name)
    if doc.status != "Under Review":
        frappe.throw(_("Đặc tả kỹ thuật phải ở trạng thái Under Review"))
    doc.status = "Approved"
    doc.reviewed_by = frappe.session.user
    doc.review_date = frappe.utils.today()
    doc.review_notes = notes
    doc.save(ignore_permissions=False)
    if doc.needs_assessment:
        frappe.db.set_value("Needs Assessment", doc.needs_assessment, "technical_specification", doc.name)
    return doc


def submit_ts_for_review(ts_name: str) -> Document:
    """Draft → Under Review."""
    doc = frappe.get_doc("Technical Specification", ts_name)
    if doc.status != "Draft":
        frappe.throw(_("Đặc tả kỹ thuật phải ở trạng thái Draft"))
    doc.status = "Under Review"
    doc.save(ignore_permissions=False)
    return doc


def resubmit_technical_spec(ts_name: str) -> Document:
    """Revised → Under Review: Ops Manager gửi lại TS sau khi nhận phản hồi (MINOR-01)."""
    doc = frappe.get_doc("Technical Specification", ts_name)
    if doc.status != "Revised":
        frappe.throw(_("Đặc tả kỹ thuật phải ở trạng thái Revised"))
    doc.status = "Under Review"
    doc.save(ignore_permissions=False)
    return doc


# ─── Vendor Evaluation ────────────────────────────────────────────────────────

def create_vendor_evaluation(
    linked_plan: str,
    evaluation_date: str = "",
    bid_issue_date: str = "",
    bid_closing_date: str = "",
    bid_opening_date: str = "",
    linked_technical_spec: str = "",
) -> Document:
    """Tạo Vendor Evaluation Draft liên kết với Procurement Plan đã khóa ngân sách."""
    if not linked_plan:
        frappe.throw(_("Phải liên kết với Kế hoạch mua sắm"))
    pp_status = frappe.db.get_value("Procurement Plan", linked_plan, "status")
    if pp_status != "Budget Locked":
        frappe.throw(_("Kế hoạch mua sắm phải ở trạng thái Budget Locked"))

    doc = frappe.get_doc({
        "doctype": "Vendor Evaluation",
        "linked_plan": linked_plan,
        "linked_technical_spec": linked_technical_spec or None,
        "evaluation_date": evaluation_date or frappe.utils.today(),
        "bid_issue_date": bid_issue_date or None,
        "bid_closing_date": bid_closing_date or None,
        "bid_opening_date": bid_opening_date or None,
        "status": "Draft",
    })
    doc.insert(ignore_permissions=False)
    return doc


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
) -> Document:
    """Thêm nhà cung cấp vào Vendor Evaluation và tính điểm."""
    doc = frappe.get_doc("Vendor Evaluation", ve_name)
    if doc.status not in ("Draft", "In Progress"):
        frappe.throw(_("Chỉ có thể thêm NCC khi đánh giá ở Draft hoặc In Progress"))

    # kiểm tra trùng vendor
    existing = [i for i in doc.items if i.vendor == vendor]
    if existing:
        frappe.throw(_("Nhà cung cấp {0} đã có trong danh sách đánh giá").format(vendor))

    doc.append("items", {
        "vendor": vendor,
        "quoted_price": float(quoted_price) if quoted_price else 0,
        "technical_score": float(technical_score),
        "financial_score": float(financial_score),
        "profile_score": float(profile_score),
        "risk_score": float(risk_score),
        "compliant_with_ts": int(compliant_with_ts),
        "has_nd98_registration": int(has_nd98_registration),
        "notes": notes or None,
        "bid_compliant": int(bid_compliant),
        "quoted_delivery_weeks": int(quoted_delivery_weeks) if quoted_delivery_weeks else None,
        "offered_payment_terms": offered_payment_terms or None,
    })
    if doc.status == "Draft" and len(doc.items) >= 1:
        doc.status = "In Progress"
    doc.save(ignore_permissions=False)
    return doc


def approve_ve_technical(ve_name: str, notes: str = "") -> Document:
    """In Progress → Tech Reviewed (PATCH-04 step 1: IMM Technical Reviewer)."""
    doc = frappe.get_doc("Vendor Evaluation", ve_name)
    if doc.status != "In Progress":
        frappe.throw(_("VE phải ở trạng thái In Progress để duyệt kỹ thuật"))
    if len(doc.items or []) < 2:
        frappe.throw(_("VR-03-04: Cần ít nhất 2 NCC để đánh giá cạnh tranh"))
    doc.tech_reviewed_by = frappe.session.user
    doc.tech_review_date = frappe.utils.today()
    doc.status = "Tech Reviewed"
    doc.save(ignore_permissions=False)
    return doc


def approve_ve_financial(
    ve_name: str,
    recommended_vendor: str,
    selection_justification: str = "",
    committee_members: str = "",
) -> dict:
    """Tech Reviewed → Approved (PATCH-04 step 2: IMM Finance Officer).
    Sau khi approve, tự động tạo POR cho từng PP Item trong kế hoạch liên kết."""
    doc = frappe.get_doc("Vendor Evaluation", ve_name)
    if doc.status != "Tech Reviewed":
        frappe.throw(_("VE phải ở trạng thái Tech Reviewed (bước 1 chưa hoàn thành)"))
    if not recommended_vendor:
        frappe.throw(_("Phải chỉ định NCC được đề xuất"))
    doc.recommended_vendor = recommended_vendor
    doc.selection_justification = selection_justification
    if committee_members:
        doc.committee_members = committee_members
    doc.status = "Approved"
    doc.approved_by = frappe.session.user
    doc.approval_date = frappe.utils.today()
    doc.save(ignore_permissions=False)

    # Auto-create POR cho từng PP Item
    created_pors = _auto_create_pors_for_ve(doc, recommended_vendor)

    return {"doc": doc, "created_pors": created_pors}


def _auto_create_pors_for_ve(ve_doc, recommended_vendor: str) -> list:
    """Tự động tạo POR (Draft) cho từng Procurement Plan Item trong kế hoạch liên kết."""
    if not ve_doc.linked_plan:
        return []

    # Tìm quoted_price của vendor được chọn trong VE items
    unit_price = 0.0
    for item in (ve_doc.items or []):
        if item.vendor == recommended_vendor and item.quoted_price:
            unit_price = float(item.quoted_price)
            break

    # Lấy tất cả PP Items chưa có POR
    pp_items = frappe.get_all(
        "Procurement Plan Item",
        filters={"parent": ve_doc.linked_plan, "status": "Pending"},
        fields=["name", "equipment_description", "quantity", "total_cost", "needs_assessment"],
    )

    created_pors = []
    for pp_item in pp_items:
        por = frappe.get_doc({
            "doctype": "Purchase Order Request",
            "linked_plan_item": pp_item.name,
            "procurement_plan": ve_doc.linked_plan,
            "linked_evaluation": ve_doc.name,
            "linked_technical_spec": ve_doc.linked_technical_spec or None,
            "vendor": recommended_vendor,
            "equipment_description": pp_item.equipment_description or "",
            "quantity": int(pp_item.quantity or 1),
            "unit_price": unit_price,
            "status": "Draft",
        })
        por.insert(ignore_permissions=True)
        # Cập nhật PP Item status → PO Raised
        frappe.db.set_value("Procurement Plan Item", pp_item.name, "status", "PO Raised")
        created_pors.append(por.name)

    return created_pors


# ─── Purchase Order Request ───────────────────────────────────────────────────

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
) -> Document:
    """Tạo Purchase Order Request Draft."""
    # Kiểm tra VE đã Approved
    ve_status = frappe.db.get_value("Vendor Evaluation", linked_evaluation, "status")
    if ve_status != "Approved":
        frappe.throw(_("Phiếu đánh giá NCC phải ở trạng thái Approved"))

    # Kiểm tra PP đã Budget Locked
    procurement_plan = frappe.db.get_value(
        "Procurement Plan Item", linked_plan_item, "parent"
    )
    if procurement_plan:
        pp_status = frappe.db.get_value("Procurement Plan", procurement_plan, "status")
        if pp_status != "Budget Locked":
            frappe.throw(
                _("BR-03-03: Kế hoạch mua sắm phải ở trạng thái Budget Locked trước khi tạo POR")
            )

    doc = frappe.get_doc({
        "doctype": "Purchase Order Request",
        "linked_plan_item": linked_plan_item,
        "procurement_plan": procurement_plan,
        "linked_evaluation": linked_evaluation,
        "linked_technical_spec": linked_technical_spec,
        "vendor": vendor,
        "equipment_description": equipment_description,
        "quantity": int(quantity),
        "unit_price": float(unit_price),
        "delivery_terms": delivery_terms or None,
        "payment_terms": payment_terms or None,
        "expected_delivery_date": expected_delivery_date or None,
        "warranty_period_months": int(warranty_period_months) if warranty_period_months else None,
        "incoterms": incoterms or None,
        "payment_schedule_notes": payment_schedule_notes or None,
        "status": "Draft",
    })
    doc.insert(ignore_permissions=False)
    if linked_plan_item:
        frappe.db.set_value("Procurement Plan Item", linked_plan_item, "status", "PO Raised")
    return doc


def approve_por(por_name: str) -> Document:
    """Under Review → Approved."""
    doc = frappe.get_doc("Purchase Order Request", por_name)
    if doc.status != "Under Review":
        frappe.throw(_("POR phải ở trạng thái Under Review"))
    doc.status = "Approved"
    doc.approved_by = frappe.session.user
    doc.approval_date = frappe.utils.today()
    doc.save(ignore_permissions=False)
    return doc


def release_por(por_name: str) -> Document:
    """Approved → Released — kích hoạt toàn bộ downstream chain."""
    doc = frappe.get_doc("Purchase Order Request", por_name)
    if doc.status != "Approved":
        frappe.throw(_("POR phải ở trạng thái Approved trước khi phát hành"))

    # Verify PP vẫn Budget Locked
    if doc.procurement_plan:
        pp_status = frappe.db.get_value("Procurement Plan", doc.procurement_plan, "status")
        if pp_status != "Budget Locked":
            frappe.throw(_("BR-03-03: Kế hoạch mua sắm không còn ở trạng thái Budget Locked"))

    doc.status = "Released"
    doc.release_date = frappe.utils.today()
    doc.released_by = frappe.session.user

    # Cập nhật PP Item → Ordered
    if doc.linked_plan_item:
        frappe.db.set_value("Procurement Plan Item", doc.linked_plan_item, "status", "Ordered")
        frappe.db.set_value("Procurement Plan Item", doc.linked_plan_item, "por_reference", doc.name)

    doc.save(ignore_permissions=False)

    # Async notify IMM-04 stakeholders
    frappe.enqueue(
        "assetcore.services.imm03.notify_imm04_readiness",
        queue="default",
        timeout=300,
        por_name=doc.name,
    )
    return doc


def submit_por_for_review(por_name: str) -> Document:
    """Draft → Under Review."""
    doc = frappe.get_doc("Purchase Order Request", por_name)
    if doc.status != "Draft":
        frappe.throw(_("POR phải ở trạng thái Draft"))
    doc.status = "Under Review"
    doc.save(ignore_permissions=False)
    return doc


def confirm_por_delivery(por_name: str, delivery_notes: str = "") -> Document:
    """Released → Fulfilled: Storekeeper xác nhận hàng về kho, PP Item → Delivered (PATCH-05)."""
    doc = frappe.get_doc("Purchase Order Request", por_name)
    if doc.status != "Released":
        frappe.throw(_("POR phải ở trạng thái Released để xác nhận giao hàng"))
    doc.status = "Fulfilled"
    if doc.linked_plan_item:
        frappe.db.set_value("Procurement Plan Item", doc.linked_plan_item, "status", "Delivered")
    doc.save(ignore_permissions=False)
    return doc


# ─── Background Job ───────────────────────────────────────────────────────────

def notify_imm04_readiness(por_name: str) -> None:
    """Async: notify IMM-04 stakeholders khi POR Released."""
    try:
        por = frappe.get_doc("Purchase Order Request", por_name)
        msg_store = (
            f"POR {por_name} đã phát hành — "
            f"Chuẩn bị tiếp nhận: {por.equipment_description} "
            f"(SL: {por.quantity}) từ {por.vendor_name or por.vendor}. "
            f"Dự kiến giao: {por.expected_delivery_date or 'TBD'}"
        )
        msg_ops = f"Khởi động IMM-04 — {por.equipment_description} (POR: {por_name})"

        # Notify Storekeeper
        for u in frappe.get_all("Has Role", filters={"role": "IMM Storekeeper", "parenttype": "User"}, fields=["parent"]):
            frappe.publish_realtime("imm_notification", {"message": msg_store, "type": "info"}, user=u.parent)

        # Notify Ops Manager
        for u in frappe.get_all("Has Role", filters={"role": "IMM Operations Manager", "parenttype": "User"}, fields=["parent"]):
            frappe.publish_realtime("imm_notification", {"message": msg_ops, "type": "success"}, user=u.parent)

        # Notify Dept Head của khoa yêu cầu ban đầu (trace chain POR → PP Item → NA → dept)
        if por.linked_plan_item:
            na_name = frappe.db.get_value("Procurement Plan Item", por.linked_plan_item, "needs_assessment")
            if na_name:
                requesting_dept = frappe.db.get_value("Needs Assessment", na_name, "requesting_dept")
                if requesting_dept:
                    dept_head = frappe.db.get_value("AC Department", requesting_dept, "dept_head")
                    if dept_head:
                        frappe.publish_realtime(
                            "imm_notification",
                            {"message": f"Thiết bị cho khoa đã được đặt hàng: {por.equipment_description}", "type": "success"},
                            user=dept_head,
                        )
        frappe.logger().info(f"[IMM-03→IMM-04] notify_imm04_readiness complete: {por_name}")
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"notify_imm04_readiness failed: {por_name}")


# ─── Dashboard ────────────────────────────────────────────────────────────────

def get_planning_dashboard_data(year: str = "") -> dict:
    """Tổng hợp KPI cho IMM-01/02/03 Planning Dashboard."""
    if not year:
        year = str(frappe.utils.getdate().year)
    yr = int(year)
    date_range = [f"{yr}-01-01", f"{yr}-12-31"]

    # IMM-01 stats
    na_records = frappe.get_list(
        "Needs Assessment",
        filters=[["request_date", "between", date_range]],
        fields=["status", "estimated_budget", "approved_budget"],
        limit=10000,
    )
    na_by_status: dict = {}
    total_requested = total_approved_budget = 0.0
    for r in na_records:
        na_by_status[r.status] = na_by_status.get(r.status, 0) + 1
        total_requested += float(r.estimated_budget or 0)
        total_approved_budget += float(r.approved_budget or 0)
    na_approved = na_by_status.get("Approved", 0) + na_by_status.get("Planned", 0)
    na_total = len(na_records)

    # IMM-02 stats
    pp_records = frappe.get_list(
        "Procurement Plan",
        filters=[["plan_year", "=", yr]],
        fields=["name", "status", "approved_budget", "allocated_budget"],
        limit=100,
    )
    pp_approved_budget = sum(float(r.approved_budget or 0) for r in pp_records)
    pp_allocated = sum(float(r.allocated_budget or 0) for r in pp_records)

    # IMM-03 stats
    por_records = frappe.get_list(
        "Purchase Order Request",
        fields=["status", "total_amount"],
        limit=10000,
    )
    por_by_status: dict = {}
    por_total_value = 0.0
    for r in por_records:
        por_by_status[r.status] = por_by_status.get(r.status, 0) + 1
        por_total_value += float(r.total_amount or 0)

    return {
        "year": yr,
        "imm01": {
            "total": na_total,
            "by_status": na_by_status,
            "approval_rate": round(na_approved / na_total * 100, 1) if na_total else 0,
            "total_requested_budget": total_requested,
            "total_approved_budget": total_approved_budget,
        },
        "imm02": {
            "total_plans": len(pp_records),
            "approved_budget": pp_approved_budget,
            "allocated_budget": pp_allocated,
            "utilization_rate": round(pp_allocated / pp_approved_budget * 100, 1) if pp_approved_budget else 0,
        },
        "imm03": {
            "total_por": len(por_records),
            "por_by_status": por_by_status,
            "total_por_value": por_total_value,
        },
    }

