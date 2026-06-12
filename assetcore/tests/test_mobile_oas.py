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
    info.title/version đóng băng (0.1.0-skeleton) + đúng 16 path (C4: +openid_profile).
  - TC-MOB-OAS-02: 16/16 path-operation CÓ operationId (0 None).
  - TC-MOB-OAS-03: operationId DUY NHẤT toàn file (len(set)==len(list)==16).
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
revoke_token→revokeOAuthToken, openid_profile→getUserInfo [C4]); GET-list→listX; create_X→createX; report_X→reportX;
get_X→getX; resolve_qr_token→resolveQrToken; get_asset_scan_info→getAssetScanInfo.

Run: bench --site miyano run-tests --module assetcore.tests.test_mobile_oas
"""
from __future__ import annotations

import re
import copy
import importlib
import inspect
import json
import unittest
from pathlib import Path

import yaml

# docs/mobile/openapi/assetcore-mobile.openapi.yaml — repo-relative (4 cấp lên từ file test).
#   assetcore/assetcore/tests/test_mobile_oas.py → repo root = parents[2]
_REPO_ROOT = Path(__file__).resolve().parents[2]
_MOBILE_YAML = _REPO_ROOT / "docs" / "mobile" / "openapi" / "assetcore-mobile.openapi.yaml"

# C-DoD-CFG (Vòng 12) — openapitools.json @repo-root = RUNNABLE codegen-config (NAY có khối
#   generators 3 target trỏ mobile YAML). Guard `TestMobileCodegenConfig` validate config NÀY
#   bằng STDLIB json.load (KHÔNG cần java/npx/toolchain) — đảm bảo handoff codegen ở máy USER
#   KHÔNG fail-câm do config rời khỏi YAML.
_OPENAPITOOLS_JSON = _REPO_ROOT / "openapitools.json"
# generator-cli.version PIN @source (NOT empty, NOT skeleton/placeholder).
_OPENAPITOOLS_VERSION = "7.23.0"

# F-C4 (Vòng 13) — state-reconciliation roadmap §3. `13-be-completion-roadmap.md` từng quảng-cáo
#   việc-đã-xong (4 scan/createPm typed C2 + list-element C3-split) NHƯ việc-cần-làm (4-STUB/
#   15-path stale prose). Guard `TestMobileRoadmapStateReconciled` raw-text scan roadmap chống
#   tái-drift §3↔source: 0 anchor stale + claim "16 path" khớp len(spec.paths) THẬT + ref
#   _STUB_PATHS dùng dạng-SYMBOL (KHÔNG số-dòng-tuyệt-đối — line-ref tuyệt-đối CHẾT do drift).
_ROADMAP_MD = _REPO_ROOT / "docs" / "mobile" / "13-be-completion-roadmap.md"
# Anchor STALE — mô tả trạng-thái CŨ (4-STUB/15-path/chưa-typed) như HIỆN-HÀNH/TO-BUILD.
#   Cho phép DUY NHẤT dạng lịch-sử khi cùng dòng đánh dấu [SUPERSEDED] hoặc @landing (mốc quá-khứ).
_ROADMAP_STALE_ANCHORS = (
    r"\b15 path\b",
    r"15/15 operationId",
    r"4 STUB path còn lại",
    r"chưa typed",
    r"còn generic ⚠️",
    r"152-157",
)

_HTTP_VERBS = ("get", "post", "put", "delete", "patch", "head", "options", "trace")

# ── F-C3 (Vòng 11) — META-GUARD count-self-verify SSoT ──────────────────────────
# SSoT con-số test-method của CHÍNH module này, định-nghĩa MỘT LẦN. Meta-guard
# `TestMobileOasCountSelfVerify.test_mob_oas_NN_count_matches_ssot` introspect TẤT CẢ
# TestCase trong module + đếm method `test*` LOAD ĐƯỢC rồi assert == hằng này. Drift
# sau-này (thêm/bớt TC mà quên cập const) = RED NGAY (chống tái count-drift 106↔107).
# Đây là count-AFTER-add (gồm chính meta-guard) ⇒ 108. Doc count-hiện-hành = giá-trị này.
# C-DoD-CFG (Vòng 12): +10 TC class `TestMobileCodegenConfig` (codegen-config-validity guard) ⇒ 118.
# F-C4 (Vòng 13): +4 TC class `TestMobileRoadmapStateReconciled` (stale-line-ref guard §3↔source) ⇒ 122.
# EPIC-D D4 (Vòng 17): +9 TC class `TestMobileDeviceTokenTyped` (device-token typed gỡ STUB) ⇒ 131.
# EPIC-D D4 (Vòng 17 follow-up): +1 TC `test_mob_oas_22j_yaml_path_resolves_to_whitelisted_callable`
#   (codegen↔runtime dead-end guard — path yaml PHẢI resolve+is_whitelisted, bịt lỗ 404) ⇒ 132.
# EPIC-D D6 (Vòng 20): +1 TC `test_mob_oas_13b_429_set_matches_rate_limit_decorator_at_source`
#   (AST-derive @rate_limit @source == OAS 429-set — bịt drift D6 register_device_token quên 429) ⇒ 133.
# F-B2 (Vòng 31 closure): +4 TC class `TestMobileRefreshOn401DocGuard` (refresh-on-401 doc-presence
#   drift-guard — invariant 401→refresh-1-lần→retry→fail-re-auth nguyên-văn trong 03 §2.5/§2.6 + 04
#   §9d(n) + cross-file grant_type=refresh_token parity + RED-before string-mutate) ⇒ 137.
# G3 (EPIC-G G3 AUTO-part): +4 TC class `TestMobileTracebackHardeningDocGuard` (prod-hardening
#   'TẮT allow_error_traceback System Setting=0' doc-presence drift-guard — item+evidence
#   `response.py:60-65` + negation 'KHÔNG ... developer_mode' nguyên-văn ở 08 §4 ∩ ADR-004
#   Consequences + 10 §6.2 reload `--preload`/rate-limit-header note + RED-before string-mutate) ⇒ 141.
_EXPECTED_TEST_COUNT = 141

# camelCase verbNoun: bắt đầu chữ thường, không gạch dưới/space, không kết thúc số dính.
_CAMEL_RE = re.compile(r"^[a-z][a-zA-Z0-9]*$")

# SSoT convention map — dotted-path (tail) → operationId mong đợi. Phase C bồi path mới
# PHẢI thêm dòng tương ứng theo CÙNG luật (../04-api-contract.md §8.1).
_EXPECTED = {
    "/api/method/frappe.integrations.oauth2.authorize": ("get", "authorizeOAuth"),
    "/api/method/frappe.integrations.oauth2.get_token": ("post", "getOAuthToken"),
    "/api/method/frappe.integrations.oauth2.revoke_token": ("post", "revokeOAuthToken"),
    # C4 — OIDC userinfo/whoami (Frappe core openid_profile). verb-first oauth-style opId
    #   (giống getOAuthToken/authorizeOAuth) — KHÔNG dùng tail dotted-path 'openidProfile'
    #   (chọn getUserInfo theo §8.1: nhóm auth verb-first). security [openid] (oauth2.py:163 bearer).
    "/api/method/frappe.integrations.oauth2.openid_profile": ("get", "getUserInfo"),
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

# EPIC-D / D4 — DEVICE-TOKEN TYPED paths (rời STUB vòng này). Handler api/mobile/v1 wrap service
#   D2 (mobile_device_token.py) sau bearer: register_device_token (trả `name` str → data:string) /
#   unregister_device_token (trả None → data:null). requestBody DeviceTokenRequest + 200 oneOf
#   [<Created>|Error] closed-schema Decision-B. operationId FROZEN (A5 — _DEVICE_TOKEN_FROZEN GIỮ).
#   Guard typed = TC-MOB-OAS-07 (rewrite: assert typed-not-Stub) + TC-MOB-OAS-22 (TestMobileDeviceTokenTyped).
_DEVICE_TOKEN_PATHS = set(_DEVICE_TOKEN_FROZEN)
_REGISTER_DEVICE_TOKEN_PATH = "/api/method/assetcore.api.mobile.v1.register_device_token"
_UNREGISTER_DEVICE_TOKEN_PATH = "/api/method/assetcore.api.mobile.v1.unregister_device_token"
_DEVICE_TOKEN_BODY_REF = "#/components/requestBodies/DeviceTokenBody"
_DEVICE_TOKEN_SCHEMA_REF = "#/components/schemas/DeviceTokenRequest"
_DEVICE_TOKEN_REQUIRED = ["fcm_token"]                       # @mobile_device_token.py:94-101 (chỉ fcm_token no-default cho dedup)
_DEVICE_TOKEN_PLATFORM_ENUM = ["android", "ios"]             # @mobile_device_token.py:56 _VALID_PLATFORMS
# `user` KHÔNG được lọt vào body — server ÉP frappe.session.user (chống spoof §6.2, mobile_device_token.py:139).
_DEVICE_TOKEN_FORBIDDEN_PROP = "user"
_REGISTER_CREATED_ENVELOPE_REF = "#/components/schemas/RegisterDeviceTokenCreatedEnvelope"
_UNREGISTER_ACK_ENVELOPE_REF = "#/components/schemas/UnregisterDeviceTokenAckEnvelope"

# _STUB_PATHS — path CÒN STUB THẬT (200 trỏ #/components/responses/Stub, 0 typed data). Sau D4:
#   2 device-token RỜI STUB (typed requestBody + 200 oneOf, handler api/mobile/v1 wrap service D2)
#   ⇒ _STUB_PATHS = ∅ (0 STUB-on-MVP). Mọi 12 path MVP nay TYPED (04 §8.7 + EPIC-D-push-fcm.md §D4).
_STUB_PATHS = set()

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

# Auth-flow path Frappe-core (oauth2.*): NẰM NGOÀI 401/403 symmetry MVP-business (TC-12).
#   3 path guest-flow (authorize=302, get_token/revoke=200/400) KHÔNG declare 401/403.
#   C4: + openid_profile (bearer-gated whitelist KHÔNG allow_guest oauth2.py:163) → declare 401
#   (no-token/expired) NHƯNG status-set Frappe-core RAW {200,401}, KHÔNG theo 403-symmetry
#   MVP-business (KHÔNG Forbidden component; userinfo guest = dispatcher-401 RAW Frappe). ⇒ loại
#   _AUTH_PATHS khỏi tập symmetry để 401/403 MVP-business GIỮ 12==12.
_AUTH_PATHS = {
    "/api/method/frappe.integrations.oauth2.authorize",
    "/api/method/frappe.integrations.oauth2.get_token",
    "/api/method/frappe.integrations.oauth2.revoke_token",
    "/api/method/frappe.integrations.oauth2.openid_profile",
}
# C4 — userinfo/whoami path (OIDC). Bearer-gated nhưng auth-flow Frappe-core (KHÔNG MVP-business).
_USERINFO_PATH = "/api/method/frappe.integrations.oauth2.openid_profile"

# 3 path có @rate_limit THẬT @source → 429: resolve_qr_token (imm00.py:311) +
#   get_asset_scan_info (imm00.py:354) + register_device_token (mobile/v1/device_token.py:62,
#   D6 chống spam đăng ký). KHÔNG path nào khác có @rate_limit MVP ⇒ wire 429 chỗ khác = bịa
#   hợp đồng. NOTE: bảng này là SSoT-mirror; consistency vs decorator THẬT @source được khóa
#   bởi test_mob_oas_13b (AST-derive) — thêm @rate_limit mà quên 429 (drift D6) = FAIL ở đó.
_PATHS_REQUIRE_429 = {
    "/api/method/assetcore.api.imm00.resolve_qr_token",
    "/api/method/assetcore.api.imm00.get_asset_scan_info",
    "/api/method/assetcore.api.mobile.v1.register_device_token",
}

# Map operationId-path → (module, function) để AST-derive @rate_limit @source (test_mob_oas_13b).
#   Khóa drift: tập path có @rate_limit THẬT phải == _PATHS_REQUIRE_429 (== tập declare 429 trong OAS).
_RATE_LIMIT_SOURCE_MAP = {
    "/api/method/assetcore.api.imm00.resolve_qr_token": ("assetcore.api.imm00", "resolve_qr_token"),
    "/api/method/assetcore.api.imm00.get_asset_scan_info": ("assetcore.api.imm00", "get_asset_scan_info"),
    "/api/method/assetcore.api.mobile.v1.register_device_token": (
        "assetcore.api.mobile.v1.device_token", "register_device_token",
    ),
    # Endpoint MVP còn lại KHÔNG @rate_limit (phải VẮNG khỏi tập derive — chống bịa).
    "/api/method/assetcore.api.mobile.v1.unregister_device_token": (
        "assetcore.api.mobile.v1.device_token", "unregister_device_token",
    ),
    "/api/method/assetcore.api.imm12.report_incident": ("assetcore.api.imm12", "report_incident"),
    "/api/method/assetcore.api.imm09.create_repair_work_order": ("assetcore.api.imm09", "create_repair_work_order"),
    "/api/method/assetcore.api.imm08.create_pm_work_order": ("assetcore.api.imm08", "create_pm_work_order"),
    "/api/method/assetcore.api.imm11.create_calibration": ("assetcore.api.imm11", "create_calibration"),
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
#   route-by-VALUE (Decision-B, KHÔNG discriminator-object). in-handler error 404/422 (report)
#   arrive HTTP status-line 200 + Error body (quirk §5) → KHÔNG keyed dưới HTTP-code response-key
#   (dead-deser branch). Gom vào nhánh Error của 200-oneOf; client route theo GIÁ TRỊ body.success
#   (Created.success.enum=[true] vs Error.success.enum=[false] qua closed-schema) + body.http_status.
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
# G-OAS-STATUSLINE — CreatedEnvelope named schema cho 200-oneOf route-by-VALUE (KHÔNG discriminator).
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
# G-OAS-STATUSLINE — CreatedEnvelope named schema cho 200-oneOf route-by-VALUE (KHÔNG discriminator).
#   404/409 (imm11.py:999/1002) arrive HTTP-200+Error → gom vào nhánh Error, KHÔNG status-line key.
_CAL_CREATE_CREATED_ENVELOPE_REF = "#/components/schemas/CreateCalibrationCreatedEnvelope"
# createCalibration status-set MỚI (G-OAS-STATUSLINE): 404/409 in-handler KHÔNG còn status-line
#   key. 401/403 GIỮ (dispatcher status-line THẬT) → symmetry 12 BẤT BIẾN.
_CAL_CREATE_STATUS_SET = ["200", "401", "403"]

# C-LISTREAD — pagination param + list-envelope refs (Phase-C list-read). Signature LIVE
#   introspect (imm08.list_pm_work_orders:28 / imm09.list_repair_work_orders:21 /
#   imm12.list_incidents:197). C3-split: 3 envelope PHÂN BIỆT (§6.2 / ADR (g) / roadmap §3.3):
#   PmWorkOrderListEnvelope=data.data[] (imm08), RepairWorkOrderListEnvelope=data.data[] (imm09),
#   IncidentListEnvelope=data.items[] (imm12). PM/CM rows-key GIỐNG (`data`) NHƯNG field-disjoint.
_PAGE_REF = "#/components/parameters/Page"
_PAGE_SIZE_REF = "#/components/parameters/PageSize"
_WO_FILTERS_REF = "#/components/parameters/WorkOrderFilters"
_PM_WO_LIST_RESP_REF = "#/components/responses/PmWorkOrderList"
_REPAIR_WO_LIST_RESP_REF = "#/components/responses/RepairWorkOrderList"
_INCIDENT_LIST_RESP_REF = "#/components/responses/IncidentList"
_PM_WO_LIST_SCHEMA_REF = "#/components/schemas/PmWorkOrderListEnvelope"
_REPAIR_WO_LIST_SCHEMA_REF = "#/components/schemas/RepairWorkOrderListEnvelope"
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
# 200-response MONG ĐỢI (C3-split: mỗi endpoint trỏ response RIÊNG → element RIÊNG).
_LIST_RESP_EXPECT = {
    _LIST_PM_PATH: _PM_WO_LIST_RESP_REF,
    _LIST_REPAIR_PATH: _REPAIR_WO_LIST_RESP_REF,
    _LIST_INCIDENT_PATH: _INCIDENT_LIST_RESP_REF,
}
# Tên hàm whitelist LIVE (introspect signature — page/page_size có THẬT).
_LIST_LIVE_FN = {
    _LIST_PM_PATH: ("assetcore.api.imm08", "list_pm_work_orders", {"filters", "page", "page_size"}),
    _LIST_REPAIR_PATH: ("assetcore.api.imm09", "list_repair_work_orders", {"filters", "page", "page_size"}),
    _LIST_INCIDENT_PATH: ("assetcore.api.imm12", "list_incidents",
                          {"status", "severity", "asset", "open", "page", "page_size"}),
}

# ─── C3-split — 2 list-ELEMENT schema FIELD-DISJOINT (Pm/RepairWorkOrderListItem) — TC-MOB-OAS-21 ───
#   Đóng KNOWN-GAP "KHÔNG ép chung" (ADR-MOBILE-001 (g) / roadmap §3.3): PM(imm08) ≠ CM(imm09)
#   field-set ⇒ KHÔNG ép 1 UNION schema. Tách 2 element-schema RIÊNG, mỗi cái CHỈ field service
#   tương ứng phát + 2 envelope RIÊNG + 2 response RIÊNG (rows-key `data` GIỮ nguyên cả 2).
#   QUYẾT ĐỊNH BA = Option A (closed-schema KHÔNG discriminator = Decision-B): mỗi schema
#   all-optional trừ `name` REQUIRED (PK chung). Field-set RE-VERIFIED @source (D4: mở file,
#   tìm symbol — KHÔNG tin số dòng):
#     • imm08 list_work_orders (PM): repo-fields + enrich asset_name/location_name/
#       assigned_to_name/supervisor_name (services/imm08.py def list_work_orders).
#     • imm09 list_work_orders (CM): repo-fields (parts_hold_started bị `r.pop()` → KHÔNG
#       ra wire) + enrich asset_name/department_name/location_name/assigned_to_name +
#       derived is_sla_breached/sla_paused (services/imm09.py def list_work_orders +
#       _enrich_rows + _enrich_sla_breach).
#     • imm12 list_incidents: 23 repo-field + enrich asset_name/reporter_name/
#       assigned_to_name + derived is_response_breached/is_resolution_breached
#       (services/imm12.py def list_incidents + _enrich_asset_names + _enrich_sla_breach).
#   Guard chốt: 2 element là $ref RIÊNG per-envelope (KHÔNG generic object, KHÔNG union chung) +
#   `name` required + closed-schema + field-set DISJOINT đúng chữ-ký service + 0 dangling.
_PM_WO_LIST_ITEM_REF = "#/components/schemas/PmWorkOrderListItem"
_REPAIR_WO_LIST_ITEM_REF = "#/components/schemas/RepairWorkOrderListItem"
_INCIDENT_LIST_ITEM_REF = "#/components/schemas/IncidentListItem"
# PmWorkOrderListItem = CHỈ field imm08.list_work_orders — grounded @source C3-split.
_PM_WO_FIELDS = {
    "name", "asset_ref", "pm_type", "wo_type", "status", "due_date", "completion_date",
    "assigned_to", "supervisor", "overall_result", "is_late", "source_pm_wo",
    "asset_name", "location_name", "assigned_to_name", "supervisor_name",
}
# RepairWorkOrderListItem = CHỈ field imm09.list_work_orders — grounded @source C3-split.
_REPAIR_WO_FIELDS = {
    "name", "asset_ref", "asset_name", "repair_type", "priority", "status",
    "open_datetime", "completion_datetime", "mttr_hours", "sla_breached",
    "sla_target_hours", "is_repeat_failure", "assigned_to", "root_cause_category",
    "risk_class", "parts_hold_hours", "department_name", "location_name",
    "assigned_to_name", "is_sla_breached", "sla_paused",
}
# DISJOINT-EXCEPT-OVERLAP: 2 doctype CÙNG trả vài key chung (PK + asset/assigned/location/status).
#   Phần KHÁC NHAU (field RIÊNG mỗi loại) PHẢI hoàn toàn disjoint — đây là chứng cứ "KHÔNG ép chung".
_WO_SHARED_FIELDS = _PM_WO_FIELDS & _REPAIR_WO_FIELDS
_PM_ONLY_FIELDS = _PM_WO_FIELDS - _REPAIR_WO_FIELDS
_REPAIR_ONLY_FIELDS = _REPAIR_WO_FIELDS - _PM_WO_FIELDS
# IncidentListItem = imm12 23 repo-field + 3 enrich + 2 derived — grounded @source C3.
_INCIDENT_LIST_ITEM_FIELDS = {
    "name", "asset", "incident_type", "severity", "status", "fault_code",
    "reported_by", "reported_at", "description", "linked_capa", "linked_repair_wo",
    "rca_required", "rca_record", "chronic_failure_flag", "patient_affected",
    "closed_date", "assigned_to", "acknowledged_at", "resolved_at",
    "response_breached", "resolution_breached", "response_due_at", "resolution_due_at",
    "asset_name", "reporter_name", "assigned_to_name",
    "is_response_breached", "is_resolution_breached",
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
    #   3 status-line key khỏi 3 create path + gom lỗi vào nhánh Error của 200-oneOf (route-by-VALUE)
    #   ⇒ 3 response component này RỜI khỏi path (HẾT referenced) → ORPHAN trở lại → vào allow-list
    #   (forward-reserve: vẫn doc-intent + có thể wire Phase-E nếu after_request hook đổi status-line).
    "#/components/responses/NotFound404",          # in-handler 404 (HTTP-200+Error) → doc-only note
    "#/components/responses/Unprocessable422",     # in-handler 422 (HTTP-200+Error) → doc-only note
    "#/components/responses/Conflict409",          # in-handler 409 + offline reuse → doc-only note
    # EPIC-D D4 (Vòng 17): 2 device-token RỜI Stub (typed requestBody + 200 oneOf, wrap service D2)
    #   ⇒ responses/Stub HẾT referenced (0 path MVP còn dùng) → ORPHAN. GIỮ component như
    #   forward-reserve (negative-injection guard 23d/24e inject ref này vào deepcopy để chứng RED-before;
    #   gỡ component = phá precondition test). Vào allow-list (đồng bộ 04 §8.2). Orphan: +1.
    "#/components/responses/Stub",                  # D4: device-token typed → Stub HẾT ref → forward-reserve
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


# ── C4 — guard requestBody dual content-type (form+json) cho MỌI RPC create-path ──
#   Frappe /api/method đọc form_dict (form-encoded mặc định, hoặc Content-Type:application/json
#   tường minh) ⇒ codegen JSON-only client KHÔNG khai form → field tới handler RỖNG (sai-âm-thầm).
#   Mọi requestBody RPC PHẢI khai CẢ application/json + application/x-www-form-urlencoded (04 §4/§9).
#   Scope = 4 AssetCore create RPC (3 create-triad $ref-component + createPm inline). KHÔNG gồm
#   oauth flow get_token/revoke (Frappe-core form-only theo OAuth2/RFC 7009 — KHÔNG AssetCore RPC).
_RPC_FORM_JSON_PATHS = (
    "/api/method/assetcore.api.imm12.report_incident",
    "/api/method/assetcore.api.imm09.create_repair_work_order",
    "/api/method/assetcore.api.imm11.create_calibration",
    "/api/method/assetcore.api.imm08.create_pm_work_order",
)
_RPC_FORM_JSON_MEDIA = {"application/json", "application/x-www-form-urlencoded"}


def _resolve_request_body(spec: dict, op: dict) -> dict:
    """Trả requestBody của operation, RESOLVE $ref về components.requestBodies nếu có (stdlib)."""
    rb = op.get("requestBody") or {}
    ref = rb.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/components/requestBodies/"):
        name = ref.split("/")[-1]
        return ((spec.get("components") or {}).get("requestBodies") or {}).get(name) or {}
    return rb


def _assert_rpc_requestbody_form_json(tc, spec: dict) -> None:
    """C4 guard — MỌI RPC create-path (3 create-triad + createPm sau C2) khai requestBody CÓ ĐỦ
    2 content-type application/json + application/x-www-form-urlencoded (Frappe RPC form_dict).

    Resolve $ref-component (3 create-triad) HOẶC inline (createPm). 0 path trong scope thiếu 1
    trong 2 media-type ⇒ codegen sinh client gửi đúng Content-Type → field KHÔNG rỗng ở handler.
    """
    ops = {path: op for path, _, op in _iter_operations(spec)}
    missing: list[str] = []
    for path in _RPC_FORM_JSON_PATHS:
        op = ops.get(path) or {}
        rb = _resolve_request_body(spec, op)
        content = set((rb.get("content") or {}).keys())
        if content != _RPC_FORM_JSON_MEDIA:
            missing.append(f"{path}: content={sorted(content)} (cần {sorted(_RPC_FORM_JSON_MEDIA)})")
    tc.assertEqual(
        missing, [],
        "RPC create-path THIẾU dual content-type form+json (codegen JSON-only → field RỖNG, 04 §4/§9): "
        f"{missing}",
    )


class TestMobileOASLint(unittest.TestCase):
    """Lint guard contract-identity cho mobile OpenAPI (no DB)."""

    @classmethod
    def setUpClass(cls):
        cls.assertTrueExists = _MOBILE_YAML.exists()
        cls.spec = _load_spec() if cls.assertTrueExists else None

    def test_mob_oas_01_lint_and_frozen_meta(self):
        """yaml hợp lệ + openapi 3.0.3 + info title/version đóng băng + đúng 16 path.

        C4: 15→16 (thêm GET openid_profile — OIDC userinfo/whoami).
        """
        self.assertTrue(_MOBILE_YAML.exists(), f"Thiếu file: {_MOBILE_YAML}")
        spec = self.spec
        self.assertIsInstance(spec, dict, "safe_load phải trả dict")
        self.assertEqual(spec.get("openapi"), "3.0.3")
        info = spec.get("info") or {}
        self.assertEqual(info.get("title"), "AssetCore Mobile API")
        self.assertEqual(info.get("version"), "0.1.0-skeleton")
        self.assertEqual(len(spec.get("paths") or {}), 16, "Phải đúng 16 path mobile MVP (C4: +openid_profile)")

    def test_mob_oas_02_all_paths_have_operation_id(self):
        """16/16 path-operation CÓ operationId — 0 None (C4: +getUserInfo)."""
        missing = [
            f"{verb.upper()} {path}"
            for path, verb, op in _iter_operations(self.spec)
            if not op.get("operationId")
        ]
        self.assertEqual(missing, [], f"Path thiếu operationId: {missing}")
        ids = [op["operationId"] for _, _, op in _iter_operations(self.spec)]
        self.assertEqual(len(ids), 16, "Phải đúng 16 operationId (C4: +getUserInfo)")

    def test_mob_oas_03_operation_id_unique(self):
        """operationId DUY NHẤT toàn file: len(set)==len(list)==16 (C4: +getUserInfo)."""
        ids = [op["operationId"] for _, _, op in _iter_operations(self.spec)]
        dupes = sorted({x for x in ids if ids.count(x) > 1})
        self.assertEqual(dupes, [], f"operationId trùng: {dupes}")
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(set(ids)), 16)

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

    def test_mob_oas_07_no_stub_on_mvp(self):
        """STUB-D4-07: 0 STUB-on-MVP — MỌI 12 path MVP nay TYPED (device-token rời STUB ở D4).

        Sau D4 §8.7: 2 device-token (register/unregister) RỜI _STUB_PATHS — handler api/mobile/v1
        wrap service D2 (mobile_device_token.py) GROUNDED chữ-ký THẬT ⇒ typed requestBody
        (DeviceTokenRequest) + 200 oneOf [<Created>|Error] (KHÔNG còn 200→responses/Stub). Cùng
        report/createRepair/createCal/3-list (Phase-C) + 3 typed read + createPm (R4). Sau D4
        _STUB_PATHS = ∅. Chống bồi STUB lén tái-xuất + chống path MVP nào còn 200→Stub.
        """
        ops = {path: op for path, _, op in _iter_operations(self.spec)}
        # MỌI path Phase-C/R4 đã rời STUB.
        for tp in (
            {_REPORT_INCIDENT_PATH, _REPAIR_CREATE_PATH, _CAL_CREATE_PATH, _CREATE_PM_PATH}
            | _LIST_PATHS | _TYPED_READ_PATHS
        ):
            self.assertNotIn(
                tp, _STUB_PATHS,
                f"{tp} phải RỜI _STUB_PATHS (Phase-C/R4 typed) — nếu còn = guard sai.",
            )
        # D4 — 2 device-token RỜI _STUB_PATHS (typed requestBody + 200 oneOf, wrap service D2).
        for dtp in _DEVICE_TOKEN_PATHS:
            self.assertNotIn(
                dtp, _STUB_PATHS,
                f"{dtp} phải RỜI _STUB_PATHS (D4 typed device-token) — nếu còn = guard sai.",
            )
        # Sau D4 _STUB_PATHS = ∅ (0 STUB-on-MVP).
        self.assertEqual(
            _STUB_PATHS, set(),
            "Sau D4 _STUB_PATHS PHẢI = ∅ (device-token typed, 0 STUB-on-MVP). 04 §8.7 + EPIC-D-push-fcm.md §D4.",
        )
        # ANTI-REGRESS: KHÔNG path MVP nào còn 200→responses/Stub (chống bồi STUB lén tái-xuất).
        for path in (_MVP_BUSINESS_PATHS | _DEVICE_TOKEN_PATHS):
            self.assertIn(path, ops, f"Thiếu MVP path: {path}")
            op = ops[path]
            resp200 = (op.get("responses") or {}).get("200") or {}
            self.assertNotEqual(
                resp200.get("$ref"), "#/components/responses/Stub",
                f"MVP path 200 KHÔNG được trỏ responses/Stub (đã typed ở Phase-C/R4/D4): {path}",
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
        #     200-oneOf (route-by-VALUE). ⇒ KHÔNG path NÀO declare 404/422/409 status-line key.
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
        #   closed-schema + envelope ở TC-MOB-OAS-18). Ở đây canh status-set TỐI GIẢN = [200,401,403].
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
        #     C4: openid_profile (bearer-gated userinfo) status-set = {200, 401} — RAW Frappe-core
        #     (200 OidcUserInfo passthrough + 401 dispatcher no-token/expired). KHÔNG 403/429.
        _AUTH_EXPECTED_STATUS = {
            "/api/method/frappe.integrations.oauth2.authorize": {"302"},
            "/api/method/frappe.integrations.oauth2.get_token": {"200", "400"},
            "/api/method/frappe.integrations.oauth2.revoke_token": {"200"},
            "/api/method/frappe.integrations.oauth2.openid_profile": {"200", "401"},
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

    def test_mob_oas_13b_429_set_matches_rate_limit_decorator_at_source(self):
        """A13b — TẬP path declare 429 trong OAS == TẬP endpoint có @rate_limit THẬT @source (AST).

        BỊT DRIFT (root-cause D6): _PATHS_REQUIRE_429 (test_mob_oas_13) là bảng HARDCODE — thêm
        @rate_limit vào endpoint mới (D6: register_device_token) mà quên cập nhật bảng + quên wire
        429 trong OAS = contract drift ÂM THẦM (codegen client KHÔNG có nhánh backoff, runtime 429
        bất ngờ). Guard này AST-derive decorator THẬT từ source rồi đối chiếu 3 chiều:
          (1) tập endpoint @rate_limit @source == _PATHS_REQUIRE_429 (bảng SSoT đồng bộ),
          (2) endpoint @rate_limit @source phải declare 429 trong OAS (no missing),
          (3) endpoint KHÔNG @rate_limit @source KHÔNG được declare 429 (no fabricated).
        Thêm @rate_limit nơi khác mà quên 429 ⇒ FAIL (1)/(2); wire 429 bịa ⇒ FAIL (1)/(3).
        """
        import ast
        import importlib.util

        def _has_rate_limit_decorator(module_path: str, func_name: str) -> bool:
            spec = importlib.util.find_spec(module_path)
            self.assertIsNotNone(spec, f"Không tìm thấy module {module_path}")
            src_file = spec.origin
            tree = ast.parse(Path(src_file).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == func_name:
                    names = []
                    for dec in node.decorator_list:
                        target = dec.func if isinstance(dec, ast.Call) else dec
                        if isinstance(target, ast.Name):
                            names.append(target.id)
                        elif isinstance(target, ast.Attribute):
                            names.append(target.attr)
                    return "rate_limit" in names
            self.fail(f"Không tìm thấy hàm {func_name} trong {module_path}")

        derived_rate_limited = {
            path
            for path, (mod, fn) in _RATE_LIMIT_SOURCE_MAP.items()
            if _has_rate_limit_decorator(mod, fn)
        }

        # (1) Tập @rate_limit @source PHẢI == bảng SSoT _PATHS_REQUIRE_429.
        self.assertEqual(
            derived_rate_limited, _PATHS_REQUIRE_429,
            "DRIFT: tập endpoint có @rate_limit @source != _PATHS_REQUIRE_429. "
            f"@source={sorted(derived_rate_limited)} vs bảng={sorted(_PATHS_REQUIRE_429)}. "
            "Thêm @rate_limit (vd D6 register) mà quên cập nhật bảng+OAS = contract drift.",
        )

        # (2)+(3) OAS 429 declaration PHẢI khớp 1:1 tập @rate_limit @source.
        ops = {path: op for path, _, op in _iter_operations(self.spec)}
        _R429 = "#/components/responses/RateLimited429"
        oas_with_429 = {
            path
            for path, (mod, fn) in _RATE_LIMIT_SOURCE_MAP.items()
            if ((ops.get(path) or {}).get("responses") or {}).get("429", {}).get("$ref") == _R429
        }
        self.assertEqual(
            oas_with_429, derived_rate_limited,
            "OAS 429-set KHÔNG khớp @rate_limit @source. "
            f"missing-429={sorted(derived_rate_limited - oas_with_429)} "
            f"fabricated-429={sorted(oas_with_429 - derived_rate_limited)}.",
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
        #   C4: LOẠI _AUTH_PATHS (oauth2.* flow Frappe-core) khỏi tập symmetry — openid_profile
        #   declare 401 (bearer-gated) nhưng auth-flow RAW (KHÔNG 403-Forbidden MVP) ⇒ 12==12 GIỮ.
        paths_with_403 = sorted(
            path for path, op in ops.items()
            if "403" in (op.get("responses") or {}) and path not in _AUTH_PATHS
        )
        self.assertEqual(
            paths_with_403, sorted(_PATHS_REQUIRE_403),
            f"Tập path declare 403 (trừ auth-flow) phải == 12 path MVP (đối xứng 401): {paths_with_403}",
        )
        paths_with_401 = {
            path for path, op in ops.items()
            if "401" in (op.get("responses") or {}) and path not in _AUTH_PATHS
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
        """(6) G-OAS-STATUSLINE — reportIncident 200 = oneOf [Created, Error] route-by-VALUE
        body.success (KHÔNG discriminator, Decision-B); 401=Unauthorized401, 403=ReportIncidentForbidden
        (dual-shape). in-handler 404/422 (HTTP-200+Error) KHÔNG còn status-line key (dead-deser) →
        gom nhánh Error. status-set = [200,401,403] (symmetry 12 GIỮ: 401+403 declare đủ)."""
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
        #   data $ref ReportIncidentResponse + success.enum:[true] (nhánh success=true route-by-VALUE, KHÔNG discriminator).
        env = ((self.spec.get("components") or {}).get("schemas") or {}).get("ReportIncidentCreatedEnvelope") or {}
        self.assertTrue(env, "Thiếu schema ReportIncidentCreatedEnvelope (G-OAS-STATUSLINE).")
        self.assertEqual(
            ((env.get("properties") or {}).get("success") or {}).get("enum"), [True],
            "ReportIncidentCreatedEnvelope.success.enum PHẢI = [true] (nhánh success=true route-by-VALUE, KHÔNG discriminator).",
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
        """(g) G-OAS-STATUSLINE — 200 = oneOf [Created, Error] route-by-VALUE body.success (KHÔNG
        discriminator, Decision-B); 401=Unauthorized401, 403=Forbidden (SINGLE-SHAPE). in-handler
        404/409 (imm09.py:746/753, HTTP-200+Error) KHÔNG còn status-line key (dead-deser) → gom
        nhánh Error. status-set = [200,401,403] (symmetry 12 GIỮ)."""
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
        #   với data $ref response schema + success.enum:[true] (nhánh success=true route-by-VALUE, KHÔNG discriminator).
        env = (((self.spec.get("components") or {}).get("schemas") or {})
               .get("CreateRepairWorkOrderCreatedEnvelope") or {})
        self.assertTrue(env, "Thiếu schema CreateRepairWorkOrderCreatedEnvelope (G-OAS-STATUSLINE).")
        self.assertEqual(
            ((env.get("properties") or {}).get("success") or {}).get("enum"), [True],
            "CreateRepairWorkOrderCreatedEnvelope.success.enum PHẢI = [true] (nhánh success=true route-by-VALUE, KHÔNG discriminator).",
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
        """(g) G-OAS-STATUSLINE — 200 = oneOf [Created, Error] route-by-VALUE body.success (KHÔNG
        discriminator, Decision-B); 401=Unauthorized401, 403=Forbidden (SINGLE-SHAPE). in-handler
        404/409 (imm11.py:999/1002, HTTP-200+Error) KHÔNG còn status-line key (dead-deser) → gom
        nhánh Error. status-set = [200,401,403] (symmetry 12 GIỮ)."""
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
        #   data $ref response schema + success.enum:[true] (nhánh success=true route-by-VALUE, KHÔNG discriminator).
        env = (((self.spec.get("components") or {}).get("schemas") or {})
               .get("CreateCalibrationCreatedEnvelope") or {})
        self.assertTrue(env, "Thiếu schema CreateCalibrationCreatedEnvelope (G-OAS-STATUSLINE).")
        self.assertEqual(
            ((env.get("properties") or {}).get("success") or {}).get("enum"), [True],
            "CreateCalibrationCreatedEnvelope.success.enum PHẢI = [true] (nhánh success=true route-by-VALUE, KHÔNG discriminator).",
        )
        data_ref = ((env.get("properties") or {}).get("data") or {}).get("$ref")
        self.assertEqual(
            data_ref, _CAL_CREATE_RESPONSE_SCHEMA_REF,
            f"CreateCalibrationCreatedEnvelope.data PHẢI $ref CreateCalibrationResponse, got {data_ref}",
        )


class TestMobileDeviceTokenTyped(unittest.TestCase):
    """TC-MOB-OAS-22 — EPIC-D / D4: 2 device-token TYPED (gỡ 2 STUB cuối). Handler api/mobile/v1
    wrap service D2 (mobile_device_token.py) sau bearer.

    Đóng băng hợp đồng device-token thành guard chạy được (chống bịa field / drift / spoof-leak —
    bám SOURCE mobile_device_token.py, KHÔNG bám chữ đề mục):
      (a) register/unregister_device_token.post CÓ requestBody $ref DeviceTokenBody + operationId
          FROZEN (registerDeviceToken/unregisterDeviceToken — A5).
      (b) requestBodies/DeviceTokenBody required:true + content json+form $ref DeviceTokenRequest.
      (c) DeviceTokenRequest.required EXACT = [fcm_token] (chỉ fcm_token no-default khóa dedup
          @mobile_device_token.py:94-101); additionalProperties:false (closed — codegen KHÔNG sinh thừa).
      (d) platform enum == [android, ios] (Select-canonical _VALID_PLATFORMS @mobile_device_token.py:56);
          device_label/app_version optional present (telemetry).
      (e) ANTI-SPOOF (§6.2) — `user` KHÔNG ở properties: server ÉP frappe.session.user
          (signature KHÔNG nhận user; **_ignore nuốt — @mobile_device_token.py:94-100,139).
      (f) content = json + x-www-form-urlencoded (Frappe RPC form_dict — CÙNG $ref schema).
      (g) 200 = oneOf [<Created>|Error] CLOSED-SCHEMA disjoint required-set (Decision-B §5c,
          KHÔNG discriminator); 401=Unauthorized401, 403=Forbidden (single-shape dispatcher-403).
          status-set = [200,401,403] (symmetry 12 GIỮ — bearer-gated self-service D-A2).
      (h) RegisterDeviceTokenCreatedEnvelope.data = STRING (`name` hash @mobile_device_token.py:153/166,
          _ok(str) — KHÔNG object {device_token_id}, BA gate KHÔNG bịa wrap); success.enum=[true].
          UnregisterDeviceTokenAckEnvelope.data = nullable (LUÔN null — _ok(None) @mobile_device_token.py:172);
          success.enum=[true]. CẢ 2 closed-schema + required[success,data] disjoint Error.
    SSoT: ../../docs/mobile/04-api-contract.md §8.7 + completion/EPIC-D-push-fcm.md §D4 +
          ../../docs/imm-00/ADR-IMM00-OPENAPI.md §D-OAS-DEVTOK + services/mobile_device_token.py:56,94-101,139,153,166,172.
    """

    @classmethod
    def setUpClass(cls):
        cls.spec = _load_spec() if _MOBILE_YAML.exists() else None

    def _op(self, path):
        return ((self.spec.get("paths") or {}).get(path) or {}).get("post") or {}

    def test_mob_oas_22a_paths_have_request_body_ref_and_frozen_opid(self):
        """(a) 2 device-token.post requestBody = $ref-ONLY DeviceTokenBody + operationId FROZEN."""
        for path, frozen_id in _DEVICE_TOKEN_FROZEN.items():
            op = self._op(path)
            self.assertEqual(op.get("operationId"), frozen_id, f"operationId FROZEN (A5): {path}")
            rb = op.get("requestBody") or {}
            self.assertTrue(rb, f"{path} PHẢI có requestBody (D4 typed).")
            self.assertEqual(
                set(rb.keys()), {"$ref"},
                f"{path} requestBody PHẢI CHỈ key `$ref` (gỡ sibling — OAS 3.0.3): {sorted(rb.keys())}",
            )
            self.assertEqual(
                rb.get("$ref"), _DEVICE_TOKEN_BODY_REF,
                f"{path} requestBody phải $ref DeviceTokenBody, got {rb.get('$ref')}",
            )

    def test_mob_oas_22b_component_request_body_wraps_schema(self):
        """(b) requestBodies/DeviceTokenBody required:true + json $ref DeviceTokenRequest."""
        comp = ((self.spec.get("components") or {}).get("requestBodies") or {}).get("DeviceTokenBody") or {}
        self.assertTrue(comp, "Thiếu component requestBodies/DeviceTokenBody.")
        self.assertEqual(comp.get("required"), True, "Component required PHẢI true.")
        schema_ref = (((comp.get("content") or {}).get("application/json") or {}).get("schema") or {}).get("$ref")
        self.assertEqual(
            schema_ref, _DEVICE_TOKEN_SCHEMA_REF,
            f"DeviceTokenBody json PHẢI $ref DeviceTokenRequest, got {schema_ref}",
        )

    def test_mob_oas_22c_schema_required_exact_and_closed(self):
        """(c) DeviceTokenRequest.required EXACT = [fcm_token] + additionalProperties:false."""
        sch = ((self.spec.get("components") or {}).get("schemas") or {}).get("DeviceTokenRequest") or {}
        self.assertTrue(sch, "Thiếu schema DeviceTokenRequest.")
        self.assertEqual(
            sorted(sch.get("required") or []), sorted(_DEVICE_TOKEN_REQUIRED),
            f"required PHẢI EXACT {_DEVICE_TOKEN_REQUIRED} (chỉ fcm_token no-default @mobile_device_token.py:94-101).",
        )
        self.assertEqual(
            sch.get("additionalProperties"), False,
            "DeviceTokenRequest PHẢI additionalProperties:false (closed — codegen KHÔNG sinh field thừa).",
        )

    def test_mob_oas_22d_platform_enum_and_optionals(self):
        """(d) platform enum [android,ios] (Select-canonical) + device_label/app_version optional present."""
        props = (((self.spec.get("components") or {}).get("schemas") or {})
                 .get("DeviceTokenRequest") or {}).get("properties") or {}
        self.assertEqual(
            (props.get("platform") or {}).get("enum"), _DEVICE_TOKEN_PLATFORM_ENUM,
            f"platform enum PHẢI = {_DEVICE_TOKEN_PLATFORM_ENUM} (_VALID_PLATFORMS @mobile_device_token.py:56).",
        )
        self.assertEqual((props.get("fcm_token") or {}).get("type"), "string", "fcm_token PHẢI string.")
        for opt in ("device_label", "app_version"):
            self.assertIn(opt, props, f"optional `{opt}` PHẢI có (telemetry @mobile_device_token.py:98-99).")

    def test_mob_oas_22e_no_user_field_leak_anti_spoof(self):
        """(e) ANTI-SPOOF §6.2 — `user` KHÔNG ở properties (server ÉP session, **_ignore nuốt)."""
        props = (((self.spec.get("components") or {}).get("schemas") or {})
                 .get("DeviceTokenRequest") or {}).get("properties") or {}
        self.assertNotIn(
            _DEVICE_TOKEN_FORBIDDEN_PROP, props,
            "`user` KHÔNG được ở requestBody — server ÉP frappe.session.user (chống spoof §6.2, "
            "mobile_device_token.py:94-100,139). Khai `user` = codegen client gửi → spoof-surface.",
        )

    def test_mob_oas_22f_request_body_content_dual_media_type(self):
        """(f) DeviceTokenBody.content = json + x-www-form-urlencoded (CÙNG $ref). Frappe RPC form_dict."""
        comp = ((self.spec.get("components") or {}).get("requestBodies") or {}).get("DeviceTokenBody") or {}
        content = comp.get("content") or {}
        self.assertEqual(
            set(content.keys()), {"application/json", "application/x-www-form-urlencoded"},
            "DeviceTokenBody.content PHẢI = {json, x-www-form-urlencoded} (Frappe RPC form_dict, 04 §8.7).",
        )
        for mt in content:
            ref = ((content.get(mt) or {}).get("schema") or {}).get("$ref")
            self.assertEqual(
                ref, _DEVICE_TOKEN_SCHEMA_REF,
                f"media-type {mt} PHẢI $ref DeviceTokenRequest (CÙNG schema), got {ref}",
            )

    def test_mob_oas_22g_register_response_surface_oneof_closed(self):
        """(g) register 200 = oneOf [RegisterCreated, Error] closed-schema (Decision-B); 401/403 GIỮ.

        D6: register CÓ @rate_limit(10/60s/IP) chống spam (device_token.py:62) ⇒ status-set thêm
        429 (RateLimited429). status-set = [200,401,403,429]. unregister KHÔNG @rate_limit ⇒ GIỮ
        [200,401,403]. Symmetry-401/403 (12-path) BẤT BIẾN — 429 là surface BỔ SUNG, KHÔNG đụng 401/403.
        """
        resp = (self._op(_REGISTER_DEVICE_TOKEN_PATH).get("responses") or {})
        _assert_200_oneof_closed_distinct(self, resp, _REGISTER_CREATED_ENVELOPE_REF, "registerDeviceToken")
        self.assertEqual(
            resp.get("401", {}).get("$ref"), "#/components/responses/Unauthorized401",
            "registerDeviceToken 401 PHẢI GIỮ Unauthorized401 (pre-handler status-line THẬT).",
        )
        self.assertEqual(
            resp.get("403", {}).get("$ref"), "#/components/responses/Forbidden",
            "registerDeviceToken 403 PHẢI = Forbidden (single-shape dispatcher-403 guest/no-token, D-A2).",
        )
        self.assertEqual(
            resp.get("429", {}).get("$ref"), "#/components/responses/RateLimited429",
            "registerDeviceToken 429 PHẢI = RateLimited429 (D6 @rate_limit device_token.py:62 trip).",
        )
        self.assertEqual(
            sorted(resp.keys()), ["200", "401", "403", "429"],
            f"registerDeviceToken status-set PHẢI = [200,401,403,429] (D6 @rate_limit): {sorted(resp.keys())}",
        )

    def test_mob_oas_22h_unregister_response_surface_oneof_closed(self):
        """(g) unregister 200 = oneOf [UnregisterAck, Error] closed-schema (Decision-B); 401/403 GIỮ."""
        resp = (self._op(_UNREGISTER_DEVICE_TOKEN_PATH).get("responses") or {})
        _assert_200_oneof_closed_distinct(self, resp, _UNREGISTER_ACK_ENVELOPE_REF, "unregisterDeviceToken")
        self.assertEqual(
            resp.get("401", {}).get("$ref"), "#/components/responses/Unauthorized401",
            "unregisterDeviceToken 401 PHẢI GIỮ Unauthorized401.",
        )
        self.assertEqual(
            resp.get("403", {}).get("$ref"), "#/components/responses/Forbidden",
            "unregisterDeviceToken 403 PHẢI = Forbidden (single-shape dispatcher-403, D-A2).",
        )
        self.assertEqual(
            sorted(resp.keys()), ["200", "401", "403"],
            f"unregisterDeviceToken status-set PHẢI = [200,401,403]: {sorted(resp.keys())}",
        )

    def test_mob_oas_22i_created_envelopes_grounded_service_return(self):
        """(h) Created envelopes GROUNDED service return: register data=STRING (`name`), unregister
        data=nullable (None→null). CẢ 2 closed + success.enum=[true] + required[success,data]."""
        schemas = (self.spec.get("components") or {}).get("schemas") or {}
        reg = schemas.get("RegisterDeviceTokenCreatedEnvelope") or {}
        self.assertTrue(reg, "Thiếu schema RegisterDeviceTokenCreatedEnvelope.")
        self.assertEqual(reg.get("additionalProperties"), False, "Register envelope PHẢI closed.")
        self.assertEqual(
            ((reg.get("properties") or {}).get("success") or {}).get("enum"), [True],
            "Register success.enum PHẢI = [true] (route-by-VALUE Decision-B).",
        )
        reg_data = (reg.get("properties") or {}).get("data") or {}
        self.assertEqual(
            reg_data.get("type"), "string",
            "Register data PHẢI type string (`name` hash @mobile_device_token.py:153/166 — KHÔNG object {device_token_id}).",
        )
        self.assertEqual(
            sorted(reg.get("required") or []), ["data", "success"],
            "Register required PHẢI = [success,data] (disjoint Error[success,error,code,http_status]).",
        )
        unreg = schemas.get("UnregisterDeviceTokenAckEnvelope") or {}
        self.assertTrue(unreg, "Thiếu schema UnregisterDeviceTokenAckEnvelope.")
        self.assertEqual(unreg.get("additionalProperties"), False, "Unregister envelope PHẢI closed.")
        self.assertEqual(
            ((unreg.get("properties") or {}).get("success") or {}).get("enum"), [True],
            "Unregister success.enum PHẢI = [true].",
        )
        unreg_data = (unreg.get("properties") or {}).get("data") or {}
        self.assertEqual(
            unreg_data.get("nullable"), True,
            "Unregister data PHẢI nullable:true (LUÔN null — _ok(None) @mobile_device_token.py:172).",
        )
        self.assertEqual(
            unreg_data.get("type"), "string",
            "Unregister data PHẢI có sibling `type` (chống orphan-nullable TC-08); nullable:true.",
        )
        self.assertEqual(
            sorted(unreg.get("required") or []), ["data", "success"],
            "Unregister required PHẢI = [success,data] (disjoint Error).",
        )

    def test_mob_oas_22j_yaml_path_resolves_to_whitelisted_callable(self):
        """(i) CODEGEN↔RUNTIME — path khai trong yaml PHẢI resolve qua frappe.get_attr.

        Bịt lỗ DEAD-END D4: handler sống trong submodule `mobile/v1/device_token.py`,
        nhưng path yaml = `assetcore.api.mobile.v1.<fn>` (PACKAGE-level). Dispatcher resolve
        bằng `frappe.get_attr(<path>)` = `getattr(get_module("...mobile.v1"), "<fn>")` —
        tra ATTR trên package `v1`, KHÔNG tự vào submodule. Nếu `v1/__init__.py` KHÔNG
        re-export → AttributeError → HTTP 404 cho MỌI call client-sinh-từ-yaml, dù spec-test
        vẫn GREEN. Guard này = test SPEC-PROPERTY vẫn không đủ; phải kiểm RESOLVE THẬT +
        whitelisted + KHÔNG guest (bearer-gated D-A2). KHÔNG xoá.
        """
        import frappe

        # Mô phỏng ĐÚNG thứ-tự dispatcher (handler.py): get_attr → is_whitelisted.
        # get_attr IMPORT module (chạy @frappe.whitelist) → đăng ký registry JIT,
        # rồi is_whitelisted kiểm. Bám is_whitelisted = gate THẬT dispatcher dùng.
        frappe.local.request = frappe._dict({"method": "POST"})
        guest = {
            (getattr(f, "__module__", ""), getattr(f, "__name__", ""))
            for f in frappe.guest_methods
        }
        for path in _DEVICE_TOKEN_FROZEN:
            dotted = path[len("/api/method/"):]
            try:
                fn = frappe.get_attr(dotted)
            except Exception as exc:  # noqa: BLE001
                self.fail(
                    f"Path yaml `{dotted}` KHÔNG resolve qua frappe.get_attr "
                    f"({type(exc).__name__}: {exc}) → client codegen sẽ 404 runtime. "
                    f"Re-export hàm trong api/mobile/v1/__init__.py."
                )
            try:
                frappe.is_whitelisted(fn)
            except Exception as exc:  # noqa: BLE001
                self.fail(
                    f"`{dotted}` resolve nhưng is_whitelisted BLOCK "
                    f"({type(exc).__name__}: {exc}) → dispatcher chặn POST."
                )
            key = (getattr(fn, "__module__", ""), getattr(fn, "__name__", ""))
            self.assertNotIn(
                key, guest,
                f"`{dotted}` KHÔNG được allow_guest (bearer-gated self-service D-A2).",
            )


# G-OAS-STATUSLINE — 3 create path × CreatedEnvelope schema (nhánh success.enum=[true] route-by-VALUE).
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
      (e) 200 trỏ ĐÚNG list-response RIÊNG (C3-split): imm08→PmWorkOrderList (data.data[]),
          imm09→RepairWorkOrderList (data.data[]), imm12→IncidentList (data.items[]). 401/403 GIỮ;
          KHÔNG requestBody (list = GET).
      (f) 3 envelope schema có rows-key đúng: Pm/RepairWorkOrderListEnvelope=data.{pagination,data};
          IncidentListEnvelope=data.{pagination,items}; cả 3 dùng CHUNG Pagination sub-schema.
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
        """(f) 3 envelope rows-key đúng + dùng CHUNG Pagination; PaginatedListEnvelope đã gỡ.

        C3-split: PM/CM dùng 2 envelope RIÊNG (rows-key `data` GIỐNG nhau nhưng element-schema
        field-disjoint); Incident envelope rows-key `items`.
        """
        for ref, label in (
            (_PM_WO_LIST_SCHEMA_REF, "PmWorkOrderListEnvelope"),
            (_REPAIR_WO_LIST_SCHEMA_REF, "RepairWorkOrderListEnvelope"),
        ):
            wo = self._resolve(ref) or {}
            wo_data = ((wo.get("properties") or {}).get("data") or {})
            wo_props = wo_data.get("properties") or {}
            self.assertIn("data", wo_props, f"{label} rows-key PHẢI là `data` (imm08/09).")
            self.assertEqual(wo_props["data"].get("type"), "array", f"{label} rows = array.")
            self.assertEqual(
                (wo_props.get("pagination") or {}).get("$ref"), "#/components/schemas/Pagination",
                f"{label} dùng CHUNG Pagination.",
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
        """3 typed read 200 KHÔNG còn $ref responses/Stub — đã có inline oneOf [<ReadEnvelope>, Error]
        typed (C6 read-path P1 closure: 200 KHÔNG còn single $ref envelope mà oneOf 2 nhánh §5c)."""
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
            # C6 — 200 = oneOf [<ReadEnvelope>, Error] (KHÔNG còn single $ref envelope).
            refs = [b.get("$ref") for b in (schema200.get("oneOf") or []) if isinstance(b, dict)]
            self.assertIn(
                env_ref, refs,
                f"{path} 200 oneOf PHẢI chứa nhánh {env_ref} (C6 read-path), got {refs}",
            )
            self.assertIn(
                _ERROR_SCHEMA_REF, refs,
                f"{path} 200 oneOf PHẢI chứa nhánh Error {_ERROR_SCHEMA_REF} (in-handler 404/403 "
                f"arrive HTTP-200 — C6 read-path P1 closure), got {refs}",
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


# ── TC-MOB-OAS-24 — C6: read-path P1 closure (200 = oneOf [<ReadEnvelope>, Error]) ────────────
#   ĐÓNG read-path analog của create-path P1 (in-handler-error-on-HTTP-200): 3 GET read
#   (resolveQrToken / getAssetScanInfo / getAsset) — in-handler 404 (_err …,404) + vendor-IDOR-403
#   (assert_vendor_can_access → ServiceError(FORBIDDEN) caught → _err) ARRIVE HTTP-200 + Error body
#   (route theo body.success/body.http_status, KHÔNG status-line — verified @source api/imm00.py:
#   get_asset 297/302 · resolve_qr_token 366/371 · get_asset_scan_info 416/421/425). TRƯỚC C6, 3 read
#   200 = single $ref <ReadEnvelope> ⇒ codegen KHÔNG có nhánh deser cho Error (in-handler 404/403 =
#   dead-deser). C6 = 200 oneOf [<ReadEnvelope>, Error] CLOSED-SCHEMA Decision-B (KHÔNG discriminator).
_READ_PATH_ENVELOPE = {
    "/api/method/assetcore.api.imm00.resolve_qr_token": "#/components/schemas/QrResolveEnvelope",
    "/api/method/assetcore.api.imm00.get_asset_scan_info": "#/components/schemas/AssetScanInfoEnvelope",
    "/api/method/assetcore.api.imm00.get_asset": "#/components/schemas/AssetDetailEnvelope",
}


class TestMobileRead200OneOfClosed(unittest.TestCase):
    """TC-MOB-OAS-24 — C6: 3 GET read 200 = oneOf [<ReadEnvelope>, Error] CLOSED-SCHEMA + disjoint
    required-set, KHÔNG discriminator (Decision-B), KHÔNG dangling. Mirror create §5c cho read-path.

    LÝ DO (read-path P1 closure): in-handler 404 + vendor-IDOR-403 của 3 read arrive HTTP-200 + Error
    body (@source imm00.py) — y hệt create-path. TRƯỚC C6, 200 single $ref <ReadEnvelope> ⇒ codegen
    KHÔNG có deser-branch Error → in-handler 404/403 = dead-deser. Sau C6: oneOf 2 nhánh máy-phân-biệt
    bằng closed-schema (additionalProperties:false trên CẢ <ReadEnvelope> + Error) + disjoint
    required-set ([success,data] vs [success,error,code,http_status]) — KHÔNG cần discriminator boolean
    (success=boolean → discriminator OAS 3.x illegal). Route-by body.success/body.http_status.
    """

    @classmethod
    def setUpClass(cls):
        cls.spec = _load_spec() if _MOBILE_YAML.exists() else None

    def setUp(self):
        if self.spec is None:
            self.skipTest("Thiếu yaml mobile spec.")

    def _read_200_schema(self, path):
        op = ((self.spec.get("paths") or {}).get(path) or {}).get("get") or {}
        return _200_schema(op.get("responses") or {}), op

    def test_mob_oas_24a_each_read_200_is_oneof_envelope_error(self):
        """(1) MỖI 3 read 200 = oneOf ĐÚNG 2 nhánh [<ReadEnvelope>, Error] (KHÔNG single $ref
        envelope, KHÔNG discriminator) — read-path P1 closure mirror create §5c."""
        for path, env_ref in _READ_PATH_ENVELOPE.items():
            schema200, op = self._read_200_schema(path)
            # KHÔNG còn single $ref response-component / single $ref schema envelope.
            self.assertNotIn(
                "$ref", (op.get("responses") or {}).get("200") or {},
                f"{path} 200 KHÔNG được single $ref response-component — PHẢI inline oneOf [Env, Error].",
            )
            one_of = schema200.get("oneOf") or []
            refs = [b.get("$ref") for b in one_of if isinstance(b, dict)]
            self.assertEqual(
                len(one_of), 2,
                f"{path} 200 PHẢI oneOf ĐÚNG 2 nhánh [<ReadEnvelope>, Error]: {refs}",
            )
            self.assertIn(env_ref, refs, f"{path} 200 oneOf thiếu nhánh Env {env_ref}: {refs}")
            self.assertIn(
                _ERROR_SCHEMA_REF, refs,
                f"{path} 200 oneOf thiếu nhánh Error {_ERROR_SCHEMA_REF} (in-handler 404/403 "
                f"arrive HTTP-200): {refs}",
            )
            # Decision-B — KHÔNG discriminator (success boolean → illegal OAS 3.x).
            self.assertNotIn(
                "discriminator", schema200,
                f"{path} 200 KHÔNG được có discriminator — Decision-B closed-schema (success boolean "
                "→ discriminator OAS 3.x illegal). Route theo body.success/body.http_status.",
            )

    def test_mob_oas_24b_read_envelope_and_error_closed_disjoint(self):
        """(2) CẢ 3 <ReadEnvelope> + Error additionalProperties:false (closed) + disjoint required-set
        + success.enum đối lập — cơ chế máy-phân-biệt 2 nhánh oneOf KHÔNG discriminator (§5c)."""
        schemas = (self.spec.get("components") or {}).get("schemas") or {}
        err = schemas.get("Error") or {}
        self.assertEqual(
            err.get("additionalProperties"), False,
            "Error.additionalProperties PHẢI = false (closed → loại-trừ nhánh ReadEnvelope, §5c).",
        )
        err_req = set(err.get("required") or [])
        self.assertEqual(
            err_req, {"success", "error", "code", "http_status"},
            "Error.required PHẢI {success,error,code,http_status} (disjoint vs ReadEnvelope [success,data]).",
        )
        self.assertEqual(
            ((err.get("properties") or {}).get("success") or {}).get("enum"), [False],
            "Error.success.enum PHẢI [false].",
        )
        for env_ref in _READ_PATH_ENVELOPE.values():
            env_name = env_ref.split("/")[-1]
            env = schemas.get(env_name) or {}
            self.assertTrue(env, f"Thiếu schema {env_name} (C6).")
            self.assertEqual(
                env.get("additionalProperties"), False,
                f"{env_name}.additionalProperties PHẢI false (closed → distinct vs Error, §5c). "
                "Lưu ý: ĐÓNG ở ENVELOPE — AssetDetail (data) GIỮ open theo §3.2, KHÔNG ảnh hưởng disjoint.",
            )
            self.assertEqual(
                ((env.get("properties") or {}).get("success") or {}).get("enum"), [True],
                f"{env_name}.success.enum PHẢI [true] (nhánh thành công).",
            )
            env_req = set(env.get("required") or [])
            self.assertEqual(
                env_req, {"success", "data"},
                f"{env_name}.required PHẢI {{success,data}} (disjoint vs Error).",
            )
            self.assertEqual(
                env_req & err_req, {"success"},
                f"{env_name} vs Error required-set CHỈ giao 'success' — phần còn lại disjoint.",
            )

    def test_mob_oas_24c_read_oneof_branches_resolve_no_dangling(self):
        """(3) CẢ 2 nhánh oneOf của 3 read resolve về schema TỒN TẠI (0 dangling) — codegen
        precondition (dangling → generator crash). Khẳng-định-lại TC-09 trong ngữ-cảnh read-path."""
        for path, env_ref in _READ_PATH_ENVELOPE.items():
            schema200, _ = self._read_200_schema(path)
            for b in (schema200.get("oneOf") or []):
                ref = b.get("$ref") if isinstance(b, dict) else None
                self.assertTrue(ref, f"{path} 200 oneOf nhánh KHÔNG phải $ref: {b}")
                self.assertTrue(
                    _resolve_pointer(ref, self.spec),
                    f"{path} 200 oneOf $ref {ref} DANGLING (codegen crash).",
                )
            self.assertTrue(
                _resolve_pointer(env_ref, self.spec) and _resolve_pointer(_ERROR_SCHEMA_REF, self.spec),
                f"{path}: Env {env_ref} HOẶC Error dangling.",
            )

    def test_mob_oas_24d_read_status_set_pre_handler_only(self):
        """(4) status-set 3 read = pre-handler {200,401,403[,429]} — in-handler 404 KHÔNG status-line
        key (arrive HTTP-200+Error nhánh oneOf). 403 = dispatcher-403 (guest/thiếu DocPerm) GIỮ
        status-line; in-handler vendor-IDOR-403 đi qua nhánh Error 200. resolve/scan-info có 429."""
        expected = {
            "/api/method/assetcore.api.imm00.resolve_qr_token": ["200", "401", "403", "429"],
            "/api/method/assetcore.api.imm00.get_asset_scan_info": ["200", "401", "403", "429"],
            "/api/method/assetcore.api.imm00.get_asset": ["200", "401", "403"],
        }
        for path, status_set in expected.items():
            op = ((self.spec.get("paths") or {}).get(path) or {}).get("get") or {}
            resp = op.get("responses") or {}
            self.assertEqual(
                sorted(resp.keys()), status_set,
                f"{path}: status-set PHẢI {status_set} (in-handler 404/IDOR-403 KHÔNG status-line key).",
            )
            self.assertNotIn(
                "404", resp,
                f"{path}: '404' KHÔNG được status-line key — in-handler _err 404 arrive HTTP-200+Error "
                "(route theo body.http_status). Dead-deser nếu giữ.",
            )

    # ── TC-MOB-OAS-24e (negative / anti-false-green) — guard THẬT bắt read-path regress ─────────
    #   CHỨNG MINH guard 24a/24b KHÔNG pass-suông: inject (deepcopy IN-MEMORY, KHÔNG đụng file yaml)
    #   1 MVP read 200 VỀ single-envelope (revert C6 — bỏ oneOf + nhánh Error, còn single $ref
    #   <ReadEnvelope>). Đây CHÍNH là trạng-thái TRƯỚC C6 (read-path P1 gap: in-handler 404/IDOR-403
    #   = dead-deser). Guard PHẢI flag RED. Nếu guard vẫn XANH sau inject = guard giả (false-green).
    #   Reuse _assert_200_oneof_closed_distinct (cùng guard create-triad dùng + mirror logic 24a).
    def test_mob_oas_24e_negative_inject_single_envelope_read_goes_red(self):
        """(5 / anti-false-green) Inject 1 MVP read 200 → single-envelope (bỏ oneOf + nhánh Error)
        ⇒ guard 200-oneOf-closed PHẢI raise AssertionError. Chứng minh guard 24a bắt read-path
        regress (revert-về-trước-C6), KHÔNG pass-suông."""
        target = "/api/method/assetcore.api.imm00.resolve_qr_token"  # MVP read path
        env_ref = _READ_PATH_ENVELOPE[target]
        mutated = copy.deepcopy(self.spec)
        get_op = mutated["paths"][target]["get"]
        # Revert C6 → trạng-thái single-envelope (TRƯỚC C6): 200 = single $ref <ReadEnvelope>,
        #   KHÔNG oneOf, KHÔNG nhánh Error (in-handler 404/IDOR-403 = dead-deser).
        get_op["responses"]["200"] = {
            "description": "200 single-envelope (pre-C6 regress)",
            "content": {"application/json": {"schema": {"$ref": env_ref}}},
        }
        regressed_resp = mutated["paths"][target]["get"]["responses"]
        with self.assertRaises(
            AssertionError,
            msg="Guard 200-oneOf-closed KHÔNG bắt read 200 bị revert về single-envelope "
            "(mất nhánh Error) → guard false-green (pass-suông).",
        ):
            _assert_200_oneof_closed_distinct(self, regressed_resp, env_ref, target)

    def test_mob_oas_24e_control_clean_read_stays_green(self):
        """(5-control) Read SẠCH (deepcopy KHÔNG inject) qua CÙNG guard ⇒ KHÔNG raise. Chứng minh
        24e ĐỎ là DO inject (guard không luôn-đỏ) — kiểm tính phân biệt của guard read-path."""
        for path, env_ref in _READ_PATH_ENVELOPE.items():
            clean = copy.deepcopy(self.spec)
            resp = clean["paths"][path]["get"]["responses"]
            # KHÔNG raise = read sạch pass guard (control cho 24e).
            _assert_200_oneof_closed_distinct(self, resp, env_ref, path)


class TestMobileListItemTyped(unittest.TestCase):
    """TC-MOB-OAS-21 — list-ELEMENT schema typed (C3-split — đóng KNOWN-GAP "KHÔNG ép chung").

    C3-split: PM(imm08) ≠ CM(imm09) field-set ⇒ tách UNION WorkOrderListItem thành 2 element-schema
    FIELD-DISJOINT (Pm/RepairWorkOrderListItem) + 2 envelope + 2 response RIÊNG; rows-key `data`
    GIỮ nguyên. QUYẾT ĐỊNH BA = Option A (all-optional trừ `name` required; KHÔNG discriminator =
    Decision-B). Guard chốt:
      (a) 3 element-schema TỒN TẠI (PmWorkOrderListItem + RepairWorkOrderListItem + IncidentListItem);
          UNION WorkOrderListItem cũ KHÔNG còn (chống hồi quy union).
      (b) Pm/RepairWorkOrderListEnvelope.data.data[].items + IncidentListEnvelope.data.items[].items
          là `$ref` ITEM RIÊNG (KHÔNG generic {type:object}, KHÔNG dùng chung 1 ref); resolve.
      (c) 3 element-schema có `name` REQUIRED (PK chung) + KHÔNG required field khác (Option A).
      (d) Field-set grounded @source — KHÔNG bịa: Pm = imm08 def list_work_orders chính xác;
          Repair = imm09 def list_work_orders (parts_hold_started bị `r.pop()` → KHÔNG khai);
          Incident = imm12 (23 repo + 3 enrich + 2 derived, key `asset` KHÔNG `asset_ref`).
      (e) ĐÓNG (additionalProperties:false) + KHÔNG discriminator — Option A closed-schema.
      (f) DISJOINT-FIELD assert: field RIÊNG mỗi loại (PM-only ∩ CM-only = ∅); KHÔNG còn 1 schema
          trộn cả PM-only lẫn CM-only (đây là chứng cứ "KHÔNG ép chung").
      (g) 0 dangling $ref toàn spec.
    SSoT: ../04-api-contract.md §6.3 + ADR-MOBILE-001 (g) + EPIC-C C3-split + roadmap §3.3.
    Re-verify @source D4: services/imm08.py/imm09.py/imm12.py (def + enrich).
    """

    @classmethod
    def setUpClass(cls):
        cls.spec = _load_spec() if _MOBILE_YAML.exists() else None
        cls.raw = _MOBILE_YAML.read_text(encoding="utf-8") if _MOBILE_YAML.exists() else ""

    def _schema(self, name):
        return ((self.spec.get("components") or {}).get("schemas") or {}).get(name) or {}

    def test_mob_oas_21a_list_item_schemas_defined(self):
        """(a) 3 element-schema RIÊNG TỒN TẠI; UNION WorkOrderListItem cũ KHÔNG còn (anti-regress)."""
        schemas = (self.spec.get("components") or {}).get("schemas") or {}
        self.assertIn(
            "PmWorkOrderListItem", schemas, "Thiếu component schemas/PmWorkOrderListItem (C3-split).")
        self.assertIn(
            "RepairWorkOrderListItem", schemas,
            "Thiếu component schemas/RepairWorkOrderListItem (C3-split).")
        self.assertIn("IncidentListItem", schemas, "Thiếu component schemas/IncidentListItem.")
        # Anti-regress: UNION cũ KHÔNG được tồn tại lại (đã tách).
        self.assertNotIn(
            "WorkOrderListItem", schemas,
            "WorkOrderListItem (UNION cũ) PHẢI bị tách — KHÔNG còn 1 schema trộn PM+CM (C3-split).")
        self.assertNotIn(
            "WorkOrderListEnvelope", schemas,
            "WorkOrderListEnvelope (UNION cũ) PHẢI tách thành Pm/RepairWorkOrderListEnvelope.")

    def test_mob_oas_21b_envelope_items_are_ref_not_generic_object(self):
        """(b) 3 envelope element-`items` là $ref ITEM RIÊNG (KHÔNG generic object, KHÔNG share ref)."""
        pm = self._schema("PmWorkOrderListEnvelope")
        pm_items = (((pm.get("properties") or {}).get("data") or {}).get("properties") or {}) \
            .get("data", {}).get("items") or {}
        self.assertEqual(
            pm_items.get("$ref"), _PM_WO_LIST_ITEM_REF,
            "PmWorkOrderListEnvelope.data.data[].items PHẢI $ref PmWorkOrderListItem RIÊNG.",
        )
        self.assertNotIn("type", pm_items, "PM element KHÔNG còn generic {type:object}.")
        self.assertTrue(
            _resolve_pointer(_PM_WO_LIST_ITEM_REF, self.spec), f"{_PM_WO_LIST_ITEM_REF} dangling.")

        rp = self._schema("RepairWorkOrderListEnvelope")
        rp_items = (((rp.get("properties") or {}).get("data") or {}).get("properties") or {}) \
            .get("data", {}).get("items") or {}
        self.assertEqual(
            rp_items.get("$ref"), _REPAIR_WO_LIST_ITEM_REF,
            "RepairWorkOrderListEnvelope.data.data[].items PHẢI $ref RepairWorkOrderListItem RIÊNG.",
        )
        self.assertNotIn("type", rp_items, "Repair element KHÔNG còn generic {type:object}.")
        self.assertTrue(
            _resolve_pointer(_REPAIR_WO_LIST_ITEM_REF, self.spec),
            f"{_REPAIR_WO_LIST_ITEM_REF} dangling.")

        # Mỗi path trỏ item RIÊNG (KHÔNG chung 1 ref).
        self.assertNotEqual(
            pm_items.get("$ref"), rp_items.get("$ref"),
            "PM và Repair PHẢI $ref item-schema KHÁC NHAU (field-disjoint — KHÔNG ép chung).")

        inc = self._schema("IncidentListEnvelope")
        inc_items = (((inc.get("properties") or {}).get("data") or {}).get("properties") or {}) \
            .get("items", {}).get("items") or {}
        self.assertEqual(
            inc_items.get("$ref"), _INCIDENT_LIST_ITEM_REF,
            "IncidentListEnvelope.data.items[].items PHẢI $ref IncidentListItem (KHÔNG type:object).",
        )
        self.assertNotIn("type", inc_items, "Incident element KHÔNG còn generic {type:object}.")
        self.assertTrue(
            _resolve_pointer(_INCIDENT_LIST_ITEM_REF, self.spec), f"{_INCIDENT_LIST_ITEM_REF} dangling.")

    def test_mob_oas_21b2_list_paths_point_to_own_response(self):
        """(b2) 2 list path trỏ response RIÊNG (Pm/RepairWorkOrderList) → envelope RIÊNG (per-endpoint)."""
        paths = self.spec.get("paths") or {}
        pm_resp = ((((paths.get("/api/method/assetcore.api.imm08.list_pm_work_orders") or {})
                     .get("get") or {}).get("responses") or {}).get("200") or {}).get("$ref")
        rp_resp = ((((paths.get("/api/method/assetcore.api.imm09.list_repair_work_orders") or {})
                     .get("get") or {}).get("responses") or {}).get("200") or {}).get("$ref")
        self.assertEqual(
            pm_resp, "#/components/responses/PmWorkOrderList",
            "listPmWorkOrders 200 PHẢI trỏ PmWorkOrderList (per-endpoint).")
        self.assertEqual(
            rp_resp, "#/components/responses/RepairWorkOrderList",
            "listRepairWorkOrders 200 PHẢI trỏ RepairWorkOrderList (per-endpoint).")
        self.assertNotEqual(pm_resp, rp_resp, "2 path PHẢI trỏ response KHÁC NHAU.")

    def test_mob_oas_21c_name_required_others_optional(self):
        """(c) 3 element-schema có `name` REQUIRED + KHÔNG required field khác (Option A)."""
        for sname in ("PmWorkOrderListItem", "RepairWorkOrderListItem", "IncidentListItem"):
            sch = self._schema(sname)
            self.assertEqual(
                sch.get("type"), "object", f"{sname} type=object.")
            self.assertEqual(
                sch.get("required"), ["name"],
                f"{sname}.required PHẢI = ['name'] (PK chung; mọi field khác optional — Option A). "
                f"got={sch.get('required')}",
            )
            self.assertIn(
                "name", (sch.get("properties") or {}),
                f"{sname}.properties PHẢI có `name`.")

    def test_mob_oas_21d_fields_grounded_at_source_no_invention(self):
        """(d) Field-set MỖI element grounded @source — chữ-ký service chính xác (KHÔNG bịa)."""
        pm_props = set((self._schema("PmWorkOrderListItem").get("properties") or {}).keys())
        self.assertEqual(
            pm_props, _PM_WO_FIELDS,
            "PmWorkOrderListItem PHẢI khai ĐÚNG chữ-ký imm08.list_work_orders. Thiếu: "
            f"{sorted(_PM_WO_FIELDS - pm_props)} ; thừa: {sorted(pm_props - _PM_WO_FIELDS)}",
        )
        rp_props = set((self._schema("RepairWorkOrderListItem").get("properties") or {}).keys())
        self.assertEqual(
            rp_props, _REPAIR_WO_FIELDS,
            "RepairWorkOrderListItem PHẢI khai ĐÚNG chữ-ký imm09.list_work_orders. Thiếu: "
            f"{sorted(_REPAIR_WO_FIELDS - rp_props)} ; thừa: {sorted(rp_props - _REPAIR_WO_FIELDS)}",
        )
        # parts_hold_started bị r.pop() ở imm09.list_work_orders ⇒ KHÔNG được khai ở CM.
        self.assertNotIn(
            "parts_hold_started", rp_props,
            "parts_hold_started bị imm09 `r.pop()` → KHÔNG ra wire → KHÔNG khai (re-verify @source D4).",
        )
        # PM-only field KHÔNG được lọt vào schema CM và ngược lại (field-disjoint THẬT).
        for f in ("pm_type", "wo_type", "due_date", "supervisor", "source_pm_wo", "is_late"):
            self.assertNotIn(
                f, rp_props, f"PM-only `{f}` KHÔNG được lọt vào RepairWorkOrderListItem (field-disjoint).")
        for f in ("repair_type", "priority", "mttr_hours", "sla_breached", "department_name", "sla_paused"):
            self.assertNotIn(
                f, pm_props, f"CM-only `{f}` KHÔNG được lọt vào PmWorkOrderListItem (field-disjoint).")

        inc_props = set((self._schema("IncidentListItem").get("properties") or {}).keys())
        self.assertEqual(
            inc_props, _INCIDENT_LIST_ITEM_FIELDS,
            "IncidentListItem PHẢI khai ĐỦ 23 repo + 3 enrich + 2 derived @source imm12. Thiếu: "
            f"{sorted(_INCIDENT_LIST_ITEM_FIELDS - inc_props)} ; thừa: "
            f"{sorted(inc_props - _INCIDENT_LIST_ITEM_FIELDS)}",
        )
        # imm12 list dùng key `asset` (KHÔNG `asset_ref` như Work Order).
        self.assertIn("asset", inc_props, "IncidentListItem dùng `asset` (imm12 @source).")
        self.assertNotIn(
            "asset_ref", inc_props, "IncidentListItem KHÔNG dùng `asset_ref` (đó là Work Order).")

    def test_mob_oas_21e_closed_schema_no_discriminator(self):
        """(e) Option A closed-schema: additionalProperties:false + KHÔNG discriminator (3 schema)."""
        for sname in ("PmWorkOrderListItem", "RepairWorkOrderListItem", "IncidentListItem"):
            sch = self._schema(sname)
            self.assertEqual(
                sch.get("additionalProperties"), False,
                f"{sname} PHẢI additionalProperties:false (Option A closed-schema).",
            )
            self.assertNotIn(
                "discriminator", sch,
                f"{sname} KHÔNG discriminator (Decision-B closed-schema, KHÔNG boolean-disc).",
            )

    @staticmethod
    def _assert_pm_cm_disjoint(tc, spec):
        """Disjoint-assert dùng CHUNG cho 21g (clean) + 21h (mutated-RED). Đọc 2 element-schema
        Pm/RepairWorkOrderListItem TỪ `spec` truyền vào (KHÔNG self.spec) ⇒ test negative có thể
        bơm spec deepcopy-mutated. PM-only ∩ CM-only PHẢI = ∅ (chứng cứ "KHÔNG ép chung")."""
        schemas = (spec.get("components") or {}).get("schemas") or {}
        pm_props = set((schemas.get("PmWorkOrderListItem", {}).get("properties") or {}).keys())
        rp_props = set((schemas.get("RepairWorkOrderListItem", {}).get("properties") or {}).keys())
        pm_only = pm_props - rp_props
        cm_only = rp_props - pm_props
        tc.assertEqual(
            pm_only & cm_only, set(),
            "PM-only ∩ CM-only PHẢI = ∅ (field RIÊNG phải disjoint).")
        # CM-only field đặc trưng KHÔNG được lọt vào PM-schema (và ngược lại) — đây là bất biến bị
        # vi phạm khi ai đó "ép chung" 1 field CM vào PM (regress về UNION).
        tc.assertFalse(
            {"repair_type", "sla_paused", "mttr_hours"} & pm_props,
            "PmWorkOrderListItem KHÔNG được chứa field CM-only (KHÔNG ép chung).")
        tc.assertFalse(
            {"pm_type", "source_pm_wo", "due_date"} & rp_props,
            "RepairWorkOrderListItem KHÔNG được chứa field PM-only (KHÔNG ép chung).")
        return pm_only, cm_only

    def test_mob_oas_21g_pm_cm_field_sets_disjoint(self):
        """(f) DISJOINT-FIELD assert: PM-only ∩ CM-only = ∅; KHÔNG schema nào trộn cả 2.

        Đây là tiêu chí PASS C3-split — chứng minh "KHÔNG ép chung": field RIÊNG mỗi loại
        (PM-only / CM-only) hoàn toàn rời nhau; PmWorkOrderListItem KHÔNG chứa field CM-only,
        RepairWorkOrderListItem KHÔNG chứa field PM-only.
        """
        pm_only, cm_only = self._assert_pm_cm_disjoint(self, self.spec)
        self.assertTrue(pm_only, "PmWorkOrderListItem PHẢI có field PM-only RIÊNG (vd pm_type).")
        self.assertTrue(cm_only, "RepairWorkOrderListItem PHẢI có field CM-only RIÊNG (vd repair_type).")
        # Phản chiếu hằng module (grounded @source) — bắt drift nếu ai sửa schema lệch chữ-ký.
        self.assertEqual(
            pm_only, _PM_ONLY_FIELDS,
            f"PM-only schema lệch chữ-ký imm08. got={sorted(pm_only)} expect={sorted(_PM_ONLY_FIELDS)}")
        self.assertEqual(
            cm_only, _REPAIR_ONLY_FIELDS,
            f"CM-only schema lệch chữ-ký imm09. got={sorted(cm_only)} expect={sorted(_REPAIR_ONLY_FIELDS)}")

    # ── TC-MOB-OAS-21h (negative / anti-false-green — RED-before/GREEN-after) ──────────────────
    #   CHỨNG MINH disjoint-guard 21g KHÔNG pass-suông: inject (deepcopy IN-MEMORY, KHÔNG đụng file
    #   yaml) 1 field CM-only (`repair_type`) VÀO PmWorkOrderListItem.properties = chính xác "ép
    #   chung" PM+CM về 1 schema (regress về UNION WorkOrderListItem cũ). Guard 21g PHẢI flag RED.
    #   Nếu guard vẫn XANH sau inject = guard giả (false-green / vacuous-pass).
    def test_mob_oas_21h_negative_inject_cm_field_into_pm_goes_red(self):
        """(f / anti-false-green) Trộn 1 field CM-only vào PM-schema (deepcopy) ⇒ disjoint-assert
        PHẢI raise AssertionError. Chứng minh 21g THẬT bắt "ép chung", KHÔNG pass-suông."""
        mutated = copy.deepcopy(self.spec)
        pm_sch = mutated["components"]["schemas"]["PmWorkOrderListItem"]
        # "Ép chung": bơm field CM-only `repair_type` (+ `sla_paused`) vào PM-schema.
        pm_sch.setdefault("properties", {})["repair_type"] = {"type": "string"}
        pm_sch["properties"]["sla_paused"] = {"type": "boolean"}
        with self.assertRaises(
            AssertionError,
            msg="Disjoint-guard 21g KHÔNG bắt field CM-only bị ép vào PM-schema (regress UNION) "
            "→ guard false-green (pass-suông).",
        ):
            self._assert_pm_cm_disjoint(self, mutated)

    def test_mob_oas_21h_control_clean_disjoint_stays_green(self):
        """(f-control) Spec SẠCH (deepcopy KHÔNG inject) qua CÙNG guard ⇒ KHÔNG raise. Chứng minh
        21h ĐỎ là DO inject (guard không luôn-đỏ) — kiểm tính phân biệt của disjoint-guard."""
        clean = copy.deepcopy(self.spec)
        # KHÔNG raise = field-set sạch pass guard (control cho 21h).
        self._assert_pm_cm_disjoint(self, clean)

    def test_mob_oas_21f_no_dangling_refs_whole_spec(self):
        """(g) 0 dangling $ref toàn spec sau khi tách 2 element (regress-guard với TC-09)."""
        dangling = sorted({r for r in _collect_refs(self.spec) if not _resolve_pointer(r, self.spec)})
        self.assertEqual(dangling, [], f"$ref dangling sau C3-split (codegen crash): {dangling}")


class TestMobileUserInfo(unittest.TestCase):
    """TC-MOB-OAS-22 — C4: OIDC userinfo/whoami path (openid_profile) + OidcUserInfo schema.

    Đóng mảnh flow-1 'đăng nhập → hiển thị danh tính KTV'. GROUNDED @frappe/oauth.py:530-555
    (get_userinfo) + oauth2.py:163-174 (openid_profile passthrough RAW). KHÔNG bịa field.
    Cũng canh guard dual content-type form+json cho MỌI RPC create-path (3 create + createPm).
    """

    _OIDC_REQUIRED = ["sub", "name", "given_name", "family_name", "email", "picture", "roles", "iss"]
    _OIDC_NULLABLE = {"sub", "picture"}   # db.get_value / user_image có thể None @oauth.py:531-548
    _OIDC_SCHEMA_REF = "#/components/schemas/OidcUserInfo"

    @classmethod
    def setUpClass(cls):
        cls.spec = _load_spec() if _MOBILE_YAML.exists() else None

    def _op(self) -> dict:
        ops = {path: op for path, _, op in _iter_operations(self.spec)}
        return ops.get(_USERINFO_PATH) or {}

    def test_mob_oas_22a_userinfo_path_exists(self):
        """(a) GET openid_profile tồn tại + operationId getUserInfo (§8.1 verb-first oauth)."""
        op = self._op()
        self.assertTrue(op, f"Thiếu path GET {_USERINFO_PATH} (C4 userinfo/whoami).")
        self.assertEqual(op.get("operationId"), "getUserInfo", "operationId PHẢI = getUserInfo (§8.1).")

    def test_mob_oas_22b_userinfo_security_openid(self):
        """(b) security = [{OAuth2: [openid]}] — bearer + scope openid (oauth2.py:163 KHÔNG allow_guest)."""
        sec = self._op().get("security")
        self.assertEqual(
            sec, [{"OAuth2": ["openid"]}],
            f"userinfo PHẢI security [{{OAuth2:[openid]}}] (scope openid, oauth.py userinfo), got {sec}",
        )

    def test_mob_oas_22c_userinfo_200_refs_oidc_schema_raw(self):
        """(c) 200 = OidcUserInfo RAW passthrough (KHÔNG envelope AssetCore). status-set {200,401}."""
        resp = self._op().get("responses") or {}
        self.assertEqual(
            sorted(resp.keys()), ["200", "401"],
            "userinfo status-set PHẢI = [200,401] (RAW Frappe-core, KHÔNG 403/429).",
        )
        ref = (((resp.get("200") or {}).get("content") or {}).get("application/json") or {}).get("schema", {}).get("$ref")
        self.assertEqual(
            ref, self._OIDC_SCHEMA_REF,
            f"userinfo 200 PHẢI $ref OidcUserInfo (RAW passthrough), got {ref}",
        )

    def test_mob_oas_22d_oidc_schema_grounded_fields(self):
        """(d) OidcUserInfo field GROUNDED @oauth.py:530-555 — required đủ 8 claim, KHÔNG bịa/thừa."""
        sch = ((self.spec.get("components") or {}).get("schemas") or {}).get("OidcUserInfo") or {}
        self.assertTrue(sch, "Thiếu schema OidcUserInfo (C4).")
        self.assertEqual(
            sorted(sch.get("required") or []), sorted(self._OIDC_REQUIRED),
            f"OidcUserInfo.required PHẢI = 8 claim @oauth.py:530-555 (KHÔNG bịa/thiếu): {self._OIDC_REQUIRED}",
        )
        props = sch.get("properties") or {}
        self.assertEqual(
            sorted(props.keys()), sorted(self._OIDC_REQUIRED),
            "OidcUserInfo.properties PHẢI ĐÚNG 8 claim grounded (KHÔNG field thừa — bịa).",
        )

    def test_mob_oas_22e_oidc_roles_array_string(self):
        """(e) roles = array<string> (frappe.get_roles oauth.py:541) — app map nhãn KTV."""
        props = (((self.spec.get("components") or {}).get("schemas") or {}).get("OidcUserInfo") or {}).get("properties") or {}
        roles = props.get("roles") or {}
        self.assertEqual(roles.get("type"), "array", "roles PHẢI type array.")
        self.assertEqual((roles.get("items") or {}).get("type"), "string", "roles.items PHẢI type string.")

    def test_mob_oas_22f_oidc_nullable_claims(self):
        """(f) sub/picture nullable:true (db.get_value/user_image có thể None oauth.py:531-548)."""
        props = (((self.spec.get("components") or {}).get("schemas") or {}).get("OidcUserInfo") or {}).get("properties") or {}
        for claim in self._OIDC_NULLABLE:
            self.assertTrue(
                (props.get(claim) or {}).get("nullable") is True,
                f"OidcUserInfo.{claim} PHẢI nullable:true (@oauth.py có thể None).",
            )
        # email format chuẩn OIDC
        self.assertEqual((props.get("email") or {}).get("type"), "string", "email PHẢI type string.")

    def test_mob_oas_22g_oidc_closed_schema_no_discriminator(self):
        """(g) Decision-B: closed-schema additionalProperties:false + KHÔNG discriminator."""
        sch = ((self.spec.get("components") or {}).get("schemas") or {}).get("OidcUserInfo") or {}
        self.assertEqual(
            sch.get("additionalProperties"), False,
            "OidcUserInfo PHẢI additionalProperties:false (Decision-B closed-schema).",
        )
        self.assertNotIn("discriminator", sch, "OidcUserInfo KHÔNG discriminator (Decision-B).")

    def test_mob_oas_22h_oidc_schema_ref_resolves(self):
        """(h) OidcUserInfo $ref resolve (0 dangling) — codegen-able (TC-09 regress-guard)."""
        self.assertTrue(
            _resolve_pointer(self._OIDC_SCHEMA_REF, self.spec),
            f"$ref {self._OIDC_SCHEMA_REF} KHÔNG resolve (dangling → codegen crash).",
        )
        dangling = sorted({r for r in _collect_refs(self.spec) if not _resolve_pointer(r, self.spec)})
        self.assertEqual(dangling, [], f"$ref dangling sau C4 (codegen crash): {dangling}")

    def test_mob_oas_22i_rpc_requestbody_form_json(self):
        """(i) Guard _assert_rpc_requestbody_form_json — MỌI RPC create-path (3 create + createPm
        sau C2) khai oneOf application/json + application/x-www-form-urlencoded (Frappe form_dict)."""
        _assert_rpc_requestbody_form_json(self, self.spec)


# ── C5 — DoD codegen-dry verify (AUTO introspection proxy) ──────────────────────────────
#   ĐÓNG EPIC-C bằng guard PyYAML codegen-clean — AUTO-part của C-DoD. python3 introspection
#   (STDLIB PyYAML, KHÔNG cần java/npx) = proxy CHÍNH-THỨC cho codegen-DoD tới khi USER cấp
#   toolchain THẬT (java NOT FOUND + @openapitools/openapi-generator-cli chưa cài — probe
#   @2026-06-11). KHÔNG trùng-lặp TC-07/09/18b-c/20/21/12 mà GỌI/KHẲNG-ĐỊNH-LẠI 3 tiền-đề
#   codegen-must-hold trên ĐÚNG 10 path MVP-business (KHÔNG device-token) + thêm assert
#   MVP-cụ-thể. SSoT: ../completion/EPIC-C-api-contract.md §4 + ADR-MOBILE-001 (C5).
#
#   3 GUARD (introspection proxy — assert (a)+(b)+(c) chạy KHÔNG-toolchain):
#     (Guard-1 / a) 0 path MVP-business còn trỏ #/components/responses/Stub. EPIC-D D4 (Vòng 17):
#                   2 device-token NAY TYPED (rời Stub, wrap service D2) → 0 STUB-on-MVP toàn bộ.
#     (Guard-2 / b) 0 dangling $ref toàn spec (mọi $ref resolve về node tồn tại) — tiền-đề
#                   codegen (dangling → openapi-generator crash / model rỗng). Khẳng-định-lại
#                   TC-09 NHƯ tiền-đề codegen (KHÔNG trùng — C5 thêm ngữ-cảnh DoD).
#     (Guard-3 / c) MỖI 10 path MVP có 200 mang `data` TYPED qua $ref schema cụ thể:
#                     • read (3)  → schema 200 = $ref *Envelope (envelope.data = $ref typed).
#                     • create(4) → schema 200 = oneOf [<CreatedEnvelope> $ref, Error $ref]
#                                   (mỗi nhánh $ref — KHÔNG generic, route-by closed-schema).
#                     • list (3)  → response-component $ref → content.schema = $ref *Envelope.
#                   KHÔNG path nào dùng generic {type:object} / free-form ở 200-data.
#
#   GATE: C5 = AUTO-PART DONE → gate sang EPIC-V (codegen Dart/Kotlin THẬT = HARD-STOP USER).
_MVP_READ_ENVELOPE = {
    "/api/method/assetcore.api.imm00.resolve_qr_token": "#/components/schemas/QrResolveEnvelope",
    "/api/method/assetcore.api.imm00.get_asset_scan_info": "#/components/schemas/AssetScanInfoEnvelope",
    "/api/method/assetcore.api.imm00.get_asset": "#/components/schemas/AssetDetailEnvelope",
}
# create RPC (4) → 200 oneOf [<CreatedEnvelope>, Error] — mỗi path có CreatedEnvelope riêng.
_MVP_CREATE_ENVELOPE = {
    _CREATE_PM_PATH: "#/components/schemas/CreatePmWorkOrderCreatedEnvelope",
    _REPORT_INCIDENT_PATH: "#/components/schemas/ReportIncidentCreatedEnvelope",
    _REPAIR_CREATE_PATH: "#/components/schemas/CreateRepairWorkOrderCreatedEnvelope",
    _CAL_CREATE_PATH: "#/components/schemas/CreateCalibrationCreatedEnvelope",
}
# list (3) → 200 = response-component $ref; component.content.schema = $ref *Envelope (typed).
#   C3-split: PM/CM trỏ envelope RIÊNG (field-disjoint element-schema) — KHÔNG còn UNION chung.
_MVP_LIST_ENVELOPE = {
    _LIST_PM_PATH: "#/components/schemas/PmWorkOrderListEnvelope",
    _LIST_REPAIR_PATH: "#/components/schemas/RepairWorkOrderListEnvelope",
    _LIST_INCIDENT_PATH: "#/components/schemas/IncidentListEnvelope",
}


def _mvp_path_verb(spec: dict, path: str) -> tuple[str, dict]:
    """Trả (verb, operation) cho path MVP — POST nếu có, ngược lại GET (10 path MVP đều get/post)."""
    item = (spec.get("paths") or {}).get(path) or {}
    verb = "post" if "post" in item else "get"
    return verb, (item.get(verb) or {})


def _resolve_response_component(spec: dict, ref: str) -> dict:
    """Resolve $ref #/components/responses/<Name> → response-component dict (stdlib)."""
    if not (isinstance(ref, str) and ref.startswith("#/components/responses/")):
        return {}
    name = ref.split("/")[-1]
    return ((spec.get("components") or {}).get("responses") or {}).get(name) or {}


