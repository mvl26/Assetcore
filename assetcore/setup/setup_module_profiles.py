# Copyright (c) 2026, AssetCore Team
"""
Seed Module Profile (Frappe core DocType) cho AssetCore.

Module Profile kiểm soát module nào hiện trong sidebar của user.
3 profile cơ bản:
  - IMM - Admin    : Admin + Ops Manager (ít block nhất)
  - IMM - Standard : Tất cả internal role còn lại
  - IMM - Vendor   : Vendor Engineer (restricted view)

Idempotent — chạy lại không duplicate.
Wire vào hooks.after_install / hooks.after_migrate.

Chạy thủ công:
    bench --site <site> execute assetcore.setup.setup_module_profiles.run
"""
from __future__ import annotations

import frappe

# (profile_name, modules_to_block)
_PROFILES: list[tuple[str, list[str]]] = [
    ("IMM - Admin", [
        "Website", "Social", "Integrations",
    ]),
    ("IMM - Standard", [
        "Website", "Social", "Integrations", "Automation", "Geo",
    ]),
    ("IMM - Vendor", [
        "Website", "Social", "Integrations", "Automation", "Geo",
        "Email", "Printing", "Contacts",
    ]),
]


def _upsert_module_profile(profile_name: str, block: list[str]) -> str:
    if frappe.db.exists("Module Profile", profile_name):
        doc = frappe.get_doc("Module Profile", profile_name)
        current = {r.module for r in doc.block_modules}
        if current == set(block):
            return "skipped"
        doc.block_modules = []
        for m in block:
            doc.append("block_modules", {"module": m})
        doc.flags.ignore_permissions = True
        doc.save()
        return "updated"

    doc = frappe.new_doc("Module Profile")
    doc.module_profile_name = profile_name
    for m in block:
        doc.append("block_modules", {"module": m})
    doc.flags.ignore_permissions = True
    doc.insert()
    return "inserted"


def run() -> None:
    stats = {"inserted": 0, "updated": 0, "skipped": 0}
    for name, block in _PROFILES:
        stats[_upsert_module_profile(name, block)] += 1
    frappe.db.commit()
    print(
        f"[AssetCore] Module Profiles: {stats['inserted']} tạo mới, "
        f"{stats['updated']} cập nhật, {stats['skipped']} bỏ qua."
    )
