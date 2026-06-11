"""TC-MOB-OAS-01..12 + TC-MOB-OAUTH-TOKEN-01..05 — Lint guard cho hợp đồng OpenAPI mobile.

Guard chống drift contract-identity của `docs/mobile/openapi/assetcore-mobile.openapi.yaml`.
KHÁC test_oas_generator/test_oas_signatures (2 suite đó target AUTO-GEN AssetCore spec,
KHÔNG đọc mobile yaml). Suite này CHỈ đọc file yaml mobile (read-only, no DB, no live BE).

A16 — ERROR-STATUS contract fix (TC-MOB-OAS-12): tách 401 (Authorization header CÓ nhưng
  bearer hết-hạn/invalid — AuthenticationError frappe/exceptions.py:26-27 status 401, raise
  auth.py:630) vs 403 (guest/no-token HOẶC thiếu permission/cap — PermissionError :34-35
  status 403, raise is_whitelisted __init__.py:876). (a) wire '403'→Forbidden lên TẤT CẢ
  12 path MVP (10 business STUB + 2 device-token bearer-gated self-service 06 §2.3) ⇒ tập
  403 == tập 401 (12==12 đối xứng). (b) +schema FrappeRawError {exc_type req · exception?/
  exc?/_server_messages? opt} source-char @frappe/utils/response.py V1 (exc_type :46;
  exception :43-45 gated; exc :185; _server_messages :188) + repoint Unauthorized401/Forbidden/
  RateLimited429 từ schemas/Error → schemas/FrappeRawError (3 response pre-handler raw, KHÔNG
  Error envelope — codegen KHỚP body runtime). (c) 3 auth path KHÔNG declare 403. orphan VẪN 10
  (Forbidden referenced từ trước; FrappeRawError $ref'd ngay → KHÔNG orphan).

B1 (Phase B) — AUTH-SECTION token-endpoint RESPONSE contract đóng băng (class
  `TestMobileOAuthToken`, TC-MOB-OAUTH-TOKEN-01..05). Đặc tả PASSTHROUGH OAuthlib
  (KHÔNG AssetCore envelope — Frappe core SSoT). SOURCE-CHARACTERIZED @Frappe v15.107.2
  (oauthlib 3.3.1), body THẬT @file:line (KHÔNG copy prose):
    - getOAuthToken 200-body keys = {access_token, expires_in, token_type, scope?, refresh_token?}
      (oauthlib BearerToken.create_token tokens.py:309-326; set oauth2.py:137).
    - getOAuthToken 400-body = OAuthError400 (oauthlib twotuples errors.py:80-88 {error,
      error_description?, error_uri?} set oauth2.py:132-135 | generate_json_error_response
      oauth.py:563-575 {description, status_code, error}). `error` = key CHUNG (required).
    - revokeOAuthToken 200-body = empty object (RFC 7009 luôn 200 — oauth2.py:158-159).
  GAP CLOSED: component `OAuthError400` (schema + response) wire '400'→OAuthError400 CHỈ lên
  getOAuthToken (token-issuance grant). KHÔNG path business STUB nhận OAuthError400 (chống leak
  nhầm — OAuthError400 KHÁC Error envelope + KHÁC FrappeRawError business-path). authorize=302,
  revoke=200 KHÔNG có 400. operationId FROZEN.

A12 — referential-integrity & codegen-validity (THÊM TC-MOB-OAS-09/10, KHÔNG THAY 01..08):
  - TC-MOB-OAS-09: 0 dangling `$ref` — walk toàn yaml bằng STDLIB (tự resolve pointer
    `#/...`, KHÔNG cần openapi_spec_validator/prance vì 2 lib này KHÔNG cài). MỌI `$ref`
    trỏ tới node TỒN TẠI (dangling = codegen crash → hard-fail). SSoT: ../../../docs/mobile/
    04-api-contract.md §8.2.
  - TC-MOB-OAS-10: orphan-component (defined-không-`$ref`'d) PHẢI ⊆ allow-list RESERVED
    10 mục (A13: 8 offline/pagination forward-reserve Phase C/E + Conflict409 reuse +
    OAuth2 false-orphan dùng qua top-level `security:`; RateLimited429 ĐÃ rời allow-list
    vì A13 wire vào 2 path @rate_limit). Orphan NGOÀI allow-list = FAIL (dead surface lén);
    mục allow-list KHÔNG-còn-orphan (đã wire) = FAIL (allow-list stale).
    `_RESERVED_ORPHANS` dưới PHẢN CHIẾU bảng RESERVED của 04 §8.2 (SSoT) 1:1.

Bám A10 (giữ STUB — KHÔNG bồi schema; chỉ contract-identity):
  - TC-MOB-OAS-01: yaml lint hợp lệ (safe_load OK) + openapi==3.0.3 +
    info.title/version đóng băng (0.1.0-skeleton) + đúng 15 path.
  - TC-MOB-OAS-02: 15/15 path-operation CÓ operationId (0 None).
  - TC-MOB-OAS-03: operationId DUY NHẤT toàn file (len(set)==len(list)==15).
  - TC-MOB-OAS-04: mọi operationId khớp regex camelCase verbNoun (^[a-z][a-zA-Z0-9]*$).
  - TC-MOB-OAS-05: convention SSoT — operationId KHỚP map dotted-path→camelCase đã đặc tả
    (../04-api-contract.md §8.1). Bắt đúng tail-của-dotted-path + verb-first cho oauth.
  - TC-MOB-OAS-06: 2 device-token GIỮ NGUYÊN TÊN (registerDeviceToken/unregisterDeviceToken,
    chốt A5) — chống drift client đã sinh.
  - TC-MOB-OAS-07 (STUB-A10-07): 6 path nghiệp vụ + 3 list VẪN là STUB — KHÔNG có
    requestBody và response 200 vẫn trỏ #/components/responses/Stub (schema chi tiết = Phase C).
    Guard chống bồi schema Phase C lén vào round A10 (A10 chỉ thêm contract-identity).
  - TC-MOB-OAS-08 (LINT-A10-08): 0 `nullable` mồ côi (thiếu sibling `type`) trong
    components.schemas — spec-correctness OpenAPI 3.0.3 (nullable-type-sibling). Phát hiện
    live qua `redocly lint` khi đóng vai mobile-dev codegen; nếu vi phạm = lint-ERROR fail
    CI gate repo native. KHÁC STUB-warning (unused-component/missing-4xx trên STUB = CHỦ Ý
    Phase C, KHÔNG guard).

Convention (../04-api-contract.md §8.1): tail-của-dotted-path → camelCase verbNoun;
verb-first cho oauth (authorize→authorizeOAuth, get_token→getOAuthToken,
revoke_token→revokeOAuthToken); GET-list→listX; create_X→createX; report_X→reportX;
get_X→getX; resolve_qr_token→resolveQrToken; get_asset_scan_info→getAssetScanInfo.

Run: bench --site miyano run-tests --module assetcore.tests.test_mobile_oas
"""
from __future__ import annotations

import re
import importlib
import inspect
import unittest
from pathlib import Path

import yaml

# docs/mobile/openapi/assetcore-mobile.openapi.yaml — repo-relative (4 cấp lên từ file test).
#   assetcore/assetcore/tests/test_mobile_oas.py → repo root = parents[2]
_REPO_ROOT = Path(__file__).resolve().parents[2]
_MOBILE_YAML = _REPO_ROOT / "docs" / "mobile" / "openapi" / "assetcore-mobile.openapi.yaml"

_HTTP_VERBS = ("get", "post", "put", "delete", "patch", "head", "options", "trace")

# camelCase verbNoun: bắt đầu chữ thường, không gạch dưới/space, không kết thúc số dính.
_CAMEL_RE = re.compile(r"^[a-z][a-zA-Z0-9]*$")

# SSoT convention map — dotted-path (tail) → operationId mong đợi. Phase C bồi path mới
# PHẢI thêm dòng tương ứng theo CÙNG luật (../04-api-contract.md §8.1).
_EXPECTED = {
    "/api/method/frappe.integrations.oauth2.authorize": ("get", "authorizeOAuth"),
    "/api/method/frappe.integrations.oauth2.get_token": ("post", "getOAuthToken"),
    "/api/method/frappe.integrations.oauth2.revoke_token": ("post", "revokeOAuthToken"),
    "/api/method/assetcore.api.imm00.resolve_qr_token": ("get", "resolveQrToken"),
    "/api/method/assetcore.api.imm00.get_asset_scan_info": ("get", "getAssetScanInfo"),
    "/api/method/assetcore.api.imm00.get_asset": ("get", "getAsset"),
    "/api/method/assetcore.api.imm12.report_incident": ("post", "reportIncident"),
    "/api/method/assetcore.api.imm08.create_pm_work_order": ("post", "createPmWorkOrder"),
    "/api/method/assetcore.api.imm09.create_repair_work_order": ("post", "createRepairWorkOrder"),
    "/api/method/assetcore.api.imm11.create_calibration": ("post", "createCalibration"),
    "/api/method/assetcore.api.imm08.list_pm_work_orders": ("get", "listPmWorkOrders"),
    "/api/method/assetcore.api.imm09.list_repair_work_orders": ("get", "listRepairWorkOrders"),
    "/api/method/assetcore.api.imm12.list_incidents": ("get", "listIncidents"),
    "/api/method/assetcore.api.mobile.v1.register_device_token": ("post", "registerDeviceToken"),
    "/api/method/assetcore.api.mobile.v1.unregister_device_token": ("post", "unregisterDeviceToken"),
}

# 2 device-token GIỮ NGUYÊN TÊN (chốt A5 — KHÔNG đổi, tránh drift client đã sinh).
_DEVICE_TOKEN_FROZEN = {
    "/api/method/assetcore.api.mobile.v1.register_device_token": "registerDeviceToken",
    "/api/method/assetcore.api.mobile.v1.unregister_device_token": "unregisterDeviceToken",
}

# Phase-C — reportIncident path (path Phase-C ĐẦU TIÊN rời STUB). Có requestBody THẬT
#   ($ref requestBodies/ReportIncidentBody → schemas/ReportIncidentRequest) ⇒ KHÔNG còn
#   trong _STUB_PATHS (guard STUB-07 KHÔNG áp). VẪN giữ 200→Stub + 401 + 403 (chỉ THÊM
#   requestBody vòng này). Guard requestBody = TC-MOB-OAS-13 (class TestMobileReportIncidentBody).
_REPORT_INCIDENT_PATH = "/api/method/assetcore.api.imm12.report_incident"

# C-REQBODY-CREATEREPAIR — createRepairWorkOrder (path Phase-C THỨ HAI rời STUB). Có requestBody
#   THẬT ($ref requestBodies/CreateRepairWorkOrderBody → schemas/CreateRepairWorkOrderRequest) ⇒
#   KHÔNG còn trong _STUB_PATHS (guard STUB-07 KHÔNG áp). VẪN MVP-business ⇒ 401/403 symmetry GIỮ
#   12. Guard requestBody+response = TC-MOB-OAS-16 (class TestMobileCreateRepairBody).
_REPAIR_CREATE_PATH = "/api/method/assetcore.api.imm09.create_repair_work_order"

# C-REQBODY-CREATECAL — createCalibration (path Phase-C THỨ BA rời STUB — hoàn tất bộ-ba create
#   report→repair→calibration). Có requestBody THẬT ($ref requestBodies/CreateCalibrationBody →
#   schemas/CreateCalibrationRequest) ⇒ KHÔNG còn trong _STUB_PATHS (guard STUB-07 KHÔNG áp). VẪN
#   MVP-business ⇒ 401/403 symmetry GIỮ 12. Guard requestBody+response = TC-MOB-OAS-17
#   (class TestMobileCreateCalibrationBody).
_CAL_CREATE_PATH = "/api/method/assetcore.api.imm11.create_calibration"

# C-LISTREAD — 3 list path Phase-C list-read (rời STUB vòng này). Có pagination param query +
#   200→Paginatedlist-envelope THẬT (KHÔNG còn Stub). Guard riêng = TC-MOB-OAS-14
#   (class TestMobileListReadContract). VẪN MVP-business ⇒ 401/403 symmetry GIỮ 12.
_LIST_PM_PATH = "/api/method/assetcore.api.imm08.list_pm_work_orders"
_LIST_REPAIR_PATH = "/api/method/assetcore.api.imm09.list_repair_work_orders"
_LIST_INCIDENT_PATH = "/api/method/assetcore.api.imm12.list_incidents"
_LIST_PATHS = {_LIST_PM_PATH, _LIST_REPAIR_PATH, _LIST_INCIDENT_PATH}

# R4 §8.7 — TYPED reads/create (rời _STUB_PATHS vòng này, GROUNDED chữ-ký service THẬT):
#   resolveQrToken (imm00.py:303) / getAssetScanInfo (imm00.py:567) / getAsset (imm00.py:288) →
#   typed envelope read; createPmWorkOrder (imm08.py:836) → 200-oneOf [Created|Error] §5c. VẪN
#   MVP-business ⇒ 401/403 symmetry GIỮ 12 via _MVP_BUSINESS_PATHS. Guard typed = TC-MOB-OAS-20.
_TYPED_READ_PATHS = {
    "/api/method/assetcore.api.imm00.resolve_qr_token",
    "/api/method/assetcore.api.imm00.get_asset_scan_info",
    "/api/method/assetcore.api.imm00.get_asset",
}
_CREATE_PM_PATH = "/api/method/assetcore.api.imm08.create_pm_work_order"

# _STUB_PATHS — path CÒN STUB THẬT (200 trỏ #/components/responses/Stub, 0 typed data). Sau R4:
#   4 typed read/create rời → CHỈ CÒN 2 device-token (register/unregister) — handler CHƯA tồn tại
#   @source (api/mobile/ chỉ __init__.py+preflight.py) ⇒ [ROADMAP] BE-PENDING, BA gate KHÔNG bịa
#   endpoint (04 §8.7 + ADR-MOBILE-001 h). 2 device-token KHÔNG dùng responses/Stub mà
#   Unauthorized401/Forbidden + 200 Stub-envelope → GIỮ trong set STUB-status (guard STUB-07).
_STUB_PATHS = set(_DEVICE_TOKEN_FROZEN)

# 10 path nghiệp vụ field-tech MVP = 3 typed read + createPm + reportIncident + createRepair +
#   createCalibration + 3 list (Phase-C). Dùng cho 401/403 symmetry (KHÔNG phụ thuộc STUB-status —
#   mọi path rời STUB nhưng VẪN MVP-business). 12 = 10 business + 2 device-token.
_MVP_BUSINESS_PATHS = (
    _TYPED_READ_PATHS
    | {_CREATE_PM_PATH, _REPORT_INCIDENT_PATH, _REPAIR_CREATE_PATH, _CAL_CREATE_PATH}
    | _LIST_PATHS
)

# A13 — ERROR-RESPONSE coverage (failure-mode prose → contract máy-đọc).
#   MỌI path MVP (10 nghiệp vụ + 2 device-token) PHẢI declare 401 (bearer hết hạn →
#   refresh/re-auth — 04 §4 row 4 + §5 line 146-147 + ADR-MOBILE-001 e). 3 auth path
#   (authorize/get_token/revoke) GIỮ NGUYÊN (302/200 — Frappe core) → KHÔNG yêu cầu 401.
#   NB: 10 business = _MVP_BUSINESS_PATHS (3 typed read + createPm + report + createRepair +
#   createCal + 3 list — R4: KHÔNG còn dựa STUB-status) ⇒ 12 path MVP (10 + 2 device-token)
#   declare 401. R4: typed reads/createPm RỜI _STUB_PATHS nhưng VẪN MVP-business ⇒ symmetry
#   GIỮ 12 (dùng _MVP_BUSINESS_PATHS, KHÔNG _STUB_PATHS). Số 12 = sự-thật @source.
_PATHS_REQUIRE_401 = _MVP_BUSINESS_PATHS | set(_DEVICE_TOKEN_FROZEN)

# A16 — ERROR-STATUS contract fix (tách 401 expired-bearer vs 403 guest/no-token/thiếu-cap).
#   403 wire lên TẤT CẢ 12 path MVP (10 business + 2 device-token). Device-token =
#   bearer-gated self-service (06 §2.3, KHÔNG allow_guest) ⇒ guest/no-token cũng 403
#   (PermissionError, is_whitelisted __init__.py:876, http_status_code=403). ĐỐI XỨNG:
#   12 path declare 401 == 12 path declare 403 (mirror _PATHS_REQUIRE_401). 3 auth path
#   (authorize/get_token/revoke) KHÔNG đụng (302/200/400 Frappe core) → KHÔNG declare 403.
#   Phase-C: reportIncident VẪN trong cả 2 set (tách khỏi _STUB_PATHS KHÔNG đổi symmetry).
_PATHS_REQUIRE_403 = _MVP_BUSINESS_PATHS | set(_DEVICE_TOKEN_FROZEN)

# 3 auth path Frappe-core: KHÔNG đụng (302/200) → KHÔNG declare 401.
_AUTH_PATHS = {
    "/api/method/frappe.integrations.oauth2.authorize",
    "/api/method/frappe.integrations.oauth2.get_token",
    "/api/method/frappe.integrations.oauth2.revoke_token",
}

# ĐÚNG 2 path có @rate_limit THẬT @source (imm00.py:311 resolve, :354 scan-info) → 429.
#   KHÔNG path nào khác có @rate_limit MVP ⇒ wire 429 chỗ khác = bịa hợp đồng.
_PATHS_REQUIRE_429 = {
    "/api/method/assetcore.api.imm00.resolve_qr_token",
    "/api/method/assetcore.api.imm00.get_asset_scan_info",
}

# ── B1 — AUTH-SECTION token-endpoint RESPONSE contract (SOURCE-CHARACTERIZED) ──
_GET_TOKEN_PATH = "/api/method/frappe.integrations.oauth2.get_token"
_REVOKE_TOKEN_PATH = "/api/method/frappe.integrations.oauth2.revoke_token"
_AUTHORIZE_PATH = "/api/method/frappe.integrations.oauth2.authorize"

# getOAuthToken 200-body keys @source: oauthlib BearerToken.create_token (tokens.py:309-326).
#   access_token+expires_in+token_type LUÔN có; scope?/refresh_token? optional.
#   (Frappe set body nguyên: oauth2.py:137 `frappe.local.response = body`.)
_GET_TOKEN_200_KEYS_REQUIRED = {"access_token", "expires_in", "token_type"}
_GET_TOKEN_200_KEYS_OPTIONAL = {"scope", "refresh_token"}
_GET_TOKEN_200_KEYS_ALL = _GET_TOKEN_200_KEYS_REQUIRED | _GET_TOKEN_200_KEYS_OPTIONAL

# OAuthError400 schema keys @source (union 2 đường error provider Frappe):
#   (1) oauthlib OAuth2Error.twotuples (errors.py:80-88): {error, error_description?, error_uri?}.
#   (2) generate_json_error_response (oauth.py:567-573): {description, status_code, error}.
#   `error` = key CHUNG → required. KHÁC AssetCore Error envelope ({success,error,code,http_status}).
_OAUTH_ERROR_SCHEMA_REQUIRED = {"error"}
_OAUTH_ERROR_SCHEMA_KEYS_ALL = {
    "error", "error_description", "error_uri", "description", "status_code",
}
# Error envelope keys (business-path) — OAuthError400 KHÔNG được trùng shape này (distinct guard).
_BUSINESS_ENVELOPE_KEYS = {"success", "code", "http_status"}

_OAUTH_ERROR_RESPONSE_REF = "#/components/responses/OAuthError400"
_OAUTH_ERROR_SCHEMA_REF = "#/components/schemas/OAuthError400"

