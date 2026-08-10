"""IMM-12 Incident Report — test suite.

Run: bench --site miyano run-tests --module assetcore.tests.test_imm12
"""
from __future__ import annotations

import json
import time
import types
import unittest
from unittest.mock import patch

import frappe

from assetcore.services.imm12 import (
    report_incident,
    acknowledge_incident,
    start_work,
    resolve_incident,
    close_incident,
    cancel_incident,
    reopen_incident,
    request_rca,
    get_incident_detail,
    list_rcas,
    get_rca,
    create_rca,
    start_rca,
    submit_rca,
    cancel_rca,
    _RCA_VALID_TRANSITIONS,
    _VALID_TRANSITIONS,
    _build_incident_available_actions,
    _ACTION_REASON_TRANSITION,
    _ACTION_REASON_CAPABILITY,
    _ACTION_REASON_RCA_GATE,
)
from assetcore.services.shared import rbac
from assetcore.services.shared import ServiceError, ErrorCode
from assetcore.utils.messages import MSG
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


def _module_cleanup():
    """Safety net: purge IMM-12 test assets/categories + incidents and their
    auto-created RCA→CAPA chain if a class teardown gap left them (recurring
    '_TestCatIMM12' / '_Test incident for RCA' / RCA→CAPA leak).

    Invoked by ``tearDownModule`` (reliable when this module is run on its own).
    A whole-app ``run-tests --app`` run may re-create the empty shared category
    after the last hook fires; the maintenance purge scripts mop that up.
    """
    from contextlib import suppress

    from assetcore.tests._asset_cleanup import (
        purge_assets_by_name_prefix,
        purge_category_by_name,
    )
    frappe.set_user("Administrator")
    # Standalone test incidents (+ their auto RCA/CAPA) not bound to a purged asset.
    for inc in frappe.db.sql_list(
        "SELECT name FROM `tabIncident Report` WHERE description LIKE %s", ("\\_Test%",)
    ):
        with suppress(Exception):
            for dt, fld in (("IMM CAPA Record", "linked_incident"),
                            ("IMM RCA Record", "incident")):
                if frappe.db.has_column(dt, fld):
                    for ch in frappe.db.sql_list(
                        f"SELECT name FROM `tab{dt}` WHERE `{fld}`=%s", (inc,)
                    ):
                        with suppress(Exception):
                            frappe.delete_doc(dt, ch, force=True, ignore_permissions=True)
            frappe.delete_doc("Incident Report", inc, force=True, ignore_permissions=True)
    purge_assets_by_name_prefix("_Test Asset IMM12")
    purge_category_by_name("_TestCatIMM12")
    frappe.db.commit()


def tearDownModule():  # noqa: N802
    _module_cleanup()


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


# ── R16: API-layer RBAC — phải dùng capability THẬT (Corrective Manager/User),
#    KHÔNG dùng role-name set bịa ("IMM Workshop Lead"...). Trước fix: mọi
#    corrective user bị 403 → cả workflow chết. Test gọi qua API wrapper (không
#    phải service) để bắt đúng tầng gate. ─────────────────────────────────────

class TestIncidentApiRbac(unittest.TestCase):
    """R16 regression: API whitelist của IMM-12 phải cho Corrective Manager/User
    thao tác incident (acknowledge/close) theo DocPerm thật, không hardcode role
    name không tồn tại trong fixtures/role.json."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-rbac")
        # Ephemeral users mang role THẬT (khớp fixtures/role.json + persona).
        cls.mgr = cls._ensure_user("_test_corr_mgr@assetcore.test", ["Corrective Manager"])
        cls.usr = cls._ensure_user("_test_corr_usr@assetcore.test", ["Corrective User"])

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        purge_asset(cls.asset.name)
        for u in (cls.mgr, cls.usr):
            try:
                frappe.delete_doc("User", u, force=True, ignore_permissions=True)
            except Exception:
                pass

    @staticmethod
    def _ensure_user(email: str, roles: list[str]) -> str:
        if not frappe.db.exists("User", email):
            doc = frappe.get_doc({
                "doctype": "User", "email": email, "first_name": email.split("@")[0],
                "send_welcome_email": 0, "enabled": 1,
            }).insert(ignore_permissions=True)
        else:
            doc = frappe.get_doc("User", email)
        existing = {r.role for r in doc.get("roles", [])}
        for r in roles:
            if r not in existing:
                doc.append("roles", {"role": r})
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        return email

    def setUp(self):
        frappe.set_user("Administrator")

    def _open_incident(self) -> str:
        out = report_incident(
            asset=self.asset.name, incident_type="Malfunction", severity="Medium",
            description="_Test R16 API RBAC incident description here",
        )
        frappe.db.commit()
        return out["name"]

    def test_corrective_manager_can_acknowledge_via_api(self):
        from assetcore.api.imm12 import acknowledge_incident as api_ack
        ir = self._open_incident()
        frappe.set_user(self.mgr)
        try:
            res = api_ack(ir, notes="_Test API ack by Corrective Manager")
        finally:
            frappe.set_user("Administrator")
        frappe.db.commit()
        self.assertTrue(
            res.get("success"),
            f"Corrective Manager phải acknowledge được qua API, nhận: {res}",
        )
        self.assertEqual(frappe.db.get_value("Incident Report", ir, "status"),
                         "Acknowledged")

    def test_corrective_user_can_acknowledge_via_api(self):
        from assetcore.api.imm12 import acknowledge_incident as api_ack
        ir = self._open_incident()
        frappe.set_user(self.usr)
        try:
            res = api_ack(ir, notes="_Test API ack by Corrective User")
        finally:
            frappe.set_user("Administrator")
        frappe.db.commit()
        self.assertTrue(
            res.get("success"),
            f"Corrective User phải acknowledge được qua API, nhận: {res}",
        )

    def test_corrective_user_cannot_close_via_api(self):
        """Corrective User KHÔNG có submit perm → không được đóng incident.
        RBAC granular: chỉ Manager (submit) mới đóng."""
        from assetcore.api.imm12 import close_incident as api_close
        ir = self._open_incident()
        frappe.set_user(self.usr)
        try:
            res = api_close(ir, verification_notes="_Test should be forbidden")
        finally:
            frappe.set_user("Administrator")
        self.assertFalse(
            res.get("success"),
            "Corrective User KHÔNG được phép đóng incident (thiếu submit perm)",
        )


# ─── SLA breach escalation (BR-12-08/09/10 — TDD-1..6) ──────────────────────────

class TestIncidentSlaEscalation(unittest.TestCase):
    """BR-12-09/10: check_incident_sla_breach phải ESCALATE notification khi quá
    hạn (response/resolution), idempotent qua cờ DB, recipient route qua notify_roles
    SSoT + escalation_l1/l2_user, NĐ98 gate Critical/High thêm QA+Ops Manager.

    Pattern test side-effect THẬT (LL-TEST-18 / R-0 anti-false-green): patch engine
    `notifications._dispatch` để CAPTURE notification thật được bắn (không chỉ assert
    return), patch `get_users_with_role` để kiểm soát resolve role-block. Incident +
    cờ breach là data DB thật (commit), idempotency assert qua chạy 2 lần liên tiếp.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-sla")
        cls._assignee = cls._ensure_user("_test_sla_assignee@assetcore.test", [])
        cls._l1 = cls._ensure_user("_test_sla_l1@assetcore.test", [])
        cls._l2 = cls._ensure_user("_test_sla_l2@assetcore.test", [])
        cls._qa = cls._ensure_user("_test_sla_qa@assetcore.test", ["Compliance Manager"])
        cls._ops = cls._ensure_user("_test_sla_ops@assetcore.test", ["Maintenance Manager"])
        cls._incidents: list[str] = []

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        # Purge incidents tạo trong class (raw SQL audit guard + ORM dependents qua purge_asset).
        for ir in cls._incidents:
            try:
                frappe.delete_doc("Incident Report", ir, force=True,
                                  ignore_permissions=True, delete_permanently=True)
            except Exception:
                pass
        purge_asset(cls.asset.name)
        for u in (cls._assignee, cls._l1, cls._l2, cls._qa, cls._ops):
            try:
                frappe.delete_doc("User", u, force=True, ignore_permissions=True)
            except Exception:
                pass
        frappe.db.commit()

    @staticmethod
    def _ensure_user(email: str, roles: list[str]) -> str:
        if not frappe.db.exists("User", email):
            doc = frappe.get_doc({
                "doctype": "User", "email": email, "first_name": email.split("@")[0],
                "send_welcome_email": 0, "enabled": 1,
            }).insert(ignore_permissions=True)
        else:
            doc = frappe.get_doc("User", email)
        existing = {r.role for r in doc.get("roles", [])}
        for r in roles:
            if r not in existing:
                doc.append("roles", {"role": r})
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        return email

    def setUp(self):
        frappe.set_user("Administrator")

    # ── fixtures ──────────────────────────────────────────────────────────────

    def _make_breached_incident(self, severity: str, *, kind: str,
                                 assigned_to: str | None = None) -> str:
        """Tạo incident với due-time đã quá hạn theo `kind` (response/resolution),
        chưa breach (cờ=0). kind='resolution' → đã acknowledged, resolution quá hạn,
        response còn hạn. kind='response' → chưa acknowledged, response quá hạn,
        resolution còn hạn. Trả về incident name."""
        from frappe.utils import add_to_date, now_datetime
        clinical = "Ảnh hưởng chẩn đoán" if severity == "Critical" else ""
        out = report_incident(
            asset=self.asset.name, incident_type="Malfunction", severity=severity,
            description=f"_Test SLA escalation {kind} {severity}", clinical_impact=clinical,
        )
        name = out["name"]
        self._incidents.append(name)
        now = now_datetime()
        vals: dict = {"response_breached": 0, "resolution_breached": 0}
        if assigned_to:
            vals["assigned_to"] = assigned_to
        if kind == "resolution":
            # Đã tiếp nhận (response không breach) + đang xử lý + resolution quá hạn.
            vals["status"] = "In Progress"
            vals["acknowledged_at"] = add_to_date(now, hours=-5)
            vals["response_due_at"] = add_to_date(now, hours=-4)  # đã ack trước hạn → no resp breach
            vals["resolution_due_at"] = add_to_date(now, hours=-3)
        else:  # response
            vals["status"] = "Open"
            vals["acknowledged_at"] = None
            vals["response_due_at"] = add_to_date(now, hours=-2)
            vals["resolution_due_at"] = add_to_date(now, hours=+48)
        frappe.db.set_value("Incident Report", name, vals, update_modified=False)
        frappe.db.commit()
        return name

    def _run_scan_capture(self):
        """Chạy check_incident_sla_breach với _dispatch + get_users_with_role patched.
        Trả về (result_dict, captured) — captured = list (recipients, subject, message)."""
        import assetcore.services.notifications as notif_svc
        import assetcore.services.imm12 as svc12
        from unittest.mock import patch

        captured: list[tuple] = []

        def fake_dispatch(users, subject, message, doc):
            captured.append((list(users), subject, message))

        role_map = {
            "Compliance Manager": [self._qa],
            "Maintenance Manager": [self._ops],
        }

        def fake_roles(role):
            return list(role_map.get(role, []))

        with patch.object(notif_svc, "_dispatch", side_effect=fake_dispatch), \
             patch("frappe.utils.user.get_users_with_role", side_effect=fake_roles):
            result = svc12.check_incident_sla_breach()
        return result, captured

    # ── TDD-1: resolution breach High → escalate đúng recipient + audit ─────────

    def test_tdd1_resolution_breach_high_escalates_once(self):
        ir = self._make_breached_incident("High", kind="resolution",
                                          assigned_to=self._assignee)
        result, captured = self._run_scan_capture()
        # (a) cờ resolution_breached set 1.
        self.assertEqual(
            frappe.db.get_value("Incident Report", ir, "resolution_breached"), 1)
        # (b) đúng 1 notification cho incident này (loại 'xử lý'), recipient gồm
        #     assigned_to + QA (High gate). escalation_l*_user policy = NULL → bỏ qua.
        mine = [c for c in captured if ir in c[1] or ir in c[2]]
        self.assertEqual(len(mine), 1, f"phải bắn ĐÚNG 1 notification, nhận {len(mine)}")
        recipients, subject, message = mine[0]
        self.assertIn(self._assignee, recipients, "assigned_to phải nhận")
        self.assertIn(self._qa, recipients, "High → QA Officer (NĐ98 gate) phải nhận")
        self.assertIn("xử lý", subject.lower() + " " + subject)
        self.assertNotIn("breached", (subject + message).lower())
        # (c) audit entry 'escalated'.
        self.assertTrue(
            frappe.db.exists("IMM Audit Trail", {
                "ref_name": ir, "change_summary": ("like", "%escalated%"),
            }),
            "phải ghi audit entry 'SLA breach escalated'",
        )

    # ── TDD-2: idempotent — chạy lần 2 không bắn thêm ──────────────────────────

    def test_tdd2_idempotent_no_reescalate(self):
        ir = self._make_breached_incident("High", kind="resolution",
                                          assigned_to=self._assignee)
        _r1, cap1 = self._run_scan_capture()
        mine1 = [c for c in cap1 if ir in c[1] or ir in c[2]]
        self.assertEqual(len(mine1), 1)
        # Lần 2 ngay sau — cờ đã =1 → KHÔNG bắn lại.
        _r2, cap2 = self._run_scan_capture()
        mine2 = [c for c in cap2 if ir in c[1] or ir in c[2]]
        self.assertEqual(len(mine2), 0, "sweep lần 2: cờ đã =1 → không bắn lại (anti-spam)")
        # Cờ vẫn =1, không thêm audit escalated trùng.
        self.assertEqual(
            frappe.db.get_value("Incident Report", ir, "resolution_breached"), 1)
        n_esc = frappe.db.count("IMM Audit Trail", {
            "ref_name": ir, "change_summary": ("like", "%escalated%")})
        self.assertEqual(n_esc, 1, "chỉ 1 audit escalated dù quét 2 lần")

    # ── TDD-3: response breach riêng — chỉ loại 'tiếp nhận' ────────────────────

    def test_tdd3_response_breach_only_acknowledge_kind(self):
        ir = self._make_breached_incident("High", kind="response",
                                          assigned_to=self._assignee)
        result, captured = self._run_scan_capture()
        self.assertEqual(
            frappe.db.get_value("Incident Report", ir, "response_breached"), 1)
        self.assertEqual(
            frappe.db.get_value("Incident Report", ir, "resolution_breached"), 0,
            "resolution chưa quá hạn → không breach",
        )
        mine = [c for c in captured if ir in c[1] or ir in c[2]]
        self.assertEqual(len(mine), 1, "chỉ 1 notification loại response")
        _r, subject, message = mine[0]
        self.assertIn("tiếp nhận", subject.lower(), "phải là loại 'tiếp nhận'")
        self.assertNotIn("xử lý", subject.lower(),
                         "KHÔNG bắn loại 'xử lý' khi chỉ response breach")

    # ── TDD-4: NĐ98 gate — Critical breach, policy không set escalation user ───

    def test_tdd4_nd98_gate_critical_adds_qa_and_ops(self):
        # Critical → severity gate; policy P1-Critical escalation_l*_user = NULL.
        ir = self._make_breached_incident("Critical", kind="resolution",
                                          assigned_to=self._assignee)
        result, captured = self._run_scan_capture()
        mine = [c for c in captured if ir in c[1] or ir in c[2]]
        self.assertEqual(len(mine), 1, "Critical breach phải bắn (không rỗng)")
        recipients = mine[0][0]
        self.assertIn(self._qa, recipients, "Critical → QA Officer (gate NĐ98)")
        self.assertIn(self._ops, recipients, "Critical → Ops Manager (gate NĐ98)")

    # ── TDD-5: robustness — không resolve được recipient nào ───────────────────

    def test_tdd5_no_recipient_sets_flag_no_empty_dispatch(self):
        # Low severity (không gate NĐ98), không assigned_to, không reported_by user
        # thật trong role-map → recipient rỗng. KHÔNG raise, KHÔNG bắn rỗng.
        ir = self._make_breached_incident("Low", kind="resolution", assigned_to=None)
        # Xoá reported_by để không resolve fallback ra user.
        frappe.db.set_value("Incident Report", ir, "reported_by", "", update_modified=False)
        frappe.db.commit()
        try:
            result, captured = self._run_scan_capture()
        except Exception as e:  # noqa: BLE001
            self.fail(f"recipient rỗng KHÔNG được raise: {e}")
        # Cờ vẫn set (entry phát hiện như cũ).
        self.assertEqual(
            frappe.db.get_value("Incident Report", ir, "resolution_breached"), 1)
        # KHÔNG bắn notification rỗng cho incident này.
        mine = [c for c in captured if ir in c[1] or ir in c[2]]
        self.assertEqual(mine, [], "recipient rỗng → KHÔNG bắn notification rỗng")
        # Entry phát hiện (detection) vẫn ghi.
        self.assertTrue(
            frappe.db.exists("IMM Audit Trail", {
                "ref_name": ir, "change_summary": ("like", "%phát hiện%"),
            }),
            "entry phát hiện SLA breach vẫn phải ghi như cũ",
        )

    # ── TDD-6: no-regression IMM-09 run_sla_breach_scan ────────────────────────

    def test_tdd6_imm09_run_sla_breach_scan_unchanged(self):
        """Chạy run_sla_breach_scan() (Asset Repair) với list rỗng → không lỗi,
        không bắn notification (hành vi IMM-09 không đổi bởi thay đổi IMM-12)."""
        import assetcore.services.notifications as notif_svc
        from unittest.mock import patch

        emitted: list = []
        with patch("assetcore.repositories.repair_repo.RepairRepo.list",
                   return_value=([], 0)), \
             patch.object(notif_svc, "_emit_sla_notification",
                          side_effect=lambda *a, **k: emitted.append(a)):
            notif_svc.run_sla_breach_scan()
        self.assertEqual(emitted, [], "IMM-09 scan list rỗng → không emit")


# ─── get_incident_detail SLA-breach LIVE (INV-SLA-5/6) ─────────────────────────


class TestIncidentDetailSlaLive(unittest.TestCase):
    """BR-12-09 / INV-SLA-5/6: get_incident_detail PHẢI surface is_response_breached/
    is_resolution_breached (0|1, derived LIVE — CÙNG SoT _enrich_sla_breach với
    list_incidents/dashboard) để badge màn Chi tiết == badge danh sách/dashboard TẠI
    CÙNG thời điểm (KHÔNG stale-divergence). Terminal (Closed) chỉ breach qua nhánh
    cờ=1 (INV-SLA-6) — KHÔNG live-overdue dù due đã quá hạn.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-detail-sla")
        cls._incidents: list[str] = []

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for ir in cls._incidents:
            try:
                frappe.delete_doc("Incident Report", ir, force=True,
                                  ignore_permissions=True, delete_permanently=True)
            except Exception:
                pass
        purge_asset(cls.asset.name)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")

    def _make_incident(self, *, status: str, response_due_h: int,
                       resolution_due_h: int, acknowledged_h: int | None,
                       response_flag: int = 0, resolution_flag: int = 0) -> str:
        """Tạo incident + set status/due-time/cờ thô THẲNG DB (bypass workflow controller).
        *_due_h < 0 = quá hạn; > 0 = còn hạn. acknowledged_h None = chưa tiếp nhận."""
        from frappe.utils import add_to_date, now_datetime
        out = report_incident(
            asset=self.asset.name, incident_type="Malfunction", severity="High",
            description="_Test detail SLA live",
        )
        name = out["name"]
        self._incidents.append(name)
        now = now_datetime()
        vals = {
            "status": status,
            "response_breached": response_flag,
            "resolution_breached": resolution_flag,
            "response_due_at": add_to_date(now, hours=response_due_h),
            "resolution_due_at": add_to_date(now, hours=resolution_due_h),
            "acknowledged_at": (add_to_date(now, hours=acknowledged_h)
                                if acknowledged_h is not None else None),
        }
        frappe.db.set_value("Incident Report", name, vals, update_modified=False)
        frappe.db.commit()
        return name

    def test_get_incident_detail_sla_live(self):
        """Open + response_due_at quá khứ + chưa tiếp nhận → is_response_breached==1;
        resolution_due_at tương lai → is_resolution_breached==0 (derived LIVE, cờ thô=0)."""
        from assetcore.services.imm12 import get_incident_detail
        name = self._make_incident(
            status="Open", response_due_h=-2, resolution_due_h=+48, acknowledged_h=None,
        )
        detail = get_incident_detail(name)
        self.assertEqual(detail.get("is_response_breached"), 1,
                         "Open + response quá hạn + chưa ack → is_response_breached=1")
        self.assertEqual(detail.get("is_resolution_breached"), 0,
                         "resolution còn hạn → is_resolution_breached=0")
        # Derived KHÔNG ghi đè cờ thô lịch sử — badge đọc derived, không cờ thô stale.
        self.assertEqual(
            frappe.db.get_value("Incident Report", name, "response_breached"), 0)

    def test_get_incident_detail_sla_terminal(self):
        """INV-SLA-6: Closed (terminal) + cờ thô=0 dù due quá hạn → is_*_breached==0
        (terminal chỉ breach qua nhánh cờ=1, KHÔNG live-overdue)."""
        from assetcore.services.imm12 import get_incident_detail
        name = self._make_incident(
            status="Closed", response_due_h=-4, resolution_due_h=-3, acknowledged_h=None,
        )
        detail = get_incident_detail(name)
        self.assertEqual(detail.get("is_response_breached"), 0,
                         "terminal Closed cờ=0 → is_response_breached=0 (INV-SLA-6)")
        self.assertEqual(detail.get("is_resolution_breached"), 0,
                         "terminal Closed cờ=0 → is_resolution_breached=0 (INV-SLA-6)")

    def test_detail_list_sla_parity(self):
        """Cùng 1 incident: is_*_breached từ get_incident_detail == từ list_incidents
        (1 SoT _enrich_sla_breach) → badge Chi tiết == badge danh sách (INV-SLA-5)."""
        from assetcore.services.imm12 import get_incident_detail, list_incidents
        name = self._make_incident(
            status="Open", response_due_h=-2, resolution_due_h=+48, acknowledged_h=None,
        )
        detail = get_incident_detail(name)
        res = list_incidents(asset=self.asset.name, page_size=100)
        row = next(r for r in res["items"] if r["name"] == name)
        self.assertEqual(detail.get("is_response_breached"),
                         row.get("is_response_breached"),
                         "is_response_breached: detail == list (cùng SoT)")
        self.assertEqual(detail.get("is_resolution_breached"),
                         row.get("is_resolution_breached"),
                         "is_resolution_breached: detail == list (cùng SoT)")
        # Sanity: parity đúng theo nhánh live (response breach, resolution còn hạn).
        self.assertEqual(detail.get("is_response_breached"), 1)
        self.assertEqual(detail.get("is_resolution_breached"), 0)

    def test_get_incident_detail_resolution_live_overdue(self):
        """AC-S6 (1): Open + resolution_due_at quá khứ (cờ thô=0) → is_resolution_breached==1
        (derived LIVE — nhánh open ∧ quá-hạn, KHÔNG dựa cờ thô)."""
        from assetcore.services.imm12 import get_incident_detail
        name = self._make_incident(
            status="Open", response_due_h=+48, resolution_due_h=-3, acknowledged_h=None,
        )
        detail = get_incident_detail(name)
        self.assertEqual(detail.get("is_resolution_breached"), 1,
                         "Open + resolution quá hạn → is_resolution_breached=1")
        # Derived KHÔNG ghi đè cờ thô lịch sử (badge đọc derived, cờ thô vẫn 0).
        self.assertEqual(
            frappe.db.get_value("Incident Report", name, "resolution_breached"), 0)

    def test_get_incident_detail_terminal_flag_breached(self):
        """AC-S6 (4)/INV-SLA-6: Closed (terminal) + cờ thô resolution_breached=1 dù due
        còn hạn → is_resolution_breached==1 (nhánh cờ=1, KHÔNG cần live-overdue)."""
        from assetcore.services.imm12 import get_incident_detail
        name = self._make_incident(
            status="Closed", response_due_h=+48, resolution_due_h=+48,
            acknowledged_h=None, resolution_flag=1,
        )
        detail = get_incident_detail(name)
        self.assertEqual(detail.get("is_resolution_breached"), 1,
                         "terminal Closed + cờ thô=1 → is_resolution_breached=1 (INV-SLA-6)")
        # response cờ thô=0 + terminal → is_response_breached=0 (không live-overdue).
        self.assertEqual(detail.get("is_response_breached"), 0,
                         "terminal + response cờ=0 → is_response_breached=0")


# ─── CR-40: get_incident_detail user/lifecycle enrich (U1/U7 UI-FIX-05) ─────────


class TestGetIncidentDetailEnrich(unittest.TestCase):
    """CR-40: get_incident_detail bồi 3 field enrich rẻ trên màn Chi tiết sự cố:
    - reporter_name = User.full_name của reported_by (fallback raw id khi thiếu
      full_name) ⇒ KHÔNG rò email thô khi full_name tồn tại (U7 / UI-FIX-05).
    - assigned_to_name = full_name của assigned_to (fallback raw id).
    - asset_lifecycle_status = AC Asset.lifecycle_status của doc.asset (song song
      asset_name) ⇒ KTV rút máy khỏi vận hành THẤY trạng thái thiết bị (U1 🔴,
      BR-12-04 acknowledge High/Critical → Out of Service).
    Cả 3 additive/optional (REUSE khuôn user-enrich list_incidents _enrich_asset_names
    :444-461 — 1 get_all User, KHÔNG re-implement predicate). Migrate-free.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-enrich")
        cls._incidents: list[str] = []
        cls._users: list[str] = []
        cls.reporter = cls._make_user("_test_imm12_reporter", "Nguyễn Văn A")
        cls.handler = cls._make_user("_test_imm12_handler", "Trần Thị B")
        cls.nameless = cls._make_user("_test_imm12_nameless", "")

    @classmethod
    def _make_user(cls, local: str, full_name: str) -> str:
        email = f"{local}_{_RUN_TAG}@assetcore.test"
        if not frappe.db.exists("User", email):
            frappe.get_doc({
                "doctype": "User", "email": email,
                "first_name": full_name or "x",
                "send_welcome_email": 0, "enabled": 1,
            }).insert(ignore_permissions=True)
            cls._users.append(email)
        # Ép full_name đúng kịch bản (rỗng = fallback raw id) — full_name auto-set từ
        # first_name nên phải ghi đè trực tiếp DB.
        frappe.db.set_value("User", email, "full_name", full_name, update_modified=False)
        frappe.db.commit()
        return email

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for ir in cls._incidents:
            try:
                frappe.delete_doc("Incident Report", ir, force=True,
                                  ignore_permissions=True, delete_permanently=True)
            except Exception:
                pass
        for u in cls._users:
            try:
                frappe.delete_doc("User", u, force=True, ignore_permissions=True)
            except Exception:
                pass
        purge_asset(cls.asset.name)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")

    def _make_incident(self, *, has_asset: bool = True, reported_by: str = "",
                       assigned_to: str = "", lifecycle_status: str | None = None) -> str:
        """Tạo incident rồi set reported_by/assigned_to/asset THẲNG DB (bypass workflow)."""
        out = report_incident(
            asset=self.asset.name, incident_type="Malfunction", severity="High",
            description="_Test detail enrich",
        )
        name = out["name"]
        self._incidents.append(name)
        vals: dict = {
            "reported_by": reported_by or None,
            "assigned_to": assigned_to or None,
            "asset": self.asset.name if has_asset else "",
        }
        frappe.db.set_value("Incident Report", name, vals, update_modified=False)
        if lifecycle_status is not None:
            frappe.db.set_value("AC Asset", self.asset.name, "lifecycle_status",
                                lifecycle_status, update_modified=False)
        frappe.db.commit()
        return name

    def test_reporter_name_uses_full_name_not_email(self):
        """reported_by = user có full_name 'Nguyễn Văn A' → reporter_name == full_name,
        KHÔNG == email thô (U7 / UI-FIX-05: chấm dứt rò email trên màn Chi tiết)."""
        name = self._make_incident(reported_by=self.reporter)
        detail = get_incident_detail(name)
        self.assertEqual(detail.get("reporter_name"), "Nguyễn Văn A",
                         "reporter_name PHẢI = User.full_name")
        self.assertNotEqual(detail.get("reporter_name"), self.reporter,
                            "reporter_name KHÔNG được rò email thô khi full_name tồn tại")

    def test_assigned_to_name_uses_full_name(self):
        """assigned_to = user có full_name → assigned_to_name == full_name."""
        name = self._make_incident(reported_by=self.reporter, assigned_to=self.handler)
        detail = get_incident_detail(name)
        self.assertEqual(detail.get("assigned_to_name"), "Trần Thị B",
                         "assigned_to_name PHẢI = User.full_name của assigned_to")

    def test_user_without_full_name_falls_back_to_raw_id(self):
        """User KHÔNG full_name → fallback == raw id (email), KHÔNG KeyError, KHÔNG rò rỗng."""
        name = self._make_incident(reported_by=self.nameless, assigned_to=self.nameless)
        detail = get_incident_detail(name)
        self.assertEqual(detail.get("reporter_name"), self.nameless,
                         "reporter_name thiếu full_name → fallback raw id")
        self.assertEqual(detail.get("assigned_to_name"), self.nameless,
                         "assigned_to_name thiếu full_name → fallback raw id")

    def test_asset_lifecycle_status_out_of_service(self):
        """asset lifecycle_status = 'Out of Service' (BR-12-04 sau acknowledge High/
        Critical) → detail['asset_lifecycle_status'] == 'Out of Service' (đồng bộ máy)."""
        name = self._make_incident(lifecycle_status="Out of Service")
        detail = get_incident_detail(name)
        self.assertEqual(detail.get("asset_lifecycle_status"), "Out of Service",
                         "asset_lifecycle_status PHẢI khớp AC Asset.lifecycle_status LIVE")

    def test_no_asset_no_assigned_regression(self):
        """Incident KHÔNG asset + KHÔNG assigned_to → asset_lifecycle_status ∈ {'', None},
        key assigned_to_name VẮNG, endpoint KHÔNG raise; keys cũ BẤT BIẾN."""
        name = self._make_incident(has_asset=False, reported_by=self.reporter)
        detail = get_incident_detail(name)  # KHÔNG raise
        self.assertIn(detail.get("asset_lifecycle_status"), ("", None),
                      "KHÔNG gắn asset → asset_lifecycle_status '' hoặc None")
        self.assertNotIn("assigned_to_name", detail,
                         "assigned_to VẮNG → key assigned_to_name KHÔNG có mặt (additive)")
        # reporter_name vẫn có mặt (reported_by set).
        self.assertEqual(detail.get("reporter_name"), "Nguyễn Văn A")
        # Keys cũ BẤT BIẾN (contract invariant — additive không phá consumer cũ).
        for k in ("is_response_breached", "is_resolution_breached",
                  "available_actions", "scene_photos", "allowed_transitions"):
            self.assertIn(k, detail, f"key cũ '{k}' PHẢI BẤT BIẾN (additive)")


# ─── SoT "incident đang mở" — INCIDENT_OPEN_STATES + open_incident_filter ───────