def _codegen_dry_introspect(spec: dict) -> dict:
    """C5 introspection proxy — STDLIB-only (KHÔNG java/npx). Trả dict 3 verdict:
        {stub_on_mvp:[...], dangling:[...], untyped_mvp:[...]}.
    Mọi list RỖNG ⇒ spec codegen-clean trên path MVP (AUTO-part C-DoD PASS).
    """
    mvp_paths = (
        set(_MVP_READ_ENVELOPE) | set(_MVP_CREATE_ENVELOPE) | set(_MVP_LIST_ENVELOPE)
    )

    # (a) Stub trên path MVP.
    stub_on_mvp: list[str] = []
    for p in sorted(mvp_paths):
        _, op = _mvp_path_verb(spec, p)
        r200 = (op.get("responses") or {}).get("200") or {}
        # Stub xuất hiện qua response-level $ref → #/components/responses/Stub.
        if r200.get("$ref") == "#/components/responses/Stub":
            stub_on_mvp.append(p)
            continue
        # ... hoặc qua schema $ref → Envelope free-form (Stub-envelope) ở read/list.
        sch = _200_schema(op.get("responses") or {})
        if sch.get("$ref") == "#/components/schemas/Envelope":
            stub_on_mvp.append(p)

    # (b) dangling $ref toàn spec.
    dangling = sorted({r for r in _collect_refs(spec) if not _resolve_pointer(r, spec)})

    # (c) 200-data typed cho TỪNG path MVP (route theo 3 shape: read/create/list).
    untyped_mvp: list[str] = []
    # C6 — read 200 nay = oneOf [<ReadEnvelope>, Error] (read-path P1 closure, KHÔNG còn single $ref
    #   envelope). TYPED ⟺ oneOf chứa CẢ <ReadEnvelope> VÀ Error (mirror create-branch). Generic
    #   {type:object} / Stub / single-branch (mất Error) ⇒ untyped (giữ anti-false-green 23d-2).
    for p, env_ref in _MVP_READ_ENVELOPE.items():
        _, op = _mvp_path_verb(spec, p)
        sch = _200_schema(op.get("responses") or {})
        refs = [b.get("$ref") for b in (sch.get("oneOf") or []) if isinstance(b, dict)]
        if env_ref not in refs or _ERROR_SCHEMA_REF not in refs:
            untyped_mvp.append(f"{p} (read: oneOf={refs}, want [{env_ref}, Error])")
    for p, created_ref in _MVP_CREATE_ENVELOPE.items():
        _, op = _mvp_path_verb(spec, p)
        sch = _200_schema(op.get("responses") or {})
        refs = [b.get("$ref") for b in (sch.get("oneOf") or []) if isinstance(b, dict)]
        if created_ref not in refs or _ERROR_SCHEMA_REF not in refs:
            untyped_mvp.append(f"{p} (create: oneOf={refs}, want [{created_ref}, Error])")
    for p, env_ref in _MVP_LIST_ENVELOPE.items():
        _, op = _mvp_path_verb(spec, p)
        r200 = (op.get("responses") or {}).get("200") or {}
        comp = _resolve_response_component(spec, r200.get("$ref"))
        comp_sch = (((comp.get("content") or {}).get("application/json") or {}).get("schema") or {})
        if comp_sch.get("$ref") != env_ref or "type" in comp_sch:
            untyped_mvp.append(
                f"{p} (list: resp.$ref={r200.get('$ref')}, comp.schema.$ref={comp_sch.get('$ref')}, want {env_ref})"
            )

    return {"stub_on_mvp": stub_on_mvp, "dangling": dangling, "untyped_mvp": untyped_mvp}


