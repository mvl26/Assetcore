# Copyright (c) 2026, AssetCore Team
"""SSoT — "user AssetCore" là ai, và cách DUY NHẤT để liệt kê/đếm họ.

Định danh (memory `user-source-base-role-pattern`, spec
`docs/res/rbac/user-scope-filter-analysis.md` §2 phương án A):

    user AssetCore  ⟺  giữ base role ``AssetCore System User``

`Administrator` / `Guest` là tài khoản hạ tầng của Frappe, KHÔNG tính. Site cài
chung ERPNext/CRM có rất nhiều `tabUser` không thuộc AssetCore — đếm thô
``frappe.db.count("User")`` cho ra con số thổi phồng, lệch với `/user-profiles`
(sự cố 2026-07-22: dashboard 29 vs danh sách 4).

Mọi trang / form / field chọn người / báo cáo PHẢI lấy user qua module này
(hoặc qua `api/user.py` vốn đã route qua đây). Guard tĩnh
`tests/test_ac_user_source.py::TestNoRawUserQueryGuard` chặn tái phát.
"""
from __future__ import annotations

import frappe

from assetcore.setup.role_profile_catalog import BASE_ROLE

# Tài khoản hạ tầng Frappe — không thuộc scope "user AssetCore".
INFRA_ACCOUNTS: frozenset[str] = frozenset({"Administrator", "Guest"})

# Trạng thái CHẶN đăng nhập — mirror cổng `api/auth.check_account_status`:
# chỉ Pending/Rejected là chặn; NULL/rỗng = user cũ chưa stamp ⇒ vẫn hợp lệ.
# (Đảo lại — lọc `== "Approved"` — sẽ làm rỗng picker trên site đã chạy trước
# khi có custom field.)
_BLOCKED_STATUSES = ("Pending", "Rejected")
_APPROVAL_FIELD = "imm_approval_status"


def _users_with_role(role: str) -> set[str]:
    """Tên (email) các User giữ ``role`` — resolve qua child table ``Has Role``.

    ``frappe.db.count`` / ``get_all`` trên User không filter xuyên child table
    được, nên phải resolve danh sách parent trước rồi lọc ``name in [...]``.
    Bắt buộc lọc ``parenttype="User"``: ``Has Role`` còn là child của
    ``Role Profile`` — thiếu clause này sẽ đếm nhầm cả row cấu hình profile.

    Args:
        role: tên Role cần tra.

    Returns:
        Tập tên User giữ role đó.
    """
    return {
        r["parent"]
        for r in frappe.get_all(
            "Has Role",
            filters={"parenttype": "User", "role": role},
            fields=["parent"],
        )
    }


def ac_user_names(*, role: str = "", approved_only: bool = False) -> set[str]:
    """Tập tên (email) của user AssetCore.

    Args:
        role: nếu truyền, GIAO thêm với tập user giữ role này (không thay thế
            base role — user có role nghiệp vụ nhưng thiếu base role vẫn bị loại).
        approved_only: loại user đang Pending / Rejected (chưa/không login được
            → gán việc cho họ là dead-end, BA §0.1.1). Dùng cho field chọn
            người. Bỏ qua nếu custom field chưa migrate.

    Returns:
        Tập tên User; rỗng khi site chưa có user AssetCore nào.
    """
    names = _users_with_role(BASE_ROLE) - INFRA_ACCOUNTS
    if role:
        names &= _users_with_role(role)
    if approved_only and names and frappe.db.has_column("User", _APPROVAL_FIELD):
        blocked = {
            r["name"]
            for r in frappe.get_all(
                "User",
                filters={"name": ["in", sorted(names)],
                         _APPROVAL_FIELD: ["in", list(_BLOCKED_STATUSES)]},
                fields=["name"],
            )
        }
        names -= blocked
    return names


def ac_user_filters(
    extra_filters: dict | None = None, *, role: str = "", approved_only: bool = False
) -> dict:
    """Filters dict đã khoá theo tập user AssetCore — dùng cho count VÀ rows.

    Tập rỗng → ``name in [""]`` (ép kết quả rỗng, KHÔNG trả toàn bộ user).
    Count và rows phải dùng CÙNG filters này để `pagination.total` luôn khớp số
    dòng (LL-BE-42, INVARIANT count == drill).

    Args:
        extra_filters: điều kiện bổ sung trên `tabUser` (vd `{"enabled": 1}`).
        role: xem `ac_user_names`.
        approved_only: xem `ac_user_names`.

    Returns:
        Filters dict truyền thẳng vào `frappe.get_all("User", ...)`.
    """
    names = ac_user_names(role=role, approved_only=approved_only)
    filters: dict = dict(extra_filters or {})
    filters["name"] = ["in", sorted(names) or [""]]
    return filters


def count_ac_users(
    extra_filters: dict | None = None,
    *,
    role: str = "",
    approved_only: bool = False,
    or_filters: list | None = None,
) -> int:
    """Đếm user AssetCore — thay cho mọi ``frappe.db.count("User", ...)`` thô.

    Args:
        extra_filters: điều kiện bổ sung trên `tabUser`.
        role: xem `ac_user_names`.
        approved_only: xem `ac_user_names`.
        or_filters: OR-clause (vd tìm kiếm). ``frappe.db.count`` KHÔNG nhận
            or_filters → đếm qua `get_all`; nếu bỏ qua, `pagination.total` sẽ
            lớn hơn số dòng khi người dùng gõ tìm kiếm.

    Returns:
        Số user khớp.
    """
    filters = ac_user_filters(extra_filters, role=role, approved_only=approved_only)
    if or_filters:
        return len(frappe.get_all(
            "User", filters=filters, or_filters=or_filters,
            fields=["name"], limit_page_length=0,
        ))
    return int(frappe.db.count("User", filters))


def get_ac_users(
    fields: list[str],
    extra_filters: dict | None = None,
    *,
    role: str = "",
    approved_only: bool = False,
    or_filters: list | None = None,
    order_by: str = "full_name asc",
    limit_start: int = 0,
    limit_page_length: int = 0,
) -> list[dict]:
    """Liệt kê user AssetCore — thay cho mọi ``frappe.get_all("User", ...)`` thô.

    Args:
        fields: field cần lấy trên `tabUser`.
        extra_filters: điều kiện bổ sung (vd `{"enabled": 1}`).
        role: xem `ac_user_names`.
        approved_only: xem `ac_user_names`.
        or_filters: OR-clause (vd tìm theo `full_name` / `email`).
        order_by: mặc định theo tên hiển thị.
        limit_start: offset phân trang.
        limit_page_length: 0 = không giới hạn (caller PHẢI tự cap — LL-BE-43).

    Returns:
        Danh sách dict theo `fields`.
    """
    return frappe.get_all(
        "User",
        filters=ac_user_filters(extra_filters, role=role, approved_only=approved_only),
        or_filters=or_filters,
        fields=fields,
        order_by=order_by,
        limit_start=limit_start,
        limit_page_length=limit_page_length,
    )


def is_ac_user(user: str) -> bool:
    """True khi ``user`` là user AssetCore (giữ base role, không phải infra account).

    Args:
        user: tên (email) User.

    Returns:
        bool
    """
    if not user or user in INFRA_ACCOUNTS:
        return False
    return bool(frappe.db.exists(
        "Has Role", {"parenttype": "User", "parent": user, "role": BASE_ROLE}
    ))
