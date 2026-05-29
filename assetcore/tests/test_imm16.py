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

    @classmethod
    def tearDownClass(cls):
        """BUG-16-01: xoá fixture đã commit ở setUpClass để không rò rỉ
        dữ liệu test (``TEST-R-IMM08-PM-90``, "Test PM 90%") sang site
        thật. setUpClass commit nên rollback per-test không dọn được."""
        with suppress(Exception):
            # Mọi fixture test đều mang tiền tố TEST- (rule_code) hoặc tên
            # TEST-...; service nội bộ commit nên rollback per-test không
            # dọn được — phải xoá tường minh để không rò rỉ sang site thật.
            for dt, filt in (
                ("IMM Compliance Finding", {"rule": "TEST-R-IMM08-PM-90"}),
                ("IMM CAPA Record", {"name": ("like", "TEST-CAPA-%")}),
                ("IMM Compliance Scorecard", {"name": ("like", "TEST-SCR-%")}),
                ("IMM Management Review", {"name": ("like", "TEST-MR-%")}),
                ("IMM Internal Audit", {"name": ("like", "TEST-AUD-%")}),
                ("IMM Compliance Finding", {"name": ("like", "TEST-FND-%")}),
            ):
                for nm in frappe.get_all(dt, filters=filt, pluck="name"):
                    with suppress(Exception):
                        frappe.delete_doc(dt, nm, force=True,
                                          ignore_permissions=True,
                                          ignore_on_trash=True)
            # Scorecard test dùng autoname (SCR-YYYY-MM-#####) — dọn theo kỳ.
            for nm in frappe.get_all(
                "IMM Compliance Scorecard",
                filters={"period_year": 2026, "period_month": 4,
                         "scope": "Hospital", "score_pct": 87.5},
                pluck="name",
            ):
                with suppress(Exception):
                    frappe.delete_doc("IMM Compliance Scorecard", nm,
                                      force=True, ignore_permissions=True,
                                      ignore_on_trash=True)
            _delete_if_exists("IMM Compliance Rule", "TEST-R-IMM08-PM-90")
            frappe.db.commit()


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
        # Scorecard dùng autoname format: — không ép literal name được.
        # Dọn mọi scorecard test cùng kỳ trước, để Frappe tự sinh name.
        for nm in frappe.get_all(
            "IMM Compliance Scorecard",
            filters={"period_year": 2026, "period_month": 4,
                     "scope": "Hospital"},
            pluck="name",
        ):
            _delete_if_exists("IMM Compliance Scorecard", nm)
        sc_doc = frappe.get_doc({
            "doctype": "IMM Compliance Scorecard",
            "period_year": 2026, "period_month": 4,
            "scope": "Hospital", "score_pct": 87.5, "is_published": 0,
        })
        sc_doc.flags.ignore_mandatory = True
        sc_doc.insert(ignore_permissions=True)
        frappe.db.commit()
        sc_name = sc_doc.name
        # VR-10 gate: prev quarter (Q1-2026) phải KHÔNG có MR Closed để
        # khẳng định publish bị chặn. Đảm bảo cô lập dữ liệu.
        if frappe.db.exists("IMM Management Review",
                            {"quarter": "Q1-2026", "status": "Closed"}):
            self.skipTest("Site có MR Closed Q1-2026 — VR-10 gate không áp dụng")
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


# ── TC-16-12: get_record_history (audit trail) ─────────────────────────────

class TestRecordHistory(TestImm16Base):
    def test_history_validation(self):
        with self.assertRaises(ServiceError):
            svc.get_record_history("", "")

    def test_history_shape(self):
        res = svc.get_record_history("IMM Compliance Rule", self.rule)
        self.assertIn("items", res)
        self.assertIn("total", res)
        self.assertIsInstance(res["items"], list)

    def test_confirm_finding_writes_audit_trail(self):
        finding = _ensure(
            "IMM Compliance Finding", "TEST-FND-AUD-01",
            {
                "rule": self.rule,
                "detected_date": nowdate(),
                "evaluation_date": nowdate(),
                "severity": "High",
                "status": "Under Review",
            },
        )
        svc.confirm_finding(finding, "audit-test")
        hist = svc.get_record_history("IMM Compliance Finding", finding)
        self.assertGreaterEqual(hist["total"], 1)


# ── TC-16-13: reactivate_rule round-trip ───────────────────────────────────

class TestRuleReactivate(TestImm16Base):
    def test_deactivate_then_reactivate(self):
        svc.deactivate_rule(self.rule)
        self.assertEqual(
            frappe.db.get_value("IMM Compliance Rule", self.rule, "is_active"), 0)
        svc.reactivate_rule(self.rule)
        self.assertEqual(
            frappe.db.get_value("IMM Compliance Rule", self.rule, "is_active"), 1)


