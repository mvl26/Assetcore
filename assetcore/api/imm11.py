# Copyright (c) 2026, AssetCore Team
# REST API cho Module IMM-11 — Calibration.
#
# Tier 1 — Presentation only.
# Parse HTTP input → gọi service → format _ok / _err envelope.
# KHÔNG gọi frappe.db.* hay frappe.get_doc trực tiếp.

from __future__ import annotations

import datetime

import frappe

from assetcore.services import imm11 as svc
from assetcore.services.shared import ServiceError
from assetcore.services.shared import rbac
from assetcore.services.shared.scope import apply_vendor_scope, assert_vendor_can_access
from assetcore.utils.api_handler import handle, parse_json
from assetcore.utils.response import _err


# ─── 1. Calibration Schedules ────────────────────────────────────────────────

@frappe.whitelist()
def list_calibration_schedules(filters: str = "{}", page: int = 1, page_size: int = 20) -> dict:
    try:
        f = parse_json(filters, default={}, field_name="filters")
    except ServiceError as e:
        return _err(e.message, e.code, http_status=e.http_status)
    f = apply_vendor_scope(f, "Calibration Schedule")
    return handle(svc.list_schedules, f, page=int(page), page_size=int(page_size))


@frappe.whitelist()
def get_calibration_schedule(name: str) -> dict:
    try:
        assert_vendor_can_access("Calibration Schedule", name)
    except ServiceError as e:
        return _err(e.message, e.code, http_status=e.http_status)
    return handle(svc.get_schedule, name)


@frappe.whitelist()
def create_calibration_schedule(asset: str, calibration_type: str, interval_days: int,
                                 preferred_lab: str = None, next_due_date: str = None) -> dict:
    # AUTH-02 — server-side gate; FE button hiding is not a security control.
    rbac.require("calibration.create")
    return handle(
        svc.create_schedule,
        asset=asset, calibration_type=calibration_type,
        interval_days=int(interval_days),
        preferred_lab=preferred_lab, next_due_date=next_due_date,
    )


@frappe.whitelist()
def update_calibration_schedule(name: str, **kwargs) -> dict:
    rbac.require("calibration.write")
    return handle(svc.update_schedule, name, kwargs)


@frappe.whitelist()
def delete_calibration_schedule(name: str) -> dict:
    rbac.require("calibration.delete")
    return handle(svc.delete_schedule, name)


# ─── 2. Calibration Work Orders ───────────────────────────────────────────────

@frappe.whitelist()
def list_calibrations(filters: str = "{}", mine: int = 0,
                      page: int = 1, page_size: int = 20) -> dict:
    # C-LISTREAD-MINE-CAL (quartet "phiếu-của-tôi" ĐÓNG NỐT sau PM/CM/Incident): tab "Phiếu hiệu
    #   chuẩn của tôi" (MVP-5d) truyền mine=1 → scope technician == session.user (calibration
    #   assignee — KHÔNG assigned_to; mirror IncidentMine dùng reported_by, mỗi domain field RIÊNG).
    #   Inject SAU apply_vendor_scope (vendor-scope vẫn áp trước). mine=0/absent ⇒ filters
    #   byte-identical baseline (web-FE list_calibrations KHÔNG đổi). count==rows giữ: count_with_or
    #   + get_all dùng CÙNG filters dict (đã có technician). Mirror imm08.py:28 / imm09.py:22.
    try:
        f = parse_json(filters, default={}, field_name="filters")
    except ServiceError as e:
        return _err(e.message, e.code, http_status=e.http_status)
    f = apply_vendor_scope(f, "Calibration Record")
    if int(mine or 0):
        f["technician"] = frappe.session.user
    return handle(svc.list_calibrations, f, page=int(page), page_size=int(page_size))


@frappe.whitelist()
def get_calibration(name: str) -> dict:
    try:
        assert_vendor_can_access("Calibration Record", name)
    except ServiceError as e:
        return _err(e.message, e.code, http_status=e.http_status)
    return handle(svc.get_calibration, name)


