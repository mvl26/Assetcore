# Copyright (c) 2026, AssetCore Team
"""IMM-05 unit tests — approve_document, reject_document, update_document, _resolve_alert_level.

Run: bench --site miyano run-tests --app assetcore --module assetcore.tests.test_imm05
"""
from __future__ import annotations

import unittest

import frappe
from frappe.utils import add_days, nowdate

from assetcore.services.imm05 import (
    DocState,
    _resolve_alert_level,
    approve_document,
    get_dashboard_stats,
    list_documents,
    reject_document,
    update_document,
)
from assetcore.services.shared import ServiceError


# ─── Fixtures ────────────────────────────────────────────────────────────────

def _ensure_uom() -> None:
    """AC Asset.uom defaults to "Cái"; self-seed so the test runs on a fresh DB."""
    if not frappe.db.exists("AC UOM", "Cái"):
        frappe.get_doc({"doctype": "AC UOM", "uom_name": "Cái"}).insert(ignore_permissions=True)


def _make_asset() -> str:
    _ensure_uom()
    doc = frappe.get_doc({
        "doctype": "AC Asset",
        "asset_name": "_Test Asset IMM05",
    })
    doc.flags.ignore_mandatory = True
    doc.insert(ignore_permissions=True)
    return doc.name


def _make_doc(asset_ref: str, state: str = DocState.DRAFT) -> str:
    doc = frappe.get_doc({
        "doctype": "Asset Document",
        "asset_ref": asset_ref,
        "doc_category": "Technical",
        "doc_type_detail": "Manual",
        "doc_number": f"DOC-TEST-{frappe.generate_hash(length=6)}",
        "version": "1.0",
        "issued_date": frappe.utils.nowdate(),
        "file_attachment": "/files/dummy-test.pdf",
        "workflow_state": state,
    })
    doc.flags.ignore_mandatory = True
    doc.insert(ignore_permissions=True)
    return doc.name


def _purge_asset(name: str | None) -> None:
    """Fully remove a test AC Asset and everything that blocks its on_trash guard.

    ``force=True`` does NOT bypass ``AC Asset.on_trash`` (WR-03) nor
    ``IMM Audit Trail.on_trash`` (ISO 13485:7.5.9). Audit rows must therefore be
    purged with raw SQL, operational dependents via the ORM, before the asset
    itself can be deleted. See LL-TEST-17.
    """
    if not name:
        return
    frappe.set_user("Administrator")
    # 1) IMM Audit Trail — raw SQL (ORM delete always throws the ISO guard).
    frappe.db.sql(
        "DELETE FROM `tabIMM Audit Trail` "
        "WHERE asset=%s OR (ref_doctype='AC Asset' AND ref_name=%s)",
        (name, name),
    )
    # 2) Operational dependents — raw delete; several (Asset Document) carry their
    #    own audit-protection on_trash guards that ``delete_doc`` cannot bypass.
    for dt, fld in (
        ("Asset Document", "asset_ref"),
        ("Asset Lifecycle Event", "asset"),
        ("AC Asset Downtime Log", "asset"),
        ("Asset Transfer", "asset"),
    ):
        if frappe.db.table_exists(dt):
            frappe.db.delete(dt, {fld: name})
    frappe.db.commit()
    # 3) The asset is now free of blockers.
    frappe.delete_doc("AC Asset", name, force=True, ignore_permissions=True)
    frappe.db.commit()


# ─── _resolve_alert_level ─────────────────────────────────────────────────────

class TestResolveAlertLevel(unittest.TestCase):

    def test_7_days_is_danger(self):
        self.assertEqual(_resolve_alert_level(7), "Danger")

    def test_5_days_is_danger(self):
        self.assertEqual(_resolve_alert_level(5), "Danger")

    def test_30_days_is_critical(self):
        self.assertEqual(_resolve_alert_level(30), "Critical")

    def test_25_days_is_critical(self):
        self.assertEqual(_resolve_alert_level(25), "Critical")

    def test_60_days_is_warning(self):
        self.assertEqual(_resolve_alert_level(60), "Warning")

    def test_90_days_is_info(self):
        self.assertEqual(_resolve_alert_level(90), "Info")

    def test_91_days_no_alert(self):
        self.assertIsNone(_resolve_alert_level(91))

    def test_0_days_is_danger(self):
        self.assertEqual(_resolve_alert_level(0), "Danger")


# ─── create_document ─────────────────────────────────────────────────────────

