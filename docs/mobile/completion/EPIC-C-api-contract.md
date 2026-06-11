# EPIC-C — API Contract (codegen-ready)

| Mục | Giá trị |
|---|---|
| Bộ tài liệu | BE Completion — App mobile field-tech (AssetCore = backend-for-mobile) |
| EPIC ID | **C** (khoá — KHÔNG đổi) |
| Khối kiến trúc | Cross-cutting (IMM-00 master + IMM-08/09/11/12 nghiệp vụ) |
| WHO HTM stage | Installation/Operation/Maintenance (xem §2) |
| Owner | BA (`assetcore-doc`) — spec/yaml/test introspection-only |
| Trạng thái | In Progress |
| Cập nhật | 2026-06-11 |
| Phụ thuộc | Độc lập (doc/yaml/test). KHÔNG chờ cloud/site_config. Làm NGAY. |
| Đầu ra cho | EPIC-V (codegen verify), repo mobile native (Flutter/RN) |

## Tham chiếu nhanh
- Hợp đồng hiện hành: `../openapi/assetcore-mobile.openapi.yaml` (openapi 3.0.3, version 0.1.0-skeleton, 15 path)
- Guard: `../../../assetcore/tests/test_mobile_oas.py` (57 test, GREEN @baseline 2026-06-11)
- Hợp đồng prose: `../04-api-contract.md`
- ADR: `../ADR-MOBILE-001.md` (a–g + Self-Correction f/g)

---

## 1) Scope & Mục tiêu

**Scope:** Đóng hợp đồng OpenAPI cho lớp mobile-BE đến mức **openapi-generator chạy sạch** (Dart/Kotlin) cho **toàn bộ 6 flow MVP field-tech**. Lớp mobile = BỌC + TÁI DÙNG endpoint+capability có sẵn — EPIC-C **KHÔNG sửa** `api/*.py`/`services/*.py`, CHỈ viết `.md` + `.yaml` + `test_mobile_oas.py`.

**Mục tiêu cụ thể (DoD EPIC-C):**
1. **Fix P1 in-handler-error-on-HTTP-200** — chốt ADR: response `'200'` của create-path = `oneOf[<...CreatedEnvelope> | Error]` + `discriminator success` (đã áp create-trio; áp đồng-nhất khi typed path mới). In-handler 404/409/422 đi qua `_err` arrive **HTTP status-line 200 + Error body** → gom vào nhánh Error, KHÔNG keyed dưới HTTP-code response-key (dead-deser).
2. **Typed 4 STUB còn lại** — `resolveQrToken` / `getAssetScanInfo` / `getAsset` / `createPmWorkOrder` rời `#/components/responses/Stub` → response `data` schema + requestBody (createPm) grounded @source.
3. **List-element schema** — `WorkOrderListItem` (PM imm08 + CM imm09) + `IncidentListItem` (imm12) cho flow "phiếu của tôi", thay `items: { type: object }` generic.
4. **userinfo/whoami OIDC** — wire path OIDC userinfo (hiện CHỈ có scope `openid` ở securityScheme, KHÔNG path) → app hiện tên+role KTV sau login. requestBody `oneOf json+form` mọi RPC path còn thiếu.

**DoD đo được:** openapi-generator dry-run sạch (Dart/Kotlin), **0 dangling $ref**, mọi path MVP typed (0 path còn `responses/Stub`), `test_mobile_oas` xanh.

## 2) Actor

| Actor | Vai trò trong EPIC-C |
|---|---|
| **BA** (`assetcore-doc`) | Chủ hợp đồng yaml + 04-api-contract + ADR-MOBILE-001; viết schema/test introspection |
| **KTV (field-tech)** | Consumer cuối — client gen-ra từ hợp đồng này chạy 6 flow MVP |
| **Repo mobile native** (project KHÁC) | Nhận yaml + chạy openapi-generator → Dart/Kotlin client (EPIC-V handoff) |
| **QA** | Verify codegen THẬT (Dart/Kotlin) sau khi USER cấp `java`/`npx` — xem EPIC-V |
| **Frappe dispatcher / `handle()`** | Sinh ra 2 lớp error (pre-handler raw vs in-handler envelope) mà hợp đồng PHẢI phản ánh đúng |

## 3) Hiện trạng (file:line CHÍNH XÁC — grounded @source v15)

### 3.1 — 4 STUB path còn lại (200 → `responses/Stub`, guard `_STUB_PATHS`)

