# Copyright (c) 2026, AssetCore Team
"""IMM Critical Spare Watchlist controller."""
from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class IMMCriticalSpareWatchlist(Document):
    def validate(self) -> None:
        """Validate min_required_on_hand > 0."""
        if float(self.min_required_on_hand or 0) <= 0:
            frappe.throw(_("Tồn tối thiểu phải > 0"))
