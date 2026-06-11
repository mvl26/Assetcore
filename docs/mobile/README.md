# AssetCore Mobile — Docset (backend-for-mobile + repo native handoff)

| Mục | Giá trị |
|---|---|
| Initiative | **AssetCore Mobile** — backend (BE) + hợp đồng API trong repo này · APK native ở **repo riêng** |
| Phase hiện tại | **PHASE A — Kiến trúc & Feasibility** — 🟢 hoàn tất (exit-ready) |
| Owner | BA Lead + System Architect (mobile) |
| Trạng thái | Phase A exit-ready (chờ USER mở Phase B — xem [`11-phase-a-exit.md`](./11-phase-a-exit.md)) |
| Cập nhật | 2026-06-09 |

> **Đây là index/cross-link hub của docset mobile.** AssetCore = **backend + hợp đồng API**; UI native nằm ở **repo riêng**, chỉ GỌI API. Docset này chốt **quyết định + roadmap + hợp đồng** (KHÔNG impl code).
> Mọi claim kỹ thuật trong docset đã verify tại source **Frappe v15.107.2** với evidence `file:line` (xem `02-deploy-feasibility.md` + các ADR). Tổng quan đầy đủ: [`00-overview.md`](./00-overview.md).

---

## 1. Chỉ mục đầy đủ (19 mục: 14 chương 00–13 + ADR-001..004 + openapi/)

### Chương đánh số (00–13)

