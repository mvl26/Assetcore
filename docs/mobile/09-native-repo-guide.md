# 09 — Hướng dẫn khởi tạo REPO MOBILE NATIVE từ hợp đồng OpenAPI

| Mục | Giá trị |
|---|---|
| Initiative | AssetCore Mobile — backend-for-mobile |
| Phase | **A — Kiến trúc & Feasibility** (A8 · handoff repo native cho Phase D) |
| Bám quyết định | **D-STACK** (native) · D-AUTH (OAuth2 + refresh) · D-MVP (field-tech) — `00-overview.md §2` |
| Owner | BA Lead + System Architect (mobile) · repo native do đội Phase D triển khai (ngoài repo) |
| Trạng thái | In Progress (Phase A) |
| Cập nhật | 2026-06-09 |

> **Mục đích:** đây là **HỢP ĐỒNG HANDOFF** cho đội triển khai **repo mobile native** (Phase D, NGOÀI repo `assetcore`). Tài liệu trả lời 1 câu hỏi: *"có sẵn hợp đồng OpenAPI rồi thì khởi tạo repo native thế nào?"* — skeleton repo, sinh API client từ OpenAPI, trỏ ENV về BE, wire OAuth2, build APK + CI.
> **KHÔNG impl code trong repo `assetcore`.** Mọi đoạn lệnh generator/build dưới đây là **mẫu/minh hoạ (illustrative)** — CHƯA verify chạy trong môi trường này; đội Phase D xác minh tại máy build của mình.
> Mọi tham chiếu artifact đều trỏ file CÓ THẬT trong docset (xem `00-overview.md §4`). Phần OAuth2 **LINK** sang `03-auth-oauth2.md` — KHÔNG viết lại.
> **Chỉ mục docset:** [`README.md`](./README.md) · [`00-overview.md`](./00-overview.md) · [`01-architecture.md`](./01-architecture.md) · [`03-auth-oauth2.md`](./03-auth-oauth2.md) · [`04-api-contract.md`](./04-api-contract.md) · [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml)

---

## 0. Context / Scope / Actor + ranh giới repo

### 0.1 Bối cảnh

3 quyết định nền (`00-overview.md §2`) định khung tài liệu này: **D-STACK** — app là **native** (Flutter HOẶC React Native), KHÔNG WebView/PWA-wrapper; UI ở **repo riêng**, chỉ **GỌI API**. Repo `assetcore` cung cấp **backend + hợp đồng OpenAPI** (`OpenAPI = HỢP ĐỒNG` — `ADR-MOBILE-001` decision (d)). Hợp đồng đã có: [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml) (skeleton Phase A; 6 path nghiệp vụ bồi schema chi tiết ở Phase C).

### 0.2 Scope tài liệu này

| Trong scope (handoff Phase D) | Ngoài scope |
|---|---|
| Skeleton repo native (Flutter + React Native) + trade-off để chốt D-STACK | Tạo repo native THẬT (Phase D, ngoài repo) |
| Lệnh **mẫu** sinh API client từ OpenAPI (Dart/dio + TS) | Sửa `openapi/*.yaml` path/operationId (đã chốt; thuộc Phase C/E) |
| Cấu hình ENV trỏ BE (BASE_URL dev/prod) | Set public HTTPS host / `allow_cors` / OAuth Client (Phase B — HARD-STOP USER) |
| Wire OAuth2 trong app (LINK sang `03`) | Viết lại đặc tả OAuth2 (đã có ở `03-auth-oauth2.md`) |
| Build APK debug/release + gợi ý CI | Pipeline CI cụ thể của hạ tầng user · store release (Phase F) |
| Checklist khởi tạo repo + cross-link 2 chiều | Deploy/ops go-live runbook (đẩy backlog — xem §7) · impl code BE nghiệp vụ |

### 0.3 Actor

| Actor | Vai trò |
|---|---|
| **Đội repo native** (Phase D) | Đối tượng đọc chính: khởi tạo repo, sinh client, build APK theo guide này. |
| **BA / System Architect** (repo `assetcore`) | Giữ hợp đồng OpenAPI đồng bộ endpoint thật; trả lời drift contract. |
| **USER / Admin** (HARD-STOP) | Phase B: public HTTPS host, OAuth Client, site_config — KHÔNG thuộc đội native, KHÔNG thuộc BA. |
| **Field-technician** | Người dùng cuối APK (D-MVP) — không thao tác repo. |

