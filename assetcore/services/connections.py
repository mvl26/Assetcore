# Copyright (c) 2026, AssetCore Team
"""Dựng CÂY DỮ LIỆU «Bản ghi liên quan» (AC-CR-87 — ADR-IMM00-CONNECTIONS-TREE).

Trước AC-CR-87 khối này chỉ trả **badge đếm**: người dùng thấy *"Phiếu bảo trì định kỳ ·
6"* rồi phải bấm sang màn khác, chờ danh sách tải, tự lọc lại mới biết 6 phiếu đó là
phiếu nào. Nói cách khác nó là **bảng điều hướng tới chức năng**, không trả lời được
câu hỏi mà chính nó gợi ra. Module này bồi thêm 5 dòng preview THẬT cho mỗi ô (mã, tiêu
đề, trạng thái tiếng Việt, mốc thời gian), nhãn DocType tiếng Việt, bộ lọc an toàn
query-string, và cờ "được phép tạo mới".

**AC-CR-105 (ADR §18 — ADDITIVE)**: ô có ĐÚNG **10 khoá** = 9 khoá của AC-CR-92 **+**
``create_prefill: dict[str,str]`` ({query key mà chính màn tạo đọc: mã bản ghi cha}).
Khoá thứ 10 đóng nợ AC-CR-90(b): trước đó người dùng bấm «Tạo phiếu sửa chữa» trên hồ
sơ thiết bị và **màn tạo mở ra TRỐNG** ⇒ phải gõ lại mã vừa đứng trên đó, gõ sai thì
phiếu treo **sai thiết bị** (vết vòng đời NĐ98 sai chủ thể). Cùng vòng, vị-từ quyền của
nút tạo đổi từ ``has_permission`` rời sang **TOKEN** ``CREATE_CAPABILITY`` (xem
``create_capability_allows``) — giá trị không đổi, RÀNG BUỘC thì đổi.

**AC-CR-92 (ADR §17 — BREAKING)**: bộ 9 khoá nền
``{doctype, label_vi, total, truncated, total_capped, items, deep_link_filters,
can_create, create_route_hint}``. Bốn khoá LEGACY đã gỡ: ``label`` (tên DocType đi qua
``frappe._()`` — tiếng Anh thô), ``count`` (cùng con số với ``total``, khác tên),
``capped`` (bool — CR-01 cấm bool cho cờ cắt), ``filters`` (dạng Frappe, value có thể là
``["in", [...]]`` ⇒ không serialize được thành query-string). ``capped`` KHÔNG bị gỡ
trắng mà **đổi tên + đổi kiểu** thành ``total_capped: int 0|1``: gỡ trắng thì badge
«100+» thành «100» trần trụi ⇒ **tái sinh cắt-câm** ở đúng con số duy nhất người dùng
nhìn thấy.

Đồ thị liên kết vẫn đọc từ nguồn DUY NHẤT là ``Meta.get_dashboard_data()`` →
``<doctype>_dashboard.py::get_data()`` (cùng nguồn với tab Connections của Desk), nên
thêm một liên kết mới vẫn chỉ phải sửa file dashboard.

PHÂN QUYỀN — ba luật không đàm phán (ADR-IMM00-LIST-SCOPE §4b):
  1. Doctype liên quan mà người gọi không có DocPerm read ⇒ **ẩn hẳn ô** (không trả
     nhóm rỗng gây tò mò — mirror ``filter_permissions`` của Desk).
  2. MỌI dòng đọc qua ``frappe.get_list`` dưới ``frappe.session.user`` ⇒ áp CÙNG
     ``permission_query_conditions`` như khi người dùng bấm drill. Cấm ``frappe.db.count``
     (bỏ qua row-scope ⇒ rò tổng số toàn viện) và cấm ``frappe.get_all``.
  3. **MỘT predicate duy nhất**: mỗi ô phát ĐÚNG một lời gọi đọc dòng; ``total``,
     ``total_capped``, ``items``, ``truncated`` đều derive từ CHÍNH kết quả đó.
     Tách thành hai truy vấn (một lấy preview, một đếm) là khuôn sinh ra bug production
     *"Tổng 1430 / bảng RỖNG"* — hai truy vấn là hai cơ hội độc lập để nói dối.

Lời gọi ORM nằm ở ``api/connections.py::_row_scoped_rows`` và được **tiêm vào** đây qua
tham số ``list_fn`` (xem docstring ``build_connections``): tầng nghiệp vụ này vì thế
thuần và test được bằng reader giả (đếm số lời gọi để chứng minh ZERO-COST).
"""
from __future__ import annotations

