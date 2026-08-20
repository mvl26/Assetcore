# Copyright (c) 2026, AssetCore Team
"""RBAC guard — admin override PHẢI có trên MỌI transition-group của MỌI Workflow
AssetCore **TRÊN CHÍNH DB ĐANG CHẠY** (live-DB driven, KHÔNG đọc file JSON).

ROOT CAUSE (bug "role QTV bị báo không có quyền", vd Phê duyệt kế hoạch mua sắm):
  Frappe enforce quyền workflow theo TỪNG transition group (state, action, next_state)
  — user phải có ≥1 role nằm trong `allowed` của group đó; `ignore_permissions=True`
  KHÔNG bypass `validate_workflow` (LL-BE-62). Profile "Quản trị viên IT" (QTV) chỉ
  cấp `AssetCore Super Admin` (+ base). Nếu 1 transition-group thiếu admin role → QTV
  bị WorkflowPermissionError → ServiceError(FORBIDDEN) khi bấm nút duyệt.

VÌ SAO KHÁC `test_workflow_admin_override` / `test_workflows` (INV-A/B/C):
  ── Cả 2 suite kia là **FILE-DRIVEN**: chúng đọc `fixtures/workflow.json` (export)
     và/hoặc `assetcore/workflow/*.json` (seed nguồn) rồi assert invariant TRÊN FILE.
  ── NHƯNG Frappe **KHÔNG** đọc file JSON lúc transition. `validate_workflow` enforce
     theo **DB Workflow doc** (bảng `tabWorkflow` + `tabWorkflow Transition`). File có
     thể GREEN mà DB đã drift (import lỗi dở, patch tay, backfill chưa chạy trên site
     này) ⇒ file-driven guard KHÔNG chứng minh được "QTV duyệt được trên site NÀY".
  ── Guard dưới đây query THẲNG `frappe.get_doc('Workflow', name)` từ DB đang chạy ⇒
     là guard **gần enforcement thật nhất** — nó chứng minh site này để QTV duyệt được.
  ── Nếu guard RED (DB drift) → chạy `assetcore.setup.backfill_workflow_admin.run()`
     (sync live, idempotent, task-endorsed — KHÔNG cần bench migrate) đưa DB về đúng.

SoT (chống drift):
  - Scope name-set = `backfill_workflow_admin._assetcore_workflow_names()` (đọc thẳng
    fixtures/workflow.json = 22 Workflow AssetCore). Foreign workflow multi-app
    (mvl_accounting / antmed_crm / workflowcore) bị LỌC — KHÔNG áp invariant AssetCore
    lên app khác (memory `workflow_admin_override_rbac`).
  - Admin role-set = `backfill_workflow_admin.ADMIN_ROLES` (import, KHÔNG hardcode) ⇒
    nếu SoT đổi role-set, guard tự bám theo.

Run:
  bench --site miyano run-tests --app assetcore \
      --module assetcore.tests.integration.test_workflow_admin_override_livedb
"""
from __future__ import annotations

import unittest
from collections import defaultdict

import frappe

from assetcore.setup import backfill_workflow_admin as bwa
from frappe.tests.utils import FrappeTestCase

# Admin role-set = SoT (import từ backfill, KHÔNG hardcode) ⇒ guard tự bám drift SoT.
ADMIN_SET: set[str] = set(bwa.ADMIN_ROLES)

# Foreign workflow (app khác trên site chung) — KHÔNG được nằm trong scope AssetCore.
_FOREIGN_SAMPLE = {"MVL Duyệt thanh toán", "Cong Tac Approval"}


def _scope_names() -> set[str]:
    """Tên 22 Workflow AssetCore (SoT = backfill helper, đọc fixtures/workflow.json)."""
    return bwa._assetcore_workflow_names()


def _live_groups(name: str) -> dict[tuple, set]:
    """Gom transitions của 1 live Workflow doc theo (state, action, next_state)→set(allowed).

    ĐỌC THẲNG DB (frappe.get_doc) — KHÔNG file JSON. Đây là điểm khác cốt lõi vs
    guard file-driven: phản ánh đúng luật enforce lúc transition.
    """
    doc = frappe.get_doc("Workflow", name)
    groups: dict[tuple, set] = defaultdict(set)
    for t in doc.transitions:
        groups[(t.state, t.action, t.next_state)].add(t.allowed)
    return groups


def _blocked_live_groups(names, admin_set: set[str]) -> list[tuple]:
    """Trả list transition-group (live DB) THIẾU bất kỳ admin role nào.

    Mỗi phần tử = (workflow_name, state, action, next_state, tuple(sorted(missing))).
    Chỉ xét Workflow tồn tại trong DB (existence check riêng ở test partial-seed).
    """
    blocked: list[tuple] = []
    for wf in sorted(names):
        if not frappe.db.exists("Workflow", wf):
            continue
        for (state, action, next_state), roles in _live_groups(wf).items():
            missing = admin_set - roles
            if missing:
                blocked.append((wf, state, action, next_state, tuple(sorted(missing))))
    return blocked