# ── A16 — pre-handler raw error (FrappeRawError) cho 401/403/429 ──
#   3 response pre-handler (Unauthorized401/Forbidden/RateLimited429) trỏ schemas/FrappeRawError
#   (raw Frappe body THẬT), KHÔNG schemas/Error (business in-handler envelope). FrappeRawError =
#   {exc_type req, exception?/exc?/_server_messages? opt} source-char @frappe/utils/response.py V1
#   (exc_type :46; exception :43-45 gated; exc :185; _server_messages :188).
_FRAPPE_RAW_ERROR_SCHEMA_REF = "#/components/schemas/FrappeRawError"
_ERROR_ENVELOPE_SCHEMA_REF = "#/components/schemas/Error"
# 3 response pre-handler PHẢI trỏ FrappeRawError (KHÔNG Error envelope) — A16.
_PREHANDLER_RAW_RESPONSES = ("Unauthorized401", "Forbidden", "RateLimited429")
_FRAPPE_RAW_ERROR_REQUIRED = {"exc_type"}
_FRAPPE_RAW_ERROR_KEYS_ALL = {"exc_type", "exception", "exc", "_server_messages"}

# ── TC-MOB-OAS-19 — P1 contract-correctness (403 oneOf disambiguation + $ref-with-sibling) ──
#   (19a) FrappeRawError.additionalProperties === false → closed-shape: dispatcher-403 raw
#         {exc_type,...} KHÔNG validate-pass Error (thiếu required success/error/code/http_status);
#         Error envelope {success,error,code,http_status,...} KHÔNG validate-pass FrappeRawError-closed
#         (có key ngoài exc_type/exception/exc/_server_messages khi additionalProperties:false).
#         ⇒ codegen deser route ĐÚNG nhánh oneOf theo shape (KHÔNG anyMatch ambiguity).
#   (19b) 0 $ref-with-sibling toàn spec: OAS 3.0.3 BỎ QUA mọi sibling cạnh `$ref` → spectral /
#         openapi-generator --strict emit warning. Walk toàn spec — KHÔNG node nào vừa có `$ref`
#         vừa có key khác (phủ 3 create requestBody + bất kỳ node khác).
#   (19c) 3 path requestBody = {$ref-only} (gỡ sibling `required:true` ở path-level) ĐỒNG THỜI
#         components.requestBodies/*Body.required === true (required CHUYỂN ĐÚNG chỗ — không mất ràng buộc).
#   (19d) disambiguation property: ReportIncidentForbidden.oneOf=[Error,FrappeRawError] — mẫu
#         dispatcher-403 {exc_type:'PermissionError'} KHÔNG thoả required của Error VÀ mẫu in-handler
#         {success:false,error,code:'FORBIDDEN',http_status:403} KHÔNG thoả FrappeRawError-closed →
#         2 shape loại trừ nhau (machine-distinguishable).
_ERROR_REQUIRED_KEYS = {"success", "error", "code", "http_status"}   # required @schemas/Error envelope
# 3 path-level requestBody trỏ component requestBodies — sau fix CHỈ còn key `$ref` (no `required` sibling).
_REQBODY_PATHS = {
    _REPORT_INCIDENT_PATH: "#/components/requestBodies/ReportIncidentBody",
    _REPAIR_CREATE_PATH: "#/components/requestBodies/CreateRepairWorkOrderBody",
    _CAL_CREATE_PATH: "#/components/requestBodies/CreateCalibrationBody",
}
# component requestBodies GIỮ `required: true` nội bộ (required CHUYỂN ĐÚNG chỗ, không mất).
_REQBODY_COMPONENTS = ("ReportIncidentBody", "CreateRepairWorkOrderBody", "CreateCalibrationBody")
# Mẫu body THẬT @source để chứng minh 2 nhánh oneOf loại trừ nhau (disambiguation property).
_SAMPLE_DISPATCHER_403 = {"exc_type": "PermissionError"}             # __init__.py:876 raw
_SAMPLE_INHANDLER_403 = {                                           # imm12.py:96 _err → Error envelope
    "success": False, "error": "Không đủ quyền", "code": "FORBIDDEN", "http_status": 403,
}

# Path business (MVP nghiệp vụ + device-token) — KHÔNG path nào được nhận OAuthError400 (anti-leak).
#   Phase-C: reportIncident VẪN business (dùng _MVP_BUSINESS_PATHS) ⇒ vẫn cấm OAuthError400/400.
_BUSINESS_PATHS = _MVP_BUSINESS_PATHS | set(_DEVICE_TOKEN_FROZEN)

# ── Phase-C — reportIncident requestBody contract (TC-MOB-OAS-13) ──
#   Body THẬT (path Phase-C ĐẦU TIÊN rời STUB). SOURCE-CHARACTERIZED:
#     required EXACT = 4 field reqd=1 @incident_report.json (KHÔNG thừa KHÔNG thiếu).
#     severity enum 1:1 Select options @incident_report.json (Low\nMedium\nHigh\nCritical).
#     incident_type enum 1:1 Select options (Failure\nSafety Event\nNear Miss\nMalfunction).
#     asset/description = string. `source` KHÔNG ở body (server coerce — imm12.py:83).
_REPORT_INCIDENT_BODY_REF = "#/components/requestBodies/ReportIncidentBody"
_REPORT_INCIDENT_SCHEMA_REF = "#/components/schemas/ReportIncidentRequest"
_REPORT_INCIDENT_REQUIRED = ["asset", "incident_type", "severity", "description"]
_SEVERITY_ENUM = ["Low", "Medium", "High", "Critical"]            # @incident_report.json Select-canonical
_INCIDENT_TYPE_ENUM = ["Failure", "Safety Event", "Near Miss", "Malfunction"]  # @incident_report.json
# `source` (provenance qr-scan/manual) KHÔNG được lọt vào body — server gán (anti-leak).
_REPORT_INCIDENT_FORBIDDEN_PROP = "source"

# ── G-REQBODY — đóng 4 contract-gap codegen report_incident (TC-MOB-OAS-13/15) ──
#   (gap-1) ReportIncidentBody.content = oneOf 2 media-type (json + form-urlencoded) CÙNG 1 $ref.
#   (gap-2) report.post '403' = DUAL-SHAPE oneOf Error|FrappeRawError (component
#           ReportIncidentForbidden, KHÁC Forbidden single-FrappeRawError). in-handler cap-403
#           HTTP-200+Error (imm12.py:96) vs dispatcher-403 HTTP-403+FrappeRawError (__init__.py:876).
#   (gap-4) report.post '200' = ReportIncidentCreated (data=ReportIncidentResponse {name,status,
#           severity} services/imm12.py:410) + wire '404'→NotFound404 (asset∄ services/imm12.py:361)
#           + '422'→Unprocessable422 (BR-12-01 services/imm12.py:359). status Select-canonical 7.
_REPORT_BODY_MEDIA_TYPES = {"application/json", "application/x-www-form-urlencoded"}
_REPORT_INCIDENT_RESPONSE_SCHEMA_REF = "#/components/schemas/ReportIncidentResponse"
_REPORT_INCIDENT_CREATED_RESP_REF = "#/components/responses/ReportIncidentCreated"
_REPORT_INCIDENT_FORBIDDEN_RESP_REF = "#/components/responses/ReportIncidentForbidden"
_NOT_FOUND_404_RESP_REF = "#/components/responses/NotFound404"
_UNPROCESSABLE_422_RESP_REF = "#/components/responses/Unprocessable422"
# status Select-canonical 1:1 @incident_report.json (create-time = "Open" imm12.py:373).
_INCIDENT_STATUS_ENUM = [
    "Open", "Acknowledged", "In Progress", "Resolved", "RCA Required", "Closed", "Cancelled",
]
_REPORT_INCIDENT_RESPONSE_REQUIRED = ["name", "status", "severity"]
# G-OAS-STATUSLINE (P1 contract-correctness) — schema CreatedEnvelope (named) cho 200-oneOf
#   discriminator. in-handler error 404/422 (report) arrive HTTP status-line 200 + Error body
#   (quirk §5) → KHÔNG keyed dưới HTTP-code response-key (dead-deser branch). Gom vào nhánh
#   Error của 200-oneOf; client route theo body.success (discriminator) + body.http_status.
_REPORT_INCIDENT_CREATED_ENVELOPE_REF = "#/components/schemas/ReportIncidentCreatedEnvelope"
_ERROR_SCHEMA_REF = "#/components/schemas/Error"
# report_incident status-set MỚI (G-OAS-STATUSLINE): in-handler 404/422 KHÔNG còn status-line key
#   (arrive HTTP-200+Error). Pre-handler 401/403 GIỮ (dispatcher status-line THẬT) → symmetry 12.
_REPORT_INCIDENT_STATUS_SET = ["200", "401", "403"]

# ── C-REQBODY-CREATEREPAIR — guard refs cho createRepairWorkOrder (TC-MOB-OAS-16) ──
#   SOURCE-CHARACTERIZED @imm09.py:36-38 (required 4 không-default + 3 optional default "") +
#   @asset_repair.json (enum repair_type/priority Select-canonical) + @imm09.py:786 (return).
#   SELF-CORRECTION 3 delta vs đề mục (bám source, KHÔNG bám chữ đề mục):
#     (d1) 200 data = {name,status,sla_target_hours} (imm09.py:786) — KHÔNG priority.
#     (d2) 403 = SINGLE-SHAPE Forbidden (rbac.require→PermissionError HTTP-403 imm09.py:40,
#          exceptions.py:35) — KHÔNG dual-shape (imm12 dùng _err in-handler; imm09 dùng require).
#     (d3) HAS_OPEN_WO = http_status 409 CONFLICT (messages.py:667) → Conflict409 — KHÔNG 422.
_REPAIR_CREATE_BODY_REF = "#/components/requestBodies/CreateRepairWorkOrderBody"
_REPAIR_CREATE_SCHEMA_REF = "#/components/schemas/CreateRepairWorkOrderRequest"
_REPAIR_CREATE_REQUIRED = ["asset_ref", "repair_type", "priority", "failure_description"]
_REPAIR_TYPE_ENUM = ["Corrective", "Breakdown", "Warranty Repair"]   # @asset_repair.json Select-canonical
_REPAIR_PRIORITY_ENUM = ["Normal", "Urgent", "Emergency"]            # @asset_repair.json (khớp _SLA_MATRIX)
_REPAIR_CREATE_OPTIONAL = ["incident_report", "source_pm_wo", "fault_image"]  # default "" @imm09.py:37-38
_REPAIR_CREATE_FORBIDDEN_PROP = "requested_by"   # server gán (imm09.py:770) — KHÔNG client gửi
_REPAIR_BODY_MEDIA_TYPES = {"application/json", "application/x-www-form-urlencoded"}
_REPAIR_CREATE_RESPONSE_SCHEMA_REF = "#/components/schemas/CreateRepairWorkOrderResponse"
_REPAIR_CREATE_CREATED_RESP_REF = "#/components/responses/CreateRepairWorkOrderCreated"
_REPAIR_CREATE_FORBIDDEN_RESP_REF = "#/components/responses/Forbidden"   # SINGLE-SHAPE (delta d2)
_CONFLICT_409_RESP_REF = "#/components/responses/Conflict409"
# status @asset_repair.json Select-canonical (create-time = "Open" RepairStatus.OPEN imm09.py:786).
_REPAIR_STATUS_ENUM = [
    "Open", "Assigned", "Diagnosing", "Pending Parts", "In Repair",
    "Pending Inspection", "Completed", "Cannot Repair", "Cancelled",
]
_REPAIR_CREATE_RESPONSE_REQUIRED = ["name", "status", "sla_target_hours"]  # imm09.py:786 (delta d1)
# G-OAS-STATUSLINE — CreatedEnvelope named schema cho 200-oneOf discriminator. in-handler
#   404/409 (imm09.py:746/753) arrive HTTP-200+Error → gom vào nhánh Error, KHÔNG status-line key.
_REPAIR_CREATE_CREATED_ENVELOPE_REF = "#/components/schemas/CreateRepairWorkOrderCreatedEnvelope"
# createRepair status-set MỚI (G-OAS-STATUSLINE): 404/409 in-handler KHÔNG còn status-line key.
#   401/403 GIỮ (dispatcher status-line THẬT) → symmetry 12 BẤT BIẾN.
_REPAIR_CREATE_STATUS_SET = ["200", "401", "403"]

# ── C-REQBODY-CREATECAL — guard refs cho createCalibration (TC-MOB-OAS-17) ──
#   SOURCE-CHARACTERIZED @api/imm11.py:90-94 (required 4 không-default + 5 optional default null) +
#   @imm_asset_calibration.json (enum calibration_type/status Select-canonical) + @services/imm11.py:1015
#   (return {name, status}). Tái dùng template C-REQBODY-CREATEREPAIR (TC-MOB-OAS-16).
#   SELF-CORRECTION 2 delta vs đề mục (bám source, KHÔNG bám chữ đề mục):
#     (c1) 403 = SINGLE-SHAPE Forbidden (rbac.require('calibration.create')→PermissionError HTTP-403
#          imm11.py:95, exceptions.py:35) — KHÔNG dual-shape (đề mục ĐÚNG: report dùng _err; cal dùng require).
#     (c2) IMM11_ASSET_BLOCKED = http_status 409 CONFLICT (messages.py:860, CAL-008) → Conflict409
#          — KHÔNG 422. Đề mục viết "422→Unprocessable422 + KHÔNG 409". SAI @source: message-code
#          map 409 CONFLICT (_HTTP_TO_BUCKET[409]=CONFLICT notify.py:42), KHÔNG validation 422.
#          handle() pass-through http_status (api_handler.py:61) ⇒ surface HTTP-409 THẬT. KHÁC
#          nguyên-nhân createRepair-409 (open-WO) nhưng CÙNG HTTP-409 (lifecycle-block CAL-008).
_CAL_CREATE_BODY_REF = "#/components/requestBodies/CreateCalibrationBody"
_CAL_CREATE_SCHEMA_REF = "#/components/schemas/CreateCalibrationRequest"
_CAL_CREATE_REQUIRED = ["asset", "calibration_type", "scheduled_date", "technician"]
_CAL_TYPE_ENUM = ["External", "In-House"]   # @imm_asset_calibration.json Select-canonical 1:1
_CAL_CREATE_OPTIONAL = [
    "calibration_schedule", "lab_supplier", "is_recalibration",
    "reference_standard_serial", "traceability_reference",
]  # default null @imm11.py:91-94
_CAL_BODY_MEDIA_TYPES = {"application/json", "application/x-www-form-urlencoded"}
_CAL_CREATE_RESPONSE_SCHEMA_REF = "#/components/schemas/CreateCalibrationResponse"
_CAL_CREATE_CREATED_RESP_REF = "#/components/responses/CreateCalibrationCreated"
_CAL_CREATE_FORBIDDEN_RESP_REF = "#/components/responses/Forbidden"   # SINGLE-SHAPE (delta c1)
# status @imm_asset_calibration.json Select-canonical (create-time = "Scheduled"
#   CalibrationResult.SCHEDULED imm11.py:1013, = doctype default).
_CAL_STATUS_ENUM = [
    "Scheduled", "Sent to Lab", "In Progress", "Certificate Received",
    "Passed", "Failed", "Conditionally Passed", "Cancelled",
]
_CAL_CREATE_RESPONSE_REQUIRED = ["name", "status"]  # imm11.py:1015 (KHÔNG sla_target_hours)
# G-OAS-STATUSLINE — CreatedEnvelope named schema cho 200-oneOf discriminator. in-handler
#   404/409 (imm11.py:999/1002) arrive HTTP-200+Error → gom vào nhánh Error, KHÔNG status-line key.
_CAL_CREATE_CREATED_ENVELOPE_REF = "#/components/schemas/CreateCalibrationCreatedEnvelope"
# createCalibration status-set MỚI (G-OAS-STATUSLINE): 404/409 in-handler KHÔNG còn status-line
#   key. 401/403 GIỮ (dispatcher status-line THẬT) → symmetry 12 BẤT BIẾN.
_CAL_CREATE_STATUS_SET = ["200", "401", "403"]

# C-LISTREAD — pagination param + list-envelope refs (Phase-C list-read). Signature LIVE
#   introspect (imm08.list_pm_work_orders:28 / imm09.list_repair_work_orders:21 /
#   imm12.list_incidents:197). 2 envelope PHÂN BIỆT theo rows-key THẬT @source (§6.2):
#   WorkOrderListEnvelope=data.data[] (imm08/09), IncidentListEnvelope=data.items[] (imm12).
_PAGE_REF = "#/components/parameters/Page"
_PAGE_SIZE_REF = "#/components/parameters/PageSize"
_WO_FILTERS_REF = "#/components/parameters/WorkOrderFilters"
_WO_LIST_RESP_REF = "#/components/responses/WorkOrderList"
_INCIDENT_LIST_RESP_REF = "#/components/responses/IncidentList"
_WO_LIST_SCHEMA_REF = "#/components/schemas/WorkOrderListEnvelope"
_INCIDENT_LIST_SCHEMA_REF = "#/components/schemas/IncidentListEnvelope"
_INCIDENT_PARAM_REFS = [
    "#/components/parameters/IncidentStatus",
    "#/components/parameters/IncidentSeverity",
    "#/components/parameters/IncidentAsset",
    "#/components/parameters/IncidentOpen",
]
# Bộ param query MONG ĐỢI cho từng list path (KHỚP signature LIVE introspect).
_LIST_PARAM_EXPECT = {
    _LIST_PM_PATH: {_WO_FILTERS_REF, _PAGE_REF, _PAGE_SIZE_REF},
    _LIST_REPAIR_PATH: {_WO_FILTERS_REF, _PAGE_REF, _PAGE_SIZE_REF},
    _LIST_INCIDENT_PATH: set(_INCIDENT_PARAM_REFS) | {_PAGE_REF, _PAGE_SIZE_REF},
}
# 200-response MONG ĐỢI (rows-key PHÂN BIỆT — codegen native deser đúng key).
_LIST_RESP_EXPECT = {
    _LIST_PM_PATH: _WO_LIST_RESP_REF,
    _LIST_REPAIR_PATH: _WO_LIST_RESP_REF,
    _LIST_INCIDENT_PATH: _INCIDENT_LIST_RESP_REF,
}
# Tên hàm whitelist LIVE (introspect signature — page/page_size có THẬT).
_LIST_LIVE_FN = {
    _LIST_PM_PATH: ("assetcore.api.imm08", "list_pm_work_orders", {"filters", "page", "page_size"}),
    _LIST_REPAIR_PATH: ("assetcore.api.imm09", "list_repair_work_orders", {"filters", "page", "page_size"}),
    _LIST_INCIDENT_PATH: ("assetcore.api.imm12", "list_incidents",
                          {"status", "severity", "asset", "open", "page", "page_size"}),
}


