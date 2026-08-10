# Copyright (c) 2026, AssetCore Team
"""Filter helpers shared by IMM list endpoints.

Three responsibilities:
1. `normalize_filters()` — wrap raw lists in ``["in", value]`` so Frappe
   does not misinterpret them as ``[op, value]`` pairs.
2. `pop_search()` + `count_with_or()` — translate the FE free-text
   ``search`` filter key into ``or_filters`` LIKE clauses. The FE puts
   ``search`` into the same dict as column filters; if it leaks through to
   ``frappe.get_list`` we get ``Unknown column 'tab<DocType>.search'``.
3. `assert_allowed_filter_keys()` (AC-CR-79) — reject filter keys outside a
   module whitelist with a TYPED 400 in-envelope, BEFORE they reach
   ``frappe.get_list`` and blow up as ``OperationalError(1054)`` → raw
   HTTP-500 leaking the SQL table/column name.
"""
from __future__ import annotations

import re

import frappe

_OP_TOKENS = ("in", "not in", "between", "like", "=", "!=", "<", ">", "<=", ">=")


def normalize_filters(f: dict | None) -> dict:
    """Normalize list values in a filter dict to Frappe [op, value] format.

    Frappe `get_all` filters accept either scalar values or [op, value] pairs.
    A raw list without an operator prefix is ambiguous — this function wraps
    such lists in ``["in", value]`` so callers can pass plain Python lists.

    Args:
        f: filter dict from API/service layer, or None.

    Returns:
        Normalized filter dict safe to pass to `frappe.get_all`.
    """
    out: dict = {}
    for k, v in (f or {}).items():
        if isinstance(v, list) and v and not (len(v) == 2 and v[0] in _OP_TOKENS):
            out[k] = ["in", v]
        else:
            out[k] = v
    return out


# ─────────────────────────────────────────────────────────────────────────────
# AC-CR-79 — whitelist khoá `filters` (MỘT nơi biết cách raise; MỖI module tự
# khai tập khoá của mình ⇒ không có bản chép tay thứ hai).
# ─────────────────────────────────────────────────────────────────────────────

_MAX_ECHOED_KEYS = 5
_SAFE_KEY_RE = re.compile(r"\A[A-Za-z0-9_]{1,64}\Z")
_UNSAFE_KEY_LABEL = "<khoá không hợp lệ>"


def _safe_key(k: object) -> str:
    """Chuẩn hoá khoá do CLIENT gửi TRƯỚC KHI đưa vào message trả về.

    Khoá lọc hợp lệ luôn là identifier (``[A-Za-z0-9_]``, ≤64 ký tự). Bất kỳ thứ gì
    khác (chuỗi rỗng, khoảng trắng, ký tự SQL/HTML, quá dài) ⇒ KHÔNG phản chiếu
    nguyên văn — tránh biến message lỗi thành kênh reflected-content.

    Args:
        k: khoá thô lấy từ dict `filters` của client.

    Returns:
        Chính khoá đó nếu an toàn, ngược lại nhãn cố định ``<khoá không hợp lệ>``.
    """
    s = str(k)
    return s if _SAFE_KEY_RE.match(s) else _UNSAFE_KEY_LABEL


