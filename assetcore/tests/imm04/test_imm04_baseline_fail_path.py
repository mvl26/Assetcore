# Copyright (c) 2026, AssetCore Team
"""IMM-04 — Fail-path đo kiểm cơ sở: ghi nhận KHÔNG ĐẠT · Tái kiểm · gate G03 structured.

Core Doc: `docs/imm-04/04_Backend_Design.md §5.5` (BR-04-04e/f · BR-04-13 · BR-04-14 ·
ADR-IMM-04-04/05) + `07_Testing_QA.md §III.4d` (TC-04-BLFAIL-01..10).

Bug gốc (mobile Spec 58 / CR-54 §2):
  1. `submit_baseline_checklist` raise VALIDATION TRƯỚC `doc.save()` khi có dòng `Fail`
     ⇒ **0 dòng persist** ⇒ mất bằng chứng incoming inspection (WHO HTM §5.1.2 / NĐ98).
  2. State-guard chỉ cho `Initial Inspection` ⇒ phiếu vào `Re Inspection` là **kẹt vĩnh
     viễn** (không endpoint nào sửa được `baseline_tests`).
  3. Cổng an toàn G03 nằm ở hook save-time (`frappe.throw` → 417 câm, NGOÀI envelope
     Decision-B) thay vì pre-check ở ranh giới transition vào `Clinical Release`.

Flow THẬT (KHÔNG shortcut `db_set` workflow_state, trừ 1 TC ghi rõ lý do): phiếu insert ở
`Draft` → 5 transition qua `svc.transition_state` tới `Initial Inspection` → gọi service /
API layer. Re-get fresh bằng `CommissioningRepo.get(name)` để kiểm PERSIST.

Chạy:
    bench --site miyano run-tests --app assetcore \
        --module assetcore.tests.imm04.test_imm04_baseline_fail_path
"""
from __future__ import annotations

import unittest
from pathlib import Path

import frappe

from assetcore.repositories.commissioning_repo import CommissioningRepo
from assetcore.services import imm04 as svc
from assetcore.services.shared import ErrorCode, ServiceError
from frappe.tests.utils import FrappeTestCase

_DT = "Asset Commissioning"
_STATE_INITIAL = "Initial Inspection"
_STATE_RE_INSPECTION = "Re Inspection"
_GATE_G03_CODE = "IMM04-GATE-G03-BASELINE"
_GATE_G06_CODE = "IMM04-GATE-G06-APPROVER"

# Draft → Initial Inspection (khớp `imm_04_workflow.json`, đếm từ JSON — không đoán).
_PATH_TO_INITIAL = (
    "Gửi kiểm tra tài liệu",     # Draft → Pending Doc Verify
    "Xác nhận đủ tài liệu",      # Pending Doc Verify → To Be Installed
    "Bắt đầu lắp đặt",           # To Be Installed → Installing
    "Lắp đặt hoàn thành",        # Installing → Identification
    "Bắt đầu kiểm tra",          # Identification → Initial Inspection
)

_P_EARTH = "Điện trở nối đất bảo vệ"
_P_LEAK = "Dòng rò điện vỏ máy"
_P_ALARM = "Kiểm tra chức năng cảnh báo"


def _first_link(dt: str) -> str | None:
    names = frappe.get_all(dt, limit=1, pluck="name")
    return names[0] if names else None


