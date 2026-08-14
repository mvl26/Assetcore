# Copyright (c) 2026, AssetCore Team
# IMM-15 Spare Parts Inventory — Test suite (Sprint 2 §4.15.3).
#
# Focus: business-rule + lifecycle correctness on the service layer.
# Test data isolation: each test creates its own warehouse / part / asset
# and rolls back via `frappe.db.rollback()` on tearDown.
from __future__ import annotations

import json
import unittest
from contextlib import suppress

import frappe

from assetcore.services import imm15 as svc
from assetcore.services.shared import ErrorCode, ServiceError
from assetcore.tests._asset_cleanup import purge_asset
from assetcore.utils.messages import MSG
from assetcore.tests._helpers.paths import APP_ROOT


def _ensure_doc(doctype: str, lookup: dict, data: dict) -> str:
    """Idempotent fixture create — look up by a unique business field.

    AC Warehouse / AC Spare Part / AC Asset are autonamed, so an explicit
    ``name`` is IGNORED on insert. Matching on ``name`` therefore never finds the
    existing fixture → every test run leaks a fresh autonamed record (LL-TEST-9).
    Always match on the business key carried in ``lookup``.
    """
    existing = frappe.db.get_value(doctype, lookup, "name")
    if existing:
        return existing
    doc = frappe.get_doc({"doctype": doctype, **lookup, **data})
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
        # Warehouse — match on business name (autonamed → explicit name ignored)
        cls.warehouse = _ensure_doc(
            "AC Warehouse", {"warehouse_name": "_Test WH IMM-15"},
            {"is_active": 1},
        )
        # Spare part — pick an existing UOM (any) so we don't depend on seeds
        any_uom = frappe.db.get_value("AC UOM", {}, "name") or None
        spare_data = {
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
        cls.part = _ensure_doc(
            "AC Spare Part", {"part_name": "_Test Part IMM-15"}, spare_data
        )
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
        # Department — receiver for Issue stock movements (Slide 27, VR via IMM-15)
        cls.department = ""
        if frappe.db.exists("DocType", "AC Department"):
            with suppress(Exception):
                cls.department = frappe.db.get_value(
                    "AC Department", {"department_name": "_Test Dept IMM-15"}, "name"
                )
                if not cls.department:
                    cls.department = frappe.get_doc({
                        "doctype": "AC Department",
                        "department_name": "_Test Dept IMM-15",
                    }).insert(ignore_permissions=True).name
        # Asset (optional) — must carry a department so issue movements validate
        cls.asset = ""
        if frappe.db.exists("DocType", "AC Asset"):
            with suppress(Exception):
                cls.asset = _ensure_doc(
                    "AC Asset", {"asset_name": "_Test Asset IMM-15"},
                    {"department": cls.department},
                )
                if cls.asset and cls.department:
                    frappe.db.set_value("AC Asset", cls.asset, "department", cls.department)
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
        # Cancel + remove stock movements tied to the test part (block part delete).
        with suppress(Exception):
            for sm in frappe.get_all(
                "AC Stock Movement Item", filters={"spare_part": cls.part},
                fields=["parent"], pluck="parent",
            ):
                with suppress(Exception):
                    doc = frappe.get_doc("AC Stock Movement", sm)
                    if doc.docstatus == 1:
                        doc.cancel()
                    frappe.delete_doc("AC Stock Movement", sm, force=True,
                                      ignore_permissions=True)
        # Remove the shared _Test master fixtures (FK-safe order, best-effort).
        with suppress(Exception):
            for st in frappe.get_all("AC Spare Part Stock",
                                     filters={"spare_part": cls.part}, pluck="name"):
                frappe.delete_doc("AC Spare Part Stock", st, force=True,
                                  ignore_permissions=True)
        if getattr(cls, "asset", ""):
            with suppress(Exception):
                purge_asset(cls.asset)
        for dt, name in (("AC Spare Part", getattr(cls, "part", "")),
                         ("AC Warehouse", getattr(cls, "warehouse", "")),
                         ("AC Department", getattr(cls, "department", ""))):
            if name:
                with suppress(Exception):
                    frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
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


class TestIssueQtyEqualsApproved(TestImm15Base):
    """BR-15-15 (04 §III-bis.7): số đã XUẤT == số đã GIỮ-CHỖ ==
    COALESCE(NULLIF(qty_approved,0), qty_requested). Khi approver cắt
    qty_approved, issue phải dispense số đã duyệt (KHÔNG phải qty_requested thuần).
    """

    def _bin_qty(self):
        row = frappe.db.get_value(
            "AC Spare Part Stock",
            {"spare_part": self.part, "warehouse": self.warehouse},
            ["qty_on_hand", "reserved_qty"], as_dict=True,
        ) or {}
        return float(row.get("qty_on_hand") or 0), float(row.get("reserved_qty") or 0)

    def _reset_bin(self, on_hand=20):
        # Cancel any still-holding allocation on this shared bin so reserved_qty is a
        # clean slate (other tests in the class create allocations on the same part).
        for n in frappe.get_all(
            "IMM Spare Allocation",
            filters={"warehouse_from": self.warehouse,
                     "allocation_status": ("in", ["Requested", "Approved", "Picked"])},
            pluck="name",
        ):
            with suppress(Exception):
                svc.cancel_allocation(n)
        frappe.db.set_value(
            "AC Spare Part Stock",
            {"spare_part": self.part, "warehouse": self.warehouse},
            {"qty_on_hand": on_hand, "reserved_qty": 0, "available_qty": on_hand},
        )
        frappe.db.commit()

    def test_issue_dispenses_approved_qty_not_requested(self):
        """Approve cắt 10→4 → qty_issued==4, qty_on_hand giảm 4 (KHÔNG 10), reserved về 0."""
        self._reset_bin(20)
        res = svc.create_allocation(
            work_order_ref="WO-BR1515-01",
            items=[{"spare_part": self.part, "qty_requested": 10}],
            asset=self.asset, warehouse=self.warehouse, urgency="Routine",
        )
        name = res["name"]
        svc.approve_allocation(name)
        # Approver cắt số duyệt 10 → 4 (mô phỏng điều chỉnh khi duyệt qua FE/API).
        doc = frappe.get_doc("IMM Spare Allocation", name)
        doc.items[0].qty_approved = 4
        doc.flags.ignore_links = True
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        # reserved phải phản ánh số đã duyệt = 4 (recompute_reserved SoT).
        from assetcore.services.inventory import recompute_reserved
        recompute_reserved(self.warehouse, self.part)
        _, reserved_before = self._bin_qty()
        self.assertEqual(reserved_before, 4.0,
                         "reserved phải == qty_approved=4 trước issue")

        on_hand_before, _ = self._bin_qty()
        svc.issue_allocation(name)

        issued = frappe.db.get_value(
            "IMM Spare Allocation Item",
            {"parent": name, "spare_part": self.part}, "qty_issued",
        )
        self.assertEqual(float(issued), 4.0,
                         "BR-15-15: phải xuất số ĐÃ DUYỆT (4), không phải qty_requested (10)")
        on_hand_after, reserved_after = self._bin_qty()
        self.assertEqual(on_hand_before - on_hand_after, 4.0,
                         "qty_on_hand chỉ trừ đúng số duyệt (4), không phải 10")
        self.assertEqual(reserved_after, 0.0,
                         "reserved release về 0 sau issue (RELEASE on terminal)")

    def test_issue_backward_compat_no_approved_qty(self):
        """qty_approved chưa set (0/NULL) → issue theo qty_requested (hành vi cũ giữ nguyên)."""
        self._reset_bin(20)
        res = svc.create_allocation(
            work_order_ref="WO-BR1515-02",
            items=[{"spare_part": self.part, "qty_requested": 6}],
            asset=self.asset, warehouse=self.warehouse, urgency="Routine",
        )
        name = res["name"]
        svc.approve_allocation(name)  # KHÔNG điều chỉnh qty_approved
        svc.issue_allocation(name)
        issued = frappe.db.get_value(
            "IMM Spare Allocation Item",
            {"parent": name, "spare_part": self.part}, "qty_issued",
        )
        self.assertEqual(float(issued), 6.0,
                         "backward-compat: qty_approved NULL → xuất qty_requested=6")

    def test_gate_uses_effective_qty_after_cut(self):
        """VR-15-03 dùng số sẽ-thật-sự-xuất: on_hand=5, requested=10, approved=4 → issue OK."""
        self._reset_bin(5)
        res = svc.create_allocation(
            work_order_ref="WO-BR1515-03",
            items=[{"spare_part": self.part, "qty_requested": 10}],
            asset=self.asset, warehouse=self.warehouse, urgency="Routine",
        )
        name = res["name"]
        svc.approve_allocation(name)
        doc = frappe.get_doc("IMM Spare Allocation", name)
        doc.items[0].qty_approved = 4
        doc.flags.ignore_links = True
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        from assetcore.services.inventory import recompute_reserved
        recompute_reserved(self.warehouse, self.part)
        # gate so 4 (số duyệt) với on_hand=5 → đủ → KHÔNG raise.
        svc.issue_allocation(name)
        issued = frappe.db.get_value(
            "IMM Spare Allocation Item",
            {"parent": name, "spare_part": self.part}, "qty_issued",
        )
        self.assertEqual(float(issued), 4.0)


class TestAllocationValue(TestImm15Base):
    """BR-15-16 (04 §III-bis.8): line_value = value_qty × unit_value;
    total_value = Σ line_value; value_qty lifecycle-aware (qty_issued nếu đã xuất,
    ngược lại effective_alloc_qty). MỘT writer ở controller — service KHÔNG clobber.
    """

    def _reset_bin(self, on_hand=50):
        for n in frappe.get_all(
            "IMM Spare Allocation",
            filters={"warehouse_from": self.warehouse,
                     "allocation_status": ("in", ["Requested", "Approved", "Picked"])},
            pluck="name",
        ):
            with suppress(Exception):
                svc.cancel_allocation(n)
        frappe.db.set_value(
            "AC Spare Part Stock",
            {"spare_part": self.part, "warehouse": self.warehouse},
            {"qty_on_hand": on_hand, "reserved_qty": 0, "available_qty": on_hand},
        )
        frappe.db.commit()

    def _unit_value(self):
        return float(frappe.db.get_value("AC Spare Part", self.part, "unit_cost") or 0)

    def test_total_value_follows_issued_qty_not_requested(self):
        """Approve cắt 10→4, Issue → total_value = 4×unit (KHÔNG 10×unit — chống clobber)."""
        self._reset_bin(50)
        uv = self._unit_value()
        res = svc.create_allocation(
            work_order_ref="WO-VAL-01",
            items=[{"spare_part": self.part, "qty_requested": 10}],
            asset=self.asset, warehouse=self.warehouse, urgency="Routine",
        )
        name = res["name"]
        svc.approve_allocation(name)
        doc = frappe.get_doc("IMM Spare Allocation", name)
        doc.items[0].qty_approved = 4
        doc.flags.ignore_links = True
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        from assetcore.services.inventory import recompute_reserved
        recompute_reserved(self.warehouse, self.part)
        svc.issue_allocation(name)
        doc = frappe.get_doc("IMM Spare Allocation", name)
        self.assertEqual(float(doc.total_value), 4.0 * uv,
                         "total_value phải theo qty_issued=4 (KHÔNG bị controller clobber về 10)")
        self.assertEqual(float(doc.items[0].line_value), 4.0 * uv,
                         "line_value = 4×unit_value (computed, KHÔNG dead column)")

    def test_total_equals_sum_of_line_values(self):
        """INVARIANT total_value == Σ line_value (sau approve, trước issue)."""
        self._reset_bin(50)
        uv = self._unit_value()
        res = svc.create_allocation(
            work_order_ref="WO-VAL-02",
            items=[{"spare_part": self.part, "qty_requested": 7}],
            asset=self.asset, warehouse=self.warehouse, urgency="Routine",
        )
        name = res["name"]
        svc.approve_allocation(name)
        doc = frappe.get_doc("IMM Spare Allocation", name)
        # chưa xuất → value_qty = effective_alloc_qty = qty_requested 7 (qty_approved NULL)
        self.assertEqual(float(doc.items[0].line_value), 7.0 * uv)
        self.assertEqual(float(doc.total_value),
                         sum(float(it.line_value or 0) for it in doc.items))

    def test_line_value_committed_before_issue(self):
        """Backward-compat: dòng mới Requested (chưa duyệt/xuất) → line_value theo qty_requested."""
        self._reset_bin(50)
        uv = self._unit_value()
        res = svc.create_allocation(
            work_order_ref="WO-VAL-03",
            items=[{"spare_part": self.part, "qty_requested": 3}],
            asset=self.asset, warehouse=self.warehouse, urgency="Routine",
        )
        doc = frappe.get_doc("IMM Spare Allocation", res["name"])
        self.assertEqual(float(doc.items[0].line_value), 3.0 * uv,
                         "Requested → value_qty=qty_requested=3 (giá trị cam kết, KHÔNG 0)")


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


class TestDashboardLowStockPerBin(unittest.TestCase):
    """BUG-15-03 regression: the /inventory dashboard low-stock KPI
    (assetcore.services.inventory.get_stock_overview) MUST be computed
    per-warehouse-bin, consistent with the /stock page
    (assetcore.api.inventory.list_stock_levels with low_only=1).

    Old defect: SUM(qty_on_hand) across all warehouses was compared to the
    part min, so a part with two bins (2 and 4, min 5) summed to 6 ≥ 5 and
    was reported as NOT low — while the stock page correctly flagged both
    bins. This test sets up exactly that masking scenario.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        any_uom = frappe.db.get_value("AC UOM", {}, "name") or None
        cls.wh_a = _ensure_doc("AC Warehouse", {"warehouse_name": "_Test Low WH A"},
                                {"is_active": 1})
        cls.wh_b = _ensure_doc("AC Warehouse", {"warehouse_name": "_Test Low WH B"},
                                {"is_active": 1})
        part_data = {"unit_cost": 50000, "is_active": 1, "min_stock_level": 5}
        if any_uom:
            part_data["stock_uom"] = any_uom
        cls.part = _ensure_doc("AC Spare Part", {"part_name": "_Test Low Stock Part"},
                               part_data)
        # Bin A qty 2 (< 5), Bin B qty 4 (< 5). SUM = 6 ≥ 5 (would mask under
        # the old aggregate logic) but each bin is individually below min.
        for wh, qty in ((cls.wh_a, 2), (cls.wh_b, 4)):
            if not frappe.db.exists("AC Spare Part Stock",
                                    {"spare_part": cls.part, "warehouse": wh}):
                frappe.get_doc({
                    "doctype": "AC Spare Part Stock", "spare_part": cls.part,
                    "warehouse": wh, "qty_on_hand": qty, "available_qty": qty,
                }).insert(ignore_permissions=True)
            else:
                frappe.db.set_value(
                    "AC Spare Part Stock",
                    {"spare_part": cls.part, "warehouse": wh},
                    {"qty_on_hand": qty, "available_qty": qty})
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        with suppress(Exception):
            for wh in (cls.wh_a, cls.wh_b):
                frappe.db.delete("AC Spare Part Stock",
                                 {"spare_part": cls.part, "warehouse": wh})
            frappe.delete_doc("AC Spare Part", cls.part,
                              ignore_permissions=True, force=True)
            for wh in (cls.wh_a, cls.wh_b):
                frappe.delete_doc("AC Warehouse", wh,
                                  ignore_permissions=True, force=True)
        frappe.db.commit()

    def _stock_page_low_bins(self) -> set:
        """Ground truth: bins the /stock page flags as low for our part."""
        from assetcore.api import inventory as inv_api
        res = inv_api.list_stock_levels(page=1, page_size=200, low_only=1,
                                        spare_part=self.part)
        return {(r["warehouse"], r["spare_part"]) for r in res["data"]["items"]}

    def test_overview_low_stock_is_per_bin(self):
        from assetcore.services.inventory import get_stock_overview
        ov = get_stock_overview()
        ours = [i for i in ov["low_stock_items"] if i["spare_part"] == self.part]
        # Both bins must surface (old SUM logic would surface neither).
        bins = {(i["warehouse"], i["spare_part"]) for i in ours}
        self.assertEqual(bins, {(self.wh_a, self.part), (self.wh_b, self.part)})
        for i in ours:
            self.assertEqual(i["min_stock_level"], 5)
            self.assertLess(i["total_qty"], i["min_stock_level"])

    def test_overview_count_matches_stock_page(self):
        from assetcore.services.inventory import get_stock_overview
        ov = get_stock_overview()
        ov_bins = {(i["warehouse"], i["spare_part"])
                   for i in ov["low_stock_items"]
                   if i["spare_part"] == self.part}
        self.assertEqual(ov_bins, self._stock_page_low_bins())
        # The KPI count is the full per-bin count, not capped at the 10-row
        # display list; it must be ≥ the 2 bins we created.
        self.assertGreaterEqual(ov["low_stock_count"], 2)


class TestLowStockBinOverride(unittest.TestCase):
    """R7 §9.4.5 / BUG-15-03 — canonical low-stock predicate honours
    min_stock_override per-bin across KPI, dashboard, drill, alerts and the
    scheduler. effective_min = COALESCE(NULLIF(s.min_stock_override,0),
    p.min_stock_level, 0); low ⟺ effective_min > 0 AND qty_on_hand < effective_min.

    Dataset: 1 part min_stock_level=50, 2 bins —
      binA qty=40           → low theo part-min (40 < 50)
      binB qty=60, override=80 → low CHỈ theo override (60 < 80, nhưng 60 ≥ 50)
    Trước fix: KPI/_count_low_stock đếm 1 (chỉ binA); sau fix đếm 2.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        any_uom = frappe.db.get_value("AC UOM", {}, "name") or None
        cls.wh_a = _ensure_doc("AC Warehouse", {"warehouse_name": "_Test Ovr WH A"},
                               {"is_active": 1})
        cls.wh_b = _ensure_doc("AC Warehouse", {"warehouse_name": "_Test Ovr WH B"},
                               {"is_active": 1})
        # Control parts used by regression cases (TDD-6).
        part_data = {"unit_cost": 50000, "is_active": 1, "min_stock_level": 50}
        if any_uom:
            part_data["stock_uom"] = any_uom
        cls.part = _ensure_doc("AC Spare Part",
                               {"part_name": "_Test Ovr Low Part"}, part_data)
        # part with NO override anywhere — must behave on part-min only (TDD-6).
        cls.part_plain = _ensure_doc("AC Spare Part",
                                     {"part_name": "_Test Ovr Plain Part"},
                                     dict(part_data))
        # inactive part (must NOT be counted) — TDD-6.
        cls.part_inactive = _ensure_doc(
            "AC Spare Part", {"part_name": "_Test Ovr Inactive Part"},
            {**part_data, "is_active": 0})

        def _set_bin(part, wh, qty, override=0):
            if not frappe.db.exists("AC Spare Part Stock",
                                    {"spare_part": part, "warehouse": wh}):
                frappe.get_doc({
                    "doctype": "AC Spare Part Stock", "spare_part": part,
                    "warehouse": wh, "qty_on_hand": qty, "available_qty": qty,
                    "min_stock_override": override,
                }).insert(ignore_permissions=True)
            else:
                frappe.db.set_value(
                    "AC Spare Part Stock",
                    {"spare_part": part, "warehouse": wh},
                    {"qty_on_hand": qty, "available_qty": qty,
                     "min_stock_override": override})

        # The headline dataset for the override predicate.
        _set_bin(cls.part, cls.wh_a, 40, 0)    # low by part-min (40 < 50)
        _set_bin(cls.part, cls.wh_b, 60, 80)   # low ONLY by override (60 < 80)
        # Regression controls.
        _set_bin(cls.part_plain, cls.wh_a, 40, 0)   # low by part-min
        _set_bin(cls.part_plain, cls.wh_b, 60, 0)   # 60 ≥ 50 → NOT low
        _set_bin(cls.part_inactive, cls.wh_a, 10, 0)  # below min but inactive → NOT counted
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        with suppress(Exception):
            for part in (cls.part, cls.part_plain, cls.part_inactive):
                frappe.db.delete("AC Spare Part Stock", {"spare_part": part})
                frappe.delete_doc("AC Spare Part", part,
                                  ignore_permissions=True, force=True)
            for wh in (cls.wh_a, cls.wh_b):
                frappe.delete_doc("AC Warehouse", wh,
                                  ignore_permissions=True, force=True)
        frappe.db.commit()

    def _our_low_bins(self, rows: list, key_wh="warehouse", key_sp="spare_part") -> set:
        return {(r[key_wh], r[key_sp]) for r in rows if r[key_sp] == self.part}

    # ── TDD-1 ──────────────────────────────────────────────────────────────
    def test_low_stock_honors_bin_override(self):
        from assetcore.services.inventory import count_low_stock_bins
        # Count restricted to our two bins via per-warehouse spot checks.
        wh_a_low = count_low_stock_bins(warehouse=self.wh_a)
        wh_b_low = count_low_stock_bins(warehouse=self.wh_b)
        # binA low (part-min) and binB low (override) — but other parts share
        # wh_a (part_plain binA also low). Assert OUR contribution via the list.
        from assetcore.services.imm15 import get_low_stock_alerts
        ours = self._our_low_bins(get_low_stock_alerts()["alerts"])
        self.assertEqual(ours, {(self.wh_a, self.part), (self.wh_b, self.part)},
                         "both binA (part-min) and binB (override) must be low")
        self.assertGreaterEqual(wh_a_low, 1)
        self.assertGreaterEqual(wh_b_low, 1)
        # _count_low_stock (KPI source) must include both our bins.
        self.assertEqual(svc._count_low_stock(),
                         _canonical_total(),
                         "_count_low_stock must equal canonical bin count")

    # ── TDD-2 ──────────────────────────────────────────────────────────────
    def test_kpi_low_stock_matches_canonical_dashboard(self):
        from assetcore.services.inventory import (get_stock_overview,
                                                  count_low_stock_bins)
        kpi = svc.get_dashboard_stats()["low_stock_alerts"]
        dash = get_stock_overview()["low_stock_count"]
        canonical = count_low_stock_bins()
        self.assertEqual(kpi, dash)
        self.assertEqual(kpi, canonical)

    # ── TDD-3 ──────────────────────────────────────────────────────────────
    def test_get_low_stock_alerts_includes_override_bin(self):
        from assetcore.services.imm15 import get_low_stock_alerts
        res = get_low_stock_alerts()
        by_wh = {(a["warehouse"]): a for a in res["alerts"]
                 if a["spare_part"] == self.part}
        self.assertIn(self.wh_b, by_wh, "override-low binB must appear")
        # effective_min returned, not raw part min (80 not 50).
        self.assertEqual(by_wh[self.wh_b]["min_stock_level"], 80)
        self.assertEqual(by_wh[self.wh_a]["min_stock_level"], 50)
        # total == number of low bins (canonical).
        from assetcore.services.inventory import count_low_stock_bins
        self.assertEqual(res["total"], count_low_stock_bins())

    # ── TDD-4 ──────────────────────────────────────────────────────────────
    def test_drill_low_stock_filter_matches_kpi(self):
        from assetcore.api import inventory as inv_api
        from assetcore.services.inventory import low_stock_part_ids
        res = inv_api.list_spare_parts(page=1, page_size=200, low_stock=1)
        drill_ids = {r["name"] for r in res["data"]["items"]}
        # our part (low because of binA part-min AND binB override) must appear.
        self.assertIn(self.part, drill_ids)
        # the drill set equals the canonical part-distinct low set.
        self.assertEqual(drill_ids, set(low_stock_part_ids()))
        # part_inactive must NOT appear (inactive).
        self.assertNotIn(self.part_inactive, drill_ids)

    # ── TDD-5 ──────────────────────────────────────────────────────────────
    def test_scheduler_email_includes_override_bin(self):
        from unittest.mock import patch
        from assetcore.services import inventory as inv_svc
        import assetcore.utils.email as email_mod
        captured = {}

        def _fake_sendmail(*, recipients, subject, message):
            captured["message"] = message
            captured["subject"] = subject

        # check_low_stock imports get_role_emails / safe_sendmail lazily from
        # assetcore.utils.email at call time — patch the source module.
        with patch.object(email_mod, "get_role_emails", return_value=["k@x.test"]), \
             patch.object(email_mod, "safe_sendmail", side_effect=_fake_sendmail):
            inv_svc.check_low_stock()
        msg = captured.get("message", "")
        self.assertIn("_Test Ovr Low Part", msg)
        # both bins present; override bin shows effective_min 80 (was SUM-masked).
        self.assertIn("định mức 80", msg)
        self.assertIn("định mức 50", msg)

    # ── TDD-6 (regression) ───────────────────────────────────────────────────
    def test_no_override_unchanged(self):
        from assetcore.services.imm15 import get_low_stock_alerts
        alerts = get_low_stock_alerts()["alerts"]
        plain = {(a["warehouse"]): a for a in alerts
                 if a["spare_part"] == self.part_plain}
        # part_plain binA (40 < 50) low; binB (60 ≥ 50, no override) NOT low.
        self.assertIn(self.wh_a, plain)
        self.assertEqual(plain[self.wh_a]["min_stock_level"], 50)
        self.assertNotIn(self.wh_b, plain)
        # inactive part never appears.
        self.assertFalse(any(a["spare_part"] == self.part_inactive for a in alerts))


def _canonical_total() -> int:
    from assetcore.services.inventory import count_low_stock_bins
    return count_low_stock_bins()


class TestExpiringBatches(unittest.TestCase):
    """TC-15-EXP-01..06 — check_expiring_batches window predicate + naming contract.

    Bug gốc (vòng 21):
      • dict-filter trùng key 'expiry_date' → cận trên 30 ngày bị Python nuốt,
        predicate còn lại chỉ `>= today` → fire MỌI batch chưa hết hạn.
      • field 'batch_code' KHÔNG tồn tại (thật = 'batch_no') → unknown-column,
        trước đây bị `except Exception: pass` nuốt im lặng.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        from frappe.utils import add_days, nowdate
        cls.warehouse = _ensure_doc(
            "AC Warehouse", {"warehouse_name": "_Test WH IMM-15 EXP"},
            {"is_active": 1},
        )
        any_uom = frappe.db.get_value("AC UOM", {}, "name") or None
        sp_data = {"unit_cost": 50000, "is_active": 1}
        if any_uom:
            sp_data["stock_uom"] = any_uom
        cls.part = _ensure_doc(
            "AC Spare Part", {"part_name": "_Test Part IMM-15 EXP"}, sp_data
        )
        today = nowdate()
        # 5 batch: 3 trong cửa sổ [today, today+30], 1 ở today+60, 1 quá hạn.
        cls.batch_specs = [
            ("_BAT-IN-0", today, 10),                 # cận dưới = today (IN)
            ("_BAT-IN-15", add_days(today, 15), 10),  # giữa cửa sổ (IN)
            ("_BAT-IN-30", add_days(today, 30), 10),  # cận trên = today+30 (IN)
            ("_BAT-OUT-60", add_days(today, 60), 10),  # ngoài cửa sổ (OUT)
            ("_BAT-EXPIRED", add_days(today, -5), 10),  # đã quá hạn (OUT)
        ]
        cls.batches = []
        for batch_no, exp, qty in cls.batch_specs:
            doc = frappe.get_doc({
                "doctype": "IMM Spare Batch",
                "spare_part": cls.part,
                "batch_no": batch_no,
                "warehouse": cls.warehouse,
                "expiry_date": exp,
                "qty_on_hand": qty,
            }).insert(ignore_permissions=True)
            cls.batches.append(doc.name)
        # 1 batch IN-window nhưng qty_on_hand = 0 → phải bị guard loại.
        empty = frappe.get_doc({
            "doctype": "IMM Spare Batch",
            "spare_part": cls.part,
            "batch_no": "_BAT-IN-10-EMPTY",
            "warehouse": cls.warehouse,
            "expiry_date": add_days(today, 10),
            "qty_on_hand": 0,
        }).insert(ignore_permissions=True)
        cls.batches.append(empty.name)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        with suppress(Exception):
            for name in getattr(cls, "batches", []):
                frappe.delete_doc("IMM Spare Batch", name,
                                  ignore_permissions=True, force=True)
            frappe.db.delete("AC Spare Part Stock", {"spare_part": cls.part})
            frappe.delete_doc("AC Spare Part", cls.part,
                              ignore_permissions=True, force=True)
            frappe.delete_doc("AC Warehouse", cls.warehouse,
                              ignore_permissions=True, force=True)
        frappe.db.commit()

    def _capture(self):
        """Run job with sendmail mocked; return captured kwargs (or None)."""
        from unittest.mock import patch
        import assetcore.utils.helpers as helpers
        captured = {}

        def _fake(*, recipients, subject, message):
            captured.update(recipients=recipients, subject=subject, message=message)

        with patch.object(helpers, "_get_role_emails", return_value=["inv@x.test"]), \
             patch.object(helpers, "_safe_sendmail", side_effect=_fake):
            svc.check_expiring_batches()
        return captured or None

    # ── TC-15-EXP-01: cửa sổ đúng — chỉ 3 batch [today, today+30] ─────────────
    def test_window_predicate_selects_exactly_three(self):
        cap = self._capture()
        self.assertIsNotNone(cap, "phải gửi mail khi có batch trong cửa sổ")
        self.assertIn("3 batch", cap["subject"],
                      f"Subject phải phản ánh đúng 3 batch, got: {cap['subject']}")
        # 3 IN, KHÔNG có batch OUT-60 / EXPIRED / EMPTY trong nội dung.
        self.assertIn("_BAT-IN-0", cap["message"])
        self.assertIn("_BAT-IN-15", cap["message"])
        self.assertIn("_BAT-IN-30", cap["message"])
        self.assertNotIn("_BAT-OUT-60", cap["message"])
        self.assertNotIn("_BAT-EXPIRED", cap["message"])
        self.assertNotIn("_BAT-IN-10-EMPTY", cap["message"])

    # ── TC-15-EXP-02: cận trên 30 ngày KHÔNG bị nuốt ──────────────────────────
    def test_upper_bound_30d_not_swallowed(self):
        cap = self._capture()
        self.assertIn("_BAT-IN-30", cap["message"],
                      "batch tại đúng today+30 phải vào danh sách (cận trên)")

    # ── TC-15-EXP-03: naming-contract batch_no (không raise unknown-column) ────
    def test_uses_batch_no_field_no_raise(self):
        # Nếu còn 'batch_code' → frappe.get_all raise unknown-column ở đây.
        try:
            cap = self._capture()
        except Exception as exc:  # noqa: BLE001
            self.fail(f"check_expiring_batches raised (naming-contract gãy?): {exc}")
        self.assertIn("Batch _BAT-IN-0", cap["message"],
                      "HTML render phải dùng batch_no, không KeyError")

    # ── TC-15-EXP-04: guard qty_on_hand > 0 (batch rỗng không gửi) ────────────
    def test_empty_batch_excluded(self):
        cap = self._capture()
        self.assertNotIn("_BAT-IN-10-EMPTY", cap["message"])
        self.assertIn("3 batch", cap["subject"])

    # ── TC-15-EXP-05: recipients rỗng → no-op (không nổ) ──────────────────────
    def test_no_recipients_no_send(self):
        from unittest.mock import patch
        import assetcore.utils.helpers as helpers
        sent = {"called": False}

        def _fake(**_kw):
            sent["called"] = True

        with patch.object(helpers, "_get_role_emails", return_value=[]), \
             patch.object(helpers, "_safe_sendmail", side_effect=_fake):
            svc.check_expiring_batches()  # KHÔNG raise
        self.assertFalse(sent["called"], "không gửi mail khi recipients rỗng")

    # ── TC-15-EXP-06: AST-guard — 0 dict literal trùng string-key trong repo ──
    def test_no_duplicate_string_dict_keys_in_repo(self):
        import ast
        import os
        app_root = APP_ROOT
        offenders: list[str] = []
        for dirpath, _dirs, files in os.walk(app_root):
            if "__pycache__" in dirpath or "/tests/" in dirpath:
                continue
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                path = os.path.join(dirpath, fn)
                with suppress(Exception):
                    tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)
                    for node in ast.walk(tree):
                        if not isinstance(node, ast.Dict):
                            continue
                        seen: set = set()
                        for k in node.keys:
                            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                                if k.value in seen:
                                    offenders.append(
                                        f"{path}:{node.lineno} dup-key {k.value!r}")
                                seen.add(k.value)
        self.assertEqual(offenders, [],
                         f"dict literal có string-key trùng (silent override): {offenders}")


# ─── CR-WF-15-CC (Trục A): SSoT guard _cycle_allowed_transitions ⇄ workflow ────
#
# _cycle_allowed_transitions là SSoT sinh `allowed_transitions` (get_cycle_count →
# CTA FE CycleCountDetailView server-driven, GATE-8/LL-FE-51). Guard đối soát
# edge-by-edge với imm_15_cycle_count_workflow.json để chống drift CÂM: workflow
# cấp cạnh Reviewed→Counting ("Sửa đếm lại") mà service KHÔNG surface = CTA ẩn câm
# (Inventory Manager/Super Admin không gửi phiếu về đếm lại được dù workflow cho
# phép). Mirror TestIncidentAllowedTransitions (CR-WF-12).


def _load_cycle_workflow_edges() -> set[tuple[str, str]]:
    """WF = {(state, next_state)} gom-vai (dedupe theo cặp, bỏ chiều role) từ
    imm_15_cycle_count_workflow.json.transitions[]."""
    path = frappe.get_app_path(
        "assetcore", "assetcore", "workflow", "imm_15_cycle_count_workflow.json")
    with open(path, encoding="utf-8") as fh:
        wf = json.load(fh)
    return {(t["state"], t["next_state"]) for t in wf["transitions"]}


def _cycle_service_edges() -> set[tuple[str, str]]:
    """SVC = {(status, target)} — mỗi token của _cycle_allowed_transitions ánh xạ đích
    qua _CYCLE_TOKEN_TARGET. Gọi DƯỚI Administrator (full cap) để lấy TẬP TOKEN đầy đủ
    (không bị cap-gate cắt bớt)."""
    s = svc.CycleCountStatus
    edges: set[tuple[str, str]] = set()
    for status in (s.PLANNED, s.COUNTING, s.REVIEWED, s.POSTED):
        for tok in svc._cycle_allowed_transitions(status):
            edges.add((status, svc._CYCLE_TOKEN_TARGET[tok]))
    return edges


class TestCycleCountAllowedTransitions(unittest.TestCase):
    """CR-WF-15-CC INVARIANT (mirror TestIncidentAllowedTransitions): SSoT
    _cycle_allowed_transitions ⇄ imm_15_cycle_count_workflow.json. RED trước fix
    (INV-2 bắt Reviewed→Counting chưa surface), GREEN sau đối soát."""

    def setUp(self):
        frappe.set_user("Administrator")

    def test_svc_subset_workflow(self):
        """INV-1 (SVC ⊆ WF ∪ EXCEPTION): mọi (status, token)→đích PHẢI là cạnh THẬT của
        workflow HOẶC exception có rationale (dual-track collapse) → chặn CTA
        dead/bypass. role∩cap: token gated bởi cap DocPerm, KHÔNG so role-name (dual-
        track: caps qua DocPerm ≠ workflow `allowed` role-name — không assert ở tầng
        cấu trúc này)."""
        svc_e = _cycle_service_edges()
        wf = _load_cycle_workflow_edges()
        exc = set(svc._CYCLE_EXCEPTION_EDGES.keys())
        extra = svc_e - (wf | exc)
        self.assertEqual(
            extra, set(),
            f"_cycle_allowed_transitions có cạnh KHÔNG có trong workflow và KHÔNG khai "
            f"EXCEPTION (dead/bypass): {extra}")

    def test_workflow_subset_svc_union_exception(self):
        """INV-2 (WF ⊆ SVC ∪ EXCEPTION): mọi cạnh workflow HOẶC được surface thành CTA
        (∈ SVC) HOẶC là exception có rationale. RED trước fix: ('Reviewed','Counting')
        ∈ WF \\ (SVC ∪ EXC) — CTA 'Sửa đếm lại' ẩn câm; GREEN sau khi surface
        'Recount'."""
        svc_e = _cycle_service_edges()
        wf = _load_cycle_workflow_edges()
        exc = set(svc._CYCLE_EXCEPTION_EDGES.keys())
        uncovered = wf - (svc_e | exc)
        self.assertEqual(
            uncovered, set(),
            f"Cạnh workflow KHÔNG surface trong _cycle_allowed_transitions và KHÔNG khai "
            f"EXCEPTION (drift câm): {uncovered}")

    def test_exception_edges_have_rationale(self):
        """Mọi EXCEPTION_EDGE phải (a) là cạnh THẬT của ít nhất một máy trạng thái
        (workflow HOẶC service — mã hoá divergence dual-track), (b) có rationale."""
        wf = _load_cycle_workflow_edges()
        svc_e = _cycle_service_edges()
        for edge, rationale in svc._CYCLE_EXCEPTION_EDGES.items():
            self.assertTrue(
                (rationale or "").strip(), f"EXCEPTION_EDGE {edge} thiếu rationale")
            self.assertIn(
                edge, wf | svc_e,
                f"EXCEPTION_EDGE {edge} không phải cạnh của workflow lẫn service")

    def test_recount_surfaced_for_reviewed(self):
        """AC: _cycle_allowed_transitions('Reviewed') == ['Recount','Post'] khi caller
        có cap inventory.submit (Administrator) — Recount đặt TRƯỚC Post."""
        self.assertEqual(
            svc._cycle_allowed_transitions(svc.CycleCountStatus.REVIEWED),
            ["Recount", "Post"])


# ─── CR-WF-15-ALLOC (Trục A): SSoT guard _allocation_allowed_transitions ⇄ workflow ──
#
# _allocation_allowed_transitions là SSoT sinh `allowed_transitions` (get_allocation →
# CTA FE AllocationDetailView server-driven, GATE-8/LL-FE-51). KHÁC cycle-count: trả
# NEXT-STATE strings (codomain ⊆ AllocationStatus), KHÔNG action-verb token → không cần
# TOKEN_TARGET indirection. Guard đối soát edge-by-edge với
# imm_15_allocation_workflow.json để chống drift CÂM + dead/bypass CTA. Mirror
# TestCycleCountAllowedTransitions / TestIncidentAllowedTransitions (CR-WF-12).


def _load_allocation_workflow_edges() -> set[tuple[str, str]]:
    """WF = {(state, next_state)} gom-vai (dedupe theo cặp, bỏ chiều role) từ
    imm_15_allocation_workflow.json.transitions[]."""
    path = frappe.get_app_path(
        "assetcore", "assetcore", "workflow", "imm_15_allocation_workflow.json")
    with open(path, encoding="utf-8") as fh:
        wf = json.load(fh)
    return {(t["state"], t["next_state"]) for t in wf["transitions"]}


def _allocation_service_edges() -> set[tuple[str, str]]:
    """SVC = codomain của _allocation_allowed_transitions dựng thành {(status, next_state)}
    trên TOÀN BỘ 6 AllocationStatus. Map trả next-state strings TRỰC TIẾP (không token)."""
    s = svc.AllocationStatus
    edges: set[tuple[str, str]] = set()
    for status in (s.REQUESTED, s.APPROVED, s.PICKED, s.ISSUED, s.RETURNED, s.CANCELLED):
        for nxt in svc._allocation_allowed_transitions(status):
            edges.add((status, nxt))
    return edges


def _allocation_enum_values() -> set[str]:
    s = svc.AllocationStatus
    return {s.REQUESTED, s.APPROVED, s.PICKED, s.ISSUED, s.RETURNED, s.CANCELLED}


class TestAllocationAllowedTransitions(unittest.TestCase):
    """CR-WF-15-ALLOC INVARIANT: SSoT _allocation_allowed_transitions ⇄
    imm_15_allocation_workflow.json. TC-ALLOC-1/2/3/5/6 + map fidelity."""

    def setUp(self):
        frappe.set_user("Administrator")

    def test_tc_alloc_1_codomain_subset_enum(self):
        """TC-ALLOC-1: mọi next-state trong codomain ∈ AllocationStatus enum (0 typo)."""
        codomain = {nxt for _s, nxt in _allocation_service_edges()}
        self.assertTrue(codomain, "codomain rỗng — map chưa surface next-state nào")
        self.assertLessEqual(
            codomain, _allocation_enum_values(),
            f"codomain chứa state lạ (typo, ∉ AllocationStatus): "
            f"{codomain - _allocation_enum_values()}")

    def test_tc_alloc_2_svc_subset_workflow_union_exception(self):
        """TC-ALLOC-2 (INV-1 SVC ⊆ WF ∪ EXC): mọi (status, next-state) service surface PHẢI
        là cạnh THẬT của workflow HOẶC exception có rationale → 0 dead/bypass CTA
        không-khai. (Approved→Issued = service-collapse Pick chain, khai EXCEPTION.)"""
        svc_e = _allocation_service_edges()
        wf = _load_allocation_workflow_edges()
        exc = set(svc._ALLOCATION_EXCEPTION_EDGES.keys())
        extra = svc_e - (wf | exc)
        self.assertEqual(
            extra, set(),
            f"_allocation_allowed_transitions có cạnh KHÔNG có trong workflow và KHÔNG "
            f"khai EXCEPTION (dead/bypass CTA): {extra}")

    def test_tc_alloc_3_exception_edges_exact(self):
        """TC-ALLOC-3 (INV-2 WF ⊆ SVC ∪ EXC + EXC EXACT): mọi cạnh workflow HOẶC surface
        CTA HOẶC là exception; VÀ keys(EXCEPTION_EDGES) == WF △ SVC (đối xứng) EXACT —
        chống drift câm. Pick chain {Approved→Picked, Picked→Issued} PHẢI ∈ exception."""
        svc_e = _allocation_service_edges()
        wf = _load_allocation_workflow_edges()
        exc = set(svc._ALLOCATION_EXCEPTION_EDGES.keys())
        uncovered = wf - (svc_e | exc)
        self.assertEqual(
            uncovered, set(),
            f"Cạnh workflow không surface CTA và không khai EXCEPTION (drift câm): "
            f"{uncovered}")
        # EXCEPTION_EDGES = ĐÚNG tập divergence đối xứng (không thừa/thiếu exception).
        self.assertEqual(
            exc, wf ^ svc_e,
            f"EXCEPTION_EDGES lệch WF△SVC — thừa: {exc - (wf ^ svc_e)}; "
            f"thiếu: {(wf ^ svc_e) - exc}")
        # Pick chain đích danh (acceptance CR-WF-15-ALLOC).
        s = svc.AllocationStatus
        self.assertIn((s.APPROVED, s.PICKED), svc._ALLOCATION_EXCEPTION_EDGES)
        self.assertIn((s.PICKED, s.ISSUED), svc._ALLOCATION_EXCEPTION_EDGES)

    def test_exception_edges_have_rationale(self):
        """Mọi EXCEPTION_EDGE (a) là cạnh THẬT của workflow HOẶC service (mã hoá divergence
        dual-track), (b) có rationale."""
        wf = _load_allocation_workflow_edges()
        svc_e = _allocation_service_edges()
        for edge, rationale in svc._ALLOCATION_EXCEPTION_EDGES.items():
            self.assertTrue((rationale or "").strip(),
                            f"EXCEPTION_EDGE {edge} thiếu rationale")
            self.assertIn(edge, wf | svc_e,
                          f"EXCEPTION_EDGE {edge} không phải cạnh của workflow lẫn service")

    def test_tc_alloc_5_keys_cover_enum_no_keyerror(self):
        """TC-ALLOC-5: keys(map) == AllocationStatus enum (6 status, mọi status có entry
        tường minh — KHÔNG dựa .get default) → _allocation_allowed_transitions ở BẤT KỲ
        status trả list (0 KeyError/None)."""
        self.assertEqual(
            set(svc._ALLOCATION_TRANSITIONS.keys()), _allocation_enum_values(),
            "keys(_ALLOCATION_TRANSITIONS) phải == AllocationStatus enum (6 status)")
        for status in _allocation_enum_values():
            out = svc._allocation_allowed_transitions(status)
            self.assertIsInstance(out, list, f"status {status} không trả list")

    def test_map_fidelity_per_status(self):
        """Map content pin (chống tautology TC-ALLOC-4): giá trị khớp cạnh
        service-supported (approve/issue/cancel/return) đã verify @source."""
        s = svc.AllocationStatus
        self.assertEqual(svc._allocation_allowed_transitions(s.REQUESTED),
                         [s.APPROVED, s.ISSUED, s.CANCELLED])
        self.assertEqual(svc._allocation_allowed_transitions(s.APPROVED),
                         [s.ISSUED, s.CANCELLED])
        self.assertEqual(svc._allocation_allowed_transitions(s.PICKED),
                         [s.CANCELLED])
        self.assertEqual(svc._allocation_allowed_transitions(s.ISSUED),
                         [s.RETURNED])
        self.assertEqual(svc._allocation_allowed_transitions(s.RETURNED), [])
        self.assertEqual(svc._allocation_allowed_transitions(s.CANCELLED), [])

    def test_tc_alloc_6_workflow_untouched_edge_set(self):
        """TC-ALLOC-6 (regression): imm_15_allocation_workflow.json edge-set (gom-vai)
        GIỮ NGUYÊN 9 cạnh unique — guard chống sửa nhầm JSON (admin-override 22/22 +
        test_workflows IMM-15 min_transitions phụ thuộc JSON untouched)."""
        s = svc.AllocationStatus
        expected = {
            (s.REQUESTED, s.APPROVED), (s.REQUESTED, s.ISSUED), (s.REQUESTED, s.CANCELLED),
            (s.APPROVED, s.PICKED), (s.APPROVED, s.CANCELLED),
            (s.PICKED, s.ISSUED), (s.PICKED, s.CANCELLED),
            (s.ISSUED, s.RETURNED), (s.RETURNED, s.ISSUED),
        }
        self.assertEqual(_load_allocation_workflow_edges(), expected)


class TestGetAllocationServerDrivenCta(TestImm15Base):
    """TC-ALLOC-4: get_allocation emit allowed_transitions ==
    _allocation_allowed_transitions(allocation_status) cho Requested/Approved/Issued
    (≥3 status) + Cancelled → []. Mirror get_cycle_count (BE-DC-15-01)."""

    def test_tc_alloc_4_emit_matches_map(self):
        res = svc.create_allocation(
            work_order_ref="WO-ALLOC-CTA-01",
            items=[{"spare_part": self.part, "qty_requested": 1}],
            asset=self.asset, warehouse=self.warehouse, urgency="Routine",
        )
        name = res["name"]
        # Requested
        d = svc.get_allocation(name)
        self.assertIn("allowed_transitions", d)
        self.assertEqual(d["allowed_transitions"],
                         svc._allocation_allowed_transitions(svc.AllocationStatus.REQUESTED))
        # Approved
        svc.approve_allocation(name)
        d = svc.get_allocation(name)
        self.assertEqual(d["allowed_transitions"],
                         svc._allocation_allowed_transitions(svc.AllocationStatus.APPROVED))
        # Issued
        svc.issue_allocation(name)
        d = svc.get_allocation(name)
        self.assertEqual(d["allowed_transitions"],
                         svc._allocation_allowed_transitions(svc.AllocationStatus.ISSUED))

    def test_tc_alloc_4_cancelled_terminal_empty(self):
        res = svc.create_allocation(
            work_order_ref="WO-ALLOC-CTA-02",
            items=[{"spare_part": self.part, "qty_requested": 1}],
            asset=self.asset, warehouse=self.warehouse, urgency="Routine",
        )
        svc.cancel_allocation(res["name"])
        d = svc.get_allocation(res["name"])
        self.assertEqual(d["allowed_transitions"], [])


def _ensure_role_user(email: str, roles: list[str]) -> str:
    """Idempotent user mang role THẬT (capability resolution). Mirror test_rbac."""
    if not frappe.db.exists("User", email):
        doc = frappe.get_doc({
            "doctype": "User", "email": email,
            "first_name": email.split("@")[0],
            "send_welcome_email": 0, "enabled": 1,
        }).insert(ignore_permissions=True)
    else:
        doc = frappe.get_doc("User", email)
    existing = {r.role for r in doc.get("roles", [])}
    for r in roles:
        if r not in existing:
            doc.append("roles", {"role": r})
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    from assetcore.services.shared import rbac as _rbac
    _rbac.invalidate_capabilities(email)
    return email


class TestCycleCountRecount(TestImm15Base):
    """CR-WF-15-CC — recount_cycle_count: Reviewed → Counting ("Sửa đếm lại").
    TC-15-RECOUNT-01..05. Cap inventory.submit (parity Post)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        # write+submit → có inventory.submit ⇒ recount OK
        cls.mgr = _ensure_role_user(
            "_cc_recount_mgr@assetcore.test", ["Inventory Manager"])
        # write only (submit=0 trên AC Stock Movement) → thiếu inventory.submit
        cls.usr = _ensure_role_user(
            "_cc_recount_usr@assetcore.test", ["Inventory User"])

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for u in (getattr(cls, "mgr", ""), getattr(cls, "usr", "")):
            if u:
                with suppress(Exception):
                    frappe.delete_doc("User", u, force=True, ignore_permissions=True)
        super().tearDownClass()

    def setUp(self):
        frappe.set_user("Administrator")

    def _make_reviewed_cc(self) -> str:
        """create → submit (counted == system → variance 0) → status Reviewed."""
        frappe.set_user("Administrator")
        cc = svc.create_cycle_count(self.warehouse, [{"spare_part": self.part}])
        svc.submit_cycle_count(
            cc["name"], [{"spare_part": self.part, "counted_qty": 20}])
        self.assertEqual(
            frappe.db.get_value("IMM Stock Cycle Count", cc["name"], "status"),
            svc.CycleCountStatus.REVIEWED)
        return cc["name"]

    def _recount_audit_count(self, name: str) -> int:
        return frappe.db.count("IMM Audit Trail", {
            "ref_doctype": "IMM Stock Cycle Count", "ref_name": name,
            "from_status": "Reviewed", "to_status": "Counting"})

    def test_tc_recount_01_reviewed_to_counting_ok(self):
        """TC-15-RECOUNT-01: Inventory Manager Reviewed→Counting OK; return {name,
        workflow_state:'Counting'}; đúng 1 audit from='Reviewed' to='Counting'
        change_summary chứa reason."""
        name = self._make_reviewed_cc()
        reason = ("Nghi đếm nhầm lô Van PEEP máy thở Dräger Evita V500 — "
                  "yêu cầu đếm lại toàn kho")
        before = self._recount_audit_count(name)
        frappe.set_user(self.mgr)
        try:
            out = svc.recount_cycle_count(name, reason)
        finally:
            frappe.set_user("Administrator")
        frappe.db.commit()
        self.assertEqual(out.get("name"), name)
        self.assertEqual(out.get("workflow_state"), svc.CycleCountStatus.COUNTING)
        self.assertEqual(
            frappe.db.get_value("IMM Stock Cycle Count", name, "status"),
            svc.CycleCountStatus.COUNTING)
        self.assertEqual(
            self._recount_audit_count(name), before + 1,
            "recount phải sinh đúng 1 audit Reviewed→Counting")
        row = frappe.get_all(
            "IMM Audit Trail",
            filters={"ref_doctype": "IMM Stock Cycle Count", "ref_name": name,
                     "to_status": "Counting"},
            fields=["change_summary", "from_status"],
            order_by="creation desc", limit=1)[0]
        self.assertEqual(row["from_status"], "Reviewed")
        self.assertIn("Van PEEP", row["change_summary"],
                      "change_summary phải chứa reason đã nhập")

    def test_tc_recount_02_bad_state_non_reviewed(self):
        """TC-15-RECOUNT-02: status≠Reviewed (Planned/Counting/Posted) → BAD_STATE
        (409 bucket); không đổi status."""
        # Planned (create only)
        cc = svc.create_cycle_count(self.warehouse, [{"spare_part": self.part}])
        with self.assertRaises(ServiceError) as ctx:
            svc.recount_cycle_count(cc["name"], "gửi về đếm lại")
        self.assertEqual(ctx.exception.code, ErrorCode.BAD_STATE)
        self.assertEqual(
            frappe.db.get_value("IMM Stock Cycle Count", cc["name"], "status"),
            svc.CycleCountStatus.PLANNED)
        # Counting (recount Reviewed → Counting, rồi recount lại = BAD_STATE)
        name = self._make_reviewed_cc()
        svc.recount_cycle_count(name, "gửi về đếm lại lần 1")
        self.assertEqual(
            frappe.db.get_value("IMM Stock Cycle Count", name, "status"),
            svc.CycleCountStatus.COUNTING)
        with self.assertRaises(ServiceError) as ctx2:
            svc.recount_cycle_count(name, "gửi về đếm lại lần 2")
        self.assertEqual(ctx2.exception.code, ErrorCode.BAD_STATE)
        # Posted (create → submit → post với verifier khác người đếm → Posted)
        posted = self._make_reviewed_cc()
        svc.post_cycle_count(posted, verified_by=self.mgr)
        self.assertEqual(
            frappe.db.get_value("IMM Stock Cycle Count", posted, "status"),
            svc.CycleCountStatus.POSTED)
        with self.assertRaises(ServiceError) as ctx3:
            svc.recount_cycle_count(posted, "gửi về đếm lại")
        self.assertEqual(ctx3.exception.code, ErrorCode.BAD_STATE)

    def test_tc_recount_03_reason_required(self):
        """TC-15-RECOUNT-03: reason rỗng/space-only → IMM15_RECOUNT_REASON_REQUIRED
        (BUSINESS_RULE / 422 bucket); không đổi status."""
        for bad in ("", "   ", "\n\t "):
            name = self._make_reviewed_cc()
            with self.assertRaises(ServiceError) as ctx:
                svc.recount_cycle_count(name, bad)
            self.assertEqual(ctx.exception.code, ErrorCode.BUSINESS_RULE)
            self.assertEqual(ctx.exception.http_status, 422)
            self.assertEqual(
                ctx.exception.message_code, MSG.IMM15_RECOUNT_REASON_REQUIRED)
            self.assertEqual(
                frappe.db.get_value("IMM Stock Cycle Count", name, "status"),
                svc.CycleCountStatus.REVIEWED)

    def test_tc_recount_04_insufficient_cap_forbidden(self):
        """TC-15-RECOUNT-04: user chỉ inventory.write (Inventory User, thiếu
        inventory.submit) → FORBIDDEN; guest → FORBIDDEN (HTTP dispatcher 401 tách
        ở tầng whitelist). Không đổi status."""
        name = self._make_reviewed_cc()
        frappe.set_user(self.usr)
        try:
            with self.assertRaises(ServiceError) as ctx:
                svc.recount_cycle_count(name, "gửi về đếm lại")
            self.assertEqual(ctx.exception.code, ErrorCode.FORBIDDEN)
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(
            frappe.db.get_value("IMM Stock Cycle Count", name, "status"),
            svc.CycleCountStatus.REVIEWED)
        frappe.set_user("Guest")
        try:
            with self.assertRaises(ServiceError) as ctx2:
                svc.recount_cycle_count(name, "gửi về đếm lại")
            self.assertEqual(ctx2.exception.code, ErrorCode.FORBIDDEN)
        finally:
            frappe.set_user("Administrator")

    def test_tc_recount_05_get_cycle_count_server_driven(self):
        """TC-15-RECOUNT-05: get_cycle_count(reviewed).allowed_transitions chứa
        'Recount' khi caller có inventory.submit (Inventory Manager), KHÔNG chứa khi
        chỉ inventory.write (Inventory User) — server-driven contract."""
        name = self._make_reviewed_cc()
        frappe.set_user(self.mgr)
        try:
            data_mgr = svc.get_cycle_count(name)
        finally:
            frappe.set_user("Administrator")
        self.assertIn("Recount", data_mgr["allowed_transitions"])
        self.assertEqual(data_mgr["allowed_transitions"], ["Recount", "Post"])
        frappe.set_user(self.usr)
        try:
            data_usr = svc.get_cycle_count(name)
        finally:
            frappe.set_user("Administrator")
        self.assertNotIn("Recount", data_usr["allowed_transitions"])


# ─────────────────────────────────────────────────────────────────────────────
# CR-WF-15-AUDIT · ADR-IMM-15-09 — Bịt silent-audit-loss (07 §III.4b)
#   6 slug domain IMM-15 ∉ Select IMM Audit Trail.event_type ⇒ log_audit_event()
#   .insert() raise ValidationError, bị try/except NUỐT ⇒ 0 dòng audit. Fix =
#   REGISTER 6 slug + SSoT constant + bare pass → log_error.
# ─────────────────────────────────────────────────────────────────────────────

def _audit_select_options() -> set[str]:
    opts = frappe.get_meta("IMM Audit Trail").get_field("event_type").options or ""
    return {o.strip() for o in opts.split("\n") if o.strip()}


class TestImm15AuditEventTypeParity(unittest.TestCase):
    """(A) INVARIANT — chống drift emit-nhưng-quên-đăng-ký. RED trước khi thêm 6
    option vào imm_audit_trail.json (+ reload/migrate JSON→DB), GREEN sau."""

    def test_imm15_slugs_subset_of_select(self):
        """IMM15_AUDIT_EVENT_TYPES ⊆ Select options — RED: 6 slug missing."""
        missing = svc.IMM15_AUDIT_EVENT_TYPES - _audit_select_options()
        self.assertEqual(
            missing, set(),
            f"IMM-15 emit slug ∉ Select (silent-audit-loss): {sorted(missing)}")

    def test_ssot_constant_matches_emit_sites(self):
        """derived slug từ _ALLOCATION_AUDIT_ACTIONS + cycle_count_posted == SSoT
        (bắt lệch nếu sửa constant mà quên emit-site / action-set — GREEN luôn)."""
        derived = ({f"allocation_{a.lower()}" for a in svc._ALLOCATION_AUDIT_ACTIONS}
                   | {"cycle_count_posted"})
        self.assertEqual(derived, set(svc.IMM15_AUDIT_EVENT_TYPES))


class TestImm15AuditRows(TestImm15Base):
    """(B) audit-row per-transition + (C) bare-pass regression guard.

    Mỗi transition ghi ĐÚNG 1 dòng đúng slug + ref_doctype/ref_name/actor (đếm delta
    theo slug + ref_name — anti-false-green: KHÔNG chỉ '≥1 dòng bất kỳ'). BEFORE fix:
    0 dòng (slug ∉ Select → ValidationError nuốt câm); AFTER: 1 dòng.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        # Inventory Manager → có inventory.submit ⇒ verifier hợp lệ cho post
        # (KHÁC counted_by=Administrator → thoả VR-15-11 segregation).
        cls.mgr = _ensure_role_user(
            "_imm15_aud_mgr@assetcore.test", ["Inventory Manager"])

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        if getattr(cls, "mgr", ""):
            with suppress(Exception):
                frappe.delete_doc("User", cls.mgr, force=True,
                                  ignore_permissions=True)
        super().tearDownClass()

    def setUp(self):
        frappe.set_user("Administrator")

    # ── helpers ───────────────────────────────────────────────────────────────
    # Đếm DELTA theo (ref_doctype, event_type) quanh 1 transition (07 §III.4b:
    # "delta = 1"). Global-delta thay vì absolute-per-ref: SAL/CYC naming-counter
    # trên dev-DB tái dùng ref_name (tabSeries current < ref lịch sử) ⇒ dòng audit
    # LEAKED của run trước pollute absolute==1. Delta-quanh-op miễn nhiễm với dòng cũ
    # + KHÔNG cần purge phá hoại (an toàn phiên concurrent). Newest row = dòng vừa ghi.
    def _cnt(self, doctype: str, event_type: str) -> int:
        return frappe.db.count("IMM Audit Trail", {
            "ref_doctype": doctype, "event_type": event_type})

    def _assert_one_new(self, doctype: str, event_type: str, expected_ref: str, fn):
        before = self._cnt(doctype, event_type)
        result = fn()
        self.assertEqual(
            self._cnt(doctype, event_type) - before, 1,
            f"transition phải ghi ĐÚNG 1 dòng {event_type} (delta)")
        newest = frappe.get_all(
            "IMM Audit Trail",
            filters={"ref_doctype": doctype, "event_type": event_type},
            fields=["ref_name"], order_by="creation desc", limit=1)[0]
        self.assertEqual(newest["ref_name"], expected_ref,
                         f"dòng {event_type} phải trỏ đúng {expected_ref}")
        return result

    def _reset_bin(self, on_hand: float = 20) -> None:
        # Giải phóng các phiếu còn HOLDING trên bin dùng-chung + đặt lại tồn.
        for n in frappe.get_all(
            "IMM Spare Allocation",
            filters={"warehouse_from": self.warehouse,
                     "allocation_status": ("in", ["Requested", "Approved", "Picked"])},
            pluck="name",
        ):
            with suppress(Exception):
                svc.cancel_allocation(n)
        frappe.db.set_value(
            "AC Spare Part Stock",
            {"spare_part": self.part, "warehouse": self.warehouse},
            {"qty_on_hand": on_hand, "reserved_qty": 0, "available_qty": on_hand})
        frappe.db.commit()

    def _new_allocation(self, wo="WO-AUD", qty=1) -> str:
        res = svc.create_allocation(
            work_order_ref=wo,
            items=[{"spare_part": self.part, "qty_requested": qty}],
            asset=self.asset, warehouse=self.warehouse, urgency="Routine")
        return res["name"]

    def _make_reviewed_cc(self) -> str:
        frappe.set_user("Administrator")
        cc = svc.create_cycle_count(self.warehouse, [{"spare_part": self.part}])
        svc.submit_cycle_count(
            cc["name"], [{"spare_part": self.part, "counted_qty": 20}])
        return cc["name"]

    # ── (B) per-transition audit-row ────────────────────────────────────────────
    def test_tc_aud_01_post_cycle_count(self):
        """post_cycle_count → 1 dòng cycle_count_posted, ref=phiếu, actor=verified_by,
        from=Reviewed to=Posted (BEFORE 0 → AFTER 1)."""
        cyc = svc.CycleCountRepo.DOCTYPE
        name = self._make_reviewed_cc()
        self._assert_one_new(
            cyc, "cycle_count_posted", name,
            lambda: svc.post_cycle_count(name, verified_by=self.mgr))
        row = frappe.get_all(
            "IMM Audit Trail",
            filters={"ref_doctype": cyc, "ref_name": name,
                     "event_type": "cycle_count_posted"},
            fields=["actor", "from_status", "to_status"],
            order_by="creation desc", limit=1)[0]
        self.assertEqual(row["actor"], self.mgr)
        self.assertEqual(row["from_status"], svc.CycleCountStatus.REVIEWED)
        self.assertEqual(row["to_status"], svc.CycleCountStatus.POSTED)

    def test_tc_aud_02_create_allocation(self):
        alloc = svc.AllocationRepo.DOCTYPE
        before = self._cnt(alloc, "allocation_created")
        name = self._new_allocation("WO-AUD-02")
        self.assertEqual(self._cnt(alloc, "allocation_created") - before, 1,
                         "create_allocation phải ghi ĐÚNG 1 dòng allocation_created")
        newest = frappe.get_all(
            "IMM Audit Trail",
            filters={"ref_doctype": alloc, "event_type": "allocation_created"},
            fields=["ref_name"], order_by="creation desc", limit=1)[0]
        self.assertEqual(newest["ref_name"], name)

    def test_tc_aud_03_approve_allocation(self):
        alloc = svc.AllocationRepo.DOCTYPE
        name = self._new_allocation("WO-AUD-03")
        self._assert_one_new(alloc, "allocation_approved", name,
                             lambda: svc.approve_allocation(name))

    def test_tc_aud_04_issue_allocation(self):
        alloc = svc.AllocationRepo.DOCTYPE
        self._reset_bin(20)
        name = self._new_allocation("WO-AUD-04")
        svc.approve_allocation(name)
        self._assert_one_new(alloc, "allocation_issued", name,
                             lambda: svc.issue_allocation(name))

    def test_tc_aud_05_return_items(self):
        alloc = svc.AllocationRepo.DOCTYPE
        self._reset_bin(20)
        name = self._new_allocation("WO-AUD-05")
        svc.approve_allocation(name)
        svc.issue_allocation(name)
        self._assert_one_new(
            alloc, "allocation_returned", name,
            lambda: svc.return_items(
                name, [{"spare_part": self.part, "qty_returned": 1,
                        "return_condition": "Good"}]))

    def test_tc_aud_06_cancel_allocation(self):
        alloc = svc.AllocationRepo.DOCTYPE
        name = self._new_allocation("WO-AUD-06")
        self._assert_one_new(alloc, "allocation_cancelled", name,
                             lambda: svc.cancel_allocation(name))

    def test_tc_aud_07_lifecycle_four_distinct_rows(self):
        """1 vòng đời create→approve→issue→return → 4 dòng PHÂN BIỆT được
        (granularity provenance — bác Alternative 'State Change' collapse)."""
        alloc = svc.AllocationRepo.DOCTYPE
        self._reset_bin(20)
        before = self._cnt(alloc, "allocation_created")
        name = self._new_allocation("WO-AUD-07")
        self.assertEqual(self._cnt(alloc, "allocation_created") - before, 1,
                         "vòng đời phải ghi đúng 1 dòng allocation_created")
        self._assert_one_new(alloc, "allocation_approved", name,
                             lambda: svc.approve_allocation(name))
        self._assert_one_new(alloc, "allocation_issued", name,
                             lambda: svc.issue_allocation(name))
        self._assert_one_new(
            alloc, "allocation_returned", name,
            lambda: svc.return_items(
                name, [{"spare_part": self.part, "qty_returned": 1,
                        "return_condition": "Good"}]))

    # ── (C) bare-pass regression guard ──────────────────────────────────────────
    def test_tc_aud_08_bare_pass_regression_allocation(self):
        """monkeypatch svc.log_audit_event → raise; cancel_allocation:
        (a) allocation VẪN Cancelled (non-blocking best-effort);
        (b) frappe.log_error ĐƯỢC gọi (KHÔNG bare pass @_write_allocation_audit)."""
        name = self._new_allocation("WO-AUD-08")
        calls: list = []
        orig_lae = svc.log_audit_event
        orig_le = frappe.log_error

        def _boom(*a, **k):
            raise RuntimeError("audit backend down")

        def _spy(*a, **k):
            calls.append((a, k))

        svc.log_audit_event = _boom
        frappe.log_error = _spy
        try:
            out = svc.cancel_allocation(name)
        finally:
            svc.log_audit_event = orig_lae
            frappe.log_error = orig_le
        self.assertEqual(out["workflow_state"], svc.AllocationStatus.CANCELLED)
        self.assertEqual(
            frappe.db.get_value("IMM Spare Allocation", name, "allocation_status"),
            svc.AllocationStatus.CANCELLED,
            "cancel phải thành công dù audit fail (non-blocking)")
        self.assertTrue(
            calls, "audit-write fail phải log_error — KHÔNG bare pass (silent-loss)")

    def test_tc_aud_09_regression_post_cycle_count(self):
        """(đối xứng) monkeypatch raise; post_cycle_count vẫn Posted + log_error gọi
        (regression-lock cho nhánh except @post @718)."""
        name = self._make_reviewed_cc()
        calls: list = []
        orig_lae = svc.log_audit_event
        orig_le = frappe.log_error

        def _boom(*a, **k):
            raise RuntimeError("audit backend down")

        svc.log_audit_event = _boom
        frappe.log_error = lambda *a, **k: calls.append(1)
        try:
            out = svc.post_cycle_count(name, verified_by=self.mgr)
        finally:
            svc.log_audit_event = orig_lae
            frappe.log_error = orig_le
        self.assertEqual(out["workflow_state"], svc.CycleCountStatus.POSTED)
        self.assertEqual(
            frappe.db.get_value("IMM Stock Cycle Count", name, "status"),
            svc.CycleCountStatus.POSTED,
            "post phải thành công dù audit fail (non-blocking)")
        self.assertTrue(calls, "post audit fail phải log_error (regression-lock)")


if __name__ == "__main__":
    unittest.main()
