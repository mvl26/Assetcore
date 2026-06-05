"""Backfill ``AC Asset.qr_token`` cho MỌI tài sản cũ/import/legacy (ADR-001 D5).

A1 — QR cấp tài sản. Sinh ``qr_token`` enumeration-safe (secrets.token_urlsafe)
cho mọi AC Asset đang trống token (kể cả asset không đi qua commissioning:
import, legacy, tạo trực tiếp trước khi field tồn tại).

Tính chất:
  - Idempotent: chỉ chạm asset ``qr_token IN ('', NULL)`` → chạy lại = no-op.
  - Collision-safe: DELEGATE SSoT ``generate_unique_qr_token`` (pre-write check qua
    ``frappe.db.exists`` — §II.1.8-COLL / BR-00-31). KHÔNG còn vòng write-then-catch
    Duplicate tự chế (dedup về 1 nguồn collision-safety, KHÔNG 2 bản logic song song).
  - Lifecycle/audit: emit ``qr_generated`` best-effort/asset (lỗi KHÔNG vỡ patch).

Đăng ký sau 007 trong patches.txt.
"""
from __future__ import annotations

import frappe

from assetcore.services.imm00 import generate_unique_qr_token, emit_qr_generated

_DOCTYPE = "AC Asset"


def _set_token_collision_safe(name: str) -> str | None:
    """Set qr_token cho 1 asset qua SSoT collision-safe. Trả token hoặc None.

    Delegate ``generate_unique_qr_token`` (pre-write uniqueness check) → token đã
    unique TRƯỚC khi ghi ⇒ ``set_value`` KHÔNG đụng UNIQUE. Cạn-retry trong helper
    → raise (frappe.ValidationError) → log_error + bỏ qua asset đó (GIỮ behavior
    idempotent best-effort: patch không vỡ vì 1 asset cá biệt).
    """
    try:
        token = generate_unique_qr_token()
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            f"Backfill qr_token bỏ qua {name}: cạn retry sinh token unique",
        )
        return None
    frappe.db.set_value(_DOCTYPE, name, "qr_token", token, update_modified=False)
    frappe.db.commit()
    return token


def execute() -> None:
    if not frappe.db.has_column(_DOCTYPE, "qr_token"):
        # Field chưa sync (migrate chạy patch trước sync schema bất thường) → bỏ qua.
        return

    names = frappe.get_all(
        _DOCTYPE,
        filters={"qr_token": ["in", ["", None]]},
        pluck="name",
    )
    if not names:
        print("[patches.v3_2.008_backfill_asset_qr_token] no-op (0 asset trống)")
        return

    backfilled = 0
    for name in names:
        token = _set_token_collision_safe(name)
        if not token:
            continue
        backfilled += 1
        # Best-effort lifecycle + audit (lỗi KHÔNG vỡ patch).
        try:
            emit_qr_generated(name, token, actor="Administrator")
        except Exception:
            frappe.log_error(frappe.get_traceback(),
                             "v3_2.008 backfill emit_qr_generated failed")

    frappe.db.commit()
    print(
        f"[patches.v3_2.008_backfill_asset_qr_token] "
        f"candidates={len(names)} backfilled={backfilled}"
    )
