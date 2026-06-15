# 07 — Offline & Sync strategy · Read-cache · Write-queue idempotency · Conflict policy

| Mục | Giá trị |
|---|---|
| Initiative | AssetCore Mobile — backend-for-mobile |
| Phase | **A — Kiến trúc & Feasibility** (vòng 6 / PHASE A · A6 Offline/Sync strategy) |
| Bám quyết định | D-AUTH (OAuth2+refresh) · D-MVP (field-tech) · D-STACK (native) — `00-overview.md §2` · **ADR-MOBILE-003** (chiến lược offline/sync) |
| Owner | BA Lead + System Architect (mobile) |
| Trạng thái | In Progress (Phase A) |
| Cập nhật | 2026-06-09 |

> **Mục đích:** chốt **chiến lược offline & sync** ở mức HỢP ĐỒNG cho repo native + BE Phase E: (1) **read-cache** dùng HTTP conditional GET (`ETag` + `If-Modified-Since`) + cờ "cập nhật lúc…/ngoại tuyến"; (2) **write-queue** với **idempotency-key contract** (client sinh key, BE dedupe, replay trả response gốc); (3) **conflict policy** dùng optimistic-lock qua Frappe `modified` (If-Match/version) → `CONFLICT` (409), server-wins + báo người dùng; (4) **lifecycle hàng đợi offline** (queued→sent→acked/conflict/failed); (5) audit NĐ98 **chỉ sinh khi record ghi THẬT ở BE**.
> **Đây là ĐẶC TẢ (spec), KHÔNG impl.** Mọi cơ chế dưới đây là **HỢP ĐỒNG** đầu vào cho **Phase E** (impl). Phase A KHÔNG sửa code, KHÔNG thêm ErrorCode, KHÔNG thêm capability, KHÔNG đụng `notifications.py`/doctype/live api.
> **Verify:** mọi claim kỹ thuật có `file:line` đối chiếu source THẬT tại **Frappe v15.107.2** (site `miyano`, 2026-06-09). KHÔNG bịa field/endpoint/cap/mã.

> **Chỉ mục docset:** [`00-overview.md`](./00-overview.md) · [`01-architecture.md`](./01-architecture.md) · [`02-deploy-feasibility.md`](./02-deploy-feasibility.md) · [`03-auth-oauth2.md`](./03-auth-oauth2.md) · [`04-api-contract.md`](./04-api-contract.md) · [`05-personas-mvp.md`](./05-personas-mvp.md) · [`06-push-fcm.md`](./06-push-fcm.md) · [`ADR-MOBILE-001.md`](./ADR-MOBILE-001.md) · [`ADR-MOBILE-002.md`](./ADR-MOBILE-002.md) · [`ADR-MOBILE-003.md`](./ADR-MOBILE-003.md) · [`openapi/assetcore-mobile.openapi.yaml`](./openapi/assetcore-mobile.openapi.yaml)

> **Quyết định đặt số (convention `00-overview.md §6`):** doc này dùng số **`07`** vì `06` đã cấp cho `06-push-fcm.md` (A5). Theo convention chống-trùng-số `00-overview §6` ("Số kế tiếp cấp khi có doc mới"), `07` là số kế tiếp khả dụng. **KHÔNG** ghi đè `06-push-fcm.md`. Ghi rõ lý do tại đây theo yêu cầu acceptance.

---

## 0. Mục tiêu / Out-of-scope

### 0.1 Mục tiêu (Phase A — đặc tả)

Giải bài toán **mạng chập chờn tại hiện trường** (`05-personas-mvp §1.1`: Wi-Fi yếu/chết vùng tầng hầm CĐHA, phòng chì X-quang, 4G phập phù) bằng chiến lược offline-first **ở app layer** mà KHÔNG drift khỏi 1 SSoT quyền/audit của BE. Cụ thể, doc này CHỐT 4 hợp đồng để Phase E impl không lệch:

