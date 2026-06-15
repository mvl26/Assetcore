# Copyright (c) 2026, AssetCore Team
"""OpenAPI 3.1 generator — introspect `@frappe.whitelist` (D1-D13).

Bám ADR-IMM00-OPENAPI. Sinh `openapi.json` dict TỪ chính chữ ký hàm + decorator +
`utils/response.py` — KHÔNG hardcode danh mục endpoint, KHÔNG khai lại ErrorCode/HTTP map.

Phạm vi ĐÃ THỰC THI:
  - D1 introspect: 22 module-file `assetcore.api.*` → mọi fn whitelisted (485) →
    path + operationId + summary/description từ docstring.
  - D2 path/method/param/security: path `/api/method/assetcore.api.<mod>.<fn>`;
    method từ `frappe.allowed_http_methods_for_whitelisted_func` (registry runtime,
    KHÔNG ast/grep chuỗi — bất biến quote style); type-map type-hint → JSON type;
    security từ `frappe.guest_methods`.
  - D3 envelope: `SuccessEnvelope` + `ErrorEnvelope` sinh TỪ `utils/response.py`
    (ErrorCode → code.enum, _HTTP_FOR_CODE.values() → http_status.enum) — nguồn DUY NHẤT.
  - D4 body-bridge (DONE): tách param theo verb. POST CÓ signature-param → `requestBody`
    application/json object schema (`_request_body_for`: 1 property/param, type-map y
    như cũ qua `_json_type_for` SSoT, `required` = các param không-default) — KHÔNG key
    `parameters` (param vào body, không lọt query). GET → giữ `parameters` (in=query).
    POST không signature-param (form_dict: create_asset/create_supplier/…) → tra D5
    registry (xem dưới); nếu chưa map → KHÔNG sinh requestBody (rỗng hợp lệ, fail-safe).
  - D5 form_dict body-bridge (DONE): POST `create_*` đọc form_dict CÓ entry trong
    `openapi_overrides.FORM_DICT_DOCTYPE_MAP` → `_request_body_from_doctype` dựng object
    schema TỪ `frappe.get_meta(DocType)` (data/link/select/check/date/int/float fields, bỏ
    hidden + API-autoset naming_series/status/lifecycle_status). `required` = reqd-meta trừ
    autoset, override curated cho AC Asset (SSoT `_ASSET_REQD_LABELS_VI`). DocType lỗi →
    None defensive (KHÔNG vỡ spec). Registry là nơi DUY NHẤT chứa map form_dict→DocType.

  - D6 enrich (DONE): imm00/04/12 → summary/description non-empty + examples request/
    response/error VI DẪN XUẤT từ `openapi_overrides.OPERATION_META` + fallback humanize
    (`_enrich_operation`). KHÔNG hardcode chuỗi ở đây; ngoài 3 module → giữ default (fail-safe).

  - D7 serve (DONE): `spec()` whitelisted GET-only (session-gated) trả RAW OpenAPI 3.1
    dict (KHÔNG bọc SuccessEnvelope — integrator/Swagger UI cần spec thuần). Guest →
    `frappe.PermissionError` (KHÔNG allow_guest → KHÔNG lộ 485-endpoint cho khách, F6).
    Cache `_cached_spec()` qua `frappe.cache()` key versioned (`_spec_cache_key()` dẫn xuất
    `CAP_SET_VERSION` + `_app_version()`) — HIT thì KHÔNG re-introspect; tự bust khi thêm
    cap / bump app version (giống pattern `ac_caps::*`). Trang `www/api-docs.html` nhúng
    Swagger UI self-host (air-gapped) trỏ vào endpoint này.

  - D8 metadata (DONE): root-level `tags` (`_root_tags`) — gom tập tag DUY NHẤT dùng ở
    operation, map mỗi tag → mô tả VI qua `openapi_overrides.tag_description_for` (SSoT,
    KHÔNG khai lại map ở đây) → list[dict]{name,description} sort theo name, no orphan-tag.
    `x-assetcore-stats` (`_assetcore_stats`) — extension đếm ĐỘNG total/get/post từ paths,
    guest_count = số operation trong paths có `security == []` (DẪN XUẤT từ paths đã sinh,
    CÙNG nguồn get/post/enriched — D11; KHÔNG đọc `frappe.guest_methods` global vì registry
    phụ thuộc boot-context → drift 2/5/10), enriched_count từ `_ovr.enrich_meta_for` (op imm00/
    04/12), cap_set_version từ `rbac.CAP_SET_VERSION` (lazy-import), generated_app_version
    từ `_app_version()`. MỌI số DẪN XUẤT — KHÔNG hardcode magic number, KHÔNG chạm DB.

  - D10 JSON-string param annotate (DONE): `_json_string_params(fn)` KHÁM PHÁ tập param
    JSON-string qua AST (Call `parse_json`/`_parse_json`/`json.loads`/`frappe.parse_json` có
    arg[0]=Name(param) — TRỰC TIẾP hoặc qua FORWARD vào private delegate `_list_xxx`; fixpoint).
    Cache theo module-file (KHÔNG re-parse mỗi endpoint), defensive set() khi lỗi. Wire vào
    `_parameters_for` (GET) + `_request_body_for` (POST body property): param JSON-string →
    schema con thêm `format:json` + `x-decoded-default-type` (default literal '{}'→object,
    '[]'→array, else object) + override `x-decoded-schema` từ `_ovr.JSON_PARAM_OVERRIDES`
    (curated SSoT; entry `{'doctype': DT}` tái dùng D5 `_request_body_from_doctype`). type GIỮ
    'string' (backward-compatible Swagger UI). `x-assetcore-stats.json_param_count` =
    `_total_json_string_params()` (đếm động — KHÔNG hardcode 109 call-site). Thêm param parse_json
    mới → generator tự gắn format:json KHÔNG sửa registry (introspection có răng).

  - D11 guest-stat (DONE): `x-assetcore-stats.guest_count` = số OPERATION có `security==[]`
    đếm trên `paths` đã render (cùng nguồn get/post/enriched) — KHÔNG đọc `frappe.guest_methods`
    global volatile (drift theo worker-boot).

  - D12 error-surface (DONE): baseline typed `401`(authed)/`403` MERGE vào MỌI op qua
    `_baseline_error_responses` (curated D6 thắng baseline); guest KHÔNG 401.
    `x-assetcore-stats.error_responses_typed_count` đếm động op có ≥1 response 4xx/5xx.

  - D13 servers-block (DONE): root-level `servers[]` DẪN XUẤT `frappe.utils.get_url()` SSoT
    (`_servers()`) — BARE origin (KHÔNG '/api/method/', strip trailing '/'), chèn GIỮA `info`
    và `components` (thứ tự canonical info→servers→components→paths→tags→x-assetcore-stats).
    Fail-safe: get_url() raise/rỗng → fallback relative '/' (KHÔNG bao giờ exception vì servers).
    KHÔNG hardcode host — chỉ gọi get_url(). servers ≠ operation → x-assetcore-stats BẤT BIẾN.

  - D14 info-contact-license (DONE): `info.contact` + `info.license` DẪN XUẤT từ `hooks.py`
    app-metadata SSoT qua `frappe.get_hooks(hook, app_name='assetcore')` (APP-SCOPED single-
    element list — KHÔNG merged list nhiều-app gây index không ổn định). Helper `_app_meta_hook`
    (fail-safe → None), `_info_contact` (name=app_publisher + email tùy chọn khi app_email non-
    empty; app_email=='' → OMIT 'email', KHÔNG leak ''), `_info_license` ({name,identifier}=
    app_license SPDX, KHÔNG 'url' — 3.1 cấm cả identifier lẫn url). Chèn CÓ ĐIỀU KIỆN sau
    'description' (helper None → bỏ qua, KHÔNG sinh dict rỗng, generate_spec KHÔNG raise). info
    GIỮ title/version/description; thứ tự top-level + servers + x-assetcore-stats BẤT BIẾN
    (info ≠ operation ≠ path). KHÔNG hardcode 'MIT'/'miyano' literal — đọc qua hook.

  - D15 externalDocs (SUPERSEDED by D16): root + per-tag `externalDocs` lúc đầu DẪN XUẤT
    doc-base từ `frappe.utils.get_url()`. NHƯNG get_url()=API origin (site Frappe), CÒN docs
    markdown chỉ tồn tại trong repo (KHÔNG web-served) ⟹ url = link CHẾT 404 ở trình duyệt.
    D16 SỬA SSoT doc-base + graceful-omit (xem dưới). D15 helper/key-order GIỮ tên — đổi NGUỒN
    + thêm nhánh omit.

  - D16 externalDocs doc-base SSoT + graceful omit (DONE): doc-base KHÔNG còn `get_url()`
    (API origin → 404 vì docs repo-only). Doc-base MỚI = hook `app_docs_url` (app-scoped
    `frappe.get_hooks('app_docs_url', app_name='assetcore')`, CÙNG pattern D14 app_publisher/
    app_license) — trỏ nơi docs THỰC SỰ web-served (published docs site / Git browse base).
    Helper `_doc_base()` (đọc hook qua `_app_meta_hook('app_docs_url')`, rstrip '/', None/rỗng
    → ''), `_docs_base_or_none()` (None khi chưa cấu hình), `_doc_url(rel)` (ghép base+'/'+rel,
    normalize KHÔNG double-slash). 2 NHÁNH:
      · app_docs_url CẤU HÌNH non-empty → root externalDocs.url = <base>/docs/imm-00/README.md;
        mỗi tag IMM-XX → <base>/docs/imm-XX/README.md; cross-cut → <base>/docs/imm-00/README.md.
        Key-order `...→tags→externalDocs→x-assetcore-stats`; per-tag = subkey THÊM.
      · app_docs_url VẮNG/rỗng/None (mặc định hiện tại — hooks chưa khai) → ROOT externalDocs
        key VẮNG HẲN + MỌI tag KHÔNG subkey externalDocs (0/23). Lý do: link chết tệ hơn không
        link — Swagger UI render sạch KHÔNG externalDocs. KHÔNG fabricate URL relative/404.
        Key-order `...→tags→x-assetcore-stats` LIỀN (KHÔNG lỗ trống, KHÔNG key None).
    Fail-safe: hook lỗi → '' → omit (generate_spec() KHÔNG raise ở CẢ 2 nhánh). externalDocs
    = field root + tag-level → x-assetcore-stats BẤT BIẾN. servers[] (D13) VẪN dùng get_url()
    (ĐÚNG — đó là API base cho 'Try it out', KHÁC doc-base).

CHỈ introspection thuần — KHÔNG modify core, KHÔNG đụng `utils/response.py` (chỉ ĐỌC).
"""
from __future__ import annotations

