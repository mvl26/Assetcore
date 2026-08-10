# Copyright (c) 2026, AssetCore Team
"""Tự động gắn `File` đã tải lên vào hồ sơ chứa nó.

Vì sao cần
----------
Ở màn hình **tạo mới**, người dùng tải tệp lên TRƯỚC khi hồ sơ tồn tại nên
`assetcore.api.files.upload_attachment` chưa biết `docname` để gắn. Frappe
(`File.has_permission`) cho phép đọc tệp riêng tư không gắn hồ sơ **chỉ với chủ
sở hữu** ⇒ người duyệt/kiểm toán mở link sẽ bị từ chối: bằng chứng NĐ98 coi như
mất. Hook dưới đây chạy sau khi hồ sơ được lưu, dò mọi field `Attach` /
`Attach Image` và gắn `File` tương ứng vào hồ sơ — quyền đọc tệp từ đó thừa
hưởng quyền đọc hồ sơ.

Chi phí: hầu hết DocType không có field đính kèm nào → thoát ngay sau khi đọc
meta (đã cache). Không ghi DB nếu không có gì để gắn.
"""
from __future__ import annotations

import frappe

_ATTACH_FIELDTYPES = ("Attach", "Attach Image")


def link_uploaded_files(doc, method: str | None = None) -> None:
    """doc_events hook — gắn File của mọi field đính kèm vào `doc` (kể cả bảng con)."""
    try:
        _link_for_doc(doc)
    except Exception:
        # Không bao giờ chặn việc lưu hồ sơ vì lỗi gắn tệp — chỉ ghi log.
        frappe.log_error(frappe.get_traceback(), "AssetCore link_uploaded_files")


def _link_for_doc(doc) -> None:
    urls = _collect_urls(doc, _attach_fieldnames(doc.doctype))
    for tf in doc.meta.get_table_fields():
        child_fields = _attach_fieldnames(tf.options)
        if not child_fields:
            continue  # bảng con không có field đính kèm → không duyệt dòng
        for row in doc.get(tf.fieldname) or []:
            urls |= _collect_urls(row, child_fields)
    if urls:
        _attach_orphans(urls, doc.doctype, doc.name)


def _attach_fieldnames(doctype: str) -> tuple[str, ...]:
    """Tên các field `Attach`/`Attach Image` của một DocType (đọc từ meta đã cache)."""
    if not doctype:
        return ()
    try:
        meta = frappe.get_meta(doctype)
    except Exception:
        return ()
    return tuple(df.fieldname for df in meta.fields
                 if df.fieldtype in _ATTACH_FIELDTYPES)


def _collect_urls(row, fieldnames: tuple[str, ...]) -> set[str]:
    out: set[str] = set()
    for fn in fieldnames:
        val = row.get(fn)
        if val and isinstance(val, str) and val.startswith("/"):
            out.add(val)
    return out


def _attach_orphans(urls: set[str], doctype: str, docname: str) -> None:
    """Gắn các File mồ côi (chưa thuộc hồ sơ nào) vào (doctype, docname)."""
    rows = frappe.get_all(
        "File",
        filters={"file_url": ["in", list(urls)], "attached_to_doctype": ["is", "not set"]},
        fields=["name"],
        ignore_permissions=True,
    )
    for r in rows:
        frappe.db.set_value("File", r["name"], {
            "attached_to_doctype": doctype,
            "attached_to_name": docname,
        }, update_modified=False)
