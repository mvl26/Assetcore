# Copyright (c) 2026, AssetCore Team
"""IMM-00 BR-00-25 (RC-08) — Depreciation PAUSE + RESCHEDULE on Out of Service.

TDD-first (CLAUDE.md §17) for the phantom-catch-up root-cause fix.

Invariants under test (INV-DEP-OOS-1..8, Core Doc 04 §II.1e):
  TC-OOS-01 PAUSE: asset Out of Service → run_due_depreciation executes 0 rows;
            accumulated_depreciation / current_book_value invariant.
  TC-OOS-02 NO PHANTOM CATCH-UP (bug chính): OoS → Active reschedules every Pending
            row → next run_due_depreciation(today) does NOT sweep idle periods.
  TC-OOS-03 RESCHEDULE: every Pending scheduled_date shifts by exactly oos_days;
            count(Pending) + sum(depreciation_amount) invariant; period_number kept.
  TC-OOS-04 Executed/Cancelled rows are NOT touched.
  TC-OOS-05 IDEMPOTENT: re-calling transition Active→Active (no-op via guard) does
            NOT double-shift.
  TC-OOS-06 AUDIT: one OoS→Active cycle emits ≥1 ALE 'out_of_service' (pause note) +
            ≥1 ALE 'restored' + ≥1 IMM Audit Trail; audit failure does NOT break
            the transition.
  TC-OOS-07 FALLBACK: no downtime log + no ALE → _resolve_oos_start_date None →
            reschedule is a no-op, NO raise.
  TC-OOS-08 REGRESSION decommission (round 8): Out of Service → Decommissioned still
            cancels Pending rows (not swallowed by reschedule).
  TC-OOS-09 grep/AST guard: executor keeps 'Out of Service' exclude; reschedule has
            no per-row SELECT (N+1 guard).

Run:
  bench --site miyano run-tests --app assetcore \
      --module assetcore.tests.depreciation.test_depreciation_oos
"""
from __future__ import annotations

import unittest

import frappe
from frappe.utils import add_days, flt, getdate, nowdate

from assetcore.services import depreciation as depr_svc
from assetcore.services import imm00 as imm00_svc
from assetcore.services.imm00 import transition_asset_status
from assetcore.tests._helpers._asset_cleanup import purge_asset, decommission_via_closure
from frappe.tests.utils import FrappeTestCase

_DT_ASSET = "AC Asset"
_DT_SCHED = "AC Asset Depreciation Schedule"
_DT_DOWNTIME = "AC Asset Downtime Log"
_DT_ALE = "Asset Lifecycle Event"
_DT_AUDIT = "IMM Audit Trail"

_GROSS = 120_000_000.0
_RESIDUAL = 0.0


def _ensure_uom() -> None:
    if not frappe.db.exists("AC UOM", "Cái"):
        frappe.get_doc({"doctype": "AC UOM", "uom_name": "Cái"}).insert(
            ignore_permissions=True
        )


