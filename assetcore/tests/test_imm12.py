"""IMM-12 Incident Report — test suite.

Run: bench --site miyano run-tests --module assetcore.tests.test_imm12
"""
from __future__ import annotations

import time
import unittest

import frappe

from assetcore.services.imm12 import (
    report_incident,
    acknowledge_incident,
    start_work,
    resolve_incident,
    close_incident,
    cancel_incident,
    list_rcas,
)
from assetcore.services.shared import ServiceError, ErrorCode
from assetcore.tests._asset_cleanup import purge_asset


# Unique per-run suffix to avoid Serial unique constraint conflicts when
# previous test runs left WR-03-protected assets behind (audit trail bảo toàn
# theo CLAUDE.md §10 — không thể hard-delete).
_RUN_TAG = str(int(time.time() * 1000))[-7:]


# ─── Fixture helpers ──────────────────────────────────────────────────────────

def _make_asset(suffix: str = "") -> object:
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    try:
        cat = _ensure_cat()
        return frappe.get_doc({
            "doctype": "AC Asset",
            "asset_name": f"_Test Asset IMM12{suffix}-{_RUN_TAG}",
            "asset_category": cat,
            "manufacturer_sn": f"SN-IMM12-{_RUN_TAG}-{suffix or '001'}",
            "lifecycle_status": "Active",
        }).insert(ignore_permissions=True)
    finally:
        frappe.flags.in_install = prev