import ast
import importlib
import inspect
import pkgutil
import types
import typing
from typing import Any

import frappe

import assetcore.api as _api_pkg
from assetcore.api import openapi_overrides as _ovr
from assetcore.utils.response import ErrorCode, _HTTP_FOR_CODE

# ── Hằng cấu hình spec (KHÔNG hardcode endpoint/enum — chỉ metadata tĩnh) ──────
_OPENAPI_VERSION = "3.1.0"
_API_TITLE = "AssetCore API"
_API_DESC = "Auto-generated từ @frappe.whitelist — KHÔNG sửa tay"
_PATH_PREFIX = "/api/method/"

# Severity enum của error envelope (response.py:121 — danh sách cố định, không phải
# code/HTTP nên khai ở đây là hợp lệ; KHÔNG trùng nguồn ErrorCode).
_SEVERITY_ENUM = ["error", "warning", "info", "success", "critical"]

# type-hint Python → JSON Schema type (bảng D2). Map cho CẢ real type object lẫn
# tên dạng chuỗi (PEP 563 — module có `from __future__ import annotations`).
_TYPE_MAP: dict[str, str] = {
    "str": "string",
    "int": "integer",
    "float": "number",
    "bool": "boolean",
    "dict": "object",
    "list": "array",
}
_DEFAULT_JSON_TYPE = "string"  # no-hint → string (D2).


def _app_version() -> str:
    """Phiên bản app cho info.version — đọc động `assetcore.__version__`, fallback '0.0.0'."""
    try:
        return str(getattr(importlib.import_module("assetcore"), "__version__", "0.0.0"))
    except Exception:  # pragma: no cover — defensive
        return "0.0.0"


# ── D14 info-contact-license (app-metadata SSoT từ hooks.py, app-scoped) ───────
_APP_NAME = "assetcore"  # app-scope cho get_hooks (KHÔNG merged list nhiều-app).


def _app_meta_hook(hook: str) -> str | None:
    """Đọc 1 giá trị app-metadata hook (app-scoped SSoT) — phần tử [0] strip() hoặc None.

    Bọc `frappe.get_hooks(hook, app_name='assetcore')` (SINGLE-element list — KHÔNG dùng
    `get_hooks(hook)` merged trả list nhiều-app: vd `app_publisher` merged gom publisher của
    MỌI app cài kèm ⟹ index không ổn định). Lấy phần tử đầu, `.strip()`; trả None nếu rỗng
    sau strip / list rỗng / None.

    Fail-safe: bất kỳ exception (ngữ cảnh không-app / test / get_hooks lỗi) → None (KHÔNG
    raise — giống pattern `_servers()` / `_app_version()`). Nhờ vậy `generate_spec()` KHÔNG
    bao giờ vỡ vì thiếu/hỏng app-metadata.

    Args:
        hook: tên hook trong hooks.py (vd 'app_publisher', 'app_license', 'app_email').

    Returns:
        str đã strip non-empty, hoặc None nếu vắng / rỗng / lỗi.
    """
    try:
        values = frappe.get_hooks(hook, app_name=_APP_NAME)
    except Exception:  # pragma: no cover — ngữ cảnh không-app / lỗi cấu hình.
        return None
    if not values:
        return None
    value = (values[0] or "").strip()
    return value or None


def _info_contact() -> dict | None:
    """`info.contact` (OpenAPI 3.1) DẪN XUẤT từ app-metadata hook — hoặc None.

    name = `_app_meta_hook('app_publisher')`; email = `_app_meta_hook('app_email')`; url chưa
    có hook chuẩn nên None. Build dict CHỈ chứa key non-None: luôn `{'name': ...}` + tùy chọn
    `'email'` khi app_email non-empty (FAIL-SAFE: app_email=='' ⟹ KHÔNG key 'email', KHÔNG leak
    `'email':''`). Trả None nếu name rỗng (KHÔNG sinh contact rỗng).

    Returns:
        dict `{'name': ...[, 'email': ...]}` hoặc None (app_publisher vắng).
    """
    name = _app_meta_hook("app_publisher")
    if not name:
        return None
    contact: dict = {"name": name}
    email = _app_meta_hook("app_email")
    if email:
        contact["email"] = email
    return contact


def _info_license() -> dict | None:
    """`info.license` (OpenAPI 3.1 SPDX) DẪN XUẤT từ app-metadata hook — hoặc None.

    spdx = `_app_meta_hook('app_license')` → trả `{'name': spdx, 'identifier': spdx}`.
    `identifier` là field SPDX MỚI của OpenAPI 3.1; identifier==name vì hooks chỉ có 1 field
    license. KHÔNG kèm 'url' khi thiếu (3.1 cấm có CẢ `identifier` lẫn `url` — chọn identifier).
    Trả None nếu spdx rỗng (KHÔNG sinh license rỗng).

    Returns:
        dict `{'name': spdx, 'identifier': spdx}` hoặc None (app_license vắng).
    """
    spdx = _app_meta_hook("app_license")
    if not spdx:
        return None
    return {"name": spdx, "identifier": spdx}


def _iter_api_modules() -> list[types.ModuleType]:
    """Import + yield mọi module `assetcore.api.*` (trừ `_`-prefix).

    Import side-effect đăng ký `@frappe.whitelist` vào `frappe.whitelisted` +
    `frappe.guest_methods` + `frappe.allowed_http_methods_for_whitelisted_func`.
    PHẢI import HẾT trước khi introspect để registry đầy đủ (485 endpoint).
    """
    mods: list[types.ModuleType] = []
    for info in pkgutil.iter_modules(_api_pkg.__path__):
        if info.name.startswith("_"):
            continue
        mods.append(importlib.import_module(f"assetcore.api.{info.name}"))
    return mods


def _whitelisted_name_set() -> set[tuple[str, str]]:
    """Tập (module, qualname) của MỌI hàm đã `@frappe.whitelist` đăng ký.

    Membership theo NAME (không identity) — robust với wrapper
    `validate_argument_types` + re-import (identity module-attr có thể khác entry
    trong `frappe.whitelisted`). Đồng bộ với `test_oas_signatures.py`.
    """
    return {
        (
            getattr(fn, "__module__", ""),
            getattr(fn, "__qualname__", getattr(fn, "__name__", "")),
        )
        for fn in frappe.whitelisted
    }


def _guest_name_set() -> set[tuple[str, str]]:
    """Tập (module, qualname) của hàm `allow_guest=True` (∈ `frappe.guest_methods`)."""
    return {
        (
            getattr(fn, "__module__", ""),
            getattr(fn, "__qualname__", getattr(fn, "__name__", "")),
        )
        for fn in frappe.guest_methods
    }


def _whitelisted_functions_in(
    module: types.ModuleType, name_set: set[tuple[str, str]]
) -> list[tuple[str, Any]]:
    """Hàm ĐỊNH NGHĨA trong `module` đã `@frappe.whitelist` đăng ký.

    Loại RE-EXPORT (import từ module khác, vd `submit_rca as svc_submit_rca` trong
    imm12.py — `__module__` = services.imm12 ≠ api.imm12) bằng `__module__` check →
    KHÔNG đếm trùng. Đồng bộ với `test_oas_signatures.py::_whitelisted_functions_in`.
    """
    out: list[tuple[str, Any]] = []
    for name, obj in vars(module).items():
        if name.startswith("_") or not callable(obj):
            continue
        if getattr(obj, "__module__", None) != module.__name__:
            continue
        qual = getattr(obj, "__qualname__", getattr(obj, "__name__", ""))
        if (module.__name__, qual) in name_set:
            out.append((name, obj))
    return out


def _module_short(module: types.ModuleType) -> str:
    """Tên ngắn module-file: 'assetcore.api.imm00' → 'imm00'."""
    return module.__name__.rsplit(".", 1)[-1]


def _http_method_for(fn: Any) -> str:
    """Verb HTTP dẫn xuất từ `frappe.allowed_http_methods_for_whitelisted_func`.

    KHÔNG ast/grep chuỗi, KHÔNG suy từ tên hàm (F11/ADR-D2). Quy tắc Frappe v15:
      - bare `@frappe.whitelist()`        → allowed = ['GET','POST','PUT','DELETE']
        (mặc định mọi verb)               → coi là **GET** (đọc dữ liệu).
      - `@frappe.whitelist(methods=["POST"])` → allowed = ['POST']
        (hạn chế POST-only)               → **POST** (mutating).

    Discriminator chốt: **POST khi GET KHÔNG nằm trong allowed-list** (hạn chế
    POST-only), ngược lại GET. Map này cho `get_asset`→get (default all-verb) và
    `create_asset`/`report_incident`→post (`['POST']`) — khớp TC-OAS-04.
    """
    allowed = frappe.allowed_http_methods_for_whitelisted_func.get(fn) or []
    if "GET" not in allowed and "POST" in allowed:
        return "post"
    return "get"