### 0.4 Ranh giới repo (KHÔNG nhập nhằng)

```
┌─────────────────────────────┐        ┌──────────────────────────────┐
│  REPO `assetcore` (đây)      │        │  REPO MOBILE NATIVE (Phase D) │
│  - Backend 3-tier (IMM-*)    │  hợp   │  - UI native (D-STACK)        │
│  - Hợp đồng OpenAPI yaml ────┼─đồng──▶│  - API client SINH từ yaml    │
│  - OAuth2 provider (wire)    │  API   │  - OAuth2 client (PKCE)       │
│  - docset mobile (00–09)     │        │  - offline cache / push (E)   │
└─────────────────────────────┘        └──────────────────────────────┘
        BE + contract                          UI + gọi API
```

- Repo native **NGOÀI** `assetcore` — bám 3 lằn ranh trách nhiệm (`01-architecture.md §2`): ① UI native (repo riêng) · ② API contract (repo `assetcore`, yaml) · ③ Business logic (repo `assetcore`, reuse). App native CHỈ thuộc ①, **chỉ gọi API** xuống ③ qua hợp đồng ②.
- App native **KHÔNG** nhúng business rule, **KHÔNG** dựng hệ quyền thứ 2 (quyền = ③ RBAC capability/DocPerm theo user, `03-auth-oauth2.md §3`).

---

## 1. Skeleton repo native (Flutter VÀ React Native)

> Nêu cấu trúc đề xuất cho **cả hai** stack để đội Phase D **chốt D-STACK** dựa trên trade-off — **KHÔNG ép chọn**. Chọn 1, áp 1 layout; phần generator (§2) + ENV (§3) + OAuth (§4) viết cho cả hai.

### 1.1 Trade-off chọn stack (input để chốt D-STACK)

| Tiêu chí | Flutter (Dart) | React Native (TS) |
|---|---|---|
| Ngôn ngữ | Dart | TypeScript (gần FE web Vue/TS hiện tại) |
| Sinh client từ OpenAPI | `openapi-generator` generator **`dart-dio`** (HTTP lib dio) | `openapi-generator` generator **`typescript-axios`** / `typescript-fetch` |
| Quét QR (D-MVP bước 2) | `mobile_scanner` / `qr_code_scanner` | `react-native-vision-camera` + code-scanner |
| Lưu token an toàn (`03 §2.4`) | `flutter_secure_storage` (Keychain/Keystore) | `react-native-keychain` |
| OAuth + PKCE (`03 §1`) | `flutter_appauth` / `oauth2` + `crypto` (S256) | `react-native-app-auth` |
| Push FCM (Phase E, `06-push-fcm.md`) | `firebase_messaging` | `@react-native-firebase/messaging` |
| Tái dùng kỹ năng đội | Cần Dart | Trùng TS với FE web (`frontend/`) |
| Build APK | `flutter build apk` | Gradle (`./gradlew assembleRelease`) |

> Cả hai stack đều thoả D-STACK (native, HTTP-client riêng KHÔNG chịu CORS browser, PKCE S256 — `01-architecture.md §1`). Quyết định cuối thuộc đội Phase D; tài liệu này không khoá.

