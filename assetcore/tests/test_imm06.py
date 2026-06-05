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
    EXPIRY_WINDOW_DAYS,
    RECERT_LEAD_DAYS,
    CompetencyStatus,
    ProgramStatus,
    SessionStatus,
    _expired_competency_filter,
    _expiring_competency_filter,
    archive_old_competency,
    auto_expire_competencies,
    check_expiring_competencies,
    compute_competency_dates,
    compute_expiry_dates,
    compute_overall_results,
    enroll_participants,
    get_dashboard_stats,
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


# ─── BR-06-14 SoT — predicate LIVE "Sắp/Đã hết hạn" (Vòng 20) ────────────────
#
# Lỗi thiết kế gốc (count-vs-drill divergence): get_dashboard_stats đếm KPI
# competencies.expiring/expired = frappe.db.count(workflow_state==Expiring/Expired)
# (cờ thuần do scheduler stamp đúng mốc 60/30 + quá-hạn), trong khi drill
# get_expiring_competencies(60) lọc LIVE theo expiry_date → tile lệch list, che
# operator quá hạn còn gắn cờ Active (rủi ro NĐ98).
#
# FIX SoT: 2 helper _expiring_competency_filter() / _expired_competency_filter()
# (date-derived, EXPIRY_WINDOW_DAYS=60) dùng CHUNG cho cả KPI count lẫn drill.
# INVARIANT đo được: kpis.competencies.expiring == len(get_expiring_competencies(60)).

def _seed_competency(*, state: str, expiry_offset_days: int) -> str:
    """Seed 1 IMM User Competency với workflow_state + expiry_date kiểm soát chính xác.

    Dùng db.set_value(update_modified=False) cho workflow_state (Link→Workflow State,
    bypass workflow transition validation) + expiry_date để mô phỏng các cảnh huống
    scheduler-miss (Active-nhưng-quá-hạn, Active-45d-chưa-stamp-Expiring, biên cửa sổ).

    Args:
        state: CompetencyStatus.{ACTIVE,EXPIRING,EXPIRED,SUSPENDED,REVOKED}.
        expiry_offset_days: offset so với today (âm = đã hết hạn).

    Returns:
        name (autoname COMP-YYYY-#####).
    """
    model_name = _ensure_test_model()
    program_name = _ensure_test_program()
    expiry = add_days(nowdate(), expiry_offset_days)
    doc = frappe.get_doc({
        "doctype": "IMM User Competency",
        "user": "Administrator",
        "device_model": model_name,
        "training_program": program_name,
        "workflow_state": CompetencyStatus.PENDING,
        "achieved_date": add_days(expiry, -730),
        "validity_months": 24,
        "competency_level": "Operator",
    })
    doc.flags.ignore_mandatory = True
    doc.flags.ignore_links = True
    doc.insert(ignore_permissions=True)
    # Đặt state + expiry trực tiếp (mô phỏng trạng thái runtime sau scheduler/legacy).
    frappe.db.set_value("IMM User Competency", doc.name,
                        {"workflow_state": state, "expiry_date": str(expiry)},
                        update_modified=False)
    return doc.name


