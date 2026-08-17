# Copyright (c) 2026, AssetCore Team
"""RBAC hardening tests cho AC Purchase (Đơn mua hàng) — IMM-03 vòng 19.

Bối cảnh (ADR-IMM-03-05/06, 02 §IV.12): trước đây `create/update/delete` dùng
`ignore_permissions=True` và `mark_received` dùng `db_set` → MỌI user login (kể cả
AssetCore Auditor chỉ-đọc) tự Gửi duyệt / Xác nhận nhận hàng / Huỷ / Xoá đơn mua.
Fix: thêm capability `purchase.{read,write,create,delete,submit,cancel}` bind DocPerm
`AC Purchase`, gate `rbac.require(...)` là câu lệnh ĐẦU mỗi endpoint đổi-trạng-thái,
`mark_received` chuyển sang `doc.save()` (allow_on_submit) — KHÔNG `db_set`, và
`get_purchase` phát 6 cờ `can_*` server-derived (SoT gating FE).

Chạy: `bench --site miyano run-tests --module assetcore.tests.purchase.test_purchase`
"""
from __future__ import annotations

import inspect
import unittest

import frappe

from assetcore.api import purchase as api
from assetcore.services.shared import rbac
from frappe.tests.utils import FrappeTestCase

# Version đóng băng SAU khi thêm 6 cap purchase.* (bench-verified — KHÔNG bịa hash).
# Re-freeze AC-CR-119 +pm.read_history (AC-CR-119 · ADR-IMM00-ASSET-OP-HISTORY §11.2/§11.9): +1 cap
# pm.read_history bind ("PM Task Log","read") → 104→105 (bench-verified:
# `bench --site miyano execute assetcore.services.shared.rbac._compute_cap_set_version`
# → "v105.b50a24e5f62f"; KHÔNG gõ tay hash).
_EXPECTED_CAP_COUNT = 105
_EXPECTED_CAP_VERSION_PREFIX = "v105."


def _make_user(roles: list[str]) -> str:
    """Tạo test user với danh sách role. Trả về email."""
    email = f"_test_pur_{frappe.generate_hash()[:8]}@test.local"
    frappe.get_doc(
        {
            "doctype": "User",
            "email": email,
            "first_name": "TestPurRbac",
            "enabled": 1,
            "roles": [{"role": r} for r in roles],
        }
    ).insert(ignore_permissions=True)
    return email


# ─── TC-PUR-CAP — capability map + version stamp (AC3) ──────────────────────────

class TestPurchaseCapabilityMap(FrappeTestCase):
    """AC3 / INV-PUR-CAP: 6 cap purchase.* bind (AC Purchase, ptype); cap-set bump."""

    def test_purchase_submit_binding(self) -> None:
        self.assertIn("purchase.submit", rbac.CAPABILITY_MAP)
        self.assertEqual(
            rbac.CAPABILITY_MAP["purchase.submit"], ("AC Purchase", "submit")
        )

    def test_all_six_ptypes_bound(self) -> None:
        for pt in ("read", "write", "create", "delete", "submit", "cancel"):
            self.assertEqual(
                rbac.CAPABILITY_MAP.get(f"purchase.{pt}"), ("AC Purchase", pt),
                f"purchase.{pt} phải bind (AC Purchase, {pt})",
            )

    def test_cap_count_and_version_bump(self) -> None:
        self.assertEqual(
            len(rbac.CAPABILITY_MAP), _EXPECTED_CAP_COUNT,
            f"len(CAPABILITY_MAP)={len(rbac.CAPABILITY_MAP)} ≠ {_EXPECTED_CAP_COUNT}",
        )
        self.assertTrue(
            rbac.CAP_SET_VERSION.startswith(_EXPECTED_CAP_VERSION_PREFIX),
            f"CAP_SET_VERSION='{rbac.CAP_SET_VERSION}' phải prefix "
            f"'{_EXPECTED_CAP_VERSION_PREFIX}' (khác baseline cũ v98).",
        )

    def test_procurement_domain_untouched(self) -> None:
        """ADR-IMM-03-05: KHÔNG đụng domain Procurement (IMM Vendor Evaluation)."""
        self.assertEqual(
            rbac.CAPABILITY_MAP["procurement.submit"],
            ("IMM Vendor Evaluation", "submit"),
        )