import importlib
import json
import os
from types import ModuleType
from typing import Callable, Iterator

import frappe

from assetcore.services.shared import connection_meta as cmeta
from assetcore.services.shared import rbac
from assetcore.services.shared.constants import AssetStatus
from assetcore.services.shared.truncation import truncation_meta

#: Trần đếm mỗi ô. Panel phụ trợ chỉ cần phân biệt "không có" / "có ít" / "nhiều" —
#: một thiết bị 10 năm tuổi có thể có hàng nghìn ``Asset Lifecycle Event``, không đáng
#: để quét bảng lớn ×19 ô. Vượt trần ⇒ ``total_capped = 1`` và ``total`` là **CẬN DƯỚI**
#: ("có ÍT NHẤT 100") ⇒ client render "100+" và **mọi phép trừ trên ``total`` là số bịa**.
CONNECTION_COUNT_CAP = 100

#: Xấp xỉ "mới nhất trước". Sắp theo mốc thời gian domain (``due_date``/``reported_at``)
#: cần index riêng ⇒ CR perf riêng, đo trước (backlog ADR §7).
PREVIEW_ORDER_BY = "modified desc"

#: ``(doctype, filters, fields) -> rows`` — cổng đọc row-scoped do tầng API tiêm vào.
ListFn = Callable[[str, dict, list[str]], list[dict]]

_DOCTYPE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assetcore", "doctype"
)

#: Cache module dashboard — derive từ CÂY FILE của app, giống hệt trên mọi site và không
#: đổi cho tới khi tiến trình restart ⇒ an toàn để giữ ở phạm vi TIẾN TRÌNH.
_dashboard_cache: dict[str, ModuleType] | None = None

#: Khoá cache deep-link đặt trên ``frappe.local`` (phạm vi MỘT REQUEST). KHÔNG được là
#: biến toàn cục tiến trình: nó derive từ ``Meta.get_dashboard_data()``, thứ đã gộp cả
#: child table ``links`` trong DB LẪN hook ``override_doctype_dashboards`` của các app
#: cài trên CHÍNH site đó ⇒ giá trị là **theo site**. Một gunicorn phục vụ nhiều site
#: (bench dùng chung) sẽ để site A dựng cache rồi site B đọc nhầm: hậu quả im lặng là
#: ``count > 0`` nhưng ``deep_link_filters == {}`` (khoá bị lọc sạch bởi allowlist của
#: site khác) ⇒ vỡ INV-CONN-10 ở production trong khi test 1-site vẫn xanh. Ngoài ra
#: cache tiến trình còn stale tới tận restart khi có ai sửa liên kết trong DB.
_DEEP_LINK_LOCAL_KEY = "assetcore_connections_deep_link_keys"


# ─────────────────────────────────────────────────────────────────────────────
# 1. Allowlist doctype nguồn — derive từ CHÍNH các module dashboard
# ─────────────────────────────────────────────────────────────────────────────
def _doctype_name_for_slug(slug: str) -> str:
    """Tên DocType THẬT của một thư mục doctype (đọc ``<slug>.json``, không chạm DB).

    Không suy ra bằng ``unscrub`` vì tên thật không theo quy tắc viết hoa nào ("AC Asset"
    ≠ "Ac Asset", "IMM CAPA Record" ≠ "Imm Capa Record").
    """
    path = os.path.join(_DOCTYPE_DIR, slug, f"{slug}.json")
    try:
        with open(path, encoding="utf-8") as fh:
            return str(json.load(fh).get("name") or "")
    except (OSError, ValueError):
        return ""


