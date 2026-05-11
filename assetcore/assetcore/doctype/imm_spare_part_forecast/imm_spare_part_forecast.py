# Copyright (c) 2026, AssetCore Team
import frappe
from frappe.model.document import Document


class IMMSparePartForecast(Document):
    def before_insert(self) -> None:
        """Set generated_by to current user."""
        if not self.generated_by:
            self.generated_by = frappe.session.user

    def on_submit(self) -> None:
        """Record approval on submit."""
        from assetcore.services.imm15 import record_forecast_approval
        record_forecast_approval(self)
