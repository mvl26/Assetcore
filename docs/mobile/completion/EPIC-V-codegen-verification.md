# EPIC-V — Codegen Verify + Handoff (BE Completion · Mobile)

| Mục | Giá trị |
|---|---|
| EPIC ID (KHÓA — KHÔNG đổi) | **V** — Codegen Verify + Handoff |
| Vị trí trong roadmap | **CHỐT CUỐI** (thứ tự 5/5 — sau C, B∥D-design, G, D) |
| Phụ thuộc | **EPIC-C** (contract codegen-ready) + **EPIC-B** & **EPIC-G** (auth + go-live HTTP) + **EPIC-D** (push, cho flow-6) |
| DoD EPIC-V | 1 client gen-ra gọi được **cả 6 flow** trên cloud; E2E runbook field-tech validated |
| Vùng tài liệu | [`09-native-repo-guide.md`](../09-native-repo-guide.md) · [`11-phase-a-exit.md §1`](../11-phase-a-exit.md) (matrix) · `openapitools.json` · `openapi/assetcore-mobile.openapi.yaml` |
| Phạm vi file này | **doc-only** — KHÔNG sửa `api/*.py` / `services/*.py` / yaml-path/operationId; KHÔNG git commit/push/migrate/reload/restart; KHÔNG cài lib |
| Owner mặc định | **QA** (codegen verify + E2E runbook) — phối **BA** (chốt Kotlin vs TypeScript) |
| Cập nhật | 2026-06-11 — ground @ Frappe v15.107.2, branch `feature/hieuc/core-refinement` |

> **SSoT** = [`13-be-completion-roadmap.md §7`](../13-be-completion-roadmap.md). File này KHÔNG re-litigate 3 quyết định nền (D-AUTH/D-MVP/D-STACK — [`00-overview.md §2`](../00-overview.md)); chỉ MỞ RỘNG §7 thành tasks `V1..V4` khoá-ID + Acceptance kiểm-được + tag AUTO/HARD-STOP.
> **Mọi claim kỹ thuật** có `file:line` evidence verify tại source. Toolchain (`java`/`npx`) đã **probe THẬT** §3 — KHÔNG tuyên bố "verified" khi chưa chạy.

---

## 1. Scope & Mục tiêu

### 1.1 Trong scope (EPIC-V)

EPIC-V là **cổng đóng cuối** của bộ BE-completion: chứng minh hợp đồng OpenAPI (EPIC-C) + auth/go-live (EPIC-B/G) + push (EPIC-D) **thật sự** cho ra 1 API client native gọi được toàn bộ 6 flow MVP field-tech trên public HTTPS host. Gồm 4 task:

| Task | Mục tiêu |
|---|---|
| **V1** | Cấu hình + chạy `openapi-generator` sinh client (Dart, +Kotlin/TS theo §V3-BA chốt) từ yaml; ghi RÕ toolchain status THẬT |
| **V2** | Smoke client gen-ra gọi 6 flow trên cloud staging (sau EPIC-G go-live) |
| **V3** | E2E runbook field-tech: login → scan → báo hỏng → WO → "phiếu của tôi" → push (1 sequence chạy được) |
| **V4** | Gói handoff repo mobile: yaml + auth-guide + base-url + ví dụ 1-call, manifest [PM] tick |

### 1.2 DoD TỔNG EPIC-V

- [ ] 1 client codegen (Dart bắt buộc; Kotlin/TS theo chốt §V3-BA = GIỮ Dart/Kotlin/TS) sinh **0-error · 0 dangling `$ref` · 16 operationId method** từ yaml _(`[SUPERSEDED]` "15 method" — C4 thêm `getUserInfo` ⇒ 16 path @source 2026-06-12)_.
- [ ] Client đó gọi được **6/6 flow MVP** trên cloud (login OAuth2+refresh · scan QR · báo hỏng · WO PM/CM/Cal · phiếu của tôi · push FCM).
- [x] E2E runbook field-tech (V3) **viết đủ** (V-A1 AUTO DONE 2026-06-12 — chương [`14-e2e-field-tech-runbook.md`](../14-e2e-field-tech-runbook.md): 6 flow, 6 operationId trục grep PASS, 0 placeholder, `test_mobile_docset` 9 OK + `test_mobile_oas` 141 OK). _Chạy hết end-to-end trên cloud = V-U5 [HARD-STOP USER]._
- [x] Handoff bundle (V4) đóng gói: yaml + version-pin + base-url ENV + auth-link + ví dụ envelope-read (V-A2 AUTO DONE 2026-06-12 — [`V4-handoff-manifest.md`](./V4-handoff-manifest.md): 4-mục + checklist [PM] §5, 4-key grep 4× OK, `test_mobile_docset` 9 OK). _Tạo repo native THẬT + chạy gen client = Phase D / V-U1 [HARD-STOP USER]._

### 1.3 Out-of-scope (KHÔNG làm — đẩy đúng EPIC/Phase)

- Tạo repo native THẬT + impl 6 luồng UI → **Phase D**, NGOÀI repo `assetcore` ([`09 §0.4`](../09-native-repo-guide.md)).
- Sửa yaml path/operationId → **EPIC-C** (16/16 operationId FROZEN @source; đổi = breaking client). _(`[SUPERSEDED]` "bồi 4 STUB còn lại" — 0 STUB-on-MVP @source 2026-06-12: 4 path C2/C6 đã typed.)_
- Cài JDK / `openapi-generator-cli` / Firebase project → **[HARD-STOP USER]** (xem §3 + V1).
- Offline-sync / manager-approval / đa-module ngoài 6 flow → post-MVP ([`07-offline-sync.md`](../07-offline-sync.md), [`13 §0`](../13-be-completion-roadmap.md)).
- Go-live `site_config` (host/CORS/FCM creds) + commit/migrate/reload → **EPIC-G/B/D + HARD-STOP USER**.

---

## 2. Actor

| Actor | Vai trò trong EPIC-V |
|---|---|
| **QA** (owner chính) | Chạy codegen verify (V1/V2), viết + validate E2E runbook (V3), đóng handoff bundle (V4). Cổng chất lượng: KHÔNG tuyên bố "verified" khi chưa chạy lệnh thật. |
| **BA / System Architect** (mobile) | Chốt Kotlin vs TypeScript có là target thật (V3-BA decision); giữ yaml đồng bộ endpoint (drift-gate). |
| **USER / Admin** (HARD-STOP) | Cài toolchain codegen (JDK + generator) HOẶC cung cấp máy build Phase-D; go-live cloud (EPIC-G) để V2 chạy; commit batch mobile-BE. |
| **Đội repo native** (Phase D) | Đối tượng nhận handoff bundle (V4) — khởi tạo repo, sinh client theo runbook V3. NGOÀI repo `assetcore`. |
| **Field-technician** | Người dùng cuối APK (D-MVP) — KHÔNG thao tác repo; là actor của 6 flow trong E2E runbook (V3). |

