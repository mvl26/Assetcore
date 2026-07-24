# Copyright (c) 2026, AssetCore Team
"""OpenAPI override registry — map form_dict POST `create_*` → DocType (D5 body-bridge).

Bám **ADR-IMM00-OPENAPI §D4/D5**. Module Python THUẦN TĨNH (import-được KHÔNG side-effect,
KHÔNG chạm DB ở mức module): chỉ chứa dict/hằng. `frappe.get_meta` được gọi LAZY trong
`openapi.generate_spec` (KHÔNG ở đây) → registry import-được kể cả khi chưa connect site /
chưa migrate.

Vấn đề D4: ~21 POST `create_*` đọc `frappe.local.form_dict` (KHÔNG signature-param) →
generator D4 không suy được schema body → `requestBody` rỗng. D5 vá: với mỗi op có entry
trong `FORM_DICT_DOCTYPE_MAP`, generator dựng object schema TỪ `frappe.get_meta(DocType)`
(data/link/select/check/date/int/float fields, bỏ hidden) → requestBody NON-EMPTY tường minh.

Nguyên tắc (ADR §D5):
  - **MAP TƯỜNG MINH** operationId-tail → tên DocType chính xác. KHÔNG heuristic từ tên hàm,
    KHÔNG rải map trong từng endpoint. Đây là nơi DUY NHẤT chứa map form_dict→DocType.
  - **reqd từ meta, API-default field bị loại:** field reqd ở DocType nhưng do API tự set /
    default (naming_series, status, lifecycle_status cho AC Asset) → KHÔNG vào
    `requestBody.required`. Xem `API_AUTOSET_FIELDS`.
  - **AC Asset required = SSoT `_ASSET_REQD_LABELS_VI`** (imm00) = ['asset_category','asset_name'].
    Khai lại keys ở đây (`REQUIRED_OVERRIDES`) CÓ cross-ref comment để tránh import vòng
    api.openapi → api.imm00 (imm00 import nặng services/rbac). Giá trị PHẢI khớp imm00.
  - **Fail-safe:** form_dict create_* KHÔNG có entry → generator giữ hành vi D4
    (requestBody=None). KHÔNG sinh body sai.

D6 enrich (Phase A6): thêm `OPERATION_META` (metadata enrich imm00/04/12) + lexicon/derive
fallback. Generator (`openapi._enrich_operation`) DẪN XUẤT từ đây — KHÔNG hardcode trong
openapi.py. Vẫn THUẦN: `OPERATION_META` là dict tĩnh, không gọi `get_meta`/DB lúc import.

D10 JSON-param (Phase A10): thêm `JSON_PARAM_OVERRIDES` (registry curated SSoT DUY NHẤT cho
param JSON-string cần `x-decoded-schema` tường minh) + `json_param_override_for`. Generator
(`openapi._json_string_params` + `_annotate_json_string`) tự KHÁM PHÁ tập param JSON-string qua
AST (KHÔNG hardcode 109 call-site) → gắn `format:json`; registry chỉ bồi decoded-schema khi cần.
Entry `{'doctype': DT}` được generator giải lazy qua D5 `_request_body_from_doctype` (vẫn THUẦN:
KHÔNG get_meta lúc import). Drift-guard: mọi key resolve về param JSON-string introspect-được.

D15/D16 externalDocs (Phase A D15→D16): thêm `_DOC_ROOT_PATH` + `tag_doc_path(tag)` (canonical-tag
→ relative doc-path `docs/imm-XX/README.md`, cross-cut/lạ → doc chung) + `tag_external_desc_for(tag)`
(mô tả VI per-tag). THUẦN tĩnh — relative-path SSoT KHÔNG host/DB (đúng tầng). D16 (DOCBASE-FIX):
host ghép ở generator `openapi._doc_url` từ **hook `app_docs_url`** (app-scoped, web-served docs /
Git browse base) — KHÔNG còn `get_url()` (= API origin → dead 404 vì docs repo-only). Khi
`app_docs_url` chưa cấu hình → generator OMIT externalDocs (graceful-omit). SSoT doc-path map cạnh
`canonical_tag`/`tag_description_for`.

KHÔNG modify core, KHÔNG đụng utils/response.py, KHÔNG thêm capability, KHÔNG serve HTTP.
"""
from __future__ import annotations

import json
import pathlib
import re

# ── Map operationId-tail (`<module>.<fn>`) → tên DocType chính xác ─────────────
# operationId đầy đủ = 'assetcore.api.<module>.<fn>'; key ở đây là TAIL '<module>.<fn>'.
# CHỈ các POST `create_*` đọc form_dict (no signature-param) — POST có signature-param đã
# được D4 body-bridge xử lý qua `inspect.signature`. Map tường minh, verify-source từng dòng
# (new_doc(_DT_*) / repo.DOCTYPE / service target). DocType core (vd 'User') KHÔNG map →
# fail-safe (giữ D4 None) + lọt vào coverage 'unmapped'.
FORM_DICT_DOCTYPE_MAP: dict[str, str] = {
    # imm00 (14 form_dict create_*; create_asset/_supplier/... đọc frappe.local.form_dict)
    "imm00.create_asset": "AC Asset",
    "imm00.create_supplier": "AC Supplier",
    "imm00.create_location": "AC Location",
    "imm00.create_department": "AC Department",
    "imm00.create_asset_category": "AC Asset Category",
    "imm00.create_device_model": "IMM Device Model",
    "imm00.create_incident": "Incident Report",
    "imm00.create_transfer": "Asset Transfer",
    "imm00.create_service_contract": "Service Contract",
    "imm00.create_sla_policy": "IMM SLA Policy",
    "imm00.create_pm_schedule": "PM Schedule",
    "imm00.create_pm_template": "PM Checklist Template",
    "imm00.create_firmware_cr": "Firmware Change Request",
    "imm00.create_document_request": "Document Request",
    # imm08 (PM module — service-layer create qua repo DOCTYPE)
    "imm08.create_pm_schedule": "PM Schedule",
    "imm08.create_pm_template": "PM Checklist Template",
    "imm08.create_pm_work_order": "PM Work Order",
    # inventory (kho/vật tư)
    "inventory.create_spare_part": "AC Spare Part",
    "inventory.create_uom": "AC UOM",
    "inventory.create_warehouse": "AC Warehouse",
    # NOTE: user.create_system_user → core 'User' DocType — CỐ TÌNH KHÔNG map (core, body
    # nhiễu nhiều field) → fail-safe D4 None + theo dõi qua coverage guard 'unmapped'.
}

# ── Field DocType reqd nhưng API tự set/default → KHÔNG đưa vào requestBody.required ──
# Per-DocType. AC Asset: naming_series (auto), status + lifecycle_status (workflow/default,
# API set qua transition_asset_status). create_supplier: naming_series (auto). Toàn cục:
# naming_series là field hệ thống Frappe luôn autoset → loại ở MỌI DocType.
API_AUTOSET_FIELDS_GLOBAL: frozenset[str] = frozenset({"naming_series"})
API_AUTOSET_FIELDS: dict[str, frozenset[str]] = {
    "AC Asset": frozenset({"naming_series", "status", "lifecycle_status"}),
}

# ── Override `required` cho DocType có API-level reqd KHÁC meta-reqd ──────────────
# AC Asset: SSoT = `_ASSET_REQD_LABELS_VI` keys (imm00.py:139). Khai lại Ở ĐÂY có cross-ref
# (tránh import vòng api.openapi → api.imm00). GIÁ TRỊ PHẢI KHỚP imm00._ASSET_REQD_LABELS_VI.
# Khi thiếu key trong dict này → generator dùng meta-reqd trừ autoset (mặc định).
_ASSET_REQUIRED_SSOT = ["asset_category", "asset_name"]  # ↔ imm00._ASSET_REQD_LABELS_VI
REQUIRED_OVERRIDES: dict[str, list[str]] = {
    "AC Asset": list(_ASSET_REQUIRED_SSOT),
}

# ── Frappe fieldtype → JSON Schema type (D5). TÁCH khỏi `_TYPE_MAP` (Python type-hint,
# openapi.py) — 2 nguồn khác nhau, KHÔNG trộn. Chỉ map các fieldtype "data-bearing"; field
# layout (Section/Column Break), Table (child), Attach, Text Editor… KHÔNG sinh property. ──
FRAPPE_FIELDTYPE_JSON_MAP: dict[str, str] = {
    "Data": "string",
    "Link": "string",
    "Select": "string",
    "Small Text": "string",
    "Text": "string",
    "Long Text": "string",
    "Code": "string",
    "Read Only": "string",
    "Password": "string",
    "Date": "string",
    "Datetime": "string",
    "Time": "string",
    "Int": "integer",
    "Float": "number",
    "Currency": "number",
    "Percent": "number",
    "Check": "boolean",
}

