# Copyright (c) 2026, AssetCore Team
# IMM-16 Compliance Monitoring & CAPA — Test suite (Sprint 3 §4.16.3).
#
# Focus: canonical service surface — Rule/Finding/Audit/CAPA/Scorecard/MR
# + BR-16 enforcement (VR-04/05/06/07/08/10/11/12, BR-16-06/09).
#
# Test data isolation: each test rolls back via tearDown.
from __future__ import annotations

import json
import time
import unittest
from contextlib import suppress
from unittest.mock import patch

import frappe
from frappe.utils import add_days, nowdate

from assetcore.services import imm16 as svc
from assetcore.services.imm16 import FindingStatus
from assetcore.services.shared import ErrorCode, ServiceError


def _delete_if_exists(doctype: str, name: str) -> None:
    """Delete a test fixture if it exists, ignoring all guards."""
    if frappe.db.exists(doctype, name):
        frappe.delete_doc(doctype, name, ignore_permissions=True,
                          force=True, ignore_on_trash=True)
        frappe.db.commit()


def tearDownModule():  # noqa: N802
    """Module-level safety net: AC Asset / IMM CAPA Record are autonamed, so the
    requested fixture names ("TEST-GATE-ASSET-01" / "TEST-CAPA-%") are IGNORED on
    insert (LL-TEST-9) → per-test _delete_if_exists never matches and leaks
    'Gate Test Asset' / 'Gate Cron Asset' + placeholder CAPAs. Purge by marker."""
    from assetcore.tests._asset_cleanup import purge_assets_by_name_prefix
    frappe.set_user("Administrator")
    # Test CAPAs (placeholder narratives) first so the assets become FK-free.
    for nm in frappe.db.sql_list(
        "SELECT name FROM `tabIMM CAPA Record` WHERE "
        "description IN ('Test effectiveness', 'Test fields', 'Gate test critical CAPA') "
        "OR description LIKE 'Eval round%%' "
        "OR (root_cause = 'test' AND corrective_action = 'test') "
        "OR (root_cause = 'RC narrative' AND corrective_action = 'CA narrative') "
        "OR root_cause LIKE 'Eval %%narrative'"
    ):
        with suppress(Exception):
            frappe.delete_doc("IMM CAPA Record", nm, force=True,
                              ignore_permissions=True, ignore_on_trash=True)
    purge_assets_by_name_prefix("Gate Test Asset", "Gate Cron Asset")
    frappe.db.commit()


def _ensure_user(email: str, roles: list[str]) -> str:
    """Create (recreate) a System User carrying exactly ``roles`` for RBAC tests."""
    if frappe.db.exists("User", email):
        frappe.delete_doc("User", email, force=True, ignore_permissions=True)
    doc = frappe.get_doc({
        "doctype": "User",
        "email": email,
        "first_name": email.split("@")[0],
        "enabled": 1,
        "user_type": "System User",
        "send_welcome_email": 0,
        "roles": [{"role": r} for r in roles],
    })
    doc.flags.ignore_permissions = True
    doc.insert()
    frappe.db.commit()
    return email


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
            # IMM CAPA Record is autonamed (CAPA-YYYY-#####) → the "TEST-CAPA-%"
            # name filter above NEVER matches effectiveness fixtures (LL-TEST-9),
            # so they leaked onto the real asset. Purge by their test markers.
            for nm in frappe.db.sql_list(
                "SELECT name FROM `tabIMM CAPA Record` WHERE "
                "description IN ('Test effectiveness', 'Test fields') "
                "OR description LIKE 'Eval round%%' "
                "OR (root_cause = 'test' AND corrective_action = 'test') "
                "OR (root_cause = 'RC narrative' AND corrective_action = 'CA narrative') "
                "OR root_cause LIKE 'Eval %%narrative'"
            ):
                with suppress(Exception):
                    frappe.delete_doc("IMM CAPA Record", nm, force=True,
                                      ignore_permissions=True, ignore_on_trash=True)
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


# ── TC-16-03b: Internal Audit server-driven CTA + state machine + audit-trail ─
# ADR-IMM-16-02 / VR-13 / BR-16-10 (docs/imm-16/02 §US-16-05, 04 §III.C.1, 07
# AA-16-1..12). SSoT _AUDIT_VALID_TRANSITIONS + capability flags + Reporting-
# before-Close guard + 1-record-per-action audit trail.

