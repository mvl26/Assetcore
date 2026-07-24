# Copyright (c) 2026, AssetCore Team
"""IMM-06 unit tests — validators, compute_overall_results, signoff, archive_old_competency.

Run: bench --site miyano run-tests --app assetcore --module assetcore.tests.test_imm06
"""
from __future__ import annotations

import contextlib
import json
import unittest

import frappe
from frappe.utils import add_days, add_months, nowdate

from assetcore.services.imm06 import (
    EXPIRY_WINDOW_DAYS,
    RECERT_LEAD_DAYS,
    COMPETENCY_RECERTIFY,
    COMPETENCY_RESTORE,
    COMPETENCY_REVOKE,
    COMPETENCY_SIGNOFF,
    COMPETENCY_SUSPEND,
    CompetencyStatus,
    ProgramStatus,
    SessionStatus,
    _COMPETENCY_VALID_TRANSITIONS,
    _SESSION_VALID_TRANSITIONS,
    _competency_states_allowing,
    _expired_competency_filter,
    _expiring_competency_filter,
    _session_source_states,
    archive_old_competency,
    get_competency,
    recertify_competency,
    restore_competency,
    revoke_competency,
    suspend_competency,
    auto_expire_competencies,
    cancel_session,
    check_expiring_competencies,
    close_session,
    complete_training_session,
    compute_competency_dates,
    compute_expiry_dates,
    compute_overall_results,
    confirm_session,
    create_training_session,
    enroll_participants,
    get_dashboard_stats,
    get_expiring_competencies,
    get_session,
    get_user_competencies,
    list_competencies,
    list_user_competencies,
    remove_participant,
    set_computed_competency_fields,
    signoff_competency,
    start_training_session,
    get_program_score_bounds,
    validate_passing_score_range,
    validate_score_bounds_config,
    validate_validity_range,
    verify_session,
)
from assetcore.api import imm06 as api06
from assetcore.services.shared import ErrorCode, ServiceError


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


# ─── get_user_competencies — enrich display names (CR-34a) ────────────────────

class TestGetUserCompetenciesEnrichment(unittest.TestCase):
    """CR-34a — get_user_competencies bồi display-name per item[]:
    device_model_name + training_program_name (reuse _enrich_competency_display_names),
    chống rò Link-ID thô ra mobile 'Năng lực của tôi' (Spec 45). LIST trả None cho
    link absent/broken (mobile OMIT — KHÔNG raw-ID fallback như detail)."""

    # 10 raw fields VERBATIM UserCompetencyRepo.list @services/imm06.py:1538-1541.
    _RAW_FIELDS = {
        "name", "device_model", "training_program", "competency_level", "workflow_state",
        "achieved_date", "expiry_date", "days_until_expiry", "is_expired", "last_assessment_score",
    }

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls._created: list[str] = []

    @classmethod
    def tearDownClass(cls):
        # BR-06-09 on_trash guard blocks ORM delete → raw purge (parity tearDownModule).
        if cls._created:
            frappe.db.delete("IMM User Competency", {"name": ["in", cls._created]})
            frappe.db.delete(
                "IMM Audit Trail",
                {"ref_doctype": "IMM User Competency", "ref_name": ["in", cls._created]},
            )
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")

    def _row_for(self, comp: str) -> dict:
        result = get_user_competencies("Administrator")
        self.assertIn("items", result, "get_user_competencies PHẢI trả key 'items'.")
        rows = [it for it in result["items"] if it.get("name") == comp]
        self.assertEqual(len(rows), 1, f"PHẢI đúng 1 hồ-sơ khớp {comp} trong items[].")
        return rows[0]

    def test_device_model_name_resolved_not_raw_id(self):
        comp = _make_competency("Administrator", "")
        self.__class__._created.append(comp)
        model = _ensure_test_model()
        row = self._row_for(comp)
        self.assertEqual(
            row["device_model_name"], "_Test Model IMM06",
            "device_model_name PHẢI = IMM Device Model.model_name (KHÔNG raw Link-ID 'DM-...').",
        )
        self.assertEqual(row["device_model"], model, "device_model raw = PK (giữ nguyên).")
        self.assertNotEqual(
            row["device_model_name"], row["device_model"],
            "name bồi KHÁC raw ID (chống rò Link-ID thô ra mobile).",
        )

    def test_training_program_name_resolved(self):
        comp = _make_competency("Administrator", "")
        self.__class__._created.append(comp)
        row = self._row_for(comp)
        self.assertEqual(
            row["training_program_name"], "_Test Program IMM06 Shared",
            "training_program_name PHẢI = IMM Training Program.program_name (SSoT parity imm06.py:1193).",
        )

    def test_missing_links_name_fields_none_no_crash(self):
        comp = _make_competency("Administrator", "")
        self.__class__._created.append(comp)
        # Blank cả 2 Link trực-tiếp (bypass controller) → test null-safe cho LIST.
        frappe.db.set_value("IMM User Competency", comp, "device_model", "")
        frappe.db.set_value("IMM User Competency", comp, "training_program", "")
        row = self._row_for(comp)
        self.assertIsNone(
            row["device_model_name"],
            "device_model rỗng → device_model_name is None (mobile OMIT, 0 raw-ID leak, KHÔNG KeyError).",
        )
        self.assertIsNone(
            row["training_program_name"],
            "training_program rỗng → training_program_name is None (LIST KHÔNG raw-ID fallback).",
        )

    def test_item_field_set_superset_guard(self):
        comp = _make_competency("Administrator", "")
        self.__class__._created.append(comp)
        row = self._row_for(comp)
        expected = self._RAW_FIELDS | {
            "device_model_name", "training_program_name", "user_full_name",
        }
        self.assertEqual(
            set(row.keys()), expected,
            "items[] field-set PHẢI = 10 raw + device_model_name + training_program_name + "
            f"user_full_name (regression guard chống drift): {sorted(row.keys())}.",
        )


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


# ─── GATE-8/LL-FE-51: server-driven CTA cho Training Session ──────────────────

