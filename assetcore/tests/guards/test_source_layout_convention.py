# Copyright (c) 2026, AssetCore Team
"""Cưỡng chế vị trí & tên file NGUỒN của BE — SSoT văn bản: skill ``assetcore-structure``.

Vì sao có file này
------------------
``test_test_layout_convention.py`` chỉ canh file **test**. File **nguồn** thì tới nay mới
chỉ có rule bằng văn bản trong skill — mà bài học của cả đợt chuẩn hoá này là *rule văn
bản luôn bị bỏ qua*. Guard này khoá phần còn lại:

* **S1** — 3-tier: file trong ``api/`` không được chạm DB thẳng.
* **S2** — ranh giới một chiều ``utils/`` ⇄ ``services/**``.
* **S3** — script không được đặt tên ``test_*`` (``os.walk`` của Frappe sẽ nhặt làm test).
* **S4** — ``scripts/`` không có file lẻ ở gốc, phải vào ``seed/``·``uat/``·``maintenance/``.
* **S5** — ``patches/`` chỉ được thêm, không được bớt (đổi tên patch = chạy lại trên prod).

Nguyên tắc allowlist
--------------------
Nợ cũ nằm trong allowlist **ĐÓNG BĂNG, CHỈ-GIẢM** — guard tự đỏ nếu allowlist dài ra.
Muốn thêm một dòng thì việc cần làm là **sửa mã, không phải sửa sổ**.
"""

from __future__ import annotations

import ast
import os
import re
import unittest

from assetcore.tests._helpers.paths import (
    API_DIR,
    APP_ROOT,
    PATCHES_DIR,
    SCRIPTS_DIR,
    UTILS_DIR,
    list_files,
    rel_repo,
)

#: Tên hàm truy vấn gọi thẳng qua ``frappe.<x>()``.
_DIRECT_CALLS = frozenset({
    "get_doc", "new_doc", "get_all", "get_list", "get_value", "delete_doc", "get_cached_doc",
})
#: ``frappe.db.<x>()`` điều khiển GIAO DỊCH — không phải truy vấn dữ liệu, không tính nợ.
_TXN_CALLS = frozenset({"rollback", "commit", "savepoint"})


def count_db_calls(source: str) -> int:
    """Đếm lời gọi DB THẬT bằng AST.

    Vì sao AST chứ không regex: bản đầu tiên của guard này quét **văn bản** nên đếm
    cả chú thích. ``api/imm11.py:6`` có đúng dòng ``# KHÔNG gọi frappe.db.* hay
    frappe.get_doc trực tiếp`` — một lời nhắc TUÂN THỦ — và bị tính thành vi phạm.
    Kết quả: nợ công bố 607 trong khi nợ thật là 510; hai file (`imm11`, `imm14`)
    bị bêu oan dù vốn đã sạch.

    Cùng class-of-bug với guard FHIR no-envelope, phát hiện cùng đợt: **guard soi
    văn bản không phân biệt được "mã vi phạm" với "câu văn nói về vi phạm".**
    """
    hits = 0
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        if not isinstance(f, ast.Attribute):
            continue
        parent = f.value
        if (isinstance(parent, ast.Attribute) and parent.attr == "db"
                and isinstance(parent.value, ast.Name) and parent.value.id == "frappe"):
            if f.attr not in _TXN_CALLS:
                hits += 1
        elif (isinstance(parent, ast.Name) and parent.id == "frappe"
                and f.attr in _DIRECT_CALLS):
            hits += 1
        elif isinstance(parent, ast.Attribute) and parent.attr == "qb":
            hits += 1
    return hits

#: ĐÓNG BĂNG · CHỈ-GIẢM — file ``api/`` còn gọi DB thẳng (nợ 3-tier, SPEC BE §3.7).
#: Chuẩn tham chiếu: ``api/imm08.py`` và ``api/imm09.py`` = 0 lời gọi.
#: Uỷ quyền xuống ``services/`` thì XOÁ dòng; TUYỆT ĐỐI không thêm dòng mới.
S1_ALLOWLIST: dict[str, int] = {
    "imm00.py": 172,
    "inventory.py": 84,
    "imm03.py": 56,
    "user.py": 38,
    "imm01.py": 32,
    "imm02.py": 23,
    "auth.py": 22,
    "purchase.py": 18,
    "import_data.py": 17,
    "layout.py": 15,
    "dashboard.py": 14,
    "files.py": 5,
    "imm04.py": 5,
    "connections.py": 3,
    "mobile/preflight.py": 3,
}

