# Copyright (c) 2026, AssetCore Team
"""IMM-04 unit tests — Gates G01/G03/G05-G06, VR-01, VR-07, log_lifecycle_event.

Run: bench --site miyano run-tests --app assetcore --module assetcore.tests.test_imm04
"""
from __future__ import annotations

import unittest

import frappe
from frappe.utils import nowdate, add_days

from assetcore.api.imm04 import get_gate_status
from assetcore.services.imm04 import (
    check_auto_clinical_hold,
    evaluate_gate_status,
    gate_g04_applies,
    gate_g04_ok,
    log_lifecycle_event,
    validate_gate_g01,
    validate_gate_g03,
    validate_gate_g05_g06,
    _count_open_ncs,
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


# ─── Gate G05 card⟺validator parity (CR-54 §3, BR-04-13) ──────────────────────
# Guard the display⟺enforcement invariant: the G05 gate CARD (api.get_gate_status
# .g05_nc) and the ENFORCEMENT validator (services.validate_gate_g05_g06) must both
# derive "no open NC" from the SAME SSoT predicate `_count_open_ncs` ('Open'-only).
# Before the fix the card counted resolution_status != 'Closed' → falsely blocked
# non-Open NCs (Resolved / Under Review / Transferred) the validator lets through.
_NC_STATES = ("Open", "Under Review", "Resolved", "Closed", "Transferred")


class TestGateG05CardValidatorParity(unittest.TestCase):

    def setUp(self):
        frappe.set_user("Administrator")
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

    # ── helpers ───────────────────────────────────────────────────────────────
    def _reset_ncs(self):
        frappe.db.delete("Asset QA Non Conformance", {"ref_commissioning": "_TEST-COMM-G05"})
        frappe.db.commit()

    def _insert_nc(self, status: str) -> str:
        nc = frappe.get_doc({
            "doctype": "Asset QA Non Conformance",
            "ref_commissioning": "_TEST-COMM-G05",
            "nc_type": "Technical",
            "resolution_status": status,
            "description": "G05 parity fixture NC",
        })
        nc.insert(ignore_permissions=True)
        frappe.db.commit()
        return nc.name

    def _card_g05_nc(self) -> bool:
        resp = get_gate_status("_TEST-COMM-G05")
        self.assertTrue(resp.get("success"), resp)
        return resp["data"]["g05_nc"]

    def _validator_raises(self) -> bool:
        # board_approver set so G06 always passes → G05 (NC) is the sole variable.
        doc = _make_doc(name="_TEST-COMM-G05", workflow_state="Clinical Release",
                        board_approver="Administrator")
        try:
            validate_gate_g05_g06(doc)
            return False
        except frappe.ValidationError:
            return True

    # ── tests ─────────────────────────────────────────────────────────────────
    def test_g05_nc_open_blocks_and_card_fails(self):
        """AC3: NC 'Open' → card g05_nc False AND validator raises (parity: both block)."""
        self._insert_nc("Open")
        self.assertFalse(self._card_g05_nc())
        self.assertTrue(self._validator_raises())

    def test_g05_nc_resolved_card_passes_matches_validator(self):
        """AC2: NC 'Resolved' (non-Open) → card g05_nc True AND validator no-raise.

        RED before fix: old card counted !='Closed' → returned False (false block).
        """
        self._insert_nc("Resolved")
        self.assertTrue(self._card_g05_nc())
        self.assertFalse(self._validator_raises())

    def test_g05_nc_under_review_passes(self):
        """AC2: NC 'Under Review' (non-Open) → card g05_nc True AND validator no-raise."""
        self._insert_nc("Under Review")
        self.assertTrue(self._card_g05_nc())
        self.assertFalse(self._validator_raises())

    def test_g05_nc_no_nc_passes(self):
        """Baseline: 0 NC → card g05_nc True AND validator no-raise."""
        self._reset_ncs()
        self.assertTrue(self._card_g05_nc())
        self.assertFalse(self._validator_raises())

    def test_g05_nc_invariant_card_iff_validator(self):
        """AC1/AC4: for ALL 5 resolution_status, (card g05_nc True) ⟺ (validator no-raise).

        Guards the display⟺enforcement bi-conditional so a predicate divergence can
        never structurally reappear (both sides call the single SSoT _count_open_ncs).
        """
        for status in _NC_STATES:
            with self.subTest(resolution_status=status):
                self._reset_ncs()
                self._insert_nc(status)
                card_passes = self._card_g05_nc()
                validator_passes = not self._validator_raises()
                self.assertEqual(
                    card_passes, validator_passes,
                    f"Divergence at resolution_status={status!r}: "
                    f"card g05_nc={card_passes} but validator_passes={validator_passes}",
                )
                # Only 'Open' should block; the other four pass.
                self.assertEqual(card_passes, status != "Open")


class TestCountOpenNcsSSoT(unittest.TestCase):
    """AC4 root-cause: single predicate counts ONLY resolution_status='Open'."""

    def setUp(self):
        frappe.set_user("Administrator")
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

    def _insert_nc(self, status: str):
        frappe.get_doc({
            "doctype": "Asset QA Non Conformance",
            "ref_commissioning": "_TEST-COMM-G05",
            "nc_type": "Technical",
            "resolution_status": status,
            "description": "G05 SSoT fixture NC",
        }).insert(ignore_permissions=True)
        frappe.db.commit()

    def test_counts_only_open(self):
        self._insert_nc("Open")
        self._insert_nc("Resolved")
        self._insert_nc("Under Review")
        self._insert_nc("Closed")
        self._insert_nc("Transferred")
        # Exactly one 'Open' → the SSoT must ignore the other four non-Open states.
        self.assertEqual(_count_open_ncs("_TEST-COMM-G05"), 1)

    def test_zero_when_no_open(self):
        self._insert_nc("Resolved")
        self._insert_nc("Closed")
        self.assertEqual(_count_open_ncs("_TEST-COMM-G05"), 0)


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

    def test_radiation_class_is_gated_by_g04(self):
        """AC-CR-85: phiếu `risk_class='Radiation'` VẪN bị cổng G04 gác.

        TC này TRƯỚC ĐÂY tên `test_radiation_class_sets_flag` và assert chính
        **side-effect đã bị gỡ** (`doc.is_radiation_device = 1` trong
        `check_auto_clinical_hold`). Ý ĐỊNH nghiệp vụ giữ nguyên — "phiếu phân loại
        Radiation phải bị cổng giấy phép bức xạ gác" — nhưng phép ĐO đổi sang predicate
        SSoT `gate_g04_applies` (07 §III.4f.3 bẫy 5). Đây là **sửa test theo spec mới**
        (BR-04-17), KHÔNG phải "sửa test cho khớp code".
        """
        doc = _make_doc(risk_class="Radiation", is_radiation_device=0)
        self.assertTrue(check_auto_clinical_hold(doc),
                        "Radiation vẫn thuộc nhóm CẦN Clinical Hold (BR-04-05a)")
        self.assertTrue(gate_g04_applies(doc),
                        "Cổng G04 PHẢI áp dụng cho phiếu risk_class='Radiation' dù Device "
                        "Model chưa gắn cờ — bỏ vế này là suy giảm an toàn thật.")


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


# ─── BR-04-10: Overdue-SLA SoT (single drillable predicate) ───────────────────
# Core Doc docs/imm-04/04_Backend_Design.md §0 + §5.1; 02_Analysis_Design.md BR-04-10.
# Date-anchor chốt = reception_date. OVERDUE_DAYS=30 module-constant. Một helper SoT
# `overdue_commissioning_filter()` dùng chung 3 call-site: scheduler / KPI count /
# list drill. INVARIANT đo được: KPI overdue_sla == list({overdue:1}).pagination.total.

class TestOverdueCommissioningFilterSoT(unittest.TestCase):
    """BR-04-10: helper SoT trả filter dùng đúng anchor reception_date."""

    def test_overdue_commissioning_filter_uses_single_anchor(self):
        from assetcore.services import imm04 as svc
        from frappe.utils import add_days, nowdate

        # OVERDUE_DAYS là module-constant (không inline literal 30).
        self.assertEqual(svc.OVERDUE_DAYS, 30)

        f = svc.overdue_commissioning_filter(today="2026-06-03")
        cutoff = add_days("2026-06-03", -svc.OVERDUE_DAYS)

        # Anchor chốt = reception_date (KPI-04-01 §I.5) — KHÔNG dùng expected_installation_date.
        self.assertIn("reception_date", f, "SoT phải dùng anchor reception_date")
        self.assertNotIn(
            "expected_installation_date", f,
            "SoT KHÔNG được tham chiếu field anchor kia (chống divergence)",
        )
        self.assertEqual(f["reception_date"], ("<", cutoff))
        # Non-terminal + chưa cancel.
        self.assertEqual(f["workflow_state"], ("not in", list(svc._TERMINAL_STATES)))
        self.assertEqual(f["docstatus"], ("!=", 2))

        # today=None → dùng nowdate() (cùng cutoff trong cùng request).
        f_now = svc.overdue_commissioning_filter()
        self.assertEqual(f_now["reception_date"], ("<", add_days(nowdate(), -svc.OVERDUE_DAYS)))


class TestOverdueSlaLiveInvariant(unittest.TestCase):
    """BR-04-10 INVARIANT (data-live): KPI overdue_sla == drill rows; terminal/
    trong-hạn KHÔNG tính; scheduler alert đúng tập = KPI."""

    @classmethod
    def setUpClass(cls):
        from assetcore.services import imm04 as svc
        from frappe.utils import add_days, nowdate

        frappe.set_user("Administrator")
        cls.svc = svc
        old = add_days(nowdate(), -svc.OVERDUE_DAYS - 5)   # quá hạn theo anchor
        recent = add_days(nowdate(), -1)                   # trong hạn
        cls.names: list[str] = []

        def _mk(state, reception):
            # Insert ở Draft để né Gate G01 (mandatory docs) — sau đó db_set state
            # đích + reception_date đúng giá trị test (né cả before_insert override).
            d = frappe.get_doc({
                "doctype": "Asset Commissioning",
                "workflow_state": "Draft",
            }).insert(ignore_permissions=True, ignore_mandatory=True, ignore_links=True)
            d.db_set("workflow_state", state, update_modified=False)
            d.db_set("reception_date", reception, update_modified=False)
            cls.names.append(d.name)
            return d.name

        # 1 quá hạn + non-terminal  → TÍNH
        cls.overdue_valid = _mk("To Be Installed", old)
        # 1 quá hạn nhưng terminal (Clinical Release) → KHÔNG tính
        cls.overdue_terminal = _mk("Clinical Release", old)
        # 1 quá hạn nhưng terminal (Return To Vendor) → KHÔNG tính
        cls.overdue_terminal2 = _mk("Return To Vendor", old)
        # 1 trong hạn + non-terminal → KHÔNG tính
        cls.in_window = _mk("Installing", recent)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for n in cls.names:
            try:
                frappe.delete_doc("Asset Commissioning", n, force=True, ignore_permissions=True)
            except Exception:
                pass
        frappe.db.commit()

    def _overdue_set(self):
        """Tập name phiếu quá hạn-hợp-lệ trong fixture (đúng SoT)."""
        rows = frappe.get_all(
            "Asset Commissioning",
            filters=self.svc.overdue_commissioning_filter(),
            fields=["name"],
        )
        return {r["name"] for r in rows} & set(self.names)

    def test_dashboard_overdue_sla_equals_list_overdue_rows(self):
        from assetcore.services import imm04 as svc
        # KPI count == drill total. Đo trên DELTA của fixture (data-live có thể có
        # phiếu khác) → so KPI/drill cùng nhau và xác nhận fixture-set khớp.
        stats = svc.get_dashboard_stats()
        kpi = stats["kpis"]["overdue_sla"]
        drill = svc.list_commissioning({"overdue": 1}, page=1, page_size=100)
        self.assertEqual(
            kpi, drill["pagination"]["total"],
            "INVARIANT vi phạm: card count != drill rows (KPI/list lệch SoT)",
        )
        # Trong tập fixture: chỉ overdue_valid hợp lệ.
        drill_names = {r["name"] for r in drill["items"]} & set(self.names)
        self.assertEqual(drill_names, {self.overdue_valid})
        self.assertNotIn(self.overdue_terminal, drill_names)
        self.assertNotIn(self.overdue_terminal2, drill_names)
        self.assertNotIn(self.in_window, drill_names)

    def test_scheduler_alert_matches_kpi_set(self):
        """check_commissioning_overdue gửi alert đúng tập = overdue_commissioning_filter()."""
        from unittest.mock import patch
        from assetcore.services import imm04 as svc

        sent_to: list[str] = []

        def _fake_sendmail(recipients=None, **kw):
            sent_to.append(recipients)

        # Ép có recipient để sendmail được gọi (role Workshop Head).
        with patch.object(frappe, "sendmail", side_effect=_fake_sendmail), \
             patch("frappe.db.get_all", wraps=frappe.db.get_all):
            with patch("assetcore.services.imm04._send_overdue_alert") as m_alert:
                svc.check_commissioning_overdue()
                alerted = {c.args[0]["name"] for c in m_alert.call_args_list} & set(self.names)

        # Tập alert == tập SoT (giao với fixture). Terminal/in-window KHÔNG có.
        self.assertEqual(alerted, {self.overdue_valid})
        self.assertNotIn(self.overdue_terminal, alerted)
        self.assertNotIn(self.in_window, alerted)

    def test_days_open_computed_from_anchor(self):
        """_send_overdue_alert days_open = date_diff(nowdate(), reception_date) — cùng anchor."""
        from unittest.mock import patch
        from assetcore.services import imm04 as svc
        from frappe.utils import date_diff, nowdate

        captured: dict = {}

        def _fake_alert(comm, days_open):
            if comm["name"] == self.overdue_valid:
                captured["days_open"] = days_open
                captured["reception_date"] = comm.get("reception_date")

        with patch("assetcore.services.imm04._send_overdue_alert", side_effect=_fake_alert):
            svc.check_commissioning_overdue()

        self.assertIn("days_open", captured, "phiếu quá hạn hợp lệ phải được alert")
        expected = date_diff(nowdate(), captured["reception_date"])
        self.assertEqual(
            captured["days_open"], expected,
            "days_open phải tính từ reception_date (cùng anchor), không lệch field",
        )

    def test_list_overdue_conjoins_not_clobbers(self):
        """list({overdue:1, workflow_state:'Clinical Hold'}) AND cả 2 ràng buộc —
        KHÔNG clobber workflow_state người dùng (chống bug filters.update())."""
        from assetcore.services import imm04 as svc
        from frappe.utils import add_days, nowdate

        # Thêm 1 phiếu Clinical Hold + quá hạn (hợp lệ cho conjoin) và 1 Clinical Hold
        # trong-hạn (phải bị loại bởi overdue).
        old = add_days(nowdate(), -svc.OVERDUE_DAYS - 5)
        hold_overdue = frappe.get_doc({
            "doctype": "Asset Commissioning", "workflow_state": "Draft",
        }).insert(ignore_permissions=True, ignore_mandatory=True, ignore_links=True)
        hold_overdue.db_set("workflow_state", "Clinical Hold", update_modified=False)
        hold_overdue.db_set("reception_date", old, update_modified=False)
        self.names.append(hold_overdue.name)
        frappe.db.commit()

        try:
            res = svc.list_commissioning(
                {"overdue": 1, "workflow_state": "Clinical Hold"}, page=1, page_size=100,
            )
            names = {r["name"] for r in res["items"]}
            # Chỉ phiếu vừa Clinical Hold VỪA quá hạn.
            self.assertIn(hold_overdue.name, names)
            # overdue_valid là 'To Be Installed' → KHÔNG được lọt (workflow_state giữ nguyên).
            self.assertNotIn(
                self.overdue_valid, names,
                "filters.update() clobber workflow_state — overdue thắng cả state người dùng (BUG)",
            )
            # in_window là Installing → loại; mọi row phải là Clinical Hold.
            for r in res["items"]:
                self.assertEqual(r["workflow_state"], "Clinical Hold")
        finally:
            frappe.delete_doc("Asset Commissioning", hold_overdue.name, force=True, ignore_permissions=True)
            frappe.db.commit()


class TestNoInlineOverdueLiteral(unittest.TestCase):
    """BR-04-10 guard: services/imm04.py KHÔNG còn inline add_days(...,-30) /
    literal 30 cho overdue ngoài OVERDUE_DAYS constant + helper SoT."""

    def test_no_inline_overdue_literal(self):
        import re
        from pathlib import Path
        import assetcore.services.imm04 as svc

        src = Path(svc.__file__).read_text(encoding="utf-8")
        # Bỏ comment lines (chỉ soát CODE — comment mô tả "KHÔNG inline -30" được phép).
        lines = [
            ln for ln in src.splitlines()
            if not ln.lstrip().startswith("#")
        ]

        # 1) Không còn add_days(..., -30) inline (anchor cũ).
        offenders_adddays = [
            (i + 1, ln) for i, ln in enumerate(lines)
            if re.search(r"add_days\([^)]*,\s*-30\b", ln)
        ]
        self.assertEqual(
            offenders_adddays, [],
            f"Inline add_days(...,-30) còn sót (phải dùng OVERDUE_DAYS): {offenders_adddays}",
        )

        # 2) Anchor cũ expected_installation_date KHÔNG xuất hiện trong filter overdue.
        #    (cho phép trong _CREATE_FIELDS / list fields — chỉ cấm trong cặp với
        #    cutoff/overdue). Kiểm: không dòng nào ghép expected_installation_date với '<'.
        offenders_anchor = [
            (i + 1, ln) for i, ln in enumerate(lines)
            if "expected_installation_date" in ln and re.search(r'["\']<["\']', ln)
        ]
        self.assertEqual(
            offenders_anchor, [],
            f"expected_installation_date dùng làm anchor overdue (sai SoT): {offenders_anchor}",
        )

        # 3) Literal 30 cho overdue chỉ được phép ở dòng định nghĩa OVERDUE_DAYS.
        bad_30 = []
        for i, ln in enumerate(lines):
            if "OVERDUE_DAYS" in ln and "=" in ln and ln.strip().startswith("OVERDUE_DAYS"):
                continue
            if re.search(r"overdue_cutoff", ln):
                bad_30.append((i + 1, ln))
        self.assertEqual(
            bad_30, [],
            f"Biến overdue_cutoff cục bộ còn sót (đã chuyển sang helper SoT): {bad_30}",
        )


class TestSearchLinkConfigFieldsExist(unittest.TestCase):
    """search_link / _ALLOWED_SEARCH_DOCTYPES naming-contract guards (BR-11-12).

    Bug gốc: config 'IMM Calibration Schedule' tham chiếu cột 'asset_ref' KHÔNG tồn
    tại trên DocType (field thật = 'asset') → frappe.db.get_all raise OperationalError
    1054 (Unknown column) → /calibration/new full-page crash + leak traceback ra UI.

    INVARIANT chống tái diễn: MỌI doctype trong _ALLOWED_SEARCH_DOCTYPES có
    search_fields ∪ extra_fields ∪ {label_field} đều là column thật (meta.has_field)
    hoặc 'name'. Test quét toàn config → FAIL nếu bất kỳ config nào tham chiếu field
    chết. RED trên config cũ (asset_ref) — GREEN sau fix.
    """

    @staticmethod
    def _field_exists(doctype: str, field: str) -> bool:
        # 'name' luôn hợp lệ (docname column ảo); các field còn lại phải has_field.
        if field == "name":
            return True
        try:
            return bool(frappe.get_meta(doctype).has_field(field))
        except Exception:
            return False

    def test_calibration_schedule_config_has_no_asset_ref(self):
        """TC-CAL-SEARCH-01/02 (bug chính): config IMM Calibration Schedule KHÔNG
        còn 'asset_ref' (cột chết) — mọi field trong config tồn tại trên DocType."""
        from assetcore.services.imm04 import _ALLOWED_SEARCH_DOCTYPES

        dt = "IMM Calibration Schedule"
        if not frappe.db.exists("DocType", dt):
            self.skipTest("DocType IMM Calibration Schedule chưa cài")
        config = _ALLOWED_SEARCH_DOCTYPES[dt]
        referenced = set(config["search_fields"]) | set(config["extra_fields"]) | {config["label_field"]}
        self.assertNotIn(
            "asset_ref", referenced,
            "Config 'IMM Calibration Schedule' vẫn tham chiếu cột chết 'asset_ref' "
            "(field thật là 'asset') → search_link sẽ raise OperationalError 1054.",
        )
        dead = [f for f in referenced if not self._field_exists(dt, f)]
        self.assertEqual(dead, [], f"Field chết trong config '{dt}': {dead}")

    def test_all_search_configs_reference_real_columns(self):
        """TC-CAL-SEARCH-02 (invariant tổng quát — anti-recurrence): loop MỌI doctype
        trong _ALLOWED_SEARCH_DOCTYPES → mọi field ∈ search∪extra∪{label} là column
        thật. Bảo vệ mọi config tương lai khỏi lặp lại bug 'asset_ref'."""
        from assetcore.services.imm04 import _ALLOWED_SEARCH_DOCTYPES

        offenders: list[tuple[str, str]] = []
        for dt, config in _ALLOWED_SEARCH_DOCTYPES.items():
            # optional config có thể trỏ DocType chưa cài (vd module chưa bật) → bỏ qua
            # khi DocType vắng mặt (search_link tự return [] nhánh optional). Nhưng nếu
            # DocType TỒN TẠI thì field PHẢI thật, kể cả config optional.
            if not frappe.db.exists("DocType", dt):
                if config.get("optional"):
                    continue
                offenders.append((dt, "<DocType không tồn tại>"))
                continue
            referenced = set(config["search_fields"]) | set(config["extra_fields"]) | {config["label_field"]}
            for f in referenced:
                if not self._field_exists(dt, f):
                    offenders.append((dt, f))
        self.assertEqual(
            offenders, [],
            f"Config search tham chiếu field/doctype chết (sẽ gây 1054/traceback): {offenders}",
        )


class TestSearchLinkRuntime(unittest.TestCase):
    """search_link runtime: KHÔNG raise SQL/traceback ra caller (defense-in-depth)."""

    def test_calibration_schedule_query_does_not_raise(self):
        """TC-CAL-SEARCH-01 (runtime): search_link('IMM Calibration Schedule', 'X')
        trả list[dict]{value,label,description} KHÔNG raise. Config cũ (asset_ref) ⇒
        OperationalError 1054 (RED); sau fix ⇒ GREEN."""
        from assetcore.services import imm04 as svc

        if not frappe.db.exists("DocType", "IMM Calibration Schedule"):
            self.skipTest("DocType IMM Calibration Schedule chưa cài")
        rows = svc.search_link("IMM Calibration Schedule", query="X")
        self.assertIsInstance(rows, list)
        for r in rows:
            self.assertIn("value", r)
            self.assertIn("label", r)
            self.assertIn("description", r)

    def test_empty_query_returns_list(self):
        """TC-CAL-SEARCH-05 (biên): query='' → trả list (rỗng hoặc full theo limit)
        KHÔNG raise."""
        from assetcore.services import imm04 as svc

        if not frappe.db.exists("DocType", "IMM Calibration Schedule"):
            self.skipTest("DocType IMM Calibration Schedule chưa cài")
        rows = svc.search_link("IMM Calibration Schedule", query="")
        self.assertIsInstance(rows, list)

    def test_dead_field_in_config_does_not_leak_sql(self):
        """TC-CAL-SEARCH-03 (guard defense-in-depth): tạm inject 1 config có field giả
        'zzz_nonexistent' → search_link KHÔNG raise OperationalError (guard lọc field
        chết), trả rows chỉ với cột tồn tại. Chứng minh endpoint không leak 1054."""
        from assetcore.services import imm04 as svc

        if not frappe.db.exists("DocType", "IMM Calibration Schedule"):
            self.skipTest("DocType IMM Calibration Schedule chưa cài")
        registry = svc._ALLOWED_SEARCH_DOCTYPES
        # Tạm thay config 'IMM Calibration Schedule' bằng config có field GIẢ trỏ
        # DocType THẬT → nếu search_link không lọc field chết, frappe.db.get_all sẽ
        # raise OperationalError 1054. Guard phải lọc → trả list không raise.
        saved = dict(registry["IMM Calibration Schedule"])
        try:
            registry["IMM Calibration Schedule"] = {
                "label_field": "name",
                "search_fields": ["name", "zzz_nonexistent"],
                "filters": {},
                "extra_fields": ["zzz_nonexistent"],
                "optional": True,
            }
            rows = svc.search_link("IMM Calibration Schedule", query="")
            self.assertIsInstance(rows, list)
            for r in rows:
                self.assertIn("value", r)
        finally:
            registry["IMM Calibration Schedule"] = saved

    def test_other_doctypes_no_regression(self):
        """TC-CAL-SEARCH-04 (no-regression): AC Asset + IMM Device Model vẫn trả
        shape {value,label,description} đúng — không hồi quy doctype khác."""
        from assetcore.services import imm04 as svc

        for dt in ("AC Asset", "IMM Device Model"):
            if not frappe.db.exists("DocType", dt):
                continue
            rows = svc.search_link(dt, query="")
            self.assertIsInstance(rows, list)
            for r in rows:
                self.assertIn("value", r)
                self.assertIn("label", r)
                self.assertIn("description", r)


# ─── B-3: Dedup generate_qr_label → asset deep-link (vòng 13 / ADR-001 §D6.1) ──
#
# RC dedup: sau vòng này CHỈ còn 1 đường QR quét-được = deep-link asset
# /a/<token> (enumeration-safe). generate_qr_label trả thêm `qr_url` (tái dùng
# imm00.ensure_asset_qr_token + _build_qr_url — 1 helper duy nhất, dedup THẬT),
# BỎ field scan_url desk. internal_tag_qr + scanner-wedge GIỮ NGUYÊN.

class TestGenerateQrLabelDeepLink(unittest.TestCase):
    """ADR-001 §D6.1 — generate_qr_label ủy quyền deep-link asset + bỏ scan_url."""

    @classmethod
    def setUpClass(cls):
        from assetcore.tests._asset_cleanup import purge_asset  # noqa: PLC0415
        cls._purge_asset = staticmethod(purge_asset)
        frappe.set_user("Administrator")
        cls._created_comm: list[str] = []
        cls._created_assets: list[str] = []

        cls._cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "_TEST B3 QR Dedup Category",
        }).insert(ignore_permissions=True)

    @classmethod
    def tearDownClass(cls):
        for name in cls._created_comm:
            try:
                frappe.delete_doc("Asset Commissioning", name, force=True,
                                  ignore_permissions=True)
            except Exception:
                pass
        for name in cls._created_assets:
            try:
                cls._purge_asset(name)
            except Exception:
                pass
        try:
            frappe.delete_doc("AC Asset Category", cls._cat.name, force=True,
                              ignore_permissions=True)
        except Exception:
            pass
        frappe.set_user("Administrator")

    # ── factories ────────────────────────────────────────────────────────────
    def _make_asset(self, with_token: bool = True) -> str:
        # AC Asset Lifecycle workflow blocks direct Draft → Active; bypass via
        # in_install flag (same pattern as test_imm00._insert_asset_bypass_workflow).
        prev = frappe.flags.in_install
        frappe.flags.in_install = "frappe"
        try:
            asset = frappe.get_doc({
                "doctype": "AC Asset",
                "asset_name": "_TEST B3 QR Asset",
                "asset_category": self._cat.name,
                "status": "Active",
                "lifecycle_status": "Active",
            }).insert(ignore_permissions=True)
        finally:
            frappe.flags.in_install = prev
        type(self)._created_assets.append(asset.name)
        if not with_token:
            # Legacy/token-less asset: blank the qr_token that before_insert set.
            frappe.db.set_value("AC Asset", asset.name, "qr_token", None,
                                update_modified=False)
        return asset.name

    def _make_comm(self, *, final_asset: str | None,
                   internal_tag_qr: str = "BV-RAD-2026-00042") -> str:
        doc = frappe.get_doc({
            "doctype": "Asset Commissioning",
            "po_reference": "_TEST-PO-B3",
            "master_item": "_TEST-MODEL-B3",
            "vendor": "_TEST-VENDOR-B3",
            "internal_tag_qr": internal_tag_qr,
            "final_asset": final_asset,
        }).insert(ignore_permissions=True, ignore_mandatory=True,
                  ignore_links=True)
        type(self)._created_comm.append(doc.name)
        return doc.name

    def _count_ale(self, asset_name: str, event_type: str = "qr_generated") -> int:
        return frappe.db.count("Asset Lifecycle Event",
                               {"asset": asset_name, "event_type": event_type})

    # ── tests ─────────────────────────────────────────────────────────────────
    def test_qr_url_present_when_final_asset(self):
        """Phiếu đã release (final_asset có qr_token) → qr_url = .../a/<token>;
        token == AC Asset.qr_token; KHÔNG còn key scan_url."""
        import re
        from assetcore.services import imm04 as svc

        asset = self._make_asset(with_token=True)
        token = frappe.db.get_value("AC Asset", asset, "qr_token")
        self.assertTrue(token)
        comm = self._make_comm(final_asset=asset)

        res = svc.generate_qr_label(comm)
        self.assertIsNotNone(res["qr_url"])
        self.assertRegex(res["qr_url"], r"^https?://.+/a/[A-Za-z0-9_-]+$")
        self.assertTrue(res["qr_url"].endswith(f"/a/{token}"))
        self.assertNotIn("scan_url", res,
                         "scan_url desk-login phải BỎ HẲN khỏi contract nhãn")

    def test_qr_url_enumeration_safe(self):
        """qr_url KHÔNG chứa internal_tag_qr (BV-...) hay name tuần tự; token opaque
        == field qr_token."""
        from assetcore.services import imm04 as svc

        asset = self._make_asset(with_token=True)
        token = frappe.db.get_value("AC Asset", asset, "qr_token")
        comm = self._make_comm(final_asset=asset,
                               internal_tag_qr="BV-ICU-2026-00777")

        res = svc.generate_qr_label(comm)
        self.assertNotIn("BV-ICU-2026-00777", res["qr_url"])
        self.assertNotIn(asset, res["qr_url"])
        self.assertNotIn(comm, res["qr_url"])
        self.assertTrue(res["qr_url"].endswith(f"/a/{token}"))

    def test_qr_url_uses_shared_helper(self):
        """Patch imm00.ensure_asset_qr_token + _build_qr_url → generate_qr_label
        GỌI đúng 2 helper đó (dedup THẬT — không tái hiện token/URL trong imm04)."""
        from unittest import mock
        from assetcore.services import imm04 as svc

        asset = self._make_asset(with_token=True)
        comm = self._make_comm(final_asset=asset)

        with mock.patch("assetcore.services.imm00.ensure_asset_qr_token",
                        return_value="STUBTOKEN") as m_ensure, \
             mock.patch("assetcore.services.imm00._build_qr_url",
                        return_value="https://x.test/a/STUBTOKEN") as m_build:
            res = svc.generate_qr_label(comm)

        m_ensure.assert_called_once_with(asset)
        m_build.assert_called_once_with("STUBTOKEN")
        self.assertEqual(res["qr_url"], "https://x.test/a/STUBTOKEN")

    def test_qr_url_null_when_no_final_asset(self):
        """Phiếu chưa mint asset (final_asset rỗng, có internal_tag_qr) → qr_url
        None, KHÔNG raise, ensure_asset_qr_token KHÔNG gọi; qr_value fallback."""
        from unittest import mock
        from assetcore.services import imm04 as svc

        comm = self._make_comm(final_asset=None,
                               internal_tag_qr="BV-LAB-2026-00009")

        with mock.patch("assetcore.services.imm00.ensure_asset_qr_token") as m_ensure:
            res = svc.generate_qr_label(comm)

        self.assertIsNone(res["qr_url"])
        m_ensure.assert_not_called()
        self.assertEqual(res["qr_value"], "BV-LAB-2026-00009")

    def test_no_double_emit_qr_generated(self):
        """final_asset đã có qr_token (emit ở mint/backfill) → generate_qr_label
        KHÔNG tạo thêm ALE qr_generated (count trước == sau, gọi nhiều lần)."""
        from assetcore.services import imm04 as svc

        asset = self._make_asset(with_token=True)
        comm = self._make_comm(final_asset=asset)

        before = self._count_ale(asset)
        svc.generate_qr_label(comm)
        svc.generate_qr_label(comm)
        self.assertEqual(self._count_ale(asset), before,
                         "ensure idempotent: token đã có → KHÔNG emit lần 2")

    def test_emit_once_when_asset_token_less(self):
        """final_asset tồn tại nhưng qr_token rỗng (legacy) → đúng 1 ALE
        qr_generated lần đầu; gọi lần 2 KHÔNG thêm event (idempotent)."""
        from assetcore.services import imm04 as svc

        asset = self._make_asset(with_token=False)
        self.assertIsNone(frappe.db.get_value("AC Asset", asset, "qr_token"))
        comm = self._make_comm(final_asset=asset)

        before = self._count_ale(asset)
        res = svc.generate_qr_label(comm)
        token = frappe.db.get_value("AC Asset", asset, "qr_token")
        self.assertTrue(token, "token-less asset → ensure phải sinh token")
        self.assertTrue(res["qr_url"].endswith(f"/a/{token}"))
        self.assertEqual(self._count_ale(asset), before + 1,
                         "token đầu tiên → đúng 1 ALE qr_generated")
        svc.generate_qr_label(comm)
        self.assertEqual(self._count_ale(asset), before + 1,
                         "gọi lại → idempotent, KHÔNG thêm event")

    def test_no_label_printed_emitted(self):
        """generate_qr_label (GET preview) KHÔNG tạo ALE label_printed."""
        from assetcore.services import imm04 as svc

        asset = self._make_asset(with_token=True)
        comm = self._make_comm(final_asset=asset)

        before = self._count_ale(asset, event_type="label_printed")
        svc.generate_qr_label(comm)
        self.assertEqual(self._count_ale(asset, event_type="label_printed"),
                         before, "preview ≠ in nhãn — không emit label_printed")

    def test_rbac_unchanged_forbidden(self):
        """User không có read trên Asset Commissioning → ServiceError(FORBIDDEN);
        ensure_asset_qr_token KHÔNG bypass quyền."""
        from unittest import mock
        from assetcore.services import imm04 as svc
        from assetcore.services.shared import ServiceError, ErrorCode

        asset = self._make_asset(with_token=True)
        comm = self._make_comm(final_asset=asset)

        with mock.patch("frappe.has_permission",
                        side_effect=frappe.PermissionError), \
             mock.patch("assetcore.services.imm00.ensure_asset_qr_token") as m_ensure:
            with self.assertRaises(ServiceError) as ctx:
                svc.generate_qr_label(comm)
        self.assertEqual(ctx.exception.code, ErrorCode.FORBIDDEN)
        m_ensure.assert_not_called()

    def test_bad_state_no_internal_tag_qr(self):
        """Phiếu chưa qua Identification (internal_tag_qr rỗng) →
        ServiceError(INVALID_PARAMS) — guard giữ nguyên."""
        from assetcore.services import imm04 as svc
        from assetcore.services.shared import ServiceError, ErrorCode

        comm = self._make_comm(final_asset=None, internal_tag_qr="")
        with self.assertRaises(ServiceError) as ctx:
            svc.generate_qr_label(comm)
        self.assertEqual(ctx.exception.code, ErrorCode.INVALID_PARAMS)

    def test_internal_tag_qr_field_intact(self):
        """Sau dedup: get_barcode_lookup(internal_tag_qr) vẫn resolve đúng phiếu
        (scanner-wedge / tương thích A1 KHÔNG vỡ)."""
        from assetcore.services import imm04 as svc

        asset = self._make_asset(with_token=True)
        tag = "BV-OPD-2026-00321"
        comm = self._make_comm(final_asset=asset, internal_tag_qr=tag)

        looked = svc.get_barcode_lookup(tag)
        self.assertEqual(looked.get("commissioning_id"), comm)
        self.assertEqual(looked["device"]["internal_qr"], tag)

    # (10) B (base-URL): dedup THẬT — generate_qr_label trả qr_url base CÔNG KHAI
    # khi conf set (KHÔNG mock _build_qr_url → chứng minh 1 SSoT helper IMM-00,
    # không copy logic dựng URL); token-less final_asset → qr_url=None như B-3.
    def test_qr_url_public_base_via_shared_helper(self):
        """conf assetcore_qr_base_url set → qr_url=https://htm.bv.vn/a/<token>
        (đi xuyên _build_qr_url thật → dedup base-URL chung với IMM-00)."""
        from assetcore.services import imm04 as svc

        orig = frappe.conf.get("assetcore_qr_base_url")
        try:
            frappe.conf["assetcore_qr_base_url"] = "https://htm.bv.vn"
            asset = self._make_asset(with_token=True)
            token = frappe.db.get_value("AC Asset", asset, "qr_token")
            comm = self._make_comm(final_asset=asset)

            res = svc.generate_qr_label(comm)
            self.assertEqual(res["qr_url"], f"https://htm.bv.vn/a/{token}",
                             "qr_url phải dùng base công khai qua _build_qr_url chung")
        finally:
            if orig is None:
                frappe.conf.pop("assetcore_qr_base_url", None)
            else:
                frappe.conf["assetcore_qr_base_url"] = orig

    def test_qr_url_null_token_less_even_with_public_base(self):
        """final_asset CHƯA mint (None) → qr_url=None bất kể conf base-URL set
        (regression B-3 — không sinh asset-less QR rác)."""
        from assetcore.services import imm04 as svc

        orig = frappe.conf.get("assetcore_qr_base_url")
        try:
            frappe.conf["assetcore_qr_base_url"] = "https://htm.bv.vn"
            comm = self._make_comm(final_asset=None,
                                   internal_tag_qr="BV-LAB-2026-00111")
            res = svc.generate_qr_label(comm)
            self.assertIsNone(res["qr_url"])
        finally:
            if orig is None:
                frappe.conf.pop("assetcore_qr_base_url", None)
            else:
                frappe.conf["assetcore_qr_base_url"] = orig


