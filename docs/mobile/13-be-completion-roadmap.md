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
| 2 | Quét QR → hồ sơ thiết bị | `api/imm00.py:312` resolve_qr_token · `:355` get_asset_scan_info · `:271` get_asset | **C** |
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

- YAML `openapi 3.0.3`, version `0.1.0-skeleton` (yaml:89), 15 path, 15/15 operationId camelCase frozen.
- **Bộ-ba CREATE đã typed ✅:** reportIncident / createRepairWorkOrder / createCalibration — requestBody oneOf (json+form-urlencoded), response `200` oneOf `[Created, Error]` + discriminator `success`, 404/4xx wire grounded `messages.py` http_status.
- **3 LIST đã typed envelope ✅:** `WorkOrderListEnvelope` (data.data[]) + `IncidentListEnvelope` (data.items[]), `Pagination` dùng chung (Option A, ADR-MOBILE-001 g).
- **Guard:** `test_mobile_oas` xanh (0 dangling `$ref`; orphan ⊆ `_RESERVED_ORPHANS`).

### 3.2 P1 — `in-handler-error-on-HTTP-200` (ĐÃ XÁC MINH @source — ADR đã CHỐT)

**Cơ chế:** service `nthrow(MSG.X)` (`utils/notify.py:61-87`) → `ServiceError(http_status=entry['http_status'])` (`services/shared/errors.py:36-42`) → `handle()` bắt (`utils/api_handler.py:48-51`) → `_service_error_to_envelope` (`:54-69`) → `_err(...,http_status=e.http_status)` (`utils/response.py:95-154`). **Body chứa `code`+`http_status` (`response.py:133-138`) NHƯNG HTTP status-line VẪN 200** (`handle` return dict; `hooks.py` no `after_request`).

**ADR (đã CHỐT trong yaml):** response `"200"` = `oneOf [<Created>, Error]` + `discriminator: success` → client route theo field `success`, KHÔNG theo status-line. Đã áp 3 CREATE path.

**Bằng chứng từng path (file:line):**

| Path | 403 shape | in-handler errors (svc) | return |
|---|---|---|---|
| `imm12.report_incident` | **DUAL** — guest 401 `imm12.py:92` = DEAD-CODE over HTTP (dispatcher-403 trip trước, [`04 §5`](./04-api-contract.md)); cap-403 `imm12.py:96` = HTTP-200+Error | 422 BR-12-01 clinical_impact `services/imm12.py:359` (`messages.py:754`); 404 asset∄ `services/imm12.py:361` (`messages.py:747`) | `{name,status,severity}` `imm12.py:410` |
| `imm09.create_repair_work_order` | **SINGLE** — `rbac.require('repair.create')` `api/imm09.py:40` → PermissionError HTTP-403 THẬT | 404 `services/imm09.py:746` (`messages.py:716`); 409 HAS_OPEN_WO `:753` (`messages.py:667`) | `{name,status,sla_target_hours}` `imm09.py:771` |
| `imm11.create_calibration` | **SINGLE** — `rbac.require('calibration.create')` `api/imm11.py:95` | 404 `services/imm11.py:999` (`messages.py:848`); 409 ASSET_BLOCKED CAL-008 `:1002` (`messages.py:855`) | `{name,status=Scheduled}` `imm11.py:1013` |

> **2 loại 403 (DONE-gate spec-contract):** (a) **dispatcher-403** = guest/no-token, raise tại `is_whitelisted` `frappe/__init__.py:876` → HTTP-403 + `FrappeRawError`. (b) **in-handler cap-403** = thiếu capability, `_err(...,403)` → HTTP-200 + Error envelope. Client phân biệt bằng **HTTP status-line** (KHÔNG anyMatch oneOf). Xem [`04 §5a/§5b`](./04-api-contract.md).

### 3.3 GAPS — 4 STUB path còn lại (chưa typed)

> Source-truth `_STUB_PATHS` @ `assetcore/tests/test_mobile_oas.py:152-157` (4 path còn lại). YAML 200→`#/components/responses/Stub`.

