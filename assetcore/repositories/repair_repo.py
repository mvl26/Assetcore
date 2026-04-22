# Copyright (c) 2026, AssetCore Team
"""Repositories cho IMM-09 Repair + IMM-12 Incident."""

from .base import BaseRepository


class RepairRepo(BaseRepository):
    DOCTYPE = "Asset Repair"


class IncidentRepo(BaseRepository):
    DOCTYPE = "Incident Report"


class FirmwareChangeRequestRepo(BaseRepository):
    DOCTYPE = "Firmware Change Request"


class SparePartsUsedRepo(BaseRepository):
    DOCTYPE = "Spare Parts Used"
