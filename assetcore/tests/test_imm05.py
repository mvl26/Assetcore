# Copyright (c) 2026, AssetCore Team
"""IMM-05 unit tests — approve_document, reject_document, update_document, _resolve_alert_level.

Run: bench --site miyano run-tests --app assetcore --module assetcore.tests.test_imm05
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.utils import add_days, nowdate

from assetcore.services.imm05 import (
    DocState,
    _DOC_VALID_TRANSITIONS,
    _resolve_alert_level,
    approve_document,
    get_dashboard_stats,
    get_document,
    list_documents,
    reject_document,
    update_document,
)
from assetcore.services.shared import ServiceError
from assetcore.tests._asset_cleanup import purge_asset


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
        # Notification contract vòng 5: VR-06 raise qua nthrow(MSG.IMM05_REJECT_REASON_REQUIRED)
        # http_status 422 → ErrorCode bucket BUSINESS_RULE (warning UX). message_code chốt contract.
        self.assertEqual(ctx.exception.code, "BUSINESS_RULE")
        self.assertEqual(ctx.exception.message_code, "IMM05-REJECT-REASON-REQUIRED")

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


# ─── BR-05-16 / INV-EXP-1: SoT predicate "Đã hết hạn" (Self-Correction Vòng 19)
#     Một predicate DUY NHẤT `expired_filter()` dùng CHUNG bởi KPI count
#     (get_dashboard_stats) + drill (list_documents marker expiry_status='expired').
#     Counterexample bug cũ: KPI đếm mọi doc quá hạn (kể cả Archived/Rejected) còn
#     drill lọc workflow_state='Expired' (dead-state) → list rỗng = count-vs-drill
#     divergence che giấu hồ sơ quá hạn còn hiệu lực (NĐ98 Điều 41).
class TestExpiredSoT(unittest.TestCase):
    """BR-05-16 / INV-EXP-1 — SoT 'Đã hết hạn' = expiry_date IS NOT NULL
    AND expiry_date < today AND workflow_state NOT IN (Archived, Rejected),
    dùng Y HỆT cho KPI count VÀ drill list."""

    asset: str

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset()

    @classmethod
    def tearDownClass(cls):
        _purge_asset(cls.asset)

    def _mk(self, state: str, *, expiry) -> str:
        """Seed an Asset Document at `state` with given expiry (date string or None).

        Bypass workflow guards via db.set_value so we can place a doc in any
        terminal/non-terminal state deterministically for predicate testing.
        """
        name = _make_doc(self.asset, state=DocState.DRAFT)
        patch: dict = {"workflow_state": state}
        if expiry is not None:
            patch["expiry_date"] = expiry
        frappe.db.set_value("Asset Document", name, patch)
        frappe.db.commit()
        return name

    def _drill_names(self) -> set[str]:
        """Drill list applying the SAME SoT via the public marker contract."""
        res = list_documents({"expiry_status": "expired"}, page=1, page_size=10000)
        return {r["name"] for r in res["items"]}

    # ── TC-EXP-01: BUG CHÍNH (RED-prove on old code) ────────────────────────────
    def test_active_overdue_counted_and_in_drill(self):
        """Active doc expiry=today-5 (cron set is_expired, KHÔNG đổi state):
        KPI 'expired_not_renewed' đếm doc này (>=1) VÀ drill list chứa đúng doc.
        Trên code cũ drill {workflow_state:'Expired'} = 0 dòng ⇒ FAIL."""
        name = self._mk(DocState.ACTIVE, expiry=add_days(nowdate(), -5))
        frappe.db.set_value("Asset Document", name, "is_expired", 1)
        frappe.db.commit()
        stats = get_dashboard_stats()
        self.assertGreaterEqual(stats["kpis"]["expired_not_renewed"], 1)
        self.assertIn(name, self._drill_names(),
            "Active doc quá hạn PHẢI hiện trong drill (NĐ98 Điều 41)")

    # ── TC-EXP-02: tightening — Archived/Rejected quá hạn KHÔNG đếm ──────────────
    def test_archived_overdue_excluded(self):
        name = self._mk(DocState.ARCHIVED, expiry=add_days(nowdate(), -10))
        self.assertNotIn(name, self._drill_names(),
            "Archived quá hạn KHÔNG phải compliance-gap còn sống → loại")

    def test_rejected_overdue_excluded(self):
        name = self._mk(DocState.REJECTED, expiry=add_days(nowdate(), -10))
        self.assertNotIn(name, self._drill_names(),
            "Rejected quá hạn (đã thu hồi) → loại khỏi 'Đã hết hạn'")

    # ── TC-EXP-03: biên ─────────────────────────────────────────────────────────
    def test_expiry_today_not_expired(self):
        """expiry_date = today (chưa < today) → KHÔNG expired."""
        name = self._mk(DocState.ACTIVE, expiry=nowdate())
        self.assertNotIn(name, self._drill_names())

    def test_expiry_yesterday_is_expired(self):
        name = self._mk(DocState.ACTIVE, expiry=add_days(nowdate(), -1))
        self.assertIn(name, self._drill_names())

    def test_expiry_null_not_expired_no_crash(self):
        """expiry_date NULL → KHÔNG expired, không crash."""
        name = self._mk(DocState.ACTIVE, expiry=None)
        frappe.db.set_value("Asset Document", name, "expiry_date", None)
        frappe.db.commit()
        self.assertNotIn(name, self._drill_names())

    # ── TC-EXP-04: đối-soát SoT (INV-EXP-1) — count == drill len, immune state ──
    def test_count_equals_drill_mixed_set(self):
        """Tập hỗn hợp → expired_not_renewed (count) == số dòng drill list."""
        self._mk(DocState.ACTIVE, expiry=add_days(nowdate(), -3))
        self._mk(DocState.DRAFT, expiry=add_days(nowdate(), -7))
        self._mk(DocState.PENDING_REVIEW, expiry=add_days(nowdate(), -2))
        self._mk(DocState.ARCHIVED, expiry=add_days(nowdate(), -8))   # excluded
        self._mk(DocState.REJECTED, expiry=add_days(nowdate(), -8))   # excluded
        self._mk(DocState.ACTIVE, expiry=add_days(nowdate(), 30))     # not expired
        stats = get_dashboard_stats()
        res = list_documents({"expiry_status": "expired"}, page=1, page_size=10000)
        self.assertEqual(
            stats["kpis"]["expired_not_renewed"], len(res["items"]),
            "INV-EXP-1: count phải == len(drill items) cho mọi tập dữ liệu (chênh=0)")

    # ── TC-EXP-05: no-regression — predicate helper trả filter chuẩn ────────────
    def test_expired_filter_shape(self):
        """SoT = list-of-conditions với NULL-guard tường minh (đồng nhất db.count
        và get_all). `expiry_date < today` một mình KHÔNG đủ: get_all bọc ifnull()
        nên hàng NULL khớp '<' → count != drill (đã chứng minh)."""
        from assetcore.services.imm05 import expired_filter
        f = expired_filter(today="2026-06-01")
        self.assertEqual(f, [
            ["expiry_date", "is", "set"],
            ["expiry_date", "<", "2026-06-01"],
            ["workflow_state", "not in", [DocState.ARCHIVED, DocState.REJECTED]],
        ])

    def test_other_kpis_unchanged_by_predicate(self):
        """total_active / expiring_90d / assets_missing_docs vẫn có (predicate
        chỉ đổi nguồn của expired_not_renewed, không đụng KPI khác)."""
        stats = get_dashboard_stats()
        for key in ("total_active", "expiring_90d",
                    "expired_not_renewed", "assets_missing_docs"):
            self.assertIn(key, stats["kpis"])


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


# ─── Executor invariants (BR-05-11..14 / INV-DEP-1..4) ────────────────────────

class TestRunDueDepreciationInvariants(unittest.TestCase):
    """Vòng 2 — Executor `run_due_depreciation` PHẢI sàn book value tại
    residual_value (KHÔNG sàn 0) và chặn trần lũy kế tại depreciable_base.

    INV-DEP-1: current_book_value >= residual_value (mọi thời điểm).
    INV-DEP-2: accumulated_depreciation <= gross - residual.
    INV-DEP-3: book value header == remaining_value dòng schedule cuối (chênh ≤ 0.01).
    INV-DEP-4: chạy lần 2 (hết Pending tới hạn) → header không đổi, executed_rows=0.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls._cleanup_assets: list[str] = []

    @classmethod
    def tearDownClass(cls):
        # purge_asset clears audit/lifecycle/dependents that WR-03 on_trash would
        # otherwise block — a plain delete_doc silently fails and leaks the asset.
        for name in cls._cleanup_assets:
            try:
                purge_asset(name)
            except Exception:
                pass
        frappe.db.commit()

    def _new_asset(self, **overrides) -> str:
        payload = {
            "doctype": "AC Asset",
            "asset_name": f"_Test ExecDepr {frappe.generate_hash(length=6)}",
        }
        payload.update(overrides)
        doc = frappe.get_doc(payload)
        doc.flags.ignore_mandatory = True
        doc.insert(ignore_permissions=True)
        self._cleanup_assets.append(doc.name)
        return doc.name

    def _full_run_asset(self, gross: float, residual: float, months: int = 12) -> str:
        """Asset với start_date đủ xa trong quá khứ → mọi kỳ đến hạn, chạy 1 lần
        Executor sẽ thực thi toàn bộ lịch (kỳ cuối Pending → Executed)."""
        from assetcore.services import depreciation as depr_svc
        # start cách đây nhiều năm để mọi scheduled_date <= today
        start = add_days(nowdate(), -(months + 2) * 31)
        asset_name = self._new_asset(
            gross_purchase_amount=gross,
            residual_value=residual,
            depreciation_method="Straight Line",
            total_depreciation_months=months,
            depreciation_frequency="Monthly",
            depreciation_start_date=start,
        )
        # Đảm bảo method không bị before_save reset về rỗng
        frappe.db.set_value("AC Asset", asset_name, {
            "depreciation_method": "Straight Line",
            "residual_value": residual,
        })
        frappe.db.commit()
        depr_svc.generate_schedule(asset_name, force=True)
        return asset_name

    def _asset_vals(self, name: str) -> dict:
        return frappe.db.get_value(
            "AC Asset", name,
            ["gross_purchase_amount", "residual_value",
             "accumulated_depreciation", "current_book_value"],
            as_dict=True,
        )

    def test_book_value_floors_at_residual_not_zero(self):
        """INV-DEP-1: sau khi thực thi kỳ cuối, book == residual (≠ 0 khi residual>0)."""
        from assetcore.services import depreciation as depr_svc
        gross, residual = 12_000_000.0, 2_000_000.0
        name = self._full_run_asset(gross, residual, months=12)
        depr_svc.run_due_depreciation(asset=name)
        v = self._asset_vals(name)
        self.assertAlmostEqual(
            float(v.current_book_value), residual, delta=0.01,
            msg="INV-DEP-1: book value kỳ cuối phải == residual, KHÔNG xuống 0",
        )
        self.assertGreaterEqual(
            float(v.current_book_value), residual - 0.01,
            "INV-DEP-1: book value không bao giờ < residual_value",
        )

    def test_accumulated_never_exceeds_depreciable_base(self):
        """INV-DEP-2: lũy kế <= gross - residual kể cả khi chạy gộp nhiều kỳ."""
        from assetcore.services import depreciation as depr_svc
        gross, residual = 10_000_000.0, 1_500_000.0
        name = self._full_run_asset(gross, residual, months=7)  # 7 kỳ → rounding kỳ cuối
        depr_svc.run_due_depreciation(asset=name)
        v = self._asset_vals(name)
        base = gross - residual
        self.assertLessEqual(
            float(v.accumulated_depreciation), base + 0.01,
            "INV-DEP-2: accumulated_depreciation không được vượt depreciable_base",
        )

    def test_header_matches_last_schedule_row(self):
        """INV-DEP-3: book value header == remaining_value dòng schedule cuối."""
        from assetcore.services import depreciation as depr_svc
        gross, residual = 9_000_000.0, 1_000_000.0
        name = self._full_run_asset(gross, residual, months=10)
        depr_svc.run_due_depreciation(asset=name)
        v = self._asset_vals(name)
        last_remaining = frappe.db.sql(
            """SELECT remaining_value FROM `tabAC Asset Depreciation Schedule`
               WHERE parent=%s ORDER BY period_number DESC LIMIT 1""",
            name,
        )[0][0]
        self.assertAlmostEqual(
            float(v.current_book_value), float(last_remaining), delta=0.01,
            msg="INV-DEP-3: header book value phải khớp dòng schedule cuối (Planner)",
        )

    def test_idempotent_second_run_no_change(self):
        """INV-DEP-4: chạy lần 2 (hết Pending tới hạn) → header không đổi, rows=0."""
        from assetcore.services import depreciation as depr_svc
        gross, residual = 8_000_000.0, 800_000.0
        name = self._full_run_asset(gross, residual, months=6)
        depr_svc.run_due_depreciation(asset=name)
        before = self._asset_vals(name)
        res2 = depr_svc.run_due_depreciation(asset=name)
        after = self._asset_vals(name)
        self.assertEqual(res2.get("executed_rows"), 0,
            "INV-DEP-4: lần 2 không còn dòng Pending tới hạn → executed_rows=0")
        self.assertAlmostEqual(float(before.accumulated_depreciation),
                               float(after.accumulated_depreciation), delta=0.01,
                               msg="INV-DEP-4: accumulated không đổi khi chạy lại")
        self.assertAlmostEqual(float(before.current_book_value),
                               float(after.current_book_value), delta=0.01,
                               msg="INV-DEP-4: book value không đổi khi chạy lại")

    def test_zero_residual_still_floors_at_zero(self):
        """Regression: residual=0 → book value vẫn về 0 đúng như cũ (không hồi quy)."""
        from assetcore.services import depreciation as depr_svc
        gross, residual = 6_000_000.0, 0.0
        name = self._full_run_asset(gross, residual, months=6)
        depr_svc.run_due_depreciation(asset=name)
        v = self._asset_vals(name)
        self.assertAlmostEqual(float(v.current_book_value), 0.0, delta=0.01,
            msg="residual=0 → book value cuối == 0 (giữ hành vi cũ)")

    def test_lifecycle_event_notes_uses_capped_delta(self):
        """Kỳ cuối bị cap (book về residual) → lifecycle event 'depreciated' notes
        ghi delta THỰC-TRỪ (capped), KHÔNG ghi inc thô vượt trần.

        Lũy kế tổng phải == gross - residual; tổng các delta ghi trong notes phải
        khớp tổng đó (không double-count phần đã chặn ở kỳ cuối)."""
        from assetcore.services import depreciation as depr_svc
        # residual lớn để kỳ cuối chắc chắn bị cap (straight-line chia đều sẽ vượt
        # depreciable_base ở kỳ cuối nếu không sàn tại residual).
        gross, residual = 10_000_000.0, 2_500_000.0
        name = self._full_run_asset(gross, residual, months=4)
        depr_svc.run_due_depreciation(asset=name)

        events = frappe.get_all(
            "Asset Lifecycle Event",
            filters={"asset": name, "event_type": "depreciated"},
            fields=["notes"],
        )
        # Lifecycle event 'depreciated' được ghi best-effort trong executor
        # (bọc try/except — không chặn cập nhật asset nếu audit chain lỗi).
        # Khi CÓ event, notes PHẢI ghi delta capped; nếu vắng (best-effort skip)
        # thì invariant này không áp dụng — book value/lũy kế đã được các test
        # INV-DEP-1/2/3 ở trên kiểm độc lập.
        if not events:
            self.skipTest("không có lifecycle event 'depreciated' (best-effort) — bỏ qua")
        import re
        total_booked = 0.0
        for ev in events:
            notes = ev.get("notes") or ""
            m = re.search(r"Depreciated\s+([\d,]+)", notes)
            self.assertIsNotNone(m, f"notes phải có 'Depreciated <số>': {notes!r}")
            total_booked += float(m.group(1).replace(",", ""))
        base = gross - residual
        # Tổng delta ghi trong notes == depreciable_base (capped) — KHÔNG vượt.
        self.assertLessEqual(
            total_booked, base + 1.0,
            "notes tổng delta không được vượt depreciable_base (kỳ cuối phải capped)",
        )
        self.assertAlmostEqual(
            total_booked, base, delta=1.0,
            msg="tổng delta ghi trong notes phải == gross - residual (đầy đủ, không thiếu)",
        )


