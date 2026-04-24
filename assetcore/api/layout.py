# Copyright (c) 2026, AssetCore Team
"""Layout API — notification center + user context + logout for AppTopBar.

Endpoints:
  GET  get_unread_notifications  → danh sách Notification Log chưa đọc
  GET  list_notifications        → danh sách Notification Log (đã đọc + chưa đọc, paginate)
  POST mark_notification_as_read → set read=1 cho 1 notification
  POST mark_all_as_read          → set read=1 cho tất cả
  GET  get_user_context          → tên + khoa/phòng + roles + ảnh
  POST logout_user               → đăng xuất chuẩn Frappe
"""
from __future__ import annotations

import frappe
from frappe import _

from assetcore.utils.response import _ok, _err
from assetcore.utils.pagination import paginate

_DT_NOTIF = "Notification Log"
_DT_DEPT = "AC Department"

_MSG_NOT_LOGGED_IN = "Chưa đăng nhập"

_NOTIF_FIELDS = [
    "name", "subject", "email_content", "document_type", "document_name",
    "type", "for_user", "from_user", "read", "creation",
]


def _serialize_notification(row: dict) -> dict:
    """Trả về shape gọn cho FE — không leak HTML metadata không cần."""
    return {
        "name": row.get("name"),
        "subject": row.get("subject") or "",
        "content": (row.get("email_content") or "").strip(),
        "document_type": row.get("document_type"),
        "document_name": row.get("document_name"),
        "type": row.get("type") or "Alert",
        "from_user": row.get("from_user"),
        "read": int(row.get("read") or 0),
        "creation": row.get("creation"),
    }


@frappe.whitelist()
def get_unread_notifications(limit: int = 20):
    """GET /api/method/assetcore.api.layout.get_unread_notifications

    Trả về { count, items[] } — chỉ unread cho user hiện tại.
    """
    user = frappe.session.user
    if user == "Guest":
        return _err(_(_MSG_NOT_LOGGED_IN), 401)

    limit = max(1, min(int(limit), 100))
    rows = frappe.get_all(
        _DT_NOTIF,
        filters={"for_user": user, "read": 0},
        fields=_NOTIF_FIELDS,
        order_by="creation desc",
        limit_page_length=limit,
    )
    total_unread = frappe.db.count(_DT_NOTIF, {"for_user": user, "read": 0})
    return _ok({
        "count": total_unread,
        "items": [_serialize_notification(r) for r in rows],
    })


@frappe.whitelist()
def list_notifications(page: int = 1, page_size: int = 20, only_unread: int = 0):
    """GET /api/method/assetcore.api.layout.list_notifications

    Paginated list (mặc định bao gồm cả đã đọc).
    """
    user = frappe.session.user
    if user == "Guest":
        return _err(_(_MSG_NOT_LOGGED_IN), 401)

    page, page_size = int(page), int(page_size)
    filters: dict = {"for_user": user}
    if int(only_unread):
        filters["read"] = 0

    total = frappe.db.count(_DT_NOTIF, filters=filters)
    pag = paginate(total, page, page_size)
    rows = frappe.get_all(
        _DT_NOTIF,
        filters=filters,
        fields=_NOTIF_FIELDS,
        order_by="creation desc",
        limit_start=pag["offset"],
        limit_page_length=page_size,
    )
    return _ok({
        "pagination": pag,
        "items": [_serialize_notification(r) for r in rows],
    })


@frappe.whitelist(methods=["POST"])
def mark_notification_as_read(name: str):
    """POST /api/method/assetcore.api.layout.mark_notification_as_read"""
    user = frappe.session.user
    if user == "Guest":
        return _err(_(_MSG_NOT_LOGGED_IN), 401)
    if not frappe.db.exists(_DT_NOTIF, name):
        return _err(_("Notification không tồn tại"), 404)

    owner = frappe.db.get_value(_DT_NOTIF, name, "for_user")
    if owner != user:
        return _err(_("Không có quyền"), 403)

    frappe.db.set_value(_DT_NOTIF, name, "read", 1)
    frappe.db.commit()
    return _ok({"name": name, "read": 1})