class TestMobileCodegenDryDoD(unittest.TestCase):
    """TC-MOB-OAS-23 — C5: DoD codegen-dry verify (AUTO introspection proxy).

    ĐÓNG AUTO-part C-DoD bằng introspection STDLIB PyYAML (KHÔNG java/npx). Khẳng-định 3
    tiền-đề codegen-must-hold trên ĐÚNG 10 path MVP-business; codegen Dart/Kotlin THẬT =
    HARD-STOP USER (gate EPIC-V). SSoT: completion/EPIC-C-api-contract.md §4 + ADR-MOBILE-001.
    """

    @classmethod
    def setUpClass(cls):
        cls.spec = _load_spec() if _MOBILE_YAML.exists() else None

    def setUp(self):
        if self.spec is None:
            self.skipTest("Thiếu yaml mobile spec.")

    def test_mob_oas_23a_mvp_path_set_is_ten_business(self):
        """(precond) Tập MVP-business = ĐÚNG 10 path (3 read + 4 create + 3 list) == _MVP_BUSINESS_PATHS.
        2 device-token KHÔNG nằm trong tập C5 (BE-PENDING EPIC-D → GIỮ Stub hợp lệ)."""
        c5_paths = set(_MVP_READ_ENVELOPE) | set(_MVP_CREATE_ENVELOPE) | set(_MVP_LIST_ENVELOPE)
        self.assertEqual(len(c5_paths), 10, f"C5 phải bao ĐÚNG 10 path MVP, got {len(c5_paths)}.")
        self.assertEqual(
            c5_paths, set(_MVP_BUSINESS_PATHS),
            "Tập C5 PHẢI == _MVP_BUSINESS_PATHS (3 typed read + createPm + report/repair/cal + 3 list).",
        )
        for dt in _DEVICE_TOKEN_FROZEN:
            self.assertNotIn(dt, c5_paths, f"device-token {dt} KHÔNG được nằm trong tập C5 (EPIC-D).")

    def test_mob_oas_23b_no_stub_on_mvp_business_paths(self):
        """(Guard-1) 0 path MVP-business còn trỏ responses/Stub (KHÔNG Stub-envelope free-form).
        EPIC-D D4 (Vòng 17): 2 device-token NAY TYPED (rời Stub — wrap service D2) ⇒ 0 STUB-on-MVP
        toàn bộ (10 C5-business + 2 device-token). responses/Stub HẾT referenced (forward-reserve)."""
        verdict = _codegen_dry_introspect(self.spec)
        self.assertEqual(
            verdict["stub_on_mvp"], [],
            "Path MVP-business CÒN Stub (chưa typed → codegen sinh model rỗng/free-form): "
            f"{verdict['stub_on_mvp']}",
        )
        # D4 — 2 device-token RỜI Stub (typed 200 oneOf). KHÔNG path nào trên spec còn 200→Stub.
        ops = {path: op for path, _, op in _iter_operations(self.spec)}
        for dt in _DEVICE_TOKEN_FROZEN:
            ref = ((ops.get(dt, {}).get("responses") or {}).get("200") or {}).get("$ref")
            self.assertNotEqual(
                ref, "#/components/responses/Stub",
                f"device-token {dt} PHẢI RỜI Stub (D4 typed 200 oneOf) — nếu còn = chưa typed.",
            )
            self.assertIsNone(
                ref,
                f"device-token {dt} 200 PHẢI inline oneOf [Created|Error] (KHÔNG single $ref response).",
            )

    def test_mob_oas_23c_no_dangling_ref_codegen_precondition(self):
        """(Guard-2) 0 dangling $ref toàn spec = TIỀN-ĐỀ codegen (dangling → generator crash/model
        rỗng). Khẳng-định-lại TC-09 trong ngữ-cảnh DoD codegen (KHÔNG trùng — C5 = pre-flight gate)."""
        verdict = _codegen_dry_introspect(self.spec)
        self.assertEqual(
            verdict["dangling"], [],
            f"$ref dangling (codegen crash — KHÔNG đủ điều kiện gate EPIC-V): {verdict['dangling']}",
        )

    def test_mob_oas_23d_every_mvp_path_typed_data_ref(self):
        """(Guard-3) MỖI 10 path MVP có 200-data TYPED qua $ref schema cụ thể (read=*Envelope.data
        $ref; create=oneOf[CreatedEnvelope,Error] mỗi nhánh $ref; list=response-comp→*Envelope $ref).
        KHÔNG generic {type:object} / KHÔNG free-form."""
        verdict = _codegen_dry_introspect(self.spec)
        self.assertEqual(
            verdict["untyped_mvp"], [],
            "Path MVP CÓ 200-data KHÔNG typed (generic/free-form → integrator KHÔNG bind model): "
            f"{verdict['untyped_mvp']}",
        )
        # Sâu thêm: mỗi *Envelope.data là $ref typed (KHÔNG any-type) — read + list.
        schemas = (self.spec.get("components") or {}).get("schemas") or {}
        for env_ref in set(_MVP_READ_ENVELOPE.values()) | set(_MVP_LIST_ENVELOPE.values()):
            env = schemas.get(env_ref.split("/")[-1]) or {}
            data = (env.get("properties") or {}).get("data") or {}
            self.assertTrue(
                "$ref" in data or "$ref" in (data.get("items") or {})
                or (data.get("properties") or {}),
                f"{env_ref}.data PHẢI typed ($ref / items.$ref / properties) — KHÔNG free-form.",
            )

    def test_mob_oas_23e_codegen_dry_all_green_auto_part_done(self):
        """(DoD AUTO-part) Gộp 3 guard — introspection proxy XANH ⇒ AUTO-part C-DoD DONE, gate
        EPIC-V. Codegen Dart/Kotlin THẬT = HARD-STOP USER (java NOT FOUND + generator chưa cài)."""
        verdict = _codegen_dry_introspect(self.spec)
        self.assertEqual(
            (verdict["stub_on_mvp"], verdict["dangling"], verdict["untyped_mvp"]),
            ([], [], []),
            "codegen-dry introspection KHÔNG sạch — C-DoD AUTO-part CHƯA đạt, KHÔNG gate EPIC-V: "
            f"{verdict}",
        )

    # ── TC-MOB-OAS-23d (negative / anti-false-green) — guard THẬT bắt regress ──────────────
    #   CHỨNG MINH `_codegen_dry_introspect` KHÔNG pass-suông: inject (deepcopy IN-MEMORY, KHÔNG
    #   đụng file yaml) 1 MVP path về Stub / generic / dangling → guard PHẢI flag RED. Nếu guard
    #   vẫn XANH sau inject = guard giả (false-green) → test này ĐỎ. Bảo vệ chống guard rỗng-nghĩa.
    def test_mob_oas_23d_negative_inject_stub_on_mvp_goes_red(self):
        """(23d-1) Inject 1 MVP read-path 200 → responses/Stub ⇒ Guard-1 PHẢI flag path đó."""
        mutated = copy.deepcopy(self.spec)
        target = "/api/method/assetcore.api.imm00.get_asset"  # MVP read path
        verb, _ = _mvp_path_verb(self.spec, target)
        mutated["paths"][target][verb]["responses"]["200"] = {"$ref": "#/components/responses/Stub"}
        verdict = _codegen_dry_introspect(mutated)
        self.assertIn(
            target, verdict["stub_on_mvp"],
            "Guard-1 KHÔNG bắt MVP-path bị inject về Stub → guard false-green (pass-suông).",
        )

    def test_mob_oas_23d_negative_inject_generic_object_goes_red(self):
        """(23d-2) Inject 1 MVP read-path 200-schema → generic {type:object} ⇒ Guard-3 PHẢI flag."""
        mutated = copy.deepcopy(self.spec)
        target = "/api/method/assetcore.api.imm00.resolve_qr_token"  # MVP read path
        verb, _ = _mvp_path_verb(self.spec, target)
        mutated["paths"][target][verb]["responses"]["200"] = {
            "description": "ok",
            "content": {"application/json": {"schema": {"type": "object"}}},  # generic free-form
        }
        verdict = _codegen_dry_introspect(mutated)
        self.assertTrue(
            any(target in u for u in verdict["untyped_mvp"]),
            "Guard-3 KHÔNG bắt MVP-path 200-data generic {type:object} → guard false-green.",
        )

    def test_mob_oas_23d_negative_inject_generic_create_branch_goes_red(self):
        """(23d-3) Strip Error-branch khỏi oneOf create-path ⇒ Guard-3 PHẢI flag (route-by hỏng)."""
        mutated = copy.deepcopy(self.spec)
        target = _CREATE_PM_PATH  # MVP create path (200 = oneOf [Created, Error])
        verb, _ = _mvp_path_verb(self.spec, target)
        sch = _200_schema(mutated["paths"][target][verb]["responses"])
        # Bỏ nhánh Error → còn 1 nhánh Created (generic-route, KHÔNG disambiguate business-error).
        sch["oneOf"] = [b for b in (sch.get("oneOf") or [])
                        if isinstance(b, dict) and b.get("$ref") != _ERROR_SCHEMA_REF]
        verdict = _codegen_dry_introspect(mutated)
        self.assertTrue(
            any(target in u for u in verdict["untyped_mvp"]),
            "Guard-3 KHÔNG bắt create-path mất nhánh Error trong oneOf → guard false-green.",
        )

    def test_mob_oas_23d_negative_inject_dangling_ref_goes_red(self):
        """(23d-4) Inject $ref tới component KHÔNG tồn tại ⇒ Guard-2 PHẢI flag dangling."""
        mutated = copy.deepcopy(self.spec)
        target = "/api/method/assetcore.api.imm12.list_incidents"  # MVP list path
        verb, _ = _mvp_path_verb(self.spec, target)
        mutated["paths"][target][verb]["responses"]["200"] = {
            "$ref": "#/components/responses/__DoesNotExist__"
        }
        verdict = _codegen_dry_introspect(mutated)
        self.assertIn(
            "#/components/responses/__DoesNotExist__", verdict["dangling"],
            "Guard-2 KHÔNG bắt $ref dangling (component không tồn tại) → guard false-green.",
        )

    def test_mob_oas_23d_negative_clean_spec_stays_green(self):
        """(23d-5 / control) Spec sạch (deepcopy KHÔNG inject) ⇒ 3 guard VẪN XANH. Chứng minh
        4 test 23d-1..4 ĐỎ là DO inject (không phải guard luôn-đỏ) — kiểm tính phân biệt của guard."""
        verdict = _codegen_dry_introspect(copy.deepcopy(self.spec))
        self.assertEqual(
            (verdict["stub_on_mvp"], verdict["dangling"], verdict["untyped_mvp"]),
            ([], [], []),
            f"Spec sạch KHÔNG-inject phải XANH (guard không luôn-đỏ): {verdict}",
        )


