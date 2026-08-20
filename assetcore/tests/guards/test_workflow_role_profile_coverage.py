# Copyright (c) 2026, AssetCore Team
"""INVARIANT (own-file): reconcile transition-role ⊆ profile-catalog ∪ admin ∪ EXCEPTION.

CR-WF-RBAC-PROFILE-COVERAGE (Trục A · dead-gate persona).

VÌ SAO (root cause "luồng duyệt không duyệt được dù đủ quyền persona"):
  Frappe enforce quyền workflow theo TỪNG transition group `allowed`. Nếu 1 role
  chỉ được gate ở workflow NHƯNG KHÔNG Role Profile nào (ROLE_PROFILE_CATALOG =
  SSoT persona→role) cấp nó, thì KHÔNG user AssetCore nào (mang 1 trong 8 Role
  Profile) có role đó → transition đó CHỈ Super Admin/System Manager thao tác được
  = **dead-gate**: persona chủ-đích không bao giờ chạm được nút, feature âm thầm
  chết (không lỗi tường minh). Ví dụ điển hình: 'Spec User' gate 'Gửi rà soát'
  (Draft→Reviewing) @ IMM-02 nhưng không profile nào cấp 'Spec User'.

Hai bất-biến FILE-driven (đọc source JSON + import catalog SSoT, KHÔNG query DB ⇒
miễn nhiễm fixture-contamination — KHÔNG đỏ do môi trường như test_imm09/00):

  INV-COV  test_every_transition_role_granted_by_profile_or_exception:
      MỌI role ở `allowed` của MỌI transition trong 22 workflow JSON nguồn PHẢI ∈
      (∪ roles_for_profile của ROLE_PROFILE_CATALOG) ∪ ADMIN_OVERRIDE ∪
      EXCEPTION_ROLES. Uncovered ⇒ dead-gate ⇒ RED. 'Spec User' hiện uncovered →
      RED trước fix; sau khi catalog cấp 'Spec User' cho 1 profile → GREEN.

  INV-EXC-REACH  test_exception_roles_never_sole_gate:
      Mọi transition-group gate role EXCEPTION (Vendor Engineer) PHẢI co-list ≥1
      role được Role Profile cấp. Nếu EXCEPTION là gate DUY NHẤT (ngoài admin) thì
      nó cũng thành dead-gate trá hình — guard reachability của chính EXCEPTION.
      Live: cả 3 transition IMM-04 gate Vendor Engineer đều co-list 'PM User'
      (profile-covered) ⇒ GREEN.

Helper FILE-driven (_load_source_workflows / _transition_groups / _ADMIN_OVERRIDE)
IMPORT TRỰC TIẾP từ tests.test_workflows — mirror THẬT (1 SoT gom-group), KHÔNG
tái-hiện logic glob → 0 drift với INV-A/B/C.

Run: bench --site miyano run-tests --app assetcore \
        --module assetcore.tests.guards.test_workflow_role_profile_coverage
"""
from __future__ import annotations

import unittest

from assetcore.setup.role_profile_catalog import (
    ROLE_PROFILE_CATALOG,
    roles_for_profile,
)
from assetcore.tests.guards.test_workflows import (
    _ADMIN_OVERRIDE,
    _load_source_workflows,
    _transition_groups,
)

# Admin-override role: mọi transition-group ĐÃ backfill 2 role này (guard INV-A/B).
# Reconcile-universe cho phép, KHÔNG coi là "covered bởi persona" — QTV chỉ thao tác
# admin-override, KHÔNG phải actor nghiệp vụ chủ-đích của transition.
ADMIN_OVERRIDE = _ADMIN_OVERRIDE

