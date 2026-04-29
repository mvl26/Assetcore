# Copyright (c) 2026, AssetCore Team
"""Smoke tests for IMM-04..IMM-12 workflows.

Validates that all 8 workflows are imported, active, and contain the expected
states + transitions used by frontend client scripts.

Run: bench --site miyano run-tests --app assetcore --module assetcore.tests.test_workflows
"""
from __future__ import annotations

import unittest
import frappe


EXPECTED_WORKFLOWS = {
    "AC Asset Lifecycle": {"doctype": "AC Asset", "min_states": 8, "min_transitions": 14},
    "IMM-04 Workflow": {"doctype": "Asset Commissioning", "min_states": 11, "min_transitions": 20},
    "IMM-05 Document Workflow": {"doctype": "Asset Document", "min_states": 6, "min_transitions": 8},
    "IMM-08 PM Workflow": {"doctype": "PM Work Order", "min_states": 7, "min_transitions": 9},
    "IMM-09 Repair Workflow": {"doctype": "Asset Repair", "min_states": 9, "min_transitions": 10},
    "IMM-11 Calibration Workflow": {"doctype": "IMM Asset Calibration", "min_states": 8, "min_transitions": 11},
    "IMM-12 Incident Workflow": {"doctype": "Incident Report", "min_states": 7, "min_transitions": 8},
    "IMM-12 RCA Workflow": {"doctype": "IMM RCA Record", "min_states": 4, "min_transitions": 4},
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