@frappe.whitelist(methods=["POST"])
def mark_all_as_read():
    """POST /api/method/assetcore.api.layout.mark_all_as_read"""
    user = frappe.session.user
    if user == "Guest":
        return _err(_(_MSG_NOT_LOGGED_IN), 401)

    frappe.db.sql(
        """UPDATE `tabNotification Log` SET `read`=1
           WHERE for_user=%s AND `read`=0""",
        (user,),
    )
    affected = frappe.db.sql("SELECT ROW_COUNT()")[0][0]
    frappe.db.commit()
    return _ok({"updated_rows": affected})


def _safe_get_user_basic(user: str) -> dict:
    """Lấy thông tin cơ bản từ Frappe User — luôn an toàn (db.get_value, không throw)."""
    data = frappe.db.get_value(
        "User", user,
        ["full_name", "user_image", "phone"],
        as_dict=True,
    ) or {}
    return {
        "full_name": data.get("full_name") or user,
        "user_image": data.get("user_image"),
        "phone": data.get("phone"),
        "roles": frappe.get_roles(user) or [],
    }


def _enrich_from_user_custom_fields(user: str) -> dict:
    """Lấy custom fields IMM trên User (imm_approval_status, ac_department)."""
    result: dict = {}
    if frappe.db.has_column("User", "ac_department"):
        dept_id = frappe.db.get_value("User", user, "ac_department")
        result["department"] = dept_id
        if dept_id:
            result["department_name"] = (
                frappe.db.get_value(_DT_DEPT, dept_id, "department_name") or dept_id
            )
    return result


def _enrich_from_employee(user: str) -> dict:
    """Lookup ERPNext Employee — designation + docname (optional)."""
    if not frappe.db.table_exists("Employee"):
        return {}
    try:
        emp = frappe.db.get_value(
            "Employee", {"user_id": user},
            ["name", "designation"],
            as_dict=True,
        )
    except Exception:
        return {}
    if not emp:
        return {}
    return {
        "hr_docname": emp.get("name"),
        "designation": emp.get("designation"),
        "has_employee_link": True,
    }


@frappe.whitelist()
def get_user_context():
    """GET /api/method/assetcore.api.layout.get_user_context

    Graceful Degradation:
      - LUÔN trả 200 nếu user đã đăng nhập, dù có hay không AC User Profile / Employee.
      - KHÔNG dùng frappe.get_doc() trên DocType có thể không tồn tại.
      - Cờ `is_profile_completed` = True khi profile có ĐỦ: department + job_title.

    Sources (theo thứ tự ưu tiên):
      1. Frappe `User` doc — luôn có sẵn (full_name, user_image, roles)
      2. AssetCore `AC User Profile` — optional (department, job_title, employee_code)
      3. ERPNext `Employee` — optional fallback (designation, department)
    """
    user = frappe.session.user
    if user == "Guest":
        return _err(_(_MSG_NOT_LOGGED_IN), 401)

    basic = _safe_get_user_basic(user)
    custom = _enrich_from_user_custom_fields(user)
    emp = _enrich_from_employee(user)

    department_id = custom.get("department")
    department_name = custom.get("department_name") or emp.get("erp_department")
    designation = emp.get("designation")
    roles = basic["roles"]

    is_profile_completed = bool(department_id and designation)

    return _ok({
        "user": user,
        "full_name": basic["full_name"],
        "user_image": basic["user_image"],
        "phone": basic["phone"],
        "roles": roles,
        "imm_roles": [r for r in roles if r.startswith("IMM ")],
        "designation": designation,
        "hr_docname": emp.get("hr_docname"),
        "department": department_id,
        "department_name": department_name,
        "is_profile_completed": is_profile_completed,
        "has_employee_link": emp.get("has_employee_link", False),
    })


@frappe.whitelist(allow_guest=True)
def ping_session():
    """GET /api/method/assetcore.api.layout.ping_session

    Endpoint nhẹ — Frappe sẽ set csrf_token cookie qua response.
    Dùng để FE warm-up CSRF token mà KHÔNG gọi vào frappe core API.
    Trả về user hiện tại (Guest nếu chưa login).
    """
    user = frappe.session.user
    return _ok({"user": user, "authenticated": user != "Guest"})


@frappe.whitelist(methods=["POST"])
def logout_user():
    """POST /api/method/assetcore.api.layout.logout_user

    Gọi LoginManager.logout() chuẩn của Frappe — clear session cookie + DB session.
    """
    if frappe.session.user == "Guest":
        return _ok({"already_logged_out": True})

    frappe.local.login_manager.logout()
    frappe.db.commit()
    return _ok({"logged_out": True})
