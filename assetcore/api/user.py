# Copyright (c) 2026, AssetCore Team
"""
IMM-00 User Management API.

Data model:
  User  (Frappe core) — xác thực, custom fields IMM, Has Role child table
  Employee (optional, nếu cài Frappe HR) — liên kết qua Employee.user_id = User.name

Custom fields trên tabUser (tạo bởi assetcore.setup.install.after_migrate):
  imm_approval_status | imm_approved_by | imm_approved_at
  imm_rejection_reason | ac_department
"""
from __future__ import annotations

import json
from typing import Any

import frappe
from frappe.utils import now_datetime, get_url

from assetcore.utils.response import _ok, _err
from assetcore.utils.helpers import _safe_sendmail

# ── Hằng số ────────────────────────────────────────────────────────────────────

from assetcore.services.shared.constants import Roles, ROLE_METADATA
from assetcore.setup.role_profile_catalog import BASE_ROLE

# Single source of truth — đồng bộ với fixtures/role.json
_IMM_ROLES: list[str] = list(Roles.ALL)
_ROLE_ADMIN = Roles.SUPER_ADMIN
_DT_ROLE_PROFILE = "Role Profile"
_MSG_NOT_LOGGED_IN = "Chưa đăng nhập"

# ── Private helpers ─────────────────────────────────────────────────────────────

def _safe_field(fieldname: str) -> bool:
    """True khi custom field đã được tạo trên tabUser (bench migrate đã chạy)."""
    return frappe.db.has_column("User", fieldname)


