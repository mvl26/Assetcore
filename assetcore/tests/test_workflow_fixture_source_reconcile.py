# Copyright (c) 2026, AssetCore Team
"""INVARIANT 2-chiều khoá fixtures/workflow.json ⇄ 22 source workflow/*.json.

TRỤC A · CR-WF-FIXTURE-SRC-RECONCILE — fresh-install-seed-drift guard.

ROOT CAUSE (lỗ seed-path lệch nguồn):
  Có HAI đường nạp Workflow vào site, ĐỌC HAI NGUỒN KHÁC NHAU:
    - Fresh-install: `setup/install._sync_workflows()` glob thư mục SOURCE
      `assetcore/assetcore/workflow/*.json` rồi `import_doc` từng file.
    - `bench migrate` + fixture-import + `setup/backfill_workflow_admin.run` +
      MỌI invariant (test_workflows.py, test_workflow_admin_override.py) đọc
      FIXTURE `assetcore/fixtures/workflow.json`.
  Nếu 2 nguồn drift (vd một edge được bồi `System Manager` ở fixtures nhưng
  KHÔNG ở source, hoặc thêm/xoá 1 workflow một phía), site CÀI MỚI seed từ
  SOURCE sẽ THIẾU quyền → tái sinh CÂM bug "QTV/admin không duyệt được" mà mọi
  test hiện có (đọc fixtures) vẫn GREEN, không phát hiện.

GUARD (SoT 2-chiều): file này chốt source ⇄ fixture KHỚP HỆT trên:
  - INV-FXSRC-1: name-set (22 == 22, set-equal) — thêm/xoá 1 phía = RED.
  - INV-FXSRC-2: edge-set {(state, action, next_state, allowed)} — set-equal
    INCLUDING allowed role ⇒ drift admin-override 1 phía = RED.
  - INV-FXSRC-3: states-set {(state, doc_status, allow_edit)} + WF-level Check
    metadata (is_active/send_email_alert/override_status) parity (Check None->0
    normalize để KHÔNG false-RED do export-artifact).
  - INV-FXSRC-4: mọi transition-group ở CẢ source & fixture cấp {AssetCore Super
    Admin, System Manager} — chứng minh SOURCE (nguồn _sync_workflows dùng)
    KHÔNG thiếu quyền, không chỉ fixture.
  - INV-FXSRC-5 (RED-first, guard-bites proof): mutate bản copy in-memory (bỏ
    'System Manager' khỏi 1 edge source / thêm phantom edge fixture) → reconcile
    RAISE AssertionError; KHÔNG persist mutation.

FILE-driven (đọc JSON, KHÔNG query DB) ⇒ miễn nhiễm fixture-contamination —
KHÔNG đỏ do môi trường multi-session/leaked-fixture.

OUT-OF-SCOPE (backlog, cần USER duyệt reload): refactor `_sync_workflows()` để
đọc single-SoT từ fixtures/workflow.json (bỏ dual-source hẳn). Guard này CHỈ
đóng lỗ drift, KHÔNG đổi runtime .py.

Run:
  bench --site miyano run-tests --app assetcore \
      --module assetcore.tests.test_workflow_fixture_source_reconcile
"""
from __future__ import annotations

import copy
import glob
import json
import os
import unittest
from collections import defaultdict

import frappe

# Cả hai admin role PHẢI hiện diện trong MỌI transition-group của MỌI workflow —
# mirror `setup/backfill_workflow_admin.ADMIN_ROLES` (SoT sync live) + test_workflows.
_ADMIN_OVERRIDE = frozenset({"AssetCore Super Admin", "System Manager"})

# 22 AssetCore Workflow (Wave 1 + Wave 2) — nguồn seed fresh-install ⇄ fixtures.
_EXPECTED_WORKFLOW_COUNT = 22

# WF-level Check field: export-fixtures ghi 0, source hand-authored để None →
# normalize None->0 để tránh false-RED (đã phát hiện override_status src=None
# vs fx=0, benign). states/edges vẫn so STRICT.
_WF_CHECK_FIELDS = ("is_active", "send_email_alert", "override_status")


# --- Loaders (mirror scope backfill_workflow_admin._assetcore_workflow_names) -


def _load_source_workflows() -> dict[str, dict]:
    """Glob assetcore/assetcore/workflow/*.json → {workflow_name: wf_dict}.

    Đây CHÍNH là thư mục `setup/install._sync_workflows()` scan khi provision
    site MỚI — oracle độc lập với fixtures/workflow.json.
    """
    wf_dir = frappe.get_app_path("assetcore", "assetcore", "workflow")
    out: dict[str, dict] = {}
    for fp in sorted(glob.glob(os.path.join(wf_dir, "*.json"))):
        with open(fp, encoding="utf-8") as fh:
            wf = json.load(fh)
        out[wf.get("workflow_name")] = wf
    return out


