# assetcore/patches/v3_1/010_consolidate_sla_priority_p1.py
# Copyright (c) 2026, AssetCore Team
"""
Gộp priority SLA: bỏ `P1 Critical` / `P1 High` (dư thừa) → còn 4 mức `P1..P4`.

Mức độ nghiêm trọng đã do `risk_class` (Low/Medium/High/Critical) đảm nhận,
nên tách đôi P1 là thừa. Sau thay đổi này Select option của IMM SLA Policy
chỉ còn `P1\\nP2\\nP3\\nP4`.

Việc cần làm (idempotent — chạy lại không đổi kết quả):
  1. Xóa các fixture doc cũ tên `P1C-Critical / P1C-High / P1H-High`
     (tên mới là `P1-Critical / P1-High` do fixtures sync tạo lại sau patch).
  2. Remap mọi cột `priority` còn giữ giá trị 'P1 Critical' / 'P1 High' → 'P1'
     trên mọi DocType có cột đó (SLA Policy, Work Order, ...).

CHẠY TRƯỚC fixtures sync: migrate thực thi patches xong mới sync_fixtures,
nên xóa doc cũ ở đây rồi fixtures sẽ tạo bản P1-* sạch.
"""
from __future__ import annotations

import frappe

_LEGACY_VALUES = ("P1 Critical", "P1 High")
_LEGACY_POLICY_NAMES = ("P1C-Critical", "P1C-High", "P1H-High")


def execute() -> None:
    # 1. Xóa fixture doc SLA Policy cũ (tên đổi → không tự bị fixtures dọn).
    for legacy in _LEGACY_POLICY_NAMES:
        if frappe.db.exists("IMM SLA Policy", legacy):
            frappe.delete_doc("IMM SLA Policy", legacy, force=True, ignore_permissions=True)

    # 2. Remap stray priority values trên mọi DocType có cột `priority`.
    remapped = 0
    for dt in frappe.get_all("DocType", filters={"issingle": 0}, pluck="name"):
        try:
            if not frappe.db.has_column(dt, "priority"):
                continue
        except Exception:
            continue
        for old in _LEGACY_VALUES:
            rows = frappe.get_all(dt, filters={"priority": old}, pluck="name")
            for name in rows:
                frappe.db.set_value(dt, name, "priority", "P1",
                                    update_modified=False)
                remapped += 1

    frappe.db.commit()
    print(f"[010_consolidate_sla_priority_p1] legacy policies dropped, "
          f"{remapped} row(s) remapped → P1")
