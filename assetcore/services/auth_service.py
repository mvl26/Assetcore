# Copyright (c) 2026, AssetCore Team
# Auth & User Account — Tier 2 Business Service Layer.
# Data model: Frappe User + ERPNext Employee (optional) + custom fields on User.

from __future__ import annotations

import frappe
from frappe.utils import validate_email_address

from assetcore.repositories.user_profile_repo import UserRepo
from assetcore.services.shared import (
    ApprovalStatus,
    ErrorCode,
    Roles,
    ServiceError,
    require_role,
)
from assetcore.utils.helpers import _get_role_emails, _safe_sendmail

_SELF_EDITABLE = {"full_name", "phone"}
_MSG_NOT_LOGGED_IN = "Chưa đăng nhập"

_PERM_ROLE_SETS: dict[str, tuple] = {
    "is_admin": (Roles.SYS_ADMIN,),
    "can_create_wo": Roles.CAN_CREATE_WO,
    "can_approve": Roles.CAN_APPROVE,
    "can_manage_docs": Roles.CAN_MANAGE_DOCS,
}


# ─── Registration ──────────────────────────────────────────────────────────────

def register_user(*, email: str, full_name: str, password: str,
                  phone: str = "", department: str = "") -> dict:
    """Self-signup: tạo User (enabled=0) + set imm_approval_status=Pending."""
    if not (email and full_name and password):
        raise ServiceError(ErrorCode.VALIDATION,
                           "Thiếu thông tin bắt buộc (email / họ tên / mật khẩu)")
    try:
        validate_email_address(email, throw=True)
    except frappe.InvalidEmailAddressError as e:
        raise ServiceError(ErrorCode.VALIDATION, "Email không hợp lệ") from e

    if UserRepo.exists(email):
        raise ServiceError(ErrorCode.DUPLICATE, "Email đã tồn tại trong hệ thống")

    if department and not frappe.db.exists("AC Department", department):
        raise ServiceError(ErrorCode.VALIDATION, f"Khoa/phòng '{department}' không tồn tại")

    user = UserRepo.create({
        "email": email,
        "first_name": full_name,
        "phone": phone,
        "enabled": 0,
        "send_welcome_email": 0,
        "user_type": "System User",
    })
    user.new_password = password
    UserRepo.save(user)

    updates: dict = {}
    if frappe.db.has_column("User", "imm_approval_status"):
        updates["imm_approval_status"] = ApprovalStatus.PENDING
    if department and frappe.db.has_column("User", "ac_department"):
        updates["ac_department"] = department
    if updates:
        frappe.db.set_value("User", email, updates)

    frappe.db.commit()
    _notify_admins_new_registration(email, full_name, department)

    return {
        "user": email,
        "pending_approval": True,
        "message": "Đăng ký thành công — vui lòng chờ quản trị viên duyệt tài khoản.",
    }


def approve_registration(user_name: str, *, roles: list[str] | None = None,
                          rejection_reason: str = "") -> dict:
    """Admin/Ops duyệt hoặc từ chối — cập nhật custom fields trên Frappe User."""
    require_role(Roles.CAN_ADMIN_USER, "Không đủ quyền duyệt")

    if not UserRepo.exists(user_name):
        raise ServiceError(ErrorCode.NOT_FOUND, "Không tìm thấy người dùng")

    user = UserRepo.get(user_name)

    if rejection_reason:
        updates = {"imm_approval_status": ApprovalStatus.REJECTED}
        if frappe.db.has_column("User", "imm_rejection_reason"):
            updates["imm_rejection_reason"] = rejection_reason
        frappe.db.set_value("User", user_name, updates)
    else:
        frappe.db.set_value("User", user_name, {
            "imm_approval_status": ApprovalStatus.APPROVED,
            "enabled": 1,
        })
        if roles:
            for r in roles:
                user.append("roles", {"role": r})
            user.flags.ignore_permissions = True
            user.save()

    frappe.db.commit()
    approval_status = frappe.db.get_value("User", user_name, "imm_approval_status")
    return {"user": user_name, "status": approval_status}


# ─── Profile queries ───────────────────────────────────────────────────────────