def _json_type_for(annotation: Any) -> str:
    """type-hint → JSON Schema type (bảng D2). Phủ real type + chuỗi PEP 563.

    - `inspect.Parameter.empty` (no-hint) → 'string'.
    - real type object (`int`, `str`, ...) → `__name__` lookup.
    - chuỗi (PEP 563, vd 'str'/'int') → lookup trực tiếp; chuỗi lạ/union → 'string'.
    """
    if annotation is inspect.Parameter.empty:
        return _DEFAULT_JSON_TYPE
    # real type object.
    if isinstance(annotation, type):
        return _TYPE_MAP.get(annotation.__name__, _DEFAULT_JSON_TYPE)
    # typing generic (vd typing.List) — lấy origin.
    origin = typing.get_origin(annotation)
    if origin is not None and isinstance(origin, type):
        return _TYPE_MAP.get(origin.__name__, _DEFAULT_JSON_TYPE)
    # chuỗi PEP 563 (vd 'str', 'int'). Chuỗi đơn → lookup; lạ → string.
    if isinstance(annotation, str):
        return _TYPE_MAP.get(annotation.strip(), _DEFAULT_JSON_TYPE)
    return _DEFAULT_JSON_TYPE


def _named_params(fn: Any) -> list[tuple[str, Any, bool]]:
    """Param đặt-tên của `fn`: list (name, annotation, required).

    - required = default là `inspect.Parameter.empty` (param KHÔNG có default).
    - Bỏ VAR_POSITIONAL/VAR_KEYWORD (*args/**kwargs — không phải param đặt tên).
    Dùng chung cho query-params (GET) và requestBody (POST, D4).
    """
    try:
        sig = inspect.signature(fn)
    except (ValueError, TypeError):  # pragma: no cover — defensive
        return []
    out: list[tuple[str, Any, bool]] = []
    for pname, p in sig.parameters.items():
        if p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue
        out.append((pname, p.annotation, p.default is inspect.Parameter.empty))
    return out


# ── D10 JSON-string param discovery (AST — bất biến quote-style) ──────────────
# Tên hàm "decode JSON" được coi là parse JSON-string param.
_JSON_PARSE_FUNCS: frozenset[str] = frozenset(
    {"parse_json", "_parse_json", "loads"}  # `loads` ← json.loads / frappe.parse_json bắt riêng
)
# Cache AST per module-file: {module_qualname: {fn_name: frozenset[param]}} — KHÔNG re-parse
# mỗi endpoint. None entry = file không parse được (defensive fail-safe).
_JSON_PARAM_CACHE: dict[str, dict[str, frozenset[str]] | None] = {}


def _call_is_json_parse(node: ast.Call) -> bool:
    """True nếu `node` gọi parse_json/_parse_json/json.loads/frappe.parse_json.

    Khớp CẢ dạng `parse_json(...)` (Name) lẫn `json.loads(...)` / `frappe.parse_json(...)`
    (Attribute) — bất biến alias (`parse_json as _parse_json`) vì bắt theo TÊN cuối.
    """
    func = node.func
    if isinstance(func, ast.Name):
        return func.id in _JSON_PARSE_FUNCS
    if isinstance(func, ast.Attribute):
        # json.loads / frappe.parse_json → khớp attr cuối.
        return func.attr in _JSON_PARSE_FUNCS or func.attr == "parse_json"
    return False


def _positional_param_names(fnode: ast.FunctionDef) -> list[str]:
    """Tên param theo THỨ TỰ positional (posonly + args) — để map forward theo vị trí."""
    return [a.arg for a in (list(fnode.args.posonlyargs) + list(fnode.args.args))]


def _scan_module_json_params(module: types.ModuleType) -> dict[str, frozenset[str]] | None:
    """Quét source-file `module` 1 lần → {fn_name: frozenset(param JSON-string)}.

    2 lớp (xử lý wrapper-delegate phổ biến: whitelisted `list_xxx` thin-wrap private
    `_list_xxx` thực sự parse):
      (1) DIRECT — mỗi `def`, tìm Call `parse_json`/`_parse_json`/`json.loads`/
          `frappe.parse_json` có `args[0]` là `ast.Name` trùng 1 param đặt-tên → JSON-string.
      (2) FORWARD — nếu `def F` GỌI 1 sibling `def G` (cùng module) truyền param `P` của F
          (qua positional Name(P) HOẶC keyword `k=Name(P)`) vào vị-trí/keyword tương ứng của
          G, và param đó của G là JSON-string ⟹ P của F cũng JSON-string. Lan truyền tới
          fixpoint (chuỗi wrapper nhiều tầng).

    Kết quả cache theo module (KHÔNG re-parse mỗi endpoint). Đếm theo (fn, param) — bất biến
    quote-style/alias. DEFENSIVE: source/parse lỗi → None (fail-safe, KHÔNG vỡ spec).
    """
    try:
        source = inspect.getsource(module)
        tree = ast.parse(source)
    except (OSError, TypeError, SyntaxError):  # pragma: no cover — defensive
        return None

    fnodes: dict[str, ast.FunctionDef] = {}
    param_names: dict[str, set[str]] = {}
    pos_params: dict[str, list[str]] = {}
    direct: dict[str, set[str]] = {}
    # forward edges: F-param → list[(G_name, G_param)] (P của F chảy vào G_param của G).
    forwards: dict[str, list[tuple[str, str]]] = {}

    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        fnodes[node.name] = node
        pnames = {a.arg for a in node.args.args} | {a.arg for a in node.args.kwonlyargs} | {
            a.arg for a in node.args.posonlyargs
        }
        param_names[node.name] = pnames
        pos_params[node.name] = _positional_param_names(node)
        direct[node.name] = set()

    # Pass 1 — direct parse + forward edges.
    for fname, node in fnodes.items():
        pnames = param_names[fname]
        edges: list[tuple[str, str]] = []
        for sub in ast.walk(node):
            if not isinstance(sub, ast.Call):
                continue
            # (1) direct parse: parse_json(Name(param)).
            if _call_is_json_parse(sub) and sub.args:
                a0 = sub.args[0]
                if isinstance(a0, ast.Name) and a0.id in pnames:
                    direct[fname].add(a0.id)
                continue
            # (2) forward: gọi sibling G(...) truyền Name(param) của F.
            callee = sub.func
            g_name = callee.id if isinstance(callee, ast.Name) else None
            if g_name is None or g_name not in fnodes:
                continue
            g_pos = pos_params[g_name]
            # positional args → map theo vị trí.
            for idx, a in enumerate(sub.args):
                if isinstance(a, ast.Name) and a.id in pnames and idx < len(g_pos):
                    edges.append((g_name, g_pos[idx]))
            # keyword args → map theo tên keyword (== tên param G).
            for kw in sub.keywords:
                if (
                    kw.arg
                    and isinstance(kw.value, ast.Name)
                    and kw.value.id in pnames
                    and kw.arg in param_names[g_name]
                ):
                    edges.append((g_name, kw.arg))
        forwards[fname] = edges

    # Pass 2 — fixpoint: lan truyền JSON-string từ direct + qua forward edges.
    result: dict[str, set[str]] = {f: set(d) for f, d in direct.items()}
    changed = True
    while changed:
        changed = False
        for fname, node in fnodes.items():
            pnames = param_names[fname]
            for sub in ast.walk(node):
                if not isinstance(sub, ast.Call):
                    continue
                callee = sub.func
                g_name = callee.id if isinstance(callee, ast.Name) else None
                if g_name is None or g_name not in fnodes:
                    continue
                g_pos = pos_params[g_name]
                g_json = result[g_name]
                # positional: P của F → g_pos[idx]; nếu g_pos[idx] ∈ g_json → P là JSON.
                for idx, a in enumerate(sub.args):
                    if (
                        isinstance(a, ast.Name)
                        and a.id in pnames
                        and idx < len(g_pos)
                        and g_pos[idx] in g_json
                        and a.id not in result[fname]
                    ):
                        result[fname].add(a.id)
                        changed = True
                # keyword: P của F → kw.arg; nếu kw.arg ∈ g_json → P là JSON.
                for kw in sub.keywords:
                    if (
                        kw.arg
                        and isinstance(kw.value, ast.Name)
                        and kw.value.id in pnames
                        and kw.arg in g_json
                        and kw.value.id not in result[fname]
                    ):
                        result[fname].add(kw.value.id)
                        changed = True

    return {f: frozenset(p) for f, p in result.items()}


def _json_string_params(fn: Any) -> set[str]:
    """Tập tên param JSON-string của `fn` (D10 — AST discovery, đếm động).

    Param JSON-string = param mà thân hàm `parse_json`/`_parse_json`/`json.loads`/
    `frappe.parse_json` áp lên (arg[0] là Name trùng tên param). Bám cơ chế AST ADR §D2
    (bất biến quote-style). Cache theo module-file.

    DEFENSIVE: module/source không parse được, hoặc hàm không tìm thấy trong AST → trả
    set() rỗng (fail-safe — KHÔNG vỡ spec).
    """
    mod_name = getattr(fn, "__module__", "")
    if not mod_name:
        return set()
    if mod_name not in _JSON_PARAM_CACHE:
        try:
            module = importlib.import_module(mod_name)
        except Exception:  # pragma: no cover — defensive
            _JSON_PARAM_CACHE[mod_name] = None
        else:
            _JSON_PARAM_CACHE[mod_name] = _scan_module_json_params(module)
    table = _JSON_PARAM_CACHE.get(mod_name)
    if not table:
        return set()
    fn_name = getattr(fn, "__name__", "")
    return set(table.get(fn_name, frozenset()))


