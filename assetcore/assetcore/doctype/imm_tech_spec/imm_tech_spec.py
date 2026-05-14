# Copyright (c) 2026, AssetCore Team
"""IMM Tech Spec — controller (delegate logic to services.imm02)."""
from __future__ import annotations

from frappe.model.document import Document

from assetcore.services import imm02 as svc


class IMMTechSpec(Document):
    def before_insert(self):
        svc.before_insert_tech_spec(self)

    def validate(self):
        svc.validate_tech_spec(self)

    def before_submit(self):
        svc.before_submit_tech_spec(self)

    def on_submit(self):
        svc.on_submit_tech_spec(self)
