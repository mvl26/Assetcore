# Copyright (c) 2026, AssetCore Team
"""Repositories cho IMM-11 Calibration."""

from .base import BaseRepository


class CalibrationScheduleRepo(BaseRepository):
    DOCTYPE = "IMM Calibration Schedule"


class CalibrationRepo(BaseRepository):
    DOCTYPE = "IMM Asset Calibration"
