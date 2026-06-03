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
        """Compute quarter label from review_date (legacy hook, keeps insert-time
        behaviour). Real enforcement is now in ``validate()`` so every save
        re-derives quarter and corrects bulk-updated rows.
        """
        if self.review_date and not self.quarter:
            self._recompute_quarter()

    def validate(self) -> None:
        """Validate review date is set and chair is valid.

        Always re-derives ``quarter`` from ``review_date`` so legacy rows
        with bad seed data are corrected on next save.
        """
        if not self.review_date:
            frappe.throw(_("Ngày họp là bắt buộc."))
        self._recompute_quarter()

    def _recompute_quarter(self) -> None:
        """Set ``self.quarter`` from ``self.review_date``."""
        if not self.review_date:
            return
        from frappe.utils import getdate
        d = getdate(self.review_date)
        q = (d.month - 1) // 3 + 1
        self.quarter = f"Q{q}-{d.year}"
