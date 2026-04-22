# Copyright (c) 2026, AssetCore Team
import frappe
from frappe.model.document import Document


class IMMRCARecord(Document):
    def before_save(self):
        if self.status == "Completed" and not self.completed_date:
            from frappe.utils import today
            self.completed_date = today()
        if not self.root_cause and self.five_why_steps:
            last = sorted(self.five_why_steps, key=lambda r: r.why_number or 0)
            if last:
                self.root_cause = last[-1].why_answer or ""