@frappe.whitelist(methods=["POST"])
def create_calibration(asset: str, calibration_type: str, scheduled_date: str,
                        technician: str, calibration_schedule: str = None,
                        lab_supplier: str = None, is_recalibration: int = 0,
                        reference_standard_serial: str = None,
                        traceability_reference: str = None) -> dict:
    rbac.require("calibration.create")
    return handle(
        svc.create_calibration,
        asset=asset, calibration_type=calibration_type,
        scheduled_date=scheduled_date, technician=technician,
        calibration_schedule=calibration_schedule,
        lab_supplier=lab_supplier,
        is_recalibration=int(is_recalibration),
        reference_standard_serial=reference_standard_serial,
        traceability_reference=traceability_reference,
    )


@frappe.whitelist()
def update_calibration(name: str, **kwargs) -> dict:
    rbac.require("calibration.write")
    # CR-24-WEB: `measurements` (child-diff nhập-đo web) đến dạng list (JSON body) HOẶC
    # JSON-string (form-encoded — mobile_be form_dict oneOf json+form). parse_json idempotent
    # cho list ⇒ chuẩn hoá về list-of-dict trước khi xuống service. parse_json malformed →
    # ServiceError(INVALID_PARAMS) envelope (KHÔNG traceback 500).
    if "measurements" in kwargs:
        kwargs["measurements"] = parse_json(
            kwargs["measurements"], default=[], field_name="measurements")
    return handle(svc.update_calibration, name, kwargs)


@frappe.whitelist(methods=["POST"])
def submit_calibration(name: str, client_request_id: str = "") -> dict:
    # CR-24-CAL-SUBMIT (op#6): client_request_id optional (mobile write-outbox idempotency;
    # body THẮNG header). Default str="" (KHÔNG None → tránh 417). rbac.require GIỮ.
    rbac.require("calibration.submit")
    return handle(svc.submit_calibration, name,
                  client_request_id=str(client_request_id or ""))


@frappe.whitelist(methods=["POST"])
def add_measurement(name: str, parameter_name: str, unit: str, nominal_value: float,
                     tolerance_positive: float, tolerance_negative: float,
                     measured_value: float = None, client_request_id: str = "") -> dict:
    rbac.require("calibration.write")
    return handle(
        svc.add_measurement, name,
        parameter_name=parameter_name, unit=unit,
        nominal_value=float(nominal_value),
        tolerance_positive=float(tolerance_positive),
        tolerance_negative=float(tolerance_negative),
        measured_value=float(measured_value) if measured_value is not None else None,
        client_request_id=str(client_request_id or ""),
    )


# ─── 3. KPIs ─────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_calibration_kpis(year: int = None, month: int = None) -> dict:
    now = datetime.date.today()
    return handle(
        svc.get_kpis,
        int(year) if year else now.year,
        int(month) if month else now.month,
    )


@frappe.whitelist()
def get_calibration_dashboard() -> dict:
    return handle(svc.get_dashboard)


@frappe.whitelist()
def get_asset_calibration_history(asset: str, limit: int = 10) -> dict:
    return handle(svc.get_asset_history, asset, int(limit))


# ─── 4. Workflow actions ─────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def send_to_lab(name: str, sent_date: str = None, lab_supplier: str = None,
                lab_contract_ref: str = None) -> dict:
    rbac.require("cal.send_lab")
    return handle(
        svc.send_to_lab, name,
        sent_date=sent_date, lab_supplier=lab_supplier,
        lab_contract_ref=lab_contract_ref,
    )


@frappe.whitelist(methods=["POST"])
def receive_certificate(name: str, certificate_file: str,
                        certificate_number: str, certificate_date: str,
                        traceability_reference: str = None,
                        reference_standard_serial: str = None) -> dict:
    rbac.require("calibration.write")
    return handle(
        svc.receive_certificate, name,
        certificate_file=certificate_file,
        certificate_number=certificate_number,
        certificate_date=certificate_date,
        traceability_reference=traceability_reference,
        reference_standard_serial=reference_standard_serial,
    )


@frappe.whitelist(methods=["POST"])
def cancel_calibration(name: str, reason: str) -> dict:
    rbac.require("calibration.cancel")
    return handle(svc.cancel_calibration, name, reason)


@frappe.whitelist()
def get_due_calibrations(days: int = 30, limit: int = 50) -> dict:
    return handle(svc.get_due_calibrations, int(days), int(limit))