class TestIncidentOpenStatesSoT(unittest.TestCase):
    """SoT duy nhất cho 'incident đang mở' (services/imm12.py).

    INCIDENT_OPEN_STATES = (Open, Acknowledged, In Progress, RCA Required).
    Cancelled/Resolved/Closed là TERMINAL → bị loại khỏi tập 'mở'. Dashboard KPI,
    severity-donut, persona, rca_incomplete + SLA engine + drill-down PHẢI dùng
    chung tập này (count == drill, không drift, không đếm Cancelled là mở).
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-sot")
        cls._incidents: list[str] = []

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for ir in cls._incidents:
            try:
                frappe.delete_doc("Incident Report", ir, force=True,
                                  ignore_permissions=True, delete_permanently=True)
            except Exception:
                pass
        purge_asset(cls.asset.name)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")

    def _make_incident(self, severity: str, status: str, *, tag: str = "") -> str:
        """Tạo incident rồi force-set status (bypass workflow gate cho test).

        `tag` ghi vào fault_code để scope count theo từng test method (asset dùng
        chung cls.asset, các method tích luỹ → đếm tuyệt đối phải lọc theo tag).
        """
        clinical = "Ảnh hưởng chẩn đoán" if severity == "Critical" else ""
        out = report_incident(
            asset=self.asset.name, incident_type="Malfunction", severity=severity,
            description=f"_Test SoT {severity} {status}", clinical_impact=clinical,
            fault_code=tag or None,
        )
        name = out["name"]
        self._incidents.append(name)
        if status != "Open":
            frappe.db.set_value("Incident Report", name, "status", status,
                                update_modified=False)
            frappe.db.commit()
        return name

    # ── TDD: SoT định nghĩa + helper loại Cancelled ────────────────────────────

    def test_incident_open_states_constant_shape(self):
        """SoT tuple = chính xác 4 positive-state, KHÔNG chứa terminal."""
        from assetcore.services.imm12 import INCIDENT_OPEN_STATES
        self.assertEqual(
            set(INCIDENT_OPEN_STATES),
            {"Open", "Acknowledged", "In Progress", "RCA Required"},
        )
        for terminal in ("Cancelled", "Resolved", "Closed"):
            self.assertNotIn(terminal, INCIDENT_OPEN_STATES)

    def test_open_incident_filter_builds_in_clause(self):
        """open_incident_filter() trả {status:[in, OPEN_STATES]}; extra merge."""
        from assetcore.services.imm12 import (
            INCIDENT_OPEN_STATES, open_incident_filter,
        )
        f = open_incident_filter()
        self.assertEqual(f.get("status"), ["in", list(INCIDENT_OPEN_STATES)])
        f2 = open_incident_filter({"severity": "Critical"})
        self.assertEqual(f2.get("severity"), "Critical")
        self.assertEqual(f2.get("status"), ["in", list(INCIDENT_OPEN_STATES)])

    def test_incident_open_states_exclude_cancelled(self):
        """1 Open + 1 Cancelled cùng severity → open_incident_filter() đếm == 1."""
        from assetcore.services.imm12 import open_incident_filter
        tag = "SOT-EXC"
        self._make_incident("Critical", "Open", tag=tag)
        self._make_incident("Critical", "Cancelled", tag=tag)
        cnt = frappe.db.count(
            "Incident Report",
            filters=open_incident_filter({"asset": self.asset.name,
                                          "severity": "Critical", "fault_code": tag}),
        )
        self.assertEqual(cnt, 1, "Cancelled là terminal → KHÔNG tính là mở")

    # ── TDD: SLA engine dùng chính SoT (không nhặt Cancelled) ──────────────────

    def test_sla_engine_uses_open_sot(self):
        """check_incident_sla_breach KHÔNG nhặt incident Cancelled làm candidate.

        Patch frappe.get_all để CAPTURE filter mà engine dùng, assert status
        in-clause khớp INCIDENT_OPEN_STATES (cùng tập, không drift). Cancelled
        nằm ngoài → không bao giờ là candidate."""
        from unittest.mock import patch
        import assetcore.services.imm12 as svc12

        captured: dict = {}
        real_get_all = frappe.get_all

        def spy_get_all(doctype, *args, **kwargs):
            if doctype == "Incident Report" and "status" in (kwargs.get("filters") or {}):
                captured["filters"] = kwargs["filters"]
            return real_get_all(doctype, *args, **kwargs)

        with patch.object(frappe, "get_all", side_effect=spy_get_all):
            svc12.check_incident_sla_breach()

        self.assertIn("filters", captured, "engine phải query Incident theo status")
        status_clause = captured["filters"].get("status")
        self.assertEqual(status_clause[0], "in")
        self.assertEqual(set(status_clause[1]), set(svc12.INCIDENT_OPEN_STATES))
        self.assertNotIn("Cancelled", status_clause[1])

    # ── TDD: list_incidents open param ─────────────────────────────────────────

    def test_list_incidents_open_param(self):
        """list_incidents(open=1) → đúng tập open-states (loại Cancelled/Resolved).
        open + severity → giao open ∩ severity. status đơn lẻ override open."""
        from assetcore.services.imm12 import list_incidents
        self._make_incident("Critical", "Open")
        self._make_incident("Critical", "In Progress")
        self._make_incident("Critical", "Cancelled")
        self._make_incident("Critical", "Resolved")
        self._make_incident("High", "Open")

        # open=1 (toàn asset): chỉ open-states (loại Cancelled/Resolved).
        res_open = list_incidents(open=1, asset=self.asset.name, page_size=100)
        statuses = {r["status"] for r in res_open["items"]}
        self.assertTrue(statuses.issubset(
            {"Open", "Acknowledged", "In Progress", "RCA Required"}))
        self.assertNotIn("Cancelled", statuses)
        self.assertNotIn("Resolved", statuses)

        # open=1 + severity=Critical → chỉ Critical open-states (KHÔNG Cancelled/Resolved).
        res_crit = list_incidents(open=1, severity="Critical",
                                  asset=self.asset.name, page_size=100)
        crit_statuses = {r["status"] for r in res_crit["items"]}
        self.assertTrue(crit_statuses.issubset(
            {"Open", "Acknowledged", "In Progress", "RCA Required"}))
        self.assertTrue(all(r["severity"] == "Critical" for r in res_crit["items"]))
        # Invariant count==drill: total == count qua open_incident_filter cùng scope.
        from assetcore.services.imm12 import open_incident_filter
        expected = frappe.db.count("Incident Report", filters=open_incident_filter(
            {"asset": self.asset.name, "severity": "Critical"}))
        self.assertEqual(res_crit["pagination"]["total"], expected)

        # status đơn lẻ override open (mutually-exclusive, ưu tiên status).
        res_cancel = list_incidents(open=1, status="Cancelled",
                                    asset=self.asset.name, page_size=100)
        self.assertTrue(all(r["status"] == "Cancelled" for r in res_cancel["items"]))
        self.assertGreaterEqual(res_cancel["pagination"]["total"], 1)
        self.assertEqual(
            res_cancel["pagination"]["total"],
            frappe.db.count("Incident Report",
                            filters={"asset": self.asset.name, "status": "Cancelled"}),
            "status đơn lẻ phải bỏ qua open-set, đếm đúng tập Cancelled",
        )


# ─── A2 closure — param `mine` self-scope reported_by (tab "Báo hỏng của tôi") ───


class TestIncidentMineScope(unittest.TestCase):
    """A2 known-gap closure (ADR-IMM12-05 / ADR-MOBILE-015) — param `mine` self-scope
    `reported_by` cho tab "Báo hỏng của tôi" (MyWorkOrdersView › MVP-5c).

    Semantic: KTV là người BÁO ⇒ mine = `reported_by == frappe.session.user` (KHÔNG
    assigned_to). mine=1 → CHỈ incident của chính session.user. mine=0/absent → hành
    vi cũ UNCHANGED (blast-radius fence — incident reporter khác VẪN hiện). mine AND
    với status/severity/asset/open KỂ CẢ nhánh status return-sớm. pagination.total ==
    len(items) khi mine=1 (count==rows — cùng filters dict).
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-mine")
        # KTV thật (Corrective User → corrective.read) — 2 reporter PHÂN BIỆT.
        cls.user_a = cls._ensure_user("_test_mine_a@assetcore.test", ["Corrective User"])
        cls.user_b = cls._ensure_user("_test_mine_b@assetcore.test", ["Corrective User"])
        cls._incidents: list[str] = []

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for ir in cls._incidents:
            try:
                frappe.delete_doc("Incident Report", ir, force=True,
                                  ignore_permissions=True, delete_permanently=True)
            except Exception:
                pass
        purge_asset(cls.asset.name)
        for u in (cls.user_a, cls.user_b):
            try:
                frappe.delete_doc("User", u, force=True, ignore_permissions=True)
            except Exception:
                pass
        frappe.db.commit()

    @staticmethod
    def _ensure_user(email: str, roles: list[str]) -> str:
        if not frappe.db.exists("User", email):
            doc = frappe.get_doc({
                "doctype": "User", "email": email, "first_name": email.split("@")[0],
                "send_welcome_email": 0, "enabled": 1,
            }).insert(ignore_permissions=True)
        else:
            doc = frappe.get_doc("User", email)
        existing = {r.role for r in doc.get("roles", [])}
        for r in roles:
            if r not in existing:
                doc.append("roles", {"role": r})
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        return email

    def setUp(self):
        frappe.set_user("Administrator")

    def _make_incident(self, reporter: str, *, severity: str = "Medium",
                       status: str = "Open") -> str:
        """Tạo incident với reported_by=reporter (Medium → KHÔNG sinh RCA chain)."""
        out = report_incident(
            asset=self.asset.name, incident_type="Malfunction", severity=severity,
            description=f"_Test mine-scope {reporter} {status}",
            reported_by=reporter,
        )
        name = out["name"]
        self._incidents.append(name)
        if status != "Open":
            frappe.db.set_value("Incident Report", name, "status", status,
                                update_modified=False)
        frappe.db.commit()
        return name

    @staticmethod
    def _names(res: dict) -> set:
        return {r["name"] for r in res["items"]}

    # ── TDD-1: mine=1 chỉ trả incident reported_by==session.user ────────────────
    def test_list_incidents_mine_filters_reported_by(self):
        from assetcore.services.imm12 import list_incidents
        ir_a = self._make_incident(self.user_a)
        ir_b = self._make_incident(self.user_b)
        frappe.set_user(self.user_a)
        try:
            res = list_incidents(mine=1, asset=self.asset.name, page_size=100)
        finally:
            frappe.set_user("Administrator")
        names = self._names(res)
        self.assertIn(ir_a, names, "mine=1 phải trả incident của chính userA")
        self.assertNotIn(ir_b, names, "mine=1 KHÔNG được leak incident của userB")
        self.assertTrue(
            all(r["reported_by"] == self.user_a for r in res["items"]),
            "mọi row mine=1 phải reported_by==userA",
        )

    # ── TDD-2: mine=0/absent → hành vi cũ UNCHANGED (blast-radius fence) ─────────
    def test_list_incidents_mine_zero_unchanged(self):
        from assetcore.services.imm12 import list_incidents
        ir_a = self._make_incident(self.user_a)
        ir_b = self._make_incident(self.user_b)
        frappe.set_user(self.user_a)
        try:
            res_zero = list_incidents(mine=0, asset=self.asset.name, page_size=100)
            res_absent = list_incidents(asset=self.asset.name, page_size=100)
        finally:
            frappe.set_user("Administrator")
        for label, res in (("mine=0", res_zero), ("absent", res_absent)):
            names = self._names(res)
            self.assertIn(ir_a, names, f"{label}: incident userA phải hiện")
            self.assertIn(
                ir_b, names,
                f"{label}: incident userB VẪN hiện (fence — reported_by KHÔNG áp ngầm)",
            )

    # ── TDD-3: mine AND open (open_incident_filter + reported_by cùng AND) ───────
    def test_list_incidents_mine_combines_with_open(self):
        from assetcore.services.imm12 import list_incidents
        ir_a_open = self._make_incident(self.user_a, status="Open")
        ir_a_closed = self._make_incident(self.user_a, status="Closed")
        ir_b_open = self._make_incident(self.user_b, status="Open")
        frappe.set_user(self.user_a)
        try:
            res = list_incidents(mine=1, open=1, asset=self.asset.name, page_size=100)
        finally:
            frappe.set_user("Administrator")
        names = self._names(res)
        self.assertIn(ir_a_open, names, "mine=1&open=1 → userA-Open phải hiện")
        self.assertNotIn(ir_a_closed, names,
                         "open=1 loại Closed (terminal) dù cùng reporter")
        self.assertNotIn(ir_b_open, names,
                         "mine=1 loại incident reporter khác dù đang mở")

    # ── TDD-4: mine AND status (nhánh status return-sớm vẫn mang reported_by) ────
    def test_list_incidents_mine_combines_with_status(self):
        from assetcore.services.imm12 import list_incidents
        ir_a_closed = self._make_incident(self.user_a, status="Closed")
        ir_b_closed = self._make_incident(self.user_b, status="Closed")
        ir_a_open = self._make_incident(self.user_a, status="Open")
        frappe.set_user(self.user_a)
        try:
            res = list_incidents(mine=1, status="Closed",
                                 asset=self.asset.name, page_size=100)
        finally:
            frappe.set_user("Administrator")
        names = self._names(res)
        self.assertIn(ir_a_closed, names, "mine=1&status=Closed → userA-Closed phải hiện")
        self.assertNotIn(
            ir_b_closed, names,
            "status branch return-sớm VẪN áp reported_by → loại userB (seed TRƯỚC nhánh)",
        )
        self.assertNotIn(ir_a_open, names, "status=Closed loại userA-Open")
        self.assertTrue(all(r["status"] == "Closed" for r in res["items"]))

    # ── TDD-5: count==rows — pagination.total == len(items) khi mine=1 ──────────
    def test_list_incidents_mine_total_matches_items(self):
        from assetcore.services.imm12 import list_incidents
        self._make_incident(self.user_a, status="Open")
        self._make_incident(self.user_a, status="Closed")
        self._make_incident(self.user_b, status="Open")
        frappe.set_user(self.user_a)
        try:
            res = list_incidents(mine=1, asset=self.asset.name, page_size=100)
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(
            res["pagination"]["total"], len(res["items"]),
            "pagination.total phải == len(items) khi mine=1 (count dùng CÙNG filters dict)",
        )
        self.assertTrue(all(r["reported_by"] == self.user_a for r in res["items"]))

    # ── TDD-6: Guest → 401 in-handler (guard api/imm12.py:212 UNCHANGED) ────────
    def test_list_incidents_guest_401_unchanged(self):
        from assetcore.api.imm12 import list_incidents as api_list
        frappe.set_user("Guest")
        try:
            res = api_list(mine=1)
        finally:
            frappe.set_user("Administrator")
        self.assertFalse(res.get("success"), "Guest gọi list_incidents(mine=1) phải lỗi")
        self.assertEqual(res.get("http_status"), 401,
                         "Guest → http_status 401 UNCHANGED (guard giữ)")

    # ── TDD-7 (API): KTV corrective.read mine=1 → 200, KHÔNG leak reporter khác ──
    def test_list_incidents_api_ktv_mine_no_leak(self):
        from assetcore.api.imm12 import list_incidents as api_list
        ir_a = self._make_incident(self.user_a)
        ir_b = self._make_incident(self.user_b)
        frappe.set_user(self.user_a)
        try:
            res = api_list(mine=1, asset=self.asset.name, page_size=100)
        finally:
            frappe.set_user("Administrator")
        self.assertTrue(res.get("success"), f"KTV corrective.read mine=1 phải 200, nhận: {res}")
        names = {r["name"] for r in res["data"]["items"]}
        self.assertIn(ir_a, names)
        self.assertNotIn(ir_b, names,
                         "KTV mine=1 KHÔNG leak incident của reporter khác")


# ─── Dashboard "đang mở" SoT — open_total + active_incidents (count == drill) ────


class TestIncidentDashboardOpenTotal(unittest.TestCase):
    """get_incident_stats().open_total + get_dashboard().active_incidents dùng CHUNG
    open_incident_filter() (SoT) → card 'đang mở' đếm MỌI open-state {Open, Acknowledged,
    In Progress, RCA Required}, KHÔNG chỉ status=='Open'. Invariant: card count ==
    số dòng drill list (open_total == count(open_incident_filter())).
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-dashtot")
        cls._incidents: list[str] = []
        # Fixture phủ MỌI open-state + terminal: assert open_total = đúng 4 mở,
        # KHÁC stats['open'] (chỉ Open = 2). RCA Required + Acknowledged phải vào.
        cls._open_open = cls._mk("Open")
        cls._open_open2 = cls._mk("Open")
        cls._ack = cls._mk("Acknowledged")
        cls._inprog = cls._mk("In Progress")
        cls._rca_req = cls._mk("RCA Required")
        cls._closed = cls._mk("Closed")
        cls._cancelled = cls._mk("Cancelled")
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for ir in cls._incidents:
            try:
                frappe.delete_doc("Incident Report", ir, force=True,
                                  ignore_permissions=True, delete_permanently=True)
            except Exception:
                pass
        purge_asset(cls.asset.name)
        frappe.db.commit()

    @classmethod
    def _mk(cls, status: str) -> str:
        """Tạo incident rồi force-set status (bypass workflow gate cho fixture)."""
        out = report_incident(
            asset=cls.asset.name, incident_type="Malfunction", severity="High",
            description=f"_Test dashboard open_total {status}",
        )
        name = out["name"]
        cls._incidents.append(name)
        if status != "Open":
            frappe.db.set_value("Incident Report", name, "status", status,
                                update_modified=False)
        return name

    def setUp(self):
        frappe.set_user("Administrator")

    # ── TC-12-DASH-01: open_total == count(open_incident_filter()) ≠ stats['open'] ──

    def test_tc_12_dash_01_open_total_equals_filter_count(self):
        """open_total = count(open_incident_filter()) = tổng 4 open-state, KHÁC
        stats['open'] (chỉ status=='Open'). Chứng minh open_total KHÔNG bằng 'open'.

        RED-proof: nếu open_total bị bind = stats['open'] thì assertNotEqual fail —
        fixture có Acknowledged+In Progress+RCA Required ngoài 2 Open."""
        from assetcore.services.imm12 import get_incident_stats, open_incident_filter
        stats = get_incident_stats()
        self.assertIn("open_total", stats, "thiếu key open_total (chưa implement)")
        expected = frappe.db.count("Incident Report", filters=open_incident_filter())
        self.assertEqual(
            stats["open_total"], expected,
            "open_total phải == count qua open_incident_filter() (SoT)")
        # Backward-compat: per-state breakdown vẫn còn (consumer khác đọc).
        self.assertIn("open", stats)
        self.assertIn("investigating", stats)
        # open_total ≠ open: fixture có >1 open-state → bắt buộc khác (chống bind nhầm).
        self.assertNotEqual(
            stats["open_total"], stats["open"],
            "open_total (MỌI open-state) phải KHÁC 'open' (chỉ status==Open)")
        self.assertGreater(stats["open_total"], stats["open"])

    # ── TC-12-DASH-02: active_incidents ⊆ open-states, count(no-limit) == open_total ──

    def test_tc_12_dash_02_active_incidents_open_set_only(self):
        """get_dashboard().active_incidents chỉ chứa incident open-state — KHÔNG
        Closed/Cancelled, CÓ Acknowledged + RCA Required. Số dòng (scope asset,
        trước limit) == open_total cùng scope."""
        from assetcore.services.imm12 import get_dashboard, open_incident_filter
        dash = get_dashboard()
        active = dash["active_incidents"]
        statuses = {r["status"] for r in active if r["asset"] == self.asset.name}
        self.assertTrue(
            statuses.issubset({"Open", "Acknowledged", "In Progress", "RCA Required"}),
            f"active_incidents lọt status ngoài open-set: {statuses}")
        self.assertNotIn("Closed", statuses)
        self.assertNotIn("Cancelled", statuses)
        # +Acknowledged +RCA Required (fixture) — KHÔNG bị bỏ sót như filter cũ.
        self.assertIn("Acknowledged", statuses)
        self.assertIn("RCA Required", statuses)
        self.assertIn("In Progress", statuses)
        # Số dòng (scope asset) == open_total cùng scope (invariant count==drill).
        rows_for_asset = sum(1 for r in active if r["asset"] == self.asset.name)
        expected = frappe.db.count(
            "Incident Report", filters=open_incident_filter({"asset": self.asset.name}))
        self.assertEqual(rows_for_asset, expected,
                         "số dòng active (scope asset) phải == open_total scope")

    # ── TC-12-DASH-03: structural/invariant guard — chỉ open_incident_filter() ──

    def test_tc_12_dash_03_no_local_open_tuple_in_dashboard(self):
        """Grep guard: get_incident_stats/get_dashboard KHÔNG còn tuple open-set cục
        bộ ([Open, In Progress]…) — chỉ open_incident_filter(). Invariant: thêm 1
        incident open-state vào DB thì open_total tăng đúng 1."""
        import inspect
        import assetcore.services.imm12 as svc12

        src_stats = inspect.getsource(svc12.get_incident_stats)
        src_dash = inspect.getsource(svc12.get_dashboard)
        # KHÔNG còn list open-set cục bộ inline ([_STATUS_OPEN, _STATUS_INVESTIGATING]).
        for bad in ("[_STATUS_OPEN, _STATUS_INVESTIGATING]",
                    '["Open", "In Progress"]', "['Open', 'In Progress']"):
            self.assertNotIn(bad, src_dash,
                             f"get_dashboard còn open-set tuple cục bộ: {bad}")
            self.assertNotIn(bad, src_stats,
                             f"get_incident_stats còn open-set tuple cục bộ: {bad}")
        # open-set semantics phải đi qua helper SoT.
        self.assertIn("open_incident_filter", src_dash)
        self.assertIn("open_incident_filter", src_stats)

        # Invariant: open_total bám DB realtime — thêm 1 In Progress → +1.
        from assetcore.services.imm12 import get_incident_stats
        before = get_incident_stats()["open_total"]
        extra = self._mk("In Progress")
        frappe.db.commit()
        after = get_incident_stats()["open_total"]
        self.assertEqual(after, before + 1,
                         "open_total phải tăng theo open-state mới (bám SoT realtime)")
        # cleanup local extra (tearDownClass cũng quét, nhưng giữ count sạch).
        frappe.delete_doc("Incident Report", extra, force=True,
                          ignore_permissions=True, delete_permanently=True)
        frappe.db.commit()


class TestIncidentStatsSeverityOpenScope(unittest.TestCase):
    """KPI strip worklist (IMM-12): severity tile đếm theo OPEN-SET SoT.

    get_incident_stats() trả thêm critical_open / high_open == _count(
    open_incident_filter() ∧ {severity}) — KHÔNG global all-status. Loại
    Closed/Cancelled/Resolved → strip khớp số dòng severity trong bảng khi drill
    ?open=1. critical_open<=critical, high_open<=high luôn đúng. DÙNG LẠI 1 SoT
    open_incident_filter() (round-18), KHÔNG inline negative-list mới.

    Count global (cls.asset dùng chung + data live) → assert theo DELTA quanh seed
    (before/after) thay vì tuyệt đối, robust với incident tích luỹ từ test khác.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-statsev")
        cls._incidents: list[str] = []

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for ir in cls._incidents:
            try:
                frappe.delete_doc("Incident Report", ir, force=True,
                                  ignore_permissions=True, delete_permanently=True)
            except Exception:
                pass
        purge_asset(cls.asset.name)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")

    def _mk(self, severity: str, status: str) -> str:
        """Tạo incident rồi force-set status (bypass workflow gate cho test)."""
        clinical = "Ảnh hưởng chẩn đoán" if severity == "Critical" else ""
        out = report_incident(
            asset=self.asset.name, incident_type="Malfunction", severity=severity,
            description=f"_Test StatSev {severity} {status}", clinical_impact=clinical,
        )
        name = out["name"]
        self._incidents.append(name)
        if status != "Open":
            frappe.db.set_value("Incident Report", name, "status", status,
                                update_modified=False)
            frappe.db.commit()
        return name

    # ── TC-12-STAT-01: open Critical=1 + open High=2 + 1 Closed Critical ─────────
    def test_stat_01_severity_open_counts_exclude_closed(self):
        """seed open Critical=1 + open High=2 + 1 Closed Critical →
        critical_open += 1 (Closed KHÔNG vào), high_open += 2; critical (global)
        += 2 (gồm Closed), high (global) += 2."""
        from assetcore.services.imm12 import get_incident_stats
        before = get_incident_stats()
        self._mk("Critical", "Open")          # → critical_open
        self._mk("Critical", "Closed")        # → critical (global) chỉ, KHÔNG open
        self._mk("High", "Open")              # → high_open
        self._mk("High", "In Progress")       # → high_open (open-state)
        frappe.db.commit()
        after = get_incident_stats()

        self.assertEqual(after["critical_open"] - before["critical_open"], 1,
                         "Closed Critical KHÔNG được vào critical_open")
        self.assertEqual(after["high_open"] - before["high_open"], 2,
                         "2 High open-state phải vào high_open")
        self.assertEqual(after["critical"] - before["critical"], 2,
                         "critical (global) gồm cả Closed → +2")
        self.assertEqual(after["high"] - before["high"], 2)

    # ── TC-12-STAT-02: SoT parity byte-for-byte (không drift) ────────────────────
    def test_stat_02_critical_open_equals_sot_count(self):
        """critical_open == _count(open_incident_filter({severity:Critical}))
        byte-for-byte; Closed/Cancelled severity=Critical KHÔNG vào."""
        from assetcore.services.imm12 import (
            get_incident_stats, open_incident_filter, _SEV_CRITICAL, _SEV_HIGH,
        )
        self._mk("Critical", "Open")
        self._mk("Critical", "Cancelled")     # terminal → ngoài open-set
        self._mk("High", "Acknowledged")
        frappe.db.commit()

        stats = get_incident_stats()
        sot_crit = frappe.db.count(
            "Incident Report",
            filters=open_incident_filter({"severity": _SEV_CRITICAL}))
        sot_high = frappe.db.count(
            "Incident Report",
            filters=open_incident_filter({"severity": _SEV_HIGH}))
        self.assertEqual(stats["critical_open"], sot_crit,
                         "critical_open phải == open_incident_filter SoT count")
        self.assertEqual(stats["high_open"], sot_high)
        # Cancelled Critical KHÔNG vào open-set → critical_open < critical (có Cancelled).
        self.assertLess(stats["critical_open"], stats["critical"])

    # ── TC-12-STAT-03: invariant open<=global + open_total bất biến ──────────────
    def test_stat_03_invariant_open_le_global_and_total_unchanged(self):
        """critical_open<=critical & high_open<=high luôn đúng; open_total
        (round-21) KHÔNG đổi bởi field severity-open mới (chỉ đo open-state)."""
        from assetcore.services.imm12 import get_incident_stats
        self._mk("Critical", "Open")
        self._mk("High", "Open")
        self._mk("High", "Resolved")          # terminal → ngoài open-set
        frappe.db.commit()

        stats = get_incident_stats()
        self.assertLessEqual(stats["critical_open"], stats["critical"])
        self.assertLessEqual(stats["high_open"], stats["high"])
        # open_total = open_incident_filter() KHÔNG kèm severity → bằng đếm mọi
        # open-state, độc lập với severity-open field; cross-check vẫn là SoT.
        from assetcore.services.imm12 import open_incident_filter
        self.assertEqual(
            stats["open_total"],
            frappe.db.count("Incident Report", filters=open_incident_filter()),
            "open_total phải == open_incident_filter() SoT (không bị field mới đổi)")


# ─── BR-12-12: KPI 'chronic' = LIVE rolling-window SoT (kill tile-vs-panel drift) ──