# ── F-C2 — drift-guard parity 16-path YAML ↔ runtime spec (2-spec-by-design A1) ──
#   ADR-MOBILE-001 (k): repo có 2 spec DIVERGENT — (A) runtime openapi.spec (3.1.0, 487 path,
#   Swagger UI, KHÔNG Decision-B → codegen-against-runtime dead-deser) + (B) YAML mobile
#   (3.0.3, 16 path, codegen-source, MANG Decision-B). Quyết định A1 = KHÔNG hợp nhất; ràng
#   scope-boundary + drift-guard introspection-only (chống drift CÂM giữa 2 spec).
#
#   Guard CROSS-CHECK 10 mobile-business path (loại 2 device-token STUB + 4 auth passthrough)
#   YAML vs runtime: PHẢI tồn tại trong runtime với CÙNG dotted-path-tail + CÙNG verb + CÙNG
#   security-class. Introspection IN-PROCESS `openapi.generate_spec()` (như test_oas_generator
#   gọi openapi._iter_api_modules) — KHÔNG HTTP, KHÔNG reload, KHÔNG migrate.
#
#   ⚠️ KNOWN-DIVERGENCE verb `create_calibration`: runtime suy verb=GET (@frappe.whitelist()
#   THIẾU methods=["POST"] imm11.py:89) vs YAML POST. Allowlist verb-check + backlog Phase-F
#   (fix decorator @source = đụng api/*.py + reload = HARD-STOP USER).

