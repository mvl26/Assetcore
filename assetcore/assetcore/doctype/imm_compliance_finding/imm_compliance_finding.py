# Copyright (c) 2026, AssetCore Team
"""IMM Compliance Finding — controller (Tier 3).

Logic nghiệp vụ ủy thác về `assetcore.services.imm16`.
"""
from __future__ import annotations

from frappe.model.document import Document

from assetcore.services import imm16 as svc


class IMMComplianceFinding(Document):
    def validate(self) -> None:
        svc.compliance_finding_validate(self)
