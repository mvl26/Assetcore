# Copyright (c) 2026, AssetCore Team
"""IMM-00 REST API — 43 endpoints for AssetCore foundation DocTypes.

Convention:
  GET  → frappe.whitelist(allow_guest=False)
  POST → frappe.whitelist(methods=["POST"])
  Response: _ok(data) | _err(message, code)
"""
import json
from typing import Optional

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit          # precedent api/auth.py:10

from assetcore.utils.response import _ok, _err
from assetcore.utils.api_handler import handle
from assetcore.services.shared import ErrorCode, ServiceError
from assetcore.services.shared.scope import apply_vendor_scope, assert_vendor_can_access
from assetcore.utils.pagination import paginate
from assetcore.services.shared.filters import count_with_or
from assetcore.services.shared import rbac
from assetcore.services.imm00 import (
    transition_asset_status,
    asset_allowed_transitions,   # SSoT server-driven CTA lifecycle (CR-WF-00-LIFECYCLE-SURFACE)
    validate_asset_for_operations,
    resolve_qr_token as _svc_resolve_qr_token,
    regenerate_asset_qr_token as _svc_regenerate_asset_qr_token,
    build_asset_scan_info as _svc_build_asset_scan_info,
    # SSoT overdue derivers (tz-safe + exempt BLOCKED_FOR_WO) — tái dùng CHÍNH
    # deriver của màn quét-QR cho màn admin-detail (KHÔNG re-implement so ngày).
    _is_pm_overdue,
    _is_calibration_overdue,
    # SSoT bảo hành (CR-38) — cùng deriver màn quét-QR (build_asset_scan_info) cho
    # màn admin-detail (KHÔNG re-implement so-ngày / chuẩn-hoá date ở api layer).
    _is_warranty_expired,
    _date_str_or_none,
    ensure_asset_qr_token,
    build_asset_label_data,
    build_asset_label_data_batch,
    mark_label_printed as _svc_mark_label_printed,
    render_asset_labels_pdf as _svc_render_asset_labels_pdf,  # ADR-LABEL-PDF §D2 — render PDF nhãn QR khổ tem
    _LABEL_PRESETS,              # SSoT whitelist khổ tem (ADR-LABEL-PDF §D2 — preset lạ → 422)
    _resolve_label_preset,       # V3 §D14 — default preset từ site_config (hợp-lệ-hoá 1 chỗ, fallback an toàn)
    DEFAULT_LABEL_PRESET,        # V3 §D14 — fallback code-default khi config vắng/sai
    _MAX_LABEL_BATCH,            # SSoT cap số nhãn / 1 request (Vòng B — KHÔNG literal lặp)
    _ERR_BATCH_TOO_LARGE,        # message VI cố định cho 413 (nêu giới hạn, KHÔNG leak name)
    byt_expiry_filter,
    reserved_prefix_filter,      # SSoT loại asset rác test/security-audit (data-hygiene)
    compose_reserved_into,       # SSoT name-safe merge (FR-00-84 — KHÔNG clobber vendor-scope)
    escape_like_term,            # SSoT escape LIKE-metachar (FR-00-95 — '%'/'_' user gõ = literal)
    get_sla_policy,
    create_capa,
    close_capa,
    verify_audit_chain,
    _str_or_blank,               # SSoT coalesce '' (Vòng 16 — enrich phiếu Điều chuyển, NEVER raw Link-id)
    transfer_asset,
    create_transfer_request,
    approve_transfer_request,
    reject_transfer_request,
    confirm_receipt,
    cancel_transfer_request,
    transfer_cta_flags,
    _TRANSFER_EDIT_CAP,          # CR-WF-00-EDIT-AUTHZ — cap-SSoT gate update_transfer
    InvalidAssetTransition,
)

_DT_ASSET = "AC Asset"
_DT_DOWNTIME_LOG = "AC Asset Downtime Log"

# Vòng 12 B (BR-00-29) — ngưỡng rate-limit 2 endpoint QR deep-link resolve.
# 30 req/60s/IP/endpoint: ~2× headroom trên peak quét-rack (10–20 tb/phút), lỏng
# hơn login (5/60s — credential-guess) nhưng chặt hơn policy GET chung (300/60s)
# vì là deep-link bán-công-khai (token in trên nhãn). Token 128-bit
# (secrets.token_urlsafe(16)) → rate-limit là defense-in-depth + chống DoS, KHÔNG
# phải hàng rào duy nhất. 1 định nghĩa duy nhất (KHÔNG literal rải rác). Xem
# docs/imm-00/05 §I.7a.
AC_QR_RESOLVE_RATE_LIMIT = 30

# Vòng 27 B (BR-00-38) — ngưỡng rate-limit endpoint GHI rotate
# `regenerate_asset_qr_token`. Hằng RIÊNG (KHÔNG tái dùng AC_QR_RESOLVE_RATE_LIMIT):
# rotate hiếm hơn quét (deliberate admin action ứng phó lộ token), blast-radius lớn
# nhất (vô hiệu hoá MỌI nhãn QR đã in + write-amplification ALE/audit) → ngưỡng
# THẤP hơn resolve (10 req/60s/IP) do BA chốt. Bucket RIÊNG: frappe rate_limiter
# cache key gồm `frappe.form_dict.cmd` ⟹ counter rotate TÁCH BIỆT resolve/scan
# (KHÔNG chung). Decorator bọc NGOÀI thân hàm → 429 raise TRƯỚC rbac.require ⇒ vượt
# ngưỡng = KHÔNG side-effect (0 token mới, 0 ALE qr_regenerated, 0 audit), no-leak.
# Đóng bất đối xứng read-throttled (BR-00-29) / write-rotate-unthrottled
# (Self-Correction đảo quyết định Vòng 12). Xem docs/imm-00/04 §II.1.8d + 02 BR-00-38.
AC_QR_REGEN_RATE_LIMIT = 10

# ADR-IMM00-LABEL-PDF §D6 — ngưỡng rate-limit endpoint sinh PDF nhãn QR
# `print_asset_labels_pdf`. Hằng RIÊNG (KHÔNG tái dùng resolve/regen): render
# wkhtmltopdf tốn CPU (mỗi call N trang + N QR SVG) → ngưỡng THẤP hơn resolve
# (20 req/60s/IP) do BA chốt. Bucket RIÊNG: frappe rate_limiter cache key gồm
# `cmd` ⟹ counter TÁCH BIỆT resolve/scan/regen. Decorator bọc NGOÀI thân hàm →
# 429 raise TRƯỚC rbac.require ⇒ vượt ngưỡng = 0 render PDF, no-leak.
AC_LABEL_PDF_RATE_LIMIT = 20

# Vòng 14 (BR-00-45 / FR-00-96 — Self-Correction, mirror rotate) — ngưỡng rate-limit
# endpoint GHI `mark_label_printed`. Hằng RIÊNG (KHÔNG tái dùng resolve/regen/pdf):
# mark = thao-tác-GHI write-AUDIT-amplification (mỗi call N asset ghi 2×N record =
# N ALE `label_printed` + N IMM Audit Trail → bơm phồng audit-chain NĐ98 + tải DB)
# → ngưỡng THẤP, ≤ AC_QR_REGEN_RATE_LIMIT (mark CÙNG HỌ write-amplify như rotate).
# Bucket RIÊNG: frappe rate_limiter cache key gồm `frappe.form_dict.cmd` ⟹ counter
# TÁCH BIỆT resolve(30)/scan(30)/regen(10)/pdf(20)/batch(20). Decorator bọc NGOÀI
# thân hàm → 429 raise TRƯỚC rbac.require("asset.print") ⇒ vượt ngưỡng = 0 ALE
# `label_printed` + 0 IMM Audit Trail (no side-effect), no-leak body generic. Đóng
# bất đối xứng read-throttled-PDF / write-mark-unthrottled (BR-00-29 mục 6 đã thu
# hẹp). Xem docs/imm-00/05 §I.7c + 02 BR-00-45.
AC_LABEL_MARK_RATE_LIMIT = 10

# Vòng 14 (BR-00-46 / FR-00-97 — đồng-đề-mục BR-00-45) — ngưỡng rate-limit endpoint
# ĐỌC `get_asset_label_data_batch`. Hằng RIÊNG (KHÔNG tái dùng resolve/regen/pdf/
# mark — TÁCH BIỆT ngữ-nghĩa kể cả trùng giá-trị pdf): batch = read-only (0 side-
# effect) đọc N asset/call → ngưỡng CAO hơn mark (write-amplify), SONG SONG
# AC_LABEL_PDF_RATE_LIMIT=20 (đọc/render preview cùng tần-suất FE-batch). Bucket
# RIÊNG (cache key gồm `cmd`) ⟹ counter TÁCH BIỆT mark/pdf/resolve/regen. Decorator
# bọc NGOÀI thân → 429 raise TRƯỚC rbac.require("asset.print") ⇒ 0 byte payload
# build (`build_asset_label_data_batch` KHÔNG chạy), no-leak. Chặn DoS đọc batch.
# Xem docs/imm-00/05 §I.7c + 02 BR-00-46.
AC_LABEL_BATCH_RATE_LIMIT = 20

# Vòng 36 (BR-00-51 / FR-00-102) — ngưỡng rate-limit endpoint ĐỌC single
# `get_asset_label_data` (preview nhãn 1 asset). Hằng RIÊNG (KHÔNG tái dùng
# resolve/regen/pdf/mark/batch — TÁCH BIỆT ngữ-nghĩa kể cả khi trùng giá-trị
# batch/pdf=20): read-mostly preview FE màn in nhãn. ⚠ KHÔNG side-effect-free
# hoàn toàn: token-less asset → `ensure_asset_qr_token` (idempotent) GHI token +
# emit `qr_generated` (ALE + audit) → endpoint nếu KHÔNG throttle bị hammer ⇒
# write-amplification mint-token (bơm phồng audit-chain NĐ98). Đóng lỗ hổng cuối
# họ endpoint nhãn QR (parity batch/mark/pdf/resolve/regen). Giá-trị = 20 (đọc
# preview cùng tần-suất batch=20/pdf=20). Bucket RIÊNG: frappe rate_limiter cache
# key gồm `frappe.form_dict.cmd` ⟹ counter TÁCH BIỆT batch/mark/pdf/resolve/regen
# (1 endpoint vượt ngưỡng KHÔNG khoá endpoint khác). Decorator bọc NGOÀI thân →
# 429 raise TRƯỚC rbac.require("asset.print") ⇒ vượt ngưỡng = 0 byte payload build
# + 0 mint-token side-effect, no-leak. Xem docs/imm-00/05 §I.7c + 02 BR-00-51.
AC_LABEL_DATA_RATE_LIMIT = 20

# ADR-IMM00-LABEL-PDF §D7 — list rỗng → 422 (KHÔNG render PDF 0 trang). Message
# VI leak-safe (KHÔNG echo asset/id). SSoT 1 chỗ (KHÔNG literal lặp ở handler).
_ERR_LABEL_EMPTY = "Vui lòng chọn ít nhất một tài sản để in nhãn."
# §D5 — preset khổ tem không thuộc whitelist `_LABEL_PRESETS` → 422 (chống render
# khổ giấy tuỳ ý từ client). Message VI cố định, KHÔNG echo giá trị preset client.
_ERR_LABEL_PRESET = "Khổ tem không hợp lệ."
# §D16 — render PDF lỗi runtime (wkhtmltopdf/pdfkit/ảnh hỏng) → degrade VI sạch,
# KHÔNG để traceback 500 leak ra client (DONE-gate no-traceback-leak). Message
# khớp fallback FE `imm00.ts` ('Không thể tạo PDF nhãn…').
_ERR_LABEL_RENDER = "Không thể tạo PDF nhãn, vui lòng thử lại sau."


def _coerce_asset_names(assets) -> list[str]:
    """SSoT coerce tham số ``assets`` của 3 endpoint nhãn QR → ``list[str]`` an toàn (dedup within-call).

    Real HTTP (Frappe RPC form_dict) gửi ``assets`` dạng JSON-string; test/python
    gửi ``list``. Hàm nhận MỌI dạng đầu vào hợp-lệ-hoá về list tên-asset str
    non-empty, **KHÔNG BAO GIỜ raise** — malformed → ``[]`` (caller đi nhánh
    empty-path sẵn có: PDF/batch → 422 empty / batch rỗng; mark → 404/empty
    no-side-effect). Khoá 2 lớp lỗi cũ (LL-BE-42 no-500/no-traceback):

    - ``frappe.parse_json`` TRẦN trên mã thô/non-JSON (``'AC-2026-00001'``,
      ``''``, ``'   '``, ``'not-json'``) raise ``JSONDecodeError`` → HTTP-500 +
      traceback leak. Bọc try/except → ``[]``.
    - JSON-scalar-string (``'"AC-1"'`` → str ``'AC-1'``): nếu nhả nguyên str cho
      ``len()``/vòng-for thì DUYỆT từng KÝ TỰ (``'A','C','-','1'``) → 4 ô lỗi /
      4 lần ``frappe.db.exists`` / IDOR trên ký tự. Coi scalar (str/int/float/
      bool/dict/None) là 'không có asset hợp lệ' → ``[]``.
    - JSON-number/object/bool (``'123'``/``'{"a":1}'``/``'true'``) → int/dict/
      bool: ``len()``/iteration TypeError → 500. Cùng nhánh scalar → ``[]``.

    Chỉ 2 nguồn hợp lệ cho ra phần tử: (a) ``list`` truyền trực tiếp; (b) str
    parse ra ``list``. Cả 2 lọc về phần tử ``str`` non-empty (loại ``1``/``None``/
    ``''`` → KHÔNG đẩy giá trị lạ vào ``frappe.db.exists``/``assert_vendor_can_access``).

    **Dedup WITHIN-CALL** (Vòng 15): name LẶP trong CÙNG 1 call bị bỏ, GIỮ thứ tự
    xuất hiện đầu (``['AC-1','AC-1','AC-2','AC-1']`` → ``['AC-1','AC-2']``). 1 chỗ
    áp cho cả 3 endpoint ⇒ chặn khuếch-đại ghi-audit/PDF/batch (mark KHÔNG ghi
    N× ALE/audit trùng; PDF KHÔNG in N trang trùng; batch KHÔNG trả N entry trùng)
    + cap ``_MAX_LABEL_BATCH`` đo TRÊN list đã dedup (unique). **CHỈ trong-call** —
    KHÔNG xuyên-call: 2 lần gọi RIÊNG ``mark_label_printed([a1])`` VẪN ghi 2 event
    (mỗi lần in = 1 sự kiện, đúng nghiệp vụ NĐ98 — bất biến cross-call GIỮ NGUYÊN).

    Args:
        assets: list (tên asset) HOẶC JSON-string (array / scalar) HOẶC giá trị lạ.

    Returns:
        list[str]: tên-asset str non-empty, ĐÃ DEDUP within-call (giữ thứ tự xuất
        hiện đầu). Malformed → ``[]``.
    """
    if isinstance(assets, str):
        try:
            assets = frappe.parse_json(assets)
        except (ValueError, TypeError):
            # JSONDecodeError (subclass ValueError) hoặc input non-str → coi như []
            return []
    if not isinstance(assets, list):
        # scalar (str/int/float/bool/dict/None) hoặc parse ra non-list → không có asset
        return []
    # Dedup within-call GIỮ thứ tự xuất hiện đầu (seen.add trả None → giữ phần tử
    # lần đầu, loại mọi lần lặp sau). Lọc str non-empty TRƯỚC khi xét trùng.
    seen: set[str] = set()
    return [a for a in assets
            if isinstance(a, str) and a and a not in seen and not seen.add(a)]


_DT_SUPPLIER = "AC Supplier"
_DT_LOCATION = "AC Location"
_DT_DEPARTMENT = "AC Department"
_DT_ASSET_CATEGORY = "AC Asset Category"
_DT_DEVICE_MODEL = "IMM Device Model"
_DT_SLA_POLICY = "IMM SLA Policy"


def _strip_qr_token(doc):
    """SSoT no-raw-token (ADR-001 §D4 rule 9): bỏ key ``qr_token`` thô khỏi
    payload đọc AC Asset TRƯỚC khi rời BE.

    ``qr_token`` là khóa tra cứu MỜ (opaque) phục vụ nội bộ (before_insert sinh +
    ``_build_qr_url``/``build_asset_label_data`` dựng deep-link server-side). Token
    KHÔNG BAO GIỜ được surface thô qua endpoint đọc asset — FE chỉ cần ``qr_url``.
    ``frappe.get_doc(...).as_dict()`` lại trả nguyên field (dù DocType đặt
    hidden/read_only) ⇒ phải pop tường minh tại tầng API-response.

    Idempotent + None-safe: ``None`` → ``None``; dict không có ``qr_token`` →
    no-op. Mutate in-place (đủ cho luồng API) RỒI trả lại ``doc`` để gọi inline:
    ``return _ok(_strip_qr_token(doc))``. 1 helper DUY NHẤT cho MỌI đường đọc AC
    Asset trả ``as_dict()`` (KHÔNG inline ``pop`` lặp → chống regress khi thêm
    endpoint asset-read mới; AST guard test khẳng định).
    """
    if doc is None:
        return None
    doc.pop("qr_token", None)
    return doc


def _enrich(items: list, field: str, doctype: str, display_field: str,
            out_field: str = None, blank_missing: bool = False) -> None:
    """Batch-enrich a list of dicts with a display name for a linked field (avoids N+1).

    ``blank_missing`` (opt-in, default ``False`` — 15 caller cũ GIỮ NGUYÊN hành vi):
      - ``False`` (mặc định): mapping miss → fallback ``row.get(field)`` (raw Link-id)
        → ``""``; early-return khi cả trang không có ``field`` (khóa ``out`` vắng).
        Đây là semantics cũ, KHÔNG đổi (tránh hồi quy asset-list category/location/…).
      - ``True`` (Vòng 16 — phiếu Điều chuyển): coalesce ``''`` qua SSoT
        ``_str_or_blank`` (NEVER raw Link-id, NEVER ``None``) + LUÔN init khóa ``out``
        cho MỌI row (kể cả ``ids`` rỗng) → mỗi item đủ khóa denorm. Xem
        docs/imm-00 §II.1.13-TRANSFERENRICH / ADR-IMM00-TRANSFER-ENRICH.
    """
    out = out_field or f"{field}_name"
    ids = list({row.get(field) for row in items if row.get(field)})
    if not ids:
        if blank_missing:
            for row in items:
                row[out] = ""
        return
    table = f"tab{doctype}"
    placeholders = ", ".join(["%s"] * len(ids))
    rows = frappe.db.sql(
        f"SELECT `name`, `{display_field}` FROM `{table}` WHERE `name` IN ({placeholders})",
        ids,
    )
    mapping = {r[0]: r[1] for r in rows}
    for row in items:
        val = mapping.get(row.get(field))
        row[out] = _str_or_blank(val) if blank_missing else (val or row.get(field) or "")
_DT_AUDIT_TRAIL = "IMM Audit Trail"
_DT_CAPA = "IMM CAPA Record"
_DT_LIFECYCLE_EVENT = "Asset Lifecycle Event"
_DT_INCIDENT = "Incident Report"
_DT_TRANSFER = "Asset Transfer"
_DT_SERVICE_CONTRACT = "Service Contract"

_ERR_TRANSFER_NOT_FOUND = "Asset Transfer không tồn tại"
_ERR_CONTRACT_NOT_FOUND = "Service Contract không tồn tại"

_ERR_ASSET_NOT_FOUND = "Asset không tồn tại"

# B2 — ánh xạ fieldname (reqd=1 trên AC Asset) → nhãn VI thân thiện. Dùng để
# pre-validate mandatory TRƯỚC doc.insert() và để map MandatoryError → message VI
# sạch (KHÔNG lộ dev-string '[AC Asset, AC-ASSET-2026-#####]: asset_category').
# Chỉ liệt kê field người dùng có thể bỏ trống thực tế (naming_series xử lý trong
# autoname; status/lifecycle_status có default JSON ⇒ không bao giờ MandatoryError).
_ASSET_REQD_LABELS_VI = {
    "asset_name": "Tên tài sản",
    "asset_category": "Danh mục thiết bị",
}
_ERR_SUPPLIER_NOT_FOUND = "Nhà cung cấp không tồn tại"
_ERR_DEVICE_MODEL_NOT_FOUND = "Device Model không tồn tại"
_ERR_AUDIT_NOT_FOUND = "Audit Trail entry không tồn tại"
_ERR_CAPA_NOT_FOUND = "CAPA Record không tồn tại"
_ERR_LIFECYCLE_NOT_FOUND = "Lifecycle Event không tồn tại"
_ERR_INCIDENT_NOT_FOUND = "Incident Report không tồn tại"

_ORDER_EVENT_TS_DESC = "timestamp desc"
_ORDER_MODIFIED_DESC = "modified desc"
_ORDER_DUE_DATE_ASC  = "due_date asc"


def _safe_page_int(value, default: int) -> int:
    """Coerce page/page_size pagination param sang int AN TOÀN cho list_assets.

    Frappe form_dict đưa query-string vào dưới dạng str (hoặc None khi param
    vắng). ``int('abc')`` / ``int('10.5')`` raise ValueError, ``int(None)`` raise
    TypeError ⇒ HTTP-500 traceback rò ra envelope. Helper này chặn nhánh phi-số:
    giá trị KHÔNG ép được về int (None / '' / 'abc' / '10.5' / whitespace-rỗng)
    → fall-back ``default`` (KHÔNG throw). Số HỢP LỆ giữ nguyên hành vi cũ; chuỗi
    số có whitespace bao quanh ('  3  ') được strip rồi parse (parity name/preset
    whitespace-norm).

    KHÔNG clamp ở đây — clamp [1, _MAX_PAGE_SIZE] vẫn do paginate() đảm nhận (1
    SSoT). Vì vậy '9999'→9999 (paginate clamp→100), '-5'→-5 (paginate clamp→1):
    parity round-5 page_size-cap GIỮ NGUYÊN.

    KHU TRÚ: chỉ list_assets (đường QR-asset) dùng helper này — KHÔNG đụng 9
    call-site int(page) khác (timeline/suppliers/device-models/audit/capa/
    lifecycle/incidents) vốn nhận param number do FE kiểm soát.
    """
    if value is None:
        return default
    if isinstance(value, bool):
        # bool là subclass của int trong Python; coi như phi-số → default.
        return default
    if isinstance(value, int):
        return value
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return default


