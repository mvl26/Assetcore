# Copyright (c) 2026, AssetCore Team
"""Bản ghi liên quan (connections) — endpoint CHUNG cho mọi doctype.

Vỏ mỏng: chuẩn hoá + clamp tham số → gác đầu vào (allowlist / tồn tại / quyền đọc) →
gọi ``services/connections.py`` → envelope ``_ok``/``_err``. Toàn bộ logic dựng cây
(đồ thị liên kết, preview, nhãn tiếng Việt, ``can_create``) nằm ở tầng service
(CLAUDE.md §15 — không viết logic trong controller). Hợp đồng đầy đủ:
``docs/imm-00/05_API_Specification.md §III.24`` · quyết định:
``docs/imm-00/ADR-IMM00-CONNECTIONS-TREE.md``.

Vì sao không để FE tự khai: trước đây mỗi màn chi tiết phải tự gọi API riêng để lấy bản
ghi liên quan ⇒ 33 màn = 33 chỗ khai trùng, lệch nhau theo thời gian. Endpoint này nhận
``doctype`` bất kỳ (trong allowlist) nên FE chỉ cần MỘT component dùng lại.

PHÂN QUYỀN (không có ``ignore_permissions`` ở bất kỳ đâu trong họ file này):
  1. Người gọi phải có quyền đọc CHÍNH bản ghi gốc — nếu không: 403.
  2. Doctype liên quan mà người gọi không có DocPerm read ⇒ **bỏ khỏi kết quả** (tầng
     service), không trả nhóm rỗng gây tò mò.
  3. Đếm/preview chạy dưới ``frappe.session.user`` qua ``frappe.get_list`` ⇒ áp CÙNG
     ``permission_query_conditions`` như khi người dùng bấm drill. Bất biến "count ==
     số dòng drill thấy" (ADR-IMM00-LIST-SCOPE §4b) — KHÔNG dùng ``frappe.db.count``
     vì hàm đó BỎ QUA row-scope ⇒ rò rỉ tổng số toàn viện.

⚠️ **RATIFY — vì sao lời gọi ORM (``_row_scoped_rows``) ở tầng API là NGOẠI LỆ CÓ TÊN,
không phải nợ kỹ thuật** (AC-CR-92 · ``ADR-IMM00-CONNECTIONS-TREE.md §17 D-CR92-6`` ·
``docs/imm-00/04_Backend_Design.md §V.7.1`` mục NGOẠI LỆ "cổng I/O"): ``_row_scoped_rows``
là **cổng I/O DUY NHẤT** của endpoint — một adapter không chứa quyết định nghiệp vụ nào
("đọc ≤ CAP+1 dòng dưới session user, hỏng thì trả ``[]``") — và được TIÊM vào service
qua tham số ``list_fn``. Nhờ vậy tầng service THUẦN (0 lời gọi đọc-theo-tập) và ZERO-COST
trở nên **đo được**: test đếm số lời gọi ``list_fn`` để chứng minh 1 truy vấn/ô + 0 COUNT.

Ngoại lệ chỉ có hiệu lực khi ĐỦ 2 điều kiện, **cả hai đo bằng test** (docstring không đỏ
được nên nó không đủ tư cách làm ngoại lệ kiến trúc):
  (a) ``tests/test_connections_tree.py::test_t27_service_layer_has_zero_row_reading_orm``
      — ``services/connections.py`` có **0** lời gọi ``frappe.get_list``/``get_all``/
      ``db.get_all``/``db.get_list``/``db.count``/``db.sql``;
  (b) ``tests/test_connections_tree.py::test_t28_api_layer_has_exactly_one_get_list_inside_the_port``
      — file này có ``frappe.get_list`` **đúng 1 lần**, nằm **trong thân** cổng.

Đây cũng là điều kiện để guard AST của ``tests/test_connections.py::
test_counts_run_under_session_user_not_administrator`` (hợp đồng cũ — giữ **0 dòng sửa**
qua AC-CR-92) tiếp tục soi đúng file mà nó soi từ đầu.
"""
from __future__ import annotations

import frappe
from frappe import _

from assetcore.services import connections as service
from assetcore.services.connections import CONNECTION_COUNT_CAP, PREVIEW_ORDER_BY
from assetcore.services.shared.connection_meta import clamp_preview_limit
from assetcore.utils.response import ErrorCode, _err, _ok

__all__ = ["get_connections", "CONNECTION_COUNT_CAP"]


def _row_scoped_rows(doctype: str, filters: dict, fields: list[str]) -> list[dict]:
    """MỘT truy vấn duy nhất cho một ô: vừa là nguồn preview, vừa là nguồn đếm.

    Trần ``CAP + 1`` để phân biệt "đúng 100" với "hơn 100" mà **không** cần truy vấn
    COUNT thứ hai — hai truy vấn khác nhau là hai cơ hội độc lập để nói dối (khuôn sinh
    bug production *"Tổng 1430 / bảng RỖNG"*).

    Chạy dưới ``frappe.session.user``: thiếu DocPerm read hoặc bị row-scope chặn hết ⇒
    ``[]`` (đúng: drill cũng ra 0 dòng). Doctype hỏng/không truy vấn được cũng trả ``[]``
    để một ô lỗi không làm vỡ cả màn chi tiết.
    """
    try:
        return frappe.get_list(
            doctype,
            filters=filters,
            fields=fields,
            order_by=PREVIEW_ORDER_BY,
            limit_page_length=CONNECTION_COUNT_CAP + 1,
            ignore_ifnull=True,
        )
    except frappe.PermissionError:
        return []
    except Exception:
        frappe.log_error(
            title="connections: truy vấn nhóm thất bại", message=frappe.get_traceback()
        )
        return []