# Auth passthrough (oauth2.*) = Frappe-core, KHÔNG sinh trong runtime AssetCore-introspect spec
#   theo cách 1-1 dotted-tail (path frappe.* không thuộc _iter_api_modules AssetCore). Loại khỏi
#   parity-set (như _AUTH_PATHS loại khỏi 401/403 symmetry). 2 device-token = mobile.v1.* handler
#   chưa tồn tại @source (EPIC-D) ⇒ KHÔNG có runtime path. ⇒ parity-set = ĐÚNG 10 mobile-business.
_PARITY_BUSINESS_PATHS = set(_MVP_BUSINESS_PATHS)
# create_calibration: verb allowlist (runtime GET do thiếu methods=["POST"] — backlog Phase-F).
_PARITY_VERB_ALLOWLIST = {"/api/method/assetcore.api.imm11.create_calibration"}


def _security_class(op: dict) -> str:
    """Phân loại security của 1 operation: 'guest' nếu security==[] (explicit empty), ngược lại
    'authed' (non-empty HOẶC absent → inherit global non-empty). Dùng cho parity cross-spec."""
    sec = op.get("security")
    if sec == []:
        return "guest"
    return "authed"


def _path_verb_op(spec: dict, path: str) -> tuple[str | None, dict]:
    """Trả (verb, operation) cho 1 path trong spec (verb HTTP đầu tiên khớp). (None,{}) nếu path∄."""
    item = (spec.get("paths") or {}).get(path)
    if not isinstance(item, dict):
        return None, {}
    for v in _HTTP_VERBS:
        if v in item:
            return v, item[v]
    return None, {}


