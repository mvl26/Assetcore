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
from assetcore.utils.helpers import _get_role_emails, _safe_sendmail, fe_url
from assetcore.utils.email_template import render_email
from assetcore.utils import password_policy
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


_dummy_pwhash_cache: str | None = None


def _constant_time_dummy_verify(pwd: str) -> None:
    """Verify `pwd` against a fixed dummy hash (cùng CryptContext của Frappe).

    Dùng cho nhánh user-không-tồn-tại để chi phí ~bằng một `check_password`
    thật → đóng timing-based user enumeration (security review #2). Hash dummy
    tính một lần rồi cache; verify luôn trả False nhưng vẫn tốn cost bcrypt.
    """
    global _dummy_pwhash_cache
    from frappe.utils.password import passlibctx

    try:
        if _dummy_pwhash_cache is None:
            _dummy_pwhash_cache = passlibctx.hash("ac-constant-time-dummy")
        passlibctx.verify(pwd or "", _dummy_pwhash_cache)
    except Exception:
        pass


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

    Người đăng ký lại PHẢI nhập đúng mật khẩu gốc (tham số `password`) để chứng
    minh quyền sở hữu — mật khẩu KHÔNG bị đổi ở đây (security review #3). Sai
    mật khẩu → trả nhãn 'đã tồn tại' (không lộ trạng thái Rejected).
    """
    status = (
        frappe.db.get_value("User", email, "imm_approval_status")
        if _safe_field("imm_approval_status") else None
    )
    enabled = int(frappe.db.get_value("User", email, "enabled") or 0)

    if status != "Rejected" or enabled == 1:
        return _err("Email đã tồn tại trong hệ thống", 400)

    # Bảo mật (security review #3): chỉ cho phép ghi đè hồ sơ Rejected khi người
    # gọi CHỨNG MINH biết mật khẩu gốc của tài khoản → chống chiếm danh tính qua
    # đường guest. Sai/thiếu mật khẩu → trả CÙNG nhãn 'email đã tồn tại' như mọi
    # trường hợp khác (không lộ ra đây là tài khoản Rejected).
    from frappe.utils.password import check_password

    try:
        check_password(email, password, delete_tracker_cache=False)
    except frappe.AuthenticationError:
        return _err("Email đã tồn tại trong hệ thống", 400)

    # Mật khẩu gốc đúng — KHÔNG đổi mật khẩu (giữ nguyên), chỉ cập nhật danh
    # tính + đưa về Pending + clear lý do từ chối.
    user_doc = frappe.get_doc("User", email)
    user_doc.first_name = full_name
    user_doc.phone = phone or ""
    user_doc.enabled = 0
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
@rate_limit(key="usr", limit=5, seconds=300, ip_based=True)
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

    # Email không tồn tại và sai mật khẩu PHẢI không phân biệt được — kể cả timing.
    if not frappe.db.exists("User", usr):
        _constant_time_dummy_verify(pwd)  # equalize cost với check_password thật
        return _ok({"status": "invalid_credentials"})

    try:
        # delete_tracker_cache=False: oracle này KHÔNG được xoá bộ đếm
        # login-fail thật của Frappe (LoginAttemptTracker) — tránh bypass lockout.
        check_password(usr, pwd, delete_tracker_cache=False)
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


# ─────────────────────────────────────────────────────────────────────────────
# ISS-002 — TỰ ĐẶT MẬT KHẨU QUA LINK TRONG EMAIL (màn hình của AssetCore)
#
# Người dùng mới nhận email chào mừng → bấm "Đặt mật khẩu" → mở
# ``/assetcore/set-password?key=...`` (UI AssetCore, KHÔNG phải form
# ``/update-password`` của Frappe desk). Hai endpoint dưới phục vụ màn hình đó;
# cả hai đều allow_guest vì user CHƯA có mật khẩu để đăng nhập.
# ─────────────────────────────────────────────────────────────────────────────

_MSG_KEY_INVALID = (
    "Liên kết đặt mật khẩu không hợp lệ hoặc đã được sử dụng. "
    "Vui lòng liên hệ quản trị viên để được cấp lại."
)
_MSG_KEY_EXPIRED = (
    "Liên kết đặt mật khẩu đã hết hạn. "
    "Vui lòng liên hệ quản trị viên để được cấp lại liên kết mới."
)
_MSG_ACCOUNT_DISABLED = (
    "Tài khoản chưa được kích hoạt hoặc đã bị vô hiệu hoá. "
    "Vui lòng liên hệ quản trị viên."
)
_MIN_PASSWORD_LEN = 8


def _resolve_password_key(key: str) -> tuple[str | None, dict | None]:
    """Đổi key thô trong link lấy tên user — hoặc trả envelope lỗi.

    Cùng ngữ nghĩa với Frappe (``_get_user_for_update_password``): key lưu trên
    User dưới dạng sha256, hết hạn theo System Settings
    ``reset_password_link_expiry_duration``.

    Bảo mật: key sai / đã dùng / không tồn tại đều trả CÙNG một thông điệp
    (không phân biệt được tài khoản nào tồn tại → không enumeration).

    Returns:
        ``(user_name, None)`` khi hợp lệ; ``(None, _err(...))`` khi không.
    """
    from datetime import timedelta

    from frappe.utils import cint, now_datetime
    from frappe.utils.data import sha256_hash

    key = (key or "").strip()
    if not key:
        return None, _err(_MSG_KEY_INVALID, 400, extra={"reason": "invalid"})

    row = frappe.db.get_value(
        "User",
        {"reset_password_key": sha256_hash(key)},
        ["name", "enabled", "full_name", "last_reset_password_key_generated_on"],
        as_dict=True,
    )
    if not row:
        return None, _err(_MSG_KEY_INVALID, 400, extra={"reason": "invalid"})

    expiry = cint(
        frappe.db.get_single_value("System Settings", "reset_password_link_expiry_duration")
    )
    generated_on = row.get("last_reset_password_key_generated_on")
    if expiry and generated_on and now_datetime() > generated_on + timedelta(seconds=expiry):
        return None, _err(_MSG_KEY_EXPIRED, 400, extra={"reason": "expired"})

    if not cint(row.get("enabled")):
        return None, _err(_MSG_ACCOUNT_DISABLED, 403, extra={"reason": "disabled"})

    return row["name"], None


def _validate_new_password(password: str, user_name: str) -> dict | None:
    """Kiểm tra độ mạnh mật khẩu; trả ``None`` nếu đạt, envelope lỗi nếu không.

    Tôn trọng chính sách của site (System Settings ``enable_password_policy`` +
    ``minimum_password_score``) — nếu tắt policy thì chỉ còn ràng buộc độ dài.
    """
    if len(password or "") < _MIN_PASSWORD_LEN:
        return _err(
            f"Mật khẩu phải có tối thiểu {_MIN_PASSWORD_LEN} ký tự",
            400,
            fields={"new_password": f"Tối thiểu {_MIN_PASSWORD_LEN} ký tự"},
        )

    # Trước đây hàm này nối THẲNG `feedback["suggestions"]` của zxcvbn vào thông
    # điệp → lọt tiếng Anh ("All-uppercase is almost as easy to guess…").
    # `password_policy` dịch trọn tập chuỗi đóng của Frappe sang tiếng Việt.
    weak = password_policy.check_password(password, user_name)
    if weak:
        return _err(weak, 400, fields={"new_password": weak})
    return None


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="key", limit=10, seconds=60, ip_based=True)
def verify_password_key(key: str) -> dict:
    """Kiểm tra link đặt mật khẩu còn hiệu lực (màn hình AssetCore gọi khi mở).

    Cho phép UI hiển thị "Xin chào <tên>" + tên đăng nhập trước khi user nhập,
    và báo lỗi rõ ràng (hết hạn / đã dùng) thay vì để user điền xong mới biết.
    Chỉ người cầm key (chủ hộp thư) mới nhận được danh tính này.
    """
    user_name, err = _resolve_password_key(key)
    if err:
        return err
    return _ok({
        "user": user_name,
        "full_name": frappe.db.get_value("User", user_name, "full_name") or user_name,
        "login_url": fe_url("/login"),
    })


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="key", limit=5, seconds=60, ip_based=True)
def set_password_with_key(key: str, new_password: str) -> dict:
    """Đặt mật khẩu lần đầu bằng key trong email chào mừng.

    Key dùng MỘT LẦN: đặt xong là xoá khỏi User → link cũ vô hiệu (chống replay
    khi email bị chuyển tiếp/lộ về sau). Mật khẩu không đạt policy KHÔNG tiêu
    key để user còn thử lại được.
    """
    from frappe.utils.password import update_password

    user_name, err = _resolve_password_key(key)
    if err:
        return err

    invalid = _validate_new_password(new_password, user_name)
    if invalid:
        return invalid

    update_password(user_name, new_password)
    frappe.db.set_value(
        "User",
        user_name,
        {"reset_password_key": "", "last_reset_password_key_generated_on": None},
        update_modified=False,
    )
    frappe.db.commit()
    frappe.logger("assetcore.auth").info(
        {"event": "set_password_with_key", "user": user_name}
    )
    return _ok({
        "user": user_name,
        "login_url": fe_url("/login"),
        "message": "Đặt mật khẩu thành công. Bạn có thể đăng nhập ngay.",
    })


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
        message=render_email(
            title="Có người dùng mới chờ duyệt",
            body_html=(
                f"<p>Người dùng mới vừa đăng ký tài khoản:</p>"
                f"<p><b>Email:</b> {frappe.utils.escape_html(email)}<br />"
                f"<b>Họ tên:</b> {frappe.utils.escape_html(full_name)}<br />"
                f"<b>Khoa/Phòng:</b> "
                f"{frappe.utils.escape_html(department) or '(chưa chọn)'}</p>"
                f"<p>Vào <b>Quản lý Người dùng IMM</b> để duyệt tài khoản.</p>"
            ),
            cta_label="Mở màn hình duyệt người dùng",
            cta_url=fe_url("/user-profiles"),
        ),
    )