def _decoded_default_type(fn: Any, param: str) -> str:
    """x-decoded-default-type dẫn xuất từ default literal của `param` (D10).

    Quy ước (ADR §D10 + parse_json default kwarg convention):
      - default `'{}'`  → 'object'
      - default `'[]'`  → 'array'
      - default `''` / no-default / khác → 'object' (parse_json falsy→{} ⟹ object;
        local helper imm15/imm16 cũng falsy→{}). 'string' chỉ khi literal khác cấu trúc.
    """
    try:
        sig = inspect.signature(fn)
    except (ValueError, TypeError):  # pragma: no cover — defensive
        return "object"
    p = sig.parameters.get(param)
    if p is None or p.default is inspect.Parameter.empty:
        return "object"
    default = p.default
    if default == "[]":
        return "array"
    if default == "{}":
        return "object"
    # '' (chuỗi rỗng) hoặc default khác → object (parse_json falsy→{}).
    return "object"


def _annotate_json_string(schema: dict, fn: Any, op_tail: str, param: str) -> None:
    """Gắn `format:json` + `x-decoded-default-type` (+ override `x-decoded-schema`) IN-PLACE.

    KHÔNG đổi `type` (giữ 'string' — backward-compatible Swagger UI). Override curated
    (`_ovr.json_param_override_for`) ĐÈ default-type bằng `x-decoded-schema` tường minh:
      - entry `{'doctype': DT}` → tái dùng D5 `_request_body_from_doctype` (lazy meta).
      - entry `{'x-decoded-schema': {...}}` → object-shape literal.
    """
    schema["format"] = "json"
    schema["x-decoded-default-type"] = _decoded_default_type(fn, param)
    override = _ovr.json_param_override_for(op_tail, param)
    if not override:
        return
    decoded = override.get("x-decoded-schema")
    if decoded is None and override.get("doctype"):
        body = _request_body_from_doctype(override["doctype"])
        if body is not None:
            decoded = body["content"]["application/json"]["schema"]
    if decoded is not None:
        schema["x-decoded-schema"] = decoded


def _parameters_for(fn: Any, op_tail: str) -> list[dict]:
    """query parameters[] từ `inspect.signature` (D2) — dùng cho verb=GET.

    - required = default là `inspect.Parameter.empty` (param KHÔNG có default).
    - schema.type = type-map của annotation.
    - in = 'query' (GET đọc dữ liệu qua query-string).
    - D10: param ∈ tập JSON-string (`_json_string_params`) → schema con thêm `format:json`
      + `x-decoded-default-type` (+ override x-decoded-schema). type GIỮ 'string'.
    POST có signature-param → KHÔNG dùng hàm này (body-bridge D4: `_request_body_for`).
    """
    json_params = _json_string_params(fn)
    params: list[dict] = []
    for pname, annotation, required in _named_params(fn):
        schema: dict = {"type": _json_type_for(annotation)}
        if pname in json_params:
            _annotate_json_string(schema, fn, op_tail, pname)
        params.append(
            {
                "name": pname,
                "in": "query",
                "required": required,
                "schema": schema,
            }
        )
    return params


def _workflow_actions_for(doctypes: list[str]) -> list[str]:
    """Helper THUẦN (D17): union sorted-distinct `transitions[].action` của workflow fixture
    cho tập `doctypes` — đọc fixture đĩa `assetcore/assetcore/workflow/*.json`, KHÔNG truy vấn DB.

    Lọc fixture theo `document_type ∈ doctypes`, gom action bỏ rỗng, union sorted distinct.
    Deterministic (chạy được cả ngoài site context như các introspect helper khác). Fail-safe
    per-file (file vắng / JSON lỗi / 0 transition) đã nằm trong `_ovr._actions_for_doctype`
    (per-doctype cached scanner — SSoT đọc đĩa). DẪN XUẤT, KHÔNG hardcode danh sách action.

    Args:
        doctypes: danh sách tên DocType workflow (vd ['IMM Needs Request', 'IMM Procurement Plan']).

    Returns:
        list[str] action sorted-distinct (VI y nguyên fixture), hoặc [] khi không doctype nào
        resolve được action (fixture vắng / 0 transition) — caller BỎ enum (plain string).
    """
    union: set[str] = set()
    for dt in doctypes or []:
        union.update(_ovr._actions_for_doctype(dt))
    return sorted(union)


def _request_body_for(fn: Any, op_tail: str) -> dict | None:
    """requestBody (application/json) từ `inspect.signature` (D4 body-bridge).

    Cho verb=POST CÓ signature-param: chuyển từng param thành 1 property của object
    schema (type-map y như query-param cũ) + mảng `required` chứa ĐÚNG các param
    KHÔNG-default. POST không signature-param (form_dict/no-arg: create_asset,
    create_supplier, …) → trả None (KHÔNG sinh requestBody round này — backlog D5
    override registry map DocType). GET KHÔNG gọi hàm này (giữ query parameters).

    D10: property của param JSON-string (`_json_string_params`) thêm `format:json` +
    `x-decoded-default-type` (+ override x-decoded-schema). type GIỮ 'string'.

    Returns:
        dict requestBody hợp lệ OpenAPI 3.1 (`required:true` + object schema với
        `properties` non-empty + `required` mảng các param không-default), hoặc
        None nếu signature trống.
    """
    named = _named_params(fn)
    if not named:
        return None
    json_params = _json_string_params(fn)
    # D17: enum VI-canonical cho body-param 'action' của 5 transition endpoint mapped
    # trong `_ovr.WORKFLOW_ACTION_OVERRIDES`. DẪN XUẤT ĐỘNG từ workflow fixture .json (SSoT;
    # KHÔNG hardcode action ở đây). Fail-safe: op_tail unmapped / fixture vắng / 0 transition
    # → trả [] ⟹ property 'action' GIỮ plain string (KHÔNG key 'enum').
    action_enum = _ovr.workflow_action_enum_for(op_tail)
    properties: dict[str, dict] = {}
    required_names: list[str] = []
    for pname, annotation, required in named:
        prop: dict = {"type": _json_type_for(annotation)}
        if pname in json_params:
            _annotate_json_string(prop, fn, op_tail, pname)
        # D17: chỉ bồi enum cho property TÊN 'action' khi resolve được ≥1 action thật
        # (action_enum non-empty). Param khác / op unmapped → KHÔNG đụng (plain string).
        if pname == "action" and action_enum:
            prop["enum"] = action_enum
        properties[pname] = prop
        if required:
            required_names.append(pname)
    schema: dict = {"type": "object", "properties": properties}
    if required_names:
        schema["required"] = sorted(required_names)
    return {
        "required": True,
        "content": {"application/json": {"schema": schema}},
    }


def _request_body_from_doctype(doctype: str) -> dict | None:
    """requestBody (application/json) sinh từ `frappe.get_meta(doctype)` (D5 form_dict bridge).

    Dùng cho POST `create_*` đọc form_dict (no signature-param) CÓ entry trong
    `openapi_overrides.FORM_DICT_DOCTYPE_MAP`. Lọc field meta:
      - giữ fieldtype ∈ `_ovr.INCLUDED_FIELDTYPES` (Data/Link/Select/Int/Float/Currency/
        Check/Date/Text/… — bảng `_ovr.FRAPPE_FIELDTYPE_JSON_MAP`); bỏ layout/Table/Attach.
      - bỏ field `hidden`.
      - bỏ field API tự set (`_ovr.autoset_fields_for(doctype)`: naming_series + per-DocType
        status/lifecycle_status) khỏi CẢ properties (vì user không nhập) lẫn `required`.
    `required` = reqd-meta trừ autoset, HOẶC override curated (`_ovr.REQUIRED_OVERRIDES`,
    vd AC Asset = SSoT `_ASSET_REQD_LABELS_VI`). type-map qua bảng Frappe RIÊNG (KHÔNG trộn
    `_TYPE_MAP` type-hint Python).

    DEFENSIVE: DocType không tồn tại / get_meta lỗi → trả None (KHÔNG vỡ toàn spec; endpoint
    quay về hành vi D4 rỗng). Import `frappe.get_meta` LAZY (đã import frappe ở module-top,
    nhưng get_meta chỉ gọi tại generate-time — registry import-được không-DB).

    Returns:
        dict requestBody hợp lệ OpenAPI 3.1 (object schema, properties NON-EMPTY) hoặc None
        (DocType lỗi / không có field data-bearing nào).
    """
    try:
        meta = frappe.get_meta(doctype)
    except Exception:  # pragma: no cover — defensive (DocType chưa migrate / lỗi)
        return None
    autoset = _ovr.autoset_fields_for(doctype)
    properties: dict[str, dict] = {}
    meta_required: list[str] = []
    for df in meta.fields:
        if df.fieldtype not in _ovr.INCLUDED_FIELDTYPES:
            continue
        if getattr(df, "hidden", 0):
            continue
        if df.fieldname in autoset:
            continue
        properties[df.fieldname] = {
            "type": _ovr.FRAPPE_FIELDTYPE_JSON_MAP[df.fieldtype]
        }
        if getattr(df, "reqd", 0):
            meta_required.append(df.fieldname)
    if not properties:
        return None
    # required: curated override (SSoT) NẾU có, ngược lại meta-reqd trừ autoset.
    override = _ovr.REQUIRED_OVERRIDES.get(doctype)
    required_names = list(override) if override is not None else meta_required
    # Lọc required về tập property thực tế (defensive: override field phải tồn tại property).
    required_names = sorted({f for f in required_names if f in properties})
    schema: dict = {"type": "object", "properties": properties}
    if required_names:
        schema["required"] = required_names
    return {
        "required": True,
        "content": {"application/json": {"schema": schema}},
    }


