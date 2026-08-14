# Copyright (c) 2026, AssetCore Team
"""IMM-05 unit tests — approve_document, reject_document, update_document, _resolve_alert_level.

Run: bench --site miyano run-tests --app assetcore --module assetcore.tests.test_imm05
"""
from __future__ import annotations

import json
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.utils import add_days, nowdate

from assetcore.services.imm05 import (
    DocState,
    Visibility,
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
from assetcore.tests._asset_cleanup import purge_asset, purge_assets_created_after
from assetcore.tests._helpers.paths import SERVICES_DIR


#: Mốc bắt đầu module — lưới an toàn purge asset sinh sau mốc này.
_MODULE_START = None


def setUpModule():
    global _MODULE_START
    frappe.set_user("Administrator")
    _MODULE_START = frappe.utils.now_datetime()


def tearDownModule():
    """Lưới an toàn: không để asset fixture nào sống sót ra site."""
    purge_assets_created_after(_MODULE_START)


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


# Teardown asset dùng CHUNG `_asset_cleanup.purge_asset` — KHÔNG tự viết lại.
# Bản sao cục bộ trước đây chỉ dọn 4 dependent (thiếu Asset Decommission, PM
# Work Order, Asset Repair, IMM Asset Calibration…) nên mỗi lần chạy module này
# để lại 6 asset trên site. Hợp đồng khoá bởi `test_fixture_cleanup_contract.py`.
_purge_asset = purge_asset


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
        # `frappe.delete_doc` trần LUÔN thất bại ở đây: `AC Asset.on_trash`
        # (WR-03) chặn khi còn audit trail, và `except: pass` nuốt lỗi → asset
        # rò ra site im lặng. Phải đi qua `purge_asset` (dọn dependent trước).
        for name in cls._cleanup_assets:
            purge_asset(name)
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
        # Xem ghi chú ở tearDownClass phía trên: delete_doc trần + except:pass
        # = rò asset im lặng (WR-03 chặn). Dùng purge_asset.
        for name in cls._cleanup_assets:
            purge_asset(name)

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


# ─── CR-75 — Hồ sơ pháp lý NÓI THẬT (get_asset_documents) ─────────────────────
#   Core Doc: docs/imm-05/05_API_Specification.md §2.7 + §2.7.a (B1..B9),
#   docs/imm-05/04_Backend_Design.md §4.3/§4.4, docs/imm-05/07_Testing_QA.md §III.2.a.
#   Trước CR-75: `completeness_pct` là literal 0 (stub) và `document_status` chỉ đo
#   SỰ-CÓ-MẶT (missing rỗng ⇒ "Complete") nên hồ sơ bắt buộc ĐÃ QUÁ HẠN vẫn báo
#   "Complete" (dương-tính-giả NĐ98 Điều 41) + từ vựng phân kỳ với enum SSoT 5 giá
#   trị `_compute_document_status()`. Bộ test này viết TRƯỚC code (TDD, CLAUDE.md §17).
class _DossierFixtureMixin:
    """Fixture dùng CHUNG cho 2 bộ ca dossier: CR-75 (số học) + AC-CR-81 (tệp).

    Tách thành mixin thay vì copy-paste: 07 §III.2.b yêu cầu `TestAssetDossierFileMeta`
    **tái dùng** `_mk_asset`/`_mk_type`/`_mk_doc` của `TestAssetDossierTruth`; 2 bộ ca
    dựng CÙNG một loại dữ liệu nên fixture phân kỳ = 2 sự thật về "dossier trông thế nào".
    Mixin KHÔNG kế thừa `unittest.TestCase` ⇒ runner không thu thập nó như 1 bộ ca.
    """

    _PREFIX = "_Test CR75 "

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        cls._assets: list[str] = []
        cls._categories: list[str] = []
        cls._types: list[str] = []

    @classmethod
    def tearDownClass(cls):
        for name in cls._assets:
            purge_asset(name)
        for name in cls._types:
            try:
                frappe.delete_doc("Required Document Type", name,
                                  force=1, ignore_permissions=True)
            except Exception:
                pass
        for name in cls._categories:
            try:
                frappe.delete_doc("AC Asset Category", name,
                                  force=1, ignore_permissions=True)
            except Exception:
                pass
        frappe.db.commit()
        super().tearDownClass()

    # ── fixtures ─────────────────────────────────────────────────────────────

    def _mk_category(self) -> str:
        cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": f"_TestCR75Cat-{frappe.generate_hash(length=6)}",
            "category_code": f"C75{frappe.generate_hash(length=4)}",
        })
        cat.flags.ignore_mandatory = True
        cat.insert(ignore_permissions=True)
        type(self)._categories.append(cat.name)
        return cat.name

    def _mk_asset(self, category: str | None = None) -> str:
        _ensure_uom()
        payload = {
            "doctype": "AC Asset",
            "asset_name": f"_Test Asset CR75 {frappe.generate_hash(length=6)}",
        }
        if category:
            payload["asset_category"] = category
        doc = frappe.get_doc(payload)
        doc.flags.ignore_mandatory = True
        doc.insert(ignore_permissions=True)
        type(self)._assets.append(doc.name)
        return doc.name

    def _mk_type(self, *, mandatory: int = 1, category: str = "") -> str:
        """Tạo `Required Document Type` tạm (autoname field:type_name ⇒ tên = PK)."""
        type_name = f"{self._PREFIX}{frappe.generate_hash(length=8)}"
        doc = frappe.get_doc({
            "doctype": "Required Document Type",
            "type_name": type_name,
            "doc_category": "Technical",
            "is_mandatory": mandatory,
            "applies_to_asset_category": category or "",
        })
        doc.flags.ignore_mandatory = True
        doc.insert(ignore_permissions=True)
        type(self)._types.append(doc.name)
        return type_name

    def _mk_doc(self, asset: str, type_name: str, state: str = DocState.ACTIVE,
                *, expiry: str | None = None, visibility: str = Visibility.PUBLIC,
                is_exempt: int = 0, stale_days: int | None = None,
                stale_expired: int | None = None,
                attach: str | None = "/files/dummy-test.pdf",
                doc_category: str = "Technical") -> str:
        """Seed 1 `Asset Document`.

        Insert ở Draft rồi `db.set_value` sang state đích: bỏ qua
        `archive_old_versions` (BR-01 tự Archive bản Active cùng loại) + VR-05/VR-06,
        cho phép dựng CHÍNH XÁC tổ hợp (state × expiry) mà predicate cần.

        ⚠ `attach` mặc định `/files/dummy-test.pdf` — chuỗi này KHÔNG có `File` doc nào
        ⇒ mọi ca CR-75 cũ là ca **LINK MỒ CÔI** sẵn có (AC-CR-81 §2.7.c F1 nhóm 2).
        """
        issued = add_days(expiry, -365) if expiry else add_days(nowdate(), -400)
        doc = frappe.get_doc({
            "doctype": "Asset Document",
            "asset_ref": asset,
            "doc_category": doc_category,
            "doc_type_detail": type_name,
            "doc_number": f"DOC-CR75-{frappe.generate_hash(length=8)}",
            "version": "1.0",
            "issued_date": issued,
            "expiry_date": expiry,
            "file_attachment": attach,
            "visibility": visibility,
            "workflow_state": DocState.DRAFT,
        })
        doc.flags.ignore_mandatory = True
        doc.insert(ignore_permissions=True)
        patch: dict = {"workflow_state": state}
        if is_exempt:
            # VR-10/VR-11 chặn is_exempt qua doc.save (chỉ cho 2 loại NĐ98 + bắt
            # buộc exempt_reason/proof) → set thẳng cột: ca thử đo READ-PATH.
            patch["is_exempt"] = 1
        if stale_days is not None:
            patch["days_until_expiry"] = stale_days
        if stale_expired is not None:
            patch["is_expired"] = stale_expired
        frappe.db.set_value("Asset Document", doc.name, patch, update_modified=False)
        frappe.db.commit()
        return doc.name

    @staticmethod
    def _dossier(asset: str) -> dict:
        from assetcore.services.imm05 import get_asset_documents
        return get_asset_documents(asset)

    @staticmethod
    def _rows(data: dict) -> list[dict]:
        return [r for rows in (data.get("documents") or {}).values() for r in rows]

    def _row_of(self, data: dict, name: str) -> dict:
        row = next((r for r in self._rows(data) if r["name"] == name), None)
        self.assertIsNotNone(row, f"Không thấy dòng {name} trong documents.")
        return row


