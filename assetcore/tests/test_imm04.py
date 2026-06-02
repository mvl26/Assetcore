# Copyright (c) 2026, AssetCore Team
"""IMM-04 unit tests — Gates G01/G03/G05-G06, VR-01, VR-07, log_lifecycle_event.

Run: bench --site miyano run-tests --app assetcore --module assetcore.tests.test_imm04
"""
from __future__ import annotations

import unittest

import frappe
from frappe.utils import nowdate, add_days

from assetcore.services.imm04 import (
    check_auto_clinical_hold,
    log_lifecycle_event,
    validate_gate_g01,
    validate_gate_g03,
    validate_gate_g05_g06,
    _vr01_unique_serial_number,
)
from assetcore.services.shared import ServiceError


# ─── Minimal stubs ────────────────────────────────────────────────────────────

def _make_doc(**kwargs):
    """Return a lightweight Frappe-like dict-obj that services can call .get() on."""
    doc = frappe._dict(kwargs)
    doc.setdefault("name", "_TEST-COMM-001")
    doc.setdefault("workflow_state", "To Be Installed")
    doc.setdefault("commissioning_documents", [])
    doc.setdefault("baseline_tests", [])
    doc.setdefault("board_approver", None)
    doc.setdefault("risk_class", "B")
    doc.setdefault("is_radiation_device", 0)
    doc.setdefault("vendor_serial_no", "")
    doc.setdefault("final_asset", None)
    doc.setdefault("documents_incomplete", 0)
    doc.setdefault("documents_incomplete_note", "")
    # Mimic frappe.model.document.Document.get()
    doc.get = lambda field, default=None: doc.__dict__.get(field, default) if hasattr(doc, "__dict__") else doc._dict.get(field, default)  # noqa: E501
    return doc


def _comm_doc_row(**kwargs):
    r = frappe._dict(kwargs)
    r.get = lambda k, d=None: r._dict.get(k, d)
    return r


# ─── Gate G01 ────────────────────────────────────────────────────────────────

class TestGateG01(unittest.TestCase):

    def _doc_with_docs(self, statuses: list[tuple[str, bool]]):
        """statuses: list of (status, is_mandatory)"""
        doc = _make_doc(workflow_state="To Be Installed")
        for status, mandatory in statuses:
            doc.commissioning_documents.append(
                _comm_doc_row(doc_type="CO", is_mandatory=int(mandatory), status=status)
            )
        return doc

    def test_all_received_passes(self):
        doc = self._doc_with_docs([("Received", True), ("Received", True)])
        validate_gate_g01(doc)  # must not raise

    def test_all_waived_passes(self):
        doc = self._doc_with_docs([("Waived", True), ("Received", True)])
        validate_gate_g01(doc)

    def test_one_pending_mandatory_blocks(self):
        doc = self._doc_with_docs([("Received", True), ("Pending", True)])
        with self.assertRaises(frappe.ValidationError):
            validate_gate_g01(doc)

    def test_pending_non_mandatory_passes(self):
        doc = self._doc_with_docs([("Received", True), ("Pending", False)])
        validate_gate_g01(doc)  # non-mandatory Pending is fine

    def test_draft_state_skips_check(self):
        doc = self._doc_with_docs([("Pending", True)])
        doc.workflow_state = "Draft"
        validate_gate_g01(doc)  # no raise for Draft

    def test_pending_doc_verify_skips_check(self):
        doc = self._doc_with_docs([("Pending", True)])
        doc.workflow_state = "Pending Doc Verify"
        validate_gate_g01(doc)

    def test_incomplete_flag_with_note_bypasses(self):
        doc = self._doc_with_docs([("Pending", True)])
        doc.documents_incomplete = 1
        doc.documents_incomplete_note = "Will supply CO within 7 days"
        validate_gate_g01(doc)  # warned but not blocked

    def test_incomplete_flag_without_note_still_blocks(self):
        doc = self._doc_with_docs([("Pending", True)])
        doc.documents_incomplete = 1
        doc.documents_incomplete_note = "   "
        with self.assertRaises(frappe.ValidationError):
            validate_gate_g01(doc)


# ─── Gate G03 ────────────────────────────────────────────────────────────────