def _dashboard_modules() -> dict[str, ModuleType]:
    """{DocType: module dashboard} — quét ``assetcore/assetcore/doctype/*/*_dashboard.py``.

    KHÔNG hardcode danh sách hub: thêm một file dashboard mới là tự động vào allowlist,
    và test parity nhãn tiếng Việt (INV-CONN-7) cũng tự động phủ theo.
    """
    global _dashboard_cache
    if _dashboard_cache is not None:
        return _dashboard_cache

    found: dict[str, ModuleType] = {}
    try:
        slugs = sorted(os.listdir(_DOCTYPE_DIR))
    except OSError:
        slugs = []
    for slug in slugs:
        module_path = os.path.join(_DOCTYPE_DIR, slug, f"{slug}_dashboard.py")
        if not os.path.isfile(module_path):
            continue
        doctype = _doctype_name_for_slug(slug)
        if not doctype:
            continue
        try:
            found[doctype] = importlib.import_module(
                f"assetcore.assetcore.doctype.{slug}.{slug}_dashboard"
            )
        except Exception:
            frappe.log_error(
                title="connections: không nạp được module dashboard",
                message=frappe.get_traceback(),
            )
    _dashboard_cache = found
    return found


def iter_dashboard_modules() -> Iterator[tuple[str, ModuleType]]:
    """Duyệt (DocType nguồn, module dashboard) — dùng cho test parity nhãn."""
    yield from _dashboard_modules().items()


def allowed_source_doctypes() -> frozenset[str]:
    """DocType được phép làm bản ghi **cha** của cây liên quan.

    Giá trị an ninh: chặn ``get_dashboard_data()`` / ``get_doc()`` / ``get_meta()`` chạy
    trên doctype TUỲ Ý người gọi truyền vào (site dùng chung có thể có doctype của app
    khác). Doctype tồn tại nhưng ngoài allowlist KHÔNG phải lỗi — nó trả cây rỗng có
    kiểm soát, giữ nguyên hợp đồng cũ (ADR §D6).
    """
    return frozenset(_dashboard_modules())


def _allowed_deep_link_keys() -> dict[str, frozenset[str]]:
    """{DocType đích: khoá được phép xuất hiện trong ``deep_link_filters``}.

    Derive từ chính 12 đồ thị: union ``fieldname`` / ``non_standard_fieldnames`` trỏ tới
    doctype đó trên MỌI hub, cộng ``"name"`` (ca ``internal_links``). KHÔNG khai tay bảng
    thứ hai — bảng tay sẽ lệch ngay lần đầu ai đó đổi tên Link field.

    Cache đặt trên ``frappe.local`` (một request) chứ KHÔNG phải biến toàn cục tiến trình
    — xem ``_DEEP_LINK_LOCAL_KEY``: đồ thị này phụ thuộc DB + hook của TỪNG site. Chi phí
    dựng lại là vài lời gọi ``get_meta`` (bản thân nó đã cache theo request/redis), KHÔNG
    có truy vấn đọc dòng nào ⇒ hợp đồng ZERO-COST (INV-CONN-6) không đổi.
    """
    cached = getattr(frappe.local, _DEEP_LINK_LOCAL_KEY, None)
    if cached is not None:
        return cached

    keys: dict[str, set[str]] = {}
    for hub in _dashboard_modules():
        data = _dashboard_data(hub)
        default_fieldname = data.get("fieldname") or ""
        non_standard = data.get("non_standard_fieldnames") or {}
        for group in data.get("transactions") or []:
            for linked_dt in group.get("items") or []:
                bucket = keys.setdefault(linked_dt, {"name"})
                fieldname = non_standard.get(linked_dt, default_fieldname)
                if fieldname:
                    bucket.add(fieldname)
    resolved = {dt: frozenset(v) for dt, v in keys.items()}
    setattr(frappe.local, _DEEP_LINK_LOCAL_KEY, resolved)
    return resolved


def deep_link_keys(doctype: str) -> frozenset[str]:
    """Khoá hợp lệ của ``deep_link_filters`` cho một DocType đích."""
    return _allowed_deep_link_keys().get(doctype) or frozenset({"name"})


# ─────────────────────────────────────────────────────────────────────────────
# 2. Đọc đồ thị + phân giải bộ lọc
# ─────────────────────────────────────────────────────────────────────────────
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


