# Copyright (c) 2026, AssetCore Team
"""
Pre-model-sync: chuẩn hóa gmdn_code trên AC Asset Category trước khi
schema sync thêm UNIQUE index.

MySQL UNIQUE cho phép nhiều NULL nhưng KHÔNG cho nhiều '' (empty string).
Dữ liệu cũ có nhiều category gmdn_code rỗng → ALTER TABLE thêm UNIQUE fail
với "Duplicate entry '' for key 'gmdn_code'".

Patch này:
  1. Set gmdn_code = NULL cho mọi dòng rỗng/NULL.
  2. Khử trùng các gmdn_code non-empty bị lặp (giữ dòng đầu, hậu tố dòng sau).
"""
from __future__ import annotations

import frappe


def execute() -> None:
    if not frappe.db.table_exists("AC Asset Category"):
        return

    # 1. Empty → NULL (UNIQUE chấp nhận nhiều NULL)
    frappe.db.sql(
        """
        UPDATE `tabAC Asset Category`
        SET gmdn_code = NULL
        WHERE gmdn_code = '' OR gmdn_code IS NULL
        """
    )

    # 2. Khử trùng giá trị non-empty bị lặp
    dupes = frappe.db.sql(
        """
        SELECT gmdn_code
        FROM `tabAC Asset Category`
        WHERE gmdn_code IS NOT NULL AND gmdn_code != ''
        GROUP BY gmdn_code
        HAVING COUNT(*) > 1
        """,
        as_dict=True,
    )
    for row in dupes:
        code = row["gmdn_code"]
        names = frappe.db.sql(
            """
            SELECT name FROM `tabAC Asset Category`
            WHERE gmdn_code = %s ORDER BY creation
            """,
            (code,),
            as_dict=True,
        )
        # Giữ dòng đầu, gắn hậu tố cho các dòng sau
        for idx, rec in enumerate(names[1:], start=1):
            frappe.db.set_value(
                "AC Asset Category", rec["name"], "gmdn_code",
                f"{code}-DUP{idx}", update_modified=False,
            )

    frappe.db.commit()