# A12/A13 — Allow-list RESERVED 10 orphan-component hợp lệ (defined-không-`$ref`'d).
#   PHẢN CHIẾU 1:1 bảng RESERVED tại docs/mobile/04-api-contract.md §8.2 (SSoT).
#   A13: RateLimited429 ĐÃ rời (wire vào 2 path @rate_limit) → 11→10.
#   8 mục offline/pagination = forward-reserve Phase C/E (wire vào path sau);
#   Conflict409 = reusable + offline-reuse; OAuth2 = FALSE-ORPHAN (dùng qua top-level
#   `security:` keyword + per-op `security: []`, KHÔNG `$ref` → walk naive KHÔNG thấy
#   ⇒ PHẢI allow-list, KHÔNG forbid naive).
#   KHI Phase C/E wire 1 component vào path (hết orphan) → GỠ mục đó khỏi set này.
#   B1: component OAuthError400 (schema + response) ĐÃ WIRE ngay khi thêm (response → schema,
#     getOAuthToken → response) ⇒ KHÔNG orphan → KHÔNG vào allow-list (allow-list GIỮ 10 mục).
_RESERVED_ORPHANS = {
    "#/components/parameters/IdempotencyKey",      # offline write-queue (07 §3) → Phase E
    "#/components/parameters/IfMatch",             # offline conflict (07 §4)    → Phase E
    "#/components/parameters/IfNoneMatch",         # offline read-cache (07 §2)  → Phase E
    "#/components/parameters/IfModifiedSince",     # offline read-cache (07 §2)  → Phase E
    # C-REQBODY-CREATEREPAIR: Conflict409 ĐÃ WIRE vào createRepairWorkOrder.post '409'
    #   (asset đã có WO mở — IMM09_ASSET_HAS_OPEN_WO services/imm09.py:753, http_status 409
    #   @messages.py:667) ⇒ HẾT orphan → GỠ khỏi allow-list (đồng bộ 04 §8.2). Orphan: 7→6.
    #   Nếu để lại = stale → TC-MOB-OAS-10 (b) ĐỎ.
    "#/components/responses/NotModified304",       # offline read-cache (07 §2)  → Phase E
    # A13: RateLimited429 ĐÃ WIRE vào 2 path @rate_limit (resolve_qr_token imm00.py:311 +
    #   get_asset_scan_info imm00.py:354) ⇒ HẾT orphan → GỠ khỏi allow-list (đồng bộ 04 §8.2).
    #   Orphan: 11→10.
    # C-LISTREAD: PaginatedListEnvelope ĐÃ tách thành WorkOrderListEnvelope+IncidentListEnvelope,
    #   cả 2 (+ 2 response WorkOrderList/IncidentList + 7 param pagination) WIRE NGAY vào 3 list
    #   path ⇒ HẾT orphan → GỠ PaginatedListEnvelope khỏi allow-list (đồng bộ 04 §8.2). Orphan:
    #   10→9. Nếu để lại = stale → TC-MOB-OAS-10 (b) ĐỎ.
    # G-OAS-STATUSLINE (P1 contract-correctness): NotFound404 / Unprocessable422 / Conflict409 =
    #   response cho in-handler business error (404/422/409). NHỮNG lỗi này arrive HTTP status-line
    #   200 + Error body (quirk §5 — handle()→_err→dict, response.py:95-154; hooks.py:405 no
    #   after_request ⇒ status-line KHÔNG BAO GIỜ set cho in-handler error). Keying chúng dưới
    #   HTTP-code response-key '404'/'422'/'409' = DEAD-DESER branch (codegen route theo HTTP
    #   status-line KHÔNG bao giờ thấy 404/422/409 cho in-handler error). G-OAS-STATUSLINE gỡ
    #   3 status-line key khỏi 3 create path + gom lỗi vào nhánh Error của 200-oneOf-discriminator
    #   ⇒ 3 response component này RỜI khỏi path (HẾT referenced) → ORPHAN trở lại → vào allow-list
    #   (forward-reserve: vẫn doc-intent + có thể wire Phase-E nếu after_request hook đổi status-line).
    "#/components/responses/NotFound404",          # in-handler 404 (HTTP-200+Error) → doc-only note
    "#/components/responses/Unprocessable422",     # in-handler 422 (HTTP-200+Error) → doc-only note
    "#/components/responses/Conflict409",          # in-handler 409 + offline reuse → doc-only note
    "#/components/securitySchemes/OAuth2",         # FALSE-orphan (top-level security:)
}

# Nhóm component trong components.* được tính là "defined" (đối chiếu orphan).
_COMPONENT_GROUPS = (
    "parameters", "headers", "schemas", "responses",
    "securitySchemes", "requestBodies", "examples", "links", "callbacks",
)


def _load_spec() -> dict:
    return yaml.safe_load(_MOBILE_YAML.read_text(encoding="utf-8"))


def _collect_refs(spec: dict) -> list[str]:
    """Walk toàn spec, trả MỌI giá trị `$ref` (string) — stdlib, no lib ngoài."""
    out: list[str] = []

    def _walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "$ref" and isinstance(v, str):
                    out.append(v)
                else:
                    _walk(v)
        elif isinstance(node, list):
            for v in node:
                _walk(v)

    _walk(spec)
    return out


def _resolve_pointer(ptr: str, root: dict) -> bool:
    """Resolve local JSON-pointer `#/...` về node trong root. True nếu resolve được."""
    if not ptr.startswith("#/"):
        return False  # non-local ref (URL/file) — KHÔNG hợp lệ cho mobile yaml self-contained
    cur = root
    for raw in ptr[2:].split("/"):
        part = raw.replace("~1", "/").replace("~0", "~")  # RFC 6901 unescape
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            return False
    return True


def _defined_component_pointers(spec: dict) -> set[str]:
    comps = spec.get("components") or {}
    out: set[str] = set()
    for group in _COMPONENT_GROUPS:
        for name in (comps.get(group) or {}):
            out.add(f"#/components/{group}/{name}")
    return out