class TestGateG03(unittest.TestCase):

    def _doc_with_tests(self, results: list[str], state="Clinical Release"):
        doc = _make_doc(workflow_state=state)
        for r in results:
            doc.baseline_tests.append(frappe._dict(parameter=f"CHK-{r}", test_result=r))
        return doc

    def test_all_pass_passes(self):
        doc = self._doc_with_tests(["Pass", "Pass", "Pass"])
        validate_gate_g03(doc)

    def test_na_counts_as_pass(self):
        doc = self._doc_with_tests(["Pass", "N/A"])
        validate_gate_g03(doc)

    def test_one_fail_blocks(self):
        doc = self._doc_with_tests(["Pass", "Fail"])
        with self.assertRaises(frappe.ValidationError):
            validate_gate_g03(doc)

    def test_non_clinical_release_state_skipped(self):
        doc = self._doc_with_tests(["Fail"])
        doc.workflow_state = "To Be Installed"
        validate_gate_g03(doc)  # only enforced at Clinical Release / Re Inspection


# ─── Gate G05 + G06 ──────────────────────────────────────────────────────────

class TestGateG05G06(unittest.TestCase):

    def setUp(self):
        frappe.set_user("Administrator")
        # Make sure there is a test commissioning record for NC count queries
        if not frappe.db.exists("Asset Commissioning", "_TEST-COMM-G05"):
            frappe.db.sql(
                "INSERT INTO `tabAsset Commissioning` (name, docstatus, workflow_state) "
                "VALUES ('_TEST-COMM-G05', 0, 'Clinical Release')"
            )
        frappe.db.commit()

    def tearDown(self):
        frappe.db.delete("Asset QA Non Conformance", {"ref_commissioning": "_TEST-COMM-G05"})
        frappe.db.delete("Asset Commissioning", {"name": "_TEST-COMM-G05"})
        frappe.db.commit()

    def test_no_nc_with_approver_passes(self):
        doc = _make_doc(name="_TEST-COMM-G05", workflow_state="Clinical Release", board_approver="Administrator")
        validate_gate_g05_g06(doc)

    def test_no_approver_blocks(self):
        doc = _make_doc(name="_TEST-COMM-G05", workflow_state="Clinical Release", board_approver=None)
        with self.assertRaises(frappe.ValidationError):
            validate_gate_g05_g06(doc)

    def test_non_clinical_release_skipped(self):
        doc = _make_doc(name="_TEST-COMM-G05", workflow_state="Identification", board_approver=None)
        validate_gate_g05_g06(doc)  # no raise


# ─── VR-01 Unique Serial ──────────────────────────────────────────────────────

class TestVR01UniqueSerial(unittest.TestCase):

    def test_empty_sn_skipped(self):
        doc = _make_doc(vendor_serial_no="")
        _vr01_unique_serial_number(doc)  # no raise

    def test_new_sn_passes(self):
        doc = _make_doc(vendor_serial_no="_TEST-SN-NOT-USED-9999")
        _vr01_unique_serial_number(doc)  # no raise


# ─── VR-07 Clinical Hold ─────────────────────────────────────────────────────

class TestVR07ClinicalHold(unittest.TestCase):

    def test_class_a_no_hold(self):
        doc = _make_doc(risk_class="A", is_radiation_device=0)
        self.assertFalse(check_auto_clinical_hold(doc))

    def test_class_b_no_hold(self):
        doc = _make_doc(risk_class="B", is_radiation_device=0)
        self.assertFalse(check_auto_clinical_hold(doc))

    def test_class_c_hold(self):
        doc = _make_doc(risk_class="C", is_radiation_device=0)
        self.assertTrue(check_auto_clinical_hold(doc))

    def test_class_d_hold(self):
        doc = _make_doc(risk_class="D", is_radiation_device=0)
        self.assertTrue(check_auto_clinical_hold(doc))

    def test_radiation_hold(self):
        # When risk_class is absent, is_radiation_device flag is used
        doc = _make_doc(risk_class="", is_radiation_device=1)
        self.assertTrue(check_auto_clinical_hold(doc))

    def test_radiation_class_sets_flag(self):
        doc = _make_doc(risk_class="Radiation", is_radiation_device=0)
        check_auto_clinical_hold(doc)
        self.assertEqual(doc.is_radiation_device, 1)


# ─── log_lifecycle_event ─────────────────────────────────────────────────────

