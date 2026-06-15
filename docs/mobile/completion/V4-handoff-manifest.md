# V4 — Handoff Manifest repo mobile native (EPIC-V · V-A2)

| Mục | Giá trị |
|---|---|
| Task | EPIC-V **V4** (checklist **V-A2**) — gói handoff repo mobile native |
| Loại | `[AUTO]` doc-only (KHÔNG đụng code / spec / yaml) |
| Đối tượng nhận | **Đội repo mobile native** (Phase D — repo RIÊNG, NGOÀI `assetcore`) + **[PM]** tick checklist khởi tạo |
| Hợp đồng nguồn (SSoT) | [`../openapi/assetcore-mobile.openapi.yaml`](../openapi/assetcore-mobile.openapi.yaml) (`openapi: 3.0.3`, `info.version: 0.1.0-skeleton`, 16 path/operationId FROZEN) |
| Hướng dẫn khởi tạo đầy đủ | [`../09-native-repo-guide.md`](../09-native-repo-guide.md) (§1–§6) — manifest này TRỎ NGƯỢC, KHÔNG sao chép |
| Cập nhật | 2026-06-12 |

> **Mục đích:** đóng gói **TƯỜNG MINH** 4 artifact handoff mà đội Phase D cần để khởi tạo repo native. `09-native-repo-guide.md` đã documented đầy đủ (skeleton/gen-client/ENV/OAuth/CI), nhưng RẢI khắp §1–§6 — manifest này gom thành **danh mục kiểm-được** + checklist [PM] tick.
> **Đây là tầng HANDOFF (verify + đóng gói), KHÔNG re-litigate quyết định nền** (D-AUTH/D-MVP/D-STACK — [`../00-overview.md`](../00-overview.md) §2). KHÔNG thêm field / endpoint / schema (EPIC-V §5).

---

## 0. TL;DR cho đội native (đọc theo thứ tự)

1. **COPY** yaml SSoT vào repo native (§1) — KHÔNG sửa tay, KHÔNG fork content (chống drift).
2. **Gen client** từ yaml → 16 operationId thành 16 method (§1 + [`../09-native-repo-guide.md`](../09-native-repo-guide.md) §2).
3. **Cấu hình `BASE_URL`** qua ENV (§2) — dev `http://localhost:8000` / prod placeholder (KHÔNG hardcode host).
4. **Wire OAuth2** PKCE S256 + token Keychain/Keystore + refresh-on-401 (§3 → [`../03-auth-oauth2.md`](../03-auth-oauth2.md)).
5. **Đọc envelope route-by-VALUE** — quyết định success/fail theo `body.success`/`body.code`/`body.http_status`, KHÔNG theo HTTP status-line (§4 + [`../04-api-contract.md`](../04-api-contract.md) §5).
6. **[PM] tick checklist khởi tạo repo** (§5).

---

## 1. Artifact #1 — Hợp đồng OpenAPI (yaml SSoT + version-pin)

### 1.1 Path SSoT — COPY, KHÔNG copy-ra-ngoài-rồi-sửa

