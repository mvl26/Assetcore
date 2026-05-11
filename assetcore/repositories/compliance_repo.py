# Copyright (c) 2026, AssetCore Team
"""IMM-16 Compliance Monitoring — Repository layer."""
from __future__ import annotations

import frappe

from assetcore.repositories.base import BaseRepository


class ComplianceRuleRepo(BaseRepository):
    """Repository cho IMM Compliance Rule."""
    DOCTYPE = "IMM Compliance Rule"

    @classmethod
    def get_active_rules(cls, evaluation_frequency: list[str] | None = None) -> list[dict]:
        """Trả list active rules, tuỳ chọn lọc theo evaluation_frequency."""
        filters: dict = {"is_active": 1}
        if evaluation_frequency:
            filters["evaluation_frequency"] = ("in", evaluation_frequency)
        rows, _ = cls.list(
            filters=filters,
            fields=["name", "rule_code", "rule_name", "source_module",
                    "category", "severity", "threshold_definition",
                    "evaluation_frequency", "data_source_doctype",
                    "data_source_field"],
            page_size=500,
        )
        return rows


class ComplianceFindingRepo(BaseRepository):
    """Repository cho IMM Compliance Finding."""
    DOCTYPE = "IMM Compliance Finding"

    @classmethod
    def find_existing(cls, rule: str, source_record: str, evaluation_date: str) -> str | None:
        """Idempotent check — tránh tạo trùng Finding."""
        return frappe.db.exists(
            cls.DOCTYPE,
            {"rule": rule, "source_record": source_record,
             "evaluation_date": evaluation_date},
        )


class InternalAuditRepo(BaseRepository):
    """Repository cho IMM Internal Audit."""
    DOCTYPE = "IMM Internal Audit"


class ComplianceScorecardRepo(BaseRepository):
    """Repository cho IMM Compliance Scorecard."""
    DOCTYPE = "IMM Compliance Scorecard"

    @classmethod
    def find_by_period(cls, year: int, month: int, scope: str = "Hospital") -> dict | None:
        """Tìm scorecard theo kỳ."""
        return cls.find_one(
            {"period_year": year, "period_month": month, "scope": scope},
            fields=["name", "score_pct", "is_published"],
        )
