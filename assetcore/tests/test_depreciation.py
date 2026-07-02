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


class TestAutoGenerateScheduleOnInsert(unittest.TestCase):
    """L-07: tạo tài sản ĐÃ cấu hình khấu hao ⇒ after_insert tự sinh lịch (không
    cần bấm 'Sinh lịch'). Tiến độ '0/0 kỳ' biến mất vì schedule rows đã tồn tại.

    - Configured (method + gross>0 + months>0) ⇒ auto-gen đúng số kỳ.
    - Chưa cấu hình (months=0) ⇒ KHÔNG sinh (không rác lịch trống).
    - Best-effort: hook KHÔNG được vỡ thao tác tạo asset.
    """

    def _count_schedule(self, asset_name: str) -> int:
        return frappe.db.count(
            "AC Asset Depreciation Schedule",
            {"parent": asset_name, "parenttype": "AC Asset"},
        )

    def tearDown(self) -> None:
        from assetcore.tests._asset_cleanup import purge_asset
        for name in getattr(self, "_created", []):
            purge_asset(name)

    def test_configured_asset_auto_generates_schedule(self) -> None:
        self._created = []
        name = _make_asset(suffix="AutoGen", months=12, frequency="Monthly")
        self._created.append(name)
        self.assertEqual(
            self._count_schedule(name), 12,
            "asset đã cấu hình (12 tháng/Monthly) phải tự sinh 12 kỳ khi tạo",
        )

    def test_unconfigured_asset_no_schedule(self) -> None:
        self._created = []
        name = _make_asset(suffix="NoRule", months=0, method="None")
        self._created.append(name)
        self.assertEqual(
            self._count_schedule(name), 0,
            "asset chưa cấu hình (months=0/method None) KHÔNG sinh lịch trống",
        )


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

    def test_fresh_asset_not_fully_depreciated(self):
        """L-05: asset MỚI (configured, current_book_value=0.0 do Frappe Currency
        NOT NULL default lúc insert, accumulated=0) KHÔNG được tính 'hết khấu hao'
        — chưa khấu hao kỳ nào. Phân biệt với asset đã KH hết (accumulated>0)."""
        self.assertFalse(
            depr_svc.is_fully_depreciated(
                self._row(
                    residual_value=0.0,
                    current_book_value=0.0,
                    accumulated_depreciation=0.0,
                ),
            ),
        )

    def test_fully_depreciated_when_accumulated_reached_base(self):
        """Asset đã KH hết THẬT (accumulated == gross-residual, book chạm sàn 0) ⇒
        VẪN tính 'hết khấu hao' (không bị fresh-asset guard nuốt)."""
        self.assertTrue(
            depr_svc.is_fully_depreciated(
                self._row(
                    residual_value=0.0,
                    current_book_value=0.0,
                    accumulated_depreciation=100_000_000.0,
                ),
            ),
        )


class TestEffectiveBookValueSoT(unittest.TestCase):
    """BR-05-13 / INV-DEP-8: SoT DUY NHẤT `effective_book_value(row)` đọc book.

    Pure-function — no DB. Fix falsy-zero bug: idiom cũ
    ``float(current_book_value or gross)`` nuốt book=0.0 HỢP LỆ (asset đã KH
    hết, residual=0) → phantom gross. `or` không phân biệt:
      - None  (chưa từng chạy KH) ⇒ ĐÚNG phải fallback gross.
      - 0.0   (đã set, giá trị thật) ⇒ PHẢI giữ 0.0, KHÔNG về gross.

    RED-EXPERIMENT (ghi lại, KHÔNG commit): tạm revert `effective_book_value`
    về ``float(asset_row.get('current_book_value') or gross)`` ⇒
    ``test_zero_stays_zero`` FAIL (trả 100tr thay vì 0.0). restore → GREEN.
    Đây là RED-proof chính của falsy-zero bug ở tầng SoT.
    """

    def test_none_falls_back_to_gross(self):
        """current_book_value=None (chưa chạy KH) ⇒ book = gross (no-regression)."""
        self.assertEqual(
            depr_svc.effective_book_value({
                "current_book_value": None,
                "gross_purchase_amount": 100_000_000,
            }),
            100_000_000.0,
        )

    def test_zero_stays_zero(self):
        """Asset đã KH hết THẬT (current_book_value=0.0 VÀ accumulated>0) ⇒ book=0.0,
        KHÔNG về gross.

        RED-PROOF của falsy-zero bug: `0.0 or gross` → gross (sai). Phân biệt với
        asset MỚI (accumulated=0 ⇒ book=gross, xem test_fresh_asset_*). Một asset
        chỉ "đã KH hết về 0" khi accumulated đã đạt depreciable_base — nên row hợp
        lệ PHẢI có accumulated>0.
        """
        self.assertEqual(
            depr_svc.effective_book_value({
                "current_book_value": 0.0,
                "gross_purchase_amount": 100_000_000,
                "accumulated_depreciation": 100_000_000,
            }),
            0.0,
        )

    def test_fresh_asset_zero_book_falls_back_to_gross(self):
        """L-04: asset MỚI — Frappe lưu current_book_value=0.0 (Currency NOT NULL
        default) lúc insert, accumulated=0 ⇒ giá trị còn lại thực = gross (sửa
        'Giá trị còn lại 0₫'). KHÁC asset đã KH hết (accumulated>0 ⇒ giữ 0.0)."""
        self.assertEqual(
            depr_svc.effective_book_value({
                "current_book_value": 0.0,
                "gross_purchase_amount": 5_000_000,
                "accumulated_depreciation": 0,
            }),
            5_000_000.0,
        )

    def test_partial_value_verbatim(self):
        """Asset đang KH dở: book = giá trị thật, không đụng (verbatim float)."""
        self.assertEqual(
            depr_svc.effective_book_value({
                "current_book_value": 37_500_000,
                "gross_purchase_amount": 100_000_000,
            }),
            37_500_000.0,
        )

    def test_missing_key_treated_as_none(self):
        """Thiếu hẳn key current_book_value ⇒ như None ⇒ fallback gross."""
        self.assertEqual(
            depr_svc.effective_book_value({"gross_purchase_amount": 60_000_000}),
            60_000_000.0,
        )

    def test_none_with_no_gross_returns_zero(self):
        """None + thiếu gross ⇒ gross coerce 0 ⇒ trả 0.0 (không vỡ)."""
        self.assertEqual(
            depr_svc.effective_book_value({"current_book_value": None}),
            0.0,
        )


class TestNoInlineBookFallbackGuard(unittest.TestCase):
    """Grep-guard (BR-05-13): chống tái-inline drift của idiom falsy-zero.

    Sau khi hợp nhất về `effective_book_value`, KHÔNG còn pattern
    ``current_book_value") or gross`` nào trong api/imm00.py — 3 call-site
    (compute_depreciation / _depr_enrich_row / get_depreciation_stats) PHẢI
    gọi SoT. Nếu ai đó inline lại idiom cũ, test này FAIL ngay.
    """

    def test_no_or_gross_in_api_imm00(self):
        import os
        import assetcore.api.imm00 as imm00_mod

        src = open(imm00_mod.__file__, encoding="utf-8").read()
        self.assertNotIn(
            'current_book_value") or gross', src,
            "falsy-zero idiom `current_book_value\") or gross` re-introduced "
            "in api/imm00.py — route book through effective_book_value (SoT).",
        )
        _ = os  # keep import explicit


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


# ─────────────────────────────────────────────────────────────────────────────
# SoT: inherit_depreciation_rules_from_category — TDD (Task BE root-cause fix)
# ─────────────────────────────────────────────────────────────────────────────

_CAT_DEPR = "_TestCatDeprSoT"          # Category WITH depreciation rule
_CAT_NORULE = "_TestCatDeprNoRule"     # Category WITHOUT rule (months=0)


def _ensure_category(name: str, *, months: int, residual_pct: float,
                     method: str = "Straight Line", frequency: str = "Monthly") -> str:
    """Idempotently create an AC Asset Category for SoT tests (by category_name).

    AC Asset Category autoname=CAT-#### (memory: factory_rounds_6_10 pitfall) ⇒
    lookup/cleanup MUST be by the `category_name` field, NOT `name`.
    """
    existing = frappe.db.get_value(
        "AC Asset Category", {"category_name": name}, "name",
    )
    if existing:
        frappe.db.set_value("AC Asset Category", existing, {
            "default_depreciation_method": method,
            "total_depreciation_months": months,
            "depreciation_frequency": frequency,
            "default_residual_value_pct": residual_pct,
        }, update_modified=False)
        return existing
    doc = frappe.get_doc({
        "doctype": "AC Asset Category",
        "category_name": name,
        "default_depreciation_method": method,
        "total_depreciation_months": months,
        "depreciation_frequency": frequency,
        "default_residual_value_pct": residual_pct,
        "is_active": 1,
    }).insert(ignore_permissions=True)
    return doc.name


