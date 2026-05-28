"""Sync ``AC Asset.asset_code`` với ``name`` để thống nhất PK ⇄ business code.

Trước đây ``name`` autogen theo naming_series (vd ``AC-ASSET-2026-00923``)
trong khi ``asset_code`` là field user nhập riêng (vd ``TS-2024-002``) → tồn
tại 2 mã song song trên cùng 1 tài sản.

Pattern mới (giống AC Department): ``name == asset_code`` luôn luôn:
  - User nhập ``asset_code`` → dùng làm name (PK).
  - User để trống → autogen từ naming_series rồi gán ``asset_code = name``.

Patch này backfill row cũ: với mỗi AC Asset có ``asset_code`` rỗng hoặc khác
``name``, set ``asset_code = name``. Không rename ``name`` để giữ nguyên FK refs
(Audit Trail, Lifecycle Event, Work Order, …). Idempotent — safe re-run.
"""
from __future__ import annotations

import frappe


def execute() -> None:
    rows = frappe.db.sql(
        "SELECT name, asset_code FROM `tabAC Asset`",
        as_dict=True,
    )
    if not rows:
        return

    synced = 0
    for r in rows:
        if (r.asset_code or "") == r.name:
            continue
        frappe.db.set_value(
            "AC Asset", r.name, "asset_code", r.name,
            update_modified=False,
        )
        synced += 1

    frappe.db.commit()
    print(
        f"[patches.v3_2.005_sync_asset_code_with_name] "
        f"checked={len(rows)} synced={synced}"
    )