def _ensure_cat() -> str:
    name = "_TestCatIMM12"
    # Lookup by unique business key (category_name), not autoname
    existing = frappe.db.get_value(
        "AC Asset Category", {"category_name": name}, "name"
    )
    if existing:
        return existing
    doc = frappe.get_doc({"doctype": "AC Asset Category", "category_name": name}).insert(
        ignore_permissions=True
    )
    return doc.name


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestIncidentCreation(unittest.TestCase):
    """BR-12-01/02: Validation + happy path for report_incident."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-ir")

    @classmethod
    def tearDownClass(cls):
        # purge_asset cancels submitted incidents/CAPA/RCA, purges audit trail
        # (raw SQL bypass of the ISO append-only guard) then deletes the asset.
        purge_asset(cls.asset.name)
        # Cleanup category by business key (autoname is CAT-####)
        cat_name = frappe.db.get_value(
            "AC Asset Category", {"category_name": "_TestCatIMM12"}, "name"
        )
        if cat_name:
            try:
                frappe.delete_doc("AC Asset Category", cat_name, force=True,
                                  ignore_permissions=True)
            except Exception:
                pass  # Other test classes may still hold ref

    def setUp(self):
        frappe.set_user("Administrator")

    def test_nonexistent_asset_raises_error(self):
        with self.assertRaises(Exception):
            report_incident(
                asset="DOES-NOT-EXIST",
                incident_type="Malfunction",
                severity="Low",
                description="_Test incident with nonexistent asset",
            )

    def test_critical_without_clinical_impact_raises_error(self):
        with self.assertRaises(Exception):
            report_incident(
                asset=self.asset.name,
                incident_type="Malfunction",
                severity="Critical",
                description="_Test critical incident without clinical_impact",
                clinical_impact="",
            )

    def test_create_medium_severity_incident(self):
        result = report_incident(
            asset=self.asset.name,
            incident_type="Malfunction",
            severity="Medium",
            description="_Test incident creation IMM-12 happy path",
        )
        frappe.db.commit()
        self.assertIn("name", result)
        doc = frappe.get_doc("Incident Report", result["name"])
        self.assertEqual(doc.status, "Open")
        self.assertEqual(doc.severity, "Medium")

    def test_create_critical_with_clinical_impact_succeeds(self):
        result = report_incident(
            asset=self.asset.name,
            incident_type="Safety Event",
            severity="Critical",
            description="_Test critical incident with clinical impact",
            clinical_impact="Patient monitoring interrupted",
        )
        frappe.db.commit()
        self.assertIn("name", result)
        doc = frappe.get_doc("Incident Report", result["name"])
        self.assertEqual(doc.severity, "Critical")


class TestIncidentWorkflow(unittest.TestCase):
    """BR-12-03: Full workflow Open → Under Investigation → Resolved → Closed in one test."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-wf")

    @classmethod
    def tearDownClass(cls):
        purge_asset(cls.asset.name)

    def setUp(self):
        frappe.set_user("Administrator")

    def test_full_workflow_open_to_closed(self):
        result = report_incident(
            asset=self.asset.name,
            incident_type="Malfunction",
            severity="Low",
            description="_Test workflow incident — enough chars for description",
        )
        frappe.db.commit()
        ir_name = result["name"]

        doc = frappe.get_doc("Incident Report", ir_name)
        self.assertEqual(doc.status, "Open")

        acknowledge_incident(ir_name, notes="_Test acknowledge")
        frappe.db.commit()
        doc.reload()
        self.assertEqual(doc.status, "Acknowledged")

        start_work(ir_name, notes="_Test start work")
        frappe.db.commit()
        doc.reload()
        self.assertEqual(doc.status, "In Progress")

        resolve_incident(
            ir_name,
            resolution_notes="_Test resolution notes",
            root_cause="Component failure",
        )
        frappe.db.commit()
        doc.reload()
        self.assertEqual(doc.status, "Resolved")

        close_incident(ir_name, verification_notes="_Test verified closed")
        frappe.db.commit()
        doc.reload()
        self.assertEqual(doc.status, "Closed")

    def test_acknowledge_goes_to_acknowledged_not_in_progress(self):
        """D3: acknowledge() chỉ đưa Open → Acknowledged (KHÔNG nhảy In Progress)."""
        result = report_incident(
            asset=self.asset.name,
            incident_type="Malfunction",
            severity="Low",
            description="_Test D3 acknowledge stops at Acknowledged",
        )
        frappe.db.commit()
        ir_name = result["name"]
        out = acknowledge_incident(ir_name, notes="_Test triage only")
        frappe.db.commit()
        self.assertEqual(out["status"], "Acknowledged")
        doc = frappe.get_doc("Incident Report", ir_name)
        self.assertEqual(doc.status, "Acknowledged")
        self.assertTrue(doc.acknowledged_at, "acknowledged_at phải được set")

    def test_resolve_blocked_from_acknowledged_requires_start_work(self):
        """D3: không thể resolve khi chưa start_work (Acknowledged → resolve illegal)."""
        result = report_incident(
            asset=self.asset.name,
            incident_type="Malfunction",
            severity="Low",
            description="_Test D3 resolve blocked before start_work",
        )
        frappe.db.commit()
        ir_name = result["name"]
        acknowledge_incident(ir_name)
        frappe.db.commit()
        with self.assertRaises(Exception):
            resolve_incident(ir_name, resolution_notes="_Test premature resolve")

    def test_start_work_advances_acknowledged_to_in_progress(self):
        """D3: start_work() đưa Acknowledged → In Progress."""
        result = report_incident(
            asset=self.asset.name,
            incident_type="Malfunction",
            severity="Low",
            description="_Test D3 start_work transition",
        )
        frappe.db.commit()
        ir_name = result["name"]
        acknowledge_incident(ir_name)
        frappe.db.commit()
        out = start_work(ir_name, notes="_Test begin")
        frappe.db.commit()
        self.assertEqual(out["status"], "In Progress")


