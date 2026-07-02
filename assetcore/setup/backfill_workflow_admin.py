# Copyright (c) 2026, AssetCore Team
"""Backfill admin override (AssetCore Super Admin + System Manager) vào MỌI
transition group của MỌI AssetCore Workflow trên site LIVE.

VÌ SAO: Frappe enforce quyền workflow theo TỪNG transition group (state, action,
next_state); `ignore_permissions=True` KHÔNG bypass `validate_workflow` (LL-BE-62).
Profile "Quản trị viên IT" (QTV) chỉ cấp `AssetCore Super Admin` (+ base) — 146
transition-group thiếu role này ⇒ QTV bị WorkflowPermissionError ("Bạn không có
quyền ..."). Đây là công cụ sync luật đã sửa ở fixtures/workflow.json xuống site
đang chạy MÀ KHÔNG cần `bench migrate` (re-import toàn bộ fixtures).

ĐẶC ĐIỂM:
  - Idempotent: chạy lần 2 → 0 thêm.
  - Chỉ APPEND role rows (clone từ transition hiện có của group, giữ nguyên
    condition/allow_self_approval/... — admin có quyền role như manager, KHÔNG
    bypass data-guard). KHÔNG xoá/đổi row nào.
  - ignore_links: bỏ qua _validate_links (một số Workflow Action Master cũ thiếu —
    dữ liệu tồn dư, không liên quan; quyền transition đọc thẳng từ Workflow.transitions
    lúc runtime, không cần master).

Chạy (review-friendly, KHÔNG cần migrate):
    bench --site <site> execute assetcore.setup.backfill_workflow_admin.run
"""
from __future__ import annotations

from collections import defaultdict

import frappe

# Admin god-mode override — khớp pattern 13 workflow đang hoạt động.
ADMIN_ROLES = ["AssetCore Super Admin", "System Manager"]
_CLONE_FIELDS = [
    "state", "action", "next_state", "condition",
    "allow_self_approval", "send_email_to_creator",
]


def run(dry_run: int = 0) -> dict:
    """Backfill admin roles vào transition groups còn thiếu.

    Args:
        dry_run: 1 = chỉ đếm, KHÔNG ghi. 0 = áp dụng thật (default).

    Returns:
        {added, workflows_touched, groups_remaining_blocked, per_workflow}
    """
    dry = bool(int(dry_run))
    admin_set = set(ADMIN_ROLES)
    wfs = frappe.get_all("Workflow", pluck="name")

    added_total = 0
    per_workflow: dict[str, int] = {}
    for wf in wfs:
        doc = frappe.get_doc("Workflow", wf)
        groups: dict[tuple, list] = defaultdict(list)
        for t in doc.transitions:
            groups[(t.state, t.action, t.next_state)].append(t)

        specs = []
        for _key, rows in groups.items():
            present = {r.allowed for r in rows}
            template = rows[0]
            for role in ADMIN_ROLES:
                if role not in present:
                    spec = {f: getattr(template, f) for f in _CLONE_FIELDS}
                    spec["allowed"] = role
                    specs.append(spec)
        if not specs:
            continue
        per_workflow[wf] = len(specs)
        added_total += len(specs)
        if dry:
            continue
        for spec in specs:
            doc.append("transitions", spec)
        doc.flags.ignore_links = True
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_permissions = True
        doc.save(ignore_permissions=True)

    if not dry:
        frappe.db.commit()
        frappe.clear_cache()

    # Verify invariant (post-state khi áp thật; pre-state khi dry-run)
    blocked = 0
    for wf in wfs:
        doc = frappe.get_doc("Workflow", wf)
        g: dict[tuple, set] = defaultdict(set)
        for t in doc.transitions:
            g[(t.state, t.action, t.next_state)].add(t.allowed)
        for roles in g.values():
            if admin_set - roles:
                blocked += 1

    result = {
        "dry_run": dry,
        "added": added_total,
        "workflows_touched": len(per_workflow),
        "groups_remaining_blocked": blocked,
        "per_workflow": per_workflow,
    }
    frappe.logger().info(f"backfill_workflow_admin: {result}")
    print(result)
    return result