# CR-WF-06-SESSION (Vòng 28) — reconcile SSoT ⇄ workflow JSON; EXCEPTION_EDGES == ∅.
#
# `_SESSION_EXCEPTION_EDGES` khai TƯỜNG MINH == frozenset() (0 cạnh ngoại lệ).
# TƯƠNG PHẢN competency (`test_competency_allowed_transitions_matches_workflow`,
# 4 EXCEPTION_EDGES): session state-machine 100% CTA người dùng — KHÔNG
# scheduler-auto (Active→Expired…), KHÔNG create-new (recertify sinh doc mới) —
# nên MỌI cạnh workflow map 1:1 vào `_SESSION_VALID_TRANSITIONS` (value =
# next-state cụ thể). ⇒ symmetric_difference(workflow_pairs, map_pairs) PHẢI
# rỗng; cạnh lạ bất kỳ (1 phía có, phía kia thiếu) = drift → RED.
_SESSION_EXCEPTION_EDGES: frozenset = frozenset()

# Tập nhãn-hành-động hợp lệ của "IMM-06 Session Workflow" (anti-drift): label lạ
# trong JSON → assertIn RED → buộc người sửa cập nhật bảng + kiểm có cạnh mới.
_SESSION_WF_ACTION_LABELS: frozenset = frozenset({
    "Xác nhận", "Bắt đầu", "Hoàn thành", "Verify", "Đóng", "Hủy",
})