# ── TC-16-14: update_capa_fields + get_capa ────────────────────────────────

class TestCapaFieldsAndGet(TestImm16Base):
    def _capa(self) -> str:
        if not self.test_asset:
            self.skipTest("No AC Asset found")
        return _ensure(
            "IMM CAPA Record", "TEST-CAPA-FLD-01",
            {
                "asset": self.test_asset,
                "source_type": "Non-Conformance",
                "severity": "Major",
                "description": "Test fields",
                "opened_date": nowdate(),
                "due_date": add_days(nowdate(), 30),
                "responsible": "Administrator",
                "workflow_state": "Investigating",
                "status": "In Progress",
            },
        )

    def test_update_capa_fields_persists(self):
        capa = self._capa()
        svc.update_capa_fields(capa, {
            "root_cause": "RC narrative",
            "corrective_action": "CA narrative",
            "imm_root_cause_method": "5-Why",
        })
        doc = svc.get_capa(capa)
        self.assertEqual(doc["root_cause"], "RC narrative")
        self.assertEqual(doc["imm_root_cause_method"], "5-Why")

    def test_get_capa_not_found(self):
        with self.assertRaises(ServiceError):
            svc.get_capa("NON-EXISTENT-CAPA")


# ── TC-16-15: Management Review lifecycle (update + advance) ────────────────

class TestMRLifecycle(TestImm16Base):
    def _mr(self) -> str:
        return _ensure(
            "IMM Management Review", "TEST-MR-Q1-2099",
            {
                "quarter": "Q1-2099",
                "review_date": nowdate(),
                "chair": "Administrator",
                "status": "Draft",
                "workflow_state": "Draft",
            },
        )

    def test_advance_draft_to_held(self):
        mr = self._mr()
        res = svc.advance_mr_state(mr, "Held")
        self.assertEqual(res["status"], "Held")

    def test_advance_invalid_transition_rejected(self):
        mr = self._mr()
        with self.assertRaises(ServiceError):
            svc.advance_mr_state(mr, "Closed")

    def test_update_management_review_content(self):
        mr = self._mr()
        svc.update_management_review(mr, {
            "inputs_summary": "Đầu vào quý",
            "output_actions": [
                {"action_description": "Cải tiến PM", "responsible": "Administrator",
                 "due_date": add_days(nowdate(), 30)},
            ],
        })
        doc = svc.get_management_review(mr)
        self.assertEqual(doc["inputs_summary"], "Đầu vào quý")
        self.assertGreaterEqual(len(doc.get("output_actions") or []), 1)

    def test_finalize_requires_output_action(self):
        mr = self._mr()
        with self.assertRaises(ServiceError):
            svc.finalize_management_review(mr, minutes_doc="/files/m.pdf",
                                           output_actions=[])


# ── RC-03: CAPA tạo từ Incident + 2-way link (Incident ↔ CAPA ↔ RCA) ────────

