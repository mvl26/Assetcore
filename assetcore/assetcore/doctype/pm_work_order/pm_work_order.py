# Copyright (c) 2026, AssetCore Team
import frappe
from frappe import _
from frappe.model.document import Document


class PMWorkOrder(Document):
    def validate(self) -> None:
        """Delegate all business rule validations to service layer (imm08)."""
        from assetcore.services.imm08 import validate_work_order
        validate_work_order(self)

    def on_submit(self) -> None:
        """Delegate all post-submit lifecycle actions to service layer (imm08)."""
        from assetcore.services.imm08 import handle_work_order_submit
        handle_work_order_submit(self)
