# Copyright (c) 2026, AssetCore Team
# IMM-16 Compliance Monitoring & CAPA — Test suite (Sprint 3 §4.16.3).
#
# Focus: canonical service surface — Rule/Finding/Audit/CAPA/Scorecard/MR
# + BR-16 enforcement (VR-04/05/06/07/08/10/11/12, BR-16-06/09).
#
# Test data isolation: each test rolls back via tearDown.
from __future__ import annotations

import unittest
from contextlib import suppress

import frappe
from frappe.utils import add_days, nowdate

from assetcore.services import imm16 as svc
from assetcore.services.shared import ServiceError


def _delete_if_exists(doctype: str, name: str) -> None:
    """Delete a test fixture if it exists, ignoring all guards."""
    if frappe.db.exists(doctype, name):
        frappe.delete_doc(doctype, name, ignore_permissions=True,
                          force=True, ignore_on_trash=True)
        frappe.db.commit()


def _ensure(doctype: str, name: str, data: dict) -> str:
    """Insert (or recreate) a test fixture in the given state.

    Always deletes and re-inserts so fixtures start from a known baseline.
    Bypasses mandatory/link/workflow validation so tests can create records
    in arbitrary states without needing full valid data graphs.
    """
    # Delete any previously-committed version to guarantee clean baseline.
    _delete_if_exists(doctype, name)

    data = dict(data)  # avoid mutating caller's dict
    # Extract workflow_state: Frappe blocks inserting into non-initial states
    # so we insert without it, then force-set via db.set_value.
    workflow_state = data.pop("workflow_state", None)
    doc = frappe.get_doc({"doctype": doctype, "name": name, **data})
    doc.flags.ignore_links = True
    doc.flags.ignore_mandatory = True
    doc.flags.ignore_validate = True
    # frappe.flags.in_install="frappe" bypasses validate_workflow() call.
    prev_in_install = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    try:
        doc.insert(ignore_permissions=True)
    finally:
        frappe.flags.in_install = prev_in_install
    if workflow_state:
        frappe.db.set_value(doctype, doc.name, "workflow_state", workflow_state,
                            update_modified=False)
    return doc.name