# ─── CR-WF-04-SURFACE: workflow-surface integrity (INV-04-WF-1..4) ────────────
#
# Đóng lỗ silent-CTA-loss: rename/xoá "IMM-04 Workflow", drift _DT khỏi
# document_type, hoặc rớt "AssetCore Super Admin" khỏi 1 cạnh → _get_workflow_
# transitions() nuốt lỗi (`except DoesNotExistError: return []`) → toàn bộ CTA
# nghiệm thu biến mất CÂM. Guard toàn cục test_workflow_admin_override glob file
# JSON theo `name`, KHÔNG biết hằng-lookup literal của service → rename lọt câm.
# Guard này COUPLE: hằng-lookup service ⇄ workflow live (DB) ⇄ file JSON ⇄ emit.
# TEST-ONLY: oracle độc lập (parse-file JSON + inspect service literal) + assert
# trên workflow LIVE (DB) + emit service LIVE. 0 chạm runtime .py → 0 reload/migrate.
# Core Doc: docs/imm-04/04_Backend_Design.md §3.1 (INV-04-WF-1..4) + ADR-IMM-04-01.

class TestImm04WorkflowSurfaceIntegrity(unittest.TestCase):
    """INV-04-WF-1..4 — khoá workflow-surface chống silent-CTA-loss (test-only)."""

    WF_NAME = "IMM-04 Workflow"
    ADMIN_ROLE = "AssetCore Super Admin"

    @classmethod
    def setUpClass(cls):
        import json
        from pathlib import Path

        frappe.set_user("Administrator")

        # Oracle độc lập: parse TRỰC TIẾP file JSON (KHÔNG qua DB) — bắt drift ở
        # tầng nguồn, không phụ thuộc seed.
        cls._wf_path = frappe.get_app_path(
            "assetcore", "assetcore", "workflow", "imm_04_workflow.json")
        cls._fx_path = frappe.get_app_path("assetcore", "fixtures", "workflow.json")
        cls._wf_json = json.loads(Path(cls._wf_path).read_text(encoding="utf-8"))
        cls._fx_json = json.loads(Path(cls._fx_path).read_text(encoding="utf-8"))

        # distinct (state, action, next_state) -> set(allowed roles)
        cls._edges = {}
        for t in cls._wf_json["transitions"]:
            cls._edges.setdefault(
                (t["state"], t["action"], t["next_state"]), set()
            ).add(t["allowed"])
        # tập next_state reachable từ các cạnh state == 'Draft' (Draft-out).
        cls._draft_out = {
            t["next_state"] for t in cls._wf_json["transitions"]
            if t["state"] == "Draft"
        }

        # 1 user Super Admin (chỉ 'AssetCore Super Admin') + 1 user role-nghèo
        # (chỉ 'Vendor Engineer' — KHÔNG ∈ allowed của bất kỳ cạnh Draft-out).
        cls.super_user = "_test_imm04_wfsurf_super@assetcore.test"
        cls.poor_user = "_test_imm04_wfsurf_poor@assetcore.test"
        cls._ensure_user(cls.super_user, cls.ADMIN_ROLE)
        cls._ensure_user(cls.poor_user, "Vendor Engineer")

        # Phiếu Asset Commissioning ở Draft (oracle live-wiring cho INV-04-WF-3/4).
        doc = frappe.get_doc({
            "doctype": "Asset Commissioning", "workflow_state": "Draft",
        }).insert(ignore_permissions=True, ignore_mandatory=True, ignore_links=True)
        doc.db_set("workflow_state", "Draft", update_modified=False)
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
        for email in (cls.super_user, cls.poor_user):
            try:
                frappe.delete_doc("User", email, force=True, ignore_permissions=True)
            except Exception:
                pass
        frappe.db.commit()

    @staticmethod
    def _ensure_user(email: str, role: str) -> None:
        """Tạo/đảm bảo user có CHÍNH XÁC 1 role (strip mọi role khác để filter
        tất định — chống default-role gây false-permissive)."""
        if not frappe.db.exists("User", email):
            u = frappe.get_doc({
                "doctype": "User", "email": email,
                "first_name": email.split("@")[0], "send_welcome_email": 0,
                "enabled": 1,
            }).insert(ignore_permissions=True)
        else:
            u = frappe.get_doc("User", email)
        u.set("roles", [])
        u.append("roles", {"role": role})
        u.save(ignore_permissions=True)

    def _emit_under(self, user: str) -> list[dict]:
        """Gọi _get_workflow_transitions LIVE trên phiếu Draft dưới session `user`."""
        from assetcore.services.imm04 import _get_workflow_transitions
        frappe.set_user(user)
        try:
            return _get_workflow_transitions(self.comm)
        finally:
            frappe.set_user("Administrator")

    # ── TC-1 (INV-04-WF-1) ────────────────────────────────────────────────────
    def test_imm04_workflow_doc_resolves_and_document_type_matches(self):
        """get_doc('Workflow','IMM-04 Workflow') KHÔNG raise + document_type ==
        services.imm04._DT ('Asset Commissioning'). RED nếu rename workflow (DB)
        hoặc drift _DT — cả hai làm _get_workflow_transitions nuốt (return [])."""
        from assetcore.services import imm04 as svc
        try:
            wf = frappe.get_doc("Workflow", self.WF_NAME)
        except frappe.DoesNotExistError:
            self.fail(
                f"Workflow '{self.WF_NAME}' KHÔNG resolve — rename/xoá ⇒ "
                "_get_workflow_transitions except→return [] ⇒ mất CÂM toàn bộ CTA "
                "nghiệm thu (0 test toàn cục bắt)")
        self.assertEqual(
            wf.document_type, svc._DT,
            f"drift: workflow.document_type ({wf.document_type!r}) != imm04._DT "
            f"({svc._DT!r}) — service đọc _DT để lấy workflow_state của phiếu")
        self.assertEqual(svc._DT, "Asset Commissioning")

    # ── TC-2 (service-string ⇄ fixture) ───────────────────────────────────────
    def test_imm04_service_lookup_name_matches_fixture_workflow_name(self):
        """Hằng-lookup literal trong _get_workflow_transitions ('IMM-04 Workflow')
        == đúng 1 workflow name có trong fixtures/workflow.json (seed live ⇄
        service-code đồng bộ). RED nếu đổi hằng @services/imm04.py:671 sang sai
        (test_workflow_admin_override KHÔNG bắt — nó chỉ glob file, không đọc hằng)."""
        import re
        import inspect
        from assetcore.services import imm04 as svc

        src = inspect.getsource(svc._get_workflow_transitions)
        m = re.search(
            r'get_doc\(\s*["\']Workflow["\']\s*,\s*["\']([^"\']+)["\']', src)
        self.assertIsNotNone(
            m, "Không trích được hằng-lookup Workflow literal từ "
            "_get_workflow_transitions — cấu trúc get_doc('Workflow', <literal>) đổi?")
        service_wf_name = m.group(1)
        self.assertEqual(
            service_wf_name, self.WF_NAME,
            f"Hằng-lookup service ({service_wf_name!r}) đã lệch hợp đồng "
            f"'{self.WF_NAME}' — rename lọt CÂM, CTA nghiệm thu biến mất")

        # Nguồn seed 1: file workflow gốc imm_04_workflow.json → 'name' top-level.
        # (đổi 'name' trong file này, KỂ CẢ chưa migrate, phải trip guard ngay).
        self.assertEqual(
            service_wf_name, self._wf_json.get("name"),
            f"Service lookup {service_wf_name!r} ≠ imm_04_workflow.json name "
            f"{self._wf_json.get('name')!r} — rename file mà giữ hằng service (hoặc "
            "ngược lại) ⇒ get_doc raise ⇒ silent-CTA-loss")
        # Nguồn seed 2: fixtures/workflow.json aggregate (bản seed live fresh-site).
        fixture_names = {w.get("name") for w in self._fx_json}
        self.assertIn(
            service_wf_name, fixture_names,
            f"Service lookup {service_wf_name!r} KHÔNG khớp bất kỳ workflow name nào "
            "trong fixtures/workflow.json (seed live ⇄ service-code lệch)")
        matched = [w for w in self._fx_json if w.get("name") == service_wf_name]
        self.assertEqual(
            len(matched), 1,
            f"Kỳ vọng đúng 1 fixture workflow '{service_wf_name}', thấy {len(matched)}")
        self.assertEqual(matched[0].get("document_type"), svc._DT)

    # ── TC-3 (INV-04-WF-2) ────────────────────────────────────────────────────
    def test_imm04_every_workflow_edge_grants_super_admin(self):
        """MỌI distinct (state, action, next_state) trong imm_04_workflow.json
        (71 row → 15 cạnh) có 'AssetCore Super Admin' ∈ allowed → QTV duyệt được
        mọi cạnh nghiệm thu. RED nếu 1 edit rớt Super Admin khỏi 1 cạnh.

        2026-07-22 (ADR-CORE-01): 45 → 71 row. +26 row do
        ``setup/backfill_workflow_domain_roles`` cấp transition cho
        ``Commissioning Manager``/``Commissioning User`` — hai vai trò CÓ DocPerm
        write/submit trên Asset Commissioning nhưng trước đó vắng mặt ở MỌI
        transition, tức không bấm được nút nào. Số CẠNH distinct GIỮ NGUYÊN 15
        (chỉ thêm vai trò vào cạnh sẵn có, không mở cạnh mới)."""
        self.assertEqual(
            len(self._wf_json["transitions"]), 71,
            "Số transition-row đổi khỏi 71 — cập nhật oracle + doc §3.1 INV-04-WF-2")
        self.assertEqual(
            len(self._edges), 15,
            "Số cạnh distinct đổi khỏi 15 — cập nhật doc §3.1")
        missing = sorted(
            edge for edge, allowed in self._edges.items()
            if self.ADMIN_ROLE not in allowed)
        self.assertEqual(
            missing, [],
            f"Cạnh THIẾU '{self.ADMIN_ROLE}' → QTV KẸT không duyệt được: {missing}")

    # ── TC-4 (INV-04-WF-3 — live-wiring emit⊆file) ────────────────────────────
    def test_imm04_get_workflow_transitions_live_wired_for_draft_as_super_admin(self):
        """Phiếu Draft, set_user Super Admin → _get_workflow_transitions trả list
        KHÁC rỗng + MỌI entry.next_state ∈ Draft-out parse từ file
        ({'Pending Doc Verify'}). Emit service khớp workflow thật (không stale)."""
        self.assertEqual(
            frappe.db.get_value("Asset Commissioning", self.comm, "workflow_state"),
            "Draft", "phiếu oracle không còn ở Draft — sửa setUpClass")
        emitted = self._emit_under(self.super_user)
        self.assertTrue(
            emitted,
            "Super Admin KHÔNG thấy CTA nào ở Draft — silent-CTA-loss (return [] câm)")
        for e in emitted:
            self.assertIn(
                e["next_state"], self._draft_out,
                f"emit next_state {e['next_state']!r} ∉ Draft-out {self._draft_out} "
                "— emit service stale/lệch file JSON")
            self.assertEqual(
                e["allowed_role"], self.ADMIN_ROLE,
                "Super-Admin-only user phải chỉ khớp cạnh do Super Admin cấp")

    # ── TC-5 (INV-04-WF-4 — không false-permissive) ───────────────────────────
    def test_imm04_get_workflow_transitions_role_filtered_no_false_permissive(self):
        """Cùng phiếu Draft, user role-nghèo (Vendor Engineer — KHÔNG ∈ allowed cạnh
        Draft-out) → emit là SUBSET CHẶT (⊆ và thực-sự-nhỏ-hơn, kỳ vọng rỗng) so
        với Super Admin. Chứng minh filter 't.allowed in user_roles' chặn CTA leo
        quyền (không false-permissive)."""
        super_set = {(e["action"], e["next_state"])
                     for e in self._emit_under(self.super_user)}
        poor_set = {(e["action"], e["next_state"])
                    for e in self._emit_under(self.poor_user)}
        self.assertTrue(super_set, "sanity: Super Admin phải có CTA ở Draft")
        self.assertTrue(
            poor_set <= super_set,
            f"FALSE-PERMISSIVE: role-nghèo emit CTA vượt Super Admin: "
            f"{poor_set - super_set}")
        self.assertLess(
            len(poor_set), len(super_set),
            "role-nghèo (Vendor Engineer) phải bị filter chặt hơn Super Admin ở "
            "Draft (kỳ vọng rỗng) — bằng nhau ⇒ filter t.allowed không hoạt động")