| Mục | Giá trị |
|---|---|
| **Path SSoT** | `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (trong repo `assetcore`) — link: [`../openapi/assetcore-mobile.openapi.yaml`](../openapi/assetcore-mobile.openapi.yaml) |
| **Quy tắc đội native** | **COPY** file này vào `openapi/` của repo native → **gen client** từ bản copy. **KHÔNG** viết tay model/HTTP. **KHÔNG** sửa nội dung yaml sau khi copy (treat như build-input). |
| **Chống drift** | Mọi thay đổi hợp đồng đi qua yaml SSoT ở repo `assetcore` (BA cập nhật) → đội native **COPY lại + regenerate**. CI drift-gate (`git diff --exit-code` trên `api/generated/`) bắt sửa-tay / quên-regenerate. Chi tiết: [`../09-native-repo-guide.md`](../09-native-repo-guide.md) §2.4. |

> ⚠️ **KHÔNG copy yaml ra ngoài rồi tự bồi/sửa** — đó là nguồn drift. yaml SSoT giữ DUY NHẤT tại `docs/mobile/openapi/`; repo native chỉ giữ 1 bản COPY làm input gen, đồng bộ lại mỗi khi version bump (bám [`../09-native-repo-guide.md`](../09-native-repo-guide.md) §2.4).

### 1.2 Version-pin

| Mục | Giá trị |
|---|---|
| **`info.version`** | `0.1.0-skeleton` (yaml header — Phase A skeleton) |
| **Quy tắc pin** | Đội native pin version contract = `info.version` của yaml. Khi version **bump** (Phase C bồi schema 6 path nghiệp vụ) → đội native BIẾT phải COPY lại + regenerate. Versioning policy: [`../04-api-contract.md`](../04-api-contract.md) §7. |
| **16 path/operationId FROZEN** | path + operationId đã ĐÓNG BĂNG (EPIC-C DoD). Phase C/E chỉ bồi **schema `data`** bên trong, KHÔNG đổi path/operationId/security ⇒ tên method client ỔN ĐỊNH qua mọi generator. |

**16 operationId (= 16 method client gen-ra)** — auth (4) · scan/asset (3) · nghiệp vụ create (4) · list (3) · device-token (2):

| # | operationId | Nhóm |
|---|---|---|
| 1 | `authorizeOAuth` | Auth (OAuth2) |
| 2 | `getOAuthToken` | Auth (OAuth2) |
| 3 | `revokeOAuthToken` | Auth (OAuth2) |
| 4 | `getUserInfo` | Auth (userinfo) |
| 5 | `resolveQrToken` | Scan QR |
| 6 | `getAssetScanInfo` | Scan QR |
| 7 | `getAsset` | Asset detail |
| 8 | `reportIncident` | Nghiệp vụ (create) |
| 9 | `createPmWorkOrder` | Nghiệp vụ (create) |
| 10 | `createRepairWorkOrder` | Nghiệp vụ (create) |
| 11 | `createCalibration` | Nghiệp vụ (create) |
| 12 | `listPmWorkOrders` | Nghiệp vụ (list) |
| 13 | `listRepairWorkOrders` | Nghiệp vụ (list) |
| 14 | `listIncidents` | Nghiệp vụ (list) |
| 15 | `registerDeviceToken` | Device-token (push — EPIC-D) |
| 16 | `unregisterDeviceToken` | Device-token (push — EPIC-D) |

> Lệnh gen MẪU (Dart `dart-dio` / TypeScript `typescript-axios` / Kotlin `kotlin` jvm-retrofit2 — 3 generator khai trong `openapitools.json`): [`../09-native-repo-guide.md`](../09-native-repo-guide.md) §2.1/§2.2. `device-token` (15/16) thuộc **EPIC-D**; 6 path nghiệp vụ field-tech bồi schema chi tiết ở **Phase C** ([`../04-api-contract.md`](../04-api-contract.md) §10).

---

## 2. Artifact #2 — `BASE_URL` ENV (dev/prod — KHÔNG hardcode host)

yaml khai 2 server (`servers:`). App native **KHÔNG hardcode** host → đọc `BASE_URL` từ ENV (bám [`../09-native-repo-guide.md`](../09-native-repo-guide.md) §3).

| Môi trường | `BASE_URL` | Ghi chú |
|---|---|---|
| **Dev** | `http://localhost:8000` | Dev gunicorn site `miyano` — CHỈ local. (Emulator Android dùng `http://10.0.2.2:8000` map về host — [`../09-native-repo-guide.md`](../09-native-repo-guide.md) §3.2.) |
| **Prod** | `https://REPLACE-WITH-PUBLIC-HOST` | **PLACEHOLDER** — public HTTPS host THẬT do **USER set ở EPIC-G go-live** (reverse-proxy + TLS + domain). **HARD-STOP USER** — chưa tồn tại (dev hiện HTTP:80 `server_name` rỗng, [`../01-architecture.md`](../01-architecture.md) §1). |

