# Copyright (c) 2026, AssetCore Team
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate, date_diff, add_days


class PMWorkOrder(Document):
    def validate(self) -> None:
        """Run all business rule validations before save."""
        self._validate_checklist_complete()
        self._validate_photo_for_high_risk()
        self._validate_cm_source()

    def on_submit(self) -> None:
        """Execute post-submit lifecycle actions."""
        self._set_completion()
        self._update_pm_schedule()
        self._update_asset_fields()
        self._create_pm_task_log()
        self._handle_failures()

    def _validate_checklist_complete(self) -> None:
        """Ensure all checklist items have results before completion (BR-08-08)."""
        if self.status not in ("Completed", "Halted\u2013Major Failure"):
            return
        for item in (self.checklist_results or []):
            if not item.result:
                frappe.throw(_(
                    "T\u1ea5t c\u1ea3 m\u1ee5c checklist ph\u1ea3i c\u00f3 k\u1ebft qu\u1ea3 tr\u01b0\u1edbc khi Submit (BR-08-08). "
                    "M\u1ee5c '{0}' ch\u01b0a \u0111i\u1ec1n."
                ).format(item.description))

    def _validate_photo_for_high_risk(self) -> None:
        """Require photo attachments for high-risk device classes (BR-08-06)."""
        risk_class = frappe.db.get_value("AC Asset", self.asset_ref, "risk_classification")
        if risk_class in ("High", "Critical") and not self.attachments:
            frappe.throw(_(
                "Thi\u1ebft b\u1ecb nguy c\u01a1 cao ({0}) b\u1eaft bu\u1ed9c upload \u1ea3nh tr\u01b0\u1edbc/sau PM (BR-08-06)."
            ).format(risk_class))

    def _validate_cm_source(self) -> None:
        """Corrective work orders must reference the originating PM WO (BR-08-02)."""
        if self.wo_type == "Corrective" and not self.source_pm_wo:
            frappe.throw(_("CM Work Order ph\u1ea3i c\u00f3 tham chi\u1ebfu PM WO g\u1ed1c (BR-08-02)."))

    def _set_completion(self) -> None:
        """Record completion date and determine if PM was completed late."""
        self.completion_date = nowdate()
        if self.due_date:
            self.is_late = 1 if date_diff(self.completion_date, self.due_date) > 0 else 0

    def _update_pm_schedule(self) -> None:
        """Advance the PM Schedule last/next dates based on this completion."""
        if not self.pm_schedule:
            return
        sched = frappe.get_doc("PM Schedule", self.pm_schedule)
        sched.last_pm_date = self.completion_date
        sched.next_due_date = add_days(self.completion_date, sched.pm_interval_days)
        sched.save(ignore_permissions=True)

    def _update_asset_fields(self) -> None:
        """Sync PM-related first-class fields on the AC Asset record (v3)."""
        sched_interval = frappe.db.get_value("PM Schedule", self.pm_schedule, "pm_interval_days") or 0
        frappe.db.set_value("AC Asset", self.asset_ref, {
            "last_pm_date": self.completion_date,
            "next_pm_date": add_days(self.completion_date, sched_interval),
        })

    def _create_pm_task_log(self) -> None:
        """Create an immutable audit record for this PM completion."""
        days_late = date_diff(self.completion_date, self.due_date) if self.is_late else 0
        sched_interval = frappe.db.get_value("PM Schedule", self.pm_schedule, "pm_interval_days") or 0
        frappe.get_doc({
            "doctype": "PM Task Log",
            "asset_ref": self.asset_ref,
            "pm_work_order": self.name,
            "pm_type": self.pm_type,
            "completion_date": self.completion_date,
            "technician": self.assigned_to or frappe.session.user,
            "overall_result": self.overall_result,
            "is_late": self.is_late,
            "days_late": days_late,
            "next_pm_date": add_days(self.completion_date, sched_interval),
            "summary": self.technician_notes or "",
        }).insert(ignore_permissions=True)

    def _handle_failures(self) -> None:
        """Auto-create CM Work Orders for failed checklist items."""
        has_minor = any(r.result == "Fail\u2013Minor" for r in (self.checklist_results or []))
        has_major = any(r.result == "Fail\u2013Major" for r in (self.checklist_results or []))

        if has_major:
            self._create_cm_wo(priority="Critical")
            # v3: use transition_asset_status for lifecycle change + audit trail
            from assetcore.services.imm00 import transition_asset_status
            transition_asset_status(
                self.asset_ref, "Out of Service",
                reason=f"PM {self.name}: Major failure detected",
                root_doctype="PM Work Order", root_record=self.name,
            )
            self.db_set("status", "Halted\u2013Major Failure")
        elif has_minor:
            self._create_cm_wo(priority="Medium")

    def _create_cm_wo(self, priority: str) -> None:
        """Insert a Corrective PM Work Order referencing this PM WO."""
        failure_items = [
            r.description for r in (self.checklist_results or [])
            if r.result in ("Fail\u2013Minor", "Fail\u2013Major")
        ]
        frappe.get_doc({
            "doctype": "PM Work Order",
            "asset_ref": self.asset_ref,
            "pm_schedule": self.pm_schedule,
            "pm_type": self.pm_type,
            "wo_type": "Corrective",
            "source_pm_wo": self.name,
            "status": "Open",
            "due_date": nowdate(),
            "technician_notes": "T\u1ea1o t\u1ef1 \u0111\u1ed9ng t\u1eeb PM failure. L\u1ed7i: " + "; ".join(failure_items),
        }).insert(ignore_permissions=True)