# ─── BR-04-04 (silent-completion): chặn vacuous-Pass ở nghiệm thu Initial Inspection ──
# Core Doc: docs/imm-04/04_Backend_Design.md §5.3 + ADR-IMM-04-02 + 02_Analysis_Design.md
# BR-04-04(a..d). submit_baseline_checklist chỉ set overall_inspection_result='Pass'
# KHI tests_recorded > 0 (số row THỰC có test_result). 0 phép đo → ServiceError
# (ErrorCode.VALIDATION / http_status 422), KHÔNG persist Pass, workflow_state giữ
# 'Initial Inspection'. Flow THẬT (07 §III.4b): phiếu vào Initial Inspection với
# baseline_tests rỗng, KTV đo phát sinh tại hiện trường → clause (b) UPSERT-append.

def _first_link(dt: str) -> str | None:
    names = frappe.get_all(dt, limit=1, pluck="name")
    return names[0] if names else None


def _get_or_create(doctype: str, filters: dict, payload: dict):
    """Fixture idempotent: tái dùng bản ghi rò từ lần chạy hỏng trước thay vì 1062.

    Cần cho doctype autoname sinh mã (vd `AC Asset Category` = CAT-####) — `name`
    khác nhau mỗi lần nhưng field nghiệp vụ (`category_name`) là unique-key THẬT.
    """
    existing = frappe.db.get_value(doctype, filters, "name")
    if existing:
        return frappe.get_doc(doctype, existing)
    return frappe.get_doc(payload).insert(ignore_permissions=True)