def _docstring_parts(fn: Any) -> tuple[str, str]:
    """(summary, description) từ `inspect.getdoc` — dòng 1 = summary, phần còn lại = desc."""
    doc = inspect.getdoc(fn) or ""
    if not doc:
        return "", ""
    lines = doc.splitlines()
    summary = lines[0].strip()
    description = "\n".join(lines[1:]).strip()
    return summary, description


def _error_response_object(code: str, message_vi: str) -> dict:
    """1 response lỗi (D6 E4): schema ref ErrorEnvelope + example envelope-error VI sạch.

    `code` PHẢI ∈ ErrorCode (E5); HTTP status = `_HTTP_FOR_CODE[code]` (KHÔNG bịa). Example
    là envelope `_err` shape thật ({success:false, error, code, http_status}). KHÔNG khai lại
    shape ErrorEnvelope — chỉ trỏ ref + thêm example.
    """
    http = _HTTP_FOR_CODE[code]
    return {
        "description": f"Lỗi {code} (envelope chuẩn).",
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/ErrorEnvelope"},
                "example": {
                    "success": False,
                    "error": message_vi,
                    "code": code,
                    "http_status": http,
                },
            }
        },
    }


# ── D12 baseline error-surface (typed 401/403 cho MỌI op) ─────────────────────
# Mô tả VI DẪN XUẤT từ comment-SSoT `utils/response.py` (ErrorCode.UNAUTHORIZED:46 =
# "chưa đăng nhập / session hết hạn"; ErrorCode.FORBIDDEN:47 = "đã đăng nhập nhưng thiếu
# quyền"). KHÔNG hardcode chuỗi rời rạc ở nơi khác — chỉ 1 nguồn ở đây, khớp ngữ nghĩa
# constants BE. VI-clean (no EN-status, no cap-token `[a-z]+\.[a-z]+`, no email).
_BASELINE_ERR_DESC_VI: dict[str, str] = {
    ErrorCode.UNAUTHORIZED: "Chưa đăng nhập hoặc phiên đã hết hạn",
    ErrorCode.FORBIDDEN: "Đã đăng nhập nhưng không đủ quyền thực hiện",
}


def _baseline_error_responses(is_guest: bool) -> dict[str, dict]:
    """Baseline typed error responses cho 1 operation (D12 — THUẦN, không side-effect).

    Trả `{<http_403>: ErrorEnvelope-response(FORBIDDEN)}` cộng `{<http_401>:
    ErrorEnvelope-response(UNAUTHORIZED)}` NẾU KHÔNG guest. Op guest (security==[]) KHÔNG
    cần phiên → KHÔNG có 401 (chỉ 403, vì cấm-quyền vẫn có thể xảy ra ở guest endpoint).

    Key status là `str(_HTTP_FOR_CODE[code])` (SSoT — KHÔNG bịa). Mỗi response reuse
    `_error_response_object` (ref ErrorEnvelope + example envelope VI sạch). Mô tả VI DẪN
    XUẤT từ `_BASELINE_ERR_DESC_VI` (khớp comment-SSoT response.py). Helper THUẦN —
    `_build_operation` MERGE bằng setdefault để `_enrich_operation` (chạy SAU) vẫn override/
    bồi `examples` cho 161 op curated mà baseline KHÔNG đè (curated WIN).

    Args:
        is_guest: True nếu operation là guest (security==[]) — bỏ 401.

    Returns:
        dict {status_key: response-object} — 1 key (403) khi guest, 2 key (401+403) khi authed.
    """
    out: dict[str, dict] = {
        str(_HTTP_FOR_CODE[ErrorCode.FORBIDDEN]): _error_response_object(
            ErrorCode.FORBIDDEN, _BASELINE_ERR_DESC_VI[ErrorCode.FORBIDDEN]
        )
    }
    if not is_guest:
        out[str(_HTTP_FOR_CODE[ErrorCode.UNAUTHORIZED])] = _error_response_object(
            ErrorCode.UNAUTHORIZED, _BASELINE_ERR_DESC_VI[ErrorCode.UNAUTHORIZED]
        )
    return out


def _enrich_operation(op_tail: str, operation: dict) -> None:
    """Enrich operation TỪ `openapi_overrides` (D6 — DẪN XUẤT, KHÔNG hardcode).

    Mọi nội dung enrich đến TỪ `_ovr.enrich_meta_for(op_tail)` (curated entry ưu tiên, hoặc
    fallback humanize cho op imm00/04/12 chưa curate). op-tail ngoài 3 module → meta=None →
    KHÔNG đụng (giữ default D1-D5, fail-safe). Mutate `operation` IN-PLACE:

      - `summary`/`description`: ghi đè (luôn non-empty cho 3 module — E0/đo-1).
      - `tags`: set theo meta.
      - `examples.request` (POST có requestBody): nhúng `content['application/json'].example`
        (E2 — keys ⊆ properties, required ⊆ keys do registry tự bảo đảm).
      - `examples.response`: response `200` THÊM `examples.success.value={success:true,data:…}`
        (E3 — vẫn ref SuccessEnvelope SSoT, KHÔNG đổi shape).
      - `examples.errors`: mỗi code → 1 response key `str(_HTTP_FOR_CODE[code])` ref ErrorEnvelope
        + example VI sạch (E4/E5).
    """
    meta = _ovr.enrich_meta_for(op_tail)
    if meta is None:
        return
    operation["summary"] = meta["summary"]
    operation["description"] = meta["description"]
    operation["tags"] = meta["tags"]

    examples = meta.get("examples") or {}
    # E2 — request example (chỉ khi op có requestBody application/json).
    req_example = examples.get("request")
    body = operation.get("requestBody")
    if req_example is not None and body:
        json_content = body.get("content", {}).get("application/json")
        if json_content is not None:
            json_content["example"] = req_example
    # E3 — response 200 envelope-success example (giữ ref SuccessEnvelope SSoT).
    resp_example = examples.get("response")
    if resp_example is not None:
        ok_content = operation["responses"]["200"]["content"]["application/json"]
        ok_content.setdefault("examples", {})["success"] = {
            "value": {"success": True, "data": resp_example}
        }
    # E4/E5 — error-responses VI (code ∈ ErrorCode, status từ _HTTP_FOR_CODE).
    for code, message_vi in (examples.get("errors") or {}).items():
        if code not in _HTTP_FOR_CODE:
            continue  # defensive: bỏ code lạ (E5 — chỉ ErrorCode SSoT).
        operation["responses"][str(_HTTP_FOR_CODE[code])] = _error_response_object(
            code, message_vi
        )


def _build_operation(
    mod_short: str, fn_name: str, fn: Any, is_guest: bool
) -> tuple[str, str, dict]:
    """Build (path, verb, operation-object) cho 1 endpoint whitelisted (D1+D2 + D6 enrich)."""
    op_id = f"assetcore.api.{mod_short}.{fn_name}"
    path = f"{_PATH_PREFIX}{op_id}"
    verb = _http_method_for(fn)
    summary, description = _docstring_parts(fn)
    # security: guest → [] (none); ngược lại → cookieSession (D2).
    security: list[dict] = [] if is_guest else [{"cookieSession": []}]
    operation: dict = {
        "operationId": op_id,
        # D9-TAGS: tag NAME canonical đọc SSoT `_ovr.canonical_tag` (KHÔNG raw mod_short —
        # gỡ leak slug nội bộ ra public spec). Op-enriched (imm00/04/12) sẽ được
        # `_enrich_operation` ghi đè CÙNG "IMM-XX" (idempotent — no double, enriched_count
        # bất biến). Module cross-cut chưa-map → canonical_tag raise (fail-fast T4).
        "tags": [_ovr.canonical_tag(mod_short)],
        "security": security,
        "responses": {
            "200": {
                "description": "Phản hồi thành công (envelope chuẩn).",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/SuccessEnvelope"}
                    }
                },
            },
            "default": {
                "description": "Lỗi (envelope chuẩn).",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorEnvelope"}
                    }
                },
            },
        },
    }
    # D2/D4/D5 param vs body bridge:
    #   - GET → query parameters (đọc dữ liệu qua query-string), KHÔNG requestBody.
    #   - POST CÓ signature-param → requestBody application/json (object schema),
    #     KHÔNG key `parameters` (param đi vào body, không lọt query) — D4.
    #   - POST không signature-param (form_dict/no-arg):
    #       · CÓ entry `FORM_DICT_DOCTYPE_MAP` → requestBody sinh từ DocType meta (D5).
    #       · KHÔNG có entry → requestBody=None → KHÔNG sinh (fail-safe, giữ D4).
    op_tail = f"{mod_short}.{fn_name}"
    if verb == "post":
        body = _request_body_for(fn, op_tail)
        if body is None:
            # D5: tra registry theo operationId-tail '<mod>.<fn>' (KHÔNG heuristic tên).
            doctype = _ovr.doctype_for(op_tail)
            if doctype:
                body = _request_body_from_doctype(doctype)
        if body is not None:
            operation["requestBody"] = body
    else:
        operation["parameters"] = _parameters_for(fn, op_tail)
    if summary:
        operation["summary"] = summary
    if description:
        operation["description"] = description
    # D12 baseline error-surface: MERGE typed 401/403 (authed) / 403 (guest) vào responses
    # bằng setdefault (CHỈ key chưa tồn tại) — chạy TRƯỚC `_enrich_operation` để 161 op
    # curated (imm00/04/12) vẫn override/bồi `examples` cho status D6 (curated WIN). Op
    # non-enriched (325) nhận baseline opaque-typed; op guest (5) KHÔNG có 401.
    for status_key, resp in _baseline_error_responses(is_guest).items():
        operation["responses"].setdefault(status_key, resp)
    # D6 enrich (Phase A6): DẪN XUẤT từ openapi_overrides — ghi đè summary/description,
    # nhúng examples request/response/error VI cho imm00/04/12 (fail-safe ngoài 3 module).
    _enrich_operation(f"{mod_short}.{fn_name}", operation)
    return path, verb, operation


