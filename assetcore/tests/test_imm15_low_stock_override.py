# Copyright (c) 2026, AssetCore Team
# IMM-15 — Low-stock predicate canonicalization (R7 §9.4.5 override-fallback).
#
# Single canonical predicate everywhere:
#   effective_min = COALESCE(NULLIF(s.min_stock_override, 0), p.min_stock_level, 0)
#   low  ⟺  effective_min > 0 AND s.qty_on_hand < effective_min
#
# These tests assert that EVERY low-stock surface (KPI count, alerts list, drill
# part-ids, dashboard widget, scheduler email) honours min_stock_override per bin
# — i.e. a bin that is low ONLY because of its per-bin override must be counted
# everywhere identically (no surface diverges).
#
# Run: bench --site miyano run-tests \
#      --module assetcore.tests.test_imm15_low_stock_override
from __future__ import annotations

import unittest
from contextlib import suppress
from unittest.mock import patch

import frappe


class TestLowStockOverride(unittest.TestCase):
    """R7 §9.4.5 override-fallback canonical predicate.

    Fixture (exact acceptance dataset):
      - 1 part, min_stock_level = 50
      - bin A: qty_on_hand = 40, no override        → low by part-min (40 < 50)
      - bin B: qty_on_hand = 60, min_stock_override = 80 → low ONLY by override (60 < 80)

    Before fix: KPI / _count_low_stock counts 1 (bin B masked because the
    predicate compared against plain p.min_stock_level = 50 ≤ 60).
    After fix:  counts 2 (both bins low under effective_min).
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls._created: list[tuple[str, str]] = []

        any_uom = frappe.db.get_value("AC UOM", {}, "name") or None

        cls.wh_a = cls._ensure_wh("_TestLowOvr WH A")
        cls.wh_b = cls._ensure_wh("_TestLowOvr WH B")

        part_data = {
            "unit_cost": 50000, "is_active": 1, "min_stock_level": 50,
            "part_code": "_TESTLOWOVR-PART",
        }
        if any_uom:
            part_data["stock_uom"] = any_uom
        cls.part = cls._ensure_part("_TestLowOvr Part", part_data)

        # Bin A: 40 < part-min 50 → low (no override).
        cls._ensure_stock(cls.part, cls.wh_a, qty=40, override=0)
        # Bin B: 60 ≥ part-min 50 BUT < override 80 → low only by override.
        cls._ensure_stock(cls.part, cls.wh_b, qty=60, override=80)
        frappe.db.commit()

    # ── fixture helpers (self-cleaning, R-9) ──────────────────────────────
    @classmethod
    def _ensure_wh(cls, name: str) -> str:
        existing = frappe.db.get_value("AC Warehouse", {"warehouse_name": name}, "name")
        if existing:
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
    def _ensure_stock(cls, part: str, wh: str, *, qty: float, override: float) -> str:
        existing = frappe.db.get_value(
            "AC Spare Part Stock", {"spare_part": part, "warehouse": wh}, "name")
        if existing:
            frappe.db.set_value("AC Spare Part Stock", existing, {
                "qty_on_hand": qty, "available_qty": qty,
                "min_stock_override": override})
            return existing
        doc = frappe.get_doc({
            "doctype": "AC Spare Part Stock", "spare_part": part, "warehouse": wh,
            "qty_on_hand": qty, "available_qty": qty, "min_stock_override": override})
        doc.flags.ignore_mandatory = True
        doc.insert(ignore_permissions=True)
        cls._created.append(("AC Spare Part Stock", doc.name))
        return doc.name

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for dt, name in reversed(cls._created):
            with suppress(Exception):
                frappe.delete_doc(dt, name, force=True, ignore_permissions=True,
                                  delete_permanently=True)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")

    def _our_bins(self, rows: list, *, wh_key="warehouse") -> set:
        return {r[wh_key] for r in rows
                if r.get("spare_part") == self.part and r.get(wh_key) in (self.wh_a, self.wh_b)}

    # ── TDD-1: _count_low_stock honours per-bin override ──────────────────
    def test_low_stock_honors_bin_override(self):
        """[BE TDD-1] _count_low_stock() counts BOTH bins (binA part-min, binB override)."""
        from assetcore.services.imm15 import _count_low_stock
        # Count only contributed by OUR two bins (others may exist in DB).
        ours = frappe.db.sql("""
            SELECT COUNT(*) FROM `tabAC Spare Part Stock` s
            JOIN `tabAC Spare Part` p ON p.name = s.spare_part
            WHERE s.spare_part = %s
              AND COALESCE(NULLIF(s.min_stock_override,0), p.min_stock_level, 0) > 0
              AND s.qty_on_hand < COALESCE(NULLIF(s.min_stock_override,0), p.min_stock_level, 0)
        """, self.part)[0][0]
        self.assertEqual(ours, 2, "Both bins must be low under effective_min")
        # The global _count_low_stock must include both of our bins.
        # (We assert delta by toggling override off bin B → count drops by exactly 1.)
        before = _count_low_stock()
        frappe.db.set_value("AC Spare Part Stock",
                            {"spare_part": self.part, "warehouse": self.wh_b},
                            "min_stock_override", 0)
        try:
            after = _count_low_stock()
        finally:
            frappe.db.set_value("AC Spare Part Stock",
                                {"spare_part": self.part, "warehouse": self.wh_b},
                                "min_stock_override", 80)
        self.assertEqual(before - after, 1,
                         "binB (low only by override) must add exactly 1 to the KPI count")

    # ── TDD-2: KPI low_stock == dashboard low_stock_count == canonical list ─
    def test_kpi_low_stock_matches_canonical_dashboard(self):
        """[BE TDD-2] KPI low_stock_alerts == dashboard low_stock_count == canonical list len."""
        from assetcore.services.imm15 import get_dashboard_stats
        from assetcore.services.inventory import get_stock_overview

        kpi = get_dashboard_stats()["low_stock_alerts"]
        dash = get_stock_overview()["low_stock_count"]
        canonical = frappe.db.sql("""
            SELECT COUNT(*) FROM `tabAC Spare Part Stock` s
            JOIN `tabAC Spare Part` p ON p.name = s.spare_part
            WHERE p.is_active = 1
              AND COALESCE(NULLIF(s.min_stock_override,0), p.min_stock_level, 0) > 0
              AND s.qty_on_hand < COALESCE(NULLIF(s.min_stock_override,0), p.min_stock_level, 0)
        """)[0][0]
        self.assertEqual(kpi, dash, "KPI low_stock_alerts must equal dashboard low_stock_count")
        self.assertEqual(kpi, canonical,
                         "KPI must equal the canonical per-bin low count (override-aware)")

    # ── TDD-3: get_low_stock_alerts includes the override bin ─────────────
    def test_get_low_stock_alerts_includes_override_bin(self):
        """[BE TDD-3] alerts contain binB; its min_stock_level == effective_min (80, not 50)."""
        from assetcore.services.imm15 import get_low_stock_alerts
        res = get_low_stock_alerts()
        alerts = res["alerts"]
        ours = [a for a in alerts
                if a["spare_part"] == self.part and a["warehouse"] in (self.wh_a, self.wh_b)]
        bins = {a["warehouse"] for a in ours}
        self.assertEqual(bins, {self.wh_a, self.wh_b},
                         "both low bins (incl. override-only binB) must be in alerts")
        bin_b = next(a for a in ours if a["warehouse"] == self.wh_b)
        self.assertEqual(int(bin_b["min_stock_level"]), 80,
                         "alert must expose effective_min (80=override) not raw part-min (50)")
        # total must equal number of low rows returned (no divergence).
        self.assertEqual(res["total"], len(alerts))

    # ── TDD-4: drill low_stock=1 part-ids include override-only part ──────
    def test_drill_low_stock_filter_matches_kpi(self):
        """[BE TDD-4] drill returns a part low ONLY via override (no part-min-low bin)."""
        from assetcore.api.inventory import _low_stock_part_ids, list_spare_parts
        # Build a part whose ONLY low bin is an override-only one: part-min=10,
        # single bin qty=15 (≥ part-min, NOT low by part-min) with override=20
        # (15 < 20 → low only by override). On the old PLAIN predicate this part
        # is invisible to the drill; the override-aware predicate must surface it.
        any_uom = frappe.db.get_value("AC UOM", {}, "name") or None
        pdata = {"part_name": "_TestLowOvr DrillOnly", "min_stock_level": 10,
                 "is_active": 1, "unit_cost": 1}
        if any_uom:
            pdata["stock_uom"] = any_uom
        ovr_part = frappe.get_doc({"doctype": "AC Spare Part", **pdata})
        ovr_part.flags.ignore_mandatory = True
        ovr_part.insert(ignore_permissions=True)
        stock = frappe.get_doc({"doctype": "AC Spare Part Stock", "spare_part": ovr_part.name,
                                "warehouse": self.wh_a, "qty_on_hand": 15,
                                "available_qty": 15, "min_stock_override": 20})
        stock.flags.ignore_mandatory = True
        stock.insert(ignore_permissions=True)
        frappe.db.commit()
        try:
            ids = set(_low_stock_part_ids())
            self.assertIn(ovr_part.name, ids,
                          "drill must include a part low ONLY via per-bin override "
                          "(qty 15 ≥ part-min 10 but < override 20)")
            res = list_spare_parts(low_stock=1, page_size=500)
            payload = res.get("data") or res
            names = {p["name"] for p in payload["items"]}
            self.assertIn(ovr_part.name, names,
                          "drill list must contain the override-only-low part")
            # No-divergence: distinct low part-ids == drill list total.
            self.assertEqual(payload["pagination"]["total"], len(set(_low_stock_part_ids())),
                             "drill total must equal distinct low part-ids (no over/undercount)")
        finally:
            with suppress(Exception):
                frappe.delete_doc("AC Spare Part Stock", stock.name, force=True,
                                  ignore_permissions=True, delete_permanently=True)
            with suppress(Exception):
                frappe.delete_doc("AC Spare Part", ovr_part.name, force=True,
                                  ignore_permissions=True, delete_permanently=True)
            frappe.db.commit()

    # ── TDD-5: scheduler email includes the override bin ──────────────────
    def test_scheduler_email_includes_override_bin(self):
        """[BE TDD-5] check_low_stock() email body lists binB (was masked by SUM-across-wh)."""
        import assetcore.services.inventory as inv
        import assetcore.utils.email as email_mod
        captured: dict = {}

        def _fake_sendmail(recipients=None, subject=None, message=None, **kw):
            captured["message"] = message or ""
            captured["subject"] = subject or ""

        # check_low_stock() imports safe_sendmail / get_role_emails locally from
        # assetcore.utils.email at call time → patch the SOURCE module, not inv.
        with patch.object(email_mod, "safe_sendmail", _fake_sendmail), \
             patch.object(email_mod, "get_role_emails", lambda *_a, **_k: ["kho@benhvien.test"]):
            inv.check_low_stock()

        body = captured.get("message", "")
        # Email renders the human-readable warehouse_name (fallback to code).
        name_b = frappe.db.get_value("AC Warehouse", self.wh_b, "warehouse_name") or self.wh_b
        name_a = frappe.db.get_value("AC Warehouse", self.wh_a, "warehouse_name") or self.wh_a
        self.assertIn(name_b, body,
                      "binB (low only by override) must appear in scheduler email body; "
                      "SUM-across-warehouse previously masked it")
        # binA (low by part-min) must also be present.
        self.assertIn(name_a, body)
        # binB line must show effective_min (80=override), not raw part-min (50).
        self.assertRegex(body, rf"{name_b}.*định mức 80")

    # ── TDD-6 (regression): no-override unchanged; min=0 / inactive / above-min ─
    def test_no_override_unchanged(self):
        """[BE TDD-6] override-free part behaves on p.min_stock_level; min=0 / inactive / above-min not counted."""
        from assetcore.services.imm15 import _count_low_stock
        created: list[tuple[str, str]] = []
        any_uom = frappe.db.get_value("AC UOM", {}, "name") or None

        def mk_part(name, *, min_level, active=1):
            data = {"part_name": name, "min_stock_level": min_level,
                    "is_active": active, "unit_cost": 1}
            if any_uom:
                data["stock_uom"] = any_uom
            d = frappe.get_doc({"doctype": "AC Spare Part", **data})
            d.flags.ignore_mandatory = True
            d.insert(ignore_permissions=True)
            created.append(("AC Spare Part", d.name))
            return d.name

        def mk_stock(part, qty):
            d = frappe.get_doc({"doctype": "AC Spare Part Stock", "spare_part": part,
                                "warehouse": self.wh_a, "qty_on_hand": qty,
                                "available_qty": qty})
            d.flags.ignore_mandatory = True
            d.insert(ignore_permissions=True)
            created.append(("AC Spare Part Stock", d.name))
            return d.name

        try:
            base = _count_low_stock()
            # min=0 part → never counted even when qty 0.
            p_zero = mk_part("_TestLowOvr ZeroMin", min_level=0)
            mk_stock(p_zero, 0)
            # inactive part below min → never counted.
            p_inactive = mk_part("_TestLowOvr Inactive", min_level=10, active=0)
            mk_stock(p_inactive, 1)
            # above-min part → never counted.
            p_above = mk_part("_TestLowOvr Above", min_level=5)
            mk_stock(p_above, 99)
            frappe.db.commit()
            self.assertEqual(_count_low_stock(), base,
                             "min=0 / inactive / above-min must NOT change the low count")

            # A plain below-min part (no override) → +1.
            p_low = mk_part("_TestLowOvr PlainLow", min_level=10)
            mk_stock(p_low, 3)
            frappe.db.commit()
            self.assertEqual(_count_low_stock(), base + 1,
                             "override-free below-min part must add exactly 1 (legacy behaviour)")
        finally:
            for dt, name in reversed(created):
                with suppress(Exception):
                    frappe.delete_doc(dt, name, force=True, ignore_permissions=True,
                                      delete_permanently=True)
            frappe.db.commit()


if __name__ == "__main__":
    unittest.main()
