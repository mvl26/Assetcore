# Copyright (c) 2026, AssetCore Team
"""
IMM-00 User Management API.

Data model:
  User  (Frappe core) — xác thực, custom fields IMM, Has Role child table
  Employee (ERPNext optional) — HR data, liên kết qua Employee.user_id = User.name

Custom fields trên tabUser (tạo bởi assetcore.setup.install.after_migrate):
  imm_approval_status | imm_approved_by | imm_approved_at
  imm_rejection_reason | ac_department

NOTE: tabEmployee dùng "name" (docname) làm định danh chính.
      Liên kết User ↔ Employee qua cột user_id của Employee.
      Frappe HR không có cột định danh phụ trong schema chuẩn.
"""
from __future__ import annotations

import json
from typing import Any

import frappe
from frappe.utils import now_datetime

from assetcore.utils.response import _ok, _err

# ── Hằng số ────────────────────────────────────────────────────────────────────

_IMM_ROLES: list[str] = [
    "IMM System Admin",
    "IMM QA Officer",
    "IMM Department Head",
    "IMM Operations Manager",
    "IMM Workshop Lead",
    "IMM Technician",
    "IMM Document Officer",
    "IMM Storekeeper",
    "IMM Clinical User",
]
_ROLE_ADMIN = "IMM System Admin"
_MSG_NOT_LOGGED_IN = "Chưa đăng nhập"

# ── Private helpers ─────────────────────────────────────────────────────────────

def _safe_field(fieldname: str) -> bool:
    """True khi custom field đã được tạo trên tabUser (bench migrate đã chạy)."""
    return frappe.db.has_column("User", fieldname)


def _get_user_row(user_name: str) -> dict:
    """Đọc các field cơ bản từ tabUser — graceful khi custom field chưa tồn tại."""
    base: dict = frappe.db.get_value(
        "User", user_name,
        ["name", "full_name", "email", "phone", "user_image", "enabled"],
        as_dict=True,
    ) or {}

    for cf in ("imm_approval_status", "imm_approved_by",
               "imm_approved_at", "imm_rejection_reason", "ac_department"):
        base[cf] = frappe.db.get_value("User", user_name, cf) if _safe_field(cf) else None

    return base


# ── HR data helper ─────────────────────────────────────────────────────────────
# tabEmployee ERPNext dùng cột "name" (docname, VD: "HR-EMP-00001") làm định danh.
# Liên kết tới tabUser qua cột "user_id" (= email của User).
# ──────────────────────────────────────────────────────────────────────────────

def _get_hr_data(user_name: str) -> dict:
    """
    Lấy thông tin nhân sự từ bảng Employee.
    Trả {} nếu:
      - Module HR chưa cài (tabEmployee không tồn tại)
      - User chưa có bản ghi Employee
      - Bất kỳ lỗi schema nào
    """
    try:
        if not frappe.db.table_exists("Employee"):
            return {}

        # Chỉ dùng các cột thực sự tồn tại trong tabEmployee chuẩn ERPNext:
        #   name          = docname (mã định danh nhân viên)
        #   employee_name = họ tên đầy đủ
        #   department    = phòng ban ERPNext
        #   designation   = chức danh
        emp = frappe.db.get_value(
            "Employee",
            {"user_id": user_name},
            ["name", "employee_name", "department", "designation"],
            as_dict=True,
        )
        if not emp:
            return {}

        return {
            "hr_docname":    emp.get("name"),           # docname = mã NV, VD: "HR-EMP-00001"
            "hr_full_name":  emp.get("employee_name"),  # họ tên theo hồ sơ HR
            "designation":   emp.get("designation"),    # chức danh
            "erp_department": emp.get("department"),    # phòng ban ERPNext
        }

    except Exception:
        frappe.log_error(frappe.get_traceback(), "_get_hr_data failed")
        return {}