| # | Path | yaml | Source | Lý do GIỮ STUB |
|---|---|---|---|---|
| 1 | resolveQrToken | :1268 | `api/imm00.py:312` `resolve_qr_token(token="")` · `@rate_limit:311` (→429) · `rbac.require("asset.read"):339` · 404 `:343` · vendor-IDOR 403 `:347` | response chưa typed |
| 2 | getAssetScanInfo | :1280 | `api/imm00.py:355` · `@rate_limit:354` (→429) · build qua `services/imm00.py:538` `build_asset_scan_info` → 12 field (`:567-602`) | response chưa typed |
| 3 | getAsset | :1292 | `api/imm00.py:271` `get_asset(name)` · 404 `:274` · vendor-IDOR `:277-279` · return `_ok(_strip_qr_token(doc.as_dict()))` `:307` + enrich `:290-293`/overdue `:301-303` | KHÔNG declare 401/403/429 — chỉ 200 |
| 4 | createPmWorkOrder | :1368 | `api/imm08.py:91` `create_pm_work_order()` (untyped `_form_dict()` `:17`) · `rbac.require pm.create:92` · `svc.create_adhoc_work_order(data)` `services/imm08.py:787` · required `("asset_ref","pm_schedule","due_date")` `:788` · return `{name,status,checklist_items_count}` `:836-840` | signature untyped → chưa typed requestBody |

**Field thật cho list-element (CHƯA typed — element = `type:object` generic, yaml:443/463):**

- **PM** (`services/imm08.py:531-533`): `[name, asset_ref, pm_type, wo_type, status, due_date, completion_date, assigned_to, supervisor, overall_result, is_late, source_pm_wo]` + enrich `asset_name`/`location_name` (`:566-567`).
- **CM** (`services/imm09.py:675-681`): `[name, asset_ref, asset_name, repair_type, priority, status, open_datetime, completion_datetime, mttr_hours, sla_breached, sla_target_hours, is_repeat_failure, assigned_to, root_cause_category, risk_class, parts_hold_hours, parts_hold_started]`.
- **Incident** (`services/imm12.py:750-756`): `[name, asset, incident_type, severity, status, fault_code, reported_by, reported_at, description, linked_capa, linked_repair_wo, rca_required, rca_record, chronic_failure_flag, patient_affected, closed_date, assigned_to, acknowledged_at, resolved_at, response_breached, resolution_breached, response_due_at, resolution_due_at]` + `_enrich_asset_names`/`_enrich_sla_breach` (`:761/:763`).

> **PM ≠ CM field-set:** 2 envelope CHIA SẺ `WorkOrderListEnvelope` nhưng FIELD KHÁC → cân nhắc 2 item-schema `PmWorkOrderListItem` / `RepairWorkOrderListItem` (KHÔNG ép chung 1 item).

### 3.4 userinfo / whoami (OIDC) — gap field-tech "hiển thị danh tính"

- YAML hiện CHỈ có scope `openid` securityScheme (yaml:148-150) — **KHÔNG có path RPC**.
- Endpoint Frappe = `frappe/integrations/oauth2.py:163-164` `openid_profile` (`@whitelist`, **KHÔNG allow_guest** → cần bearer) → `create_userinfo_response` → OIDC claims.
- **`[AUTO+VERIFY]`** xác minh `openid_profile` / `openid_configuration` @ v15.107.2 → thêm path + operationId `getUserInfo`/`whoami` + response schema. Nếu KHÔNG có endpoint chuẩn → ghi `open_issue` cho BA.

### 3.5 TO-BUILD EPIC-C