> **V3-BA — chốt "Dart/Kotlin vs Dart+TypeScript" (EPIC-V V3, 2026-06-12).** DoD EPIC-V ghi "gen client **Dart/Kotlin**" trong khi PROSE-SAMPLE chương này chỉ minh hoạ **Dart** (`dart-dio` §2.1) + **TypeScript** (`typescript-axios` §2.2). Reconcile **KHÔNG để mâu thuẫn config↔docset**:
> - **Codegen-config (`openapitools.json` SSoT) = 3 generator THẬT:** `mobile-dart` (`dart-dio`) · `mobile-kotlin` (`kotlin`, `library: jvm-retrofit2`) · `mobile-typescript` (`typescript-axios`). ⇒ **Kotlin LÀ target codegen hợp lệ** (DoD "Dart/Kotlin" thoả ở tầng config — V-U1/V-U2 verify Dart+Kotlin). Đây là SSoT quyết định, KHÔNG phải prose-sample.
> - **Prose-sample chương 09 = Dart + TypeScript** (2 generator điển hình của trade-off §1.1 Flutter vs RN). **Kotlin = config-only** (chạy được từ `openapitools.json` khi USER cấp toolchain `java`+`npx`; KHÔNG cần sample prose riêng — tên method = `operationId` ổn định mọi generator, §2.3). Thêm sample Kotlin = bloat KHÔNG cần (3 generator dùng CÙNG yaml + CÙNG operationId).
> - **Kết luận (KHÔNG re-litigate):** DoD GIỮ "Dart bắt buộc; Kotlin/TS theo `openapitools.json`" — KHÔNG narrow về "Dart + TypeScript" (sẽ bỏ rơi target Kotlin đã khai trong config + DoD). Docset phủ: Dart-sample + TS-sample (prose) + Dart/Kotlin/TS (config runnable). Hết mâu thuẫn.

### 1.2 Skeleton Flutter (đề xuất)

```
assetcore-mobile/                # repo native riêng (ngoài assetcore)
├── pubspec.yaml                 # deps: dio, flutter_secure_storage, flutter_appauth, mobile_scanner, firebase_messaging
├── openapi/
│   └── assetcore-mobile.openapi.yaml   # COPY từ repo assetcore (single source — xem §2.4 chống drift)
├── lib/
│   ├── main.dart
│   ├── config/
│   │   └── env.dart             # BASE_URL từ --dart-define (§3)
│   ├── api/
│   │   └── generated/           # OUTPUT openapi-generator (dart-dio) — KHÔNG sửa tay
│   ├── auth/
│   │   ├── oauth_service.dart   # PKCE + authorize + token + refresh + revoke (§4 → 03)
│   │   └── token_store.dart     # flutter_secure_storage (Keychain/Keystore)
│   ├── features/
│   │   ├── scan/                # MVP-2 quét QR → hồ sơ thiết bị
│   │   ├── incident/            # MVP-3 báo hỏng
│   │   ├── work_order/          # MVP-4 PM/CM/Hiệu chuẩn
│   │   └── my_tickets/          # MVP-5 phiếu của tôi
│   └── core/
│       └── api_client.dart      # interceptor: gắn bearer + xử lý 401→refresh (§4 → 03 §2.5)
├── android/                     # cấu hình intent-filter custom-scheme (§4) + applicationId
├── ios/                         # URL Type custom-scheme (§4)
├── tool/
│   └── gen-client.sh            # lệnh sinh client (§2) — CI gọi
└── .github/workflows/ci.yml     # lint + gen-client + build (§5)
```

### 1.3 Skeleton React Native (đề xuất)

```
assetcore-mobile/                # repo native riêng (ngoài assetcore)
├── package.json                 # deps: axios, react-native-keychain, react-native-app-auth,
│                                #       react-native-vision-camera, @react-native-firebase/messaging
├── openapi/
│   └── assetcore-mobile.openapi.yaml   # COPY từ repo assetcore (§2.4)
├── src/
│   ├── config/
│   │   └── env.ts               # BASE_URL từ react-native-config / .env (§3)
│   ├── api/
│   │   └── generated/           # OUTPUT openapi-generator (typescript-axios) — KHÔNG sửa tay
│   ├── auth/
│   │   ├── oauthService.ts      # PKCE + authorize + token + refresh + revoke (§4 → 03)
│   │   └── tokenStore.ts        # react-native-keychain (Keychain/Keystore)
│   ├── features/
│   │   ├── scan/                # MVP-2
│   │   ├── incident/            # MVP-3
│   │   ├── workOrder/           # MVP-4
│   │   └── myTickets/           # MVP-5
│   └── core/
│       └── apiClient.ts         # axios interceptor: bearer + 401→refresh (§4 → 03 §2.5)
├── android/                     # intent-filter custom-scheme (§4)
├── ios/                         # URL Type custom-scheme (§4)
├── scripts/
│   └── gen-client.sh            # lệnh sinh client (§2)
└── .github/workflows/ci.yml     # lint + gen-client + build (§5)
```

---