class TestChronicSoT(unittest.TestCase):
    """BR-12-12: KPI tile 'Lặp lại (Chronic)' phái sinh từ SoT LIVE rolling-window
    (get_chronic_failures / chronic_failure_count) — số NHÓM (asset, fault_code)
    đang chronic trong cửa sổ 90 ngày — KHÔNG đếm cờ stale chronic_failure_flag.

    SoT helper chronic_failure_count() == len(get_chronic_failures()) (1 query
    builder, anti-drift). Cờ chronic_failure_flag GIỮ NGUYÊN cho badge per-row
    (lifecycle BR-12-03) — KHÔNG xoá/reset/regression.

    Lưu ý isolation: get_chronic_failures()/chronic_failure_count() là GLOBAL
    (không scope asset). Test dùng fault_code tag DUY NHẤT/run để định danh nhóm
    của test trong list, và đo DELTA của chronic_failure_count() (before/after)
    để bất biến với data chronic có sẵn trong DB.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-chronic")
        cls.asset2 = _make_asset("-chronic2")
        cls._incidents: list[str] = []

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for ir in cls._incidents:
            try:
                frappe.delete_doc("Incident Report", ir, force=True,
                                  ignore_permissions=True, delete_permanently=True)
            except Exception:
                pass
        # Dọn RCA Chronic auto-tạo (nếu có) bám asset test.
        for asset in (cls.asset.name, cls.asset2.name):
            for rca in frappe.get_all(
                "IMM RCA Record", filters={"asset": asset}, pluck="name"
            ):
                try:
                    frappe.delete_doc("IMM RCA Record", rca, force=True,
                                      ignore_permissions=True, delete_permanently=True)
                except Exception:
                    pass
        purge_asset(cls.asset.name)
        purge_asset(cls.asset2.name)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")

    def _mk_incident(
        self, asset: str, fault_code: str, *, age_days: int = 0, flag: int = 0,
        status: str = "Open",
    ) -> str:
        """Tạo 1 Incident cho nhóm (asset, fault_code).

        age_days > 0 → backdate reported_at vào quá khứ (aged-out test cho cửa sổ
        90d). flag=1 → set chronic_failure_flag (mô phỏng cụm cũ từng chronic, cờ
        bền vững vẫn còn). status force-set bypass workflow gate.
        """
        out = report_incident(
            asset=asset, incident_type="Malfunction", severity="High",
            description=f"_Test chronic {fault_code}", fault_code=fault_code,
        )
        name = out["name"]
        self._incidents.append(name)
        updates: dict = {}
        if age_days:
            from frappe.utils import add_to_date, now_datetime
            updates["reported_at"] = add_to_date(now_datetime(), days=-age_days)
        if flag:
            updates["chronic_failure_flag"] = 1
        if status != "Open":
            updates["status"] = status
        if updates:
            frappe.db.set_value("Incident Report", name, updates,
                                update_modified=False)
        frappe.db.commit()
        return name

    def _groups_for(self, asset: str, fault_code: str) -> int:
        """Số nhóm LIVE từ get_chronic_failures() khớp (asset, fault_code) test."""
        from assetcore.services.imm12 import get_chronic_failures
        groups = get_chronic_failures()
        return sum(
            1 for g in groups
            if g["asset"] == asset and g["fault_code"] == fault_code
        )

    # ── TC-IMM12-CHRONIC-01: tile đếm số NHÓM live, KHÔNG đếm incident-rows ──────
    def test_chronic_01_counts_live_groups_not_rows(self):
        """3 incident cùng (asset, fault_code) trong 90d → 1 nhóm chronic. Thêm
        nhóm thứ 2 đủ 3 → +1 nhóm. stats.chronic đo DELTA = +1 rồi +2 (không phải
        3 rồi 6 incident-rows).

        RED với _count(chronic_failure_flag): cờ chưa set bởi scheduler ⇒ trả 0,
        không phản ánh nhóm live. RED với đếm rows: trả 3/6 thay vì 1/2."""
        from assetcore.services.imm12 import (
            get_incident_stats, chronic_failure_count, get_chronic_failures,
        )
        tag1 = f"FC-CHR1-{_RUN_TAG}"
        base = get_incident_stats()["chronic"]
        base_helper = chronic_failure_count()
        self.assertEqual(base, base_helper,
                         "stats.chronic phải == chronic_failure_count() (cùng SoT)")

        # Nhóm 1: đúng 3 incident cùng (asset, fault_code) trong 90d.
        for _ in range(3):
            self._mk_incident(self.asset.name, tag1)
        after1 = get_incident_stats()["chronic"]
        self.assertEqual(after1 - base, 1,
                         "3 incident cùng nhóm trong 90d → +1 NHÓM (không +3 rows)")
        # Nhóm test xuất hiện đúng 1 lần (1 nhóm) trong list live.
        self.assertEqual(self._groups_for(self.asset.name, tag1), 1)

        # Nhóm 2 (asset khác, đủ 3) → +1 nhóm nữa.
        tag2 = f"FC-CHR2-{_RUN_TAG}"
        for _ in range(3):
            self._mk_incident(self.asset2.name, tag2)
        after2 = get_incident_stats()["chronic"]
        self.assertEqual(after2 - base, 2,
                         "2 nhóm đủ chronic → +2 NHÓM (không 6 incident-rows)")
        # Helper == stats.chronic == len(list) (1 SoT, no drift).
        self.assertEqual(get_incident_stats()["chronic"], chronic_failure_count())
        self.assertEqual(chronic_failure_count(), len(get_chronic_failures()))

    # ── TC-IMM12-CHRONIC-02 (BUG CHÍNH): aged-out cụm → tile GIẢM về delta 0 ─────
    def test_chronic_02_aged_out_group_drops_to_zero(self):
        """3 incident cùng (asset, fault_code) với reported_at > 90 ngày trước
        (cờ chronic_failure_flag=1 vẫn còn — mô phỏng cụm từng chronic). KHÔNG còn
        nhóm nào ≥3 trong cửa sổ 90d → đóng góp của test vào stats.chronic = 0.

        RED-prove: revert SoT về _count(chronic_failure_flag=1) ⇒ tile đếm 3 cờ
        stale (delta +1 nhóm-ảo / +3 rows) thay vì 0 ⇒ test FAIL. Restore ⇒ GREEN."""
        from assetcore.services.imm12 import get_incident_stats
        tag = f"FC-AGED-{_RUN_TAG}"
        base = get_incident_stats()["chronic"]
        # 3 incident AGED-OUT (95 ngày) + cờ stale =1 trên cả 3.
        for _ in range(3):
            self._mk_incident(self.asset.name, tag, age_days=95, flag=1)

        after = get_incident_stats()["chronic"]
        # Cờ stale còn nguyên trên 3 incident — chứng minh cờ KHÔNG bị refactor reset.
        flagged = frappe.db.count("Incident Report", filters={
            "asset": self.asset.name, "fault_code": tag,
            "chronic_failure_flag": 1,
        })
        self.assertEqual(flagged, 3, "cờ chronic_failure_flag PHẢI giữ (badge per-row)")
        # SoT LIVE: nhóm aged-out KHÔNG còn ≥3 trong 90d → KHÔNG đóng góp vào tile.
        self.assertEqual(self._groups_for(self.asset.name, tag), 0,
                         "nhóm aged-out >90d KHÔNG được là chronic live")
        self.assertEqual(after, base,
                         "tile chronic KHÔNG tăng vì cờ stale aged-out (BUG CHÍNH)")

    # ── TC-IMM12-CHRONIC-03: invariant stats.chronic == panel trên CÙNG payload ──
    def test_chronic_03_invariant_count_equals_panel(self):
        """get_dashboard(): stats.chronic == len(get_chronic_failures()) (FULL).
        chronic_failures là [:5] view-limit; với data ≤5 nhóm, == panel trực tiếp.
        Quy ước Core Doc (b): count = tổng nhóm FULL, panel = top-5 hiển thị."""
        from assetcore.services.imm12 import get_dashboard, get_chronic_failures
        tag = f"FC-INV-{_RUN_TAG}"
        for _ in range(3):
            self._mk_incident(self.asset.name, tag)
        dash = get_dashboard()
        full = len(get_chronic_failures())
        # Invariant chính (BR-12-12): tile == FULL số nhóm live.
        self.assertEqual(dash["stats"]["chronic"], full,
                         "stats.chronic phải == len(get_chronic_failures()) FULL")
        # Panel [:5]: với ≤5 nhóm == stats.chronic trực tiếp (không drift trên màn).
        if full <= 5:
            self.assertEqual(dash["stats"]["chronic"],
                             len(dash["chronic_failures"]),
                             "data ≤5 nhóm → tile == panel rows (cùng payload)")
        else:
            self.assertEqual(len(dash["chronic_failures"]), 5,
                             "panel cap top-5 khi >5 nhóm (UX)")
            self.assertGreaterEqual(dash["stats"]["chronic"], 5)

    # ── TC-IMM12-CHRONIC-04: no-regression badge cờ + exclude Cancelled ──────────
    def test_chronic_04_badge_flag_preserved_and_cancelled_excluded(self):
        """Cờ chronic_failure_flag VẪN trả về trong list_incidents/detail (badge
        per-row) kể cả khi tile chronic = 0. Cancelled KHÔNG vào nhóm chronic live.
        Refactor KHÔNG reset cờ."""
        from assetcore.services.imm12 import (
            list_incidents, get_incident_detail,
        )
        tag = f"FC-BADGE-{_RUN_TAG}"
        # 1 incident có cờ =1 (aged-out → không là live group) — badge phải còn.
        flagged_name = self._mk_incident(self.asset.name, tag, age_days=120, flag=1)
        # list_incidents trả field chronic_failure_flag (FE badge :271/:317).
        res = list_incidents(asset=self.asset.name, page_size=100)
        row = next(r for r in res["items"] if r["name"] == flagged_name)
        self.assertEqual(row.get("chronic_failure_flag"), 1,
                         "list_incidents PHẢI trả chronic_failure_flag cho badge")
        detail = get_incident_detail(flagged_name)
        self.assertEqual(detail.get("chronic_failure_flag"), 1,
                         "detail PHẢI trả chronic_failure_flag (badge per-row)")

        # Cancelled exclude: 3 incident cùng nhóm trong 90d nhưng Cancelled →
        # KHÔNG là chronic live (get_chronic_failures lọc status != Cancelled).
        tag_c = f"FC-CANC-{_RUN_TAG}"
        for _ in range(3):
            self._mk_incident(self.asset2.name, tag_c, status="Cancelled")
        self.assertEqual(self._groups_for(self.asset2.name, tag_c), 0,
                         "Cancelled KHÔNG được tính vào nhóm chronic live")

    # ── TC-IMM12-CHRONIC-05: grep-guard SoT single-source ───────────────────────
    def test_chronic_05_grep_guard_single_source(self):
        """get_incident_stats() KHÔNG còn _count({'chronic_failure_flag': 1}) cho
        KPI 'chronic' — phải qua chronic_failure_count() (SoT live). chronic_failure_count
        phái sinh từ get_chronic_failures() (no duplicate SQL / no inline GROUP BY)."""
        import inspect
        import assetcore.services.imm12 as svc12

        src_stats = inspect.getsource(svc12.get_incident_stats)
        # KPI tile KHÔNG được đếm cờ stale dưới mọi biến thể quote/spacing.
        for bad in (
            "{'chronic_failure_flag': 1}", '{"chronic_failure_flag": 1}',
            "{'chronic_failure_flag':1}", '{"chronic_failure_flag":1}',
        ):
            self.assertNotIn(
                bad, src_stats,
                f"get_incident_stats còn đếm cờ stale cho KPI chronic: {bad}")
        # 'chronic' key phải bind chronic_failure_count() (SoT helper).
        self.assertIn("chronic_failure_count()", src_stats,
                      "stats.chronic phải bind qua chronic_failure_count() SoT")

        # chronic_failure_count() KHÔNG re-implement SQL — dùng lại get_chronic_failures().
        self.assertTrue(hasattr(svc12, "chronic_failure_count"),
                        "thiếu SoT helper chronic_failure_count()")
        # Loại docstring khỏi guard (docstring mô tả predicate có cụm "GROUP BY";
        # ta chỉ chặn SQL THẬT trong CODE). Inspect CODE BODY, không phải comment.
        import ast
        tree = ast.parse(inspect.getsource(svc12.chronic_failure_count).lstrip())
        fn_node = tree.body[0]
        body = fn_node.body
        if body and isinstance(body[0], ast.Expr) and isinstance(
            getattr(body[0], "value", None), ast.Constant
        ):
            body = body[1:]  # drop docstring node
        code_only = "\n".join(ast.dump(n) for n in body)
        self.assertIn("get_chronic_failures", code_only,
                      "chronic_failure_count phải phái sinh từ get_chronic_failures()")
        self.assertNotIn("frappe.db.sql", code_only.lower(),
                         "chronic_failure_count KHÔNG được inline raw SQL (no dup)")
        # Cross-runtime đảm bảo 1 SoT predicate: count == len(list).
        from assetcore.services.imm12 import (
            chronic_failure_count, get_chronic_failures,
        )
        self.assertEqual(chronic_failure_count(), len(get_chronic_failures()))



# ─── BR-12-09/BR-12-13: SLA-breach LIVE SoT predicate (kill scheduler-lag undercount) ──

class TestSlaBreachKpiSoT(unittest.TestCase):
    """BR-12-09 (LIVE SoT): KPI 'Vi phạm SLA tiếp nhận/xử lý' phải đếm theo SoT
    predicate live `sla_breach_filter(kind)` = (cờ-set) OR (đang-mở ∧ quá-hạn-live),
    KHÔNG chỉ cờ stale stamped-by-scheduler → kill undercount cửa-sổ-trễ-scheduler.

    Mọi fixture: incident OPEN/In-Progress với due-time đã quá hạn nhưng cờ DB còn 0
    (KHÔNG chạy scheduler) → BE phải đếm = 1 (live). Idempotent vs scheduler: chạy
    check_incident_sla_breach() stamp cờ ⇒ KPI BẰNG giá trị trước (anti double-count).
    INV-SLA-1..6 + grep-guard 1 SoT.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-slakpi")
        cls._incidents: list[str] = []

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for ir in cls._incidents:
            try:
                frappe.delete_doc("Incident Report", ir, force=True,
                                  ignore_permissions=True, delete_permanently=True)
            except Exception:
                pass
        purge_asset(cls.asset.name)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")

    # ── fixtures ────────────────────────────────────────────────────────────────

    def _new_incident(self, severity: str = "Medium", description: str = "") -> str:
        clinical = "Ảnh hưởng chẩn đoán" if severity == "Critical" else ""
        out = report_incident(
            asset=self.asset.name, incident_type="Malfunction", severity=severity,
            description=description or f"_Test SLA-KPI {severity}", clinical_impact=clinical,
        )
        name = out["name"]
        self._incidents.append(name)
        return name

    def _set(self, name: str, **vals) -> None:
        frappe.db.set_value("Incident Report", name, vals, update_modified=False)
        frappe.db.commit()

    def _open_resolution_overdue(self, *, flag: int = 0) -> str:
        """OPEN/In-Progress incident, resolution_due_at = now−2h, cờ=flag, no scheduler."""
        from frappe.utils import add_to_date, now_datetime
        ir = self._new_incident(description="_Test SLA-KPI resolution-overdue")
        now = now_datetime()
        self._set(
            ir, status="In Progress",
            acknowledged_at=add_to_date(now, hours=-5),
            response_due_at=add_to_date(now, hours=-4),   # ack trước hạn → no resp breach
            resolution_due_at=add_to_date(now, hours=-2),  # đã quá hạn LIVE
            response_breached=0, resolution_breached=flag,
        )
        return ir

    def _open_response_overdue(self, *, flag: int = 0) -> str:
        """OPEN chưa acknowledged, response_due_at = now−1h, cờ=flag, no scheduler."""
        from frappe.utils import add_to_date, now_datetime
        ir = self._new_incident(description="_Test SLA-KPI response-overdue")
        now = now_datetime()
        self._set(
            ir, status="Open", acknowledged_at=None,
            response_due_at=add_to_date(now, hours=-1),    # đã quá hạn LIVE
            resolution_due_at=add_to_date(now, hours=+48),  # còn hạn
            response_breached=0, resolution_breached=flag,
        )
        return ir

    # ── TC-SLA-KPI-01: live resolution overdue, cờ=0, no scheduler → tile =1 (INV-SLA-1) ──

    def test_tc01_resolution_live_overdue_flag0_counts(self):
        from assetcore.services.imm12 import get_incident_stats
        before = get_incident_stats()["sla_resolution_breached"]
        self._open_resolution_overdue(flag=0)
        after = get_incident_stats()["sla_resolution_breached"]
        # cờ DB vẫn 0 (scheduler chưa chạy) — nhưng phải đếm LIVE.
        self.assertEqual(
            after - before, 1,
            "INV-SLA-1: incident OPEN quá hạn resolution cờ=0 (no scheduler) "
            "PHẢI đếm LIVE =+1 (cũ trả 0 — RED-first)",
        )

    # ── TC-SLA-KPI-02: live response overdue, cờ=0, no scheduler → tile =1 (INV-SLA-2) ──

    def test_tc02_response_live_overdue_flag0_counts(self):
        from assetcore.services.imm12 import get_incident_stats
        before = get_incident_stats()["sla_response_breached"]
        self._open_response_overdue(flag=0)
        after = get_incident_stats()["sla_response_breached"]
        self.assertEqual(
            after - before, 1,
            "INV-SLA-2: incident OPEN chưa ack quá hạn response cờ=0 PHẢI đếm LIVE =+1",
        )

    # ── TC-SLA-KPI-03: idempotent vs scheduler (INV-SLA-4 anti double-count) ─────

    def test_tc03_idempotent_vs_scheduler(self):
        from assetcore.services.imm12 import get_incident_stats, check_incident_sla_breach
        ir = self._open_resolution_overdue(flag=0)
        before = get_incident_stats()["sla_resolution_breached"]
        # Scheduler stamp cờ → incident chuyển từ nhánh live sang nhánh cờ=1.
        check_incident_sla_breach()
        # cờ phải =1 sau scheduler (write-path stamp giữ nguyên).
        self.assertEqual(
            frappe.db.get_value("Incident Report", ir, "resolution_breached"), 1,
            "scheduler phải stamp cờ resolution_breached=1 (write-path no-regression)",
        )
        after = get_incident_stats()["sla_resolution_breached"]
        self.assertEqual(
            after, before,
            "INV-SLA-4: KPI trước==sau scheduler (incident đã đếm vì live nay đếm vì "
            "cờ — KHÔNG nhảy số / double-count)",
        )

    # ── TC-SLA-KPI-04: cờ lịch sử (đóng đúng hạn rồi set cờ) vẫn đếm (INV-SLA-3) ──

    def test_tc04_historical_flag_still_counts(self):
        from frappe.utils import add_to_date, now_datetime
        from assetcore.services.imm12 import get_incident_stats
        before = get_incident_stats()["sla_resolution_breached"]
        ir = self._new_incident(description="_Test SLA-KPI historical-flag")
        now = now_datetime()
        # Resolved/Closed (terminal) — due KHÔNG còn 'live-open', nhưng cờ lịch sử =1.
        self._set(
            ir, status="Closed",
            resolution_due_at=add_to_date(now, hours=-200),  # quá khứ xa
            resolution_breached=1,
        )
        after = get_incident_stats()["sla_resolution_breached"]
        self.assertEqual(
            after - before, 1,
            "INV-SLA-3: incident terminal với cờ lịch sử=1 VẪN đếm (nhánh A predicate)",
        )

    # ── TC-SLA-KPI-05: terminal Cancelled overdue cờ=0 → KHÔNG đếm (INV-SLA-6) ───

    def test_tc05_cancelled_overdue_flag0_no_phantom(self):
        from frappe.utils import add_to_date, now_datetime
        from assetcore.services.imm12 import get_incident_stats
        before = get_incident_stats()["sla_resolution_breached"]
        ir = self._new_incident(description="_Test SLA-KPI cancelled-overdue")
        now = now_datetime()
        # Cancelled (terminal, đóng đúng hạn) — due quá hạn nhưng cờ=0 → KHÔNG live-overdue.
        self._set(
            ir, status="Cancelled",
            resolution_due_at=add_to_date(now, hours=-3),
            resolution_breached=0,
        )
        after = get_incident_stats()["sla_resolution_breached"]
        self.assertEqual(
            after, before,
            "INV-SLA-6: Cancelled (terminal) cờ=0 KHÔNG bị tính live-overdue (no phantom)",
        )

    # ── TC-SLA-KPI-06: per-row enrich is_*_breached live (INV-SLA-5) ────────────

    def test_tc06_list_enrich_is_breached_live(self):
        from assetcore.services.imm12 import list_incidents
        overdue = self._open_resolution_overdue(flag=0)
        in_window = self._new_incident(description="_Test SLA-KPI in-window")
        from frappe.utils import add_to_date, now_datetime
        now = now_datetime()
        self._set(
            in_window, status="In Progress",
            acknowledged_at=add_to_date(now, hours=-1),
            response_due_at=add_to_date(now, hours=-1),    # ack trước → no resp breach
            resolution_due_at=add_to_date(now, hours=+24),  # còn hạn
            response_breached=0, resolution_breached=0,
        )
        rows = {r["name"]: r for r in list_incidents(asset=self.asset.name,
                                                     page_size=100)["items"]}
        self.assertIn(overdue, rows)
        self.assertIn(in_window, rows)
        # overdue incident: cờ thô vẫn 0 nhưng derived live =1.
        self.assertEqual(rows[overdue].get("resolution_breached"), 0,
                         "cờ thô resolution_breached giữ 0 (backward-compat)")
        self.assertEqual(rows[overdue].get("is_resolution_breached"), 1,
                         "INV-SLA-5: badge derive live=1 cho incident open-overdue cờ=0")
        # in-window incident: derived =0.
        self.assertEqual(rows[in_window].get("is_resolution_breached"), 0,
                         "incident open trong-hạn → is_resolution_breached=0")

    def test_tc06b_response_enrich_live(self):
        from assetcore.services.imm12 import list_incidents
        overdue = self._open_response_overdue(flag=0)
        rows = {r["name"]: r for r in list_incidents(asset=self.asset.name,
                                                     page_size=100)["items"]}
        self.assertEqual(rows[overdue].get("response_breached"), 0)
        self.assertEqual(rows[overdue].get("is_response_breached"), 1,
                         "INV-SLA-5: response live-overdue chưa ack cờ=0 → derived=1")

    # ── TC-SLA-KPI-07: grep-guard — get_incident_stats KHÔNG còn _count(cờ) đơn lẻ ──

    def test_tc07_grep_guard_single_sot(self):
        import ast
        import inspect
        import assetcore.services.imm12 as svc12

        src = inspect.getsource(svc12.get_incident_stats)
        tree = ast.parse(src.lstrip())
        fn = tree.body[0]
        # Scan mọi call _count(...) trong body: KHÔNG được có dict literal {flag:1}.
        for node in ast.walk(fn):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "_count" and node.args
                    and isinstance(node.args[0], ast.Dict)):
                keys = [k.value for k in node.args[0].keys
                        if isinstance(k, ast.Constant)]
                self.assertNotIn(
                    "response_breached", keys,
                    "grep-guard: get_incident_stats KHÔNG còn _count({response_breached:1}) "
                    "đơn lẻ — phải qua sla_breach_count('response')")
                self.assertNotIn(
                    "resolution_breached", keys,
                    "grep-guard: get_incident_stats KHÔNG còn _count({resolution_breached:1}) "
                    "đơn lẻ — phải qua sla_breach_count('resolution')")
        # 2 KPI phải sinh qua sla_breach_count (1 SoT).
        self.assertIn("sla_breach_count", src,
                      "get_incident_stats phải gọi sla_breach_count() cho 2 KPI SLA")

    def test_tc07b_sla_breach_count_derives_from_filter(self):
        """sla_breach_filter là điểm SoT DUY NHẤT — sla_breach_count phái sinh từ nó,
        KHÔNG re-implement open-set/overdue predicate cục bộ."""
        import ast
        import inspect
        import assetcore.services.imm12 as svc12

        src = inspect.getsource(svc12.sla_breach_count)
        self.assertIn("sla_breach_filter", src,
                      "sla_breach_count phải phái sinh từ sla_breach_filter (1 SoT)")
        # sla_breach_filter tái dùng open_incident_filter (chống drift 'open').
        fsrc = inspect.getsource(svc12.sla_breach_filter)
        self.assertIn("open_incident_filter", fsrc,
                      "sla_breach_filter phải tái dùng open_incident_filter (SoT 'open')")


# ─── V4-GATE BÁO-HỎNG e2e (ADR-IMM12-REPORT-FAILURE D1/D2) ──────────────────────
# AC1 3-tier cap-gate parity (đóng lỗ leo quyền P1) + AC2 canonical lifecycle
# event 'incident_reported' + provenance source + hash-chain intact.

class TestReportIncidentCapGate(unittest.TestCase):
    """AC1 (D1): API report_incident PHẢI gate cap 'corrective.create'.

    user CÓ corrective.read NHƯNG KHÔNG corrective.create → 403 VI sạch (KHÔNG
    leak raw cap 'corrective.create'), KHÔNG tạo Incident. user có corrective.create
    → 200 + Incident tạo. Gate ở API tier (đường HTTP duy nhất) — pattern cancel_incident.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-capgate")
        # read-only persona: AssetCore Auditor có read=1 NHƯNG create=0 trên Incident
        # Report (verified live DocPerm) → có corrective.read, KHÔNG corrective.create.
        cls.reader = cls._ensure_user(
            "_test_corr_reader@assetcore.test", ["AssetCore Auditor"])
        # create persona: Corrective User có create=1.
        cls.creator = cls._ensure_user(
            "_test_corr_creator@assetcore.test", ["Corrective User"])

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        purge_asset(cls.asset.name)
        for u in (cls.reader, cls.creator):
            try:
                frappe.delete_doc("User", u, force=True, ignore_permissions=True)
            except Exception:
                pass

    @staticmethod
    def _ensure_user(email: str, roles: list[str]) -> str:
        if not frappe.db.exists("User", email):
            doc = frappe.get_doc({
                "doctype": "User", "email": email, "first_name": email.split("@")[0],
                "send_welcome_email": 0, "enabled": 1,
            }).insert(ignore_permissions=True)
        else:
            doc = frappe.get_doc("User", email)
        existing = {r.role for r in doc.get("roles", [])}
        for r in roles:
            if r not in existing:
                doc.append("roles", {"role": r})
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        return email

    def setUp(self):
        frappe.set_user("Administrator")

    def _count_incidents(self) -> int:
        return frappe.db.count("Incident Report", {"asset": self.asset.name})

    def test_report_incident_requires_corrective_create_cap(self):
        """user thiếu corrective.create → 403 VI, KHÔNG tạo Incident, KHÔNG leak raw cap."""
        from assetcore.api.imm12 import report_incident as api_report
        before = self._count_incidents()
        frappe.set_user(self.reader)
        try:
            res = api_report(
                asset=self.asset.name, incident_type="Malfunction",
                severity="Medium", description="_Test capgate forbidden reader",
            )
        finally:
            frappe.set_user("Administrator")
        # 403 + không thành công.
        self.assertFalse(res.get("success"),
                         f"reader (corrective.read, KHÔNG create) phải bị chặn, nhận: {res}")
        self.assertEqual(res.get("http_status"), 403,
                         f"phải trả HTTP 403, nhận: {res.get('http_status')}")
        # KHÔNG leak raw capability string vào message VI.
        msg = (res.get("error") or res.get("message") or "")
        self.assertNotIn("corrective.create", msg,
                         f"message KHÔNG được leak raw cap 'corrective.create', nhận: {msg!r}")
        # KHÔNG tạo Incident.
        self.assertEqual(self._count_incidents(), before,
                         "user thiếu cap KHÔNG được tạo Incident")

    def test_report_incident_with_cap_succeeds(self):
        """user có corrective.create → 200 + Incident tạo."""
        from assetcore.api.imm12 import report_incident as api_report
        frappe.set_user(self.creator)
        try:
            res = api_report(
                asset=self.asset.name, incident_type="Malfunction",
                severity="Medium", description="_Test capgate allowed creator",
            )
        finally:
            frappe.set_user("Administrator")
        frappe.db.commit()
        self.assertTrue(res.get("success"),
                        f"creator (corrective.create) phải tạo được Incident, nhận: {res}")
        data = res.get("data") or res
        self.assertTrue(data.get("name"),
                        f"phải trả tên Incident, nhận: {res}")


class TestReportIncidentLifecycleProvenance(unittest.TestCase):
    """AC2 (D2): report_incident emit canonical lifecycle event 'incident_reported'
    + provenance source trong notes; audit hash-chain KHÔNG vỡ."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-lifecycle")

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        purge_asset(cls.asset.name)

    def setUp(self):
        frappe.set_user("Administrator")

    def _lifecycle_events(self, event_type: str | None = None) -> list:
        f: dict = {"asset": self.asset.name}
        if event_type:
            f["event_type"] = event_type
        return frappe.get_all(
            "Asset Lifecycle Event", filters=f,
            fields=["name", "event_type", "notes", "root_doctype", "root_record"],
            order_by="creation desc",
        )

    def test_report_incident_emits_failure_reported_event(self):
        """Sau report_incident: lifecycle event 'incident_reported' cho incident vừa tạo.

        Đo DELTA (asset chia sẻ per-class — test khác cùng class có thể đã tạo event
        trước): KHÔNG có event nào trỏ root_record=incident-này TRƯỚC report; có SAU.
        """
        out = report_incident(
            asset=self.asset.name, incident_type="Malfunction", severity="Medium",
            description="_Test lifecycle emit incident_reported here",
        )
        frappe.db.commit()
        self.assertTrue(out.get("name"))
        after = self._lifecycle_events("incident_reported")
        ev = next((e for e in after if e["root_record"] == out["name"]), None)
        self.assertIsNotNone(
            ev,
            "sau report phải có Asset Lifecycle Event event_type='incident_reported' "
            "trỏ tới incident vừa tạo")
        # Canonical event PHẢI link tới Incident Report (root_doctype + root_record).
        self.assertEqual(ev["root_doctype"], "Incident Report")
        self.assertEqual(ev["root_record"], out["name"])

    def test_report_incident_source_provenance_qr_scan(self):
        """source='qr-scan' → provenance 'qr-scan' trong notes của lifecycle event."""
        out = report_incident(
            asset=self.asset.name, incident_type="Failure", severity="Low",
            description="_Test provenance qr-scan source here",
            source="qr-scan",
        )
        frappe.db.commit()
        evs = self._lifecycle_events("incident_reported")
        target = next((e for e in evs if e["root_record"] == out["name"]), None)
        self.assertIsNotNone(target, "phải có lifecycle event cho incident vừa tạo")
        self.assertIn("qr-scan", (target["notes"] or ""),
                      f"notes phải chứa provenance 'qr-scan', nhận: {target['notes']!r}")

    def test_report_incident_source_provenance_manual_default(self):
        """source mặc định (không truyền) → provenance 'manual' trong notes."""
        out = report_incident(
            asset=self.asset.name, incident_type="Failure", severity="Low",
            description="_Test provenance manual default source",
        )
        frappe.db.commit()
        evs = self._lifecycle_events("incident_reported")
        target = next((e for e in evs if e["root_record"] == out["name"]), None)
        self.assertIsNotNone(target)
        self.assertIn("manual", (target["notes"] or ""),
                      f"notes default phải chứa 'manual', nhận: {target['notes']!r}")

    def test_report_incident_source_unknown_coerced_to_manual(self):
        """source giá trị lạ → coerce về 'manual' (ADR D2: KHÔNG throw, provenance≠gate)."""
        out = report_incident(
            asset=self.asset.name, incident_type="Failure", severity="Low",
            description="_Test provenance unknown coerce manual value",
            source="hacker-injected-value",
        )
        frappe.db.commit()
        evs = self._lifecycle_events("incident_reported")
        target = next((e for e in evs if e["root_record"] == out["name"]), None)
        self.assertIsNotNone(target)
        self.assertIn("manual", (target["notes"] or ""),
                      f"source lạ phải coerce 'manual', nhận: {target['notes']!r}")
        self.assertNotIn("hacker-injected-value", (target["notes"] or ""),
                         "KHÔNG echo giá trị source lạ vào notes")

    def test_report_incident_audit_chain_intact(self):
        """Sau report (+lifecycle event): verify_audit_chain(asset) valid=True (chain KHÔNG vỡ)."""
        from assetcore.utils.lifecycle import verify_audit_chain
        report_incident(
            asset=self.asset.name, incident_type="Malfunction", severity="Medium",
            description="_Test audit chain intact after report here",
            source="qr-scan",
        )
        frappe.db.commit()
        result = verify_audit_chain(self.asset.name)
        self.assertTrue(result.get("valid"),
                        f"hash-chain audit KHÔNG được vỡ sau report, nhận: {result}")


