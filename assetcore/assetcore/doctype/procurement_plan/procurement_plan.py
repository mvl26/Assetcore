"""Procurement Plan — IMM-02 controller."""
import frappe
from frappe import _
from frappe.model.document import Document


class ProcurementPlan(Document):
    """Controller for IMM-02 Procurement Plan DocType."""

    def validate(self) -> None:
        """Recalculate totals and run validation rules."""
        _calculate_totals(self)
        _vr01_budget_overrun(self)
        _vr02_items_required_on_submit(self)
        _vr03_linked_nas_approved(self)

    def on_submit(self) -> None:
        """Lifecycle event on final submit."""
        _append_lifecycle_event(self, "plan_approved", "Under Review", "Approved")

    def on_update_after_submit(self) -> None:
        if self.status == "Budget Locked":
            _set_items_po_raised(self)
            _notify_ops_manager_budget_locked(self)


def _calculate_totals(doc: Document) -> None:
    """Compute item total_cost and plan allocated/remaining budgets."""
    allocated = 0.0
    for item in doc.items or []:
        qty = float(item.quantity or 1)
        unit = float(item.estimated_unit_cost or 0)
        item.total_cost = qty * unit
        allocated += item.total_cost
    doc.allocated_budget = allocated
    doc.remaining_budget = float(doc.approved_budget or 0) - allocated


def _vr01_budget_overrun(doc: Document) -> None:
    """VR-02-01: Allocated ≤ approved_budget."""
    if (doc.allocated_budget or 0) > (doc.approved_budget or 0):
        frappe.throw(
            _("VR-02-01: Tổng phân bổ ({0:,.0f}) vượt ngân sách được duyệt ({1:,.0f})").format(
                doc.allocated_budget, doc.approved_budget
            )
        )


def _vr02_items_required_on_submit(doc: Document) -> None:
    """VR-02-02: At least 1 item when submitting."""
    if doc.docstatus == 1 and not doc.items:
        frappe.throw(_("VR-02-02: Kế hoạch chưa có thiết bị nào"))


def _vr03_linked_nas_approved(doc: Document) -> None:
    """VR-02-03: Linked Needs Assessments must be Approved."""
    for item in doc.items or []:
        if item.needs_assessment:
            na_status = frappe.db.get_value("Needs Assessment", item.needs_assessment, "status")
            if na_status not in ("Approved", "Planned"):
                frappe.throw(
                    _("VR-02-03: Phiếu đánh giá nhu cầu {0} chưa được phê duyệt (status: {1})").format(
                        item.needs_assessment, na_status
                    )
                )


def _set_items_po_raised(doc: Document) -> None:
    """PATCH-01: Set items to PO Raised and propagate NA.status → Planned on budget lock."""
    for item in doc.items or []:
        if item.status == "Pending":
            frappe.db.set_value("Procurement Plan Item", item.name, "status", "PO Raised")
            if item.needs_assessment:
                na_status = frappe.db.get_value(
                    "Needs Assessment", item.needs_assessment, "status"
                )
                if na_status == "Approved":
                    frappe.db.set_value(
                        "Needs Assessment", item.needs_assessment, "status", "Planned"
                    )


def _notify_ops_manager_budget_locked(doc: Document) -> None:
    """PATCH-03: Notify Ops Managers when PP budget is locked."""
    n_items = len([i for i in doc.items or [] if i.status in ("PO Raised", "Pending")])
    msg = (
        f"PP {doc.name} đã khóa ngân sách — "
        f"Cần tạo Đặc tả Kỹ thuật cho {n_items} dòng thiết bị."
    )
    ops_managers = frappe.get_all(
        "Has Role",
        filters={"role": "IMM Operations Manager", "parenttype": "User"},
        fields=["parent"],
    )
    for u in ops_managers:
        frappe.publish_realtime(
            "imm_notification",
            {
                "message": msg,
                "type": "info",
                "link": f"/planning/procurement-plans/{doc.name}",
            },
            user=u.parent,
        )


def _append_lifecycle_event(doc: Document, event_type: str, from_s: str, to_s: str) -> None:
    """Append an immutable lifecycle event row."""
    doc.append(
        "lifecycle_events",
        {
            "event_type": event_type,
            "from_status": from_s,
            "to_status": to_s,
            "actor": frappe.session.user,
            "event_timestamp": frappe.utils.now(),
        },
    )
