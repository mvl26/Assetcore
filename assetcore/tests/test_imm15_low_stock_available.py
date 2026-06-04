# Copyright (c) 2026, AssetCore Team
# IMM-15 — Low-stock + forecast SoT = tồn KHẢ DỤNG (BR-15-17 / VR-15-17, vòng 23).
#
# Core Doc: docs/imm-15/04_Backend_Design.md §II.A + §III.6.2; 02 §BR-15-17/VR-15-17.
#
# SoT chốt (đảo round-3): "dưới định mức / cần đặt lại" so theo tồn KHẢ DỤNG
#   available_for_min(bin) = (s.qty_on_hand − COALESCE(s.reserved_qty,0))   -- RAW
#   low(bin)               ⟺ effective_min > 0 AND available_for_min < effective_min
# Biểu thức RAW (KHÔNG cột available_qty đã clamp MAX(0,…)) để bắt cả oversell.
#
# INV-LOW-AVAIL-1..6:
#   1. bin reserved-full (on_hand=100, reserved=100 ⇒ available=0), min=20 → LOW.
#   2. bin reserved=0, on_hand=25, min=20 → NOT low (đối chứng — hành vi cũ giữ).
#   3. card == drill == count == len(part_ids-distinct) — 1 con số, cùng tập.
#   4. predicate dùng RAW (qty_on_hand − reserved) — bin oversell (raw<0) vẫn LOW.
#   5. _sum_part_stock / forecast.current_qty = Σ(qty_on_hand − COALESCE(reserved,0)),
#      1 aggregate (no N+1) → recommended_action='Reorder' cho part giữ-chỗ-hết.
#   6. forecast_qty / safety_stock / reorder_point / historical_consumption_12m
#      / avg_monthly BẤT BIẾN (chỉ current_qty đổi nghĩa).
#
# RED-prove: trên code cũ (predicate so qty_on_hand vật lý) bin reserved-full
# KHÔNG bị flag → test 01/04/06 FAIL; sau fix PASS.
#
# Test isolation: tự seed warehouse + part riêng; tearDownClass dọn sạch (LL-TEST-9).
from __future__ import annotations

import unittest
from contextlib import suppress

import frappe

from assetcore.services import imm15 as svc


def _ensure_doc(doctype: str, lookup: dict, data: dict) -> str:
    """Idempotent fixture create keyed on a unique business field (LL-TEST-9)."""
    existing = frappe.db.get_value(doctype, lookup, "name")
    if existing:
        return existing
    doc = frappe.get_doc({"doctype": doctype, **lookup, **data})
    doc.flags.ignore_links = True
    doc.flags.ignore_mandatory = True
    doc.insert(ignore_permissions=True)
    return doc.name


def _set_bin(part: str, wh: str, on_hand: float, reserved: float = 0,
             override: float = 0) -> None:
    """Create/update a bin and let before_save derive available_qty.

    IMPORTANT: go through the DocType save() so available_qty is the REAL
    stored column = MAX(0, on_hand − reserved). Oversell bins therefore have a
    clamped available_qty = 0 while the RAW expression (on_hand − reserved) is
    negative — which is exactly what the predicate-uses-RAW assertion needs.
    """
    if frappe.db.exists("AC Spare Part Stock", {"spare_part": part, "warehouse": wh}):
        doc = frappe.get_doc("AC Spare Part Stock", {"spare_part": part, "warehouse": wh})
    else:
        doc = frappe.get_doc({"doctype": "AC Spare Part Stock",
                              "spare_part": part, "warehouse": wh})
    doc.qty_on_hand = on_hand
    doc.reserved_qty = reserved
    doc.min_stock_override = override
    doc.flags.ignore_links = True
    doc.save(ignore_permissions=True)
    frappe.db.commit()