def _iter_operations(spec: dict):
    """Yield (path, verb, operation_dict) cho mọi HTTP-operation trong paths."""
    for path, item in (spec.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        for verb, op in item.items():
            if verb in _HTTP_VERBS and isinstance(op, dict):
                yield path, verb, op


def _200_schema(resp: dict) -> dict:
    """Trả schema của response 200 (application/json) — inline (KHÔNG $ref response component)."""
    r200 = resp.get("200") or {}
    return (((r200.get("content") or {}).get("application/json") or {}).get("schema") or {})


def _assert_200_oneof_closed_distinct(tc, resp: dict, created_envelope_ref: str, label: str) -> dict:
    """G-OAS-NO-BOOL-DISC (§5c, Self-Correction R1) — assert 200 = inline oneOf [<CreatedEnvelope>,
    Error] máy-phân-biệt bằng CLOSED-SCHEMA + disjoint required-set, KHÔNG discriminator boolean.

    LÝ DO ĐỔI (vs guard cũ _assert_200_oneof_discriminator): OAS 3.x yêu cầu discriminator.propertyName
    trỏ property type STRING; `success` là BOOLEAN ⇒ discriminator illegal (generator Dart/Kotlin/Java
    drop nó + fallback try-each-branch HOẶC sinh switch(string)==boolean → deser-fail). Quyết-định BA
    = cách B (bỏ discriminator, mirror R2 403-fix): 2 nhánh closed (additionalProperties:false) +
    disjoint required-set ⇒ codegen route ĐÚNG. Guard NAY:
      (1) 200 = inline oneOf ĐÚNG 2 nhánh [Created, Error] (KHÔNG single $ref response component);
      (2) KHÔNG còn block `discriminator` trong schema 200 (chống tái phát boolean-discriminator illegal).
    Client route theo body.success/body.http_status (in-handler error arrive HTTP-200 body §5). Trả
    schema200 để caller assert thêm. (Structural-distinctness của 2 nhánh = TC-18c kiểm @component.)
    """
    schema200 = _200_schema(resp)
    # KHÔNG còn single $ref Created response component (đã inline-hoá thành oneOf).
    tc.assertNotIn(
        "$ref", resp.get("200") or {},
        f"{label} 200 KHÔNG được là single $ref response component — PHẢI inline oneOf [Created, Error].",
    )
    one_of = schema200.get("oneOf") or []
    refs = [b.get("$ref") for b in one_of if isinstance(b, dict)]
    tc.assertEqual(
        len(one_of), 2,
        f"{label} 200 PHẢI oneOf ĐÚNG 2 nhánh [Created, Error] (KHÔNG single $ref): {refs}",
    )
    tc.assertIn(
        created_envelope_ref, refs,
        f"{label} 200 oneOf PHẢI chứa nhánh Created {created_envelope_ref}: {refs}",
    )
    tc.assertIn(
        _ERROR_SCHEMA_REF, refs,
        f"{label} 200 oneOf PHẢI chứa nhánh Error {_ERROR_SCHEMA_REF} (in-handler business error): {refs}",
    )
    # G-OAS-NO-BOOL-DISC — KHÔNG discriminator (success=boolean → discriminator illegal OAS 3.x).
    tc.assertNotIn(
        "discriminator", schema200,
        f"{label} 200 KHÔNG được có `discriminator` — `success` là BOOLEAN, discriminator OAS 3.x "
        "yêu cầu propertyName trỏ property STRING (illegal → generator drop/deser-fail). 2 nhánh "
        "máy-phân-biệt bằng closed-schema + disjoint required-set (§5c). Route theo body.success/http_status.",
    )
    return schema200


class TestMobileOASLint(unittest.TestCase):
    """Lint guard contract-identity cho mobile OpenAPI (no DB)."""

    @classmethod
    def setUpClass(cls):
        cls.assertTrueExists = _MOBILE_YAML.exists()
        cls.spec = _load_spec() if cls.assertTrueExists else None

    def test_mob_oas_01_lint_and_frozen_meta(self):
        """yaml hợp lệ + openapi 3.0.3 + info title/version đóng băng + đúng 15 path."""
        self.assertTrue(_MOBILE_YAML.exists(), f"Thiếu file: {_MOBILE_YAML}")
        spec = self.spec
        self.assertIsInstance(spec, dict, "safe_load phải trả dict")
        self.assertEqual(spec.get("openapi"), "3.0.3")
        info = spec.get("info") or {}
        self.assertEqual(info.get("title"), "AssetCore Mobile API")
        self.assertEqual(info.get("version"), "0.1.0-skeleton")
        self.assertEqual(len(spec.get("paths") or {}), 15, "Phải đúng 15 path mobile MVP")

    def test_mob_oas_02_all_paths_have_operation_id(self):
        """15/15 path-operation CÓ operationId — 0 None."""
        missing = [
            f"{verb.upper()} {path}"
            for path, verb, op in _iter_operations(self.spec)
            if not op.get("operationId")
        ]
        self.assertEqual(missing, [], f"Path thiếu operationId: {missing}")
        ids = [op["operationId"] for _, _, op in _iter_operations(self.spec)]
        self.assertEqual(len(ids), 15, "Phải đúng 15 operationId")

    def test_mob_oas_03_operation_id_unique(self):
        """operationId DUY NHẤT toàn file: len(set)==len(list)==15."""
        ids = [op["operationId"] for _, _, op in _iter_operations(self.spec)]
        dupes = sorted({x for x in ids if ids.count(x) > 1})
        self.assertEqual(dupes, [], f"operationId trùng: {dupes}")
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(set(ids)), 15)

    def test_mob_oas_04_operation_id_camel_case(self):
        """Mọi operationId khớp regex camelCase verbNoun (^[a-z][a-zA-Z0-9]*$)."""
        bad = [
            op["operationId"]
            for _, _, op in _iter_operations(self.spec)
            if not _CAMEL_RE.match(op.get("operationId", ""))
        ]
        self.assertEqual(bad, [], f"operationId không camelCase: {bad}")

    def test_mob_oas_05_operation_id_matches_convention(self):
        """operationId KHỚP map convention SSoT (dotted-path tail → camelCase, verb-first oauth)."""
        actual = {path: (verb, op.get("operationId")) for path, verb, op in _iter_operations(self.spec)}
        # mọi path mong đợi tồn tại + opId khớp
        for path, (exp_verb, exp_id) in _EXPECTED.items():
            self.assertIn(path, actual, f"Thiếu path mong đợi: {path}")
            act_verb, act_id = actual[path]
            self.assertEqual(act_verb, exp_verb, f"Verb lệch ở {path}")
            self.assertEqual(act_id, exp_id, f"operationId lệch convention ở {path}")
        # không có path lạ ngoài map (chống thêm path không theo luật ở A10)
        extra = set(actual) - set(_EXPECTED)
        self.assertEqual(extra, set(), f"Path ngoài convention map (Phase C cần cập nhật map): {extra}")

    def test_mob_oas_06_device_token_names_frozen(self):
        """2 device-token GIỮ NGUYÊN TÊN (chốt A5) — chống drift client đã sinh."""
        actual = {path: op.get("operationId") for path, _, op in _iter_operations(self.spec)}
        for path, frozen_id in _DEVICE_TOKEN_FROZEN.items():
            self.assertEqual(
                actual.get(path), frozen_id,
                f"device-token operationId ĐỔI TÊN (cấm — A5): {path} -> {actual.get(path)}",
            )

    def test_mob_oas_08_no_orphan_nullable(self):
        """LINT-A10-08: KHÔNG có `nullable` mồ côi (thiếu sibling `type`) trong components.schemas.

        OpenAPI 3.0.3 rule `nullable-type-sibling` (redocly/swagger-parser): `nullable` CHỈ
        hợp lệ khi schema CÓ `type`. `nullable` mồ côi = lint-ERROR → fail CI gate codegen
        của repo native + sinh field generic không nhất quán. Đây là spec-correctness của
        component A3 (KHÔNG phải STUB/Phase C) — guard chống tái xuất. Phát hiện live khi
        đóng vai mobile-dev chạy `redocly lint` (2026-06-09)."""
        offenders = []

        def _walk(node, where):
            if isinstance(node, dict):
                if "nullable" in node and "type" not in node:
                    offenders.append(where)
                for k, v in node.items():
                    _walk(v, f"{where}.{k}")
            elif isinstance(node, list):
                for i, v in enumerate(node):
                    _walk(v, f"{where}[{i}]")

        _walk((self.spec.get("components") or {}).get("schemas") or {}, "components.schemas")
        self.assertEqual(
            offenders, [],
            f"`nullable` mồ côi (thiếu sibling `type`) — vi phạm OpenAPI 3.0.3: {offenders}",
        )

    def test_mob_oas_07_business_and_list_paths_still_stub(self):
        """STUB-A10-07: CHỈ 2 device-token còn STUB (R4 — 4 typed read/create rời).

        Sau R4 §8.7: 3 typed read (resolveQrToken/getAssetScanInfo/getAsset) + createPmWorkOrder rời
        _STUB_PATHS (typed response GROUNDED service sig — TC-MOB-OAS-20). CHỈ CÒN 2 device-token
        (register/unregister) STUB vì handler CHƯA tồn tại @source (ADR-MOBILE-001 h, BA gate KHÔNG
        bịa endpoint). 2 device-token phải KHÔNG có requestBody + response 200 vẫn trỏ
        #/components/responses/Stub. Chống bồi schema lén: report/createRepair/createCal/3-list rời
        STUB ở Phase-C; typed reads + createPm rời ở R4 — 4 còn-lại-cũ NAY xuống còn 2 device-token.
        """
        ops = {path: op for path, _, op in _iter_operations(self.spec)}
        # report + createRepair + createCalibration + 3 list KHÔNG còn trong _STUB_PATHS (đã rời — Phase-C).
        self.assertNotIn(
            _REPORT_INCIDENT_PATH, _STUB_PATHS,
            "reportIncident phải RỜI _STUB_PATHS (Phase-C requestBody) — nếu còn = guard sai.",
        )
        self.assertNotIn(
            _REPAIR_CREATE_PATH, _STUB_PATHS,
            "createRepairWorkOrder phải RỜI _STUB_PATHS (C-REQBODY-CREATEREPAIR) — nếu còn = guard sai.",
        )
        self.assertNotIn(
            _CAL_CREATE_PATH, _STUB_PATHS,
            "createCalibration phải RỜI _STUB_PATHS (C-REQBODY-CREATECAL) — nếu còn = guard sai.",
        )
        for lp in _LIST_PATHS:
            self.assertNotIn(
                lp, _STUB_PATHS,
                f"{lp} phải RỜI _STUB_PATHS (Phase-C list-read) — nếu còn = guard sai.",
            )
        # R4 §8.7 — 3 typed read + createPm RỜI _STUB_PATHS (typed response GROUNDED).
        for tp in (_TYPED_READ_PATHS | {_CREATE_PM_PATH}):
            self.assertNotIn(
                tp, _STUB_PATHS,
                f"{tp} phải RỜI _STUB_PATHS (R4 §8.7 typed response) — nếu còn = guard sai.",
            )
        # Sau R4 _STUB_PATHS CHỈ CÒN 2 device-token (handler chưa impl, ROADMAP).
        self.assertEqual(
            _STUB_PATHS, set(_DEVICE_TOKEN_FROZEN),
            "Sau R4 _STUB_PATHS PHẢI = 2 device-token (BE chưa impl, ADR-MOBILE-001 h).",
        )
        for path in _STUB_PATHS:
            self.assertIn(path, ops, f"Thiếu STUB path: {path}")
            op = ops[path]
            self.assertNotIn(
                "requestBody", op,
                f"STUB path đã bồi requestBody (đó là Phase C, KHÔNG phải A10): {path}",
            )
            ref = ((op.get("responses") or {}).get("200") or {}).get("$ref")
            self.assertEqual(
                ref, "#/components/responses/Stub",
                f"STUB path 200 KHÔNG còn trỏ Stub (schema chi tiết = Phase C): {path} -> {ref}",
            )

    def test_mob_oas_09_no_dangling_refs(self):
        """A12 — 0 dangling `$ref`: MỌI `$ref` resolve về node TỒN TẠI (codegen crash nếu dangling).

        Walk toàn yaml bằng STDLIB (KHÔNG cần openapi_spec_validator/prance — 2 lib không cài).
        Dangling = `openapi-generator` crash / sinh model rỗng → hard-fail. SSoT: 04 §8.2.
        """
        refs = _collect_refs(self.spec)
        self.assertTrue(refs, "Phải có ít nhất 1 $ref trong yaml (sanity).")
        dangling = sorted({r for r in refs if not _resolve_pointer(r, self.spec)})
        self.assertEqual(
            dangling, [],
            f"$ref dangling (trỏ node KHÔNG tồn tại — codegen crash): {dangling}",
        )

    def test_mob_oas_10_orphan_components_within_reserved_allow_list(self):
        """A12 — orphan-component (defined-không-`$ref`'d) PHẢI ⊆ allow-list RESERVED (04 §8.2).

        - Orphan NGOÀI allow-list = FAIL (dead contract-surface lén lút).
        - Mục allow-list KHÔNG-còn-orphan (đã wire vào path) = FAIL (allow-list stale → gỡ ở §8.2).
        - OAuth2 BẮT BUỘC là orphan (false-orphan dùng qua top-level `security:`) — KHÔNG forbid naive.
        `_RESERVED_ORPHANS` phản chiếu bảng RESERVED 04 §8.2 (SSoT) 1:1.
        """
        defined = _defined_component_pointers(self.spec)
        referenced = set(_collect_refs(self.spec))
        orphans = defined - referenced

        # (a) Không orphan NGOÀI allow-list (chống dead surface lén).
        unexpected = sorted(orphans - _RESERVED_ORPHANS)
        self.assertEqual(
            unexpected, [],
            f"Orphan-component NGOÀI allow-list RESERVED (cập nhật 04 §8.2 nếu cố ý): {unexpected}",
        )
        # (b) Allow-list KHÔNG có mục stale (đã wire → hết orphan → phải gỡ khỏi §8.2 + set này).
        stale = sorted(_RESERVED_ORPHANS - orphans)
        self.assertEqual(
            stale, [],
            f"Mục allow-list KHÔNG-còn-orphan (đã wire — gỡ khỏi 04 §8.2 + _RESERVED_ORPHANS): {stale}",
        )
        # (c) OAuth2 = false-orphan: PHẢI nằm trong orphan (dùng qua security: keyword, KHÔNG $ref).
        self.assertIn(
            "#/components/securitySchemes/OAuth2", orphans,
            "OAuth2 phải là orphan (false-orphan dùng qua top-level `security:`) — nếu hết orphan,"
            " ai đó đã thêm `$ref` vào OAuth2 (sai cách dùng securityScheme).",
        )
        # (d) Mọi mục allow-list được resolve được (sanity — pointer hợp lệ, không typo).
        bad_ptr = sorted(p for p in _RESERVED_ORPHANS if not _resolve_pointer(p, self.spec))
        self.assertEqual(
            bad_ptr, [],
            f"Allow-list chứa pointer KHÔNG resolve (typo trong _RESERVED_ORPHANS / 04 §8.2): {bad_ptr}",
        )

    def test_mob_oas_11_error_response_coverage(self):
        """A13 — ERROR-RESPONSE coverage: 401 lên MỌI path MVP + 429 ĐÚNG 2 path @rate_limit.

        Biến failure-mode prose (04 §4 row 4 / §5 line 143,146-147 / ADR-MOBILE-001 e) thành
        contract máy-đọc CHẠY ĐƯỢC:
          (1) MỌI path MVP (10 nghiệp vụ STUB + 2 device-token) declare `401` $ref
              Unauthorized401 (bearer hết hạn → refresh/re-auth).
          (2) ĐÚNG 2 path @rate_limit THẬT (resolve_qr_token imm00.py:311 + get_asset_scan_info
              imm00.py:354) declare `429` $ref RateLimited429; KHÔNG path nào khác (wire chỗ
              khác = bịa hợp đồng — chỉ 2 GET này có @rate_limit ⇒ 429 = sự-thật-runtime).
          (3) 3 auth path Frappe-core (authorize/get_token/revoke) KHÔNG declare 429 (KHÔNG
              @rate_limit ở core — 08 §1 T1) và GIỮ NGUYÊN status hiện có (302/200).
          (4) G-OAS-STATUSLINE — 0 path declare 404/422/409 status-line key (in-handler business
              error arrive HTTP-200+Error → gom nhánh Error của 200-oneOf, route theo
              body.http_status). NotFound404/Unprocessable422/Conflict409 = RESERVED orphan
              (forward-reserve doc-intent — TC-MOB-OAS-10 đã canh). 3 create status-set=[200,401,403].
          (5) 3 auth path Frappe-core GIỮ NGUYÊN status (authorize=302, get_token/revoke=200)
              + KHÔNG bị thêm 401 (anti-regress — A13 KHÔNG đụng token-issuance flow).
        """
        ops = {path: op for path, _, op in _iter_operations(self.spec)}

        # (1) MỌI path MVP có 401 $ref Unauthorized401.
        _U401 = "#/components/responses/Unauthorized401"
        missing_401 = sorted(
            path for path in _PATHS_REQUIRE_401
            if ((ops.get(path) or {}).get("responses") or {}).get("401", {}).get("$ref") != _U401
        )
        self.assertEqual(
            missing_401, [],
            f"Path MVP THIẾU 401→Unauthorized401 (bearer hết hạn → refresh, 04 §4/§5): {missing_401}",
        )

        # (2a) ĐÚNG 2 path @rate_limit có 429 $ref RateLimited429.
        _R429 = "#/components/responses/RateLimited429"
        missing_429 = sorted(
            path for path in _PATHS_REQUIRE_429
            if ((ops.get(path) or {}).get("responses") or {}).get("429", {}).get("$ref") != _R429
        )
        self.assertEqual(
            missing_429, [],
            f"Path @rate_limit THIẾU 429→RateLimited429 (imm00.py:311/354): {missing_429}",
        )
        # (2b) KHÔNG path NÀO KHÁC declare 429 (chống bịa hợp đồng — chỉ 2 GET có @rate_limit thật).
        extra_429 = sorted(
            path for path, op in ops.items()
            if "429" in (op.get("responses") or {}) and path not in _PATHS_REQUIRE_429
        )
        self.assertEqual(
            extra_429, [],
            f"Path KHÔNG có @rate_limit @source mà declare 429 (bịa hợp đồng — gỡ): {extra_429}",
        )

        # (3) 3 auth path KHÔNG declare 429 (KHÔNG @rate_limit core — 08 §1 T1).
        auth_with_429 = sorted(
            path for path in _AUTH_PATHS
            if "429" in ((ops.get(path) or {}).get("responses") or {})
        )
        self.assertEqual(
            auth_with_429, [],
            f"Auth path (Frappe core, KHÔNG @rate_limit) KHÔNG được declare 429: {auth_with_429}",
        )

        # (4) G-OAS-STATUSLINE (P1 contract-correctness) — in-handler business error (404/422/409)
        #     arrive HTTP status-line 200 + Error body (quirk §5: _err response.py:95-154 +
        #     handle() return dict api_handler.py:48 + hooks.py:405 no after_request ⇒ status-line
        #     KHÔNG BAO GIỜ set cho in-handler error). ⇒ keying 404/422/409 dưới HTTP-code
        #     response-key = DEAD-DESER (codegen route-by-status-line KHÔNG bao giờ khớp). G-OAS-
        #     STATUSLINE gỡ 3 status-line key khỏi 3 create path + gom lỗi vào nhánh Error của
        #     200-oneOf-discriminator. ⇒ KHÔNG path NÀO declare 404/422/409 status-line key.
        for dead_key in ("404", "422", "409"):
            extra = sorted(
                f"{dead_key} @ {path}"
                for path, op in ops.items()
                if dead_key in (op.get("responses") or {})
            )
            self.assertEqual(
                extra, [],
                f"{dead_key} KHÔNG được là status-line key ở BẤT KỲ path nào — in-handler business "
                f"error arrive HTTP-200+Error (route theo body.http_status). Dead-deser nếu giữ: {extra}",
            )
        # 3 create path: 404/422/409 surface qua nhánh Error của 200-oneOf (đã canh chi tiết
        #   discriminator + envelope ở TC-MOB-OAS-18). Ở đây canh status-set TỐI GIẢN = [200,401,403].
        for path, status_set in (
            (_REPORT_INCIDENT_PATH, _REPORT_INCIDENT_STATUS_SET),
            (_REPAIR_CREATE_PATH, _REPAIR_CREATE_STATUS_SET),
            (_CAL_CREATE_PATH, _CAL_CREATE_STATUS_SET),
        ):
            resp = (ops.get(path) or {}).get("responses") or {}
            self.assertEqual(
                sorted(resp.keys()), status_set,
                f"{path}: status-set PHẢI = {status_set} (G-OAS-STATUSLINE — in-handler error gom 200-Error).",
            )

        # (5) 3 auth path GIỮ status Frappe-core + KHÔNG bị thêm 401 (anti-regress).
        #     ADR-MOBILE-001 (e): bearer-gated chỉ áp endpoint nghiệp vụ; 3 auth path là
        #     token-issuance flow (chưa-có-bearer-khi-gọi) ⇒ 401 vô nghĩa ở đây.
        #     B1 (Phase B): get_token NAY có thêm '400' (OAuthError400 grant-fail PASSTHROUGH —
        #     oauth2.py:132-135). Status set get_token = {200, 400}. authorize=302, revoke=200
        #     GIỮ NGUYÊN. Chi tiết hợp đồng 200/400-body = class TestMobileOAuthToken (B1).
        _AUTH_EXPECTED_STATUS = {
            "/api/method/frappe.integrations.oauth2.authorize": {"302"},
            "/api/method/frappe.integrations.oauth2.get_token": {"200", "400"},
            "/api/method/frappe.integrations.oauth2.revoke_token": {"200"},
        }
        auth_status_drift = sorted(
            f"{path} status={sorted((ops.get(path) or {}).get('responses', {}).keys())} (mong đợi {sorted(want)})"
            for path, want in _AUTH_EXPECTED_STATUS.items()
            if set(((ops.get(path) or {}).get("responses") or {}).keys()) != want
        )
        self.assertEqual(
            auth_status_drift, [],
            f"Auth path (Frappe core) DRIFT status — chỉ get_token thêm 400 (B1): {auth_status_drift}",
        )
        # (5b) get_token 400 PHẢI là OAuthError400 (passthrough), KHÔNG Error/401/429 (anti-leak B1).
        gt_400 = ((ops.get(_GET_TOKEN_PATH) or {}).get("responses") or {}).get("400", {}).get("$ref")
        self.assertEqual(
            gt_400, _OAUTH_ERROR_RESPONSE_REF,
            f"get_token '400' phải $ref OAuthError400 (B1 passthrough), got {gt_400}",
        )

    def test_mob_oas_12_error_status_class_401_403_split(self):
        """A16 — TÁCH status-class 401 (expired-bearer) vs 403 (guest/no-token/thiếu-cap) + body raw.

        Đóng băng hợp đồng error-status A16 thành guard chạy được (chống regress âm thầm):
          (a) MỌI 12 path MVP (10 business STUB + 2 device-token) declare `403`. 11 path →
              `Forbidden` (single FrappeRawError). G-REQBODY EXEMPT: report_incident → 403 =
              `ReportIncidentForbidden` (DUAL-SHAPE oneOf Error|FrappeRawError — in-handler cap-403
              HTTP-200+Error imm12.py:96 ≠ dispatcher-403 HTTP-403+FrappeRawError __init__.py:876).
              Device-token = bearer-gated self-service (06 §2.3, KHÔNG allow_guest) ⇒ guest/no-token
              cũng 403 (PermissionError, is_whitelisted __init__.py:876). ĐỐI XỨNG: tập 403 == tập 401
              (report_incident VẪN declare 403, chỉ KHÁC shape ⇒ symmetry 12==12 BẤT BIẾN).
          (b) 3 response pre-handler (Unauthorized401/Forbidden/RateLimited429) $ref
              schemas/FrappeRawError (raw Frappe body THẬT), KHÔNG schemas/Error (business
              in-handler envelope). Repoint A16 → codegen sinh model KHỚP body runtime
              (KHÔNG deser-fail). schemas/FrappeRawError component TỒN TẠI + keys khớp source.
          (c) 3 auth path Frappe-core (authorize/get_token/revoke) KHÔNG declare 403
              (302/200/400 — KHÔNG đụng token-issuance flow ở A16).

        Status-class semantics (verify @source frappe/exceptions.py):
          401 = AuthenticationError (:26-27, http_status_code=401; raise auth.py:630) —
                Authorization header CÓ nhưng bearer hết-hạn/invalid + session=Guest.
          403 = PermissionError (:34-35, http_status_code=403; raise __init__.py:876) —
                guest/no-token HOẶC method thiếu permission/capability.
          429 = TooManyRequestsError (:80, http_status_code=429) — @rate_limit trip.
        """
        ops = {path: op for path, _, op in _iter_operations(self.spec)}
        _FORBIDDEN = "#/components/responses/Forbidden"

        # (a) 11/12 path MVP có 403 $ref Forbidden. G-REQBODY EXEMPT report_incident (403 dual-shape
        #     = ReportIncidentForbidden, KHÁC Forbidden) — kiểm riêng bên dưới.
        missing_403 = sorted(
            path for path in (_PATHS_REQUIRE_403 - {_REPORT_INCIDENT_PATH})
            if ((ops.get(path) or {}).get("responses") or {}).get("403", {}).get("$ref") != _FORBIDDEN
        )
        self.assertEqual(
            missing_403, [],
            f"Path MVP (trừ report_incident) THIẾU 403→Forbidden (guest/no-token/thiếu-cap, __init__.py:876): {missing_403}",
        )
        # (a') G-REQBODY — report_incident 403 = ReportIncidentForbidden (DUAL-SHAPE oneOf
        #     Error|FrappeRawError). KHÁC Forbidden (single FrappeRawError) — in-handler cap-403
        #     (HTTP-200+Error imm12.py:96) ≠ dispatcher-403 (HTTP-403+FrappeRawError __init__.py:876).
        rpt_403_ref = ((ops.get(_REPORT_INCIDENT_PATH) or {}).get("responses") or {}).get("403", {}).get("$ref")
        self.assertEqual(
            rpt_403_ref, _REPORT_INCIDENT_FORBIDDEN_RESP_REF,
            f"report_incident 403 PHẢI = ReportIncidentForbidden (dual-shape, G-REQBODY), got {rpt_403_ref}",
        )
        rifb = ((self.spec.get("components") or {}).get("responses") or {}).get("ReportIncidentForbidden") or {}
        one_of = (((rifb.get("content") or {}).get("application/json") or {}).get("schema") or {}).get("oneOf") or []
        one_of_refs = {m.get("$ref") for m in one_of if isinstance(m, dict)}
        self.assertEqual(
            one_of_refs, {_ERROR_ENVELOPE_SCHEMA_REF, _FRAPPE_RAW_ERROR_SCHEMA_REF},
            "ReportIncidentForbidden PHẢI oneOf [Error, FrappeRawError] (BOTH shape 403 báo hỏng).",
        )
        # ĐỐI XỨNG: tập path-403 == tập path-401 (12==12). 403 ngoài _PATHS_REQUIRE_403 = bịa.
        paths_with_403 = sorted(
            path for path, op in ops.items() if "403" in (op.get("responses") or {})
        )
        self.assertEqual(
            paths_with_403, sorted(_PATHS_REQUIRE_403),
            f"Tập path declare 403 phải == 12 path MVP (đối xứng 401): {paths_with_403}",
        )
        paths_with_401 = {
            path for path, op in ops.items() if "401" in (op.get("responses") or {})
        }
        self.assertEqual(
            paths_with_401, set(_PATHS_REQUIRE_403),
            "Tập path declare 401 phải == tập path declare 403 (12==12 đối xứng A16).",
        )

        # (b) 3 response pre-handler trỏ FrappeRawError (KHÔNG Error envelope).
        resps = (self.spec.get("components") or {}).get("responses") or {}
        wrong_ref = []
        for name in _PREHANDLER_RAW_RESPONSES:
            ref = (((resps.get(name) or {}).get("content") or {})
                   .get("application/json", {}).get("schema", {}).get("$ref"))
            if ref != _FRAPPE_RAW_ERROR_SCHEMA_REF:
                wrong_ref.append(f"{name} -> {ref}")
        self.assertEqual(
            wrong_ref, [],
            "Pre-handler response (401/403/429) PHẢI $ref FrappeRawError, KHÔNG Error "
            f"(A16 — body raw Frappe, codegen-khớp): {wrong_ref}",
        )
        # KHÔNG response pre-handler nào còn trỏ Error envelope (anti-regress A16).
        still_error = [
            name for name in _PREHANDLER_RAW_RESPONSES
            if (((resps.get(name) or {}).get("content") or {})
                .get("application/json", {}).get("schema", {}).get("$ref")) == _ERROR_ENVELOPE_SCHEMA_REF
        ]
        self.assertEqual(
            still_error, [],
            f"Pre-handler response KHÔNG được còn trỏ Error envelope (A16 repoint): {still_error}",
        )

        # (b') schema FrappeRawError tồn tại + keys/required khớp source-characterized.
        schemas = (self.spec.get("components") or {}).get("schemas") or {}
        fre = schemas.get("FrappeRawError") or {}
        self.assertTrue(fre, "Thiếu schema FrappeRawError (A16).")
        fre_props = set((fre.get("properties") or {}).keys())
        self.assertEqual(
            fre_props, _FRAPPE_RAW_ERROR_KEYS_ALL,
            f"FrappeRawError props lệch source ({_FRAPPE_RAW_ERROR_KEYS_ALL}): {fre_props}",
        )
        self.assertEqual(
            set(fre.get("required") or []), _FRAPPE_RAW_ERROR_REQUIRED,
            "FrappeRawError required phải = {'exc_type'} (response.py:46 LUÔN set; 3 field còn lại gated).",
        )
        # DISTINCT vs business Error envelope: KHÔNG mang success/code/http_status.
        leaked = fre_props & _BUSINESS_ENVELOPE_KEYS
        self.assertEqual(
            leaked, set(),
            f"FrappeRawError KHÔNG được trùng key Error envelope (phải DISTINCT raw): {leaked}",
        )

        # (c) 3 auth path Frappe-core KHÔNG declare 403 (A16 KHÔNG đụng token-issuance flow).
        auth_with_403 = sorted(
            path for path in _AUTH_PATHS
            if "403" in ((ops.get(path) or {}).get("responses") or {})
        )
        self.assertEqual(
            auth_with_403, [],
            f"Auth path (Frappe core, 302/200/400) KHÔNG được declare 403 (A16): {auth_with_403}",
        )


