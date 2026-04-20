# Copyright (c) 2026, AssetCore Team
"""API endpoints for AC User Profile management."""
import frappe
from frappe import _

from assetcore.utils.helpers import _ok, _err

_DOCTYPE = "AC User Profile"
_ROLE_ADMIN = "IMM System Admin"
_IMM_ROLES = [
    _ROLE_ADMIN, "IMM QA Officer", "IMM Department Head",
    "IMM Operations Manager", "IMM Workshop Lead", "IMM Technician",
    "IMM Document Officer",
]

_MSG_NOT_LOGGED_IN = "Chưa đăng nhập"


@frappe.whitelist()
def list_profiles(search: str = "", department: str = "", is_active: int = None,
                   page: int = 1, page_size: int = 20) -> dict:
    try:
        filters: dict = {}
        if department:
            filters["department"] = department
        if is_active is not None:
            filters["is_active"] = int(is_active)

        or_filters = None
        if search:
            or_filters = [
                ["user", "like", f"%{search}%"],
                ["full_name", "like", f"%{search}%"],
                ["employee_code", "like", f"%{search}%"],
            ]

        page, page_size = int(page), int(page_size)
        offset = (page - 1) * page_size
        total = frappe.db.count(_DOCTYPE, filters)
        items = frappe.get_list(
            _DOCTYPE,
            filters=filters,
            or_filters=or_filters,
            fields=["name", "user", "full_name", "email", "employee_code",
                    "job_title", "department", "location", "is_active", "modified"],
            limit_start=offset,
            limit_page_length=page_size,
            order_by="modified desc",
        )
        dept_ids = {i.get("department") for i in items if i.get("department")}
        dept_map = {d.name: d.department_name for d in frappe.get_all(
            "AC Department", filters={"name": ["in", list(dept_ids)]}, fields=["name", "department_name"],
        )} if dept_ids else {}
        for item in items:
            item["department_name"] = dept_map.get(item.get("department"), item.get("department") or "")

        return _ok({
            "items": items,
            "pagination": {"page": page, "page_size": page_size, "total": total,
                            "total_pages": (total + page_size - 1) // page_size if total else 0,
                            "offset": offset},
        })
    except Exception as e:
        return _err(str(e))


@frappe.whitelist()
def get_profile(name: str) -> dict:
    """GET profile theo User name.

    Behavior:
      - Nếu AC User Profile tồn tại → trả về full doc.
      - Nếu chưa có nhưng Frappe User tồn tại → synth skeleton từ User (FE
        có thể pre-fill và save → upsert sẽ tạo mới). Field is_synth=1.
      - Nếu cả User cũng không có → 404.
    """
    try:
        if frappe.db.exists(_DOCTYPE, name):
            doc = frappe.get_doc(_DOCTYPE, name)
            data = doc.as_dict()
            data["is_synth"] = 0
            # gắn Frappe roles để FE hiển thị tham khảo
            data["frappe_roles"] = [
                r.role for r in frappe.get_doc("User", name).roles
            ]
            return _ok(data)

        if not frappe.db.exists("User", name):
            return _err(f"Không tìm thấy User: {name}", "NOT_FOUND")

        # Synth skeleton từ Frappe User
        u = frappe.get_doc("User", name)
        existing_imm_roles = [
            {"role": r.role} for r in u.roles if r.role in _IMM_ROLES
        ]
        return _ok({
            "name": name,
            "user": name,
            "full_name": u.full_name or "",
            "email": u.email or name,
            "phone": u.phone or "",
            "employee_code": "",
            "job_title": "",
            "department": None,
            "location": None,
            "is_active": 1 if u.enabled else 0,
            "approval_status": "Pending",
            "imm_roles": existing_imm_roles,
            "certifications": [],
            "notes": "",
            "is_synth": 1,
            "frappe_roles": [r.role for r in u.roles],
        })
    except Exception as e:
        return _err(str(e))


def _parse_json_list(raw) -> list:
    import json
    if isinstance(raw, str):
        return json.loads(raw or "[]")
    return raw or []


