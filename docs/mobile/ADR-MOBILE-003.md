# ADR-MOBILE-003 — Chiến lược offline & sync cho mobile: idempotency-key + optimistic-lock `modified` + read-cache ETag

| Mục | Giá trị |
|---|---|
| ADR | MOBILE-003 |
| Phase | A — Kiến trúc & Feasibility (A6 — Offline/Sync strategy) |
| Ngày | 2026-06-09 |
| Tác giả | BA Lead + System Architect (mobile) |
| **Status** | **Accepted** |
| Bám quyết định | D-AUTH · D-MVP · D-STACK (`00-overview.md §2`) · ADR-MOBILE-001 (kiến trúc nền) |
| Đặc tả đi kèm | [`07-offline-sync.md`](./07-offline-sync.md) (read-cache · write-queue idempotency · conflict · lifecycle hàng đợi · audit) |

> Mọi claim kỹ thuật trích dẫn evidence `file:line` đã VERIFY tại source **Frappe v15.107.2** (site `miyano`, 2026-06-09). Phase A read-only — KHÔNG sửa code, KHÔNG thêm ErrorCode, KHÔNG thêm capability.

---

## Context

[`ADR-MOBILE-001`](./ADR-MOBILE-001.md) đã chốt kiến trúc nền mobile (wire OAuth · RBAC 1 SSoT · reuse endpoint · OpenAPI hợp đồng · bearer-không-cookie) và ghi rõ trong Consequences: **"Push/offline/sync chỉ kiến trúc ở Phase A — device-token registry + idempotency + conflict policy ở Phase E"**. `01-architecture §6.2` cũng đã nêu sơ bộ nhu cầu read-cache + idempotency-key + conflict policy + nguyên tắc "audit chỉ sinh khi record THẬT ghi ở BE" (lines 142-143).

Persona field-tech làm việc trong **mạng chập chờn** (`05-personas-mvp §1.1`: Wi-Fi yếu/chết vùng tầng hầm CĐHA, phòng chì X-quang, 4G phập phù). `05 §4` đã gán nhãn OFFLINE per-màn (`read-cache-ok` / `idempotent-write-needed` / `online-only`) như **yêu cầu** cho Phase E, NHƯNG chưa chốt **cơ chế** cho từng nhãn. ADR này CHỐT 4 cơ chế (hợp đồng cho Phase E impl), tránh Phase E đi sai hướng (đặc biệt: KHÔNG bịa ErrorCode mới, KHÔNG silent-overwrite, KHÔNG offline-audit).

Đã khảo sát read-only tại source và xác nhận khả thi:

- `CONFLICT` (409), `DUPLICATE` (409), `RATE_LIMITED` (429) đã tồn tại trong `utils/response.py` (`_HTTP_FOR_CODE`) + catalog `04-api-contract §4` ⇒ KHÔNG cần mã mới.
- Frappe có **optimistic-lock primitive sẵn** qua `modified` timestamp (`Document.check_if_latest()` → `TimestampMismatchError`) trên MỌI doc ⇒ không cần thêm field.
- `/api/method` (RPC whitelisted) hiện KHÔNG tự phát `ETag`/`Last-Modified` ⇒ read-cache conditional GET là việc Phase E (lớp bọc/middleware), KHÔNG impl ở A6.

---

## Decision

### (a) Idempotency-key — client sinh + BE dedupe (replay trả response gốc)

Client (app native) **sinh idempotency-key** (UUIDv4 hoặc ULID) cho mỗi thao tác-ghi-logic, gửi qua header **`Idempotency-Key`**. **BE (Phase E) lưu `key → first-response`** + **replay trả LẠI response gốc** (KHÔNG tạo bản ghi thứ 2). Áp ĐÚNG 4 màn `idempotent-write-needed` (`05 §4`: báo hỏng `report_incident` · PM `create_pm_work_order` · CM `create_repair_work_order` · Cal `create_calibration`) + đường **asset-create**. Key window/TTL hữu hạn (đề xuất 24h) + scope **per-token/per-user** (`frappe.session.user` từ bearer).