class TestMobileOAuthToken(unittest.TestCase):
    """B1 — AUTH-SECTION token-endpoint RESPONSE contract (PASSTHROUGH OAuthlib).

    Khoá hợp đồng RESPONSE của 2 token-endpoint (get_token / revoke_token) thành guard
    chạy được. KHÔNG đụng operationId / path-string (FROZEN). SOURCE-CHARACTERIZED:
      - getOAuthToken 200-body = {access_token, expires_in, token_type, scope?, refresh_token?}
        (oauthlib tokens.py:309-326; set oauth2.py:137).
      - getOAuthToken 400-body = OAuthError400 (twotuples errors.py:80-88 / oauth.py:567-573).
      - revokeOAuthToken 200-body = empty object (RFC 7009 luôn 200 — oauth2.py:158-159).
    PASSTHROUGH (Frappe core SSoT) — KHÁC AssetCore Error envelope. DECISION: 03 §2 + 04 §5b.
    """

    @classmethod
    def setUpClass(cls):
        cls.spec = _load_spec() if _MOBILE_YAML.exists() else None

    def _op(self, path, verb):
        return ((self.spec.get("paths") or {}).get(path) or {}).get(verb) or {}

    def test_mob_oauth_token_01_get_token_400_wired_to_oauth_error(self):
        """TC-MOB-OAUTH-TOKEN-01: getOAuthToken declare '400'→OAuthError400 (grant fail).

        wrong PKCE verifier / expired code / invalid_grant refresh → 400 PASSTHROUGH
        (oauth2.py:132-135 → oauthlib errors.py:80-88). Wire ĐÚNG 1 path = getOAuthToken.
        """
        op = self._op(_GET_TOKEN_PATH, "post")
        self.assertEqual(op.get("operationId"), "getOAuthToken", "operationId getOAuthToken FROZEN")
        ref = ((op.get("responses") or {}).get("400") or {}).get("$ref")
        self.assertEqual(
            ref, _OAUTH_ERROR_RESPONSE_REF,
            f"getOAuthToken '400' phải $ref OAuthError400 (grant fail passthrough), got {ref}",
        )

    def test_mob_oauth_token_02_oauth_error_wired_exactly_one_path(self):
        """TC-MOB-OAUTH-TOKEN-02: OAuthError400 wire ĐÚNG 1 path (getOAuthToken) — 0 leak.

        0 path BUSINESS (10 nghiệp vụ STUB + 2 device-token) nhận OAuthError400 (chống leak
        nhầm auth-error shape vào business-path — business dùng Error envelope/FrappeRawError).
        authorize/revoke KHÔNG có 400.
        """
        carriers = sorted(
            f"{verb.upper()} {path}"
            for path, verb, op in _iter_operations(self.spec)
            for r in (op.get("responses") or {}).values()
            if isinstance(r, dict) and r.get("$ref") == _OAUTH_ERROR_RESPONSE_REF
        )
        self.assertEqual(
            carriers, ["POST " + _GET_TOKEN_PATH],
            f"OAuthError400 phải wire ĐÚNG 1 path (getOAuthToken); thấy: {carriers}",
        )
        # anti-leak: KHÔNG path business declare 400 NÀO (chưa Phase C).
        business_400 = sorted(
            path for path in _BUSINESS_PATHS
            if "400" in ((self._op(path, "get") or self._op(path, "post")).get("responses") or {})
        )
        self.assertEqual(
            business_400, [],
            f"Path business KHÔNG được declare 400 ở B1 (anti-leak OAuthError400): {business_400}",
        )

    def test_mob_oauth_token_03_oauth_error_schema_keys_match_source(self):
        """TC-MOB-OAUTH-TOKEN-03: OAuthError400 schema-keys KHỚP source-characterized.

        Union 2 đường provider: oauthlib twotuples {error, error_description?, error_uri?}
        (errors.py:80-88) + generate_json_error_response {description, status_code, error}
        (oauth.py:567-573). `error` required (key chung). DISTINCT vs Error envelope.
        """
        schema = (((self.spec.get("components") or {}).get("schemas") or {})
                  .get("OAuthError400") or {})
        self.assertTrue(schema, "Thiếu schema OAuthError400")
        props = set((schema.get("properties") or {}).keys())
        self.assertEqual(
            props, _OAUTH_ERROR_SCHEMA_KEYS_ALL,
            f"OAuthError400 props lệch source ({_OAUTH_ERROR_SCHEMA_KEYS_ALL}): {props}",
        )
        self.assertEqual(
            set(schema.get("required") or []), _OAUTH_ERROR_SCHEMA_REQUIRED,
            "OAuthError400 required phải = {'error'} (key chung 2 đường — oauthlib + generate_json).",
        )
        # DISTINCT vs business Error envelope: KHÔNG mang success/code/http_status.
        leaked = props & _BUSINESS_ENVELOPE_KEYS
        self.assertEqual(
            leaked, set(),
            f"OAuthError400 KHÔNG được trùng key Error envelope (phải DISTINCT): {leaked}",
        )
        # Response OAuthError400 trỏ đúng schema.
        resp_schema_ref = ((((self.spec.get("components") or {}).get("responses") or {})
                            .get("OAuthError400") or {}).get("content") or {}
                           ).get("application/json", {}).get("schema", {}).get("$ref")
        self.assertEqual(
            resp_schema_ref, _OAUTH_ERROR_SCHEMA_REF,
            f"Response OAuthError400 phải $ref schema OAuthError400, got {resp_schema_ref}",
        )

    def test_mob_oauth_token_04_get_token_200_body_keys_match_source(self):
        """TC-MOB-OAUTH-TOKEN-04: getOAuthToken 200-body keys KHỚP source (OAuthlib passthrough).

        keys @source = {access_token, expires_in, token_type} required + {scope, refresh_token}
        optional (tokens.py:309-326). PASSTHROUGH — KHÔNG có success/data/code (Error envelope).
        """
        op = self._op(_GET_TOKEN_PATH, "post")
        schema = ((((op.get("responses") or {}).get("200") or {}).get("content") or {})
                  .get("application/json", {}).get("schema") or {})
        props = set((schema.get("properties") or {}).keys())
        self.assertEqual(
            props, _GET_TOKEN_200_KEYS_ALL,
            f"getOAuthToken 200 props lệch source-characterized ({_GET_TOKEN_200_KEYS_ALL}): {props}",
        )
        self.assertEqual(
            set(schema.get("required") or []), _GET_TOKEN_200_KEYS_REQUIRED,
            f"getOAuthToken 200 required phải = {_GET_TOKEN_200_KEYS_REQUIRED} (tokens.py:309-313).",
        )
        # PASSTHROUGH: KHÔNG mang envelope-shape (success/data) — distinct với business 200.
        self.assertEqual(
            props & {"success", "data"}, set(),
            "getOAuthToken 200 là PASSTHROUGH OAuthlib — KHÔNG được bọc envelope {success,data}.",
        )

    def test_mob_oauth_token_05_revoke_200_empty_authorize_302_no_400(self):
        """TC-MOB-OAUTH-TOKEN-05: revoke 200 empty-body (RFC 7009) + authorize 302; cả 2 KHÔNG 400.

        revoke_token LUÔN 200 body rỗng (oauth2.py:158-159) → schema empty object,
        additionalProperties:false. authorize = 302-only. KHÔNG path nào trong 2 cái có 400
        (anti-regress: B1 wire 400 CHỈ getOAuthToken).
        """
        # revoke: status 200 (chỉ), body empty object.
        revoke = self._op(_REVOKE_TOKEN_PATH, "post")
        self.assertEqual(revoke.get("operationId"), "revokeOAuthToken", "revokeOAuthToken FROZEN")
        revoke_codes = sorted((revoke.get("responses") or {}).keys())
        self.assertEqual(revoke_codes, ["200"], f"revoke phải CHỈ 200 (RFC 7009): {revoke_codes}")
        revoke_schema = ((((revoke.get("responses") or {}).get("200") or {}).get("content") or {})
                         .get("application/json", {}).get("schema") or {})
        self.assertEqual(
            revoke_schema.get("type"), "object",
            "revoke 200 body = empty object (RFC 7009 — oauth2.py:158-159).",
        )
        self.assertEqual(
            revoke_schema.get("properties", {}), {},
            "revoke 200 body PHẢI rỗng (0 property) — empty object.",
        )
        self.assertFalse(
            revoke_schema.get("additionalProperties", True),
            "revoke 200 body additionalProperties phải false (đóng — empty object thật).",
        )
        # authorize: 302-only.
        authorize = self._op(_AUTHORIZE_PATH, "get")
        self.assertEqual(authorize.get("operationId"), "authorizeOAuth", "authorizeOAuth FROZEN")
        self.assertEqual(
            sorted((authorize.get("responses") or {}).keys()), ["302"],
            "authorize phải CHỈ 302 (redirect) — B1 KHÔNG đụng.",
        )
        # Cả authorize + revoke KHÔNG có 400 (B1 chỉ wire getOAuthToken).
        for path, verb in ((_AUTHORIZE_PATH, "get"), (_REVOKE_TOKEN_PATH, "post")):
            self.assertNotIn(
                "400", (self._op(path, verb).get("responses") or {}),
                f"{path} KHÔNG được có 400 (B1 wire 400 CHỈ getOAuthToken).",
            )


class TestMobileReportIncidentBody(unittest.TestCase):
    """TC-MOB-OAS-13 — Phase-C requestBody THẬT cho reportIncident (path ĐẦU TIÊN rời STUB).

    Đóng băng hợp đồng body thành guard chạy được (chống bịa enum / drift required):
      (1) report_incident.post CÓ requestBody (required:true, $ref ReportIncidentBody).
      (2) component requestBodies/ReportIncidentBody required:true + content application/json
          + $ref schema ReportIncidentRequest.
      (3) schema ReportIncidentRequest.required EXACT = [asset,incident_type,severity,description]
          (KHÔNG thừa KHÔNG thiếu — 4 field reqd=1 @incident_report.json).
      (4) severity enum == [Low,Medium,High,Critical] + incident_type enum ==
          [Failure,Safety Event,Near Miss,Malfunction] (Select-canonical 1:1 @incident_report.json).
      (5) asset + description = type string; `source` KHÔNG xuất hiện ở body (server coerce).
      (6) G-REQBODY — reportIncident response surface BỒI: 200=ReportIncidentCreated
          (data=ReportIncidentResponse), 401=Unauthorized401, 403=ReportIncidentForbidden
          (DUAL-SHAPE oneOf Error|FrappeRawError), +404=NotFound404, +422=Unprocessable422.
      (7) G-REQBODY gap-1 — ReportIncidentBody.content = json + x-www-form-urlencoded (Frappe
          RPC form_dict; codegen JSON-only client KHÔNG khớp → field RỖNG).
      (8) G-REQBODY gap-4 — ReportIncidentResponse {name,status,severity} grounded imm12.py:410;
          status enum Select-canonical 7 (create-time "Open"); ReportIncidentCreated.data $ref schema.
    SSoT: ../04-api-contract.md §8.3 + incident_report.json + imm12.py:71-84,361,359,410.
    """

    @classmethod
    def setUpClass(cls):
        cls.spec = _load_spec() if _MOBILE_YAML.exists() else None

    def _report_op(self):
        return ((self.spec.get("paths") or {}).get(_REPORT_INCIDENT_PATH) or {}).get("post") or {}

    def test_mob_oas_13a_path_has_required_request_body_ref(self):
        """(1) report_incident.post requestBody = $ref-ONLY ReportIncidentBody (no `required` sibling).

        G-OAS-403-DISAMBIG (P1): `required:true` GỠ khỏi path-level (OAS 3.0.3 bỏ qua sibling cạnh
        `$ref` → codegen --strict warning); required GIỮ trong component (13b). Xem TC-MOB-OAS-19c.
        """
        op = self._report_op()
        self.assertEqual(op.get("operationId"), "reportIncident", "reportIncident operationId FROZEN")
        rb = op.get("requestBody") or {}
        self.assertTrue(rb, "report_incident PHẢI có requestBody (Phase-C).")
        self.assertEqual(
            set(rb.keys()), {"$ref"},
            f"requestBody PHẢI CHỈ có key `$ref` (gỡ sibling `required`): {sorted(rb.keys())}",
        )
        self.assertEqual(
            rb.get("$ref"), _REPORT_INCIDENT_BODY_REF,
            f"requestBody phải $ref ReportIncidentBody, got {rb.get('$ref')}",
        )

    def test_mob_oas_13b_component_request_body_wraps_schema(self):
        """(2) requestBodies/ReportIncidentBody required:true + application/json + $ref schema."""
        comp = ((self.spec.get("components") or {}).get("requestBodies") or {}).get("ReportIncidentBody") or {}
        self.assertTrue(comp, "Thiếu component requestBodies/ReportIncidentBody.")
        self.assertEqual(comp.get("required"), True, "Component required PHẢI true.")
        schema_ref = (((comp.get("content") or {}).get("application/json") or {}).get("schema") or {}).get("$ref")
        self.assertEqual(
            schema_ref, _REPORT_INCIDENT_SCHEMA_REF,
            f"ReportIncidentBody phải content application/json → $ref ReportIncidentRequest, got {schema_ref}",
        )

    def test_mob_oas_13c_schema_required_exact(self):
        """(3) ReportIncidentRequest.required EXACT = [asset,incident_type,severity,description]."""
        sch = ((self.spec.get("components") or {}).get("schemas") or {}).get("ReportIncidentRequest") or {}
        self.assertTrue(sch, "Thiếu schema ReportIncidentRequest.")
        self.assertEqual(
            sorted(sch.get("required") or []), sorted(_REPORT_INCIDENT_REQUIRED),
            f"required PHẢI EXACT {_REPORT_INCIDENT_REQUIRED} (4 field reqd=1, KHÔNG thừa/thiếu).",
        )

    def test_mob_oas_13d_select_enums_canonical(self):
        """(4) severity/incident_type enum 1:1 Select-canonical @incident_report.json."""
        props = (((self.spec.get("components") or {}).get("schemas") or {})
                 .get("ReportIncidentRequest") or {}).get("properties") or {}
        self.assertEqual(
            (props.get("severity") or {}).get("enum"), _SEVERITY_ENUM,
            f"severity enum PHẢI = {_SEVERITY_ENUM} (Select-canonical @incident_report.json).",
        )
        self.assertEqual(
            (props.get("incident_type") or {}).get("enum"), _INCIDENT_TYPE_ENUM,
            f"incident_type enum PHẢI = {_INCIDENT_TYPE_ENUM} (Select-canonical @incident_report.json).",
        )

    def test_mob_oas_13e_string_fields_and_no_source_leak(self):
        """(5) asset/description string; `source` KHÔNG lọt body (server coerce — imm12.py:83)."""
        props = (((self.spec.get("components") or {}).get("schemas") or {})
                 .get("ReportIncidentRequest") or {}).get("properties") or {}
        self.assertEqual((props.get("asset") or {}).get("type"), "string", "asset PHẢI type string (Link).")
        self.assertEqual(
            (props.get("description") or {}).get("type"), "string",
            "description PHẢI type string (Text Editor).",
        )
        self.assertNotIn(
            _REPORT_INCIDENT_FORBIDDEN_PROP, props,
            "`source` KHÔNG được ở requestBody (server gán provenance — KHÔNG client gửi).",
        )
        # severity/incident_type cũng là string + có enum (đã canh ở 13d).
        for f in ("severity", "incident_type"):
            self.assertEqual((props.get(f) or {}).get("type"), "string", f"{f} PHẢI type string.")

    def test_mob_oas_13f_response_surface_status_line(self):
        """(6) G-OAS-STATUSLINE — reportIncident 200 = oneOf [Created, Error] + discriminator
        success; 401=Unauthorized401, 403=ReportIncidentForbidden (dual-shape). in-handler
        404/422 (HTTP-200+Error) KHÔNG còn status-line key (dead-deser) → gom nhánh Error.
        status-set = [200,401,403] (symmetry 12 GIỮ: 401+403 declare đủ)."""
        resp = (self._report_op().get("responses") or {})
        # 200 = inline oneOf [CreatedEnvelope, Error] closed-schema, KHÔNG discriminator (§5c).
        schema200 = _assert_200_oneof_closed_distinct(
            self, resp, _REPORT_INCIDENT_CREATED_ENVELOPE_REF, "reportIncident",
        )
        self.assertIsNotNone(schema200, "reportIncident 200 PHẢI có inline oneOf schema.")
        self.assertEqual(
            resp.get("401", {}).get("$ref"), "#/components/responses/Unauthorized401",
            "reportIncident 401 PHẢI GIỮ Unauthorized401 (pre-handler status-line THẬT).",
        )
        self.assertEqual(
            resp.get("403", {}).get("$ref"), _REPORT_INCIDENT_FORBIDDEN_RESP_REF,
            "reportIncident 403 PHẢI = ReportIncidentForbidden (dual-shape, KHÁC Forbidden).",
        )
        # in-handler 404/422 KHÔNG còn status-line key (arrive HTTP-200+Error → dead-deser branch).
        self.assertNotIn(
            "404", resp,
            "reportIncident 404 KHÔNG còn status-line key — in-handler arrive HTTP-200+Error "
            "(services/imm12.py:361) → gom nhánh Error của 200-oneOf, route theo body.http_status.",
        )
        self.assertNotIn(
            "422", resp,
            "reportIncident 422 KHÔNG còn status-line key — in-handler arrive HTTP-200+Error "
            "(services/imm12.py:359) → gom nhánh Error của 200-oneOf, route theo body.http_status.",
        )
        self.assertEqual(
            sorted(resp.keys()), _REPORT_INCIDENT_STATUS_SET,
            f"reportIncident status set PHẢI = {_REPORT_INCIDENT_STATUS_SET} (G-OAS-STATUSLINE): {sorted(resp.keys())}",
        )

    def test_mob_oas_13g_request_body_content_dual_media_type(self):
        """(7) G-REQBODY gap-1 — ReportIncidentBody.content = json + x-www-form-urlencoded
        (CÙNG $ref ReportIncidentRequest). Frappe RPC /api/method đọc form_dict (form-encoded
        mặc định) — codegen JSON-only KHÔNG khớp → field RỖNG. 04 §4/§9."""
        comp = ((self.spec.get("components") or {}).get("requestBodies") or {}).get("ReportIncidentBody") or {}
        content = comp.get("content") or {}
        self.assertEqual(
            set(content.keys()), _REPORT_BODY_MEDIA_TYPES,
            f"ReportIncidentBody.content PHẢI = {_REPORT_BODY_MEDIA_TYPES} (Frappe RPC form_dict).",
        )
        for mt in _REPORT_BODY_MEDIA_TYPES:
            ref = ((content.get(mt) or {}).get("schema") or {}).get("$ref")
            self.assertEqual(
                ref, _REPORT_INCIDENT_SCHEMA_REF,
                f"media-type {mt} PHẢI $ref ReportIncidentRequest (CÙNG schema), got {ref}",
            )

    def test_mob_oas_13h_response_schema_grounded_imm12(self):
        """(8) G-REQBODY gap-4 — ReportIncidentResponse {name,status,severity} grounded
        services/imm12.py:410. status enum Select-canonical 7 (create-time "Open" imm12.py:373);
        severity enum 4. ReportIncidentCreated = success envelope, data $ref schema này."""
        sch = ((self.spec.get("components") or {}).get("schemas") or {}).get("ReportIncidentResponse") or {}
        self.assertTrue(sch, "Thiếu schema ReportIncidentResponse (G-REQBODY).")
        self.assertEqual(
            sorted(sch.get("required") or []), sorted(_REPORT_INCIDENT_RESPONSE_REQUIRED),
            f"ReportIncidentResponse.required EXACT {_REPORT_INCIDENT_RESPONSE_REQUIRED} (imm12.py:410).",
        )
        props = sch.get("properties") or {}
        self.assertEqual(
            (props.get("status") or {}).get("enum"), _INCIDENT_STATUS_ENUM,
            f"status enum PHẢI = {_INCIDENT_STATUS_ENUM} (Select-canonical @incident_report.json).",
        )
        self.assertEqual(
            (props.get("severity") or {}).get("enum"), _SEVERITY_ENUM,
            f"severity enum PHẢI = {_SEVERITY_ENUM} (Select-canonical).",
        )
        self.assertEqual((props.get("name") or {}).get("type"), "string", "name PHẢI type string.")
        # G-OAS-STATUSLINE — ReportIncidentCreatedEnvelope (named schema) = success envelope với
        #   data $ref ReportIncidentResponse + success.enum:[true] (nhánh discriminator 'true').
        env = ((self.spec.get("components") or {}).get("schemas") or {}).get("ReportIncidentCreatedEnvelope") or {}
        self.assertTrue(env, "Thiếu schema ReportIncidentCreatedEnvelope (G-OAS-STATUSLINE).")
        self.assertEqual(
            ((env.get("properties") or {}).get("success") or {}).get("enum"), [True],
            "ReportIncidentCreatedEnvelope.success.enum PHẢI = [true] (nhánh discriminator 'true').",
        )
        data_ref = ((env.get("properties") or {}).get("data") or {}).get("$ref")
        self.assertEqual(
            data_ref, _REPORT_INCIDENT_RESPONSE_SCHEMA_REF,
            f"ReportIncidentCreatedEnvelope.data PHẢI $ref ReportIncidentResponse, got {data_ref}",
        )