def _error_code_values() -> list[str]:
    """Tập value hằng UPPER_CASE str của `ErrorCode` — đọc TRỰC TIẾP response.py (D3).

    Lọc: bỏ dunder/private + chỉ giữ value là `str` (loại helper/method nếu có).
    NGUỒN DUY NHẤT — KHÔNG khai lại danh sách ErrorCode trong file này.
    """
    return sorted(
        {
            v
            for k, v in vars(ErrorCode).items()
            if not k.startswith("_") and isinstance(v, str)
        }
    )


def _build_components() -> dict:
    """`components` với 2 envelope (D3) + securityScheme cookieSession (D2).

    `code.enum` ← `ErrorCode` (response.py:37); `http_status.enum` ←
    `_HTTP_FOR_CODE.values()` (response.py:60). Thêm ErrorCode/HTTP mới ở
    response.py → spec tự cập nhật lần generate kế (chống hardcode danh sách 2).
    """
    return {
        "schemas": {
            "SuccessEnvelope": {  # nguồn: utils/response.py:79 _ok
                "type": "object",
                "required": ["success", "data"],
                "properties": {
                    "success": {"type": "boolean", "enum": [True]},
                    "data": {},  # payload tuỳ endpoint (D6 enrich round sau).
                },
            },
            "ErrorEnvelope": {  # nguồn: utils/response.py:95 _err
                "type": "object",
                "required": ["success", "error", "code", "http_status"],
                "properties": {
                    "success": {"type": "boolean", "enum": [False]},
                    "error": {"type": "string"},
                    "code": {"type": "string", "enum": _error_code_values()},
                    "http_status": {
                        "type": "integer",
                        "enum": sorted(set(_HTTP_FOR_CODE.values())),
                    },
                    "fields": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                    },
                    # optional notification-framework fields (response.py:142-151).
                    "message_code": {"type": "string"},
                    "context": {"type": "object"},
                    "action_hint": {"type": "string"},
                    "severity": {"type": "string", "enum": list(_SEVERITY_ENUM)},
                    "title": {"type": "string"},
                },
            },
        },
        "securitySchemes": {
            "cookieSession": {"type": "apiKey", "in": "cookie", "name": "sid"},
        },
    }


def _root_tags(paths: dict) -> list[dict]:
    """Root-level `tags` (D8) — list[dict]{name,description} cho MỌI tag dùng ở operation.

    Quét `operation['tags']` của mọi path (đã sinh), gom tập tag DUY NHẤT, map mỗi tag →
    mô tả VI qua `_ovr.tag_description_for` (SSoT metadata — KHÔNG khai lại map ở đây,
    tránh drift). Đảm bảo MỌI tag dùng ở operation đều có entry (no orphan-tag) + KHÔNG
    entry thừa (chỉ tag thực sự xuất hiện). Sort theo `name` (ổn định Swagger UI).

    Args:
        paths: dict path → {verb → operation} đã sinh (mỗi operation có key 'tags').

    Returns:
        list[dict] `[{name, description}, ...]` sort theo name; mỗi description VI non-empty.
    """
    unique_tags: set[str] = set()
    for item in paths.values():
        for operation in item.values():
            for tag in operation.get("tags", []) or []:
                unique_tags.add(tag)
    entries: list[dict] = []
    for tag in sorted(unique_tags):
        # D16 (OpenAPI 3.1 §4.8.22 Tag Object): per-tag externalDocs trỏ doc module tương ứng
        # (IMM-XX → docs/imm-XX/README.md; cross-cut → doc chung docs/imm-00/README.md) GHÉP
        # doc-base hook `app_docs_url`. `_tag_external_docs` trả None khi hook chưa cấu hình →
        # KHÔNG gắn subkey externalDocs (0/23 — graceful omit, KHÔNG link chết). name+description
        # GIỮ NGUYÊN (D8/D9 bất biến, sort theo name không đổi); externalDocs chỉ là SUBKEY THÊM
        # khi cấu hình. Key-order subkey: name→description→externalDocs (externalDocs cuối).
        entry: dict = {
            "name": tag,
            "description": _ovr.tag_description_for(tag),
        }
        tag_ed = _tag_external_docs(tag)
        if tag_ed is not None:
            entry["externalDocs"] = tag_ed
        entries.append(entry)
    return entries


def _assetcore_stats(paths: dict) -> dict:
    """`x-assetcore-stats` (D8) — số liệu coverage đếm ĐỘNG (THUẦN, KHÔNG DB/get_meta).

    Mọi con số DẪN XUẤT từ introspection — KHÔNG hardcode magic number:
      - total_endpoints = len(paths).
      - get_count / post_count = Σ verb get / post trong paths (get+post == total).
      - guest_count = số OPERATION trong `paths` có `security == []` (D11 — bề mặt guest
        THẬT mà spec phơi ra). DẪN XUẤT từ CHÍNH paths dict (cùng nguồn total/get/post/
        enriched) — KHÔNG đọc `frappe.guest_methods` global volatile (registry gồm guest-
        method của MỌI app + re-import → trả 2/5/10 tuỳ worker-boot context, gây drift
        10-vs-5). `_guest_name_set()` GIỮ là SSoT cho quyết định is_guest per-op trong
        `_build_operation` (security==[] do đó); ở đây chỉ ĐẾM lại operation đã render.
      - enriched_count = số op-tail có `_ovr.enrich_meta_for(tail) is not None`
        (== op thuộc imm00/04/12 — đếm bằng CHÍNH helper, KHÔNG magic).
      - json_param_count = Σ param JSON-string introspect-được qua MỌI endpoint
        (D10 — đếm động bằng `_json_string_params`, KHÔNG hardcode 109 call-site).
      - cap_set_version = `rbac.CAP_SET_VERSION` (lazy-import như `_spec_cache_key` —
        chống circular import lúc `bench start`).
      - generated_app_version = `_app_version()` (== info.version).

    Args:
        paths: dict path → {verb → operation} đã sinh.

    Returns:
        dict các khóa stats (int cho số đếm; str cho 2 version).
    """
    from assetcore.services.shared import rbac  # lazy — chống circular import.

    get_count = sum(1 for item in paths.values() if "get" in item)
    post_count = sum(1 for item in paths.values() if "post" in item)
    # D11: bề mặt guest = số OPERATION đã render có security==[] (đếm trên paths, KHÔNG
    # global). Đếm theo operation (không path-item) — path multi-verb sẽ đếm từng verb.
    guest_count = sum(
        1
        for item in paths.values()
        for op in item.values()
        if op.get("security") == []
    )
    enriched_count = 0
    for path in paths:
        tail = path[len(_PATH_PREFIX) :].replace("assetcore.api.", "", 1)
        if _ovr.enrich_meta_for(tail) is not None:
            enriched_count += 1
    # D12: số op có ≥1 response key 4xx/5xx (đếm ĐỘNG — KHÔNG hardcode). Khớp `^[45]\d\d$`:
    # key 3 ký tự, bắt đầu '4'/'5', toàn chữ số (KHÔNG đếm '200'/'default').
    error_responses_typed_count = sum(
        1
        for item in paths.values()
        for op in item.values()
        if any(_is_4xx_5xx(code) for code in op.get("responses", {}))
    )
    return {
        "total_endpoints": len(paths),
        "get_count": get_count,
        "post_count": post_count,
        "guest_count": guest_count,
        "enriched_count": enriched_count,
        "error_responses_typed_count": error_responses_typed_count,
        "json_param_count": _total_json_string_params(),
        "cap_set_version": rbac.CAP_SET_VERSION,
        "generated_app_version": _app_version(),
    }


def _is_4xx_5xx(code: str) -> bool:
    """True nếu `code` là chuỗi status-code 4xx/5xx hợp lệ (`^[45]\\d\\d$`).

    Loại key '200'/'default'/chuỗi lạ. Dùng đếm `error_responses_typed_count` (D12) —
    THUẦN string-check (KHÔNG cần `re`, bất biến cho mọi status 400-599).
    """
    return len(code) == 3 and code[0] in ("4", "5") and code.isdigit()


def _total_json_string_params() -> int:
    """Σ số param JSON-string introspect-được qua MỌI endpoint whitelisted (D10).

    Đếm ĐỘNG: re-introspect 22 module-file + `_json_string_params` mỗi fn → tổng số
    (fn, param) là JSON-string. KHÔNG hardcode 109; thêm param parse_json mới → tự tăng
    (mutation-guard có răng). Mỗi (fn, param) đếm 1 lần kể cả nhiều call-site cùng param.
    """
    total = 0
    name_set = _whitelisted_name_set()
    for module in _iter_api_modules():
        for _fn_name, fn in _whitelisted_functions_in(module, name_set):
            total += len(_json_string_params(fn))
    return total