def get_current_user_profile() -> dict:
    user_name = frappe.session.user
    if user_name == "Guest":
        raise ServiceError(ErrorCode.UNAUTHORIZED, _MSG_NOT_LOGGED_IN)

    user = UserRepo.get(user_name)
    imm_roles = [r.role for r in user.roles if r.role.startswith("IMM ")]

    dept_id = (frappe.db.get_value("User", user_name, "ac_department")
               if frappe.db.has_column("User", "ac_department") else None)
    dept_name = (frappe.db.get_value("AC Department", dept_id, "department_name") or dept_id
                 if dept_id else None)
    approval_status = (frappe.db.get_value("User", user_name, "imm_approval_status")
                       if frappe.db.has_column("User", "imm_approval_status") else "Approved")
    emp = _get_employee_extra(user_name)

    return {
        "user": {
            "name": user.name, "full_name": user.full_name,
            "email": user.email, "user_image": user.user_image,
        },
        "roles": imm_roles,
        "profile": {
            "user": user_name,
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "ac_department": dept_id,
            "department_name": dept_name,
            "imm_approval_status": approval_status,
            "designation": emp.get("designation"),
            "hr_docname": emp.get("hr_docname"),
        },
        "permissions": _compute_permissions(set(imm_roles)),
    }


def update_my_profile(patch: dict) -> dict:
    user_name = frappe.session.user
    if user_name == "Guest":
        raise ServiceError(ErrorCode.UNAUTHORIZED, _MSG_NOT_LOGGED_IN)

    clean_patch = {k: v for k, v in patch.items() if k in _SELF_EDITABLE}
    if not clean_patch:
        raise ServiceError(ErrorCode.VALIDATION, "Không có trường nào được cập nhật")

    user = UserRepo.get(user_name)
    for k, v in clean_patch.items():
        user.set(k, v)
    user.flags.ignore_permissions = True
    UserRepo.save(user)
    frappe.db.commit()
    return {"updated_fields": list(clean_patch.keys())}


def change_password(*, old_password: str, new_password: str) -> dict:
    user_name = frappe.session.user
    if user_name == "Guest":
        raise ServiceError(ErrorCode.UNAUTHORIZED, _MSG_NOT_LOGGED_IN)
    if not old_password or not new_password:
        raise ServiceError(ErrorCode.VALIDATION, "Thiếu mật khẩu cũ hoặc mới")

    from frappe.utils.password import check_password, update_password
    try:
        check_password(user_name, old_password)
    except frappe.AuthenticationError as e:
        raise ServiceError("BAD_OLD_PWD", "Mật khẩu cũ không đúng") from e

    update_password(user_name, new_password)
    frappe.db.commit()
    return {"message": "Đổi mật khẩu thành công"}


# ─── Internal ──────────────────────────────────────────────────────────────────

def _compute_permissions(role_set: set[str]) -> dict[str, bool]:
    return {key: bool(role_set.intersection(roles))
            for key, roles in _PERM_ROLE_SETS.items()}


def _get_employee_extra(user_name: str) -> dict:
    if not frappe.db.table_exists("Employee"):
        return {}
    try:
        emp = frappe.db.get_value(
            "Employee", {"user_id": user_name},
            ["name", "designation"],
            as_dict=True,
        )
    except Exception:
        return {}
    return {"hr_docname": emp.get("name"), "designation": emp.get("designation")} if emp else {}


def _notify_admins_new_registration(email: str, full_name: str, department: str) -> None:
    recipients = _get_role_emails([Roles.SYS_ADMIN])
    if not recipients:
        return
    _safe_sendmail(
        recipients=recipients,
        subject=f"[AssetCore] Đăng ký mới — {full_name}",
        message=(
            f"<p>Người dùng mới vừa đăng ký tài khoản:</p>"
            f"<ul>"
            f"<li><b>Email:</b> {email}</li>"
            f"<li><b>Họ tên:</b> {full_name}</li>"
            f"<li><b>Khoa/Phòng:</b> {department or '(chưa chọn)'}</li>"
            f"</ul>"
            f"<p>Vào <b>Quản lý Người dùng IMM</b> để duyệt tài khoản.</p>"
        ),
    )
