# Copyright (c) 2026, AssetCore Team
"""IMM Internal Audit — controller (Tier 3).

Logic nghiệp vụ ủy thác về `assetcore.services.imm16`.
"""
from __future__ import annotations

from frappe.model.document import Document

from assetcore.services import imm16 as svc


class IMMInternalAudit(Document):
    def validate(self) -> None:
        svc.validate_internal_audit(self)

    def on_update(self) -> None:
        svc.on_update_internal_audit(self)
