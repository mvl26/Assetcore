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
from .scope import (
    apply_vendor_scope,
    assert_distinct_signers,
    assert_not_self_submitter,
    assert_vendor_can_access,
)

__all__ = [
    "ApprovalStatus",
    "AssetStatus",
    "CalibrationResult",
    "CalibrationStatus",
    "ErrorCode",
    "Roles",
    "ServiceError",
    "apply_vendor_scope",
    "assert_distinct_signers",
    "assert_not_self_submitter",
    "assert_vendor_can_access",
    "count_with_or",
    "has_any_role",
    "is_admin",
    "normalize_filters",
    "pop_search",
    "require_admin",
    "require_role",
]