def _purge_category(name: str) -> None:
    cat = frappe.db.get_value("AC Asset Category", {"category_name": name}, "name")
    if cat:
        try:
            frappe.delete_doc("AC Asset Category", cat, force=True,
                              ignore_permissions=True)
        except Exception:
            pass


import contextlib  # noqa: E402


@contextlib.contextmanager
def _suppress_commit():
    """Neutralise frappe.db.commit() inside the block.

    compute_all_depreciation() iterates ALL assets and commits internally
    (run_due_depreciation). In a shared-DB test run that would PERSIST schedule
    rows / executed depreciation / lifecycle events on real + other-test assets,
    breaking downstream tests' rollback isolation. We swap commit for a no-op so
    every side-effect stays in the open transaction and is undone by
    frappe.db.rollback() in tearDown. Assertions still read the in-transaction
    state correctly.
    """
    real_commit = frappe.db.commit
    frappe.db.commit = lambda *a, **k: None
    try:
        yield
    finally:
        frappe.db.commit = real_commit


class TestInheritDepreciationRulesSoT(unittest.TestCase):
    """[TDD] SoT `inherit_depreciation_rules_from_category` — pure-ish (needs Category).

    INVARIANT (SoT luật khấu hao = AC Asset Category):
      (a) Category months=60, residual_pct=10, asset thiếu months/residual →
          helper set months==60 ∧ residual==round(gross*0.10,2), returns True.
      (b) Category months=0 → helper returns False, KHÔNG raise, asset.months stays 0.
      (c) asset ĐÃ có months=24 (user nhập) → helper KHÔNG ghi đè (giữ 24).
    """

    @classmethod
    def setUpClass(cls):
        _ensure_uom()
        cls.cat_rule = _ensure_category(_CAT_DEPR, months=60, residual_pct=10.0)
        cls.cat_norule = _ensure_category(_CAT_NORULE, months=0, residual_pct=0.0)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        _purge_category(_CAT_DEPR)
        _purge_category(_CAT_NORULE)
        frappe.db.commit()

    def _new_doc(self, **kw) -> "frappe.model.document.Document":
        """A non-inserted AC Asset doc (supports .get/.set, no DB write)."""
        base = {
            "doctype": _DT_ASSET,
            "asset_name": "_Test InheritSoT",
            "gross_purchase_amount": 100_000_000.0,
        }
        base.update(kw)
        return frappe.get_doc(base)

    # ── (a) inherits months + residual when asset missing both ────────────────
    def test_a_inherits_months_and_residual(self):
        doc = self._new_doc(asset_category=self.cat_rule)
        result = depr_svc.inherit_depreciation_rules_from_category(doc)
        self.assertTrue(result)
        self.assertEqual(int(doc.total_depreciation_months), 60)
        self.assertAlmostEqual(
            flt(doc.residual_value),
            round(100_000_000.0 * 10.0 / 100, 2),
            delta=0.01,
        )

    # ── (b) Category months=0 → no fabrication, no raise, returns False ───────
    def test_b_no_rule_category_returns_false_no_raise(self):
        doc = self._new_doc(asset_category=self.cat_norule)
        result = depr_svc.inherit_depreciation_rules_from_category(doc)
        self.assertFalse(result)
        self.assertEqual(int(doc.total_depreciation_months or 0), 0)

    # ── (c) user-entered months=24 preserved (no clobber) ─────────────────────
    def test_c_user_months_not_clobbered(self):
        doc = self._new_doc(asset_category=self.cat_rule,
                            total_depreciation_months=24)
        depr_svc.inherit_depreciation_rules_from_category(doc)
        self.assertEqual(int(doc.total_depreciation_months), 24)

    # ── user-entered residual preserved (no clobber) ──────────────────────────
    def test_c_user_residual_not_clobbered(self):
        doc = self._new_doc(asset_category=self.cat_rule,
                            residual_value=7_777.0)
        depr_svc.inherit_depreciation_rules_from_category(doc)
        self.assertAlmostEqual(flt(doc.residual_value), 7_777.0, delta=0.01)

    # ── no category / gross<=0 → no-op False ──────────────────────────────────
    def test_no_category_returns_false(self):
        doc = self._new_doc(asset_category="")
        self.assertFalse(depr_svc.inherit_depreciation_rules_from_category(doc))

    def test_zero_gross_returns_false(self):
        doc = self._new_doc(asset_category=self.cat_rule,
                            gross_purchase_amount=0)
        self.assertFalse(depr_svc.inherit_depreciation_rules_from_category(doc))