class TestAuditServerDrivenLifecycle(TestImm16Base):
    """Internal Audit vòng đời server-driven: allowed_transitions/can_operate/
    can_close, Reporting-before-Close (VR-13), audit-trail 1 record/thao tác."""

    def _mk_audit(self, code: str, status: str = "Planned") -> str:
        """Dựng 1 IMM Internal Audit ở ``status`` (autoname → trả tên thật).
        Cleanup theo ``audit_code`` prefix (name bị autoname ghi đè)."""
        return _ensure(
            "IMM Internal Audit", code,
            {
                "audit_code": code,
                "audit_type": "Internal",
                "planned_start": nowdate(),
                "planned_end": nowdate(),
                # lead_auditor mandatory — start/complete gọi doc.save() re-validate.
                "lead_auditor": "Administrator",
                "status": status,
            },
        )

    def _mk_audit_with_items(self, code: str, item_count: int = 4,
                             status: str = "In Progress") -> str:
        """Audit ở ``status`` kèm ``item_count`` checklist item (auto idx 1..N).
        Dùng cho CR-27b: kiểm tra verdict round-trip vào child ``result``."""
        return _ensure(
            "IMM Internal Audit", code,
            {
                "audit_code": code,
                "audit_type": "Internal",
                "planned_start": nowdate(),
                "planned_end": nowdate(),
                "lead_auditor": "Administrator",
                "status": status,
                "checklist_items": [
                    {"item_description": f"Muc kiem tra {i}"}
                    for i in range(1, item_count + 1)
                ],
            },
        )

    @staticmethod
    def _count_audit_events(ref_name: str, event_type: str | None = None) -> int:
        filt = {"ref_doctype": "IMM Internal Audit", "ref_name": ref_name}
        if event_type:
            filt["event_type"] = event_type
        return frappe.db.count("IMM Audit Trail", filt)

    # AA-16-1..5 — allowed_transitions map + safe-default cho status lạ.
    def test_get_audit_allowed_transitions_by_status(self):
        cases = {
            "Planned": ["start"],
            "In Progress": ["complete_checklist"],
            "Reporting": ["close"],
            "Closed": [],
        }
        for status, expected in cases.items():
            name = self._mk_audit(f"TEST-AUDSD-AT-{status.replace(' ', '')}", status)
            data = svc.get_audit(name)
            self.assertEqual(data["allowed_transitions"], expected,
                             f"status={status}")
        # status rỗng/lạ → [] (safe-default .get, KHÔNG KeyError)
        weird = self._mk_audit("TEST-AUDSD-AT-WEIRD", "Planned")
        frappe.db.set_value("IMM Internal Audit", weird, "status",
                            "Zzz-Unknown", update_modified=False)
        data = svc.get_audit(weird)
        self.assertEqual(data["allowed_transitions"], [])

    # AA-16-6 — capability flags derive server-side + FORBIDDEN close.
    def test_get_audit_capability_flags(self):
        name = self._mk_audit("TEST-AUDSD-CAP", "Reporting")

        def only_write(cap, doc=None):
            return {"compliance.write": True, "compliance.submit": False}.get(cap, False)

        with patch.object(svc.rbac, "can", side_effect=only_write):
            data = svc.get_audit(name)
            self.assertTrue(data["can_operate"])
            self.assertFalse(data["can_close"])
            with self.assertRaises(ServiceError) as ctx:
                svc.close_audit(name)
            self.assertEqual(ctx.exception.code, ErrorCode.FORBIDDEN)

        def with_submit(cap, doc=None):
            return {"compliance.write": True, "compliance.submit": True}.get(cap, False)

        with patch.object(svc.rbac, "can", side_effect=with_submit):
            data = svc.get_audit(name)
            self.assertTrue(data["can_operate"])
            self.assertTrue(data["can_close"])

    # AA-16-7/8 — complete_audit_checklist In Progress→Reporting; Planned → BAD_STATE.
    def test_complete_checklist_moves_to_reporting(self):
        name = self._mk_audit("TEST-AUDSD-CK", "Planned")
        svc.start_audit(name)  # → In Progress
        res = svc.complete_audit_checklist(name, [])
        self.assertEqual(res["status"], svc.AuditStatus.REPORTING)
        self.assertEqual(svc.get_audit(name)["status"], "Reporting")

        # Gọi complete lúc PLANNED (chưa start) → BAD_STATE (bỏ nhánh Planned)
        name2 = self._mk_audit("TEST-AUDSD-CK2", "Planned")
        with self.assertRaises(ServiceError) as ctx:
            svc.complete_audit_checklist(name2, [])
        self.assertEqual(ctx.exception.code, ErrorCode.BAD_STATE)

    # AA-16-9/11 — close chặn jump-skip (In Progress) rồi cho close từ Reporting.
    def test_close_audit_blocked_before_reporting(self):
        name = self._mk_audit("TEST-AUDSD-CL", "Planned")
        svc.start_audit(name)  # → In Progress
        with self.assertRaises(ServiceError) as ctx:
            svc.close_audit(name)  # jump-skip từ In Progress
        self.assertEqual(ctx.exception.code, ErrorCode.BAD_STATE)
        # Đưa về Reporting rồi close → Closed
        svc.complete_audit_checklist(name, [])
        res = svc.close_audit(name)
        self.assertEqual(res["status"], svc.AuditStatus.CLOSED)

    # AA-16-10 — VR-08 regression: từ Reporting còn Major NC chưa CAPA → FIN-008.
    def test_close_audit_still_blocks_major_nc_without_capa(self):
        name = self._mk_audit("TEST-AUDSD-NC", "Reporting")
        _ensure(
            "IMM Compliance Finding", "TEST-FND-AUDNC-01",
            {
                "rule": self.rule,
                "source_record_doctype": "IMM Internal Audit",
                "source_record": name,
                "detected_date": nowdate(),
                "evaluation_date": nowdate(),
                "severity": "High",
                "status": "Open",
            },
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.close_audit(name)
        self.assertEqual(ctx.exception.code, "FIN-008")

    # AA-16-12 — mỗi start/checklist/close ghi ĐÚNG 1 IMM Audit Trail record.
    def test_audit_lifecycle_writes_audit_trail(self):
        # Đếm DELTA (không tuyệt đối): IMM Audit Trail append-only (ISO 13485:
        # 7.5.9) → row các run trước KHÔNG xoá được; autoname series roll-back bởi
        # test không-commit ⇒ ref_name có thể trùng run trước. Delta cô lập đúng
        # +1 record/thao tác + đúng event_type của run này.
        name = self._mk_audit("TEST-AUDSD-TRAIL", "Planned")

        def evt(event_type=None):
            return self._count_audit_events(name, event_type)

        c0, s0 = evt(), evt("audit_started")
        svc.start_audit(name)
        self.assertEqual(evt(), c0 + 1)
        self.assertEqual(evt("audit_started"), s0 + 1)

        k0 = evt("audit_checklist_completed")
        svc.complete_audit_checklist(name, [])
        self.assertEqual(evt(), c0 + 2)
        self.assertEqual(evt("audit_checklist_completed"), k0 + 1)

        z0 = evt("audit_closed")
        svc.close_audit(name)
        self.assertEqual(evt(), c0 + 3)
        self.assertEqual(evt("audit_closed"), z0 + 1)

    # AA-16-13 (guard-detect, CR-WF-16-AUDIT) — legacy submit_audit_findings SIẾT
    # về linear: chỉ In Progress. RED-before round 22: guard `not in
    # (IN_PROGRESS, PLANNED)` cho Planned→Reporting skip-start.
    def test_legacy_submit_findings_rejects_planned(self):
        name = self._mk_audit("TEST-AUDSD-LEGSUB", "Planned")
        with self.assertRaises(ServiceError) as ctx:
            svc.submit_audit_findings(name, [])   # skip-start từ Planned
        self.assertEqual(ctx.exception.code, ErrorCode.BAD_STATE)
        # In Progress vẫn hợp lệ (linear) → Reporting.
        svc.start_audit(name)
        res = svc.submit_audit_findings(name, [])
        self.assertEqual(res["status"], svc.AuditStatus.REPORTING)

    # AA-16-14 (guard-detect) — legacy close_internal_audit SIẾT về linear: chỉ
    # Reporting (VR-13 parity close_audit). RED-before: guard `== CLOSED` cho
    # đóng từ mọi non-Closed (Planned/In Progress) → bypass cổng Reporting.
    def test_legacy_close_internal_rejects_non_reporting(self):
        name = self._mk_audit("TEST-AUDSD-LEGCL", "Planned")
        with self.assertRaises(ServiceError) as ctx:
            svc.close_internal_audit(name)        # close từ Planned
        self.assertEqual(ctx.exception.code, ErrorCode.BAD_STATE)
        svc.start_audit(name)                     # → In Progress
        with self.assertRaises(ServiceError) as ctx2:
            svc.close_internal_audit(name)        # close từ In Progress
        self.assertEqual(ctx2.exception.code, ErrorCode.BAD_STATE)
        # Reporting → close hợp lệ.
        svc.complete_audit_checklist(name, [])
        res = svc.close_internal_audit(name)
        self.assertEqual(res["status"], svc.AuditStatus.CLOSED)

    # CR-27b (silent-verdict-loss) — RED-first: verdict finding_status PHẢI
    # round-trip vào child.result qua _FINDING_STATUS_TO_RESULT. Trước fix:
    # hasattr(child,"finding_status")==False → NO-OP câm → result rỗng hết (RED).
    def test_complete_checklist_persists_result_from_finding_status(self):
        name = self._mk_audit_with_items("TEST-AUDSD-RESULT", item_count=4,
                                         status="In Progress")
        svc.complete_audit_checklist(name, [
            {"idx": 1, "finding_status": "Compliant"},
            {"idx": 2, "finding_status": "Minor NC"},
            {"idx": 3, "finding_status": "Major NC"},
            {"idx": 4, "finding_status": "N/A"},
        ])
        rows = sorted(svc.get_audit(name)["checklist_items"],
                      key=lambda r: r["idx"])
        self.assertEqual(
            [r.get("result") for r in rows],
            ["Conforming", "Non-Conforming", "Non-Conforming", "Not Applicable"],
            "verdict finding_status phải round-trip vào child.result (CR-27b)")

    # CR-27b regression (0 hồi quy) — mở rộng test_complete_checklist_moves_to_
    # reporting: Major+Minor NC vẫn chạy nhánh Finding + state→Reporting + notes
    # persist + đúng 1 audit-event; verdict-mapping KHÔNG phá hành vi cũ.
    def test_complete_checklist_still_creates_findings_and_reporting(self):
        name = self._mk_audit_with_items("TEST-AUDSD-REGR", item_count=2,
                                         status="In Progress")
        ev0 = self._count_audit_events(name, "audit_checklist_completed")
        res = svc.complete_audit_checklist(name, [
            {"idx": 1, "finding_status": "Major NC", "notes": "Thiếu hồ sơ hiệu chuẩn"},
            {"idx": 2, "finding_status": "Minor NC", "notes": "Nhãn UDI mờ"},
        ])
        # state In Progress → Reporting (KHÔNG đổi).
        self.assertEqual(res["status"], svc.AuditStatus.REPORTING)
        self.assertEqual(svc.get_audit(name)["status"], "Reporting")
        # notes vẫn persist + result mapped song song.
        rows = sorted(svc.get_audit(name)["checklist_items"],
                      key=lambda r: r["idx"])
        self.assertEqual([r.get("notes") for r in rows],
                         ["Thiếu hồ sơ hiệu chuẩn", "Nhãn UDI mờ"])
        self.assertEqual([r.get("result") for r in rows],
                         ["Non-Conforming", "Non-Conforming"])
        # đúng 1 audit-event/thao tác (delta, append-only trail).
        self.assertEqual(
            self._count_audit_events(name, "audit_checklist_completed"), ev0 + 1)
        # CR-27d: nhánh NC nay auto-sinh IMM Compliance Finding THỰC (rule đã
        # resolve — clause_ref→rule đang có, else fallback IMM-16-AUDIT-NC).
        # 2 NC (Major+Minor) ⇒ 2 Finding persist. Guard 0-hồi-quy: fix result-
        # mapping (CR-27b) song song vẫn giữ verdict→child.result đúng.
        self.assertEqual(res["findings_created"], 2)

    # CR-27c (bug-fix hiện trường): audit tạo qua flow THẬT có 0 checklist_items
    # (create_internal_audit/start_audit KHÔNG seed child). Trước fix:
    # complete_audit_checklist loop qua 0 row → verdict + notes MẤT TRẮNG câm,
    # items_count=len(payload) success-giả. Sau fix: APPEND child từ payload
    # idx chưa-match → verdict persist vào child.result, count phản ánh THỰC.
    def test_complete_checklist_appends_rows_when_audit_unseeded(self):
        name = self._mk_audit("TEST-AUDSD-APPEND", status="Planned")
        svc.start_audit(name)  # Planned → In Progress; KHÔNG seed child row nào
        res = svc.complete_audit_checklist(name, [
            {"idx": 1, "finding_status": "Compliant", "notes": "Dat"},
            {"idx": 2, "finding_status": "Major NC", "notes": "Thieu ho so",
             "clause_ref": "7.5.9"},
            {"idx": 3, "finding_status": "Minor NC", "notes": "Nhan mo"},
        ])
        rows = sorted(svc.get_audit(name)["checklist_items"],
                      key=lambda r: r["idx"])
        # verdict KHÔNG còn mất trắng: 3 row persist với result mapped.
        self.assertEqual(len(rows), 3,
                         "checklist rows phải APPEND khi audit chưa seed child")
        self.assertEqual([r.get("result") for r in rows],
                         ["Conforming", "Non-Conforming", "Non-Conforming"])
        self.assertEqual([r.get("notes") for r in rows],
                         ["Dat", "Thieu ho so", "Nhan mo"])
        # item_description reqd=1 → phải điền (fallback clause_ref / 'Mục kiểm tra N').
        self.assertTrue(all(r.get("item_description") for r in rows),
                        "item_description (reqd) phải được điền khi append")
        # items_count phản ánh số THỰC persist (hết success-giả).
        self.assertEqual(res["items_count"], 3)
        self.assertEqual(res["status"], svc.AuditStatus.REPORTING)

    # ── CR-27d: auto-sinh IMM Compliance Finding từ Major/Minor NC ──────────
    # Nhánh NC trước đây NO-OP CÂM: rule="" (child KHÔNG có rule_ref → getattr
    # trả "") → MandatoryError bị except nuốt → findings_created=0. Fix: resolve
    # rule (clause_ref → rule đang có, else fallback IMM-16-AUDIT-NC) + create
    # THỰC; findings_created LUÔN == số IMM Compliance Finding doc persist.
    @staticmethod
    def _audit_findings(audit_name, fields=None):
        return frappe.get_all(
            "IMM Compliance Finding",
            filters={"source_record_doctype": "IMM Internal Audit",
                     "source_record": audit_name},
            fields=fields or ["name", "severity", "rule"],
            order_by="creation asc",
        )

    def test_complete_checklist_creates_findings_from_nc(self):
        """RED-first (flip guard): 1 Major + 1 Minor NC ⇒ findings_created==2.
        FAIL trên code cũ (trả 0 — no-op câm) TRƯỚC khi fix."""
        name = self._mk_audit_with_items("TEST-AUDSD-NCFIND", item_count=2,
                                         status="In Progress")
        res = svc.complete_audit_checklist(name, [
            {"idx": 1, "finding_status": "Major NC",
             "notes": "Thiếu hồ sơ hiệu chuẩn"},
            {"idx": 2, "finding_status": "Minor NC", "notes": "Nhãn UDI mờ"},
        ])
        self.assertEqual(res["findings_created"], 2)

    def test_findings_actually_persist_in_db(self):
        """Persist THẬT (không đếm len payload): sau complete, đúng 2 IMM
        Compliance Finding tồn tại theo source_record; severity High + Medium
        (Major NC→High, Minor NC→Medium)."""
        name = self._mk_audit_with_items("TEST-AUDSD-PERSIST", item_count=2,
                                         status="In Progress")
        svc.complete_audit_checklist(name, [
            {"idx": 1, "finding_status": "Major NC", "notes": "NC lớn"},
            {"idx": 2, "finding_status": "Minor NC", "notes": "NC nhỏ"},
        ])
        rows = self._audit_findings(name)
        self.assertEqual(len(rows), 2, "đúng 2 Finding THỰC persist trong DB")
        self.assertEqual(sorted(r["severity"] for r in rows), ["High", "Medium"])

    def test_finding_has_nonempty_resolved_rule(self):
        """Mỗi Finding sinh ra có rule != '' và rule đó tồn tại trong IMM
        Compliance Rule (chống MandatoryError câm khi rule rỗng)."""
        name = self._mk_audit_with_items("TEST-AUDSD-RULE", item_count=1,
                                         status="In Progress")
        svc.complete_audit_checklist(name, [
            {"idx": 1, "finding_status": "Major NC", "notes": "NC"},
        ])
        rows = self._audit_findings(name)
        self.assertEqual(len(rows), 1)
        rule = rows[0]["rule"]
        self.assertTrue(rule, "rule PHẢI non-empty (đã resolve)")
        self.assertTrue(frappe.db.exists("IMM Compliance Rule", rule),
                        "rule đã resolve PHẢI tồn tại trong IMM Compliance Rule")

    def test_compliant_na_do_not_create_finding(self):
        """Compliant / N/A KHÔNG sinh Finding; payload hỗn hợp
        [Compliant, N/A, Major NC] ⇒ findings_created==1; chỉ 1 doc persist."""
        name = self._mk_audit_with_items("TEST-AUDSD-MIX", item_count=3,
                                         status="In Progress")
        res = svc.complete_audit_checklist(name, [
            {"idx": 1, "finding_status": "Compliant"},
            {"idx": 2, "finding_status": "N/A"},
            {"idx": 3, "finding_status": "Major NC", "notes": "NC"},
        ])
        self.assertEqual(res["findings_created"], 1)
        self.assertEqual(len(self._audit_findings(name)), 1,
                         "chỉ dòng NC sinh Finding")

    def test_fallback_rule_idempotent(self):
        """Get-or-create fallback IMM-16-AUDIT-NC idempotent: complete trên 2
        audit khác nhau (mỗi cái 1 NC) ⇒ CHỈ 1 doc rule fallback (không nhân
        bản, không DuplicateEntryError trên create thứ 2)."""
        a = self._mk_audit_with_items("TEST-AUDSD-IDEMPA", item_count=1,
                                      status="In Progress")
        b = self._mk_audit_with_items("TEST-AUDSD-IDEMPB", item_count=1,
                                      status="In Progress")
        r1 = svc.complete_audit_checklist(a, [
            {"idx": 1, "finding_status": "Major NC", "notes": "NC A"}])
        r2 = svc.complete_audit_checklist(b, [
            {"idx": 1, "finding_status": "Minor NC", "notes": "NC B"}])
        self.assertEqual(r1["findings_created"], 1)
        self.assertEqual(r2["findings_created"], 1)
        self.assertEqual(
            frappe.db.count("IMM Compliance Rule", {"name": "IMM-16-AUDIT-NC"}),
            1, "fallback rule KHÔNG được nhân bản qua nhiều lần complete")

    def test_clause_ref_resolves_specific_rule(self):
        """clause_ref khớp rule_code của IMM Compliance Rule đang có ⇒
        Finding.rule trỏ đúng rule đó (KHÔNG rơi về fallback)."""
        _ensure(
            "IMM Compliance Rule", "7.5.9",
            {
                "rule_code": "7.5.9",
                "rule_name": "ISO 13485 §7.5.9 — Truy xuất nguồn gốc",
                "source_module": "IMM-08",
                "category": "Document",
                "severity": "Medium",
                "evaluation_frequency": "Quarterly",
                "is_active": 1,
                "version": "1.0",
            },
        )
        name = self._mk_audit_with_items("TEST-AUDSD-CLAUSE", item_count=1,
                                         status="In Progress")
        svc.complete_audit_checklist(name, [
            {"idx": 1, "finding_status": "Major NC", "notes": "NC",
             "clause_ref": "7.5.9"},
        ])
        rows = self._audit_findings(name)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["rule"], "7.5.9",
                         "clause_ref khớp rule_code → dùng rule đó, không fallback")

    @classmethod
    def tearDownClass(cls):
        # start/complete/close commit nội bộ → dọn tường minh theo audit_code
        # (name đã bị autoname ghi đè). IMM Audit Trail append-only (ISO
        # 13485:7.5.9) → KHÔNG xoá được, để nguyên (asset='' + ref autoname,
        # KHÔNG match R-9 %test%).
        frappe.set_user("Administrator")
        audit_names = frappe.get_all(
            "IMM Internal Audit",
            filters={"audit_code": ("like", "TEST-AUDSD-%")}, pluck="name",
        )
        # CR-27d: auto-sinh Finding commit nội bộ → xoá TRƯỚC rule (FK reqd) &
        # audit. Gom Finding theo audit source_record + theo rule test-seed.
        finding_names: set[str] = set()
        if audit_names:
            finding_names.update(frappe.get_all(
                "IMM Compliance Finding",
                filters={"source_record_doctype": "IMM Internal Audit",
                         "source_record": ("in", audit_names)}, pluck="name"))
        for rn in ("IMM-16-AUDIT-NC", "7.5.9"):
            finding_names.update(frappe.get_all(
                "IMM Compliance Finding", filters={"rule": rn}, pluck="name"))
        for nm in finding_names:
            with suppress(Exception):
                frappe.delete_doc("IMM Compliance Finding", nm, force=True,
                                  ignore_permissions=True, ignore_on_trash=True)
        for rn in ("IMM-16-AUDIT-NC", "7.5.9"):
            _delete_if_exists("IMM Compliance Rule", rn)
        for nm in audit_names:
            with suppress(Exception):
                frappe.delete_doc("IMM Internal Audit", nm, force=True,
                                  ignore_permissions=True, ignore_on_trash=True)
        frappe.db.commit()
        super().tearDownClass()


# ── CR-27b guards: SSoT map ⇄ Select options + no-op-proof (drift-proof) ─────

class TestChecklistFindingStatusResultMap(unittest.TestCase):
    """Pin _FINDING_STATUS_TO_RESULT (SSoT verdict→result) đúng & drift-proof.
    KHÔNG cần fixture — thuần đọc doctype JSON + inspect map/meta (Small test)."""

    @staticmethod
    def _result_select_options() -> set[str]:
        """Parse imm_audit_checklist_item.json → options Select ``result``
        (nguồn SSoT ở tầng JSON — bắt drift nếu ai đổi Select)."""
        path = frappe.get_app_path(
            "assetcore", "assetcore", "doctype", "imm_audit_checklist_item",
            "imm_audit_checklist_item.json")
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        for f in doc["fields"]:
            if f["fieldname"] == "result":
                return {o for o in (f.get("options") or "").split("\n") if o}
        raise AssertionError("field 'result' không tồn tại trong child JSON")

    # INVARIANT: mọi value map ∈ options Select result → set/map đổi lệch = ĐỎ.
    def test_finding_status_map_values_subset_of_result_select(self):
        opts = self._result_select_options()
        self.assertEqual(opts, {"Conforming", "Non-Conforming", "Not Applicable"},
                         "Select result baseline drift")
        values = set(svc._FINDING_STATUS_TO_RESULT.values())
        self.assertTrue(
            values <= opts,
            f"map values {values} phải ⊆ options Select result {opts}")
        # keys = đúng 4 verdict FE/mobile (Compliant/Minor NC/Major NC/N/A).
        self.assertEqual(set(svc._FINDING_STATUS_TO_RESULT),
                         {"Compliant", "Minor NC", "Major NC", "N/A"})

    # Guard no-op-proof: child KHÔNG có finding_status/clause_ref → 2 assign cũ
    # (hasattr-gán) là NO-OP CÂM. Nếu ai THÊM field → test đỏ, buộc xem lại map.
    def test_audit_checklist_item_has_no_finding_status_clause_ref_field(self):
        meta = frappe.get_meta("IMM Audit Checklist Item")
        fieldnames = {f.fieldname for f in meta.fields}
        cols = set(meta.get_valid_columns())
        for ghost in ("finding_status", "clause_ref"):
            self.assertNotIn(
                ghost, fieldnames,
                f"child có field {ghost!r} → hasattr-assign cũ KHÔNG còn no-op, "
                f"phải reconcile map/logic complete_audit_checklist")
            self.assertNotIn(ghost, cols)
        # result (đích của map) PHẢI tồn tại → verdict có chỗ persist.
        self.assertIn("result", fieldnames)


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