# ─────────────────────────────────────────────────────────────────────────────
# AC Asset  (8 endpoints)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_assets(
    page: "int" = 1,
    page_size: "int" = 20,
    lifecycle_status: str = None,
    department: str = None,
    location: str = None,
    asset_category: str = None,
    search: str = None,
    gmdn_code: str = None,
    byt_status: str = None,
):
    """GET /api/method/assetcore.api.imm00.list_assets

    byt_status (NĐ98 drill, BR-00-17): 'expiring' | 'expired' → áp SoT
    byt_expiry_filter(byt_status) HỢP NHẤT (AND) với mọi filter hiện có. Giá trị
    khác → no-op (bỏ qua, không throw). Count get_overview().assets.byt_* ==
    total list này khi cùng bucket (INVARIANT count==drill).

    INVARIANT pagination.total == len(items) (cộng dồn qua các trang) — ENFORCED
    cho MỌI persona (ADR-IMM00-LIST-SCOPE): count (count_with_or) và items
    (frappe.get_list) dùng CÙNG ``filters``/``or_filters`` VÀ CÙNG
    ``permission_query_conditions`` (count qua frappe.get_list, KHÔNG db.count/
    get_all). Row-scope:
      • Senior / Auditor / Internal technician (PM/Repair/Calibration/Corrective
        User) → read-all (ac_asset_query="").
      • Vendor Engineer → isolated: responsible_technician=<user> (ac_asset_query)
        ∩ asset-được-giao-qua-WO (apply_vendor_scope) — count==rows giữ vì cả 2
        lớp áp cho count lẫn list.
    Reserved-prefix exclusion ('_' / 'SI-') + apply_vendor_scope (RC-LIST-
    VENDORCLOBBER) giữ nguyên — fix này CỘNG THÊM permission-awareness vào count.

    search (free-text, FR-00-95 / BR-00-44 / ADR-IMM00-SEARCH-ESCAPE): đi qua
    escape_like_term (SSoT) → '%'/'_'/'\\' user gõ là KÝ TỰ LITERAL (không phải
    wildcard SQL): search='_'/'%' KHÔNG over-match toàn bảng, search='\\' KHÔNG
    throw, '%%%%%%%%%%' finite (đóng LIKE-backtracking DoS surface). Escape áp CÙNG
    or_filters cho cả count (count_with_or) lẫn items (get_list) ⟹ INVARIANT
    total==len(items) giữ. SQLi-safe BẤT BIẾN (parametrized — escape TRƯỚC bind).

    page / page_size (FR-00-LIST-SCOPE coercion): form_dict đưa query-string là
    str (hoặc None khi vắng). Annotation CHỦ Ý viết dạng CHUỖI ``"int"`` (KHÔNG
    real-type ``int``) — module này KHÔNG có ``from __future__ import annotations``
    nên annotation giữ NGUYÊN là chuỗi runtime. Tác động kép & cố ý:
      (1) @frappe.whitelist() → transform_parameter_types: gặp annotation kiểu
          str/ForwardRef thì ``continue`` (BỎ QUA pydantic-cast) ⇒ '?page=abc'/
          'page_size=10.5' KHÔNG còn raise FrappeTypeError (HTTP-417/500) ở lớp
          decorator → chuỗi phi-số đi LỌT vào thân để _safe_page_int xử lý.
      (2) OpenAPI generator (_json_type_for): chuỗi 'int' → _TYPE_MAP → 'integer'
          ⇒ OAS contract page/page_size GIỮ type:integer (regression A2 mobile-BE
          codegen KHÔNG vỡ). KHÔNG được đổi về real-type ``int`` (sẽ bật lại
          pydantic-reject) hay bỏ annotation (OAS rớt về 'string').
    _safe_page_int → phi-số ('abc'/'10.5'/''/None) fall-back default (page=1,
    page_size=20) thay vì ném ValueError/TypeError ⇒ HTTP-500. Clamp
    [1, _MAX_PAGE_SIZE] VẪN do paginate() đảm nhận (1 SSoT) ⇒ '9999'→100, '-5'→1,
    '  3  '→3. Coercion CHỈ đụng 2 param số — KHÔNG đụng filters/or_filters/
    permission_query_conditions ⇒ INVARIANT total==len(items) GIỮ NGUYÊN mọi persona.
    """
    page = _safe_page_int(page, 1)
    page_size = _safe_page_int(page_size, 20)
    filters = {}
    if lifecycle_status:
        filters["lifecycle_status"] = lifecycle_status
    if department:
        filters["department"] = department
    if location:
        filters["location"] = location
    if asset_category:
        filters["asset_category"] = asset_category
    if gmdn_code:
        filters["gmdn_code"] = gmdn_code
    if byt_status:
        # SoT predicate — merge AND, KHÔNG clobber field khác (byt_reg_expiry là
        # field riêng). bucket không hợp lệ → byt_expiry_filter trả {} (no-op).
        filters.update(byt_expiry_filter(byt_status))

    # AUTH-01: Vendor Engineer chỉ thấy asset được giao việc. Với Vendor Engineer,
    # apply_vendor_scope đặt filters["name"] = ["in", assigned] (field-map AC Asset →
    # "name", scope.py). KHÔNG được merge reserved-exclusion bằng dict.update sau đó
    # (cùng key "name" → ghi đè → mất vendor-scope = RC-LIST-VENDORCLOBBER, Vòng 26 B).
    filters = apply_vendor_scope(filters, _DT_ASSET)

    # Data-hygiene + AUTH-01 name-safe compose (FR-00-84 / BR-00-35 mục 6): loại asset
    # rác test ('_…') + security-audit ('SI-…') BẰNG filter-list form qua SSoT helper
    # compose_reserved_into() — KHÔNG dict.update. Helper chuyển filters dict (kể cả
    # khi đã có "name in assigned" từ vendor-scope) sang list-of-conditions rồi THÊM
    # dòng RIÊNG ["name","not in",reserved]; hai điều kiện "name" cùng tồn tại, ANDed
    # → predicate hiệu dụng name ∈ (assigned ∖ reserved). 1 NGUỒN predicate cho CẢ
    # count (count_with_or/db.count) lẫn get_list ⇒ INVARIANT total==len(items) giữ ở
    # MỌI persona (Administrator/bypass → name không có → chỉ "name not in reserved";
    # Vendor Engineer → "name in assigned" AND "name not in reserved"; empty-scope
    # → "name in [__none__]" → 0 row, KHÔNG fallback). DB sạch → bỏ dòng reserved (no-op).
    filters = compose_reserved_into(filters, _DT_ASSET)

    or_filters = None
    if search:
        # FR-00-95 / BR-00-44 (ADR-IMM00-SEARCH-ESCAPE): bọc search qua escape_like_term
        # (SSoT) → '%'/'_'/'\' user gõ là KÝ TỰ LITERAL, KHÔNG wildcard SQL. Chống
        # over-match toàn bảng (search='_'/'%' không match-all) + LIKE-backtracking DoS
        # ('%%%%%%%%%%' finite). 4 cột dùng CÙNG term đã-escape (1 lời gọi — KHÔNG rải
        # .replace thủ công). or_filters đi y nguyên cho CẢ count_with_or lẫn get_list
        # qua CÙNG động cơ DatabaseQuery ⟹ INVARIANT total==len(items) GIỮ mọi persona.
        like = f"%{escape_like_term(str(search))}%"
        or_filters = [
            [_DT_ASSET, "asset_name",      "like", like],
            [_DT_ASSET, "asset_code",      "like", like],
            [_DT_ASSET, "manufacturer_sn", "like", like],
            [_DT_ASSET, "gmdn_code",       "like", like],
        ]

    # Count dùng CHUNG filters (đã gồm data-hygiene + vendor-scope) + or_filters
    # qua count_with_or → ĐÚNG cùng engine (DatabaseQuery), cùng predicate VÀ cùng
    # permission_query_conditions (ac_asset_query) với get_list bên dưới ⇒ INVARIANT
    # total == len(items) cho CẢ search & non-search path & MỌI persona (ADR-IMM00-
    # LIST-SCOPE §4b — count_with_or nay đếm qua frappe.get_list, KHÔNG db.count).
    total = count_with_or(_DT_ASSET, filters, or_filters)

    pag = paginate(int(total), page, page_size)

    fields = [
        "name", "asset_name", "asset_code", "lifecycle_status",
        "asset_category", "location", "department", "responsible_technician",
        "supplier", "device_model",
        "next_pm_date", "next_calibration_date", "byt_reg_expiry",
        "gmdn_code",
        "gross_purchase_amount", "accumulated_depreciation", "current_book_value",
    ]
    items = frappe.get_list(
        _DT_ASSET,
        filters=filters,
        or_filters=or_filters if or_filters else None,
        fields=fields,
        limit_start=pag["offset"],
        limit_page_length=pag["page_size"],
        order_by=_ORDER_MODIFIED_DESC,
    )
    _enrich(items, "asset_category", _DT_ASSET_CATEGORY, "category_name")
    _enrich(items, "department", _DT_DEPARTMENT, "department_name")
    _enrich(items, "location", _DT_LOCATION, "location_name")
    _enrich(items, "supplier", _DT_SUPPLIER, "supplier_name")
    _enrich(items, "device_model", _DT_DEVICE_MODEL, "model_name", out_field="device_model_name")
    _enrich(items, "responsible_technician", "User", "full_name", out_field="responsible_technician_name")
    return _ok({"pagination": pag, "items": items})


@frappe.whitelist()
def get_asset(name: str):
    """GET /api/method/assetcore.api.imm00.get_asset?name=AC-ASSET-...

    Bảo mật — 3 lớp theo thứ tự (parity get_asset_scan_info / resolve_qr_token):
      0. ``rbac.require("asset.read")`` chạy ĐẦU TIÊN → user thiếu DocPerm read
         AC Asset → ``frappe.PermissionError`` (HTTP 403). Gate bằng CAPABILITY
         (DocPerm), KHÔNG hardcode role-name. Chạy TRƯỚC ``frappe.db.exists`` →
         no existence-oracle (thiếu cap → 403, KHÔNG 404 — user không dò được
         tài sản có tồn tại). RC: ``frappe.get_doc(...).as_dict()`` trên whitelist
         method KHÔNG tự enforce read-DocPerm → nếu thiếu gate này, user thiếu
         read vẫn đọc trọn doc qua endpoint QR-detail (đối xứng sibling read).
      1. exists → ``_err(404)`` leak-safe (name không tồn tại).
      2. IDOR/vendor isolation: ``assert_vendor_can_access`` → vendor ngoài scope
         → 403, KHÔNG leak payload (KHÔNG re-implement).
    Sau 3 lớp: strip qr_token (no-raw-token ADR-001 §D4) + 2 cờ overdue server-flag.
    """
    # 0. RBAC gate — require asset.read (DocPerm AC Asset). PermissionError → 403.
    #    TRƯỚC exists → no existence-oracle (parity scan_info/resolve_qr_token).
    rbac.require("asset.read")
    if not frappe.db.exists(_DT_ASSET, name):
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)
    # AUTH-10: IDOR guard — vendor user can't read assets outside their scope.
    try:
        assert_vendor_can_access(_DT_ASSET, name)
    except ServiceError as e:
        return _err(e.message, e.code)
    doc = frappe.get_doc(_DT_ASSET, name).as_dict()
    # Enrich linked display names
    if doc.get("asset_category"):
        doc["category_name"] = frappe.db.get_value(_DT_ASSET_CATEGORY, doc["asset_category"], "category_name") or ""
    if doc.get("department"):
        doc["department_name"] = frappe.db.get_value(_DT_DEPARTMENT, doc["department"], "department_name") or ""
    if doc.get("location"):
        doc["location_name"] = frappe.db.get_value(_DT_LOCATION, doc["location"], "location_name") or ""
    if doc.get("supplier"):
        doc["supplier_name"] = frappe.db.get_value(_DT_SUPPLIER, doc["supplier"], "supplier_name") or ""
    if doc.get("device_model"):
        doc["device_model_name"] = frappe.db.get_value(_DT_DEVICE_MODEL, doc["device_model"], "model_name") or ""
    if doc.get("responsible_technician"):
        doc["responsible_technician_name"] = frappe.db.get_value("User", doc["responsible_technician"], "full_name") or ""
    # SSoT overdue (server-flag) — derive 2 cờ bằng CHÍNH deriver của màn quét-QR
    # (_is_pm_overdue/_is_calibration_overdue): tz-safe (getdate server, STRICT <)
    # + exempt BLOCKED_FOR_WO (Out of Service / Decommissioned → cờ=False dù ngày
    # quá khứ). KHÔNG re-implement so ngày ở đây ⇒ màn admin-detail & màn quét-QR
    # CÙNG 1 kết luận overdue. FE CHỈ render cờ — KHÔNG so ngày client (chống
    # tz-drift). next_pm_date/next_calibration_date đọc từ doc (đã as_dict).
    _status = doc.get("lifecycle_status")
    doc["pm_overdue"] = _is_pm_overdue(doc.get("next_pm_date"), _status)
    doc["calibration_overdue"] = _is_calibration_overdue(
        doc.get("next_calibration_date"), _status)
    # Parity BẢO HÀNH với get_asset_scan_info (CR-38) — server-flag SSoT. as_dict()
    # leak warranty_expiry_date NGUYÊN datetime.date object → chuẩn-hoá 'YYYY-MM-DD'|
    # None qua _date_str_or_none (KHÔNG rò date thô ra JSON). warranty_expired derive
    # SERVER-SIDE qua CHÍNH _is_warranty_expired (STRICT < theo NGÀY server, tz-safe;
    # null/tương-lai/hôm-nay → False) — KHÔNG re-implement so-ngày ⇒ màn admin-detail
    # & màn quét-QR CÙNG 1 kết luận. ĐỘC LẬP lifecycle_status (no-exempt — bảo hành là
    # sự kiện HỢP ĐỒNG). FE CHỈ render cờ — KHÔNG so ngày client.
    _warranty_raw = doc.get("warranty_expiry_date")
    doc["warranty_expired"] = _is_warranty_expired(_warranty_raw)
    doc["warranty_expiry_date"] = _date_str_or_none(_warranty_raw)
    # Server-driven CTA (CR-WF-00-LIFECYCLE-SURFACE, Trục A) — allowed_transitions =
    # tập trạng-thái-đích CTA-surfaceable (SSoT asset_allowed_transitions:
    # _VALID_ASSET_TRANSITIONS − EXCEPTION − terminal Decommissioned) LỌC theo
    # capability caller. FE dựng nút chuyển-trạng-thái CHỈ từ field này (xoá bảng
    # TRANSITION_MAP hardcode → 0 bản sao drift). Caller thiếu asset.write (read-only
    # DocPerm) → [] ⇒ FE ẩn khối CTA. Thanh lý (→Decommissioned) KHÔNG bao giờ ở đây
    # — đi qua cổng IMM-14 riêng (đối xứng precedent firmware_allowed_transitions).
    doc["allowed_transitions"] = (
        asset_allowed_transitions(_status or "") if rbac.can("asset.write") else []
    )
    # No-raw-token (ADR-001 §D4 rule 9): qr_token là khóa tra cứu MỜ nội bộ —
    # KHÔNG surface thô qua endpoint đọc asset (deep-link dùng qr_url server-side).
    # as_dict() leak nguyên field dù hidden/read_only → pop qua SSoT trước return.
    return _ok(_strip_qr_token(doc))


# SSoT 6 key panel meta thiết bị (màn tạo WO: CM / Hiệu chuẩn / PM). Cố định, KHÔNG
# kế thừa as_dict() đầy đủ → đóng over-fetch field tài chính/nhạy cảm
# (gross_purchase_amount, accumulated_depreciation, current_book_value, purchase_cost,
# salvage_value) + qr_token + audit-chain. FE chỉ render 5 dòng (name là khóa nội bộ).
_ASSET_ACTION_META_KEYS = (
    "name",
    "asset_name",
    "device_model_name",
    "lifecycle_status",
    "risk_classification",
    "location_name",
)


@frappe.whitelist()
def get_asset_action_meta(name: str = ""):
    """GET — panel META NẠC cho 3 màn tạo WO (CM/Hiệu chuẩn/PM).

    Trả ĐÚNG 6 key cố định (``_ASSET_ACTION_META_KEYS``) — KHÔNG over-fetch field
    tài chính/nhạy cảm như ``get_asset`` (full doc rò ``gross_purchase_amount`` /
    ``accumulated_depreciation`` / ``current_book_value`` / ``purchase_cost`` /
    ``salvage_value`` / ``qr_token`` / audit-chain). FE panel chỉ render 5 dòng
    (asset_name / device_model_name / location_name / lifecycle_status /
    risk_classification); ``name`` là khóa nội bộ.

    Bảo mật — 3 lớp ĐỒNG NHẤT thứ tự với ``get_asset`` (KHÔNG nới):
      0. ``rbac.require("asset.read")`` chạy ĐẦU TIÊN (CÂU LỆNH ĐẦU thân hàm) →
         user thiếu DocPerm read AC Asset → ``frappe.PermissionError`` (HTTP 403).
         Gate bằng CAPABILITY (DocPerm), KHÔNG hardcode role-name. Chạy TRƯỚC
         ``frappe.db.exists`` → no existence-oracle: user thiếu cap KHÔNG dò được
         tài sản tồn tại hay không qua endpoint meta NẠC này (parity get_asset /
         get_asset_scan_info / resolve_qr_token). Nếu thiếu gate này, ``get_doc``
         chỉ enforce DocPerm SAU exists → tên-không-tồn-tại trả 404 còn tên-tồn-tại
         trả 403 ⇒ rò sự tồn tại của asset cho user thiếu read.
      1. name rỗng/None hoặc không tồn tại → ``_err(404)`` leak-safe (KHÔNG 500/
         traceback, KHÔNG full-scan). Chỉ tới đây sau khi user ĐÃ có asset.read.
      2. IDOR/vendor isolation: ``assert_vendor_can_access(_DT_ASSET, name)`` → vendor
         ngoài scope → 403, KHÔNG leak payload (tái dùng, KHÔNG re-implement).

    Enrich: ``device_model_name`` / ``location_name`` resolve từ Link
    (``device_model`` → IMM Device Model.model_name; ``location`` → AC Location.
    location_name). Asset thiếu link/risk → field "" (KHÔNG None — tránh vỡ FE).
    """
    # 0. RBAC gate — require asset.read (DocPerm AC Asset). PermissionError → 403.
    #    CÂU LỆNH ĐẦU TIÊN, TRƯỚC exists → no existence-oracle (parity get_asset).
    rbac.require("asset.read")
    if not name or not frappe.db.exists(_DT_ASSET, name):
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)
    # IDOR guard — vendor user không được đọc asset ngoài scope (parity get_asset).
    try:
        assert_vendor_can_access(_DT_ASSET, name)
    except ServiceError as e:
        return _err(e.message, e.code)
    # DocPerm read enforce qua get_doc().has_permission (PermissionError → 403) —
    # KHÔNG dùng frappe.db.get_value bỏ qua perm. Chỉ pull field cần cho panel.
    doc = frappe.get_doc(_DT_ASSET, name)
    device_model = doc.get("device_model")
    location = doc.get("location")
    device_model_name = (
        frappe.db.get_value(_DT_DEVICE_MODEL, device_model, "model_name") or ""
    ) if device_model else ""
    location_name = (
        frappe.db.get_value(_DT_LOCATION, location, "location_name") or ""
    ) if location else ""
    meta = {
        "name": doc.name,
        "asset_name": doc.get("asset_name") or "",
        "device_model_name": device_model_name,
        "lifecycle_status": doc.get("lifecycle_status") or "",
        "risk_classification": doc.get("risk_classification") or "",
        "location_name": location_name,
    }
    # Guard cứng: payload CHỈ gồm 6 key allowlist (chống regress over-fetch nếu sửa sau).
    return _ok({k: meta[k] for k in _ASSET_ACTION_META_KEYS})


@frappe.whitelist()
@rate_limit(limit=AC_QR_RESOLVE_RATE_LIMIT, seconds=60, ip_based=True)  # Vòng 12 B — 429 TRƯỚC rbac.require (BR-00-29)
def resolve_qr_token(token: str = ""):
    """GET — A2 (ADR-001 D4): tra mã QR (deep-link /a/<token>) → định danh asset.

    Flow màn QrResolveView (FE): quét/mở /a/<token> → gọi endpoint NÀY → thành
    công thì điều hướng /assets/<name> (màn info đầy đủ là A6/V7). A2 CHỈ
    resolve + định danh + field hiển thị tối thiểu, KHÔNG trả toàn bộ asset.

    Bảo mật (theo thứ tự, ADR-001 D4):
      0. ``@rate_limit(30/60s/IP)`` (Vòng 12 B, BR-00-29) — decorator bọc NGOÀI
         thân hàm → frappe tăng counter rồi ``frappe.throw(RateLimitExceededError)``
         (HTTP 429) TRƯỚC khi thân hàm chạy ⇒ TRƯỚC ``rbac.require``. Chống
         brute-force token + DoS (entry-point camera điện thoại ``/a/<token>``).
         No-leak parity: 429 body generic, KHÔNG build byte payload nào. Đếm MỌI
         call (kể cả 404/403 → chống enumeration). KHÔNG-HTTP context (test/CLI)
         bypass có chủ đích (``if not frappe.request: return fn``).
      1. ``rbac.require("asset.read")`` → user KHÔNG có DocPerm read AC Asset →
         ``frappe.PermissionError`` (HTTP 403). Gate bằng CAPABILITY (DocPerm),
         KHÔNG hardcode role-name (chống RBAC dead-gate). NĐ98: KHÔNG public.
      2. token rỗng/None hoặc không khớp asset nào → 404 leak-safe (KHÔNG 500,
         KHÔNG phân biệt "sai định dạng" vs "không tồn tại", KHÔNG full-scan).
      3. IDOR/vendor isolation: tái dùng ``assert_vendor_can_access`` (KHÔNG
         re-implement) → vendor resolve token asset NGOÀI scope → 403, KHÔNG leak
         payload.
      4. Read-only → KHÔNG ghi audit/lifecycle (chống spam chain mỗi lần quét —
         qr_generated/label_printed mới ghi, xem A1/A4).
    """
    # 1. RBAC gate — require asset.read (DocPerm AC Asset). PermissionError → 403.
    rbac.require("asset.read")
    # 2. Resolve token → payload tối thiểu (None nếu rỗng/không tồn tại → 404 no-leak).
    payload = _svc_resolve_qr_token(token if isinstance(token, str) else "")
    if not payload:
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)
    # 3. IDOR guard — vendor không được giao việc trên asset → 403, KHÔNG leak payload.
    try:
        assert_vendor_can_access(_DT_ASSET, payload["name"])
    except ServiceError as e:
        return _err(e.message, e.code)
    # 4. Read-only — KHÔNG audit. Trả định danh + field hiển thị tối thiểu.
    return _ok(payload)