def _set_imm_roles(doc, raw_roles) -> None:
    roles = _parse_json_list(raw_roles)
    doc.set("imm_roles", [])
    for r in roles:
        role_name = r.get("role") if isinstance(r, dict) else r
        if role_name:
            doc.append("imm_roles", {
                "role": role_name,
                "notes": r.get("notes", "") if isinstance(r, dict) else "",
            })


def _set_certifications(doc, raw_certs) -> None:
    certs = _parse_json_list(raw_certs)
    doc.set("certifications", [])
    for c in certs:
        if c.get("cert_name"):
            doc.append("certifications", c)


@frappe.whitelist(methods=["POST"])
def upsert_profile() -> dict:
    try:
        data = frappe.local.form_dict
        user = data.get("user")
        if not user:
            return _err("Thiếu trường user", "VALIDATION")

        existing = frappe.db.exists(_DOCTYPE, user)
        doc = frappe.get_doc(_DOCTYPE, user) if existing else frappe.new_doc(_DOCTYPE)

        # CRITICAL: lazy-create profile cho user đã active → Approved để không disable User.
        if not existing:
            if bool(frappe.db.get_value("User", user, "enabled")) and "approval_status" not in data:
                doc.approval_status = "Approved"

        for field in ("user", "employee_code", "job_title", "phone",
                       "department", "location", "is_active", "notes", "approval_status"):
            if field in data:
                doc.set(field, data.get(field))

        if "imm_roles" in data:
            _set_imm_roles(doc, data.get("imm_roles"))
        if "certifications" in data:
            _set_certifications(doc, data.get("certifications"))

        doc.flags.ignore_permissions = True
        doc.save()
        frappe.db.commit()
        return _ok({"name": doc.name, "user": doc.user})
    except Exception as e:
        return _err(str(e))


@frappe.whitelist()
def get_available_imm_roles() -> dict:
    return _ok([{"name": r, "label": r.replace("IMM ", "")} for r in _IMM_ROLES])


@frappe.whitelist()
def list_frappe_users(search: str = "", limit: int = 30) -> dict:
    """Liệt kê Frappe Users (enabled) — phục vụ form pick user khi tạo profile."""
    try:
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
        # Mark which already have AC User Profile
        existing = {p.user for p in frappe.get_all(_DOCTYPE, fields=["user"])}
        for u in users:
            u["has_profile"] = 1 if u["name"] in existing else 0
        return _ok(users)
    except Exception as e:
        return _err(str(e))


def _assert_admin() -> str | None:
    """Trả về None nếu OK, hoặc error message nếu không đủ quyền."""
    actor = frappe.session.user
    if actor == "Guest":
        return _MSG_NOT_LOGGED_IN
    actor_roles = {r.role for r in frappe.get_doc("User", actor).roles}
    if _ROLE_ADMIN not in actor_roles and "System Manager" not in actor_roles:
        return f"Chỉ {_ROLE_ADMIN} được thực hiện thao tác này"
    return None


def _create_frappe_user(email: str, first_name: str, last_name: str,
                        password: str, send_welcome: bool, imm_roles: list) -> "frappe.Document":
    user_doc = frappe.new_doc("User")
    user_doc.email = email
    user_doc.first_name = first_name
    user_doc.last_name = last_name
    user_doc.send_welcome_email = 1 if send_welcome else 0
    user_doc.user_type = "System User"
    user_doc.enabled = 1
    if password:
        user_doc.new_password = password
    user_doc.flags.ignore_permissions = True
    user_doc.insert()
    for r in imm_roles:
        role_name = r.get("role") if isinstance(r, dict) else r
        if role_name and role_name in _IMM_ROLES:
            user_doc.append("roles", {"role": role_name})
    user_doc.flags.ignore_permissions = True
    user_doc.save()
    return user_doc


