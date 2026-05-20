# Copyright (c) 2026, AssetCore Team
"""Shared cross-cutting primitives for AssetCore service layer.

Re-exports chính:
- constants: Roles, AssetStatus, CalibrationStatus, CalibrationResult, ErrorCode
- errors: ServiceError
- permissions: has_any_role, require_role
"""
from .constants import (
    ApprovalStatus,
    AssetStatus,
    CalibrationResult,
    CalibrationStatus,
    ErrorCode,
    Roles,
)
from .errors import ServiceError
from .filters import count_with_or, normalize_filters, pop_search
from .permissions import has_any_role, is_admin, require_admin, require_role

__all__ = [
    "ApprovalStatus",
    "AssetStatus",
    "CalibrationResult",
    "CalibrationStatus",
    "ErrorCode",
    "Roles",
    "ServiceError",
    "count_with_or",
    "has_any_role",
    "is_admin",
    "normalize_filters",
    "pop_search",
    "require_admin",
    "require_role",
]
