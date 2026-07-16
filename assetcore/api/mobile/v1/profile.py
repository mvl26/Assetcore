# Copyright (c) 2026, AssetCore Team and contributors
"""Mobile account/profile API — thin `mobile.v1` wrappers cho màn "Tài khoản".

Hợp đồng OpenAPI (SSoT codegen mobile — mobile parity-curate theo response THẬT)
------------------------------------------------------------------------------
  - ``GET  /api/method/assetcore.api.mobile.v1.get_my_profile``     → operationId ``getMyProfile``
  - ``POST /api/method/assetcore.api.mobile.v1.update_my_profile``  → operationId ``updateMyProfile``
  - ``POST /api/method/assetcore.api.mobile.v1.change_my_password`` → operationId ``changeMyPassword``

**function-name == operationId FROZEN** (đồng luật device_token): đổi tên = vỡ hợp đồng codegen.

Ranh giới (Feature Spec 16-tai-khoan-ho-so §8 · HANDOFF-account-profile · CLAUDE.md §15)
----------------------------------------------------------------------------------------
- **THIN wrapper — DELEGATE, KHÔNG reimplement business rule:**
  - ``get_my_profile``     → tái dùng ``auth.get_user_profile`` (gom field phone/khoa/vai-trò)
    rồi **project GỌN** ``MyProfile`` (LOẠI web-only ``permissions``/``hr_docname``/
    ``imm_approval_status``/``designation``/``user_image``/khối ``profile`` lồng).
  - ``update_my_profile``  → delegate ``auth.update_my_profile`` (allowlist ``_SELF_EDITABLE=
    {full_name, phone}``; khoa/phòng READ-ONLY) rồi trả LẠI ``MyProfile`` ĐẦY ĐỦ (Q-C).
  - ``change_my_password`` → delegate ``user.change_my_password`` (verify cũ / len≥8 / chặn
    old==new / update_password). Wrapper chỉ MAP kết quả → ``{reauth_required}`` + fielded error.
- **Chống spoof (§6.2):** user ÉP ``frappe.session.user`` — signature KHÔNG nhận ``user``;
  ``**_ignore`` nuốt kwargs lạ; ``update`` đọc allowlist qua delegate ⇒ ``department``/``roles``
  client gửi bị drop. KHÔNG sửa hồ sơ / mật khẩu người khác.
- **Envelope Decision-B (route-by-VALUE ``body.success``):** lỗi nghiệp vụ → HTTP-200 +
  ``{success:false, code, http_status, fields}`` (``_err`` KHÔNG động status-line). Mobile route
  theo KEY trong ``fields`` (``old_password``/``new_password``/``full_name``/``phone``).
- **Error-code:** enum ``ErrorCode`` KHÔNG có ``INVALID_PASSWORD``/``WEAK_PASSWORD`` → dùng
  ``VALIDATION`` (422) + ``fields`` cho MỌI lỗi password/hồ-sơ (BA CHỐT §8c).
- **reauth_required (Q-A) = False:** delegate gọi ``update_password(user, pwd)`` với
  ``logout_all_sessions`` mặc-định False (frappe/utils/password.py:117,150) ⇒ cookie ``sid``
  HIỆN TẠI KHÔNG bị vô hiệu ⇒ mobile GIỮ phiên, KHÔNG ép re-login.
- **Bảo mật:** KHÔNG log/echo/persist ``old/new_password`` ở bất kỳ tầng nào.

Param typing (LL-BE-1)
----------------------
Param string khai ``str = ""`` (KHÔNG ``None``) để form/GET param rỗng KHÔNG trip
``validate_argument_types`` → HTTP 417.
"""
from __future__ import annotations

import frappe

from assetcore.api import auth as _auth
from assetcore.api import user as _user
from assetcore.services.shared.constants import ROLE_METADATA
from assetcore.utils.response import ErrorCode, _err, _ok

_MSG_NOT_LOGGED_IN = "Chưa đăng nhập"
_MIN_PASSWORD_LENGTH = 8  # canonical mobile.v1 (Q-B) — khớp guard user.change_my_password:754

# Thông điệp tiếng Việt authoritative cho 3 nhánh lỗi đổi mật khẩu (§8c).
_MSG_WRONG_OLD = "Mật khẩu hiện tại không đúng"
_MSG_WEAK = "Mật khẩu mới phải có ít nhất 8 ký tự"
_MSG_SAME = "Mật khẩu mới phải khác mật khẩu cũ"


def _role_label(role: str) -> str:
    """Nhãn tiếng Việt của 1 role IMM — y hệt ``user.get_available_imm_roles`` (user.py:778).

    ``ROLE_METADATA[role].label`` nếu có, fallback bỏ tiền tố ``IMM `` (KHÔNG hard-code
    map ở mobile — backend build sẵn ``role_labels[]`` song song ``roles[]``).
    """
    return ROLE_METADATA.get(role, {}).get("label") or role.replace("IMM ", "")


def _build_my_profile(user_name: str) -> dict:
    """Project GESLIM ``MyProfile`` — DELEGATE field-gathering cho ``auth.get_user_profile``.

    ``auth.get_user_profile`` gom (session user) phone←User.phone, ac_department←User
    (Link), department_name←AC Department (fallback id), roles←IMM-prefixed. Ta unwrap web
    shape rồi CHỈ giữ 6 trường + ``role_labels`` — LOẠI mọi field web-only.
    """
    body = _auth.get_user_profile()  # envelope web-shape (session user, KHÔNG nhận param)
    data = body["data"]
    profile = data.get("profile") or {}
    roles = list(data.get("roles") or [])
    return {
        "full_name": data["user"]["full_name"],
        "email": data["user"]["email"],
        "phone": profile.get("phone"),
        "roles": roles,
        "role_labels": [_role_label(r) for r in roles],
        "department": profile.get("ac_department"),
        "department_name": profile.get("department_name"),
    }