| operationId | YAML | Source handler | Cap gate | Error @source |
|---|---|---|---|---|
| `resolveQrToken` | yaml:1268–1279 | `api/imm00.py:325` `resolve_qr_token(token="")` | `rbac.require("asset.read")` imm00.py:351 | 404 `_err(_ERR_ASSET_NOT_FOUND)`; vendor-IDOR 403 `assert_vendor_can_access`; 429 `@rate_limit` imm00.py:326 |
| `getAssetScanInfo` | yaml:1280–1291 | `api/imm00.py:370` `get_asset_scan_info(token="",name="")` | `rbac.require("asset.read")` imm00.py:402 | 404 imm00.py:410; vendor-IDOR 403; 429 `@rate_limit` imm00.py:371 |
| `getAsset` | yaml:1292–1301 | `api/imm00.py:287` `get_asset(name)` | (whitelist, KHÔNG rbac.require — read-permission qua DocPerm/IDOR) | 404 imm00.py:290; vendor-IDOR 403 imm00.py:294–296 `assert_vendor_can_access` |
| `createPmWorkOrder` | yaml:1368–1377 | `api/imm08.py:91` `create_pm_work_order()` | `rbac.require("pm.create")` imm08.py:92 | untyped `_form_dict()` → `svc.create_adhoc_work_order` services/imm08.py:781 |

Guard `_STUB_PATHS` @ `tests/test_mobile_oas.py:152–157` (4 path) + comment STUB-A10-07 (0 requestBody + 200→Stub).

### 3.2 — Return shape grounded (cho §5 schema)

| Path | Return @source | Field |
|---|---|---|
| `resolveQrToken` | `_ok(_strip_qr_token(payload))` imm00.py:367; payload = `_svc_resolve_qr_token` (định danh tối thiểu) | `name, asset_code, ...` (strip `qr_token`) — định danh tối thiểu |
| `getAssetScanInfo` | `services/imm00.py:560` `build_asset_scan_info` return imm00.py:573–602 | `name, asset_code, asset_name, lifecycle_status, device_model_name, location_name, next_pm_date, next_calibration_date, recent_maintenance, pm_overdue, calibration_overdue, available_actions[]` |
| `available_actions[]` | `services/imm00.py:500` `_build_available_actions` → imm00.py:528–534 | `{key, label, route, enabled, reason}` (has_cap `rbac.can` ∩ `_lifecycle_allows`) |
| `pm_overdue`/`calibration_overdue` | server-flag `_is_pm_overdue`/`_is_calibration_overdue` (tz-safe STRICT `<`, exempt BLOCKED_FOR_WO) | bool |
| `getAsset` | `_ok(_strip_qr_token(doc.as_dict()))` imm00.py + enrich imm00.py:300–310 | AC Asset full + `device_model_name`/`responsible_technician_name`/`category_name`/`department_name`/`location_name`/`supplier_name` + `pm_overdue`/`calibration_overdue` |
| `createPmWorkOrder` | `services/imm08.py:835–840` | `{name, status, checklist_items_count}` (status init `PMStatus.OPEN` imm08.py:822); required `("asset_ref","pm_schedule","due_date")` imm08.py:782 |

### 3.3 — P1 in-handler-error-on-HTTP-200 — cơ chế XÁC MINH @source

Chuỗi: service `nthrow(MSG.X)` (`notify.py:61-87`) → `ServiceError(http_status=entry['http_status'])` (`errors.py:36-42`) → `handle()` (`api_handler.py:48-51`) bắt `ServiceError` → `_service_error_to_envelope` (`api_handler.py:54-69`) → `_err(..., http_status=e.http_status)` (`response.py:95-154`). Body chứa `code`+`http_status` (response.py:133-138) NHƯNG **HTTP status-line VẪN 200** (`handle()` return dict; `hooks.py:405` no `after_request` → status-line KHÔNG set cho in-handler error). ⇒ codegen route-by-status-line KHÔNG bao giờ thấy HTTP 404/409/422 cho in-handler error.

**Bằng chứng từng path:**

