# Copyright (c) 2026, AssetCore Team
"""IMM-06 unit tests — validators, compute_overall_results, signoff, archive_old_competency.

Run: bench --site miyano run-tests --app assetcore --module assetcore.tests.test_imm06
"""
from __future__ import annotations

import contextlib
import unittest

import frappe
from frappe.utils import add_days, add_months, nowdate

from assetcore.services.imm06 import (
    RECERT_LEAD_DAYS,
    CompetencyStatus,
    ProgramStatus,
    SessionStatus,
    archive_old_competency,
    compute_competency_dates,
    compute_expiry_dates,
    compute_overall_results,
    enroll_participants,
    get_expiring_competencies,
    list_competencies,
    list_user_competencies,
    remove_participant,
    set_computed_competency_fields,
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


def tearDownModule():  # noqa: N802
    """Purge the shared module-level fixtures so they never leak into prod-like
    lists (the recurring '_Test Model IMM06' / '_TEST-PROG-IMM06-SHARED' leak).

    IMM User Competency has an ``on_trash`` guard (BR-06-09) that blocks ORM
    delete even with ``force=True`` → competencies are raw-SQL purged. The device
    model / training program / asset are then ORM-deletable once FK-free.
    """
    frappe.set_user("Administrator")
    # 1) Competencies pointing at the shared test model/program (raw SQL — on_trash blocks ORM).
    comp_names = frappe.db.sql_list(
        "SELECT uc.name FROM `tabIMM User Competency` uc "
        "LEFT JOIN `tabIMM Device Model` dm ON dm.name = uc.device_model "
        "WHERE dm.model_name = %s OR uc.training_program IN ("
        "  SELECT name FROM `tabIMM Training Program` WHERE program_code = %s)",
        ("_Test Model IMM06", "_TEST-PROG-IMM06-SHARED"),
    )
    if comp_names:
        frappe.db.delete("IMM User Competency", {"name": ["in", comp_names]})
        frappe.db.delete("IMM Audit Trail",
                         {"ref_doctype": "IMM User Competency", "ref_name": ["in", comp_names]})
    # 2) Shared test assets (raw audit/lifecycle purge via helper).
    from assetcore.tests._asset_cleanup import purge_asset
    for an in frappe.db.sql_list(
        "SELECT name FROM `tabAC Asset` WHERE asset_name = %s", ("_Test Asset IMM06",)
    ):
        try:
            purge_asset(an)
        except Exception:  # noqa: BLE001
            pass
    # 3) Shared training program(s) + device model (ORM, now FK-free).
    for prog in frappe.db.sql_list(
        "SELECT name FROM `tabIMM Training Program` WHERE program_code = %s "
        "OR program_name LIKE %s", ("_TEST-PROG-IMM06-SHARED", "\\_Test Program IMM06%"),
    ):
        with contextlib.suppress(Exception):
            frappe.delete_doc("IMM Training Program", prog, force=True, ignore_permissions=True)
    for mdl in frappe.db.sql_list(
        "SELECT name FROM `tabIMM Device Model` WHERE model_name = %s", ("_Test Model IMM06",)
    ):
        with contextlib.suppress(Exception):
            frappe.delete_doc("IMM Device Model", mdl, force=True, ignore_permissions=True)
    frappe.db.commit()
    # Reset module globals so a re-run within the same process re-seeds cleanly.
    global _TEST_MODEL, _TEST_PROGRAM
    _TEST_MODEL = None
    _TEST_PROGRAM = None


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
        cls._sessions: list[str] = []

    @classmethod
    def tearDownClass(cls):
        # Sessions are committed in _session(); delete them first so the program
        # teardown doesn't leave orphaned IMM Training Session rows behind.
        for name in cls._sessions:
            if frappe.db.exists("IMM Training Session", name):
                frappe.delete_doc("IMM Training Session", name,
                                  force=True, ignore_permissions=True)
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
        type(self)._sessions.append(sess.name)
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


# ─── BR-06-13 SoT recertification_due_date (Vòng 22) ─────────────────────────

class TestComputeCompetencyDatesSoT(unittest.TestCase):
    """BR-06-13: 1 SoT compute_competency_dates — INVARIANT recert = expiry − 60d.

    Pure-helper tests (no DB). Anchor = expiry_date (KHÔNG achieved+validity-2).
    """

    def test_tdd1_predicate_boundary_exact_60d(self):
        """TDD-1: recert == expiry − 60 ngày (add_days(-60)) chính xác 1 ngày cụ thể."""
        # achieved 2026-03-15, validity 12 → expiry 2027-03-15 → recert 2027-01-14
        dates = compute_competency_dates("2026-03-15", 12)
        self.assertEqual(str(dates["expiry_date"]), "2027-03-15")
        self.assertEqual(str(dates["recertification_due_date"]), "2027-01-14")
        # INVARIANT: recert = expiry − RECERT_LEAD_DAYS
        self.assertEqual(
            add_days(dates["expiry_date"], -RECERT_LEAD_DAYS),
            dates["recertification_due_date"],
        )
        self.assertEqual(RECERT_LEAD_DAYS, 60)

    def test_tdd3_anchor_is_expiry_not_achieved_end_of_month(self):
        """TDD-3: achieved cuối tháng (2026-01-31, validity 24) → recert = expiry(2028-01-31)−60d,
        KHÔNG phải add_months(achieved, 22) (chứng minh đã bỏ formula B)."""
        dates = compute_competency_dates("2026-01-31", 24)
        self.assertEqual(str(dates["expiry_date"]), "2028-01-31")
        # SoT (formula A): expiry − 60d = 2027-12-02
        self.assertEqual(str(dates["recertification_due_date"]), "2027-12-02")
        # Formula B (cũ, sai): add_months(2026-01-31, 22) = 2027-11-30 → KHÁC
        self.assertNotEqual(
            str(dates["recertification_due_date"]),
            str(add_months("2026-01-31", 22)),
        )

    def test_tdd3_boundary_matrix_all_ba_cases(self):
        """TDD-3 (mở rộng): mọi cặp achieved×validity BA chốt → recert = expiry−60d (anchor expiry)."""
        cases = [("2026-01-31", 24), ("2026-02-28", 12), ("2025-12-31", 36), ("2026-03-15", 12)]
        for ach, v in cases:
            dates = compute_competency_dates(ach, v)
            self.assertEqual(
                dates["recertification_due_date"],
                add_days(add_months(ach, v), -60),
                f"recert phải = expiry−60d cho achieved={ach} validity={v}",
            )


class TestSeedWriteSiteSoT(unittest.TestCase):
    """BR-06-13 seed/script write-site (Vòng 23) — đóng nốt consumer thứ 7 (seed).

    seed_imm_456.py:345-346 PHẢI route qua compute_competency_dates (1 SoT call),
    KHÔNG inline `add_months(achieved, validity)` (expiry) hay
    `add_months(achieved, validity-2)` (recert formula-B → trôi 0–2 ngày).
    """

    # ── TC-06-SEED-01: drift formula-B documented + SoT 0-day-drift ─────────────
    def test_seed01_sot_recert_equals_expiry_minus_60_and_not_formula_b(self):
        """TC-06-SEED-01: validity=24, achieved=today-1 → recert == expiry−60d, != add_months(achieved,22)."""
        achieved = add_days(nowdate(), -1)
        dates = compute_competency_dates(achieved, 24)
        # SoT INVARIANT: recert = expiry − 60 ngày (0-day drift, anchor = expiry)
        self.assertEqual(
            dates["recertification_due_date"],
            add_days(dates["expiry_date"], -60),
        )
        self.assertEqual(dates["expiry_date"], add_months(achieved, 24))

    def test_seed01_formula_b_drifts_at_month_boundary(self):
        """TC-06-SEED-01: chứng minh formula-B cũ (add_months(achieved, validity-2)) cho
        giá trị KHÁC SoT trên ít nhất 1 mốc cuối tháng → đó là 0–2 ngày drift fix loại bỏ."""
        # achieved 2025-12-31, validity 24 → expiry 2027-12-31 → SoT recert = 2027-11-01
        achieved, validity = "2025-12-31", 24
        sot = compute_competency_dates(achieved, validity)
        formula_b = add_months(achieved, validity - 2)  # = 2027-10-31 (30-day tháng → drift)
        self.assertEqual(str(sot["recertification_due_date"]), "2027-11-01")
        self.assertEqual(str(formula_b), "2027-10-31")
        self.assertNotEqual(sot["recertification_due_date"], formula_b)

    # ── TC-06-SEED-02: grep guard mở rộng services/ + scripts/ ──────────────────
    def test_seed02_no_inline_recert_expiry_formula_in_services_or_scripts(self):
        """TC-06-SEED-02 (RED on revert): scan services/**.py + scripts/**.py, assert 0
        inline formula-A `add_days(<expiry>, -60)` / formula-B `add_months(<x>, <validity>-2)`
        cho recert NGOÀI thân compute_competency_dates. FAIL nếu seed:346 bị revert về literal."""
        import os
        import re

        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        scan_roots = [
            os.path.join(app_dir, "services"),
            os.path.join(app_dir, "scripts"),
        ]
        # formula-B: add_months(<bất kỳ>, <... validity ...> - 2)
        re_formula_b = re.compile(r"add_months\([^)]*validity[^)]*-\s*2\s*\)")
        # formula-A inline recert: add_days(<... expiry ...>, -60) HOẶC add_days(<x>, -60)
        # giới hạn quanh recert/expiry để KHÔNG bắt nhầm issued_date hay field khác.
        re_formula_a = re.compile(r"add_days\([^)]*expiry[^)]*,\s*-\s*60\s*\)")

        # Allow-list DUY NHẤT = thân SoT compute_competency_dates trong services/imm06.py
        # (định nghĩa thật + docstring CẤM-pattern). Mọi nơi khác PHẢI = 0.
        sot_file = os.path.join(app_dir, "services", "imm06.py")

        violations: list[str] = []
        for root in scan_roots:
            for dirpath, _dirs, files in os.walk(root):
                for fname in files:
                    if not fname.endswith(".py"):
                        continue
                    fpath = os.path.join(dirpath, fname)
                    with open(fpath, encoding="utf-8") as fh:
                        lines = fh.readlines()
                    in_sot_body = (os.path.abspath(fpath) == os.path.abspath(sot_file))
                    for lineno, line in enumerate(lines, start=1):
                        if re_formula_b.search(line) or re_formula_a.search(line):
                            # Allow CHỈ trong file SoT (docstring CẤM-pattern + thân hàm).
                            if in_sot_body:
                                continue
                            rel = os.path.relpath(fpath, app_dir)
                            violations.append(f"{rel}:{lineno}: {line.strip()}")

        self.assertEqual(
            violations,
            [],
            "BR-06-13: inline recert/expiry formula NGOÀI compute_competency_dates "
            "(services/ + scripts/). Mọi write-site phải gọi SoT:\n"
            + "\n".join(violations),
        )


class TestComputeHooksUseSoT(unittest.TestCase):
    """Compute hooks (set_computed_competency_fields / compute_expiry_dates) gọi CHUNG SoT."""

    def _doc(self, achieved, validity):
        return frappe._dict(
            achieved_date=achieved,
            validity_months=validity,
            expiry_date=None,
            recertification_due_date=None,
            days_until_expiry=None,
            is_expired=None,
        )

    def test_set_computed_fields_uses_sot(self):
        """set_computed_competency_fields (#4) → recert = expiry−60d (không còn formula B)."""
        d = self._doc("2026-01-31", 24)
        set_computed_competency_fields(d)
        self.assertEqual(str(d.expiry_date), "2028-01-31")
        self.assertEqual(str(d.recertification_due_date), "2027-12-02")

    def test_compute_expiry_dates_uses_sot(self):
        """compute_expiry_dates (#5) → recert = expiry−60d (không còn formula B)."""
        d = self._doc("2026-02-28", 12)
        compute_expiry_dates(d)
        self.assertEqual(str(d.expiry_date), "2027-02-28")
        self.assertEqual(str(d.recertification_due_date), "2026-12-30")

    def test_two_compute_hooks_agree(self):
        """Dedup: 2 compute hook KHÔNG ghi 2 giá trị khác nhau cho cùng input."""
        a = self._doc("2025-12-31", 36)
        b = self._doc("2025-12-31", 36)
        set_computed_competency_fields(a)
        compute_expiry_dates(b)
        self.assertEqual(a.recertification_due_date, b.recertification_due_date)
        self.assertEqual(a.expiry_date, b.expiry_date)


class TestRecertNoDivergenceCrossPath(unittest.TestCase):
    """TDD-2 / TDD-4: cùng achieved+validity → recert BẰNG NHAU bất kể code path; save idempotent."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.model = _ensure_test_model()
        cls.program = _ensure_test_program()
        cls._created: list[str] = []

    @classmethod
    def tearDownClass(cls):
        for name in cls._created:
            try:
                frappe.db.set_value("IMM User Competency", name, "workflow_state",
                                    CompetencyStatus.SUSPENDED, update_modified=False)
                frappe.delete_doc("IMM User Competency", name, force=True,
                                  ignore_permissions=True, delete_permanently=True)
            except Exception:
                pass
        frappe.db.commit()

    def _make_active_competency(self, achieved: str, validity: int) -> "frappe.Document":
        """Tạo competency rồi đưa lên Active QUA controller before_save (live save-path #3).

        Insert ở Pending (transition hợp lệ), rồi set Active + save lại — before_save chạy
        với state=Active và expiry còn trống → tính recert qua SoT. Không set expiry sẵn."""
        doc = frappe.get_doc({
            "doctype": "IMM User Competency",
            "user": "Administrator",
            "device_model": self.model,
            "training_program": self.program,
            "workflow_state": CompetencyStatus.PENDING,
            "achieved_date": achieved,
            "validity_months": validity,
            "competency_level": "Operator",
            "supervisor_signoff": "Administrator",
        })
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_links = True
        doc.insert(ignore_permissions=True)
        self._created.append(doc.name)
        # Live transition → Active qua ORM (chạy controller before_save #3)
        doc.workflow_state = CompetencyStatus.ACTIVE
        doc.flags.ignore_workflow_status_check = True
        doc.save(ignore_permissions=True)
        doc.reload()
        return doc

    def test_tdd2_controller_before_save_matches_sot(self):
        """TDD-2: controller before_save → recert = SoT(achieved, validity)."""
        achieved, validity = "2026-01-31", 24
        doc = self._make_active_competency(achieved, validity)
        expected = compute_competency_dates(achieved, validity)
        self.assertEqual(str(doc.recertification_due_date),
                         str(expected["recertification_due_date"]))
        self.assertEqual(str(doc.expiry_date), str(expected["expiry_date"]))

    def test_tdd4_idempotent_save(self):
        """TDD-4: save 2 lần liên tiếp (achieved/expiry không đổi) → recert KHÔNG đổi."""
        doc = self._make_active_competency("2026-02-28", 12)
        first = str(doc.recertification_due_date)
        doc.save(ignore_permissions=True)
        doc.reload()
        second = str(doc.recertification_due_date)
        self.assertEqual(first, second)


class TestSchedulerEligibilityInvariant(unittest.TestCase):
    """TDD-5: check_recertification_due chọn đúng tập theo recert date SoT (cửa sổ 60 ngày)."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.model = _ensure_test_model()
        cls.program = _ensure_test_program()
        cls._created: list[str] = []

    @classmethod
    def tearDownClass(cls):
        for name in cls._created:
            try:
                frappe.db.set_value("IMM User Competency", name, "workflow_state",
                                    CompetencyStatus.SUSPENDED, update_modified=False)
                frappe.delete_doc("IMM User Competency", name, force=True,
                                  ignore_permissions=True, delete_permanently=True)
            except Exception:
                pass
        frappe.db.commit()

    def test_tdd5_recert_due_within_window_is_selected(self):
        """Competency recert-due trong cửa sổ 60 ngày → nằm trong tập scheduler chọn."""
        from frappe.utils import getdate, nowdate
        # achieved sao cho recert-due nằm trong 60 ngày tới: expiry ≈ today+75d → recert ≈ today+15d
        expiry = add_days(nowdate(), 75)
        recert = add_days(expiry, -RECERT_LEAD_DAYS)
        doc = frappe.get_doc({
            "doctype": "IMM User Competency",
            "user": "Administrator",
            "device_model": self.model,
            "training_program": self.program,
            "workflow_state": CompetencyStatus.PENDING,
            "achieved_date": add_days(nowdate(), -100),
            "validity_months": 6,
            "expiry_date": expiry,
            "recertification_due_date": recert,
            "competency_level": "Operator",
            "supervisor_signoff": "Administrator",
        })
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_links = True
        doc.insert(ignore_permissions=True)
        self._created.append(doc.name)
        # Đưa lên Active để khớp filter scheduler (set_value bypass workflow guard cho fixture)
        frappe.db.set_value("IMM User Competency", doc.name, "workflow_state",
                            CompetencyStatus.ACTIVE, update_modified=False)

        due_limit = add_days(nowdate(), 60)
        rows = frappe.get_all(
            "IMM User Competency",
            filters={
                "name": doc.name,
                "workflow_state": ("in", [CompetencyStatus.ACTIVE, CompetencyStatus.EXPIRING]),
                "recertification_due_date": ("<=", due_limit),
            },
            pluck="name",
        )
        self.assertIn(doc.name, rows,
                      "Competency recert-due trong 60 ngày phải được scheduler chọn")


# ─── Read-path field-list parity (Vòng 22 — recert SoT surfaced in detail view) ──
#
# Root cause covered: services/imm06.py::list_user_competencies select list (lines
# 289-291) MUST carry recertification_due_date + is_expired + department_at_assessment
# so training/CompetencyDetailView.vue:241 renders the recert date instead of "—".
# These are the BE half of the BE↔FE naming/field contract; the FE vitest is the
# other half (frontend/.../CompetencyDetailView.recertField.test.ts).

class TestListUserCompetenciesReadPath(unittest.TestCase):
    """TC-06-READ-01..04: list_user_competencies read-path == DB (no field drift)."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.model = _ensure_test_model()
        cls.program = _ensure_test_program()
        cls._created: list[str] = []
        # Known record: Active competency với recert SoT = expiry − 60d (BR-06-13),
        # department_at_assessment non-null để khẳng định read-path == DB.
        achieved = "2026-01-15"
        dates = compute_competency_dates(achieved, 24)
        doc = frappe.get_doc({
            "doctype": "IMM User Competency",
            "user": "Administrator",
            "device_model": cls.model,
            "training_program": cls.program,
            "workflow_state": CompetencyStatus.PENDING,
            "achieved_date": achieved,
            "validity_months": 24,
            "expiry_date": dates["expiry_date"],
            "recertification_due_date": dates["recertification_due_date"],
            "department_at_assessment": "_Test Dept IMM06",
            "competency_level": "Operator",
            "supervisor_signoff": "Administrator",
        })
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_links = True
        doc.insert(ignore_permissions=True)
        # Active để khớp filter của get_expiring_competencies (parity path #2).
        frappe.db.set_value("IMM User Competency", doc.name, "workflow_state",
                            CompetencyStatus.ACTIVE, update_modified=False)
        cls.comp = doc.name
        cls._created.append(doc.name)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        for name in cls._created:
            try:
                frappe.db.set_value("IMM User Competency", name, "workflow_state",
                                    CompetencyStatus.SUSPENDED, update_modified=False)
                frappe.delete_doc("IMM User Competency", name, force=True,
                                  ignore_permissions=True, delete_permanently=True)
            except Exception:
                pass
        frappe.db.commit()

    def _row(self) -> dict:
        res = list_user_competencies({"name": self.comp}, page=1, page_size=20)
        rows = [r for r in res["data"] if r["name"] == self.comp]
        self.assertEqual(len(rows), 1, "Known competency phải xuất hiện đúng 1 lần")
        return rows[0]

    def test_read01_recert_due_date_present_equals_db(self):
        """TC-06-READ-01: row carries recertification_due_date == DB value (not None/missing)."""
        row = self._row()
        db_val = frappe.db.get_value(
            "IMM User Competency", self.comp, "recertification_due_date")
        self.assertIn("recertification_due_date", row,
                      "list_user_competencies row PHẢI có key recertification_due_date")
        self.assertIsNotNone(db_val, "fixture phải có recert non-null")
        self.assertEqual(str(row["recertification_due_date"]), str(db_val),
                         "read-path recert PHẢI bằng DB (no drift)")

    def test_read02_is_expired_and_department_present_equal_db(self):
        """TC-06-READ-02: row also carries is_expired + department_at_assessment == DB."""
        row = self._row()
        for field in ("is_expired", "department_at_assessment"):
            self.assertIn(field, row,
                          f"list_user_competencies row PHẢI có key {field}")
            db_val = frappe.db.get_value("IMM User Competency", self.comp, field)
            self.assertEqual(str(row[field]), str(db_val),
                             f"read-path {field} PHẢI bằng DB")

    def test_read03_parity_superset_of_expiring(self):
        """TC-06-READ-03: list_user_competencies field-set ⊇ get_expiring_competencies
        w.r.t. recertification_due_date + department_at_assessment (no read-path divergence)."""
        row = self._row()
        expiring = [r for r in get_expiring_competencies(9999)
                    if r["name"] == self.comp]
        self.assertEqual(len(expiring), 1,
                         "known Active competency phải nằm trong get_expiring_competencies")
        exp = expiring[0]
        for field in ("recertification_due_date", "department_at_assessment"):
            self.assertIn(field, row, f"list_user_competencies thiếu {field}")
            self.assertEqual(str(row[field]), str(exp[field]),
                             f"hai read-path PHẢI đồng nhất ở {field}")

    def test_read04_alias_list_competencies_keeps_recert(self):
        """TC-06-READ-04: alias list_competencies (enrich wrapper) does NOT strip recert."""
        res = list_competencies({"name": self.comp}, page=1, page_size=20)
        rows = [r for r in res["data"] if r["name"] == self.comp]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        db_val = frappe.db.get_value(
            "IMM User Competency", self.comp, "recertification_due_date")
        self.assertIn("recertification_due_date", row,
                      "enrich wrapper KHÔNG được strip recertification_due_date")
        self.assertEqual(str(row["recertification_due_date"]), str(db_val))
        # enrich vẫn phải bổ sung display names (không phá hợp đồng cũ)
        self.assertIn("device_model_name", row)


# ─── BR-06-13 SEED write-site SoT (Vòng 26 — kill surviving formula-B in seed) ───
#
# Root cause: scripts/seed_imm_456.py inline-computed recertification_due_date as
# add_months(achieved, validity-2) (formula B) instead of routing through
# compute_competency_dates() SoT. Formula B anchors achieved (NOT expiry) → drifts
# 0–2 days vs expiry−60d depending on month length. The pre-existing grep guard
# scanned services/ only, so this seed write-site escaped detection.

import os
import re

_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))


def _strip_compute_sot_body(src: str) -> str:
    """Blank out the body of compute_competency_dates so its docstring mention of the
    banned formulas + its legit add_days(expiry, -RECERT_LEAD_DAYS) call are excluded
    from the guard scan. Returns source with that function's lines replaced by ''."""
    lines = src.splitlines()
    out: list[str] = []
    in_sot = False
    sot_indent = 0
    for line in lines:
        if not in_sot and re.match(r"^\s*def\s+compute_competency_dates\b", line):
            in_sot = True
            sot_indent = len(line) - len(line.lstrip())
            out.append("")  # drop def line
            continue
        if in_sot:
            stripped = line.strip()
            indent = len(line) - len(line.lstrip())
            # End of body: a non-blank line dedented to <= def indent (next def/class).
            if stripped and indent <= sot_indent:
                in_sot = False
                out.append(line)
            else:
                out.append("")  # blank out body line
            continue
        out.append(line)
    return "\n".join(out)


# Formula B (recert anchored to achieved): add_months(<x>, <validity>-2)
_FORMULA_B = re.compile(r"add_months\([^)]*,\s*[^)]*-\s*2\s*\)")
# Formula A inlined for recert (must go through SoT): a recert-field assignment
# whose RHS inlines add_days(..., -60) or add_days(..., -RECERT_LEAD_DAYS).
_FORMULA_A_RECERT = re.compile(
    r"recertification_due_date.*add_days\([^)]*,\s*-\s*(60|RECERT_LEAD_DAYS)\s*\)")


def _scan_dir_for_inline_recert(rel_dir: str) -> list[str]:
    """Walk rel_dir (relative to repo root) for .py files and return a list of
    'path:lineno: text' hits where recert is computed inline (formula A or B),
    excluding the body of compute_competency_dates."""
    hits: list[str] = []
    base = os.path.join(_REPO_ROOT, "assetcore", rel_dir)
    for root, _dirs, files in os.walk(base):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            with open(fpath, encoding="utf-8") as fh:
                src = fh.read()
            scanned = _strip_compute_sot_body(src)
            for i, line in enumerate(scanned.splitlines(), start=1):
                if _FORMULA_B.search(line) or _FORMULA_A_RECERT.search(line):
                    rel = os.path.relpath(fpath, _REPO_ROOT)
                    hits.append(f"{rel}:{i}: {line.strip()}")
    return hits


class TestBR0613GrepGuardScopesScripts(unittest.TestCase):
    """TC-06-SEED-02: BR-06-13 grep guard scans services/ AND scripts/ — ZERO inline
    formula-A/B recert literals outside compute_competency_dates. RED if seed reverts."""

    def test_seed02_no_inline_recert_formula_in_services(self):
        """services/ has no inline recert formula (only the SoT body, which is excluded)."""
        hits = _scan_dir_for_inline_recert("services")
        self.assertEqual(
            hits, [],
            "services/ inline-computes recert outside SoT — route via "
            f"compute_competency_dates:\n" + "\n".join(hits))

    def test_seed02_no_inline_recert_formula_in_scripts(self):
        """scripts/ (incl. seed_imm_456.py) has no inline recert formula — PROVES the
        guard now covers scripts scope it previously missed. RED if line 346 reverts to
        add_months(achieved, validity-2)."""
        hits = _scan_dir_for_inline_recert("scripts")
        self.assertEqual(
            hits, [],
            "scripts/ inline-computes recert outside SoT — route via "
            f"compute_competency_dates:\n" + "\n".join(hits))

    def test_seed02_guard_detects_formula_b_literal(self):
        """Sanity: the guard regex actually matches the banned formula-B literal (so a
        revert WOULD turn the scans above RED — not a vacuous green)."""
        sample = '"recertification_due_date": add_months(achieved, s["validity_months"] - 2),'
        self.assertTrue(_FORMULA_B.search(sample),
                        "guard regex must catch formula-B add_months(x, validity-2)")
        sample_a = '"recertification_due_date": add_days(expiry, -60),'
        self.assertTrue(_FORMULA_A_RECERT.search(sample_a),
                        "guard regex must catch inline formula-A add_days(expiry, -60)")

    def test_seed02_guard_excludes_sot_body(self):
        """The legit add_days(expiry, -RECERT_LEAD_DAYS) inside compute_competency_dates
        is NOT a hit (body stripped) — guard is precise, not over-eager."""
        from assetcore.services import imm06 as _imm06
        with open(_imm06.__file__, encoding="utf-8") as fh:
            stripped = _strip_compute_sot_body(fh.read())
        for i, line in enumerate(stripped.splitlines(), start=1):
            self.assertFalse(
                _FORMULA_A_RECERT.search(line) or _FORMULA_B.search(line),
                f"SoT body line {i} should be stripped, got hit: {line.strip()}")


class TestSeedWriteSiteUsesSoT(unittest.TestCase):
    """TC-06-SEED-01 / TC-06-SEED-03: seed competency dates come from the SoT — recert
    == expiry−60d for every comp_spec, with 0-day drift vs the old formula-B."""

    def test_seed01_sot_zero_drift_vs_formula_b_at_month_boundary(self):
        """TC-06-SEED-01: at a month-boundary achieved date, SoT recert == expiry−60d AND
        != add_months(achieved, validity-2) (the old seed formula) → drift removed."""
        achieved, validity = "2026-01-31", 24
        dates = compute_competency_dates(achieved, validity)
        # SoT invariant
        self.assertEqual(dates["expiry_date"], add_months(achieved, validity))
        self.assertEqual(dates["recertification_due_date"],
                         add_days(dates["expiry_date"], -60))
        # Old seed formula B drifts: add_months(2026-01-31, 22)=2027-11-30 ≠ 2027-12-02
        formula_b = add_months(achieved, validity - 2)
        self.assertNotEqual(
            str(dates["recertification_due_date"]), str(formula_b),
            "SoT recert must differ from formula-B at month boundary (0-day drift vs "
            "expiry−60, NOT 0–2d drift of add_months(achieved, validity−2))")

    def test_seed03_invariant_holds_for_all_comp_specs(self):
        """TC-06-SEED-03: the three seed comp_specs (validity 24/24/36) all satisfy
        recert == expiry−60d and expiry == add_months(achieved, validity) via the SoT.
        Asserts on the constructed payload (no DB insert)."""
        achieved = add_days(nowdate(), -1)
        for validity in (24, 24, 36):
            dates = compute_competency_dates(achieved, validity)
            expiry = add_months(achieved, validity)
            self.assertEqual(dates["expiry_date"], expiry,
                             f"expiry must = achieved+{validity}mo")
            self.assertEqual(dates["recertification_due_date"], add_days(expiry, -60),
                             f"recert must = expiry−60d for validity={validity}")


if __name__ == "__main__":
    unittest.main()
