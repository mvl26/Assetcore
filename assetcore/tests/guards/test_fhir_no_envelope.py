# Copyright (c) 2026, AssetCore Team
"""Guard: nhánh FHIR KHÔNG được bọc envelope — SPEC §6.2, §13, §15 TC-3.

Class-of-bug đóng ở đây
------------------------
Bề mặt cũ trả ``{"success": true, "data": {...}}`` và đặt **mã lỗi trong thân HTTP
200**. FHIR đòi ngược lại: thân là resource TRẦN, mã lỗi ở **status line**.

Hai hợp đồng loại trừ nhau, nên rủi ro thật là ai đó "tiện tay" ``from
assetcore.utils.response import _ok`` trong một mapper — code chạy, test nghiệp vụ
xanh, và client FHIR lạ nhận về một thứ không phải resource. Không có compiler nào
bắt được; chỉ guard này bắt.
"""

from __future__ import annotations

import ast
import os
import re
import unittest

from assetcore.tests._helpers.paths import APP_ROOT, list_files, rel_repo

FHIR_DIR = os.path.join(APP_ROOT, "fhir")

#: Import bị cấm tuyệt đối dưới ``assetcore/fhir/``.
FORBIDDEN_IMPORT = re.compile(
    r"^\s*(from\s+assetcore\.utils\.response\s+import|import\s+assetcore\.utils\.response)",
    re.M,
)

#: Khoá envelope — dò bằng AST chứ KHÔNG bằng regex trên văn bản.
#:
#: Bài học ngay tại chỗ này: bản regex đầu tiên bắt chính docstring của guard —
#: nơi trích ``{"success": ...}`` làm VÍ DỤ PHẢN DIỆN. Guard soi văn bản thì không
#: phân biệt được "mã dựng envelope" với "câu văn nói về envelope". AST thì có:
#: nó chỉ thấy khoá dict thật.
ENVELOPE_KEYS = frozenset({"success"})


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class TestFhirNoEnvelope(unittest.TestCase):
    """Bề mặt FHIR trả resource trần, không envelope."""

    def test_fhir_package_exists_and_is_populated(self):
        """Chốt dân số — gói rỗng thì mọi khẳng định dưới đây đúng-rỗng-tuếch."""
        files = list_files(FHIR_DIR, ".py", min_count=6, skip=("__pycache__",))
        self.assertGreaterEqual(len(files), 6)

    def test_no_file_under_fhir_imports_utils_response(self):
        """``utils/response.py`` là envelope của bề mặt CŨ — cấm dùng ở nhánh FHIR."""
        offenders = []
        for p in list_files(FHIR_DIR, ".py", min_count=6, skip=("__pycache__",)):
            if FORBIDDEN_IMPORT.search(_read(p)):
                offenders.append(rel_repo(p))
        self.assertEqual(
            offenders, [],
            "File dưới `assetcore/fhir/` import `utils/response.py` ⇒ sẽ bọc envelope "
            "quanh resource. FHIR CẤM bọc resource (SPEC §6.2). Dùng "
            "`assetcore.fhir.response` — nó trả resource trần + OperationOutcome.",
        )

    def test_no_success_key_built_under_fhir(self):
        """0 chỗ dựng khoá ``success`` — dấu hiệu chắc chắn của envelope."""
        offenders = []
        for p in list_files(FHIR_DIR, ".py", min_count=6, skip=("__pycache__",)):
            tree = ast.parse(_read(p))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Dict):
                    continue
                for key in node.keys:
                    if isinstance(key, ast.Constant) and key.value in ENVELOPE_KEYS:
                        offenders.append(f"{rel_repo(p)}:{key.lineno} — khoá {key.value!r}")
        self.assertEqual(
            offenders, [],
            "Nhánh FHIR dựng khoá `success` ⇒ đang bọc envelope. Resource phải TRẦN.",
        )

    def test_error_path_sets_real_http_status(self):
        """Lỗi phải ở **status line**, không nằm trong thân HTTP 200.

        Đây là lỗi đã trả giá thật ở bề mặt cũ: bộ sinh mã client đọc status-line
        để định tuyến lỗi, thấy 200 thì coi là thành công rồi vỡ ở bước parse.
        """
        src = _read(os.path.join(FHIR_DIR, "response.py"))
        self.assertIn(
            'frappe.local.response["http_status_code"]', src,
            "`fhir_error` phải đặt HTTP status thật — client FHIR đọc status line, "
            "không đọc khoá trong thân.",
        )