class _FakeDoc:
    """Minimal stand-in with a real append() method for lifecycle_event tests."""
    def __init__(self, **kwargs):
        self.lifecycle_events = []
        self.name = kwargs.pop("name", "_TEST-FAKE")
        self.__dict__.update(kwargs)

    def append(self, field, row):
        getattr(self, field).append(frappe._dict(row))

    def get(self, field, default=None):
        return getattr(self, field, default)


class TestLogLifecycleEvent(unittest.TestCase):

    def test_event_appended(self):
        doc = _FakeDoc()
        log_lifecycle_event(doc, "status_changed", "Draft", "To Be Installed")
        self.assertEqual(len(doc.lifecycle_events), 1)
        ev = doc.lifecycle_events[0]
        self.assertEqual(ev.event_type, "status_changed")
        self.assertEqual(ev.from_status, "Draft")
        self.assertEqual(ev.to_status, "To Be Installed")
        self.assertEqual(ev.actor, frappe.session.user)

    def test_no_lifecycle_events_attr_is_noop(self):
        doc = _FakeDoc()
        del doc.lifecycle_events  # remove the attribute
        log_lifecycle_event(doc, "status_changed", "Draft", "To Be Installed")  # no crash


# ─── RC-05: log_lifecycle_event must persist to canonical IMM Audit Trail ─────

class TestRC05AuditTrailNotEmpty(unittest.TestCase):
    """RC-05: mọi state transition của Asset Commissioning phải để lại 1 row
    trong `IMM Audit Trail` (SHA-256 chained). Trước fix, child table
    `lifecycle_events` không tồn tại trong DocType JSON → no-op silently.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        # Real commissioning row so the FK on IMM Audit Trail.ref_name is valid
        if not frappe.db.exists("Asset Commissioning", "_TEST-RC05-AUDIT"):
            frappe.db.sql(
                "INSERT INTO `tabAsset Commissioning` "
                "(name, docstatus, workflow_state) "
                "VALUES ('_TEST-RC05-AUDIT', 0, 'To Be Installed')"
            )
            frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.db.delete("IMM Audit Trail", {"ref_name": "_TEST-RC05-AUDIT"})
        frappe.db.delete("Asset Commissioning", {"name": "_TEST-RC05-AUDIT"})
        frappe.db.commit()

    def test_log_lifecycle_event_writes_audit_trail_row(self):
        doc = _FakeDoc(name="_TEST-RC05-AUDIT")
        doc.workflow_state = "Pending Doc Verify"
        before = frappe.db.count(
            "IMM Audit Trail", {"ref_name": "_TEST-RC05-AUDIT"}
        )
        log_lifecycle_event(
            doc, "Xác nhận đủ tài liệu",
            "Pending Doc Verify", "To Be Installed",
            remarks="_TEST-RC05",
        )
        after = frappe.db.count(
            "IMM Audit Trail", {"ref_name": "_TEST-RC05-AUDIT"}
        )
        self.assertGreater(
            after, before,
            "RC-05: log_lifecycle_event phải tạo row mới trong IMM Audit Trail "
            "(canonical SHA-256 chained audit log) — không chỉ append vào "
            "child table không tồn tại.",
        )


# ─── AUTH-05: 4-eyes / Separation-of-Duties ──────────────────────────────────

class TestAUTH05FourEyes(unittest.TestCase):
    """AUTH-05: 1 user không được vừa tạo phiếu vừa duyệt phiếu.

    Cụ thể: `assert_distinct_signers` raises ServiceError(FORBIDDEN) khi
    candidate_user đã đảm nhiệm 1 vai khác trên cùng phiếu (clinical_head,
    qa_officer, board_approver, owner...).
    """

    def test_same_user_cannot_be_clinical_head_and_qa_officer(self):
        from assetcore.services.shared import assert_distinct_signers
        doc = _make_doc(
            clinical_head="reviewer@test.local",
            qa_officer="",
            board_approver="",
            owner="other@test.local",
        )
        with self.assertRaises(ServiceError) as ctx:
            assert_distinct_signers(
                doc, "clinical_head", "qa_officer", "board_approver", "owner",
                candidate_user="reviewer@test.local",
                candidate_field="qa_officer",
            )
        self.assertIn("4-eyes", str(ctx.exception))

    def test_distinct_signers_passes_for_different_users(self):
        from assetcore.services.shared import assert_distinct_signers
        doc = _make_doc(
            clinical_head="alice@test.local",
            qa_officer="",
            board_approver="charlie@test.local",
            owner="dave@test.local",
        )
        # bob is fresh — should not raise
        assert_distinct_signers(
            doc, "clinical_head", "qa_officer", "board_approver", "owner",
            candidate_user="bob@test.local",
            candidate_field="qa_officer",
        )

    def test_self_submitter_cannot_approve_own_phieu(self):
        from assetcore.services.shared import assert_not_self_submitter
        doc = _make_doc(owner="alice@test.local")
        with self.assertRaises(ServiceError) as ctx:
            assert_not_self_submitter(
                doc, submitter_field="owner",
                candidate_user="alice@test.local",
            )
        self.assertIn("4-eyes", str(ctx.exception))

    def test_self_submitter_allows_other_user_approve(self):
        from assetcore.services.shared import assert_not_self_submitter
        doc = _make_doc(owner="alice@test.local")
        # No raise — different user is fine.
        assert_not_self_submitter(
            doc, submitter_field="owner",
            candidate_user="bob@test.local",
        )


# ─── RC-06: Auto-mint AC Asset on Clinical Release ───────────────────────────

class TestRC06AssetAutoMint(unittest.TestCase):
    """RC-06: phiếu nghiệm thu IMM-04 đạt 'Clinical Release' → tự sinh AC Asset.

    Test cấp service: `create_ac_asset(doc)` được gọi → idempotent (gọi 2 lần
    không tạo asset thứ hai). Test cấp transition (qua `transition_state`)
    được cover bởi integration tests khác — ở đây ta verify đơn vị mạch chuyển
    qua công thức quan trọng.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls._created_assets: list[str] = []

    @classmethod
    def tearDownClass(cls):
        for name in cls._created_assets:
            try:
                frappe.delete_doc("AC Asset", name, force=True,
                                  ignore_permissions=True)
            except Exception:
                pass

    def test_create_ac_asset_returns_existing_when_already_set(self):
        from assetcore.services.imm04 import create_ac_asset
        doc = _make_doc(final_asset="_PRE_EXISTING_ASSET_NAME")
        result = create_ac_asset(doc)
        self.assertEqual(
            result, "_PRE_EXISTING_ASSET_NAME",
            "RC-06: nếu phiếu đã có final_asset, create_ac_asset trả về luôn — "
            "không tạo asset thứ 2 (idempotent).",
        )


