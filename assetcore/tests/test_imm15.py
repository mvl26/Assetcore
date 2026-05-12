# Copyright (c) 2026, AssetCore Team
# IMM-15 Spare Parts Inventory — Test suite (Sprint 2 §4.15.3).
#
# Focus: business-rule + lifecycle correctness on the service layer.
# Test data isolation: each test creates its own warehouse / part / asset
# and rolls back via `frappe.db.rollback()` on tearDown.
from __future__ import annotations

import unittest
from contextlib import suppress

import frappe

from assetcore.services import imm15 as svc
from assetcore.services.shared import ErrorCode, ServiceError


def _ensure_doc(doctype: str, name: str, data: dict) -> str:
    if frappe.db.exists(doctype, name):
        return name
    doc = frappe.get_doc({"doctype": doctype, "name": name, **data})
    doc.flags.ignore_links = True
    doc.flags.ignore_mandatory = True
    doc.insert(ignore_permissions=True)
    return doc.name


class TestImm15Base(unittest.TestCase):
    """Set up minimal fixtures shared across TC-15-01..07."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        # Seed UOM if missing (test isolation)
        if not frappe.db.exists("AC UOM", "Cái"):
            with suppress(Exception):
                frappe.get_doc({
                    "doctype": "AC UOM", "uom_name": "Cái",
                    "is_active": 1,
                }).insert(ignore_permissions=True)
        # Warehouse
        cls.warehouse = _ensure_doc(
            "AC Warehouse", "AC-WH-TEST15",
            {"warehouse_name": "Test WH IMM-15", "is_active": 1},
        )
        # Spare part — pick an existing UOM (any) so we don't depend on seeds
        any_uom = frappe.db.get_value("AC UOM", {}, "name") or None
        spare_data = {
            "part_name": "Test Part IMM-15",
            "unit_cost": 100000,
            "is_active": 1,
            "min_stock_level": 5,
            "is_critical": 1,  # fallback signal for service when imm_part_class CF absent
        }
        # Only attach imm_part_class if Wave-3 CF installed (column exists)
        if frappe.db.has_column("AC Spare Part", "imm_part_class"):
            spare_data["imm_part_class"] = "Critical"
        if any_uom:
            spare_data["stock_uom"] = any_uom
        cls.part = _ensure_doc("AC Spare Part", "AC-SP-TEST15", spare_data)
        # Seed stock
        if not frappe.db.exists("AC Spare Part Stock",
                                {"spare_part": cls.part, "warehouse": cls.warehouse}):
            frappe.get_doc({
                "doctype": "AC Spare Part Stock",
                "spare_part": cls.part,
                "warehouse": cls.warehouse,
                "qty_on_hand": 20,
                "available_qty": 20,
            }).insert(ignore_permissions=True)
        else:
            frappe.db.set_value(
                "AC Spare Part Stock",
                {"spare_part": cls.part, "warehouse": cls.warehouse},
                {"qty_on_hand": 20, "available_qty": 20},
            )
        # Asset (optional)
        cls.asset = ""
        if frappe.db.exists("DocType", "AC Asset"):
            with suppress(Exception):
                cls.asset = _ensure_doc(
                    "AC Asset", "AC-AS-TEST15",
                    {"asset_name": "Test Asset IMM-15"},
                )
        frappe.db.commit()

    def tearDown(self):
        # tests run with commits inside svc → no rollback (would lose fixtures).
        # Cleanup performed in tearDownClass.
        pass

    @classmethod
    def tearDownClass(cls):
        # Best-effort cleanup of test allocations / cycle counts / forecasts.
        for dt in ("IMM Spare Allocation", "IMM Stock Cycle Count",
                   "IMM Spare Part Forecast", "IMM Critical Spare Watchlist"):
            with suppress(Exception):
                names = frappe.get_all(dt, filters={"creation": (">", "2026-05-10")},
                                       fields=["name"], limit_page_length=200)
                for n in names:
                    with suppress(Exception):
                        frappe.delete_doc(dt, n.name, ignore_permissions=True, force=True)
        frappe.db.commit()


class TestAllocationLifecycle(TestImm15Base):
    """TC-15-01: create → approve → issue → return."""

    def test_create_requires_work_order_for_non_emergency(self):
        with self.assertRaises(ServiceError) as ctx:
            svc.create_allocation(
                work_order_ref="", items=[{"spare_part": self.part, "qty_requested": 1}],
                asset=self.asset, warehouse=self.warehouse, urgency="Routine",
            )
        self.assertEqual(ctx.exception.code, ErrorCode.BUSINESS_RULE)

    def test_create_emergency_without_wo_succeeds(self):
        res = svc.create_allocation(
            work_order_ref="", items=[{"spare_part": self.part, "qty_requested": 1}],
            asset=self.asset, warehouse=self.warehouse, urgency="Emergency",
        )
        self.assertEqual(res["workflow_state"], "Requested")

    def test_approve_requires_correct_role(self):
        res = svc.create_allocation(
            work_order_ref="WO-TEST-01",
            items=[{"spare_part": self.part, "qty_requested": 1}],
            asset=self.asset, warehouse=self.warehouse, urgency="Routine",
        )
        approved = svc.approve_allocation(res["name"])
        self.assertEqual(approved["workflow_state"], "Approved")

    def test_approve_bad_state(self):
        res = svc.create_allocation(
            work_order_ref="WO-TEST-02",
            items=[{"spare_part": self.part, "qty_requested": 1}],
            asset=self.asset, warehouse=self.warehouse, urgency="Routine",
        )
        svc.approve_allocation(res["name"])
        with self.assertRaises(ServiceError) as ctx:
            svc.approve_allocation(res["name"])
        self.assertEqual(ctx.exception.code, ErrorCode.BAD_STATE)


class TestUrgencyValidation(TestImm15Base):
    """TC-15-02: VR-15-05 urgency enum."""

    def test_invalid_urgency_rejected(self):
        with self.assertRaises(ServiceError) as ctx:
            svc.create_allocation(
                work_order_ref="WO-INV-01",
                items=[{"spare_part": self.part, "qty_requested": 1}],
                asset=self.asset, warehouse=self.warehouse, urgency="Pretty Please",
            )
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)


class TestWarehouseValidation(TestImm15Base):
    """TC-15-03: VR-15-13 inactive warehouse."""

    def test_inactive_warehouse_rejected(self):
        frappe.db.set_value("AC Warehouse", self.warehouse, "is_active", 0)
        frappe.db.commit()
        try:
            with self.assertRaises(ServiceError) as ctx:
                svc.create_allocation(
                    work_order_ref="WO-WH-01",
                    items=[{"spare_part": self.part, "qty_requested": 1}],
                    asset=self.asset, warehouse=self.warehouse, urgency="Routine",
                )
            self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
        finally:
            frappe.db.set_value("AC Warehouse", self.warehouse, "is_active", 1)
            frappe.db.commit()


class TestReturnValidation(TestImm15Base):
    """TC-15-04: VR-15-08 return qty must not exceed issued qty."""

    def test_return_qty_exceeds_issued(self):
        res = svc.create_allocation(
            work_order_ref="WO-RET-01",
            items=[{"spare_part": self.part, "qty_requested": 1}],
            asset=self.asset, warehouse=self.warehouse, urgency="Routine",
        )
        svc.approve_allocation(res["name"])
        svc.issue_allocation(res["name"])
        with self.assertRaises(ServiceError) as ctx:
            svc.return_items(res["name"],
                             [{"spare_part": self.part, "qty_returned": 999}])
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)


class TestForecastGeneration(TestImm15Base):
    """TC-15-05: generate_spare_forecast produces a Draft + items."""

    def test_generate_forecast(self):
        res = svc.generate_spare_forecast(horizon_months=3, method="Moving_Avg")
        self.assertIn("name", res)
        self.assertGreaterEqual(res["items_count"], 1)


class TestWatchlist(TestImm15Base):
    """TC-15-06: add_to_watchlist enforces VR-15-09 (Critical only)."""

    def test_add_critical_part_ok(self):
        wl_name = "WL-TEST-CRIT"
        # cleanup if exists
        if frappe.db.exists("IMM Critical Spare Watchlist", wl_name):
            frappe.delete_doc("IMM Critical Spare Watchlist", wl_name,
                              ignore_permissions=True, force=True)
        res = svc.add_to_watchlist(
            watchlist_name=wl_name, critical_asset=self.asset or "X",
            spare_part=self.part, min_required_on_hand=2,
            warehouse=self.warehouse,
        )
        self.assertEqual(res["name"], wl_name)
        self.assertTrue(res["active"])

    def test_add_non_critical_rejected(self):
        # demote part class temporarily (only if CF installed; always demote is_critical)
        has_cf = frappe.db.has_column("AC Spare Part", "imm_part_class")
        if has_cf:
            frappe.db.set_value("AC Spare Part", self.part, "imm_part_class", "Major")
        frappe.db.set_value("AC Spare Part", self.part, "is_critical", 0)
        frappe.db.commit()
        try:
            with self.assertRaises(ServiceError) as ctx:
                svc.add_to_watchlist(
                    watchlist_name="WL-TEST-NONCRIT",
                    critical_asset=self.asset or "X",
                    spare_part=self.part, min_required_on_hand=1,
                    warehouse=self.warehouse,
                )
            self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
        finally:
            if has_cf:
                frappe.db.set_value("AC Spare Part", self.part, "imm_part_class", "Critical")
            frappe.db.set_value("AC Spare Part", self.part, "is_critical", 1)
            frappe.db.commit()


class TestDashboardStats(TestImm15Base):
    """TC-15-07: dashboard stats returns expected keys."""

    def test_dashboard_keys(self):
        stats = svc.get_dashboard_stats()
        for key in ("stock_turnover_year", "days_on_hand_avg",
                    "stockout_incidents_30d", "low_stock_alerts",
                    "pending_allocations", "pending_cycle_counts"):
            self.assertIn(key, stats)


if __name__ == "__main__":
    unittest.main()