| Tag | Task |
|---|---|
| `[AUTO]` | Viết doc BE-completion vùng C (đề xuất `docs/mobile/be-completion/C-api-contract.md` HOẶC tích hợp §3 file này): liệt kê 4 STUB + `_STUB_PATHS` guard + chứng cứ P1 — **CHỈ .md** |
| `[AUTO]` | Type 4 STUB response: `ResolveQrResponse` · `AssetScanInfoResponse {…12 field + available_actions:AvailableAction[]{key,label,route,enabled,reason}}` (`services/imm00.py:567-602`) · `AssetDetailResponse` (as_dict enrich + overdue). Wire 200-oneOf[Created,Error]+discriminator + 404 in-handler vào nhánh Error (đồng pattern 3 create) |
| `[AUTO+BA]` | `createPmWorkOrder`: chốt `CreatePmWorkOrderRequest` (required `asset_ref`/`pm_schedule`/`due_date` @`services/imm08.py:788` + optional `pm_type`/`wo_type`/`assigned_to`/`supervisor`/`technician_notes`) + response `{name,status,checklist_items_count}`. **Self-Correction:** required nằm ở service KHÔNG ở `@whitelist` signature → codegen KHÔNG suy được field → **BA chốt requestBody TRƯỚC khi typed**. Cân nhắc đổi `api/imm08.py:91` signature typed → `[HARD-STOP]` reload gunicorn nếu sửa api |
| `[AUTO]` | Type list-element `PmWorkOrderListItem`/`RepairWorkOrderListItem` + `IncidentListItem` thay `type:object` generic |
| `[AUTO+VERIFY]` | Thêm userinfo/whoami OIDC path (§3.4) |
| `[AUTO]` | Cập nhật `test_mobile_oas` + `_STUB_PATHS`/`_EXPECTED`/`_PATHS_REQUIRE_401/403` khi 4 STUB rời + userinfo thêm; chạy `bench --site miyano run-tests --module assetcore.tests.test_mobile_oas` |
| `[AUTO→V]` | Sau 4 STUB typed: smoke `openapi-generator` (Dart/Kotlin) verify 0 dangling `$ref` + mọi path MVP typed (DoD EPIC-C) — thuộc EPIC-V |

### 3.6 DoD EPIC-C

- [ ] `openapi-generator` chạy sạch (Dart/Kotlin) — 0 dangling `$ref`, mọi path MVP typed.
- [ ] `test_mobile_oas` xanh (4 STUB rời + list-element + userinfo).
- [ ] requestBody oneOf json+form mọi RPC path; response `200` oneOf[Created,Error]+discriminator áp đủ 4 STUB.

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

- **DocType "AC Mobile Device Token" CHƯA tồn tại** (grep `device_token`/`fcm_token` toàn assetcore = 0 hit). Chỉ spec BA [`06-push-fcm.md §2`](./06-push-fcm.md) (self-scope qua `permission_query_conditions` + `has_permission user==session.user`; ÉP `user=session.user` chống spoof §5). `register_device_token`/`unregister_device_token` CHƯA impl (Phase E).
- `api/mobile/` CHỈ chứa `__init__.py` + `preflight.py` (KHÔNG `v1/`, KHÔNG `device_token.py`). 2 STUB OpenAPI: yaml:1565 (`registerDeviceToken`) + :1582 (`unregisterDeviceToken`).
- **→ Đây là gap chặn EPIC-D. SINGLE-OWNER = EPIC-D (D1/D2/D4 build DocType + service + endpoint MỘT LẦN).** EPIC-B **B3 = dependency-gate** (chỉ xác nhận bearer→`set_user` reach `api/mobile/v1` qua **B2**), **KHÔNG impl device-token** (tránh build trùng giữa B và D). Impl chi tiết = §6 (EPIC-D).

### 4.4 TO-BUILD + DoD EPIC-B

