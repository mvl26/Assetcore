# Copyright (c) 2026, AssetCore Team
"""Đồng bộ vai trò NGHIỆP VỤ vào transition của Workflow AssetCore (ADR-CORE-01).

VÌ SAO. Hôm nay service ghi thẳng ``doc.status`` nên chỉ bị chặn bởi capability
(``rbac.require`` → DocPerm). Sau ADR-CORE-01, mọi chuyển trạng thái đi qua
``frappe.model.workflow.apply_workflow`` — hàm này CHỈ cho phép khi vai trò người dùng
nằm trong ``transition.allowed``. Đo 2026-07-22: **18/22 workflow** có vai trò giữ DocPerm
write/submit nhưng vắng mặt ở MỌI transition (đáng chú ý: ``PM Manager``,
``Repair Manager``, ``Calibration Manager`` vắng khỏi chính workflow module mình). Cắt
sang engine mà không sửa ⇒ tước quyền thao tác của đúng những người đó.

NGUYÊN TẮC CẤP — *chỉ đồng bộ, KHÔNG nâng quyền*. Phải thoả **CẢ HAI**:

    1. **R hiện KHÔNG có transition nào trong workflow đó.** Vai trò đã tham gia
       workflow thì các giới hạn của nó là CÓ CHỦ ĐÍCH — vd ``PM User`` có DocPerm
       ``write`` nhưng workflow cố ý chỉ cho cấp quản lý "Hủy phiếu"/"Đánh dấu trễ hạn".
       Suy từ DocPerm mà cấp thêm cho họ là diễn giải sai ý định của người thiết kế
       workflow. Chỉ vá đúng lỗ hổng đã đo: vai trò bị bỏ quên HOÀN TOÀN.
    2. **R đã có sẵn DocPerm mà transition group đòi hỏi.** Quyền đòi hỏi suy từ
       ``doc_status`` của state đích: ``0 → write``, ``1 → submit``, ``2 → cancel`` —
       đúng nhánh ``apply_workflow`` chạy (``doc.save()`` / ``doc.submit()`` /
       ``doc.cancel()``).

    Nhờ hai điều kiện đó, module này **không cấp thêm bất kỳ quyền thực chất nào** — nó
    chỉ gỡ tình trạng "có quyền trên tài liệu nhưng không có nút nào bấm được".

PHẠM VI — chỉ **vai trò nghiệp vụ nội bộ** (``<Domain> Manager`` / ``<Domain> User``):
    - ``Vendor Engineer`` CỐ Ý loại trừ: cách ly nhà cung cấp là bất biến kiến trúc
      (CLAUDE.md §5/§19), không được nới rộng bằng một script backfill.
    - ``AssetCore Auditor`` chỉ đọc ⇒ tự nhiên không đủ điều kiện.
    - ``AssetCore Super Admin`` / ``System Manager`` đã do
      ``backfill_workflow_admin.run`` lo — module này KHÔNG đụng tới.
    - Chỉ 22 Workflow AssetCore (``_assetcore_workflow_names``): site triển khai chạy
      nhiều app dùng chung bảng ``Workflow``, tuyệt đối không chạm workflow app khác.

⚠️ KHÔNG xử lý chiều lệch NGƯỢC LẠI (``report_unexecutable_transitions``): vai trò ĐANG
   có transition nhưng THIẾU DocPerm mà nó đòi hỏi — vd ``PM User`` được cấp
   "Hoàn thành PM" (state ``Completed`` có ``doc_status=1``) trong khi không có DocPerm
   ``submit`` trên PM Work Order. Những transition đó **đã chết sẵn** hôm nay và sẽ thành
   lỗi cứng khi cắt sang engine. Sửa chúng đòi hỏi hoặc cấp thêm DocPerm (nâng quyền
   thật sự), hoặc đổi ``doc_status`` của state (đổi ngữ nghĩa bất biến của tài liệu) —
   cả hai đều là QUYẾT ĐỊNH CỦA NGƯỜI DÙNG, không phải việc của script. Hàm báo cáo
   dưới đây liệt kê chúng để đưa ra quyết định.

Chạy (KHÔNG cần ``bench migrate``):
    bench --site <site> execute assetcore.setup.backfill_workflow_domain_roles.run \
        --kwargs '{"dry_run": 1}'
    bench --site <site> execute assetcore.setup.backfill_workflow_domain_roles.run
    bench --site <site> execute \
        assetcore.setup.backfill_workflow_domain_roles.report_unexecutable_transitions
"""
from __future__ import annotations

from collections import defaultdict

import frappe

from assetcore.services.shared.constants import Roles
from assetcore.setup.backfill_workflow_admin import _assetcore_workflow_names

#: doc_status của state đích → DocPerm mà ``apply_workflow`` sẽ cần.
DOC_STATUS_PERMISSION = {"0": "write", "1": "submit", "2": "cancel"}

#: Chỉ vai trò nghiệp vụ nội bộ. Vendor/Auditor/Super Admin cố ý nằm ngoài (xem docstring).
GRANTABLE_ROLES = frozenset(Roles.DOMAIN_ROLES)

