# Copyright (c) 2026, AssetCore Team
"""L-18b (audit BaoCao_RaSoat_AssetCore_17062026) — seed master data idempotent.

Pin CƠ CHẾ idempotent của patch 010_seed_master_data._seed: tạo 1 lần, lần sau
bỏ qua (skip-if-exists), KHÔNG nhân đôi. Dùng UOM throwaway (`_TestSeedUOM-<tag>`)
để KHÔNG đụng nội dung seed thật và tự dọn ở tearDown.

Patch nạp khi `bench migrate` (user chạy lúc deploy — HARD-STOP no-migrate ở phiên
build). Test này chạy độc lập, không cần migrate.

Run: bench --site miyano run-tests --module assetcore.tests.test_seed_master_data
"""
from __future__ import annotations

import importlib
import time
import unittest

import frappe

_PATCH = importlib.import_module("assetcore.patches.v3_2.010_seed_master_data")
_seed = _PATCH._seed


class TestSeedMasterDataIdempotent(unittest.TestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._uom = f"_TestSeedUOM-{str(int(time.time() * 1000))[-7:]}"

    def tearDown(self):
        existing = frappe.db.get_value("AC UOM", {"uom_name": self._uom}, "name")
        if existing:
            frappe.delete_doc("AC UOM", existing, force=True, ignore_permissions=True)
        frappe.db.commit()

    def test_seed_creates_once_then_skips(self):
        rows = [{"uom_name": self._uom, "symbol": "x", "must_be_whole_number": 1}]
        self.assertEqual(_seed("AC UOM", "uom_name", rows), 1, "lần đầu tạo 1 bản ghi")
        self.assertEqual(_seed("AC UOM", "uom_name", rows), 0, "lần hai bỏ qua (idempotent)")
        self.assertEqual(
            frappe.db.count("AC UOM", {"uom_name": self._uom}), 1, "không nhân đôi bản ghi"
        )


if __name__ == "__main__":
    unittest.main()