1. **Read-cache** an toàn cho dữ liệu chỉ-đọc (hồ sơ thiết bị, "phiếu của tôi") dùng HTTP conditional GET — tiết kiệm băng thông + chịu mất mạng tạm.
2. **Write-queue idempotency-key contract** cho 4 màn `idempotent-write-needed` (`05 §4`) + đường write asset-create — retry KHÔNG tạo bản ghi thứ 2.
3. **Conflict policy** dùng optimistic-lock primitive có sẵn của Frappe (`modified` timestamp) — xung đột → `CONFLICT` (409) + server-wins + báo người dùng (KHÔNG silent-overwrite).
4. **Lifecycle hàng đợi offline** rõ ràng (queued→sent→acked/conflict/failed) để repo native + BE đồng thuận về vòng đời 1 thao tác ghi-ngoại-tuyến.

### 0.2 Out-of-scope (Phase A — KHÔNG làm vòng này)

| Ngoài scope | Lý do / thuộc về |
|---|---|
| Impl sync engine / write-queue / cache-store trong app | Phase D/E (repo native + BE) |
| Impl idempotency dedupe store (key→first-response) ở BE | **Phase E** (DocType/cache + middleware) |
| Impl optimistic-lock wiring `If-Match`→`modified` ở api-tier | **Phase E** (lớp bọc `api/mobile/v1` HOẶC middleware) |
| Thêm ErrorCode mới (vd `STALE`, `OUTDATED`) | **CẤM** — tái dùng `CONFLICT` (409) đã có (§4) |
| Thêm capability mới cho offline/sync | **CẤM** — quyền vẫn 1 SSoT `rbac.py` (`ADR-MOBILE-001 (b)`) |
| Sửa `services/notifications.py` / DocType / api nghiệp vụ | Phase A read-only; impl Phase E |
| Sinh **offline-write-audit** (audit khi còn trong queue) | **CẤM** — audit NĐ98 chỉ sinh khi record ghi THẬT ở BE (§6, đồng bộ `ADR-001` + `01-architecture §6.2` lines 142-143) |
| Bồi 4 path nghiệp vụ với header offline trong OpenAPI | Phase C/E wire — A6 chỉ đặt **COMPONENTS dùng-lại** (§7.2) |

---

## 1. Ba lằn ranh đọc / ghi / online-only (đồng bộ `05-personas-mvp §4`)

> **Đồng bộ nhãn với `05-personas-mvp §4`** (3 nhãn: `read-cache-ok` / `idempotent-write-needed` / `online-only`) — KHÔNG mâu thuẫn. Doc này (`07`) bồi **cơ chế** cho từng nhãn; `05 §4` gán **nhãn per-màn**. Mỗi màn ở `05 §4` rơi vào ĐÚNG 1 trong 3 lằn ranh dưới.

| Lằn ranh (nhãn `05 §4`) | Cơ chế A6 áp dụng | Màn áp (theo `05 §4`) |
|---|---|---|
| **`read-cache-ok`** | **§2 Read-cache** — conditional GET (`ETag` + `If-Modified-Since`) + cache-store local + cờ "cập nhật lúc…/ngoại tuyến" | `QrScanView` (resolve) · `AssetScanInfoView` · `AssetDetailView` · `AssetListView` · `list_pm_schedules` · `MyWorkOrdersView` (PM/CM/Incident/Cal) |
| **`idempotent-write-needed`** | **§3 Write-queue idempotency-key** + **§4 Conflict policy** + **§5 Lifecycle hàng đợi** | `IncidentCreateView` (báo hỏng) · `PMWorkOrderCreateView` · `CMCreateView` · `CalibrationCreateView` (+ đường **asset-create** — §3.4) |
| **`online-only`** | KHÔNG cache, KHÔNG queue — yêu cầu mạng trực tiếp; mất mạng → chặn + báo "cần kết nối" | `LoginView` (OAuth flow + cấp/refresh token) |

> **Invariant nhất quán:** 3 nhãn ↔ 3 lằn ranh là **ánh xạ 1-1**. Nếu Phase C/E phát hiện 1 màn cần đổi nhãn (vd thêm màn ghi mới) → cập nhật `05 §4` TRƯỚC, rồi map vào đúng cơ chế ở đây (Self-Correction, KHÔNG để 2 doc lệch).

---

## 2. Read-cache (HTTP conditional GET — `ETag` + `If-Modified-Since`)

