# Copyright (c) 2026, AssetCore Team
"""Backfill admin override (AssetCore Super Admin + System Manager) vào MỌI
transition group của MỌI AssetCore Workflow trên site LIVE.

VÌ SAO: Frappe enforce quyền workflow theo TỪNG transition group (state, action,
next_state); `ignore_permissions=True` KHÔNG bypass `validate_workflow` (LL-BE-62).
Profile "Quản trị viên IT" (QTV) chỉ cấp `AssetCore Super Admin` (+ base) — 146
transition-group thiếu role này ⇒ QTV bị WorkflowPermissionError ("Bạn không có
quyền ..."). Đây là công cụ sync luật đã sửa ở fixtures/workflow.json xuống site
đang chạy MÀ KHÔNG cần `bench migrate` (re-import toàn bộ fixtures).

⚠️ SCOPE — CHỈ WORKFLOW ASSETCORE (memory `workflow_admin_override_rbac`):
  Site triển khai (vd `miyano`) chạy MULTI-APP: assetcore + mvl_accounting +
  antmed_crm + workflowcore cùng 1 DB. Bảng `Workflow` là SHARED. Bản `run()` cũ
  dùng `frappe.get_all("Workflow")` → lặp qua CẢ workflow của app khác và clone-append
  admin-role AssetCore vào chúng ('MVL Duyệt thanh toán', 'Cong Tac Approval') — RÒ RỈ
  role sang domain không liên quan. TUYỆT ĐỐI KHÔNG touch foreign workflow.
  SoT scope = `_assetcore_workflow_names()` (đọc thẳng fixtures/workflow.json, đồng bộ
  danh sách 22 Workflow khai trong hooks.py fixtures block). Nếu lỡ nhiễm foreign →
  dùng `revert_foreign()` để gỡ đúng row đã clone-append.

ĐẶC ĐIỂM `run()`:
  - Idempotent: chạy lần 2 → 0 thêm.
  - Chỉ APPEND role rows (clone từ transition hiện có của group, giữ nguyên
    condition/allow_self_approval/... — admin có quyền role như manager, KHÔNG
    bypass data-guard). KHÔNG xoá/đổi row nào.
  - ignore_links: bỏ qua _validate_links (một số Workflow Action Master cũ thiếu —
    dữ liệu tồn dư, không liên quan; quyền transition đọc thẳng từ Workflow.transitions
    lúc runtime, không cần master).

Chạy (review-friendly, KHÔNG cần migrate):
    bench --site <site> execute assetcore.setup.backfill_workflow_admin.run

Gỡ nhiễm foreign (HARD-STOP USER lane — không tự chạy write):
    bench --site <site> execute assetcore.setup.backfill_workflow_admin.revert_foreign
    bench --site <site> execute assetcore.setup.backfill_workflow_admin.revert_foreign \
        --kwargs '{"dry_run": 0}'
"""
from __future__ import annotations

import json
from collections import defaultdict

import frappe

# Admin god-mode override — khớp pattern 13 workflow đang hoạt động.
ADMIN_ROLES = ["AssetCore Super Admin", "System Manager"]
_ADMIN_SET = set(ADMIN_ROLES)
_CLONE_FIELDS = [
    "state", "action", "next_state", "condition",
    "allow_self_approval", "send_email_to_creator",
]


def _assetcore_workflow_names() -> set[str]:
    """SoT scope — tên Workflow AssetCore đọc TRỰC TIẾP từ fixtures/workflow.json.

    THUẦN + deterministic: chỉ đọc 1 file fixtures trong app (KHÔNG query live DB,
    KHÔNG phụ thuộc app khác). Đồng bộ 1:1 với danh sách 22 Workflow khai trong
    `hooks.py` fixtures block. Dùng làm hàng rào scope cho `run()`/`revert_foreign()`
    trên site multi-app — mọi Workflow NGOÀI tập này là của app khác, KHÔNG được chạm.

    Returns:
        set[str]: tên đúng của 22 Workflow AssetCore.
    """
    path = frappe.get_app_path("assetcore", "fixtures", "workflow.json")
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return {d.get("name") for d in data if d.get("doctype") == "Workflow"}