class TestLowStockAvailable(unittest.TestCase):
    """BR-15-17 / VR-15-17 — low-stock predicate so theo tồn KHẢ DỤNG.

    Dataset (1 part min_stock_level=20, distinct bins per warehouse):
      RF (reserved-full): on_hand=100, reserved=100 (available=0)  → LOW (avail 0 < 20)
      OK (no reserve)   : on_hand=25,  reserved=0   (available=25) → NOT low (25 ≥ 20)
      PARTIAL           : on_hand=30,  reserved=15  (available=15) → LOW (15 < 20)
      OVERSELL          : on_hand=10,  reserved=12  (raw=−2, clamp 0), min=5 → LOW
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        any_uom = frappe.db.get_value("AC UOM", {}, "name") or None
        part_data = {"unit_cost": 100000, "is_active": 1, "min_stock_level": 20}
        if any_uom:
            part_data["stock_uom"] = any_uom
        cls.part = _ensure_doc("AC Spare Part", {"part_name": "_Test LowAvail Part"},
                               dict(part_data))
        # OVERSELL bin uses a lower effective_min via override (5) on its own bin.
        cls.wh_rf = _ensure_doc("AC Warehouse", {"warehouse_name": "_Test LA WH RF"},
                                {"is_active": 1})
        cls.wh_ok = _ensure_doc("AC Warehouse", {"warehouse_name": "_Test LA WH OK"},
                                {"is_active": 1})
        cls.wh_partial = _ensure_doc("AC Warehouse",
                                     {"warehouse_name": "_Test LA WH PARTIAL"},
                                     {"is_active": 1})
        cls.wh_over = _ensure_doc("AC Warehouse", {"warehouse_name": "_Test LA WH OVER"},
                                  {"is_active": 1})

        _set_bin(cls.part, cls.wh_rf, 100, reserved=100)              # available=0  → LOW
        _set_bin(cls.part, cls.wh_ok, 25, reserved=0)                 # available=25 → NOT low
        _set_bin(cls.part, cls.wh_partial, 30, reserved=15)           # available=15 → LOW
        _set_bin(cls.part, cls.wh_over, 10, reserved=12, override=5)  # raw=−2 < 5  → LOW

    @classmethod
    def tearDownClass(cls):
        with suppress(Exception):
            frappe.db.delete("AC Spare Part Stock", {"spare_part": cls.part})
            frappe.delete_doc("AC Spare Part", cls.part,
                              ignore_permissions=True, force=True)
            for wh in (cls.wh_rf, cls.wh_ok, cls.wh_partial, cls.wh_over):
                frappe.delete_doc("AC Warehouse", wh,
                                  ignore_permissions=True, force=True)
        frappe.db.commit()

    def _our_low_bins(self) -> set:
        from assetcore.services.imm15 import get_low_stock_alerts
        return {(a["warehouse"], a["spare_part"])
                for a in get_low_stock_alerts()["alerts"]
                if a["spare_part"] == self.part}

    # ── TC-15-LOW-AVAIL-01 (RED on old code) ────────────────────────────────
    def test_reserved_full_bin_counted_low(self):
        """Bin on_hand=100, reserved=100 (available=0), min=20 → LOW.

        OLD predicate (qty_on_hand < min): 100 ≥ 20 → NOT low → this FAILS.
        NEW predicate (available raw < min): 0 < 20 → LOW.
        """
        from assetcore.services.inventory import (count_low_stock_bins,
                                                  low_stock_part_ids)
        self.assertGreaterEqual(count_low_stock_bins(warehouse=self.wh_rf), 1,
                                "reserved-full bin must count as low")
        self.assertIn((self.wh_rf, self.part), self._our_low_bins(),
                      "reserved-full bin must appear in get_low_stock_alerts drill")
        self.assertIn(self.part, low_stock_part_ids(),
                      "part must be in low_stock_part_ids distinct set")

    # ── TC-15-LOW-AVAIL-02 (no false-positive, old behaviour preserved) ─────
    def test_reserved_zero_bin_not_low(self):
        """Bin on_hand=25, reserved=0 (available=25), min=20 → NOT low (25 ≥ 20)."""
        from assetcore.services.inventory import count_low_stock_bins
        self.assertEqual(count_low_stock_bins(warehouse=self.wh_ok), 0,
                         "reserved=0 bin at/above min must NOT be low (no false-positive)")
        self.assertNotIn((self.wh_ok, self.part), self._our_low_bins())

    # ── TC-15-LOW-AVAIL-03 (reserved pulls available below min) ─────────────
    def test_partial_reserve_bin_low(self):
        """Bin on_hand=30, reserved=15 (available=15), min=20 → LOW (15 < 20)."""
        from assetcore.services.inventory import count_low_stock_bins
        self.assertGreaterEqual(count_low_stock_bins(warehouse=self.wh_partial), 1)
        self.assertIn((self.wh_partial, self.part), self._our_low_bins())

    # ── TC-15-LOW-AVAIL-04 (oversell — predicate uses RAW not clamped col) ──
    def test_oversell_bin_low_via_raw_expression(self):
        """Bin on_hand=10, reserved=12 (raw=−2, stored available_qty clamps to 0),
        override min=5 → LOW.

        Proves the predicate compares the RAW expression (qty_on_hand − reserved),
        NOT the clamped available_qty column (which would be 0; 0 < 5 also low here,
        so additionally assert the stored column really is clamped to 0 to make the
        intent — RAW catches oversell — explicit)."""
        from assetcore.services.inventory import count_low_stock_bins
        stored = frappe.db.get_value(
            "AC Spare Part Stock",
            {"spare_part": self.part, "warehouse": self.wh_over},
            ["qty_on_hand", "reserved_qty", "available_qty"], as_dict=True)
        self.assertEqual(float(stored.available_qty), 0.0,
                         "stored available_qty must be clamped at 0 (before_save)")
        self.assertEqual(float(stored.qty_on_hand) - float(stored.reserved_qty), -2.0,
                         "raw on_hand − reserved must be negative (oversell)")
        self.assertGreaterEqual(count_low_stock_bins(warehouse=self.wh_over), 1,
                                "oversell bin (raw −2 < 5) must be low")
        self.assertIn((self.wh_over, self.part), self._our_low_bins())

    # ── TC-15-LOW-AVAIL-05 (count == drill == card invariant) ───────────────
    def test_count_equals_drill_equals_card(self):
        """get_dashboard_stats.low_stock_alerts == len(get_low_stock_alerts().alerts)
        == count_low_stock_bins() — 1 con số, KHÔNG divergence card-vs-drill."""
        from assetcore.services.inventory import (count_low_stock_bins,
                                                  low_stock_part_ids)
        card = svc.get_dashboard_stats()["low_stock_alerts"]
        drill = len(svc.get_low_stock_alerts()["alerts"])
        count = count_low_stock_bins()
        self.assertEqual(card, drill, "card KPI must equal drill list length")
        self.assertEqual(card, count, "card KPI must equal canonical bin count")
        # our 3 low bins (RF + PARTIAL + OVERSELL) must all be inside the global set;
        # the OK bin must not. distinct part-ids must contain our part.
        ours = self._our_low_bins()
        self.assertEqual(ours, {(self.wh_rf, self.part),
                                (self.wh_partial, self.part),
                                (self.wh_over, self.part)},
                         "exactly our 3 reserved-low bins; OK bin excluded")
        self.assertIn(self.part, low_stock_part_ids())

    # ── TC-15-LOW-AVAIL-08 (N+1 / SQL-shape guard) ──────────────────────────
    def test_count_and_alerts_single_sql(self):
        """count_low_stock_bins / get_low_stock_alerts each issue exactly 1
        low-stock SELECT (no python per-bin loop). _sum_part_stock = 1 aggregate."""
        from assetcore.services import inventory as inv

        def _count_low_stock_sql(fn) -> int:
            calls = {"n": 0}
            real = frappe.db.sql

            def _spy(query, *a, **k):
                q = query if isinstance(query, str) else getattr(query, "value", "")
                if "tabAC Spare Part Stock" in q and "qty_on_hand" in q:
                    calls["n"] += 1
                return real(query, *a, **k)

            orig = frappe.db.sql
            frappe.db.sql = _spy  # type: ignore[assignment]
            try:
                fn()
            finally:
                frappe.db.sql = orig  # type: ignore[assignment]
            return calls["n"]

        self.assertEqual(_count_low_stock_sql(inv.count_low_stock_bins), 1,
                         "count_low_stock_bins must be a single stock SQL")
        self.assertEqual(_count_low_stock_sql(svc.get_low_stock_alerts), 1,
                         "get_low_stock_alerts must be a single low-stock stock SQL")
        self.assertEqual(_count_low_stock_sql(lambda: svc._sum_part_stock(self.part)), 1,
                         "_sum_part_stock must be a single aggregate")

    # ── TC-15-LOW-AVAIL-09 (scheduler parity) ───────────────────────────────
    def test_scheduler_emails_reserved_low_bins(self):
        """check_low_stock() (the LOW_STOCK_COND scheduler) emails the reserved-full
        / partial / oversell bins (low-by-available) and NOT the reserved=0 OK bin."""
        from unittest.mock import patch
        from assetcore.services import inventory as inv_svc
        import assetcore.utils.email as email_mod
        captured = {}

        def _fake_sendmail(*, recipients, subject, message):
            captured["message"] = message

        with patch.object(email_mod, "get_role_emails", return_value=["k@x.test"]), \
             patch.object(email_mod, "safe_sendmail", side_effect=_fake_sendmail):
            inv_svc.check_low_stock()
        msg = captured.get("message", "")
        # reserved-full / partial / oversell bins appear; OK warehouse must not.
        self.assertIn("_Test LowAvail Part", msg)
        ok_name = frappe.db.get_value("AC Warehouse", self.wh_ok, "warehouse_name")
        self.assertNotIn(ok_name, msg,
                         "reserved=0 at-min OK bin must NOT be emailed (no spam)")


class TestForecastAvailable(unittest.TestCase):
    """BR-15-17 §III.6.2 — forecast current_qty = tồn KHẢ DỤNG; reserved-full part
    (on_hand ≥ reorder_point but available < reorder_point) → recommended_action='Reorder'.

    No consumption seeded → total_consumed=0 → avg_monthly=0 → reorder_point=0.
    With reorder_point=0 the action tree can't distinguish Reorder for these bins, so
    this fixture seeds Issue consumption to push reorder_point > available, then asserts
    the action flips with reserved-full stock while reorder_point/forecast_qty/etc stay
    invariant vs a reserved=0 baseline. Reuses the forecast data-contract fixture pattern.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        if not frappe.db.exists("AC UOM", "Cái"):
            with suppress(Exception):
                frappe.get_doc({"doctype": "AC UOM", "uom_name": "Cái",
                                "is_active": 1}).insert(ignore_permissions=True)
        any_uom = frappe.db.get_value("AC UOM", {}, "name") or None
        part_data = {"unit_cost": 100000, "is_active": 1, "min_stock_level": 5,
                     "is_critical": 0}
        if any_uom:
            part_data["stock_uom"] = any_uom
        cls.part = _ensure_doc("AC Spare Part", {"part_name": "_Test FcAvail Part"},
                               dict(part_data))
        cls.warehouse = _ensure_doc("AC Warehouse",
                                    {"warehouse_name": "_Test FcAvail WH"},
                                    {"is_active": 1})
        cls.department = ""
        if frappe.db.exists("DocType", "AC Department"):
            with suppress(Exception):
                cls.department = _ensure_doc(
                    "AC Department", {"department_name": "_Test FcAvail Dept"}, {})
        cls.asset = ""
        if frappe.db.exists("DocType", "AC Asset"):
            with suppress(Exception):
                cls.asset = _ensure_doc("AC Asset",
                                        {"asset_name": "_Test FcAvail Asset"},
                                        {"department": cls.department})
                if cls.asset and cls.department:
                    frappe.db.set_value("AC Asset", cls.asset, "department",
                                        cls.department)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        with suppress(Exception):
            for p in set(frappe.get_all(
                    "AC Stock Movement Item", filters={"spare_part": cls.part},
                    fields=["parent"], pluck="parent")):
                with suppress(Exception):
                    d = frappe.get_doc("AC Stock Movement", p)
                    if d.docstatus == 1:
                        d.cancel()
                    frappe.delete_doc("AC Stock Movement", p, force=True,
                                      ignore_permissions=True)
        with suppress(Exception):
            frappe.db.delete("AC Spare Part Stock", {"spare_part": cls.part})
            frappe.delete_doc("AC Spare Part", cls.part,
                              ignore_permissions=True, force=True)
            frappe.delete_doc("AC Warehouse", cls.warehouse,
                              ignore_permissions=True, force=True)
        if getattr(cls, "asset", ""):
            with suppress(Exception):
                from assetcore.tests._asset_cleanup import purge_asset
                purge_asset(cls.asset)
        if getattr(cls, "department", ""):
            with suppress(Exception):
                frappe.delete_doc("AC Department", cls.department,
                                  ignore_permissions=True, force=True)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        # Generous on-hand so backdated Issues submit; reset reservations.
        _set_bin(self.part, self.warehouse, 500, reserved=0)
        self._seed_consumption()

    def tearDown(self):
        with suppress(Exception):
            for p in set(frappe.get_all(
                    "AC Stock Movement Item", filters={"spare_part": self.part},
                    fields=["parent"], pluck="parent")):
                with suppress(Exception):
                    d = frappe.get_doc("AC Stock Movement", p)
                    if d.docstatus == 1:
                        d.cancel()
                    frappe.delete_doc("AC Stock Movement", p, force=True,
                                      ignore_permissions=True)
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

    def _seed_consumption(self) -> None:
        """12 monthly Issues of 5 each → total_consumed(12m)=60, avg_monthly=5.

        With default lead 30d / safety 14d: safety=5*14/30≈2.33, reorder=safety+5≈7.33.
        Available below ~7.33 → Reorder. on_hand 500 reserved=0 → available 500 → Hold.
        """
        from frappe.utils import add_months, nowdate, add_days
        for m in range(1, 13):
            mdate = add_months(nowdate(), -m)
            sm = frappe.get_doc({
                "doctype": "AC Stock Movement",
                "movement_type": "Issue",
                "from_warehouse": self.warehouse,
                "receiver_department": self.department or None,
                "reference_type": "Manual",
                "movement_date": mdate,
                "requested_by": "Administrator",
                "notes": "FcAvail consumption seed",
                "items": [{"spare_part": self.part, "qty": 5,
                           "warehouse": self.warehouse}],
            })
            sm.flags.ignore_links = True
            sm.insert(ignore_permissions=True)
            sm.submit()
            frappe.db.set_value("AC Stock Movement", sm.name, "movement_date", mdate)
        frappe.db.commit()

    def _forecast_item(self, horizon: int = 3) -> dict:
        res = svc.generate_spare_forecast(horizon_months=horizon, method="Moving_Avg")
        doc = frappe.get_doc("IMM Spare Part Forecast", res["name"])
        for it in doc.items:
            if it.spare_part == self.part:
                return it.as_dict()
        self.fail(f"Part {self.part} not in forecast {res['name']}")

    # ── TC-15-LOW-AVAIL-06a: baseline (reserved=0, ample stock) → Hold ──────
    def test_baseline_ample_available_holds(self):
        item = self._forecast_item()
        self.assertGreater(float(item["reorder_point"]), 0,
                           "consumption seeded → reorder_point must be > 0")
        self.assertNotEqual(item["recommended_action"], "Reorder",
                            "ample available (500) must NOT trigger Reorder")
        # remember invariants for the reserved-full comparison.
        self._baseline = item

    # ── TC-15-LOW-AVAIL-06b: reserved-full part → Reorder (RED on old) ──────
    def test_reserved_full_triggers_reorder(self):
        """on_hand ≥ reorder_point but reserved-full (available≈0 < reorder_point)
        → current_qty (= available) < reorder_point → Reorder.

        OLD code (current_qty = Σ qty_on_hand = 500) → 500 ≥ reorder_point → Hold/
        ReduceMin, NOT Reorder → this FAILS on old code.
        """
        base = self._forecast_item()  # reserved=0 baseline (ample) → not Reorder
        self.assertNotEqual(base["recommended_action"], "Reorder")
        rp = float(base["reorder_point"])
        # Now reserve the whole bin: on_hand 500, reserved 500 → available 0.
        _set_bin(self.part, self.warehouse, 500, reserved=500)
        item = self._forecast_item()
        # current_qty must reflect AVAILABLE (0), not physical on-hand (500).
        self.assertLess(float(item["current_qty"]), rp,
                        "current_qty must be available (≈0) < reorder_point")
        self.assertEqual(item["recommended_action"], "Reorder",
                         "reserved-full part must recommend Reorder")
        # invariants UNCHANGED vs baseline (only current_qty / action differ).
        for k in ("forecast_qty", "reorder_point", "safety_stock",
                  "historical_consumption_12m"):
            self.assertEqual(float(item[k]), float(base[k]),
                             f"{k} must be invariant across reservation change")

    # ── TC-15-LOW-AVAIL-05/06: _sum_part_stock reflects available, 1 aggregate ─
    def test_sum_part_stock_is_available_single_aggregate(self):
        # reserved=0 → equals on_hand.
        _set_bin(self.part, self.warehouse, 500, reserved=0)
        self.assertEqual(svc._sum_part_stock(self.part), 500.0)
        # reserve 200 → available 300.
        _set_bin(self.part, self.warehouse, 500, reserved=200)
        self.assertEqual(svc._sum_part_stock(self.part), 300.0,
                         "_sum_part_stock must subtract reserved (available)")
        # single SQL aggregate (no per-bin loop).
        calls = {"n": 0}
        real = frappe.db.sql

        def _spy(query, *a, **k):
            q = query if isinstance(query, str) else getattr(query, "value", "")
            if "tabAC Spare Part Stock" in q:
                calls["n"] += 1
            return real(query, *a, **k)

        frappe.db.sql = _spy  # type: ignore[assignment]
        try:
            svc._sum_part_stock(self.part)
        finally:
            frappe.db.sql = real  # type: ignore[assignment]
        self.assertEqual(calls["n"], 1, "_sum_part_stock must be 1 aggregate")


