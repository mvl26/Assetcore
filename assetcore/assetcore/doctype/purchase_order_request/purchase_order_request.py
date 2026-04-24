"""Purchase Order Request — IMM-03 controller."""
from __future__ import annotations
import frappe
from frappe import _
from frappe.model.document import Document


class PurchaseOrderRequest(Document):
    """Controller cho IMM-03 Purchase Order Request."""

    def validate(self) -> None:
        self._calc_total_amount()
        self._vr_06_budget_variance()
        self._vr_07_vendor_match()
        self._br_01_set_director_flag()

    def before_submit(self) -> None:
        if not self.linked_plan_item:
            frappe.throw(_("POR phải liên kết với Dòng kế hoạch mua sắm"))
        if not self.linked_evaluation:
            frappe.throw(_("POR phải liên kết với Phiếu đánh giá nhà cung cấp"))

    def on_update_after_submit(self) -> None:
        if self.status == "Approved":
            self.approved_by = frappe.session.user
            self.approval_date = frappe.utils.today()
            _append_lifecycle(self, "por_approved", "Under Review", "Approved")
            self.db_update()
        elif self.status == "Released":
            self.release_date = frappe.utils.today()
            self.released_by = frappe.session.user
            _append_lifecycle(self, "por_released", "Approved", "Released")
            self._update_plan_item_ordered()
            self.db_update()
            frappe.enqueue(
                "assetcore.services.imm03.notify_imm04_readiness",
                queue="default",
                timeout=300,
                por_name=self.name,
            )
        elif self.status == "Fulfilled":                              # PATCH-05
            _update_plan_item_status(self, "Delivered")
            _append_lifecycle(self, "por_fulfilled", "Released", "Fulfilled",
                              notes="Storekeeper confirmed delivery")
            self.db_update()
        elif self.status == "Cancelled":
            _append_lifecycle(self, "por_cancelled", self.get_db_value("status"), "Cancelled")
            self.db_update()

    def _calc_total_amount(self) -> None:
        qty = float(self.quantity or 0)
        price = float(self.unit_price or 0)
        self.total_amount = qty * price

    def _vr_06_budget_variance(self) -> None:
        """VR-03-06: total_amount ≤ PP item total_cost × 1.10."""
        if not self.linked_plan_item:
            return
        item_cost = frappe.db.get_value("Procurement Plan Item", self.linked_plan_item, "total_cost") or 0
        if item_cost and (self.total_amount or 0) > float(item_cost) * 1.10:
            frappe.throw(
                _("VR-03-06: Giá trị POR ({0:,.0f}) vượt quá 110% ngân sách dòng kế hoạch ({1:,.0f})").format(
                    self.total_amount, item_cost
                )
            )

    def _vr_07_vendor_match(self) -> None:
        """VR-03-07: Vendor phải là recommended_vendor của VE (trừ khi có ghi chú giải trình)."""
        if not self.linked_evaluation or not self.vendor:
            return
        recommended = frappe.db.get_value("Vendor Evaluation", self.linked_evaluation, "recommended_vendor")
        if recommended and self.vendor != recommended and not self.cancellation_reason:
            frappe.throw(
                _("VR-03-07: Nhà cung cấp không khớp với đề xuất ({0}). Điền lý do vào ô 'Lý do hủy/giải trình' nếu cố ý chọn khác.").format(recommended)
            )

    def _br_01_set_director_flag(self) -> None:
        """BR-03-01: tự động đặt cờ cần Giám đốc ký khi > 500 triệu."""
        self.requires_director_approval = 1 if (self.total_amount or 0) > 500_000_000 else 0

    def _update_plan_item_ordered(self) -> None:
        _update_plan_item_status(self, "Ordered")
        if self.linked_plan_item:
            frappe.db.set_value("Procurement Plan Item", self.linked_plan_item, "por_reference", self.name)


def _update_plan_item_status(doc: Document, new_status: str) -> None:
    """PATCH-05: Update PP Item status (Ordered or Delivered)."""
    if doc.linked_plan_item:
        frappe.db.set_value("Procurement Plan Item", doc.linked_plan_item, "status", new_status)


def _append_lifecycle(
    doc: Document, event_type: str, from_status: str, to_status: str, notes: str = ""
) -> None:
    doc.append(
        "lifecycle_events",
        {
            "event_type": event_type,
            "event_domain": "imm_planning",
            "from_status": from_status,
            "to_status": to_status,
            "actor": frappe.session.user,
            "event_timestamp": frappe.utils.now(),
            "notes": notes,
        },
    )
