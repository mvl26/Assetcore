# Copyright (c) 2026, AssetCore Team
# IMM-15 — Soft-reservation ledger (reserved_qty SoT) — docs/imm-15 §III-bis, VR-15-14.
#
# Invariant (Single Source of Truth) per bin = (warehouse × spare_part):
#   reserved_qty(bin)  = Σ COALESCE(NULLIF(qty_approved,0), qty_requested) of every
#                        allocation line in a HOLDING state {Requested, Approved}
#   available_qty(bin) = MAX(0, qty_on_hand − reserved_qty)        # before_save clamp
#
# RELEASE on terminal: Issued / Returned / Cancelled leave HOLDING → reserved drops.
# Anti-oversell: two OPEN allocations on a bin that only stocks ONE → the 2nd issue
# must FAIL VR-15-03 (available already held to 0). Emergency+Critical bypass stays.
#
# These tests are TDD RED-first: before the writer (`recompute_reserved`) is wired,
# reserved_qty has no writer anywhere → available_qty == qty_on_hand always, so
# TC-15-RSV-01/03/04/06/07 fail. After the fix they go GREEN.
#
# Run: bench --site miyano run-tests \
#      --module assetcore.tests.test_imm15_reservation
from __future__ import annotations

import unittest
from contextlib import suppress

import frappe

from assetcore.services import imm15 as svc
from assetcore.services import inventory as inv
from assetcore.services.shared import ErrorCode, ServiceError