def _create_imm_profile(email: str, full_name: str, data: dict, imm_roles: list) -> "frappe.Document":
    profile = frappe.new_doc(_DOCTYPE)
    profile.user = email
    profile.full_name = full_name
    profile.email = email
    profile.approval_status = "Approved"
    profile.is_active = 1
    for field in ("employee_code", "job_title", "phone", "department", "location", "notes"):
        val = data.get(field)
        if val:
            profile.set(field, val)
    _set_imm_roles(profile, imm_roles)
    _set_certifications(profile, data.get("certifications") or "[]")
    profile.flags.ignore_permissions = True
    profile.insert()
    return profile


@frappe.whitelist(methods=["POST"])
def create_user() -> dict:
    """Tạo Frappe User MỚI + AC User Profile cùng lúc. Yêu cầu role IMM System Admin."""
    try:
        err_msg = _assert_admin()
        if err_msg:
            return _err(err_msg, "FORBIDDEN" if frappe.session.user != "Guest" else "UNAUTHORIZED")

        data = frappe.local.form_dict
        email = (data.get("email") or "").strip().lower()
        first_name = (data.get("first_name") or "").strip()
        if not email:
            return _err("Thiếu email", "VALIDATION")
        if not first_name:
            return _err("Thiếu họ tên", "VALIDATION")
        if frappe.db.exists("User", email):
            return _err(f"Email {email} đã có tài khoản Frappe", "DUPLICATE")

        imm_roles = _parse_json_list(data.get("imm_roles") or "[]")
        last_name = (data.get("last_name") or "").strip()
        send_welcome = data.get("send_welcome_email") in (1, "1", True, "true")

        user_doc = _create_frappe_user(email, first_name, last_name,
                                       data.get("password") or "", send_welcome, imm_roles)
        full_name = f"{first_name} {user_doc.last_name}".strip()
        profile = _create_imm_profile(email, full_name, data, imm_roles)
        frappe.db.commit()
        return _ok({"user": email, "name": profile.name, "full_name": profile.full_name})
    except Exception as e:
        frappe.db.rollback()
        return _err(str(e))


@frappe.whitelist(methods=["POST"])
def reset_user_password(user: str, new_password: str) -> dict:
    """Admin reset mật khẩu cho user. Yêu cầu role IMM System Admin."""
    try:
        err_msg = _assert_admin()
        if err_msg:
            return _err(err_msg, "FORBIDDEN" if frappe.session.user != "Guest" else "UNAUTHORIZED")

        if not frappe.db.exists("User", user):
            return _err(f"User không tồn tại: {user}", "NOT_FOUND")
        if len(new_password) < 8:
            return _err("Mật khẩu phải tối thiểu 8 ký tự", "VALIDATION")

        from frappe.utils.password import update_password
        update_password(user, new_password)
        frappe.db.commit()
        return _ok({"user": user, "reset_by": frappe.session.user})
    except Exception as e:
        return _err(str(e))


@frappe.whitelist(methods=["POST"])
def change_my_password(old_password: str, new_password: str) -> dict:
    """User tự đổi mật khẩu — yêu cầu old_password để verify."""
    try:
        user = frappe.session.user
        if user == "Guest":
            return _err(_MSG_NOT_LOGGED_IN, "UNAUTHORIZED")
        if len(new_password) < 8:
            return _err("Mật khẩu mới phải tối thiểu 8 ký tự", "VALIDATION")
        if old_password == new_password:
            return _err("Mật khẩu mới phải khác mật khẩu cũ", "VALIDATION")

        from frappe.utils.password import check_password, update_password
        try:
            check_password(user, old_password)
        except frappe.AuthenticationError:
            return _err("Mật khẩu hiện tại không đúng", "AUTH_FAIL")

        update_password(user, new_password)
        frappe.db.commit()
        return _ok({"user": user})
    except Exception as e:
        return _err(str(e))


@frappe.whitelist()
def get_my_profile() -> dict:
    user = frappe.session.user
    if user == "Guest":
        return _err(_MSG_NOT_LOGGED_IN, "UNAUTHORIZED")
    if not frappe.db.exists(_DOCTYPE, user):
        return _ok({"user": user, "profile": None})
    doc = frappe.get_doc(_DOCTYPE, user)
    return _ok({"user": user, "profile": doc.as_dict()})