class TestCAPAFromIncidentChain(unittest.TestCase):
    """RC-03: create_capa_from_incident() đảm bảo CAPA được tạo
    với 2-way link Incident.linked_capa + CAPA.linked_incident, idempotent.

    Service path: assetcore.services.imm16.create_capa_from_incident.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        # Resolve an existing asset for FK; nếu chưa có thì test skip.
        assets = frappe.get_all("AC Asset", limit=1, fields=["name"])
        cls.asset_name = assets[0].name if assets else None

    def setUp(self):
        if not self.asset_name:
            self.skipTest("Không có AC Asset trên site — RC-03 chain test cần asset")
        # Tạo incident High (severity High → severity_map → Major)
        from assetcore.services.imm12 import report_incident
        result = report_incident(
            asset=self.asset_name,
            incident_type="Malfunction",
            severity="High",
            description="_Test RC-03 CAPA chain — incident description",
            clinical_impact="Test clinical impact RC-03",
        )
        frappe.db.commit()
        self.incident_name = result["name"]

    def tearDown(self):
        # Cleanup theo thứ tự link: CAPA → RCA → Incident
        capa = frappe.db.get_value(
            "Incident Report", self.incident_name, "linked_capa"
        )
        if capa:
            with suppress(Exception):
                frappe.delete_doc(
                    "IMM CAPA Record", capa, force=True, ignore_permissions=True,
                )
        for rca in frappe.get_all(
            "IMM RCA Record",
            filters={"incident_report": self.incident_name},
            pluck="name",
        ):
            with suppress(Exception):
                frappe.delete_doc(
                    "IMM RCA Record", rca, force=True, ignore_permissions=True,
                )
        with suppress(Exception):
            frappe.delete_doc(
                "Incident Report", self.incident_name,
                force=True, ignore_permissions=True,
            )
        frappe.db.commit()

    def test_create_capa_from_incident_basic_link(self):
        """RC-03: gọi create_capa_from_incident → CAPA tồn tại + linked_incident set."""
        result = svc.create_capa_from_incident(
            incident_name=self.incident_name,
            rca_name="",
            responsible="Administrator",
        )
        frappe.db.commit()
        capa_name = result.get("capa_name")
        self.assertTrue(capa_name, "RC-03: phải trả về capa_name")
        self.assertTrue(frappe.db.exists("IMM CAPA Record", capa_name))
        # 2-way link
        self.assertEqual(
            frappe.db.get_value("IMM CAPA Record", capa_name, "linked_incident"),
            self.incident_name,
            "RC-03: CAPA.linked_incident phải trỏ về incident",
        )
        self.assertEqual(
            frappe.db.get_value("Incident Report", self.incident_name, "linked_capa"),
            capa_name,
            "RC-03: Incident.linked_capa phải trỏ về CAPA",
        )

    def test_create_capa_from_incident_idempotent(self):
        """RC-03: gọi 2 lần → reuse CAPA cũ (không tạo bản trùng)."""
        r1 = svc.create_capa_from_incident(
            incident_name=self.incident_name, responsible="Administrator",
        )
        frappe.db.commit()
        r2 = svc.create_capa_from_incident(
            incident_name=self.incident_name, responsible="Administrator",
        )
        frappe.db.commit()
        self.assertEqual(
            r1.get("capa_name"), r2.get("capa_name"),
            "RC-03: gọi lần 2 phải reuse CAPA (idempotent)",
        )
        self.assertTrue(r2.get("reused"), "RC-03: lần 2 phải có reused=True")

    def test_create_capa_links_back_to_rca(self):
        """RC-03: nếu truyền rca_name → CAPA cũng link với RCA."""
        # Tạo RCA gắn với incident
        from assetcore.services.imm12 import create_rca
        rca_info = create_rca(self.incident_name)
        frappe.db.commit()
        rca_name = rca_info["name"]

        result = svc.create_capa_from_incident(
            incident_name=self.incident_name,
            rca_name=rca_name,
            responsible="Administrator",
        )
        frappe.db.commit()
        capa_name = result["capa_name"]
        self.assertEqual(
            frappe.db.get_value("IMM RCA Record", rca_name, "linked_capa"),
            capa_name,
            "RC-03: RCA.linked_capa phải được set khi truyền rca_name",
        )

    def test_create_capa_from_invalid_incident_raises(self):
        """RC-03: incident không tồn tại → ServiceError NOT_FOUND."""
        with self.assertRaises(ServiceError):
            svc.create_capa_from_incident(
                incident_name="INVALID-IR-XXX",
                responsible="Administrator",
            )


class TestLLBE1Heatmap417(unittest.TestCase):
    """LL-BE-1 guard: GET endpoint phải tolerate query param numeric RỖNG
    (`?period_year=`) mà KHÔNG raise FrappeTypeError → HTTP 417.

    Hiện AN TOÀN vì `api/imm16.py` có `from __future__ import annotations`
    (PEP 563 → annotation là string → Frappe `validate_argument_types` SKIP
    coercion → không 417, dù hint là `int | None`). Test này GUARD chống
    regression nếu future-import bị gỡ hoặc annotation chuyển sang real-type
    (khi đó `int|None` + `""` sẽ 417 — xem dashboard.py không có future-import).

    Gọi qua `validate_argument_types(apply_condition=True)` mô phỏng request-context.
    """

    def test_heatmap_empty_period_no_417(self):
        from frappe.utils.typing_validations import validate_argument_types
        from assetcore.api.imm16 import get_compliance_heatmap

        wrapped = validate_argument_types(
            get_compliance_heatmap, apply_condition=lambda: True
        )
        # FE gửi ?period_year=&period_month= → trước fix: FrappeTypeError (417)
        resp = wrapped(period_year="", period_month="")
        self.assertIsInstance(resp, dict)

    def test_heatmap_missing_args_no_417(self):
        from frappe.utils.typing_validations import validate_argument_types
        from assetcore.api.imm16 import get_compliance_heatmap

        wrapped = validate_argument_types(
            get_compliance_heatmap, apply_condition=lambda: True
        )
        resp = wrapped()
        self.assertIsInstance(resp, dict)


if __name__ == "__main__":
    unittest.main()