class TestBaselineVacuousPassGuard(unittest.TestCase):
    """TC-04-BASELINE-01..05 — BR-04-04 guard (a+d) + clause (b)/(c) regression.

    Dùng phiếu Asset Commissioning THẬT ở workflow_state 'Initial Inspection', re-get
    fresh (CommissioningRepo.get) để kiểm persist — KHÔNG stub doc, đúng ADR-IMM-04-02.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.po = _first_link("AC Purchase")
        cls.model = _first_link("IMM Device Model")
        cls.vendor = _first_link("AC Supplier")
        cls._created: list[str] = []

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for n in cls._created:
            try:
                frappe.delete_doc("Asset Commissioning", n, force=True, ignore_permissions=True)
            except Exception:
                pass
        frappe.db.commit()

    def setUp(self):
        if not (self.po and self.model and self.vendor):
            self.skipTest(
                "Thiếu master data (AC Purchase / IMM Device Model / AC Supplier) "
                "để tạo phiếu Asset Commissioning hợp lệ cho save()")
        frappe.set_user("Administrator")

    def _make_comm(self, seeded_rows: list | None = None) -> str:
        """Tạo phiếu THẬT ở Initial Inspection (mandatory-link đủ để service save())."""
        doc = frappe.get_doc({
            "doctype": "Asset Commissioning",
            "po_reference": self.po,
            "master_item": self.model,
            "vendor": self.vendor,
            "risk_class": "B",
            # Bypass Gate G01 hợp lệ (documents_incomplete + note) — phiếu tới mà
            # CO/CQ chậm; test tập trung nghiệm thu baseline, KHÔNG hồ sơ pháp lý.
            "documents_incomplete": 1,
            "documents_incomplete_note": "Hồ sơ CO/CQ bổ sung sau — test baseline verdict",
            "workflow_state": "Draft",
        }).insert(ignore_permissions=True, ignore_mandatory=True)
        if seeded_rows:
            for row in seeded_rows:
                doc.append("baseline_tests", row)
            # Save ở Draft → VR-03 (validate_checklist_completion) skip state Draft,
            # nên seed row thiếu test_result vẫn persist được.
            doc.save(ignore_permissions=True)
        # Chuyển sang Initial Inspection qua db_set (né workflow transition validation).
        doc.db_set("workflow_state", "Initial Inspection", update_modified=False)
        type(self)._created.append(doc.name)
        return doc.name

    # ── TC-04-BASELINE-01 (RED-first): 0 phép đo, baseline rỗng → VALIDATION, KHÔNG Pass ──
    def test_baseline_01_empty_results_blocks_vacuous_pass(self):
        from assetcore.services.imm04 import submit_baseline_checklist
        from assetcore.services.shared import ErrorCode
        from assetcore.repositories.commissioning_repo import CommissioningRepo

        name = self._make_comm()
        with self.assertRaises(ServiceError) as ctx:
            submit_baseline_checklist(name, [])
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION,
                         "0 phép đo phải raise ErrorCode.VALIDATION (BR-04-04)")
        self.assertIn("BR-04-04", ctx.exception.message)
        reloaded = CommissioningRepo.get(name)
        self.assertNotEqual(reloaded.overall_inspection_result, "Pass",
                            "vacuous submit KHÔNG được set overall_inspection_result='Pass'")
        self.assertEqual(reloaded.workflow_state, "Initial Inspection",
                         "phiếu KHÔNG được advance khỏi Initial Inspection")

    # ── TC-04-BASELINE-02: seeded rows nhưng results chỉ measured_val → tests_recorded==0 ──
    def test_baseline_02_seeded_rows_no_test_result_blocks(self):
        from assetcore.services.imm04 import submit_baseline_checklist
        from assetcore.services.shared import ErrorCode
        from assetcore.repositories.commissioning_repo import CommissioningRepo

        name = self._make_comm(seeded_rows=[
            {"parameter": "Dòng rò điện vỏ máy"},
            {"parameter": "Điện trở tiếp đất"},
        ])
        # results khớp parameter nhưng KHÔNG gửi test_result (chỉ measured_val).
        with self.assertRaises(ServiceError) as ctx:
            submit_baseline_checklist(name, [
                {"parameter": "Dòng rò điện vỏ máy", "measured_val": "0.12"},
                {"parameter": "Điện trở tiếp đất", "measured_val": "0.05"},
            ])
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
        reloaded = CommissioningRepo.get(name)
        self.assertNotEqual(reloaded.overall_inspection_result, "Pass")
        self.assertEqual(reloaded.workflow_state, "Initial Inspection")

    # ── TC-04-BASELINE-03: ≥1 row test_result='Pass' → Pass + tests_recorded==1 ──
    def test_baseline_03_one_pass_row_sets_pass(self):
        from assetcore.services.imm04 import submit_baseline_checklist
        from assetcore.repositories.commissioning_repo import CommissioningRepo

        name = self._make_comm()
        res = submit_baseline_checklist(name, [
            {"parameter": "Dòng rò điện vỏ máy", "measured_val": "0.10", "test_result": "Pass"},
        ])
        self.assertEqual(res["overall_result"], "Pass")
        self.assertEqual(res["tests_recorded"], 1,
                         "tests_recorded = số row THỰC ghi test_result, KHÔNG len(results) mù")
        reloaded = CommissioningRepo.get(name)
        self.assertEqual(reloaded.overall_inspection_result, "Pass")

    # ── TC-04-BASELINE-04 (clause b regression): parameter chưa có row → APPEND + persist ──
    def test_baseline_04_upsert_appends_new_parameter(self):
        from assetcore.services.imm04 import submit_baseline_checklist
        from assetcore.repositories.commissioning_repo import CommissioningRepo

        # Seed 1 row (đã có kết quả) để phiếu hợp lệ; gửi result cho parameter MỚI.
        name = self._make_comm(seeded_rows=[
            {"parameter": "Dòng rò điện vỏ máy", "test_result": "Pass", "measured_val": "0.10"},
        ])
        submit_baseline_checklist(name, [
            {"parameter": "Áp suất khí nén", "measured_val": "2.5", "test_result": "Pass"},
        ])
        reloaded = CommissioningRepo.get(name)
        appended = [r for r in reloaded.baseline_tests if r.parameter == "Áp suất khí nén"]
        self.assertEqual(len(appended), 1,
                         "parameter chưa có row phải được APPEND (KHÔNG drop câm)")
        self.assertEqual(appended[0].test_result, "Pass")
        self.assertEqual(str(appended[0].measured_val), "2.5")

    # ── TC-04-BASELINE-05 → SUPERSEDED bởi BR-04-04e (2026-07-24, 07 §III.4b) ──────
    # Vế cũ (BR-04-04c) đòi raise VALIDATION khi có dòng `Fail` ⇒ raise TRƯỚC doc.save()
    # ⇒ 0 dòng persist ⇒ MẤT bằng chứng KHÔNG ĐẠT (WHO HTM §5.1.2 / NĐ98). Nay: verdict
    # DẪN XUẤT — ghi nhận luôn, cổng an toàn chuyển lên ranh giới Clinical Release
    # (BR-04-13, xem tests/test_imm04_baseline_fail_path.py::TC-04-BLFAIL-06/07).
    def test_baseline_05_fail_row_is_recorded_not_rejected(self):
        from assetcore.services.imm04 import submit_baseline_checklist
        from assetcore.repositories.commissioning_repo import CommissioningRepo

        name = self._make_comm()
        res = submit_baseline_checklist(name, [
            {"parameter": "Dòng rò điện vỏ máy", "measured_val": "9.9",
             "test_result": "Fail", "fail_note": "Vượt ngưỡng 0.5mA"},
        ])
        self.assertEqual(res["overall_result"], "Fail")
        self.assertEqual(res["failed_parameters"], ["Dòng rò điện vỏ máy"])
        reloaded = CommissioningRepo.get(name)
        self.assertEqual(reloaded.overall_inspection_result, "Fail",
                         "verdict dẫn xuất 'Fail' — KHÔNG được set 'Pass'")
        row = next(r for r in reloaded.baseline_tests if r.parameter == "Dòng rò điện vỏ máy")
        self.assertEqual(row.test_result, "Fail")
        self.assertTrue((row.fail_note or "").strip(), "bằng chứng KHÔNG ĐẠT phải persist")


# ─── BR-04-12: Gỡ deadlock board_approver trong transition_state ──────────────
# Core Doc: docs/imm-04/04_Backend_Design.md §5.4 + ADR-IMM-04-03.
# Deadlock gốc: Gate G06 đòi board_approver tại lúc save vào Clinical Release,
# nhưng transition_state(name, action) KHÔNG có param approver, còn
# approve_clinical_release lại đòi ĐÃ ở Clinical Release → 417 nút chết cho path
# trực tiếp/mobile. Fix: transition_state(name, action, board_approver="") cấp
# approver 4-mắt ATOMIC ngay trong transition khi (và chỉ khi) next_state ==
# Clinical Release; thiếu approver → ServiceError Decision-B (message_code
# IMM04-GATE-G06-APPROVER), KHÔNG raw 417.

_GATE_G06_CODE = "IMM04-GATE-G06-APPROVER"


class TestTransitionBoardApprover(unittest.TestCase):
    """BR-04-12 (a..e): board_approver atomic trong transition_state.

    Real-DB fixtures (né mock service): phiếu ở Initial Inspection với baseline
    100% Pass, 0 NC Open, documents_incomplete bypass Gate G01. Device model +
    PM Checklist Template cho full-path (submit → PM/Calibration schedule).
    """

    @classmethod
    def setUpClass(cls):
        from assetcore.tests._asset_cleanup import purge_asset  # noqa: PLC0415
        cls._purge_asset = staticmethod(purge_asset)
        frappe.set_user("Administrator")
        cls._comms: list[str] = []
        cls._assets: list[str] = []
        cls._asset_docs: list[str] = []

        # Approver hợp lệ (khác owner=Administrator) — user THẬT, không super-admin.
        cls.approver = "_test_imm04_board@assetcore.test"
        cls.dup_user = "_test_imm04_dup@assetcore.test"
        for email, fn in ((cls.approver, "imm04board"), (cls.dup_user, "imm04dup")):
            if not frappe.db.exists("User", email):
                u = frappe.get_doc({
                    "doctype": "User", "email": email, "first_name": fn,
                    "send_welcome_email": 0, "enabled": 1,
                }).insert(ignore_permissions=True)
            else:
                u = frappe.get_doc("User", email)
            if "Maintenance User" not in {r.role for r in u.get("roles", [])}:
                u.append("roles", {"role": "Maintenance User"})
                u.save(ignore_permissions=True)

        # Device Model yêu cầu PM + Calibration → full-path sinh cả 2 schedule.
        # get-or-create: AC Asset Category autoname=CAT-#### nên `category_name` là
        # unique-key THẬT — fixture rò từ lần chạy hỏng trước sẽ gây 1062 nếu insert mù.
        cls._cat = _get_or_create("AC Asset Category", {"category_name": "_TEST BR0412 Category"}, {
            "doctype": "AC Asset Category",
            "category_name": "_TEST BR0412 Category",
        })
        cls.model = _get_or_create("IMM Device Model", {"model_name": "_TEST BR0412 Ventilator"}, {
            "doctype": "IMM Device Model",
            "model_name": "_TEST BR0412 Ventilator",
            "manufacturer": "_TEST BR0412 Mfr",
            "asset_category": cls._cat.name,
            "medical_device_class": "Class II",
            "is_pm_required": 1,
            "pm_interval_days": 180,
            "is_calibration_required": 1,
            "calibration_interval_days": 365,
            "default_calibration_type": "External",
        })
        cls._template = _get_or_create(
            "PM Checklist Template", {"template_name": "_TEST BR0412 PM Template"}, {
                "doctype": "PM Checklist Template",
                "template_name": "_TEST BR0412 PM Template",
                "asset_category": cls._cat.name,
                "pm_type": "Semi-Annual",
            })
        # Fixture rò từ lần chạy hỏng trước có thể trỏ Nhóm tài sản đã bị xoá (dangling
        # link) → re-point về category hiện hành, nếu không mint AC Asset sẽ 1054/link err.
        for doc_ref, field in ((cls.model, "asset_category"), (cls._template, "asset_category")):
            if doc_ref.get(field) != cls._cat.name:
                doc_ref.db_set(field, cls._cat.name, update_modified=False)
        cls.po = _first_link("AC Purchase")
        cls.vendor = _first_link("AC Supplier")
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for name in cls._comms:
            for dt, flt in (
                ("Asset QA Non Conformance", {"ref_commissioning": name}),
                ("IMM Audit Trail", {"ref_name": name}),
            ):
                try:
                    frappe.db.delete(dt, flt)
                except Exception:
                    pass
            try:
                frappe.db.set_value("Asset Commissioning", name, "docstatus", 0)
                frappe.delete_doc("Asset Commissioning", name, force=True, ignore_permissions=True)
            except Exception:
                pass
        for asset in cls._assets:
            for dt, flt in (
                ("PM Schedule", {"asset_ref": asset}),
                ("IMM Calibration Schedule", {"asset": asset}),
                ("PM Work Order", {"asset_ref": asset}),
            ):
                try:
                    frappe.db.delete(dt, flt)
                except Exception:
                    pass
            try:
                cls._purge_asset(asset)
            except Exception:
                pass
        for name in cls._asset_docs:
            try:
                frappe.delete_doc("Asset Document", name, force=True, ignore_permissions=True)
            except Exception:
                pass
        for ref, dt in (
            (getattr(cls, "_template", None), "PM Checklist Template"),
            (getattr(cls, "model", None), "IMM Device Model"),
            (getattr(cls, "_cat", None), "AC Asset Category"),
            (cls.approver, "User"), (cls.dup_user, "User"),
        ):
            name = ref.name if hasattr(ref, "name") else ref
            if not name:
                continue
            try:
                frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
            except Exception:
                pass
        frappe.db.commit()

    # ── factory ────────────────────────────────────────────────────────────────
    def _seed_comm(self, workflow_state="Initial Inspection", master_item=None, owner=None):
        """Phiếu THẬT ở `workflow_state` (db_set né workflow-validation), baseline
        100% Pass, documents_incomplete=1 bypass Gate G01."""
        # po_reference / master_item / vendor là mandatory: `apply_workflow` →
        # `doc.save()` re-validate mandatory ở mỗi hop ⇒ KHÔNG thể dựa vào
        # `ignore_mandatory` lúc insert (MandatoryError giữa chừng transition).
        payload = {
            "doctype": "Asset Commissioning",
            "workflow_state": "Draft",
            "po_reference": self.po,
            "master_item": self.model.name,
            "vendor": self.vendor,
            "risk_class": "B",
            "is_radiation_device": 0,
            "documents_incomplete": 1,
            "documents_incomplete_note": "Hồ sơ CO/CQ bổ sung trong 7 ngày (fixture nghiệm thu).",
            "baseline_tests": [
                {"parameter": "Dòng rò vỏ máy (chassis leakage)", "measured_val": "0.10",
                 "unit": "mA", "test_result": "Pass"},
                {"parameter": "Điện trở nối đất bảo vệ", "measured_val": "0.05",
                 "unit": "Ohm", "test_result": "Pass"},
            ],
        }
        if master_item:
            payload["master_item"] = master_item
        if not (self.po and self.vendor):
            self.skipTest("Thiếu master data (AC Purchase / AC Supplier) cho phiếu hợp lệ")
        doc = frappe.get_doc(payload).insert(ignore_permissions=True)
        doc.db_set("workflow_state", workflow_state, update_modified=False)
        if owner:
            doc.db_set("owner", owner, update_modified=False)
        frappe.db.commit()
        type(self)._comms.append(doc.name)
        return doc.name

    def _make_active_registration(self, asset: str) -> str:
        """GW-2: Asset Document 'Chứng nhận đăng ký lưu hành' Active để submit qua
        cổng compliance IMM-05 (`_gw2_check_document_compliance`)."""
        d = frappe.get_doc({
            "doctype": "Asset Document",
            "asset_ref": asset,
            "doc_category": "Legal",
            "doc_type_detail": "Chứng nhận đăng ký lưu hành",
            "doc_number": "ĐKLH-TEST-BR0412",
            "version": "1.0",
            # VR-04 + VR-07 (IMM-05): tài liệu Pháp lý BẮT BUỘC có Cơ quan cấp và
            # Ngày hết hạn (chứng nhận đăng ký lưu hành).
            "issuing_authority": "Bộ Y tế",
            "expiry_date": add_days(nowdate(), 365),
            "issued_date": nowdate(),
        }).insert(ignore_permissions=True, ignore_mandatory=True, ignore_links=True)
        d.db_set("workflow_state", "Active", update_modified=False)
        frappe.db.commit()
        type(self)._asset_docs.append(d.name)
        return d.name

    # ── tests ──────────────────────────────────────────────────────────────────
    def test_transition_to_clinical_release_with_board_approver_succeeds(self):
        """BR-04-12d (deadlock GỠ): Initial Inspection + baseline Pass + 0 NC +
        board_approver hợp lệ → Clinical Release THÀNH CÔNG + approver persist.
        Trước fix: ValidationError 'board_approver là bắt buộc' (417)."""
        from assetcore.services import imm04 as svc

        name = self._seed_comm("Initial Inspection")
        res = svc.transition_state(name, "Phê duyệt phát hành", board_approver=self.approver)
        self.assertEqual(res["new_state"], "Clinical Release")
        self.assertEqual(res["board_approver"], self.approver)
        if res.get("final_asset"):
            type(self)._assets.append(res["final_asset"])
        doc = frappe.get_doc("Asset Commissioning", name)
        self.assertEqual(doc.workflow_state, "Clinical Release")
        self.assertEqual(doc.board_approver, self.approver)

    def test_transition_to_clinical_release_without_approver_returns_structured_error(self):
        """BR-04-12b (STRUCTURED, KHÔNG 417): board_approver='' và doc.board_approver=''
        → ServiceError message_code IMM04-GATE-G06-APPROVER + context.missing;
        KHÔNG frappe.ValidationError, state KHÔNG đổi."""
        from assetcore.services import imm04 as svc
        from assetcore.services.shared import ErrorCode

        name = self._seed_comm("Initial Inspection")
        with self.assertRaises(ServiceError) as ctx:
            svc.transition_state(name, "Phê duyệt phát hành", board_approver="")
        e = ctx.exception
        self.assertEqual(e.message_code, _GATE_G06_CODE)
        self.assertEqual(e.code, ErrorCode.VALIDATION)
        self.assertEqual(e.context, {"missing": ["board_approver"]})
        # KHÔNG raw ValidationError (417) — phải là ServiceError nghiệp vụ.
        self.assertNotIsInstance(e, frappe.ValidationError)
        self.assertEqual(
            frappe.db.get_value("Asset Commissioning", name, "workflow_state"),
            "Initial Inspection", "state KHÔNG được đổi khi thiếu approver",
        )

    def test_transition_board_approver_four_eyes_rejected(self):
        """BR-04-12c (NĐ98 SoD): board_approver == owner (không super-admin) →
        ServiceError FORBIDDEN (assert_distinct_signers); state bất biến,
        board_approver KHÔNG ghi."""
        from assetcore.services import imm04 as svc
        from assetcore.services.shared import ErrorCode

        name = self._seed_comm("Initial Inspection", owner=self.dup_user)
        with self.assertRaises(ServiceError) as ctx:
            svc.transition_state(name, "Phê duyệt phát hành", board_approver=self.dup_user)
        self.assertEqual(ctx.exception.code, ErrorCode.FORBIDDEN)
        self.assertEqual(
            frappe.db.get_value("Asset Commissioning", name, "workflow_state"),
            "Initial Inspection",
        )
        self.assertFalse(
            frappe.db.get_value("Asset Commissioning", name, "board_approver"),
            "board_approver KHÔNG được ghi khi 4-eyes reject",
        )

    def test_full_commissioning_path_reaches_submit_and_generates_schedules(self):
        """PATH END-TO-END: transition(board_approver) → Clinical Release →
        submit_commissioning → docstatus==1 + PM schedule (IMM-08) + Calibration
        schedule (IMM-11) sinh ra ⇒ mạch Needs→Operation thông (không nút chết)."""
        from assetcore.services import imm04 as svc

        name = self._seed_comm("Initial Inspection", master_item=self.model.name)
        res = svc.transition_state(name, "Phê duyệt phát hành", board_approver=self.approver)
        self.assertEqual(res["new_state"], "Clinical Release")
        final_asset = res.get("final_asset")
        self.assertTrue(final_asset, "Clinical Release phải auto-mint AC Asset (final_asset)")
        type(self)._assets.append(final_asset)

        # GW-2 compliance: cấp Chứng nhận ĐK lưu hành Active trước submit.
        self._make_active_registration(final_asset)

        # State 'Clinical Release' khai doc_status=1 ⇒ `apply_workflow` ĐÃ submit phiếu
        # và bắn on_submit (mint asset + PM/Calibration schedule). Gọi lại
        # `submit_commissioning` phải là no-op an toàn — KHÔNG double-mint/double-schedule.
        docstatus = frappe.db.get_value("Asset Commissioning", name, "docstatus")
        self.assertEqual(docstatus, 1, "transition vào Clinical Release phải Submit phiếu")
        with self.assertRaises(ServiceError) as ctx:
            svc.submit_commissioning(name)
        self.assertIn("Submit", ctx.exception.message)

        pm = frappe.db.count("PM Schedule", {"asset_ref": final_asset})
        cal = frappe.db.count("IMM Calibration Schedule", {"asset": final_asset})
        self.assertGreaterEqual(pm, 1, "IMM-08 PM schedule phải sinh từ path nghiệm thu")
        self.assertGreaterEqual(cal, 1, "IMM-11 Calibration schedule phải sinh từ path nghiệm thu")

    def test_transition_non_release_action_ignores_board_approver(self):
        """BR-04-12e (backward-compat): action KHÔNG dẫn tới Clinical Release +
        truyền board_approver → param BỎ QUA, transition chạy như cũ, approver
        KHÔNG ghi, 0 side-effect."""
        from assetcore.services import imm04 as svc

        name = self._seed_comm("Initial Inspection")
        res = svc.transition_state(name, "Báo cáo lỗi baseline", board_approver=self.approver)
        self.assertEqual(res["new_state"], "Re Inspection")
        self.assertFalse(
            frappe.db.get_value("Asset Commissioning", name, "board_approver"),
            "board_approver KHÔNG được ghi ở transition non-CR-bound (backward-compat)",
        )
        self.assertFalse(res.get("board_approver") or "")


class TestTransitionBoardApproverOASContract(unittest.TestCase):
    """OAS mirror guard: op `transition_state` (commissioning) KHÔNG có trong
    mobile OAS surface (ADR-IMM-04-03: 0 whitelist mới, KHÔNG đụng mobile OAS).
    Guard chống vô tình thêm operation mới (op-count baseline & test_mobile_oas
    KHÔNG đổi). Nếu BA sau này đưa transition_state vào mobile OAS, test này PHẢI
    cập nhật để assert board_approver optional + error IMM04-GATE-G06-APPROVER."""

    def test_mobile_oas_transition_documents_board_approver(self):
        import yaml
        from pathlib import Path

        oas_path = Path(frappe.get_app_path("assetcore")).parent / "docs" / "mobile" / "openapi" / "assetcore-mobile.openapi.yaml"
        if not oas_path.exists():
            self.skipTest("mobile OAS không tồn tại trên site này")
        spec = yaml.safe_load(oas_path.read_text(encoding="utf-8"))
        paths = spec.get("paths", {})

        transition_path = "/api/method/assetcore.api.imm04.transition_state"
        if transition_path in paths:
            # Nếu op ĐƯỢC đưa vào mobile OAS → PHẢI document board_approver optional
            # + error IMM04-GATE-G06-APPROVER (KHÔNG thành required, KHÔNG whitelist mới).
            op = paths[transition_path]
            body = str(op)
            self.assertIn("board_approver", body,
                          "op transition_state trong OAS phải document field board_approver")
            self.assertIn(_GATE_G06_CODE, body,
                          "op transition_state trong OAS phải document error IMM04-GATE-G06-APPROVER")
        else:
            # Trạng thái hiện tại (Core Doc §5.4 Boundaries): op KHÔNG có trong mobile
            # OAS ⇒ thay đổi board_approver là hợp đồng service/web, op-count GIỮ NGUYÊN.
            self.assertNotIn(transition_path, paths,
                             "0 whitelist mới: transition_state không được thêm vào mobile OAS")


# ═══════════════════════════════════════════════════════════════════════════════
# CR-76 — Thẻ cổng G01–G06 ⟺ enforcement parity (BR-04-15 · 04 §5.6 · 07 §III.4e)
# ═══════════════════════════════════════════════════════════════════════════════
#
# Bất biến chấm điểm (INV-GATE-PARITY): với MỖI fixture, hai phép đo phải ĐỒNG DẤU
#
#     get_gate_status(name).data[gXX] is True   ⟺   enforcement tương ứng KHÔNG chặn
#
# — hai chiều. Test viết dạng BẢNG CHÂN TRỊ (helper `_assert_parity`), KHÔNG hai
# assert rời rạc: mục tiêu là chứng minh TƯƠNG ĐƯƠNG, không phải "hai sự thật độc lập"
# (ADR-IMM-04-06). Thẻ mang ngữ nghĩa **pre-flight / as-if-armed** ⇒ fixture PHẢI đặt
# phiếu ở trạng thái mà cổng thật sự được gác (04 §5.6.1 cột 4), nếu không so sánh
# với một validator đang return sớm = parity vô nghĩa.
#
# Fixture dựng bằng RAW SQL (KHÔNG `doc.insert()/doc.save()`) vì:
#   * `Asset Commissioning.validate` GỌI CHÍNH `validate_gate_g01` ⇒ dựng fixture
#     "thiếu hồ sơ" bằng `save()` là bất khả (enforcement chặn ngay lúc seed);
#   * `insert()` kéo theo mandatory link (po_reference/master_item/vendor) không liên
#     quan tới cổng đang đo — nhiễu, chậm, và dễ rơi rác khi bị ngắt giữa chừng.
_CR76_COMM = "_TEST-COMM-CR76"
_CR76_DT = "Asset Commissioning"
_CR76_DOC_MANDATORY = "CO - Chứng nhận Xuất xứ"
_CR76_DOC_OPTIONAL = "Manual / HDSD"
_CR76_ACTION_RELEASE = "Phê duyệt phát hành"      # Initial Inspection → Clinical Release
_CR76_STATE_G01_ARMED = "To Be Installed"        # G01 gác ở MỌI state ≠ Draft/Pending Doc Verify
_CR76_STATE_INITIAL = "Initial Inspection"
_CR76_STATE_RELEASE = "Clinical Release"
_CR76_LEGACY_KEYS = ("g01_docs", "g02_facility", "g03_baseline",
                     "g04_radiation", "g05_nc", "g06_approver")


class TestGateStatusEnforcementParity(unittest.TestCase):
    """TC-04-GATE-01..14 — thẻ «Điều kiện bàn giao» nói ĐÚNG cổng thật."""

    # ── fixture plumbing ──────────────────────────────────────────────────────
    @staticmethod
    def _purge() -> None:
        frappe.db.delete("Commissioning Document Record", {"parent": _CR76_COMM})
        frappe.db.delete("Commissioning Checklist", {"parent": _CR76_COMM})
        frappe.db.delete("Asset QA Non Conformance", {"ref_commissioning": _CR76_COMM})
        frappe.db.delete(_CR76_DT, {"name": _CR76_COMM})
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        self._purge()

    def tearDown(self):
        frappe.set_user("Administrator")
        self._purge()

    def _seed(self, **fields) -> None:
        """Tạo phiếu stub. `workflow_state` mặc định = trạng thái G01 được gác."""
        frappe.db.sql(
            """
            INSERT INTO `tabAsset Commissioning`
                (name, creation, modified, owner, modified_by, docstatus, idx,
                 workflow_state, documents_incomplete, documents_incomplete_note,
                 facility_checklist_pass, is_radiation_device, qa_license_doc,
                 board_approver)
            VALUES (%(name)s, NOW(), NOW(), 'Administrator', 'Administrator', 0, 0,
                    %(workflow_state)s, %(documents_incomplete)s,
                    %(documents_incomplete_note)s, %(facility_checklist_pass)s,
                    %(is_radiation_device)s, %(qa_license_doc)s, %(board_approver)s)
            """,
            {
                "name": _CR76_COMM,
                "workflow_state": fields.get("workflow_state", _CR76_STATE_G01_ARMED),
                "documents_incomplete": int(fields.get("documents_incomplete", 0)),
                "documents_incomplete_note": fields.get("documents_incomplete_note", ""),
                "facility_checklist_pass": int(fields.get("facility_checklist_pass", 0)),
                "is_radiation_device": int(fields.get("is_radiation_device", 0)),
                "qa_license_doc": fields.get("qa_license_doc", ""),
                "board_approver": fields.get("board_approver", ""),
            },
        )
        frappe.db.commit()

    def _add_doc_row(self, *, is_mandatory: int, status: str, idx: int = 1,
                     doc_type: str = _CR76_DOC_MANDATORY) -> None:
        frappe.db.sql(
            """
            INSERT INTO `tabCommissioning Document Record`
                (name, creation, modified, owner, modified_by, docstatus, idx,
                 parent, parentfield, parenttype, doc_type, is_mandatory, status)
            VALUES (%(name)s, NOW(), NOW(), 'Administrator', 'Administrator', 0, %(idx)s,
                    %(parent)s, 'commissioning_documents', 'Asset Commissioning',
                    %(doc_type)s, %(is_mandatory)s, %(status)s)
            """,
            {
                "name": frappe.generate_hash(length=12),
                "idx": idx, "parent": _CR76_COMM, "doc_type": doc_type,
                "is_mandatory": int(is_mandatory), "status": status,
            },
        )
        frappe.db.commit()

    def _add_baseline_row(self, *, parameter: str, test_result: str, idx: int = 1) -> None:
        frappe.db.sql(
            """
            INSERT INTO `tabCommissioning Checklist`
                (name, creation, modified, owner, modified_by, docstatus, idx,
                 parent, parentfield, parenttype, parameter, test_result)
            VALUES (%(name)s, NOW(), NOW(), 'Administrator', 'Administrator', 0, %(idx)s,
                    %(parent)s, 'baseline_tests', 'Asset Commissioning',
                    %(parameter)s, %(test_result)s)
            """,
            {
                "name": frappe.generate_hash(length=12), "idx": idx,
                "parent": _CR76_COMM, "parameter": parameter, "test_result": test_result,
            },
        )
        frappe.db.commit()

    def _insert_nc(self, status: str) -> None:
        frappe.get_doc({
            "doctype": "Asset QA Non Conformance", "ref_commissioning": _CR76_COMM,
            "nc_type": "Technical", "resolution_status": status,
            "description": "CR-76 parity fixture NC",
        }).insert(ignore_permissions=True)
        frappe.db.commit()

    # ── phép đo 1: THẺ ────────────────────────────────────────────────────────
    def _card(self) -> dict:
        resp = get_gate_status(_CR76_COMM)
        self.assertTrue(resp.get("success"),
                        f"get_gate_status phải trả 200 envelope cho phiếu fixture: {resp}")
        return resp["data"]

    # ── phép đo 2: ENFORCEMENT (nơi thật sự CHẶN — 04 §5.6.1 cột 3) ───────────
    def _g01_enforcement_blocks(self) -> bool:
        doc = frappe.get_doc(_CR76_DT, _CR76_COMM)
        try:
            validate_gate_g01(doc)
            return False
        except frappe.ValidationError:
            return True

    def _g03_enforcement_blocks(self) -> bool:
        """Pre-check BR-04-13 trong `transition_state` — cổng G03 THẬT.

        Fixture G03 LUÔN để `board_approver` rỗng ⇒ nhánh "G03 cho qua" chắc chắn
        dừng ở pre-check G06 kế tiếp (KHÔNG chạm `apply_workflow`/`doc.save`) ⇒ đo
        được ĐÚNG một cổng, 0 side-effect lên workflow_state.
        """
        from assetcore.services import imm04 as _svc
        from assetcore.utils.messages import MSG as _MSG

        try:
            _svc.transition_state(_CR76_COMM, _CR76_ACTION_RELEASE)
        except ServiceError as exc:
            return exc.message_code == _MSG.IMM04_GATE_G03_BASELINE
        self.fail("transition_state KHÔNG raise — fixture G03 phải dừng ở pre-check "
                  "G03 hoặc G06, KHÔNG được đi tiếp vào apply_workflow")

    def _g05_g06_enforcement_blocks(self) -> bool:
        doc = frappe.get_doc(_CR76_DT, _CR76_COMM)
        try:
            validate_gate_g05_g06(doc)
            return False
        except frappe.ValidationError:
            return True

    # ── chấm parity (bảng chân trị — KHÔNG 2 assert rời) ─────────────────────
    def _assert_parity(self, gate_key: str, expect_pass: bool, enforcement, label: str) -> None:
        card = self._card()
        self.assertIn(gate_key, card, f"[{label}] thẻ thiếu khoá `{gate_key}`: {sorted(card)}")
        blocked = enforcement()
        self.assertIs(
            card[gate_key], expect_pass,
            f"[{label}] thẻ `{gate_key}`={card[gate_key]!r}, kỳ vọng {expect_pass!r}.",
        )
        self.assertEqual(
            card[gate_key], not blocked,
            f"[{label}] LỆCH display⟺enforcement (BR-04-15): thẻ `{gate_key}`="
            f"{card[gate_key]!r} nhưng enforcement {'CHẶN' if blocked else 'CHO QUA'}. "
            f"Thẻ PHẢI dùng CHÍNH predicate mà server dùng để chặn.",
        )

    # ── G01 ───────────────────────────────────────────────────────────────────
    def test_tc_gate_01_no_mandatory_docs_passes(self):
        """TC-04-GATE-01 (E1 báo oan): 0 dòng hồ sơ bắt buộc ⇒ thẻ XANH, validator cho qua."""
        self._seed()
        self._assert_parity("g01_docs", True, self._g01_enforcement_blocks, "0 hồ sơ bắt buộc")
        self.assertIs(self._card()["g01_waived"], False,
                      "0 hồ sơ bắt buộc ⇒ KHÔNG phải nhánh giải trình")

    def test_tc_gate_02_waiver_passes_and_flags(self):
        """TC-04-GATE-02 (E2 báo oan): thiếu hồ sơ + giải trình hợp lệ ⇒ XANH + `g01_waived`."""
        self._seed(documents_incomplete=1, documents_incomplete_note="CO/CQ về sau")
        self._add_doc_row(is_mandatory=1, status="Pending")
        self._assert_parity("g01_docs", True, self._g01_enforcement_blocks, "thiếu + giải trình")
        self.assertIs(
            self._card()["g01_waived"], True,
            "`g01_waived` PHẢI True ⇒ UI nói 'Đạt — có giải trình thiếu hồ sơ', "
            "KHÔNG nói 'đã đủ hồ sơ' (nói sai với người duyệt).",
        )

    def test_tc_gate_03_missing_without_waiver_blocks(self):
        """TC-04-GATE-03 (chiều ngược): thiếu hồ sơ, KHÔNG giải trình ⇒ ĐỎ + validator raise."""
        self._seed()
        self._add_doc_row(is_mandatory=1, status="Pending")
        self._assert_parity("g01_docs", False, self._g01_enforcement_blocks, "thiếu, 0 giải trình")
        self.assertIs(self._card()["g01_waived"], False)

    def test_tc_gate_04_optional_doc_not_counted(self):
        """TC-04-GATE-04: hồ sơ TUỲ CHỌN `Pending` KHÔNG được tính vào cổng."""
        self._seed()
        self._add_doc_row(is_mandatory=1, status="Received", idx=1)
        self._add_doc_row(is_mandatory=0, status="Pending", idx=2, doc_type=_CR76_DOC_OPTIONAL)
        self._assert_parity("g01_docs", True, self._g01_enforcement_blocks, "tuỳ chọn Pending")
        self.assertIs(self._card()["g01_waived"], False)

    def test_tc_gate_05_blank_waiver_note_does_not_pass(self):
        """TC-04-GATE-05: `documents_incomplete=1` + note toàn khoảng trắng ⇒ KHÔNG phải giải trình."""
        self._seed(documents_incomplete=1, documents_incomplete_note="   ")
        self._add_doc_row(is_mandatory=1, status="Pending")
        self._assert_parity("g01_docs", False, self._g01_enforcement_blocks, "waiver rỗng")
        self.assertIs(self._card()["g01_waived"], False,
                      "predicate giải trình PHẢI `.strip()` — note trắng = KHÔNG giải trình")

    def test_tc_gate_g01_truth_table(self):
        """Bảng bất biến G01 — 4 fixture, `g01_docs == (validator KHÔNG raise)` từng dòng."""
        cases = (
            ("đủ hồ sơ bắt buộc", [(1, "Received")], {}, True, False),
            ("0 hồ sơ bắt buộc", [], {}, True, False),
            ("thiếu + giải trình", [(1, "Pending")],
             {"documents_incomplete": 1, "documents_incomplete_note": "CO/CQ về sau"}, True, True),
            ("thiếu + 0 giải trình", [(1, "Pending")], {}, False, False),
        )
        for label, rows, parent_fields, expect_pass, expect_waived in cases:
            with self.subTest(fixture=label):
                self._purge()
                self._seed(**parent_fields)
                for idx, (mand, status) in enumerate(rows, start=1):
                    self._add_doc_row(is_mandatory=mand, status=status, idx=idx)
                self._assert_parity("g01_docs", expect_pass, self._g01_enforcement_blocks, label)
                self.assertIs(self._card()["g01_waived"], expect_waived, f"[{label}] g01_waived")

    # ── G03 ───────────────────────────────────────────────────────────────────
    def test_tc_gate_06_empty_baseline_blocks(self):
        """TC-04-GATE-06: baseline RỖNG ⇒ thẻ ĐỎ và pre-check BR-04-13 chặn."""
        self._seed(workflow_state=_CR76_STATE_INITIAL)
        self._assert_parity("g03_baseline", False, self._g03_enforcement_blocks, "baseline rỗng")

    def test_tc_gate_07_all_pass_or_na_passes(self):
        """TC-04-GATE-07: 2 `Pass` + 1 `N/A` ⇒ thẻ XANH và pre-check KHÔNG chặn vì G03."""
        self._seed(workflow_state=_CR76_STATE_INITIAL)
        self._add_baseline_row(parameter="Điện trở nối đất", test_result="Pass", idx=1)
        self._add_baseline_row(parameter="Dòng rò vỏ máy", test_result="Pass", idx=2)
        self._add_baseline_row(parameter="Cảnh báo âm thanh", test_result="N/A", idx=3)
        self._assert_parity("g03_baseline", True, self._g03_enforcement_blocks, "Pass + N/A")

    def test_tc_gate_08_one_fail_blocks(self):
        """TC-04-GATE-08: 1 dòng `Fail` ⇒ thẻ ĐỎ và pre-check chặn."""
        self._seed(workflow_state=_CR76_STATE_INITIAL)
        self._add_baseline_row(parameter="Điện trở nối đất", test_result="Pass", idx=1)
        self._add_baseline_row(parameter="Dòng rò vỏ máy", test_result="Fail", idx=2)
        self._assert_parity("g03_baseline", False, self._g03_enforcement_blocks, "1 Fail")

    def test_tc_gate_09_unmeasured_row_blocks(self):
        """TC-04-GATE-09: dòng CHƯA ĐO (`test_result` rỗng) ⇒ chặn ở CẢ hai phía."""
        self._seed(workflow_state=_CR76_STATE_INITIAL)
        self._add_baseline_row(parameter="Điện trở nối đất", test_result="Pass", idx=1)
        self._add_baseline_row(parameter="Dòng rò vỏ máy", test_result="", idx=2)
        self._assert_parity("g03_baseline", False, self._g03_enforcement_blocks, "1 dòng chưa đo")

    def test_tc_gate_09b_whitespace_pass_still_passes(self):
        """TC-04-GATE-09 (E3): `" Pass"` thừa khoảng trắng — pre-check `.strip()`, thẻ PHẢI theo."""
        self._seed(workflow_state=_CR76_STATE_INITIAL)
        self._add_baseline_row(parameter="Điện trở nối đất", test_result=" Pass", idx=1)
        self._assert_parity("g03_baseline", True, self._g03_enforcement_blocks, "' Pass' có space")

    def test_tc_gate_10_no_duplicated_literal_in_api_tier(self):
        """TC-04-GATE-10 (AC3): literal `("Pass", "N/A")` KHÔNG được tái sinh ở tầng api."""
        import pathlib

        api_src = (pathlib.Path(frappe.get_app_path("assetcore")) / "api" / "imm04.py").read_text(
            encoding="utf-8")
        self.assertNotIn(
            '"Pass", "N/A"', api_src,
            "Tầng api chép lại tập kết quả đạt ⇒ thêm/bớt 1 giá trị ở `_G03_PASSING` "
            "làm thẻ và cổng lệch CÂM. Dùng predicate SSoT của services/imm04.py.",
        )

    # ── G05 ───────────────────────────────────────────────────────────────────
    def test_tc_gate_12_non_open_ncs_do_not_block(self):
        """TC-04-GATE-12: NC `Resolved` + `Under Review` + `Transferred` (0 `Open`) ⇒ XANH."""
        self._seed(workflow_state=_CR76_STATE_RELEASE, board_approver="Administrator")
        for status in ("Resolved", "Under Review", "Transferred"):
            self._insert_nc(status)
        self._assert_parity("g05_nc", True, self._g05_g06_enforcement_blocks, "3 NC non-Open")

    def test_tc_gate_11_open_nc_blocks(self):
        """TC-04-GATE-11: 1 NC `Open` ⇒ ĐỎ ở CẢ hai phía (regression CR-54 §3)."""
        self._seed(workflow_state=_CR76_STATE_RELEASE, board_approver="Administrator")
        self._insert_nc("Open")
        self._assert_parity("g05_nc", False, self._g05_g06_enforcement_blocks, "1 NC Open")

    # ── G06 ───────────────────────────────────────────────────────────────────
    def test_tc_gate_13_missing_approver_blocks(self):
        """TC-04-GATE-13: `board_approver` rỗng ở `Clinical Release` ⇒ ĐỎ + validator raise."""
        self._seed(workflow_state=_CR76_STATE_RELEASE)
        self._assert_parity("g06_approver", False, self._g05_g06_enforcement_blocks, "0 approver")

    def test_tc_gate_14_approver_set_passes(self):
        """TC-04-GATE-14: đã chỉ định `board_approver` ⇒ XANH + validator cho qua."""
        self._seed(workflow_state=_CR76_STATE_RELEASE, board_approver="Administrator")
        self._assert_parity("g06_approver", True, self._g05_g06_enforcement_blocks, "có approver")

    # ── hợp đồng khoá (additive) ─────────────────────────────────────────────
    def test_tc_gate_18_contract_eight_boolean_keys(self):
        """TC-04-GATE-18: ĐÚNG 8 khoá `bool` — 6 khoá cũ NGUYÊN vẹn + `g01_waived` + `g04_applicable`.

        AC-CR-85 cập nhật 7 → 8 (khoá `g04_applicable` LUÔN emit — khuôn `g01_waived`).
        """
        self._seed()
        card = self._card()
        self.assertEqual(
            sorted(card), sorted(_CR76_LEGACY_KEYS + ("g01_waived", "g04_applicable")),
            "Hợp đồng phải ADDITIVE: 6 khoá cũ nguyên vẹn (Hyrum — FE/mobile đã bind), "
            f"chỉ THÊM `g01_waived` (CR-76) + `g04_applicable` (AC-CR-85). Thực tế: {sorted(card)}",
        )
        for key, value in card.items():
            self.assertIsInstance(
                value, bool,
                f"`{key}` PHẢI bool THẬT (KHÔNG int 0/1 — strict-deser Dart/Kotlin nổ): "
                f"{value!r} ({type(value).__name__})",
            )


# ═════════════════════════════════════════════════════════════════════════════
# AC-CR-85 · BR-04-17 — Cổng G04 gác ĐÚNG 1 domain (predicate SSoT `gate_g04_applies`)
# ═════════════════════════════════════════════════════════════════════════════
# Spec: `02 §IV.2` BR-04-17 · `04 §5.7` (ADR-IMM-04-08/09) · `05 §24.6` · `07 §III.4f`.
#
# Bug gốc (verify @source 2026-07-27): `check_auto_clinical_hold` làm HAI việc không liên
# quan nhau — (1) trả về "phiếu có thuộc nhóm nguy cơ cao không" (ĐÚNG, giữ) và (2) GHI ĐÈ
# `doc.is_radiation_device = 1` cho MỌI phiếu `risk_class ∈ {C,D}` kể cả thiết bị KHÔNG hề
# phát bức xạ (SAI, gỡ). Hệ quả: VR-07 đòi «Giấy phép Cục An toàn Bức xạ Hạt nhân» cho máy
# không bức xạ — giấy phép đó KHÔNG THỂ tồn tại ⇒ deadlock, lối thoát duy nhất của người
# dùng là upload giấy tờ SAI vào hồ sơ pháp lý NĐ98. Hai domain pháp lý bị gộp:
#   * Class C/D  → NĐ 98/2021 Điều 28-32 «Chứng nhận đăng ký lưu hành» — gác bởi GW-2;
#   * phát bức xạ → NĐ 142/2020 Điều 25-27 «Giấy phép Cục ATBXHN» (`qa_license_doc`) — VR-07.
#
# Bẫy fixture (07 §III.4f.3 — đọc trước khi sửa test):
#   1. `_autofill_from_device_model` ghi `risk_class` ở `before_insert` (Class I/II/III → A/B/C).
#   2. `fetch_from` chạy TRƯỚC `validate()` (`base_document.py:848-851` trong `_validate_links`)
#      ⇒ mọi assert về `is_radiation_device` phải ĐỌC LẠI TỪ DB, không đọc object bộ nhớ.
#   3. VR-07 chỉ gác ở `{Clinical Release, Pending Release}` — fixture sai state = xanh GIẢ.
#   4. G01/G03 chạy trước trong `validate()` ⇒ phiếu ma trận B phải sạch hồ sơ + có baseline.
_G04_DT = "Asset Commissioning"
_G04_COMM = "_TEST-COMM-G04-CR85"
_G04_STATE_RELEASE = "Clinical Release"
_G04_LICENSE = "/files/_test_cr85_atbxhn_license.pdf"
_G04_VR07_TOKEN = "An toàn Bức xạ"      # chuỗi message VR-07 (giữ NGUYÊN — i18n đã dịch)
# Ma trận A (07 §III.4f.1) — hằng số ĐÓNG BĂNG hành vi TRƯỚC fix của `check_auto_clinical_hold`.
# Viết tường minh 12 ô, KHÔNG tái sinh bằng chính biểu thức đang đo (test rỗng).
# 6 giá trị `risk_class` (5 enum + RỖNG) × 2 cờ — ô `risk_class=''` là nhánh fallback mà ma
# trận 5×2 của acceptance bỏ sót hoàn toàn (xoá nhánh đó vẫn xanh 10/10 nếu chỉ chốt 10 ô).
_G04_HOLD_MATRIX: tuple[tuple[str, int, bool], ...] = (
    ("A", 0, False), ("A", 1, False),
    ("B", 0, False), ("B", 1, False),
    ("C", 0, True), ("C", 1, True),
    ("D", 0, True), ("D", 1, True),
    ("Radiation", 0, True), ("Radiation", 1, True),
    ("", 0, False), ("", 1, True),
)


class TestGateG04Applicability(unittest.TestCase):
    """TC-04-G04-01..13 (`07 §III.4f`) — cổng G04 gác ĐÚNG 1 domain + gỡ deadlock Class C/D.

    Boundaries khoá bằng test: **Always** `check_auto_clinical_hold` bất biến 12/12 ô ·
    `gate_g04_applies` là predicate DUY NHẤT (VR-07 + verdict + thẻ đọc CHUNG) · INV-G04-1
    hai chiều ở mọi ô. **Never** `check_auto_clinical_hold` GHI `is_radiation_device` ·
    VR-07 chặn phiếu Class C/D không bức xạ · bỏ vế `risk_class == 'Radiation'` (mất cổng
    thật cho phiếu do người dùng phân loại).
    """

    # ── fixture plumbing ─────────────────────────────────────────────────────
    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls._real_comms: list[str] = []
        cls.po = _first_link_g04("AC Purchase")
        cls.vendor = _first_link_g04("AC Supplier")
        # Pre-clean idempotent: lần chạy trước bị ngắt (timeout/SIGTERM) SAU commit nhưng
        # TRƯỚC tearDownClass để lại model/category mồ côi. `AC Asset Category` autoname
        # `CAT-####` ⇒ quét theo `category_name`, KHÔNG theo `name`.
        cls._purge_master()
        cls._cat = frappe.get_doc({
            "doctype": "AC Asset Category", "category_name": "_TEST CR85 Category",
        }).insert(ignore_permissions=True)
        cls.model_nonrad = frappe.get_doc({
            "doctype": "IMM Device Model",
            "model_name": "_TEST CR85 NonRad Analyzer",
            "manufacturer": "_TEST CR85 Mfr",
            "asset_category": cls._cat.name,
            "medical_device_class": "Class III",   # → risk_class 'C', KHÔNG bức xạ
            "is_radiation_device": 0,
        }).insert(ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for name in getattr(cls, "_real_comms", []):
            try:
                frappe.db.delete("IMM Audit Trail", {"ref_name": name})
                frappe.db.set_value(_G04_DT, name, "docstatus", 0)
                frappe.delete_doc(_G04_DT, name, force=True, ignore_permissions=True)
            except Exception:
                pass
        cls._purge_master()
        frappe.db.commit()

    @classmethod
    def _purge_master(cls):
        for model in frappe.get_all("IMM Device Model",
                                    filters={"model_name": "_TEST CR85 NonRad Analyzer"},
                                    pluck="name"):
            try:
                frappe.delete_doc("IMM Device Model", model, force=True, ignore_permissions=True)
            except Exception:
                pass
        for cat in frappe.get_all("AC Asset Category",
                                  filters={"category_name": "_TEST CR85 Category"},
                                  pluck="name"):
            try:
                frappe.delete_doc("AC Asset Category", cat, force=True, ignore_permissions=True)
            except Exception:
                pass

    @staticmethod
    def _purge_stub() -> None:
        frappe.db.delete("Commissioning Checklist", {"parent": _G04_COMM})
        frappe.db.delete("Commissioning Document Record", {"parent": _G04_COMM})
        frappe.db.delete(_G04_DT, {"name": _G04_COMM})
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        self._purge_stub()

    def tearDown(self):
        frappe.set_user("Administrator")
        self._purge_stub()

    def _seed_stub(self, *, risk_class: str, is_radiation_device: int,
                   qa_license_doc: str = "",
                   workflow_state: str = _G04_STATE_RELEASE) -> str:
        """Phiếu stub bằng RAW SQL — `insert()` kéo theo mandatory link (po/model/vendor)
        hoàn toàn không liên quan tới cổng đang đo (nhiễu + chậm + dễ rơi rác)."""
        frappe.db.sql(
            """
            INSERT INTO `tabAsset Commissioning`
                (name, creation, modified, owner, modified_by, docstatus, idx,
                 workflow_state, risk_class, is_radiation_device, qa_license_doc,
                 board_approver, documents_incomplete, documents_incomplete_note,
                 facility_checklist_pass)
            VALUES (%(name)s, NOW(), NOW(), 'Administrator', 'Administrator', 0, 0,
                    %(workflow_state)s, %(risk_class)s, %(is_radiation_device)s,
                    %(qa_license_doc)s, 'Administrator', 0, '', 0)
            """,
            {
                "name": _G04_COMM, "workflow_state": workflow_state,
                "risk_class": risk_class,
                "is_radiation_device": int(is_radiation_device),
                "qa_license_doc": qa_license_doc,
            },
        )
        frappe.db.commit()
        return _G04_COMM

    # ── 3 phép đo trên CÙNG một phiếu (07 §III.4f.2) ──────────────────────────
    def _vr07_error(self, name: str) -> str | None:
        """Enforcement THẬT: `AssetCommissioning.validate_radiation_hold()` (VR-07)."""
        doc = frappe.get_doc(_G04_DT, name)
        try:
            doc.validate_radiation_hold()
        except frappe.ValidationError as exc:
            return str(exc)
        return None

    def _measure(self, name: str) -> dict:
        from assetcore.repositories.commissioning_repo import CommissioningRepo

        doc = CommissioningRepo.get(name)
        card = evaluate_gate_status(name)
        return {
            "applies": gate_g04_applies(doc),
            "verdict_fn": gate_g04_ok(doc),
            "card_applicable": card["g04_applicable"],
            "card_verdict": card["g04_radiation"],
            "vr07": self._vr07_error(name),
        }

    def _assert_inv_g04_1(self, m: dict, label: str) -> None:
        """INV-G04-1 (2 chiều) — chấm ở MỌI ô, không chỉ ô "thú vị"."""
        self.assertIs(
            m["card_applicable"], m["applies"],
            f"[{label}] thẻ `g04_applicable` PHẢI == predicate SSoT `gate_g04_applies` "
            f"(thẻ là TẤM GƯƠNG của enforcement, không phải diễn giải thứ hai).",
        )
        self.assertIs(
            m["card_verdict"], m["verdict_fn"],
            f"[{label}] thẻ `g04_radiation` PHẢI == `gate_g04_ok`.",
        )
        if not m["card_applicable"]:
            self.assertIs(
                m["card_verdict"], True,
                f"[{label}] INV-G04-1: `g04_applicable=False` ⇒ `g04_radiation` LUÔN True. "
                f"Tổ hợp {{False, False}} là BẤT KHẢ.",
            )
            self.assertIsNone(
                m["vr07"],
                f"[{label}] INV-G04-1: cổng KHÔNG áp dụng ⇒ VR-07 KHÔNG BAO GIỜ được chặn "
                f"(advertise == enforce). Thực tế: {m['vr07']}",
            )

    # ── Ma trận A — `check_auto_clinical_hold` KHÔNG suy giảm (12 ô) ──────────
    def _assert_hold_cells(self, risk_class: str) -> None:
        cells = [c for c in _G04_HOLD_MATRIX if c[0] == risk_class]
        self.assertEqual(len(cells), 2, "mỗi `risk_class` phải có ĐỦ 2 ô cờ 0/1")
        for _rc, flag, expected in cells:
            doc = _make_doc(risk_class=risk_class, is_radiation_device=flag)
            self.assertIs(
                check_auto_clinical_hold(doc), expected,
                f"A2 SUY GIẢM AN TOÀN: risk_class={risk_class!r} × is_radiation_device={flag} "
                f"⇒ Clinical Hold routing phải GIỮ NGUYÊN {expected!r} như trước fix.",
            )
            # A1: hàm quyết định Clinical Hold KHÔNG được ghi đè cờ bức xạ (side-effect đã gỡ).
            self.assertEqual(
                int(doc.is_radiation_device or 0), int(flag),
                "A1: `check_auto_clinical_hold` KHÔNG được GHI `doc.is_radiation_device` — "
                "field khai read_only + fetch_from master_item ⇒ ghi đè là đảo ngược chính "
                "SSoT của nó, và người dùng KHÔNG có đường sửa lại.",
            )

    def test_tc_04_g04_01_class_a_hold_unchanged(self):
        """TC-04-G04-01: `risk_class='A'` × cờ 0/1 ⇒ `False` (nhánh enum)."""
        self._assert_hold_cells("A")

    def test_tc_04_g04_02_class_b_hold_unchanged(self):
        """TC-04-G04-02: `risk_class='B'` × cờ 0/1 ⇒ `False`."""
        self._assert_hold_cells("B")

    def test_tc_04_g04_03_class_c_hold_unchanged(self):
        """TC-04-G04-03: `risk_class='C'` × cờ 0/1 ⇒ `True` — Clinical Hold GIỮ, chỉ cờ bức xạ bị gỡ."""
        self._assert_hold_cells("C")

    def test_tc_04_g04_04_class_d_hold_unchanged(self):
        """TC-04-G04-04: `risk_class='D'` × cờ 0/1 ⇒ `True`."""
        self._assert_hold_cells("D")

    def test_tc_04_g04_05_class_radiation_hold_unchanged(self):
        """TC-04-G04-05: `risk_class='Radiation'` × cờ 0/1 ⇒ `True`."""
        self._assert_hold_cells("Radiation")

    def test_tc_04_g04_06_empty_risk_class_falls_back_to_flag(self):
        """TC-04-G04-06: `risk_class=''` ⇒ theo cờ (`False`/`True`) — NHÁNH FALLBACK.

        2 ô mà ma trận 5×2 bỏ sót: mọi giá trị enum đều truthy nên `else` không bao giờ
        chạy; xoá nhánh fallback vẫn xanh 10/10 nếu chỉ chốt 10 ô (M7).
        """
        self._assert_hold_cells("")

    # ── Ma trận B — INV-G04-1 hai chiều (10 ô) ────────────────────────────────
    def test_tc_04_g04_07_non_radiation_gate_not_applicable(self):
        """TC-04-G04-07: model KHÔNG bức xạ × `risk_class ∈ {A,B,C,D}`, chưa có giấy phép.

        `applies=False` · `g04_applicable=False` · `g04_radiation=True` · VR-07 KHÔNG chặn.
        Trước fix, ô `C`/`D` cho `g04_radiation=False` + VR-07 CHẶN (deadlock).
        """
        for rc in ("A", "B", "C", "D"):
            with self.subTest(risk_class=rc):
                self._purge_stub()
                name = self._seed_stub(risk_class=rc, is_radiation_device=0)
                m = self._measure(name)
                self.assertIs(m["applies"], False,
                              f"Class {rc} KHÔNG phát bức xạ ⇒ cổng G04 KHÔNG áp dụng "
                              f"(nghĩa vụ NĐ98 của Class C/D do GW-2 gác).")
                self.assertIs(m["card_applicable"], False)
                self.assertIs(m["card_verdict"], True)
                self.assertIsNone(m["vr07"])
                self._assert_inv_g04_1(m, f"non-rad {rc}")

    def test_tc_04_g04_08_non_radiation_with_license_unchanged(self):
        """TC-04-G04-08: như TC-07 nhưng ĐÃ có `qa_license_doc` ⇒ kết quả KHÔNG đổi.

        Giấy phép thừa không biến cổng "không áp dụng" thành "đã đạt".
        """
        for rc in ("A", "B", "C", "D"):
            with self.subTest(risk_class=rc):
                self._purge_stub()
                name = self._seed_stub(risk_class=rc, is_radiation_device=0,
                                       qa_license_doc=_G04_LICENSE)
                m = self._measure(name)
                self.assertIs(m["card_applicable"], False)
                self.assertIs(m["card_verdict"], True)
                self.assertIsNone(m["vr07"])
                self._assert_inv_g04_1(m, f"non-rad+license {rc}")

    def test_tc_04_g04_09_radiation_device_without_license_blocks(self):
        """TC-04-G04-09 (regression an toàn THẬT): thiết bị bức xạ, chưa có giấy phép ⇒ VR-07 CHẶN."""
        name = self._seed_stub(risk_class="Radiation", is_radiation_device=1)
        m = self._measure(name)
        self.assertIs(m["applies"], True)
        self.assertIs(m["card_applicable"], True)
        self.assertIs(m["card_verdict"], False, "chưa có giấy phép ⇒ cổng ĐANG CHẶN")
        self.assertIsNotNone(m["vr07"], "VR-07 PHẢI vẫn chặn thiết bị bức xạ thiếu giấy phép")
        self.assertIn(_G04_VR07_TOKEN, m["vr07"],
                      "chuỗi message VR-07 giữ NGUYÊN (người dùng đã quen, i18n đã dịch)")
        self._assert_inv_g04_1(m, "radiation no-license")

    def test_tc_04_g04_10_radiation_device_with_license_passes(self):
        """TC-04-G04-10: thiết bị bức xạ ĐÃ có giấy phép ⇒ `g04_radiation=True`, không chặn."""
        name = self._seed_stub(risk_class="Radiation", is_radiation_device=1,
                               qa_license_doc=_G04_LICENSE)
        m = self._measure(name)
        self.assertIs(m["card_applicable"], True)
        self.assertIs(m["card_verdict"], True)
        self.assertIsNone(m["vr07"])
        self._assert_inv_g04_1(m, "radiation +license")

    def test_tc_04_g04_11_user_classified_radiation_still_gated(self):
        """TC-04-G04-11 (chống suy giảm an toàn): model chưa gắn cờ NHƯNG người dùng phân
        loại `risk_class='Radiation'` ⇒ cổng VẪN áp dụng và VẪN chặn.

        Đây chính là ô mà bỏ vế `risk_class == 'Radiation'` khỏi predicate sẽ MẤT cổng (M3).
        """
        name = self._seed_stub(risk_class="Radiation", is_radiation_device=0)
        m = self._measure(name)
        self.assertIs(m["applies"], True,
                      "phân loại Radiation là nguồn HỢP LỆ thứ hai của cổng G04")
        self.assertIs(m["card_applicable"], True)
        self.assertIs(m["card_verdict"], False)
        self.assertIsNotNone(m["vr07"])
        self._assert_inv_g04_1(m, "user-classified radiation")

    # ── Ô người dùng THẬT — gỡ deadlock (A6) ──────────────────────────────────
    def test_tc_04_g04_12_class_c_non_radiation_saves_at_clinical_release(self):
        """TC-04-G04-12 (A1 + A6): phiếu THẬT Class C, model không bức xạ, chưa có giấy
        phép, ở `Clinical Release` ⇒ `doc.save()` KHÔNG throw VR-07 và DB đọc lại cờ = 0.

        TRƯỚC fix: throw «…Giấy phép của Cục An toàn Bức xạ Hạt nhân» — giấy phép KHÔNG THỂ
        tồn tại cho máy không phát bức xạ ⇒ lối thoát duy nhất là nộp giấy tờ SAI vào hồ sơ
        pháp lý NĐ98. Phép đo `is_radiation_device` ĐỌC LẠI TỪ DB (bẫy 2: `fetch_from` chạy
        trước `validate()` nên object bộ nhớ không chứng minh được gì).
        """
        if not (self.po and self.vendor):
            self.skipTest("Thiếu master data (AC Purchase / AC Supplier) để tạo phiếu thật")
        doc = frappe.get_doc({
            "doctype": _G04_DT,
            "workflow_state": "Draft",
            "po_reference": self.po,
            "master_item": self.model_nonrad.name,
            "vendor": self.vendor,
            "board_approver": "Administrator",
            "documents_incomplete": 1,
            "documents_incomplete_note": "Hồ sơ CO/CQ bổ sung sau — fixture AC-CR-85.",
            "baseline_tests": [
                {"parameter": "Điện trở nối đất bảo vệ", "measured_val": "0.05",
                 "test_result": "Pass"},
            ],
        }).insert(ignore_permissions=True)
        frappe.db.commit()
        type(self)._real_comms.append(doc.name)
        self.assertEqual(doc.risk_class, "C",
                         "fixture phải là Class C (map từ `medical_device_class='Class III'`)")

        # Đặt state bằng db_set CÓ CHỦ Ý: đối tượng đo là `validate()` ở `Clinical Release`,
        # KHÔNG phải tính hợp lệ của chuỗi transition (đã có suite riêng). `_doc_before_save`
        # sau reload == state hiện tại ⇒ `validate_workflow` không coi đây là transition
        # (`frappe/model/workflow.py:196`).
        frappe.db.set_value(_G04_DT, doc.name, "workflow_state", _G04_STATE_RELEASE,
                            update_modified=False)
        frappe.db.commit()

        fresh = frappe.get_doc(_G04_DT, doc.name)
        try:
            fresh.save(ignore_permissions=True)
        except frappe.ValidationError as exc:
            self.assertNotIn(
                _G04_VR07_TOKEN, str(exc),
                "DEADLOCK: phiếu Class C KHÔNG phát bức xạ bị VR-07 đòi Giấy phép Cục "
                "ATBXHN — hồ sơ đó KHÔNG THỂ tồn tại; người dùng chỉ còn cách nộp giấy tờ "
                "SAI vào hồ sơ NĐ98.",
            )
            raise
        frappe.db.commit()

        self.assertEqual(
            frappe.db.get_value(_G04_DT, doc.name, "is_radiation_device"), 0,
            "A1: đọc LẠI từ DB phải bằng 0 — `is_radiation_device` khai `read_only` + "
            "`fetch_from: master_item.is_radiation_device` nên SSoT là Device Model.",
        )
        self.assertIs(evaluate_gate_status(doc.name)["g04_applicable"], False)

    # ── Mutation-probe thường trực (A10) ──────────────────────────────────────
    def test_tc_04_g04_13_consumers_wired_to_ssot_predicate(self):
        """TC-04-G04-13: 3 điểm tiêu thụ đọc CHÍNH `gate_g04_applies`, không diễn giải lại.

        Đột biến predicate → `True` phải làm ĐỔI hành vi ở CẢ ba (verdict · thẻ · VR-07)
        trên một phiếu không bức xạ. Nếu bất kỳ điểm nào tự đọc `is_radiation_device` thì
        đột biến không tới được nó ⇒ TC ĐỎ (chống "test rỗng" + chống tái sinh diễn giải
        thứ hai, 04 §5.7.3).
        """
        from unittest.mock import patch

        from assetcore.repositories.commissioning_repo import CommissioningRepo
        from assetcore.services import imm04 as _svc

        name = self._seed_stub(risk_class="C", is_radiation_device=0)
        base = self._measure(name)
        self.assertIs(base["card_applicable"], False, "tiền đề: cổng đang KHÔNG áp dụng")

        with patch.object(_svc, "gate_g04_applies", lambda doc: True):
            doc = CommissioningRepo.get(name)
            self.assertIs(
                _svc.gate_g04_ok(doc), False,
                "P1 `gate_g04_ok` KHÔNG gọi predicate SSoT — verdict đang có diễn giải riêng.",
            )
            self.assertIs(
                _svc.evaluate_gate_status(name)["g04_applicable"], True,
                "P2 thẻ KHÔNG tính bằng predicate SSoT — thẻ là bản diễn giải thứ hai.",
            )
            self.assertIsNotNone(
                self._vr07_error(name),
                "P3 VR-07 KHÔNG đọc predicate SSoT — advertise và enforce sẽ trôi khỏi nhau.",
            )


def _first_link_g04(dt: str) -> str | None:
    names = frappe.get_all(dt, limit=1, pluck="name")
    return names[0] if names else None


if __name__ == "__main__":
    unittest.main()
