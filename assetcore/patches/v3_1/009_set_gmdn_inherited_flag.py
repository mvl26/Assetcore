# assetcore/patches/v3_1/009_set_gmdn_inherited_flag.py
# Copyright (c) 2026, AssetCore Team
"""
Post-model-sync: backfill gmdn_inherited cho IMM Device Model cũ (P3 Hybrid).

Cần chạy SAU model sync vì cột gmdn_inherited phải tồn tại trong schema.

Quy tắc (docs/res/plans/2026-05-19-gmdn-code-sync-strategy.md §6 C3):
  - gmdn_code rỗng                       → gmdn_inherited = 1 (kế thừa lười)
  - gmdn_code == Category.gmdn_code      → gmdn_inherited = 1 (kế thừa)
  - gmdn_code khác Category.gmdn_code    → gmdn_inherited = 0 (override cố ý)

CHỈ set cờ gmdn_inherited. KHÔNG sửa gmdn_code (data hiện tại là rác —
blocker §8, không thuộc phạm vi cơ chế P3). Idempotent: chạy lại không đổi
kết quả vì luôn tính lại từ so sánh hiện trạng.
"""
from __future__ import annotations

import frappe


def execute() -> None:
    if not frappe.db.table_exists("IMM Device Model"):
        return

    models = frappe.get_all(
        "IMM Device Model",
        fields=["name", "gmdn_code", "asset_category"],
    )
    set_inherited = 0
    set_override = 0
    for m in models:
        cat_code = None
        if m.asset_category:
            cat_code = frappe.db.get_value(
                "AC Asset Category", m.asset_category, "gmdn_code"
            )
        my_code = (m.gmdn_code or "").strip()
        inherited = 1 if (not my_code or my_code == (cat_code or "")) else 0
        # set_value trực tiếp: KHÔNG trigger controller validate/cascade,
        # KHÔNG đụng gmdn_code.
        frappe.db.set_value(
            "IMM Device Model", m.name, "gmdn_inherited", inherited,
            update_modified=False,
        )
        if inherited:
            set_inherited += 1
        else:
            set_override += 1

    frappe.db.commit()
    print(
        f"[AssetCore][patch 009] gmdn_inherited backfill: "
        f"{set_inherited} inherited, {set_override} override "
        f"(tổng {len(models)} Model). gmdn_code KHÔNG thay đổi."
    )
