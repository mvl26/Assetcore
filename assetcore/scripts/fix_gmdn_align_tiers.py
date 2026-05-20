# Copyright (c) 2026, AssetCore Team
"""
One-off: căn 3 tầng GMDN cho NHẤT QUÁN (Model là nguồn).

Bối cảnh: Category.gmdn_code phần lớn NULL, Model giữ giá trị (từ seed/import).
Mục tiêu: Category.gmdn_code = Model.gmdn_code = Asset.gmdn_code cho từng dòng
thiết bị, để P3 cascade (patch 009) duy trì nhất quán về sau.

⚠️ Đây CHỈ là fix tính nhất quán nội bộ. Các mã hiện tại CHƯA phải mã BYT
đúng (xem docs/res/plans/2026-05-19-gmdn-code-sync-strategy.md §8 — chờ QĐ
3107 / nguồn BYT tổng quát). gmdn_term KHÔNG backfill được (không có nguồn).

Chạy: bench --site miyano execute assetcore.scripts.fix_gmdn_align_tiers.run
"""
from __future__ import annotations

import frappe


def run() -> None:
    models = frappe.db.sql(
        """SELECT name, model_name, asset_category, gmdn_code, gmdn_inherited
           FROM `tabIMM Device Model` WHERE gmdn_code IS NOT NULL AND gmdn_code != ''""",
        as_dict=True,
    )
    changes = {"category": 0, "model_flag": 0, "asset": 0}

    for m in models:
        code = m["gmdn_code"]
        cat = m["asset_category"]
        if not cat:
            print(f"SKIP {m['name']}: không có asset_category")
            continue

        cat_code = frappe.db.get_value("AC Asset Category", cat, "gmdn_code")
        if cat_code != code:
            print(f"CATEGORY {cat}: gmdn_code {cat_code!r} -> {code!r} "
                  f"(nguồn: Model {m['name']} {m['model_name']})")
            frappe.db.set_value("AC Asset Category", cat, "gmdn_code", code)
            changes["category"] += 1

        # Model giờ khớp Category → là 'inherited/aligned' để P3 cascade hoạt động
        if m["gmdn_inherited"] != 1:
            frappe.db.set_value("IMM Device Model", m["name"], "gmdn_inherited", 1)
            print(f"MODEL {m['name']}: gmdn_inherited 0 -> 1 (đã khớp Category)")
            changes["model_flag"] += 1

        # Resync Asset của Model này
        assets = frappe.db.get_all(
            "AC Asset", filters={"device_model": m["name"]}, pluck="name"
        )
        for a in assets:
            a_code = frappe.db.get_value("AC Asset", a, "gmdn_code")
            if a_code != code:
                frappe.db.set_value("AC Asset", a, "gmdn_code", code)
                print(f"ASSET {a}: gmdn_code {a_code!r} -> {code!r}")
                changes["asset"] += 1

    # Category không có Model → để nguyên (vd Thiet-bi-Phau-thuat-Can-thiep)
    orphan_cats = frappe.db.sql(
        """SELECT c.name, c.gmdn_code FROM `tabAC Asset Category` c
           WHERE NOT EXISTS (SELECT 1 FROM `tabIMM Device Model` m
                             WHERE m.asset_category = c.name)""",
        as_dict=True,
    )
    for c in orphan_cats:
        print(f"ORPHAN CATEGORY {c['name']}: gmdn_code={c['gmdn_code']!r} "
              f"(không có Model — giữ nguyên)")

    frappe.db.commit()
    print(f"\nDONE — category={changes['category']} "
          f"model_flag={changes['model_flag']} asset={changes['asset']}")
    print("LƯU Ý: gmdn_term toàn bộ NULL — không backfill (thiếu nguồn BYT, §8).")
