"""Migrate IMM SLA Policy escalation fields from Role link to User link.

Old: escalation_l1_role / escalation_l2_role  (Link → Role)
New: escalation_l1_user / escalation_l2_user  (Link → User)

Lý do: leo thang theo Role match toàn bộ user có role đó (rộng + ai nhận?).
Theo User mới rõ ràng — đúng người, đúng phiên trực, có thể audit.

Dữ liệu cũ (role name VD: "IMM Workshop Lead") không phải User ID hợp lệ
(User ID là email) → migration set NULL để admin gán lại thủ công.
"""
from __future__ import annotations
import frappe


_TABLE = "tabIMM SLA Policy"


def _has_column(table: str, col: str) -> bool:
    rows = frappe.db.sql(
        f"SHOW COLUMNS FROM `{table}` LIKE %s", (col,)
    )
    return bool(rows)


def execute() -> None:
    """Rename DB columns + clear old role values; sync from doctype JSON."""
    if not frappe.db.exists("DocType", "IMM SLA Policy"):
        return

    # 1. Rename columns nếu còn tên cũ
    for old, new in [
        ("escalation_l1_role", "escalation_l1_user"),
        ("escalation_l2_role", "escalation_l2_user"),
    ]:
        if _has_column(_TABLE, old) and not _has_column(_TABLE, new):
            frappe.db.sql_ddl(
                f"ALTER TABLE `{_TABLE}` "
                f"CHANGE COLUMN `{old}` `{new}` VARCHAR(140) DEFAULT NULL"
            )

    # 2. Xóa giá trị cũ (role name không phải User ID hợp lệ)
    if _has_column(_TABLE, "escalation_l1_user"):
        frappe.db.sql(
            f"UPDATE `{_TABLE}` SET escalation_l1_user = NULL "
            "WHERE escalation_l1_user IS NOT NULL "
            "AND escalation_l1_user NOT IN (SELECT name FROM `tabUser`)"
        )
    if _has_column(_TABLE, "escalation_l2_user"):
        frappe.db.sql(
            f"UPDATE `{_TABLE}` SET escalation_l2_user = NULL "
            "WHERE escalation_l2_user IS NOT NULL "
            "AND escalation_l2_user NOT IN (SELECT name FROM `tabUser`)"
        )

    # 3. Reload doctype để Frappe nhận field mới
    frappe.reload_doc("assetcore", "doctype", "imm_sla_policy")
    frappe.clear_cache(doctype="IMM SLA Policy")
