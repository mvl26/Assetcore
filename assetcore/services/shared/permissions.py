# Copyright (c) 2026, AssetCore Team
"""Permission helpers — tập trung role checks."""

from collections.abc import Iterable

import frappe

from .constants import Roles
from .errors import forbidden
from . import rbac


def has_any_role(roles: Iterable[str]) -> bool:
    """True nếu user hiện tại có ít nhất 1 role trong `roles`."""
    return bool(set(frappe.get_roles()) & set(roles))


def has_role(role: str) -> bool:
    return role in set(frappe.get_roles())


def require_role(roles: Iterable[str], message: str = "Không đủ quyền thực hiện") -> None:
    """Raise ServiceError(FORBIDDEN) nếu user không có role phù hợp."""
    if not has_any_role(roles):
        raise forbidden(message)


def is_admin() -> bool:
    return has_role(Roles.SUPER_ADMIN)


def require_admin() -> None:
    require_role((Roles.SUPER_ADMIN,), "Yêu cầu quyền Super Admin")


def require_user_mgmt() -> None:
    if not rbac.can("data.admin"):
        raise forbidden("Không đủ quyền quản lý người dùng")


def assert_doctype_read_permission(doctype: str) -> None:
    """Gate DocPerm read **CẤP VAI TRÒ** — dùng cho nhánh bỏ row-scope.

    Vì sao tồn tại (finding CRITICAL/HIGH 2026-07-25 — OWASP A01 Broken Access
    Control): ``scope="system"`` (``frappe.get_all``) bỏ qua **HAI** thứ khác nhau
    về bản chất, trong khi ADR-IMM00-LIST-SCOPE §8.2 D6 chỉ ratify nới **một**:

    ============================ =============================== ==================
    Trục                          Nghĩa                            D6 ratify?
    ============================ =============================== ==================
    ROW-scope                     ``permission_query_conditions``  ✔ CÓ (device /
    (ai-được-giao)                + User Permission                  plan-centric)
    ROLE-scope                    DocPerm ``read`` trên DocType    ✘ KHÔNG
    (vai-trò-nào-được-đọc)        (`Has Role` → `DocPerm`)
    ============================ =============================== ==================

    Hệ quả khi thiếu gate: user CHỈ có role ``PM User`` (0 DocPerm read trên
    ``Asset Repair``) gọi ``get_asset_repair_history`` vẫn nhận full bản ghi
    ``WO-CM-*`` (repair_type / mttr_hours / root_cause_category). Trước khi
    tham-số-hoá ``scope``, mọi call site chạy ``frappe.get_list`` một lần cho
    ``total`` nên DocPerm được enforce như **tác dụng phụ** — tham-số-hoá đã gỡ
    mất tác dụng phụ đó mà không thay bằng gate tường minh.

    Predicate mirror **byte-for-byte** ``DatabaseQuery._set_permission_map``
    (`frappe/model/db_query.py:577-583`, v15): cùng ``ptype`` (`select` khi user
    chỉ có select-perm, ngược lại `read`) ⇒ gate KHÔNG chặt hơn cũng KHÔNG lỏng
    hơn nhánh ``scope="user"``; khác biệt duy nhất còn lại đúng bằng row-scope.

    Raise ``frappe.PermissionError`` (KHÔNG ``frappe.throw``) để:
      * đồng nhất một loại exception với nhánh ``scope="user"`` ⇒ :func:`run_rowscoped`
        bọc được cả hai bằng CÙNG một ``except``;
      * KHÔNG đẩy tên DocType vào ``_server_messages`` (``frappe.throw`` sẽ msgprint
        ⇒ leak nội bộ ra client).

    Raises:
        frappe.PermissionError: session-user không có DocPerm read/select trên ``doctype``.
    """
    ptype = "select" if frappe.only_has_select_perm(doctype) else "read"
    if not frappe.has_permission(doctype, ptype=ptype):
        # Message chỉ đi vào traceback/Error Log (server-side). Client nhận message
        # HẰNG qua run_rowscoped → MSG.AUTH_FORBIDDEN.
        raise frappe.PermissionError(
            f"Thiếu DocPerm {ptype!r} trên {doctype!r} (row-scope bypass vẫn giữ role-gate)"
        )


