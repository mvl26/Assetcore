# Copyright (c) 2026, AssetCore Team
"""Seed user test cho kiểm thử phân quyền giao diện theo role THẬT.

Mục đích: tạo nhiều tài khoản, mỗi tài khoản gán role khác nhau, để verify nav +
RBAC gating hiển thị/chặn ĐÚNG theo role đăng nhập (Core Doc
docs/architecture/FE_Persona_Navigation.md §7.ter/§7.quinquies). Mỗi vai trò
chính 1 user (gán qua Role Profile — role khoá); thêm 1 user MULTI-ROLE gán THỦ
CÔNG (role_profile_name=None) để chứng minh nav là UNION + nhánh sửa tự do.
Tên người Việt thật, email hợp lệ — KHÔNG dữ liệu rác.

Chạy:
    bench --site miyano execute assetcore.scripts.seed_test_users.seed_test_users

Idempotent: user đã tồn tại → cập nhật (đồng bộ) role, không tạo trùng. Mọi role
đều đã verify tồn tại trong fixtures/role.json. Mỗi user thêm role nền
"AssetCore System User" để đăng nhập + đọc shared-core.

KHÔNG dùng cho production — email *.assetcore.test + mật khẩu mặc định.
"""
from __future__ import annotations

import frappe

from assetcore.setup.role_profile_catalog import roles_for_profile

# Mật khẩu mặc định cho tài khoản test (môi trường dev). Đủ mạnh để qua policy.
_DEFAULT_PASSWORD = "AssetCore@2026"

# Role nền — mọi user cần để đăng nhập SPA + đọc shared-core.
_BASE_ROLE = "AssetCore System User"

# Tài khoản test — Core Doc §7.quinquies: 8 user gán qua Role Profile (tên VI,
# role bị KHOÁ bởi profile) + 1 user multi-role gán THỦ CÔNG (role_profile=None,
# role sửa tự do) để chứng minh 2 nhánh. `role_profile` khớp ROLE_PROFILE_CATALOG
# (role_profile_catalog) → role suy ra từ catalog, KHÔNG hardcode (chống drift).
_TEST_USERS: list[dict] = [
    {
        "email": "itadmin@assetcore.test",
        "first_name": "Đỗ Minh", "last_name": "Quân",
        "role_profile": "Quản trị viên IT",
    },
    {
        "email": "tranquanghuy@assetcore.test",
        "first_name": "Trần Quang", "last_name": "Huy",
        "role_profile": "Trưởng phòng VT-TTBYT",
    },
    {
        "email": "lethanhtung@assetcore.test",
        "first_name": "Lê Thanh", "last_name": "Tùng",
        "role_profile": "Trưởng xưởng kỹ thuật",
    },
    {
        "email": "phamvanduc@assetcore.test",
        "first_name": "Phạm Văn", "last_name": "Đức",
        "role_profile": "Kỹ thuật viên",
    },
    {
        "email": "nguyenthimaihoa@assetcore.test",
        "first_name": "Nguyễn Thị Mai", "last_name": "Hoa",
        "role_profile": "Cán bộ QA / Kiểm toán",
    },
    {
        "email": "vodinhkhanh@assetcore.test",
        "first_name": "Võ Đình", "last_name": "Khánh",
        "role_profile": "Thủ kho phụ tùng",
    },
    {
        "email": "buithihonganh@assetcore.test",
        "first_name": "Bùi Thị Hồng", "last_name": "Anh",
        "role_profile": "Cán bộ hồ sơ",
    },
    {
        "email": "dangvanson@assetcore.test",
        "first_name": "Đặng Văn", "last_name": "Sơn",
        "role_profile": "Trưởng khoa lâm sàng",
    },
    # Multi-role THỦ CÔNG: PM User + Inventory Manager → nav UNION.
    # KHÔNG gán Role Profile (role_profile_name=None) → role sửa tự do; chứng minh
    # nhánh thủ công khác nhánh khoá-bởi-Role-Profile.
    {
        "email": "hoangthithuy@assetcore.test",
        "first_name": "Hoàng Thị", "last_name": "Thuý",
        "role_profile": None,  # thủ công
        "manual_roles": ["PM User", "Inventory Manager"],
    },
]


def _spec_profile_name(spec: dict) -> str | None:
    """Tên Role Profile của spec (None nếu gán thủ công)."""
    return spec.get("role_profile")