def _get_user_row(user_name: str) -> dict:
    """Đọc các field cơ bản từ tabUser — graceful khi custom field chưa tồn tại."""
    base: dict = frappe.db.get_value(
        "User", user_name,
        ["name", "full_name", "email", "phone", "user_image", "enabled", "role_profile_name"],
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


def _get_imm_roles(user_name: str) -> list[dict]:
    """Trả danh sách IMM role hiện tại — format Has Role child table: [{"role": "..."}]."""
    return [
        {"role": r.role}
        for r in frappe.get_doc("User", user_name).roles
        if r.role in _IMM_ROLES
    ]


def _get_dept_name(dept_id: str | None) -> str | None:
    if not dept_id:
        return None
    return frappe.db.get_value("AC Department", dept_id, "department_name") or dept_id


def _assert_admin() -> str | None:
    """Trả None nếu caller có capability `data.admin` (Super Admin hoặc
    System Manager qua umbrella). Trả chuỗi lỗi nếu không."""
    actor = frappe.session.user
    if actor == "Guest":
        return _MSG_NOT_LOGGED_IN
    from assetcore.services.shared import rbac
    if not rbac.can("data.admin"):
        return "Chỉ quản trị hệ thống được thực hiện thao tác này"
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


def _users_with_role(role: str) -> list[str]:
    """Tên (email) các User giữ `role` — resolve qua child table Has Role.

    `frappe.db.count` / `get_all` trên User không filter xuyên child table được
    nên phải resolve danh sách parent trước rồi lọc `name in [...]`.
    """
    return [
        r["parent"]
        for r in frappe.get_all(
            "Has Role",
            filters={"parenttype": "User", "role": role},
            fields=["parent"],
        )
    ]


def _profile_lock_error(user_name: str) -> dict | None:
    """Trả _err nếu user đang gắn Role Profile → role bị khoá, không sửa thủ công.

    Core Doc §7.quinquies: khi User.role_profile_name ≠ rỗng, Frappe core
    `populate_role_profile_roles` clear+replace role mỗi lần save → sửa thủ công
    vô nghĩa (bị ghi đè). Chặn sớm với thông báo rõ thay vì để user tưởng đã sửa.
    """
    profile = frappe.db.get_value("User", user_name, "role_profile_name")
    if profile:
        return _err(
            f"Role của user đang được quản lý bởi Role Profile '{profile}'. "
            "Bỏ Role Profile để sửa role thủ công.",
            409,
        )
    return None


# ── Helpers thao tác trên User document ────────────────────────────────────────

def _ensure_base_role(user_doc: Any) -> None:
    """Đảm bảo user luôn giữ base role `AssetCore System User`.

    Base role = định danh "user AssetCore" (đăng nhập SPA + đọc shared-core) →
    BẮT BUỘC trên mọi user trong scope, KHÔNG gỡ được qua UI. Re-inject nếu bị
    thiếu sau khi sửa role. SSoT = `role_profile_catalog.BASE_ROLE`.
    """
    if not any(r.role == BASE_ROLE for r in user_doc.roles):
        user_doc.append("roles", {"role": BASE_ROLE})


def _sync_imm_roles(user_doc: Any, new_roles: list[str]) -> None:
    """
    Thay thế toàn bộ IMM roles trên user_doc bằng new_roles.
    Frappe non-IMM roles (System Manager, v.v.) được giữ nguyên.

    CHÚ Ý: KHÔNG dùng `user_doc.add_roles()` — method này gọi `self.save()`
    nội bộ mà KHÔNG có `flags.ignore_permissions = True`. Frappe User DocType
    có DocPerm restrictive nên save fail âm thầm và rollback role changes →
    bug "Lưu thành công nhưng role không vào DB" (theo cảm nhận user). Thay
    vào đó, chỉ MUTATE child table `roles` trong bộ nhớ; caller `_save_user`
    sẽ gọi `user_doc.save()` MỘT LẦN duy nhất với `ignore_permissions = True`.
    """
    # 1. Giữ lại non-IMM roles (System Manager, Maintenance User, …)
    user_doc.set("roles", [r for r in user_doc.roles if r.role not in _IMM_ROLES])
    # 2. Append IMM roles mới — không gọi save, để _save_user lo
    existing = {r.role for r in user_doc.roles}
    for role in new_roles:
        if role not in existing:
            user_doc.append("roles", {"role": role})
            existing.add(role)
    # 3. Base role bắt buộc — re-inject dù payload không gồm (không gỡ qua UI).
    _ensure_base_role(user_doc)


def _apply_scalar_fields(user_doc: Any, data: dict) -> None:
    # full_name is auto-computed from first_name + middle_name + last_name in Frappe's
    # User.update_full_name(). Setting full_name directly is silently overwritten on save.
    # Split into first_name + last_name so the change actually persists.
    if "full_name" in data:
        full = (data["full_name"] or "").strip()
        parts = full.split(None, 1)
        user_doc.first_name = parts[0] if parts else ""
        user_doc.middle_name = ""
        user_doc.last_name = parts[1] if len(parts) > 1 else ""
    if "phone" in data:
        user_doc.set("phone", data["phone"])
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
    # Frappe core validate() chạy set_system_user() — hạ user_type xuống
    # "Website User" nếu user không có desk-access role. Module IMM coi mọi
    # user trong scope là System User (kể cả khi tạm chưa gán role) → ép lại.
    if user_doc.user_type != "System User":
        frappe.db.set_value("User", user_doc.name, "user_type", "System User")
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
        "role_profile_name": row.get("role_profile_name"),
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
    role: str = "",
    is_active: int = None,
    approval_status: str = "",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Liệt kê System Users có phân trang — kèm department_name."""
    page, page_size = int(page), int(page_size)
    page_size = max(1, min(page_size, 100))  # cap chống unbounded-fetch (LL-BE-43)
    offset = (page - 1) * page_size

    filters: dict = {"user_type": "System User", "name": ["!=", "Guest"]}
    if is_active is not None:
        filters["enabled"] = int(is_active)
    if department and _safe_field("ac_department"):
        filters["ac_department"] = department
    if approval_status and _safe_field("imm_approval_status"):
        filters["imm_approval_status"] = approval_status

    # Chỉ "user AssetCore" — phải giữ base role `AssetCore System User`. Role nằm ở
    # child table Has Role (parent=User) → resolve danh sách User trước rồi lọc
    # `name in [...]` (frappe.db.count/get_all không filter xuyên child table).
    # Loại Administrator/Guest (infra account, không thuộc scope user AssetCore).
    base_holders = set(_users_with_role(BASE_ROLE)) - {"Administrator", "Guest"}
    if role and role in _IMM_ROLES:
        # Lọc thêm theo 1 IMM role cụ thể → giao với tập base-holder.
        base_holders &= set(_users_with_role(role))
    # Tập rỗng → ép kết quả rỗng (tránh trả toàn bộ). count & rows dùng CÙNG
    # filters["name"] nên pagination.total luôn khớp số dòng (LL-BE-42).
    filters["name"] = ["in", sorted(base_holders) or [""]]

    or_filters = None
    if search:
        or_filters = [
            ["name", "like", f"%{search}%"],
            ["full_name", "like", f"%{search}%"],
        ]

    total = frappe.db.count("User", filters)

    fields = ["name", "full_name", "email", "enabled", "user_image", "role_profile_name"]
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

    # Batch-load IMM roles cho tất cả user trong trang (tránh N+1)
    user_names = [u["name"] for u in users]
    roles_map: dict[str, list[str]] = {n: [] for n in user_names}
    if user_names:
        rows = frappe.get_all(
            "Has Role",
            filters={"parent": ("in", user_names), "role": ("in", _IMM_ROLES)},
            fields=["parent", "role"],
        )
        for r in rows:
            roles_map.setdefault(r["parent"], []).append(r["role"])

    for u in users:
        u["department_name"] = dept_map.get(u.get("ac_department") or "", "")
        u["is_active"] = u.get("enabled", 1)
        if "imm_approval_status" not in u:
            u["imm_approval_status"] = "Approved"
        u["imm_roles"] = [
            {
                "name": r,
                "label": ROLE_METADATA.get(r, {}).get("label") or r.replace("IMM ", ""),
                "group": ROLE_METADATA.get(r, {}).get("group", "Other"),
            }
            for r in roles_map.get(u["name"], [])
        ]

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

    # Sửa role thủ công khi user có Role Profile → chặn (role bị khoá).
    if "imm_roles" in data:
        lock_err = _profile_lock_error(user_name)
        if lock_err:
            return lock_err

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
    Quyền: BẮT BUỘC capability data.admin — đổi role là hành vi CẤP QUYỀN.
    Core Doc §7.sexies.2: KHÔNG cho self-edit miễn admin (tránh leo quyền —
    user tự gán Super Admin cho chính mình). Self-edit role ≠ self-service.
    Logic: _sync_imm_roles thay bộ IMM role; save một lần.
    """
    actor = frappe.session.user
    if actor == "Guest":
        return _err(_MSG_NOT_LOGGED_IN, 401)

    # Đổi role = cấp quyền → luôn yêu cầu admin, kể cả khi sửa chính mình.
    err_msg = _assert_admin()
    if err_msg:
        return _err(err_msg, 403)

    data = frappe.local.form_dict
    target = (data.get("user") or actor).strip()
    raw_roles = _parse_json(data.get("roles") or "[]")
    new_imm_roles = _extract_imm_role_names(raw_roles)

    if not frappe.db.exists("User", target):
        return _err(f"User không tồn tại: {target}", 404)

    # Role bị khoá khi user có Role Profile — chặn sửa thủ công.
    lock_err = _profile_lock_error(target)
    if lock_err:
        return lock_err

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

    # Idempotency (G1): chỉ gửi email kích hoạt khi THỰC SỰ chuyển sang Approved.
    # Nếu user đã Approved sẵn → approve lại là no-op về mặt notification.
    was_approved = (user_doc.get("imm_approval_status") == "Approved")

    if action == "reject":
        _set_rejection(user_doc, data.get("rejection_reason") or "")
    else:
        _set_approval(
            user_doc,
            _extract_imm_role_names(_parse_json(data.get("roles") or "[]")),
        )

    _save_user(user_doc)

    # G1: gửi email kích hoạt cho user — chỉ khi vừa chuyển sang Approved.
    # Robust: lỗi gửi mail KHÔNG được làm fail transaction approve (user đã
    # được enabled trong DB; mail chỉ là thông báo phụ).
    if action != "reject" and not was_approved:
        _send_activation_email(user_name)

    return _ok({
        "user": user_name,
        "status": user_doc.imm_approval_status,
        "enabled": user_doc.enabled,
    })


def _send_activation_email(user_name: str) -> None:
    """G1: thông báo cho user rằng tài khoản đã được kích hoạt + link đăng nhập.

    Wrap toàn bộ trong try/except: gửi mail là side-effect phụ, KHÔNG được
    phép phá transaction approve (user đã enabled=1 ở DB). `_safe_sendmail`
    đã bỏ qua khi email server chưa cấu hình, nhưng vẫn bọc thêm 1 lớp để
    chống mọi lỗi resolve URL / lookup.
    """
    try:
        full_name = frappe.db.get_value("User", user_name, "full_name") or user_name
        # FE route đăng nhập là /login (Vue Router history mode dưới site URL).
        login_url = f"{get_url()}/login"
        _safe_sendmail(
            recipients=[user_name],
            subject="[AssetCore] Tài khoản của bạn đã được kích hoạt",
            message=(
                f"<p>Xin chào <b>{frappe.utils.escape_html(full_name)}</b>,</p>"
                f"<p>Tài khoản AssetCore của bạn đã được quản trị viên "
                f"<b>kích hoạt</b>. Bạn có thể đăng nhập ngay bây giờ.</p>"
                f"<p><a href=\"{login_url}\" "
                f"style=\"display:inline-block;padding:10px 18px;background:#2563eb;"
                f"color:#fff;border-radius:6px;text-decoration:none\">Đăng nhập</a></p>"
                f"<p>Hoặc truy cập: <a href=\"{login_url}\">{login_url}</a></p>"
                f"<p style=\"color:#888;font-size:12px\">Email tự động từ hệ thống "
                f"AssetCore — vui lòng không trả lời.</p>"
            ),
            reference_doctype="User",
            reference_name=user_name,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "approve: send activation email failed")


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
    # Base role bắt buộc cho mọi user tạo từ UI AssetCore (định danh user
    # AssetCore) + các domain role admin đã chọn. dedupe giữ thứ tự, base trước.
    seen: set[str] = set()
    for role in (BASE_ROLE, *imm_roles):
        if role not in seen:
            seen.add(role)
            user_doc.append("roles", {"role": role})
    user_doc.flags.ignore_permissions = True
    return user_doc


def _cleanup_orphan_contacts(email: str) -> int:
    """
    Xóa Contact + Contact Email orphan (Contact với email_id = `email` mà không có
    User tương ứng). Frappe khi tạo User auto-tạo Contact, nhưng `delete_doc(User)`
    không cascade — để lại orphan gây DuplicateEntryError ở lần insert sau.
    Return số Contact đã xóa.
    """
    rows = frappe.db.sql(
        """
        SELECT c.name FROM `tabContact` c
        LEFT JOIN `tabUser` u ON LOWER(u.email) = LOWER(c.email_id)
        WHERE LOWER(c.email_id) = %s AND u.name IS NULL
        """,
        (email.lower(),),
        as_dict=True,
    )
    n = 0
    for r in rows:
        try:
            frappe.delete_doc("Contact", r["name"], ignore_permissions=True, force=True)
            n += 1
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"Cleanup orphan Contact {r['name']} failed")
    if n:
        frappe.db.commit()
    return n


