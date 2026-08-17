# Copyright (c) 2026, AssetCore Team
# IMM-10 Recall/FSCA — Test suite TC-B1→B9 (Spec mobile 47 §Test — contract FROZEN).
#
# Endpoint dưới test: assetcore.api.imm10.check_asset_recall (read-only).
# Fixture: _ensure_doc idempotent (parity test_imm15 LL-TEST-9) + cleanup
# tearDownClass qua purge_asset. KHÔNG đụng doctype Asset Repair (collision
# ERPNext đã biết) — vendor-scope test dùng PM Work Order.
#
# Run: bench --site miyano run-tests --module assetcore.tests.imm10.test_imm10
from __future__ import annotations

import unittest
import uuid
from contextlib import suppress

import frappe

from assetcore.api.imm10 import check_asset_recall
from assetcore.tests._helpers._asset_cleanup import purge_asset
from frappe.tests.utils import FrappeTestCase

_DT_RECALL = "IMM Recall Notice"

# 8 field / row recall — verbatim Spec 47 §3b (khoá shape cho mobile parity-curate).
_ROW_KEYS = {
    "name", "title", "source", "severity",
    "action_required", "scope_note", "published_date", "reference_no",
}


def _ensure_doc(doctype: str, lookup: dict, data: dict) -> str:
    """Idempotent fixture create — parity test_imm15._ensure_doc (LL-TEST-9).

    Doctype autonamed → match theo business key trong ``lookup`` (KHÔNG theo
    ``name``), tránh leak record mới mỗi lần chạy.
    """
    existing = frappe.db.get_value(doctype, lookup, "name")
    if existing:
        return existing
    doc = frappe.get_doc({"doctype": doctype, **lookup, **data})
    doc.flags.ignore_links = True
    doc.flags.ignore_mandatory = True
    doc.insert(ignore_permissions=True)
    return doc.name