# ── TC-16-04b: CAPA server-driven CTA — allowed_transitions/can_advance ─────
# ADR-IMM-16-01 / GATE-8 / LL-FE-51 (mirror get_finding/get_audit). get_capa
# emit allowed_transitions dẫn xuất TỪ CÙNG _CAPA_TRANSITIONS mà advance_capa_state
# enforce (1 SoT — chống desync nút↔transition). = [] khi caller KHÔNG có
# compliance.write. Bất biến parity có test khoá.

class TestCapaServerDrivenLifecycle(TestImm16Base):
    """CAPA vòng đời server-driven: allowed_transitions/can_advance derive
    server-side từ _CAPA_TRANSITIONS (SoT DUY NHẤT), parity với guard
    advance_capa_state, gate theo capability compliance.write."""

    _MARKER = "CAPA server-driven CTA test"

    def _mk_capa(self, name: str, state: str, asset: str = "N/A") -> str:
        """Dựng 1 IMM CAPA Record ở ``state`` (autoname → trả tên thật).
        Cleanup theo ``description`` marker (name bị autoname ghi đè)."""
        return _ensure(
            "IMM CAPA Record", name,
            {
                "asset": asset,
                "source_type": "Non-Conformance",
                "severity": "Major",
                "description": self._MARKER,
                "opened_date": nowdate(),
                "due_date": add_days(nowdate(), 30),
                "workflow_state": state,
                "status": "Open" if state == "Open" else "In Progress",
                # responsible mandatory — advance_capa_state gọi doc.save() re-validate.
                "responsible": "Administrator",
                "root_cause": "test",
                "corrective_action": "test",
                "preventive_action": "test",
            },
        )

    @staticmethod
    def _has_write(cap, doc=None):
        return cap == svc._CAP_COMPLIANCE_WRITE

    # [BE][invariant] mỗi state → allowed_transitions == sorted(_CAPA_TRANSITIONS[state]).
    def test_get_capa_allowed_transitions_by_state(self):
        with patch.object(svc.rbac, "can", side_effect=self._has_write):
            for state, targets in svc._CAPA_TRANSITIONS.items():
                name = self._mk_capa(
                    f"TEST-CAPA-AT-{state.replace(' ', '')}", state)
                data = svc.get_capa(name)
                self.assertEqual(data["allowed_transitions"], sorted(targets),
                                 f"state={state}")
                self.assertTrue(data["can_advance"], f"state={state}")
            # Verification → ['Closed','Re-opened'] (đóng/mở lại qua gate xác minh)
            vname = self._mk_capa("TEST-CAPA-AT-VER", "Verification")
            self.assertEqual(svc.get_capa(vname)["allowed_transitions"],
                             ["Closed", "Re-opened"])
            # Terminal 'Closed' không phải key → [] (safe .get, KHÔNG KeyError)
            cname = self._mk_capa("TEST-CAPA-AT-CLO", "Closed")
            data = svc.get_capa(cname)
            self.assertEqual(data["allowed_transitions"], [])
            self.assertTrue(data["can_advance"])  # cờ do capability, không do state

    # [BE] viewer read-only (KHÔNG compliance.write) → không lộ CTA.
    def test_get_capa_readonly_viewer_hides_cta(self):
        name = self._mk_capa("TEST-CAPA-RO", "Investigating")
        with patch.object(svc.rbac, "can", return_value=False):
            data = svc.get_capa(name)
        self.assertEqual(data["allowed_transitions"], [])
        self.assertFalse(data["can_advance"])

    # [BE][axis-A regression] Super Admin (Administrator có compliance.write) →
    # allowed_transitions KHÔNG rỗng + can_advance True; advance hợp lệ thành công
    # (KHÔNG FORBIDDEN); jump-skip vẫn INVALID_STATE.
    def test_get_capa_super_admin_can_advance_axis_a(self):
        if not self.test_asset:
            self.skipTest("No AC Asset found in DB — skipping axis-A advance test")
        name = self._mk_capa("TEST-CAPA-AXA", "Open", asset=self.test_asset)
        # Administrator (setUpClass) có capability compliance.write — KHÔNG patch.
        data = svc.get_capa(name)
        self.assertTrue(data["can_advance"])
        self.assertEqual(data["allowed_transitions"], ["Investigating"])
        # transition hợp lệ (Open→Investigating, không state-validation) → thành công
        res = svc.advance_capa_state(name, "Investigating")
        self.assertEqual(res["workflow_state"], "Investigating")
        # transition sai (jump-skip Open→Verification) vẫn INVALID_STATE
        name2 = self._mk_capa("TEST-CAPA-AXA2", "Open", asset=self.test_asset)
        with self.assertRaises(ServiceError) as ctx:
            svc.advance_capa_state(name2, "Verification")
        self.assertEqual(ctx.exception.code, "INVALID_STATE")

    # [BE][anti-desync] test khoá: emit của get_capa == tập target advance chấp nhận.
    def test_allowed_transitions_parity_with_advance_guard(self):
        with patch.object(svc.rbac, "can", side_effect=self._has_write):
            for state, guard_targets in svc._CAPA_TRANSITIONS.items():
                name = self._mk_capa(
                    f"TEST-CAPA-PAR-{state.replace(' ', '')}", state)
                emitted = set(svc.get_capa(name)["allowed_transitions"])
                self.assertEqual(
                    emitted, set(guard_targets),
                    f"desync at state={state}: emit={emitted} guard={guard_targets}")

    @classmethod
    def tearDownClass(cls):
        # advance_capa_state commit nội bộ → dọn tường minh theo description marker
        # (name đã bị autoname ghi đè, _delete_if_exists không match).
        frappe.set_user("Administrator")
        for nm in frappe.get_all(
            "IMM CAPA Record",
            filters={"description": cls._MARKER}, pluck="name",
        ):
            with suppress(Exception):
                frappe.delete_doc("IMM CAPA Record", nm, force=True,
                                  ignore_permissions=True, ignore_on_trash=True)
        frappe.db.commit()
        super().tearDownClass()


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

    # ── BUG-16: evidence loss on Effective→Close (NĐ98/ISO 13485 §8.5.2) ──
    def _new_verification_capa(self, fixture_name: str) -> str:
        """Mirror fixture (dòng 286-302): CAPA ở Verification/In Progress."""
        return _ensure(
            "IMM CAPA Record", fixture_name,
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

    def test_effectiveness_check_effective_persists_evidence(self):
        """RED-before-fix: closing a CAPA as Effective must KEEP the
        effectiveness evidence (NĐ98/ISO 13485 §8.5.2 audit trail)."""
        if not self.test_asset:
            self.skipTest("No AC Asset found in DB — skipping effectiveness test")
        capa_name = self._new_verification_capa("TEST-CAPA-EFF-CLOSE-01")
        result = svc.perform_effectiveness_check(
            capa_name, result="Effective",
            effectiveness_evidence="/files/eff-close-01.pdf",
        )
        self.assertEqual(result["new_state"], "Closed")
        # Evidence must survive into the DB on the Close branch (post-commit).
        self.assertEqual(
            frappe.db.get_value("IMM CAPA Record", capa_name,
                                "imm_effectiveness_evidence"),
            "/files/eff-close-01.pdf",
        )
        ec, status = frappe.db.get_value(
            "IMM CAPA Record", capa_name,
            ["effectiveness_check", "status"])
        self.assertEqual(ec, "Effective")
        self.assertEqual(status, "Closed")

    def test_effectiveness_check_effective_empty_evidence_still_closes(self):
        """Guard (GREEN both sides): empty evidence on Effective must NOT
        overwrite the field with '', and CAPA must still Close — parity with
        the Re-open branch's ``if effectiveness_evidence:`` guard."""
        if not self.test_asset:
            self.skipTest("No AC Asset found in DB — skipping effectiveness test")
        capa_name = self._new_verification_capa("TEST-CAPA-EFF-CLOSE-EMPTY")
        result = svc.perform_effectiveness_check(
            capa_name, result="Effective", effectiveness_evidence="",
        )
        self.assertEqual(result["new_state"], "Closed")
        # Empty evidence must not clobber the field to ''.
        self.assertNotEqual(
            frappe.db.get_value("IMM CAPA Record", capa_name,
                                "imm_effectiveness_evidence"),
            "",
        )

    def test_effectiveness_check_not_effective_persists_evidence(self):
        """Lock existing (correct) Re-open behaviour: evidence persists and the
        re-open counter increments — guard against regression."""
        if not self.test_asset:
            self.skipTest("No AC Asset found in DB — skipping effectiveness test")
        capa_name = self._new_verification_capa("TEST-CAPA-EFF-REOPEN-01")
        result = svc.perform_effectiveness_check(
            capa_name, result="Not Effective",
            effectiveness_evidence="/files/eff-reopen.pdf",
        )
        self.assertEqual(result["new_state"], "Re-opened")
        self.assertGreaterEqual(result["imm_reopen_count"], 1)
        self.assertEqual(
            frappe.db.get_value("IMM CAPA Record", capa_name,
                                "imm_effectiveness_evidence"),
            "/files/eff-reopen.pdf",
        )


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


# ── TC-16-GATE: duplicate-collapse parity + invariant-under-cron ─────────────
# Pre-flight banner (PMWorkOrderCreateView) reads gate_wo_submit SoT via the
# canonical whitelist endpoint. These guard: (1) collapse left exactly ONE
# whitelisted gate fn delegating to svc.check_asset_compliance_status, and
# (2) the gate stays blocked + reasons[].status renders the REAL status after
# the daily cron flips Open→'Overdue' (BR-16-09 invariant, round 12).

class TestGateDuplicateCollapse(TestImm16Base):
    """TC-16-GATE-01: after collapse there is exactly ONE whitelisted gate fn."""

    _ASSET = "TEST-GATE-ASSET-01"
    _CAPA = "TEST-CAPA-GATE-CRIT-01"

    def setUp(self):
        super().setUp()
        _ensure("AC Asset", self._ASSET, {"asset_name": "Gate Test Asset"})
        # IMM CAPA Record uses naming_series autoname → captured name, not
        # the requested fixture name. Track it for assertion + teardown.
        self._capa_name = _ensure(
            "IMM CAPA Record", self._CAPA,
            {
                "asset": self._ASSET,
                "imm_risk_level": "Critical",
                "severity": "Critical",
                "status": "Open",
                "due_date": add_days(nowdate(), -10),  # past-due
                "description": "Gate test critical CAPA",
            },
        )
        frappe.db.commit()

    def tearDown(self):
        _delete_if_exists("IMM CAPA Record", self._capa_name)
        _delete_if_exists("AC Asset", self._ASSET)
        frappe.db.commit()
        super().tearDown()

    def test_canonical_endpoint_blocks_critical_open_past_due(self):
        # Call the CANONICAL whitelist endpoint (api layer), not the service,
        # to prove the FE-facing path still enforces BR-16-09 after collapse.
        from assetcore.api import imm16 as api
        resp = api.check_asset_compliance_status(self._ASSET)
        self.assertTrue(resp["success"], resp)
        result = resp["data"]
        self.assertTrue(result["blocked"])
        self.assertGreaterEqual(len(result["reasons"]), 1)
        # reasons[0].status surfaces the REAL CAPA status (render-ready for FE).
        self.assertEqual(result["reasons"][0]["status"], "Open")
        self.assertEqual(result["reasons"][0]["ref"], self._capa_name)

    def test_only_one_whitelisted_gate_endpoint_remains(self):
        # grep-equivalent: parse api/imm16.py AST, count whitelisted module-level
        # functions whose body delegates to svc.check_asset_compliance_status.
        import ast
        import inspect

        from assetcore.api import imm16 as api
        src = inspect.getsource(api)
        tree = ast.parse(src)
        delegating = []
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            is_whitelisted = any(
                (isinstance(d, ast.Call) and getattr(d.func, "attr", "")
                 == "whitelist")
                or getattr(d, "attr", "") == "whitelist"
                for d in node.decorator_list
            )
            if not is_whitelisted:
                continue
            # Match an ACTUAL call expression `svc.check_asset_compliance_status`
            # in the executable body — NOT docstrings/comments (the deprecated
            # alias mentions the canonical fn in its docstring but does not
            # delegate to the service directly).
            delegates = any(
                isinstance(c, ast.Attribute)
                and c.attr == "check_asset_compliance_status"
                and isinstance(c.value, ast.Name) and c.value.id == "svc"
                for c in ast.walk(node)
            )
            if delegates:
                delegating.append(node.name)
        self.assertEqual(
            len(delegating), 1,
            f"Expected exactly 1 whitelisted gate fn delegating to "
            f"svc.check_asset_compliance_status, found: {delegating}",
        )
        # Canonical name = the path FE client imm16.ts:513 targets.
        self.assertEqual(delegating[0], "check_asset_compliance_status")


class TestGateInvariantUnderCron(TestImm16Base):
    """TC-16-GATE-02: blocked invariant after cron flips Open→'Overdue'."""

    _ASSET = "TEST-GATE-ASSET-02"
    _CAPA = "TEST-CAPA-GATE-CRIT-02"

    def setUp(self):
        super().setUp()
        _ensure("AC Asset", self._ASSET, {"asset_name": "Gate Cron Asset"})
        self._capa_name = _ensure(
            "IMM CAPA Record", self._CAPA,
            {
                "asset": self._ASSET,
                "imm_risk_level": "Critical",
                "severity": "Critical",
                "status": "Open",
                "due_date": add_days(nowdate(), -5),  # past-due → cron flippable
                "description": "Gate cron invariant CAPA",
            },
        )
        frappe.db.commit()

    def tearDown(self):
        _delete_if_exists("IMM CAPA Record", self._capa_name)
        _delete_if_exists("AC Asset", self._ASSET)
        frappe.db.commit()
        super().tearDown()

    def test_blocked_invariant_and_status_renders_overdue_after_cron(self):
        from assetcore.services.imm00 import check_capa_overdue

        # Before cron: Critical CAPA Open past-due → blocked, status 'Open'.
        before = svc.check_asset_compliance_status(self._ASSET)
        self.assertTrue(before["blocked"])
        self.assertEqual(before["reasons"][0]["status"], "Open")

        # Run daily cron: flips Open→'Overdue'.
        check_capa_overdue()
        frappe.db.commit()

        # After cron: gate STILL blocked (invariant) + reasons[].status now
        # surfaces the REAL flipped status 'Overdue' (render-ready, no leak guard
        # is FE responsibility via translateStatus).
        after = svc.check_asset_compliance_status(self._ASSET)
        self.assertTrue(after["blocked"])
        self.assertEqual(after["reasons"][0]["status"], "Overdue")


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
    # Distinct quarters per status so fixtures never collide on find_by_quarter.
    _Q_BY_STATUS = {
        "Draft": "Q1-2099",
        "Held": "Q2-2099",
        "Minutes Approved": "Q3-2099",
        "Closed": "Q4-2099",
    }

    def _mr(self) -> str:
        return self._mr_in("Draft")

    def _mr_in(self, status: str) -> str:
        """Fixture MR forced into ``status`` (status + workflow_state) for CTA tests."""
        quarter = self._Q_BY_STATUS.get(status, "Q1-2098")
        return _ensure(
            "IMM Management Review",
            f"TEST-MR-{status.replace(' ', '')}-CTA",
            {
                "quarter": quarter,
                "review_date": nowdate(),
                "chair": "Administrator",
                "status": status,
                "workflow_state": status,
            },
        )

    # [BE][TDD] AA-16-MR-1 — allowed_transitions dẫn xuất từ _MR_TRANSITIONS per status.
    def test_get_mr_emits_allowed_transitions_per_status(self):
        for status in ("Draft", "Held", "Minutes Approved", "Closed"):
            expected = sorted(svc._MR_TRANSITIONS.get(status, set()))
            mr = self._mr_in(status)
            data = svc.get_management_review(mr)
            self.assertEqual(data["allowed_transitions"], expected,
                             f"status={status}")
        # Kiểm chứng cụ thể (đọc từ SoT, không hardcode kỳ vọng rời).
        self.assertEqual(
            svc.get_management_review(self._mr_in("Draft"))["allowed_transitions"],
            ["Held"])
        self.assertEqual(
            svc.get_management_review(self._mr_in("Held"))["allowed_transitions"],
            ["Minutes Approved"])
        self.assertEqual(
            svc.get_management_review(
                self._mr_in("Minutes Approved"))["allowed_transitions"],
            ["Closed"])
        self.assertEqual(
            svc.get_management_review(self._mr_in("Closed"))["allowed_transitions"],
            [])
        # status lạ → [] (safe-default .get, KHÔNG KeyError)
        weird = self._mr_in("Draft")
        frappe.db.set_value("IMM Management Review", weird, "status",
                            "Zzz-Unknown", update_modified=False)
        self.assertEqual(
            svc.get_management_review(weird)["allowed_transitions"], [])

    # [BE][TDD] AA-16-MR-2 — cờ capability derive server-side (== compliance.submit).
    def test_get_mr_emits_capability_flags(self):
        mr = self._mr()

        def with_submit(cap, doc=None):
            return cap == "compliance.submit"

        with patch.object(svc.rbac, "can", side_effect=with_submit):
            data = svc.get_management_review(mr)
            self.assertTrue(data["can_advance"])
            self.assertTrue(data["can_close"])

        def no_submit(cap, doc=None):
            return {"compliance.write": True, "compliance.submit": False}.get(
                cap, False)

        with patch.object(svc.rbac, "can", side_effect=no_submit):
            data = svc.get_management_review(mr)
            self.assertFalse(data["can_advance"])
            self.assertFalse(data["can_close"])
            # Cả hai cờ == rbac.can('compliance.submit').
            self.assertEqual(data["can_advance"], data["can_close"])

    # [BE][TDD][INVARIANT] AA-16-MR-3 — hint ⊆ guard: mọi target emit được
    # advance_mr_state (hoặc finalize cho 'Closed') chấp nhận; bịa ngoài SoT → INVALID_STATE.
    def test_mr_allowed_transitions_subset_of_guard(self):
        for status, guard_targets in svc._MR_TRANSITIONS.items():
            emitted = set(
                svc.get_management_review(self._mr_in(status))["allowed_transitions"])
            self.assertEqual(emitted, set(guard_targets),
                             f"desync at status={status}")
            for target in emitted:
                fresh = self._mr_in(status)
                if target == "Closed":
                    # 'Closed' đi qua finalize; advance từ chối VALIDATION (không INVALID).
                    res = svc.finalize_management_review(
                        fresh, minutes_doc="/files/m.pdf",
                        output_actions=[{"action": "Cải tiến",
                                         "responsible": "Administrator"}])
                    self.assertEqual(res["status"], "Closed")
                else:
                    res = svc.advance_mr_state(fresh, target)
                    self.assertEqual(res["status"], target)
        # target bịa ngoài _MR_TRANSITIONS → INVALID_STATE (chống desync hint↔guard).
        with self.assertRaises(ServiceError) as ctx:
            svc.advance_mr_state(self._mr_in("Draft"), "Bogus-State")
        self.assertEqual(ctx.exception.code, "INVALID_STATE")

    # [BE][TDD][axis-A crux] AA-16-MR-4 — user CHỈ mang role 'AssetCore Super Admin'
    # (QTV) → rbac.can('compliance.submit') True → advance Draft→Held→Minutes Approved
    # OK + finalize đóng MR OK (chứng minh "QTV duyệt/đóng được dù chỉ có quyền AssetCore").
    def test_super_admin_can_advance_and_close_mr(self):
        uid = str(int(time.time() * 1000) % 1_000_000)
        email = _ensure_user(
            f"_test_mr_sadm_{uid}@example.com", ["AssetCore Super Admin"])
        mr = self._mr()  # Draft (tạo dưới Administrator)
        try:
            frappe.set_user(email)
            self.assertTrue(
                svc.rbac.can("compliance.submit"),
                "AssetCore Super Admin thiếu compliance.submit → vá SoT DocPerm "
                "'IMM CAPA Record' submit=1 (chống RBAC dead-gate, KHÔNG hardcode role)")
            self.assertEqual(svc.advance_mr_state(mr, "Held")["status"], "Held")
            self.assertEqual(
                svc.advance_mr_state(mr, "Minutes Approved")["status"],
                "Minutes Approved")
            self.assertEqual(
                svc.finalize_management_review(
                    mr, minutes_doc="/files/mr.pdf",
                    output_actions=[{"action": "Cải tiến PM",
                                     "responsible": "Administrator"}])["status"],
                "Closed")
        finally:
            frappe.set_user("Administrator")
            _delete_if_exists("User", email)

    # [BE][TDD] AA-16-MR-5 — guard cứng còn nguyên: user KHÔNG capability gọi
    # advance/finalize → FORBIDDEN (dù FE đã ẩn nút).
    def test_non_approver_advance_forbidden(self):
        mr = self._mr()
        with patch.object(svc.rbac, "can", return_value=False):
            with self.assertRaises(ServiceError) as ctx:
                svc.advance_mr_state(mr, "Held")
            self.assertEqual(ctx.exception.code, ErrorCode.FORBIDDEN)
            with self.assertRaises(ServiceError) as ctx2:
                svc.finalize_management_review(
                    mr, minutes_doc="/files/m.pdf",
                    output_actions=[{"action": "A", "responsible": "Administrator"}])
            self.assertEqual(ctx2.exception.code, ErrorCode.FORBIDDEN)

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
        # Cleanup theo thứ tự link: CAPA → RCA → Incident.
        # Phải xoá MỌI CAPA trỏ về incident (linked_incident), không chỉ CAPA
        # mà Incident.linked_capa trỏ tới — nếu back-link một chiều, CAPA mồ côi
        # vẫn giữ FK linked_incident và gây LinkExistsError khi xoá Incident.
        capa_names = set(frappe.get_all(
            "IMM CAPA Record",
            filters={"linked_incident": self.incident_name},
            pluck="name",
        ))
        back_link = frappe.db.get_value(
            "Incident Report", self.incident_name, "linked_capa"
        )
        if back_link:
            capa_names.add(back_link)
        for capa in capa_names:
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


# ── BR-16-11: compute_compliance_rate SoT (scorecard + heatmap) ─────────────
#
# Root cause: score_pct phồng vì finding chưa phân định (Open/Under Review) bị
# tính NHƯ tuân thủ (compliant = total - nc). SoT mới loại pending khỏi mẫu số.

class _F:
    """Lightweight finding-like stub: SoT chỉ đọc ``.status``."""

    def __init__(self, status: str):
        self.status = status


class TestComputeComplianceRateSoT(unittest.TestCase):
    """SoT BR-16-11 — phân loại finding thành 3 nhóm cho compliance-rate."""

    def test_tdd1_confirmed_nc_and_resolved(self):
        """[BE TDD-1] {1 Confirmed NC, 1 Resolved} → adjudicated=2, nc=1,
        compliant=1, score_pct=50.0, pending=0."""
        findings = [_F(FindingStatus.CONFIRMED_NC), _F(FindingStatus.RESOLVED)]
        r = svc.compute_compliance_rate(findings)
        self.assertEqual(r["total_adjudicated"], 2)
        self.assertEqual(r["non_compliant"], 1)
        self.assertEqual(r["compliant"], 1)
        self.assertEqual(r["pending"], 0)
        self.assertEqual(r["score_pct"], 50.0)

    def test_tdd3_only_pending_yields_100(self):
        """[BE TDD-3] Edge: chỉ {2 Open, 1 Under Review} → adjudicated=0 →
        score_pct=100.0 (semantics 'không có NC xác nhận'), pending=3."""
        findings = [_F(FindingStatus.OPEN), _F(FindingStatus.OPEN),
                    _F(FindingStatus.UNDER_REVIEW)]
        r = svc.compute_compliance_rate(findings)
        self.assertEqual(r["total_adjudicated"], 0)
        self.assertEqual(r["pending"], 3)
        self.assertEqual(r["non_compliant"], 0)
        self.assertEqual(r["compliant"], 0)
        self.assertEqual(r["score_pct"], 100.0)

    def test_tdd4_false_positive_excluded_from_both(self):
        """[BE TDD-4] FP đã loại từ query filter (status != FP). Nếu lọt vào
        SoT vẫn KHÔNG được làm phồng mẫu số. {1 Confirmed NC} (FP đã lọc) →
        adjudicated=1, score_pct=0.0."""
        # Mô phỏng list sau filter `status != False Positive`.
        findings = [_F(FindingStatus.CONFIRMED_NC)]
        r = svc.compute_compliance_rate(findings)
        self.assertEqual(r["total_adjudicated"], 1)
        self.assertEqual(r["score_pct"], 0.0)
        # Defensive: dù FP lọt vào list cũng không vào mẫu số.
        r2 = svc.compute_compliance_rate(
            [_F(FindingStatus.CONFIRMED_NC), _F(FindingStatus.FALSE_POSITIVE)])
        self.assertEqual(r2["total_adjudicated"], 1)
        self.assertEqual(r2["score_pct"], 0.0)


class TestScorecardRegressionBR1611(TestImm16Base):
    """[BE TDD-2 + TDD-5] generate_scorecard + heatmap dùng CÙNG SoT."""

    PERIOD = "2027-03"

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._day = 0

    def _make_finding(self, status: str, eval_date: str | None = None,
                      detected_date: str | None = None) -> str:
        """Tạo finding committed, gán status + 2 cột date ĐỘC LẬP.

        ``create_finding`` dedup theo (rule, source_record, eval_date) → mặc định
        dùng ngày khác nhau trong kỳ T3 để tránh idempotent-collapse.

        BR-16-12: ``eval_date`` và ``detected_date`` CÓ THỂ KHÁC kỳ (mô phỏng lag
        adjudication: phát hiện T2, đánh giá T3). Scorecard + Heatmap PHẢI neo kỳ
        theo CÙNG field ``evaluation_date`` → finding chỉ thuộc kỳ của
        ``evaluation_date`` ở CẢ 2 view.
        """
        self._day += 1
        if eval_date is None:
            eval_date = f"2027-03-{self._day:02d}"
        if detected_date is None:
            detected_date = f"{eval_date} 09:00:00"
        res = svc.create_finding(
            rule_ref=self.rule, asset_ref="", work_order_ref="",
            severity="High", description=f"BR1611 regression {status}",
            evaluation_date=eval_date,
        )
        name = res["name"]
        frappe.db.set_value(
            "IMM Compliance Finding", name,
            {"status": status,
             "evaluation_date": eval_date,
             "detected_date": detected_date,
             "responsible_dept": None},
            update_modified=False,
        )
        frappe.db.commit()
        return name

    def _purge_period(self):
        # BR-16-12: dataset trải 2 kỳ T2(2027-02)+T3(2027-03) → purge cả 2 +
        # finding nào có detected_date lệch kỳ.
        for nm in frappe.get_all(
            "IMM Compliance Scorecard",
            filters={"period_year": 2027, "period_month": ("in", [2, 3])},
            pluck="name",
        ):
            _delete_if_exists("IMM Compliance Scorecard", nm)
        for nm in frappe.get_all(
            "IMM Compliance Finding",
            filters={"rule": self.rule,
                     "evaluation_date": ("between",
                                         ["2027-02-01", "2027-03-31"])},
            pluck="name",
        ):
            _delete_if_exists("IMM Compliance Finding", nm)
        # Defensive: finding có detected_date trong T2 nhưng eval_date ngoài range.
        for nm in frappe.get_all(
            "IMM Compliance Finding",
            filters={"rule": self.rule,
                     "detected_date": ("between",
                                       ["2027-02-01 00:00:00",
                                        "2027-03-31 23:59:59"])},
            pluck="name",
        ):
            _delete_if_exists("IMM Compliance Finding", nm)
        frappe.db.commit()

    def setUp(self):
        super().setUp()
        self._day = 0
        self._purge_period()
        self.addCleanup(self._purge_period)

    def test_tdd2_scorecard_excludes_pending_from_denominator(self):
        """[BE TDD-2] dataset {1 Confirmed NC, 1 Open, 1 Resolved}:
        TRƯỚC fix score=66.67 (3 total, 1 nc, Open tính tuân thủ);
        SAU fix score=50.0 (adjudicated=2), pending_count=1, nc=1, compliant=1.
        Assert == 50.0 (chống phồng)."""
        self._make_finding(FindingStatus.CONFIRMED_NC)
        self._make_finding(FindingStatus.OPEN)
        self._make_finding(FindingStatus.RESOLVED)

        result = svc.generate_scorecard(module_ref="", period=self.PERIOD)
        self.assertEqual(result["score_pct"], 50.0)
        self.assertNotEqual(result["score_pct"], 66.67)
        self.assertEqual(result["pending_count"], 1)
        self.assertEqual(result["non_compliant"], 1)

        sc = frappe.db.get_value(
            "IMM Compliance Scorecard", result["scorecard"],
            ["score_pct", "non_compliant_count", "compliant_count",
             "total_rules_evaluated"], as_dict=True,
        )
        self.assertEqual(sc.score_pct, 50.0)
        self.assertEqual(sc.non_compliant_count, 1)   # Confirmed NC only
        self.assertEqual(sc.compliant_count, 1)        # adjudicated-compliant
        # total_rules_evaluated vẫn báo tổng (gồm pending) để UX không mất dấu.
        self.assertEqual(sc.total_rules_evaluated, 3)

    def test_tdd5_scorecard_heatmap_parity(self):
        """[BE TDD-5] cùng dataset (cả 2 date trong kỳ) → score_pct scorecard
        == score cell heatmap (1 module / 1 dept). Parity cơ bản (không lệch kỳ)
        — divergence kỳ được phủ bởi test_tdd5b dưới."""
        self._make_finding(FindingStatus.CONFIRMED_NC)
        self._make_finding(FindingStatus.OPEN)
        self._make_finding(FindingStatus.RESOLVED)

        sc_result = svc.generate_scorecard(module_ref="", period=self.PERIOD)
        heat = svc.get_compliance_heatmap(period_year=2027, period_month=3)
        # Tất cả finding cùng rule (IMM-08) + cùng dept (None→__none__) → 1 cell.
        cells = [c for c in heat["matrix"]
                 if c["findings_count"] == 3]
        self.assertTrue(cells, "Expected a single cell with all 3 findings")
        self.assertEqual(cells[0]["score"], sc_result["score_pct"])
        self.assertEqual(cells[0]["score"], 50.0)

    def _imm08_cell(self, heat: dict):
        """Lấy cell heatmap của module IMM-08 (source_module của test rule)."""
        cells = [c for c in heat["matrix"] if c["module"] == "IMM-08"]
        return cells[0] if cells else None

    def test_tdd5b_period_anchor_parity_detected_ne_evaluation(self):
        """[BE TDD-5b · BR-16-12] PARITY THẬT — detected_date ≠ evaluation_date.

        Dataset: 1 Confirmed-NC có detected_date='2027-02-25' (kỳ T2) NHƯNG
        evaluation_date='2027-03-05' (kỳ T3) — mô phỏng lag adjudication.

        SAU fix (cả 2 view neo kỳ theo evaluation_date):
          - Kỳ T2 (2027-02): finding KHÔNG thuộc kỳ ở CẢ scorecard lẫn heatmap →
            score == 100.0 cả 2 (không có NC khác trong T2).
          - Kỳ T3 (2027-03): finding thuộc kỳ ở CẢ 2 → score == 0.0 cả 2
            (1 Confirmed-NC, adjudicated=1, compliant=0).
          - score scorecard kỳ K == cell.score heatmap kỳ K cho module IMM-08.

        TRƯỚC fix (heatmap lọc detected_date): heatmap T2 ĐẾM finding này
        (score giảm) trong khi scorecard T2 KHÔNG → assert T2 parity FAIL đúng
        symptom (RED-experiment: revert anchor heatmap về detected_date).
        """
        # Finding lag: phát hiện T2, đánh giá/xác nhận NC ở T3.
        self._make_finding(
            FindingStatus.CONFIRMED_NC,
            eval_date="2027-03-05",
            detected_date="2027-02-25 14:00:00",
        )

        # --- Kỳ T2 (2027-02): finding KHÔNG thuộc kỳ theo evaluation_date ---
        sc_t2 = svc.generate_scorecard(module_ref="", period="2027-02")
        heat_t2 = svc.get_compliance_heatmap(period_year=2027, period_month=2)
        cell_t2 = self._imm08_cell(heat_t2)
        # Scorecard T2: không có finding adjudicated trong kỳ → 100.0.
        self.assertEqual(sc_t2["score_pct"], 100.0)
        self.assertEqual(sc_t2["non_compliant"], 0)
        # Heatmap T2: KHÔNG có cell IMM-08 (finding không neo vào T2) — parity:
        # cả 2 view "không thấy" finding NC trong T2 ⇒ T2 sạch.
        if cell_t2 is not None:
            self.fail(
                "BR-16-12 divergence: heatmap T2 vẫn đếm finding có "
                "detected_date T2 nhưng evaluation_date T3 — phải neo kỳ theo "
                f"evaluation_date. cell={cell_t2}"
            )

        # generate_scorecard persist 1 Scorecard mỗi lần gọi; autoname
        # `format:SCR-.YYYY.-.MM.-.#####` resolve theo NGÀY HIỆN TẠI (không theo
        # period) → 2 lần gọi cùng phiên dùng chung series, dễ collide trong
        # test DB. Assertion chỉ cần return dict (score_pct) → purge scorecard
        # T2 trước khi gọi T3. (_purge_period cleanup mọi scorecard T2/T3.)
        _delete_if_exists("IMM Compliance Scorecard", sc_t2["scorecard"])
        frappe.db.commit()

        # --- Kỳ T3 (2027-03): finding thuộc kỳ theo evaluation_date ---
        sc_t3 = svc.generate_scorecard(module_ref="", period="2027-03")
        heat_t3 = svc.get_compliance_heatmap(period_year=2027, period_month=3)
        cell_t3 = self._imm08_cell(heat_t3)
        self.assertEqual(sc_t3["score_pct"], 0.0)        # 1 Confirmed-NC
        self.assertEqual(sc_t3["non_compliant"], 1)
        self.assertIsNotNone(cell_t3, "Heatmap T3 phải có cell IMM-08")
        self.assertEqual(cell_t3["findings_count"], 1)
        # PARITY THẬT: score scorecard T3 == cell.score heatmap T3.
        self.assertEqual(cell_t3["score"], sc_t3["score_pct"])
        self.assertEqual(cell_t3["score"], 0.0)

    def test_tdd4_period_boundary_inclusive_start_exclusive_next(self):
        """[BE TDD-4 · BR-16-12] Boundary của period-anchor (CÙNG _period_bounds
        cho scorecard + heatmap):

        - evaluation_date == NGÀY ĐẦU kỳ ('2027-03-01') → THUỘC kỳ T3.
        - evaluation_date == NGÀY ĐẦU kỳ KẾ ('2027-04-01') → KHÔNG thuộc kỳ T3
          (half-open ``[start, end)`` như doc 02:526; tránh off-by-one do Frappe
          ``between`` inclusive cả 2 đầu nếu dùng first-of-next-month làm upper).

        Cả Scorecard lẫn Heatmap PHẢI cho cùng kết luận (cùng _period_bounds).
        Dataset: 1 Confirmed-NC ở '2027-03-01' (in) + 1 Confirmed-NC ở
        '2027-04-01' (out). Kỳ T3: chỉ thấy finding ngày 01/03 → nc=1.
        """
        # In-period: đúng ngày đầu kỳ T3.
        self._make_finding(FindingStatus.CONFIRMED_NC, eval_date="2027-03-01")
        # Out-of-period: đúng ngày đầu kỳ kế (T4) — KHÔNG được lọt vào T3.
        self._make_finding(FindingStatus.CONFIRMED_NC, eval_date="2027-04-01")

        sc_t3 = svc.generate_scorecard(module_ref="", period="2027-03")
        heat_t3 = svc.get_compliance_heatmap(period_year=2027, period_month=3)
        cell_t3 = self._imm08_cell(heat_t3)

        # Scorecard T3: chỉ đếm finding 01/03, KHÔNG đếm 01/04.
        self.assertEqual(sc_t3["total_findings"], 1,
                         "Finding ngày đầu kỳ kế (01/04) bị lọt vào T3 — "
                         "off-by-one upper-bound (Frappe between inclusive)")
        self.assertEqual(sc_t3["non_compliant"], 1)
        # Heatmap T3: cùng kết luận — chỉ 1 finding trong cell IMM-08.
        self.assertIsNotNone(cell_t3, "Heatmap T3 phải có cell IMM-08")
        self.assertEqual(cell_t3["findings_count"], 1)
        # Parity boundary: scorecard và heatmap cùng đếm 1 → cùng _period_bounds.
        self.assertEqual(cell_t3["findings_count"], sc_t3["total_findings"])


class TestScorecardImmutabilityBR1611(TestImm16Base):
    """[BE TDD-6] VR-09 immutability KHÔNG hồi quy sau khi đổi sang SoT."""

    def test_tdd6_published_scorecard_score_immutable(self):
        for nm in frappe.get_all(
            "IMM Compliance Scorecard",
            filters={"period_year": 2027, "period_month": 9},
            pluck="name",
        ):
            _delete_if_exists("IMM Compliance Scorecard", nm)
        sc_doc = frappe.get_doc({
            "doctype": "IMM Compliance Scorecard",
            "period_year": 2027, "period_month": 9,
            "scope": "Hospital", "score_pct": 50.0,
            "non_compliant_count": 1, "compliant_count": 1,
            "is_published": 1,
        })
        sc_doc.flags.ignore_mandatory = True
        sc_doc.insert(ignore_permissions=True)
        frappe.db.commit()
        self.addCleanup(
            lambda: _delete_if_exists("IMM Compliance Scorecard", sc_doc.name))
        # Mutate score_pct on a published scorecard → VR-09 must block.
        sc_doc.score_pct = 99.9
        with self.assertRaises(ServiceError) as ctx:
            svc.validate_scorecard_immutability(sc_doc)
        self.assertEqual(ctx.exception.code, "VALIDATION")


# ── LL-BE: QA persona dashboard "Điểm tuân thủ" reads canonical SoT field ───
#
# Root cause: api/dashboard.py::_build_qa đọc score qua các field PHANTOM
# (`overall_score`/`score`/`total_score`) — đây là field của IMM-03 Supplier
# Scorecard + IMM Internal Audit, KHÔNG tồn tại trên IMM Compliance Scorecard
# (SoT field = `score_pct`, do generate_scorecard ghi qua compute_compliance_rate).
# Hệ quả: card "Điểm tuân thủ" LUÔN None ('Chưa có scorecard kỳ này') dù đã có
# scorecard kỳ này. Test bind KPI vào CÙNG field SoT mà scorecard ghi.

class TestQaPersonaComplianceScoreSoT(TestImm16Base):
    """[BE TDD-1..5] _build_qa.compliance_score đọc score_pct (SoT IMM-16),
    KHÔNG đọc overall_score/total_score (IMM-03/Internal Audit phantom)."""

    @staticmethod
    def _current_period():
        from frappe.utils import getdate
        today = getdate(nowdate())
        return today.year, today.month

    def _purge_current_scorecard(self):
        year, month = self._current_period()
        for nm in frappe.get_all(
            "IMM Compliance Scorecard",
            filters={"period_year": year, "period_month": month,
                     "scope": "Hospital"},
            pluck="name",
        ):
            _delete_if_exists("IMM Compliance Scorecard", nm)
        frappe.db.commit()

    def _seed_current_scorecard(self, score_pct: float = 87.5) -> str:
        """Seed a Compliance Scorecard for the CURRENT period/scope.

        get_current_scorecard() neo kỳ theo nowdate() → phải seed đúng kỳ hôm
        nay để _build_qa đọc được. Trả về docname (đăng ký cleanup)."""
        self._purge_current_scorecard()
        year, month = self._current_period()
        doc = frappe.get_doc({
            "doctype": "IMM Compliance Scorecard",
            "period_year": year, "period_month": month,
            "scope": "Hospital", "score_pct": score_pct,
            "non_compliant_count": 1, "compliant_count": 7,
            "total_rules_evaluated": 8, "is_published": 0,
        })
        doc.flags.ignore_mandatory = True
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        self.addCleanup(self._purge_current_scorecard)
        return doc.name

    @staticmethod
    def _qa_kpi(key: str):
        """Build QA persona payload và bóc 1 KPI theo key."""
        from assetcore.api.dashboard import _build_qa
        payload = _build_qa({})
        for kpi in payload["kpis"]:
            if kpi["key"] == key:
                return kpi
        return None

    def test_tdd1_compliance_score_reads_score_pct(self):
        """[BE TDD-1] Có scorecard kỳ này (draft) score_pct=87.5 →
        compliance_score.value == 87.5 (KHÔNG None) + foot 'Mục tiêu ≥ 85'."""
        self._seed_current_scorecard(87.5)
        kpi = self._qa_kpi("compliance_score")
        self.assertIsNotNone(kpi, "compliance_score KPI missing in QA dashboard")
        self.assertEqual(kpi["value"], 87.5)
        self.assertEqual(kpi["foot_vi"], "Mục tiêu ≥ 85")

    def test_tdd2_no_scorecard_preserves_none_and_foot(self):
        """[BE TDD-2] Không scorecard kỳ này → value None (no false 0.0) +
        foot 'Chưa có scorecard kỳ này' (behavior preserved)."""
        self._purge_current_scorecard()
        self.addCleanup(self._purge_current_scorecard)
        kpi = self._qa_kpi("compliance_score")
        self.assertIsNotNone(kpi)
        self.assertIsNone(kpi["value"])
        self.assertEqual(kpi["foot_vi"], "Chưa có scorecard kỳ này")

    def test_tdd3_kpi_bound_to_sot_field(self):
        """[BE TDD-3] divergence guard: score _build_qa trả == score_pct của
        get_current_scorecard() — bind KPI vào SoT, re-break nếu ai revert về
        overall_score."""
        self._seed_current_scorecard(73.0)
        from assetcore.services.imm16 import get_current_scorecard
        sc = get_current_scorecard()
        self.assertEqual(sc.get("exists"), None)  # hit → as_dict(), no 'exists'
        kpi = self._qa_kpi("compliance_score")
        self.assertEqual(kpi["value"], float(sc["score_pct"]))

    def test_tdd4_value_is_float_or_none(self):
        """[BE TDD-4] type guard: value là float khi có scorecard, None khi
        không — KHÔNG bao giờ str/Decimal (FE numeric format an toàn)."""
        self._seed_current_scorecard(91.25)
        kpi = self._qa_kpi("compliance_score")
        self.assertIsInstance(kpi["value"], float)
        # No-scorecard branch → None.
        self._purge_current_scorecard()
        self.addCleanup(self._purge_current_scorecard)
        kpi2 = self._qa_kpi("compliance_score")
        self.assertIsNone(kpi2["value"])

    def test_tdd5_grep_guard_no_phantom_field_read(self):
        """[BE TDD-5] grep guard: _build_qa KHÔNG ĐỌC field phantom
        overall_score/total_score (IMM-03 Supplier Scorecard / Internal Audit)
        khỏi scorecard object — chỉ đọc canonical `score_pct`.

        Quét trên CODE thực thi (loại comment/docstring) để guard bắt đúng
        root-cause: một `sc.get("overall_score")` READ. Comment giải thích
        'KHÔNG đọc overall_score' là HỢP LỆ (không phải read) → không tính."""
        import ast
        import inspect
        from assetcore.api import dashboard

        src = inspect.getsource(dashboard._build_qa)
        # Strip comment lines (# ...) trước khi match — comment chứa tên field
        # cảnh báo là hợp lệ; chỉ executable read mới re-break card.
        code_lines = [ln for ln in src.splitlines()
                      if not ln.lstrip().startswith("#")]
        code_only = "\n".join(code_lines)
        for phantom in ('"overall_score"', "'overall_score'",
                        '"total_score"', "'total_score'"):
            self.assertNotIn(
                phantom, code_only,
                f"_build_qa must not READ phantom field {phantom} "
                "(IMM-03/Internal-Audit), only IMM-16 SoT 'score_pct'")
        # Positive: phải đọc score_pct.
        self.assertIn('"score_pct"', code_only,
                      "_build_qa must read canonical SoT field 'score_pct'")

        # AST belt-and-suspenders: collect every str literal passed to a
        # `<obj>.get(...)` call inside _build_qa — assert none is a phantom.
        tree = ast.parse(src.strip())
        read_keys: set[str] = set()
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "get"
                    and node.args
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)):
                read_keys.add(node.args[0].value)
        self.assertNotIn("overall_score", read_keys)
        self.assertNotIn("total_score", read_keys)
        self.assertIn("score_pct", read_keys,
                      "_build_qa must .get('score_pct') from scorecard SoT")


