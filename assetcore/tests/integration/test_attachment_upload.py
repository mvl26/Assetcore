"""Upload tệp đính kèm dùng chung — `assetcore.api.files` + guard chống hồi quy.

Bối cảnh (2026-07-22): modal "Thêm chứng chỉ nhà cung cấp" render field đính kèm
bằng `<input type="text" placeholder="/files/...">` — người dùng phải TỰ GÕ đường
dẫn. Tệp không bao giờ vào hệ thống ⇒ hồ sơ NĐ98 mất bằng chứng. Sửa: endpoint
`upload_attachment` + component FE `FileUploadField.vue`.

Test gồm 3 lớp:
  1. Gate của endpoint (field phải là Attach thật, doctype phải của AssetCore,
     bảng con phải khai parent_doctype, validate đuôi/dung lượng).
  2. Hook `link_uploaded_files` gắn File mồ côi vào hồ sơ (quyền đọc tệp thừa
     hưởng quyền đọc hồ sơ — nếu không, chỉ người tải lên đọc được).
  3. GUARD tĩnh: không file .vue nào được bind `<input type="text">` vào field
     Attach nữa.
"""
from __future__ import annotations

import json
import os
import re
import unittest

import frappe

from assetcore.api.files import (
    _is_corrupt_file_error,
    _resolve_attach_field,
    _resolve_owner_doctype,
    _validate_file,
    MAX_ATTACHMENT_BYTES,
)
from assetcore.services.shared import ErrorCode, ServiceError
from frappe.tests.utils import FrappeTestCase

_APP_ROOT = frappe.get_app_path("assetcore")
_REPO_ROOT = os.path.dirname(_APP_ROOT)
_FE_SRC = os.path.join(_REPO_ROOT, "frontend", "src")

#: Component chuẩn thay thế ô gõ đường dẫn — miễn trừ khỏi guard placeholder.
_CANONICAL_COMPONENT = "FileUploadField.vue"


class TestUploadAttachmentGate(FrappeTestCase):
    """Endpoint chỉ nhận field đính kèm THẬT trên doctype AssetCore."""

    def test_accepts_real_attach_field(self) -> None:
        df = _resolve_attach_field("Vendor Cert", "attachment")
        self.assertEqual(df.fieldtype, "Attach")

    def test_rejects_non_attach_field(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            _resolve_attach_field("Vendor Cert", "cert_number")
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)

    def test_rejects_unknown_field(self) -> None:
        with self.assertRaises(ServiceError):
            _resolve_attach_field("Vendor Cert", "khong_ton_tai")

    def test_rejects_non_assetcore_doctype(self) -> None:
        """Không cho ghi tệp lên doctype core (vd 'User') qua endpoint này."""
        with self.assertRaises(ServiceError) as ctx:
            _resolve_attach_field("User", "user_image")
        self.assertEqual(ctx.exception.code, ErrorCode.FORBIDDEN)

    def test_child_table_requires_parent_doctype(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            _resolve_owner_doctype("Vendor Cert", "")
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
        self.assertEqual(_resolve_owner_doctype("Vendor Cert", "AC Supplier"),
                         "AC Supplier")

    def test_parent_doctype_ignored_for_non_child(self) -> None:
        self.assertEqual(
            _resolve_owner_doctype("IMM Procurement Decision", ""),
            "IMM Procurement Decision")


class TestUploadValidation(FrappeTestCase):
    """Chặn đuôi tệp lạ + tệp quá lớn TRƯỚC khi ghi File."""

    def test_rejects_executable_extension(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            _validate_file("payload.exe", b"MZ", is_image=False)
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)

    def test_rejects_non_image_for_attach_image(self) -> None:
        with self.assertRaises(ServiceError):
            _validate_file("ho-so.pdf", b"%PDF", is_image=True)

    def test_rejects_empty_file(self) -> None:
        with self.assertRaises(ServiceError):
            _validate_file("trong.pdf", b"", is_image=False)

    def test_rejects_oversized(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            _validate_file("to.pdf", b"x" * (MAX_ATTACHMENT_BYTES + 1), is_image=False)
        self.assertIn("dung lượng", ctx.exception.message)

    def test_accepts_pdf_and_image(self) -> None:
        _validate_file("chung-chi.pdf", b"%PDF-1.4", is_image=False)
        _validate_file("anh.png", b"\x89PNG", is_image=True)

    def test_corrupt_file_error_is_classified(self) -> None:
        """Tệp hỏng → VALIDATION đọc được, KHÔNG 500 kèm thông điệp thư viện.

        Frappe quét nội dung trước khi ghi (pypdf tìm JS trong PDF, PIL đọc ảnh);
        bytes rác dù đúng đuôi ném PdfStreamError/UnidentifiedImageError.
        """
        from pypdf.errors import PdfStreamError

        self.assertTrue(_is_corrupt_file_error(PdfStreamError("startxref not found")))
        self.assertTrue(_is_corrupt_file_error(OSError("Truncated File Read")))
        self.assertFalse(_is_corrupt_file_error(ValueError("khac")))


class TestLinkUploadedFiles(FrappeTestCase):
    """Hook gắn File mồ côi vào hồ sơ — nếu không, chỉ người tải lên đọc được."""

    def setUp(self) -> None:
        self.supplier = frappe.get_doc({
            "doctype": "AC Supplier",
            "supplier_name": "_TestUpload NCC",
        }).insert(ignore_permissions=True)
        self.file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": "_test_upload_cert.txt",
            "is_private": 1,
            "content": b"noi dung bang chung test",
            "decode": False,
        }).insert(ignore_permissions=True)

    def tearDown(self) -> None:
        frappe.delete_doc("File", self.file_doc.name,
                          force=True, ignore_permissions=True)
        frappe.delete_doc("AC Supplier", self.supplier.name,
                          force=True, ignore_permissions=True)
        frappe.db.commit()

    def test_child_row_attachment_gets_linked(self) -> None:
        """file_url nằm trên bảng con `imm_certifications` cũng phải được gắn."""
        self.assertFalse(
            frappe.db.get_value("File", self.file_doc.name, "attached_to_doctype"))

        doc = frappe.get_doc("AC Supplier", self.supplier.name)
        doc.append("imm_certifications", {
            "cert_type": "ISO 13485",
            "cert_number": "_TEST-UPLOAD-1",
            "attachment": self.file_doc.file_url,
            "status": "Active",
        })
        doc.save(ignore_permissions=True)

        linked = frappe.db.get_value(
            "File", self.file_doc.name,
            ["attached_to_doctype", "attached_to_name"], as_dict=True)
        self.assertEqual(linked.attached_to_doctype, "AC Supplier")
        self.assertEqual(linked.attached_to_name, self.supplier.name)


