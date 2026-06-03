# Copyright (c) 2026, AssetCore Team
import unittest

import frappe

# AC Asset Category autonames to a CAT-#### series, so the document name is NOT
# the category_name value. Existence / cleanup must resolve through the
# category_name field, otherwise leaked rows collide on the unique index.
_TEST_CATEGORY_NAMES = (
    "_TestCatGMDN A", "_TestCatGMDN B", "_TestCatGMDN C",
    "_TestCatGMDN D", "_TestCatGMDN E", "_TestCatGMDN F",
)
_TEST_GMDN_CODES = ("GMDN-DUP-001", "GMDN-UNQ-100", "GMDN-UNQ-200")


def _purge_test_categories():
    """Delete every test category by resolving the real CAT-#### doc name from
    its category_name / gmdn_code. Idempotent; safe to call repeatedly."""
    names = set()
    for value in _TEST_CATEGORY_NAMES:
        names.update(frappe.get_all(
            "AC Asset Category", filters={"category_name": value}, pluck="name"
        ))
    for value in _TEST_GMDN_CODES:
        names.update(frappe.get_all(
            "AC Asset Category", filters={"gmdn_code": value}, pluck="name"
        ))
    for doc_name in names:
        frappe.delete_doc("AC Asset Category", doc_name, force=True, ignore_permissions=True)


class TestACAssetCategory(unittest.TestCase):
    def setUp(self):
        _purge_test_categories()

    def _make_cat(self, name: str, gmdn: str | None = None):
        existing = frappe.get_all(
            "AC Asset Category", filters={"category_name": name}, pluck="name"
        )
        for doc_name in existing:
            frappe.delete_doc("AC Asset Category", doc_name, force=True, ignore_permissions=True)
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
        _purge_test_categories()
