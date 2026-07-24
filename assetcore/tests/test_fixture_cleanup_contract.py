# Copyright (c) 2026, AssetCore Team
"""Hợp đồng dọn fixture của test — chống rò data test ra site thật.

Bối cảnh (2026-07-22): sau khi purge sạch site, MỘT lần chạy
``bench run-tests --module assetcore.tests.test_imm00`` để lại **18 Asset
Decommission + 1 AC Asset**. Truy nguyên: ``test_imm00.py`` giữ MỘT BẢN SAO cục
bộ của ``_purge_asset`` với danh sách dependent thiếu ``Asset Decommission``,
trong khi helper dùng chung ``_asset_cleanup.purge_asset`` đã có đủ. Mỗi asset
bị decommission qua ``decommission_via_closure`` để lại phiếu thanh lý mồ côi →
đây là nguồn tái sinh của rác test (STATE Blocker#5).

Khoá 2 bất biến:
  A. HÀNH VI — purge một asset đã decommission phải xoá luôn phiếu thanh lý.
  B. CẤU TRÚC — không app-test nào được tự định nghĩa lại ``_purge_asset``;
     phải dùng chung ``_asset_cleanup.purge_asset`` (một nguồn sự thật, để lần
     sau thêm dependent mới thì mọi test module cùng được vá).

Run:
    bench --site miyano run-tests --app assetcore \
        --module assetcore.tests.test_fixture_cleanup_contract
"""
from __future__ import annotations

import time
import unittest

import frappe

from assetcore.tests import _asset_cleanup
from assetcore.tests._asset_cleanup import decommission_via_closure, purge_asset

_UID = str(int(time.time()) % 100000)


def setUpModule():
    frappe.set_user("Administrator")


def _make_asset(tag: str) -> str:
    """Asset tối thiểu, bypass workflow (fixture chỉ để test dọn dẹp)."""
    if not frappe.db.exists("AC UOM", "Cái"):
        frappe.get_doc({"doctype": "AC UOM", "uom_name": "Cái"}).insert(ignore_permissions=True)
    doc = frappe.get_doc({
        "doctype": "AC Asset",
        "asset_name": f"_Test CleanupContract {tag}",
        "lifecycle_status": "Active",
        "gross_purchase_amount": 10_000_000,
        "in_service_date": "2024-01-01",
    })
    doc.flags.ignore_mandatory = True
    doc.flags.ignore_links = True
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    try:
        doc.insert(ignore_permissions=True)
    finally:
        frappe.flags.in_install = prev
    frappe.db.commit()
    return doc.name


class TestPurgeAssetRemovesDecommission(unittest.TestCase):
    """A. Hành vi — không để lại phiếu thanh lý mồ côi."""

    def setUp(self):
        frappe.set_user("Administrator")
        self.asset = _make_asset(f"beh-{_UID}")

    def tearDown(self):
        frappe.set_user("Administrator")
        if frappe.db.exists("AC Asset", self.asset):
            purge_asset(self.asset)
        frappe.db.commit()

    def test_shared_purge_removes_decommission_record(self):
        rec = decommission_via_closure(self.asset)
        self.assertTrue(frappe.db.exists("Asset Decommission", rec),
                        "Tiền đề: closure phải tạo phiếu thanh lý")

        purge_asset(self.asset)
        frappe.db.commit()

        self.assertFalse(
            frappe.db.exists("Asset Decommission", rec),
            "purge_asset PHẢI xoá phiếu thanh lý — nếu không, mỗi lần chạy test "
            "lại để lại rác trên site (STATE Blocker#5)",
        )
        self.assertFalse(frappe.db.exists("AC Asset", self.asset))

    def test_purge_leaves_no_orphan_for_any_dependent_doctype(self):
        """Mọi doctype trong `_ASSET_DEPENDENTS` phải sạch sau purge."""
        rec = decommission_via_closure(self.asset)
        self.assertTrue(rec)
        purge_asset(self.asset)
        frappe.db.commit()

        leftovers = []
        for dt, fld in _asset_cleanup._ASSET_DEPENDENTS:
            if not (frappe.db.table_exists(dt) and frappe.db.has_column(dt, fld)):
                continue
            if frappe.db.count(dt, {fld: self.asset}):
                leftovers.append(dt)
        self.assertEqual(leftovers, [], f"Còn record mồ côi ở: {leftovers}")


class TestNoDuplicatePurgeHelper(unittest.TestCase):
    """B. Cấu trúc — một nguồn sự thật cho teardown."""

    def test_test_modules_reuse_shared_purge_helper(self):
        """Quét ĐỘNG mọi module test — danh sách cứng sẽ bỏ sót module mới.

        Bằng chứng cần quét động: bản guard đầu chỉ liệt kê ``test_imm00`` nên
        ``test_imm05`` (cũng có bản sao lệch) vẫn rò 6 asset mỗi lần chạy.
        """
        import importlib
        import pkgutil

        import assetcore.tests as tests_pkg

        divergent = []
        for info in pkgutil.iter_modules(tests_pkg.__path__):
            if not info.name.startswith("test_"):
                continue
            mod_name = f"assetcore.tests.{info.name}"
            try:
                mod = importlib.import_module(mod_name)
            except Exception:  # module lỗi import là việc của test khác
                continue
            local = getattr(mod, "_purge_asset", None)
            if local is None:
                continue
            if local is not purge_asset:
                divergent.append(mod_name)
        self.assertEqual(
            divergent,
            [],
            "Các module sau tự định nghĩa lại `_purge_asset` thay vì dùng "
            "`_asset_cleanup.purge_asset` → danh sách dependent sẽ lệch và rò "
            f"data test ra site: {divergent}",
        )

    def test_asset_heavy_modules_have_module_level_safety_net(self):
        """Module tạo nhiều asset PHẢI có lưới an toàn ``tearDownModule``.

        Teardown theo-class hụt khi test tương tác nhau (đo thực tế: chạy riêng
        1 test thì sạch, chạy CẢ module thì sót asset). Lưới cuối module là thứ
        duy nhất chặn được, nên phải khoá lại bằng guard.
        """
        import importlib
        import inspect

        missing = []
        for mod_name in ("assetcore.tests.test_imm00", "assetcore.tests.test_imm05"):
            mod = importlib.import_module(mod_name)
            teardown = getattr(mod, "tearDownModule", None)
            if teardown is None:
                missing.append(f"{mod_name}: thiếu tearDownModule")
                continue
            src = inspect.getsource(teardown)
            if "purge_assets_created_after" not in src and "purge_assets_by_name_prefix" not in src:
                missing.append(f"{mod_name}: tearDownModule không gọi lưới purge")
        self.assertEqual(missing, [], f"Thiếu lưới an toàn: {missing}")

    def test_shared_helper_covers_decommission(self):
        """Guard tự-cắn: `Asset Decommission` phải nằm trong danh sách dependent."""
        doctypes = {dt for dt, _ in _asset_cleanup._ASSET_DEPENDENTS}
        self.assertIn(
            "Asset Decommission",
            doctypes,
            "Bỏ `Asset Decommission` khỏi _ASSET_DEPENDENTS = mở lại đúng lỗ rò đã vá",
        )


if __name__ == "__main__":
    unittest.main()