# ─── TC-PUR-GATE — gate rbac.require TRƯỚC khi ghi (AC1, short-circuit) ──────────

class TestPurchaseGateShortCircuit(FrappeTestCase):
    """AC1: mỗi endpoint đổi-trạng-thái gọi rbac.require(cap) TRƯỚC khi ghi; thiếu
    quyền → PermissionError propagate (HTTP 403), KHÔNG có ghi/đổi trạng thái.

    Monkeypatch rbac.require (pattern test_imm01.py::test_create_calls_rbac_require_
    before_insert) — verify cap đúng + short-circuit, không cần seed data thật.
    """

    def setUp(self) -> None:
        frappe.set_user("Administrator")
        self._orig_require = rbac.require
        self.calls: list[str] = []

        def _fake(cap: str, doc=None) -> None:
            self.calls.append(cap)
            raise frappe.PermissionError("blocked for test")

        rbac.require = _fake

    def tearDown(self) -> None:
        rbac.require = self._orig_require
        frappe.set_user("Administrator")

    def test_create_gate_before_insert(self) -> None:
        before = frappe.db.count("AC Purchase")
        with self.assertRaises(frappe.PermissionError):
            api.create_purchase(payload='{"supplier":"_X","devices":[{"device_model":"_Y"}]}')
        self.assertEqual(self.calls[0], "purchase.create")
        self.assertEqual(frappe.db.count("AC Purchase"), before)

    def test_update_gate_before_write(self) -> None:
        with self.assertRaises(frappe.PermissionError):
            api.update_purchase("_no_such_po", payload='{"notes":"x"}')
        self.assertEqual(self.calls[0], "purchase.write")

    def test_submit_gate_before_write(self) -> None:
        with self.assertRaises(frappe.PermissionError):
            api.submit_purchase("_no_such_po")
        self.assertEqual(self.calls[0], "purchase.submit")

    def test_cancel_gate_before_write(self) -> None:
        with self.assertRaises(frappe.PermissionError):
            api.cancel_purchase("_no_such_po")
        self.assertEqual(self.calls[0], "purchase.cancel")

    def test_delete_gate_before_write(self) -> None:
        with self.assertRaises(frappe.PermissionError):
            api.delete_purchase("_no_such_po")
        self.assertEqual(self.calls[0], "purchase.delete")

    def test_mark_received_gate_before_write(self) -> None:
        with self.assertRaises(frappe.PermissionError):
            api.mark_received("_no_such_po")
        self.assertEqual(self.calls[0], "purchase.submit")

    def test_create_receipt_movement_gate(self) -> None:
        with self.assertRaises(frappe.PermissionError):
            api.create_receipt_movement("_no_such_po", "_WH")
        self.assertEqual(self.calls[0], "inventory.create")


# ─── TC-PUR-NODBSET — mark_received không còn db_set (AC2) ───────────────────────

class TestMarkReceivedNoDbSet(FrappeTestCase):
    """INV-PUR-NODBSET / AC2: mark_received chuyển sang doc.save() (Version audit),
    KHÔNG còn db_set bỏ qua permission."""

    def test_source_has_no_db_set_and_uses_save(self) -> None:
        src = inspect.getsource(api.mark_received)
        self.assertNotIn("db_set(", src, "mark_received KHÔNG được dùng db_set (AC2)")
        self.assertIn("doc.save()", src, "mark_received PHẢI dùng doc.save()")
        self.assertIn('rbac.require("purchase.submit")', src)


# ─── TC-PUR-AC6 / FLAGS — real-role enforcement + can_* flags (AC1/AC2/AC4/AC6) ──

