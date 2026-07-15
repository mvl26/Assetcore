# Copyright (c) 2026, AssetCore Team
"""Smoke + RBAC-invariant tests cho 22 AssetCore Workflow (Wave 1 + Wave 2).

Hai nhóm:
  1. Smoke (DB-driven): mỗi workflow tồn tại, active, đúng DocType, đủ state/
     transition, không vi phạm docstatus rule, role tham chiếu tồn tại
     (TestWorkflowsRegistered / DocstatusValidity / RolesExist / IMM12 / IMM11).

  2. Admin-override + parity invariant (FILE-driven — đọc thẳng JSON, KHÔNG lệ
     thuộc DB nên miễn nhiễm fixture-contamination):
       - INV-A test_source_transitions_grant_admin_override: MỌI transition-group
         trong MỌI file assetcore/assetcore/workflow/*.json phải cấp CẢ hai admin
         role {AssetCore Super Admin, System Manager}.
       - INV-B test_fixture_transitions_grant_admin_override: y hệt cho 22 workflow
         AssetCore trong fixtures/workflow.json (lọc foreign multi-app theo tên
         source).
       - INV-C test_source_fixture_transition_parity: map {(state,action,next_state)
         -> set(roles)} KHỚP HỆT giữa source JSON ⇄ fixtures — khoá drift giữa 2
         install-path (fresh-install `_sync_workflows` đọc source · `bench migrate`
         import fixtures).

VÌ SAO admin-override (LL-BE-62 + memory `workflow_admin_override_rbac`):
  Frappe enforce quyền workflow theo TỪNG transition group; `ignore_permissions=
  True` KHÔNG bypass `validate_workflow`. Profile "Quản trị viên IT" (QTV) chỉ
  cấp role `AssetCore Super Admin` — mọi transition thiếu role này ⇒ QTV bị
  WorkflowPermissionError ("Bạn không có quyền …"). Guard khoá regression "QTV
  không duyệt được" trên CẢ hai install-path.

Run: bench --site miyano run-tests --app assetcore --module assetcore.tests.test_workflows
"""
from __future__ import annotations

import glob
import json
import os
import unittest
from collections import defaultdict

import frappe

# --- Admin-override + parity invariant helpers (FILE-driven) -----------------

# Cả hai admin role PHẢI hiện diện trong MỌI transition group của MỌI workflow
# AssetCore. Mirror `setup/backfill_workflow_admin.ADMIN_ROLES` (SoT sync live).
_ADMIN_OVERRIDE = frozenset({"AssetCore Super Admin", "System Manager"})


def _source_workflow_dir() -> str:
    """Thư mục source workflow JSON — CÙNG thư mục `_sync_workflows` scan."""
    return frappe.get_app_path("assetcore", "assetcore", "workflow")


def _load_source_workflows() -> list[tuple[str, dict]]:
    """Glob mọi file source workflow → list (basename, wf_dict).

    Data-driven: đọc TỪ thư mục nên workflow mới thêm vào folder TỰ ĐỘNG được
    kiểm (KHÔNG hardcode danh sách 22 trong assert-path).
    """
    out: list[tuple[str, dict]] = []
    for fp in sorted(glob.glob(os.path.join(_source_workflow_dir(), "*.json"))):
        with open(fp, encoding="utf-8") as fh:
            out.append((os.path.basename(fp), json.load(fh)))
    return out


def _source_workflow_names() -> set[str]:
    """Tập tên 22 Workflow AssetCore, đọc từ source JSON (SoT scope)."""
    return {wf.get("name") for _bn, wf in _load_source_workflows()}


def _fixture_assetcore_workflows() -> dict[str, dict]:
    """{name: wf_dict} cho các Workflow AssetCore trong fixtures/workflow.json.

    Lọc theo tập tên source (mirror `backfill_workflow_admin._assetcore_workflow_
    names`) để BỎ QUA foreign workflow của mvl_accounting/antmed_crm/workflowcore
    trên DB/fixtures shared — KHÔNG áp invariant AssetCore lên domain app khác.
    """
    path = frappe.get_app_path("assetcore", "fixtures", "workflow.json")
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    names = _source_workflow_names()
    return {
        d.get("name"): d
        for d in data
        if d.get("doctype") == "Workflow" and d.get("name") in names
    }


