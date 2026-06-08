# assetcore/tests/test_import_asset_identity.py
# Copyright (c) 2026, AssetCore Team
"""TDD — IMM-00 [V1-D] Import wizard parity định danh tài sản.

Acceptance (pre-validate chặn TRƯỚC, KHÔNG để frappe.throw nổ mid-insert):
  - asset_code SAI PATTERN (khoảng trắng / ký tự ngoài ^[A-Za-z0-9._\\-/]+$) →
    ImportError severity='error' field='asset_code', VI 'Mã tài sản chỉ được chứa
    chữ cái, số và các ký tự . _ - /'. Hàng KHÔNG được commit ở process_import.
  - Regex pattern dùng CHUNG 1 SoT DUY NHẤT với BE create — import
    _ASSET_CODE_PATTERN từ ac_asset (KHÔNG copy literal regex thứ 2 ở codebase).
  - manufacturer_sn trùng được pre-validate: (a) trùng DB → 'đã tồn tại trong hệ
    thống'; (b) trùng giữa 2 hàng trong file → 'bị trùng lặp trong file'. Trống →
    bỏ qua (optional, mutable — ADR D3).
  - reserved-prefix asset_code: '_' hoặc 'SI-' đầu chuỗi → error VI; dùng hằng SoT
    _RESERVED_NAME_PREFIX / _RESERVED_NAME_SI_PREFIX (services.imm00) — '_' ở GIỮA
    và 'TS-' KHÔNG bị chặn (0 false-positive).
  - Mixed file (hợp lệ + bad-pattern + serial-trùng) → validate trả đúng row-level
    error, hàng hợp lệ import OK; KHÔNG DuplicateEntryError/ValidationError raw lọt.
  - whitespace 2 đầu asset_code/manufacturer_sn .strip() TRƯỚC mọi check (parity
    create path).
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import frappe
from frappe.tests.utils import FrappeTestCase

from assetcore.assetcore.doctype.ac_asset.ac_asset import _ASSET_CODE_PATTERN
from assetcore.services.import_validators import AssetImportValidator
from assetcore.services.imm00 import (
    _RESERVED_NAME_PREFIX,
    _RESERVED_NAME_SI_PREFIX,
)
from assetcore.tests._asset_cleanup import purge_asset

_APP_ROOT = Path(__file__).resolve().parents[1]  # …/assetcore (package root)


def _insert_asset(data: dict):
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    try:
        return frappe.get_doc(data).insert(ignore_permissions=True)
    finally:
        frappe.flags.in_install = prev


def _errs(rows: list[dict]) -> list[dict]:
    """Run AssetImportValidator.validate_all → list[ImportError]."""
    return AssetImportValidator().validate_all(rows)


def _err_for(errors, row: int, field: str):
    return [e for e in errors if e["row"] == row and e["field"] == field]


class TestImportAssetIdentity(FrappeTestCase):
    """Service-layer pre-validate parity với BE create path."""

    TAG = "IMPID"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._purge()
        cls._cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_code": f"_TestIMPID-{cls.TAG}",
            "category_name": f"_TestIMPID-{cls.TAG}",
        }).insert(ignore_permissions=True)
        cls.cat_name = cls._cat.name
        # Seed an existing asset carrying a known manufacturer_sn (for DB-dup check).
        cls._seed_asset = _insert_asset({
            "doctype": "AC Asset",
            "asset_code": f"SEED-IMPID-{cls.TAG}",
            "asset_name": "Máy siêu âm Philips EPIQ 7 (seed)",
            "asset_category": cls.cat_name,
            "manufacturer_sn": "SN-EPIQ-001",
        })
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        cls._purge()
        super().tearDownClass()

    @classmethod
    def _purge(cls):
        for a in frappe.get_all(
            "AC Asset",
            filters={"asset_category": ["in", [
                f"_TestIMPID-{cls.TAG}",
            ]]},
            pluck="name",
        ):
            purge_asset(a)
        # also purge by known seed / mixed-file names if category already gone
        for nm in (
            f"SEED-IMPID-{cls.TAG}", "TS-OK-01", "TS-MIX-OK-1",
            "TS-HAPPY-IMPID",
        ):
            if frappe.db.exists("AC Asset", nm):
                purge_asset(nm)
        if frappe.db.exists("AC Asset Category", f"_TestIMPID-{cls.TAG}"):
            frappe.delete_doc(
                "AC Asset Category", f"_TestIMPID-{cls.TAG}",
                force=True, ignore_permissions=True,
            )
        frappe.db.commit()

    # ── asset_code pattern ─────────────────────────────────────────────────

    def test_asset_code_bad_pattern_blocked(self):
        rows = [{
            "asset_code": "TS LAB 001",  # space → invalid
            "asset_name": "Máy xét nghiệm",
            "asset_category": self.cat_name,
        }]
        errors = _errs(rows)
        bad = _err_for(errors, 1, "asset_code")
        self.assertTrue(bad, "asset_code sai pattern phải trả ImportError")
        self.assertEqual(bad[0]["severity"], "error")
        self.assertIn("chỉ được chứa", bad[0]["message"])

        # KHÔNG được insert ở process: name không tồn tại sau pre-validate block.
        self.assertFalse(frappe.db.exists("AC Asset", "TS LAB 001"))

    def test_asset_code_bad_pattern_variants(self):
        for code in ("Mã@01", "TS#1", "TS LAB 001"):
            rows = [{
                "asset_code": code,
                "asset_name": "X",
                "asset_category": self.cat_name,
            }]
            bad = _err_for(_errs(rows), 1, "asset_code")
            self.assertTrue(
                any("chỉ được chứa" in e["message"] for e in bad),
                f"{code!r} phải bị chặn bad-pattern",
            )

    def test_asset_code_pattern_sot_single_source(self):
        """`_ASSET_CODE_PATTERN` được ĐỊNH NGHĨA đúng 1 lần (ac_asset.py); mọi
        consumer khác (import_validators) IMPORT lại, KHÔNG re.compile literal mới.

        Lưu ý: `service_contract._CONTRACT_CODE_PATTERN` là regex của field KHÁC
        (contract_code) — trùng chuỗi nhưng là SoT riêng cho domain hợp đồng, KHÔNG
        phải bản sao của asset_code → KHÔNG tính là vi phạm.
        """
        # (a) Tên hằng `_ASSET_CODE_PATTERN` = re.compile chỉ ở ac_asset.py.
        defines: list[str] = []
        for py in _APP_ROOT.rglob("*.py"):
            if "/tests/" in str(py).replace("\\", "/"):
                continue
            src = py.read_text(encoding="utf-8")
            if "_ASSET_CODE_PATTERN" not in src:
                continue
            for node in ast.walk(ast.parse(src)):
                if not isinstance(node, ast.Assign):
                    continue
                targets = {
                    t.id for t in node.targets if isinstance(t, ast.Name)
                }
                if "_ASSET_CODE_PATTERN" not in targets:
                    continue
                # only count re.compile(...) assignments as a "definition"
                if (
                    isinstance(node.value, ast.Call)
                    and getattr(node.value.func, "attr", "") == "compile"
                ):
                    defines.append(str(py.relative_to(_APP_ROOT)))
        self.assertEqual(
            defines,
            ["assetcore/doctype/ac_asset/ac_asset.py"],
            f"_ASSET_CODE_PATTERN phải re.compile DUY NHẤT ở ac_asset.py, "
            f"thấy ở: {defines}",
        )

        # (b) import_validators dùng CÙNG object (identity) chứ không phải bản sao.
        from assetcore.services import import_validators as iv
        self.assertIs(iv._ASSET_CODE_PATTERN, _ASSET_CODE_PATTERN)

        # (c) import_validators.py KHÔNG re.compile bất kỳ regex asset_code literal.
        iv_src = (_APP_ROOT / "services" / "import_validators.py").read_text(
            encoding="utf-8"
        )
        literal = r"[A-Za-z0-9._\-/]+"
        for node in ast.walk(ast.parse(iv_src)):
            if (
                isinstance(node, ast.Call)
                and getattr(node.func, "attr", "") == "compile"
            ):
                for a in node.args:
                    if isinstance(a, ast.Constant) and literal in str(a.value):
                        self.fail(
                            "import_validators.py KHÔNG được re.compile lại "
                            "regex asset_code — import _ASSET_CODE_PATTERN."
                        )

    # ── reserved prefix ────────────────────────────────────────────────────

    def test_asset_code_reserved_prefix_blocked(self):
        for code in (f"{_RESERVED_NAME_SI_PREFIX}FOO", f"{_RESERVED_NAME_PREFIX}RAC"):
            rows = [{
                "asset_code": code,
                "asset_name": "X",
                "asset_category": self.cat_name,
            }]
            bad = _err_for(_errs(rows), 1, "asset_code")
            self.assertTrue(
                any("tiền tố dành riêng" in e["message"] for e in bad),
                f"{code!r} phải bị chặn reserved-prefix",
            )

    def test_asset_code_reserved_prefix_no_false_positive(self):
        # '_' ở GIỮA (Model_X) và 'TS-' (KHÔNG reserved) KHÔNG bị flag. Dùng suffix
        # tag-scoped để KHÔNG đụng asset cũ trong DB (loại nhiễu dup-DB error).
        for code in (f"Model_X-{self.TAG}", f"TS-LAB-{self.TAG}-001"):
            rows = [{
                "asset_code": code,
                "asset_name": "X",
                "asset_category": self.cat_name,
            }]
            bad = _err_for(_errs(rows), 1, "asset_code")
            self.assertFalse(
                bad, f"{code!r} KHÔNG được flag (0 false-positive), thấy: {bad}",
            )

    # ── manufacturer_sn ────────────────────────────────────────────────────

    def test_manufacturer_sn_dup_db_blocked(self):
        rows = [{
            "asset_code": "TS-SN-DBDUP",
            "asset_name": "X",
            "asset_category": self.cat_name,
            "manufacturer_sn": "SN-EPIQ-001",  # seeded in setUpClass
        }]
        bad = _err_for(_errs(rows), 1, "manufacturer_sn")
        self.assertTrue(bad, "serial trùng DB phải bị chặn")
        self.assertEqual(bad[0]["severity"], "error")
        self.assertIn("đã tồn tại trong hệ thống", bad[0]["message"])

    def test_manufacturer_sn_dup_in_batch_blocked(self):
        rows = [
            {"asset_code": "TS-SN-A", "asset_name": "A",
             "asset_category": self.cat_name, "manufacturer_sn": "SN-DUP"},
            {"asset_code": "TS-SN-B", "asset_name": "B",
             "asset_category": self.cat_name, "manufacturer_sn": "SN-DUP"},
        ]
        errors = _errs(rows)
        self.assertFalse(_err_for(errors, 1, "manufacturer_sn"),
                         "row đầu KHÔNG bị chặn (lần xuất hiện đầu)")
        bad2 = _err_for(errors, 2, "manufacturer_sn")
        self.assertTrue(bad2, "row 2 (serial trùng trong file) phải bị chặn")
        self.assertIn("bị trùng lặp trong file", bad2[0]["message"])

    def test_manufacturer_sn_blank_ignored(self):
        rows = [
            {"asset_code": "TS-NOSN-1", "asset_name": "A",
             "asset_category": self.cat_name, "manufacturer_sn": ""},
            {"asset_code": "TS-NOSN-2", "asset_name": "B",
             "asset_category": self.cat_name},  # key absent
            {"asset_code": "TS-NOSN-3", "asset_name": "C",
             "asset_category": self.cat_name, "manufacturer_sn": "   "},
        ]
        errors = _errs(rows)
        for i in (1, 2, 3):
            self.assertFalse(
                _err_for(errors, i, "manufacturer_sn"),
                f"manufacturer_sn trống ở row {i} KHÔNG được flag",
            )

    # ── strip parity ───────────────────────────────────────────────────────

    def test_strip_parity(self):
        """asset_code/manufacturer_sn .strip() TRƯỚC check + import parity."""
        rows = [{
            "asset_code": "  TS-OK-01  ",
            "asset_name": "Máy thở",
            "asset_category": self.cat_name,
            "manufacturer_sn": "  SN-9  ",
        }]
        # 0 error trên hàng hợp lệ sau strip
        self.assertEqual(_errs(rows), [], "hàng hợp lệ sau strip KHÔNG được lỗi")

        # Parity create path: insert với cùng giá trị có space → name strip-clean.
        doc = _insert_asset({
            "doctype": "AC Asset",
            "asset_code": "  TS-OK-01  ",
            "asset_name": "Máy thở",
            "asset_category": self.cat_name,
            "manufacturer_sn": "  SN-9  ",
        })
        self.assertEqual(doc.name, "TS-OK-01")
        self.assertEqual(doc.asset_code, "TS-OK-01")
        purge_asset(doc.name)

    # ── happy path ─────────────────────────────────────────────────────────

    def test_happy_path_no_regression(self):
        rows = [{
            "asset_code": "TS-HAPPY-IMPID",
            "asset_name": "Máy đo",
            "asset_category": self.cat_name,
            "manufacturer_sn": "SN-NEW-UNIQUE-1",
        }]
        self.assertEqual(_errs(rows), [], "happy path phải 0 error")

    def test_existing_dup_asset_code_messages_unchanged(self):
        """Hồi quy: dup asset_code (DB + trong file) giữ nguyên 2 message cũ."""
        rows = [
            {"asset_code": f"SEED-IMPID-{self.TAG}", "asset_name": "A",
             "asset_category": self.cat_name},                       # dup DB
            {"asset_code": "TS-FILEDUP", "asset_name": "B",
             "asset_category": self.cat_name},
            {"asset_code": "TS-FILEDUP", "asset_name": "C",
             "asset_category": self.cat_name},                       # dup file
        ]
        errors = _errs(rows)
        db_dup = _err_for(errors, 1, "asset_code")
        self.assertTrue(any("đã tồn tại trong hệ thống" in e["message"] for e in db_dup))
        file_dup = _err_for(errors, 3, "asset_code")
        self.assertTrue(any("bị trùng lặp trong file" in e["message"] for e in file_dup))


class TestImportAssetIdentityEndToEnd(FrappeTestCase):
    """Mixed file: pre-validate chặn → process import chỉ hàng hợp lệ, KHÔNG raw throw."""

    TAG = "IMPE2E"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._purge()
        cls._cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_code": f"_TestIMPE2E-{cls.TAG}",
            "category_name": f"_TestIMPE2E-{cls.TAG}",
        }).insert(ignore_permissions=True)
        cls.cat_name = cls._cat.name
        cls._seed = _insert_asset({
            "doctype": "AC Asset",
            "asset_code": f"SEED-E2E-{cls.TAG}",
            "asset_name": "Seed E2E",
            "asset_category": cls.cat_name,
            "manufacturer_sn": "SN-SEEDED-E2E",
        })
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        cls._purge()
        super().tearDownClass()

    @classmethod
    def _purge(cls):
        for nm in ("TS-MIX-OK-1", f"SEED-E2E-{cls.TAG}"):
            if frappe.db.exists("AC Asset", nm):
                purge_asset(nm)
        if frappe.db.exists("AC Asset Category", f"_TestIMPE2E-{cls.TAG}"):
            # purge any asset still under category first
            for a in frappe.get_all(
                "AC Asset", filters={"asset_category": f"_TestIMPE2E-{cls.TAG}"},
                pluck="name",
            ):
                purge_asset(a)
            frappe.delete_doc(
                "AC Asset Category", f"_TestIMPE2E-{cls.TAG}",
                force=True, ignore_permissions=True,
            )
        frappe.db.commit()

    def test_mixed_file_partial_success_no_raw_throw(self):
        """File 3 row: (1) hợp lệ, (2) asset_code sai pattern, (3) serial trùng DB.

        Emulate process_import partial-success path: pre-validate xác định
        invalid_idx (severity='error'), chỉ hàng hợp lệ đi vào new_doc().insert().
        Assert KHÔNG raise DuplicateEntryError/ValidationError raw; row1 tồn tại,
        row2/row3 KHÔNG tồn tại.
        """
        rows = [
            {"asset_code": "TS-MIX-OK-1", "asset_name": "Hợp lệ",
             "asset_category": self.cat_name, "manufacturer_sn": "SN-MIX-NEW"},
            {"asset_code": "TS MIX 002", "asset_name": "Bad pattern",
             "asset_category": self.cat_name},
            {"asset_code": "TS-MIX-OK-3", "asset_name": "Serial trùng",
             "asset_category": self.cat_name, "manufacturer_sn": "SN-SEEDED-E2E"},
        ]

        errors = AssetImportValidator().validate_all(rows)
        blocking = [e for e in errors if e["severity"] == "error"]
        bad_rows = {e["row"] for e in blocking}
        # row 2 (pattern) + row 3 (serial dup) phải bị chặn; row 1 không.
        self.assertIn(2, bad_rows)
        self.assertIn(3, bad_rows)
        self.assertNotIn(1, bad_rows)

        # Process: chỉ insert hàng KHÔNG nằm trong bad_rows. KHÔNG raw throw.
        inserted: list[str] = []
        for i, row in enumerate(rows, start=1):
            if i in bad_rows:
                continue
            doc = _insert_asset({
                "doctype": "AC Asset",
                "asset_code": str(row["asset_code"]).strip(),
                "asset_name": row["asset_name"],
                "asset_category": row["asset_category"],
                "manufacturer_sn": str(row.get("manufacturer_sn", "")).strip(),
            })
            inserted.append(doc.name)

        self.assertEqual(inserted, ["TS-MIX-OK-1"])
        self.assertTrue(frappe.db.exists("AC Asset", "TS-MIX-OK-1"))
        self.assertFalse(frappe.db.exists("AC Asset", "TS MIX 002"))
        self.assertFalse(frappe.db.exists("AC Asset", "TS-MIX-OK-3"))


# ──────────────────────────────────────────────────────────────────────────
# BE-D4 (ADR-IMM00-QR-SCAN-ACTION §D4) — QR-gen coverage: ĐƯỜNG IMPORT.
#
# "QR sinh ở đâu khi import?" → KHÔNG có code QR riêng cho import. Token sinh ở
# MODEL LAYER: ``ac_asset.py::before_insert`` → ``_ensure_qr_token`` (ac_asset.py
# :50,63,65). Đường import (``api/import_data.py::_do_import`` →
# ``frappe.new_doc().update().insert()``, import_data.py:348-350) gọi
# ``doc.insert()`` ⇒ Frappe Document lifecycle fire ``before_insert`` Y HỆT
# đường form/registration ⇒ token tự sinh idempotent. KHÔNG thêm code token-gen
# riêng cho import — chỉ CHỨNG MINH bằng test trên ĐƯỜNG IMPORT THẬT.
#
# Test này NẠP 1 file CSV thật (đúng layout template: row1 banner / row2
# fieldnames / row3-5 skip / row6+ data) rồi gọi ``_do_import`` (đường HTTP
# import production) — KHÔNG emulate bằng _insert_asset thủ công. RED nếu
# before_insert/_ensure_qr_token bị gỡ; GREEN với code hiện tại.
# ──────────────────────────────────────────────────────────────────────────


class TestQrGenCoverageImport(FrappeTestCase):
    """BE-D4: import 1 hàng AC Asset qua đường import THẬT → qr_token != rỗng.

    Chứng minh QR-gen coverage cho đường (2) import: token sinh ở model-layer
    ``before_insert→_ensure_qr_token``, fire qua ``doc.insert()`` trong
    ``_do_import`` — KHÔNG có code QR riêng cho import.
    """

    TAG = "QRIMP"
    _URLSAFE = re.compile(r"^[A-Za-z0-9_-]+$")

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        cls._purge()
        cls._cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_code": f"_TestQRIMP-{cls.TAG}",
            "category_name": f"_TestQRIMP-{cls.TAG}",
        }).insert(ignore_permissions=True)
        cls.cat_name = cls._cat.name
        cls._files: list[str] = []
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        cls._purge()
        super().tearDownClass()

    @classmethod
    def _purge(cls):
        for nm in ("TS-QRIMP-001", "TS-QRIMP-KEEP-TOKEN"):
            if frappe.db.exists("AC Asset", nm):
                purge_asset(nm)
        for fname in getattr(cls, "_files", []):
            if frappe.db.exists("File", fname):
                frappe.delete_doc("File", fname, force=True, ignore_permissions=True)
        if frappe.db.exists("AC Asset Category", f"_TestQRIMP-{cls.TAG}"):
            for a in frappe.get_all(
                "AC Asset", filters={"asset_category": f"_TestQRIMP-{cls.TAG}"},
                pluck="name",
            ):
                purge_asset(a)
            frappe.delete_doc(
                "AC Asset Category", f"_TestQRIMP-{cls.TAG}",
                force=True, ignore_permissions=True,
            )
        frappe.db.commit()

    def _save_csv(self, data_rows: list[list[str]]) -> str:
        """Tạo File CSV thật đúng layout template (row2=fieldnames, data từ row6).

        Trả file_url để truyền vào ``_do_import``. File được track để cleanup.
        """
        import csv
        import io

        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["BANNER — Danh sách tài sản (bỏ qua khi parse)"])  # row1
        w.writerow(["asset_code", "asset_name", "asset_category",
                    "manufacturer_sn"])                                # row2 fieldnames
        w.writerow(["Mã tài sản", "Tên tài sản", "Danh mục thiết bị",
                    "Số serial NSX"])                                  # row3 labels (skip)
        w.writerow(["bắt buộc", "bắt buộc", "bắt buộc", "tuỳ chọn"])    # row4 desc (skip)
        w.writerow(["TS-VD-01", "Máy ví dụ", "Danh mục", "SN-VD"])     # row5 example (skip)
        for r in data_rows:                                            # row6+ data
            w.writerow(r)

        from frappe.utils.file_manager import save_file
        fname = f"qrimp_{frappe.generate_hash(length=8)}.csv"
        fdoc = save_file(
            fname, buf.getvalue().encode("utf-8-sig"),
            "AC Asset", "import-qrimp", is_private=1,
        )
        self.__class__._files.append(fdoc.name)
        frappe.db.commit()
        return fdoc.file_url

    def test_import_row_generates_qr_token(self):
        """Import 1 hàng AC Asset hợp lệ qua _do_import → reload doc → qr_token
        != '' và != None; URL-safe regex ^[A-Za-z0-9_-]+$ len>=20.

        Đây là RED-guard cốt lõi cho đường import: nếu before_insert/_ensure_qr_token
        bị gỡ → doc.insert() không sinh token → assertTrue(qr_token) FAIL.
        """
        from assetcore.api.import_data import _do_import

        file_url = self._save_csv([
            ["TS-QRIMP-001", "Máy siêu âm Philips EPIQ 7 (import)",
             self.cat_name, "SN-QRIMP-001"],
        ])
        res = _do_import("AC Asset", file_url, skip_invalid=False)
        self.assertEqual(res["success"], 1, f"import phải thành công 1 hàng: {res}")
        self.assertTrue(frappe.db.exists("AC Asset", "TS-QRIMP-001"))

        # reload doc → đọc qr_token trực tiếp từ DB sau insert
        token = frappe.db.get_value("AC Asset", "TS-QRIMP-001", "qr_token")
        self.assertTrue(token,
                        "qr_token PHẢI != rỗng sau import (before_insert sinh)")
        self.assertIsNotNone(token)
        self.assertGreaterEqual(len(token), 20, "token URL-safe >= 20 ký tự")
        self.assertRegex(token, self._URLSAFE,
                         "token chỉ chứa ký tự URL-safe [A-Za-z0-9_-]")
        # Định danh-leak guard: token KHÔNG nhúng asset_code/serial
        self.assertNotIn("TS-QRIMP-001", token)
        self.assertNotIn("SN-QRIMP-001", token)

    def test_import_token_not_clobber_when_present(self):
        """Import hàng có sẵn qr_token → before_insert KHÔNG ghi đè (idempotent
        ``if self.qr_token: return``). Token sau import == token đã cấp trong file.
        """
        from assetcore.api.import_data import _do_import

        preset = "PRESET-IMPORT-TOKEN-ABC123XYZ789"
        file_url = self._save_csv([
            ["TS-QRIMP-KEEP-TOKEN", "Máy có sẵn token (import)",
             self.cat_name, "SN-QRIMP-KEEP"],
        ])
        # Inject qr_token vào CSV không khả thi (template không có cột qr_token),
        # nên chứng minh idempotent ở MODEL: new_doc đã set qr_token TRƯỚC insert
        # → before_insert thấy có token → no-op (không clobber). Mô phỏng đúng cơ
        # chế import_data._do_import (new_doc().update(clean).insert()) với clean
        # mang sẵn qr_token.
        doc = frappe.new_doc("AC Asset")
        doc.update({
            "asset_code": "TS-QRIMP-KEEP-TOKEN",
            "asset_name": "Máy có sẵn token (import)",
            "asset_category": self.cat_name,
            "manufacturer_sn": "SN-QRIMP-KEEP",
            "qr_token": preset,
            "lifecycle_status": "Draft",
        })
        doc.insert(ignore_permissions=True)
        token = frappe.db.get_value("AC Asset", "TS-QRIMP-KEEP-TOKEN", "qr_token")
        self.assertEqual(token, preset,
                         "before_insert KHÔNG được ghi đè qr_token đã có "
                         "(idempotent — if self.qr_token: return)")
