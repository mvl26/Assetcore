# Copyright (c) 2026, AssetCore Team
"""Repositories cho IMM-00 foundation doctypes."""

from .base import BaseRepository


class AssetRepo(BaseRepository):
    DOCTYPE = "AC Asset"


class DeviceModelRepo(BaseRepository):
    DOCTYPE = "IMM Device Model"


class DepartmentRepo(BaseRepository):
    DOCTYPE = "AC Department"


class LocationRepo(BaseRepository):
    DOCTYPE = "AC Location"


class SupplierRepo(BaseRepository):
    DOCTYPE = "AC Supplier"


class AuditTrailRepo(BaseRepository):
    DOCTYPE = "IMM Audit Trail"


class CapaRepo(BaseRepository):
    DOCTYPE = "IMM CAPA Record"


class LifecycleEventRepo(BaseRepository):
    DOCTYPE = "Asset Lifecycle Event"
