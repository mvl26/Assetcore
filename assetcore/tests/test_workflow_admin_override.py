# Copyright (c) 2026, AssetCore Team
"""RBAC guard — admin override PHẢI có trên MỌI workflow transition + SCOPE guard.

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

SCOPE GUARD (2026-07-09, memory `workflow_admin_override_rbac`): site miyano chạy
MULTI-APP (assetcore + mvl_accounting + antmed_crm + workflowcore) → `run()` cũ dùng
`frappe.get_all("Workflow")` đã clone-append admin-role vào CẢ workflow của app khác
('MVL Duyệt thanh toán', 'Cong Tac Approval'). Các test dưới chốt: (a) `run()` CHỈ chạm
đúng 22 workflow AssetCore (SoT = fixtures/workflow.json); (b) `revert_foreign()` gỡ
đúng các row clone-append đã nhiễm sang foreign, giữ nguyên row gốc, idempotent.

Run:
  bench --site miyano run-tests --app assetcore \
      --module assetcore.tests.test_workflow_admin_override
"""
from __future__ import annotations

import glob
import json
import os
import unittest
from collections import defaultdict
from types import SimpleNamespace

import frappe

from assetcore.setup import backfill_workflow_admin as bwa

# Admin god-mode override — khớp 13 workflow đang hoạt động (Super Admin + System Manager).
_ADMIN_ROLES = {"AssetCore Super Admin", "System Manager"}

# Workflow của app KHÁC trên site chung — KHÔNG được nằm trong scope AssetCore.
_FOREIGN_SAMPLE = {"MVL Duyệt thanh toán", "Cong Tac Approval"}


def _load_workflow_fixture() -> list[dict]:
    path = frappe.get_app_path("assetcore", "fixtures", "workflow.json")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _fixture_workflow_names() -> set[str]:
    """Tên Workflow parse TRỰC TIẾP từ fixtures/workflow.json (oracle độc lập)."""
    return {
        d.get("name")
        for d in _load_workflow_fixture()
        if d.get("doctype") == "Workflow"
    }


def _groups_of(wf: dict) -> dict[tuple, set]:
    """Gom transitions của 1 Workflow theo (state, action, next_state) → set(allowed)."""
    groups: dict[tuple, set] = defaultdict(set)
    for t in wf.get("transitions", []):
        groups[(t.get("state"), t.get("action"), t.get("next_state"))].add(t.get("allowed"))
    return groups


def _source_workflow_files() -> list[str]:
    """MỌI file workflow NGUỒN assetcore/assetcore/workflow/*.json.

    Đây chính là path mà seed fresh-install (`_sync_workflows`) `import_doc` khi
    provision site mới — oracle ĐỘC LẬP với fixtures/workflow.json.
    """
    wf_dir = frappe.get_app_path("assetcore", "assetcore", "workflow")
    return sorted(glob.glob(os.path.join(wf_dir, "*.json")))


def _load_source_workflow(path: str) -> dict:
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


class TestBackfillScope(unittest.TestCase):
    """Helper thuần `_assetcore_workflow_names()` = SoT scope, không chạm live DB."""

    def test_scope_equals_fixture_workflows(self) -> None:
        # Helper thuần PHẢI == tập tên Workflow parse trực tiếp từ fixtures/workflow.json.
        self.assertEqual(bwa._assetcore_workflow_names(), _fixture_workflow_names())
        # 22 workflow AssetCore (Wave 1+2).
        self.assertEqual(len(bwa._assetcore_workflow_names()), 22)

    def test_scope_excludes_foreign(self) -> None:
        # Workflow của app khác TUYỆT ĐỐI không nằm trong scope AssetCore.
        scope = bwa._assetcore_workflow_names()
        for name in _FOREIGN_SAMPLE:
            self.assertNotIn(name, scope)

    def test_run_touches_only_assetcore(self) -> None:
        # run(dry_run=1) chỉ được lặp/đụng đúng tập AssetCore — per_workflow ⊆ scope,
        # KHÔNG xuất hiện workflow foreign (kể cả khi live có foreign đã nhiễm).
        res = bwa.run(dry_run=1)
        touched = set(res["per_workflow"].keys())
        scope = bwa._assetcore_workflow_names()
        self.assertTrue(
            touched <= scope,
            f"run() chạm workflow NGOÀI scope AssetCore: {sorted(touched - scope)}",
        )
        for name in _FOREIGN_SAMPLE:
            self.assertNotIn(name, touched)


def _row(state, action, next_state, allowed, condition=None,
         allow_self_approval=0, send_email_to_creator=0, name=None):
    """Fake Workflow Transition row (đủ field _CLONE_FIELDS + allowed + name)."""
    return SimpleNamespace(
        state=state, action=action, next_state=next_state, allowed=allowed,
        condition=condition, allow_self_approval=allow_self_approval,
        send_email_to_creator=send_email_to_creator, name=name,
    )


