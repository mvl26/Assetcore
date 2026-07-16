# Copyright (c) 2025, miyano and contributors
# License: MIT
"""``before_request`` guard — ánh xạ phiên mobile HẾT HẠN/không hợp lệ → HTTP **401**.

BỐI CẢNH (mobile B1 dead-end)
    Client mobile giữ cookie phiên ``sid`` trong SecureStore; interceptor axios CHỈ
    logout + điều hướng về màn Login khi HTTP **401**. Nhưng khi ``sid`` hết hạn/không
    hợp lệ, Frappe hạ user xuống ``"Guest"`` (đặt cờ ``frappe.response["session_expired"]``
    trong ``Session.get_session_record``) rồi ``is_whitelisted()`` ở dispatcher NÉM
    ``frappe.PermissionError`` → HTTP **403** cho MỌI method whitelisted KHÔNG
    ``allow_guest``. HTTP-403 này KHÔNG phân biệt được với "user còn phiên nhưng thiếu
    quyền/role" → mobile không thể logout an toàn ⇒ dead-end.

FIX (hẹp — chỉ sửa code app ``assetcore``, KHÔNG đụng frappe core)
    Ép **401** CHỈ khi HỘI ĐỦ 3 điều kiện:
      1. path = ``/api/method/assetcore.api.*`` (bề mặt API app này, mobile tiêu thụ),
      2. caller là ``Guest`` DO cookie phiên bị từ chối — cờ ``session_expired`` đã bật
         (KHÔNG phải guest thật không cookie),
      3. method KHÔNG ``allow_guest`` (không đụng login / probe phiên ở trang Login).

    → ``raise frappe.SessionExpired`` (``http_status_code = 401``). Body vẫn giữ
    ``session_expired: 1`` + thêm ``exc_type: "SessionExpired"`` (tín hiệu phụ cho client).

KHÔNG đụng (giữ nguyên hành vi cũ):
    - User CÒN phiên nhưng thiếu quyền/role (``frappe.session.user != "Guest"``) → vẫn 403.
    - Guest THẬT không gửi cookie (không có cờ ``session_expired``) → luồng dispatcher cũ.
    - Endpoint ``allow_guest`` (``assetcore.api.auth.*`` login, ``assetcore.api.layout.*``
      probe phiên) kể cả khi kèm cookie ``sid`` cũ → luồng cũ, không bị 401.
"""

from __future__ import annotations

import frappe
from frappe import _

#: Tiền tố path RPC của app assetcore (mobile + web đều tiêu thụ qua ``/api/method/``).
_ASSETCORE_API_PREFIX = "/api/method/assetcore.api."
_METHOD_PATH_PREFIX = "/api/method/"


def enforce_authenticated_session() -> None:
    """Hook ``before_request`` — xem docstring module.

    Chạy trong ``frappe.app.init_request`` SAU khi ``HTTPRequest``/``LoginManager`` đã
    resume phiên (nên ``frappe.session.user`` + cờ ``session_expired`` đã sẵn sàng) và
    TRƯỚC khi dispatcher gọi ``is_whitelisted`` — điểm chèn đúng để nâng 403→401.
    """
    request = getattr(frappe.local, "request", None)
    if request is None or request.method == "OPTIONS":
        return

    path = request.path or ""
    if not path.startswith(_ASSETCORE_API_PREFIX):
        return

    # (2) chỉ xử lý Guest DO cookie phiên bị từ chối (hết hạn/không hợp lệ),
    # KHÔNG đụng user còn phiên (thiếu quyền → vẫn 403) và guest thật không cookie.
    if frappe.session.user != "Guest":
        return
    if not frappe.local.response.get("session_expired"):
        return

    # (3) không ép 401 với method cho phép guest (login / kiểm tra phiên ở trang Login).
    method_path = path[len(_METHOD_PATH_PREFIX):]
    if _method_allows_guest(method_path):
        return

    raise frappe.SessionExpired(_("Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại."))


def _method_allows_guest(method_path: str) -> bool:
    """``True`` nếu ``method_path`` (dotted) đăng ký ``@frappe.whitelist(allow_guest=True)``.

    KHÔNG resolve được (method lạ/không tồn tại) → trả ``True`` một cách THẬN TRỌNG để
    KHÔNG ép 401 — nhường cho dispatcher xử theo luồng gốc (404/permission/…).
    """
    try:
        fn = frappe.get_attr(method_path)
    except Exception:
        return True
    return fn in frappe.guest_methods