## 2. Sinh API client TỪ OpenAPI

> Hợp đồng nguồn = [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml) (`openapi: 3.0.3`, `info.title: AssetCore Mobile API`, `version: 0.1.0-skeleton`). Repo native **sinh** client từ file này — KHÔNG viết tay model/HTTP. (Bám `ADR-MOBILE-001` decision (d): "OpenAPI viết tay là HỢP ĐỒNG … để sinh API client + chống drift".)

> ⚠️ **Tất cả lệnh dưới là MẪU/MINH HOẠ — CHƯA verify chạy trong môi trường này.** Tên generator (`dart-dio`, `typescript-axios`) là generator chính thức của `openapi-generator`; đội Phase D xác minh phiên bản generator + chạy thực tế tại máy build. Có thể dùng `openapi-generator-cli` (Java) HOẶC `swagger-codegen` tương đương.

### 2.1 Flutter — generator `dart-dio` (HTTP lib dio)

```bash
# MẪU — chưa verify chạy. openapi-generator-cli (npm wrapper hoặc jar).
npx @openapitools/openapi-generator-cli generate \
  -i openapi/assetcore-mobile.openapi.yaml \
  -g dart-dio \
  -o lib/api/generated \
  --additional-properties=pubName=assetcore_api,nullableFields=true
# → sinh model (Envelope/Error/Pagination…) + API class theo tag (auth/asset/incident/work-order)
```

### 2.2 React Native — generator `typescript-axios`

```bash
# MẪU — chưa verify chạy.
npx @openapitools/openapi-generator-cli generate \
  -i openapi/assetcore-mobile.openapi.yaml \
  -g typescript-axios \
  -o src/api/generated \
  --additional-properties=supportsES6=true,withSeparateModelsAndApi=true
# → sinh interface (Envelope/Error/Pagination…) + *Api class theo tag
```

> Generator hợp lệ khác (chọn theo team): `dart` (HTTP lib `http` thay dio) cho Flutter; `typescript-fetch` cho RN không muốn axios. Liệt kê đầy đủ: `openapi-generator-cli list`.

### 2.3 Lưu ý hợp đồng khi dùng client sinh ra

- **Tên method client = `operationId`** (KHÔNG auto-derive từ path): `openapi-generator` đặt tên method API client THEO `operationId` của từng operation (vd `getAsset()`, `createPmWorkOrder()`, `getOAuthToken()`). Yaml mobile đã có **15/15 `operationId` ổn định** (A10 — convention [`04-api-contract.md §8.1`](./04-api-contract.md)) ⇒ tên method sinh ra ỔN ĐỊNH, KHÔNG phụ thuộc generator tự chế tên từ URL (tránh tên xấu/lệch giữa Dart vs TS). **KHÔNG đổi `operationId`** đã chốt — đổi = breaking mọi client đã sinh; 2 device-token (`registerDeviceToken`/`unregisterDeviceToken`) đặc biệt đóng băng (chốt A5).
- **Codegen-validity (0 dangling `$ref`):** trước khi sinh model, generator resolve mọi `$ref`. Yaml mobile đã được guard **0 dangling** + orphan-component ⊆ allow-list RESERVED (forward-reserve offline/pagination + `OAuth2` false-orphan) ⇒ generator **chạy không crash** + KHÔNG sinh model rỗng/dead-surface. Hợp đồng đầy đủ + bảng RESERVED 10 mục + lý do giữ từng orphan: [`04-api-contract.md §8.2`](./04-api-contract.md). Guard = `assetcore/tests/guards/test_mobile_oas.py` (`TC-MOB-OAS-09/10/11`). A13: error-response coverage máy-đọc — generated client sinh sẵn nhánh **401** (toàn bộ 12 path MVP → refresh/re-auth) + **429** (2 path `@rate_limit` → backoff). Nếu Phase C/E bồi component vào path (hết orphan) → gỡ mục đó khỏi allow-list guard (xem §8.2).
- **Envelope HTTP-200 quirk:** lỗi NGHIỆP VỤ trả HTTP 200 + error envelope (`http_status` THẬT nằm TRONG body). Client sinh ra có thể coi HTTP-200 là "thành công" → **đội native PHẢI thêm lớp đọc `body.success` + `body.code`** quanh client sinh ra. Hợp đồng đầy đủ: [`04-api-contract.md §5`](./04-api-contract.md) (+ §2 success envelope, §3 error envelope).
- **ErrorCode:** nhánh UX theo `body.code` (15 mã — `04-api-contract.md §4`), KHÔNG parse string `error`.
- **Pagination:** lặp trang theo `total_pages`/`len(items)` (`04-api-contract.md §6`).
- **401 raw (gap đã ghi):** 401 Guest hiện trả raw Frappe traceback (KHÔNG envelope sạch) → client sinh ra có thể deser-fail. Client phải fallback HTTP status line cho 401/403/429/500. Xem [`04-api-contract.md §5`](./04-api-contract.md) (ngoại lệ HTTP thật) + [`03-auth-oauth2.md`](./03-auth-oauth2.md) (A2 live-finding).
- **6 path nghiệp vụ còn STUB:** ở skeleton Phase A, 6 path field-tech (`resolve_qr_token`/`get_asset_scan_info`/`get_asset`/`report_incident`/`create_*`/`list_*`) chưa có schema `data` chi tiết — client sinh ra trả `data` generic tới khi **Phase C** bồi. Đội native bám bảng "việc Phase C" (`04-api-contract.md §10`).

