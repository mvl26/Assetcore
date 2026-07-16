"""IMM-12 Incident Report — test suite.

Run: bench --site miyano run-tests --module assetcore.tests.test_imm12
"""
from __future__ import annotations

import json
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
    reopen_incident,
    request_rca,
    get_incident_detail,
    list_rcas,
    get_rca,
    start_rca,
    submit_rca,
    cancel_rca,
    _RCA_VALID_TRANSITIONS,
    _VALID_TRANSITIONS,
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
