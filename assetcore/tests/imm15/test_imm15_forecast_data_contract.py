# Copyright (c) 2026, AssetCore Team
# IMM-15 — Forecast data-contract tests (VR-15-15 + VR-15-07).
#
# VR-15-15: `IMM Spare Forecast Item.historical_consumption_12m` PHẢI bằng tổng qty
#   Issue (movement_type='Issue', docstatus=1) của spare_part trong CHÍNH XÁC 12 tháng
#   trailing (CURDATE() − INTERVAL 12 MONTH) — TÁCH khỏi lookback window biến thiên
#   (lookback_months = max(horizon*4, 12)). Bug gốc: field gán = total_consumed (cửa
#   sổ lookback) → tại horizon=6 (lookback=24) field = consumption 24 tháng nhưng nhãn
#   DB "Tiêu thụ 12 tháng" → SAI 2×.
# VR-15-07: reorder_point >= safety_stock cho MỌI item của forecast sinh ra.
#
# Test isolation: tự seed 1 spare part riêng + Issue stock movements backdated, không
# đụng fixture của TestImm15Base. tearDownClass dọn sạch (LL-TEST-9 / R-9).
from __future__ import annotations

import unittest
from contextlib import suppress
from unittest.mock import patch

import frappe
from frappe.utils import add_months, nowdate

from assetcore.repositories.allocation_repo import StockMovementRepo
from assetcore.services import imm15 as svc
from frappe.tests.utils import FrappeTestCase

# Unique business keys (LL-TEST-9: lookup by business field, autonamed PKs ignored).
_WH_NAME = "_Test WH IMM15-FC"
_PART_NAME = "_Test Part IMM15-FC"
_DEPT_NAME = "_Test Dept IMM15-FC"
_ASSET_NAME = "_Test Asset IMM15-FC"


def _ensure_doc(doctype: str, lookup: dict, data: dict) -> str:
    existing = frappe.db.get_value(doctype, lookup, "name")
    if existing:
        return existing
    doc = frappe.get_doc({"doctype": doctype, **lookup, **data})
    doc.flags.ignore_links = True
    doc.flags.ignore_mandatory = True
    doc.insert(ignore_permissions=True)
    return doc.name