def assert_allowed_filter_keys(f: dict | None, allowed: frozenset[str]) -> None:
    """Chặn khoá `filters` KHÔNG thuộc whitelist của module — **400 IN-ENVELOPE**.

    Vì sao tồn tại (đo được, probe LIVE 2026-07-27): ``frappe.get_list(filters={<khoá
    lạ>: …})`` ném ``OperationalError(1054, "Unknown column 'tab<DocType>.<khoá>' in
    'WHERE'")``, mà :func:`assetcore.utils.api_handler.handle` **CỐ Ý** không bắt
    Exception chung ⇒ lỗi INPUT thoát ra **HTTP-500 KHÔNG có ``body.success``** và
    **lộ tên bảng/cột SQL**. Client mobile route theo ``body.success`` nên không phân
    loại được (có app hiểu nhầm hết phiên → đăng xuất người dùng).

    Gọi ở ĐẦU entrypoint list công khai, **TRƯỚC** mọi phép biến đổi dict
    (``pop_search`` / ``_apply_open_drill`` / ``normalize_filters``) ⇒ khoá ẢO vẫn còn
    nguyên lúc kiểm (nên chúng PHẢI ∈ whitelist) và ngữ nghĩa của chúng KHÔNG đổi.
    Đặt **NGOÀI** ``run_rowscoped``: ``ServiceError`` ≠ ``PermissionError`` nên không
    bị nhánh 403 nuốt.

    Args:
        f: filter dict SAU parse_json + vendor-scope + ``mine`` + ``search`` injection.
        allowed: whitelist của module (``_ALLOWED_FILTER_KEYS``) — SSoT DUY NHẤT.

    Raises:
        ServiceError: ``code=INVALID_PARAMS``, ``http_status=400``,
            ``message_code=MSG.VAL_INVALID_FILTER_KEY``. Message TIẾNG VIỆT nêu khoá
            sai + tập khoá hợp lệ; **KHÔNG** echo GIÁ TRỊ người dùng gửi (giá trị có
            thể là dữ liệu người bệnh/thiết bị) và **KHÔNG** echo tên bảng/cột SQL.
            Khi ``f`` KHÔNG phải mapping ⇒ CÙNG bucket ``INVALID_PARAMS``/400 nhưng
            KHÔNG kèm ``message_code`` (đồng nhất họ "``filters`` sai định dạng" của
            :func:`assetcore.utils.api_handler.parse_json`).
    """
    # Lazy-import: `services.shared.__init__` import `.filters` ⇒ import
    # `utils.notify` ở top-level tạo vòng import lúc `bench start`. Chi phí ~0
    # (chỉ chạy ở nhánh LỖI, và module đã nằm trong sys.modules từ lâu).
    from assetcore.services.shared.constants import ErrorCode
    from assetcore.services.shared.errors import ServiceError
    from assetcore.utils.messages import MSG
    from assetcore.utils.notify import nthrow

    # SHAPE-GATE (QA 2026-07-27) — `parse_json` trả VERBATIM thứ JSON parse ra, nên
    # `filters` có thể là list/int/str chứ không chỉ dict. Trước gate này:
    #   `[["asset_ref","=","X"]]` (dạng filter CANONICAL của Frappe) → `set(f)` ném
    #   `TypeError: unhashable type: 'list'`; `123` → `'int' object is not iterable`.
    # Cả hai thoát `api_handler.handle` (cố ý không bắt Exception chung) ⇒ **HTTP-500
    # KHÔNG có `body.success`** = ĐÚNG class-of-bug AC-CR-79 hứa đóng, chỉ khác đường
    # vào. `str` CỐ Ý KHÔNG chặn ở đây: nó iterate ra ký tự nên rơi xuống nhánh
    # khoá-lạ bên dưới và đã có message hữu ích + `message_code`.
    if f is not None and not isinstance(f, (dict, str)):
        raise ServiceError(
            ErrorCode.INVALID_PARAMS,
            "Tham số filters phải là đối tượng JSON dạng {\"<khoá>\": <giá trị>}. "
            f"Các khoá hợp lệ: {', '.join(sorted(allowed))}.",
            http_status=400,
        )

    unknown = sorted(set(f or {}) - set(allowed))
    if not unknown:
        return
    # `sorted()` CẢ HAI vế ⇒ message DETERMINISTIC (test/diff/cache ổn định).
    shown = [_safe_key(k) for k in unknown[:_MAX_ECHOED_KEYS]]
    if len(unknown) > _MAX_ECHOED_KEYS:
        shown.append(f"(và {len(unknown) - _MAX_ECHOED_KEYS} khoá khác)")
    nthrow(
        MSG.VAL_INVALID_FILTER_KEY,
        invalid_keys=", ".join(shown),
        allowed_keys=", ".join(sorted(allowed)),
    )


_LINK_LOOKUP_LIMIT = 500


def _escape_like(term: str) -> str:
    """Escape LIKE-metachar so a user-typed ``%`` / ``_`` matches LITERALLY.

    Mirror :func:`assetcore.services.imm00.escape_like_term` (SSoT contract,
    ADR-IMM00-SEARCH-ESCAPE): escape ``%`` → ``\\%`` and ``_`` → ``\\_`` only.
    Do NOT touch ``\\`` — Frappe ``DatabaseQuery`` already doubles the backslash
    for the ``like`` operator (db_query.py:938-940); escaping it here would flip
    a literal backslash into a wildcard-escape and break the match. Without this,
    ``search='%'`` → ``LIKE '%%%'`` matches the whole table (over-match /
    LIKE-backtracking DoS surface). Total-function: never raises; ``''`` → ``''``.

    Applied ONCE at the ``like`` build point so BOTH the parent OR-LIKE and the
    ``link_search`` lookup use the same escaped term ⇒ count_with_or / get_list
    stay byte-parity on the same ``or_filters``.
    """
    return term.replace("%", "\\%").replace("_", "\\_")