# ── D13 servers[] (base URL ĐỘNG từ get_url() SSoT — KHÔNG hardcode host) ──────
# Mô tả VI cho server site hiện tại + fallback. CHÈN ở root spec (sau info, trước
# components). Swagger UI native render dropdown 'Servers' + dùng cho 'Try it out'.
_SERVERS_DESC_VI = "Site hiện tại — dẫn xuất động từ cấu hình Frappe"
_SERVERS_FALLBACK_DESC_VI = (
    "Cùng nguồn với trang tài liệu (fallback — không lấy được URL site động)"
)


def _servers() -> list[dict]:
    """Root `servers[]` OpenAPI 3.1 — base URL ĐỘNG từ `frappe.utils.get_url()` (SSoT).

    `servers[0].url` = BARE origin của site hiện tại (`frappe.utils.get_url()`) —
    KHÔNG kèm `_PATH_PREFIX` (path-prefix đã nằm trong từng `paths` key), KHÔNG
    trailing slash thừa (`.rstrip('/')`). Cho Swagger UI 'Try it out' + codegen base
    URL đúng, đa-môi-trường/air-gapped (đổi site/host → URL tự đổi lần generate kế).
    KHÔNG hardcode host/URL ở đây — CHỈ gọi get_url() (no-hardcode guard TC-OAS-D13-04).

    Fail-safe (ngữ cảnh không-request / test / get_url lỗi): url rỗng/None/raise →
    fallback an toàn `[{'url':'/', 'description':<fallback>}]` (relative root — Swagger
    UI dùng page-origin) → generate_spec() KHÔNG bao giờ exception vì servers.

    Returns:
        list[dict] 1 entry `[{url, description}]` — luôn non-empty (>=1).
    """
    try:
        base = frappe.utils.get_url()
    except Exception:  # pragma: no cover — ngữ cảnh không-request / lỗi cấu hình.
        base = None
    base = (base or "").rstrip("/")
    if not base:  # rỗng/None → fallback relative root (page-origin Swagger UI).
        return [{"url": "/", "description": _SERVERS_FALLBACK_DESC_VI}]
    return [{"url": base, "description": _SERVERS_DESC_VI}]


# ── D16 externalDocs (doc-base SSoT = hook `app_docs_url`; graceful omit khi chưa cấu hình) ─
# Bám ADR-IMM00-OPENAPI §D16 + OpenAPI 3.1 §4.8.11 (Root) / §4.8.22 (Tag Object) `externalDocs`.
# D16 SỬA SSoT doc-base: KHÔNG còn `get_url()` (= API origin site Frappe → 404 vì docs markdown
# repo-only, KHÔNG web-served). Doc-base MỚI = hook `app_docs_url` (app-scoped get_hooks
# app_name='assetcore', CÙNG pattern D14) — trỏ nơi docs THỰC SỰ web-served. KHÔNG hardcode host.
#   · CẤU HÌNH non-empty → externalDocs xuất (root + 23 tag), url = <base>/docs/imm-XX/README.md.
#   · VẮNG/rỗng/None (mặc định hiện tại) → OMIT externalDocs HẲN (root key vắng + 0/23 tag).
#     Lý do: link chết tệ hơn không link — KHÔNG fabricate URL 404. generate_spec() KHÔNG raise
#     (helper trả None khi omit ⟹ caller bỏ qua). servers[] (D13) GIỮ get_url() (api-base KHÁC).
_ROOT_EXTERNAL_DOCS_DESC_VI = (
    "Tài liệu phát triển AssetCore (docs/) — kiến trúc, module IMM, tuân thủ NĐ98/WHO HTM"
)
_DOCS_BASE_HOOK = "app_docs_url"  # hook SSoT doc-base (app-scoped, D14 pattern — KHÔNG get_url).


def _doc_base() -> str:
    """Doc-base ĐÃ CẤU HÌNH từ hook `app_docs_url` (app-scoped SSoT, D16) — '' khi chưa khai.

    Đọc qua `_app_meta_hook(_DOCS_BASE_HOOK)` (CÙNG cơ chế D14 app_publisher/app_license —
    app-scoped get_hooks, phần tử [0] strip), rstrip trailing slash. KHÔNG còn dùng API-origin
    helper Frappe (= API base → 404 vì docs repo-only, KHÔNG web-served). KHÔNG hardcode host
    (no-hardcode guard): vùng source KHÔNG literal scheme/host/tên-site.

    Fail-safe: hook vắng/rỗng/None/lỗi (kể cả `_app_meta_hook` raise) → '' (caller OMIT
    externalDocs — KHÔNG fabricate, generate_spec() KHÔNG raise). try/except bọc TƯỜNG MINH
    ngoài fail-safe nội bộ `_app_meta_hook` để chắc doc-base KHÔNG bao giờ vỡ spec.

    Returns:
        Doc-base đã rstrip (nơi docs web-served / Git browse base), hoặc '' khi chưa cấu hình.
    """
    try:
        base = _app_meta_hook(_DOCS_BASE_HOOK)
    except Exception:  # pragma: no cover — fail-safe: lỗi đọc hook → '' (OMIT, KHÔNG raise).
        base = None
    return (base or "").rstrip("/")


def _docs_base_or_none() -> str | None:
    """Doc-base ĐÃ CẤU HÌNH hoặc None (D16 gate omit) — None ⟹ OMIT externalDocs.

    Returns:
        str doc-base non-empty (đã rstrip), hoặc None (hook `app_docs_url` chưa cấu hình).
    """
    base = _doc_base()
    return base or None


def _doc_url(rel_path: str) -> str:
    """Ghép doc-URL ABSOLUTE từ doc-base ĐÃ CẤU HÌNH + rel-path (D16) — normalize no double-slash.

    CHỈ gọi khi `_docs_base_or_none()` non-None (base ĐÃ cấu hình). Ghép `<base>/<rel_path>`:
    base đã rstrip trailing slash ở `_doc_base`, rel_path strip leading slash → KHÔNG bao giờ
    double-slash giữa base và path (base có trailing slash đã được chuẩn hoá ở `_doc_base`).

    Args:
        rel_path: đường dẫn doc tương đối (vd 'docs/imm-04/README.md').

    Returns:
        URL doc ABSOLUTE `<base>/<rel>` (NON-EMPTY khi base cấu hình).
    """
    base = _doc_base()
    return f"{base}/{rel_path.lstrip('/')}"


def _external_docs_root() -> dict | None:
    """Root-level `externalDocs` OpenAPI 3.1 (§4.8.11) — {url, description} hoặc None (D16 T2/T5).

    `url` = doc nền tảng (`_ovr._DOC_ROOT_PATH` = 'docs/imm-00/README.md') ghép doc-base ĐÃ CẤU
    HÌNH. Trả None khi `app_docs_url` chưa cấu hình ⟹ generate_spec() OMIT key 'externalDocs'
    HẲN (KHÔNG fabricate link chết). `description` VI non-empty (chỉ khi present).

    Returns:
        dict `{'url', 'description'}` khi doc-base cấu hình; None khi chưa cấu hình (→ omit).
    """
    if _docs_base_or_none() is None:
        return None  # chưa cấu hình app_docs_url → OMIT root externalDocs (KHÔNG link chết).
    return {
        "url": _doc_url(_ovr._DOC_ROOT_PATH),
        "description": _ROOT_EXTERNAL_DOCS_DESC_VI,
    }


def _tag_external_docs(tag: str) -> dict | None:
    """Per-tag `externalDocs` OpenAPI 3.1 Tag Object (§4.8.22) — {url, description} hoặc None (D16).

    Rel-path doc của `tag` từ SSoT `_ovr.tag_doc_path` ('IMM-04'→'docs/imm-04/README.md';
    cross-cut/lạ → doc chung 'docs/imm-00/README.md'). url ghép doc-base ĐÃ CẤU HÌNH. Trả None
    khi `app_docs_url` chưa cấu hình ⟹ `_root_tags` KHÔNG gắn subkey externalDocs (0/23 — KHÔNG
    fabricate). description = `_ovr.tag_external_desc_for(tag)` (VI non-empty, chứa tên tag).

    Args:
        tag: tên tag CANONICAL (vd 'IMM-04', 'Xác thực').

    Returns:
        dict `{'url', 'description'}` khi doc-base cấu hình; None khi chưa cấu hình (→ omit).
    """
    if _docs_base_or_none() is None:
        return None  # chưa cấu hình app_docs_url → tag KHÔNG có subkey externalDocs.
    return {
        "url": _doc_url(_ovr.tag_doc_path(tag)),
        "description": _ovr.tag_external_desc_for(tag),
    }