def _transition_groups(wf: dict) -> dict[tuple[str, str, str], set[str]]:
    """Gom `allowed` role theo (state, action, next_state).

    Mirror logic gom-group của `setup/backfill_workflow_admin` — Frappe enforce
    quyền theo group này, nên đây là đơn vị đúng để kiểm admin-override + parity.
    """
    groups: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for t in wf.get("transitions", []):
        key = (t.get("state"), t.get("action"), t.get("next_state"))
        groups[key].add(t.get("allowed"))
    return dict(groups)


EXPECTED_WORKFLOWS = {
    "AC Asset Lifecycle": {"doctype": "AC Asset", "min_states": 8, "min_transitions": 14},
    # Wave 2 — Planning & Procurement
    "IMM-01 Needs Workflow": {"doctype": "IMM Needs Request", "min_states": 8, "min_transitions": 20},
    "IMM-01 Plan Workflow": {"doctype": "IMM Procurement Plan", "min_states": 4, "min_transitions": 4},
    "IMM-02 Spec Workflow": {"doctype": "IMM Tech Spec", "min_states": 7, "min_transitions": 9},
    "IMM-03 AVL Workflow": {"doctype": "IMM AVL Entry", "min_states": 5, "min_transitions": 7},
    "IMM-03 Vendor Eval Workflow": {"doctype": "IMM Vendor Evaluation", "min_states": 5, "min_transitions": 6},
    "IMM-03 Decision Workflow": {"doctype": "IMM Procurement Decision", "min_states": 9, "min_transitions": 8},
    # Wave 1
    "IMM-04 Workflow": {"doctype": "Asset Commissioning", "min_states": 11, "min_transitions": 20},
    "IMM-05 Document Workflow": {"doctype": "Asset Document", "min_states": 6, "min_transitions": 8},
    "IMM-06 Session Workflow": {"doctype": "IMM Training Session", "min_states": 7, "min_transitions": 14},
    "IMM-06 Competency Workflow": {"doctype": "IMM User Competency", "min_states": 6, "min_transitions": 7},
    "IMM-08 PM Workflow": {"doctype": "PM Work Order", "min_states": 7, "min_transitions": 9},
    "IMM-09 Repair Workflow": {"doctype": "Asset Repair", "min_states": 9, "min_transitions": 10},
    "IMM-11 Calibration Workflow": {"doctype": "IMM Asset Calibration", "min_states": 8, "min_transitions": 11},
    "IMM-12 Incident Workflow": {"doctype": "Incident Report", "min_states": 7, "min_transitions": 8},
    "IMM-12 RCA Workflow": {"doctype": "IMM RCA Record", "min_states": 4, "min_transitions": 4},
    "IMM-15 Spare Allocation Workflow": {"doctype": "IMM Spare Allocation", "min_states": 6, "min_transitions": 12},
    "IMM-15 Cycle Count Workflow": {"doctype": "IMM Stock Cycle Count", "min_states": 4, "min_transitions": 4},
    "IMM-16 Compliance Finding Workflow": {"doctype": "IMM Compliance Finding", "min_states": 7, "min_transitions": 8},
    "IMM-16 CAPA Workflow": {"doctype": "IMM CAPA Record", "min_states": 7, "min_transitions": 7},
    "IMM-16 Internal Audit Workflow": {"doctype": "IMM Internal Audit", "min_states": 4, "min_transitions": 3},
    "IMM-16 Management Review Workflow": {"doctype": "IMM Management Review", "min_states": 4, "min_transitions": 3},
}


class TestWorkflowsRegistered(unittest.TestCase):
    """Mỗi workflow phải tồn tại, active, và đúng DocType."""

    def test_all_workflows_active(self):
        for name, expected in EXPECTED_WORKFLOWS.items():
            with self.subTest(workflow=name):
                self.assertTrue(
                    frappe.db.exists("Workflow", name),
                    f"Workflow {name} chưa tồn tại trong DB",
                )
                wf = frappe.get_doc("Workflow", name)
                self.assertEqual(wf.is_active, 1, f"{name} chưa active")
                self.assertEqual(
                    wf.document_type, expected["doctype"],
                    f"{name} document_type sai: expected {expected['doctype']}, got {wf.document_type}",
                )

    def test_workflow_state_counts(self):
        for name, expected in EXPECTED_WORKFLOWS.items():
            with self.subTest(workflow=name):
                wf = frappe.get_doc("Workflow", name)
                self.assertGreaterEqual(
                    len(wf.states), expected["min_states"],
                    f"{name}: states count {len(wf.states)} < {expected['min_states']}",
                )
                self.assertGreaterEqual(
                    len(wf.transitions), expected["min_transitions"],
                    f"{name}: transitions count {len(wf.transitions)} < {expected['min_transitions']}",
                )