class TestAssetDossierTruth(_DossierFixtureMixin, unittest.TestCase):
    """CR-75 — BR-05-17..BR-05-21 cho `get_asset_documents`.

    Kỹ thuật: BVA (biên hạn today/-1/+30/+31) · Decision Table (5 giá trị enum) ·
    Invariant (INV-DOC-2/3, INV-EXP-2) · Counterexample (Archived quá hạn).

    ⚠ Quyết định thiết kế test (chống dương-tính-giả do master data):
    `Required Document Type` là **master data site-wide**; loại bắt buộc có
    `applies_to_asset_category` rỗng áp cho MỌI asset ⇒ mẫu số của asset fixture
    KHÔNG thể cô lập bằng fixture. Vì vậy:
      * ca kiểm SỐ HỌC (mẫu số/pct/enum) `patch` `_applicable_required_types` để
        chốt ĐÚNG tập loại của ca thử ⇒ số kỳ vọng tất định, khớp literal spec;
      * ca kiểm MẪU SỐ (B1 — #03/#04/#05) chạy helper THẬT, assert theo
        membership (∈ / ∉) nên miễn nhiễm master data có sẵn.
    """

    # ── #01 — mẫu số rỗng ⇒ KHÔNG chia 0 (TC-05-DOSSIER-01) ──────────────────

    def test_cr75_01_no_applicable_required_types_is_compliant_100(self):
        """required_total==0 ⇒ pct=100 (B5), 'Compliant', is_compliant=1, 3 mảng rỗng."""
        asset = self._mk_asset()
        with patch("assetcore.services.imm05._applicable_required_types", return_value=[]):
            data = self._dossier(asset)
        self.assertEqual(data["required_total"], 0)
        self.assertEqual(data["required_satisfied"], 0)
        self.assertEqual(data["completeness_pct"], 100,
                         "required_total==0 PHẢI ⇒ pct=100 (không chia 0).")
        self.assertEqual(data["document_status"], "Compliant")
        self.assertEqual(data["is_compliant"], 1)
        self.assertEqual(data["missing_required"], [])
        self.assertEqual(data["expired_required"], [])
        self.assertEqual(data["expiring_required"], [])

    # ── #02 — nửa bộ hồ sơ ⇒ số THẬT (TC-05-DOSSIER-02) ──────────────────────

    def test_cr75_02_half_dossier_returns_real_pct(self):
        """4 loại bắt buộc, 2 loại có bản Active còn hiệu lực ⇒ pct=50, Incomplete.

        RED trước fix: `completeness_pct` là literal 0.
        """
        asset = self._mk_asset()
        t = [self._mk_type() for _ in range(4)]
        self._mk_doc(asset, t[0], expiry=add_days(nowdate(), 365))
        self._mk_doc(asset, t[1], expiry=None)
        with patch("assetcore.services.imm05._applicable_required_types",
                   return_value=sorted(t)):
            data = self._dossier(asset)
        self.assertEqual(data["required_total"], 4)
        self.assertEqual(data["required_satisfied"], 2)
        self.assertEqual(data["completeness_pct"], 50,
                         "pct PHẢI = round(2/4*100) = 50 (KHÔNG stub 0).")
        self.assertEqual(data["document_status"], "Incomplete")
        self.assertEqual(data["is_compliant"], 0)
        self.assertEqual(sorted(data["missing_required"]), sorted([t[2], t[3]]))
        self.assertEqual(data["expired_required"], [])

    # ── #03/#04/#05 — mẫu số ÁP DỤNG theo nhóm thiết bị (B1) ─────────────────

    def test_cr75_03_type_of_other_category_excluded_from_denominator(self):
        """Loại bắt buộc có applies_to_asset_category ≠ nhóm asset ⇒ NGOÀI mẫu số.

        RED trước fix: mọi loại is_mandatory=1 đều bị đếm.
        """
        cat_a = self._mk_category()
        cat_b = self._mk_category()
        asset = self._mk_asset(cat_a)
        foreign = self._mk_type(category=cat_b)
        data = self._dossier(asset)
        self.assertNotIn(foreign, data["missing_required"],
                         "Loại thuộc nhóm KHÁC không được vào missing_required.")
        self.assertNotIn(foreign, data["expired_required"])

    def test_cr75_04_type_of_same_category_included_in_denominator(self):
        """Loại bắt buộc có applies_to_asset_category == nhóm asset ⇒ TRONG mẫu số."""
        cat = self._mk_category()
        asset = self._mk_asset(cat)
        mine = self._mk_type(category=cat)
        data = self._dossier(asset)
        self.assertIn(mine, data["missing_required"],
                      "Loại cùng nhóm PHẢI vào mẫu số (và thiếu ⇒ missing_required).")
        self.assertGreaterEqual(data["required_total"], 1)

    def test_cr75_05_type_without_category_applies_to_every_asset(self):
        """applies_to_asset_category rỗng ⇒ áp MỌI nhóm (kể cả asset không có nhóm)."""
        asset = self._mk_asset()
        glob = self._mk_type(category="")
        data = self._dossier(asset)
        self.assertIn(glob, data["missing_required"])

    def test_cr75_05b_non_mandatory_type_never_counted(self):
        """is_mandatory=0 ⇒ KHÔNG bao giờ vào mẫu số (B1)."""
        asset = self._mk_asset()
        optional = self._mk_type(mandatory=0)
        data = self._dossier(asset)
        self.assertNotIn(optional, data["missing_required"])
        self.assertNotIn(optional, data["expired_required"])

    # ── #06 — BUG LÕI: bắt buộc Active QUÁ HẠN (TC-05-DOSSIER-03) ────────────

    def test_cr75_06_expired_mandatory_is_non_compliant(self):
        """Mọi loại bắt buộc CÓ bản Active nhưng 1 loại hết hạn hôm qua ⇒
        'Non-Compliant', loại đó ∈ expired_required ∧ ∉ missing_required, pct < 100.

        RED trước fix: document_status == 'Complete' (chỉ đo sự-có-mặt).
        """
        asset = self._mk_asset()
        t_ok, t_bad = self._mk_type(), self._mk_type()
        self._mk_doc(asset, t_ok, expiry=add_days(nowdate(), 365))
        self._mk_doc(asset, t_bad, expiry=add_days(nowdate(), -1))
        with patch("assetcore.services.imm05._applicable_required_types",
                   return_value=sorted([t_ok, t_bad])):
            data = self._dossier(asset)
        self.assertEqual(data["document_status"], "Non-Compliant")
        self.assertEqual(data["is_compliant"], 0)
        self.assertIn(t_bad, data["expired_required"])
        self.assertNotIn(t_bad, data["missing_required"])
        self.assertEqual(data["required_satisfied"], 1)
        self.assertEqual(data["completeness_pct"], 50)
        self.assertLess(data["completeness_pct"], 100)

    # ── #07/#08/#09 — biên ngày (BVA) ────────────────────────────────────────

    def test_cr75_07_expiry_today_is_not_expired(self):
        """expiry == today ⇒ CHƯA hết hạn (`expired_filter` dùng `<`) ⇒ satisfied +
        expiring ⇒ 'Expiring_Soon' ∧ is_compliant == 1 ∧ is_expired dòng == 0."""
        asset = self._mk_asset()
        t = self._mk_type()
        name = self._mk_doc(asset, t, expiry=nowdate())
        with patch("assetcore.services.imm05._applicable_required_types",
                   return_value=[t]):
            data = self._dossier(asset)
        self.assertEqual(data["required_satisfied"], 1)
        self.assertEqual(data["completeness_pct"], 100)
        self.assertEqual(data["document_status"], "Expiring_Soon")
        self.assertEqual(data["is_compliant"], 1,
                         "Expiring_Soon là CẢNH BÁO — KHÔNG kéo is_compliant xuống 0.")
        self.assertIn(t, data["expiring_required"])
        self.assertEqual(self._row_of(data, name)["is_expired"], 0)

    def test_cr75_08_expiry_plus_30_days_is_expiring_soon(self):
        """Biên +30 ngày (tier Critical của _ALERT_THRESHOLDS) ⇒ Expiring_Soon."""
        asset = self._mk_asset()
        t = self._mk_type()
        self._mk_doc(asset, t, expiry=add_days(nowdate(), 30))
        with patch("assetcore.services.imm05._applicable_required_types",
                   return_value=[t]):
            data = self._dossier(asset)
        self.assertEqual(data["document_status"], "Expiring_Soon")
        self.assertEqual(data["is_compliant"], 1)
        self.assertEqual(data["completeness_pct"], 100)

    def test_cr75_09_expiry_plus_31_days_is_compliant(self):
        """Biên +31 ngày ⇒ NGOÀI ngưỡng 30 ⇒ 'Compliant', expiring_required rỗng."""
        asset = self._mk_asset()
        t = self._mk_type()
        self._mk_doc(asset, t, expiry=add_days(nowdate(), 31))
        with patch("assetcore.services.imm05._applicable_required_types",
                   return_value=[t]):
            data = self._dossier(asset)
        self.assertEqual(data["document_status"], "Compliant")
        self.assertEqual(data["expiring_required"], [])
        self.assertEqual(data["is_compliant"], 1)

    # ── #10/#11 — counterexample: KHÔNG đọc cột đã lưu ───────────────────────

    def test_cr75_10_archived_overdue_row_is_not_expired(self):
        """Archived quá hạn 100 ngày + cột DB is_expired=1 ⇒ dòng trả về is_expired==0
        (predicate loại Archived) — chứng minh KHÔNG đọc cột đã lưu."""
        asset = self._mk_asset()
        t = self._mk_type()
        name = self._mk_doc(asset, t, state=DocState.ARCHIVED,
                            expiry=add_days(nowdate(), -100), stale_expired=1)
        data = self._dossier(asset)
        self.assertEqual(self._row_of(data, name)["is_expired"], 0)

    def test_cr75_11_rejected_overdue_row_is_not_expired(self):
        """Rejected quá hạn ⇒ is_expired == 0 (cùng predicate `expired_filter`)."""
        asset = self._mk_asset()
        t = self._mk_type()
        name = self._mk_doc(asset, t, state=DocState.REJECTED,
                            expiry=add_days(nowdate(), -100), stale_expired=1)
        data = self._dossier(asset)
        self.assertEqual(self._row_of(data, name)["is_expired"], 0)

    def test_cr75_11b_active_overdue_row_is_expired(self):
        """Active quá hạn ⇒ is_expired == 1 (mặt còn lại của #10/#11)."""
        asset = self._mk_asset()
        t = self._mk_type()
        name = self._mk_doc(asset, t, expiry=add_days(nowdate(), -3), stale_expired=0)
        data = self._dossier(asset)
        row = self._row_of(data, name)
        self.assertEqual(row["is_expired"], 1)
        self.assertIsInstance(row["is_expired"], int)

    # ── #12 — days_until_expiry dẫn xuất lúc đọc (BR-05-21) ──────────────────

    def test_cr75_12_days_until_expiry_derived_not_stale_column(self):
        """Cột DB bịa 999 ⇒ response trả giá trị tính theo today (server clock)."""
        asset = self._mk_asset()
        t = self._mk_type()
        name = self._mk_doc(asset, t, expiry=add_days(nowdate(), 10), stale_days=999)
        data = self._dossier(asset)
        row = self._row_of(data, name)
        self.assertEqual(row["days_until_expiry"], 10,
                         "days_until_expiry PHẢI dẫn xuất lúc đọc, KHÔNG đọc cột stale.")

    def test_cr75_12b_null_expiry_row_has_null_days(self):
        """expiry_date NULL ⇒ days_until_expiry None ∧ is_expired 0 (không crash)."""
        asset = self._mk_asset()
        t = self._mk_type()
        name = self._mk_doc(asset, t, expiry=None)
        data = self._dossier(asset)
        row = self._row_of(data, name)
        self.assertIsNone(row["days_until_expiry"])
        self.assertEqual(row["is_expired"], 0)

    # ── #13/#14 — miễn đăng ký (BR-05-08 + ADR-IMM05-02 narrowed exempt) ─────

    def test_cr75_13_exempt_covering_full_dossier(self):
        """Đủ loại bắt buộc + 1 bản is_exempt=1 (không expiring) ⇒
        'Compliant (Exempt)' ∧ is_compliant == 1."""
        asset = self._mk_asset()
        t = self._mk_type()
        self._mk_doc(asset, t, expiry=add_days(nowdate(), 365), is_exempt=1)
        with patch("assetcore.services.imm05._applicable_required_types",
                   return_value=[t]):
            data = self._dossier(asset)
        self.assertEqual(data["document_status"], "Compliant (Exempt)")
        self.assertEqual(data["is_compliant"], 1)
        self.assertEqual(data["completeness_pct"], 100)

    def test_cr75_14_exempt_does_not_mask_missing_type(self):
        """ANTI-LIE: 1 bản is_exempt=1 nhưng còn 1 loại bắt buộc THIẾU ⇒
        'Incomplete' (KHÔNG 'Compliant (Exempt)') ∧ is_compliant == 0."""
        asset = self._mk_asset()
        t_ok, t_missing = self._mk_type(), self._mk_type()
        self._mk_doc(asset, t_ok, expiry=add_days(nowdate(), 365), is_exempt=1)
        with patch("assetcore.services.imm05._applicable_required_types",
                   return_value=sorted([t_ok, t_missing])):
            data = self._dossier(asset)
        self.assertEqual(data["document_status"], "Incomplete")
        self.assertEqual(data["is_compliant"], 0)
        self.assertIn(t_missing, data["missing_required"])

    # ── #15/#16 — invariant ──────────────────────────────────────────────────

    def test_cr75_15_inv_doc_2_partition(self):
        """INV-DOC-2: |missing| + |expired| == total − satisfied ∧ 2 mảng RỜI NHAU."""
        asset = self._mk_asset()
        t_ok, t_exp, t_missing, t_null = (self._mk_type() for _ in range(4))
        self._mk_doc(asset, t_ok, expiry=add_days(nowdate(), 365))
        self._mk_doc(asset, t_exp, expiry=add_days(nowdate(), -2))
        self._mk_doc(asset, t_null, expiry=None)
        with patch("assetcore.services.imm05._applicable_required_types",
                   return_value=sorted([t_ok, t_exp, t_missing, t_null])):
            data = self._dossier(asset)
        missing, expired = set(data["missing_required"]), set(data["expired_required"])
        self.assertEqual(missing & expired, set(), "2 mảng PHẢI rời nhau.")
        self.assertEqual(
            len(missing) + len(expired),
            data["required_total"] - data["required_satisfied"],
            "INV-DOC-2: |missing| + |expired| == total − satisfied.")

    def test_cr75_16_inv_doc_3_is_compliant_equivalence(self):
        """INV-DOC-3: is_compliant == int(satisfied == total) == int(pct == 100)
        ∧ is_compliant == 1 ⟺ status ∈ {Compliant, Compliant (Exempt), Expiring_Soon}."""
        compliant_set = {"Compliant", "Compliant (Exempt)", "Expiring_Soon"}
        asset = self._mk_asset()
        t_ok, t_exp, t_missing = (self._mk_type() for _ in range(3))
        self._mk_doc(asset, t_ok, expiry=add_days(nowdate(), 365))
        self._mk_doc(asset, t_exp, expiry=add_days(nowdate(), -2))
        cases = [
            sorted([t_ok, t_exp, t_missing]),   # hỗn hợp
            [t_ok],                             # đủ
            [t_missing],                        # thiếu
            [],                                 # mẫu số rỗng
        ]
        for required in cases:
            with self.subTest(required=len(required)):
                with patch("assetcore.services.imm05._applicable_required_types",
                           return_value=required):
                    data = self._dossier(asset)
                self.assertEqual(
                    data["is_compliant"],
                    int(data["required_satisfied"] == data["required_total"]))
                self.assertEqual(data["is_compliant"], int(data["completeness_pct"] == 100))
                self.assertEqual(data["is_compliant"],
                                 int(data["document_status"] in compliant_set))

    # ── #17 — INV-EXP-2: cặp song sinh predicate (mutation target) ───────────

    def test_cr75_17_inv_exp_2_row_predicate_matches_expired_filter(self):
        """`is_expired_row` (row đã nạp) trùng KHÍT `expired_filter()` (query) trên
        tập ≥6 doc phủ mọi state × (NULL / quá hạn / còn hạn)."""
        from assetcore.services.imm05 import expired_filter, is_expired_row
        asset = self._mk_asset()
        t = self._mk_type()
        names = [
            self._mk_doc(asset, t, state=DocState.ACTIVE, expiry=add_days(nowdate(), -5)),
            self._mk_doc(asset, t, state=DocState.DRAFT, expiry=add_days(nowdate(), -5)),
            self._mk_doc(asset, t, state=DocState.PENDING_REVIEW, expiry=add_days(nowdate(), -5)),
            self._mk_doc(asset, t, state=DocState.ARCHIVED, expiry=add_days(nowdate(), -5)),
            self._mk_doc(asset, t, state=DocState.REJECTED, expiry=add_days(nowdate(), -5)),
            self._mk_doc(asset, t, state=DocState.ACTIVE, expiry=None),
            self._mk_doc(asset, t, state=DocState.ACTIVE, expiry=add_days(nowdate(), 5)),
        ]
        rows = frappe.get_all(
            "Asset Document", filters={"asset_ref": asset},
            fields=["name", "workflow_state", "expiry_date"], limit_page_length=0)
        by_python = {r["name"] for r in rows if is_expired_row(r)}
        by_query = {
            r["name"] for r in frappe.get_all(
                "Asset Document",
                filters=expired_filter() + [["asset_ref", "=", asset]],
                fields=["name"], limit_page_length=0)
        }
        self.assertEqual(by_python, by_query,
                         "INV-EXP-2: predicate Python PHẢI trùng khít predicate query.")
        self.assertEqual(len(names), 7)

    # ── #18 — BR-05-20: tính trên tập ĐẦY ĐỦ, hiển thị vẫn lọc quyền ─────────

    def test_cr75_18_completeness_computed_on_full_set_display_filtered(self):
        """Persona thiếu `document.read`: `documents` chỉ còn bản Public (+ hidden_count>0)
        NHƯNG required_total/pct/status BẰNG kết quả chạy dưới Administrator."""
        asset = self._mk_asset()
        t_pub, t_int = self._mk_type(), self._mk_type()
        self._mk_doc(asset, t_pub, expiry=add_days(nowdate(), 365))
        self._mk_doc(asset, t_int, expiry=add_days(nowdate(), 365),
                     visibility=Visibility.INTERNAL_ONLY)
        required = sorted([t_pub, t_int])
        with patch("assetcore.services.imm05._applicable_required_types",
                   return_value=required):
            full = self._dossier(asset)
            with patch("assetcore.services.imm05._can_see_internal", return_value=False):
                limited = self._dossier(asset)
        for key in ("required_total", "required_satisfied", "completeness_pct",
                    "document_status", "is_compliant"):
            self.assertEqual(limited[key], full[key],
                             f"'{key}' PHẢI tính trên tập ĐẦY ĐỦ (BR-05-20), không theo visibility.")
        self.assertEqual(full["hidden_count"], 0)
        self.assertGreater(limited["hidden_count"], 0,
                           "hidden_count PHẢI lộ số bản bị ẩn (minh bạch phân quyền).")
        self.assertLess(len(self._rows(limited)), len(self._rows(full)))
        self.assertEqual(limited["completeness_pct"], 100)

    def test_cr75_18b_visibility_filtered_rows_are_public_only(self):
        """No-leak: persona thiếu `document.read` KHÔNG thấy bản Internal_Only, KHÔNG 500."""
        asset = self._mk_asset()
        t = self._mk_type()
        self._mk_doc(asset, t, expiry=add_days(nowdate(), 365),
                     visibility=Visibility.INTERNAL_ONLY)
        with patch("assetcore.services.imm05._can_see_internal", return_value=False):
            data = self._dossier(asset)
        self.assertTrue(
            all(r.get("visibility") in (Visibility.PUBLIC, "", None)
                for r in self._rows(data)),
            "Chỉ tài liệu Public được hiển thị cho persona thiếu document.read.")

    # ── 0-regress hợp đồng + guard nguồn ─────────────────────────────────────

    def test_cr75_19_legacy_keys_and_grouped_shape_preserved(self):
        """5 khoá cũ còn nguyên + `documents` VẪN là grouped-object theo doc_category."""
        asset = self._mk_asset()
        t = self._mk_type()
        self._mk_doc(asset, t, expiry=add_days(nowdate(), 365))
        data = self._dossier(asset)
        for key in ("asset", "completeness_pct", "document_status",
                    "documents", "missing_required"):
            self.assertIn(key, data, f"Khoá cũ '{key}' KHÔNG được biến mất (backward-compat).")
        for key in ("required_total", "required_satisfied", "is_compliant",
                    "expired_required", "expiring_required", "hidden_count"):
            self.assertIn(key, data, f"Khoá mới CR-75 '{key}' phải LUÔN xuất hiện.")
        self.assertEqual(data["asset"], asset)
        self.assertIsInstance(data["documents"], dict,
                              "`documents` PHẢI là grouped-object keyed doc_category.")
        self.assertIn("Technical", data["documents"])
        self.assertIsInstance(data["documents"]["Technical"], list)
        self.assertIsInstance(data["is_compliant"], int)
        self.assertNotIsInstance(data["is_compliant"], bool)
        self.assertIsInstance(data["completeness_pct"], int)

    def test_cr75_20_no_stub_literal_in_source(self):
        """Guard A1: literal `"completeness_pct": 0` KHÔNG còn trong services/imm05.py."""
        src = Path(SERVICES_DIR) / "imm05.py"
        text = src.read_text(encoding="utf-8")
        self.assertNotIn(
            '"completeness_pct": 0', text,
            "Stub hồi quy: completeness_pct KHÔNG được là hằng 0 (CR-75 A1).")

    def test_cr75_21_document_status_never_uses_legacy_vocabulary(self):
        """Hết phân kỳ từ vựng: 'Complete' KHÔNG còn là giá trị document_status."""
        allowed = {"Compliant", "Compliant (Exempt)", "Expiring_Soon",
                   "Non-Compliant", "Incomplete"}
        asset = self._mk_asset()
        t = self._mk_type()
        self._mk_doc(asset, t, expiry=add_days(nowdate(), 365))
        data = self._dossier(asset)
        self.assertIn(data["document_status"], allowed,
                      "document_status PHẢI thuộc enum SSoT 5 giá trị của "
                      "_compute_document_status() — KHÔNG 'Complete'/'Incomplete' riêng.")