# Tập fieldtype được PHÉP đưa vào requestBody (== keys của map trên — single source).
INCLUDED_FIELDTYPES: frozenset[str] = frozenset(FRAPPE_FIELDTYPE_JSON_MAP)


def doctype_for(op_tail: str) -> str | None:
    """DocType map cho operationId-tail (`<module>.<fn>`), hoặc None nếu chưa map (fail-safe)."""
    return FORM_DICT_DOCTYPE_MAP.get(op_tail)


def autoset_fields_for(doctype: str) -> frozenset[str]:
    """Field API tự set cho `doctype` (per-DocType ∪ global naming_series)."""
    return API_AUTOSET_FIELDS.get(doctype, frozenset()) | API_AUTOSET_FIELDS_GLOBAL


# ══════════════════════════════════════════════════════════════════════════════
# D10 — JSON_PARAM_OVERRIDES: decoded-schema tường minh cho param JSON-string.
#
# Bám ADR-IMM00-OPENAPI §D10. Nhiều whitelisted-fn nhận 1 param là CHUỖI JSON
# (`filters`, `data`, `fields`, `items`, `parts`…) rồi `parse_json`/`json.loads`
# server-side. Generator (`openapi._json_string_params`) tự KHÁM PHÁ tập param này
# qua AST (đếm động, KHÔNG hardcode 109 call-site) → gắn `format:json` +
# `x-decoded-default-type` (dẫn xuất default literal) vào schema con.
#
# Registry NÀY là SSoT DUY NHẤT cho param cần `x-decoded-schema` TƯỜNG MINH (object-
# shape của payload sau-decode) — vượt qua mức `x-decoded-default-type` chung chung.
# Keyed '<module>.<fn>.<param>'. Mỗi entry:
#   - {'x-decoded-schema': {...}} → object-shape literal (thuần tĩnh).
#   - {'doctype': 'Asset Commissioning'} → generator dựng shape TỪ DocType meta
#     (TÁI DÙNG D5 `_request_body_from_doctype`, lazy get_meta tại generate-time —
#     registry vẫn import-được không-DB). KHÔNG get_meta ở mức module.
#
# Drift-guard (test TC-OAS-D10-05): MỌI key PHẢI resolve về 1 param JSON-string
# introspect-được thực tế; entry trỏ param không-tồn-tại → test fail.
# ══════════════════════════════════════════════════════════════════════════════
JSON_PARAM_OVERRIDES: dict[str, dict] = {
    # imm04.create_commissioning(data: str) — `data` là JSON hồ sơ nghiệm thu →
    # shape = DocType 'Asset Commissioning' (tái dùng D5 doctype-bridge).
    "imm04.create_commissioning.data": {"doctype": "Asset Commissioning"},
    # imm04.save_commissioning(name, fields: str) — `fields` là JSON các trường cần
    # cập nhật (subset của Asset Commissioning) → cùng DocType shape.
    "imm04.save_commissioning.fields": {"doctype": "Asset Commissioning"},
}


def json_param_override_for(op_tail: str, param: str) -> dict | None:
    """Override decoded-schema cho 1 param JSON-string của op (D10), hoặc None (fail-safe).

    Args:
        op_tail: operationId-tail '<module>.<fn>'.
        param: tên param JSON-string.

    Returns:
        dict override (`{'x-decoded-schema': {...}}` hoặc `{'doctype': ...}`), hoặc None
        nếu cặp (op_tail, param) KHÔNG có entry curated.
    """
    return JSON_PARAM_OVERRIDES.get(f"{op_tail}.{param}")


# ══════════════════════════════════════════════════════════════════════════════
# D17 — WORKFLOW_ACTION_OVERRIDES: enum constraint cho body-param 'action' của 5
# transition endpoint (ADR-IMM00-OPENAPI §D17).
#
# 5 POST transition endpoint nhận `action: str` (workflow action) → generator D4
# body-bridge sinh property `action` type:string THUẦN. D17 bồi `enum` (list str
# VI-canonical) = UNION các `transitions[].action` đọc ĐỘNG từ workflow fixture .json
# theo doctype mà endpoint đụng (KHÔNG hardcode danh sách action trong generator —
# fixture .json là SSoT). Swagger UI/Redoc TỰ render dropdown khi schema có enum.
#
# Registry NÀY là SSoT DUY NHẤT cho mapping op_tail → doctype(s) workflow:
#   - imm01.transition_workflow đụng CẢ IMM Needs Request + IMM Procurement Plan
#     (_handle dispatch theo doctype của `name`) → list 2 doctype, enum = union
#     sorted-distinct của 2 fixture.
#   - 4 op còn lại đụng 1 doctype → str đơn.
# Op_tail KHÔNG có entry ở đây → generator GIỮ property action plain string (fail-safe).
#
# Fail-safe (KHÔNG raise, KHÔNG fabricate): doctype map nhưng fixture vắng / parse-lỗi /
# 0 transition → `workflow_action_enum_for` trả [] ⟹ generator BỎ enum (plain string).
# Enum chỉ xuất hiện khi resolve được ≥1 action thật trên đĩa.
# ══════════════════════════════════════════════════════════════════════════════
WORKFLOW_ACTION_OVERRIDES: dict[str, str | list[str]] = {
    # imm01.transition_workflow → _handle dispatch theo doctype của `name`: cả Needs
    # Request lẫn Procurement Plan dùng CHUNG endpoint này → union 2 fixture.
    "imm01.transition_workflow": ["IMM Needs Request", "IMM Procurement Plan"],
    "imm02.transition_workflow": "IMM Tech Spec",
    "imm03.transition_eval_workflow": "IMM Vendor Evaluation",
    "imm03.transition_decision_workflow": "IMM Procurement Decision",
    "imm04.transition_state": "Asset Commissioning",
}

# Thư mục fixture workflow: <app-repo>/assetcore/assetcore/workflow/*.json.
# `__file__` = .../assetcore/api/openapi_overrides.py → parents[2] = app-repo root.
_WORKFLOW_FIXTURE_DIR = (
    pathlib.Path(__file__).resolve().parents[2] / "assetcore" / "assetcore" / "workflow"
)

# Cache {doctype: sorted-distinct action list} — quét fixture 1 lần/process (KHÔNG re-scan
# mỗi generate_spec). None entry = doctype chưa resolve / fixture vắng (đếm lại = []).
_WORKFLOW_ACTION_CACHE: dict[str, list[str]] = {}


def workflow_doctypes_for(op_tail: str) -> list[str]:
    """DocType(s) workflow map cho `op_tail` — chuẩn hoá str→[str], `[]` nếu chưa map (D17).

    SSoT mapping = `WORKFLOW_ACTION_OVERRIDES`. Chuẩn hoá giá trị str đơn thành list 1 phần tử
    (caller xử lý đồng nhất). Giá trị list → copy ra list mới. op_tail KHÔNG trong registry →
    trả `[]` (fail-safe — caller giữ property 'action' plain string, KHÔNG enum).

    Args:
        op_tail: operationId-tail '<module>.<fn>' (vd 'imm01.transition_workflow').

    Returns:
        list[str] tên DocType (1 hoặc nhiều), hoặc `[]` nếu op_tail chưa map.
    """
    value = WORKFLOW_ACTION_OVERRIDES.get(op_tail)
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)


def _scan_actions_for_doctype(doctype: str) -> list[str]:
    """Quét MỌI fixture .json trong workflow dir → sorted-distinct actions cho `doctype`.

    Khớp fixture theo `document_type == doctype` (KHÔNG đoán theo tên file → bất biến quy ước
    đặt tên fixture). Gom `transitions[].action` thành tập, sort distinct. 1 doctype có thể nằm
    ở >1 fixture (vd nhiều workflow cùng DocType) → union hết.

    Fail-safe (KHÔNG raise): dir vắng / file parse-lỗi / thiếu key → BỎ QUA file đó (continue);
    0 fixture khớp / 0 transition → trả [] (caller OMIT enum). KHÔNG fabricate action.

    Returns:
        list[str] sorted-distinct các action y nguyên fixture (VI-canonical), hoặc [] khi vắng.
    """
    actions: set[str] = set()
    try:
        files = sorted(_WORKFLOW_FIXTURE_DIR.glob("*.json"))
    except OSError:  # pragma: no cover — dir không truy cập được.
        return []
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):  # pragma: no cover — file lỗi → bỏ qua, KHÔNG vỡ.
            continue
        if not isinstance(data, dict) or data.get("document_type") != doctype:
            continue
        for t in data.get("transitions", []) or []:
            action = t.get("action") if isinstance(t, dict) else None
            if isinstance(action, str) and action.strip():
                actions.add(action)
    return sorted(actions)