---

## 3. Hiện trạng (file:line CHÍNH XÁC — đã probe THẬT)

### 3.1 Toolchain codegen — probe THẬT 2026-06-11 (KHÔNG bịa)

| Probe | Kết quả THẬT | Hệ quả |
|---|---|---|
| `command -v java` | **NOT FOUND** | `openapi-generator` JAR cần JVM → KHÔNG chạy được trong env này |
| `npx --no-install @openapitools/openapi-generator-cli version` | **REFUSED** — `npx canceled due to missing packages` (`@openapitools/openapi-generator-cli@2.35.0` chưa cài) | wrapper npm chưa cài; `--no-install` từ chối tải |
| `node --version` | `v20.20.2` (`/home/miyano/.nvm/.../v20.20.2`) | Node CÓ — đủ chạy npm-wrapper NẾU cài + có JDK |
| `npx --version` | `10.8.2` | npx CÓ |

> ⇒ **codegen KHÔNG chạy được trong env hiện tại** (thiếu JDK + generator chưa cài). Cả 2 = **[HARD-STOP USER cài]** HOẶC chạy ở máy build Phase-D. **PyYAML introspection = proxy hiện tại** (stdlib, KHÔNG cần JVM) — đã PASS làm bằng chứng codegen-validity tới khi có toolchain thật.

### 3.2 `openapitools.json` — RUNNABLE-config (3 generators trỏ mobile YAML)

`openapitools.json` (repo root) NAY là **runnable codegen-config** (KHÔNG còn bare version-pin):

```json
{
  "$schema": "./node_modules/@openapitools/openapi-generator-cli/config.schema.json",
  "spaces": 2,
  "generator-cli": {
    "version": "7.23.0",
    "generators": {
      "mobile-dart":       { "generatorName": "dart-dio",        "inputSpec": "docs/mobile/openapi/assetcore-mobile.openapi.yaml", "output": "#{cwd}/build/codegen/dart" },
      "mobile-kotlin":     { "generatorName": "kotlin",          "inputSpec": "docs/mobile/openapi/assetcore-mobile.openapi.yaml", "output": "#{cwd}/build/codegen/kotlin" },
      "mobile-typescript": { "generatorName": "typescript-axios","inputSpec": "docs/mobile/openapi/assetcore-mobile.openapi.yaml", "output": "#{cwd}/build/codegen/typescript" }
    }
  }
}
```

- = **runnable-config** `generator-cli.version: 7.23.0` + khối `generators` **3 target** (`mobile-dart` `dart-dio` · `mobile-kotlin` `kotlin` `jvm-retrofit2` · `mobile-typescript` `typescript-axios`). Mỗi target có `generatorName` + `inputSpec` trỏ ĐÚNG `docs/mobile/openapi/assetcore-mobile.openapi.yaml` + `output` → `npx @openapitools/openapi-generator-cli generate` đọc config, sinh CẢ 3 vào `build/codegen/<lang>` (KHÔNG cần truyền `-g`/`-i`/`-o` ở CLI).
- **CHỈ còn HARD-STOP USER = toolchain** (`java`/`npx`+generator — §3.1 NOT FOUND @2026-06-11). Config-validity (KHÔNG cần toolchain) = **guard máy-kiểm** `assetcore.tests.guards.test_mobile_oas::TestMobileCodegenConfig` (TC-MOB-OAS-28a..j, STDLIB `json.load`) — assert version-pin + generators non-empty + MỌI `inputSpec` resolve == `_MOBILE_YAML` SSoT (`test_mobile_oas.py:86`) + file tồn tại + name/output non-empty; RED-before/GREEN-after (inject sai-path / xoá generators / version='' → RED). Drift config↔YAML (handoff codegen fail-câm máy USER) = bắt NGAY.
- `$schema` trỏ `./node_modules/...` (chưa cài → schema-resolve fail trong IDE; KHÔNG ảnh hưởng codegen-validity — guard `TestMobileCodegenConfig` STDLIB-only, không cần `$schema` resolve).

### 3.3 Hợp đồng OpenAPI — trạng thái contract (nguồn sinh client)

> **[RECONCILED @source 2026-06-12 — V3-BA reconcile].** Bảng dưới = trạng-thái HIỆN-HÀNH (re-verify @source `openapi/assetcore-mobile.openapi.yaml`). 3 dòng dưới đây từng ghi STALE (`15 path` / `4 STUB còn` / `userinfo CHƯA là path`) — đã cập nhật theo @source + giữ ghi chú `[SUPERSEDED]` cho audit-trail (KHÔNG xoá lịch sử).

| Khía cạnh | Trạng thái @source (re-verify 2026-06-12) |
|---|---|
| Spec | `openapi: 3.0.3` (yaml:1) · `info.title: AssetCore Mobile API` (yaml:88) · `version: 0.1.0-skeleton` (yaml:89) |
| Paths | **16 path** · 16/16 `operationId` camelCase FROZEN — `[SUPERSEDED]` "15 path" (C4 thêm path `openid_profile`→`getUserInfo`; grep `^  /api/method/` @source = 16). |
| servers[0] | **PLACEHOLDER** `https://REPLACE-WITH-PUBLIC-HOST` (yaml:107) — Phase B set host thật ([EPIC-G]) · servers[1] dev `http://localhost:8000` (yaml:109) |
| Bộ-ba CREATE typed ✅ | reportIncident / createRepairWorkOrder / createCalibration — requestBody oneOf json+form, 200 oneOf `[Created, Error]` closed-schema (Decision-B, KHÔNG discriminator), 404/4xx route-by-VALUE body |
| 3 LIST typed envelope ✅ | `PmWorkOrderListEnvelope`/`RepairWorkOrderListEnvelope` (data.data[], item-schema C3-split) + `IncidentListEnvelope` (data.items[]) — "phiếu của tôi" |
| 4 path C2/C6 ✅ all-typed | `[SUPERSEDED]` "4 STUB còn" → 3 read (resolveQrToken/getAssetScanInfo/getAsset) typed 200 oneOf `[<ReadEnvelope>, Error]` closed-schema (C6 read-path P1 closure) + **createPmWorkOrder typed** 200 oneOf `[CreatePmWorkOrderCreatedEnvelope, Error]` (C2). 0 STUB-on-MVP @source. |
| 2 device-token typed ✅ | registerDeviceToken + unregisterDeviceToken = TYPED (D4: requestBody DeviceTokenBody + 200 oneOf `[<Created/Ack>, Error]` closed-schema), name đóng băng A5 — `[SUPERSEDED]` "= STUB" (EPIC-D D4 đã typed). |
| userinfo/whoami ✅ | **LÀ path** `getUserInfo` (`openid_profile`) trong yaml (C4 wired — passthrough RAW OidcUserInfo) — `[SUPERSEDED]` "CHƯA là path". Endpoint Frappe `frappe/integrations/oauth2.py:163-164`. |