# ─────────────────────────────────────────────────────────────────────────────
# 3. Preview — field THẬT, giá trị chuẩn hoá, không bao giờ ``None``
# ─────────────────────────────────────────────────────────────────────────────
def _usable_field(meta, fieldname: str) -> bool:
    """Field tồn tại và ở ``permlevel 0``.

    Field ``permlevel > 0`` chọn qua ``get_list`` bị **strip CÂM** khi người dùng không
    có DocPerm ở permlevel đó (``memory/permlevel_no_docperm_silent_strip.md``) — badge
    im lặng về rỗng, trông y hệt "chưa có dữ liệu".
    """
    if not fieldname:
        return False
    df = meta.get_field(fieldname)
    return bool(df) and (df.permlevel or 0) == 0


def _preview_plan(doctype: str) -> tuple[list[str], cmeta.PreviewSpec]:
    """(danh sách field cần SELECT, spec đã lọc theo meta THẬT).

    Doctype chưa khai trong ``PREVIEW_FIELDS`` ⇒ fallback ``Meta.title_field`` +
    ``modified``: vẫn có preview đọc được, KHÔNG raise, và ``total`` vẫn đúng.
    """
    spec = cmeta.preview_spec(doctype) or cmeta.PreviewSpec("", "", "")
    try:
        meta = frappe.get_meta(doctype)
    except Exception:
        return ["name", "modified"], cmeta.PreviewSpec("", "", "")

    title = spec.title if _usable_field(meta, spec.title) else ""
    if not title:
        fallback = getattr(meta, "title_field", "") or ""
        title = fallback if _usable_field(meta, fallback) else ""
    status = spec.status if _usable_field(meta, spec.status) else ""
    date = spec.date if _usable_field(meta, spec.date) else ""

    fields = ["name", "modified"]
    for fieldname in (title, status, date):
        if fieldname and fieldname not in fields:
            fields.append(fieldname)
    return fields, cmeta.PreviewSpec(title, status, date)


def _as_date_str(value: object) -> str:
    """Chuẩn hoá mốc thời gian về ``YYYY-MM-DD``; không phân giải được ⇒ ``""``."""
    if not value:
        return ""
    try:
        return frappe.utils.getdate(value).strftime("%Y-%m-%d")
    except Exception:
        return ""