### 2.4 Chống drift — regenerate khi contract đổi (BẮT BUỘC)

> `ADR-MOBILE-001` (d): OpenAPI là hợp đồng để **chống drift**. Drift = client native lệch endpoint thật BE → lỗi runtime âm thầm.

- Khi BE đổi hợp đồng (BA cập nhật `openapi/assetcore-mobile.openapi.yaml` ở repo `assetcore`, vd Phase C bồi 6 path): repo native **COPY lại** yaml mới rồi **regenerate** client (§2.1/§2.2).
- KHÔNG sửa tay file trong `api/generated/` — mọi thay đổi phải đi qua yaml + regenerate (treat generated như build artifact).
- **CI gate:** thêm bước "gen-client từ yaml" trong CI (§5) — nếu output khác bản commit → fail (phát hiện ai đó sửa tay HOẶC quên regenerate). Đây là cơ chế chống drift tự động.
- Khuyến nghị: pin **version contract** = `info.version` của yaml (`0.1.0-skeleton`); khi version bump (Phase C) → đội native biết phải regenerate. (Versioning: `04-api-contract.md §7`.)

---

## 3. Cấu hình ENV trỏ BE (KHÔNG hardcode host)

> yaml có 2 server: `https://REPLACE-WITH-PUBLIC-HOST` (placeholder Phase B) + `http://localhost:8000` (dev). App native **KHÔNG hardcode** host → đọc từ biến ENV `BASE_URL`.

### 3.1 Phân biệt dev vs prod

| Môi trường | BASE_URL | Ghi chú |
|---|---|---|
| **Dev (local)** | `http://localhost:8000` (HOẶC IP LAN của máy chạy `bench start`, vd `http://192.168.x.x:8000`) | Trùng server #2 của yaml. Emulator Android → host `10.0.2.2:8000` (alias localhost của host). HTTP cleartext chỉ cho dev. |
| **Prod** | `https://<public-host>` thay cho `REPLACE-WITH-PUBLIC-HOST` | Public HTTPS host do **Phase B** cấp (HARD-STOP USER — `01-architecture.md §1` ghi chú topology; `02-deploy-feasibility.md`). Bearer-over-HTTPS bắt buộc (`03 §5`). |

> ⚠️ `REPLACE-WITH-PUBLIC-HOST` là **placeholder** — Phase B (USER) mới có host thật (chưa tồn tại: dev hiện HTTP:80 `server_name` rỗng — `01-architecture.md §1`). App native KHÔNG được commit host thật vào source; đọc qua ENV/secret CI.

### 3.2 Truyền BASE_URL — KHÔNG hardcode

**Flutter** (`--dart-define`, đọc trong `config/env.dart`):

```dart
// config/env.dart — MẪU
class Env {
  static const baseUrl = String.fromEnvironment(
    'BASE_URL',
    defaultValue: 'http://localhost:8000', // chỉ dev; prod truyền qua --dart-define
  );
}
// build dev:  flutter run --dart-define=BASE_URL=http://10.0.2.2:8000
// build prod: flutter build apk --dart-define=BASE_URL=https://<public-host>
```