class TestReportIncidentIdempotency(unittest.TestCase):
    """CR-24: idempotency key `client_request_id` đóng cửa sổ re-drain outbox tạo phiếu TRÙNG.

    Gọi report_incident 2× CÙNG client_request_id (cùng reporter) → CHỈ 1 Incident Report;
    call thứ 2 trả name phiếu đã tạo, KHÔNG double lifecycle/audit (NĐ98 audit-integrity).
    Rỗng key → hành vi cũ nguyên vẹn (mỗi call = 1 phiếu, backward-compat 100%).
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-idempotency")

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        purge_asset(cls.asset.name)

    def setUp(self):
        frappe.set_user("Administrator")

    def _key(self, tag: str) -> str:
        return f"crid-{_RUN_TAG}-{tag}-{int(time.time() * 1000)}"

    def _count_key(self, key: str) -> int:
        return frappe.db.count("Incident Report", {"client_request_id": key})

    def _asset_lifecycle_count(self, asset: str) -> int:
        return frappe.db.count(
            "Asset Lifecycle Event",
            {"asset": asset, "event_type": "incident_reported"},
        )

    def _audit_count(self, name: str) -> int:
        return frappe.db.count(
            "IMM Audit Trail", {"ref_doctype": "Incident Report", "ref_name": name})

    def test_report_incident_idempotent_same_key_returns_existing(self):
        """TC1: 2× CÙNG client_request_id → 1 phiếu; name2 == name1 (KHÔNG insert thứ 2)."""
        key = self._key("tc1")
        out1 = report_incident(
            asset=self.asset.name, incident_type="Malfunction", severity="Medium",
            description="_Test idempotent same key first call here",
            client_request_id=key)
        frappe.db.commit()
        out2 = report_incident(
            asset=self.asset.name, incident_type="Malfunction", severity="Medium",
            description="_Test idempotent same key second call DIFFERENT desc",
            client_request_id=key)
        frappe.db.commit()
        self.assertEqual(out2["name"], out1["name"],
                         "call trùng key PHẢI trả name phiếu đã tạo, KHÔNG tạo phiếu thứ 2")
        self.assertEqual(self._count_key(key), 1, "CÙNG key → CHỈ 1 Incident Report")
        # shape ĐỒNG NHẤT create-response (3 key name/status/severity).
        self.assertEqual(set(out2.keys()), {"name", "status", "severity"},
                         f"response trùng-key phải cùng shape create-path, nhận: {out2}")

    def test_report_incident_idempotent_no_double_side_effects(self):
        """TC2: sau call trùng thứ 2 → lifecycle incident_reported cho asset==1 + audit row
        cho phiếu==1 (KHÔNG double — làm bẩn vết audit NĐ98).

        Dùng ASSET RIÊNG (không phải asset chia-sẻ per-class) để đếm 'cho asset == 1' đúng
        acceptance — bug tạo 2 phiếu sẽ sinh 2 event trên CÙNG asset ⇒ RED thật (asset
        chia-sẻ sẽ che bug vì mỗi phiếu-trùng là 1 name khác nhau).
        """
        asset = _make_asset("-tc2nodouble")
        self.addCleanup(purge_asset, asset.name)
        key = self._key("tc2")
        out1 = report_incident(
            asset=asset.name, incident_type="Failure", severity="Medium",
            description="_Test idempotent no double side effects first",
            client_request_id=key)
        frappe.db.commit()
        name = out1["name"]
        ev_before = self._asset_lifecycle_count(asset.name)
        au_before = self._audit_count(name)
        self.assertEqual(ev_before, 1,
                         "sau phiếu mới, asset phải có ĐÚNG 1 lifecycle event incident_reported")
        self.assertEqual(au_before, 1, "phiếu mới phải có ĐÚNG 1 dòng IMM Audit Trail")
        report_incident(
            asset=asset.name, incident_type="Failure", severity="Medium",
            description="_Test idempotent no double side effects duplicate",
            client_request_id=key)
        frappe.db.commit()
        self.assertEqual(self._asset_lifecycle_count(asset.name), 1,
                         "call trùng KHÔNG được emit lifecycle event lần 2 (asset vẫn ĐÚNG 1)")
        self.assertEqual(self._audit_count(name), au_before,
                         "call trùng KHÔNG được ghi audit trail lần 2 (không làm bẩn vết NĐ98)")

    def test_report_incident_no_key_backward_compat(self):
        """TC3: 2 call KHÔNG client_request_id → 2 phiếu riêng (hành vi cũ nguyên vẹn)."""
        before = frappe.db.count("Incident Report", {"asset": self.asset.name})
        out1 = report_incident(
            asset=self.asset.name, incident_type="Failure", severity="Low",
            description="_Test backward compat no key call one here")
        out2 = report_incident(
            asset=self.asset.name, incident_type="Failure", severity="Low",
            description="_Test backward compat no key call two here")
        frappe.db.commit()
        self.assertNotEqual(out1["name"], out2["name"],
                            "KHÔNG key → mỗi call = 1 phiếu riêng biệt")
        self.assertEqual(frappe.db.count("Incident Report", {"asset": self.asset.name}),
                         before + 2, "2 call không khoá phải tạo đúng 2 phiếu")

    def test_report_incident_distinct_keys_create_two(self):
        """TC4: 2 client_request_id KHÁC nhau → 2 phiếu riêng biệt."""
        k1, k2 = self._key("tc4a"), self._key("tc4b")
        out1 = report_incident(
            asset=self.asset.name, incident_type="Malfunction", severity="Low",
            description="_Test distinct keys create two first",
            client_request_id=k1)
        out2 = report_incident(
            asset=self.asset.name, incident_type="Malfunction", severity="Low",
            description="_Test distinct keys create two second",
            client_request_id=k2)
        frappe.db.commit()
        self.assertNotEqual(out1["name"], out2["name"], "2 key khác nhau → 2 phiếu")
        self.assertEqual(self._count_key(k1), 1)
        self.assertEqual(self._count_key(k2), 1)

    def test_report_incident_client_request_id_persisted(self):
        """TC5: field client_request_id lưu đúng giá trị trên doc đã tạo."""
        key = self._key("tc5")
        out = report_incident(
            asset=self.asset.name, incident_type="Failure", severity="Low",
            description="_Test client_request_id persisted on doc",
            client_request_id=key)
        frappe.db.commit()
        self.assertEqual(
            frappe.db.get_value("Incident Report", out["name"], "client_request_id"), key,
            "field client_request_id phải persist đúng giá trị đã truyền")

    def test_report_incident_concurrent_race_no_dup(self):
        """TC6: race concurrent re-drain — insert thứ 2 ném UniqueValidationError → catch +
        re-read → return existing, KHÔNG raise ra client, KHÔNG tạo phiếu trùng."""
        from unittest import mock
        from assetcore.services import imm12 as svc12

        key = self._key("tc6")
        out1 = report_incident(
            asset=self.asset.name, incident_type="Malfunction", severity="Medium",
            description="_Test race winner created first here",
            client_request_id=key)
        frappe.db.commit()
        self.assertEqual(self._count_key(key), 1)
        winner = {"name": out1["name"], "status": out1["status"], "severity": out1["severity"]}
        # Mô phỏng race: pre-insert dedupe MISS (như winner chưa hiện) → code đi vào insert →
        # unique constraint DB ném UniqueValidationError → handler re-read (call thứ 2) → winner.
        with mock.patch.object(svc12, "_dedupe_lookup", side_effect=[None, winner]):
            out2 = svc12.report_incident(
                asset=self.asset.name, incident_type="Malfunction", severity="Medium",
                description="_Test race concurrent second insert dup",
                client_request_id=key)
        frappe.db.commit()
        self.assertEqual(out2["name"], out1["name"],
                         "race → return winner idempotent, KHÔNG raise ra client")
        self.assertEqual(self._count_key(key), 1, "race KHÔNG được tạo phiếu trùng (unique DB chặn)")


class TestReportIncidentHeaderParity(unittest.TestCase):
    """CR-24 §2.1 (HANDOFF header-parity closure): report_incident honor khoá idempotency
    từ header ``X-Idempotency-Key`` / alias ``Idempotency-Key`` qua shared
    ``resolve_idempotency_key`` — body param ``client_request_id`` THẮNG header khi cả hai
    present; cả hai vắng ⇒ NO-OP dedup (legacy web-desk byte-identical). Parity 3 op đã
    honor (imm09 close_work_order / imm00 confirm_receipt / imm11 add_measurement).

    Test-context header: monkeypatch ``frappe.get_request_header`` (resolver try/except
    khi vắng request). Đếm DB theo asset RIÊNG per-test ⇒ delta cô lập.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")

    def setUp(self):
        frappe.set_user("Administrator")

    def _count_asset(self, asset: str) -> int:
        return frappe.db.count("Incident Report", {"asset": asset})

    def _count_key(self, key: str) -> int:
        return frappe.db.count("Incident Report", {"client_request_id": key})

    @staticmethod
    def _hdr_factory(mapping):
        def _hdr(key, default=None):
            return mapping.get(key, default or "")
        return _hdr

    def test_report_incident_header_only_dedup(self):
        """RED-first: body client_request_id='' NHƯNG header X-Idempotency-Key GIỐNG nhau
        2× ⇒ CÙNG name + ĐÚNG 1 Incident Report persist. Hiện ĐỎ trước fix (service chỉ
        đọc body param → 2 phiếu trùng)."""
        from unittest import mock
        asset = _make_asset("-hdronly")
        self.addCleanup(purge_asset, asset.name)
        key = f"crid-hdr-{_RUN_TAG}-{int(time.time() * 1000)}"
        before = self._count_asset(asset.name)
        with mock.patch("frappe.get_request_header",
                        side_effect=self._hdr_factory({"X-Idempotency-Key": key})):
            out1 = report_incident(
                asset=asset.name, incident_type="Malfunction", severity="Medium",
                description="_Test header only dedup first call here here",
                client_request_id="")
            frappe.db.commit()
            out2 = report_incident(
                asset=asset.name, incident_type="Malfunction", severity="Medium",
                description="_Test header only dedup second call DIFFERENT desc",
                client_request_id="")
            frappe.db.commit()
        self.assertEqual(out2["name"], out1["name"],
                         "header-only re-drain CÙNG X-Idempotency-Key phải trả phiếu đã tạo")
        self.assertEqual(self._count_asset(asset.name) - before, 1,
                         "header-only dedup: ĐÚNG 1 Incident Report persist (không nhân đôi)")
        # khoá ĐÃ RESOLVE (header) persist vào Incident.client_request_id ⇒ header-only
        # re-drain khớp đúng row cũ (KHÔNG raw body '').
        self.assertEqual(self._count_key(key), 1,
                         "khoá header đã persist vào client_request_id (không phải raw body)")

    def test_report_incident_body_wins_over_header(self):
        """body='B' + header='H' cùng present ⇒ resolved dùng 'B' (persist/lookup theo 'B',
        KHÔNG 'H') — parity semantics 3 op kia (body non-empty THẮNG)."""
        from unittest import mock
        asset = _make_asset("-bodywins")
        self.addCleanup(purge_asset, asset.name)
        body_key = f"crid-body-{_RUN_TAG}-{int(time.time() * 1000)}"
        hdr_key = f"crid-hdrx-{_RUN_TAG}-{int(time.time() * 1000)}"
        with mock.patch("frappe.get_request_header",
                        side_effect=self._hdr_factory({"X-Idempotency-Key": hdr_key})):
            out = report_incident(
                asset=asset.name, incident_type="Failure", severity="Low",
                description="_Test body wins over header persisted key",
                client_request_id=body_key)
            frappe.db.commit()
        self.assertEqual(
            frappe.db.get_value("Incident Report", out["name"], "client_request_id"),
            body_key, "body param THẮNG header — persist theo body key")
        self.assertEqual(self._count_key(body_key), 1)
        self.assertEqual(self._count_key(hdr_key), 0,
                         "header KHÔNG được dùng làm khoá khi body present (body wins)")

    def test_report_incident_alias_idempotency_key_dedup(self):
        """alias 'Idempotency-Key' (KHÔNG tiền tố X-) cũng được honor (HANDOFF A6 §9)."""
        from unittest import mock
        asset = _make_asset("-alias")
        self.addCleanup(purge_asset, asset.name)
        key = f"crid-alias-{_RUN_TAG}-{int(time.time() * 1000)}"
        before = self._count_asset(asset.name)
        with mock.patch("frappe.get_request_header",
                        side_effect=self._hdr_factory({"Idempotency-Key": key})):
            out1 = report_incident(
                asset=asset.name, incident_type="Malfunction", severity="Medium",
                description="_Test alias idempotency key first call here",
                client_request_id="")
            frappe.db.commit()
            out2 = report_incident(
                asset=asset.name, incident_type="Malfunction", severity="Medium",
                description="_Test alias idempotency key second call here",
                client_request_id="")
            frappe.db.commit()
        self.assertEqual(out2["name"], out1["name"], "alias Idempotency-Key phải dedup")
        self.assertEqual(self._count_asset(asset.name) - before, 1)

    def test_report_incident_no_key_no_header_legacy_noop(self):
        """cả body param LẪN header đều VẮNG ⇒ NO-OP dedup: 2 call = 2 phiếu (legacy
        byte-identical, web-desk/client-cũ 0 regression)."""
        from unittest import mock
        asset = _make_asset("-noopnokey")
        self.addCleanup(purge_asset, asset.name)
        before = self._count_asset(asset.name)
        with mock.patch("frappe.get_request_header",
                        side_effect=self._hdr_factory({})):   # 0 header
            out1 = report_incident(
                asset=asset.name, incident_type="Failure", severity="Low",
                description="_Test no key no header legacy call one here")
            out2 = report_incident(
                asset=asset.name, incident_type="Failure", severity="Low",
                description="_Test no key no header legacy call two here")
            frappe.db.commit()
        self.assertNotEqual(out1["name"], out2["name"], "NO-OP dedup → 2 phiếu riêng")
        self.assertEqual(self._count_asset(asset.name) - before, 2,
                         "cả body lẫn header vắng ⇒ legacy 2 phiếu (byte-identical)")


class TestWriteFamilyIdempotencyInvariant(unittest.TestCase):
    """CR-24 write-family closure guard: cả 5 op offline-write resolve khoá idempotency
    theo CÙNG semantics (body THẮNG header X-Idempotency-Key / Idempotency-Key). Chống
    regression — ai revert 1 op về đọc raw body param ⇒ guard ĐỎ.

    4/5 route qua shared ``assetcore.utils.idempotency.resolve_idempotency_key``
    (imm08 submit_result · imm09 close_work_order · imm00 confirm_receipt · imm12
    report_incident); imm11 add_measurement dùng resolver riêng
    ``_resolve_measurement_idempotency_key`` (ĐÃ honor header — migrate sang shared util
    = backlog, KHÔNG regress).
    """

    def test_shared_resolver_body_wins_header_fallback(self):
        from unittest import mock
        from assetcore.utils.idempotency import resolve_idempotency_key

        # body present → THẮNG (không cần request ctx)
        self.assertEqual(resolve_idempotency_key("B"), "B")
        self.assertEqual(resolve_idempotency_key("  B  "), "B")   # strip
        # body rỗng + header X- → header; body present + header → body THẮNG
        with mock.patch("frappe.get_request_header",
                        side_effect=lambda k, d=None: "H" if k == "X-Idempotency-Key" else (d or "")):
            self.assertEqual(resolve_idempotency_key(""), "H")
            self.assertEqual(resolve_idempotency_key("B"), "B")
        # alias Idempotency-Key khi X- vắng
        with mock.patch("frappe.get_request_header",
                        side_effect=lambda k, d=None: "A" if k == "Idempotency-Key" else (d or "")):
            self.assertEqual(resolve_idempotency_key(""), "A")
        # ngoài request-context → '' KHÔNG raise
        with mock.patch("frappe.get_request_header",
                        side_effect=RuntimeError("outside request context")):
            self.assertEqual(resolve_idempotency_key(""), "")

    def test_five_write_family_ops_route_through_resolver(self):
        import inspect
        from assetcore.services import imm00, imm08, imm09, imm11, imm12

        shared = (
            imm12.report_incident,
            imm08.submit_result,
            imm09.close_work_order,
            imm00.confirm_receipt,
        )
        for fn in shared:
            src = inspect.getsource(fn)
            self.assertIn(
                "resolve_idempotency_key", src,
                f"{fn.__module__}.{fn.__name__} PHẢI resolve khoá qua shared "
                "resolve_idempotency_key (header-fallback, body-wins) — write-family parity")
        # imm11 add_measurement honor header qua resolver riêng (backlog: migrate shared)
        src11 = inspect.getsource(imm11.add_measurement)
        self.assertTrue(
            "_resolve_measurement_idempotency_key" in src11
            or "resolve_idempotency_key" in src11,
            "imm11 add_measurement PHẢI resolve khoá qua resolver honor-header")


class TestCorrectiveCreateCapConsistency(unittest.TestCase):
    """AC1 3-tier parity (test tương đẳng): scan-action SSoT == route meta == svc gate cap.

    Chứng minh CẢ 3 binding cap đều = 'corrective.create' (1 SSoT, không drift).
    Route-meta parity (tầng-1, FE) verify bằng vue-test riêng — ở đây assert 2 binding
    BE (scan-action SSoT tầng-2 + API gate tầng-3) + đọc cap literal route từ ADR/source.
    """

    def test_scan_action_report_failure_cap_is_corrective_create(self):
        """tầng-2: _SCAN_ACTION_SPECS report_failure.capability == 'corrective.create'."""
        from assetcore.services.imm00 import _SCAN_ACTION_SPECS
        spec = next((s for s in _SCAN_ACTION_SPECS
                     if s.get("key") == "report_failure"), None)
        self.assertIsNotNone(spec, "scan-action SSoT phải có report_failure")
        self.assertEqual(spec["capability"], "corrective.create",
                         "scan-action report_failure capability phải = corrective.create")
        self.assertEqual(spec["route"], "IncidentCreate",
                         "scan-action report_failure route phải = IncidentCreate (parity FE)")

    def test_api_report_incident_gates_corrective_create(self):
        """tầng-3: api/imm12.py module hằng _CAP_REPORT == 'corrective.create'."""
        import assetcore.api.imm12 as api12
        self.assertEqual(getattr(api12, "_CAP_REPORT", None), "corrective.create",
                         "API report_incident phải gate cap _CAP_REPORT='corrective.create'")

    def test_corrective_create_resolves_to_incident_report_create(self):
        """SSoT cap binding: CAPABILITY_MAP['corrective.create'] == ('Incident Report','create')."""
        from assetcore.services.shared.rbac import CAPABILITY_MAP
        self.assertEqual(CAPABILITY_MAP.get("corrective.create"),
                         ("Incident Report", "create"))


# ─── BR-12-17/18: attach_incident_photo — bằng chứng hiện trường NĐ98 ───────────
# Mobile CR-17/G6. Đính ảnh sự cố vào Incident Report → File private + đúng 1
# Asset Lifecycle Event 'incident_photo_attached'. Reject (FORBIDDEN/VALIDATION) →
# 0 File, 0 event (mọi nhánh reject TRƯỚC File.insert). get_incident_detail +=
# scene_photos (parity mobile+web, count==rows với max-check qua CÙNG helper).


def _jpg_bytes(pad: int = 32) -> bytes:
    """Bytes ảnh JPEG THẬT (PIL). Frappe File.before_insert strip EXIF ⇒ PIL.open
    phải nhận diện được ảnh (fake magic-byte → UnidentifiedImageError)."""
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (200, 30, 30)).save(buf, format="JPEG")
    return buf.getvalue()


def _truncated_jpg_bytes() -> bytes:
    """Ảnh JPEG THẬT bị CẮT CỤT thân (magic header \\xff\\xd8\\xff hợp lệ nhưng dữ
    liệu scan đứt giữa chừng) — mô phỏng KTV chụp hiện trường wifi/4G chập chờn, đứt
    truyền. PIL.Image.open nhận diện JPEG nhưng .save() ném OSError('Truncated File
    Read'). Filename .jpg ⇒ mimetypes→image/jpeg ⇒ strip_exif chạy (đường vào PIL)."""
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (200, 30, 30)).save(buf, format="JPEG")
    full = buf.getvalue()
    return full[: len(full) // 2]


def _garbage_jpg_bytes() -> bytes:
    """Magic-byte JPEG hợp lệ nhưng thân là RÁC (không phải ảnh) → PIL.Image.open ném
    PIL.UnidentifiedImageError."""
    return b"\xff\xd8\xff" + b"\x00" * 64


class TestIncidentPhotoAttach(unittest.TestCase):
    """BR-12-17/18 (mobile CR-17/G6): đính ảnh bằng chứng hiện trường.

    - success → đúng 1 File private (attached_to Incident Report, is_private=1) +
      đúng 1 lifecycle 'incident_photo_attached' (actor=session.user, hard-req).
    - permission reporter OR incident.write (AUTH-10): outsider read-only → FORBIDDEN,
      0 File; reporter dù thiếu write vẫn đính được (BR-12-17).
    - validation: content-type≠ảnh / size>cap / ảnh thứ 6 khi đủ 5 → VALIDATION
      fields.file, 0 File (nhánh reject KHÔNG tạo File).
    - get_incident_detail.scene_photos: [] khi rỗng; liệt kê đúng list (creation asc).
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-photo")
        # reporter: Corrective User (read+write+create). outsider: Auditor (read-only,
        # write=0) → not-reporter ∧ not-write ⇒ FORBIDDEN.
        cls.reporter = cls._ensure_user("_test_photo_reporter@assetcore.test",
                                        ["Corrective User"])
        cls.outsider = cls._ensure_user("_test_photo_outsider@assetcore.test",
                                        ["AssetCore Auditor"])
        cls._incidents: list[str] = []

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for ir in cls._incidents:
            try:
                for f in frappe.get_all(
                    "File", filters={"attached_to_doctype": "Incident Report",
                                     "attached_to_name": ir}, pluck="name"):
                    frappe.delete_doc("File", f, force=True, ignore_permissions=True)
            except Exception:
                pass
            try:
                frappe.delete_doc("Incident Report", ir, force=True,
                                  ignore_permissions=True, delete_permanently=True)
            except Exception:
                pass
        purge_asset(cls.asset.name)
        for u in (cls.reporter, cls.outsider):
            try:
                frappe.delete_doc("User", u, force=True, ignore_permissions=True)
            except Exception:
                pass
        frappe.db.commit()

    @staticmethod
    def _ensure_user(email: str, roles: list[str]) -> str:
        if not frappe.db.exists("User", email):
            doc = frappe.get_doc({
                "doctype": "User", "email": email, "first_name": email.split("@")[0],
                "send_welcome_email": 0, "enabled": 1,
            }).insert(ignore_permissions=True)
        else:
            doc = frappe.get_doc("User", email)
        existing = {r.role for r in doc.get("roles", [])}
        for r in roles:
            if r not in existing:
                doc.append("roles", {"role": r})
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        return email

    def setUp(self):
        frappe.set_user("Administrator")

    def _new_incident(self, reported_by: str = "Administrator") -> str:
        out = report_incident(
            asset=self.asset.name, incident_type="Malfunction", severity="Medium",
            description="_Test scene-photo evidence incident description here",
            reported_by=reported_by,
        )
        frappe.db.commit()
        self._incidents.append(out["name"])
        return out["name"]

    def _file_count(self, ir: str) -> int:
        return frappe.db.count("File", {
            "attached_to_doctype": "Incident Report",
            "attached_to_name": ir, "is_private": 1})

    # ── TC-12-PHOTO-01 ─────────────────────────────────────────────────────────
    def test_reporter_attach_valid_jpg_creates_private_file(self):
        from assetcore.services.imm12 import attach_incident_photo, get_incident_detail
        ir = self._new_incident(reported_by="Administrator")
        before = len(get_incident_detail(ir)["scene_photos"])
        res = attach_incident_photo(ir, filedata=_jpg_bytes(), filename="scene_a.jpg",
                                    content_type="image/jpeg")
        self.assertTrue(res.get("file_url"), "phải trả file_url")
        self.assertEqual(res.get("file_name"), "scene_a.jpg")
        files = frappe.get_all(
            "File",
            filters={"attached_to_doctype": "Incident Report", "attached_to_name": ir},
            fields=["name", "is_private", "attached_to_doctype", "attached_to_name"])
        self.assertEqual(len(files), 1, "đúng 1 File được tạo")
        self.assertEqual(files[0]["is_private"], 1, "File PHẢI private (NĐ98)")
        self.assertEqual(files[0]["attached_to_doctype"], "Incident Report")
        self.assertEqual(files[0]["attached_to_name"], ir)
        self.assertEqual(len(get_incident_detail(ir)["scene_photos"]), before + 1,
                         "scene_photos +1 sau khi đính")

    # ── TC-12-PHOTO-02 ─────────────────────────────────────────────────────────
    def test_success_emits_exactly_one_lifecycle_event(self):
        from assetcore.services.imm12 import attach_incident_photo
        ir = self._new_incident()
        attach_incident_photo(ir, filedata=_jpg_bytes(), filename="scene_b.png",
                              content_type="image/png")
        evts = frappe.get_all(
            "Asset Lifecycle Event",
            filters={"event_type": "incident_photo_attached", "root_record": ir},
            fields=["name", "actor", "asset", "root_doctype"])
        self.assertEqual(len(evts), 1, "đúng 1 lifecycle event/lần success")
        self.assertEqual(evts[0]["actor"], "Administrator", "actor = session.user")
        self.assertEqual(evts[0]["asset"], self.asset.name)
        self.assertEqual(evts[0]["root_doctype"], "Incident Report")

    # ── TC-12-PHOTO-03 ─────────────────────────────────────────────────────────
    def test_outsider_not_reporter_no_write_forbidden_no_file(self):
        from assetcore.services.imm12 import attach_incident_photo
        ir = self._new_incident(reported_by="Administrator")
        frappe.set_user(self.outsider)
        try:
            with self.assertRaises(ServiceError) as ctx:
                attach_incident_photo(ir, filedata=_jpg_bytes(), filename="x.jpg",
                                      content_type="image/jpeg")
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(ctx.exception.code, ErrorCode.FORBIDDEN)
        self.assertEqual(self._file_count(ir), 0, "nhánh FORBIDDEN KHÔNG tạo File")

    def test_reporter_without_write_can_attach(self):
        """BR-12-17: reporter luôn đính được phiếu của mình dù thiếu write DocPerm."""
        from assetcore.services.imm12 import attach_incident_photo
        ir = self._new_incident(reported_by=self.outsider)  # outsider = reporter (no write)
        frappe.set_user(self.outsider)
        try:
            res = attach_incident_photo(ir, filedata=_jpg_bytes(), filename="r.jpg",
                                        content_type="image/jpeg")
        finally:
            frappe.set_user("Administrator")
        self.assertTrue(res.get("file_url"))
        self.assertEqual(self._file_count(ir), 1)

    # ── TC-12-PHOTO-04 ─────────────────────────────────────────────────────────
    def test_reject_non_image_content_type_validation_no_file(self):
        from assetcore.services.imm12 import attach_incident_photo
        ir = self._new_incident()
        with self.assertRaises(ServiceError) as ctx:
            attach_incident_photo(ir, filedata=b"plain text not image",
                                  filename="note.txt", content_type="text/plain")
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
        self.assertIn("file", ctx.exception.fields, "VALIDATION phải có fields.file")
        self.assertEqual(self._file_count(ir), 0, "nhánh VALIDATION KHÔNG tạo File")

    def test_reject_oversize_photo_validation_no_file(self):
        from assetcore.services.imm12 import (attach_incident_photo,
                                              MAX_INCIDENT_PHOTO_BYTES)
        ir = self._new_incident()
        big = b"\x00" * (MAX_INCIDENT_PHOTO_BYTES + 1)
        with self.assertRaises(ServiceError) as ctx:
            attach_incident_photo(ir, filedata=big, filename="big.jpg",
                                  content_type="image/jpeg")
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
        self.assertIn("file", ctx.exception.fields)
        self.assertEqual(self._file_count(ir), 0)

    def test_reject_sixth_photo_when_five_exist(self):
        from assetcore.services.imm12 import (attach_incident_photo,
                                              MAX_INCIDENT_PHOTOS)
        ir = self._new_incident()
        for i in range(MAX_INCIDENT_PHOTOS):
            attach_incident_photo(ir, filedata=_jpg_bytes(), filename=f"s{i}.jpg",
                                  content_type="image/jpeg")
        self.assertEqual(self._file_count(ir), MAX_INCIDENT_PHOTOS)
        with self.assertRaises(ServiceError) as ctx:
            attach_incident_photo(ir, filedata=_jpg_bytes(), filename="s6.jpg",
                                  content_type="image/jpeg")
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
        self.assertIn("Tối đa 5 ảnh", ctx.exception.message)
        self.assertEqual(self._file_count(ir), MAX_INCIDENT_PHOTOS,
                         "ảnh thứ 6 bị chặn → File count giữ nguyên 5")

    # ── TC-12-PHOTO-05 ─────────────────────────────────────────────────────────
    def test_get_incident_detail_scene_photos_parity(self):
        from assetcore.services.imm12 import attach_incident_photo, get_incident_detail
        ir = self._new_incident()
        self.assertEqual(get_incident_detail(ir)["scene_photos"], [],
                         "scene_photos = [] khi chưa có ảnh")
        attach_incident_photo(ir, filedata=_jpg_bytes(), filename="p1.jpg",
                              content_type="image/jpeg")
        attach_incident_photo(ir, filedata=_jpg_bytes(), filename="p2.jpg",
                              content_type="image/jpeg")
        photos = get_incident_detail(ir)["scene_photos"]
        self.assertEqual(len(photos), 2)
        self.assertEqual([p["file_name"] for p in photos], ["p1.jpg", "p2.jpg"],
                         "thứ tự ổn định (creation asc)")
        for p in photos:
            self.assertIn("file_url", p)
            self.assertTrue(p["file_url"])

    # ── API tier — Decision-B envelope + fields propagation (multipart) ──────────
    def _fake_request(self, filedata: bytes, filename: str, content_type: str):
        import io
        from werkzeug.datastructures import FileStorage
        fs = FileStorage(stream=io.BytesIO(filedata), filename=filename,
                         content_type=content_type)

        class _Req:
            files = {"file": fs}
            host = None  # File.get_url() đọc request.host — None → fallback site conf

        return _Req()

    def test_api_attach_returns_decision_b_ok(self):
        from assetcore.api.imm12 import attach_incident_photo as api_attach
        ir = self._new_incident()
        orig = getattr(frappe.local, "request", None)
        frappe.local.request = self._fake_request(_jpg_bytes(), "api.jpg", "image/jpeg")
        try:
            res = api_attach(incident_name=ir)
        finally:
            frappe.local.request = orig
        self.assertTrue(res.get("success"), f"phải success, nhận: {res}")
        self.assertIn("file_url", res["data"])
        self.assertEqual(res["data"]["file_name"], "api.jpg")

    def test_api_attach_non_image_returns_validation_fields(self):
        from assetcore.api.imm12 import attach_incident_photo as api_attach
        ir = self._new_incident()
        orig = getattr(frappe.local, "request", None)
        frappe.local.request = self._fake_request(b"hello", "note.txt", "text/plain")
        try:
            res = api_attach(incident_name=ir)
        finally:
            frappe.local.request = orig
        self.assertFalse(res.get("success"))
        self.assertEqual(res.get("code"), ErrorCode.VALIDATION)
        self.assertIn("file", res.get("fields", {}))
        self.assertEqual(self._file_count(ir), 0)

    # ── TC-12-PHOTO-06: ảnh HỎNG / ĐỨT TRUYỀN → VALIDATION, no 500, no orphan ─────
    def test_reject_corrupt_or_truncated_image_validation_no_file(self):
        """Finding B (ROOT CAUSE): content-type hợp lệ 'image/jpeg' nhưng bytes KHÔNG
        giải mã được (ảnh cắt-cụt/rác). Frappe File.before_insert → strip_exif →
        PIL.Image.open ném UnidentifiedImageError / OSError('Truncated File Read').
        PHẢI chuyển thành VALIDATION Decision-B (fields.file, thông điệp VN), KHÔNG
        raise HTTP-500, KHÔNG tạo File orphan, KHÔNG sinh lifecycle event (bằng chứng
        NĐ98 không lưu nửa vời)."""
        from assetcore.services.imm12 import attach_incident_photo
        for label, data in (("truncated-OSError", _truncated_jpg_bytes()),
                            ("garbage-Unidentified", _garbage_jpg_bytes())):
            with self.subTest(kind=label):
                ir = self._new_incident()
                with self.assertRaises(ServiceError) as ctx:
                    attach_incident_photo(ir, filedata=data, filename="scene_bad.jpg",
                                          content_type="image/jpeg")
                self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION,
                                 f"[{label}] ảnh hỏng → VALIDATION, KHÔNG 500")
                self.assertIn("file", ctx.exception.fields,
                              f"[{label}] Decision-B phải có fields.file")
                self.assertIn("bị lỗi hoặc không đọc được",
                              ctx.exception.fields["file"],
                              f"[{label}] thông điệp VN chụp/chọn lại")
                self.assertEqual(self._file_count(ir), 0,
                                 f"[{label}] KHÔNG tạo File orphan")
                self.assertEqual(frappe.db.count("Asset Lifecycle Event", {
                    "event_type": "incident_photo_attached", "root_record": ir}), 0,
                    f"[{label}] KHÔNG sinh lifecycle event khi ảnh hỏng")


# ─── BR-12-26 / ADR-IMM12-10: attach_incident_photo idempotency (CR-24 phần dư) ──


class TestIncidentPhotoIdempotency(unittest.TestCase):
    """CR-24 phần dư · B-rel-3: idempotency `client_request_id` đóng cửa sổ attachment-dup.

    Re-drain outbox PHA-2 re-POST cùng ảnh (response rớt mạng SAU khi server đã tạo
    File) → File TRÙNG + lifecycle event `incident_photo_attached` TRÙNG (bẩn
    evidence-trail NĐ98). Dedupe theo composite scoped key `{incident}::{key}` trên
    Custom Field `File.ac_client_request_id` (unique NULL-store — ADR-IMM12-10):
      - TC-12-PHOTO-IDEMP-01/02: replay cùng (incident, key) → 1 File + 1 event;
        response#2 == response#1 (KHÔNG insert mới).
      - TC-12-PHOTO-IDEMP-03: key rỗng/thiếu → at-least-once CŨ (2 File, field NULL).
      - TC-12-PHOTO-IDEMP-04: cùng key KHÁC incident → KHÔNG dedupe chéo (2 File).
      - TC-12-PHOTO-IDEMP-05: key persist composite + Custom Field `unique==1`.
      - TC-12-PHOTO-IDEMP-06: dedupe-hit thắng max-count (replay ảnh #5 khi đã đủ
        5 ảnh → success, KHÔNG `VALIDATION "Tối đa 5 ảnh"`).
      - TC-12-PHOTO-IDEMP-07: permission TRƯỚC dedupe — outsider replay key hợp lệ
        → FORBIDDEN (KHÔNG leak file_url qua dedupe-hit).
      - LL-BE-54 kwargs-swallow guard: handler API nhận `client_request_id` TƯỜNG
        MINH (hết bị `**_ignore` nuốt câm) — replay qua API tier vẫn dedupe.

    Precondition: Custom Field `File.ac_client_request_id` đã sync
    (`fixtures/file_custom_fields.json` — qua migrate/import-fixtures).
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-photoidemp")
        # outsider: Auditor read-only (not-reporter ∧ not-write) ⇒ FORBIDDEN.
        cls.outsider = TestIncidentPhotoAttach._ensure_user(
            "_test_photoidemp_outsider@assetcore.test", ["AssetCore Auditor"])
        cls._incidents: list[str] = []

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for ir in cls._incidents:
            try:
                for f in frappe.get_all(
                    "File", filters={"attached_to_doctype": "Incident Report",
                                     "attached_to_name": ir}, pluck="name"):
                    frappe.delete_doc("File", f, force=True, ignore_permissions=True)
            except Exception:
                pass
            try:
                frappe.delete_doc("Incident Report", ir, force=True,
                                  ignore_permissions=True, delete_permanently=True)
            except Exception:
                pass
        purge_asset(cls.asset.name)
        try:
            frappe.delete_doc("User", cls.outsider, force=True,
                              ignore_permissions=True)
        except Exception:
            pass
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")

    def _new_incident(self) -> str:
        out = report_incident(
            asset=self.asset.name, incident_type="Malfunction", severity="Medium",
            description="_Test photo idempotency incident description here",
        )
        frappe.db.commit()
        self._incidents.append(out["name"])
        return out["name"]

    def _key(self, tag: str) -> str:
        return f"pk-{_RUN_TAG}-{tag}-{int(time.time() * 1000)}"

    _seq = 0

    @classmethod
    def _unique_jpg_bytes(cls) -> bytes:
        """Bytes JPEG THẬT, KHÁC nhau mỗi call (đổi màu pixel) — tránh Frappe
        `File` reuse `file_url` khi trùng `content_hash` (2 File riêng nhưng URL
        chung → assert URL-khác sẽ false-fail dù ROW đúng)."""
        import io

        from PIL import Image

        cls._seq += 1
        buf = io.BytesIO()
        Image.new(
            "RGB", (8, 8),
            (cls._seq % 256, (cls._seq * 7) % 256, 30),
        ).save(buf, format="JPEG")
        return buf.getvalue()

    def _attach(self, ir: str, key: str = "", filename: str = "scene.jpg",
                data: bytes | None = None) -> dict:
        from assetcore.services.imm12 import attach_incident_photo
        return attach_incident_photo(
            ir, filedata=data if data is not None else self._unique_jpg_bytes(),
            filename=filename, content_type="image/jpeg", client_request_id=key)

    def _file_count(self, ir: str) -> int:
        return frappe.db.count("File", {
            "attached_to_doctype": "Incident Report",
            "attached_to_name": ir, "is_private": 1})

    def _event_count(self, ir: str) -> int:
        return frappe.db.count("Asset Lifecycle Event", {
            "event_type": "incident_photo_attached", "root_record": ir})

    # ── TC-12-PHOTO-IDEMP-01 + 02 (AC2 lõi) ───────────────────────────────────
    def test_replay_same_key_single_file_event_same_response(self):
        """2× CÙNG key + cùng incident → 1 ROW File + 1 lifecycle event; call#2 trả
        `{file_url, file_name}` == call#1 (KHÔNG insert mới). RED-before: chưa dedupe
        → 2 File."""
        ir = self._new_incident()
        key = self._key("tc1")
        res1 = self._attach(ir, key=key, filename="idemp_a.jpg")
        res2 = self._attach(ir, key=key, filename="idemp_a.jpg")
        self.assertEqual(
            frappe.db.count("File", {"ac_client_request_id": f"{ir}::{key}"}), 1,
            "CÙNG (incident, key) → CHỈ 1 ROW File mang scoped key")
        self.assertEqual(self._file_count(ir), 1,
                         "replay KHÔNG được insert File thứ 2")
        self.assertEqual(self._event_count(ir), 1,
                         "replay KHÔNG được emit lifecycle event lần 2 (NĐ98)")
        self.assertEqual(res2, res1,
                         "response replay phải == lần 1 (file_url/file_name File ĐÃ đính)")
        self.assertEqual(set(res2.keys()), {"file_url", "file_name"},
                         f"shape EXACT 2-key KHÔNG đổi (OAS closed), nhận: {res2}")

    # ── 2 key KHÁC nhau cùng incident → 2 File (không over-dedupe) ─────────────
    def test_distinct_keys_same_incident_two_files(self):
        ir = self._new_incident()
        res1 = self._attach(ir, key=self._key("tc2a"), filename="d1.jpg")
        res2 = self._attach(ir, key=self._key("tc2b"), filename="d2.jpg")
        self.assertNotEqual(res1["file_url"], res2["file_url"],
                            "2 key KHÁC nhau → 2 File riêng biệt")
        self.assertEqual(self._file_count(ir), 2, "2 key KHÁC → đúng 2 File")
        self.assertEqual(self._event_count(ir), 2, "2 File thật → đúng 2 event")

    # ── TC-12-PHOTO-IDEMP-03 (AC3 backward-compat) ─────────────────────────────
    def test_no_key_backward_compat_two_files_null_key(self):
        """2× KHÔNG key → 2 File riêng (at-least-once CŨ); cả 2 ROW ac_client_request_id
        NULL (NULL-store — unique index không collide)."""
        ir = self._new_incident()
        same_photo = _jpg_bytes()  # CÙNG ảnh 2 lần (doc TC-03: "attach 2× cùng ảnh")
        self._attach(ir, key="", filename="nk1.jpg", data=same_photo)
        self._attach(ir, key="", filename="nk2.jpg", data=same_photo)
        self.assertEqual(self._file_count(ir), 2,
                         "KHÔNG key → mỗi call = 1 File (hành vi cũ nguyên vẹn)")
        keys = frappe.get_all(
            "File", filters={"attached_to_doctype": "Incident Report",
                             "attached_to_name": ir, "is_private": 1},
            pluck="ac_client_request_id")
        self.assertTrue(all(not k for k in keys),
                        f"File không-khoá phải lưu NULL/empty, nhận: {keys}")

    # ── TC-12-PHOTO-IDEMP-04 (AC4 scope key) ───────────────────────────────────
    def test_same_key_different_incidents_no_cross_dedupe(self):
        """CÙNG key nhưng 2 incident KHÁC nhau → KHÔNG dedupe chéo (composite khác)
        — mỗi incident 1 File, KHÔNG UniqueValidation lộ ra client."""
        ir_a = self._new_incident()
        ir_b = self._new_incident()
        key = self._key("tc4")
        res_a = self._attach(ir_a, key=key, filename="xa.jpg")
        res_b = self._attach(ir_b, key=key, filename="xb.jpg")
        self.assertNotEqual(res_a["file_url"], res_b["file_url"],
                            "cùng key KHÁC incident → 2 File riêng (composite khác)")
        self.assertEqual(self._file_count(ir_a), 1)
        self.assertEqual(self._file_count(ir_b), 1)
        self.assertEqual(self._event_count(ir_a), 1)
        self.assertEqual(self._event_count(ir_b), 1)

    # ── TC-12-PHOTO-IDEMP-05 (persist + unique index) ──────────────────────────
    def test_key_persisted_composite_and_unique_meta(self):
        """File mang `ac_client_request_id == f'{IR}::{K}'` (key THỰC được persist —
        chứng minh không còn bị `**_ignore` nuốt) + Custom Field `unique==1` (lớp-2
        race qua unique index)."""
        ir = self._new_incident()
        key = self._key("tc5")
        res = self._attach(ir, key=key, filename="pk.jpg")
        stored = frappe.db.get_value(
            "File", {"ac_client_request_id": f"{ir}::{key}"},
            ["file_url", "file_name"], as_dict=True)
        self.assertIsNotNone(stored, "lookup theo scoped key PHẢI hit (key đã persist)")
        self.assertEqual(stored.file_url, res["file_url"])
        field = frappe.get_meta("File").get_field("ac_client_request_id")
        self.assertIsNotNone(field, "Custom Field File.ac_client_request_id phải tồn tại")
        self.assertEqual(int(field.unique or 0), 1,
                         "ac_client_request_id PHẢI unique (NULL-store, ADR-IMM12-10)")

    # ── TC-12-PHOTO-IDEMP-06 (dedupe TRƯỚC max-count) ──────────────────────────
    def test_dedupe_hit_wins_max_count(self):
        """Incident đủ 5 ảnh, ảnh #5 mang key K5 → replay K5 trả success File #5
        (KHÔNG dội VALIDATION 'Tối đa 5 ảnh') — chứng minh dedupe TRƯỚC validation."""
        from assetcore.services.imm12 import MAX_INCIDENT_PHOTOS
        ir = self._new_incident()
        for i in range(MAX_INCIDENT_PHOTOS - 1):
            self._attach(ir, key="", filename=f"m{i}.jpg")
        key5 = self._key("tc6")
        res5 = self._attach(ir, key=key5, filename="m5.jpg")
        self.assertEqual(self._file_count(ir), MAX_INCIDENT_PHOTOS)
        replay = self._attach(ir, key=key5, filename="m5.jpg")
        self.assertEqual(replay, res5,
                         "replay ảnh #5 phải success trả File đã đính, KHÔNG VALIDATION max")
        self.assertEqual(self._file_count(ir), MAX_INCIDENT_PHOTOS,
                         "replay KHÔNG thêm File vượt max")

    # ── TC-12-PHOTO-IDEMP-07 (permission TRƯỚC dedupe) ─────────────────────────
    def test_permission_before_dedupe_forbidden_no_leak(self):
        """Key đã đính bởi admin; outsider (không-reporter ∧ không-write) replay CÙNG
        key → FORBIDDEN Decision-B — KHÔNG leak file_url qua dedupe-hit."""
        ir = self._new_incident()
        key = self._key("tc7")
        res = self._attach(ir, key=key, filename="perm.jpg")
        frappe.set_user(self.outsider)
        try:
            with self.assertRaises(ServiceError) as ctx:
                self._attach(ir, key=key, filename="perm.jpg")
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(ctx.exception.code, ErrorCode.FORBIDDEN,
                         "outsider replay key → FORBIDDEN (permission TRƯỚC dedupe)")
        self.assertNotIn(res["file_url"], str(ctx.exception),
                         "message FORBIDDEN KHÔNG được leak file_url File đã đính")

    # ── LL-BE-54 kwargs-swallow guard: API tier nhận param TƯỜNG MINH ──────────
    def test_api_handler_explicit_param_replay_dedupes(self):
        """Handler `api.imm12.attach_incident_photo` nhận `client_request_id` TƯỜNG
        MINH (∈ signature, KHÔNG bị `**_ignore` nuốt câm) — replay 2× qua API tier
        cùng key → 1 File, response#2 == #1 (Decision-B success)."""
        import inspect as _inspect

        from assetcore.api.imm12 import attach_incident_photo as api_attach
        params = _inspect.signature(api_attach).parameters
        self.assertIn("client_request_id", params,
                      "client_request_id PHẢI là param tường minh của handler API")
        self.assertEqual(params["client_request_id"].default, "",
                         "default PHẢI '' (KHÔNG None — tránh HTTP-417 coercion)")
        ir = self._new_incident()
        key = self._key("api")
        orig = getattr(frappe.local, "request", None)
        results = []
        try:
            for _ in range(2):
                frappe.local.request = TestIncidentPhotoAttach._fake_request(
                    self, self._unique_jpg_bytes(), "api_idemp.jpg", "image/jpeg")
                results.append(api_attach(incident_name=ir, client_request_id=key))
        finally:
            frappe.local.request = orig
        self.assertTrue(results[0].get("success"), f"call#1 phải success: {results[0]}")
        self.assertTrue(results[1].get("success"), f"call#2 phải success: {results[1]}")
        self.assertEqual(results[1]["data"], results[0]["data"],
                         "replay qua API tier phải trả CÙNG File (key không bị nuốt)")
        self.assertEqual(self._file_count(ir), 1,
                         "API replay cùng key → CHỈ 1 File")


# ─── IMM-12 RCA server-driven transitions (GATE-8/LL-FE-51) ──────────────────────
# AC1 get_rca emits allowed_transitions + can_manage_rca; AC2 start_rca; AC3 submit
# only from In Progress (chặn nhảy-cóc); AC4 cancel_rca; AC5 capability enforcement.

def _make_rca(asset_name: str, status: str = "RCA Required",
              rca_method: str = "Fishbone", incident: str | None = None) -> str:
    """Tạo IMM RCA Record fixture ở `status` cho trước.

    Insert ở 'RCA Required' (validate() nhẹ) rồi bump status bằng ``set_value``
    (bypass workflow validate — đối xứng start_rca/cancel_rca thật). rca_method mặc
    định 'Fishbone' để bỏ qua gate 5-Why khi test transition (orthogonal).
    """
    rca = frappe.get_doc({
        "doctype": "IMM RCA Record",
        "asset": asset_name,
        "incident_report": incident,
        "rca_method": rca_method,
        "status": "RCA Required",
        "trigger_type": "Manual",
        "assigned_to": frappe.session.user,
    })
    rca.flags.ignore_permissions = True
    rca.insert()
    if status != "RCA Required":
        frappe.db.set_value("IMM RCA Record", rca.name,
                            {"status": status, "workflow_state": status},
                            update_modified=False)
    frappe.db.commit()
    return rca.name


def _rca_audit_count(rca_name: str, to_status: str) -> int:
    """Đếm bản ghi IMM Audit Trail của transition RCA (ref = RCA, to_status = đích).

    token → to_status: rca_started→'RCA In Progress', rca_completed→'Completed',
    rca_cancelled→'Cancelled' (SSoT _RCA_VALID_TRANSITIONS target states).
    """
    return frappe.db.count("IMM Audit Trail", {
        "ref_doctype": "IMM RCA Record", "ref_name": rca_name, "to_status": to_status,
    })


class TestRCAAllowedTransitions(unittest.TestCase):
    """AC1: get_rca emit allowed_transitions (SSoT _RCA_VALID_TRANSITIONS) +
    can_manage_rca (int 0/1) theo capability corrective — parity get_work_order."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-rcaallowed")

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        purge_asset(cls.asset.name)
        # R-9: xoá user fixture tạo trong test_get_rca_can_manage_flag_zero_for_base_user
        # (unittest.TestCase → KHÔNG auto-rollback; phải dọn tường minh, tránh leak DB).
        try:
            frappe.delete_doc("User", "_rca_base_read@assetcore.test",
                              force=True, ignore_permissions=True)
            frappe.db.commit()
        except Exception:
            pass

    def setUp(self):
        frappe.set_user("Administrator")

    def test_ssot_map_matches_workflow(self):
        """_RCA_VALID_TRANSITIONS khớp đúng đặc tả AC1."""
        self.assertEqual(_RCA_VALID_TRANSITIONS.get("RCA Required"),
                         ["RCA In Progress", "Cancelled"])
        self.assertEqual(_RCA_VALID_TRANSITIONS.get("RCA In Progress"),
                         ["Completed", "Cancelled"])
        self.assertEqual(_RCA_VALID_TRANSITIONS.get("Completed"), [])
        self.assertEqual(_RCA_VALID_TRANSITIONS.get("Cancelled"), [])

    def test_get_rca_emits_allowed_transitions_per_status(self):
        """Mỗi status → allowed_transitions khớp SSoT; can_manage_rca=1 (Admin đủ quyền)."""
        for status, expected in (
            ("RCA Required", ["RCA In Progress", "Cancelled"]),
            ("RCA In Progress", ["Completed", "Cancelled"]),
            ("Completed", []),
            ("Cancelled", []),
        ):
            with self.subTest(status=status):
                name = _make_rca(self.asset.name, status=status)
                data = get_rca(name)
                self.assertIn("allowed_transitions", data,
                              "get_rca phải emit allowed_transitions")
                self.assertEqual(data["allowed_transitions"], expected,
                                 f"{status} → allowed_transitions sai")
                self.assertEqual(data.get("can_manage_rca"), 1,
                                 "Administrator (đủ quyền corrective) → can_manage_rca=1")

    def test_get_rca_can_manage_flag_zero_for_base_user(self):
        """User AssetCore cơ bản (không cap corrective) → can_manage_rca=0."""
        name = _make_rca(self.asset.name, status="RCA Required")
        base = _ensure_role_user("_rca_base_read@assetcore.test", ["AssetCore System User"])
        frappe.set_user(base)
        try:
            data = get_rca(name)
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(data.get("can_manage_rca"), 0,
                         "base user không cap corrective → can_manage_rca=0")


class TestRCAStartTransition(unittest.TestCase):
    """AC2: start_rca 'RCA Required' → 'RCA In Progress' + audit 'rca_started'."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-rcastart")

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        purge_asset(cls.asset.name)

    def setUp(self):
        frappe.set_user("Administrator")

    def test_start_rca_required_to_in_progress_ok(self):
        name = _make_rca(self.asset.name, status="RCA Required")
        before = _rca_audit_count(name, "RCA In Progress")
        out = start_rca(name)
        frappe.db.commit()
        self.assertEqual(out.get("status"), "RCA In Progress")
        self.assertEqual(
            frappe.db.get_value("IMM RCA Record", name, "status"), "RCA In Progress")
        self.assertEqual(_rca_audit_count(name, "RCA In Progress"), before + 1,
                         "start_rca phải sinh 1 audit 'rca_started'")

    def test_start_rca_rejected_when_not_required(self):
        for status in ("RCA In Progress", "Completed"):
            with self.subTest(status=status):
                name = _make_rca(self.asset.name, status=status)
                with self.assertRaises(ServiceError) as ctx:
                    start_rca(name)
                self.assertEqual(ctx.exception.code, ErrorCode.BAD_STATE)
                self.assertIn("bắt đầu phân tích", ctx.exception.message.lower())
                # Status KHÔNG đổi.
                self.assertEqual(
                    frappe.db.get_value("IMM RCA Record", name, "status"), status)