def _get_imm_roles(user_name: str) -> list[str]:
    """Trả danh sách tên IMM role hiện tại của user từ Has Role child table."""
    return [
        r.role
        for r in frappe.get_doc("User", user_name).roles
        if r.role in _IMM_ROLES
    ]


def _get_dept_name(dept_id: str | None) -> str | None:
    if not dept_id:
        return None
    return frappe.db.get_value("AC Department", dept_id, "department_name") or dept_id


def _assert_admin() -> str | None:
    """Trả None nếu caller là IMM Admin / System Manager. Trả chuỗi lỗi nếu không."""
    actor = frappe.session.user
    if actor == "Guest":
        return _MSG_NOT_LOGGED_IN
    actor_roles = {r.role for r in frappe.get_doc("User", actor).roles}
    if _ROLE_ADMIN not in actor_roles and "System Manager" not in actor_roles:
        return f"Chỉ {_ROLE_ADMIN} được thực hiện thao tác này"
    return None


def _parse_json(raw: Any) -> list:
    if isinstance(raw, str):
        return json.loads(raw or "[]")
    return raw or []


def _extract_imm_role_names(raw_roles: list) -> list[str]:
    """Chuẩn hóa payload roles (list[str] hoặc list[dict]) → list[str] hợp lệ."""
    result = []
    for r in raw_roles:
        name = r.get("role") if isinstance(r, dict) else r
        if name in _IMM_ROLES:
            result.append(name)
    return result


# ── Helpers thao tác trên User document ────────────────────────────────────────

def _sync_imm_roles(user_doc: Any, new_roles: list[str]) -> None:
    """
    Thay thế toàn bộ IMM roles trên user_doc bằng new_roles.
    Frappe non-IMM roles (System Manager, v.v.) được giữ nguyên.
    Dùng user_doc.add_roles() để append — chuẩn Frappe child table.
    """
    user_doc.roles = [r for r in user_doc.roles if r.role not in _IMM_ROLES]
    if new_roles:
        user_doc.add_roles(*new_roles)


def _apply_scalar_fields(user_doc: Any, data: dict) -> None:
    for field in ("full_name", "phone"):
        if field in data:
            user_doc.set(field, data[field])
    if "enabled" in data:
        user_doc.enabled = int(data["enabled"])


def _apply_custom_fields(user_doc: Any, data: dict) -> None:
    for cf in ("ac_department", "imm_approval_status", "imm_rejection_reason"):
        if cf in data and _safe_field(cf):
            user_doc.set(cf, data[cf] or None)


def _set_approval(user_doc: Any, roles: list[str]) -> None:
    user_doc.enabled = 1
    user_doc.imm_approval_status = "Approved"
    user_doc.imm_approved_by = frappe.session.user
    user_doc.imm_approved_at = now_datetime()
    user_doc.imm_rejection_reason = ""
    _sync_imm_roles(user_doc, roles)


def _set_rejection(user_doc: Any, reason: str) -> None:
    user_doc.enabled = 0
    user_doc.imm_approval_status = "Rejected"
    if reason:
        user_doc.imm_rejection_reason = reason


def _save_user(user_doc: Any) -> None:
    user_doc.flags.ignore_permissions = True
    user_doc.save()
    frappe.db.commit()


# ── Payload builder ─────────────────────────────────────────────────────────────

def _build_user_detail(user_name: str) -> dict:
    """Tổng hợp User + HR data thành payload chuẩn trả về Frontend."""
    row = _get_user_row(user_name)
    hr = _get_hr_data(user_name)      # {} nếu chưa có bản ghi Employee
    dept_id = row.get("ac_department")

    return {
        "name":              user_name,
        "user":              user_name,
        "full_name":         row.get("full_name") or user_name,
        "email":             row.get("email") or user_name,
        "phone":             row.get("phone"),
        "user_image":        row.get("user_image"),
        "enabled":           row.get("enabled", 1),
        "imm_approval_status": row.get("imm_approval_status") or "Approved",
        "imm_approved_by":   row.get("imm_approved_by"),
        "imm_approved_at":   str(row.get("imm_approved_at") or ""),
        "imm_rejection_reason": row.get("imm_rejection_reason"),
        "ac_department":     dept_id,
        "department_name":   _get_dept_name(dept_id),
        "imm_roles":         _get_imm_roles(user_name),
        # HR fields — đọc từ Employee nếu có, None nếu chưa cài HR hoặc chưa có bản ghi
        "hr_docname":        hr.get("hr_docname"),
        "hr_full_name":      hr.get("hr_full_name"),
        "designation":       hr.get("designation"),
        "erp_department":    hr.get("erp_department"),
        "has_employee":      bool(hr),
    }


