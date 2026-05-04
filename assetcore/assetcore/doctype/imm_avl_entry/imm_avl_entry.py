# Copyright (c) 2026, AssetCore Team
from __future__ import annotations
from frappe.model.document import Document
from assetcore.services import imm03 as svc


class IMMAVLEntry(Document):
    def validate(self):
        svc.validate_avl(self)

    def on_submit(self):
        svc.activate_avl(self)