| Path | 403 shape | In-handler business error @source | Return @source |
|---|---|---|---|
| `report_incident` (imm12) | **DUAL** — guest 401 `_err(401)` imm12.py:92 = dead-code over HTTP (dispatcher-403 trip trước, 04 §5); cap-403 `_err(_MSG_FORBIDDEN,403)` imm12.py:96 = in-handler HTTP-200+Error | 422 BR-12-01 clinical_impact services/imm12.py:359 (`MSG.IMM12_CLINICAL_IMPACT_REQUIRED` http_status 422 messages.py:754); 404 asset∄ services/imm12.py:361 (`MSG.IMM12_ASSET_NOT_FOUND` 404 messages.py:747) | `{name,status,severity}` imm12.py:410 (status init Open imm12.py:373) |
| `create_repair_work_order` (imm09) | **SINGLE** — `rbac.require('repair.create')` api/imm09.py:40 → `PermissionError` HTTP-403 status-line THẬT | 404 asset∄ services/imm09.py:746 (`MSG.IMM09_ASSET_NOT_FOUND` 404 messages.py:716); 409 HAS_OPEN_WO services/imm09.py:753 (`MSG.IMM09_ASSET_HAS_OPEN_WO` 409 messages.py:667) | `{name,status=RepairStatus.OPEN,sla_target_hours}` imm09.py:771-772 |
| `create_calibration` (imm11) | **SINGLE** — `rbac.require('calibration.create')` api/imm11.py:95 → `PermissionError` HTTP-403 | 404 asset∄ services/imm11.py:999 (`MSG.IMM11_ASSET_NOT_FOUND` 404 messages.py:848); 409 ASSET_BLOCKED CAL-008 services/imm11.py:1002 (`MSG.IMM11_ASSET_BLOCKED` 409 messages.py:855) | `{name,status=Scheduled}` imm11.py:1013-1015 |

### 3.4 — ĐÃ ĐÓNG trong YAML hiện tại (KHÔNG build lại)

| Đã đóng | YAML |
|---|---|
| (a) ADR response-200-oneOf[Created,Error]+discriminator success cho 3 create path (report/repair/cal) | yaml:1337-1355, 1410-1428, 1473-1491 |
| (b) requestBody typed (oneOf json+form) + Created/Response schema cho 3 create | yaml:593-834, 1062-1112 |
| (c) WorkOrderListEnvelope(data.data[]) / IncidentListEnvelope(data.items[]) cho 3 list | yaml:426-469 |
| (d) userinfo/whoami: **KHÔNG có path nào** — chỉ scope `openid` ở securityScheme | yaml:150 |
| (e) form+json oneOf mọi create RPC | yaml:1061-1112 |

Guard `test_mobile_oas.py` xanh (57 test; 15 path; 0 dangling $ref; orphan ⊆ `_RESERVED_ORPHANS` 7 mục).

### 3.5 — List-element gap (CHƯA typed — element vẫn `type: object` generic)

`WorkOrderListEnvelope.data.data[].items` yaml:443-445 + `IncidentListEnvelope.data.items[].items` yaml:463-466 = `{ type: object }`. Field thật @source:

| List | Source | Field projection |
|---|---|---|
| PM WO (imm08) | `services/imm08.py:531-533` | `name, asset_ref, pm_type, wo_type, status, due_date, completion_date, assigned_to, supervisor, overall_result, is_late, source_pm_wo` + enrich `asset_name`/`location_name` (imm08.py:566-567) |
| Repair WO (imm09) | `services/imm09.py:675-681` | `name, asset_ref, asset_name, repair_type, priority, status, open_datetime, completion_datetime, mttr_hours, sla_breached, sla_target_hours, is_repeat_failure, assigned_to, root_cause_category, risk_class, parts_hold_hours, parts_hold_started` |
| Incident (imm12) | `services/imm12.py:750-756` | `name, asset, incident_type, severity, status, fault_code, reported_by, reported_at, description, linked_capa, linked_repair_wo, rca_required, rca_record, chronic_failure_flag, patient_affected, closed_date, assigned_to, acknowledged_at, resolved_at, response_breached, resolution_breached, response_due_at, resolution_due_at` + `_enrich_asset_names` + `_enrich_sla_breach` (imm12.py:761,763) |

> ⚠️ **PM (imm08) và CM (imm09) DÙNG CHUNG `WorkOrderListEnvelope` (`data.data[]`) nhưng projection KHÁC NHAU** (12 vs 17 field). Quyết định schema xem **C3**.

### 3.6 — Self-correction đang mở (carry từ factory-run3-apidocs) — đầu vào EPIC-C

| Mã | Triệu chứng | Đóng tại task |
|---|---|---|
| `discriminator-boolean` (P1) | `discriminator.propertyName: success` = **boolean** → OAS bắt buộc propertyName trỏ property kiểu **STRING** → codegen-illegal | **C1** |
| `additionalProperties-distinct` (P2) | 3 `*CreatedEnvelope` + `Error` open → 2 nhánh oneOf KHÔNG structurally-distinct khi generator DROP discriminator | **C1** |