class TestMobileCreateRepairBody(unittest.TestCase):
    """TC-MOB-OAS-16 — C-REQBODY-CREATEREPAIR: requestBody + response THẬT cho
    createRepairWorkOrder (path Phase-C THỨ HAI rời STUB, tái dùng template G-REQBODY).

    Đóng băng hợp đồng body+response thành guard chạy được (chống bịa enum / drift required /
    sai shape 403/409 — bám SOURCE, KHÔNG bám chữ đề mục):
      (a) create_repair_work_order.post CÓ requestBody (required:true, $ref CreateRepairWorkOrderBody).
      (b) requestBodies/CreateRepairWorkOrderBody required:true + content json $ref schema.
      (c) CreateRepairWorkOrderRequest.required EXACT = [asset_ref,repair_type,priority,
          failure_description] (4 tham số không-default @imm09.py:36-38).
      (d) repair_type enum == [Corrective,Breakdown,Warranty Repair] + priority enum ==
          [Normal,Urgent,Emergency] (Select-canonical 1:1 @asset_repair.json; priority khớp
          _SLA_MATRIX imm09 services).
      (e) 3 optional (incident_report/source_pm_wo/fault_image) CÓ trong properties (type string);
          `requested_by` KHÔNG ở body (server gán — imm09.py:770).
      (f) content = json + x-www-form-urlencoded (Frappe RPC form_dict — CÙNG $ref schema).
      (g) response surface = 200=CreateRepairWorkOrderCreated, 401=Unauthorized401,
          403=Forbidden (SINGLE-SHAPE — rbac.require→PermissionError HTTP-403 imm09.py:40,
          KHÁC report_incident dual-shape), 404=NotFound404, 409=Conflict409.
          status-set = [200,401,403,404,409] (409 NOT 422 — HAS_OPEN_WO http_status 409).
      (h) CreateRepairWorkOrderResponse {name,status,sla_target_hours} grounded imm09.py:786
          (SELF-CORRECTION: sla_target_hours NOT priority); status enum Select-canonical 9
          (create-time "Open"); CreateRepairWorkOrderCreated.data $ref schema này.
    SSoT: ../04-api-contract.md §8.4 + asset_repair.json + imm09.py:36-38,746,753,786 + messages.py:667.
    """

    @classmethod
    def setUpClass(cls):
        cls.spec = _load_spec() if _MOBILE_YAML.exists() else None

    def _create_op(self):
        return ((self.spec.get("paths") or {}).get(_REPAIR_CREATE_PATH) or {}).get("post") or {}

    def test_mob_oas_16a_path_has_required_request_body_ref(self):
        """(a) create_repair.post requestBody = $ref-ONLY CreateRepairWorkOrderBody (no `required` sibling).

        G-OAS-403-DISAMBIG (P1): `required:true` GỠ khỏi path-level (OAS 3.0.3 bỏ qua sibling cạnh
        `$ref`); required GIỮ trong component (16b). Xem TC-MOB-OAS-19c.
        """
        op = self._create_op()
        self.assertEqual(op.get("operationId"), "createRepairWorkOrder", "operationId FROZEN")
        rb = op.get("requestBody") or {}
        self.assertTrue(rb, "create_repair_work_order PHẢI có requestBody (C-REQBODY-CREATEREPAIR).")
        self.assertEqual(
            set(rb.keys()), {"$ref"},
            f"requestBody PHẢI CHỈ có key `$ref` (gỡ sibling `required`): {sorted(rb.keys())}",
        )
        self.assertEqual(
            rb.get("$ref"), _REPAIR_CREATE_BODY_REF,
            f"requestBody phải $ref CreateRepairWorkOrderBody, got {rb.get('$ref')}",
        )

    def test_mob_oas_16b_component_request_body_wraps_schema(self):
        """(b) requestBodies/CreateRepairWorkOrderBody required:true + json + $ref schema."""
        comp = ((self.spec.get("components") or {}).get("requestBodies") or {}).get("CreateRepairWorkOrderBody") or {}
        self.assertTrue(comp, "Thiếu component requestBodies/CreateRepairWorkOrderBody.")
        self.assertEqual(comp.get("required"), True, "Component required PHẢI true.")
        schema_ref = (((comp.get("content") or {}).get("application/json") or {}).get("schema") or {}).get("$ref")
        self.assertEqual(
            schema_ref, _REPAIR_CREATE_SCHEMA_REF,
            f"CreateRepairWorkOrderBody json PHẢI $ref CreateRepairWorkOrderRequest, got {schema_ref}",
        )

    def test_mob_oas_16c_schema_required_exact(self):
        """(c) CreateRepairWorkOrderRequest.required EXACT = 4 tham số không-default @imm09.py:36-38."""
        sch = ((self.spec.get("components") or {}).get("schemas") or {}).get("CreateRepairWorkOrderRequest") or {}
        self.assertTrue(sch, "Thiếu schema CreateRepairWorkOrderRequest.")
        self.assertEqual(
            sorted(sch.get("required") or []), sorted(_REPAIR_CREATE_REQUIRED),
            f"required PHẢI EXACT {_REPAIR_CREATE_REQUIRED} (4 không-default @imm09.py:36-38).",
        )

    def test_mob_oas_16d_select_enums_canonical(self):
        """(d) repair_type/priority enum 1:1 Select-canonical @asset_repair.json."""
        props = (((self.spec.get("components") or {}).get("schemas") or {})
                 .get("CreateRepairWorkOrderRequest") or {}).get("properties") or {}
        self.assertEqual(
            (props.get("repair_type") or {}).get("enum"), _REPAIR_TYPE_ENUM,
            f"repair_type enum PHẢI = {_REPAIR_TYPE_ENUM} (Select-canonical @asset_repair.json).",
        )
        self.assertEqual(
            (props.get("priority") or {}).get("enum"), _REPAIR_PRIORITY_ENUM,
            f"priority enum PHẢI = {_REPAIR_PRIORITY_ENUM} (Select-canonical, khớp _SLA_MATRIX).",
        )

    def test_mob_oas_16e_optional_present_and_no_server_field_leak(self):
        """(e) 3 optional có (type string); `requested_by` KHÔNG lọt body (server gán imm09.py:770)."""
        props = (((self.spec.get("components") or {}).get("schemas") or {})
                 .get("CreateRepairWorkOrderRequest") or {}).get("properties") or {}
        self.assertEqual((props.get("asset_ref") or {}).get("type"), "string", "asset_ref PHẢI string (Link).")
        self.assertEqual(
            (props.get("failure_description") or {}).get("type"), "string",
            "failure_description PHẢI type string (Text).",
        )
        for opt in _REPAIR_CREATE_OPTIONAL:
            self.assertIn(opt, props, f"optional `{opt}` PHẢI có trong properties (@imm09.py:37-38).")
            self.assertEqual((props.get(opt) or {}).get("type"), "string", f"{opt} PHẢI type string.")
        self.assertNotIn(
            _REPAIR_CREATE_FORBIDDEN_PROP, props,
            "`requested_by` KHÔNG được ở requestBody (server gán session.user — imm09.py:770).",
        )

    def test_mob_oas_16f_request_body_content_dual_media_type(self):
        """(f) CreateRepairWorkOrderBody.content = json + x-www-form-urlencoded (CÙNG $ref).
        Frappe RPC /api/method đọc form_dict — codegen JSON-only KHÔNG khớp → field RỖNG. 04 §4/§9."""
        comp = ((self.spec.get("components") or {}).get("requestBodies") or {}).get("CreateRepairWorkOrderBody") or {}
        content = comp.get("content") or {}
        self.assertEqual(
            set(content.keys()), _REPAIR_BODY_MEDIA_TYPES,
            f"CreateRepairWorkOrderBody.content PHẢI = {_REPAIR_BODY_MEDIA_TYPES} (Frappe RPC form_dict).",
        )
        for mt in _REPAIR_BODY_MEDIA_TYPES:
            ref = ((content.get(mt) or {}).get("schema") or {}).get("$ref")
            self.assertEqual(
                ref, _REPAIR_CREATE_SCHEMA_REF,
                f"media-type {mt} PHẢI $ref CreateRepairWorkOrderRequest (CÙNG schema), got {ref}",
            )

    def test_mob_oas_16g_response_surface(self):
        """(g) G-OAS-STATUSLINE — 200 = oneOf [Created, Error] + discriminator success;
        401=Unauthorized401, 403=Forbidden (SINGLE-SHAPE). in-handler 404/409 (imm09.py:746/753,
        HTTP-200+Error) KHÔNG còn status-line key (dead-deser) → gom nhánh Error. status-set =
        [200,401,403] (symmetry 12 GIỮ)."""
        resp = (self._create_op().get("responses") or {})
        _assert_200_oneof_closed_distinct(
            self, resp, _REPAIR_CREATE_CREATED_ENVELOPE_REF, "createRepair",
        )
        self.assertEqual(
            resp.get("401", {}).get("$ref"), "#/components/responses/Unauthorized401",
            "createRepair 401 PHẢI GIỮ Unauthorized401 (pre-handler status-line THẬT).",
        )
        # delta d2 — 403 SINGLE-SHAPE Forbidden (rbac.require→PermissionError HTTP-403 imm09.py:40);
        #   KHÁC report_incident (dual-shape vì imm12 dùng _err in-handler). KHÔNG ReportIncidentForbidden.
        self.assertEqual(
            resp.get("403", {}).get("$ref"), _REPAIR_CREATE_FORBIDDEN_RESP_REF,
            "createRepair 403 PHẢI = Forbidden (single-shape, rbac.require→PermissionError HTTP-403).",
        )
        self.assertNotEqual(
            resp.get("403", {}).get("$ref"), _REPORT_INCIDENT_FORBIDDEN_RESP_REF,
            "createRepair 403 KHÔNG được dùng ReportIncidentForbidden (dual-shape sai @source).",
        )
        # G-OAS-STATUSLINE — in-handler 404/409 KHÔNG còn status-line key (arrive HTTP-200+Error,
        #   imm09.py:746/753 → handle()→_err→dict; status-line KHÔNG bao giờ set). Dead-deser branch
        #   nếu key dưới HTTP-code → gom vào nhánh Error của 200-oneOf, route theo body.http_status.
        self.assertNotIn(
            "404", resp,
            "createRepair 404 KHÔNG còn status-line key — in-handler arrive HTTP-200+Error (imm09.py:746).",
        )
        self.assertNotIn(
            "409", resp,
            "createRepair 409 KHÔNG còn status-line key — in-handler arrive HTTP-200+Error (imm09.py:753).",
        )
        self.assertNotIn(
            "422", resp,
            "createRepair KHÔNG được khai 422 — HAS_OPEN_WO là 409 CONFLICT @source (delta d3).",
        )
        self.assertEqual(
            sorted(resp.keys()), _REPAIR_CREATE_STATUS_SET,
            f"createRepair status set PHẢI = {_REPAIR_CREATE_STATUS_SET}: {sorted(resp.keys())}",
        )

    def test_mob_oas_16h_response_schema_grounded_imm09(self):
        """(h) CreateRepairWorkOrderResponse {name,status,sla_target_hours} grounded imm09.py:786
        (SELF-CORRECTION: sla_target_hours NOT priority). status enum Select-canonical 9
        (create-time "Open"); CreateRepairWorkOrderCreated.data $ref schema này."""
        sch = ((self.spec.get("components") or {}).get("schemas") or {}).get("CreateRepairWorkOrderResponse") or {}
        self.assertTrue(sch, "Thiếu schema CreateRepairWorkOrderResponse (C-REQBODY-CREATEREPAIR).")
        self.assertEqual(
            sorted(sch.get("required") or []), sorted(_REPAIR_CREATE_RESPONSE_REQUIRED),
            f"required EXACT {_REPAIR_CREATE_RESPONSE_REQUIRED} (imm09.py:786 — NOT priority).",
        )
        props = sch.get("properties") or {}
        self.assertNotIn(
            "priority", props,
            "Response KHÔNG có `priority` — service trả sla_target_hours (imm09.py:786, delta d1).",
        )
        self.assertEqual(
            (props.get("status") or {}).get("enum"), _REPAIR_STATUS_ENUM,
            f"status enum PHẢI = {_REPAIR_STATUS_ENUM} (Select-canonical @asset_repair.json).",
        )
        self.assertEqual((props.get("name") or {}).get("type"), "string", "name PHẢI type string.")
        self.assertEqual(
            (props.get("sla_target_hours") or {}).get("type"), "number",
            "sla_target_hours PHẢI type number (giờ SLA — imm09.py:112).",
        )
        # G-OAS-STATUSLINE — CreateRepairWorkOrderCreatedEnvelope (named schema) = success envelope
        #   với data $ref response schema + success.enum:[true] (nhánh discriminator 'true').
        env = (((self.spec.get("components") or {}).get("schemas") or {})
               .get("CreateRepairWorkOrderCreatedEnvelope") or {})
        self.assertTrue(env, "Thiếu schema CreateRepairWorkOrderCreatedEnvelope (G-OAS-STATUSLINE).")
        self.assertEqual(
            ((env.get("properties") or {}).get("success") or {}).get("enum"), [True],
            "CreateRepairWorkOrderCreatedEnvelope.success.enum PHẢI = [true] (nhánh discriminator 'true').",
        )
        data_ref = ((env.get("properties") or {}).get("data") or {}).get("$ref")
        self.assertEqual(
            data_ref, _REPAIR_CREATE_RESPONSE_SCHEMA_REF,
            f"CreateRepairWorkOrderCreatedEnvelope.data PHẢI $ref CreateRepairWorkOrderResponse, got {data_ref}",
        )


class TestMobileCreateCalibrationBody(unittest.TestCase):
    """TC-MOB-OAS-17 — C-REQBODY-CREATECAL: requestBody + response THẬT cho createCalibration
    (path Phase-C THỨ BA rời STUB — hoàn tất bộ-ba create report→repair→calibration, tái dùng
    template C-REQBODY-CREATEREPAIR).

    Đóng băng hợp đồng body+response thành guard chạy được (chống bịa enum / drift required /
    sai shape 403/409 — bám SOURCE, KHÔNG bám chữ đề mục):
      (a) create_calibration.post CÓ requestBody (required:true, $ref CreateCalibrationBody).
      (b) requestBodies/CreateCalibrationBody required:true + content json $ref schema.
      (c) CreateCalibrationRequest.required EXACT = [asset,calibration_type,scheduled_date,
          technician] (4 tham số không-default @imm11.py:90-91).
      (d) calibration_type enum == [External,In-House] (Select-canonical 1:1
          @imm_asset_calibration.json — KHÔNG bịa giá trị).
      (e) 5 optional (calibration_schedule/lab_supplier/is_recalibration/reference_standard_serial/
          traceability_reference) CÓ trong properties; is_recalibration = integer enum [0,1]
          (Check); KHÔNG field server-gán (technician là tham số THẬT — khác report `source` /
          repair `requested_by`).
      (f) content = json + x-www-form-urlencoded (Frappe RPC form_dict — CÙNG $ref schema).
      (g) response surface = 200=CreateCalibrationCreated, 401=Unauthorized401,
          403=Forbidden (SINGLE-SHAPE — rbac.require→PermissionError HTTP-403 imm11.py:95,
          KHÁC report_incident dual-shape), 404=NotFound404, 409=Conflict409.
          status-set = [200,401,403,404,409] (409 NOT 422 — ASSET_BLOCKED http_status 409 CAL-008).
      (h) CreateCalibrationResponse {name,status} grounded imm11.py:1015 (KHÔNG sla_target_hours —
          khác createRepair); status enum Select-canonical 8 (create-time "Scheduled"
          CalibrationResult.SCHEDULED); CreateCalibrationCreated.data $ref schema này.
    SSoT: ../04-api-contract.md §8.6 + imm_asset_calibration.json + imm11.py:90-95,999,1002,1013-1015
          + messages.py:853,860.
    """

    @classmethod
    def setUpClass(cls):
        cls.spec = _load_spec() if _MOBILE_YAML.exists() else None

    def _create_op(self):
        return ((self.spec.get("paths") or {}).get(_CAL_CREATE_PATH) or {}).get("post") or {}

    def test_mob_oas_17a_path_has_required_request_body_ref(self):
        """(a) create_calibration.post requestBody = $ref-ONLY CreateCalibrationBody (no `required` sibling).

        G-OAS-403-DISAMBIG (P1): `required:true` GỠ khỏi path-level (OAS 3.0.3 bỏ qua sibling cạnh
        `$ref`); required GIỮ trong component (17b). Xem TC-MOB-OAS-19c.
        """
        op = self._create_op()
        self.assertEqual(op.get("operationId"), "createCalibration", "operationId FROZEN")
        rb = op.get("requestBody") or {}
        self.assertTrue(rb, "create_calibration PHẢI có requestBody (C-REQBODY-CREATECAL).")
        self.assertEqual(
            set(rb.keys()), {"$ref"},
            f"requestBody PHẢI CHỈ có key `$ref` (gỡ sibling `required`): {sorted(rb.keys())}",
        )
        self.assertEqual(
            rb.get("$ref"), _CAL_CREATE_BODY_REF,
            f"requestBody phải $ref CreateCalibrationBody, got {rb.get('$ref')}",
        )

    def test_mob_oas_17b_component_request_body_wraps_schema(self):
        """(b) requestBodies/CreateCalibrationBody required:true + json + $ref schema."""
        comp = ((self.spec.get("components") or {}).get("requestBodies") or {}).get("CreateCalibrationBody") or {}
        self.assertTrue(comp, "Thiếu component requestBodies/CreateCalibrationBody.")
        self.assertEqual(comp.get("required"), True, "Component required PHẢI true.")
        schema_ref = (((comp.get("content") or {}).get("application/json") or {}).get("schema") or {}).get("$ref")
        self.assertEqual(
            schema_ref, _CAL_CREATE_SCHEMA_REF,
            f"CreateCalibrationBody json PHẢI $ref CreateCalibrationRequest, got {schema_ref}",
        )

    def test_mob_oas_17c_schema_required_exact(self):
        """(c) CreateCalibrationRequest.required EXACT = 4 tham số không-default @imm11.py:90-91."""
        sch = ((self.spec.get("components") or {}).get("schemas") or {}).get("CreateCalibrationRequest") or {}
        self.assertTrue(sch, "Thiếu schema CreateCalibrationRequest.")
        self.assertEqual(
            sorted(sch.get("required") or []), sorted(_CAL_CREATE_REQUIRED),
            f"required PHẢI EXACT {_CAL_CREATE_REQUIRED} (4 không-default @imm11.py:90-91).",
        )

    def test_mob_oas_17d_select_enum_canonical(self):
        """(d) calibration_type enum 1:1 Select-canonical @imm_asset_calibration.json."""
        props = (((self.spec.get("components") or {}).get("schemas") or {})
                 .get("CreateCalibrationRequest") or {}).get("properties") or {}
        self.assertEqual(
            (props.get("calibration_type") or {}).get("enum"), _CAL_TYPE_ENUM,
            f"calibration_type enum PHẢI = {_CAL_TYPE_ENUM} (Select-canonical @imm_asset_calibration.json).",
        )

    def test_mob_oas_17e_optional_present_and_no_server_field_leak(self):
        """(e) 5 optional có; is_recalibration int enum [0,1]; KHÔNG field server-gán lọt body."""
        props = (((self.spec.get("components") or {}).get("schemas") or {})
                 .get("CreateCalibrationRequest") or {}).get("properties") or {}
        self.assertEqual((props.get("asset") or {}).get("type"), "string", "asset PHẢI string (Link).")
        self.assertEqual(
            (props.get("scheduled_date") or {}).get("type"), "string",
            "scheduled_date PHẢI type string (Date).",
        )
        self.assertEqual((props.get("technician") or {}).get("type"), "string", "technician PHẢI string (Link User).")
        for opt in _CAL_CREATE_OPTIONAL:
            self.assertIn(opt, props, f"optional `{opt}` PHẢI có trong properties (@imm11.py:91-94).")
        # is_recalibration = Check (0|1) → integer enum [0,1] (quyết định bypass business-block).
        self.assertEqual(
            (props.get("is_recalibration") or {}).get("type"), "integer",
            "is_recalibration PHẢI type integer (Check 0|1).",
        )
        self.assertEqual(
            (props.get("is_recalibration") or {}).get("enum"), [0, 1],
            "is_recalibration enum PHẢI = [0, 1] (Check — bypass business-block @imm11.py:1001).",
        )
        # KHÔNG field server-gán: technician là tham số THẬT của signature (KHÁC report `source` /
        #   repair `requested_by` — không có server-coerce field để loại).
        self.assertNotIn(
            "source", props,
            "`source` KHÔNG được ở requestBody (createCalibration KHÔNG nhận provenance — anti-leak).",
        )

    def test_mob_oas_17f_request_body_content_dual_media_type(self):
        """(f) CreateCalibrationBody.content = json + x-www-form-urlencoded (CÙNG $ref).
        Frappe RPC /api/method đọc form_dict — codegen JSON-only KHÔNG khớp → field RỖNG. 04 §4/§9."""
        comp = ((self.spec.get("components") or {}).get("requestBodies") or {}).get("CreateCalibrationBody") or {}
        content = comp.get("content") or {}
        self.assertEqual(
            set(content.keys()), _CAL_BODY_MEDIA_TYPES,
            f"CreateCalibrationBody.content PHẢI = {_CAL_BODY_MEDIA_TYPES} (Frappe RPC form_dict).",
        )
        for mt in _CAL_BODY_MEDIA_TYPES:
            ref = ((content.get(mt) or {}).get("schema") or {}).get("$ref")
            self.assertEqual(
                ref, _CAL_CREATE_SCHEMA_REF,
                f"media-type {mt} PHẢI $ref CreateCalibrationRequest (CÙNG schema), got {ref}",
            )

    def test_mob_oas_17g_response_surface(self):
        """(g) G-OAS-STATUSLINE — 200 = oneOf [Created, Error] + discriminator success;
        401=Unauthorized401, 403=Forbidden (SINGLE-SHAPE). in-handler 404/409 (imm11.py:999/1002,
        HTTP-200+Error) KHÔNG còn status-line key (dead-deser) → gom nhánh Error. status-set =
        [200,401,403] (symmetry 12 GIỮ)."""
        resp = (self._create_op().get("responses") or {})
        _assert_200_oneof_closed_distinct(
            self, resp, _CAL_CREATE_CREATED_ENVELOPE_REF, "createCalibration",
        )
        self.assertEqual(
            resp.get("401", {}).get("$ref"), "#/components/responses/Unauthorized401",
            "createCalibration 401 PHẢI GIỮ Unauthorized401 (pre-handler status-line THẬT).",
        )
        # delta c1 — 403 SINGLE-SHAPE Forbidden (rbac.require→PermissionError HTTP-403 imm11.py:95);
        #   KHÁC report_incident (dual-shape vì imm12 dùng _err in-handler). KHÔNG ReportIncidentForbidden.
        self.assertEqual(
            resp.get("403", {}).get("$ref"), _CAL_CREATE_FORBIDDEN_RESP_REF,
            "createCalibration 403 PHẢI = Forbidden (single-shape, rbac.require→PermissionError HTTP-403).",
        )
        self.assertNotEqual(
            resp.get("403", {}).get("$ref"), _REPORT_INCIDENT_FORBIDDEN_RESP_REF,
            "createCalibration 403 KHÔNG được dùng ReportIncidentForbidden (dual-shape sai @source).",
        )
        # G-OAS-STATUSLINE — in-handler 404/409 KHÔNG còn status-line key (arrive HTTP-200+Error,
        #   imm11.py:999/1002 → handle()→_err→dict; status-line KHÔNG bao giờ set). Gom nhánh Error.
        self.assertNotIn(
            "404", resp,
            "createCalibration 404 KHÔNG còn status-line key — in-handler arrive HTTP-200+Error (imm11.py:999).",
        )
        self.assertNotIn(
            "409", resp,
            "createCalibration 409 KHÔNG còn status-line key — in-handler arrive HTTP-200+Error (imm11.py:1002).",
        )
        self.assertNotIn(
            "422", resp,
            "createCalibration KHÔNG được khai 422 — ASSET_BLOCKED là 409 CONFLICT @source (delta c2).",
        )
        self.assertEqual(
            sorted(resp.keys()), _CAL_CREATE_STATUS_SET,
            f"createCalibration status set PHẢI = {_CAL_CREATE_STATUS_SET}: {sorted(resp.keys())}",
        )

    def test_mob_oas_17h_response_schema_grounded_imm11(self):
        """(h) CreateCalibrationResponse {name,status} grounded imm11.py:1015 (KHÔNG sla_target_hours
        — khác createRepair). status enum Select-canonical 8 (create-time "Scheduled");
        CreateCalibrationCreated.data $ref schema này."""
        sch = ((self.spec.get("components") or {}).get("schemas") or {}).get("CreateCalibrationResponse") or {}
        self.assertTrue(sch, "Thiếu schema CreateCalibrationResponse (C-REQBODY-CREATECAL).")
        self.assertEqual(
            sorted(sch.get("required") or []), sorted(_CAL_CREATE_RESPONSE_REQUIRED),
            f"required EXACT {_CAL_CREATE_RESPONSE_REQUIRED} (imm11.py:1015 — KHÔNG sla_target_hours).",
        )
        props = sch.get("properties") or {}
        self.assertNotIn(
            "sla_target_hours", props,
            "Response KHÔNG có `sla_target_hours` — calibration return CHỈ {name,status} (imm11.py:1015).",
        )
        self.assertEqual(
            (props.get("status") or {}).get("enum"), _CAL_STATUS_ENUM,
            f"status enum PHẢI = {_CAL_STATUS_ENUM} (Select-canonical @imm_asset_calibration.json).",
        )
        self.assertEqual((props.get("name") or {}).get("type"), "string", "name PHẢI type string.")
        # G-OAS-STATUSLINE — CreateCalibrationCreatedEnvelope (named schema) = success envelope với
        #   data $ref response schema + success.enum:[true] (nhánh discriminator 'true').
        env = (((self.spec.get("components") or {}).get("schemas") or {})
               .get("CreateCalibrationCreatedEnvelope") or {})
        self.assertTrue(env, "Thiếu schema CreateCalibrationCreatedEnvelope (G-OAS-STATUSLINE).")
        self.assertEqual(
            ((env.get("properties") or {}).get("success") or {}).get("enum"), [True],
            "CreateCalibrationCreatedEnvelope.success.enum PHẢI = [true] (nhánh discriminator 'true').",
        )
        data_ref = ((env.get("properties") or {}).get("data") or {}).get("$ref")
        self.assertEqual(
            data_ref, _CAL_CREATE_RESPONSE_SCHEMA_REF,
            f"CreateCalibrationCreatedEnvelope.data PHẢI $ref CreateCalibrationResponse, got {data_ref}",
        )