class TestComputeAllNoNPlusOne(unittest.TestCase):
    """[TDD] compute_all_depreciation must NOT issue 2×N per-asset count queries.

    ROOT CAUSE (pre-optimize): inside the asset loop the endpoint called
    ``frappe.db.count`` twice per asset — once to detect Executed history
    (skipped_has_history branch) and once to detect an existing schedule
    (generate_schedule branch). Total per-asset count calls = 2×N ⇒ N+1 query
    explosion that grows linearly with the asset count.

    OPTIMIZED CONTRACT (this test pins it):
      * exactly TWO GROUP-BY prefetch queries run ONCE before the loop:
          (a) executed_parents  = parents WITH >=1 status='Executed' row,
          (b) scheduled_parents = parents WITH >=1 row (any status);
      * inside the loop each check is an O(1) Python set membership test —
        ``frappe.db.count`` is called ZERO times for these two per-asset checks.

    The spy filters on ``_DT_SCHED`` count calls carrying a ``parent`` /
    ``parenttype`` filter (the exact signature of the two removed per-asset
    checks) so unrelated count usage elsewhere in the call graph does not make
    the assertion brittle. On the un-optimized code this asserts RED (>=2N>0);
    after batching it is GREEN (==0).

    Dataset (>=3 assets, per acceptance):
      A1 — missing months, Category HAS rule → inherited + generated.
      A2 — fully configured + has an Executed schedule row (history) →
           skipped_has_history, accumulated UNCHANGED (executed_parents set
           must drive the preserve-history branch).
      A3 — no method + Category has NO rule → skipped_no_rule.
    """

    @classmethod
    def setUpClass(cls):
        _ensure_uom()
        cls.cat_rule = _ensure_category(_CAT_DEPR, months=60, residual_pct=10.0)
        cls.cat_norule = _ensure_category(_CAT_NORULE, months=0, residual_pct=0.0)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        _purge_category(_CAT_DEPR)
        _purge_category(_CAT_NORULE)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.db.rollback()
        frappe.set_user("Administrator")

    def _bare_asset(self, *, suffix: str, category: str = "",
                    method: str = "", months: int = 0,
                    gross: float = 50_000_000.0) -> str:
        """Insert an asset in the OPEN transaction (no commit), optionally
        re-pointing at a rule Category via direct db set so a 'missing months'
        state survives until compute_all runs (mirrors the sibling test)."""
        doc = frappe.get_doc({
            "doctype": _DT_ASSET,
            "asset_name": f"_Test ComputeAll NPLUS1 {suffix}",
            "gross_purchase_amount": gross,
            "depreciation_method": method,
            "total_depreciation_months": months,
            "lifecycle_status": "Active",
        })
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_links = True
        prev = frappe.flags.in_install
        frappe.flags.in_install = "frappe"
        try:
            doc.insert(ignore_permissions=True)
        finally:
            frappe.flags.in_install = prev
        if category:
            frappe.db.set_value(_DT_ASSET, doc.name, "asset_category", category,
                                update_modified=False)
        return doc.name

    def _seed_three(self):
        """A1 (inherit+generate), A2 (executed history), A3 (no rule)."""
        a1 = self._bare_asset(suffix="A1", category=self.cat_rule,
                              method="", months=0)
        a2 = self._bare_asset(suffix="A2", category=self.cat_rule,
                              method="Straight Line", months=12)
        depr_svc.generate_schedule(a2, force=True)
        row = frappe.db.get_value(
            _DT_SCHED, {"parent": a2, "status": "Pending"}, "name",
            order_by="period_number asc")
        frappe.db.set_value(_DT_SCHED, row, "status", "Executed",
                            update_modified=False)
        frappe.db.set_value(_DT_ASSET, a2, "accumulated_depreciation",
                            123_456.0, update_modified=False)
        a3 = self._bare_asset(suffix="A3", category=self.cat_norule,
                              method="", months=0)
        return a1, a2, a3

    @contextlib.contextmanager
    def _query_spy(self):
        """Spy two call surfaces during compute_all:

        * ``frappe.db.count`` — records per-asset schedule-count calls
          (doctype==_DT_SCHED with a ``parent`` filter). The optimization
          removes these → must be ZERO (RED on the old 2×N code).
        * ``frappe.get_all`` — records the prefetch GROUP-BY-parent reads on
          _DT_SCHED. The optimization adds EXACTLY TWO (executed + scheduled),
          each running once before the loop, independent of N.
        """
        real_count = frappe.db.count
        real_get_all = frappe.get_all
        rec = {"per_asset_count": [], "prefetch_groupby": []}

        def _count_spy(doctype, filters=None, *a, **k):
            if doctype == _DT_SCHED and isinstance(filters, dict) \
                    and "parent" in filters:
                rec["per_asset_count"].append(dict(filters))
            return real_count(doctype, filters, *a, **k)

        def _get_all_spy(doctype, *a, **k):
            if doctype == _DT_SCHED and k.get("group_by") == "parent":
                rec["prefetch_groupby"].append(dict(k.get("filters") or {}))
            return real_get_all(doctype, *a, **k)

        frappe.db.count = _count_spy
        frappe.get_all = _get_all_spy
        try:
            yield rec
        finally:
            frappe.db.count = real_count
            frappe.get_all = real_get_all

    def test_no_per_asset_count_calls(self):
        """N+1 contract: ZERO per-asset frappe.db.count(parent=..) calls; the
        two count checks are served by EXACTLY TWO GROUP-BY-parent prefetch
        reads run once before the loop (count NOT linear in N)."""
        from assetcore.api.imm00 import compute_all_depreciation
        self._seed_three()

        with self._query_spy() as rec, _suppress_commit():
            compute_all_depreciation()

        self.assertEqual(
            rec["per_asset_count"], [],
            f"expected 0 per-asset frappe.db.count(parent=..) calls (replaced "
            f"by GROUP-BY prefetch sets); got {len(rec['per_asset_count'])}: "
            f"{rec['per_asset_count']}",
        )
        self.assertEqual(
            len(rec["prefetch_groupby"]), 2,
            f"expected EXACTLY 2 GROUP-BY-parent prefetch reads on {_DT_SCHED} "
            f"(executed + scheduled, once each); got "
            f"{len(rec['prefetch_groupby'])}: {rec['prefetch_groupby']}",
        )
        # one prefetch filters status='Executed' (preserve-history set), the
        # other has no status filter (all-rows scheduled set).
        statuses = sorted(
            f.get("status", "") for f in rec["prefetch_groupby"])
        self.assertEqual(
            statuses, ["", "Executed"],
            f"prefetch reads must be {{executed, all-rows}}; got {statuses}")

    def test_payload_identical_after_optimize(self):
        """Payload shape + per-group counts invariant on the fixed dataset."""
        from assetcore.api.imm00 import compute_all_depreciation
        self._seed_three()

        with _suppress_commit():
            resp = compute_all_depreciation()
        data = resp["data"] if "data" in resp else resp

        for key in ("inherited", "generated", "executed_rows",
                    "updated_assets", "skipped_has_history", "skipped_no_rule"):
            self.assertIn(key, data, f"payload missing key {key}")
        self.assertGreaterEqual(data["inherited"], 1, "A1 inherited")
        self.assertGreaterEqual(data["generated"], 1, "A1 generated")
        self.assertGreaterEqual(data["skipped_has_history"], 1, "A2 history")
        self.assertGreaterEqual(data["skipped_no_rule"], 1, "A3 no-rule")

    def test_executed_history_preserved_via_prefetch_set(self):
        """A2 (1 Executed row) → skipped_has_history; accumulated UNCHANGED and
        NOT regenerated. Proves the executed_parents prefetch set drives the
        preserve-history branch correctly."""
        from assetcore.api.imm00 import compute_all_depreciation
        _a1, a2, _a3 = self._seed_three()
        acc_before = flt(frappe.db.get_value(
            _DT_ASSET, a2, "accumulated_depreciation"))
        rows_before = frappe.db.count(
            _DT_SCHED, {"parent": a2, "parenttype": _DT_ASSET})

        with _suppress_commit():
            resp = compute_all_depreciation()
        data = resp["data"] if "data" in resp else resp

        self.assertGreaterEqual(data["skipped_has_history"], 1)
        acc_after = flt(frappe.db.get_value(
            _DT_ASSET, a2, "accumulated_depreciation"))
        self.assertAlmostEqual(acc_after, acc_before, delta=0.01,
                               msg="executed-history accumulated tampered")
        rows_after = frappe.db.count(
            _DT_SCHED, {"parent": a2, "parenttype": _DT_ASSET})
        self.assertEqual(rows_after, rows_before,
                         "history asset schedule must NOT be regenerated")


class TestComputeAllBackfillsThenGenerates(unittest.TestCase):
    """[TDD] compute_all_depreciation backfills rule from Category THEN generates.

    Seed 3 assets:
      A1 — missing months, Category HAS rule → expect inherited + generated.
      A2 — has >=1 Executed period → expect skipped_has_history, accumulated UNCHANGED.
      A3 — no method + Category has NO rule → expect skipped_no_rule.
    """

    @classmethod
    def setUpClass(cls):
        _ensure_uom()
        cls.cat_rule = _ensure_category(_CAT_DEPR, months=60, residual_pct=10.0)
        cls.cat_norule = _ensure_category(_CAT_NORULE, months=0, residual_pct=0.0)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        _purge_category(_CAT_DEPR)
        _purge_category(_CAT_NORULE)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        # Roll back EVERYTHING this test did — including compute_all's global
        # side-effects on real/other-test assets (commit was suppressed) — so the
        # shared DB is pristine for downstream tests.
        frappe.db.rollback()
        frappe.set_user("Administrator")

    def _bare_asset(self, *, suffix: str, category: str = "",
                    method: str = "", months: int = 0,
                    gross: float = 50_000_000.0) -> str:
        """Insert an asset in the OPEN transaction (no commit).

        before_insert inherits from Category when category set + gross>0. To seed
        A1 'missing months' we insert WITHOUT the category, then point it at the
        rule category via direct db set (bypass controller) so the missing-state
        survives until compute_all runs.
        """
        doc = frappe.get_doc({
            "doctype": _DT_ASSET,
            "asset_name": f"_Test ComputeAll {suffix}",
            "gross_purchase_amount": gross,
            "depreciation_method": method,
            "total_depreciation_months": months,
            "lifecycle_status": "Active",
        })
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_links = True
        prev = frappe.flags.in_install
        frappe.flags.in_install = "frappe"
        try:
            doc.insert(ignore_permissions=True)
        finally:
            frappe.flags.in_install = prev
        if category:
            frappe.db.set_value(_DT_ASSET, doc.name, "asset_category", category,
                                update_modified=False)
        return doc.name

    def test_payload_counts_each_group(self):
        from assetcore.api.imm00 import compute_all_depreciation

        # A1: missing months, Category HAS rule.
        a1 = self._bare_asset(suffix="A1", category=self.cat_rule,
                              method="", months=0)
        # A2: fully configured + has an Executed schedule row (history).
        a2 = self._bare_asset(suffix="A2", category=self.cat_rule,
                              method="Straight Line", months=12)
        depr_svc.generate_schedule(a2, force=True)
        # mark first row Executed + seed accumulated to detect tampering
        row = frappe.db.get_value(
            _DT_SCHED,
            {"parent": a2, "status": "Pending"}, "name",
            order_by="period_number asc",
        )
        frappe.db.set_value(_DT_SCHED, row, "status", "Executed",
                            update_modified=False)
        frappe.db.set_value(_DT_ASSET, a2, "accumulated_depreciation",
                            123_456.0, update_modified=False)
        acc_before = flt(frappe.db.get_value(
            _DT_ASSET, a2, "accumulated_depreciation"))
        # A3: no method, Category has NO rule.
        self._bare_asset(suffix="A3", category=self.cat_norule,
                         method="", months=0)

        with _suppress_commit():
            resp = compute_all_depreciation()
        data = resp["data"] if "data" in resp else resp

        self.assertGreaterEqual(data["inherited"], 1, "A1 must be inherited")
        self.assertGreaterEqual(data["generated"], 1, "A1 must generate schedule")
        self.assertGreaterEqual(data["skipped_has_history"], 1,
                                "A2 must be skipped_has_history")
        self.assertGreaterEqual(data["skipped_no_rule"], 1,
                                "A3 must be skipped_no_rule")
        for key in ("inherited", "generated", "executed_rows",
                    "updated_assets", "skipped_has_history", "skipped_no_rule"):
            self.assertIn(key, data, f"payload missing key {key}")

        # A1 now has the inherited rule.
        a1_months = int(frappe.db.get_value(
            _DT_ASSET, a1, "total_depreciation_months") or 0)
        self.assertEqual(a1_months, 60)
        # A2 history preserved — accumulated unchanged by backfill path.
        acc_after = flt(frappe.db.get_value(
            _DT_ASSET, a2, "accumulated_depreciation"))
        self.assertAlmostEqual(acc_after, acc_before, delta=0.01)

        # Audit trail (CLAUDE.md §5): A1 backfill must leave a lifecycle event.
        ev = frappe.get_all(
            "Asset Lifecycle Event",
            filters={"asset": a1, "event_type": "depreciation_rules_inherited"},
            fields=["name"],
        )
        self.assertGreaterEqual(
            len(ev), 1,
            "backfill must record a 'depreciation_rules_inherited' lifecycle event")


