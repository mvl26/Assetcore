# 14 — E2E field-tech runbook (login OAuth2+refresh → quét QR → báo hỏng → WO PM/CM/Cal → phiếu của tôi → push)

| Mục | Giá trị |
|---|---|
| Initiative | **AssetCore Mobile** — backend-for-mobile (repo này) + APK native (repo riêng) |
| Vai trò file | **Runbook E2E CHẠY-ĐƯỢC** — 6 flow field-tech MVP tuần tự, mỗi bước có lệnh kiểm-được THẬT (curl/dart) + expected envelope + tiền-điều-kiện + tag `[AUTO]`/`[HARD-STOP USER]` |
| Phase / EPIC | **EPIC-V V3** (Codegen Verify + Handoff) — hợp nhất coverage phân mảnh (`11 §1` design-matrix + `10 §6.3` smoke + `09 §6.2` checklist) thành 1 sequence |
| Owner | BA Lead + System Architect (mobile) |
| Trạng thái docs | Stable |
| Cập nhật | 2026-06-12 |

> **Đây KHÔNG phải spec mới — là runbook HỢP NHẤT.** Mọi endpoint/operationId/capability/envelope đã đặc tả ở các chương nguồn; file này gom thành **1 chuỗi chạy-được** đầu-cuối + chỉ TRỎ NGƯỢC `file:section` (chống drift). Quirk hợp đồng quan trọng (route-by-VALUE HTTP-200, refresh-on-401, dual-403) lặp lại ngắn TẠI CHỖ cần để người chạy không phải nhảy file.
> Mọi `file:line`/operationId đã re-verify @source `openapi/assetcore-mobile.openapi.yaml` (16 path, all typed) + `api/*.py` (Frappe v15) — 2026-06-12.

> **Chỉ mục docset:** [`00-overview.md`](./00-overview.md) · [`03-auth-oauth2.md`](./03-auth-oauth2.md) · [`04-api-contract.md`](./04-api-contract.md) · [`05-personas-mvp.md`](./05-personas-mvp.md) · [`06-push-fcm.md`](./06-push-fcm.md) · [`09-native-repo-guide.md`](./09-native-repo-guide.md) · [`10-deploy-ops.md`](./10-deploy-ops.md) · [`11-phase-a-exit.md`](./11-phase-a-exit.md) · [`13-be-completion-roadmap.md`](./13-be-completion-roadmap.md) · [`README.md`](./README.md) · [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml)

---

## 0. Mục tiêu / Cách dùng / Out-of-scope

### 0.1 Mục tiêu

Một runbook DUY NHẤT cho đội repo native + QA chạy **6/6 flow MVP field-tech** theo đúng thứ tự hành trình:

```
[1] Login OAuth2 (+refresh-on-401) → [2] Quét QR → hồ sơ → [3] Báo hỏng
   → [4] Yêu cầu PM/CM/Hiệu chuẩn → [5] "Phiếu của tôi" → [6] Push FCM
```

Mỗi bước trình bày:
- **operationId trục** (= tên method client codegen sinh ra — [`09 §2.3`](./09-native-repo-guide.md));
- **Lệnh kiểm-được THẬT** — `curl` (cloud) + tương đương **dart-dio** (client gen-ra, [`09 §2.1`](./09-native-repo-guide.md));
- **Expected envelope** — `success` + `code` + `http_status` (route-by-VALUE, [`04 §5`](./04-api-contract.md));
- **Tiền-điều-kiện** — OAuth Client + bearer + go-live knob;
- **Tag** — `[AUTO]` (factory introspect được, không cần cloud) vs `[HARD-STOP USER]` (cần cloud HTTPS + reload + creds).

### 0.2 Hai loại lệnh — đọc kỹ trước khi chạy

| Tag | Ý nghĩa | Chạy ở đâu |
|---|---|---|
| `[AUTO]` | Kiểm chứng **introspection/contract** (operationId tồn tại, schema khớp, endpoint @source) — KHÔNG cần cloud/bearer. Factory chạy được ngay. | `bench run-tests` / `grep` local |
| `[HARD-STOP USER]` | Chạy THẬT qua HTTP với bearer trên cloud — cần OAuth Client + public HTTPS host + gunicorn reload (+ FCM creds cho flow-6). Agent **KHÔNG** thực thi. | Máy USER, cloud staging |

