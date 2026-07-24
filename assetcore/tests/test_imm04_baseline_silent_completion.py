# Copyright (c) 2026, AssetCore Team
"""IMM-04 baseline checklist — silent-completion lens (guard proof).

Đề mục vòng: chặn Pass-giả khi 0 phép đo + UPSERT-by-parameter.

RECONCILE (doubt-driven): `submit_baseline_checklist` (service) tự nó KHÔNG guard
0-phép-đo, NHƯNG kết thúc bằng `doc.save()` ở state 'Initial Inspection' → controller
`AssetCommissioning.validate()` chạy `validate_checklist_completion()` (VR-03 + VR-03a)
CHẶN cả baseline rỗng lẫn dòng chưa có test_result. Đây là guard THẬT end-to-end.

Test này gọi TRỰC TIẾP method controller trên doc IN-MEMORY (get_doc, KHÔNG insert)
→ chạy đúng logic VR-03/VR-03a, KHÔNG ghi DB, KHÔNG rò fixture. Assert hành vi THẬT
(raise / không raise), KHÔNG proxy cấu trúc.

Chạy: bench --site miyano run-tests --app assetcore \
    --module assetcore.tests.test_imm04_baseline_silent_completion
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import frappe

_STATE_INITIAL = "Initial Inspection"
_STATE_RELEASE = "Clinical Release"


def _comm(workflow_state, rows):
    """Doc Asset Commissioning IN-MEMORY (chưa insert) với baseline_tests."""
    doc = frappe.get_doc({"doctype": "Asset Commissioning", "workflow_state": workflow_state})
    for r in rows:
        doc.append("baseline_tests", {
            "parameter": r.get("parameter", "P"),
            "test_result": r.get("test_result", ""),
            "measured_val": r.get("measured_val", ""),
            "fail_note": r.get("fail_note", ""),
        })
    return doc


class TestBaselineSilentCompletionGuard(unittest.TestCase):
    """VR-03/VR-03a = guard THẬT chặn Pass-giả khi 0 phép đo (controller-enforced)."""

    # ── VR-03: baseline rỗng bị chặn ở node Inspection ───────────────────────
    def test_empty_baseline_blocks_at_initial_inspection(self):
        doc = _comm(_STATE_INITIAL, [])
        with self.assertRaises(frappe.ValidationError):
            doc.validate_checklist_completion()

    def test_empty_baseline_blocks_at_clinical_release(self):
        doc = _comm(_STATE_RELEASE, [])
        with self.assertRaises(frappe.ValidationError):
            doc.validate_checklist_completion()

    # ── VR-03a: dòng chưa đo (test_result rỗng) bị chặn ──────────────────────
    def test_unmeasured_row_blocks(self):
        doc = _comm(_STATE_INITIAL, [
            {"parameter": "Điện trở nối đất", "test_result": "Pass", "measured_val": "0.1"},
            {"parameter": "Dòng rò vỏ máy"},  # chưa đo
        ])
        with self.assertRaises(frappe.ValidationError):
            doc.validate_checklist_completion()

    def test_all_unmeasured_rows_block(self):
        doc = _comm(_STATE_INITIAL, [
            {"parameter": "Điện trở nối đất"},
            {"parameter": "Dòng rò vỏ máy"},
        ])
        with self.assertRaises(frappe.ValidationError):
            doc.validate_checklist_completion()

    # ── Fail phải kèm ghi chú (VR-03a) ───────────────────────────────────────
    def test_fail_without_note_blocks(self):
        doc = _comm(_STATE_INITIAL, [
            {"parameter": "Dòng rò vỏ máy", "test_result": "Fail", "measured_val": "9.9"},
        ])
        with self.assertRaises(frappe.ValidationError):
            doc.validate_checklist_completion()

    # ── Positive: đo đủ, Pass/N-A → không raise ──────────────────────────────
    def test_all_measured_pass_or_na_ok(self):
        doc = _comm(_STATE_INITIAL, [
            {"parameter": "Điện trở nối đất", "test_result": "Pass", "measured_val": "0.1"},
            {"parameter": "Dòng rò vỏ máy", "test_result": "N/A"},
        ])
        doc.validate_checklist_completion()  # không raise

    # ── node ngoài Inspection thì bỏ qua (đúng thiết kế) ─────────────────────
    def test_non_inspection_state_skipped(self):
        doc = _comm("To Be Installed", [])
        doc.validate_checklist_completion()  # không raise


class TestBaselineUpsertAndCount(unittest.TestCase):
    """`submit_baseline_checklist` (SERVICE) — UPSERT-by-parameter + tests_recorded.

    Trước fix (agent R1 lỗi mid-stream, land nửa vời): loop chỉ update dòng
    ``baseline_tests`` có sẵn theo parameter → phép đo KTV tự thêm (parameter mới)
    bị DROP CÂM; return thiếu ``tests_recorded`` mà FE (api/imm04.ts) gate banner
    thành công → banner CHẾT với mọi user. Test drive ĐÚNG loop service (patch ranh
    giới persistence ``doc.save`` + ``check_auto_clinical_hold`` — KHÔNG phải chủ đề)."""

    def _run(self, seeded, payload):
        from assetcore.services import imm04 as svc
        doc = frappe.get_doc({"doctype": "Asset Commissioning",
                              "workflow_state": _STATE_INITIAL})
        for p in seeded:
            doc.append("baseline_tests", {"parameter": p})
        doc.save = MagicMock()  # bypass controller VR-03/G01 + DB (đã test riêng)
        with patch.object(svc.CommissioningRepo, "get", return_value=doc), \
             patch.object(svc, "check_auto_clinical_hold", return_value=False):
            res = svc.submit_baseline_checklist("X", payload)
        return doc, res

    def test_new_parameter_is_appended_not_dropped(self):
        doc, res = self._run(
            ["Điện trở nối đất"],
            [{"parameter": "Điện trở nối đất", "test_result": "Pass", "measured_val": "0.1"},
             {"parameter": "Dòng rò vỏ máy", "test_result": "Pass", "measured_val": "0.2"}],
        )
        params = [r.parameter for r in doc.baseline_tests]
        self.assertIn("Dòng rò vỏ máy", params,
                      "parameter KTV tự thêm phải APPEND (không drop câm)")
        self.assertEqual(len(doc.baseline_tests), 2)

    def test_returns_tests_recorded_real_count(self):
        _, res = self._run(
            [],
            [{"parameter": "P1", "test_result": "Pass", "measured_val": "1"},
             {"parameter": "P2", "test_result": "N/A"},
             {"parameter": "P3"}],  # chưa ghi test_result → KHÔNG đếm
        )
        self.assertEqual(res.get("tests_recorded"), 2,
                         "tests_recorded = số dòng THỰC có test_result (FE gate banner)")
        self.assertEqual(res["overall_result"], "Pass")


if __name__ == "__main__":
    unittest.main()