class TestComputeAllIdempotent(unittest.TestCase):
    """[TDD] running compute_all twice → 2nd run inherited==0, no dup schedule,
    A2 accumulated invariant."""

    @classmethod
    def setUpClass(cls):
        _ensure_uom()
        cls.cat_rule = _ensure_category(_CAT_DEPR, months=60, residual_pct=10.0)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        _purge_category(_CAT_DEPR)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        # Roll back the seed + both compute_all passes' global side-effects.
        frappe.db.rollback()
        frappe.set_user("Administrator")

    def _seed_a1(self) -> str:
        doc = frappe.get_doc({
            "doctype": _DT_ASSET,
            "asset_name": "_Test ComputeAll IDEMP A1",
            "gross_purchase_amount": 50_000_000.0,
            "depreciation_method": "",
            "total_depreciation_months": 0,
            "lifecycle_status": "Active",
        })
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_links = True
        prev = frappe.flags.in_install
        frappe.flags.in_install = "frappe"
        try:
            doc.insert(ignore_permissions=True)
        finally:
            frappe.flags.in_install = prev
        frappe.db.set_value(_DT_ASSET, doc.name, "asset_category", self.cat_rule,
                            update_modified=False)
        return doc.name

    def test_second_run_inherited_zero_no_dup(self):
        from assetcore.api.imm00 import compute_all_depreciation
        a1 = self._seed_a1()

        with _suppress_commit():
            r1 = compute_all_depreciation()
        d1 = r1["data"] if "data" in r1 else r1
        self.assertGreaterEqual(d1["inherited"], 1)
        sched_after_1 = frappe.db.count(
            _DT_SCHED, {"parent": a1, "parenttype": _DT_ASSET})
        self.assertGreater(sched_after_1, 0)

        with _suppress_commit():
            r2 = compute_all_depreciation()
        d2 = r2["data"] if "data" in r2 else r2
        # Nothing left to backfill for our seeded asset on 2nd pass.
        self.assertEqual(d2["inherited"], 0)
        # No duplicate schedule rows created for A1.
        sched_after_2 = frappe.db.count(
            _DT_SCHED, {"parent": a1, "parenttype": _DT_ASSET})
        self.assertEqual(sched_after_2, sched_after_1)


class TestComputeAllRBAC(unittest.TestCase):
    """[TDD] non-admin caller → PermissionError, backfill NOT executed."""

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")

    def test_non_admin_blocked(self):
        from assetcore.api.imm00 import compute_all_depreciation
        # Guest definitely lacks data.admin capability.
        frappe.set_user("Guest")
        try:
            with self.assertRaises(frappe.PermissionError):
                compute_all_depreciation()
        finally:
            frappe.set_user("Administrator")


class TestInheritGrepGuardSoT(unittest.TestCase):
    """[TDD] grep-guard: no 2nd branch RE-IMPLEMENTS the Category residual
    FORMULA (`gross * residual_pct / 100`) outside the SoT
    (inherit_depreciation_rules_from_category / create_ac_asset @ imm04 /
    bulk_regenerate_by_category @ depreciation).

    Guards the actual drift risk (a rogue copy of the residual computation),
    NOT a mere read of the column name (display/list endpoints legitimately
    SELECT default_residual_value_pct).
    """

    def test_no_rogue_residual_formula_copy(self):
        import os
        import re
        svc_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "services")
        api_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "api")
        ctrl = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "assetcore", "doctype", "ac_asset", "ac_asset.py")
        # Allowed SoT / historical write-sites (Task BE: đối chiếu KHÔNG lệch).
        allowed = {"depreciation.py", "imm04.py"}
        # residual formula: a `residual_pct` variable multiplied with gross/amount
        # then divided by 100 (the canonical Category-residual computation).
        formula_pat = re.compile(
            r"residual_pct\s*/\s*100|/\s*100(?:\.0)?\s*if\s*residual_pct",
        )
        offenders: list[str] = []
        for d in (svc_dir, api_dir):
            for fn in os.listdir(d):
                if not fn.endswith(".py") or fn in allowed:
                    continue
                blob = open(os.path.join(d, fn), encoding="utf-8").read()
                if formula_pat.search(blob):
                    offenders.append(os.path.join(d, fn))
        ctrl_blob = open(ctrl, encoding="utf-8").read()
        if formula_pat.search(ctrl_blob):
            offenders.append(ctrl)
        self.assertEqual(
            offenders, [],
            f"rogue Category residual FORMULA copy outside SoT: {offenders}",
        )


# ─────────────────────────────────────────────────────────────────────────────
# RC-04 (Round-2): per-asset self-heal at regenerate_depreciation_schedule
# (BR-00-22 / FR-00-53..55). TDD — written BEFORE the endpoint change.
# ─────────────────────────────────────────────────────────────────────────────

_DT_ALE = "Asset Lifecycle Event"
_DT_AUD = "IMM Audit Trail"


def _unwrap(resp):
    """Decode the api envelope (utils/response).

    _ok → {"success": True,  "data": <payload>}            → status 200
    _err → {"success": False, "error": msg, "http_status": N} → status N

    Returns (payload_or_envelope, status_int). For success the payload is the
    inner data dict; for error the full envelope (so .get('error') works)."""
    if isinstance(resp, dict) and resp.get("success") is True:
        return resp.get("data"), 200
    if isinstance(resp, dict) and resp.get("success") is False:
        return resp, int(resp.get("http_status") or 400)
    return resp, 200


