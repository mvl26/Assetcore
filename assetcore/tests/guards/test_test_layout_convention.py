# Copyright (c) 2026, AssetCore Team
"""SSoT CƯỠNG CHẾ bố cục & tên file test BE — SPEC ``docs/architecture/SPEC_chuan_hoa_cau_truc_backend.md`` §7.1.

Vì sao có file này
------------------
Rule bằng văn bản (skill, CLAUDE.md) dễ bị bỏ qua — người quên, mô hình quên.
File này là lớp thứ hai: nó ĐỎ ngay trong lượt chạy suite khi ai đó đặt test sai
chỗ, sai tên, hoặc ghi DB mà không rollback.

Backend không có ``vue-tsc``. Với FE, mọi lỗi dời import đều bị compiler bắt;
Python thì không — nên guard này gánh phần việc đó.

Bốn nhà, không có nhà thứ năm (§5.1)
-------------------------------------
1. ``assetcore/assetcore/doctype/<dt>/test_<dt>.py`` — test của chính DocType (chuẩn Frappe).
2. ``assetcore/tests/<module>/test_<module>[_<khia_canh>].py`` — test một module ``services/``/``api/``.
3. ``assetcore/tests/guards/test_<chu_de>.py`` — guard/parity/lint, không cần DB.
4. ``assetcore/tests/integration/test_<luong>.py`` — cắt ngang ≥2 module.

Nguyên tắc allowlist
--------------------
Mọi ngoại lệ tồn dư nằm trong allowlist **ĐÓNG BĂNG, CHỈ-GIẢM**: guard tự đỏ nếu
allowlist DÀI RA. Muốn thêm một dòng thì việc cần làm là sửa mã, không phải sửa sổ.
"""

from __future__ import annotations

import ast
import os
import re
import unittest

from assetcore.tests._helpers.paths import (
    API_DIR,
    APP_ROOT,
    DOCTYPE_DIR,
    PATCHES_DIR,
    SERVICES_DIR,
    TESTS_DIR,
    UTILS_DIR,
    list_files,
    rel_repo,
)

#: Nhà chuyên biệt trong ``tests/`` — không phải tên module services/api.
SPECIAL_HOMES = {"guards", "integration", "_helpers"}

#: Thư mục hạ tầng của bản thân bộ test — không chứa file test.
NON_TEST_DIRS = {"_helpers", "__pycache__"}

#: Hàm ghi DB gọi thẳng qua ``frappe.<x>()``.
_WRITE_CALLS = frozenset({"get_doc", "new_doc", "delete_doc"})
#: Hàm ghi qua ``frappe.db.<x>()``.
_DB_WRITE_CALLS = frozenset({"set_value", "insert", "delete", "sql"})