class TestMobileSpecParityRuntime(unittest.TestCase):
    """TC-MOB-OAS-25 — F-C2: drift-guard parity 16-path YAML ↔ runtime spec (2-spec-by-design A1).

    Chống DRIFT CÂM giữa (A) runtime openapi.spec (introspect 487-path) và (B) YAML mobile
    (16-path codegen-source). 10 mobile-business path PHẢI tồn tại trong runtime với CÙNG
    dotted-tail + verb (allowlist create_calibration) + security-class. Introspection
    IN-PROCESS `openapi.generate_spec()` — KHÔNG HTTP/reload/migrate (như test_oas_generator).
    SSoT: ADR-MOBILE-001 (k) + completion/EPIC-C-api-contract.md §F-C2 + 04 §9b.
    """

    @classmethod
    def setUpClass(cls):
        cls.spec = _load_spec() if _MOBILE_YAML.exists() else None
        cls.runtime = None
        if cls.spec is not None:
            # Lazy import — generator chạm Frappe meta (cần frappe init của bench run-tests).
            from assetcore.api import openapi as _openapi  # noqa: PLC0415

            cls.runtime = _openapi.generate_spec()

    def setUp(self):
        if self.spec is None or self.runtime is None:
            self.skipTest("Thiếu yaml mobile spec hoặc không sinh được runtime spec.")

    def test_mob_oas_25a_runtime_and_yaml_versions_and_scale(self):
        """(precond) Runtime = OAS 3.1.0 + nhiều path (full surface, ≥400); YAML = 3.0.3 + 16 path.
        Khẳng-định 2 spec phân-vai THẬT tồn tại (KHÔNG hợp nhất) — tiền-đề F-C2."""
        self.assertEqual(self.runtime.get("openapi"), "3.1.0", "Runtime spec PHẢI là OAS 3.1.0.")
        self.assertGreaterEqual(
            len(self.runtime.get("paths") or {}), 400,
            "Runtime spec PHẢI là full-surface (≥400 path) — SSoT human-browse/integrator.",
        )
        self.assertEqual(self.spec.get("openapi"), "3.0.3", "YAML mobile PHẢI là OAS 3.0.3 (codegen).")
        self.assertEqual(
            len(self.spec.get("paths") or {}), 16,
            "YAML mobile PHẢI GIỮ 16 path (4 auth + 10 business + 2 device-token STUB).",
        )

    def test_mob_oas_25b_business_paths_exist_in_runtime_same_tail(self):
        """(Guard) MỌI mobile-business path (10) PHẢI TỒN TẠI trong runtime spec với CÙNG
        dotted-path-tail (= chính path /api/method/<dotted>). Path YAML KHÔNG có trong runtime
        → RED (drift câm: thêm/đổi path bên YAML mà runtime không serve)."""
        runtime_paths = set((self.runtime.get("paths") or {}).keys())
        missing = sorted(p for p in _PARITY_BUSINESS_PATHS if p not in runtime_paths)
        self.assertEqual(
            missing, [],
            "mobile-business path KHÔNG tồn tại trong runtime spec (drift câm — codegen mobile "
            f"khai path runtime không serve): {missing}",
        )
        # Đối-chứng: 2 device-token + 4 auth passthrough KHÔNG nằm trong parity-set (loại đúng).
        self.assertEqual(len(_PARITY_BUSINESS_PATHS), 10, "parity-set PHẢI = ĐÚNG 10 mobile-business.")
        for dt in _DEVICE_TOKEN_FROZEN:
            self.assertNotIn(dt, _PARITY_BUSINESS_PATHS, f"device-token {dt} loại khỏi parity (EPIC-D).")
        for ap in _AUTH_PATHS:
            self.assertNotIn(ap, _PARITY_BUSINESS_PATHS, f"auth passthrough {ap} loại khỏi parity (Frappe-core).")

    def test_mob_oas_25c_verb_parity_with_calibration_allowlist(self):
        """(Guard) verb YAML == verb runtime cho mỗi mobile-business path, TRỪ create_calibration
        (allowlist — runtime GET do thiếu methods=["POST"] imm11.py:89, backlog Phase-F). Verb
        lệch ngoài allowlist → RED (chống drift verb câm)."""
        mismatches = []
        for p in sorted(_PARITY_BUSINESS_PATHS):
            yv, _ = _path_verb_op(self.spec, p)
            rv, _ = _path_verb_op(self.runtime, p)
            if rv is None:
                continue  # 25b đã bắt missing — KHÔNG double-fail ở đây.
            if yv != rv and p not in _PARITY_VERB_ALLOWLIST:
                mismatches.append(f"{p}: yaml={yv} runtime={rv}")
        self.assertEqual(
            mismatches, [],
            "verb YAML ≠ verb runtime (ngoài allowlist create_calibration) — drift verb câm: "
            f"{mismatches}",
        )
        # KNOWN-DIVERGENCE: create_calibration THẬT lệch (yaml POST vs runtime GET) — khẳng-định
        #   allowlist KHÔNG rỗng-nghĩa (nếu source được fix methods=["POST"] thì 2 verb khớp → có
        #   thể gỡ allowlist; tới lúc đó assert này nhắc backlog Phase-F còn mở).
        cal = "/api/method/assetcore.api.imm11.create_calibration"
        yv, _ = _path_verb_op(self.spec, cal)
        rv, _ = _path_verb_op(self.runtime, cal)
        self.assertEqual(yv, "post", "YAML create_calibration PHẢI khai POST (mutating-create).")
        self.assertEqual(
            rv, "get",
            "Runtime create_calibration KỲ VỌNG GET (thiếu methods=[POST] imm11.py:89). Nếu nay = "
            "POST ⇒ source ĐÃ fix → gỡ _PARITY_VERB_ALLOWLIST + đóng backlog Phase-F (cập nhật ADR k).",
        )

    def test_mob_oas_25d_security_class_parity(self):
        """(Guard) security-class YAML == runtime cho mỗi mobile-business path: authed (bearer/cap)
        vs guest (security==[]). 10 mobile-business đều authed 2 bên. Lệch class → RED (drift quyền
        câm: 1 spec khai guest, spec kia khai authed → codegen sinh client gọi sai chế-độ-auth)."""
        mismatches = []
        for p in sorted(_PARITY_BUSINESS_PATHS):
            _, yop = _path_verb_op(self.spec, p)
            _, rop = _path_verb_op(self.runtime, p)
            if not rop:
                continue
            yc, rc = _security_class(yop), _security_class(rop)
            if yc != rc:
                mismatches.append(f"{p}: yaml={yc} runtime={rc}")
        self.assertEqual(
            mismatches, [],
            f"security-class YAML ≠ runtime — drift quyền câm: {mismatches}",
        )
        # Khẳng-định 10 business đều 'authed' ở YAML (inherit global OAuth2:[all], KHÔNG security:[]).
        for p in _PARITY_BUSINESS_PATHS:
            _, yop = _path_verb_op(self.spec, p)
            self.assertEqual(
                _security_class(yop), "authed",
                f"{p} (YAML) PHẢI authed (mobile-business KHÔNG guest) — nếu thành guest = leo-quyền câm.",
            )

    # ── TC-MOB-OAS-25e (negative / anti-false-green) — guard THẬT bắt drift ──────────────────
    #   CHỨNG MINH parity-guard KHÔNG pass-suông: inject (deepcopy IN-MEMORY runtime, KHÔNG đụng
    #   server/spec file) — (1) xoá 1 business path khỏi runtime → 25b RED; (2) flip security-class
    #   1 path → 25d RED. Control sạch (KHÔNG inject) → cả 2 guard XANH. Nếu guard vẫn xanh sau
    #   inject = guard giả → test này ĐỎ.
    def test_mob_oas_25e_negative_drop_runtime_path_and_flip_security_go_red(self):
        target = "/api/method/assetcore.api.imm12.report_incident"

        # (1) xoá path khỏi runtime → existence-guard PHẢI flag missing.
        mutated = copy.deepcopy(self.runtime)
        mutated["paths"].pop(target, None)
        runtime_paths = set((mutated.get("paths") or {}).keys())
        missing = [p for p in _PARITY_BUSINESS_PATHS if p not in runtime_paths]
        self.assertIn(
            target, missing,
            "Existence-guard KHÔNG bắt business-path bị xoá khỏi runtime → guard false-green.",
        )

        # (2) flip security-class (authed→guest) ở runtime → security-guard PHẢI flag mismatch.
        mutated2 = copy.deepcopy(self.runtime)
        rverb, _ = _path_verb_op(mutated2, target)
        mutated2["paths"][target][rverb]["security"] = []  # ép guest
        _, yop = _path_verb_op(self.spec, target)
        _, rop2 = _path_verb_op(mutated2, target)
        self.assertNotEqual(
            _security_class(yop), _security_class(rop2),
            "Security-guard KHÔNG phân-biệt authed vs guest sau khi flip runtime→guest → false-green.",
        )

        # (control) runtime sạch (deepcopy KHÔNG inject) → 2 guard XANH (guard KHÔNG luôn-đỏ).
        clean = copy.deepcopy(self.runtime)
        clean_paths = set((clean.get("paths") or {}).keys())
        self.assertEqual(
            [p for p in _PARITY_BUSINESS_PATHS if p not in clean_paths], [],
            "Runtime sạch KHÔNG-inject phải đủ 10 business path (guard không luôn-đỏ).",
        )
        for p in _PARITY_BUSINESS_PATHS:
            _, yop = _path_verb_op(self.spec, p)
            _, rop = _path_verb_op(clean, p)
            self.assertEqual(
                _security_class(yop), _security_class(rop),
                f"Runtime sạch: security-class {p} phải khớp YAML (control GREEN).",
            )

    # ── TC-MOB-OAS-25f (drift-guard hardening) — chống ALLOWLIST-CREEP cho verb-allowlist ─────
    #   VÌ SAO: 25c bỏ qua verb-mismatch cho MỌI path nằm trong `_PARITY_VERB_ALLOWLIST`. Nếu ai
    #   đó âm thầm THÊM path lạ vào allowlist → 25c sẽ MASK real verb-drift của path đó (drift câm
    #   cấp-2: guard tự bị vô-hiệu hoá qua allowlist). Guard này KHOÁ allowlist về đúng cardinality
    #   1 + exact-set {create_calibration} → mọi path-thêm-vào allowlist ⇒ suite RED, buộc review.
    #
    #   BACKLOG Phase-F item #3 (SSoT — đóng khi source fix): create_calibration @ api/imm11.py:90
    #   hiện THIẾU methods=["POST"] ⇒ runtime suy verb=GET ≠ YAML POST ⇒ allowlist phải CHỨA path
    #   này (1 phần-tử). Khi USER fix decorator (HARD-STOP: đụng api/*.py + reload gunicorn
    #   --preload + re-verify 25c) → 2 verb khớp → allowlist NÊN RỖNG. Lúc đó:
    #     • assert exact-set dưới đây sẽ RED → BÁO HIỆU phải GỠ _PARITY_VERB_ALLOWLIST (về set())
    #       và sửa cardinality-guard này thành `== 0`, đồng thời ĐÓNG ADR-MOBILE-001 (k) backlog
    #       Phase-F item #3.
    #   ⇒ cardinality-guard vừa chống creep (thêm), vừa NHẮC dọn (khi divergence thật biến mất).
    def test_mob_oas_25f_verb_allowlist_cardinality_locked(self):
        """(Guard drift-hardening) `_PARITY_VERB_ALLOWLIST` PHẢI khoá cứng = ĐÚNG 1 phần-tử và
        BẰNG exact-set {create_calibration} — chống allowlist-creep câm (thêm path lạ vào allowlist
        để 25c bỏ qua verb-drift thật của nó). Anti-false-green: mutate BẢN SAO in-memory thêm 1
        path giả → cardinality + exact-set check RED; allowlist gốc → GREEN (control).

        BACKLOG Phase-F item #3 (ADR-MOBILE-001 k): khi USER fix create_calibration thêm
        methods=["POST"] @api/imm11.py:90 (HARD-STOP — reload gunicorn --preload + re-verify 25c)
        → runtime verb=POST khớp YAML → allowlist NÊN rỗng. Lúc đó exact-set assert này RED → NHẮC
        gỡ _PARITY_VERB_ALLOWLIST (về set()) + chuyển cardinality-guard về `== 0` + đóng backlog.
        """
        _CAL = "/api/method/assetcore.api.imm11.create_calibration"

        # (positive / lock) cardinality == 1 + exact-set == {create_calibration}.
        self.assertEqual(
            len(_PARITY_VERB_ALLOWLIST), 1,
            "Verb-allowlist PHẢI = ĐÚNG 1 phần-tử (chỉ create_calibration — backlog Phase-F item "
            f"#3). cardinality≠1 = allowlist-creep HOẶC source đã fix (xem docstring): {sorted(_PARITY_VERB_ALLOWLIST)}",
        )
        self.assertEqual(
            _PARITY_VERB_ALLOWLIST, {_CAL},
            "Verb-allowlist PHẢI = exact-set {create_calibration}. Path khác xuất hiện = allowlist-"
            "creep câm (mask verb-drift thật của path đó trong 25c) — review + gỡ: "
            f"{sorted(_PARITY_VERB_ALLOWLIST)}",
        )

        # (anti-false-green / RED-before) CHỨNG MINH guard THẬT bắt creep: deepcopy allowlist (KHÔNG
        #   đụng hằng module) + thêm 1 path giả → cả cardinality lẫn exact-set check PHẢI RED.
        crept = copy.deepcopy(_PARITY_VERB_ALLOWLIST)
        crept.add("/api/method/assetcore.api.imm99.fake_creep")
        self.assertNotEqual(
            len(crept), 1,
            "Cardinality-guard false-green: thêm path giả mà len vẫn ==1 → guard không bắt creep.",
        )
        self.assertNotEqual(
            crept, {_CAL},
            "Exact-set guard false-green: thêm path giả mà set vẫn == {create_calibration} → "
            "guard không bắt creep.",
        )

        # (control / GREEN-after) allowlist GỐC (sau khi đã chứng minh negative) vẫn đúng exact-set.
        self.assertEqual(
            _PARITY_VERB_ALLOWLIST, {_CAL},
            "Control: allowlist GỐC (không mutate) PHẢI giữ exact-set {create_calibration} — guard "
            "không luôn-đỏ.",
        )


# ── TC-MOB-OAS-26 (C1-residual — prose-residue discriminator guard) ──────────────────────────
#   EPIC-C §C1 closure (Decision-B): yaml = 0 `discriminator:` key NHƯNG prose (description-text +
#   comment) TỪNG còn sót mô tả "ROUTE THEO body.success discriminator" / "+ discriminator success"
#   như CƠ CHẾ HIỆN HỮU — mâu thuẫn Decision-B (route-by-VALUE closed-schema, KHÔNG discriminator-
#   object). Guard này đọc RAW yaml text (KHÔNG qua safe_load — bắt CẢ comment lẫn description) và
#   FAIL nếu prose bịa discriminator như mechanism đang dùng. Mọi nhắc discriminator hợp-lệ CÒN LẠI
#   PHẢI ở dạng NEGATED ("KHÔNG discriminator" / "BỎ discriminator…illegal" / "thay cho discriminator")
#   hoặc đánh dấu [SUPERSEDED] — KHÔNG mô tả nó là đường route hiện hành.
#   SSoT: ../../../docs/mobile/04-api-contract.md §5c + ADR-MOBILE-001 (f) + completion/EPIC-C §C1.

# Pattern prose-residue = discriminator mô tả NHƯ cơ chế hiện hữu (forbidden). re.I.
_PROSE_RESIDUE_PATTERNS = (
    r"ROUTE THEO body\.success discriminator",          # summary-line cũ 3 create path
    r"\+\s*discriminator success",                       # "… | Error] + discriminator success"
    r"route theo body\.success \(discriminator\)",       # comment cũ "Client route theo body.success (discriminator)"
    r"=\s*oneOf \[Created, Error\]\s*\+\s*discriminator", # comment cũ "200 = oneOf [Created, Error] + discriminator"
    r"discriminator\s*\{propertyName:\s*success",        # literal discriminator-object draft (route-by-body-discriminator)
)


class TestMobileProseResidueDiscriminator(unittest.TestCase):
    """C1-residual — chống tái phát prose mô tả discriminator như cơ chế route hiện hữu (Decision-B)."""

    @classmethod
    def setUpClass(cls):
        cls.exists = _MOBILE_YAML.exists()
        cls.raw = _MOBILE_YAML.read_text(encoding="utf-8") if cls.exists else ""

    def test_mob_oas_26a_no_discriminator_route_prose_residue(self):
        """RAW yaml text KHÔNG còn prose mô tả 'route theo body.success discriminator' / '+ discriminator
        success' / discriminator-object như mechanism hiện hữu (Decision-B = route-by-VALUE closed-schema).
        """
        self.assertTrue(self.exists, f"Thiếu file: {_MOBILE_YAML}")
        hits = []
        for ln, line in enumerate(self.raw.splitlines(), start=1):
            for pat in _PROSE_RESIDUE_PATTERNS:
                if re.search(pat, line, flags=re.IGNORECASE):
                    # [SUPERSEDED] line = ghi-chép lịch sử ĐƯỢC PHÉP (đã đánh dấu rõ là bản nháp bỏ).
                    if "[SUPERSEDED" in line.upper():
                        continue
                    hits.append(f"L{ln}: {line.strip()}  (match /{pat}/)")
        self.assertEqual(
            hits, [],
            "PROSE-RESIDUE discriminator còn sót trong yaml — mâu thuẫn Decision-B (route-by-VALUE "
            "closed-schema, KHÔNG discriminator-object). Sửa prose thành 'route theo GIÁ TRỊ body.success "
            "(Created.success.enum=[true] vs Error.success.enum=[false]) qua closed-schema disjoint "
            f"required-set'. Hits:\n  " + "\n  ".join(hits),
        )

    def test_mob_oas_26b_real_discriminator_keys_stay_zero(self):
        """Decision-B BẤT BIẾN — 0 `discriminator:` KEY trong toàn yaml (C1-residual KHÔNG thêm key,
        chỉ sửa prose). Đếm theo regex key-line `^\\s*discriminator:` trên RAW text."""
        self.assertTrue(self.exists, f"Thiếu file: {_MOBILE_YAML}")
        key_lines = [
            f"L{ln}: {line.strip()}"
            for ln, line in enumerate(self.raw.splitlines(), start=1)
            if re.match(r"\s*discriminator:", line)
        ]
        self.assertEqual(
            key_lines, [],
            "Decision-B vỡ: xuất hiện `discriminator:` KEY trong yaml (phải = 0 — closed-schema "
            f"route-by-VALUE, KHÔNG discriminator-object): {key_lines}",
        )

    def test_mob_oas_26c_detector_red_before_on_injected_residue(self):
        """Anti-false-green — CHỨNG MINH detector 26a KHÔNG pass-suông: inject 1 dòng residue tổng-hợp
        vào BẢN SAO text (KHÔNG ghi file) → detector PHẢI flag; control sạch → 0 flag."""
        self.assertTrue(self.exists, f"Thiếu file: {_MOBILE_YAML}")

        def _scan(text: str) -> list[str]:
            out = []
            for ln, line in enumerate(text.splitlines(), start=1):
                for pat in _PROSE_RESIDUE_PATTERNS:
                    if re.search(pat, line, flags=re.IGNORECASE) and "[SUPERSEDED" not in line.upper():
                        out.append(f"L{ln}:{pat}")
            return out

        # control: text THẬT hiện hành = sạch (0 residue — đồng nhất 26a GREEN).
        self.assertEqual(_scan(self.raw), [], "Control text THẬT phải SẠCH residue (đồng bộ 26a).")

        # inject: thêm 1 dòng prose bịa discriminator-as-mechanism → detector PHẢI bắt (RED-before).
        injected = self.raw + "\n        # client ROUTE THEO body.success discriminator + body.http_status\n"
        self.assertTrue(
            _scan(injected),
            "Detector residue KHÔNG bắt dòng inject 'ROUTE THEO body.success discriminator' → guard giả "
            "(false-green). Detector PHẢI RED-trước-fix khi prose bịa discriminator.",
        )


# ── TC-MOB-OAS-18f (C1-residual — STRUCTURAL prose guard cho 200-oneOf operation objects) ─────────
#   BỔ-TRỢ cho 26a (raw-text grep). 18f đi qua SPEC ĐÃ PARSE (safe_load) — walk MỌI prose-field
#   (summary / operation.description / responses.200.description) của 4 create + 3 read path có
#   200-oneOf, FAIL nếu BẤT KỲ clause nào nhắc 'discriminator' NHƯ CƠ CHẾ ROUTE HIỆN HỮU.
#   Hợp-lệ CHỈ khi clause đó NEGATED ("KHÔNG/không discriminator", "no discriminator", "BỎ
#   discriminator", "thay cho/thay thế discriminator", "illegal") HOẶC đánh dấu [SUPERSEDED].
#   Decision-B = route-by-VALUE closed-schema (Created.success.enum=[true] vs Error.success.enum=
#   [false] qua additionalProperties:false + disjoint required-set), KHÔNG discriminator-object.
#   SSoT: ../../../docs/mobile/04-api-contract.md §5c + ADR-MOBILE-001 (f) + completion/EPIC-C §C1.

# 7 path có 200-oneOf route-by-VALUE (4 create POST + 3 read GET) — Decision-B closed-schema.
_OAS18F_CREATE_PATHS = (
    (_CREATE_PM_PATH, "post"),
    (_REPORT_INCIDENT_PATH, "post"),
    (_REPAIR_CREATE_PATH, "post"),
    (_CAL_CREATE_PATH, "post"),
)
_OAS18F_READ_PATHS = tuple((p, "get") for p in _READ_PATH_ENVELOPE)

# Token negation cho phép 'discriminator' xuất hiện trong CÙNG clause (KHÔNG mô tả mechanism).
#   Scope CLAUSE-local: 1 câu có thể vừa "route theo body.success" vừa "KHÔNG discriminator".
_DISC_NEG_TOKENS = (
    "không discriminator",
    "khong discriminator",          # ASCII fallback
    "no discriminator",
    "bỏ discriminator",
    "bo discriminator",
    "thay cho discriminator",
    "thay thế discriminator",
    "thay the discriminator",
    "discriminator illegal",
    "discriminator boolean illegal",
    "discriminator oas 3.x illegal",
)
# Marker lịch-sử — scope TOÀN-TEXT (cả bullet/comment ghi-chép bản nháp bỏ); MIỄN toàn field.
_DISC_HISTORICAL_MARKERS = ("[superseded", "superseded —", "superseded -")


def _disc_mechanism_clauses(text: str) -> list[str]:
    """Tách `text` thành clause (theo dấu câu/xuống dòng) → trả các clause nhắc 'discriminator'
    NHƯ cơ chế route HIỆN HỮU. MIỄN clause NEGATED (clause-local) HOẶC text đánh dấu lịch-sử
    [SUPERSEDED] (text-scope toàn field). Stdlib-only, no lib ngoài."""
    if not text:
        return []
    low_all = text.lower()
    # Ghi-chép lịch-sử (bản nháp bỏ) — MIỄN toàn field (marker scope cả câu/bullet).
    if any(m in low_all for m in _DISC_HISTORICAL_MARKERS):
        return []
    # Tách theo các ranh giới clause: newline, dấu chấm/phẩy/chấm-phẩy, ngoặc, gạch-ngang em.
    clauses = re.split(r"[\n.;,()—–]| - ", text)
    out: list[str] = []
    for c in clauses:
        low = c.lower()
        if "discriminator" not in low:
            continue
        if any(tok in low for tok in _DISC_NEG_TOKENS):
            continue  # negated (clause-local) — hợp lệ
        out.append(c.strip())
    return out


class TestMobileOas18fNoDiscriminatorRouteProse(unittest.TestCase):
    """TC-MOB-OAS-18f — STRUCTURAL guard (parsed-spec) chống prose mô tả discriminator NHƯ cơ chế
    route HIỆN HỮU trên 4 create + 3 read 200-oneOf path. BỔ-TRỢ 26a (raw-text). Decision-B intact."""

    @classmethod
    def setUpClass(cls):
        cls.spec = _load_spec() if _MOBILE_YAML.exists() else None

    def setUp(self):
        if self.spec is None:
            self.skipTest("Thiếu yaml mobile spec.")

    def _op(self, path, verb):
        return ((self.spec.get("paths") or {}).get(path) or {}).get(verb) or {}

    def _prose_fields(self, op):
        """Yield (label, text) cho summary / description / responses.200.description."""
        if op.get("summary"):
            yield "summary", op["summary"]
        if op.get("description"):
            yield "operation.description", op["description"]
        r200 = ((op.get("responses") or {}).get("200") or {})
        if r200.get("description"):
            yield "responses.200.description", r200["description"]

    def test_mob_oas_18f_create_paths_no_discriminator_route_prose(self):
        """4 create path (200-oneOf): KHÔNG prose-field nào mô tả 'discriminator' như đường route
        hiện hữu (cho phép clause NEGATED / [SUPERSEDED]). Decision-B = route-by-VALUE closed-schema."""
        bad: list[str] = []
        for path, verb in _OAS18F_CREATE_PATHS:
            op = self._op(path, verb)
            self.assertTrue(op, f"Thiếu operation {verb.upper()} {path} (4 create path).")
            for label, text in self._prose_fields(op):
                for clause in _disc_mechanism_clauses(text):
                    bad.append(f"{path} [{label}]: …{clause}…")
        self.assertEqual(
            bad, [],
            "PROSE mô tả 'discriminator' NHƯ cơ chế route hiện hữu trên CREATE path — mâu thuẫn "
            "Decision-B (route-by-VALUE: Created.success.enum=[true] vs Error.success.enum=[false] "
            "qua closed-schema additionalProperties:false + disjoint required-set, KHÔNG discriminator-"
            "object). Sửa prose hoặc đánh dấu NEGATED/[SUPERSEDED]:\n  " + "\n  ".join(bad),
        )

    def test_mob_oas_18f_read_paths_no_discriminator_route_prose(self):
        """3 read path (200-oneOf, C6 mirror create §5c): KHÔNG prose mô tả discriminator hiện hữu."""
        bad: list[str] = []
        for path, verb in _OAS18F_READ_PATHS:
            op = self._op(path, verb)
            self.assertTrue(op, f"Thiếu operation {verb.upper()} {path} (3 read path).")
            for label, text in self._prose_fields(op):
                for clause in _disc_mechanism_clauses(text):
                    bad.append(f"{path} [{label}]: …{clause}…")
        self.assertEqual(
            bad, [],
            "PROSE mô tả 'discriminator' NHƯ cơ chế route hiện hữu trên READ path — mâu thuẫn "
            "Decision-B closed-schema route-by-VALUE. Sửa prose hoặc đánh dấu NEGATED/[SUPERSEDED]:\n  "
            + "\n  ".join(bad),
        )

    def test_mob_oas_18f_detector_red_before_on_injected_mechanism_prose(self):
        """Anti-false-green — CHỨNG MINH detector clause-level KHÔNG pass-suông: prose bịa
        discriminator-as-mechanism PHẢI bị bắt; control (prose Decision-B negated) PHẢI sạch."""
        # control: clause Decision-B negated thực tế = sạch (đồng nhất 18f GREEN).
        self.assertEqual(
            _disc_mechanism_clauses(
                "200 = oneOf [Created, Error] CLOSED-SCHEMA disjoint required-set "
                "(Decision-B §5c, KHÔNG discriminator). Route theo body.success."
            ),
            [],
            "Control prose negated ('KHÔNG discriminator') phải SẠCH (đồng bộ 18f GREEN).",
        )
        # [SUPERSEDED] historical mention — cũng hợp lệ.
        self.assertEqual(
            _disc_mechanism_clauses(
                "[SUPERSEDED — Decision-B] bản nháp R1 đặt discriminator {propertyName: success}; BỎ."
            ),
            [],
            "Mention [SUPERSEDED] phải được MIỄN (ghi-chép lịch-sử, KHÔNG mechanism hiện hữu).",
        )
        # inject: prose bịa discriminator như đường route hiện hữu → detector PHẢI bắt (RED-before).
        injected = (
            "200 = oneOf [Created | Error]: client ROUTE THEO body.success discriminator "
            "+ body.http_status để chọn nhánh."
        )
        flagged = _disc_mechanism_clauses(injected)
        self.assertTrue(
            flagged,
            "Detector 18f KHÔNG bắt prose bịa 'ROUTE THEO body.success discriminator' (mechanism "
            "hiện hữu) → guard giả (false-green). Detector PHẢI RED-trước-fix.",
        )


# ── C-DoD-CFG (Vòng 12) — codegen-config-validity guard (STDLIB-only, KHÔNG toolchain) ──────
#   GAP đóng: openapitools.json NAY là RUNNABLE-config (3 generators mobile-dart/mobile-kotlin/
#   mobile-typescript, generator-cli.version 7.23.0, mỗi cái inputSpec trỏ mobile YAML +
#   generatorName + output) NHƯNG TRƯỚC Vòng 12 KHÔNG guard nào kiểm — config có thể drift rời
#   khỏi YAML (đổi/xoá YAML, sai path) mà suite VẪN xanh ⇒ handoff codegen FAIL-CÂM ở máy USER.
#
#   Guard validate config bằng STDLIB `json.load` (KHÔNG cần java/npx/@openapitools generator) —
#   = AUTO-part config-validity, bổ-trợ §EPIC-V V1 [AUTO] (python3 1-liner thủ công → NAY guard
#   máy-kiểm). SSoT path = `_MOBILE_YAML` (single-SSoT, AC-3) — đổi YAML 1 chỗ thì guard theo,
#   KHÔNG hardcode lại path-string. RED-before/GREEN-after qua inject IN-MEMORY (json deepcopy,
#   KHÔNG sửa file thật — file read-only assert). SSoT doc: ../../../docs/mobile/completion/
#   EPIC-V-codegen-verification.md §3.2 + §4 V1 + ACCEPTANCE-CHECKLIST §1 C-A13.
def _load_openapitools() -> dict:
    """STDLIB json.load openapitools.json — KHÔNG java/npx/toolchain. Trả dict config."""
    return json.loads(_OPENAPITOOLS_JSON.read_text(encoding="utf-8"))


def _config_generators(cfg: dict) -> dict:
    """Trả khối generators (nested dưới `generator-cli.generators` theo schema
    @openapitools/openapi-generator-cli). KHÔNG top-level `generators`."""
    return ((cfg.get("generator-cli") or {}).get("generators") or {})