def _make_active_asset(
    *, suffix: str, months: int = 12, gross: float = _GROSS,
    start_date: str | None = None,
) -> str:
    """Insert an Active AC Asset with a depreciation schedule (Pending rows).

    ``start_date`` defaults to ~4 months before today so the monthly Pending
    periods straddle "now" — making the OoS window genuinely bracket some
    periods (required to expose phantom catch-up). Fixed dates like 2024-01-01
    leave every period far in the past, where a +oos_days shift still lands
    before today and cannot distinguish the fix from the bug.
    """
    _ensure_uom()
    start = start_date or add_days(nowdate(), -120)
    doc = frappe.get_doc({
        "doctype": _DT_ASSET,
        "asset_name": f"_Test OOS Depr {suffix}",
        "gross_purchase_amount": gross,
        "residual_value": _RESIDUAL,
        "depreciation_method": "Straight Line",
        "total_depreciation_months": months,
        "depreciation_frequency": "Monthly",
        "depreciation_start_date": start,
        "in_service_date": start,
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
    depr_svc.generate_schedule(doc.name, force=True)
    return doc.name


def _pending_rows(asset: str) -> list[dict]:
    return frappe.get_all(
        _DT_SCHED,
        filters={"parent": asset, "parenttype": _DT_ASSET, "status": "Pending"},
        fields=["name", "period_number", "scheduled_date", "depreciation_amount"],
        order_by="period_number asc",
        limit_page_length=0,
    )


def _rows_by_status(asset: str, status: str) -> list[dict]:
    return frappe.get_all(
        _DT_SCHED,
        filters={"parent": asset, "parenttype": _DT_ASSET, "status": status},
        fields=["name", "period_number", "scheduled_date", "depreciation_amount"],
        order_by="period_number asc",
        limit_page_length=0,
    )


def _acc(asset: str) -> float:
    return flt(frappe.db.get_value(_DT_ASSET, asset, "accumulated_depreciation"))


def _book(asset: str) -> float:
    return flt(frappe.db.get_value(_DT_ASSET, asset, "current_book_value"))


def _backdate_oos_downtime(asset: str, start: str) -> None:
    """Back-date the OoS downtime log start_time to simulate elapsed OoS time.

    The real transition_asset_status(... 'Out of Service') opens an
    AC Asset Downtime Log (reason='Hỏng hóc') at now() via _sync_downtime_log.
    To simulate an asset that has been OoS for `start..today`, back-date that
    log's start_time (the SoT anchor read by _resolve_oos_start_date). Call this
    AFTER transitioning into Out of Service.
    """
    name = frappe.db.get_value(
        _DT_DOWNTIME,
        {"asset": asset, "reason": "Hỏng hóc"},
        "name", order_by="start_time desc",
    )
    if name:
        frappe.db.set_value(_DT_DOWNTIME, name, "start_time", f"{start} 08:00:00",
                            update_modified=False)
        frappe.db.commit()


class TestDepreciationOosPauseReschedule(FrappeTestCase):
    """BR-00-25 PAUSE + RESCHEDULE invariants (service layer)."""

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
        name = _make_active_asset(**kw)
        self._assets.append(name)
        return name

    # ── TC-OOS-01 PAUSE ───────────────────────────────────────────────────────
    def test_oos_01_pause_executor_no_run_book_invariant(self):
        asset = self._new(suffix="01", months=6)
        transition_asset_status(asset, "Out of Service", actor="Administrator",
                                reason="Hỏng hóc tạm ngừng")
        acc_before, book_before = _acc(asset), _book(asset)
        # Run executor far in the future while OoS — nothing must execute.
        res1 = depr_svc.run_due_depreciation(as_of="2099-12-31", asset=asset)
        res2 = depr_svc.run_due_depreciation(as_of="2099-12-31", asset=asset)
        self.assertEqual(res1["executed_rows"], 0)
        self.assertEqual(res2["executed_rows"], 0)
        self.assertEqual(_acc(asset), acc_before)
        self.assertEqual(_book(asset), book_before)

    # ── TC-OOS-02 NO PHANTOM CATCH-UP (bug chính) ─────────────────────────────
    def test_oos_02_no_phantom_catch_up_after_restore(self):
        asset = self._new(suffix="02", months=12)
        # Anchor OoS start to 95 days ago so ≥3 monthly periods fall inside window.
        oos_start = add_days(nowdate(), -95)
        transition_asset_status(asset, "Out of Service", actor="Administrator")
        _backdate_oos_downtime(asset, oos_start)
        acc_before = _acc(asset)
        # Periods overdue during OoS (scheduled_date < today).
        overdue_before = frappe.db.count(_DT_SCHED, {
            "parent": asset, "parenttype": _DT_ASSET, "status": "Pending",
            "scheduled_date": ["<", nowdate()],
        })
        self.assertGreaterEqual(overdue_before, 1,
                                "fixture must have ≥1 overdue Pending period")
        # Restore → reschedule shifts every Pending past today.
        transition_asset_status(asset, "Active", actor="Administrator")
        # Now run executor at today → must NOT sweep the idle periods.
        res = depr_svc.run_due_depreciation(as_of=nowdate(), asset=asset)
        self.assertEqual(res["executed_rows"], 0,
                         "phantom catch-up: idle periods executed in one sweep")
        self.assertEqual(_acc(asset), acc_before,
                         "delta_accumulated must be 0 for periods inside OoS window")

    # ── TC-OOS-03 RESCHEDULE correct gap ──────────────────────────────────────
    def test_oos_03_reschedule_shifts_by_oos_days(self):
        asset = self._new(suffix="03", months=6)
        oos_start = add_days(nowdate(), -40)
        transition_asset_status(asset, "Out of Service", actor="Administrator")
        _backdate_oos_downtime(asset, oos_start)
        before = _pending_rows(asset)
        count_before = len(before)
        sum_before = sum(flt(r["depreciation_amount"]) for r in before)
        dates_before = {r["period_number"]: getdate(r["scheduled_date"]) for r in before}

        transition_asset_status(asset, "Active", actor="Administrator")
        oos_days = (getdate(nowdate()) - getdate(oos_start)).days

        after = _pending_rows(asset)
        self.assertEqual(len(after), count_before, "count(Pending) changed")
        self.assertEqual(sum(flt(r["depreciation_amount"]) for r in after), sum_before,
                         "sum(depreciation_amount Pending) changed")
        for r in after:
            expected = add_days(dates_before[r["period_number"]], oos_days)
            self.assertEqual(getdate(r["scheduled_date"]), getdate(expected),
                             f"period {r['period_number']} not shifted by oos_days")

    # ── TC-OOS-04 Executed/Cancelled invariant ────────────────────────────────
    def test_oos_04_executed_and_cancelled_untouched(self):
        asset = self._new(suffix="04", months=6)
        rows = frappe.get_all(
            _DT_SCHED,
            filters={"parent": asset, "parenttype": _DT_ASSET},
            fields=["name", "period_number"], order_by="period_number asc",
            limit_page_length=0,
        )
        # Mark period 1 Executed, period 2 Cancelled (manual setup).
        frappe.db.set_value(_DT_SCHED, rows[0]["name"],
                            {"status": "Executed", "executed_on": "2024-02-01"},
                            update_modified=False)
        frappe.db.set_value(_DT_SCHED, rows[1]["name"], "status", "Cancelled",
                            update_modified=False)
        frappe.db.commit()
        exec_before = _rows_by_status(asset, "Executed")
        canc_before = _rows_by_status(asset, "Cancelled")

        oos_start = add_days(nowdate(), -30)
        transition_asset_status(asset, "Out of Service", actor="Administrator")
        _backdate_oos_downtime(asset, oos_start)
        transition_asset_status(asset, "Active", actor="Administrator")

        self.assertEqual(_rows_by_status(asset, "Executed"), exec_before,
                         "Executed rows mutated by reschedule")
        self.assertEqual(_rows_by_status(asset, "Cancelled"), canc_before,
                         "Cancelled rows mutated by reschedule")

    # ── TC-OOS-05 IDEMPOTENT (no double-shift) ────────────────────────────────
    def test_oos_05_idempotent_no_double_shift(self):
        asset = self._new(suffix="05", months=6)
        oos_start = add_days(nowdate(), -40)
        transition_asset_status(asset, "Out of Service", actor="Administrator")
        _backdate_oos_downtime(asset, oos_start)
        transition_asset_status(asset, "Active", actor="Administrator")
        dates_after_first = {r["period_number"]: getdate(r["scheduled_date"])
                             for r in _pending_rows(asset)}
        # Re-call transition Active→Active — guard prev==to must no-op (no re-shift).
        transition_asset_status(asset, "Active", actor="Administrator")
        dates_after_second = {r["period_number"]: getdate(r["scheduled_date"])
                              for r in _pending_rows(asset)}
        self.assertEqual(dates_after_second, dates_after_first,
                         "double-shift: Active→Active re-call moved Pending dates")

    # ── TC-OOS-06 AUDIT ───────────────────────────────────────────────────────
    def test_oos_06_audit_events_on_cycle(self):
        asset = self._new(suffix="06", months=6)
        oos_start = add_days(nowdate(), -30)
        transition_asset_status(asset, "Out of Service", actor="Administrator")
        _backdate_oos_downtime(asset, oos_start)
        transition_asset_status(asset, "Active", actor="Administrator")

        ale_oos = frappe.db.count(_DT_ALE, {"asset": asset, "event_type": "out_of_service"})
        ale_restored = frappe.db.count(_DT_ALE, {"asset": asset, "event_type": "restored"})
        audit = frappe.db.count(_DT_AUDIT, {"asset": asset})
        self.assertGreaterEqual(ale_oos, 1, "missing ALE out_of_service (pause)")
        self.assertGreaterEqual(ale_restored, 1, "missing ALE restored (resume)")
        self.assertGreaterEqual(audit, 1, "missing IMM Audit Trail entry")

    def test_oos_06b_audit_failure_does_not_break_reschedule(self):
        # The reschedule helper's audit/lifecycle write is best-effort: an
        # exception there must NOT propagate (still returns rescheduled count, so
        # the calling transition completes). Exercise the helper directly with its
        # audit patched to raise — the main transition's own (mandatory) audit is
        # intentionally NOT best-effort and is out of scope here.
        asset = self._new(suffix="06b", months=6)
        oos_start = add_days(nowdate(), -30)
        transition_asset_status(asset, "Out of Service", actor="Administrator")
        _backdate_oos_downtime(asset, oos_start)
        frappe.db.set_value(_DT_ASSET, asset, "lifecycle_status", "Active")

        orig = imm00_svc.create_lifecycle_event

        def boom(*a, **kw):
            raise RuntimeError("audit boom")

        imm00_svc.create_lifecycle_event = boom
        try:
            res = imm00_svc._reschedule_pending_depreciation_on_restore(asset)
        finally:
            imm00_svc.create_lifecycle_event = orig
        # Reschedule itself succeeded (rows shifted) despite the audit blowing up.
        self.assertGreaterEqual(res["rescheduled"], 1,
                                "audit failure swallowed the reschedule result")

    # ── TC-OOS-07 FALLBACK (no anchor) ────────────────────────────────────────
    def test_oos_07_fallback_no_anchor_no_raise(self):
        asset = self._new(suffix="07", months=6)
        # No downtime log, and we delete any ALE out_of_service to remove the
        # fallback anchor → _resolve_oos_start_date must return None safely.
        # Directly call the helper after manually flipping status (no event).
        frappe.db.set_value(_DT_ASSET, asset, "lifecycle_status", "Out of Service")
        frappe.db.sql(
            "DELETE FROM `tabAsset Lifecycle Event` "
            "WHERE asset=%s AND event_type='out_of_service'", (asset,))
        frappe.db.commit()
        # No raise; rescheduled=0.
        res = imm00_svc._reschedule_pending_depreciation_on_restore(asset)
        self.assertEqual(res["rescheduled"], 0)

    # ── TC-OOS-08 REGRESSION decommission round-8 ─────────────────────────────
    def test_oos_08_decommission_still_cancels_pending(self):
        asset = self._new(suffix="08", months=6)
        oos_start = add_days(nowdate(), -10)
        transition_asset_status(asset, "Out of Service", actor="Administrator")
        _backdate_oos_downtime(asset, oos_start)
        pending_before = frappe.db.count(_DT_SCHED, {
            "parent": asset, "parenttype": _DT_ASSET, "status": "Pending"})
        self.assertGreaterEqual(pending_before, 1)
        # Out of Service → Decommissioned must cancel Pending (not reschedule).
        # IMM-14 GATE: đi qua closure flow (transition vẫn cancel Pending).
        decommission_via_closure(asset)
        self.assertEqual(
            frappe.db.count(_DT_SCHED, {
                "parent": asset, "parenttype": _DT_ASSET, "status": "Pending"}),
            0, "Pending periods not cancelled on decommission")
        self.assertEqual(
            frappe.db.count(_DT_SCHED, {
                "parent": asset, "parenttype": _DT_ASSET, "status": "Cancelled"}),
            pending_before, "decommission did not cancel exactly the Pending rows")

    # ── TC-OOS-08b no-config / 0 pending no-op ────────────────────────────────
    def test_oos_08b_no_pending_no_op(self):
        asset = self._new(suffix="08b", months=6)
        # Cancel every Pending row → reschedule must no-op without error.
        frappe.db.sql(
            "UPDATE `tabAC Asset Depreciation Schedule` SET status='Cancelled' "
            "WHERE parent=%s AND parenttype='AC Asset' AND status='Pending'",
            (asset,))
        frappe.db.commit()
        # Provide a valid OoS anchor via ALE so _resolve_oos_start_date is not None
        # — the no-op must come from "0 Pending rows", not a missing anchor.
        oos_start = add_days(nowdate(), -30)
        imm00_svc.create_lifecycle_event(
            asset=asset, event_type="out_of_service", actor="Administrator",
            root_doctype=_DT_ASSET, root_record=asset, notes="oos")
        frappe.db.set_value(_DT_ASSET, asset, "lifecycle_status", "Out of Service")
        frappe.db.commit()
        res = imm00_svc._reschedule_pending_depreciation_on_restore(asset)
        self.assertEqual(res["rescheduled"], 0)
        _ = oos_start  # documents intent; anchor resolves via ALE creation


class TestDepreciationOosGuards(FrappeTestCase):
    """TC-OOS-09 — source guards (executor exclude kept; no N+1 in reschedule)."""

    def test_oos_09a_executor_keeps_out_of_service_exclude(self):
        import inspect
        src = inspect.getsource(depr_svc.run_due_depreciation)
        self.assertIn("Out of Service", src,
                      "executor must keep lifecycle_status NOT IN (...Out of Service...)")
        self.assertIn("lifecycle_status NOT IN", src)

    def test_oos_09b_reschedule_no_per_row_select(self):
        import inspect
        src = inspect.getsource(
            imm00_svc._reschedule_pending_depreciation_on_restore)
        # The Pending set is fetched once via get_all; the per-row loop must only
        # set_value (no SELECT/get_all/db.sql inside the loop body).
        self.assertEqual(src.count("frappe.get_all"), 1,
                         "reschedule must fetch Pending rows in a single batch")
        self.assertNotIn("frappe.db.sql", src,
                         "reschedule must not issue raw SQL per row")


# ── INV-ALE-RESTORE-1..4 — Out of Service → Active emits exactly ONE 'restored' ──
#
# Root cause (before fix): the OoS→Active transition emitted BOTH
#   * 'activated' (parent transition via _lifecycle_event_for('Active'))
#   * 'restored'  (reschedule helper's own create_lifecycle_event)
# → double-emit when there ARE Pending periods to reschedule; and a single
# MISLABELLED 'activated' when there are NONE (reschedule returns early).
# Fix: _lifecycle_event_for(to, from) returns 'restored' for the OoS→Active edge
# (single SoT), and the reschedule helper no longer emits a lifecycle event.
class TestOosRestoreLifecycleLabel(FrappeTestCase):
    """INV-ALE-RESTORE-1..4 — restore-after-OoS labels exactly one 'restored'."""

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
        name = _make_active_asset(**kw)
        self._assets.append(name)
        return name

    def _count_ale(self, asset: str, event_type: str) -> int:
        return frappe.db.count(_DT_ALE, {"asset": asset, "event_type": event_type})

    # ── TC-ALE-RST-01 — BUG CHÍNH: OoS→Active with Pending periods ────────────
    def test_ale_rst_01_oos_to_active_with_pending_single_restored(self):
        asset = self._new(suffix="rst01", months=6)
        oos_start = add_days(nowdate(), -30)
        transition_asset_status(asset, "Out of Service", actor="Administrator")
        _backdate_oos_downtime(asset, oos_start)
        # Sanity: there ARE Pending periods to reschedule (exposes double-emit).
        self.assertGreaterEqual(
            frappe.db.count(_DT_SCHED, {
                "parent": asset, "parenttype": _DT_ASSET, "status": "Pending"}), 1)
        transition_asset_status(asset, "Active", actor="Administrator")
        self.assertEqual(self._count_ale(asset, "restored"), 1,
                         "OoS→Active must emit exactly ONE 'restored'")
        self.assertEqual(self._count_ale(asset, "activated"), 0,
                         "OoS→Active must emit ZERO 'activated' (mislabel/double-emit)")

    # ── TC-ALE-RST-02 — consistency when NO Pending periods exist ─────────────
    def test_ale_rst_02_oos_to_active_no_pending_still_single_restored(self):
        asset = self._new(suffix="rst02", months=6)
        oos_start = add_days(nowdate(), -30)
        transition_asset_status(asset, "Out of Service", actor="Administrator")
        _backdate_oos_downtime(asset, oos_start)
        # Remove every Pending row → reschedule helper returns early. Before fix
        # the early-return path left only the mislabelled parent 'activated'.
        frappe.db.sql(
            "UPDATE `tabAC Asset Depreciation Schedule` SET status='Cancelled' "
            "WHERE parent=%s AND parenttype='AC Asset' AND status='Pending'",
            (asset,))
        frappe.db.commit()
        transition_asset_status(asset, "Active", actor="Administrator")
        self.assertEqual(self._count_ale(asset, "restored"), 1,
                         "OoS→Active (no Pending) must still emit ONE 'restored'")
        self.assertEqual(self._count_ale(asset, "activated"), 0,
                         "OoS→Active (no Pending) must emit ZERO 'activated'")

    # ── TC-ALE-RST-03 — no-regression repair path (Under Repair→Active) ───────
    def test_ale_rst_03_repair_path_stays_activated(self):
        asset = self._new(suffix="rst03", months=6)
        transition_asset_status(asset, "Under Repair", actor="Administrator")
        transition_asset_status(asset, "Active", actor="Administrator")
        self.assertEqual(self._count_ale(asset, "activated"), 1,
                         "Under Repair→Active must stay 'activated' (test_imm09:839)")
        self.assertEqual(self._count_ale(asset, "restored"), 0,
                         "Under Repair→Active must NOT emit 'restored'")

    # ── TC-ALE-RST-04 — no-regression calibration path (Calibrating→Active) ───
    def test_ale_rst_04_calibration_path_stays_activated(self):
        asset = self._new(suffix="rst04", months=6)
        transition_asset_status(asset, "Calibrating", actor="Administrator")
        transition_asset_status(asset, "Active", actor="Administrator")
        self.assertEqual(self._count_ale(asset, "activated"), 1,
                         "Calibrating→Active must stay 'activated' (test_imm11:1317)")
        self.assertEqual(self._count_ale(asset, "restored"), 0,
                         "Calibrating→Active must NOT emit 'restored'")

    # ── TC-ALE-RST-05 — unit _lifecycle_event_for(to, from) ───────────────────
    def test_ale_rst_05_lifecycle_event_for_from_aware(self):
        f = imm00_svc._lifecycle_event_for
        self.assertEqual(f("Active", "Out of Service"), "restored")
        self.assertEqual(f("Active", "Under Repair"), "activated")
        self.assertEqual(f("Active", "Calibrating"), "activated")
        self.assertEqual(f("Active", "Under Maintenance"), "activated")
        self.assertEqual(f("Active", "Commissioned"), "activated")
        self.assertEqual(f("Active", ""), "activated")
        self.assertEqual(f("Active"), "activated")            # default from=''
        self.assertEqual(f("Decommissioned", "Out of Service"), "decommissioned")
        self.assertEqual(f("Decommissioned", "Active"), "decommissioned")
        self.assertEqual(f("Out of Service", "Active"), "out_of_service")

    # ── TC-ALE-RST-06 — audit-trail invariant (count up, chain OK, note kept) ─
    def test_ale_rst_06_audit_trail_invariant(self):
        asset = self._new(suffix="rst06", months=6)
        oos_start = add_days(nowdate(), -30)
        transition_asset_status(asset, "Out of Service", actor="Administrator")
        _backdate_oos_downtime(asset, oos_start)
        audit_before = frappe.db.count(_DT_AUDIT, {"asset": asset})
        transition_asset_status(asset, "Active", actor="Administrator")
        audit_after = frappe.db.count(_DT_AUDIT, {"asset": asset})
        self.assertGreaterEqual(audit_after - audit_before, 1,
                                "≥1 IMM Audit Trail 'State Change' for the restore")
        # Hash-chain must stay intact.
        chain = imm00_svc.verify_audit_chain(asset)
        self.assertTrue(chain.get("valid", chain.get("ok", False)),
                        f"audit hash-chain broken after restore: {chain}")
        # Depreciation-reschedule detail must still be auditable.
        notes = frappe.get_all(
            _DT_AUDIT, filters={"asset": asset, "event_type": "State Change"},
            fields=["change_summary"], limit_page_length=0)
        joined = " ".join((r.get("change_summary") or "") for r in notes)
        self.assertIn("dời", joined,
                      "reschedule note (oos_days) must remain in audit trail")

    # ── TC-ALE-RST-07 — re-call Active→Active no-op (no double restore/shift) ─
    def test_ale_rst_07_recall_active_no_double_restore(self):
        asset = self._new(suffix="rst07", months=6)
        oos_start = add_days(nowdate(), -40)
        transition_asset_status(asset, "Out of Service", actor="Administrator")
        _backdate_oos_downtime(asset, oos_start)
        transition_asset_status(asset, "Active", actor="Administrator")
        dates_after_first = {r["period_number"]: getdate(r["scheduled_date"])
                             for r in _pending_rows(asset)}
        restored_after_first = self._count_ale(asset, "restored")
        # Re-call Active→Active: guard prev==to must no-op (no extra ALE, no shift).
        transition_asset_status(asset, "Active", actor="Administrator")
        self.assertEqual(self._count_ale(asset, "restored"), restored_after_first,
                         "Active→Active re-call must NOT emit another 'restored'")
        dates_after_second = {r["period_number"]: getdate(r["scheduled_date"])
                              for r in _pending_rows(asset)}
        self.assertEqual(dates_after_second, dates_after_first,
                         "Active→Active re-call must NOT double-shift Pending dates")


class TestRestoreSourceGuards(FrappeTestCase):
    """INV-ALE-RESTORE-3 grep-guard — no stray create_lifecycle_event('restored')."""

    def test_no_restored_emit_outside_parent_transition(self):
        import inspect
        # The reschedule helper must NOT emit a lifecycle event anymore — the
        # parent transition owns the single 'restored' emission.
        src = inspect.getsource(
            imm00_svc._reschedule_pending_depreciation_on_restore)
        self.assertNotIn("create_lifecycle_event", src,
                         "reschedule helper must NOT emit any lifecycle event "
                         "(parent transition owns the 'restored' emission)")
        # No event_type='restored' literal call inside the helper (substring
        # checks would false-positive on the function name / INVARIANT comments).
        self.assertNotIn('event_type="restored"', src)
        self.assertNotIn("event_type='restored'", src)
        # But it MUST still write a State Change audit with the reschedule note.
        self.assertIn("log_audit_event", src)
        self.assertIn("State Change", src)

    def test_every_lifecycle_event_for_call_passes_from_status(self):
        import inspect
        # Both call-sites (service transition + controller on_update) must pass a
        # from_status so the OoS→Active label resolves consistently.
        svc_src = inspect.getsource(imm00_svc.transition_asset_status)
        self.assertIn("_lifecycle_event_for(to_status, prev_status)", svc_src)
        from assetcore.assetcore.doctype.ac_asset import ac_asset as ac_mod
        ctrl_src = inspect.getsource(ac_mod.ACAsset.on_update)
        self.assertIn("_lifecycle_event_for(cur, prev)", ctrl_src)