def _preview_row(doctype: str, row: dict, spec: cmeta.PreviewSpec) -> dict:
    """Một dòng preview: 5 khoá, toàn bộ ``str``, KHÔNG BAO GIỜ ``None``.

    ``title`` không bao giờ rỗng (fallback cuối cùng là mã bản ghi); ``status_label`` là
    nhãn tiếng Việt — FE render khoá này, ``status`` thô chỉ để so sánh/lọc.
    """
    name = str(row.get("name") or "")
    title = str(row.get(spec.title) or "").strip() if spec.title else ""
    status = str(row.get(spec.status) or "").strip() if spec.status else ""
    date = _as_date_str(row.get(spec.date)) if spec.date else ""
    return {
        "name": name,
        "title": title or name,
        "status": status,
        "status_label": cmeta.status_label(doctype, status),
        "date": date or _as_date_str(row.get("modified")),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4. Nút "tạo bản ghi liên quan" — mặc định ĐÓNG
# ─────────────────────────────────────────────────────────────────────────────
def _parent_blocks_creation(doctype: str, name: str) -> bool:
    """Cổng vòng đời: thiết bị ngừng sử dụng/đã thanh lý ⇒ không quảng cáo tạo phiếu.

    Dùng **CÙNG hằng** ``AssetStatus.BLOCKED_FOR_WO`` mà ``services/imm00.py::
    validate_asset_for_operations`` (BR-00-05) dùng để CHẶN ⇒ hiển thị là *tấm gương*
    của enforcement, không phải bản diễn giải thứ hai.
    """
    if doctype != "AC Asset":
        return False
    status = frappe.db.get_value("AC Asset", name, "lifecycle_status")
    return status in AssetStatus.BLOCKED_FOR_WO


def create_capability_allows(target: str) -> bool:
    """Vị-từ P3 — người gọi có quyền TẠO ``target``, gác bằng **TOKEN** capability.

    Khai trong ``connection_meta.CREATE_CAPABILITY`` ⇒ ``rbac.can(token)``; **không** khai
    ⇒ giữ nguyên hành vi cũ ``frappe.has_permission(target, "create")`` (3 doctype cố ý
    không khai — lý do từng dòng ở ``connection_meta.CREATE_CAPABILITY``).

    Giá trị trả về **không đổi hôm nay** (``CAPABILITY_MAP[token] == (target, "create")``
    cho cả 5 token nên ``rbac.can`` cho ra đúng con số ``has_permission`` đang cho): cái
    đổi là **RÀNG BUỘC**. Trước đây ai đó đổi binding của ``pm.create`` sang permtype
    khác thì gate API đổi, route-guard FE đổi, còn ô liên quan **im lặng giữ nguyên** —
    khuôn "RBAC dead-gate". Nay token nằm trong đường thực thi và có guard
    (``tests/test_connections_tree.py::t33``/``t34``) nên drift phải ĐỎ.

    ⚠️ ``rbac.can`` với cap **vắng** trong ``CAPABILITY_MAP`` trả ``False`` IM LẶNG
    (stale-safe ``rbac.py:183-185``) ⇒ khai sai một chữ = nút biến mất toàn hệ thống mà
    không lỗi nào bật lên. Đó chính là ca mà guard INV-CONN4-2 (t33) chặn.

    Args:
        target: DocType đích của ô liên quan (bản ghi sắp được tạo).

    Returns:
        bool: True khi người gọi hiện tại được phép tạo ``target``.
    """
    token = cmeta.CREATE_CAPABILITY.get(target)
    if token:
        return rbac.can(token)
    return bool(frappe.has_permission(target, ptype="create"))


def _create_affordance(
    source_doctype: str, linked_dt: str, fieldname: str, is_internal: bool,
    blocked: bool, name: str,
) -> tuple[bool, str, dict[str, str]]:
    """``(can_create, create_route_hint, create_prefill)`` — giao 4 vị-từ, mặc định ĐÓNG.

    1. **ROUTE** — doctype đích có màn tạo THẬT (``CREATE_CONTEXT``);
    2. **HƯỚNG** — nhóm là **reverse-link** và Link field khớp ngữ cảnh cha đã khai (bản
       ghi mới phải nối được vào đúng bản ghi cha); nhóm ``internal_links`` (xuôi) luôn
       False ("tạo Thiết bị" từ màn phiếu sửa chữa là vô nghĩa);
    3. **CAPABILITY** — ``create_capability_allows`` (token, xem hàm trên);
    4. **VÒNG ĐỜI** — ``blocked`` từ ``_parent_blocks_creation``. Vòng này GIỮ cổng
       chặn-tất ``AssetStatus.BLOCKED_FOR_WO``; vị-từ per-doctype là ``AC-CR-90(c)``
       (ADR §18.6) ⇒ ô «Phiếu sửa chữa»/«Sự cố» vẫn tắt ở ``Out of Service``: advertise
       **HẸP HƠN** enforcement là an toàn (không sinh nút chết), chỉ là chưa đủ rộng.

    Ba khoá sinh ra tại **CÙNG MỘT câu ``return``** nên KHÔNG THỂ lệch nhau — bất biến
    INV-CONN4-1 (đính chính ADR §18 D-CR105-2) đúng do **CẤU TRÚC** chứ không do một
    assert rời:

    * ``can_create is False ⟺ create_route_hint == ""`` (biconditional THẬT);
    * ``can_create is False ⇒ create_prefill == {}`` — **cấm prefill mồ côi** (nút tắt mà
      payload vẫn mang mã bản ghi cha = rò dữ liệu client không có đường hợp lệ để dùng);
    * ``can_create is True ∧ create_prefill == {}`` là **HỢP LỆ**. Mệnh đề
      "True ⇒ prefill ≠ {}" **KHÔNG TỒN TẠI**: ``can_create`` trả lời *"được phép tạo và
      nối được vào cha"*, ``create_prefill`` trả lời *"màn tạo có đọc khoá query nào để
      mà điền sẵn không"* — hai câu hỏi ở hai tầng (quyền/schema vs hợp đồng URL của FE).

    Prefill thuần **in-memory** từ ``(ctx.query_keys, source_doctype, name)`` — cả ba đã
    nằm trong tay hàm ⇒ **0 truy vấn phụ** (ZERO-COST INV-CONN-6/4-10).

    Args:
        source_doctype: DocType bản ghi CHA (hub).
        linked_dt: DocType đích của ô.
        fieldname: Link fieldname phân giải được cho ô (rỗng với ``internal_links``).
        is_internal: ô thuộc nhóm liên kết XUÔI.
        blocked: cổng vòng đời của bản ghi cha đã chặn.
        name: mã bản ghi CHA — **tham số cuối**; là giá trị duy nhất đi vào prefill.

    Returns:
        tuple: ``(can_create, create_route_hint, create_prefill)``.
    """
    if is_internal or blocked:
        return False, "", {}
    context = cmeta.CREATE_CONTEXT.get(linked_dt)
    if not context or context.parents.get(source_doctype) != fieldname:
        return False, "", {}
    if not create_capability_allows(linked_dt):
        return False, "", {}
    # Khoá là **QUERY KEY của FE** (``asset``/``pm_wo``/``incident``), KHÔNG phải Link
    # fieldname của BE (``asset_ref``/``source_pm_wo``): màn tạo đọc ``route.query.<key>``
    # nên fieldname sẽ thành query rác + "đã điền sẵn" mà ô trống (ADR §18 D-CR105-3).
    query_key = context.query_keys.get(source_doctype) or ""
    prefill = {query_key: name} if query_key else {}
    return True, context.route, prefill


# ─────────────────────────────────────────────────────────────────────────────
# 5. Dựng cây
# ─────────────────────────────────────────────────────────────────────────────
def _safe_deep_link(linked_dt: str, filters: dict[str, str]) -> dict[str, str]:
    """Chỉ giữ khoá thuộc allowlist derive từ đồ thị; mọi value đã là ``str``."""
    allowed = deep_link_keys(linked_dt)
    return {k: v for k, v in filters.items() if k in allowed}


def build_connections(
    doctype: str, name: str, *, preview_limit: int, list_fn: ListFn
) -> dict:
    """Cây bản ghi liên quan của một hồ sơ (payload của ``_ok``).

    Args:
        doctype: DocType bản ghi cha — người gọi PHẢI đã kiểm tra tồn tại + quyền đọc.
        name: mã bản ghi cha.
        preview_limit: số dòng preview mỗi ô, **đã clamp** (``clamp_preview_limit``).
            Truyền số chưa clamp vào ``truncation_meta`` sẽ báo "không cắt" trong khi
            đã cắt (INV-TRUNC-LIMIT).
        list_fn: cổng đọc row-scoped ``(doctype, filters, fields) -> rows``, chạy dưới
            ``frappe.session.user`` với trần ``CONNECTION_COUNT_CAP + 1``. Tiêm vào để
            tầng này thuần (test đếm được số lời gọi ⇒ chứng minh 1 truy vấn/ô).

    Returns:
        dict: ``{doctype, name, groups, total}``; ``total`` cấp payload là **tổng cộng
        dồn ``item["total"]`` mọi ô** — cộng dồn CHÍNH biến được phát ra, không tính lại
        bằng biểu thức thứ hai (AC-CR-92 D-CR92-3: hai biểu thức cùng nghĩa cạnh nhau là
        hai cơ hội độc lập để nói dối). Mỗi ô có ĐÚNG **10** khoá (AC-CR-105 thêm
        ``create_prefill``, ADR §18 D-CR105-1); ``total_capped == 1`` ⇒
        ``total`` là **CẬN DƯỚI** ⇒ tầng trên PHẢI hiển thị "100+" và **cấm mọi phép
        trừ** trên ``total`` ("còn N chưa hiển thị" khi đó có thể sai hàng trăm đơn vị).
        Doctype chưa khai đồ thị ⇒ ``groups: []`` (KHÔNG lỗi — màn chi tiết vẫn render).
    """
    data = _dashboard_data(doctype)
    transactions = data.get("transactions") or []
    if not transactions:
        return {"doctype": doctype, "name": name, "groups": [], "total": 0}

    default_fieldname = data.get("fieldname")
    non_standard = data.get("non_standard_fieldnames") or {}
    internal = data.get("internal_links") or {}

    parent_doc = frappe.get_doc(doctype, name) if internal else None
    blocked = _parent_blocks_creation(doctype, name)

    groups: list[dict] = []
    total = 0
    for group in transactions:
        items: list[dict] = []
        for linked_dt in group.get("items") or []:
            if not frappe.has_permission(linked_dt, ptype="read"):
                continue  # ẩn hẳn — không bộc lộ sự tồn tại của dữ liệu ngoài quyền

            link = internal.get(linked_dt)
            is_internal = link is not None
            fieldname = ""
            if is_internal:
                names = _internal_link_names(parent_doc, link)
                if not names:
                    continue
                filters: dict = {"name": ["in", names]}
                # FE ghép thẳng vào query-string ⇒ mọi value phải là scalar chuỗi;
                # dấu phẩy = tập "in" (ADR §D7).
                deep_link = {"name": ",".join(names)}
            else:
                fieldname = non_standard.get(linked_dt, default_fieldname)
                if not fieldname:
                    continue  # không phân giải được ⇒ bỏ, thay vì đếm sai
                filters = {fieldname: name}
                deep_link = {fieldname: name}

            fields, spec = _preview_plan(linked_dt)
            rows = list_fn(linked_dt, filters, fields)

            count = min(len(rows), CONNECTION_COUNT_CAP)
            # ``> CAP`` chứ KHÔNG ``>= CAP``: dùng ``>=`` biến "đúng 100" thành "100+" =
            # bịa thêm dữ liệu. ``1 if … else 0`` chứ KHÔNG ``len(rows) > CAP``: ``bool``
            # là subclass của ``int`` ⇒ JSON ``true`` ⇒ codegen mobile crash (CR-01).
            total_capped = 1 if len(rows) > CONNECTION_COUNT_CAP else 0
            preview = [_preview_row(linked_dt, row, spec) for row in rows[:preview_limit]]
            # SSoT truncation (ADR-IMM00-TRUNCATION-SSOT D1). ``count_fn`` thuần
            # in-memory ⇒ 0 truy vấn COUNT ở MỌI ca (mạnh hơn ZERO-COST D4).
            item_total, truncated = truncation_meta(len(preview), preview_limit, lambda c=count: c)
            can_create, route_hint, prefill = _create_affordance(
                doctype, linked_dt, fieldname, is_internal, blocked, name
            )

            total += item_total          # cộng dồn CHÍNH biến được phát ra (D-CR92-3)
            items.append({
                "doctype": linked_dt,
                "label_vi": cmeta.label_vi(linked_dt),
                "total": item_total,
                "truncated": truncated,          # int 0|1 — ``items`` cắt theo preview_limit
                "total_capped": total_capped,    # int 0|1 — ``total`` là CẬN DƯỚI (≥ CAP)
                "items": preview,
                "deep_link_filters": _safe_deep_link(linked_dt, deep_link),
                "can_create": can_create,
                "create_route_hint": route_hint,
                # Khoá thứ 10 (AC-CR-105) — {query key màn tạo ĐỌC: mã bản ghi cha}.
                # LUÔN có mặt, LUÔN là dict (không bao giờ ``None``): mỗi khoá optional ở
                # client là một nhánh fallback, và mỗi nhánh fallback là một chỗ để hợp
                # đồng lệch âm thầm. ``{}`` là **câu trả lời** ("không có gì điền sẵn"),
                # không phải thiếu dữ liệu ⇒ FE push TRẦN, không fallback deep_link.
                "create_prefill": prefill,
            })

        if items:
            # Nhãn nhóm đã là tiếng Việt (khai bằng ``_("…")`` trong chính file
            # dashboard). ``label_vi`` mirror lại để FE có MỘT accessor thống nhất cho
            # cả nhóm lẫn ô, không phải nhớ "nhóm thì đọc label, ô thì đọc label_vi".
            label = group.get("label") or ""
            groups.append({
                "label": label,
                "label_vi": label,
                "items": items,
            })

    return {"doctype": doctype, "name": name, "groups": groups, "total": total}
