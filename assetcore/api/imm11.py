# Copyright (c) 2026, AssetCore Team
# REST API cho Module IMM-11 — Calibration.
#
# Tier 1 — Presentation only.
# Parse HTTP input → gọi service → format _ok / _err envelope.
# KHÔNG gọi frappe.db.* hay frappe.get_doc trực tiếp.

from __future__ import annotations

import datetime
import json

import frappe

from assetcore.services import imm11 as svc
from assetcore.services.shared import ErrorCode, ServiceError
from assetcore.utils.helpers import _err, _ok


def _parse_filters(raw: str | dict | None) -> dict:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except (ValueError, TypeError) as e:
        raise ServiceError(ErrorCode.INVALID_PARAMS, "Tham số 'filters' không hợp lệ") from e


def _handle(fn, *args, **kwargs) -> dict:
    """Wrap service call → convert ServiceError → _err envelope."""
    try:
        return _ok(fn(*args, **kwargs))
    except ServiceError as e:
        return _err(e.message, e.code)


# ─── 1. Calibration Schedules ────────────────────────────────────────────────

@frappe.whitelist()
def list_calibration_schedules(filters: str = "{}", page: int = 1, page_size: int = 20) -> dict:
    try:
        f = _parse_filters(filters)
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.list_schedules, f, page=int(page), page_size=int(page_size))


@frappe.whitelist()
def get_calibration_schedule(name: str) -> dict:
    return _handle(svc.get_schedule, name)


@frappe.whitelist()
def create_calibration_schedule(asset: str, calibration_type: str, interval_days: int,
                                 preferred_lab: str = None, next_due_date: str = None) -> dict:
    return _handle(
        svc.create_schedule,
        asset=asset, calibration_type=calibration_type,
        interval_days=int(interval_days),
        preferred_lab=preferred_lab, next_due_date=next_due_date,
    )


@frappe.whitelist()
def update_calibration_schedule(name: str, **kwargs) -> dict:
    return _handle(svc.update_schedule, name, kwargs)


@frappe.whitelist()
def delete_calibration_schedule(name: str) -> dict:
    return _handle(svc.delete_schedule, name)


# ─── 2. Calibration Work Orders ───────────────────────────────────────────────

@frappe.whitelist()
def list_calibrations(filters: str = "{}", page: int = 1, page_size: int = 20) -> dict:
    try:
        f = _parse_filters(filters)
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.list_calibrations, f, page=int(page), page_size=int(page_size))


@frappe.whitelist()
def get_calibration(name: str) -> dict:
    return _handle(svc.get_calibration, name)


@frappe.whitelist()
def create_calibration(asset: str, calibration_type: str, scheduled_date: str,
                        technician: str, calibration_schedule: str = None,
                        lab_supplier: str = None, is_recalibration: int = 0,
                        reference_standard_serial: str = None,
                        traceability_reference: str = None) -> dict:
    return _handle(
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
    return _handle(svc.update_calibration, name, kwargs)


@frappe.whitelist()
def submit_calibration(name: str) -> dict:
    return _handle(svc.submit_calibration, name)


@frappe.whitelist()
def add_measurement(name: str, parameter_name: str, unit: str, nominal_value: float,
                     tolerance_positive: float, tolerance_negative: float,
                     measured_value: float = None) -> dict:
    return _handle(
        svc.add_measurement, name,
        parameter_name=parameter_name, unit=unit,
        nominal_value=float(nominal_value),
        tolerance_positive=float(tolerance_positive),
        tolerance_negative=float(tolerance_negative),
        measured_value=float(measured_value) if measured_value is not None else None,
    )


# ─── 3. KPIs ─────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_calibration_kpis(year: int = None, month: int = None) -> dict:
    now = datetime.date.today()
    return _handle(
        svc.get_kpis,
        int(year) if year else now.year,
        int(month) if month else now.month,
    )


@frappe.whitelist()
def get_calibration_dashboard() -> dict:
    return _handle(svc.get_dashboard)


@frappe.whitelist()
def get_asset_calibration_history(asset: str, limit: int = 10) -> dict:
    return _handle(svc.get_asset_history, asset, int(limit))


# ─── 4. Workflow actions ─────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def send_to_lab(name: str, sent_date: str = None, lab_supplier: str = None,
                lab_contract_ref: str = None) -> dict:
    return _handle(
        svc.send_to_lab, name,
        sent_date=sent_date, lab_supplier=lab_supplier,
        lab_contract_ref=lab_contract_ref,
    )


@frappe.whitelist(methods=["POST"])
def receive_certificate(name: str, certificate_file: str,
                        certificate_number: str, certificate_date: str,
                        traceability_reference: str = None,
                        reference_standard_serial: str = None) -> dict:
    return _handle(
        svc.receive_certificate, name,
        certificate_file=certificate_file,
        certificate_number=certificate_number,
        certificate_date=certificate_date,
        traceability_reference=traceability_reference,
        reference_standard_serial=reference_standard_serial,
    )


@frappe.whitelist(methods=["POST"])
def cancel_calibration(name: str, reason: str) -> dict:
    return _handle(svc.cancel_calibration, name, reason)


@frappe.whitelist()
def get_due_calibrations(days: int = 30, limit: int = 50) -> dict:
    return _handle(svc.get_due_calibrations, int(days), int(limit))