class TestRCASubmitPrecondition(unittest.TestCase):
    """AC3: submit_rca CHỈ từ 'RCA In Progress' (chặn nhảy-cóc từ 'RCA Required')."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-rcasubmit")

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        purge_asset(cls.asset.name)

    def setUp(self):
        frappe.set_user("Administrator")

    def test_submit_rejected_from_rca_required(self):
        name = _make_rca(self.asset.name, status="RCA Required")
        with self.assertRaises(ServiceError) as ctx:
            submit_rca(name, root_cause="Nguyên nhân", corrective_action="Khắc phục")
        self.assertEqual(ctx.exception.code, ErrorCode.BAD_STATE,
                         "submit từ RCA Required = nhảy-cóc → BAD_STATE")
        self.assertEqual(
            frappe.db.get_value("IMM RCA Record", name, "status"), "RCA Required",
            "submit bị chặn KHÔNG được đổi status")

    def test_submit_ok_from_in_progress_with_audit(self):
        name = _make_rca(self.asset.name, status="RCA In Progress")
        before = _rca_audit_count(name, "Completed")
        out = submit_rca(name, root_cause="Nguyên nhân gốc",
                         corrective_action="Hành động khắc phục")
        frappe.db.commit()
        self.assertEqual(out.get("status"), "Completed")
        self.assertEqual(
            frappe.db.get_value("IMM RCA Record", name, "status"), "Completed")
        self.assertEqual(_rca_audit_count(name, "Completed"), before + 1,
                         "submit_rca phải sinh 1 audit 'rca_completed'")


class TestRCACancelTransition(unittest.TestCase):
    """AC4: cancel_rca active-states → 'Cancelled' + audit 'rca_cancelled';
    từ 'Completed'/'Cancelled' → ServiceError."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-rcacancel")

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        purge_asset(cls.asset.name)

    def setUp(self):
        frappe.set_user("Administrator")

    def test_cancel_from_active_states_ok(self):
        for status in ("RCA Required", "RCA In Progress"):
            with self.subTest(status=status):
                name = _make_rca(self.asset.name, status=status)
                before = _rca_audit_count(name, "Cancelled")
                out = cancel_rca(name, reason="Thiết bị đã thanh lý")
                frappe.db.commit()
                self.assertEqual(out.get("status"), "Cancelled")
                self.assertEqual(
                    frappe.db.get_value("IMM RCA Record", name, "status"), "Cancelled")
                self.assertEqual(_rca_audit_count(name, "Cancelled"), before + 1,
                                 "cancel_rca phải sinh 1 audit 'rca_cancelled'")

    def test_cancel_rejected_from_terminal_states(self):
        for status in ("Completed", "Cancelled"):
            with self.subTest(status=status):
                name = _make_rca(self.asset.name, status=status)
                with self.assertRaises(ServiceError) as ctx:
                    cancel_rca(name, reason="x")
                self.assertEqual(ctx.exception.code, ErrorCode.BAD_STATE)
                self.assertEqual(
                    frappe.db.get_value("IMM RCA Record", name, "status"), status)

    def test_cancel_requires_reason(self):
        """BR-12-22: reason bắt buộc — hủy không lý do → VALIDATION, status giữ nguyên."""
        name = _make_rca(self.asset.name, status="RCA In Progress")
        with self.assertRaises(ServiceError) as ctx:
            cancel_rca(name, reason="   ")
        self.assertIn(ctx.exception.code, (ErrorCode.VALIDATION, ErrorCode.BUSINESS_RULE))
        self.assertEqual(
            frappe.db.get_value("IMM RCA Record", name, "status"), "RCA In Progress")


class TestRCATransitionsCapability(unittest.TestCase):
    """AC5 (axis-A guard): user AssetCore cơ bản (không cap corrective) → start/
    submit/cancel raise ServiceError(FORBIDDEN); AssetCore Super Admin → cả 3 OK."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-rcacap")
        cls.base = _ensure_role_user(
            "_rca_base@assetcore.test", ["AssetCore System User"])
        cls.super_admin = _ensure_role_user(
            "_rca_super@assetcore.test", ["AssetCore Super Admin"])

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        purge_asset(cls.asset.name)
        for u in (cls.base, cls.super_admin):
            try:
                frappe.delete_doc("User", u, force=True, ignore_permissions=True)
            except Exception:
                pass

    def setUp(self):
        frappe.set_user("Administrator")

    def test_base_user_blocked_on_all_transitions(self):
        r_start = _make_rca(self.asset.name, status="RCA Required")
        r_submit = _make_rca(self.asset.name, status="RCA In Progress")
        r_cancel = _make_rca(self.asset.name, status="RCA In Progress")
        frappe.set_user(self.base)
        try:
            for label, fn in (
                ("start", lambda: start_rca(r_start)),
                ("submit", lambda: submit_rca(r_submit, root_cause="a",
                                              corrective_action="b")),
                ("cancel", lambda: cancel_rca(r_cancel, reason="x")),
            ):
                with self.subTest(action=label):
                    with self.assertRaises(ServiceError) as ctx:
                        fn()
                    self.assertEqual(ctx.exception.code, ErrorCode.FORBIDDEN,
                                     f"{label}: base user phải bị chặn 403")
                    self.assertEqual(ctx.exception.http_status, 403)
                    # KHÔNG leak raw cap string.
                    self.assertNotIn("corrective.", ctx.exception.message)
        finally:
            frappe.set_user("Administrator")
        # KHÔNG transition nào xảy ra.
        self.assertEqual(
            frappe.db.get_value("IMM RCA Record", r_start, "status"), "RCA Required")
        self.assertEqual(
            frappe.db.get_value("IMM RCA Record", r_submit, "status"), "RCA In Progress")
        self.assertEqual(
            frappe.db.get_value("IMM RCA Record", r_cancel, "status"), "RCA In Progress")

    def test_super_admin_can_do_all_transitions(self):
        r_start = _make_rca(self.asset.name, status="RCA Required")
        r_submit = _make_rca(self.asset.name, status="RCA In Progress")
        r_cancel = _make_rca(self.asset.name, status="RCA In Progress")
        frappe.set_user(self.super_admin)
        try:
            start_rca(r_start)
            frappe.db.commit()
            submit_rca(r_submit, root_cause="Nguyên nhân", corrective_action="Khắc phục")
            frappe.db.commit()
            cancel_rca(r_cancel, reason="Hủy do trùng")
            frappe.db.commit()
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(
            frappe.db.get_value("IMM RCA Record", r_start, "status"), "RCA In Progress")
        self.assertEqual(
            frappe.db.get_value("IMM RCA Record", r_submit, "status"), "Completed")
        self.assertEqual(
            frappe.db.get_value("IMM RCA Record", r_cancel, "status"), "Cancelled")


def _ensure_role_user(email: str, roles: list[str]) -> str:
    """Tạo/ensure 1 User với đúng roles cho test capability (đối xứng
    TestReportIncidentCapGate._ensure_user)."""
    if not frappe.db.exists("User", email):
        doc = frappe.get_doc({
            "doctype": "User", "email": email, "first_name": email.split("@")[0],
            "send_welcome_email": 0, "enabled": 1,
        }).insert(ignore_permissions=True)
    else:
        doc = frappe.get_doc("User", email)
    existing = {r.role for r in doc.get("roles", [])}
    for r in roles:
        if r not in existing:
            doc.append("roles", {"role": r})
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return email


def _make_resolved_incident(asset_name: str, *, severity: str = "Low",
                            clinical_impact: str = "") -> str:
    """Dựng 1 Incident ở trạng thái 'Resolved' qua đúng luồng nghiệp vụ
    (report → acknowledge → start_work → resolve). severity='Low' (mặc định) để
    tránh auto-tạo RCA (orthogonal với reopen)."""
    out = report_incident(
        asset=asset_name, incident_type="Malfunction", severity=severity,
        description="_Test reopen fixture incident description here",
        clinical_impact=clinical_impact,
    )
    frappe.db.commit()
    name = out["name"]
    acknowledge_incident(name)
    start_work(name)
    resolve_incident(name, resolution_notes="_Test resolved for reopen")
    frappe.db.commit()
    return name


def _incident_audit_count(name: str, to_status: str) -> int:
    """Đếm bản ghi IMM Audit Trail của transition Incident (ref = Incident, to_status
    = đích). reopen → to_status='In Progress' from_status='Resolved'."""
    return frappe.db.count("IMM Audit Trail", {
        "ref_doctype": "Incident Report", "ref_name": name, "to_status": to_status,
    })


# ─── CR-WF-12 (Round 12): SSoT guard `_VALID_TRANSITIONS` (incident) ⇄ workflow ──
#
# _VALID_TRANSITIONS là SSoT sinh `allowed_transitions` (get_incident_detail:1084) →
# điều khiển render CTA FE (IncidentDetailView gate status===X && allowed.includes(Y)).
# Guard đối soát edge-by-edge với imm_12_incident_workflow.json để chống drift câm:
# map thừa cạnh workflow-từ-chối = nút DEAD/bypass; map thiếu cạnh workflow-cho-phép
# = CTA ẩn câm (QTV không mở lại được dù workflow cho phép).

def _load_incident_workflow_edges() -> set[tuple[str, str]]:
    """WF = {(state, next_state)} gom-vai (dedupe theo cặp, bỏ chiều role) từ
    imm_12_incident_workflow.json.transitions[]."""
    path = frappe.get_app_path(
        "assetcore", "assetcore", "workflow", "imm_12_incident_workflow.json")
    with open(path, encoding="utf-8") as fh:
        wf = json.load(fh)
    return {(t["state"], t["next_state"]) for t in wf["transitions"]}


# EXCEPTION_EDGES — cạnh workflow CỐ Ý không đưa vào _VALID_TRANSITIONS (không phải
# CTA-FE, có cơ chế thực thi khác). Mọi entry PHẢI kèm rationale.
_INCIDENT_EXCEPTION_EDGES: dict[tuple[str, str], str] = {
    ("RCA Required", "Closed"):
        "auto-advance _advance_incident_after_rca (services/imm12.py:1475) sau khi "
        "RCA Record → Completed (RC-04) — hệ thống tự đẩy, KHÔNG CTA-FE; RCA có map "
        "CTA riêng _RCA_VALID_TRANSITIONS trên IMM RCA Record.",
}


def _incident_service_edges() -> set[tuple[str, str]]:
    """SVC = {(f, t) | t ∈ _VALID_TRANSITIONS[f]}."""
    return {(f, t) for f, tos in _VALID_TRANSITIONS.items() for t in tos}


class TestIncidentAllowedTransitions(unittest.TestCase):
    """CR-WF-12 INVARIANT (mirror TestRCAAllowedTransitions): `_VALID_TRANSITIONS`
    (incident) ⇄ imm_12_incident_workflow.json. RED trước fix (bắt drift a+b),
    GREEN sau đối soát."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-incallowed")

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        purge_asset(cls.asset.name)

    def setUp(self):
        frappe.set_user("Administrator")

    def test_inv1_service_subset_workflow(self):
        """INV-1 (SVC ⊆ WF): mọi cạnh trong _VALID_TRANSITIONS PHẢI là cạnh THẬT của
        workflow → chặn nút dead/bypass. RED trước fix: ('In Progress','RCA Required')
        ∈ SVC \\ WF (drift b — service map chào đích workflow từ chối)."""
        svc = _incident_service_edges()
        wf = _load_incident_workflow_edges()
        extra = svc - wf
        self.assertEqual(
            extra, set(),
            f"_VALID_TRANSITIONS có cạnh KHÔNG tồn tại trong workflow (dead/bypass): "
            f"{extra}")

    def test_inv2_workflow_subset_service_or_exception(self):
        """INV-2 (WF ⊆ SVC ∪ EXCEPTION): mọi cạnh workflow HOẶC là CTA (∈ SVC) HOẶC là
        exception có rationale. RED trước fix: ('Resolved','In Progress') ∈ WF \\
        (SVC ∪ EXCEPTION) (drift a — CTA 'Mở lại' ẩn câm)."""
        svc = _incident_service_edges()
        wf = _load_incident_workflow_edges()
        exc = set(_INCIDENT_EXCEPTION_EDGES.keys())
        uncovered = wf - (svc | exc)
        self.assertEqual(
            uncovered, set(),
            f"Cạnh workflow KHÔNG được surface trong _VALID_TRANSITIONS và KHÔNG khai "
            f"EXCEPTION_EDGES (drift câm): {uncovered}")

    def test_exception_edges_have_rationale(self):
        """Mọi EXCEPTION_EDGE phải (a) là cạnh workflow THẬT, (b) có rationale, (c)
        KHÔNG nằm trong SVC (nếu đã surface CTA thì không phải exception)."""
        wf = _load_incident_workflow_edges()
        svc = _incident_service_edges()
        for edge, rationale in _INCIDENT_EXCEPTION_EDGES.items():
            self.assertIn(edge, wf, f"EXCEPTION_EDGE {edge} không phải cạnh workflow")
            self.assertTrue(rationale.strip(), f"EXCEPTION_EDGE {edge} thiếu rationale")
            self.assertNotIn(edge, svc, f"EXCEPTION_EDGE {edge} đã ∈ SVC — mâu thuẫn")

    def test_map_matches_core_doc_spec(self):
        """_VALID_TRANSITIONS khớp CHÍNH XÁC Core Doc (04 §3.0, Round 12)."""
        self.assertEqual(_VALID_TRANSITIONS.get("Open"),
                         ["Acknowledged", "Cancelled"])
        self.assertEqual(_VALID_TRANSITIONS.get("Acknowledged"),
                         ["In Progress", "Cancelled"])
        self.assertEqual(_VALID_TRANSITIONS.get("In Progress"),
                         ["Resolved", "Cancelled"])
        self.assertEqual(_VALID_TRANSITIONS.get("Resolved"),
                         ["Closed", "RCA Required", "In Progress"])

    def test_no_dead_or_bypass_cta_for_every_status(self):
        """TC-no-bypass: mọi đích trong allowed_transitions (cho MỌI status) phải là
        cạnh workflow thật → click CTA đi qua apply_workflow không dead-fail/bypass."""
        wf = _load_incident_workflow_edges()
        for status, targets in _VALID_TRANSITIONS.items():
            for target in targets:
                with self.subTest(edge=(status, target)):
                    self.assertIn(
                        (status, target), wf,
                        f"allowed_transitions[{status}]→{target} KHÔNG có cạnh workflow")

    def test_get_incident_detail_emits_allowed_transitions_resolved(self):
        """TC-allowed-transitions-resolved: get_incident_detail trên phiếu Resolved →
        allowed_transitions KHỚP _VALID_TRANSITIONS[Resolved] (gồm 'In Progress' =
        surface 'Mở lại'); không thừa/thiếu."""
        name = _make_resolved_incident(self.asset.name)
        data = get_incident_detail(name)
        self.assertIn("allowed_transitions", data)
        self.assertEqual(data["allowed_transitions"],
                         _VALID_TRANSITIONS.get("Resolved"))
        self.assertIn("In Progress", data["allowed_transitions"],
                      "Resolved phải surface 'In Progress' (Mở lại điều tra)")

    def test_get_incident_detail_rca_required_no_fe_cta(self):
        """TC-rca-required-no-fe-cta: get_incident_detail trên phiếu 'RCA Required' →
        allowed_transitions == [] (đóng CHỈ qua auto-advance RCA — EXCEPTION_EDGE), mã
        hoá exception thành hành vi."""
        name = _make_resolved_incident(self.asset.name)
        # Đẩy tay sang 'RCA Required' (desk workflow "Yêu cầu RCA"); service KHÔNG có
        # setter status='RCA Required' nên set trực tiếp để dựng fixture trạng thái.
        frappe.db.set_value("Incident Report", name,
                            {"status": "RCA Required", "workflow_state": "RCA Required"},
                            update_modified=False)
        frappe.db.commit()
        data = get_incident_detail(name)
        self.assertEqual(data["allowed_transitions"], [],
                         "RCA Required KHÔNG có CTA-FE (đóng qua auto-advance)")