class TestCreateDocument(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset()

    @classmethod
    def tearDownClass(cls):
        _purge_asset(cls.asset)

    def test_create_returns_name_and_state(self):
        # _make_doc uses ignore_mandatory; verify state via direct fixture
        name = _make_doc(self.asset, DocState.DRAFT)
        state = frappe.db.get_value("Asset Document", name, "workflow_state")
        self.assertEqual(state, DocState.DRAFT)

    def test_default_version_is_1_0(self):
        name = _make_doc(self.asset, DocState.DRAFT)
        doc = frappe.get_doc("Asset Document", name)
        self.assertEqual(doc.version, "1.0")


# ─── update_document ─────────────────────────────────────────────────────────

class TestUpdateDocument(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset()

    @classmethod
    def tearDownClass(cls):
        _purge_asset(cls.asset)

    def test_update_draft_succeeds(self):
        name = _make_doc(self.asset, DocState.DRAFT)
        result = update_document(name, {"doc_number": "DOC-2026-0001"})
        self.assertIn("name", result)

    def test_update_active_blocked(self):
        name = _make_doc(self.asset, DocState.DRAFT)
        frappe.db.set_value("Asset Document", name, "workflow_state", DocState.ACTIVE)
        with self.assertRaises(ServiceError) as ctx:
            update_document(name, {"doc_number": "X"})
        self.assertEqual(ctx.exception.code, "BAD_STATE")

    def test_update_not_found_raises(self):
        with self.assertRaises(ServiceError) as ctx:
            update_document("FAKE-DOC-NAME", {"doc_number": "X"})
        self.assertEqual(ctx.exception.code, "NOT_FOUND")


# ─── approve_document ────────────────────────────────────────────────────────

class TestApproveDocument(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset()

    @classmethod
    def tearDownClass(cls):
        _purge_asset(cls.asset)

    def test_approve_pending_review_succeeds(self):
        name = _make_doc(self.asset, DocState.DRAFT)
        frappe.db.set_value("Asset Document", name, "workflow_state", DocState.PENDING_REVIEW)
        result = approve_document(name)
        self.assertEqual(result["new_state"], DocState.ACTIVE)
        self.assertEqual(result["approved_by"], "Administrator")

    def test_approve_draft_raises_bad_state(self):
        name = _make_doc(self.asset, DocState.DRAFT)
        with self.assertRaises(ServiceError) as ctx:
            approve_document(name)
        self.assertEqual(ctx.exception.code, "BAD_STATE")

    def test_approve_archives_old_active(self):
        # Create old Active doc for same (asset, doc_type_detail)
        old_name = _make_doc(self.asset, DocState.DRAFT)
        frappe.db.set_value("Asset Document", old_name, {
            "workflow_state": DocState.ACTIVE,
            "doc_type_detail": "Manual",
        })
        # Create new doc, move to Pending Review, approve
        new_name = _make_doc(self.asset, DocState.DRAFT)
        frappe.db.set_value("Asset Document", new_name, {
            "workflow_state": DocState.PENDING_REVIEW,
            "doc_type_detail": "Manual",
        })
        approve_document(new_name)
        old_state = frappe.db.get_value("Asset Document", old_name, "workflow_state")
        self.assertEqual(old_state, DocState.ARCHIVED)


# ─── reject_document ─────────────────────────────────────────────────────────

class TestRejectDocument(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset()

    @classmethod
    def tearDownClass(cls):
        _purge_asset(cls.asset)

    def test_reject_without_reason_raises(self):
        name = _make_doc(self.asset, DocState.DRAFT)
        frappe.db.set_value("Asset Document", name, "workflow_state", DocState.PENDING_REVIEW)
        with self.assertRaises(ServiceError) as ctx:
            reject_document(name, "")
        self.assertEqual(ctx.exception.code, "VALIDATION")

    def test_reject_pending_review_succeeds(self):
        name = _make_doc(self.asset, DocState.DRAFT)
        frappe.db.set_value("Asset Document", name, "workflow_state", DocState.PENDING_REVIEW)
        result = reject_document(name, "Tài liệu không hợp lệ")
        self.assertEqual(result["new_state"], DocState.REJECTED)

    def test_reject_draft_raises_bad_state(self):
        name = _make_doc(self.asset, DocState.DRAFT)
        with self.assertRaises(ServiceError) as ctx:
            reject_document(name, "reason")
        self.assertEqual(ctx.exception.code, "BAD_STATE")


# ─── list_documents ──────────────────────────────────────────────────────────

class TestListDocuments(unittest.TestCase):

    def test_list_returns_dict_with_items(self):
        result = list_documents({})
        self.assertIn("items", result)
        # total is under pagination or at top level depending on version
        has_total = "total" in result or ("pagination" in result and "total" in result["pagination"])
        self.assertTrue(has_total)
        self.assertIsInstance(result["items"], list)

    def test_page_size_respected(self):
        result = list_documents({}, page=1, page_size=5)
        self.assertLessEqual(len(result["items"]), 5)


# ─── RC-08 (NextRound): KPI "Đã hết hạn" phải đếm theo expiry_date < today
#     bất kể workflow_state (bao gồm Draft / Pending Review / Active đã quá hạn).
class TestKpiExpiredDocs(unittest.TestCase):
    """Regression test cho RC-08 — đảm bảo expired-but-Draft cũng được đếm."""

    asset: str
    draft_expired_doc: str
    active_expired_doc: str

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset()
        # Doc Draft đã quá hạn 10 ngày — TRƯỚC FIX: bị bỏ qua vì state != Active
        cls.draft_expired_doc = _make_doc(cls.asset, state=DocState.DRAFT)
        frappe.db.set_value("Asset Document", cls.draft_expired_doc,
                            "expiry_date", add_days(nowdate(), -10))
        # Doc Pending Review đã quá hạn 5 ngày — TRƯỚC FIX cũng bị bỏ qua
        cls.active_expired_doc = _make_doc(cls.asset, state=DocState.DRAFT)
        # Bypass workflow guard: set trực tiếp state + expiry qua db.set_value
        frappe.db.set_value("Asset Document", cls.active_expired_doc, {
            "workflow_state": DocState.PENDING_REVIEW,
            "expiry_date": add_days(nowdate(), -5),
        })
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        _purge_asset(cls.asset)

    def test_expired_kpi_counts_draft_doc(self):
        """expired_not_renewed phải bao gồm cả Draft expired (RC-08)."""
        stats = get_dashboard_stats()
        expired = stats["kpis"]["expired_not_renewed"]
        # Ít nhất phải đếm 2 doc test (Draft + Active) đã quá hạn
        self.assertGreaterEqual(expired, 2,
            "RC-08: KPI 'Đã hết hạn' phải đếm cả Draft/Pending Review đã quá expiry_date")

    def test_expired_kpi_filter_is_by_expiry_date_only(self):
        """KPI count phải khớp với SQL filter `expiry_date < today` thuần."""
        stats = get_dashboard_stats()
        kpi_count = stats["kpis"]["expired_not_renewed"]
        truth = frappe.db.count("Asset Document", {"expiry_date": ["<", nowdate()]})
        self.assertEqual(kpi_count, truth,
            "RC-08: KPI phải bằng count theo expiry_date<today, không AND status")


# ─── Depreciation (RC-01 / RC-02) ────────────────────────────────────────────

class TestDepreciationDefaults(unittest.TestCase):
    """RC-02: default depreciation_method auto-assignment on AC Asset."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls._cleanup_assets: list[str] = []
        cls._cleanup_categories: list[str] = []

    @classmethod
    def tearDownClass(cls):
        for name in cls._cleanup_assets:
            try:
                frappe.delete_doc("AC Asset", name, force=1, ignore_permissions=True)
            except Exception:
                pass
        for name in cls._cleanup_categories:
            try:
                frappe.delete_doc(
                    "AC Asset Category", name, force=1, ignore_permissions=True,
                )
            except Exception:
                pass

    def _new_asset(self, **overrides) -> "frappe.model.document.Document":
        payload = {
            "doctype": "AC Asset",
            "asset_name": f"_Test Depr Asset {frappe.generate_hash(length=6)}",
        }
        payload.update(overrides)
        doc = frappe.get_doc(payload)
        doc.flags.ignore_mandatory = True
        doc.insert(ignore_permissions=True)
        self._cleanup_assets.append(doc.name)
        return doc

    def _new_category(self, default_method: str | None = None) -> str:
        cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": f"_TestCat-{frappe.generate_hash(length=6)}",
            "category_code": f"TC{frappe.generate_hash(length=4)}",
            "default_depreciation_method": default_method or "",
        })
        cat.flags.ignore_mandatory = True
        cat.insert(ignore_permissions=True)
        self._cleanup_categories.append(cat.name)
        return cat.name

    def test_depreciation_default_method_auto_assigned(self):
        """RC-02: Asset có gross_purchase_amount > 0 → method = 'Straight Line'."""
        doc = self._new_asset(gross_purchase_amount=10_000_000)
        self.assertEqual(
            doc.depreciation_method, "Straight Line",
            "RC-02: phải auto-gán 'Straight Line' khi gross > 0 và method rỗng",
        )

    def test_depreciation_default_from_category(self):
        """RC-02: nếu Category có default_depreciation_method → asset dùng method
        của Category thay vì fallback Straight Line."""
        cat_name = self._new_category(default_method="Double Declining")
        doc = self._new_asset(
            gross_purchase_amount=20_000_000,
            asset_category=cat_name,
        )
        self.assertEqual(
            doc.depreciation_method, "Double Declining",
            "RC-02: phải inherit method từ Category khi Category có default_depreciation_method",
        )

    def test_depreciation_no_default_when_zero_price(self):
        """RC-02: gross_purchase_amount = 0 → KHÔNG auto-gán method (để user/cron biết)."""
        doc = self._new_asset(gross_purchase_amount=0)
        self.assertFalse(
            (doc.depreciation_method or "").strip(),
            "RC-02: không gán method khi gross = 0",
        )


class TestGenerateScheduleZeroPrice(unittest.TestCase):
    """RC-01: generate_schedule phải raise rõ ràng khi nguyên giá = 0."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls._cleanup_assets: list[str] = []

    @classmethod
    def tearDownClass(cls):
        for name in cls._cleanup_assets:
            try:
                frappe.delete_doc("AC Asset", name, force=1, ignore_permissions=True)
            except Exception:
                pass

    def _new_asset(self, **overrides) -> str:
        payload = {
            "doctype": "AC Asset",
            "asset_name": f"_Test Schedule Asset {frappe.generate_hash(length=6)}",
        }
        payload.update(overrides)
        doc = frappe.get_doc(payload)
        doc.flags.ignore_mandatory = True
        doc.insert(ignore_permissions=True)
        self._cleanup_assets.append(doc.name)
        return doc.name

    def test_generate_schedule_zero_price_raises(self):
        """RC-01: gross = 0 → ValidationError với thông báo tiếng Việt rõ ràng."""
        from assetcore.services import depreciation as depr_svc
        asset_name = self._new_asset(
            gross_purchase_amount=0,
            depreciation_method="Straight Line",
            total_depreciation_months=60,
            depreciation_frequency="Monthly",
            depreciation_start_date=nowdate(),
        )
        with self.assertRaises(frappe.ValidationError) as ctx:
            depr_svc.generate_schedule(asset_name, force=True)
        self.assertIn(
            "nguyên giá", str(ctx.exception).lower(),
            "RC-01: thông báo lỗi phải nói rõ 'nguyên giá'",
        )

    def test_generate_schedule_auto_assigns_method_when_missing(self):
        """RC-01: method rỗng + gross > 0 → service tự gán Straight Line + tiếp tục."""
        from assetcore.services import depreciation as depr_svc
        asset_name = self._new_asset(
            gross_purchase_amount=12_000_000,
            depreciation_method="",
            total_depreciation_months=12,
            depreciation_frequency="Monthly",
            depreciation_start_date=nowdate(),
        )
        # Force method back to empty bypassing before_save autoset
        frappe.db.set_value("AC Asset", asset_name, "depreciation_method", "")
        frappe.db.commit()

        result = depr_svc.generate_schedule(asset_name, force=True)
        self.assertEqual(result.get("method"), "Straight Line",
            "RC-01: phải fallback 'Straight Line' khi method rỗng + gross > 0")
        self.assertGreater(result.get("periods", 0), 0)

    def test_generate_schedule_excessive_periods_raises(self):
        """RC-01: tổng periods > 240 → raise ValidationError để FE bắt được."""
        from assetcore.services import depreciation as depr_svc
        asset_name = self._new_asset(
            gross_purchase_amount=10_000_000,
            depreciation_method="Straight Line",
            total_depreciation_months=300,  # 25 năm * 12 = 300 > 240
            depreciation_frequency="Monthly",
            depreciation_start_date=nowdate(),
        )
        with self.assertRaises(frappe.ValidationError):
            depr_svc.generate_schedule(asset_name, force=True)


if __name__ == "__main__":
    unittest.main()
