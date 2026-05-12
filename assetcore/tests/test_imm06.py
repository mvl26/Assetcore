# Copyright (c) 2026, AssetCore Team
"""IMM-06 unit tests — validators, compute_overall_results, signoff, archive_old_competency.

Run: bench --site miyano run-tests --app assetcore --module assetcore.tests.test_imm06
"""
from __future__ import annotations

import unittest

import frappe
from frappe.utils import add_days, add_months, nowdate

from assetcore.services.imm06 import (
    CompetencyStatus,
    ProgramStatus,
    SessionStatus,
    archive_old_competency,
    compute_overall_results,
    signoff_competency,
    validate_passing_score_range,
    validate_validity_range,
)
from assetcore.services.shared import ServiceError


# ─── Fixtures ────────────────────────────────────────────────────────────────

def _make_asset(device_model: str = "") -> str:
    doc = frappe.get_doc({
        "doctype": "AC Asset",
        "asset_name": "_Test Asset IMM06",
    })
    if device_model:
        doc.device_model = device_model
    doc.flags.ignore_mandatory = True
    doc.insert(ignore_permissions=True)
    return doc.name


def _make_program() -> str:
    doc = frappe.get_doc({
        "doctype": "IMM Training Program",
        "program_code": f"_TEST-PROG-{frappe.generate_hash(length=6)}",
        "program_name": "_Test Program IMM06",
        "target_device_category": "_Test Category",
        "passing_score_pct": 70,
        "assessment_method": "Both",
        "validity_period_months": 12,
        "workflow_state": ProgramStatus.ACTIVE,
    })
    doc.flags.ignore_mandatory = True
    doc.flags.ignore_links = True
    doc.insert(ignore_permissions=True)
    return doc.name


_TEST_MODEL = None
_TEST_PROGRAM = None


def _ensure_test_model() -> str:
    global _TEST_MODEL
    if _TEST_MODEL and frappe.db.exists("IMM Device Model", _TEST_MODEL):
        return _TEST_MODEL
    existing = frappe.db.get_value(
        "IMM Device Model",
        {"model_name": "_Test Model IMM06", "manufacturer": "Test Manufacturer"},
        "name",
    )
    if existing:
        _TEST_MODEL = existing
        return _TEST_MODEL
    doc = frappe.get_doc({
        "doctype": "IMM Device Model",
        "model_name": "_Test Model IMM06",
        "manufacturer": "Test Manufacturer",
        "medical_device_class": "Class II",
    })
    doc.flags.ignore_mandatory = True
    doc.flags.ignore_links = True
    doc.insert(ignore_permissions=True)
    _TEST_MODEL = doc.name
    return _TEST_MODEL


def _ensure_test_program() -> str:
    global _TEST_PROGRAM
    if _TEST_PROGRAM and frappe.db.exists("IMM Training Program", _TEST_PROGRAM):
        return _TEST_PROGRAM
    existing = frappe.db.get_value(
        "IMM Training Program",
        {"program_name": "_Test Program IMM06 Shared"},
        "name",
    )
    if existing:
        _TEST_PROGRAM = existing
        return _TEST_PROGRAM
    doc = frappe.get_doc({
        "doctype": "IMM Training Program",
        "program_code": "_TEST-PROG-IMM06-SHARED",
        "program_name": "_Test Program IMM06 Shared",
        "target_device_category": "_Test Category",
        "passing_score_pct": 70,
        "assessment_method": "Both",
        "validity_period_months": 12,
        "workflow_state": ProgramStatus.ACTIVE,
    })
    doc.flags.ignore_mandatory = True
    doc.flags.ignore_links = True
    doc.insert(ignore_permissions=True)
    _TEST_PROGRAM = doc.name
    return _TEST_PROGRAM


def _make_competency(user: str, device_model: str, state: str = CompetencyStatus.PENDING) -> str:
    model_name = _ensure_test_model()
    program_name = _ensure_test_program()
    doc = frappe.get_doc({
        "doctype": "IMM User Competency",
        "user": user,
        "device_model": model_name,
        "training_program": program_name,
        "workflow_state": CompetencyStatus.PENDING,
        "achieved_date": nowdate(),
        "validity_months": 24,
        "competency_level": "Operator",
    })
    doc.flags.ignore_mandatory = True
    doc.flags.ignore_links = True
    doc.insert(ignore_permissions=True)
    if state != CompetencyStatus.PENDING:
        frappe.db.set_value("IMM User Competency", doc.name, "workflow_state", state)
    return doc.name


# ─── validate_passing_score_range ────────────────────────────────────────────

class TestValidatePassingScoreRange(unittest.TestCase):

    def _program_doc(self, score):
        return frappe._dict(passing_score_pct=score)

    def test_score_70_passes(self):
        doc = self._program_doc(70)
        validate_passing_score_range(doc)  # no raise

    def test_score_1_passes(self):
        validate_passing_score_range(self._program_doc(1))

    def test_score_100_passes(self):
        validate_passing_score_range(self._program_doc(100))

    def test_score_0_raises(self):
        with self.assertRaises(frappe.ValidationError):
            validate_passing_score_range(self._program_doc(0))

    def test_score_101_raises(self):
        with self.assertRaises(frappe.ValidationError):
            validate_passing_score_range(self._program_doc(101))

    def test_none_skipped(self):
        validate_passing_score_range(frappe._dict(passing_score_pct=None))


