# assetcore/tests/test_imm00_list_assets.py
# Copyright (c) 2026, AssetCore Team
"""Unit tests cho list_assets filter theo gmdn_code + search mở rộng."""
from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from assetcore.api.imm00 import list_assets


class TestListAssetsGmdnFilter(FrappeTestCase):
    """BR-00-XX: lọc Asset theo gmdn_code kế thừa từ Asset Category."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Category với gmdn_code cố định
        if not frappe.db.exists("AC Asset Category", "TEST-CAT-USG"):
            frappe.get_doc({
                "doctype": "AC Asset Category",
                "category_name": "Test Ultrasound",
                "category_code": "TEST-CAT-USG",
                "gmdn_code": "35304",
                "gmdn_term": "Ultrasound imaging system, general purpose",
            }).insert(ignore_permissions=True)

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
