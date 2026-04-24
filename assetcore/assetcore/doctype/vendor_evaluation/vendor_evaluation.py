"""Vendor Evaluation — IMM-03 controller."""
from __future__ import annotations
import frappe
from frappe import _
from frappe.model.document import Document


class VendorEvaluation(Document):
    """Controller cho IMM-03 Vendor Evaluation với weighted scoring."""

    def validate(self) -> None:
        self._calculate_scores()
        self._vr_05_recommend_justification()

    def before_submit(self) -> None:
        if not self.recommended_vendor:
            frappe.throw(_("Phải chọn nhà cung cấp được đề xuất trước khi phê duyệt"))
        if not self.committee_members or len((self.committee_members or "").strip()) < 5:
            frappe.throw(_("VR-03-03: Phải ghi tên thành viên hội đồng đánh giá"))

    def on_update_after_submit(self) -> None:
        # PATCH-04: 2-step approval — Tech Reviewer then Finance Officer
        if self.status == "Tech Reviewed":
            self.tech_reviewed_by = frappe.session.user
            self.tech_review_date = frappe.utils.today()
            _append_lifecycle(self, "vendor_evaluation_tech_reviewed", "In Progress", "Tech Reviewed")
            self.db_update()
        elif self.status == "Approved":
            self.approved_by = frappe.session.user
            self.approval_date = frappe.utils.today()
            _append_lifecycle(self, "vendor_selected", "Tech Reviewed", "Approved")
            self.db_update()
            _notify_ops_vendor_selected(self)

    def _calculate_scores(self) -> None:
        """D4: tính điểm có trọng số 40/30/20/10 cho từng nhà cung cấp."""
        for item in self.items or []:
            tech = float(item.technical_score or 0)
            fin = float(item.financial_score or 0)
            prof = float(item.profile_score or 0)
            risk = float(item.risk_score or 0)

            # clamp 0–10
            tech = max(0.0, min(10.0, tech))
            fin = max(0.0, min(10.0, fin))
            prof = max(0.0, min(10.0, prof))
            risk = max(0.0, min(10.0, risk))

            item.total_score = round(tech * 0.40 + fin * 0.30 + prof * 0.20 + risk * 0.10, 2)
            s = item.total_score
            item.score_band = (
                "A (≥8)" if s >= 8 else
                "B (6–7.9)" if s >= 6 else
                "C (4–5.9)" if s >= 4 else
                "D (<4)"
            )

    def _vr_05_recommend_justification(self) -> None:
        """VR-03-05: nếu không chọn vendor điểm cao nhất phải có lý do."""
        if not self.recommended_vendor or not self.items:
            return
        max_score = max((float(i.total_score or 0) for i in self.items), default=0)
        top_vendor = next(
            (i.vendor for i in self.items if float(i.total_score or 0) >= max_score), None
        )
        if top_vendor and self.recommended_vendor != top_vendor:
            if not self.selection_justification or len(self.selection_justification.strip()) < 20:
                frappe.throw(
                    _("VR-03-05: Nhà cung cấp được chọn không có điểm cao nhất — "
                      "phải ghi rõ lý do (ít nhất 20 ký tự) vào ô 'Lý do lựa chọn'")
                )



def _notify_ops_vendor_selected(doc: Document) -> None:
    msg = (
        f"Đánh giá NCC {doc.name} đã hoàn thành — "
        f"NCC được chọn: {doc.recommended_vendor}. "
        f"Có thể tạo Yêu cầu Mua sắm (POR)."
    )
    ops_managers = frappe.get_all(
        "Has Role",
        filters={"role": "IMM Operations Manager", "parenttype": "User"},
        fields=["parent"],
    )
    for u in ops_managers:
        frappe.publish_realtime(
            "imm_notification",
            {"message": msg, "type": "success"},
            user=u.parent,
        )


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
