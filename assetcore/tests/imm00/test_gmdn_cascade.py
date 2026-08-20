# Copyright (c) 2026, AssetCore Team
"""IMM-00 — P3 Hybrid GMDN cascade test suite (TDD per CLAUDE.md §17).

Run: bench --site miyano run-tests --module assetcore.tests.imm00.test_gmdn_cascade

Scope (docs/res/plans/2026-05-19-gmdn-code-sync-strategy.md §6 C2/C4/C5):
  - Controller sets gmdn_inherited flag correctly on Model create/update.
  - Category.gmdn_code change cascades ONLY to inherited Models + their Assets.
  - Override Models (gmdn_inherited=0) are NOT touched.
  - Each cascade propagation writes an IMM Audit Trail row.
  - Cascade is idempotent (re-running same value does not duplicate audit rows).
"""
import unittest

import frappe

from assetcore.tests._helpers._asset_cleanup import purge_asset
from frappe.tests.utils import FrappeTestCase


def _sweep_leaked_fixtures() -> None:
    """Dọn danh mục fixture còn sót của LƯỢT TRƯỚC (tự lành).

    Mọi danh mục ở đây mang cùng ``gmdn_code='47821'``, mà ``AC Asset Category``
    ép mã GMDN là DUY NHẤT. Một lượt chạy đứt giữa chừng để lại 1 danh mục là
    MỌI lượt sau đều ném "Mã GMDN đã được dùng" ở setUp ⇒ cả suite chết cứng.
    Sự cố có thật: 'GMDN-CAS-eb024b' rò ngày 2026-06-15 làm 9/9 test error tới
    tận 2026-08-14.
    """
    for cat in frappe.db.sql_list(
        "SELECT name FROM `tabAC Asset Category` WHERE category_code LIKE 'GMDN-CAS-%%'"
    ):
        for asset in frappe.db.sql_list(
            "SELECT name FROM `tabAC Asset` WHERE asset_category=%s", (cat,)
        ):
            purge_asset(asset)
        for model in frappe.db.sql_list(
            "SELECT name FROM `tabIMM Device Model` WHERE asset_category=%s", (cat,)
        ):
            frappe.delete_doc("IMM Device Model", model, force=True,
                              ignore_permissions=True, delete_permanently=True)
        frappe.delete_doc("AC Asset Category", cat, force=True,
                          ignore_permissions=True, delete_permanently=True)
    frappe.db.commit()


def setUpModule():
    frappe.set_user("Administrator")
    if not frappe.db.exists("AC UOM", "Cái"):
        frappe.get_doc({"doctype": "AC UOM", "uom_name": "Cái"}).insert(ignore_permissions=True)
        frappe.db.commit()
    _sweep_leaked_fixtures()


