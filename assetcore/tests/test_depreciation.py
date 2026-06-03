# Copyright (c) 2026, AssetCore Team
"""IMM-05 depreciation EXECUTOR invariants — run_due_depreciation floor/cap.

TDD (CLAUDE.md §17) for the root-cause fix:
  INVARIANT-1: after run_due_depreciation, current_book_value NEVER < residual_value
               (was floored at 0.0 → asset depreciated through residual down to 0,
               sai NĐ98 / chuẩn kế toán VN).
  INVARIANT-2: accumulated_depreciation NEVER exceeds depreciable_base = gross - residual
               (lagging cron batching multiple periods + last-period rounding).
  CONSISTENCY: header current_book_value == last Executed schedule row remaining_value.
  IDEMPOTENT: a second run with no due Pending rows → executed_rows=0, no double-count.

Run:
  bench --site miyano run-tests --app assetcore \
      --module assetcore.tests.test_depreciation
"""
from __future__ import annotations

import unittest

import frappe
from frappe.utils import flt

from assetcore.services import depreciation as depr_svc
from assetcore.tests._asset_cleanup import purge_asset

_DT_ASSET = "AC Asset"
_DT_SCHED = "AC Asset Depreciation Schedule"

# Far-future cutoff so a single run executes EVERY scheduled period at once
# (also exercises the lagging-cron multi-period batch path).
_FAR_FUTURE = "2099-12-31"

# Asset under test: gross=100tr, residual=10tr, depreciable_base=90tr.
_GROSS = 100_000_000.0
_RESIDUAL = 10_000_000.0
_DEPRECIABLE_BASE = _GROSS - _RESIDUAL  # 90tr


def _ensure_uom() -> None:
    if not frappe.db.exists("AC UOM", "Cái"):
        frappe.get_doc({"doctype": "AC UOM", "uom_name": "Cái"}).insert(
            ignore_permissions=True
        )


def _make_asset(
    *,
    suffix: str,
    gross: float = _GROSS,
    residual: float = _RESIDUAL,
    months: int = 12,
    frequency: str = "Monthly",
    method: str = "Straight Line",
    lifecycle: str = "Active",
) -> str:
    """Insert an AC Asset with depreciation rules, bypassing workflow/mandatory.

    ``lifecycle_status`` is a workflow_state field; inserting straight to a
    non-Draft state is blocked by validate_workflow. Setting
    ``frappe.flags.in_install`` skips that validation (same pattern as
    ``test_imm00._insert_asset_bypass_workflow``).
    """
    _ensure_uom()
    doc = frappe.get_doc({
        "doctype": _DT_ASSET,
        "asset_name": f"_Test Depr {suffix}",
        "gross_purchase_amount": gross,
        "residual_value": residual,
        "depreciation_method": method,
        "total_depreciation_months": months,
        "depreciation_frequency": frequency,
        "depreciation_start_date": "2024-01-01",
        "in_service_date": "2024-01-01",
        "lifecycle_status": lifecycle,
    })
    doc.flags.ignore_mandatory = True
    doc.flags.ignore_links = True
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    try:
        doc.insert(ignore_permissions=True)
    finally:
        frappe.flags.in_install = prev
    return doc.name


def _book(asset: str) -> float:
    return flt(frappe.db.get_value(_DT_ASSET, asset, "current_book_value"))


def _acc(asset: str) -> float:
    return flt(frappe.db.get_value(_DT_ASSET, asset, "accumulated_depreciation"))


def _seed_accumulated(asset: str, amount: float) -> None:
    """Pre-set accumulated_depreciation to simulate drift / partial history.

    Without drift, straight-line schedule amounts already sum exactly to
    depreciable_base, so the floor/cap never trigger and a buggy
    floor-at-0.0 executor produces an identical result. Seeding a non-zero
    starting accumulated forces prev_acc + Σschedule > depreciable_base, which
    is precisely the condition INVARIANT-1/2 protect against — and the only
    way these RED tests can distinguish the fixed formula from the bug.
    """
    frappe.db.set_value(_DT_ASSET, asset, "accumulated_depreciation", amount,
                        update_modified=False)


