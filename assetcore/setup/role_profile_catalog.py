# Copyright (c) 2026, AssetCore Team
"""Catalog SSOT: 8 Role Profile (tên VI thuần) -> bộ role chọn sẵn.

Core Doc: docs/architecture/FE_Persona_Navigation.md §7.quinquies.

Role Profile (DocType core Frappe) là cơ chế chuẩn để gán bộ role chọn sẵn cho
một User. Khi User.role_profile_name được set, Frappe core
`populate_role_profile_roles` clear + replace toàn bộ user.roles bằng đúng bộ
role của profile mỗi lần save -> role bị "khoá" bởi profile. Bỏ profile (None)
-> role sửa thủ công tự do.

RANH GIỚI (Phase 1.4): BE chỉ biết **Role Profile** + **Role Permission** (chuẩn
Frappe). Khái niệm "persona" (nhãn/nhóm/màu/nav) sống TRỌN ở FE
(`frontend/src/constants/personas.ts`); FE tự ánh xạ persona -> tên Role Profile
rồi gọi API thuần `assign_role_profile`. Catalog này KHÔNG dùng mã persona làm
khoá — khoá (key) là tên Role Profile.

Mỗi profile thêm role nền `AssetCore System User` (đăng nhập SPA + đọc
shared-core). Bộ role mỗi profile = đúng tập role module-based trong
`fixtures/role.json` / `Roles.ALL` (trừ role Frappe-native System
Manager/Administrator — KHÔNG đưa vào profile vì do Frappe core sở hữu; profile
"Quản trị viên IT" chỉ chứa AssetCore Super Admin).

Tên profile dùng tiếng Việt thuần — KHÔNG prefix "AssetCore —" / "IMM -" (đó là
tên legacy đã bị xoá; tránh trùng để cleanup legacy không xoá nhầm profile mới).
"""
from __future__ import annotations

from assetcore.services.shared.constants import Roles

# Role nền mọi Role Profile — đăng nhập + đọc shared-core.
BASE_ROLE = Roles.SYSTEM_USER

# Role Profile name (VI thuần) -> [domain roles ngoài BASE_ROLE].
# Bộ role bất biến vs §7.quater.2 (chỉ đổi KHOÁ catalog từ persona_code -> tên
# Role Profile). FE map persona -> các tên dưới đây (personas.ts §7.quinquies.3).
ROLE_PROFILE_CATALOG: dict[str, list[str]] = {
    "Quản trị viên IT": [
        Roles.SUPER_ADMIN,
    ],
    "Trưởng phòng VT-TTBYT": [
        "Commissioning Manager", "Needs Manager",
        "Procurement Manager", "Spec Manager",
    ],
    "Trưởng xưởng kỹ thuật": [
        "PM Manager", "Repair Manager",
        "Calibration Manager", "Corrective Manager",
    ],
    "Kỹ thuật viên": [
        "PM User", "Repair User",
        "Calibration User", "Corrective User",
    ],
    "Cán bộ QA / Kiểm toán": [
        "Compliance Manager", "Compliance User", Roles.AUDITOR,
    ],
    "Cán bộ hồ sơ": [
        "Document Manager", "Document User", "Training Manager",
    ],
    "Thủ kho phụ tùng": [
        "Inventory Manager", "Inventory User",
    ],
    "Trưởng khoa lâm sàng": [
        "Corrective Manager", "Corrective User",
    ],
}

# Tên 8 Role Profile (dùng cho fixtures filter + API whitelist + cleanup guard).
PROFILE_NAMES: list[str] = list(ROLE_PROFILE_CATALOG.keys())


def roles_for_profile(profile_name: str) -> list[str]:
    """Bộ role đầy đủ (gồm BASE_ROLE) của 1 Role Profile (theo tên profile)."""
    domain_roles = ROLE_PROFILE_CATALOG[profile_name]
    # dedupe giữ thứ tự: BASE_ROLE trước, rồi domain roles.
    seen: set[str] = set()
    out: list[str] = []
    for r in (BASE_ROLE, *domain_roles):
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


def profile_name_to_roles() -> dict[str, list[str]]:
    """Map {profile_name -> [roles]} cho mọi Role Profile (gồm BASE_ROLE)."""
    return {name: roles_for_profile(name) for name in ROLE_PROFILE_CATALOG}