class TestIncidentReopen(unittest.TestCase):
    """CR-WF-12 (BR-12-23) — reopen_incident: Resolved → In Progress ("Mở lại điều
    tra"). Mirror TestRCAStartTransition + TestIncidentApiRbac (cap-403 tại API)."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-reopen")
        # Users mang role THẬT cho ma trận cap axis-A (reopen cap = incident.close =
        # submit perm). Corrective User chỉ có write (incident.acknowledge) → cap-403.
        cls.base = _ensure_role_user(
            "_reopen_base@assetcore.test", ["AssetCore System User"])
        cls.corr_user = _ensure_role_user(
            "_reopen_corr_usr@assetcore.test", ["Corrective User"])
        cls.corr_mgr = _ensure_role_user(
            "_reopen_corr_mgr@assetcore.test", ["Corrective Manager"])
        cls.super_admin = _ensure_role_user(
            "_reopen_super@assetcore.test", ["AssetCore Super Admin"])

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        purge_asset(cls.asset.name)
        for u in (cls.base, cls.corr_user, cls.corr_mgr, cls.super_admin):
            try:
                frappe.delete_doc("User", u, force=True, ignore_permissions=True)
            except Exception:
                pass

    def setUp(self):
        frappe.set_user("Administrator")

    def test_tc_reopen_01_resolved_to_in_progress_ok(self):
        """TC-12-REOPEN-01: Resolved → In Progress OK; return {name, status:'In
        Progress'}; 1 audit IMM Audit Trail from='Resolved' to='In Progress' chứa
        'Mở lại điều tra'."""
        name = _make_resolved_incident(self.asset.name)
        before = _incident_audit_count(name, "In Progress")
        out = reopen_incident(name, reason="Lỗi tái diễn — cần điều tra thêm")
        frappe.db.commit()
        self.assertEqual(out.get("status"), "In Progress")
        self.assertEqual(out.get("name"), name)
        self.assertEqual(
            frappe.db.get_value("Incident Report", name, "status"), "In Progress")
        self.assertEqual(_incident_audit_count(name, "In Progress"), before + 1,
                         "reopen phải sinh đúng 1 audit 'Mở lại điều tra'")
        row = frappe.get_all(
            "IMM Audit Trail",
            filters={"ref_doctype": "Incident Report", "ref_name": name,
                     "to_status": "In Progress"},
            fields=["change_summary", "from_status"],
            order_by="creation desc", limit=1)[0]
        self.assertEqual(row["from_status"], "Resolved")
        self.assertIn("Mở lại điều tra", row["change_summary"])

    def test_tc_reopen_01b_allowed_transitions_refetch_after_reopen(self):
        """TC-12-REOPEN-01 (refetch): sau reopen, get_incident_detail trả
        allowed_transitions của state mới ('In Progress')."""
        name = _make_resolved_incident(self.asset.name)
        reopen_incident(name, reason="Mở lại để kiểm tra lại")
        frappe.db.commit()
        data = get_incident_detail(name)
        self.assertEqual(data["allowed_transitions"],
                         _VALID_TRANSITIONS.get("In Progress"))

    def test_tc_reopen_02_bad_state_when_not_resolved(self):
        """TC-12-REOPEN-02: status ≠ Resolved (Open) → IMM12_BAD_STATE (message_code
        stable, http 409 — bucket CONFLICT qua nthrow(MSG.IMM12_BAD_STATE), đối xứng
        mọi transition Incident khác); status giữ nguyên."""
        out = report_incident(
            asset=self.asset.name, incident_type="Malfunction", severity="Low",
            description="_Test reopen bad-state incident description here")
        frappe.db.commit()
        name = out["name"]
        with self.assertRaises(ServiceError) as ctx:
            reopen_incident(name, reason="Không hợp lệ vì đang Open")
        self.assertEqual(ctx.exception.message_code, "IMM12-BAD-STATE")
        self.assertEqual(ctx.exception.http_status, 409)
        self.assertEqual(
            frappe.db.get_value("Incident Report", name, "status"), "Open")

    def test_tc_reopen_03_reason_required(self):
        """TC-12-REOPEN-03: reason rỗng/space → IMM12_REOPEN_REASON_REQUIRED (422
        bucket); status giữ 'Resolved'."""
        name = _make_resolved_incident(self.asset.name)
        with self.assertRaises(ServiceError) as ctx:
            reopen_incident(name, reason="   ")
        self.assertIn(ctx.exception.code,
                      (ErrorCode.BUSINESS_RULE, ErrorCode.VALIDATION))
        self.assertEqual(ctx.exception.message_code, "IMM12-REOPEN-REASON-REQUIRED")
        self.assertEqual(
            frappe.db.get_value("Incident Report", name, "status"), "Resolved")

    def test_tc_reopen_04_cap_gate_axis_a(self):
        """TC-12-REOPEN-04: cap `incident.close` tại API (parity close_incident =
        ("Incident Report","submit")). base + Corrective User (chỉ write) → cap-403;
        Corrective Manager + AssetCore Super Admin (holder submit) → OK.

        Ghi chú (grounded @DocPerm): submit holder = {Corrective Manager, AssetCore
        Super Admin} (incident_report.json). System Manager KHÔNG có DocPerm submit →
        KHÔNG phải cap holder (dù workflow "Mở lại điều tra" allowed=System Manager) —
        service transition bypass workflow engine, cap-gate là authorization thật, đối
        xứng close_incident. Xem open issue role-set workflow⇄cap."""
        from assetcore.api.imm12 import reopen_incident as api_reopen

        # Denied: base + Corrective User (chỉ có write, thiếu submit → thiếu
        # incident.close).
        for user in (self.base, self.corr_user):
            name = _make_resolved_incident(self.asset.name)
            frappe.set_user(user)
            try:
                res = api_reopen(name, reason="_Test reopen forbidden")
            finally:
                frappe.set_user("Administrator")
            self.assertFalse(res.get("success"),
                             f"{user} KHÔNG được reopen (thiếu incident.close)")
            self.assertEqual(res.get("http_status"), 403)
            self.assertEqual(
                frappe.db.get_value("Incident Report", name, "status"), "Resolved",
                f"{user} bị chặn → status giữ Resolved")

        # Allowed: Corrective Manager + AssetCore Super Admin (holder submit).
        for user in (self.corr_mgr, self.super_admin):
            name = _make_resolved_incident(self.asset.name)
            frappe.set_user(user)
            try:
                res = api_reopen(name, reason="_Test reopen allowed")
            finally:
                frappe.set_user("Administrator")
            frappe.db.commit()
            self.assertTrue(res.get("success"),
                            f"{user} phải reopen được, nhận: {res}")
            self.assertEqual(
                frappe.db.get_value("Incident Report", name, "status"), "In Progress")

    def test_tc_reopen_05_does_not_restore_asset(self):
        """TC-12-REOPEN-05: reopen KHÔNG đổi asset lifecycle_status — asset Out of
        Service (Critical/OOS) vẫn Out of Service sau reopen."""
        name = _make_resolved_incident(self.asset.name)
        # Đặt asset về Out of Service (mô phỏng Critical/OOS chưa restore ở Resolved).
        frappe.db.set_value("AC Asset", self.asset.name,
                            "lifecycle_status", "Out of Service")
        frappe.db.commit()
        reopen_incident(name, reason="Mở lại — asset vẫn ngưng dùng")
        frappe.db.commit()
        self.assertEqual(
            frappe.db.get_value("AC Asset", self.asset.name, "lifecycle_status"),
            "Out of Service",
            "reopen KHÔNG được restore asset (chỉ Close mới restore)")
        # Dọn: trả asset về Active để không nhiễu test khác dùng chung asset.
        frappe.db.set_value("AC Asset", self.asset.name, "lifecycle_status", "Active")
        frappe.db.commit()


# ── CR-WF-12-RCA: desk==endpoint parity cho luồng RCA ────────────────────────
#    Bug (Trục A): Corrective Manager có cap corrective.write (endpoint start_rca/
#    submit_rca cho phép qua _require_rca_cap) NHƯNG workflow JSON transition
#    'Bắt đầu phân tích RCA' + 'Hoàn thành RCA' THIẾU role 'Corrective Manager'
#    → nút desk không hiện/không bấm được = asymmetry RBAC. Nguyên tắc đã áp cho
#    'Hủy RCA' (đủ 4 role) phải áp nốt Start/Complete.
#    Ba invariant reconcile SSoT⇄workflow + guard chống drift. Pure-JSON parse,
#    mirror test_imm08.TestPMDetailAllowedTransitions (codomain reconcile).

def _load_rca_workflow_source() -> dict:
    """Đọc THẲNG source workflow JSON (assetcore/workflow/imm_12_rca_workflow.json)."""
    from pathlib import Path

    path = (
        Path(frappe.get_app_path("assetcore"))
        / "assetcore" / "workflow" / "imm_12_rca_workflow.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def _load_rca_workflow_fixture() -> dict:
    """Đọc block 'IMM-12 RCA Workflow' trong fixtures/workflow.json (fresh-install seed)."""
    from pathlib import Path

    path = Path(frappe.get_app_path("assetcore")) / "fixtures" / "workflow.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for wf in data:
        if wf.get("doctype") == "Workflow" and wf.get("name") == "IMM-12 RCA Workflow":
            return wf
    raise AssertionError("fixtures/workflow.json thiếu 'IMM-12 RCA Workflow'")


def _roles_resolving_cap(cap: str) -> set[str]:
    """Roles resolve `cap` ĐỘNG qua rbac.CAPABILITY_MAP → DocPerm/Custom DocPerm.

    KHÔNG hardcode role-name (chống RBAC dead-gate): capability corrective.write bind
    (Incident Report, write); role có write=1 trên Incident Report = role resolve cap.
    Mirror ngữ nghĩa rbac.can() = frappe.has_permission(dt, ptype).
    """
    from assetcore.services.shared.rbac import CAPABILITY_MAP

    dt, ptype = CAPABILITY_MAP[cap]
    roles: set[str] = set()
    for src in ("DocPerm", "Custom DocPerm"):
        for r in frappe.get_all(
            src, filters=[["parent", "=", dt], [ptype, "=", 1]], fields=["role"]
        ):
            if r.get("role"):
                roles.add(r["role"])
    return roles


_RCA_MANAGE_ACTIONS = ("Bắt đầu phân tích RCA", "Hoàn thành RCA", "Hủy RCA")
_RCA_ADMIN_OVERRIDE = {"AssetCore Super Admin", "System Manager"}


class TestRcaWorkflowParity(unittest.TestCase):
    """INV-RCA-PARITY-A/B/C + admin-override — reconcile SSoT⇄workflow JSON.
    (Core Doc: docs/imm-12/07_Testing_QA.md §TestRcaWorkflowParity, Round 30.)

    Không cần fixture DB (pure-JSON parse). RED-before: Start/Complete thiếu
    'Corrective Manager' → INV-B đỏ đúng chỗ. GREEN-after: đủ 4 role mỗi action.
    """

    def _from_collections_defaultdict(self):
        from collections import defaultdict
        return defaultdict

    # INV-RCA-PARITY-A ─ reconcile codomain(state→{next_state}) == _RCA_VALID_TRANSITIONS
    def test_tc_rca_parity_a_codomain_reconcile(self):
        data = _load_rca_workflow_source()
        # Init codomain từ states[] → terminal (Completed/Cancelled) = ∅ có mặt.
        codomain = {s["state"]: set() for s in data["states"]}
        for t in data["transitions"]:
            codomain.setdefault(t["state"], set()).add(t["next_state"])
        expected = {st: set(nx) for st, nx in _RCA_VALID_TRANSITIONS.items()}
        self.assertEqual(
            set(codomain.keys()), set(expected.keys()),
            "Key-set states[] workflow JSON PHẢI == _RCA_VALID_TRANSITIONS keys.")
        for st, nx in expected.items():
            self.assertEqual(
                codomain.get(st, set()), nx,
                f"DRIFT '{st}': JSON codomain {sorted(codomain.get(st, set()))} "
                f"≠ _RCA_VALID_TRANSITIONS {sorted(nx)}.")
        # Terminal states rỗng (không transition ra).
        self.assertEqual(codomain["Completed"], set(), "Completed phải terminal (∅).")
        self.assertEqual(codomain["Cancelled"], set(), "Cancelled phải terminal (∅).")

    # INV-RCA-PARITY-B ─ desk==endpoint (động): mỗi action ⊇ roles(corrective.write) ∪ admin
    def test_tc_rca_parity_b_desk_equals_endpoint(self):
        from assetcore.services.imm12 import _CAP_RCA_MANAGE

        required = _roles_resolving_cap(_CAP_RCA_MANAGE) | _RCA_ADMIN_OVERRIDE
        data = _load_rca_workflow_source()
        defaultdict = self._from_collections_defaultdict()
        by_action: dict = defaultdict(set)
        for t in data["transitions"]:
            by_action[t["action"]].add(t["allowed"])
        for action in _RCA_MANAGE_ACTIONS:
            with self.subTest(action=action):
                allowed = by_action.get(action, set())
                missing = required - allowed
                self.assertFalse(
                    missing,
                    f"desk≠endpoint: action '{action}' allowed={sorted(allowed)} "
                    f"THIẾU role resolve-cap {sorted(missing)} "
                    f"(required={sorted(required)}).")

    # TC-RCA-PARITY-B-red-before → SAU fix: Start + Complete ⊇ {Corrective User, Corrective Manager}
    def test_tc_rca_parity_b_start_complete_contains_both_corrective(self):
        data = _load_rca_workflow_source()
        for action in ("Bắt đầu phân tích RCA", "Hoàn thành RCA"):
            allowed = {t["allowed"] for t in data["transitions"]
                       if t["action"] == action}
            for role in ("Corrective User", "Corrective Manager"):
                with self.subTest(action=action, role=role):
                    self.assertIn(
                        role, allowed,
                        f"Action '{action}' PHẢI cho '{role}' (desk==endpoint; "
                        f"corrective.write = quyền quản RCA).")

    # INV-RCA-PARITY-C ─ fresh-install seed: fixtures tuple-set == source tuple-set
    def test_tc_rca_parity_c_source_equals_fixture(self):
        src = _load_rca_workflow_source()
        fix = _load_rca_workflow_fixture()
        src_t = {(t["state"], t["action"], t["next_state"], t["allowed"])
                 for t in src["transitions"]}
        fix_t = {(t["state"], t["action"], t["next_state"], t["allowed"])
                 for t in fix["transitions"]}
        self.assertEqual(
            src_t, fix_t,
            "source imm_12_rca_workflow.json ≠ fixtures/workflow.json (transition "
            f"tuple-set lệch): chỉ-source={sorted(src_t - fix_t)} "
            f"chỉ-fixture={sorted(fix_t - src_t)}.")
        # states khớp (state + doc_status).
        src_s = {(s["state"], s["doc_status"]) for s in src["states"]}
        fix_s = {(s["state"], s["doc_status"]) for s in fix["states"]}
        self.assertEqual(src_s, fix_s, "states[] source ≠ fixtures.")

    # TC-RCA-ADMIN-OVERRIDE ─ không regress admin-override (parity test_workflows 22/22)
    def test_tc_rca_admin_override_present_every_group(self):
        data = _load_rca_workflow_source()
        defaultdict = self._from_collections_defaultdict()
        groups: dict = defaultdict(set)
        for t in data["transitions"]:
            groups[(t["state"], t["action"], t["next_state"])].add(t["allowed"])
        for key, roles in groups.items():
            for admin in _RCA_ADMIN_OVERRIDE:
                with self.subTest(group=key, admin=admin):
                    self.assertIn(
                        admin, roles,
                        f"Transition group {key} thiếu admin-override '{admin}'.")


class TestRCAManagerCanStart(unittest.TestCase):
    """TC-RCA-MGR-CAN-START (behavior end-to-end): user Corrective Manager mở RCA
    → get_rca can_manage_rca==1 VÀ start_rca thành công (endpoint path). Cùng với
    invariant desk==endpoint ở trên → guard cap↔role↔workflow không lệch."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-rcaparity")
        cls.mgr = cls._ensure_user("_test_rca_mgr@assetcore.test", ["Corrective Manager"])

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        purge_asset(cls.asset.name)
        try:
            frappe.delete_doc("User", cls.mgr, force=True, ignore_permissions=True)
        except Exception:
            pass

    @staticmethod
    def _ensure_user(email: str, roles: list[str]) -> str:
        if not frappe.db.exists("User", email):
            doc = frappe.get_doc({
                "doctype": "User", "email": email, "first_name": email.split("@")[0],
                "send_welcome_email": 0, "enabled": 1,
            }).insert(ignore_permissions=True)
        else:
            doc = frappe.get_doc("User", email)
        existing = {r.role for r in doc.get("roles", [])}
        for r in roles:
            if r not in existing:
                doc.append("roles", {"role": r})
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        return email

    def setUp(self):
        frappe.set_user("Administrator")

    def _rca_required(self) -> str:
        from assetcore.services.imm12 import create_rca

        ir = report_incident(
            asset=self.asset.name, incident_type="Malfunction", severity="High",
            description="_Test RCA desk-endpoint parity incident description here",
        )
        create_rca(ir["name"])
        frappe.db.commit()
        rca_name = frappe.db.get_value("Incident Report", ir["name"], "rca_record")
        self.assertTrue(rca_name, "create_rca phải set incident.rca_record")
        self.assertEqual(
            frappe.db.get_value("IMM RCA Record", rca_name, "status"), "RCA Required")
        return rca_name

    def test_tc_rca_mgr_can_start(self):
        rca_name = self._rca_required()
        frappe.set_user(self.mgr)
        try:
            detail = get_rca(rca_name)
            self.assertEqual(
                detail["can_manage_rca"], 1,
                "Corrective Manager PHẢI can_manage_rca (cap corrective.write).")
            out = start_rca(rca_name)
        finally:
            frappe.set_user("Administrator")
        frappe.db.commit()
        self.assertEqual(out["status"], "RCA In Progress")
        # workflow_state đồng bộ (không dual-track drift).
        self.assertEqual(
            frappe.db.get_value("IMM RCA Record", rca_name, "workflow_state"),
            "RCA In Progress",
            "start_rca phải đồng bộ workflow_state (cap↔role↔workflow parity).")


# ── BR-12-24 / CR-WF-12-RCA-ENTRY: request_rca (Resolved → RCA Required) ───────
#   Surface cạnh workflow "Yêu cầu RCA" thành CTA server-driven — cấp DRIVER THẬT
#   cho allowed_transitions['RCA Required'] đang advertise-mà-câm (hidden-CTA).
#   Mirror TestIncidentReopen (cap-403 tại API) + TestRcaWorkflowParity (desk⊆endpoint).
#   Cap = compliance.submit (Core Doc 05 §6c: role-set {Compliance Manager, Super
#   Admin} ⊆ workflow "Yêu cầu RCA" allowed {Compliance Manager, System Manager,
#   Super Admin} → KHÔNG false-clickable). KHÔNG đổi _VALID_TRANSITIONS/workflow JSON.

_CAP_REQUEST_RCA = "compliance.submit"
_WF_ACTION_REQUEST_RCA = "Yêu cầu RCA"


def _rca_count_for_incident(incident_name: str) -> int:
    """Số IMM RCA Record liên kết 1 Incident (idempotent guard — reuse == 1)."""
    return frappe.db.count("IMM RCA Record", {"incident_report": incident_name})


def _workflow_allowed_roles(action: str) -> set[str]:
    """Role-set desk cho 1 action trong imm_12_incident_workflow.json (union các
    transition-row cùng action, gom-vai). Dùng cho INVARIANT cap ⊆ workflow."""
    path = frappe.get_app_path(
        "assetcore", "assetcore", "workflow", "imm_12_incident_workflow.json")
    with open(path, encoding="utf-8") as fh:
        wf = json.load(fh)
    return {t["allowed"] for t in wf["transitions"] if t["action"] == action}


class TestIncidentRequestRca(unittest.TestCase):
    """BR-12-24 (CR-WF-12-RCA-ENTRY) — request_rca: Resolved → RCA Required
    ("Yêu cầu phân tích RCA") qua apply_workflow + sync status; idempotent RCA
    reuse; audit IMM Audit Trail (Resolved→RCA Required). Cap-gate compliance.submit
    tại API (parity ack/close). ENTRY của nhánh RCA Required; EXIT =
    _advance_incident_after_rca (auto-close sau RCA Completed)."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-reqrca")
        # Ma trận cap axis-A (cap = compliance.submit = ("IMM CAPA Record","submit")):
        #  base / Corrective User / Compliance User (chỉ create) → cap-403;
        #  Compliance Manager + AssetCore Super Admin (submit=1) → OK.
        cls.base = _ensure_role_user(
            "_reqrca_base@assetcore.test", ["AssetCore System User"])
        cls.corr_user = _ensure_role_user(
            "_reqrca_corr_usr@assetcore.test", ["Corrective User"])
        cls.comp_user = _ensure_role_user(
            "_reqrca_comp_usr@assetcore.test", ["Compliance User"])
        cls.comp_mgr = _ensure_role_user(
            "_reqrca_comp_mgr@assetcore.test", ["Compliance Manager"])
        cls.super_admin = _ensure_role_user(
            "_reqrca_super@assetcore.test", ["AssetCore Super Admin"])
        cls.sys_mgr = _ensure_role_user(
            "_reqrca_sysmgr@assetcore.test", ["System Manager"])

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        purge_asset(cls.asset.name)
        for u in (cls.base, cls.corr_user, cls.comp_user, cls.comp_mgr,
                  cls.super_admin, cls.sys_mgr):
            try:
                frappe.delete_doc("User", u, force=True, ignore_permissions=True)
            except Exception:
                pass

    def setUp(self):
        frappe.set_user("Administrator")

    # TC-12-REQRCA-01 — happy path (Resolved → RCA Required)
    def test_request_rca_resolved_to_rca_required(self):
        """Resolved → RCA Required OK; status Select VÀ workflow_state == 'RCA
        Required' (qua apply_workflow, KHÔNG chỉ 1 field); rca_record link; return
        {name, status, rca_record}; 1 audit from='Resolved' to='RCA Required'
        change_summary chứa 'Yêu cầu RCA'; event_type == 'Incident' (KHÔNG Select mới)."""
        name = _make_resolved_incident(self.asset.name, severity="Medium")
        before = _incident_audit_count(name, "RCA Required")
        out = request_rca(name, rca_reason="Cần điều tra nguyên nhân gốc theo NĐ98")
        frappe.db.commit()
        self.assertEqual(out.get("status"), "RCA Required")
        self.assertEqual(out.get("name"), name)
        self.assertTrue(out.get("rca_record"), "request_rca phải trả rca_record")
        row = frappe.db.get_value(
            "Incident Report", name,
            ["status", "workflow_state", "rca_record"], as_dict=True)
        self.assertEqual(row.status, "RCA Required", "status Select phải sync")
        self.assertEqual(row.workflow_state, "RCA Required",
                         "workflow_state phải sync (dual-track, KHÔNG chỉ 1 field)")
        self.assertEqual(row.rca_record, out["rca_record"])
        self.assertTrue(frappe.db.exists("IMM RCA Record", row.rca_record))
        self.assertEqual(_incident_audit_count(name, "RCA Required"), before + 1,
                         "request_rca phải sinh đúng 1 audit 'Yêu cầu RCA'")
        arow = frappe.get_all(
            "IMM Audit Trail",
            filters={"ref_doctype": "Incident Report", "ref_name": name,
                     "to_status": "RCA Required"},
            fields=["change_summary", "from_status", "event_type"],
            order_by="creation desc", limit=1)[0]
        self.assertEqual(arow["from_status"], "Resolved")
        self.assertIn("Yêu cầu RCA", arow["change_summary"])
        self.assertEqual(arow["event_type"], "Incident",
                         "KHÔNG thêm event_type Select mới (precedent reopen D4)")

    # TC-12-REQRCA-02 — wrong state rejected (không side-effect)
    def test_request_rca_wrong_state_rejected(self):
        """status Open/Acknowledged/In Progress/Closed → IMM12_REQUEST_RCA_BAD_STATE
        (422 bucket, MSG MỚI — KHÔNG IMM12_BAD_STATE=409); status GIỮ nguyên
        (KHÔNG đổi status, KHÔNG tạo RCA)."""
        # Open
        open_ir = report_incident(
            asset=self.asset.name, incident_type="Malfunction", severity="Low",
            description="_Test request_rca wrong-state Open incident here")["name"]
        # Acknowledged
        ack_ir = report_incident(
            asset=self.asset.name, incident_type="Malfunction", severity="Low",
            description="_Test request_rca wrong-state Acknowledged incident here")["name"]
        acknowledge_incident(ack_ir)
        # In Progress
        inprog_ir = report_incident(
            asset=self.asset.name, incident_type="Malfunction", severity="Low",
            description="_Test request_rca wrong-state In Progress incident here")["name"]
        acknowledge_incident(inprog_ir)
        start_work(inprog_ir)
        # Closed (Low severity → close không cần RCA)
        closed_ir = _make_resolved_incident(self.asset.name, severity="Low")
        close_incident(closed_ir)
        frappe.db.commit()

        for name, expect_status in (
            (open_ir, "Open"), (ack_ir, "Acknowledged"),
            (inprog_ir, "In Progress"), (closed_ir, "Closed"),
        ):
            with self.subTest(status=expect_status):
                rca_before = _rca_count_for_incident(name)
                with self.assertRaises(ServiceError) as ctx:
                    request_rca(name, rca_reason="Không hợp lệ vì sai trạng thái")
                self.assertEqual(ctx.exception.message_code,
                                 "IMM12-REQUEST-RCA-BAD-STATE")
                self.assertEqual(ctx.exception.http_status, 422)
                self.assertEqual(
                    frappe.db.get_value("Incident Report", name, "status"),
                    expect_status, "status GIỮ nguyên (không side-effect)")
                self.assertEqual(_rca_count_for_incident(name), rca_before,
                                 "KHÔNG tạo RCA khi reject sai trạng thái")

    # TC-12-REQRCA — rca_reason bắt buộc
    def test_request_rca_reason_required(self):
        """rca_reason rỗng/space → IMM12_RCA_REASON_REQUIRED (422 bucket); status
        GIỮ 'Resolved'; KHÔNG tạo RCA."""
        name = _make_resolved_incident(self.asset.name, severity="Medium")
        rca_before = _rca_count_for_incident(name)
        with self.assertRaises(ServiceError) as ctx:
            request_rca(name, rca_reason="   ")
        self.assertEqual(ctx.exception.message_code, "IMM12-RCA-REASON-REQUIRED")
        self.assertEqual(ctx.exception.http_status, 422)
        self.assertEqual(
            frappe.db.get_value("Incident Report", name, "status"), "Resolved")
        self.assertEqual(_rca_count_for_incident(name), rca_before,
                         "reason rỗng → KHÔNG tạo RCA")

    # TC-12-REQRCA-05 — idempotent RCA reuse (KHÔNG tạo trùng)
    def test_request_rca_idempotent_existing_rca(self):
        """Incident đã có rca_record hợp lệ (High severity auto-tạo ở resolve) →
        request_rca tái dùng, KHÔNG tạo RCA trùng (count IMM RCA Record theo
        incident_report == 1, KHÔNG 2); rca_record giữ nguyên; KHÔNG raise 409."""
        name = _make_resolved_incident(self.asset.name, severity="High")
        existing = frappe.db.get_value("Incident Report", name, "rca_record")
        self.assertTrue(existing, "High severity resolve phải auto-tạo RCA")
        self.assertEqual(_rca_count_for_incident(name), 1)
        out = request_rca(name, rca_reason="Yêu cầu chính thức phân tích RCA")
        frappe.db.commit()
        self.assertEqual(out["rca_record"], existing,
                         "PHẢI tái dùng RCA cũ, KHÔNG tạo mới")
        self.assertEqual(_rca_count_for_incident(name), 1, "KHÔNG tạo RCA trùng")
        self.assertEqual(out["status"], "RCA Required")

    # TC-12-REQRCA-04 — cap-403 (base / Corrective User / Compliance User)
    def test_request_rca_forbidden_without_cap(self):
        """base + Corrective User + Compliance User (thiếu compliance.submit) →
        cap-403 in-handler (HTTP-200 body http_status=403), KHÔNG leak raw cap;
        status GIỮ 'Resolved' (KHÔNG side-effect)."""
        from assetcore.api.imm12 import request_rca as api_request_rca

        for user in (self.base, self.corr_user, self.comp_user):
            name = _make_resolved_incident(self.asset.name, severity="Medium")
            frappe.set_user(user)
            try:
                res = api_request_rca(name, rca_reason="_Test forbidden request_rca")
            finally:
                frappe.set_user("Administrator")
            self.assertFalse(res.get("success"),
                             f"{user} thiếu compliance.submit → cap-403")
            self.assertEqual(res.get("http_status"), 403)
            # KHÔNG leak raw cap 'compliance.submit' trong message.
            self.assertNotIn("compliance.submit", str(res.get("error") or ""))
            self.assertEqual(
                frappe.db.get_value("Incident Report", name, "status"), "Resolved",
                f"{user} bị chặn → status giữ Resolved (không side-effect)")

    # TC-12-REQRCA — cap-holder execute (admin-override)
    def test_request_rca_admin_override(self):
        """Cap-holder {Compliance Manager, AssetCore Super Admin} (compliance.submit
        = DocPerm submit IMM CAPA Record) thực thi được qua API → Resolved →
        RCA Required. (Core Doc 05 §6c: OK-set = {Compliance Manager, Super Admin};
        Super Admin = QTV admin-override.)"""
        from assetcore.api.imm12 import request_rca as api_request_rca

        for user in (self.comp_mgr, self.super_admin):
            name = _make_resolved_incident(self.asset.name, severity="Medium")
            frappe.set_user(user)
            try:
                res = api_request_rca(name, rca_reason="_Test cap-holder request_rca")
            finally:
                frappe.set_user("Administrator")
            frappe.db.commit()
            self.assertTrue(res.get("success"),
                            f"{user} (compliance.submit) phải thực thi được, nhận: {res}")
            self.assertEqual(
                frappe.db.get_value("Incident Report", name, "status"),
                "RCA Required")

    # TC-12-REQRCA — pure System Manager residual-hidden (Core Doc 05 §6c residual)
    def test_request_rca_system_manager_residual_cap403(self):
        """pure-System Manager ∉ compliance.submit → cap-403 trên SPA/endpoint
        (residual an-toàn, ⊆-hẹp KHÔNG false-clickable; phủ qua Super Admin + desk
        admin-override). Lock hành vi residual Core Doc 05 §6c."""
        from assetcore.api.imm12 import request_rca as api_request_rca

        name = _make_resolved_incident(self.asset.name, severity="Medium")
        frappe.set_user(self.sys_mgr)
        try:
            res = api_request_rca(name, rca_reason="_Test sysmgr residual")
        finally:
            frappe.set_user("Administrator")
        self.assertFalse(res.get("success"),
                         "pure System Manager ∉ compliance.submit → cap-403")
        self.assertEqual(res.get("http_status"), 403)
        self.assertEqual(
            frappe.db.get_value("Incident Report", name, "status"), "Resolved")

    # TC — allowed_transitions advertise + DRIVER THẬT (đóng hidden-CTA)
    def test_allowed_transitions_rca_required_has_driver(self):
        """get_incident_detail(Resolved).allowed_transitions chứa 'RCA Required' VÀ
        request_rca thực thi thành công — CTA advertise giờ CÓ driver THẬT.
        RED-before: chưa có request_rca (import fail) = dead-CTA → GREEN-after."""
        name = _make_resolved_incident(self.asset.name, severity="Medium")
        data = get_incident_detail(name)
        self.assertIn("RCA Required", data["allowed_transitions"],
                      "allowed_transitions[Resolved] PHẢI advertise 'RCA Required'")
        out = request_rca(name, rca_reason="Driver THẬT cho CTA advertise")
        frappe.db.commit()
        self.assertEqual(out["status"], "RCA Required",
                         "advertise 'RCA Required' phải có driver thực thi được")

    # INVARIANT desk↔endpoint parity (anti false-clickable / anti dead-gate)
    def test_desk_endpoint_parity_request_rca(self):
        """INV cap ⊆ workflow: role-set(compliance.submit) resolve ĐỘNG qua rbac
        (DocPerm submit IMM CAPA Record) PHẢI ⊆ workflow 'Yêu cầu RCA' allowed →
        mọi user qua cap-gate đều apply_workflow được (KHÔNG false-clickable). +
        edge ('Resolved','RCA Required') ∈ workflow ∧ ∈ _VALID_TRANSITIONS[Resolved]
        (reconcile chống drift dead-CTA)."""
        cap_roles = _roles_resolving_cap(_CAP_REQUEST_RCA)
        wf_roles = _workflow_allowed_roles(_WF_ACTION_REQUEST_RCA)
        # Grounding: workflow role-set khớp Core Doc (chống drift âm thầm JSON).
        self.assertEqual(
            wf_roles,
            {"Compliance Manager", "System Manager", "AssetCore Super Admin"},
            "workflow 'Yêu cầu RCA' allowed role-set lệch Core Doc")
        self.assertTrue(
            cap_roles, "compliance.submit phải resolve ≥1 role (chống dead-gate)")
        self.assertTrue(
            cap_roles <= wf_roles,
            f"cap compliance.submit role-set {sorted(cap_roles)} ⊄ workflow "
            f"'Yêu cầu RCA' {sorted(wf_roles)} → có user false-clickable "
            f"(cap-pass nhưng workflow từ chối apply_workflow)")
        # State-edge reconcile (không đổi map/JSON — chỉ assert bất biến).
        self.assertIn("RCA Required", _VALID_TRANSITIONS["Resolved"])
        self.assertIn(("Resolved", "RCA Required"), _load_incident_workflow_edges())

    # TC-12-REQRCA-06 — downstream loop khép kín (ENTRY↔EXIT)
    def test_rca_required_auto_closes_after_completion(self):
        """Sau request_rca (Resolved→RCA Required) → start_rca → submit_rca
        (RCA Completed) → _advance_incident_after_rca tự đẩy Incident → Closed
        (ENTRY↔EXIT khép kín)."""
        name = _make_resolved_incident(self.asset.name, severity="Medium")
        out = request_rca(name, rca_reason="Đóng loop downstream RCA")
        frappe.db.commit()
        rca_name = out["rca_record"]
        self.assertEqual(
            frappe.db.get_value("Incident Report", name, "workflow_state"),
            "RCA Required", "request_rca phải đặt workflow_state='RCA Required' cho "
            "downstream apply_workflow('RCA hoàn tất - đóng sự cố')")
        start_rca(rca_name)
        # RCA method '5-Why' → phải điền đủ 5 bước (why_question + why_answer) khi
        # hoàn thành (imm_rca_record._validate_five_why_when_method_5why).
        five_why = [
            {"why_number": i, "why_question": f"Vì sao tầng {i}?",
             "why_answer": f"Nguyên nhân tầng {i}: linh kiện cảm biến xuống cấp"}
            for i in range(1, 6)
        ]
        submit_rca(rca_name, root_cause="Nguyên nhân gốc: mòn linh kiện cảm biến",
                   corrective_action="Thay cảm biến + hiệu chuẩn lại theo NĐ98",
                   five_why_steps=five_why)
        frappe.db.commit()
        self.assertEqual(
            frappe.db.get_value("Incident Report", name, "status"), "Closed",
            "sau RCA Completed, Incident PHẢI auto-close (_advance_incident_after_rca)")


# ── RCA-gate SSoT (BR-12-02): rca_required = derived(severity) re-sync mọi save ──
#    Chống ĐÓNG-GIẢ sự cố escalation Medium→Critical. Cả 2 gate (service
#    close_incident + controller hook validate_incident_close_gate) đọc CÙNG SSoT =
#    LIVE severity. TẤT CẢ drive qua service/doc-save path — KHÔNG pre-seed
#    rca_required qua db.set_value (khác _make_incident_at_rca_required cũ vốn
#    pre-seed cờ = false-green). Ref: memory server-flag-SSoT / derive-live.
class TestIncidentCloseRcaGateSSoT(unittest.TestCase):
    """RCA-gate SSoT — rca_required derive-live từ severity, non-waivable High/Critical."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-rcassot")

    @classmethod
    def tearDownClass(cls):
        purge_asset(cls.asset.name)

    def setUp(self):
        frappe.set_user("Administrator")

    # ── helpers (đường doc-save / service THẬT, KHÔNG db.set_value cờ) ──────────
    def _escalate(self, name: str, to: str = "Critical") -> None:
        """Nâng/hạ severity qua doc.save() TRỰC TIẾP (đường desk) → kích hoạt
        controller re-sync rca_required. Critical bắt buộc clinical_impact
        (mandatory_depends_on trong DocType) nên seed khi thiếu."""
        doc = frappe.get_doc("Incident Report", name)
        doc.severity = to
        if to == "Critical" and not (doc.clinical_impact or "").strip():
            doc.clinical_impact = (
                "Nâng mức nghiêm trọng sau đánh giá lại — ảnh hưởng an toàn bệnh nhân")
        doc.flags.ignore_permissions = True
        doc.save()
        frappe.db.commit()

    def _open_medium_incident(self) -> str:
        out = report_incident(
            asset=self.asset.name, incident_type="Malfunction", severity="Medium",
            description="_Test SSoT rca-gate incident description body")
        frappe.db.commit()
        return out["name"]

    def _rca_required(self, name: str) -> int:
        return frappe.db.get_value("Incident Report", name, "rca_required")

    # ── #1 SSoT: rca_required derive-live từ severity trên MỌI save ─────────────
    def test_rca_required_derives_live_from_severity_on_save(self):
        name = self._open_medium_incident()
        self.assertEqual(
            self._rca_required(name), 0,
            "Medium mới tạo → rca_required=0 (SSoT severity)")
        # Escalate Medium → Critical: re-sync PHẢI bật cờ (RED trước fix: stays 0).
        self._escalate(name, "Critical")
        self.assertEqual(
            self._rca_required(name), 1,
            "Sau escalate Critical + save → rca_required=1 (derive-live, KHÔNG stale)")
        # Downgrade Critical → Medium: re-sync PHẢI tắt cờ.
        self._escalate(name, "Medium")
        self.assertEqual(
            self._rca_required(name), 0,
            "Hạ lại Medium + save → rca_required=0 (mirror-của-severity)")

    # ── #2 close-giả (CA sắc nhất): escalation Medium→Critical KHÔNG rca_record ──
    def test_escalated_critical_without_rca_close_blocked_required(self):
        # Resolve khi CÒN Medium ⇒ resolve KHÔNG auto-tạo RCA (rca_record rỗng).
        name = _make_resolved_incident(self.asset.name, severity="Medium")
        self.assertEqual(self._rca_required(name), 0)
        # Escalate lên Critical SAU resolve → re-sync rca_required=1, rca_record vẫn rỗng.
        self._escalate(name, "Critical")
        self.assertEqual(self._rca_required(name), 1)
        with self.assertRaises(ServiceError) as ctx:
            close_incident(name, verification_notes="_Test close escalated critical")
        self.assertEqual(
            ctx.exception.message_code, MSG.IMM12_CLOSE_RCA_REQUIRED,
            "Escalated Critical không RCA → chặn REQUIRED (KHÔNG đóng-giả)")
        self.assertNotEqual(
            frappe.db.get_value("Incident Report", name, "status"), "Closed",
            "close BỊ CHẶN ⇒ status KHÔNG được thành Closed (chống fake-close)")

    # ── #3 escalated Critical có rca_record nhưng RCA chưa Completed → INCOMPLETE ─
    def test_escalated_critical_incomplete_rca_close_blocked_incomplete(self):
        name = self._open_medium_incident()
        acknowledge_incident(name)
        start_work(name)
        frappe.db.commit()
        # Escalate TRƯỚC resolve ⇒ resolve auto-tạo RCA (status='RCA Required').
        self._escalate(name, "Critical")
        resolve_incident(name, resolution_notes="_Test resolve escalated critical")
        frappe.db.commit()
        rca_name = frappe.db.get_value("Incident Report", name, "rca_record")
        self.assertTrue(rca_name, "resolve Critical PHẢI auto-tạo RCA record")
        self.assertNotEqual(
            frappe.db.get_value("IMM RCA Record", rca_name, "status"), "Completed")
        with self.assertRaises(ServiceError) as ctx:
            close_incident(name, verification_notes="_Test close incomplete rca")
        self.assertEqual(
            ctx.exception.message_code, MSG.IMM12_CLOSE_RCA_INCOMPLETE,
            "rca_record tồn tại nhưng chưa Completed → chặn INCOMPLETE")

    # ── #4 GREEN happy: RCA driven Completed → close OK, asset khôi phục Active ──
    def test_escalated_critical_completed_rca_close_succeeds(self):
        name = self._open_medium_incident()
        acknowledge_incident(name)   # Critical (sau escalate) → asset Out of Service
        start_work(name)
        frappe.db.commit()
        self._escalate(name, "Critical")
        resolve_incident(name, resolution_notes="_Test resolve for green rca")
        frappe.db.commit()
        rca_name = frappe.db.get_value("Incident Report", name, "rca_record")
        self.assertTrue(rca_name)
        # Drive RCA → Completed qua service THẬT (start_rca → submit_rca), KHÔNG
        # db.set_value (khác _make_incident_at_rca_required cũ = false-green).
        start_rca(rca_name)
        five_why = [
            {"why_number": i, "why_question": f"Vì sao tầng {i}?",
             "why_answer": f"Nguyên nhân tầng {i}: linh kiện xuống cấp theo thời gian"}
            for i in range(1, 6)
        ]
        submit_rca(
            rca_name, root_cause="Nguyên nhân gốc: mòn linh kiện sau chu kỳ vận hành",
            corrective_action="Thay linh kiện + hiệu chuẩn lại theo NĐ98",
            five_why_steps=five_why)
        frappe.db.commit()
        self.assertEqual(
            frappe.db.get_value("IMM RCA Record", rca_name, "status"), "Completed")
        res = close_incident(name, verification_notes="Đã xác minh khắc phục hoàn tất")
        self.assertEqual(res["status"], "Closed")
        self.assertEqual(
            frappe.db.get_value("Incident Report", name, "status"), "Closed")
        self.assertEqual(
            frappe.db.get_value("AC Asset", self.asset.name, "lifecycle_status"),
            "Active", "Critical acknowledge → Out of Service; close → khôi phục Active")

    # ── #5 non-regression: Medium thực (không escalate) → close bình thường ──────
    def test_medium_non_escalated_closes_without_rca(self):
        name = _make_resolved_incident(self.asset.name, severity="Medium")
        self.assertEqual(self._rca_required(name), 0)
        res = close_incident(name, verification_notes="_Test close medium normal")
        self.assertEqual(res["status"], "Closed")
        self.assertEqual(
            self._rca_required(name), 0,
            "Medium thực → rca_required=0, KHÔNG bắt RCA (non-regression)")

    # ── #6 non-regression: Critical từ đầu chưa RCA Completed → close chặn ───────
    def test_critical_from_start_incomplete_rca_close_blocked(self):
        name = _make_resolved_incident(
            self.asset.name, severity="Critical",
            clinical_impact="Ảnh hưởng lâm sàng nghiêm trọng — thiết bị ngừng an toàn")
        self.assertEqual(self._rca_required(name), 1)
        rca_name = frappe.db.get_value("Incident Report", name, "rca_record")
        self.assertTrue(rca_name, "resolve Critical PHẢI auto-tạo RCA")
        with self.assertRaises(ServiceError) as ctx:
            close_incident(name, verification_notes="_Test close critical from start")
        self.assertEqual(
            ctx.exception.message_code, MSG.IMM12_CLOSE_RCA_INCOMPLETE,
            "Critical từ đầu, RCA chưa Completed → close chặn (giữ hành vi, chống lệch)")

    # ── #7 controller net: chặn desk-path (doc.save status→Closed, KHÔNG service) ─
    def test_controller_gate_blocks_desk_close_path(self):
        out = report_incident(
            asset=self.asset.name, incident_type="Malfunction", severity="Critical",
            description="_Test desk-path close gate incident body",
            clinical_impact="Ảnh hưởng lâm sàng — cần chặn đóng-giả đường desk")
        frappe.db.commit()
        name = out["name"]
        self.assertEqual(self._rca_required(name), 1)
        # Đóng TRỰC TIẾP qua doc.save() flip workflow_state='Closed' (đường
        # desk/apply_workflow — gate ưu tiên workflow_state) — KHÔNG qua service
        # close_incident. Controller hook validate_incident_close_gate PHẢI chặn.
        with self.assertRaises(frappe.ValidationError):
            doc = frappe.get_doc("Incident Report", name)
            doc.workflow_state = "Closed"
            doc.flags.ignore_permissions = True
            doc.save()
        self.assertEqual(
            frappe.local.response.get("message_code"), MSG.IMM12_CLOSE_RCA_REQUIRED,
            "hook chặn desk-path phải phát message_code REQUIRED")
        self.assertNotEqual(
            frappe.db.get_value("Incident Report", name, "workflow_state"), "Closed",
            "desk-path bị chặn ⇒ KHÔNG persist workflow_state Closed")


