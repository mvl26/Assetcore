# EPIC-C — API Contract (codegen-ready)

| Mục | Giá trị |
|---|---|
| Bộ tài liệu | BE Completion — App mobile field-tech (AssetCore = backend-for-mobile) |
| EPIC ID | **C** (khoá — KHÔNG đổi) |
| Khối kiến trúc | Cross-cutting (IMM-00 master + IMM-08/09/11/12 nghiệp vụ) |
| WHO HTM stage | Installation/Operation/Maintenance (xem §2) |
| Owner | BA (`assetcore-doc`) — spec/yaml/test introspection-only |
| Trạng thái | **EPIC-C AUTO-PART DONE → gate EPIC-V** (codegen Dart/Kotlin THẬT = HARD-STOP USER toolchain → V-U1/V-U2) |
| Cập nhật | 2026-06-11 |
| Phụ thuộc | Độc lập (doc/yaml/test). KHÔNG chờ cloud/site_config. Làm NGAY. |
| Đầu ra cho | EPIC-V (codegen verify), repo mobile native (Flutter/RN) |

## Tham chiếu nhanh
- Hợp đồng hiện hành: `../openapi/assetcore-mobile.openapi.yaml` (openapi 3.0.3, 16 path, 0 `discriminator:` key — Decision-B closed-schema)
- Guard: `../../../assetcore/tests/test_mobile_oas.py` (**108 test** count HIỆN HÀNH, GREEN re-run @source Vòng 11 2026-06-11; guard-suite 6-module tổng **196 OK**)
- Hợp đồng prose: `../04-api-contract.md`
- ADR: `../ADR-MOBILE-001.md` (a–g + Self-Correction f/g)

---

## 1) Scope & Mục tiêu

**Scope:** Đóng hợp đồng OpenAPI cho lớp mobile-BE đến mức **openapi-generator chạy sạch** (Dart/Kotlin) cho **toàn bộ 6 flow MVP field-tech**. Lớp mobile = BỌC + TÁI DÙNG endpoint+capability có sẵn — EPIC-C **KHÔNG sửa** `api/*.py`/`services/*.py`, CHỈ viết `.md` + `.yaml` + `test_mobile_oas.py`.

**Mục tiêu cụ thể (DoD EPIC-C):**
1. **Fix P1 in-handler-error-on-HTTP-200** — chốt ADR: response `'200'` của create-path = `oneOf[<...CreatedEnvelope> | Error]` (Decision-B closed-schema, KHÔNG discriminator boolean). In-handler 404/409/422 đi qua `_err` arrive **HTTP status-line 200 + Error body** → gom vào nhánh Error, KHÔNG keyed dưới HTTP-code response-key (dead-deser). **✅ C6 (2026-06-11) mở rộng SANG 3 GET read** (`resolveQrToken`/`getAssetScanInfo`/`getAsset`): 200 = `oneOf[<ReadEnvelope> | Error]` — đóng read-path analog (in-handler 404 + vendor-IDOR-403 cũng arrive HTTP-200+Error).
2. **Typed 4 STUB còn lại** — `resolveQrToken` / `getAssetScanInfo` / `getAsset` / `createPmWorkOrder` rời `#/components/responses/Stub` → response `data` schema + requestBody (createPm) grounded @source.
3. **List-element schema** — ✅ **C3-split DONE (2026-06-11):** 2 item-schema field-disjoint `PmWorkOrderListItem` (imm08) + `RepairWorkOrderListItem` (imm09) + `IncidentListItem` (imm12) cho flow "phiếu của tôi", thay `items: { type: object }` generic. KHÔNG còn 1 UNION schema (đóng KNOWN-GAP "KHÔNG ép chung").
4. **userinfo/whoami OIDC** — ✅ **C4 DONE (2026-06-11):** path `GET openid_profile` (`getUserInfo`, security `[openid]`) + schema `OidcUserInfo` RAW passthrough (8 claim grounded) → app hiện tên+role KTV sau login. requestBody `oneOf json+form` đủ 4 RPC create (vá `createPm`).

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

### 3.1 — Path landscape: 4 scan/createPm ✅ typed (C2) · STUB còn lại = 2 device-token (BE-PENDING EPIC-D)

> **Reconciled F-C4 (2026-06-11):** heading cũ "4 STUB path còn lại" + dòng-guard `tests/test_mobile_oas.py:152–157` đã STALE — số dòng line-drift, 4 path scan/createPm ĐÃ RỜI STUB (typed C2). Source-truth = **SYMBOL `_STUB_PATHS = set(_DEVICE_TOKEN_FROZEN)`** (re-verify @source theo symbol, KHÔNG số-dòng-tuyệt-đối). Bảng dưới = 4 path scan/createPm ĐÃ typed; STUB thật còn lại = 2 device-token (§3.4 / `_DEVICE_TOKEN_FROZEN`).

| operationId | YAML | Source handler | Cap gate | Error @source | Trạng thái |
|---|---|---|---|---|---|
| `resolveQrToken` | yaml:1268–1279 | `api/imm00.py:325` `resolve_qr_token(token="")` | `rbac.require("asset.read")` imm00.py:351 | 404 `_err(_ERR_ASSET_NOT_FOUND)`; vendor-IDOR 403 `assert_vendor_can_access`; 429 `@rate_limit` imm00.py:326 | ✅ typed C2 (`QrResolveEnvelope`) |
| `getAssetScanInfo` | yaml:1280–1291 | `api/imm00.py:370` `get_asset_scan_info(token="",name="")` | `rbac.require("asset.read")` imm00.py:402 | 404 imm00.py:410; vendor-IDOR 403; 429 `@rate_limit` imm00.py:371 | ✅ typed C2 (`AssetScanInfoEnvelope`) |
| `getAsset` | yaml:1292–1301 | `api/imm00.py:287` `get_asset(name)` | (whitelist, KHÔNG rbac.require — read-permission qua DocPerm/IDOR) | 404 imm00.py:290; vendor-IDOR 403 imm00.py:294–296 `assert_vendor_can_access` | ✅ typed C2+C6 (`AssetDetailEnvelope`) |
| `createPmWorkOrder` | yaml:1368–1377 | `api/imm08.py:91` `create_pm_work_order()` | `rbac.require("pm.create")` imm08.py:92 | `_form_dict()` → `svc.create_adhoc_work_order` services/imm08.py:781; required chốt BA @`:782` | ✅ typed C2 (`CreatePmWorkOrderRequest`, dual json+form C4) |

Guard `_STUB_PATHS` @ SYMBOL `_STUB_PATHS = set(_DEVICE_TOKEN_FROZEN)` (`tests/test_mobile_oas.py`, re-verify theo symbol — số-dòng cũ chết do drift; symbol thật @~L184) + comment STUB-A10-07. **Set sau R4/C2 = 2 device-token** (register/unregister — handler chưa impl, [ROADMAP] EPIC-D). Guard assert `_STUB_PATHS == set(_DEVICE_TOKEN_FROZEN)` (`test_mob_oas_20`).

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
| (a) ADR response-200-oneOf[Created,Error] closed-schema route-by-VALUE `body.success` (Decision-B, KHÔNG discriminator) cho 3 create path (report/repair/cal) | yaml ReportIncident/CreateRepairWorkOrder/CreateCalibration `'200'` + `*CreatedEnvelope` |
| (b) requestBody typed (oneOf json+form) + Created/Response schema cho 3 create | yaml:593-834, 1062-1112 |
| (c) WorkOrderListEnvelope(data.data[]) / IncidentListEnvelope(data.items[]) cho 3 list | yaml:426-469 |
| (d) userinfo/whoami: ✅ **C4 DONE** — path `GET openid_profile` (operationId `getUserInfo`, security `[openid]`) + schema `OidcUserInfo` RAW passthrough | yaml path `openid_profile` + `components/schemas/OidcUserInfo` |
| (e) form+json oneOf mọi create RPC — ✅ C4 mở rộng `createPm` (C2 lỡ chỉ khai form-only) → nay dual json+form như 3 create-triad | yaml `createPm` requestBody (json+form) |

