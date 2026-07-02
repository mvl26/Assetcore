"""Backfill base role ``AssetCore System User`` cho System User hiện có.

Bối cảnh (2026-06-29): base role = định danh "user AssetCore" (đăng nhập SPA +
đọc shared-core). Từ nay user tạo qua UI luôn được cấp base role + ``list_users``
chỉ trả user có base role. Patch này cấp base role cho các System User đã tồn tại
TRƯỚC thay đổi để họ không biến mất khỏi danh sách user AssetCore.

Scope (quyết định USER): MỌI System User TRỪ ``Administrator``/``Guest``
(infra account, không thuộc scope user AssetCore). Bao gồm cả user ``enabled=0``
(self-signup đang chờ duyệt) — họ vẫn là user AssetCore (admin cần thấy để duyệt).

An toàn:
  - Additive + idempotent (skip user đã có base role) — chạy lại không nhân đôi.
  - KHÔNG cấp cho Administrator/Guest (guard 2 lớp: query filter + skip trong loop).
  - ``doc.save(ignore_permissions=True)`` giữ nguyên các role khác.
"""
from __future__ import annotations

import frappe

from assetcore.setup.role_profile_catalog import BASE_ROLE

_EXCLUDED = {"Administrator", "Guest"}


def grant_base_role(user_names: list[str] | None = None) -> int:
    """Cấp base role cho ``user_names`` (mặc định: mọi System User trừ Admin/Guest).

    Trả số user được cấp mới (đã có base role → bỏ qua). Tách khỏi ``execute`` để
    unit-test scope theo user cụ thể, KHÔNG đụng toàn bộ DB site khi test.
    """
    if not frappe.db.exists("Role", BASE_ROLE):
        return 0

    if user_names is None:
        user_names = frappe.get_all(
            "User",
            filters={"user_type": "System User", "name": ["not in", list(_EXCLUDED)]},
            pluck="name",
        )

    granted = 0
    for name in user_names:
        if name in _EXCLUDED or not frappe.db.exists("User", name):
            continue
        doc = frappe.get_doc("User", name)
        if any(r.role == BASE_ROLE for r in doc.roles):
            continue
        doc.append("roles", {"role": BASE_ROLE})
        doc.flags.ignore_permissions = True
        doc.save()
        granted += 1
    return granted


def execute() -> None:
    granted = grant_base_role()
    frappe.db.commit()
    print(f"[patches.v3_2.009_backfill_base_role] granted_base_role={granted}")
