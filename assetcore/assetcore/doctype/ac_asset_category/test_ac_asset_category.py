# Copyright (c) 2026, AssetCore Team
import unittest

import frappe


class TestACAssetCategory(unittest.TestCase):
    def _make_cat(self, name: str, gmdn: str | None = None):
        if frappe.db.exists("AC Asset Category", name):
            frappe.delete_doc("AC Asset Category", name, force=True)
        doc = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": name,
            "gmdn_code": gmdn,
        })
        doc.insert(ignore_permissions=True)
        return doc

    def test_duplicate_gmdn_raises(self):
        self._make_cat("_TestCatGMDN A", "GMDN-DUP-001")
        with self.assertRaises(frappe.ValidationError) as ctx:
            self._make_cat("_TestCatGMDN B", "GMDN-DUP-001")
        self.assertIn("GMDN", str(ctx.exception))

    def test_unique_gmdn_succeeds(self):
        a = self._make_cat("_TestCatGMDN C", "GMDN-UNQ-100")
        b = self._make_cat("_TestCatGMDN D", "GMDN-UNQ-200")
        self.assertTrue(a.name and b.name)

    def test_empty_gmdn_allowed_multiple(self):
        a = self._make_cat("_TestCatGMDN E", None)
        b = self._make_cat("_TestCatGMDN F", None)
        self.assertTrue(a.name and b.name)

    def tearDown(self):
        for n in (
            "_TestCatGMDN A", "_TestCatGMDN B", "_TestCatGMDN C",
            "_TestCatGMDN D", "_TestCatGMDN E", "_TestCatGMDN F",
        ):
            if frappe.db.exists("AC Asset Category", n):
                frappe.delete_doc("AC Asset Category", n, force=True)