class TestRCAListing(unittest.TestCase):
    """Task 2 — list_rcas endpoint cho RCAListView (/rca)."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-rcalist")
        # Tạo 1 incident High → resolve để auto-RCA
        from assetcore.services.imm12 import resolve_incident as _resolve
        result = report_incident(
            asset=cls.asset.name,
            incident_type="Malfunction",
            severity="High",
            description="_Test RCA list incident description",
        )
        frappe.db.commit()
        cls.ir_name = result["name"]
        acknowledge_incident(cls.ir_name)
        start_work(cls.ir_name)
        _resolve(cls.ir_name, resolution_notes="_Test resolve for RCA listing")
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        purge_asset(cls.asset.name)

    def test_list_rcas_returns_items_and_pagination(self):
        out = list_rcas(page=1, page_size=20)
        self.assertIn("items", out)
        self.assertIn("pagination", out)
        self.assertIsInstance(out["items"], list)

    def test_list_rcas_enriches_asset_name(self):
        out = list_rcas(asset=self.asset.name, page=1, page_size=20)
        for r in out["items"]:
            self.assertIn("asset_name", r, "Mỗi RCA row phải có asset_name enrich")

    def test_list_rcas_filter_by_method(self):
        out = list_rcas(method="5-Why", page=1, page_size=20)
        for r in out["items"]:
            self.assertEqual(r["rca_method"], "5-Why")


class TestIncidentCancellation(unittest.TestCase):
    """BR-12-04: Open incident can be cancelled."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-cancel")
        result = report_incident(
            asset=cls.asset.name,
            incident_type="Malfunction",
            severity="Low",
            description="_Test cancel flow — incident description here",
        )
        frappe.db.commit()
        cls.ir_name = result["name"]

    @classmethod
    def tearDownClass(cls):
        purge_asset(cls.asset.name)

    def test_cancel_from_open(self):
        cancel_incident(self.ir_name, reason="_Test cancel reason")
        frappe.db.commit()
        doc = frappe.get_doc("Incident Report", self.ir_name)
        self.assertEqual(doc.status, "Cancelled")


# ── RC-03 + RC-04: RCA → CAPA + Incident workflow chain ─────────────────────

