# Copyright (c) 2026, AssetCore Team
"""Repositories cho IMM-04 Commissioning."""

from .base import BaseRepository


class CommissioningRepo(BaseRepository):
    DOCTYPE = "Asset Commissioning"


class NonConformanceRepo(BaseRepository):
    DOCTYPE = "Asset QA Non Conformance"


class CommissioningChecklistRepo(BaseRepository):
    DOCTYPE = "Commissioning Checklist Item"


class BaselineTestRepo(BaseRepository):
    DOCTYPE = "Commissioning Baseline Test"