# ── LL-BE: QA persona "compliance_findings" worklist uses FindingStatus.ACTIVE ─
#
# Root cause: api/dashboard.py::_build_qa lọc findings bằng NOT IN [Closed]
# → leak Resolved/Waived/False Positive vào danh sách việc của QA reviewer
# (chỉ Closed bị loại). SoT IMM-16 coi "đang hoạt động" = FindingStatus.ACTIVE
# = (Open, Under Review, Confirmed NC) — dùng tại imm16.py:680/1405/2157/2346.
# Test bind worklist vào CÙNG SoT → không divergence + chống tái phát.

class TestQaPersonaComplianceFindingsActive(TestImm16Base):
    """[BE TDD] section 'compliance_findings' của QA persona chỉ chứa finding
    thuộc FindingStatus.ACTIVE (Open/Under Review/Confirmed NC), KHÔNG chứa
    Resolved/Waived/False Positive/Closed."""

    def _seed_finding(self, status: str) -> str:
        """Tạo finding committed cho rule fixture, set status trực tiếp.

        Mỗi finding 1 evaluation_date riêng (tránh dedup (rule, src, eval) của
        create_finding). detected_date = nowdate() để rơi vào trang đầu
        (order_by detected_date desc, page_size=10)."""
        self._fnd_day = getattr(self, "_fnd_day", 0) + 1
        eval_date = f"2027-04-{self._fnd_day:02d}"
        res = svc.create_finding(
            rule_ref=self.rule, asset_ref="", work_order_ref="",
            severity="High", description=f"QA worklist regression {status}",
            evaluation_date=eval_date,
        )
        name = res["name"]
        frappe.db.set_value(
            "IMM Compliance Finding", name,
            {"status": status,
             "evaluation_date": eval_date,
             "detected_date": f"{nowdate()} 09:00:00",
             "responsible_dept": None},
            update_modified=False,
        )
        frappe.db.commit()
        self.addCleanup(_delete_if_exists, "IMM Compliance Finding", name)
        return name

    def _seed_all_statuses(self) -> dict:
        """Seed 1 finding mỗi trạng thái. Trả map status→name."""
        from assetcore.services.imm16 import FindingStatus
        statuses = [
            FindingStatus.OPEN, FindingStatus.UNDER_REVIEW,
            FindingStatus.CONFIRMED_NC, FindingStatus.RESOLVED,
            FindingStatus.WAIVED, FindingStatus.FALSE_POSITIVE,
            FindingStatus.CLOSED,
        ]
        return {s: self._seed_finding(s) for s in statuses}

    @staticmethod
    def _qa_finding_names() -> set:
        from assetcore.api.dashboard import _build_qa
        payload = _build_qa({})
        rows = payload["sections"]["compliance_findings"]
        return {r["name"] for r in rows}

    def test_qa_persona_compliance_findings_only_active(self):
        """[BE TDD-1] Seed 1 finding mỗi trạng thái → section
        'compliance_findings' CHỈ chứa 3 finding ACTIVE (Open/Under Review/
        Confirmed NC), KHÔNG chứa Resolved/Waived/False Positive/Closed."""
        from assetcore.services.imm16 import FindingStatus
        names = self._seed_all_statuses()
        got = self._qa_finding_names()
        for st in FindingStatus.ACTIVE:
            self.assertIn(
                names[st], got,
                f"ACTIVE finding ({st}) phải có trong worklist QA persona")
        for st in (FindingStatus.RESOLVED, FindingStatus.WAIVED,
                   FindingStatus.FALSE_POSITIVE, FindingStatus.CLOSED):
            self.assertNotIn(
                names[st], got,
                f"finding {st} KHÔNG được leak vào worklist QA persona")

    def test_qa_persona_findings_matches_active_sot(self):
        """[BE TDD-2] divergence guard: tập name trong section
        'compliance_findings' == tập name list_compliance_findings(
        {status: in list(FindingStatus.ACTIVE)}) — cùng SoT, không divergence."""
        from assetcore.services.imm16 import (
            FindingStatus, list_compliance_findings)
        self._seed_all_statuses()
        got = self._qa_finding_names()
        sot_rows = list_compliance_findings(
            {"status": ["in", list(FindingStatus.ACTIVE)]},
            page=1, page_size=10).get("data", [])
        sot_names = {r["name"] for r in sot_rows}
        self.assertEqual(
            got, sot_names,
            "worklist QA persona phải == tập SoT FindingStatus.ACTIVE")

    def test_qa_persona_no_not_in_closed_predicate(self):
        """[BE TDD-3] contract guard: trên ĐƯỜNG finding của _build_qa KHÔNG
        còn literal NOT IN [Closed] (chỉ còn ở capa_rows). Chống tái phát
        cross-predicate drift — bind finding vào FindingStatus.ACTIVE."""
        import inspect
        from assetcore.api import dashboard

        src = inspect.getsource(dashboard._build_qa)
        code_lines = [ln for ln in src.splitlines()
                      if not ln.lstrip().startswith("#")]
        # Cô lập statement gán `findings = list_compliance_findings(...)`.
        finding_stmt = ""
        capture = False
        for ln in code_lines:
            if "findings = list_compliance_findings" in ln:
                capture = True
            if capture:
                finding_stmt += ln + "\n"
                if ".get(" in ln and ")" in ln and "findings" not in ln.split("=")[0]:
                    # đến dòng kết .get("data", []) → kết thúc statement
                    break
                if finding_stmt.count("(") <= finding_stmt.count(")") and "list_compliance_findings" in finding_stmt:
                    break
        self.assertIn("list_compliance_findings", finding_stmt,
                      "không tìm thấy statement findings trong _build_qa")
        self.assertIn("FindingStatus.ACTIVE", finding_stmt,
                      "đường finding phải dùng FindingStatus.ACTIVE (SoT)")
        for closed_lit in ('["Closed"]', "['Closed']"):
            self.assertNotIn(
                closed_lit, finding_stmt,
                "đường finding KHÔNG còn literal NOT IN [Closed]")

    def test_qa_persona_capa_rows_predicate_unchanged(self):
        """[BE TDD-4] regression: capa_rows của QA persona KHÔNG đổi (vẫn
        status NOT IN Closed) — fix finding KHÔNG lan sang predicate CAPA."""
        import inspect
        from assetcore.api import dashboard

        src = inspect.getsource(dashboard._build_qa)
        code_lines = [ln for ln in src.splitlines()
                      if not ln.lstrip().startswith("#")]
        code_only = "\n".join(code_lines)
        # capa_rows vẫn phải gate bằng NOT IN [Closed].
        self.assertIn("capa_rows", code_only)
        self.assertTrue(
            '["Closed"]' in code_only or "['Closed']" in code_only,
            "capa_rows phải GIỮ predicate status NOT IN [Closed]")