@frappe.whitelist()
@rate_limit(limit=AC_QR_RESOLVE_RATE_LIMIT, seconds=60, ip_based=True)  # Vòng 12 B — bucket RIÊNG (cache key gồm cmd), 429 TRƯỚC rbac.require
def get_asset_scan_info(token: str = "", name: str = ""):
    """GET — A6: payload màn THÔNG TIN thiết bị mobile-first khi quét QR.

    Deep-link landing (route ``AssetScanInfo`` — ``/scan/:token`` / ``/assets/:id/info``)
    gọi endpoint NÀY để dựng màn info read-only: định danh + model + vị trí +
    lifecycle_status (mã canonical — FE dịch nhãn VI qua SSoT) + bảo trì gần nhất
    + next_pm_date. Resolve theo ``token`` (deep-link QR) HOẶC ``name`` (điều hướng
    nội bộ list/desktop). KHÔNG trả field nhạy cảm (giá mua, khấu hao, audit chain,
    supplier code).

    Bảo mật (theo thứ tự, đồng nhất A2 — ADR-001 D4):
      0. ``@rate_limit(30/60s/IP)`` (Vòng 12 B, BR-00-29) — bucket RIÊNG với
         ``resolve_qr_token`` (cache key gồm ``cmd``). 429 TRƯỚC ``rbac.require``,
         no-leak parity (KHÔNG lộ asset name/lifecycle). Chống brute-force token +
         DoS (entry-point camera điện thoại ``/scan/:token``).
      1. ``rbac.require("asset.read")`` → user KHÔNG có DocPerm read AC Asset →
         ``frappe.PermissionError`` (HTTP 403). Gate bằng CAPABILITY (DocPerm),
         KHÔNG hardcode role-name. KHÔNG cấp cap/DocType mới (tái dùng asset.read).
      2. token/name rỗng/None hoặc không khớp asset → 404 leak-safe (KHÔNG 500,
         KHÔNG phân biệt "sai định dạng" vs "không tồn tại", KHÔNG full-scan).
      3. IDOR/vendor isolation: tái dùng ``assert_vendor_can_access`` (KHÔNG
         re-implement) → vendor ngoài scope → 403, KHÔNG leak payload.
      4. Read-only → KHÔNG ghi audit/lifecycle (chống spam chain mỗi lần quét).
    """
    # 1. RBAC gate — require asset.read (DocPerm AC Asset). PermissionError → 403.
    rbac.require("asset.read")
    # 2. Resolve định danh asset: ưu tiên token (deep-link QR), fallback name.
    #    Cả hai → name asset hoặc None (404 no-leak, KHÔNG phân biệt nhánh).
    token = token if isinstance(token, str) else ""
    name = name if isinstance(name, str) else ""
    # Parity nhánh token (Vòng 6 — `_svc_resolve_qr_token` đã `.strip()` SSoT):
    # chuẩn-hoá `name` bằng strip 2 đầu TRƯỚC `frappe.db.exists`. Asset hợp lệ
    # kèm leading/trailing whitespace/newline (deep-link /assets/:id/info,
    # copy-paste, mobile-BE) → khớp exists → mở ĐÚNG hồ sơ (200) thay vì 404 giả.
    # CHỈ strip 2 đầu (KHÔNG lowercase/transform giữa-chuỗi — KHÔNG over-normalize;
    # space GIỮA = id hỏng thật → vẫn 404). Rỗng-sau-strip rơi guard `elif name`
    # → asset_name=None → 404 no-leak, KHÔNG query exists (chống full-scan).
    name = name.strip()
    asset_name = None
    if token:
        resolved = _svc_resolve_qr_token(token)
        if resolved:
            asset_name = resolved.get("name")
    elif name and frappe.db.exists(_DT_ASSET, name):
        asset_name = name
    if not asset_name:
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)
    # 3. IDOR guard — vendor không được giao việc trên asset → 403, KHÔNG leak payload.
    try:
        assert_vendor_can_access(_DT_ASSET, asset_name)
    except ServiceError as e:
        return _err(e.message, e.code)
    # 4. Read-only — KHÔNG audit. Trả payload mobile cốt lõi.
    payload = _svc_build_asset_scan_info(asset_name)
    if not payload:
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)
    return _ok(payload)


@frappe.whitelist()
@rate_limit(limit=AC_LABEL_DATA_RATE_LIMIT, seconds=60, ip_based=True)  # Vòng 36 / BR-00-51 — 429 TRƯỚC rbac.require; bucket RIÊNG (cmd), read-mostly preview; đóng write-amplification mint-token (ensure_asset_qr_token emit qr_generated)
def get_asset_label_data(asset: str = ""):
    """GET — A3 (ADR-001 D3): dữ liệu in nhãn QR cho 1 asset (READ-ONLY về print).

    FE màn in nhãn (A4/V5) gọi để dựng payload tem + ``QRLabel`` encode URL
    ``/a/<token>``. KHÔNG phải sự kiện in — chỉ lấy dữ liệu (KHÔNG emit
    ``label_printed``/audit; preview ≠ in, chống spam chain — D3/D4).

    Bảo mật (theo thứ tự):
      0. ``@rate_limit(AC_LABEL_DATA_RATE_LIMIT/60s/IP)`` (Vòng 36, BR-00-51) —
         decorator bọc NGOÀI thân → frappe tăng counter + ``frappe.throw(
         RateLimitExceededError)`` (429) TRƯỚC ``rbac.require`` ⇒ vượt ngưỡng = 0
         byte payload build + 0 mint-token side-effect (``ensure_asset_qr_token``
         KHÔNG chạy → 0 ``qr_generated`` ALE/audit). Đóng write-amplification do
         mint-token bị hammer không giới hạn. Bucket RIÊNG (cache key gồm ``cmd``)
         TÁCH BIỆT batch/mark/pdf/resolve/regen → 1 endpoint vượt ngưỡng KHÔNG
         khoá endpoint khác. read-mostly preview → ngưỡng song song batch/pdf=20.
      1. ``rbac.require("asset.print")`` → PermissionError (403). ADR-IMM00-QR-
         SCAN-ACTION D6 (Accepted→EXECUTED, phương án B): TÁCH cap riêng
         ``asset.print``→(AC Asset,"print") thay ``asset.write`` (vốn chỉ Super
         Admin có → KTV/QL vật tư KHÔNG in được — self-correction P2). Resolve
         ``has_permission("AC Asset","print")``: DocPerm print=1 sẵn cho ~mọi role
         vận hành ⇒ in được NGAY (KHÔNG đổi DocPerm). User KHÔNG có print → 403.
         (Cap mới ⇒ ``CAP_SET_VERSION`` ĐỔI ``v95.3388ee5629c1``→
         ``v104.e46d05d9a66d`` — FE auto-invalidate persisted-caps stale.)
      2. asset rỗng/không tồn tại → 404 leak-safe (KHÔNG 500, KHÔNG đoán id).
      3. IDOR: ``assert_vendor_can_access`` → vendor ngoài scope → 403, KHÔNG leak.

    ``qr_url`` KHÔNG BAO GIỜ rỗng: token-less asset → ``ensure_asset_qr_token``
    (idempotent) trong service trước khi build (BR-00-28).
    """
    rbac.require("asset.print")
    if not asset or not frappe.db.exists(_DT_ASSET, asset):
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)
    try:
        assert_vendor_can_access(_DT_ASSET, asset)
    except ServiceError as e:
        return _err(e.message, e.code)
    return _ok(build_asset_label_data(asset))


@frappe.whitelist()
@rate_limit(limit=AC_LABEL_BATCH_RATE_LIMIT, seconds=60, ip_based=True)  # Vòng 14 / BR-00-46 — 429 TRƯỚC rbac.require; bucket RIÊNG (cmd), read-only ngưỡng cao hơn mark
def get_asset_label_data_batch(assets=None):
    """GET — A3 (ADR-001 D3): dữ liệu in nhãn QR hàng loạt (READ-ONLY, KHÔNG N+1).

    FE in hàng loạt (A4/V5) gọi 1 lần lấy payload N asset. Output theo ĐÚNG thứ
    tự input; asset không tồn tại → ``{"name": n, "error": "AC-E001"}`` tại đúng
    index (KHÔNG drop → giữ index FE). 1 truy vấn gộp + IN-clause cho enrich
    (KHÔNG loop get_value).

    Thứ tự gate (Vòng 14 / BR-00-46 — đo từng bậc):
      0. ``@rate_limit(AC_LABEL_BATCH_RATE_LIMIT/60s/IP)`` — decorator bọc NGOÀI
         thân → frappe tăng counter + ``frappe.throw(RateLimitExceededError)``
         (429) TRƯỚC ``rbac.require`` ⇒ vượt ngưỡng = 0 byte payload build
         (``build_asset_label_data_batch`` KHÔNG chạy), no-leak. Bucket RIÊNG
         (cache key gồm ``cmd``) TÁCH BIỆT mark/pdf/resolve/regen. read-only →
         ngưỡng CAO hơn mark (song song pdf=20).

    Bảo mật: ``rbac.require("asset.print")`` (403) — ADR-IMM00-QR-SCAN-ACTION D6
    (phương án B): TÁCH cap ``asset.print``→(AC Asset,"print") thay ``asset.write``
    (least-privilege; in nhãn = quyền PRINT, không phải WRITE toàn asset). DocPerm
    print=1 sẵn cho ~mọi role vận hành → in hàng loạt được NGAY. User KHÔNG có
    print → 403. (Cap mới ⇒ ``CAP_SET_VERSION`` ĐỔI →``v104.e46d05d9a66d``.) IDOR mỗi
    asset hợp lệ qua ``assert_vendor_can_access`` → vendor có ≥1 asset ngoài scope →
    403 TOÀN call (KHÔNG partial, KHÔNG leak asset nào thuộc/không-thuộc scope).

    ``assets`` coerce an toàn qua ``_coerce_asset_names`` (SSoT 3 endpoint):
    malformed (bare-code/non-JSON/scalar/int/dict) → ``[]`` → batch RỖNG hợp lệ
    (read-only) — KHÔNG HTTP-500, KHÔNG traceback/JSONDecodeError leak, KHÔNG
    duyệt ký-tự khi là JSON-scalar-string (ref LL-BE-42 no-500/no-traceback).
    Coerce DEDUP within-call (Vòng 15): name lặp trong CÙNG call → 1 entry (giữ
    thứ tự đầu) ⇒ ``[a1,a1]`` trả ĐÚNG 1 phần tử; cap đo TRÊN list đã dedup.
    """
    rbac.require("asset.print")
    # SSoT coerce an toàn — assets malformed (bare-code/non-JSON/scalar/int/dict)
    # → [] → batch rỗng hợp lệ (read-only, KHÔNG 500/leak). KHÔNG parse_json trần.
    names = _coerce_asset_names(assets)
    # CAP batch-size SAU rbac (chỉ user đã-auth-print tới đây — KHÔNG lộ giới hạn cho
    # khách) TRƯỚC vòng exists/IDOR + build payload → chặn per-request payload-DoS.
    # 413 bucket RIÊNG (PAYLOAD_TOO_LARGE), message VI cố định, KHÔNG leak asset name.
    if len(names) > _MAX_LABEL_BATCH:
        return _err(_(_ERR_BATCH_TOO_LARGE), 413)
    try:
        for n in names:
            if frappe.db.exists(_DT_ASSET, n):
                assert_vendor_can_access(_DT_ASSET, n)
    except ServiceError as e:
        return _err(e.message, e.code)
    return _ok(build_asset_label_data_batch(names))


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=AC_LABEL_MARK_RATE_LIMIT, seconds=60, ip_based=True)  # Vòng 14 / BR-00-45 — 429 TRƯỚC rbac.require; bucket RIÊNG (cmd), write-audit-amplification → ngưỡng thấp
def mark_label_printed(assets=None):
    """POST — A3 (ADR-001 D3): ghi sự kiện in nhãn QR (1 event+audit / asset / lần in).

    FE gọi SAU khi người dùng thực sự bấm in → ghi 1 ``Asset Lifecycle Event``
    ``label_printed`` + 1 ``IMM Audit Trail`` cho MỖI asset UNIQUE (NĐ98 truy xuất
    tem). Coerce DEDUP within-call (Vòng 15): name lặp trong CÙNG 1 call → ghi
    ĐÚNG 1 event/audit (``[a1,a1,a1]`` 1 call → 1 event, KHÔNG 3 — chặn khuếch
    đại ghi-audit). Gọi N lần RIÊNG = N event (mỗi lần in 1 event — KHÔNG dedup
    XUYÊN-call; bất biến cross-call GIỮ NGUYÊN).

    All-or-nothing: validate tồn tại + RBAC + IDOR cho TẤT CẢ asset TRƯỚC khi ghi
    event nào → tránh audit chain lệch. ≥1 không tồn tại → 404 (KHÔNG ghi gì);
    vendor ngoài scope → 403 toàn call.

    Thứ tự gate (Vòng 14 / BR-00-45 — đo từng bậc):
      0. ``@rate_limit(AC_LABEL_MARK_RATE_LIMIT/60s/IP)`` — decorator bọc NGOÀI
         thân → frappe tăng counter + ``frappe.throw(RateLimitExceededError)``
         (429) TRƯỚC ``rbac.require`` ⇒ vượt ngưỡng = 0 ALE ``label_printed`` +
         0 IMM Audit Trail (KHÔNG chạm ``_svc_mark_label_printed``/``commit``),
         no-leak body generic. Bucket RIÊNG (cache key gồm ``cmd``) TÁCH BIỆT
         resolve/scan/regen/pdf/batch. mark = write-audit-amplification (2×N
         record/call) → ngưỡng THẤP, ≤ regen.

    Bảo mật: ``rbac.require("asset.print")`` chạy ĐẦU TIÊN — ADR-IMM00-QR-SCAN-
    ACTION D6 (phương án B, Accepted→EXECUTED): cap ``asset.print``→(AC Asset,
    "print"). Ghi ``label_printed``+audit là HỆ QUẢ của hành-động-IN → gate đúng
    quyền PRINT (least-privilege; KHÔNG cần ``asset.write`` toàn asset). DocPerm
    print=1 sẵn cho ~mọi role vận hành → KTV/QL vật tư in được NGAY (sửa lỗi
    self-correction P2: trước đây chỉ Super Admin in được). User KHÔNG có print →
    403, chặn TRƯỚC mọi write (KHÔNG dò được asset tồn tại, KHÔNG sinh event/audit).
    (Cap mới ⇒ ``CAP_SET_VERSION`` ĐỔI ``v95.3388ee5629c1``→``v104.e46d05d9a66d``.)

    ``assets`` coerce an toàn qua ``_coerce_asset_names`` (SSoT 3 endpoint):
    malformed (bare-code/non-JSON/scalar/int/dict) → ``[]`` → all-or-nothing
    404/empty no-side-effect (KHÔNG ghi ALE ``label_printed``/``IMM Audit Trail``)
    — KHÔNG HTTP-500, KHÔNG traceback/JSONDecodeError leak (ref LL-BE-42).
    Coerce DEDUP within-call (Vòng 15): name lặp trong CÙNG call → ghi 1 lần
    (giữ thứ tự đầu); cap ``_MAX_LABEL_BATCH`` đo TRÊN list đã dedup (unique).
    """
    rbac.require("asset.print")
    # SSoT coerce an toàn — assets malformed → [] → all-or-nothing 404/empty
    # no-side-effect (KHÔNG ghi ALE/audit). KHÔNG parse_json trần (no-500/leak).
    names = _coerce_asset_names(assets)
    # CAP batch-size SAU rbac, TRƯỚC mọi write/validate → chặn khuếch đại write/audit
    # chain (2 record/asset). 413 bucket RIÊNG, message VI cố định, KHÔNG leak name,
    # KHÔNG side-effect (0 ALE label_printed + 0 IMM Audit Trail khi vượt cap).
    if len(names) > _MAX_LABEL_BATCH:
        return _err(_(_ERR_BATCH_TOO_LARGE), 413)
    # All-or-nothing: validate tồn tại + IDOR TRƯỚC khi ghi event nào.
    try:
        for n in names:
            if not frappe.db.exists(_DT_ASSET, n):
                return _err(_(_ERR_ASSET_NOT_FOUND), 404)
            assert_vendor_can_access(_DT_ASSET, n)
    except ServiceError as e:
        return _err(e.message, e.code)
    result = _svc_mark_label_printed(names)
    frappe.db.commit()
    return _ok(result)


@frappe.whitelist()
@rate_limit(limit=AC_LABEL_PDF_RATE_LIMIT, seconds=60, ip_based=True)  # ADR-LABEL-PDF §D6 — 429 TRƯỚC rbac.require; bucket RIÊNG (cmd), render nặng → ngưỡng thấp
def print_asset_labels_pdf(assets="", preset=""):
    """A3-PDF (ADR-IMM00-LABEL-PDF §D1/§D6): sinh PDF nhãn QR khổ tem nhiệt 60×100mm.

    FE tải PDF → iframe ẩn → ``iframe.print()`` → hộp thoại in → chọn máy in tem
    LAN → ra CHÍNH XÁC 60×100mm (mỗi asset UNIQUE = 1 trang). QR vẽ SERVER-SIDE
    (pyqrcode SVG inline encode ``qr_url`` deep-link ``/a/<token>`` — KHÔNG raw
    token). Coerce DEDUP within-call (Vòng 15): name lặp trong CÙNG call → 1
    trang (``[a1,a1]`` → ĐÚNG 1 trang PDF, KHÔNG 2 trang trùng).

    **Trả PDF bytes** (KHÔNG ``_ok`` JSON envelope) — set ``frappe.local.response``
    (Frappe set Content-Type: application/pdf + download). **Lỗi nghiệp vụ**
    (cap/IDOR/batch/preset/empty) = ``_err`` HTTP-200 Error envelope (DONE-gate
    LL-BE-42 — KHÔNG raise→4xx). Chỉ THÀNH CÔNG mới set response PDF.

    Signature: ``assets`` bare (KHÔNG annotation — đồng nhất
    ``get_asset_label_data_batch``; annotation ``str``/``X|None`` kích hoạt
    coercion pydantic v15 → reject native list 417). Default ``""`` (KHÔNG
    ``None``). Real HTTP gửi JSON-string; test/python gửi list — cả 2 coerce an
    toàn qua ``_coerce_asset_names`` (SSoT 3 endpoint): malformed (bare-code/
    non-JSON/scalar/int/dict) → ``[]`` → đi nhánh ``_err(_ERR_LABEL_EMPTY, 422)``
    sẵn có — KHÔNG HTTP-500, KHÔNG traceback/JSONDecodeError leak, KHÔNG duyệt
    KÝ TỰ khi là JSON-scalar-string (ref LL-BE-42). ``preset`` default ``""`` (V3 §D14 — KHÔNG hardcode
    ``"tem-60x100"``): caller bỏ trống → ``_resolve_label_preset()`` (site_config
    ``assetcore_label_preset``, hợp-lệ-hoá 1 chỗ + fallback an toàn 60×100mm, KHÔNG
    raise); caller truyền tường minh → GIỮ gate whitelist (lạ → 422). Thứ tự ưu
    tiên: explicit > site_config > code-default. Thứ tự gate (§D6 — đo từng bậc):

      0. ``@rate_limit`` (429 TRƯỚC rbac, decorator NGOÀI thân).
      1. ``rbac.require("asset.print")`` ĐẦU TIÊN → user thiếu cap →
         PermissionError (403) + KHÔNG render + KHÔNG đụng DB.
      2. ``preset`` strip 2-đầu TRƯỚC gate whitelist (Vòng 32 §D6 — parity token
         Vòng 6 / name Vòng 31): preset hợp lệ kèm whitespace/newline (copy-paste/
         mobile-BE/dropdown stray ``\n``) → khớp whitelist → render đúng khổ thay
         vì 422 giả. CHỈ strip leading/trailing — KHÔNG lowercase/transform GIỮA
         chuỗi (no-over-normalize: 'tem 60x100' space-GIỮA / 'TEM-60X100' case khác
         vẫn 422). Rỗng-sau-strip ('   '/'\n'/non-str) → site_config default (V3
         §D14); preset LẠ tường minh → 422 (chống render khổ tuỳ ý; resolver KHÔNG nới).
      3. list rỗng → 422 (BA chốt §D7 — KHÔNG render PDF 0 trang).
      4. ``len > _MAX_LABEL_BATCH(200)`` → 413 bucket RIÊNG, msg VI cố định
         (KHÔNG leak asset name), SAU rbac (chỉ user đã-auth-print biết giới hạn).
      5. IDOR all-or-nothing: mỗi asset tồn tại qua ``assert_vendor_can_access``;
         vendor có ≥1 asset ngoài scope → 403 TOÀN call (no partial, no leak).
      6. asset∄ TRONG batch (mix valid+invalid) KHÔNG chặn — render "ô lỗi an
         toàn" trong PDF (§D7); asset valid khác VẪN in được (KHÔNG 404 all-or-nothing).

    **KHÔNG emit ``label_printed``** (render = preview ≠ in — §D8; sự kiện in chỉ
    ghi qua ``mark_label_printed`` gọi RIÊNG sau khi user xác nhận đã in). KHÔNG
    chạm logic gen/rotate/scan/resolve QR (§D9 — chỉ ĐỌC ``qr_url`` qua batch).
    """
    rbac.require("asset.print")
    # SSoT coerce an toàn — assets malformed (bare-code/non-JSON/scalar/int/dict)
    # → [] → đi nhánh _err(_ERR_LABEL_EMPTY, 422) sẵn có. KHÔNG parse_json trần
    # (chống JSONDecodeError/TypeError → HTTP-500/traceback-leak; chống duyệt KÝ TỰ
    # khi assets là JSON-scalar-string). LL-BE-42 no-500/no-traceback.
    names = _coerce_asset_names(assets)
    # Vòng 32 §D6 bước 2: chuẩn-hoá `preset` strip 2-đầu TRƯỚC gate whitelist
    # (parity token Vòng 6 / name Vòng 31). preset hợp lệ kèm whitespace/newline
    # (copy-paste / mobile-BE / dropdown stray \n) → khớp whitelist → render đúng
    # khổ thay vì 422 giả. CHỈ strip leading/trailing — KHÔNG lowercase/transform
    # GIỮA chuỗi (no-over-normalize: 'tem 60x100' space-GIỮA / 'TEM-60X100' case
    # khác vẫn KHÔNG ∈ _LABEL_PRESETS → 422; whitelist KHÔNG bị nới). non-str
    # (0/None qua coercion) → '' qua isinstance guard (no raise/500).
    preset = preset.strip() if isinstance(preset, str) else ""
    # V3 §D14: caller bỏ trống preset (rỗng-sau-strip rơi đúng đây) → server-default
    # qua resolver (site_config assetcore_label_preset, hợp-lệ-hoá 1 chỗ + fallback
    # an toàn 60×100mm, KHÔNG raise). Thứ tự ưu tiên: explicit client > site_config >
    # code-default. Resolver LUÔN trả giá-trị-whitelist → nhánh-resolved KHÔNG tự-422.
    if not preset:
        preset = _resolve_label_preset()
    # GIỮ NGUYÊN gate whitelist (caller truyền preset LẠ tường minh vẫn 422 —
    # resolver KHÔNG nới whitelist; chỉ áp khi `not preset`).
    if preset not in _LABEL_PRESETS:
        return _err(_(_ERR_LABEL_PRESET), 422)
    if not names:
        return _err(_(_ERR_LABEL_EMPTY), 422)
    # CAP batch SAU rbac (chỉ user đã-auth-print tới đây) TRƯỚC IDOR + render →
    # chặn payload-DoS render N PDF. 413 bucket RIÊNG, msg VI, KHÔNG leak name.
    if len(names) > _MAX_LABEL_BATCH:
        return _err(_(_ERR_BATCH_TOO_LARGE), 413)
    # IDOR all-or-nothing: asset tồn tại nào cũng phải trong scope. asset∄ KHÔNG
    # chặn (render ô-lỗi trong PDF — §D7); vendor có ≥1 asset ngoài scope → 403 toàn call.
    try:
        for n in names:
            if frappe.db.exists(_DT_ASSET, n):
                assert_vendor_can_access(_DT_ASSET, n)
    except ServiceError as e:
        return _err(e.message, e.code)
    # Render chỉ tới đây khi pass hết gate → KHÔNG render cho call thiếu quyền/quá-batch/IDOR.
    # §D16 hardening: bọc render — pdfkit/wkhtmltopdf có thể raise runtime
    # (binary thiếu, ảnh hỏng, OOM…). KHÔNG để raise → 500+traceback leak; trả
    # _err VI sạch (HTTP-200 Error envelope, FE map về message 'Không thể tạo PDF…').
    try:
        pdf_bytes = _svc_render_asset_labels_pdf(names, preset)
    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         "print_asset_labels_pdf render error")
        return _err(_(_ERR_LABEL_RENDER), ErrorCode.INTERNAL)
    frappe.local.response.filename = "asset-labels.pdf"
    frappe.local.response.filecontent = pdf_bytes
    frappe.local.response.type = "pdf"
    # KHÔNG return _ok(...) — PDF trả qua frappe.local.response (Frappe Content-Type pdf).


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=AC_QR_REGEN_RATE_LIMIT, seconds=60, ip_based=True)  # Vòng 27 B — 429 TRƯỚC rbac.require (BR-00-38); bucket+ngưỡng RIÊNG (KHÔNG chung resolve=30)
def regenerate_asset_qr_token(asset: str = ""):
    """POST — B (hardening): cấp lại (rotate) mã QR cấp tài sản.

    Vô hiệu hoá qr_token bị lộ + cấp token MỚI enumeration-safe. KHÁC
    ``ensure_asset_qr_token`` (idempotent — KHÔNG overwrite): rotate luôn GHI ĐÈ
    token → mọi nhãn QR đã in/lộ KHÔNG còn resolve (token cũ → 404). FE màn
    AssetDetailView gọi sau khi người dùng xác nhận cảnh báo "vô hiệu hoá mọi nhãn
    QR đã in".

    Bảo mật (theo thứ tự — ADR-001 D4 + lesson P1 417 → sig ``str=""``):
      0. ``@rate_limit(AC_QR_REGEN_RATE_LIMIT/60s/IP)`` (Vòng 27 B, BR-00-38) —
         decorator bọc NGOÀI thân hàm → frappe tăng counter rồi
         ``frappe.throw(RateLimitExceededError)`` (HTTP 429) TRƯỚC khi thân hàm
         chạy ⇒ TRƯỚC ``rbac.require``. Vượt ngưỡng → KHÔNG side-effect (0 token
         mới, 0 ALE ``qr_regenerated``, 0 audit — service KHÔNG bị chạm), no-leak
         (body generic, KHÔNG lộ asset name/token). Hằng + bucket RIÊNG (cache key
         gồm ``cmd`` → counter TÁCH BIỆT resolve/scan; ngưỡng THẤP hơn resolve vì
         rotate hiếm hơn + blast-radius lớn nhất). KHÔNG-HTTP context (test/CLI)
         bypass có chủ đích (``if not frappe.request: return fn``). Đóng bất đối
         xứng read-throttled (BR-00-29) / write-rotate-unthrottled.
      1. ``rbac.require("asset.qr.rotate")`` chạy ĐẦU TIÊN → user không có quyền
         rotate (Guest/nurse/KTV chỉ-print) → ``frappe.PermissionError`` (403).
         ADR-IMM00-QR-SCAN-ACTION D6 (phương án B, Accepted→EXECUTED): TÁCH cap
         ``asset.qr.rotate``→(AC Asset,"write"). Rotate = side-effect GHI (đổi định
         danh phụ + vô hiệu nhãn cũ + ghi event/audit) ⇒ bind permtype "write"
         (KHÔNG ``asset.print`` — print KHÔNG được rotate). Gate bằng CAPABILITY
         (DocPerm), KHÔNG hardcode role. Hiện chỉ Super Admin (write=1); QL vật tư
         cấp thêm write/grant qua DocPerm (config /app, KHÔNG deploy code). (Cap
         mới ⇒ ``CAP_SET_VERSION`` ĐỔI ``v95.3388ee5629c1``→``v104.e46d05d9a66d``.)
      2. asset rỗng/không tồn tại → 404 leak-safe (KHÔNG 500, KHÔNG đoán id) —
         chặn TRƯỚC khi đụng service (no side-effect khi không hợp lệ).
      3. IDOR: ``assert_vendor_can_access`` → vendor ngoài scope → 403, KHÔNG leak
         token mới (đồng nhất leak-safe với resolve).
      4. Service rotate → token MỚI (str nội bộ). API dựng ``qr_url`` qua
         ``build_asset_label_data`` (đọc token MỚI từ DB) → ``qr_url`` phản ánh
         deep-link mới (preview/print). Envelope CHỈ trả ``{name, qr_url}`` —
         KHÔNG surface token thô (ADR-001 §D4 rule 9 + 05 §III.1: FE chỉ cần
         ``qr_url``, no-raw-token parity với resolve/scan).
    """
    rbac.require("asset.qr.rotate")
    if not asset or not isinstance(asset, str) or not frappe.db.exists(_DT_ASSET, asset):
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)
    try:
        assert_vendor_can_access(_DT_ASSET, asset)
    except ServiceError as e:
        return _err(e.message, e.code)
    # Service vẫn trả str token nội bộ để dựng qr_url; KHÔNG đưa vào envelope.
    _svc_regenerate_asset_qr_token(asset)
    frappe.db.commit()
    # qr_url phản ánh token MỚI (build_asset_label_data đọc lại token vừa overwrite).
    label = build_asset_label_data(asset)
    return _ok({"name": asset, "qr_url": label["qr_url"]})