> Áp cho mọi màn `read-cache-ok` (§1). Mục tiêu: app hiển thị dữ liệu cũ-an-toàn khi mất mạng + tiết kiệm băng thông khi có mạng (304 Not Modified). **HỢP ĐỒNG cho Phase E** (BE chưa phát `ETag` cho `/api/method` — xác nhận §2.4).

### 2.1 Cơ chế conditional GET (hợp đồng)

```
GET /api/method/assetcore.api.imm00.get_asset?name=AC-ASSET-2026-00001
Authorization: Bearer <access_token>
If-None-Match: "<etag-đã-cache>"            # nếu app đã có bản cache
If-Modified-Since: <HTTP-date-bản-cache>     # fallback khi không có ETag

─── BE trả về 1 trong 2 ───
(a) 200 OK + ETag: "<etag-mới>" + Last-Modified: <date> + body envelope {success,data}
    → app cập nhật cache + cờ "cập nhật lúc <now>"
(b) 304 Not Modified  (body RỖNG)
    → app DÙNG cache cũ; chỉ refresh timestamp "cập nhật lúc…", KHÔNG tải lại data
```

### 2.2 Khoá validator (ETag derive từ `modified`)

- **`ETag`** của 1 doc derive từ Frappe `modified` timestamp (primitive có sẵn MỌI doc — §4.1) — vd weak ETag `W/"<docname>-<modified-epoch>"`. Doc đổi ⇒ `modified` đổi ⇒ ETag đổi ⇒ 304 không còn áp.
- **`Last-Modified`** = `modified` của doc (hoặc max(`modified`) của tập list) ở định dạng HTTP-date cho fallback `If-Modified-Since`.
- **List endpoint** ("phiếu của tôi"): ETag derive từ tổ hợp (count + max `modified` của trang) — đổi khi có item mới/sửa. (Chi tiết thuật toán = Phase E; A6 chốt nguồn validator = `modified`.)

### 2.3 Cờ trạng thái dữ liệu trên UI (hợp đồng app)

App native PHẢI hiển thị 1 trong 2 cờ cho mọi màn read-cache:

| Cờ | Khi nào | Hành vi |
|---|---|---|
| **"Cập nhật lúc HH:mm"** | Vừa nhận 200/304 thành công (online) | Hiển thị mốc làm-tươi gần nhất; data đáng tin. |
| **"Ngoại tuyến — dữ liệu có thể cũ"** | GET fail (mất mạng) → fallback cache | Hiển thị data cache + banner ngoại tuyến; cờ overdue (`pm_overdue`/`calibration_overdue`) CÓ THỂ stale → KHÔNG dùng để ra quyết định an toàn tối hậu khi đang offline. |

> **Quan trọng (SSoT overdue):** cờ `pm_overdue`/`calibration_overdue` là **server-flag** (`memory/overdue_server_flag_ssot.md`; `05 §2b`). App **KHÔNG** tự so ngày client-clock để "tự tính overdue" khi offline — chỉ hiển thị giá trị cache + nhãn "có thể cũ", refresh khi online. Đây là rào chống drift logic giữa cache offline và SSoT server.

### 2.4 Khả thi tại source (verify-only, Phase A read-only)

- Frappe `/api/method/<dotted>` (RPC) **HIỆN KHÔNG tự phát `ETag`/`Last-Modified`** cho response whitelisted method (envelope JSON tự build, `utils/response.py`). ⇒ Read-cache conditional GET là **việc Phase E**: lớp bọc `api/mobile/v1` HOẶC middleware set header `ETag`/`Last-Modified` từ `modified` của doc + đọc `If-None-Match`/`If-Modified-Since` → trả 304 khi khớp.
- **Primitive khả dụng:** mọi doc Frappe có cột `modified` (timestamp tự cập nhật mỗi lần ghi) — nguồn validator chuẩn cho cả ETag (read-cache) lẫn optimistic-lock (§4). KHÔNG cần thêm field.
- A6 KHÔNG impl header này; chỉ CHỐT hợp đồng + nguồn validator. OpenAPI §7.2 đặt sẵn COMPONENTS `ETag`/`If-Modified-Since`/304 để Phase C/E wire vào 4 path read.

---

## 3. Write-queue idempotency-key contract