# ── TC-16-CTA: server-driven CTA — allowed_transitions + can_create_capa ────
#
# GATE-8 / LL-FE-51 (đối xứng test_imm09.TestRepairAllowedTransitions): get_finding
# emit `allowed_transitions` (SoT = _FINDING_VALID_TRANSITIONS) + cờ eligibility
# `can_create_capa` để FE gate nút status-CTA / CAPA theo SERVER, KHÔNG hardcode
# finding.status===X client-side. SoT map = docs/imm-16/04 §III.B.1 (BA-chotted):
# Confirmed NC → ['Waived'] CHỈ (KHÔNG 'Closed' — hint dối).
class TestFindingAllowedTransitions(TestImm16Base):
    def _finding_in_status(self, status: str, *, capa_ref: str = "") -> str:
        data = {
            "rule": self.rule,
            "detected_date": nowdate(),
            "evaluation_date": nowdate(),
            "severity": "High",
            "status": status,
        }
        if capa_ref:
            data["capa_ref"] = capa_ref
        return _ensure("IMM Compliance Finding", "TEST-FND-CTA-01", data)

    def test_open_transitions_and_capa_flag(self):
        """[BE TDD-1] Open → allowed = {Confirmed NC, False Positive, Waived};
        can_create_capa == 0 (chưa Confirmed NC)."""
        name = self._finding_in_status(FindingStatus.OPEN)
        data = svc.get_finding(name)
        self.assertIn(FindingStatus.CONFIRMED_NC, data["allowed_transitions"])
        self.assertIn(FindingStatus.FALSE_POSITIVE, data["allowed_transitions"])
        self.assertIn(FindingStatus.WAIVED, data["allowed_transitions"])
        self.assertEqual(data["can_create_capa"], 0)

    def test_under_review_mirrors_open(self):
        """[BE TDD-1b] Under Review đối xứng Open (cùng codomain)."""
        name = self._finding_in_status(FindingStatus.UNDER_REVIEW)
        data = svc.get_finding(name)
        self.assertCountEqual(
            data["allowed_transitions"],
            [FindingStatus.CONFIRMED_NC, FindingStatus.FALSE_POSITIVE,
             FindingStatus.WAIVED],
        )
        self.assertEqual(data["can_create_capa"], 0)

    def test_confirmed_nc_without_capa(self):
        """[BE TDD-2] Confirmed NC (chưa capa_ref) → allowed chứa 'Waived'
        (KHÔNG 'Closed' — SoT 04 §III.B.1); can_create_capa == 1."""
        name = self._finding_in_status(FindingStatus.CONFIRMED_NC)
        data = svc.get_finding(name)
        self.assertIn(FindingStatus.WAIVED, data["allowed_transitions"])
        self.assertNotIn(
            FindingStatus.CLOSED, data["allowed_transitions"],
            "Confirmed NC KHÔNG advertise 'Closed' (close_finding→Resolved; "
            "Resolved→Closed là cạnh workflow-engine, không status-CTA)")
        self.assertEqual(data["can_create_capa"], 1)

    def test_confirmed_nc_with_capa_flag_off(self):
        """[BE TDD-3] Confirmed NC ĐÃ có capa_ref → can_create_capa == 0."""
        name = self._finding_in_status(
            FindingStatus.CONFIRMED_NC, capa_ref="CAPA-2026-99999")
        data = svc.get_finding(name)
        self.assertEqual(data["can_create_capa"], 0)

    def test_terminal_states_empty(self):
        """[BE TDD-4] terminal (Waived/Closed/False Positive/Resolved) →
        allowed_transitions == []; can_create_capa == 0."""
        for st in (FindingStatus.WAIVED, FindingStatus.CLOSED,
                   FindingStatus.FALSE_POSITIVE, FindingStatus.RESOLVED):
            name = self._finding_in_status(st)
            data = svc.get_finding(name)
            self.assertEqual(data["allowed_transitions"], [],
                             f"{st} phải terminal (0 status-CTA)")
            self.assertEqual(data["can_create_capa"], 0,
                             f"{st}: can_create_capa phải 0")

    def test_confirm_on_waived_raises_bad_state(self):
        """[BE TDD-5] Invariant guard: confirm_finding trên Finding Waived →
        ServiceError(BAD_STATE). allowed_transitions là hint hiển thị, KHÔNG
        bypass guard BE (defense-in-depth)."""
        name = self._finding_in_status(FindingStatus.WAIVED)
        with self.assertRaises(ServiceError) as ctx:
            svc.confirm_finding(name, "reviewer note")
        self.assertEqual(ctx.exception.code, ErrorCode.BAD_STATE)

    def test_confirm_on_confirmed_nc_raises_bad_state(self):
        """[BE TDD-5b] confirm_finding trên Finding Confirmed NC → BAD_STATE
        (siết guard ACTIVE→REVIEWABLE, đóng self-confirm — 04 §III.B.1)."""
        name = self._finding_in_status(FindingStatus.CONFIRMED_NC)
        with self.assertRaises(ServiceError) as ctx:
            svc.confirm_finding(name, "reviewer note")
        self.assertEqual(ctx.exception.code, ErrorCode.BAD_STATE)

    def test_map_invariant_codomain_subset_and_keyed_by_status(self):
        """[BE TDD-6] Invariant map↔state-machine: codomain ⊆ FindingStatus
        enum (chống typo/drift) + key ⊆ enum. Terminal → []."""
        from assetcore.services.imm16 import _FINDING_VALID_TRANSITIONS
        valid = {
            FindingStatus.OPEN, FindingStatus.UNDER_REVIEW,
            FindingStatus.CONFIRMED_NC, FindingStatus.FALSE_POSITIVE,
            FindingStatus.RESOLVED, FindingStatus.WAIVED, FindingStatus.CLOSED,
        }
        for src_status, targets in _FINDING_VALID_TRANSITIONS.items():
            self.assertIn(src_status, valid, f"key {src_status} ⊄ enum")
            for t in targets:
                self.assertIn(t, valid, f"đích {t} ⊄ FindingStatus enum")
        # confirm/mark_false_positive ⊆ REVIEWABLE; waive ⊆ WAIVABLE;
        # start_review ⊆ START_REVIEWABLE — map KHÔNG advertise transition guard
        # sẽ từ chối (round 14: +UNDER_REVIEW ∈ map[Open] khớp START_REVIEWABLE).
        for src_status, targets in _FINDING_VALID_TRANSITIONS.items():
            if FindingStatus.CONFIRMED_NC in targets or \
               FindingStatus.FALSE_POSITIVE in targets:
                self.assertIn(src_status, FindingStatus.REVIEWABLE)
            if FindingStatus.WAIVED in targets:
                self.assertIn(src_status, FindingStatus.WAIVABLE)
            if FindingStatus.UNDER_REVIEW in targets:
                self.assertIn(src_status, FindingStatus.START_REVIEWABLE)


