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
    enroll_participants,
    remove_participant,
    signoff_competency,
    get_program_score_bounds,
    validate_passing_score_range,
    validate_score_bounds_config,
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


# ─── Slide 21: score bounds config + helper ──────────────────────────────────

class TestScoreBoundsConfig(unittest.TestCase):
    """Slide 21: max_score must be > min_score."""

    def test_valid_bounds_pass(self):
        validate_score_bounds_config(frappe._dict(min_score=0, max_score=100))

    def test_max_equals_min_raises(self):
        with self.assertRaises(frappe.ValidationError):
            validate_score_bounds_config(frappe._dict(min_score=50, max_score=50))

    def test_max_below_min_raises(self):
        with self.assertRaises(frappe.ValidationError):
            validate_score_bounds_config(frappe._dict(min_score=80, max_score=20))

    def test_defaults_when_unset(self):
        # missing attrs → min 0 / max 100 → valid
        validate_score_bounds_config(frappe._dict())

    def test_get_bounds_returns_tuple(self):
        mn, mx = get_program_score_bounds(frappe._dict(min_score=10, max_score=90))
        self.assertEqual((mn, mx), (10.0, 90.0))

    def test_get_bounds_invalid_raises(self):
        with self.assertRaises(frappe.ValidationError):
            get_program_score_bounds(frappe._dict(min_score=90, max_score=10))


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


# ─── Slide 20: IMM Trainer ───────────────────────────────────────────────────

class TestIMMTrainer(unittest.TestCase):
    """Slide 20: create IMM Trainer + assign to a training session."""

    def test_create_trainer_and_assign_to_session(self):
        trainer = frappe.get_doc({
            "doctype": "IMM Trainer",
            "trainer_name": "_Test Trainer Slide20",
            "organization": "_Test Org",
            "is_internal": 1,
        })
        trainer.insert(ignore_permissions=True)
        self.assertTrue(trainer.name.startswith("TRN-"))

        prog = _make_program()
        sess = frappe.get_doc({
            "doctype": "IMM Training Session",
            "training_program": prog,
            "session_date": nowdate(),
            "session_type": "Onsite",
            "duration_planned_hours": 4,
            "evaluation_method": "Cả hai",
            "trainer_ref": trainer.name,
        })
        sess.flags.ignore_links = True
        sess.insert(ignore_permissions=True)
        self.assertEqual(sess.trainer_ref, trainer.name)

        frappe.delete_doc("IMM Training Session", sess.name, force=True, ignore_permissions=True)
        frappe.delete_doc("IMM Training Program", prog, force=True, ignore_permissions=True)
        frappe.delete_doc("IMM Trainer", trainer.name, force=True, ignore_permissions=True)
        frappe.db.commit()


# ─── Slide 21: participant score range enforcement ───────────────────────────

class TestParticipantScoreRange(unittest.TestCase):
    """Slide 21: theory/practical score outside [min,max] → reject on session save."""

    def _program(self, *, min_score, max_score) -> str:
        doc = frappe.get_doc({
            "doctype": "IMM Training Program",
            "program_code": f"_TEST-SC-{frappe.generate_hash(length=6)}",
            "program_name": "_Test Score Program",
            "target_device_category": "_Test Category",
            "passing_score_pct": 70,
            "assessment_method": "Both",
            "validity_period_months": 12,
            "min_score": min_score,
            "max_score": max_score,
            "workflow_state": ProgramStatus.ACTIVE,
        })
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_links = True
        doc.insert(ignore_permissions=True)
        return doc.name

    def test_score_above_max_rejected(self):
        prog = self._program(min_score=0, max_score=100)
        sess = frappe.get_doc({
            "doctype": "IMM Training Session",
            "training_program": prog,
            "session_date": nowdate(),
            "session_type": "Onsite",
            "duration_planned_hours": 4,
            "instructor": "Administrator",
            "participants": [{
                "user": "Administrator",
                "theory_score": 150,
                "practical_score": 50,
            }],
        })
        sess.flags.ignore_links = True
        with self.assertRaises(frappe.ValidationError):
            sess.insert(ignore_permissions=True)
        frappe.delete_doc("IMM Training Program", prog, force=True, ignore_permissions=True)
        frappe.db.commit()

    def test_program_max_le_min_rejected(self):
        with self.assertRaises(frappe.ValidationError):
            self._program(min_score=80, max_score=20)
        frappe.db.rollback()


# ─── Slide 19: enroll / remove participants ──────────────────────────────────

class TestEnrollParticipants(unittest.TestCase):
    """Slide 19: BE enroll/remove trainees on a Training Session."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        # RBAC module-based: AssetCore Super Admin + Training Manager
        for r in ("AssetCore Super Admin", "Training Manager"):
            if not frappe.db.exists("Role", r):
                frappe.get_doc({"doctype": "Role", "role_name": r}
                               ).insert(ignore_permissions=True)
        frappe.get_doc("User", "Administrator").add_roles(
            "AssetCore Super Admin", "Training Manager")
        cls.prog = _make_program()

    @classmethod
    def tearDownClass(cls):
        frappe.delete_doc("IMM Training Program", cls.prog,
                          force=True, ignore_permissions=True)
        frappe.db.commit()

    def _session(self) -> str:
        sess = frappe.get_doc({
            "doctype": "IMM Training Session",
            "training_program": self.prog,
            "session_date": nowdate(),
            "session_type": "Onsite",
            "duration_planned_hours": 4,
            "instructor": "Administrator",
        })
        sess.flags.ignore_links = True
        sess.insert(ignore_permissions=True)
        frappe.db.commit()
        return sess.name

    def test_enroll_adds_rows(self):
        name = self._session()
        res = enroll_participants(name, [
            {"user": "Administrator", "role_at_session": "Operator"},
            {"external_name": "Nguyen Van Ngoai"},
        ])
        self.assertEqual(res["added"], 2)
        self.assertEqual(res["participant_count"], 2)
        doc = frappe.get_doc("IMM Training Session", name)
        self.assertEqual(len(doc.participants), 2)
        ext = [p for p in doc.participants if p.role_at_session == "External"]
        self.assertEqual(len(ext), 1)
        self.assertIn("Nguyen Van Ngoai", ext[0].remarks)

    def test_enroll_on_completed_rejected(self):
        name = self._session()
        frappe.db.set_value("IMM Training Session", name,
                            "workflow_state", SessionStatus.COMPLETED)
        frappe.db.commit()
        with self.assertRaises(ServiceError) as ctx:
            enroll_participants(name, [{"user": "Administrator"}])
        self.assertIn("Completed", str(ctx.exception.message))

    def test_remove_participant_works(self):
        name = self._session()
        enroll_participants(name, [{"user": "Administrator"}])
        doc = frappe.get_doc("IMM Training Session", name)
        row = doc.participants[0].name
        res = remove_participant(name, row)
        self.assertTrue(res["removed"])
        self.assertEqual(res["participant_count"], 0)
        doc2 = frappe.get_doc("IMM Training Session", name)
        self.assertEqual(len(doc2.participants), 0)


if __name__ == "__main__":
    unittest.main()