# G-OAS-STATUSLINE — 3 create path × CreatedEnvelope schema (nhánh 'true' discriminator).
_CREATE_PATH_ENVELOPE = {
    _REPORT_INCIDENT_PATH: _REPORT_INCIDENT_CREATED_ENVELOPE_REF,
    _REPAIR_CREATE_PATH: _REPAIR_CREATE_CREATED_ENVELOPE_REF,
    _CAL_CREATE_PATH: _CAL_CREATE_CREATED_ENVELOPE_REF,
}


class TestMobileCreate200OneOfDiscriminator(unittest.TestCase):
    """TC-MOB-OAS-18 — G-OAS-NO-BOOL-DISC (§5c, Self-Correction R1): 3 create path 200 = oneOf
    [Created, Error] máy-phân-biệt bằng CLOSED-SCHEMA + disjoint required-set, KHÔNG discriminator
    boolean (illegal OAS 3.x — `success` boolean ≠ string propertyName).

    ROOT-FACT @source (verified): in-handler business error (404/422 report; 404/409 repair/cal)
    đi qua `_err` (response.py:95-154) + `handle()` return dict (api_handler.py:48) → Frappe
    serialize HTTP-200 (hooks.py:405 no after_request hook đổi status-line) ⇒ status-line KHÔNG
    BAO GIỜ set cho in-handler error. Keying chúng dưới HTTP-code response-key (404/422/409) =
    DEAD-DESER branch (codegen route-by-status-line KHÔNG bao giờ khớp). G-OAS-NO-BOOL-DISC:
      (1) 3 create path 200 = inline oneOf [<CreatedEnvelope>, Error] (KHÔNG single $ref Created).
      (2) KHÔNG block `discriminator` trong schema 200 — `success` boolean → discriminator illegal
          (OAS 3.x yêu cầu propertyName trỏ property STRING; generator drop/deser-fail). 2 nhánh
          máy-phân-biệt bằng closed-schema (additionalProperties:false trên CẢ Created + Error) +
          disjoint required-set ([success,data] vs [success,error,code,http_status]). Mirror R2 fix-403.
      (3) Created envelope success.enum==[true]; Error success.enum==[false] — disambiguation phụ
          theo VALUE. in-handler error CHỈ surface qua 200-Error nhánh — KHÔNG dưới HTTP-code
          status-line key (3 path status-set = [200,401,403]; 404/422/409 vắng status-line key).
    SSoT: ../04-api-contract.md §5/§5b/§5c (route-by-body, closed-schema) + ADR-MOBILE-001 (f) +
          response.py:95-154 + api_handler.py:48 + hooks.py:405.
    """

    @classmethod
    def setUpClass(cls):
        cls.spec = _load_spec() if _MOBILE_YAML.exists() else None

    def _resp(self, path):
        return (((self.spec.get("paths") or {}).get(path) or {}).get("post") or {}).get("responses") or {}

    def test_mob_oas_18a_each_create_200_is_oneof_not_single_ref(self):
        """(1) 3 create path 200 = oneOf 2 nhánh [Created, Error] (KHÔNG single $ref Created)."""
        for path, env_ref in _CREATE_PATH_ENVELOPE.items():
            resp = self._resp(path)
            _assert_200_oneof_closed_distinct(self, resp, env_ref, path)

    def test_mob_oas_18b_no_boolean_discriminator(self):
        """(2) §5c — KHÔNG block `discriminator` ở 200 schema CỦA 3 create path (chống tái phát
        boolean-discriminator illegal). 2 nhánh oneOf resolve (0 dangling)."""
        for path, env_ref in _CREATE_PATH_ENVELOPE.items():
            schema200 = _200_schema(self._resp(path))
            self.assertNotIn(
                "discriminator", schema200,
                f"{path}: 200 KHÔNG được có `discriminator` — success=boolean → illegal OAS 3.x "
                "(generator drop/deser-fail). Dùng closed-schema + disjoint required-set thay thế (§5c).",
            )
            # 2 nhánh oneOf resolve (0 dangling).
            one_of = schema200.get("oneOf") or []
            for branch in one_of:
                ref = branch.get("$ref") if isinstance(branch, dict) else None
                self.assertTrue(ref and _resolve_pointer(ref, self.spec), f"{path}: nhánh oneOf dangling {ref}")
            self.assertIn(env_ref, [b.get("$ref") for b in one_of if isinstance(b, dict)], f"{path}: thiếu nhánh Created")

    def test_mob_oas_18c_created_error_closed_distinct(self):
        """(2b+3) STRUCTURAL DISTINCTNESS (§5c) — Created + Error CẢ HAI additionalProperties:false
        (closed) + disjoint required-set + success.enum đối lập ([true] vs [false]). Đây là cơ chế
        máy-phân-biệt 2 nhánh oneOf khi KHÔNG có discriminator (thay boolean-discriminator illegal)."""
        schemas = (self.spec.get("components") or {}).get("schemas") or {}
        # Error nhánh 'false' — closed + required quad.
        err = schemas.get("Error") or {}
        self.assertEqual(
            err.get("additionalProperties"), False,
            "Error.additionalProperties PHẢI = false (closed-schema → loại-trừ nhánh Created, §5c).",
        )
        self.assertEqual(
            ((err.get("properties") or {}).get("success") or {}).get("enum"), [False],
            "Error.success.enum PHẢI = [false] (nhánh in-handler error).",
        )
        err_req = set(err.get("required") or [])
        self.assertEqual(
            err_req, {"success", "error", "code", "http_status"},
            "Error.required PHẢI = {success,error,code,http_status} (disjoint vs Created [success,data]).",
        )
        # Created nhánh 'true' (3 envelope) — closed + required pair + success.enum=[true].
        for env_name in (
            "ReportIncidentCreatedEnvelope",
            "CreateRepairWorkOrderCreatedEnvelope",
            "CreateCalibrationCreatedEnvelope",
        ):
            env = schemas.get(env_name) or {}
            self.assertTrue(env, f"Thiếu schema {env_name} (§5c).")
            self.assertEqual(
                env.get("additionalProperties"), False,
                f"{env_name}.additionalProperties PHẢI = false (closed-schema → distinct vs Error, §5c).",
            )
            self.assertEqual(
                ((env.get("properties") or {}).get("success") or {}).get("enum"), [True],
                f"{env_name}.success.enum PHẢI = [true] (nhánh thành công).",
            )
            env_req = set(env.get("required") or [])
            self.assertEqual(
                env_req, {"success", "data"},
                f"{env_name}.required PHẢI = {{success,data}} (disjoint vs Error required-set → 2 nhánh "
                "oneOf loại-trừ máy-đọc KHÔNG cần discriminator).",
            )
            # Disjoint required-set proof: KHÔNG trùng ngoài 'success'.
            self.assertEqual(
                (env_req & err_req), {"success"},
                f"{env_name} vs Error required-set CHỈ giao 'success' — phần còn lại disjoint (distinctness).",
            )

    def test_mob_oas_18d_inhandler_error_only_via_200_not_status_line(self):
        """(3) in-handler error (404/422/409) CHỈ surface qua 200-Error nhánh — KHÔNG dưới
        HTTP-code status-line key. 3 path status-set = [200,401,403]."""
        expected = {
            _REPORT_INCIDENT_PATH: _REPORT_INCIDENT_STATUS_SET,
            _REPAIR_CREATE_PATH: _REPAIR_CREATE_STATUS_SET,
            _CAL_CREATE_PATH: _CAL_CREATE_STATUS_SET,
        }
        for path, status_set in expected.items():
            resp = self._resp(path)
            self.assertEqual(
                sorted(resp.keys()), status_set,
                f"{path}: status-set PHẢI = {status_set} (in-handler 404/422/409 KHÔNG status-line key).",
            )
            for dead_key in ("404", "422", "409"):
                self.assertNotIn(
                    dead_key, resp,
                    f"{path}: '{dead_key}' KHÔNG được là status-line key — in-handler arrive HTTP-200+Error "
                    "(route theo body.http_status, KHÔNG status-line). Dead-deser nếu giữ.",
                )

    def test_mob_oas_18e_no_dead_inhandler_response_component_referenced(self):
        """(3-regress) NotFound404/Unprocessable422/Conflict409 KHÔNG còn referenced từ 3 create
        path (đã gom vào nhánh Error 200) — chống tái phát dead-deser status-line key."""
        dead_resp_refs = {
            "#/components/responses/NotFound404",
            "#/components/responses/Unprocessable422",
            "#/components/responses/Conflict409",
        }
        for path in _CREATE_PATH_ENVELOPE:
            resp = self._resp(path)
            referenced = {v.get("$ref") for v in resp.values() if isinstance(v, dict) and v.get("$ref")}
            leaked = referenced & dead_resp_refs
            self.assertEqual(
                leaked, set(),
                f"{path}: status-line key vẫn $ref in-handler response {leaked} — dead-deser tái phát.",
            )


class TestMobileListReadContract(unittest.TestCase):
    """TC-MOB-OAS-14 — Phase-C list-read contract cho 3 list path (§6.1/§6.2).

    Đóng băng hợp đồng list-read thành guard chạy được (chống bịa param / drift envelope):
      (a) 3 list path RỜI _STUB_PATHS (200 KHÔNG còn Stub) NHƯNG GIỮ _MVP_BUSINESS_PATHS.
      (b) Mỗi list path có ĐỦ pagination param query đúng tên/$ref:
            imm08/09 = filters + page + page_size; imm12 = status+severity+asset+open + page+page_size.
      (c) param Page/PageSize đúng tên+type+default+min/max (page int default1 min1;
          page_size int default20 min1 max100) — KHỚP utils/pagination.py:7-8 + signature LIVE.
      (d) imm12 `open` enum [0,1] + filters JSON-string default '{}' (imm08/09) — đúng signature.
      (e) 200 trỏ ĐÚNG list-envelope rows-key PHÂN BIỆT: imm08/09→WorkOrderList (data.data[]),
          imm12→IncidentList (data.items[]). 401/403 GIỮ nguyên; KHÔNG requestBody (list = GET).
      (f) 2 envelope schema có rows-key đúng: WorkOrderListEnvelope=data.{pagination,data};
          IncidentListEnvelope=data.{pagination,items}; cả 2 dùng CHUNG Pagination sub-schema.
      (g) LIVE introspect: page/page_size (+ filters / status,severity,asset,open) CÓ THẬT trong
          signature whitelist imm08.list_pm_work_orders / imm09.list_repair_work_orders /
          imm12.list_incidents — yaml param KHÔNG bịa so với hàm thật.
    SSoT: ../04-api-contract.md §6.1/§6.2 + ADR-MOBILE-001 (g) + imm08.py:28/imm09.py:21/imm12.py:197.
    """

    @classmethod
    def setUpClass(cls):
        cls.spec = _load_spec() if _MOBILE_YAML.exists() else None

    def _op(self, path):
        return ((self.spec.get("paths") or {}).get(path) or {}).get("get") or {}

    def _param_refs(self, op):
        return {p.get("$ref") for p in (op.get("parameters") or []) if p.get("$ref")}

    def _resolve(self, ref):
        """Resolve #/... pointer → node (dict). None nếu không resolve."""
        if not ref or not ref.startswith("#/"):
            return None
        cur = self.spec
        for raw in ref[2:].split("/"):
            part = raw.replace("~1", "/").replace("~0", "~")
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return None
        return cur

    def test_mob_oas_14a_list_paths_left_stub_kept_mvp(self):
        """(a) 3 list path RỜI _STUB_PATHS (200 != Stub) NHƯNG GIỮ _MVP_BUSINESS_PATHS."""
        for lp in _LIST_PATHS:
            self.assertNotIn(lp, _STUB_PATHS, f"{lp} phải RỜI _STUB_PATHS (Phase-C list-read).")
            self.assertIn(lp, _MVP_BUSINESS_PATHS, f"{lp} phải GIỮ _MVP_BUSINESS_PATHS (401/403 symmetry).")
            op = self._op(lp)
            ref200 = ((op.get("responses") or {}).get("200") or {}).get("$ref")
            self.assertNotEqual(
                ref200, "#/components/responses/Stub",
                f"{lp} 200 KHÔNG còn Stub (đã bồi list-envelope Phase-C).",
            )

    def test_mob_oas_14b_pagination_params_present(self):
        """(b) Mỗi list path có ĐỦ pagination param query đúng $ref (KHỚP signature LIVE)."""
        for lp, expected in _LIST_PARAM_EXPECT.items():
            op = self._op(lp)
            got = self._param_refs(op)
            self.assertEqual(
                got, expected,
                f"{lp} param query LỆCH. expected={sorted(expected)} got={sorted(got)}",
            )

    def test_mob_oas_14c_page_pagesize_schema_exact(self):
        """(c) Page/PageSize param đúng tên+type+default+min/max (pagination.py:7-8)."""
        page = self._resolve(_PAGE_REF) or {}
        self.assertEqual(page.get("name"), "page")
        self.assertEqual(page.get("in"), "query")
        psch = page.get("schema") or {}
        self.assertEqual(psch.get("type"), "integer", "page type=integer.")
        self.assertEqual(psch.get("default"), 1, "page default=1 (pagination.py:7).")
        self.assertEqual(psch.get("minimum"), 1, "page minimum=1.")

        size = self._resolve(_PAGE_SIZE_REF) or {}
        self.assertEqual(size.get("name"), "page_size")
        ssch = size.get("schema") or {}
        self.assertEqual(ssch.get("type"), "integer", "page_size type=integer.")
        self.assertEqual(ssch.get("default"), 20, "page_size default=20 (pagination.py:8).")
        self.assertEqual(ssch.get("minimum"), 1, "page_size minimum=1.")
        self.assertEqual(ssch.get("maximum"), 100, "page_size maximum=100 (clamp 1..100).")

    def test_mob_oas_14d_filter_param_shapes(self):
        """(d) imm08/09 filters JSON-string default '{}'; imm12 open enum [0,1] int."""
        wof = self._resolve(_WO_FILTERS_REF) or {}
        self.assertEqual(wof.get("name"), "filters")
        wsch = wof.get("schema") or {}
        self.assertEqual(wsch.get("type"), "string", "filters type=string (JSON-encoded).")
        self.assertEqual(wsch.get("default"), "{}", "filters default '{}' (signature LIVE).")

        op = self._resolve("#/components/parameters/IncidentOpen") or {}
        self.assertEqual(op.get("name"), "open")
        osch = op.get("schema") or {}
        self.assertEqual(osch.get("type"), "integer", "open type=integer (0|1).")
        self.assertEqual(osch.get("default"), 0, "open default=0.")
        self.assertEqual(osch.get("enum"), [0, 1], "open enum=[0,1].")
        for ref in ("#/components/parameters/IncidentStatus",
                    "#/components/parameters/IncidentSeverity",
                    "#/components/parameters/IncidentAsset"):
            p = self._resolve(ref) or {}
            self.assertEqual((p.get("schema") or {}).get("type"), "string", f"{ref} type=string.")
            self.assertEqual((p.get("schema") or {}).get("default"), "", f"{ref} default ''.")

    def test_mob_oas_14e_200_points_to_distinct_envelope(self):
        """(e) 200 trỏ list-envelope rows-key PHÂN BIỆT; 401/403 GIỮ; KHÔNG requestBody (GET)."""
        for lp, exp_resp in _LIST_RESP_EXPECT.items():
            op = self._op(lp)
            resp = op.get("responses") or {}
            self.assertEqual(
                (resp.get("200") or {}).get("$ref"), exp_resp,
                f"{lp} 200 phải trỏ {exp_resp} (rows-key đúng @source — §6.2).",
            )
            self.assertEqual(
                (resp.get("401") or {}).get("$ref"), "#/components/responses/Unauthorized401",
                f"{lp} 401 GIỮ Unauthorized401.",
            )
            self.assertEqual(
                (resp.get("403") or {}).get("$ref"), "#/components/responses/Forbidden",
                f"{lp} 403 GIỮ Forbidden.",
            )
            self.assertNotIn("requestBody", op, f"{lp} là GET — KHÔNG requestBody.")
            self.assertEqual(
                sorted(resp.keys()), ["200", "401", "403"],
                f"{lp} status set = [200,401,403]: {sorted(resp.keys())}",
            )

    def test_mob_oas_14f_envelope_rows_key_distinct(self):
        """(f) 2 envelope rows-key đúng + dùng CHUNG Pagination; PaginatedListEnvelope đã gỡ."""
        wo = self._resolve(_WO_LIST_SCHEMA_REF) or {}
        wo_data = ((wo.get("properties") or {}).get("data") or {})
        wo_props = wo_data.get("properties") or {}
        self.assertIn("data", wo_props, "WorkOrderListEnvelope rows-key PHẢI là `data` (imm08/09).")
        self.assertEqual(wo_props["data"].get("type"), "array", "WO rows = array.")
        self.assertEqual(
            (wo_props.get("pagination") or {}).get("$ref"), "#/components/schemas/Pagination",
            "WorkOrderListEnvelope dùng CHUNG Pagination.",
        )
        self.assertEqual(sorted(wo_data.get("required") or []), ["data", "pagination"])

        inc = self._resolve(_INCIDENT_LIST_SCHEMA_REF) or {}
        inc_data = ((inc.get("properties") or {}).get("data") or {})
        inc_props = inc_data.get("properties") or {}
        self.assertIn("items", inc_props, "IncidentListEnvelope rows-key PHẢI là `items` (imm12).")
        self.assertEqual(inc_props["items"].get("type"), "array", "Incident rows = array.")
        self.assertEqual(
            (inc_props.get("pagination") or {}).get("$ref"), "#/components/schemas/Pagination",
            "IncidentListEnvelope dùng CHUNG Pagination.",
        )
        self.assertEqual(sorted(inc_data.get("required") or []), ["items", "pagination"])

        # PaginatedListEnvelope orphan cũ ĐÃ GỠ (tách 2 envelope).
        self.assertIsNone(
            self._resolve("#/components/schemas/PaginatedListEnvelope"),
            "PaginatedListEnvelope phải ĐÃ GỠ (tách WorkOrder/Incident envelope — §6.2).",
        )

    def test_mob_oas_14g_params_match_live_signature(self):
        """(g) LIVE introspect — page/page_size (+ filters / status,severity,asset,open) CÓ THẬT
        trong signature whitelist (yaml KHÔNG bịa param so với hàm thật @source).
        """
        for lp, (modname, fnname, expected_args) in _LIST_LIVE_FN.items():
            mod = importlib.import_module(modname)
            fn = getattr(mod, fnname, None)
            self.assertIsNotNone(fn, f"Thiếu hàm whitelist LIVE: {modname}.{fnname}")
            sig = inspect.signature(fn)
            live_args = set(sig.parameters.keys())
            self.assertTrue(
                expected_args <= live_args,
                f"{modname}.{fnname} signature LIVE thiếu param yaml-khai: "
                f"expected⊆ {sorted(expected_args)} got {sorted(live_args)}",
            )
            # page/page_size BẮT BUỘC có thật ở MỌI list path.
            for must in ("page", "page_size"):
                self.assertIn(
                    must, live_args,
                    f"{modname}.{fnname} PHẢI có param `{must}` LIVE (pagination contract).",
                )


