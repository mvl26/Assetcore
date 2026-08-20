# Copyright (c) 2026, AssetCore Team
"""IMM-00 scan-action — LEAN asset-action meta endpoint (over-fetch close).

Vòng 25 — `get_asset_action_meta(name)` cấp payload NẠC (least-privilege, NĐ98
data-minimization) cho 3 màn tạo WO (CM / Hiệu chuẩn / PM). Thay `get_asset`
(full doc rò gross_purchase_amount/accumulated_depreciation/current_book_value/
purchase_cost/salvage_value/qr_token/audit-chain) chỉ để render panel 5-6 field.

TDD viết TRƯỚC implement. Coverage:
  (1) keys-allowlist: payload == ĐÚNG 6 key {name, asset_name, device_model_name,
      lifecycle_status, risk_classification, location_name}; assertNotIn các field
      tài chính/nhạy cảm + KHÔNG audit-chain key.
  (2) 404 no-leak: name không tồn tại / rỗng / None → HTTP 404 _err (KHÔNG 500/
      traceback, KHÔNG full-scan).
  (3) enrich: asset có device_model+location+risk → *_name + risk_classification
      đúng; asset thiếu link → field '' (KHÔNG None vỡ FE).
  (4) IDOR/vendor: assert_vendor_can_access raise ServiceError → 403, KHÔNG leak
      payload (mock vendor ngoài scope).

Run:
    bench --site miyano run-tests --app assetcore \
        --module assetcore.tests.imm00.test_imm00_action_meta
"""
from __future__ import annotations

import time
import unittest
from unittest.mock import patch

import frappe

from assetcore.services.shared import ErrorCode, ServiceError
from frappe.tests.utils import FrappeTestCase


_UID = str(int(time.time()) % 100000)

# 6 key CỐ ĐỊNH — bất biến hợp đồng BE↔FE (panel meta thiết bị). Bất kỳ thừa/thiếu
# = FAIL (over-fetch tài chính đóng + FE không vỡ vì thiếu field).
_EXPECTED_KEYS = {
    "name",
    "asset_name",
    "device_model_name",
    "lifecycle_status",
    "risk_classification",
    "location_name",
}

# Field tài chính/nhạy cảm TUYỆT ĐỐI không được lọt qua đường meta nạc.
_FORBIDDEN_KEYS = {
    "gross_purchase_amount",
    "accumulated_depreciation",
    "current_book_value",
    "purchase_cost",
    "salvage_value",
    "qr_token",
    # audit-chain / opaque internal
    "prev_hash",
    "current_hash",
    "audit_hash",
}


def _insert_asset_bypass_workflow(data: dict):
    """Insert AC Asset bypassing workflow guard (BR-00-02) for fixtures."""
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    try:
        return frappe.get_doc(data).insert(ignore_permissions=True)
    finally:
        frappe.flags.in_install = prev


def setUpModule():
    frappe.set_user("Administrator")


