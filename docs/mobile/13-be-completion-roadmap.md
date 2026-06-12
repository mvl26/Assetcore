# 13 — BE Completion Roadmap (MASTER)

| Mục | Giá trị |
|---|---|
| Vai trò file | **MASTER roadmap** hoàn thiện lớp Backend-for-Mobile — chốt 5 EPIC, DoD, dependency, AUTO vs HARD-STOP |
| Initiative | Mobile Backend (AssetCore = BE cho app mobile native; repo UI riêng) |
| Cấu trúc | USER đã duyệt 2026-06-11 |
| Trạng thái | Phase A exit-ready → mở Phase B/C/E/F (xem [`11-phase-a-exit.md`](./11-phase-a-exit.md)) |
| Phạm vi file này | **doc-only** — KHÔNG sửa `api/*.py` / `services/*.py` / yaml-path/operationId; KHÔNG git commit/push/migrate/reload/restart |
| Cập nhật | 2026-06-11 |

> **Nguồn chân lý kiến trúc** = [`00-overview.md §2`](./00-overview.md) (3 quyết định USER) + [`11-phase-a-exit.md §1`](./11-phase-a-exit.md) (traceability matrix 6 flow). File này KHÔNG re-litigate quyết định nền — chỉ TỔ CHỨC việc còn lại thành 5 EPIC khoá-ID + DoD + thứ tự.
> **Mọi claim kỹ thuật** trong file này có `file:line` evidence verify tại source **Frappe v15.107.2** (branch `feature/hieuc/core-refinement`, ground 2026-06-11). Việc CHƯA verify → đánh dấu `[ROADMAP]` / `*(Cần khảo sát)*`.
> ⚠️ **Số dòng `file:line` là CHỈ DẪN tại thời điểm ground (2026-06-11)** — code drift theo thời gian; agent thực thi **PHẢI re-verify @source** (mở file, tìm theo tên symbol/hàm) TRƯỚC khi sửa, KHÔNG tin số dòng tuyệt đối. Tên file + hàm/symbol là ổn định; số dòng thì không.

---

## 0. Mục tiêu (DoD TỔNG)

**DoD TỔNG = MVP field-tech 6-flow END-TO-END chạy THẬT trên cloud:**

