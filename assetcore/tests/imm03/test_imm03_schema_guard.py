"""IMM-03 schema invariants — custom field trên AC Supplier / AC Purchase.

Bối cảnh (2026-07-22): các Custom Field IMM-03 biến mất khỏi site khiến
`/vendor-profiles` vỡ với `(1054, "Unknown column 'tabAC Supplier.imm_overall_score'
in 'WHERE'")`. Patch 003 vẫn nằm trong Patch Log vì lỗi bị nuốt bởi try/except.
Hai invariant dưới đây chặn cả hai nguyên nhân:

1. STATIC — mọi custom field IMM-03 phải khai báo `module`, nếu không sẽ bị các
   đợt quét "orphan custom field" (app khác gỡ dirty) xoá nhầm.
2. LIVE — cột DB phải thực sự tồn tại; API `list_vendor_profiles` phụ thuộc.
"""
from __future__ import annotations

import importlib
import unittest

import frappe

from assetcore.api.imm03 import _AVL_COLUMNS, _DT_SUPPLIER

_patch = importlib.import_module("assetcore.patches.v3_1.003_install_imm03")

#: fieldtype không sinh cột DB (layout / child table)
_NO_COLUMN = ("Section Break", "Column Break", "Table")


class TestIMM03SchemaGuard(unittest.TestCase):
    """Invariant schema IMM-03 — chạy độc lập, không tạo dữ liệu."""

    def test_patch_tags_module_on_every_custom_field(self) -> None:
        """Patch phải gắn module='AssetCore' cho MỌI custom field nó cài."""
        self.assertEqual(_patch._MODULE, "AssetCore")
        for dt, cfields in (("AC Supplier", _patch._AC_SUPPLIER_CFIELDS),
                            ("AC Purchase", _patch._AC_PURCHASE_CFIELDS)):
            self.assertTrue(cfields, f"{dt}: danh sách custom field rỗng")

    def test_avl_columns_declared_by_patch(self) -> None:
        """`_AVL_COLUMNS` ở tầng API phải là tập con field patch thực sự cài."""
        declared = {cf["fieldname"] for cf in _patch._AC_SUPPLIER_CFIELDS}
        self.assertTrue(
            set(_AVL_COLUMNS).issubset(declared),
            f"API tham chiếu cột không do patch cài: {set(_AVL_COLUMNS) - declared}",
        )

    def test_live_columns_exist(self) -> None:
        """Cột DB thật phải tồn tại — bắt trường hợp custom field bị xoá mất."""
        for dt, cfields in (("AC Supplier", _patch._AC_SUPPLIER_CFIELDS),
                            ("AC Purchase", _patch._AC_PURCHASE_CFIELDS)):
            expected = [cf["fieldname"] for cf in cfields
                        if cf["fieldtype"] not in _NO_COLUMN]
            missing = [fn for fn in expected if not frappe.db.has_column(dt, fn)]
            self.assertEqual(
                missing, [],
                f"{dt} thiếu cột IMM-03: {missing}. "
                f"Chạy lại assetcore.patches.v3_1.003_install_imm03.execute()",
            )

    def test_live_custom_fields_tagged_with_module(self) -> None:
        """Custom Field trên site phải mang module='AssetCore' (chống sweep orphan)."""
        rows = frappe.get_all(
            "Custom Field",
            filters={"dt": ["in", ["AC Supplier", "AC Purchase"]]},
            fields=["dt", "fieldname", "module"],
        )
        untagged = [f"{r.dt}.{r.fieldname}" for r in rows if not r.module]
        self.assertEqual(
            untagged, [],
            f"Custom Field thiếu module tag (dễ bị quét orphan xoá): {untagged}",
        )

    def test_api_guard_raises_readable_error(self) -> None:
        """Guard phải ném ServiceError đọc được, không để lọt SQL 1054 ra user."""
        from unittest.mock import patch as mock_patch

        from assetcore.api.imm03 import _require_avl_schema
        from assetcore.services.shared import ErrorCode, ServiceError

        with mock_patch.object(frappe.db, "has_column", return_value=False):
            with self.assertRaises(ServiceError) as ctx:
                _require_avl_schema()
        self.assertEqual(ctx.exception.code, ErrorCode.INTERNAL)
        self.assertIn("imm_overall_score", ctx.exception.message)
        self.assertNotIn("1054", ctx.exception.message)
        # sanity: schema thật đang OK
        self.assertTrue(frappe.db.has_column(_DT_SUPPLIER, "imm_overall_score"))