class TestGetAssetActionMeta(FrappeTestCase):
    """get_asset_action_meta — lean meta payload cho màn tạo WO (scan-action)."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls._cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_code": f"_TestActMetaCat-{_UID}",
            "category_name": f"Thiết bị Chẩn đoán Hình ảnh (action-meta) {_UID}",
        }).insert(ignore_permissions=True)
        cls._loc = frappe.get_doc({
            "doctype": "AC Location",
            "location_name": f"_TestActMeta Khoa CĐHA {_UID}",
            "clinical_area_type": "Imaging",
        }).insert(ignore_permissions=True)
        cls._model = frappe.get_doc({
            "doctype": "IMM Device Model",
            "model_name": f"_TestActMeta Siemens Somatom {_UID}",
            "manufacturer": "Siemens (action-meta)",
            "medical_device_class": "Class III",
            "asset_category": cls._cat.name,
        }).insert(ignore_permissions=True)
        # Asset ĐẦY ĐỦ link (model + location) — verify enrich.
        cls._asset_full = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": f"_TestActMeta CT Full {_UID}",
            "asset_category": cls._cat.name,
            "device_model": cls._model.name,
            "location": cls._loc.name,
            "manufacturer_sn": f"_TestActMetaSN-full-{_UID}",
            "medical_device_class": "Class III",
            "risk_classification": "High",
            "purchase_date": "2024-03-15",
            "gross_purchase_amount": 12_000_000_000,
            "warranty_expiry_date": "2027-03-15",
            "in_service_date": "2024-03-20",
            "byt_reg_no": f"BYT-TB-2024-AM-full-{_UID}",
            "lifecycle_status": "Active",
        })
        # Asset THIẾU link (không model / không location) — verify field '' (KHÔNG None).
        cls._asset_bare = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": f"_TestActMeta Bare {_UID}",
            "asset_category": cls._cat.name,
            "manufacturer_sn": f"_TestActMetaSN-bare-{_UID}",
            "medical_device_class": "Class I",
            "risk_classification": "",
            "purchase_date": "2024-04-15",
            "gross_purchase_amount": 50_000_000,
            "warranty_expiry_date": "2027-04-15",
            "in_service_date": "2024-04-20",
            "byt_reg_no": f"BYT-TB-2024-AM-bare-{_UID}",
            "lifecycle_status": "Active",
        })
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for a in (cls._asset_full, cls._asset_bare):
            frappe.db.sql("DELETE FROM `tabIMM Audit Trail` WHERE asset=%s", (a.name,))
            frappe.db.sql("DELETE FROM `tabAsset Lifecycle Event` WHERE asset=%s", (a.name,))
            frappe.delete_doc("AC Asset", a.name, force=True, ignore_permissions=True)
        frappe.delete_doc("IMM Device Model", cls._model.name, force=True, ignore_permissions=True)
        frappe.delete_doc("AC Location", cls._loc.name, force=True, ignore_permissions=True)
        frappe.delete_doc("AC Asset Category", cls._cat.name, force=True, ignore_permissions=True)
        frappe.db.commit()

    # ─── (1) keys-allowlist ─────────────────────────────────────────────────
    def test_payload_has_exactly_six_keys(self):
        from assetcore.api.imm00 import get_asset_action_meta

        resp = get_asset_action_meta(self._asset_full.name)
        self.assertTrue(resp.get("success"), f"Endpoint failed: {resp}")
        data = resp["data"]
        self.assertEqual(
            set(data.keys()), _EXPECTED_KEYS,
            f"Payload keys phải == 6 key cố định. Got: {sorted(data.keys())}",
        )

    def test_payload_excludes_financial_and_sensitive_fields(self):
        from assetcore.api.imm00 import get_asset_action_meta

        data = get_asset_action_meta(self._asset_full.name)["data"]
        for forbidden in _FORBIDDEN_KEYS:
            self.assertNotIn(
                forbidden, data,
                f"Over-fetch leak: field nhạy cảm '{forbidden}' KHÔNG được có trong meta nạc.",
            )

    # ─── (3) enrich ─────────────────────────────────────────────────────────
    def test_enrich_resolves_model_location_risk(self):
        from assetcore.api.imm00 import get_asset_action_meta

        data = get_asset_action_meta(self._asset_full.name)["data"]
        self.assertEqual(data["name"], self._asset_full.name)
        self.assertEqual(data["asset_name"], self._asset_full.asset_name)
        self.assertEqual(data["device_model_name"], self._model.model_name)
        self.assertEqual(data["location_name"], self._loc.location_name)
        self.assertEqual(data["risk_classification"], "High")
        self.assertEqual(data["lifecycle_status"], "Active")

    def test_missing_links_yield_empty_string_not_none(self):
        from assetcore.api.imm00 import get_asset_action_meta

        data = get_asset_action_meta(self._asset_bare.name)["data"]
        # Thiếu link → '' (KHÔNG None — None vỡ FE render). risk_classification rỗng → ''.
        self.assertEqual(data["device_model_name"], "")
        self.assertEqual(data["location_name"], "")
        self.assertEqual(data["risk_classification"], "")
        self.assertIsNotNone(data["device_model_name"])
        self.assertIsNotNone(data["location_name"])
        self.assertIsNotNone(data["risk_classification"])

    # ─── (2) 404 no-leak ────────────────────────────────────────────────────
    def test_nonexistent_name_returns_404(self):
        from assetcore.api.imm00 import get_asset_action_meta

        resp = get_asset_action_meta(f"AC-ASSET-NOPE-{_UID}")
        self.assertFalse(resp.get("success"))
        self.assertEqual(resp.get("http_status"), 404)

    def test_empty_name_returns_404_no_leak(self):
        from assetcore.api.imm00 import get_asset_action_meta

        resp = get_asset_action_meta("")
        self.assertFalse(resp.get("success"))
        self.assertEqual(resp.get("http_status"), 404)

    def test_none_name_returns_404_no_leak(self):
        from assetcore.api.imm00 import get_asset_action_meta

        # Over HTTP, Frappe @whitelist validator coerce GET param về str (None KHÔNG
        # bao giờ tới body — param vắng = default ''). Test None-safety của THÂN hàm
        # qua __wrapped__ (bỏ qua type-validator) → body coerce None → '' → 404
        # no-leak (KHÔNG 500/traceback). Đảm bảo defensive in-body guard tồn tại.
        body = getattr(get_asset_action_meta, "__wrapped__", get_asset_action_meta)
        resp = body(None)
        self.assertFalse(resp.get("success"))
        self.assertEqual(resp.get("http_status"), 404)

    # ─── (4) IDOR/vendor ────────────────────────────────────────────────────
    def test_vendor_idor_returns_403_no_payload_leak(self):
        from assetcore.api import imm00 as api

        def _raise_forbidden(doctype, name, *a, **kw):
            raise ServiceError(
                ErrorCode.FORBIDDEN,
                "Bạn không có quyền truy cập tài sản này (không được giao việc).",
            )

        with patch.object(api, "assert_vendor_can_access", side_effect=_raise_forbidden):
            resp = api.get_asset_action_meta(self._asset_full.name)
        self.assertFalse(resp.get("success"))
        self.assertEqual(resp.get("http_status"), 403)
        # KHÔNG leak payload: không có key 'data' chứa field asset.
        self.assertNotIn("device_model_name", resp)
        self.assertNotIn("asset_name", resp)

    # NOTE (Vòng 35): Bộ test capability-gate-TRƯỚC-existence (bịt existence-oracle,
    # parity get_asset Vòng 34) là SSoT ở
    # assetcore.tests.test_imm00.TestGetAssetActionMetaRequiresAssetReadCapability
    # (5 case: requires_asset_read_capability / capability_gate_before_existence /
    # allows_user_with_asset_read / no_overfetch_financial /
    # empty_name_still_404_for_privileged). KHÔNG nhân bản ở đây để tránh drift
    # fixture (risk_classification options, _err envelope key) giữa 2 file.


if __name__ == "__main__":
    unittest.main()