def _satisfies_required(sample: dict, required: set) -> bool:
    """True nếu `sample` mang ĐỦ mọi key required (điều kiện CẦN để validate-pass schema-object).

    Dùng để chứng minh disambiguation: dispatcher-403 raw KHÔNG đủ required của Error envelope.
    """
    return required.issubset(set(sample.keys()))


def _violates_closed_shape(sample: dict, allowed_keys: set) -> bool:
    """True nếu `sample` mang key NGOÀI tập cho phép — vi phạm additionalProperties:false (closed).

    Dùng để chứng minh disambiguation: Error envelope mang success/error/code/http_status =
    key NGOÀI {exc_type,exception,exc,_server_messages} ⇒ KHÔNG validate-pass FrappeRawError-closed.
    """
    return bool(set(sample.keys()) - allowed_keys)


def _nodes_with_ref_and_sibling(spec: dict) -> list[str]:
    """Walk toàn spec — trả path-breadcrumb của MỌI node-dict vừa có `$ref` vừa có key khác.

    OAS 3.0.3: sibling cạnh `$ref` bị BỎ QUA → spectral / openapi-generator --strict warning.
    """
    offenders: list[str] = []

    def _walk(node, where):
        if isinstance(node, dict):
            if "$ref" in node and len(node) > 1:
                siblings = sorted(k for k in node if k != "$ref")
                offenders.append(f"{where} (sibling: {siblings})")
            for k, v in node.items():
                _walk(v, f"{where}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                _walk(v, f"{where}[{i}]")

    _walk(spec, "$")
    return offenders


class TestMobileOAS19Disambiguation(unittest.TestCase):
    """TC-MOB-OAS-19a/b/c/d — P1 contract-correctness: 403 oneOf machine-distinguishability
    (FrappeRawError additionalProperties:false) + gỡ $ref-with-sibling (codegen --strict).

    Introspection-only (đọc yaml, no DB, no live BE). SSoT: docs/mobile/04-api-contract.md §5/§5b
    + ADR-MOBILE-001 (f).
    """

    @classmethod
    def setUpClass(cls):
        cls.spec = _load_spec() if _MOBILE_YAML.exists() else None

    def test_mob_oas_19a_frappe_raw_error_closed_shape(self):
        """(19a) FrappeRawError.additionalProperties === false (machine-distinguishable raw branch)
        + required==[exc_type] vẫn GIỮ.

        Closed-shape = cơ chế disambiguation: Error envelope (mang key ngoài 4 raw-key) KHÔNG
        validate-pass FrappeRawError khi additionalProperties:false → codegen route đúng nhánh oneOf.
        """
        fre = ((self.spec.get("components") or {}).get("schemas") or {}).get("FrappeRawError") or {}
        self.assertTrue(fre, "Thiếu schema FrappeRawError.")
        self.assertEqual(
            fre.get("additionalProperties"), False,
            "FrappeRawError.additionalProperties PHẢI === false (closed-shape = disambiguation "
            "mechanism cho oneOf 403; Error envelope mang key ngoài 4 raw-key → loại trừ nhánh raw).",
        )
        self.assertEqual(
            fre.get("required") or [], ["exc_type"],
            "FrappeRawError.required PHẢI GIỮ == [exc_type] (response.py:46 LUÔN set).",
        )
        # §5c UPDATE (Self-Correction R1) — Error NAY CŨNG closed (additionalProperties:false). Mọi
        #   notification-extension field (fields/context/message_code/action_hint/severity/title) ĐÃ
        #   khai property → đóng KHÔNG drop field hợp lệ. Đóng Error: (1) 200-oneOf [Created|Error]
        #   máy-phân-biệt (thay discriminator boolean illegal); (2) 403-oneOf MẠNH hơn (cả 2 nhánh
        #   closed = strictly mutual-exclusive). Disambiguation 19d (sample-based) KHÔNG đổi.
        err = ((self.spec.get("components") or {}).get("schemas") or {}).get("Error") or {}
        self.assertTrue(err, "Thiếu schema Error.")
        self.assertEqual(
            err.get("additionalProperties"), False,
            "Error PHẢI closed (additionalProperties:false, §5c) — mọi notification-extension field đã "
            "khai property nên đóng không drop gì; đóng để 200-oneOf [Created|Error] máy-phân-biệt + "
            "403-oneOf strictly mutual-exclusive (cả 2 nhánh closed).",
        )

    def test_mob_oas_19b_no_ref_with_sibling(self):
        """(19b) 0 node nào vừa có `$ref` vừa có sibling-key toàn spec (chống tái phát
        $ref-with-sibling; phủ 3 create requestBody + bất kỳ node khác).

        OAS 3.0.3 BỎ QUA sibling cạnh `$ref` → spectral/openapi-generator --strict warning →
        CI codegen strict-mode CÓ THỂ FAIL.
        """
        offenders = _nodes_with_ref_and_sibling(self.spec)
        self.assertEqual(
            offenders, [],
            f"$ref-with-sibling (OAS 3.0.3 bỏ qua sibling — codegen --strict warning): {offenders}",
        )

    def test_mob_oas_19c_reqbody_ref_only_and_component_required(self):
        """(19c) 3 path requestBody = {$ref-only} (no `required` sibling) ĐỒNG THỜI
        components.requestBodies/*Body.required === true (required CHUYỂN ĐÚNG chỗ, không mất ràng buộc).
        """
        ops = {path: op for path, _, op in _iter_operations(self.spec)}
        for path, expected_ref in _REQBODY_PATHS.items():
            self.assertIn(path, ops, f"Thiếu path: {path}")
            rb = (ops[path].get("requestBody") or {})
            self.assertEqual(
                set(rb.keys()), {"$ref"},
                f"{path} requestBody PHẢI CHỈ có key `$ref` (gỡ sibling `required`/khác): {sorted(rb.keys())}",
            )
            self.assertEqual(
                rb.get("$ref"), expected_ref,
                f"{path} requestBody.$ref lệch: got {rb.get('$ref')}",
            )
        # required CHUYỂN sang component (không mất ràng buộc).
        comp_rb = (self.spec.get("components") or {}).get("requestBodies") or {}
        for name in _REQBODY_COMPONENTS:
            body = comp_rb.get(name) or {}
            self.assertTrue(body, f"Thiếu component requestBodies/{name}.")
            self.assertEqual(
                body.get("required"), True,
                f"components.requestBodies/{name}.required PHẢI === true (required giữ nội bộ component).",
            )

    def test_mob_oas_19d_forbidden_oneof_branches_mutually_exclusive(self):
        """(19d) disambiguation property — ReportIncidentForbidden.oneOf=[Error,FrappeRawError]:
        mẫu dispatcher-403 {exc_type:'PermissionError'} KHÔNG thoả required của Error (thiếu
        success/error/code/http_status) VÀ mẫu in-handler {success:false,error,code:'FORBIDDEN',
        http_status:403} KHÔNG thoả FrappeRawError-closed (additionalProperties:false + key lạ)
        → 2 shape loại trừ nhau (codegen route đúng nhánh theo shape).
        """
        comps = (self.spec.get("components") or {})
        rifb = (comps.get("responses") or {}).get("ReportIncidentForbidden") or {}
        schema = (((rifb.get("content") or {}).get("application/json") or {}).get("schema") or {})
        one_of = schema.get("oneOf") or []
        refs = {b.get("$ref") for b in one_of if isinstance(b, dict)}
        self.assertEqual(
            refs, {_ERROR_ENVELOPE_SCHEMA_REF, _FRAPPE_RAW_ERROR_SCHEMA_REF},
            f"ReportIncidentForbidden.oneOf PHẢI = [Error, FrappeRawError]: {sorted(refs)}",
        )
        # Error required + FrappeRawError closed-allowed-keys lấy TỪ spec (không hard-code rời nguồn).
        err = (comps.get("schemas") or {}).get("Error") or {}
        err_required = set(err.get("required") or [])
        self.assertEqual(
            err_required, _ERROR_REQUIRED_KEYS,
            f"Error.required lệch kỳ vọng (disambiguation dựa vào): {sorted(err_required)}",
        )
        fre = (comps.get("schemas") or {}).get("FrappeRawError") or {}
        self.assertIs(
            fre.get("additionalProperties"), False,
            "FrappeRawError PHẢI additionalProperties:false (closed) để (19d) thành lập.",
        )
        fre_allowed = set((fre.get("properties") or {}).keys())

        # (1) dispatcher-403 raw thoả FrappeRawError (đủ exc_type, KHÔNG key lạ) NHƯNG KHÔNG thoả Error.
        self.assertTrue(
            _satisfies_required(_SAMPLE_DISPATCHER_403, _FRAPPE_RAW_ERROR_REQUIRED)
            and not _violates_closed_shape(_SAMPLE_DISPATCHER_403, fre_allowed),
            "Mẫu dispatcher-403 PHẢI validate-pass FrappeRawError (nhánh raw).",
        )
        self.assertFalse(
            _satisfies_required(_SAMPLE_DISPATCHER_403, err_required),
            "Mẫu dispatcher-403 KHÔNG được thoả required của Error (thiếu success/error/code/http_status) "
            "— nếu thoả = 2 nhánh oneOf ambiguous.",
        )

        # (2) in-handler-200 Error thoả Error required NHƯNG vi phạm FrappeRawError-closed (key lạ).
        self.assertTrue(
            _satisfies_required(_SAMPLE_INHANDLER_403, err_required),
            "Mẫu in-handler cap-403 PHẢI validate-pass Error (nhánh envelope).",
        )
        self.assertTrue(
            _violates_closed_shape(_SAMPLE_INHANDLER_403, fre_allowed),
            "Mẫu in-handler cap-403 PHẢI vi phạm FrappeRawError-closed (mang key ngoài "
            f"{sorted(fre_allowed)} khi additionalProperties:false) — đó là cơ chế disambiguation.",
        )


class TestMobileTypedReads(unittest.TestCase):
    """TC-MOB-OAS-20 — R4 §8.7: 4 STUB read/create rời _STUB_PATHS với typed `data` GROUNDED
    chữ-ký service THẬT (KHÔNG bịa field). Introspect 200 schema typed (KHÔNG còn responses/Stub):
      - resolveQrToken    → QrResolveEnvelope.data = QrResolveResult (imm00.py:303-315).
      - getAssetScanInfo  → AssetScanInfoEnvelope.data = AssetScanInfo (imm00.py:567-602) gồm
                            available_actions[]=AvailableAction {key,label,route,enabled,reason} +
                            pm_overdue/calibration_overdue (server-flag SSoT).
      - getAsset          → AssetDetailEnvelope.data = AssetDetail (imm00.py:288-324, overdue flags).
      - createPmWorkOrder → 200-oneOf [CreatePmWorkOrderCreatedEnvelope | Error] §5c (closed-schema).
    2 device-token (register/unregister) GIỮ STUB (handler CHƯA tồn tại @source — ADR-MOBILE-001 h).
    """

    @classmethod
    def setUpClass(cls):
        cls.spec = _load_spec() if _MOBILE_YAML.exists() else None

    def _get_200_schema(self, path, verb="get"):
        op = ((self.spec.get("paths") or {}).get(path) or {}).get(verb) or {}
        return _200_schema(op.get("responses") or {}), op

    def test_mob_oas_20a_typed_reads_not_stub(self):
        """3 typed read 200 KHÔNG còn $ref responses/Stub — đã có inline schema $ref typed envelope."""
        expect = {
            "/api/method/assetcore.api.imm00.resolve_qr_token": "#/components/schemas/QrResolveEnvelope",
            "/api/method/assetcore.api.imm00.get_asset_scan_info": "#/components/schemas/AssetScanInfoEnvelope",
            "/api/method/assetcore.api.imm00.get_asset": "#/components/schemas/AssetDetailEnvelope",
        }
        for path, env_ref in expect.items():
            schema200, op = self._get_200_schema(path)
            self.assertNotEqual(
                ((op.get("responses") or {}).get("200") or {}).get("$ref"),
                "#/components/responses/Stub",
                f"{path} 200 vẫn trỏ responses/Stub — phải typed (R4 §8.7).",
            )
            self.assertEqual(
                schema200.get("$ref"), env_ref,
                f"{path} 200 schema PHẢI $ref {env_ref}, got {schema200.get('$ref')}",
            )
            self.assertTrue(_resolve_pointer(env_ref, self.spec), f"{env_ref} dangling")

    def test_mob_oas_20b_scan_info_available_actions_typed(self):
        """getAssetScanInfo.data = AssetScanInfo có available_actions[]=AvailableAction
        {key,label,route,enabled,reason} (GROUNDED imm00.py:528-534) + 2 cờ overdue server-flag."""
        schemas = (self.spec.get("components") or {}).get("schemas") or {}
        info = schemas.get("AssetScanInfo") or {}
        props = info.get("properties") or {}
        # available_actions = array items $ref AvailableAction.
        aa = props.get("available_actions") or {}
        self.assertEqual(aa.get("type"), "array", "AssetScanInfo.available_actions PHẢI array.")
        self.assertEqual(
            (aa.get("items") or {}).get("$ref"), "#/components/schemas/AvailableAction",
            "available_actions[] PHẢI $ref AvailableAction.",
        )
        action = schemas.get("AvailableAction") or {}
        self.assertEqual(
            set((action.get("properties") or {}).keys()), {"key", "label", "route", "enabled", "reason"},
            "AvailableAction PHẢI shape CHÍNH XÁC {key,label,route,enabled,reason} (imm00.py:528-534).",
        )
        self.assertEqual(
            set(action.get("required") or []), {"key", "label", "route", "enabled", "reason"},
            "AvailableAction.required PHẢI gồm đủ 5 field (KHÔNG optional — service luôn trả).",
        )
        # 2 cờ overdue server-flag (FE CHỈ render — KHÔNG so ngày client).
        for flag in ("pm_overdue", "calibration_overdue"):
            self.assertEqual(
                (props.get(flag) or {}).get("type"), "boolean",
                f"AssetScanInfo.{flag} PHẢI boolean (server-flag SSoT).",
            )
            self.assertIn(flag, info.get("required") or [], f"{flag} PHẢI required (luôn trả).")

    def test_mob_oas_20c_typed_envelopes_closed_and_grounded(self):
        """4 typed envelope (QrResolve/AssetScanInfo/AssetDetail/CreatePmWorkOrderCreated) +
        AssetScanInfo/QrResolveResult/CreatePmWorkOrderResponse có data typed (KHÔNG any-type)."""
        schemas = (self.spec.get("components") or {}).get("schemas") or {}
        # Envelope data $ref typed (KHÔNG free-form như Envelope/Stub).
        env_data = {
            "QrResolveEnvelope": "#/components/schemas/QrResolveResult",
            "AssetScanInfoEnvelope": "#/components/schemas/AssetScanInfo",
            "AssetDetailEnvelope": "#/components/schemas/AssetDetail",
            "CreatePmWorkOrderCreatedEnvelope": "#/components/schemas/CreatePmWorkOrderResponse",
        }
        for env_name, data_ref in env_data.items():
            env = schemas.get(env_name) or {}
            self.assertTrue(env, f"Thiếu schema {env_name} (R4 §8.7).")
            self.assertEqual(
                ((env.get("properties") or {}).get("data") or {}).get("$ref"), data_ref,
                f"{env_name}.data PHẢI $ref {data_ref} (typed, KHÔNG any-type).",
            )
            self.assertTrue(_resolve_pointer(data_ref, self.spec), f"{data_ref} dangling")
        # createPm 200 = oneOf [Created | Error] closed (§5c) — KHÔNG discriminator.
        schema200, _ = self._get_200_schema(_CREATE_PM_PATH, verb="post")
        refs = [b.get("$ref") for b in (schema200.get("oneOf") or []) if isinstance(b, dict)]
        self.assertIn("#/components/schemas/CreatePmWorkOrderCreatedEnvelope", refs, "createPm 200 thiếu nhánh Created.")
        self.assertIn(_ERROR_SCHEMA_REF, refs, "createPm 200 thiếu nhánh Error.")
        self.assertNotIn("discriminator", schema200, "createPm 200 KHÔNG được có discriminator boolean (§5c).")
        # CreatePmWorkOrderResponse GROUNDED imm08.py:836-840 {name,status,checklist_items_count}.
        pm_resp = schemas.get("CreatePmWorkOrderResponse") or {}
        self.assertEqual(
            set((pm_resp.get("properties") or {}).keys()), {"name", "status", "checklist_items_count"},
            "CreatePmWorkOrderResponse PHẢI {name,status,checklist_items_count} (imm08.py:836-840).",
        )


if __name__ == "__main__":
    unittest.main()