# ─── R20: submit/cancel RBAC must use REAL roles (capability), not dead names ──
# Bug gốc (giống IMM-12 P1): _SUBMIT_ROLES = {"IMM Operations Manager",
# "IMM Workshop Lead"} — KHÔNG tồn tại trong fixtures/role.json → mọi
# Commissioning Manager (kể cả Super Admin) bị FORBIDDEN → submit/cancel
# commissioning chết. Fix: gate qua rbac capability commissioning.submit/cancel.

class TestCommissioningSubmitRbac(unittest.TestCase):
    """R20 regression: Commissioning Manager PHẢI qua được role-gate của
    submit_commissioning (không bị FORBIDDEN bởi role-name bịa)."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.mgr = "_test_comm_mgr@assetcore.test"
        if not frappe.db.exists("User", cls.mgr):
            u = frappe.get_doc({
                "doctype": "User", "email": cls.mgr,
                "first_name": "comm_mgr", "send_welcome_email": 0, "enabled": 1,
            }).insert(ignore_permissions=True)
        else:
            u = frappe.get_doc("User", cls.mgr)
        if "Commissioning Manager" not in {r.role for r in u.get("roles", [])}:
            u.append("roles", {"role": "Commissioning Manager"})
            u.save(ignore_permissions=True)
        # Phiếu commissioning thật ở state KHÔNG phải Clinical Release (Draft).
        doc = frappe.get_doc({
            "doctype": "Asset Commissioning",
            "workflow_state": "Draft",  # Draft skip Gate G01 (đang soạn)
        }).insert(ignore_permissions=True, ignore_mandatory=True, ignore_links=True)
        cls.comm = doc.name
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        try:
            frappe.delete_doc("Asset Commissioning", cls.comm, force=True,
                              ignore_permissions=True)
        except Exception:
            pass
        try:
            frappe.delete_doc("User", cls.mgr, force=True, ignore_permissions=True)
        except Exception:
            pass
        frappe.db.commit()

    def test_commissioning_manager_passes_submit_role_gate(self):
        """Commissioning Manager KHÔNG được bị FORBIDDEN ở role-gate. Phiếu ở
        state Draft → kỳ vọng lỗi STATE (INVALID_PARAMS), KHÔNG phải FORBIDDEN."""
        from assetcore.services.imm04 import submit_commissioning
        from assetcore.services.shared import ErrorCode
        frappe.set_user(self.mgr)
        try:
            with self.assertRaises(ServiceError) as ctx:
                submit_commissioning(self.comm)
            self.assertNotEqual(
                ctx.exception.code, ErrorCode.FORBIDDEN,
                "Commissioning Manager bị chặn FORBIDDEN ở submit — role-gate "
                "đang dùng role-name không tồn tại (bug IMM-12 lặp lại ở IMM-04)",
            )
        finally:
            frappe.set_user("Administrator")


# ─── R22: submit_for_approval _STAGE_ROLE must use REAL roles ─────────────────
# Bug (cùng họ R20/IMM-12): _STAGE_ROLE map stage -> "IMM Biomed Technician" /
# "IMM Operations Manager" — KHÔNG tồn tại → required_role không bao giờ nằm
# trong frappe.get_roles(approver) → MỌI approver không-super-admin bị FORBIDDEN
# "không có vai trò 'IMM Biomed Technician'" → flow gửi-duyệt commissioning chết.
# Fix: map sang role THẬT (Maintenance User cho stage kỹ thuật, Commissioning
# Manager cho Clinical Release).

class TestSubmitForApprovalStageRole(unittest.TestCase):
    """R22 regression: approver mang role THẬT của stage PHẢI qua được gate
    _STAGE_ROLE (không bị FORBIDDEN bởi role-name bịa)."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.tech = "_test_r22_tech@assetcore.test"
        cls.submitter = "_test_r22_sub@assetcore.test"
        for email, role, fn in (
            (cls.tech, "Maintenance User", "r22tech"),
            (cls.submitter, "Maintenance User", "r22sub"),
        ):
            if not frappe.db.exists("User", email):
                u = frappe.get_doc({
                    "doctype": "User", "email": email, "first_name": fn,
                    "send_welcome_email": 0, "enabled": 1,
                }).insert(ignore_permissions=True)
            else:
                u = frappe.get_doc("User", email)
            if role not in {r.role for r in u.get("roles", [])}:
                u.append("roles", {"role": role})
                u.save(ignore_permissions=True)
        doc = frappe.get_doc({
            "doctype": "Asset Commissioning",
            "workflow_state": "Draft",
        }).insert(ignore_permissions=True, ignore_mandatory=True, ignore_links=True)
        # Đặt state qua db_set để né workflow transition validation.
        doc.db_set("workflow_state", "Pending Doc Verify", update_modified=False)  # -> stage "Doc Verify"
        cls.comm = doc.name
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for ref, dt in ((cls.comm, "Asset Commissioning"),
                        (cls.tech, "User"), (cls.submitter, "User")):
            try:
                frappe.delete_doc(dt, ref, force=True, ignore_permissions=True)
            except Exception:
                pass
        frappe.db.commit()

    def test_real_role_approver_passes_stage_gate(self):
        """Maintenance User (role THẬT của stage Doc Verify) KHÔNG được bị
        FORBIDDEN bởi _STAGE_ROLE. Submitter khác approver để qua 4-eyes."""
        from assetcore.services.imm04 import submit_for_approval
        from assetcore.services.shared import ErrorCode
        frappe.set_user(self.submitter)
        try:
            try:
                submit_for_approval(self.comm, approver=self.tech, stage="Doc Verify")
            except ServiceError as e:
                self.assertNotEqual(
                    e.code, ErrorCode.FORBIDDEN,
                    "Approver mang role THẬT của stage bị FORBIDDEN — _STAGE_ROLE "
                    "đang trỏ role-name không tồn tại (dead-gate R22)",
                )
        finally:
            frappe.set_user("Administrator")


if __name__ == "__main__":
    unittest.main()