class TestRevertForeign(unittest.TestCase):
    """`_clone_appended_admin_rows` gỡ đúng row do run() clone-append, giữ row gốc,
    idempotent — test THUẦN trên fake rows (deterministic, không chạm live DB)."""

    def _foreign_transitions_polluted(self):
        """2 group, mỗi group 1 row gốc (non-admin) + 2 clone admin (như run() sinh)."""
        rows = []
        # group A: gốc + 2 clone
        rows.append(_row("Draft", "Gửi duyệt", "Chờ duyệt", "Ke Toan MVL",
                         condition="doc.total>0", name="A0"))
        rows.append(_row("Draft", "Gửi duyệt", "Chờ duyệt", "AssetCore Super Admin",
                         condition="doc.total>0", name="A1"))
        rows.append(_row("Draft", "Gửi duyệt", "Chờ duyệt", "System Manager",
                         condition="doc.total>0", name="A2"))
        # group B: gốc + 2 clone
        rows.append(_row("Chờ duyệt", "Duyệt", "Đã duyệt", "Truong Phong", name="B0"))
        rows.append(_row("Chờ duyệt", "Duyệt", "Đã duyệt", "AssetCore Super Admin",
                         name="B1"))
        rows.append(_row("Chờ duyệt", "Duyệt", "Đã duyệt", "System Manager", name="B2"))
        return rows

    def test_revert_foreign_targets_only_added_rows(self) -> None:
        rows = self._foreign_transitions_polluted()
        to_remove = bwa._clone_appended_admin_rows(rows)
        removed_names = {r.name for r in to_remove}

        # Gỡ đúng 4 clone admin (2 group × 2 admin role) — KHÔNG chạm row gốc.
        self.assertEqual(removed_names, {"A1", "A2", "B1", "B2"})
        # Mọi row bị gỡ đều là admin-role.
        for r in to_remove:
            self.assertIn(r.allowed, _ADMIN_ROLES)
        # Row gốc (non-admin) TUYỆT ĐỐI không bị đụng.
        self.assertNotIn("A0", removed_names)
        self.assertNotIn("B0", removed_names)

        # Idempotent: sau khi gỡ, chạy lại → 0 row (chỉ còn row gốc).
        remaining = [r for r in rows if r.name not in removed_names]
        self.assertEqual(bwa._clone_appended_admin_rows(remaining), [])

    def test_revert_keeps_genuine_non_clone_admin(self) -> None:
        # Row admin KHÔNG phải clone của template (condition khác) = coi như gốc,
        # GIỮ nguyên (run() không sinh row lệch template).
        rows = [
            _row("Draft", "Gửi", "Chờ", "Ke Toan", condition="A", name="G0"),
            _row("Draft", "Gửi", "Chờ", "System Manager", condition="B", name="G1"),
        ]
        self.assertEqual(bwa._clone_appended_admin_rows(rows), [])


class TestRevertForeignLive(unittest.TestCase):
    """Integration nhẹ: revert_foreign(dry_run=1) chỉ nhắm foreign, shape ổn định."""

    def test_revert_foreign_scope_and_shape(self) -> None:
        res = bwa.revert_foreign(dry_run=1)
        self.assertEqual(set(res.keys()) >= {"removed", "per_workflow", "dry_run"}, True)
        self.assertEqual(res["dry_run"], True)
        scope = bwa._assetcore_workflow_names()
        # revert TUYỆT ĐỐI không nhắm workflow AssetCore.
        for name in res["per_workflow"]:
            self.assertNotIn(name, scope)
        # removed == tổng per_workflow (đếm nhất quán).
        self.assertEqual(res["removed"], sum(res["per_workflow"].values()))


