# Copyright (c) 2026, AssetCore Team
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days


class PMSchedule(Document):
    def before_save(self) -> None:
        """Recalculate next_due_date whenever last_pm_date or interval changes."""
        if self.last_pm_date and self.pm_interval_days:
            self.next_due_date = add_days(self.last_pm_date, self.pm_interval_days)

    def validate(self) -> None:
        """Validate checklist template matches asset category (BR-08-01)."""
        if not self.checklist_template:
            frappe.throw(_("Template checklist l\u00e0 b\u1eaft bu\u1ed9c (BR-08-01)"))
        template = frappe.get_doc("PM Checklist Template", self.checklist_template)
        asset_category = frappe.db.get_value("Asset", self.asset_ref, "asset_category")
        if template.asset_category != asset_category:
            frappe.throw(_(
                "Template {0} kh\u00f4ng kh\u1edbp v\u1edbi lo\u1ea1i thi\u1ebft b\u1ecb {1}"
            ).format(self.checklist_template, asset_category))