class _ForecastFixture(FrappeTestCase):
    """Shared fixture: isolated warehouse + spare part + department + asset.

    Issue movements are seeded PER-test (each test controls its own consumption
    distribution), then cleaned in tearDown — keeps the 12m/24m windows deterministic.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        if not frappe.db.exists("AC UOM", "Cái"):
            with suppress(Exception):
                frappe.get_doc({"doctype": "AC UOM", "uom_name": "Cái",
                                "is_active": 1}).insert(ignore_permissions=True)
        cls.warehouse = _ensure_doc("AC Warehouse", {"warehouse_name": _WH_NAME},
                                    {"is_active": 1})
        any_uom = frappe.db.get_value("AC UOM", {}, "name") or None
        spare_data = {"unit_cost": 100000, "is_active": 1, "min_stock_level": 5,
                      "is_critical": 0}
        if any_uom:
            spare_data["stock_uom"] = any_uom
        cls.part = _ensure_doc("AC Spare Part", {"part_name": _PART_NAME}, spare_data)
        # Department — Issue stock movement requires a receiver department (Slide 27).
        cls.department = ""
        if frappe.db.exists("DocType", "AC Department"):
            with suppress(Exception):
                cls.department = _ensure_doc(
                    "AC Department", {"department_name": _DEPT_NAME}, {})
        cls.asset = ""
        if frappe.db.exists("DocType", "AC Asset"):
            with suppress(Exception):
                cls.asset = _ensure_doc("AC Asset", {"asset_name": _ASSET_NAME},
                                        {"department": cls.department})
                if cls.asset and cls.department:
                    frappe.db.set_value("AC Asset", cls.asset, "department", cls.department)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        # Generous on-hand so backdated Issues submit cleanly (before_submit gate
        # checks live qty_on_hand; we issue cumulatively ≤ on-hand).
        self._reset_stock(500)

    def tearDown(self):
        # Cancel + purge this test's Issue movements so the next test starts clean.
        with suppress(Exception):
            parents = frappe.get_all(
                "AC Stock Movement Item", filters={"spare_part": self.part},
                fields=["parent"], pluck="parent",
            )
            for p in set(parents):
                with suppress(Exception):
                    doc = frappe.get_doc("AC Stock Movement", p)
                    if doc.docstatus == 1:
                        doc.cancel()
                    frappe.delete_doc("AC Stock Movement", p, force=True,
                                      ignore_permissions=True)
        # Purge forecasts created by this test.
        with suppress(Exception):
            for f in frappe.get_all("IMM Spare Part Forecast",
                                    filters={"generated_by": "Administrator"},
                                    pluck="name"):
                with suppress(Exception):
                    fd = frappe.get_doc("IMM Spare Part Forecast", f)
                    if fd.docstatus == 1:
                        fd.cancel()
                    frappe.delete_doc("IMM Spare Part Forecast", f, force=True,
                                      ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        with suppress(Exception):
            for st in frappe.get_all("AC Spare Part Stock",
                                     filters={"spare_part": cls.part}, pluck="name"):
                frappe.delete_doc("AC Spare Part Stock", st, force=True,
                                  ignore_permissions=True)
        if getattr(cls, "asset", ""):
            with suppress(Exception):
                from assetcore.tests._helpers._asset_cleanup import purge_asset
                purge_asset(cls.asset)
        for dt, name in (("AC Spare Part", getattr(cls, "part", "")),
                         ("AC Warehouse", getattr(cls, "warehouse", "")),
                         ("AC Department", getattr(cls, "department", ""))):
            if name:
                with suppress(Exception):
                    frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
        frappe.db.commit()

    # ── helpers ──────────────────────────────────────────────────────────────
    def _reset_stock(self, qty: float) -> None:
        if frappe.db.exists("AC Spare Part Stock",
                            {"spare_part": self.part, "warehouse": self.warehouse}):
            frappe.db.set_value(
                "AC Spare Part Stock",
                {"spare_part": self.part, "warehouse": self.warehouse},
                {"qty_on_hand": qty, "available_qty": qty, "reserved_qty": 0},
            )
        else:
            frappe.get_doc({
                "doctype": "AC Spare Part Stock", "spare_part": self.part,
                "warehouse": self.warehouse, "qty_on_hand": qty,
                "available_qty": qty,
            }).insert(ignore_permissions=True)
        frappe.db.commit()

    def _seed_issue(self, qty: float, months_ago: float) -> str:
        """Create a SUBMITTED Issue stock movement of `qty`, dated `months_ago` back.

        Backdates `movement_date` so the get_consumption(months=N) window predicate is
        exercised. movement_date is set BEFORE submit; submit's stock gate reads live
        on-hand (kept high in setUp), the consumption query reads movement_date only.
        """
        mdate = add_months(nowdate(), -int(months_ago)) if months_ago == int(months_ago) \
            else frappe.utils.add_days(nowdate(), -int(round(months_ago * 30)))
        sm = frappe.get_doc({
            "doctype": "AC Stock Movement",
            "movement_type": "Issue",
            "from_warehouse": self.warehouse,
            "receiver_department": self.department or None,
            "reference_type": "Manual",
            "movement_date": mdate,
            "requested_by": "Administrator",
            "notes": "IMM15-FC consumption seed",
            "items": [{"spare_part": self.part, "qty": qty,
                       "warehouse": self.warehouse}],
        })
        sm.flags.ignore_links = True
        sm.insert(ignore_permissions=True)
        sm.submit()
        # submit/validate may normalise movement_date — force the backdated value so the
        # trailing-window predicate is deterministic regardless of controller defaults.
        frappe.db.set_value("AC Stock Movement", sm.name, "movement_date", mdate)
        frappe.db.commit()
        return sm.name

    def _forecast_item(self, horizon: int) -> dict:
        """Run generate_spare_forecast and return THIS part's child item as a dict."""
        res = svc.generate_spare_forecast(horizon_months=horizon, method="Moving_Avg")
        doc = frappe.get_doc("IMM Spare Part Forecast", res["name"])
        for it in doc.items:
            if it.spare_part == self.part:
                return it.as_dict()
        self.fail(f"Part {self.part} not found in forecast {res['name']}")