# ─── validate_validity_range ─────────────────────────────────────────────────

class TestValidateValidityRange(unittest.TestCase):

    def _doc(self, months):
        return frappe._dict(validity_period_months=months)

    def test_12_months_passes(self):
        validate_validity_range(self._doc(12))

    def test_1_month_passes(self):
        validate_validity_range(self._doc(1))

    def test_0_months_raises(self):
        with self.assertRaises(frappe.ValidationError):
            validate_validity_range(self._doc(0))

    def test_negative_raises(self):
        with self.assertRaises(frappe.ValidationError):
            validate_validity_range(self._doc(-5))

    def test_none_skipped(self):
        validate_validity_range(frappe._dict(validity_period_months=None))


# ─── compute_overall_results ─────────────────────────────────────────────────

class TestComputeOverallResults(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.prog = _make_program()

    @classmethod
    def tearDownClass(cls):
        frappe.delete_doc("IMM Training Program", cls.prog, force=True, ignore_permissions=True)

    def _session_doc(self, participants):
        doc = frappe._dict(training_program=self.prog)
        doc.participants = [frappe._dict(p) for p in participants]
        return doc

    def test_pass_with_both_above_threshold(self):
        doc = self._session_doc([{
            "theory_score": 80, "practical_score": 75, "attendance_pct": 90,
            "overall_result": None, "retake_required": None,
        }])
        compute_overall_results(doc)
        self.assertEqual(doc.participants[0].overall_result, "Pass")
        self.assertEqual(doc.participants[0].retake_required, 0)

    def test_fail_when_average_below_threshold(self):
        doc = self._session_doc([{
            "theory_score": 50, "practical_score": 55, "attendance_pct": 90,
            "overall_result": None, "retake_required": None,
        }])
        compute_overall_results(doc)
        self.assertEqual(doc.participants[0].overall_result, "Fail")
        self.assertEqual(doc.participants[0].retake_required, 1)

    def test_fail_when_attendance_below_80(self):
        doc = self._session_doc([{
            "theory_score": 95, "practical_score": 95, "attendance_pct": 79,
            "overall_result": None, "retake_required": None,
        }])
        compute_overall_results(doc)
        self.assertEqual(doc.participants[0].overall_result, "Fail")

    def test_no_program_is_noop(self):
        doc = frappe._dict(training_program=None, participants=[
            frappe._dict(theory_score=80, practical_score=80, attendance_pct=90,
                         overall_result=None, retake_required=None)
        ])
        compute_overall_results(doc)  # no crash

    def test_multiple_participants(self):
        doc = self._session_doc([
            {"theory_score": 90, "practical_score": 90, "attendance_pct": 100,
             "overall_result": None, "retake_required": None},
            {"theory_score": 40, "practical_score": 40, "attendance_pct": 100,
             "overall_result": None, "retake_required": None},
        ])
        compute_overall_results(doc)
        self.assertEqual(doc.participants[0].overall_result, "Pass")
        self.assertEqual(doc.participants[1].overall_result, "Fail")


# ─── signoff_competency ───────────────────────────────────────────────────────

class TestSignoffCompetency(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")

    def test_signoff_pending_succeeds(self):
        comp = _make_competency("Administrator", "", state=CompetencyStatus.PENDING)
        result = signoff_competency(comp, "Administrator")
        self.assertEqual(result["workflow_state"], CompetencyStatus.ACTIVE)
        self.assertIsNotNone(result.get("expiry_date"))
        frappe.db.delete("IMM User Competency", {"name": comp})

    def test_signoff_already_active_raises(self):
        comp = _make_competency("Administrator", "", state=CompetencyStatus.ACTIVE)
        with self.assertRaises(ServiceError) as ctx:
            signoff_competency(comp, "Administrator")
        self.assertEqual(ctx.exception.code, "BAD_STATE")
        frappe.db.delete("IMM User Competency", {"name": comp})

    def test_signoff_not_found_raises(self):
        with self.assertRaises(ServiceError) as ctx:
            signoff_competency("FAKE-COMP-NAME", "Administrator")
        self.assertEqual(ctx.exception.code, "NOT_FOUND")


# ─── archive_old_competency ───────────────────────────────────────────────────

class TestArchiveOldCompetency(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        model = _ensure_test_model()
        frappe.db.delete("IMM User Competency", {
            "user": "Administrator",
            "device_model": model,
        })

    def test_old_active_gets_suspended(self):
        model = _ensure_test_model()
        old = _make_competency("Administrator", "", state=CompetencyStatus.ACTIVE)
        new = _make_competency("Administrator", "", state=CompetencyStatus.ACTIVE)
        count = archive_old_competency("Administrator", model, exclude=new)
        self.assertGreaterEqual(count, 1)
        old_state = frappe.db.get_value("IMM User Competency", old, "workflow_state")
        self.assertEqual(old_state, CompetencyStatus.SUSPENDED)
        frappe.db.delete("IMM User Competency", {"name": old})
        frappe.db.delete("IMM User Competency", {"name": new})

    def test_no_old_active_returns_zero(self):
        model = _ensure_test_model()
        comp = _make_competency("Administrator", "", state=CompetencyStatus.PENDING)
        count = archive_old_competency("Administrator", model, exclude=comp)
        self.assertEqual(count, 0)
        frappe.db.delete("IMM User Competency", {"name": comp})


if __name__ == "__main__":
    unittest.main()