> Áp cho mọi màn `idempotent-write-needed` (§1) + đường **asset-create**. Mục tiêu: KTV báo hỏng/yêu cầu WO **khi mất mạng** → ghi vào hàng đợi local → khi có mạng app gửi lại; **retry KHÔNG tạo bản ghi thứ 2**. **HỢP ĐỒNG cho Phase E** (đường write hiện CHƯA có idempotency-key — `05 §4` bàn giao).

### 3.1 Hợp đồng idempotency-key (CHỐT — đo được)

| Hạng mục | Hợp đồng (CHỐT) |
|---|---|
| **Ai sinh key** | **Client (app native) sinh** — 1 key/1 thao tác-ghi-logic, sinh NGAY khi user bấm "Gửi" (kể cả offline), gắn cố định với mục trong hàng đợi (KHÔNG đổi qua các lần retry). |
| **Định dạng key** | **UUIDv4** HOẶC **ULID** (chuỗi đủ entropy, đụng-độ thực tế = 0). Opaque với BE. |
| **Truyền key** | Header HTTP **`Idempotency-Key: <uuid|ulid>`** trên request ghi (POST). (Chuẩn de-facto Stripe/IETF draft — repo native dễ generate sẵn.) |
| **BE dedupe (Phase E)** | BE lưu ánh xạ **`key → first-response`** (envelope gốc + HTTP-status logic). Lần đầu: xử lý nghiệp vụ THẬT + lưu (key→response) + trả. Lần sau (retry trùng key): **KHÔNG tạo bản ghi thứ 2** — TRẢ LẠI **response gốc** đã lưu. |
| **Replay shape** | Replay trùng key → giữ **NGUYÊN shape envelope cũ** (`{success,data}` của lần đầu). **KHÔNG** trả `DUPLICATE` chỉ vì là retry-an-toàn (retry = idempotent thành công, KHÔNG phải lỗi trùng khoá nghiệp vụ — §4.4 phân biệt). |
| **Window / TTL key** | Store (key→response) giữ trong **TTL hữu hạn** (đề xuất **24h**, đủ phủ chu kỳ mất-mạng-tại-hiện-trường của 1 ca trực + sync trễ; chốt giá trị cuối ở Phase E). Sau TTL: key hết hiệu lực dedupe (request mới cùng key = thao tác mới). |
| **Scope key** | **Per-token / per-user** (gắn `frappe.session.user` từ bearer→`set_user`). Key của user A KHÔNG dedupe-nhầm với user B. (1 SSoT — bearer xác định actor; KHÔNG dựng scope thứ 2.) |

### 3.2 Áp ĐÚNG 4 màn `idempotent-write-needed` (`05 §4`)

| Màn (`05 §4`) | Endpoint write (tái dùng — `05 §3`) | Cap | Idempotency-Key bắt buộc |
|---|---|---|---|
| `IncidentCreateView` (báo hỏng) | `assetcore.api.imm12.report_incident` (`imm12.py:71`) | `corrective.create` | ✅ — mất báo hỏng = rủi ro an toàn TBYT (NĐ98) |
| `PMWorkOrderCreateView` | `assetcore.api.imm08.create_pm_work_order` (`imm08.py:91`) | `pm.create` | ✅ |
| `CMCreateView` | `assetcore.api.imm09.create_repair_work_order` (`imm09.py:36`) | `repair.create` | ✅ |
| `CalibrationCreateView` | `assetcore.api.imm11.create_calibration` (`imm11.py:90`) | `calibration.create` | ✅ |

### 3.3 Đường write tổng quát (sequence hợp đồng)

```
[Offline] User bấm "Gửi" → app sinh Idempotency-Key=K + enqueue {endpoint, payload, K, status=queued}
   ... mất mạng — chờ ...
[Online]  app POST endpoint + header Idempotency-Key: K   (status=sent)
   ├─ 200 {success:true, data:{name:...}}        → status=acked   (record tạo THẬT — audit NĐ98 sinh ở đây, §6)
   ├─ 200 {success:true, data:{...}} (REPLAY)     → status=acked   (BE đã có K → trả response gốc, KHÔNG tạo thêm)
   ├─ 200 {success:false, code:CONFLICT,409}      → status=conflict (§4 — server-wins + báo user)
   └─ 200 {success:false, code:VALIDATION/...}    → status=failed  (lỗi nghiệp vụ thật — báo user sửa, KHÔNG auto-retry vô hạn)
```