class TestRegenerateSelfHeal(unittest.TestCase):
    """[TDD-BE-1..6] regenerate_depreciation_schedule per-asset self-heal.

    The endpoint MUST call the SoT inherit_depreciation_rules_from_category(asset)
    BEFORE the 4-field pre-check; 422 only when (post-inherit) the rule is still
    missing (Category also lacks rule / no category). No-clobber + history-safe +
    idempotent + audit-on-real-inherit (no garbage event on no-op).
    """

    @classmethod
    def setUpClass(cls):
        _ensure_uom()
        cls.cat_rule = _ensure_category(_CAT_DEPR, months=60, residual_pct=10.0)
        cls.cat_norule = _ensure_category(_CAT_NORULE, months=0, residual_pct=0.0)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        _purge_category(_CAT_DEPR)
        _purge_category(_CAT_NORULE)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.db.rollback()
        if hasattr(frappe.local, "response"):
            frappe.local.response.pop("http_status_code", None)
        frappe.set_user("Administrator")

    # ── seed an OLD asset: created BEFORE before_insert wired the SoT, so it has
    #    gross>0 + asset_category but total_depreciation_months=0 (never inherited)
    def _old_asset(self, *, suffix: str, category: str = "",
                   method: str = "", months: int = 0,
                   residual: float = 0.0,
                   gross: float = 50_000_000.0,
                   start: str = "2024-01-01") -> str:
        doc = frappe.get_doc({
            "doctype": _DT_ASSET,
            "asset_name": f"_Test SelfHeal {suffix}",
            "gross_purchase_amount": gross,
            "depreciation_method": method,
            "total_depreciation_months": months,
            "residual_value": residual,
            "depreciation_start_date": start,
            "in_service_date": start,
            "lifecycle_status": "Active",
        })
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_links = True
        prev = frappe.flags.in_install
        frappe.flags.in_install = "frappe"  # skip workflow + before_insert inherit
        try:
            doc.insert(ignore_permissions=True)
        finally:
            frappe.flags.in_install = prev
        if category:
            # Point at category via direct db set so the missing-state survives
            # (bypass controller inherit) — mirrors a real "old" asset.
            frappe.db.set_value(_DT_ASSET, doc.name, "asset_category", category,
                                update_modified=False)
        return doc.name

    def _ale_count(self, asset: str) -> int:
        return frappe.db.count(_DT_ALE, {
            "asset": asset, "event_type": "depreciation_rules_inherited"})

    def _aud_count(self, asset: str) -> int:
        return frappe.db.count(_DT_AUD, {"asset": asset, "event_type": "System"})

    # ── [TDD-BE-1] old asset months=0 + Category HAS rule → self-heal → 200 ────
    def test_be1_selfheal_inherits_then_generates(self):
        from assetcore.api.imm00 import regenerate_depreciation_schedule
        a = self._old_asset(suffix="BE1", category=self.cat_rule)
        # sanity RED-state: months=0 → would 422 without self-heal.
        self.assertEqual(
            int(frappe.db.get_value(_DT_ASSET, a, "total_depreciation_months") or 0),
            0)

        data, status = _unwrap(regenerate_depreciation_schedule(a))
        self.assertEqual(status, 200, f"expected 200, got {status}: {data}")
        self.assertGreater(data.get("periods", 0), 0)
        # months inherited from Category.
        self.assertEqual(
            int(frappe.db.get_value(_DT_ASSET, a, "total_depreciation_months")),
            60)
        # residual inherited (round(gross*10/100,2)).
        self.assertAlmostEqual(
            flt(frappe.db.get_value(_DT_ASSET, a, "residual_value")),
            round(50_000_000.0 * 10.0 / 100, 2), delta=0.01)

    # ── [TDD-BE-2] Category ALSO missing rule → STILL 422 (no fabrication) ─────
    def test_be2_category_no_rule_still_422(self):
        from assetcore.api.imm00 import regenerate_depreciation_schedule
        a = self._old_asset(suffix="BE2", category=self.cat_norule)
        data, status = _unwrap(regenerate_depreciation_schedule(a))
        self.assertEqual(status, 422)
        # message names the missing field (no fabricated number).
        msg = data.get("error") if isinstance(data, dict) else str(data)
        self.assertIn("total_depreciation_months", msg)

    # ── [TDD-BE-4] no asset_category at all → STILL 422 on months ─────────────
    def test_be4_no_category_still_422(self):
        from assetcore.api.imm00 import regenerate_depreciation_schedule
        a = self._old_asset(suffix="BE4", category="")
        data, status = _unwrap(regenerate_depreciation_schedule(a))
        self.assertEqual(status, 422)
        msg = data.get("error") if isinstance(data, dict) else str(data)
        self.assertIn("total_depreciation_months", msg)

    # ── [TDD-BE-3] user-entered months=36 preserved (no-clobber), periods=36 ──
    def test_be3_no_clobber_user_months(self):
        from assetcore.api.imm00 import regenerate_depreciation_schedule
        # user typed months=36 + method; Category says 60 → must KEEP 36.
        a = self._old_asset(suffix="BE3", category=self.cat_rule,
                            method="Straight Line", months=36)
        data, status = _unwrap(regenerate_depreciation_schedule(a))
        self.assertEqual(status, 200, f"got {status}: {data}")
        self.assertEqual(
            int(frappe.db.get_value(_DT_ASSET, a, "total_depreciation_months")),
            36, "user months must be preserved (inherit no-op)")
        # Monthly frequency → periods == months == 36.
        self.assertEqual(data.get("periods"), 36)

    # ── [TDD-BE-5] audit: real self-heal → exactly 1 ALE + 1 IMM Audit Trail;
    #    2nd call (now configured, inherit no-op) → NO new garbage event ───────
    def test_be5_audit_on_real_inherit_then_no_garbage(self):
        from assetcore.api.imm00 import regenerate_depreciation_schedule
        a = self._old_asset(suffix="BE5", category=self.cat_rule)
        # Asset insert emits exactly 1 'System' IMM Audit Trail for qr_generated
        # (ADR-001) — UNRELATED to the self-heal. _aud_count filters by the shared
        # 'System' enum so it also catches the qr audit; measure the self-heal
        # DELTA (not the absolute count) to assert the self-heal contribution.
        base_aud = self._aud_count(a)

        _data, status = _unwrap(regenerate_depreciation_schedule(a))
        self.assertEqual(status, 200)
        self.assertEqual(self._ale_count(a), 1,
                         "real self-heal must record exactly 1 lifecycle event")
        self.assertEqual(self._aud_count(a) - base_aud, 1,
                         "real self-heal must record exactly 1 IMM Audit Trail")

        # 2nd call: asset now has months → inherit no-op → NO new events.
        _data2, status2 = _unwrap(regenerate_depreciation_schedule(a))
        self.assertEqual(status2, 200)
        self.assertEqual(self._ale_count(a), 1,
                         "inherit no-op must NOT emit a 2nd lifecycle event")
        self.assertEqual(self._aud_count(a) - base_aud, 1,
                         "inherit no-op must NOT emit a 2nd audit trail")

    # ── [TDD-BE-5b] idempotent: 2 consecutive calls → same period count ───────
    def test_be5b_idempotent_same_periods(self):
        from assetcore.api.imm00 import regenerate_depreciation_schedule
        a = self._old_asset(suffix="BE5b", category=self.cat_rule)
        d1, s1 = _unwrap(regenerate_depreciation_schedule(a))
        d2, s2 = _unwrap(regenerate_depreciation_schedule(a))
        self.assertEqual(s1, 200)
        self.assertEqual(s2, 200)
        self.assertEqual(d1.get("periods"), d2.get("periods"))
        self.assertGreater(d1.get("periods"), 0)

    # ── [TDD-BE-6] history-safe: asset with an Executed period + months set →
    #    self-heal must NOT override the months/residual already running ───────
    def test_be6_history_safe_no_override(self):
        from assetcore.api.imm00 import regenerate_depreciation_schedule
        # configured with months=12 (user/historic), Category=60.
        a = self._old_asset(suffix="BE6", category=self.cat_rule,
                            method="Straight Line", months=12,
                            residual=5_000_000.0)
        depr_svc.generate_schedule(a, force=True)
        row = frappe.db.get_value(
            _DT_SCHED, {"parent": a, "status": "Pending"}, "name",
            order_by="period_number asc")
        frappe.db.set_value(_DT_SCHED, row, "status", "Executed",
                            update_modified=False)

        months_before = int(frappe.db.get_value(
            _DT_ASSET, a, "total_depreciation_months"))
        residual_before = flt(frappe.db.get_value(_DT_ASSET, a, "residual_value"))

        _data, status = _unwrap(regenerate_depreciation_schedule(a))
        self.assertEqual(status, 200)
        # months/residual already-running must be invariant (inherit no-op).
        self.assertEqual(
            int(frappe.db.get_value(_DT_ASSET, a, "total_depreciation_months")),
            months_before, "Executed-history months must not be overridden")
        self.assertAlmostEqual(
            flt(frappe.db.get_value(_DT_ASSET, a, "residual_value")),
            residual_before, delta=0.01,
            msg="Executed-history residual must not be overridden")
        # no garbage inherit event (months were already present → no-op).
        self.assertEqual(self._ale_count(a), 0)


class TestRegenerateNoInlineCopyGuard(unittest.TestCase):
    """[Grep-guard BR-00-22] api/imm00.py must NOT inline-copy
    total_depreciation_months / residual_value FROM Category — the ONLY allowed
    path is the SoT inherit_depreciation_rules_from_category(...) call."""

    def test_no_inline_category_copy_in_imm00(self):
        import os
        import re
        api_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "api", "imm00.py")
        blob = open(api_file, encoding="utf-8").read()
        # rogue copy = assigning months/residual FROM a `cat`/Category-derived
        # value (the canonical drift signature). The SoT residual formula
        # `residual_pct / 100` must NOT appear in api/imm00.py at all.
        rogue_residual = re.compile(r"residual_pct\s*/\s*100")
        self.assertIsNone(
            rogue_residual.search(blob),
            "api/imm00.py must not re-implement Category residual formula; "
            "use inherit_depreciation_rules_from_category (SoT) only.")
        # months copied from a cat dict (e.g. cat.get('total_depreciation_months')
        # / cat['total_depreciation_months']) assigned to total_depreciation_months.
        rogue_months = re.compile(
            r"total_depreciation_months\s*=\s*[^=\n]*\bcat\b")
        self.assertIsNone(
            rogue_months.search(blob),
            "api/imm00.py must not copy total_depreciation_months from Category "
            "inline; use the SoT helper only.")