@frappe.whitelist()
def get_my_profile() -> dict:
    """Đọc hồ sơ GESLIM của user ĐANG đăng nhập (operationId ``getMyProfile`` FROZEN).

    GET · user ÉP ``frappe.session.user`` (KHÔNG param). Trả ``_ok(MyProfile)``:
    ``{full_name, email, phone|null, roles[], role_labels[], department|null,
    department_name|null}`` — KHÔNG rò ``permissions``/``hr_docname``/``imm_approval_status``.
    Guest → ``_err(UNAUTHORIZED)`` (thực tế dispatcher chặn 403 trước khi vào handler).
    """
    user_name = frappe.session.user
    if user_name == "Guest":
        return _err(_MSG_NOT_LOGGED_IN, ErrorCode.UNAUTHORIZED)
    return _ok(_build_my_profile(user_name))


@frappe.whitelist(methods=["POST"])
def update_my_profile(full_name: str = "", phone: str = "", **_ignore) -> dict:
    """Cập nhật partial hồ sơ (operationId ``updateMyProfile`` FROZEN).

    POST · DELEGATE ``auth.update_my_profile`` — allowlist ``_SELF_EDITABLE={full_name,phone}``
    (khoa/phòng/roles READ-ONLY; kwargs lạ như ``department``/``user`` bị delegate drop ⇒ chống
    spoof). Q-C: thành công → trả LẠI ``MyProfile`` ĐẦY ĐỦ (re-project 8a) để mobile set-cache.
    Lỗi validate (vd doctype từ chối) → ``_err(VALIDATION, fields=...)`` HTTP-200 (KHÔNG lưu im lặng).

    Args:
        full_name: họ tên mới (tuỳ chọn — chỉ cập nhật nếu gửi).
        phone: số điện thoại mới (tuỳ chọn).
    """
    user_name = frappe.session.user
    if user_name == "Guest":
        return _err(_MSG_NOT_LOGGED_IN, ErrorCode.UNAUTHORIZED)

    try:
        result = _auth.update_my_profile()  # đọc form_dict, allowlist, save+commit
    except frappe.ValidationError as exc:
        # Doctype từ chối (vd định dạng) → surface message THẬT inline (BR-FIX-09 cấm im lặng).
        msg = str(exc) or "Không cập nhật được hồ sơ"
        return _err(msg, ErrorCode.VALIDATION, fields=_attribute_profile_error(msg))

    if result.get("success") is False:
        # Delegate error nghiệp vụ (vd "Không có trường nào được cập nhật") → chuẩn hoá VALIDATION.
        return _err(result.get("error") or "Không cập nhật được hồ sơ", ErrorCode.VALIDATION)

    return _ok(_build_my_profile(user_name))


def _attribute_profile_error(msg: str) -> dict | None:
    """Best-effort gán lỗi doctype về đúng ô nhập (chỉ full_name/phone self-editable).

    KHÔNG bịa field — nếu không nhận diện được thì trả None (mobile hiện banner). KHÔNG
    reimplement rule validate; chỉ định tuyến message THẬT của delegate về ô tương ứng.
    """
    low = msg.lower()
    if "phone" in low or "điện thoại" in low:
        return {"phone": msg}
    if "full name" in low or "họ tên" in low or "tên" in low:
        return {"full_name": msg}
    return None


@frappe.whitelist(methods=["POST"])
def change_my_password(old_password: str = "", new_password: str = "", **_ignore) -> dict:
    """Đổi mật khẩu tự phục vụ (operationId ``changeMyPassword`` FROZEN).

    POST · DELEGATE ``user.change_my_password`` (verify cũ qua ``check_password`` · len≥8 ·
    chặn old==new · ``update_password``). Wrapper CHỈ map kết quả:
      - thành công → ``_ok({reauth_required: False})`` (Q-A: sid hiện tại còn hợp lệ).
      - lỗi → ``_err(VALIDATION, fields={old_password|new_password: <msg VN>})`` (§8c).
        Định tuyến field theo THỨ TỰ check của delegate (len<8 → new; old==new → new; còn lại
        = sai mật khẩu cũ → old) — KHÔNG match chuỗi mỏng manh.

    Bảo mật: KHÔNG log/echo/persist old/new password.

    Args:
        old_password: mật khẩu hiện tại (verify).
        new_password: mật khẩu mới (≥8, khác cũ).
    """
    user_name = frappe.session.user
    if user_name == "Guest":
        return _err(_MSG_NOT_LOGGED_IN, ErrorCode.UNAUTHORIZED)

    result = _user.change_my_password(old_password, new_password)  # delegate = single decision-maker
    if result.get("success"):
        # Q-A: update_password(logout_all_sessions mặc-định False) KHÔNG xoá sid hiện tại.
        return _ok({"reauth_required": False})

    # Delegate từ chối → phân loại field cho lỗi inline (mirror thứ tự check user.py:754/756/762).
    if len(new_password or "") < _MIN_PASSWORD_LENGTH:
        return _err(_MSG_WEAK, ErrorCode.VALIDATION, fields={"new_password": _MSG_WEAK})
    if old_password == new_password:
        return _err(_MSG_SAME, ErrorCode.VALIDATION, fields={"new_password": _MSG_SAME})
    return _err(_MSG_WRONG_OLD, ErrorCode.VALIDATION, fields={"old_password": _MSG_WRONG_OLD})
