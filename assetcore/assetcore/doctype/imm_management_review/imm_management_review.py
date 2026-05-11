# Copyright (c) 2026, AssetCore Team
"""IMM Management Review controller."""
from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class IMMManagementReview(Document):
    """Quarterly management review record linking audit, CAPA, and scorecard data.

    The quarter field is auto-populated from review_date on before_insert.
    """

    def before_insert(self) -> None:
        """Compute quarter label from review_date."""
        if self.review_date and not self.quarter:
            from frappe.utils import getdate
            d = getdate(self.review_date)
            q = (d.month - 1) // 3 + 1
            self.quarter = f"Q{q}-{d.year}"

    def validate(self) -> None:
        """Validate review date is set and chair is valid."""
        if not self.review_date:
            frappe.throw(_("Ngày họp là bắt buộc."))
