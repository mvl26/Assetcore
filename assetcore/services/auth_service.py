# Copyright (c) 2026, AssetCore Team
# Auth & User Account — Tier 2 Business Service Layer.

from __future__ import annotations

import frappe
from frappe.utils import now_datetime, validate_email_address

from assetcore.repositories.asset_repo import DepartmentRepo
from assetcore.repositories.user_profile_repo import UserProfileRepo, UserRepo
from assetcore.services.shared import (
    ApprovalStatus,
    ErrorCode,
    Roles,
    ServiceError,
    has_any_role,
    require_role,
)
from assetcore.utils.helpers import _get_role_emails, _safe_sendmail

_SELF_EDITABLE = {"full_name", "phone", "job_title", "employee_code"}

# Mỗi key ↔ 1 set role (dùng cho permissions trả về FE)
_PERM_ROLE_SETS = {
    "is_admin": (Roles.SYS_ADMIN,),
    "can_create_wo": Roles.CAN_CREATE_WO,
    "can_approve": Roles.CAN_APPROVE,
    "can_manage_docs": Roles.CAN_MANAGE_DOCS,
}


# ─── Registration ─────────────────────────────────────────────────────────────

def register_user(*, email: str, full_name: str, password: str,
                  phone: str = "", department: str = "",
                  employee_code: str = "", job_title: str = "") -> dict:
    """Self-signup: tạo User (enabled=0) + AC User Profile (Pending)."""
    if not (email and full_name and password):
        raise ServiceError(ErrorCode.VALIDATION,
                           "Thiếu thông tin bắt buộc (email / họ tên / mật khẩu)")
    try:
        validate_email_address(email, throw=True)
    except frappe.InvalidEmailAddressError as e:
        raise ServiceError(ErrorCode.VALIDATION, "Email không hợp lệ") from e

    if UserRepo.exists(email):
        raise ServiceError(ErrorCode.DUPLICATE, "Email đã tồn tại trong hệ thống")

    if department and not DepartmentRepo.exists(department):
        raise ServiceError(ErrorCode.VALIDATION, f"Khoa/phòng '{department}' không tồn tại")

    user = UserRepo.create({
        "email": email,
        "first_name": full_name,
        "enabled": 0,
        "send_welcome_email": 0,
        "user_type": "System User",
    })
    user.new_password = password
    UserRepo.save(user)

    profile = UserProfileRepo.create({
        "user": email,
        "full_name": full_name,
        "phone": phone,
        "department": department or None,
        "employee_code": employee_code,
        "job_title": job_title,
        "is_active": 0,
        "approval_status": ApprovalStatus.PENDING,
    })
    frappe.db.commit()

    _notify_admins_new_registration(email, full_name, department)

    return {
        "user": email,
        "profile": profile.name,
        "pending_approval": True,
        "message": "Đăng ký thành công — vui lòng chờ quản trị viên duyệt tài khoản.",
    }


def approve_registration(profile_name: str, *, roles: list[str] | None = None,
                          rejection_reason: str = "") -> dict:
    """Admin/Ops duyệt hoặc từ chối."""
    require_role(Roles.CAN_ADMIN_USER, "Không đủ quyền duyệt")

    if not UserProfileRepo.exists(profile_name):
        raise ServiceError(ErrorCode.NOT_FOUND, "Không tìm thấy hồ sơ")

    patch: dict = {}
    if rejection_reason:
        patch["approval_status"] = ApprovalStatus.REJECTED
        patch["rejection_reason"] = rejection_reason
    else:
        patch["approval_status"] = ApprovalStatus.APPROVED
        patch["is_active"] = 1

    doc = UserProfileRepo.update_fields(profile_name, patch)

    if not rejection_reason and roles:
        doc.set("imm_roles", [])
        for r in roles:
            doc.append("imm_roles", {"role": r})
        UserProfileRepo.save(doc)

    return {"profile": doc.name, "status": doc.approval_status}


# ─── Profile queries ──────────────────────────────────────────────────────────

def get_current_user_profile() -> dict:
    user_name = frappe.session.user
    if user_name == "Guest":
        raise ServiceError(ErrorCode.UNAUTHORIZED, "Chưa đăng nhập")

    user = UserRepo.get(user_name)
    roles = [r.role for r in user.roles if r.role.startswith("IMM ")]

    profile_data = None
    if UserProfileRepo.exists(user_name):
        prof = UserProfileRepo.get(user_name)
        profile_data = prof.as_dict()
        if prof.department:
            profile_data["department_name"] = (
                DepartmentRepo.get_value(prof.department, "department_name")
                or prof.department
            )

    return {
        "user": {
            "name": user.name, "full_name": user.full_name,
            "email": user.email, "user_image": user.user_image,
        },
        "roles": roles,
        "profile": profile_data,
        "permissions": _compute_permissions(set(roles)),
    }


def update_my_profile(patch: dict) -> dict:
    user_name = frappe.session.user
    if user_name == "Guest":
        raise ServiceError(ErrorCode.UNAUTHORIZED, "Chưa đăng nhập")
    if not UserProfileRepo.exists(user_name):
        raise ServiceError(ErrorCode.NOT_FOUND, "Không tìm thấy hồ sơ người dùng")

    clean_patch = {k: v for k, v in patch.items() if k in _SELF_EDITABLE}
    if not clean_patch:
        raise ServiceError(ErrorCode.VALIDATION, "Không có trường nào được cập nhật")

    UserProfileRepo.update_fields(user_name, clean_patch)
    return {"updated_fields": list(clean_patch.keys())}


def change_password(*, old_password: str, new_password: str) -> dict:
    user_name = frappe.session.user
    if user_name == "Guest":
        raise ServiceError(ErrorCode.UNAUTHORIZED, "Chưa đăng nhập")
    if not old_password or not new_password:
        raise ServiceError(ErrorCode.VALIDATION, "Thiếu mật khẩu cũ hoặc mới")

    from frappe.auth import check_password
    try:
        check_password(user_name, old_password)
    except frappe.AuthenticationError as e:
        raise ServiceError("BAD_OLD_PWD", "Mật khẩu cũ không đúng") from e

    user = UserRepo.get(user_name)
    user.new_password = new_password
    UserRepo.save(user)
    return {"message": "Đổi mật khẩu thành công"}


# ─── Internal ─────────────────────────────────────────────────────────────────

def _compute_permissions(role_set: set[str]) -> dict[str, bool]:
    return {key: bool(role_set.intersection(roles))
            for key, roles in _PERM_ROLE_SETS.items()}


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
            f"<p>Vui lòng vào AC User Profile để duyệt.</p>"
        ),
    )