def generate_spec() -> dict:
    """Sinh OpenAPI 3.1 dict TỪ introspection `@frappe.whitelist` (D1-D15).

    `info` (D14) THÊM `contact` (name=app_publisher + email tùy chọn) + `license`
    ({name,identifier} SPDX = app_license) DẪN XUẤT app-scoped hook SSoT `frappe.get_hooks(
    hook, app_name='assetcore')` — fail-safe (hook vắng/rỗng → bỏ qua, KHÔNG raise; app_email
    rỗng → KHÔNG key 'email'). KHÔNG hardcode chuỗi license/publisher literal — đọc qua hook.
    info giữ title/version/description.

    `externalDocs` (D16) CHÈN CÓ ĐIỀU KIỆN GIỮA `tags`↔`x-assetcore-stats` (root §4.8.11) +
    mỗi tag entry có subkey `externalDocs` (§4.8.22) — CHỈ khi hook `app_docs_url` cấu hình
    non-empty (doc-base SSoT; KHÔNG dùng API origin → 404 vì docs repo-only). Cấu hình →
    root + 23 tag, url = <base>/docs/imm-XX/README.md. CHƯA cấu hình (mặc định) → BỎ root key
    'externalDocs' HẲN + 0/23 tag subkey (key-order `tags→x-assetcore-stats` liền; KHÔNG link
    chết). externalDocs = field root + tag-level (KHÔNG operation/path) ⟹ x-assetcore-stats +
    root tags name+description BẤT BIẾN. servers[] (D13) GIỮ get_url() (API base, KHÁC doc-base).

    Returns:
        dict OpenAPI 3.1 `{openapi, info, servers, components, paths, tags, x-assetcore-stats}`.
        `servers` (D13) = base URL ĐỘNG từ `get_url()` (chèn sau info, trước components;
        fail-safe relative '/'). Mỗi endpoint whitelisted (introspect-được, loại re-export) → 1 path
        `/api/method/assetcore.api.<mod>.<fn>` với operationId DUY NHẤT. `tags` (D8) phủ
        ĐỦ tập tag duy nhất ở operation (no orphan); `x-assetcore-stats` (D8) chứa số liệu
        coverage đếm động. Thứ tự key info/components/paths GIỮ NGUYÊN (D1-D7); 2 key D8
        chèn SAU paths.

    Đảm bảo (acceptance): `len(spec['paths']) == số fn whitelisted introspect-được`
    (== `grep -c '^@frappe.whitelist' api/*.py`); `x-assetcore-stats.total_endpoints ==
    len(paths)`; `get_count + post_count == total_endpoints`. Chạy KHÔNG exception trên cả
    485 endpoint. KHÔNG modify core, KHÔNG đụng response.py (chỉ đọc enum).
    """
    modules = _iter_api_modules()
    name_set = _whitelisted_name_set()
    guest_set = _guest_name_set()

    paths: dict[str, dict] = {}
    for module in modules:
        mod_short = _module_short(module)
        for fn_name, fn in _whitelisted_functions_in(module, name_set):
            qual = getattr(fn, "__qualname__", getattr(fn, "__name__", ""))
            is_guest = (module.__name__, qual) in guest_set
            path, verb, operation = _build_operation(mod_short, fn_name, fn, is_guest)
            paths.setdefault(path, {})[verb] = operation

    # D14 info-contact-license: chèn CÓ ĐIỀU KIỆN sau 'description' (dict-merge — KHÔNG
    # sinh key None). DẪN XUẤT app-scoped hook SSoT; helper trả None → bỏ qua (info giữ
    # title/version/description nguyên vẹn, KHÔNG sinh dict rỗng).
    info: dict = {
        "title": _API_TITLE,
        "version": _app_version(),
        "description": _API_DESC,
    }
    contact = _info_contact()
    if contact is not None:
        info["contact"] = contact
    license_obj = _info_license()
    if license_obj is not None:
        info["license"] = license_obj

    spec: dict = {
        "openapi": _OPENAPI_VERSION,
        "info": info,
        # D13 servers — CHÈN ngay sau info, TRƯỚC components (info→servers→components→
        # paths→tags→[externalDocs]→x-assetcore-stats). Base URL ĐỘNG từ get_url() SSoT.
        "servers": _servers(),
        "components": _build_components(),
        "paths": paths,
        # D8 metadata — chèn SAU paths (info/components/paths giữ thứ tự D1-D7).
        "tags": _root_tags(paths),
    }
    # D16 externalDocs (root-level §4.8.11) — CHÈN CÓ ĐIỀU KIỆN GIỮA `tags` và `x-assetcore-stats`.
    # Doc-base = hook `app_docs_url` (KHÔNG get_url — đó là API origin → 404 vì docs repo-only).
    #   · CẤU HÌNH → key-order `...→tags→externalDocs→x-assetcore-stats` (T4).
    #   · CHƯA cấu hình (mặc định) → `_external_docs_root()` None ⟹ BỎ key 'externalDocs' HẲN,
    #     `tags→x-assetcore-stats` LIỀN (T5 — KHÔNG lỗ trống, KHÔNG key None, KHÔNG link chết).
    # externalDocs = field root (KHÔNG operation/path) → x-assetcore-stats BẤT BIẾN (T7).
    root_ed = _external_docs_root()
    if root_ed is not None:
        spec["externalDocs"] = root_ed
    # x-assetcore-stats LUÔN cuối (sau externalDocs nếu present, hoặc liền sau tags nếu omit).
    spec["x-assetcore-stats"] = _assetcore_stats(paths)
    return spec


# ── D7 serve (session-gated + cached) ─────────────────────────────────────────
_SPEC_CACHE_PREFIX = "ac_openapi_spec_v"
_SPEC_CACHE_TTL_SEC = 3600  # 1h — đủ lâu cho tài liệu, đủ ngắn để self-heal.


def _spec_cache_key() -> str:
    """Khoá cache versioned cho spec — bust tự động khi cap-set / app version đổi.

    Dẫn xuất từ `services.shared.rbac.CAP_SET_VERSION` (số cap + hash tên cap) + `_app_version()`
    (`assetcore.__version__`). Thêm 1 cap (CAP_SET_VERSION đổi) HOẶC bump `__version__` → key MỚI
    → cache cũ bị bỏ qua (miss) → re-introspect sinh spec mới → KHÔNG bao giờ phục vụ spec stale.
    Giống pattern `ac_caps::*` (rbac.py). Import `rbac` LAZY trong function để tránh circular
    import lúc `bench start` (api.openapi ↔ services.shared.rbac).

    Returns:
        'ac_openapi_spec_v<cap_set_version>.<app_version>' — string ổn định khi 2 nguồn không đổi.
    """
    from assetcore.services.shared import rbac  # lazy — chống circular import.

    return f"{_SPEC_CACHE_PREFIX}{rbac.CAP_SET_VERSION}.{_app_version()}"


def _cached_spec() -> dict:
    """Trả OpenAPI spec dict — đọc cache trước, miss thì `generate_spec()` rồi set.

    HIT (`frappe.cache().get_value(key)` không None) → parse JSON trả thẳng, KHÔNG gọi
    `generate_spec` (KHÔNG re-introspect 485 endpoint — TC-OAS-D7-03). MISS → introspect 1 lần,
    set cache TTL 1h, trả spec. Key versioned (`_spec_cache_key`) bust khi cap/version đổi
    (TC-OAS-D7-04).

    LƯU JSON STRING (KHÔNG dict thô): spec ~634KB; round-trip string ổn định mọi kích cỡ.

    `get_value(key, expires=True)` (KHÔNG default `expires=False`): key set qua `expires_in_sec`
    nên PHẢI đọc với `expires=True` — nếu không, lần miss đầu `get_value` ghi `frappe.local.cache
    [key] = None` (poison), `set_value(expires_in_sec=...)` chỉ ghi redis (KHÔNG ghi local.cache)
    → lần get kế đọc trúng None ở local.cache → cache MISS vĩnh viễn (mỗi request re-introspect).
    `expires=True` bỏ qua nhánh ghi local.cache → đọc thẳng redis (Frappe RedisWrapper).
    """
    import json

    key = _spec_cache_key()
    cached = frappe.cache().get_value(key, expires=True)
    if cached is not None:
        try:
            return json.loads(cached)
        except (TypeError, ValueError):  # pragma: no cover — cache corrupt/legacy → re-gen.
            pass
    spec = generate_spec()
    frappe.cache().set_value(
        key, frappe.as_json(spec), expires_in_sec=_SPEC_CACHE_TTL_SEC
    )
    return spec


def _bust_spec_cache() -> None:
    """Xoá MỌI key cache spec (mọi version) — dùng cho test isolation + manual bust.

    Xoá theo wildcard prefix (`ac_openapi_spec_v*`) giống `invalidate_capabilities`
    (`ac_caps::*`) → không cần biết version hiện hành. Idempotent (no-op khi cache rỗng).
    """
    frappe.cache().delete_keys(f"{_SPEC_CACHE_PREFIX}*")


@frappe.whitelist(methods=["GET"])
def spec() -> dict:
    """Trả OpenAPI 3.1 spec THUẦN (raw dict) cho Swagger UI / integrator.

    Session-gated (D7/F6): chỉ user đã đăng nhập (`frappe.session.user != 'Guest'`) mới nhận
    spec — Guest → `frappe.PermissionError` (HTTP 401/403 chuẩn Frappe) để KHÔNG lộ bề mặt 485
    endpoint cho khách (môi trường bệnh viện). GET-only (`@frappe.whitelist(methods=['GET'])`),
    KHÔNG `allow_guest`. Trả RAW dict — KHÔNG bọc SuccessEnvelope (Swagger UI/integrator cần spec
    OpenAPI thuần, không envelope `{success, data}`). Cache qua `_cached_spec()` (versioned key,
    HIT không re-introspect, tự bust khi cap/app-version đổi).

    Returns:
        dict OpenAPI 3.1 `{openapi:'3.1.0', info, components, paths}` == `generate_spec()`.

    Raises:
        frappe.PermissionError: khi caller là Guest (chưa đăng nhập).
    """
    if frappe.session.user == "Guest":
        frappe.throw(
            frappe._("Cần đăng nhập để xem OpenAPI spec."), frappe.PermissionError
        )
    return _cached_spec()
