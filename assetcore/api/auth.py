# Copyright (c) 2026, AssetCore Team
# API xác thực & quản lý tài khoản — Tier 1.
# Parse HTTP input → gọi services.auth_service → format _ok / _err envelope.

from __future__ import annotations

import frappe
from frappe.rate_limiter import rate_limit

from assetcore.services import auth_service as svc
from assetcore.services.shared import ServiceError
from assetcore.utils.helpers import _err, _ok


def _handle(fn, *args, **kwargs) -> dict:
    try:
        return _ok(fn(*args, **kwargs))
    except ServiceError as e:
        return _err(e.message, e.code)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=60, ip_based=True)
def register_user(email: str, full_name: str, password: str,
                  phone: str = "", department: str = "",
                  employee_code: str = "", job_title: str = "") -> dict:
    return _handle(
        svc.register_user,
        email=email, full_name=full_name, password=password,
        phone=phone, department=department,
        employee_code=employee_code, job_title=job_title,
    )


@frappe.whitelist()
def get_user_profile() -> dict:
    return _handle(svc.get_current_user_profile)


@frappe.whitelist(methods=["POST"])
def update_my_profile(**kwargs) -> dict:
    return _handle(svc.update_my_profile, kwargs)


@frappe.whitelist(methods=["POST"])
def change_password(old_password: str, new_password: str) -> dict:
    return _handle(svc.change_password,
                   old_password=old_password, new_password=new_password)


@frappe.whitelist(methods=["POST"])
def approve_registration(profile_name: str, roles: list = None,
                          rejection_reason: str = "") -> dict:
    return _handle(svc.approve_registration, profile_name,
                   roles=roles, rejection_reason=rejection_reason)