# ═════════════════════════════════════════════════════════════════════════════
# bulk_regenerate_by_category — hợp nhất về SoT round-1/2
#   • no-clobber inherit (route 100% qua inherit_depreciation_rules_from_category)
#   • N+1 đóng (1 GROUP BY parent prefetch, KHÔNG count-in-loop)
#   • payload chuẩn hoá khớp compute_all (inherited / skipped_no_rule mới)
#   • preserve-history + idempotent
# TDD — viết TRƯỚC khi sửa service (RED-proven: revert inline-copy / count-in-loop).
# ═════════════════════════════════════════════════════════════════════════════


def _bulk_bare_asset(*, suffix: str, category: str = "", method: str = "",
                     months: int = 0, residual: float = 0.0,
                     gross: float = 50_000_000.0) -> str:
    """Insert an asset in the OPEN transaction (no commit), then re-point at a
    Category via direct db set so a 'missing rule' / user-set state survives until
    bulk_regenerate_by_category runs (mirror compute_all test harness)."""
    doc = frappe.get_doc({
        "doctype": _DT_ASSET,
        "asset_name": f"_Test BulkRegen {suffix}",
        "gross_purchase_amount": gross,
        "depreciation_method": method,
        "total_depreciation_months": months,
        "residual_value": residual,
        "lifecycle_status": "Active",
    })
    doc.flags.ignore_mandatory = True
    doc.flags.ignore_links = True
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    try:
        doc.insert(ignore_permissions=True)
    finally:
        frappe.flags.in_install = prev
    if category:
        frappe.db.set_value(_DT_ASSET, doc.name, "asset_category", category,
                            update_modified=False)
    return doc.name


def _execute_one_period(asset: str) -> None:
    """Generate a schedule for `asset` then mark its first period Executed +
    seed accumulated/book so preserve-history can be asserted as invariant."""
    depr_svc.generate_schedule(asset, force=True)
    row = frappe.db.get_value(
        _DT_SCHED, {"parent": asset, "status": "Pending"}, "name",
        order_by="period_number asc")
    frappe.db.set_value(_DT_SCHED, row, "status", "Executed",
                        update_modified=False)
    frappe.db.set_value(_DT_ASSET, asset, {
        "accumulated_depreciation": 123_456.0,
        "current_book_value": 9_876_544.0,
    }, update_modified=False)


class TestBulkRegenNoClobber(unittest.TestCase):
    """[TDD] bulk_regenerate_by_category must NOT clobber user-entered fields.

    Asset has total_depreciation_months=99 (user-set, != Category 60) + a manual
    residual_value. After bulk → months STAYS 99 ∧ residual PRESERVED (NOT
    overwritten by Category). RED-proven: revert service to inline-copy
    (`asset_doc.total_depreciation_months = cat_months`) → months becomes 60.
    """

    @classmethod
    def setUpClass(cls):
        _ensure_uom()
        cls.cat_rule = _ensure_category(_CAT_DEPR, months=60, residual_pct=10.0)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        _purge_category(_CAT_DEPR)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.db.rollback()
        frappe.set_user("Administrator")

    def test_user_months_and_residual_preserved(self):
        a = _bulk_bare_asset(suffix="NoClobber", category=self.cat_rule,
                             method="Straight Line", months=99,
                             residual=7_777_777.0, gross=80_000_000.0)
        with _suppress_commit():
            depr_svc.bulk_regenerate_by_category(self.cat_rule)

        months_after = int(frappe.db.get_value(
            _DT_ASSET, a, "total_depreciation_months") or 0)
        residual_after = flt(frappe.db.get_value(_DT_ASSET, a, "residual_value"))
        self.assertEqual(
            months_after, 99,
            "user-entered total_depreciation_months must NOT be clobbered by "
            "Category (60); bulk must route through the no-clobber SoT")
        self.assertAlmostEqual(
            residual_after, 7_777_777.0, delta=0.01,
            msg="user-entered residual_value must be preserved (no clobber)")


class TestBulkRegenNoNPlusOne(unittest.TestCase):
    """[TDD] bulk_regenerate_by_category must NOT issue per-asset count queries.

    ROOT CAUSE (pre-optimize): the executed-history check called
    ``frappe.db.count(_DT_SCHED, {parent, status='Executed'})`` ONCE PER ASSET
    inside the loop → query count linear in N (N+1).

    OPTIMIZED CONTRACT (this test pins it, mirror compute_all round-3):
      * EXACTLY ONE GROUP-BY-parent prefetch read on _DT_SCHED runs ONCE before
        the loop (executed_parents set);
      * ZERO per-asset ``frappe.db.count(parent=..)`` calls for the history check.

    RED-proven: revert service to count-in-loop → per_asset_count >= N > 0.
    """

    @classmethod
    def setUpClass(cls):
        _ensure_uom()
        cls.cat_rule = _ensure_category(_CAT_DEPR, months=60, residual_pct=10.0)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        _purge_category(_CAT_DEPR)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.db.rollback()
        frappe.set_user("Administrator")

    @contextlib.contextmanager
    def _query_spy(self):
        real_count = frappe.db.count
        real_get_all = frappe.get_all
        rec = {"per_asset_count": [], "prefetch_groupby": []}

        def _count_spy(doctype, filters=None, *a, **k):
            if doctype == _DT_SCHED and isinstance(filters, dict) \
                    and "parent" in filters:
                rec["per_asset_count"].append(dict(filters))
            return real_count(doctype, filters, *a, **k)

        def _get_all_spy(doctype, *a, **k):
            if doctype == _DT_SCHED and k.get("group_by") == "parent":
                rec["prefetch_groupby"].append(dict(k.get("filters") or {}))
            return real_get_all(doctype, *a, **k)

        frappe.db.count = _count_spy
        frappe.get_all = _get_all_spy
        try:
            yield rec
        finally:
            frappe.db.count = real_count
            frappe.get_all = real_get_all

    def test_no_per_asset_count_for_executed_history(self):
        # >=3 assets same Category, one of them with Executed history.
        _bulk_bare_asset(suffix="N1", category=self.cat_rule, method="", months=0)
        _bulk_bare_asset(suffix="N2", category=self.cat_rule,
                         method="Straight Line", months=12)
        a3 = _bulk_bare_asset(suffix="N3", category=self.cat_rule,
                              method="Straight Line", months=12)
        _execute_one_period(a3)

        with self._query_spy() as rec, _suppress_commit():
            depr_svc.bulk_regenerate_by_category(self.cat_rule)

        self.assertEqual(
            rec["per_asset_count"], [],
            f"executed-history check must use a GROUP-BY prefetch set, NOT "
            f"per-asset frappe.db.count(parent=..); got "
            f"{len(rec['per_asset_count'])}: {rec['per_asset_count']}")
        # exactly one GROUP-BY-parent prefetch (executed set), filtered Executed.
        self.assertEqual(
            len(rec["prefetch_groupby"]), 1,
            f"expected EXACTLY 1 GROUP-BY-parent prefetch on {_DT_SCHED} "
            f"(executed_parents, once); got {len(rec['prefetch_groupby'])}: "
            f"{rec['prefetch_groupby']}")
        self.assertEqual(
            rec["prefetch_groupby"][0].get("status"), "Executed",
            "the single prefetch must filter status='Executed' (preserve-history)")


class TestBulkRegenPayload(unittest.TestCase):
    """[TDD] payload chuẩn hoá khớp compute_all — đủ key + đếm đúng mỗi nhóm.

    Mix dataset (Category has rule):
      P1 — missing rule (method='', months=0) → inherited + regenerated.
      P2 — already configured (method+months) → regenerated (no inherit needed).
      P3 — has >=1 Executed period → skipped_has_history.
      P4 — gross=0 → skipped_no_rule (master-data gap NOT hidden).
    """

    @classmethod
    def setUpClass(cls):
        _ensure_uom()
        cls.cat_rule = _ensure_category(_CAT_DEPR, months=60, residual_pct=10.0)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        _purge_category(_CAT_DEPR)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.db.rollback()
        frappe.set_user("Administrator")

    def test_payload_shape_and_group_counts(self):
        p1 = _bulk_bare_asset(suffix="P1", category=self.cat_rule,
                              method="", months=0)
        _bulk_bare_asset(suffix="P2", category=self.cat_rule,
                         method="Straight Line", months=12)
        p3 = _bulk_bare_asset(suffix="P3", category=self.cat_rule,
                              method="Straight Line", months=12)
        _execute_one_period(p3)
        _bulk_bare_asset(suffix="P4", category=self.cat_rule,
                         method="", months=0, gross=0.0)

        with _suppress_commit():
            res = depr_svc.bulk_regenerate_by_category(self.cat_rule)

        # payload has the 7 standardized keys (inherited + skipped_no_rule added).
        for key in ("category", "total_assets", "inherited", "regenerated",
                    "skipped_has_history", "skipped_no_rule", "errors"):
            self.assertIn(key, res, f"payload missing key {key}")

        self.assertGreaterEqual(res["inherited"], 1, "P1 inherited")
        self.assertGreaterEqual(res["regenerated"], 2, "P1+P2 regenerated")
        self.assertGreaterEqual(res["skipped_has_history"], 1, "P3 history")
        self.assertGreaterEqual(res["skipped_no_rule"], 1, "P4 gross=0 no-rule")

        # P1 inherited Category months (60) since it had none.
        self.assertEqual(
            int(frappe.db.get_value(_DT_ASSET, p1,
                                    "total_depreciation_months") or 0), 60)