---

## 4) Tasks

> Quy ước: owner [BA] viết yaml/md/test introspection · [QA] verify codegen THẬT. Tag [AUTO] = factory tự đóng (introspection PyYAML/test, KHÔNG cần cloud). [HARD-STOP USER] = cần USER (cloud/migrate/site_config/creds/`java`+`npx`). Acceptance = lệnh kiểm-được THẬT.

### C1 — ADR + fix P1 in-handler-error-on-HTTP-200 (discriminator codegen-legal)

**Mô tả:** Chốt ADR `response '200' = oneOf[<...CreatedEnvelope> | Error]` cho **mọi** create-path (create-trio đã có + typed-path mới C2). Sửa P1 `discriminator-boolean`: `discriminator.propertyName` PHẢI trỏ property kiểu STRING. Áp **Option A** (khuyến nghị, giữ máy-đọc): thêm field STRING phân-biệt `result_type` (enum `[created, error]`, const mỗi nhánh) làm `propertyName`, GIỮ `success` boolean cho FE logic. `mapping: { created: <...CreatedEnvelope>, error: '#/components/schemas/Error' }`. Set `additionalProperties: false` cho 3 `*CreatedEnvelope` + `FrappeRawError` (P2 `additionalProperties-distinct`) — 2 nhánh structurally-distinct khi generator drop discriminator. Cập nhật `04-api-contract.md §5c` + `ADR-MOBILE-001 (f)` Self-Correction.

- **Files:**
  - Modify: `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (3 create-path `'200'` discriminator yaml:1351/1424/1487 → `propertyName: result_type`; +property `result_type` const trong 3 `*CreatedEnvelope` + `Error`; `additionalProperties: false`)
  - Modify: `docs/mobile/04-api-contract.md` (§5c bảng discriminator + ghi chú STRING-propertyName)
  - Modify: `docs/mobile/ADR-MOBILE-001.md` (§(f) Self-Correction: boolean→string propertyName)
  - Modify: `assetcore/tests/test_mobile_oas.py` (guard `_assert_200_oneof_discriminator`: assert schema của `discriminator.propertyName` có `type == 'string'`; assert `mapping` keys khớp enum VALUE của property string đó)
- **Acceptance:** `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` — guard mới RED TRƯỚC fix, GREEN SAU (RED→GREEN gate). 0 dangling $ref (PyYAML introspection). `discriminator.propertyName` trỏ property `type: string` ở cả 3 create-path.
- **Owner:** [BA] · **Tag:** [AUTO] · **Dependencies:** không (độc lập). Là tiền-đề C2 (typed path mới dùng cùng pattern 200-oneOf).

### C2 — Typed 4 STUB (rời `responses/Stub`)

**Mô tả:** 4 path STUB → typed response `data` schema + requestBody (createPm). Schema grounded §3.2 — KHÔNG bịa field.
- `resolveQrToken` → `data` = `QrResolveResult` (định danh tối thiểu @source imm00.py:367; KHÔNG chứa `qr_token` — no-raw-token ADR-001 D4). Giữ 401/403/429.
- `getAssetScanInfo` → `data` = `AssetScanInfo` { `name, asset_code, asset_name, lifecycle_status, device_model_name, location_name, next_pm_date(str|null), next_calibration_date(str|null), recent_maintenance, pm_overdue(bool), calibration_overdue(bool), available_actions: [AvailableAction]` } + schema `AvailableAction` {`key, label, route, enabled(bool), reason`} (services/imm00.py:528-534). Giữ 401/403/429.
- `getAsset` → `data` = `AssetDetail` (AC Asset full + 6 enrich field §3.2 + `pm_overdue`/`calibration_overdue`). KHÔNG declare 429 (handler KHÔNG `@rate_limit`); declare 401/403/404 (404 imm00.py:290, vendor-IDOR 403 imm00.py:294). `additionalProperties: true` (AC Asset registry-doc nhiều field) — chỉ liệt kê field MVP cần + ghi chú open-shape.
- `createPmWorkOrder` → requestBody `CreatePmWorkOrderBody` (oneOf json+form, CÙNG $ref `CreatePmWorkOrderRequest`, required EXACT `[asset_ref, pm_schedule, due_date]` services/imm08.py:782; optional `pm_type, wo_type, assigned_to, supervisor, technician_notes` imm08.py:818-832) + `'200'` = oneOf[`CreatePmWorkOrderCreatedEnvelope` | Error] + discriminator `result_type` (C1 pattern); `data` = `CreatePmWorkOrderResponse` {`name, status, checklist_items_count`} (imm08.py:836-840). **403 = SINGLE-shape** `Forbidden` (`rbac.require('pm.create')` imm08.py:92 → `PermissionError` HTTP-403 THẬT — KHÔNG dual-shape; xác minh handler @source TRƯỚC khi chọn component, ADR-001 (f) caveat). In-handler business error (VALIDATION thiếu field imm08.py:783, IMM08_SCHEDULE_NOT_FOUND, BAD_STATE schedule) → gom nhánh Error 200-oneOf (KHÔNG keyed HTTP-code). status-set declare = `[200, 401, 403]` (pre-handler) + note in-handler errors trong nhánh Error.
- Gỡ 4 path khỏi `_STUB_PATHS` (`tests/test_mobile_oas.py:152-157`); cập nhật `04 §8.x` (STUB 4→0) + TC-MOB-OAS.
- **Files:**
  - Modify: `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (+schema `QrResolveResult, AssetScanInfo, AvailableAction, AssetDetail, CreatePmWorkOrderRequest, CreatePmWorkOrderResponse, CreatePmWorkOrderCreatedEnvelope` + requestBody `CreatePmWorkOrderBody`; wire 4 path)
  - Modify: `docs/mobile/04-api-contract.md` (§8 STUB-count 4→0; §8.x bồi 4 path; §9 ví dụ createPm form_dict)
  - Modify: `assetcore/tests/test_mobile_oas.py` (`_STUB_PATHS` rỗng; +TC `TestMobileQrResolveTyped`/`TestMobileScanInfoTyped`/`TestMobileAssetDetailTyped`/`TestMobileCreatePmBody`)
  - Modify: `docs/mobile/ADR-MOBILE-001.md` (§(f) +ghi chú createPm 403 single-shape — re-check 2 caveat trước rời STUB)
