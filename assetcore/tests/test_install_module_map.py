# Copyright (c) 2026, AssetCore Team
"""Regression: before_install rebuilds module map for fresh cloud install.

Bug (cloud, bench đang chạy): `bench install-app assetcore` báo
`Workflow sync error … DocType <X> not found` cho MỌI doctype + `_seed_uoms` lỗi
`No module named 'frappe.core.doctype.ac_uom'`. Nguyên nhân: Redis cache
`app_modules` cũ (set trước khi assetcore vào bench) thiếu key "assetcore" →
`setup_module_map()` dùng cache cũ → `frappe.local.app_modules` thiếu "assetcore" →
`sync_for("assetcore")` lặp 0 module → 0/108 doctype được sync.

`before_install()` phải bust cache + rebuild để map chứa "assetcore" → sync_for
thấy module và sync đủ doctype.

Run:
    bench --site miyano run-tests --app assetcore \
        --module assetcore.tests.test_install_module_map
"""
from __future__ import annotations

import unittest

import frappe

from assetcore.setup.install import (
    _drop_orphan_user_link_fields,
    _ensure_app_doctypes_synced,
    _foreign_custom_field_specs,
    _rebuild_module_map,
    before_install,
)


class TestInstallModuleMap(unittest.TestCase):
    def setUp(self) -> None:
        self._saved_local = frappe.local.app_modules
        self._saved_cache = frappe.cache.get_value("app_modules")

    def tearDown(self) -> None:
        # Khôi phục map đúng để không ảnh hưởng test khác trong cùng tiến trình.
        frappe.local.app_modules = self._saved_local
        if self._saved_cache is not None:
            frappe.cache.set_value("app_modules", self._saved_cache)
        else:
            frappe.cache.delete_value("app_modules")
        frappe.setup_module_map(include_all_apps=True)

    def test_before_install_recovers_assetcore_module_from_stale_cache(self) -> None:
        # Giả lập cache cũ: app_modules KHÔNG có "assetcore" (in-memory + Redis).
        stale = {"frappe": ["frappe", "core"]}
        frappe.local.app_modules = dict(stale)
        frappe.cache.set_value("app_modules", dict(stale))

        # Tiền điều kiện: map đang thiếu assetcore (state mà sync_for lỗi).
        self.assertIsNone(frappe.local.app_modules.get("assetcore"))

        before_install()

        # Sau fix: map chứa module "assetcore" → sync_for sẽ import doctype.
        mods = frappe.local.app_modules.get("assetcore")
        self.assertIsNotNone(
            mods, "before_install phải rebuild app_modules chứa key 'assetcore'"
        )
        self.assertIn(
            "assetcore",
            mods,
            "module 'assetcore' (scrub của 'AssetCore') phải có trong app_modules",
        )

    def test_rebuild_module_map_recovers_from_stale_cache(self) -> None:
        # _rebuild_module_map (helper dùng chung) cũng phải khôi phục được.
        frappe.local.app_modules = {"frappe": ["frappe", "core"]}
        frappe.cache.set_value("app_modules", {"frappe": ["frappe", "core"]})

        _rebuild_module_map()

        self.assertIn("assetcore", frappe.local.app_modules.get("assetcore") or [])

    def test_ensure_app_doctypes_synced_is_noop_when_present(self) -> None:
        # Trên site test, "AC Asset" đã tồn tại → self-heal phải no-op nhanh,
        # KHÔNG đụng module map (giữ nguyên app_modules đang đúng).
        before = frappe.local.app_modules
        _ensure_app_doctypes_synced()
        self.assertTrue(frappe.db.exists("DocType", "AC Asset"))
        self.assertIs(frappe.local.app_modules, before)

    def test_drop_orphan_keeps_valid_field_when_target_exists(self) -> None:
        # An toàn: KHÔNG gỡ Custom Field còn hợp lệ. Trên site test "AC Department"
        # tồn tại → field User.ac_department phải được GIỮ NGUYÊN.
        self.assertTrue(frappe.db.exists("DocType", "AC Department"))
        cf_before = frappe.db.exists(
            "Custom Field", {"dt": "User", "fieldname": "ac_department"}
        )
        _drop_orphan_user_link_fields()
        cf_after = frappe.db.exists(
            "Custom Field", {"dt": "User", "fieldname": "ac_department"}
        )
        self.assertEqual(
            cf_before,
            cf_after,
            "field hợp lệ (target tồn tại) KHÔNG được bị gỡ",
        )

    def test_foreign_custom_field_specs_covers_user_and_asset(self) -> None:
        # before_uninstall phải biết gỡ field AssetCore khỏi doctype core/ERPNext.
        specs = _foreign_custom_field_specs()
        # User: field gây crash + các field IMM khác.
        self.assertIn(("User", "ac_department"), specs)
        self.assertIn(("User", "imm_approval_status"), specs)
        # ERPNext Asset: field từ asset_custom_fields.json (kể cả khi chưa cài ERPNext,
        # spec vẫn liệt kê để dọn sạch nếu site có Asset).
        asset_specs = [fn for (dt, fn) in specs if dt == "Asset"]
        self.assertIn("custom_imm_device_model", asset_specs)
        # KHÔNG đụng tới doctype của chính AssetCore (chúng tự drop theo app).
        self.assertNotIn(
            "AC Asset", {dt for (dt, _fn) in specs}
        )


if __name__ == "__main__":
    unittest.main()