class TestWorkflowDocstatusValidity(unittest.TestCase):
    """Frappe cấm các transition vi phạm docstatus rule."""

    VALID_TRANSITIONS = {
        ("0", "0"), ("0", "1"), ("1", "1"), ("1", "2"),
    }

    def test_no_invalid_docstatus_transitions(self):
        for name in EXPECTED_WORKFLOWS:
            with self.subTest(workflow=name):
                wf = frappe.get_doc("Workflow", name)
                state_status = {s.state: s.doc_status for s in wf.states}
                for t in wf.transitions:
                    from_ds = state_status.get(t.state)
                    to_ds = state_status.get(t.next_state)
                    self.assertIsNotNone(from_ds, f"{name}: state {t.state} không có doc_status")
                    self.assertIsNotNone(to_ds, f"{name}: state {t.next_state} không có doc_status")
                    self.assertIn(
                        (str(from_ds), str(to_ds)), self.VALID_TRANSITIONS,
                        f"{name}: transition {t.state}({from_ds}) → {t.next_state}({to_ds}) "
                        f"vi phạm Frappe docstatus rule",
                    )


class TestWorkflowRolesExist(unittest.TestCase):
    """Mỗi role được workflow dùng phải tồn tại trong DB."""

    def test_all_roles_exist(self):
        used_roles = set()
        for name in EXPECTED_WORKFLOWS:
            wf = frappe.get_doc("Workflow", name)
            for s in wf.states:
                if s.allow_edit:
                    used_roles.add(s.allow_edit)
            for t in wf.transitions:
                if t.allowed:
                    used_roles.add(t.allowed)

        for role in used_roles:
            with self.subTest(role=role):
                self.assertTrue(
                    frappe.db.exists("Role", role),
                    f"Role '{role}' được workflow tham chiếu nhưng không tồn tại",
                )


class TestIMM12IncidentRCAGate(unittest.TestCase):
    """IMM-12 Incident workflow phải có RCA gate (BR-12-02)."""

    def test_rca_required_state_present(self):
        wf = frappe.get_doc("Workflow", "IMM-12 Incident Workflow")
        states = {s.state for s in wf.states}
        self.assertIn("RCA Required", states, "IMM-12 thiếu state 'RCA Required'")

    def test_resolved_to_rca_required_transition(self):
        wf = frappe.get_doc("Workflow", "IMM-12 Incident Workflow")
        match = [t for t in wf.transitions
                 if t.state == "Resolved" and t.next_state == "RCA Required"]
        self.assertGreater(len(match), 0,
                           "IMM-12 thiếu transition Resolved → RCA Required")
        # Phải có condition kiểm tra severity hoặc requires_rca
        cond = (match[0].condition or "").lower()
        self.assertTrue(
            "severity" in cond or "requires_rca" in cond,
            f"Transition Resolved→RCA Required thiếu condition: {match[0].condition}",
        )

    def test_rca_required_to_closed_transition(self):
        wf = frappe.get_doc("Workflow", "IMM-12 Incident Workflow")
        match = [t for t in wf.transitions
                 if t.state == "RCA Required" and t.next_state == "Closed"]
        self.assertGreater(len(match), 0,
                           "IMM-12 thiếu transition RCA Required → Closed")


class TestIMM11CapaTransition(unittest.TestCase):
    """IMM-11 phải có Failed → Conditionally Passed sau CAPA."""

    def test_failed_to_conditionally_passed(self):
        wf = frappe.get_doc("Workflow", "IMM-11 Calibration Workflow")
        match = [t for t in wf.transitions
                 if t.state == "Failed" and t.next_state == "Conditionally Passed"]
        self.assertGreater(len(match), 0,
                           "IMM-11 thiếu transition Failed → Conditionally Passed")
        cond = (match[0].condition or "").lower()
        self.assertIn("capa_closed", cond,
                      f"Transition thiếu condition capa_closed: {match[0].condition}")