> ⚠️ **gunicorn `--preload` staleness:** mọi sửa `api/*.py`/`services/*.py` chỉ LIVE qua HTTP **sau khi USER reload** ([`13 §8`](./13-be-completion-roadmap.md) blocker #1). Trước reload, `[HARD-STOP USER]` curl có thể trả raw/`417`/stale — KHÔNG phải lỗi hợp đồng.

### 0.3 Out-of-scope (KHÔNG làm ở runbook này)

| KHÔNG làm | Vì sao / đẩy đâu |
|---|---|
| Impl UI native 6 màn | Phase D, repo riêng ([`09 §0`](./09-native-repo-guide.md)) |
| Sửa yaml path/operationId/schema | EPIC-C đóng băng (16 path, 6 operationId trục FROZEN) — runbook CHỈ ĐỌC |
| Bật go-live (OAuth Client / CORS / host / FCM creds / reload) | **[HARD-STOP USER]** ([`10-deploy-ops.md`](./10-deploy-ops.md) + [`13 §8`](./13-be-completion-roadmap.md)) |
| Cài JDK / openapi-generator / Firebase | **[HARD-STOP USER]** (toolchain — [`13 §7.1`](./13-be-completion-roadmap.md)) |

---

## 1. Tiền-điều-kiện chung (chạy MỘT lần, trước cả 6 flow)

> Bám [`11 §2`](./11-phase-a-exit.md) (Phase-B prereqs B-1..B-8) + [`10-deploy-ops.md`](./10-deploy-ops.md) (runbook go-live). Mọi mục dưới = **[HARD-STOP USER]** trừ pre-flight verifier (read-only).

| # | Điều kiện | Tag | Lệnh kiểm-được | PASS khi |
|---|---|---|---|---|
| P1 | **OAuth Client native** tồn tại (redirect `assetcore://oauth/callback`, PKCE S256, scopes `all openid`) | [HARD-STOP USER] | `bench --site $SITE execute assetcore.api.mobile.preflight.verify_oauth_client` ([`12 §1`](./12-phase-b-preflight.md)) | report `"ready": true`, `blockers: []` |
| P2 | **Public HTTPS host** + reverse-proxy ([`10 §3`](./10-deploy-ops.md)) | [HARD-STOP USER] | `bench --site $SITE execute frappe.utils.get_url` | == public host (KHÔNG `http://miyano`) |
| P3 | **gunicorn reload** sau mọi sửa `api/*.py`/`services/*.py` | [HARD-STOP USER] | (USER) `bench restart` / reload `--preload` | endpoint live HTTP (KHÔNG `417`/stale) |
| P4 | **FCM creds** `site_config` (CHỈ flow-6) — `fcm_service_account_path`+`fcm_project_id` ([`06`](./06-push-fcm.md) + ADR-002) | [HARD-STOP USER] | `bench --site $SITE execute "frappe.get_conf" --kwargs "{}"` (kiểm key) | 2 key có giá trị |
| P5 | **`bench migrate`** (DocType `AC Mobile Device Token` cho flow-6) | [HARD-STOP USER] | (USER) `bench --site $SITE migrate` | `tabAC Mobile Device Token` tồn tại |

**Biến môi trường dùng xuyên suốt** (đặt 1 lần ở shell USER):

```bash
HOST="https://$PUBLIC_HOST"                  # public HTTPS host (P2)
CLIENT_ID="<OAuth Client.client_id>"          # P1
# Sau flow-1: ACCESS_TOKEN / REFRESH_TOKEN điền từ get_token response.
ACCESS_TOKEN=""
REFRESH_TOKEN=""
```

**[AUTO] sanity contract** — 6 operationId trục đều có trong yaml (chạy không cần cloud):

```bash
Y=docs/mobile/openapi/assetcore-mobile.openapi.yaml
for op in getOAuthToken resolveQrToken reportIncident createPmWorkOrder listPmWorkOrders registerDeviceToken; do
  grep -q "operationId: $op" "$Y" && echo "OK $op" || echo "MISSING $op"; done
# PASS: 6× OK (mỗi flow ≥1 operationId trục)
```

---

## 2. HỢP ĐỒNG ĐỌC-ENVELOPE (áp CHO MỌI bước — non-negotiable)

> 3 quy tắc này quyết định client native đọc đúng/sai. Lặp ngắn ở đây để chạy runbook không phải nhảy file; nguồn đầy đủ: [`04 §5`](./04-api-contract.md) (HTTP-200 quirk + dual-403) + [`03 §2.5`](./03-auth-oauth2.md) (refresh-on-401).

### 2.1 Route-by-VALUE, KHÔNG route-by-status-line (business endpoint)

Lỗi **NGHIỆP VỤ IN-HANDLER** (404/422/409 + in-handler cap-403) trả **HTTP-200** + Error envelope; `http_status` THẬT nằm **TRONG body** ([`04 §5`](./04-api-contract.md)).

```jsonc
// HTTP/1.1 200 OK            ← status-line = 200 (wrapper quirk)
{ "success": false, "error": "…", "code": "FORBIDDEN", "http_status": 403 }
```

⇒ Client quyết định bằng **`body.success`** → nếu `false`, phân nhánh UX theo **`body.code`** + **`body.http_status`**. KHÔNG chỉ đọc HTTP status-line cho business path.

### 2.2 Decision-B closed-schema 200-oneOf (KHÔNG discriminator boolean)

Mọi 200 của create/read path = `oneOf [<X>CreatedEnvelope|<X>Envelope, Error]` — **KHÔNG `discriminator`** (`success` là BOOLEAN → discriminator OAS 3.x illegal, [`04 §5c`](./04-api-contract.md) Self-Correction R1). 2 nhánh máy-phân-biệt bằng **closed-schema** (`additionalProperties:false` cả 2) + **disjoint required-set** + `success` enum đối lập (`[true]` vs `[false]`). Client codegen route theo **giá trị `body.success`**, KHÔNG `anyMatch` oneOf.

### 2.3 Refresh-on-401 MỘT-lần (transport, KHÔNG business)

`401` (HTTP status-line THẬT — bearer hết-hạn/invalid, có gửi `Authorization`): app thử **refresh MỘT lần** (`grant_type=refresh_token`) → retry request gốc với access mới. Refresh fail (`invalid_grant`) → xoá token → **re-auth**. KHÔNG vòng lặp refresh vô hạn ([`03 §2.5`](./03-auth-oauth2.md)). Phân biệt với **403** (guest/no-token dispatcher HOẶC thiếu-cap in-handler) — KHÔNG tự refresh ([`04 §5`/§5a](./04-api-contract.md)).

---

## 3. Flow 1 — Đăng nhập OAuth2 (+ refresh-on-401)

**operationId trục:** `getOAuthToken` · **Endpoint:** `frappe.integrations.oauth2.get_token` (`frappe/integrations/oauth2.py:124`) · **Cap:** — (allow_guest, PKCE S256) · **Tiền-điều-kiện:** P1 (OAuth Client) + P2 (HTTPS host). Matrix nguồn: [`11 §1 Flow 1`](./11-phase-a-exit.md). Sequence a→f: [`03 §1`](./03-auth-oauth2.md).

### 3.1 Bước 1a — authorize (PKCE) → lấy authorization code

> `authorizeOAuth` (`oauth2.py:75`) — 302 redirect trong WebView/Custom Tab, KHÔNG curl-able thuần (browser). Chi tiết PKCE S256: [`03 §1.3`](./03-auth-oauth2.md). Output bước này = `$AUTHCODE` + `$verifier` (PKCE verifier gốc).

### 3.2 Bước 1b — get_token (đổi code → token) — `getOAuthToken`

**[HARD-STOP USER]** (cloud + OAuth Client) — bám [`10 §6.3`](./10-deploy-ops.md) Smoke 1:

```bash
curl -sS -X POST "$HOST/api/method/frappe.integrations.oauth2.get_token" \
  --data-urlencode "grant_type=authorization_code" \
  --data-urlencode "code=$AUTHCODE" \
  --data-urlencode "redirect_uri=assetcore://oauth/callback" \
  --data-urlencode "client_id=$CLIENT_ID" \
  --data-urlencode "code_verifier=$verifier"
```

**Expected envelope (PASSTHROUGH OAuthlib — KHÔNG AssetCore envelope, [`04 §5b`](./04-api-contract.md)):**

| Khía cạnh | Giá trị |
|---|---|
| HTTP status-line | `200` (THẬT — token issuance) |
| Body | `{"access_token":"…","refresh_token":"…","expires_in":3600,"token_type":"Bearer","scope":"all openid"}` |
| `success`/`code`/`http_status` | **N/A** — auth-section KHÔNG dùng Error envelope. Phân nhánh theo key **`error`** (OAuth RFC 6749), KHÔNG `code`. |
| FAIL | HTTP `400` + `{"error":"invalid_grant"}` (PKCE sai / code hết hạn) → **re-auth** ([`03 §2.3.1`](./03-auth-oauth2.md)) |

```bash
# Lưu token vào biến (USER):
ACCESS_TOKEN="<access_token>"; REFRESH_TOKEN="<refresh_token>"
```

**Dart (client gen-ra — `dart-dio`, [`09 §2.1`](./09-native-repo-guide.md)):**

```dart
final tok = await AuthApi(dio).getOAuthToken(
  grantType: 'authorization_code', code: authCode,
  redirectUri: 'assetcore://oauth/callback', clientId: clientId, codeVerifier: verifier);
// tok.accessToken / tok.refreshToken / tok.expiresIn == 3600 / tok.tokenType == 'Bearer'
// Lưu Keychain/Keystore (03 §2.4). KHÔNG log token.
```

### 3.3 Bước 1c — refresh-on-401 (1 lần) — `getOAuthToken` (grant_type=refresh_token)

**[HARD-STOP USER]** — khi BẤT KỲ business-call nào ở flow 2–6 trả **HTTP-401** (status-line THẬT):

```bash
curl -sS -X POST "$HOST/api/method/frappe.integrations.oauth2.get_token" \
  --data-urlencode "grant_type=refresh_token" \
  --data-urlencode "refresh_token=$REFRESH_TOKEN" \
  --data-urlencode "client_id=$CLIENT_ID"
# PASS: 200 + access_token MỚI → retry request gốc 1 LẦN (§2.3).
# FAIL: 400 {"error":"invalid_grant"} (refresh hết hạn/revoked) → xoá token → re-auth (03 §2.5). KHÔNG loop.
```

**[AUTO] kiểm hợp đồng refresh-on-401 (doc-guard, không cần cloud):**

```bash
bench --site miyano run-tests --module assetcore.tests.test_mobile_oas
# PASS: Ran 141 tests ... OK (gồm TestMobileRefreshOn401DocGuard — invariant 03 §2.5/§2.6 + 04 §9d)
```

---

## 4. Flow 2 — Quét QR → hồ sơ thiết bị

**operationId trục:** `resolveQrToken` (+ `getAssetScanInfo`/`getAsset`) · **Endpoint:** `assetcore.api.imm00.resolve_qr_token` (`api/imm00.py:588`) · **Cap:** `asset.read` → `("AC Asset","read")` · **Tiền-điều-kiện:** bearer (flow-1). Matrix nguồn: [`11 §1 Flow 2`](./11-phase-a-exit.md).

> App tự decode QR (camera) + parse token khỏi URL `/a/<token>` (native KHÔNG dùng deep-link SPA). `resolve_qr_token` có `@rate_limit(30/60s/IP)` → có thể `429` (backoff). `get_asset`/`get_asset_scan_info` đính kèm cờ overdue **server-flag** (`pm_overdue`/`calibration_overdue`) — FE CHỈ render cờ (`overdue_server_flag_ssot`).

### 4.1 Bước 2a — resolve QR token → asset — `resolveQrToken`

**[HARD-STOP USER]** (bearer):

```bash
curl -sS "$HOST/api/method/assetcore.api.imm00.resolve_qr_token?token=$QR_TOKEN" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Expected envelope (200-oneOf closed-schema, route-by-VALUE §2.1/§2.2):**

| Trường hợp | `success` | `code` | `http_status` (body) | HTTP line | Hành động client |
|---|---|---|---|---|---|
| Resolve OK | `true` | — | — | 200 | đọc `data` (asset) → màn info |
| Token∄/rỗng | `false` | `NOT_FOUND` | `404` | **200** | thông báo "QR không hợp lệ" (leak-safe `api/imm00.py:619`) |
| Vendor-IDOR | `false` | `FORBIDDEN` | `403` | **200** | "không thuộc phạm vi" — KHÔNG re-auth (token còn tốt) |
| Guest/no-token / thiếu DocPerm | — | — | — | **403** (status-line THẬT) | dispatcher-403 → **re-auth** ([`04 §5a`](./04-api-contract.md)) |
| Vượt rate-limit | — | — | — | **429** (status-line THẬT) | exponential-backoff ([`04 §5`](./04-api-contract.md)) |

**Dart:**

```dart
try {
  final r = await AssetApi(dio).resolveQrToken(token: qrToken); // 200-oneOf
  if (r.success == true) { /* r.data */ } else { switch (r.httpStatus) { /* 404/403 body */ } }
} on DioException catch (e) { /* 403 status-line → re-auth · 429 → backoff · 401 → refresh §2.3 */ }
```

### 4.2 Bước 2b — màn info + available_actions — `getAssetScanInfo`

**[HARD-STOP USER]** — bám [`10 §6.3`](./10-deploy-ops.md) Smoke 2:

```bash
curl -sS "$HOST/api/method/assetcore.api.imm00.get_asset_scan_info?token=$QR_TOKEN" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
# PASS: 200 {"success":true,"data":{...available_actions, pm_overdue, calibration_overdue...}}
#   available_actions = capability ∩ lifecycle (SSoT _build_available_actions services/imm00.py:589) → ẩn nút KTV không có quyền.
#   404/vendor-403 in-handler arrive HTTP-200 body (route §2.1); dispatcher-403/429 = status-line THẬT.
```

---

## 5. Flow 3 — Báo hỏng

**operationId trục:** `reportIncident` · **Endpoint:** `assetcore.api.imm12.report_incident` (`api/imm12.py:71`) · **Cap:** `corrective.create` → `("Incident Report","create")` · **Tiền-điều-kiện:** bearer + persona có `corrective.create` (persona `corrective.read-only` → cap-403). Matrix nguồn: [`11 §1 Flow 3`](./11-phase-a-exit.md). Request/response: [`04 §8.3`](./04-api-contract.md).

> POST-only. `requestBody` THẬT 4 field bắt buộc (`asset`/`incident_type`/`severity`/`description`); `source` server-coerce (`mobile`→`qr-scan`/`manual`, KHÔNG client gửi). Emit lifecycle `incident_reported` + audit NĐ98. Critical → asset Out of Service (BR-12-04). **403 = DUAL-SHAPE** (xem dưới).

### 5.1 Bước 3 — report incident — `reportIncident`

**[HARD-STOP USER]** (bearer + cap):

```bash
curl -sS -X POST "$HOST/api/method/assetcore.api.imm12.report_incident" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  --data-urlencode "asset=$ASSET_CODE" \
  --data-urlencode "incident_type=Failure" \
  --data-urlencode "severity=High" \
  --data-urlencode "description=Màn hình không lên nguồn"
```

> Content khai **oneOf** `application/json` + `application/x-www-form-urlencoded` ([`04 §4/§9`](./04-api-contract.md)) — Frappe RPC `/api/method` đọc `form_dict`. curl form-encoded trên là đường mặc định; client JSON set `Content-Type: application/json`.
> Enum bắt buộc (Select-canonical @`incident_report.json`): `incident_type ∈ [Failure, Safety Event, Near Miss, Malfunction]` · `severity ∈ [Low, Medium, High, Critical]`.

**Expected envelope (200-oneOf, route-by-VALUE §2.1/§2.2):**

| Trường hợp | `success` | `code` | `http_status` (body) | HTTP line | Hành động |
|---|---|---|---|---|---|
| Tạo OK | `true` | — | — | 200 | `data = {name, status:"Open", severity}` (`services/imm12.py:410`) → push E3 tới KTV được giao |
| Asset∄ | `false` | `NOT_FOUND` | `404` | **200** | "thiết bị không tồn tại" (`services/imm12.py:361`) |
| BR-12-01 (Critical thiếu clinical_impact) | `false` | `VALIDATION` | `422` | **200** | hiện lỗi validate (`services/imm12.py:359`) |
| **(b) in-handler cap-403** (persona thiếu `corrective.create`) | `false` | `FORBIDDEN` | `403` | **200** | **SHOW-MESSAGE** — KHÔNG re-auth (token tốt, `api/imm12.py:96`) |
| **(a) dispatcher-403** (guest/no-token) | — | — | — | **403** (status-line THẬT) | **RE-AUTH** — `FrappeRawError` raw (`__init__.py:876`) |

> ⚠️ **DUAL-403 (báo hỏng = nhánh (b) phổ biến nhất của field-tech):** component OpenAPI `ReportIncidentForbidden` = `oneOf [Error, FrappeRawError]` (KHÔNG discriminator). Client route theo **HTTP status-line**: `200`→`Error`→**SHOW-MESSAGE**; `403`→`FrappeRawError`→**RE-AUTH**. Tầng phân biệt phụ = `FrappeRawError` `additionalProperties:false` (closed) loại trừ `Error`. KHÔNG `anyMatch` ([`04 §5a`](./04-api-contract.md)).

**Dart:**

```dart
final r = await IncidentApi(dio).reportIncident(reportIncidentRequest:
  ReportIncidentRequest(asset: assetCode, incidentType: 'Failure', severity: 'High',
    description: 'Màn hình không lên nguồn'));
// r.success==true → r.data.name/status/severity. false → route body.httpStatus (404/422). cap-403 = 200+Error{FORBIDDEN}.
```

---

## 6. Flow 4 — Yêu cầu PM / CM / Hiệu chuẩn

**operationId trục:** `createPmWorkOrder` (+ `createRepairWorkOrder`/`createCalibration`) · **Endpoint:** `assetcore.api.imm08.create_pm_work_order` (`api/imm08.py:91`) · **Cap:** `pm.create` → `("PM Work Order","create")` · **Tiền-điều-kiện:** bearer + cap. Matrix nguồn: [`11 §1 Flow 4`](./11-phase-a-exit.md). Response shape: [`04 §5c`](./04-api-contract.md).

> 3 POST-only. Push E1 (assignment) tự phát qua channel #3 `_dispatch` → deep-link `assetcore://wo/pm/<name>` ([`06 §3.3`](./06-push-fcm.md)). **403 = SINGLE-SHAPE** cho cả 3 (rbac.require dispatcher-403, KHÁC report_incident).

### 6.1 Bước 4a — tạo PM Work Order — `createPmWorkOrder`

**[HARD-STOP USER]** (bearer + `pm.create`):

```bash
curl -sS -X POST "$HOST/api/method/assetcore.api.imm08.create_pm_work_order" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  --data-urlencode "asset_ref=$ASSET_CODE" \
  --data-urlencode "pm_schedule=$PM_SCHEDULE" \
  --data-urlencode "due_date=2026-07-01"
```

> Bắt buộc `asset_ref`/`pm_schedule`/`due_date` (`services/imm08.py:788`; `pm_schedule` phải Active + khớp asset). Content oneOf json+form ([`04 §4`](./04-api-contract.md)).

**Expected envelope (200-oneOf, route-by-VALUE §2.1/§2.2):**

| Trường hợp | `success` | `code` | `http_status` (body) | HTTP line | Hành động |
|---|---|---|---|---|---|
| Tạo OK | `true` | — | — | 200 | `data = {name, status, checklist_items_count}` (`services/imm08.py:836`) |
| Thiếu field / schedule-asset mismatch | `false` | `VALIDATION` | `422` | **200** | hiện lỗi (`services/imm08.py:788,804`) |
| PM Schedule∄ | `false` | `NOT_FOUND` | `404` | **200** | "lịch PM không tồn tại" (`services/imm08.py:800`) |
| Schedule không Active (BAD_STATE) | `false` | `CONFLICT` | `409` | **200** | "trạng thái không cho tạo WO" (`services/imm08.py:808`) |
| Thiếu cap / guest | — | — | — | **403** (status-line THẬT) | dispatcher-403 single-shape → re-auth/thiếu-quyền |

**Dart:**

```dart
final r = await WorkOrderApi(dio).createPmWorkOrder(
  assetRef: assetCode, pmSchedule: pmSchedule, dueDate: DateTime.parse('2026-07-01'));
// r.success==true → r.data.name/status/checklistItemsCount. false → route body.httpStatus (422/404/409).
```

### 6.2 Bước 4b/4c — CM / Hiệu chuẩn (đối xứng) — `createRepairWorkOrder` / `createCalibration`

**[HARD-STOP USER]** — cùng pattern (route-by-VALUE, single-shape 403):

```bash
# CM (repair) — bắt buộc asset_ref/repair_type/priority/failure_description (api/imm09.py:36-38)
curl -sS -X POST "$HOST/api/method/assetcore.api.imm09.create_repair_work_order" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  --data-urlencode "asset_ref=$ASSET_CODE" --data-urlencode "repair_type=Corrective" \
  --data-urlencode "priority=High" --data-urlencode "failure_description=Bơm rò rỉ"
# OK 200 → data {name, status, sla_target_hours} (services/imm09.py:786). 404 asset∄ / 409 HAS_OPEN_WO arrive HTTP-200 body.

# Hiệu chuẩn — bắt buộc asset/calibration_type/scheduled_date/technician (api/imm11.py:90)
curl -sS -X POST "$HOST/api/method/assetcore.api.imm11.create_calibration" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  --data-urlencode "asset=$ASSET_CODE" --data-urlencode "calibration_type=Periodic" \
  --data-urlencode "scheduled_date=2026-07-10" --data-urlencode "technician=$USER_ID"
# OK 200 → data {name, status} (services/imm11.py:1015). 404 asset∄ / 409 ASSET_BLOCKED (CAL-008) arrive HTTP-200 body.
```

---

## 7. Flow 5 — "Phiếu của tôi"

**operationId trục:** `listPmWorkOrders` (+ `listRepairWorkOrders`/`listIncidents`) · **Endpoint:** `assetcore.api.imm08.list_pm_work_orders` (`api/imm08.py:28`) · **Cap:** `pm.read` → `("PM Work Order","read")` · **Tiền-điều-kiện:** bearer. Matrix nguồn: [`11 §1 Flow 5`](./11-phase-a-exit.md). Pagination + rows-key: [`04 §6.2/§8.4`](./04-api-contract.md).

> 3 GET permission-aware (scope theo user) — **invariant `count==rows`** (count khớp drill theo `permission_query_conditions`; `asset_list_count_drill_technician`). **rows-key PHÂN BIỆT @source:** imm08/09 → `data.data[]`; imm12 → `data.items[]` ([`ADR-MOBILE-001 (g)`](./ADR-MOBILE-001.md)).

### 7.1 Bước 5 — list PM của tôi — `listPmWorkOrders`

**[HARD-STOP USER]** (bearer):

```bash
curl -sS "$HOST/api/method/assetcore.api.imm08.list_pm_work_orders?page=1&page_size=20" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Expected envelope (`PmWorkOrderListEnvelope`):**

| Khía cạnh | Giá trị |
|---|---|
| HTTP line | 200 |
| `success` | `true` |
| rows-key | `data.data[]` (element `PmWorkOrderListItem` — CHỈ field imm08, C3-split) |
| Pagination | `page`/`page_size`/`total` trong `data` ([`04 §6`](./04-api-contract.md)); lặp theo `total_pages`/`len(items)` |
| `code`/`http_status` | CHỈ khi `success:false`; guest/thiếu cap = **403 status-line THẬT** (single-shape `Forbidden`) |

> **Invariant kiểm-được:** `count` (tổng) == `len(rows)` cộng dồn qua các trang khi scope-resolve theo user — nếu count > rows tổng = bug permission-drift (memory `asset_list_count_drill_technician`).

**CM/Báo hỏng (đối xứng):**

```bash
# CM của tôi — rows-key data.data[]
curl -sS "$HOST/api/method/assetcore.api.imm09.list_repair_work_orders?page=1&page_size=20" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
# Báo hỏng của tôi — rows-key data.items[]; mine=1 scope reported_by==session.user (param
#   IncidentMine, ADR-MOBILE-015); AND filter status/severity/asset/open. count==len(items).
curl -sS "$HOST/api/method/assetcore.api.imm12.list_incidents?mine=1&open=1&page=1&page_size=20" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Dart:**

```dart
final r = await WorkOrderApi(dio).listPmWorkOrders(page: 1, pageSize: 20);
// r.success==true → r.data.data (List<PmWorkOrderListItem>) + r.data.total. count==len(rows) per scope.
```

---

## 8. Flow 6 — Push FCM

**operationId trục:** `registerDeviceToken` (+ `unregisterDeviceToken`) · **Endpoint:** `assetcore.api.mobile.v1.register_device_token` · **Cap:** self-scope (bearer + DocPerm `AC Mobile Device Token`, KHÔNG cap mới) · **Tiền-điều-kiện:** P4 (FCM creds) + P5 (migrate) + reload (P3). Matrix nguồn: [`11 §1 Flow 6`](./11-phase-a-exit.md). DocType/payload: [`06`](./06-push-fcm.md) + ADR-002.

> Push = **kênh thứ 3** chèn tại `_dispatch` ([`06 §3`](./06-push-fcm.md)) — KHÔNG endpoint "nhận push" riêng. 2 endpoint device-token = vòng đời token. `user` ÉP `frappe.session.user` (server, KHÔNG client gửi → chống spoof). `register` có `@rate_limit(10/60s/IP)`. UPSERT-dedup theo `fcm_token` UNIQUE. Cơ chế = FCM Admin SDK trực tiếp (ADR-002).

### 8.1 Bước 6a — đăng ký device-token — `registerDeviceToken`

**[HARD-STOP USER]** (bearer + P4 + P5 + reload):

```bash
curl -sS -X POST "$HOST/api/method/assetcore.api.mobile.v1.register_device_token" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  --data-urlencode "fcm_token=$FCM_TOKEN" \
  --data-urlencode "platform=android" \
  --data-urlencode "device_label=Pixel-KTV-A" \
  --data-urlencode "app_version=1.0.0"
```

> Bắt buộc `fcm_token`; `platform ∈ [android, ios]` (bắt buộc khi register). `device_label`/`app_version` optional telemetry. Content oneOf json+form. `unregister` dùng CHUNG body (chỉ đọc `fcm_token`).

**Expected envelope (200-oneOf, route-by-VALUE §2.1/§2.2):**

| Trường hợp | `success` | `code` | `http_status` (body) | HTTP line | Hành động |
|---|---|---|---|---|---|
| Đăng ký OK | `true` | — | — | 200 | `data = "<hash>"` (STRING — PK record token, `services/mobile_device_token.py:153/169`) |
| `fcm_token` rỗng / `platform` ngoài enum | `false` | `VALIDATION` | `422` | **200** | hiện lỗi (`services/mobile_device_token.py:130-137`) |
| Guest/no-token | — | — | — | **403** (status-line THẬT) | dispatcher-403 single-shape → re-auth |
| Vượt rate-limit (10/60s) | — | — | — | **429** (status-line THẬT) | backoff |

### 8.2 Bước 6b — nhận push + thu hồi token — `unregisterDeviceToken`

> **Nhận push (kiểm THẬT):** sau khi `registerDeviceToken` OK, kích 1 event có push (vd flow-3 báo hỏng → KTV được giao, HOẶC flow-4 assignment) → thiết bị nhận FCM notification + deep-link (`assetcore://incident/<name>` / `assetcore://wo/pm/<name>`). Đây là **[HARD-STOP USER]** (cần thiết bị thật + FCM creds + reload).

**[HARD-STOP USER]** thu hồi (logout/gỡ app — idempotent):

```bash
curl -sS -X POST "$HOST/api/method/assetcore.api.mobile.v1.unregister_device_token" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  --data-urlencode "fcm_token=$FCM_TOKEN"
# OK 200 {"success":true,"data":null} — ack thuần (set enabled=0, GIỮ record cho audit NĐ98).
#   Idempotent: token∄ vẫn success no-op (services/mobile_device_token.py:185-188).
```

**Dart:**

```dart
await PushApi(dio).registerDeviceToken(deviceTokenRequest:
  DeviceTokenRequest(fcmToken: fcmToken, platform: 'android', deviceLabel: 'Pixel-KTV-A'));
// success==true → data = '<hash>' (String). 422 VALIDATION arrive HTTP-200 body.
// Logout: await PushApi(dio).unregisterDeviceToken(deviceTokenRequest: DeviceTokenRequest(fcmToken: fcmToken));
```

---

## 9. Đối soát E2E (acceptance runbook)

> Chốt runbook phủ ĐỦ 6 flow + kiểm-được. `[AUTO]` chạy ngay; `[HARD-STOP USER]` gộp vào DoD V-DoD (V-U4/U5).

| # | Flow | operationId trục | Endpoint @source | Tag chính | Expected (success-path) |
|---|---|---|---|---|---|
| 1 | Login (+refresh) | `getOAuthToken` | `oauth2.py:124` | [HARD-STOP USER] | 200 token passthrough `expires_in=3600` |
| 2 | Quét QR → hồ sơ | `resolveQrToken` | `api/imm00.py:588` | [HARD-STOP USER] | 200 `success:true`+`data`(asset) |
| 3 | Báo hỏng | `reportIncident` | `api/imm12.py:71` | [HARD-STOP USER] | 200 `success:true`+`data{name,status,severity}` |
| 4 | WO PM/CM/Cal | `createPmWorkOrder` | `api/imm08.py:91` | [HARD-STOP USER] | 200 `success:true`+`data{name,status,checklist_items_count}` |
| 5 | Phiếu của tôi | `listPmWorkOrders` | `api/imm08.py:28` | [HARD-STOP USER] | 200 `success:true`+`data.data[]` (count==rows) |
| 6 | Push FCM | `registerDeviceToken` | `mobile/v1` (P5 migrate) | [HARD-STOP USER] | 200 `success:true`+`data:"<hash>"` + push tới thiết bị |

**[AUTO] — 6 operationId trục phủ đủ trong runbook (kiểm-được):**

```bash
F=docs/mobile/14-e2e-field-tech-runbook.md
for op in getOAuthToken resolveQrToken reportIncident createPmWorkOrder listPmWorkOrders registerDeviceToken; do
  grep -q "$op" "$F" && echo "OK $op" || echo "MISSING $op"; done
# PASS: 6× OK
```

**[AUTO] — docset parity GREEN sau khi thêm chương 14:**

```bash
bench --site miyano run-tests --module assetcore.tests.test_mobile_docset
# PASS: Ran 9 tests ... OK (FS↔index parity 15 chương 00–14; 0 broken link; 0 placeholder ngoài code-fence)
```

**[AUTO] — contract suite XANH (route-by-VALUE + closed-schema + refresh-on-401 doc-guard):**

```bash
bench --site miyano run-tests --module assetcore.tests.test_mobile_oas
# PASS: Ran 141 tests ... OK (0 dangling $ref; 200-oneOf closed-schema; refresh-on-401 doc-guard)
```

**[HARD-STOP USER] — V-DoD validate end-to-end:** chạy tuần tự §3→§8 trên cloud staging với 1 client gen-ra (Dart/TS) — mỗi flow reproduce được, 0 bước thiếu (ACCEPTANCE-CHECKLIST V-U4/V-U5).

---

## 10. Tham chiếu chéo

- **Matrix design-time (6 flow × endpoint × cap × operationId):** [`11-phase-a-exit.md §1`](./11-phase-a-exit.md) — runbook này là phiên bản CHẠY-ĐƯỢC của matrix đó.
- **Envelope quirk (HTTP-200 route-by-VALUE + dual-403 + closed-schema):** [`04-api-contract.md §5/§5a/§5b/§5c`](./04-api-contract.md).
- **Refresh-on-401 (1 lần) + token lifecycle:** [`03-auth-oauth2.md §2.5/§2.6`](./03-auth-oauth2.md).
- **Smoke go-live (get_token + biz-call) + security gate:** [`10-deploy-ops.md §6.3`](./10-deploy-ops.md).
- **Sinh client từ OpenAPI (Dart/TS) + lớp đọc envelope:** [`09-native-repo-guide.md §2`](./09-native-repo-guide.md).
- **Push design (channel #3 `_dispatch` + DocType + deep-link):** [`06-push-fcm.md`](./06-push-fcm.md) + [`ADR-MOBILE-002.md`](./ADR-MOBILE-002.md).
- **Hợp đồng máy đọc (nguồn sinh client):** [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml) (16 path, 6 operationId trục FROZEN).
- **Roadmap EPIC-V (V1..V4) + toolchain status:** [`13-be-completion-roadmap.md §7`](./13-be-completion-roadmap.md) + [`completion/EPIC-V-codegen-verification.md`](./completion/EPIC-V-codegen-verification.md).
- **DoD/checklist nghiệm thu V-A1/V-U4/V-U5:** [`completion/ACCEPTANCE-CHECKLIST.md §5`](./completion/ACCEPTANCE-CHECKLIST.md).