- **Acceptance:** `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` xanh; `_STUB_PATHS == set()`; 0 path còn trỏ `#/components/responses/Stub` (grep yaml = 0 trừ component definition); 0 dangling $ref.
- **Owner:** [BA] · **Tag:** [AUTO] · **Dependencies:** C1 (pattern 200-oneOf + discriminator string áp cho createPm). createPm là Self-Correction case (đọc handler trước — ADR-001 (f)).

### C3 — List-element schema (WorkOrderListItem / IncidentListItem)

**Mô tả:** Thay `items: { type: object }` generic trong 2 list envelope (§3.5) bằng schema typed cho flow "phiếu của tôi". Field grounded @source — KHÔNG bịa.
- `IncidentListItem` ← imm12 projection §3.5 (23 field + 2 enrich) → `IncidentListEnvelope.data.items[].items` (yaml:463-466).
- **Work Order:** PM (imm08, 12 field + 2 enrich) và CM (imm09, 17 field) KHÁC projection nhưng CÙNG `WorkOrderListEnvelope`. **QUYẾT ĐỊNH BA (Option A):** khai `WorkOrderListItem` = **union các field của cả 2 endpoint, tất cả optional trừ `name`** (name là PK chung 2 doctype). Ghi chú prose: 1 endpoint chỉ điền subset field của nó (PM-only: `pm_type/wo_type/due_date/completion_date/supervisor/overall_result/is_late/source_pm_wo/location_name`; CM-only: `repair_type/priority/open_datetime/completion_datetime/mttr_hours/sla_breached/sla_target_hours/is_repeat_failure/root_cause_category/risk_class/parts_hold_hours/parts_hold_started`; chung: `name/asset_ref/asset_name/status/assigned_to`). Lý do: 2 endpoint chia chung envelope (di sản service) → 1 element schema union là wire-truth cho codegen; tách 2 element schema = đổi envelope (đụng nhiều hơn, đẩy Phase-E). KNOWN-GAP normalize element = Phase-E (đụng service `.py`), ghi `04 §6.2` + `ADR-MOBILE-001 (g)`.
- **Files:**
  - Modify: `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (+schema `WorkOrderListItem, IncidentListItem`; `WorkOrderListEnvelope.data.data[].items.$ref` → WorkOrderListItem; `IncidentListEnvelope.data.items[].items.$ref` → IncidentListItem)
  - Modify: `docs/mobile/04-api-contract.md` (§6 bảng field list-item + ghi chú union WO PM/CM)
  - Modify: `assetcore/tests/test_mobile_oas.py` (+TC `TestMobileListItemTyped`: assert 2 envelope element-`items` là `$ref` (KHÔNG generic object) + assert field `name` required ở cả 2)
- **Acceptance:** `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` xanh; grep `items:\n *type: object` trong 2 list envelope = 0; 0 dangling $ref; `WorkOrderListItem`/`IncidentListItem` đều có `name` required.
- **Owner:** [BA] · **Tag:** [AUTO] · **Dependencies:** không (độc lập C1/C2). Cùng spec cho flow 5 "phiếu của tôi".

### C4 — userinfo/whoami OIDC + requestBody oneOf json+form (mọi RPC path)

**Mô tả:** Wire path OIDC userinfo (hiện CHỈ scope `openid` ở securityScheme yaml:150, KHÔNG path nào) → app hiện **tên + role KTV** sau login (đóng mảnh flow 1 "đăng nhập → hiển thị danh tính" field-tech MVP). Path = `GET /api/method/frappe.integrations.oauth2.openid_profile` (Frappe core OIDC userinfo endpoint — security `oauth2: [openid]`); response `data` = `OidcUserInfo` {`sub, name, given_name, family_name, email, roles[]`} (OIDC standard claims + Frappe `roles`). Thêm 1 ví dụ **sequence refresh-on-401** vào `04 §9` (401 → `getOAuthToken grant_type=refresh_token` → retry — đóng vòng OAuth2+refresh; cross-ref **EPIC-B B-refresh**). Rà soát mọi RPC path còn requestBody (sau C2): xác minh `oneOf application/json + application/x-www-form-urlencoded` (Frappe `/api/method` đọc `form_dict`) — codegen JSON-only client KHÔNG set header → field tới handler RỖNG (sai-âm-thầm).

- **Files:**
  - Modify: `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (+path `openid_profile` GET; +schema `OidcUserInfo`; verify form+json oneOf mọi create requestBody)
  - Modify: `docs/mobile/03-auth-oauth2.md` (§ userinfo/whoami + sequence refresh-on-401)
  - Modify: `docs/mobile/04-api-contract.md` (§9 ví dụ refresh-on-401)
  - Modify: `assetcore/tests/test_mobile_oas.py` (+TC `TestMobileUserInfo`: assert path `openid_profile` tồn tại + security `[openid]` + `OidcUserInfo.roles` array; +guard `_assert_rpc_requestbody_form_json` assert mọi requestBody RPC có CẢ 2 content-type)