# ── AT-16-10..16: dual-track lockstep workflow_state ⇄ status (CR-WF-16-FIND) ─
#
# Root cause: transition-fn Finding set doc.status NHƯNG KHÔNG chạm
# doc.workflow_state → workflow_state đọng 'Open' vĩnh viễn trên workflow ĐANG
# ACTIVE (is_active=1). Fix (§III.B.2 ADR-IMM-16-05): SAU mỗi transition,
# frappe.db.set_value(..., {"workflow_state": <status>}) lockstep. RED-before:
# workflow_state đọng 'Open'; GREEN-after: workflow_state == status.
class TestFindingDualTrackLockstep(TestImm16Base):
    def _finding(self, name: str, status: str, **extra) -> str:
        return _ensure("IMM Compliance Finding", name, {
            "rule": self.rule,
            "detected_date": nowdate(),
            "evaluation_date": nowdate(),
            "severity": "High",
            "status": status,
            "workflow_state": status,
            **extra,
        })

    def _track(self, name: str) -> dict:
        return frappe.db.get_value(
            "IMM Compliance Finding", name, ["status", "workflow_state"],
            as_dict=True)

    def test_at_16_10_confirm_locksteps_workflow_state(self):
        """AT-16-10 (RED→GREEN): Open → confirm_finding → status AND
        workflow_state == 'Confirmed NC' (RED: workflow_state đọng 'Open')."""
        name = self._finding("TEST-FND-LOCK-CFM", FindingStatus.OPEN)
        svc.confirm_finding(name, "kiểm tra vi phạm")
        row = self._track(name)
        self.assertEqual(row.status, FindingStatus.CONFIRMED_NC)
        self.assertEqual(row.workflow_state, FindingStatus.CONFIRMED_NC,
                         "workflow_state phải lockstep với status (đọng 'Open' = RED)")

    def test_at_16_11_mark_false_positive_locksteps(self):
        """AT-16-11: Open → mark_false_positive → cả hai == 'False Positive'."""
        name = self._finding("TEST-FND-LOCK-FP", FindingStatus.OPEN)
        svc.mark_false_positive(name, "cảnh báo sai do lỗi cảm biến")
        row = self._track(name)
        self.assertEqual(row.status, FindingStatus.FALSE_POSITIVE)
        self.assertEqual(row.workflow_state, FindingStatus.FALSE_POSITIVE)

    def test_at_16_12_waive_locksteps(self):
        """AT-16-12: Under Review → waive_finding (VR-04) → cả hai == 'Waived'."""
        name = self._finding("TEST-FND-LOCK-WV", FindingStatus.UNDER_REVIEW)
        svc.waive_finding(
            name,
            waiver_reason="Thiết bị dự phòng, không sử dụng lâm sàng nên tạm "
                          "miễn áp dụng tới khi tái vận hành theo kế hoạch.",
            waiver_evidence="/files/waiver-approval.pdf",
            waiver_expiry=add_days(nowdate(), 60),
        )
        row = self._track(name)
        self.assertEqual(row.status, FindingStatus.WAIVED)
        self.assertEqual(row.workflow_state, FindingStatus.WAIVED)

    def test_at_16_13_close_locksteps(self):
        """AT-16-13: Confirmed NC → close_finding → cả hai == 'Resolved'
        (EXCEPTION_EDGE CAPA-auto @imm16:720)."""
        name = self._finding("TEST-FND-LOCK-CLS", FindingStatus.CONFIRMED_NC)
        svc.close_finding(name, capa_ref="", resolution_note="Đã khắc phục")
        row = self._track(name)
        self.assertEqual(row.status, FindingStatus.RESOLVED)
        self.assertEqual(row.workflow_state, FindingStatus.RESOLVED)

    def test_at_16_14_capa_cascade_locksteps(self):
        """AT-16-14: CAPA (source_type='Compliance Finding') → Closed → cascade
        Finding status AND workflow_state == 'Resolved'."""
        if not self.test_asset:
            self.skipTest("No AC Asset found")
        finding = self._finding("TEST-FND-LOCK-CASC", FindingStatus.CONFIRMED_NC)
        # source_type = canonical Select value (imm16:1826/1882); chuỗi cũ
        # "Compliance Finding" KHÔNG có trong Select ⇒ cascade DEAD (root-cause phụ).
        capa = _ensure("IMM CAPA Record", "TEST-CAPA-CASC-01", {
            "asset": self.test_asset,
            "source_type": "IMM Compliance Finding",
            "source_ref": finding,
            "severity": "Major",
            "description": "Cascade resolve test",
            "opened_date": nowdate(),
            "due_date": add_days(nowdate(), 30),
            "responsible": "Administrator",
            "status": "Closed",
        })
        svc.capa_record_on_update(frappe.get_doc("IMM CAPA Record", capa))
        row = self._track(finding)
        self.assertEqual(row.status, FindingStatus.RESOLVED)
        self.assertEqual(row.workflow_state, FindingStatus.RESOLVED,
                         "cascade CAPA phải đặt CẢ HAI track lockstep")

    def test_at_16_15_start_review_locksteps(self):
        """AT-16-15 (RED→GREEN): Open → start_review → cả hai == 'Under Review'
        (fn mới; surface phantom Open→Under Review)."""
        name = self._finding("TEST-FND-LOCK-SR", FindingStatus.OPEN)
        res = svc.start_review(name, "bắt đầu điều tra hồ sơ")
        self.assertEqual(res["status"], FindingStatus.UNDER_REVIEW)
        row = self._track(name)
        self.assertEqual(row.status, FindingStatus.UNDER_REVIEW)
        self.assertEqual(row.workflow_state, FindingStatus.UNDER_REVIEW)

    def test_at_16_16_start_review_guard_non_open(self):
        """AT-16-16: start_review từ status ≠ Open (Under Review/Confirmed NC) →
        BAD_STATE (START_REVIEWABLE = (Open,))."""
        for st in (FindingStatus.UNDER_REVIEW, FindingStatus.CONFIRMED_NC):
            name = self._finding("TEST-FND-LOCK-GRD", st)
            with self.assertRaises(ServiceError) as ctx:
                svc.start_review(name)
            self.assertEqual(ctx.exception.code, ErrorCode.BAD_STATE,
                             f"start_review từ {st} phải BAD_STATE")