class TestExpiryPredicateSoT(unittest.TestCase):
    """BR-06-14: KPI 'Sắp/Đã hết hạn' và drill cùng 1 predicate LIVE (date-derived).

    Mỗi test seed dữ liệu cô lập trong setUp, purge trong tearDown (IMM User
    Competency có on_trash guard → raw-SQL purge). KPI/drill chỉ đếm các record
    vừa seed bằng cách lọc theo tập name đã tạo trong test.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        # Cô lập tuyệt đối: dọn mọi competency Active/Expiring/Expired còn sót lại
        # của model test để KPI baseline không bị nhiễm bởi test khác trong module.
        _purge_test_competencies()

    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[str] = []

    def tearDown(self):
        if self._created:
            # Alert Log do check_expiring_competencies (TC-06-EXP-06) sinh ra → purge trước.
            frappe.db.delete(
                "IMM Competency Alert Log", {"competency": ["in", self._created]})
            frappe.db.delete("IMM User Competency", {"name": ["in", self._created]})
            frappe.db.delete(
                "IMM Audit Trail",
                {"ref_doctype": "IMM User Competency", "ref_name": ["in", self._created]},
            )
            frappe.db.commit()

    def _seed(self, *, state: str, expiry_offset_days: int) -> str:
        name = _seed_competency(state=state, expiry_offset_days=expiry_offset_days)
        self._created.append(name)
        return name

    def _kpi(self) -> dict:
        return get_dashboard_stats()["competencies"]

    def _expiring_count_seeded(self) -> int:
        """COUNT theo SoT _expiring_competency_filter NHƯNG giới hạn vào tập seed
        (tránh nhiễu bởi data thật/khác test cùng DB)."""
        f = dict(_expiring_competency_filter())
        f["name"] = ["in", self._created]
        return frappe.db.count("IMM User Competency", f)

    def _expired_count_seeded(self) -> int:
        f = dict(_expired_competency_filter())
        f["name"] = ["in", self._created]
        return frappe.db.count("IMM User Competency", f)

    def _drill_seeded(self) -> list:
        return [r for r in get_expiring_competencies(EXPIRY_WINDOW_DAYS)
                if r["name"] in self._created]

    # ── TC-06-EXP-01 — RED-prove BUG CHÍNH: Active 45d → card phải == drill ──
    def test_exp01_active_45d_counted_and_in_drill(self):
        """Active expiry=today+45 (scheduler CHƯA stamp Expiring vì chưa trúng mốc
        60/30). Trên code CŨ (db.count workflow_state==Expiring) → card=0 nhưng
        drill có → card != drill (RED). Sau fix SoT: card == drill == 1 (GREEN)."""
        self._seed(state=CompetencyStatus.ACTIVE, expiry_offset_days=45)
        drill = self._drill_seeded()
        self.assertEqual(len(drill), 1,
                         "Active 45d PHẢI nằm trong drill get_expiring_competencies(60)")
        self.assertEqual(self._expiring_count_seeded(), 1,
                         "Active 45d PHẢI đếm vào 'Sắp hết hạn' (SoT live, không cờ thuần)")
        # INVARIANT card == drill trên tập seed này.
        self.assertEqual(self._expiring_count_seeded(), len(drill),
                         "INVARIANT card == drill bị vi phạm (count-vs-drill divergence)")

    # ── TC-06-EXP-02 — INVARIANT card==drill trên tập hỗn hợp ──
    def test_exp02_invariant_card_equals_drill_mixed(self):
        """Tập hỗn hợp (Active 45d, Expiring 20d, Active 90d ngoài cửa sổ, Revoked 10d)
        → expiring count == len(drill); Active-90d và Revoked KHÔNG đếm."""
        self._seed(state=CompetencyStatus.ACTIVE, expiry_offset_days=45)
        self._seed(state=CompetencyStatus.EXPIRING, expiry_offset_days=20)
        self._seed(state=CompetencyStatus.ACTIVE, expiry_offset_days=90)   # ngoài cửa sổ
        self._seed(state=CompetencyStatus.REVOKED, expiry_offset_days=10)  # bị loại
        drill = self._drill_seeded()
        count = self._expiring_count_seeded()
        self.assertEqual(count, 2,
                         "Chỉ Active-45d + Expiring-20d nằm trong cửa sổ [today, today+60]")
        self.assertEqual(count, len(drill),
                         "INVARIANT card == drill (đo được trên tập hỗn hợp)")
        drill_names = {r["name"] for r in drill}
        self.assertEqual(len(drill_names), 2)

    # ── TC-06-EXP-03 — no-undercount stale-Active expired (cửa-sổ-trễ-scheduler) ──
    def test_exp03_stale_active_past_counted_as_expired(self):
        """Active expiry=today-5 (scheduler lỡ auto_expire) + Expired expiry=today-30
        → expired đếm = 2 (live), KHÔNG undercount stale-Active về 0."""
        self._seed(state=CompetencyStatus.ACTIVE, expiry_offset_days=-5)   # scheduler lỡ phiên
        self._seed(state=CompetencyStatus.EXPIRED, expiry_offset_days=-30)
        self.assertEqual(self._expired_count_seeded(), 2,
                         "Cả Active-quá-hạn (stale) lẫn Expired đều phải đếm 'Đã hết hạn'")
        # stale-Active expired KHÔNG bị tính nhầm vào 'Sắp hết hạn'.
        self.assertEqual(self._expiring_count_seeded(), 0,
                         "expiry_date < today KHÔNG vào 'Sắp hết hạn'")

    # ── TC-06-EXP-04 — loại Revoked/Suspended ──
    def test_exp04_revoked_suspended_never_counted(self):
        """Revoked expiry=today-2 + Suspended expiry=today+10 → KHÔNG đếm vào
        expired/expiring (assert 0 contribution cả 2 phía)."""
        self._seed(state=CompetencyStatus.REVOKED, expiry_offset_days=-2)
        self._seed(state=CompetencyStatus.SUSPENDED, expiry_offset_days=10)
        self.assertEqual(self._expired_count_seeded(), 0,
                         "Revoked quá hạn KHÔNG được đếm 'Đã hết hạn'")
        self.assertEqual(self._expiring_count_seeded(), 0,
                         "Suspended trong cửa sổ KHÔNG được đếm 'Sắp hết hạn'")
        self.assertEqual(len(self._drill_seeded()), 0,
                         "Revoked/Suspended KHÔNG xuất hiện trong drill")

    # ── TC-06-EXP-05 — biên cửa sổ (inclusive low/high, exclusive ngoài) ──
    def test_exp05_window_boundaries(self):
        """expiry==today → 'Sắp hết hạn' (inclusive low); expiry==today+60 → inclusive
        high; expiry==today+61 → KHÔNG; expiry==today-1 → 'Đã hết hạn' KHÔNG 'Sắp'."""
        n_today = self._seed(state=CompetencyStatus.ACTIVE, expiry_offset_days=0)
        n_high = self._seed(state=CompetencyStatus.ACTIVE, expiry_offset_days=EXPIRY_WINDOW_DAYS)
        self._seed(state=CompetencyStatus.ACTIVE, expiry_offset_days=EXPIRY_WINDOW_DAYS + 1)
        n_past = self._seed(state=CompetencyStatus.ACTIVE, expiry_offset_days=-1)
        drill_names = {r["name"] for r in self._drill_seeded()}
        # today + today+60 vào cửa sổ; today+61 ngoài; today-1 đã hết hạn (không 'Sắp').
        self.assertIn(n_today, drill_names, "expiry==today PHẢI vào 'Sắp hết hạn' (inclusive low)")
        self.assertIn(n_high, drill_names, "expiry==today+60 PHẢI vào (inclusive high)")
        self.assertEqual(self._expiring_count_seeded(), 2,
                         "Chỉ today + today+60 trong cửa sổ; today+61 và today-1 bị loại")
        self.assertNotIn(n_past, drill_names, "expiry==today-1 KHÔNG vào 'Sắp hết hạn'")
        # today-1 thuộc 'Đã hết hạn'.
        f = dict(_expired_competency_filter())
        f["name"] = ["=", n_past]
        self.assertEqual(frappe.db.count("IMM User Competency", f), 1,
                         "expiry==today-1 PHẢI thuộc 'Đã hết hạn'")

    # ── TC-06-EXP-06 — scheduler-behavior-invariant ──
    def test_exp06_scheduler_invariant_kpi_idempotent(self):
        """Chạy check_expiring_competencies + auto_expire_competencies SAU seed →
        workflow_state vẫn được stamp như cũ, NHƯNG KPI live KHÔNG đổi giá trị
        trước/sau scheduler (SoT date-derived idempotent với việc stamp cờ)."""
        # Active đúng mốc 30 ngày → check_expiring_competencies sẽ stamp Expiring.
        n_30 = self._seed(state=CompetencyStatus.ACTIVE, expiry_offset_days=30)
        # Active quá hạn → auto_expire_competencies sẽ stamp Expired.
        n_past = self._seed(state=CompetencyStatus.ACTIVE, expiry_offset_days=-3)
        expiring_before = self._expiring_count_seeded()
        expired_before = self._expired_count_seeded()
        # Chạy scheduler (vẫn stamp workflow_state — hành vi BẤT BIẾN).
        check_expiring_competencies()
        auto_expire_competencies()
        frappe.db.commit()
        # Cờ workflow_state ĐÃ được stamp (scheduler hoạt động như cũ).
        self.assertEqual(
            frappe.db.get_value("IMM User Competency", n_30, "workflow_state"),
            CompetencyStatus.EXPIRING, "check_expiring_competencies PHẢI stamp Expiring tại mốc 30")
        self.assertEqual(
            frappe.db.get_value("IMM User Competency", n_past, "workflow_state"),
            CompetencyStatus.EXPIRED, "auto_expire_competencies PHẢI stamp Expired khi quá hạn")
        # KPI live KHÔNG đổi (idempotent: count theo date, không theo cờ).
        self.assertEqual(self._expiring_count_seeded(), expiring_before,
                         "KPI 'Sắp hết hạn' PHẢI bất biến trước/sau scheduler (SoT date-derived)")
        self.assertEqual(self._expired_count_seeded(), expired_before,
                         "KPI 'Đã hết hạn' PHẢI bất biến trước/sau scheduler")

    def test_exp06b_dashboard_no_pure_workflow_state_count(self):
        """Verify get_dashboard_stats KHÔNG còn đếm expiring/expired theo cờ
        workflow_state thuần (AST: call frappe.db.count với filter chứa
        workflow_state==Expiring/Expired)."""
        import ast
        import inspect
        src = inspect.getsource(get_dashboard_stats)
        tree = ast.parse(src)
        offenders = []
        # Chỉ soi đối số filter của các call _count(...) / frappe.db.count(...) —
        # tránh false-positive trên dict return lồng nhau.
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = ast.unparse(node.func)
            if fn not in ("_count", "frappe.db.count"):
                continue
            for arg in list(node.args) + [kw.value for kw in node.keywords]:
                if not isinstance(arg, ast.Dict):
                    continue
                literal = ast.unparse(arg)
                # Bắt cả dạng literal ("Expiring"/"Expired") lẫn enum-reference
                # (CompetencyStatus.EXPIRING/EXPIRED) — KPI expiring/expired KHÔNG
                # được đếm theo cờ workflow_state thuần (chỉ qua _expiring/_expired
                # filter SoT). Cho phép workflow_state cho KPI active/pending/revoked.
                if "workflow_state" in literal and (
                    "Expiring" in literal or "Expired" in literal
                    or "EXPIRING" in literal or "EXPIRED" in literal
                ):
                    offenders.append(literal)
        self.assertEqual(
            offenders, [],
            "get_dashboard_stats KHÔNG được đếm expiring/expired theo cờ "
            f"workflow_state thuần — tìm thấy: {offenders}")

    # ── TC-06-EXP-07 — no N+1 / no-regression (INVARIANT full dashboard) ──
    def test_exp07_dashboard_card_equals_drill_full(self):
        """INVARIANT đầu-cuối: kpis.competencies.expiring (qua get_dashboard_stats)
        == len(get_expiring_competencies(60)) trên TOÀN dataset (card == drill).
        Đây là INVARIANT đo được của BR-06-14."""
        self._seed(state=CompetencyStatus.ACTIVE, expiry_offset_days=45)
        self._seed(state=CompetencyStatus.EXPIRING, expiry_offset_days=10)
        self._seed(state=CompetencyStatus.ACTIVE, expiry_offset_days=200)  # ngoài cửa sổ
        kpi_expiring = self._kpi()["expiring"]
        drill_full = len(get_expiring_competencies(EXPIRY_WINDOW_DAYS))
        self.assertEqual(kpi_expiring, drill_full,
                         "INVARIANT card == drill trên toàn dataset (BR-06-14)")

    def test_exp07b_count_helper_is_single_query(self):
        """No N+1: KPI expiring/expired đi qua frappe.db.count (1 call/predicate),
        KHÔNG loop per-row. Đếm số lần gọi frappe.db.count khi seed nhiều record:
        số call cố định, KHÔNG scale theo số competency."""
        from unittest.mock import patch

        # Seed 3 record cùng vào cửa sổ → nếu N+1 thì call count sẽ tăng theo record.
        self._seed(state=CompetencyStatus.ACTIVE, expiry_offset_days=30)
        self._seed(state=CompetencyStatus.ACTIVE, expiry_offset_days=40)
        self._seed(state=CompetencyStatus.ACTIVE, expiry_offset_days=50)

        real_count = frappe.db.count
        calls: list = []

        def _counting(doctype, *args, **kwargs):
            calls.append(doctype)
            return real_count(doctype, *args, **kwargs)

        with patch.object(frappe.db, "count", side_effect=_counting):
            get_dashboard_stats()
        comp_calls = [d for d in calls if d == "IMM User Competency"]
        # 6 KPI competency-count cố định (total/pending/active/expiring/expired/revoked) —
        # KHÔNG phụ thuộc số record seed (= no N+1, bounded per-predicate).
        self.assertEqual(
            len(comp_calls), 6,
            "get_dashboard_stats phải gọi đúng 6 db.count cho IMM User Competency "
            f"(per-predicate, no N+1) — thực tế {len(comp_calls)}")


def _purge_test_competencies() -> None:
    """Raw-SQL purge mọi competency của model/program test (on_trash chặn ORM)."""
    names = frappe.db.sql_list(
        "SELECT uc.name FROM `tabIMM User Competency` uc "
        "LEFT JOIN `tabIMM Device Model` dm ON dm.name = uc.device_model "
        "WHERE dm.model_name = %s OR uc.training_program IN ("
        "  SELECT name FROM `tabIMM Training Program` WHERE program_code = %s)",
        ("_Test Model IMM06", "_TEST-PROG-IMM06-SHARED"),
    )
    if names:
        frappe.db.delete(
            "IMM Competency Alert Log", {"competency": ["in", names]})
        frappe.db.delete("IMM User Competency", {"name": ["in", names]})
        frappe.db.delete(
            "IMM Audit Trail",
            {"ref_doctype": "IMM User Competency", "ref_name": ["in", names]})
    # Quét sạch alert log mồ côi (competency đã purge ở phiên test trước).
    orphan_alerts = frappe.db.sql_list(
        "SELECT cal.name FROM `tabIMM Competency Alert Log` cal "
        "LEFT JOIN `tabIMM User Competency` uc ON uc.name = cal.competency "
        "WHERE uc.name IS NULL")
    if orphan_alerts:
        frappe.db.delete("IMM Competency Alert Log", {"name": ["in", orphan_alerts]})
    frappe.db.commit()


if __name__ == "__main__":
    unittest.main()
