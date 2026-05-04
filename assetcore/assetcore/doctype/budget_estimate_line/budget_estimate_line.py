# Copyright (c) 2026, AssetCore Team
"""Child table — Budget Estimate Line (IMM-01)."""
from frappe.model.document import Document


class BudgetEstimateLine(Document):
    def validate(self):
        self.amount = (self.qty or 0) * (self.unit_cost or 0)
