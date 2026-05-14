# Copyright (c) 2026, AssetCore Team
import frappe
from frappe.model.document import Document


class PMChecklistTemplate(Document):
    def before_save(self) -> None:
        self._auto_number_items()

    def _auto_number_items(self) -> None:
        """Auto-assign item_code sequence numbers to checklist items."""
        for i, item in enumerate(self.checklist_items or [], start=1):
            item.item_code = f"ITEM-{i:03d}"