| File | Mô tả 1 dòng |
|---|---|
| [`00-overview.md`](./00-overview.md) | Tổng quan initiative — mục tiêu · **3 quyết định chốt** (§2) · roadmap 6 phase · chỉ mục · convention đặt tên · glossary OAuth2. |
| [`01-architecture.md`](./01-architecture.md) | Kiến trúc Phase A — topology · 3 lằn ranh trách nhiệm · auth-flow PKCE+refresh (mức kiến trúc) · API versioning · OpenAPI-as-contract · điểm chèn push/offline/security. |
| [`02-deploy-feasibility.md`](./02-deploy-feasibility.md) | Khảo sát deploy/OAuth2/CORS read-only tại source — gaps + blocker triển khai Phase B (public host, allow_cors, OAuth Client=0). |
| [`03-auth-oauth2.md`](./03-auth-oauth2.md) | Auth deep-dive (A2) — sequence Authorization Code + PKCE S256 + refresh + revoke (a→f) · vòng đời token (TTL 3600s/refresh/revoke/storage Keychain) · scope↔capability 1 SSoT · checklist OAuth Client. |
| [`04-api-contract.md`](./04-api-contract.md) | Hợp đồng API (A3) — success/error envelope shape THẬT · ErrorCode 15 mã + HTTP map · quirk HTTP-200 wrapper · pagination contract · versioning/deprecation · param convention `str=""` · **§8.1 convention `operationId` (A10)** — luật camelCase verbNoun + bảng 15/15 codegen-able · **§8.2 contract-integrity & codegen-validity (A12/A13)** — 0 dangling `$ref` + bảng RESERVED 10 orphan-component allow-list + **A13 error-response coverage** (401 lên 12 path MVP · 429 lên 2 path `@rate_limit`) (guard `TC-MOB-OAS-09/10/11`). |
| [`05-personas-mvp.md`](./05-personas-mvp.md) | Persona & MVP field-tech (A4) — persona KTV hiện trường · hành trình end-to-end 5 feature · bảng MÀN↔API grounded · phân loại offline per-màn · map quyền/cap per-màn bám SSoT rbac.py. |
| [`06-push-fcm.md`](./06-push-fcm.md) | Push FCM design (A5) — cơ chế push (FCM Admin SDK trực tiếp) · DocType **AC Mobile Device Token** spec · MAP 6-event→FCM (kênh #3 tại `_dispatch`) · payload + deep-link + opt-in/out + bảo mật + audit. |
| [`07-offline-sync.md`](./07-offline-sync.md) | Offline & Sync strategy (A6) — read-cache ETag/If-Modified-Since · write-queue idempotency-key contract · conflict optimistic-lock qua `modified` → 409 · lifecycle hàng đợi · audit chỉ-khi-ghi-thật. |
| [`08-security-compliance.md`](./08-security-compliance.md) | Bảo mật & Tuân thủ (A7) — threat model 7 mối (T1–T7) mỗi dòng evidence · NĐ98 audit-from-mobile · phân loại mitigation 3 nhóm · checklist go-live · KPI. |
| [`09-native-repo-guide.md`](./09-native-repo-guide.md) | **Handoff repo native (A8)** — skeleton repo (Flutter/RN) · sinh API client từ OpenAPI · ENV trỏ BE · wire OAuth2 (link sang 03) · build APK + CI · checklist khởi tạo repo. |
| [`10-deploy-ops.md`](./10-deploy-ops.md) | **Runbook go-live mobile-BE (A9)** — quy trình THỰC THI CÓ THỨ TỰ (khác 02 feasibility): §1 bật OAuth2 · §2 CORS list-origin · §3 public host+QR deep-link · §4 FCM creds · §5 versioning `Sunset`/`Deprecation` · §6 checklist go-live (pre-flight/execute/smoke curl) · §7 rollback. Mỗi bước HARD-STOP USER. |
| [`11-phase-a-exit.md`](./11-phase-a-exit.md) | **Phase-A EXIT GATE (A11 — đóng Phase A)** — §1 traceability matrix 6 flow MVP × 7 cột (màn · endpoint `file:line` @source · capability · operationId · offline-class · push-event · STUB-status; 9 nghiệp vụ + 3 auth verify @source, 15/15 operationId) · §2 Phase-B prereqs/blocker hợp nhất (B-1..B-8, trỏ ngược 02/03 §4/08 §4/10, chủ thể=USER) · §3 checklist go/no-go A→B đo được (13 đã-đạt vs 9 chờ-USER) · §4 KPI/acceptance exit. doc-only. **A14: matrix §1 (endpoint↔capability) nay GUARDED máy-đọc bởi `assetcore/tests/test_mobile_capability_map.py` (`TC-MOB-CAP-01..06`) — binding `(DocType, ptype)` ↔ SSoT `rbac.py` + anti-cap-creep `v97.c30c69b8974d`.** |
| [`12-phase-b-preflight.md`](./12-phase-b-preflight.md) | **Phase-B pre-flight verifier (B0-PREFLIGHT — Phase A→B bridge)** — biến checklist OAuth Client (`03 §4` / blocker B-1) thành hợp đồng CHẠY ĐƯỢC: §0 mục tiêu/out-of-scope + admin-only ngoài hợp đồng app · §1 lệnh `bench execute …verify_oauth_client` + diễn giải 7 check · §2 map 7 check ↔ B-1 field `03 §4` ↔ runbook `10 §1` · §3 đọc report `ready`/`blockers` + khắc phục · §4 acceptance. Verifier READ-ONLY (`assetcore/api/mobile/preflight.py`), gate System Manager, chịu count==0 (KHÔNG raise). doc-only + verifier read-only. |
| [`13-be-completion-roadmap.md`](./13-be-completion-roadmap.md) | **MASTER roadmap BE-completion** (cấu trúc USER duyệt 2026-06-11) — hoàn thiện lớp Backend-for-Mobile để repo native gọi API chạy app. DoD TỔNG = MVP field-tech 6-flow E2E trên cloud. **5 EPIC khoá-ID:** C (API Contract codegen-ready: 4 STUB typed + list-element + userinfo + P1 in-handler-error-on-HTTP-200) · B (Auth & Provisioning: refresh ✅ + TTL 3600s + preflight gate + device-token) · D (Push FCM: kênh #3 `_dispatch` + FCM HTTP v1 + DocType) · G (Go-live & Hardening: 5 knob site_config matrix + traceback/CORS/rate-limit) · V (Codegen Verify + Handoff: gen Dart/Kotlin + E2E runbook + gói handoff). Thứ tự C→B∥D-design→G→D→V; mỗi TASK tag `[AUTO]` vs `[HARD-STOP USER]`. doc-only. |

### ADR (Architecture Decision Records)

| File | Mô tả 1 dòng |
|---|---|
| [`ADR-MOBILE-001.md`](./ADR-MOBILE-001.md) | ADR kiến trúc nền — 5 quyết định: (a) wire-not-write OAuth · (b) capability=1 SSoT · (c) reuse-endpoint wrapper · (d) OpenAPI=hợp đồng · (e) no session-cookie native + evidence `file:line`. **Accepted.** |
| [`ADR-MOBILE-002.md`](./ADR-MOBILE-002.md) | ADR cơ chế push (A5) — CHỐT **FCM Admin SDK trực tiếp** (credentials site_config), KHÔNG relay Frappe Cloud + alternatives + consequences + evidence. **Accepted.** |
| [`ADR-MOBILE-003.md`](./ADR-MOBILE-003.md) | ADR offline/sync (A6) — CHỐT idempotency-key client-gen + BE-dedupe · conflict optimistic-lock + server-wins · read-cache ETag · no offline-write-audit tới khi sync thật. **Accepted.** |
| [`ADR-MOBILE-004.md`](./ADR-MOBILE-004.md) | ADR mô hình bảo mật (A7) — CHỐT rate-limit oauth2 ở nginx (no core) · 1 SSoT quyền · CORS list-origin (cấm wildcard prod) · audit NĐ98 chuỗi hiện hữu. **Accepted.** |

### Hợp đồng máy đọc

| File | Mô tả 1 dòng |
|---|---|
| [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml) | OpenAPI 3.0.3 (`AssetCore Mobile API`, `0.1.0-skeleton`) — securityScheme OAuth2 · 3 path auth bồi · Envelope/Error/Pagination + responses chuẩn · 6 path nghiệp vụ STUB · 2 path device-token STUB · COMPONENTS offline dùng-lại · **`operationId` đầy đủ 15/15 (codegen-able, A10)** — convention `04-api-contract.md §8.1`. Nguồn sinh API client (repo native). |

> **A15 — Docset-integrity GUARDED (chống regress tầng navigation).** Toàn vẹn chính bộ docset này (index ↔ filesystem parity · link-health · ADR registration · no-placeholder) nay được kiểm chứng tự động bởi `assetcore/tests/test_mobile_docset.py` (`TC-MOB-DOC-01..05`): (1) mọi chương đánh số `NN-*.md` trên đĩa ↔ đúng 1 dòng index §1 (đếm động bằng glob, 0 chương mồ côi / 0 mục index treo); (2) mọi `ADR-MOBILE-*.md` + `openapi/assetcore-mobile.openapi.yaml` được README liệt kê/tham chiếu; (3) mọi link nội bộ tương đối (`./`,`../`) trong `docs/mobile/*.md` resolve về file tồn tại (baseline 405 link / 0 broken); (4) 0 placeholder (`TODO/TBD/FIXME/XXX/<...>/lorem`) NGOÀI code-fence + mỗi chương non-empty có ≥1 H1. Edit Phase B/C/D mà phá parity/link/placeholder ⇒ test ĐỎ. Đây là guard tầng **navigation**, song song guard tầng **contract** (`test_mobile_oas` = yaml · `test_mobile_capability_map` = rbac · `test_mobile_preflight` = oauth-client).

---

## 2. Bảng map Phase A→F ↔ file

> Roadmap 6 phase: [`00-overview.md §3`](./00-overview.md). Ranh giới repo: Phase A/B/C/E/F (BE + contract + deploy) thuộc repo `assetcore`; **Phase D** (UI native) thuộc **repo mobile riêng**.

| Phase | Tên | Trạng thái | File liên quan |
|---|---|---|---|
| **A** | Kiến trúc & Feasibility | 🟢 Hoàn tất (exit-ready) | `00`·`01`·`02`·`03` (A2)·`04` (A3)·`05` (A4)·`06`+ADR-002 (A5)·`07`+ADR-003 (A6)·`08`+ADR-004 (A7)·`09` (A8)·`10` (A9)·**`11` (A11 — EXIT GATE)**·ADR-001·`openapi/` |
| **B** | Provisioning & Auth wiring (HARD-STOP USER) | ⬜ Chưa | **`10-deploy-ops.md` (runbook go-live: numbered steps §1–§5 + checklist + smoke + rollback)** · `02-deploy-feasibility.md` (blocker/survey) · `03-auth-oauth2.md §4` (checklist OAuth Client) · `08 §4` (security go-live) |
| **C** | API contract bồi đắp | ⬜ Chưa | `04-api-contract.md §10` (việc Phase C) · `openapi/*.yaml` (bồi 6 path nghiệp vụ) |
| **D** | Repo native MVP (repo riêng, ngoài `assetcore`) | ⬜ Chưa | `09-native-repo-guide.md` (handoff) · `05-personas-mvp.md` (luồng MVP) · `openapi/*.yaml` (sinh client) |
| **E** | Push / Offline / Sync (impl) | ⬜ Chưa (spec sẵn) | `06-push-fcm.md`+ADR-002 · `07-offline-sync.md`+ADR-003 · `openapi/` (COMPONENTS offline) |
| **F** | Hardening & Go-live | ⬜ Chưa | `08-security-compliance.md` (security review · go-live) + ADR-004 · `03 §2.1` (token TTL backlog) |

---

## 3. Ba quyết định CHỐT (in nguyên ở [`00-overview.md §2`](./00-overview.md))

> 3 quyết định nền do USER chốt (2026-06-09); KHÔNG re-litigate. Mọi thiết kế phải BÁM theo. **Nguồn chân lý = [`00-overview.md §2`](./00-overview.md).**

| Mã | Quyết định | Đặc tả chi tiết |
|---|---|---|
| **D-AUTH** | OAuth2 (Authorization Code + PKCE) + access-token ngắn hạn + refresh + revoke. WIRE provider Frappe có sẵn — KHÔNG tự viết OAuth. Bearer→`set_user`→RBAC capability (1 SSoT). | [`03-auth-oauth2.md`](./03-auth-oauth2.md) · [`ADR-MOBILE-001.md`](./ADR-MOBILE-001.md) (a/b/e) |
| **D-MVP** | MVP nhắm **kỹ thuật viên hiện trường** (6 luồng: login · quét QR→hồ sơ · báo hỏng · yêu cầu PM/CM/Hiệu chuẩn · phiếu của tôi · push). Tái dùng endpoint nghiệp vụ. | [`05-personas-mvp.md`](./05-personas-mvp.md) |
| **D-STACK** | App **native** (Flutter HOẶC React Native), KHÔNG WebView/PWA. Repo UI tách riêng; HTTP-client native; PKCE bắt buộc. | [`01-architecture.md`](./01-architecture.md) · [`09-native-repo-guide.md`](./09-native-repo-guide.md) (skeleton + trade-off chọn stack) |

---

## 4. Điểm vào cho người mới — đọc theo thứ tự

1. **[`00-overview.md`](./00-overview.md)** — bắt đầu ở đây: mục tiêu · 3 quyết định chốt (§2) · roadmap · glossary OAuth2/PKCE/refresh.
2. **[`01-architecture.md`](./01-architecture.md)** — topology + 3 lằn ranh trách nhiệm (repo nào làm gì) + OpenAPI=hợp đồng.
3. **[`ADR-MOBILE-001.md`](./ADR-MOBILE-001.md)** — vì sao 5 quyết định kiến trúc (wire OAuth · 1 SSoT quyền · reuse · contract · no-cookie).
4. **[`03-auth-oauth2.md`](./03-auth-oauth2.md)** + **[`04-api-contract.md`](./04-api-contract.md)** — 2 hợp đồng cốt lõi: xác thực (PKCE/refresh/revoke) + envelope/error/pagination.
5. **[`05-personas-mvp.md`](./05-personas-mvp.md)** — persona field-tech + 6 luồng MVP + bảng MÀN↔API.
6. **[`06-push-fcm.md`](./06-push-fcm.md)** · **[`07-offline-sync.md`](./07-offline-sync.md)** · **[`08-security-compliance.md`](./08-security-compliance.md)** (+ ADR-002/003/004) — push · offline/sync · bảo mật (đặc tả Phase E/F).
7. **[`09-native-repo-guide.md`](./09-native-repo-guide.md)** — khi sẵn sàng dựng repo native (Phase D): skeleton · sinh client từ OpenAPI · ENV · OAuth wiring · build APK + CI · checklist khởi tạo.
8. **[`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml)** — hợp đồng máy đọc (nguồn sinh API client). Tra song song với `03`/`04`.
9. **[`11-phase-a-exit.md`](./11-phase-a-exit.md)** — **cổng thoát Phase A:** traceability matrix 6 flow MVP (xem nhanh toàn bộ chuỗi màn→endpoint→cap→opId→offline→push) + danh sách Phase-B prereqs hợp nhất + checklist go/no-go. Đọc khi cần "ảnh chụp" toàn cảnh + quyết định mở Phase B.

> **Lối tắt theo vai:**
> - **Quyết định mở Phase B / nắm toàn cảnh:** **`11-phase-a-exit.md`** (matrix 6 flow + prereqs + go/no-go) — 1 file thấy hết.
> - **Đội repo native (Phase D):** `00 §2` → `09` → `03` → `04` → `openapi/` → `05` (tra nhanh matrix `11 §1`).
> - **USER/Admin (Phase B go-live):** `11 §2/§3` (prereqs B-1..B-8 + checklist) → `10-deploy-ops.md` (runbook numbered steps + checklist + smoke) → `03 §4` (OAuth Client field) → `08 §4` (security checklist). `02-deploy-feasibility.md` = survey nền (đọc trước nếu cần hiểu gap).
> - **BE dev (Phase C/E):** `04 §10` (việc Phase C) → `06`/`07` (push/offline) → `openapi/` (tra STUB-status `11 §1`).

---

## Tham chiếu chéo (ngoài docset)

- **Guard docset (self-referential — kiểm chính bộ docset này):** `../../assetcore/tests/test_mobile_docset.py` (`TC-MOB-DOC-01..05`) — index↔filesystem parity + link-health + ADR registration + no-placeholder. Song song 3 guard contract: `../../assetcore/tests/test_mobile_oas.py` (yaml — `TC-MOB-OAS-*`) · `../../assetcore/tests/test_mobile_capability_map.py` (rbac — `TC-MOB-CAP-*`) · `../../assetcore/tests/test_mobile_preflight.py` (oauth client — `TC-MOB-PRE-*`).
- RBAC SSoT (capability): `../../assetcore/services/shared/rbac.py`
- Envelope/ErrorCode SSoT: `../../assetcore/utils/response.py`
- QR/asset endpoint: `../../assetcore/api/imm00.py` · Báo hỏng: `../../assetcore/api/imm12.py`
- Push engine (channel #3 insert point): `../../assetcore/services/notifications.py::_dispatch`
- Provider Frappe OAuth2: `../../../frappe/frappe/integrations/oauth2.py` · `../../../frappe/frappe/oauth.py` · `../../../frappe/frappe/auth.py`
