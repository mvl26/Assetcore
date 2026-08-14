# Copyright (c) 2026, AssetCore Team
"""Money/value overflow guard — large VND values (> 2.1 tỷ) MUST NOT overflow.

ROOT CONCERN (user report): "giá trị tiền của asset lẫn khấu hao để int thì
bị tràn khi giá trị lớn hơn 2 tỷ". Frappe maps fieldtypes to MariaDB columns:

    Int       → int(11)       signed 32-bit   → max  2,147,483,647 (~2.1 tỷ)  ❌
    Currency  → decimal(21,9)  12 int digits   → max ~999,999,999,999 (~1 nghìn tỷ) ✅
    Float     → decimal(21,9)  12 int digits   → max ~999,999,999,999 (~1 nghìn tỷ) ✅
    Long Int  → bigint(20)     signed 64-bit   → max ~9.2e18

Money is therefore SAFE only if its fieldtype is a DECIMAL type (Currency/Float),
NEVER an integer type (Int/Long Int — Long Int has no decimal places so it can't
hold đồng-precision money either). These tests pin that contract two ways:

  1. SCHEMA GUARD (TestMoneyFieldsAreDecimalNotInt) — every money-semantic field
     across all DocTypes is Currency/Float, never Int. Reading the JSON directly
     (no DB) keeps it fast and catches a regression the instant someone flips a
     money field to Int.
        RED-EXPERIMENT (verified, KHÔNG commit): set `gross_purchase_amount`
        fieldtype to "Int" in ac_asset.json → this test FAILs; revert → GREEN.

  2. FUNCTIONAL + DB ROUND-TRIP (TestLargeValueDepreciation*) — a 5-tỷ asset
     (> int32 ceiling) flows through preview_schedule / generate_schedule /
     run_due_depreciation with accumulated reaching ~4.5 tỷ and book floored at
     residual — values that an int(11) column would reject on insert.

Run:
  bench --site miyano run-tests --app assetcore \
      --module assetcore.tests.test_depreciation_large_value
"""
from __future__ import annotations

import json
import os
import unittest

import frappe
from frappe.utils import flt

from assetcore.services import depreciation as depr_svc
from assetcore.tests._asset_cleanup import purge_asset
from assetcore.tests._helpers.paths import DOCTYPE_DIR

_DT_ASSET = "AC Asset"

# int(11) ceiling — any money value above this would overflow an Int column.
_INT32_MAX = 2_147_483_647  # ~2.147 tỷ

# Decimal fieldtypes that safely hold money (decimal(21,9), no 32-bit overflow).
_DECIMAL_MONEY_TYPES = {"Currency", "Float"}

# Widened decimal width for money columns (§2.4.1): Currency is a CONFIGURABLE
# decimal type → `length` sets the column width. decimal(28,9) → 19 integer
# digits → ceiling ~10^19 VND ("long long"-scale), keeps 9 decimals (no rounding
# behaviour change). Activated by `bench migrate` (alters decimal(21,9)→(28,9)).
_MONEY_DECIMAL_WIDTH = 28

# ── Explicit money-field inventory (doctype_folder → fieldnames) ──────────────
# Derived from a full sweep of assetcore/assetcore/doctype/**.json. These are
# the fields that hold a sum of money (đồng). They MUST be a decimal type so a
# value > 2.1 tỷ does not overflow. Counts (months/days/years/qty/scores/lft/rgt)
# are intentionally EXCLUDED — those are correct as Int (always < 2.1 tỷ).
_MONEY_FIELDS: dict[str, tuple[str, ...]] = {
    "ac_asset": (
        "gross_purchase_amount", "residual_value", "accumulated_depreciation",
        "current_book_value", "insured_value",
    ),
    "ac_asset_depreciation_schedule": (
        "depreciation_amount", "accumulated_amount", "remaining_value",
    ),
    "ac_purchase": ("total_value",),
    "ac_purchase_device_item": ("unit_cost",),
    "ac_purchase_item": ("unit_cost", "total_cost"),
    "ac_spare_part": ("unit_cost",),
    "ac_stock_movement": ("total_value",),
    "ac_stock_movement_item": ("unit_cost", "total_cost"),
    "ac_supplier": ("contract_value",),
    "asset_commissioning": ("purchase_price",),
    "asset_qa_non_conformance": ("penalty_amount",),
    "asset_repair": ("total_parts_cost",),
    "benchmark_candidate": ("price_estimate",),
    "budget_estimate_line": ("unit_cost", "amount"),
    "imm_cycle_count_item": ("variance_value",),
    "imm_device_spare_part": ("estimated_cost",),
    "imm_procurement_decision": ("awarded_price",),
    "imm_procurement_plan": ("budget_envelope",),
    "imm_spare_allocation": ("total_value",),
    "imm_spare_allocation_item": ("unit_value", "line_value"),
    "imm_stock_cycle_count": ("variance_value",),
    "imm_stock_cycle_count_item": ("variance_value",),
    "infra_compatibility_item": ("upgrade_cost_estimate",),
    "procurement_plan_line": ("allocated_budget",),
    "service_contract": ("contract_value",),
    "spare_parts_used": ("unit_cost", "total_cost"),
    "vendor_quotation_line": ("price",),
}

