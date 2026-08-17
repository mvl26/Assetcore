# 00 — AssetCore Mobile BE: Tổng quan Initiative

| Mục | Giá trị |
|---|---|
| Initiative | **AssetCore Mobile** — backend-for-mobile (BE-only trong repo này) + APK native (repo riêng) |
| Khối kiến trúc | Cross-cutting (mở rộng truy cập IMM-00/08/09/11/12 cho field-tech) |
| Phase hiện tại | **PHASE A — Kiến trúc & Feasibility** — 🟢 hoàn tất (exit-ready, xem [`11-phase-a-exit.md`](./11-phase-a-exit.md)) |
| Owner | BA Lead + System Architect (mobile) · APK do repo native (ngoài) |
| Trạng thái docs | Phase A exit-ready (chờ USER mở Phase B) |
| Cập nhật | 2026-06-09 |

> Single Source of Truth kiến trúc cho initiative mobile. **AssetCore = backend (BE) + hợp đồng API**; UI native nằm ở **repo riêng**, chỉ GỌI API. Tài liệu này KHÔNG impl — chỉ chốt quyết định + roadmap + thuật ngữ.
> Mọi claim kỹ thuật trong docset đã verify tại source **Frappe v15.107.2** (xem `02-deploy-feasibility.md` + `ADR-MOBILE-001.md` với `file:line`).

---

## 1. Mục tiêu initiative

Mở khả năng cho **kỹ thuật viên hiện trường (field technician)** thao tác vòng đời thiết bị y tế ngay tại máy bằng **ứng dụng di động native** (Android APK trước; iOS sau), thay vì phải về bàn làm việc dùng web SPA.

Nguyên tắc cốt lõi:

- **Tách repo:** UI native ở repo riêng (Flutter / React Native — chốt D-STACK). Repo `assetcore` này CHỈ cung cấp **backend + hợp đồng API** (`OpenAPI = HỢP ĐỒNG`).
- **APK gọi API:** app native không nhúng business logic; mọi nghiệp vụ vẫn chạy ở Frappe BE (service layer 3-tier hiện có). App = UI + gọi REST/RPC + cache offline.
- **Tái dùng, không viết lại:** OAuth2 dùng provider có sẵn của Frappe (KHÔNG tự viết OAuth); RBAC capability (`services/shared/rbac.py`) là **1 SSoT** (KHÔNG dựng hệ quyền thứ 2); endpoint nghiệp vụ tái dùng nguyên, lớp mobile chỉ **BỌC** (wrap).
- **An toàn-trước:** bearer-over-HTTPS, PKCE cho native (không client_secret nhúng app), refresh + revoke token; offline/push chỉ ở mức kiến trúc trong Phase A.

Phạm vi MVP (D-MVP): field-tech — đăng nhập, quét QR → hồ sơ thiết bị, báo hỏng, yêu cầu PM/CM/Hiệu chuẩn, "phiếu của tôi". (Chi tiết mapping endpoint: `02-deploy-feasibility.md §6`.)

---

## 2. Ba quyết định đã CHỐT (in nguyên — USER 2026-06-09)

> 3 quyết định nền tảng đã được USER chốt; KHÔNG re-litigate trong Phase A. Mọi thiết kế phải BÁM theo.

### D-AUTH — OAuth2 + refresh

> **Xác thực mobile dùng OAuth2 (Authorization Code + PKCE) với access-token ngắn hạn + refresh token + revoke.** WIRE provider OAuth2 có sẵn của Frappe — KHÔNG tự viết OAuth. Bearer token → `set_user` → RBAC capability hiện hữu áp dụng nguyên vẹn (1 SSoT, không hệ quyền thứ 2). Session-cookie web KHÔNG tái dùng cho native.
>
> → Đặc tả end-to-end (sequence a→f · vòng đời token · scope↔capability · checklist OAuth Client): [`03-auth-oauth2.md`](./03-auth-oauth2.md).

### D-MVP — Field-technician MVP