# EXCEPTION_ROLES — role cố ý KHÔNG thuộc bất kỳ Role Profile nội bộ nào.
#
# 'Vendor Engineer' = kỹ sư hiện trường của NHÀ CUNG CẤP (external service engineer).
# Cấp ad-hoc theo hợp đồng bảo hành/lắp đặt, NGOÀI 8 persona nội bộ ("user AssetCore"
# = giữ base role `AssetCore System User`). Cố ý không nằm trong ROLE_PROFILE_CATALOG:
# vendor không phải nhân sự cơ hữu, không được cấp Role Profile. An toàn vì EXCEPTION
# KHÔNG bao giờ sole-gate (xem INV-EXC-REACH): mọi transition có Vendor Engineer luôn
# co-list ≥1 role nội bộ (PM User) → user nội bộ vẫn thao tác được. Thêm role vào tập
# này = QUYẾT ĐỊNH REVIEW có chủ đích (mở dead-gate exemption), KHÔNG phải sửa vặt.
EXCEPTION_ROLES = frozenset({"Vendor Engineer"})


def _profile_granted_roles() -> set[str]:
    """∪ roles_for_profile của MỌI Role Profile trong catalog (gồm base role)."""
    granted: set[str] = set()
    for name in ROLE_PROFILE_CATALOG:
        granted |= set(roles_for_profile(name))
    return granted


def _transition_allowed_roles() -> dict[str, set[str]]:
    """{basename: set(ALL `allowed` role của MỌI transition)} cho 22 source JSON."""
    out: dict[str, set[str]] = {}
    for basename, wf in _load_source_workflows():
        out[basename] = {
            t.get("allowed") for t in wf.get("transitions", []) if t.get("allowed")
        }
    return out


class TestWorkflowRoleProfileCoverage(unittest.TestCase):
    """Reconcile: role gate ở workflow ⊆ role cấp bởi Role Profile ∪ admin ∪ exception."""

    def test_every_transition_role_granted_by_profile_or_exception(self):
        """INV-COV: MỌI `allowed` role ⊆ (∪profile) ∪ ADMIN_OVERRIDE ∪ EXCEPTION_ROLES.

        'Spec User' uncovered (không profile nào cấp) ⇒ RED trước fix; sau khi thêm
        'Spec User' vào 1 Role Profile (ROLE_PROFILE_CATALOG) ⇒ GREEN.
        """
        universe = _profile_granted_roles() | ADMIN_OVERRIDE | EXCEPTION_ROLES
        uncovered: dict[str, list[str]] = {}
        for basename, roles in _transition_allowed_roles().items():
            gap = roles - universe
            if gap:
                uncovered[basename] = sorted(gap)
        self.assertEqual(
            uncovered, {},
            "DEAD-GATE — role gate ở workflow transition nhưng KHÔNG Role Profile "
            "nào cấp (chỉ admin-override thao tác được, persona chủ-đích bị khoá).\n"
            "Fix: cấp role cho 1 Role Profile trong role_profile_catalog.py, HOẶC "
            "thêm role vào EXCEPTION_ROLES (nếu external/ad-hoc có chủ đích).\n"
            f"  {{file: [uncovered_roles]}} = {uncovered}",
        )

    def test_exception_roles_never_sole_gate(self):
        """INV-EXC-REACH: mọi transition-group chứa role EXCEPTION PHẢI co-list ≥1
        role được Role Profile cấp — EXCEPTION KHÔNG bao giờ là gate DUY NHẤT (ngoài
        admin), nếu không chính EXCEPTION cũng thành dead-gate trá hình.
        """
        granted = _profile_granted_roles()
        sole_gated: list[tuple] = []
        for basename, wf in _load_source_workflows():
            for (state, action, next_state), roles in _transition_groups(wf).items():
                if not (roles & EXCEPTION_ROLES):
                    continue  # group không gate EXCEPTION → bỏ qua
                if not (roles & granted):
                    # Chỉ có admin + EXCEPTION → user nội bộ (non-admin) không chạm được.
                    sole_gated.append(
                        (basename, state, action, next_state, sorted(roles)))
        self.assertEqual(
            sole_gated, [],
            "EXCEPTION role sole-gate 1 transition-group (không co-list role nội bộ "
            "nào) → EXCEPTION thành dead-gate trá hình. Phải co-list ≥1 role được "
            "Role Profile cấp.\n"
            "  (file, state, action, next_state, roles):\n"
            + "\n".join(str(m) for m in sole_gated),
        )