class TestSourceWorkflowFiles(unittest.TestCase):
    """Guard SEED-PATH fresh-install — parse TRỰC TIẾP file workflow nguồn.

    ROOT CAUSE bổ sung (2026-07-11): fixtures/workflow.json đã GREEN (admin phủ mọi
    group), NHƯNG file NGUỒN `assetcore/assetcore/workflow/*.json` — thứ mà seed
    fresh-install `_sync_workflows` `import_doc` khi provision site MỚI — vẫn thiếu
    admin override trên nhiều transition-group. Site cài mới sẽ seed từ file nguồn
    (KHÔNG từ fixtures export) ⇒ QTV lại bị WorkflowPermissionError ngay từ đầu.

    Oracle ĐỘC LẬP với `TestWorkflowAdminOverride` (đọc fixtures): các test dưới đọc
    THẲNG file nguồn. Invariant giống nhau — mọi (state, action, next_state) PHẢI cho
    phép CẢ 2 admin role — nhưng nguồn dữ liệu khác ⇒ bắt được drift fixtures↔nguồn.
    """

    def test_every_individual_workflow_transition_group_allows_admin(self) -> None:
        blocked: list[tuple] = []
        for path in _source_workflow_files():
            wf = _load_source_workflow(path)
            for key, roles in _groups_of(wf).items():
                missing = _ADMIN_ROLES - roles
                if missing:
                    blocked.append(
                        (os.path.basename(path), wf.get("name"), *key, tuple(sorted(missing)))
                    )
        files = sorted({b[0] for b in blocked})
        self.assertEqual(
            blocked, [],
            f"{len(files)} file / {len(blocked)} transition-group NGUỒN thiếu admin "
            f"(fresh-install _sync_workflows seed thiếu → QTV bị chặn). files={files}; "
            + "; ".join(f"{f}:{s}--{a}-->{n} thiếu {list(m)}"
                        for f, w, s, a, n, m in blocked[:12]),
        )

    def test_individual_files_match_fixture_admin_coverage(self) -> None:
        # (a) Tập tên Workflow suy từ file nguồn == tên trong fixtures (22) — scope parity.
        src_names = {_load_source_workflow(p).get("name") for p in _source_workflow_files()}
        fx_names = _fixture_workflow_names()
        self.assertEqual(
            src_names, fx_names,
            f"Tên Workflow file-nguồn lệch fixtures: "
            f"src-only={sorted(src_names - fx_names)}, fx-only={sorted(fx_names - src_names)}",
        )
        self.assertEqual(len(src_names), 22)

        # (b) admin-coverage per-group file-nguồn ⊇ admin-coverage fixtures (0 drift):
        #     mọi group có admin ở fixtures PHẢI có admin đó ở file nguồn.
        fx = {
            d.get("name"): _groups_of(d)
            for d in _load_workflow_fixture()
            if d.get("doctype") == "Workflow"
        }
        src = {
            _load_source_workflow(p).get("name"): _groups_of(_load_source_workflow(p))
            for p in _source_workflow_files()
        }
        drift: list[tuple] = []
        for name, fgroups in fx.items():
            sgroups = src.get(name, {})
            for key, froles in fgroups.items():
                missing = (froles & _ADMIN_ROLES) - (sgroups.get(key, set()) & _ADMIN_ROLES)
                if missing:
                    drift.append((name, *key, tuple(sorted(missing))))
        self.assertEqual(
            drift, [],
            f"{len(drift)} group: admin-coverage file-nguồn KHÔNG phủ fixtures: "
            + "; ".join(f"{w}:{s}--{a}-->{n} thiếu {list(m)}"
                        for w, s, a, n, m in drift[:12]),
        )

    def test_no_extra_role_added(self) -> None:
        """Hyrum-safe: fix CHỈ được APPEND 2 admin role — KHÔNG role lạ, KHÔNG xoá row cũ.

        Oracle độc lập = fixtures/workflow.json (SoT GREEN). (a) mọi role ở file nguồn
        phải nằm trong fixtures cùng-tên (workflow-level) HOẶC là 1 trong 2 admin role
        → chặn role lạ (typo / thêm nhầm). (b) mọi non-admin role mà SoT (fixtures) khai
        cho 1 group vẫn còn nguyên ở file nguồn → chứng minh APPEND-only, không xoá row cũ.
        """
        fx = {
            d.get("name"): _groups_of(d)
            for d in _load_workflow_fixture()
            if d.get("doctype") == "Workflow"
        }
        rogue: list[tuple] = []
        dropped: list[tuple] = []
        for path in _source_workflow_files():
            wf = _load_source_workflow(path)
            name = wf.get("name")
            sgroups = _groups_of(wf)
            fgroups = fx.get(name, {})
            src_roles = set().union(*sgroups.values()) if sgroups else set()
            fx_roles = set().union(*fgroups.values()) if fgroups else set()
            # (a) role lạ = có ở nguồn, KHÔNG ở fixtures, và KHÔNG phải admin.
            extra = src_roles - fx_roles - _ADMIN_ROLES
            if extra:
                rogue.append((os.path.basename(path), name, tuple(sorted(extra))))
            # (b) non-admin row của SoT phải còn ở nguồn (append-only, không xoá).
            for key, froles in fgroups.items():
                lost = (froles - _ADMIN_ROLES) - (sgroups.get(key, set()) - _ADMIN_ROLES)
                if lost:
                    dropped.append((name, *key, tuple(sorted(lost))))
        self.assertEqual(
            rogue, [],
            f"Role lạ (ngoài fixtures + 2 admin) xuất hiện ở file nguồn: {rogue[:12]}",
        )
        self.assertEqual(
            dropped, [],
            f"Row non-admin cũ (SoT) bị mất khỏi file nguồn (vi phạm APPEND-only): "
            + "; ".join(f"{w}:{s}--{a}-->{n} mất {list(m)}"
                        for w, s, a, n, m in dropped[:12]),
        )


if __name__ == "__main__":
    unittest.main()