class TestReservationBase(unittest.TestCase):
    """Self-cleaning fixtures: 1 warehouse + 1 Critical part + 1 bin.

    Each test sets the bin's qty_on_hand/reserved_qty explicitly and creates its
    OWN allocations (deleted in tearDownClass) so scenarios never interfere.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls._created: list[tuple[str, str]] = []

        if not frappe.db.exists("AC UOM", "Cái"):
            with suppress(Exception):
                frappe.get_doc({"doctype": "AC UOM", "uom_name": "Cái",
                                "is_active": 1}).insert(ignore_permissions=True)
        any_uom = frappe.db.get_value("AC UOM", {}, "name") or None

        cls.warehouse = cls._ensure_wh("_TestRsv WH")
        part_data = {
            "unit_cost": 100000, "is_active": 1, "min_stock_level": 5,
            "is_critical": 1, "part_code": "_TESTRSV-PART",
        }
        if frappe.db.has_column("AC Spare Part", "imm_part_class"):
            part_data["imm_part_class"] = "Critical"
        if any_uom:
            part_data["stock_uom"] = any_uom
        cls.part = cls._ensure_part("_TestRsv Part", part_data)
        cls.stock = cls._ensure_stock(cls.part, cls.warehouse, qty=10)

        # Department + asset — IMM Spare Allocation has a mandatory `asset` field;
        # the asset must carry a department so Issue stock movements validate.
        cls.department = ""
        if frappe.db.exists("DocType", "AC Department"):
            with suppress(Exception):
                cls.department = frappe.db.get_value(
                    "AC Department", {"department_name": "_TestRsv Dept"}, "name")
                if not cls.department:
                    cls.department = frappe.get_doc({
                        "doctype": "AC Department",
                        "department_name": "_TestRsv Dept",
                    }).insert(ignore_permissions=True).name
                    cls._created.append(("AC Department", cls.department))
        cls.asset = ""
        if frappe.db.exists("DocType", "AC Asset"):
            with suppress(Exception):
                cls.asset = frappe.db.get_value(
                    "AC Asset", {"asset_name": "_TestRsv Asset"}, "name")
                if not cls.asset:
                    adoc = frappe.get_doc({
                        "doctype": "AC Asset", "asset_name": "_TestRsv Asset",
                        "department": cls.department})
                    adoc.flags.ignore_mandatory = True
                    adoc.insert(ignore_permissions=True)
                    cls.asset = adoc.name
                    cls._created.append(("AC Asset", cls.asset))
                if cls.asset and cls.department:
                    frappe.db.set_value("AC Asset", cls.asset, "department",
                                        cls.department)
        frappe.db.commit()

    # ── fixture helpers (self-cleaning, R-9) ───────────────────────────────
    @classmethod
    def _ensure_wh(cls, name: str) -> str:
        existing = frappe.db.get_value("AC Warehouse", {"warehouse_name": name}, "name")
        if existing:
            frappe.db.set_value("AC Warehouse", existing, "is_active", 1)
            return existing
        doc = frappe.get_doc({"doctype": "AC Warehouse", "warehouse_name": name,
                              "is_active": 1})
        doc.flags.ignore_mandatory = True
        doc.insert(ignore_permissions=True)
        cls._created.append(("AC Warehouse", doc.name))
        return doc.name

    @classmethod
    def _ensure_part(cls, name: str, data: dict) -> str:
        existing = frappe.db.get_value("AC Spare Part", {"part_name": name}, "name")
        if existing:
            frappe.db.set_value("AC Spare Part", existing,
                                {k: v for k, v in data.items() if k != "part_code"})
            return existing
        doc = frappe.get_doc({"doctype": "AC Spare Part", "part_name": name, **data})
        doc.flags.ignore_mandatory = True
        doc.insert(ignore_permissions=True)
        cls._created.append(("AC Spare Part", doc.name))
        return doc.name

    @classmethod
    def _ensure_stock(cls, part: str, wh: str, *, qty: float) -> str:
        existing = frappe.db.get_value(
            "AC Spare Part Stock", {"spare_part": part, "warehouse": wh}, "name")
        if existing:
            frappe.db.set_value("AC Spare Part Stock", existing,
                                {"qty_on_hand": qty, "reserved_qty": 0,
                                 "available_qty": qty})
            return existing
        doc = frappe.get_doc({
            "doctype": "AC Spare Part Stock", "spare_part": part, "warehouse": wh,
            "qty_on_hand": qty, "reserved_qty": 0, "available_qty": qty})
        doc.flags.ignore_mandatory = True
        doc.insert(ignore_permissions=True)
        cls._created.append(("AC Spare Part Stock", doc.name))
        return doc.name

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        # 1) allocations referencing our part (cancel submitted, then delete).
        with suppress(Exception):
            for parent in frappe.get_all(
                "IMM Spare Allocation Item", filters={"spare_part": cls.part},
                fields=["parent"], pluck="parent",
            ):
                with suppress(Exception):
                    doc = frappe.get_doc("IMM Spare Allocation", parent)
                    if doc.docstatus == 1:
                        doc.cancel()
                    frappe.delete_doc("IMM Spare Allocation", parent, force=True,
                                      ignore_permissions=True, delete_permanently=True)
        # 2) stock movements tied to the part (block part delete).
        with suppress(Exception):
            for parent in frappe.get_all(
                "AC Stock Movement Item", filters={"spare_part": cls.part},
                fields=["parent"], pluck="parent",
            ):
                with suppress(Exception):
                    doc = frappe.get_doc("AC Stock Movement", parent)
                    if doc.docstatus == 1:
                        doc.cancel()
                    frappe.delete_doc("AC Stock Movement", parent, force=True,
                                      ignore_permissions=True, delete_permanently=True)
        # 3) watchlist entries on our part.
        with suppress(Exception):
            for n in frappe.get_all("IMM Critical Spare Watchlist",
                                    filters={"spare_part": cls.part}, pluck="name"):
                frappe.delete_doc("IMM Critical Spare Watchlist", n, force=True,
                                  ignore_permissions=True, delete_permanently=True)
        # 4) shared master fixtures (FK-safe order).
        for dt, name in reversed(cls._created):
            with suppress(Exception):
                frappe.delete_doc(dt, name, force=True, ignore_permissions=True,
                                  delete_permanently=True)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        # Per-test isolation: remove ALL allocations on our part (prior tests leave
        # OPEN holds that recompute would otherwise re-sum), then reset the bin to a
        # clean physical baseline (10 on-hand, 0 reserved).
        self._purge_allocations()
        self._reset_bin(qty=10)

    def _purge_allocations(self) -> None:
        for parent in frappe.get_all(
            "IMM Spare Allocation Item", filters={"spare_part": self.part},
            fields=["parent"], pluck="parent",
        ):
            with suppress(Exception):
                doc = frappe.get_doc("IMM Spare Allocation", parent)
                if doc.docstatus == 1:
                    doc.cancel()
                frappe.delete_doc("IMM Spare Allocation", parent, force=True,
                                  ignore_permissions=True, delete_permanently=True)
        # Cancel + drop any stock movements created during a test (so on_hand resets).
        for parent in frappe.get_all(
            "AC Stock Movement Item", filters={"spare_part": self.part},
            fields=["parent"], pluck="parent",
        ):
            with suppress(Exception):
                doc = frappe.get_doc("AC Stock Movement", parent)
                if doc.docstatus == 1:
                    doc.cancel()
                frappe.delete_doc("AC Stock Movement", parent, force=True,
                                  ignore_permissions=True, delete_permanently=True)
        frappe.db.commit()

    # ── helpers ────────────────────────────────────────────────────────────
    def _reset_bin(self, *, qty: float) -> None:
        """Set on_hand + reserved=0 via a real save so before_save derives available."""
        doc = frappe.get_doc("AC Spare Part Stock", self.stock)
        doc.qty_on_hand = qty
        doc.reserved_qty = 0
        doc.save(ignore_permissions=True)
        frappe.db.commit()

    def _set_on_hand(self, qty: float) -> None:
        # Real save → before_save recomputes available_qty (clamp) from on_hand/reserved.
        doc = frappe.get_doc("AC Spare Part Stock", self.stock)
        doc.qty_on_hand = qty
        doc.save(ignore_permissions=True)
        frappe.db.commit()

    def _bin_row(self) -> dict:
        return frappe.db.get_value(
            "AC Spare Part Stock", self.stock,
            ["qty_on_hand", "reserved_qty", "available_qty"], as_dict=True)

    def _make_allocation(self, *, qty_requested: float, status: str,
                         qty_approved: float = 0, urgency: str = "Routine") -> str:
        """Insert a raw IMM Spare Allocation in a target HOLDING/terminal state.

        We bypass the service create→approve→issue chain so we can plant an
        allocation directly in any state (Requested/Approved/Cancelled/…) to
        exercise recompute_reserved in isolation.
        """
        doc = frappe.get_doc({
            "doctype": "IMM Spare Allocation",
            "work_order_ref": "WO-RSV-TEST",
            "work_order_doctype": "IMM PM Work Order",
            "asset": self.asset,
            "warehouse_from": self.warehouse,
            "requested_by": frappe.session.user,
            "requested_date": frappe.utils.nowdate(),
            "required_date": frappe.utils.add_days(frappe.utils.nowdate(), 3),
            "urgency": urgency,
            "allocation_status": status,
            "items": [{
                "spare_part": self.part,
                "qty_requested": qty_requested,
                "qty_approved": qty_approved,
                "unit_value": 100000,
            }],
        })
        doc.flags.ignore_links = True
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return doc.name


class TestReservedHasWriter(TestReservationBase):
    """TC-15-RSV-01 (RED): an OPEN allocation must hold stock."""

    def test_open_allocation_holds_stock(self):
        self._set_on_hand(10)
        self._make_allocation(qty_requested=5, status="Requested")
        reserved = inv.recompute_reserved(self.warehouse, self.part)
        self.assertEqual(reserved, 5, "reserved_qty must equal the held qty")
        row = self._bin_row()
        self.assertEqual(row.reserved_qty, 5)
        self.assertEqual(row.available_qty, 5, "available = on_hand − reserved")
        self.assertEqual(row.qty_on_hand, 10, "physical on-hand must NOT change")
        # consumer surface reflects it
        self.assertEqual(inv.get_available_qty(self.warehouse, self.part), 5)


class TestRecomputeSoT(TestReservationBase):
    """TC-15-RSV-02: recompute = Σ HOLDING lines; terminal lines excluded."""

    def test_recompute_sums_holding_only(self):
        self._make_allocation(qty_requested=3, status="Requested")
        self._make_allocation(qty_requested=4, status="Approved", qty_approved=4)
        reserved = inv.recompute_reserved(self.warehouse, self.part)
        self.assertEqual(reserved, 7, "Requested 3 + Approved 4 = 7")
        # A Cancelled line must NOT be counted.
        self._make_allocation(qty_requested=9, status="Cancelled")
        reserved2 = inv.recompute_reserved(self.warehouse, self.part)
        self.assertEqual(reserved2, 7, "Cancelled line is terminal — not held")

    def test_approve_uses_qty_approved_when_set(self):
        # Requested 5 but approved only 2 → held = 2 (qty_approved wins).
        self._make_allocation(qty_requested=5, status="Approved", qty_approved=2)
        self.assertEqual(inv.recompute_reserved(self.warehouse, self.part), 2)


class TestReleaseOnIssue(TestReservationBase):
    """TC-15-RSV-03: issue releases reserved (no double-count)."""

    def test_issue_releases_reserved(self):
        self._set_on_hand(10)
        res = svc.create_allocation(
            work_order_ref="WO-RSV-ISSUE",
            items=[{"spare_part": self.part, "qty_requested": 6}],
            asset=self.asset, warehouse=self.warehouse, urgency="Routine",
        )
        # after create (Requested) → held 6
        row = self._bin_row()
        self.assertEqual(row.reserved_qty, 6)
        self.assertEqual(row.available_qty, 4)
        self.assertEqual(row.qty_on_hand, 10)

        svc.approve_allocation(res["name"])
        row = self._bin_row()
        self.assertEqual(row.reserved_qty, 6, "Approved still holds")

        svc.issue_allocation(res["name"])
        row = self._bin_row()
        self.assertEqual(row.qty_on_hand, 4, "physical on-hand drops by issued 6")
        self.assertEqual(row.reserved_qty, 0, "released — no double count")
        self.assertEqual(row.available_qty, 4, "available == new on_hand")


class TestAntiOversell(TestReservationBase):
    """TC-15-RSV-04 (bug chính): 2nd issue on a bin that only stocks one fails."""

    def test_second_issue_fails_vr_15_03(self):
        self._set_on_hand(5)  # only enough for ONE allocation of 5
        a = svc.create_allocation(
            work_order_ref="WO-RSV-A",
            items=[{"spare_part": self.part, "qty_requested": 5}],
            asset=self.asset, warehouse=self.warehouse, urgency="Routine",
        )
        # A (Requested) holds the whole bin → available 0.
        row = self._bin_row()
        self.assertEqual(row.reserved_qty, 5)
        self.assertEqual(row.available_qty, 0)

        b = svc.create_allocation(
            work_order_ref="WO-RSV-B",
            items=[{"spare_part": self.part, "qty_requested": 5}],
            asset=self.asset, warehouse=self.warehouse, urgency="Routine",
        )
        svc.approve_allocation(b["name"])
        with self.assertRaises(ServiceError) as ctx:
            svc.issue_allocation(b["name"])
        self.assertEqual(ctx.exception.code, ErrorCode.BUSINESS_RULE)
        self.assertIn("VR-15-03", ctx.exception.message)


class TestEmergencyBypass(TestReservationBase):
    """TC-15-RSV-05: Emergency + Critical still bypasses VR-15-03."""

    def test_emergency_critical_bypass_unchanged(self):
        self._set_on_hand(5)
        a = svc.create_allocation(
            work_order_ref="WO-RSV-EA",
            items=[{"spare_part": self.part, "qty_requested": 5}],
            asset=self.asset, warehouse=self.warehouse, urgency="Routine",
        )
        # A holds all 5 → available 0 for B.
        self.assertEqual(self._bin_row().available_qty, 0)

        b = svc.create_allocation(
            work_order_ref="",
            items=[{"spare_part": self.part, "qty_requested": 5}],
            asset=self.asset, warehouse=self.warehouse, urgency="Emergency",
        )
        # part is Critical (fixture is_critical=1) + Emergency → bypass VR-15-03.
        out = svc.issue_allocation(b["name"])
        self.assertEqual(out["workflow_state"], "Issued")


class TestClampNonNegative(TestReservationBase):
    """TC-15-RSV-06: available_qty never negative (before_save clamp)."""

    def test_available_never_negative(self):
        # Manually set reserved > on_hand then save → before_save clamps to 0.
        doc = frappe.get_doc("AC Spare Part Stock", self.stock)
        doc.qty_on_hand = 3
        doc.reserved_qty = 9
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        row = self._bin_row()
        self.assertEqual(row.available_qty, 0, "clamped at 0, never negative")


class TestConsumerNoRegression(TestReservationBase):
    """TC-15-RSV-07: watchlist / critical_breach reflect reservation."""

    def test_critical_breach_reflects_reserved(self):
        self._set_on_hand(5)
        # Watchlist: min_required 3. With 1 Requested(3) → available 2 < 3 → breach.
        wl_name = "_TestRsv-WL"
        if frappe.db.exists("IMM Critical Spare Watchlist", wl_name):
            frappe.delete_doc("IMM Critical Spare Watchlist", wl_name,
                              force=True, ignore_permissions=True)
        asset = frappe.db.get_value("AC Asset", {}, "name") or "X"
        svc.add_to_watchlist(
            watchlist_name=wl_name, critical_asset=asset,
            spare_part=self.part, min_required_on_hand=3, warehouse=self.warehouse,
        )
        # Before any allocation: available 5 ≥ 3 → NOT below.
        self.assertEqual(inv.get_available_qty(self.warehouse, self.part), 5)

        self._make_allocation(qty_requested=3, status="Requested")
        inv.recompute_reserved(self.warehouse, self.part)
        self.assertEqual(inv.get_available_qty(self.warehouse, self.part), 2)

        wl = svc.get_critical_watchlist()
        ours = [r for r in wl if r["name"] == wl_name]
        self.assertTrue(ours, "watchlist entry must surface as below_minimum")
        self.assertTrue(ours[0]["below_minimum"])

        # KPI critical_breach must also reflect the held availability.
        stats = svc.get_dashboard_stats()
        self.assertGreaterEqual(stats["critical_breach_hours_30d"]["value"], 1)


class TestLowStockSemanticsUnchanged(TestReservationBase):
    """TC-15-RSV-08: low-stock predicate still uses qty_on_hand, not available."""

    def test_reservation_does_not_make_bin_low(self):
        # on_hand 10 ≥ part-min 5 → NOT low. Reserve 8 → available 2, but the bin
        # must STILL not be low (low compares physical on_hand vs effective_min).
        self._set_on_hand(10)
        self._make_allocation(qty_requested=8, status="Requested")
        inv.recompute_reserved(self.warehouse, self.part)
        ours_low = frappe.db.sql("""
            SELECT COUNT(*) FROM `tabAC Spare Part Stock` s
            JOIN `tabAC Spare Part` p ON p.name = s.spare_part
            WHERE s.name = %s
              AND COALESCE(NULLIF(s.min_stock_override,0), p.min_stock_level, 0) > 0
              AND s.qty_on_hand < COALESCE(NULLIF(s.min_stock_override,0), p.min_stock_level, 0)
        """, self.stock)[0][0]
        self.assertEqual(ours_low, 0, "on_hand 10 ≥ min 5 → bin NOT low despite reserve")


class TestIdempotent(TestReservationBase):
    """TC-15-RSV-09: recompute is idempotent; return does not re-reserve."""

    def test_recompute_idempotent(self):
        self._make_allocation(qty_requested=4, status="Approved", qty_approved=4)
        r1 = inv.recompute_reserved(self.warehouse, self.part)
        r2 = inv.recompute_reserved(self.warehouse, self.part)
        self.assertEqual(r1, r2)
        self.assertEqual(r2, 4)

    def test_return_after_issue_no_re_reserve(self):
        self._set_on_hand(10)
        res = svc.create_allocation(
            work_order_ref="WO-RSV-RET",
            items=[{"spare_part": self.part, "qty_requested": 4}],
            asset=self.asset, warehouse=self.warehouse, urgency="Routine",
        )
        svc.approve_allocation(res["name"])
        svc.issue_allocation(res["name"])
        self.assertEqual(self._bin_row().reserved_qty, 0)
        svc.return_items(res["name"],
                         [{"spare_part": self.part, "qty_returned": 4,
                           "return_condition": "Good"}])
        # After return reserved must remain 0 (no re-reserve of returned stock).
        self.assertEqual(self._bin_row().reserved_qty, 0)


if __name__ == "__main__":
    unittest.main()