def _insert_user_doc(user_doc: Any, email: str) -> dict | None:
    """Insert user_doc vào DB. Trả _err dict nếu thất bại, None nếu thành công."""
    try:
        user_doc.insert()
        return None
    except frappe.DuplicateEntryError:
        frappe.db.rollback()
        # Trường hợp Contact orphan từ User cũ đã xóa — auto-cleanup và retry 1 lần.
        if _cleanup_orphan_contacts(email):
            try:
                user_doc.insert()
                return None
            except Exception:
                frappe.db.rollback()
        existing = frappe.db.exists("User", email) or frappe.db.exists("User", {"email": email})
        return _err(
            f"Email '{email}' đã tồn tại trong hệ thống",
            409,
            extra={"existing_user": existing} if existing else None,
        )
    except frappe.exceptions.ValidationError as exc:
        frappe.db.rollback()
        return _err(str(exc), 400)
    except Exception as exc:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "create_system_user insert failed")
        return _err(f"Không thể tạo user: {exc}", 500)


def _stamp_imm_approval(email: str, ac_department: str | None) -> None:
    """Ghi custom fields IMM sau khi User đã insert thành công.

    Đồng thời ép user_type = "System User": Frappe core `User.set_system_user()`
    chạy trong validate() sẽ tự hạ cấp xuống "Website User" nếu user không có
    role nào có desk_access=1 (xảy ra khi admin tạo user mà chưa tick role IMM
    nào). Direct DB write bypass logic đó để user mới luôn xuất hiện trong
    `list_users` (vốn lọc theo user_type="System User").
    """
    payload: dict = {"user_type": "System User"}
    if _safe_field("imm_approval_status"):
        payload.update({
            "imm_approval_status": "Approved",
            "imm_approved_by": frappe.session.user,
            "imm_approved_at": now_datetime(),
            "ac_department": ac_department or None,
        })
    frappe.db.set_value("User", email, payload)


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
    password = (data.get("password") or "").strip()
    if password and len(password) < 10:
        return _err(
            "Mật khẩu phải có tối thiểu 10 ký tự. Khuyến nghị kết hợp chữ hoa, "
            "chữ thường, số và ký tự đặc biệt.",
            400,
        )
    # Kiểm tra cả primary key (name) và field email — case-insensitive để tránh
    # false negative khi user nhập IN HOA mà DB lưu thường.
    by_name = frappe.db.exists("User", email)
    by_email = frappe.db.exists("User", {"email": email}) if not by_name else None
    existing = by_name or by_email
    if existing:
        # Log chi tiết để debug khi user báo "ko tạo được" — xem app log để biết
        # lý do thực sự (maybe user thấy field bị restore từ form draft).
        frappe.logger().info(
            f"[create_system_user] DUPLICATE blocked: email={email!r} "
            f"matched_by={'name' if by_name else 'email_field'} existing={existing!r}"
        )
        return _err(
            f"Email '{email}' đã tồn tại trong hệ thống",
            409,
            extra={
                "existing_user": existing,
                "matched_by": "name" if by_name else "email_field",
            },
        )

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
    if len(new_password) < 10:
        return _err("Mật khẩu phải tối thiểu 10 ký tự", 400)

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
    """Danh sách role IMM kèm metadata để FE hiển thị nhãn tiếng Việt + mô tả + nhóm."""
    items = []
    for r in _IMM_ROLES:
        meta = ROLE_METADATA.get(r, {})
        items.append({
            "name": r,
            "label": meta.get("label") or r.replace("IMM ", ""),
            "description": meta.get("description", ""),
            "group": meta.get("group", "Other"),
        })
    return _ok(items)


