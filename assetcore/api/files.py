# Copyright (c) 2026, AssetCore Team
"""Upload tệp đính kèm dùng chung — SSoT cho MỌI field `Attach` / `Attach Image`.

Vì sao có file này
------------------
Trước đây mỗi module tự làm một kiểu: IMM-00 có `upload_device_model_file`,
IMM-09/IMM-12 có endpoint ảnh riêng, IMM-05 gọi thẳng `/api/method/upload_file`,
và MỘT SỐ MÀN HÌNH KHÔNG CÓ UPLOAD GÌ CẢ — chỉ là ô `<input type="text">` bắt
người dùng **tự gõ đường dẫn** `/files/...`. Ô gõ tay đó là lỗi nghiệp vụ nghiêm
trọng: tệp không bao giờ vào hệ thống, `File` record không tồn tại, không có
quyền/không có vết audit, và đường dẫn gõ sai thì hồ sơ NĐ98 mất bằng chứng.

Endpoint này là nơi DUY NHẤT FE cần gọi để đưa tệp vào hệ thống:

    POST /api/method/assetcore.api.files.upload_attachment
    multipart: file=<binary>, doctype=..., fieldname=..., [docname], [parent_doctype]

Gate quyền
----------
KHÔNG dùng `/api/method/upload_file` trần (không gate được theo nghiệp vụ). Ở đây:
  1. DocType đích phải thuộc module ``AssetCore`` (không cho ghi tệp lên doctype core).
  2. ``fieldname`` phải THỰC SỰ là field `Attach`/`Attach Image` trên doctype đó
     (đọc từ meta) — chặn upload vào field bịa.
  3. Capability ``<domain>.write`` theo `rbac.DOCTYPE_DOMAIN` — capability-based,
     KHÔNG hardcode role-name (chống RBAC dead-gate).
  4. Có ``docname`` ⇒ thêm `frappe.has_permission(..., "write", doc=...)` để chặn
     ghi đè hồ sơ ngoài phạm vi của người dùng.

File tạo ra luôn `is_private=1` (bằng chứng tuân thủ, không để lộ qua URL đoán được).
"""
from __future__ import annotations

import os

import frappe
from frappe import _

from assetcore.services.shared import ErrorCode, ServiceError
from assetcore.services.shared import rbac
from assetcore.utils.response import _err, _ok

_DT_FILE = "File"
_ATTACH_FIELDTYPES = ("Attach", "Attach Image")

#: Đuôi tệp cho phép với field `Attach` (hồ sơ, chứng chỉ, biên bản, bằng chứng).
_ALLOWED_DOC_EXT = frozenset({
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".txt",
    ".png", ".jpg", ".jpeg", ".webp", ".gif",
})
#: Đuôi tệp cho phép với field `Attach Image`.
_ALLOWED_IMG_EXT = frozenset({".png", ".jpg", ".jpeg", ".webp", ".gif"})

MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024  #: 10MB cho tài liệu
MAX_IMAGE_BYTES = 5 * 1024 * 1024        #: 5MB cho ảnh


@frappe.whitelist(methods=["POST"])
def upload_attachment(doctype: str = "", fieldname: str = "", docname: str = "",
                      parent_doctype: str = "", **_ignore) -> dict:
    """POST (multipart) — tải tệp lên hệ thống, trả về `file_url` để lưu vào field.

    Args:
        doctype: DocType chứa field đính kèm. Có thể là child table
            (vd ``Vendor Cert``) — khi đó phải truyền thêm ``parent_doctype``.
        fieldname: tên field `Attach`/`Attach Image` trên ``doctype``.
        docname: tên bản ghi cha để gắn `File` vào (tuỳ chọn — màn hình "tạo mới"
            chưa có tên thì để trống, FE lưu ``file_url`` khi submit).
        parent_doctype: DocType cha khi ``doctype`` là child table.

    Returns:
        Envelope ``{success, data: {name, file_url, file_name, is_private}}``.

    ``**_ignore`` nuốt kwargs lạ (multipart form part thừa) — KHÔNG để HTTP-417.
    """
    try:
        return _ok(_upload_attachment(doctype, fieldname, docname, parent_doctype))
    except ServiceError as e:
        return _err(e.message, e.code)
    except frappe.PermissionError as e:
        return _err(str(e), ErrorCode.FORBIDDEN)
    except Exception as e:  # noqa: BLE001 — biên API, không để traceback lọt ra FE
        frappe.log_error(frappe.get_traceback(), "AssetCore upload_attachment")
        return _err(str(e), ErrorCode.INTERNAL)


