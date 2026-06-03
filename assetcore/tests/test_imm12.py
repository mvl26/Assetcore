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