class TestImm04BaselineFailPath(FrappeTestCase):
    """TC-04-BLFAIL-01..10 — AC1..AC6 của đề mục Fail-path baseline."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls._comms: list[str] = []
        cls._assets: list[str] = []
        cls.approver = "_test_imm04_blfail_approver@assetcore.test"
        if not frappe.db.exists("User", cls.approver):
            frappe.get_doc({
                "doctype": "User", "email": cls.approver, "first_name": "imm04blfail",
                "send_welcome_email": 0, "enabled": 1,
            }).insert(ignore_permissions=True)
        # Link bắt buộc của Asset Commissioning (po_reference / master_item / vendor):
        # `apply_workflow` → `doc.save()` re-validate mandatory ở MỖI hop ⇒ fixture
        # KHÔNG thể dựa vào `ignore_mandatory` lúc insert.
        cls.po = _first_link("AC Purchase")
        cls.vendor = _first_link("AC Supplier")
        # Idempotent pre-clean: một lần chạy trước bị ngắt (SIGTERM/timeout) SAU commit
        # nhưng TRƯỚC tearDownClass để lại category/model mồ côi. AC Asset Category có
        # autoname CAT-#### (name ≠ category_name) ⇒ phải quét theo `category_name`
        # (KHÔNG theo name). Model trỏ FK vào category ⇒ xoá model TRƯỚC. Không có →
        # no-op. Chống false-RED "Duplicate entry '_TEST BLFAIL Category'".
        for stale_model in frappe.get_all(
            "IMM Device Model", filters={"model_name": "_TEST BLFAIL Monitor"}, pluck="name"
        ):
            frappe.delete_doc("IMM Device Model", stale_model, force=True, ignore_permissions=True)
        for stale_cat in frappe.get_all(
            "AC Asset Category", filters={"category_name": "_TEST BLFAIL Category"}, pluck="name"
        ):
            frappe.delete_doc("AC Asset Category", stale_cat, force=True, ignore_permissions=True)
        cls._cat = frappe.get_doc({
            "doctype": "AC Asset Category", "category_name": "_TEST BLFAIL Category",
        }).insert(ignore_permissions=True)
        cls.model = frappe.get_doc({
            "doctype": "IMM Device Model",
            "model_name": "_TEST BLFAIL Monitor",
            "manufacturer": "_TEST BLFAIL Mfr",
            "asset_category": cls._cat.name,
            "medical_device_class": "Class II",   # → risk_class 'B' (không bức xạ)
        }).insert(ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for name in cls._comms:
            for dt, flt in (
                ("Asset QA Non Conformance", {"ref_commissioning": name}),
                ("IMM Audit Trail", {"ref_name": name}),
            ):
                try:
                    frappe.db.delete(dt, flt)
                except Exception:
                    pass
            try:
                frappe.db.set_value(_DT, name, "docstatus", 0)
                frappe.delete_doc(_DT, name, force=True, ignore_permissions=True)
            except Exception:
                pass
        if cls._assets:
            from assetcore.tests._helpers._asset_cleanup import purge_asset  # noqa: PLC0415
            for asset in cls._assets:
                try:
                    purge_asset(asset)
                except Exception:
                    pass
        for ref, dt in (
            (getattr(cls, "model", None), "IMM Device Model"),
            (getattr(cls, "_cat", None), "AC Asset Category"),
            (cls.approver, "User"),
        ):
            target = ref.name if hasattr(ref, "name") else ref
            if not target:
                continue
            try:
                frappe.delete_doc(dt, target, force=True, ignore_permissions=True)
            except Exception:
                pass
        frappe.db.commit()

    def setUp(self):
        if not (self.po and self.vendor):
            self.skipTest("Thiếu master data (AC Purchase / AC Supplier) để tạo phiếu hợp lệ")
        frappe.set_user("Administrator")

    # ── fixtures ──────────────────────────────────────────────────────────────
    def _insert_draft(self, rows: list[dict]) -> str:
        """Phiếu THẬT ở `Draft`. `documents_incomplete` bypass Gate G01 hợp lệ.

        `vendor_serial_no` để rỗng ⇒ VR-01 (unique serial) skip — tránh va chạm
        fixture giữa các lần chạy.
        """
        doc = frappe.get_doc({
            "doctype": _DT,
            "workflow_state": "Draft",
            "po_reference": self.po,
            "master_item": self.model.name,
            "vendor": self.vendor,
            "risk_class": "B",
            "is_radiation_device": 0,
            "documents_incomplete": 1,
            "documents_incomplete_note": "Hồ sơ CO/CQ bổ sung sau — fixture fail-path baseline.",
            "baseline_tests": rows,
        }).insert(ignore_permissions=True)
        frappe.db.commit()
        type(self)._comms.append(doc.name)
        return doc.name

    def _make_at_initial(self) -> str:
        """Phiếu ở `Initial Inspection` qua 5 transition THẬT (KHÔNG db_set).

        Baseline seed 3 dòng đã có `test_result` — điều kiện BẮT BUỘC của VR-03a để
        `apply_workflow` vào Initial Inspection save được (mọi dòng phải có kết quả).
        Đây chính là phiếu KTV mở ra để nhập lại số đo thực tế tại hiện trường.
        """
        name = self._insert_draft([
            {"parameter": _P_EARTH, "measured_val": "0.05", "unit": "Ohm", "test_result": "Pass"},
            {"parameter": _P_LEAK, "measured_val": "0.10", "unit": "mA", "test_result": "Pass"},
            {"parameter": _P_ALARM, "measured_val": "OK", "test_result": "Pass"},
        ])
        for action in _PATH_TO_INITIAL:
            svc.transition_state(name, action)
        self.assertEqual(
            frappe.db.get_value(_DT, name, "workflow_state"), _STATE_INITIAL,
            "fixture phải tới Initial Inspection bằng transition THẬT",
        )
        return name

    @staticmethod
    def _fail_payload() -> list[dict]:
        """3 phép đo hiện trường: 1 KHÔNG ĐẠT (kèm ghi chú) + 2 ĐẠT."""
        return [
            {"parameter": _P_LEAK, "measured_val": "9.9", "test_result": "Fail",
             "fail_note": "Vượt ngưỡng 0.5 mA theo IEC 60601-1"},
            {"parameter": _P_EARTH, "measured_val": "0.05", "test_result": "Pass"},
            {"parameter": _P_ALARM, "measured_val": "OK", "test_result": "Pass"},
        ]

    def _to_re_inspection(self, name: str) -> None:
        svc.transition_state(name, "Báo cáo lỗi baseline")

    # ── TC-04-BLFAIL-01 — AC1: dòng KHÔNG ĐẠT được PERSIST ────────────────────
    def test_submit_baseline_persists_fail_rows(self):
        name = self._make_at_initial()
        svc.submit_baseline_checklist(name, self._fail_payload())  # KHÔNG được raise

        doc = CommissioningRepo.get(name)
        row = next((r for r in doc.baseline_tests if r.parameter == _P_LEAK), None)
        self.assertIsNotNone(row, "dòng KHÔNG ĐẠT phải TỒN TẠI sau reload (bằng chứng NĐ98)")
        self.assertEqual(row.test_result, "Fail")
        self.assertEqual(str(row.measured_val), "9.9", "measured_val phải persist")
        self.assertTrue((row.fail_note or "").strip(), "fail_note phải persist")
        self.assertEqual(doc.overall_inspection_result, "Fail",
                         "verdict dẫn xuất phải là 'Fail' (KHÔNG 'Pass') — BR-04-04e")
        self.assertEqual(doc.workflow_state, _STATE_INITIAL,
                         "submit_baseline_checklist KHÔNG được đụng workflow_state")

    # ── TC-04-BLFAIL-02 — AC1: response 5-key ─────────────────────────────────
    def test_submit_baseline_response_contract(self):
        name = self._make_at_initial()
        res = svc.submit_baseline_checklist(name, self._fail_payload())

        self.assertEqual(res["overall_result"], "Fail")
        self.assertEqual(res["tests_recorded"], 3,
                         "tests_recorded = số dòng THỰC ghi test_result")
        self.assertEqual(res["failed_parameters"], [_P_LEAK])
        self.assertTrue(
            {"name", "overall_result", "tests_recorded", "failed_parameters",
             "clinical_hold_required"} <= set(res),
            "response phải đủ 5 key (BR-04-04f) — thiếu ⇒ banner FE/mobile chết",
        )

    # ── TC-04-BLFAIL-03 — AC2: nộp lại được ở Re Inspection ───────────────────
    def test_resubmit_allowed_in_re_inspection(self):
        name = self._make_at_initial()
        svc.submit_baseline_checklist(name, self._fail_payload())
        self._to_re_inspection(name)

        res = svc.submit_baseline_checklist(name, [
            {"parameter": _P_LEAK, "measured_val": "0.08", "test_result": "Pass", "fail_note": ""},
        ])
        self.assertEqual(res["overall_result"], "Pass")
        self.assertEqual(
            frappe.db.get_value(_DT, name, "workflow_state"), _STATE_RE_INSPECTION,
            "endpoint ghi nhận KHÔNG được tự chuyển trạng thái",
        )

    # ── TC-04-BLFAIL-04 — AC2: đo lại Fail→Pass, UPSERT không nhân đôi ────────
    def test_reinspection_upsert_flips_fail_to_pass(self):
        name = self._make_at_initial()
        svc.submit_baseline_checklist(name, self._fail_payload())
        self._to_re_inspection(name)

        res = svc.submit_baseline_checklist(name, [
            {"parameter": _P_LEAK, "measured_val": "0.08", "test_result": "Pass", "fail_note": ""},
        ])
        self.assertEqual(res["failed_parameters"], [])
        doc = CommissioningRepo.get(name)
        rows = [r for r in doc.baseline_tests if r.parameter == _P_LEAK]
        self.assertEqual(len(rows), 1, "UPSERT-by-parameter: KHÔNG append dòng trùng")
        self.assertEqual(rows[0].test_result, "Pass")
        self.assertEqual(doc.overall_inspection_result, "Pass")
        self.assertEqual(doc.workflow_state, _STATE_RE_INSPECTION)

    # ── TC-04-BLFAIL-05 — AC3: nút «Báo cáo lỗi baseline» hết chết ────────────
    def test_transition_to_re_inspection_with_fail_ok(self):
        from assetcore.api import imm04 as api

        name = self._make_at_initial()
        svc.submit_baseline_checklist(name, self._fail_payload())

        before = frappe.db.count("IMM Audit Trail", {
            "ref_doctype": _DT, "ref_name": name, "to_status": _STATE_RE_INSPECTION,
        })
        res = api.transition_state(name, "Báo cáo lỗi baseline")
        self.assertTrue(res.get("success"), f"envelope phải success — nhận: {res}")
        self.assertEqual(res["data"]["new_state"], _STATE_RE_INSPECTION)
        after = frappe.db.count("IMM Audit Trail", {
            "ref_doctype": _DT, "ref_name": name, "to_status": _STATE_RE_INSPECTION,
        })
        # SC#4: IMM-04 ghi audit vào `IMM Audit Trail` (hash-chain), KHÔNG child
        # `Asset Lifecycle Event` (doctype không khai bảng đó).
        self.assertEqual(after - before, 1, "transition phải sinh đúng 1 bản ghi audit")

    # ── TC-04-BLFAIL-06 — AC4: cổng KHÔNG nới (từ Initial Inspection) ─────────
    def test_clinical_release_blocked_from_initial_inspection(self):
        from assetcore.api import imm04 as api

        name = self._make_at_initial()
        svc.submit_baseline_checklist(name, self._fail_payload())

        res = api.transition_state(name, "Phê duyệt phát hành", board_approver=self.approver)
        self.assertFalse(res.get("success"), "còn dòng Fail ⇒ PHẢI bị chặn")
        self.assertEqual(res["code"], ErrorCode.VALIDATION)
        self.assertEqual(res["http_status"], 422, "KHÔNG được là 417 câm")
        self.assertEqual(res["message_code"], _GATE_G03_CODE)
        self.assertIn(_P_LEAK, res["context"]["failed"])
        doc = CommissioningRepo.get(name)
        self.assertEqual(doc.workflow_state, _STATE_INITIAL, "state KHÔNG được đổi")
        self.assertEqual(doc.docstatus, 0, "docstatus KHÔNG được đổi")
        self.assertFalse(doc.board_approver, "board_approver KHÔNG được ghi khi bị chặn")

    # ── TC-04-BLFAIL-07 — AC4: cổng KHÔNG nới (đường vòng qua Re Inspection) ──
    def test_clinical_release_blocked_from_re_inspection(self):
        from assetcore.api import imm04 as api

        name = self._make_at_initial()
        svc.submit_baseline_checklist(name, self._fail_payload())
        self._to_re_inspection(name)

        res = api.transition_state(name, "Phê duyệt sau tái kiểm", board_approver=self.approver)
        self.assertFalse(res.get("success"))
        self.assertEqual(res["message_code"], _GATE_G03_CODE)
        self.assertEqual(res["http_status"], 422)
        doc = CommissioningRepo.get(name)
        self.assertEqual(doc.workflow_state, _STATE_RE_INSPECTION)
        self.assertEqual(doc.docstatus, 0)

    # ── TC-04-BLFAIL-08 — AC4: G03 chạy TRƯỚC G06 ────────────────────────────
    def test_g03_precedes_g06_when_approver_missing(self):
        from assetcore.api import imm04 as api

        name = self._make_at_initial()
        svc.submit_baseline_checklist(name, self._fail_payload())

        res = api.transition_state(name, "Phê duyệt phát hành")  # KHÔNG cấp approver
        self.assertEqual(
            res["message_code"], _GATE_G03_CODE,
            "thiết bị chưa đạt đo kiểm thì không được hỏi người duyệt trước "
            f"(nhận {res.get('message_code')} — kỳ vọng {_GATE_G03_CODE})",
        )
        self.assertNotEqual(res["message_code"], _GATE_G06_CODE)

    # ── TC-04-BLFAIL-09 — AC5: guard silent-completion còn nguyên ─────────────
    def test_silent_completion_guard_intact(self):
        name = self._make_at_initial()
        with self.assertRaises(ServiceError) as ctx:
            svc.submit_baseline_checklist(name, [])
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
        self.assertIn("BR-04-04", ctx.exception.message)
        doc = CommissioningRepo.get(name)
        self.assertNotIn(doc.overall_inspection_result, ("Pass", "Fail"),
                         "0 phép đo ⇒ KHÔNG được set verdict (dù Pass hay Fail)")

    def test_silent_completion_guard_rows_without_verdict(self):
        """Biến thể: phiếu có dòng nhưng chưa ghi `test_result`, `results=[]`.

        Dùng `db_set` cho hop cuối vì VR-03a (`validate_checklist_completion`) CHẶN
        transition vào Initial Inspection khi còn dòng thiếu `test_result` — trạng thái
        này chỉ tồn tại được ở dữ liệu legacy, không tới được bằng flow thật.
        """
        name = self._insert_draft([{"parameter": _P_EARTH}, {"parameter": _P_LEAK}])
        frappe.db.set_value(_DT, name, "workflow_state", _STATE_INITIAL, update_modified=False)

        with self.assertRaises(ServiceError) as ctx:
            svc.submit_baseline_checklist(name, [{"parameter": _P_EARTH, "measured_val": "0.05"}])
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
        doc = CommissioningRepo.get(name)
        self.assertNotIn(doc.overall_inspection_result, ("Pass", "Fail"))
        self.assertFalse(
            [r for r in doc.baseline_tests if (r.measured_val or "")],
            "raise TRƯỚC doc.save() ⇒ KHÔNG được persist gì",
        )

    # ── TC-04-BLFAIL-10 — AC6: parity message-code BE ↔ FE ───────────────────
    def test_message_code_parity_be_fe(self):
        from assetcore.utils.messages import MESSAGES, MSG

        self.assertEqual(MSG.IMM04_GATE_G03_BASELINE, _GATE_G03_CODE)
        self.assertIn(MSG.IMM04_GATE_G03_BASELINE, MESSAGES)
        fe = Path(frappe.get_app_path("assetcore")).parent / "frontend/src/locales/messages.ts"
        text = fe.read_text(encoding="utf-8")
        for code in (_GATE_G03_CODE, "IMM09-SELF-INSPECT-FORBIDDEN"):
            self.assertIn(code, text,
                          f"{code} thiếu trong messages.ts ⇒ FE rơi về toast SYS-500 "
                          "(chạy `python scripts/gen_fe_messages.py`)")


if __name__ == "__main__":
    unittest.main()