### 3.4 Docset codegen-ready proxy (guard máy-đọc — chạy THẬT)

| Test module | #test methods (probe) | Vai trò proxy cho V |
|---|---|---|
| `assetcore/tests/guards/test_mobile_oas.py` | **141** (count HIỆN HÀNH @source G3 2026-06-12 — `Ran 141 tests ... OK`; SSoT `_EXPECTED_TEST_COUNT=141` + meta-guard `TestMobileOasCountSelfVerify`; lineage `[SUPERSEDED]` interim: _106 @landing Vòng 9 → 107 @baseline Vòng 11 → 108 @F-C3 meta-guard → 118 @C-DoD-CFG Vòng 12 → 122 @F-C4 Vòng 13 → 133 @F-B → 137 @F-B4 → **141 @G3 2026-06-12** (+4 `TestMobileTracebackHardeningDocGuard`)_; khớp ACCEPTANCE-CHECKLIST §Baseline) | 0 dangling `$ref` · orphan ⊆ `_RESERVED_ORPHANS` (`:434`) · `_STUB_PATHS` guard (`:152`) · **openapitools.json ↔ `_MOBILE_YAML` config-validity** (`TestMobileCodegenConfig` 28a..j) — codegen-validity proxy |
| `assetcore/tests/guards/test_oas_generator.py` | **49** | envelope/error-code/operationId-unique introspection |
| `assetcore/tests/guards/test_oas_signatures.py` | **11** | signature ↔ yaml param parity |
| `assetcore/tests/guards/test_oas_serve.py` | **13** (count HIỆN HÀNH @source Vòng 9 2026-06-11) | serve `api-docs` + cache-bust on cap-set version |
| `assetcore/tests/guards/test_mobile_docset.py` | **9** (5 cũ + 4 TC F-C3 round-2 `TestMobileGuardSuiteCountParity`) | FS↔index parity + link-health (`TC-MOB-DOC-01..05`) + guard-suite-sum count-parity (06..09) |
| `assetcore/tests/guards/test_mobile_preflight.py` | **26** (count HIỆN HÀNH @source 2026-06-12 — `Ran 26 tests ... OK`; SSoT `_EXPECTED_PREFLIGHT_TEST_COUNT=26` @F-B7 `test_mobile_preflight.py:114` + meta-guard self-count; `[SUPERSEDED]` "9" = base trước F-B3..F-B7) | preflight `verify_oauth_client()` ([EPIC-B] gate) + doc-value/report-shape/blocker-VI/count-self/stale-line-ref guard |
| `assetcore/tests/integration/test_mobile_capability_map.py` | **6** | endpoint↔capability binding (`TC-MOB-CAP-01..06`) |
| `assetcore/tests/guards/test_mobile_security_gate.py` | **52** (count HIỆN HÀNH @source 2026-06-12 — `Ran 52 tests ... OK`; SSoT `_EXPECTED_SECURITY_GATE_TEST_COUNT=52` + meta-guard `TestSecGateSelfCount`; module guard thứ 7 thêm @G-A8 GUARD-9 `TestSecGateHostNameIssuerDoc` host_name/issuer go-live G4(f)) | 9 security invariant introspection (GUARD-1..9: no-traceback-leak · CI-placeholder · CORS-no-wildcard · `http_status`-invariant · traceback-gate · no-token-leak · rate-limit-header · audit-actor NĐ98 · host_name/issuer go-live) |

> **Guard-suite total (re-run @source G-A8 2026-06-12):** guard-suite **7-module** (oas+generator+serve+signatures+docset+capability_map+**security_gate**) = 141+49+13+11+9+6+52 = **281 OK** (byte-match SSoT `test_mobile_docset.py:517 _GUARD_SUITE_SUM=281`), +`test_mobile_preflight` 26 = **307 mobile/OAS** (byte-match `test_mobile_docset.py:543 _MOBILE_OAS_TOTAL=307` + ACCEPTANCE-CHECKLIST §Baseline + GO-2). _`[SUPERSEDED]` interim (audit-trail, KHÔNG current-truth): Vòng 12 6-module 118+49+13+11+9+6 = 206 OK / +preflight 9 = 215 mobile/OAS. Reconcile @source G-A8: sec-gate ENTER guard-suite (module thứ 7, +52 G-A8 GUARD-9 host_name/issuer); oas 118→141 (G-A2/G3 +23); preflight 9→26 (F-B3..F-B7 +17); guard-suite 206→281; mobile/OAS 215→307._ PyYAML/json introspection = **proxy** cho codegen-DoD (KHÔNG codegen THẬT) tới khi USER cấp toolchain `java`+`npx` (re-probe 2026-06-12 = NOT FOUND) → V-U1/V-U2 GIỮ `[ ]`.

### 3.5 Native repo guide — bộ phận handoff ✅ ĐÃ đóng gói artifact (V-A2 DONE 2026-06-12)

- Skeleton repo (Flutter §1.2 / RN §1.3), lệnh gen MẪU (`dart-dio` [`09 §2.1`](../09-native-repo-guide.md) · `typescript-axios` §2.2), ENV BASE_URL (§3), OAuth wiring (§4 → `03`), build APK + CI drift-gate (§5), checklist khởi tạo (§6.2) — **đã có ĐỦ ở `09`**, nay **ĐÃ đóng gói thành artifact tường minh** → **V4 DONE**: [`V4-handoff-manifest.md`](./V4-handoff-manifest.md) (manifest 4-mục: yaml SSoT+version-pin · BASE_URL ENV · auth-link+envelope-quirk · ví dụ 1-call `getAsset` envelope-read; + checklist [PM] §5 mirror `09 §6.2`). yaml giữ DUY NHẤT tại `docs/mobile/openapi/` — manifest TRỎ path + hướng dẫn COPY (chống drift `09 §2.4`), KHÔNG copy yaml ra ngoài.
- **KOTLIN gap — ✅ ĐÓNG (V3-BA decision, 2026-06-12).** `[SUPERSEDED]` "cần BA chốt": `openapitools.json` (SSoT codegen-config) khai **3 generator THẬT** — `mobile-dart` (`dart-dio`) · `mobile-kotlin` (`kotlin`, `library: jvm-retrofit2`) · `mobile-typescript` (`typescript-axios`) ⇒ **Kotlin LÀ codegen-target hợp lệ**, DoD "Dart/Kotlin" thoả ở tầng config (V-U1/V-U2). Prose-sample chương `09` = Dart+TS (Kotlin = config-only, runnable khi USER cấp toolchain — tên method = `operationId` ổn định mọi generator). **KHÔNG narrow DoD về "Dart + TypeScript"** (sẽ bỏ rơi target Kotlin đã khai). Quyết định + lý do: [`09 §1.1`](../09-native-repo-guide.md) (note V3-BA).