| Tag | Task |
|---|---|
| `[AUTO]` | Doc "Auth provider sẵn sàng": khẳng định refresh ĐÃ hỗ trợ + TTL 3600s hard-coded (KNOWN-LIMIT) + userinfo=openid_profile — bám file:line §4.1, KHÔNG re-litigate |
| `[AUTO]` | Doc "Provisioning": runbook thủ công `10 §1` + preflight gate = cơ chế DoD; ghi RÕ KHÔNG fixture/patch auto |
| `[ref EPIC-D]` | Device-token DocType + service + `register/unregister_device_token` = **OWNED & impl bởi EPIC-D (D1/D2/D4)**; EPIC-B B3 CHỈ gate dependency (bearer reach `api/mobile/v1`), **KHÔNG impl trùng** |
| `[AUTO]` | Backlog đóng vòng: (a) wire userinfo/whoami vào yaml (§3.4); (b) thêm ví dụ refresh-on-401 sequence vào [`03 §1`](./03-auth-oauth2.md) hoặc `04 §9` |

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
| `host_name` | ABSENT. `frappe/utils/data.py:1605` (`conf.host_name or conf.hostname`); vắng ⇒ fallback Host header `:1611-1614` → `protocol+site` `:1631` = `http://miyano` nội bộ (camera/QR deep-link KHÔNG mở được) | public HTTPS host | **[HARD-STOP USER]** | `get_url()` / `openid_configuration` issuer == host công khai (KHÔNG `http://miyano`) |
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
| `[AUTO]` | Bồi `10 §2` CORS phân biệt native vs web; checklist `host_name` vào `10 §6.2`; CI-guard chặn servers placeholder `REPLACE-WITH-PUBLIC-HOST` (yaml:107) + version skeleton (yaml:89) |
| `[AUTO]` | Ghi RÕ: SAU mọi đổi site_config/System Setting → **[HARD-STOP USER]** `bench restart`/reload (--preload, 41 workers) MỚI live HTTP (LL-DEPLOY-01/04) |

**DoD EPIC-G:** HTTPS reachable ngoài · security gate: no traceback leak · CORS no-wildcard · no token-leak · rate-limit headers (qua conf/nginx).

---

## 6. EPIC-D — Push FCM (impl)

> Vùng tài liệu: [`06-push-fcm.md`](./06-push-fcm.md) (spec 327 dòng) + ADR-MOBILE-002 (Accepted — FCM Admin SDK HTTP v1 TRỰC TIẾP, KHÔNG relay Frappe Cloud). **Push = SPEC-ONLY, CHƯA impl 1 dòng code.**

### 6.1 Điểm dispatch hiện tại

- `services/notifications.py:366` `_dispatch` = **1 điểm fan-out duy nhất, CHỈ 2 KÊNH:** in-app `enqueue_create_notification` `:385` (Notification Log Alert = audit NĐ98) + email `_safe_sendmail` `:407-409` (chỉ `_user_wants_email()==True` `:251`). **KHÔNG có kênh push.**
- 7 call-site `_dispatch`: `:452 :498 :562 :627 :791 :931 :1116` → chèn kênh #3 tại `:366` phủ cả 7 event, KHÔNG sửa call-site.
- E3 `notify_incident_created` `:506` wired @`hooks.py:270` (Incident Report after_insert) = **MVP trigger báo hỏng**.

### 6.2 GAPS (chặn flow-6)

- DocType AC Mobile Device Token CHƯA tạo (folder ∄; spec 7 field [`06 §2.1`](./06-push-fcm.md), autoname=hash §2.2, UNIQUE fcm_token §2.4).
- `register/unregister_device_token` = STUB OpenAPI (yaml:1565/1582), KHÔNG Python impl (folder `api/mobile/v1/` ∄).
- RBAC wiring CHƯA có: `permission_query_conditions` + `has_permission` self-scope chưa đăng ký `hooks.py` (hiện `:390/:397` chỉ Incident Report).
- Kênh #3 push CHƯA chèn `_dispatch`. FCM HTTP v1 sender CHƯA có (grep fcm `.py` = 0; KHÔNG lib firebase-admin/google-auth; KHÔNG đọc `site_config.fcm_*`). Audit register/unregister (NĐ98 §5.4) chưa wire. Rate-limit register (chống spam §5.3) chưa impl. Library FCM chưa chọn (firebase-admin vs REST HTTP v1 tự-ký SA).
- **Phụ thuộc B:** register cần bearer→set_user; chưa e2e xác nhận OAuth bearer reach `api/mobile/v1`.

### 6.3 TO-BUILD EPIC-D (Phase E)