- **Replay-an-toàn ≠ DUPLICATE:** retry trùng key (thao tác an toàn lặp do mất mạng/timeout) → BE trả **response gốc thành công** (giữ nguyên shape envelope `{success,data}` cũ). **KHÔNG** trả `DUPLICATE` chỉ vì retry. `DUPLICATE` (409) chỉ dành cho **trùng-khoá-nghiệp-vụ-thật** (input đụng unique constraint — `04 §4` #9).
- **Khả thi:** endpoint write hiện CHƯA đọc `Idempotency-Key` ⇒ dedupe là việc Phase E (middleware đọc header → tra store key→response → short-circuit; store đề xuất `frappe.cache`/Redis TTL hoặc DocType nhẹ). A6 chỉ chốt hợp đồng + định dạng key + header name.
- Chi tiết: [`07-offline-sync.md §3`](./07-offline-sync.md).

### (b) Conflict = optimistic-lock qua `modified` + server-wins (báo người dùng)

Xung đột ghi đè (edit song song mobile-queue vs web/khác) giải bằng **optimistic-lock dùng Frappe `modified` timestamp** (primitive có sẵn MỌI doc): client gửi `modified` đã đọc (header **`If-Match`** / field `version`); BE so với `modified` hiện tại → lệch ⇒ trả **`CONFLICT` (409)** (TÁI DÙNG mã đã có — KHÔNG bịa mới). Chính sách mặc định = **server-wins + BÁO người dùng** (tải lại bản server → user xem khác biệt → quyết định gửi lại). **KHÔNG silent-overwrite**, **KHÔNG auto-merge** field-level ở MVP (rủi ro mất dữ liệu y tế).

- **Evidence primitive:** `Document.check_if_latest()` so `modified` → raise `frappe.TimestampMismatchError` — `frappe/model/document.py:850-874` (gọi tại `:301`/`:408`); exception `frappe/exceptions.py:156`. ErrorCode `CONFLICT`→409 verified `utils/response.py` (`_HTTP_FOR_CODE`).
- **Phạm vi MVP:** 4 màn write MVP chủ yếu là CREATE (không có `modified` cũ để so) ⇒ optimistic-lock ít chạm ở create-path; lằn bảo vệ create = idempotency-key (a). Conflict policy (b) là hợp đồng sẵn cho **đường UPDATE** tương lai (edit/đổi-trạng-thái phiếu) — Phase E.
- Chi tiết: [`07-offline-sync.md §4`](./07-offline-sync.md).

### (c) Read-cache = ETag / If-Modified-Since (HTTP conditional GET)

Màn `read-cache-ok` (`05 §4`) dùng **conditional GET**: BE (Phase E) phát `ETag` + `Last-Modified` (derive từ `modified` — cùng primitive với (b)); client gửi `If-None-Match`/`If-Modified-Since` → BE trả **304 Not Modified** (body rỗng) khi chưa đổi → app dùng cache. App hiển thị cờ **"cập nhật lúc…"** (online) / **"ngoại tuyến — dữ liệu có thể cũ"** (fallback cache). Cờ overdue (`pm_overdue`/`calibration_overdue`) là **server-flag** — app KHÔNG tự so client-clock khi offline (`memory/overdue_server_flag_ssot.md`).

- **Khả thi:** `/api/method` hiện KHÔNG phát `ETag`/`Last-Modified` ⇒ Phase E set header từ `modified` (lớp bọc/middleware). A6 chốt nguồn validator = `modified` + đặt COMPONENTS OpenAPI dùng-lại (`07 §7.2`).
- Chi tiết: [`07-offline-sync.md §2`](./07-offline-sync.md).

### (d) KHÔNG offline-write-audit cho tới khi sync THẬT

Audit trail NĐ98 (SHA-256 lifecycle chain `utils/lifecycle.py`) **chỉ sinh khi record được ghi THẬT ở BE** (lúc sync, state `acked` của hàng đợi), KHÔNG sinh khi thao tác còn trong queue offline (`queued`/`sent`). Replay (trùng idempotency-key) KHÔNG sinh audit thứ 2 (vì không tạo record thứ 2). **KHÔNG** dựng cơ chế audit-trong-queue ở app (sẽ là audit-chain thứ 2 → drift khỏi SSoT BE + không bất biến). 1 SSoT audit = BE.

- **Đồng bộ:** `ADR-MOBILE-001` Consequences + `01-architecture §6.2` lines 142-143 ("Audit trail NĐ98 SHA-256 chain chỉ sinh khi record THẬT ghi ở BE — offline queue KHÔNG sinh audit cho tới khi sync thành công").
- **Hệ quả timestamp:** lifecycle event mang timestamp lúc-BE-ghi (sync), KHÔNG phải lúc user bấm-offline. Nếu cần "thời điểm phát hiện tại hiện trường" → field nghiệp vụ trong payload (vd `detected_at`), TÁCH khỏi audit-timestamp.
- Chi tiết: [`07-offline-sync.md §6`](./07-offline-sync.md).

---

## Alternatives considered

| # | Phương án | Vì sao LOẠI |
|---|---|---|
| A1 | **BE sinh idempotency-key (server-gen)** | Client offline cần key NGAY lúc bấm-gửi (chưa có mạng để xin server-gen) + key phải ổn định qua mọi retry. Client-gen UUID/ULID đáp ứng cả 2; server-gen không khả thi cho offline-first. ⇒ chọn (a) client-gen. |
| A2 | **Last-write-wins (silent overwrite) cho conflict** | Ghi đè im lặng = mất dữ liệu người khác (web edit song song) → rủi ro nghiêm trọng với dữ liệu thiết bị y tế (NĐ98 truy xuất). ⇒ chọn (b) server-wins + báo user. |
| A3 | **Thêm ErrorCode mới `STALE`/`OUTDATED`/`SYNC_CONFLICT`** | `CONFLICT` (409) đã tồn tại + đúng ngữ nghĩa (trùng lặp / xung đột trạng thái — `04 §4` #7); thêm mã = vỡ catalog 15-mã SSoT + buộc client+FE mirror mã mới. ⇒ tái dùng `CONFLICT`. |
| A4 | **Auto-merge field-level khi conflict** | Merge thông minh phức tạp + rủi ro tạo bản ghi y tế sai (trộn 2 nguồn). server-wins là mặc định an toàn cho MVP; merge = backlog ngoài MVP. ⇒ chọn (b) server-wins, no-merge. |
| A5 | **Cache thời-gian-sống cứng (TTL cache) thay conditional GET** | TTL cứng dễ phục vụ data cũ quá hạn HOẶC refetch thừa. ETag/`If-Modified-Since` (validator = `modified`) chính xác hơn: chỉ tải lại khi doc THẬT đổi + 304 tiết kiệm băng thông. ⇒ chọn (c) conditional GET. |
| A6 | **Optimistic-lock bằng field `version`/`_version` riêng** | Frappe đã có `modified` timestamp + `check_if_latest()` raise `TimestampMismatchError` trên MỌI doc (`document.py:850-874`) — primitive sẵn, không cần thêm cột/field. ⇒ chọn (b) reuse `modified`. |
| A7 | **Sinh audit ngay khi enqueue offline (offline-write-audit)** | Audit-trong-queue = audit-chain thứ 2 ở app, drift khỏi SSoT BE + không bất biến + ghi audit cho thao tác CHƯA xảy ra ở BE (sai bản chất NĐ98). ⇒ chọn (d) audit chỉ-khi-ghi-thật. |

---

## Consequences

**Tích cực:**
- **At-most-once tạo bản ghi:** idempotency-key (a) ⇒ retry-do-mất-mạng KHÔNG tạo Incident/WO/Asset trùng — đúng yêu cầu nghiệp vụ "mất báo hỏng = rủi ro an toàn" (NĐ98).
- **Không mất dữ liệu song song:** server-wins + báo user (b) ⇒ KHÔNG ghi đè im lặng; user thấy + quyết định.
- **Tái dùng primitive + mã có sẵn:** `modified` (optimistic-lock + ETag) + `CONFLICT`/`DUPLICATE`/`RATE_LIMITED` (catalog 15 mã) ⇒ KHÔNG thêm field/ErrorCode/capability ⇒ giữ 1 SSoT (quyền `rbac.py`, envelope `response.py`, audit `lifecycle.py`).
- **Audit nguyên vẹn:** (d) ⇒ audit NĐ98 vẫn 1 SSoT ở BE, đúng actor/timestamp lúc-ghi, không drift.
- **Băng thông + chịu-mất-mạng:** read-cache conditional GET (c) ⇒ 304 tiết kiệm, cache phục vụ vùng chết mạng.

**Đánh đổi / việc phải làm (carry sang Phase C/E):**
- **Phase E impl:** (1) middleware/lớp bọc đọc `Idempotency-Key` + store key→response (TTL 24h, per-user); (2) wiring `If-Match`/`modified` → 409 `CONFLICT`; (3) set `ETag`/`Last-Modified` + đọc `If-None-Match`/`If-Modified-Since` → 304. Tất cả BỌC quanh service hiện có — KHÔNG sửa code nghiệp vụ (`ADR-001 (c)`).
- **Repo native (Phase D/E):** write-queue + lifecycle queued→sent→acked/conflict/failed (`07 §5`) + cache-store + retry transient cùng key.
- **TTL key cuối cùng** (đề xuất 24h) chốt ở Phase E theo chu kỳ mất-mạng thực tế.
- **Create-path conflict ít chạm:** optimistic-lock (b) chủ yếu phủ đường UPDATE tương lai; MVP create dựa idempotency-key (a) để chống-trùng.
- **OpenAPI Phase C/E:** wire COMPONENTS offline (`07 §7.2`: `IdempotencyKey`/`IfMatch`/`IfNoneMatch`/`IfModifiedSince`/`ETag`/`LastModified`/`Conflict409`/`NotModified304`) vào path nghiệp vụ + read. A6 chỉ đặt COMPONENTS dùng-lại, KHÔNG bồi vào path.

---

## Tham chiếu chéo

- **Đặc tả đầy đủ (read-cache · write-queue · conflict · lifecycle · audit):** [`07-offline-sync.md`](./07-offline-sync.md)
- **ADR nền (link-backward):** [`ADR-MOBILE-001.md`](./ADR-MOBILE-001.md) — kiến trúc mobile (decision (b) RBAC 1 SSoT · (c) reuse-endpoint · Consequences push/offline/sync Phase E)
- **Nhãn OFFLINE per-màn:** [`05-personas-mvp.md §4`](./05-personas-mvp.md) — 3 nhãn `read-cache-ok`/`idempotent-write-needed`/`online-only`
- **ErrorCode catalog (CONFLICT/DUPLICATE/RATE_LIMITED + HTTP map):** [`04-api-contract.md §4`](./04-api-contract.md) · §5 quirk HTTP-200 wrapper
- **Audit nguyên tắc:** [`01-architecture.md §6.2`](./01-architecture.md) (lines 142-143)
- **Tổng quan + roadmap Phase E:** [`00-overview.md`](./00-overview.md) §3 · §4
- **Source SSoT (verify-only — KHÔNG sửa Phase A):** `utils/response.py` (`CONFLICT`/`DUPLICATE`/`RATE_LIMITED` + `_HTTP_FOR_CODE`) · `frappe/model/document.py:850-874` (`check_if_latest`) · `frappe/exceptions.py:156` (`TimestampMismatchError`) · `utils/lifecycle.py` (audit SHA-256 chain)