- **Acceptance:** `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` xanh; path `openid_profile` + schema `OidcUserInfo` resolve (0 dangling $ref); mọi requestBody RPC khai oneOf json+form.
- **Owner:** [BA] · **Tag:** [AUTO] · **Dependencies:** không (độc lập). Cross-ref **EPIC-B** (refresh-token flow + token lifetime). userinfo phụ thuộc Frappe OIDC bật — go-live HTTP cần **EPIC-B B-preflight** (OAuth Client scope `openid`).

### C5 — DoD codegen-dry verify (gate sang EPIC-V)

**Mô tả:** Chốt DoD EPIC-C bằng dry-run codegen. STDLIB PyYAML introspection (no `java`/`npx`) = proxy bắt buộc; codegen THẬT (Dart/Kotlin) cần USER cấp toolchain → thuộc **EPIC-V**.
- **Files:** (không tạo file mới — verify gate)
- **Acceptance (introspection, [AUTO]):** `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` xanh; `python3 -c "import yaml; d=yaml.safe_load(open('docs/mobile/openapi/assetcore-mobile.openapi.yaml')); ..."` — assert (a) 0 path còn `responses/Stub`; (b) 0 dangling $ref (mọi `$ref` resolve trong document); (c) mọi path MVP có response `data` typed (`$ref`, KHÔNG generic object).
- **Acceptance (codegen THẬT, [HARD-STOP USER]):** sau khi USER cấp `java`+`npx`: `openapi-generator-cli generate -i docs/mobile/openapi/assetcore-mobile.openapi.yaml -g dart -o /tmp/gen-dart` + `-g kotlin` chạy sạch (exit 0, 0 ERROR, model deser route-by-`result_type` discriminator) — chuyển sang **EPIC-V V-codegen**.
- **Owner:** [BA] (introspection) → [QA] (codegen THẬT) · **Tag:** [AUTO] phần introspection / [HARD-STOP USER] phần codegen THẬT (cần `java`+`npx`) · **Dependencies:** C1 + C2 + C3 + C4. Gate cuối sang **EPIC-V**.