def writes_db(source: str) -> bool:
    """Có ghi DB không — dò bằng AST, KHÔNG bằng regex trên văn bản.

    Vì sao AST: bản regex của guard này bắt chính
    ``guards/test_source_layout_convention.py`` — file đó có docstring TRÍCH
    ``frappe.get_doc`` để **giải thích** lỗi đếm-văn-bản. Guard soi văn bản không
    phân biệt được "mã ghi DB" với "câu văn nói về ghi DB".

    Đây là lần thứ BA cùng một class-of-bug trong một đợt (guard FHIR no-envelope ·
    bộ đếm nợ 3-tier · guard này). Luật rút ra: **mọi guard soi mã Python phải dùng
    AST**; regex chỉ dùng cho thứ không parse được (tên file, đường dẫn).
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        if not isinstance(f, ast.Attribute):
            continue
        parent = f.value
        if isinstance(parent, ast.Name) and parent.id == "frappe" and f.attr in _WRITE_CALLS:
            return True
        if (isinstance(parent, ast.Attribute) and parent.attr == "db"
                and isinstance(parent.value, ast.Name) and parent.value.id == "frappe"
                and f.attr in _DB_WRITE_CALLS):
            return True
    return False
SCANS_DIR = re.compile(r"os\.walk|glob\.|listdir|list_files")
POPULATION_LOCKED = re.compile(r"assertGreater|min_count\s*=\s*\d+|assertEqual\(\s*len\(")

#: ĐÓNG BĂNG · CHỈ-GIẢM — file còn ghi DB mà lớp cơ sở không phải ``FrappeTestCase``.
#: Lô B4 đã đưa 68 file về ``FrappeTestCase``; sổ này giữ phần chưa xử lý được.
#: Xoá dòng khi đã chuyển; TUYỆT ĐỐI không thêm dòng mới.
K7_ALLOWLIST: frozenset[str] = frozenset()
K7_FROZEN_SIZE = 0

#: ĐÓNG BĂNG · CHỈ-GIẢM — file quét thư mục nhưng nằm ngoài ``tests/guards/``.
#:
#: Đây là các test **của một module** có kèm một đoạn quét cây (vd
#: ``test_imm00_reserved_prefix`` quét toàn app tìm tiền tố dành riêng). Chúng
#: vừa ghi DB vừa quét đĩa nên không thuộc hẳn nhà #3. Sổ ĐÓNG BĂNG ở 9:
#: tách phần quét ra ``tests/guards/`` thì XOÁ dòng; TUYỆT ĐỐI không thêm dòng.
K5_ALLOWLIST: frozenset[str] = frozenset({
    "connections/test_connections_tree.py",
    "depreciation/test_depreciation.py",
    "imm00/test_imm00_byt_expiry.py",
    "imm00/test_imm00_reserved_prefix.py",
    "imm06/test_imm06.py",
    "imm15/test_imm15.py",
    "imm16/test_imm16_scorecard_naming.py",
    "integration/test_attachment_upload.py",
    "integration/test_rbac.py",
})
K5_FROZEN_SIZE = 9


def _all_test_files() -> list[str]:
    """Mọi file ``test_*.py`` trong ``assetcore/tests`` — chốt dân số (§5.2 N5).

    ``list_files`` lọc theo HẬU TỐ nên phải lọc tiền tố ``test_`` sau.
    """
    files = list_files(TESTS_DIR, ".py", min_count=100, skip=("__pycache__",))
    return [p for p in files if os.path.basename(p).startswith("test_")]


def _module_names() -> set[str]:
    mods = set()
    for d in (SERVICES_DIR, API_DIR):
        for f in os.listdir(d):
            if f.endswith(".py") and f != "__init__.py":
                mods.add(f[:-3])
    return mods


def _rel_tests(path: str) -> str:
    return os.path.relpath(path, TESTS_DIR).replace(os.sep, "/")


class TestTestLayoutConvention(unittest.TestCase):
    """K1–K9 — bố cục, tên, và kỷ luật rollback của bộ test BE."""

    # ── K1 · Có nhà hợp lệ ────────────────────────────────────────────────────
    def test_k1_no_test_file_at_tests_root(self):
        """Gốc ``assetcore/tests/`` phải RỖNG file test — mọi test thuộc 1 trong 4 nhà."""
        stray = [
            f for f in os.listdir(TESTS_DIR)
            if f.startswith("test_") and f.endswith(".py")
            and os.path.isfile(os.path.join(TESTS_DIR, f))
        ]
        self.assertEqual(
            stray, [],
            "File test nằm ở gốc `assetcore/tests/` — phải vào `tests/<module>/`, "
            "`tests/guards/` hoặc `tests/integration/` (SPEC §5.1).",
        )

    def test_k2_module_dir_matches_a_real_module(self):
        """``tests/<X>/`` phải ứng với ``services/<X>.py`` hoặc ``api/<X>.py`` có thật."""
        mods = _module_names()
        extra = {"utils", "mobile", "mobile_device_token", "import_data",
                 "connections", "depreciation", "notifications", "dashboard"}
        bad = []
        for name in sorted(os.listdir(TESTS_DIR)):
            full = os.path.join(TESTS_DIR, name)
            if not os.path.isdir(full) or name in SPECIAL_HOMES or name in NON_TEST_DIRS:
                continue
            if name not in mods and name not in extra:
                bad.append(name)
        self.assertEqual(
            bad, [],
            "Thư mục `tests/<X>/` không ứng với module `services/<X>.py`/`api/<X>.py` nào. "
            "Đặt test vào đúng module, hoặc dùng `tests/integration/` nếu cắt ngang nhiều lát.",
        )

    def test_k4_every_subdir_has_init(self):
        """R2 — thiếu ``__init__.py`` thì ``--module`` gãy (runner dựng tên từ đường dẫn)."""
        missing = []
        for name in sorted(os.listdir(TESTS_DIR)):
            full = os.path.join(TESTS_DIR, name)
            if os.path.isdir(full) and name not in NON_TEST_DIRS - {"_helpers"}:
                if name == "__pycache__":
                    continue
                if not os.path.isfile(os.path.join(full, "__init__.py")):
                    missing.append(name)
        self.assertEqual(missing, [], "Thư mục con của `tests/` thiếu `__init__.py` (SPEC R2).")

    def test_k9_no_test_file_outside_the_four_homes(self):
        """Không có ``test_*.py`` lạc ngoài 4 nhà (``docs/`` được miễn — tooling tài liệu)."""
        strays = []
        for root, dirs, files in os.walk(APP_ROOT):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for f in files:
                if not (f.startswith("test_") and f.endswith(".py")):
                    continue
                full = os.path.join(root, f)
                if full.startswith(TESTS_DIR + os.sep):
                    continue
                if os.sep + "doctype" + os.sep in full:      # nhà #1 — chuẩn Frappe
                    continue
                strays.append(rel_repo(full))
        self.assertEqual(
            strays, [],
            "File test nằm ngoài 4 nhà. Test của DocType đặt cạnh doctype; còn lại vào `tests/`.",
        )

    # ── K3 · Không mã ticket trong tên file ───────────────────────────────────
    def test_k3_no_ticket_code_in_filename(self):
        """Mã sổ chết theo vòng phát hành — đưa vào docstring/tên method, không vào tên file."""
        pat = re.compile(r"(?:^|[._-])(ac|acr|cr)\d+(?:[._-]|$)|AC-(CR|UX)", re.I)
        bad = [_rel_tests(p) for p in _all_test_files() if pat.search(os.path.basename(p))]
        self.assertEqual(bad, [], "Mã ticket trong TÊN FILE — chuyển vào docstring/`test_*` method.")

    # ── K5 · Guard đọc đĩa phải ở tests/guards/ ───────────────────────────────
    def test_k5_directory_scanners_live_in_guards(self):
        """File **quét thư mục** là guard cưỡng chế quy ước ⇒ thuộc ``tests/guards/``."""
        self.assertLessEqual(len(K5_ALLOWLIST), K5_FROZEN_SIZE,
                             "Allowlist K5 dài ra = quy ước đang bị nới.")
        bad = []
        for p in _all_test_files():
            rel = _rel_tests(p)
            if rel.startswith("guards/") or rel in K5_ALLOWLIST:
                continue
            if SCANS_DIR.search(_read(p)):
                bad.append(rel)
        self.assertEqual(
            bad, [],
            "Test quét thư mục (`os.walk`/`glob`/`listdir`/`list_files`) nhưng không ở "
            "`tests/guards/`. Quét cả cây = cưỡng chế quy ước ⇒ là guard.",
        )

    # ── K6 · Guard quét phải chốt dân số ──────────────────────────────────────
    def test_k6_scanning_guards_lock_population(self):
        """Quét mà không chốt dân số ⇒ thư mục bị dời thì đếm 0 và **PASS giả** (§5.2 N5)."""
        bad = []
        for p in _all_test_files():
            rel = _rel_tests(p)
            if not rel.startswith("guards/"):
                continue
            src = _read(p)
            if SCANS_DIR.search(src) and not POPULATION_LOCKED.search(src):
                bad.append(rel)
        self.assertEqual(
            bad, [],
            "Guard quét thư mục mà không chốt dân số tối thiểu. Dùng "
            "`list_files(DIR, ext, min_count=N)` hoặc `assertGreater(len(files), N)` — "
            "nếu không, thư mục bị dời thì guard đếm 0 và mọi khẳng định "
            '"không có vi phạm" thành đúng-rỗng-tuếch.',
        )

    # ── K7 · Ghi DB phải rollback ─────────────────────────────────────────────
    def test_k7_db_writing_tests_use_frappe_testcase(self):
        """Bệnh gốc §3.4: test ghi DB không rollback ⇒ rác rơi vào site thật.

        ``FrappeTestCase`` bọc mỗi test trong savepoint và rollback. Sổ allowlist
        ĐÓNG BĂNG ở 0 sau lô B4 — file mới **không thể** ghi DB mà không rollback.
        """
        self.assertLessEqual(
            len(K7_ALLOWLIST), K7_FROZEN_SIZE,
            "Allowlist K7 dài ra = nợ rollback đang MỌC THÊM. Kế thừa `FrappeTestCase` "
            "thay vì thêm dòng vào sổ.",
        )
        bad = []
        for p in _all_test_files():
            rel = _rel_tests(p)
            if rel in K7_ALLOWLIST:
                continue
            src = _read(p)
            if not writes_db(src):
                continue
            if "FrappeTestCase" in src:
                continue
            # kế thừa gián tiếp: lớp cơ sở import từ file test khác trong app
            if re.search(r"^from assetcore\.tests\.[\w.]+ import .*Base", src, re.M):
                continue
            bad.append(rel)
        self.assertEqual(
            bad, [],
            "Test ghi DB (`frappe.get_doc/new_doc/insert/db.set/delete_doc`) mà lớp cơ sở "
            "không phải `FrappeTestCase` ⇒ dữ liệu KHÔNG rollback, rác rơi vào site thật "
            "(§3.4 — nguồn của 45 CAPA + 24 hiệu chuẩn mồ côi và 16 script purge).",
        )

    # ── K8 · Tên file snake_case ──────────────────────────────────────────────
    def test_k8_python_filenames_are_snake_case(self):
        """Ngoại lệ ĐÓNG BĂNG: ``patches/**`` (đánh số — R3) và ``www/*.py`` (tên = URL)."""
        ok = re.compile(r"^[a-z_][a-z0-9_]*\.py$")
        bad = []
        for root, dirs, files in os.walk(APP_ROOT):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            if root.startswith(PATCHES_DIR) or os.sep + "www" in root:
                continue
            for f in files:
                if f.endswith(".py") and not ok.match(f):
                    bad.append(rel_repo(os.path.join(root, f)))
        self.assertEqual(bad, [], "File `.py` phải snake_case (SPEC §5.2 N1).")

    def test_k8b_patch_filenames_are_never_renamed(self):
        """R3 — Frappe nhận diện patch bằng **chuỗi dotted path** (``patch_handler.py:228``).

        Đổi tên một patch ĐÃ CHẠY ⇒ Frappe coi là patch mới ⇒ **chạy lại trên
        production**. Guard chỉ chốt dân số: số file patch không được TỤT.
        """
        files = list_files(PATCHES_DIR, ".py", min_count=25, skip=("__pycache__",))
        self.assertGreaterEqual(
            len(files), 25,
            "Số file trong `patches/` tụt — patch bị xoá/đổi tên. CẤM TUYỆT ĐỐI (R3).",
        )

    # ── B6 · Ranh giới utils/ ⇄ services/shared/ ──────────────────────────────
    def test_b6_utils_never_imports_services(self):
        """§5.4 — ranh giới MỘT CHIỀU, chống tái phát vòng lặp import module-level.

        ``utils/`` là hạ tầng kỹ thuật: được import thư viện ngoài + ``frappe``,
        **CẤM** import ``services/**``. Chiều ngược lại (``services/shared/`` dùng
        ``utils/``) là hợp lệ. Trước lô B6, hai chiều cùng tồn tại và phải chữa
        bằng ``# noqa: E402`` — dấu vết của người đi vòng để phá circular import.
        """
        # CHỈ bắt import MỨC MODULE (cột 0) — đó là chỗ sinh vòng lặp lúc nạp
        # module. Lazy-import BÊN TRONG hàm (thụt lề) là lối thoát hợp lệ của
        # Python và KHÔNG tạo vòng: vd `utils/fcm.py` gọi
        # `services.mobile_device_token.invalidate_token` chỉ khi gặp dead-token.
        offenders = []
        for f in sorted(os.listdir(UTILS_DIR)):
            if not f.endswith(".py"):
                continue
            src = _read(os.path.join(UTILS_DIR, f))
            for i, line in enumerate(src.splitlines(), 1):
                if re.match(r"(from|import)\s+assetcore\.services", line):
                    offenders.append(f"utils/{f}:{i} — {line.strip()}")
        self.assertEqual(
            offenders, [],
            "`utils/` import ngược lên `services/**` ⇒ vòng lặp module-level. "
            "Thứ bị CẢ HAI tầng dùng phải nằm ở tầng THẤP hơn (`utils/`), rồi "
            "`services/shared/` re-export một chiều.",
        )


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()
