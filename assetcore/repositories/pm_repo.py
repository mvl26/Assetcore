# Copyright (c) 2026, AssetCore Team
"""Repositories cho IMM-08 Preventive Maintenance."""

from .base import BaseRepository


class PMScheduleRepo(BaseRepository):
    DOCTYPE = "PM Schedule"


class PMWorkOrderRepo(BaseRepository):
    DOCTYPE = "PM Work Order"


class PMChecklistTemplateRepo(BaseRepository):
    DOCTYPE = "PM Checklist Template"


class PMTaskLogRepo(BaseRepository):
    DOCTYPE = "PM Task Log"
