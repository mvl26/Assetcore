# Copyright (c) 2026, AssetCore Team
"""
Auth API — đăng ký tự phục vụ, đổi mật khẩu, profile cá nhân.

Data model: Frappe User + Employee (optional, nếu có Frappe HR).
"""
from __future__ import annotations

import frappe
from frappe.rate_limiter import rate_limit
from frappe.utils import validate_email_address

from assetcore.utils.response import _ok, _err
from assetcore.utils.helpers import _get_role_emails, _safe_sendmail
from assetcore.services.shared import rbac

# Email-by-role lookup (data, KHONG phai gate) — remap persona -> role moi.
_ROLE_ADMIN = "AssetCore Super Admin"
_ROLE_QA = "Compliance Manager"
_ROLE_OPS = "Commissioning Manager"
_ROLE_WORKSHOP = "PM Manager"
_ROLE_DOC = "Document Manager"
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

    if department and not frappe.db.exists("AC Department", department):
        return _err(f"Khoa/phòng '{department}' không tồn tại", 400)

    if frappe.db.exists("User", email):
        # G4: user đã bị TỪ CHỐI (Rejected + enabled=0) được phép đăng ký lại —
        # reset record về Pending thay vì tạo bản trùng. Pending/Approved vẫn chặn.
        return _reapply_if_rejected(email, full_name, password, phone, department)

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