def assert_can_read_doc(doctype: str, doc) -> None:
    """Gate quyền-đọc **CẤP BẢN GHI** — ROLE ∧ ROW ∧ User Permission trong MỘT predicate.

    Vì sao tồn tại (CR-74 / ADR-IMM00-LIST-SCOPE §9.3 — IDOR-đọc trên 4 màn detail):
    ``BaseRepository.get`` = ``frappe.db.exists`` → ``frappe.get_doc``, mà
    ``frappe.get_doc`` (``frappe/model/document.py:36``) chỉ ``load_from_db`` — nó
    **KHÔNG** gọi ``Document.check_permission`` (``:227``). Hệ quả: hook
    ``has_permission`` đã đăng ký đầy đủ ở ``hooks.py:448-455``
    (``asset_repair_has_permission`` / ``pm_work_order_has_permission`` /
    ``incident_report_has_permission``) **chưa bao giờ chạy** trên đường đọc chi tiết
    ⇒ dán thẳng URL/`?name=` là đọc trọn hồ sơ phiếu của người khác, kể cả persona
    0 DocPerm read (OWASP A01).

    ``frappe.has_permission(doctype, ptype, doc=…)`` (``frappe/permissions.py:77-194``)
    là predicate HỢP NHẤT: nó chạy lần lượt
    (1) ``has_controller_permissions`` → dispatch hook AssetCore,
    (2) ``get_role_permissions`` → DocPerm cấp vai-trò,
    (3) ``has_user_permission`` → User Permission.
    ⟹ MỘT lời gọi phủ cả 3 trục, và dùng ĐÚNG predicate mà ``list``/write-gate đang
    dùng (D5/D8: một predicate cho list + count + detail + mutate).

    ⚠️ Hook **chỉ DENY, không GRANT** (docstring ``has_controller_permissions:443-446``)
    ⇒ persona senior/auditor giữ 200 là nhờ **DocPerm**, không phải nhờ hook. Đừng suy
    diễn "hook trả True ⇒ pass" khi viết test.

    DocType chưa có hook (vd ``IMM Asset Calibration``) ⇒ thang tự suy biến về
    DocPerm + User Permission, **CÙNG code path** (D10): mai này thêm hook là gate có
    hiệu lực ngay, không phải nhớ quay lại sửa.

    Args:
        doctype: tên DocType đích (verbatim — dùng hằng ``_DT_*`` của service).
        doc: Document ĐÃ load ở bước EXISTS ⇒ **0 query thêm** (KHÔNG load lần 2).

    Raises:
        frappe.PermissionError: session-user không được đọc CHÍNH bản ghi này.

    KHÔNG dùng ``doc.check_permission("read")``: nó đi qua ``frappe.throw`` ⇒ msgprint
    tên DocType + tên bản ghi vào ``_server_messages`` (rò existence + rò nội bộ) và
    biến 403 thành shape ``ValidationError``. Message dưới đây KHÔNG chứa ``doc.name``
    và chỉ đi vào traceback/Error Log; client nhận message HẰNG ``MSG.AUTH_FORBIDDEN``
    qua :func:`run_rowscoped`.
    """
    if not frappe.has_permission(doctype, ptype="read", doc=doc, user=frappe.session.user):
        raise frappe.PermissionError(
            f"Không đủ quyền đọc bản ghi thuộc {doctype!r} (row-scope/DocPerm read)"
        )


def run_rowscoped(fn, *args, **kwargs):
    """Chạy một list-service `scope="user"` và chuyển `PermissionError` → 403 envelope.

    BR-00-ROWSCOPE-403 (ADR-IMM00-LIST-SCOPE §8.5): ``frappe.get_list`` **raise
    ``frappe.PermissionError``** khi session-user KHÔNG có DocPerm ``read`` trên
    DocType. ``handle()`` cố ý KHÔNG bắt Exception chung ⇒ nếu để bubble, client
    nhận **HTTP-500 / trang lỗi Frappe** thay vì envelope — không phân biệt được
    với sự cố hệ thống.

    Chuyển thành ``ServiceError(FORBIDDEN, http_status=403)`` ⇒ ``handle()`` trả
    **HTTP-200 + Error envelope** (in-handler cap-403: user CÒN phiên, chỉ thiếu
    quyền ⇒ client hiển thị message, **KHÔNG logout**; khác dispatcher-403 của
    guest/hết token).

    TUYỆT ĐỐI KHÔNG trả list rỗng thay cho 403 — silent-empty che RBAC misconfig
    (anti-pattern "dead-gate": tính năng chết âm thầm, test giả vẫn xanh).
    """
    import frappe as _frappe

    from assetcore.utils.messages import MSG
    from assetcore.utils.notify import nthrow

    try:
        return fn(*args, **kwargs)
    except _frappe.PermissionError:
        # message HẰNG từ registry (MSG.AUTH_FORBIDDEN → "Không đủ quyền", 403 ⇒
        # bucket FORBIDDEN) — KHÔNG leak tên DocType/SQL/traceback ra client.
        nthrow(MSG.AUTH_FORBIDDEN)


def rowscoped(fn):
    """Decorator dạng khai-báo của :func:`run_rowscoped` — dán lên service entrypoint.

    Vì sao cần: bọc thủ công (`def f(): return run_rowscoped(_f, ...)`) buộc tách đôi
    mỗi hàm ⇒ thực tế chỉ 2/≈20 entrypoint được bọc, phần còn lại ném
    ``frappe.PermissionError`` TRẦN (client nhận dispatcher-403/500 thay vì Error
    envelope — FE hiểu nhầm là hết phiên và ĐĂNG XUẤT người dùng). Decorator giữ
    nguyên thân hàm ⇒ dán được cho MỌI entrypoint đọc-danh-sách trong 1 dòng.

    Dùng cho: service entrypoint **đọc** được gọi từ ``@frappe.whitelist`` (qua
    ``handle``). KHÔNG dùng cho scheduler/domain-logic nội bộ (ở đó dùng
    ``scope="internal"`` — không có client để hiển thị 403).
    """
    import functools

    @functools.wraps(fn)
    def _wrapped(*args, **kwargs):
        return run_rowscoped(fn, *args, **kwargs)

    _wrapped.__wrapped_rowscoped__ = True
    return _wrapped