> **MVP nhắm kỹ thuật viên hiện trường (field-tech).** 6 luồng cốt lõi: (1) đăng nhập OAuth2; (2) quét QR → hồ sơ thiết bị; (3) báo hỏng; (4) yêu cầu PM/CM/Hiệu chuẩn; (5) "phiếu của tôi" (list+detail); (6) thông báo đẩy (push — kiến trúc Phase A, impl sau). Tái dùng endpoint nghiệp vụ đã có, permission-aware. KHÔNG mở rộng sang persona quản lý/giám đốc ở MVP.

### D-STACK — Native

> **App là native (Flutter hoặc React Native), KHÔNG WebView/PWA-wrapper.** Repo UI tách riêng. Native HTTP-client (Dio/http/OkHttp) gọi thẳng API — không chịu CORS browser; PKCE bắt buộc (S256) vì không nhúng được client_secret an toàn trong APK. Cache/offline-first ở app layer.

---

## 3. Roadmap 6 PHASE (A–F)

| Phase | Tên | Mục tiêu | Trạng thái |
|---|---|---|---|
| **A** | Kiến trúc & Feasibility | ADR kiến trúc (topology, OAuth2, versioning, OpenAPI strategy, push/offline/security ở MỨC kiến trúc) + OpenAPI **skeleton** + feasibility verified tại source. Deliverable: `00`·`01`·`02`·`03`(A2)·`04`(A3)·`05`(A4)·`06`+ADR-002(A5)·`07`+ADR-003(A6)·`08`+ADR-004(A7)·`09`(A8 — handoff repo native) + `README` (index/cross-link hub, A8)·**`10`(A9 — runbook go-live) + `11`(A11 — EXIT GATE: traceability 6 flow + Phase-B prereqs + go/no-go)**. | 🟢 Hoàn tất (exit-ready — `11-phase-a-exit.md`) |
| **B** | Provisioning & Auth wiring | Tạo OAuth Client (Auth Code + PKCE + redirect native-scheme + allowed_roles); set `allow_cors`; public HTTPS host (reverse-proxy + TLS); set `assetcore_qr_base_url`. HARD-STOP thuộc USER (site_config/migrate/reload). | ⬜ Chưa |
| **C** | API contract bồi đắp | Bồi `openapi/assetcore-mobile.openapi.yaml` từng endpoint MVP (request/response schema thật từ type-hints+docstring); chốt namespace `api/mobile/v1` nếu cần lớp BỌC; ErrorCode envelope. | ⬜ Chưa |
| **D** | Repo native MVP | App native (repo riêng) impl 6 luồng D-MVP gọi API contract Phase C; sinh API client từ OpenAPI. (Ngoài repo `assetcore`.) | ⬜ Chưa |
| **E** | Push / Offline / Sync | Channel #3 push (FCM) chèn tại `_dispatch`; device-token registry; offline cache + sync policy (conflict, idempotency). **Cơ chế push + DocType device-token + MAP 6-event ĐÃ đặc tả ở `06-push-fcm.md` + `ADR-MOBILE-002` (A5). Offline/sync (read-cache ETag · write-queue idempotency-key · conflict optimistic-lock `modified` · lifecycle hàng đợi · audit) ĐÃ đặc tả ở `07-offline-sync.md` + `ADR-MOBILE-003` (A6).** | ⬜ Chưa (spec sẵn) |
| **F** | Hardening & Go-live | Security review (token TTL, scope↔capability, rate-limit, audit NĐ98), UAT field-tech, store release, runbook vận hành. | ⬜ Chưa |

> **Ranh giới repo:** Phase A/B/C/E/F (BE + contract + deploy) thuộc repo `assetcore`. Phase D (UI native) thuộc **repo mobile riêng** — repo này chỉ giao OpenAPI + API client guide.

---

## 4. Chỉ mục docset (Phase A)