def _actions_for_doctype(doctype: str) -> list[str]:
    """Sorted-distinct actions cho 1 doctype (cached). [] khi fixture vắng/0 transition."""
    if doctype not in _WORKFLOW_ACTION_CACHE:
        _WORKFLOW_ACTION_CACHE[doctype] = _scan_actions_for_doctype(doctype)
    return _WORKFLOW_ACTION_CACHE[doctype]


def workflow_action_enum_for(op_tail: str) -> list[str]:
    """Enum VI-canonical (sorted-distinct) cho body-param 'action' của op `op_tail` (D17).

    Tra `WORKFLOW_ACTION_OVERRIDES[op_tail]` → 1 hoặc nhiều doctype → đọc ĐỘNG fixture .json
    (qua `_actions_for_doctype`), UNION các action, sort distinct. Đây là nguồn duy nhất generator
    gọi để bồi enum vào schema con của property 'action'.

    Fail-safe (KHÔNG raise, KHÔNG fabricate):
      - op_tail KHÔNG có entry → trả [] (generator GIỮ plain string, KHÔNG enum).
      - doctype map nhưng fixture vắng / parse-lỗi / 0 transition → trả [] (generator BỎ enum).
    Enum chỉ non-empty khi resolve được ≥1 action thật trên đĩa.

    Args:
        op_tail: operationId-tail '<module>.<fn>' (vd 'imm01.transition_workflow').

    Returns:
        list[str] sorted-distinct (VI y nguyên fixture), hoặc [] (unmapped / fixture vắng).
    """
    doctypes = workflow_doctypes_for(op_tail)
    if not doctypes:
        return []
    # Union sorted-distinct qua pure helper `openapi._workflow_actions_for` (tầng generator —
    # Task BE §D17). LAZY-import api.openapi để tránh import vòng (api.openapi import module này
    # ở top). `_actions_for_doctype` (per-doctype cached scanner) VẪN là SSoT đọc đĩa.
    from assetcore.api import openapi as _oas  # lazy — chống import vòng.

    return _oas._workflow_actions_for(doctypes)


# ══════════════════════════════════════════════════════════════════════════════
# D6 ENRICH (Phase A6) — bám ADR-IMM00-OPENAPI §D6 (E0-E6).
#
# Nguồn DUY NHẤT chứa metadata enrich (summary/description/tags/examples) cho 3 module
# trọng yếu imm00/04/12. Generator (`openapi._enrich_operation`) DẪN XUẤT từ đây — KHÔNG
# hardcode chuỗi trong openapi.py. Thêm/xoá entry → spec phản ánh ngay (mutation có răng).
#
# 2 lớp:
#   (1) `OPERATION_META` — entry CURATED tay cho op ưu tiên (request/response/error VI sạch).
#   (2) `derive_*` — fallback DẪN XUẤT (humanize fn_name → VI) cho op imm00/04/12 CHƯA curate,
#       để đảm bảo E0/đo-1 "MỌI op 3 module có summary>0 + description>0" mà KHÔNG cần
#       liệt kê tay từng op (62 op rỗng-cả-2). Lexicon verb/entity là dữ-liệu, không chuỗi
#       rải trong generator. op-tail KHÔNG thuộc 3 module → không enrich (None).
#
# E2 lưu ý: giá trị Select trong `examples.request` = giá trị CANONICAL của DocType (hợp đồng
# API thật, vd severity:"Critical", incident_type:"Failure") — KHÔNG phải status-pill UI, KHÔNG
# bị quy tắc no-EN (chỉ áp lên ERROR message E4). Toàn bộ ERROR message lấy hằng VI BE thật,
# sạch: KHÔNG raw cap token ('corrective.create'), KHÔNG EN-status, KHÔNG qr_token/email/serial.
# ══════════════════════════════════════════════════════════════════════════════
D6_MODULES: frozenset[str] = frozenset({"imm00", "imm04", "imm09", "imm12"})

# Lexicon verb-prefix fn_name → động từ tiếng Việt (E0 fallback derive — DỮ LIỆU, không chuỗi
# rải trong generator). Mọi prefix trong 3 module phải có entry; thiếu → fallback "Thao tác".
_VERB_VI: dict[str, str] = {
    "list": "Liệt kê",
    "get": "Lấy thông tin",
    "create": "Tạo",
    "update": "Cập nhật",
    "delete": "Xoá",
    "submit": "Gửi duyệt",
    "resolve": "Xử lý",
    "close": "Đóng",
    "trigger": "Kích hoạt",
    "approve": "Phê duyệt",
    "reject": "Từ chối",
    "receive": "Tiếp nhận",
    "generate": "Sinh",
    "report": "Báo cáo",
    "regenerate": "Tạo lại",
    "transition": "Chuyển trạng thái",
    "upload": "Tải lên",
    "compute": "Tính toán",
    "cancel": "Huỷ",
    "mark": "Đánh dấu",
    "validate": "Kiểm tra",
    "verify": "Xác minh",
    "open": "Mở",
    "preview": "Xem trước",
    "run": "Chạy",
    "bulk": "Hàng loạt",
    "search": "Tìm kiếm",
    "check": "Kiểm tra",
    "save": "Lưu",
    "assign": "Gán",
    "request": "Yêu cầu",
    "confirm": "Xác nhận",
    "clear": "Gỡ",
    "retry": "Thử lại",
    "acknowledge": "Tiếp nhận",
    "start": "Bắt đầu",
    "resolve_incident": "Xử lý",
}

# Nhãn module (cho description fallback + tags + D9 tag-description). Khớp ADR §D6/§D9
# (tag = "IMM-XX"). 3 module enrich (imm00/04/12) + 11 imm-module khác (D9: tag NAME chuyển
# từ raw-slug → "IMM-XX" ⟹ nhánh "IMM-" trong tag_description_for cần đủ 14 key VI). Đây là
# SSoT VI-description cho MỌI tag imm-named — tag_description_for tra qua nhánh "IMM-".
_MODULE_LABEL_VI: dict[str, str] = {
    "imm00": "Nền tảng tài sản (IMM-00)",
    "imm01": "Nhu cầu & kế hoạch mua sắm (IMM-01)",
    "imm02": "Yêu cầu kỹ thuật (IMM-02)",
    "imm03": "Đánh giá nhà cung cấp & quyết định mua (IMM-03)",
    "imm04": "Lắp đặt & nghiệm thu (IMM-04)",
    "imm05": "Kho tài liệu thiết bị (IMM-05)",
    "imm06": "Đào tạo & chuyển giao (IMM-06)",
    "imm08": "Bảo trì định kỳ (IMM-08)",
    "imm09": "Sửa chữa khắc phục (IMM-09)",
    "imm10": "Thu hồi & cảnh báo an toàn thiết bị (IMM-10)",
    "imm11": "Hiệu chuẩn (IMM-11)",
    "imm12": "Sự cố & khắc phục (IMM-12)",
    "imm14": "Thanh lý & kết thúc vòng đời (IMM-14)",
    "imm15": "Phụ tùng & tồn kho (IMM-15)",
    "imm16": "Tuân thủ & dấu vết kiểm toán (IMM-16)",
}

# ══════════════════════════════════════════════════════════════════════════════
# D9-TAGS — CANONICALIZE operation tags qua 1 SSoT map module→tag (ADR §D9-TAGS).
#
# Trước D9: tag NAME ở operation = raw lowercase module-slug ('imm01'..'imm16','auth',
# 'dashboard'…) cho 20/23 module → LEAK slug nội bộ ra public API doc + Swagger UI nhóm
# endpoint bằng tên-file thường. D9 chuẩn hoá TÊN tag (NAME) qua `canonical_tag` (SSoT DUY
# NHẤT). Generator (`openapi.py:_build_operation`) ĐỌC helper này — KHÔNG dùng mod_short.
#
# Quy tắc (T1):
#   - 13 module imm-named (immXX có endpoint) → "IMM-XX" uppercase (`f"IMM-{slug[-2:]}"`).
#     DẪN XUẤT bằng quy tắc ⟹ KHỚP `enrich_meta_for` (imm00/04/12 trả CÙNG "IMM-XX" ⟹
#     idempotent: KHÔNG double-tag, KHÔNG đổi enriched_count).
#   - 10 cross-cut + openapi → domain-tag VI canonical (`_CROSSCUT_TAG_MAP`, 11 value).
#   - module CHƯA-map (cross-cut mới) → raise KeyError (fail-fast T4 — KHÔNG fallback raw-slug
#     im lặng → no silent leak; guard test bắt thêm-module-mới).
# ══════════════════════════════════════════════════════════════════════════════
_IMM_SLUG_RE = re.compile(r"imm[0-9]{2}")