def run(dry_run: int = 0) -> dict:
    """Backfill admin roles vào transition groups còn thiếu — CHỈ workflow AssetCore.

    Chỉ lặp qua `_assetcore_workflow_names()` (22 workflow) → KHÔNG mutate workflow
    của app khác (mvl_accounting/antmed_crm/workflowcore) trên site chung.

    Args:
        dry_run: 1 = chỉ đếm, KHÔNG ghi. 0 = áp dụng thật (default).

    Returns:
        {dry_run, added, workflows_touched, groups_remaining_blocked, per_workflow}
    """
    dry = bool(int(dry_run))
    wfs = sorted(_assetcore_workflow_names())

    added_total = 0
    per_workflow: dict[str, int] = {}
    for wf in wfs:
        if not frappe.db.exists("Workflow", wf):
            # Fresh site / workflow chưa provision — bỏ qua an toàn (scope vẫn đúng).
            continue
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

    # Verify invariant (post-state khi áp thật; pre-state khi dry-run) — CHỈ scope AssetCore.
    blocked = 0
    for wf in wfs:
        if not frappe.db.exists("Workflow", wf):
            continue
        doc = frappe.get_doc("Workflow", wf)
        g: dict[tuple, set] = defaultdict(set)
        for t in doc.transitions:
            g[(t.state, t.action, t.next_state)].add(t.allowed)
        for roles in g.values():
            if _ADMIN_SET - roles:
                blocked += 1

    result = {
        "dry_run": dry,
        "added": added_total,
        "workflows_touched": len(per_workflow),
        "groups_remaining_blocked": blocked,
        "per_workflow": per_workflow,
    }
    frappe.logger().info(f"backfill_workflow_admin.run: {result}")
    print(result)
    return result


def _clone_appended_admin_rows(transitions) -> list:
    """Xác định đúng các row admin-role mà `run()` đã clone-append vào 1 workflow.

    THUẦN — nhận list transition rows (frappe child doc HOẶC object có các attr
    `state/action/next_state/allowed/condition/allow_self_approval/send_email_to_creator`),
    trả về list các row CẦN GỠ (giữ nguyên input, không mutate).

    Cách nhận diện (mirror chính xác `run()`): `run()` clone template = row ĐẦU của mỗi
    group `(state, action, next_state)`, sao y `_CLONE_FIELDS`, chỉ set `allowed` = admin
    role. Vậy 1 row là "clone-append" ⇔ (a) `allowed ∈ ADMIN_ROLES`, (b) 6 field
    `_CLONE_FIELDS` KHỚP HỆT template của group, (c) KHÔNG phải chính template row.
    Row gốc pre-existing (non-admin, hoặc admin nhưng lệch template) được GIỮ nguyên
    ⇒ chỉ gỡ đúng cái `run()` sinh ra. Idempotent: sau khi gỡ, group chỉ còn row gốc →
    chạy lại trả [].

    Returns:
        list: các transition row là clone-append của admin role.
    """
    groups: dict[tuple, list] = defaultdict(list)
    for t in transitions:
        groups[(getattr(t, "state", None),
                getattr(t, "action", None),
                getattr(t, "next_state", None))].append(t)

    to_remove: list = []
    for _key, rows in groups.items():
        template = rows[0]
        tsig = tuple(getattr(template, f, None) for f in _CLONE_FIELDS)
        for r in rows:
            if r is template:
                continue
            if getattr(r, "allowed", None) not in _ADMIN_SET:
                continue
            if tuple(getattr(r, f, None) for f in _CLONE_FIELDS) == tsig:
                to_remove.append(r)
    return to_remove


def revert_foreign(dry_run: int = 1) -> dict:
    """Gỡ admin-role rows mà `run()` cũ đã clone-append NHẦM vào workflow app khác.

    ⚠️ HARD-STOP USER lane khi áp thật (dry_run=0) — thao tác WRITE + commit trên
    dữ liệu app khác. Mặc định dry_run=1 (chỉ báo cáo).

    Với MỖI Workflow NGOÀI `_assetcore_workflow_names()` (= foreign, của mvl_accounting/
    antmed_crm/workflowcore...), tính đúng các row clone-append (`_clone_appended_admin_rows`)
    và gỡ CHỈ các row đó — GIỮ nguyên row gốc pre-existing. Idempotent: chạy lần 2 → 0.

    Args:
        dry_run: 1 = chỉ đếm (default). 0 = gỡ thật + commit + clear_cache.

    Returns:
        {dry_run, removed, workflows_touched, per_workflow}
    """
    dry = bool(int(dry_run))
    scope = _assetcore_workflow_names()
    foreign = [w for w in frappe.get_all("Workflow", pluck="name") if w not in scope]

    removed_total = 0
    per_workflow: dict[str, int] = {}
    for wf in foreign:
        doc = frappe.get_doc("Workflow", wf)
        rows_to_remove = _clone_appended_admin_rows(doc.transitions)
        if not rows_to_remove:
            continue
        per_workflow[wf] = len(rows_to_remove)
        removed_total += len(rows_to_remove)
        if dry:
            continue
        remove_names = {r.name for r in rows_to_remove}
        doc.set("transitions", [t for t in doc.transitions if t.name not in remove_names])
        doc.flags.ignore_links = True
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_permissions = True
        doc.save(ignore_permissions=True)

    if not dry:
        frappe.db.commit()
        frappe.clear_cache()

    result = {
        "dry_run": dry,
        "removed": removed_total,
        "workflows_touched": len(per_workflow),
        "per_workflow": per_workflow,
    }
    frappe.logger().info(f"backfill_workflow_admin.revert_foreign: {result}")
    print(result)
    return result
