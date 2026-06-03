"""Patch v3_2.003 — BUG-014 fix.

Khắc phục seed data trước đây lưu `template_name` chứa slug (ví dụ
"Checklist PM Quý — Thiet-bi-Chan-doan-Hinh-anh") thay vì tên hiển thị.

Chiến lược:
- Duyệt tất cả PM Checklist Template.
- Nếu `template_name` kết thúc bằng `asset_category` (slug = name của
  AC Asset Category) thì thay phần đuôi đó bằng `category_name` (display).
- KHÔNG động vào `name` (autoname format:PMCT-{asset_category}-{pm_type})
  để tránh ảnh hưởng các record liên kết.
"""

from __future__ import annotations

import frappe


def execute() -> None:
    rows = frappe.get_all(
        "PM Checklist Template",
        fields=["name", "template_name", "asset_category"],
    )
    if not rows:
        return

    cat_slugs = {r["asset_category"] for r in rows if r.get("asset_category")}
    cat_map: dict[str, str] = {}
    if cat_slugs:
        cat_map = dict(
            frappe.get_all(
                "AC Asset Category",
                filters={"name": ["in", list(cat_slugs)]},
                fields=["name", "category_name"],
                as_list=True,
            )
        )

    fixed = 0
    for r in rows:
        tn = r.get("template_name") or ""
        slug = r.get("asset_category") or ""
        display = cat_map.get(slug) or ""
        if not (tn and slug and display) or slug == display:
            continue
        if tn.endswith(slug):
            new_tn = tn[: -len(slug)] + display
            frappe.db.set_value(
                "PM Checklist Template", r["name"], "template_name", new_tn,
                update_modified=False,
            )
            fixed += 1

    if fixed:
        frappe.db.commit()
        print(f"[patch v3_2.003] Fixed PM Checklist Template names: {fixed}")
