"""Revert Service Contract về DocType lưu trữ đơn giản (không submit, không duyệt).

- Drop 4 cột approval workflow (approval_status, approver, approved_at, rejection_reason)
- Drop cột amended_from (chỉ dùng khi is_submittable=1)
- Reset docstatus=1 → 0 cho records đã submit (vì không còn submittable)
- Reload doctype để Frappe sync schema mới
"""
from __future__ import annotations
import frappe


_TABLE = "tabService Contract"


def _has_column(col: str) -> bool:
    rows = frappe.db.sql(f"SHOW COLUMNS FROM `{_TABLE}` LIKE %s", (col,))
    return bool(rows)


def execute() -> None:
    if not frappe.db.exists("DocType", "Service Contract"):
        return

    # Reset docstatus về 0 trước khi reload (Frappe v15 vẫn giữ cột docstatus
    # ngay cả khi is_submittable=0 — chuẩn hóa giá trị để FE hiển thị đúng).
    frappe.db.sql(f"UPDATE `{_TABLE}` SET docstatus=0 WHERE docstatus IN (1, 2)")

    # Drop columns nếu còn (sync_meta sẽ không tự drop columns).
    for col in ("approval_status", "approver", "approved_at",
                "rejection_reason", "amended_from"):
        if _has_column(col):
            try:
                frappe.db.sql_ddl(f"ALTER TABLE `{_TABLE}` DROP COLUMN `{col}`")
            except Exception:
                frappe.log_error(frappe.get_traceback(),
                                 f"Drop column {col} failed (may already be dropped)")

    # Reload doctype JSON
    frappe.reload_doc("assetcore", "doctype", "service_contract")
    frappe.clear_cache(doctype="Service Contract")