# ─── AC-CR-81 — mỗi dòng hồ sơ phơi TỆP THẬT ─────────────────────────────────
#   Core Doc: docs/imm-05/05_API_Specification.md §2.7.c (F0–F6 + INV-FILE-1..8),
#   docs/imm-05/04_Backend_Design.md §4.4-bis, docs/imm-05/07_Testing_QA.md §III.2.b.
#   Trước AC-CR-81: CR-75 CỐ Ý không phát `file_url` ⇒ màn "Hồ sơ pháp lý thiết bị" là
#   STATE CHẾT — người dùng thấy "Giấy phép nhập khẩu · Active · còn 300 ngày" mà KHÔNG
#   có đường nào mở tờ giấy phép (NĐ98 Điều 41: bằng chứng không truy xuất được ≈ không
#   có bằng chứng). Bộ ca này viết TRƯỚC code (TDD, CLAUDE.md §17).
class TestAssetDossierFileMeta(_DossierFixtureMixin, unittest.TestCase):
    """AC-CR-81 — 5 khoá TỆP trên MỖI dòng `documents[<doc_category>][]`.

    Kỹ thuật: Decision Table (có tệp / mồ côi / rỗng) · Invariant (INV-FILE-1..8) ·
    Counterexample (link mồ côi KHÔNG được phát ra UI) · Đo-số-query (chống N+1).

    ⚠ Fixture `_mk_doc` mặc định gán `file_attachment = "/files/dummy-test.pdf"` mà
    KHÔNG có `File` doc ⇒ mọi ca CR-75 cũ tự rơi nhánh `has_file = 0` — đây là TÍNH
    NĂNG (0 sửa fixture cũ) và là lý do ca #03 phải khẳng định tường minh.
    """

    _PREFIX = "_Test CR81 "

    _FILE_KEYS = ("file_url", "file_name", "file_size", "is_private", "has_file")

    #: Tiền tố `File.file_name` của bộ ca — teardown quét THEO TIỀN TỐ, không theo
    #: danh sách đã tạo: hook `link_uploaded_files` (`hooks.py::doc_events["*"]`) NHÂN
    #: BẢN File cho mỗi `Asset Document` trỏ tới cùng URL ⇒ danh sách tự-ghi bỏ sót
    #: bản sao và để rác trên site (class-of-bug fixture-leak đã dọn 2026-05-29).
    _FILE_PREFIX = "_test_cr81_"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._files: list[str] = []

    @classmethod
    def tearDownClass(cls):
        # Xoá Asset Document/asset TRƯỚC (super) rồi mới xoá File: File còn bị doc
        # tham chiếu sẽ vướng `validate_attachment_references`.
        super().tearDownClass()
        cls._purge_test_files()

    @classmethod
    def _purge_test_files(cls) -> None:
        """Xoá MỌI `File` fixture của bộ ca (kể cả bản sao do hook sinh) + tệp trên đĩa."""
        # `_` là ký tự đại diện của LIKE ⇒ bọc `%…%` thay vì ghép tiền tố thô.
        names = frappe.get_all(
            "File", filters={"file_name": ["like", f"%{cls._FILE_PREFIX}%"]},
            pluck="name", limit_page_length=0)
        for name in names:
            try:
                frappe.delete_doc("File", name, force=1, ignore_permissions=True,
                                  delete_permanently=True)
            except Exception:
                pass
        frappe.db.commit()
        for scope in ("public", "private"):
            folder = Path(frappe.get_site_path(scope, "files"))
            for leftover in folder.glob(f"*{cls._FILE_PREFIX}*"):
                try:
                    leftover.unlink()
                except OSError:
                    pass

    # ── fixtures ─────────────────────────────────────────────────────────────

    def _mk_file(self, *, private: int = 0, size: int = 64) -> dict:
        """Tạo `File` doc THẬT (ghi bytes xuống đĩa) — xoá trong tearDownClass.

        Đuôi `.docx`: VR-08 (`asset_document.py`) chỉ nhận PDF/JPG/PNG/DOCX, còn
        `File.check_content` quét nội dung bằng pypdf khi `file_type == "PDF"` nên bytes
        rác + đuôi `.pdf` ném `PdfStreamError` (xem `test_attachment_upload.py`).
        Nội dung có tiền tố NGẪU NHIÊN: `File.validate_duplicate_entry` gộp 2 file trùng
        `content_hash` về CÙNG `file_url` ⇒ nội dung giống nhau sẽ phá ca #06 (6 URL riêng).
        """
        content = (frappe.generate_hash(length=16) + "x" * max(size - 16, 0)).encode()
        doc = frappe.get_doc({
            "doctype": "File",
            "file_name": f"_test_cr81_{frappe.generate_hash(length=8)}.docx",
            "is_private": private,
            "content": content,
            "decode": False,
        }).insert(ignore_permissions=True)
        type(self)._files.append(doc.name)
        return {
            "url": doc.file_url,
            "file_name": doc.file_name,
            "file_size": int(doc.file_size or 0),
            "is_private": int(doc.is_private or 0),
        }

    @contextmanager
    def _count_queries(self):
        """Đếm `frappe.get_all` THEO doctype (07 §III.2.b) — không phụ thuộc log SQL.

        Yield list `[(doctype, filters), …]`; ca #06/#07/#08 lọc `doctype == "File"`.
        """
        calls: list[tuple] = []
        real = frappe.get_all

        def spy(doctype, *args, **kwargs):
            calls.append((doctype, kwargs.get("filters")))
            return real(doctype, *args, **kwargs)

        with patch("assetcore.services.imm05.frappe.get_all", side_effect=spy):
            yield calls

    @staticmethod
    def _file_calls(calls: list[tuple]) -> list[tuple]:
        return [c for c in calls if c[0] == "File"]

    def _assert_empty_file_meta(self, row: dict, why: str) -> None:
        """INV-FILE-1/2/3 — 5 khoá CÓ MẶT và ở giá trị RỖNG chuẩn ("", 0)."""
        for key in self._FILE_KEYS:
            self.assertIn(key, row, f"{why}: khoá `{key}` PHẢI luôn có mặt (INV-FILE-1).")
            self.assertIsNotNone(row[key], f"{why}: `{key}` KHÔNG được None (AC1).")
        self.assertEqual(row["has_file"], 0, why)
        self.assertEqual(row["file_url"], "", f"{why}: KHÔNG phát link chết (INV-FILE-2).")
        self.assertEqual(row["file_name"], "", f"{why} (INV-FILE-3).")
        self.assertEqual(row["file_size"], 0, f"{why} (INV-FILE-3).")
        self.assertEqual(row["is_private"], 0, f"{why} (INV-FILE-3).")

    # ── #01 — 5 khoá LUÔN có mặt (TC-05-FILE-01, INV-FILE-1/AC1) ─────────────

    def test_cr81_01_five_file_keys_always_present(self):
        """Dòng CHƯA đính tệp vẫn có ĐỦ 5 khoá, 0 giá trị None (client không null-check)."""
        asset = self._mk_asset()
        t = self._mk_type()
        name = self._mk_doc(asset, t, expiry=add_days(nowdate(), 365), attach="")
        row = self._row_of(self._dossier(asset), name)
        self._assert_empty_file_meta(row, "Dòng chưa đính tệp")

    # ── #02 — tệp THẬT (TC-05-FILE-02, AC2) ──────────────────────────────────

    def test_cr81_02_real_file_resolves_all_four_metadata_keys(self):
        """`file_attachment` trỏ File doc TỒN TẠI ⇒ has_file=1 + 4 khoá khớp ĐÚNG File doc."""
        asset = self._mk_asset()
        t = self._mk_type()
        f = self._mk_file(size=128)
        name = self._mk_doc(asset, t, expiry=add_days(nowdate(), 365), attach=f["url"])
        row = self._row_of(self._dossier(asset), name)
        self.assertEqual(row["has_file"], 1,
                         "File doc TỒN TẠI ⇒ has_file PHẢI = 1 (AC2).")
        self.assertEqual(row["file_url"], f["url"])
        self.assertEqual(row["file_name"], f["file_name"],
                         "file_name PHẢI lấy từ `File.file_name` (SSoT), KHÔNG phải cột "
                         "denorm `file_name_display` (F4).")
        self.assertEqual(row["file_size"], f["file_size"])
        self.assertGreater(row["file_size"], 0)
        self.assertIn(row["is_private"], (0, 1))

    # ── #03 — LINK MỒ CÔI (TC-05-FILE-03, INV-FILE-2/3 — khoá nghiệp vụ F3) ──

    def test_cr81_03_orphan_link_never_leaves_a_dead_url(self):
        """`file_attachment` trỏ URL KHÔNG còn File doc ⇒ has_file=0 ∧ 5 khoá RỖNG.

        Counterexample: nút «Mở tệp» dẫn 404 giữa ca trực khiến KTV/thanh tra tin rằng
        bệnh viện MẤT hồ sơ NĐ98, trong khi sự thật là bản ghi trỏ sai.
        """
        asset = self._mk_asset()
        t = self._mk_type()
        orphan = f"/files/khong-ton-tai-{frappe.generate_hash(length=8)}.pdf"
        name = self._mk_doc(asset, t, expiry=add_days(nowdate(), 365), attach=orphan)
        data = self._dossier(asset)
        row = self._row_of(data, name)
        self._assert_empty_file_meta(row, "Link mồ côi")
        self.assertNotIn(orphan, json.dumps(data, default=str),
                         "URL mồ côi KHÔNG được xuất hiện ở BẤT KỲ đâu trong payload.")

    # ── #04 — rỗng / None (TC-05-FILE-04) ────────────────────────────────────

    def test_cr81_04_empty_and_null_attachment_both_safe(self):
        """`file_attachment` "" và None ⇒ như #01, KHÔNG KeyError (2 biến thể)."""
        asset = self._mk_asset()
        t = self._mk_type()
        n_empty = self._mk_doc(asset, t, expiry=add_days(nowdate(), 365), attach="")
        n_null = self._mk_doc(asset, t, expiry=add_days(nowdate(), 365), attach=None)
        data = self._dossier(asset)
        self._assert_empty_file_meta(self._row_of(data, n_empty), 'attach = ""')
        self._assert_empty_file_meta(self._row_of(data, n_null), "attach = None")

    # ── #05 — cờ là int THUẦN (TC-05-FILE-05, INV-FILE-7 / quirk CR-01) ──────

    def test_cr81_05_flags_are_plain_int_not_bool(self):
        """`has_file`/`is_private` PHẢI là int thuần — bool lọt vào làm vỡ strict-deser
        Dart/Kotlin (bool là subclass của int ⇒ phải assertNotIsInstance riêng)."""
        asset = self._mk_asset()
        t = self._mk_type()
        f = self._mk_file(private=1)
        name = self._mk_doc(asset, t, expiry=add_days(nowdate(), 365), attach=f["url"])
        row = self._row_of(self._dossier(asset), name)
        for key in ("has_file", "is_private", "file_size"):
            self.assertIs(type(row[key]), int, f"`{key}` PHẢI là int thuần (INV-FILE-7).")
            self.assertNotIsInstance(row[key], bool,
                                     f"`{key}` KHÔNG được là bool (quirk CR-01).")

    # ── #06 — chống N+1 (TC-05-FILE-06, INV-FILE-4/AC3) ──────────────────────

    def test_cr81_06_batch_resolve_is_exactly_one_file_query(self):
        """12 dòng / 3 doc_category, 6 dòng có tệp ⇒ ĐÚNG 1 truy vấn `File` toàn payload.

        Mutation: chuyển `_resolve_file_meta` vào trong vòng lặp dòng ⇒ ca này ĐỎ.
        """
        asset = self._mk_asset()
        t = self._mk_type()
        # 3 nhóm KHÔNG kích VR-04 (`Legal` bắt buộc `issuing_authority`) — ca này đo
        # SỐ QUERY, không đo validator.
        categories = ["Technical", "Certification", "Training"]
        for i in range(12):
            attach = self._mk_file()["url"] if i % 2 == 0 else ""
            self._mk_doc(asset, t, expiry=add_days(nowdate(), 365),
                         attach=attach, doc_category=categories[i % 3])
        with self._count_queries() as calls:
            data = self._dossier(asset)
        self.assertEqual(len(self._file_calls(calls)), 1,
                         "PHẢI ĐÚNG 1 truy vấn `File` bất kể số dòng (INV-FILE-4). "
                         f"Thực tế: {len(self._file_calls(calls))}.")
        self.assertEqual(len(self._rows(data)), 12)
        self.assertEqual(sum(r["has_file"] for r in self._rows(data)), 6)

    # ── #07 — tập rỗng ⇒ 0 query (TC-05-FILE-07) ─────────────────────────────

    def test_cr81_07_no_attachment_means_zero_file_query(self):
        """Mọi dòng rỗng ⇒ 0 truy vấn `File` (KHÔNG phát `IN ()` vô nghĩa)."""
        asset = self._mk_asset()
        t = self._mk_type()
        for _ in range(3):
            self._mk_doc(asset, t, expiry=add_days(nowdate(), 365), attach="")
        with self._count_queries() as calls:
            data = self._dossier(asset)
        self.assertEqual(self._file_calls(calls), [],
                         "Tập URL rỗng ⇒ KHÔNG được chạy truy vấn `File` nào.")
        self.assertTrue(all(r["has_file"] == 0 for r in self._rows(data)))

    # ── #08 — dedup (TC-05-FILE-08) ──────────────────────────────────────────

    def test_cr81_08_same_url_on_three_rows_is_deduped(self):
        """3 dòng dùng CÙNG `file_url` ⇒ 1 query, đối số `in` có ĐÚNG 1 phần tử."""
        asset = self._mk_asset()
        t = self._mk_type()
        f = self._mk_file()
        for _ in range(3):
            self._mk_doc(asset, t, expiry=add_days(nowdate(), 365), attach=f["url"])
        with self._count_queries() as calls:
            data = self._dossier(asset)
        file_calls = self._file_calls(calls)
        self.assertEqual(len(file_calls), 1)
        urls = (file_calls[0][1] or {}).get("file_url")
        self.assertEqual(urls[0], "in", f"filters PHẢI dùng toán tử `in`: {urls}")
        self.assertEqual(len(urls[1]), 1,
                         f"Tập URL PHẢI dedup trước khi query (F2): {urls[1]}")
        rows = self._rows(data)
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(r["has_file"] == 1 for r in rows))

    # ── #09 — 0 REGRESS nhánh tuân thủ (TC-05-FILE-09, INV-FILE-5/AC4) ───────

    def test_cr81_09_compliance_branch_is_untouched(self):
        """Ca CR-75 #02 (pct 50) chạy lại: 9 khoá F6 y hệt giá trị kỳ vọng CR-75."""
        asset = self._mk_asset()
        t = [self._mk_type() for _ in range(4)]
        self._mk_doc(asset, t[0], expiry=add_days(nowdate(), 365),
                     attach=self._mk_file()["url"])
        self._mk_doc(asset, t[1], expiry=None, attach="")
        with patch("assetcore.services.imm05._applicable_required_types",
                   return_value=sorted(t)):
            data = self._dossier(asset)
        self.assertEqual(data["required_total"], 4)
        self.assertEqual(data["required_satisfied"], 2)
        self.assertEqual(data["completeness_pct"], 50,
                         "AC4: nhánh tính toán (C) KHÔNG được đụng khi bồi khoá tệp.")
        self.assertEqual(data["document_status"], "Incomplete")
        self.assertEqual(data["is_compliant"], 0)
        self.assertEqual(sorted(data["missing_required"]), sorted([t[2], t[3]]))
        self.assertEqual(data["expired_required"], [])
        self.assertEqual(data["expiring_required"], [])
        self.assertEqual(data["hidden_count"], 0)

    # ── #10 — 0 RÒ QUYỀN (TC-05-FILE-10, INV-FILE-6/AC5) ─────────────────────

    def test_cr81_10_hidden_row_url_never_reaches_payload(self):
        """Persona thiếu `document.read`: dòng Internal_Only vắng khỏi `documents` VÀ
        URL tệp của nó KHÔNG xuất hiện ở bất kỳ đâu trong payload; hidden_count == 1.

        Mutation: đổi tập vào của batch từ V (đã lọc visibility) sang C ⇒ ca này ĐỎ.
        """
        asset = self._mk_asset()
        t_pub, t_int = self._mk_type(), self._mk_type()
        f_pub, f_int = self._mk_file(), self._mk_file()
        n_pub = self._mk_doc(asset, t_pub, expiry=add_days(nowdate(), 365),
                             attach=f_pub["url"])
        n_int = self._mk_doc(asset, t_int, expiry=add_days(nowdate(), 365),
                             attach=f_int["url"], visibility=Visibility.INTERNAL_ONLY)
        with patch("assetcore.services.imm05._can_see_internal", return_value=False):
            data = self._dossier(asset)
        names = {r["name"] for r in self._rows(data)}
        self.assertIn(n_pub, names)
        self.assertNotIn(n_int, names, "Dòng Internal_Only PHẢI bị lọc khỏi `documents`.")
        self.assertEqual(data["hidden_count"], 1,
                         "hidden_count PHẢI vẫn đếm đúng số bản bị ẩn (AC5).")
        blob = json.dumps(data, default=str)
        self.assertNotIn(f_int["url"], blob,
                         "RÒ QUYỀN: URL tệp của dòng bị ẩn KHÔNG BAO GIỜ được ra response "
                         "(INV-FILE-6) — batch PHẢI chạy trên tập V, KHÔNG phải tập C.")
        self.assertEqual(self._row_of(data, n_pub)["file_url"], f_pub["url"])

    # ── #11 — tệp riêng tư (TC-05-FILE-11, F5) ───────────────────────────────

    def test_cr81_11_private_file_flag_and_path(self):
        """`File.is_private = 1` ⇒ is_private == 1 ∧ file_url bắt đầu `/private/files/`."""
        asset = self._mk_asset()
        t = self._mk_type()
        f = self._mk_file(private=1)
        name = self._mk_doc(asset, t, expiry=add_days(nowdate(), 365), attach=f["url"])
        row = self._row_of(self._dossier(asset), name)
        self.assertEqual(row["is_private"], 1)
        self.assertTrue(row["file_url"].startswith("/private/files/"),
                        f"Tệp riêng tư phục vụ qua /private/files/…: {row['file_url']}")
        self.assertEqual(row["has_file"], 1)

    # ── #12 — key-set ĐÚNG 18 (TC-05-FILE-12, INV-FILE-8) ────────────────────

    def test_cr81_12_row_keyset_is_exactly_eighteen_keys(self):
        """13 khoá CR-75 + 5 khoá tệp; `file_attachment` THÔ KHÔNG lọt (closed-schema OAS).

        Mutation: bỏ `row.pop("file_attachment")` ⇒ ca này ĐỎ (khoá thứ 19 làm vỡ
        codegen client vì `additionalProperties: false`).
        """
        expected = sorted([
            "approval_date", "approved_by", "days_until_expiry", "doc_category",
            "doc_number", "doc_type_detail", "expiry_date", "is_exempt", "is_expired",
            "name", "version", "visibility", "workflow_state",
            *self._FILE_KEYS,
        ])
        asset = self._mk_asset()
        t = self._mk_type()
        f = self._mk_file()
        name = self._mk_doc(asset, t, expiry=add_days(nowdate(), 365), attach=f["url"])
        row = self._row_of(self._dossier(asset), name)
        self.assertEqual(sorted(row.keys()), expected,
                         "Key-set mỗi dòng PHẢI ĐÚNG 18 khoá (INV-FILE-8).")
        self.assertNotIn("file_attachment", row,
                         "`file_attachment` THÔ KHÔNG BAO GIỜ ra response (F3).")


if __name__ == "__main__":
    unittest.main()