| # | Flow MVP | Endpoint trục (file:line @source) | EPIC chốt |
|---|---|---|---|
| 1 | Đăng nhập OAuth2 + refresh | `frappe/integrations/oauth2.py:74` authorize · `:123` get_token · `:144` revoke | **B** |
| 2 | Quét QR → hồ sơ thiết bị | `api/imm00.py:588` resolve_qr_token · `:631` get_asset_scan_info · `:454` get_asset | **C** |
| 3 | Báo hỏng (Incident) | `api/imm12.py:71` report_incident | **C** (typed ✅) |
| 4 | Yêu cầu WO PM/CM/Cal | `api/imm08.py:91` create_pm · `api/imm09.py:35` create_repair · `api/imm11.py:89` create_cal | **C** |
| 5 | "Phiếu của tôi" (list+detail) | `api/imm08.py:28` list_pm · `api/imm09.py` list_repair · `api/imm12.py:197` list_incidents | **C** |
| 6 | Push FCM | `services/notifications.py:366` `_dispatch` (kênh #3 CHƯA có) | **D** |

**Tiêu chí "chạy THẬT trên cloud":** 1 client codegen (Dart/Kotlin) gọi được cả 6 flow trên public HTTPS host → **EPIC-V** chốt cuối.

### Out-of-scope MVP (post-MVP — ghi RÕ, KHÔNG làm round này)

- **Offline-sync** ([`07-offline-sync.md`](./07-offline-sync.md) + ADR-003) — read-cache/write-queue/conflict đã đặc tả, impl Phase E.
- **Manager / luồng duyệt** (approval) — MVP chỉ field-tech (D-MVP, [`05-personas-mvp.md`](./05-personas-mvp.md)).
- **Mở rộng đa-module** ngoài 6 flow — không thêm persona quản lý/giám đốc.

---

## 1. Ba quyết định nền (AUTHORITATIVE — KHÔNG re-litigate)

> In nguyên ở [`00-overview.md §2`](./00-overview.md). USER chốt 2026-06-09. Mọi EPIC BÁM theo.

| Mã | Quyết định | Hệ quả cho BE-completion |
|---|---|---|
| **D-AUTH** | OAuth2 (Authorization Code + PKCE S256) + access-token ngắn hạn + refresh + revoke. WIRE provider Frappe có sẵn — KHÔNG tự viết OAuth. Bearer→`set_user`→RBAC capability (scope↔capability = **1 SSoT**). | EPIC-B = WIRE-not-write; refresh ĐÃ hỗ trợ (`frappe/oauth.py:187`). |
| **D-MVP** | MVP nhắm **kỹ thuật viên hiện trường** (6 flow). Tái dùng endpoint nghiệp vụ permission-aware. | Lớp mobile = **BỌC + TÁI DÙNG** endpoint+capability có sẵn — KHÔNG viết lại logic. |
| **D-STACK** | App **native** (Flutter HOẶC React Native), KHÔNG WebView/PWA. Repo UI tách riêng; PKCE bắt buộc. | Native APK **KHÔNG cần CORS** (không browser engine) — EPIC-G CORS chỉ cho web/PWA/Swagger/WebView-OAuth. |

---

## 2. Năm EPIC (ID KHOÁ — KHÔNG đổi) + thứ tự

```
        EPIC-C  (API Contract codegen-ready)  ── độc lập, doc/yaml/test → LÀM NGAY
           │
           ├──────────────┐
           ▼              ▼
        EPIC-B         thiết kế EPIC-D
   (Auth & Provision)   (Push FCM design)
           │              │
           ▼              │
        EPIC-G ◄──────────┘   (Go-live & Hardening — cần USER: cloud + site_config)
           │
           ▼
        EPIC-D  (Push FCM impl — cần B + FCM creds)
           │
           ▼
        EPIC-V  (Codegen Verify + Handoff — CHỐT CUỐI)
```

| Thứ tự | EPIC | Tên | Phụ thuộc | Gate chính |
|---|---|---|---|---|
| 1 | **C** | API Contract codegen-ready | (độc lập) | `openapi-generator` chạy sạch · `test_mobile_oas` xanh |
| 2 | **B** ∥ thiết kế **D** | Auth & Provisioning | (∥ C) | `preflight.verify_oauth_client()` ready=True |
| 3 | **G** | Go-live & Hardening | C + B | HTTPS reachable + security gate |
| 4 | **D** | Push FCM impl | B + FCM creds + G | báo hỏng → KTV nhận push |
| 5 | **V** | Codegen Verify + Handoff | C + D + G | 1 client gen gọi được 6 flow trên cloud |

**Mỗi TASK tag rõ:** `[AUTO]` = factory tự đóng được (doc/yaml/test/impl-không-deploy) vs `[HARD-STOP USER]` = cloud / `bench migrate` / `bench restart` / `site_config` / FCM creds (BE KHÔNG tự chạy — xem §8 Blockers).

---

## 3. EPIC-C — API Contract (codegen-ready)

> Vùng tài liệu: [`04-api-contract.md §5/§8/§10`](./04-api-contract.md) + `openapi/assetcore-mobile.openapi.yaml`. **CHỈ ĐỌC yaml round này** (BE-completion doc liệt-kê, KHÔNG sửa yaml ở đây).

### 3.1 Hiện trạng

- YAML `openapi 3.0.3`, **16 path, 16/16 operationId** camelCase frozen (grep @working-tree: `grep -cE '^\s{2}/'` = 16 + `grep -cE 'operationId:'` = 16). *(version-string `info.version` còn `0.1.0-skeleton` (yaml:89) — KHÔNG là EPIC-C gap; semver-bump = CI-guard concern **EPIC-G** G-A-series, KHÔNG block codegen-readiness EPIC-C.)*
- **Bộ-ba CREATE đã typed ✅:** reportIncident / createRepairWorkOrder / createCalibration — requestBody oneOf (json+form-urlencoded), response `200` oneOf `[Created, Error]` **closed-schema route-by-VALUE `body.success`** (Decision-B — `additionalProperties:false` + disjoint required-set, KHÔNG discriminator), 404/4xx wire grounded `messages.py` http_status.
- **3 LIST đã typed envelope ✅:** `WorkOrderListEnvelope` (data.data[]) + `IncidentListEnvelope` (data.items[]), `Pagination` dùng chung (Option A, ADR-MOBILE-001 g).
- **Guard:** `test_mobile_oas` xanh (0 dangling `$ref`; orphan ⊆ `_RESERVED_ORPHANS`).

### 3.2 P1 — `in-handler-error-on-HTTP-200` (ĐÃ XÁC MINH @source — ADR đã CHỐT)

**Cơ chế:** service `nthrow(MSG.X)` (`utils/notify.py:61-87`) → `ServiceError(http_status=entry['http_status'])` (`services/shared/errors.py:36-42`) → `handle()` bắt (`utils/api_handler.py:48-51`) → `_service_error_to_envelope` (`:54-69`) → `_err(...,http_status=e.http_status)` (`utils/response.py:95-154`). **Body chứa `code`+`http_status` (`response.py:133-138`) NHƯNG HTTP status-line VẪN 200** (`handle` return dict; `hooks.py` no `after_request`).

**ADR (đã CHỐT trong yaml — Decision-B):** response `"200"` = `oneOf [<Created>, Error]` **closed-schema** (`additionalProperties:false` CẢ 2 nhánh + disjoint required-set, **KHÔNG `discriminator`**) → client route theo **GIÁ TRỊ** field `body.success` (`Created.success.enum=[true]` vs `Error.success.enum=[false]`), KHÔNG theo status-line. Đã áp 3 CREATE path (+ `createPmWorkOrder` C2 + 3 GET read C6). yaml = 0 `discriminator:` key. *(Bản nháp R1 từng đề xuất `discriminator: success` — BỎ vì `success` boolean → OAS 3.x illegal; xem ADR-MOBILE-001 (f) R1→R4.)*

**Bằng chứng từng path (file:line):**

| Path | 403 shape | in-handler errors (svc) | return |
|---|---|---|---|
| `imm12.report_incident` | **DUAL** — guest 401 `imm12.py:92` = DEAD-CODE over HTTP (dispatcher-403 trip trước, [`04 §5`](./04-api-contract.md)); cap-403 `imm12.py:96` = HTTP-200+Error | 422 BR-12-01 clinical_impact `services/imm12.py:359` (`messages.py:754`); 404 asset∄ `services/imm12.py:361` (`messages.py:747`) | `{name,status,severity}` `imm12.py:410` |
| `imm09.create_repair_work_order` | **SINGLE** — `rbac.require('repair.create')` `api/imm09.py:40` → PermissionError HTTP-403 THẬT | 404 `services/imm09.py:746` (`messages.py:716`); 409 HAS_OPEN_WO `:753` (`messages.py:667`) | `{name,status,sla_target_hours}` `imm09.py:771` |
| `imm11.create_calibration` | **SINGLE** — `rbac.require('calibration.create')` `api/imm11.py:95` | 404 `services/imm11.py:999` (`messages.py:848`); 409 ASSET_BLOCKED CAL-008 `:1002` (`messages.py:855`) | `{name,status=Scheduled}` `imm11.py:1013` |

> **2 loại 403 (DONE-gate spec-contract):** (a) **dispatcher-403** = guest/no-token, raise tại `is_whitelisted` `frappe/__init__.py:876` → HTTP-403 + `FrappeRawError`. (b) **in-handler cap-403** = thiếu capability, `_err(...,403)` → HTTP-200 + Error envelope. Client phân biệt bằng **HTTP status-line** (KHÔNG anyMatch oneOf). Xem [`04 §5a/§5b`](./04-api-contract.md).

### 3.3 STUB = ∅ (0 STUB-on-MVP — EPIC-D D4 typed device-token) · 4 path C2 ĐÃ typed (F-C4 reconciled)

> **Source-truth `_STUB_PATHS` @ SYMBOL `_STUB_PATHS = set()`** trong `assetcore/tests/test_mobile_oas.py` (re-verify @source theo SYMBOL, KHÔNG số-dòng-tuyệt-đối — số dòng cũ đã line-drift). **EPIC-D D4 (Vòng 17):** 2 device-token (`registerDeviceToken`/`unregisterDeviceToken` @ yaml `/register_device_token`, `/unregister_device_token`) **ĐÃ typed** (service D2 `mobile_device_token.py` tồn tại @source) — `requestBody DeviceTokenRequest` + 200 oneOf `[<Created>, Error]` closed-schema **Decision-B route-by-VALUE, 0 discriminator** (04 §8.9). ⇒ **`_STUB_PATHS = ∅`** (0 STUB-on-MVP toàn bộ 16 path). `responses/Stub` HẾT referenced → forward-reserve (`_RESERVED_ORPHANS`). Handler `api/mobile/v1/device_token.py` = BE impl-part PENDING (wrap service D2). 4 path scan/createPm **ĐÃ typed (C2)** — RỜI `_STUB_PATHS`, không còn `responses/Stub`.

| # | Path | yaml | Source | Trạng thái |
|---|---|---|---|---|
| 1 | resolveQrToken | :1268 | `api/imm00.py:588` `resolve_qr_token(token="")` · `@rate_limit:587` (→429) · `rbac.require("asset.read"):615` · 404 `:619` · vendor-IDOR 403 `:622` | ✅ **typed C2** — `QrResolveEnvelope` 200-oneOf[Created,Error] closed-schema route-by-VALUE `body.success` (Decision-B); RỜI `_STUB_PATHS` |
| 2 | getAssetScanInfo | :1280 | `api/imm00.py:631` · `@rate_limit:630` (→429) · build qua `services/imm00.py:637` `build_asset_scan_info` | ✅ **typed C2** — `AssetScanInfoEnvelope` (12 field + `available_actions[]{key,label,route,enabled,reason}`); RỜI `_STUB_PATHS` |
| 3 | getAsset | :1292 | `api/imm00.py:454` `get_asset(name)` · `rbac.require:472` · 404 `:474` · vendor-IDOR `:477` · return `_ok(_strip_qr_token(...))` `:507` | ✅ **typed C2+C6** — `AssetDetailEnvelope` 200-oneOf[Created,Error] (read-path P1 closure C6); RỜI `_STUB_PATHS` |
| 4 | createPmWorkOrder | :1368 | `api/imm08.py:91` `create_pm_work_order()` (`_form_dict()` `:17`) · `rbac.require pm.create:92` · `svc.create_adhoc_work_order(data)` `services/imm08.py:787` · required `("asset_ref","pm_schedule","due_date")` `:788` · return `{name,status,checklist_items_count}` `:836-840` | ✅ **typed C2** — `CreatePmWorkOrderRequest` (required chốt BA) + response, dual json+form (C4); RỜI `_STUB_PATHS` |

**Field thật cho list-element (✅ C3-split DONE — KHÔNG còn `type:object` generic; element = `$ref` field-disjoint):**

- **PM** (`services/imm08.py:531-533`): `[name, asset_ref, pm_type, wo_type, status, due_date, completion_date, assigned_to, supervisor, overall_result, is_late, source_pm_wo]` + enrich `asset_name`/`location_name` (`:566-567`).
- **CM** (`services/imm09.py:675-681`): `[name, asset_ref, asset_name, repair_type, priority, status, open_datetime, completion_datetime, mttr_hours, sla_breached, sla_target_hours, is_repeat_failure, assigned_to, root_cause_category, risk_class, parts_hold_hours, parts_hold_started]`.
- **Incident** (`services/imm12.py:750-756`): `[name, asset, incident_type, severity, status, fault_code, reported_by, reported_at, description, linked_capa, linked_repair_wo, rca_required, rca_record, chronic_failure_flag, patient_affected, closed_date, assigned_to, acknowledged_at, resolved_at, response_breached, resolution_breached, response_due_at, resolution_due_at]` + `_enrich_asset_names`/`_enrich_sla_breach` (`:761/:763`).

> **PM ≠ CM field-set → ✅ ĐÃ TÁCH (C3-split 2026-06-11):** vì FIELD KHÁC nhau, KHÔNG ép chung 1 UNION item. Tách 2 envelope RIÊNG `PmWorkOrderListEnvelope` / `RepairWorkOrderListEnvelope` + 2 item-schema field-disjoint `PmWorkOrderListItem` (16 field imm08) / `RepairWorkOrderListItem` (21 field imm09); mỗi list path trỏ item của nó (rows-key `data` GIỮ nguyên). KNOWN-GAP "KHÔNG ép chung" ĐÓNG — không còn defer Phase-E. Chi tiết: EPIC-C §C3-split + ADR-MOBILE-001 (g).

### 3.4 userinfo / whoami (OIDC) — ✅ ĐÓNG bởi C4 (2026-06-11)

- ✅ **C4 DONE:** path `GET /api/method/frappe.integrations.oauth2.openid_profile` (`operationId getUserInfo`, security `OAuth2: [openid]`) + schema `OidcUserInfo` **RAW passthrough** đã wire vào yaml. App lấy tên+role KTV sau login (flow-1).
- Endpoint Frappe = `frappe/integrations/oauth2.py:163-164` `openid_profile` (`@whitelist`, **KHÔNG allow_guest** → cần bearer) → `create_userinfo_response` → set `frappe.local.response = body` (`:172-174`, RAW). Claims `get_userinfo` `oauth.py:530-555`.
- **`[VERIFIED @source]`** 8 claim GROUNDED (KHÔNG bịa): `sub`(string|null), `name`, `given_name`, `family_name`, `email`, `picture`(string|null), `roles`(array\<string\>), `iss`. `OidcUserInfo` closed-schema (`additionalProperties:false`, Decision-B). Guard `test_mob_oas_22` (TestMobileUserInfo 9 TC) XANH.

### 3.5 TO-BUILD EPIC-C

| Tag | Task |
|---|---|
| ✅ `[DONE C2]` | Doc BE-completion vùng C tích hợp §3 file này (`completion/EPIC-C-api-contract.md`): liệt kê STUB còn lại + `_STUB_PATHS` guard (symbol) + chứng cứ P1 — **.md** xong |
| ✅ `[DONE C2]` | Type 4 scan/createPm response (RỜI `responses/Stub`): `QrResolveEnvelope` · `AssetScanInfoEnvelope {…12 field + available_actions:AvailableAction[]{key,label,route,enabled,reason}}` (`services/imm00.py:567-602`) · `AssetDetailEnvelope` (as_dict enrich + overdue). 200-oneOf[Created,Error] closed-schema route-by-VALUE `body.success` (Decision-B, KHÔNG discriminator) + 404 in-handler vào nhánh Error (đồng pattern 3 create); `TestMobileTypedReadCreate` (TC-MOB-OAS-20) xanh |
| ✅ `[DONE C2 — BA chốt requestBody]` | `createPmWorkOrder`: `CreatePmWorkOrderRequest` (required `asset_ref`/`pm_schedule`/`due_date` @`services/imm08.py:788` + optional `pm_type`/`wo_type`/`assigned_to`/`supervisor`/`technician_notes`) + response `{name,status,checklist_items_count}`. BA chốt requestBody @source (required ở service KHÔNG ở `@whitelist` signature → codegen KHÔNG suy được → BA khai tường-minh trong yaml). KHÔNG đổi `api/imm08.py:91` signature (introspection-only, KHÔNG reload gunicorn). dual json+form (C4 vá) |
| ✅ `[DONE C3-split]` | 2 item-schema field-disjoint `PmWorkOrderListItem`/`RepairWorkOrderListItem` + `IncidentListItem` thay `type:object` generic; mỗi list path trỏ envelope+item RIÊNG (KHÔNG còn UNION). `TestMobileListItemTyped` 8 TC (+`21b2`/`21g` disjoint-field) xanh |
| ✅ `[DONE C4]` | userinfo/whoami OIDC path `getUserInfo` + schema `OidcUserInfo` (§3.4) — wire xong, test_mob_oas_22 xanh |
| ✅ `[DONE C2]` | `test_mobile_oas` + `_STUB_PATHS = set(_DEVICE_TOKEN_FROZEN)`/`_EXPECTED_TEST_COUNT`/`_PATHS_REQUIRE_401/403` cập nhật khi 4 scan/createPm rời + userinfo thêm; `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` XANH |
| ✅ `[DONE C5+C6+F-C2+C-DoD-CFG AUTO]` | codegen-dry introspection proxy PyYAML (`TestMobileCodegenDryDoD`) + read-path oneOf (C6 `TestMobileRead200OneOfClosed`) + drift-guard parity (F-C2 `TestMobileSpecParityRuntime`) + **config-validity (`TestMobileCodegenConfig` — `openapitools.json`↔YAML)**: 0 Stub-on-MVP + 0 dangling + mọi 10 path MVP typed + runnable-config 3 generators trỏ YAML — `test_mobile_oas` **141 OK** (count HIỆN HÀNH @source G3 2026-06-12; `_EXPECTED_TEST_COUNT=141` SSoT; gồm 1 meta-guard `TestMobileOasCountSelfVerify` F-C3 + 10 TC `TestMobileCodegenConfig` C-DoD-CFG + 4 TC `TestMobileRoadmapStateReconciled` F-C4 + 4 TC `TestMobileRefreshOn401DocGuard` F-B2 + 4 TC `TestMobileTracebackHardeningDocGuard` G3; guard-suite 7-module tổng **281 OK** re-run @source G3 2026-06-12). AUTO-part DoD EPIC-C đóng → gate EPIC-V |
| `[V · HARD-STOP USER]` | Smoke `openapi-generator` THẬT (Dart/Kotlin) qua `openapitools.json` runnable-config — cần `java`+`npx` (NOT FOUND @2026-06-11) → thuộc EPIC-V V-U1/V-U2 |

### 3.6 DoD EPIC-C

**AUTO-part (introspection proxy PyYAML — đã đóng):**
- [x] **codegen-dry introspection** (C5 `TestMobileCodegenDryDoD` `test_mob_oas_23a..e`) + **config-validity** (C-DoD-CFG `TestMobileCodegenConfig` `test_mob_oas_28a..j` — `openapitools.json`↔`_MOBILE_YAML`): 0 path MVP còn Stub + 0 dangling `$ref` + mọi 10 path MVP có `data` typed `$ref` + runnable-config 3 generators trỏ YAML — chạy KHÔNG-toolchain (`bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` = **141 OK** count HIỆN HÀNH @source G3 2026-06-12; `_EXPECTED_TEST_COUNT=141` SSoT; guard-suite 7-module = `test_mobile_oas` 141 + `test_oas_generator` 49 + `test_oas_serve` 13 + `test_oas_signatures` 11 + `test_mobile_docset` 9 + `test_mobile_capability_map` 6 + `test_mobile_security_gate` 52 = **281 OK** re-run @source G3 2026-06-12).
- [x] `test_mobile_oas` xanh (10 path MVP rời Stub + list-element + userinfo + C5 dry-DoD); CHỈ 2 device-token GIỮ Stub = BE-PENDING EPIC-D (hợp lệ).
- [x] requestBody oneOf json+form mọi RPC path (`test_mob_oas_22i`); response `200` oneOf[Created,Error] **closed-schema KHÔNG discriminator** (Decision-B) áp đủ 4 create.

**THẬT-part (codegen Dart/Kotlin — HARD-STOP USER, gate EPIC-V):**
- [ ] `openapi-generator` chạy THẬT sạch (Dart/Kotlin) — exit 0, 0 ERROR. `java` **NOT FOUND** + `@openapitools/openapi-generator-cli` chưa cài (probe @2026-06-11) ⇒ **[HARD-STOP USER]** → EPIC-V V-U1/V-U2.

---

## 4. EPIC-B — Auth & Provisioning

> Vùng tài liệu: [`03-auth-oauth2.md`](./03-auth-oauth2.md) · [`10-deploy-ops.md §1`](./10-deploy-ops.md) · [`12-phase-b-preflight.md`](./12-phase-b-preflight.md) · ADR-MOBILE-001.

### 4.1 Auth provider SẴN SÀNG (WIRE-not-write — KHÔNG sửa core)

| Khía cạnh | Trạng thái @source (file:line) |
|---|---|
| authorize | `frappe/integrations/oauth2.py:74-75` (`@whitelist allow_guest`); Guest→302 `/login` `:81-82` |
| get_token | `oauth2.py:123-124` (allow_guest); success body **PASSTHROUGH OAuthlib** `:137` (KHÔNG envelope); error grant đường thường → `http_status_code=400` `:133-134` |
| revoke_token | `oauth2.py:144-145` (allow_guest); **LUÔN 200** body rỗng `frappe._dict({})` `:158-159` (RFC 7009) |
| openid_configuration (discovery) | `oauth2.py:180-181` (allow_guest). introspect: `:205-206` |
| userinfo (openid_profile) | `oauth2.py:163-164` (`@whitelist` KHÔNG allow_guest → cần bearer) → OIDC claims |
| **refresh-token** | **HỖ TRỢ ĐẦY ĐỦ** — `frappe/oauth.py:184-187` `validate_grant_type ∈ [authorization_code, refresh_token, password]`; `validate_refresh_token` chỉ status="Active" `:270-296`; `get_original_scopes` `:244-249` |
| **token lifetime** | **3600s HARD-CODED, KHÔNG site_config knob** — `get_oauth_server()` `oauth2.py:19-24` dựng `WebApplicationServer` KHÔNG truyền `token_expires_in` → oauthlib fallback `or 3600`; `expiration_time = creation + timedelta(expires_in)` `oauth_bearer_token.py:28-31`. OAuth Provider Settings (Single) CHỈ field `skip_authorization`. **KNOWN-LIMIT:** đổi TTL = ADR-MOBILE-001 alt A7 (wrap/fork `get_oauth_server`) Phase F — KHÔNG chặn MVP. |

### 4.2 Provisioning OAuth Client — preflight gate (DoD cơ chế)

- **Preflight verifier (ĐÃ CÓ, READ-ONLY):** `assetcore/api/mobile/preflight.py:146-220` `verify_oauth_client()` (`@frappe.whitelist` KHÔNG allow_guest + `frappe.only_for("System Manager"):171`). Chấm 7 điều kiện B-1: `client_count>=1` `:177-179` · grant_type `:88` · response_type `:96` · `default_redirect_uri∈redirect_uris` `:105` · `scopes='all openid'` `:121` · `skip_authorization==0` `:129` · `allowed_roles` non-empty `:136`. count==0 → `ready=False` + blocker VI, **KHÔNG raise** `:181-190`.
- **Provisioning AUTO = KHÔNG có** — grep `hooks.py::fixtures` / `patches.txt` / `setup/` = 0 → BẮT BUỘC runbook thủ công [`10 §1`](./10-deploy-ops.md). OAuth Client count=0 @ site miyano.
- **Decision (chủ ý):** giữ runbook thủ công + preflight READ-ONLY là **gate khách quan** thay helper write (DB-write = HARD-STOP USER, vi phạm read-only ADR-MOBILE-001 nếu auto). Nếu USER yêu cầu helper idempotent write → đề xuất NHƯNG đánh dấu `[HARD-STOP execute]`.

### 4.3 Device-token cho FCM (chặn EPIC-D)

> **Trạng-thái-hiện-hành @F-B2 2026-06-12 (re-verify @source):** đồng bộ với [§3.3](#33-stub--0-stub-on-mvp--epic-d-d4-typed-device-token--4-path-c2-đã-typed-f-c4-reconciled) cùng file. Snapshot stale 2026-06-11 (device-token "CHƯA tồn tại") đã `[SUPERSEDED]` — xem cuối mục để giữ audit-trail.

- **DocType + service + handler ĐÃ TỒN TẠI @source (EPIC-D D4/D6/D7):** `assetcore/assetcore/doctype/ac_mobile_device_token/{json,py,__init__}` (7 field, autoname=hash, `fcm_token` UNIQUE, track_changes=1) · service `assetcore/services/mobile_device_token.py` (`register_device_token(*, fcm_token, platform, device_label='', app_version='')` ÉP `user=frappe.session.user` chống spoof §6.2 · UPSERT dedup · `unregister_device_token(fcm_token)` enabled=0 giữ audit · `invalidate_token`; gọi `log_audit_event` NĐ98 §5.4) · handler `assetcore/api/mobile/v1/device_token.py` (`@frappe.whitelist(methods=["POST"])` KHÔNG allow_guest → cần bearer; `register_device_token` thêm `@rate_limit` chống spam §5.3 — THỨ TỰ decorator: `@whitelist` NGOÀI, `@rate_limit` TRONG). Spec gốc: [`06-push-fcm.md §2`](./06-push-fcm.md).
- **OpenAPI = 2 path TYPED (KHÔNG STUB):** `registerDeviceToken`/`unregisterDeviceToken` @ yaml `/api/method/assetcore.api.mobile.v1.register_device_token` (+ `…unregister_device_token`) — `requestBody DeviceTokenRequest` oneOf json+form + 200 oneOf `[<Created>, Error]` **closed-schema Decision-B route-by-VALUE, 0 discriminator** (schema `DeviceTokenRequest`/`RegisterDeviceTokenAckEnvelope`/`UnregisterDeviceTokenAckEnvelope` ~yaml L1238–1323; KHÔNG còn yaml:1565/1582). Guard `_STUB_PATHS = set()` (∅) @ `assetcore/tests/test_mobile_oas.py` (SYMBOL — re-verify @source, KHÔNG số-dòng-tuyệt-đối) ⇒ 0 STUB-on-MVP. Chi tiết: [§3.3](#33-stub--0-stub-on-mvp--epic-d-d4-typed-device-token--4-path-c2-đã-typed-f-c4-reconciled) + [`04-api-contract.md §8.9`](./04-api-contract.md) + [`completion/EPIC-D-push-fcm.md §D4`](./completion/EPIC-D-push-fcm.md).
- **→ SINGLE-OWNER = EPIC-D (D1/D2/D4 build DocType + service + endpoint MỘT LẦN) — GIỮ NGUYÊN.** EPIC-B **B3 = dependency-gate** (chỉ xác nhận bearer→`set_user` reach `api/mobile/v1` qua **B2**), **KHÔNG impl device-token** (tránh build trùng giữa B và D). Impl chi tiết = §6 (EPIC-D). `bench migrate` (table+UNIQUE live) + reload gunicorn = **[HARD-STOP USER]** vẫn `[ ]`.

> **`[SUPERSEDED]` snapshot 2026-06-11 (giữ audit-trail tiến độ — KHÔNG đọc như trạng-thái-hiện-hành):** ground ban đầu khi DocType "AC Mobile Device Token" CHƯA tồn tại (grep `device_token`/`fcm_token` = 0 hit ngoài test), `api/mobile/` chỉ có `__init__.py` + `preflight.py` (chưa `v1/`), 2 path OpenAPI còn STUB (yaml:1565/:1582). Đã thay bằng trạng-thái-hiện-hành ở trên @F-B2. Đồng bộ với [`completion/EPIC-B-auth-provisioning.md §3.4 [SUPERSEDED]`](./completion/EPIC-B-auth-provisioning.md).

### 4.4 TO-BUILD + DoD EPIC-B

| Tag | Task |
|---|---|
| `[AUTO]` | Doc "Auth provider sẵn sàng": khẳng định refresh ĐÃ hỗ trợ + TTL 3600s hard-coded (KNOWN-LIMIT) + userinfo=openid_profile — bám file:line §4.1, KHÔNG re-litigate |
| `[AUTO]` | Doc "Provisioning": runbook thủ công `10 §1` + preflight gate = cơ chế DoD; ghi RÕ KHÔNG fixture/patch auto |
| `[ref EPIC-D]` | Device-token DocType + service + `register/unregister_device_token` = **OWNED & impl bởi EPIC-D (D1/D2/D4)**; EPIC-B B3 CHỈ gate dependency (bearer reach `api/mobile/v1`), **KHÔNG impl trùng** |
| ✅ `[DONE]` | Backlog đóng vòng: **(a) ✅ DONE (C-A6)** userinfo/whoami ĐÃ wire vào yaml — path `GET …openid_profile` `operationId getUserInfo` (yaml:2030/2033) + schema `OidcUserInfo` RAW passthrough (yaml:1581), security `[openid]` (§3.4); **(b) ✅ DONE (B-A4)** ví dụ refresh-on-401 sequence ĐÃ có ở [`03 §1.3e/§2.5`](./03-auth-oauth2.md) (`grant_type=refresh_token`) + [`04 §9d(n)`](./04-api-contract.md) (401 → đổi refresh_token → retry MỘT lần → fail re-auth). Cross-ref [`ACCEPTANCE-CHECKLIST.md`](./completion/ACCEPTANCE-CHECKLIST.md) C-A6 + B-A4 `[x]`. |

**DoD checklist EPIC-B:**

| # | Tiêu chí | Ai chạy |
|---|---|---|
| 1 | `preflight.verify_oauth_client()` ready=True | **[HARD-STOP USER]** tạo OAuth Client record |
| 2 | authorize→token→refresh→revoke + PKCE smoke trên cloud | **[HARD-STOP USER]** reload + host |
| 3 | device-token doctype sẵn sàng (impl ở **EPIC-D D1/D2/D4** — KHÔNG ở B) | **[AUTO impl EPIC-D]** + **[HARD-STOP USER]** migrate |

**4-bước go-live HARD-STOP (LL-DEPLOY-03):** `bench migrate` (OAuth Client/Bearer Token native + device-token + bust `ac_caps`) → `bench restart` (gunicorn --preload) → `site_config` (allow_cors LIST / OAuth Client / qr_base_url / FCM) → verify preflight. **Toàn bộ HARD-STOP USER — doc nêu, BE KHÔNG chạy.**

---

## 5. EPIC-G — Go-live & Hardening

> Vùng tài liệu: [`10-deploy-ops.md`](./10-deploy-ops.md) + [`08-security-compliance.md`](./08-security-compliance.md) + ADR-MOBILE-004 + [`12-phase-b-preflight.md`](./12-phase-b-preflight.md). **CHỈ ĐỌC code** — chỉ viết .md.

### 5.1 GO-LIVE KNOB MATRIX (5 knob × hiện trạng/evidence/giá-trị/ai-chạy/verify)

> TẤT CẢ knob ABSENT ở `site_config.json` (miyano) + `common_site_config.json` → mobile-BE CHƯA go-live. `gunicorn_workers=41` + boot `--preload` (LL-DEPLOY-01 staleness đứng).

| Knob | Hiện trạng (evidence file:line) | Giá trị go-live | Ai chạy | Verify |
|---|---|---|---|---|
| `allow_cors` | ABSENT → CORS OFF. `frappe/app.py:268-269` (`if allowed_origins := conf.allow_cors`) None⇒return sớm; wildcard `:275-280` BỎ lọc + LUÔN echo `Allow-Credentials:"true"` `:283` + echo Origin `:284` = lỗ credential-echo T3 | **native APK → GIỮ OFF (None) hợp lệ.** web/PWA/Swagger/WebView-OAuth → list-origin tường minh. **CẤM wildcard `*` prod** | **[HARD-STOP USER]** | smoke OPTIONS preflight từ origin cho phép |
| `host_name` | ABSENT. `frappe/utils/data.py:1599` (`def get_url`) · `:1605` (`host_name = ...conf.host_name or ...conf.hostname`); vắng ⇒ fallback Host header `:1611-1614` → `protocol + ...site` `:1631` = `http://miyano` nội bộ (camera/QR deep-link KHÔNG mở được). **GUARD-9 machine-check** (`TestSecGateHostNameIssuerDoc`) source-grounded @source + prose-invariant `08 §5.1(f)`/`10 §3`+§6.2(3c0)+§6.3 | public HTTPS host | **[HARD-STOP USER]** | `get_url()` / `openid_configuration issuer == public host` (KHÔNG `http://miyano`) |
| `assetcore_qr_base_url` | ABSENT. `services/imm00.py:635` `_QR_BASE_URL_CONF_KEY`, `_build_qr_url` `:685` | public HTTPS QR base | **[HARD-STOP USER]** | QR deep-link mở được trên thiết bị |
| `allow_error_traceback` | **System Setting (KHÔNG site_config) default=1 (ON)** — `system_settings.json:262-265`. Gate THẬT `frappe/utils/response.py:60-65` `is_traceback_allowed()`; dùng `:36`/`:182`/`:190`/`:203`. PROD hiện LEAK traceback/SQL ở 401/403/429 raw | System Setting → **0** | **[HARD-STOP USER]** | `bench --site <site> execute frappe.utils.response.is_traceback_allowed` trên staging |
| `conf.rate_limit` + nginx | ABSENT → `frappe.local.rate_limiter` KHÔNG instantiate. Gate `frappe/rate_limiter.py:17-19`. Headers emit qua `app.py:256-257` → `rate_limiter.py:82-103` (X-RateLimit-*/Retry-After). ⚠️ `@rate_limit` decorator (`imm00.py:311/354/514`) tự đếm cache `:155-161` → `throw(RateLimitExceededError)` `:163-166` = **429 body-only, NO header** | `conf.rate_limit` global HOẶC nginx `limit_req` inject Retry-After | **[HARD-STOP USER]** | curl >limit → kiểm header Retry-After/X-RateLimit-* |

> **CORS phân biệt TƯỜNG MINH:** native APK MVP → `allow_cors` GIỮ OFF, KHÔNG bật chỉ vì mobile. Cross-ref ADR-MOBILE-004(c).
> **rate-limit 2 đường:** (a) `conf.rate_limit` global cho X-RateLimit-* mọi request; HOẶC (b) nginx `limit_req` inject Retry-After cho oauth2.* + RPC. Decorator-path 429 = body-only no-header (KNOWN).

### 5.2 TO-BUILD + DoD EPIC-G

| Tag | Task |
|---|---|
| `[AUTO]` | Viết KNOB MATRIX (§5.1) vào [`10-deploy-ops.md`](./10-deploy-ops.md) (hoặc chương G) — 5 knob × cột [ABSENT/evidence / go-live / ai-chạy / verify] |
| `[AUTO]` | Thêm `08 §4` checklist + ADR-004 Consequences: item "(b) PROD TẮT `allow_error_traceback` (System Setting=0)" evidence `response.py:60-65` — phủ T-leak. Ghi RÕ KHÔNG phải developer_mode/site_config |
| `[AUTO]` | Sửa file:line rate-limit (gate=`rate_limiter.py:17-19`, KHÔNG `:82-92`=headers) + note decorator-429-no-header |
| `[AUTO]` ✅ | Bồi `10 §2` CORS phân biệt native vs web; **checklist `host_name` vào `10 §6.2` (DONE — item `(3c0)` §6.2 + knob row §3 + invariant note; machine-check GUARD-9)**; CI-guard chặn servers placeholder `REPLACE-WITH-PUBLIC-HOST` (yaml:107) + version skeleton (yaml:89) |
| `[AUTO]` | Ghi RÕ: SAU mọi đổi site_config/System Setting → **[HARD-STOP USER]** `bench restart`/reload (--preload, 41 workers) MỚI live HTTP (LL-DEPLOY-01/04) |

> ✅ **G-A2 closed — G3 AUTO doc-part (2026-06-12):** invariant traceback-gate (hàng 2 bảng trên — "PROD TẮT `allow_error_traceback` (System Setting=0)" evidence `response.py:60-65`, KHÔNG `developer_mode`/`site_config`) NAY có **machine-check drift-guard**: `test_mobile_security_gate.py::TestSecGateTracebackGateDoc` (GUARD-5, 5 TC raw-text STDLIB derive-from-source) assert invariant xuyên `08 §4(b)/§5` + `10 §6.2(6)` + `ADR-004 Consequences`, ground-truth @source `frappe/utils/response.py:60` `is_traceback_allowed` + `:63` `get_system_settings('allow_error_traceback')` (anti stale-evidence), RED-before string-mutate (`System Setting`→`developer_mode` / xoá phủ-định) → RAISE. `test_mobile_security_gate` **16→21 OK** (SSoT `_EXPECTED_SECURITY_GATE_TEST_COUNT=21`); guard-suite gộp 6→7 module (GO-2). Runtime knob (System Setting=0 + reload gunicorn + curl live verify body 401/403/429 no-`Traceback`) = **[HARD-STOP USER]** G-U4/G-U6 — AUTO chỉ check PROSE-mechanism, KHÔNG set runtime knob. doc/test introspection-only, `git diff --stat` api/services/*.py + yaml = TRỐNG.

> ✅ **G-A8 closed — host_name/issuer go-live drift-guard (2026-06-12):** invariant knob #1 `host_name`
> (hàng 2 bảng §5.1 — `host_name` set ⇒ `get_url()`/OIDC `openid_configuration issuer == public host`, KHÔNG
> `http://miyano` nội bộ) NAY có **machine-check** `test_mobile_security_gate.py::TestSecGateHostNameIssuerDoc`
> (GUARD-9, 8 TC raw-text STDLIB derive-from-source). Đóng KNOB-MATRIX invariant CUỐI chưa-guard (4/5 đã có:
> CORS=GUARD-3, traceback=GUARD-5, rate-limit-header=GUARD-7, token-leak/audit=GUARD-6/8; host_name = knob #1
> = LAST). Assert: (1) @source `frappe/utils/data.py:1599 def get_url` + `:1605 host_name = ...conf.host_name or
> ...conf.hostname` + fallback `:1631 protocol + ...site` TỒN TẠI (anti stale-evidence); (2) prose-invariant
> raw-text xuyên `08 §5.1(f)` + `10 §3`/§6.2(3c0)/§6.3 + `EPIC-G §3.3`/§8 R4 — mỗi nơi có `host_name` +
> `get_url()`/`openid_configuration issuer == public host` + phủ-định `KHÔNG http://miyano`; (3) RED-before/
> GREEN-after string-mutate bản-sao (xoá `http://miyano` / flip phủ-định / xoá host_name gate-line @source-derive)
> → guard RAISE; control THẬT → GREEN. `test_mobile_security_gate` **44→52 OK** (SSoT
> `_EXPECTED_SECURITY_GATE_TEST_COUNT=52`, meta-guard `TestSecGateSelfCount`); cross-module count-parity:
> `test_mobile_docset` `_GUARD_SUITE_SUM` 273→281 + `_MOBILE_OAS_TOTAL` 299→307 + `_GUARD_SUITE_EXPECTED[sec-gate]`
> 44→52. Live `get_url()`/issuer == public host + curl `openid_configuration issuer` = **[HARD-STOP USER]**
> G-U2/G-U6. doc/test introspection-only, `git diff --stat` api/services/*.py + yaml = TRỐNG.

**DoD EPIC-G:** HTTPS reachable ngoài · security gate: no traceback leak · CORS no-wildcard · no token-leak · rate-limit headers (qua conf/nginx) · host_name/issuer go-live (GUARD-9).

---

## 6. EPIC-D — Push FCM (impl)

> Vùng tài liệu: [`06-push-fcm.md`](./06-push-fcm.md) (spec 327 dòng) + ADR-MOBILE-002 (Accepted — FCM Admin SDK HTTP v1 TRỰC TIẾP, KHÔNG relay Frappe Cloud).
> **Trạng-thái-hiện-hành @F-B2 2026-06-12 (re-verify @source — reconcile stale Vòng-19 snapshot):** **D1/D2/D4-handler/D5/D6/D7 = AUTO-part ĐÃ IMPL @source** (DocType json · `services/mobile_device_token.py` · handler `api/mobile/v1/device_token.py` · sender `utils/fcm.py:272` `send_fcm_message` · RBAC `permissions.py:268/285`+`hooks.py:395/404`). **D6 = AUTO-part ĐÃ ĐÓNG (KHÔNG còn mở):** kênh #3 push wired `_dispatch:416`→`_dispatch_push` (def `:457`, fan-out token enabled=1 + fail-safe try/except `:512`) · `@rate_limit(seconds=60, ip_based=True)` register `device_token.py:62` (decorator-order whitelist-NGOÀI/rate_limit-TRONG, guard `test_mob_oas_22j`). Re-verify @F-B2: `grep -ciE 'fcm\|push' notifications.py`=**18** (KHÔNG 0) · `grep -ciE 'rate_limit' device_token.py`=**7** (KHÔNG 0); test `test_mobile_device_token` **62 OK (10 skip DB-write chờ migrate)** + `test_mobile_oas` **141 OK** @source G3 2026-06-12. **CÒN MỞ = CHỈ HARD-STOP USER:** `site_config.fcm_*` creds + `bench migrate` (table live) + reload gunicorn (xem bảng §6.3 2 dòng `[HARD-STOP USER]`). Chi tiết: [`completion/EPIC-D-push-fcm.md §4 D6 + §5.5`](./completion/EPIC-D-push-fcm.md).
>
> **`[SUPERSEDED]` snapshot Vòng 19 2026-06-12 (giữ audit-trail tiến độ — KHÔNG đọc như trạng-thái-hiện-hành):** từng ghi "**D6 = task AUTO DUY NHẤT còn mở**" với evidence `grep fcm\|push notifications.py`=**0** + `grep rate_limit device_token.py`=**0**. Evidence ĐÃ lật @source (18 / 7) — D6 AUTO-part đã impl sau snapshot. Thay bằng trạng-thái-hiện-hành ở trên @F-B2.

### 6.1 Điểm dispatch hiện tại

- `services/notifications.py:366` `_dispatch` = **1 điểm fan-out duy nhất, CHỈ 2 KÊNH:** in-app `enqueue_create_notification` `:385` (Notification Log Alert = audit NĐ98) + email `_safe_sendmail` `:407-409` (chỉ `_user_wants_email()==True` `:251`). **KHÔNG có kênh push.**
- 7 call-site `_dispatch`: `:452 :498 :562 :627 :791 :931 :1116` → chèn kênh #3 tại `:366` phủ cả 7 event, KHÔNG sửa call-site.
- E3 `notify_incident_created` `:506` wired @`hooks.py:270` (Incident Report after_insert) = **MVP trigger báo hỏng**.

### 6.2 GAPS (chặn flow-6) — ✅ RECONCILED @F-B2 2026-06-12 (AUTO-part đã đóng @source)

> **Trạng-thái-hiện-hành @F-B2:** mọi GAP `[AUTO]` dưới ĐÃ ĐÓNG @source (re-verify `find`/`grep`). Chỉ còn 2 GAP `[HARD-STOP USER]` (creds + migrate/reload). Snapshot "CHƯA/∄" cũ giữ làm `[SUPERSEDED]` audit-trail bên dưới.

- ✅ **(ĐÓNG)** DocType AC Mobile Device Token ĐÃ tạo: `assetcore/assetcore/doctype/ac_mobile_device_token/{json,py,__init__}` (7 field, autoname=hash, `fcm_token` UNIQUE, track_changes=1).
- ✅ **(ĐÓNG)** `register/unregister_device_token`: yaml typed (D4 §8.9 Decision-B oneOf, 0 STUB) **+ handler ĐÃ impl** `api/mobile/v1/device_token.py` (`@whitelist methods=[POST]` wrap service D2; register thêm `@rate_limit:62`).
- ✅ **(ĐÓNG)** RBAC wiring ĐÃ đăng ký `hooks.py:395/404` (`ac_mobile_device_token_query` + `ac_mobile_device_token_has_permission` self-scope, def `permissions.py:268/285`).
- ✅ **(ĐÓNG)** Kênh #3 push ĐÃ chèn `_dispatch:416`→`_dispatch_push:457` (fan-out token enabled=1 + fail-safe). FCM HTTP v1 sender ĐÃ có `utils/fcm.py:272` `send_fcm_message` (STDLIB tự-ký SA JWT — `_sign_jwt:158`/`_fetch_access_token:189`, KHÔNG lib firebase-admin → STDLIB-only guard giữ). Audit register/unregister wire qua `log_audit_event` (service D2). Rate-limit register ĐÃ impl `device_token.py:62`.
- ⚠️ **(CÒN — HARD-STOP USER)** `site_config.fcm_service_account_path`/`fcm_project_id` ABSENT → `send_fcm_message` no-op (push skip, in-app/email VẪN gửi); `bench migrate` (table live) + reload + e2e OAuth-bearer-reach `api/mobile/v1` (Phụ thuộc B / B2) chờ go-live.

> **`[SUPERSEDED]` snapshot Vòng 19 (audit-trail — KHÔNG đọc như hiện-hành):** từng ghi DocType "CHƯA tạo (folder ∄)" · handler "CHƯA impl (`api/mobile/v1/` ∄)" · RBAC "CHƯA đăng ký" · kênh #3 "CHƯA chèn" + "grep fcm `.py` = 0" · rate-limit "chưa impl". Mọi claim ĐÃ lật @source (`find`/`grep` @F-B2). Reconcile bởi F-B2 doc-only.

### 6.3 TO-BUILD EPIC-D (Phase E)

> **Trạng-thái-hiện-hành @F-B2 2026-06-12 (re-verify @source — reconcile stale Vòng-19 BA-GATE):** D1/D2/D4-handler/D5/**D6**/D7 **AUTO-part ĐÃ IMPL** (`find assetcore -iname "*device_token*"` = `doctype/ac_mobile_device_token/` + `services/mobile_device_token.py` + `api/mobile/v1/device_token.py` + `tests/test_mobile_device_token.py`; sender `utils/fcm.py:272`). **DoD-gate D6 ĐÃ THỎA @source:** `grep fcm|push notifications.py`=**18 (>0)** ✅ + `_dispatch_push` kênh #3 `:457` ✅ + `@rate_limit` register `device_token.py:62` ✅ + TC `test_mobile_device_token` **62 OK** + `test_mobile_oas` **141 OK** ✅. Bảng TO-BUILD dưới = **spec build SSoT (audit-trail hợp đồng impl)** — hàng `[AUTO]` NAY ĐÃ ĐÓNG @source; CHỈ **2 hàng `[HARD-STOP USER]`** (creds `site_config.fcm_*` + `bench migrate`/reload) CÒN MỞ.
>
> **`[SUPERSEDED]` snapshot Vòng 19 2026-06-12:** từng ghi "**CÒN MỞ = D6**" + "KHÔNG tick DONE tới khi `grep fcm|push notifications.py`>0". Điều kiện ĐÃ thỏa @source (grep=18) — D6 AUTO-part đóng. Giữ dòng này làm audit-trail tiến độ, KHÔNG đọc như trạng-thái-hiện-hành.

| Tag | Task |
|---|---|
| `[AUTO]` | DocType `assetcore/doctype/ac_mobile_device_token/` (__init__/.json/.py delegate). 7 field [`06 §2.1`]: `user` Link reqd · `fcm_token` UNIQUE reqd · `platform` Select android/ios reqd · `device_label` · `app_version` · `last_seen` Datetime · `enabled` Check default 1. autoname=hash. track_changes=1. Perm: System Manager read-all + field-tech self |
| `[AUTO]` | Service `services/mobile_device_token.py` (3-tier): `register_device_token(*, fcm_token, platform, device_label='', app_version='')` ÉP `user=frappe.session.user` (KHÔNG nhận từ client §5.3); UPSERT dedup theo fcm_token (§2.4); `unregister_device_token(fcm_token)` set enabled=0 giữ audit (§2.5); `invalidate_token(fcm_token)`. Require bearer (KHÔNG cap mới, self-service §2.3). Gọi `log_audit_event` register/unregister (NĐ98 §5.4) |
| `[AUTO]` D4 | **yaml-part ✅ DONE+GREEN (Vòng 17):** requestBody `DeviceTokenRequest` (fcm_token reqd/platform enum[android,ios]/device_label?/app_version?) oneOf json+form + 200 typed oneOf `[<Created>, Error]` closed-schema **Decision-B route-by-VALUE, 0 discriminator**; `_STUB_PATHS=∅`; `test_mobile_oas` **131 OK** + `TestMobileDeviceTokenTyped` 9 TC; yaml + 04 §8.9 + ADR-IMM00-OPENAPI §D-OAS-DEVTOK. **handler-part ⏳ PENDING:** `api/mobile/v1/__init__.py` + `device_token.py` (`@whitelist methods=[POST]`, KHÔNG allow_guest; function-name == operationId; chỉ wrap service D2 qua `handle`, ÉP user=session) |
| `[AUTO]` | RBAC wiring `hooks.py`: thêm `AC Mobile Device Token` vào `permission_query_conditions` (self-scope) + `has_permission` (vendor isolation `_VENDOR_ROLE` pattern `permissions.py:46/90/188`). **Same-commit wiring gate** |
| `[AUTO]` | Chèn KÊNH #3 push `_dispatch` SAU kênh 1+2: per user dedupe → tra device-token enabled=1 → gửi FCM HTTP v1. Payload [`06 §4.1`] (title/body VI strip-HTML ≤1000 + data{doctype,name,event,deeplink}). Lỗi FCM fail-safe (try/except + log_error, KHÔNG vỡ in-app/email — pattern `_safe_sendmail`) |
| `[AUTO]` | Sender `utils/fcm.py`: đọc `site_config` (`fcm_service_account_path`/`fcm_project_id`) — firebase-admin HOẶC REST HTTP v1 + ký OAuth2 SA (quyết Phase E kèm test); lỗi UNREGISTERED/404 → `invalidate_token()`. KHÔNG log credentials |
| `[AUTO]` | Rate-limit register (§5.3/§5.5) theo `@rate_limit` (`imm00.py:311/354`) |
| `[AUTO test]` | `tests/test_mobile_device_token.py`: upsert dedup · ÉP user=session (spoof chặn) · self-scope · unregister enabled=0 · invalidate-on-401 · `_dispatch` fan-out push đúng token enabled (mock FCM) · audit record. Update `test_mobile_oas` (gỡ 2 STUB + assert typed) |
| `[HARD-STOP USER]` | `site_config`: `fcm_service_account_path` + `fcm_project_id` (cùng nhóm allow_cors/qr_base_url); đăng ký Firebase project; cho phép outbound HTTPS `fcm.googleapis.com`. Runbook + rollback xoay key [`10 §4`](./10-deploy-ops.md) |
| `[HARD-STOP USER]` | `bench migrate` (DocType mới) + `bench restart`/reload (`api/mobile/v1` + `_dispatch` sửa) |

**DoD EPIC-D:** báo hỏng → KTV được giao nhận push; test xanh (mock FCM + audit + self-scope).

---

## 7. EPIC-V — Codegen Verify + Handoff

> Vùng tài liệu: [`09-native-repo-guide.md`](./09-native-repo-guide.md) + [`11-phase-a-exit.md §1`](./11-phase-a-exit.md) (matrix) + `openapitools.json`. **CHỈ viết .md** — KHÔNG sửa api/services/yaml-path/operationId.

### 7.1 Toolchain status (probed THẬT — KHÔNG tuyên bố "verified" khi chưa chạy)

- `which java` = **NOT FOUND** (re-probe @2026-06-11). `npx --no-install @openapitools/openapi-generator-cli version` = **canceled** (`@openapitools/openapi-generator-cli@2.35.0` chưa cài, no auto-install). ⇒ codegen THẬT KHÔNG chạy được trong env này. Cả 2 lý do (no JDK + generator chưa cài) = **[HARD-STOP USER cài]** HOẶC chạy ở máy build Phase-D. **C5 codegen-dry + C-DoD-CFG config-validity introspection PyYAML/json = proxy CHÍNH-THỨC** cho codegen-DoD (`test_mobile_oas` **141 OK** count HIỆN HÀNH @source G3 2026-06-12; `_EXPECTED_TEST_COUNT=141` SSoT; guard-suite 7-module tổng **281 OK** re-run @source G3 2026-06-12 · `TestMobileCodegenDryDoD` 10 TC: 0 Stub-on-MVP + 0 dangling + mọi MVP typed · `TestMobileCodegenConfig` 10 TC: `openapitools.json` runnable-config ↔ YAML SSoT).
- `openapitools.json` = **NAY runnable-config** (chuẩn bị V handoff): `generator-cli.version: 7.23.0` + block `generators` 3 target trỏ `docs/mobile/openapi/assetcore-mobile.openapi.yaml` — `mobile-dart` (`dart-dio`), `mobile-kotlin` (`kotlin`, `library: jvm-retrofit2`), `mobile-typescript` (`typescript-axios`). USER cấp `java`+`npx` → `npx @openapitools/openapi-generator-cli generate` (đọc config, sinh cả 3 vào `build/codegen/<lang>`). KHÔNG còn bare version-pin.
- **KOTLIN gap — ĐÓNG:** `openapitools.json` nay khai Kotlin là target THẬT (`mobile-kotlin`). EPIC-V V-U1/V-U2 verify Dart+Kotlin (+ TypeScript bonus). Sample/config docset bổ sung khi USER cấp toolchain (EPIC-V).

### 7.2 GAPS

- ✅ **ĐÓNG (V3 DONE 2026-06-12):** field-tech E2E runbook hợp nhất = chương [`14-e2e-field-tech-runbook.md`](./14-e2e-field-tech-runbook.md) (login→scan→báo hỏng→WO→phiếu→push như 1 sequence chạy-được; 6 operationId trục + curl/dart + expected envelope + tag AUTO/HARD-STOP). `[SUPERSEDED]` "KHÔNG có runbook hợp nhất" — coverage cũ phân mảnh (`11 §1` matrix design-time · `10 §6` smoke · `09 §6.2` 1 dòng) NAY hợp nhất vào chương 14.
- ✅ 4 STUB typed (C2) + list-element typed **field-disjoint 2 item-schema (C3-split)** + **userinfo/whoami = path `getUserInfo` (C4 — codegen sinh method whoami)** ⇒ flow-1/2/4/5 deser typed. flow-6 push CHỜ EPIC-D + FCM creds. **C5+C6+F-C2+C-DoD-CFG DoD codegen-dry+config-validity AUTO-part = DONE** (introspection proxy PyYAML/json XANH, `test_mobile_oas` **141 OK** count HIỆN HÀNH @source G3 2026-06-12, `_EXPECTED_TEST_COUNT=141` SSoT, guard-suite 7-module tổng **281 OK** re-run @source G3 2026-06-12); CHỈ codegen Dart/Kotlin **THẬT** = HARD-STOP USER (java/npx) → gate EPIC-V.
- Handoff bundle documented (`09`) nhưng CHƯA đóng gói artifact tường minh (zip/manifest yaml+base-url+auth-guide+example).

### 7.3 TO-BUILD + DoD EPIC-V

| Tag | Task |
|---|---|
| `[AUTO]` ✅ **DONE 2026-06-12** | Viết chương E2E runbook field-tech [`14-e2e-field-tech-runbook.md`](./14-e2e-field-tech-runbook.md): 6 flow tuần tự, curl/dart-client mỗi bước, expected envelope (success+code+http_status route-by-VALUE), tiền-điều-kiện (OAuth Client+bearer), tag `[AUTO]` vs `[HARD-STOP USER]`. Bám matrix `11 §1` + smoke `10 §6.3` + quirk `04 §5` + refresh-on-401 `03 §2.5`. Index parity README/00-overview GREEN (`test_mobile_docset` 9 OK). |
| `[AUTO]` | Ghi RÕ toolchain status THẬT (§7.1) — KHÔNG tuyên bố "codegen verified" khi chưa chạy |
| `[AUTO+BA]` ✅ **CHỐT 2026-06-12 (V3-BA)** | Kotlin vs TypeScript = **GIỮ "Dart bắt buộc; Kotlin/TS theo `openapitools.json`"** (KHÔNG narrow "Dart + TypeScript"): `openapitools.json` khai 3 generator THẬT gồm `mobile-kotlin` ⇒ Kotlin = codegen-target hợp lệ (DoD "Dart/Kotlin" thoả ở config). Prose-sample `09` = Dart+TS; Kotlin config-only. Chi tiết [`09 §1.1`](./09-native-repo-guide.md) note V3-BA. |
| `[AUTO]` | Bổ sung `openapitools.json` generator-config runnable (input=yaml, output, generatorName) HOẶC `tool/gen-client.sh` mẫu (illustrative) — KHÔNG để config rỗng |
| `[AUTO]` | Mục "gói handoff": (1) yaml copy + version pin · (2) base-url ENV (dev localhost:8000 / prod HTTPS placeholder) · (3) link `03` auth + `04` envelope-quirk · (4) ví dụ 1 call đã-gen + đọc `body.success`/`body.code`. Manifest checklist cho [PM] tick |
| `[QA→CI]` | Guard test: khi toolchain có ở CI, assert gen Dart (+Kotlin nếu chốt) chạy 0-error + 0 dangling `$ref` + sinh 15 operationId method; trước đó giữ PyYAML proxy |

**DoD EPIC-V:** 1 client gen-ra gọi được cả 6 flow trên cloud; runbook validated.

---

## 8. Blockers — AUTO vs HARD-STOP (handoff gate)

> BE KHÔNG tự chạy bất kỳ dòng nào ở cột HARD-STOP. Đây là ranh giới handoff cho USER + orchestrator.

| # | Blocker | Loại | Mở khi |
|---|---|---|---|
| 1 | RELOAD gunicorn (`--preload`, boot Mon Jun 8 08:32) — mọi sửa `api/*.py`/`services/*.py` SAU 08:32 chỉ live ở `run-tests`/`execute`, CHƯA live HTTP | **[HARD-STOP USER]** | USER `bench restart`/reload |
| 2 | `bench migrate` — OAuth Client/Bearer Token native + device-token doctype + bust `ac_caps::*` (v95→v97) | **[HARD-STOP USER]** | USER `bench migrate` |
| 3 | `site_config` go-live — `allow_cors` list / OAuth Client / `assetcore_qr_base_url` / FCM creds / rate-limit (B-1..B-8 + 5 knob §5.1) | **[HARD-STOP USER]** | USER set site_config (preflight gate B-1) |
| 4 | Toolchain codegen — JDK + `@openapitools/openapi-generator-cli` chưa cài | **[HARD-STOP USER]** | USER cài HOẶC máy build Phase-D |
| 5 | USER COMMIT — toàn bộ mobile-BE batch UNCOMMITTED (working tree `??`) | **[HARD-STOP USER]** | USER commit (BE KHÔNG auto-commit) |

**AUTO (factory tự đóng được):** mọi `.md` trong `docs/mobile/` · type 4 STUB + list-element + userinfo trong yaml · DocType+service+api device-token impl (chờ migrate) · `_dispatch` kênh #3 + FCM sender impl (chờ creds/reload) · test mới. **KHÔNG** chạm: commit / migrate / reload / restart / site_config / cài lib.

---

## 9. Traceability — 6 flow MVP × EPIC × DoD-gate

> Xương sống = [`11-phase-a-exit.md §1`](./11-phase-a-exit.md) traceability matrix. Bảng này map flow → EPIC chốt → trạng thái contract.

| Flow | Endpoint (file:line) | operationId | EPIC | Contract status |
|---|---|---|---|---|
| 1 Login | `oauth2.py:74/123/144` + userinfo `:163` | (auth) / getUserInfo | **B** + **C** (userinfo) | auth passthrough ✅; userinfo path `getUserInfo` + `OidcUserInfo` ✅ (C4) |
| 2 Scan QR | `imm00.py:588/631/454` | resolveQrToken / getAssetScanInfo / getAsset | **C** | typed ✅ (C2+C6 — `QrResolveEnvelope`/`AssetScanInfoEnvelope`/`AssetDetailEnvelope`, 200-oneOf closed-schema) |
| 3 Báo hỏng | `imm12.py:71` | reportIncident | **C** | typed ✅ |
| 4 WO PM/CM/Cal | `imm08.py:91` / `imm09.py:35` / `imm11.py:89` | createPmWorkOrder / createRepairWorkOrder / createCalibration | **C** | typed ✅ (cả 3 — repair+cal C1; createPm C2 requestBody BA chốt, dual json+form C4) |
| 5 Phiếu của tôi | `imm08.py:28` / `imm09` / `imm12.py:197` | listPmWorkOrders / listRepairWorkOrders / listIncidents | **C** | typed ✅ (envelope + element — C3-split `Pm`/`RepairWorkOrderListItem` + `IncidentListItem` field-disjoint, KHÔNG còn generic) |
| 6 Push FCM | `notifications.py:366` `_dispatch` + register/unregister | registerDeviceToken / unregisterDeviceToken | **D** | device-token: **service D2 ✅ + yaml D4 ✅ typed (Decision-B)**; handler/kênh#3/sender = PENDING ⚠️ |

**Invariant (DONE-gate spec-contract):** list `count == rows` (count khớp drill theo `permission_query_conditions`) — đã fix dashboard KPI (count==drill, `api/dashboard.py`), list-endpoint riêng cần test confirm persona technician/vendor (backlog STATE).

---

## 10. Việc còn lại (open issues — feed STATE)

- **EPIC-C AUTO-PART DONE → gate EPIC-V (C1-C6 + F-C1 + F-C2 + C3-split DONE+GREEN re-verify @source); còn lại = codegen THẬT HARD-STOP USER gate EPIC-V.** ✅ 4 STUB typed (C2) · ✅ **list-element 2 item-schema field-disjoint `Pm`/`RepairWorkOrderListItem` + `IncidentListItem` (C3-split — KNOWN-GAP "KHÔNG ép chung" ĐÓNG, không còn UNION/Phase-E defer)** · ✅ **userinfo/whoami = path `getUserInfo` + `OidcUserInfo` (C4)** · ✅ `createPmWorkOrder` requestBody chốt (C2; C4 vá dual json+form) · ✅ `$ref`-sibling-required gỡ (R2) · ✅ **C5 DoD codegen-dry AUTO-part** = introspection PyYAML XANH (`TestMobileCodegenDryDoD` `test_mob_oas_23a..e`) · ✅ **C6 read-path oneOf** (`TestMobileRead200OneOfClosed` `24a..d`) · ✅ **F-C1 Swagger UI unwrap** (`www/api-docs.html` §F-C1) · ✅ **F-C2 drift-guard parity** (`TestMobileSpecParityRuntime` `25a..e`) · ✅ **C1-residual prose-residue cleared (Vòng 8) + continuation 18f (Vòng 9)** — 7 prose-residue discriminator trong SSoT yaml + docset (ADR (f) R1, roadmap §3.2/§3.5, 04 §8.2, EPIC-C) gỡ sạch về route-by-VALUE closed-schema; guard raw-text `TestMobileProseResidueDiscriminator` (`26a/b/c` RED-trước GREEN-sau, `103 OK @landing Vòng 8`) **+ guard STRUCTURAL `TestMobileOas18fNoDiscriminatorRouteProse` (3 TC: `test_mob_oas_18f` create/read prose-route + detector-RED-before, bổ-trợ 26a trên parsed-spec — bổ sung Vòng 9 như phần mở rộng prose-residue closure)** · ✅ **C-DoD-CFG codegen-config-validity (`TestMobileCodegenConfig` `28a..j` — `openapitools.json` runnable-config 3 generators ↔ `_MOBILE_YAML` SSoT, RED-before/GREEN-after)** · ✅ **F-C4 state-reconciliation roadmap §3 + stale-line-ref guard (`TestMobileRoadmapStateReconciled` `29a..d` — 4-STUB/15-path stale prose → 16-path/2-device-token, raw-text + cross-check `len(spec.paths)`, RED-before/GREEN-after)** — `test_mobile_oas` = **141 OK** (count HIỆN HÀNH @source G3 2026-06-12, `_EXPECTED_TEST_COUNT=141` SSoT; chuỗi phân-rã lịch-sử: 103 @landing Vòng 8 + 3 TC 18f -> 106 @landing Vòng 9 -> 107 @baseline Vòng 11 -> 108 @F-C3 Vòng 11 (meta-guard `TestMobileOasCountSelfVerify`) -> 118 @C-DoD-CFG Vòng 12 (+10 `TestMobileCodegenConfig`) -> 122 @landing Vòng 13 (+4 `TestMobileRoadmapStateReconciled`) -> 133 @landing F-B 2026-06-12 -> 137 @F-B4 2026-06-12 (+4 `TestMobileRefreshOn401DocGuard`) -> 141 @G3 2026-06-12 (+4 `TestMobileTracebackHardeningDocGuard`); guard-suite 7-module tổng **281 OK** re-run @source G3 2026-06-12). **CHỈ còn:** codegen Dart/Kotlin **THẬT** = `[HARD-STOP USER]` (`java` NOT FOUND + `@openapitools/openapi-generator-cli` chưa cài, re-probe @2026-06-11) → gate sang **EPIC-V** V-U1/V-U2. discriminator-note đóng = **Decision-B** (closed-schema KHÔNG discriminator). **Verdict ĐÓNG BĂNG = EPIC-C AUTO-PART DONE → gate EPIC-V.**
- **F-C2 (EPIC-C): 2-spec divergent — AUTO-part ĐÓNG, port-runtime = backlog Phase-F.** ✅ **AUTO DONE:** ADR-MOBILE-001 (k) chốt **A1 (2-spec-by-design)** — YAML 16-path (3.0.3, mang Decision-B) = SSoT codegen mobile; runtime `openapi.spec` 487-path (3.1.0, Swagger UI, KHÔNG Decision-B → codegen-against-runtime dead-deser) = SSoT human-browse/integrator; KHÔNG hợp nhất + scope-boundary + **drift-guard introspection-only** (`TestMobileSpecParityRuntime` `test_mob_oas_25a..e` — parity 10 mobile-business path: tail+verb+security-class YAML↔runtime). 04 §9b + EPIC-C §F-C2 + checklist C-A12 cập nhật. **HARD-STOP USER = backlog Phase-F:** (1) **port Decision-B vào `openapi_overrides.py`** (A2 — runtime carry `oneOf[Env,Error]`; đụng `api/*.py` ⇒ reload gunicorn `--preload` + re-verify 487-path no-regress); (2) **codegen-against-runtime live HTTP** (gate EPIC-V, cần java+npx + reload); (3) **`create_calibration` thiếu `methods=["POST"]`** `imm11.py:89` → runtime verb=GET vs YAML POST (allowlist trong guard tới khi fix decorator @source + reload).
- **F-C3 (Vòng 11, EPIC-C): count-truth reconciliation + meta-guard count-self-verify — DONE+GREEN, introspection/doc-only.** reconcile count-drift `106 -> 107 @baseline Vòng 11` (re-verify @source: `test_mobile_oas` THẬT = 107, KHÔNG phải 106 như doc Vòng 9 viết) + thêm **meta-guard** `TestMobileOasCountSelfVerify.test_mob_oas_NN_count_matches_ssot` (introspect mọi `TestCase` trong module → đếm method `test*` load-được → assert == `_EXPECTED_TEST_COUNT` SSoT định-nghĩa MỘT LẦN @`test_mobile_oas.py` line ~92) ⇒ count-after-add **107 -> 108 @F-C3 Vòng 11**. C-A1 literal count này dùng `@source` (KHÔNG để literal 106 sai-lệch gây phantom-red trên gate đã tick). RED-before/GREEN-after đã chứng minh (const lệch 999 → RED `108 != 999`; const đúng 108 → GREEN) ⇒ chống tái count-drift về sau (drift = RED ngay). **F-C3 round-1 (meta-guard test_mobile_oas) thêm CHỈ 1 test ⇒ +1 mỗi tổng** — guard-suite 6-module **191 -> 192 OK** (baseline = 107+49+13+11+5+6; KHÔNG phải 190) + mobile/OAS total **200 -> 201 OK** (+`test_mobile_preflight` 9; baseline 200, KHÔNG phải 199). ⚠️ **Doc Vòng 11 trước ghi `190 -> 192`/`199 -> 201` = off-by-one BASELINE (ngụ ý F-C3 thêm 2 test trong khi chỉ thêm 1) — reconciled.** **F-C3 round-2 (cross-module SUM meta-guard):** thêm class `TestMobileGuardSuiteCountParity` (4 TC) vào `test_mobile_docset` (5 -> 9) → introspect `def test` THẬT của cả 6 module + assert sum == SSoT + transition-baseline self-consistency (bắt off-by-one `190 vs 191`) ⇒ guard-suite 6-module **192 -> 196 OK** + mobile/OAS total **201 -> 205 OK**, re-verify @source Vòng 11 2026-06-11 `bench --site miyano run-tests` (docset 9 OK). `git diff --stat` api/*.py + services/*.py + yaml-schema = TRỐNG (KHÔNG reload gunicorn, KHÔNG migrate). Cross-ref ADR-MOBILE-001 (count-truth = source THẬT, không phải mốc lịch-sử). UNCOMMITTED (chờ USER).
- **C-DoD-CFG (Vòng 12, EPIC-C→V): codegen-config-validity guard `openapitools.json` ↔ `_MOBILE_YAML` — DONE+GREEN, test+doc-only.** Đóng GAP: `openapitools.json` NAY là runnable-config (3 generators `mobile-dart`/`mobile-kotlin`/`mobile-typescript`, version `7.23.0`, mỗi cái `inputSpec` trỏ mobile YAML) NHƯNG TRƯỚC Vòng 12 KHÔNG guard nào kiểm → config có thể drift rời YAML (sai path/xoá YAML) mà suite VẪN xanh = handoff codegen FAIL-CÂM máy USER. Thêm class **`TestMobileCodegenConfig`** (`test_mob_oas_28a..j`, +10 TC) — STDLIB `json.load` (KHÔNG java/npx/toolchain): assert version-pin `7.23.0` + `generators` non-empty ≥1 `generatorName` + **MỌI `inputSpec` resolve == `_MOBILE_YAML` SSoT** (single-path, `test_mobile_oas.py:86`, KHÔNG hardcode lại) + file tồn tại + name/output non-empty. **RED-before/GREEN-after** (inject IN-MEMORY deepcopy, file read-only KHÔNG sửa): sai-path→RED (28g), xoá generators→RED (28h), `version=''`→RED (28i), control config-thật→GREEN (28j). Reconcile EPIC-V §3.2 stale prose 'bare version-pin/KHÔNG runnable' → trạng-thái THẬT runnable + tick V1 [AUTO]-part config-non-empty (guard máy-kiểm thay 1-liner thủ công). Count: `test_mobile_oas` **108 -> 118 @C-DoD-CFG Vòng 12** (+10); guard-suite 6-module **196 -> 206 OK** + mobile/OAS total **205 -> 215 OK** — cross-module count-parity giữ bởi `test_mobile_docset::TestMobileGuardSuiteCountParity` (`_GUARD_SUITE_EXPECTED`/`_GUARD_SUITE_SUM`/`_MOBILE_OAS_TOTAL` cập); meta-guard `TestMobileOasCountSelfVerify` (`_EXPECTED_TEST_COUNT` 108→118). Re-run @source Vòng 12 2026-06-11 `bench --site miyano run-tests` (oas 118 OK, docset 9 OK, 6-module 206 OK). `git diff --stat` api/*.py + services/*.py + yaml-schema-path/operationId = TRỐNG (openapitools.json read-only, KHÔNG reload gunicorn, KHÔNG migrate, KHÔNG cài lib — STDLIB json/pathlib). Decision-B intact (0 discriminator). UNCOMMITTED (chờ USER).
- **F-C4 (Vòng 13, EPIC-C): state-reconciliation roadmap §3 (prose trạng-thái-cũ → trạng-thái-hiện-hành) + stale-line-ref guard — DONE+GREEN, doc+test-only.** Đóng GAP: roadmap §3 (CURRENT + TO-BUILD) còn quảng-cáo việc-đã-xong (4 path scan/createPm typed C2 + list-element C3-split) NHƯ việc-cần-làm: §3.1 ghi path-count CŨ (yaml THẬT=16); §3.3 heading + ref `_STUB_PATHS` bằng số-dòng-tuyệt-đối (line-drift CHẾT; symbol thật `set(_DEVICE_TOKEN_FROZEN)`=2 device-token) + 3 hàng nhãn untyped + list-element generic; §3.5 `[AUTO]`/`[AUTO+BA]` rows + §9 matrix nhãn-cảnh-báo. **LÀM (doc):** reconcile §3.1/§3.3/§3.5/§9 → trạng-thái THẬT (16-path; 4 path ✅ typed C2/C6; list-element ✅ C3-split; STUB còn = 2 device-token EPIC-D); gỡ `0.1.0-skeleton` khỏi gap-framing (= CI-guard concern EPIC-G). **LÀM (test):** class **`TestMobileRoadmapStateReconciled`** (`test_mob_oas_29a..d`, +4 TC) — raw-text scan roadmap: 0 anchor stale (chỉ giữ dạng lịch-sử [SUPERSEDED]/@landing) + claim path-count khớp `len(spec.paths)`=16 THẬT + ref `_STUB_PATHS` dạng-SYMBOL (KHÔNG line-tuyệt-đối) + **RED-before/GREEN-after** PROVEN (inject anchor stale vào file/bản-sao → 29a/29d RED; revert → GREEN). Count: `test_mobile_oas` **118 -> 122 @F-C4 Vòng 13** (+4); guard-suite 6-module **206 -> 210 OK** + mobile/OAS total **215 -> 219 OK** — cross-module count-parity giữ bởi `test_mobile_docset::TestMobileGuardSuiteCountParity` (`_GUARD_SUITE_EXPECTED`/`_GUARD_SUITE_SUM`/`_MOBILE_OAS_TOTAL` cập + transition-baseline +Δ(F-C4=4)); meta-guard `TestMobileOasCountSelfVerify` (`_EXPECTED_TEST_COUNT` 118→122). Re-run @source Vòng 13 2026-06-11 (oas 122 OK, docset 9 OK, 6-module 210 OK). `git diff --stat` api/*.py + services/*.py + yaml-schema = **TRỐNG** (introspection-only, KHÔNG reload gunicorn, KHÔNG migrate, KHÔNG cài lib — STDLIB). 5 QUYẾT ĐỊNH KHOÁ bám (Decision-B no-discriminator · device-token=EPIC-D · re-verify @source theo symbol · 2-spec A1 · count-truth=source). UNCOMMITTED (chờ USER).
- **F-B4 (2026-06-12, EPIC-B): REPORT-SHAPE doc↔code drift-guard (B1/B4 acceptance #3) + count-reconcile @source — DONE+GREEN, doc+test-only (re-verify run-only, KHÔNG sửa code). `[count-claim @F-B4-landing — SUPERSEDED @G3+G-A8: oas 137→141 (+4 TC G3 `TestMobileTracebackHardeningDocGuard`), preflight 17→26 (+G-A push/preflight TC), sec-gate 44→52 (+8 G-A8 GUARD-9), guard-suite 6-module 225→7-module 281, mobile/OAS 242→307 — SSoT HIỆN HÀNH `_EXPECTED_TEST_COUNT=141`/`_GUARD_SUITE_SUM=281`/`_MOBILE_OAS_TOTAL=307`, xem §Baseline + C-A1 + GO-2 + roadmap §3.5/§3.6/§7.1]`** Drift-guard `12 §1.2/§1.3` ↔ `preflight.verify_oauth_client()`: class **`TestMobilePreflightReportShapeDocGuard`** (`TC-MOB-PRE-14..17`, +4 TC `test_mobile_preflight`) — 5 report-key (ready/client_count/checks/blockers/checked_client từ output nhánh count==0) `<key>` trong 12 §1.2 + 7 check-field-name (`client_count` ∪ 6 field `_evaluate_client`) `<field>` trong 12 §1.3, expected-set **DERIVE TỪ `preflight.py` runtime** (KHÔNG hardcode literal → preflight đổi field/key mà doc 12 không cập nhật → ĐỎ) + blocker VI 'Chưa có OAuth Client' nguyên-văn + RED-before/GREEN-after PROVEN (`test_17` xoá field/key in-memory → RAISE; khôi phục → GREEN). `test_mobile_preflight` **13 -> 17 OK @F-B4** (+4). **COUNT-RECONCILE @source (F-B current-claim stale):** `test_mobile_oas` **133 -> 137** (SSoT code `_EXPECTED_TEST_COUNT=137 test_mobile_oas.py:132` ĐÃ bump; +4 `TestMobileRefreshOn401DocGuard` F-B2 TC-MOB-OAS-30a..d landed sau F-B-doc) · `test_mobile_preflight` **9 -> 17** (+4 F-B3 + 4 F-B4) · guard-suite 6-module = 137+49+13+11+9+6 = **221 -> 225 OK** · mobile/OAS total = 225+17 = **242 OK**. Đồng-bộ literal: C-A1/§Baseline/GO-2/B-A1 + roadmap §3.5/§3.6 + EPIC-C verdict line. `git diff --stat` api/*.py + services/*.py + yaml-schema + preflight.py = **TRỐNG** (doc+test-only, KHÔNG sửa code, KHÔNG reload gunicorn, KHÔNG migrate, STDLIB-only). EPIC-B AUTO-part B-A1/B-A6(F-B4) = **PASS**. UNCOMMITTED (chờ USER).
- **F-B (2026-06-12, EPIC-B): acceptance reconciliation @source + count-drift fix — DONE+GREEN, doc-only (re-verify run-only, KHÔNG sửa code). `[count-claim SUPERSEDED @F-B4: preflight 9→17, oas 133→137, suite 221→225 — xem F-B4 ở trên]`** RE-VERIFY @source (mốc F-B, ĐÃ bị F-B4 vượt): `test_mobile_preflight` = **9 OK** `@landing F-B` (B-A1 [x]) · `TestMobileOAuthToken` `test_mob_oauth_token_01..05` = **5 OK** subset (B-A2 [x]) · `test_mobile_oas` toàn suite = **133 OK** `@landing F-B` (`_EXPECTED_TEST_COUNT` SSoT) · guard-suite 6-module = 133+49+13+11+9+6 = **221 OK** `@landing F-B`. GREP-VERIFY B-A4 [x]: `grant_type=refresh_token`/`refresh MỘT lần` ≥1 hit MỖI file (`03-auth-oauth2.md` §1.3e/§2.5/§2.6 dòng 110/236/260-272 + `04-api-contract.md` §9d(n) dòng 894-913). **B-A3 reconcile** = preflight verifier READ-ONLY (`[n/a-by-design]` no-helper-write): DB-write OAuth Client = HARD-STOP USER (EPIC-B §3.3/B1) → idempotent-vì-không-ghi-DB; ngữ-nghĩa MỚI = "preflight READ-ONLY chạy nhiều lần count bất biến" (TC-MOB-PRE-09), BỎ yêu-cầu helper-write. **COUNT-DRIFT reconcile** `122 @F-C4 Vòng 13 -> 133 @F-B` (+11 TC landed sau Vòng 13): C-A1 + §Baseline THẬT + GO-2 + roadmap §3.5/§3.6 literal = **133**. `git diff --stat` api/*.py + services/*.py + yaml-schema = **TRỐNG** (re-verify run-only + doc-only, KHÔNG sửa code, KHÔNG reload gunicorn, KHÔNG migrate). EPIC-B AUTO-part (B-A1/B-A2/B-A4 [x] + B-A5 [x] + B-A3 reconciled) = **PASS**; B-U1..U4 + B-DoD = `[ ]` **[HARD-STOP USER]** (cloud migrate + tạo OAuth Client THẬT + verify_oauth_client ready=True + smoke PKCE). UNCOMMITTED (chờ USER).
- **EPIC-B:** OAuth Client count=0 (HARD-STOP USER) · token TTL 3600s KNOWN-LIMIT · helper provisioning write = **no-helper-write (reconciled F-B):** DB-write OAuth Client = HARD-STOP USER, preflight verifier READ-ONLY = gate khách quan (idempotent-vì-không-ghi).
- **EPIC-G:** 5 knob ABSENT (allow_cors/host_name/qr_base_url/allow_error_traceback/rate_limit) · `allow_error_traceback`=System Setting default=1 → PROD leak traceback · decorator-429-no-header · CI-guard servers placeholder + version skeleton.
- **EPIC-D:** DocType + service + api/mobile/v1 + RBAC wiring + kênh #3 + FCM sender = 0 code (Phase E) · library FCM chưa chọn · FCM creds HARD-STOP USER.
- **EPIC-V:** toolchain (JDK+generator) chưa cài = **[HARD-STOP USER]** (CHỈ còn lại đây) · ~~`openapitools.json` bare version-pin~~ → **ĐÓNG (Vòng 12 C-DoD-CFG):** NAY runnable-config 3 generators trỏ YAML + guard chống drift `inputSpec`↔YAML (`TestMobileCodegenConfig` 28a..j) · ~~Kotlin vs TypeScript chưa chốt~~ → **ĐÓNG:** config khai cả Kotlin (`jvm-retrofit2`) + TypeScript (`typescript-axios`) là target THẬT · ~~E2E runbook hợp nhất chưa viết (V3)~~ → **ĐÓNG (V3 DONE 2026-06-12):** chương [`14-e2e-field-tech-runbook.md`](./14-e2e-field-tech-runbook.md) (6 flow + 6 operationId trục + curl/dart + expected envelope; docset 9 OK + oas 141 OK) · handoff bundle chưa đóng gói (V4).

---

## Tham chiếu chéo

- Roadmap 6 phase: [`00-overview.md §3`](./00-overview.md) · Index docset: [`README.md`](./README.md)
- EPIC-C: [`04-api-contract.md`](./04-api-contract.md) · `openapi/assetcore-mobile.openapi.yaml`
- EPIC-B: [`03-auth-oauth2.md`](./03-auth-oauth2.md) · [`12-phase-b-preflight.md`](./12-phase-b-preflight.md) · [`ADR-MOBILE-001.md`](./ADR-MOBILE-001.md)
- EPIC-G: [`10-deploy-ops.md`](./10-deploy-ops.md) · [`08-security-compliance.md`](./08-security-compliance.md) · [`ADR-MOBILE-004.md`](./ADR-MOBILE-004.md)
- EPIC-D: [`06-push-fcm.md`](./06-push-fcm.md) · [`ADR-MOBILE-002.md`](./ADR-MOBILE-002.md)
- EPIC-V: [`09-native-repo-guide.md`](./09-native-repo-guide.md) · [`11-phase-a-exit.md`](./11-phase-a-exit.md)
- Exit gate Phase A: [`11-phase-a-exit.md`](./11-phase-a-exit.md)
