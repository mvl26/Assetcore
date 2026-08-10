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
    _prune_broken_link_customfields,
    _rebuild_module_map,
    before_install,
    prune_orphan_link_customfields,
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


class TestPruneOrphanLinkCustomFields(unittest.TestCase):
    """Dọn orphan Custom Field Link/Table do APP KHÁC để lại (vd ERPNext `company`
    trên Email Account/Communication khi site KHÔNG cài ERPNext).

    Triệu chứng: `Field company is referring to non-existing doctype Company.
    Please delete the field from Email Account-company or add the required doctype.`
    """

    _HOST = "ToDo"  # doctype core LUÔN tồn tại, dùng làm host cho CF test
    _ABSENT = "AC Zzz Nonexistent Target"  # doctype đích cố tình KHÔNG tồn tại

    def _make_cf(self, fieldname: str, fieldtype: str, options: str) -> str:
        """Tạo Custom Field trên host; với Link-orphan thì set options tới doctype
        không tồn tại BẰNG DB trực tiếp (bypass WrongOptionsDoctypeLinkError khi
        insert) — mô phỏng đúng field còn sót sau khi app định nghĩa target bị gỡ."""
        cf = frappe.new_doc("Custom Field")
        cf.dt = self._HOST
        cf.fieldname = fieldname
        cf.label = fieldname
        cf.fieldtype = fieldtype
        # Insert với options HỢP LỆ (hoặc rỗng) để qua validate, rồi ép thành orphan.
        cf.options = "User" if fieldtype in ("Link", "Table", "Table MultiSelect") else ""
        cf.flags.ignore_permissions = True
        cf.insert(ignore_if_duplicate=True)
        if options and options != cf.options:
            frappe.db.set_value("Custom Field", cf.name, "options", options)
        frappe.db.commit()
        return cf.name

    def _drop_cf(self, fieldname: str) -> None:
        cf = frappe.db.exists("Custom Field", {"dt": self._HOST, "fieldname": fieldname})
        if cf:
            frappe.delete_doc("Custom Field", cf, ignore_permissions=True, force=True)
            frappe.db.commit()

    def setUp(self) -> None:
        self._fields = ["_test_orphan_link", "_test_valid_link", "_test_orphan_data"]
        for fn in self._fields:
            self._drop_cf(fn)

    def tearDown(self) -> None:
        for fn in self._fields:
            self._drop_cf(fn)

    def test_prunes_link_field_with_absent_target(self) -> None:
        # Pre: doctype đích không tồn tại → field là orphan.
        self.assertFalse(frappe.db.exists("DocType", self._ABSENT))
        self._make_cf("_test_orphan_link", "Link", self._ABSENT)
        self.assertTrue(
            frappe.db.exists("Custom Field", {"dt": self._HOST, "fieldname": "_test_orphan_link"})
        )

        removed = _prune_broken_link_customfields()

        self.assertGreaterEqual(removed, 1)
        self.assertFalse(
            frappe.db.exists("Custom Field", {"dt": self._HOST, "fieldname": "_test_orphan_link"}),
            "orphan Link CF (target thiếu) PHẢI bị gỡ",
        )

    def test_keeps_link_field_with_existing_target(self) -> None:
        # Field hợp lệ (Link → User, tồn tại) KHÔNG được đụng.
        self._make_cf("_test_valid_link", "Link", "User")

        _prune_broken_link_customfields()

        self.assertTrue(
            frappe.db.exists("Custom Field", {"dt": self._HOST, "fieldname": "_test_valid_link"}),
            "Link CF có target tồn tại PHẢI được giữ",
        )

    def test_ignores_non_link_fieldtype(self) -> None:
        # Field không phải Link/Table (vd Data) dù options lạ cũng KHÔNG bị đụng.
        self._make_cf("_test_orphan_data", "Data", self._ABSENT)

        _prune_broken_link_customfields()

        self.assertTrue(
            frappe.db.exists("Custom Field", {"dt": self._HOST, "fieldname": "_test_orphan_data"}),
            "field non-Link KHÔNG thuộc phạm vi prune",
        )

    def test_idempotent_second_run_is_noop(self) -> None:
        self._make_cf("_test_orphan_link", "Link", self._ABSENT)
        first = _prune_broken_link_customfields()
        self.assertGreaterEqual(first, 1)
        # Lần 2: orphan đã sạch → phần của field test không còn gì để gỡ.
        self.assertFalse(
            frappe.db.exists("Custom Field", {"dt": self._HOST, "fieldname": "_test_orphan_link"})
        )

    def test_public_entrypoint_best_effort_returns_count(self) -> None:
        self._make_cf("_test_orphan_link", "Link", self._ABSENT)
        n = prune_orphan_link_customfields()
        self.assertGreaterEqual(n, 1)


if __name__ == "__main__":
    unittest.main()