_DOCTYPE_DIR = os.path.join(
    DOCTYPE_DIR,
)


def _load_doctype_fields(folder: str) -> dict[str, str]:
    """Return {fieldname: fieldtype} for a DocType, read straight from JSON."""
    path = os.path.join(_DOCTYPE_DIR, folder, f"{folder}.json")
    with open(path, encoding="utf-8") as fh:
        meta = json.load(fh)
    return {
        f.get("fieldname"): f.get("fieldtype")
        for f in meta.get("fields", [])
        if f.get("fieldname")
    }


class TestMoneyFieldsAreDecimalNotInt(unittest.TestCase):
    """SCHEMA GUARD: every money field is a decimal type, NEVER Int/Long Int.

    No DB — reads DocType JSON. This is the single contract that prevents the
    "int tràn ở 2 tỷ" regression: money columns must be decimal(21,9), so a value
    up to ~1 nghìn tỷ VND stores without overflow.
    """

    def test_every_money_field_is_currency_or_float(self):
        offenders: list[str] = []
        missing: list[str] = []
        for folder, fields in _MONEY_FIELDS.items():
            try:
                ftypes = _load_doctype_fields(folder)
            except FileNotFoundError:
                missing.append(folder)
                continue
            for fn in fields:
                ftype = ftypes.get(fn)
                if ftype is None:
                    missing.append(f"{folder}.{fn}")
                elif ftype not in _DECIMAL_MONEY_TYPES:
                    offenders.append(f"{folder}.{fn} = {ftype}")
        self.assertEqual(
            offenders, [],
            "money field(s) declared with a non-decimal type — an Int column "
            f"overflows at {_INT32_MAX:,} (~2.1 tỷ). Use Currency: {offenders}",
        )
        self.assertEqual(
            missing, [],
            f"money-field inventory drifted from schema (renamed/removed): {missing}",
        )


class TestMoneyColumnsWidenedToLongLong(unittest.TestCase):
    """§2.4.1: money columns declare `length: 28` → decimal(28,9), ceiling ~10^19 VND.

    No DB. Two assertions:
      1. JSON GUARD — every money field declares length >= 28 so the widening
         can't silently regress to the decimal(21,9) default (~1 nghìn tỷ trần).
      2. MAPPING — Frappe's own get_definition maps Currency+length=28 to the
         exact column "decimal(28,9)" (grounds the ceiling claim in real Frappe
         code, no migrate needed to verify the schema the next migrate will apply).
    """

    def test_every_money_field_declares_widened_length(self):
        offenders: list[str] = []
        for folder, fields in _MONEY_FIELDS.items():
            try:
                path = os.path.join(_DOCTYPE_DIR, folder, f"{folder}.json")
                with open(path, encoding="utf-8") as fh:
                    meta = json.load(fh)
            except FileNotFoundError:
                offenders.append(f"{folder} (missing)")
                continue
            by_name = {f.get("fieldname"): f for f in meta.get("fields", [])}
            for fn in fields:
                fld = by_name.get(fn) or {}
                width = int(fld.get("length") or 0)
                if width < _MONEY_DECIMAL_WIDTH:
                    offenders.append(f"{folder}.{fn} length={width or 'unset'}")
        self.assertEqual(
            offenders, [],
            f"money field(s) not widened to length>={_MONEY_DECIMAL_WIDTH} "
            f"(decimal({_MONEY_DECIMAL_WIDTH},9)); default decimal(21,9) caps at "
            f"~1 nghìn tỷ: {offenders}",
        )

    def test_frappe_maps_currency_length28_to_decimal_28_9(self):
        from frappe.database.schema import get_definition
        self.assertEqual(
            get_definition("Currency", precision=9, length=_MONEY_DECIMAL_WIDTH),
            f"decimal({_MONEY_DECIMAL_WIDTH},9)",
        )
        # The unwidened default stays decimal(21,9) — confirms 28 is the lever.
        self.assertEqual(get_definition("Currency"), "decimal(21,9)")