#: Tổng ngân sách đóng băng — đo bằng AST 2026-08-18. CHỈ ĐƯỢC GIẢM.
#:
#: ⚠️ Mốc 607 công bố ngày 2026-08-14 đo bằng REGEX nên tính cả chú thích. Số thật
#: đo lại bằng AST là 510; nợ KHÔNG tự giảm — chỉ là phép đo trước đó sai.
S1_TOTAL_BUDGET = 507

#: Thư mục con hợp lệ của ``assetcore/scripts/``.
SCRIPT_HOMES = {"seed", "uat", "maintenance"}

#: Dân số tối thiểu của ``patches/`` — đo từ đĩa 2026-08-14. Tụt = patch bị xoá/đổi tên.
MIN_PATCH_FILES = 25


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _py_files(directory: str, min_count: int) -> list[str]:
    return [
        p for p in list_files(directory, ".py", min_count=min_count, skip=("__pycache__",))
        if os.path.basename(p) != "__init__.py"
    ]


class TestSourceLayoutConvention(unittest.TestCase):
    """S1–S5 — vị trí, tên và ranh giới tầng của file nguồn BE."""

    # ── S1 · 3-tier: api/ không chạm DB ───────────────────────────────────────
    def test_s1_allowlist_only_shrinks(self):
        """Sổ nợ 3-tier CHỈ được giảm — thêm dòng = nợ đang mọc thêm."""
        self.assertLessEqual(
            len(S1_ALLOWLIST), 15,
            "Allowlist S1 dài ra = có file `api/` MỚI gọi DB thẳng. "
            "Uỷ quyền xuống `services/` thay vì thêm dòng vào sổ.",
        )
        self.assertLessEqual(
            sum(S1_ALLOWLIST.values()), S1_TOTAL_BUDGET,
            "Tổng nợ 3-tier tăng. Ngân sách CHỈ ĐƯỢC GIẢM — mỗi lần đụng file `api/` "
            "là một cơ hội hạ số, không bao giờ nâng.",
        )

    def test_s1_allowlist_entries_are_real_and_not_growing(self):
        """Mỗi dòng trong sổ phải trỏ file CÓ THẬT, và số lời gọi KHÔNG được tăng."""
        for name, budget in S1_ALLOWLIST.items():
            path = os.path.join(API_DIR, name)
            self.assertTrue(os.path.isfile(path), f"Sổ S1 trỏ file không tồn tại: api/{name}")
            actual = count_db_calls(_read(path))
            self.assertLessEqual(
                actual, budget,
                f"api/{name} có {actual} lời gọi DB thẳng, vượt ngân sách đóng băng {budget}. "
                "Ngân sách CHỈ ĐƯỢC GIẢM — đẩy truy vấn xuống `services/`.",
            )

    def test_s1_api_layer_never_touches_db(self):
        """Tầng ``api/`` CHỈ validate + uỷ quyền. Mọi truy vấn thuộc ``services/``/``repositories/``.

        Chuẩn tham chiếu trong chính repo: ``api/imm08.py`` và ``api/imm09.py`` đạt **0**
        lời gọi — nên đây là mức đạt được, không phải lý tưởng suông.
        """
        offenders = []
        for p in _py_files(API_DIR, min_count=20):
            rel = os.path.relpath(p, API_DIR).replace(os.sep, "/")
            if rel in S1_ALLOWLIST:
                continue
            hits = count_db_calls(_read(p))
            if hits:
                offenders.append(f"api/{rel} — {hits} lời gọi DB thẳng")
        self.assertEqual(
            offenders, [],
            "File `api/` gọi thẳng DB ⇒ vi phạm 3-tier: logic rò lên tầng vận chuyển, "
            "không test được ở tầng service, và mọi endpoint phải tự lặp lại quy tắc. "
            "Đẩy truy vấn xuống `services/<module>.py`.",
        )

    # ── S2 · ranh giới utils/ ⇄ services/ ─────────────────────────────────────
    def test_s2_utils_never_imports_services_at_module_level(self):
        """``utils/`` là hạ tầng — CẤM import ``services/**`` ở cột 0 (sinh vòng lúc nạp module).

        Lazy-import BÊN TRONG hàm là lối thoát hợp lệ và không tạo vòng.
        """
        offenders = []
        for p in _py_files(UTILS_DIR, min_count=10):
            for i, line in enumerate(_read(p).splitlines(), 1):
                if re.match(r"(from|import)\s+assetcore\.services", line):
                    offenders.append(f"utils/{os.path.basename(p)}:{i} — {line.strip()}")
        self.assertEqual(
            offenders, [],
            "`utils/` import ngược lên `services/**` ⇒ vòng lặp import module-level. "
            "Thứ bị CẢ HAI tầng dùng phải nằm ở tầng THẤP hơn (`utils/`), rồi "
            "`services/shared/` re-export một chiều — đúng cách `ServiceError` đang làm.",
        )

    # ── S3 · script không được mang tên test_* ────────────────────────────────
    def test_s3_no_script_named_like_a_test(self):
        """``frappe/test_runner.py`` dùng ``os.walk`` toàn cây app.

        Bất kỳ ``test_*.py`` ở đâu cũng bị nhặt làm **test module** — kể cả trong
        ``scripts/``. Script phân tích phải đặt ``plan_*``/``check_*``/``scan_*``.
        """
        bad = []
        for root, dirs, files in os.walk(APP_ROOT):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            if root.startswith(os.path.join(APP_ROOT, "tests")):
                continue
            if os.sep + "doctype" + os.sep in root:
                continue
            bad += [rel_repo(os.path.join(root, f))
                    for f in files if f.startswith("test_") and f.endswith(".py")]
        self.assertEqual(
            bad, [],
            "File tên `test_*.py` nằm ngoài `tests/` và ngoài `doctype/<dt>/` ⇒ runner sẽ "
            "cố import nó như một test module. Đổi tiền tố (`plan_`/`check_`/`scan_`).",
        )

    # ── S4 · scripts/ không có file lẻ ở gốc ──────────────────────────────────
    def test_s4_scripts_are_grouped_by_purpose(self):
        """``scripts/`` chỉ có 3 nhà: ``seed/`` · ``uat/`` · ``maintenance/``.

        Trước lô B0 có **3 nhà script** rải rác và **14 file lẻ** ở gốc trùng mục đích
        với thư mục con đã tồn tại.
        """
        stray = [
            f for f in sorted(os.listdir(SCRIPTS_DIR))
            if f.endswith(".py") and f != "__init__.py"
            and os.path.isfile(os.path.join(SCRIPTS_DIR, f))
        ]
        self.assertEqual(
            stray, [],
            "File lẻ ở gốc `assetcore/scripts/` — phải vào `seed/`, `uat/` hoặc `maintenance/`.",
        )

        unexpected = [
            d for d in sorted(os.listdir(SCRIPTS_DIR))
            if os.path.isdir(os.path.join(SCRIPTS_DIR, d))
            and d not in SCRIPT_HOMES and d != "__pycache__"
        ]
        self.assertEqual(unexpected, [], "Thư mục con lạ trong `scripts/` — chỉ có seed/uat/maintenance.")

    # ── S5 · patches/ chỉ thêm, không bớt ─────────────────────────────────────
    def test_s5_patches_never_shrink(self):
        """Frappe nhận diện patch bằng **chuỗi dotted path** (``patch_handler.py:228``).

        Đổi tên/xoá một patch **đã chạy** ⇒ Frappe coi là patch mới ⇒ **chạy lại trên
        production**. Guard chỉ chốt dân số: số file patch không được TỤT.
        """
        files = list_files(PATCHES_DIR, ".py", min_count=MIN_PATCH_FILES, skip=("__pycache__",))
        self.assertGreaterEqual(
            len(files), MIN_PATCH_FILES,
            f"Số file `patches/` tụt dưới {MIN_PATCH_FILES} — patch bị xoá hoặc đổi tên. "
            "CẤM TUYỆT ĐỐI: patch đã chạy mà đổi tên sẽ chạy LẠI trên production.",
        )