def _spec_target_roles(spec: dict) -> list[str]:
    """Bộ role kỳ vọng của spec (profile → catalog; thủ công → manual + base)."""
    profile = spec.get("role_profile")
    if profile:
        return roles_for_profile(profile)  # đã gồm _BASE_ROLE
    seen: set[str] = set()
    out: list[str] = []
    for r in (_BASE_ROLE, *spec.get("manual_roles", [])):
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


def _ensure_roles_exist(role_names: set[str]) -> None:
    """Fail-fast nếu role chưa migrate vào site (tránh add_roles silent no-op)."""
    missing = [r for r in sorted(role_names) if not frappe.db.exists("Role", r)]
    if missing:
        raise frappe.ValidationError(
            "Role chưa tồn tại trên site (chạy bench migrate trước): "
            + ", ".join(missing)
        )


def _ensure_profiles_exist(profile_names: set[str]) -> None:
    """Fail-fast nếu Role Profile chưa seed (chạy migrate / setup_role_profiles trước)."""
    missing = [p for p in sorted(profile_names) if not frappe.db.exists("Role Profile", p)]
    if missing:
        raise frappe.ValidationError(
            "Role Profile chưa tồn tại (chạy bench migrate trước): " + ", ".join(missing)
        )


def _upsert_user(spec: dict) -> str:
    """Tạo mới/cập nhật 1 user test. Có Role Profile → gán role_profile_name (role
    khoá); thủ công → role_profile_name=None + add_roles. Idempotent. Trả 'created'|'updated'."""
    email = spec["email"]
    profile_name = _spec_profile_name(spec)        # None nếu thủ công
    target_roles = _spec_target_roles(spec)        # bộ role kỳ vọng (gồm _BASE_ROLE)

    if frappe.db.exists("User", email):
        user = frappe.get_doc("User", email)
        outcome = "updated"
    else:
        user = frappe.new_doc("User")
        user.email = email
        user.send_welcome_email = 0
        user.user_type = "System User"
        user.new_password = _DEFAULT_PASSWORD
        outcome = "created"

    user.first_name = spec["first_name"]
    user.last_name = spec["last_name"]
    user.enabled = 1

    if profile_name:
        # Gán qua Role Profile: core populate_role_profile_roles sẽ clear+replace
        # roles bằng đúng bộ của profile khi save → role bị khoá bởi Role Profile.
        user.role_profile_name = profile_name
        user.flags.ignore_permissions = True
        user.save(ignore_permissions=True) if outcome == "updated" else user.insert(ignore_permissions=True)
    else:
        # Thủ công: bỏ profile + set đúng bộ role (idempotent).
        user.role_profile_name = None
        existing = {r.role for r in user.roles}
        if set(target_roles) != existing:
            user.set("roles", [])
            for r in target_roles:
                user.append("roles", {"role": r})
        user.flags.ignore_permissions = True
        user.save(ignore_permissions=True) if outcome == "updated" else user.insert(ignore_permissions=True)

    return outcome


def seed_test_users() -> dict:
    """Entrypoint — idempotent. Tạo/cập nhật 9 user test phân quyền (8 qua Role Profile + 1 thủ công)."""
    # Verify role (cho user thủ công) + Role Profile (cho user có profile) đã tồn tại.
    all_roles: set[str] = set()
    profile_names: set[str] = set()
    for spec in _TEST_USERS:
        all_roles.update(_spec_target_roles(spec))
        p = _spec_profile_name(spec)
        if p:
            profile_names.add(p)
    _ensure_roles_exist(all_roles)
    _ensure_profiles_exist(profile_names)

    results: list[dict] = []
    for spec in _TEST_USERS:
        outcome = _upsert_user(spec)
        # Đọc lại role thực tế trên user sau khi save (chứng minh khoá/sync).
        actual_roles = sorted(r.role for r in frappe.get_doc("User", spec["email"]).roles)
        results.append({
            "email": spec["email"],
            "name": f'{spec["first_name"]} {spec["last_name"]}',
            "role_profile": _spec_profile_name(spec) or "(thủ công)",
            "roles": actual_roles,
            "outcome": outcome,
        })

    frappe.db.commit()

    print("\n=== Seed user test phân quyền — site:", frappe.local.site, "===")
    for r in results:
        print(f'  [{r["outcome"]:7}] {r["name"]:22} <{r["email"]}>')
        print(f'            role_profile: {r["role_profile"]}')
        print(f'            roles       : {", ".join(r["roles"])}')
    print(f"\n  Mật khẩu đăng nhập (tất cả): {_DEFAULT_PASSWORD}")
    print("  (Chỉ dùng cho môi trường dev — KHÔNG production.)\n")

    return {"password": _DEFAULT_PASSWORD, "users": results}