_CLONE_FIELDS = [
    "state", "action", "next_state", "condition",
    "allow_self_approval", "send_email_to_creator",
]


def _doc_perms(doctype: str) -> dict[str, set[str]]:
    """{role: {ptype đã cấp}} đọc từ metadata DocType đang hiệu lực."""
    perms: dict[str, set[str]] = defaultdict(set)
    for p in frappe.get_meta(doctype).permissions:
        for ptype in ("read", "write", "create", "submit", "cancel", "delete"):
            if p.get(ptype):
                perms[p.role].add(ptype)
    return perms


def _target_doc_status(workflow_doc) -> dict[str, str]:
    return {s.state: str(s.doc_status or "0") for s in workflow_doc.states}


def orphan_roles(workflow_doc) -> list[str]:
    """Vai trò nghiệp vụ có DocPerm write/submit nhưng KHÔNG có transition nào.

    Đây chính xác là tập đã đo được (18/22 workflow) — và là tập DUY NHẤT module này
    đụng tới. Vai trò đã tham gia workflow không nằm ở đây, nên giới hạn có chủ đích của
    chúng được giữ nguyên.
    """
    perms = _doc_perms(workflow_doc.document_type)
    participating = {t.allowed for t in workflow_doc.transitions}
    return sorted(
        role
        for role in GRANTABLE_ROLES
        if role not in participating and ({"write", "submit"} & perms.get(role, set()))
    )


def _missing_grants(workflow_doc) -> list[dict]:
    """Các dòng transition cần THÊM cho workflow này (rỗng = đã đồng bộ)."""
    orphans = orphan_roles(workflow_doc)
    if not orphans:
        return []

    perms = _doc_perms(workflow_doc.document_type)
    doc_status = _target_doc_status(workflow_doc)

    groups: dict[tuple, list] = defaultdict(list)
    for t in workflow_doc.transitions:
        groups[(t.state, t.action, t.next_state)].append(t)

    specs: list[dict] = []
    for (_state, _action, next_state), rows in groups.items():
        required = DOC_STATUS_PERMISSION.get(doc_status.get(next_state, "0"), "write")
        template = rows[0]
        for role in orphans:
            if required not in perms.get(role, set()):
                continue  # chưa có quyền trên tài liệu ⇒ KHÔNG cấp (không nâng quyền)
            spec = {f: getattr(template, f) for f in _CLONE_FIELDS}
            spec["allowed"] = role
            specs.append(spec)
    return specs


def run(dry_run: int = 0) -> dict:
    """Cấp transition cho vai trò nghiệp vụ ĐÃ có DocPerm tương ứng. Idempotent.

    Args:
        dry_run: 1 = chỉ đếm, KHÔNG ghi. 0 = áp dụng thật (default).

    Returns:
        {dry_run, added, workflows_touched, per_workflow}
    """
    dry = bool(int(dry_run))
    added = 0
    per_workflow: dict[str, int] = {}

    for name in sorted(_assetcore_workflow_names()):
        if not frappe.db.exists("Workflow", name):
            continue  # site mới chưa provision — bỏ qua an toàn
        doc = frappe.get_doc("Workflow", name)
        specs = _missing_grants(doc)
        if not specs:
            continue
        per_workflow[name] = len(specs)
        added += len(specs)
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

    result = {
        "dry_run": dry,
        "added": added,
        "workflows_touched": len(per_workflow),
        "per_workflow": per_workflow,
    }
    frappe.logger().info(f"backfill_workflow_domain_roles.run: {result}")
    print(result)
    return result


def report_unexecutable_transitions() -> dict:
    """Liệt kê transition ĐÃ cấp cho vai trò THIẾU DocPerm mà nó đòi hỏi (chỉ ĐỌC).

    Đây là chiều lệch mà script KHÔNG tự sửa được: những transition này đã chết sẵn hôm
    nay (bấm sẽ ra PermissionError) và sẽ thành lỗi cứng khi module cắt sang
    ``apply_workflow``. Xem docstring đầu module để biết vì sao cần người dùng quyết.
    """
    findings: dict[str, list[str]] = {}
    for name in sorted(_assetcore_workflow_names()):
        if not frappe.db.exists("Workflow", name):
            continue
        doc = frappe.get_doc("Workflow", name)
        perms = _doc_perms(doc.document_type)
        doc_status = _target_doc_status(doc)
        rows: set[str] = set()
        for t in doc.transitions:
            if t.allowed in ("System Manager", "Administrator"):
                continue
            required = DOC_STATUS_PERMISSION.get(doc_status.get(t.next_state, "0"), "write")
            if required not in perms.get(t.allowed, set()):
                rows.add(f"{t.allowed} → '{t.next_state}' cần DocPerm '{required}'")
        if rows:
            findings[f"{name} [{doc.document_type}]"] = sorted(rows)

    total = sum(len(v) for v in findings.values())
    print(f"{total} transition KHÔNG thực thi được, trên {len(findings)} workflow:")
    for wf, rows in findings.items():
        print(f"  {wf}")
        for r in rows:
            print(f"      {r}")
    return {"total": total, "workflows": len(findings), "findings": findings}