class TestWorkflowAdminOverrideLiveDB(FrappeTestCase):
    """DB-DRIVEN invariant: mọi transition-group của mọi live AssetCore Workflow cấp
    CẢ {AssetCore Super Admin, System Manager}. Đọc DB đang chạy (KHÔNG file JSON)."""

    # -- TC-DB-ADMIN-4 (SoT parity, drift-proof) -------------------------------
    def test_admin_set_tracks_backfill_sot(self) -> None:
        """ADMIN_SET dùng trong guard IS backfill_workflow_admin.ADMIN_ROLES (import),
        KHÔNG hardcode ⇒ SoT đổi role-set thì guard tự bám theo."""
        self.assertEqual(ADMIN_SET, set(bwa.ADMIN_ROLES))
        self.assertEqual(ADMIN_SET, {"AssetCore Super Admin", "System Manager"})

    # -- TC-DB-ADMIN-5 (existence / partial-seed) ------------------------------
    def test_all_scope_workflows_exist_in_db(self) -> None:
        """Mỗi tên scope PHẢI là 1 live Workflow doc — chặn fresh-install nửa vời
        (seed thiếu workflow) khiến enforcement sau này lệch."""
        missing = sorted(w for w in _scope_names() if not frappe.db.exists("Workflow", w))
        self.assertEqual(
            missing, [],
            f"{len(missing)} Workflow scope AssetCore KHÔNG tồn tại trên DB (seed thiếu): "
            + ", ".join(missing),
        )

    # -- TC-DB-ADMIN-1 (happy / GREEN) — guard chính --------------------------
    def test_every_live_transition_group_grants_admin(self) -> None:
        """Với mỗi live Workflow ∈ scope (22): mọi (state, action, next_state) PHẢI cho
        phép CẢ AssetCore Super Admin + System Manager trên DB ĐANG CHẠY.

        RED ⇒ DB drift ⇒ chạy `assetcore.setup.backfill_workflow_admin.run()` reconcile.
        """
        blocked = _blocked_live_groups(_scope_names(), ADMIN_SET)
        self.assertEqual(
            blocked, [],
            f"{len(blocked)} transition-group (live DB) thiếu admin override — QTV bị "
            f"chặn duyệt trên site này. Fix: backfill_workflow_admin.run(). Chi tiết: "
            + "; ".join(f"{w}:{s}--{a}-->{n} thiếu {list(m)}"
                        for w, s, a, n, m in blocked[:12]),
        )

    # -- TC-DB-ADMIN-2 (RED-proof — guard cắn trên DB thật) --------------------
    def test_guard_detects_injected_missing_admin(self) -> None:
        """Inject 1 live transition-group thiếu Super Admin (set_value allowed → role
        non-admin đang có sẵn, trong try/finally restore) → guard PHẢI report đúng tuple.

        Chứng minh guard đọc DB thật cắn được (không nhận suông). KHÔNG commit; restore
        trong finally ⇒ net-effect = 0 dù test fail giữa chừng.
        """
        target = None  # (wf, row_name, (state, action, next_state), replacement)
        for wf in sorted(_scope_names()):
            if not frappe.db.exists("Workflow", wf):
                continue
            doc = frappe.get_doc("Workflow", wf)
            groups: dict[tuple, list] = defaultdict(list)
            for t in doc.transitions:
                groups[(t.state, t.action, t.next_state)].append(t)
            for key, rows in groups.items():
                sa_rows = [r for r in rows if r.allowed == "AssetCore Super Admin"]
                non_admin = sorted(
                    {r.allowed for r in rows} - ADMIN_SET - {None, ""}
                )
                # Cần ĐÚNG 1 row Super Admin (flip nó là gỡ SA khỏi group) + 1 role
                # non-admin đang có sẵn để flip sang (không bịa role mới).
                if len(sa_rows) == 1 and non_admin:
                    target = (wf, sa_rows[0].name, key, non_admin[0])
                    break
            if target:
                break

        self.assertIsNotNone(
            target,
            "Không tìm được transition-group nào có đúng 1 row Super Admin + 1 role "
            "non-admin sẵn có để inject — không thể chứng minh guard cắn.",
        )
        wf, row_name, (state, action, next_state), replacement = target
        expected = (wf, state, action, next_state, ("AssetCore Super Admin",))
        try:
            frappe.db.set_value(
                "Workflow Transition", row_name, "allowed", replacement,
                update_modified=False,
            )
            frappe.clear_document_cache("Workflow", wf)  # buộc _live_groups đọc lại DB
            blocked = _blocked_live_groups([wf], ADMIN_SET)
            self.assertIn(
                expected, blocked,
                f"Guard KHÔNG bắt được group vừa strip Super Admin: expected {expected}, "
                f"blocked={blocked}",
            )
        finally:
            frappe.db.set_value(
                "Workflow Transition", row_name, "allowed", "AssetCore Super Admin",
                update_modified=False,
            )
            frappe.clear_document_cache("Workflow", wf)

        # Sau restore: group đó sạch trở lại (guard hết report) — chống drift để lại.
        self.assertNotIn(expected, _blocked_live_groups([wf], ADMIN_SET))

    # -- TC-DB-ADMIN-3 (scope / foreign-isolation) ----------------------------
    def test_scope_is_assetcore_only_and_size_22(self) -> None:
        """Chỉ 22 Workflow AssetCore được check; foreign multi-app KHÔNG bị assert."""
        scope = _scope_names()
        self.assertEqual(len(scope), 22)
        for name in _FOREIGN_SAMPLE:
            self.assertNotIn(name, scope)


if __name__ == "__main__":
    unittest.main()
