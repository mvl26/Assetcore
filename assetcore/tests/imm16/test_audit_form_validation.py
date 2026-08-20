# Copyright (c) 2026, AssetCore Team
"""Audit-fix BE validation invariants (BaoCao_RaSoat_AssetCore_17062026).

Covers the server-side guards that back the client-side form validation:
  T2 (L-01/L-09): AC Supplier email_id / technical_email → Vietnamese throw
                  (NOT the framework English "is not a valid Email Address").
  T3 (L-02):      AC Asset gross_purchase_amount must NOT be negative.
  T7 (L-06):      depreciation_start_date falls back to purchase_date before
                  nowdate() when in_service / commissioning are absent.

Run:
  bench --site miyano run-tests --app assetcore \
      --module assetcore.tests.imm16.test_audit_form_validation
"""
from __future__ import annotations

import unittest

import frappe

from assetcore.tests._helpers._asset_cleanup import purge_asset
from frappe.tests.utils import FrappeTestCase

_DT_SUP = "AC Supplier"
_DT_ASSET = "AC Asset"


def _make_supplier(**overrides) -> frappe.model.document.Document:
    data = {
        "doctype": _DT_SUP,
        "supplier_name": "_T-AuditVal NCC",
        "supplier_group": "Manufacturer",
        "vendor_type": "Manufacturer",
        "country": "Vietnam",
        "is_active": 1,
    }
    data.update(overrides)
    return frappe.get_doc(data)


def _insert_asset_bypass(**overrides) -> str:
    """Insert AC Asset bypassing workflow/mandatory (same pattern as
    test_depreciation._make_asset). Returns the asset name."""
    data = {
        "doctype": _DT_ASSET,
        "asset_name": "_T-AuditVal Asset",
        "lifecycle_status": "Active",
    }
    data.update(overrides)
    doc = frappe.get_doc(data)
    doc.flags.ignore_mandatory = True
    doc.flags.ignore_links = True
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    try:
        doc.insert(ignore_permissions=True)
    finally:
        frappe.flags.in_install = prev
    return doc.name


class TestSupplierEmailValidation(FrappeTestCase):
    """T2 — supplier email fields throw a Vietnamese message, not English."""

    def setUp(self) -> None:
        frappe.set_user("Administrator")
        self._created: list[str] = []

    def tearDown(self) -> None:
        frappe.set_user("Administrator")
        for name in self._created:
            frappe.delete_doc(_DT_SUP, name, force=True, ignore_permissions=True)

    def test_invalid_email_id_throws_vietnamese(self) -> None:
        sup = _make_supplier(email_id="not-an-email")
        with self.assertRaises(frappe.ValidationError) as ctx:
            sup.insert(ignore_permissions=True)
        msg = str(ctx.exception)
        self.assertIn("không hợp lệ", msg)
        self.assertNotIn("valid Email Address", msg)

    def test_invalid_technical_email_throws_vietnamese(self) -> None:
        sup = _make_supplier(technical_email="bad@@x")
        with self.assertRaises(frappe.ValidationError) as ctx:
            sup.insert(ignore_permissions=True)
        msg = str(ctx.exception)
        self.assertIn("không hợp lệ", msg)
        self.assertNotIn("valid Email Address", msg)

    def test_valid_emails_pass(self) -> None:
        sup = _make_supplier(
            email_id="sales@drager.com.vn",
            technical_email="tech@drager.com.vn",
        )
        sup.insert(ignore_permissions=True)
        self._created.append(sup.name)
        self.assertTrue(frappe.db.exists(_DT_SUP, sup.name))

    def test_blank_emails_pass(self) -> None:
        sup = _make_supplier()
        sup.insert(ignore_permissions=True)
        self._created.append(sup.name)
        self.assertTrue(frappe.db.exists(_DT_SUP, sup.name))


class TestAssetNegativePriceGuard(FrappeTestCase):
    """T3 — gross_purchase_amount must not be negative."""

    def setUp(self) -> None:
        frappe.set_user("Administrator")
        self._created: list[str] = []

    def tearDown(self) -> None:
        frappe.set_user("Administrator")
        for name in self._created:
            purge_asset(name)

    def test_negative_gross_rejected(self) -> None:
        with self.assertRaises(frappe.ValidationError) as ctx:
            _insert_asset_bypass(gross_purchase_amount=-1000)
        self.assertIn("âm", str(ctx.exception))

    def test_zero_gross_ok(self) -> None:
        name = _insert_asset_bypass(gross_purchase_amount=0)
        self._created.append(name)
        self.assertTrue(frappe.db.exists(_DT_ASSET, name))

    def test_positive_gross_ok(self) -> None:
        name = _insert_asset_bypass(gross_purchase_amount=5_000_000)
        self._created.append(name)
        self.assertTrue(frappe.db.exists(_DT_ASSET, name))


class TestDepreciationStartFallback(FrappeTestCase):
    """T7 — depreciation_start_date uses purchase_date before today."""

    def setUp(self) -> None:
        frappe.set_user("Administrator")
        self._created: list[str] = []

    def tearDown(self) -> None:
        frappe.set_user("Administrator")
        for name in self._created:
            purge_asset(name)

    def test_purchase_date_used_when_no_in_service(self) -> None:
        from frappe.utils import getdate

        name = _insert_asset_bypass(
            gross_purchase_amount=80_000_000,
            purchase_date="2024-01-15",
        )
        self._created.append(name)
        start = frappe.db.get_value(_DT_ASSET, name, "depreciation_start_date")
        self.assertEqual(getdate(start), getdate("2024-01-15"))

    def test_in_service_still_wins_over_purchase(self) -> None:
        from frappe.utils import getdate

        name = _insert_asset_bypass(
            gross_purchase_amount=80_000_000,
            purchase_date="2024-01-15",
            in_service_date="2024-03-01",
        )
        self._created.append(name)
        start = frappe.db.get_value(_DT_ASSET, name, "depreciation_start_date")
        self.assertEqual(getdate(start), getdate("2024-03-01"))


if __name__ == "__main__":
    unittest.main()
