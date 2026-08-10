# Copyright (c) 2026, AssetCore Team
# IMM-15 §3.9 approve_forecast — fail-loud approval guard (TDD, RED-first).
#
# Bug gốc (services/imm15.py::approve_forecast):
#   - `try: doc.submit() except Exception: pass`  → NUỐT lỗi submit (duyệt-giả:
#     response báo "Approved" trong khi submit đã lỗi). Root-cause thực: controller
#     on_submit import `record_forecast_approval` — hàm KHÔNG tồn tại → mọi submit ném
#     ImportError, bị except:pass che.
#   - `if hasattr(doc, "workflow_state")`         → field-ảo (workflow_state LÀ schema
#     field chắc chắn của IMM Spare Part Forecast → guard thừa, che lỗi tương lai).
#   - KHÔNG guard BAD_STATE                       → re-approve doc đã submit ném raw
#     Frappe UpdateAfterSubmit (leak).
#   - return workflow_state HARDCODE "Approved"   → không phản ánh state THỰC persist.
#
# Acceptance:
#   AC1 happy — Draft(docstatus 0) → approve → reload DB: docstatus==1 &
#     workflow_state=='Approved' & approved_by==session.user; response.workflow_state
#     ĐỌC-LẠI từ DB (== saved.workflow_state), KHÔNG hardcode.
#   AC2 fail-loud (RED-first) — on_submit ném lỗi → RAISES ServiceError, KHÔNG success;
#     reload → docstatus==0 & workflow_state!='Approved' (rollback savepoint, không claim).
#   AC3 idempotent guard — approve lần 2 (đã Approved) → ServiceError(BAD_STATE), KHÔNG
#     rò UpdateAfterSubmit thô; docstatus giữ 1.
#   AC4 no-hardcode — response.workflow_state == SparePartForecastRepo.get().workflow_state.
#
# Isolation (R-9): seed 1 active spare part riêng; mỗi test track forecast tạo ra +
#   purge trong tearDown; tearDownClass dọn part/warehouse.
from __future__ import annotations

import unittest
from contextlib import suppress
from unittest import mock

import frappe

from assetcore.assetcore.doctype.imm_spare_part_forecast.imm_spare_part_forecast import (
    IMMSparePartForecast,
)
from assetcore.repositories.allocation_repo import SparePartForecastRepo
from assetcore.services import imm15 as svc
from assetcore.services.shared import ErrorCode, ServiceError

_PART_NAME = "_Test Part IMM15-APV"
_WH_NAME = "_Test WH IMM15-APV"


def _ensure_doc(doctype: str, lookup: dict, data: dict) -> str:
    existing = frappe.db.get_value(doctype, lookup, "name")
    if existing:
        return existing
    doc = frappe.get_doc({"doctype": doctype, **lookup, **data})
    doc.flags.ignore_links = True
    doc.flags.ignore_mandatory = True
    doc.insert(ignore_permissions=True)
    return doc.name