def _config_validity_errors(cfg: dict) -> list[str]:
    """Validate runnable-config codegen — trả list LỖI (rỗng ⇒ config hợp lệ codegen-ready).

    SSoT-path = `_MOBILE_YAML`: mọi `inputSpec` resolve (repo-relative) PHẢI == `_MOBILE_YAML`
    VÀ file TỒN TẠI. Drift (sai path / xoá YAML / version rỗng / generators rỗng) ⇒ LỖI ⇒ RED.
    STDLIB-only (Path/json) — KHÔNG cần toolchain.
    """
    errs: list[str] = []
    # (i) generator-cli.version pin (NOT empty, NOT skeleton/placeholder).
    version = ((cfg.get("generator-cli") or {}).get("version"))
    if not version:
        errs.append(f"generator-cli.version RỖNG/thiếu (cần '{_OPENAPITOOLS_VERSION}')")
    elif version != _OPENAPITOOLS_VERSION:
        errs.append(f"generator-cli.version={version!r} ≠ pin {_OPENAPITOOLS_VERSION!r}")
    # (ii) generators KHÔNG rỗng + có ≥1 generatorName.
    generators = _config_generators(cfg)
    if not generators:
        errs.append("generators RỖNG — config KHÔNG runnable (thiếu khối generator-cli.generators)")
        return errs  # KHÔNG iterate tiếp khi rỗng (các check (iii)/(iv) vô-nghĩa)
    if not any((g or {}).get("generatorName") for g in generators.values()):
        errs.append("KHÔNG generator nào có generatorName — config KHÔNG runnable")
    # (iii)+(iv) mỗi generator: inputSpec trỏ ĐÚNG _MOBILE_YAML (+ file tồn tại) + name + output.
    for gid, g in generators.items():
        g = g or {}
        name = g.get("generatorName")
        if not name:
            errs.append(f"generator '{gid}' thiếu generatorName non-empty")
        if not g.get("output"):
            errs.append(f"generator '{gid}' thiếu output non-empty")
        input_spec = g.get("inputSpec")
        if not input_spec:
            errs.append(f"generator '{gid}' thiếu inputSpec")
            continue
        resolved = (_REPO_ROOT / input_spec).resolve()
        if resolved != _MOBILE_YAML.resolve():
            errs.append(
                f"generator '{gid}' inputSpec={input_spec!r} resolve→{resolved} "
                f"≠ _MOBILE_YAML {_MOBILE_YAML} (config rời khỏi YAML SSoT)"
            )
        elif not resolved.exists():
            errs.append(f"generator '{gid}' inputSpec trỏ file KHÔNG tồn tại: {resolved}")
    return errs


class TestMobileCodegenConfig(unittest.TestCase):
    """TC-MOB-OAS-28 — C-DoD-CFG: codegen-config-validity guard (STDLIB json, KHÔNG toolchain).

    Validate openapitools.json (runnable-config) ↔ mobile YAML consistency. File read-only
    (KHÔNG sửa) — drift bắt qua inject IN-MEMORY (json deepcopy). SSoT-path = `_MOBILE_YAML`
    (single-SSoT, AC-3). SSoT doc: completion/EPIC-V-codegen-verification.md §3.2 + §4 V1.
    """

    @classmethod
    def setUpClass(cls):
        cls.exists = _OPENAPITOOLS_JSON.exists()
        cls.cfg = _load_openapitools() if cls.exists else None

    def setUp(self):
        if not self.exists:
            self.skipTest(f"Thiếu openapitools.json: {_OPENAPITOOLS_JSON}")

    # ── AC-1 — config-validity guard (STDLIB-only) ──────────────────────────────────────
    def test_mob_oas_28a_openapitools_exists_and_valid_json(self):
        """openapitools.json TỒN TẠI + parse được bằng STDLIB json.load (KHÔNG java/npx)."""
        self.assertTrue(_OPENAPITOOLS_JSON.exists(), f"Thiếu config: {_OPENAPITOOLS_JSON}")
        self.assertIsInstance(self.cfg, dict, "json.load openapitools.json phải trả dict")

    def test_mob_oas_28b_generator_cli_version_pinned(self):
        """(i) generator-cli.version == '7.23.0' — NOT empty, NOT skeleton/placeholder."""
        version = ((self.cfg.get("generator-cli") or {}).get("version"))
        self.assertTrue(version, "generator-cli.version RỖNG/thiếu (config bare/skeleton).")
        self.assertEqual(
            version, _OPENAPITOOLS_VERSION,
            f"generator-cli.version PHẢI pin {_OPENAPITOOLS_VERSION!r} (got {version!r}).",
        )

    def test_mob_oas_28c_generators_non_empty_with_generator_name(self):
        """(ii) generators KHÔNG rỗng + có ≥1 generatorName (config runnable, KHÔNG bare-pin)."""
        generators = _config_generators(self.cfg)
        self.assertTrue(
            generators,
            "generators RỖNG — config bare version-pin (KHÔNG runnable). Cần khối "
            "generator-cli.generators ≥1 target.",
        )
        names = [(g or {}).get("generatorName") for g in generators.values()]
        self.assertTrue(
            any(names), f"KHÔNG generator nào có generatorName: {list(generators)}",
        )
        # 3 target mobile @source (dart-dio/kotlin/typescript-axios) — chứng minh runnable đa-stack.
        self.assertGreaterEqual(
            len(generators), 1, "Phải có ≥1 generator (config runnable).",
        )

    def test_mob_oas_28d_every_inputspec_resolves_to_mobile_yaml_ssot(self):
        """(iii)+AC-3 — MỌI generator.inputSpec resolve (repo-relative) == `_MOBILE_YAML`
        (single-SSoT path, KHÔNG hardcode path-string) + file TỒN TẠI."""
        generators = _config_generators(self.cfg)
        self.assertTrue(generators, "generators rỗng — không có inputSpec để kiểm.")
        for gid, g in generators.items():
            input_spec = (g or {}).get("inputSpec")
            self.assertTrue(input_spec, f"generator '{gid}' thiếu inputSpec.")
            resolved = (_REPO_ROOT / input_spec).resolve()
            self.assertEqual(
                resolved, _MOBILE_YAML.resolve(),
                f"generator '{gid}' inputSpec={input_spec!r} PHẢI trỏ _MOBILE_YAML SSoT "
                f"({_MOBILE_YAML}); resolve→{resolved}.",
            )
            self.assertTrue(
                resolved.exists(), f"generator '{gid}' inputSpec trỏ file KHÔNG tồn tại: {resolved}",
            )

    def test_mob_oas_28e_every_generator_has_name_and_output(self):
        """(iv) mỗi generator có generatorName non-empty + output non-empty (runnable per-target)."""
        generators = _config_generators(self.cfg)
        self.assertTrue(generators, "generators rỗng.")
        for gid, g in generators.items():
            g = g or {}
            self.assertTrue((g.get("generatorName") or ""), f"generator '{gid}' thiếu generatorName.")
            self.assertTrue((g.get("output") or ""), f"generator '{gid}' thiếu output.")

    def test_mob_oas_28f_config_validity_aggregate_green(self):
        """(gộp AC-1) `_config_validity_errors(config THẬT)` = [] ⇒ runnable-config codegen-ready."""
        errs = _config_validity_errors(self.cfg)
        self.assertEqual(
            errs, [],
            f"openapitools.json KHÔNG phải runnable-config codegen-ready (drift config↔YAML): {errs}",
        )

    # ── AC-2 — anti-false-green / drift-bắt (inject IN-MEMORY, KHÔNG sửa file thật) ──────
    def test_mob_oas_28g_negative_wrong_inputspec_goes_red(self):
        """(AC-2.1) Đổi 1 inputSpec sang path SAI (in-memory deepcopy) ⇒ guard PHẢI RED."""
        mutated = copy.deepcopy(self.cfg)
        gens = _config_generators(mutated)
        first = next(iter(gens))
        gens[first]["inputSpec"] = "docs/mobile/openapi/__WRONG_PATH__.yaml"
        errs = _config_validity_errors(mutated)
        self.assertTrue(
            any("inputSpec" in e and first in e for e in errs),
            f"Guard KHÔNG bắt inputSpec sai path → false-green (config rời YAML không bị bắt): {errs}",
        )

    def test_mob_oas_28h_negative_missing_generators_goes_red(self):
        """(AC-2.2) Xoá block generators (in-memory) ⇒ guard PHẢI RED (config bare-pin câm)."""
        mutated = copy.deepcopy(self.cfg)
        (mutated.get("generator-cli") or {}).pop("generators", None)
        errs = _config_validity_errors(mutated)
        self.assertTrue(
            any("generators RỖNG" in e for e in errs),
            f"Guard KHÔNG bắt generators rỗng → false-green (bare version-pin lọt): {errs}",
        )

    def test_mob_oas_28i_negative_empty_version_goes_red(self):
        """(AC-2.3) Đặt version='' (in-memory) ⇒ guard PHẢI RED (config skeleton/placeholder)."""
        mutated = copy.deepcopy(self.cfg)
        (mutated.get("generator-cli") or {})["version"] = ""
        errs = _config_validity_errors(mutated)
        self.assertTrue(
            any("version" in e.lower() for e in errs),
            f"Guard KHÔNG bắt version rỗng → false-green (skeleton-pin lọt): {errs}",
        )

    def test_mob_oas_28j_control_real_config_stays_green(self):
        """(AC-2 control) Config THẬT (deepcopy KHÔNG inject) ⇒ guard XANH. Chứng minh 28g..i
        ĐỎ là DO inject (guard KHÔNG luôn-đỏ) — kiểm tính phân biệt drift của guard."""
        errs = _config_validity_errors(copy.deepcopy(self.cfg))
        self.assertEqual(
            errs, [], f"Config THẬT KHÔNG-inject phải XANH (guard không luôn-đỏ): {errs}",
        )


def _discover_test_methods() -> list[str]:
    """Introspect module hiện tại → đếm MỌI method `test*` của MỌI `unittest.TestCase`.

    STDLIB-only (inspect): liệt kê class con TestCase định-nghĩa TRONG module này
    (loại import-vào), gom method bắt đầu 'test'. Đây là SỰ-THẬT runtime mà runner
    `bench run-tests` sẽ load — khớp 1:1 với `Ran N tests`. Trả list 'Class.method'
    (đã khử trùng-lặp do kế-thừa: method định-nghĩa ở class nào tính ở class đó).
    """
    module = __import__(__name__, fromlist=["*"])
    found: list[str] = []
    for _cls_name, cls in inspect.getmembers(module, inspect.isclass):
        if not issubclass(cls, unittest.TestCase) or cls is unittest.TestCase:
            continue
        if cls.__module__ != __name__:  # bỏ class import từ module khác
            continue
        for meth_name, _meth in inspect.getmembers(cls, inspect.isfunction):
            if not meth_name.startswith("test"):
                continue
            # chỉ tính method ĐỊNH-NGHĨA ở class này (không đếm lại bản kế-thừa)
            if meth_name in vars(cls):
                found.append(f"{cls.__name__}.{meth_name}")
    return found


class TestMobileOasCountSelfVerify(unittest.TestCase):
    """F-C3 (Vòng 11) META-GUARD — count test-method self-verify chống tái count-drift.

    Assert số test-method LOAD ĐƯỢC của module == `_EXPECTED_TEST_COUNT` (SSoT định-nghĩa
    MỘT LẦN, line ~92). Thêm/bớt TC mà quên cập const ⇒ RED NGAY ⇒ buộc doc + const đồng-bộ.
    Count gồm CHÍNH TC này (count-after-add = 108 là sự-thật cuối). RED-before/GREEN-after
    đã chứng minh: tạm set const lệch (999) → RED; set đúng (108) → GREEN ⇒ guard THẬT bắt
    drift, KHÔNG pass-suông. Doc count-hiện-hành PHẢI = `_EXPECTED_TEST_COUNT`.
    """

    def test_mob_oas_NN_count_matches_ssot(self):
        """Số test-method introspect được PHẢI == _EXPECTED_TEST_COUNT (drift = RED).

        ĐÚNG 1 TC (count-after-add 107→108). Sanity introspection (count>0 + tự-thấy chính
        meta-guard) gộp VÀO ĐÂY để KHÔNG nâng count thêm — chống introspection-rỗng giả-GREEN
        (filter sai → assertEqual(0,0) vẫn pass) mà vẫn giữ tổng = 108.
        """
        discovered = _discover_test_methods()
        actual = len(discovered)
        # Sanity 1 — introspection KHÔNG rỗng/hỏng-filter (chống giả-GREEN do _discover trả []).
        self.assertGreater(actual, 100, "Introspection trả < 100 test-method — filter hỏng.")
        # Sanity 2 — chính meta-guard NẰM TRONG tập discover (phạm-vi introspect đúng module).
        self.assertIn(
            "TestMobileOasCountSelfVerify.test_mob_oas_NN_count_matches_ssot",
            set(discovered),
            "Meta-guard KHÔNG tự-thấy trong tập introspect → _discover_test_methods sai phạm-vi.",
        )
        # Assert chính — count khớp SSoT (drift = RED).
        self.assertEqual(
            actual,
            _EXPECTED_TEST_COUNT,
            f"COUNT-DRIFT: introspect {actual} test-method NHƯNG _EXPECTED_TEST_COUNT="
            f"{_EXPECTED_TEST_COUNT}. Nếu CỐ Ý thêm/bớt TC → cập NHẬT _EXPECTED_TEST_COUNT "
            f"(line ~92) + đồng-bộ count trong docs/mobile (roadmap §10 + EPIC-C + "
            f"ACCEPTANCE-CHECKLIST C-A1/Baseline/GO-2 + 04-api-contract + EPIC-V). "
            f"Drift KHÔNG-chủ-ý = regress, sửa code. discovered(head)={sorted(discovered)[:3]}",
        )


# ── F-C4 (Vòng 13) — TC-MOB-OAS-29: stale-line-ref guard roadmap §3 ↔ source ──────────────
#   `13-be-completion-roadmap.md §3` từng quảng-cáo việc-đã-xong (4 scan/createPm typed C2 +
#   list-element C3-split) NHƯ việc-cần-làm (4-STUB/15-path stale prose) + dùng line-ref tuyệt-đối
#   `152-157` cho `_STUB_PATHS` (đã CHẾT do line-drift; symbol thật = `set(_DEVICE_TOKEN_FROZEN)`).
#   Guard chống tái-drift: (a) 0 anchor stale trong roadmap (trừ dạng [SUPERSEDED]/@landing);
#   (b) claim "16 path/operationId" khớp len(spec.paths) THẬT; (c) ref _STUB_PATHS dùng dạng-SYMBOL
#   KHÔNG số-dòng-tuyệt-đối; (d) RED-before/GREEN-after — inject anchor stale → detector PHẢI bắt.
#   SSoT: ../completion/EPIC-C-api-contract.md §F-C4 + ACCEPTANCE-CHECKLIST C-A14.
class TestMobileRoadmapStateReconciled(unittest.TestCase):
    """F-C4 — state-reconciliation: roadmap §3 phản-ánh ĐÚNG source (16-path/2-device-token-STUB),
    KHÔNG quảng-cáo việc-đã-xong là TO-BUILD. Raw-text introspection (KHÔNG đụng api/services .py)."""

    @classmethod
    def setUpClass(cls):
        cls.roadmap_exists = _ROADMAP_MD.exists()
        cls.raw = _ROADMAP_MD.read_text(encoding="utf-8") if cls.roadmap_exists else ""
        cls.spec = _load_spec() if _MOBILE_YAML.exists() else None

    @staticmethod
    def _scan_stale(text: str) -> list[str]:
        """Trả về list 'Lnn: <line>  (/pat/)' cho MỌI anchor stale — TRỪ dòng đánh-dấu lịch-sử
        ([SUPERSEDED] / @landing = mốc quá-khứ ĐƯỢC PHÉP giữ)."""
        hits = []
        for ln, line in enumerate(text.splitlines(), start=1):
            up = line.upper()
            if "[SUPERSEDED" in up or "@LANDING" in up:
                continue
            for pat in _ROADMAP_STALE_ANCHORS:
                if re.search(pat, line):
                    hits.append(f"L{ln}: {line.strip()}  (match /{pat}/)")
        return hits

    def test_mob_oas_29a_roadmap_no_stale_stub_anchors(self):
        """(a) roadmap §3 KHÔNG còn anchor stale CURRENT/TO-BUILD (15-path / 4-STUB / chưa-typed /
        generic⚠️ / 152-157) — mọi mô-tả phản-ánh source HIỆN-HÀNH (16-path, 2-device-token STUB)."""
        self.assertTrue(self.roadmap_exists, f"Thiếu roadmap: {_ROADMAP_MD}")
        hits = self._scan_stale(self.raw)
        self.assertEqual(
            hits, [],
            "STALE-ANCHOR còn trong roadmap §3 — quảng-cáo việc-đã-xong (4 scan/createPm typed C2 + "
            "list-element C3-split) NHƯ việc-cần-làm / dùng line-ref tuyệt-đối đã chết. Reconcile §3 "
            "về source THẬT (16 path/operationId; _STUB_PATHS=set(_DEVICE_TOKEN_FROZEN)=2 device-token). "
            "Chỉ giữ dạng lịch-sử khi cùng dòng [SUPERSEDED]/@landing. Hits:\n  " + "\n  ".join(hits),
        )

    def test_mob_oas_29b_roadmap_16_path_claim_matches_spec(self):
        """(b) claim '16 path/16 operationId' trong roadmap khớp len(spec.paths) THẬT @working-tree —
        chống claim count drift khỏi yaml (vd quên cập sau khi thêm path)."""
        self.assertTrue(self.roadmap_exists, f"Thiếu roadmap: {_ROADMAP_MD}")
        self.assertIsNotNone(self.spec, f"Thiếu/lỗi yaml: {_MOBILE_YAML}")
        actual_paths = len(self.spec.get("paths", {}))
        op_ids = [
            op["operationId"]
            for p in self.spec["paths"].values()
            for verb, op in p.items()
            if verb in _HTTP_VERBS and isinstance(op, dict) and "operationId" in op
        ]
        # source THẬT = 16/16; nếu yaml đổi, sửa CẢ yaml + roadmap claim (drift = RED).
        self.assertEqual(actual_paths, 16, f"yaml paths THẬT={actual_paths} ≠ 16 (claim roadmap §3.1).")
        self.assertEqual(len(op_ids), 16, f"yaml operationId THẬT={len(op_ids)} ≠ 16.")
        # roadmap PHẢI khẳng định đúng con-số THẬT (KHÔNG để 15 cũ — đã phủ ở 29a, đây assert positive).
        self.assertRegex(
            self.raw, r"16 path",
            "roadmap §3.1 KHÔNG khẳng-định '16 path' — claim count phải khớp len(spec.paths)=16 THẬT.",
        )

    def test_mob_oas_29c_stub_paths_ref_by_symbol_not_absolute_line(self):
        """(c) ref `_STUB_PATHS` trong roadmap dùng dạng-SYMBOL, KHÔNG số-dòng-tuyệt-đối (re-verify
        @source theo symbol — line-ref tuyệt-đối chết do drift). EPIC-D D4: symbol = `set()` (∅,
        device-token typed) — KHÔNG còn `set(_DEVICE_TOKEN_FROZEN)`."""
        self.assertTrue(self.roadmap_exists, f"Thiếu roadmap: {_ROADMAP_MD}")
        # roadmap §3.3 phải nhắc symbol-form `_STUB_PATHS = set()` (∅ sau D4 — device-token typed).
        self.assertRegex(
            self.raw, r"_STUB_PATHS\s*=\s*set\(\)",
            "roadmap §3.3 KHÔNG ref `_STUB_PATHS = set()` (dạng-symbol, ∅ sau EPIC-D D4). "
            "Re-verify @source theo SYMBOL, KHÔNG số-dòng-tuyệt-đối (line-drift).",
        )
        # KHÔNG còn line-ref tuyệt-đối kiểu `test_mobile_oas.py:NNN-NNN` cho _STUB_PATHS.
        abs_line_refs = re.findall(r"_STUB_PATHS`?\s*@?\s*`?[^`\n]*test_mobile_oas\.py:\d+-\d+", self.raw)
        self.assertEqual(
            abs_line_refs, [],
            f"roadmap còn line-ref TUYỆT-ĐỐI cho _STUB_PATHS (chết do drift) — đổi sang symbol: {abs_line_refs}",
        )

    def test_mob_oas_29d_detector_red_before_on_injected_stale(self):
        """(d) Anti-false-green — detector 29a KHÔNG pass-suông: inject 1 anchor stale vào BẢN SAO
        text (KHÔNG ghi file) → detector PHẢI bắt; control text THẬT = sạch."""
        self.assertTrue(self.roadmap_exists, f"Thiếu roadmap: {_ROADMAP_MD}")
        # control: text THẬT hiện hành = sạch (đồng nhất 29a GREEN).
        self.assertEqual(self._scan_stale(self.raw), [], "Control roadmap THẬT phải SẠCH anchor (đồng bộ 29a).")
        # inject: thêm dòng prose bịa trạng-thái cũ → detector PHẢI bắt (RED-before).
        injected = self.raw + "\n- YAML 15 path, 15/15 operationId; 4 STUB path còn lại chưa typed.\n"
        self.assertTrue(
            self._scan_stale(injected),
            "Detector stale-anchor KHÔNG bắt dòng inject '15 path / 4 STUB path còn lại / chưa typed' "
            "→ guard giả (false-green). Detector PHẢI RED-trước-fix khi prose tái-drift về trạng-thái cũ.",
        )
        # đảm bảo dòng [SUPERSEDED] KHÔNG bị flag (lịch-sử ĐƯỢC PHÉP).
        hist = self.raw + "\n> [SUPERSEDED] bản nháp cũ từng ghi 15 path / 4 STUB path còn lại.\n"
        self.assertEqual(
            self._scan_stale(hist), [],
            "Dòng [SUPERSEDED] (lịch-sử) bị flag oan — guard phải BỎ QUA dạng lịch-sử [SUPERSEDED]/@landing.",
        )


# ── F-B2 (Vòng 31 closure) — TC-MOB-OAS-30: refresh-on-401 doc-presence drift-guard ──────────
#   B2 acceptance #2: invariant refresh-on-401 (401 → refresh MỘT lần → retry → fail re-auth)
#   PHẢI tồn tại NGUYÊN-VĂN trong CẢ docs/mobile/03-auth-oauth2.md (§2.5 policy + §2.6 sequence)
#   VÀ docs/mobile/04-api-contract.md (§9d(n) sequence). Trước F-B2 chỉ one-time grep (B-A4) →
#   nay MACHINE-CHECKED: doc bị xoá/đổi token load-bearing (vd xoá block §9d(n) HOẶC đổi
#   grant_type=refresh_token→authorization_code) → guard RED ngay.
#   Pattern y hệt `test_mobile_preflight.py::TestMobilePreflightDocValueParity` (F-B3): region-slice
#   theo heading-anchor (§2.5/§2.6/§9d) + assertIn nguyên-văn token load-bearing + RED-before
#   deepcopy/string-mutate. STDLIB-only (open()+read), NO Frappe DB, NO yaml, NO reload, NO migrate.
#   SSoT: docs/mobile/03-auth-oauth2.md §1.3e/§2.5/§2.6 + 04-api-contract.md §9d(n);
#     ../completion/EPIC-B-auth-provisioning.md B2 + §4.4 + ACCEPTANCE-CHECKLIST B-A4.
_DOC_03_AUTH = _REPO_ROOT / "docs" / "mobile" / "03-auth-oauth2.md"
_DOC_04_API = _REPO_ROOT / "docs" / "mobile" / "04-api-contract.md"
_DOC_08_SEC = _REPO_ROOT / "docs" / "mobile" / "08-security-compliance.md"
_DOC_10_OPS = _REPO_ROOT / "docs" / "mobile" / "10-deploy-ops.md"
_ADR_004 = _REPO_ROOT / "docs" / "mobile" / "ADR-MOBILE-004.md"


def _read_doc_text(path: Path) -> str:
    """Đọc raw-text doc qua STDLIB Path.read_text (KHÔNG DB, KHÔNG yaml, KHÔNG lib mới)."""
    return path.read_text(encoding="utf-8")


def _doc_region(text: str, start_marker: str, end_markers: tuple[str, ...]) -> str:
    """Cắt vùng raw-text từ dòng chứa ``start_marker`` tới dòng chứa marker kết tiếp.

    Section-scoped để guard chấm ĐÚNG vùng (§2.5 / §2.6 / §9d), tránh literal lọt do xuất
    hiện ở section khác (vd grant_type=refresh_token có ở §1.1/§1.3e/§2.2). Trả phần thân
    (KHÔNG gồm dòng start/end marker). Mirror `test_mobile_preflight._section`.
    """
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines) if start_marker in ln), None)
    assert start is not None, (
        f"Không tìm thấy start-marker '{start_marker}' — doc đổi cấu trúc heading?"
    )
    end = next(
        (j for j in range(start + 1, len(lines)) if any(m in lines[j] for m in end_markers)),
        len(lines),
    )
    return "\n".join(lines[start + 1 : end])


