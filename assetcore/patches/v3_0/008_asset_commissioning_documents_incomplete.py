"""Asset Commissioning — thêm flag documents_incomplete + note.

Cho phép user mark phiếu thiếu hồ sơ + bổ sung sau (không block duyệt).
"""
from __future__ import annotations
import frappe


def execute() -> None:
    if not frappe.db.exists("DocType", "Asset Commissioning"):
        return
    frappe.reload_doc("assetcore", "doctype", "asset_commissioning")
    # Default 0 cho records hiện có (không thiếu hồ sơ)
    frappe.db.sql(
        "UPDATE `tabAsset Commissioning` SET documents_incomplete=0 "
        "WHERE documents_incomplete IS NULL"
    )
    frappe.clear_cache(doctype="Asset Commissioning")