@frappe.whitelist(methods=["POST"])
def create_asset():
    """POST /api/method/assetcore.api.imm00.create_asset

    Hỗ trợ 2 luồng:
      1. Tài sản có sẵn (không qua phiếu tiếp nhận) → cho phép set lifecycle_status
         ban đầu là Commissioned/Active. API insert ở Draft (theo workflow), rồi
         dùng transition_asset_status để dịch chuyển → đúng workflow + audit trail.
      2. Tài sản mua mới → đi qua flow IMM-04 Commissioning, không gọi endpoint này.
    """
    data = dict(frappe.local.form_dict)
    desired_status = data.pop("lifecycle_status", None) or ""
    clean = {k: v for k, v in data.items() if k not in ("cmd", "doctype")}

    # B2 (root-cause): pre-validate mandatory fields TRƯỚC doc.insert() → trả 422 +
    # nhãn VI sạch thay vì để Frappe raise MandatoryError (dev-string
    # '[AC Asset, AC-ASSET-2026-#####]: asset_category'). Quét MỌI field trong
    # _ASSET_REQD_LABELS_VI (asset_name + asset_category) — coi "" / khoảng trắng /
    # thiếu key là vi phạm.
    missing_labels = [
        label
        for field, label in _ASSET_REQD_LABELS_VI.items()
        if not str(clean.get(field) or "").strip()
    ]
    if missing_labels:
        return _err(
            _("Vui lòng nhập: {0}.").format(", ".join(missing_labels)),
            ErrorCode.VALIDATION,
            fields={
                field: _("Trường bắt buộc")
                for field in _ASSET_REQD_LABELS_VI
                if not str(clean.get(field) or "").strip()
            },
        )

    # SAVEPOINT cục bộ: rollback CHỈ phần insert đang dở khi lỗi (KHÔNG nuốt cả
    # transaction → tránh xoá công việc khác trong cùng request / fixture test).
    # Bảo đảm 'Failed cases KHÔNG tạo row rác' mà KHÔNG dùng frappe.db.rollback() thô.
    frappe.db.savepoint("create_asset")
    try:
        doc = frappe.new_doc(_DT_ASSET)
        doc.update(clean)
        doc.insert(ignore_permissions=False)
        if desired_status and desired_status != doc.lifecycle_status:
            # Draft → Active phải đi qua Commissioned (state machine guard).
            chain = ["Commissioned", "Active"] if desired_status == "Active" else [desired_status]
            for step in chain:
                transition_asset_status(
                    doc.name, step,
                    actor=frappe.session.user,
                    reason=_("Khởi tạo tài sản có sẵn"),
                )
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.MandatoryError as e:
        # Defense-in-depth: nếu một reqd field khác (ngoài map) thiếu, KHÔNG để
        # dev-string '[AC Asset, ...]: <field>' lộ ra user — map sang nhãn VI.
        frappe.db.rollback(save_point="create_asset")
        return _err(_map_mandatory_error_vi(e), ErrorCode.VALIDATION)
    except frappe.exceptions.ValidationError as e:
        # Nhánh lỗi nghiệp vụ (dup asset_code, immutable, pattern, dates…) — message
        # đã là VI sạch từ controller AC Asset. Rollback savepoint → KHÔNG để row rác.
        frappe.db.rollback(save_point="create_asset")
        return _err(str(e), ErrorCode.VALIDATION)


def _map_mandatory_error_vi(exc: Exception) -> str:
    """B2 — map frappe MandatoryError → message VI sạch (KHÔNG lộ dev-string).

    Frappe raise MandatoryError với message dạng
    ``[AC Asset, AC-ASSET-2026-#####]: asset_category`` (đôi khi nhiều field cách
    nhau dấu phẩy sau dấu ``:``). Trích phần fieldname sau ``:``, ánh xạ qua
    _ASSET_REQD_LABELS_VI (fallback nhãn từ DocType meta nếu field nằm ngoài map).
    """
    raw = str(exc) or ""
    field_part = raw.rsplit(":", 1)[-1].strip() if ":" in raw else raw.strip()
    fieldnames = [f.strip() for f in field_part.split(",") if f.strip()]
    labels = []
    for fn in fieldnames:
        label = _ASSET_REQD_LABELS_VI.get(fn)
        if not label:
            label = frappe.get_meta(_DT_ASSET).get_label(fn) or fn
        labels.append(label)
    if not labels:
        return _("Vui lòng nhập đầy đủ các trường bắt buộc.")
    return _("Vui lòng nhập: {0}.").format(", ".join(labels))


@frappe.whitelist(methods=["POST"])
def update_asset(name: str):
    """POST /api/method/assetcore.api.imm00.update_asset"""
    if not frappe.db.exists(_DT_ASSET, name):
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)
    data = frappe.local.form_dict
    try:
        doc = frappe.get_doc(_DT_ASSET, name)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "name", "doctype")})
        doc.save(ignore_permissions=False)
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def transition_status(name: str, to_status: str, reason: str = ""):
    """POST /api/method/assetcore.api.imm00.transition_status

    Bảo mật — 3 lớp theo thứ tự (MIRROR get_asset:471, CR-WF-00-TRANSITION-AUTHZ,
    ADR-IMM00-LIFECYCLE-AUTHZ):
      0. ``rbac.require("asset.write")`` chạy ĐẦU TIÊN (CÂU LỆNH ĐẦU thân hàm) →
         caller thiếu DocPerm write AC Asset → ``frappe.PermissionError`` (HTTP 403).
         Gate bằng CAPABILITY (DocPerm), KHÔNG hardcode role-name (chống RBAC
         dead-gate). Chạy TRƯỚC ``frappe.db.exists`` → no existence-oracle (thiếu
         cap → 403 KHÔNG 404, parity thứ-tự-lớp get_asset). RC: endpoint này ĐỔI
         lifecycle_status AC Asset qua service ``transition_asset_status`` (perm-free
         — đường WO-driven programmatic). Thiếu gate ⇒ MỌI user login POST được
         endpoint tự đổi trạng thái thiết bị (missing-authorization write).
      1. exists → ``_err(404)`` leak-safe (name không tồn tại).
      2. IDOR/vendor isolation: ``assert_vendor_can_access`` → Vendor Engineer ngoài
         scope → ServiceError(FORBIDDEN) → ``_err(403)``, KHÔNG đổi lifecycle_status.
    Authz đặt ở tầng ENDPOINT — service ``transition_asset_status`` GIỮ NGUYÊN
    perm-free (lớp WO-complete: KTV không có asset.write vẫn chuyển trạng thái khi
    hoàn tất Work Order). Xem docstring service để rõ ranh giới tier.
    """
    # 0. RBAC gate — require asset.write (DocPerm AC Asset). PermissionError → 403.
    #    TRƯỚC exists → no existence-oracle (parity get_asset).
    rbac.require("asset.write")
    if not frappe.db.exists(_DT_ASSET, name):
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)
    # AUTH-10: IDOR guard — Vendor Engineer can't transition assets outside scope.
    try:
        assert_vendor_can_access(_DT_ASSET, name)
    except ServiceError as e:
        return _err(e.message, e.code)
    try:
        transition_asset_status(name, to_status, actor=frappe.session.user, reason=reason)
        frappe.db.commit()
        return _ok({"name": name, "lifecycle_status": to_status})
    except InvalidAssetTransition as e:
        return _err(str(e), ErrorCode.BAD_STATE)
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), ErrorCode.VALIDATION)


@frappe.whitelist()
def get_asset_timeline(name: str, page: int = 1, page_size: int = 50):
    """GET /api/method/assetcore.api.imm00.get_asset_timeline"""
    if not frappe.db.exists(_DT_ASSET, name):
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)
    page, page_size = int(page), int(page_size)
    total = frappe.db.count(_DT_LIFECYCLE_EVENT, {"asset": name})
    pag = paginate(total, page, page_size)
    items = frappe.get_list(
        _DT_LIFECYCLE_EVENT,
        filters={"asset": name},
        fields=["name", "event_type", "actor", "from_status", "to_status", "timestamp", "notes"],
        limit_start=pag["offset"],
        limit_page_length=pag["page_size"],
        order_by=_ORDER_EVENT_TS_DESC,
    )
    return _ok({"pagination": pag, "items": items})


@frappe.whitelist()
def validate_for_operations(name: str):
    """GET /api/method/assetcore.api.imm00.validate_for_operations"""
    if not frappe.db.exists(_DT_ASSET, name):
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)
    try:
        validate_asset_for_operations(name)
        return _ok({"valid": True})
    except frappe.exceptions.ValidationError as e:
        return _ok({"valid": False, "reason": str(e)})


@frappe.whitelist()
def get_asset_kpi(name: str):
    """GET /api/method/assetcore.api.imm00.get_asset_kpi

    Tính KPI on-the-fly từ:
      - AC Asset Downtime Log (uptime, downtime_hours)
      - Asset Repair docstatus=1 (MTTR, MTBF, total_repair_cost)
      - PM Work Order (pm_compliance_pct = on-time/total)
    Bug fix: trước đây đọc `doc.get("uptime_pct")` từ các field không tồn tại
    trong AC Asset schema → luôn trả None. Nay compute từ source records.
    """
    if not frappe.db.exists(_DT_ASSET, name):
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)
    doc = frappe.get_doc(_DT_ASSET, name)

    # Window: 12 tháng gần nhất
    from frappe.utils import nowdate, add_months, now_datetime, get_datetime, time_diff_in_hours
    window_start = add_months(nowdate(), -12)
    now_dt = now_datetime()
    window_hours = 365.0 * 24.0

    # Downtime hours từ AC Asset Downtime Log
    dt_rows = frappe.get_all(
        _DT_DOWNTIME_LOG,
        filters={"asset": name, "start_time": [">=", window_start]},
        fields=["start_time", "end_time", "downtime_hours", "is_open"],
        limit_page_length=0,
    )
    total_downtime_h = 0.0
    breakdown_count = len(dt_rows)
    for r in dt_rows:
        if r["is_open"]:
            total_downtime_h += float(time_diff_in_hours(now_dt, r["start_time"]) or 0)
        else:
            total_downtime_h += float(r["downtime_hours"] or 0)
    uptime_pct = round(max(0.0, (window_hours - total_downtime_h) / window_hours * 100.0), 2)

    # MTTR (giờ) — trung bình mttr_hours từ Asset Repair Completed
    rep_rows = frappe.get_all(
        "Asset Repair",
        filters={"asset_ref": name, "status": "Completed", "docstatus": 1},
        fields=["mttr_hours", "total_parts_cost", "completion_datetime"],
    )
    mttr_hours = (
        round(sum(float(r["mttr_hours"] or 0) for r in rep_rows) / len(rep_rows), 2)
        if rep_rows else None
    )
    total_repair_cost = sum(float(r["total_parts_cost"] or 0) for r in rep_rows) or None

    # MTBF (ngày) — khoảng cách trung bình giữa các lần hỏng
    if len(rep_rows) >= 2:
        sorted_dates = sorted([get_datetime(r["completion_datetime"]) for r in rep_rows if r["completion_datetime"]])
        if len(sorted_dates) >= 2:
            diffs = [(sorted_dates[i+1] - sorted_dates[i]).days for i in range(len(sorted_dates)-1)]
            mtbf_days = round(sum(diffs) / len(diffs), 0) if diffs else None
        else:
            mtbf_days = None
    elif len(rep_rows) == 1:
        # 1 lần hỏng → khoảng từ commissioning → repair
        if doc.commissioning_date and rep_rows[0]["completion_datetime"]:
            mtbf_days = (get_datetime(rep_rows[0]["completion_datetime"]).date() - doc.commissioning_date).days
        else:
            mtbf_days = None
    else:
        mtbf_days = None

    # PM compliance: completed-on-time / total scheduled trong 12 tháng
    pm_rows = frappe.get_all(
        "PM Work Order",
        filters={"asset_ref": name, "due_date": [">=", window_start]},
        fields=["status", "is_late"],
    )
    pm_total = len(pm_rows)
    pm_on_time = sum(1 for p in pm_rows if p["status"] == "Completed" and not p["is_late"])
    pm_compliance_pct = round(pm_on_time / pm_total * 100.0, 1) if pm_total else None

    return _ok({
        "name": name,
        "lifecycle_status": doc.lifecycle_status,
        "uptime_pct": uptime_pct,
        "mtbf_days": mtbf_days,
        "mttr_hours": mttr_hours,
        "pm_compliance_pct": pm_compliance_pct,
        "total_repair_cost": total_repair_cost,
        "next_pm_date": doc.next_pm_date,
        "next_calibration_date": doc.next_calibration_date,
        "byt_reg_expiry": doc.byt_reg_expiry,
        "breakdown_count": breakdown_count,
        "total_downtime_hours": round(total_downtime_h, 2),
    })


# ─────────────────────────────────────────────────────────────────────────────
# AC Supplier  (4 endpoints)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_suppliers(page: int = 1, page_size: int = 20, search: str = None, supplier_type: str = None):
    """GET /api/method/assetcore.api.imm00.list_suppliers"""
    page, page_size = int(page), int(page_size)
    filters = {}
    if supplier_type:
        filters["supplier_type"] = supplier_type

    or_filters = None
    if search:
        like = f"%{search}%"
        or_filters = [
            [_DT_SUPPLIER, "name",          "like", like],
            [_DT_SUPPLIER, "supplier_name", "like", like],
            [_DT_SUPPLIER, "supplier_code", "like", like],
            [_DT_SUPPLIER, "email_id",      "like", like],
            [_DT_SUPPLIER, "tax_id",        "like", like],
        ]
        total = frappe.db.sql(
            f"SELECT COUNT(*) FROM `tab{_DT_SUPPLIER}`"
            f" WHERE name LIKE %s OR supplier_name LIKE %s OR supplier_code LIKE %s"
            f" OR email_id LIKE %s OR tax_id LIKE %s",
            [like, like, like, like, like],
        )[0][0]
    else:
        total = frappe.db.count(_DT_SUPPLIER, filters=filters)

    pag = paginate(int(total), page, page_size)
    items = frappe.get_list(
        _DT_SUPPLIER,
        filters=filters,
        or_filters=or_filters,
        fields=["name", "supplier_name", "supplier_code", "supplier_group", "vendor_type",
                "country", "email_id", "phone", "contract_end", "is_active"],
        limit_start=pag["offset"],
        limit_page_length=pag["page_size"],
        order_by="supplier_name asc",
    )
    return _ok({"pagination": pag, "items": items})


@frappe.whitelist()
def get_supplier(name: str):
    """GET /api/method/assetcore.api.imm00.get_supplier"""
    if not frappe.db.exists(_DT_SUPPLIER, name):
        return _err(_(_ERR_SUPPLIER_NOT_FOUND), 404)
    return _ok(frappe.get_doc(_DT_SUPPLIER, name).as_dict())


@frappe.whitelist(methods=["POST"])
def create_supplier():
    """POST /api/method/assetcore.api.imm00.create_supplier"""
    data = frappe.local.form_dict
    try:
        doc = frappe.new_doc(_DT_SUPPLIER)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "doctype")})
        doc.insert()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def update_supplier(name: str):
    """POST /api/method/assetcore.api.imm00.update_supplier"""
    if not frappe.db.exists(_DT_SUPPLIER, name):
        return _err(_(_ERR_SUPPLIER_NOT_FOUND), 404)
    data = frappe.local.form_dict
    try:
        doc = frappe.get_doc(_DT_SUPPLIER, name)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "name", "doctype")})
        doc.save()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


# ─────────────────────────────────────────────────────────────────────────────
# Locations / Departments / Categories  (6 endpoints)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_locations(parent: str = None):
    """GET /api/method/assetcore.api.imm00.list_locations"""
    filters = {}
    if parent:
        filters["parent_location"] = parent
    items = frappe.get_list(
        _DT_LOCATION,
        filters=filters,
        fields=["name", "location_name", "location_code", "parent_location", "is_group",
                "clinical_area_type", "infection_control_level", "power_backup_available",
                "dept_head", "contact_phone", "notes"],
        order_by="lft asc",
    )
    _enrich(items, "parent_location", _DT_LOCATION, "location_name")
    _enrich(items, "dept_head", "User", "full_name", out_field="dept_head_name")
    return _ok(items)


@frappe.whitelist()
def list_departments(parent: str = None):
    """GET /api/method/assetcore.api.imm00.list_departments"""
    filters = {}
    if parent:
        filters["parent_department"] = parent
    items = frappe.get_list(
        _DT_DEPARTMENT,
        filters=filters,
        fields=["name", "department_name", "department_code", "parent_department", "is_group",
                "dept_head", "phone", "email", "is_active"],
        order_by="lft asc",
    )
    _enrich(items, "parent_department", _DT_DEPARTMENT, "department_name")
    _enrich(items, "dept_head", "User", "full_name", out_field="dept_head_name")
    return _ok(items)


@frappe.whitelist()
def list_asset_categories():
    """GET /api/method/assetcore.api.imm00.list_asset_categories"""
    items = frappe.get_list(
        _DT_ASSET_CATEGORY,
        fields=["name", "category_name", "category_code", "description",
                "gmdn_code", "gmdn_term",
                "default_pm_required", "default_pm_interval_days",
                "default_calibration_required", "default_calibration_interval_days",
                "default_depreciation_method", "total_depreciation_months",
                "depreciation_frequency", "default_residual_value_pct",
                "has_radiation", "is_active"],
        order_by="category_name asc",
    )
    return _ok(items)


def _norm_check(d: dict, fields: list) -> dict:
    """Normalize Frappe Check fields (True/False booleans) to 0/1 integers."""
    for f in fields:
        if f in d:
            d[f] = 1 if d[f] else 0
    return d


@frappe.whitelist()
def get_location(name: str):
    """GET /api/method/assetcore.api.imm00.get_location"""
    if not frappe.db.exists(_DT_LOCATION, name):
        return _err(_("Location not found"), 404)
    d = frappe.get_doc(_DT_LOCATION, name).as_dict()
    _norm_check(d, ["is_group", "power_backup_available"])
    return _ok(d)


@frappe.whitelist()
def get_department(name: str):
    """GET /api/method/assetcore.api.imm00.get_department"""
    if not frappe.db.exists(_DT_DEPARTMENT, name):
        return _err(_("Department not found"), 404)
    d = frappe.get_doc(_DT_DEPARTMENT, name).as_dict()
    _norm_check(d, ["is_group", "is_active"])
    return _ok(d)


@frappe.whitelist()
def get_asset_category(name: str):
    """GET /api/method/assetcore.api.imm00.get_asset_category"""
    if not frappe.db.exists(_DT_ASSET_CATEGORY, name):
        return _err(_("Asset Category not found"), 404)
    d = frappe.get_doc(_DT_ASSET_CATEGORY, name).as_dict()
    _norm_check(d, ["default_pm_required", "default_calibration_required", "has_radiation", "is_active"])
    return _ok(d)


