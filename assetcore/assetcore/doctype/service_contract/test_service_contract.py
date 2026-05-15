# Copyright (c) 2026, AssetCore Team
"""Service Contract — slide 05b/c: contract_code/sign_date/amount_in_words.

Run: bench --site miyano run-tests --module assetcore.assetcore.doctype.service_contract.test_service_contract
"""
import unittest

import frappe
from frappe.utils import add_days, nowdate


class TestServiceContract(unittest.TestCase):
    def _supplier(self) -> str:
        existing = frappe.db.get_value(
            "AC Supplier", {"supplier_name": "_TestSCSupplier"}, "name"
        )
        if existing:
            return existing
        doc = frappe.get_doc({
            "doctype": "AC Supplier",
            "supplier_name": "_TestSCSupplier",
        }).insert(ignore_permissions=True)
        return doc.name

    def _make(self, code: str, value: float | None):
        return frappe.get_doc({
            "doctype": "Service Contract",
            "contract_code": code,
            "contract_title": f"HĐ {code}",
            "supplier": self._supplier(),
            "contract_type": "Preventive Maintenance",
            "contract_start": nowdate(),
            "contract_end": add_days(nowdate(), 365),
            "sign_date": nowdate(),
            "contract_value": value,
        }).insert(ignore_permissions=True)

    def test_amount_in_words_autopopulated(self):
        doc = self._make("_TC-AIW-01", 1000000)
        self.assertEqual(doc.amount_in_words, "Một triệu đồng")

    def test_amount_in_words_empty_when_no_value(self):
        doc = self._make("_TC-AIW-02", None)
        self.assertFalsy = self.assertFalse
        self.assertFalse(doc.amount_in_words)

    def test_duplicate_contract_code_raises(self):
        self._make("_TC-DUP-01", 5000)
        with self.assertRaises(frappe.exceptions.ValidationError):
            self._make("_TC-DUP-01", 6000)

    def tearDown(self):
        for c in frappe.get_all(
            "Service Contract",
            filters={"contract_code": ["like", "_TC-%"]},
            fields=["name"],
        ):
            frappe.delete_doc("Service Contract", c.name, force=True)