def _assert_refresh_on_401_invariant(
    testcase: unittest.TestCase, region_03_25: str, region_03_26: str, region_04_9d: str
) -> None:
    """Khẳng định invariant refresh-on-401 hiện diện NGUYÊN-VĂN ở 3 vùng load-bearing.

    Token load-bearing (KHÔNG hardcode rải rác — gom 1 chỗ để RED-before mutate đúng điểm):
      · grant_type=refresh_token       — grant đổi token (CẢ 03 §2.5/§2.6 VÀ 04 §9d).
      · refresh MỘT lần → retry        — policy 401: thử-refresh-1-lần rồi retry request gốc.
      · KHÔNG vòng lặp refresh vô hạn   — chống infinite-loop (chỉ ở 03; cross-ref ở §2.6/04).
      · re-auth khi refresh fail        — fallback xoá token → đăng nhập lại.
      · 3-bước sequence (401 dispatcher → get_token refresh → retry access MỚI) — §2.6 + §9d(n).
    Tách vùng để 1 literal lọt-section KHÔNG che drift ở section khác.
    """
    GRANT = "grant_type=refresh_token"
    # ── 03 §2.5 — policy app: 401 → refresh MỘT lần → retry; refresh fail → re-auth; no-loop ──
    testcase.assertIn(
        GRANT, region_03_25,
        "03 §2.5 thiếu '`grant_type=refresh_token`' — policy 401→refresh drift khỏi §1.1 bước (e).",
    )
    testcase.assertIn(
        "MỘT lần", region_03_25,
        "03 §2.5 thiếu quy-tắc refresh 'MỘT lần' → mất chặn infinite-refresh ở tầng policy.",
    )
    testcase.assertIn(
        "retry", region_03_25,
        "03 §2.5 thiếu 'retry' request gốc sau refresh — policy 401 không đóng vòng.",
    )
    testcase.assertIn(
        "re-auth", region_03_25,
        "03 §2.5 thiếu fallback 're-auth' khi refresh fail.",
    )
    testcase.assertIn(
        "KHÔNG vòng lặp refresh vô hạn", region_03_25,
        "03 §2.5 thiếu khẳng định 'KHÔNG vòng lặp refresh vô hạn' — invariant chống infinite-loop mất.",
    )
    # ── 03 §2.6 — block sequence refresh-on-401 3-bước (401 dispatcher RAW → get_token → retry MỚI) ──
    testcase.assertIn(
        GRANT, region_03_26,
        "03 §2.6 block sequence thiếu '`grant_type=refresh_token`' (bước đổi token).",
    )
    for step, lit in (
        ("401 dispatcher RAW", "401 (dispatcher, RAW Frappe)"),
        ("retry access MỚI", "access MỚI"),
    ):
        testcase.assertIn(
            lit, region_03_26,
            f"03 §2.6 block sequence thiếu bước '{step}' (literal '{lit}') — sequence 3-bước drift.",
        )
    testcase.assertIn(
        "KHÔNG vòng lặp refresh vô hạn", region_03_26,
        "03 §2.6 thiếu cross-ref quy-tắc 'KHÔNG vòng lặp refresh vô hạn' (đồng bộ §2.5).",
    )
    # ── 04 §9d(n) — block sequence refresh-on-401 (curl 3 bước) + quy tắc refresh-1-lần ──
    testcase.assertIn(
        "**(n) Sequence refresh-on-401**", region_04_9d,
        "04 §9d thiếu header block '(n) Sequence refresh-on-401' — sequence machine-readable mất.",
    )
    testcase.assertIn(
        GRANT, region_04_9d,
        "04 §9d(n) thiếu '`grant_type=refresh_token`' (bước 2 curl đổi refresh→access).",
    )
    for step, lit in (
        ("401 dispatcher RAW", "401 (dispatcher RAW Frappe"),
        ("retry access MỚI", "access MỚI"),
    ):
        testcase.assertIn(
            lit, region_04_9d,
            f"04 §9d(n) curl thiếu bước '{step}' (literal '{lit}') — sequence 3-bước drift.",
        )
    testcase.assertIn(
        "refresh MỘT lần → retry → fail thì re-auth", region_04_9d,
        "04 §9d thiếu quy-tắc 'refresh MỘT lần → retry → fail thì re-auth' — invariant policy mất.",
    )


class TestMobileRefreshOn401DocGuard(unittest.TestCase):
    """F-B2 (B2 acceptance #2) — refresh-on-401 doc-presence drift-guard.

    Machine-check invariant refresh-on-401 (401 → refresh MỘT lần → retry → fail re-auth, KHÔNG
    vòng lặp vô hạn) TỒN TẠI nguyên-văn ở CẢ 03 (§2.5 policy + §2.6 sequence 3-bước) VÀ 04 (§9d(n)
    sequence 3-bước) + grant_type=refresh_token cross-file parity. Thay one-time grep (B-A4) bằng
    guard chạy mỗi suite. STDLIB-only (read_text), NO Frappe DB / yaml / reload / migrate.
    Pattern: region-slice heading-anchor + assertIn nguyên-văn + RED-before string-mutate (F-B3).
    """

    @classmethod
    def setUpClass(cls):
        cls.text_03 = _read_doc_text(_DOC_03_AUTH)
        cls.text_04 = _read_doc_text(_DOC_04_API)
        # 03 §2.5 — từ '### 2.5 Policy app' tới '### 2.6'.
        cls.region_03_25 = _doc_region(cls.text_03, "### 2.5 Policy app", ("### 2.6",))
        # 03 §2.6 — từ '### 2.6 userinfo / whoami' tới '## 3.' (kết section §2).
        cls.region_03_26 = _doc_region(
            cls.text_03, "### 2.6 userinfo / whoami", ("## 3. Scope", "\n---\n")
        )
        # 04 §9d — từ '### 9d.' tới '## 9b.' (kết block §9d, trước section §9b).
        cls.region_04_9d = _doc_region(
            cls.text_04, "### 9d. userinfo / whoami + refresh-on-401", ("## 9b.",)
        )

    def test_mob_oas_30a_policy_25_refresh_once_retry_no_loop(self):
        """NNa — 03 §2.5 chứa nguyên-văn policy 401→refresh(grant_type=refresh_token) MỘT lần→retry
        + refresh-fail→re-auth + 'KHÔNG vòng lặp refresh vô hạn'."""
        region = self.region_03_25
        self.assertIn("grant_type=refresh_token", region, "03 §2.5 thiếu grant_type=refresh_token.")
        self.assertIn("MỘT lần", region, "03 §2.5 thiếu 'MỘT lần'.")
        self.assertIn("retry", region, "03 §2.5 thiếu 'retry'.")
        self.assertIn("re-auth", region, "03 §2.5 thiếu 're-auth' khi refresh fail.")
        self.assertIn(
            "KHÔNG vòng lặp refresh vô hạn", region,
            "03 §2.5 thiếu 'KHÔNG vòng lặp refresh vô hạn'.",
        )

    def test_mob_oas_30b_seq_26_three_step_block(self):
        """NNb — 03 §2.6 chứa block sequence refresh-on-401 3-bước (401 dispatcher RAW → POST
        get_token grant_type=refresh_token → retry access MỚI → 200)."""
        region = self.region_03_26
        self.assertIn(
            "Sequence refresh-on-401", region,
            "03 §2.6 thiếu nhãn block 'Sequence refresh-on-401'.",
        )
        self.assertIn(
            "401 (dispatcher, RAW Frappe)", region,
            "03 §2.6 thiếu bước-1 '401 (dispatcher, RAW Frappe)'.",
        )
        self.assertIn(
            "grant_type=refresh_token", region,
            "03 §2.6 thiếu bước-2 POST get_token grant_type=refresh_token.",
        )
        self.assertIn(
            "access MỚI", region,
            "03 §2.6 thiếu bước-3 retry với 'access MỚI'.",
        )

    def test_mob_oas_30c_api_9d_n_three_step_curl(self):
        """NNc — 04 §9d(n) chứa block sequence refresh-on-401 (curl 3 bước: 401 → get_token
        grant_type=refresh_token → retry access MỚI) + quy tắc 'refresh MỘT lần → retry → fail re-auth'."""
        region = self.region_04_9d
        self.assertIn(
            "**(n) Sequence refresh-on-401**", region,
            "04 §9d thiếu header block '(n) Sequence refresh-on-401'.",
        )
        self.assertIn(
            "401 (dispatcher RAW Frappe", region,
            "04 §9d(n) curl thiếu bước-1 401 dispatcher RAW.",
        )
        self.assertIn(
            "grant_type=refresh_token", region,
            "04 §9d(n) curl thiếu bước-2 get_token grant_type=refresh_token.",
        )
        self.assertIn(
            "access MỚI", region,
            "04 §9d(n) curl thiếu bước-3 retry với 'access MỚI'.",
        )
        self.assertIn(
            "refresh MỘT lần → retry → fail thì re-auth", region,
            "04 §9d thiếu quy-tắc 'refresh MỘT lần → retry → fail thì re-auth'.",
        )

    def test_mob_oas_30d_cross_file_parity_and_red_before(self):
        """NNd — grant_type=refresh_token xuất hiện ≥1 ở CẢ 03 VÀ 04 (cross-file parity) +
        control GREEN; RED-before: mutate BẢN SAO in-memory (xoá §9d block HOẶC đổi grant_type) →
        guard PHẢI raise AssertionError (chứng minh bắt drift, KHÔNG pass-suông)."""
        GRANT = "grant_type=refresh_token"
        # (a) cross-file parity — token grant hiện diện ≥1 ở mỗi file (toàn-văn).
        self.assertGreaterEqual(
            self.text_03.count(GRANT), 1, "03 KHÔNG có grant_type=refresh_token nào (cross-file parity vỡ)."
        )
        self.assertGreaterEqual(
            self.text_04.count(GRANT), 1, "04 KHÔNG có grant_type=refresh_token nào (cross-file parity vỡ)."
        )
        # (b) control GREEN — text THẬT pass full-invariant assert (đồng bộ 30a/b/c).
        _assert_refresh_on_401_invariant(self, self.region_03_25, self.region_03_26, self.region_04_9d)

        # (c) RED-before #1 — xoá BLOCK §9d(n) sequence khỏi BẢN SAO 04 → guard PHẢI bắt.
        mutated_04 = self.region_04_9d.replace("**(n) Sequence refresh-on-401**", "").replace(GRANT, "")
        self.assertNotEqual(mutated_04, self.region_04_9d, "Bản-sao §9d phải khác bản gốc (block tồn tại).")
        with self.assertRaises(AssertionError, msg="Guard KHÔNG bắt việc xoá §9d(n) — false-green!"):
            _assert_refresh_on_401_invariant(self, self.region_03_25, self.region_03_26, mutated_04)

        # (d) RED-before #2 — đổi grant_type=refresh_token→authorization_code trong BẢN SAO 03 §2.5.
        mutated_03_25 = self.region_03_25.replace(GRANT, "grant_type=authorization_code")
        self.assertNotEqual(mutated_03_25, self.region_03_25, "Bản-sao 03 §2.5 phải khác (grant literal tồn tại).")
        with self.assertRaises(AssertionError, msg="Guard KHÔNG bắt đổi grant_type ở 03 §2.5 — false-green!"):
            _assert_refresh_on_401_invariant(self, mutated_03_25, self.region_03_26, self.region_04_9d)

        # (e) control RE-confirm — text THẬT vẫn GREEN sau 2 mutate (mutate KHÔNG đụng bản gốc).
        _assert_refresh_on_401_invariant(self, self.region_03_25, self.region_03_26, self.region_04_9d)


def _assert_traceback_hardening_invariant(
    testcase: unittest.TestCase, region_08_4: str, region_adr_cons: str, region_10_62: str
) -> None:
    """Khẳng định invariant prod-hardening 'TẮT allow_error_traceback' hiện diện NGUYÊN-VĂN
    ở 3 vùng load-bearing (G3 AUTO-part). Gom token 1 chỗ để RED-before mutate đúng điểm.

    Token load-bearing (verify @source Frappe v15.107.2, read-only):
      · allow_error_traceback        — tên System Setting (field `system_settings.json:263`,
                                        fieldtype Check, default 1 = ON).
      · response.py:60-65            — gate THẬT `is_traceback_allowed()` đọc
                                        `get_system_settings('allow_error_traceback')` (KHÔNG
                                        developer_mode/site_config). Dùng ở `:36/:182/:190/:203`.
      · negation 'KHÔNG ... developer_mode' — chống prose sai-cơ-chế (gate ≠ developer_mode/site_config).
      · System Setting = 0           — hành động prod-hardening (tắt cờ → 401/403/429 KHÔNG leak
                                        traceback/SQL).
    Cross-file parity: cùng item phải có ở 08 §4 ∩ ADR-004 Consequences (≥1 hit/file). 10 §6.2 =
    note reload gunicorn (--preload) SAU đổi System Setting + rate-limit-header (429 Retry-After/
    X-RateLimit-* CHỈ khi conf.rate_limit/nginx; decorator-429 body-only no-header KNOWN).
    """
    SETTING = "allow_error_traceback"
    EVID = "response.py:60-65"
    # ── 08 §4 — checklist item (b) PROD TẮT allow_error_traceback (System Setting=0) ──
    testcase.assertIn(
        SETTING, region_08_4,
        "08 §4 thiếu '`allow_error_traceback`' — checklist hardening item (b) drift.",
    )
    testcase.assertIn(
        EVID, region_08_4,
        "08 §4 thiếu evidence '`response.py:60-65`' (gate is_traceback_allowed) — claim không grounded.",
    )
    testcase.assertIn(
        "System Setting", region_08_4,
        "08 §4 thiếu 'System Setting' — phải nói RÕ gate là System Setting (không config khác).",
    )
    # Negation chống prose sai-cơ-chế: phải khẳng định KHÔNG phải developer_mode/site_config.
    testcase.assertIn(
        "developer_mode", region_08_4,
        "08 §4 thiếu negation nhắc 'developer_mode' — phải ghi RÕ gate KHÔNG phải developer_mode.",
    )
    testcase.assertRegex(
        region_08_4, r"KHÔNG[^\n]*developer_mode",
        "08 §4 thiếu khẳng định 'KHÔNG ... developer_mode/site_config' — chống prose sai-cơ-chế.",
    )
    # ── ADR-004 Consequences (Ràng buộc / phải làm) — cùng item traceback-off ──
    testcase.assertIn(
        SETTING, region_adr_cons,
        "ADR-004 Consequences thiếu '`allow_error_traceback`' — cross-file parity với 08 §4 vỡ.",
    )
    testcase.assertIn(
        EVID, region_adr_cons,
        "ADR-004 Consequences thiếu evidence '`response.py:60-65`' (đồng bộ 08 §4).",
    )
    testcase.assertIn(
        "System Setting", region_adr_cons,
        "ADR-004 Consequences thiếu 'System Setting' — phải đồng bộ cơ-chế với 08 §4.",
    )
    # ── 10 §6.2 — note: reload gunicorn (--preload) SAU đổi System Setting + rate-limit-header ──
    testcase.assertIn(
        SETTING, region_10_62,
        "10 §6.2 thiếu '`allow_error_traceback`' — note hardening reload drift.",
    )
    testcase.assertIn(
        "--preload", region_10_62,
        "10 §6.2 thiếu 'gunicorn --preload' reload note — đổi System Setting chỉ live SAU reload.",
    )
    testcase.assertIn(
        "Retry-After", region_10_62,
        "10 §6.2 thiếu 'Retry-After' — rate-limit-header note (429 header CHỈ khi conf.rate_limit/nginx).",
    )
    testcase.assertIn(
        "X-RateLimit", region_10_62,
        "10 §6.2 thiếu 'X-RateLimit-*' — rate-limit-header note thiếu.",
    )


class TestMobileTracebackHardeningDocGuard(unittest.TestCase):
    """G3 (EPIC-G G3 AUTO-part) — prod-hardening 'TẮT allow_error_traceback' doc-presence drift-guard.

    Machine-check invariant: item '(b) PROD TẮT `allow_error_traceback` (System Setting=0)' với
    evidence `response.py:60-65` + negation 'KHÔNG ... developer_mode/site_config' TỒN TẠI nguyên-văn
    ở CẢ 08 §4 (checklist security) VÀ ADR-004 Consequences (cross-file parity) + 10 §6.2 (note reload
    gunicorn --preload SAU đổi System Setting + rate-limit-header 429 Retry-After/X-RateLimit-*).
    Analog F-C4/F-B2 (region-slice heading-anchor + assertIn nguyên-văn + RED-before string-mutate).
    STDLIB-only (Path.read_text + re), NO Frappe DB / yaml / reload / migrate.

    Cơ-chế @source (verify Frappe v15.107.2, read-only): gate = `is_traceback_allowed()`
    (`frappe/utils/response.py:60-65`) đọc `get_system_settings('allow_error_traceback')`
    (System Setting field `system_settings.json:263`, fieldtype Check, default 1=ON); dùng ở
    `:36`/`:182`/`:190`/`:203`. KHÔNG phải developer_mode/site_config.
    """

    @classmethod
    def setUpClass(cls):
        cls.text_08 = _read_doc_text(_DOC_08_SEC)
        cls.text_adr = _read_doc_text(_ADR_004)
        cls.text_10 = _read_doc_text(_DOC_10_OPS)
        # 08 §4 — từ '## 4. Checklist Security' tới '## 5.' (kết section §4).
        cls.region_08_4 = _doc_region(
            cls.text_08, "## 4. Checklist Security Go-live", ("## 5.",)
        )
        # ADR-004 Consequences — từ '**Ràng buộc / phải làm:**' tới '**Rủi ro còn lại:**'.
        cls.region_adr_cons = _doc_region(
            cls.text_adr, "**Ràng buộc / phải làm:**", ("**Rủi ro còn lại:**",)
        )
        # 10 §6.2 — từ '### 6.2 Execute' tới '### 6.3' (kết block §6.2).
        cls.region_10_62 = _doc_region(
            cls.text_10, "### 6.2 Execute", ("### 6.3",)
        )

    def test_mob_oas_31a_08_4_traceback_item_with_evidence(self):
        """NNa — 08 §4 checklist chứa item (b) PROD TẮT allow_error_traceback (System Setting=0)
        + evidence response.py:60-65 + negation KHÔNG ... developer_mode/site_config."""
        region = self.region_08_4
        self.assertIn(
            "allow_error_traceback", region,
            "08 §4 thiếu '`allow_error_traceback`' checklist item.",
        )
        self.assertIn(
            "System Setting=0", region,
            "08 §4 thiếu hành-động hardening 'System Setting=0' (tắt cờ).",
        )
        self.assertIn(
            "response.py:60-65", region,
            "08 §4 thiếu evidence '`response.py:60-65`' (gate is_traceback_allowed).",
        )
        self.assertRegex(
            region, r"KHÔNG[^\n]*developer_mode",
            "08 §4 thiếu negation 'KHÔNG ... developer_mode/site_config' (chống prose sai-cơ-chế).",
        )

    def test_mob_oas_31b_adr_consequences_parity(self):
        """NNb — ADR-004 mục Consequences (Ràng buộc / phải làm) chứa CÙNG item traceback-off
        (allow_error_traceback + evidence response.py:60-65 + System Setting) — đồng bộ 08 §4."""
        region = self.region_adr_cons
        self.assertIn(
            "allow_error_traceback", region,
            "ADR-004 Consequences thiếu '`allow_error_traceback`' (parity với 08 §4 vỡ).",
        )
        self.assertIn(
            "System Setting", region,
            "ADR-004 Consequences thiếu 'System Setting' — cơ-chế đồng bộ 08 §4.",
        )
        self.assertIn(
            "response.py:60-65", region,
            "ADR-004 Consequences thiếu evidence '`response.py:60-65`'.",
        )

    def test_mob_oas_31c_10_62_reload_and_ratelimit_note(self):
        """NNc — 10 §6.2 chứa note: SAU đổi System Setting → reload gunicorn (--preload, 41 workers)
        MỚI live + rate-limit-header (429 Retry-After/X-RateLimit-* CHỈ khi conf.rate_limit/nginx;
        decorator-429 body-only no-header KNOWN)."""
        region = self.region_10_62
        self.assertIn(
            "allow_error_traceback", region,
            "10 §6.2 thiếu '`allow_error_traceback`' reload note.",
        )
        self.assertIn(
            "--preload", region,
            "10 §6.2 thiếu 'gunicorn --preload' — đổi System Setting chỉ live HTTP SAU reload.",
        )
        self.assertIn(
            "Retry-After", region,
            "10 §6.2 thiếu 'Retry-After' header note (rate-limit).",
        )
        self.assertIn(
            "X-RateLimit", region,
            "10 §6.2 thiếu 'X-RateLimit-*' header note.",
        )
        self.assertIn(
            "conf.rate_limit", region,
            "10 §6.2 thiếu điều-kiện 'conf.rate_limit'/nginx (429 header CHỈ khi set).",
        )

    def test_mob_oas_31d_cross_file_parity_and_red_before(self):
        """NNd — cross-file parity (allow_error_traceback ≥1 ở CẢ 08 VÀ ADR-004) + control GREEN;
        RED-before: mutate BẢN SAO in-memory (xoá item khỏi 08 §4 / ADR Consequences / 10 §6.2) →
        guard PHẢI raise AssertionError (chứng minh bắt drift, KHÔNG pass-suông)."""
        SETTING = "allow_error_traceback"
        # (a) cross-file parity — token hiện diện ≥1 ở mỗi file (toàn-văn).
        self.assertGreaterEqual(
            self.text_08.count(SETTING), 1,
            "08 KHÔNG có allow_error_traceback nào (cross-file parity vỡ).",
        )
        self.assertGreaterEqual(
            self.text_adr.count(SETTING), 1,
            "ADR-004 KHÔNG có allow_error_traceback nào (cross-file parity vỡ).",
        )
        # (b) control GREEN — text THẬT pass full-invariant assert (đồng bộ 31a/b/c).
        _assert_traceback_hardening_invariant(
            self, self.region_08_4, self.region_adr_cons, self.region_10_62
        )

        # (c) RED-before #1 — xoá item traceback khỏi BẢN SAO 08 §4 → guard PHẢI bắt.
        mutated_08 = self.region_08_4.replace(SETTING, "").replace("response.py:60-65", "")
        self.assertNotEqual(mutated_08, self.region_08_4, "Bản-sao 08 §4 phải khác bản gốc (item tồn tại).")
        with self.assertRaises(AssertionError, msg="Guard KHÔNG bắt việc xoá item 08 §4 — false-green!"):
            _assert_traceback_hardening_invariant(
                self, mutated_08, self.region_adr_cons, self.region_10_62
            )

        # (d) RED-before #2 — xoá item traceback khỏi BẢN SAO ADR-004 Consequences → guard PHẢI bắt.
        mutated_adr = self.region_adr_cons.replace(SETTING, "").replace("response.py:60-65", "")
        self.assertNotEqual(mutated_adr, self.region_adr_cons, "Bản-sao ADR Consequences phải khác bản gốc.")
        with self.assertRaises(AssertionError, msg="Guard KHÔNG bắt việc xoá item ADR Consequences — false-green!"):
            _assert_traceback_hardening_invariant(
                self, self.region_08_4, mutated_adr, self.region_10_62
            )

        # (e) RED-before #3 — xoá reload/rate-limit note khỏi BẢN SAO 10 §6.2 → guard PHẢI bắt.
        mutated_10 = self.region_10_62.replace("--preload", "").replace("Retry-After", "")
        self.assertNotEqual(mutated_10, self.region_10_62, "Bản-sao 10 §6.2 phải khác bản gốc.")
        with self.assertRaises(AssertionError, msg="Guard KHÔNG bắt việc xoá note 10 §6.2 — false-green!"):
            _assert_traceback_hardening_invariant(
                self, self.region_08_4, self.region_adr_cons, mutated_10
            )

        # (f) control RE-confirm — text THẬT vẫn GREEN sau mutate (mutate KHÔNG đụng bản gốc).
        _assert_traceback_hardening_invariant(
            self, self.region_08_4, self.region_adr_cons, self.region_10_62
        )


if __name__ == "__main__":
    unittest.main()