class TestPurchaseRbacRealRoles(FrappeTestCase):
    """Enforcement THẬT theo DocPerm AC Purchase (không monkeypatch):
    - Auditor / Procurement User thiếu quyền → PermissionError (đóng lỗ bypass).
    - Super Admin (QTV) + Procurement Manager full flow OK (không false-restrictive).
    - get_purchase phát can_* đúng công thức state × cap (AC4).
    """

    @classmethod
    def setUpClass(cls) -> None:
        frappe.set_user("Administrator")
        cls.super_admin = _make_user(["AssetCore Super Admin"])
        cls.mgr = _make_user(["Procurement Manager"])
        cls.user = _make_user(["Procurement User"])
        cls.auditor = _make_user(["AssetCore Auditor"])

        # Supplier (reuse existing hoặc tạo)
        existing = frappe.get_all("AC Supplier", limit=1, pluck="name")
        if existing:
            cls.supplier = existing[0]
        else:
            d = frappe.get_doc({"doctype": "AC Supplier", "supplier_name": "_T-PUR-SUP"})
            d.insert(ignore_permissions=True)
            cls.supplier = d.name

        # Cần ≥1 device model hoặc spare part để thoả validate (≥1 device/item).
        model = frappe.get_all("IMM Device Model", limit=1, pluck="name")
        cls.model = model[0] if model else None
        spare = frappe.get_all("AC Spare Part", limit=1, pluck="name")
        cls.spare = spare[0] if spare else None
        cls.have_master = bool(cls.model or cls.spare)

        cls._pos: list[str] = []
        if cls.have_master:
            cls.draft_po = cls._mk_po(submit=False)
            cls.sub_po = cls._mk_po(submit=True)
        frappe.db.commit()

    @classmethod
    def _mk_po(cls, submit: bool) -> str:
        po = frappe.new_doc("AC Purchase")
        po.supplier = cls.supplier
        if cls.model:
            po.append("devices", {"device_model": cls.model, "qty": 1, "unit_cost": 1000})
        elif cls.spare:
            po.append("items", {"spare_part": cls.spare, "qty": 1, "unit_cost": 100})
        po.insert(ignore_permissions=True)
        if submit:
            po.submit()
        cls._pos.append(po.name)
        return po.name

    @classmethod
    def tearDownClass(cls) -> None:
        frappe.set_user("Administrator")
        for name in cls._pos:
            try:
                d = frappe.get_doc("AC Purchase", name)
                if d.docstatus == 1:
                    d.cancel()
                frappe.delete_doc("AC Purchase", name, force=True, ignore_permissions=True)
            except Exception:  # noqa: BLE001
                pass
        for email in (cls.super_admin, cls.mgr, cls.user, cls.auditor):
            try:
                frappe.delete_doc("User", email, force=True, ignore_permissions=True)
            except Exception:  # noqa: BLE001
                pass
        frappe.db.commit()

    def tearDown(self) -> None:
        frappe.set_user("Administrator")

    def _need_master(self) -> None:
        if not self.have_master:
            self.skipTest("Site thiếu IMM Device Model / AC Spare Part để dựng PO test")

    # ── Forbidden: đóng lỗ bypass (regression guards) ─────────────────────────

    def test_submit_forbidden_without_cap(self) -> None:
        """Auditor (read-only, submit=0) gọi submit_purchase(draft) → PermissionError.
        Regression: trước đây bypass qua submit không gate → lọt."""
        self._need_master()
        frappe.set_user(self.auditor)
        try:
            with self.assertRaises(frappe.PermissionError):
                api.submit_purchase(self.draft_po)
        finally:
            frappe.set_user("Administrator")
        # Không đổi trạng thái
        self.assertEqual(frappe.db.get_value("AC Purchase", self.draft_po, "docstatus"), 0)

    def test_mark_received_forbidden_for_procurement_user(self) -> None:
        """Procurement User (create/write, submit=0) gọi mark_received(submitted)
        → PermissionError (đóng lỗ db_set-bypass, AC2)."""
        self._need_master()
        frappe.set_user(self.user)
        try:
            with self.assertRaises(frappe.PermissionError):
                api.mark_received(self.sub_po)
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(frappe.db.get_value("AC Purchase", self.sub_po, "status"), "Submitted")

    def test_cancel_forbidden_for_procurement_user(self) -> None:
        self._need_master()
        frappe.set_user(self.user)
        try:
            with self.assertRaises(frappe.PermissionError):
                api.cancel_purchase(self.sub_po)
        finally:
            frappe.set_user("Administrator")

    def test_delete_forbidden_for_auditor(self) -> None:
        """Auditor (delete=0) gọi delete_purchase(draft) → PermissionError
        (đóng lỗ ignore_permissions)."""
        self._need_master()
        frappe.set_user(self.auditor)
        try:
            with self.assertRaises(frappe.PermissionError):
                api.delete_purchase(self.draft_po)
        finally:
            frappe.set_user("Administrator")
        self.assertTrue(frappe.db.exists("AC Purchase", self.draft_po))

    # ── Allowed: không hồi quy false-restrictive (AC6) ────────────────────────

    def test_super_admin_full_flow_allowed(self) -> None:
        """AssetCore Super Admin (QTV): create→submit→mark_received→cancel đều OK
        (root-cause 'đủ quyền nhưng không làm được' KHÔNG tái phát)."""
        self._need_master()
        payload = self._payload_json()
        frappe.set_user(self.super_admin)
        try:
            res = api.create_purchase(payload=payload)
            self.assertTrue(res["success"])
            name = res["data"]["name"]
            type(self)._pos.append(name)

            r_sub = api.submit_purchase(name)
            self.assertTrue(r_sub["success"])
            self.assertEqual(r_sub["data"]["status"], "Submitted")

            r_rec = api.mark_received(name)
            self.assertTrue(r_rec["success"])
            self.assertEqual(r_rec["data"]["status"], "Received")

            r_can = api.cancel_purchase(name)
            self.assertTrue(r_can["success"])
        finally:
            frappe.set_user("Administrator")

    def test_procurement_manager_full_flow_allowed(self) -> None:
        """Procurement Manager: create→submit→mark_received→cancel OK (AC6)."""
        self._need_master()
        payload = self._payload_json()
        frappe.set_user(self.mgr)
        try:
            res = api.create_purchase(payload=payload)
            name = res["data"]["name"]
            type(self)._pos.append(name)
            api.submit_purchase(name)
            self.assertEqual(api.mark_received(name)["data"]["status"], "Received")
            api.cancel_purchase(name)
        finally:
            frappe.set_user("Administrator")

    def test_procurement_user_can_create_but_not_submit(self) -> None:
        """Procurement User (create/write=1, submit=0): create OK; submit → 403
        (least-privilege đúng — AC6)."""
        self._need_master()
        payload = self._payload_json()
        frappe.set_user(self.user)
        try:
            res = api.create_purchase(payload=payload)
            self.assertTrue(res["success"])
            name = res["data"]["name"]
            type(self)._pos.append(name)
            with self.assertRaises(frappe.PermissionError):
                api.submit_purchase(name)
        finally:
            frappe.set_user("Administrator")

    # ── can_* flags (AC4) ─────────────────────────────────────────────────────

    def test_get_purchase_emits_can_flags(self) -> None:
        """AC4: get_purchase phát 6 cờ server-derived đúng công thức state × cap.
        - draft(authorized=Super Admin): can_submit True, can_receive/can_cancel False
        - submitted(authorized): can_receive/can_cancel True, can_submit False
        - auditor (read-only): cả 3 core cờ False.
        """
        self._need_master()

        # Draft, authorized (Super Admin)
        frappe.set_user(self.super_admin)
        try:
            d = api.get_purchase(self.draft_po)["data"]
        finally:
            frappe.set_user("Administrator")
        self.assertTrue(d["can_submit"])
        self.assertFalse(d["can_receive"])
        self.assertFalse(d["can_cancel"])
        self.assertTrue(d["can_edit"])
        self.assertTrue(d["can_delete"])
        self.assertIn("can_create_receipt", d)

        # Submitted, authorized (Super Admin)
        frappe.set_user(self.super_admin)
        try:
            s = api.get_purchase(self.sub_po)["data"]
        finally:
            frappe.set_user("Administrator")
        self.assertFalse(s["can_submit"])
        self.assertTrue(s["can_receive"])
        self.assertTrue(s["can_cancel"])
        self.assertFalse(s["can_edit"])
        self.assertFalse(s["can_delete"])

        # Auditor (read-only) — mọi cờ hành động False (least-privilege)
        frappe.set_user(self.auditor)
        try:
            a = api.get_purchase(self.sub_po)["data"]
        finally:
            frappe.set_user("Administrator")
        self.assertFalse(a["can_submit"])
        self.assertFalse(a["can_receive"])
        self.assertFalse(a["can_cancel"])
        self.assertFalse(a["can_edit"])
        self.assertFalse(a["can_delete"])

    def _payload_json(self) -> str:
        import json

        dev = [{"device_model": self.model, "unit_cost": 1000}] if self.model else []
        items = [] if self.model else [{"spare_part": self.spare, "qty": 1, "unit_cost": 100}]
        return json.dumps({"supplier": self.supplier, "devices": dev, "items": items})


if __name__ == "__main__":
    unittest.main()
