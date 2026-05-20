# assetcore/patches/v3_1/008_drop_gmdn_status.py
# Copyright (c) 2026, AssetCore Team
"""
Pre-model-sync: xoá column gmdn_status khỏi tabAC Asset trước khi schema sync.

Lý do: gmdn_status (In Use / Not Use) trộn ngữ nghĩa với lifecycle_status —
ref docs/res/gmdn-asset-category-analysis.md §6. Lọc thiết bị chuyển sang
dùng gmdn_code (kế thừa từ Asset Category).
"""
from __future__ import annotations

import frappe


def execute() -> None:
    if not frappe.db.table_exists("AC Asset"):
        return

    cols = frappe.db.sql(
        """SELECT COLUMN_NAME FROM information_schema.COLUMNS
           WHERE TABLE_SCHEMA = DATABASE()
             AND TABLE_NAME = 'tabAC Asset'
             AND COLUMN_NAME = 'gmdn_status'""",
        as_dict=True,
    )
    if not cols:
        return

    frappe.db.sql("ALTER TABLE `tabAC Asset` DROP COLUMN `gmdn_status`")
    frappe.db.commit()