class TestNoTypedFilePathInputs(FrappeTestCase):
    """GUARD: FE không được bắt người dùng gõ đường dẫn tệp vào ô text.

    Bắt 2 dấu hiệu: (a) placeholder gợi ý đường dẫn `/files/...`, (b) `<input>`
    text bind vào một fieldname vốn là `Attach`/`Attach Image` trong doctype.
    """

    def test_no_files_path_placeholder(self) -> None:
        offenders = []
        pattern = re.compile(r"placeholder\s*=\s*[\"'][^\"']*/files/", re.I)
        for path in _iter_vue_files():
            if os.path.basename(path) == _CANONICAL_COMPONENT:
                continue  # component chuẩn — nhắc lại anti-pattern trong docstring
            if pattern.search(_read(path)):
                offenders.append(os.path.relpath(path, _REPO_ROOT))
        self.assertEqual(
            offenders, [],
            "Field đính kèm phải dùng FileUploadField.vue, không phải ô gõ "
            f"đường dẫn: {offenders}")

    def test_no_text_input_bound_to_attach_field(self) -> None:
        attach_fields = _attach_fieldnames_from_doctype_json()
        # Fieldname quá chung, trùng biến FE không liên quan → bỏ qua ở guard này
        # (đã được phủ bởi test placeholder ở trên).
        ambiguous = {"evidence", "photo", "file_url", "attachment"}
        offenders = []
        for path in _iter_vue_files():
            src = _read(path)
            for tag in re.findall(r"<input\b[^>]*>", src, re.S):
                if 'type="file"' in tag:
                    continue
                m = re.search(r'v-model(?:\.\w+)?\s*=\s*"([^"]+)"', tag)
                if not m:
                    continue
                leaf = m.group(1).split(".")[-1].strip()
                if leaf in attach_fields and leaf not in ambiguous:
                    offenders.append(
                        f"{os.path.relpath(path, _REPO_ROOT)} → {m.group(1)}")
        self.assertEqual(
            offenders, [],
            f"Field Attach bị render bằng <input type=text>: {offenders}")


# ─── helpers ──────────────────────────────────────────────────────────────────

def _iter_vue_files():
    for root, _dirs, files in os.walk(_FE_SRC):
        for fn in files:
            if fn.endswith(".vue"):
                yield os.path.join(root, fn)


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _attach_fieldnames_from_doctype_json() -> set[str]:
    out: set[str] = set()
    dt_root = os.path.join(_APP_ROOT, "assetcore", "doctype")
    for entry in os.listdir(dt_root):
        path = os.path.join(dt_root, entry, f"{entry}.json")
        if not os.path.exists(path):
            continue
        try:
            data = json.loads(_read(path))
        except ValueError:
            continue
        for f in data.get("fields", []):
            if f.get("fieldtype") in ("Attach", "Attach Image"):
                out.add(f["fieldname"])
    return out