class TestImm10Base(FrappeTestCase):
    """Fixture chung TC-B1→B9: 2 device model + 2 asset (có/không model) + QR token."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.model_a = _ensure_doc(
            "IMM Device Model", {"model_name": "_Test Model IMM-10 A"}, {})
        cls.model_b = _ensure_doc(
            "IMM Device Model", {"model_name": "_Test Model IMM-10 B"}, {})
        cls.asset = _ensure_doc(
            "AC Asset", {"asset_name": "_Test Asset IMM-10"}, {})
        cls.asset_no_model = _ensure_doc(
            "AC Asset", {"asset_name": "_Test Asset IMM-10 NoModel"}, {})
        # QR token test-riêng (uuid mỗi run — tránh đụng unique index nếu run
        # trước leak); set thẳng DB, KHÔNG qua ensure_asset_qr_token (tránh
        # side-effect ALE qr_generated ngoài lane).
        cls.qr_token = f"_t-imm10-{uuid.uuid4().hex[:12]}"
        frappe.db.set_value(
            "AC Asset", cls.asset,
            {"device_model": cls.model_a, "qr_token": cls.qr_token},
            update_modified=False)
        frappe.db.set_value(
            "AC Asset", cls.asset_no_model, "device_model", "",
            update_modified=False)
        cls._users: list[str] = []
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        cls._purge_notices()
        with suppress(Exception):
            for wo in frappe.get_all(
                    "PM Work Order", filters={"asset_ref": cls.asset},
                    pluck="name"):
                frappe.delete_doc("PM Work Order", wo, force=True,
                                  ignore_permissions=True)
        for asset in (getattr(cls, "asset", ""), getattr(cls, "asset_no_model", "")):
            if asset:
                with suppress(Exception):
                    purge_asset(asset)
        for model in (getattr(cls, "model_a", ""), getattr(cls, "model_b", "")):
            if model:
                with suppress(Exception):
                    frappe.delete_doc("IMM Device Model", model, force=True,
                                      ignore_permissions=True)
        for email in cls._users:
            if frappe.db.exists("User", email):
                with suppress(Exception):
                    frappe.delete_doc("User", email, force=True,
                                      ignore_permissions=True)
        frappe.db.commit()

    def setUp(self):
        # Isolation giữa các test: mỗi test tự tạo notice cần thiết trên nền sạch.
        frappe.set_user("Administrator")
        self._purge_notices()

    @classmethod
    def _purge_notices(cls):
        for n in frappe.get_all(
                _DT_RECALL,
                filters={"device_model": ["in", [cls.model_a, cls.model_b]]},
                pluck="name"):
            with suppress(Exception):
                frappe.delete_doc(_DT_RECALL, n, force=True,
                                  ignore_permissions=True)
        frappe.db.commit()

    def _mk_notice(self, **over) -> str:
        data = {
            "doctype": _DT_RECALL,
            "title": "Thu hồi bơm tiêm điện — lỗi driver liều",
            "source": "Manufacturer",
            "severity": "Class I",
            "status": "Active",
            "device_model": self.model_a,
            "action_required": "Ngừng sử dụng, cách ly thiết bị, liên hệ phòng VTYT trong 24h.",
            "scope_note": "Lô SX 2025-Q4, serial 1000–2000",
            "published_date": "2026-07-01",
            "reference_no": "FSCA-2026-001",
        }
        data.update(over)
        doc = frappe.get_doc(data).insert(ignore_permissions=True)
        frappe.db.commit()
        return doc.name

    def _mk_user(self, email: str, roles: list[str]) -> str:
        """User fixture — parity test_imm00._mk_user (invalidate caps cache)."""
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        u = frappe.get_doc({
            "doctype": "User", "email": email,
            "first_name": email.split("@")[0], "send_welcome_email": 0,
            "user_type": "System User", "enabled": 1,
        }).insert(ignore_permissions=True)
        for r in roles:
            u.append("roles", {"role": r})
        u.flags.ignore_permissions = True
        u.save()
        from assetcore.services.shared import rbac as _rbac
        _rbac.invalidate_capabilities(email)
        self._users.append(email)
        frappe.db.commit()
        return email


class TestCheckAssetRecall(TestImm10Base):
    """TC-B1→B8 — shape verbatim §3b + quy tắc chọn rows + resolve token."""

    # ── TC-B1: asset có model dính 1 notice Active → has_recall true + row đủ 8 field ──
    def test_tc_b1_active_notice_returns_full_row(self):
        notice = self._mk_notice()
        env = check_asset_recall(asset=self.asset)
        self.assertIs(env["success"], True)
        data = env["data"]
        self.assertEqual(data["asset"], self.asset)
        # bool THẬT — không int-0/1 (Spec §3b).
        self.assertIs(data["has_recall"], True)
        self.assertEqual(len(data["recalls"]), 1)
        row = data["recalls"][0]
        self.assertEqual(set(row.keys()), _ROW_KEYS,
                         "Row recall PHẢI đúng 8 field verbatim §3b")
        self.assertEqual(row["name"], notice)
        self.assertEqual(row["title"], "Thu hồi bơm tiêm điện — lỗi driver liều")
        self.assertEqual(row["source"], "Manufacturer")
        self.assertEqual(row["severity"], "Class I")
        self.assertEqual(row["scope_note"], "Lô SX 2025-Q4, serial 1000–2000")
        self.assertEqual(row["reference_no"], "FSCA-2026-001")
        # Date phải là STRING 'YYYY-MM-DD' (không datetime.date object).
        self.assertEqual(row["published_date"], "2026-07-01")
        self.assertIsInstance(row["published_date"], str)

    # ── TC-B2: notice Closed cùng model → false / [] ──────────────────────────
    def test_tc_b2_closed_notice_excluded(self):
        self._mk_notice(status="Closed")
        env = check_asset_recall(asset=self.asset)
        self.assertIs(env["success"], True)
        self.assertIs(env["data"]["has_recall"], False)
        self.assertEqual(env["data"]["recalls"], [])

    # ── TC-B3: notice Active model KHÁC → false / [] ──────────────────────────
    def test_tc_b3_other_model_excluded(self):
        self._mk_notice(device_model=self.model_b)
        env = check_asset_recall(asset=self.asset)
        self.assertIs(env["success"], True)
        self.assertIs(env["data"]["has_recall"], False)
        self.assertEqual(env["data"]["recalls"], [])

    # ── TC-B4: asset không gán device_model → false / [] (success, KHÔNG lỗi) ──
    def test_tc_b4_asset_without_model_success_empty(self):
        self._mk_notice()  # notice Active model A tồn tại nhưng asset này không có model
        env = check_asset_recall(asset=self.asset_no_model)
        self.assertIs(env["success"], True)
        self.assertEqual(env["data"]["asset"], self.asset_no_model)
        self.assertIs(env["data"]["has_recall"], False)
        self.assertEqual(env["data"]["recalls"], [])

    # ── TC-B5: asset ∄ / token sai / cả hai rỗng → 404 leak-safe Decision-B ────
    def test_tc_b5_not_found_leak_safe(self):
        for kwargs in ({"asset": "AC-KHONG-TON-TAI-99999"},
                       {"token": "_khong-phai-token-hop-le"},
                       {}):
            env = check_asset_recall(**kwargs)
            self.assertIs(env["success"], False, f"phải fail với {kwargs}")
            self.assertEqual(env["code"], "NOT_FOUND",
                             f"code phải NOT_FOUND với {kwargs} (HTTP-200 Decision-B)")
            self.assertNotIn("data", env, "404 KHÔNG được leak payload")

    # ── TC-B7: 2 notice Active cùng model → 2 rows ORDER published_date DESC ───
    def test_tc_b7_two_notices_ordered_desc(self):
        older = self._mk_notice(published_date="2026-07-01",
                                title="Notice cũ", severity="Class II")
        newer = self._mk_notice(published_date="2026-07-10",
                                title="Notice mới", reference_no="FSCA-2026-002")
        env = check_asset_recall(asset=self.asset)
        self.assertIs(env["success"], True)
        rows = env["data"]["recalls"]
        self.assertEqual(len(rows), 2)
        self.assertEqual([r["name"] for r in rows], [newer, older],
                         "ORDER phải published_date DESC (mới nhất trước)")
        self.assertEqual([r["published_date"] for r in rows],
                         ["2026-07-10", "2026-07-01"])

    # ── TC-B8: gọi bằng token ≡ gọi bằng asset (resolve qua resolve_qr_token imm00) ──
    def test_tc_b8_token_equals_asset(self):
        self._mk_notice()
        env_token = check_asset_recall(token=self.qr_token)
        env_asset = check_asset_recall(asset=self.asset)
        self.assertIs(env_token["success"], True)
        self.assertEqual(env_token, env_asset,
                         "Response qua token PHẢI ≡ response qua asset-name")
        self.assertIs(env_token["data"]["has_recall"], True)


class TestCheckAssetRecallAuthz(TestImm10Base):
    """TC-B6 + TC-B9 — capability gate + IDOR vendor-scope."""

    # ── TC-B6: thiếu cap asset.read → FORBIDDEN (PermissionError propagate) ────
    def test_tc_b6_missing_cap_forbidden(self):
        nocap = self._mk_user("_test_imm10_nocap@assetcore.test", [])
        try:
            frappe.set_user(nocap)
            with self.assertRaises(frappe.PermissionError):
                check_asset_recall(asset=self.asset)
        finally:
            frappe.set_user("Administrator")

    # ── TC-B9: vendor ngoài phạm vi giao việc → FORBIDDEN envelope (IDOR) ──────
    def test_tc_b9_vendor_out_of_scope_forbidden(self):
        # Vendor Engineer + base role (đủ asset.read để qua gate ①) nhưng KHÔNG
        # được giao WO nào trên asset → assert_vendor_can_access chặn (403).
        vendor = self._mk_user("_test_imm10_vendor@assetcore.test",
                               ["AssetCore System User", "Vendor Engineer"])
        self._mk_notice()
        try:
            frappe.set_user(vendor)
            env = check_asset_recall(asset=self.asset)
        finally:
            frappe.set_user("Administrator")
        self.assertIs(env["success"], False)
        self.assertEqual(env["code"], "FORBIDDEN",
                         "Vendor ngoài scope phải nhận FORBIDDEN (IDOR guard)")
        self.assertNotIn("data", env, "FORBIDDEN KHÔNG được leak payload recall")