@frappe.whitelist(methods=["POST"])
def create_location():
    """POST /api/method/assetcore.api.imm00.create_location"""
    data = frappe.local.form_dict
    try:
        doc = frappe.new_doc(_DT_LOCATION)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "doctype")})
        doc.insert()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def create_department():
    """POST /api/method/assetcore.api.imm00.create_department"""
    data = frappe.local.form_dict
    try:
        doc = frappe.new_doc(_DT_DEPARTMENT)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "doctype")})
        doc.insert()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def create_asset_category():
    """POST /api/method/assetcore.api.imm00.create_asset_category"""
    data = frappe.local.form_dict
    try:
        doc = frappe.new_doc(_DT_ASSET_CATEGORY)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "doctype")})
        doc.insert()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


# ─────────────────────────────────────────────────────────────────────────────
# IMM Device Model  (4 endpoints)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_device_models(page: int = 1, page_size: int = 20, manufacturer: str = None, search: str = None):
    """GET /api/method/assetcore.api.imm00.list_device_models"""
    page, page_size = int(page), int(page_size)
    filters = {}
    if manufacturer:
        filters["manufacturer"] = manufacturer
    or_filters = []
    if search:
        or_filters = [
            [_DT_DEVICE_MODEL, "name", "like", f"%{search}%"],
            [_DT_DEVICE_MODEL, "model_name", "like", f"%{search}%"],
            [_DT_DEVICE_MODEL, "manufacturer", "like", f"%{search}%"],
            [_DT_DEVICE_MODEL, "model_version", "like", f"%{search}%"],
            [_DT_DEVICE_MODEL, "gmdn_code", "like", f"%{search}%"],
        ]
        like = f"%{search}%"
        filter_conds = " OR ".join([
            f"name LIKE {frappe.db.escape(like)}",
            f"model_name LIKE {frappe.db.escape(like)}",
            f"manufacturer LIKE {frappe.db.escape(like)}",
            f"model_version LIKE {frappe.db.escape(like)}",
            f"gmdn_code LIKE {frappe.db.escape(like)}",
        ])
        manufacturer_cond = f" AND manufacturer = {frappe.db.escape(manufacturer)}" if manufacturer else ""
        total = frappe.db.sql(
            f"SELECT COUNT(*) FROM `tab{_DT_DEVICE_MODEL}` WHERE ({filter_conds}){manufacturer_cond}"
        )[0][0]
    else:
        total = frappe.db.count(_DT_DEVICE_MODEL, filters=filters)
    pag = paginate(total, page, page_size)
    items = frappe.get_list(
        _DT_DEVICE_MODEL,
        filters=filters,
        or_filters=or_filters if or_filters else None,
        fields=["name", "model_name", "model_version", "manufacturer",
                "medical_device_class", "gmdn_code", "asset_category", "model_image"],
        limit_start=pag["offset"],
        limit_page_length=pag["page_size"],
        order_by="model_name asc",
    )
    _enrich(items, "asset_category", _DT_ASSET_CATEGORY, "category_name")
    return _ok({"pagination": pag, "items": items})


@frappe.whitelist()
def get_device_model(name: str):
    """GET /api/method/assetcore.api.imm00.get_device_model"""
    if not frappe.db.exists(_DT_DEVICE_MODEL, name):
        return _err(_(_ERR_DEVICE_MODEL_NOT_FOUND), 404)
    return _ok(frappe.get_doc(_DT_DEVICE_MODEL, name).as_dict())


@frappe.whitelist(methods=["POST"])
def create_device_model():
    """POST /api/method/assetcore.api.imm00.create_device_model"""
    data = frappe.local.form_dict
    try:
        doc = frappe.new_doc(_DT_DEVICE_MODEL)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "doctype")})
        doc.insert()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def update_device_model(name: str):
    """POST /api/method/assetcore.api.imm00.update_device_model"""
    if not frappe.db.exists(_DT_DEVICE_MODEL, name):
        return _err(_(_ERR_DEVICE_MODEL_NOT_FOUND), 404)
    data = frappe.local.form_dict
    try:
        doc = frappe.get_doc(_DT_DEVICE_MODEL, name)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "name", "doctype")})
        doc.save()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


# ─── Device Model file upload ────────────────────────────────────────────────
_DEVICE_MODEL_FOLDER = "Home/Device Models"


def _ensure_device_model_folder() -> str:
    """Đảm bảo folder Home/Device Models tồn tại trong File tree, return name."""
    if frappe.db.exists("File", _DEVICE_MODEL_FOLDER):
        return _DEVICE_MODEL_FOLDER
    folder = frappe.get_doc({
        "doctype":   "File",
        "file_name": "Device Models",
        "is_folder": 1,
        "folder":    "Home",
    })
    folder.insert(ignore_permissions=True)
    return folder.name


@frappe.whitelist(methods=["POST"])
def upload_device_model_file(model_name: str = "", fieldname: str = "model_image"):
    """POST — Upload 1 file vào folder Home/Device Models, attach vào IMM Device Model nếu có model_name.

    Form-data:
      - file: File (required)
      - model_name: optional — nếu có sẽ attach vào doc + set field
      - fieldname: 'model_image' | 'catalog_file' (default: model_image)

    Returns: { file_url, file_name, name }
    """
    if fieldname not in ("model_image", "catalog_file"):
        return _err(_("fieldname phải là 'model_image' hoặc 'catalog_file'"), 400)

    files = frappe.request.files
    if not files or "file" not in files:
        return _err(_("Thiếu file upload"), 400)
    upload = files["file"]
    if not upload.filename:
        return _err(_("File không có tên"), 400)

    folder_name = _ensure_device_model_folder()

    file_doc = frappe.get_doc({
        "doctype":      "File",
        "file_name":    upload.filename,
        "folder":       folder_name,
        "is_private":   0,
        "content":      upload.stream.read(),
        "decode":       False,
    })
    if model_name and frappe.db.exists(_DT_DEVICE_MODEL, model_name):
        file_doc.attached_to_doctype = _DT_DEVICE_MODEL
        file_doc.attached_to_name    = model_name
        file_doc.attached_to_field   = fieldname
    file_doc.save(ignore_permissions=True)

    if model_name and frappe.db.exists(_DT_DEVICE_MODEL, model_name):
        frappe.db.set_value(_DT_DEVICE_MODEL, model_name, fieldname, file_doc.file_url,
                            update_modified=False)

    return _ok({
        "name":      file_doc.name,
        "file_url":  file_doc.file_url,
        "file_name": file_doc.file_name,
        "fieldname": fieldname,
    })


# ─────────────────────────────────────────────────────────────────────────────
# IMM SLA Policy  (2 endpoints)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_sla_policies(priority: str = None, risk_class: str = None,
                       is_active: str = None):
    """GET /api/method/assetcore.api.imm00.list_sla_policies

    Mặc định trả về TẤT CẢ chính sách (cả active và inactive) để FE tự lọc.
    Truyền is_active=1 hoặc 0 nếu muốn lọc ở BE.
    """
    filters: dict = {}
    if priority:
        filters["priority"] = priority
    if risk_class:
        filters["risk_class"] = risk_class
    if is_active in ("0", "1", 0, 1):
        filters["is_active"] = int(is_active)
    items = frappe.get_list(
        _DT_SLA_POLICY,
        filters=filters,
        fields=["name", "policy_name", "priority", "risk_class", "is_default",
                "is_active", "response_time_minutes", "resolution_time_hours"],
        order_by="is_active desc, priority asc, risk_class asc",
        ignore_permissions=False,
    )
    # Normalize Check fields → int 0/1 (Frappe đôi khi trả str/bool gây sai lệch FE)
    for it in items:
        it["is_active"] = 1 if it.get("is_active") else 0
        it["is_default"] = 1 if it.get("is_default") else 0
    return _ok(items)


@frappe.whitelist()
def resolve_sla_policy(priority: str, risk_class: str):
    """GET /api/method/assetcore.api.imm00.resolve_sla_policy"""
    try:
        policy = get_sla_policy(priority, risk_class)
        if not policy:
            return _err(_("Không tìm thấy SLA Policy phù hợp"), ErrorCode.NOT_FOUND)
        return _ok(policy)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "resolve_sla_policy error")
        return _err(_("Lỗi server"), ErrorCode.INTERNAL)


# ─────────────────────────────────────────────────────────────────────────────
# IMM Audit Trail  (3 endpoints)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_audit_trail(asset: str = None, q: str = None, event_type: str = None,
                      page: int = 1, page_size: int = 50):
    """GET /api/method/assetcore.api.imm00.list_audit_trail

    Params (tất cả optional):
      - asset:      lọc theo 1 mã thiết bị cụ thể
      - event_type: lọc theo loại sự kiện (CAPA, Maintenance, State Change, …)
      - q:          free-text search trong name / change_summary / actor / ref_name / asset
      - page, page_size: phân trang (default 50)

    Không truyền filter → trả về N bản ghi mới nhất toàn hệ thống.

    `asset`/`event_type` là AND-filter (cột trực tiếp); `q` là OR-LIKE clause.
    Total phải đếm qua `count_with_or` để áp đúng CẢ AND lẫn OR — nếu chỉ đếm
    theo `or_filters`, pagination sẽ over-count khi có thêm `asset`/`event_type`.
    """
    page, page_size = int(page), int(page_size)
    filters: dict = {}

    if asset:
        if not frappe.db.exists(_DT_ASSET, asset):
            return _err(_(_ERR_ASSET_NOT_FOUND), 404)
        filters["asset"] = asset

    if event_type:
        filters["event_type"] = event_type

    or_filters = None
    if q:
        like = f"%{q}%"
        or_filters = [
            ["name", "like", like],
            ["asset", "like", like],
            ["change_summary", "like", like],
            ["actor", "like", like],
            ["ref_name", "like", like],
        ]

    total = count_with_or(_DT_AUDIT_TRAIL, filters, or_filters)
    pag = paginate(total, page, page_size)
    items = frappe.get_list(
        _DT_AUDIT_TRAIL,
        filters=filters,
        or_filters=or_filters,
        fields=["name", "asset", "event_type", "actor", "change_summary",
                "from_status", "to_status", "ref_doctype", "ref_name",
                "timestamp", "hash_sha256 as hash"],
        limit_start=pag["offset"],
        limit_page_length=pag["page_size"],
        order_by=_ORDER_EVENT_TS_DESC,
    )
    # Batch-enrich với asset_name (tránh N+1; dùng UX pattern "Tên chính — Mã phụ")
    asset_ids = {r.get("asset") for r in items if r.get("asset")}
    if asset_ids:
        name_map = {
            a["name"]: a["asset_name"]
            for a in frappe.get_all(
                _DT_ASSET,
                filters={"name": ["in", list(asset_ids)]},
                fields=["name", "asset_name"],
            )
        }
        for r in items:
            r["asset_name"] = name_map.get(r.get("asset"), "")
    return _ok({"pagination": pag, "items": items})


@frappe.whitelist()
def get_audit_entry(name: str):
    """GET /api/method/assetcore.api.imm00.get_audit_entry"""
    if not frappe.db.exists(_DT_AUDIT_TRAIL, name):
        return _err(_(_ERR_AUDIT_NOT_FOUND), 404)
    return _ok(frappe.get_doc(_DT_AUDIT_TRAIL, name).as_dict())


@frappe.whitelist()
def verify_chain(asset: str):
    """GET /api/method/assetcore.api.imm00.verify_chain"""
    if not frappe.db.exists(_DT_ASSET, asset):
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)
    result = verify_audit_chain(asset)
    return _ok(result)


# ─────────────────────────────────────────────────────────────────────────────
# IMM CAPA Record  (5 endpoints)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_capas(
    page: int = 1,
    page_size: int = 20,
    status: str = None,
    capa_type: str = None,
    asset: str = None,
    not_closed: int = 0,
    overdue: int = 0,
):
    """GET /api/method/assetcore.api.imm00.list_capas

    R10 §9.4.8 — virtual filters cho drill-down từ KPI qa:
      not_closed=1 → _open_capa_filter() SoT: status NOT IN [Closed] (khớp KPI 'capa_open').
      overdue=1    → _overdue_capa_filter() SoT: status NOT IN [Closed] AND
                     due_date IS NOT NULL AND due_date < today (khớp KPI 'capa_overdue').
    SSOT: cùng predicate đếm KPI ở get_overview / dashboard.py → list khớp KPI byte-for-byte.

    BR-00-16 — filter-composition CONJOIN (AND), KHÔNG clobber:
      Filter build dạng **list-of-conditions** `[[_DT_CAPA, field, op, value], ...]` để
      explicit `status == X` (drill từ chip) VÀ virtual `status NOT IN [Closed]`
      (not_closed/overdue) cùng tồn tại trên CÙNG field → AND thật. (Dict-filter cũ chỉ
      giữ 1 predicate/field → key 'status' bị filters.update() GHI ĐÈ → trả full open-set
      ~117 thay vì subset — bug #4 USER Vòng 12 'chọn status=Quá hạn vẫn 117'.)
      count VÀ get_list nhận CÙNG conditions → pagination.total == len(items) mọi tổ hợp.
    """
    page, page_size = int(page), int(page_size)
    # List-of-conditions: cho phép NHIỀU điều kiện trên CÙNG field (AND), không clobber.
    conditions: list[list] = []
    if status:
        conditions.append([_DT_CAPA, "status", "=", status])
    if capa_type:
        conditions.append([_DT_CAPA, "capa_type", "=", capa_type])
    if asset:
        conditions.append([_DT_CAPA, "asset", "=", asset])
    # overdue thắng not_closed (overdue ⊃ not-closed: NOT IN Closed + date-window).
    # SoT-adjacent: list-form của _overdue_capa_filter / _open_capa_filter (services/imm00)
    # — KHÔNG inline literal; membership == KPI capa_overdue / capa_open (round 10/11).
    # Explicit `status` (nếu có) LUÔN conjoin THÊM (AND) với cờ → 2 predicate/'status'.
    if int(overdue):
        from assetcore.services.imm00 import _overdue_capa_conditions
        conditions.extend(_overdue_capa_conditions(_DT_CAPA))
    elif int(not_closed):
        from assetcore.services.imm00 import _open_capa_conditions
        conditions.extend(_open_capa_conditions(_DT_CAPA))
    total = frappe.db.count(_DT_CAPA, filters=conditions)
    pag = paginate(total, page, page_size)
    items = frappe.get_list(
        _DT_CAPA,
        filters=conditions,
        fields=["name", "capa_type", "status", "asset", "title",
                "severity", "description", "source_type", "source_ref",
                "due_date", "owner", "creation"],
        limit_start=pag["offset"],
        limit_page_length=pag["page_size"],
        order_by=_ORDER_DUE_DATE_ASC,
    )
    _enrich(items, "asset", _DT_ASSET, "asset_name")
    return _ok({"pagination": pag, "items": items})


@frappe.whitelist()
def get_capa(name: str):
    """GET /api/method/assetcore.api.imm00.get_capa"""
    if not frappe.db.exists(_DT_CAPA, name):
        return _err(_(_ERR_CAPA_NOT_FOUND), 404)
    doc = frappe.get_doc(_DT_CAPA, name).as_dict()
    if doc.get("asset"):
        doc["asset_name"] = frappe.db.get_value(_DT_ASSET, doc["asset"], "asset_name") or ""
    return _ok(doc)


@frappe.whitelist(methods=["POST"])
def open_capa():
    """POST /api/method/assetcore.api.imm00.open_capa"""
    data = frappe.local.form_dict
    required = ("asset", "severity", "description", "responsible")
    missing = [f for f in required if not data.get(f)]
    if missing:
        return _err(_("Thiếu trường bắt buộc: {0}").format(", ".join(missing)), ErrorCode.VALIDATION)
    try:
        name = create_capa(
            asset=data["asset"],
            source_type=data.get("source_type", "Nonconformance"),
            source_ref=data.get("source_ref", ""),
            severity=data["severity"],
            description=data["description"],
            responsible=data["responsible"],
            due_days=int(data.get("due_days", 30)),
        )
        frappe.db.commit()
        return _ok({"name": name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def close_capa_record(name: str):
    """POST /api/method/assetcore.api.imm00.close_capa_record"""
    if not frappe.db.exists(_DT_CAPA, name):
        return _err(_(_ERR_CAPA_NOT_FOUND), 404)
    data = frappe.local.form_dict
    required = ("root_cause", "corrective_action", "preventive_action")
    missing = [f for f in required if not data.get(f)]
    if missing:
        return _err(_("Thiếu trường bắt buộc: {0}").format(", ".join(missing)), ErrorCode.VALIDATION)
    try:
        close_capa(
            capa_name=name,
            root_cause=data["root_cause"],
            corrective_action=data["corrective_action"],
            preventive_action=data["preventive_action"],
            effectiveness_check=data.get("effectiveness_check"),
            actor=frappe.session.user,
        )
        frappe.db.commit()
        return _ok({"name": name, "status": "Closed"})
    except ServiceError as e:
        # BR-00-26 (round 12): cổng hiệu quả CAPA raise ServiceError(VALIDATION,
        # message_code='FIN-007'). Trả 422 + message_code để FE match thông báo VI
        # 'Chưa xác minh hiệu quả — không thể đóng CAPA' (KHÔNG leak code/EN).
        frappe.db.rollback()
        return _err(e.message, e.code, message_code=e.message_code)
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist()
def list_overdue_capas(page: int = 1, page_size: int = 20):
    """GET /api/method/assetcore.api.imm00.list_overdue_capas

    SoT: dùng _overdue_capa_filter() (services/imm00) — KHÔNG inline. Predicate
    == KPI capa_overdue (dashboard.py) == imm16 get_overdue_actions → count == drill.
    """
    from assetcore.services.imm00 import _overdue_capa_filter
    page, page_size = int(page), int(page_size)
    filters = _overdue_capa_filter()
    total = frappe.db.count(_DT_CAPA, filters=filters)
    pag = paginate(total, page, page_size)
    items = frappe.get_list(
        _DT_CAPA,
        filters=filters,
        fields=["name", "capa_type", "status", "asset", "title", "due_date", "owner"],
        limit_start=pag["offset"],
        limit_page_length=pag["page_size"],
        order_by=_ORDER_DUE_DATE_ASC,
    )
    return _ok({"pagination": pag, "items": items})


# ─────────────────────────────────────────────────────────────────────────────
# Asset Lifecycle Event  (2 endpoints)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_lifecycle_events(asset: str, page: int = 1, page_size: int = 50, event_type: str = None):
    """GET /api/method/assetcore.api.imm00.list_lifecycle_events"""
    if not frappe.db.exists(_DT_ASSET, asset):
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)
    page, page_size = int(page), int(page_size)
    filters = {"asset": asset}
    if event_type:
        filters["event_type"] = event_type
    total = frappe.db.count(_DT_LIFECYCLE_EVENT, filters=filters)
    pag = paginate(total, page, page_size)
    items = frappe.get_list(
        _DT_LIFECYCLE_EVENT,
        filters=filters,
        fields=["name", "event_type", "actor", "from_status", "to_status",
                "timestamp", "root_doctype", "root_record", "notes"],
        limit_start=pag["offset"],
        limit_page_length=pag["page_size"],
        order_by=_ORDER_EVENT_TS_DESC,
    )
    return _ok({"pagination": pag, "items": items})


@frappe.whitelist()
def get_lifecycle_event(name: str):
    """GET /api/method/assetcore.api.imm00.get_lifecycle_event"""
    if not frappe.db.exists(_DT_LIFECYCLE_EVENT, name):
        return _err(_(_ERR_LIFECYCLE_NOT_FOUND), 404)
    return _ok(frappe.get_doc(_DT_LIFECYCLE_EVENT, name).as_dict())


# ─────────────────────────────────────────────────────────────────────────────
# Incident Report  (5 endpoints)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_incidents(
    page: int = 1,
    page_size: int = 20,
    status: str = None,
    severity: str = None,
    asset: str = None,
):
    """GET /api/method/assetcore.api.imm00.list_incidents"""
    page, page_size = int(page), int(page_size)
    filters = {}
    if status:
        filters["status"] = status
    if severity:
        filters["severity"] = severity
    if asset:
        filters["asset"] = asset
    total = frappe.db.count(_DT_INCIDENT, filters=filters)
    pag = paginate(total, page, page_size)
    items = frappe.get_list(
        _DT_INCIDENT,
        filters=filters,
        fields=["name", "severity", "status", "asset", "description",
                "reported_at", "incident_type", "patient_affected", "reported_to_byt"],
        limit_start=pag["offset"],
        limit_page_length=pag["page_size"],
        order_by="reported_at desc",
    )
    _enrich(items, "asset", _DT_ASSET, "asset_name")
    return _ok({"pagination": pag, "items": items})


@frappe.whitelist()
def get_incident(name: str):
    """GET /api/method/assetcore.api.imm00.get_incident"""
    if not frappe.db.exists(_DT_INCIDENT, name):
        return _err(_(_ERR_INCIDENT_NOT_FOUND), 404)
    return _ok(frappe.get_doc(_DT_INCIDENT, name).as_dict())


@frappe.whitelist(methods=["POST"])
def create_incident():
    """POST /api/method/assetcore.api.imm00.create_incident"""
    data = frappe.local.form_dict
    required = ("asset", "severity", "incident_type", "description")
    missing = [f for f in required if not data.get(f)]
    if missing:
        return _err(_("Thiếu trường bắt buộc: {0}").format(", ".join(missing)), ErrorCode.VALIDATION)
    try:
        doc = frappe.new_doc(_DT_INCIDENT)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "doctype")})
        doc.insert()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def update_incident(name: str):
    """POST /api/method/assetcore.api.imm00.update_incident"""
    if not frappe.db.exists(_DT_INCIDENT, name):
        return _err(_(_ERR_INCIDENT_NOT_FOUND), 404)
    data = frappe.local.form_dict
    try:
        doc = frappe.get_doc(_DT_INCIDENT, name)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "name", "doctype")})
        doc.save()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def submit_incident(name: str):
    """POST /api/method/assetcore.api.imm00.submit_incident — submit + create lifecycle event"""
    if not frappe.db.exists(_DT_INCIDENT, name):
        return _err(_(_ERR_INCIDENT_NOT_FOUND), 404)
    doc = frappe.get_doc(_DT_INCIDENT, name)
    if doc.docstatus == 1:
        return _err(_("Incident Report đã được submit"), 422)
    try:
        doc.submit()
        frappe.db.commit()
        return _ok({"name": name, "status": doc.status})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


# ─────────────────────────────────────────────────────────────────────────────
# Asset Transfer  (3 endpoints)
# ─────────────────────────────────────────────────────────────────────────────

def _enrich_transfer(items: list) -> None:
    """SSoT denorm phiếu Điều chuyển (Vòng 16 — FR-00-TRF-01 / §II.1.13-TRANSFERENRICH).

    Thêm ``asset_name`` + 6 khóa ``*_name`` (from/to × location/department/custodian)
    vào MỖI item, coalesce ``''`` qua nhánh ``_enrich(blank_missing=True)``
    (NEVER raw Link-id, NEVER ``None``, khóa LUÔN present). Batch IN-query mỗi
    field ⇒ N+1-free, O(1)/số phiếu. 1 code-path DUY NHẤT cho
    ``list_transfers`` / ``get_transfer`` / ``get_transfer_full`` (One-Version parity).
    """
    _enrich(items, "asset", _DT_ASSET, "asset_name", "asset_name", blank_missing=True)
    _enrich(items, "from_location", _DT_LOCATION, "location_name", "from_location_name", blank_missing=True)
    _enrich(items, "to_location", _DT_LOCATION, "location_name", "to_location_name", blank_missing=True)
    _enrich(items, "from_department", _DT_DEPARTMENT, "department_name", "from_department_name", blank_missing=True)
    _enrich(items, "to_department", _DT_DEPARTMENT, "department_name", "to_department_name", blank_missing=True)
    _enrich(items, "from_custodian", "User", "full_name", "from_custodian_name", blank_missing=True)
    _enrich(items, "to_custodian", "User", "full_name", "to_custodian_name", blank_missing=True)