**React Native** (`react-native-config` / `.env`, đọc trong `config/env.ts`):

```ts
// config/env.ts — MẪU
import Config from 'react-native-config';
export const BASE_URL = Config.BASE_URL ?? 'http://10.0.2.2:8000'; // dev fallback
// .env.dev:  BASE_URL=http://10.0.2.2:8000
// .env.prod: BASE_URL=https://<public-host>   (KHÔNG commit .env.prod chứa host thật)
```

- Cấu hình `basePath`/`baseURL` của client sinh ra (§2) = `Env.baseUrl` / `BASE_URL` — KHÔNG dùng `servers[0].url` cứng trong yaml làm runtime host.
- Android release HTTPS-only: KHÔNG bật `usesCleartextTraffic` cho prod (chỉ dev).

---

## 4. Wire OAuth2 trong app native (TÁI DÙNG đặc tả 03 — KHÔNG viết lại)

> Toàn bộ đặc tả OAuth2 đã ở [`03-auth-oauth2.md`](./03-auth-oauth2.md). Mục này CHỈ **map đặc tả → bước wiring trong app** + LINK; KHÔNG lặp lại sequence/evidence.

### 4.1 Map đặc tả 03 → việc app native phải làm

| Việc trong app native | Đặc tả nguồn (KHÔNG lặp lại ở đây) |
|---|---|
| Sinh `code_verifier` + `code_challenge = BASE64URL-no-pad(SHA256(verifier))`, `code_challenge_method=S256` | [`03-auth-oauth2.md §1.1`](./03-auth-oauth2.md) bước (a) + §1.2 |
| Mở `/authorize` (WebView/Custom Tab) với `client_id`/`redirect_uri`/`response_type=code`/`code_challenge` | [`03 §1`](./03-auth-oauth2.md) bước (b); params yaml path `oauth2.authorize` |
| Đăng ký **redirect-scheme `assetcore://oauth/callback`** (Android intent-filter / iOS URL Type) để bắt redirect | [`03 §1.3`](./03-auth-oauth2.md) (ghi chú custom-scheme); phải KHỚP `default_redirect_uri` OAuth Client (`03 §4`, Phase B) |
| Đổi `code` + `code_verifier` → token tại `/get_token` (`grant_type=authorization_code`) | [`03 §1`](./03-auth-oauth2.md) bước (c); yaml path `oauth2.get_token` |
| **Lưu token Keychain/Keystore** (KHÔNG cookie/CSRF, KHÔNG SharedPrefs/log) | [`03 §2.4`](./03-auth-oauth2.md) |
| Gắn `Authorization: Bearer <access>` mọi request (interceptor) | [`03 §1`](./03-auth-oauth2.md) bước (d) |
| **Policy 401 → refresh MỘT lần → retry; refresh fail → re-auth** | [`03 §2.5`](./03-auth-oauth2.md) (bảng policy app) |
| **Revoke khi logout / mất máy** (RFC 7009) | [`03 §2.3`](./03-auth-oauth2.md) + §2.5; yaml path `oauth2.revoke_token` |

### 4.2 Điểm wiring cụ thể (KHÔNG đặc tả lại nghiệp vụ OAuth)

- **Interceptor HTTP** (`core/api_client.*`): trước mỗi request gắn bearer từ `token_store`; bắt response 401 → gọi refresh đúng **policy `03 §2.5`** (refresh 1 lần, fail → xoá token + re-auth). KHÔNG vòng lặp refresh vô hạn.
- **redirect-scheme**: khai báo `assetcore://oauth/callback` ở native config (Android `intent-filter` trong `AndroidManifest.xml`; iOS `CFBundleURLTypes` trong `Info.plist`). Giá trị **phải KHỚP** `redirect_uris`/`default_redirect_uri` OAuth Client (USER tạo ở Phase B — `03 §4`).
- **PKCE S256** bắt buộc (public client — KHÔNG nhúng `client_secret` trong APK): dùng lib OAuth của stack (`flutter_appauth` / `react-native-app-auth`) HOẶC tự sinh PKCE với crypto lib. Công thức S256: `03 §1.2` bước (a).
- **Quyền = 1 SSoT:** sau bearer→`set_user`, RBAC capability/DocPerm theo user áp nguyên vẹn. App **KHÔNG** parse scope để tự gate quyền (anti-pattern "hệ quyền thứ 2" — `03 §3.2`). Lỗi thiếu quyền = `code=FORBIDDEN` VI sạch (`04 §4`).

