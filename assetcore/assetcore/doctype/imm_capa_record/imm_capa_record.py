# Copyright (c) 2026, AssetCore Team
"""IMM CAPA Record — controller (Tier 3).

Logic nghiệp vụ ủy thác về `assetcore.services.imm16`.
"""
from __future__ import annotations

from frappe.model.document import Document

from assetcore.services import imm16 as svc


class IMMCAPARecord(Document):
    def validate(self) -> None:
        svc.capa_record_validate(self)

    def before_submit(self) -> None:
        svc.capa_record_before_submit(self)

    def on_update(self) -> None:
        svc.capa_record_on_update(self)