def _load_fixture_workflows() -> dict[str, dict]:
    """Load assetcore/fixtures/workflow.json → {name: wf_dict} (doctype==Workflow).

    Mirror `test_workflow_admin_override._load_workflow_fixture` +
    `backfill_workflow_admin._assetcore_workflow_names` — KHÔNG bịa glob mới lệch
    scope. Fixture file của app chỉ chứa 22 Workflow AssetCore (foreign multi-app
    KHÔNG nằm trong fixture file này).
    """
    path = frappe.get_app_path("assetcore", "fixtures", "workflow.json")
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return {d.get("name"): d for d in data if d.get("doctype") == "Workflow"}


# --- Projections (chỉ giữ field nghiệp-vụ; bỏ noise export-artifact) ----------


def _norm_check(v):
    """Check field None <-> 0 (export-fixtures ghi 0, source để None)."""
    return 0 if v is None else v


def _edge_set(wf: dict) -> set[tuple]:
    """{(state, action, next_state, allowed)} — đơn vị Frappe enforce quyền."""
    return {
        (t.get("state"), t.get("action"), t.get("next_state"), t.get("allowed"))
        for t in wf.get("transitions", [])
    }


def _state_set(wf: dict) -> set[tuple]:
    """{(state, doc_status, allow_edit)} — doc_status str-normalize (strict)."""
    return {
        (s.get("state"), str(s.get("doc_status")), s.get("allow_edit"))
        for s in wf.get("states", [])
    }


def _transition_groups(wf: dict) -> dict[tuple, set]:
    """Gom `allowed` role theo (state, action, next_state)."""
    groups: dict[tuple, set] = defaultdict(set)
    for t in wf.get("transitions", []):
        groups[(t.get("state"), t.get("action"), t.get("next_state"))].add(t.get("allowed"))
    return dict(groups)


# --- Reconcile primitives (RAISE AssertionError on drift) ---------------------
#
# Đây là SoT logic khoá source⇄fixture. Test method gọi trên dữ liệu THẬT (không
# raise = GREEN); INV-FXSRC-5 gọi CHÍNH các hàm này trên bản copy đã mutate để
# chứng minh guard THỰC bite (RED-first), không no-op.


def _assert(condition: bool, msg: str) -> None:
    if not condition:
        raise AssertionError(msg)


def _reconcile_name_set(src: dict[str, dict], fx: dict[str, dict]) -> None:
    s, f = set(src), set(fx)
    _assert(
        s == f,
        f"name-set drift source⇄fixtures: src-only={sorted(s - f)}, "
        f"fx-only={sorted(f - s)}",
    )
    _assert(
        len(s) == _EXPECTED_WORKFLOW_COUNT,
        f"expected {_EXPECTED_WORKFLOW_COUNT} workflow, got source={len(s)} fixture={len(f)}",
    )


def _reconcile_edges(name: str, src_wf: dict, fx_wf: dict) -> None:
    se, fe = _edge_set(src_wf), _edge_set(fx_wf)
    _assert(
        se == fe,
        f"{name}: edge drift (INCL. allowed role) "
        f"only-source={sorted(se - fe)}, only-fixture={sorted(fe - se)}",
    )


def _reconcile_states(name: str, src_wf: dict, fx_wf: dict) -> None:
    ss, fs = _state_set(src_wf), _state_set(fx_wf)
    _assert(
        ss == fs,
        f"{name}: state drift (state, doc_status, allow_edit) "
        f"only-source={sorted(ss - fs)}, only-fixture={sorted(fs - ss)}",
    )
    for field in _WF_CHECK_FIELDS:
        sv, fv = _norm_check(src_wf.get(field)), _norm_check(fx_wf.get(field))
        _assert(
            sv == fv,
            f"{name}: WF-level Check '{field}' drift (norm None->0): "
            f"source={sv} fixture={fv}",
        )


def _reconcile_admin(name: str, wf: dict, origin: str) -> None:
    for key, roles in _transition_groups(wf).items():
        gap = _ADMIN_OVERRIDE - roles
        _assert(
            not gap,
            f"[{origin}] {name}: group {key} thiếu admin-override {sorted(gap)} "
            f"(QTV/admin bị chặn)",
        )


