# Copyright (c) 2026, AssetCore Team
from frappe.model.document import Document


class ACSparePartStock(Document):
    def autoname(self):
        # Composite key: warehouse::spare_part → also the `name`
        self.stock_key = f"{self.warehouse}::{self.spare_part}"
        self.name = self.stock_key

    def before_save(self):
        self.available_qty = float(self.qty_on_hand or 0) - float(self.reserved_qty or 0)