@frappe.whitelist()
def list_transfers(asset: str = None, status: str = None,
                   transfer_type: str = None,
                   page: int = 1, page_size: int = 20):
    """GET /api/method/assetcore.api.imm00.list_transfers"""
    page, page_size = int(page), int(page_size)
    filters = {}
    if asset:
        filters["asset"] = asset
    if status:
        filters["status"] = status
    if transfer_type:
        filters["transfer_type"] = transfer_type
    total = frappe.db.count(_DT_TRANSFER, filters=filters)
    pag = paginate(total, page, page_size)
    items = frappe.get_list(
        _DT_TRANSFER,
        filters=filters,
        fields=["name", "asset", "transfer_date", "transfer_type", "status",
                "from_location", "to_location", "from_department", "to_department",
                "from_custodian", "to_custodian", "reason",
                "approved_by", "approval_date", "received_by", "received_date"],
        limit_start=pag["offset"],
        limit_page_length=pag["page_size"],
        order_by="transfer_date desc",
    )
    # Vòng 16 (FR-00-TRF-01) — denorm asset_name + 6 *_name (from/to location/
    # department/custodian) qua SSoT enrich N+1-free, coalesce '' (NEVER raw
    # Link-id). Chạy SAU count/get_list ⇒ pagination.total + len(items) bất biến.
    _enrich_transfer(items)
    return _ok({"pagination": pag, "items": items})


@frappe.whitelist()
def get_transfer(name: str):
    """GET /api/method/assetcore.api.imm00.get_transfer"""
    if not frappe.db.exists(_DT_TRANSFER, name):
        return _err(_(_ERR_TRANSFER_NOT_FOUND), 404)
    doc = frappe.get_doc(_DT_TRANSFER, name).as_dict()
    # Vòng 16 (FR-00-TRF-01) — enrich asset_name + 6 *_name (parity list_transfers).
    _enrich_transfer([doc])
    return _ok(doc)


@frappe.whitelist(methods=["POST"])
def create_transfer():
    """POST — Tạo phiếu yêu cầu luân chuyển (status = Pending Approval)."""
    data = {k: v for k, v in frappe.local.form_dict.items() if k not in ("cmd", "doctype")}
    try:
        return _ok(create_transfer_request(data))
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def delete_transfer(name: str):
    """POST — Hủy phiếu luân chuyển (chỉ khi Pending Approval hoặc Rejected)."""
    try:
        return _ok(cancel_transfer_request(name))
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


# ─────────────────────────────────────────────────────────────────────────────
# Service Contract  (4 endpoints)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_service_contracts(
    supplier: str = None,
    contract_type: str = None,
    page: int = 1,
    page_size: int = 20,
):
    """GET /api/method/assetcore.api.imm00.list_service_contracts"""
    try:
        page, page_size = int(page), int(page_size)
        filters = {}
        if supplier:
            filters["supplier"] = supplier
        if contract_type:
            filters["contract_type"] = contract_type
        total = frappe.db.count(_DT_SERVICE_CONTRACT, filters=filters)
        pag = paginate(total, page, page_size)
        items = frappe.get_list(
            _DT_SERVICE_CONTRACT,
            filters=filters,
            fields=["name", "contract_title", "supplier", "contract_type",
                    "contract_start", "contract_end", "contract_value", "sla_response_hours"],
            limit_start=pag["offset"],
            limit_page_length=pag["page_size"],
            order_by="contract_end asc",
        )
        _enrich(items, "supplier", _DT_SUPPLIER, "supplier_name")
        return _ok({"pagination": pag, "items": items})
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "list_service_contracts error")
        return _err(str(e))


@frappe.whitelist()
def get_service_contract(name: str):
    """GET /api/method/assetcore.api.imm00.get_service_contract"""
    if not frappe.db.exists(_DT_SERVICE_CONTRACT, name):
        return _err(_(_ERR_CONTRACT_NOT_FOUND), 404)
    doc = frappe.get_doc(_DT_SERVICE_CONTRACT, name).as_dict()
    if doc.get("supplier"):
        doc["supplier_name"] = frappe.db.get_value(_DT_SUPPLIER, doc["supplier"], "supplier_name") or doc["supplier"]
    return _ok(doc)


def _normalize_covered_assets(raw):
    """Chuẩn hóa payload child-table `covered_assets`.

    FE gửi list[dict] (hoặc JSON string khi qua form-encoded). Chỉ giữ
    `asset` + `coverage_note`, bỏ dòng trống và khử trùng lặp theo asset.
    `asset_name` do DocType tự fetch_from nên không nhận từ client.
    """
    if raw is None:
        return None
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return []
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            frappe.throw(_("Danh sách thiết bị không hợp lệ"), frappe.exceptions.ValidationError)
    if not isinstance(raw, (list, tuple)):
        frappe.throw(_("Danh sách thiết bị không hợp lệ"), frappe.exceptions.ValidationError)
    rows, seen = [], set()
    for r in raw:
        if not isinstance(r, dict):
            continue
        asset = (r.get("asset") or "").strip()
        if not asset or asset in seen:
            continue
        seen.add(asset)
        rows.append({"asset": asset, "coverage_note": (r.get("coverage_note") or "").strip()})
    return rows


@frappe.whitelist(methods=["POST"])
def create_service_contract():
    """POST /api/method/assetcore.api.imm00.create_service_contract"""
    data = frappe.local.form_dict
    required = ("contract_title", "supplier", "contract_type", "contract_start", "contract_end")
    missing = [f for f in required if not data.get(f)]
    if missing:
        return _err(_("Thiếu trường bắt buộc: {0}").format(", ".join(missing)), ErrorCode.VALIDATION)
    try:
        covered_assets = _normalize_covered_assets(data.get("covered_assets"))
        doc = frappe.new_doc(_DT_SERVICE_CONTRACT)
        doc.update({k: v for k, v in data.items()
                    if k not in ("cmd", "doctype", "covered_assets")})
        for row in (covered_assets or []):
            doc.append("covered_assets", row)
        doc.insert()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def update_service_contract(name: str):
    """POST /api/method/assetcore.api.imm00.update_service_contract"""
    if not frappe.db.exists(_DT_SERVICE_CONTRACT, name):
        return _err(_(_ERR_CONTRACT_NOT_FOUND), 404)
    data = frappe.local.form_dict
    try:
        doc = frappe.get_doc(_DT_SERVICE_CONTRACT, name)
        if doc.docstatus == 1:
            return _err(_("Hợp đồng đã submit, không thể sửa"), 422)
        doc.update({k: v for k, v in data.items()
                    if k not in ("cmd", "name", "doctype", "covered_assets")})
        # covered_assets chỉ thay thế khi client gửi field này (None = giữ nguyên)
        if "covered_assets" in data:
            doc.set("covered_assets", _normalize_covered_assets(data.get("covered_assets")) or [])
        doc.save()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


# Service Contract là DocType lưu trữ đơn giản — không có luồng duyệt.
# Lifecycle: create → update → delete (hoặc để contract_end qua hạn = tự deprecate).
# Dùng làm tham chiếu cho PM / Calibration / Repair WO khi thiết bị có hợp đồng.


@frappe.whitelist(methods=["POST"])
def delete_service_contract(name: str):
    """POST /api/method/assetcore.api.imm00.delete_service_contract"""
    if not frappe.db.exists(_DT_SERVICE_CONTRACT, name):
        return _err(_(_ERR_CONTRACT_NOT_FOUND), 404)
    try:
        doc = frappe.get_doc(_DT_SERVICE_CONTRACT, name)
        if doc.docstatus == 1:
            doc.cancel()
        frappe.delete_doc(_DT_SERVICE_CONTRACT, name, ignore_permissions=False)
        frappe.db.commit()
        return _ok({"name": name, "deleted": True})
    except (frappe.exceptions.ValidationError, frappe.exceptions.LinkExistsError) as e:
        return _err(str(e), ErrorCode.VALIDATION)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "delete_service_contract error")
        return _err(_("Không thể xóa hợp đồng"), ErrorCode.INTERNAL)


@frappe.whitelist()
def list_asset_contracts(asset: str):
    """GET /api/method/assetcore.api.imm00.list_asset_contracts — contracts covering a specific asset"""
    if not frappe.db.exists(_DT_ASSET, asset):
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)
    rows = frappe.db.sql(
        """
        SELECT sc.name, sc.contract_title, sc.supplier, sc.contract_type,
               sc.contract_start, sc.contract_end, sc.sla_response_hours
        FROM `tabService Contract` sc
        INNER JOIN `tabService Contract Asset` sca ON sca.parent = sc.name
        WHERE sca.asset = %s AND sc.docstatus = 1
        ORDER BY sc.contract_end ASC
        """,
        (asset,),
        as_dict=True,
    )
    return _ok(rows)


# ─────────────────────────────────────────────────────────────────────────────
# Scheduler triggers  (3 endpoints — for testing / manual trigger)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def trigger_capa_overdue_check():
    """GET /api/method/assetcore.api.imm00.trigger_capa_overdue_check — admin only"""
    _assert_system_admin()
    from assetcore.services.imm00 import check_capa_overdue
    check_capa_overdue()
    return _ok({"triggered": "check_capa_overdue"})


@frappe.whitelist()
def trigger_contract_expiry_check():
    """GET /api/method/assetcore.api.imm00.trigger_contract_expiry_check — admin only"""
    _assert_system_admin()
    from assetcore.services.imm00 import check_vendor_contract_expiry
    check_vendor_contract_expiry()
    return _ok({"triggered": "check_vendor_contract_expiry"})


@frappe.whitelist()
def trigger_registration_expiry_check():
    """GET /api/method/assetcore.api.imm00.trigger_registration_expiry_check — admin only"""
    _assert_system_admin()
    from assetcore.services.imm00 import check_registration_expiry
    check_registration_expiry()
    return _ok({"triggered": "check_registration_expiry"})


# ─────────────────────────────────────────────────────────────────────────────
# Reference Data — Generic Update / Delete (Location, Department, Category)
# ─────────────────────────────────────────────────────────────────────────────

def _generic_update(doctype: str, name: str):
    if not frappe.db.exists(doctype, name):
        return _err(_("Không tìm thấy {0}").format(doctype), ErrorCode.NOT_FOUND)
    data = frappe.local.form_dict
    try:
        doc = frappe.get_doc(doctype, name)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "name", "doctype")})
        doc.flags.ignore_links = True
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), ErrorCode.BUSINESS_RULE)


def _generic_delete(doctype: str, name: str):
    if not frappe.db.exists(doctype, name):
        return _err(_("Không tìm thấy {0}").format(doctype), ErrorCode.NOT_FOUND)
    try:
        frappe.delete_doc(doctype, name, ignore_permissions=False)
        frappe.db.commit()
        return _ok({"name": name, "deleted": True})
    except frappe.exceptions.LinkExistsError as e:
        return _err(_("Không thể xóa — đang được tham chiếu: {0}").format(e),
                    ErrorCode.CONFLICT)
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), ErrorCode.BUSINESS_RULE)
    except Exception:
        frappe.log_error(frappe.get_traceback(), f"delete {doctype} error")
        return _err(_("Không thể xóa {0}").format(doctype), ErrorCode.INTERNAL)


@frappe.whitelist(methods=["POST"])
def update_location(name: str):
    return _generic_update(_DT_LOCATION, name)


@frappe.whitelist(methods=["POST"])
def delete_location(name: str):
    return _generic_delete(_DT_LOCATION, name)


@frappe.whitelist(methods=["POST"])
def update_department(name: str):
    return _generic_update(_DT_DEPARTMENT, name)


@frappe.whitelist(methods=["POST"])
def delete_department(name: str):
    return _generic_delete(_DT_DEPARTMENT, name)


@frappe.whitelist(methods=["POST"])
def update_asset_category(name: str):
    return _generic_update(_DT_ASSET_CATEGORY, name)


@frappe.whitelist(methods=["POST"])
def delete_asset_category(name: str):
    return _generic_delete(_DT_ASSET_CATEGORY, name)


@frappe.whitelist(methods=["POST"])
def delete_supplier(name: str):
    return _generic_delete(_DT_SUPPLIER, name)


@frappe.whitelist(methods=["POST"])
def delete_device_model(name: str):
    return _generic_delete(_DT_DEVICE_MODEL, name)


@frappe.whitelist(methods=["POST"])
def delete_asset(name: str):
    return _generic_delete(_DT_ASSET, name)


@frappe.whitelist(methods=["POST"])
def delete_incident(name: str):
    return _generic_delete(_DT_INCIDENT, name)


# ─────────────────────────────────────────────────────────────────────────────
# IMM SLA Policy — full CRUD
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_sla_policy(name: str):
    if not frappe.db.exists(_DT_SLA_POLICY, name):
        return _err(_("SLA Policy not found"), 404)
    d = frappe.get_doc(_DT_SLA_POLICY, name).as_dict()
    # Normalize Check fields về int 0/1 để FE compare chính xác
    d["is_active"] = 1 if d.get("is_active") else 0
    d["is_default"] = 1 if d.get("is_default") else 0
    return _ok(d)


_SLA_CHECK_FIELDS = ("is_active", "is_default")


def _coerce_sla_payload(data: dict) -> dict:
    """Ép Check fields về int 0/1 để tránh sai lệch khi FE gửi '0'/'1' string."""
    out = {k: v for k, v in data.items() if k not in ("cmd", "doctype", "name")}
    for f in _SLA_CHECK_FIELDS:
        if f in out:
            v = out[f]
            out[f] = 1 if str(v).lower() in ("1", "true", "yes", "on") else 0
    return out


@frappe.whitelist(methods=["POST"])
def create_sla_policy():
    try:
        doc = frappe.new_doc(_DT_SLA_POLICY)
        doc.update(_coerce_sla_payload(dict(frappe.local.form_dict)))
        doc.insert()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def update_sla_policy(name: str):
    if not frappe.db.exists(_DT_SLA_POLICY, name):
        return _err(_("SLA Policy not found"), 404)
    try:
        doc = frappe.get_doc(_DT_SLA_POLICY, name)
        doc.update(_coerce_sla_payload(dict(frappe.local.form_dict)))
        doc.save()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def delete_sla_policy(name: str):
    return _generic_delete(_DT_SLA_POLICY, name)


# ─────────────────────────────────────────────────────────────────────────────
# Incident — update/submit already exist; add get_supplier read
# ─────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
# Depreciation (straight-line calculation)
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def compute_depreciation(name: str):
    """Sinh schedule (nếu thiếu) + chạy mọi kỳ đến hạn cho 1 asset, đến today.

    - Nếu chưa có schedule → `generate_schedule(force=False)`.
    - Mark Executed cho mọi dòng Pending có `scheduled_date <= today`.
    - Cập nhật accumulated_depreciation + current_book_value trên asset.
    - Trả về summary mới (đã refresh).
    """
    from assetcore.services import depreciation as depr_svc

    if not frappe.db.exists(_DT_ASSET, name):
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)

    rows_count = frappe.db.count(
        "AC Asset Depreciation Schedule",
        {"parent": name, "parenttype": _DT_ASSET},
    )
    generated = False
    if rows_count == 0:
        # RC-01: surface generate errors instead of letting them propagate as 500
        # (which the FE shows as a generic "Lỗi" toast).
        try:
            gen_res = depr_svc.generate_schedule(name, force=False)
        except (frappe.LinkValidationError, frappe.ValidationError) as e:
            return _err(str(e), 422)
        if gen_res.get("skipped"):
            return _err(
                _("Không sinh được lịch khấu hao: {0}").format(gen_res.get("reason") or ""),
                422,
            )
        generated = True

    try:
        run_res = depr_svc.run_due_depreciation(asset=name)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"RC-01 compute_depreciation run failed: {name}")
        return _err(_("Lỗi khi chạy khấu hao: {0}").format(str(e)), 500)

    a = frappe.db.get_value(
        _DT_ASSET, name,
        ["gross_purchase_amount", "residual_value",
         "accumulated_depreciation", "current_book_value",
         "depreciation_method"],
        as_dict=True,
    ) or {}
    gross = float(a.get("gross_purchase_amount") or 0)
    accumulated = float(a.get("accumulated_depreciation") or 0)
    # BR-05-13: SoT đọc book — None→gross, 0.0→0.0 (KHÔNG inline `or gross`).
    book_value = depr_svc.effective_book_value(a)
    pct = round(accumulated / gross * 100, 1) if gross > 0 else 0.0
    return _ok({
        "name": name,
        "accumulated": accumulated,
        "book_value": book_value,
        "method": a.get("depreciation_method") or "",
        "pct_depreciated": pct,
        "schedule_generated": generated,
        "executed_rows": run_res.get("executed_rows", 0),
    })


# ─────────────────────────────────────────────────────────────────────────────
# Asset Transfer — Workflow endpoints
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_transfer_full(name: str):
    """GET — Lấy toàn bộ thông tin phiếu luân chuyển."""
    if not frappe.db.exists(_DT_TRANSFER, name):
        return _err(_("Phiếu luân chuyển không tồn tại"), 404)
    doc = frappe.get_doc(_DT_TRANSFER, name).as_dict()
    # Vòng 16 (FR-00-TRF-01) — consumer web AssetTransferDetailView.vue: enrich
    # asset_name + 6 *_name (from/to location/department/custodian) coalesce ''
    # ⇒ màn chi tiết KHÔNG còn rò Link-id thô (parity get_transfer/list_transfers).
    _enrich_transfer([doc])
    # CR-WF-00-TRANSFER-AUTHZ — server-driven CTA authz (CHỈ get_transfer_full, KHÔNG
    # đụng _enrich_transfer → giữ list_transfers/get_transfer rows parity, tránh N+1
    # rbac.can trên list). FE gate 3 nút theo can_approve/can_receive (mirror imm14 R39).
    doc.update(transfer_cta_flags(doc.get("status")))
    return _ok(doc)


@frappe.whitelist(methods=["POST"])
def update_transfer(name: str):
    """POST — Cập nhật thông tin phiếu luân chuyển (chỉ khi Pending Approval).

    CR-WF-00-EDIT-AUTHZ: bịt lỗ missing-authorization write (custody-hole) — trước đây
    THIẾU rbac.require ⇒ mọi user login (kể cả Inventory User không có commissioning.write)
    sửa được đích/khoa/người nhận/ngày/lý do/ghi chú qua ``_generic_update`` (chạy
    ``ignore_permissions=True``). Thứ tự chốt bởi BA: tồn tại (404) → ``rbac.require``
    (403) → status Pending (422). Handler KHÔNG try/except ⇒ ``PermissionError`` từ
    ``rbac.require`` propagate tự nhiên → HTTP-403; status-gate 422 GIỮ NGUYÊN (user CÓ
    cap mới đến được status-check ⇒ KHÔNG bị rbac che thành 403). Base/Inventory user sửa
    phiếu SAI status vẫn 403 (rbac trước status ⇒ không rò trạng thái).
    """
    if not frappe.db.exists(_DT_TRANSFER, name):
        return _err(_("Phiếu luân chuyển không tồn tại"), 404)
    rbac.require(_TRANSFER_EDIT_CAP)
    if frappe.db.get_value(_DT_TRANSFER, name, "status") != "Pending Approval":
        return _err(_("Chỉ có thể chỉnh sửa phiếu đang Pending Approval"), 422)
    return _generic_update(_DT_TRANSFER, name)


@frappe.whitelist(methods=["POST"])
def approve_transfer(name: str):
    """POST — Phê duyệt phiếu luân chuyển → cập nhật vị trí thiết bị ngay."""
    try:
        return _ok(approve_transfer_request(name))
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def reject_transfer(name: str, rejection_reason: str = ""):
    """POST — Từ chối phiếu luân chuyển."""
    try:
        return _ok(reject_transfer_request(name, rejection_reason))
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def receive_transfer(name: str, handover_notes: str = "", client_request_id: str = ""):
    """POST — Bên nhận xác nhận đã tiếp nhận thiết bị.

    `client_request_id` (CR-24 idempotency): khoá do client (mobile write-outbox)
    sinh — CÙNG khoá gọi 2 lần trên 1 phiếu chỉ set_value/audit/lifecycle 1 lần;
    call trùng REPLAY envelope `{name, status:'Received', received_by}` (KHÔNG throw
    BAD_STATE, KHÔNG nhân đôi vết custody NĐ98). Header `X-Idempotency-Key` fallback
    khi param vắng (param THẮNG header). Rỗng cả hai → NO-OP legacy (backward-compat
    100%). str='' (KHÔNG str|None → tránh HTTP 417 pydantic-coercion).
    """
    try:
        return _ok(confirm_receipt(name, handover_notes, client_request_id=client_request_id))
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist()
def get_pending_approvals_inbox(**_ignore) -> dict:
    """GET — Inbox gộp "Phiếu chờ tôi duyệt" xuyên module (APPROVAL-INBOX-CR32).

    Session-scoped: KHÔNG nhận param ``user`` — ``**_ignore`` nuốt kwargs lạ
    (chống spoof đọc inbox người khác). Guest/no-session → dispatcher-403
    (bare @whitelist, KHÔNG allow_guest). Controller mỏng: gộp/gate/enrich nằm
    trọn ở service (services/imm00.get_pending_approvals_inbox); envelope
    Decision-B qua ``handle()``.
    """
    from assetcore.services.imm00 import (
        get_pending_approvals_inbox as _svc_get_pending_approvals_inbox,
    )
    return handle(_svc_get_pending_approvals_inbox)


# ─────────────────────────────────────────────────────────────────────────────
# PM Schedule — List / CRUD (delegates basic fields)
# ─────────────────────────────────────────────────────────────────────────────

_DT_PM_SCHEDULE = "PM Schedule"
_DT_PM_TEMPLATE = "PM Checklist Template"
_DT_FIRMWARE_CR = "Firmware Change Request"
_DT_DOC_REQUEST = "Document Request"


def _paginated_list(doctype: str, filters: dict, fields: list[str],
                    page: int, page_size: int, order_by: str = _ORDER_MODIFIED_DESC,
                    # Optional[list] (KHÔNG dạng union-None PEP-604): helper PRIVATE
                    # không whitelist — guard ADR test_oas_signatures cấm text-form đó
                    # trong api/*.py (chống 417 GET-coercion lan vào whitelist signature).
                    or_filters: Optional[list] = None):
    offset = (page - 1) * page_size
    if or_filters:
        # frappe.db.count KHÔNG nhận or_filters → total = len(name-only query) với
        # cùng ngữ nghĩa (AND filters) AND (OR or_filters). Giữ total ĐÚNG khi có
        # tìm kiếm (không thể suy total từ trang bị cắt — đúng lớp bug đang fix).
        total = len(frappe.get_all(doctype, filters=filters, or_filters=or_filters,
                                   fields=["name"], limit=0))
    else:
        total = frappe.db.count(doctype, filters)
    items = frappe.get_all(doctype, filters=filters, or_filters=or_filters, fields=fields,
                           order_by=order_by, limit=page_size, start=offset)
    return items, {"total": total, "page": page, "page_size": page_size}