---

## 5. Build APK + CI

> Lệnh build/CI dưới là **MẪU/MINH HOẠ — CHƯA verify chạy** trong môi trường này; đội Phase D xác minh tại hạ tầng của mình. CI **KHÔNG phụ thuộc** hạ tầng cụ thể nào (mô tả ở mức bước logic).

### 5.1 Build APK debug / release

**Flutter** (mẫu):

```bash
# Debug (test nhanh, ký debug-key tự động)
flutter build apk --debug --dart-define=BASE_URL=http://10.0.2.2:8000

# Release (ký release-key — keystore do đội native quản, KHÔNG commit)
flutter build apk --release --dart-define=BASE_URL=https://<public-host>
# → build/app/outputs/flutter-apk/app-release.apk
```

**React Native** (mẫu, Gradle):

```bash
cd android
./gradlew assembleDebug      # → app/build/outputs/apk/debug/app-debug.apk
./gradlew assembleRelease    # → app/build/outputs/apk/release/app-release.apk (cần signingConfig release)
```

- **Signing release:** keystore + mật khẩu là secret của đội native (CI secret store), **KHÔNG commit** vào repo.
- **HTTPS prod-only:** release APK trỏ `BASE_URL` HTTPS (§3); KHÔNG bật cleartext cho release.

### 5.2 Gợi ý pipeline CI (mức logic — không khoá hạ tầng)

```
CI pipeline (mẫu — chạy trên runner bất kỳ: GitHub Actions / GitLab CI / Jenkins):
  1. checkout
  2. setup toolchain (Flutter SDK / Node + JDK + Android SDK)
  3. install deps           (flutter pub get / npm ci)
  4. LINT                   (flutter analyze / eslint + tsc)
  5. GEN-CLIENT-FROM-YAML   (§2: openapi-generator từ openapi/*.yaml)
       └─ DRIFT GATE: git diff --exit-code trên api/generated/  → fail nếu lệch (§2.4)
  6. TEST                   (flutter test / jest) — nếu có
  7. BUILD                  (flutter build apk / ./gradlew assembleRelease)
  8. artifact: app-release.apk  (+ store upload ở Phase F, KHÔNG ở guide này)
```

- **Bước 5 (gen-client) + drift gate** là cốt lõi chống drift (§2.4): CI tự sinh client từ yaml mỗi lần → đảm bảo client luôn khớp hợp đồng.
- Pipeline mô tả **bước logic**, không ép runner/cloud cụ thể — đội Phase D ánh xạ sang công cụ CI họ dùng.
- Store release (Play Console / TestFlight) + UAT field-tech thuộc **Phase F** (`00-overview.md §3`) — KHÔNG trong guide này.

---

## 6. Cross-link 2 chiều + checklist khởi tạo repo

### 6.1 Cross-link 2 chiều

| Chủ đề | Tài liệu (repo `assetcore`) |
|---|---|
| Tổng quan · 3 quyết định chốt (D-AUTH/D-MVP/D-STACK) · glossary | [`00-overview.md`](./00-overview.md) §2 · §7 |
| Chỉ mục docset đầy đủ + lộ trình đọc | [`README.md`](./README.md) |
| Kiến trúc (topology · 3 lằn ranh · versioning · OpenAPI=hợp đồng) | [`01-architecture.md`](./01-architecture.md) §1 · §2 · §4 · §5 |
| Auth deep-dive (PKCE/refresh/revoke/storage/policy 401) | [`03-auth-oauth2.md`](./03-auth-oauth2.md) §1 · §2.4 · §2.5 · §3 |
| Hợp đồng API (envelope · ErrorCode · pagination · quirk HTTP-200) | [`04-api-contract.md`](./04-api-contract.md) §2 · §3 · §4 · §5 · §6 |
| ADR kiến trúc (OpenAPI=hợp đồng decision (d)) | [`ADR-MOBILE-001.md`](./ADR-MOBILE-001.md) |
| Hợp đồng máy đọc (nguồn sinh client) | [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml) |