@frappe.whitelist()
def list_role_profiles() -> dict:
    """Danh sách 8 Role Profile (catalog, core DocType, tên VI).

    Core Doc FE_Persona_Navigation.md §7.quinquies. FE chọn 1 profile → BE gán
    vào `User.role_profile_name`, Frappe core tự clear+replace role thành viên.
    FE tự gắn nhãn persona (nếu muốn) — BE chỉ trả Role Profile thuần.
    """
    from assetcore.setup.role_profile_catalog import PROFILE_NAMES
    profiles = frappe.get_all(
        _DT_ROLE_PROFILE,
        filters={"name": ("in", PROFILE_NAMES)},
        fields=["name", "role_profile"],
        order_by="role_profile asc",
    )
    # Kèm danh sách role thành viên (đọc child table Has Role)
    result = []
    for p in profiles:
        roles = frappe.get_all(
            "Has Role",
            filters={"parent": p.name, "parenttype": _DT_ROLE_PROFILE},
            fields=["role"],
            pluck="role",
        )
        result.append({
            "name": p.name,
            "label": p.role_profile,
            "roles": [
                {
                    "name": r,
                    "label": ROLE_METADATA.get(r, {}).get("label") or r.replace("IMM ", ""),
                    "group": ROLE_METADATA.get(r, {}).get("group", "Other"),
                }
                for r in roles
            ],
        })
    return _ok(result)