def _upload_attachment(doctype: str, fieldname: str, docname: str,
                       parent_doctype: str) -> dict:
    df = _resolve_attach_field(doctype, fieldname)
    owner_dt = _resolve_owner_doctype(doctype, parent_doctype)
    _assert_can_write(owner_dt, docname)

    filename, filedata = _read_upload()
    is_image = df.fieldtype == "Attach Image"
    _validate_file(filename, filedata, is_image=is_image)

    payload = {
        "doctype": _DT_FILE,
        "file_name": filename,
        "is_private": 1,
        "content": filedata,
        "decode": False,
    }
    if docname:
        payload["attached_to_doctype"] = owner_dt
        payload["attached_to_name"] = docname
        # child table: field nằm trên row, không phải trên doc cha → không set
        # attached_to_field (Frappe sẽ validate field tồn tại trên doctype cha).
        if owner_dt == doctype:
            payload["attached_to_field"] = fieldname

    try:
        file_doc = frappe.get_doc(payload).insert(ignore_permissions=True)
    except Exception as exc:
        # Tệp HỎNG/ĐỨT TRUYỀN: Frappe quét nội dung trước khi ghi (pypdf tìm JS
        # trong PDF, PIL đọc ảnh). Bytes rác dù đúng đuôi → PdfStreamError /
        # UnidentifiedImageError / OSError. Đây là lỗi NHẬP LIỆU của người dùng,
        # không phải sự cố hệ thống — trả VALIDATION đọc được thay vì 500 kèm
        # thông điệp thư viện ("startxref not found"). Đối xứng imm09/imm12.
        if _is_corrupt_file_error(exc):
            frappe.clear_last_message()
            raise ServiceError(
                ErrorCode.VALIDATION,
                _("Tệp {0} bị hỏng hoặc không đọc được. Vui lòng chọn tệp khác.")
                .format(filename),
            ) from exc
        raise
    return {
        "name": file_doc.name,
        "file_url": file_doc.file_url,
        "file_name": file_doc.file_name,
        "is_private": file_doc.is_private,
    }


#: Tên exception (không import thư viện — pypdf/PIL là phụ thuộc gián tiếp).
_CORRUPT_FILE_ERRORS = frozenset({
    "PdfStreamError", "PdfReadError", "UnidentifiedImageError",
    "DecompressionBombError", "OSError",
})


def _is_corrupt_file_error(exc: Exception) -> bool:
    return type(exc).__name__ in _CORRUPT_FILE_ERRORS


# ─── validation helpers ───────────────────────────────────────────────────────

def _resolve_attach_field(doctype: str, fieldname: str):
    """Field đích phải là `Attach`/`Attach Image` THẬT trên doctype AssetCore."""
    if not doctype or not fieldname:
        raise ServiceError(ErrorCode.VALIDATION,
                           _("Thiếu doctype hoặc fieldname"))
    if not frappe.db.exists("DocType", doctype):
        raise ServiceError(ErrorCode.NOT_FOUND,
                           _("Không tìm thấy loại hồ sơ {0}").format(doctype))
    if frappe.db.get_value("DocType", doctype, "module") != "AssetCore":
        raise ServiceError(ErrorCode.FORBIDDEN,
                           _("Chỉ hỗ trợ đính kèm cho hồ sơ AssetCore"))
    df = frappe.get_meta(doctype).get_field(fieldname)
    if not df or df.fieldtype not in _ATTACH_FIELDTYPES:
        raise ServiceError(
            ErrorCode.VALIDATION,
            _("Trường {0} trên {1} không phải trường đính kèm tệp").format(
                fieldname, doctype),
        )
    return df