> ✅ **CORRECTION C4 (re-verify @source `frappe/oauth.py:530-555` — `get_userinfo`):** schema `OidcUserInfo` GROUNDED **8 claim** (KHÔNG bịa): `sub` (string|**null** — db.get_value `:531-535`), `name`, `given_name`, `family_name`, `email`, **`picture`** (string|**null** — `user_image` resolve `:529-548`), `roles` (array\<string\> `:541`), **`iss`** (server URL `:542`). ⚠️ Đề mục C4 ban đầu liệt kê 6 field (`sub,name,given_name,family_name,email,roles`) — **THIẾU `picture` + `iss`** và KHÔNG nêu `sub` nullable. Đã bổ sung đủ + đánh dấu `sub`/`picture` `nullable:true` (Decision-B closed-schema, `additionalProperties:false`, KHÔNG discriminator). userinfo trả **RAW** (`oauth2.py:172-174` set `frappe.local.response = body`) ⇒ KHÔNG envelope AssetCore (KHÁC create path — chúng dùng oneOf[Created|Error]).

Guard `test_mobile_oas.py` xanh (**75 test @landing C4**; count HIỆN HÀNH @source Vòng 11 2026-06-11 = **108 OK**; **16 path** — C4 +`openid_profile`; 0 dangling $ref; orphan ⊆ `_RESERVED_ORPHANS`; `OidcUserInfo` $ref'd ngay → KHÔNG orphan).

### 3.5 — List-element gap (✅ RESOLVED bởi C3-split — 2 element typed `$ref` field-disjoint)

> ✅ **ĐÓNG bởi C3-split (2026-06-11):** `PmWorkOrderListEnvelope.data.data[].items` → `$ref PmWorkOrderListItem`; `RepairWorkOrderListEnvelope.data.data[].items` → `$ref RepairWorkOrderListItem`; `IncidentListEnvelope.data.items[].items` → `$ref IncidentListItem`. KHÔNG còn `{type:object}` generic, KHÔNG còn 1 UNION schema trộn PM+CM. **KNOWN-GAP "KHÔNG ép chung" ĐÓNG** (PM ≠ CM field-set → 2 item-schema RIÊNG; không còn defer Phase-E). **Re-verify @source (D4):** `parts_hold_started` bị imm09 `r.pop("parts_hold_started", None)` trước khi trả ⇒ KHÔNG ra wire → KHÔNG khai trong `RepairWorkOrderListItem`. imm09 còn enrich `assigned_to_name`/`department_name`/`location_name` + derived `is_sla_breached`/`sla_paused`; imm12 enrich `reporter_name`/`assigned_to_name` + derived `is_response_breached`/`is_resolution_breached`. Chi tiết: §C3-split + [04 §6.3](../04-api-contract.md).

Field thật @source (snapshot khảo sát — số dòng tham khảo, re-verified theo symbol ở C3):

| List | Source | Field projection |
|---|---|---|
| PM WO (imm08) | `services/imm08.py:531-533` | `name, asset_ref, pm_type, wo_type, status, due_date, completion_date, assigned_to, supervisor, overall_result, is_late, source_pm_wo` + enrich `asset_name`/`location_name` (imm08.py:566-567) |
| Repair WO (imm09) | `services/imm09.py:675-681` | `name, asset_ref, asset_name, repair_type, priority, status, open_datetime, completion_datetime, mttr_hours, sla_breached, sla_target_hours, is_repeat_failure, assigned_to, root_cause_category, risk_class, parts_hold_hours, parts_hold_started` |
| Incident (imm12) | `services/imm12.py:750-756` | `name, asset, incident_type, severity, status, fault_code, reported_by, reported_at, description, linked_capa, linked_repair_wo, rca_required, rca_record, chronic_failure_flag, patient_affected, closed_date, assigned_to, acknowledged_at, resolved_at, response_breached, resolution_breached, response_due_at, resolution_due_at` + `_enrich_asset_names` + `_enrich_sla_breach` (imm12.py:761,763) |

> ✅ **PM (imm08) và CM (imm09) projection KHÁC NHAU** (16 vs 21 field, field-disjoint ở phần riêng) ⇒ **C3-split tách 2 envelope + 2 item-schema RIÊNG** (rows-key `data` giống nhau nhưng element khác). Quyết định schema xem **C3-split**.

### 3.6 — Self-correction đang mở (carry từ factory-run3-apidocs) — đầu vào EPIC-C

| Mã | Triệu chứng | Đóng tại task |
|---|---|---|
| `discriminator-boolean` (P1) | `discriminator.propertyName: success` = **boolean** → OAS bắt buộc propertyName trỏ property kiểu **STRING** → codegen-illegal | **C1** |
| `additionalProperties-distinct` (P2) | 3 `*CreatedEnvelope` + `Error` open → 2 nhánh oneOf KHÔNG structurally-distinct khi generator DROP discriminator | **C1** |
| `read-path-error-on-200` (P1) | 3 GET read (resolveQrToken/getAssetScanInfo/getAsset) 200 = single `$ref <ReadEnvelope>` → in-handler **404 + vendor-IDOR-403** arrive HTTP-200+Error (`_err`) = **dead-deser** (KHÔNG nhánh Error). Read-path analog của create-path P1 — bỏ sót vì read KHÔNG có requestBody. | **C6** |

> **§3.6 — Self-correction extended to reads (C6, 2026-06-11):** quyết-định Decision-B (closed-schema oneOf `[<Envelope>, Error]` KHÔNG discriminator) ban đầu áp create-path (C1) — **C6 mở rộng SANG 3 GET read**. Root-fact GIỐNG create: in-handler error đi qua `_err` → HTTP-200 + Error body (verified @source `api/imm00.py`). Xem C6 dưới + ADR-MOBILE-001 (f) SELF-CORRECTION C6.

---

## 4) Tasks

> Quy ước: owner [BA] viết yaml/md/test introspection · [QA] verify codegen THẬT. Tag [AUTO] = factory tự đóng (introspection PyYAML/test, KHÔNG cần cloud). [HARD-STOP USER] = cần USER (cloud/migrate/site_config/creds/`java`+`npx`). Acceptance = lệnh kiểm-được THẬT.

### C1 — ADR + fix P1 in-handler-error-on-HTTP-200 (route-by-VALUE closed-schema, Decision-B) ✅ DONE · residual prose CLEARED (Vòng 8 C1-residual) · continuation 18f-guard (Vòng 9 C1-close)

> ⚠️ **SUPERSEDED bởi Decision-B (xem §5 CORRECTION + ADR-MOBILE-001 (f)):** mô tả Option A `result_type` STRING dưới đây là **bản nháp C1** — đã BỎ. Triển khai THẬT = **Decision-B**: BỎ discriminator hoàn toàn + closed-schema (`additionalProperties:false`) + disjoint required-set. yaml có 0 `discriminator:` key. Giữ block dưới làm ghi-chép lịch sử quyết định.
>
> ✅ **C1-residual CLOSED (Vòng 8, 2026-06-11):** đồng-bộ ngôn-ngữ Decision-B — gỡ **prose-residue** còn sót trong SSoT yaml (7 description/comment từng nói "ROUTE THEO body.success discriminator" / "+ discriminator success" như cơ-chế hiện-hữu) + docset (ADR (f) R1 bullet, roadmap §3.2/§3.5, 04 §8.2 note). Mọi mô tả nay = **route-by-VALUE `body.success`** (Created.success.enum=[true] vs Error.success.enum=[false]) qua **closed-schema disjoint required-set**; KHÔNG nhắc `discriminator` như đường route hiện hành (chỉ NEGATED / `[SUPERSEDED]`). Guard chống tái-phát: `TestMobileProseResidueDiscriminator` (`test_mob_oas_26a/b/c`, RED-trước-fix GREEN-sau). yaml VẪN 0 `discriminator:` key (KHÔNG thêm key — chỉ sửa prose); `git diff --stat` api/services `.py` TRỐNG (KHÔNG reload). `test_mobile_oas` = **103 OK @landing Vòng 8** (98 + 2 C3-split/F-C2 carry + 3 prose-guard mới).
>
> ✅ **C1-close — continuation 18f-guard (Vòng 9, 2026-06-11):** mở rộng prose-residue closure bằng guard STRUCTURAL `TestMobileOas18fNoDiscriminatorRouteProse` (**3 TC**: `test_mob_oas_18f_create_paths_no_discriminator_route_prose` + `test_mob_oas_18f_read_paths_no_discriminator_route_prose` + `test_mob_oas_18f_detector_red_before_on_injected_mechanism_prose`). Khác với `26a` (raw-text), 18f **parse spec đã-load** rồi quét `summary` / `operation.description` / `responses.200.description` trên 4 create + 3 read 200-oneOf path để bắt prose mô tả `discriminator` NHƯ cơ-chế route hiện-hữu (cho phép clause NEGATED / `[SUPERSEDED]`). Bổ-trợ 26a, Decision-B intact, yaml VẪN 0 `discriminator:` key. Doc/test-only, `git diff --stat` api/services `.py`/yaml-schema TRỐNG (KHÔNG reload). `test_mobile_oas` = **108 OK** (count HIỆN HÀNH @source Vòng 11 = 103 @landing Vòng 8 + 3 TC 18f → 106 @landing Vòng 9 → 107 @baseline Vòng 11 → 108 @F-C3 Vòng 11 meta-guard; guard-suite 6-module tổng **196 OK**).

**Mô tả (NHÁP C1 — SUPERSEDED):** Chốt ADR `response '200' = oneOf[<...CreatedEnvelope> | Error]` cho **mọi** create-path (create-trio đã có + typed-path mới C2). Sửa P1 `discriminator-boolean`: `discriminator.propertyName` PHẢI trỏ property kiểu STRING. ~~Áp **Option A** (thêm field STRING `result_type` enum `[created, error]` làm `propertyName`)~~ → **ĐÃ ĐỔI sang Decision-B (bỏ discriminator)**. Set `additionalProperties: false` cho `*CreatedEnvelope` + `Error` + `FrappeRawError` — 2 nhánh structurally-distinct (closed-schema). Cập nhật `04-api-contract.md §5c` + `ADR-MOBILE-001 (f)` Self-Correction.

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
- `createPmWorkOrder` → requestBody `CreatePmWorkOrderBody` (oneOf json+form, CÙNG $ref `CreatePmWorkOrderRequest`, required EXACT `[asset_ref, pm_schedule, due_date]` services/imm08.py:782; optional `pm_type, wo_type, assigned_to, supervisor, technician_notes` imm08.py:818-832) + `'200'` = oneOf[`CreatePmWorkOrderCreatedEnvelope` | Error] **closed-schema route-by-VALUE `body.success`** (Decision-B, KHÔNG discriminator — bản nháp "discriminator `result_type`" ĐÃ BỎ); `data` = `CreatePmWorkOrderResponse` {`name, status, checklist_items_count`} (imm08.py:836-840). **403 = SINGLE-shape** `Forbidden` (`rbac.require('pm.create')` imm08.py:92 → `PermissionError` HTTP-403 THẬT — KHÔNG dual-shape; xác minh handler @source TRƯỚC khi chọn component, ADR-001 (f) caveat). In-handler business error (VALIDATION thiếu field imm08.py:783, IMM08_SCHEDULE_NOT_FOUND, BAD_STATE schedule) → gom nhánh Error 200-oneOf (KHÔNG keyed HTTP-code). status-set declare = `[200, 401, 403]` (pre-handler) + note in-handler errors trong nhánh Error.
- Gỡ 4 path khỏi `_STUB_PATHS` (`tests/test_mobile_oas.py:152-157`); cập nhật `04 §8.x` (STUB 4→0) + TC-MOB-OAS.
- **Files:**
  - Modify: `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (+schema `QrResolveResult, AssetScanInfo, AvailableAction, AssetDetail, CreatePmWorkOrderRequest, CreatePmWorkOrderResponse, CreatePmWorkOrderCreatedEnvelope` + requestBody `CreatePmWorkOrderBody`; wire 4 path)
  - Modify: `docs/mobile/04-api-contract.md` (§8 STUB-count 4→0; §8.x bồi 4 path; §9 ví dụ createPm form_dict)
  - Modify: `assetcore/tests/test_mobile_oas.py` (`_STUB_PATHS` rỗng; +TC `TestMobileQrResolveTyped`/`TestMobileScanInfoTyped`/`TestMobileAssetDetailTyped`/`TestMobileCreatePmBody`)
  - Modify: `docs/mobile/ADR-MOBILE-001.md` (§(f) +ghi chú createPm 403 single-shape — re-check 2 caveat trước rời STUB)
- **Acceptance:** `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` xanh; `_STUB_PATHS == set()`; 0 path còn trỏ `#/components/responses/Stub` (grep yaml = 0 trừ component definition); 0 dangling $ref.
- **Owner:** [BA] · **Tag:** [AUTO] · **Dependencies:** C1 (pattern 200-oneOf closed-schema route-by-VALUE `body.success`, Decision-B KHÔNG discriminator, áp cho createPm). createPm là Self-Correction case (đọc handler trước — ADR-001 (f)).

### C3-split — 2 element-schema field-disjoint (Pm/RepairWorkOrderListItem) — ✅ DONE (2026-06-11)

**Trạng thái:** ✅ **DONE+GREEN** (RED→GREEN gate qua `TestMobileListItemTyped` 8 TC; `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` = **98 OK @landing C3-split** · count HIỆN HÀNH @source Vòng 11 = **108 OK**). 3 element-schema THẬT (`PmWorkOrderListItem` + `RepairWorkOrderListItem` + `IncidentListItem`), wire `$ref` per-endpoint, 0 generic `{type:object}`, 0 dangling, OAS 3.0.3 codegen-able. **KNOWN-GAP "KHÔNG ép chung" ĐÓNG** (không còn defer Phase-E). UNCOMMITTED (chờ USER).

**Lịch sử:** C3 ban đầu (2026-06-11) khai 1 UNION `WorkOrderListItem` (PM imm08 ∪ CM imm09) chia chung `WorkOrderListEnvelope` + để KNOWN-GAP "tách 2 element-schema per-endpoint = Phase-E". **C3-split (round này)** đóng gap đó: PM ≠ CM field-set ⇒ tách thành 2 item-schema RIÊNG, mỗi endpoint trỏ item của nó.

**Mô tả:** Thay 1 UNION schema bằng 2 element-schema FIELD-DISJOINT cho flow "phiếu của tôi". Field grounded @source — KHÔNG bịa.
- `IncidentListItem` ← imm12 `list_incidents` projection (23 repo-field + enrich `asset_name/reporter_name/assigned_to_name` + derived `is_response_breached/is_resolution_breached`) → `IncidentListEnvelope.data.items[].items`. Dùng key `asset` (KHÔNG `asset_ref`). **KHÔNG đổi round này.**
- **`PmWorkOrderListItem`** ← CHỈ field `imm08.list_work_orders` (16 field: repo `name/asset_ref/pm_type/wo_type/status/due_date/completion_date/assigned_to/supervisor/overall_result/is_late/source_pm_wo` + enrich `asset_name/location_name/assigned_to_name/supervisor_name`) → `PmWorkOrderListEnvelope.data.data[].items`.
- **`RepairWorkOrderListItem`** ← CHỈ field `imm09.list_work_orders` (21 field: repo `name/asset_ref/asset_name/repair_type/priority/status/open_datetime/completion_datetime/mttr_hours/sla_breached/sla_target_hours/is_repeat_failure/assigned_to/root_cause_category/risk_class/parts_hold_hours` + enrich `department_name/location_name/assigned_to_name` + derived `is_sla_breached/sla_paused`) → `RepairWorkOrderListEnvelope.data.data[].items`. `parts_hold_started` bị `r.pop()` → KHÔNG khai.
- **QUYẾT ĐỊNH BA (giữ Option A closed-schema = Decision-B):** mỗi schema `required:[name]` DUY NHẤT + `additionalProperties:false` + KHÔNG discriminator boolean. **Field-set 2 schema DISJOINT** ở phần RIÊNG (PM-only ∩ CM-only = ∅) — codegen sinh 2 model tường minh, integrator KHÔNG còn đoán field nào thuộc loại nào. rows-key `data` GIỮ nguyên cả 2 (KHÔNG sửa service `.py` → KHÔNG reload gunicorn).
- **Files (đã chạm — KHÔNG đụng api/services `.py`):**
  - `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (−schema UNION `WorkOrderListItem`+`WorkOrderListEnvelope`+response `WorkOrderList`; +`PmWorkOrderListItem`/`RepairWorkOrderListItem` + `Pm`/`RepairWorkOrderListEnvelope` + response `Pm`/`RepairWorkOrderList`; 2 list path trỏ response RIÊNG)
  - `docs/mobile/04-api-contract.md` (§6.3 bảng field list-item — 2 schema per-endpoint, gỡ nhãn union)
  - `docs/mobile/ADR-MOBILE-001.md` ((g) — KNOWN-GAP normalize-element ĐÓNG, không còn defer Phase-E)
  - `docs/mobile/13-be-completion-roadmap.md` (§3.3 + §10)
  - `assetcore/tests/test_mobile_oas.py` (class `TestMobileListItemTyped` refactor 6→8 TC: +`21b2` path-trỏ-response-riêng + `21g` disjoint-field assert; `_PM_WO_FIELDS`/`_REPAIR_WO_FIELDS` grounded @source; anti-regress UNION cũ KHÔNG còn)
- **Acceptance (đã verify):** module test xanh (**98 OK @landing C3-split**; count HIỆN HÀNH @source Vòng 11 = **108 OK**); grep `WorkOrderListItem:` UNION cũ = 0; `PmWorkOrderListItem`/`RepairWorkOrderListItem`/`IncidentListItem` đều `required:[name]` + `additionalProperties:false`; PM-only ∩ CM-only = ∅; 0 dangling $ref; `discriminator` real-key = 0; orphan ⊆ `_RESERVED_ORPHANS`; `git diff --stat` cho api/services `.py` TRỐNG → KHÔNG reload.
- **Owner:** [BA] · **Tag:** [AUTO] · **Dependencies:** C3 ban đầu (refine). Cùng spec cho flow 5 "phiếu của tôi".

### C4 — userinfo/whoami OIDC + requestBody oneOf json+form (mọi RPC path) — ✅ DONE (2026-06-11)

**Trạng thái:** ✅ **DONE+GREEN** (RED→GREEN gate qua `TestMobileUserInfo` 9 TC `test_mob_oas_22a..i`; `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` = **75 OK @landing C4** — 66 @landing C3 +9; count HIỆN HÀNH @source Vòng 11 = **108 OK**). Path `openid_profile` + schema `OidcUserInfo` (8 claim grounded) + dual json+form mọi RPC create (gồm `createPm` đã vá). 0 dangling $ref; OAS 3.0.3 codegen-able. UNCOMMITTED (chờ USER).

**Mô tả:** Wire path OIDC userinfo (trước CHỈ scope `openid` ở securityScheme, KHÔNG path nào) → app hiện **tên + role KTV** sau login (đóng mảnh flow 1 "đăng nhập → hiển thị danh tính" field-tech MVP). Path = `GET /api/method/frappe.integrations.oauth2.openid_profile` (Frappe core OIDC userinfo endpoint — `operationId getUserInfo`, security `OAuth2: [openid]`); response 200 = `OidcUserInfo` **RAW passthrough** (KHÔNG envelope — `oauth2.py:172-174`). **CORRECTION @source `oauth.py:530-555`:** 8 claim `{sub(string|null), name, given_name, family_name, email, picture(string|null), roles[], iss}` — đề mục ban đầu THIẾU `picture`+`iss` + chưa nêu `sub` nullable (xem §3.4 CORRECTION). Thêm ví dụ **sequence refresh-on-401** vào `04 §9d` + `03 §2.6` (401 → `getOAuthToken grant_type=refresh_token` → retry — đóng vòng OAuth2+refresh). Rà RPC requestBody (sau C2): guard `_assert_rpc_requestbody_form_json` xác minh **4** create RPC (3 create-triad + `createPm`) khai `oneOf application/json + application/x-www-form-urlencoded` (Frappe `form_dict`) — **PHÁT HIỆN `createPm` (C2) lỡ chỉ khai form-only → đã vá dual json+form**.

- **Files (DONE):**
  - ✅ `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (+path `openid_profile` GET `getUserInfo` security `[openid]` 200→`OidcUserInfo`; +schema `OidcUserInfo` 8 claim; vá `createPm` requestBody → dual json+form)
  - ✅ `docs/mobile/03-auth-oauth2.md` (§1.2 step (e2) + §2.6 userinfo/whoami: endpoint, claims grounded, bearer-required + sequence refresh-on-401)
  - ✅ `docs/mobile/04-api-contract.md` (§8.1 +`getUserInfo` row [16/16] · §9d ví dụ userinfo + refresh-on-401 + passthrough raw cross-ref §5b passthrough OAuth)
  - ✅ `assetcore/tests/test_mobile_oas.py` (+class `TestMobileUserInfo` 9 TC `test_mob_oas_22a..i`: path/opId/security/200-ref/8-claim-grounded/roles-array/nullable/closed-schema/no-dangling + guard `_assert_rpc_requestbody_form_json` 4 RPC; +`getUserInfo` vào `_EXPECTED`; count 15→16; `_AUTH_PATHS` +openid_profile loại khỏi 401/403 symmetry)
  - ✅ `docs/mobile/ADR-MOBILE-001.md` (+bullet userinfo OIDC passthrough raw + 2-content-type RPC guard rationale)
  - ✅ `docs/mobile/13-be-completion-roadmap.md` (§3.4/§3.5 + §10 — gỡ 'userinfo/whoami chưa là path')
- **Acceptance:** `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` xanh; path `openid_profile` + schema `OidcUserInfo` resolve (0 dangling $ref); mọi requestBody RPC khai oneOf json+form.
- **Owner:** [BA] · **Tag:** [AUTO] · **Dependencies:** không (độc lập). Cross-ref **EPIC-B** (refresh-token flow + token lifetime). userinfo phụ thuộc Frappe OIDC bật — go-live HTTP cần **EPIC-B B-preflight** (OAuth Client scope `openid`).

### C5 — DoD codegen-dry verify (AUTO introspection proxy → gate sang EPIC-V)

**Mô tả:** Chốt DoD EPIC-C bằng dry-run codegen. STDLIB PyYAML introspection (no `java`/`npx`) = proxy CHÍNH-THỨC cho codegen-DoD; codegen THẬT (Dart/Kotlin) cần USER cấp toolchain → thuộc **EPIC-V**.
- **Files:** `assetcore/tests/test_mobile_oas.py` (+class `TestMobileCodegenDryDoD` = `TC-MOB-OAS-23a..e`) — KHÔNG tạo file mới, KHÔNG đụng yaml.
- **Acceptance (introspection, [AUTO]) — ✅ DONE+GREEN 2026-06-11:** `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` = **85 OK @landing C5** (75 + 5 C5 positive `23a..e` + 5 C5 negative anti-false-green `23d_negative_*`; baseline 75 GIỮ, 0 regression; SAU đó C6 +4 → 89 @landing C6, F-C2 +5 → 96 @landing F-C2, C3-split +2 → 98, C1-residual +3 → 103 @Vòng 8, 18f +3 → count HIỆN HÀNH @source Vòng 11 = **108 OK**). Introspection proxy STDLIB PyYAML `_codegen_dry_introspect(spec)` assert đồng thời trên ĐÚNG 10 path MVP-business (`_MVP_BUSINESS_PATHS` = 3 typed read + createPm + report/repair/cal + 3 list):
  - **(Guard-1 / a)** 0 path MVP còn trỏ `#/components/responses/Stub` (KHÔNG Stub-envelope free-form). 2 device-token (`register/unregister_device_token`) GIỮ Stub = **HỢP LỆ** (BE-PENDING EPIC-D, ADR-MOBILE-001 h) → KHÔNG assert (loại khỏi tập C5).
  - **(Guard-2 / b)** 0 dangling `$ref` toàn spec (mọi `$ref` resolve về node tồn tại). Khẳng-định-lại `test_mob_oas_09` NHƯ tiền-đề codegen (KHÔNG trùng-lặp — C5 = pre-flight gate EPIC-V).
  - **(Guard-3 / c)** mỗi 10 path MVP có 200-`data` TYPED qua `$ref` schema cụ thể: read=`*Envelope.data` $ref; create=`oneOf [<CreatedEnvelope>, Error]` mỗi nhánh $ref (closed-schema Decision-B); list=response-component→`*Envelope` $ref. KHÔNG generic `{type:object}` / KHÔNG free-form.
- **Acceptance (codegen THẬT, [HARD-STOP USER]) — ❌ CHƯA chạy được:** `java` **NOT FOUND** + `@openapitools/openapi-generator-cli` **chưa cài** (npx canceled — no auto-install; probe @2026-06-11). Sau khi USER cấp `java`+`npx`: `openapi-generator-cli generate -i docs/mobile/openapi/assetcore-mobile.openapi.yaml -g dart -o /tmp/gen-dart` + `-g kotlin` chạy sạch (exit 0, 0 ERROR, model deser route-by **closed-schema disjoint required-set** — KHÔNG discriminator, Decision-B) — chuyển sang **EPIC-V V-U1/V-U2**.
- **Owner:** [BA] (introspection) → [QA] (codegen THẬT) · **Tag:** [AUTO] phần introspection ✅ / [HARD-STOP USER] phần codegen THẬT (cần `java`+`npx`) · **Dependencies:** C1 + C2 + C3 + C4 (tất cả DONE).

**Trạng thái:** ✅ **AUTO-PART DONE+GREEN** (introspection proxy XANH — `TestMobileCodegenDryDoD` 10 TC = 5 positive `23a..e` + 5 negative anti-false-green `23d_negative_*`; `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` = **108 OK** count HIỆN HÀNH @source Vòng 11; guard-suite 6-module re-run @source Vòng 11 2026-06-11 = 108+49+13+11+9+6 = **196 OK**). 5 negative TC inject Stub/generic/dangling vào deepcopy IN-MEMORY → guard RED ⇒ chứng minh guard THẬT bắt regress (KHÔNG pass-suông). C-DoD codegen THẬT GIỮ `[ ]` = HARD-STOP USER (toolchain `java`/`npx` — re-probe 2026-06-11 `java` NOT FOUND + generator chưa cài) → chuyển **EPIC-V V-U1/V-U2**. **EPIC-C verdict ĐÓNG BĂNG = AUTO-PART DONE → gate EPIC-V.** UNCOMMITTED (chờ USER).

---

### C6 — Read-path P1 closure: 3 GET read 200 = oneOf `[<ReadEnvelope>, Error]` (Decision-B → reads) — ✅ DONE+GREEN (2026-06-11)

**Mô tả:** Đóng **read-path analog của create-path P1** (`in-handler-error-on-HTTP-200`). 3 GET read (`resolveQrToken`/`getAssetScanInfo`/`getAsset`) TRƯỚC C6 khai 200 = single `$ref <ReadEnvelope>` ⇒ codegen KHÔNG có nhánh deser `Error` cho read → in-handler **404** + **vendor-IDOR-403** (arrive HTTP-200+Error body qua `_err`) = **dead-deser**. C6 mở rộng **Decision-B** (closed-schema oneOf KHÔNG discriminator boolean) SANG read: 200 = `oneOf [<ReadEnvelope>, Error]`, 2 nhánh `additionalProperties:false` (ENVELOPE-level) + disjoint required-set (`[success,data]` vs `[success,error,code,http_status]`).

- **Re-verify @source (`api/imm00.py`):** `get_asset` 404@`:297`, vendor-IDOR-403@`:302` (`assert_vendor_can_access`→`ServiceError(FORBIDDEN)` **caught**→`_err`). `resolve_qr_token` 404@`:366`, IDOR-403@`:371`. `get_asset_scan_info` 404@`:416,425`, IDOR-403@`:421`. dispatcher-403 = guest/no-token (`resolve`/`scan-info` thêm `rbac.require('asset.read')`@`:362,403`; `getAsset` whitelist-only) → GIỮ status-line key `403`. `getAsset.data` (`AssetDetail`) GIỮ `additionalProperties:true` (as_dict surface field §3.2) — đóng ở tầng envelope nên disjoint KHÔNG ảnh hưởng.
- **Files:**
  - Modify: `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (3 read path `'200'` single-$ref → inline `oneOf [<ReadEnvelope>, Error]` + comment C6; description-set route-by-body)
  - Modify: `assetcore/tests/test_mobile_oas.py` (+class `TestMobileRead200OneOfClosed` = `TC-MOB-OAS-24a..d`; update `test_mob_oas_20a` single-$ref→oneOf; update `_codegen_dry_introspect` read-branch single-$ref→oneOf-chứa-Env+Error để C5 GIỮ GREEN)
  - Modify: `docs/mobile/04-api-contract.md §5c` (header create→create+read, +bảng read, +note C6) + `§8.7` (table read 200=oneOf + note read-path closure + invariant C6) + `§8.8` (read 200=oneOf)
  - Modify: `docs/mobile/ADR-MOBILE-001.md (f)` (+bullet SELF-CORRECTION C6 — Decision-B → reads)
- **Acceptance — ✅ DONE+GREEN 2026-06-11:** `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` = **89 OK @landing C6** (baseline 85 + 4 C6 `24a..d`; SAU đó F-C2/C3-split/C1-residual/18f → count HIỆN HÀNH @source Vòng 11 = **108 OK** — xem §C5 Trạng thái + §F-C2 + §C1-close). **RED→GREEN gate proven:** revert 1 read về single-$ref IN-FILE → `24a` + `20a` + C5 `23d/23e` RED (5 fail); restore → 89 OK (số tại C6). Mỗi 3 read 200 = `oneOf [<ReadEnvelope>, Error]` (`24a`); CẢ 2 nhánh `additionalProperties:false` + disjoint required-set + `success.enum` đối lập (`24b`); KHÔNG discriminator (Decision-B, `24a`); 0 dangling toàn spec (`24c` + `test_mob_oas_09`); status-set pre-handler-only, 404 KHÔNG status-line key (`24d`). C5 `TestMobileCodegenDryDoD` GIỮ GREEN (3 read trong `_MVP_BUSINESS_PATHS`, KHÔNG Stub/generic regress). grep yaml: `QrResolveEnvelope`/`AssetScanInfoEnvelope`/`AssetDetailEnvelope` mỗi cái nằm trong oneOf cạnh `Error`.
- **Owner:** [BA] · **Tag:** [AUTO] (yaml/doc/test introspection-only — KHÔNG đụng `api/services .py` ⇒ KHÔNG reload/migrate) · **Dependencies:** C1 (Decision-B pattern) + C2 (typed read envelope) + C5 (introspector — read-branch cập nhật để KHÔNG regress).

**Trạng thái:** ✅ **DONE+GREEN** (89 OK @landing C6; count HIỆN HÀNH @source Vòng 11 = **108 OK** — §C5/§F-C2/§C1-close; RED-before/GREEN-after gate). Doc/yaml/test introspection-only — KHÔNG reload/migrate. UNCOMMITTED (chờ USER).

---

### F-C2 — ADR hợp nhất 2 spec divergent + drift-guard introspection-only (Decision A1 2-spec-by-design) — ✅ AUTO-PART DONE (2026-06-11)

**Bối cảnh:** repo có **2 spec OpenAPI DIVERGENT** (verify @source 2026-06-11): **(A)** runtime `openapi.spec` = `api/openapi.py::generate_spec()`(`:1254`) + `openapi_overrides.py`, **3.1.0**, **487 path**, served LIVE Swagger UI `www/api-docs.html`; CÓ D1–D16 enrich NHƯNG create/read 200 = **plain `$ref SuccessEnvelope`** (KHÔNG Decision-B `oneOf[Env,Error]`) ⇒ **codegen-against-runtime = dead-deser** in-handler 404/IDOR-403. **(B)** `docs/mobile/openapi/assetcore-mobile.openapi.yaml` = **3.0.3**, **16 path**, codegen-source repo-native, MANG Decision-B closed-schema + requestBody `oneOf json+form`.

**Quyết định BA = A1 (2-spec-by-design + scope-boundary + drift-guard) — KHÔNG hợp nhất. A2 (port Decision-B vào `openapi_overrides.py`) = backlog Phase-F** (đụng runtime `api/*.py` ⇒ HARD-STOP reload). Lý do đầy đủ: [`ADR-MOBILE-001.md (k)`](../ADR-MOBILE-001.md). Hợp đồng phân vai: [`04-api-contract.md §9b`](../04-api-contract.md).

- **Drift-guard [AUTO introspection-only]:** `tests/test_mobile_oas.py::TestMobileSpecParityRuntime` (TC-MOB-OAS-25a..e) — import IN-PROCESS `openapi.generate_spec()` (KHÔNG HTTP/reload/migrate, như `test_oas_generator`) cross-check 16-path YAML vs runtime. **10 mobile-business path** (loại 2 device-token STUB `mobile.v1.*` + 4 auth passthrough `oauth2.*`) PHẢI tồn tại trong runtime với **CÙNG dotted-path-tail + CÙNG verb (allowlist `create_calibration`) + CÙNG security-class** (authed vs guest). Lệch → RED.
- **⚠️ KNOWN-DIVERGENCE verb `create_calibration`:** runtime suy verb=GET (`@frappe.whitelist()` thiếu `methods=["POST"]` `imm11.py:89`) vs YAML POST → allowlist trong guard + backlog Phase-F (fix decorator = đụng `api/*.py` + reload).
- **Files:**
  - Modify: `docs/mobile/ADR-MOBILE-001.md` (+decision (k) F-C2 + Alternatives A10 + Consequences bullet)
  - Modify: `docs/mobile/04-api-contract.md` (+§9b "Hai spec phân vai" + cross-ref (k))
  - Modify: `docs/mobile/completion/EPIC-C-api-contract.md` (mục này)
  - Modify: `docs/mobile/completion/ACCEPTANCE-CHECKLIST.md` (+C-A12 drift-guard parity [AUTO])
  - Modify: `docs/mobile/13-be-completion-roadmap.md §10` (open_issues F-C2: AUTO-part đóng, port-runtime = backlog Phase-F)
  - Modify: `assetcore/tests/test_mobile_oas.py` (+class `TestMobileSpecParityRuntime` = TC-MOB-OAS-25a..e)
- **Acceptance — ✅ AUTO-PART DONE+GREEN:** `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` = **96 OK @landing F-C2** (91 + 5 drift-guard `25a..e` `TestMobileSpecParityRuntime`, 0 regression; count HIỆN HÀNH @source Vòng 11 = **108 OK**). RED-before/GREEN-after PROVEN (inject IN-MEMORY: xoá 1 path khỏi runtime / đổi security-class → RED; control sạch → GREEN). 0 dangling `$ref`; YAML GIỮ 16 path 3.0.3, 0 `discriminator:` key; KHÔNG đụng `api/services .py` (introspection-only).
- **Owner:** [BA] · **Tag:** [AUTO] (ADR + drift-guard introspection-only) · **HARD-STOP USER (backlog Phase-F):** (1) port Decision-B vào `openapi_overrides.py` (A2 — đụng runtime + reload); (2) codegen-against-runtime live HTTP (gate EPIC-V); (3) fix `create_calibration` `methods=["POST"]` @source.

**Trạng thái:** ✅ **AUTO-PART DONE+GREEN** (ADR + drift-guard introspection-only). **HARD-STOP USER = backlog Phase-F** (port runtime / codegen live). UNCOMMITTED (chờ USER).

---

### F-C3 — count-truth reconciliation + meta-guard count-self-verify (chống tái count-drift) — ✅ DONE+GREEN (Vòng 11, 2026-06-11)

- **Vấn đề:** doc Vòng 9 ghi `test_mobile_oas` = **106 OK** như count HIỆN HÀNH, nhưng re-verify @source Vòng 11 (`bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` + `grep -cE '^\s+def test'`) cho **107** — count-drift doc-vs-source (mốc 106 là @landing Vòng 9, KHÔNG còn là count hiện hành).
- **Làm (introspection/doc-only):** (1) reconcile mọi con-số count-HIỆN-HÀNH trong docset về **source THẬT** (`106 → 107 @baseline Vòng 11`), GIỮ NGUYÊN chuỗi `@landing` lịch-sử (75/85/89/96/98/103/106) làm mốc quá-khứ. (2) thêm **meta-guard** `TestMobileOasCountSelfVerify.test_mob_oas_NN_count_matches_ssot` @`test_mobile_oas.py`: introspect mọi `unittest.TestCase` định-nghĩa trong module (STDLIB `inspect`, loại class import-vào) → đếm method `test*` load-được → assert == `_EXPECTED_TEST_COUNT` (SSoT định-nghĩa MỘT LẦN, line ~92). Count-after-add **107 → 108 @F-C3 Vòng 11** (count cuối GỒM chính meta-guard = sự-thật cuối).
- **Count tự-xác-minh:** drift sau-này (thêm/bớt TC mà quên cập `_EXPECTED_TEST_COUNT` + doc) = **RED ngay**. Sanity gộp trong cùng 1 TC (introspect > 100 + meta-guard tự-thấy) chống introspection-rỗng giả-GREEN — KHÔNG nâng count thêm (giữ đúng 108).
- **RED-before/GREEN-after PROVEN:** tạm set `_EXPECTED_TEST_COUNT = 999` → guard RED (`AssertionError: 108 != 999`); set đúng `108` → GREEN ⇒ guard THẬT bắt drift, KHÔNG pass-suông.
- **Acceptance @source Vòng 11:** `test_mobile_oas` **108 OK** · guard-suite 6-module = 108+49+13+11+9+6 = **196 OK** · +`test_mobile_preflight` 9 = **205 mobile/OAS**. `git diff --stat` api/*.py + services/*.py + yaml-schema = **TRỐNG** (KHÔNG reload gunicorn, KHÔNG migrate). C-A1 literal count dùng `@source` (KHÔNG để 106 sai gây phantom-red trên gate đã tick).
- **⚠️ TRANSITION-BASELINE off-by-one reconciled (F-C3 round-2, 2026-06-11):** narrative TRANSITION trong roadmap §10 + ACCEPTANCE-CHECKLIST từng ghi `guard-suite 190 → 192` / `mobile-OAS 199 → 201` = **off-by-one BASELINE** (ngụ ý F-C3 round-1 meta-guard thêm 2 test trong khi chỉ thêm **1**). F-C3 round-1 thực thêm 1 ⇒ baseline đúng = **191** (107+49+13+11+5+6) → 192 guard-suite, và **200** → 201 (+preflight 9). Đã sửa cả 2 nơi.
- **F-C3 round-2 — cross-module SUM meta-guard (mới):** thêm class `TestMobileGuardSuiteCountParity` (4 TC: `test_tc_mob_doc_06..09`) vào `test_mobile_docset` (5 → **9** test) → introspect `def test` THẬT của cả 6 guard-module (STDLIB regex, KHÔNG import frappe/yaml — giữ kỷ luật docset TC-MOB-DOC-05) + assert: (a) per-module count == SSoT, (b) 6-module SUM == `_GUARD_SUITE_SUM` (196), (c) docset self-count đếm-động khớp entry (anti chicken-egg), (d) transition-baseline self-consistency `final − Δ == pre-F-C3 baseline` (bắt off-by-one `190 vs 191`). **Hệ quả round-2:** docset 5→9 ⇒ guard-suite 6-module **192 → 196 OK**, mobile/OAS total **201 → 205 OK** (final count-hiện-hành mới). **RED-before/GREEN-after proven** (set `_GUARD_SUITE_SUM=999` → RED `196 != 999`; restore → GREEN). Khác F-C3 round-1 meta-guard (chỉ tự-kiểm 1 module `test_mobile_oas`), round-2 đóng lỗ **cross-module SUM + transition-baseline** — đúng loại drift đã phát hiện.
- **Owner:** [BA/MOBILE-DEV] · **Tag:** [AUTO] (meta-guard introspection + doc-sync, KHÔNG đụng api/services .py/yaml-schema) · **Cross-ref:** `ADR-MOBILE-001` (count-truth = source THẬT) · `13-be-completion-roadmap.md §10` · `ACCEPTANCE-CHECKLIST C-A1/Baseline/GO-2`.

**Trạng thái:** ✅ **DONE+GREEN** (round-1: count reconciled 106→107@source + meta-guard self-verify →108; round-2: cross-module SUM meta-guard `TestMobileGuardSuiteCountParity` 4 TC → docset 5→9, guard-suite 192→196, total 201→205; RED-before/GREEN-after proven cả 2 round). introspection/doc-only — KHÔNG reload/migrate. UNCOMMITTED (chờ USER).

---

### F-C4 — state-reconciliation roadmap §3 (4-STUB/15-path stale prose → 16-path/2-device-token DONE) + stale-line-ref guard — ✅ DONE+GREEN (Vòng 13, 2026-06-11)

- **Vấn đề:** `13-be-completion-roadmap.md §3` (CURRENT-state + TO-BUILD) còn quảng-cáo việc **đã xong** như việc **cần-làm**: §3.1 ghi `15 path,15/15 operationId` (yaml THẬT = **16**); §3.3 heading "GAPS — 4 STUB path còn lại (chưa typed)" + ref `_STUB_PATHS @ test_mobile_oas.py:152-157 (4 path)` (số-dòng line-drift CHẾT; symbol thật `_STUB_PATHS = set(_DEVICE_TOKEN_FROZEN)` @~L184 = **2 device-token**) + 3 hàng resolveQr/getAssetScan/createPm nhãn "response chưa typed"/"chưa typed requestBody" (THẬT ĐÃ typed C2) + list-element "type:object generic yaml:443/463" (THẬT C3-split DONE); §3.5 TO-BUILD `[AUTO]`/`[AUTO+BA]` rows + §9 matrix "4 STUB còn generic ⚠️" advertise việc-đã-xong là TO-BUILD.
- **Làm (doc/test introspection-only):** (1) **reconcile §3** roadmap: §3.1 `15→16 path/operationId` (+ gỡ `0.1.0-skeleton` khỏi gap-framing — version-skeleton = CI-guard concern **EPIC-G**, KHÔNG EPIC-C gap); §3.3 heading → "STUB còn lại = 2 device-token (BE-PENDING EPIC-D) · 4 path C2 ĐÃ typed", ref → **symbol** (KHÔNG `152-157`), 3 hàng + list-element → ✅ typed C2/C3-split; §3.5 + §9 matrix → ✅ DONE thay `[AUTO]`/`⚠️`. (2) **stale-line-ref guard** `TestMobileRoadmapStateReconciled` @`test_mobile_oas.py` — raw-text scan roadmap chống tái-drift §3↔source: assert 0 occurrence của anchor stale (`15 path`/`15/15 operationId`/`4 STUB path còn lại`/`chưa typed`/`còn generic ⚠️`/`152-157`) + assert `16 path` claim khớp `len(spec['paths'])` THẬT + assert `_STUB_PATHS` ref dùng dạng-symbol KHÔNG số-dòng-tuyệt-đối.
- **5 QUYẾT ĐỊNH KHOÁ bám:** Decision-B (closed-schema KHÔNG discriminator) intact; device-token = EPIC-D (KHÔNG bịa endpoint); re-verify @source theo SYMBOL (line-ref tuyệt-đối CẤM); 2-spec-by-design (A1); count-truth = source THẬT.
- **RED-before/GREEN-after PROVEN:** inject IN-MEMORY 1 anchor stale (vd "15 path") vào bản roadmap đọc-được → guard RED; bản THẬT (reconciled) → GREEN ⇒ guard bắt re-drift, KHÔNG pass-suông.
- **Acceptance @source Vòng 13:** `grep -E '15 path|15/15 operationId|4 STUB path còn lại|chưa typed|còn generic ⚠️|152-157' 13-be-completion-roadmap.md` = **0**; `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` + `test_mobile_docset` XANH (count tăng đúng số TC F-C4; `_EXPECTED_TEST_COUNT` + cross-module SUM SSoT cập). `git diff --stat` api/*.py + services/*.py + yaml-schema = **TRỐNG** (KHÔNG reload gunicorn, KHÔNG migrate).
- **Owner:** [BA/MOBILE-DEV] · **Tag:** [AUTO] (doc-reconcile + raw-text guard, KHÔNG đụng api/services .py/yaml-schema) · **Cross-ref:** `13-be-completion-roadmap.md §3.1/§3.3/§3.5/§9 + §10` · `ACCEPTANCE-CHECKLIST C-A14` · `ADR-MOBILE-001` (re-verify @source theo symbol).

**Trạng thái:** ✅ **DONE+GREEN** (roadmap §3 reconciled — 0 stale anchor; stale-line-ref guard RED-before/GREEN-after proven). doc/test introspection-only — KHÔNG reload/migrate. UNCOMMITTED (chờ USER).

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
| `PmWorkOrderListItem` (16 field imm08, name required, closed) | services/imm08.py def list_work_orders | C3-split list PM "phiếu của tôi" |
| `RepairWorkOrderListItem` (21 field imm09, name required, closed) | services/imm09.py def list_work_orders | C3-split list CM "phiếu của tôi" |
| `IncidentListItem` (23 repo + 3 enrich + 2 derived) | services/imm12.py def list_incidents | C3 |
| `OidcUserInfo` {sub,name,given_name,family_name,email,roles[]} | Frappe OIDC `openid_profile` standard claims | C4 |
| ~~`result_type` (string enum [created,error])~~ → **SUPERSEDED bởi Decision-B** (đóng C1) | xem ghi chú dưới | C1 |

> ⚠️ **CORRECTION C5 (Decision-B AUTHORITATIVE — đóng `discriminator-boolean` P1):** Phương án `result_type` discriminator (bản nháp C1) đã **BỎ**. Quyết-định cuối = **Decision-B closed-schema KHÔNG discriminator**: 200 = `oneOf [<CreatedEnvelope>, Error]` với **CẢ 2 nhánh `additionalProperties:false` + disjoint required-set** ⇒ codegen route ĐÚNG nhánh theo shape (KHÔNG cần `discriminator`). LÝ DO: `success` là BOOLEAN, OAS 3.x yêu cầu `discriminator.propertyName` trỏ property STRING ⇒ discriminator boolean **illegal** (Dart/Kotlin drop nó → deser-fail). yaml THẬT đã không có `discriminator:` key nào (0 occurrence ngoài comment giải-thích); guard `TestMobileCreate200OneOfDiscriminator` (`test_mob_oas_18b_no_boolean_discriminator`) + `_assert_200_oneof_closed_distinct` đóng băng. Field `success` boolean GIỮ NGUYÊN cho FE logic. SSoT route-by = `body.success` + `body.http_status` (in-handler error arrive HTTP-200 body §5).

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
| ADR | `ADR-MOBILE-001.md` (a–g: WIRE provider OAuth2 · RBAC 1 SSoT · BỌC endpoint · OpenAPI=hợp đồng · native no-cookie · (f) pre-handler passthrough + 2-loại-403 + form_dict + 200-oneOf [Created,Error] closed-schema route-by-VALUE (Decision-B, KHÔNG discriminator) + additionalProperties-distinct · (g) 2-list-envelope) · `ADR-MOBILE-004.md` (CORS no-wildcard) |
| LL skill | `assetcore-be` LL-BE-42..49 (in-handler HTTP-200 + Error envelope ≠ raise→4xx; 2 loại 403; count==rows) · `assetcore-doc` DONE-gate spec-contract |
| EPIC khác | **B** (B-preflight OAuth Client scope `openid` cho C4; B-refresh cho C4 refresh-on-401) · **G** (CORS/traceback hardening §6) · **V** (V-codegen verify Dart/Kotlin THẬT — C5 [HARD-STOP USER]) · **D** (không phụ thuộc trực tiếp) |

## 8) Rủi ro

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Tái phát `discriminator-boolean` (propertyName trỏ property non-string) | P1 | C1 guard `_assert_200_oneof_discriminator` assert `type=='string'` + mapping khớp enum VALUE — RED→GREEN gate |
| ~~`WorkOrderListItem` union (PM+CM chia envelope) → client nhận field null không-mong-đợi~~ | ~~P2~~ → ✅ ĐÓNG | **C3-split** tách 2 item-schema field-disjoint (`Pm`/`RepairWorkOrderListItem`); mỗi endpoint trỏ item của nó → KHÔNG còn field null lạ. KNOWN-GAP normalize ĐÓNG (không còn Phase-E). |
| `AssetDetail` open-shape (AC Asset nhiều field) → codegen sinh model thiếu field | P2 | C2 khai `additionalProperties: true` + liệt kê field MVP cần; ghi chú registry-doc open-shape |
| Frappe `form_dict` — codegen JSON-only client gửi field tới handler RỖNG (sai-âm-thầm) | P1 | C2/C4 requestBody oneOf `json + form-urlencoded` (CÙNG $ref); C4 guard `_assert_rpc_requestbody_form_json` |
| createPm chọn NHẦM 403 dual-shape (copy mù pattern report_incident) | P1 | C2 đọc handler @source TRƯỚC (imm08.py:92 `rbac.require` = SINGLE-shape `Forbidden`); ADR-001 (f) caveat |
| in-handler 404/409/422 keyed dưới HTTP-code response-key = dead-deser | P1 | C1/C2 gom vào nhánh Error của 200-oneOf; pre-handler 401/403/429 GIỮ status-line key (§3.3) |
| Codegen THẬT (Dart/Kotlin) chưa chạy được — thiếu `java`/`npx` | P2 | C5 introspection PyYAML = proxy [AUTO]; codegen THẬT = [HARD-STOP USER] → EPIC-V |
| userinfo path Frappe OIDC chưa bật trên cloud (scope `openid` chưa cấp ở OAuth Client) | P2 | C4 chỉ khai hợp đồng; go-live HTTP phụ thuộc EPIC-B B-preflight (cấp scope `openid`) — [HARD-STOP USER] |
