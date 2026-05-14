# Copyright (c) 2026, AssetCore Team
"""IMM Procurement Plan — controller."""
from __future__ import annotations

from frappe.model.document import Document

from assetcore.services import imm01 as svc


class IMMProcurementPlan(Document):
    def validate(self):
        svc.validate_procurement_plan(self)

    def on_submit(self):
        svc.on_submit_procurement_plan(self)
