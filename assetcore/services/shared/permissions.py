# Copyright (c) 2026, AssetCore Team
"""Permission helpers — tập trung role checks."""

from collections.abc import Iterable

import frappe

from .constants import Roles
from .errors import forbidden


def has_any_role(roles: Iterable[str]) -> bool:
    """True nếu user hiện tại có ít nhất 1 role trong `roles`."""
    return bool(set(frappe.get_roles()) & set(roles))


def has_role(role: str) -> bool:
    return role in set(frappe.get_roles())


def require_role(roles: Iterable[str], message: str = "Không đủ quyền thực hiện") -> None:
    """Raise ServiceError(FORBIDDEN) nếu user không có role phù hợp."""
    if not has_any_role(roles):
        raise forbidden(message)


def is_admin() -> bool:
    return has_role(Roles.SYS_ADMIN)


def require_admin() -> None:
    require_role((Roles.SYS_ADMIN,), "Yêu cầu quyền System Admin")


def require_user_mgmt() -> None:
    require_role(Roles.CAN_ADMIN_USER, "Không đủ quyền quản lý người dùng")
