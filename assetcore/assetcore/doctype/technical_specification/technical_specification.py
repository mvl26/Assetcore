"""Technical Specification — IMM-03 controller."""
from __future__ import annotations
import frappe
from frappe import _
from frappe.model.document import Document


class TechnicalSpecification(Document):
    """Controller cho IMM-03 Technical Specification."""

    def validate(self) -> None:
        self._vr_02_regulatory_class()

    def before_submit(self) -> None:
        if not self.performance_requirements or len((self.performance_requirements or "").strip()) < 20:
            frappe.throw(_("Yêu cầu hiệu suất phải có ít nhất 20 ký tự"))
        if not self.safety_standards or len((self.safety_standards or "").strip()) < 10:
            frappe.throw(_("Tiêu chuẩn an toàn không được để trống"))

    def on_update_after_submit(self) -> None:
        if self.status == "Approved":
            self.reviewed_by = frappe.session.user
            self.review_date = frappe.utils.today()
            _append_lifecycle(self, "technical_spec_approved", "Under Review", "Approved")
            self.db_update()
            # Link back to NA if associated
            if self.needs_assessment:
                frappe.db.set_value(
                    "Needs Assessment", self.needs_assessment,
                    "technical_specification", self.name
                )

    def _vr_02_regulatory_class(self) -> None:
        """VR-03-02: regulatory_class bắt buộc (NĐ98/2021)."""
        if not self.regulatory_class:
            frappe.throw(_("VR-03-02: Phân loại NĐ98 (A/B/C/D) là bắt buộc"))


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