class TestLargeValueSchedulePure(unittest.TestCase):
    """FUNCTIONAL (pure, no DB): preview_schedule handles a 5-tỷ asset exactly.

    depreciable_base = 4.5 tỷ > int32 max → proves the planner math never caps
    a money value at 2^31.
    """

    _GROSS = 5_000_000_000.0      # 5 tỷ  (> int32 max)
    _RESIDUAL = 500_000_000.0     # 500 tr
    _BASE = _GROSS - _RESIDUAL    # 4.5 tỷ
    _MONTHS = 60

    def test_straight_line_sums_to_base_above_int32(self):
        amounts = depr_svc._straight_line_amounts(self._BASE, self._MONTHS)
        self.assertEqual(len(amounts), self._MONTHS)
        self.assertAlmostEqual(sum(amounts), self._BASE, delta=1.0)
        # The cumulative total exceeds the int32 ceiling → no integer cap.
        self.assertGreater(sum(amounts), _INT32_MAX)

    def test_preview_schedule_large_value_intact(self):
        rows = depr_svc.preview_schedule(
            gross=self._GROSS, residual=self._RESIDUAL, method="Straight Line",
            total_months=self._MONTHS, frequency="Monthly",
            start_date="2024-01-01",
        )
        self.assertEqual(len(rows), self._MONTHS)
        # Accumulated reaches the full depreciable base (4.5 tỷ > 2.1 tỷ).
        last = rows[-1]
        self.assertAlmostEqual(last["accumulated_amount"], self._BASE, delta=1.0)
        self.assertGreater(last["accumulated_amount"], _INT32_MAX)
        # Book value floors at residual, not 0, not a wrapped negative.
        self.assertAlmostEqual(last["remaining_value"], self._RESIDUAL, delta=1.0)


class TestLargeValueAssetRoundTrip(unittest.TestCase):
    """DB ROUND-TRIP: a 5-tỷ AC Asset stores & depreciates without overflow.

    Insert > int32 max into gross_purchase_amount, read back EXACT, then run the
    full executor. An int(11) column would reject the insert ("Out of range"),
    so a green run here proves the column is decimal(21,9).
    """

    _GROSS = 5_000_000_000.0
    _RESIDUAL = 500_000_000.0
    _BASE = _GROSS - _RESIDUAL
    _FAR_FUTURE = "2099-12-31"

    def setUp(self) -> None:
        self._assets: list[str] = []
        if not frappe.db.exists("AC UOM", "Cái"):
            frappe.get_doc({"doctype": "AC UOM", "uom_name": "Cái"}).insert(
                ignore_permissions=True)

    def tearDown(self) -> None:
        for a in self._assets:
            try:
                purge_asset(a)
            except Exception:
                pass
        frappe.db.commit()

    def _make(self) -> str:
        doc = frappe.get_doc({
            "doctype": _DT_ASSET,
            "asset_name": "_Test Depr LargeValue 5ty",
            "gross_purchase_amount": self._GROSS,
            "residual_value": self._RESIDUAL,
            "depreciation_method": "Straight Line",
            "total_depreciation_months": 60,
            "depreciation_frequency": "Monthly",
            "depreciation_start_date": "2024-01-01",
            "in_service_date": "2024-01-01",
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
        self._assets.append(doc.name)
        return doc.name

    def test_gross_stored_exact_above_int32(self):
        asset = self._make()
        stored = flt(frappe.db.get_value(
            _DT_ASSET, asset, "gross_purchase_amount"))
        self.assertGreater(stored, _INT32_MAX, "gross truncated below int32 max")
        self.assertAlmostEqual(stored, self._GROSS, delta=0.01)

    def test_full_pipeline_5ty_floors_at_residual(self):
        asset = self._make()
        depr_svc.generate_schedule(asset, force=True)
        depr_svc.run_due_depreciation(as_of=self._FAR_FUTURE, asset=asset)
        acc = flt(frappe.db.get_value(
            _DT_ASSET, asset, "accumulated_depreciation"))
        book = flt(frappe.db.get_value(
            _DT_ASSET, asset, "current_book_value"))
        # accumulated reaches depreciable base (4.5 tỷ > 2.1 tỷ) — no int cap.
        self.assertAlmostEqual(acc, self._BASE, delta=1.0)
        self.assertGreater(acc, _INT32_MAX)
        # book floors at residual (500 tr), never below / never wrapped.
        self.assertAlmostEqual(book, self._RESIDUAL, delta=1.0)