class TestSessionAllowedTransitions(unittest.TestCase):
    """IMM-06 Buổi đào tạo — get_session emit `allowed_transitions` khớp EXACT
    SSoT `_SESSION_VALID_TRANSITIONS`, và 6 service transition đọc guard từ CHUNG
    map (map↔guard KHÔNG drift). Đối xứng test_imm08.TestPmAllowedTransitions +
    test_imm09.TestRepairAllowedTransitions.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
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
        for name in cls._sessions:
            if frappe.db.exists("IMM Training Session", name):
                frappe.delete_doc("IMM Training Session", name,
                                  force=True, ignore_permissions=True)
        frappe.delete_doc("IMM Training Program", cls.prog,
                          force=True, ignore_permissions=True)
        frappe.db.commit()

    def _session(self, state: str = SessionStatus.PLANNED) -> str:
        """Tạo buổi đào tạo có 1 học viên rồi ép workflow_state = ``state``
        (qua db.set_value → bỏ qua controller side-effects)."""
        sess = frappe.get_doc({
            "doctype": "IMM Training Session",
            "training_program": self.prog,
            "session_date": nowdate(),
            "session_type": "Onsite",
            "duration_planned_hours": 4,
            "instructor": "Administrator",
        })
        sess.append("participants", {"user": "Administrator",
                                     "role_at_session": "Operator"})
        sess.flags.ignore_links = True
        sess.insert(ignore_permissions=True)
        frappe.db.set_value("IMM Training Session", sess.name,
                            "workflow_state", state)
        frappe.db.commit()
        type(self)._sessions.append(sess.name)
        return sess.name

    # ── TC1-TC4: allowed_transitions khớp EXACT map (thứ tự ổn định) ──────────

    def test_tc1_planned_allowed(self):
        name = self._session(SessionStatus.PLANNED)
        self.assertEqual(
            get_session(name)["allowed_transitions"],
            ["Confirmed", "In Progress", "Cancelled"],
        )

    def test_tc2_confirmed_allowed(self):
        name = self._session(SessionStatus.CONFIRMED)
        self.assertEqual(
            get_session(name)["allowed_transitions"],
            ["In Progress", "Cancelled"],
        )

    def test_tc3_in_progress_allowed(self):
        name = self._session(SessionStatus.IN_PROGRESS)
        self.assertEqual(get_session(name)["allowed_transitions"], ["Completed"])

    def test_tc4_completed_verified_terminal(self):
        cases = {
            SessionStatus.COMPLETED: ["Verified"],
            SessionStatus.VERIFIED: ["Closed"],
            SessionStatus.CLOSED: [],
            SessionStatus.CANCELLED: [],
        }
        for state, expected in cases.items():
            name = self._session(state)
            self.assertEqual(
                get_session(name)["allowed_transitions"], expected,
                msg=f"allowed_transitions sai cho state={state}",
            )

    # ── TC5: regression desync — Bắt đầu từ Planned hợp lệ (imm06.py:242) ─────

    def test_tc5_desync_start_from_planned(self):
        name = self._session(SessionStatus.PLANNED)
        # 1) map PHẢI offer 'In Progress' cho buổi Planned (trước fix thiếu → FE ẩn nút)
        self.assertIn("In Progress", get_session(name)["allowed_transitions"])
        # 2) service start_session từ Planned chạy thành công, KHÔNG throw
        res = start_training_session(name)
        self.assertEqual(res["workflow_state"], SessionStatus.IN_PROGRESS)
        self.assertEqual(
            frappe.db.get_value("IMM Training Session", name, "workflow_state"),
            SessionStatus.IN_PROGRESS,
        )

    # ── TC6: invariant map↔guard — chống drift ──────────────────────────────

    def test_tc6_map_guard_no_drift(self):
        all_states = list(_SESSION_VALID_TRANSITIONS.keys())
        specs = [
            (SessionStatus.CONFIRMED, lambda n: confirm_session(n)),
            (SessionStatus.IN_PROGRESS, lambda n: start_training_session(n)),
            # Reconcile BR-06-08: `_session` gắn 1 participant "Administrator". Gate
            # empty-scoring mới raise VALIDATION (≠ BAD_STATE) khi results=[], nên
            # nhánh COMPLETED phải chấm 1 result KHỚP participant để test đúng
            # forward-happy-path (không raise) thay vì dựa vào VALIDATION≠BAD_STATE.
            (SessionStatus.COMPLETED, lambda n: complete_training_session(
                n, [{"user": "Administrator",
                     "theory_score": 0, "practical_score": 0}])),
            (SessionStatus.VERIFIED, lambda n: verify_session(n)),
            (SessionStatus.CLOSED, lambda n: close_session(n)),
            (SessionStatus.CANCELLED, lambda n: cancel_session(n, "Lý do hủy hợp lệ")),
        ]
        for next_state, invoke in specs:
            sources = _session_source_states(next_state)
            self.assertTrue(
                sources, msg=f"{next_state} phải có ≥1 state nguồn trong map")
            # Forward: từ MỖI state nguồn hợp lệ → service KHÔNG raise BAD_STATE.
            for s in sources:
                name = self._session(s)
                try:
                    invoke(name)
                except ServiceError as e:
                    self.assertNotEqual(
                        e.code, ErrorCode.BAD_STATE,
                        msg=f"→{next_state}: nguồn hợp lệ {s} KHÔNG được raise BAD_STATE",
                    )
            # Reverse: từ state NGOÀI tập nguồn → service PHẢI raise BAD_STATE.
            for s in [x for x in all_states if x not in sources]:
                name = self._session(s)
                with self.assertRaises(ServiceError) as ctx:
                    invoke(name)
                self.assertEqual(
                    ctx.exception.code, ErrorCode.BAD_STATE,
                    msg=f"→{next_state}: state ngoài map {s} PHẢI raise BAD_STATE",
                )

    # ── CR-WF-06-SESSION: reconcile map ⇄ workflow JSON (EXCEPTION_EDGES == ∅) ─

    def test_session_allowed_transitions_matches_workflow(self):
        """SSoT `_SESSION_VALID_TRANSITIONS` (next-state) reconcile ⇄ file workflow
        `imm_06_session_workflow.json` (name "IMM-06 Session Workflow", doctype IMM
        Training Session). Symmetric-difference các cạnh `(state, next_state)` giữa 2
        nguồn PHẢI == `_SESSION_EXCEPTION_EDGES` (== frozenset() — 0 ngoại lệ). Parity
        R26 competency `test_competency_allowed_transitions_matches_workflow`.

        TƯƠNG PHẢN competency (4 EXCEPTION_EDGES: 3 scheduler-auto + 1 create-new):
        session-state-machine 100% CTA người dùng ⇒ map ≡ workflow (8 cạnh khớp hệt).

        RED-before demo: gỡ 'In Progress' khỏi `map[Planned]` → sym-diff mọc
        {('Planned','In Progress')} ≠ ∅ → RED (CTA 'Bắt đầu' ẩn ở buổi Planned dù
        workflow còn cạnh). Restore → GREEN.
        """
        path = frappe.get_app_path(
            "assetcore", "assetcore", "workflow", "imm_06_session_workflow.json")
        with open(path, encoding="utf-8") as fh:
            wf = json.load(fh)

        # Anti-drift nhãn: mọi action-label workflow PHẢI ∈ tập đã khai (lạ → RED).
        for t in wf["transitions"]:
            self.assertIn(
                t["action"], _SESSION_WF_ACTION_LABELS,
                msg=(f"Action-label workflow '{t['action']}' chưa khai trong "
                     "_SESSION_WF_ACTION_LABELS — cập nhật + kiểm cạnh mới"),
            )

        # Cạnh distinct (role-expanded → set gom): workflow vs SSoT map.
        workflow_pairs = {(t["state"], t["next_state"]) for t in wf["transitions"]}
        map_pairs = {
            (state, nxt)
            for state, nexts in _SESSION_VALID_TRANSITIONS.items()
            for nxt in nexts
        }

        divergent = workflow_pairs.symmetric_difference(map_pairs)
        self.assertEqual(
            divergent, _SESSION_EXCEPTION_EDGES,
            msg=(f"map ⇄ workflow divergent {sorted(divergent)} != EXCEPTION_EDGES "
                 f"{sorted(_SESSION_EXCEPTION_EDGES)} — cạnh lạ = drift SSoT↔workflow"),
        )

        # Grounding 2-chiều tường minh (0 orphan): map ⊆ workflow ∧ workflow ⊆ map.
        self.assertEqual(
            map_pairs - workflow_pairs, set(),
            msg=f"Cạnh map MỒ CÔI (∉ workflow): {sorted(map_pairs - workflow_pairs)}",
        )
        self.assertEqual(
            workflow_pairs - map_pairs, set(),
            msg=(f"Cạnh workflow KHÔNG surface thành CTA trong map: "
                 f"{sorted(workflow_pairs - map_pairs)}"),
        )

        # EXCEPTION_EDGES tường minh rỗng (tương phản competency 4 cạnh) + chốt 8 cạnh.
        self.assertEqual(_SESSION_EXCEPTION_EDGES, frozenset())
        self.assertEqual(len(workflow_pairs), 8, "workflow phải có đúng 8 cạnh distinct")
        self.assertEqual(len(map_pairs), 8, "map phải có đúng 8 cạnh")


class TestCompleteTrainingSessionBR0608(unittest.TestCase):
    """BR-06-08 (VR-13/VR-14) — chặn nghiệm-thu-giả buổi đào tạo trong
    `complete_training_session`. Guard-before-persist (docs/imm-06/05 §B.5):
      (a) result trỏ user KHÔNG thuộc buổi → VALIDATION strict fail-loud (BA chốt),
          KHÔNG drop câm, KHÔNG đổi state.
      (b) scored_count == 0 (gồm results=[]) → VALIDATION message FROZEN, DB giữ
          `In Progress` (chống chuyển-trạng-thái-rồi-mới-fail).
      return.scored_count = số participant THỰC set overall_result (đếm trong loop,
      KHÔNG len(results)); competencies_created = tên IMM User Competency THỰC persist.
    Session dựng qua flow THẬT: create → enroll → confirm → start.
    """

    _FROZEN_NO_SCORE = ("Phải chấm điểm ít nhất 1 học viên trước khi hoàn thành "
                        "buổi học (BR-06-08)")

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        for r in ("AssetCore Super Admin", "Training Manager"):
            if not frappe.db.exists("Role", r):
                frappe.get_doc({"doctype": "Role", "role_name": r}
                               ).insert(ignore_permissions=True)
        frappe.get_doc("User", "Administrator").add_roles(
            "AssetCore Super Admin", "Training Manager")
        cls.prog = _make_program()
        cls.trainee2 = cls._ensure_user("_test-trainee2-imm06@assetcore.test")
        cls._sessions: list[str] = []
        cls._comps: list[str] = []

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for name in cls._comps:
            if frappe.db.exists("IMM User Competency", name):
                frappe.db.delete("IMM User Competency", {"name": name})
                frappe.db.delete("IMM Audit Trail",
                                 {"ref_doctype": "IMM User Competency", "ref_name": name})
        for name in cls._sessions:
            if frappe.db.exists("IMM Training Session", name):
                frappe.delete_doc("IMM Training Session", name,
                                  force=True, ignore_permissions=True)
        if frappe.db.exists("IMM Training Program", cls.prog):
            frappe.delete_doc("IMM Training Program", cls.prog,
                              force=True, ignore_permissions=True)
        frappe.db.commit()

    @staticmethod
    def _ensure_user(email: str) -> str:
        if not frappe.db.exists("User", email):
            u = frappe.get_doc({
                "doctype": "User", "email": email,
                "first_name": "Trainee2 IMM06", "send_welcome_email": 0,
                "enabled": 1,
            })
            u.flags.ignore_permissions = True
            u.insert(ignore_permissions=True)
            frappe.db.commit()
        return email

    def _inprogress_session(self, enroll: list[dict]) -> str:
        """Dựng buổi In Progress qua flow THẬT (create→enroll→confirm→start)."""
        res = create_training_session({
            "training_program": self.prog,
            "session_date": nowdate(),
            "session_type": "Onsite",
            "duration_planned_hours": 4,
            "instructor": "Administrator",
        })
        name = res["name"]
        type(self)._sessions.append(name)
        enroll_participants(name, enroll)
        confirm_session(name)
        start_training_session(name)
        self.assertEqual(
            frappe.db.get_value("IMM Training Session", name, "workflow_state"),
            SessionStatus.IN_PROGRESS)
        return name

    # ── RED (b/VR-13): empty-scoring reject + DB giữ In Progress ──────────────
    def test_complete_empty_results_rejected(self):
        name = self._inprogress_session(
            [{"user": "Administrator", "role_at_session": "Operator"}])
        with self.assertRaises(ServiceError) as ctx:
            complete_training_session(name, [])
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
        self.assertEqual(ctx.exception.message, self._FROZEN_NO_SCORE)
        # DB PHẢI giữ In Progress — guard TRƯỚC persist.
        self.assertEqual(
            frappe.db.get_value("IMM Training Session", name, "workflow_state"),
            SessionStatus.IN_PROGRESS)

    # ── RED (a/VR-14): unmatched user strict fail-loud ───────────────────────
    def test_complete_unknown_user_strict_raises(self):
        name = self._inprogress_session(
            [{"user": "Administrator", "role_at_session": "Operator"}])
        stranger = "nguoi-la-khong-ghi-danh@benhvien.vn"
        with self.assertRaises(ServiceError) as ctx:
            complete_training_session(name, [
                {"user": stranger, "theory_score": 80, "practical_score": 80}])
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
        self.assertIn(stranger, ctx.exception.message)
        self.assertIn("không thuộc buổi", ctx.exception.message)
        self.assertEqual(
            frappe.db.get_value("IMM Training Session", name, "workflow_state"),
            SessionStatus.IN_PROGRESS)

    # ── GREEN: 1 participant Pass → scored_count=1 + 1 competency THỰC persist ─
    def test_complete_scored_count_real_and_competency_persists(self):
        name = self._inprogress_session(
            [{"user": "Administrator", "role_at_session": "Operator"}])
        res = complete_training_session(name, [
            {"user": "Administrator", "theory_score": 85, "practical_score": 80}])
        type(self)._comps.extend(res.get("competencies_created", []))
        self.assertEqual(res["scored_count"], 1)
        self.assertEqual(len(res["competencies_created"]), 1)
        self.assertTrue(frappe.db.exists(
            "IMM User Competency", res["competencies_created"][0]))
        self.assertEqual(
            frappe.db.get_value("IMM Training Session", name, "workflow_state"),
            SessionStatus.COMPLETED)
        row = frappe.db.get_value(
            "IMM Training Participant",
            {"parent": name, "user": "Administrator"},
            "overall_result")
        self.assertEqual(row, "Pass")

    # ── GREEN/pin-BA: 2 participant chấm 1 → partial cho phép, scored_count THỰC ─
    def test_complete_partial_scoring_counts_real(self):
        name = self._inprogress_session([
            {"user": "Administrator", "role_at_session": "Operator"},
            {"user": self.trainee2, "role_at_session": "Operator"},
        ])
        # Chỉ chấm trainee2 (Fail 40<70) — Administrator để trống.
        res = complete_training_session(name, [
            {"user": self.trainee2, "theory_score": 40, "practical_score": 40}])
        type(self)._comps.extend(res.get("competencies_created", []))
        # scored_count đếm THỰC (1), KHÔNG len(results) (cũng 1 ở đây nhưng
        # participant còn lại KHÔNG được set) — cốt là honest count trong loop.
        self.assertEqual(res["scored_count"], 1)
        self.assertEqual(len(res["competencies_created"]), 0)  # Fail → 0 competency
        admin_result = frappe.db.get_value(
            "IMM Training Participant",
            {"parent": name, "user": "Administrator"}, "overall_result")
        self.assertIn(admin_result, (None, ""))  # partial cho phép: chưa chấm → rỗng
        t2_result = frappe.db.get_value(
            "IMM Training Participant",
            {"parent": name, "user": self.trainee2}, "overall_result")
        self.assertEqual(t2_result, "Fail")


class TestCompetencyAllowedTransitions(unittest.TestCase):
    """IMM-06 Năng lực — get_competency emit `allowed_transitions` khớp EXACT SSoT
    `_COMPETENCY_VALID_TRANSITIONS`, và 3 service transition (signoff/revoke/recertify)
    đọc guard từ CHUNG map (map↔guard KHÔNG drift). Đối xứng TestSessionAllowedTransitions.
    GATE-8 / LL-FE-51 — AC1 + AC4.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        for r in ("AssetCore Super Admin", "Training Manager"):
            if not frappe.db.exists("Role", r):
                frappe.get_doc({"doctype": "Role", "role_name": r}
                               ).insert(ignore_permissions=True)
        frappe.get_doc("User", "Administrator").add_roles(
            "AssetCore Super Admin", "Training Manager")
        cls._comps: list[str] = []

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for name in cls._comps:
            if frappe.db.exists("IMM User Competency", name):
                frappe.db.delete("IMM User Competency", {"name": name})
                frappe.db.delete("IMM Audit Trail",
                                 {"ref_doctype": "IMM User Competency", "ref_name": name})
        frappe.db.commit()

    def _comp(self, state: str) -> str:
        name = _make_competency("Administrator", "", state=state)
        type(self)._comps.append(name)
        return name

    # ── AC1: allowed_transitions khớp EXACT SSoT theo từng state ──────────────

    def test_get_competency_allowed_transitions_by_state(self):
        cases = {
            CompetencyStatus.PENDING:   [COMPETENCY_SIGNOFF],
            CompetencyStatus.ACTIVE:    [COMPETENCY_SUSPEND, COMPETENCY_REVOKE],
            CompetencyStatus.EXPIRING:  [COMPETENCY_RECERTIFY, COMPETENCY_REVOKE],
            CompetencyStatus.EXPIRED:   [COMPETENCY_RECERTIFY, COMPETENCY_REVOKE],
            CompetencyStatus.SUSPENDED: [COMPETENCY_RESTORE, COMPETENCY_REVOKE],
            CompetencyStatus.REVOKED:   [],
        }
        for state, expected in cases.items():
            name = self._comp(state)
            got = get_competency(name)["allowed_transitions"]
            self.assertEqual(
                got, expected,
                msg=f"allowed_transitions sai cho state={state}: {got} != {expected}",
            )

    def test_get_competency_terminal_revoked_empty(self):
        name = self._comp(CompetencyStatus.REVOKED)
        self.assertEqual(get_competency(name)["allowed_transitions"], [])

    # ── AC3: Super Admin (training.submit) → cờ can_* non-empty ở state hợp lệ ──

    def test_superadmin_can_flags_non_empty(self):
        # Administrator có Super Admin + Training Manager (training.submit) → cờ True.
        name = self._comp(CompetencyStatus.EXPIRING)
        data = get_competency(name)
        self.assertTrue(data["can_recertify"], "Super Admin phải can_recertify ở Expiring")
        self.assertTrue(data["can_revoke"], "Super Admin phải can_revoke ở Expiring")
        self.assertFalse(data["can_signoff"], "Sign-off KHÔNG khả dụng ở Expiring")

    # ── AC4: invariant map↔guard — chống desync SoT↔enforce (bidirectional) ────

    def test_competency_allowed_transitions_parity_invariant(self):
        all_states = list(_COMPETENCY_VALID_TRANSITIONS.keys())
        # invoke(name) — mỗi action, isolate STATE guard:
        #   • Sign-off  : signoff_competency(name, admin) — guard PENDING.
        #   • Revoke    : revoke_competency(name, reason) — guard {Active,Expiring,Expired,Suspended}.
        #   • Recertify : recertify_competency(name, "__NO_SESSION__") — guard {Expiring,Expired}
        #       chạy TRƯỚC session lookup → state hợp lệ ⇒ NOT_FOUND (≠ BAD_STATE);
        #       state sai ⇒ BAD_STATE (guard state chặn trước).
        specs = [
            (COMPETENCY_SIGNOFF, lambda n: signoff_competency(n, "Administrator")),
            (COMPETENCY_SUSPEND, lambda n: suspend_competency(n, "Lý do tạm ngưng hợp lệ")),
            (COMPETENCY_RESTORE, lambda n: restore_competency(n)),
            (COMPETENCY_REVOKE, lambda n: revoke_competency(n, "Lý do thu hồi hợp lệ")),
            (COMPETENCY_RECERTIFY, lambda n: recertify_competency(n, "__NO_SESSION__")),
        ]
        for action, invoke in specs:
            sources = _competency_states_allowing(action)
            self.assertTrue(sources, msg=f"{action} phải có ≥1 state nguồn trong map")
            # Forward: từ MỖI state nguồn hợp lệ → service KHÔNG raise BAD_STATE.
            for s in sources:
                name = self._comp(s)
                try:
                    invoke(name)
                except ServiceError as e:
                    self.assertNotEqual(
                        e.code, ErrorCode.BAD_STATE,
                        msg=f"{action}: nguồn hợp lệ {s} KHÔNG được raise BAD_STATE",
                    )
            # Reverse: từ state NGOÀI tập nguồn → service PHẢI raise BAD_STATE.
            for s in [x for x in all_states if x not in sources]:
                name = self._comp(s)
                with self.assertRaises(ServiceError) as ctx:
                    invoke(name)
                self.assertEqual(
                    ctx.exception.code, ErrorCode.BAD_STATE,
                    msg=f"{action}: state ngoài map {s} PHẢI raise BAD_STATE",
                )

    def test_competency_transitions_no_jump_skip(self):
        # signoff CHỈ từ Pending; recertify CHỈ từ Expiring/Expired; revoke KHÔNG từ Revoked.
        active = self._comp(CompetencyStatus.ACTIVE)
        with self.assertRaises(ServiceError) as c1:
            signoff_competency(active, "Administrator")   # Active → signoff error
        self.assertEqual(c1.exception.code, ErrorCode.BAD_STATE)

        active2 = self._comp(CompetencyStatus.ACTIVE)
        with self.assertRaises(ServiceError) as c2:
            recertify_competency(active2, "__NO_SESSION__")  # Active → recertify error
        self.assertEqual(c2.exception.code, ErrorCode.BAD_STATE)

        revoked = self._comp(CompetencyStatus.REVOKED)
        with self.assertRaises(ServiceError) as c3:
            revoke_competency(revoked, "Lý do")            # Revoked → revoke error
        self.assertEqual(c3.exception.code, ErrorCode.BAD_STATE)

    # ── AC6: mỗi CTA sinh audit trail (NĐ98) ──────────────────────────────────

    def test_competency_cta_emits_audit(self):
        name = self._comp(CompetencyStatus.PENDING)
        signoff_competency(name, "Administrator")
        self.assertTrue(
            frappe.db.exists("IMM Audit Trail", {
                "ref_doctype": "IMM User Competency", "ref_name": name,
                "event_type": "competency_signoff",
            }),
            "signoff phải sinh audit competency_signoff",
        )
        # từ Active → revoke → audit competency_revoked
        revoke_competency(name, "Lý do thu hồi hợp lệ")
        self.assertTrue(
            frappe.db.exists("IMM Audit Trail", {
                "ref_doctype": "IMM User Competency", "ref_name": name,
                "event_type": "competency_revoked",
            }),
            "revoke phải sinh audit competency_revoked",
        )

    # ── CR-WF-06-COMP: cờ can_suspend/can_restore (parity can_revoke) ──────────

    def test_superadmin_can_suspend_at_active(self):
        # Active → allowed chứa 'Suspend' + can_suspend True (Administrator đủ quyền);
        # KHÔNG can_restore (Restore không hợp lệ ở Active).
        name = self._comp(CompetencyStatus.ACTIVE)
        data = get_competency(name)
        self.assertIn(COMPETENCY_SUSPEND, data["allowed_transitions"])
        self.assertTrue(data["can_suspend"], "Super Admin phải can_suspend ở Active")
        self.assertFalse(data["can_restore"], "Restore KHÔNG khả dụng ở Active")

    def test_superadmin_can_restore_at_suspended(self):
        # Suspended → allowed == ['Restore','Revoke'] (thứ tự ổn định) + can_restore True.
        name = self._comp(CompetencyStatus.SUSPENDED)
        data = get_competency(name)
        self.assertEqual(data["allowed_transitions"], [COMPETENCY_RESTORE, COMPETENCY_REVOKE])
        self.assertTrue(data["can_restore"], "Super Admin phải can_restore ở Suspended")
        self.assertFalse(data["can_suspend"], "Suspend KHÔNG khả dụng ở Suspended")

    # ── CR-WF-06-COMP: reconcile map ⇄ workflow JSON (EXCEPTION_EDGES tường minh) ─

    def test_competency_allowed_transitions_matches_workflow(self):
        """SSoT `_COMPETENCY_VALID_TRANSITIONS` (action-label) reconcile ⇄ file workflow
        `imm_06_competency_workflow.json`. Symmetric-difference (state, action) giữa 2
        nguồn PHẢI == EXCEPTION_EDGES khai tường minh — mọi cạnh khác divergent = drift.

        EXCEPTION_EDGES (4):
          • (Active, MarkExpiring)  — scheduler-auto (Active→Expiring, không CTA)
          • (Active, Expire)        — scheduler-auto (Active→Expired, không CTA)
          • (Expiring, Expire)      — scheduler-auto (Expiring→Expired, không CTA)
          • (Expiring, Recertify)   — create-new (service cho recertify từ Expiring nhưng
                                       workflow chỉ wire Expired→Active; recertify sinh
                                       competency MỚI ở Pending + đánh dấu cũ Expired)
        RED-before demo: gỡ Suspend/Restore khỏi map → (Active,Suspend)/(Suspended,Restore)
        rơi khỏi map_pairs nhưng còn trong workflow → symmetric-diff ≠ EXCEPTION_EDGES → đỏ.
        """
        # VN action-label workflow → canonical action (service vocab / scheduler token).
        wf_action_to_canon = {
            "Sign-off": COMPETENCY_SIGNOFF,
            "Tạm ngưng": COMPETENCY_SUSPEND,
            "Khôi phục": COMPETENCY_RESTORE,
            "Thu hồi": COMPETENCY_REVOKE,
            "Tái chứng nhận": COMPETENCY_RECERTIFY,
            "Đánh dấu sắp hết hạn": "MarkExpiring",  # scheduler-auto (no service CTA)
            "Hết hạn": "Expire",                      # scheduler-auto (no service CTA)
        }
        path = frappe.get_app_path(
            "assetcore", "assetcore", "workflow", "imm_06_competency_workflow.json")
        with open(path, encoding="utf-8") as fh:
            wf = json.load(fh)

        # Mọi action-label workflow PHẢI khai trong bảng dịch (anti-drift: label lạ → KeyError).
        for t in wf["transitions"]:
            self.assertIn(
                t["action"], wf_action_to_canon,
                msg=f"Action-label workflow '{t['action']}' chưa khai trong bảng reconcile",
            )
        workflow_pairs = {
            (t["state"], wf_action_to_canon[t["action"]]) for t in wf["transitions"]
        }
        map_pairs = {
            (state, action)
            for state, actions in _COMPETENCY_VALID_TRANSITIONS.items()
            for action in actions
        }
        exception_edges = {
            (CompetencyStatus.ACTIVE, "MarkExpiring"),
            (CompetencyStatus.ACTIVE, "Expire"),
            (CompetencyStatus.EXPIRING, "Expire"),
            (CompetencyStatus.EXPIRING, COMPETENCY_RECERTIFY),
        }
        divergent = workflow_pairs.symmetric_difference(map_pairs)
        self.assertEqual(
            divergent, exception_edges,
            msg=(f"map ⇄ workflow divergent {divergent} != EXCEPTION_EDGES "
                 f"{exception_edges} — cạnh lạ = drift SSoT↔workflow (Suspend/Restore "
                 "phải KHỚP workflow, không còn divergent)"),
        )
        # Sau fix: cạnh Suspend/Restore KHÔNG nằm trong divergent (đã khớp 2-chiều).
        self.assertNotIn((CompetencyStatus.ACTIVE, COMPETENCY_SUSPEND), divergent)
        self.assertNotIn((CompetencyStatus.SUSPENDED, COMPETENCY_RESTORE), divergent)

    def test_competency_audit_event_types_registered_in_select(self):
        """Chống silent-audit-loss (R12 imm15): mọi event_type competency service emit
        PHẢI ∈ Select `IMM Audit Trail.event_type`. Thiếu → log_audit_event nuốt câm →
        mất bản ghi NĐ98. Guard emitted ⊆ Select.
        """
        meta = frappe.get_meta("IMM Audit Trail")
        opts = set((meta.get_field("event_type").options or "").split("\n"))
        emitted = {
            "competency_signoff", "competency_revoked", "competency_recertified",
            "competency_suspended", "competency_restored",
        }
        missing = emitted - opts
        self.assertEqual(
            missing, set(),
            msg=f"event_type competency thiếu trong Select IMM Audit Trail: {missing}",
        )


