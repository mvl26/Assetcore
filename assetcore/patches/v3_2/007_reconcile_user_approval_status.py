"""Reconcile ``User.imm_approval_status`` lệch với thực tế truy cập.

Root cause: Custom Field ``imm_approval_status`` từng có ``default='Pending'``.
Hậu quả: MỌI user tạo ngoài luồng self-signup (test fixture, ERPNext desk, bench,
import) bị gán ``Pending`` dù ``enabled=1`` — badge "Chờ duyệt" giả, không có gate
duyệt thật phía sau. User chỉ thấy trạng thái vô nghĩa.

Invariant đúng (xem docs/imm-00/04_Backend_Design.md §User Account & Approval):
  - ``Pending``  ⟺ ``enabled=0`` (self-signup, đang chờ admin duyệt).
  - ``enabled=1`` ⇒ đã có quyền truy cập ⇒ ``Approved`` (hoặc rỗng nếu ngoài IMM).

Patch (idempotent, safe re-run):
  1. enabled=1 AND status='Pending' → 'Approved' (mâu thuẫn: có quyền mà "chờ duyệt").
     Stamp ``imm_approved_by='Administrator'`` + ``imm_approved_at=now`` để giữ
     audit trail (trước đây không có ai duyệt → reconcile tự ghi nguồn).
  2. Administrator → '' (root user, không thuộc luồng duyệt IMM).
Genuine pending self-signup (enabled=0, status='Pending') giữ NGUYÊN.
"""
from __future__ import annotations

import frappe
from frappe.utils import now_datetime


def execute() -> None:
    if not frappe.db.has_column("User", "imm_approval_status"):
        return

    # 1. Mâu thuẫn: enabled nhưng vẫn 'Pending' → Approved (đã có quyền = đã duyệt).
    contradictory = frappe.get_all(
        "User",
        filters={
            "imm_approval_status": "Pending",
            "enabled": 1,
            "name": ["!=", "Guest"],
        },
        pluck="name",
    )
    stamp = now_datetime()
    for name in contradictory:
        frappe.db.set_value(
            "User", name,
            {
                "imm_approval_status": "Approved",
                "imm_approved_by": "Administrator",
                "imm_approved_at": stamp,
            },
            update_modified=False,
        )

    # 2. Administrator root user — không thuộc luồng duyệt IMM → để rỗng.
    if frappe.db.exists("User", "Administrator"):
        frappe.db.set_value(
            "User", "Administrator", "imm_approval_status", "",
            update_modified=False,
        )

    frappe.db.commit()
    print(
        f"[patches.v3_2.007_reconcile_user_approval_status] "
        f"reconciled_enabled_pending={len(contradictory)}"
    )
