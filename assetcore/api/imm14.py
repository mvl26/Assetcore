# Copyright (c) 2026, AssetCore Team
"""IMM-14 — Giải nhiệm thiết bị (Decommission Closure Gate) API endpoints.

3 endpoint (MVP vòng 2):
  - create_decommission  POST  → tạo hồ sơ giải nhiệm docstatus=0
  - approve_decommission POST  → duyệt → transition asset Decommissioned
  - get_decommission     GET   → đọc chi tiết (enrich)

Naming contract BE↔FE: tên function = path FE gọi
(/api/method/assetcore.api.imm14.<name>).

Logic ở service layer (CLAUDE.md §15); API chỉ gate quyền + envelope chuẩn.
ServiceError → envelope error (qua `handle`). InvalidAssetTransition (NEG-09 /
gate) → bắt riêng, map BAD_STATE, message VI từ exception (KHÔNG leak traceback).

Base URL: /api/method/assetcore.api.imm14
"""
from __future__ import annotations

import frappe

from assetcore.utils.api_handler import handle
from assetcore.utils.response import _err
from assetcore.utils.response import ErrorCode
from assetcore.services.shared import rbac
from assetcore.services import imm14 as svc

_CAP_CREATE = "decommission.create"   # → ("Asset Decommission", "create")
_CAP_APPROVE = "decommission.approve"  # → ("Asset Decommission", "submit")
_CAP_READ = "decommission.read"        # → ("Asset Decommission", "read")


@frappe.whitelist(methods=["POST"])
def create_decommission(
    asset: str,
    disposal_method: str,
    decommission_reason: str,
    patient_data_sanitized: int = 0,
    responsible: str | None = None,
    sanitization_note: str = "",
):
    """Tạo hồ sơ giải nhiệm (Asset Decommission) docstatus=0. KHÔNG đổi asset status."""
    rbac.require(_CAP_CREATE)
    return handle(
        svc.create_decommission,
        asset=asset,
        disposal_method=disposal_method,
        decommission_reason=decommission_reason,
        patient_data_sanitized=int(patient_data_sanitized or 0),
        responsible=responsible,
        sanitization_note=sanitization_note or "",
    )


@frappe.whitelist(methods=["POST"])
def approve_decommission(name: str):
    """Duyệt hồ sơ giải nhiệm → transition asset sang Decommissioned (NEG-09 + gate).

    InvalidAssetTransition (NEG-09 / state-machine) không phải ServiceError →
    bắt riêng, map BAD_STATE, message VI từ exception. KHÔNG để leak 'Lỗi hệ thống'.
    """
    rbac.require(_CAP_APPROVE)
    from assetcore.services.imm00 import InvalidAssetTransition
    try:
        return handle(svc.approve_decommission, name)
    except InvalidAssetTransition as e:
        frappe.db.rollback()
        return _err(
            str(e),
            ErrorCode.BAD_STATE,
            http_status=409,
        )


@frappe.whitelist()
def get_decommission(name: str):
    """Đọc chi tiết hồ sơ giải nhiệm (enrich asset_name, responsible_name, lifecycle)."""
    rbac.require(_CAP_READ)
    return handle(svc.get_decommission, name)
