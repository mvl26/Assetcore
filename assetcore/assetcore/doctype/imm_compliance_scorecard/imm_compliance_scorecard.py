# Copyright (c) 2026, AssetCore Team
"""IMM Compliance Scorecard controller."""
from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class IMMComplianceScorecard(Document):
    """Monthly compliance scorecard aggregated from IMM Compliance Findings.

    VR-09: once published (is_published=1), score_pct and non_compliant_count
    become immutable.  Create a new restate_of document to correct errors.
    """

    def validate(self) -> None:
        """VR-09: immutable after publish."""
        from assetcore.services.imm16 import validate_scorecard_immutability
        validate_scorecard_immutability(self)