class TestFullyDepreciatedReadPath(unittest.TestCase):
    """BR-05-15 / INV-DEP-5: card count == drill rows for "Hết khấu hao".

    `get_depreciation_stats().fully_depreciated` (the KPI count) and
    `list_assets_depreciation(depreciation_filter='fully_depreciated')` (the
    drill list) MUST resolve to the same set via the single SoT predicate
    `is_fully_depreciated`. These integration tests seed a mix of assets —
    some fully-depreciated, some still depreciating, some unconfigured — and
    assert the two read-paths agree, the filter is exact, it ANDs with other
    filters, and the unfiltered stats keys are unchanged.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        _ensure_uom()
        cls._assets: list[str] = []
        cls._cat: str = cls._make_category()
        # gross=100tr, residual=10tr; fully-dep ⇔ book<=10tr+1.
        # 3 fully-depreciated (book at/just-above/within tolerance of residual)
        cls.full_1 = cls._make("FULL1", book=10_000_000.0)
        cls.full_2 = cls._make("FULL2", book=10_000_001.0)   # boundary +1
        cls.full_3 = cls._make("FULL3", book=9_500_000.0, category=cls._cat)
        # 2 still depreciating (book well above residual)
        cls.part_1 = cls._make("PART1", book=60_000_000.0)
        cls.part_2 = cls._make("PART2", book=10_000_002.0, category=cls._cat)  # +2 ⇒ NOT
        # 1 unconfigured (no method) but book<=residual — must NOT count
        cls.unconf = cls._make("UNCONF", book=0.0, method="", months=0)

    @classmethod
    def tearDownClass(cls):
        for a in cls._assets:
            try:
                purge_asset(a)
            except Exception:
                pass
        if cls._cat:
            try:
                frappe.delete_doc("AC Asset Category", cls._cat,
                                  force=1, ignore_permissions=True)
            except Exception:
                pass
        frappe.db.commit()

    @classmethod
    def _make_category(cls) -> str:
        cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": f"_TestDeprCat-{frappe.generate_hash(length=6)}",
            "category_code": f"TD{frappe.generate_hash(length=4)}",
        })
        cat.flags.ignore_mandatory = True
        cat.insert(ignore_permissions=True)
        return cat.name

    @classmethod
    def _make(cls, suffix: str, *, book: float, gross: float = 100_000_000.0,
              residual: float = 10_000_000.0, method: str = "Straight Line",
              months: int = 12, category: str | None = None) -> str:
        accumulated = max(gross - book, 0.0)
        payload = {
            "doctype": "AC Asset",
            # NON-reserved asset_name (KHÔNG prefix '_'): data-hygiene SSoT ẩn '_…'
            # khỏi list_assets_depreciation/get_depreciation_stats; read-path fixture
            # cần XUẤT HIỆN trong drill ⇒ tên thường.
            "asset_name": f"ZZTest DeprRead {suffix} {frappe.generate_hash(length=4)}",
            "gross_purchase_amount": gross,
            "residual_value": residual,
            "depreciation_method": method,
            "total_depreciation_months": months,
            "depreciation_frequency": "Monthly",
            "accumulated_depreciation": accumulated,
            "current_book_value": book,
            "lifecycle_status": "Active",
        }
        if category:
            payload["asset_category"] = category
        doc = frappe.get_doc(payload)
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_links = True
        prev = frappe.flags.in_install
        frappe.flags.in_install = "frappe"
        try:
            doc.insert(ignore_permissions=True)
        finally:
            frappe.flags.in_install = prev
        # Asset.before_save may re-derive method/book — force our test values back.
        frappe.db.set_value("AC Asset", doc.name, {
            "depreciation_method": method,
            "total_depreciation_months": months,
            "accumulated_depreciation": accumulated,
            "current_book_value": book,
        }, update_modified=False)
        frappe.db.commit()
        cls._assets.append(doc.name)
        return doc.name

    def _drill_names(self, **extra) -> set[str]:
        from assetcore.api.imm00 import list_assets_depreciation
        res = list_assets_depreciation(
            page=1, page_size=10000,
            depreciation_filter="fully_depreciated", **extra,
        )
        items = res["data"]["items"]
        return {a["name"] for a in items}, res["data"]["pagination"]

    # ── INVARIANT: card count == drill rows ─────────────────────────────────────

    def test_count_equals_drill_rows(self):
        """INV-DEP-5: stats.fully_depreciated == len(drill items) (de-dup name)."""
        from assetcore.api.imm00 import get_depreciation_stats
        stats = get_depreciation_stats()["data"]
        names, pagination = self._drill_names()
        # Our 3 seeded fully-dep assets are a SUBSET of the live total; both
        # read-paths see the same predicate so they must agree on the live set.
        self.assertEqual(
            stats["fully_depreciated"], len(names),
            "card count must equal de-duped drill rows (INV-DEP-5)",
        )
        # Our 3 seeded full assets present; the 3 non-full ones absent.
        self.assertIn(self.full_1, names)
        self.assertIn(self.full_2, names)
        self.assertIn(self.full_3, names)
        self.assertNotIn(self.part_1, names)
        self.assertNotIn(self.part_2, names)
        self.assertNotIn(self.unconf, names)

    def test_drill_pagination_total_reflects_filtered_set(self):
        """pagination.total == number of SoT-passing rows, NOT raw db.count."""
        from assetcore.api.imm00 import get_depreciation_stats
        names, pagination = self._drill_names()
        self.assertEqual(
            pagination["total"], len(names),
            "pagination.total must equal filtered item count, not raw table count",
        )
        stats = get_depreciation_stats()["data"]
        self.assertEqual(pagination["total"], stats["fully_depreciated"])

    def test_drill_items_all_satisfy_predicate(self):
        """Every drill item passes is_fully_depreciated; no in-progress leaks."""
        from assetcore.api.imm00 import list_assets_depreciation
        from assetcore.services import depreciation as depr_svc
        res = list_assets_depreciation(
            page=1, page_size=10000, depreciation_filter="fully_depreciated",
        )
        for a in res["data"]["items"]:
            self.assertTrue(
                depr_svc.is_fully_depreciated(a),
                f"drill leaked non-fully-depreciated asset {a['name']}",
            )

    # ── AND with other filters (no clobber) ─────────────────────────────────────

    def test_depreciation_filter_ands_with_category(self):
        """depreciation_filter ∩ category_filter — intersection, not clobber."""
        names, _ = self._drill_names(category_filter=self._cat)
        # Only full_3 is BOTH fully-depreciated AND in cls._cat.
        # (part_2 is in the category but NOT fully-depreciated.)
        self.assertIn(self.full_3, names)
        self.assertNotIn(self.full_1, names)   # full but different category
        self.assertNotIn(self.part_2, names)   # in category but not full

    def test_depreciation_filter_ands_with_method(self):
        """depreciation_filter ∩ method_filter."""
        names, _ = self._drill_names(method_filter="Straight Line")
        # All seeded full assets use Straight Line → present.
        self.assertIn(self.full_1, names)
        self.assertIn(self.full_3, names)
        # Sanity: a non-matching method yields none of our SL fulls.
        names_dd, _ = self._drill_names(method_filter="Double Declining")
        self.assertNotIn(self.full_1, names_dd)

    # ── REGRESSION: other stats keys unchanged ──────────────────────────────────

    def test_other_stats_keys_present_and_typed(self):
        """The refactor must not alter unrelated stats keys (BR regression)."""
        from assetcore.api.imm00 import get_depreciation_stats
        stats = get_depreciation_stats()["data"]
        for key in ("total_gross", "total_accumulated", "total_book_value",
                    "configured_count", "unconfigured_count", "overall_pct",
                    "by_method", "by_category", "total_assets"):
            self.assertIn(key, stats, f"stats key '{key}' missing after refactor")
        self.assertIsInstance(stats["by_method"], list)
        self.assertIsInstance(stats["by_category"], list)

    def test_unfiltered_list_unchanged_backward_compat(self):
        """No depreciation_filter ⇒ list still paginates the full table
        (param is optional; old callers unaffected)."""
        from assetcore.api.imm00 import list_assets_depreciation
        res = list_assets_depreciation(page=1, page_size=5)
        self.assertIn("items", res["data"])
        self.assertIn("pagination", res["data"])
        # Unfiltered total >= our 6 seeded assets.
        self.assertGreaterEqual(res["data"]["pagination"]["total"], 6)


# ─── Server-driven CTA: get_document allowed_transitions + can_approve ────────
#     GATE-8 / LL-FE-51 — màn Chi tiết tài liệu (get_document) emit tập
#     allowed_transitions (SoT = workflow 'IMM-05 Document Workflow') + cờ
#     can_approve (rbac.can('doc.approve')) → FE render nút CTA theo SERVER, KHÔNG
#     hardcode workflow_state===. Mirror imm08._PM_VALID_TRANSITIONS / imm12.
class TestGetDocumentAllowedTransitions(unittest.TestCase):
    """(1) get_document(name) CHỨA key allowed_transitions == _DOC_VALID_TRANSITIONS
    map cho MỖI workflow_state (Draft/Pending Review/Active/Rejected/Archived).
    Archived (terminal) → []."""

    asset: str

    @classmethod
    def setUpClass(cls):
        cls.asset = _make_asset()
        cls.names: dict[str, str] = {}
        for state in (
            DocState.DRAFT, DocState.PENDING_REVIEW, DocState.ACTIVE,
            DocState.REJECTED, DocState.ARCHIVED,
        ):
            # Insert as Draft then flip via set_value — bypass Frappe workflow-engine
            # transition validation (Draft→X không phải transition hợp lệ khi insert).
            name = _make_doc(cls.asset)
            if state != DocState.DRAFT:
                frappe.db.set_value(
                    "Asset Document", name, "workflow_state", state,
                    update_modified=False,
                )
            cls.names[state] = name
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        purge_asset(cls.asset)
        frappe.db.commit()

    def test_get_document_emits_allowed_transitions_per_state(self):
        for state, name in self.names.items():
            data = get_document(name)
            self.assertIn(
                "allowed_transitions", data,
                "get_document PHẢI emit key 'allowed_transitions' (server-driven CTA).")
            self.assertEqual(
                data["allowed_transitions"], _DOC_VALID_TRANSITIONS[state],
                f"allowed_transitions '{state}' PHẢI == map[{state}].")
        # Archived (terminal) → [] rỗng, tường minh.
        self.assertEqual(
            get_document(self.names[DocState.ARCHIVED])["allowed_transitions"], [],
            "Archived (terminal) → [] rỗng (KHÔNG transition ra).")

    def test_get_document_allowed_transitions_matches_workflow_fixture(self):
        """INVARIANT chống drift: map BE == next_states của fixture
        'IMM-05 Document Workflow'. Ai thêm/sửa transition mà quên map → test đỏ."""
        wf_path = Path(frappe.get_app_path("assetcore")) / "fixtures" / "workflow.json"
        fixtures = json.loads(wf_path.read_text(encoding="utf-8"))
        wf = next(
            (w for w in fixtures if w.get("name") == "IMM-05 Document Workflow"), None,
        )
        self.assertIsNotNone(wf, "fixture 'IMM-05 Document Workflow' KHÔNG tồn tại.")
        # Codomain gồm MỌI state (kể cả terminal không có transition ra → set() rỗng).
        codomain = {s["state"]: set() for s in wf["states"]}
        for t in wf["transitions"]:
            codomain.setdefault(t["state"], set()).add(t["next_state"])
        self.assertEqual(
            set(_DOC_VALID_TRANSITIONS.keys()), set(codomain.keys()),
            "Key-set map BE PHẢI == states[] workflow fixture (thừa/thiếu state → drift).")
        for state, wf_nexts in codomain.items():
            self.assertEqual(
                set(_DOC_VALID_TRANSITIONS[state]), wf_nexts,
                f"DRIFT '{state}': map {sorted(_DOC_VALID_TRANSITIONS[state])} "
                f"≠ workflow {sorted(wf_nexts)}.")


class TestGetDocumentCanApprove(unittest.TestCase):
    """(3) can_approve:int 0/1 = int(rbac.can('doc.approve')) — phản ánh capability
    thật của user (stub rbac.can để deterministic, KHÔNG so role-name)."""

    asset: str
    name: str

    @classmethod
    def setUpClass(cls):
        cls.asset = _make_asset()
        cls.name = _make_doc(cls.asset)  # Draft
        frappe.db.set_value(
            "Asset Document", cls.name, "workflow_state", DocState.PENDING_REVIEW,
            update_modified=False,
        )
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        purge_asset(cls.asset)
        frappe.db.commit()

    def test_can_approve_1_when_capable(self):
        with patch("assetcore.services.imm05.rbac.can", return_value=True):
            data = get_document(self.name)
        self.assertEqual(
            data.get("can_approve"), 1,
            "user CÓ capability doc.approve → can_approve == 1.")

    def test_can_approve_0_when_not_capable(self):
        with patch("assetcore.services.imm05.rbac.can", return_value=False):
            data = get_document(self.name)
        self.assertEqual(
            data.get("can_approve"), 0,
            "user KHÔNG có capability doc.approve → can_approve == 0.")

    def test_can_approve_is_int_not_bool(self):
        """Contract codegen (LL-BE-50): cờ 0/1 phải là int (Dart/Kotlin), KHÔNG bool."""
        with patch("assetcore.services.imm05.rbac.can", return_value=True):
            data = get_document(self.name)
        self.assertIsInstance(data.get("can_approve"), int)


if __name__ == "__main__":
    unittest.main()