def _resolve_owner_doctype(doctype: str, parent_doctype: str) -> str:
    """DocType dùng để xét quyền — child table thì phải xét trên bảng cha."""
    if not frappe.get_meta(doctype).istable:
        return doctype
    if not parent_doctype:
        raise ServiceError(
            ErrorCode.VALIDATION,
            _("{0} là bảng con — cần truyền parent_doctype để xét quyền").format(doctype),
        )
    if not frappe.db.exists("DocType", parent_doctype):
        raise ServiceError(ErrorCode.NOT_FOUND,
                           _("Không tìm thấy loại hồ sơ {0}").format(parent_doctype))
    return parent_doctype


def _assert_can_write(owner_dt: str, docname: str) -> None:
    """Capability ghi trên loại hồ sơ + quyền ghi trên chính bản ghi (nếu đã có).

    Màn hình **tạo mới** (chưa có ``docname``) chỉ cần quyền `create` — người dùng
    có create=1/write=0 vẫn phải đính kèm được tệp cho hồ sơ họ đang lập.
    """
    ptypes = ("write",) if docname else ("write", "create")
    domain = rbac.DOCTYPE_DOMAIN.get(owner_dt)
    if domain and not domain.startswith("_"):
        prefix = domain.lower()
        if not any(rbac.can(f"{prefix}.{pt}") for pt in ptypes):
            raise ServiceError(ErrorCode.FORBIDDEN,
                               _("Không đủ quyền đính kèm tệp cho {0}").format(owner_dt))
    elif not any(frappe.has_permission(owner_dt, pt) for pt in ptypes):
        # Doctype ngoài bản đồ domain (vd _shared) → rơi về DocPerm chuẩn Frappe.
        raise ServiceError(ErrorCode.FORBIDDEN,
                           _("Không đủ quyền đính kèm tệp cho {0}").format(owner_dt))
    if docname:
        if not frappe.db.exists(owner_dt, docname):
            raise ServiceError(ErrorCode.NOT_FOUND,
                               _("Không tìm thấy hồ sơ {0}").format(docname))
        if not frappe.has_permission(owner_dt, "write", doc=docname):
            raise ServiceError(ErrorCode.FORBIDDEN,
                               _("Không đủ quyền sửa hồ sơ {0}").format(docname))


def _read_upload() -> tuple[str, bytes]:
    files = frappe.request.files if getattr(frappe, "request", None) else None
    upload = files.get("file") if files else None
    if upload is None:
        raise ServiceError(ErrorCode.VALIDATION, _("Thiếu tệp tải lên"))
    filename = upload.filename or ""
    if not filename:
        raise ServiceError(ErrorCode.VALIDATION, _("Tệp không có tên"))
    return filename, upload.stream.read()


def _validate_file(filename: str, filedata: bytes, *, is_image: bool) -> None:
    if not filedata:
        raise ServiceError(ErrorCode.VALIDATION, _("Tệp rỗng"))
    allowed = _ALLOWED_IMG_EXT if is_image else _ALLOWED_DOC_EXT
    ext = os.path.splitext(filename)[1].lower()
    if ext not in allowed:
        raise ServiceError(
            ErrorCode.VALIDATION,
            _("Định dạng {0} không được phép. Chấp nhận: {1}").format(
                ext or _("(không rõ)"), ", ".join(sorted(allowed))),
        )
    limit = MAX_IMAGE_BYTES if is_image else MAX_ATTACHMENT_BYTES
    if len(filedata) > limit:
        raise ServiceError(
            ErrorCode.VALIDATION,
            _("Tệp vượt quá dung lượng cho phép ({0}MB)").format(limit // (1024 * 1024)),
        )