@frappe.whitelist(methods=["POST"])
def assign_role_profile(user: str, role_profile: str = "") -> dict:
    """Gán Role Profile cho user. Đặt chuỗi rỗng để bỏ profile.

    Frappe core tự động sync các role trong profile vào user.roles khi
    `role_profile_name` đổi (thông qua `User.validate_roles_through_role_profile`).
    """
    if frappe.session.user == "Guest":
        return _err(_MSG_NOT_LOGGED_IN, 401)
    if not frappe.db.exists("User", user):
        return _err(f"User '{user}' không tồn tại", 404)
    if role_profile and not frappe.db.exists(_DT_ROLE_PROFILE, role_profile):
        return _err(f"Role Profile '{role_profile}' không tồn tại", 404)

    # Gán Role Profile = cấp quyền (core clear+replace roles theo profile) →
    # BẮT BUỘC admin, kể cả khi đổi của chính mình. Core Doc §7.sexies.2:
    # cho phép self-assign sẽ thành lỗ leo quyền (tự gán profile "Quản trị viên IT").
    err_msg = _assert_admin()
    if err_msg:
        return _err(err_msg, 403)

    user_doc = frappe.get_doc("User", user)
    user_doc.role_profile_name = role_profile or None
    user_doc.flags.ignore_permissions = True
    user_doc.save()  # core Frappe code sẽ sync roles từ profile
    frappe.db.commit()

    return _ok({
        "user": user,
        "role_profile": role_profile or None,
        "imm_roles": _get_imm_roles(user),
    })