| Tag | Task |
|---|---|
| `[AUTO]` | DocType `assetcore/doctype/ac_mobile_device_token/` (__init__/.json/.py delegate). 7 field [`06 §2.1`]: `user` Link reqd · `fcm_token` UNIQUE reqd · `platform` Select android/ios reqd · `device_label` · `app_version` · `last_seen` Datetime · `enabled` Check default 1. autoname=hash. track_changes=1. Perm: System Manager read-all + field-tech self |
| `[AUTO]` | Service `services/mobile_device_token.py` (3-tier): `register_device_token(*, fcm_token, platform, device_label='', app_version='')` ÉP `user=frappe.session.user` (KHÔNG nhận từ client §5.3); UPSERT dedup theo fcm_token (§2.4); `unregister_device_token(fcm_token)` set enabled=0 giữ audit (§2.5); `invalidate_token(fcm_token)`. Require bearer (KHÔNG cap mới, self-service §2.3). Gọi `log_audit_event` register/unregister (NĐ98 §5.4) |
| `[AUTO]` | API `api/mobile/v1/__init__.py` + handler `register/unregister_device_token` (`@whitelist methods=[POST]`, KHÔNG allow_guest). Function-name = operationId. Gỡ 2 path khỏi `_STUB_PATHS`; bồi requestBody `DeviceTokenRequest` (fcm_token/platform/device_label?/app_version?) + response 200 typed (oneOf json+form) yaml + ADR-IMM00-OPENAPI |
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

- `which java` = **NOT FOUND**. `npx --no-install @openapitools/openapi-generator-cli` = **REFUSED** (pkg chưa cài). ⇒ codegen KHÔNG chạy được trong env này. Cả 2 lý do (no JDK + generator chưa cài) = **[HARD-STOP USER cài]** HOẶC chạy ở máy build Phase-D. PyYAML introspection = proxy hiện tại (`test_mobile_oas` 57 OK · docset/preflight/capability_map 6 OK).
- `openapitools.json` = **bare version-pin** (`generator-cli.version: 7.23.0` + spaces:2) — KHÔNG generator-config (no `-g`/`-i`/`-o`/dart/kotlin target). Không runnable as-is.
- **KOTLIN gap:** EPIC-V DoD ghi "Dart/Kotlin" nhưng docset chỉ phủ Dart (`dart-dio`) + TypeScript (`typescript-axios`) [`09 §1.1/§2`](./09-native-repo-guide.md). KHÔNG có kotlin sample/config → **cần BA xác nhận** Kotlin có thật là target (native Android thuần?) HOẶC narrow DoD về "Dart + TypeScript".

### 7.2 GAPS

- KHÔNG có field-tech E2E runbook hợp nhất (login→scan→báo hỏng→WO→phiếu→push như 1 sequence chạy được). Coverage phân mảnh: `11 §1` = traceability matrix (design-time) · `10 §6` = go-live smoke curl · `09 §6.2` = 1 dòng "build APK + smoke 1 luồng".
- 4 STUB path còn generic-data → flow-2 (scan) + flow-4 (PM) KHÔNG deser typed tới khi EPIC-C đóng. List-element generic → "phiếu của tôi" rows untyped. userinfo/whoami chưa là path → KHÔNG gen method whoami. flow-6 push CHỜ EPIC-D + FCM creds.
- Handoff bundle documented (`09`) nhưng CHƯA đóng gói artifact tường minh (zip/manifest yaml+base-url+auth-guide+example).

### 7.3 TO-BUILD + DoD EPIC-V

