# Copyright (c) 2026, AssetCore Team
"""IMM Needs Request — controller (Tier 3).

Logic nghiệp vụ ủy thác về `assetcore.services.imm01`.
"""
from __future__ import annotations

from frappe.model.document import Document

from assetcore.services import imm01 as svc


class IMMNeedsRequest(Document):
    def before_insert(self):
        svc.before_insert_needs_request(self)

    def validate(self):
        svc.validate_needs_request(self)

    def before_submit(self):
        svc.before_submit_needs_request(self)

    def on_submit(self):
        svc.on_submit_needs_request(self)

    def on_cancel(self):
        svc.on_cancel_needs_request(self)
