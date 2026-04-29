"""Thêm workflow duyệt cho Service Contract.

Backfill cho records hiện có:
- docstatus=1 → approval_status='Approved' (đã submit = đã được "duyệt" theo logic cũ)
- docstatus=0 → approval_status='Draft'
- docstatus=2 (cancelled) → giữ nguyên Draft (Frappe sẽ filter ra)
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

    # Frappe sync_meta sẽ tự ALTER TABLE add columns. Patch chỉ backfill data.
    frappe.reload_doc("assetcore", "doctype", "service_contract")

    if _has_column("approval_status"):
        # Backfill từ docstatus
        frappe.db.sql(
            f"UPDATE `{_TABLE}` "
            "SET approval_status='Approved' "
            "WHERE docstatus=1 AND (approval_status IS NULL OR approval_status='Draft')"
        )
        frappe.db.sql(
            f"UPDATE `{_TABLE}` "
            "SET approval_status='Draft' "
            "WHERE docstatus=0 AND approval_status IS NULL"
        )

    frappe.clear_cache(doctype="Service Contract")
