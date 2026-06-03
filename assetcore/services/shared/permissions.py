# Copyright (c) 2026, AssetCore Team
"""Permission helpers — tập trung role checks."""

from collections.abc import Iterable

import frappe

from .constants import Roles
from .errors import forbidden
from . import rbac


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
    return has_role(Roles.SUPER_ADMIN)


def require_admin() -> None:
    require_role((Roles.SUPER_ADMIN,), "Yêu cầu quyền Super Admin")


def require_user_mgmt() -> None:
    if not rbac.can("data.admin"):
        raise forbidden("Không đủ quyền quản lý người dùng")
