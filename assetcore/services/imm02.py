"""IMM-02 — Procurement Plan service layer."""
from __future__ import annotations
import frappe
from frappe import _


def create_procurement_plan(plan_year: int, approved_budget: float) -> Document:
    """Tạo Procurement Plan Draft mới."""
    _br_01_check_unique_locked_plan(int(plan_year))
    doc = frappe.get_doc({
        "doctype": "Procurement Plan",
        "plan_year": int(plan_year),
        "approved_budget": float(approved_budget),
        "status": "Draft",
    })
    doc.insert(ignore_permissions=False)
    return doc


def add_na_to_plan(
    plan_name: str,
    needs_assessment: str,
    planned_quarter: str = "",
    estimated_unit_cost: float = 0,
) -> Document:
    """Gắn Needs Assessment đã duyệt vào Procurement Plan.

    Thông tin thiết bị được lấy tự động từ NA.
    VR-02-03: NA phải ở trạng thái Approved.
    """
    doc = frappe.get_doc("Procurement Plan", plan_name)
    if doc.status != "Draft":
        frappe.throw(_("Chỉ có thể thêm nhu cầu khi kế hoạch ở trạng thái Draft"))

    if not needs_assessment:
        frappe.throw(_("VR-02-03: Phải chọn Phiếu nhu cầu mua sắm"))

    na = frappe.get_doc("Needs Assessment", needs_assessment)
    if na.status not in ("Approved", "Planned"):
        frappe.throw(
            _("VR-02-03: Phiếu {0} chưa được phê duyệt (trạng thái: {1})").format(
                needs_assessment, na.status
            )
        )

    # Kiểm tra trùng lặp
    for item in doc.items:
        if item.needs_assessment == needs_assessment:
            frappe.throw(
                _("Phiếu {0} đã có trong kế hoạch này").format(needs_assessment)
            )

    unit_cost = float(estimated_unit_cost) if estimated_unit_cost else (
        float(na.approved_budget or na.estimated_budget) / int(na.quantity or 1)
    )

    doc.append("items", {
        "needs_assessment": needs_assessment,
        "equipment_description": na.equipment_type,
        "quantity": int(na.quantity),
        "estimated_unit_cost": unit_cost,
        "priority": na.priority,
        "planned_quarter": planned_quarter or None,
        "status": "Pending",
    })
    doc.save(ignore_permissions=False)
    return doc


def submit_plan_for_review(plan_name: str) -> Document:
    """Draft → Under Review (VR-02-02: phải có ít nhất 1 item)."""
    doc = frappe.get_doc("Procurement Plan", plan_name)
    if doc.status != "Draft":
        frappe.throw(_("Kế hoạch phải ở trạng thái Draft"))
    if not doc.items:
        frappe.throw(_("VR-02-02: Kế hoạch chưa có dòng thiết bị nào"))
    doc.status = "Under Review"
    doc.save(ignore_permissions=False)
    return doc


def approve_plan(plan_name: str, notes: str = "") -> Document:
    """Under Review → Approved."""
    doc = frappe.get_doc("Procurement Plan", plan_name)
    if doc.status != "Under Review":
        frappe.throw(_("Kế hoạch phải ở trạng thái Under Review"))
    doc.status = "Approved"
    doc.approved_by = frappe.session.user
    doc.approval_date = frappe.utils.today()
    doc.approval_notes = notes
    doc.save(ignore_permissions=False)
    return doc


def lock_budget(plan_name: str) -> Document:
    """Approved → Budget Locked — set items → PO Raised, NA → Planned."""
    doc = frappe.get_doc("Procurement Plan", plan_name)
    if doc.status != "Approved":
        frappe.throw(_("Kế hoạch phải ở trạng thái Approved trước khi khóa ngân sách"))
    _br_01_check_unique_locked_plan(doc.plan_year, exclude=plan_name)
    doc.status = "Budget Locked"
    doc.save(ignore_permissions=False)
    # on_update_after_submit trong controller sẽ xử lý items + notify
    return doc


def get_approved_nas_for_plan(year: int) -> list[dict]:
    """Trả về Needs Assessments đã Approved trong năm, chưa có trong kế hoạch nào."""
    return frappe.get_list(
        "Needs Assessment",
        filters={
            "status": "Approved",
            "request_date": ["between", [f"{year}-01-01", f"{year}-12-31"]],
        },
        fields=["name", "requesting_dept", "equipment_type", "quantity",
                "estimated_budget", "approved_budget", "priority"],
        order_by="priority asc, request_date asc",
        limit=500,
    )


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _br_01_check_unique_locked_plan(plan_year: int, exclude: str = "") -> None:
    """BR-02-01: Mỗi năm chỉ 1 PP ở Approved hoặc Budget Locked."""
    filters = {
        "plan_year": plan_year,
        "status": ["in", ["Approved", "Budget Locked"]],
    }
    if exclude:
        filters["name"] = ["!=", exclude]
    existing = frappe.db.get_value("Procurement Plan", filters, "name")
    if existing:
        frappe.throw(
            _("BR-02-01: Năm {0} đã có kế hoạch đang hoạt động: {1}").format(plan_year, existing)
        )