class TestWorkflowFixtureSourceReconcile(unittest.TestCase):
    """SoT 2-chiều: source workflow/*.json ⇄ fixtures/workflow.json."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.src = _load_source_workflows()
        cls.fx = _load_fixture_workflows()

    def test_inv_fxsrc_1_name_set(self) -> None:
        """INV-FXSRC-1: name-set(22 source workflow_name) == name-set(22 fixture name)."""
        # gọi reconcile primitive (raise = RED); thêm assert tường minh cho count.
        _reconcile_name_set(self.src, self.fx)
        self.assertEqual(len(self.src), _EXPECTED_WORKFLOW_COUNT)
        self.assertEqual(len(self.fx), _EXPECTED_WORKFLOW_COUNT)
        self.assertEqual(set(self.src), set(self.fx))

    def test_inv_fxsrc_2_edge_set(self) -> None:
        """INV-FXSRC-2: mỗi workflow, edge-set {(state,action,next_state,allowed)}
        source == fixture (bao gồm allowed → khoá admin-override drift 1 phía)."""
        drift: list[str] = []
        for name in sorted(set(self.src) | set(self.fx)):
            if name not in self.src or name not in self.fx:
                drift.append(f"{name}: thiếu 1 phía (INV-1 sẽ báo)")
                continue
            try:
                _reconcile_edges(name, self.src[name], self.fx[name])
            except AssertionError as e:
                drift.append(str(e))
        self.assertEqual(drift, [], "Edge reconcile drift:\n" + "\n".join(drift))

    def test_inv_fxsrc_3_states(self) -> None:
        """INV-FXSRC-3: states-set + per-state (doc_status, allow_edit) source ==
        fixture (strict); WF-level Check field normalize None->0."""
        drift: list[str] = []
        for name in sorted(set(self.src) | set(self.fx)):
            if name not in self.src or name not in self.fx:
                drift.append(f"{name}: thiếu 1 phía (INV-1 sẽ báo)")
                continue
            try:
                _reconcile_states(name, self.src[name], self.fx[name])
            except AssertionError as e:
                drift.append(str(e))
        self.assertEqual(drift, [], "State reconcile drift:\n" + "\n".join(drift))

    def test_inv_fxsrc_4_admin_override_both_sources(self) -> None:
        """INV-FXSRC-4: mọi transition-group ở CẢ source & fixture ⊇ {AssetCore
        Super Admin, System Manager} — chứng minh SOURCE không thiếu quyền."""
        blocked: list[str] = []
        for name in sorted(self.src):
            try:
                _reconcile_admin(name, self.src[name], "SOURCE")
            except AssertionError as e:
                blocked.append(str(e))
        for name in sorted(self.fx):
            try:
                _reconcile_admin(name, self.fx[name], "FIXTURE")
            except AssertionError as e:
                blocked.append(str(e))
        self.assertEqual(blocked, [], "Admin-override gap:\n" + "\n".join(blocked))

    def test_inv_fxsrc_5_guard_bites(self) -> None:
        """INV-FXSRC-5 (RED-first): reconcile primitives PHẢI raise AssertionError
        khi drift — mutate bản copy in-memory, KHÔNG persist ra file."""
        name = "IMM-02 Spec Workflow"
        self.assertIn(name, self.src)
        self.assertIn(name, self.fx)

        # Sanity: dữ liệu THẬT phải PASS (không raise) — nếu không, guard vô nghĩa.
        _reconcile_edges(name, self.src[name], self.fx[name])
        _reconcile_admin(name, self.src[name], "SOURCE")
        _reconcile_name_set(self.src, self.fx)

        # (a) Bỏ 'System Manager' khỏi 1 edge SOURCE (deep-copy) → admin gap + edge drift.
        src_mut = copy.deepcopy(self.src[name])
        victim = next(
            (t for t in src_mut["transitions"] if t.get("allowed") == "System Manager"),
            None,
        )
        self.assertIsNotNone(victim, f"{name} source thiếu edge System Manager để mutate")
        src_mut["transitions"] = [
            t for t in src_mut["transitions"]
            if not (
                t.get("state") == victim["state"]
                and t.get("action") == victim["action"]
                and t.get("next_state") == victim["next_state"]
                and t.get("allowed") == "System Manager"
            )
        ]
        with self.assertRaises(AssertionError):
            _reconcile_admin(name, src_mut, "SOURCE")
        with self.assertRaises(AssertionError):
            _reconcile_edges(name, src_mut, self.fx[name])

        # (b) Thêm phantom edge vào FIXTURE (deep-copy) → edge drift.
        fx_mut = copy.deepcopy(self.fx[name])
        fx_mut["transitions"].append(
            {
                "state": "__PHANTOM_STATE__",
                "action": "__PHANTOM_ACTION__",
                "next_state": "__PHANTOM_NEXT__",
                "allowed": "System Manager",
            }
        )
        with self.assertRaises(AssertionError):
            _reconcile_edges(name, self.src[name], fx_mut)

        # (c) Name-set drift (xoá 1 workflow 1 phía) → raise.
        src_drop = dict(self.src)
        src_drop.pop(name)
        with self.assertRaises(AssertionError):
            _reconcile_name_set(src_drop, self.fx)

        # KHÔNG persist: re-load fresh từ đĩa → phantom KHÔNG tồn tại, count == 22.
        fresh_src = _load_source_workflows()
        fresh_fx = _load_fixture_workflows()
        self.assertEqual(len(fresh_src), _EXPECTED_WORKFLOW_COUNT)
        self.assertEqual(len(fresh_fx), _EXPECTED_WORKFLOW_COUNT)
        self.assertNotIn(
            ("__PHANTOM_STATE__", "__PHANTOM_ACTION__", "__PHANTOM_NEXT__", "System Manager"),
            _edge_set(fresh_fx[name]),
            "Phantom edge bị PERSIST vào fixtures/workflow.json — mutation không được ghi đĩa!",
        )
        # SOURCE edge bị bỏ vẫn còn nguyên trên đĩa (deep-copy không đụng file).
        self.assertEqual(
            _edge_set(fresh_src[name]), _edge_set(self.src[name]),
            "Source edge-set trên đĩa bị đổi — mutation rò rỉ ra file!",
        )


if __name__ == "__main__":
    unittest.main()
