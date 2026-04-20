# Copyright (c) 2026, AssetCore Team
from frappe.model.document import Document


class ACStockMovementItem(Document):
    def before_save(self):
        self.total_cost = float(self.qty or 0) * float(self.unit_cost or 0)
