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
        self.__dict__.update(kwargs)
        self.lifecycle_events = []
        self.name = "_TEST-FAKE"

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


if __name__ == "__main__":
    unittest.main()