# ─── RBAC admin endpoints (trang /admin/roles) ──────────────────────────────


@frappe.whitelist()
def list_assignable_roles() -> dict:
    """Catalog 30 role (RBAC module-based) + metadata cho FE grid.

    Gate: capability `data.admin` — chỉ Super Admin (+ Frappe System Manager
    qua umbrella) gọi được.
    """
    from assetcore.services.shared import rbac
    rbac.require("data.admin")
    catalog = [
        {"name": n, **ROLE_METADATA.get(n, {})}
        for n in _IMM_ROLES
    ]
    return _ok(catalog)


@frappe.whitelist(methods=["POST"])
def set_user_roles(user: str, roles=None) -> dict:
    """Thay toàn bộ AssetCore role của 1 user (giữ role app khác như Frappe
    `System Manager`, `Norm Manager`, `Internal Auditor` ...).

    Args:
        user: User name (email).
        roles: list role-name (chỉ role nằm trong Roles.ALL được áp).

    Gate: capability `data.admin`.
    """
    from assetcore.services.shared import rbac
    rbac.require("data.admin")

    if not frappe.db.exists("User", user):
        return _err(f"User '{user}' không tồn tại", 404)

    # Role bị khoá khi user có Role Profile — chặn sửa thủ công (Core Doc §7.quater).
    lock_err = _profile_lock_error(user)
    if lock_err:
        return lock_err

    raw = _parse_json(roles) if isinstance(roles, str) else (roles or [])
    target = _extract_imm_role_names(raw)
    allowed = set(_IMM_ROLES)

    doc = frappe.get_doc("User", user)
    # Giữ mọi role không thuộc AssetCore (Frappe core, app khác)
    keep = [r.role for r in doc.roles if r.role not in allowed]
    # Base role bắt buộc — luôn giữ dù payload không gồm (không gỡ qua UI).
    final = sorted(set(keep + target + [BASE_ROLE]))

    doc.set("roles", [])
    for r in final:
        doc.append("roles", {"role": r})
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()

    return _ok({"user": user, "roles": final})


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


