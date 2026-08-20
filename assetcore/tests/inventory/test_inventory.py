"""Inventory stock-movement validator tests (Slide 27 + Slide 18).

Run: bench --site miyano run-tests --module assetcore.tests.inventory.test_inventory
"""
from __future__ import annotations

import unittest

import frappe

from assetcore.services.inventory import validate_stock_movement
from frappe.tests.utils import FrappeTestCase


class TestSparePartLowStockDrill(FrappeTestCase):
    """R7 §9.4.5 — list_spare_parts(low_stock=1) drill từ KPI store 'low_stock'.

    Round-trip: KPI _count_low_stock đếm STOCK ROW (part×warehouse) có
    qty_on_hand < min_stock_level. List low_stock=1 trả PARTS có ≥1 row như vậy
    (subset hợp lệ part-granularity). Mọi part trả về phải is_low_stock=True.

    Seed 1 part low-stock + 1 part đủ tồn để test KHÔNG vacuous (rule false-green).
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls._created = []
        # Warehouse dùng chung (tạo nếu chưa có).
        wh = frappe.db.get_value("AC Warehouse", {"warehouse_code": "WH-LOWTEST"}, "name")
        if not wh:
            w = frappe.get_doc({
                "doctype": "AC Warehouse", "warehouse_code": "WH-LOWTEST",
                "warehouse_name": "Kho test low-stock", "is_active": 1,
            }).insert(ignore_permissions=True)
            wh = w.name
            cls._created.append(("AC Warehouse", wh))
        cls.wh = wh
        # Part LOW (min=10, on_hand=2).
        cls.low = cls._mk_part("LOWTEST-LOW", min_level=10, qty=2)
        # Part OK (min=5, on_hand=50).
        cls.ok = cls._mk_part("LOWTEST-OK", min_level=5, qty=50)

    @classmethod
    def _mk_part(cls, code, min_level, qty):
        p = frappe.get_doc({
            "doctype": "AC Spare Part", "part_code": code, "part_name": code,
            "part_category": "Other", "unit_cost": 1, "stock_uom": "Cái",
            "min_stock_level": min_level, "is_active": 1,
        }).insert(ignore_permissions=True)
        cls._created.append(("AC Spare Part", p.name))
        s = frappe.get_doc({
            "doctype": "AC Spare Part Stock", "warehouse": cls.wh,
            "spare_part": p.name, "qty_on_hand": qty,
        }).insert(ignore_permissions=True)
        cls._created.append(("AC Spare Part Stock", s.name))
        frappe.db.commit()
        return p.name

    @classmethod
    def tearDownClass(cls):
        for dt, name in reversed(cls._created):
            try:
                frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
            except Exception:
                pass
        frappe.db.commit()

    def test_list_low_stock_only_returns_below_min_parts(self):
        from assetcore.api.inventory import list_spare_parts
        res = list_spare_parts(low_stock=1, page_size=500)
        payload = res.get("data") or res.get("message") or res
        items = payload.get("items", [])
        names = {p.get("name") for p in items}
        # Part LOW phải có; part OK KHÔNG được lọt; mọi part trả về is_low_stock=True.
        self.assertIn(self.low, names, "part low-stock không xuất hiện trong filter")
        self.assertNotIn(self.ok, names, "part đủ tồn KHÔNG được lọt filter low_stock=1")
        for p in items:
            self.assertTrue(p.get("is_low_stock"),
                            f"{p.get('part_code')} lọt filter nhưng is_low_stock=False")

    def test_low_stock_count_matches_distinct_low_parts(self):
        from assetcore.api.inventory import list_spare_parts
        distinct = frappe.db.sql(
            """SELECT COUNT(DISTINCT s.spare_part)
               FROM `tabAC Spare Part Stock` s
               JOIN `tabAC Spare Part` p ON p.name = s.spare_part
               WHERE p.is_active=1 AND COALESCE(p.min_stock_level,0) > 0
                 AND s.qty_on_hand < p.min_stock_level""")[0][0]
        res = list_spare_parts(low_stock=1, page_size=500)
        payload = res.get("data") or res.get("message") or res
        total = payload.get("pagination", {}).get("total", 0)
        self.assertGreaterEqual(int(distinct), 1, "fixture low-stock không được seed")
        self.assertEqual(total, int(distinct),
                         "tổng list low_stock=1 lệch số part distinct dưới định mức")


class TestIssueReceiverRequired(FrappeTestCase):
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


class TestReceiptPoValidationLazy(FrappeTestCase):
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