# Cross-cut + openapi (không mã IMM) → TÊN tag VI canonical (SSoT NAME — cột 4 D9-MAP).
_CROSSCUT_TAG_MAP: dict[str, str] = {
    "auth": "Xác thực",
    "connections": "Bản ghi liên quan",
    "dashboard": "Bảng điều khiển",
    "files": "Tệp đính kèm",
    "import_data": "Nhập liệu",
    "inventory": "Kho",
    "layout": "Bố cục",
    "notifications": "Thông báo",
    "purchase": "Mua sắm",
    "user": "Người dùng",
    "openapi": "Tài liệu API",
}


def canonical_tag(module_short: str) -> str:
    """Tag canonical (SSoT DUY NHẤT) cho 1 module-file (D9-TAGS T1).

    - imm-named (`immXX`) → "IMM-XX" uppercase (`f"IMM-{slug[-2:]}"`). KHỚP `enrich_meta_for`
      cho imm00/04/12 ⟹ idempotent (no double-tag, enriched_count bất biến).
    - cross-cut/openapi (`_CROSSCUT_TAG_MAP`) → domain-tag VI canonical.
    - module CHƯA-map → raise KeyError (fail-fast T4 — KHÔNG fallback raw-slug, no silent leak).

    Args:
        module_short: tên ngắn module-file (vd 'imm00', 'auth', 'inventory').

    Returns:
        Tên tag canonical ('IMM-XX' hoặc domain-tag VI).

    Raises:
        KeyError: module cross-cut chưa khai trong `_CROSSCUT_TAG_MAP` (no silent raw-slug).
    """
    if _IMM_SLUG_RE.fullmatch(module_short):
        return f"IMM-{module_short[-2:]}"
    try:
        return _CROSSCUT_TAG_MAP[module_short]
    except KeyError:
        raise KeyError(
            f"Module '{module_short}' chưa map canonical tag — thêm vào "
            "_CROSSCUT_TAG_MAP (D9-TAGS, no silent raw-slug leak)."
        ) from None


# ── D8/D9 root tags[] — SSoT mô tả VI per CANONICAL tag (Swagger UI nhóm endpoint kèm mô tả) ─
# Sau D9, tag NAME ở operation = tập canonical (13 "IMM-XX" + 11 domain-VI). `tag_description_for`
# phủ CẢ 2 dạng để KHÔNG tag mồ côi (mọi tag dùng → có entry mô tả VI non-empty).
#
# 13 tag "IMM-XX" DẪN XUẤT từ `_MODULE_LABEL_VI` (SSoT chung D6 — KHÔNG khai lại chuỗi). 11 tag
# domain-VI cross-cut keyed-by-CANONICAL-NAME (== value `_CROSSCUT_TAG_MAP`). Tag lạ → fallback
# an toàn VI (KHÔNG vỡ, KHÔNG leak raw key) qua `_TAG_FALLBACK_VI`.
_TAG_LABEL_VI: dict[str, str] = {
    # Cross-cut / nền tảng — KEY = canonical tag NAME (== value _CROSSCUT_TAG_MAP), KHÔNG slug.
    "Xác thực": "Xác thực & tài khoản người dùng",
    "Bản ghi liên quan": "Bản ghi liên quan giữa các hồ sơ (đồ thị liên kết)",
    "Bảng điều khiển": "Bảng điều khiển & chỉ số",
    "Nhập liệu": "Nhập dữ liệu hàng loạt",
    "Kho": "Kho & vật tư (nền tảng)",
    "Bố cục": "Bố cục & phiên người dùng",
    "Thông báo": "Thông báo & cảnh báo",
    "Mua sắm": "Mua hàng & đơn đặt hàng",
    "Người dùng": "Quản trị người dùng & phân quyền",
    "Tài liệu API": "Tài liệu OpenAPI (tự sinh)",
    "Tệp đính kèm": "Tệp đính kèm & tải lên tài liệu",
}
_TAG_FALLBACK_VI = "Nhóm chức năng AssetCore"

# ══════════════════════════════════════════════════════════════════════════════
# D15/D16 — externalDocs doc-path map (ADR §D15 T3/T4, host SSoT đổi ở §D16). SSoT relative doc-path per
# CANONICAL tag (cạnh `canonical_tag`/`tag_description_for`). THUẦN tĩnh (KHÔNG DB,
# KHÔNG get_url — host ghép ở generator qua `_doc_url`). Mọi path là segment hợp lệ
# `docs/imm-XX/README.md` (KHÔNG host, KHÔNG leading-slash).
#
#   - root/landing doc = `_DOC_ROOT_PATH` (README IMM-00 nền tảng — entry-point tài liệu).
#   - 13 tag IMM-XX (có-endpoint) → `docs/imm-XX/README.md` DẪN XUẤT mã module
#     ('IMM-00'→'imm-00', 'IMM-16'→'imm-16'). 14/14 README imm00..imm16 tồn tại @source.
#   - 9 tag cross-cut (KHÔNG module docs/imm-XX riêng) → `_DOC_ROOT_PATH` (doc chung).
#   - tag lạ → fallback `_DOC_ROOT_PATH` (KHÔNG vỡ, KHÔNG leak raw key).
# ══════════════════════════════════════════════════════════════════════════════
_DOC_ROOT_PATH = "docs/imm-00/README.md"  # IMM-00 = foundation doc (landing tài liệu).
# Tag canonical NAME → mã 2 chữ số (vd 'IMM-04' → '04'). KHÔNG khớp → cross-cut/lạ.
_IMM_CANONICAL_TAG_RE = re.compile(r"^IMM-([0-9]{2})$")


def tag_doc_path(tag: str) -> str:
    """Relative doc-path (SSoT D15 T3/T4) cho 1 tag canonical — luôn NON-EMPTY.

    - 'IMM-XX' → `f"docs/imm-{NN}/README.md"` (mã lowercase, vd 'IMM-04'→'docs/imm-04/README.md').
    - cross-cut/openapi (domain-VI tag) → `_DOC_ROOT_PATH` (doc chung README IMM-00 nền tảng).
    - tag lạ → `_DOC_ROOT_PATH` (fallback an toàn — KHÔNG vỡ, KHÔNG leak raw key).

    THUẦN: chỉ ghép chuỗi path (KHÔNG host/get_url/DB). Generator ghép host qua `_doc_url`.

    Args:
        tag: tên tag canonical y như xuất hiện trong operation['tags'] / root tags[].name.

    Returns:
        Relative path segment 'docs/imm-XX/README.md' (NON-EMPTY, đúng pattern).
    """
    m = _IMM_CANONICAL_TAG_RE.match(tag)
    if m:
        return f"docs/imm-{m.group(1)}/README.md"
    return _DOC_ROOT_PATH


def tag_external_desc_for(tag: str) -> str:
    """Mô tả VI (SSoT D15) cho per-tag externalDocs — luôn NON-EMPTY, KHÔNG leak slug raw.

    - 'IMM-XX' → `f"Tài liệu module {tag}"` (vd 'Tài liệu module IMM-00').
    - cross-cut → `f"Tài liệu chung — {tag}"` (vd 'Tài liệu chung — Xác thực').

    Args:
        tag: tên tag canonical ('IMM-XX' hoặc domain-VI cross-cut).

    Returns:
        Chuỗi mô tả VI non-empty (chứa tên tag — KHÔNG raw lowercase slug).
    """
    if _IMM_CANONICAL_TAG_RE.match(tag):
        return f"Tài liệu module {tag}"
    return f"Tài liệu chung — {tag}"