> Cross-link NGƯỢC: chương này được trỏ tới từ `00-overview.md` (§3 roadmap A8 · §4 chỉ mục · §6 số đã cấp) + `README.md` (chỉ mục docset).

### 6.2 Checklist khởi tạo repo native (cho [PM] / đội Phase D tick)

- [ ] **Chốt D-STACK** (Flutter HOẶC React Native) dựa §1.1 trade-off — ghi quyết định.
- [ ] Tạo repo native riêng (ngoài `assetcore`) + skeleton thư mục theo §1.2 (Flutter) hoặc §1.3 (RN).
- [ ] COPY `openapi/assetcore-mobile.openapi.yaml` từ repo `assetcore` vào `openapi/` của repo native (§2.4).
- [ ] Cài generator (`openapi-generator-cli`) + chạy gen-client (§2.1 Flutter / §2.2 RN) → `api/generated/`.
- [ ] Thêm lớp đọc envelope (`body.success`/`body.code`/`http_status`) quanh client sinh ra (§2.3 + `04 §5`).
- [ ] Cấu hình ENV `BASE_URL` (dev `localhost:8000` / prod HTTPS) — KHÔNG hardcode host (§3).
- [ ] Wire OAuth2: PKCE S256 + redirect-scheme `assetcore://oauth/callback` + token Keychain/Keystore + policy 401→refresh→re-auth + revoke logout (§4 → `03`).
- [ ] Đăng ký redirect-scheme native (Android intent-filter / iOS URL Type) khớp `default_redirect_uri` OAuth Client (Phase B).
- [ ] Build APK debug trỏ BE dev → smoke-test login + quét QR + 1 luồng nghiệp vụ (§5.1).
- [ ] Thiết lập CI: lint + gen-client-from-yaml + **drift gate** + build (§5.2).
- [ ] (Chờ Phase B) Nhận public HTTPS host + `client_id` OAuth Client từ USER → cấu hình prod ENV.
- [ ] (Chờ Phase C) Khi yaml bồi 6 path nghiệp vụ → regenerate client (§2.4).

---

## 7. Out of scope (đẩy backlog — KHÔNG ôm việc dư)

- **Deploy/ops go-live runbook** (provision public HTTPS host, nginx rate-limit, `allow_cors`, OAuth Client, store release) — KHÔNG viết ở chương này (chồng lấn `02-deploy-feasibility.md` + `03-auth-oauth2.md §4` checklist Phase B + `08-security-compliance.md §4` go-live). Nếu cần là 1 vòng Phase A khác HOẶC Phase B (HARD-STOP USER).
- **Tạo repo native THẬT + impl 6 luồng** — Phase D, NGOÀI repo `assetcore`.
- **Sửa OpenAPI yaml path/operationId** — đã chốt; bồi schema thuộc Phase C/E.
- **Push/offline impl** — `06-push-fcm.md` / `07-offline-sync.md` (đặc tả) → impl Phase E.

---

## Tham chiếu chéo

- Tổng quan + 3 quyết định + glossary: [`00-overview.md`](./00-overview.md)
- Chỉ mục docset + lộ trình đọc: [`README.md`](./README.md)
- Kiến trúc (topology/3 lằn ranh/versioning/OpenAPI=hợp đồng): [`01-architecture.md`](./01-architecture.md)
- Auth deep-dive (PKCE/refresh/revoke/storage/policy 401): [`03-auth-oauth2.md`](./03-auth-oauth2.md)
- Hợp đồng API (envelope/ErrorCode/pagination/quirk HTTP-200): [`04-api-contract.md`](./04-api-contract.md)
- ADR kiến trúc (OpenAPI=hợp đồng): [`ADR-MOBILE-001.md`](./ADR-MOBILE-001.md)
- Hợp đồng máy đọc (nguồn sinh client): [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml)
- Feasibility (blocker triển khai Phase B): [`02-deploy-feasibility.md`](./02-deploy-feasibility.md)
