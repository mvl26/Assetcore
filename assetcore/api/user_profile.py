# Copyright (c) 2026, AssetCore Team
"""API endpoints for AC User Profile management."""
import frappe
from frappe import _

from assetcore.utils.helpers import _ok, _err

_DOCTYPE = "AC User Profile"
_IMM_ROLES = [
    "IMM System Admin", "IMM QA Officer", "IMM Department Head",
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


@frappe.whitelist(methods=["POST"])
def upsert_profile() -> dict:
    try:
        data = frappe.local.form_dict
        user = data.get("user")
        if not user:
            return _err("Thiếu trường user", "VALIDATION")

        existing = frappe.db.exists(_DOCTYPE, user)
        doc = frappe.get_doc(_DOCTYPE, user) if existing else frappe.new_doc(_DOCTYPE)

        # CRITICAL: Khi lazy-create profile cho user đã active sẵn trong Frappe,
        # mặc định approval_status="Approved" để controller hook không disable User.
        # Chỉ set Pending nếu là self-signup (thông qua services.auth_service).
        if not existing:
            user_already_enabled = bool(frappe.db.get_value("User", user, "enabled"))
            if user_already_enabled and "approval_status" not in data:
                doc.approval_status = "Approved"

        for field in ("user", "employee_code", "job_title", "phone",
                       "department", "location", "is_active", "notes",
                       "approval_status"):
            if field in data:
                doc.set(field, data.get(field))

        if "imm_roles" in data:
            import json
            raw = data.get("imm_roles") or "[]"
            roles = json.loads(raw) if isinstance(raw, str) else raw
            doc.set("imm_roles", [])
            for r in roles:
                role_name = r.get("role") if isinstance(r, dict) else r
                if role_name:
                    doc.append("imm_roles", {"role": role_name, "notes": r.get("notes", "") if isinstance(r, dict) else ""})

        if "certifications" in data:
            import json
            raw = data.get("certifications") or "[]"
            certs = json.loads(raw) if isinstance(raw, str) else raw
            doc.set("certifications", [])
            for c in certs:
                if c.get("cert_name"):
                    doc.append("certifications", c)

        doc.flags.ignore_permissions = True
        doc.save()
        frappe.db.commit()

        # IMPORTANT: KHÔNG sync IMM roles ngược về Frappe User doc.
        # Frappe User là core DocType — không được mutate từ AssetCore.
        # AC User Profile.imm_roles là source-of-truth riêng cho AssetCore;
        # để cấp role thực sự cho phép Frappe Desk: admin assign Role qua
        # /app/user/<email> bằng tay, hoặc dùng Frappe Role Profile.

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


@frappe.whitelist(methods=["POST"])
def reset_user_password(user: str, new_password: str) -> dict:
    """Admin reset mật khẩu cho user. Yêu cầu role IMM System Admin."""
    try:
        actor = frappe.session.user
        if actor == "Guest":
            return _err(_MSG_NOT_LOGGED_IN, "UNAUTHORIZED")
        actor_roles = {r.role for r in frappe.get_doc("User", actor).roles}
        if "IMM System Admin" not in actor_roles and "System Manager" not in actor_roles:
            return _err("Chỉ IMM System Admin được phép reset mật khẩu", "FORBIDDEN")

        if not frappe.db.exists("User", user):
            return _err(f"User không tồn tại: {user}", "NOT_FOUND")
        if len(new_password) < 8:
            return _err("Mật khẩu phải tối thiểu 8 ký tự", "VALIDATION")

        from frappe.utils.password import update_password
        update_password(user, new_password)
        frappe.db.commit()
        return _ok({"user": user, "reset_by": actor})
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