def _reapply_if_rejected(email: str, full_name: str, password: str,
                         phone: str, department: str) -> dict:
    """G4: cho phép user Rejected đăng ký lại — reset về Pending.

    Chỉ áp dụng khi record hiện tại là Rejected (và enabled=0 — invariant đã
    khoá: Rejected ⟹ chưa active). Mọi trạng thái khác (Pending đang chờ,
    Approved/enabled=1) → giữ nguyên hành vi 'đã tồn tại' để chống chiếm tài
    khoản đang hoạt động.
    """
    status = (
        frappe.db.get_value("User", email, "imm_approval_status")
        if _safe_field("imm_approval_status") else None
    )
    enabled = int(frappe.db.get_value("User", email, "enabled") or 0)

    if status != "Rejected" or enabled == 1:
        return _err("Email đã tồn tại trong hệ thống", 400)

    # Reset hồ sơ: cập nhật danh tính + mật khẩu mới, đưa về Pending, clear lý do từ chối.
    user_doc = frappe.get_doc("User", email)
    user_doc.first_name = full_name
    user_doc.phone = phone or ""
    user_doc.enabled = 0
    user_doc.new_password = password
    if _safe_field("imm_approval_status"):
        user_doc.imm_approval_status = "Pending"
    if _safe_field("imm_rejection_reason"):
        user_doc.imm_rejection_reason = ""
    if department and _safe_field("ac_department"):
        user_doc.ac_department = department
    user_doc.flags.ignore_permissions = True
    user_doc.save()
    frappe.db.commit()

    _notify_admins_registration(email, full_name, department)
    return _ok({
        "user": email,
        "pending_approval": True,
        "reapplied": True,
        "message": "Đăng ký lại thành công — vui lòng chờ quản trị viên duyệt tài khoản.",
    })


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="email", limit=5, seconds=60, ip_based=True)
def check_account_status(email: str) -> dict:
    """BR-00-USR-02 (security 2026-06-01): probe trạng thái cho FE — NON-ENUMERABLE.

    Thiết kế cũ (G5) phân biệt not_found/active/pending/rejected/disabled cho
    BẤT KỲ email nào mà không cần mật khẩu → kẻ tấn công liệt kê được email đã
    đăng ký + trạng thái tài khoản (user enumeration / information disclosure).

    Thiết kế mới: endpoint guest này KHÔNG bao giờ phân biệt tồn tại hay trạng
    thái — LUÔN trả nhãn đồng nhất `unknown`. Trạng thái nhạy cảm
    (pending/rejected/disabled) chỉ được surface qua `account_state(usr, pwd)`
    SAU KHI mật khẩu đúng.

    Bảo mật:
      - allow_guest nhưng response độc lập với email → không leak gì.
      - Rate-limit kép: per-(IP, email) (key='email', 5/60s) chống dò hàng loạt.

    Giữ endpoint (thay vì xoá) để FE/clients cũ không gãy; vì nó không còn lộ
    thông tin, không còn là vector enumeration.
    """
    email = (email or "").strip().lower()
    if not email:
        return _err("Thiếu email", 400)
    # Cố ý KHÔNG truy vấn DB theo tồn tại → response đồng nhất, không enumeration,
    # không lệch timing giữa email tồn tại và không tồn tại.
    return _ok({"status": "unknown"})


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="usr", limit=5, seconds=60, ip_based=True)
def account_state(usr: str, pwd: str) -> dict:
    """BR-00-USR-02: tra trạng thái tài khoản — PASSWORD-GATED.

    Chỉ lộ pending/rejected/disabled/active SAU KHI người gọi chứng minh biết
    mật khẩu. Dùng cho FE login UX: khi `/api/method/login` fail, FE gọi endpoint
    này với CHÍNH mật khẩu user vừa nhập để biết có nên báo "chờ duyệt / bị từ
    chối / vô hiệu hoá" hay "sai thông tin".

    Bằng chứng cần endpoint riêng (frappe/auth.py LoginManager.authenticate):
      - Frappe xác thực mật khẩu TRƯỚC; user enabled=0 (mọi Pending/Rejected/
        Disabled) bị `fail("User disabled or missing")` nhưng KHÔNG tạo session
        và message này không phải contract ổn định để FE đọc. Endpoint này tái
        xác thực mật khẩu qua check_password rồi trả nhãn ổn định.

    Bảo mật:
      - Sai mật khẩu HOẶC email không tồn tại → CÙNG nhãn `invalid_credentials`
        (không phân biệt được email tồn tại hay không → đóng enumeration).
      - Chỉ khi mật khẩu ĐÚNG mới trả pending/rejected/disabled/active.
      - allow_guest nhưng KHÔNG trả role/profile/dữ liệu nghiệp vụ — 1 nhãn.
      - Rate-limit kép per-(IP, usr) (key='usr', 5/60s).
    """
    from frappe.utils.password import check_password

    usr = (usr or "").strip().lower()
    if not usr or not pwd:
        return _err("Thiếu thông tin đăng nhập", 400)

    # Email không tồn tại và sai mật khẩu PHẢI không phân biệt được.
    if not frappe.db.exists("User", usr):
        return _ok({"status": "invalid_credentials"})

    try:
        check_password(usr, pwd)
    except frappe.AuthenticationError:
        return _ok({"status": "invalid_credentials"})

    # Mật khẩu ĐÚNG — giờ mới an toàn để tiết lộ trạng thái tài khoản.
    enabled = int(frappe.db.get_value("User", usr, "enabled") or 0)
    approval = (
        frappe.db.get_value("User", usr, "imm_approval_status")
        if _safe_field("imm_approval_status") else None
    )

    if approval == "Pending":
        status = "pending"
    elif approval == "Rejected":
        status = "rejected"
    elif enabled == 0:
        status = "disabled"
    else:
        status = "active"
    return _ok({"status": status})


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


@frappe.whitelist()
def get_capabilities() -> dict:
    """Trả map capability đã resolve cho user hiện tại — FE cache 1 lần sau
    login. KHÔNG cấp dữ liệu nghiệp vụ — chỉ map { 'pm.read': true, ... }.
    """
    if frappe.session.user == "Guest":
        return _err(_MSG_NOT_LOGGED_IN, "UNAUTHORIZED")
    return _ok(rbac.get_capabilities())


# ── Internal ───────────────────────────────────────────────────────────────────

# Legacy FE permission dict — resolve qua capability (rbac), KHONG so ten role.
_PERM_CAP_MAP: dict[str, str] = {
    "is_admin": "data.admin",
    "can_create_wo": "pm.create",
    "can_approve": "pm.submit",
    "can_manage_docs": "document" + ".write",
}


def _compute_permissions(role_set: set[str] | None = None) -> dict[str, bool]:
    return {k: rbac.can(cap) for k, cap in _PERM_CAP_MAP.items()}


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