class TestLowStockNoDirectOnHandCompare(unittest.TestCase):
    """VR-15-17 grep-guard — 0 chỗ so trực tiếp s.qty_on_hand < effective_min
    ngoài fragment SoT (LOW_STOCK_COND) + 0 chỗ inline qty_on_hand < min_level."""

    def test_no_direct_onhand_lt_min_outside_fragment(self):
        import re
        import assetcore.services.inventory as inv_mod
        import assetcore.services.imm15 as imm_mod
        import assetcore.api.inventory as inv_api_mod
        import inspect

        # The canonical fragment must compare AVAILABLE (raw), not bare on-hand.
        self.assertIn("qty_on_hand - COALESCE(s.reserved_qty",
                      inv_mod.LOW_STOCK_COND.replace(" ", " "),
                      "LOW_STOCK_COND must subtract reserved_qty (available)")
        self.assertNotRegex(inv_mod.LOW_STOCK_COND,
                            r"s\.qty_on_hand\s*<\s*COALESCE\(NULLIF",
                            "LOW_STOCK_COND must NOT compare bare on-hand to min")

        # Scan each module source for a direct `qty_on_hand < <min-expr>` comparison
        # OUTSIDE the LOW_STOCK_COND assignment line. Tolerate references to the
        # fragment itself. Pattern: qty_on_hand followed by `<` then an effective-min
        # token (min_stock / effective_min / min_level), with no intervening `-`.
        bad = re.compile(
            r"qty_on_hand\s*(?:or\s*0\s*\)?)?\s*<\s*"
            r"(?![^\n]*reserved)"
            r"[^\n]*?(effective_min|min_stock|min_level)")
        for mod in (inv_mod, imm_mod, inv_api_mod):
            src = inspect.getsource(mod)
            for ln in src.splitlines():
                if "qty_on_hand" not in ln or "<" not in ln:
                    continue
                if "reserved" in ln:        # available expression → OK
                    continue
                if "LOW_STOCK_COND" in ln:  # the fragment definition itself
                    continue
                self.assertNotRegex(
                    ln, bad,
                    f"direct on-hand < min comparison outside fragment in "
                    f"{mod.__name__}: {ln.strip()}")
