# assetcore/tests/imm00/test_imm00_list_assets.py
# Copyright (c) 2026, AssetCore Team
"""Unit tests cho list_assets filter theo gmdn_code + search mở rộng.

Ngoài suite gmdn filter, file này khoá HỢP ĐỒNG enrich `category_name` của
`list_assets` (CR-64): LIST phải phát cùng key `category_name` như DETAIL
(`get_asset`) và như OAS `AssetListItem.category_name`, KHÔNG phát key thừa
`asset_category_name` (contract-vs-impl parity, chống drift runtime↔OpenAPI).
"""
from __future__ import annotations

import time

import frappe
from frappe.tests.utils import FrappeTestCase

from assetcore.api.imm00 import get_asset, list_assets


def _insert_asset_bypass_workflow(data: dict):
    """Insert AC Asset bypassing workflow guard (BR-00-02) cho fixture test."""
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    try:
        return frappe.get_doc(data).insert(ignore_permissions=True)
    finally:
        frappe.flags.in_install = prev


class TestListAssetsGmdnFilter(FrappeTestCase):
    """BR-00-XX: lọc Asset theo gmdn_code kế thừa từ Asset Category."""

    _cat_name: str | None = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # AC Asset Category autoname=CAT-#### → lookup by category_code field, NOT
        # by name (LL-TEST-9). Track the real doc-name so tearDownClass can purge it.
        existing = frappe.db.get_value(
            "AC Asset Category", {"category_code": "TEST-CAT-USG"}, "name"
        )
        if existing:
            cls._cat_name = existing
        else:
            doc = frappe.get_doc({
                "doctype": "AC Asset Category",
                "category_name": "Test Ultrasound",
                "category_code": "TEST-CAT-USG",
                "gmdn_code": "35304",
                "gmdn_term": "Ultrasound imaging system, general purpose",
            }).insert(ignore_permissions=True)
            cls._cat_name = doc.name

    @classmethod
    def tearDownClass(cls):
        # Purge the self-seeded category so it never leaks into prod-like lists.
        if cls._cat_name and frappe.db.exists("AC Asset Category", cls._cat_name):
            frappe.delete_doc("AC Asset Category", cls._cat_name,
                              force=True, ignore_permissions=True)
            frappe.db.commit()
        super().tearDownClass()

    def test_filter_by_gmdn_code_returns_only_matching_assets(self):
        # list_assets bọc kết quả trong envelope _ok → {success, data}
        result = list_assets(gmdn_code="35304")
        data = result["data"]
        assert "items" in data
        for item in data["items"]:
            assert item["gmdn_code"] == "35304"

    def test_search_by_gmdn_code_substring(self):
        result = list_assets(search="35304")
        data = result["data"]
        # Không raise; items có thể rỗng nếu chưa có asset thật
        assert "items" in data
        assert "pagination" in data

    def test_gmdn_status_param_removed(self):
        import inspect
        sig = inspect.signature(list_assets)
        assert "gmdn_status" not in sig.parameters, \
            "list_assets() vẫn còn param gmdn_status — phải xoá."