class TestForecastDataContract(_ForecastFixture):
    """VR-15-15 — historical_consumption_12m == trailing-12m consumption ∀ horizon."""

    def test_hist_12m_only_counts_trailing_12m_at_horizon_6(self):
        """TC-FC-12M-01 (BUG CHÍNH / RED-prove).

        Seed 10 @ −2m (inside 12m) + 100 @ −18m (outside 12m, inside 24m).
        horizon=6 → lookback=24. field MUST == 10, NOT 110.
        Pre-fix (field = total_consumed @ lookback=24) → 110 (RED).
        """
        self._seed_issue(10, months_ago=2)
        self._seed_issue(100, months_ago=18)
        item = self._forecast_item(horizon=6)
        self.assertEqual(item["historical_consumption_12m"], 10,
                         "VR-15-15: field must reflect exactly trailing-12m (10), "
                         "not the 24m lookback window (110)")

    def test_hist_12m_equals_trailing_12m_all_horizons(self):
        """TC-FC-12M (EP): ∀ horizon ∈ {1,3,6,12} field == get_consumption(12)."""
        self._seed_issue(7, months_ago=2)     # inside 12m
        self._seed_issue(50, months_ago=20)   # outside 12m
        expected12 = StockMovementRepo.get_consumption(self.part, months=12)
        self.assertEqual(expected12, 7)
        for horizon in (1, 3, 6, 12):
            item = self._forecast_item(horizon=horizon)
            self.assertEqual(
                item["historical_consumption_12m"], expected12,
                f"horizon={horizon}: field must equal trailing-12m consumption (7)")

    def test_forecast_qty_invariant_horizon_3(self):
        """TC-FC-12M-03: forecast outputs unchanged by the field split.

        Even consumption: 12 Issues × qty=5 spread monthly (−1..−12m). horizon=3 →
        lookback==12 (trùng). forecast_qty/avg_monthly/reorder_point/safety_stock are
        computed from total_consumed (unchanged) — only the field is added precisely.
        """
        for m in range(1, 13):
            self._seed_issue(5, months_ago=m)
        total12 = StockMovementRepo.get_consumption(self.part, months=12)
        self.assertEqual(total12, 60)
        item = self._forecast_item(horizon=3)
        # avg_monthly = 60/12 = 5 ; forecast_qty = 5*3 = 15
        self.assertEqual(item["forecast_qty"], 15.0)
        self.assertEqual(item["historical_consumption_12m"], 60)
        # safety_stock = avg_monthly * safety_stock_days/30 = 5 * 14/30 = 2.33
        self.assertEqual(item["safety_stock"], round(5 * 14 / 30, 2))
        # reorder_point = safety_stock + avg_monthly*lead/30 = 2.33 + 5*30/30 = 7.33
        self.assertEqual(item["reorder_point"], round(round(5 * 14 / 30, 2) + 5 * 30 / 30, 2))

    def test_no_extra_query_when_lookback_eq_12(self):
        """TC-FC-12M-02 (no N+1): horizon=3 (lookback==12) reuses total_consumed.

        get_consumption is called EXACTLY ONCE for this part (the lookback read);
        the field MUST NOT trigger a second get_consumption(months=12).
        """
        self._seed_issue(10, months_ago=2)
        real = StockMovementRepo.get_consumption.__func__
        calls: list[dict] = []

        def _spy(cls, spare_part, months=12):
            if spare_part == self.part:
                calls.append({"months": months})
            return real(cls, spare_part, months=months)

        with patch.object(StockMovementRepo, "get_consumption",
                          classmethod(_spy)):
            item = self._forecast_item(horizon=3)
        self.assertEqual(item["historical_consumption_12m"], 10)
        self.assertEqual(len(calls), 1,
                         f"horizon=3 must reuse total_consumed (1 call); got {calls}")
        self.assertEqual(calls[0]["months"], 12)

    def test_extra_query_added_only_when_lookback_gt_12(self):
        """TC-FC-12M-02b: horizon=6 (lookback=24) adds exactly ONE 12m read (no N+1)."""
        self._seed_issue(10, months_ago=2)
        real = StockMovementRepo.get_consumption.__func__
        calls: list[int] = []

        def _spy(cls, spare_part, months=12):
            if spare_part == self.part:
                calls.append(months)
            return real(cls, spare_part, months=months)

        with patch.object(StockMovementRepo, "get_consumption",
                          classmethod(_spy)):
            self._forecast_item(horizon=6)
        # exactly 2 calls for this part: lookback=24 + fixed 12m; no more.
        self.assertEqual(sorted(calls), [12, 24],
                         f"horizon=6 must read lookback(24)+12m once each; got {calls}")

    def test_hist_12m_boundary_at_exactly_12_months(self):
        """TC-FC-12M-04 (BVA): Issue dated exactly −12m is INCLUDED (>= boundary).

        get_consumption uses movement_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH);
        an Issue at exactly −12m sits on the inclusive boundary → counts. One slightly
        beyond (−12m − 5d) must be excluded.
        """
        self._seed_issue(8, months_ago=12)            # on boundary → included
        self._seed_issue(40, months_ago=12.2)         # just beyond → excluded
        item = self._forecast_item(horizon=6)
        self.assertEqual(item["historical_consumption_12m"], 8,
                         "boundary −12m must be inclusive; −12m−margin excluded")

    def test_hist_12m_zero_when_no_issue(self):
        """TC-FC-12M-05 (no-consumption): no Issue → field == 0 + Hold/Obsolete action."""
        item = self._forecast_item(horizon=6)
        self.assertEqual(item["historical_consumption_12m"], 0)
        # current_qty > 0 (we keep 500 on-hand) → Hold, never Reorder.
        self.assertEqual(item["recommended_action"], "Hold")


class TestForecastReorderInvariant(_ForecastFixture):
    """VR-15-07 — reorder_point >= safety_stock for every generated item."""

    def test_reorder_point_ge_safety_stock_all_items(self):
        """TC-VR-15-07: every item in a generated forecast satisfies VR-15-07.

        Includes the avg_monthly==0 boundary (no consumption → both 0 → 0>=0 holds).
        """
        # seed some consumption on our isolated part so it is non-trivial
        self._seed_issue(12, months_ago=1)
        self._seed_issue(8, months_ago=5)
        res = svc.generate_spare_forecast(horizon_months=6, method="Moving_Avg")
        doc = frappe.get_doc("IMM Spare Part Forecast", res["name"])
        self.assertGreaterEqual(len(doc.items), 1)
        for it in doc.items:
            rp = float(it.reorder_point or 0)
            ss = float(it.safety_stock or 0)
            self.assertGreaterEqual(
                rp, ss,
                f"VR-15-07 violated for {it.spare_part}: "
                f"reorder_point={rp} < safety_stock={ss}")


if __name__ == "__main__":
    unittest.main()