def tag_description_for(tag: str) -> str:
    """Mô tả VI (SSoT) cho 1 tag root-level CANONICAL — DẪN XUẤT, KHÔNG hardcode ở generator.

    Phủ CẢ 2 dạng tag canonical (D9):
      - "IMM-XX" (13 module imm-named) → `_MODULE_LABEL_VI['immXX']` (SSoT chung D6 — KHÔNG
        khai lại chuỗi). 'IMM-00'→'Nền tảng tài sản (IMM-00)', 'IMM-01'→'Nhu cầu...', v.v.
      - domain-tag VI cross-cut ('Xác thực','Kho','Tài liệu API'…) → `_TAG_LABEL_VI[tag]`.
    Tag lạ (không khớp dạng nào) → `_TAG_FALLBACK_VI` (VI an toàn, KHÔNG vỡ, KHÔNG leak
    raw key tiếng Anh). Luôn trả chuỗi VI NON-EMPTY (acceptance: mọi tag entry description>0).

    Args:
        tag: tên tag CANONICAL y như xuất hiện trong operation['tags'].

    Returns:
        Chuỗi mô tả tiếng Việt non-empty.
    """
    # Dạng "IMM-XX" → tra _MODULE_LABEL_VI qua khóa 'immXX' (SSoT D6 — đủ 14 key sau D9).
    if tag.upper().startswith("IMM-"):
        mod_key = "imm" + tag.split("-", 1)[1].strip()
        label = _MODULE_LABEL_VI.get(mod_key.lower())
        if label:
            return label
    # Dạng domain-tag VI cross-cut → nhãn curated keyed-by-canonical-NAME.
    if tag in _TAG_LABEL_VI:
        return _TAG_LABEL_VI[tag]
    return _TAG_FALLBACK_VI


def _humanize_tail(fn_name: str) -> tuple[str, str]:
    """(verb_vi, object_vi) từ fn_name: prefix → động từ VI, phần còn lại → cụm danh từ thô."""
    parts = fn_name.split("_", 1)
    verb = parts[0]
    rest = parts[1] if len(parts) > 1 else ""
    verb_vi = _VERB_VI.get(verb, "Thao tác")
    object_vi = rest.replace("_", " ").strip()
    return verb_vi, object_vi


def derive_summary(op_tail: str) -> str:
    """Summary DẪN XUẤT (humanize) cho op imm00/04/12 CHƯA curate — luôn non-empty (E0)."""
    _, fn_name = op_tail.split(".", 1)
    verb_vi, object_vi = _humanize_tail(fn_name)
    return f"{verb_vi} {object_vi}".strip() if object_vi else verb_vi


def derive_description(op_tail: str, summary: str) -> str:
    """Description DẪN XUẤT — luôn non-empty (E0). Ghép summary + nhãn module + operationId."""
    mod = op_tail.split(".", 1)[0]
    label = _MODULE_LABEL_VI.get(mod, mod)
    return (
        f"{summary}. Thuộc module {label}. "
        f"Endpoint: assetcore.api.{op_tail} (xem 05_API_Specification.md)."
    )


def enrich_meta_for(op_tail: str) -> dict | None:
    """Metadata enrich hiệu lực cho `op_tail`, hoặc None nếu ngoài 3 module (fail-safe).

    Ưu tiên entry CURATED (`OPERATION_META`); nếu op thuộc 3 module nhưng CHƯA curate →
    fallback DẪN XUẤT (summary/description humanize) bảo đảm E0 (mọi op 3 module có
    summary>0 + description>0). op-tail ngoài 3 module → None (KHÔNG ép enrich — lô 4+ roadmap).

    Trả dict GỘP {summary, description, tags, examples}: curated keys override derived;
    summary/description luôn non-empty.
    """
    mod = op_tail.split(".", 1)[0]
    if mod not in D6_MODULES:
        return None
    curated = OPERATION_META.get(op_tail) or {}
    summary = curated.get("summary") or derive_summary(op_tail)
    description = curated.get("description") or derive_description(op_tail, summary)
    return {
        "summary": summary,
        "description": description,
        "tags": curated.get("tags") or [f"IMM-{mod[-2:]}"],
        "examples": curated.get("examples", {}),
    }