class TestApproveForecast(unittest.TestCase):
    """§3.9 approve_forecast — fail-loud + BAD_STATE guard + no-hardcode return."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        if not frappe.db.exists("AC UOM", "Cái"):
            with suppress(Exception):
                frappe.get_doc({"doctype": "AC UOM", "uom_name": "Cái",
                                "is_active": 1}).insert(ignore_permissions=True)
        any_uom = frappe.db.get_value("AC UOM", {}, "name") or None
        spare_data = {"unit_cost": 100000, "is_active": 1, "min_stock_level": 5,
                      "is_critical": 0}
        if any_uom:
            spare_data["stock_uom"] = any_uom
        cls.part = _ensure_doc("AC Spare Part", {"part_name": _PART_NAME}, spare_data)
        cls.warehouse = _ensure_doc("AC Warehouse", {"warehouse_name": _WH_NAME},
                                    {"is_active": 1})
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[str] = []

    def tearDown(self):
        for name in getattr(self, "_created", []):
            with suppress(Exception):
                fd = frappe.get_doc("IMM Spare Part Forecast", name)
                if fd.docstatus == 1:
                    fd.cancel()
                frappe.delete_doc("IMM Spare Part Forecast", name, force=True,
                                  ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        for dt, name in (("AC Spare Part", getattr(cls, "part", "")),
                         ("AC Warehouse", getattr(cls, "warehouse", ""))):
            if name:
                with suppress(Exception):
                    frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
        frappe.db.commit()

    # ── helpers ──────────────────────────────────────────────────────────────
    def _generate(self) -> str:
        """Tạo forecast Draft qua path THẬT (svc.generate_spare_forecast)."""
        res = svc.generate_spare_forecast(horizon_months=3, method="Moving_Avg")
        self._created.append(res["name"])
        return res["name"]

    # ── AC2 — RED-first: submit lỗi → fail-loud, KHÔNG claim duyệt ────────────
    def test_approve_forecast_submit_failure_fails_loud(self):
        name = self._generate()

        def _boom(self_doc):  # noqa: ANN001 — monkeypatch on_submit
            raise frappe.ValidationError("simulated on_submit failure")

        with mock.patch.object(IMMSparePartForecast, "on_submit", _boom):
            with self.assertRaises(ServiceError) as ctx:
                svc.approve_forecast(name)
        # Lỗi nghiệp vụ có code (không rò success)
        self.assertTrue(ctx.exception.code)
        # DB KHÔNG bị claim duyệt: rollback savepoint giữ Draft.
        saved = SparePartForecastRepo.get(name)
        self.assertEqual(saved.docstatus, 0,
                         "submit lỗi PHẢI rollback — docstatus giữ 0, không claim submit")
        self.assertNotEqual(saved.workflow_state, svc.ForecastState.APPROVED,
                            "submit lỗi PHẢI KHÔNG để workflow_state=='Approved'")

    # ── AC1 — happy: persist state THỰC, response đọc-lại DB ──────────────────
    def test_approve_forecast_draft_persists_real_state(self):
        name = self._generate()
        res = svc.approve_forecast(name)
        saved = SparePartForecastRepo.get(name)
        self.assertEqual(saved.docstatus, 1)
        self.assertEqual(saved.workflow_state, svc.ForecastState.APPROVED)
        self.assertEqual(saved.approved_by, frappe.session.user)
        self.assertEqual(res["workflow_state"], svc.ForecastState.APPROVED)
        # response đọc-lại từ DB (không hardcode)
        self.assertEqual(res["workflow_state"], saved.workflow_state)
        self.assertEqual(res.get("docstatus"), 1)

    # ── AC3 — idempotent guard: re-approve → BAD_STATE, no UpdateAfterSubmit ──
    def test_approve_forecast_already_approved_bad_state(self):
        name = self._generate()
        svc.approve_forecast(name)  # xanh 1 lần
        with self.assertRaises(ServiceError) as ctx:
            svc.approve_forecast(name)
        self.assertEqual(ctx.exception.code, ErrorCode.BAD_STATE)
        # KHÔNG rò lỗi Frappe UpdateAfterSubmit thô ra message nghiệp vụ.
        msg = str(ctx.exception.message or "")
        self.assertNotIn("UpdateAfterSubmit", msg)
        self.assertNotIn("after submission", msg.lower())
        # docstatus giữ nguyên 1.
        self.assertEqual(SparePartForecastRepo.get(name).docstatus, 1)

    # ── AC4 — no-hardcode guard (chống regress về hardcode "Approved") ────────
    def test_approve_forecast_return_not_hardcoded(self):
        name = self._generate()
        res = svc.approve_forecast(name)
        db_state = SparePartForecastRepo.get(name).workflow_state
        self.assertEqual(res["workflow_state"], db_state,
                         "response.workflow_state PHẢI == giá trị persist DB, KHÔNG hardcode")