| Tag | Task |
|---|---|
| `[AUTO]` | Viết chương E2E runbook field-tech (đề xuất `docs/mobile/14-e2e-field-tech-runbook.md` HOẶC mục mới `09`): 6 flow tuần tự, curl/dart-client mỗi bước, expected envelope (success+code+http_status), tiền-điều-kiện (OAuth Client+bearer), tag `[AUTO]` vs `[HARD-STOP USER]`. Bám matrix `11 §1` |
| `[AUTO]` | Ghi RÕ toolchain status THẬT (§7.1) — KHÔNG tuyên bố "codegen verified" khi chưa chạy |
| `[AUTO+BA]` | Chốt Kotlin vs TypeScript: (a) thêm sample kotlin vào `09` khớp DoD, HOẶC (b) cập nhật DoD về "Dart + TypeScript" |
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
| 1 Login | `oauth2.py:74/123/144` + userinfo `:163` | (auth) / getUserInfo | **B** + **C** (userinfo) | auth passthrough ✅; userinfo path CHƯA có ⚠️ |
| 2 Scan QR | `imm00.py:312/355/271` | resolveQrToken / getAssetScanInfo / getAsset | **C** | 4 STUB còn generic ⚠️ |
| 3 Báo hỏng | `imm12.py:71` | reportIncident | **C** | typed ✅ |
| 4 WO PM/CM/Cal | `imm08.py:91` / `imm09.py:35` / `imm11.py:89` | createPmWorkOrder / createRepairWorkOrder / createCalibration | **C** | repair+cal typed ✅; createPm STUB ⚠️ (BA chốt requestBody) |
| 5 Phiếu của tôi | `imm08.py:28` / `imm09` / `imm12.py:197` | listPmWorkOrders / listRepairWorkOrders / listIncidents | **C** | envelope typed ✅; list-element generic ⚠️ |
| 6 Push FCM | `notifications.py:366` `_dispatch` + register/unregister | registerDeviceToken / unregisterDeviceToken | **D** | SPEC-ONLY, 0 code ⚠️ |

**Invariant (DONE-gate spec-contract):** list `count == rows` (count khớp drill theo `permission_query_conditions`) — đã fix dashboard KPI (count==drill, `api/dashboard.py`), list-endpoint riêng cần test confirm persona technician/vendor (backlog STATE).

---

## 10. Việc còn lại (open issues — feed STATE)

- **EPIC-C:** 4 STUB chưa typed (resolveQrToken/getAssetScanInfo/getAsset/createPmWorkOrder) · list-element `PmWorkOrderListItem`/`RepairWorkOrderListItem`/`IncidentListItem` chưa typed · userinfo/whoami chưa là path · `createPmWorkOrder` requestBody **BA phải chốt** (required ở service KHÔNG ở signature) · `$ref`-sibling-required ở report_incident.requestBody (P2 codegen-warning) · discriminator-note cho `ReportIncidentForbidden` oneOf (P2).
- **EPIC-B:** OAuth Client count=0 (HARD-STOP USER) · token TTL 3600s KNOWN-LIMIT · helper idempotent write = decision (giữ thủ công + preflight gate).
- **EPIC-G:** 5 knob ABSENT (allow_cors/host_name/qr_base_url/allow_error_traceback/rate_limit) · `allow_error_traceback`=System Setting default=1 → PROD leak traceback · decorator-429-no-header · CI-guard servers placeholder + version skeleton.
- **EPIC-D:** DocType + service + api/mobile/v1 + RBAC wiring + kênh #3 + FCM sender = 0 code (Phase E) · library FCM chưa chọn · FCM creds HARD-STOP USER.
- **EPIC-V:** toolchain (JDK+generator) chưa cài · `openapitools.json` bare version-pin · Kotlin vs TypeScript chưa chốt (BA) · E2E runbook hợp nhất chưa viết · handoff bundle chưa đóng gói.

---

## Tham chiếu chéo

- Roadmap 6 phase: [`00-overview.md §3`](./00-overview.md) · Index docset: [`README.md`](./README.md)
- EPIC-C: [`04-api-contract.md`](./04-api-contract.md) · `openapi/assetcore-mobile.openapi.yaml`
- EPIC-B: [`03-auth-oauth2.md`](./03-auth-oauth2.md) · [`12-phase-b-preflight.md`](./12-phase-b-preflight.md) · [`ADR-MOBILE-001.md`](./ADR-MOBILE-001.md)
- EPIC-G: [`10-deploy-ops.md`](./10-deploy-ops.md) · [`08-security-compliance.md`](./08-security-compliance.md) · [`ADR-MOBILE-004.md`](./ADR-MOBILE-004.md)
- EPIC-D: [`06-push-fcm.md`](./06-push-fcm.md) · [`ADR-MOBILE-002.md`](./ADR-MOBILE-002.md)
- EPIC-V: [`09-native-repo-guide.md`](./09-native-repo-guide.md) · [`11-phase-a-exit.md`](./11-phase-a-exit.md)
- Exit gate Phase A: [`11-phase-a-exit.md`](./11-phase-a-exit.md)
