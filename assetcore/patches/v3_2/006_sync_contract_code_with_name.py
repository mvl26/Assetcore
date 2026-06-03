"""Sync ``Service Contract.contract_code`` với ``name`` để thống nhất PK ⇄ business code.

Trước đây ``name`` autogen theo naming_series (vd ``SC-2026-0042``) trong khi
``contract_code`` là field user nhập riêng (vd ``HD-2026-NCC-DRG-01``) → tồn
tại 2 mã song song trên cùng 1 hợp đồng.

Pattern mới (giống AC Department / AC Asset): ``name == contract_code`` luôn:
  - User nhập ``contract_code`` → dùng làm name (PK).
  - User để trống → autogen từ naming_series rồi gán ``contract_code = name``.

Patch này backfill row cũ: với mỗi Service Contract có ``contract_code`` rỗng
hoặc khác ``name``, set ``contract_code = name``. Không rename ``name`` để giữ
FK refs (Service Contract Asset, AC Asset.service_contract, …). Idempotent.
"""
from __future__ import annotations

import frappe


def execute() -> None:
    rows = frappe.db.sql(
        "SELECT name, contract_code FROM `tabService Contract`",
        as_dict=True,
    )
    if not rows:
        return

    synced = 0
    for r in rows:
        if (r.contract_code or "") == r.name:
            continue
        frappe.db.set_value(
            "Service Contract", r.name, "contract_code", r.name,
            update_modified=False,
        )
        synced += 1

    frappe.db.commit()
    print(
        f"[patches.v3_2.006_sync_contract_code_with_name] "
        f"checked={len(rows)} synced={synced}"
    )