# ── AT-16-17: INVARIANT map codomain ⇄ workflow next_state (CR-WF-16-FIND) ────
#
# Guard chống drift phantom giữa SSoT service-CTA (_FINDING_VALID_TRANSITIONS,
# sinh allowed_transitions → CTA FE) và state-machine imm_16_finding_workflow.json.
# §III.B.2 INV-16-A/B/C. RED trước round 14: 'Under Review' ∈ (wf_next − codomain)
# NHƯNG ∉ EXCEPTION_EDGES ⇒ INV-16-B FAIL (phantom chưa phân định). GREEN sau:
# thêm 'Under Review' vào codomain (map[Open]) ⇒ wf_next − codomain == {Resolved,
# Closed} = EXCEPTION_EDGES. Đối xứng TestIncidentAllowedTransitions (test_imm12).
def _load_finding_workflow_next_states() -> set[str]:
    path = frappe.get_app_path(
        "assetcore", "assetcore", "workflow", "imm_16_finding_workflow.json")
    with open(path, encoding="utf-8") as fh:
        wf = json.load(fh)
    return {tr["next_state"] for tr in wf["transitions"]}


class TestFindingWorkflowInvariant(unittest.TestCase):
    def _codomain(self) -> set[str]:
        from assetcore.services.imm16 import _FINDING_VALID_TRANSITIONS
        return {t for tgts in _FINDING_VALID_TRANSITIONS.values() for t in tgts}

    def test_inv_16_a_codomain_reachable_in_workflow(self):
        """INV-16-A: mọi đích CTA advertise PHẢI reachable trong workflow
        (codomain − wf_next == ∅) — 0 nút dead/bypass."""
        codomain = self._codomain()
        wf_next = _load_finding_workflow_next_states()
        self.assertEqual(
            codomain - wf_next, set(),
            f"_FINDING_VALID_TRANSITIONS advertise đích KHÔNG có cạnh workflow: "
            f"{codomain - wf_next}")

    def test_inv_16_b_workflow_extra_states_are_documented_exceptions(self):
        """INV-16-B (RED→GREEN): state workflow KHÔNG do map-CTA sinh ⊆
        _FINDING_EXCEPTION_EDGES = {Resolved, Closed}. RED trước round 14:
        'Under Review' ∈ dư-thừa NHƯNG ∉ EXCEPTION ⇒ FAIL."""
        from assetcore.services.imm16 import _FINDING_EXCEPTION_EDGES
        codomain = self._codomain()
        wf_next = _load_finding_workflow_next_states()
        self.assertEqual(
            _FINDING_EXCEPTION_EDGES,
            {FindingStatus.RESOLVED, FindingStatus.CLOSED},
            "EXCEPTION_EDGES phải đúng 2 cạnh acceptance nêu (Resolved, Closed)")
        self.assertEqual(
            wf_next - codomain, _FINDING_EXCEPTION_EDGES,
            f"State workflow ngoài codomain PHẢI == EXCEPTION_EDGES (drift "
            f"phantom nếu lệch): {wf_next - codomain}")

    def test_inv_16_c_service_produced_reachable(self):
        """INV-16-C: mọi status service SINH ĐƯỢC PHẢI reachable trong workflow."""
        wf_next = _load_finding_workflow_next_states()
        produced = {FindingStatus.CONFIRMED_NC, FindingStatus.FALSE_POSITIVE,
                    FindingStatus.WAIVED, FindingStatus.RESOLVED,
                    FindingStatus.UNDER_REVIEW}
        self.assertTrue(
            produced <= wf_next,
            f"status service-produced KHÔNG reachable: {produced - wf_next}")


# ── AT-16-CAPA-INV: INVARIANT 2 chiều _CAPA_TRANSITIONS ⇄ imm_16_capa_workflow.json ──
# (CR-WF-16-CAPA, round 19). Guard chống drift phantom giữa SSoT service-CTA
# (_CAPA_TRANSITIONS@imm16:1958 — sinh allowed_transitions → 6 CTA CAPADetailView) và
# state-machine imm_16_capa_workflow.json (is_active=1). §III.D.2 / ADR-IMM-16-07.
# KHÁC Finding (§III.B.2 codomain-only, EXCEPTION_EDGES={Resolved,Closed}): CAPA đối
# soát EDGE-by-EDGE (cặp state→next_state) 2 chiều — bắt cả drift "đúng đích, sai
# nguồn". Map đối xứng HOÀN TOÀN workflow (7 cạnh khớp 1-1) ⇒ EXCEPTION_EDGES=∅ cả 2
# chiều. Đối xứng TestFindingWorkflowInvariant + test_imm12.TestIncidentAllowedTransitions.

# 7 state CAPA hợp lệ (== states[] của imm_16_capa_workflow.json)
_CAPA_VALID_STATES = {
    "Open", "Investigating", "Action Plan", "Implementation",
    "Verification", "Re-opened", "Closed",
}
# EXCEPTION_EDGES = ∅ — map ⇄ workflow đối xứng hoàn toàn (0 cạnh miễn trừ 2 chiều).
# Đặt TEST-LEVEL (KHÔNG trong services/imm16.py) — round TEST-ONLY, 0 service change.
_CAPA_EXCEPTION_EDGES: frozenset = frozenset()


def _load_capa_workflow_edges() -> set:
    """Tập cạnh (state, next_state) DEDUPED của imm_16_capa_workflow.json.

    Workflow lặp transition theo vai (Compliance Manager / System Manager /
    AssetCore Super Admin) ⇒ nhiều entry cùng cạnh; set() gom về cạnh duy nhất.
    """
    path = frappe.get_app_path(
        "assetcore", "assetcore", "workflow", "imm_16_capa_workflow.json")
    with open(path, encoding="utf-8") as fh:
        wf = json.load(fh)
    return {(tr["state"], tr["next_state"]) for tr in wf["transitions"]}


