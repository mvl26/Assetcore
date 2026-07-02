# Copyright (c) 2026, AssetCore Team
"""IMM-00 — get_depreciation_by_category (quản lý khấu hao tập trung theo Danh mục).

TDD (CLAUDE.md §17) cho slice T1 của feature "màn quản lý khấu hao theo danh mục".

Nội dung kiểm:
  A. PER-CATEGORY CORRECTNESS: gom đúng số TS / nguyên giá / độ phủ cấu hình theo
     từng Danh mục tài sản.
  B. PARITY (INVARIANT SoT): endpoint mới dùng CHUNG filter (docstatus!=2 +
     reserved_prefix_filter) + CHUNG predicate (effective_book_value /
     is_fully_depreciated / configured) với get_depreciation_stats ⇒
       Σ cat.asset_count      == totals.total_assets == stats.total_assets
       Σ cat.fully_depreciated                        == stats.fully_depreciated
       totals.total_gross                             == stats.total_gross
     KHÔNG được drift (2 nguồn số quản trị khác nhau = bug niềm tin).

Run:
  bench --site miyano run-tests --app assetcore \
      --module assetcore.tests.test_depreciation_by_category
"""
from __future__ import annotations

import unittest

import frappe

from assetcore.tests._asset_cleanup import purge_asset

_DT_ASSET = "AC Asset"
_DT_CATEGORY = "AC Asset Category"


def _ensure_uom() -> None:
    if not frappe.db.exists("AC UOM", "Cái"):
        frappe.get_doc({"doctype": "AC UOM", "uom_name": "Cái"}).insert(
            ignore_permissions=True
        )


class TestDepreciationByCategory(unittest.TestCase):
    def setUp(self) -> None:
        _ensure_uom()
        self._assets: list[str] = []
        self._cats: list[str] = []

    def tearDown(self) -> None:
        for name in self._assets:
            purge_asset(name)
        for cat in self._cats:
            try:
                frappe.delete_doc(
                    _DT_CATEGORY, cat, force=True, ignore_permissions=True
                )
            except Exception:
                pass
        frappe.db.commit()

    # ── fixtures ──────────────────────────────────────────────────────────────
    def _make_category(self, months: int = 12, method: str = "Straight Line") -> str:
        code = f"TDC-{frappe.generate_hash(length=8)}"
        doc = frappe.get_doc({
            "doctype": _DT_CATEGORY,
            "category_name": f"_Test DeprCat {code}",
            "category_code": code,
            "default_depreciation_method": method,
            "total_depreciation_months": months,
            "depreciation_frequency": "Monthly",
            "default_residual_value_pct": 0,
        }).insert(ignore_permissions=True)
        self._cats.append(doc.name)
        return doc.name

    def _make_asset(
        self, *, category: str, gross: float, months: int = 12,
        method: str = "Straight Line",
    ) -> str:
        """Insert AC Asset (đã cấu hình khấu hao) thuộc `category`, bypass workflow.

        LƯU Ý: asset_name KHÔNG được bắt đầu bằng '_' — reserved_prefix_filter (SSoT
        data-hygiene) loại mọi asset có asset_name LIKE '_%' khỏi aggregate ⇒ dùng
        prefix 'ZZ' để asset test ĐƯỢC gom vào by-category (teardown vẫn purge theo
        docname). Category (không bị reserved-filter) vẫn dùng nhãn '_Test' được.
        """
        doc = frappe.get_doc({
            "doctype": _DT_ASSET,
            "asset_name": f"ZZ Test DeprCat Asset {frappe.generate_hash(length=6)}",
            "asset_category": category,
            "gross_purchase_amount": gross,
            "residual_value": 0,
            "depreciation_method": method,
            "total_depreciation_months": months,
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

    def _by_id(self, categories: list[dict], category_id: str) -> dict:
        for c in categories:
            if c.get("category_id") == category_id:
                return c
        self.fail(f"category_id {category_id} không có trong kết quả by-category")

    # ── A. per-category correctness ───────────────────────────────────────────
    def test_aggregates_per_category(self) -> None:
        from assetcore.api.imm00 import get_depreciation_by_category

        cat_a = self._make_category(months=12)
        cat_b = self._make_category(months=24)
        self._make_asset(category=cat_a, gross=100_000_000.0)
        self._make_asset(category=cat_a, gross=100_000_000.0)
        self._make_asset(category=cat_b, gross=50_000_000.0)

        cats = get_depreciation_by_category()["data"]["categories"]

        row_a = self._by_id(cats, cat_a)
        self.assertEqual(row_a["asset_count"], 2)
        self.assertEqual(row_a["configured_count"], 2)
        self.assertEqual(row_a["total_gross"], 200_000_000)
        # asset mới (accumulated=0) ⇒ book = gross (effective_book_value SoT)
        self.assertEqual(row_a["total_book_value"], 200_000_000)
        self.assertEqual(row_a["fully_depreciated"], 0)

        row_b = self._by_id(cats, cat_b)
        self.assertEqual(row_b["asset_count"], 1)
        self.assertEqual(row_b["total_gross"], 50_000_000)

    # ── B. parity với get_depreciation_stats (SoT chung) ──────────────────────
    def test_parity_with_depreciation_stats(self) -> None:
        from assetcore.api.imm00 import (
            get_depreciation_by_category, get_depreciation_stats,
        )

        cat = self._make_category(months=12)
        self._make_asset(category=cat, gross=80_000_000.0)
        self._make_asset(category=cat, gross=120_000_000.0)

        res = get_depreciation_by_category()["data"]
        cats = res["categories"]
        totals = res["totals"]
        stats = get_depreciation_stats()["data"]

        # Σ per-category (int, không rounding) == tổng toàn cục == stats
        self.assertEqual(
            sum(c["asset_count"] for c in cats), totals["total_assets"],
            "Σ asset_count theo danh mục phải == totals.total_assets",
        )
        self.assertEqual(
            totals["total_assets"], stats["total_assets"],
            "totals.total_assets phải == get_depreciation_stats().total_assets",
        )
        self.assertEqual(
            sum(c["fully_depreciated"] for c in cats), stats["fully_depreciated"],
            "Σ fully_depreciated theo danh mục phải == stats.fully_depreciated",
        )
        # cả hai đều round(same_raw_sum, 0) ⇒ khớp tuyệt đối
        self.assertEqual(
            totals["total_gross"], stats["total_gross"],
            "totals.total_gross phải == stats.total_gross (cùng raw sum)",
        )
        # Σ per-category gross (mỗi cat đã round) ≈ grand (dung sai theo #cat)
        self.assertAlmostEqual(
            sum(c["total_gross"] for c in cats), totals["total_gross"],
            delta=len(cats) + 1,
        )


if __name__ == "__main__":
    unittest.main()