# ── OPERATION_META — entry CURATED tay (op ưu tiên). Op 3 module CHƯA ở đây vẫn được
# fallback derive (xem `enrich_meta_for`). Mọi value Select trong request example =
# canonical DocType (E2). Mọi error message = hằng VI BE thật, sạch (E4). ──────────────
OPERATION_META: dict[str, dict] = {
    # ─────────────────────────── IMM-00 ───────────────────────────
    "imm00.create_asset": {
        "summary": "Tạo tài sản (thiết bị y tế) mới",
        "description": (
            "Đăng ký AC Asset mới vào registry. Sinh QR-token + lifecycle event. "
            "Mã tài sản = định danh (asset_code == name). Bắt buộc nhóm tài sản + tên."
        ),
        "tags": ["IMM-00"],
        "examples": {
            "request": {
                "asset_category": "CAT-0001",
                "asset_name": "Máy siêu âm GE Logiq E10",
            },
            "response": {
                "name": "ACC-ASS-2026-00001",
                "asset_name": "Máy siêu âm GE Logiq E10",
                "lifecycle_status": "Đang hoạt động",
            },
            "errors": {
                "FORBIDDEN": "Bạn không có quyền tạo tài sản",
                "VALIDATION": "Thiếu trường bắt buộc: Tên tài sản",
            },
        },
    },
    "imm00.list_assets": {
        "summary": "Liệt kê tài sản (có phân trang + lọc)",
        "description": (
            "Trả danh sách AC Asset theo bộ lọc + phân trang. Bảo đảm bất biến "
            "count == số dòng trả về (đồng nhất quyền). Mỗi dòng kèm tên đọc được."
        ),
        "tags": ["IMM-00"],
        "examples": {
            "response": {
                "items": [
                    {
                        "name": "ACC-ASS-2026-00001",
                        "asset_name": "Máy siêu âm GE Logiq E10",
                        "lifecycle_status": "Đang hoạt động",
                    }
                ],
                "pagination": {"total": 1, "page": 1, "page_size": 20, "total_pages": 1},
            },
            "errors": {
                "UNAUTHORIZED": "Chưa đăng nhập",
                "FORBIDDEN": "Bạn không có quyền xem danh sách tài sản",
            },
        },
    },
    "imm00.get_asset": {
        "summary": "Lấy chi tiết một tài sản",
        "description": (
            "Trả thông tin đầy đủ của một AC Asset theo mã định danh, kèm trạng thái "
            "vòng đời và tên đọc được. Dùng cho màn chi tiết tài sản."
        ),
        "tags": ["IMM-00"],
        "examples": {
            "response": {
                "name": "ACC-ASS-2026-00001",
                "asset_name": "Máy siêu âm GE Logiq E10",
                "lifecycle_status": "Đang hoạt động",
            },
            "errors": {
                "NOT_FOUND": "Không tìm thấy tài sản",
                "FORBIDDEN": "Bạn không có quyền xem tài sản này",
            },
        },
    },
    "imm00.transition_status": {
        "summary": "Chuyển trạng thái vòng đời tài sản",
        "description": (
            "Chuyển AC Asset sang trạng thái vòng đời mới hợp lệ (sinh lifecycle event "
            "+ audit trail). Chỉ cho phép chuyển tiếp theo đúng máy trạng thái."
        ),
        "tags": ["IMM-00"],
        "examples": {
            "request": {
                "name": "ACC-ASS-2026-00001",
                "to_status": "Ngừng sử dụng",
                "reason": "Hết khấu hao, đề nghị thanh lý",
            },
            "response": {
                "name": "ACC-ASS-2026-00001",
                "lifecycle_status": "Ngừng sử dụng",
            },
            "errors": {
                "BUSINESS_RULE": "Không thể chuyển sang trạng thái này từ trạng thái hiện tại",
                "FORBIDDEN": "Bạn không có quyền chuyển trạng thái tài sản",
            },
        },
    },
    "imm00.mark_label_printed": {
        "summary": "Đánh dấu đã in nhãn QR tài sản",
        "description": (
            "Ghi nhận lô tài sản đã in nhãn QR (tăng số lần in, ghi audit). Giới hạn "
            "số lượng mỗi lô để tránh quá tải."
        ),
        "tags": ["IMM-00"],
        "examples": {
            "request": {"assets": ["ACC-ASS-2026-00001", "ACC-ASS-2026-00002"]},
            "response": {"marked": 2},
            "errors": {
                "PAYLOAD_TOO_LARGE": "Vượt quá số lượng nhãn cho phép mỗi lần in",
                "FORBIDDEN": "Bạn không có quyền in nhãn tài sản",
            },
        },
    },
    "imm00.regenerate_asset_qr_token": {
        "summary": "Tạo lại mã QR cho tài sản",
        "description": (
            "Sinh lại QR-token mới cho tài sản (vô hiệu token cũ, ghi audit). Dùng khi "
            "nhãn cũ bị mất hoặc nghi ngờ lộ."
        ),
        "tags": ["IMM-00"],
        "examples": {
            "request": {"asset": "ACC-ASS-2026-00001"},
            "response": {"asset": "ACC-ASS-2026-00001", "rotated": True},
            "errors": {
                "RATE_LIMITED": "Bạn thao tác quá nhanh, vui lòng thử lại sau",
                "FORBIDDEN": "Bạn không có quyền tạo lại mã QR",
            },
        },
    },
    # ─────────────────────────── IMM-04 ───────────────────────────
    "imm04.create_commissioning": {
        "summary": "Tạo hồ sơ lắp đặt & nghiệm thu",
        "description": (
            "Khởi tạo hồ sơ nghiệm thu thiết bị (Asset Commissioning). Tham số `data` là "
            "chuỗi JSON chứa các trường hồ sơ; server parse rồi tạo bản ghi + lifecycle event."
        ),
        "tags": ["IMM-04"],
        "examples": {
            "request": {
                "data": (
                    '{"device_model": "DM-0001", "location": "LOC-0001", '
                    '"vendor_serial_no": "SN-2026-0001"}'
                )
            },
            "response": {
                "name": "COMM-2026-00001",
                "workflow_state": "Bản nháp",
            },
            "errors": {
                "VALIDATION_ERROR": "Dữ liệu JSON không hợp lệ",
                "FORBIDDEN": "Bạn không có quyền tạo hồ sơ nghiệm thu",
            },
        },
    },
    "imm04.transition_state": {
        "summary": "Chuyển trạng thái hồ sơ nghiệm thu",
        "description": (
            "Thực hiện một hành động workflow trên hồ sơ nghiệm thu (vd nộp duyệt, phê "
            "duyệt). Chỉ cho phép hành động hợp lệ ở trạng thái hiện tại."
        ),
        "tags": ["IMM-04"],
        "examples": {
            "request": {"name": "COMM-2026-00001", "action": "submit"},
            "response": {"name": "COMM-2026-00001", "workflow_state": "Chờ duyệt"},
            "errors": {
                "BUSINESS_RULE": "Hành động không hợp lệ ở trạng thái hiện tại",
                "FORBIDDEN": "Bạn không có quyền thao tác hồ sơ nghiệm thu",
            },
        },
    },
    "imm04.submit_commissioning": {
        "summary": "Nộp hồ sơ nghiệm thu để duyệt",
        "description": (
            "Khoá hồ sơ nghiệm thu và chuyển sang luồng phê duyệt. Yêu cầu các mục bắt "
            "buộc (định danh, checklist) đã hoàn tất."
        ),
        "tags": ["IMM-04"],
        "examples": {
            "request": {"name": "COMM-2026-00001"},
            "response": {"name": "COMM-2026-00001", "workflow_state": "Chờ duyệt"},
            "errors": {
                "BUSINESS_RULE": "Hồ sơ chưa đủ điều kiện để nộp duyệt",
                "FORBIDDEN": "Bạn không có quyền nộp hồ sơ nghiệm thu",
            },
        },
    },
    "imm04.report_doa": {
        "summary": "Báo cáo thiết bị hỏng khi nhận (DOA)",
        "description": (
            "Ghi nhận thiết bị hỏng ngay khi tiếp nhận (Dead On Arrival) trên hồ sơ "
            "nghiệm thu, sinh điểm không phù hợp + lifecycle event để xử lý với nhà cung cấp."
        ),
        "tags": ["IMM-04"],
        "examples": {
            "request": {
                "commissioning": "COMM-2026-00001",
                "description": "Màn hình không lên nguồn khi mở hộp",
            },
            "response": {"commissioning": "COMM-2026-00001", "doa_reported": True},
            "errors": {
                "VALIDATION": "Thiếu mô tả tình trạng hỏng",
                "FORBIDDEN": "Bạn không có quyền báo cáo DOA",
            },
        },
    },
    # ─────────────────────────── IMM-09 ───────────────────────────
    # Source-ground: DocType 'Asset Repair' (@asset_repair.json) — required
    # [asset_ref, failure_description, repair_type, priority]; Select enum canonical
    # repair_type [Corrective,Breakdown,Warranty Repair] · priority [Normal,Urgent,
    # Emergency] · root_cause_category [Mechanical,Electrical,Software,User Error,
    # Wear and Tear,Unknown] · status 9-set. Response shape = service imm09.py thật
    # (create:786 {name,status,sla_target_hours} · assign:804 · close:956 · confirm:992).
    # Error message = hằng VI BE thật (utils/messages.py IMM09_*) đã làm sạch placeholder.
    "imm09.create_repair_work_order": {
        "summary": "Tạo lệnh sửa chữa khắc phục (CM Work Order)",
        "description": (
            "Tạo lệnh sửa chữa Asset Repair cho một thiết bị gặp lỗi. Khởi tạo mục tiêu "
            "SLA theo độ ưu tiên + lifecycle event. Bắt buộc thiết bị, mô tả lỗi, loại "
            "sửa chữa và độ ưu tiên. Một thiết bị chỉ có một lệnh sửa chữa đang mở."
        ),
        "tags": ["IMM-09"],
        "examples": {
            "request": {
                "asset_ref": "ACC-ASS-2026-00001",
                "repair_type": "Corrective",
                "priority": "Urgent",
                "failure_description": "Máy báo lỗi nguồn, không khởi động được",
                "incident_report": "INC-2026-00001",
            },
            "response": {
                "name": "WO-CM-2026-00001",
                "status": "Open",
                "sla_target_hours": 8.0,
            },
            "errors": {
                "FORBIDDEN": "Bạn không có quyền tạo lệnh sửa chữa",
                "VALIDATION": "Thiếu trường bắt buộc: Mô tả lỗi",
                "CONFLICT": "Thiết bị đang có lệnh sửa chữa đang mở",
            },
        },
    },
    "imm09.list_repair_work_orders": {
        "summary": "Liệt kê lệnh sửa chữa (có phân trang + lọc)",
        "description": (
            "Trả danh sách Asset Repair theo bộ lọc + phân trang. Tự áp phạm vi theo "
            "nhà cung cấp (vendor scope) khi người dùng là đối tác. Mỗi dòng kèm tên "
            "thiết bị và trạng thái đọc được."
        ),
        "tags": ["IMM-09"],
        "examples": {
            "response": {
                "data": [
                    {
                        "name": "WO-CM-2026-00001",
                        "asset_name": "Máy siêu âm GE Logiq E10",
                        "repair_type": "Corrective",
                        "priority": "Urgent",
                        "status": "Open",
                    }
                ],
                "pagination": {"total": 1, "page": 1, "page_size": 20, "total_pages": 1},
            },
            "errors": {
                "UNAUTHORIZED": "Chưa đăng nhập",
                "FORBIDDEN": "Bạn không có quyền xem danh sách lệnh sửa chữa",
            },
        },
    },
    "imm09.get_repair_work_order": {
        "summary": "Lấy chi tiết một lệnh sửa chữa",
        "description": (
            "Trả thông tin đầy đủ của một Asset Repair theo mã định danh, kèm thông tin "
            "thiết bị, người phân công và trạng thái xử lý. Dùng cho màn chi tiết lệnh."
        ),
        "tags": ["IMM-09"],
        "examples": {
            "response": {
                "name": "WO-CM-2026-00001",
                "asset_name": "Máy siêu âm GE Logiq E10",
                "repair_type": "Corrective",
                "priority": "Urgent",
                "status": "Assigned",
            },
            "errors": {
                "NOT_FOUND": "Không tìm thấy lệnh sửa chữa",
                "FORBIDDEN": "Bạn không có quyền xem lệnh sửa chữa này",
            },
        },
    },
    "imm09.attach_repair_checklist_photo": {
        "summary": "Đính ảnh bằng chứng cho mục kiểm tra sửa chữa",
        "description": (
            "Đính MỘT ảnh bằng chứng (JPG/PNG, tối đa 10 MB) cho một mục trong danh "
            "mục kiểm tra của lệnh sửa chữa (Asset Repair) — phục vụ hồ sơ thiết bị rủi "
            "ro cao (Class C/D) theo NĐ98. Gửi dạng multipart (trường 'file'); mục xác "
            "định qua chỉ số hàng (checklist_item_idx). Tệp lưu riêng tư; đính thành "
            "công sinh sự kiện vòng đời và ghi nhận đường dẫn ảnh vào mục tương ứng."
        ),
        "tags": ["IMM-09"],
        "examples": {
            "request": {
                "work_order_name": "WO-CM-2026-00001",
                "checklist_item_idx": 1,
            },
            "response": {
                "file_url": "/private/files/anh_bang_chung_muc_1.jpg",
                "file_name": "anh_bang_chung_muc_1.jpg",
                "checklist_item_idx": 1,
            },
            "errors": {
                "NOT_FOUND": "Không tìm thấy lệnh sửa chữa",
                "FORBIDDEN": "Không có quyền đính ảnh cho lệnh sửa chữa này",
                "VALIDATION": "Tệp phải là ảnh JPG hoặc PNG",
            },
        },
    },
    "imm09.assign_technician": {
        "summary": "Phân công kỹ thuật viên sửa chữa",
        "description": (
            "Gán kỹ thuật viên thực hiện cho lệnh sửa chữa (chuyển sang trạng thái đã "
            "phân công), tuỳ chọn điều chỉnh độ ưu tiên. Ghi nhận người phân công + thời "
            "điểm để tính SLA."
        ),
        "tags": ["IMM-09"],
        "examples": {
            "request": {
                "name": "WO-CM-2026-00001",
                "technician": "ktv.tran.a@benhvien.vn",
                "priority": "Urgent",
            },
            "response": {
                "name": "WO-CM-2026-00001",
                "status": "Assigned",
                "assigned_to": "ktv.tran.a@benhvien.vn",
            },
            "errors": {
                "FORBIDDEN": "Bạn không có quyền phân công lệnh sửa chữa",
                "NOT_FOUND": "Không tìm thấy lệnh sửa chữa",
                "CONFLICT": "Không thể thực hiện khi lệnh sửa chữa đang ở trạng thái hiện tại",
            },
        },
    },
    "imm09.close_work_order": {
        "summary": "Hoàn tất & đóng lệnh sửa chữa",
        "description": (
            "Ghi nhận kết quả sửa chữa và đưa lệnh sang chờ nghiệm thu. Yêu cầu tóm tắt "
            "sửa chữa, nguyên nhân gốc và tên người nghiệm thu cấp khoa. Checklist phải "
            "hoàn tất; nếu cập nhật firmware cần có yêu cầu đổi firmware được duyệt."
        ),
        "tags": ["IMM-09"],
        "examples": {
            "request": {
                "name": "WO-CM-2026-00001",
                "repair_summary": "Thay bộ nguồn, chạy thử ổn định 30 phút",
                "root_cause_category": "Electrical",
                "dept_head_name": "Trưởng khoa Chẩn đoán hình ảnh",
            },
            "response": {
                "name": "WO-CM-2026-00001",
                "status": "Pending Inspection",
                "mttr_hours": 6.5,
                "sla_breached": False,
                # CR-13b: trạng thái LIVE asset (SSoT) — happy → 'Under Repair'
                # (asset chưa reactivate tới confirm_inspection).
                "asset_status": "Under Repair",
            },
            "errors": {
                "FORBIDDEN": "Bạn không có quyền đóng lệnh sửa chữa",
                "VALIDATION_ERROR": "Cần nhập tên trưởng khoa/phòng nghiệm thu khi đóng lệnh hoàn thành",
                "BUSINESS_RULE": "Còn mục kiểm tra trong checklist chưa điền kết quả",
            },
        },
    },
    "imm09.confirm_inspection": {
        "summary": "Nghiệm thu sau sửa chữa",
        "description": (
            "Xác nhận nghiệm thu lệnh sửa chữa (chuyển từ chờ nghiệm thu sang hoàn thành). "
            "Tính MTTR/SLA, đưa thiết bị trở lại hoạt động, kích hoạt hiệu chuẩn lại nếu "
            "cần. Đây là bước kiểm soát chất lượng cuối, yêu cầu quyền phê duyệt cấp khoa/QA."
        ),
        "tags": ["IMM-09"],
        "examples": {
            "request": {"name": "WO-CM-2026-00001"},
            "response": {
                "name": "WO-CM-2026-00001",
                "status": "Completed",
                "mttr_hours": 6.5,
                "sla_breached": False,
                # CR-13a: trạng thái LIVE asset (SSoT) SAU nghiệm thu — happy →
                # 'Active' (complete_repair restore); đối xứng override
                # close_work_order. Edge (governance hold) giữ prev (BR-09-09).
                "asset_status": "Active",
            },
            "errors": {
                "FORBIDDEN": "Bạn không có quyền nghiệm thu lệnh sửa chữa",
                "NOT_FOUND": "Không tìm thấy lệnh sửa chữa",
                "CONFLICT": "Không thể thực hiện khi lệnh sửa chữa đang ở trạng thái hiện tại",
            },
        },
    },
    # ── 7 op còn lại của IMM-09 — curated để phủ enrich 13/13 (D6-IMM09-ENRICH).
    # Response shape = service imm09.py thật (submit_diagnosis:828 · start_repair:847 ·
    # request_spare_parts:896 · get_kpis:1075 · get_asset_history:1098 · search_spare_parts:1115
    # · get_mttr_report:1149). Error message = hằng VI BE thật (utils/messages.py IMM09_*,
    # template đã thay {placeholder} bằng giá trị mẫu — KHÔNG leak raw token). Mọi giá trị
    # Select = canonical 'Asset Repair' (E2: status 9-set, priority/root_cause canonical).
    "imm09.submit_diagnosis": {
        "summary": "Gửi kết quả chẩn đoán lỗi",
        "description": (
            "Ghi nhận kết quả chẩn đoán cho lệnh sửa chữa. Nếu cần linh kiện (needs_parts=1) "
            "lệnh chuyển sang chờ vật tư (đồng hồ SLA tạm dừng); nếu không chuyển thẳng sang "
            "đang sửa chữa. Áp dụng khi lệnh đang ở trạng thái Đã phân công hoặc Đang chẩn đoán."
        ),
        "tags": ["IMM-09"],
        "examples": {
            "request": {
                "name": "WO-CM-2026-00001",
                "diagnosis_notes": "Xác định hỏng bo nguồn, cần thay module công suất",
                "needs_parts": 1,
            },
            "response": {"name": "WO-CM-2026-00001", "status": "Pending Parts"},
            "errors": {
                "FORBIDDEN": "Bạn không có quyền chẩn đoán lệnh sửa chữa",
                "NOT_FOUND": "Không tìm thấy Asset Repair 'WO-CM-2026-00001'.",
                "CONFLICT": "Không thể thực hiện khi lệnh sửa chữa đang ở trạng thái 'In Repair'.",
            },
        },
    },
    "imm09.start_repair": {
        "summary": "Bắt đầu thực hiện sửa chữa",
        "description": (
            "Chuyển lệnh sửa chữa sang trạng thái đang sửa chữa. Nếu lệnh đang chờ vật tư, "
            "khoảng thời gian chờ được chốt lại và đồng hồ SLA tiếp tục chạy. Áp dụng khi lệnh "
            "đang ở Đã phân công, Đang chẩn đoán hoặc Chờ vật tư."
        ),
        "tags": ["IMM-09"],
        "examples": {
            "request": {"name": "WO-CM-2026-00001"},
            "response": {"name": "WO-CM-2026-00001", "status": "In Repair"},
            "errors": {
                "FORBIDDEN": "Bạn không có quyền bắt đầu sửa chữa",
                "NOT_FOUND": "Không tìm thấy Asset Repair 'WO-CM-2026-00001'.",
                "CONFLICT": "Không thể thực hiện khi lệnh sửa chữa đang ở trạng thái 'Completed'.",
            },
        },
    },
    "imm09.request_spare_parts": {
        "summary": "Yêu cầu cấp linh kiện thay thế",
        "description": (
            "Gắn phiếu xuất kho cho các linh kiện đã dùng và tạo yêu cầu cấp phát về kho "
            "(IMM-15). Nếu lệnh đang chờ vật tư, khi nhận đủ linh kiện lệnh chuyển sang đang "
            "sửa chữa và đồng hồ SLA tiếp tục."
        ),
        "tags": ["IMM-09"],
        "examples": {
            "request": {
                "name": "WO-CM-2026-00001",
                "parts": [
                    {"spare_part": "SP-PSU-500W", "qty": 1, "item_code": "SP-PSU-500W"}
                ],
            },
            "response": {
                "name": "WO-CM-2026-00001",
                "status": "In Repair",
                "updated": 1,
                "allocation": "ALLOC-2026-00007",
            },
            "errors": {
                "FORBIDDEN": "Bạn không có quyền yêu cầu linh kiện",
                "NOT_FOUND": "Không tìm thấy Asset Repair 'WO-CM-2026-00001'.",
                "VALIDATION": "Phiếu xuất kho 'STE-2026-0001' không tồn tại.",
            },
        },
    },
    "imm09.get_repair_kpis": {
        "summary": "Chỉ số bảo trì sửa chữa (KPI) theo tháng",
        "description": (
            "Trả KPI sửa chữa của một tháng: số lệnh hoàn thành, MTTR trung bình, tỷ lệ đạt "
            "SLA, số lỗi lặp, số lệnh đang mở, kèm phân rã theo nhóm nguyên nhân gốc. Mặc định "
            "lấy tháng hiện tại nếu không truyền year/month."
        ),
        "tags": ["IMM-09"],
        "examples": {
            "request": {"year": "2026", "month": "6"},
            "response": {
                "kpis": {
                    "total_completed": 12,
                    "mttr_avg_hours": 6.4,
                    "sla_compliance_pct": 91.7,
                    "repeat_failure_count": 1,
                    "open_wos": 3,
                },
                "root_cause_breakdown": [
                    {"category": "Electrical", "count": 5},
                    {"category": "Mechanical", "count": 4},
                ],
            },
            "errors": {
                "UNAUTHORIZED": "Chưa đăng nhập",
                "FORBIDDEN": "Bạn không có quyền xem chỉ số sửa chữa",
            },
        },
    },
    "imm09.get_asset_repair_history": {
        "summary": "Lịch sử sửa chữa của một thiết bị",
        "description": (
            "Trả danh sách các lệnh sửa chữa đã hoàn tất của một thiết bị (mới nhất trước), "
            "kèm MTTR, kết quả SLA, nguyên nhân gốc và tóm tắt sửa chữa. Dùng cho hồ sơ lý "
            "lịch thiết bị và phân tích lỗi lặp."
        ),
        "tags": ["IMM-09"],
        "examples": {
            "request": {"asset_ref": "ACC-ASS-2026-00001", "limit": "10"},
            "response": {
                "asset_ref": "ACC-ASS-2026-00001",
                "history": [
                    {
                        "name": "WO-CM-2026-00001",
                        "repair_type": "Corrective",
                        "priority": "Urgent",
                        "mttr_hours": 6.5,
                        "sla_breached": False,
                        "root_cause_category": "Electrical",
                        "repair_summary": "Thay bộ nguồn, chạy thử ổn định 30 phút",
                    }
                ],
            },
            "errors": {
                "UNAUTHORIZED": "Chưa đăng nhập",
                "FORBIDDEN": "Bạn không có quyền xem lịch sử sửa chữa",
            },
        },
    },
    "imm09.search_spare_parts": {
        "summary": "Tìm linh kiện thay thế theo tên/mã",
        "description": (
            "Tìm linh kiện trong danh mục theo tên hoặc mã nhà sản xuất (tối thiểu 2 ký tự). "
            "Trả các dòng linh kiện sẵn sàng để thêm vào lệnh sửa chữa, kèm đơn giá ước tính. "
            "Phục vụ ô tìm kiếm khi lập danh sách vật tư sử dụng."
        ),
        "tags": ["IMM-09"],
        "examples": {
            "request": {"query": "nguồn", "limit": "10"},
            "response": [
                {
                    "item_code": "SP-PSU-500W",
                    "item_name": "Bộ nguồn 500W",
                    "manufacturer_part_no": "SP-PSU-500W",
                    "qty": 1,
                    "uom": "Cái",
                    "unit_cost": 1200000.0,
                    "total_cost": 1200000.0,
                }
            ],
            "errors": {
                "UNAUTHORIZED": "Chưa đăng nhập",
                "FORBIDDEN": "Bạn không có quyền tìm linh kiện",
            },
        },
    },
    "imm09.get_mttr_report": {
        "summary": "Báo cáo MTTR & tồn đọng sửa chữa",
        "description": (
            "Trả báo cáo MTTR của một tháng: thời gian sửa trung bình, tỷ lệ sửa đúng lần đầu, "
            "số lệnh tồn đọng, chi phí linh kiện bình quân mỗi lệnh và xu hướng MTTR. Mặc định "
            "lấy tháng hiện tại nếu không truyền year/month."
        ),
        "tags": ["IMM-09"],
        "examples": {
            "request": {"year": "2026", "month": "6"},
            "response": {
                "mttr_avg": 6.4,
                "first_fix_rate": 91.7,
                "backlog_count": 3,
                "cost_per_repair": 1500000.0,
                "mttr_trend": [],
                "backlog_by_dept": [],
            },
            "errors": {
                "UNAUTHORIZED": "Chưa đăng nhập",
                "FORBIDDEN": "Bạn không có quyền xem báo cáo MTTR",
            },
        },
    },
    # ─────────────────────────── IMM-12 ───────────────────────────
    "imm12.report_incident": {
        "summary": "Báo cáo sự cố thiết bị",
        "description": (
            "Tạo phiếu báo cáo sự cố cho một tài sản (NĐ98 Điều 67). Khởi tạo SLA phản "
            "hồi/khắc phục + lifecycle event. Phục vụ cả luồng quét QR và nhập thủ công."
        ),
        "tags": ["IMM-12"],
        "examples": {
            "request": {
                "asset": "ACC-ASS-2026-00001",
                "incident_type": "Failure",
                "severity": "Critical",
                "description": "Máy ngừng hoạt động giữa ca chụp, báo lỗi nguồn",
                "source": "manual",
            },
            "response": {
                "name": "INC-2026-00001",
                "status": "Mới tiếp nhận",
                "severity": "Critical",
            },
            "errors": {
                "FORBIDDEN": "Không có quyền thực hiện hành động này",
                "UNAUTHORIZED": "Chưa đăng nhập",
                "VALIDATION": "Thiếu trường bắt buộc: Mô tả sự cố",
            },
        },
    },
    "imm12.acknowledge_incident": {
        "summary": "Tiếp nhận xử lý sự cố",
        "description": (
            "Kỹ thuật viên tiếp nhận phiếu sự cố (dừng đồng hồ SLA phản hồi), tuỳ chọn "
            "gán người xử lý + ghi chú. Chuyển trạng thái sang đang xử lý."
        ),
        "tags": ["IMM-12"],
        "examples": {
            "request": {
                "name": "INC-2026-00001",
                "assigned_to": "Kỹ thuật viên Trần Văn A",
                "notes": "Đã liên hệ khoa, chuẩn bị xuống kiểm tra",
            },
            "response": {"name": "INC-2026-00001", "status": "Đang xử lý"},
            "errors": {
                "FORBIDDEN": "Không có quyền thực hiện hành động này",
                "NOT_FOUND": "Không tìm thấy phiếu sự cố",
            },
        },
    },
    "imm12.resolve_incident": {
        "summary": "Đánh dấu đã khắc phục sự cố",
        "description": (
            "Ghi nhận sự cố đã được khắc phục (dừng đồng hồ SLA khắc phục) kèm ghi chú "
            "xử lý + nguyên nhân. Chuyển sang chờ xác minh đóng phiếu."
        ),
        "tags": ["IMM-12"],
        "examples": {
            "request": {
                "name": "INC-2026-00001",
                "resolution_notes": "Thay bộ nguồn, chạy thử ổn định 30 phút",
                "root_cause": "Hỏng bộ nguồn do quá nhiệt",
            },
            "response": {"name": "INC-2026-00001", "status": "Đã khắc phục"},
            "errors": {
                "BUSINESS_RULE": "Phiếu chưa ở trạng thái cho phép khắc phục",
                "FORBIDDEN": "Không có quyền thực hiện hành động này",
            },
        },
    },
    "imm12.close_incident": {
        "summary": "Đóng phiếu sự cố",
        "description": (
            "Xác minh và đóng phiếu sự cố sau khắc phục. Sinh lifecycle event; nếu mức "
            "độ nghiêm trọng cao có thể yêu cầu RCA/CAPA trước khi đóng."
        ),
        "tags": ["IMM-12"],
        "examples": {
            "request": {
                "name": "INC-2026-00001",
                "verification_notes": "Đã kiểm tra lại thiết bị hoạt động bình thường",
            },
            "response": {"name": "INC-2026-00001", "status": "Đã đóng"},
            "errors": {
                "BUSINESS_RULE": "Cần hoàn tất RCA trước khi đóng phiếu",
                "FORBIDDEN": "Không có quyền đóng phiếu sự cố (cần Trưởng xưởng hoặc QA)",
            },
        },
    },
    "imm12.create_rca": {
        "summary": "Tạo phân tích nguyên nhân gốc (RCA)",
        "description": (
            "Khởi tạo bản ghi phân tích nguyên nhân gốc cho một phiếu sự cố theo phương "
            "pháp chọn (mặc định 5-Why). Liên kết ngược về phiếu sự cố nguồn."
        ),
        "tags": ["IMM-12"],
        "examples": {
            "request": {"incident_name": "INC-2026-00001", "rca_method": "5-Why"},
            "response": {"name": "RCA-2026-00001", "status": "Bản nháp"},
            "errors": {
                "FORBIDDEN": "Không có quyền tạo RCA",
                "NOT_FOUND": "Không tìm thấy phiếu sự cố",
            },
        },
    },
}
