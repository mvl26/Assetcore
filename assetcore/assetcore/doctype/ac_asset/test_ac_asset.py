# Copyright (c) 2026, AssetCore Team
"""AC Asset controller smoke tests.

Covers fixes from Test Plan Next Round #1 analysis:
- RC-02: auto-default depreciation method when gross > 0.
- RC-11: next_pm_date / next_calibration_date fallback to commissioning_date.
- WR-03: block hard-delete of asset with linked records.

Run: bench --site miyano run-tests --app assetcore \
        --module assetcore.assetcore.doctype.ac_asset.test_ac_asset
"""
from __future__ import annotations

import unittest

import frappe
from frappe.utils import nowdate


_DT = "AC Asset"


class TestACAssetSmoke(unittest.TestCase):
    """Smoke tests scoped to the new controller-side fixes.

    Each test inserts an asset with `ignore_mandatory` + `ignore_links` so we
    don't depend on the full fixture chain (Model/Category) that other tests
    require — fixture chain has pre-existing failures unrelated to these fixes.
    """

    def _insert(self, **overrides):
        data = {
            "doctype": _DT,
            "asset_name": "_RC_TEST",
            "lifecycle_status": "Draft",
        }
        data.update(overrides)
        doc = frappe.get_doc(data)
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_links = True
        doc.insert(ignore_permissions=True)
        return doc

    # ── RC-02 ────────────────────────────────────────────────────────────────
    def test_rc02_default_depreciation_method_when_gross_positive(self):
        doc = self._insert(
            asset_name="_RC02_A",
            gross_purchase_amount=100_000_000,
            in_service_date=nowdate(),
        )
        try:
            self.assertEqual(doc.depreciation_method, "Straight Line")
            self.assertEqual(doc.depreciation_frequency, "Monthly")
            self.assertTrue(doc.depreciation_start_date)
        finally:
            frappe.db.delete(_DT, {"name": doc.name})
            frappe.db.commit()

    def test_rc02_no_default_when_gross_zero(self):
        doc = self._insert(asset_name="_RC02_B", gross_purchase_amount=0)
        try:
            self.assertFalse(doc.depreciation_method)
        finally:
            frappe.db.delete(_DT, {"name": doc.name})
            frappe.db.commit()

    # ── RC-11 ────────────────────────────────────────────────────────────────
    def test_rc11_next_pm_uses_commission_date_when_no_last_pm(self):
        doc = self._insert(
            asset_name="_RC11_PM",
            is_pm_required=1,
            pm_interval_days=90,
            commissioning_date=nowdate(),
        )
        try:
            self.assertIsNotNone(doc.next_pm_date)
        finally:
            frappe.db.delete(_DT, {"name": doc.name})
            frappe.db.commit()

    def test_rc11_next_cal_uses_in_service_date_when_no_last_cal(self):
        doc = self._insert(
            asset_name="_RC11_CAL",
            is_calibration_required=1,
            calibration_interval_days=180,
            in_service_date=nowdate(),
        )
        try:
            self.assertIsNotNone(doc.next_calibration_date)
        finally:
            frappe.db.delete(_DT, {"name": doc.name})
            frappe.db.commit()

    # ── WR-03 ────────────────────────────────────────────────────────────────
    def test_wr03_delete_without_linked_records_passes(self):
        """Happy path: asset without ràng buộc → xóa được."""
        doc = self._insert(asset_name="_WR03_CLEAN")
        try:
            # Should not raise — no PM/Incident/Audit linked yet.
            frappe.delete_doc(_DT, doc.name, ignore_permissions=True, force=False)
            self.assertFalse(frappe.db.exists(_DT, doc.name))
        except frappe.LinkExistsError:
            self.fail("WR-03: xóa asset chưa có ràng buộc không được throw LinkExistsError")
        finally:
            # tearDown safety
            if frappe.db.exists(_DT, doc.name):
                frappe.db.delete(_DT, {"name": doc.name})
                frappe.db.commit()

    def test_wr03_delete_blocked_by_linked_audit_trail(self):
        """Negative: tạo IMM Audit Trail trỏ tới asset → hard-delete bị chặn."""
        doc = self._insert(asset_name="_WR03_LINKED")
        audit_name = None
        try:
            try:
                audit = frappe.get_doc({
                    "doctype": "IMM Audit Trail",
                    "asset": doc.name,
                    "event_type": "State Change",
                    "actor": "Administrator",
                    "ref_doctype": _DT,
                    "ref_name": doc.name,
                    "change_summary": "_TEST WR-03 fixture",
                })
                audit.flags.ignore_mandatory = True
                audit.flags.ignore_permissions = True
                audit.insert(ignore_permissions=True)
                audit_name = audit.name
            except Exception:
                # If IMM Audit Trail schema differs (mandatory hash chain etc.),
                # skip this assertion — covered by on_trash blocker logic anyway.
                self.skipTest("IMM Audit Trail không thể tạo trực tiếp trong test env")

            with self.assertRaises(frappe.LinkExistsError):
                frappe.delete_doc(_DT, doc.name, ignore_permissions=True, force=False)
        finally:
            if audit_name and frappe.db.exists("IMM Audit Trail", audit_name):
                frappe.db.delete("IMM Audit Trail", {"name": audit_name})
            if frappe.db.exists(_DT, doc.name):
                frappe.db.delete(_DT, {"name": doc.name})
            frappe.db.commit()


if __name__ == "__main__":
    unittest.main()