### 3.6 E2E runbook — ✅ ĐÃ HỢP NHẤT (V3 DONE, 2026-06-12)

> `[SUPERSEDED]` "coverage PHÂN MẢNH (chưa hợp nhất)" → **V3 đã build** chương [`14-e2e-field-tech-runbook.md`](../14-e2e-field-tech-runbook.md): 6 flow tuần tự (login OAuth2+refresh → quét QR → báo hỏng → WO PM/CM/Cal → "phiếu của tôi" → push FCM), mỗi bước operationId trục + curl/dart kiểm-được + expected envelope (`success`+`code`+`http_status` route-by-VALUE) + tiền-điều-kiện + tag `[AUTO]`/`[HARD-STOP USER]`. 3 mảnh nguồn dưới HỢP NHẤT vào 1 sequence:

| Mảnh nguồn (đã hợp nhất) | Tính chất | Vai trò trong runbook 14 |
|---|---|---|
| [`11 §1`](../11-phase-a-exit.md) traceability matrix | design-time (flow↔endpoint↔cap↔operationId) | nguồn cột operationId/endpoint/cap (runbook 14 = phiên bản CHẠY-ĐƯỢC) |
| [`10 §6.3`](../10-deploy-ops.md) smoke curl (2 lệnh) | go-live smoke (get_token + 1 biz-call) | flow-1 §3.2 + flow-2 §4.2 dùng lại 2 smoke này, mở rộng đủ 6 flow |
| [`09 §6.2`](../09-native-repo-guide.md) checklist | 1 dòng "build APK + smoke 1 luồng" | nâng thành sequence 6 flow + dart-client mỗi bước |

⇒ Runbook hợp nhất login→scan→báo hỏng→WO→phiếu→push = 1 sequence chạy-được — **V3 DONE** (chương 14 + README/00-overview index parity GREEN, `test_mobile_docset` 9 OK). `[AUTO]` grep 6 operationId trục PASS; `[HARD-STOP USER]` validate cloud = V-U5.

### 3.7 Endpoint trục 6 flow (file:line @source — nền E2E runbook V3)

> **[RECONCILED @source 2026-06-12].** Cột "Contract status" cập nhật theo @source (yaml all-typed). `[SUPERSEDED]` các nhãn cũ ("userinfo path CHƯA có" / "4 STUB còn" / "createPm STUB" / "SPEC-ONLY 0 code") — giữ ghi chú cũ inline cho audit-trail.