**Quy tắc (bám [`../09-native-repo-guide.md`](../09-native-repo-guide.md) §3):**
- **KHÔNG hardcode host** trong source. Truyền qua ENV: Flutter `--dart-define=BASE_URL=...`; RN `react-native-config` / `.env`.
- **KHÔNG commit host prod thật** vào source (đọc qua ENV / secret CI).
- Cấu hình `basePath`/`baseURL` của client gen-ra = `BASE_URL` ENV — **KHÔNG** dùng `servers[0].url` cứng trong yaml làm runtime host (yaml `servers` chỉ là khai báo hợp đồng).
- Release APK trỏ `BASE_URL` **HTTPS** (prod-only); KHÔNG bật cleartext cho release.

---

## 3. Artifact #3 — Auth wiring + envelope-quirk (link deep-dive)

### 3.1 OAuth2 wiring → [`../03-auth-oauth2.md`](../03-auth-oauth2.md)

| Yêu cầu | Nguồn |
|---|---|
| **PKCE S256 public client** — KHÔNG nhúng `client_secret` trong APK; `code_challenge_method=S256` | [`../03-auth-oauth2.md`](../03-auth-oauth2.md) §1.2 |
| **Token-store Keychain/Keystore** — KHÔNG cookie/CSRF, KHÔNG SharedPrefs/log | [`../03-auth-oauth2.md`](../03-auth-oauth2.md) §2.4 |
| **Policy 401 → refresh-on-401 (1 lần) → fail thì re-auth** | [`../03-auth-oauth2.md`](../03-auth-oauth2.md) §2.5 |
| **Revoke token khi logout** (RFC 7009) | [`../03-auth-oauth2.md`](../03-auth-oauth2.md) §2.4 + `revokeOAuthToken` (op #3) |
| **Redirect-scheme** native `assetcore://oauth/callback` khớp OAuth Client (Phase B/EPIC-B) | [`../09-native-repo-guide.md`](../09-native-repo-guide.md) §4 |

> **Quyền = 1 SSoT (server-side):** sau bearer → `set_user`, RBAC capability/DocPerm theo user áp NGUYÊN VẸN. Client gen-ra **KHÔNG** parse scope để tự gate quyền (anti-pattern "hệ quyền thứ 2"). Lỗi thiếu quyền = `code=FORBIDDEN` (xem §4). Bám [`../08-security-compliance.md`](../08-security-compliance.md) + [`../03-auth-oauth2.md`](../03-auth-oauth2.md) §3.

### 3.2 Envelope-quirk → [`../04-api-contract.md`](../04-api-contract.md) §5 (BẮT BUỘC đọc kỹ)

Client gen-ra từ OpenAPI có thể coi **HTTP-200 = thành công** → SAI với lỗi NGHIỆP VỤ AssetCore (trả HTTP-200 + Error envelope, `http_status` THẬT nằm TRONG body). Đội native **PHẢI thêm lớp đọc envelope** quanh client gen-ra:
- Quyết định success/fail = **`body.success`** (boolean).
- Map lỗi theo **`body.code`** (coarse-grained, ổn định) + **`body.http_status`** (HTTP THẬT trong body).
- KHÔNG nhánh UX theo HTTP status-line cho lỗi nghiệp vụ (phần lớn arrive HTTP-200). Chi tiết + 4 ngoại lệ raw (401/403-dispatcher/429/500 = `FrappeRawError`, route theo HTTP status-line): [`../04-api-contract.md`](../04-api-contract.md) §5 + §5b.

---

## 4. Artifact #4 — Ví dụ 1-call đã-gen + lớp đọc envelope (route-by-VALUE)

Ví dụ: **`getAsset`** (op #7 — GET chi tiết thiết bị, cap `asset.read`). 200 = `oneOf [AssetDetailEnvelope (success:true) | Error (success:false)]` — **CLOSED-SCHEMA Decision-B, KHÔNG discriminator** (route theo GIÁ TRỊ disjoint required-set, [`../04-api-contract.md`](../04-api-contract.md) §5c).

### 4.1 Gọi raw (curl — minh hoạ shape envelope)

```bash
# BASE_URL từ ENV (§2) — KHÔNG hardcode host
curl -s "$BASE_URL/api/method/assetcore.api.imm00.get_asset?name=ASSET-0001" \
     -H "Authorization: Bearer $ACCESS_TOKEN"
# -> HTTP-200 + body:
#   success-case: { "success": true,  "data": { ...AssetDetail... } }
#   error-case:   { "success": false, "code": "NOT_FOUND",  "http_status": 404 }   (asset không tồn tại)
#   error-case:   { "success": false, "code": "FORBIDDEN",  "http_status": 403 }   (vendor-IDOR in-handler)
```

### 4.2 Lớp đọc envelope quanh client gen-ra (route-by-VALUE — KHÔNG discriminator)

```dart
// Pseudo-Dart — client gen-ra trả AssetDetailEnvelope|Error oneOf (closed-schema).
// Route THEO GIÁ TRỊ body.success/body.code/body.http_status (KHÔNG HTTP status-line, KHÔNG discriminator-object).
final body = await api.getAsset(name: 'ASSET-0001');   // method = operationId
if (body.success == true) {
  final asset = body.data;                 // AssetDetailEnvelope.data
  // ... render hồ sơ thiết bị
} else {
  switch (body.code) {                     // coarse-grained, ổn định (KHÔNG parse string `error`)
    case 'NOT_FOUND':  /* body.http_status == 404 */ showNotFound();      break;
    case 'FORBIDDEN':  /* body.http_status == 403 */ showNoPermission();  break;  // KHÔNG re-auth (in-handler cap-403)
    default:           showError(body.code, body.httpStatus);
  }
}
// LƯU Ý: quyết định success/fail = body.success — KHÔNG dựa HTTP status-line (lỗi nghiệp vụ arrive HTTP-200, §3.2).
// Ngoại lệ raw (dispatcher-403 guest / 401 bearer-hết-hạn / 429 / 500) = FrappeRawError → route theo HTTP status-line
// (refresh-on-401 §3.1 / re-auth / backoff). Chi tiết: ../04-api-contract.md §5 + §5b.
```

> Quy tắc **route-by-VALUE** áp CHO MỌI endpoint nghiệp vụ (Decision-B closed-schema, KHÔNG boolean-discriminator-object): đọc `body.success` → thành công lấy `data`, lỗi nhánh theo `body.code`+`body.http_status`. Hợp đồng đầy đủ + 4 ngoại lệ raw: [`../04-api-contract.md`](../04-api-contract.md) §4/§5/§5b.

---

## 5. Checklist khởi tạo repo native — cho [PM] / đội Phase D tick

> Mirror [`../09-native-repo-guide.md`](../09-native-repo-guide.md) §6.2 (checklist khởi tạo repo). Tick khi DONE; cột "Nguồn" trỏ section hướng dẫn chi tiết.

- [ ] **Chốt D-STACK** (Flutter HOẶC React Native) theo trade-off — ghi quyết định. _(Nguồn: [`../09-native-repo-guide.md`](../09-native-repo-guide.md) §1.1)_
- [ ] **Skeleton repo native** riêng (ngoài `assetcore`) theo layout §1.2 (Flutter) / §1.3 (RN). _(§1)_
- [ ] **COPY** `assetcore-mobile.openapi.yaml` từ repo `assetcore` vào `openapi/` repo native (KHÔNG sửa tay). _(§1 + [`../09-native-repo-guide.md`](../09-native-repo-guide.md) §2.4)_
- [ ] **Gen client** từ yaml → **16 operationId = 16 method** (`api/generated/`). _([`../09-native-repo-guide.md`](../09-native-repo-guide.md) §2.1/§2.2)_
- [ ] **Lớp đọc envelope** (`body.success`/`body.code`/`body.http_status`) quanh client gen-ra. _(§4 + [`../04-api-contract.md`](../04-api-contract.md) §5)_
- [ ] **ENV `BASE_URL`** (dev `localhost:8000` / prod HTTPS) — KHÔNG hardcode host. _(§2 + [`../09-native-repo-guide.md`](../09-native-repo-guide.md) §3)_
- [ ] **OAuth wiring**: PKCE S256 + redirect-scheme `assetcore://oauth/callback` + token Keychain/Keystore + 401→refresh→re-auth + revoke logout. _(§3 + [`../03-auth-oauth2.md`](../03-auth-oauth2.md))_
- [ ] **Build APK debug** trỏ BE dev → smoke login + quét QR + 1 luồng nghiệp vụ. _([`../09-native-repo-guide.md`](../09-native-repo-guide.md) §5.1)_
- [ ] **CI**: lint + gen-client-from-yaml + **drift-gate** (`git diff --exit-code` trên `api/generated/`) + build. _([`../09-native-repo-guide.md`](../09-native-repo-guide.md) §5.2 + §2.4)_
- [ ] _(Chờ EPIC-B/Phase B — HARD-STOP USER)_ Nhận public HTTPS host + `client_id` OAuth Client từ USER → cấu hình prod ENV.
- [ ] _(Chờ Phase C)_ Khi yaml bồi 6 path nghiệp vụ → version bump → COPY lại + regenerate client. _([`../09-native-repo-guide.md`](../09-native-repo-guide.md) §2.4)_

---

## 6. Invariant bảo mật trong manifest (BẢO TOÀN — EPIC-V §6)

- **RBAC 1-SSoT server-side:** client gen-ra **KHÔNG** tự gate quyền; quyền áp ở BE theo user sau `set_user` (capability/DocPerm). KHÔNG dựng "hệ quyền thứ 2" trong app.
- **PKCE public client:** KHÔNG commit `client_secret`/keystore vào repo native (signing-key = secret CI store, §3.1).
- **Native APK KHÔNG cần CORS:** request không từ browser-origin ⇒ `allow_cors` chỉ liên quan FE web, KHÔNG app native ([`../08-security-compliance.md`](../08-security-compliance.md)).
- **Token-store an toàn:** Keychain/Keystore — KHÔNG cookie/CSRF/SharedPrefs/log (§3.1).

---

## Tham chiếu chéo

- Hướng dẫn khởi tạo repo native (skeleton/gen/ENV/OAuth/CI/checklist): [`../09-native-repo-guide.md`](../09-native-repo-guide.md) §1–§6
- Hợp đồng máy đọc (nguồn sinh client): [`../openapi/assetcore-mobile.openapi.yaml`](../openapi/assetcore-mobile.openapi.yaml)
- Auth deep-dive (PKCE/refresh/revoke/token-store/policy 401): [`../03-auth-oauth2.md`](../03-auth-oauth2.md)
- Hợp đồng API (envelope · ErrorCode · quirk HTTP-200 route-by-VALUE): [`../04-api-contract.md`](../04-api-contract.md) §4 · §5 · §5b
- E2E runbook field-tech (V3 — 6 flow tuần tự): [`../14-e2e-field-tech-runbook.md`](../14-e2e-field-tech-runbook.md)
- Traceability matrix 6 flow (màn→endpoint→cap→operationId): [`../11-phase-a-exit.md`](../11-phase-a-exit.md) §1
- ADR kiến trúc (OpenAPI=hợp đồng decision (d); RBAC 1-SSoT decision (b)): [`../ADR-MOBILE-001.md`](../ADR-MOBILE-001.md)
- 3 quyết định nền (D-AUTH/D-MVP/D-STACK) + glossary: [`../00-overview.md`](../00-overview.md) §2
- Task EPIC-V V4 + acceptance: [`./EPIC-V-codegen-verification.md`](./EPIC-V-codegen-verification.md) §4 (V4)
- Checklist nghiệm thu EPIC-V (V-A2): [`./ACCEPTANCE-CHECKLIST.md`](./ACCEPTANCE-CHECKLIST.md)