class TestDepreciationExecutorInvariants(unittest.TestCase):
    """Service-layer tests for run_due_depreciation floor-at-residual + cap."""

    def setUp(self) -> None:
        self._assets: list[str] = []

    def tearDown(self) -> None:
        for a in self._assets:
            try:
                purge_asset(a)
            except Exception:
                pass
        frappe.db.commit()

    def _new(self, **kw) -> str:
        name = _make_asset(**kw)
        self._assets.append(name)
        depr_svc.generate_schedule(name, force=True)
        return name

    # ── INVARIANT-1 (root cause) ──────────────────────────────────────────────

    def test_run_due_depreciation_floors_book_value_at_residual(self):
        """[TDD-RED] gross=100tr residual=10tr, execute ALL periods under drift
        → current_book_value == 10tr (residual), NOT below it / NOT 0.

        Seeds a 5tr pre-existing accumulated so prev_acc + Σschedule (95tr) >
        depreciable_base (90tr). The buggy max(gross - new_acc, 0.0) formula
        yields book = 100 - 95 = 5tr (< residual) → FAILs here, proving the bug.
        The fix floors book at residual = 10tr."""
        asset = self._new(suffix="FLOOR")
        _seed_accumulated(asset, 5_000_000.0)
        res = depr_svc.run_due_depreciation(as_of=_FAR_FUTURE, asset=asset)
        self.assertGreater(res["executed_rows"], 0)
        self.assertAlmostEqual(_book(asset), _RESIDUAL, delta=0.01)
        self.assertGreaterEqual(_book(asset), _RESIDUAL - 0.01)

    def test_accumulated_never_exceeds_depreciable_base(self):
        """[TDD-RED] under drift (5tr pre-existing acc), execute ALL periods →
        accumulated capped at depreciable_base == 90tr, NOT 95tr.

        Buggy formula: new_acc = 5tr + 90tr = 95tr > 90tr → FAILs here."""
        asset = self._new(suffix="CAP")
        _seed_accumulated(asset, 5_000_000.0)
        depr_svc.run_due_depreciation(as_of=_FAR_FUTURE, asset=asset)
        self.assertAlmostEqual(_acc(asset), _DEPRECIABLE_BASE, delta=0.01)
        self.assertLessEqual(_acc(asset), _DEPRECIABLE_BASE + 0.01)

    # ── CONSISTENCY: planner ↔ executor ───────────────────────────────────────

    def test_book_value_matches_last_schedule_remaining(self):
        """[TDD] header current_book_value == remaining_value of the last
        Executed schedule row (planner ↔ executor consistency)."""
        asset = self._new(suffix="CONSIST")
        depr_svc.run_due_depreciation(as_of=_FAR_FUTURE, asset=asset)
        last = frappe.db.sql(
            """
            SELECT remaining_value
            FROM `tab{0}`
            WHERE parent = %s AND status = 'Executed'
            ORDER BY period_number DESC
            LIMIT 1
            """.format(_DT_SCHED),
            (asset,),
            as_dict=True,
        )
        self.assertTrue(last, "expected at least one Executed schedule row")
        self.assertAlmostEqual(_book(asset), flt(last[0]["remaining_value"]), delta=0.01)

    # ── IDEMPOTENT / NO OVER-DEPRECIATION ─────────────────────────────────────

    def test_run_due_idempotent_no_overdepreciation(self):
        """[TDD] run #1 executes all; run #2 (no more due Pending) →
        executed_rows=0 and accumulated + book_value unchanged."""
        asset = self._new(suffix="IDEMP")
        depr_svc.run_due_depreciation(as_of=_FAR_FUTURE, asset=asset)
        acc1, book1 = _acc(asset), _book(asset)

        res2 = depr_svc.run_due_depreciation(as_of=_FAR_FUTURE, asset=asset)
        self.assertEqual(res2["executed_rows"], 0)
        self.assertAlmostEqual(_acc(asset), acc1, delta=0.01)
        self.assertAlmostEqual(_book(asset), book1, delta=0.01)

    # ── BACKWARD COMPAT: residual = 0 ─────────────────────────────────────────

    def test_residual_zero_backward_compatible(self):
        """[TDD] residual=0 → book value floors at 0 (old behaviour);
        accumulated == gross. No regression."""
        asset = self._new(suffix="ZERO", residual=0.0)
        depr_svc.run_due_depreciation(as_of=_FAR_FUTURE, asset=asset)
        self.assertAlmostEqual(_book(asset), 0.0, delta=0.01)
        self.assertAlmostEqual(_acc(asset), _GROSS, delta=0.01)

    # ── LAGGING CRON: multi-period batch in one pass ──────────────────────────

    def test_lagging_cron_multi_period_caps_correctly(self):
        """[TDD] cron late: many Pending periods due → executed in one batch →
        still stops exactly at residual, accumulated capped at depreciable_base.
        (INVARIANT-1 + INVARIANT-2 under the batch path.)"""
        # 24 monthly periods, all due by the far-future cutoff → single batch.
        # Seed drift so the cap is genuinely exercised by the batch path.
        asset = self._new(suffix="LAG", months=24)
        _seed_accumulated(asset, 8_000_000.0)
        res = depr_svc.run_due_depreciation(as_of=_FAR_FUTURE, asset=asset)
        self.assertGreaterEqual(res["executed_rows"], 24)
        self.assertAlmostEqual(_book(asset), _RESIDUAL, delta=0.01)
        self.assertGreaterEqual(_book(asset), _RESIDUAL - 0.01)
        self.assertLessEqual(_acc(asset), _DEPRECIABLE_BASE + 0.01)

    # ── LIFECYCLE EVENT NOTES: capped delta, not raw inc ──────────────────────

    def test_lifecycle_event_notes_uses_capped_delta(self):
        """[TDD] when the last period is capped, the 'depreciated' lifecycle
        event notes record the ACTUALLY-BOOKED delta (acc moves to the cap),
        NOT the raw schedule increment. With drift, run_due_depreciation runs
        once-per-asset (batched), so a single event records the booked total =
        depreciable_base - prev_acc, which must equal final_acc - seed."""
        asset = self._new(suffix="NOTES")
        seed = 5_000_000.0
        _seed_accumulated(asset, seed)
        depr_svc.run_due_depreciation(as_of=_FAR_FUTURE, asset=asset)
        events = frappe.get_all(
            "Asset Lifecycle Event",
            filters={"asset": asset, "event_type": "depreciated"},
            fields=["notes"],
            order_by="creation asc",
        )
        self.assertTrue(events, "expected 'depreciated' lifecycle events")
        # Final accumulated capped at depreciable_base.
        self.assertAlmostEqual(_acc(asset), _DEPRECIABLE_BASE, delta=0.01)
        # The booked delta = capped acc - seed = 90tr - 5tr = 85tr. The raw
        # schedule total is 90tr; the buggy `booked = inc` would print 90tr.
        expected_booked = _DEPRECIABLE_BASE - seed
        notes_blob = " ".join(e.get("notes") or "" for e in events)
        digits = lambda s: float(s.replace(",", ""))  # noqa: E731
        booked_numbers = [
            digits(m) for m in __import__("re").findall(
                r"Depreciated ([\d,]+) VND", notes_blob,
            )
        ]
        self.assertTrue(booked_numbers, f"no booked delta parsed from: {notes_blob!r}")
        self.assertAlmostEqual(sum(booked_numbers), expected_booked, delta=1.0)