class TestBulkRegenPreservesHistory(unittest.TestCase):
    """[TDD] asset with >=1 Executed period → skipped_has_history; accumulated +
    current_book_value + schedule rows BẤT BIẾN after bulk."""

    @classmethod
    def setUpClass(cls):
        _ensure_uom()
        cls.cat_rule = _ensure_category(_CAT_DEPR, months=60, residual_pct=10.0)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        _purge_category(_CAT_DEPR)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.db.rollback()
        frappe.set_user("Administrator")

    def test_executed_history_invariant(self):
        a = _bulk_bare_asset(suffix="Hist", category=self.cat_rule,
                             method="Straight Line", months=12)
        _execute_one_period(a)
        acc_before = flt(frappe.db.get_value(_DT_ASSET, a,
                                             "accumulated_depreciation"))
        book_before = flt(frappe.db.get_value(_DT_ASSET, a, "current_book_value"))
        rows_before = frappe.db.count(_DT_SCHED, {"parent": a})

        with _suppress_commit():
            res = depr_svc.bulk_regenerate_by_category(self.cat_rule)

        self.assertGreaterEqual(res["skipped_has_history"], 1)
        self.assertAlmostEqual(
            flt(frappe.db.get_value(_DT_ASSET, a, "accumulated_depreciation")),
            acc_before, delta=0.01, msg="accumulated must be invariant")
        self.assertAlmostEqual(
            flt(frappe.db.get_value(_DT_ASSET, a, "current_book_value")),
            book_before, delta=0.01, msg="current_book_value must be invariant")
        self.assertEqual(
            frappe.db.count(_DT_SCHED, {"parent": a}), rows_before,
            "schedule rows must be invariant (NOT regenerated)")


class TestBulkRegenIdempotent(unittest.TestCase):
    """[TDD] running bulk twice → 2nd run inherited==0 ∧ regenerated==0, no dup
    schedule rows (generate_schedule force=False skips on existing rows)."""

    @classmethod
    def setUpClass(cls):
        _ensure_uom()
        cls.cat_rule = _ensure_category(_CAT_DEPR, months=60, residual_pct=10.0)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        _purge_category(_CAT_DEPR)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.db.rollback()
        frappe.set_user("Administrator")

    def test_second_run_no_op(self):
        a = _bulk_bare_asset(suffix="Idem", category=self.cat_rule,
                             method="", months=0)
        with _suppress_commit():
            res1 = depr_svc.bulk_regenerate_by_category(self.cat_rule)
            rows_after_1 = frappe.db.count(_DT_SCHED, {"parent": a})
            res2 = depr_svc.bulk_regenerate_by_category(self.cat_rule)
            rows_after_2 = frappe.db.count(_DT_SCHED, {"parent": a})

        self.assertGreaterEqual(res1["inherited"], 1, "1st run inherits")
        self.assertGreaterEqual(res1["regenerated"], 1, "1st run generates")
        self.assertEqual(res2["inherited"], 0, "2nd run: nothing left to inherit")
        self.assertEqual(res2["regenerated"], 0,
                         "2nd run: schedule already exists → no regenerate")
        self.assertEqual(rows_after_1, rows_after_2,
                         "2nd run must NOT create duplicate schedule rows")


class TestBulkRegenNoInlineCopyGuard(unittest.TestCase):
    """[Grep-guard] bulk_regenerate_by_category body must NOT inline-copy the
    Category rule down to the asset — the ONLY allowed path is the SoT
    inherit_depreciation_rules_from_category(...) call (mirror round-1 guard for
    the regenerate path)."""

    def test_no_inline_category_copy_in_bulk_body(self):
        import os
        import re
        svc_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "services", "depreciation.py")
        blob = open(svc_file, encoding="utf-8").read()

        # Extract the bulk_regenerate_by_category function body (up to the next
        # top-level `def `) so the guard is scoped to THAT function only.
        m = re.search(
            r"\ndef bulk_regenerate_by_category\(.*?\):\n(.*?)\n(?=def \w)",
            blob, re.DOTALL)
        self.assertIsNotNone(m, "bulk_regenerate_by_category not found")
        body = m.group(1)

        # (1) must call the SoT inherit helper.
        self.assertIn(
            "inherit_depreciation_rules_from_category", body,
            "bulk must route through the SoT inherit helper")

        # (2) NO inline assignment of the 4 rule fields FROM Category onto the
        # asset_doc (the canonical clobber/drift signature).
        rogue = re.compile(
            r"asset_doc\.(depreciation_method|total_depreciation_months|"
            r"depreciation_frequency|residual_value)\s*=")
        offenders = rogue.findall(body)
        self.assertEqual(
            offenders, [],
            f"bulk_regenerate_by_category must NOT inline-assign rule fields onto "
            f"asset_doc (route via SoT only); found assignments to: {offenders}")

        # (3) NO Category residual formula copy in the body.
        self.assertIsNone(
            re.search(r"residual_pct\s*/\s*100", body),
            "bulk must not re-implement the Category residual formula inline")


# ─────────────────────────────────────────────────────────────────────────────
# RC-05 (Round-4): bulk_regenerate_by_category consolidated onto the SoT.
# TDD (CLAUDE.md §17) — written BEFORE the service change. The bulk path must
# route 100% through inherit_depreciation_rules_from_category (no-clobber),
# close N+1 (1 GROUP-BY-parent prefetch, no per-asset db.count), and return the
# 7-key payload that mirrors compute_all.
# ─────────────────────────────────────────────────────────────────────────────

_CAT_BULK = "_TestCatBulkRegenSoT"        # Category WITH rule (months=60, 10%)
_CAT_BULK_NORULE = "_TestCatBulkRegenNoRule"  # Category WITHOUT rule (months=0)


class _BulkRegenBase(unittest.TestCase):
    """Shared seed + isolation for the bulk_regenerate_by_category test suite.

    bulk_regenerate_by_category() commits internally; _suppress_commit keeps every
    side-effect in the open transaction so tearDown rollback restores isolation
    on the shared DB (same pattern as the compute_all suite)."""

    @classmethod
    def setUpClass(cls):
        _ensure_uom()
        cls.cat_rule = _ensure_category(_CAT_BULK, months=60, residual_pct=10.0)
        cls.cat_norule = _ensure_category(_CAT_BULK_NORULE, months=0,
                                          residual_pct=0.0)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        _purge_category(_CAT_BULK)
        _purge_category(_CAT_BULK_NORULE)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.db.rollback()
        frappe.set_user("Administrator")

    def _bare_asset(self, *, suffix: str, category: str = "",
                    method: str = "", months: int = 0,
                    residual: float = 0.0,
                    gross: float = 50_000_000.0) -> str:
        """Insert an asset in the OPEN transaction (no commit). Re-point at the
        Category via raw db set so a 'missing months' state survives until the
        bulk runs (mirrors the compute_all sibling test)."""
        doc = frappe.get_doc({
            "doctype": _DT_ASSET,
            "asset_name": f"_Test BulkRegen {suffix}",
            "gross_purchase_amount": gross,
            "depreciation_method": method,
            "total_depreciation_months": months,
            "residual_value": residual,
            "lifecycle_status": "Active",
        })
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_links = True
        prev = frappe.flags.in_install
        frappe.flags.in_install = "frappe"
        try:
            doc.insert(ignore_permissions=True)
        finally:
            frappe.flags.in_install = prev
        if category:
            frappe.db.set_value(_DT_ASSET, doc.name, "asset_category", category,
                                update_modified=False)
        return doc.name

    def _seed_executed(self, asset: str) -> None:
        """Generate a schedule for `asset`, mark its first period Executed and
        seed a non-zero accumulated so preserve-history is observable."""
        depr_svc.generate_schedule(asset, force=True)
        row = frappe.db.get_value(
            _DT_SCHED, {"parent": asset, "status": "Pending"}, "name",
            order_by="period_number asc")
        frappe.db.set_value(_DT_SCHED, row, "status", "Executed",
                            update_modified=False)
        frappe.db.set_value(_DT_ASSET, asset, {
            "accumulated_depreciation": 123_456.0,
            "current_book_value": 49_876_544.0,
        }, update_modified=False)