class TestWorkflowAdminOverrideInvariant(unittest.TestCase):
    """Bất-biến admin-override + parity source⇄fixtures (FILE-driven).

    VÌ SAO (LL-BE-62): Frappe enforce quyền workflow theo TỪNG transition group;
    `ignore_permissions=True` KHÔNG bypass `validate_workflow`. QTV (profile
    "Quản trị viên IT") chỉ có role `AssetCore Super Admin` → mọi transition-group
    thiếu role này = WorkflowPermissionError ("QTV không duyệt được"). Guard khoá
    regression đó trên CẢ hai install-path: fresh-install (`_sync_workflows` đọc
    source JSON) VÀ `bench migrate` (import fixtures/workflow.json).

    FILE-driven (đọc JSON, KHÔNG query DB) ⇒ miễn nhiễm fixture-contamination —
    KHÔNG đỏ do môi trường như test_imm09/test_imm00.
    """

    def test_source_transitions_grant_admin_override(self):
        """INV-A: MỌI transition-group trong MỌI source JSON ⊇ _ADMIN_OVERRIDE."""
        missing: list[tuple] = []
        for basename, wf in _load_source_workflows():
            for (state, action, next_state), roles in _transition_groups(wf).items():
                gap = _ADMIN_OVERRIDE - roles
                if gap:
                    missing.append((basename, state, action, next_state, sorted(gap)))
        self.assertEqual(
            missing, [],
            "Source transition-group thiếu admin-override "
            "(file, state, action, next_state, missing_roles):\n"
            + "\n".join(str(m) for m in missing),
        )

    def test_fixture_transitions_grant_admin_override(self):
        """INV-B: MỌI transition-group của 22 AssetCore workflow trong fixtures
        ⊇ _ADMIN_OVERRIDE; foreign multi-app workflow bị lọc theo tên source."""
        fx = _fixture_assetcore_workflows()
        # Foreign workflow (mvl/antmed/workflowcore) bị loại → tập fixtures đúng
        # bằng tập source (data-driven, KHÔNG hardcode 22 — glob source suy ra).
        self.assertEqual(
            set(fx.keys()), _source_workflow_names(),
            "Tập AssetCore workflow trong fixtures phải KHỚP tập source "
            "(foreign bị lọc, KHÔNG thiếu workflow source nào):\n"
            f"  chỉ-source={sorted(_source_workflow_names() - set(fx.keys()))}\n"
            f"  chỉ-fixture={sorted(set(fx.keys()) - _source_workflow_names())}",
        )
        missing: list[tuple] = []
        for name, wf in fx.items():
            for (state, action, next_state), roles in _transition_groups(wf).items():
                gap = _ADMIN_OVERRIDE - roles
                if gap:
                    missing.append((name, state, action, next_state, sorted(gap)))
        self.assertEqual(
            missing, [],
            "Fixture transition-group thiếu admin-override "
            "(workflow, state, action, next_state, missing_roles):\n"
            + "\n".join(str(m) for m in missing),
        )

    def test_source_fixture_transition_parity(self):
        """INV-C: map {(state,action,next_state) -> set(roles)} KHỚP HỆT giữa
        source JSON ⇄ fixtures cho MỖI workflow — khoá 0 drift giữa install-path
        fresh-install (`_sync_workflows` đọc source) và migrate (import fixtures).
        """
        source = {wf.get("name"): _transition_groups(wf)
                  for _bn, wf in _load_source_workflows()}
        fixture = {name: _transition_groups(wf)
                   for name, wf in _fixture_assetcore_workflows().items()}

        drift: list[str] = []
        for name in sorted(source):
            s = source[name]
            f = fixture.get(name)
            if f is None:
                drift.append(f"{name}: KHÔNG có trong fixtures/workflow.json")
                continue
            if s == f:
                continue
            only_src = {k: sorted(s[k]) for k in sorted(s.keys() - f.keys())}
            only_fix = {k: sorted(f[k]) for k in sorted(f.keys() - s.keys())}
            role_diff = {
                k: {"source": sorted(s[k]), "fixture": sorted(f[k])}
                for k in sorted(s.keys() & f.keys()) if s[k] != f[k]
            }
            drift.append(
                f"{name}:\n"
                f"    only_source_edges={only_src}\n"
                f"    only_fixture_edges={only_fix}\n"
                f"    role_diff={role_diff}"
            )
        self.assertEqual(
            drift, [],
            "Source⇄fixtures transition parity drift (install-path divergence):\n"
            + "\n".join(drift),
        )