---

## 5) Data model / Schema (mới trong EPIC-C — KHÔNG thêm DocType/field DB)

> EPIC-C **KHÔNG** thêm DocType hay custom field. CHỈ thêm **OpenAPI component schema** (hợp đồng máy-đọc) — toàn bộ field grounded từ return-shape service/api có sẵn (§3.2/§3.5).

| Schema mới | Nguồn @source | Dùng tại |
|---|---|---|
| `QrResolveResult` | imm00.py:367 (`_strip_qr_token(payload)`, định danh tối thiểu) | C2 resolveQrToken |
| `AssetScanInfo` | services/imm00.py:573-602 | C2 getAssetScanInfo |
| `AvailableAction` {key,label,route,enabled,reason} | services/imm00.py:528-534 | C2 (nested trong AssetScanInfo) |
| `AssetDetail` (open-shape, field MVP + 6 enrich) | imm00.py get_asset return + enrich:300-310 | C2 getAsset |
| `CreatePmWorkOrderRequest` (required asset_ref/pm_schedule/due_date) | services/imm08.py:782 + optional:818-832 | C2 createPmWorkOrder requestBody |
| `CreatePmWorkOrderResponse` {name,status,checklist_items_count} | services/imm08.py:836-840 | C2 |
| `CreatePmWorkOrderCreatedEnvelope` {result_type,success,data} | pattern C1 | C2 |
| `WorkOrderListItem` (union PM imm08 + CM imm09, name required) | services/imm08.py:531-533 + imm09.py:675-681 | C3 list "phiếu của tôi" |
| `IncidentListItem` (23 field + 2 enrich) | services/imm12.py:750-756 | C3 |
| `OidcUserInfo` {sub,name,given_name,family_name,email,roles[]} | Frappe OIDC `openid_profile` standard claims | C4 |
| `result_type` (string enum [created,error]) — property thêm vào 3 `*CreatedEnvelope` + Error | quyết định C1 (codegen-legal discriminator) | C1 |

**Quy ước discriminator (C1, AUTHORITATIVE):** `discriminator.propertyName = result_type` (STRING, KHÔNG `success` boolean). `mapping: { created: <...CreatedEnvelope>, error: '#/components/schemas/Error' }`. Field `success` boolean GIỮ NGUYÊN cho FE logic (KHÔNG xoá). Created: `result_type: { enum: [created] }`; Error: `result_type: { enum: [error] }`.

## 6) Security & Audit (RBAC / token / CORS / NĐ98)

- **RBAC = 1 SSoT (capability/DocPerm):** Bearer → `set_user` → `rbac.py` capability (ADR-MOBILE-001 (b)). EPIC-C KHÔNG dựng hệ quyền thứ 2 — schema chỉ phản ánh cap-gate có sẵn: `asset.read` (3 QR/getAsset), `pm.create` (createPm). userinfo (C4) = scope `openid` (OIDC).
- **2 loại 403 (DONE-gate spec-contract):**
  - **dispatcher-403** (guest/no-token) = `PermissionError` raw @HTTP-line **403** (pre-handler, `is_whitelisted` `__init__.py:876`) → `FrappeRawError`. GIỮ status-line key 403.
  - **in-handler cap-403** (bearer hợp lệ, thiếu cap, vd `report_incident` imm12.py:96) = `_err(_MSG_FORBIDDEN,403)` qua `handle()` @HTTP-line **200** + Error envelope `{code:'FORBIDDEN',http_status:403}`. Client route theo HTTP status-line.
  - `createPmWorkOrder` (C2) = **SINGLE-shape** `Forbidden` (`rbac.require('pm.create')` imm08.py:92 → `PermissionError` HTTP-403 THẬT — KHÔNG dual-shape). 3 QR/getAsset = `asset.read` gate + vendor-IDOR 403 (`assert_vendor_can_access`).