class TestBulkRegenNoClobber(_BulkRegenBase):
    """[TDD RC-05] bulk_regenerate_by_category must NOT overwrite user-entered
    rule fields. RED-proven by reverting to the inline 4-line copy (months would
    become cat_months=60 instead of the user-set 99)."""

    def test_user_months_and_residual_preserved(self):
        # User set months=99 + residual=7tr by hand; Category says months=60 / 10%.
        asset = self._bare_asset(
            suffix="NoClobber", category=self.cat_rule,
            method="Straight Line", months=99, residual=7_000_000.0,
            gross=50_000_000.0)

        with _suppress_commit():
            res = depr_svc.bulk_regenerate_by_category(self.cat_rule)

        self.assertNotIn("error", res, res)
        months = int(frappe.db.get_value(
            _DT_ASSET, asset, "total_depreciation_months") or 0)
        residual = flt(frappe.db.get_value(
            _DT_ASSET, asset, "residual_value") or 0)
        self.assertEqual(months, 99,
                         "user-set months MUST survive bulk (no clobber)")
        self.assertEqual(residual, 7_000_000.0,
                         "user-set residual MUST survive bulk (no clobber)")


class TestBulkRegenNoNPlusOne(_BulkRegenBase):
    """[TDD RC-05] executed-history check must NOT call frappe.db.count per-asset;
    a single GROUP-BY-parent prefetch serves the whole loop. RED-proven by
    reverting to count-in-loop (per_asset_count length == N)."""

    @contextlib.contextmanager
    def _query_spy(self):
        real_count = frappe.db.count
        real_get_all = frappe.get_all
        rec = {"per_asset_count": [], "prefetch_groupby": []}

        def _count_spy(doctype, filters=None, *a, **k):
            if doctype == _DT_SCHED and isinstance(filters, dict) \
                    and "parent" in filters:
                rec["per_asset_count"].append(dict(filters))
            return real_count(doctype, filters, *a, **k)

        def _get_all_spy(doctype, *a, **k):
            if doctype == _DT_SCHED and k.get("group_by") == "parent":
                rec["prefetch_groupby"].append(dict(k.get("filters") or {}))
            return real_get_all(doctype, *a, **k)

        frappe.db.count = _count_spy
        frappe.get_all = _get_all_spy
        try:
            yield rec
        finally:
            frappe.db.count = real_count
            frappe.get_all = real_get_all

    def test_no_per_asset_count_in_loop(self):
        # N assets under the same Category — count MUST stay constant, not O(N).
        for i in range(3):
            self._bare_asset(suffix=f"NPlus1-{i}", category=self.cat_rule,
                             method="", months=0)

        with self._query_spy() as rec, _suppress_commit():
            depr_svc.bulk_regenerate_by_category(self.cat_rule)

        self.assertEqual(
            rec["per_asset_count"], [],
            f"expected 0 per-asset frappe.db.count(parent=..) calls in bulk "
            f"(replaced by 1 GROUP-BY prefetch); got "
            f"{len(rec['per_asset_count'])}: {rec['per_asset_count']}")
        # exactly ONE GROUP-BY-parent prefetch (executed-history set), once,
        # before the loop — independent of N.
        self.assertEqual(
            len(rec["prefetch_groupby"]), 1,
            f"expected EXACTLY 1 GROUP-BY-parent prefetch on {_DT_SCHED} "
            f"(executed-history); got {len(rec['prefetch_groupby'])}: "
            f"{rec['prefetch_groupby']}")
        self.assertEqual(
            rec["prefetch_groupby"][0].get("status"), "Executed",
            "the single prefetch must filter status='Executed'")


class TestBulkRegenPayload(_BulkRegenBase):
    """[TDD RC-05] 7-key payload mirroring compute_all, each group counted right.

    Dataset under one rule-Category:
      A1 — missing rule, Category HAS rule        → inherited + regenerated.
      A2 — has an Executed period (history)       → skipped_has_history.
      A3 — gross=0                                 → skipped_no_rule.
    Plus A4 under a no-rule Category               → skipped_no_rule.
    """

    def test_payload_shape_and_group_counts(self):
        a1 = self._bare_asset(suffix="PA1", category=self.cat_rule,
                              method="", months=0)
        a2 = self._bare_asset(suffix="PA2", category=self.cat_rule,
                              method="Straight Line", months=12)
        self._seed_executed(a2)
        a3 = self._bare_asset(suffix="PA3", category=self.cat_rule,
                              method="", months=0, gross=0.0)

        with _suppress_commit():
            res = depr_svc.bulk_regenerate_by_category(self.cat_rule)

        for key in ("category", "total_assets", "inherited", "regenerated",
                    "skipped_has_history", "skipped_no_rule", "errors"):
            self.assertIn(key, res, f"payload missing key {key}")
        self.assertEqual(res["category"], self.cat_rule)
        self.assertGreaterEqual(res["inherited"], 1, "A1 inherited")
        self.assertGreaterEqual(res["regenerated"], 1, "A1 regenerated")
        self.assertGreaterEqual(res["skipped_has_history"], 1, "A2 history")
        self.assertGreaterEqual(res["skipped_no_rule"], 1, "A3 gross=0 no-rule")
        # A2 (executed) must NOT be regenerated nor inherited.
        a2_months_unchanged = int(frappe.db.get_value(
            _DT_ASSET, a2, "total_depreciation_months") or 0)
        self.assertEqual(a2_months_unchanged, 12,
                         "A2 with history must stay untouched")
        _ = a1, a3

    def test_no_rule_category_skips(self):
        self._bare_asset(suffix="PB1", category=self.cat_norule,
                         method="", months=0)
        with _suppress_commit():
            res = depr_svc.bulk_regenerate_by_category(self.cat_norule)
        self.assertGreaterEqual(res["skipped_no_rule"], 1,
                                "asset under no-rule Category → skipped_no_rule")
        self.assertEqual(res["inherited"], 0, "no rule to inherit")
        self.assertEqual(res["regenerated"], 0, "nothing generated")


class TestBulkRegenPreservesHistory(_BulkRegenBase):
    """[TDD RC-05] an asset with >=1 Executed period is preserved: accumulated +
    book value + schedule rows are invariant; it counts as skipped_has_history."""

    def test_executed_asset_invariant(self):
        asset = self._bare_asset(suffix="Hist", category=self.cat_rule,
                                 method="Straight Line", months=12)
        self._seed_executed(asset)
        acc_before = flt(frappe.db.get_value(
            _DT_ASSET, asset, "accumulated_depreciation"))
        book_before = flt(frappe.db.get_value(
            _DT_ASSET, asset, "current_book_value"))
        rows_before = frappe.db.count(_DT_SCHED, {"parent": asset})

        with _suppress_commit():
            res = depr_svc.bulk_regenerate_by_category(self.cat_rule)

        self.assertGreaterEqual(res["skipped_has_history"], 1)
        self.assertEqual(
            flt(frappe.db.get_value(_DT_ASSET, asset, "accumulated_depreciation")),
            acc_before, "accumulated_depreciation must be invariant")
        self.assertEqual(
            flt(frappe.db.get_value(_DT_ASSET, asset, "current_book_value")),
            book_before, "current_book_value must be invariant")
        self.assertEqual(
            frappe.db.count(_DT_SCHED, {"parent": asset}), rows_before,
            "schedule rows must be invariant (no regen on history asset)")


class TestBulkRegenIdempotent(_BulkRegenBase):
    """[TDD RC-05] running bulk twice → 2nd run inherited==0 ∧ regenerated==0,
    no duplicate schedule rows."""

    def test_second_run_inherited_and_regenerated_zero(self):
        asset = self._bare_asset(suffix="Idem", category=self.cat_rule,
                                 method="", months=0)
        with _suppress_commit():
            d1 = depr_svc.bulk_regenerate_by_category(self.cat_rule)
            self.assertGreaterEqual(d1["inherited"], 1)
            self.assertGreaterEqual(d1["regenerated"], 1)
            rows_after_1 = frappe.db.count(_DT_SCHED, {"parent": asset})

            d2 = depr_svc.bulk_regenerate_by_category(self.cat_rule)

        self.assertEqual(d2["inherited"], 0,
                         "2nd run: rule already inherited → inherited=0")
        self.assertEqual(d2["regenerated"], 0,
                         "2nd run: schedule already exists → regenerated=0")
        self.assertEqual(
            frappe.db.count(_DT_SCHED, {"parent": asset}), rows_after_1,
            "no duplicate schedule rows on 2nd run")
