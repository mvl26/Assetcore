# Copyright (c) 2026, AssetCore Team
"""RBAC guard — admin override PHẢI có trên MỌI workflow transition.

ROOT CAUSE (bug "role QTV bị báo không có quyền", vd Phê duyệt kế hoạch mua sắm):
  Frappe enforce quyền workflow theo TỪNG transition group (state, action, next_state)
  — user phải có 1 role nằm trong `allowed` của group đó, `ignore_permissions=True`
  KHÔNG bypass `validate_workflow` (LL-BE-62). Profile "Quản trị viên IT" (QTV) chỉ
  cấp `AssetCore Super Admin` (+ base). 113 transition-group trên 20/22 workflow BỎ
  SÓT admin role ⇒ QTV bị WorkflowPermissionError → ServiceError(FORBIDDEN).

INVARIANT (SoT): mọi (state, action, next_state) của MỌI AssetCore Workflow PHẢI cho
phép ≥1 admin role — `AssetCore Super Admin` là role god-mode (37× toàn hệ, role được
allow nhiều nhất). Guard này RED trước fix (113 group thiếu), GREEN sau khi bồi admin
vào fixtures/workflow.json (nguồn seed live).

Run:
  bench --site miyano run-tests --app assetcore \
      --module assetcore.tests.test_workflow_admin_override
"""
from __future__ import annotations

import json
import unittest
from collections import defaultdict

import frappe

# Admin god-mode override — khớp 13 workflow đang hoạt động (Super Admin + System Manager).
_ADMIN_ROLES = {"AssetCore Super Admin", "System Manager"}


def _load_workflow_fixture() -> list[dict]:
    path = frappe.get_app_path("assetcore", "fixtures", "workflow.json")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


class TestWorkflowAdminOverride(unittest.TestCase):
    def test_every_transition_group_allows_admin(self) -> None:
        blocked: list[tuple] = []
        for d in _load_workflow_fixture():
            if d.get("doctype") != "Workflow":
                continue
            groups: dict[tuple, set] = defaultdict(set)
            for t in d.get("transitions", []):
                key = (t.get("state"), t.get("action"), t.get("next_state"))
                groups[key].add(t.get("allowed"))
            for key, roles in groups.items():
                missing = _ADMIN_ROLES - roles
                if missing:
                    blocked.append((d.get("name"), *key, tuple(sorted(missing))))

        self.assertEqual(
            blocked, [],
            f"{len(blocked)} transition-group thiếu admin override (QTV bị chặn): "
            + "; ".join(f"{w}:{s}--{a}-->{n} thiếu {list(m)}"
                        for w, s, a, n, m in blocked[:12]),
        )


if __name__ == "__main__":
    unittest.main()