class TestCapaWorkflowInvariant(unittest.TestCase):
    """CR-WF-16-CAPA: đối soát 2 chiều edge-by-edge _CAPA_TRANSITIONS ⇄ workflow JSON."""

    def _map_edges(self) -> set:
        return {(s, t) for s, tgts in svc._CAPA_TRANSITIONS.items() for t in tgts}

    def test_at_16_capa_inv_1_map_edges_subset_workflow(self):
        """INV-16-CAPA-1 (MAP⊆WF): mọi cạnh (state,next) trong _CAPA_TRANSITIONS
        là cạnh THẬT của workflow ∪ EXCEPTION_EDGES=∅ ⇒ 0 CTA dead/bypass."""
        extra = self._map_edges() - _load_capa_workflow_edges()
        self.assertEqual(
            extra, set(_CAPA_EXCEPTION_EDGES),
            f"_CAPA_TRANSITIONS advertise cạnh KHÔNG có trong workflow "
            f"(CTA dead/bypass): {sorted(extra)}")

    def test_at_16_capa_inv_2_workflow_edges_subset_map(self):
        """INV-16-CAPA-2 (WF⊆MAP): mọi cạnh (state→next_state) của workflow được
        map surface ∪ EXCEPTION_EDGES=∅. RED-before: strip 1 cạnh map (vd
        Verification→Re-opened) ⇒ cạnh workflow đó KHÔNG surface ⇒ FAIL (CTA câm)."""
        unsurfaced = _load_capa_workflow_edges() - self._map_edges()
        # message nêu RÕ cạnh drift + hệ quả (đối chiếu acceptance RED-before)
        detail = ", ".join(f"{s}→{t}" for s, t in sorted(unsurfaced)) or "∅"
        self.assertEqual(
            unsurfaced, set(_CAPA_EXCEPTION_EDGES),
            f"workflow có cạnh {detail} KHÔNG surface (CTA câm — nút duyệt CAPA "
            f"sẽ mất trên state machine 6-state)")

    def test_at_16_capa_inv_3_codomain_subset_valid_states(self):
        """Codomain (keys ∪ values) ⊆ 7 state CAPA hợp lệ — chống typo/orphan."""
        codomain = set(svc._CAPA_TRANSITIONS.keys()) | {
            t for tgts in svc._CAPA_TRANSITIONS.values() for t in tgts}
        orphans = codomain - _CAPA_VALID_STATES
        self.assertEqual(
            orphans, set(),
            f"_CAPA_TRANSITIONS chứa state KHÔNG hợp lệ (typo/orphan): {sorted(orphans)}")

    def test_at_16_capa_inv_4_terminal_closed_not_key(self):
        """Terminal 'Closed' ∉ keys ⇒ get_capa(CAPA Closed).allowed_transitions
        == [] (safe .get, KHÔNG KeyError). Live-proof: AC-16-5@test:557."""
        self.assertNotIn(
            "Closed", svc._CAPA_TRANSITIONS,
            "'Closed' là terminal — KHÔNG được là key (phải trả [] qua safe .get)")
        self.assertEqual(
            sorted(svc._CAPA_TRANSITIONS.get("Closed", set())), [],
            "allowed_transitions của Closed phải == []")


# ── AT-16-MR-INV: INVARIANT 2 chiều _MR_TRANSITIONS ⇄ imm_16_mr_workflow.json ──
# (CR-WF-16-MR, round 20). Guard chống drift phantom giữa SSoT service-CTA
# (_MR_TRANSITIONS@imm16:2391 — sinh allowed_transitions@imm16:2245 → CTA
# MRDetailView) và state-machine imm_16_mr_workflow.json (is_active=1). ĐÓNG NỐT
# quartet reconcile IMM-16 (Finding R14 / CAPA R19 / MR) — khoá 0 hidden-CTA-câm
# trên state machine MR 4-state (Draft→Held→Minutes Approved→Closed). ADR-IMM-16-07.
# KHÁC Finding (§III.B.2 codomain-only): MR đối soát EDGE-by-EDGE (cặp
# state→next_state) 2 chiều — bắt cả drift "đúng đích, sai nguồn". Map đối xứng HOÀN
# TOÀN workflow (3 cạnh khớp 1-1) ⇒ EXCEPTION_EDGES=∅ cả 2 chiều. Đối xứng
# TestCapaWorkflowInvariant + TestFindingWorkflowInvariant.
# NOTE: cạnh Minutes Approved→Closed thực thi bởi finalize_management_review@2340
# (advance_mr_state@2451 từ chối bằng VALIDATION) NHƯNG là cạnh workflow THẬT ⇒ ∈ cả
# map + json ⇒ reconcile SẠCH, KHÔNG phải exception-edge.

# 4 state MR hợp lệ (== states[] của imm_16_mr_workflow.json)
_MR_VALID_STATES = {"Draft", "Held", "Minutes Approved", "Closed"}
# EXCEPTION_EDGES = ∅ — map ⇄ workflow đối xứng hoàn toàn (0 cạnh miễn trừ 2 chiều).
# Đặt TEST-LEVEL (KHÔNG trong services/imm16.py) — round TEST-ONLY, 0 service change.
_MR_EXCEPTION_EDGES: frozenset = frozenset()


def _load_mr_workflow_edges() -> set:
    """Tập cạnh (state, next_state) DEDUPED của imm_16_mr_workflow.json.

    Workflow lặp transition theo vai (Compliance Manager / System Manager /
    AssetCore Super Admin) ⇒ nhiều entry cùng cạnh; set() gom về cạnh duy nhất.
    Mirror ``_load_capa_workflow_edges``.
    """
    path = frappe.get_app_path(
        "assetcore", "assetcore", "workflow", "imm_16_mr_workflow.json")
    with open(path, encoding="utf-8") as fh:
        wf = json.load(fh)
    return {(tr["state"], tr["next_state"]) for tr in wf["transitions"]}


class TestMrWorkflowInvariant(unittest.TestCase):
    """CR-WF-16-MR: đối soát 2 chiều edge-by-edge _MR_TRANSITIONS ⇄ workflow JSON."""

    def _map_edges(self) -> set:
        return {(s, t) for s, tgts in svc._MR_TRANSITIONS.items() for t in tgts}

    def test_at_16_mr_inv_1_map_edges_subset_workflow(self):
        """INV-16-MR-1 (MAP⊆WF): mọi cạnh (state,next) trong _MR_TRANSITIONS
        là cạnh THẬT của workflow ∪ EXCEPTION_EDGES=∅ ⇒ 0 CTA dead/bypass."""
        extra = self._map_edges() - _load_mr_workflow_edges()
        self.assertEqual(
            extra, set(_MR_EXCEPTION_EDGES),
            f"_MR_TRANSITIONS advertise cạnh KHÔNG có trong workflow "
            f"(CTA dead/bypass): {sorted(extra)}")

    def test_at_16_mr_inv_2_workflow_edges_subset_map(self):
        """INV-16-MR-2 (WF⊆MAP): mọi cạnh (state→next_state) của workflow được
        map surface ∪ EXCEPTION_EDGES=∅. RED-before: strip 1 cạnh map (vd
        Held→Minutes Approved) ⇒ cạnh workflow đó KHÔNG surface ⇒ FAIL (CTA câm)."""
        unsurfaced = _load_mr_workflow_edges() - self._map_edges()
        # message nêu RÕ cạnh drift + hệ quả (đối chiếu acceptance RED-before)
        detail = ", ".join(f"{s}→{t}" for s, t in sorted(unsurfaced)) or "∅"
        self.assertEqual(
            unsurfaced, set(_MR_EXCEPTION_EDGES),
            f"workflow có cạnh {detail} KHÔNG surface (CTA câm — nút duyệt MR mất)")

    def test_at_16_mr_inv_3_codomain_subset_valid_states(self):
        """Codomain (keys ∪ values) ⊆ 4 state MR hợp lệ — chống typo/orphan."""
        codomain = set(svc._MR_TRANSITIONS.keys()) | {
            t for tgts in svc._MR_TRANSITIONS.values() for t in tgts}
        orphans = codomain - _MR_VALID_STATES
        self.assertEqual(
            orphans, set(),
            f"_MR_TRANSITIONS chứa state KHÔNG hợp lệ (typo/orphan): {sorted(orphans)}")

    def test_at_16_mr_inv_4_terminal_closed_not_key(self):
        """Terminal 'Closed' ∉ keys ⇒ get_management_review(MR Closed)
        .allowed_transitions == [] (safe .get@imm16:2246, KHÔNG KeyError)."""
        self.assertNotIn(
            "Closed", svc._MR_TRANSITIONS,
            "'Closed' là terminal — KHÔNG được là key (phải trả [] qua safe .get)")
        self.assertEqual(
            sorted(svc._MR_TRANSITIONS.get("Closed", set())), [],
            "allowed_transitions của MR Closed phải == []")


# ── AT-16-AUD-INV: INVARIANT 2-chiều _AUDIT_VALID_TRANSITIONS ⇄ imm_16_internal_audit.json ──
# (CR-WF-16-AUDIT, round 22). ĐÓNG NỐT quartet reconcile IMM-16 (Finding R14 /
# CAPA R19 / MR R20 / Internal Audit R22) — khoá 0 hidden-CTA-câm + guard-
# permissive trên state machine Audit 4-state (Planned→In Progress→Reporting→
# Closed). §III.C.2 / ADR-IMM-16-09.
#
# KHÁC 3 workflow kia (map codomain = STATE-đích ⇒ edge-by-edge trực tiếp):
# Audit map codomain = ACTION-KEY (start/complete_checklist/close). ⇒ cần
# resolver ``_AUDIT_ACTION_TO_NEXT_STATE`` (action-key→AuditStatus, SSoT@imm16)
# bắc cầu action→state TRƯỚC khi đối soát per-state. Đối xứng
# TestFindingWorkflowInvariant + TestCapa/MrWorkflowInvariant + test_imm12
# TestIncidentAllowedTransitions. Pure map+resolver+JSON parse, KHÔNG DB fixture.

def _load_audit_workflow_state_edges() -> dict:
    """{state: set(next_state)} DEDUPED của imm_16_internal_audit.json.

    Workflow lặp transition theo vai (Compliance Manager / System Manager /
    AssetCore Super Admin) ⇒ nhiều entry cùng cạnh; set() gom về cạnh duy nhất
    per state (9 transition-entry → 3 cạnh: Planned→In Progress, In Progress→
    Reporting, Reporting→Closed)."""
    path = frappe.get_app_path(
        "assetcore", "assetcore", "workflow", "imm_16_internal_audit.json")
    with open(path, encoding="utf-8") as fh:
        wf = json.load(fh)
    edges: dict = {}
    for tr in wf["transitions"]:
        edges.setdefault(tr["state"], set()).add(tr["next_state"])
    return edges


def _load_audit_workflow_states() -> set:
    """states[] của imm_16_internal_audit.json (oracle độc lập)."""
    path = frappe.get_app_path(
        "assetcore", "assetcore", "workflow", "imm_16_internal_audit.json")
    with open(path, encoding="utf-8") as fh:
        wf = json.load(fh)
    return {s["state"] for s in wf["states"]}


class TestAuditWorkflowInvariant(unittest.TestCase):
    """CR-WF-16-AUDIT: đối soát 2-chiều _AUDIT_VALID_TRANSITIONS ⇄ workflow JSON
    qua resolver _AUDIT_ACTION_TO_NEXT_STATE (SSoT action-key→AuditStatus)."""

    _AUDIT_STATES = {"Planned", "In Progress", "Reporting", "Closed"}

    def test_at_16_aud_inv_1_map_keys_equal_workflow_states(self):
        """(a) set(_AUDIT_VALID_TRANSITIONS.keys()) == states[] workflow (4-state).
        Map keyed bằng status ⇒ mọi status của state-machine có 1 entry (kể cả
        terminal Closed → [])."""
        self.assertEqual(
            set(svc._AUDIT_VALID_TRANSITIONS.keys()),
            _load_audit_workflow_states(),
            "keys map (AuditStatus) PHẢI == states[] workflow (Planned, In "
            "Progress, Reporting, Closed)")

    def test_at_16_aud_inv_2_resolver_keys_are_the_3_handlers(self):
        """resolver keys == {start, complete_checklist, close} == 3 handler
        canonical whitelisted (start_audit / complete_audit_checklist /
        close_audit)."""
        self.assertEqual(
            set(svc._AUDIT_ACTION_TO_NEXT_STATE.keys()),
            {"start", "complete_checklist", "close"},
            "resolver keys PHẢI khớp 3 canonical handler whitelisted")

    def test_at_16_aud_inv_3_no_orphan_action(self):
        """Mọi action ∈ codomain(_AUDIT_VALID_TRANSITIONS) có entry resolver
        (no orphan — action advertise nhưng không dịch được → state)."""
        codomain = {a for acts in svc._AUDIT_VALID_TRANSITIONS.values()
                    for a in acts}
        orphans = codomain - set(svc._AUDIT_ACTION_TO_NEXT_STATE.keys())
        self.assertEqual(
            orphans, set(),
            f"action advertise KHÔNG có resolver entry (orphan): {sorted(orphans)}")

    def test_at_16_aud_inv_4_resolver_values_subset_status_enum(self):
        """values(resolver) ⊆ AuditStatus enum {Planned, In Progress, Reporting,
        Closed} — chống typo/orphan status-đích."""
        vals = set(svc._AUDIT_ACTION_TO_NEXT_STATE.values())
        self.assertTrue(
            vals <= self._AUDIT_STATES,
            f"resolver values ngoài AuditStatus enum: {vals - self._AUDIT_STATES}")
        # AuditStatus.* == 4 giá trị enum (oracle độc lập với set literal ở trên).
        self.assertEqual(
            {svc.AuditStatus.PLANNED, svc.AuditStatus.IN_PROGRESS,
             svc.AuditStatus.REPORTING, svc.AuditStatus.CLOSED},
            self._AUDIT_STATES)

    def test_at_16_aud_inv_5_per_state_map_equals_workflow(self):
        """(b) ∀ state: {resolver[a] for a in map[state]} == {next_state cạnh
        workflow từ state}. RED-before round 22 (perturbation THẬT): đổi 1 entry
        resolver (vd start→Reporting) HOẶC thêm 'close' vào map[In Progress] ⇒
        FAIL 'DRIFT <state>: map ≠ workflow'. Aligned hiện tại: Planned→{In
        Progress}, In Progress→{Reporting}, Reporting→{Closed}, Closed→∅."""
        wf_edges = _load_audit_workflow_state_edges()
        resolver = svc._AUDIT_ACTION_TO_NEXT_STATE
        for state in svc._AUDIT_VALID_TRANSITIONS:
            mapped = {resolver[a] for a in svc._AUDIT_VALID_TRANSITIONS[state]}
            wf_next = wf_edges.get(state, set())
            self.assertEqual(
                mapped, wf_next,
                f"DRIFT {state}: map ≠ workflow "
                f"(map→{sorted(mapped)} vs workflow→{sorted(wf_next)})")


if __name__ == "__main__":
    unittest.main()