def _search_or_filters(search: str, fields: list[str]) -> list | None:
    """Build or_filters LIKE %search% trên nhiều field (OR). None nếu search rỗng."""
    if not search or not search.strip():
        return None
    like = f"%{search.strip()}%"
    return [[fld, "like", like] for fld in fields]


@frappe.whitelist()
def list_pm_schedules(page: int = 1, page_size: int = 20, asset: str = None,
                      status: str = None, pm_type: str = None, search: str = None):
    f = {}
    if asset: f["asset_ref"] = asset
    if status: f["status"] = status
    if pm_type: f["pm_type"] = pm_type
    of = _search_or_filters(search, ["name", "asset_ref", "checklist_template",
                                     "responsible_technician"])
    items, meta = _paginated_list(_DT_PM_SCHEDULE, f,
        ["name", "asset_ref", "pm_type", "status", "pm_interval_days",
         "checklist_template", "responsible_technician",
         "last_pm_date", "next_due_date"],
        int(page), int(page_size), "next_due_date asc", or_filters=of)
    asset_ids = {r.get("asset_ref") for r in items if r.get("asset_ref")}
    if asset_ids:
        info_map = {a["name"]: a for a in frappe.get_all(
            _DT_ASSET, filters={"name": ["in", list(asset_ids)]},
            fields=["name", "asset_name", "asset_code"])}
        for r in items:
            info = info_map.get(r.get("asset_ref")) or {}
            r["asset_name"] = info.get("asset_name") or ""
            r["asset_code"] = info.get("asset_code") or ""
    return _ok({"items": items, **meta})


@frappe.whitelist()
def get_pm_schedule(name: str):
    if not frappe.db.exists(_DT_PM_SCHEDULE, name):
        return _err(_("Không tìm thấy lịch PM"), ErrorCode.NOT_FOUND)
    return _ok(frappe.get_doc(_DT_PM_SCHEDULE, name).as_dict())


@frappe.whitelist(methods=["POST"])
def create_pm_schedule():
    data = frappe.local.form_dict
    # Validate field-level trước khi insert — trả fields cho FE highlight.
    missing = {}
    if not data.get("asset_ref"):
        missing["asset_ref"] = _("Vui lòng chọn thiết bị")
    if not data.get("checklist_template"):
        missing["checklist_template"] = _("Vui lòng chọn template checklist")
    if not data.get("pm_interval_days"):
        missing["pm_interval_days"] = _("Vui lòng nhập chu kỳ (ngày)")
    if missing:
        return _err(_("Thiếu thông tin bắt buộc"),
                    ErrorCode.VALIDATION, fields=missing)

    try:
        doc = frappe.new_doc(_DT_PM_SCHEDULE)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "doctype")})
        doc.insert()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.DuplicateEntryError:
        return _err(_("Lịch PM đã tồn tại cho thiết bị + loại PM này"),
                    ErrorCode.CONFLICT)
    except frappe.exceptions.LinkValidationError as e:
        return _err(str(e), ErrorCode.VALIDATION)
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), ErrorCode.BUSINESS_RULE)


@frappe.whitelist(methods=["POST"])
def update_pm_schedule(name: str):
    return _generic_update(_DT_PM_SCHEDULE, name)


@frappe.whitelist(methods=["POST"])
def delete_pm_schedule(name: str):
    return _generic_delete(_DT_PM_SCHEDULE, name)


# ─────────────────────────────────────────────────────────────────────────────
# PM Checklist Template — List / CRUD
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_pm_templates(page: int = 1, page_size: int = 50):
    items, meta = _paginated_list(_DT_PM_TEMPLATE, {},
        ["name", "template_name", "asset_category", "pm_type", "version", "effective_date"],
        int(page), int(page_size), _ORDER_MODIFIED_DESC)
    return _ok({"items": items, **meta})


@frappe.whitelist()
def get_pm_template(name: str):
    if not frappe.db.exists(_DT_PM_TEMPLATE, name):
        return _err(_("Template not found"), 404)
    return _ok(frappe.get_doc(_DT_PM_TEMPLATE, name).as_dict())


@frappe.whitelist(methods=["POST"])
def create_pm_template():
    data = frappe.local.form_dict
    try:
        doc = frappe.new_doc(_DT_PM_TEMPLATE)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "doctype")})
        doc.insert()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def update_pm_template(name: str):
    return _generic_update(_DT_PM_TEMPLATE, name)


@frappe.whitelist(methods=["POST"])
def delete_pm_template(name: str):
    return _generic_delete(_DT_PM_TEMPLATE, name)


# ─────────────────────────────────────────────────────────────────────────────
# Firmware Change Request — List / CRUD
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_firmware_crs(page: int = 1, page_size: int = 20, status: str = None,
                      asset: str = None, search: str = None):
    f = {}
    if status: f["status"] = status
    if asset: f["asset_ref"] = asset
    of = _search_or_filters(search, ["name", "asset_ref", "version_before",
                                     "version_after", "source_reference"])
    items, meta = _paginated_list(_DT_FIRMWARE_CR, f,
        ["name", "asset_ref", "version_before", "version_after", "status",
         "approved_by", "approved_datetime", "applied_datetime"],
        int(page), int(page_size), or_filters=of)
    _enrich(items, "asset_ref", _DT_ASSET, "asset_name", "asset_name")
    _enrich(items, "approved_by", "User", "full_name", "approved_by_name")
    return _ok({"items": items, **meta})


# Field điều khiển state-machine FCR — status CHỈ đổi qua transition_firmware_cr;
# CRUD chung (update_firmware_cr) VÀ create_firmware_cr STRIP các field này
# (BR-09-19b, ADR-IMM09-FCR-01).
_FCR_CONTROLLED_FIELDS = {"status", "approved_by", "approved_datetime",
                          "applied_datetime", "rollback_reason"}
# Trạng thái khởi tạo bất biến — MỌI FCR tạo qua create_firmware_cr LUÔN ở 'Draft'
# (⟺ DocType default + services.imm09.FirmwareStatus.DRAFT; guard test chống drift:
# TestFirmwareCrCreateGuard.test_initial_status_constant_matches_doctype_default_and_enum).
_FCR_INITIAL_STATUS = "Draft"


@frappe.whitelist()
def get_firmware_cr(name: str):
    if not frappe.db.exists(_DT_FIRMWARE_CR, name):
        return _err(_("FCR not found"), 404)
    doc = frappe.get_doc(_DT_FIRMWARE_CR, name).as_dict()
    items = [doc]
    _enrich(items, "asset_ref", _DT_ASSET, "asset_name", "asset_name")
    _enrich(items, "approved_by", "User", "full_name", "approved_by_name")
    # Server-driven CTA (BR-09-20): allowed_transitions LỌC theo capability caller
    # + cờ can_approve. FE gate nút CHỈ theo 2 field này (KHÔNG hardcode
    # fcr.status==='X'). Lazy-import services.imm09 (né circular).
    from assetcore.services import imm09 as _svc09
    allowed, can_approve = _svc09.firmware_allowed_transitions(doc.get("status"))
    doc["allowed_transitions"] = allowed
    doc["can_approve"] = bool(can_approve)   # boolean cho FE (=== true), KHÔNG int 1
    return _ok(doc)


@frappe.whitelist(methods=["POST"])
def create_firmware_cr():
    # BR-09-19b (create path): STRIP field điều khiển state-machine khỏi payload TẠO
    # → FCR LUÔN khởi tạo ở 'Draft'. Repair User (DocPerm create=1, submit=0, KHÔNG
    # capability firmware.approve) KHÔNG được POST status='Applied'/'Approved' để nhảy
    # thẳng vào trạng thái đã duyệt/áp dụng, bỏ qua capability-gate + valid-transition
    # guard + audit Lifecycle Event (governance NĐ98 change-control). Đối xứng
    # update_firmware_cr. Status FCR CHỈ đổi qua transition_firmware_cr.
    data = frappe.local.form_dict
    try:
        doc = frappe.new_doc(_DT_FIRMWARE_CR)
        doc.update({
            k: v for k, v in data.items()
            if k not in ("cmd", "doctype") and k not in _FCR_CONTROLLED_FIELDS
        })
        doc.status = _FCR_INITIAL_STATUS   # bất biến: tạo LUÔN ở Draft (belt-and-braces)
        doc.insert()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def update_firmware_cr(name: str):
    # BR-09-19b: STRIP field điều khiển state-machine khỏi payload CRUD chung →
    # status FCR KHÔNG BAO GIỜ đổi qua đây (dù caller gửi status=Approved). Field
    # mô tả tự do (change_notes/source_reference/version_*) vẫn sửa được.
    data = frappe.local.form_dict
    for f in _FCR_CONTROLLED_FIELDS:
        data.pop(f, None)
    return _generic_update(_DT_FIRMWARE_CR, name)


@frappe.whitelist(methods=["POST"])
def transition_firmware_cr(name: str, action: str, reason: str = ""):
    """POST /api/method/assetcore.api.imm00.transition_firmware_cr

    Transition FCR có kiểm soát SERVER-side (capability-role + valid-transition
    guard + audit trail Lifecycle Event). `action` ∈ {submit, approve, deploy,
    rollback}; `reason` BẮT BUỘC cho 'rollback'. Controller mỏng — logic ở
    services/imm09.py (co-locate cạnh firmware repair). Lazy-import né circular.
    Lỗi nghiệp vụ (cap/cạnh/reason/not-found) → HTTP-200 Error envelope qua
    `handle` (ADR-IMM09-FCR-03), KHÔNG raise→4xx."""
    from assetcore.services import imm09 as _svc09
    return handle(_svc09.transition_firmware_cr, name, action=action, reason=reason)


@frappe.whitelist(methods=["POST"])
def delete_firmware_cr(name: str):
    return _generic_delete(_DT_FIRMWARE_CR, name)


# ─────────────────────────────────────────────────────────────────────────────
# Document Request — List / CRUD
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def list_document_requests(page: int = 1, page_size: int = 20, status: str = None,
                           asset: str = None, priority: str = None, search: str = None):
    f = {}
    if status: f["status"] = status
    if asset: f["asset_ref"] = asset
    if priority: f["priority"] = priority
    of = _search_or_filters(search, ["name", "asset_ref", "doc_type_required",
                                     "doc_category"])
    items, meta = _paginated_list(_DT_DOC_REQUEST, f,
        ["name", "asset_ref", "doc_type_required", "doc_category", "status",
         "priority", "assigned_to", "due_date", "fulfilled_by"],
        int(page), int(page_size), _ORDER_DUE_DATE_ASC, or_filters=of)
    _enrich(items, "asset_ref", _DT_ASSET, "asset_name", "asset_name")
    _enrich(items, "assigned_to", "User", "full_name", "assigned_to_name")
    return _ok({"items": items, **meta})


@frappe.whitelist()
def get_document_request(name: str):
    if not frappe.db.exists(_DT_DOC_REQUEST, name):
        return _err(_("Document Request not found"), 404)
    return _ok(frappe.get_doc(_DT_DOC_REQUEST, name).as_dict())


@frappe.whitelist(methods=["POST"])
def create_document_request():
    data = frappe.local.form_dict
    try:
        doc = frappe.new_doc(_DT_DOC_REQUEST)
        doc.update({k: v for k, v in data.items() if k not in ("cmd", "doctype")})
        doc.insert()
        frappe.db.commit()
        return _ok({"name": doc.name})
    except frappe.exceptions.ValidationError as e:
        return _err(str(e), 422)


@frappe.whitelist(methods=["POST"])
def update_document_request(name: str):
    return _generic_update(_DT_DOC_REQUEST, name)


@frappe.whitelist(methods=["POST"])
def delete_document_request(name: str):
    return _generic_delete(_DT_DOC_REQUEST, name)


# ─────────────────────────────────────────────────────────────────────────────
# Asset Downtime Metrics
# ─────────────────────────────────────────────────────────────────────────────


@frappe.whitelist()
def get_asset_downtime_metrics(asset_name: str, year: str = ""):
    """Trả về thống kê dừng máy của 1 asset:
    - total_hours: tổng giờ dừng (closed + open đến hiện tại)
    - breakdown_count: số lần dừng máy (số log)
    - mttr_hours: Mean Time To Repair = total_hours / breakdown_count
    - by_reason: phân loại giờ dừng theo reason
    - current_open: log đang mở (nếu có)
    """
    if not frappe.db.exists("AC Asset", asset_name):
        return _err(_("Không tìm thấy thiết bị"), 404)

    now_dt = frappe.utils.now_datetime()
    y = int(year) if year else frappe.utils.getdate(frappe.utils.nowdate()).year
    start_of_year = f"{y}-01-01 00:00:00"
    end_of_year = f"{y}-12-31 23:59:59"

    rows = frappe.get_all(
        _DT_DOWNTIME_LOG,
        filters={
            "asset": asset_name,
            "start_time": ["between", [start_of_year, end_of_year]],
        },
        fields=["name", "reason", "start_time", "end_time",
                "downtime_hours", "is_open", "reference_doctype", "reference_name"],
        order_by="start_time desc",
        limit_page_length=0,
    )

    total_hours = 0.0
    by_reason: dict[str, float] = {}
    current_open = None
    for r in rows:
        if r["is_open"]:
            hrs = frappe.utils.time_diff_in_hours(now_dt, r["start_time"])
            current_open = {**r, "downtime_hours_so_far": round(hrs, 2)}
        else:
            hrs = float(r["downtime_hours"] or 0)
        total_hours += hrs
        by_reason[r["reason"]] = round(by_reason.get(r["reason"], 0.0) + hrs, 2)

    count = len(rows)
    mttr = round(total_hours / count, 2) if count else 0.0

    return _ok({
        "asset": asset_name,
        "year": y,
        "total_hours": round(total_hours, 2),
        "breakdown_count": count,
        "mttr_hours": mttr,
        "by_reason": by_reason,
        "current_open": current_open,
        "logs": rows[:10],
    })


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _assert_system_admin():
    """Gate System Admin via capability `data.admin` (RBAC module-based)."""
    from assetcore.services.shared import rbac
    if not rbac.can("data.admin"):
        frappe.throw(_("Không có quyền thực hiện thao tác này"), frappe.PermissionError)


# ─── Depreciation Schedule (Phase 2) ─────────────────────────────────────────

@frappe.whitelist()
def get_depreciation_schedule(asset_name: str):
    """GET — Trả về schedule rows của 1 asset + tổng hợp."""
    if not frappe.db.exists("AC Asset", asset_name):
        return _err(_("Asset not found"), 404)
    rows = frappe.get_all(
        "AC Asset Depreciation Schedule",
        filters={"parent": asset_name, "parenttype": "AC Asset"},
        fields=["name", "period_number", "scheduled_date", "depreciation_amount",
                "accumulated_amount", "remaining_value", "status",
                "executed_on", "journal_entry"],
        order_by="period_number asc",
        limit_page_length=500,
    )
    summary = {
        "total_periods": len(rows),
        "executed_periods": sum(1 for r in rows if r.get("status") == "Executed"),
        "pending_periods":  sum(1 for r in rows if r.get("status") == "Pending"),
        "total_depreciated": sum(float(r.get("depreciation_amount") or 0)
                                  for r in rows if r.get("status") == "Executed"),
    }
    asset = frappe.db.get_value(
        "AC Asset", asset_name,
        ["gross_purchase_amount", "residual_value", "accumulated_depreciation",
         "current_book_value", "depreciation_method", "total_depreciation_months",
         "depreciation_frequency", "depreciation_start_date", "in_service_date"],
        as_dict=True,
    ) or {}
    return _ok({"asset": asset_name, "asset_info": asset, "rows": rows, "summary": summary})


@frappe.whitelist(methods=["POST"])
def regenerate_depreciation_schedule(asset_name: str, force: int = 1):
    """POST — Sinh lại schedule (xóa cũ nếu force=1).

    RC-01 fix: FE button "Sinh lịch khấu hao" used to appear to "hang" because:
      1. asset.save() inside generate_schedule() raised an unhandled exception
         (typically `LinkValidationError` from stale `device_model` / `location`),
         or
      2. Required fields (method / total_months / gross / start_date) were missing
         and the service returned `{skipped: true, reason: "..."}` but the FE
         button label never updated because the toast was eaten silently.

    Hardening:
      - Pre-validate the 4 required inputs and return a 422 with a Vietnamese
        message naming exactly which field is missing (so user can fix in form).
      - Wrap save() exceptions in 500 with the original message surfaced.
      - Always return within seconds; never hold the request.
    """
    from assetcore.services import depreciation as depr_svc

    if not frappe.db.exists(_DT_ASSET, asset_name):
        return _err(_(_ERR_ASSET_NOT_FOUND), 404)

    # ── RC-04 (Round-2) per-asset self-heal (BR-00-22) ────────────────────────
    # Asset CŨ (tạo TRƯỚC khi before_insert wire SoT inherit) có gross>0 +
    # asset_category CÓ luật nhưng total_depreciation_months=0 ⇒ trước đây pre-check
    # 4-field fail ngay ⇒ 422 "Thiếu: Số tháng" oan dù Category đã có luật.
    # Fix: nạp doc, gọi SoT DUY NHẤT inherit_depreciation_rules_from_category(asset)
    # TRƯỚC pre-check — KHÔNG inline copy months/residual ở đây (grep-guard:
    # 0 occurrence trong api/imm00.py ngoài lời gọi SoT). did_inherit=True ⇒ save
    # + audit. Pre-check chạy LẠI SAU (đọc state SAU self-heal) nên 422 chỉ còn khi
    # Category cũng thiếu / không có asset_category (KHÔNG che lỗi master-data).
    try:
        asset_doc = frappe.get_doc(_DT_ASSET, asset_name)
        did_inherit = depr_svc.inherit_depreciation_rules_from_category(asset_doc)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(),
                         f"RC-04 self-heal load/inherit failed: {asset_name}")
        return _err(_("Lỗi hệ thống khi kế thừa luật khấu hao: {0}").format(str(e)), 500)
    if did_inherit:
        try:
            asset_doc.flags.ignore_links = True
            asset_doc.flags.ignore_mandatory = True
            asset_doc.save(ignore_permissions=True)
        except frappe.LinkValidationError as e:
            return _err(_("Liên kết không hợp lệ khi lưu tài sản: {0}").format(str(e)), 422)
        except Exception as e:
            frappe.log_error(frappe.get_traceback(),
                             f"RC-04 self-heal save failed: {asset_name}")
            return _err(_("Lỗi hệ thống khi lưu luật khấu hao: {0}").format(str(e)), 500)
        # Audit best-effort — KHÔNG để lỗi audit chặn sinh lịch. No-op → KHÔNG event.
        _log_regenerate_selfheal_audit(asset_name)

    # Pre-validate inputs — bail early with a clear message instead of returning
    # `{skipped: true}` (which the FE may swallow as a non-error state).
    # CHẠY LẠI SAU inherit: đọc giá trị MỚI (db.get_value sau save) — KHÔNG đọc
    # state cũ trước self-heal (đó là gốc 422 oan ở round-1).
    a = frappe.db.get_value(
        _DT_ASSET, asset_name,
        ["depreciation_method", "total_depreciation_months",
         "gross_purchase_amount",
         "depreciation_start_date", "in_service_date", "commissioning_date"],
        as_dict=True,
    ) or {}
    missing: list[str] = []
    if not (a.get("depreciation_method") or "").strip():
        missing.append("Phương pháp khấu hao (depreciation_method)")
    if int(a.get("total_depreciation_months") or 0) <= 0:
        missing.append("Số tháng khấu hao (total_depreciation_months)")
    if float(a.get("gross_purchase_amount") or 0) <= 0:
        missing.append("Nguyên giá (gross_purchase_amount)")
    if not (a.get("depreciation_start_date")
            or a.get("in_service_date")
            or a.get("commissioning_date")):
        missing.append("Ngày bắt đầu khấu hao (depreciation_start_date / in_service_date / commissioning_date)")
    if missing:
        return _err(
            _("Không đủ thông tin để sinh lịch khấu hao. Thiếu: {0}.").format(
                "; ".join(missing),
            ),
            422,
        )

    try:
        result = depr_svc.generate_schedule(asset_name, force=bool(int(force)))
    except frappe.LinkValidationError as e:
        return _err(_("Liên kết không hợp lệ khi lưu tài sản: {0}").format(str(e)), 422)
    except frappe.ValidationError as e:
        return _err(str(e), 422)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"RC-01 regenerate_depreciation_schedule failed: {asset_name}")
        return _err(_("Lỗi hệ thống khi sinh lịch khấu hao: {0}").format(str(e)), 500)

    # If service skipped silently (race condition: another worker generated rows
    # between our pre-check and the save), surface that to the user too.
    if result.get("skipped"):
        return _err(
            _("Không sinh được lịch khấu hao: {0}").format(result.get("reason") or "Không rõ lý do"),
            422,
        )
    return _ok(result)


def _log_regenerate_selfheal_audit(asset_name: str) -> None:
    """1 Asset Lifecycle Event 'depreciation_rules_inherited' + 1 IMM Audit Trail
    'System' cho self-heal per-asset (BR-00-22 / RC-04).

    Best-effort (try/except) — KHÔNG để lỗi audit chặn sinh lịch. Chỉ gọi khi
    did_inherit=True (caller guard) ⇒ no-op KHÔNG sinh event rác.
    """
    try:
        from assetcore.services.imm00 import create_lifecycle_event, log_audit_event
        actor = frappe.session.user or "Administrator"
        # event_type 'depreciation_rules_inherited' = Select option HỢP LỆ
        # (asset_lifecycle_event.json, đã thêm round-1) → KHÔNG cần migrate.
        create_lifecycle_event(
            asset=asset_name, event_type="depreciation_rules_inherited",
            actor=actor, from_status="", to_status="",
            root_doctype=_DT_ASSET, root_record=asset_name,
            notes="Self-heal: kế thừa luật khấu hao từ Category khi sinh lịch (RC-04).",
        )
        # IMM Audit Trail event_type='System' = enum governance hiện hữu.
        log_audit_event(
            asset=asset_name, event_type="System", actor=actor,
            ref_doctype=_DT_ASSET, ref_name=asset_name,
            change_summary=(
                f"Self-heal kế thừa luật khấu hao từ Category cho {asset_name} "
                f"khi 'Sinh lịch khấu hao'."
            ),
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "regenerate self-heal audit failed")


@frappe.whitelist()
def preview_depreciation_schedule(gross: float, residual: float, method: str,
                                    total_months: int, frequency: str, start_date: str):
    """GET — Preview schedule không lưu DB (dùng cho form before commit)."""
    from assetcore.services import depreciation as depr_svc
    rows = depr_svc.preview_schedule(
        float(gross or 0), float(residual or 0), method,
        int(total_months or 0), frequency or "Monthly", start_date,
    )
    return _ok(rows)


@frappe.whitelist(methods=["POST"])
def run_due_depreciation_now(as_of: str = ""):
    """POST — Thủ công chạy cron (dành cho admin/testing)."""
    _assert_system_admin()
    from assetcore.services import depreciation as depr_svc
    return _ok(depr_svc.run_due_depreciation(as_of or None))