> **Retry-an-toàn:** nếu app gửi K nhưng KHÔNG nhận được response (timeout/rớt mạng giữa chừng) → app retry CÙNG K. BE: nếu lần trước đã xử lý → trả response gốc (acked); nếu chưa tới BE → xử lý lần đầu. ⇒ **at-most-once tạo bản ghi**, bất kể số lần retry.

### 3.4 Đường asset-create (ngoài 4 màn MVP — vẫn áp idempotency)

Đường **tạo tài sản** (`assetcore.api.imm00.create_asset`, form_dict-based — `04-api-contract §10` / generator D5) cũng là write có hệ quả tạo-bản-ghi ⇒ **áp cùng idempotency-key contract** khi đi qua đường offline/queue (vd nhập tài sản mới tại hiện trường khi mất mạng). KHÔNG tạo Asset trùng khi retry. (Asset-create KHÔNG nằm trong 5 feature MVP field-tech của `05 §2`, nhưng acceptance A6 yêu cầu phủ đường write này — ghi nhận như hợp đồng cho Phase E nếu repo native hỗ trợ tạo tài sản offline.)

### 3.5 Khả thi tại source (verify-only)

- Endpoint write hiện (`report_incident`/`create_*`/`create_asset`) **CHƯA đọc `Idempotency-Key`** → idempotency dedupe là **việc Phase E** (middleware/lớp bọc đọc header → tra store key→response → short-circuit nếu trùng, ngược lại chạy nghiệp vụ + lưu). A6 KHÔNG impl.
- Store (key→first-response) đề xuất Phase E: `frappe.cache` (Redis, TTL native) HOẶC DocType nhẹ (nếu cần audit/bền). Chốt ở Phase E.

---

## 4. Conflict policy (optimistic-lock qua Frappe `modified`)

> Mục tiêu: khi 2 nguồn (mobile offline-queue vs web/khác) cùng sửa 1 doc, tránh **silent-overwrite** (ghi đè mất dữ liệu người khác). **HỢP ĐỒNG cho Phase E.**

### 4.1 Primitive: Frappe `modified` (verify-source — KHÔNG bịa, KHÔNG thêm field)

Frappe có sẵn **optimistic-lock dựa trên `modified` timestamp** trên MỌI doc:

- `Document.check_if_latest()` (`frappe/model/document.py:850-874`) so `modified` của bản đang lưu với `modified` đọc lúc mở; **khác nhau ⇒ raise `frappe.TimestampMismatchError`** (`document.py:871-874`, message _"Document has been modified after you have opened it"_).
- `check_if_latest()` được gọi trong luồng save/submit (`document.py:301`, `:408`).
- Exception class: `frappe.TimestampMismatchError(ValidationError)` (`frappe/exceptions.py:156`).
- ⇒ Primitive **đã khả dụng, không cần thêm field/cột**. `modified` cũng là nguồn validator cho ETag read-cache (§2.2) — 1 primitive phục vụ cả 2.

### 4.2 Hợp đồng conflict (CHỐT)

