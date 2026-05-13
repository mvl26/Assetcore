# Copyright (c) 2026, AssetCore Team
from __future__ import annotations
from frappe.model.document import Document
from assetcore.services import imm03 as svc


class IMMProcurementDecision(Document):
    def validate(self):
        svc.validate_decision(self)

    def before_submit(self):
        svc.before_submit_decision(self)

    def on_submit(self):
        svc.on_submit_decision(self)

    def on_cancel(self):
        svc.on_cancel_decision(self)