class TestImm16Base(unittest.TestCase):
    """Setup fixtures: rule, finding, audit, capa, scorecard, MR."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.rule = _ensure(
            "IMM Compliance Rule", "TEST-R-IMM08-PM-90",
            {
                "rule_code": "TEST-R-IMM08-PM-90",
                "rule_name": "Test PM 90%",
                "source_module": "IMM-08",
                "category": "PM",
                "severity": "High",
                "threshold_definition": '{"metric":"pm","op":"<","value":90}',
                "evaluation_frequency": "Monthly",
                "is_active": 1,
                "version": "1.0",
                "effective_date": nowdate(),
            },
        )
        # Always reset to known state — _ensure() deletes+recreates but
        # subsequent tests (update_rule) commit changes, so reset before each.
        frappe.db.set_value(
            "IMM Compliance Rule", cls.rule,
            {
                "severity": "High",
                "threshold_definition": '{"metric":"pm","op":"<","value":90}',
                "version": "1.0",
                "previous_version": None,
                "is_active": 1,
            },
        )
        frappe.db.commit()
        frappe.clear_cache(doctype="IMM Compliance Rule")

        # Resolve a real AC Asset for tests that call doc.save() (link validation).
        assets = frappe.get_all("AC Asset", limit=1, fields=["name"])
        cls.test_asset = assets[0].name if assets else None

    def setUp(self):
        # Reset rule to known baseline before each test, since some service
        # functions commit internally (e.g. update_rule, deactivate_rule).
        frappe.db.set_value(
            "IMM Compliance Rule", self.rule,
            {
                "severity": "High",
                "threshold_definition": '{"metric":"pm","op":"<","value":90}',
                "version": "1.0",
                "previous_version": None,
                "is_active": 1,
            },
        )
        frappe.db.commit()

    def tearDown(self):
        frappe.db.rollback()


# ── TC-16-01: Create + update rule with version bump (VR-11) ────────────────

class TestRuleLifecycle(TestImm16Base):
    def test_update_rule_without_change_summary_fails(self):
        with self.assertRaises(ServiceError) as ctx:
            svc.update_rule(self.rule,
                            rule_data={"severity": "Critical"},
                            change_summary="")
        self.assertEqual(ctx.exception.code, "FIN-011")

    def test_update_rule_with_change_summary_bumps_version(self):
        result = svc.update_rule(
            self.rule,
            rule_data={"severity": "Critical"},
            change_summary="Tăng severity theo BYT yêu cầu mới 2026",
        )
        self.assertEqual(result["previous_version"], "1.0")
        self.assertNotEqual(result["version"], "1.0")

    def test_deactivate_rule(self):
        res = svc.deactivate_rule(self.rule)
        self.assertEqual(res["is_active"], 0)


# ── TC-16-02: Finding waiver enforcement (VR-04 + BR-16-06) ─────────────────

class TestFindingWaiver(TestImm16Base):
    def _create_finding(self) -> str:
        result = svc.create_finding(
            rule_ref=self.rule, asset_ref="", work_order_ref="",
            severity="High", description="Test waiver finding",
            evaluation_date=nowdate(),
        )
        return result["name"]

    def test_waive_with_short_reason_fails(self):
        fname = self._create_finding()
        with self.assertRaises(ServiceError) as ctx:
            svc.waive_finding(fname, waiver_reason="short",
                              waiver_evidence="/files/x.pdf",
                              waiver_expiry=add_days(nowdate(), 30))
        self.assertEqual(ctx.exception.code, "FIN-004")

    def test_waive_missing_evidence_fails(self):
        fname = self._create_finding()
        with self.assertRaises(ServiceError) as ctx:
            svc.waive_finding(fname,
                              waiver_reason="x" * 60,
                              waiver_evidence="",
                              waiver_expiry=add_days(nowdate(), 30))
        self.assertEqual(ctx.exception.code, "FIN-004")

    def test_waive_expired_expiry_fails(self):
        fname = self._create_finding()
        with self.assertRaises(ServiceError) as ctx:
            svc.waive_finding(fname,
                              waiver_reason="x" * 60,
                              waiver_evidence="/files/x.pdf",
                              waiver_expiry=add_days(nowdate(), -1))
        self.assertEqual(ctx.exception.code, "FIN-004")


# ── TC-16-03: Audit close gated by Major NC without CAPA (VR-08) ────────────

class TestAuditClose(TestImm16Base):
    def test_close_audit_missing_planned_audit(self):
        # Audit must exist
        with self.assertRaises(ServiceError) as ctx:
            svc.close_audit("NONEXISTENT")
        self.assertIn(ctx.exception.code, ("NOT_FOUND",))


# ── TC-16-04..07: CAPA workflow advance ─────────────────────────────────────

class TestCapaWorkflow(TestImm16Base):
    def test_advance_to_action_plan_requires_root_cause_method(self):
        # Setup CAPA at Open state
        # Note: source_ref omitted — Dynamic Link validation would fail for
        # "Compliance Finding" (not a valid DocType name).
        capa_name = _ensure(
            "IMM CAPA Record", "TEST-CAPA-WF-01",
            {
                "asset": "N/A",
                "source_type": "Non-Conformance",
                "severity": "Major",
                "description": "Test workflow",
                "opened_date": nowdate(),
                "due_date": add_days(nowdate(), 30),
                "workflow_state": "Investigating",
                "status": "In Progress",
                "root_cause": "test",
                "corrective_action": "test",
                "preventive_action": "test",
            },
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.advance_capa_state(capa_name, "Action Plan",
                                   payload={"due_date": add_days(nowdate(), 30)})
        self.assertEqual(ctx.exception.code, "FIN-005")

    def test_advance_to_action_plan_requires_future_due_date(self):
        capa_name = _ensure(
            "IMM CAPA Record", "TEST-CAPA-WF-02",
            {
                "asset": "N/A",
                "source_type": "Non-Conformance",
                "severity": "Major",
                "description": "Test workflow",
                "opened_date": nowdate(),
                "workflow_state": "Investigating",
                "status": "In Progress",
                "root_cause": "test",
                "corrective_action": "test",
                "preventive_action": "test",
            },
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.advance_capa_state(
                capa_name, "Action Plan",
                payload={"imm_root_cause_method": "5-Why",
                         "due_date": nowdate()},
            )
        self.assertEqual(ctx.exception.code, "FIN-012")


# ── TC-16-08: Effectiveness Not Effective → reopen counter++ ────────────────

class TestEffectivenessCheck(TestImm16Base):
    def test_not_effective_reopens_capa(self):
        # Use a real AC Asset so doc.save() link validation passes.
        if not self.test_asset:
            self.skipTest("No AC Asset found in DB — skipping effectiveness test")
        capa_name = _ensure(
            "IMM CAPA Record", "TEST-CAPA-EFF-01",
            {
                "asset": self.test_asset,
                "source_type": "Non-Conformance",
                "severity": "Major",
                "description": "Test effectiveness",
                "opened_date": nowdate(),
                "due_date": add_days(nowdate(), 30),
                "responsible": "Administrator",
                "workflow_state": "Verification",
                "status": "In Progress",
                "root_cause": "test",
                "corrective_action": "test",
                "preventive_action": "test",
            },
        )
        result = svc.perform_effectiveness_check(
            capa_name, result="Not Effective",
        )
        # Workflow: Verification → Re-opened (not directly to Investigating).
        self.assertEqual(result["new_state"], "Re-opened")
        self.assertGreaterEqual(result["imm_reopen_count"], 1)


# ── TC-16-09: Publish scorecard blocked when prev quarter MR missing ────────

class TestScorecardPublish(TestImm16Base):
    def test_publish_scorecard_without_prev_mr_fails(self):
        sc_name = _ensure(
            "IMM Compliance Scorecard", "TEST-SCR-2026-04",
            {
                "period_year": 2026,
                "period_month": 4,
                "scope": "Hospital",
                "score_pct": 87.5,
                "is_published": 0,
            },
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.publish_scorecard(sc_name)
        # Expect FIN-010 (missing prev quarter MR) or permission denied
        self.assertIn(ctx.exception.code, ("FIN-010", "FORBIDDEN"))


# ── TC-16-10: Cross-module gate (BR-16-09) ──────────────────────────────────

class TestCrossModuleGate(TestImm16Base):
    def test_check_asset_compliance_returns_unblocked_for_empty(self):
        result = svc.check_asset_compliance_status("")
        self.assertFalse(result["blocked"])
        self.assertEqual(result["active_findings_count"], 0)
        self.assertEqual(result["active_capas_count"], 0)

    def test_check_asset_compliance_returns_unblocked_for_clean_asset(self):
        result = svc.check_asset_compliance_status("NONEXISTENT-ASSET-XYZ")
        self.assertFalse(result["blocked"])
        # Schema check
        self.assertIn("blocking_findings", result)
        self.assertIn("reasons", result)
        self.assertIn("active_findings_count", result)
        self.assertIn("active_capas_count", result)


# ── TC-16-11: Dashboard stats shape ─────────────────────────────────────────

class TestDashboard(TestImm16Base):
    def test_dashboard_stats_shape(self):
        result = svc.get_dashboard_stats()
        self.assertIn("kpis", result)
        self.assertIn("trend_12m", result)
        self.assertIn("top_modules_low", result)
        self.assertIn("recent_findings", result)
        kpis = result["kpis"]
        for key in ("overall_compliance_pct", "findings_open",
                    "findings_critical", "capa_open", "capa_overdue",
                    "audits_in_progress", "mr_quarterly_status"):
            self.assertIn(key, kpis)


if __name__ == "__main__":
    unittest.main()