class TestGmdnCascade(FrappeTestCase):
    def setUp(self):
        suffix = frappe.generate_hash(length=6)
        self.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": f"GMDN Cascade Cat {suffix}",
            "category_code": f"GMDN-CAS-{suffix}",
            "gmdn_code": "47821",
            "is_active": 1,
        }).insert(ignore_permissions=True)

        # Model A — inherits gmdn_code from Category (no explicit gmdn_code).
        self.model_inh = frappe.get_doc({
            "doctype": "IMM Device Model",
            "naming_series": "IMM-MDL-.YYYY.-.####",
            "model_name": f"InhModel {suffix}",
            "manufacturer": f"Mfr {suffix}",
            "asset_category": self.cat.name,
            "medical_device_class": "Class II",
        }).insert(ignore_permissions=True)

        # Model B — explicit override gmdn_code different from Category.
        self.model_ovr = frappe.get_doc({
            "doctype": "IMM Device Model",
            "naming_series": "IMM-MDL-.YYYY.-.####",
            "model_name": f"OvrModel {suffix}",
            "manufacturer": f"Mfr {suffix}",
            "asset_category": self.cat.name,
            "medical_device_class": "Class II",
            "gmdn_code": "99999",
        }).insert(ignore_permissions=True)

        self.asset_inh = frappe.get_doc({
            "doctype": "AC Asset",
            "naming_series": "AC-ASSET-.YYYY.-.#####",
            "asset_name": f"InhAsset {suffix}",
            "asset_category": self.cat.name,
            "device_model": self.model_inh.name,
            "status": "Submitted",
            "lifecycle_status": "Draft",
        }).insert(ignore_permissions=True)

        self.asset_ovr = frappe.get_doc({
            "doctype": "AC Asset",
            "naming_series": "AC-ASSET-.YYYY.-.#####",
            "asset_name": f"OvrAsset {suffix}",
            "asset_category": self.cat.name,
            "device_model": self.model_ovr.name,
            "status": "Submitted",
            "lifecycle_status": "Draft",
        }).insert(ignore_permissions=True)
        frappe.db.commit()

    def tearDown(self):
        # AC Asset.on_trash blocks delete while Audit Trail / Lifecycle Events
        # exist, and force=True does NOT bypass a custom on_trash (LL-TEST-17).
        # The cascade tests create those rows, so purge them first or the
        # Category leaks and its gmdn_code collides on the next run.
        # Dùng SSoT purge_asset thay vì chép lại chuỗi dọn phụ thuộc: nó xử lý đủ
        # append-only (Audit Trail/Lifecycle Event) + dependent nghiệp vụ, quét lại
        # lần hai, và CHỐT bằng commit (thiếu commit thì lệnh xoá bị rollback).
        for asset in (self.asset_inh.name, self.asset_ovr.name):
            purge_asset(asset)
        for dt, nm in (
            ("IMM Device Model", self.model_inh.name),
            ("IMM Device Model", self.model_ovr.name),
            ("AC Asset Category", self.cat.name),
        ):
            if frappe.db.exists(dt, nm):
                frappe.delete_doc(dt, nm, force=True, ignore_permissions=True,
                                  delete_permanently=True)
        frappe.db.commit()

    # ── C2 — controller flag logic ──────────────────────────────────────
    def test_c2_inherited_model_flag_is_1(self):
        m = frappe.get_doc("IMM Device Model", self.model_inh.name)
        self.assertEqual(m.gmdn_inherited, 1)
        self.assertEqual(m.gmdn_code, "47821")  # inherited from Category

    def test_c2_override_model_flag_is_0(self):
        m = frappe.get_doc("IMM Device Model", self.model_ovr.name)
        self.assertEqual(m.gmdn_inherited, 0)
        self.assertEqual(m.gmdn_code, "99999")

    def test_c2_override_then_realign_sets_flag_back_to_1(self):
        m = frappe.get_doc("IMM Device Model", self.model_ovr.name)
        m.gmdn_code = "47821"  # back to Category value -> inherited again
        m.save(ignore_permissions=True)
        m.reload()
        self.assertEqual(m.gmdn_inherited, 1)

    def test_c2_numeric_gmdn_code_does_not_crash(self):
        """Regression: bulk import (openpyxl) yields gmdn_code as int for a
        numeric cell -> controller must not crash on `(int).strip()`."""
        suffix = frappe.generate_hash(length=6)
        m = frappe.get_doc({
            "doctype": "IMM Device Model",
            "naming_series": "IMM-MDL-.YYYY.-.####",
            "model_name": f"NumGmdnModel {suffix}",
            "manufacturer": f"Mfr {suffix}",
            "asset_category": self.cat.name,
            "medical_device_class": "Class II",
            "gmdn_code": 99999,  # int, as Excel import supplies it
        }).insert(ignore_permissions=True)
        self.addCleanup(
            frappe.delete_doc, "IMM Device Model", m.name, force=True, ignore_permissions=True
        )
        m.reload()
        self.assertEqual(m.gmdn_code, "99999")   # coerced to str
        self.assertEqual(m.gmdn_inherited, 0)    # differs from Category 47821

    # ── C4 — cascade behaviour ──────────────────────────────────────────
    def test_c4_cascade_updates_inherited_model_and_asset(self):
        cat = frappe.get_doc("AC Asset Category", self.cat.name)
        cat.gmdn_code = "55512"
        cat.save(ignore_permissions=True)
        frappe.db.commit()

        self.assertEqual(
            frappe.db.get_value("IMM Device Model", self.model_inh.name, "gmdn_code"),
            "55512",
        )
        self.assertEqual(
            frappe.db.get_value("AC Asset", self.asset_inh.name, "gmdn_code"),
            "55512",
        )

    def test_c4_cascade_skips_override_model_and_asset(self):
        cat = frappe.get_doc("AC Asset Category", self.cat.name)
        cat.gmdn_code = "55512"
        cat.save(ignore_permissions=True)
        frappe.db.commit()

        self.assertEqual(
            frappe.db.get_value("IMM Device Model", self.model_ovr.name, "gmdn_code"),
            "99999",
        )
        self.assertEqual(
            frappe.db.get_value("AC Asset", self.asset_ovr.name, "gmdn_code"),
            "99999",
        )

    def test_c4_cascade_writes_audit_row(self):
        before = frappe.db.count("IMM Audit Trail", {"asset": self.asset_inh.name})
        cat = frappe.get_doc("AC Asset Category", self.cat.name)
        cat.gmdn_code = "55512"
        cat.save(ignore_permissions=True)
        frappe.db.commit()
        after = frappe.db.count("IMM Audit Trail", {"asset": self.asset_inh.name})
        self.assertGreater(after, before)

    def test_c4_cascade_idempotent(self):
        cat = frappe.get_doc("AC Asset Category", self.cat.name)
        cat.gmdn_code = "55512"
        cat.save(ignore_permissions=True)
        frappe.db.commit()
        count_after_1 = frappe.db.count("IMM Audit Trail", {"asset": self.asset_inh.name})

        # Re-save with SAME value -> has_value_changed False -> no new cascade/audit.
        cat.reload()
        cat.save(ignore_permissions=True)
        frappe.db.commit()
        count_after_2 = frappe.db.count("IMM Audit Trail", {"asset": self.asset_inh.name})
        self.assertEqual(count_after_1, count_after_2)

    def test_c4_no_cascade_when_gmdn_unchanged(self):
        before = frappe.db.count("IMM Audit Trail", {"asset": self.asset_inh.name})
        cat = frappe.get_doc("AC Asset Category", self.cat.name)
        cat.description = "touch unrelated field only"
        cat.save(ignore_permissions=True)
        frappe.db.commit()
        after = frappe.db.count("IMM Audit Trail", {"asset": self.asset_inh.name})
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
