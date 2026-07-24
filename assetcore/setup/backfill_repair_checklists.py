# Copyright (c) 2026, AssetCore Team
"""Backfill danh mục Repair Checklist chuẩn cho phiếu CM (Asset Repair) ĐANG KẸT
0 dòng `repair_checklist` — gỡ deadlock `confirm_inspection` 422 (CR-50).

VÌ SAO: phiếu CM tạo TRƯỚC khi seeding land (04 §3.7 / ADR-IMM09-SEED-CHECKLIST)
có `repair_checklist == []` ⇒ chuỗi nghiệm thu `confirm_inspection` (doc.submit →
before_submit `validate_repair_checklist_complete`, BR-09-04) gặp `if not
doc.repair_checklist` → 422 → phiếu KẸT ở Pending Inspection, asset kẹt Under
Repair, MTTR không chốt. Công cụ này append 6 dòng chuẩn cho các phiếu đang kẹt
MÀ KHÔNG cần `bench migrate` / patch.

ĐẶC ĐIỂM:
  - Idempotent: bỏ qua phiếu đã có >=1 dòng + phiếu đã đóng (status terminal /
    docstatus != 0). Chạy lần 2 → 0 thêm.
  - CHỈ append (KHÔNG submit, KHÔNG đổi status/workflow_state) — dựng khung để KTV
    điền; BR-09-04 vẫn chặn đến khi điền đủ Pass.
  - Logic thực nằm ở `assetcore.services.imm09.backfill_repair_checklists` (cùng
    module giữ hằng `_STANDARD_REPAIR_CHECKLIST` + `RepairRepo`).

Chạy (review-friendly, KHÔNG cần migrate):
    # Preview (chỉ đếm, KHÔNG ghi):
    bench --site <site> execute assetcore.setup.backfill_repair_checklists.run \
        --kwargs '{"dry_run": 1}'
    # Áp thật (mặc định):
    bench --site <site> execute assetcore.setup.backfill_repair_checklists.run
"""
from __future__ import annotations

import frappe

from assetcore.services.imm09 import backfill_repair_checklists


def run(dry_run: int = 0) -> dict:
    """User-invoke entrypoint (pattern `backfill_workflow_admin.run`) — KHÔNG migrate.

    Args:
        dry_run: 0 (mặc định) = áp thật + commit; 1 = chỉ đếm (preview an toàn).

    Returns:
        {"scanned", "backfilled", "skipped_has_rows"}.
    """
    result = backfill_repair_checklists(dry_run=int(dry_run))
    frappe.logger("assetcore").info({
        "event": "backfill_repair_checklists",
        "dry_run": int(dry_run),
        **result,
    })
    return result