# Allowlist "ngữ cảnh phân công" → (DocType, ptype) để kiểm capability.
# Chống probe quyền tùy ý: endpoint CHỈ nhận context có tên, KHÔNG nhận doctype thô.
# Mở rộng khi thêm field phân công mới (PM, Calibration…). "repair" = KTV nhận
# lệnh sửa chữa (mirror services/imm09._is_repair_capable, BR-09-DISPATCH).
# Context "any AssetCore user" — KHÔNG lọc năng lực, chỉ cần base role (field mô
# tả người: giám sát, thủ kho, người nhận, trưởng khoa, leo thang SLA…).
_ANY_USER_CONTEXT = "user"

_ASSIGNABLE_CONTEXTS: dict[str, tuple[str, str]] = {
    "repair": ("Asset Repair", "write"),   # KTV nhận lệnh sửa chữa (IMM-09)
    "pm": ("PM Work Order", "write"),      # KTV nhận lệnh bảo trì định kỳ (IMM-08)
    "calibration": ("IMM Asset Calibration", "write"),   # KTV hiệu chuẩn (IMM-11)
    "incident": ("Incident Report", "write"),            # người xử lý sự cố (IMM-12)
    "commissioning": ("Asset Commissioning", "write"),   # KTV lắp đặt/nghiệm thu (IMM-04)
}


@frappe.whitelist()
def list_assignable_users(context: str, search: str = "", limit: int = 20) -> dict:
    """User AssetCore (có base role) ĐỦ NĂNG LỰC cho 1 ngữ cảnh phân công.

    Nguồn user = base-role holder (= "user AssetCore"), enabled, System User —
    KHÔNG lấy toàn bộ Frappe user. "Đủ năng lực" = capability/DocPerm
    (`frappe.has_permission(doctype, ptype, user=u)`), KHÔNG so role-name
    (LL-BE-49; mirror `_is_repair_capable`) → picker khớp đúng gate BE khi submit,
    user không chọn nhầm người rồi bị từ chối.

    Context "user" = BẤT KỲ user AssetCore (chỉ cần base role, KHÔNG lọc năng lực)
    — dùng cho field mô tả người (giám sát, thủ kho, leo thang SLA…).

    Args:
        context: "user" (mọi user AssetCore) HOẶC khoá `_ASSIGNABLE_CONTEXTS` (vd "repair").
        search:  lọc theo full_name / email.
        limit:   trần kết quả (cap 100).
    """
    if context != _ANY_USER_CONTEXT and context not in _ASSIGNABLE_CONTEXTS:
        return _err(f"Ngữ cảnh phân công không hợp lệ: {context}", 400)
    limit = max(1, min(int(limit), 100))

    # Candidate = base-role holder (user AssetCore), enabled, System User, khớp search.
    base_holders = set(_users_with_role(BASE_ROLE)) - {"Administrator", "Guest"}
    if not base_holders:
        return _ok([])

    or_filters = None
    if search:
        or_filters = [
            ["full_name", "like", f"%{search}%"],
            ["email", "like", f"%{search}%"],
        ]
    candidates = frappe.get_all(
        "User",
        filters={"name": ["in", sorted(base_holders)], "enabled": 1,
                 "user_type": "System User"},
        or_filters=or_filters,
        fields=["name", "full_name", "email", "user_image"],
        order_by="full_name asc",
    )

    # Context "user": mọi user AssetCore (không lọc năng lực). Context khác: lọc
    # theo năng lực (capability/DocPerm) — mirror _is_repair_capable. Candidate đã
    # bị giới hạn ở base-holder (+search) nên vòng has_permission có chặn trên.
    if context == _ANY_USER_CONTEXT:
        capable = candidates
    else:
        doctype, ptype = _ASSIGNABLE_CONTEXTS[context]
        capable = [
            u for u in candidates
            if frappe.has_permission(doctype, ptype, user=u["name"])
        ]
    return _ok(capable[:limit])
