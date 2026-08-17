# Copyright (c) 2026, AssetCore Team
"""TDD — IMM-16 BR: phiếu chấm điểm tuân thủ phải tự đánh số theo chuỗi.

Bối cảnh (phát hiện 2026-08-14 khi chạy 5 vòng test toàn hệ thống):
``imm_compliance_scorecard.json`` khai ``autoname: "format:SCR-.YYYY.-.MM.-.#####"``.
Tiền tố ``format:`` của Frappe KHÔNG giãn token chuỗi kiểu ``.YYYY.``/``.#####``
(đó là cú pháp naming-series) — nó chỉ nội suy ``{fieldname}``. Hệ quả: MỌI bản
ghi lấy nguyên chuỗi thô ``SCR-.YYYY.-.MM.-.#####`` làm khoá chính ⇒ bản ghi thứ
hai trở đi ném ``DuplicateEntryError`` ⇒ tính năng chấm điểm tuân thủ chết hẳn.

Bằng chứng lúc phát hiện: bảng ``tabIMM Compliance Scorecard`` trên site có đúng
1 dòng, tên literal ``SCR-.YYYY.-.MM.-.#####`` (tạo 2026-08-10 17:14), và 9 test
IMM-16 error vì đúng lỗi này.

Phủ:
  - TC-SCR-NAME-01: hai phiếu liên tiếp phải có tên KHÁC nhau, đúng khuôn
    ``SCR-<năm>-<tháng>-<5 số>`` (hành vi — RED trước khi sửa autoname).
  - TC-SCR-NAME-02: guard toàn kho — KHÔNG DocType nào được trộn ``format:``
    với token chuỗi ``.YYYY.``/``.MM.``/``.#####`` (chống tái phát ở DocType khác).
"""
from __future__ import annotations

import glob
import json
import os
import re

import frappe
from frappe.tests.utils import FrappeTestCase

_DT = "IMM Compliance Scorecard"
#: Khuôn tên kỳ vọng khi naming-series giãn đúng: SCR-2026-08-00001.
_NAME_RE = re.compile(r"^SCR-\d{4}-\d{2}-\d{5}$")
#: Token chuỗi (series) — chỉ hợp lệ trong autoname KHÔNG có tiền tố ``format:``.
_SERIES_TOKEN_RE = re.compile(r"\.(?:YYYY|YY|MM|DD|WW|#+)\.")


class TestScorecardAutoname(FrappeTestCase):
    """TC-SCR-NAME-01 — tên tự sinh phải duy nhất theo chuỗi."""

    def setUp(self):
        self._created: list[str] = []

    def tearDown(self):
        # R-9: fixture tự dọn — phiếu chấm điểm không có on_trash guard.
        for n in self._created:
            if frappe.db.exists(_DT, n):
                frappe.delete_doc(_DT, n, force=True, ignore_permissions=True)
        frappe.db.commit()

    def _new_scorecard(self):
        doc = frappe.get_doc({
            "doctype": _DT,
            "period_year": 2026,
            "period_month": 8,
            "scope": "Hospital",
        }).insert(ignore_permissions=True)
        self._created.append(doc.name)
        return doc

    def test_two_scorecards_get_distinct_series_names(self):
        first = self._new_scorecard()
        second = self._new_scorecard()

        self.assertRegex(
            first.name, _NAME_RE,
            f"Tên phiếu KHÔNG theo chuỗi đã khai: {first.name!r}. Dấu hiệu autoname "
            f"'format:' nuốt token .YYYY./.MM./.#####",
        )
        self.assertRegex(second.name, _NAME_RE, f"Tên phiếu thứ hai sai khuôn: {second.name!r}")
        self.assertNotEqual(
            first.name, second.name,
            "Hai phiếu chấm điểm trùng khoá chính ⇒ bản ghi thứ hai luôn ném "
            "DuplicateEntryError ⇒ không thể chấm điểm tuân thủ lần thứ hai.",
        )


class TestAutonameSyntaxGuard(FrappeTestCase):
    """TC-SCR-NAME-02 — guard kho DocType: không trộn ``format:`` với token chuỗi."""

    def test_no_doctype_mixes_format_prefix_with_series_tokens(self):
        app = frappe.get_app_path("assetcore")
        paths = [
            p for p in glob.glob(os.path.join(app, "**", "doctype", "*", "*.json"),
                                 recursive=True)
            if os.path.basename(p)[:-5] == os.path.basename(os.path.dirname(p))
        ]
        # Chốt dân số: kho DocType rỗng ⇒ guard khẳng định "sạch" một cách rỗng tuếch.
        self.assertGreater(len(paths), 20,
                           f"Chỉ thấy {len(paths)} DocType JSON — bộ quét đã trỏ sai chỗ, "
                           f"kết luận 'không vi phạm' sẽ vô nghĩa.")

        offenders = []
        for p in paths:
            with open(p, encoding="utf-8") as fh:
                j = json.load(fh)
            autoname = j.get("autoname") or ""
            if autoname.startswith("format:") and _SERIES_TOKEN_RE.search(autoname):
                offenders.append(f"{j.get('name')}: {autoname}")

        self.assertEqual(
            offenders, [],
            "DocType trộn 'format:' với token chuỗi (.YYYY./.MM./.#####). Frappe CHỈ "
            "nội suy {fieldname} trong 'format:' ⇒ mọi bản ghi trùng đúng một tên thô. "
            "Bỏ tiền tố 'format:' để dùng naming-series.",
        )