def _not_found() -> dict:
    """Lỗi "không tìm thấy" với message THỐNG NHẤT — không echo giá trị người gọi gửi.

    Phạm vi CHÍNH XÁC của lời hứa (ADR §D6 — đã ratify): doctype rác và mã bản ghi rác
    trả CÙNG một message, nên message không phân biệt được "sai doctype" với "sai mã".
    **KHÔNG** hứa che sự tồn tại của DocType: hình dạng phản hồi vẫn phân biệt được —
    doctype rác ⇒ ``NOT_FOUND``, còn doctype có thật nhưng ngoài allowlist ⇒
    ``success`` + ``groups: []`` (hợp đồng cũ, giữ nguyên). Ai cần bịt kênh đó phải đổi
    ADR trước, không phải sửa hàm này.
    """
    return _err(_("Không tìm thấy bản ghi."), code=ErrorCode.NOT_FOUND)


@frappe.whitelist()
def get_connections(doctype: str = "", name: str = "", preview_limit: str = "") -> dict:
    """GET /api/method/assetcore.api.connections.get_connections — cây bản ghi liên quan.

    Args:
        doctype: DocType của bản ghi gốc (vd ``AC Asset``).
        name: Mã bản ghi gốc (vd ``AC-ASSET-2026-00001``).
        preview_limit: số dòng preview mỗi ô; clamp về ``[1, 10]``, parse lỗi ⇒ mặc
            định 5. KHÔNG raise — panel phụ trợ không được làm vỡ màn chi tiết.

    Returns:
        Envelope ``_ok`` với ``groups`` = danh sách nhóm đã khai trong dashboard, mỗi ô
        gồm **10 khoá** (AC-CR-92 §17 D-CR92-1 + AC-CR-105 §18 D-CR105-1): ``doctype`` /
        ``label_vi`` / ``total`` / ``truncated`` / ``total_capped`` / ``items`` /
        ``deep_link_filters`` / ``can_create`` / ``create_route_hint`` /
        ``create_prefill``. ``create_prefill`` (khoá thứ 10) là ``dict[str,str]`` **luôn
        có mặt** — ``{query key mà chính màn tạo đọc: mã bản ghi cha}``, 0 hoặc 1 cặp;
        ``{}`` là **câu trả lời** ("không có gì để điền sẵn"), không phải thiếu dữ liệu ⇒
        client điều hướng bằng ``router.push({path})`` TRẦN, **không** fallback sang
        ``deep_link_filters`` (khoá của nó là Link fieldname dùng lọc *danh sách*, không
        phải khoá query của *màn tạo* — đính chính ADR §12.7). Hai cờ cắt là ``int`` 0|1 và nói về hai
        chủ thể KHÁC nhau: ``truncated`` cắt ``items`` theo ``preview_limit``,
        ``total_capped`` báo ``total`` chạm trần ``CONNECTION_COUNT_CAP`` (⇒ ``total`` là
        cận dưới, client render "100+"). Doctype tồn tại nhưng chưa khai đồ thị (hoặc ngoài
        allowlist) ⇒ ``groups: []`` (KHÔNG lỗi) — màn chi tiết vẫn hiển thị bình thường,
        chỉ là chưa có gì để nối. Mọi lỗi nghiệp vụ trả **in-envelope HTTP-200**.
    """
    doctype = (doctype or "").strip()
    name = (name or "").strip()
    if not doctype or not name:
        return _err(_("Thiếu doctype hoặc mã bản ghi."), code=ErrorCode.VALIDATION_ERROR)

    limit = clamp_preview_limit(preview_limit)
    empty = {"doctype": doctype, "name": name, "groups": [], "total": 0}

    # Allowlist TRƯỚC mọi thứ khác: chặn get_dashboard_data/get_doc/get_meta chạy trên
    # doctype tuỳ ý người gọi truyền vào. Doctype tồn tại nhưng ngoài allowlist KHÔNG
    # phải lỗi (hợp đồng cũ) — chỉ là chưa có đồ thị để dựng.
    if doctype not in service.allowed_source_doctypes():
        if not frappe.db.exists("DocType", doctype):
            return _not_found()
        return _ok(empty)

    if not frappe.db.exists(doctype, name):
        return _not_found()

    if not frappe.has_permission(doctype, ptype="read", doc=name):
        return _err(_("Bạn không có quyền xem bản ghi này."), code=ErrorCode.FORBIDDEN)

    try:
        payload = service.build_connections(
            doctype, name, preview_limit=limit, list_fn=_row_scoped_rows
        )
    except Exception:
        frappe.log_error(
            title="connections: dựng cây liên quan thất bại", message=frappe.get_traceback()
        )
        return _err(_("Không tải được bản ghi liên quan."), code=ErrorCode.INTERNAL)

    return _ok(payload)
