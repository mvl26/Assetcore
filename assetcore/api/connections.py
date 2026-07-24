# Copyright (c) 2026, AssetCore Team
"""Bản ghi liên quan (connections) — endpoint CHUNG cho mọi doctype.

Đọc CÙNG một nguồn với tab Connections của Desk: ``Meta.get_dashboard_data()`` →
``<doctype>_dashboard.py::get_data()``. Nhờ vậy Desk và Vue không bao giờ lệch nhau, và
thêm một liên kết mới chỉ phải sửa DUY NHẤT file dashboard (SPEC §3 P1).

Vì sao không để FE tự khai: trước đây mỗi màn chi tiết phải tự gọi API riêng để lấy bản
ghi liên quan ⇒ 33 màn = 33 chỗ khai trùng, lệch nhau theo thời gian. Endpoint này nhận
``doctype`` bất kỳ nên FE chỉ cần MỘT component dùng lại.

PHÂN QUYỀN (không có ``ignore_permissions`` ở bất kỳ đâu trong file này):
  1. Người gọi phải có quyền đọc CHÍNH bản ghi gốc — nếu không: 403.
  2. Doctype liên quan mà người gọi không có DocPerm read ⇒ **bỏ khỏi kết quả**, không
     trả về nhóm rỗng gây tò mò (mirror ``filter_permissions`` của Desk).
  3. Đếm chạy dưới ``frappe.session.user`` qua ``frappe.get_list`` ⇒ áp CÙNG
     ``permission_query_conditions`` như khi người dùng bấm vào drill list. Bất biến
     "count == số dòng drill thấy" (ADR-IMM00-LIST-SCOPE §4b) — KHÔNG dùng
     ``frappe.db.count`` vì hàm đó BỎ QUA row-scope ⇒ rò rỉ tổng số toàn viện.

Đếm bị CHẶN TRẦN ở ``CONNECTION_COUNT_CAP``: panel chỉ cần con số để người dùng biết có
hay không, không đáng để quét bảng lớn. Vượt trần trả ``capped=True`` để FE hiện "99+"
thay vì bịa một con số sai.
"""
from __future__ import annotations

import frappe
from frappe import _

from assetcore.utils.response import ErrorCode, _err, _ok

#: Trần đếm mỗi ô liên kết. Đủ để phân biệt "không có" / "có ít" / "nhiều".
CONNECTION_COUNT_CAP = 100


def _dashboard_data(doctype: str) -> dict:
    """Đồ thị liên kết đã khai của doctype ({} nếu chưa khai).

    ``Meta.get_dashboard_data`` đã gộp sẵn: module ``*_dashboard.py``, child table
    ``links`` của DocType, và hook ``override_doctype_dashboards`` của app khác.
    """
    try:
        return dict(frappe.get_meta(doctype).get_dashboard_data() or {})
    except Exception:
        frappe.log_error(
            title="connections: không đọc được dashboard data", message=frappe.get_traceback()
        )
        return {}


def _count_scoped(doctype: str, filters: dict) -> tuple[int, bool]:
    """(số bản ghi người dùng THẬT SỰ thấy, đã chạm trần?).

    Chạy dưới session user, KHÔNG ``ignore_permissions``. Thiếu DocPerm read hoặc bị
    row-scope chặn hết ⇒ 0 (đúng: drill cũng ra 0 dòng).
    """
    try:
        rows = frappe.get_list(
            doctype,
            filters=filters,
            fields=["name"],
            limit_page_length=CONNECTION_COUNT_CAP + 1,
            ignore_ifnull=True,
        )
    except frappe.PermissionError:
        return 0, False
    except Exception:
        return 0, False
    if len(rows) > CONNECTION_COUNT_CAP:
        return CONNECTION_COUNT_CAP, True
    return len(rows), False


def _internal_link_names(doc, link) -> list[str]:
    """Tên bản ghi mà CHÍNH doc này trỏ tới (``internal_links``).

    Hai dạng Frappe hỗ trợ (frappe/desk/notifications.py::get_internal_links):
      - ``str``  → tên Link field trên doc;
      - ``list`` → ``[table_fieldname, link_fieldname]``, gom qua child table.
    """
    names: list[str] = []
    if isinstance(link, str):
        value = doc.get(link)
        if value:
            names.append(value)
    elif isinstance(link, (list, tuple)) and len(link) == 2:
        table_fieldname, link_fieldname = link
        for row in doc.get(table_fieldname) or []:
            value = row.get(link_fieldname)
            if value and value not in names:
                names.append(value)
    return names


@frappe.whitelist()
def get_connections(doctype: str, name: str) -> dict:
    """GET /api/method/assetcore.api.connections.get_connections — bản ghi liên quan.

    Args:
        doctype: DocType của bản ghi gốc (vd ``AC Asset``).
        name: Mã bản ghi gốc (vd ``AC-ASSET-2026-00001``).

    Returns:
        Envelope ``_ok`` với ``groups`` = danh sách nhóm đã khai trong dashboard, mỗi ô
        gồm ``doctype``/``label``/``count``/``capped``/``filters`` (để FE tự dựng link
        drill). Doctype chưa khai đồ thị ⇒ ``groups: []`` (KHÔNG lỗi) — màn chi tiết
        vẫn hiển thị bình thường, chỉ là chưa có gì để nối.
    """
    doctype = (doctype or "").strip()
    name = (name or "").strip()
    if not doctype or not name:
        return _err(_("Thiếu doctype hoặc mã bản ghi."), code=ErrorCode.VALIDATION_ERROR)

    if not frappe.db.exists("DocType", doctype):
        return _err(_("Loại bản ghi không tồn tại: {0}").format(doctype), code=ErrorCode.NOT_FOUND)

    if not frappe.db.exists(doctype, name):
        return _err(_("Không tìm thấy bản ghi {0}.").format(name), code=ErrorCode.NOT_FOUND)

    if not frappe.has_permission(doctype, ptype="read", doc=name):
        return _err(
            _("Bạn không có quyền xem bản ghi này."), code=ErrorCode.FORBIDDEN
        )

    data = _dashboard_data(doctype)
    transactions = data.get("transactions") or []
    if not transactions:
        return _ok({"doctype": doctype, "name": name, "groups": [], "total": 0})

    default_fieldname = data.get("fieldname")
    non_standard = data.get("non_standard_fieldnames") or {}
    internal = data.get("internal_links") or {}

    doc = frappe.get_doc(doctype, name) if internal else None

    groups: list[dict] = []
    total = 0
    for group in transactions:
        items: list[dict] = []
        for linked_dt in group.get("items") or []:
            if not frappe.has_permission(linked_dt, ptype="read"):
                continue  # ẩn hẳn — không bộc lộ sự tồn tại của dữ liệu ngoài quyền

            link = internal.get(linked_dt)
            if link is not None:
                names = _internal_link_names(doc, link)
                if not names:
                    continue
                filters = {"name": ["in", names]}
            else:
                fieldname = non_standard.get(linked_dt, default_fieldname)
                if not fieldname:
                    continue  # không phân giải được ⇒ bỏ, thay vì đếm sai
                filters = {fieldname: name}

            count, capped = _count_scoped(linked_dt, filters)
            total += count
            items.append({
                "doctype": linked_dt,
                "label": _(linked_dt),
                "count": count,
                "capped": capped,
                "filters": filters,
            })

        if items:
            groups.append({"label": group.get("label") or "", "items": items})

    return _ok({"doctype": doctype, "name": name, "groups": groups, "total": total})