| Flow | operationId | Endpoint (`file:line` @source) | EPIC chốt | Contract status (re-verify 2026-06-12) |
|---|---|---|---|---|
| 1 Login | (auth) `authorizeOAuth`/`getOAuthToken`/`revokeOAuthToken` + `getUserInfo` | `frappe/integrations/oauth2.py:75/124/145` + userinfo `:163-164` | **B** + **C** (userinfo) | auth passthrough ✅; **userinfo = path `getUserInfo` ✅** (C4 wired — `[SUPERSEDED]` "CHƯA có") |
| 2 Scan QR | `resolveQrToken`/`getAssetScanInfo`/`getAsset` | `api/imm00.py:588/631/454` | **C** | **3 read typed ✅** 200 oneOf `[<ReadEnvelope>, Error]` closed-schema (C6 — `[SUPERSEDED]` "4 STUB còn generic") |
| 3 Báo hỏng | `reportIncident` | `api/imm12.py:71` | **C** | typed ✅ (dual-403, route-by-VALUE) |
| 4 WO PM/CM/Cal | `createPmWorkOrder`/`createRepairWorkOrder`/`createCalibration` | `api/imm08.py:91` / `api/imm09.py:36` / `api/imm11.py:90` | **C** | **cả 3 typed ✅** (createPm 200 oneOf `[CreatePmWorkOrderCreatedEnvelope, Error]` — C2; `[SUPERSEDED]` "createPm STUB") |
| 5 Phiếu của tôi | `listPmWorkOrders`/`listRepairWorkOrders`/`listIncidents` | `api/imm08.py:28` / `api/imm09.py:21` / `api/imm12.py:197` | **C** | envelope + **list-element typed ✅** (item-schema C3-split field-disjoint) |
| 6 Push FCM | `registerDeviceToken`/`unregisterDeviceToken` + `_dispatch` | `services/notifications.py:366` `_dispatch` (kênh #3) | **D** | **yaml typed ✅** (D4 — requestBody+200 oneOf closed-schema); impl `_dispatch`/register live = HARD-STOP USER (migrate+reload+FCM creds) |

---

## 4. Tasks (đánh số V1..V4)

> Mỗi task: mô tả + Files (Create/Modify exact path) + Acceptance (lệnh kiểm-được) + owner + tag + Dependencies. Cross-ref EPIC khác bằng ID+task.

### V1 — Cấu hình + chạy `openapi-generator` (Dart/Kotlin) + ghi toolchain status THẬT

**Mô tả:** (a) Bổ sung `openapitools.json` thành generator-config runnable (HOẶC tạo `tool/gen-client.sh` mẫu) — input=yaml, output, `generatorName` Dart (`dart-dio`) + Kotlin (`kotlin`) + TS (`typescript-axios`) (V3-BA CHỐT), KHÔNG để config rỗng (§3.2). (b) Khi USER cấp toolchain (JDK + generator — §3.1 [HARD-STOP USER cài]), chạy gen client THẬT, assert: 0-error · 0 dangling `$ref` · sinh **16 operationId method** (tên method = `operationId`, ổn định Dart vs Kotlin — [`09 §2.3`](../09-native-repo-guide.md)) _(`[SUPERSEDED]` "15 method")_. (c) Ghi RÕ toolchain status THẬT vào doc — KHÔNG tuyên bố "codegen verified" khi chưa chạy.

- **Files:**
  - Modify: `openapitools.json` (root) — thêm khối `generators` (input/output/generatorName); GIỮ `generator-cli.version: 7.23.0`.
  - Create (tùy chọn, illustrative): `tool/gen-client.sh` — lệnh gen mẫu (Dart + Kotlin/TS), CI gọi (bám [`09 §2.1/§2.2`](../09-native-repo-guide.md)).
  - Modify: file này (§3.1 toolchain status) + [`13 §7.1`](../13-be-completion-roadmap.md).
- **Acceptance:**
  - `[AUTO]` (proxy — không cần toolchain): PyYAML introspection 0 dangling `$ref`:
    ```bash
    bench --site miyano run-tests --module assetcore.tests.guards.test_mobile_oas
    # PASS: Ran 141 tests ... OK (count HIỆN HÀNH @source G3 2026-06-12; 0 dangling $ref; orphan ⊆ _RESERVED_ORPHANS; gồm class TestMobileCodegenConfig 28a..j; SSoT _EXPECTED_TEST_COUNT=141)
    ```
  - ✅ `[AUTO]` config non-empty (ĐÃ có guard máy-kiểm — Vòng 12 C-DoD-CFG): `openapitools.json` = runnable-config (`generator-cli.generators` ≥1 target, `inputSpec` trỏ mobile YAML SSoT, `generatorName`/`output` non-empty). Guard `assetcore.tests.guards.test_mobile_oas::TestMobileCodegenConfig` (TC-MOB-OAS-28a..j, STDLIB `json.load` — KHÔNG toolchain) THAY 1-liner python3 thủ công, bắt drift config↔YAML (RED-before/GREEN-after):
    ```bash
    # Guard máy-kiểm (chạy trong suite test_mobile_oas ở trên):
    #   28b version-pin · 28c generators non-empty · 28d MỌI inputSpec == _MOBILE_YAML SSoT (single-path)
    #   28e name+output non-empty · 28g/h/i drift-RED (sai-path / xoá generators / version='') · 28j control-GREEN
    # 1-liner thủ công (tương đương — LƯU Ý generators nested dưới generator-cli):
    python3 -c "import json; g=json.load(open('openapitools.json'))['generator-cli']['generators']; assert g, 'generators rỗng — V1 chưa đóng'; print('generators:', list(g))"
    # → ['mobile-dart', 'mobile-kotlin', 'mobile-typescript']
    ```
  - `[HARD-STOP USER cài]` codegen THẬT (sau JDK + generator):
    ```bash
    # USER chạy ở máy có JDK + @openapitools/openapi-generator-cli
    npx @openapitools/openapi-generator-cli generate \
      -i docs/mobile/openapi/assetcore-mobile.openapi.yaml -g dart-dio -o /tmp/gen-dart
    # PASS: exit 0, không "unresolvable", sinh 16 *.dart method khớp operationId  ([SUPERSEDED] "15" — C4 thêm getUserInfo ⇒ 16 operationId @source 2026-06-12)
    ```
- **Owner:** QA · **Tag:** config `[AUTO]` · codegen-run `[HARD-STOP USER cài]` (xem §6 Blocker B4 [`13 §8`](../13-be-completion-roadmap.md))
- **Dependencies:** EPIC-C (16/16 operationId FROZEN + 0 dangling `$ref` — DoD EPIC-C; `[SUPERSEDED]` "15/15"); V3-BA ✅ CHỐT (Dart/Kotlin/TS — `-g` thứ 2 = `kotlin`).

### V2 — Smoke client gen-ra gọi 6 flow trên cloud staging

**Mô tả:** Sau EPIC-G go-live (public HTTPS host + OAuth Client + reload), dùng client gen-ra (V1) gọi **6/6 flow MVP** trên cloud staging: login OAuth2+refresh → scan QR → báo hỏng → WO → phiếu của tôi → push. Assert mỗi flow trả envelope đúng (`body.success`/`body.code`/`http_status` — HTTP-200 quirk [`04 §5`](../04-api-contract.md)); assert refresh-on-401 1-lần ([`03 §2.5`](../03-auth-oauth2.md)).

- **Files:** Modify: file này (§ kết quả smoke) — ghi PASS/FAIL từng flow + lệnh thật chạy. KHÔNG tạo code client trong repo `assetcore` (client ở repo native Phase-D / `/tmp`).
- **Acceptance:**
  - `[HARD-STOP USER]` (cần EPIC-G go-live + V1 client) — smoke get_token (bám [`10 §6.3`](../10-deploy-ops.md) Smoke 1):
    ```bash
    curl -sS -X POST "https://$HOST/api/method/frappe.integrations.oauth2.get_token" \
      --data-urlencode "grant_type=authorization_code" --data-urlencode "code=$AUTHCODE" \
      --data-urlencode "redirect_uri=assetcore://oauth/callback" \
      --data-urlencode "client_id=$CLIENT_ID" --data-urlencode "code_verifier=$verifier"
    # PASS: 200 {"access_token":...,"refresh_token":...,"expires_in":3600,"token_type":"Bearer"}
    ```
  - `[HARD-STOP USER]` smoke biz-call qua bearer (Smoke 2):
    ```bash
    curl -sS "https://$HOST/api/method/assetcore.api.imm00.get_asset_scan_info?token=<qr_token>" \
      -H "Authorization: Bearer $ACCESS_TOKEN"
    # PASS: 200 {"success":true,"data":{...available_actions, pm_overdue, calibration_overdue...}}
    ```
  - `[AUTO]` proxy trước go-live: 6/6 flow có operationId trong yaml + endpoint verify @source (matrix §3.7):
    ```bash
    bench --site miyano run-tests --module assetcore.tests.guards.test_mobile_capability_map
    # PASS: Ran 6 tests ... OK (10 endpoint MVP ↔ matrix §1 ↔ CABILITY_MAP binding khớp)
    ```
- **Owner:** QA · **Tag:** `[HARD-STOP USER]` (cloud + reload) — proxy-test `[AUTO]`
- **Dependencies:** V1 (client) · **EPIC-G** (HTTPS host + reload, knob matrix [`13 §5`](../13-be-completion-roadmap.md)) · **EPIC-B** (OAuth Client `preflight.verify_oauth_client()` ready=True) · **EPIC-D** + FCM creds (flow-6 push). Flow 2/4 deser typed = ✅ @source (4 path C2/C6 đã typed — `[SUPERSEDED]` "CHỜ EPIC-C 4 STUB").

### V3 — E2E runbook field-tech (login→scan→báo hỏng→WO→phiếu→push) — ✅ V-A1 AUTO DONE (2026-06-12)

> **Trạng thái:** AUTO-part (viết runbook + V3-BA decision) = **DONE 2026-06-12** ([BA] Vòng 46). Chương [`14-e2e-field-tech-runbook.md`](../14-e2e-field-tech-runbook.md) tồn tại + index parity GREEN + 6 operationId trục grep PASS + 0 placeholder. Validate end-to-end cloud (chạy 6 flow thật) = **V-U5 [HARD-STOP USER]** (carry).

**Mô tả:** Viết chương E2E runbook hợp nhất (`docs/mobile/14-e2e-field-tech-runbook.md`): 6 flow tuần tự, mỗi bước có curl/dart-client + expected envelope (`success`+`code`+`http_status`) + tiền-điều-kiện (OAuth Client + bearer) + tag `[AUTO]` vs `[HARD-STOP USER]`. Bám matrix [`11 §1`](../11-phase-a-exit.md) (endpoint+operationId+cap) + smoke [`10 §6.3`](../10-deploy-ops.md) + HTTP-200 quirk [`04 §5`](../04-api-contract.md) + refresh-on-401 [`03 §2.5`](../03-auth-oauth2.md). **V3-BA (decision — CHỐT):** Kotlin vs TypeScript = **GIỮ "Dart bắt buộc; Kotlin/TS theo `openapitools.json`"** (KHÔNG narrow về "Dart + TypeScript"). Lý do: `openapitools.json` SSoT khai 3 generator THẬT gồm `mobile-kotlin` (`kotlin` jvm-retrofit2) ⇒ Kotlin là codegen-target hợp lệ (DoD "Dart/Kotlin" thoả ở config); prose-sample 09 = Dart+TS, Kotlin = config-only (runnable khi USER cấp toolchain). Chi tiết: [`09 §1.1`](../09-native-repo-guide.md) note V3-BA + §3.5 trên.

- **Files:**
  - Create: `docs/mobile/14-e2e-field-tech-runbook.md` (6 flow sequence) — HOẶC mục mới trong [`09`](../09-native-repo-guide.md). **Nếu tạo chương mới:** cập nhật index [`README.md`](../README.md) + [`00-overview.md §4`](../00-overview.md) (giữ `test_mobile_docset` FS↔index parity GREEN).
  - Modify: [`09 §1.1/§2`](../09-native-repo-guide.md) — kết luận V3-BA (Kotlin sample HOẶC narrow DoD "Dart + TypeScript").
- **Acceptance:**
  - `[AUTO]` runbook tồn tại + phủ 6 flow (kiểm-được): file chứa 6 operationId trục:
    ```bash
    F=docs/mobile/14-e2e-field-tech-runbook.md; \
    for op in getOAuthToken resolveQrToken reportIncident createPmWorkOrder listPmWorkOrders registerDeviceToken; do \
      grep -q "$op" "$F" && echo "OK $op" || echo "MISSING $op"; done
    # PASS: 6× OK (mỗi flow ≥1 operationId trục)
    ```
  - `[AUTO]` docset parity GREEN sau thêm chương (VERIFIED 2026-06-12):
    ```bash
    bench --site miyano run-tests --module assetcore.tests.guards.test_mobile_docset
    # PASS: Ran 9 tests ... OK (FS↔index parity 15 chương 00–14; 0 broken link; 0 placeholder ngoài code-fence;
    #   guard-suite count-parity intact — runbook = doc, KHÔNG thêm def test ⇒ _GUARD_SUITE_SUM 281 BẤT ĐỘNG)
    ```
  - `[HARD-STOP USER]` runbook validated end-to-end trên cloud (chạy 6 flow thật — gộp V2 smoke = V-U5).
- **Owner:** QA (runbook) + **BA** (Kotlin vs TS decision — CHỐT) · **Tag:** viết `[AUTO]` ✅ DONE · validate-cloud `[HARD-STOP USER]`
- **Dependencies:** matrix [`11 §1`](../11-phase-a-exit.md) (đã có) · V2 (smoke evidence) · EPIC-C (flow 2/4 typed @source — đã typed §3.3/§3.7) · EPIC-D (flow-6 push impl live = HARD-STOP USER).

### V4 — Gói handoff repo mobile (yaml + auth + base-url + ví dụ)

**Mô tả:** Đóng gói artifact handoff tường minh cho đội repo native (§3.5 — `09` đã documented nhưng chưa đóng gói). Manifest gồm: (1) copy `assetcore-mobile.openapi.yaml` + version-pin (`info.version` 0.1.0-skeleton — bump khi Phase-C đổi); (2) base-url ENV (dev `localhost:8000` / prod HTTPS placeholder `REPLACE-WITH-PUBLIC-HOST`); (3) link `03` auth-wiring + `04` envelope-quirk; (4) ví dụ 1 call đã-gen + lớp đọc `body.success`/`body.code`/`http_status`. Manifest checklist cho [PM] tick.

- **Files:**
  - Create: `docs/mobile/completion/V4-handoff-manifest.md` — manifest 4-mục + checklist [PM] tick (bám [`09 §6.2`](../09-native-repo-guide.md) checklist khởi tạo).
  - KHÔNG copy yaml ra ngoài (yaml SSoT giữ tại `docs/mobile/openapi/`); manifest TRỎ path + hướng dẫn đội native COPY (chống drift [`09 §2.4`](../09-native-repo-guide.md)).
- **Acceptance:**
  - `[AUTO]` manifest đủ 4 mục (kiểm-được):
    ```bash
    M=docs/mobile/completion/V4-handoff-manifest.md; \
    for k in "assetcore-mobile.openapi.yaml" "BASE_URL" "03-auth-oauth2.md" "body.success"; do \
      grep -q "$k" "$M" && echo "OK $k" || echo "MISSING $k"; done
    # PASS: 4× OK (yaml-pin · base-url · auth-link · envelope-read example)
    ```
  - `[AUTO]` link-health (manifest link resolve được):
    ```bash
    bench --site miyano run-tests --module assetcore.tests.guards.test_mobile_docset
    # PASS: Ran 9 tests ... OK (link-health TC-MOB-DOC-03 rglob bắt completion/V4-*.md: mọi ./ ../ resolve, 0 broken; total ≥ baseline 400)
    ```
- **Owner:** QA · **Tag:** `[AUTO]` (doc-only)
- **Dependencies:** EPIC-C (yaml ổn định để pin version) · V1 (ví dụ 1-call đã-gen) · V3 (auth-wiring + base-url ENV reference).

---

## 5. Data model / Schema

**EPIC-V KHÔNG thêm field / DocType / schema.** EPIC-V là tầng **verify + handoff** — chỉ TIÊU THỤ hợp đồng có sẵn (yaml + envelope) + ghi doc/manifest. Mọi schema mới thuộc:

- Schema response typed (read-envelope `QrResolveEnvelope`/`AssetScanInfoEnvelope`/`AssetDetailEnvelope` + `CreatePmWorkOrderCreatedEnvelope`) + list-element (`PmWorkOrderListItem`/`RepairWorkOrderListItem`/`IncidentListItem`) + userinfo path (`getUserInfo`) → **EPIC-C** (✅ ĐÃ typed @source 2026-06-12 — [`13 §3`](../13-be-completion-roadmap.md); `[SUPERSEDED]` "4 STUB còn").
- DocType `AC Mobile Device Token` (7 field, [`06 §2.1`](../06-push-fcm.md)) + `DeviceTokenRequest` → **EPIC-D** ([`13 §6`](../13-be-completion-roadmap.md)).

> **Invariant verify-được (DONE-gate):** list `count == rows` (count khớp drill theo `permission_query_conditions`) — đã fix dashboard KPI (`api/dashboard.py`); list-endpoint riêng (`listPmWorkOrders`/`listIncidents`) cần test confirm persona technician/vendor khi V2 smoke (carry STATE — `asset_list_count_drill_technician`).

---

## 6. Security & Audit

> EPIC-V KHÔNG đổi RBAC/code — nhưng codegen verify + E2E runbook PHẢI bảo toàn các bất biến bảo mật của lớp dưới. Liệt kê gate phải re-assert khi chạy V2/V3:

| Khía cạnh | Bất biến phải giữ (file:line @source) | Verify trong EPIC-V |
|---|---|---|
| **Quyền = 1 SSoT** | bearer→`set_user`→RBAC capability/DocPerm theo user; app native KHÔNG parse scope tự-gate (anti "hệ quyền thứ 2", [`03 §3.2`](../03-auth-oauth2.md)). Scope coarse `all openid`, quyền THỰC = DocPerm (B-8) | V3 runbook ghi RÕ: client gen-ra KHÔNG tự gate; 403 = `code=FORBIDDEN` VI sạch ([`04 §4`](../04-api-contract.md)) |
| **Vendor isolation (IDOR)** | `get_asset` (`api/imm00.py:271`) `assert_vendor_can_access` IDOR-guard (`:277-279`); list permission-aware `count==rows` | V2 smoke flow-2/5 với persona vendor → chỉ thấy asset assigned (LL-TEST-19 row-level filter) |
| **Token storage** | client lưu Keychain/Keystore (KHÔNG cookie/CSRF/SharedPrefs/log) ([`03 §2.4`](../03-auth-oauth2.md)); revoke logout RFC 7009 (`oauth2.py:158-159`) | V3 runbook bước login/logout ghi token-store + revoke; handoff (V4) link `03 §2.4` |
| **PKCE S256 public client** | KHÔNG nhúng `client_secret` trong APK; `code_challenge_method=S256` ([`03 §1.2`](../03-auth-oauth2.md)) | V1/V3: client gen-ra dùng PKCE; manifest (V4) nêu KHÔNG commit secret |
| **No traceback leak (prod)** | `allow_error_traceback` = System Setting default=1 ON (`frappe/utils/response.py:60-65`) → PROD phải TẮT (=0) để 401/403/429 KHÔNG leak SQL/traceback → **EPIC-G** | V2 smoke: assert 401/403 KHÔNG raw traceback (đã tắt). Nếu thấy raw → STALE-WORKER/chưa tắt (LL-QA-8, [`13 §5`](../13-be-completion-roadmap.md)) |
| **CORS (D-STACK native)** | native APK **KHÔNG cần CORS** (không browser engine — D-STACK); `allow_cors` GIỮ OFF hợp lệ; CẤM wildcard `*` prod (`frappe/app.py:283` credential-echo) → **EPIC-G** | V2/handoff ghi RÕ: native không trigger CORS; chỉ web/Swagger/WebView-OAuth cần list-origin |
| **Audit NĐ98** | mọi action write (báo hỏng/WO) emit lifecycle + IMM Audit Trail với actor = user THẬT (`source=mobile` coerce — `imm12.py:83`) | V2 flow-3/4 (write): verify audit-chain actor = bearer-user ([`10 §6.3`](../10-deploy-ops.md) verify-audit) |

> **CI-guard (V → QA→CI):** chặn `servers` placeholder `REPLACE-WITH-PUBLIC-HOST` (yaml:107) + version `0.1.0-skeleton` (yaml:89) lọt prod build — Phase B set host thật = [HARD-STOP USER]. Đây là task QA→CI ([`13 §5.2`](../13-be-completion-roadmap.md) EPIC-G chia sẻ).

---

## 7. Tham chiếu

### 7.1 Chương docset (00–13) + ADR + roadmap

- **SSoT roadmap:** [`13-be-completion-roadmap.md §7`](../13-be-completion-roadmap.md) (EPIC-V) · §8 (Blockers AUTO/HARD-STOP) · §9 (traceability 6 flow).
- **Handoff repo native (V1/V4 nguồn):** [`09-native-repo-guide.md`](../09-native-repo-guide.md) §1 (skeleton) · §2 (gen client) · §3 (ENV) · §4 (OAuth wiring) · §5 (build+CI drift-gate) · §6 (checklist).
- **Traceability matrix (V3 nền):** [`11-phase-a-exit.md §1`](../11-phase-a-exit.md) (6 flow × endpoint × operationId × cap × STUB-status) · §3 (go/no-go).
- **Smoke curl (V2/V3):** [`10-deploy-ops.md §6.3`](../10-deploy-ops.md) (2 lệnh curl get_token + biz-call) · §7 (rollback).
- **Auth deep-dive (V3 security):** [`03-auth-oauth2.md`](../03-auth-oauth2.md) §1 (PKCE) · §2.4 (token-store) · §2.5 (refresh-on-401) · §3 (RBAC 1-SSoT).
- **Hợp đồng API (envelope-quirk):** [`04-api-contract.md`](../04-api-contract.md) §3 (envelope) · §4 (15 ErrorCode) · §5 (HTTP-200 quirk) · §6 (pagination) · §8.2 (RESERVED orphan).
- **Go-live knob (V2 prereq):** [`13 §5`](../13-be-completion-roadmap.md) EPIC-G knob matrix · [`08-security-compliance.md §4`](../08-security-compliance.md).
- **Push (V2/V3 flow-6):** [`06-push-fcm.md`](../06-push-fcm.md) · [`13 §6`](../13-be-completion-roadmap.md) EPIC-D.

### 7.2 ADR-MOBILE-00x

- [`ADR-MOBILE-001`](../ADR-MOBILE-001.md) (d) — **OpenAPI = HỢP ĐỒNG** (sinh client + chống drift) — nền V1/V4. (b) RBAC 1-SSoT — nền §6. (g) 2 envelope list rows-key (data.data[] vs data.items[]) — flow-5.
- [`ADR-MOBILE-002`](../ADR-MOBILE-002.md) — FCM Admin SDK HTTP v1 trực tiếp (flow-6 push, V2/V3).
- [`ADR-MOBILE-004`](../ADR-MOBILE-004.md) (c) — native APK KHÔNG cần CORS (§6 security gate).

### 7.3 LL-* skill (assetcore-test)

- **LL-QA-8 / LL-TEST-25** — reload gunicorn TRƯỚC Playwright/HTTP-verify khi sửa `api/`/`services/` .py (`--preload` đông cứng); guest-403 ≠ stale; 417 phantom. → V2 smoke chỉ chạy SAU [HARD-STOP USER reload].
- **LL-QA-4 / LL-TEST-21** — `tests_green=true` CHỈ khi chạy THẬT `bench run-tests` + ĐỌC output (chống false-green); pass-ngay-lần-đầu trên side-effect = nghi false-green. → V1/V3/V4 Acceptance đọc dòng tổng `Ran N tests ... OK`.
- **LL-TEST-19** — test permission gate + row-level filter (vendor isolation) cho mọi mutating/list endpoint. → §6 V2 smoke persona vendor.
- **R-11 / R-12 / LL-QA-1/2/3** — artifact eval → `.playwright/eval/`; POST-RUN cleanup BẮT BUỘC (`bash .claude/scripts/tidy-eval-artifacts.sh`) là phần của DONE.

---

## 8. Rủi ro

| # | Rủi ro | Mức | Mitigation (kiểm-được) |
|---|---|---|---|
| RV-1 | **Toolchain ABSENT** (no JDK + generator chưa cài §3.1) → V1 codegen THẬT KHÔNG chạy được trong env này → DoD "1 client gen-ra" KHÔNG đóng được tự động | **HIGH** | `[HARD-STOP USER cài]` HOẶC máy build Phase-D. PyYAML proxy (`test_mobile_oas` **141 OK** count HIỆN HÀNH @source 2026-06-12; gồm config-validity guard `TestMobileCodegenConfig`) đảm bảo codegen-validity + config↔YAML consistency tới khi có toolchain. KHÔNG tuyên bố "verified" khi chưa chạy (LL-QA-4). |
| RV-2 | ~~**4 STUB còn generic**~~ → ✅ **RESOLVED @source 2026-06-12** | ~~HIGH~~ → **CLOSED** | `[SUPERSEDED]`: 4 path C2/C6 đã typed @source (3 read 200-oneOf closed-schema + createPm typed — §3.3/§3.7). flow-2/4 deser typed. KHÔNG còn blocker. |
| RV-3 | ~~**Kotlin gap** (DoD "Dart/Kotlin" vs docset)~~ → ✅ **RESOLVED (V3-BA, 2026-06-12)** | ~~MEDIUM~~ → **CLOSED** | `[SUPERSEDED]`: `openapitools.json` khai 3 generator THẬT gồm `mobile-kotlin` ⇒ Kotlin = codegen-target hợp lệ. GIỮ DoD "Dart/Kotlin", KHÔNG narrow. Prose-sample 09 = Dart+TS; Kotlin config-only (§3.5 + [`09 §1.1`](../09-native-repo-guide.md)). |
| RV-4 | ~~**userinfo/whoami CHƯA là path**~~ → ✅ **RESOLVED @source (C4)** | ~~MEDIUM~~ → **CLOSED** | `[SUPERSEDED]`: `getUserInfo` (`openid_profile`) LÀ path trong yaml (16 path) — codegen sinh method whoami. flow-1 danh tính đủ. |
| RV-5 | **flow-6 push — yaml typed ✅ nhưng impl-live CHƯA** (D4 typed contract; `_dispatch` kênh #3 + register live cần migrate+reload+FCM creds) → V2/V-U4 flow-6 chạy THẬT tới khi EPIC-D live | **HIGH** (impl-live) | **Phụ thuộc EPIC-D** ([`13 §6`](../13-be-completion-roadmap.md)) + FCM creds [HARD-STOP USER]. yaml-contract đã typed (D4); chỉ live-HTTP = last-to-validate. |
| RV-6 | **Go-live chưa live** — servers placeholder (yaml:107) + host ABSENT ([`13 §5`](../13-be-completion-roadmap.md)) → V2 cloud smoke KHÔNG chạy được tới khi EPIC-G | **HIGH** | **Phụ thuộc EPIC-G** + [HARD-STOP USER] reload/host. CI-guard chặn placeholder lọt prod (§6). |
| RV-7 | **Drift contract↔client** — đội native sửa tay `api/generated/` HOẶC quên regenerate khi yaml đổi (Phase-C bồi STUB) | **MEDIUM** | CI drift-gate ([`09 §2.4/§5.2`](../09-native-repo-guide.md)): `git diff --exit-code` trên `api/generated/`; pin `info.version`. V4 manifest nêu quy tắc regenerate. |
| RV-8 | **False-green codegen** — claim "gen 0-error" mà chưa đọc output generator (stale/cached gen) | **MEDIUM** | LL-QA-4: đọc exit-code + đếm **16** method THẬT từ output; assert 0 "unresolvable" trong log. KHÔNG suy đoán. |

---

## Cross-ref EPIC khác (bằng ID+task)

- **EPIC-C** (API Contract): ✅ C đã đóng @source (4 path C2/C6 typed + list-element C3-split + userinfo path C4 — 16 path, 16/16 operationId all-typed; `[SUPERSEDED]` "đóng 4 STUB"). V1 gen "mọi path MVP typed" + V2 "typed deser" KHÔNG còn chặn ở contract. DoD EPIC-C = `openapi-generator` sạch ([`13 §3.6`](../13-be-completion-roadmap.md)) = tiền-đề V1 (chỉ chờ toolchain THẬT).
- **EPIC-B** (Auth & Provisioning): V2 smoke flow-1 cần B đóng (`preflight.verify_oauth_client()` ready=True — B DoD). Token TTL 3600s (B KNOWN-LIMIT) → V3 runbook refresh-on-401 dùng `expires_in=3600`.
- **EPIC-G** (Go-live): V2 cloud smoke cần G đóng (HTTPS host thay placeholder yaml:107 + reload + tắt `allow_error_traceback` + CORS-off native). CI-guard servers-placeholder = G∥V task.
- **EPIC-D** (Push FCM): V2/V3 flow-6 cần D đóng (DocType device-token + register/unregister + kênh #3 `_dispatch:366` + FCM creds [HARD-STOP USER]).
