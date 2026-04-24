"""Needs Assessment — IMM-01 controller."""
import frappe
from frappe import _
from frappe.model.document import Document


class NeedsAssessment(Document):
    """Controller for IMM-01 Needs Assessment DocType."""

    def validate(self) -> None:
        """Run validation rules before save."""
        _vr02_budget_range(self)
        _vr03_quantity_range(self)
        if self.status not in ("Draft", None):
            _vr04_justification_length(self)
        _vr01_duplicate_check(self)

    def on_submit(self) -> None:
        """Create lifecycle event on submit (Approved state)."""
        _append_lifecycle_event(self, "approved", "Under Review", "Approved")

    def on_cancel(self) -> None:
        """Lifecycle event on cancel."""
        _append_lifecycle_event(self, "cancelled", self.status, "Cancelled")


# ─── Validation helpers ───────────────────────────────────────────────────────

def _vr02_budget_range(doc: Document) -> None:
    """VR-01-02: Dự toán phải > 0 và ≤ 50 tỷ."""
    if not doc.estimated_budget or doc.estimated_budget <= 0:
        frappe.throw(_("VR-01-02: Dự toán phải lớn hơn 0"))
    if doc.estimated_budget > 50_000_000_000:
        frappe.throw(_("VR-01-02: Dự toán vượt giới hạn 50 tỷ VND cho một phiếu"))


def _vr03_quantity_range(doc: Document) -> None:
    """VR-01-03: Số lượng phải từ 1 đến 100."""
    qty = doc.quantity or 0
    if qty < 1 or qty > 100:
        frappe.throw(_("VR-01-03: Số lượng phải từ 1 đến 100. Trên 100 vui lòng tách phiếu"))


def _vr04_justification_length(doc: Document) -> None:
    """VR-01-04: Lý do y tế ≥ 50 ký tự khi nộp."""
    text = (doc.clinical_justification or "").replace("<[^>]+>", "").strip()
    if len(text) < 50:
        frappe.throw(_("VR-01-04: Lý do y tế phải chi tiết ít nhất 50 ký tự (hiện có {0})").format(len(text)))


def _vr01_duplicate_check(doc: Document) -> None:
    """VR-01-01: Cảnh báo nếu cùng khoa + loại thiết bị đang xử lý trong năm."""
    if not doc.requesting_dept or not doc.equipment_type or not doc.request_date:
        return
    year = str(doc.request_date)[:4] if doc.request_date else ""
    existing = frappe.db.sql(
        """SELECT name FROM `tabNeeds Assessment`
           WHERE requesting_dept=%s AND equipment_type=%s
             AND YEAR(request_date)=%s AND status IN ('Draft','Submitted','Under Review')
             AND name != %s LIMIT 1""",
        (doc.requesting_dept, doc.equipment_type, year, doc.name or ""),
        as_dict=True,
    )
    if existing:
        frappe.msgprint(
            _("VR-01-01: Khoa đã có yêu cầu tương tự đang xử lý: {0}").format(existing[0].name),
            alert=True,
        )


# ─── Lifecycle event helper ───────────────────────────────────────────────────

def _append_lifecycle_event(
    doc: Document, event_type: str, from_status: str, to_status: str, notes: str = ""
) -> None:
    """Append an immutable lifecycle event row."""
    doc.append(
        "lifecycle_events",
        {
            "event_type": event_type,
            "from_status": from_status,
            "to_status": to_status,
            "actor": frappe.session.user,
            "event_timestamp": frappe.utils.now(),
            "notes": notes,
        },
    )