def pop_search(
    f: dict | None,
    searchable_fields: list[str],
    *,
    link_search: dict[str, tuple[str, str]] | None = None,
    escape_wildcards: bool = False,
) -> tuple[dict, list | None]:
    """Pop the FE free-text ``search`` key and translate it to ``or_filters``.

    The FE list views put ``search`` into the same filter dict as the column
    filters (e.g. ``{"workflow_state": "Draft", "search": "NR-2026"}``). If
    the BE passes the dict straight to ``frappe.get_list`` MariaDB rejects
    with ``Unknown column 'tab<DocType>.search' in 'WHERE'``.

    This helper extracts ``search`` and returns an ``or_filters`` list of
    ``[field, "like", "%search%"]`` triples — one per ``searchable_fields``.

    Args:
        f: filter dict from API layer, may contain a ``search`` key.
        searchable_fields: fields on the parent DocType to OR-LIKE the term
            across (direct LIKE on parent columns).
        link_search: optional ``{link_field: (linked_doctype, display_field)}``.
            Use when the FE placeholder promises searching by the **display
            name** of a Link target (e.g. "tên model" — model_name lives on
            ``IMM Device Model``, not on the parent). For each entry the
            helper looks up linked rows whose ``display_field`` LIKE the
            term, then adds ``[link_field, "in", [matched_ids]]`` to the OR
            clause. Lookup is capped at ``_LINK_LOOKUP_LIMIT`` matches.
        escape_wildcards: when True, escape LIKE-metachar (``%``/``_``) in the
            user term so they match LITERALLY instead of acting as SQL
            wildcards (prevents ``search='%'`` matching the whole table +
            LIKE-backtracking DoS surface — CR-18 IMM-08/09). Opt-in: default
            False keeps the pre-existing behavior of every current caller
            (e.g. IMM-11 ``list_schedules`` whose ``_Test``-prefixed fixtures
            rely on ``_`` as a single-char wildcard) byte-identical.
            NOTE: under Frappe's ``like`` the escaped metachar matches nothing
            (engine doubles the backslash), so real data containing literal
            ``%``/``_`` is out of scope — acceptable for WO/asset codes+names
            which never contain them.

    Returns:
        ``(filters_without_search, or_filters_or_None)``. Pass both straight
        to ``frappe.get_list`` / :func:`count_with_or`.
    """
    f = dict(f or {})
    raw = f.pop("search", None)
    if raw is None:
        return f, None
    term = str(raw).strip()
    if not term:
        return f, None
    safe = _escape_like(term) if escape_wildcards else term
    like = f"%{safe}%"
    or_filters: list = [[field, "like", like] for field in searchable_fields]
    for link_field, (linked_doctype, display_field) in (link_search or {}).items():
        try:
            rows = frappe.get_all(
                linked_doctype,
                or_filters=[
                    [display_field, "like", like],
                    ["name", "like", like],
                ],
                fields=["name"],
                limit_page_length=_LINK_LOOKUP_LIMIT,
                ignore_permissions=True,
            )
        except Exception:
            rows = []
        ids = [r["name"] for r in rows]
        if ids:
            or_filters.append([link_field, "in", ids])
    return f, or_filters


