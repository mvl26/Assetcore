# Copyright (c) 2026, AssetCore Team
"""
Auth API — đăng ký tự phục vụ, đổi mật khẩu, profile cá nhân.

Không còn phụ thuộc vào AC User Profile.
Data model: Frappe User + ERPNext Employee (optional).
"""
from __future__ import annotations

import frappe
from frappe.rate_limiter import rate_limit
from frappe.utils import validate_email_address

from assetcore.utils.response import _ok, _err
from assetcore.utils.helpers import _get_role_emails, _safe_sendmail

_ROLE_ADMIN = "IMM System Admin"
_ROLE_QA = "IMM QA Officer"
_ROLE_DEPT_HEAD = "IMM Department Head"
_ROLE_OPS = "IMM Operations Manager"
_ROLE_WORKSHOP = "IMM Workshop Lead"
_ROLE_TECH = "IMM Technician"
_ROLE_DOC = "IMM Document Officer"
_MSG_NOT_LOGGED_IN = "Chưa đăng nhập"
_SELF_EDITABLE = {"full_name", "phone"}


def _safe_field(fieldname: str) -> bool:
    return frappe.db.has_column("User", fieldname)


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


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=60, ip_based=True)
def register_user(email: str, full_name: str, password: str,
                  phone: str = "", department: str = "") -> dict:
    """Self-registration — tạo User (enabled=0) chờ admin duyệt."""
    email = email.strip().lower()
    if not (email and full_name and password):
        return _err("Thiếu thông tin bắt buộc (email / họ tên / mật khẩu)", 400)

    try:
        validate_email_address(email, throw=True)
    except frappe.InvalidEmailAddressError:
        return _err("Email không hợp lệ", 400)

    if frappe.db.exists("User", email):
        return _err("Email đã tồn tại trong hệ thống", 400)

    if department and not frappe.db.exists("AC Department", department):
        return _err(f"Khoa/phòng '{department}' không tồn tại", 400)

    user_doc = frappe.new_doc("User")
    user_doc.email = email
    user_doc.first_name = full_name
    user_doc.phone = phone
    user_doc.user_type = "System User"
    user_doc.enabled = 0
    user_doc.send_welcome_email = 0
    user_doc.new_password = password
    user_doc.flags.ignore_permissions = True
    user_doc.insert()

    updates: dict = {}
    if _safe_field("imm_approval_status"):
        updates["imm_approval_status"] = "Pending"
    if department and _safe_field("ac_department"):
        updates["ac_department"] = department
    if updates:
        frappe.db.set_value("User", email, updates)

    frappe.db.commit()
    _notify_admins_registration(email, full_name, department)

    return _ok({
        "user": email,
        "pending_approval": True,
        "message": "Đăng ký thành công — vui lòng chờ quản trị viên duyệt tài khoản.",
    })


@frappe.whitelist()
def get_user_profile() -> dict:
    user_name = frappe.session.user
    if user_name == "Guest":
        return _err(_MSG_NOT_LOGGED_IN, 401)

    user_doc = frappe.get_doc("User", user_name)
    imm_roles = [r.role for r in user_doc.roles if r.role.startswith("IMM ")]
    emp = _get_employee_extra(user_name)

    dept_id = frappe.db.get_value("User", user_name, "ac_department") if _safe_field("ac_department") else None
    dept_name = (frappe.db.get_value("AC Department", dept_id, "department_name") or dept_id) if dept_id else None

    approval_status = (
        frappe.db.get_value("User", user_name, "imm_approval_status")
        if _safe_field("imm_approval_status") else "Approved"
    )

    profile = {
        "user": user_name,
        "full_name": user_doc.full_name,
        "email": user_doc.email,
        "phone": user_doc.phone,
        "user_image": user_doc.user_image,
        "ac_department": dept_id,
        "department_name": dept_name,
        "imm_approval_status": approval_status,
        "designation": emp.get("designation"),
        "hr_docname": emp.get("hr_docname"),
    }

    return _ok({
        "user": {"name": user_name, "full_name": user_doc.full_name,
                 "email": user_doc.email, "user_image": user_doc.user_image},
        "roles": imm_roles,
        "profile": profile,
        "permissions": _compute_permissions(set(imm_roles)),
    })


@frappe.whitelist(methods=["POST"])
def update_my_profile(**kwargs) -> dict:
    user_name = frappe.session.user
    if user_name == "Guest":
        return _err(_MSG_NOT_LOGGED_IN, 401)

    data = frappe.local.form_dict
    clean = {k: v for k, v in data.items() if k in _SELF_EDITABLE}
    if not clean:
        return _err("Không có trường nào được cập nhật", 400)

    user_doc = frappe.get_doc("User", user_name)
    for k, v in clean.items():
        user_doc.set(k, v)
    user_doc.flags.ignore_permissions = True
    user_doc.save()
    frappe.db.commit()
    return _ok({"updated_fields": list(clean.keys())})


@frappe.whitelist(methods=["POST"])
def change_password(old_password: str, new_password: str) -> dict:
    user_name = frappe.session.user
    if user_name == "Guest":
        return _err(_MSG_NOT_LOGGED_IN, 401)
    if not old_password or not new_password:
        return _err("Thiếu mật khẩu cũ hoặc mới", 400)
    if len(new_password) < 8:
        return _err("Mật khẩu mới phải tối thiểu 8 ký tự", 400)

    from frappe.utils.password import check_password, update_password
    try:
        check_password(user_name, old_password)
    except frappe.AuthenticationError:
        return _err("Mật khẩu cũ không đúng", 400)

    update_password(user_name, new_password)
    frappe.db.commit()
    return _ok({"message": "Đổi mật khẩu thành công"})


# ── Internal ───────────────────────────────────────────────────────────────────

_PERM_ROLE_SETS: dict[str, tuple] = {
    "is_admin": (_ROLE_ADMIN,),
    "can_create_wo": (_ROLE_ADMIN, _ROLE_OPS, _ROLE_WORKSHOP, _ROLE_TECH, _ROLE_QA),
    "can_approve": (_ROLE_ADMIN, _ROLE_QA, _ROLE_DEPT_HEAD, _ROLE_OPS),
    "can_manage_docs": (_ROLE_ADMIN, _ROLE_DOC, _ROLE_QA),
}


def _compute_permissions(role_set: set[str]) -> dict[str, bool]:
    return {k: bool(role_set.intersection(roles)) for k, roles in _PERM_ROLE_SETS.items()}


def _notify_admins_registration(email: str, full_name: str, department: str) -> None:
    recipients = _get_role_emails([_ROLE_ADMIN])
    if not recipients:
        return
    _safe_sendmail(
        recipients=recipients,
        subject=f"[AssetCore] Đăng ký mới — {full_name}",
        message=(
            f"<p>Người dùng mới vừa đăng ký:</p>"
            f"<ul><li><b>Email:</b> {email}</li>"
            f"<li><b>Họ tên:</b> {full_name}</li>"
            f"<li><b>Khoa/Phòng:</b> {department or '(chưa chọn)'}</li></ul>"
            f"<p>Vào <b>Quản lý Người dùng IMM</b> để duyệt tài khoản.</p>"
        ),
    )
