# Copyright (c) 2026, AssetCore Team
"""L-03 (audit BaoCao_RaSoat 17/06) — "Sinh lịch khấu hao" KHÔNG treo (no hang).

VERIFY the generator is bounded and deterministic (the audit reported a UI "hang"
on schedule generation). The hardening already in `generate_schedule`:
  - bounded loop: periods = total_months // months_per_period, capped at
    _MAX_SCHEDULE_PERIODS (240 = 20y monthly) → >cap raises 422, never loops.
  - one append per period → row count == periods exactly.
These tests PIN that contract (regression guard): a 60-period generation finishes
(the test completing IS the no-hang proof) and writes exactly 60 child rows; the
240 cap is the hard ceiling (240 OK, 241 raises, no runaway).

Run:
  bench --site miyano run-tests --app assetcore \
      --module assetcore.tests.test_depreciation_l03_no_hang
"""
from __future__ import annotations

import unittest

import frappe
from frappe.utils import flt

from assetcore.services import depreciation as depr_svc
from assetcore.tests._asset_cleanup import purge_asset

_DT_ASSET = "AC Asset"
_DT_SCHED = "AC Asset Depreciation Schedule"
# Mirror module constant (RC-01): 240 = 20 năm * 12 tháng.
_MAX = depr_svc._MAX_SCHEDULE_PERIODS


def _ensure_uom() -> None:
    if not frappe.db.exists("AC UOM", "Cái"):
        frappe.get_doc({"doctype": "AC UOM", "uom_name": "Cái"}).insert(
            ignore_permissions=True)


def _make_asset(*, suffix: str, months: int, frequency: str = "Monthly",
                gross: float = 120_000_000.0, residual: float = 0.0) -> str:
    _ensure_uom()
    doc = frappe.get_doc({
        "doctype": _DT_ASSET,
        "asset_name": f"_Test L03 {suffix}",
        "gross_purchase_amount": gross,
        "residual_value": residual,
        "depreciation_method": "Straight Line",
        "total_depreciation_months": months,
        "depreciation_frequency": frequency,
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
    return doc.name


def _row_count(asset: str) -> int:
    return frappe.db.count(_DT_SCHED, {"parent": asset, "parenttype": _DT_ASSET})


class TestL03ScheduleNoHang(unittest.TestCase):
    """Bounded, deterministic schedule generation (no infinite loop / hang)."""

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
        return name

    def test_60_period_monthly_completes_with_60_rows(self):
        """[L-03] 60 tháng / Monthly → đúng 60 kỳ, hoàn tất (no hang), lũy kế = base."""
        asset = self._new(suffix="60M", months=60, frequency="Monthly")
        res = depr_svc.generate_schedule(asset, force=True)
        self.assertFalse(res.get("skipped"), f"unexpected skip: {res}")
        self.assertEqual(res["periods"], 60)
        self.assertEqual(_row_count(asset), 60, "phải sinh ĐÚNG 60 dòng schedule")
        # Lũy kế kỳ cuối == depreciable_base (120tr, residual=0) — không thiếu/thừa kỳ.
        last = frappe.db.get_value(
            _DT_SCHED, {"parent": asset}, "accumulated_amount",
            order_by="period_number desc")
        self.assertAlmostEqual(flt(last), 120_000_000.0, delta=1.0)

    def test_quarterly_60_months_yields_20_periods(self):
        """[L-03] frequency chia số kỳ: 60 tháng / Quarterly → 20 kỳ (bounded)."""
        asset = self._new(suffix="60Q", months=60, frequency="Quarterly")
        res = depr_svc.generate_schedule(asset, force=True)
        self.assertEqual(res["periods"], 20)
        self.assertEqual(_row_count(asset), 20)

    def test_at_cap_240_periods_completes(self):
        """[L-03] đúng ngưỡng trần 240 kỳ → vẫn hoàn tất, sinh 240 dòng (no hang)."""
        asset = self._new(suffix="CAP", months=_MAX, frequency="Monthly")
        res = depr_svc.generate_schedule(asset, force=True)
        self.assertEqual(res["periods"], _MAX)
        self.assertEqual(_row_count(asset), _MAX)

    def test_over_cap_raises_not_hang(self):
        """[L-03] vượt trần (241 kỳ) → raise 422 NGAY, KHÔNG loop vô hạn / treo."""
        asset = self._new(suffix="OVER", months=_MAX + 1, frequency="Monthly")
        with self.assertRaises(frappe.ValidationError):
            depr_svc.generate_schedule(asset, force=True)
        # Không ghi dòng nào khi vượt trần (raise trước vòng append).
        self.assertEqual(_row_count(asset), 0)

    def test_regen_force_idempotent_row_count(self):
        """[L-03] regen force=True 2 lần → vẫn đúng 60 dòng (clear trước khi append,
        không nhân đôi)."""
        asset = self._new(suffix="REGEN", months=60, frequency="Monthly")
        depr_svc.generate_schedule(asset, force=True)
        depr_svc.generate_schedule(asset, force=True)
        self.assertEqual(_row_count(asset), 60, "regen không được nhân đôi dòng")
