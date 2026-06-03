# Copyright (c) 2026, AssetCore Team
from frappe.model.document import Document


class ACSparePartStock(Document):
    def autoname(self):
        # Composite key: warehouse::spare_part → also the `name`
        self.stock_key = f"{self.warehouse}::{self.spare_part}"
        self.name = self.stock_key

    def before_save(self):
        # IMM-15 §III-bis.5 — soft-reservation ledger.
        # available_qty = MAX(0, qty_on_hand − reserved_qty). Clamp at 0: reserved_qty
        # may transiently exceed qty_on_hand (e.g. a stock adjustment lowers on-hand
        # while an allocation still holds the bin), and a negative available_qty would
        # break VR-15-03 / KPI / FE. reserved_qty is itself floored at 0 (guard nulls).
        on_hand = float(self.qty_on_hand or 0)
        reserved = max(0.0, float(self.reserved_qty or 0))
        self.available_qty = max(0.0, on_hand - reserved)
