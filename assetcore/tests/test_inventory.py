"""Inventory stock-movement validator tests (Slide 27 + Slide 18).

Run: bench --site miyano run-tests --module assetcore.tests.test_inventory
"""
from __future__ import annotations

import unittest

import frappe

from assetcore.services.inventory import validate_stock_movement


class TestIssueReceiverRequired(unittest.TestCase):
    """Slide 27: phiếu Xuất kho bắt buộc có Khoa/Phòng nhận."""

    def test_issue_without_receiver_rejected(self):
        doc = frappe._dict(
            movement_type="Issue",
            reference_type="Manual",
            reference_name="",
            notes="lý do xuất kho",
            receiver_department="",
        )
        with self.assertRaises(frappe.ValidationError):
            validate_stock_movement(doc)

    def test_issue_with_receiver_passes(self):
        doc = frappe._dict(
            movement_type="Issue",
            reference_type="Manual",
            reference_name="",
            notes="lý do xuất kho",
            receiver_department="AC-DEPT-TEST",
        )
        # No raise for the receiver rule (Manual notes provided).
        validate_stock_movement(doc)

    def test_receipt_without_receiver_ok(self):
        doc = frappe._dict(
            movement_type="Receipt",
            reference_type="Manual",
            reference_name="",
            notes="nhập kho",
            receiver_department="",
        )
        validate_stock_movement(doc)


class TestReceiptPoValidationLazy(unittest.TestCase):
    """Slide 18: Receipt referencing a PO calls procurement validator;
    ImportError/AttributeError must NOT crash (logs TODO instead)."""

    def test_receipt_with_po_does_not_crash(self):
        doc = frappe._dict(
            name="STK-TEST-001",
            movement_type="Receipt",
            reference_type="AC Purchase",
            reference_name="AC-PUR-DOESNOTEXIST",
            notes="",
            receiver_department="",
            items=[],
        )
        # Referenced PO doesn't exist, and imm03 validator may be absent —
        # validator must surface the missing-ref error OR skip gracefully,
        # never an unhandled ImportError/AttributeError.
        try:
            validate_stock_movement(doc)
        except frappe.ValidationError:
            pass  # acceptable: BR-INV-08 missing-ref throw
        except (ImportError, AttributeError) as e:  # pragma: no cover
            self.fail(f"Lazy import not handled: {e}")


if __name__ == "__main__":
    unittest.main()