class TestCompetencySuspendRestore(unittest.TestCase):
    """CR-WF-06-COMP — suspend_competency (Active→Suspended) + restore_competency
    (Suspended→Active): state guard qua SSoT, reason bắt buộc, audit SUSPENDED/RESTORED
    + lifecycle competency_suspended/competency_restored, BAD_STATE nguồn sai.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        for r in ("AssetCore Super Admin", "Training Manager"):
            if not frappe.db.exists("Role", r):
                frappe.get_doc({"doctype": "Role", "role_name": r}
                               ).insert(ignore_permissions=True)
        frappe.get_doc("User", "Administrator").add_roles(
            "AssetCore Super Admin", "Training Manager")
        cls._comps: list[str] = []

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for name in cls._comps:
            if frappe.db.exists("IMM User Competency", name):
                frappe.db.delete("IMM User Competency", {"name": name})
                frappe.db.delete("IMM Audit Trail",
                                 {"ref_doctype": "IMM User Competency", "ref_name": name})
        frappe.db.commit()

    def _comp(self, state: str) -> str:
        name = _make_competency("Administrator", "", state=state)
        type(self)._comps.append(name)
        return name

    def _audit_exists(self, name: str, event_type: str) -> bool:
        return bool(frappe.db.exists("IMM Audit Trail", {
            "ref_doctype": "IMM User Competency", "ref_name": name,
            "event_type": event_type,
        }))

    # ── AC-SUSPEND ────────────────────────────────────────────────────────────

    def test_suspend_active_to_suspended_with_audit_and_lifecycle(self):
        name = self._comp(CompetencyStatus.ACTIVE)
        res = suspend_competency(name, "Tạm ngưng do vi phạm quy trình vận hành")
        self.assertEqual(res["workflow_state"], CompetencyStatus.SUSPENDED)
        self.assertEqual(
            frappe.db.get_value("IMM User Competency", name, "workflow_state"),
            CompetencyStatus.SUSPENDED,
        )
        # audit action 'SUSPENDED' + lifecycle event_type competency_suspended (1 bản ghi).
        self.assertTrue(self._audit_exists(name, "competency_suspended"),
                        "suspend phải sinh audit/lifecycle competency_suspended")

    def test_suspend_empty_reason_raises_validation(self):
        name = self._comp(CompetencyStatus.ACTIVE)
        for bad in ("", "   "):
            with self.assertRaises(ServiceError) as ctx:
                suspend_competency(name, bad)
            self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
        # State KHÔNG đổi khi reason rỗng.
        self.assertEqual(
            frappe.db.get_value("IMM User Competency", name, "workflow_state"),
            CompetencyStatus.ACTIVE,
        )

    def test_suspend_from_non_active_bad_state(self):
        for state in (CompetencyStatus.PENDING, CompetencyStatus.EXPIRING,
                      CompetencyStatus.EXPIRED, CompetencyStatus.REVOKED,
                      CompetencyStatus.SUSPENDED):
            name = self._comp(state)
            with self.assertRaises(ServiceError) as ctx:
                suspend_competency(name, "Lý do bất kỳ")
            self.assertEqual(
                ctx.exception.code, ErrorCode.BAD_STATE,
                msg=f"suspend từ {state} PHẢI BAD_STATE",
            )
            # state bất biến.
            self.assertEqual(
                frappe.db.get_value("IMM User Competency", name, "workflow_state"), state)

    # ── AC-RESTORE ────────────────────────────────────────────────────────────

    def test_restore_suspended_to_active_with_audit_and_lifecycle(self):
        name = self._comp(CompetencyStatus.SUSPENDED)
        res = restore_competency(name)
        self.assertEqual(res["workflow_state"], CompetencyStatus.ACTIVE)
        self.assertEqual(
            frappe.db.get_value("IMM User Competency", name, "workflow_state"),
            CompetencyStatus.ACTIVE,
        )
        self.assertTrue(self._audit_exists(name, "competency_restored"),
                        "restore phải sinh audit/lifecycle competency_restored")

    def test_restore_from_non_suspended_bad_state(self):
        for state in (CompetencyStatus.PENDING, CompetencyStatus.ACTIVE,
                      CompetencyStatus.EXPIRING, CompetencyStatus.EXPIRED,
                      CompetencyStatus.REVOKED):
            name = self._comp(state)
            with self.assertRaises(ServiceError) as ctx:
                restore_competency(name)
            self.assertEqual(
                ctx.exception.code, ErrorCode.BAD_STATE,
                msg=f"restore từ {state} PHẢI BAD_STATE",
            )
            self.assertEqual(
                frappe.db.get_value("IMM User Competency", name, "workflow_state"), state)

    def test_suspend_then_restore_roundtrip(self):
        name = self._comp(CompetencyStatus.ACTIVE)
        suspend_competency(name, "Tạm ngưng để rà soát năng lực")
        self.assertEqual(
            frappe.db.get_value("IMM User Competency", name, "workflow_state"),
            CompetencyStatus.SUSPENDED)
        restore_competency(name)
        self.assertEqual(
            frappe.db.get_value("IMM User Competency", name, "workflow_state"),
            CompetencyStatus.ACTIVE)
        self.assertTrue(self._audit_exists(name, "competency_suspended"))
        self.assertTrue(self._audit_exists(name, "competency_restored"))


class TestCompetencyRbacGate(unittest.TestCase):
    """VÁ lỗ RBAC (AC2/AC3): api.revoke_competency + api.recertify_competency REJECT
    caller thiếu capability `training.submit` với FORBIDDEN + KHÔNG đổi workflow_state
    (parity signoff_competency). Super Admin / Training Manager → thành công.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        for r in ("AssetCore Super Admin", "Training Manager"):
            if not frappe.db.exists("Role", r):
                frappe.get_doc({"doctype": "Role", "role_name": r}
                               ).insert(ignore_permissions=True)
        frappe.get_doc("User", "Administrator").add_roles(
            "AssetCore Super Admin", "Training Manager")
        # User thiếu quyền: chỉ base role, KHÔNG training.submit (không delete IMM Training Session).
        cls.plain_user = f"_test_imm06_rbac_{frappe.generate_hash()[:8]}@test.local"
        if not frappe.db.exists("User", cls.plain_user):
            frappe.get_doc({
                "doctype": "User", "email": cls.plain_user,
                "first_name": "PlainRBAC", "enabled": 1,
                "user_type": "System User", "send_welcome_email": 0,
                "roles": [{"role": "AssetCore System User"}]
                if frappe.db.exists("Role", "AssetCore System User") else [],
            }).insert(ignore_permissions=True)
        cls._comps: list[str] = []
        cls._sessions: list[str] = []

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for name in cls._comps:
            if frappe.db.exists("IMM User Competency", name):
                frappe.db.delete("IMM User Competency", {"name": name})
                frappe.db.delete("IMM Audit Trail",
                                 {"ref_doctype": "IMM User Competency", "ref_name": name})
        for name in cls._sessions:
            if frappe.db.exists("IMM Training Session", name):
                frappe.delete_doc("IMM Training Session", name,
                                  force=True, ignore_permissions=True)
        if frappe.db.exists("User", cls.plain_user):
            frappe.delete_doc("User", cls.plain_user, force=True, ignore_permissions=True)
        frappe.db.commit()

    def _comp(self, state: str) -> str:
        frappe.set_user("Administrator")
        name = _make_competency("Administrator", "", state=state)
        type(self)._comps.append(name)
        return name

    def _completed_session_pass(self, user: str) -> str:
        """Buổi đào tạo Completed có ``user`` đạt (Pass) — dùng cho recertify success."""
        program = _ensure_test_program()
        sess = frappe.get_doc({
            "doctype": "IMM Training Session",
            "training_program": program,
            "session_date": nowdate(),
            "session_type": "Onsite",
            "duration_planned_hours": 4,
            "instructor": "Administrator",
        })
        sess.append("participants", {
            "user": user, "role_at_session": "Operator",
            "overall_result": "Pass", "theory_score": 85, "practical_score": 88,
        })
        sess.flags.ignore_links = True
        sess.flags.ignore_mandatory = True
        sess.insert(ignore_permissions=True)
        frappe.db.set_value("IMM Training Session", sess.name,
                            "workflow_state", SessionStatus.COMPLETED)
        frappe.db.commit()
        type(self)._sessions.append(sess.name)
        return sess.name

    def test_revoke_competency_forbidden_without_capability(self):
        name = self._comp(CompetencyStatus.ACTIVE)
        frappe.set_user(self.plain_user)
        try:
            res = api06.revoke_competency(name, "Lý do bất kỳ")
        finally:
            frappe.set_user("Administrator")
        self.assertFalse(res["success"], "revoke phải bị chặn")
        self.assertEqual(res["code"], ErrorCode.FORBIDDEN)
        # workflow_state KHÔNG đổi (assert DB).
        self.assertEqual(
            frappe.db.get_value("IMM User Competency", name, "workflow_state"),
            CompetencyStatus.ACTIVE,
        )

    def test_recertify_competency_forbidden_without_capability(self):
        name = self._comp(CompetencyStatus.EXPIRED)
        frappe.set_user(self.plain_user)
        try:
            res = api06.recertify_competency(name, "__NO_SESSION__")
        finally:
            frappe.set_user("Administrator")
        self.assertFalse(res["success"], "recertify phải bị chặn")
        self.assertEqual(res["code"], ErrorCode.FORBIDDEN)
        self.assertEqual(
            frappe.db.get_value("IMM User Competency", name, "workflow_state"),
            CompetencyStatus.EXPIRED,
        )

    def test_superadmin_can_signoff_and_revoke(self):
        # Administrator (Super Admin + Training Manager) → get_competency emit non-empty +
        # api.signoff/revoke thành công đổi đúng state.
        frappe.set_user("Administrator")
        name = self._comp(CompetencyStatus.PENDING)
        self.assertIn(COMPETENCY_SIGNOFF, get_competency(name)["allowed_transitions"])
        r1 = api06.signoff_competency(name)
        self.assertTrue(r1["success"], f"signoff phải thành công: {r1}")
        self.assertEqual(
            frappe.db.get_value("IMM User Competency", name, "workflow_state"),
            CompetencyStatus.ACTIVE,
        )
        r2 = api06.revoke_competency(name, "Lý do thu hồi hợp lệ")
        self.assertTrue(r2["success"], f"revoke phải thành công: {r2}")
        self.assertEqual(
            frappe.db.get_value("IMM User Competency", name, "workflow_state"),
            CompetencyStatus.REVOKED,
        )

    def test_superadmin_can_recertify(self):
        # old Expired + buổi Completed (user Pass) → api.recertify thành công: old→Expired,
        # sinh competency mới (Pending). Xác minh chiều ngược root-cause (AC3).
        frappe.set_user("Administrator")
        name = self._comp(CompetencyStatus.EXPIRED)
        self.assertIn(COMPETENCY_RECERTIFY, get_competency(name)["allowed_transitions"])
        session = self._completed_session_pass("Administrator")
        res = api06.recertify_competency(name, session)
        self.assertTrue(res["success"], f"recertify phải thành công: {res}")
        new_comp = res["data"]["new_competency"]
        type(self)._comps.append(new_comp)
        self.assertTrue(frappe.db.exists("IMM User Competency", new_comp))
        self.assertEqual(
            frappe.db.get_value("IMM User Competency", name, "workflow_state"),
            CompetencyStatus.EXPIRED,
        )

    # ── CR-WF-06-COMP: RBAC gate suspend/restore (parity revoke) ──────────────

    def test_suspend_competency_forbidden_without_capability(self):
        name = self._comp(CompetencyStatus.ACTIVE)
        frappe.set_user(self.plain_user)
        try:
            res = api06.suspend_competency(name, "Lý do bất kỳ")
        finally:
            frappe.set_user("Administrator")
        self.assertFalse(res["success"], "suspend phải bị chặn")
        self.assertEqual(res["code"], ErrorCode.FORBIDDEN)
        # workflow_state KHÔNG đổi (assert DB) — thiếu quyền KHÔNG chạm state.
        self.assertEqual(
            frappe.db.get_value("IMM User Competency", name, "workflow_state"),
            CompetencyStatus.ACTIVE,
        )

    def test_restore_competency_forbidden_without_capability(self):
        name = self._comp(CompetencyStatus.SUSPENDED)
        frappe.set_user(self.plain_user)
        try:
            res = api06.restore_competency(name)
        finally:
            frappe.set_user("Administrator")
        self.assertFalse(res["success"], "restore phải bị chặn")
        self.assertEqual(res["code"], ErrorCode.FORBIDDEN)
        self.assertEqual(
            frappe.db.get_value("IMM User Competency", name, "workflow_state"),
            CompetencyStatus.SUSPENDED,
        )

    def test_superadmin_can_suspend_and_restore(self):
        # Administrator (Super Admin + Training Manager, capability training.submit) →
        # api.suspend + api.restore thành công đổi đúng state (parity revoke).
        frappe.set_user("Administrator")
        name = self._comp(CompetencyStatus.ACTIVE)
        self.assertIn(COMPETENCY_SUSPEND, get_competency(name)["allowed_transitions"])
        r1 = api06.suspend_competency(name, "Tạm ngưng để rà soát")
        self.assertTrue(r1["success"], f"suspend phải thành công: {r1}")
        self.assertEqual(
            frappe.db.get_value("IMM User Competency", name, "workflow_state"),
            CompetencyStatus.SUSPENDED,
        )
        self.assertIn(COMPETENCY_RESTORE, get_competency(name)["allowed_transitions"])
        r2 = api06.restore_competency(name)
        self.assertTrue(r2["success"], f"restore phải thành công: {r2}")
        self.assertEqual(
            frappe.db.get_value("IMM User Competency", name, "workflow_state"),
            CompetencyStatus.ACTIVE,
        )


if __name__ == "__main__":
    unittest.main()