def count_with_or(
    doctype: str,
    filters: dict | list | None,
    or_filters: list | None,
) -> int:
    """Count rows matching ``filters`` AND/OR ``or_filters`` — permission-aware.

    ``filters`` nhận CẢ dạng **list-form** ``[[doctype, field, op, val], …]`` (AC-CR-98):
    một số endpoint phải dùng dạng này để CÙNG một cột mang nhiều ràng buộc mà không
    clobber (vd ``imm04.list_commissioning`` với ``overdue=1``: ``workflow_state``
    user-chọn AND ``not in`` terminal). ``frappe.get_list`` nhận cả hai dạng như nhau
    nên đường đếm và đường đọc vẫn là MỘT predicate — điều kiện của INVARIANT dưới đây.

    INVARIANT (ADR-IMM00-LIST-SCOPE §4b): the total MUST be computed with the
    **same predicate that ``frappe.get_list`` applies to the items** — including
    ``permission_query_conditions`` (row-scope hooks). The previous implementation
    used ``frappe.db.count`` / ``frappe.get_all``, **neither of which applies
    ``permission_query_conditions``**, so for a row-scoped persona (vendor /
    internal technician before the read-all fix) the count counted EVERY row while
    ``get_list`` returned only the scoped subset → header "Tổng N" ≠ số dòng thực.

    Fix: count via ``frappe.get_list(..., limit_page_length=0)`` for BOTH the
    search (``or_filters``) and non-search paths. ``get_list`` runs the same
    ``DatabaseQuery`` engine as the items query and applies the same
    ``permission_query_conditions`` + DocPerm checks ⇒ ``count == len(items)`` for
    every persona on every list endpoint that pairs this helper with
    ``frappe.get_list`` (AC Asset / NR / Plan Period / Tender Spec / Vendor Eval /
    Procurement Document). ``or_filters`` is preserved verbatim for free-text LIKE
    search parity.

    NOTE — chi phí (ĐO 2026-07-25 trên site dev, KHÔNG phải ước lượng):
    ``limit_page_length=0`` materialize TOÀN BỘ cột ``name`` vào Python ⇒ chi phí
    **tuyến tính theo số dòng KHỚP**: 1.6 ms @104 dòng · 5.1 ms @1060 dòng
    (≈ 4 ms/1000 dòng). Hot path hiện tại chưa nghẽn (``PM Work Order`` 0 dòng,
    ``Asset Repair`` 9 dòng ⇒ ``count_overdue_pm`` p95 = 1.96 ms;
    ``imm08.get_dashboard_stats`` p95 = 24 ms) nên **cố ý CHƯA tối ưu**
    (measure-first).

    Recipe thay thế khi một DocType được đếm vượt ~20k dòng (ADR
    §8.10 B7 — đã verify parity 11/11 case, 0 lệch, phẳng ~0.9 ms):
    ``frappe.get_list(doctype, filters=…, or_filters=…, fields=["count(name) as _c"],
    limit_page_length=0)[0]["_c"]`` — vẫn là DatabaseQuery ⇒ **cùng predicate**
    (``permission_query_conditions`` + DocPerm) nên INVARIANT count==rows giữ
    nguyên. KHÔNG đổi sang ``frappe.db.count`` (mất row-scope = tái sinh §1).
    """
    rows = frappe.get_list(
        doctype,
        filters=filters,
        or_filters=or_filters if or_filters else None,
        fields=["name"],
        limit_page_length=0,
    )
    return len(rows)


def count_ignore_permissions(
    doctype: str,
    filters: dict | None,
    or_filters: list | None,
) -> int:
    """Count rows matching ``filters`` AND/OR ``or_filters`` — **ignoring permissions**.

    Cặp song sinh RAW của :func:`count_with_or`. Mirror byte-for-byte trừ đúng MỘT
    thứ: entrypoint là ``frappe.get_all`` (bỏ qua ``permission_query_conditions`` +
    DocPerm) thay vì ``frappe.get_list``.

    INVARIANT (ADR-IMM00-LIST-SCOPE §8.3): **counter và rows PHẢI LUÔN đi qua CÙNG
    MỘT engine**. Dùng 2 engine khác nhau cho ``total`` và ``rows`` là nguồn duy nhất
    sinh ra cả 2 chiều lệch đã gặp ở production:
      - §1 (count thô > rows scoped): header "Tổng 1430" mà bảng RỖNG;
      - §8 (count scoped < rows thô): KTV đọc được phiếu KHÔNG được giao (RÒ DỮ LIỆU).

    Helper này CHỈ dùng cho ``BaseRepository.list(scope="system")`` — nhánh
    scheduler / KPI tổng hợp / denorm-enrich, nơi rows cũng đi ``frappe.get_all``.
    KHÔNG dùng cho endpoint list người-dùng: ở đó phải là :func:`count_with_or`.

    Args:
        doctype: tên DocType.
        filters: filter dict (AND) — truyền VERBATIM, không normalize thêm.
        or_filters: OR-LIKE clauses (free-text search) — verbatim như count_with_or.

    Returns:
        int — số bản ghi khớp, KHÔNG áp row-scope hook.
    """
    rows = frappe.get_all(
        doctype,
        filters=filters,
        or_filters=or_filters if or_filters else None,
        fields=["name"],
        limit_page_length=0,
    )
    return len(rows)