class TestListAssetsCategoryNameParity(FrappeTestCase):
    """CR-64 — `list_assets` enrich `category_name` (parity DETAIL + OAS).

    LIST phải phát key `category_name` (== AC Asset Category.category_name, tên VN)
    và KHÔNG phát key legacy `asset_category_name` — khớp `get_asset` (:508) và OAS
    `AssetListItem.category_name` (additionalProperties:false). 5 field enrich còn
    lại (department/location/supplier/device_model/responsible_technician) GIỮ NGUYÊN.
    """

    _uid = str(int(time.time()) % 1000000)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        cls._cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị siêu âm",
            "category_code": f"_TestCatName-{cls._uid}",
        }).insert(ignore_permissions=True)
        cls._dept = frappe.get_doc({
            "doctype": "AC Department",
            "department_name": f"_Test Khoa CĐHA {cls._uid}",
        }).insert(ignore_permissions=True)
        cls._loc = frappe.get_doc({
            "doctype": "AC Location",
            "location_name": f"_Test Phòng SA {cls._uid}",
        }).insert(ignore_permissions=True)
        cls._sup = frappe.get_doc({
            "doctype": "AC Supplier",
            "supplier_name": f"_Test NCC {cls._uid}",
            "supplier_group": "Manufacturer",
            "vendor_type": "Manufacturer",
        }).insert(ignore_permissions=True)
        cls._model = frappe.get_doc({
            "doctype": "IMM Device Model",
            "model_name": f"_Test Model SA {cls._uid}",
            "manufacturer": "GE (list-cat)",
            "medical_device_class": "Class II",
            "asset_category": cls._cat.name,
        }).insert(ignore_permissions=True)
        cls._tech = "Administrator"
        cls._tech_full = frappe.db.get_value("User", cls._tech, "full_name") or ""
        # asset_name KHÔNG prefix '_' — reserved_asset_names() ẩn asset '_…' khỏi
        # list_assets (data-hygiene). Cần list-visible để kiểm enrich; tearDownClass
        # purge (force) nên không leak prod.
        cls._asset = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": f"CR64 SA Enrich {cls._uid}",
            "asset_category": cls._cat.name,
            "department": cls._dept.name,
            "location": cls._loc.name,
            "supplier": cls._sup.name,
            "device_model": cls._model.name,
            "responsible_technician": cls._tech,
            "manufacturer_sn": f"_TestSN-catname-{cls._uid}",
            "medical_device_class": "Class II",
            "lifecycle_status": "Active",
        })
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        frappe.db.sql("DELETE FROM `tabIMM Audit Trail` WHERE asset=%s", (cls._asset.name,))
        frappe.db.sql("DELETE FROM `tabAsset Lifecycle Event` WHERE asset=%s", (cls._asset.name,))
        frappe.delete_doc("AC Asset", cls._asset.name, force=True, ignore_permissions=True)
        frappe.delete_doc("IMM Device Model", cls._model.name, force=True, ignore_permissions=True)
        frappe.delete_doc("AC Supplier", cls._sup.name, force=True, ignore_permissions=True)
        frappe.delete_doc("AC Location", cls._loc.name, force=True, ignore_permissions=True)
        frappe.delete_doc("AC Department", cls._dept.name, force=True, ignore_permissions=True)
        frappe.delete_doc("AC Asset Category", cls._cat.name, force=True, ignore_permissions=True)
        frappe.db.commit()
        super().tearDownClass()

    def _find_item(self):
        """Lấy item test khỏi list_assets (filter theo category test → deterministic)."""
        data = list_assets(asset_category=self._cat.name)["data"]
        items = [it for it in data["items"] if it["name"] == self._asset.name]
        self.assertEqual(
            len(items), 1,
            f"Không tìm thấy asset test trong list_assets: {data['items']}",
        )
        return items[0]

    def test_list_assets_emits_category_name(self):
        # RED trước fix: hiện phát key 'asset_category_name', thiếu 'category_name'.
        item = self._find_item()
        self.assertEqual(
            item.get("category_name"), "Thiết bị siêu âm",
            "list_assets item phải mang key category_name = tên nhóm VN.",
        )

    def test_list_assets_drops_legacy_asset_category_name(self):
        # RED trước fix: parity contract — hết field không-khai 'asset_category_name'.
        item = self._find_item()
        self.assertNotIn(
            "asset_category_name", item,
            "list_assets KHÔNG được phát key legacy 'asset_category_name' "
            "(lệch OAS AssetListItem additionalProperties:false + lệch get_asset).",
        )

    def test_list_assets_category_parity_with_get_asset(self):
        # INVARIANT LIST↔DETAIL: cùng asset → cùng giá trị category_name.
        list_item = self._find_item()
        detail = get_asset(self._asset.name)["data"]
        self.assertEqual(
            list_item.get("category_name"), detail.get("category_name"),
            "category_name phải KHỚP giữa list_assets và get_asset cho cùng asset.",
        )
        self.assertEqual(detail.get("category_name"), "Thiết bị siêu âm")

    def test_list_assets_sibling_enrich_intact(self):
        # Regression guard cho thay đổi 1-dòng: 5 enrich còn lại giữ mặt + đúng giá trị.
        item = self._find_item()
        self.assertEqual(item.get("department_name"), self._dept.department_name)
        self.assertEqual(item.get("location_name"), self._loc.location_name)
        self.assertEqual(item.get("supplier_name"), self._sup.supplier_name)
        self.assertEqual(item.get("device_model_name"), self._model.model_name)
        self.assertEqual(item.get("responsible_technician_name"), self._tech_full)