class TestRCAToCAPAAndIncidentChain(unittest.TestCase):
    """RC-03: submit RCA → IMM CAPA Record được tạo và link 2-chiều.
    RC-04: submit RCA khi incident ở RCA Required → workflow advance → Closed.

    Cover function:
      - assetcore.services.imm12.on_rca_completed
      - assetcore.services.imm12._advance_incident_after_rca
      - assetcore.services.imm16.create_capa_from_incident (chain)
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-rcachain")

    @classmethod
    def tearDownClass(cls):
        # purge_asset cancels submitted CAPA/RCA/Incident (in dependency order) and
        # raw-SQL purges the audit trail before deleting the asset. CAPA whose
        # linked_incident points elsewhere are untouched (filtered by asset link).
        purge_asset(cls.asset.name)

    def setUp(self):
        frappe.set_user("Administrator")

    def _make_incident_at_rca_required(self) -> str:
        """Tạo Incident High → ack → resolve để asset rơi vào trạng thái auto-create RCA.

        Sau khi resolve_incident chạy với severity=High, service sẽ:
          - set requires_rca/rca_required = 1
          - auto-tạo IMM RCA Record và set incident.rca_record
        Đẩy workflow_state về "RCA Required" và bump RCA status="Completed"
        (mô phỏng tình huống thực tế khi RCA on_submit gọi on_rca_completed —
        validate_incident_close_gate cần RCA Completed để pass).
        """
        result = report_incident(
            asset=self.asset.name,
            incident_type="Malfunction",
            severity="High",
            description="_Test RCA chain incident description",
            clinical_impact="Test clinical impact for RCA chain",
        )
        frappe.db.commit()
        ir_name = result["name"]

        acknowledge_incident(ir_name, notes="_Test ack for RCA chain")
        frappe.db.commit()
        start_work(ir_name, notes="_Test start for RCA chain")
        frappe.db.commit()
        resolve_incident(
            ir_name,
            resolution_notes="_Test resolution for RCA chain",
            root_cause="Test root cause",
        )
        frappe.db.commit()

        # Đẩy workflow_state về RCA Required để RC-04 advance hợp lệ.
        frappe.db.set_value(
            "Incident Report", ir_name,
            {"workflow_state": "RCA Required", "requires_rca": 1, "rca_required": 1},
            update_modified=False,
        )
        # Bump auto-RCA về Completed để validate_incident_close_gate pass
        rca_name = frappe.db.get_value("Incident Report", ir_name, "rca_record")
        if rca_name:
            frappe.db.set_value(
                "IMM RCA Record", rca_name,
                {
                    "status": "Completed",
                    "root_cause": "Test root cause for RCA chain",
                    "corrective_action_summary": "Test corrective action",
                },
                update_modified=False,
            )
        frappe.db.commit()
        return ir_name

    def test_rca_no_incident_link_skips_silently(self):
        """RC-03/04: on_rca_completed với incident_name rỗng → no-op an toàn."""
        from assetcore.services.imm12 import on_rca_completed
        out = on_rca_completed("", "")
        self.assertFalse(out.get("workflow_advanced"))
        self.assertIsNone(out.get("capa_name"))

    def test_rca_invalid_incident_skips_silently(self):
        """on_rca_completed với incident không tồn tại → no-op."""
        from assetcore.services.imm12 import on_rca_completed
        out = on_rca_completed("INVALID-INCIDENT-XXX", "")
        self.assertFalse(out.get("workflow_advanced"))

    def test_rca_completed_creates_capa_and_advances_incident(self):
        """RC-03 + RC-04: chain đầy đủ.

        Flow:
          1. Tạo Incident High → auto RCA + workflow_state=RCA Required.
          2. Gọi on_rca_completed(incident, rca).
          3. Kỳ vọng:
             - IMM CAPA Record được tạo, linked_incident = incident.
             - Incident.linked_capa được set.
             - Incident workflow_state → 'Closed', status='Closed'.
        """
        from assetcore.services.imm12 import on_rca_completed

        ir_name = self._make_incident_at_rca_required()
        rca_name = frappe.db.get_value("Incident Report", ir_name, "rca_record")
        self.assertTrue(rca_name, "Auto-RCA phải được tạo sau resolve High incident")

        out = on_rca_completed(ir_name, rca_name)
        frappe.db.commit()

        # RC-03: CAPA tạo + link 2-chiều
        capa_name = out.get("capa_name")
        self.assertTrue(capa_name, "RC-03: CAPA phải được tạo sau RCA Completed")
        self.assertTrue(frappe.db.exists("IMM CAPA Record", capa_name))
        self.assertEqual(
            frappe.db.get_value("IMM CAPA Record", capa_name, "linked_incident"),
            ir_name,
            "RC-03: CAPA.linked_incident phải trỏ về incident",
        )
        self.assertEqual(
            frappe.db.get_value("Incident Report", ir_name, "linked_capa"),
            capa_name,
            "RC-03: Incident.linked_capa phải trỏ về CAPA mới",
        )

        # RC-04: Incident workflow advance → Closed
        self.assertTrue(
            out.get("workflow_advanced"),
            "RC-04: workflow phải advance khi incident đang ở RCA Required",
        )
        ir_state = frappe.db.get_value(
            "Incident Report", ir_name, ["workflow_state", "status"], as_dict=True,
        )
        self.assertEqual(
            ir_state.get("status"), "Closed",
            "RC-04: status sau RCA Completed phải = Closed",
        )

    def test_advance_skipped_when_not_in_rca_required(self):
        """RC-04: incident KHÔNG ở 'RCA Required' (vd Resolved) → no-op, không raise."""
        from assetcore.services.imm12 import _advance_incident_after_rca

        result = report_incident(
            asset=self.asset.name,
            incident_type="Malfunction",
            severity="Low",
            description="_Test advance skip — low severity no RCA",
        )
        frappe.db.commit()
        ir_name = result["name"]
        # workflow_state ở "Open", không phải RCA Required
        advanced = _advance_incident_after_rca(ir_name)
        self.assertFalse(
            advanced,
            "RC-04: nếu chưa ở RCA Required, _advance_incident_after_rca phải trả False",
        )

    def test_capa_chain_idempotent_when_capa_exists(self):
        """RC-03: gọi on_rca_completed 2 lần → reuse CAPA, không tạo bản trùng."""
        from assetcore.services.imm12 import on_rca_completed

        ir_name = self._make_incident_at_rca_required()
        rca_name = frappe.db.get_value("Incident Report", ir_name, "rca_record")

        first = on_rca_completed(ir_name, rca_name)
        frappe.db.commit()
        first_capa = first.get("capa_name")

        # Reset workflow_state để gọi lần 2 (tránh confound với close-state)
        frappe.db.set_value(
            "Incident Report", ir_name,
            {"workflow_state": "RCA Required"},
            update_modified=False,
        )
        frappe.db.commit()

        second = on_rca_completed(ir_name, rca_name)
        frappe.db.commit()
        second_capa = second.get("capa_name")

        self.assertEqual(
            first_capa, second_capa,
            "RC-03: gọi 2 lần phải reuse cùng CAPA (idempotent)",
        )