- **invariant count==rows:** list "phiếu của tôi" (C3) — `Pagination.total` permission-aware (ADR-IMM00-LIST-SCOPE, `permission_query_conditions`). Schema khai `total: integer (permission-aware)` (yaml:401). Codegen client KHÔNG client-side-filter → tin `total` server.
- **No-raw-token (NĐ98 traceability + IDOR):** `QrResolveResult`/`AssetScanInfo`/`AssetDetail` (C2) KHÔNG chứa `qr_token` (strip qua `_strip_qr_token` imm00.py:367) — `qr_token` là khóa tra cứu MỜ nội bộ (ADR-001 D4 rule 9).
- **server-flag overdue (SSoT):** `pm_overdue`/`calibration_overdue` (C2 AssetScanInfo/AssetDetail) derive SERVER-SIDE (tz-safe, exempt BLOCKED_FOR_WO) — schema khai `boolean` (read-only flag). FE KHÔNG so ngày client-clock (memory: overdue_server_flag_ssot).
- **CORS:** native APK KHÔNG cần CORS (xem **EPIC-G** — CORS chỉ nếu UI web; ADR-MOBILE-004 cấm wildcard+credentials). EPIC-C không chạm CORS.
- **traceback leak:** `FrappeRawError` (dispatcher-403/401/429 body) chứa traceback nếu `allow_error_traceback` ON — hardening prod tắt cờ thuộc **EPIC-G**. EPIC-C chỉ khai schema `FrappeRawError` (closed-shape `additionalProperties:false` C1) để codegen route đúng.

## 7) Tham chiếu

| Loại | Tham chiếu |
|---|---|
| Chương mobile | `00-overview.md` · `03-auth-oauth2.md` (C4 userinfo+refresh) · `04-api-contract.md` (§4/§5/§5a/§5b/§5c/§6/§8/§9) · `05-personas-mvp.md` (field-tech MVP) · `08-security-compliance.md` (traceback gate) · `09-native-repo-guide.md` (EPIC-V handoff) · `13-be-completion-roadmap.md` |
| ADR | `ADR-MOBILE-001.md` (a–g: WIRE provider OAuth2 · RBAC 1 SSoT · BỌC endpoint · OpenAPI=hợp đồng · native no-cookie · (f) pre-handler passthrough + 2-loại-403 + form_dict + 200-oneOf-discriminator + additionalProperties-distinct · (g) 2-list-envelope) · `ADR-MOBILE-004.md` (CORS no-wildcard) |
| LL skill | `assetcore-be` LL-BE-42..49 (in-handler HTTP-200 + Error envelope ≠ raise→4xx; 2 loại 403; count==rows) · `assetcore-doc` DONE-gate spec-contract |
| EPIC khác | **B** (B-preflight OAuth Client scope `openid` cho C4; B-refresh cho C4 refresh-on-401) · **G** (CORS/traceback hardening §6) · **V** (V-codegen verify Dart/Kotlin THẬT — C5 [HARD-STOP USER]) · **D** (không phụ thuộc trực tiếp) |

## 8) Rủi ro

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Tái phát `discriminator-boolean` (propertyName trỏ property non-string) | P1 | C1 guard `_assert_200_oneof_discriminator` assert `type=='string'` + mapping khớp enum VALUE — RED→GREEN gate |
| `WorkOrderListItem` union (PM+CM chia envelope) → client nhận field null không-mong-đợi | P2 | C3 khai tất cả optional trừ `name`; prose ghi rõ PM-only/CM-only subset; KNOWN-GAP normalize = Phase-E (ADR-001 (g)) |
| `AssetDetail` open-shape (AC Asset nhiều field) → codegen sinh model thiếu field | P2 | C2 khai `additionalProperties: true` + liệt kê field MVP cần; ghi chú registry-doc open-shape |
| Frappe `form_dict` — codegen JSON-only client gửi field tới handler RỖNG (sai-âm-thầm) | P1 | C2/C4 requestBody oneOf `json + form-urlencoded` (CÙNG $ref); C4 guard `_assert_rpc_requestbody_form_json` |
| createPm chọn NHẦM 403 dual-shape (copy mù pattern report_incident) | P1 | C2 đọc handler @source TRƯỚC (imm08.py:92 `rbac.require` = SINGLE-shape `Forbidden`); ADR-001 (f) caveat |
| in-handler 404/409/422 keyed dưới HTTP-code response-key = dead-deser | P1 | C1/C2 gom vào nhánh Error của 200-oneOf; pre-handler 401/403/429 GIỮ status-line key (§3.3) |
| Codegen THẬT (Dart/Kotlin) chưa chạy được — thiếu `java`/`npx` | P2 | C5 introspection PyYAML = proxy [AUTO]; codegen THẬT = [HARD-STOP USER] → EPIC-V |
| userinfo path Frappe OIDC chưa bật trên cloud (scope `openid` chưa cấp ở OAuth Client) | P2 | C4 chỉ khai hợp đồng; go-live HTTP phụ thuộc EPIC-B B-preflight (cấp scope `openid`) — [HARD-STOP USER] |