# ── CR-55: RCA deadlock — hồ sơ RCA Cancelled KHÔNG được khoá vĩnh viễn phiếu ────
#    High/Critical. create_rca/request_rca dùng CÙNG vị từ _has_live_rca (rca_record
#    tồn tại ∧ status != 'Cancelled') để "thay hồ sơ RCA đã huỷ" mà KHÔNG chạm hồ sơ
#    huỷ (giữ vết audit NĐ98). Regression: RCA còn sống VẪN chặn IMM12_RCA_ALREADY_EXISTS.
# ─────────────────────────────────────────────────────────────────────────────────

class TestRCADeadlockCancelledReplacement(unittest.TestCase):
    """CR-55: gỡ deadlock hồ sơ RCA Cancelled khoá phiếu sự cố Cao/Nguy kịch.

    Cover:
      - create_rca thay hồ sơ RCA đã Cancelled (tạo mới, không raise ALREADY_EXISTS).
      - create_rca VẪN chặn khi RCA còn sống (regression guard idempotent).
      - request_rca (Resolved→RCA Required) tạo hồ sơ MỚI sau khi hồ sơ cũ Cancelled.
      - request_rca precondition status != Resolved → 422 (bất biến).
      - close_incident hết deadlock sau khi RCA thay-thế Completed; asset OOS→Active.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-rcadeadlock")

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        # purge_asset cancels submitted Incident/RCA/CAPA (dependency order) và purge
        # raw-SQL audit trail trước khi xoá asset.
        purge_asset(cls.asset.name)

    def setUp(self):
        frappe.set_user("Administrator")

    def _resolved_incident_with_auto_rca(self, severity: str = "High") -> tuple[str, str]:
        """report → ack → start_work → resolve; resolve auto-tạo RCA (RCA Required).

        Trả (incident_name, auto_rca_name). Incident.status = Resolved,
        rca_record trỏ hồ sơ RCA auto-tạo (LIVE — 'RCA Required'). KHÔNG set
        workflow_state='RCA Required' ⇒ _advance_incident_after_rca sẽ no-op
        (tránh auto-close nhiễu test close tường minh).
        """
        result = report_incident(
            asset=self.asset.name,
            incident_type="Malfunction",
            severity=severity,
            description="_Test CR-55 deadlock incident body",
            clinical_impact="_Test clinical impact CR-55 deadlock",
        )
        frappe.db.commit()
        ir = result["name"]
        acknowledge_incident(ir, notes="_Test ack CR-55")
        frappe.db.commit()
        start_work(ir, notes="_Test start CR-55")
        frappe.db.commit()
        resolve_incident(
            ir,
            resolution_notes="_Test resolution CR-55",
            root_cause="_Test root cause CR-55",
        )
        frappe.db.commit()
        rca = frappe.db.get_value("Incident Report", ir, "rca_record")
        self.assertTrue(rca, "resolve High/Critical phải auto-tạo hồ sơ RCA")
        return ir, rca

    @staticmethod
    def _filled_five_whys() -> list:
        return [
            {"why_number": i, "why_question": f"Vì sao {i}?",
             "why_answer": f"Nguyên nhân mức {i}"}
            for i in range(1, 6)
        ]

    def test_create_rca_replaces_cancelled_record(self):
        """rca_record trỏ hồ sơ Cancelled → create_rca tạo hồ sơ MỚI, hồ sơ cũ giữ Cancelled."""
        ir, old_rca = self._resolved_incident_with_auto_rca(severity="High")
        cancel_rca(old_rca, reason="_Test hủy RCA để thay thế")
        frappe.db.commit()
        self.assertEqual(
            frappe.db.get_value("IMM RCA Record", old_rca, "status"), "Cancelled")

        result = create_rca(ir)
        frappe.db.commit()
        new_rca = result["name"]

        self.assertNotEqual(
            new_rca, old_rca, "create_rca phải tạo hồ sơ RCA MỚI, không tái dùng hồ sơ huỷ")
        self.assertEqual(
            frappe.db.get_value("Incident Report", ir, "rca_record"), new_rca,
            "Incident.rca_record phải cập nhật sang tên hồ sơ RCA mới")
        # Hồ sơ cũ GIỮ NGUYÊN Cancelled — vết audit NĐ98, không bị mutate/xoá.
        self.assertEqual(
            frappe.db.get_value("IMM RCA Record", old_rca, "status"), "Cancelled",
            "hồ sơ RCA cũ phải giữ nguyên status=Cancelled (bằng chứng audit)")
        self.assertTrue(
            frappe.db.exists("IMM RCA Record", old_rca),
            "hồ sơ RCA cũ KHÔNG được xoá")

    def test_create_rca_still_blocks_live_rca(self):
        """Regression: rca_record trỏ hồ sơ còn sống → VẪN raise IMM12_RCA_ALREADY_EXISTS."""
        ir, live_rca = self._resolved_incident_with_auto_rca(severity="High")
        # 'RCA Required' (LIVE) → chặn.
        self.assertEqual(
            frappe.db.get_value("IMM RCA Record", live_rca, "status"), "RCA Required")
        with self.assertRaises(ServiceError) as ctx:
            create_rca(ir)
        self.assertEqual(ctx.exception.message_code, MSG.IMM12_RCA_ALREADY_EXISTS)

        # 'RCA In Progress' (LIVE) → cũng chặn.
        start_rca(live_rca)
        frappe.db.commit()
        self.assertEqual(
            frappe.db.get_value("IMM RCA Record", live_rca, "status"), "RCA In Progress")
        with self.assertRaises(ServiceError) as ctx2:
            create_rca(ir)
        self.assertEqual(ctx2.exception.message_code, MSG.IMM12_RCA_ALREADY_EXISTS)

    def test_request_rca_creates_new_after_cancel(self):
        """Phiếu Resolved, rca_record Cancelled → request_rca tạo hồ sơ MỚI, KHÔNG tái dùng huỷ."""
        ir, old_rca = self._resolved_incident_with_auto_rca(severity="High")
        cancel_rca(old_rca, reason="_Test hủy RCA trước khi yêu cầu lại")
        frappe.db.commit()
        self.assertEqual(
            frappe.db.get_value("Incident Report", ir, "status"), "Resolved",
            "hủy RCA không đổi trạng thái phiếu (vẫn Resolved)")

        out = request_rca(ir, rca_reason="_Test yêu cầu RCA mới sau khi hủy")
        frappe.db.commit()

        self.assertEqual(out["status"], "RCA Required")
        new_rca = frappe.db.get_value("Incident Report", ir, "rca_record")
        self.assertNotEqual(
            new_rca, old_rca, "request_rca phải tạo hồ sơ RCA MỚI, không tái dùng hồ sơ huỷ")
        self.assertEqual(
            frappe.db.get_value("IMM RCA Record", new_rca, "status"), "RCA Required")
        # Hồ sơ huỷ giữ nguyên (audit).
        self.assertEqual(
            frappe.db.get_value("IMM RCA Record", old_rca, "status"), "Cancelled")

    def test_request_rca_precondition_not_resolved_422(self):
        """Bất biến: request_rca trên phiếu status != Resolved → 422."""
        result = report_incident(
            asset=self.asset.name,
            incident_type="Malfunction",
            severity="High",
            description="_Test CR-55 precondition not resolved",
            clinical_impact="_Test clinical impact precondition",
        )
        frappe.db.commit()
        ir = result["name"]  # status = Open (chưa Resolved)
        self.assertNotEqual(
            frappe.db.get_value("Incident Report", ir, "status"), "Resolved")
        with self.assertRaises(ServiceError) as ctx:
            request_rca(ir, rca_reason="_Test yêu cầu RCA khi chưa Resolved")
        self.assertEqual(ctx.exception.message_code, MSG.IMM12_REQUEST_RCA_BAD_STATE)
        self.assertEqual(ctx.exception.http_status, 422)

    def test_close_incident_unblocked_after_replacement_rca_completed(self):
        """End-to-end: Critical → cancel RCA (deadlock) → thay RCA mới → Completed →
        close_incident OK (KHÔNG IMM12_CLOSE_RCA_INCOMPLETE); asset OOS→Active."""
        # Đảm bảo điểm xuất phát asset = Active (test độc lập thứ tự).
        frappe.db.set_value(
            "AC Asset", self.asset.name, "lifecycle_status", "Active",
            update_modified=False)
        frappe.db.commit()

        ir, old_rca = self._resolved_incident_with_auto_rca(severity="Critical")
        # BR-12-04: Critical report → asset Out of Service.
        self.assertEqual(
            frappe.db.get_value("AC Asset", self.asset.name, "lifecycle_status"),
            "Out of Service", "Critical report phải đưa asset về Out of Service")

        # Hủy RCA auto → tạo deadlock: close bị chặn vì RCA chưa Completed.
        cancel_rca(old_rca, reason="_Test hủy RCA gây deadlock")
        frappe.db.commit()
        with self.assertRaises(ServiceError) as ctx:
            close_incident(ir, verification_notes="_Test đóng khi RCA còn huỷ")
        self.assertEqual(
            ctx.exception.message_code, MSG.IMM12_CLOSE_RCA_INCOMPLETE,
            "RCA Cancelled → close phải chặn IMM12_CLOSE_RCA_INCOMPLETE (deadlock)")

        # CR-55: thay hồ sơ RCA mới rồi hoàn tất qua đường thật.
        new_rca = create_rca(ir)["name"]
        frappe.db.commit()
        self.assertNotEqual(new_rca, old_rca)
        start_rca(new_rca)
        frappe.db.commit()
        submit_rca(
            new_rca,
            root_cause="_Test nguyên nhân gốc thay thế CR-55",
            corrective_action="_Test hành động khắc phục thay thế CR-55",
            five_why_steps=self._filled_five_whys(),
        )
        frappe.db.commit()
        self.assertEqual(
            frappe.db.get_value("IMM RCA Record", new_rca, "status"), "Completed")
        # workflow_state != 'RCA Required' ⇒ submit không auto-close ⇒ đóng tường minh.
        self.assertNotEqual(
            frappe.db.get_value("Incident Report", ir, "status"), "Closed",
            "RCA hoàn tất không auto-close phiếu (đóng qua close_incident tường minh)")

        # Deadlock đã gỡ: close_incident KHÔNG còn raise.
        close_incident(ir, verification_notes="_Test đóng sau khi thay RCA hoàn tất")
        frappe.db.commit()
        self.assertEqual(
            frappe.db.get_value("Incident Report", ir, "status"), "Closed",
            "close_incident phải thành công sau khi RCA thay-thế Completed")
        # Asset khôi phục Out of Service → Active (deadlock gỡ end-to-end).
        self.assertEqual(
            frappe.db.get_value("AC Asset", self.asset.name, "lifecycle_status"),
            "Active", "đóng phiếu phải khôi phục asset Out of Service → Active")


# ══════════════════════════════════════════════════════════════════════════════
# CR-39 — get_incident_detail.available_actions[] server-driven (6 CTA vòng đời)
# Xoá predicate-mirror client-side + "403 sau khi bấm". Mirror imm00.
# ══════════════════════════════════════════════════════════════════════════════

_AA_KEYS_ORDER = ["acknowledge", "start_work", "resolve", "close", "reopen", "cancel"]
# Shape AvailableAction (tái dùng schema QR-scan yaml:7795, required 5 field) —
# route ∈ required ⇒ incident emit route="" (CTA nằm TRONG màn Chi tiết).
_AA_SHAPE = {"key", "label", "route", "enabled", "reason"}

_C_ACK = "incident.acknowledge"
_C_CLOSE = "incident.close"


def _aa_stub(status: str, severity: str = "Medium"):
    """Doc-stub tối thiểu cho builder (chỉ đọc .status/.severity) — cho phép duyệt
    MỌI status kể cả '' và mã LẠ (Select DocType không tạo được các state đó)."""
    return types.SimpleNamespace(status=status, severity=severity)


def _fake_can(allow: set):
    """rbac.can giả: True ⇔ cap ∈ allow. Điều khiển has_cap deterministic (unit)."""
    def _c(cap, doc=None):
        return cap in allow
    return _c


def _by_key(actions: list) -> dict:
    return {a["key"]: a for a in actions}


class TestIncidentAvailableActionsShape(unittest.TestCase):
    """TDD-1: get_incident_detail bồi available_actions = list ĐÚNG 6 CTA, thứ tự cố
    định, shape AvailableAction {key,label,route,enabled,reason} (route='') — KHÔNG
    khoá thừa/thiếu."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-aa-shape")
        out = report_incident(
            asset=cls.asset.name, incident_type="Malfunction", severity="Medium",
            description="_Test available_actions shape incident description",
        )
        cls.inc = out["name"]
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        purge_asset(cls.asset.name)
        frappe.db.commit()

    def test_available_actions_present_exactly_six_fixed_order(self):
        data = get_incident_detail(self.inc)
        self.assertIn("available_actions", data,
                      "get_incident_detail PHẢI bồi khoá available_actions (CR-39)")
        aa = data["available_actions"]
        self.assertIsInstance(aa, list)
        self.assertEqual(len(aa), 6, "PHẢI đúng 6 CTA vòng đời")
        self.assertEqual([a["key"] for a in aa], _AA_KEYS_ORDER,
                         "thứ tự CỐ ĐỊNH [acknowledge,start_work,resolve,close,reopen,cancel]")

    def test_each_element_exact_shape_route_empty(self):
        aa = get_incident_detail(self.inc)["available_actions"]
        for a in aa:
            self.assertEqual(
                set(a.keys()), _AA_SHAPE,
                f"CTA {a.get('key')} shape phải = {_AA_SHAPE} (AvailableAction), KHÔNG khoá thừa/thiếu")
            self.assertEqual(a["route"], "", "route='' — CTA nằm trong màn (không deep-link)")
            self.assertIsInstance(a["enabled"], bool)
            self.assertIsInstance(a["reason"], str)