class TestFullyDepreciatedSoT(unittest.TestCase):
    """BR-05-15 / INV-DEP-5: SoT predicate `is_fully_depreciated(row)`.

    Pure-function tests — no DB. The single predicate `configured ∧
    current_book_value <= residual_value + 1` is the ONLY source of truth for
    the "Hết khấu hao" KPI count AND the drill-down list filter. The `+ 1`
    (1 VND) absorbs last-period rounding; residual=0 ⇒ only book<=1 (~0) counts.
    """

    def _row(self, **kw) -> dict:
        base = {
            "gross_purchase_amount": 100_000_000.0,
            "residual_value": 10_000_000.0,
            "current_book_value": 10_000_000.0,
            "depreciation_method": "Straight Line",
            "total_depreciation_months": 12,
        }
        base.update(kw)
        return base

    # ── boundary tolerance ────────────────────────────────────────────────────

    def test_true_when_book_equals_residual(self):
        self.assertTrue(
            depr_svc.is_fully_depreciated(self._row(current_book_value=10_000_000.0)),
        )

    def test_true_at_boundary_residual_plus_one(self):
        """book == residual + 1 (1 VND rounding tolerance) → True."""
        self.assertTrue(
            depr_svc.is_fully_depreciated(self._row(current_book_value=10_000_001.0)),
        )

    def test_false_beyond_tolerance_residual_plus_two(self):
        """book == residual + 2 → outside tolerance → False (still depreciating)."""
        self.assertFalse(
            depr_svc.is_fully_depreciated(self._row(current_book_value=10_000_002.0)),
        )

    # ── NOT configured ⇒ False even if book <= residual ─────────────────────────

    def test_false_when_method_empty(self):
        self.assertFalse(
            depr_svc.is_fully_depreciated(
                self._row(depreciation_method="", current_book_value=0.0),
            ),
        )

    def test_false_when_method_none_literal(self):
        self.assertFalse(
            depr_svc.is_fully_depreciated(
                self._row(depreciation_method="None", current_book_value=0.0),
            ),
        )

    def test_false_when_months_zero(self):
        self.assertFalse(
            depr_svc.is_fully_depreciated(
                self._row(total_depreciation_months=0, current_book_value=0.0),
            ),
        )

    def test_false_when_gross_zero(self):
        self.assertFalse(
            depr_svc.is_fully_depreciated(
                self._row(gross_purchase_amount=0, current_book_value=0.0),
            ),
        )

    # ── residual = 0 backward-compat ────────────────────────────────────────────

    def test_residual_zero_true_when_book_le_one(self):
        self.assertTrue(
            depr_svc.is_fully_depreciated(
                self._row(residual_value=0.0, current_book_value=1.0),
            ),
        )

    def test_residual_zero_false_when_book_two(self):
        """residual=0, book=2 → False — không kéo asset khấu hao dở vào tập."""
        self.assertFalse(
            depr_svc.is_fully_depreciated(
                self._row(residual_value=0.0, current_book_value=2.0),
            ),
        )

    def test_book_none_falls_back_to_gross(self):
        """current_book_value=None ⇒ book defaults to gross (not yet depreciated)
        → only fully-depreciated if gross<=residual+1 (here gross=100tr ⇒ False)."""
        self.assertFalse(
            depr_svc.is_fully_depreciated(self._row(current_book_value=None)),
        )


class TestClampHelpers(unittest.TestCase):
    """Pure-function tests for the shared floor/cap helpers (DRY guard)."""

    def test_clamp_book_value_floors_at_residual(self):
        # gross - acc would be 5tr but residual is 10tr → floor at residual.
        self.assertAlmostEqual(
            depr_svc._clamp_book_value(100_000_000, 10_000_000, 95_000_000),
            10_000_000, delta=0.01,
        )

    def test_clamp_book_value_residual_zero(self):
        self.assertAlmostEqual(
            depr_svc._clamp_book_value(100_000_000, 0, 100_000_000), 0.0, delta=0.01,
        )

    def test_clamp_accumulated_caps_at_depreciable_base(self):
        # acc overshoots base (90tr) → capped at 90tr.
        self.assertAlmostEqual(
            depr_svc._clamp_accumulated(100_000_000, 10_000_000, 95_000_000),
            90_000_000, delta=0.01,
        )

    def test_clamp_accumulated_below_base_unchanged(self):
        self.assertAlmostEqual(
            depr_svc._clamp_accumulated(100_000_000, 10_000_000, 40_000_000),
            40_000_000, delta=0.01,
        )
