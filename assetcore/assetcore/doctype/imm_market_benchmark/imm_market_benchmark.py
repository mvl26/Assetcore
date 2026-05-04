# Copyright (c) 2026, AssetCore Team
from __future__ import annotations
from frappe.model.document import Document
from assetcore.services import imm02 as svc


class IMMMarketBenchmark(Document):
    def validate(self):
        svc.validate_market_benchmark(self)