| File | Nội dung |
|---|---|
| [`README.md`](./README.md) | **Index/cross-link hub docset** — liệt kê 17 mục (12 chương 00–11 + ADR-001..004 + openapi/) · bảng map Phase A→F↔file · 3 quyết định chốt (trỏ §2) · điểm vào + lộ trình đọc cho người mới |
| [`00-overview.md`](./00-overview.md) | (file này) Mục tiêu · 3 quyết định chốt · roadmap 6 phase · chỉ mục · convention đặt tên · glossary |
| [`01-architecture.md`](./01-architecture.md) | Topology · 3 lằn ranh trách nhiệm · auth flow Auth-Code+PKCE+refresh · API versioning · OpenAPI-as-contract · điểm chèn push/offline/security (mức kiến trúc) |
| [`ADR-MOBILE-001.md`](./ADR-MOBILE-001.md) | ADR kiến trúc — 5 quyết định (wire-not-write OAuth · capability=1 SSoT · reuse-endpoint wrapper · OpenAPI hợp đồng · no session-cookie native) + evidence `file:line` |
| [`02-deploy-feasibility.md`](./02-deploy-feasibility.md) | Khảo sát deploy/OAuth2/CORS read-only tại source (gaps + blocker triển khai). *(Trước là `01_Deploy_OAuth_CORS_Feasibility.md` — đã renumber.)* |
| [`03-auth-oauth2.md`](./03-auth-oauth2.md) | **Auth deep-dive (A2):** sequence Authorization Code + PKCE S256 + refresh + revoke end-to-end (a→f, evidence `file:line`) · vòng đời token (TTL 3600s/refresh/revoke/storage) · scope↔capability 1 SSoT · checklist field OAuth Client (Phase B) |
| [`04-api-contract.md`](./04-api-contract.md) | **Hợp đồng API (A3):** success/error envelope shape THẬT (`utils/response.py`) · ErrorCode catalog 15 mã + HTTP map · quirk HTTP-200 wrapper · pagination contract · versioning/deprecation · param convention (`str=""`) |
| [`05-personas-mvp.md`](./05-personas-mvp.md) | **Persona & MVP field-tech (A4):** persona KTV hiện trường (mục tiêu/môi trường/mạng/quét QR) + ánh xạ persona↔Role Profile "Kỹ thuật viên" thật (`role_profile_catalog.py`) · hành trình end-to-end ≥5 bước (5 feature MVP) · bảng MÀN↔API grounded `file:line` · phân loại OFFLINE per-màn (yêu cầu Phase E) · map QUYỀN/cap per-màn bám SSoT `rbac.py` (corrective.read-only KHÔNG vào báo-hỏng) |
| [`06-push-fcm.md`](./06-push-fcm.md) | **Push FCM design (A5):** cơ chế push (FCM Admin SDK trực tiếp vs relay) + sơ đồ register→event→FCM→APK · DocType **AC Mobile Device Token** spec (field/naming/dedup/RBAC/lifecycle) · MAP 6-event→FCM (kênh #3 tại `_dispatch`, in-app/email GIỮ NGUYÊN) · payload + deep-link native · opt-in/out + bảo mật server-key `site_config` + threat + audit NĐ98 |
| [`ADR-MOBILE-002.md`](./ADR-MOBILE-002.md) | ADR cơ chế push (A5) — CHỐT **FCM Admin SDK trực tiếp** (credentials `site_config`), KHÔNG relay Frappe Cloud (`push_notification.py` chỉ proxy `notification_relay.api.*` ⇒ không air-gapped) + alternatives + consequences + evidence `file:line` |
| [`07-offline-sync.md`](./07-offline-sync.md) | **Offline & Sync strategy (A6):** 3 lằn ranh đọc/ghi/online-only (đồng bộ `05 §4`) · **read-cache** ETag + `If-Modified-Since` + cờ "cập nhật lúc…/ngoại tuyến" · **write-queue idempotency-key contract** (client-gen UUID/ULID qua header `Idempotency-Key`, BE dedupe + replay trả response gốc, áp 4 màn idempotent-write + asset-create) · **conflict policy** optimistic-lock qua Frappe `modified` → 409 `CONFLICT` (reuse) + server-wins · **lifecycle hàng đợi** queued→sent→acked/conflict/failed · audit NĐ98 chỉ-khi-ghi-thật · bàn giao Phase E. Mọi cơ chế = HỢP ĐỒNG, impl Phase E. |
| [`ADR-MOBILE-003.md`](./ADR-MOBILE-003.md) | ADR chiến lược offline/sync (A6) — CHỐT (a) idempotency-key client-gen + BE-dedupe; (b) conflict = optimistic-lock qua `modified` + server-wins; (c) read-cache = ETag/`If-Modified-Since`; (d) KHÔNG offline-write-audit cho tới khi sync thật + alternatives + consequences + evidence `file:line`. Link-backward ADR-001. |
| [`08-security-compliance.md`](./08-security-compliance.md) | **Bảo mật & Tuân thủ (A7) — SSoT bảo mật mobile:** threat model bề mặt mobile ≥7 mối (T1 brute-force oauth2 no-rate-limit · T2 IDOR-qua-bearer · T3 CORS credential-echo · T4 token leak/storage · T5 scope leo quyền · T6 replay/duplicate-write · T7 MITM/cert-pinning) mỗi dòng evidence `file:line` · **NĐ98 audit-from-mobile** (bearer→`set_user`→hash-chain `lifecycle.py`, actor=KTV thật, KHÔNG thêm field/đường audit) · **phân loại mitigation 3 nhóm** (đã-có / config-HARD-STOP-USER / repo-native) · checklist security go-live · KPI/acceptance. Hợp nhất ghi chú rải rác (`06 §5.3` + ADR-001). |
| [`ADR-MOBILE-004.md`](./ADR-MOBILE-004.md) | ADR mô hình bảo mật mobile (A7) — CHỐT (a) rate-limit oauth2 ở tầng nginx KHÔNG sửa frappe core; (b) 1 SSoT quyền — KHÔNG hệ quyền thứ 2 (bearer→set_user→DocPerm gate cuối); (c) CORS list-origin CẤM wildcard prod; (d) audit NĐ98 = chuỗi hiện hữu KHÔNG thêm field + Context/Decision/Alternatives/Consequences + evidence `file:line`. Link-backward ADR-001. |
| [`09-native-repo-guide.md`](./09-native-repo-guide.md) | **Handoff repo native (A8):** hướng dẫn khởi tạo repo mobile native TỪ hợp đồng OpenAPI — §0 context/ranh giới repo · §1 skeleton (Flutter/RN + trade-off chọn D-STACK) · §2 sinh API client từ yaml (generator mẫu Dart/dio + TS, chống drift) · §3 ENV trỏ BE (BASE_URL dev/prod, KHÔNG hardcode) · §4 wire OAuth2 (LINK sang 03 §2.4/§2.5) · §5 build APK + CI · §6 cross-link 2 chiều + checklist khởi tạo. KHÔNG impl code repo này (Phase D ngoài). |
| [`10-deploy-ops.md`](./10-deploy-ops.md) | **Runbook go-live mobile-BE (A9 — quy trình THỰC THI, khác `02` feasibility):** §0 scope+phân biệt-với-02 (survey vs execute) · §1 bật OAuth2 (OAuth Client native, least-priv — link `03 §4` KHÔNG nhân đôi) · §2 CORS `allow_cors` LIST-origin (cấm wildcard prod, ADR-004, `app.py:269/275/283-284`) · §3 public host/reverse-proxy + QR deep-link host (`assetcore_qr_base_url`) · §4 FCM creds `site_config` (link `06`+ADR-002, bảo mật key) · §5 versioning header `Sunset`/`Deprecation` cho `/api/mobile/v1` + quy trình deprecate (gap thật) · §6 checklist go-live (pre-flight/execute/post-verify smoke curl) · §7 rollback · §8 cross-link. Mỗi bước HARD-STOP USER. |
| [`11-phase-a-exit.md`](./11-phase-a-exit.md) | **Phase-A EXIT GATE (A11 — đóng Phase A):** §0 mục tiêu/out-of-scope + lý do cấp số 11 · §1 **traceability matrix 6 flow MVP** (login OAuth2 · quét QR→hồ sơ · báo hỏng · yêu cầu PM/CM/Hiệu chuẩn · phiếu của tôi · push) × 7 cột [màn `05 §` · endpoint `file:line` @source · capability `rbac.py` · operationId OpenAPI · offline-class · push-event `06` · STUB-status] — 9 nghiệp vụ + 3 auth verify @source, 15/15 operationId khớp yaml · §2 **Phase-B prereqs/blocker hợp nhất** (B-1..B-8, trỏ ngược 02/03 §4/08 §4/10, chủ thể=USER) · §3 **checklist go/no-go A→B** đo được (12 đã-đạt Phase A vs 9 chờ-USER Phase B) · §4 KPI/acceptance exit. doc-only. |
| [`12-phase-b-preflight.md`](./12-phase-b-preflight.md) | **Phase-B pre-flight verifier (B0-PREFLIGHT — Phase A→B bridge):** §0 mục tiêu/out-of-scope + lý do cấp số 12 + admin-only ngoài hợp đồng app · §1 lệnh `bench execute …verify_oauth_client` + diễn giải 7 check · §2 map 7 check ↔ B-1 field `03 §4` ↔ runbook `10 §1` · §3 đọc report `ready`/`blockers` + khắc phục · §4 acceptance. Verifier READ-ONLY `assetcore/api/mobile/preflight.py` (gate System Manager, chịu count==0, KHÔNG raise) — biến checklist OAuth Client thành hợp đồng CHẠY ĐƯỢC. doc-only + verifier read-only. |
| [`13-be-completion-roadmap.md`](./13-be-completion-roadmap.md) | **MASTER roadmap BE-completion** — hoàn thiện lớp Backend-for-Mobile để repo native gọi API chạy app. DoD TỔNG = MVP field-tech 6-flow E2E trên cloud. 5 EPIC khoá-ID (C API-contract codegen-ready · B Auth & Provisioning · D Push FCM · G Go-live & Hardening · V Codegen Verify + Handoff). Mỗi TASK tag `[AUTO]` vs `[HARD-STOP USER]`. doc-only. |
| [`14-e2e-field-tech-runbook.md`](./14-e2e-field-tech-runbook.md) | **E2E field-tech runbook CHẠY-ĐƯỢC (EPIC-V V3):** hợp nhất `11 §1` matrix + `10 §6.3` smoke + `09 §6.2` checklist thành 1 sequence 6 flow tuần tự (login OAuth2+refresh → quét QR → báo hỏng → WO PM/CM/Cal → "phiếu của tôi" → push FCM). Mỗi bước: operationId trục + curl/dart kiểm-được THẬT + expected envelope (`success`+`code`+`http_status` route-by-VALUE) + tiền-điều-kiện + tag `[AUTO]`/`[HARD-STOP USER]`. §2 hợp đồng đọc-envelope (HTTP-200 quirk + Decision-B closed-schema + refresh-on-401). doc-only. |
| [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml) | OpenAPI (3.0.3) — info/servers/securitySchemes OAuth2; **3 path auth bồi** (A2); **Envelope/Error/Pagination/PaginatedListEnvelope + responses chuẩn 401/404/409/422/429** (A3); 6 path nghiệp vụ STUB (Phase C); **2 path device-token STUB** register/unregister (A5 — shape/security/operationId); **COMPONENTS offline dùng-lại** (A6 — parameters `Idempotency-Key`/`If-Match`/`If-None-Match`/`If-Modified-Since` + headers `ETag`/`Last-Modified` + response `NotModified304` + reuse `Conflict409`; KHÔNG bồi path nghiệp vụ — Phase C/E wire) |

---

## 5. Vị trí trong AssetCore (KHÔNG đụng web cũ)

- Initiative mobile là **lớp truy cập mới**, KHÔNG thay thế FE web SPA hiện có (Vue 3). Web cookie+CSRF GIỮ NGUYÊN cho người dùng bàn làm việc.
- Mobile BE **tái dùng** endpoint nghiệp vụ đang phục vụ web (imm00 QR/asset, imm12 báo hỏng, imm08/09/11 WO) — KHÔNG sửa code nghiệp vụ ở Phase A.
- Audit trail (NĐ98 — SHA-256 lifecycle chain `utils/lifecycle.py`) áp dụng tự nhiên: bearer→`set_user`→mọi action vẫn sinh record với đúng actor. Mobile KHÔNG phá audit.

---

## 6. Convention đặt tên docset mobile (giải quyết naming collision)

> Lý do: file scout ban đầu là `01_Deploy_OAuth_CORS_Feasibility.md` (underscore + số 01) sẽ TRÙNG số `01` với `01-architecture.md`. Chốt convention dưới đây + đã renumber file scout thành `02-deploy-feasibility.md`.

- **Format:** `NN-name-kebab.md` — `NN` = số thứ tự 2 chữ số theo roadmap/round goal, `name-kebab` = mô tả ngắn dạng kebab-case (chữ thường, gạch nối).
- **ADR:** `ADR-MOBILE-<NNN>.md` (3 chữ số tuần tự, không gắn vào dãy `NN-`).
- **OpenAPI:** đặt trong thư mục con `openapi/`, tên `assetcore-mobile.openapi.yaml`.
- **`operationId` (A10):** 15/15 path CÓ `operationId` ổn định (codegen-able) theo convention camelCase verbNoun = tail-của-dotted-path; verb-first cho oauth. SSoT quy tắc + bảng 15 dòng = `04-api-contract.md §8.1`. 2 device-token GIỮ NGUYÊN TÊN (chốt A5). Guard: `assetcore/tests/guards/test_mobile_oas.py`.
- **endpoint↔capability (A14):** ma trận endpoint MVP → capability (`11-phase-a-exit.md §1`) được GUARD máy-đọc bởi `assetcore/tests/integration/test_mobile_capability_map.py` (`TC-MOB-CAP-01..06`) — introspect `CAPABILITY_MAP` SSoT (`rbac.py`): binding `(DocType, ptype)` khớp matrix · 0 cap mới vì mobile (`len==97`) · version đóng băng `v97.c30c69b8974d`. KHÔNG dựng "hệ quyền thứ 2" (`ADR-MOBILE-001 b`). KHÔNG cấp số chương mới (test + note, không phải chương).
- **docset-integrity (A15):** toàn vẹn tầng NAVIGATION của chính docset (index↔filesystem parity 14 chương `NN-*.md` + 4 ADR + openapi · 0 broken local link · 0 placeholder · mỗi chương ≥1 H1) được GUARD máy-đọc bởi `assetcore/tests/guards/test_mobile_docset.py` (`TC-MOB-DOC-01..05`) — đếm động bằng glob (KHÔNG hardcode 14/19). Read-only `.md`/dir-listing; KHÔNG đụng yaml/code/cap/generator. Đóng kín gate Phase A chống regress khi Phase B/C/D edit. Khi thêm chương mới (vd `13-be-completion-roadmap.md`) PHẢI đồng-bộ dòng index README §1 (parity glob), nếu không TC-MOB-DOC-01 ĐỎ.
- **auth-token RESPONSE contract (B1 — Phase B land):** hợp đồng RESPONSE của 2 token-endpoint (`get_token`/`revoke_token`) đóng băng = **PASSTHROUGH OAuthlib** (Frappe core SSoT — KHÔNG AssetCore envelope). SOURCE-CHARACTERIZED @file:line: get_token 200-keys `{access_token,expires_in,token_type,scope?,refresh_token?}` (tokens.py:309-326), 400-body `OAuthError400` `{error,…}` (oauth2.py:132-135 / errors.py:80-88 / oauth.py:567-573), revoke 200 empty (oauth2.py:158-159). Component `OAuthError400` wire `'400'` CHỈ `getOAuthToken`. GUARD = `assetcore/tests/guards/test_mobile_oas.py` (`TC-MOB-OAUTH-TOKEN-01..05`). Quyết định + bảng error 2-lớp: `03 §2/§2.3.1` + `04 §5b`. **KHÔNG cấp số chương mới** (edit `03`/`04` + component yaml + test). Provisioning OAuth Client (B-1) vẫn HARD-STOP USER.
- **error-status contract fix (A16 — KHÁC A14 capability-map):** TÁCH status-class pre-handler **401** (Authorization header CÓ nhưng bearer hết-hạn/invalid — `AuthenticationError` `frappe/exceptions.py:26-27`, raise `auth.py:630`) vs **403** (guest/no-token HOẶC thiếu permission/cap — `PermissionError` `:34-35`, raise `is_whitelisted` `__init__.py:876`). Wire `'403'`→`Forbidden` lên **TẤT CẢ 12 path MVP** (10 business STUB + 2 device-token bearer-gated self-service `06 §2.3`) ⇒ 12-path-401 == 12-path-403 (đối xứng). +component `schemas/FrappeRawError` `{exc_type* · exception?/exc?/_server_messages? opt}` source-char @`frappe/utils/response.py` V1 (`:46`/`:43-45`/`:185`/`:188`) + repoint `Unauthorized401`/`Forbidden`/`RateLimited429` `$ref` từ `schemas/Error` → `schemas/FrappeRawError` (3 response pre-handler raw — KHÔNG Error envelope; codegen KHỚP body runtime). Error envelope CHỈ áp lỗi IN-HANDLER (HTTP-200 quirk `04 §5`). `Retry-After`/`X-RateLimit-*` = Phase-B-conditional (P2 DEFER — `conf.rate_limit=null` ⇒ 0 backoff-header). Decision passthrough (normalize raw→envelope = option DEFERRED Phase B): `ADR-MOBILE-001 (f)`. GUARD `assetcore/tests/guards/test_mobile_oas.py` (`TC-MOB-OAS-12`). Counter: defined 21→22 · `$ref` distinct 11→12 · orphan VẪN 10. **KHÔNG cấp số chương mới** (edit `04`/`ADR-MOBILE-001` + component yaml + test).
- **Số đã cấp:** `00`=overview · `01`=architecture · `02`=deploy-feasibility · `03`=auth-oauth2 (A2) · `04`=api-contract (A3) · `05`=personas-mvp (A4 — dùng `05` vì `04` đã cấp cho api-contract; tránh trùng số) · `06`=push-fcm (A5 — dùng `06` vì `05` đã cấp cho personas-mvp; tránh trùng số) · `07`=offline-sync (A6 — dùng `07` vì `06` đã cấp cho push-fcm; KHÔNG ghi đè `06`) · `08`=security-compliance (A7 — dùng `08` vì `07` đã cấp cho offline-sync) · `09`=native-repo-guide (A8 — handoff repo native) · `10`=deploy-ops (A9 — runbook go-live, khác `02` feasibility) · `11`=phase-a-exit (A11 — exit gate, dùng `11` vì số kế tiếp khả dụng; KHÔNG ghi đè `00-10`) · `12`=phase-b-preflight (B0-PREFLIGHT — Phase A→B bridge, verifier OAuth Client; dùng `12` vì số kế tiếp khả dụng, KHÔNG ghi đè `00-11`) · `13`=be-completion-roadmap (**MASTER roadmap BE-completion** — 5 EPIC C/B/D/G/V, cấu trúc USER duyệt 2026-06-11; dùng `13` vì số kế tiếp khả dụng, KHÔNG ghi đè `00-12`). **Số kế tiếp = `14-…`** cấp khi có doc mới (vd E2E field-tech runbook EPIC-V).
- **KHÔNG gắn số:** `README.md` = index/cross-link hub docset (A8) — đặt ngoài dãy `NN-` (vai trò mục lục, không phải chương nội dung).
- **ADR đã cấp:** `ADR-MOBILE-001` (kiến trúc nền) · `ADR-MOBILE-002` (cơ chế push FCM — A5) · `ADR-MOBILE-003` (chiến lược offline/sync — A6) · `ADR-MOBILE-004` (mô hình bảo mật mobile — A7).
- **KHÔNG xoá nội dung feasibility** — chỉ tránh đụng số (đã đổi `01_…` → `02-deploy-feasibility.md`, nội dung nguyên vẹn).

---

## 7. Glossary — thuật ngữ mobile / OAuth2

| Thuật ngữ | Định nghĩa (trong ngữ cảnh AssetCore Mobile) |
|---|---|
| **Bearer token** | Access token gửi trong header `Authorization: Bearer <token>`. Frappe verify rồi `set_user` (`auth.py:633/667`). Token CHÍNH là PK của doctype `OAuth Bearer Token`. |
| **Scope** | Phạm vi THÔ ở tầng oauthlib (vd `all openid`). Gate on/off ở cấp client; KHÔNG biết tới `CAPABILITY_MAP`. Quyền THỰC vẫn do RBAC capability/DocPerm theo user quyết định. |
| **Capability** | Đơn vị quyền AssetCore (`asset.read`, `corrective.create`…) trong `CAPABILITY_MAP`. `rbac.can(cap)` → `frappe.has_permission(DocType, ptype)` trên `frappe.session.user` (`rbac.py:156`). **1 SSoT quyền** — bearer→set_user nên áp dụng nguyên vẹn cho request mobile. |
| **PKCE** | Proof Key for Code Exchange (RFC 7636). Client sinh `code_verifier` → `code_challenge` (S256). Cho phép native app dùng Authorization Code mà KHÔNG cần client_secret nhúng APK. Frappe verify ở `oauth.py:146-160`. |
| **Refresh token** | Token dài hạn để đổi lấy access-token mới khi access hết hạn (default 3600s/1h), KHÔNG bắt user login lại. `grant_type=refresh_token` (`oauth.py:187`). |
| **Authorization Code** | Luồng OAuth2 chuẩn cho UI có người dùng: app mở `/authorize` → user login → BE trả `code` về redirect_uri → app đổi `code` (+ `code_verifier`) lấy token tại `/get_token`. |
| **Revoke** | Thu hồi token (RFC 7009) qua `revoke_token` (`oauth2.py:144`) — đăng xuất an toàn / mất máy. |
| **OAuth Client** | Record cấu hình app trong Frappe (app_name, client_id/secret, redirect_uris, grant_type, allowed_roles). **Hiện = 0** → Phase B phải tạo. |
| **OpenAPI = hợp đồng** | File YAML viết tay là HỢP ĐỒNG giữa BE và repo native: định nghĩa endpoint/param/response để sinh API client + tránh drift. Frappe KHÔNG auto-gen cho `/api/method`. |
| **`/api/method/<dotted>`** | Đường gọi RPC tới whitelisted method (vd `assetcore.api.imm12.report_incident`) — đường FE web đang dùng; mobile tái dùng. |

---

## Tham chiếu chéo

- Kiến trúc chi tiết: [`01-architecture.md`](./01-architecture.md)
- ADR + evidence: [`ADR-MOBILE-001.md`](./ADR-MOBILE-001.md)
- Feasibility (gaps/blocker): [`02-deploy-feasibility.md`](./02-deploy-feasibility.md)
- Auth deep-dive (sequence/TTL/scope↔cap/OAuth Client): [`03-auth-oauth2.md`](./03-auth-oauth2.md)
- Push FCM design + DocType device-token + MAP 6-event: [`06-push-fcm.md`](./06-push-fcm.md) · ADR cơ chế push: [`ADR-MOBILE-002.md`](./ADR-MOBILE-002.md)
- Offline & Sync strategy (read-cache · idempotency · conflict · lifecycle hàng đợi): [`07-offline-sync.md`](./07-offline-sync.md) · ADR chiến lược offline/sync: [`ADR-MOBILE-003.md`](./ADR-MOBILE-003.md)
- Bảo mật & Tuân thủ (threat model T1–T7 · NĐ98 audit-from-mobile · 3 nhóm mitigation): [`08-security-compliance.md`](./08-security-compliance.md) · ADR mô hình bảo mật: [`ADR-MOBILE-004.md`](./ADR-MOBILE-004.md)
- OpenAPI (auth-section bồi): [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml)
- RBAC SSoT: `assetcore/services/shared/rbac.py`
- QR/asset endpoint: `assetcore/api/imm00.py` · Báo hỏng: `assetcore/api/imm12.py`
- Push engine (channel #3 insert point): `assetcore/services/notifications.py::_dispatch`
