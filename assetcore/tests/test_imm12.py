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
