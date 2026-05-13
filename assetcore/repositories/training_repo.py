# Copyright (c) 2026, AssetCore Team
"""IMM-06 Training & Competency — Repository layer."""
from __future__ import annotations

import frappe

from assetcore.repositories.base import BaseRepository


class TrainingProgramRepo(BaseRepository):
    """Repository cho IMM Training Program."""
    DOCTYPE = "IMM Training Program"


class TrainingSessionRepo(BaseRepository):
    """Repository cho IMM Training Session."""
    DOCTYPE = "IMM Training Session"


class TrainingParticipantRepo(BaseRepository):
    """Repository cho IMM Training Participant (child)."""
    DOCTYPE = "IMM Training Participant"


class UserCompetencyRepo(BaseRepository):
    """Repository cho IMM User Competency."""
    DOCTYPE = "IMM User Competency"

    @classmethod
    def find_active_for_user_model(cls, user: str, device_model: str) -> dict | None:
        """Tìm competency Active/Expiring cho (user, device_model)."""
        return cls.find_one(
            {"user": user, "device_model": device_model,
             "workflow_state": ["in", ["Active", "Expiring"]]},
            fields=["name", "workflow_state", "expiry_date",
                    "competency_level", "recertification_due_date"],
        )

    @classmethod
    def find_all_active_for_user_model(cls, user: str, device_model: str,
                                        exclude: str = "") -> list[dict]:
        """Trả list Active competency cho (user × device_model) trừ exclude."""
        filters: dict = {"user": user, "device_model": device_model,
                         "workflow_state": "Active"}
        if exclude:
            filters["name"] = ("!=", exclude)
        rows, _ = cls.list(filters=filters, fields=["name"], page_size=100)
        return rows


class CompetencyAlertLogRepo(BaseRepository):
    """Repository cho IMM Competency Alert Log."""
    DOCTYPE = "IMM Competency Alert Log"

    @classmethod
    def alert_exists(cls, competency: str, alert_date: str, milestone: int) -> bool:
        """Kiểm tra idempotent — alert đã gửi chưa."""
        return bool(frappe.db.exists(
            cls.DOCTYPE,
            {"competency": competency, "alert_date": alert_date,
             "milestone": str(milestone)},
        ))


class GapReportRepo(BaseRepository):
    """Repository cho IMM Competency Gap Report."""
    DOCTYPE = "IMM Competency Gap Report"