| Hạng mục | Hợp đồng (CHỐT) |
|---|---|
| **Cơ chế** | **Optimistic-lock qua `modified`** — client gửi `modified` đã đọc (qua header **`If-Match: "<modified>"`** HOẶC field `version`/`modified` trong payload update). BE so với `modified` hiện tại của doc. |
| **Khi xung đột** | `modified` client-gửi ≠ `modified` BE-hiện-tại ⇒ **xung đột** → trả ErrorCode **`CONFLICT` (409)** — **TÁI DÙNG** mã đã có (`utils/response.py` `_HTTP_FOR_CODE[CONFLICT]=409`; catalog `04-api-contract §4` hàng #7). **KHÔNG bịa mã mới** (không `STALE`/`OUTDATED`). |
| **Chính sách mặc định** | **server-wins + BÁO người dùng.** BE KHÔNG ghi đè theo client; trả 409 `CONFLICT` + message VI "Bản ghi đã được người khác cập nhật. Vui lòng tải lại." App: tải lại bản mới (refresh) → cho user xem khác biệt → user quyết định gửi lại. **KHÔNG silent-overwrite.** |
| **KHÔNG auto-merge** | MVP KHÔNG merge tự động field-level (rủi ro mất dữ liệu y tế). server-wins là mặc định an toàn; merge thông minh = backlog ngoài MVP. |

### 4.3 Lưu ý phạm vi conflict cho MVP

- 4 màn write MVP (`05 §3`) chủ yếu là **CREATE** (report_incident/create_*), KHÔNG phải update doc đang tồn tại ⇒ conflict optimistic-lock **ít chạm** ở MVP create-path (create không có `modified` cũ để so). Conflict policy CHỐT ở đây phủ **đường UPDATE** tương lai (vd edit phiếu đã tạo, đổi trạng thái WO) — là hợp đồng sẵn cho Phase E khi mở luồng sửa.
- Với create-path, lằn bảo vệ chính là **idempotency-key** (§3, chống tạo trùng do retry), KHÔNG phải optimistic-lock. Hai cơ chế bù nhau: idempotency = chống-trùng-do-retry; optimistic-lock = chống-ghi-đè-do-edit-song-song.

### 4.4 Phân biệt CONFLICT (409) vs DUPLICATE (409) vs replay-an-toàn

> 3 tình huống cùng "đụng nhau" nhưng KHÁC bản chất — client xử lý KHÁC nhau. Cả `CONFLICT` và `DUPLICATE` đều map 409 (verify `utils/response.py`).

| Tình huống | ErrorCode | HTTP | App xử lý |
|---|---|---|---|
| **Optimistic-lock xung đột** (edit song song, `modified` lệch) | **`CONFLICT`** | 409 | server-wins: tải lại → user xem → gửi lại (§4.2). |
| **Trùng khoá nghiệp vụ** (vd serial/asset_code đã tồn tại — KHÔNG do retry) | **`DUPLICATE`** | 409 | báo user "đã tồn tại" — sửa input (lỗi nghiệp vụ thật, `04-api-contract §4` #9). |
| **Retry trùng idempotency-key** (cùng K, thao tác an toàn lặp) | **(KHÔNG lỗi)** | 200 | BE trả **response gốc** (acked) — giữ shape envelope cũ, **KHÔNG** `DUPLICATE` (§3.1). |

> ⚠️ **Hợp đồng then chốt:** retry-an-toàn-trùng-key ≠ lỗi-trùng-khoá. Replay 1 idempotency-key đã thành công PHẢI trả **response gốc thành công** (KHÔNG bao giờ biến thành `DUPLICATE`). `DUPLICATE` chỉ dành cho trùng-khoá-nghiệp-vụ-thật (input đụng unique constraint, KHÔNG phải do app retry).

---

## 5. Lifecycle hàng đợi offline (queued → sent → acked / conflict / failed)

> State machine của **1 mục trong write-queue** ở app native (hợp đồng để repo native + BE đồng thuận). KHÔNG phải workflow Frappe; là trạng thái client-side của thao tác-ghi-ngoại-tuyến.

```
         (user bấm Gửi, sinh Idempotency-Key)
                       │
                       ▼
                  ┌─────────┐   có mạng + đang gửi   ┌──────┐
                  │ queued  │ ─────────────────────▶ │ sent │
                  └─────────┘                        └──┬───┘
                       ▲                                │
              (mất mạng / chờ)                          │  nhận response (theo envelope.body.success/code)
                       │                                ▼
                       │            ┌───────────────────┼───────────────────┐
                       │            ▼                    ▼                   ▼
                       │       ┌─────────┐         ┌──────────┐        ┌─────────┐
                       │       │  acked  │         │ conflict │        │ failed  │
                       │       └─────────┘         └────┬─────┘        └────┬────┘
                       │   (success:true —             │                   │
                       │    record THẬT / replay)      │ (CONFLICT 409)    │ (VALIDATION/BUSINESS_RULE/…)
                       │                               ▼                   ▼
                       └───────────────── user-resolve: tải lại → gửi lại (K mới nếu là thao tác mới)
```

| State | Ý nghĩa | Chuyển tiếp |
|---|---|---|
| **queued** | Đã ghi vào hàng đợi local (có thể offline). Idempotency-Key đã gán cố định. | → `sent` khi có mạng + bắt đầu gửi. |
| **sent** | Đã POST lên BE, đang chờ response (hoặc timeout). | → `acked` / `conflict` / `failed` theo response; timeout/rớt → quay `queued` để retry **cùng K**. |
| **acked** | BE xác nhận thành công (`success:true`) — record tạo THẬT **HOẶC** replay trả response gốc. **Audit NĐ98 sinh tại đây** (§6). | Terminal (xoá khỏi queue sau khi đồng bộ UI). |
| **conflict** | BE trả `CONFLICT` (409) — optimistic-lock (§4). | → user-resolve: tải lại bản server → quyết định gửi lại. |
| **failed** | Lỗi nghiệp vụ thật (`VALIDATION`/`BUSINESS_RULE`/`FORBIDDEN`/…). | → báo user sửa; KHÔNG auto-retry vô hạn (tránh bão request). |

> **Retry policy (hợp đồng):** chỉ auto-retry cho lỗi transient (mất mạng, timeout, 429/`RATE_LIMITED` với backoff — `04-api-contract §4` #12). Lỗi nghiệp vụ (`failed`) + `conflict` cần user-resolve, KHÔNG auto-retry. Mọi retry transient dùng **cùng Idempotency-Key** (§3.1) ⇒ an toàn.

---

## 6. Audit / NĐ98 — chỉ sinh khi record ghi THẬT ở BE

> **Nguyên tắc CHỐT (đồng bộ `ADR-MOBILE-001` Consequences + `01-architecture §6.2` lines 142-143):** audit trail NĐ98 (SHA-256 lifecycle chain `utils/lifecycle.py`) **chỉ sinh khi record được ghi THẬT ở BE** — KHÔNG sinh khi thao tác còn nằm trong hàng đợi offline của app.

- **Offline queue KHÔNG sinh audit:** mục ở state `queued`/`sent` chưa có bản ghi BE ⇒ chưa có lifecycle event, chưa có hash-chain entry. Đúng — audit là bằng chứng bất biến về **hành động đã xảy ra ở BE**, không phải về ý định lưu ở app.
- **Audit sinh tại `acked`:** khi BE xử lý write THẬT (lần đầu, KHÔNG phải replay) → `set_user` (bearer xác định actor) → service emit lifecycle event + audit chain với **đúng actor + đúng timestamp BE** (`05 §0.3`). Replay (trùng idempotency-key) KHÔNG sinh audit thứ 2 (vì KHÔNG tạo record thứ 2 — §3.1).
- **Hệ quả timestamp:** lifecycle event mang timestamp **lúc BE ghi** (lúc sync), KHÔNG phải lúc user bấm-offline. Nếu nghiệp vụ cần "thời điểm phát hiện sự cố tại hiện trường" thì đó là **field nghiệp vụ trong payload** (vd `detected_at` do app gửi), TÁCH BIỆT với audit-timestamp (lúc ghi BE). Phân biệt này = hợp đồng cho Phase E nếu cần.
- **KHÔNG offline-write-audit:** KHÔNG dựng cơ chế audit-trong-queue ở app (sẽ là audit-chain thứ 2, drift khỏi SSoT BE + không bất biến). 1 SSoT audit = BE.

---

## 7. Bàn giao Phase E + cross-link

### 7.1 Bàn giao Phase E (việc impl — A6 chỉ giao hợp đồng)

| # | Việc Phase E | Hợp đồng nguồn (A6) |
|---|---|---|
| 1 | **Read-cache:** lớp bọc/middleware set `ETag`/`Last-Modified` từ `modified` + đọc `If-None-Match`/`If-Modified-Since` → 304 | §2 |
| 2 | **Idempotency dedupe:** đọc header `Idempotency-Key` → store `key→first-response` (TTL 24h, per-user) → replay trả response gốc, KHÔNG tạo record thứ 2 | §3 |
| 3 | **Optimistic-lock wiring:** đọc `If-Match`/`modified` → so `check_if_latest` semantics → trả `CONFLICT` (409) khi lệch (server-wins) | §4 |
| 4 | **Write-queue (app, repo native):** lifecycle queued→sent→acked/conflict/failed + retry transient cùng key | §5 |
| 5 | **Audit:** không đổi — audit sinh tự nhiên khi BE ghi record THẬT (giữ `utils/lifecycle.py`) | §6 |
| 6 | **OpenAPI Phase C/E:** wire COMPONENTS offline (§7.2) vào 4 path nghiệp vụ + path read | §7.2 |

> **Ranh giới repo:** §1-§4 BE (lớp bọc `api/mobile/v1` HOẶC middleware) + repo native (queue + cache). §5 thuần repo native (app-layer state). KHÔNG sửa code nghiệp vụ; lớp offline BỌC quanh service hiện có (`ADR-MOBILE-001 (c)`).

### 7.2 OpenAPI — COMPONENTS dùng-lại cho offline (đặt ở A6, KHÔNG bồi path nghiệp vụ)

A6 bổ sung vào `openapi/assetcore-mobile.openapi.yaml` ở mức **SKELETON COMPONENTS dùng-lại** (KHÔNG đụng 4 path nghiệp vụ — để Phase C/E wire):

| Component | Loại | Vai trò |
|---|---|---|
| `IdempotencyKey` | `parameters` (header, optional) | Header `Idempotency-Key` cho path write (§3). |
| `IfMatch` | `parameters` (header, optional) | Header `If-Match` (optimistic-lock `modified`, §4). |
| `IfNoneMatch` | `parameters` (header, optional) | Header `If-None-Match` (read-cache, §2). |
| `IfModifiedSince` | `parameters` (header, optional) | Header `If-Modified-Since` (read-cache fallback, §2). |
| `ETag` | `headers` (response) | Header `ETag` trả về (read-cache validator, §2). |
| `LastModified` | `headers` (response) | Header `Last-Modified` trả về (§2). |
| `Conflict409` | `responses` (ĐÃ CÓ) | **Tái dùng** — 409 `CONFLICT` reuse `Error` envelope (§4). KHÔNG thêm mới. |
| `NotModified304` | `responses` | 304 shape (body rỗng + header ETag) cho read-cache (§2). |

> COMPONENTS này là **building-block dùng-lại** — Phase C/E ráp vào path nghiệp vụ/read. yaml vẫn lint OK + KHÔNG phá `test_oas_generator`/`test_oas_signatures` (2 test introspect BE `assetcore/api/openapi.py` + whitelist signatures, KHÔNG đọc file mobile yaml).

### 7.3 Cross-link (2 chiều)

- **Nhãn OFFLINE per-màn (nguồn của §1):** [`05-personas-mvp.md §4`](./05-personas-mvp.md) — 3 nhãn `read-cache-ok`/`idempotent-write-needed`/`online-only` + bàn giao Phase E. `05 §4` trỏ NGƯỢC tới doc này (cross-link 2 chiều).
- **ErrorCode catalog (CONFLICT/DUPLICATE/RATE_LIMITED):** [`04-api-contract.md §4`](./04-api-contract.md) — 15 mã + HTTP map; §5 quirk HTTP-200 wrapper (client đọc `body.code`/`body.http_status`).
- **Audit chỉ-khi-ghi-thật (nền §6):** [`ADR-MOBILE-001.md`](./ADR-MOBILE-001.md) Consequences + [`01-architecture.md §6.2`](./01-architecture.md) (lines 142-143).
- **Quyết định A6:** [`ADR-MOBILE-003.md`](./ADR-MOBILE-003.md) — idempotency-key client-gen + conflict optimistic-lock `modified` + server-wins + read-cache ETag + no-offline-audit-until-sync.
- **Tổng quan + roadmap (Phase E row):** [`00-overview.md`](./00-overview.md) §3 (Phase E) · §4 (chỉ mục file).
- **Source SSoT (verify-only):** `utils/response.py` (`CONFLICT`/`DUPLICATE`/`RATE_LIMITED` + `_HTTP_FOR_CODE`) · `frappe/model/document.py:850-874` (`check_if_latest` optimistic-lock) · `frappe/exceptions.py:156` (`TimestampMismatchError`) · `utils/lifecycle.py` (audit SHA-256 chain) — KHÔNG sửa ở Phase A.
