# Copyright (c) 2026, AssetCore Team
from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today


class IMMRCARecord(Document):
    """IMM-12 RCA Record — Root Cause Analysis cho sự cố chronic / High-Critical."""

    def validate(self) -> None:
        self._validate_assignment()
        self._validate_five_why_when_method_5why()
        self._validate_completion_requirements()

    def before_save(self) -> None:
        if self.status == "Completed" and not self.completed_date:
            self.completed_date = today()
        if self.status == "Completed" and not self.completed_by:
            self.completed_by = frappe.session.user
        if not self.root_cause and self.get("five_why_steps"):
            last = sorted(self.five_why_steps, key=lambda r: r.why_number or 0)
            if last:
                self.root_cause = last[-1].why_answer or ""

    def on_submit(self) -> None:
        if self.status != "Completed":
            frappe.throw(
                _("RCA chỉ có thể submit khi đã ở trạng thái Completed. Hiện tại: {0}").format(self.status)
            )
        self._mark_incident_rca_done()
        self._log_lifecycle_event()

    # ───────── validations ─────────

    def _validate_assignment(self) -> None:
        if self.status in ("RCA In Progress", "Completed") and not self.assigned_to:
            frappe.throw(_("Phải gán người phụ trách RCA (assigned_to) trước khi tiến hành phân tích."))

    def _validate_five_why_when_method_5why(self) -> None:
        method = (self.rca_method or "").lower()
        if "why" not in method:
            return
        if self.status not in ("RCA In Progress", "Completed"):
            return
        steps = self.get("five_why_steps") or []
        if len(steps) < 5:
            frappe.throw(
                _("Phương pháp 5 Whys yêu cầu đủ 5 bước phân tích. Hiện có {0}.").format(len(steps))
            )
        for row in steps:
            if not (row.why_question and row.why_answer):
                frappe.throw(
                    _("Bước {0}: phải điền đầy đủ câu hỏi và câu trả lời.").format(row.why_number or row.idx)
                )

    def _validate_completion_requirements(self) -> None:
        if self.status != "Completed":
            return
        if not self.root_cause:
            frappe.throw(_("Không thể đánh dấu hoàn thành: thiếu Root Cause."))
        if not (self.corrective_action_summary or self.linked_capa):
            frappe.throw(_("Không thể đánh dấu hoàn thành: cần CAPA hoặc tóm tắt hành động khắc phục."))

    # ───────── side-effects ─────────

    def _mark_incident_rca_done(self) -> None:
        """Khi RCA hoàn tất, mở khóa cho Incident Report đóng (BR-12-02)."""
        if not self.incident_report:
            return
        if not frappe.db.exists("Incident Report", self.incident_report):
            return
        frappe.db.set_value(
            "Incident Report", self.incident_report,
            {"requires_rca": 0},
            update_modified=False,
        )

    def _log_lifecycle_event(self) -> None:
        """Ghi Lifecycle Event để traceability (CLAUDE.md #10)."""
        if not self.asset:
            return
        try:
            frappe.get_doc({
                "doctype": "Asset Lifecycle Event",
                "asset": self.asset,
                "event_type": "rca_completed",
                "actor": frappe.session.user,
                "from_state": "RCA In Progress",
                "to_state": "Completed",
                "root_record_doctype": "IMM RCA Record",
                "root_record": self.name,
                "remarks": f"RCA hoàn tất - Root cause: {(self.root_cause or '')[:140]}",
            }).insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(f"RCA lifecycle log failed: {e}", "IMM-12 RCA")