# ── Public endpoints ────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_users(
    search: str = "",
    department: str = "",
    is_active: int = None,
    approval_status: str = "",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Liệt kê System Users có phân trang — kèm department_name."""
    page, page_size = int(page), int(page_size)
    offset = (page - 1) * page_size

    filters: dict = {"user_type": "System User", "name": ["!=", "Guest"]}
    if is_active is not None:
        filters["enabled"] = int(is_active)
    if department and _safe_field("ac_department"):
        filters["ac_department"] = department
    if approval_status and _safe_field("imm_approval_status"):
        filters["imm_approval_status"] = approval_status

    or_filters = None
    if search:
        or_filters = [
            ["name", "like", f"%{search}%"],
            ["full_name", "like", f"%{search}%"],
        ]

    total = frappe.db.count("User", filters)

    fields = ["name", "full_name", "email", "enabled", "user_image"]
    if _safe_field("imm_approval_status"):
        fields.append("imm_approval_status")
    if _safe_field("ac_department"):
        fields.append("ac_department")

    users = frappe.get_all(
        "User",
        filters=filters,
        or_filters=or_filters,
        fields=fields,
        limit_start=offset,
        limit_page_length=page_size,
        order_by="full_name asc",
    )

    dept_ids = {u.get("ac_department") for u in users if u.get("ac_department")}
    dept_map: dict = {}
    if dept_ids:
        dept_map = {
            d.name: d.department_name
            for d in frappe.get_all(
                "AC Department",
                filters={"name": ["in", list(dept_ids)]},
                fields=["name", "department_name"],
            )
        }

    for u in users:
        u["department_name"] = dept_map.get(u.get("ac_department") or "", "")
        u["is_active"] = u.get("enabled", 1)
        if "imm_approval_status" not in u:
            u["imm_approval_status"] = "Approved"

    return _ok({
        "items": users,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": max(1, (total + page_size - 1) // page_size),
        },
    })


@frappe.whitelist()
def get_user_info(user: str) -> dict:
    """GET chi tiết một user — User fields + HR/Employee fields (optional)."""
    if not frappe.db.exists("User", user):
        return _err(f"Không tìm thấy user: {user}", 404)
    try:
        return _ok(_build_user_detail(user))
    except Exception as exc:
        frappe.log_error(frappe.get_traceback(), "get_user_info failed")
        return _err(f"Lỗi tải thông tin user: {exc}", 500)


@frappe.whitelist(methods=["POST"])
def update_user_info() -> dict:
    """Admin cập nhật thông tin user — trả về full detail mới sau khi save."""
    err_msg = _assert_admin()
    if err_msg:
        return _err(err_msg, 403)

    data = frappe.local.form_dict
    user_name = data.get("user")
    if not user_name or not frappe.db.exists("User", user_name):
        return _err("user không hợp lệ", 400)

    user_doc = frappe.get_doc("User", user_name)
    _apply_scalar_fields(user_doc, data)
    _apply_custom_fields(user_doc, data)
    if "imm_roles" in data:
        _sync_imm_roles(user_doc, _extract_imm_role_names(_parse_json(data["imm_roles"])))

    _save_user(user_doc)

    try:
        return _ok(_build_user_detail(user_name))
    except Exception as exc:
        frappe.log_error(frappe.get_traceback(), "update_user_info: build detail failed")
        return _ok({"user": user_name, "warning": str(exc)})


@frappe.whitelist(methods=["POST"])
def update_user_roles() -> dict:
    """
    Cập nhật IMM roles cho một user qua UI tích chọn role.

    Payload: { "user": "<email>", "roles": ["IMM Technician", ...] }
    Quyền: chỉ IMM System Admin / System Manager đổi role của người khác.
    Logic: Frappe add_roles() append vào Has Role child table.
    """
    actor = frappe.session.user
    if actor == "Guest":
        return _err(_MSG_NOT_LOGGED_IN, 401)

    data = frappe.local.form_dict
    target = (data.get("user") or actor).strip()
    raw_roles = _parse_json(data.get("roles") or "[]")
    new_imm_roles = _extract_imm_role_names(raw_roles)

    if target != actor:
        err_msg = _assert_admin()
        if err_msg:
            return _err(err_msg, 403)

    if not frappe.db.exists("User", target):
        return _err(f"User không tồn tại: {target}", 404)

    try:
        user_doc = frappe.get_doc("User", target)
        _sync_imm_roles(user_doc, new_imm_roles)
        _save_user(user_doc)
        return _ok({
            "user": target,
            "imm_roles": new_imm_roles,
        })
    except Exception as exc:
        frappe.log_error(frappe.get_traceback(), "update_user_roles failed")
        return _err(f"Lỗi cập nhật roles: {exc}", 500)


@frappe.whitelist(methods=["POST"])
def approve_registration() -> dict:
    """Admin duyệt (approve) hoặc từ chối (reject) user đang Pending."""
    err_msg = _assert_admin()
    if err_msg:
        return _err(err_msg, 403)

    data = frappe.local.form_dict
    user_name = data.get("user")
    if not user_name or not frappe.db.exists("User", user_name):
        return _err("User không tồn tại", 404)
    if not _safe_field("imm_approval_status"):
        return _err("Custom fields chưa cài. Hãy chạy bench migrate.", 500)

    action = (data.get("action") or "approve").lower()
    user_doc = frappe.get_doc("User", user_name)

    if action == "reject":
        _set_rejection(user_doc, data.get("rejection_reason") or "")
    else:
        _set_approval(
            user_doc,
            _extract_imm_role_names(_parse_json(data.get("roles") or "[]")),
        )

    _save_user(user_doc)
    return _ok({
        "user": user_name,
        "status": user_doc.imm_approval_status,
        "enabled": user_doc.enabled,
    })


def _build_new_user_doc(email: str, first_name: str, data: dict, imm_roles: list) -> Any:
    """Tạo User document trong bộ nhớ — chưa insert vào DB."""
    user_doc = frappe.new_doc("User")
    user_doc.email = email
    user_doc.first_name = first_name
    user_doc.last_name = (data.get("last_name") or "").strip()
    user_doc.phone = data.get("phone") or ""
    user_doc.user_type = "System User"
    user_doc.enabled = 1
    user_doc.send_welcome_email = (
        1 if data.get("send_welcome_email") in (1, "1", True, "true") else 0
    )
    if data.get("password"):
        user_doc.new_password = data["password"]
    if imm_roles:
        user_doc.add_roles(*imm_roles)
    user_doc.flags.ignore_permissions = True
    return user_doc


def _insert_user_doc(user_doc: Any, email: str) -> dict | None:
    """Insert user_doc vào DB. Trả _err dict nếu thất bại, None nếu thành công."""
    try:
        user_doc.insert()
        return None
    except frappe.DuplicateEntryError:
        frappe.db.rollback()
        return _err(f"Email '{email}' đã tồn tại trong hệ thống", 409)
    except frappe.exceptions.ValidationError as exc:
        frappe.db.rollback()
        return _err(str(exc), 400)
    except Exception as exc:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "create_system_user insert failed")
        return _err(f"Không thể tạo user: {exc}", 500)


def _stamp_imm_approval(email: str, ac_department: str | None) -> None:
    """Ghi custom fields IMM sau khi User đã insert thành công."""
    if not _safe_field("imm_approval_status"):
        return
    frappe.db.set_value("User", email, {
        "imm_approval_status": "Approved",
        "imm_approved_by": frappe.session.user,
        "imm_approved_at": now_datetime(),
        "ac_department": ac_department or None,
    })


@frappe.whitelist(methods=["POST"])
def create_system_user() -> dict:
    """Admin tạo Frappe User mới (enabled=1, Approved) — không qua luồng đăng ký."""
    err_msg = _assert_admin()
    if err_msg:
        return _err(err_msg, 403)

    data = frappe.local.form_dict
    email = (data.get("email") or "").strip().lower()
    first_name = (data.get("first_name") or "").strip()

    if not email:
        return _err("Thiếu email", 400)
    if not first_name:
        return _err("Thiếu họ tên", 400)
    if frappe.db.exists("User", email):
        return _err(f"Email '{email}' đã tồn tại trong hệ thống", 409)

    imm_roles = _extract_imm_role_names(_parse_json(data.get("imm_roles") or "[]"))
    user_doc = _build_new_user_doc(email, first_name, data, imm_roles)

    insert_err = _insert_user_doc(user_doc, email)
    if insert_err:
        return insert_err

    _stamp_imm_approval(email, data.get("ac_department"))
    frappe.db.commit()
    return _ok({"user": email, "full_name": user_doc.full_name})


@frappe.whitelist(methods=["POST"])
def reset_user_password(user: str, new_password: str) -> dict:
    """Admin reset mật khẩu của bất kỳ user nào."""
    err_msg = _assert_admin()
    if err_msg:
        return _err(err_msg, 403)
    if not frappe.db.exists("User", user):
        return _err(f"User không tồn tại: {user}", 404)
    if len(new_password) < 8:
        return _err("Mật khẩu phải tối thiểu 8 ký tự", 400)

    from frappe.utils.password import update_password
    update_password(user, new_password)
    frappe.db.commit()
    return _ok({"user": user, "reset_by": frappe.session.user})


@frappe.whitelist(methods=["POST"])
def change_my_password(old_password: str, new_password: str) -> dict:
    """User tự đổi mật khẩu."""
    user = frappe.session.user
    if user == "Guest":
        return _err(_MSG_NOT_LOGGED_IN, 401)
    if len(new_password) < 8:
        return _err("Mật khẩu mới phải tối thiểu 8 ký tự", 400)
    if old_password == new_password:
        return _err("Mật khẩu mới phải khác mật khẩu cũ", 400)

    from frappe.utils.password import check_password, update_password
    try:
        check_password(user, old_password)
    except frappe.AuthenticationError:
        return _err("Mật khẩu hiện tại không đúng", 400)

    update_password(user, new_password)
    frappe.db.commit()
    return _ok({"user": user})


@frappe.whitelist()
def get_available_imm_roles() -> dict:
    return _ok([{"name": r, "label": r.replace("IMM ", "")} for r in _IMM_ROLES])


@frappe.whitelist()
def list_frappe_users(search: str = "", limit: int = 30) -> dict:
    """Autocomplete tìm Frappe System Users theo tên / email."""
    limit = max(1, min(int(limit), 100))
    filters: dict = {"enabled": 1, "user_type": ["!=", "Website User"]}
    or_filters = None
    if search:
        or_filters = [
            ["name", "like", f"%{search}%"],
            ["full_name", "like", f"%{search}%"],
            ["email", "like", f"%{search}%"],
        ]
    users = frappe.get_all(
        "User",
        filters=filters,
        or_filters=or_filters,
        fields=["name", "full_name", "email", "user_image"],
        order_by="full_name asc",
        limit_page_length=limit,
    )
    return _ok(users)
