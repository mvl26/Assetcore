# Copyright (c) 2026, AssetCore Team
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import nowdate, getdate


class IMMCAPARecord(Document):
    def validate(self) -> None:
        self._validate_dates()
        if not self.capa_number:
            self.capa_number = self.name

    def _validate_dates(self) -> None:
        if self.due_date and self.opened_date and getdate(self.due_date) < getdate(self.opened_date):
            frappe.throw(_("due_date phải >= opened_date."))
        if self.closed_date and self.opened_date and getdate(self.closed_date) < getdate(self.opened_date):
            frappe.throw(_("closed_date phải >= opened_date."))

    def before_submit(self) -> None:
        if not (self.root_cause and self.root_cause.strip()):
            frappe.throw(_("Phải điền Root Cause trước khi submit CAPA (BR-00-08)."))
        if not (self.corrective_action and self.corrective_action.strip()):
            frappe.throw(_("Phải điền Corrective Action trước khi submit CAPA (BR-00-08)."))
        if not (self.preventive_action and self.preventive_action.strip()):
            frappe.throw(_("Phải điền Preventive Action trước khi submit CAPA (BR-00-08)."))
        if self.status != "Closed":
            self.status = "Closed"
        if not self.closed_date:
            self.closed_date = nowdate()
