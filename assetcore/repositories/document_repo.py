# Copyright (c) 2026, AssetCore Team
"""Repositories cho IMM-05 Document Repository."""

from .base import BaseRepository


class DocumentRepo(BaseRepository):
    DOCTYPE = "Asset Document"


class DocumentRequestRepo(BaseRepository):
    DOCTYPE = "Document Request"


class RequiredDocumentTypeRepo(BaseRepository):
    DOCTYPE = "Required Document Type"


class ExpiryAlertLogRepo(BaseRepository):
    DOCTYPE = "Expiry Alert Log"