class TestIncidentAvailableActionsReadOnly(unittest.TestCase):
    """TDD-7: get_incident_detail READ-ONLY tuyệt đối — KHÔNG tạo IMM Audit Trail /
    Asset Lifecycle Event, KHÔNG modify doc (count/modified before == after)."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-aa-ro")
        out = report_incident(
            asset=cls.asset.name, incident_type="Malfunction", severity="Medium",
            description="_Test available_actions read-only incident description",
        )
        cls.inc = out["name"]
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        purge_asset(cls.asset.name)
        frappe.db.commit()

    def test_get_incident_detail_has_no_write_side_effects(self):
        audit_before = frappe.db.count("IMM Audit Trail")
        lifecycle_before = frappe.db.count("Asset Lifecycle Event")
        mod_before = frappe.db.get_value("Incident Report", self.inc, "modified")
        # Gọi 2 lần để chắc chắn không tích luỹ side-effect ghi.
        get_incident_detail(self.inc)
        data = get_incident_detail(self.inc)
        audit_after = frappe.db.count("IMM Audit Trail")
        lifecycle_after = frappe.db.count("Asset Lifecycle Event")
        mod_after = frappe.db.get_value("Incident Report", self.inc, "modified")
        self.assertEqual(audit_after, audit_before,
                         "get_incident_detail KHÔNG được tạo IMM Audit Trail")
        self.assertEqual(lifecycle_after, lifecycle_before,
                         "get_incident_detail KHÔNG được tạo Asset Lifecycle Event")
        self.assertEqual(mod_after, mod_before,
                         "get_incident_detail KHÔNG được modify doc (modified bất biến)")
        self.assertEqual(len(data["available_actions"]), 6,
                         "vẫn trả đủ 6 CTA (đảm bảo test không vô nghĩa)")


class TestIncidentAvailableActionsTransition(unittest.TestCase):
    """TDD-2: transition_allowed = target ∈ _VALID_TRANSITIONS[status] ∧ from-state.
    Open + đủ cap → acknowledge mở (reason=''); close chưa cho transition → đóng
    (reason != '')."""

    def test_open_acknowledge_enabled_close_transition_blocked(self):
        with patch.object(rbac, "can", side_effect=_fake_can({_C_ACK, _C_CLOSE})):
            actions = _by_key(_build_incident_available_actions(_aa_stub("Open"), ""))
        ack = actions["acknowledge"]
        self.assertTrue(ack["enabled"], "Open + cap acknowledge ⟹ acknowledge mở")
        self.assertEqual(ack["reason"], "", "enabled ⟹ reason=''")
        close = actions["close"]
        self.assertFalse(close["enabled"], "close chưa mở transition tại Open")
        self.assertEqual(close["reason"], _ACTION_REASON_TRANSITION,
                         "transition chưa cho ⟹ reason bậc transition (VI != '')")


class TestIncidentAvailableActionsCapability(unittest.TestCase):
    """TDD-3: has_cap dùng ĐÚNG predicate SSoT endpoint ghi. Thiếu incident.acknowledge
    → 4 op investigate (ack/start/resolve/cancel) disabled + reason capability;
    close/reopen theo incident.close ĐỘC LẬP (verify cả 2 chiều)."""

    # (cta, status transition-hợp-lệ để cô lập nhánh capability, không phải transition)
    _INVESTIGATE_AT = [
        ("acknowledge", "Open"),
        ("start_work", "Acknowledged"),
        ("resolve", "In Progress"),
        ("cancel", "Open"),
    ]

    def test_missing_investigate_cap_disables_investigate_ctas(self):
        # CÓ incident.close, THIẾU incident.acknowledge.
        with patch.object(rbac, "can", side_effect=_fake_can({_C_CLOSE})):
            for key, status in self._INVESTIGATE_AT:
                actions = _by_key(
                    _build_incident_available_actions(_aa_stub(status, "Low"), ""))
                a = actions[key]
                self.assertFalse(a["enabled"], f"{key}@{status}: thiếu cap acknowledge ⟹ disabled")
                self.assertEqual(a["reason"], _ACTION_REASON_CAPABILITY,
                                 f"{key}: transition OK nhưng thiếu cap ⟹ reason bậc capability")

    def test_close_reopen_independent_of_investigate_cap(self):
        # Chiều 1: THIẾU acknowledge, CÓ close → close/reopen mở tại Resolved (Low → no RCA gate).
        with patch.object(rbac, "can", side_effect=_fake_can({_C_CLOSE})):
            actions = _by_key(
                _build_incident_available_actions(_aa_stub("Resolved", "Low"), ""))
        self.assertTrue(actions["close"]["enabled"], "close độc lập cap acknowledge")
        self.assertEqual(actions["close"]["reason"], "")
        self.assertTrue(actions["reopen"]["enabled"], "reopen độc lập cap acknowledge")
        self.assertEqual(actions["reopen"]["reason"], "")
        # Chiều 2: CÓ acknowledge, THIẾU close → close/reopen disabled + reason capability.
        with patch.object(rbac, "can", side_effect=_fake_can({_C_ACK})):
            actions = _by_key(
                _build_incident_available_actions(_aa_stub("Resolved", "Low"), ""))
        self.assertFalse(actions["close"]["enabled"], "thiếu cap close ⟹ close đóng")
        self.assertEqual(actions["close"]["reason"], _ACTION_REASON_CAPABILITY)
        self.assertFalse(actions["reopen"]["enabled"], "thiếu cap close ⟹ reopen đóng")
        self.assertEqual(actions["reopen"]["reason"], _ACTION_REASON_CAPABILITY)


class TestIncidentAvailableActionsBusinessGate(unittest.TestCase):
    """TDD-4: business_gate close = BR-12-02. severity High/Critical + Resolved:
    (a) RCA rỗng/chưa Completed → close đóng + reason RCA-gate; (b) RCA Completed +
    đủ cap → close mở + reason=''."""

    def test_close_blocked_when_rca_incomplete_high_severity(self):
        with patch.object(rbac, "can", side_effect=_fake_can({_C_ACK, _C_CLOSE})):
            for sev in ("High", "Critical"):
                for rca_status in ("", "RCA Required", "In Progress"):
                    actions = _by_key(_build_incident_available_actions(
                        _aa_stub("Resolved", sev), rca_status))
                    close = actions["close"]
                    self.assertFalse(
                        close["enabled"],
                        f"sev={sev} rca={rca_status!r}: BR-12-02 chặn close")
                    self.assertEqual(close["reason"], _ACTION_REASON_RCA_GATE,
                                     f"sev={sev} rca={rca_status!r}: reason bậc business-gate RCA")

    def test_close_allowed_when_rca_completed(self):
        with patch.object(rbac, "can", side_effect=_fake_can({_C_ACK, _C_CLOSE})):
            for sev in ("High", "Critical"):
                actions = _by_key(_build_incident_available_actions(
                    _aa_stub("Resolved", sev), "Completed"))
                close = actions["close"]
                self.assertTrue(close["enabled"],
                                f"sev={sev} rca=Completed + đủ cap ⟹ close mở")
                self.assertEqual(close["reason"], "")


class TestIncidentAvailableActionsD9Invariant(unittest.TestCase):
    """TDD-5: bất biến D9 — duyệt MỌI status (kể cả '' và mã LẠ 'Foo') × severity ×
    cap-combo: enabled is False ⟹ reason != ''; enabled is True ⟹ reason == ''."""

    _ALL_STATUSES = [
        "Open", "Acknowledged", "In Progress", "Resolved", "RCA Required",
        "Closed", "Cancelled", "", "Foo",
    ]

    def test_invariant_holds_over_full_matrix(self):
        cap_scenarios = [set(), {_C_ACK}, {_C_CLOSE}, {_C_ACK, _C_CLOSE}]
        for caps in cap_scenarios:
            with patch.object(rbac, "can", side_effect=_fake_can(caps)):
                for status in self._ALL_STATUSES:
                    for sev in ("Low", "High", "Critical"):
                        for rca_status in ("", "Completed"):
                            actions = _build_incident_available_actions(
                                _aa_stub(status, sev), rca_status)
                            self.assertEqual(len(actions), 6)
                            for a in actions:
                                ctx = (f"status={status!r} sev={sev} rca={rca_status!r} "
                                       f"cap={sorted(caps)} key={a['key']}")
                                if a["enabled"]:
                                    self.assertEqual(a["reason"], "",
                                                     f"enabled True ⟹ reason='' ({ctx})")
                                else:
                                    self.assertNotEqual(a["reason"], "",
                                                        f"enabled False ⟹ reason!='' ({ctx})")


class TestIncidentAvailableActionsReopenCollision(unittest.TestCase):
    """TDD-6 + regression va-chạm: start_work↔reopen cùng đích 'In Progress' được khử
    bằng from-state. reopen mở CHỈ tại Resolved; start_work mở CHỈ tại Acknowledged."""

    def test_reopen_enabled_at_resolved_with_close_cap(self):
        with patch.object(rbac, "can", side_effect=_fake_can({_C_CLOSE})):
            actions = _by_key(
                _build_incident_available_actions(_aa_stub("Resolved", "Low"), ""))
        self.assertTrue(actions["reopen"]["enabled"])
        self.assertEqual(actions["reopen"]["reason"], "")

    def test_reopen_disabled_at_in_progress_transition_blocked(self):
        with patch.object(rbac, "can", side_effect=_fake_can({_C_CLOSE})):
            actions = _by_key(
                _build_incident_available_actions(_aa_stub("In Progress", "Low"), ""))
        r = actions["reopen"]
        self.assertFalse(r["enabled"], "reopen KHÔNG mở tại In Progress")
        self.assertEqual(r["reason"], _ACTION_REASON_TRANSITION)

    def test_start_work_not_enabled_at_resolved(self):
        # Va-chạm: 'In Progress' ∈ _VALID_TRANSITIONS['Resolved'] nhưng đó là reopen,
        # KHÔNG phải start_work. from-state phải khử.
        with patch.object(rbac, "can", side_effect=_fake_can({_C_ACK, _C_CLOSE})):
            actions = _by_key(
                _build_incident_available_actions(_aa_stub("Resolved", "Low"), ""))
        self.assertFalse(actions["start_work"]["enabled"],
                         "start_work KHÔNG được mở tại Resolved (chỉ reopen)")
        self.assertTrue(actions["reopen"]["enabled"], "reopen mở tại Resolved")

    def test_reopen_not_enabled_at_acknowledged(self):
        with patch.object(rbac, "can", side_effect=_fake_can({_C_ACK, _C_CLOSE})):
            actions = _by_key(
                _build_incident_available_actions(_aa_stub("Acknowledged", "Low"), ""))
        self.assertFalse(actions["reopen"]["enabled"],
                         "reopen KHÔNG được mở tại Acknowledged (chỉ start_work)")
        self.assertTrue(actions["start_work"]["enabled"], "start_work mở tại Acknowledged")


# ─── CR-69 · Hợp đồng TRUNG THỰC khi cắt — lịch sử SỰ CỐ của thiết bị ─────────

class TestAssetIncidentHistoryTruncation(unittest.TestCase):
    """TC-BE-12-HIST-01..05 (CR-69): ``get_asset_incident_history`` PHẢI công bố
    ``total`` + ``truncated`` thay vì cắt IM LẶNG theo ``limit``.

    KHÁC IMM-08/09 ở shape: rows-key là ``items``, asset-key là ``asset``.
    Nguồn rows là ``frappe.get_all`` trần ⇒ ``count_fn`` phải là ``frappe.db.count``
    trên ĐÚNG filter ``{asset}`` (cùng predicate VÀ cùng engine với rows).
    """

    _assets: list[str] = []

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls._assets = []

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for a in cls._assets:
            purge_asset(a)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")

    def _seed(self, n: int, tag: str) -> str:
        asset = _make_asset(f"-cr69{tag}")
        type(self)._assets.append(asset.name)
        for i in range(n):
            frappe.get_doc({
                "doctype": "Incident Report",
                "asset": asset.name,
                "incident_type": "Malfunction",
                "severity": "Low",
                "description": f"_Test CR-69 incident {tag}-{i}",
                "reported_by": "Administrator",
                "status": "Open",
            }).insert(ignore_permissions=True)
        frappe.db.commit()
        return asset.name

    # ── TC-BE-12-HIST-01: quá trần → total thật + truncated=1 ────────────────
    def test_tc_be_12_hist_01_over_limit_exposes_real_total(self):
        from assetcore.services.imm12 import get_asset_incident_history
        asset = self._seed(12, "01")
        res = get_asset_incident_history(asset, limit=10)
        self.assertEqual(len(res["items"]), 10,
                         "limit=10 ⇒ CHỈ 10 dòng trả về (trần giữ nguyên).")
        self.assertEqual(res["total"], 12,
                         "total = COUNT DB thật trên {asset} TRƯỚC khi cắt (12).")
        self.assertEqual(res["truncated"], 1, "12 > 10 ∧ chạm trần ⇒ truncated=1.")
        self.assertEqual(res["asset"], asset, "asset echo GIỮ NGUYÊN (KHÔNG asset_ref).")
        self.assertIsInstance(res["items"], list, "items[] GIỮ NGUYÊN (KHÔNG history).")

    # ── TC-BE-12-HIST-02: dưới trần → truncated=0 ∧ total == len(rows) ───────
    def test_tc_be_12_hist_02_under_limit_no_truncation(self):
        from assetcore.services.imm12 import get_asset_incident_history
        asset = self._seed(3, "02")
        res = get_asset_incident_history(asset, limit=10)
        self.assertEqual(res["total"], 3, "3 sự cố ⇒ total=3.")
        self.assertEqual(res["truncated"], 0, "3 < 10 ⇒ KHÔNG cắt.")
        self.assertEqual(res["total"], len(res["items"]),
                         "Bất biến: truncated==0 ⇒ total == len(items).")

    # ── TC-BE-12-HIST-03 (biên): vừa khít trần ⇒ KHÔNG báo cắt oan ───────────
    def test_tc_be_12_hist_03_exactly_at_limit_not_truncated(self):
        from assetcore.services.imm12 import get_asset_incident_history
        asset = self._seed(10, "03")
        res = get_asset_incident_history(asset, limit=10)
        self.assertEqual(len(res["items"]), 10, "10 sự cố, limit=10 ⇒ 10 dòng.")
        self.assertEqual(res["total"], 10, "total=10 (COUNT thật).")
        self.assertEqual(res["truncated"], 0,
                         "total == limit ⇒ vừa khít trần, KHÔNG báo cắt oan.")

    # ── TC-BE-12-HIST-04 (type-parity CR-01): int thuần, KHÔNG bool/None ─────
    def test_tc_be_12_hist_04_int_parity_not_bool(self):
        from assetcore.services.imm12 import get_asset_incident_history
        asset = self._seed(1, "04")
        res = get_asset_incident_history(asset, limit=10)
        self.assertIs(type(res["truncated"]), int,
                      "truncated PHẢI là int THUẦN — bool là subclass của int nên "
                      "assertEqual(x, 0) KHÔNG bắt được; codegen Dart/Kotlin crash.")
        self.assertIs(type(res["total"]), int, "total PHẢI là int thuần.")
        self.assertIn(res["truncated"], (0, 1), "truncated ∈ {0,1}.")

    # ── TC-BE-XX-HIST-05 (ZERO-COST): count_fn lazy ─────────────────────────
    def test_tc_be_12_hist_05_zero_cost_no_count_below_limit(self):
        """``len(rows) < limit`` ⇒ KHÔNG phát thêm query COUNT (SSoT lazy)."""
        from assetcore.services.imm12 import get_asset_incident_history
        asset = self._seed(3, "05")
        real_count = frappe.db.count
        calls: list[tuple] = []

        def _spy(*a, **kw):
            calls.append((a, kw))
            return real_count(*a, **kw)

        with patch.object(frappe.db, "count", side_effect=_spy):
            res = get_asset_incident_history(asset, limit=10)
        self.assertEqual(len(calls), 0,
                         "3 < 10 ⇒ đã lấy hết, count_fn KHÔNG được gọi "
                         "(zero-cost: truncation_meta lazy).")
        self.assertEqual(res["total"], 3, "total = len(items) khi không cắt.")

    def test_tc_be_12_hist_05b_count_called_exactly_once_at_limit(self):
        """``len(rows) >= limit`` ⇒ count_fn gọi ĐÚNG 1 lần (không N+1)."""
        from assetcore.services.imm12 import get_asset_incident_history
        asset = self._seed(12, "05b")
        real_count = frappe.db.count
        calls: list[tuple] = []

        def _spy(*a, **kw):
            calls.append((a, kw))
            return real_count(*a, **kw)

        with patch.object(frappe.db, "count", side_effect=_spy):
            res = get_asset_incident_history(asset, limit=10)
        self.assertEqual(len(calls), 1,
                         "chạm trần ⇒ ĐÚNG 1 query COUNT (không lặp/không N+1).")
        # count PHẢI dùng ĐÚNG filter {asset} như query rows (chống lệch predicate).
        args, kwargs = calls[0]
        flt = kwargs.get("filters", args[1] if len(args) > 1 else None)
        self.assertEqual(flt, {"asset": asset},
                         "count_fn PHẢI dùng ĐÚNG filter {asset} như rows.")
        self.assertEqual(res["total"], 12, "total = COUNT thật.")

    # ── INV-INCH (bẫy clamp riêng imm12): limit=0 = KHÔNG GIỚI HẠN của Frappe ─
    def test_tc_be_12_hist_06_limit_zero_falls_back_to_default_no_false_cut(self):
        """`limit_page_length=0` trong Frappe = KHÔNG GIỚI HẠN ⇒ nếu truyền `limit`
        thô vào truncation_meta thì `len(rows) < 0` là False ⇒ COUNT rồi báo cắt
        OAN. Sau CR-69: clamp TRƯỚC truy vấn (0 → default 10).
        """
        from assetcore.services.imm12 import get_asset_incident_history
        asset = self._seed(3, "06")
        res = get_asset_incident_history(asset, limit=0)
        self.assertEqual(len(res["items"]), 3, "3 sự cố ⇒ 3 dòng (trần 10).")
        self.assertEqual(res["total"], 3, "total=3.")
        self.assertEqual(res["truncated"], 0,
                         "KHÔNG dòng nào bị cắt ⇒ truncated=0 (chống báo cắt oan "
                         "khi limit=0).")

    def test_tc_be_12_hist_07_limit_above_cap_clamped_and_truthful(self):
        """INV-INCH-6: `limit=500` ⇒ rows bị clamp về trần hệ thống 100, `total`
        vẫn là COUNT THẬT (>100) ∧ `truncated=1`.

        Fixture PHẢI có > 100 sự cố: với fixture 12 dòng thì `12 < 100` và
        `12 < 500` cho kết quả Y HỆT nhau ⇒ TC không phân biệt được "có clamp"
        với "không clamp" (vacuous / false-green — LL-TEST-26). Đối xứng
        `test_imm08::test_tc_be_08_hist_06` (seed 105).
        """
        from assetcore.services.imm12 import get_asset_incident_history
        asset = self._seed(101, "07")
        res = get_asset_incident_history(asset, limit=500)
        self.assertEqual(len(res["items"]), 100,
                         "trần hệ thống _MAX_PAGE_SIZE=100 vẫn áp cho rows "
                         "(clamp TRƯỚC truy vấn), KHÔNG trả 101 dòng theo limit thô.")
        self.assertEqual(res["total"], 101,
                         "total = COUNT thật (101), KHÔNG phải số dòng đã clamp.")
        self.assertEqual(res["truncated"], 1,
                         "101 > 100 (trần THỰC ÁP) ⇒ PHẢI khai báo bị cắt.")

    # ── INV-INCH-5 (nửa CẮT): limit=0 trên thiết bị nhiều sự cố ──────────────
    def test_tc_be_12_hist_08_limit_zero_cuts_at_default_and_tells_truth(self):
        """INV-INCH-5 nửa sau: 25 sự cố, `limit=0` ⇒ `len==10` ∧ `total==25` ∧
        `truncated==1`.

        hist_06 chỉ phủ nhánh KHÔNG cắt (3 sự cố) nên không chứng minh được
        default thực áp là 10 (mọi default ≥ 3 đều xanh). TC này ghim CON SỐ
        default: đây cũng là parity `limit=0` với 2 tab anh em imm08/imm09
        (cùng `clamp_page_size(limit, 10)`).
        """
        from assetcore.services.imm12 import get_asset_incident_history
        asset = self._seed(25, "08")
        res = get_asset_incident_history(asset, limit=0)
        self.assertEqual(len(res["items"]), 10,
                         "limit=0 ⇒ rơi về default 10 của CHÍNH endpoint (KHÔNG "
                         "'không giới hạn' của Frappe, KHÔNG 20 của paginate).")
        self.assertEqual(res["total"], 25, "total = COUNT thật (25).")
        self.assertEqual(res["truncated"], 1, "25 > 10 ⇒ PHẢI khai báo bị cắt.")


# ─── AC-CR-83 — submit_rca: 3 ràng buộc hồ sơ RCA HẾT thoát envelope thành 417 ────
# Hợp đồng: docs/imm-12/05_API_Specification.md §22 · TC: 07_Testing_QA.md §IX.
# Gọi qua TẦNG API (assetcore.api.imm12.submit_rca) — KHÔNG gọi thẳng service: bug
# gốc nằm ĐÚNG ở ranh giới api↔hook (frappe.throw trần thoát khỏi `handle`).

_RCA83_MC_FIVE_WHY = "IMM12-RCA-FIVE-WHY-INCOMPLETE"
_RCA83_MC_ROOT_CAUSE = "IMM12-RCA-ROOT-CAUSE-REQUIRED"
_RCA83_MC_CORRECTIVE = "IMM12-RCA-CORRECTIVE-REQUIRED"
_RCA83_MC_ASSIGNEE = "IMM12-RCA-ASSIGNEE-REQUIRED"
_RCA83_MC_ALREADY = "IMM12-RCA-ALREADY-COMPLETED"


def _rca83_steps(holes: tuple[int, ...] = (), count: int = 5) -> list[dict]:
    """STEPS_OK (mặc định) / STEPS_HOLE<N> — bước ∈ `holes` có why_answer rỗng."""
    return [
        {
            "why_number": i,
            "why_question": f"Vì sao tầng {i}?",
            "why_answer": "" if i in holes else f"Nguyên nhân tầng {i}",
        }
        for i in range(1, count + 1)
    ]


def _rca83_make_inprogress(asset_name: str, method: str = "5-Why") -> tuple[str, str]:
    """(incident, rca) ở 'RCA In Progress' qua ĐÚNG đường người dùng thật.

    report_incident → create_rca (seed 5 bước why_answer='') → start_rca.
    Đây chính là hồ sơ mà ca lỗi phổ biến nhất (E6/E7 §22.0) rơi vào.
    """
    inc = report_incident(
        asset=asset_name,
        incident_type="Malfunction",
        severity="Low",
        description="_Test AC-CR-83 incident description for RCA envelope",
    )
    frappe.db.commit()
    rca = create_rca(inc["name"], rca_method=method)
    frappe.db.commit()
    start_rca(rca["name"])
    frappe.db.commit()
    return inc["name"], rca["name"]


def _rca83_api_submit(name: str, *, root_cause: str = "Nguyên nhân gốc rễ đã xác định",
                      corrective_action: str = "Thay bo mạch nguồn và hiệu chỉnh lại",
                      steps: list[dict] | None = None,
                      preventive_action: str = "", rca_notes: str = "") -> dict:
    """Gọi tầng API THẬT — five_why_steps đi dạng JSON-string như FE gửi."""
    from assetcore.api.imm12 import submit_rca as api_submit_rca
    return api_submit_rca(
        name,
        root_cause=root_cause,
        corrective_action=corrective_action,
        preventive_action=preventive_action,
        five_why_steps=json.dumps(steps if steps is not None else []),
        rca_notes=rca_notes,
    )


class TestRcaSubmitEnvelope(unittest.TestCase):
    """AC-CR-83 — 3 ràng buộc hồ sơ RCA trả Error envelope Decision-B + `fields`.

    INV-RCA-1 (0 ValidationError thoát ra 417) · INV-RCA-3 (khoá `fields` = tên
    tham số GHI) · INV-RCA-4 (đếm khoá) · INV-RCA-5 (KHÔNG-MUTATE) · INV-RCA-6
    (message_code cũ bất biến) · INV-RCA-8 (happy path).
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-rca83")
        # USER_RCA: HỘI 2 tầng cap (incident.acknowledge ∩ corrective.write).
        cls.user_rca = _ensure_role_user(
            "_rca83_user@assetcore.test", ["AssetCore Super Admin"])
        # USER_NOCAP: base role — thiếu corrective.write (TC-10).
        cls.user_nocap = _ensure_role_user(
            "_rca83_nocap@assetcore.test", ["AssetCore System User"])

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        purge_asset(cls.asset.name)
        for u in (cls.user_rca, cls.user_nocap):
            try:
                frappe.delete_doc("User", u, force=True, ignore_permissions=True)
            except Exception:
                pass
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        self.incident, self.rca = _rca83_make_inprogress(self.asset.name)
        # BẮT BUỘC chạy dưới persona thật: Administrator bypass permission
        # (frappe/permissions.py return True) ⇒ xanh giả.
        frappe.set_user(self.user_rca)

    def tearDown(self):
        frappe.set_user("Administrator")

    # ── TC-12-RCA83-01 — ca PHỔ BIẾN NHẤT: 1 ô Why trống ────────────────────
    def test_tc_12_rca83_01_five_why_missing_answer_returns_envelope_not_417(self):
        """AC-1: bước 3 thiếu câu trả lời ⇒ DICT envelope, KHÔNG raise 417."""
        env = _rca83_api_submit(self.rca, steps=_rca83_steps(holes=(3,)))
        self.assertIsInstance(env, dict,
                              "submit_rca PHẢI trả envelope — raise ValidationError = "
                              "HTTP-417 THÔ (không success/code/message_code/fields).")
        self.assertIs(env.get("success"), False)
        self.assertEqual(env.get("code"), ErrorCode.BUSINESS_RULE)
        self.assertEqual(env.get("http_status"), 422)
        self.assertEqual(env.get("message_code"), _RCA83_MC_FIVE_WHY)
        self.assertEqual(list((env.get("fields") or {}).keys()), ["five_why_steps.3"],
                         "fields PHẢI neo ĐÚNG dòng «Why 3» (INV-RCA-4).")
        self.assertTrue((env["fields"]["five_why_steps.3"] or "").strip(),
                        "Câu tiếng Việt KHÔNG được rỗng — FE render nguyên văn.")
        for leak in ("Traceback", "ValidationError", "_server_messages"):
            self.assertNotIn(leak, json.dumps(env, ensure_ascii=False),
                             f"Envelope KHÔNG được lộ chuỗi kỹ thuật `{leak}`.")

    # ── TC-12-RCA83-02 — thiếu bước ─────────────────────────────────────────
    def test_tc_12_rca83_02_five_why_fewer_than_five_steps(self):
        """AC-2: 3 bước ⇒ CÙNG message_code, ĐÚNG 1 khoá `five_why_steps`."""
        env = _rca83_api_submit(self.rca, steps=_rca83_steps(count=3))
        self.assertIs(env.get("success"), False)
        self.assertEqual(env.get("message_code"), _RCA83_MC_FIVE_WHY)
        self.assertEqual(list((env.get("fields") or {}).keys()), ["five_why_steps"],
                         "Ca thiếu bước ⇒ ĐÚNG 1 khoá bảng (KHÔNG khoá con) — INV-RCA-4.")
        self.assertIn("3", env["fields"]["five_why_steps"],
                      "Câu VI PHẢI nêu SỐ BƯỚC HIỆN CÓ để người dùng biết còn thiếu mấy.")

    # ── TC-12-RCA83-03 — KHÔNG-MUTATE ───────────────────────────────────────
    def test_tc_12_rca83_03_failed_submit_does_not_mutate_doc(self):
        """INV-RCA-5: pre-check chạy TRƯỚC mọi phép gán ⇒ hồ sơ giữ nguyên."""
        frappe.set_user("Administrator")
        before = frappe.db.get_value(
            "IMM RCA Record", self.rca,
            ["status", "root_cause", "corrective_action_summary",
             "completed_by", "completed_date"], as_dict=True)
        frappe.set_user(self.user_rca)
        env = _rca83_api_submit(self.rca, steps=_rca83_steps(count=3))
        self.assertIs(env.get("success"), False)
        frappe.set_user("Administrator")
        after = frappe.db.get_value(
            "IMM RCA Record", self.rca,
            ["status", "root_cause", "corrective_action_summary",
             "completed_by", "completed_date"], as_dict=True)
        self.assertEqual(after.status, "RCA In Progress",
                         "Hồ sơ bị từ chối PHẢI giữ 'RCA In Progress'.")
        self.assertEqual(dict(after), dict(before),
                         "KHÔNG-MUTATE: 5 field PHẢI y nguyên giá trị trước lệnh "
                         "(ghi-nửa-chừng = hồ sơ NĐ98 sai sự thật).")

    # ── TC-12-RCA83-04 — hợp đồng cũ + fields mới ───────────────────────────
    def test_tc_12_rca83_04_root_cause_required_now_carries_fields(self):
        """AC-3 / INV-RCA-6: message_code CŨ giữ nguyên, chỉ THÊM `fields`."""
        env = _rca83_api_submit(self.rca, root_cause="   ", steps=_rca83_steps())
        self.assertEqual(env.get("message_code"), _RCA83_MC_ROOT_CAUSE,
                         "KHÔNG được đổi message_code cũ (client đang route theo).")
        self.assertEqual(env.get("http_status"), 422)
        self.assertEqual(list((env.get("fields") or {}).keys()), ["root_cause"])

    # ── TC-12-RCA83-05 — khoá `fields` = tên tham số GHI ────────────────────
    def test_tc_12_rca83_05_corrective_required_field_key_is_write_param_name(self):
        """INV-RCA-3 (CR-52 quirk 2): `corrective_action`, KHÔNG `..._summary`."""
        env = _rca83_api_submit(self.rca, corrective_action="", steps=_rca83_steps())
        self.assertEqual(env.get("message_code"), _RCA83_MC_CORRECTIVE)
        fields = env.get("fields") or {}
        self.assertIn("corrective_action", fields,
                      "Khoá PHẢI là TÊN THAM SỐ GHI — client neo vào ô nhập.")
        self.assertNotIn("corrective_action_summary", fields,
                         "Tên field ĐỌC = ô không tồn tại trên form ⇒ lỗi 'tàng hình'.")

    # ── TC-12-RCA83-06 — thiếu phân công ────────────────────────────────────
    def test_tc_12_rca83_06_assignee_required_envelope(self):
        """D-RCA-4: start_rca bypass validate ⇒ service PHẢI tự kiểm assigned_to."""
        frappe.set_user("Administrator")
        frappe.db.set_value("IMM RCA Record", self.rca, "assigned_to", "",
                            update_modified=False)
        frappe.db.commit()
        frappe.set_user(self.user_rca)
        env = _rca83_api_submit(self.rca, steps=_rca83_steps())
        self.assertIs(env.get("success"), False)
        self.assertEqual(env.get("message_code"), _RCA83_MC_ASSIGNEE)
        self.assertEqual(env.get("http_status"), 422)
        self.assertEqual(list((env.get("fields") or {}).keys()), ["assigned_to"])

    # ── TC-12-RCA83-07 — gom ĐỦ dòng khuyết (ADR-IMM12-15) ──────────────────
    def test_tc_12_rca83_07_multiple_holes_yield_one_code_and_all_field_keys(self):
        """INV-RCA-4: 3 ô trống ⇒ 3 khoá con, 1 message_code (không sửa-thử 3 vòng)."""
        env = _rca83_api_submit(self.rca, steps=_rca83_steps(holes=(2, 3, 5)))
        self.assertEqual(env.get("message_code"), _RCA83_MC_FIVE_WHY)
        self.assertEqual(sorted((env.get("fields") or {}).keys()),
                         ["five_why_steps.2", "five_why_steps.3", "five_why_steps.5"])

    # ── TC-12-RCA83-08 — happy path (AC-6 / INV-RCA-8) ──────────────────────
    def test_tc_12_rca83_08_happy_path_completes_and_creates_capa(self):
        """5 bước đủ ⇒ Completed + auto-CAPA + chuỗi on_rca_completed y như trước."""
        env = _rca83_api_submit(self.rca, steps=_rca83_steps())
        self.assertIs(env.get("success"), True, f"Happy path PHẢI xanh: {env}")
        self.assertEqual((env.get("data") or {}).get("status"), "Completed")
        self.assertNotIn("fields", env,
                         "Envelope thành công KHÔNG được kèm `fields` (chống vacuous).")
        frappe.set_user("Administrator")
        self.assertEqual(
            frappe.db.get_value("IMM RCA Record", self.rca, "status"), "Completed")
        self.assertTrue(
            frappe.db.exists("IMM CAPA Record", {"linked_incident": self.incident}),
            "BR-12-06: RCA hoàn tất PHẢI sinh CAPA gắn sự cố (chuỗi không regress).")

    # ── TC-12-RCA83-09 — gọi lại lần 2 ──────────────────────────────────────
    def test_tc_12_rca83_09_second_submit_is_already_completed_without_fields(self):
        """§22.2 hàng 5: 409 + KHÔNG `fields` (không phải lỗi của một ô nhập)."""
        first = _rca83_api_submit(self.rca, steps=_rca83_steps())
        self.assertIs(first.get("success"), True, f"Lần 1 phải xanh: {first}")
        env = _rca83_api_submit(self.rca, steps=_rca83_steps())
        self.assertEqual(env.get("message_code"), _RCA83_MC_ALREADY)
        self.assertEqual(env.get("http_status"), 409)
        self.assertNotIn("fields", env)

    # ── TC-12-RCA83-10 — thiếu quyền (D-RCA-1) ──────────────────────────────
    def test_tc_12_rca83_10_missing_capability_is_403_in_envelope(self):
        """403 IN-ENVELOPE trên HTTP-200, message KHÔNG leak chuỗi capability."""
        frappe.set_user(self.user_nocap)
        try:
            env = _rca83_api_submit(self.rca, steps=_rca83_steps())
        finally:
            frappe.set_user("Administrator")
        self.assertIsInstance(env, dict)
        self.assertEqual(env.get("code"), ErrorCode.FORBIDDEN)
        self.assertEqual(env.get("http_status"), 403)
        self.assertNotIn("corrective.write", json.dumps(env, ensure_ascii=False))
        self.assertEqual(
            frappe.db.get_value("IMM RCA Record", self.rca, "status"),
            "RCA In Progress", "Thiếu quyền ⇒ KHÔNG transition.")

    # ── TC-12-RCA83-13 — non-regress phương pháp khác (D-RCA-3) ─────────────
    def test_tc_12_rca83_13_non_five_why_method_is_untouched(self):
        """rca_method='Fishbone' + 0 bước ⇒ vẫn hoàn thành (không mở rộng luật)."""
        frappe.set_user("Administrator")
        _inc, rca = _rca83_make_inprogress(self.asset.name, method="Fishbone")
        # Xoá sạch bảng con: chứng minh predicate KHÔNG áp cho phương pháp khác
        # (0 bước mà vẫn hoàn thành = D-RCA-3 giữ nguyên, không mở rộng luật).
        frappe.db.sql("DELETE FROM `tabIMM RCA Five Why Step` WHERE parent=%s", (rca,))
        frappe.db.commit()
        frappe.set_user(self.user_rca)
        env = _rca83_api_submit(rca, steps=[])
        self.assertIs(env.get("success"), True,
                      f"Phương pháp không chứa 'why' KHÔNG bị kiểm 5-Why: {env}")


class TestRcaValidatorSsot(unittest.TestCase):
    """AC-4 / AC-5 — MỘT predicate cho service + hook; controller 0 `frappe.throw`."""

    _CONTROLLER = "assetcore/assetcore/doctype/imm_rca_record/imm_rca_record.py"

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-rca83ssot")

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        purge_asset(cls.asset.name)

    def setUp(self):
        frappe.set_user("Administrator")

    def _controller_source(self) -> str:
        import assetcore.assetcore.doctype.imm_rca_record.imm_rca_record as mod
        return open(mod.__file__, encoding="utf-8").read()

    # ── TC-12-RCA83-11 (GUARD tĩnh) ─────────────────────────────────────────
    def test_tc_12_rca83_11_no_bare_frappe_throw_in_rca_controller(self):
        """INV-RCA-9: 0 `frappe.throw(` ∧ dùng CHUNG 3 predicate ∧ 0 luật thứ hai."""
        import ast

        src = self._controller_source()
        tree = ast.parse(src)
        throws = [
            n for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == "throw"
            and isinstance(n.func.value, ast.Name) and n.func.value.id == "frappe"
        ]
        self.assertEqual(
            [n.lineno for n in throws], [],
            "Controller RCA PHẢI 0 `frappe.throw(` — mọi lỗi tối thiểu mang "
            "message_code (đi qua nthrow_in_hook).")
        imported = {
            alias.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
            for alias in n.names
        }
        for sym in ("validate_five_why_payload", "validate_rca_assignment",
                    "validate_rca_completion"):
            self.assertIn(sym, imported,
                          f"Hook PHẢI import CHÍNH `{sym}` từ services.imm12 (SSoT).")
        # 0 "luật thứ hai": validator 5-Why của controller KHÔNG được tự lặp trên
        # bảng con hay tự so số bước — chỉ ủy quyền cho predicate SSoT.
        # (`before_save` VẪN được đọc `why_answer` để suy root_cause — đó là phép
        # DẪN XUẤT, không phải luật kiểm tra.)
        fn = next((n for n in ast.walk(tree)
                   if isinstance(n, ast.FunctionDef)
                   and n.name == "_validate_five_why_when_method_5why"), None)
        self.assertIsNotNone(fn, "Hook backstop 5-Why PHẢI còn (defense-in-depth).")
        self.assertEqual(
            [n for n in ast.walk(fn) if isinstance(n, (ast.For, ast.While))], [],
            "Vòng lặp kiểm 5-Why trong controller = bản kiểm tra THỨ HAI "
            "(class-of-bug display⇔enforcement) — phải gọi predicate SSoT.")
        self.assertEqual(
            [c for c in ast.walk(fn)
             if isinstance(c, ast.Constant) and c.value == 5], [],
            "Controller KHÔNG được tự khẳng định 'đủ 5 bước' — hằng số đó thuộc "
            "predicate SSoT (sửa 1 chỗ ⇒ cả 2 đổi).")
        called = {c.func.id for c in ast.walk(fn)
                  if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
        self.assertIn("validate_five_why_payload", called,
                      "Hook PHẢI GỌI chính predicate SSoT.")

    # ── TC-12-RCA83-12 (parity 2 kênh) ──────────────────────────────────────
    def test_tc_12_rca83_12_hook_backstop_shares_predicate(self):
        """AC-4: doc.save() trực tiếp ⇒ ValidationError CÓ message_code cùng mã."""
        _inc, rca = _rca83_make_inprogress(self.asset.name)
        doc = frappe.get_doc("IMM RCA Record", rca)
        doc.status = "RCA In Progress"
        for row in doc.get("five_why_steps") or []:
            row.why_answer = "" if row.why_number == 3 else f"Đáp án {row.why_number}"
        frappe.local.response.pop("message_code", None)
        with self.assertRaises(frappe.ValidationError):
            doc.save(ignore_permissions=True)
        self.assertEqual(frappe.local.response.get("message_code"), _RCA83_MC_FIVE_WHY,
                         "Hook backstop PHẢI dùng CÙNG predicate/CÙNG mã với service "
                         "(patch 1 chỗ ⇒ cả 2 đổi — INV-RCA-2).")

    def test_tc_12_rca83_12b_hook_calls_shared_predicate_symbol(self):
        """INV-RCA-2 (mutation-proof): patch symbol service ⇒ hook đổi hành vi."""
        from unittest.mock import patch as _patch

        _inc, rca = _rca83_make_inprogress(self.asset.name)
        doc = frappe.get_doc("IMM RCA Record", rca)
        doc.status = "RCA In Progress"
        for row in doc.get("five_why_steps") or []:
            row.why_answer = f"Đáp án {row.why_number}"
        with _patch("assetcore.services.imm12.validate_five_why_payload",
                    return_value={"message_code": MSG.IMM12_RCA_FIVE_WHY_INCOMPLETE,
                                  "fields": {"five_why_steps": "x"},
                                  "context": {"detail": "x"}}):
            with self.assertRaises(frappe.ValidationError):
                doc.save(ignore_permissions=True)
