# Copyright (c) 2026, AssetCore Team
# REST API cho Module IMM-06 — Bàn giao & Đào tạo.
# Tier 1 — parse HTTP input → gọi services.imm06 → _ok / _err envelope.

from __future__ import annotations

import json

import frappe

from assetcore.services import imm06 as svc
from assetcore.services.shared import ServiceError, ErrorCode
from assetcore.utils.helpers import _err, _ok


def _parse_json(raw, *, field_name: str, default=None):
    """Parse JSON string or return raw if already a list/dict."""
    if not raw:
        return default if default is not None else {}
    if not isinstance(raw, str):
        return raw
    try:
        return json.loads(raw)
    except (ValueError, TypeError) as e:
        raise ServiceError(ErrorCode.INVALID_PARAMS,
                           f"{field_name} không phải JSON hợp lệ") from e


def _handle(fn, *args, **kwargs) -> dict:
    """Execute service function and wrap result in _ok/_err envelope."""
    try:
        return _ok(fn(*args, **kwargs))
    except ServiceError as e:
        return _err(e.message, e.code)
    except frappe.ValidationError as e:
        return _err(str(e), "VALIDATION_ERROR")
    except frappe.DoesNotExistError as e:
        return _err(str(e), "NOT_FOUND")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"IMM-06 {fn.__name__}")
        return _err(str(e), "SYSTEM_ERROR")


# ─── Read Endpoints ───────────────────────────────────────────────────────────

@frappe.whitelist()
def get_handover_record(name: str) -> dict:
    """Lấy chi tiết Handover Record kèm Training Sessions và lifecycle events."""
    return _handle(svc.get_handover_record, name)


@frappe.whitelist()
def list_handover_records(
    status: str = "",
    dept: str = "",
    asset: str = "",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Danh sách Handover Records với filter và pagination."""
    return _handle(
        svc.list_handover_records,
        status or None, dept or None, asset or None,
        int(page), int(page_size),
    )


@frappe.whitelist()
def get_asset_training_history(asset_name: str) -> dict:
    """Lịch sử đào tạo theo thiết bị."""
    return _handle(svc.get_asset_training_history, asset_name)


@frappe.whitelist()
def get_dashboard_stats() -> dict:
    """KPI tổng quan IMM-06."""
    return _handle(svc.get_dashboard_stats)


# ─── Write Endpoints ──────────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def create_handover_record(
    commissioning_ref: str,
    clinical_dept: str,
    handover_date: str,
    received_by: str,
    handover_type: str = "Full",
) -> dict:
    """Tạo Handover Record từ Commissioning đã Clinical Release."""
    return _handle(
        svc.create_handover_record,
        commissioning_ref, clinical_dept, handover_date, received_by, handover_type,
    )


@frappe.whitelist(methods=["POST"])
def schedule_training(
    handover_name: str,
    training_type: str,
    trainer: str,
    training_date: str,
    duration_hours: float = 0.0,
    trainees: str | list | None = None,
) -> dict:
    """Lên lịch đào tạo cho phiếu bàn giao."""
    try:
        parsed_trainees = _parse_json(trainees, field_name="trainees", default=[])
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(
        svc.schedule_training,
        handover_name, training_type, trainer, training_date,
        float(duration_hours), parsed_trainees,
    )


@frappe.whitelist(methods=["POST"])
def complete_training(
    training_session_name: str,
    scores: str | list | None = None,
    notes: str = "",
) -> dict:
    """Ghi nhận kết quả đào tạo và điểm số học viên."""
    try:
        parsed_scores = _parse_json(scores, field_name="scores", default=[])
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.complete_training, training_session_name, parsed_scores, notes)


@frappe.whitelist(methods=["POST"])
def confirm_handover(
    name: str,
    dept_head_signoff: str,
    notes: str = "",
) -> dict:
    """Xác nhận bàn giao: set chữ ký Trưởng khoa và Submit."""
    return _handle(svc.confirm_handover, name, dept_head_signoff, notes)
