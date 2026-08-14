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
    # NB (2026-06-02): vai trò giám sát — ngoài 4 role planning/deployment dưới,
    # role "Commissioning Manager" (độc quyền profile này) còn được cấp DocPerm
    # READ-ONLY trên PM Work Order / Asset Repair / Incident Report (+RCA/QA NC) để
    # KPI dashboard opsmgr drill-down xem được (pm.read/repair.read/corrective.read).
    # Read-only thuần — KHÔNG write/create/delete/workflow. Xem DocPerm read trong
    # các *.json doctype tương ứng + docs/architecture/FE_Persona_Dashboards.md §9.5.
    "Trưởng phòng VT-TTBYT": [
        "Commissioning Manager", "Needs Manager",
        "Procurement Manager", "Spec Manager",
        # 'Spec User' (2026-07-14, CR-WF-RBAC-PROFILE-COVERAGE / ADR-IMM02-03): đóng
        # dead-gate persona — 'Gửi rà soát' (Draft→Reviewing) @ IMM-02 có sole
        # non-admin gate = 'Spec User', nhưng KHÔNG Role Profile nào cấp role này →
        # chỉ Super Admin/System Manager duyệt được (persona soạn spec bị khoá). VT-
        # TTBYT là persona SOẠN + rà-soát spec chủ-đích; 'Spec User' = drafter 2-tier
        # DocPerm (submit=0) song hành 'Spec Manager' (submit=1) vốn đã có. Fix
        # catalog-only, KHÔNG chạm workflow JSON (giữ admin-override guard). Xem
        # tests/test_workflow_role_profile_coverage.py (INV-COV) + docs/imm-02.
        "Spec User",
        # 2026-08-14 (5-vòng test toàn hệ thống): đóng nốt 3 dead-gate CÙNG DẠNG với
        # 'Spec User' ở trên — role tầng thừa hành gate transition thật nhưng KHÔNG
        # Role Profile nào cấp ⇒ chỉ Manager/Super Admin thao tác được, persona chủ
        # đích bị khoá khỏi chính việc của mình:
        #   'Needs User'         → 7 transition @ imm_01_needs_workflow
        #   'Procurement User'   → 4 @ imm_03_decision + 2 @ imm_03_vendor_eval
        #   'Commissioning User' → 11 @ imm_04_workflow
        # Đặt cùng profile với role Manager tương ứng (Needs/Procurement/
        # Commissioning Manager đều đã ở đây) — đúng tiền lệ 'Spec User', và VT-TTBYT
        # là persona SOẠN đề xuất + hồ sơ mua sắm + nghiệm thu lắp đặt.
        "Needs User", "Procurement User", "Commissioning User",
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
        # 'Training User' (2026-08-14): dead-gate — 11 transition @ imm_06_competency
        # + 8 @ imm_06_session gate role này mà không profile nào cấp. Đặt cạnh
        # 'Training Manager' (đã ở đây) đúng tiền lệ 'Spec User'.
        "Document Manager", "Document User", "Training Manager", "Training User",
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