@frappe.whitelist(methods=["POST"])
def bulk_regenerate_schedule_by_category(category_name: str):
    """POST — Áp dụng luật khấu hao của Category cho TẤT CẢ assets thuộc danh mục.

    Route 100% qua SoT inherit_depreciation_rules_from_category (no-clobber field
    user nhập), sinh schedule cho asset chưa có. Asset đã có kỳ Executed → giữ
    nguyên lịch sử. Payload: {category, total_assets, inherited, regenerated,
    skipped_has_history, skipped_no_rule, errors}.
    """
    _assert_system_admin()
    from assetcore.services import depreciation as depr_svc
    return _ok(depr_svc.bulk_regenerate_by_category(category_name))


# ─── Depreciation: List + Stats (Asset Finance Hub) ───────────────────────────

_DEPR_LIST_FIELDS = [
    "name", "asset_name", "asset_category",
    "department", "location",
    "purchase_date", "in_service_date", "depreciation_start_date",
    "gross_purchase_amount", "residual_value",
    "depreciation_method", "total_depreciation_months", "depreciation_frequency",
    "accumulated_depreciation", "current_book_value",
    "lifecycle_status",
]


def _depr_row_progress(asset_name: str) -> tuple[int, int]:
    """Return (executed_periods, total_periods) for the asset schedule."""
    rows = frappe.db.sql(
        """SELECT status FROM `tabAC Asset Depreciation Schedule`
           WHERE parent = %s AND parenttype = 'AC Asset'""",
        (asset_name,),
    )
    total = len(rows)
    executed = sum(1 for (s,) in rows if s == "Executed")
    return executed, total


def _depr_enrich_row(a: dict) -> dict:
    from assetcore.services.depreciation import effective_book_value
    gross = float(a.get("gross_purchase_amount") or 0)
    accumulated = float(a.get("accumulated_depreciation") or 0)
    # BR-05-13: SoT đọc book — None→gross, 0.0→0.0 (KHÔNG inline `or gross`).
    book_value = effective_book_value(a)
    method = (a.get("depreciation_method") or "").strip()
    months = int(a.get("total_depreciation_months") or 0)
    configured = bool(method and method != "None" and gross > 0 and months > 0)

    executed, total = _depr_row_progress(a["name"])
    a["configured"]        = configured
    a["pct_depreciated"]   = round(accumulated / gross * 100, 1) if gross > 0 else 0.0
    a["executed_periods"]  = executed
    a["total_periods"]     = total
    a["current_book_value"] = book_value
    return a


_DEPR_FILTER_FULLY_DEPRECIATED = "fully_depreciated"


@frappe.whitelist()
def list_assets_depreciation(page: int = 1, page_size: int = 50,
                              method_filter: str = "",
                              status_filter: str = "",
                              category_filter: str = "",
                              depreciation_filter: str = ""):
    """GET — Danh sách asset kèm thông tin khấu hao (sourced từ schedule rows).

    ``depreciation_filter`` (vd 'fully_depreciated'): khi set, danh sách CHỈ chứa
    asset thỏa SoT ``is_fully_depreciated`` (depreciation.py). Predicate này cần
    current_book_value/residual/configured ⇒ áp SAU enrich, AND với các filter
    DB sẵn có (method/status/category) — KHÔNG clobber. Pagination total phản ánh
    TẬP ĐÃ LỌC (== len filtered), KHÔNG phải frappe.db.count thô bỏ qua predicate.

    INVARIANT (data-live): de-dup len(items mọi trang) == get_depreciation_stats().fully_depreciated.
    """
    filters: dict = {"docstatus": ("!=", 2)}
    if method_filter:
        filters["depreciation_method"] = method_filter
    if status_filter:
        filters["lifecycle_status"] = status_filter
    if category_filter:
        filters["asset_category"] = category_filter
    # Data-hygiene SSoT: loại asset rác test/security-audit khỏi count + list
    # (cùng predicate cả fast-path db.count lẫn get_all ⇒ INVARIANT count==list).
    filters.update(reserved_prefix_filter())

    page    = int(page)
    pg_size = int(page_size)
    depreciation_filter = (depreciation_filter or "").strip()

    # ── Fast path: KHÔNG có depreciation_filter → paginate ở DB như cũ ──────────
    if depreciation_filter != _DEPR_FILTER_FULLY_DEPRECIATED:
        total = frappe.db.count(_DT_ASSET, filters)
        assets = frappe.get_all(
            _DT_ASSET, filters=filters,
            fields=_DEPR_LIST_FIELDS,
            limit_start=(page - 1) * pg_size,
            limit_page_length=pg_size,
            order_by="asset_name asc",
        )
        for a in assets:
            _depr_enrich_row(a)
        return _ok({
            "items": assets,
            "pagination": {"page": page, "page_size": pg_size, "total": total},
        })

    # ── SoT path: lọc 'fully_depreciated' SAU enrich, paginate trong Python ─────
    # Predicate phụ thuộc current_book_value (enrich) ⇒ phải fetch full candidate
    # set (đã AND DB-filter), enrich, lọc SoT, rồi mới cắt trang → total == len(filtered).
    from assetcore.services.depreciation import (
        is_fully_depreciated as _depr_is_fully_depreciated,
    )

    candidates = frappe.get_all(
        _DT_ASSET, filters=filters,
        fields=_DEPR_LIST_FIELDS,
        order_by="asset_name asc",
    )
    matched = []
    for a in candidates:
        _depr_enrich_row(a)
        if _depr_is_fully_depreciated(a):
            matched.append(a)

    total = len(matched)
    start = (page - 1) * pg_size
    items = matched[start:start + pg_size]

    return _ok({
        "items": items,
        "pagination": {"page": page, "page_size": pg_size, "total": total},
    })


@frappe.whitelist()
def get_depreciation_stats():
    """GET — Tổng hợp tài chính khấu hao toàn danh mục.

    Lưu ý: total_accumulated lấy từ `accumulated_depreciation` (đã được cron
    cập nhật từ các kỳ Executed) — không tính trên-the-fly nữa.
    """
    from assetcore.services.depreciation import (
        is_fully_depreciated as _depr_is_fully_depreciated,
        effective_book_value as _depr_effective_book_value,
    )

    BATCH = 500
    totals = {
        "total_gross": 0.0, "total_accumulated": 0.0, "total_book": 0.0,
        "configured": 0, "unconfigured": 0, "fully_depreciated": 0,
        "by_method": {}, "by_category": {},
    }
    count = 0
    offset = 0
    # Data-hygiene SSoT: KPI total_assets KHÔNG đếm asset rác test/security-audit
    # — cùng predicate với list_assets_depreciation ⇒ parity KPI↔list (count==list).
    _depr_filters = {"docstatus": ("!=", 2), **reserved_prefix_filter()}
    while True:
        batch = frappe.get_all(
            _DT_ASSET,
            filters=_depr_filters,
            fields=_DEPR_LIST_FIELDS,
            limit_start=offset, limit_page_length=BATCH,
        )
        if not batch:
            break
        count += len(batch)
        for a in batch:
            gross    = float(a.get("gross_purchase_amount") or 0)
            residual = float(a.get("residual_value") or 0)
            accum    = float(a.get("accumulated_depreciation") or 0)
            # BR-05-13: SoT đọc book — None→gross, 0.0→0.0 (KHÔNG inline `or gross`).
            book     = _depr_effective_book_value(a)
            method   = (a.get("depreciation_method") or "").strip()
            months   = int(a.get("total_depreciation_months") or 0)
            configured = bool(method and method != "None" and gross > 0 and months > 0)

            totals["total_gross"] += gross
            totals["total_accumulated"] += accum
            totals["total_book"] += book

            if configured:
                totals["configured"] += 1
                # SoT DUY NHẤT — KHÔNG inline `book <= residual + 1` ở đây nữa.
                # is_fully_depreciated tự kiểm `configured` (đã True ở nhánh này)
                # + `book <= residual + tolerance`. Cùng tập, cùng số (backward-compat).
                if _depr_is_fully_depreciated({
                    "depreciation_method": method,
                    "gross_purchase_amount": gross,
                    "total_depreciation_months": months,
                    "residual_value": residual,
                    "current_book_value": book,
                    # accumulated PHẢI truyền: effective_book_value (SoT) phân biệt
                    # asset mới (book=0,accum=0→gross) vs đã KH hết (book=0,accum>0→0).
                    "accumulated_depreciation": accum,
                }):
                    totals["fully_depreciated"] += 1
                m = method
            else:
                totals["unconfigured"] += 1
                m = "Chưa cấu hình"

            totals["by_method"][m] = totals["by_method"].get(m, 0) + 1
            cat = a.get("asset_category") or "Chưa phân loại"
            totals["by_category"][cat] = totals["by_category"].get(cat, 0.0) + book

        if len(batch) < BATCH:
            break
        offset += BATCH

    tg = totals["total_gross"]
    ta = totals["total_accumulated"]

    # Enrich category ID -> human-readable category_name
    cat_ids = [k for k in totals["by_category"].keys() if k and k != "Chưa phân loại"]
    cat_name_map: dict = {}
    if cat_ids:
        rows = frappe.get_all(
            _DT_ASSET_CATEGORY,
            filters={"name": ("in", cat_ids)},
            fields=["name", "category_name"],
        )
        cat_name_map = {r["name"]: (r.get("category_name") or r["name"]) for r in rows}

    return _ok({
        "total_assets":       count,
        "configured_count":   totals["configured"],
        "unconfigured_count": totals["unconfigured"],
        "fully_depreciated":  totals["fully_depreciated"],
        "total_gross":        round(tg, 0),
        "total_accumulated":  round(ta, 0),
        "total_book_value":   round(totals["total_book"], 0),
        "overall_pct":        round(ta / tg * 100, 1) if tg > 0 else 0.0,
        "by_method":          [{"method": k, "count": v} for k, v in totals["by_method"].items()],
        "by_category":        sorted(
            [{"category": cat_name_map.get(k, k), "book_value": v} for k, v in totals["by_category"].items()],
            key=lambda x: -x["book_value"],
        )[:8],
    })


# Bucket key cho asset chưa gán Danh mục — hiển thị nhãn VI, category_id = "".
_DEPR_UNCATEGORIZED = "Chưa phân loại"


@frappe.whitelist()
def get_depreciation_by_category():
    """GET — Tổng hợp khấu hao GOM THEO DANH MỤC (quản lý tập trung theo danh mục).

    Mỗi Danh mục tài sản trả đủ chỉ số quản trị:
      asset_count, configured_count, fully_depreciated, total_gross,
      total_accumulated, total_book_value, pct_depreciated.
    Khác get_depreciation_stats().by_category (chỉ book_value top-8) — endpoint này
    là nguồn cho màn quản lý khấu hao theo danh mục (drill + áp dụng luật).

    PARITY (INVARIANT SoT — KHÔNG drift với get_depreciation_stats): dùng CHUNG
      • filter: ``docstatus != 2`` + ``reserved_prefix_filter()`` (loại asset rác test)
      • predicate: ``effective_book_value`` / ``is_fully_depreciated`` / ``configured``
    ⇒ Σ per-category == tổng toàn cục:
        Σ cat.asset_count      == totals.total_assets == get_depreciation_stats().total_assets
        Σ cat.fully_depreciated                        == get_depreciation_stats().fully_depreciated
        totals.total_gross     == get_depreciation_stats().total_gross  (cùng raw sum)

    Category id → category_name enrich (mirror get_depreciation_stats). Sắp theo
    total_gross giảm dần (danh mục 'nặng vốn' lên đầu).
    """
    from assetcore.services.depreciation import (
        is_fully_depreciated as _depr_is_fully_depreciated,
        effective_book_value as _depr_effective_book_value,
    )

    BATCH = 500
    # per-category accumulator, key = category docname hoặc _DEPR_UNCATEGORIZED
    acc: dict[str, dict] = {}
    grand = {"total_assets": 0, "total_gross": 0.0,
             "total_accumulated": 0.0, "total_book": 0.0}

    # SoT chung với get_depreciation_stats (parity KPI ↔ by-category).
    _depr_filters = {"docstatus": ("!=", 2), **reserved_prefix_filter()}
    offset = 0
    while True:
        batch = frappe.get_all(
            _DT_ASSET, filters=_depr_filters, fields=_DEPR_LIST_FIELDS,
            limit_start=offset, limit_page_length=BATCH,
        )
        if not batch:
            break
        for a in batch:
            gross    = float(a.get("gross_purchase_amount") or 0)
            residual = float(a.get("residual_value") or 0)
            accum    = float(a.get("accumulated_depreciation") or 0)
            # BR-05-13: SoT đọc book — None→gross, 0.0(mới)→gross (KHÔNG inline `or gross`).
            book     = _depr_effective_book_value(a)
            method   = (a.get("depreciation_method") or "").strip()
            months   = int(a.get("total_depreciation_months") or 0)
            configured = bool(method and method != "None" and gross > 0 and months > 0)

            cat_id = a.get("asset_category") or _DEPR_UNCATEGORIZED
            g = acc.get(cat_id)
            if g is None:
                g = {"asset_count": 0, "configured_count": 0, "fully_depreciated": 0,
                     "total_gross": 0.0, "total_accumulated": 0.0, "total_book": 0.0}
                acc[cat_id] = g

            g["asset_count"]       += 1
            g["total_gross"]       += gross
            g["total_accumulated"] += accum
            g["total_book"]        += book
            if configured:
                g["configured_count"] += 1
                # SoT DUY NHẤT — KHÔNG inline `book <= residual + 1` (cùng số với KPI).
                if _depr_is_fully_depreciated({
                    "depreciation_method": method,
                    "gross_purchase_amount": gross,
                    "total_depreciation_months": months,
                    "residual_value": residual,
                    "current_book_value": book,
                    "accumulated_depreciation": accum,
                }):
                    g["fully_depreciated"] += 1

            grand["total_assets"]       += 1
            grand["total_gross"]        += gross
            grand["total_accumulated"]  += accum
            grand["total_book"]         += book

        if len(batch) < BATCH:
            break
        offset += BATCH

    # Enrich category id -> human-readable category_name (mirror get_depreciation_stats).
    cat_ids = [k for k in acc.keys() if k and k != _DEPR_UNCATEGORIZED]
    cat_name_map: dict = {}
    if cat_ids:
        rows = frappe.get_all(
            _DT_ASSET_CATEGORY, filters={"name": ("in", cat_ids)},
            fields=["name", "category_name"],
        )
        cat_name_map = {r["name"]: (r.get("category_name") or r["name"]) for r in rows}

    categories = []
    for cat_id, g in acc.items():
        tg = g["total_gross"]
        ta = g["total_accumulated"]
        uncategorized = cat_id == _DEPR_UNCATEGORIZED
        categories.append({
            "category_id":       "" if uncategorized else cat_id,
            "category":          _DEPR_UNCATEGORIZED if uncategorized
                                 else cat_name_map.get(cat_id, cat_id),
            "asset_count":       g["asset_count"],
            "configured_count":  g["configured_count"],
            "fully_depreciated": g["fully_depreciated"],
            "total_gross":       round(tg, 0),
            "total_accumulated": round(ta, 0),
            "total_book_value":  round(g["total_book"], 0),
            "pct_depreciated":   round(ta / tg * 100, 1) if tg > 0 else 0.0,
        })
    categories.sort(key=lambda x: -x["total_gross"])

    tg = grand["total_gross"]
    ta = grand["total_accumulated"]
    return _ok({
        "categories": categories,
        "totals": {
            "total_assets":       grand["total_assets"],
            "total_gross":        round(tg, 0),
            "total_accumulated":  round(ta, 0),
            "total_book_value":   round(grand["total_book"], 0),
            "overall_pct":        round(ta / tg * 100, 1) if tg > 0 else 0.0,
        },
    })


@frappe.whitelist(methods=["POST"])
def compute_all_depreciation():
    """POST — Backfill luật khấu hao từ Category rồi sinh schedule + execute due
    rows cho TẤT CẢ assets có thể khấu hao.

    ROOT-CAUSE fix (thay 'skip' cũ bằng 'backfill-rồi-sinh'):
      Asset có gross>0 + Category có luật (total_depreciation_months>0) nhưng
      asset đang thiếu method/months → trước đây bị bỏ qua (skipped). Giờ:
        1. Backfill luật từ Category qua SoT DUY NHẤT
           inherit_depreciation_rules_from_category (services/depreciation),
           save(ignore_permissions=True), đếm vào `inherited`.
        2. Asset có >=1 kỳ Executed → KHÔNG backfill/regenerate (preserve
           history) → đếm `skipped_has_history`.
        3. Asset không có cả luật ở Category (months<=0 hoặc không category) và
           bản thân chưa cấu hình → `skipped_no_rule` (KHÔNG che lỗi cấu hình).
      Sau đó sinh schedule cho asset chưa có (force=False) + run_due_depreciation.

    Idempotent: chạy lần 2 trên cùng dataset → inherited=0 (không còn gì thiếu),
    không tạo schedule trùng (generate_schedule skip khi đã có rows), accumulated
    của asset đã Executed bất biến.

    Hiệu năng (N+1 fix): 2 phép kiểm tra count trước đây (executed-history +
    existing-schedule) chạy 2×N frappe.db.count per-asset. Giờ batch-prefetch
    bằng ĐÚNG 2 query GROUP BY parent chạy MỘT LẦN trước vòng lặp:
      • executed_parents  — parent có >=1 kỳ status='Executed' (preserve-history).
      • scheduled_parents — parent đã có >=1 schedule row bất kỳ.
    Trong loop chỉ còn set lookup O(1) → tổng số query KHÔNG còn phụ thuộc tuyến
    tính vào N cho 2 phép kiểm tra này.

    Return: {inherited, generated, executed_rows, updated_assets,
             skipped_has_history, skipped_no_rule}
    """
    _assert_system_admin()
    from assetcore.services import depreciation as depr_svc

    # Đọc sẵn asset_category + field khấu hao hiện có để tránh get_doc thừa cho
    # asset KHÔNG cần backfill (chỉ get_doc khi thực sự inherit).
    assets = frappe.get_all(
        _DT_ASSET,
        filters={"docstatus": ("!=", 2)},
        fields=["name", "asset_category", "depreciation_method",
                "total_depreciation_months", "gross_purchase_amount"],
        limit_page_length=10000,
    )

    inherited = 0
    generated = 0
    skipped_has_history = 0
    skipped_no_rule = 0
    inherited_assets: list[str] = []

    # ── N+1 fix: batch-prefetch 2 tập (executed-parents + schedule-parents) bằng
    # ĐÚNG 2 query GROUP BY parent chạy MỘT LẦN trước vòng lặp, thay cho 2×N
    # frappe.db.count per-asset. Set lookup O(1) trong loop → tổng số query
    # KHÔNG còn phụ thuộc tuyến tính vào N cho 2 phép kiểm tra count này.
    #   • executed_parents  → parent có >=1 kỳ status='Executed' (preserve-history).
    #   • scheduled_parents → parent đã có >=1 schedule row bất kỳ status
    #     (quyết định có generate_schedule hay không). KHÔNG có row nào được tạo
    #     trước generate_schedule() nên set chụp-trước-loop là chính xác.
    executed_parents = {
        r["parent"] for r in frappe.get_all(
            "AC Asset Depreciation Schedule",
            filters={"parenttype": _DT_ASSET, "status": "Executed"},
            fields=["parent"],
            group_by="parent",
        )
    }
    scheduled_parents = {
        r["parent"] for r in frappe.get_all(
            "AC Asset Depreciation Schedule",
            filters={"parenttype": _DT_ASSET},
            fields=["parent"],
            group_by="parent",
        )
    }

    for a in assets:
        name = a["name"]
        method = (a.get("depreciation_method") or "").strip()
        months = int(a.get("total_depreciation_months") or 0)
        gross = float(a.get("gross_purchase_amount") or 0)
        configured = bool(method and method != "None" and months > 0 and gross > 0)

        # ── Asset đã có lịch sử Executed → tuyệt đối KHÔNG đụng (preserve) ──────
        if name in executed_parents:
            skipped_has_history += 1
            continue

        # ── Asset thiếu luật (method rỗng / months<=0) → thử backfill từ Category ─
        if not configured and gross > 0:
            asset_doc = frappe.get_doc(_DT_ASSET, name)
            did_inherit = depr_svc.inherit_depreciation_rules_from_category(asset_doc)
            if did_inherit:
                asset_doc.flags.ignore_links = True
                asset_doc.flags.ignore_mandatory = True
                asset_doc.save(ignore_permissions=True)
                inherited += 1
                inherited_assets.append(name)
                # refresh post-backfill state để quyết định generate
                method = (asset_doc.depreciation_method or "").strip()
                months = int(asset_doc.total_depreciation_months or 0)
                configured = bool(method and method != "None" and months > 0 and gross > 0)

        # Vẫn chưa cấu hình được (cả Category cũng thiếu luật, hoặc gross<=0) →
        # không có gì để sinh → skipped_no_rule (KHÔNG che lỗi cấu hình thật).
        if not configured:
            skipped_no_rule += 1
            continue

        if name not in scheduled_parents:
            try:
                depr_svc.generate_schedule(name, force=False)
                generated += 1
            except Exception:
                # Sinh thất bại (input bất thường) → coi như không có luật khả dụng.
                skipped_no_rule += 1

    run_res = depr_svc.run_due_depreciation(None)

    # ── Audit trail cho hành động backfill global (CLAUDE.md §5) ───────────────
    if inherited:
        _log_compute_all_backfill_audit(inherited, inherited_assets)

    return _ok({
        "inherited":           inherited,
        "generated":           generated,
        "executed_rows":       run_res.get("executed_rows", 0),
        "updated_assets":      run_res.get("updated_assets", 0),
        "skipped_has_history": skipped_has_history,
        "skipped_no_rule":     skipped_no_rule,
    })


def _log_compute_all_backfill_audit(inherited: int, assets: list[str]) -> None:
    """Ghi 1 lifecycle/audit event TỔNG cho lần backfill khấu hao global.

    Best-effort — KHÔNG để lỗi audit chặn payload trả về cho user.
    """
    try:
        from assetcore.services.imm00 import create_lifecycle_event, log_audit_event
        actor = frappe.session.user or "Administrator"
        sample = ", ".join(assets[:10])
        more = f" (+{len(assets) - 10} khác)" if len(assets) > 10 else ""
        summary = (
            f"Backfill luật khấu hao từ AC Asset Category cho {inherited} tài sản "
            f"qua 'Áp dụng khấu hao cho TẤT CẢ tài sản'. Mẫu: {sample}{more}."
        )
        for asset_name in assets:
            # event_type 'depreciation_rules_inherited' = Select option HỢP LỆ
            # (asset_lifecycle_event.json) → per-asset lifecycle trace của backfill.
            # Per-asset guard: 1 asset lỗi KHÔNG được làm hỏng audit tổng bên dưới.
            try:
                create_lifecycle_event(
                    asset=asset_name, event_type="depreciation_rules_inherited",
                    actor=actor, from_status="", to_status="",
                    root_doctype=_DT_ASSET, root_record=asset_name,
                    notes="Kế thừa luật khấu hao từ Category (backfill global).",
                )
            except Exception:
                frappe.logger().warning(
                    f"compute_all backfill lifecycle event failed for {asset_name}")
        # event_type PHẢI khớp Select options của IMM Audit Trail → 'System'
        # (governance enum, KHÔNG mở rộng); change_summary mô tả rõ hành động.
        log_audit_event(
            asset=assets[0], event_type="System",
            actor=actor, ref_doctype=_DT_ASSET, ref_name=assets[0],
            change_summary=summary,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "compute_all_depreciation audit failed")
