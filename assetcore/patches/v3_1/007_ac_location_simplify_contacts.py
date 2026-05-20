# Copyright (c) 2026, AssetCore Team
"""Patch v3_1.007 — AC Location simplify contacts.

Mục tiêu:
- Gộp 3 trường liên hệ (`emergency_contact`, `dept_head`, `technical_contact`)
  thành 2 trường (`dept_head`, `contact_phone`).
- `contact_phone` mới sẽ `fetch_from: dept_head.mobile_no` ở DocType.

Quy tắc migrate dữ liệu (chỉ chạy 1 lần):
1. Nếu `contact_phone` rỗng & `emergency_contact` có giá trị → copy sang `contact_phone`.
2. Nếu `dept_head` rỗng & `technical_contact` có giá trị → copy sang `dept_head`.
3. Drop column `emergency_contact` và `technical_contact` (sau khi đã migrate).
"""
from __future__ import annotations

import frappe


def execute() -> None:
    table = "tabAC Location"

    cols = {c[0] for c in frappe.db.sql(f"SHOW COLUMNS FROM `{table}`")}
    has_emergency = "emergency_contact" in cols
    has_technical = "technical_contact" in cols
    has_contact_phone = "contact_phone" in cols

    if not (has_emergency or has_technical):
        # Nothing legacy to migrate; DocType sync will add contact_phone if missing.
        return

    if not has_contact_phone:
        # DocType sync chưa chạy → tạo column tạm để copy dữ liệu vào
        frappe.db.sql(f"ALTER TABLE `{table}` ADD COLUMN `contact_phone` VARCHAR(140) DEFAULT NULL")

    # 1. Copy emergency_contact → contact_phone
    if has_emergency:
        frappe.db.sql(f"""
            UPDATE `{table}`
            SET contact_phone = emergency_contact
            WHERE (contact_phone IS NULL OR contact_phone = '')
              AND emergency_contact IS NOT NULL AND emergency_contact != ''
        """)

    # 2. Copy technical_contact → dept_head
    if has_technical:
        frappe.db.sql(f"""
            UPDATE `{table}`
            SET dept_head = technical_contact
            WHERE (dept_head IS NULL OR dept_head = '')
              AND technical_contact IS NOT NULL AND technical_contact != ''
        """)

    frappe.db.commit()

    # 3. Drop legacy columns
    if has_emergency:
        frappe.db.sql(f"ALTER TABLE `{table}` DROP COLUMN `emergency_contact`")
    if has_technical:
        frappe.db.sql(f"ALTER TABLE `{table}` DROP COLUMN `technical_contact`")

    frappe.db.commit()
    frappe.clear_cache(doctype="AC Location")
