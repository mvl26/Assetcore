# 05 — API Specification — IMM-00 Foundation (Master / Cross-cutting)

| Mục | Giá trị |
|---|---|
| Module | IMM-00 — Foundation / Master Cross-cutting |
| Phạm vi | Foundation — cross-cutting |
| Owner | BE Lead |
| Liên kết | [04 Backend Design](./04_Backend_Design.md) · [06 Frontend Design](./06_Frontend_Design.md) |
| Base URL | `/api/method/assetcore.api.imm00` |
| Phiên bản API | 3.1.1 |
| Trạng thái | **Live ✅** — synced vs `api/imm00.py` 2026-05-19 (`list_locations` đổi fields: gộp contact, patch v3_1.007) |

---

# Phần I — Conventions & Standards

## I.1. Response Envelope

Mọi response (success và error) đều dùng format chuẩn AssetCore. Client parse `response.json().message`.

**Success (HTTP 200 — luôn luôn 200):**

```json
{
  "message": {
    "success": true,
    "data": { }
  }
}
```

**Error (HTTP 400/401/403/404/409/422/500):**

```json
{
  "message": {
    "success": false,
    "error": "Thông báo lỗi tiếng Việt",
    "code": 422
  }
}
```

> **Quy tắc bắt buộc:** KHÔNG sử dụng `{"message": {...}}` trực tiếp ở tầng nghiệp vụ — luôn wrap qua `_ok(data)` / `_err(msg, code)`.

Helper chuẩn hoá (`assetcore/utils/response.py`):

```python
def _ok(data: dict | list) -> dict:
    return {"success": True, "data": data}

def _err(msg: str, code: int = 400) -> dict:
    return {"success": False, "error": msg, "code": code}
```

## I.2. Authentication

```http
# API Token (server-to-server)
Authorization: token <api_key>:<api_secret>

# Session cookie (browser / SPA)
Cookie: sid=<session_id>
X-Frappe-CSRF-Token: <csrf_token>
```

Thiếu credential → HTTP 401. Sai Role → HTTP 403.

### I.2b. Capability resolution endpoint (RBAC — stale-safe)

FE gate UX bằng capability, KHÔNG so role-name. BE là chốt chặn thật (`rbac.require`).

| Method | Verb | Path | Auth |
|---|---|---|---|
| `assetcore.api.auth.get_capabilities` | GET | `/api/method/assetcore.api.auth.get_capabilities` | Session (mọi user đã đăng nhập) |

- **Request:** không param. Resolve cho `frappe.session.user`.
- **Response:** envelope `{success: true, data: {<cap>: <bool>, ...}}` — TOÀN BỘ key trong `CAPABILITY_MAP` (shape KHÔNG đổi qua các vòng — AC5). Ví dụ trích:
  ```json
  { "success": true, "data": {
      "pm.read": true, "pm.write": true, "pm.create": false,
      "decommission.read": true, "decommission.create": true, "decommission.approve": false
  } }
  ```
- **Cache:** server cache `ac_caps::<user>` TTL 1h (xem 04 §III.1c). Sau `bench migrate` cache bị bust → lần gọi đầu trả cap-set mới (AC2).
- **Cap LẠ:** không bao giờ xuất hiện trong response (chỉ resolve key có trong map). FE hỏi cap không tồn tại → `can()=false` (KHÔNG lỗi).
- **Version-stamp (AC4):** response GỘP thêm khóa kỹ thuật `__cap_set_version__: <int>` = hằng `CAP_SET_VERSION` ở BE (bump khi tập cap đổi số lượng/tên). FE so version để invalidate persisted-caps cũ trước render gate-button. (Khóa bắt đầu `__` → FE loại khỏi vòng lặp hiển thị cap thường.)

> **Tác động cap lạ ở mọi endpoint nhạy cảm:** mọi whitelisted method gọi `rbac.require('<cap>')` đầu hàm. Nếu cap chưa nạp ở worker → `require` deny → **HTTP 403 + message VI "Khong du quyen: <cap>"**, KHÔNG 500 KeyError. Verify: `api.imm14.create_decommission` khi `decommission.create` chưa có trong worker map → 403, KHÔNG 500.

## I.3. HTTP Status Codes

| Code | Ý nghĩa | Khi nào |
|---|---|---|
| 200 | OK | Thành công (kể cả error business — parse `success` field) |
| 400 | Bad Request | Payload sai schema / thiếu param |
| 401 | Unauthorized | Sai / hết hạn token / session |
| 403 | Forbidden | Thiếu Role |
| 404 | Not Found | Record không tồn tại |
| 409 | Conflict | Vi phạm uniqueness |
| 413 | Payload Too Large | Batch nhãn QR vượt `_MAX_LABEL_BATCH` (BR-00-33) — per-request payload-DoS |
| 422 | Unprocessable Entity | Vi phạm business rule |
| 429 | Too Many Requests | Rate limit (BR-00-29 — 2 endpoint QR resolve; **BR-00-38 — rotate `regenerate_asset_qr_token`**; **BR-00-45 — `mark_label_printed`**; **BR-00-46 — `get_asset_label_data_batch`**; §D6 — `print_asset_labels_pdf` — mỗi endpoint bucket+ngưỡng RIÊNG) |
| 500 | Internal Server Error | Lỗi không xác định |

## I.4. Business Error Codes

| Code | HTTP | Business Rule | Mô tả |
|---|---|---|---|
| `AC-E001` | 400 | — | Asset không tồn tại |
| `AC-E002` | 422 | BR-00-02 | Transition lifecycle_status không hợp lệ |
| `AC-E003` | 403 | BR-00-05 | Asset Out of Service / Decommissioned — block operation |
| `AC-E004` | 400 | — | SLA Policy không tìm được |
| `AC-E005` | 422 | BR-00-08 | CAPA thiếu required field khi đóng |
| `AC-E006` | 422 | BR-00-06 | Calibration Lab thiếu ISO 17025 |
| `AC-E007` | 422 | BR-00-07 | SLA response_time ≥ resolution_time |
| `AC-E008` | 422 | — | Incident Critical chưa báo cáo BYT |
| `AC-E009` | 422 | — | Patient affected thiếu mô tả |
| `AC-E010` | 422 | BR-00-03 | Audit Trail SHA-256 chain bị tamper |
| `AC-E011` | 409 | — | asset_code / serial_no trùng |
| `AC-E012` | 409 | — | Device Model (model_name + manufacturer) trùng |

## I.5. Pagination

List endpoint hỗ trợ pagination qua query string:

| Param | Kiểu | Default | Max | Ghi chú |
|---|---|---|---|---|
| `page` | int | 1 | — | 1-based |
| `page_size` | int | 20 | **100 (HARD-CAP — clamp về [1,100] TRƯỚC khi vào query)** | Xem **BR-00-39 / §I.5b** |
| `sort` | string | `modified desc` | — | Frappe order_by syntax |

### I.5b — Hard-cap `page_size` ở mọi list endpoint imm00 (BR-00-39 — Self-Correction)

> **Self-Correction (lỗi thiết kế gốc — phát hiện factory vòng 5, 2026-06-11).** Bảng trên TỪNG khẳng định "server cap tại 100" NHƯNG 11 list-endpoint imm00 **KHÔNG enforce** cap đó lên **query thực tế**: chúng parse `page, page_size = int(page), int(page_size)` rồi truyền THẲNG `limit_page_length=page_size` vào `frappe.get_list`. Helper `paginate()` (`utils/pagination.py:8`) CHỈ clamp **metadata** trả về `[1,100]`, KHÔNG clamp limit query ⟹ (1) **invariant `len(items) <= pagination.page_size` VỠ** (metadata nói 100, query trả 100000 row), (2) **truy vấn vô giới hạn** (`page_size=100000` materialize toàn bảng → DoS / perf). Sibling **imm01** (`api/imm01.py:93,365`), **imm02** (`:70`), **imm03** (`:65,270,556`), **imm04** (`:853`) đã clamp `max(1, min(int(page_size), 100))`; **imm00 là module lệch**.

**Quy tắc (đầy đủ ràng buộc ở [02 BR-00-39 + FR-00-89](./02_Analysis_Design.md) · cài đặt ở [04 §II.1.13-PAGESIZE](./04_Backend_Design.md)):**

1. **HARD-CAP [1,100] qua MỘT SSoT** — KHÔNG copy-paste literal `100` rải rác. SSoT = hằng `MAX_PAGE_SIZE = 100` + helper `clamp_page_size(page_size) -> int` (= `max(1, min(int(page_size), MAX_PAGE_SIZE))`) đặt trong `assetcore/utils/pagination.py` (cùng nhà với `paginate()`, đã clamp metadata về cùng khoảng). `paginate()` GIỮ NGUYÊN clamp metadata; endpoint gọi `clamp_page_size()` cho biến `page_size` THỰC sự đi vào `frappe.get_list(limit_page_length=...)` **TRƯỚC** mọi query (count + list).
2. **11 endpoint áp dụng:** `list_assets`, `get_asset_timeline`, `list_lifecycle_events`, `list_suppliers`, `list_device_models`, `list_audit_trail`, `list_capas`, `list_overdue_capas`, `list_incidents`, `list_transfers`, `list_service_contracts`. Mỗi endpoint clamp `page_size` ngay sau `page, page_size = int(page), int(page_size)`, dùng giá trị đã-clamp cho CẢ `paginate()` lẫn `limit_page_length`.
3. **Biên dưới:** `page_size <= 0` hoặc âm → clamp về `>= 1` (KHÔNG `0`/âm → KHÔNG trả 0-row sai). `page_size` hợp lệ (`<= 100`) → giữ NGUYÊN (KHÔNG regress trang nhỏ default 20/50).
4. **Non-int:** giá trị không-parse-được `int()` GIỮ hành vi cũ — `int()` raise `ValueError` (KHÔNG nuốt lỗi thầm; KHÔNG thêm except). Clamp chỉ áp SAU khi `int()` thành công.
5. **Invariant sau fix:** `len(items) == pagination.page_size` (khi đủ data ở trang) VÀ luôn `<= 100`. Với `list_assets`: INVARIANT **count==drill / count==rows hiện có (BR-00-17 / ADR-IMM00-LIST-SCOPE)** KHÔNG bị fix này phá — clamp CHỈ đụng `limit_page_length`, **KHÔNG** đụng `filters`/`or_filters`/`apply_vendor_scope`/`permission_query_conditions`/`compose_reserved_into`.
6. **KHÔNG đổi field-select** (no-leak parity GIỮ — `test_list_assets_no_qr_token` vẫn xanh). **Schema-delta: KHÔNG.** `CAP_SET_VERSION` GIỮ NGUYÊN.

> **EXCLUSION — `list_assets_depreciation` KHÔNG nằm trong 11 endpoint trên.** Endpoint này dùng path đếm/cắt-trang RIÊNG (`pg_size`, dict pagination `{page, page_size, total}` inline — `api/imm00.py:2788`) phục vụ Asset Finance Hub; **drill test khấu hao cố ý gọi `page_size=200`** để gom toàn tập theo trang (de-dup INV-DEP-5 — `test_imm00.py:1485,1516`). Clamp depreciation về 100 sẽ **phá vòng drill** (`page * 200 >= total` under-fetch). Round này KHÔNG clamp depreciation; nếu muốn cap depreciation về sau → phải đồng thời sửa drill-loop test sang `page_size <= 100` → **[ROADMAP]** riêng, ngoài scope BR-00-39.

**Response shape (list):**

```json
{
  "success": true,
  "data": {
    "items": [ ],
    "page": 1,
    "page_size": 20,
    "total": 137,
    "total_pages": 7
  }
}
```

## I.6. Filter Convention

```json
{ "lifecycle_status": "Active" }
{ "next_pm_date": ["<=", "2026-05-01"] }
{ "risk_class": ["in", ["High", "Critical"]] }
{ "asset_name": ["like", "%MRI%"] }
```

## I.7. Rate Limiting

| Nhóm endpoint | Giới hạn | Cơ chế thực thi |
|---|---|---|
| GET (list / detail) | 300 req/phút/user | *(policy mục tiêu — chưa enforce ở code; aspirational, KHÔNG decorator)* |
| POST / PUT (mutation) | 60 req/phút/user | *(policy mục tiêu — chưa enforce ở code)* |
| Scheduler trigger (admin) | 5 req/phút/user | *(policy mục tiêu — chưa enforce ở code)* |
| **Auth (login / register / status probe)** | **5 req/60s/IP** (`register_user`), kép per-(IP,email/usr) các probe | **ENFORCED** — `@rate_limit(...)` `api/auth.py:67,176,205` |
| **QR deep-link resolve** (`resolve_qr_token`, `get_asset_scan_info`) | **`AC_QR_RESOLVE_RATE_LIMIT` = 30 req/60s/IP, MỖI endpoint riêng bucket** | **ENFORCED (Vòng 12 B)** — `@rate_limit(limit=30, seconds=60, ip_based=True)` (precedent `api/auth.py:67`). Xem §I.7a. |
| **QR rotate** (`regenerate_asset_qr_token`) | **`AC_QR_REGEN_RATE_LIMIT` = 10 req/60s/IP, bucket RIÊNG** | **ENFORCED (Vòng 27 B / BR-00-38)** — GHI bảo mật write-amplify; ngưỡng THẤP hơn resolve. Xem §I.7b. |
| **In nhãn PDF** (`print_asset_labels_pdf`) | **`AC_LABEL_PDF_RATE_LIMIT` = 20 req/60s/IP, bucket RIÊNG** | **ENFORCED (ADR-LABEL-PDF §D6)** — render wkhtmltopdf nặng CPU. |
| **Mark in nhãn** (`mark_label_printed`) | **`AC_LABEL_MARK_RATE_LIMIT` = 10 req/60s/IP, bucket RIÊNG** | **ENFORCED (Vòng 14 / BR-00-45)** — GHI write-audit-amplification (2×N ALE+audit/call); ngưỡng THẤP (≤ rotate). Xem §I.7c. |
| **Đọc nhãn batch** (`get_asset_label_data_batch`) | **`AC_LABEL_BATCH_RATE_LIMIT` = 20 req/60s/IP, bucket RIÊNG** | **ENFORCED (Vòng 14 / BR-00-46)** — đọc N-asset/call; read-only ngưỡng CAO hơn mark (= pdf). Xem §I.7c. |
| **Đọc nhãn single** (`get_asset_label_data`) | **`AC_LABEL_DATA_RATE_LIMIT` = 20 req/60s/IP, bucket RIÊNG** | **ENFORCED (Vòng 36 / BR-00-51)** — read-mostly preview 1 asset NHƯNG CÓ mint side-effect (`ensure_asset_qr_token` emit `qr_generated` cho asset token-less) → hammer = write-amplification → vẫn throttle; song song batch/pdf=20. Xem §I.7c. |

Vượt hạn → HTTP 429. **Toàn bộ họ endpoint nhãn QR NAY throttled — KHÔNG còn endpoint nào miễn (Vòng 36 đóng lỗ cuối).**

### I.7a. QR deep-link resolve — rate-limit chống brute-force token + DoS (Vòng 12 B — **NEW**)

**Bối cảnh (5 câu hỏi domain):** WHO HTM stage = *Cross-cutting/Foundation* (IMM-00 registry). NĐ98: hồ sơ thiết bị KHÔNG public → 2 endpoint này đã AUTH-REQUIRED + `asset.read`. Stakeholder: kỹ thuật viên / điều dưỡng quét QR tại hiện trường (camera điện thoại). Lifecycle event: **KHÔNG** (read-only, no-audit — ADR-001 D4). Hậu quả nếu sai: kẻ tấn công có session hợp lệ (hoặc DoS không-auth chạm tới gate) có thể dội request dò token / làm nghẽn endpoint → cần lớp phòng-thủ-chiều-sâu.

**Vì sao 2 endpoint NÀY (và CHỈ 2):** đây là **2 entry-point DUY NHẤT mà camera điện thoại hit** qua deep-link `/a/<token>` (route FE `QrResolveView` → `resolve_qr_token`) và `/scan/:token` (route FE `AssetScanInfo` → `get_asset_scan_info`). Chúng nhận `token` từ URL công khai (in trên nhãn dán), là bề mặt brute-force/DoS tự nhiên.

**Ngưỡng (CHỐT BA): `limit=30, seconds=60, ip_based=True`** — đặt hằng `AC_QR_RESOLVE_RATE_LIMIT = 30` (đầu `api/imm00.py`, KHÔNG literal rải rác). Lý do chốt:

| Yếu tố | Phân tích | Kết luận ngưỡng |
|---|---|---|
| Entropy token | `secrets.token_urlsafe(16)` = **128-bit** (`services/imm00.py:111`) → namespace ~3.4e38; brute-force vô vọng kể cả không rate-limit | Rate-limit là **defense-in-depth + chống DoS**, KHÔNG phải hàng rào duy nhất → ngưỡng có thể RỘNG, không cần siết như login |
| Tốc độ quét người thật | 1 người quét nhãn vật lý ≤ ~1 lần/giây bền vững; quét cả rack (10–20 thiết bị/phút) là peak hiếm | 30/60s cho **~2× headroom** trên peak quét-rack → happy-path KHÔNG vỡ |
| So login (`auth.py:67` = 5/60s) | Login = bề mặt đoán-credential → siết chặt. QR resolve ≠ credential-guess (token 128-bit) | Lỏng hơn login (30 > 5) nhưng chặt hơn policy GET chung (30 < 300) — hợp lý cho deep-link bán-công-khai |
| Per-endpoint bucket | `rate_limit` cache key gồm `frappe.form_dict.cmd` → 2 endpoint **KHÔNG chung bucket**; mỗi scan gọi 1 resolve + 1 scan_info nhưng đếm riêng | 30 mỗi endpoint = đủ cho 30 scan trọn vẹn/phút/IP |

**`ip_based=True`, KHÔNG `key=`:** đồng nhất precedent `register_user` (`auth.py:67`). Caveat shared-NAT (wifi bệnh viện → nhiều máy chung 1 IP egress): 30/60s/IP/endpoint đủ rộng để vài người quét đồng thời sau 1 NAT KHÔNG đụng trần ở mức dùng bình thường; nếu site có mật độ quét cao bất thường → nâng `AC_QR_RESOLVE_RATE_LIMIT` (1 chỗ). KHÔNG dùng `key="token"` (token thay đổi mỗi request → bucket vô dụng cho brute-force).

**Thứ tự gate (CHỐT — BẮT BUỘC):** `@rate_limit` là **decorator bọc NGOÀI thân hàm** → frappe tăng counter rồi `frappe.throw(RateLimitExceededError)` **TRƯỚC** khi thân hàm chạy → **TRƯỚC `rbac.require("asset.read")`** và trước mọi resolve/IDOR. Thứ tự đầy đủ:

```
@frappe.whitelist()                          # 1. dispatch
@rate_limit(limit=30, seconds=60, ip_based=True)  # 2. RATE-LIMIT (vượt → 429, dừng tại đây)
def resolve_qr_token(token=""):
    rbac.require("asset.read")               # 3. RBAC (403)
    ...resolve → 404 → IDOR (403) → 200      # 4. thân hàm như cũ
```

Decorator ĐẶT GIỮA `@frappe.whitelist()` (trên) và `@rate_limit` (dưới) — `@rate_limit` phải nằm **sát def** để bọc trong cùng (giống `auth.py:66-68`).

**No-leak parity (CHỐT):** 429 (`frappe.RateLimitExceededError` ⊂ `frappe.TooManyRequestsError`, HTTP **429**) trả body generic của frappe ("Too Many Requests / too many requests…"), **KHÔNG** chứa payload asset, `name`, `asset_code`, lý do nội bộ, hay phân biệt token-tồn-tại — **đồng nhất** triết lý leak-safe của 404/403 hiện có. Vì rate-limit chặn TRƯỚC thân hàm, không một byte dữ liệu asset nào được build.

**Đếm MỌI call (kể cả 404/403):** counter tăng TRƯỚC thân hàm → request dò token-sai (kết cục 404) VẪN bị tính → brute-forcer dội 404 vẫn bị bóp ở call thứ 31. Đây là hành vi mong muốn (chống enumeration).

**Bối cảnh không-HTTP (test/CLI) — bypass có chủ đích:** `rate_limit` wrapper có `if not frappe.request: return fn(...)` → khi gọi hàm TRỰC TIẾP (unit test cũ `TestResolveQrToken`/`TestAssetScanInfo` không set `frappe.local.request`) limiter **bị bỏ qua** → các test happy/404/403/IDOR cũ **KHÔNG REGRESS**. Để test 429 thật, class test MỚI phải mô phỏng HTTP context: set `frappe.local.request` (truthy, giống `_http_call` của `TestQrWhitelistHttpLayer`), `frappe.local.request_ip`, và `frappe.form_dict.cmd` (cache key cần `cmd`); dội >30 call → assert `frappe.RateLimitExceededError` (429). Xem 07 §rate-limit.

**Endpoint nhãn còn unthrottled — KHÔNG còn (Vòng 36 đóng lỗ cuối):** sau Self-Correction 3 bậc (BR-00-38 rotate, BR-00-45/46 mark/batch, **BR-00-51 single**), danh sách miễn rate-limit đã **CẠN**. `get_asset_label_data` (single-asset preview) — endpoint nhãn DUY NHẤT còn hở trước Vòng 36 — NAY mang `@rate_limit(AC_LABEL_DATA_RATE_LIMIT=20)` bucket RIÊNG. Lý do throttle dù read-mostly: token-less asset → `ensure_asset_qr_token` (idempotent) emit `qr_generated` (ALE+audit) ⇒ hammer = **write-amplification mint-token**. Xem §I.7c (BR-00-51).

> **⚠️ Self-Correction Vòng 27 B (§I.7b — BR-00-38): `regenerate_asset_qr_token` ĐÃ TÁCH KHỎI** danh sách miễn rate-limit. Rotate là GHI **bảo mật** (vô hiệu hoá nhãn QR đã in + ghi audit chain), hiếm-tần-suất, có thể bị spam-rotate (DoS nhãn hợp lệ + write-amplification audit). → mang `@rate_limit(limit=AC_QR_REGEN_RATE_LIMIT, seconds=60, ip_based=True)` với hằng RIÊNG `AC_QR_REGEN_RATE_LIMIT = 10` (THẤP hơn resolve=30) + bucket RIÊNG (cmd). 429 NGOÀI/TRƯỚC `rbac.require` → 0 side-effect, no-leak. Chi tiết §III.1 `regenerate_asset_qr_token` + [02 BR-00-38](./02_Analysis_Design.md). FE cặp: FR-00-87/88 (httpStatusToCode 429→RATE_LIMITED + message VI).

> **⚠️ Self-Correction Vòng 14 (§I.7c — BR-00-45/46): `mark_label_printed` + `get_asset_label_data_batch` ĐÃ TÁCH KHỎI** danh sách miễn. `mark_label_printed` = GHI **write-audit-amplification** (2×N record ALE `label_printed`+audit/call → bơm audit-chain NĐ98 + tải DB); `get_asset_label_data_batch` = ĐỌC N-asset/call (DoS đọc). → mang `@rate_limit` hằng RIÊNG (`AC_LABEL_MARK_RATE_LIMIT = 10` ≤ regen; `AC_LABEL_BATCH_RATE_LIMIT = 20` = pdf) + bucket RIÊNG (cmd). 429 NGOÀI/TRƯỚC `rbac.require` → mark: 0 ALE+0 audit / batch: 0 byte payload, no-leak. Chi tiết §I.7c + §III.1 (`mark_label_printed` / `get_asset_label_data_batch`) + [02 BR-00-45/46](./02_Analysis_Design.md). FE 429→RATE_LIMITED+VI ĐÃ CÓ (FR-00-87/88).

> **⚠️ Self-Correction Vòng 36 (§I.7c — BR-00-51 / FR-00-102): `get_asset_label_data` (single) ĐÃ TÁCH KHỎI** danh sách miễn — **đóng lỗ hổng CUỐI** họ endpoint nhãn QR (single là endpoint nhãn DUY NHẤT còn chưa-throttle sau Vòng 14). Tưởng read-mostly (1 record/call, low-amplify) nhưng **CÓ mint side-effect**: token-less asset → `ensure_asset_qr_token` (idempotent) GHI token + emit `qr_generated` (ALE + audit) ⇒ hammer KHÔNG giới hạn = **write-amplification mint-token** (bơm audit-chain NĐ98). → mang `@rate_limit(AC_LABEL_DATA_RATE_LIMIT = 20)` (song song batch/pdf=20 — read-mostly preview cùng tần-suất FE màn in nhãn) + bucket RIÊNG (cmd → counter TÁCH BIỆT batch/mark/pdf/resolve/regen; 1 endpoint vượt ngưỡng KHÔNG khoá endpoint khác). 429 NGOÀI/TRƯỚC `rbac.require("asset.print")` → 0 byte payload build + 0 mint side-effect (`ensure_asset_qr_token` KHÔNG chạy → 0 `qr_generated`), no-leak. Hằng RIÊNG (KHÔNG tái dùng định-danh khác kể cả khi trùng giá-trị batch/pdf — tách ngữ-nghĩa). Chi tiết §I.7c + §III.1 (`get_asset_label_data`) + [02 BR-00-51](./02_Analysis_Design.md). FE 429→RATE_LIMITED+VI ĐÃ CÓ (FR-00-87/88).

> **Rate-limit (req/phút/IP) ≠ batch-size cap (per-request payload) — 2 lớp phòng thủ TRỰC GIAO.** 2 endpoint nhãn batch (`get_asset_label_data_batch`, `mark_label_printed`) NAY mang `@rate_limit` (Vòng 14) ĐỒNG THỜI bị **cap kích thước batch** `_MAX_LABEL_BATCH=200` (vòng 22 / BR-00-33): rate-limit chặn flood NHIỀU request/phút; cap chặn payload-DoS 1 request đơn lẻ (N name → batch-read/IDOR + ghi 2 record/asset). 2 lớp trực giao, KHÔNG thay thế nhau. Chi tiết spec từng endpoint dưới.

**KHÔNG đổi schema/cap/DocType/patch:** các vòng rate-limit thuần thêm decorator + hằng + test. `CAP_SET_VERSION` GIỮ `v97.c30c69b8974d` (sau D6). FE KHÔNG đổi (BE-only) — xử lý 429 gracefully đã nằm trong contract notification chung (xem 06).

### I.7c. In nhãn — rate-limit `mark_label_printed` (write-audit-amplification) + `get_asset_label_data_batch` (read) + `get_asset_label_data` (single, mint side-effect) (Vòng 14 / BR-00-45 / BR-00-46 + Vòng 36 / BR-00-51 — **NEW**, Self-Correction)

> **Đề mục Vòng 14 (hardening/security — mirror rotate §I.7b).** Đóng bất đối xứng: PDF (`print_asset_labels_pdf`) đã throttle (§D6) nhưng `mark_label_printed` (GHI 2×N record/call) + `get_asset_label_data_batch` (đọc N-asset/call) còn hở (BR-00-29 mục 6 miễn nhóm in-nhãn). 2 endpoint nay mang `@rate_limit` hằng+bucket RIÊNG.

> **Đề mục Vòng 36 (BR-00-51 — đóng lỗ CUỐI họ nhãn).** `get_asset_label_data` (single) — endpoint nhãn DUY NHẤT còn chưa-throttle sau Vòng 14 — NAY mang `@rate_limit(AC_LABEL_DATA_RATE_LIMIT = 20, seconds=60, ip_based=True)` đặt GIỮA `@frappe.whitelist()` và `def` (bọc NGOÀI thân → 429 TRƯỚC `rbac.require("asset.print")`). Hằng RIÊNG `AC_LABEL_DATA_RATE_LIMIT = 20` (song song batch/pdf — read-mostly preview; KHÔNG tái dùng định-danh hằng khác kể cả khi trùng giá-trị — tách ngữ-nghĩa). Bucket RIÊNG (cache key gồm `cmd` → counter single TÁCH BIỆT batch/mark/pdf/resolve/regen; 1 endpoint vượt ngưỡng KHÔNG khoá endpoint khác). Lý do throttle dù read-mostly: token-less asset → `ensure_asset_qr_token` (idempotent) emit `qr_generated` (ALE+audit) ⇒ hammer = write-amplification mint-token. Vượt ngưỡng → **429** NGOÀI/TRƯỚC thân → **0 byte payload build + 0 mint side-effect**, no-leak (KHÔNG name/asset_code/serial). Thứ tự gate dưới ngưỡng GIỮ NGUYÊN: 429(rate) → 403(`rbac.require asset.print`) → 404(asset rỗng/∄ leak-safe) → 403(IDOR `assert_vendor_can_access`) → 200(`_ok build_asset_label_data`). Test: [07 §rate-limit single](./07_Testing_QA.md) (`TestLabelDataRateLimit` — RED-first). [02 BR-00-51](./02_Analysis_Design.md).

```python
@frappe.whitelist(methods=["POST"])
@rate_limit(limit=AC_LABEL_MARK_RATE_LIMIT, seconds=60, ip_based=True)   # 429 TRƯỚC rbac.require
def mark_label_printed(assets=None): ...

@frappe.whitelist()
@rate_limit(limit=AC_LABEL_BATCH_RATE_LIMIT, seconds=60, ip_based=True)  # 429 TRƯỚC rbac.require
def get_asset_label_data_batch(assets=None): ...
```

| Quy tắc | Giá trị / lý do |
|---|---|
| Hằng `AC_LABEL_MARK_RATE_LIMIT = 10` | mark = GHI write-amplify (2×N ALE+audit/call) → ngưỡng THẤP, **≤ `AC_QR_REGEN_RATE_LIMIT=10`** (cùng họ rotate-asymmetry-logic). |
| Hằng `AC_LABEL_BATCH_RATE_LIMIT = 20` | batch = read-only (0 side-effect) → CAO hơn mark, song song `AC_LABEL_PDF_RATE_LIMIT=20` (FE preview-rồi-mark). |
| Định nghĩa DUY NHẤT 1 nơi (khối hằng đầu `api/imm00.py`, cạnh `AC_LABEL_PDF_RATE_LIMIT`) | KHÔNG literal `10`/`20` rải rác; KHÔNG tái dùng resolve/regen/pdf (TÁCH BIỆT ngữ-nghĩa). Comment nêu lý do (write-audit-amplification vs read). |
| Bucket RIÊNG (cache key gồm `cmd`) | counter mark / batch TÁCH BIỆT resolve(30)/scan(30)/regen(10)/pdf(20). |
| 429 NGOÀI/TRƯỚC `rbac.require("asset.print")` | mark vượt → **0 ALE `label_printed` + 0 IMM Audit Trail**; batch vượt → 0 byte payload build. no-leak body generic (parity 404/403). |
| Happy-path ≤ngưỡng | mark vẫn ghi 2×N record + `_ok`; batch vẫn `_ok` payload N-item. |
| Test/CLI bypass | `if not frappe.request: return fn` → suite cũ GREEN; test 429 MỚI mô phỏng HTTP-ctx (mirror §I.7a). |

**No-leak parity (CHỐT):** 429 (`frappe.RateLimitExceededError`, HTTP **429**) body generic — KHÔNG `name`/`asset_code`/số-record/lý-do, vì chặn TRƯỚC thân hàm (0 byte build/đọc). Xem 07 §III.6.i-LABELRL.

---

# Phần II — Permission Matrix

| Endpoint nhóm | System Admin | Dept Head | Ops Manager | Workshop Lead | Technician | QA Officer | Doc Officer | Storekeeper |
|---|---|---|---|---|---|---|---|---|
| list/get assets | ✓ | ✓ | ✓ | ✓ | ✓ (scoped) | ✓ | ✓ | — |
| resolve_qr_token (`asset.read`) ‡ | ✓ | ✓ | ✓ | ✓ | ✓ (scoped IDOR) | ✓ | ✓ | — |
| get_asset_scan_info (`asset.read`) — A6 ‡ | ✓ | ✓ | ✓ | ✓ | ✓ (scoped IDOR) | ✓ | ✓ | — |
| get_asset_label_data[_batch] (`asset.write`†) | ✓ | ✓ | ✓ | ✓ | ✓ (scoped IDOR, nếu có write) | ✓ | — | — |
| mark_label_printed (`asset.write`†) | ✓ | ✓ | ✓ | ✓ | ✓ (scoped IDOR, nếu có write) | ✓ | — | — |
| regenerate_asset_qr_token (`asset.write`†) — B-2 | ✓ | ✓ | ✓ | ✓ | ✓ (scoped IDOR, nếu có write) | ✓ | — | — |
| create/update asset | ✓ | ✓ | ✓ | — | — | — | — | — |
| transition_status (`asset.write`§) | ✓ | ✓ | ✓ | — | — | ✓ | — | — |
| list/get supplier | ✓ | ✓ | ✓ | — | — | — | — | ✓ |
| create/update supplier | ✓ | — | ✓ | — | — | — | — | — |
| list_locations / list_departments | All | All | All | All | All | All | All | All |
| create location/dept/category | ✓ | ✓ (dept) | — | ✓ (cat) | — | — | — | — |
| list/get device_model | All | All | All | All | All | All | All | — |
| create/update device_model | ✓ | — | — | ✓ | — | — | — | — |
| list/get SLA | All | All | All | All | All | All | All | All |
| list_audit_trail / get_audit_entry | ✓ | — | — | — | — | ✓ | ✓ | — |
| verify_chain | ✓ | — | — | — | — | ✓ | — | — |
| list/get CAPA | ✓ | ✓ | ✓ | — | — | ✓ | — | — |
| open_capa | ✓ | — | ✓ | ✓ | — | ✓ | — | — |
| close_capa_record | ✓ | — | — | — | — | ✓ | — | — |
| list/get lifecycle_events | All | All | All | All | All | All | All | All |
| list/get/create/submit incident | All | All | All | All | All | All | — | All |
| scheduler triggers | ✓ | — | — | — | — | — | — | — |
| inventory endpoints | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | ✓ |

> **† [EXECUTED Vòng 3 — ADR-IMM00-QR-SCAN-ACTION D6] Nhóm IN nhãn (`get_asset_label_data`, `get_asset_label_data_batch`, `mark_label_printed`) — gate `asset.print`; ROTATE (`regenerate_asset_qr_token`) — gate `asset.qr.rotate`:** D6 TÁCH cap riêng thay `asset.write` (vốn chỉ Super Admin có → KTV/QL vật tư KHÔNG in/rotate được). **`asset.print`→(AC Asset,"print")**: DocPerm print=1 sẵn cho MỌI role vận hành (Repair/Calibration/Corrective/Inventory… User) → in nhãn được NGAY; user KHÔNG print (Guest) → **403**. **`asset.qr.rotate`→(AC Asset,"write")**: rotate = GHI (đổi định danh phụ + vô hiệu nhãn cũ) ⇒ chỉ Super Admin/role được cấp write; user chỉ print → rotate **403**. **CAP_SET_VERSION đổi** `v95.3388ee5629c1`→`v97.c30c69b8974d` (thêm 2 cap; FE auto-invalidate). `asset.read` GIỮ NGUYÊN cho 3 endpoint read-only: `resolve_qr_token`, `get_asset_scan_info`, `get_asset`. *(Lịch sử: A2 gốc dự kiến `asset.print_label`; vòng B đổi tạm sang `asset.write`; D6 chốt `asset.print`/`asset.qr.rotate` đúng tên ADR.)*

> **‡ QR deep-link resolve (`resolve_qr_token`, `get_asset_scan_info`) — rate-limited (Vòng 12 B):** ngoài RBAC/IDOR, 2 endpoint NÀY có `@rate_limit(AC_QR_RESOLVE_RATE_LIMIT=30/60s/IP/endpoint)` chống brute-force token + DoS (entry-point camera điện thoại `/a/<token>` & `/scan/:token`). 429 chạy TRƯỚC RBAC, no-leak parity với 404/403. **`regenerate_asset_qr_token` (rotate) CÓ rate-limit RIÊNG** `@rate_limit(AC_QR_REGEN_RATE_LIMIT=10/60s/IP)`, bucket RIÊNG (Vòng 27 B / BR-00-38 — rotate = GHI bảo mật, ngưỡng THẤP hơn resolve). **`mark_label_printed` (`AC_LABEL_MARK_RATE_LIMIT=10`) + `get_asset_label_data_batch` (`AC_LABEL_BATCH_RATE_LIMIT=20`) + `print_asset_labels_pdf` (`AC_LABEL_PDF_RATE_LIMIT=20`) + `get_asset_label_data` (`AC_LABEL_DATA_RATE_LIMIT=20`) CŨNG rate-limited** (Vòng 14 / BR-00-45/46 + §D6 + **Vòng 36 / BR-00-51** — bucket RIÊNG mỗi endpoint). **TOÀN BỘ họ endpoint nhãn QR NAY throttled — KHÔNG còn endpoint nào miễn** (Vòng 36 đóng lỗ cuối: single CÓ mint side-effect `ensure_asset_qr_token` ⇒ write-amplification khi hammer). Chi tiết §I.7a/§I.7b/§I.7c.

> **§ `transition_status` (`asset.write`) — CR-WF-00-TRANSITION-AUTHZ (Vòng 39, BR-00-57):** trước Vòng 39 endpoint đổi `lifecycle_status` **KHÔNG** có gate server-side (missing-authorization write, Trục A) — mọi user đăng nhập (kể cả base `AssetCore System User`) POST thẳng là đổi được trạng thái vòng đời. Nay SIẾT 3 lớp **MIRROR `get_asset`**: `rbac.require("asset.write")` (cap-403 status-line, TRƯỚC `exists` → no existence-oracle) + `assert_vendor_can_access` (IDOR-403 in-handler). FE `AssetDetailView.vue:480` ĐÃ gate nút chuyển trạng thái bằng `can('asset.write')` từ trước → đây là **defense-in-depth** (BE bắt kịp FE, đóng đường bypass gọi API trực tiếp). `asset.write`→(AC Asset,"write"): DocPerm write=1 hiện chỉ Super Admin (persona vận hành KTV/QL vật tư KHÔNG write=1 — cấp thêm qua DocPerm /app, KHÔNG deploy code). **SERVICE `transition_asset_status` GIỮ perm-free** (WO-complete IMM-08/09/11/12 gọi thẳng service → 0 blast-radius). Cột ✓ ở bảng phản ánh persona DỰ KIẾN được cấp write; enforcement THẬT = `frappe.has_permission("AC Asset","write")` (capability-based). Xem `04 §II.1.7-AUTHZ` + `ADR-IMM00-TRANSITION-AUTHZ`.

---

# Phần III — Endpoints

Base Python path: `assetcore.api.imm00.<function>`  
URL pattern: `POST|GET /api/method/assetcore.api.imm00.<function>`

---

## III.1. AC Asset (12 endpoints code + QR)

> **Thực tế từ code:** `api/imm00.py` cung cấp 11 endpoints CRUD/transition cho AC Asset (không phải 8). **QR (ADR-001):** `resolve_qr_token` (A2 — đã có); `get_asset_scan_info` (A6 — màn info mobile-first khi quét, spec NEW dưới đây); `get_asset_label_data`, `get_asset_label_data_batch`, `mark_label_printed` (A3 — spec chốt); `regenerate_asset_qr_token` (**B-2 — rotate token, spec NEW dưới đây**). Xem danh sách đầy đủ phía dưới.

### `list_assets` — Liệt kê Asset

| Thuộc tính | Giá trị |
|---|---|
| Method | GET |
| Path | `assetcore.api.imm00.list_assets` |
| Permission | IMM Department Head / Operations Manager / Technician (scoped) / Admin |

**Request params:**

```json
{
  "filters": {
    "lifecycle_status": "Active",
    "risk_class": ["in", ["High", "Critical"]],
    "department": "AC-DEPT-0001"
  },
  "page": 1,
  "page_size": 20,
  "sort": "next_pm_date asc"
}
```

**Response 200:**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "name": "AC-ASSET-2026-00001",
        "asset_name": "MRI Siemens Magnetom Aera 1.5T",
        "asset_code": "MRI-001",
        "lifecycle_status": "Active",
        "risk_class": "High",
        "next_pm_date": "2026-04-30",
        "department": "AC-DEPT-0001"
      }
    ],
    "page": 1, "page_size": 20, "total": 1, "total_pages": 1
  }
}
```

**Query params bổ sung:**

| Param | Kiểu | Mô tả |
|---|---|---|
| `lifecycle_status` | str | Lọc theo trạng thái vòng đời |
| `department` / `location` / `asset_category` | str | Lọc theo Link field |
| `gmdn_code` | str | **Lọc thiết bị theo mã GMDN** (kế thừa từ Asset Category). Dùng cho recall/FSCA, KPI per-GMDN |
| `byt_status` | str | **Drill số ĐKLH BYT (BR-00-17 — SoT `byt_expiry_filter`).** `'expiring'` → `byt_reg_expiry ∈ [today, today+30]`; `'expired'` → `byt_reg_expiry < today`. CẢ HAI loại bản ghi `byt_reg_expiry` rỗng/NULL. Khi set → **conjoin (AND)** với mọi filter hiện có (lifecycle_status/department/…) KHÔNG clobber; `apply_vendor_scope` áp SAU. Giá trị khác → **no-op** (bỏ qua, KHÔNG throw). |
| `search` | str | Tìm theo `asset_name`, `asset_code`, `manufacturer_sn`, **`gmdn_code`** (LIKE substring). **Metachar `%`/`_`/`\` user gõ = KÝ TỰ LITERAL** (escape qua SSoT `escape_like_term` — `search='_'`/`'%'` KHÔNG over-match toàn bảng, `search='\'` KHÔNG throw) — xem ADR-IMM00-SEARCH-ESCAPE. |

> **Note (2026-05-19):** Tham số lọc theo trạng thái sử dụng GMDN (cũ) đã bị loại bỏ cùng field tương ứng. Trục lọc/quản lý thiết bị nay là `gmdn_code`. Tham chiếu: [docs/res/analysis/gmdn-asset-category-analysis.md](../res/analysis/gmdn-asset-category-analysis.md) §6.

> **INVARIANT count==drill (BR-00-17 — Vòng 31):** `list_assets(byt_status='expiring')` `pagination.total` == KPI `get_overview().assets.byt_expiring_30d`; `list_assets(byt_status='expired')` `pagination.total` == `get_overview().assets.byt_expired`, byte-for-byte trên CÙNG dataset + CÙNG vendor scope (cả 2 read-path gọi SoT `byt_expiry_filter`). FE tile NĐ98 click → `/assets?byt_status=expiring\|expired`; header "Tổng N" của list == giá trị tile vừa click. KHÔNG inline literal window — xem [04 Backend §III.1a](../imm-00/04_Backend_Design.md).

> **Reserved test-prefix exclusion (BR-00-35 — Vòng 25 B, áp NGẦM mọi request):** `list_assets` **luôn** loại asset rác test/security-audit qua SSoT `reserved_test_prefix_sql()` — KHÔNG trả row nào có `asset_name` bắt đầu `_` (`_Test*`/`_Probe*`) HOẶC `name` bắt đầu `SI-` (security-injection probe). Không có param điều khiển (mặc định bật, áp cho TẤT CẢ caller). Escape-safe (`ESCAPE '\\'` tường minh → `_` đầu chuỗi là LITERAL). 3 nguồn count (`pagination.total` non-search, search-count, `get_overview().assets.total`) áp **CÙNG** predicate ⟹ **INVARIANT `total == len(items)`** khi cùng filter (parity IMM-06/12). 0 false-positive: asset hợp lệ (`Máy thở`, `TS-2025-USG-001`, `AC-ASSET-…`, `Model_X` có `_` ở GIỮA) hiện đầy đủ. FE list/count **tự hưởng lợi, KHÔNG đổi component**. Xem [04 Backend §II.1.13-TESTPREFIX](../imm-00/04_Backend_Design.md). (Helper đã ship dùng bộ 3 tên `reserved_prefix_sql`/`reserved_prefix_filter`/`reserved_asset_names` — `reserved_test_prefix_sql` ở đây là tham chiếu đồng nghĩa, KHÔNG rename code.)

> **Compose AND với vendor-scope (BR-00-35 mục 6 / FR-00-84 — Self-Correction Vòng 26 B, RC-LIST-VENDORCLOBBER):** reserved-exclusion áp ORM filter trên field **`name`** (`{"name": ["not in", reserved]}` qua `reserved_prefix_filter()`). `apply_vendor_scope` (AUTH-01) cho **Vendor Engineer** cũng áp predicate trên field `name` (`{"name": ["in", assigned]}`). Hai predicate cùng field ⟹ **KHÔNG** merge bằng `dict.update` (sẽ ghi đè key `name` → mất vendor-scope = HIGH regression). `list_assets` compose AND qua **filter-list form** (hai dòng `name` riêng biệt, ANDed) → predicate hiệu dụng `name ∈ (assigned ∖ reserved)`: Vendor Engineer chỉ thấy asset **được giao việc** VÀ đã loại reserved-prefix; scope RỖNG (`["__none__"]`) → 0 row (KHÔNG fallback toàn bộ). INVARIANT `total == len(items)` giữ ở cả 3 nguồn count cho MỌI persona (Administrator/bypass + Vendor Engineer). Helper SSoT KHÔNG đổi tên. 2 endpoint `list_assets_depreciation`/`get_depreciation_stats` KHÔNG gọi `apply_vendor_scope` → giữ `filters.update(reserved_prefix_filter())` an toàn (no-regress). Xem [04 §II.1.13-TESTPREFIX RC-LIST-VENDORCLOBBER](../imm-00/04_Backend_Design.md) + [02 FR-00-84](../imm-00/02_Analysis_Design.md).

> **Search LIKE-metachar escape (ADR-IMM00-SEARCH-ESCAPE — Vòng 13, áp NGẦM khi có `search`):** ký tự `%`/`_`/`\` user gõ trong `search` là **KÝ TỰ LITERAL**, KHÔNG phải wildcard SQL. `list_assets` escape term qua SSoT `escape_like_term(search)` (`%`→`\%`, `_`→`\_`; **KHÔNG** đụng `\` vì Frappe DatabaseQuery TỰ nhân đôi backslash — `db_query.py:938-940`) TRƯỚC khi dựng `or_filters` 4 cột. Hệ quả: `search='_'`/`'%'` **KHÔNG over-match toàn bảng** (RED cũ: `_`/`%` = wildcard → match-all); `search='\'` (1 backslash) **KHÔNG throw/500**, khớp record có backslash literal; `search='%%%%%%%%%%'` (10×`%`) trả `total` hữu hạn, KHÔNG match-all (đóng bề mặt LIKE-backtracking DoS). Escape áp **CÙNG `or_filters`** cho cả count (`count_with_or`) lẫn items (`get_list`) ⟹ INVARIANT `total==len(items)` GIỮ NGUYÊN, MỌI persona. SQLi vẫn an toàn (parametrized — `test_search_param_is_sqli_safe` GREEN). Substring không-metachar (`vent`/`AC-ASSET`/`35304`) match đúng như cũ (`test_search_by_gmdn_code_substring` GREEN). Xem [04 §II.1.13-SEARCHESCAPE](../imm-00/04_Backend_Design.md) + [ADR-IMM00-SEARCH-ESCAPE](./ADR-IMM00-SEARCH-ESCAPE.md).

---

### `get_asset` — Chi tiết Asset

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.get_asset` |
| Capability | `asset.read` (read-only — xem 04 §III.1c-1; KHÔNG đổi) |

**Request:** `?name=AC-ASSET-2026-00001`

**Response 200** — đầy đủ HTM fields (asset_name, udi_code, gmdn_code, byt_reg_no, byt_reg_expiry, lifecycle_status, risk_classification, next_pm_date, next_calibration_date, commissioning_date, …) + display-name enrich (`category_name`, `department_name`, `location_name`, `supplier_name`, `device_model_name`, `responsible_technician_name`) + 2 cờ overdue server-flag (`pm_overdue`, `calibration_overdue`) + **2 field BẢO HÀNH server-flag** (`warranty_expired`, `warranty_expiry_date`) — CR-38, xem dưới + **`allowed_transitions: string[]`** (Vòng 41 — CR-WF-00-LIFECYCLE-SURFACE, xem dưới).

> **Field delta (CR-38 — parity BẢO HÀNH detail ↔ scan-info, 2026-07-19):** payload thêm ĐÚNG 2 field ĐỐI XỨNG `get_asset_scan_info`: **`warranty_expired: bool`** (SERVER-FLAG derive qua CHÍNH `services.imm00._is_warranty_expired` — `True` ⟺ `warranty_expiry_date` không rỗng ∧ `getdate(warranty_expiry_date) < getdate(nowdate())`; STRICT `<` theo NGÀY server, tz-safe; NULL/hôm-nay/tương-lai → `false`; **ĐỘC LẬP `lifecycle_status`** — bảo hành là sự kiện HỢP ĐỒNG, Out of Service/Decommissioned VẪN có thể hết bảo hành) + **`warranty_expiry_date: str\|None`** (`'YYYY-MM-DD'`/`null` qua CÙNG `_date_str_or_none` — chuẩn hoá field `AC Asset.warranty_expiry_date` mà `as_dict()` trả NGUYÊN `datetime.date` object, KHÔNG rò date thô ra JSON). **SSoT chống drift:** `get_asset().warranty_expired == build_asset_scan_info().warranty_expired` cho CÙNG 1 asset — KHÔNG re-implement so-ngày ở api layer. FE `AssetDetailView` render badge "Hết hạn"/"Còn hạn" TỪ cờ server, KHÔNG so ngày client. `warranty_expired` LUÔN emit (∈ `required`); `warranty_expiry_date` nullable (NGOÀI `required`). **KHÔNG whitelist/schema/cap/endpoint/enum/patch/`CAP_SET_VERSION` delta** — chỉ enrich return của hàm sẵn có (`api/imm00.py get_asset`). Mobile mirror: [`../mobile/openapi/assetcore-mobile.openapi.yaml`](../mobile/openapi/assetcore-mobile.openapi.yaml) (`AssetDetail.warranty_expired`/`warranty_expiry_date`) + [`../mobile/04-api-contract.md`](../mobile/04-api-contract.md). Parity scan-info: `AssetScanInfo` §04.

> **`allowed_transitions: string[]` (CHỐT Vòng 41 — CR-WF-00-LIFECYCLE-SURFACE / FR-00-109 / BR-00-58):** tập trạng-thái-đích **CTA-surfaceable của SPA** cho `lifecycle_status` hiện tại, **server-derive** qua `services.imm00.asset_allowed_transitions(status)` (mirror precedent `firmware_allowed_transitions` @get_firmware_cr). Quy tắc: `_VALID_ASSET_TRANSITIONS[status]` − **loại HẲN target `Decommissioned`** (thanh lý đi qua nút riêng "Hồ sơ giải nhiệm" IMM-14 closure — KHÔNG phải CTA chuyển-trạng-thái tự do; loại-hẳn-Decommissioned bao trùm cả `_LIFECYCLE_EXCEPTION_EDGES` lẫn 2 cạnh Thanh lý đã surface Desk) − terminal, **sorted ổn định**, rồi **LỌC theo capability caller**. **Acceptance:** (a) caller CÓ `asset.write` → subset đúng theo SSoT (verify BẰNG-NHAU từng status, bảng 8-status ở [04 §II.1.7-SURFACE](./04_Backend_Design.md)); (b) caller THIẾU `asset.write` (read-only DocPerm) → `allowed_transitions == []`; (c) status terminal `Decommissioned` → `[]`; (d) BẤT-VARIANT: **KHÔNG status nào** cho `allowed_transitions` chứa `'Decommissioned'`. FE `AssetDetailView.vue` dựng nút "Chuyển trạng thái:" **CHỈ từ** field này (bảng hardcode `TRANSITIONS` client-side BỊ XÓA hẳn); server `[]` → không render block CTA. **Không schema/cap-delta** (`asset.write` sẵn; `CAP_SET_VERSION` GIỮ; `allowed_transitions` là field dẫn-xuất response, KHÔNG lưu DB). Test: [07 §XII TC-00-WF-SURFACE](./07_Testing_QA.md).

> **No-raw-token (CHỐT Vòng 24 B — ADR-001 §D4.1 / BR-00-34, rule 9 mở rộng):** payload build qua `frappe.get_doc("AC Asset", name).as_dict()` PHẢI **STRIP** field `qr_token` (`data.pop("qr_token", None)` SAU `as_dict()`, TRƯỚC enrich/`_ok`) → response **KHÔNG BAO GIỜ** còn key `qr_token`. `qr_token` là **khóa tra cứu MỜ** (opaque), enumeration-safe (D1) — token thô KHÔNG rời BE qua đường ĐỌC asset. **Acceptance:** `assert 'qr_token' not in data`. **Mọi field khác GIỮ NGUYÊN** (FE `AssetDetailView` render đầy đủ — KHÔNG re-whitelist, chỉ pop 1 key). Deep-link/in nhãn KHÔNG qua `get_asset` — dùng `get_asset_label_data` (`qr_url` dựng server-side qua `_build_qr_url`) / `regenerate_asset_qr_token`. RBAC/IDOR/404 GIỮ NGUYÊN (`assert_vendor_can_access` 403 + 404 `AC-E001`). Parity đồng nhất: `get_asset_timeline` (đọc Asset Lifecycle Event — KHÔNG có `qr_token`), `get_asset_kpi` (build dict KPI tường minh — KHÔNG `as_dict()`), `resolve_qr_token`/`get_asset_scan_info`/`get_asset_label_data[_batch]` (đã whitelist tường minh). **Guard chống tái phát:** test Grep/AST khẳng định 0 endpoint trả `get_doc(_DT_ASSET, …).as_dict()` thiếu strip `qr_token` (chống regress khi thêm endpoint asset-read mới) — xem [07 §Guard no-raw-token](./07_Testing_QA.md). **KHÔNG schema-delta** (`CAP_SET_VERSION` GIỮ `v95.3388ee5629c1`); FE KHÔNG đổi (BE-only — 0 FE đọc field `data.qr_token` từ payload đọc-asset; `grep -rn qr_token frontend/src` chỉ ra endpoint-name/comment/URL-flow, KHÔNG consumer payload).

**Errors:** 404 (`AC-E001`), 401, 403.

> **📱 Cross-ref Mobile-BE — `get_asset_kpi` (KPI vận-hành, asset-detail sub-tab, CR-11a 2026-07-13):** Endpoint `api/imm00.get_asset_kpi(name)` (`@frappe.whitelist()` bare → GET; guest dispatcher-403) `@imm00.py:1174` trả **KPI vận-hành 12-key OBJECT PHẲNG** tính on-the-fly cửa-sổ 12 tháng (`_ok({12-key})` @`:1250-1263` — compute từ `AC Asset Downtime Log` [uptime/downtime] + `Asset Repair docstatus=1` [MTTR/MTBF/`total_repair_cost`] + `PM Work Order` [`pm_compliance_pct`]; build dict tường minh KHÔNG `as_dict()` ⇒ no-raw-token parity §get_asset). **LIVE whitelisted — KHÔNG đụng `.py`.** `getAssetKpi` là **curate ĐẦU TIÊN của CR-11** (mở nhánh asset-detail sub-tab; 5 sub-tab backend LIVE 0 curated: `kpi`/`verify_chain`/`depreciation`/`commissioning`/`downtime`). Contract đầy đủ (`AssetKpi` closed **EXACT 12 prop** VERBATIM return-dict — `required` 5 always-present + nullable 7 return-None-hợp-lệ; `breakdown_count`=integer + 6 number + `name`/`lifecycle_status`/3-date string; **`total_repair_cost` = FINANCIAL** nullable number curate VERBATIM, **UI-render deferred mobile client** persona-gate; `AssetKpiEnvelope`; **200 = `oneOf[AssetKpiEnvelope, Error]`** closed-schema Decision-B — `_err(404)` asset∄ @`:1185-1186` → HTTP-200 nhánh Error; slot `{200,401,403}`) đặc tả tại **mobile-contract** [`docs/mobile/04-api-contract.md` §8.40](../mobile/04-api-contract.md) + [`docs/mobile/openapi/assetcore-mobile.openapi.yaml`](../mobile/openapi/assetcore-mobile.openapi.yaml) (`operationId: getAssetKpi`) + [ADR-MOBILE-038](../mobile/ADR-MOBILE-038.md). **Boundaries:** *Always* — curate VERBATIM 12 key theo return-dict (KHÔNG strip `total_repair_cost` FINANCIAL khỏi contract) · Decision-B lỗi nghiệp-vụ = HTTP-200 + Error envelope (KHÔNG raise→4xx). *Never* — bọc `{items}`/`{pagination}` (handler trả flat dict, KHÔNG paginate) · ép field nullable vào `required` (7 field return `None` hợp-lệ) · render `total_repair_cost` cho persona không quyền tài-chính (UI-gate FE). **One-Version Rule:** web SPA `frontend/` dùng cùng endpoint (tab KPI màn hồ-sơ) — 1 contract phục vụ cả web + mobile.

---

### `get_asset_action_meta` — Meta nạc cho 3 màn tạo WO scan-action (ADR-IMM00-QR-SCAN-ACTION §D11 / FR-00-99 / BR-00-48) — **NEW (Vòng 25)**

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.get_asset_action_meta` |
| Auth | **AUTH-REQUIRED** (`@frappe.whitelist()`, KHÔNG `allow_guest`) — session-gated như `get_asset` |
| Capability | đọc asset cơ bản (DocPerm read AC Asset — KHÔNG cap mới; IDOR `assert_vendor_can_access` là hàng rào chính) |

**Mục đích:** panel meta thiết bị trên 3 màn tạo WO đến từ deep-link QR scan-action (`CMCreateView`/`CalibrationCreateView`/`PMWorkOrderCreateView`, `?asset=<name>&source=qr-scan`) chỉ cần ~5-6 field hiển thị → endpoint NẠC này thay `get_asset` (full-doc) để **KHÔNG over-fetch field tài chính** xuống persona vận hành.

**Request:** `?name=AC-ASSET-2026-00001`

**Response 200 — ĐÚNG 6 key allowlist (KHÔNG hơn/kém):**
```json
{
  "name": "AC-ASSET-2026-00001",
  "asset_name": "Máy thở Dräger V500",
  "device_model_name": "Dräger Evita V500",
  "lifecycle_status": "Active",
  "risk_classification": "C",
  "location_name": "Khoa Hồi sức tích cực"
}
```

> **Allowlist EXACT (CHỐT §D11 / BR-00-48):** dựng qua `frappe.db.get_value("AC Asset", name, ["name","asset_name","device_model","lifecycle_status","risk_classification","location"], as_dict=True)` → enrich `device_model_name` (IMM Device Model.model_name) + `location_name` (AC Location.location_name) + DROP raw Link key `device_model`/`location` TRƯỚC return. **KHÔNG `as_dict()`** (không leak full-doc). `risk_classification` đọc THẲNG (Select stored, read_only, `fetch_from device_model.risk_classification`). **Acceptance:** `set(data.keys()) == {"name","asset_name","device_model_name","lifecycle_status","risk_classification","location_name"}`; tập cấm `{gross_purchase_amount, accumulated_depreciation, current_book_value, purchase_cost, salvage_value, qr_token}` ∩ keys = ∅.

> **3 lớp bảo mật GIỮ như `get_asset` (KHÔNG nới):** (1) **404 in-handler** — `name` rỗng/None/∄ → `_err(_ERR_ASSET_NOT_FOUND, 404)` (HTTP-200 + Error envelope **in-handler**, KHÔNG raise→4xx, KHÔNG 500/traceback-leak). (2) **403 IDOR** — `assert_vendor_can_access("AC Asset", name)` TRƯỚC build payload → vendor ngoài scope `_err(e.message, e.code)` in-handler cap-403 no-leak (0 byte 6-field payload); guest/no-token → **dispatcher-403** re-auth (KHÔNG vào handler). (3) **DocPerm read** áp như đường `get_asset` (whitelist session-gate). **`get_asset` GIỮ NGUYÊN** (admin-detail `AssetDetailView` còn cần tài chính — KHÔNG đổi).

**FE consumer:** `getAssetActionMeta(name): Promise<AssetActionMeta>` (`api/imm00.ts`) — type `AssetActionMeta` CHỈ 6 field (KHÔNG `extends AcAsset`). 3 view loader đổi `getAsset`→`getAssetActionMeta`; nhãn rỗng VI `'Chưa gán'` (KHÔNG `'—'`); fail-safe 403/404/network→`assetMeta=null` panel ẩn no-leak. Xem [06 §action-meta-lean](./06_Frontend_Design.md).

**Errors:** 404 (`AC-E001`), 401, 403 (IDOR in-handler + dispatcher guest). **KHÔNG 500/traceback** (no-leak). Lỗi nghiệp vụ = HTTP-200 + Error envelope (in-handler), KHÔNG raise→4xx. Cài đặt: [04 §II.1.8g-ACTIONMETA](./04_Backend_Design.md) · test [07 §III.6.f-ACTIONMETA](./07_Testing_QA.md).

---

### `resolve_qr_token` — Deep-link QR → Asset (ADR-001 A2)

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.resolve_qr_token` |
| Auth | **AUTH-REQUIRED** (`@frappe.whitelist()`, KHÔNG `allow_guest`) — NĐ98 |
| Capability | `asset.read` (gate `rbac.require("asset.read")` đầu hàm — xem 04 §III.1c-1a) |
| **Rate limit** | **`@rate_limit(limit=30, seconds=60, ip_based=True)` (Vòng 12 B)** — chống brute-force token + DoS; chạy TRƯỚC `rbac.require`; vượt → **429** no-leak. Xem §I.7a. |

**Mục đích:** FE route `/a/:token` (camera điện thoại quét QR) gọi endpoint này → lấy `name` asset → `router.replace({name:'AssetScanInfo'})`. A2 CHỈ resolve + redirect; màn info mobile-first = **A6/V7** (`get_asset_scan_info`, xem dưới).

> **Self-Correction A6 (2026-06-04):** A2 nguyên gốc redirect sang `AssetDetail` (`/assets/:id`, màn admin 926 dòng / 5 tab — KHÔNG mobile-first, lộ field quản trị). A6 ĐỔI đích redirect sang màn info mobile-first MỚI `AssetScanInfo` (xem 06 §II.3c) + endpoint payload riêng `get_asset_scan_info`. `resolve_qr_token` GIỮ NGUYÊN contract (vẫn dùng được như fallback / lookup name), KHÔNG đổi shape. Màn `AssetScanInfo` gọi THẲNG `get_asset_scan_info` (1 call, không cần qua `resolve_qr_token` trước).

**Request:** `?token=Xk7p2Qm9_aZ4Lr8sT0wVcQ` (`AC Asset.qr_token`, ~22 ký tự URL-safe)

**Response 200:**
```json
{ "success": true, "data": {
  "name": "AC-ASSET-2026-00001",
  "asset_code": "BV-A-001",
  "lifecycle_status": "Active",
  "device_model_name": "Máy thở Bennett 980",
  "location_name": "Khoa Hồi sức tích cực — Giường 03"
} }
```

| Trường hợp | Mã | Ghi chú |
|---|---|---|
| Token hợp lệ + có quyền | 200 | trả định danh + field hiển thị tối thiểu |
| **Token hợp lệ KÈM whitespace** (`' <tok> '`, `'<tok>\n'`) | **200** | **Chuẩn hoá server-side (BR-00-40)** — `resolve_qr_token` strip token đầu hàm → resolve ĐÚNG asset; KHÔNG còn false-404 do space/newline (artifact encode QR tem nhiệt / nhập tay / wedge-scanner) |
| **Token TOÀN khoảng trắng** (`'   '`, `'\t'`, `'\n'`) | **404** `AC-E001` | sau strip → `''` → 404 leak-safe **NHƯ token rỗng**, **KHÔNG query DB** (query-count = 0, đối xứng `''`) |
| Token KHÔNG tồn tại | **404** `AC-E001` | KHÔNG 500, message generic — enumeration/leak-safe |
| User KHÔNG có `asset.read` | **403** PermissionError | `require("asset.read")` |
| Vendor user, asset NGOÀI scope | **403** (`ErrorCode.FORBIDDEN`) | `assert_vendor_can_access("AC Asset", name)` — IDOR guard, KHÔNG trả data |

> **Chuẩn hoá input (CHỐT factory vòng 6 — BR-00-40 / §IV.17):** `resolve_qr_token` (SSoT `services/imm00.py`) **strip whitespace `token` đầu hàm** (`token = token.strip()`) TRƯỚC guard rỗng + TRƯỚC query → (1) token hợp lệ kèm space/`\n` resolve đúng; (2) whitespace-only → rỗng-sau-strip → 404 KHÔNG query; (3) whitespace KHÔNG khớp → 404 leak-safe (KHÔNG phân biệt sai-định-dạng vs không-tồn-tại, KHÔNG 500/417, KHÔNG raw exc). **Chuẩn hoá đặt DUY NHẤT ở service** (KHÔNG ở API tier, KHÔNG fork) → `get_asset_scan_info` nhánh `token` kế thừa parity. FE `QrResolveView.vue:34` (`.trim()`) GIỮ làm defense-in-depth lớp 1; server tự đúng độc lập (mobile-BE/caller-khác). Cài đặt: [04 §II.1.8a-NORM](./04_Backend_Design.md).

**Audit:** KHÔNG ghi audit/lifecycle khi resolve (read-only lookup — chốt ADR-001 D4, tránh spam chain mỗi lần quét).

---

> **Cross-ref Mobile-BE — `get_user_context` (session bootstrap who-am-I, FLOW-1):** Endpoint `api/layout.py:get_user_context()` (`@frappe.whitelist(allow_guest=True)`, GET 0-param) trả identity session hiện tại (13 field: `user`, `full_name`, `roles`, `imm_roles`, `role_profile_name`, `department`, `is_profile_completed`, `has_employee_link`, …) cho **app home mobile persona-aware + flow-gating** (sau login, KHÔNG còn hardcode "Đã đăng nhập"). LIVE whitelisted — KHÔNG đụng `.py`. Contract đầy đủ (envelope `UserContextEnvelope` / `UserContextData`, 200=`oneOf[UserContextEnvelope,Error]` closed-schema C7, slot `{200,401}` do `allow_guest=True` ⇒ Guest vào handler → in-handler `_err` 401, KHÔNG dispatcher-403; 2 cờ `is_profile_completed`/`has_employee_link` = `integer enum[0,1]` né int-vs-bool codegen trap) đặc tả tại **mobile-contract** [`docs/mobile/04-api-contract.md` §8.19](../mobile/04-api-contract.md) + [`docs/mobile/openapi/assetcore-mobile.openapi.yaml`](../mobile/openapi/assetcore-mobile.openapi.yaml) (`operationId: getUserContext`) + ADR-MOBILE-008 (allow_guest exempt 401/403 symmetry). Web SPA `frontend/` dùng cùng endpoint qua auth-store (login-page session-check) — **One-Version Rule**: 1 contract phục vụ cả web + mobile.

---

### `get_asset_scan_info` — Thông tin thiết bị mobile-first khi quét QR (ADR-001 A6 / V7) — **NEW**

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.get_asset_scan_info` |
| Auth | **AUTH-REQUIRED** (`@frappe.whitelist()`, KHÔNG `allow_guest`) — NĐ98 |
| Capability | `asset.read` (gate `rbac.require("asset.read")` đầu hàm — **TÁI DÙNG cap A2, KHÔNG thêm cap mới**) |
| **Rate limit** | **`@rate_limit(limit=30, seconds=60, ip_based=True)` (Vòng 12 B)** — bucket RIÊNG với `resolve_qr_token` (cache key gồm `cmd`); chạy TRƯỚC `rbac.require`; vượt → **429** no-leak. Xem §I.7a. |
| Service | `assetcore.services.imm00.build_asset_scan_info(asset_name)` (READ-ONLY) |

**Mục đích:** Màn `AssetScanInfo` (mobile-first, 06 §II.3c) gọi endpoint NÀY → payload **cốt lõi cho người dùng tại hiện trường**: định danh + model + vị trí + trạng thái (nhãn VI) + bảo trì gần nhất. Thay thế việc redirect sang `AssetDetail` (màn admin). KHÔNG phải sự kiện gì — chỉ đọc.

**Request:** chấp nhận **token HOẶC name** (đúng 1 trong 2):
- `?token=Xk7p2Qm9_aZ4Lr8sT0wVcQ` — luồng quét QR (FE truyền thẳng `route.params.token`).
- `?name=AC-ASSET-2026-00001` — luồng mở từ link nội bộ (đã biết name).

Resolve thứ tự: nếu có `token` → `_svc_resolve_qr_token(token)` (SSoT — **strip whitespace tự động kế thừa**, BR-00-40); nếu không → dùng `name` (`name.strip()` TRƯỚC `frappe.db.exists` — **chuẩn-hoá whitespace riêng nhánh name, BR-00-50/Vòng 31**). Cả hai rỗng/không khớp → 404 leak-safe.

> **Parity chuẩn hoá token (CHỐT factory vòng 6 — FR-00-91 / BR-00-40):** nhánh `token` của `get_asset_scan_info` gọi CÙNG SSoT `_svc_resolve_qr_token` → chuẩn-hoá whitespace **kế thừa tự động**, KHÔNG fork nhánh strip riêng. `get_asset_scan_info(token=' <tok> ')` / `'<tok>\n'` → trả ĐÚNG payload A6 (12-field) — parity hoàn toàn với `resolve_qr_token`. Token TOÀN khoảng trắng → SSoT strip → `''` → resolve None → `asset_name=None` → 404, KHÔNG query asset thừa.

> **Parity chuẩn hoá `name` (CHỐT factory vòng 31 — FR-00-101 / BR-00-50 — Self-Correction bất đối xứng 2 nhánh):** nhánh `name` (điều hướng nội bộ list/desktop, deep-link `/assets/:id/info`, copy-paste, mobile-BE) **KHÔNG** qua SSoT token nên trước Vòng 31 tra `name` THÔ → false-404 khi `name` kèm whitespace. Vòng 31 thêm `name = name.strip()` (1 dòng, trong `get_asset_scan_info`, sau coerce-str, TRƯỚC `frappe.db.exists`) — đường riêng, KHÔNG fork strip-TOKEN (token-path BẤT ĐỘNG). `get_asset_scan_info(name='  A-042  ')` / `'A-042\n'` → strip → `'A-042'` → `db.exists` khớp → payload A6 đúng. `name` TOÀN khoảng trắng → strip `''` → `elif name and …` short-circuit (`name` falsy → KHÔNG gọi `db.exists`) → 404, KHÔNG full-scan. Space GIỮA (`'A 042'`) sau strip 2 đầu VẪN không khớp → 404 (CHỈ strip leading/trailing — KHÔNG lowercase/collapse-inner, parity quy tắc token Vòng 6, KHÔNG over-normalize). Contract bất biến — CHỈ thêm normalize input `name`.

**Response 200:**
```json
{ "success": true, "data": {
  "name": "AC-ASSET-2026-00001",
  "asset_code": "BV-A-001",
  "asset_name": "Máy thở Bennett 980 — HSTC G03",
  "manufacturer_sn": "SN-980-2024-0457",
  "device_model_name": "Máy thở Bennett 980",
  "location_name": "Khoa Hồi sức tích cực — Giường 03",
  "lifecycle_status": "Active",
  "lifecycle_status_label": "Đang hoạt động",
  "last_maintenance": {
    "event_type": "pm_completed",
    "event_type_label": "Hoàn tất bảo trì định kỳ",
    "date": "2026-04-18"
  },
  "next_pm_date": "2026-07-18",
  "pm_overdue": false,
  "next_calibration_date": "2026-09-30",
  "calibration_overdue": false
} }
```

> **Field-name parity (CHỐT Vòng 27 B):** mã hiện tại (`services/imm00.py:352`) trả key bảo trì gần nhất là **`recent_maintenance`** (KHÔNG `last_maintenance`) và CHƯA có `lifecycle_status_label`. Spec này mô tả contract A6 mục tiêu; **đề mục Vòng 27 B CHỈ thêm `pm_overdue`** (KHÔNG đụng/đổi tên 8 field hiện có). Việc đồng bộ tên `recent_maintenance`↔`last_maintenance` + thêm `lifecycle_status_label` là `[ROADMAP]` riêng — KHÔNG gộp vào vòng này để giữ scope (KHÔNG breaking FE).

> **Field delta (CHỐT Vòng 28 B — chiều HIỆU CHUẨN):** payload thêm ĐÚNG 2 field `next_calibration_date` (str|None) + `calibration_overdue` (bool) — DISTINCT với cặp PM `next_pm_date`/`pm_overdue` (Vòng 27). 9 field FR-00-85 GIỮ NGUYÊN tên+giá trị. `next_calibration_date` đọc field AC Asset đã có (chỉ thêm vào fields-list `db.get_value` + dict); KHÔNG schema/field/cap/endpoint/enum/patch delta. Derive `calibration_overdue` xem 04 §II.1.8e-CALOVERDUE.

> **Value-type delta (CHỐT Vòng 11 — Self-Correction parity):** `next_pm_date` ĐỔI KIỂU từ `datetime.date` object thô → `str\|None` (`'YYYY-MM-DD'`/`null`) qua CÙNG helper `_date_str_or_none` như `next_calibration_date`. **KHÔNG đổi whitelist** (vẫn 9 FR-00-85 + `next_calibration_date` + `calibration_overdue` + `available_actions`) — chỉ chuẩn hoá giá trị của 1 key đã có để shape đối xứng hoàn toàn. INVARIANT: `pm_overdue` vẫn derive từ RAW row value TRƯỚC normalize (KHÔNG hồi quy). KHÔNG schema/field/cap/endpoint/enum/patch/`CAP_SET_VERSION` delta. Xem 04 §II.1.8d-PMDATESTR · test 07 §III.6.f-PMDATESTR.

> **Field delta (CHỐT Vòng 37 — `manufacturer_sn` Số serial NSX, FR-00-103 / BR-00-52):** payload thêm ĐÚNG 1 field `manufacturer_sn: str` (Số serial NSX — định danh truy xuất NĐ98, parity đường label-PDF D5). Coalesce `row.get("manufacturer_sn") or ""` ⇒ str (rỗng/NULL → `''`, KHÔNG `null`, KHÔNG raw object — đối xứng `asset_code`/`asset_name`). Đọc từ field AC Asset **đã có** (`ac_asset.json:296`, `fieldtype=Data`) — THÊM vào fields-list của CÙNG `db.get_value` (no extra round-trip / no-N+1) + dict trả về. Payload **11→12-field**. KHÔNG schema/field/cap/endpoint/enum/patch/`CAP_SET_VERSION` delta (`v97.c30c69b8974d` GIỮ). KHÔNG field nhạy cảm mới (BR-00-34 `'qr_token' not in payload` GIỮ). FE serialText `'Chưa rõ'` fallback: xem 06 §AssetScanInfoView serialText. Derive xem 04 §II.1.8d-SCANSN · test 07 §III.6.m-SCANSN.

> **Field delta (CR-19 — `department_name` Khoa/Phòng, scan-schema-parity 2026-07-13):** payload thêm ĐÚNG 1 field `department_name: str` (Tên **Khoa/Phòng** thiết bị) — **denorm** `AC Asset.department` (Link → `AC Department`) → `AC Department.department_name` qua CÙNG `_str_or_blank`, **đối xứng cách `location_name` đang điền** trong CÙNG builder (`if row.get("department")` chỉ skip N+1 khi chưa gán; `_str_or_blank('') → ''`). Rỗng/NULL → `''` (KHÔNG `null`, KHÔNG rò raw Link id `AC-DEPT-xxxx`). Đọc từ field AC Asset **đã có** — THÊM `department` vào fields-list của CÙNG `db.get_value` (no extra round-trip / no-N+1) + `department_name` vào dict trả về `services/imm00.py:825`. **Precedent verbatim:** `get_asset` đã enrich `department_name` tại `imm00.py:302` (`AssetDetail.department_name`). KTV hiện trường cần biết thiết bị thuộc **khoa nào** (KHÔNG chỉ vị trí lắp đặt) trước khi báo sự cố / mở WO. Emit vô-điều-kiện ⇒ ∈ `required[]` (parity `location_name`, KHÔNG nullable). KHÔNG cap/schema/DocType/enum/patch/`CAP_SET_VERSION` delta. Mobile mirror parity: [`../mobile/ADR-MOBILE-035.md`](../mobile/ADR-MOBILE-035.md) + [`../mobile/04-api-contract.md`](../mobile/04-api-contract.md) (`AssetScanInfo.department_name`). *(Ghi chú: bảng field-A6 dưới có trước C-ASCAN-PARITY/CR-19 — bộ field BE-emit đầy đủ (kèm `risk_classification`/`warranty_expiry_date`/`warranty_expired`) lấy SSoT ở mobile contract `AssetScanInfo` §04.)*

| Trường | Nguồn | Ghi chú |
|---|---|---|
| `name`, `asset_code`, `asset_name` | `AC Asset` | định danh cốt lõi |
| `manufacturer_sn` | `AC Asset.manufacturer_sn` (`fieldtype=Data`, đã có) — coalesce `or ""` | **`str`** (Số serial NSX — định danh truy xuất NĐ98 D5/BR-00-52). Rỗng/NULL → `''` (KHÔNG `null`, KHÔNG raw object — parity `asset_code`/`asset_name`). FE render dòng "Số serial NSX" với fallback VI `'Chưa rõ'` khi rỗng. Vòng 37 / FR-00-103 — xem 04 §II.1.8d-SCANSN. |
| `device_model_name` | `IMM Device Model.model_name` (1 `get_value` qua FK `device_model`) | "" nếu chưa gán model |
| `location_name` | `AC Location.location_name` (1 `get_value` qua FK `location`) | "" nếu chưa gán vị trí |
| `department_name` | `AC Department.department_name` (1 `get_value` qua FK `department`) — coalesce `_str_or_blank` | **`str`** (Tên Khoa/Phòng — CR-19, parity `location_name`). `''` nếu chưa gán khoa (KHÔNG `null`, KHÔNG raw Link id). ∈ `required` (emit vô-điều-kiện). `services/imm00.py:825` — xem mobile [`ADR-MOBILE-035`](../mobile/ADR-MOBILE-035.md). |
| `lifecycle_status` | `AC Asset.lifecycle_status` (mã EN canonical) — **CÓ THỂ là `''`** (BE phát `lifecycle_status or ""` cho asset legacy chưa-set — `services/imm00.py:317/597`) HOẶC mã LẠ ngoài enum (drift import/migration) | để FE chọn class + nhãn pill; **KHÔNG hiển thị thô**. **FE safe-fallback (CHỐT factory vòng 8 — FR-00-93 / BR-00-42 / ADR §D10):** pill render qua `lifecycleStatusLabel(lifecycle_status)` (`constants/labels.ts`) — với mã rỗng/lạ → nhãn VI an toàn `'Không xác định'` (KHÔNG leak mã EN/code thô, KHÔNG box rỗng); class qua `lifecycleStatusClass` → chip trung tính gray. **BE contract KHÔNG đổi** (`or ""` GIỮ) — FE chịu trách nhiệm nhãn an toàn. Xem [06 §status-pill-safe](./06_Frontend_Design.md). |
| `lifecycle_status_label` | **SSoT VI** `services/shared/labels.py::LIFECYCLE_STATUS_LABEL_VI` (xem 04 §III.1c-6) | nhãn hiển thị VI, fallback = mã gốc nếu thiếu key |
| `last_maintenance` | **1 truy vấn** `Asset Lifecycle Event` filter `asset=name`, `event_type IN (pm_completed, repair_completed, calibration_passed)`, `ORDER BY timestamp DESC LIMIT 1` | `null` nếu chưa có sự kiện bảo trì nào (KHÔNG load toàn timeline — chống N+1) |
| `last_maintenance.event_type` | mã enum thô (vd `pm_completed`) | |
| `last_maintenance.event_type_label` | SSoT VI `LIFECYCLE_EVENT_LABEL_VI` | nhãn loại sự kiện tiếng Việt |
| `last_maintenance.date` | `timestamp` của event (format `YYYY-MM-DD`) | ngày bảo trì gần nhất |
| `next_pm_date` | `AC Asset.next_pm_date` (denormalized field — KHÔNG truy PM Schedule) — chuẩn hoá qua `_date_str_or_none` | **`str\|None`** (`'YYYY-MM-DD'`/`null`) — Date field từ DB trả `date` object thô → BE chuẩn hoá str để FE `formatDate` parse ổn định. `null` nếu không có. **Đối xứng `next_calibration_date`** (Vòng 11 / FR-00-86 — xem 04 §II.1.8d-PMDATESTR). |
| `pm_overdue` | **DERIVE SERVER-SIDE** (BR-00-36): `True` ⟺ `next_pm_date` không rỗng ∧ `getdate(next_pm_date) < getdate(nowdate())` ∧ `lifecycle_status ∉ {Out of Service, Decommissioned}` | `bool` — SSoT quá-hạn ở BE (timezone-safe). NULL/hôm-nay/tương-lai/ngừng-dùng → `false`. FE CHỈ render cờ, KHÔNG so ngày bằng client clock. Xem 04 §II.1.8c-PMOVERDUE. |
| `next_calibration_date` | `AC Asset.next_calibration_date` (denormalized field đã có — KHÔNG truy Calibration Schedule) | `null` nếu không có (Vòng 28 B / BR-00-37) |
| `calibration_overdue` | **DERIVE SERVER-SIDE** (BR-00-37): `True` ⟺ `next_calibration_date` không rỗng ∧ `getdate(next_calibration_date) < getdate(nowdate())` ∧ `lifecycle_status ∉ {Out of Service, Decommissioned}` | `bool` — SSoT quá-hạn hiệu chuẩn ở BE (timezone-safe). NULL/hôm-nay/tương-lai/ngừng-dùng → `false`. FE CHỈ render cờ, KHÔNG so ngày bằng client clock. Xem 04 §II.1.8e-CALOVERDUE. |
| `available_actions` | **DERIVE SERVER-SIDE** (ADR §D1/D2/D9) qua `_build_available_actions(lifecycle_status)` — `list[dict]` 4 CTA màn quét QR (`report_failure`/`request_pm`/`request_cm`/`request_calibration`). Mỗi phần tử shape **CHÍNH XÁC** `{key:str, label:str (VI SSoT BE), route:str (route-name FE), enabled:bool, reason:str}`. `enabled = has_cap ∩ lifecycle_allows`. Xem §III.2 (bất biến reason). | `list[dict]` (đúng 4 phần tử, thứ tự cố định = thứ tự render FE). Xem 04 §II.1.8f. |

**KHÔNG trả (field nhạy cảm — A6 acceptance):** `gross_purchase_amount`, `current_book_value`, `accumulated_depreciation`, `depreciation_schedule`, audit hash chain, `supplier` / internal supplier code, `byt_reg_no` chi tiết. Payload là **whitelist tường minh** (chỉ build các field liệt kê ở trên — KHÔNG `frappe.get_doc().as_dict()` rồi pop).

| Trường hợp | Mã | Ghi chú |
|---|---|---|
| token/name hợp lệ + có quyền | 200 | payload mobile cốt lõi ở trên |
| **`token` hợp lệ KÈM whitespace** (`' <tok> '`, `'<tok>\n'`) | **200** | **kế thừa chuẩn-hoá SSoT `_svc_resolve_qr_token` (BR-00-40)** → payload A6 (12-field) đúng; parity với `resolve_qr_token` |
| **`token` TOÀN khoảng trắng** | **404** `AC-E001` | SSoT strip → `''` → resolve None → 404, KHÔNG query asset thừa |
| **`name` hợp lệ KÈM whitespace 2 đầu** (`'  A-042  '`, `'A-042\n'`, `'\tA-042\t'`) | **200** | **`name.strip()` TRƯỚC `db.exists` (BR-00-50 / Vòng 31)** → khớp asset → payload A6 (12-field) đúng; hết false-404 — parity nhánh token |
| **`name` TOÀN khoảng trắng** (`'   '`, `'\n'`) | **404** `AC-E001` | strip → `''` → `elif name and …` short-circuit (`name` falsy) → KHÔNG gọi `db.exists` → 404, **KHÔNG full-scan** |
| **`name` có space GIỮA** (`'A 042'` — name hỏng thật) | **404** `AC-E001` | strip 2 đầu VẪN `'A 042'` → `db.exists` không khớp → 404 (CHỈ strip leading/trailing — KHÔNG over-normalize/lowercase/collapse-inner) |
| token/name KHÔNG tồn tại / rỗng / sai định dạng | **404** `AC-E001` | KHÔNG 500, KHÔNG phân biệt sai-định-dạng vs không-tồn-tại — leak-safe |
| User KHÔNG có `asset.read` | **403** PermissionError | `rbac.require("asset.read")` (gate TRƯỚC mọi DB read) |
| Vendor user, asset NGOÀI scope | **403** (`ErrorCode.FORBIDDEN`) | `assert_vendor_can_access("AC Asset", name)` sau khi resolve được name |

**Thứ tự gate (BẮT BUỘC):** `rbac.require("asset.read")` → resolve name (token|name) → `name` rỗng/không khớp → 404 → `assert_vendor_can_access("AC Asset", name)` (403 IDOR) → build payload. Gate cap chạy TRƯỚC resolve để guest không phân biệt được token tồn tại hay không.

**Audit (CHỐT A6 — đồng nhất quyết định A2/D4):** `get_asset_scan_info` là **READ-ONLY** → **KHÔNG emit lifecycle event, KHÔNG ghi IMM Audit Trail** (mỗi lần quét QR KHÔNG được sinh record — chống spam audit chain). KHÔNG gọi `ensure_asset_qr_token` (không sinh token ở luồng đọc; token đã có từ A1/backfill D5).

**KHÔNG N+1:** tối đa 4 `get_value`/`get_all` cố định bất kể dữ liệu: (1) resolve name, (2) AC Asset row đa-field, (3) device_model→model_name + location→location_name (2 get_value), (4) 1 `get_all` ALE `LIMIT 1`. KHÔNG loop, KHÔNG load timeline.

#### `available_actions` — contract + bất biến `reason` non-empty (ADR §D1/D2/D9 / FR-00-92 / BR-00-41) — **REASON-NON-EMPTY (factory vòng 7)**

Payload `get_asset_scan_info` chứa `available_actions: list[dict]` — 4 CTA màn quét QR, derive 100% SERVER-SIDE. **Shape mỗi phần tử (CHÍNH XÁC — KHÔNG field thừa):**

```json
{ "key": "report_failure", "label": "Báo hỏng", "route": "IncidentCreate",
  "enabled": false, "reason": "Thiết bị đã thanh lý" }
```

| Field | Kiểu | Ghi chú |
|---|---|---|
| `key` | str | 1 trong `report_failure` / `request_pm` / `request_cm` / `request_calibration` |
| `label` | str | nhãn VI — **SSoT literal BE** (`_scan_action_specs`); FE KHÔNG hardcode |
| `route` | str | route-NAME FE (`IncidentCreate`/`PMWorkOrderCreate`/`CMCreate`/`CalibrationCreate`); FE dựng URL qua `router.resolve({name, query:{asset, source:'qr-scan'}})` — KHÔNG path thô, KHÔNG token |
| `enabled` | bool | `has_cap ∩ lifecycle_allows` (derive BE) |
| `reason` | str | VI giải thích khi `enabled=false`; `""` khi `enabled=true` |

**Bất biến `reason` (FR-00-92 / BR-00-41 — D9):**

| # | Bất biến | Đo được |
|---|---|---|
| 1 | **enabled=False ⟹ reason!=""** | `for a in available_actions: a["enabled"] is False ⟹ a["reason"] != ""` — cả 4 action, MỌI `lifecycle_status` (5 đã biết + `''` rỗng + mã LẠ ngoài enum) |
| 2 | **enabled=True ⟹ reason==""** | bất biến cũ D2 GIỮ |
| 3 | **status rỗng/lạ + có cap** → `reason == "Thiết bị không ở trạng thái cho phép thao tác này"` (`_LIFECYCLE_REASON_UNKNOWN`) | 4 action |
| 4 | **status rỗng/lạ + thiếu cap** action đó → `reason == "Bạn không có quyền thực hiện thao tác này"` (`_CAPABILITY_REASON`) | bậc 2 ưu tiên bậc 3 |
| 5 | **5 status đã biết byte-for-byte** | Active/Commissioned → enabled `reason==""`; Decommissioned → 4 disabled `"Thiết bị đã thanh lý"`; Out of Service → report_failure/request_cm enabled, request_pm/request_calibration disabled `"Thiết bị đang ngừng hoạt động — chỉ cho phép báo hỏng / yêu cầu sửa chữa"`; Draft → 4 disabled `"Thiết bị chưa đưa vào vận hành"` |

**Derive reason (BE — 04 §II.1.8f):** 3 bậc `_lifecycle_reason(status,key)` **or** (`_CAPABILITY_REASON` nếu thiếu cap) **or** `_LIFECYCLE_REASON_UNKNOWN`. Reason 100% VI literal **ở BE** (no-EN-leak); FE render `a.reason` nguyên văn (KHÔNG bịa/dịch). **KHÔNG field payload mới, KHÔNG đổi shape, `CAP_SET_VERSION` GIỮ.** FE render an toàn (hết dangling `aria-describedby` + trailing-rỗng `aria-label`): xem [06 §reason-render](./06_Frontend_Design.md).

---

### `get_asset_label_data` — Dữ liệu in nhãn QR theo 1 asset (ADR-001 A3 / D3)

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.get_asset_label_data` |
| Auth | **AUTH-REQUIRED** (`@frappe.whitelist()`, KHÔNG `allow_guest`) — NĐ98 |
| Capability | **`asset.print`** (gate `rbac.require("asset.print")` đầu hàm) — **D6 (EXECUTED Vòng 3) đổi từ `asset.write`**: in nhãn = quyền PRINT (DocPerm print=1 sẵn cho persona vận hành), KHÔNG còn `asset.write` (chỉ Super Admin). `asset.print`→(AC Asset,"print"). `CAP_SET_VERSION` = `v97.c30c69b8974d`. |
| Rate limit | **`@rate_limit(limit=AC_LABEL_DATA_RATE_LIMIT, seconds=60, ip_based=True)` (Vòng 36 / BR-00-51)** — hằng RIÊNG `AC_LABEL_DATA_RATE_LIMIT = 20` (read-mostly preview, song song batch/pdf=20; KHÔNG tái dùng định-danh hằng khác kể cả khi trùng giá-trị — tách ngữ-nghĩa), **bucket RIÊNG** (cmd → counter TÁCH BIỆT batch/mark/pdf/resolve/regen). Vượt → **429** NGOÀI/TRƯỚC `rbac.require` ⇒ **0 byte payload build + 0 mint side-effect** (`ensure_asset_qr_token` KHÔNG chạy → 0 `qr_generated`), no-leak. Đóng write-amplification mint-token bị hammer — lỗ hổng CUỐI họ endpoint nhãn. Xem §I.7c. |

**Mục đích:** FE màn in nhãn (A4/V5) gọi endpoint NÀY để build payload tem QR theo 1 asset (preview + dựng `QRLabel` encode URL `/a/<token>`). KHÔNG phải là sự kiện in — chỉ lấy dữ liệu (nhưng là tiền-đề bắt buộc của thao-tác-in ⇒ xếp nhóm WRITE).

**Request:** `?asset=AC-ASSET-2026-00001` (`AC Asset.name`)

**Response 200:**
```json
{ "success": true, "data": {
  "name": "AC-ASSET-2026-00001",
  "asset_code": "BV-A-001",
  "device_model_name": "Máy thở Bennett 980",
  "location_name": "Khoa Hồi sức tích cực — Giường 03",
  "lifecycle_status": "Active",
  "qr_url": "https://assetcore.benhvien.vn/a/Xk7p2Qm9_aZ4Lr8sT0wVcQ"
} }
```

| Trường | Nguồn | Ghi chú |
|---|---|---|
| `name` | `AC Asset.name` | định danh nội bộ |
| `asset_code` | `AC Asset.asset_code` | mã hiển thị trên tem |
| `device_model_name` | `IMM Device Model.model_name` (join từ `device_model`) | rỗng `""` nếu chưa gán model |
| `location_name` | `AC Location.location_name` (join từ `location`) | rỗng `""` nếu chưa gán vị trí |
| `lifecycle_status` | `AC Asset.lifecycle_status` | trạng thái vòng đời |
| `qr_url` | `_build_qr_url(qr_token)` (SSoT — §04 II.1.8-QRBASE) | **URL tuyệt đối**; host = base-URL **công khai cấu hình được** (site_config `assetcore_qr_base_url`), fallback `frappe.utils.get_url("/a/<token>")` khi chưa cấu hình — KHÔNG hardcode (BR-00-30); deep-link camera điện thoại **thật** mở thẳng (KHÔNG lộ host nội bộ) |

> **qr_url — base-URL công khai cấu hình được (BR-00-30, Vòng 14 B):** `qr_url` build qua helper SSoT `_build_qr_url`. Khi site_config `assetcore_qr_base_url` có host công khai (vd `https://htm.benhvien.vn`) → `qr_url = '<base>/a/<token>'`; vắng/sai → fallback `get_url` (hành vi cũ). Shape envelope KHÔNG đổi (vẫn field `qr_url`) — chỉ HOST bên trong khác. Áp cho MỌI endpoint trả `qr_url` (`get_asset_label_data[_batch]`, `regenerate_asset_qr_token`). Spec: [`04 §II.1.8-QRBASE`](./04_Backend_Design.md), [`02 BR-00-30`](./02_Analysis_Design.md), deploy [`08 §II.2`](./08_Deployment.md).

**qr_url — KHÔNG BAO GIỜ rỗng (BR-00-28):** nếu asset chưa có `qr_token` (legacy/import lọt backfill) → gọi `ensure_asset_qr_token(asset)` (idempotent — D1/D5) sinh token TRƯỚC khi build `qr_url`. Việc sinh token lần đầu emit `qr_generated` (1 lần, qua `ensure_asset_qr_token` — đây là sự kiện A1 sinh-token, KHÔNG phải sự kiện in). Asset đã có token → NO-OP, KHÔNG emit lại.

**Thứ tự gate (BẮT BUỘC — Vòng 36 / BR-00-51):** **`@rate_limit(AC_LABEL_DATA_RATE_LIMIT=20/60s/IP)` → 429 NGOÀI/TRƯỚC thân hàm** → `rbac.require("asset.print")` (403 nếu KHÔNG print) → `asset` rỗng/∄ → 404 leak-safe → `assert_vendor_can_access` (403 IDOR) → `_ok(build_asset_label_data(asset))` (200; mint idempotent chạy TRONG service trước build). Bucket RIÊNG (cmd); vượt ngưỡng → 0 byte payload build + 0 mint side-effect (`ensure_asset_qr_token` KHÔNG chạy ⇒ 0 `qr_generated` ALE/audit), no-leak. Đây là vì-sao throttle dù read-mostly: mint-token side-effect = write-amplification khi bị hammer. Xem §I.7c.

| Trường hợp | Mã | Ghi chú |
|---|---|---|
| Asset hợp lệ + có quyền | 200 | trả payload tem (qr_url tuyệt đối, không rỗng) |
| Asset KHÔNG tồn tại | **404** `AC-E001` | KHÔNG 500, message generic — leak-safe, KHÔNG đoán được id nội bộ |
| User KHÔNG có `asset.print` (Guest / role không-print) | **403** PermissionError | `require("asset.print")` — KHÔNG quyền in (least-privilege D6) |
| User có `asset.print` (print=1 — KTV/QL vật tư/Super Admin) | tiếp tục (200 nếu hợp lệ) | gate PRINT pass |
| Vendor user, asset NGOÀI scope | **403** (`ErrorCode.FORBIDDEN`) | `assert_vendor_can_access("AC Asset", name)` — IDOR guard GIỮ NGUYÊN, KHÔNG trả data |

**Audit (CHỐT A3 — D3):** `get_asset_label_data` là **READ-ONLY về sự kiện in** → **KHÔNG emit `label_printed`, KHÔNG ghi IMM Audit Trail** (preview nhãn ≠ in nhãn; tránh spam audit chain — KTV mở màn in nhiều lần). Ngoại lệ DUY NHẤT: nếu asset chưa có token, `ensure_asset_qr_token` emit `qr_generated` 1 lần (sự kiện sinh-token A1, không phải print event). Sự kiện in chỉ ghi ở `mark_label_printed`.

---

### Coerce tham số `assets` — SSoT `_coerce_asset_names` (V10 / ADR-IMM00-LABEL-PDF D17 — V15 +dedup D19) — áp cho 3 endpoint nhãn batch

> **Áp cho:** `print_asset_labels_pdf`, `get_asset_label_data_batch`, `mark_label_printed`. CHỐT 1 chỗ — KHÔNG lặp ở 3 mục dưới.

**Vấn đề gốc (Self-Correction):** 3 endpoint trước V10 dùng dòng trần `names = frappe.parse_json(assets) if isinstance(assets,str) else (assets or [])`. `frappe.parse_json` gọi `json.loads` THẲNG → input HTTP non-JSON **raise `JSONDecodeError` → HTTP-500 + traceback leak**; JSON-scalar-string `'"AC-1"'` parse ra str `'AC-1'` → `len()`/iterate **duyệt từng KÝ TỰ** (4 ô lỗi / 4 `db.exists` / 4 IDOR-probe — vi phạm count==rows); JSON-number/object → `TypeError`/duyệt key. **V15 (D19) thêm vấn đề gốc thứ 2:** input chứa name TRÙNG (`['AC-1','AC-1','AC-2','AC-1']`) KHÔNG được khử → **khuếch đại trong-call** (mark ghi 2×4 record cho 2 asset thật / PDF 4 trang 2 trùng / batch 4 phần tử 3 trùng).

**Hợp đồng coerce (CHỐT — total-function, KHÔNG raise, idempotent + dedup giữ-thứ-tự in-call):** SSoT **`api/imm00.py:126`::`_coerce_asset_names(assets) -> list[str]`** (⚠️ NOT `services/imm00.py` — drift-note D19.1; drift-guard test xác nhận vị-trí-thật). 3 endpoint gọi `names = _coerce_asset_names(assets)` **NGAY SAU** `rbac.require("asset.print")`, **TRƯỚC** preset/empty/cap/IDOR.

| Input `assets` (HTTP/python) | `_coerce_asset_names` trả | Hệ quả endpoint |
|---|---|---|
| `['AC-1','AC-2']` (list unique) · `'["AC-1"]'` (JSON-array-string) | giữ nguyên `['AC-1',…]` (lọc element non-str) | **đường hợp lệ 0 regression** byte-for-byte |
| `['AC-1','AC-1','AC-2','AC-1']` (list TRÙNG) · `'["AC-1","AC-1"]'` | **`['AC-1','AC-2']`** / **`['AC-1']`** (dedup giữ-thứ-tự, lần đầu giữ) | **D19:** mark 1 event/asset thật · PDF 1 trang/asset · batch count==rows |
| `'AC-2026-00001'` (bare-code) · `''` · `'   '` · `'not-json'` | `[]` (try/except nuốt JSONDecodeError) | PDF→`_ERR_LABEL_EMPTY` (422) · batch→`_ok([])` · mark→`_ok` no-side-effect |
| `'"AC-1"'` (JSON-scalar str) | `[]` (list-gate loại str đơn) | KHÔNG char-walk; như hàng rỗng |
| `'123'` (JSON-number) · `'{"a":1}'` (JSON-object) | `[]` (list-gate loại int/dict) | KHÔNG `len()`/iterate sai kiểu → KHÔNG 500 |
| `[1, 'AC-1', None, 'AC-1']` (list lẫn non-str + trùng) | `['AC-1']` (per-element str-filter → dedup) | lọc-kiểu TRƯỚC, dedup SAU (compose D17→D19) |
| `None` | `[]` | default an toàn |

**Quy tắc (D17 3 bước + D19 dedup — khớp source thật `api/imm00.py`):** (1) str → `try: assets = frappe.parse_json(assets) except (ValueError, TypeError): return []`. (2) `if not isinstance(assets, list): return []` (loại scalar/str-đơn/int/dict/None). (3) `names = [a for a in assets if isinstance(a, str) and a]` (chỉ str non-rỗng). (4) **D19:** `return list(dict.fromkeys(names))` — khử trùng-lặp **giữ thứ-tự xuất-hiện-ĐẦU** (stdlib O(n), KHÔNG `set()`). **KHÔNG raise 422 trong helper** — helper thuần, không biết HTTP-status; empty-`[]` để gate empty của TỪNG endpoint xử (PDF 422 / batch `_ok([])` / mark no-op). **Thứ tự gate KHÔNG đổi**: `rbac.require` vẫn ĐẦU (403 cho Guest/thiếu-cap → coerce KHÔNG rò giới hạn cho khách chưa-auth).

#### §I.7d — Khử trùng-lặp in-call (D19) — bất biến đo được + cap-trên-dedup + GIỮ cross-call

**Dedup CHỈ trong-call** (1 lần gọi `_coerce_asset_names`), **KHÔNG xuyên-call** (no cache, no DB-state). Hệ quả per-endpoint:

| Lời gọi (1 call) | coerce ra | Kết quả | Bất biến |
|---|---|---|---|
| `mark_label_printed(assets=[a1,a1,a1])` | `[a1]` | **1** ALE `label_printed` + **1** IMM Audit Trail, `event_count=1`, `printed=[a1]` (KHÔNG 3) | all-or-nothing GIỮ |
| `print_asset_labels_pdf(assets=[a1,a1])` | `[a1]` | PDF **1 trang** (`pypdf.PdfReader.pages==1`, MediaBox khổ preset), KHÔNG 2 trang trùng | render-no-audit GIỮ (§D8) |
| `get_asset_label_data_batch([a1,a1])` | `[a1]` | `_ok([1 phần tử])` (count==rows: 1 unique == 1 row) | thứ-tự GIỮ |
| 2 lần gọi RIÊNG `mark_label_printed([a1])` | mỗi lần `[a1]` | **2** event (mỗi lần in = 1 sự kiện) | **GIỮ `test_mark_label_printed_idempotent_count` (4342)** — dedup KHÔNG xuyên-call |
| `get_asset_label_data_batch([a]*300)` (300 trùng) | `[a]` (len 1) | **KHÔNG 413** (cap đo TRÊN list dedup, `len(names)>200` = False) | cap `_MAX_LABEL_BATCH=200` |
| `>200 asset UNIQUE` | giữ N>200 unique | **413** `_ERR_BATCH_TOO_LARGE` GIỮ | cap đo unique, hành vi cũ |

**Gate-order (GIỮ NGUYÊN):** `[@rate_limit] → rbac.require("asset.print") → names = _coerce_asset_names(assets)` (D17 coerce + **D19 dedup**) `→ len(names) > _MAX_LABEL_BATCH (413) → exists/IDOR → ghi/render/build`. Cap đo SAU coerce ⟹ tự đo trên list ĐÃ dedup (KHÔNG cần sửa dòng cap). Malformed→`[]` GIỮ (LL-BE-42 no-500). FE: validNames đã unique → 0 regression (lưới-an-toàn BE, defense-in-depth).

---

### `get_asset_label_data_batch` — Dữ liệu in nhãn QR hàng loạt (ADR-001 A3 / D3)

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.get_asset_label_data_batch` |
| Auth | **AUTH-REQUIRED** — NĐ98 |
| Capability | **`asset.print`** (gate `rbac.require("asset.print")` đầu hàm) — **D6 (EXECUTED Vòng 3) đổi từ `asset.write`** (least-privilege; in hàng loạt = quyền PRINT). `CAP_SET_VERSION` = `v97.c30c69b8974d`. User KHÔNG print → **403**. |
| Rate limit | **`@rate_limit(limit=AC_LABEL_BATCH_RATE_LIMIT, seconds=60, ip_based=True)` (Vòng 14 / BR-00-46)** — hằng RIÊNG `AC_LABEL_BATCH_RATE_LIMIT = 20` (read-only ngưỡng CAO hơn mark, song song pdf=20), **bucket RIÊNG** (cmd). Vượt → **429** NGOÀI/TRƯỚC `rbac.require` ⇒ **0 byte payload build**, no-leak. Xem §I.7c. |

**Mục đích:** FE in hàng loạt (A4/V5 — nhiều tem 1 lần) gọi 1 lần lấy payload N asset.

**Request:** `?assets=["AC-ASSET-2026-00001","AC-ASSET-2026-00002"]` (JSON list `AC Asset.name`; FE truyền `frappe.call` arg `assets`).

**Response 200:** list payload theo **ĐÚNG thứ tự input**:
```json
{ "success": true, "data": [
  { "name": "AC-ASSET-2026-00001", "asset_code": "BV-A-001", "device_model_name": "Máy thở Bennett 980", "location_name": "Khoa HSTC — Giường 03", "lifecycle_status": "Active", "qr_url": "https://.../a/Xk7p..." },
  { "name": "AC-ASSET-2026-00099", "error": "AC-E001" }
] }
```

**Hợp đồng batch (CHỐT A3 — chống N+1, leak-safe):**

| Quy tắc | Chi tiết |
|---|---|
| **Thứ tự** | Output `data[i]` tương ứng `assets[i]` đầu vào (giữ nguyên thứ tự, KHÔNG sort lại). |
| **KHÔNG N+1** | Lookup `device_model_name`/`location_name` qua **1 truy vấn gộp / IN-clause / join** (KHÔNG loop `frappe.db.get_value` mỗi asset). Pattern: `frappe.get_all("AC Asset", filters={"name":["in",names]}, fields=[...])` 1 lần → map theo `name`; resolve `device_model`/`location` qua 2 IN-query gộp → dict lookup; build `qr_url` từ `qr_token` đã lấy sẵn. |
| **Asset không tồn tại** | **CHỐT: entry lỗi rõ ràng** `{ "name": "<input>", "error": "AC-E001" }` tại đúng vị trí — KHÔNG drop khỏi list (FE cần biết tem nào fail), KHÔNG 500, KHÔNG leak field khác. (Phương án "bỏ qua leak-safe" bị loại: làm lệch index input↔output, FE in nhầm tem.) |
| **IDOR / vendor scope** | Mỗi asset hợp lệ trong list PHẢI qua `assert_vendor_can_access("AC Asset", name)`. Vendor có ≥1 asset NGOÀI scope trong list → **403 cho TOÀN BỘ call** (`ErrorCode.FORBIDDEN`) — KHÔNG trả partial, KHÔNG leak asset nào thuộc/không-thuộc scope (nhất quán với single-asset IDOR; tránh dùng batch để dò scope). |
| **qr_url rỗng** | Như single: token-less asset → `ensure_asset_qr_token` trước khi build (idempotent). Để giữ "KHÔNG N+1" cho lookup hiển thị, token-backfill chỉ chạm asset thực sự thiếu token (thường 0 sau patch D5). |
| **Giới hạn batch (CHỐT vòng 22 / BR-00-33 — payload-DoS cap)** | `len(names) > _MAX_LABEL_BATCH` (hằng SSoT `services/imm00.py::_MAX_LABEL_BATCH = 200`) → **413** `_err(<MSG_VI>, 413)`, message VI cố định (vd `'Chỉ in tối đa 200 nhãn mỗi lần. Vui lòng chọn ít hơn.'`), KHÔNG leak asset name nào, KHÔNG build payload nào. Input rỗng `[]`/`None` → `data: []` (200, KHÔNG 413, KHÔNG side-effect). `len == _MAX_LABEL_BATCH` → PASS bình thường; `len == _MAX_LABEL_BATCH+1` → 413. Cap chạy **SAU** `rbac.require("asset.print")`, **TRƯỚC** vòng `exists`/IDOR → chỉ user đã-auth-print mới chạm ngưỡng (no-leak cho khách). |

**Thứ tự gate (BẮT BUỘC — KHÔNG đổi precedent):** **`@rate_limit(AC_LABEL_BATCH_RATE_LIMIT=20/60s/IP)` → 429 NGOÀI/TRƯỚC thân hàm (Vòng 14 / BR-00-46)** → `rbac.require("asset.print")` (403 nếu KHÔNG print) → **`names = _coerce_asset_names(assets)` (V10/D17 — coerce an toàn, KHÔNG raise/char-walk)** → **CAP-CHECK `len(names) > _MAX_LABEL_BATCH` → 413** → vòng `frappe.db.exists` + `assert_vendor_can_access` mỗi asset (403 IDOR; entry `AC-E001` cho missing tại đúng index) → `build_asset_label_data_batch`. Bucket RIÊNG (cmd); vượt → 0 byte payload build, no-leak. Xem §I.7c.

**Audit:** Như `get_asset_label_data` — READ-ONLY về sự kiện in, KHÔNG emit `label_printed`/audit (chỉ token-backfill emit `qr_generated` nếu cần).

---

### `mark_label_printed` — Ghi sự kiện in nhãn QR (ADR-001 A3 / D3)

| Method | POST |
|---|---|
| Path | `assetcore.api.imm00.mark_label_printed` |
| Auth | **AUTH-REQUIRED** — NĐ98 |
| Capability | **`asset.print`** (gate `rbac.require("asset.print")` đầu hàm) — **D6 (EXECUTED Vòng 3) đổi từ `asset.write`**: ghi `label_printed`+audit là HỆ QUẢ của hành-động-IN ⇒ gate đúng quyền PRINT (DocPerm print=1 sẵn cho persona vận hành). `CAP_SET_VERSION` = `v97.c30c69b8974d` (cap mới `asset.print`/`asset.qr.rotate`). |
| Rate limit | **`@rate_limit(limit=AC_LABEL_MARK_RATE_LIMIT, seconds=60, ip_based=True)` (Vòng 14 / BR-00-45)** — hằng RIÊNG `AC_LABEL_MARK_RATE_LIMIT = 10` (write-audit-amplification: 2×N ALE+audit/call → ngưỡng THẤP, **≤ `AC_QR_REGEN_RATE_LIMIT=10`**), **bucket RIÊNG** (cmd). Vượt → **429** NGOÀI/TRƯỚC `rbac.require` ⇒ **0 ALE `label_printed` + 0 IMM Audit Trail** (no side-effect), no-leak. Đóng bất đối xứng read-throttled-PDF / write-mark-unthrottled (mirror rotate BR-00-38). Xem §I.7c. |

**Mục đích:** FE gọi SAU khi người dùng thực sự bấm in (1 hoặc nhiều tem) → ghi 1 `Asset Lifecycle Event` `label_printed` + 1 `IMM Audit Trail` cho MỖI asset (audit trail in nhãn — NĐ98 truy xuất).

**Request body:** `{ "assets": ["AC-ASSET-2026-00001", "AC-ASSET-2026-00002"] }` (JSON list `AC Asset.name`).

**Response 200:**
```json
{ "success": true, "data": {
  "printed": ["AC-ASSET-2026-00001", "AC-ASSET-2026-00002"],
  "event_count": 2
} }
```

**Hợp đồng (CHỐT A3 — D3):**

| Quy tắc | Chi tiết |
|---|---|
| **1 event / asset / lần in** | Mỗi asset trong `assets` → ĐÚNG 1 `Asset Lifecycle Event` `event_type='label_printed'` + ĐÚNG 1 `IMM Audit Trail`. |
| **root_doctype / root_record** | `root_doctype='AC Asset'`, `root_record=<asset name>` (lifecycle event); `ref_doctype/ref_name='AC Asset'/<asset name>` (audit). |
| **Idempotent-an-toàn về SỐ bản ghi** | Gọi N lần in → N×len(assets) event — **đúng nghiệp vụ** "mỗi lần in 1 event" (KHÔNG dedup theo asset; in lại tem = sự kiện mới, đáng ghi). "Idempotent" ở đây nghĩa: KHÔNG sinh thừa/thiếu trong 1 call (1 asset 1 event), KHÔNG phải "gọi nhiều lần = 1 event". |
| **Token đảm bảo** | Trước khi ghi `label_printed`, mỗi asset gọi `ensure_asset_qr_token` (idempotent) — đảm bảo asset đã in được nhãn (có token). Token-less asset → sinh token (emit `qr_generated` 1 lần) rồi mới `label_printed`. |
| **Actor** | `frappe.session.user`. |

| Trường hợp | Mã | Ghi chú |
|---|---|---|
| Tất cả asset hợp lệ + có quyền | 200 | `printed` = list name, `event_count` = số event đã ghi |
| `len(assets) > _MAX_LABEL_BATCH` (=200) | **413** | `_err(<MSG_VI>, 413)` (BR-00-33) — payload-DoS cap; message VI cố định (vd `'Chỉ in tối đa 200 nhãn mỗi lần. Vui lòng chọn ít hơn.'`); KHÔNG ghi event/audit nào, KHÔNG leak asset name; chạy SAU `rbac.require`, TRƯỚC vòng `exists`/IDOR |
| Asset KHÔNG tồn tại (≥1 trong list) | **404** `AC-E001` | leak-safe, KHÔNG 500, KHÔNG đoán id nội bộ; KHÔNG ghi event nào (all-or-nothing — tránh audit lệch) |
| User KHÔNG có `asset.print` (Guest / role không-print) | **403** PermissionError | `require("asset.print")` — KHÔNG ghi `label_printed` (least-privilege D6); chặn TRƯỚC mọi write |
| User có `asset.print` | tiếp tục (200 nếu hợp lệ) | gate PRINT pass |
| Vendor user, ≥1 asset NGOÀI scope | **403** (`ErrorCode.FORBIDDEN`) | `assert_vendor_can_access("AC Asset", name)` mỗi asset; 403 toàn call, KHÔNG ghi event — IDOR GIỮ NGUYÊN |
| `assets` rỗng `[]`/`None` | **200** | `{printed: [], event_count: 0}` — KHÔNG 413, KHÔNG side-effect (hành vi hiện tại GIỮ) |

**Thứ tự gate (BẮT BUỘC — CHỐT vòng 22 / BR-00-33 + Vòng 14 / BR-00-45):** **`@rate_limit(AC_LABEL_MARK_RATE_LIMIT=10/60s/IP)` → 429 NGOÀI/TRƯỚC thân hàm (BR-00-45)** → `rbac.require("asset.print")` (403 nếu KHÔNG print) → **`names = _coerce_asset_names(assets)` (V10/D17 — coerce an toàn, KHÔNG raise/char-walk; coerce-`[]` → vòng exists rỗng → `_ok` no-side-effect)** → **CAP-CHECK `len(names) > _MAX_LABEL_BATCH` → 413** (hằng SSoT `services/imm00.py::_MAX_LABEL_BATCH = 200`, KHÔNG literal lặp) → validate tồn tại MỌI asset (404 nếu ≥1 thiếu) → `assert_vendor_can_access` MỖI asset (403 IDOR) → ghi event. **429 chạy TRƯỚC mọi gate (decorator) ⇒ vượt ngưỡng → 0 ALE `label_printed` + 0 IMM Audit Trail (no side-effect), no-leak.** Gate PRINT chạy SAU RL, ĐẦU TIÊN trong thân → user không-print KHÔNG dò được asset nào tồn tại; cap-check chạy SAU PRINT → KHÔNG lộ ngưỡng cho khách. `mark_label_printed` ghi 2 record/asset trong 1 transaction → cap chặn khuếch đại 1-request; rate-limit (BR-00-45) chặn flood NHIỀU request (write-audit-amplification). Bucket RIÊNG (cmd). Xem §I.7c.

**Atomicity:** validate WRITE + tồn tại + IDOR cho TẤT CẢ asset TRƯỚC khi ghi event nào (all-or-nothing) → tránh ghi nửa chừng rồi lỗi → audit chain lệch. `frappe.db.commit()` sau khi ghi đủ.

---

### `regenerate_asset_qr_token` — Sinh-lại / rotate mã QR (ADR-001 B item 2) — **NEW**

| Method | POST |
|---|---|
| Path | `assetcore.api.imm00.regenerate_asset_qr_token` |
| Auth | **AUTH-REQUIRED** — NĐ98 |
| Capability | **`asset.qr.rotate`** (gate `rbac.require("asset.qr.rotate")` đầu hàm) — **D6 (EXECUTED Vòng 3) đổi từ `asset.write`**: rotate = GHI (overwrite token + emit event/audit) ⇒ bind permtype "write" (`asset.qr.rotate`→(AC Asset,"write")). KHÔNG đủ với `asset.print` (in ≠ rotate). `CAP_SET_VERSION` = `v97.c30c69b8974d`. User chỉ-đọc/chỉ-print / Guest / điều dưỡng → **403**. |
| Rate limit | **`@rate_limit(limit=AC_QR_REGEN_RATE_LIMIT, seconds=60, ip_based=True)` (Vòng 27 B / BR-00-38)** — hằng RIÊNG `AC_QR_REGEN_RATE_LIMIT = 10` (THẤP hơn `AC_QR_RESOLVE_RATE_LIMIT=30`; rotate hiếm hơn quét), **bucket RIÊNG** (cache key gồm `cmd` — KHÔNG chung counter resolve/scan). Vượt → **429** NGOÀI/TRƯỚC `rbac.require` ⇒ **0 side-effect** (KHÔNG token mới, KHÔNG ALE, KHÔNG audit), no-leak. Đóng bất đối xứng read-throttled (BR-00-29) / write-rotate-unthrottled. |

**Mục đích:** Vô hiệu hoá QR bị lộ (in nhầm / chụp / rò rỉ) + cấp token MỚI. FE `AssetDetailView` nút "Sinh lại mã QR" (gate `can('asset.write')`) → BaseModal cảnh báo "thao tác này vô hiệu hoá mọi nhãn QR đã in" → xác nhận → gọi endpoint này → refetch asset + toast VI. **KHÁC `ensure_asset_qr_token`** (idempotent if-empty — KHÔNG overwrite token đang có).

**Request body:** `{ "asset": "AC-ASSET-2026-00001" }` (1 `AC Asset.name`).

**Response 200:**
```json
{ "success": true, "data": {
  "name": "AC-ASSET-2026-00001",
  "qr_url": "https://<site-host>/a/<NEW_token>"
} }
```

> **`qr_url` = deep-link MỚI** (token đã rotate). FE refetch để preview/nhãn (`get_asset_label_data`) phản ánh token mới. **KHÔNG trả token thô** trong envelope (FE chỉ cần `qr_url`).

**Hợp đồng (CHỐT B-2 — ADR D1/D3/D4):**

| Quy tắc | Chi tiết |
|---|---|
| **Token MỚI enumeration-safe, KHÁC token cũ** | `generate_qr_token()` (`secrets.token_urlsafe(16)`) + loop-guard `new != old`. **GHI ĐÈ** `qr_token` (`update_modified=False`) — KHÔNG idempotent (rotate LUÔN đổi). Collision-safe với UNIQUE index. |
| **Token CŨ chết** | Sau rotate: `resolve_qr_token(old)` → 404; `resolve_qr_token(new)` → asset đúng. Mọi nhãn QR đã in với token cũ → vô hiệu hoá (đúng mục tiêu). |
| **1 ALE `qr_regenerated` + 1 audit / lần rotate** | `emit_qr_regenerated` (KHÔNG nuốt lỗi). `root_doctype/ref_doctype='AC Asset'`, `root_record/ref_name=<asset name>`, `event_type='System'` (audit). `change_summary`/`notes` nêu rotate/vô-hiệu-hoá — **KHÔNG log token thô**. |
| **Actor** | `frappe.session.user`. |

| Trường hợp | Mã | Ghi chú |
|---|---|---|
| Asset hợp lệ + có `asset.write` | 200 | `{name, qr_url}` (qr_url = deep-link mới) |
| Asset KHÔNG tồn tại | **404** `AC-E001` | leak-safe, KHÔNG 500, KHÔNG đoán id; KHÔNG rotate / ghi event |
| User KHÔNG có `asset.qr.rotate` (chỉ read/print, Guest, điều dưỡng) | **403** PermissionError | `require("asset.qr.rotate")` — chỉ-đọc/chỉ-print KHÔNG rotate được; chặn TRƯỚC mọi write |
| User có `asset.qr.rotate` (write=1 — Super Admin/được cấp) | tiếp tục (200 nếu hợp lệ) | gate ROTATE pass |
| Vendor user, asset NGOÀI scope | **403** (`ErrorCode.FORBIDDEN`) | `assert_vendor_can_access("AC Asset", asset)`; KHÔNG rotate — IDOR GIỮ NGUYÊN |
| Vượt `AC_QR_REGEN_RATE_LIMIT` rotate/60s/IP (Vòng 27 B / BR-00-38) | **429** `RateLimitExceededError` | NGOÀI/TRƯỚC thân hàm → **KHÔNG side-effect** (0 token mới, 0 ALE `qr_regenerated`, 0 audit); body generic frappe, KHÔNG leak `name`/`asset_code`/`qr_token`. Bucket RIÊNG resolve/scan. FE map 429→`RATE_LIMITED`→message VI (FR-00-87/88). |

**Thứ tự gate (BẮT BUỘC):** `@rate_limit` (**429** NGOÀI thân hàm) → `rbac.require("asset.qr.rotate")` (403 nếu KHÔNG rotate-cap) → `frappe.db.exists` (404) → `assert_vendor_can_access` (403 IDOR) → rotate + emit + `frappe.db.commit()`. 429 chạy TRƯỚC mọi gate (decorator) ⇒ vượt ngưỡng → KHÔNG dò/ghi gì; sau RL, gate ROTATE ĐẦU TIÊN → user chỉ-đọc/chỉ-print KHÔNG dò được asset nào tồn tại.

**Audit (CHỐT B-2):** `regenerate_asset_qr_token` là **WRITE** → BẮT BUỘC ghi **1** ALE `qr_regenerated` + **1** IMM Audit Trail (NĐ98 truy xuất + ứng phó lộ token). `emit_qr_regenerated` **KHÔNG nuốt lỗi** (≠ `qr_generated` best-effort): lỗi ghi event → raise (422/500), KHÔNG để asset đổi token mà thiếu audit. **KHÔNG log token thô** (cũ/mới) vào audit chain.

---

### `create_asset` — Tạo Asset mới

| Method | POST |
|---|---|
| Path | `assetcore.api.imm00.create_asset` |
| Permission | IMM System Admin / Department Head / Operations Manager |

**Required body:** `asset_name, asset_code, device_model, asset_category, department, location`

Khi `device_model` được set → auto-fetch `risk_class`, `gmdn_code`, `pm_interval_days`, `is_calibration_required` từ IMM Device Model qua `fetch_from`.

> **GMDN propagation (BR-00-13/14):** `gmdn_code` trên AC Asset được populate tự động từ `device_model.gmdn_code`. Không nhập tay trực tiếp — đây là field `fetch_from`. Để thay đổi `gmdn_code` của Asset, đổi `device_model` hoặc cập nhật `gmdn_code` trên Device Model tương ứng.

**Response 200:** `{ "success": true, "data": { "name": "AC-ASSET-2026-00001" } }`

**Errors:** 409 `AC-E011` (trùng asset_code/serial_no), 422 validation.

---

### `update_asset` — Cập nhật Asset

| Method | POST |
|---|---|
| Path | `assetcore.api.imm00.update_asset` |

**Body:** `{ "name": "AC-ASSET-..." }` + bất kỳ field nào cần cập nhật (trừ `lifecycle_status`).

> Muốn đổi trạng thái vòng đời phải dùng `transition_status` (BR-00-02).

---

### `transition_status` — Đổi lifecycle_status

| Method | POST |
|---|---|
| Path | `assetcore.api.imm00.transition_status` |
| Permission | **`asset.write`** (gate `rbac.require("asset.write")` — CÂU LỆNH ĐẦU thân hàm) + **IDOR** `assert_vendor_can_access("AC Asset", name)` — **3 lớp MIRROR `get_asset`** (CR-WF-00-TRANSITION-AUTHZ, Vòng 39). Cap `asset.write`→(AC Asset,"write") qua DocPerm (KHÔNG hardcode role); ai được write=1 trên AC Asset (config /app, KHÔNG deploy code) mới đổi được trạng thái vòng đời. Xem `04 §II.1.7-AUTHZ` + `ADR-IMM00-TRANSITION-AUTHZ`. |

> **🔒 Bảo mật — 3 lớp theo thứ tự (parity `get_asset` — CR-WF-00-TRANSITION-AUTHZ, Vòng 39):**
> 0. `rbac.require("asset.write")` chạy **ĐẦU TIÊN** (TRƯỚC `frappe.db.exists`) → user thiếu DocPerm write AC Asset → `frappe.PermissionError` (**HTTP-403 status-line**). Gate bằng CAPABILITY (DocPerm), KHÔNG hardcode role-name (chống RBAC dead-gate). Chạy TRƯỚC `exists` → **no existence-oracle** (thiếu cap → 403 **KHÔNG 404**; user không dò được tài sản có tồn tại). `lifecycle_status` DB **KHÔNG đổi** (raise TRƯỚC mọi `db.set_value`).
> 1. `frappe.db.exists` → `_err(404)` leak-safe (name không tồn tại).
> 2. IDOR/vendor isolation: `assert_vendor_can_access("AC Asset", name)` → vendor ngoài scope → `ServiceError(FORBIDDEN)` → `_err(e.message, e.code)` = **in-handler HTTP-200 + Error envelope** (`error_code=FORBIDDEN`); `lifecycle_status` DB KHÔNG đổi. Try/except vendor-guard là khối RIÊNG, đóng TRƯỚC call `transition_asset_status` → KHÔNG chạm error-contract nghiệp vụ bên dưới (zero blast-radius).
> Sau 3 lớp: gọi `transition_asset_status(...)` (SERVICE **GIỮ NGUYÊN perm-free** — WO-complete IMM-08/09/11/12 gọi thẳng service, KHÔNG qua endpoint; gate CHỈ ở tầng endpoint).

**Body:**

```json
{
  "name": "AC-ASSET-2026-00001",
  "to_status": "Under Repair",
  "reason": "Incident IR-2026-0007 — tube cooling failure"
}
```

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "AC-ASSET-2026-00001",
    "lifecycle_status": "Under Repair"
  }
}
```

**Errors:** **403** (thiếu `asset.write` — cap-gate, status-line, KHÔNG 404), **403** (vendor ngoài scope — IDOR, in-handler envelope `FORBIDDEN`), 404 (asset not found), 422 (invalid transition — BR-00-02), 422 (NEG-09: chặn thanh lý khi asset đang `Under Maintenance/Under Repair/Calibrating`).

> **Error-contract (DONE-gate spec-contract) — cập nhật CR-WF-00-TRANSITION-AUTHZ (Vòng 39).** Handler `transition_status` (api/imm00.py) trả lỗi **nghiệp vụ** qua `_err(...)` = **in-handler HTTP-200 + Error envelope** (`{success:false, error_code, message}`), KHÔNG `raise→HTTP-4xx`: `InvalidAssetTransition` (state-machine BR-00-02 **hoặc** NEG-09) → `_err(str(e), BAD_STATE)`; `ValidationError` → `_err(str(e), VALIDATION)`; asset∄ → `_err(..., 404)`; **vendor IDOR** → `_err(e.message, e.code=FORBIDDEN)`. Cột "422/404/FORBIDDEN" ở trên là `error_code` **trong envelope** (không phải status-line).
>
> **2 loại 403 (parity `get_asset` — SUPERSEDE dự đoán cũ):**
> 1. **dispatcher-403 (status-line HTTP-403):** (a) guest/no-token → Frappe re-auth (`@whitelist(methods=["POST"])` no `allow_guest`); **(b) thiếu cap `asset.write`** → `rbac.require` gọi `frappe.throw(..., frappe.PermissionError)` KHÔNG bắt trong handler → Frappe dispatcher map thành **HTTP-403 status-line** (KHÔNG 200-envelope).
> 2. **in-handler HTTP-200 Error envelope (`error_code=FORBIDDEN`):** vendor IDOR (`assert_vendor_can_access`→`ServiceError`→`_err`).
>
> ⚠️ **Self-Correction:** bản trước dự đoán "nếu thêm RBAC cap thì cap-403 phải là in-handler HTTP-200 envelope, KHÔNG raise". Dự đoán này **SUPERSEDED** — quyết định là **raise-based** (parity `get_asset` §III.1). Lý do cơ-chế (khớp ADR-IMM00-OAS-NOTIFPREF-B): cap-403 sinh bởi `rbac.require`→`PermissionError` ⇒ status-line 403 (như MỌI endpoint `asset.*`: `get_asset`/`get_asset_action_meta`/`resolve_qr_token`/label/rotate). `setEmailEnabled` dùng 200-envelope vì gate đó là ServiceError admin-check (cơ-chế khác), KHÔNG `rbac.require`. Ép `rbac.require` thành 200-envelope sẽ DIVERGE khỏi sibling `get_asset` mà đề mục yêu cầu MIRROR + phá bộ test parity `asset.*`. Xem `ADR-IMM00-TRANSITION-AUTHZ`.
>
> **Reconcile Vòng 32 (CR-WF-00 — xem `04 §II.1.7-RECON`):** REST endpoint này cho phép MỌI cạnh ∈ `_VALID_ASSET_TRANSITIONS` (map). Sau reconcile, Desk-workflow ĐỒNG BỘ thêm 2 CTA `→Out of Service` (từ `Commissioned`, `Under Maintenance`); 5 cạnh `→Decommissioned` là EXCEPTION_EDGES (thanh lý đi qua closure IMM-14, KHÔNG phải nút Desk/endpoint tự do — endpoint này gặp IMM-14 gate `ServiceError` nếu chưa có `Asset Decommission` approved).

> **Khi `to_status='Decommissioned'` (BR-00-24 / RC-07 — Vòng 8):** ngoài đổi status + sinh event `decommissioned`, service tự **chốt sổ khấu hao**: hủy MỌI kỳ `AC Asset Depreciation Schedule.status='Pending'` → `'Cancelled'` (`Executed` bất biến). Nếu hủy ≥1 kỳ → sinh thêm 1 Asset Lifecycle Event `event_type='depreciation_stopped'` + 1 IMM Audit Trail `System`. Response shape KHÔNG đổi (vẫn `{name, lifecycle_status}`) — hệ quả chỉ phản ánh qua `get_depreciation_schedule` (`pending_periods=0` sau đó) và `get_asset_timeline` (có thêm event `depreciation_stopped`). Best-effort: lỗi audit KHÔNG làm transition fail.

> **Khi `to_status='Out of Service'` (BR-00-25 / RC-08 — Vòng 9):** ngoài đổi status + sinh event `out_of_service`, service **TẠM DỪNG** khấu hao: trong suốt thời gian asset Out of Service, executor `run_due_depreciation` KHÔNG trích kỳ nào của asset (`accumulated_depreciation`/`current_book_value` bất biến). KHÔNG hủy kỳ (khác Decommissioned) — kỳ Pending GIỮ nguyên, chờ dời lịch khi khôi phục. Best-effort: ghi thêm 1 ALE `out_of_service` note `'depreciation paused'`. Response shape KHÔNG đổi (`{name, lifecycle_status}`).

> **Khi `to_status='Active'` từ `prev_status='Out of Service'` (BR-00-25 / RC-08 — Vòng 9; nhãn event sửa RC-09 / BR-00-27 — Vòng 14):** service sinh **ĐÚNG 1** Asset Lifecycle Event `event_type='restored'` (KHÔNG `activated`) cho transition này — do `transition_asset_status` emit theo (from=`Out of Service`, to=`Active`) qua `_lifecycle_event_for(to, from)`. Ngoài đổi status, service **DỜI LỊCH** khấu hao: mọi kỳ `status='Pending'` được dời `scheduled_date += oos_days` (`oos_days = restore_date − oos_start_date`), GIỮ NGUYÊN `depreciation_amount`/`period_number`/số kỳ; `Executed`/`Cancelled` bất biến. **Diệt phantom catch-up:** các kỳ idle quá hạn trong lúc OoS KHÔNG bị `run_due_depreciation(today)` trích bù 1 lần — chỉ kỳ đến hạn SAU restore (sau dời) mới trích. **RC-09 (Vòng 14):** helper RESCHEDULE **KHÔNG còn** emit ALE `restored` (trước đây ⇒ double-emit) — chỉ best-effort 1 IMM Audit Trail `State Change` (note nêu số kỳ dời + oos_days). ⟹ **bất kể** có kỳ Pending để dời hay không, transition luôn sinh ĐÚNG 1 `restored` + 0 `activated` (consistency). `oos_start_date` không xác định (thiếu downtime log + ALE) → no-op an toàn, KHÔNG raise. Response shape KHÔNG đổi (`{name, lifecycle_status}`) — hệ quả phản ánh qua `get_depreciation_schedule` (`scheduled_date` các kỳ Pending đã dời) + `get_asset_timeline` (ĐÚNG 1 event `restored`). **Lưu ý:** chỉ nhánh `Active` **từ** `Out of Service` mới dời lịch + nhãn `restored`; `Active` từ `Under Repair`/`Calibrating`/`Under Maintenance`/`Commissioned` KHÔNG dời + giữ nhãn `activated` (các đường đó không pause khấu hao).

---

### `get_asset_timeline` — Lịch sử vòng đời

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.get_asset_timeline` |

**Params:** `name, page=1, page_size=50`

Trả về paginated `Asset Lifecycle Event[]` sorted desc theo timestamp.

> **AC-CR-100 (2026-07-28) — hợp đồng ĐỌC đầy đủ ở §III.25 (cuối Phần III, file này)**: shape response **KHÔNG đổi** (`data.pagination` + `data.items`, `pagination.total` là số công bố cho người dùng); **đổi duy nhất** là `ORDER BY` thành **tiền định** `"timestamp desc, name desc"` (`api/imm00.py:293`) — thiếu tiebreaker thì hai trang liền kề **lặp/sót** im lặng (BR-00-TL-08). Nghĩa vụ client (không cast, lật `page`, APPEND + dedupe theo `name`, tách 3 trạng thái) ở §III.25.3.

---

### `validate_for_operations` — Kiểm tra thiết bị hoạt động được

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.validate_for_operations` |

**Params:** `?name=AC-ASSET-...`

**Response 200:** `{ "valid": true }` hoặc `{ "valid": false, "reason": "..." }`

---

### `get_asset_kpi` — KPI thiết bị

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.get_asset_kpi` |

**Params:** `?name=AC-ASSET-...`

**Response 200:** `{ uptime_pct, mtbf_days, mttr_hours, pm_compliance_pct, total_repair_cost, next_pm_date, next_calibration_date, byt_reg_expiry }`

---

### `delete_asset` — Xóa Asset

| Method | POST |
|---|---|
| Path | `assetcore.api.imm00.delete_asset` |

**Body:** `{ "name": "AC-ASSET-..." }`

> Endpoints không còn tồn tại (được loại khỏi spec): `search_assets_by_udi`, `get_assets_due_pm`, `get_asset_lifecycle_history` — không có trong `api/imm00.py`.

---

## III.2. AC Supplier (4 endpoints)

### `list_suppliers`

GET `assetcore.api.imm00.list_suppliers`

Filters: `vendor_type`, `is_active`, `contract_end` (operator syntax).

### `get_supplier`

GET `assetcore.api.imm00.get_supplier?name=AC-SUP-2026-0001`

Trả chi tiết + `authorized_technicians` child table.

**Response 200 example:**

```json
{
  "success": true,
  "data": {
    "name": "AC-SUP-2026-0001",
    "supplier_name": "Siemens Healthineers VN",
    "vendor_type": "Service Provider",
    "contract_end": "2026-12-31",
    "authorized_technicians": [
      { "technician_name": "Nguyễn Văn A", "cert_no": "SIE-TECH-001", "cert_expiry": "2027-06-30" }
    ]
  }
}
```

### `create_supplier`

POST. Body required: `supplier_name, vendor_type`.

Nếu `vendor_type = "Calibration Lab"` mà thiếu `iso_17025_cert` → warning (không block) trả `data.warnings[{code: "AC-E006", message: "..."}]`.

### `update_supplier`

POST `assetcore.api.imm00.update_supplier`. Body: `name` (param) + fields cần cập nhật.

---

## III.3. Location / Department / Asset Category (9 endpoints)

> **Thực tế từ code:** Mỗi entity có GET (list) + GET (detail) + POST (create) + POST (update) + POST (delete) = 5 endpoints/entity. Một số đã implement đầy đủ CRUD.

### `list_locations`

GET `assetcore.api.imm00.list_locations` — Params: `parent` (optional). Trả flat list (`_ok(items)`, `order_by lft asc`) với fields: `name, location_name, location_code, parent_location, is_group, clinical_area_type, infection_control_level, power_backup_available, dept_head, contact_phone, notes` (+ enrich `parent_location_name` từ AC Location.location_name, `dept_head_name` từ User.full_name). `is_group`/`power_backup_available` = **Check** (`get_list` trả int 0/1); `clinical_area_type`/`infection_control_level` = **Select leading-blank** (`''` hợp lệ). Handler bare `@frappe.whitelist()` — KHÔNG `handle()`/`try-except`/`_err` ⇒ LUÔN `_ok` (single-shape).

> **Đổi schema (2026-05-19):** 3 trường liên hệ cũ (`emergency_contact`, `dept_head`, `technical_contact`) được gộp còn 2: `dept_head` (Link → User, label "Người phụ trách") + `contact_phone` (Data, `fetch_from: dept_head.phone`, label "Số liên hệ"). Migrate qua patch `v3_1.007_ac_location_simplify_contacts`. Xem README §Changelog.

> **Cross-ref Mobile-BE — `list_locations` (ref-data dropdown "Vị trí" lọc Asset List, CR-10b — đối xứng `list_departments` CR-10a):** Endpoint LIVE này là **nguồn danh-mục Vị trí** cho dropdown lọc màn Asset List mobile — thay chip raw Link-id `AC-LOC-xxxx` bằng `location_name` (VI). Contract mobile (`operationId: listLocations`, **200 = SINGLE-shape `LocationListEnvelope` {success, data: LocationListItem[]}** — KHÔNG `oneOf[Env,Error]` vì handler 0 `_err`, mirror `listDepartments`/`listTransfers`; `LocationListItem` CLOSED **13-field** `required[name]`; `is_group`/`power_backup_available` = `integer enum[0,1]` né int-vs-bool trap; `clinical_area_type`/`infection_control_level` = `string nullable` KHÔNG `enum` (Select leading-blank ⇒ `''` hợp lệ); param `LocationParent` query optional string no-default; slot `{200,401,403}` guest dispatcher-403) đặc tả tại **mobile-contract** [`docs/mobile/04-api-contract.md` §8.32](../mobile/04-api-contract.md) + [`docs/mobile/openapi/assetcore-mobile.openapi.yaml`](../mobile/openapi/assetcore-mobile.openapi.yaml) + [ADR-MOBILE-026](../mobile/ADR-MOBILE-026.md). **CONTRACT-ONLY** — `list_locations` LIVE, mobile chỉ bồi OAS mirror (KHÔNG đụng `.py`). **One-Version Rule**: 1 endpoint phục vụ cả web SPA (`frontend/`) lẫn mobile codegen.

### `get_location`

GET `assetcore.api.imm00.get_location?name=...`

### `create_location`

POST. Body: `location_name` (required) + optional fields.

### `update_location`

POST. Body: `{ "name": "...", ...fields }`

### `delete_location`

POST. Body: `{ "name": "..." }` — block nếu có asset đang link.

### `list_departments`

GET `assetcore.api.imm00.list_departments` — Params: `parent` (optional). Trả flat list (`_ok(items)`, `order_by lft asc`) với fields: `name, department_name, department_code, parent_department, is_group, dept_head, phone, email, is_active` (+ enrich `parent_department_name` từ AC Department.department_name, `dept_head_name` từ User.full_name). `is_group`/`is_active` = **Check** (int 0/1). Handler bare `@frappe.whitelist()` — KHÔNG `handle()`/`try-except`/`_err` ⇒ LUÔN `_ok` (single-shape).

> **Cross-ref Mobile-BE — `list_departments` (ref-data dropdown "Khoa/Phòng" lọc Asset List, CR-10a):** Endpoint LIVE này là **nguồn danh-mục Khoa/Phòng** cho dropdown lọc màn Asset List mobile — thay chip raw Link-id `AC-DEPT-xxxx` bằng `department_name` (VI). Contract mobile (`operationId: listDepartments`, **200 = SINGLE-shape `DepartmentListEnvelope` {success, data: DepartmentListItem[]}** — KHÔNG `oneOf[Env,Error]` vì handler 0 `_err`, mirror `listTransfers`/`getAssetPmHistory`; `DepartmentListItem` CLOSED 11-field `required[name]`; `is_group`/`is_active` = `integer enum[0,1]` né int-vs-bool trap; param `DepartmentParent` query optional string no-default; slot `{200,401,403}` guest dispatcher-403) đặc tả tại **mobile-contract** [`docs/mobile/04-api-contract.md` §8.31](../mobile/04-api-contract.md) + [`docs/mobile/openapi/assetcore-mobile.openapi.yaml`](../mobile/openapi/assetcore-mobile.openapi.yaml) + [ADR-MOBILE-025](../mobile/ADR-MOBILE-025.md). **CONTRACT-ONLY** — `list_departments` LIVE, mobile chỉ bồi OAS mirror (KHÔNG đụng `.py`). **One-Version Rule**: 1 endpoint phục vụ cả web SPA (`frontend/`) lẫn mobile codegen.

### `get_department` / `create_department` / `update_department` / `delete_department`

Pattern tương tự locations.

### `list_asset_categories`

GET `assetcore.api.imm00.list_asset_categories` — **Flat list, ZERO param** (danh-mục PHẲNG, KHÔNG tree ⇒ KHÔNG `parent`). Trả `_ok(items)`, `order_by category_name asc`. Fields (**16, VERBATIM `fields=[...]`@`imm00.py:1395-1401`, KHÔNG enrich**): `name, category_name, category_code, description, gmdn_code, gmdn_term, default_pm_required, default_pm_interval_days, default_calibration_required, default_calibration_interval_days, default_depreciation_method, total_depreciation_months, depreciation_frequency, default_residual_value_pct, has_radiation, is_active`. Typing: 4× **Check** (`default_pm_required`/`default_calibration_required`/`has_radiation`/`is_active` — `get_list` trả int 0/1, KHÔNG `_norm_check`); 3× **Int** + 1× **Percent** (`default_residual_value_pct`); 2× **Select** — `default_depreciation_method` = leading-blank (`''` hợp lệ), `depreciation_frequency` = bounded `Monthly|Quarterly|Yearly`. Handler bare `@frappe.whitelist()` — KHÔNG `handle()`/`try-except`/`_err` ⇒ LUÔN `_ok` (single-shape).

> **[SELF-CORRECTION 2026-07-11]** Field-list cũ ghi **14** field (thiếu `category_code` + `gmdn_term`) và sai thứ-tự — đã đồng-bộ về **16** field VERBATIM handler `fields=[...]`. Grounded lại @source + DB.

> **Cross-ref Mobile-BE — `list_asset_categories` (ref-data dropdown "Nhóm/Loại thiết bị" lọc Asset List, CR-10c — hoàn tất bộ-ba sau `list_departments` CR-10a + `list_locations` CR-10b):** Endpoint LIVE này là **nguồn danh-mục Nhóm/Loại thiết bị** cho dropdown lọc màn Asset List mobile — thay chip raw Link-id `CAT-####` bằng `category_name` (VI). Contract mobile (`operationId: listAssetCategories`, **ZERO param** — live-sig 0-arg, KHÁC `list_departments`/`list_locations` có `parent`; **200 = SINGLE-shape `AssetCategoryListEnvelope` {success, data: AssetCategoryListItem[]}** — KHÔNG `oneOf[Env,Error]` vì handler 0 `_err`, mirror `listDepartments`/`listLocations`; `AssetCategoryListItem` CLOSED **16-field** `required[name]`, **0 enrich**; 4 Check = `integer enum[0,1]` né int-vs-bool trap; 3 Int = `integer nullable` + `default_residual_value_pct` = `number nullable`; `default_depreciation_method` = `string nullable` KHÔNG `enum` (Select leading-blank, DB `''`×105/131); `depreciation_frequency` = `string enum [Monthly,Quarterly,Yearly]` (Select bounded, DB `Monthly`×131/131 BA-verify); slot `{200,401,403}` guest dispatcher-403; tag `asset` đối-xứng 2 sibling) đặc tả tại **mobile-contract** [`docs/mobile/04-api-contract.md` §8.34](../mobile/04-api-contract.md) + [`docs/mobile/openapi/assetcore-mobile.openapi.yaml`](../mobile/openapi/assetcore-mobile.openapi.yaml) + [ADR-MOBILE-028](../mobile/ADR-MOBILE-028.md). **CONTRACT-ONLY** — `list_asset_categories` LIVE, mobile chỉ bồi OAS mirror (KHÔNG đụng `.py`). **One-Version Rule**: 1 endpoint phục vụ cả web SPA (`frontend/`) lẫn mobile codegen.

### `get_asset_category` / `create_asset_category` / `update_asset_category` / `delete_asset_category`

Pattern tương tự locations.

`create_asset_category` body: `category_name` (required) + optional fields bao gồm `gmdn_code`.

> `gmdn_code` tại đây là **nguồn kế thừa** — tất cả `IMM Device Model` thuộc danh mục này sẽ kế thừa giá trị này khi tạo mới (nếu chưa nhập tay). Xem BR-00-13.

---

## III.4. IMM Device Model (4 endpoints)

### `list_device_models`

GET. Filters: `manufacturer`, `asset_category`, `class` (I/II/III), `risk_class`, `gmdn_code`, `is_active`.

### `get_device_model`

GET `?name=IMM-MDL-2026-0001` → chi tiết + `spare_parts_list` child table.

### `create_device_model`

POST. Required: `model_name, manufacturer, asset_category, class`.

Validation BR-00-01: `class ↔ risk_class` mapping bắt buộc.

> **GMDN inheritance (BR-00-13):** Nếu `gmdn_code` không được cung cấp trong body, hệ thống tự động kế thừa từ `asset_category.gmdn_code` tại `before_insert`. Người dùng có thể override bằng cách truyền `gmdn_code` tường minh.

### `update_device_model`

POST `assetcore.api.imm00.update_device_model`. Body: `name` (param) + fields cần cập nhật.

---

## III.5. IMM SLA Policy (5 endpoints — full CRUD + lookup)

### `list_sla_policies`

GET `assetcore.api.imm00.list_sla_policies` — Params: `priority, risk_class, is_active` (tất cả optional). Trả không paginated. Fields: `name, policy_name, priority, risk_class, is_default, is_active, response_time_minutes, resolution_time_hours`.

### `get_sla_policy` — Lấy chi tiết 1 policy

GET `assetcore.api.imm00.get_sla_policy?name=...` — Trả full policy fields.

### `resolve_sla_policy` — Lookup SLA theo priority × risk_class

GET `assetcore.api.imm00.resolve_sla_policy?priority=P2+Urgent&risk_class=High`

Logic: exact match `(priority, risk_class)` → fallback `is_default=1` cùng priority.

**Response 200:**

```json
{
  "success": true,
  "data": {
    "name": "SLA-P2-High",
    "priority": "P2 Urgent",
    "risk_class": "High",
    "response_time_minutes": 60,
    "resolution_time_hours": 8,
    "is_default": 0
  }
}
```

**Errors:** 404 nếu không tìm được cả exact lẫn default.

### `create_sla_policy` / `update_sla_policy` / `delete_sla_policy`

POST CRUD. Body check fields (`is_active`, `is_default`) được coerce sang int 0/1 tự động.

---

## III.6. IMM Audit Trail (3 endpoints — read-only)

> Audit Trail là read-only qua API. Mọi record sinh từ service `log_audit_event()` nội bộ.

### `list_audit_trail`

GET `assetcore.api.imm00.list_audit_trail`. Params: `asset? (AC Asset name), q? (free-text search), page, page_size`.

Response items: `name, asset, asset_name, event_type, actor, change_summary, from_status, to_status, ref_doctype, ref_name, timestamp, hash`.

### `get_audit_entry`

GET `assetcore.api.imm00.get_audit_entry?name=IMM-AUD-...`. Chi tiết full payload.

### `verify_chain`

GET `assetcore.api.imm00.verify_chain?asset=AC-ASSET-...`

Duyệt toàn bộ audit trail của asset, tính lại SHA-256 chain.

**Response 200:** `{ "valid": true/false, "count": N, "broken_at": "IMM-AUD-..." (nếu có) }`

**Response 200 (OK):**

```json
{
  "success": true,
  "data": {
    "asset": "AC-ASSET-2026-00001",
    "verified": true,
    "total_records": 137,
    "first_record": "IMM-AUD-2024-0000001",
    "last_record": "IMM-AUD-2026-0001234"
  }
}
```

**Response 200 (tamper detected):**

```json
{
  "success": true,
  "data": {
    "verified": false,
    "tampered_at": "IMM-AUD-2025-0000789",
    "expected_hash": "a1b2c3...",
    "actual_hash": "ffee00..."
  }
}
```

Kể cả tampered vẫn trả HTTP 200 — frontend xử lý alert. Service tự tạo 1 record `"Integrity Violation"` (`AC-E010`) và email QA Officer.

---

## III.7. IMM CAPA Record (5 endpoints)

### `list_capas`

GET `assetcore.api.imm00.list_capas`. Filters: `status, capa_type, asset`. Paginated.

**Virtual drill filters (SoT — KHÔNG inline literal):**
- `not_closed=1` → **conjoin (AND) SoT `_open_capa_filter()`** (services/imm00): `status NOT IN ('Closed')`. Drill total BẰNG KPI `capa_open` (dashboard.py) == scorecard `capa_open_count` == quality-dash `capa_open` == `get_capa_aging.total_open`, byte-for-byte trên cùng dataset (khi KHÔNG có explicit status). CAPA `Overdue` VẪN nằm trong tập (open ⊇ overdue) → count bất biến sau cron flip Open→Overdue.
- `overdue=1` → **conjoin (AND) SoT `_overdue_capa_filter()`**: `status NOT IN ('Closed') AND due_date IS NOT NULL AND due_date < today` (strict `<`). Khi cả hai cờ cùng gửi, `overdue` thắng `not_closed` (overdue ⊂ open) — chỉ áp `_overdue_capa_filter()`.

**BR-00-16 — Filter composition (conjoin, KHÔNG clobber):** explicit `status` (giá trị enum, vd `Overdue`/`Open`/`Closed`) và virtual filter `not_closed`/`overdue` đặt điều kiện trên CÙNG field `status`. Một Frappe **dict-filter KHÔNG biểu diễn được 2 điều kiện trên cùng 1 field** (key trùng → ghi đè). Do đó endpoint PHẢI build filter dạng **list-of-conditions** `[[doctype, field, op, value], ...]` để cả `["status", "=", status]` (explicit) VÀ `["status", "not in", ["Closed"]]` (virtual) cùng tồn tại = **AND thật**. TUYỆT ĐỐI KHÔNG `dict.update(_open_capa_filter())` đè lên `filters["status"]` (= clobber → đổi AND thành either-or, trả nhầm full open-set).

| Request | Tập kết quả (AND đúng) | Lý do |
|---|---|---|
| `?not_closed=1&status=Overdue` | `(status NOT IN [Closed]) ∧ (status == 'Overdue')` = các CAPA `Overdue` | giao 2 điều kiện; KHÔNG ra full open-set |
| `?not_closed=1&status=Closed` | `(status NOT IN [Closed]) ∧ (status == 'Closed')` = **0 rows** | tập rỗng — minh chứng AND thật, không bị clobber thành either-or |
| `?overdue=1&status=Open` | `(due_date<today flip→'Overdue') ∧ (status == 'Open')` = **0 rows** | `Open` không nằm trong tập đã flip `Overdue` → AND không giao |
| `?not_closed=1` (không status) | `_open_capa_filter()` byte-for-byte | no-regression — khớp KPI `capa_open` |
| `?overdue=1` (không status) | `_overdue_capa_filter()` byte-for-byte | no-regression — khớp KPI `capa_overdue` (round 10/11) |

**INVARIANT count==drill:** `pagination.total` (qua `frappe.db.count`) và `items` (qua `frappe.get_list`) PHẢI dùng CÙNG bộ filter đã conjoin cho MỌI tổ hợp `{status} × {not_closed | overdue | none}` → `pagination.total == len(items)` (trên cùng trang khi đủ chứa). FE `CAPAListView` gửi `status=CODE` + `not_closed/overdue` đồng thời → số "Tổng N hồ sơ" == số dòng render (không còn "chọn status=Quá hạn mà vẫn 117").

### `get_capa`

GET `assetcore.api.imm00.get_capa?name=CAPA-...` → full CAPA fields.

### `open_capa` — Tạo CAPA mới

POST `assetcore.api.imm00.open_capa`. Body required: `asset, severity, description, responsible`. Optional: `source_type (default: Nonconformance), source_ref, due_days (default: 30)`.

**Response 200:** `{ "success": true, "data": { "name": "CAPA-2026-00007" } }`

### `close_capa_record` — Đóng CAPA

POST `assetcore.api.imm00.close_capa_record`. Body: `name` (param) + `root_cause, corrective_action, preventive_action` (required) + `effectiveness_check` (**bắt buộc để đóng** — phải = `Effective`; xem cổng VR-06/VR-07).

```json
{
  "root_cause": "Worn bearing in cooling pump",
  "corrective_action": "Replaced bearing per OEM SOP",
  "preventive_action": "Shorten PM interval from 6m to 3m",
  "effectiveness_check": "Effective"
}
```

> **round 12 — `effectiveness_check` là enum đóng cổng, KHÔNG phải free-text.** Giá trị hợp lệ: `Effective` / `Partially Effective` / `Not Effective`. CHỈ `Effective` cho phép đóng (VR-07). null/rỗng → VR-06 chặn.

**Response 200:** `{ "name": "CAPA-...", "status": "Closed" }`

**Errors:**
- `422 VALIDATION` — thiếu `root_cause / corrective_action / preventive_action` (BR-00-08). *(check sớm, message "Thiếu trường bắt buộc: ...")*.
- `422 VALIDATION` + `message_code: "FIN-007"` — **round 12 (cổng hiệu quả):**
  - `effectiveness_check` null/thiếu → VR-06: *"Phải xác minh hiệu quả (effectiveness_check) trước khi đóng CAPA."* CAPA KHÔNG chuyển Closed, KHÔNG submit.
  - `effectiveness_check ∈ {Not Effective, Partially Effective}` → VR-07: *"effectiveness_check phải = 'Effective' để đóng CAPA"*. KHÔNG đóng.

> **BE delta bắt buộc (round 12):** `api/imm00.py::close_capa_record` hiện **chỉ** `except frappe.exceptions.ValidationError` (line 1020) → `ServiceError` từ `assert_capa_effectiveness_gate` sẽ KHÔNG bị bắt và thoát ra 500. PHẢI thêm `except ServiceError as e: return _err(e.message, e.code, message_code=e.message_code)` **trước** nhánh `ValidationError`. Như vậy envelope trả `code=VALIDATION` (422) + `message_code=FIN-007` → FE match được.

### `list_overdue_capas`

GET `assetcore.api.imm00.list_overdue_capas`. Paginated. **Filter = SoT `_overdue_capa_filter()`** (services/imm00): `status NOT IN ('Closed') AND due_date IS NOT NULL AND due_date < today` (strict `<`; `due_date == today` CHƯA quá hạn). KHÔNG inline predicate. Drill rows BẰNG KPI `capa_overdue` (dashboard.py) và `imm16.get_overdue_actions().overdue_capas` trên cùng dataset. CAPA status `Overdue` VẪN xuất hiện (NOT IN Closed) → count bất biến sau cron flip.

---

## III.8. Asset Lifecycle Event (2 endpoints — read-only)

> Read-only. Event sinh tự động bởi service `create_lifecycle_event()` / `transition_asset_status()`.

### `list_lifecycle_events`

GET `assetcore.api.imm00.list_lifecycle_events`. Params: `asset` (required), `page, page_size, event_type` (optional).

Event types (từ `_lifecycle_event_for()` trong services/imm00.py): `activated, commissioned, pm_started, repair_opened, calibration_started, out_of_service, decommissioned, restored, transferred`. Ngoài state-change, các event khấu hao sinh trực tiếp: `depreciated` (cron chạy kỳ), `depreciation_rules_inherited` (kế thừa luật từ Category), `depreciation_stopped` (**MỚI Vòng 8 / BR-00-24** — thanh lý hủy kỳ Pending còn lại). Toàn bộ giá trị này PHẢI nằm trong Select `event_type` của DocType `Asset Lifecycle Event`.

### `get_lifecycle_event`

GET `assetcore.api.imm00.get_lifecycle_event?name=...` → full event fields.

---

## III.9. Incident Report (6 endpoints)

### `list_incidents`

GET `assetcore.api.imm00.list_incidents`. Params: `status, severity, asset, page, page_size`.

### `get_incident`

GET `assetcore.api.imm00.get_incident?name=IR-...` → full Incident fields.

### `create_incident`

POST `assetcore.api.imm00.create_incident`. Required: `asset, severity, incident_type, description`.

> 🔒 **AC-CR-90 (vòng 4/5) — bịt lỗ ghi.** Hiện trạng verify @source 2026-07-28 (`api/imm00.py::create_incident`): **0** cap-gate · **0** kiểm tra thiết bị tồn tại · `doc.update({k: v for k, v in form_dict.items() if k not in ("cmd","doctype")})` ⇒ **mọi** tài khoản đăng nhập tạo được `Incident Report`, gán **bất kỳ** field nào (kể cả `status`/`reported_by`/`reported_to_byt`), trỏ vào mã thiết bị **không tồn tại**. Đây là đường ghi **song song** với `api/imm12.py::report_incident` (đường có gác). Quyết định: [ADR §12 D-CR4-7](./ADR-IMM00-CONNECTIONS-TREE.md) · luật: [`02` BR-00-CONN-33](./02_Analysis_Design.md).

**Hợp đồng SAU vòng 4 (3 tầng gác, theo đúng thứ tự):**

| # | Gác | Hành vi khi vi phạm | Bất biến |
|---|---|---|---|
| 1 | `rbac.require("corrective.create")` — **câu lệnh ĐẦU TIÊN** của thân hàm (khuôn nhà `api/imm00.py`, 42 call-site) | `frappe.PermissionError` → **403** | `count("Incident Report")` **trước == sau** |
| 2 | Thiếu trường bắt buộc (`asset`/`severity`/`incident_type`/`description`) | envelope `success=false`, `code=VALIDATION` — **GIỮ hành vi cũ** | — |
| 3 | `asset` **không tồn tại** | envelope `success=false`, `code=NOT_FOUND`, **HTTP-200 in-envelope** (KHÔNG để `doc.insert()` ném FK → HTTP-417 thô) | `count("Incident Report")` **trước == sau** |

**Whitelist field (tập ĐÓNG — khoá ngoài tập bị bỏ IM LẶNG, không raise):**
`asset` · `incident_type` · `severity` · `description` · `fault_code` · `clinical_impact` · `workaround_applied` · `patient_affected` · `patient_impact_description` · `immediate_action` · `occurred_datetime` · `linked_repair_wo`.

**CẤM TUYỆT ĐỐI nhận từ client:** `status` · `reported_by` · `reported_at` · `docstatus` · `workflow_state` · `name` · `owner` · `rca_record` · `reported_to_byt` — server quyết định; nhận từ client = **giả mạo vết audit** (NĐ98 đòi vết sự cố toàn vẹn, truy vết được).

> ⚠️ **Ngoài phạm vi vòng 4 (đã ghi backlog, ADR §12.9):** `update_incident` mang **cùng** khuyết tật (`doc.update(form_dict)` mở + 0 cap-gate) — **KHÔNG** sửa trong vòng này. Và endpoint này trùng chức năng với `report_incident` (khác: không sinh Lifecycle Event, không audit trail, không idempotency) ⇒ hướng gộp/gỡ là CR riêng.

### `update_incident`

POST `assetcore.api.imm00.update_incident`. Body: `name` (param) + fields cần cập nhật.

### `submit_incident`

POST `assetcore.api.imm00.submit_incident`. Body: `{ "name": "IR-..." }`

**Response 200:** `{ "name": "IR-...", "status": "..." }` (status từ doc sau khi submit).

**Errors:** 422 nếu đã submit rồi.

### `delete_incident`

POST `assetcore.api.imm00.delete_incident`. Body: `{ "name": "IR-..." }`.

> **Không còn tồn tại:** `close_incident` — không có trong `api/imm00.py`. Đóng Incident thực hiện qua `update_incident` + `submit_incident`.

---

## III.10. (Đã loại bỏ — GMDN Status)

> **Note (2026-05-19):** Nhóm endpoint quản lý trạng thái sử dụng GMDN (cũ) đã bị loại bỏ cùng field tương ứng trên `AC Asset`. Quản lý thiết bị nay theo `gmdn_code`. Lọc thiết bị qua `list_assets?gmdn_code=...`. Tham chiếu: [docs/res/analysis/gmdn-asset-category-analysis.md](../res/analysis/gmdn-asset-category-analysis.md) §6.

---

## III.12. Asset Transfer (6 endpoints)

### `list_transfers` / `get_transfer` / `create_transfer` / `delete_transfer`

CRUD cơ bản. `delete_transfer` thực ra là cancel (chỉ khi Pending/Rejected).

### `approve_transfer` / `reject_transfer` / `receive_transfer`

Workflow endpoints — POST với body `{ "name": "..." }`.

> **📱 Cross-ref Mobile-BE — `receive_transfer` (xác nhận tiếp nhận thiết bị điều chuyển, transfer WRITE-action ĐẦU TIÊN, CR-TRANSFER-RECV-01 2026-07-14):** Endpoint `api/imm00.receive_transfer(name, handover_notes="")` (`@frappe.whitelist(methods=["POST"])` @`imm00.py:2600` no-`allow_guest` → guest dispatcher-403; **KHÔNG `rbac.require` in-handler** ⇒ 0 cap-403; `try _ok(confirm_receipt(name, handover_notes))` @`:2604` / `except frappe.exceptions.ValidationError → _err(str(e), 422)` @`:2605-2606`) delegate service `confirm_receipt(name, handover_notes="")` @`services/imm00.py:2677` — bên NHẬN xác nhận đã tiếp nhận thiết bị điều chuyển `Approved → Received` (màn Điều chuyển feature-12 luồng NHẬN scan-confirm): patch `status=_TRANSFER_STATUS_RECEIVED='Received'` @`:2564,2687` + `received_by=session.user` + `received_date=nowdate()` @`:2686-2693` (+ `handover_notes` nếu truthy @`:2691-2692`) + audit `log_audit_event("Transfer")` @`:2695` + `create_lifecycle_event("transferred")` @`:2701`; **return EXACT 3-key `{name, status, received_by}` @`:2708`**. **LIVE whitelisted — `confirm_receipt` @2768 += `rbac.require('commissioning.write')` (CR-WF-00-TRANSFER-AUTHZ; .py cần gunicorn reload LIVE — HARD-STOP user); handler `receive_transfer` byte-identical.** `receiveTransfer` là **write-action ĐẦU TIÊN domain Điều chuyển** vào OAS mirror mobile (READ `getTransfer`/`listTransfers` đã curate — TRANSFER-READ-WIRE; `approve_transfer`/`reject_transfer`/`create_transfer` **FORWARD-RESERVE** vòng Trục-B kế). **⚠️ 2 ĐIỂM KHÁC CỐT-LÕI:** (1) **403 SINGLE `Forbidden` REACHABLE cap-branch `commissioning.write`** — `confirm_receipt` `rbac.require(_TRANSFER_RECEIVE_CAP='commissioning.write')` @`services/imm00.py:2768` propagate NGOÀI `except-ValidationError` @`api/imm00.py:2645-2648` → cap-403 status-line THẬT (mirror `approveTransfer`/`sendToLab` cap-403 REACHABLE, KHÁC cap: receive `commissioning.write` least-privilege vs approve/reject `commissioning.submit`; 403-slot VẪN SINGLE `Forbidden` — schema BẤT BIẾN; CR-WF-00-TRANSFER-AUTHZ, ADR-043 Amended; app gate nút "Xác nhận tiếp nhận" theo cap `commissioning.write`); (2) **ANTI-DRIFT `Error.http_status` = 422 ĐỒNG NHẤT** cho CẢ phiếu∄ @`:2680` LẪN status≠Approved @`:2684` — `confirm_receipt` dùng `frappe.throw`→`ValidationError`→`_err(str(e),422)` (KHÁC `get_transfer` 404 tường minh — `receive_transfer` KHÔNG phát 404). Contract đầy đủ (`ReceiveTransferRequest` closed `req[name]` + `handover_notes` optional NON-nullable; `ReceiveTransferResponse` closed EXACT 3-prop `{name,status,received_by}` — `status` enum single-value `['Received']` GROUNDED verbatim hằng `_TRANSFER_STATUS_RECEIVED`; `ReceiveTransferEnvelope`; **200 = `oneOf[ReceiveTransferEnvelope, Error]`** Decision-B route-by-VALUE; requestBody 2 media-type json+form; slot `{200,401,403}`) đặc tả tại **mobile-contract** [`docs/mobile/04-api-contract.md` §8.45](../mobile/04-api-contract.md) + [`docs/mobile/openapi/assetcore-mobile.openapi.yaml`](../mobile/openapi/assetcore-mobile.openapi.yaml) (`operationId: receiveTransfer`) + [ADR-MOBILE-043](../mobile/ADR-MOBILE-043.md).

> **📱 Cross-ref Mobile-BE — `approve_transfer` (phê duyệt phiếu điều chuyển thiết bị, transfer WRITE-action #2, CR-TRANSFER-APPROVE-01 2026-07-14):** Endpoint `api/imm00.approve_transfer(name)` (`@frappe.whitelist(methods=["POST"])` @`imm00.py:2582` no-`allow_guest` → guest dispatcher-403; `try _ok(approve_transfer_request(name))` @`:2586` / `except frappe.exceptions.ValidationError → _err(str(e), 422)` @`:2587-2588`) delegate service `approve_transfer_request(name)` @`services/imm00.py:2615` — người có quyền phê duyệt phiếu điều chuyển `Pending Approval → Approved` (màn Điều chuyển feature-12 luồng DUYỆT): kiểm phiếu tồn tại @`:2617-2618` → **`rbac.require(_TRANSFER_APPROVE_CAP='commissioning.submit')` @`:2620`** → kiểm `status==Pending Approval` @`:2623-2624` → patch `status=_TRANSFER_STATUS_APPROVED='Approved'` @`:2562,2627` + `approved_by=session.user` + `approval_date=nowdate()` @`:2626-2630` + **`transfer_asset(...)` cập vị trí thiết bị NGAY** @`:2632-2639` (đổi location/department/custodian + SINH Lifecycle Event audit) + `_notify_transfer_requester(approved=True)` @`:2641`; **return EXACT 2-key `{name, status}` @`:2643`** (KHÔNG echo `approved_by`). **LIVE whitelisted — KHÔNG đụng `.py` (byte-identical HEAD↔working).** `approveTransfer` là **write-action #2 domain Điều chuyển** vào OAS mirror mobile (`receiveTransfer` ADR-043 đã MỞ NHÁNH; `reject_transfer`/`create_transfer` **FORWARD-RESERVE** vòng Trục-B kế). **⚠️ 3 ĐIỂM KHÁC CỐT-LÕI vs `receive_transfer`:** (1) **403 SINGLE `Forbidden` REACHABLE cap-branch** — `rbac.require('commissioning.submit')` @`:2620` (TRONG service) raise `PermissionError` **NGOÀI** `except-ValidationError` @`:2587` ⇒ propagate dispatcher → HTTP-403 status-line THẬT (mirror `cancelCalibration`; GIỐNG `receive_transfer` cap-403 REACHABLE nay [CR-WF-00-TRANSFER-AUTHZ], KHÁC cap: approve `commissioning.submit` vs receive `commissioning.write`; 403-slot VẪN SINGLE `Forbidden` — reachability ≠ shape; app PHẢI gate nút theo cap `commissioning.submit`); (2) **response 2-prop `{name,status}`** — KHÔNG echo `approved_by` (return @`:2643` CHỈ 2-key, KHÁC `receive_transfer` 3-prop `received_by`); (3) **request `name`-only 0 optional** (signature 1-param, KHÁC `receive_transfer` `handover_notes`). **⚠️ ANTI-DRIFT `Error.http_status` = 422 ĐỒNG NHẤT** cho CẢ phiếu∄ @`:2617-2618` LẪN status≠Pending Approval @`:2623-2624` — `frappe.throw`→`ValidationError`→`_err(str(e),422)` (KHÁC `get_transfer` 404 tường minh — `approve_transfer` KHÔNG phát 404). Contract đầy đủ (`ApproveTransferRequest` closed `req[name]` 0 optional; `ApproveTransferResponse` closed EXACT 2-prop `{name,status}` — `status` enum single-value `['Approved']` GROUNDED verbatim hằng `_TRANSFER_STATUS_APPROVED` @`:2562` (TC-e import LIVE assert equality); `ApproveTransferEnvelope`; **200 = `oneOf[ApproveTransferEnvelope, Error]`** Decision-B route-by-VALUE; requestBody 2 media-type json+form; slot `{200,401,403}` — **403 REACHABLE** description GHI RÕ cap) đặc tả tại **mobile-contract** [`docs/mobile/04-api-contract.md` §8.46](../mobile/04-api-contract.md) + [`docs/mobile/openapi/assetcore-mobile.openapi.yaml`](../mobile/openapi/assetcore-mobile.openapi.yaml) (`operationId: approveTransfer`) + [ADR-MOBILE-044](../mobile/ADR-MOBILE-044.md). **Boundaries:** *Always* — grep `return {…}` @service (2-key `{name,status}` KHÔNG copy `receiveTransfer` 3-key) · gate nút "Phê duyệt" theo cap `commissioning.submit` (403 REACHABLE) · Decision-B lỗi nghiệp-vụ = HTTP-200 + Error 422-uniform. *Never* — khai `approved_by` trong response (return @2643 CHỈ 2-key) · khai 404 (422-uniform) · 403 dispatcher-only (CÓ `rbac.require` — REACHABLE).

> **📱 Cross-ref Mobile-BE — `reject_transfer` (từ chối phiếu điều chuyển thiết bị, transfer WRITE-action #3, CR-TRANSFER-REJECT-01 2026-07-14):** Endpoint `api/imm00.reject_transfer(name, rejection_reason="")` (`@frappe.whitelist(methods=["POST"])` @`imm00.py:2591` no-`allow_guest` → guest dispatcher-403; `try _ok(reject_transfer_request(name, rejection_reason))` @`:2595` / `except frappe.exceptions.ValidationError → _err(str(e), 422)` @`:2596-2597`) delegate service `reject_transfer_request(name, rejection_reason)` @`services/imm00.py:2646` — người có quyền từ chối phiếu điều chuyển `Pending Approval → Rejected` (màn "Điều chuyển – Chờ duyệt" feature-12 luồng DUYỆT): kiểm phiếu tồn tại @`:2648-2649` → **`rbac.require(_TRANSFER_APPROVE_CAP='commissioning.submit')` @`:2651`** → **`if not rejection_reason or len(rejection_reason.strip()) < 5: frappe.throw(...)` @`:2653-2654`** (lý do BẮT BUỘC ≥5 ký tự sau strip) → kiểm `status==Pending Approval` @`:2657-2658` → patch `status=_TRANSFER_STATUS_REJECTED='Rejected'` @`:2563,2661` + `rejected_by=session.user` + `rejection_reason=rejection_reason.strip()` @`:2660-2664` + audit `log_audit_event("Transfer")` @`:2666` + `_notify_transfer_requester(approved=False)` @`:2672`; **return EXACT 2-key `{name, status}` @`:2674`** (KHÔNG echo `rejected_by`/`rejection_reason`). **LIVE whitelisted — KHÔNG đụng `.py` (byte-identical HEAD↔working).** `rejectTransfer` là **write-action #3 domain Điều chuyển** vào OAS mirror mobile — **HOÀN TẤT cặp quyết định duyệt** (`approveTransfer` ADR-044 / reject) màn "Điều chuyển – Chờ duyệt"; `create_transfer` **FORWARD-RESERVE** vòng Trục-B kế. **⚠️ 3 ĐIỂM KHÁC CỐT-LÕI vs `approve_transfer`:** (1) **request có body BẮT BUỘC `rejection_reason`** — FIRST transfer action có required text-body (service ép `len(rejection_reason.strip()) < 5 → frappe.throw` @`:2653-2654`; handler chữ-ký có default `""` NHƯNG service ép runtime ⇒ contract REQUIRED; `minLength:5` TYPED-HINT, ngữ nghĩa RUNTIME strip-then-≥5; KHÁC `approve_transfer` name-only & `receive_transfer` `handover_notes` OPTIONAL); (2) **NHÁNH 422 THỨ-3** — `rejection_reason` thiếu/<5 (ngoài not-found @`:2649` + wrong-status @`:2657-2658`); (3) **status enum single-value `['Rejected']`** (vs `['Approved']`), response 2-prop `{name,status}` KHÔNG echo `rejected_by`/`rejection_reason`. **⚠️ GIỐNG `approve_transfer`: 403 SINGLE `Forbidden` REACHABLE cap-branch** — `rbac.require('commissioning.submit')` @`:2651` (TRONG service, TRƯỚC reason-check) raise `PermissionError` **NGOÀI** `except-ValidationError` @`:2596` ⇒ HTTP-403 status-line THẬT (403-slot VẪN SINGLE `Forbidden` — reachability ≠ shape; app PHẢI gate nút theo cap `commissioning.submit`, cùng cap nút "Phê duyệt"). **⚠️ ANTI-DRIFT `Error.http_status` = 422 ĐỒNG NHẤT** cho CẢ 3 nhánh (`frappe.throw`→`ValidationError`→`_err(str(e),422)`; KHÁC `get_transfer` 404 tường minh — `reject_transfer` KHÔNG phát 404). Contract đầy đủ (`RejectTransferRequest` closed `req[name, rejection_reason]` — `rejection_reason` string `minLength:5`; `RejectTransferResponse` closed EXACT 2-prop `{name,status}` — `status` enum single-value `['Rejected']` GROUNDED verbatim hằng `_TRANSFER_STATUS_REJECTED` @`:2563` (TC-e import LIVE assert equality); `RejectTransferEnvelope`; **200 = `oneOf[RejectTransferEnvelope, Error]`** Decision-B route-by-VALUE; requestBody 2 media-type json+form; slot `{200,401,403}` — **403 REACHABLE** description GHI RÕ cap + nhánh `rejection_reason`) đặc tả tại **mobile-contract** [`docs/mobile/04-api-contract.md` §8.47](../mobile/04-api-contract.md) + [`docs/mobile/openapi/assetcore-mobile.openapi.yaml`](../mobile/openapi/assetcore-mobile.openapi.yaml) (`operationId: rejectTransfer`) + [ADR-MOBILE-045](../mobile/ADR-MOBILE-045.md). **Boundaries:** *Always* — gửi `rejection_reason` ≥5 ký tự (validate client trước; service 422) · grep `return {…}` @service (2-key `{name,status}` KHÔNG echo `rejected_by`/`rejection_reason`) · gate nút "Từ chối" theo cap `commissioning.submit` (403 REACHABLE, cùng cap "Phê duyệt") · Decision-B lỗi nghiệp-vụ = HTTP-200 + Error 422-uniform 3-nhánh. *Never* — khai `rejection_reason` OPTIONAL (service ép required) · khai `rejected_by`/`rejection_reason` trong response (return @2674 CHỈ 2-key) · khai 404 (422-uniform) · bỏ nhánh 422 `rejection_reason` (missing-branch drift) · 403 dispatcher-only (CÓ `rbac.require` — REACHABLE).

> **📱 Cross-ref Mobile-BE — `create_transfer` (tạo phiếu yêu cầu điều chuyển thiết bị, transfer CREATE-action ĐẦU TIÊN, CR-TRANSFER-CREATE-01 2026-07-14):** Endpoint `api/imm00.create_transfer()` (`@frappe.whitelist(methods=["POST"])` @`imm00.py:2124` no-`allow_guest` → guest dispatcher-403; **signature 0-param** — đọc `data = {k: v for k, v in frappe.local.form_dict.items() if k not in ("cmd","doctype")}` @`:2126`; `try _ok(create_transfer_request(data))` @`:2128` / `except frappe.exceptions.ValidationError → _err(str(e), 422)` @`:2130`) delegate service `create_transfer_request(data: dict)` @`services/imm00.py:2568` — người dùng **tạo phiếu yêu cầu điều chuyển thiết bị MỚI** `∅ → Pending Approval` (màn "Điều chuyển" feature-12 luồng KHỞI TẠO): `required = ("asset","transfer_type","to_department","reason")` @`:2574` → `frappe.throw "Thiếu trường bắt buộc"` @`:2577` nếu thiếu → kiểm asset tồn tại `frappe.db.exists(_DOCTYPE_ASSET, asset_name)` else `frappe.throw` @`:2580-2581` → **`from_location`/`from_department`/`from_custodian` = `prev.get("location"/"department"/"custodian")` auto-derive từ asset hiện tại @`:2592-2594` (KHÔNG nhận client)** → `doc.status=_TRANSFER_STATUS_PENDING='Pending Approval'` @`:2561,2601` + `doc.insert(ignore_permissions=False)` @`:2602` + `_notify_transfer_approvers(doc)` @`:2603` + audit `log_audit_event("Transfer")` @`:2604-2609` + commit; **return EXACT 2-key `{name, status}` @`:2612`**. **LIVE whitelisted — KHÔNG đụng `.py` (byte-identical HEAD↔working, AST-extract 7+45 dòng so-khớp byte).** `createTransfer` là **CREATE-action ĐẦU TIÊN domain Điều chuyển** vào OAS mirror mobile — **HOÀN TẤT transfer write-action quartet** (`receiveTransfer` ADR-043 / `approveTransfer` ADR-044 / `rejectTransfer` ADR-045 / create). **⚠️ 3 ĐIỂM KHÁC CỐT-LÕI vs 3 write-action trước (action-on-existing):** (1) **CREATE sinh record MỚI — 0 name-param đầu vào** (handler đọc `form_dict`; request RICHEST **4-required `[asset,transfer_type,to_department,reason]` + 5-optional `[to_location,to_custodian,expected_return_date,notes,transfer_date]` = 9 prop**; `from_*` SERVER auto-derive @`:2592-2594` — KHÔNG khai trong request, `additionalProperties:false` chặn client gán vị trí nguồn giả); (2) **`∈ _MVP_CREATE_ENVELOPE`** (create-action mirror `createRepairWorkOrder`/`createCalibration`) — KHÁC 3 write-action `∈ _MVP_ACTION_ENVELOPE`; envelope tên RÚT-GỌN `CreateTransferEnvelope` (mirror `ReceiveTransferEnvelope` transfer-family, KHÔNG `...CreatedEnvelope`); (3) **403 SINGLE `Forbidden` dispatcher-ONLY** — `create_transfer` handler+service KHÔNG `rbac.require` ⇒ 0 in-handler cap-403 (mirror `attachIncidentPhoto`, KHÁC receive/`approve`/`reject` nay CẢ 3 cap-403 REACHABLE sau CR-WF-00-TRANSFER-AUTHZ — createTransfer là transfer-action DUY NHẤT còn dispatcher-only). **⚠️ ANTI-DRIFT `Error.http_status` = 422 ĐỒNG NHẤT** cho CẢ 2 nhánh (missing-required @`:2577` + asset∄ @`:2581` — `frappe.throw`→`ValidationError`→`_err(str(e),422)`; KHÁC `get_transfer` 404 tường minh — `create_transfer` KHÔNG phát 404). Contract đầy đủ (`CreateTransferRequest` closed `req[asset,transfer_type,to_department,reason]` props EXACT 9 — `from_*` KHÔNG khai; `CreateTransferResponse` closed EXACT 2-prop `{name,status}` — `status` enum single-value `['Pending Approval']` GROUNDED verbatim hằng `_TRANSFER_STATUS_PENDING` @`:2561` (TC-e import LIVE assert equality); `CreateTransferEnvelope`; **200 = `oneOf[CreateTransferEnvelope, Error]`** Decision-B route-by-VALUE; requestBody 2 media-type json+form; slot `{200,401,403}`) đặc tả tại **mobile-contract** [`docs/mobile/04-api-contract.md` §8.48](../mobile/04-api-contract.md) + [`docs/mobile/openapi/assetcore-mobile.openapi.yaml`](../mobile/openapi/assetcore-mobile.openapi.yaml) (`operationId: createTransfer`) + [ADR-MOBILE-046](../mobile/ADR-MOBILE-046.md). **Boundaries:** *Always* — gửi 4 field bắt buộc `[asset,transfer_type,to_department,reason]` (service 422 nếu thiếu) · grep `return {…}` @service (2-key `{name,status}` KHÔNG echo `from_*`/`to_*`/`approved_by`) · Decision-B lỗi nghiệp-vụ = HTTP-200 + Error 422-uniform (missing-required + asset∄). *Never* — gửi `from_location`/`from_department`/`from_custodian` (server auto-derive, `additionalProperties:false` chặn) · khai 404 (422-uniform) · gate nút "Tạo phiếu" theo cap (403 dispatcher-only — KHÔNG `rbac.require`) · `∈ _MVP_ACTION_ENVELOPE` (create ≠ action).

### `get_transfer_full` / `update_transfer`

GET chi tiết + POST update (chỉ khi Pending Approval **AND** có `commissioning.write`). `get_transfer_full` emit 4 flag CTA server-driven `can_approve`/`can_receive`/`can_cancel`/`can_edit` (§III.12-AUTHZ / §III.12-CANCELAUTHZ / §III.12-EDITAUTHZ). `update_transfer` gate `rbac.require("commissioning.write")` (§III.12-EDITAUTHZ — cap-403 REACHABLE).

---

#### III.12-NAMES — Denorm tên hiển thị Khoa / Vị trí / Người giữ (Vòng 16 — FR-00-TRF-01 / BR-00-TRF-01) — **NEW (Self-Correction: gỡ rò Link-id thô trên phiếu Điều chuyển)**

> **Đề mục Vòng 16 (2026-07-10 — denorm from/to location+department+custodian, parity `list_assets` enrich).** Phiếu Điều chuyển (`Asset Transfer`) mang 6 Link thô: `from_location`/`to_location` (→AC Location), `from_department`/`to_department` (→AC Department), `from_custodian`/`to_custodian` (→User). `list_transfers` ĐÃ enrich `asset_name` (thủ công, coalesce `''`) nhưng KHÔNG enrich 6 Link còn lại; `get_transfer` + `get_transfer_full` trả **raw `as_dict()`** (0 enrichment). **Hệ quả:** màn web `AssetTransferDetailView.vue` (consume `get_transfer_full`) và màn "Nhận bàn giao" mobile (feature 12 — consume `list_transfers`/`get_transfer`) hiển thị **Link-id thô** (`AC-DEPT-…` / `ER-…`/`AC-LOC-…` / `user@…`) thay vì tên đọc được → người nhận không đối chiếu được Khoa/Vị trí/Người giữ nguồn↔đích. **Quyết định: 3 endpoint đọc thêm ĐÚNG 6 khóa `*_name` (coalesce `''`), qua SSoT enrich N+1-free.** KHÔNG endpoint/cap/schema/DocType/field/enum/patch mới; envelope Decision-B `_ok(...)` GIỮ nguyên.

**6 khóa denorm THÊM (contract bất biến — áp cho CẢ `list_transfers`, `get_transfer`, `get_transfer_full`):**

| Khóa THÊM | Nguồn (SSoT) | Từ Link field |
|---|---|---|
| `from_location_name` | `AC Location.location_name` | `from_location` |
| `to_location_name` | `AC Location.location_name` | `to_location` |
| `from_department_name` | `AC Department.department_name` | `from_department` |
| `to_department_name` | `AC Department.department_name` | `to_department` |
| `from_custodian_name` | `User.full_name` | `from_custodian` |
| `to_custodian_name` | `User.full_name` | `to_custodian` |

`asset_name` (AC Asset.asset_name) — **GIỮ nguyên** (đã có ở `list_transfers`; `get_transfer`/`get_transfer_full` THÊM cho parity). Tổng khóa THÊM = **6 `*_name` + `asset_name`**.

**Coalesce rỗng BẮT BUỘC (đối xứng `location_name` của `list_assets` — qua SSoT `_str_or_blank`, `services/imm00.py:505`):**

```
<field>_name  ==  _str_or_blank( <display value tra được> )
    • Link có + record tồn tại + display có giá trị  → tên nguyên văn (vd 'Khoa HSTC')
    • Link RỖNG (from_department/from_custodian/to_custodian reqd=0 → có thể trống)  → ''  (str)
    • Link trỏ record đã XÓA / display whitespace-only / None  → ''  (str)
```

- **NEVER `None`, NEVER raw Link-id** (`AC-DEPT-…`/`user@…`) rò ra payload. ⚠️ Đây là **điểm khác semantics của SSoT `_enrich`** hiện có (`api/imm00.py:226`) — `_enrich` fallback `... or row.get(field) or ""` **trả raw Link-id** khi mapping miss → 6 call-site transfer PHẢI dùng nhánh coalesce-blank (xem 04 §II.1.13-TRANSFERENRICH + ADR-IMM00-TRANSFER-ENRICH).
- **Mọi item LUÔN có đủ 6 khóa** kể cả khi cả trang không phiếu nào có `from_department` (khóa = `''`, KHÔNG vắng key).

**N+1-free (bất biến):** enrichment chạy qua batch IN-query (SSoT enrich), **KHÔNG** `frappe.db.get_value` per-row trong vòng lặp. Query-count **O(1) theo số phiếu** (độc lập số row/trang) — parity `list_assets` (cũng 6 `_enrich`/field). 6 field ⇒ tối đa 6 IN-query (AC Location ×2, AC Department ×2, User ×2). *(Gộp from+to cùng doctype về 1 IN-query = tối ưu tùy chọn, KHÔNG bắt buộc — SSoT per-field GIỮ.)*

**Bất biến pagination (GIỮ NGUYÊN):** enrichment chạy **SAU** `total = frappe.db.count(...)` và **SAU** `get_list(...)` — chỉ mutate item tại chỗ (thêm khóa), **KHÔNG** thêm/bớt row, **KHÔNG** đụng `filters`/`paginate`/count. ⟹ `pagination` (dựng trước enrich) + `len(items)` bất biến; parity count-scope không đổi.

**KHÔNG rò field thừa:** chỉ thêm ĐÚNG 6 `*_name` (+`asset_name` sẵn có). **KHÔNG** kéo theo cost-center / permission / field HR / `approved_by_name`/`received_by_name`/Link-id thô mới. *(Rò `approved_by`/`received_by`/`rejected_by` = User-id thô trên màn chi tiết là leak RIÊNG, **[BACKLOG]** ngoài Vòng 16 — xem 06 §II.3a-TRANSFERNAMES.)*

**Dual detail endpoint (Self-Correction — bắt buộc enrich CẢ HAI):** contract acceptance nêu `get_transfer` (`api/imm00.py:2082`), nhưng **web `AssetTransferDetailView.vue` thực consume `get_transfer_full`** (`imm00.ts:707` → `api/imm00.py:2527`) — cả hai đang `as_dict()` 0-enrich. Nếu chỉ enrich `get_transfer`, màn web VẪN rò Link-id. ⟹ **enrich cả `get_transfer` VÀ `get_transfer_full`** cùng 1 code-path (One-Version parity). `get_transfer_full` = consumer load-bearing của màn web.

**Boundaries (Always / Never):**
- **Always**: thêm đúng 6 `*_name`; coalesce `''` qua SSoT `_str_or_blank`; enrich post-query batch (N+1-free); giữ `asset_name`; enrich cả 3 endpoint đồng shape.
- **Never**: rò raw Link-id/`None`; per-row `get_value`; đụng `filters`/count/paginate; thêm field ngoài 6 `*_name`; đổi envelope/cap/schema.

**Cross-ref:** derive 04 §II.1.13-TRANSFERENRICH · ADR-IMM00-TRANSFER-ENRICH · FE 06 §II.3a-TRANSFERNAMES · mobile feature 12 consume `list_transfers`/`get_transfer` đã enrich (contract mobile self-curate, ngoài scope BE).

#### III.12-AUTHZ — Gate `confirm_receipt` + server-driven CTA flags `can_approve`/`can_receive` (Vòng 48 — CR-WF-00-TRANSFER-AUTHZ / BR-00-TRF-02 / FR-00-TRF-02) — **NEW (missing-auth-write + dead-button)**

> **Đề mục Vòng 48 (Trục A).** `confirm_receipt` thiếu `rbac.require` (P1 — mọi user login xác nhận tiếp nhận được, kể cả base). Gỡ lỗ + phát flags cho FE gate nút. Derive BE + ADR: 04 §II.1.13-TRANSFERAUTHZ / ADR-IMM00-TRANSFER-AUTHZ. FE: 06 §II.3a-TRANSFERAUTHZ.

**`get_transfer_full` — 2 khóa flag THÊM (int 0/1, additive; envelope Decision-B `_ok(...)` GIỮ):**

| Khóa | Kiểu | Công thức (SoT `transfer_cta_flags`) | base user |
|---|---|---|---|
| `can_approve` | int 0/1 | `rbac.can("commissioning.submit")` **AND** `status == "Pending Approval"` | 0 |
| `can_receive` | int 0/1 | `rbac.can("commissioning.write")` **AND** `status == "Approved"` | 0 |

Fail-closed: thiếu cap HOẶC sai state → `0`. Suy từ CÙNG cap constant mà gate service enforce (parity, chống desync). Consumer: web `AssetTransferDetailView.vue` (06 §II.3a-TRANSFERAUTHZ).

**`receive_transfer` (POST) — cập nhật authorization (gate `confirm_receipt`):**
- Cap gate: **`rbac.require("commissioning.write")`** (`_TRANSFER_RECEIVE_CAP`) trong `confirm_receipt` (service) — SAU exists-check, TRƯỚC status-check. Base `AssetCore System User` (không có DocPerm write Asset Commissioning) → `PermissionError` → **HTTP-403** (in-handler cap-403, REACHABLE — propagate NGOÀI `except-ValidationError` của handler `:2604-2606`).
- **2 loại 403 giờ đây (DONE-gate spec-contract):** (1) **dispatcher-403** — guest/no-token (no `allow_guest`, trước handler); (2) **in-handler cap-403** — user login THIẾU `commissioning.write` (rbac.require → PermissionError). Trước Vòng 48 CHỈ có (1).
- Business errors GIỮ 422 (không đổi): phiếu∄ + status≠Approved → `frappe.throw`→`ValidationError`→`_err(str(e),422)`. Auth failure = 403 (KHÁC business = 422/HTTP-200-envelope).

> **✅ Mobile contract ĐÃ ĐỒNG BỘ (CR-WF-00-TRANSFER-AUTHZ-CONTRACT-SYNC, 2026-07-15):** OAS `receiveTransfer` ([`docs/mobile/openapi/assetcore-mobile.openapi.yaml`](../mobile/openapi/assetcore-mobile.openapi.yaml) — block `receive_transfer` + cross-ref approve/reject/create + [`docs/mobile/04-api-contract.md` §8.45](../mobile/04-api-contract.md) + [ADR-MOBILE-043](../mobile/ADR-MOBILE-043.md) **Amended**) đã sửa "403 dispatcher-ONLY" (STALE) → **403 SINGLE `Forbidden` REACHABLE cap-branch `commissioning.write`** (mirror `approveTransfer`/`rejectTransfer`, KHÁC cap: receive `commissioning.write` least-privilege vs approve/reject `commissioning.submit`; 403-slot VẪN SINGLE `Forbidden` — schema BẤT BIẾN). **Regression = 0 drift:** OAS 403 SHAPE giữ SINGLE Forbidden `$ref` (reachability ≠ shape — `test_mob_oas_recvtransfer_g` chỉ assert `$ref==Forbidden` + `http_status ⊇ {422}`, KHÔNG assert op.description text); handler signature `receive_transfer(name, handover_notes="")` KHÔNG đổi (`test_..._i` live-sig xanh) ⇒ `test_mobile_oas.py` + `oas_baseline.py` GIỮ XANH (description-only change). **Còn lại (BACKLOG — mobile-BE/test owner, KHÔNG blocking):** docstring/assertion-message informational trong `TestMobileReceiveTransferContract`/`TestMobileCreateTransferContract` (test_mobile_oas.py) vẫn ghi "receive dispatcher-only / mirror receiveTransfer" — comment stale, KHÔNG ảnh hưởng pass/fail (assertion check SHAPE bất biến). App mobile (repo UI riêng) gate nút "Xác nhận tiếp nhận" theo cap `commissioning.write`.

**Boundaries (Always / Never):**
- **Always**: flags CHỈ ở `get_transfer_full` (web consumer); gate `confirm_receipt` bằng `commissioning.write`; flag int 0/1 fail-closed; parity cap constant read↔gate.
- **Never**: thêm flags vào `get_transfer` (mobile `TransferDetail` closed-schema — drift `additionalProperties`) / `list_transfers`; đổi envelope/status-code business (422 GIỮ); reuse approve-cap cho receive; đụng cancel/create authz (backlog).

**Cross-ref:** derive 04 §II.1.13-TRANSFERAUTHZ · ADR-IMM00-TRANSFER-AUTHZ · FE 06 §II.3a-TRANSFERAUTHZ · test 07 §XIII-TRANSFERAUTHZ · SoT gate `imm14.get_decommission` R39 (parity server-driven CTA).

---

#### III.12-CANCELAUTHZ — Gate `delete_transfer`/`cancel_transfer_request` + audit-on-cancel + flag `can_cancel` (Vòng 41 — CR-WF-00-CANCEL-AUTHZ / BR-00-TRF-03 / FR-00-TRF-03) — **NEW (missing-authz + silent-audit-loss)**

> **Đề mục Vòng 41 (Trục A).** `cancel_transfer_request` thiếu `rbac.require` (P1 — mọi user login hủy phiếu được, kể cả base) + thiếu `log_audit_event` (P1 — hủy KHÔNG để dấu vết). Đóng backlog cancel-authz §III.12-AUTHZ tách ra. Derive BE + ADR: 04 §II.1.13-CANCELAUTHZ / ADR-IMM00-CANCEL-AUTHZ. FE: 06 §II.3a-CANCELAUTHZ.

**`delete_transfer` (POST — thực chất là "hủy phiếu", `name` bắt buộc) — cập nhật authorization + audit:**
- Cap gate: **`rbac.require("commissioning.write")`** (`_TRANSFER_CANCEL_CAP`) trong `cancel_transfer_request` (service) — đặt **SAU** existence-check, **TRƯỚC** status-check (mirror EXACT `confirm_receipt` `:2757`). Base `AssetCore System User` (không có DocPerm write Asset Commissioning) → `PermissionError` → **HTTP-403** (in-handler cap-403 REACHABLE — propagate NGOÀI `except-ValidationError` của handler `delete_transfer` `:2172-2177`).
- **Audit (MỚI):** mỗi lần hủy thành công sinh **ĐÚNG 1** dòng `IMM Audit Trail` — `event_type='Transfer'`, `ref_doctype='Asset Transfer'`, `ref_name=name`, `change_summary` chứa `'Hủy'` (vd `"Hủy phiếu luân chuyển (trạng thái trước: Pending Approval)"`). Trước Vòng 41 = **0 dòng** (silent-audit-loss). Đồng bộ trong transaction (KHÔNG best-effort) → all-or-nothing.
- Happy-path: Commissioning User (write=1) hủy phiếu `Pending Approval` HOẶC `Rejected` → `_ok({name, status:'Cancelled'})`. Return shape KHÔNG đổi.
- **Ordering & error-taxonomy (chống rò trạng thái):**
  - phiếu **KHÔNG tồn tại** → existence-check (TRƯỚC rbac) → `frappe.throw(_ERR_TRANSFER_NOT_FOUND)` → `ValidationError` → handler `_err(str(e), 422)` (NOT-FOUND business-error; existence-leak chấp nhận — mirror mọi sibling transfer). base user hủy phiếu-∄ vẫn nhận NOT-FOUND (không phải 403).
  - base user hủy phiếu **SAI status** (Approved/Received/Cancelled — phiếu CÓ tồn tại) → `rbac.require` (TRƯỚC status-check) fire → **HTTP-403**, KHÔNG bao giờ chạm status-check ⇒ **KHÔNG rò trạng thái phiếu** cho user thiếu quyền.
  - user CÓ cap hủy phiếu sai status → `frappe.throw("Chỉ có thể hủy phiếu đang Pending Approval hoặc Rejected")` → `ValidationError` → `_err(str(e), 422)`.
  - **2 loại 403:** (1) dispatcher-403 guest/no-token (no `allow_guest`); (2) in-handler cap-403 user login THIẾU `commissioning.write`.

**`get_transfer_full` — khóa flag THỨ 3 `can_cancel` (int 0/1, additive; auto-echo qua `transfer_cta_flags`, KHÔNG đổi code api):**

| Khóa | Kiểu | Công thức (SoT `transfer_cta_flags`) | base user |
|---|---|---|---|
| `can_cancel` | int 0/1 | `rbac.can("commissioning.write")` **AND** `status ∈ {"Pending Approval", "Rejected"}` | 0 |

Fail-closed: thiếu cap HOẶC status ngoài 2-giá-trị → `0`. Suy từ CÙNG cap constant mà `cancel_transfer_request` enforce (parity, chống desync). Consumer: web `AssetTransferDetailView.vue` (06 §II.3a-CANCELAUTHZ). `get_transfer_full` là web-only (KHÔNG trong mobile OAS) ⇒ 0 mobile-OAS impact; `delete_transfer` cũng KHÔNG có trong mobile OAS ⇒ 0 mobile drift.

**Boundaries (Always / Never):**
- **Always**: gate `cancel_transfer_request` bằng `commissioning.write` SAU exists TRƯỚC status; sinh ĐÚNG 1 audit `Transfer` (change_summary chứa 'Hủy'); `can_cancel` CHỈ ở `get_transfer_full`; flag int 0/1 fail-closed; return `{name, status:'Cancelled'}`.
- **Never**: HTTP-200+Error-envelope cho auth-failure (cap-403 ≠ business-422); reuse approve-cap `commissioning.submit` cho cancel; thêm `can_cancel` vào `get_transfer`/`list_transfers` (mobile closed-schema drift); đảo ordering (403 trước NOT-FOUND); nới status-check.

**Cross-ref:** derive 04 §II.1.13-CANCELAUTHZ · ADR-IMM00-CANCEL-AUTHZ · FE 06 §II.3a-CANCELAUTHZ · test 07 §XIV · SoT `confirm_receipt` ordering (`:2757`).

---

#### III.12-EDITAUTHZ — Gate `update_transfer` (endpoint-level) + emit `can_edit` (Vòng 46 — CR-WF-00-EDIT-AUTHZ / BR-00-TRF-04 / FR-00-TRF-04) — **NEW (missing-authorization write + custody-hole)**

> **Đề mục Vòng 46 (Trục A — HOÀN TẤT bộ-bốn transfer-authz).** `update_transfer` (`api/imm00.py:2616`) CHỈ check `status=='Pending Approval'` (422) rồi `_generic_update` — **THIẾU `rbac.require`** ⇒ mọi user login (kể cả chỉ `inventory.read`) đổi được đích/khoa/người-nhận/ngày/lý do/ghi-chú phiếu Pending → 200 (custody-hole). Bịt lỗ + emit `can_edit` cho FE gate form. Derive BE + ADR: 04 §II.1.13-EDITAUTHZ / ADR-IMM00-EDIT-AUTHZ. FE: 06 §II.3a-EDITAUTHZ. Test: 07 §XIV-EDIT.

**`update_transfer` (POST) — cập nhật authorization (gate endpoint-level, ordering mirror `transition_status` rbac-first):**
- Cap gate: **`rbac.require("commissioning.write")`** (`_TRANSFER_EDIT_CAP`) làm **CÂU LỆNH ĐẦU** thân handler — TRƯỚC `frappe.db.exists` (no existence-oracle, mirror EXACT `transition_status` `:1163`). Base `AssetCore System User` / user chỉ `inventory.read` (không DocPerm write Asset Commissioning) → `frappe.PermissionError` → **HTTP-403** (in-handler cap-403 REACHABLE — KHÔNG try/except trong handler ⇒ propagate; `PermissionError ∉ ValidationError` MRO ⇒ `_generic_update`'s `except-ValidationError` cũng KHÔNG nuốt).
- **Status-gate 422 GIỮ NGUYÊN:** user CÓ `commissioning.write` POST trên phiếu Approved/Received/Cancelled → `_err("Chỉ có thể chỉnh sửa phiếu đang Pending Approval", 422)` (KHÔNG bị rbac che thành 403 — có cap nên `rbac.require` KHÔNG fire; status-check chạy → 422 message rõ).
- **Happy-path:** user CÓ `commissioning.write` + phiếu Pending → `_generic_update(_DT_TRANSFER, name)` cập nhật field THẬT (`to_department`/`to_location`/`to_custodian`/`transfer_date`/`expected_return_date`/`reason`/`notes` từ `frappe.local.form_dict`) → `_ok({name})` (re-fetch `get_transfer_full` xác nhận field đổi).
- **Not-found nay 404 (cải thiện):** phiếu∄ + user CÓ cap → existence-check → `_err(NOT_FOUND, 404)` (trước đây `get_value(...,"status")=None != 'Pending Approval'` → 422 sai-nghĩa). base user + phiếu∄ → 403 (rbac-first, no existence-oracle) — chủ ý.
- **2 loại 403 (DONE-gate spec-contract):** (1) **dispatcher-403** — guest/no-token (no `allow_guest`, trước handler); (2) **in-handler cap-403** — user login THIẾU `commissioning.write` (rbac.require → PermissionError). Trước Vòng 46 CHỈ có (1); business errors GIỮ HTTP-200+Error-envelope (422/404).

**`get_transfer_full` — khóa flag THỨ 4 `can_edit` (int 0/1, additive; auto-echo qua `transfer_cta_flags`, KHÔNG đổi code api):**

| Khóa | Kiểu | Công thức (SoT `transfer_cta_flags`) | base user |
|---|---|---|---|
| `can_edit` | int 0/1 | `rbac.can("commissioning.write")` **AND** `status == "Pending Approval"` | 0 |

Fail-closed: thiếu cap HOẶC sai status → `0`. Suy từ CÙNG cap constant mà `update_transfer` enforce (parity, chống desync). **INVARIANT button-affordance ⇔ action:** `can_edit=1` cho session hiện tại ⇒ `update_transfer` KHÔNG raise PermissionError cùng session (rbac.require pass) VÀ status==Pending pass ⇒ 200 (mirror parity `can_cancel`/`can_receive`). Consumer: web `AssetTransferDetailView.vue` (06 §II.3a-EDITAUTHZ). `get_transfer_full` là web-only (KHÔNG trong mobile OAS) ⇒ 0 mobile-OAS impact; `update_transfer` cũng KHÔNG trong mobile OAS ⇒ 0 mobile drift.

**Boundaries (Always / Never):**
- **Always**: gate `update_transfer` bằng `commissioning.write` làm câu-lệnh-ĐẦU handler (rbac TRƯỚC exists, no existence-oracle — mirror transition_status); giữ status-gate 422 cho phiếu non-Pending; `can_edit` CHỈ ở `get_transfer_full`; flag int 0/1 fail-closed; parity cap constant read↔gate (1 nguồn `services/imm00.py`).
- **Never**: HTTP-200+Error-envelope cho cap-403 (auth-failure ≠ business-422); thêm `can_edit` vào `get_transfer`/`list_transfers` (mobile closed-schema drift); reuse approve-cap `commissioning.submit` cho edit; để rbac che status-gate thành 403 cho user CÓ cap; nới status-check (Approved/Received/Cancelled vẫn 422); đụng receive/cancel/create authz.

**Cross-ref:** derive 04 §II.1.13-EDITAUTHZ · ADR-IMM00-EDIT-AUTHZ · FE 06 §II.3a-EDITAUTHZ · test 07 §XIV-EDIT · SoT `transition_status` endpoint-gate ordering (`api/imm00.py:1163`, ADR-IMM00-TRANSITION-AUTHZ) · parity flags §III.12-AUTHZ/§III.12-CANCELAUTHZ.

---

## III.13. Service Contract (5 endpoints)

`list_service_contracts`, `get_service_contract`, `create_service_contract`, `update_service_contract`, `delete_service_contract` + `list_asset_contracts` (GET contracts của 1 asset).

---

## III.14. PM Schedule (5 endpoints)

`list_pm_schedules`, `get_pm_schedule`, `create_pm_schedule`, `update_pm_schedule`, `delete_pm_schedule`. Served bởi `assetcore.api.imm00`.

> **`list_pm_schedules(asset=…)` — khoá drill của ô «Lịch bảo trì định kỳ» (AC-CR-94):** tham số `asset` dịch thẳng sang bộ lọc cột `asset_ref`, **không** áp bộ lọc `status`/`pm_type` mặc định ⇒ lịch `Paused`/`Suspended` **thuộc** tập trả về, giữ bất biến `count == drill` với `get_connections` (INV-CONN-18 — xem **§III.24.8** cuối phần III.24). ⚠️ **Không nhầm** với `assetcore.api.imm08.list_pm_schedules(asset_ref=…)` — hai bề mặt khác nhau; ô «Bản ghi liên quan» drill qua **`imm00`** (đường mà `frontend/src/api/imm00.ts:854` gọi).

---

## III.15. PM Checklist Template (5 endpoints)

`list_pm_templates`, `get_pm_template`, `create_pm_template`, `update_pm_template`, `delete_pm_template`.

> **Lưu ý:** FE client (`frontend/src/api/imm00.ts`) route các PM Template endpoints sang `assetcore.api.imm08` (service-based xử lý checklist_items JSON), nhưng BE có cả 2 implementations.

### `list_pm_templates` — GET

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.list_pm_templates` |
| Params | `page=1, page_size=50` |
| Permission | All IMM roles |

Response: paginated list `PmTemplate{name, template_name, asset_category?, pm_type?, version?, checklist_items?}`.

### `get_pm_template` / `create_pm_template` / `update_pm_template` / `delete_pm_template`

CRUD pattern. POST body: `{ "name": "..." }` + fields.

**Errors:** `AC-E001` (404), `AC-E011` (409 trùng template_name + version).

---

## III.16. Firmware Change Request (5 endpoints)

`list_firmware_crs`, `get_firmware_cr`, `create_firmware_cr`, `update_firmware_cr`, `delete_firmware_cr`.

### `list_firmware_crs` — GET

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.list_firmware_crs` |
| Params | `page=1, page_size=20, status?, asset?` |

Response items: `FirmwareCR{name, asset_ref, version_before?, version_after?, status?, ...}`.

### `get_firmware_cr` — GET `?name=...`

### `create_firmware_cr` — POST

Body required: `asset_ref` (Link AC Asset), `version_after`. Optional: `version_before`, `status`, attachments.

**Response 200:** `{ "name": "FCR-..." }`.

**Errors:** 422 nếu thiếu `asset_ref`.

### `update_firmware_cr` / `delete_firmware_cr`

POST. Body `{ "name": "..." }` + update fields (resp. `{ "name": "..." }` for delete).

---

## III.17. Document Request (5 endpoints)

`list_document_requests`, `get_document_request`, `create_document_request`, `update_document_request`, `delete_document_request`.

### `list_document_requests` — GET

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.list_document_requests` |
| Params | `page=1, page_size=20, status?, asset?` |

Response items: `DocumentRequest{name, asset_ref, doc_type_required, status?, priority?, ...}`.

### `get_document_request` / `create_document_request` / `update_document_request` / `delete_document_request`

Standard CRUD. `create` requires: `asset_ref`, `doc_type_required`. Returns `{ "name": "DR-..." }`.

**Errors:** 422 thiếu required; 404 (`AC-E001`) khi không tìm thấy.

---

## III.18. Depreciation (9 endpoints)

### `compute_depreciation` (POST)

Body: `name` (AC Asset). Trả `{ accumulated, book_value, method?, days_elapsed?, note? }`.

> **`book_value` qua SoT `effective_book_value` (BR-05-13 / RC-06).** `book_value` suy bằng SoT DUY NHẤT `services/depreciation.py::effective_book_value(asset_row)` — KHÔNG idiom falsy `current_book_value or gross`. Asset đã khấu hao **hết** về `current_book_value=0.0` (residual=0) → trả **`0.0`** (đúng), KHÔNG phantom `gross`. Asset CHƯA chạy KH (`current_book_value IS NULL`) → trả `gross` (no regression).

### `get_depreciation_schedule` (GET)

Params: `asset_name`. Trả `{ asset, asset_info, rows[], summary{total_periods, executed_periods, pending_periods, total_depreciated} }`.

> **Sau thanh lý (BR-00-24 / RC-07 — Vòng 8):** với asset đã `Decommissioned`, các kỳ Pending đã được chuyển sang `Cancelled` ⇒ `summary.pending_periods == 0`. Các dòng `Cancelled` VẪN xuất hiện trong `rows[]` (`status='Cancelled'`) — KHÔNG bị xoá; chỉ không còn được đếm vào `pending_periods` và không bị cron chạy. `executed_periods` + `total_depreciated` + `asset_info.accumulated_depreciation/current_book_value` bất biến so với trước thanh lý.

> **Sau khôi phục từ Out of Service (BR-00-25 / RC-08 — Vòng 9):** với asset đã `Out of Service → Active`, các kỳ `status='Pending'` có `scheduled_date` **đã được dời** `+= oos_days` (`rows[].scheduled_date` mới = ngày-cũ + số-ngày-ngừng). `summary.pending_periods` KHÔNG đổi (không mất/thêm kỳ), `sum(depreciation_amount)` các kỳ Pending KHÔNG đổi. `executed_periods` + `accumulated_depreciation`/`current_book_value` bất biến (PAUSE — không trích trong lúc OoS, không trích bù khi khôi phục). FE render `rows[].scheduled_date` verbatim ⇒ tự hiện ngày đã dời + banner "Kỳ tiếp theo" (`nextPendingRow`) trỏ kỳ Pending đầu tiên với `scheduled_date` mới — **zero shape-change** ở response (`get_depreciation_schedule` giữ nguyên field).

**Errors:** 404 (`AC-E001`) khi không tồn tại asset.

> **📱 Cross-ref Mobile-BE — `get_depreciation_schedule` (khấu hao, asset-detail sub-tab #5, CR-11e 2026-07-13):** `getAssetDepreciationSchedule` là sub-tab THỨ NĂM & **CUỐI** của CR-11 (sau `getAssetKpi` §III.1/ADR-038 + `getAssetDowntimeMetrics` §III.19/ADR-039 + `getAssetVerifyChain` §III/ADR-040 + `getAssetCommissioningOrigin` §imm-04/ADR-041) — tab "Khấu hao" màn hồ-sơ-thiết-bị; dữ-liệu **giá-trị tài-sản** (kế-toán khấu hao + WHO HTM end-of-life planning). **HOÀN TẤT bộ-năm CR-11.** Handler `get_depreciation_schedule(asset_name)` @`api/imm00.py:2962` (bare `@frappe.whitelist()` → GET; guest dispatcher-403; **self-contained** KHÔNG service/`_handle`; `_err(_("Asset not found"), 404)` asset∄ @`:2965` → HTTP-200 nhánh Error Decision-B). **LIVE whitelisted — KHÔNG đụng `.py`.** Contract đầy đủ (**LẦN ĐẦU WRAPPER 4-key với 3 nested-schema** — payload phức-nhất bộ CR-11: `AssetDepreciationSchedule` closed `{asset:string, asset_info:object|null, rows:array, summary:object}` required=cả 4; **`asset_info` = nullable-ref idiom** `{type:object,nullable:true,allOf:[$ref AssetDepreciationInfo]}` `get_value(...) or {}` @`:2988` mirror `commissioning` ADR-041/`current_open` ADR-039; **`DepreciationScheduleRow` closed EXACT 9-prop** VERBATIM get_all @`:2969-2971` [`name` req · 3 Currency **FINANCIAL** number nullable · `status` **enum[Pending,Executed,Cancelled]** Select bounded no-blank default 'Pending' **DB-verified 413/79/42 0-blank/534** bám ADR-028 · 2 Date `format:date`], required=EXACT`[name]`; **`DepreciationScheduleSummary` closed EXACT 4-prop** compute @`:2975-2981` [3 integer + `total_depreciated` **FINANCIAL** number] required=đủ 4; **`AssetDepreciationInfo` closed EXACT 9-prop** VERBATIM get_value @`:2984-2986` [4 Currency **FINANCIAL** number nullable · `depreciation_method`/`depreciation_frequency` string nullable **NO-enum** Select LEADING-BLANK `''` hợp-lệ ADR-028 sub-case · 1 Int · 2 Date] **required=∅** TOÀN value-nullable convention `getAssetKpi`; `AssetDepreciationScheduleEnvelope`; **200 = `oneOf[AssetDepreciationScheduleEnvelope, Error]`** closed-schema Decision-B — `_err(404)` asset∄ → HTTP-200 nhánh Error; slot `{200,401,403}`) đặc tả tại **mobile-contract** [`docs/mobile/04-api-contract.md` §8.44](../mobile/04-api-contract.md) + [`docs/mobile/openapi/assetcore-mobile.openapi.yaml`](../mobile/openapi/assetcore-mobile.openapi.yaml) (`operationId: getAssetDepreciationSchedule`) + [ADR-MOBILE-042](../mobile/ADR-MOBILE-042.md). **Boundaries:** *Always* — curate VERBATIM theo return-dict (KHÔNG strip 8 FINANCIAL khỏi contract) · **⚠️ param `asset_name` KHÔNG `name`** (chữ-ký @`:2962`), **REQUIRED** (positional no-default + `_err(404)` asset∄) · `Row.status` bounded no-blank → **enum** VS `Info.*_method`/`*_frequency` leading-blank → **string nullable no-enum** (ADR-028 2 sub-case) · Decision-B lỗi nghiệp-vụ = HTTP-200 + Error envelope (KHÔNG raise→4xx). *Never* — flatten 3 nested-schema (mất `rows[]`/`asset_info` nullable/`summary`) · ép `AssetDepreciationInfo.*` vào required (9 field get_value null hợp-lệ + `{}` coalesce → deser crash) · enum-hoá 2 Select leading-blank (`''` hợp-lệ) · render 8 FINANCIAL cho persona không quyền tài-chính (UI-gate FE). **One-Version Rule:** web SPA `frontend/` dùng cùng endpoint (tab Khấu hao màn hồ-sơ + Asset Finance Hub) — 1 contract phục vụ cả web + mobile.

### `regenerate_depreciation_schedule` (POST)

Params: `asset_name, force=1`. Sinh lại schedule (xoá cũ nếu force=1). Service: `assetcore.services.depreciation.generate_schedule`.

**Luồng (RC-04 — self-heal-rồi-pre-check, Round-2):**
1. **Self-heal TRƯỚC pre-check:** `frappe.get_doc(asset)` → `inherit_depreciation_rules_from_category(asset)` (SoT round-1). Nếu `did_inherit=True` → `save(ignore_permissions=True)` + sinh audit (ALE `depreciation_rules_inherited` + IMM Audit Trail `System`).
2. **Pre-validate 4 input CHẠY LẠI SAU inherit** (method, `total_depreciation_months>0`, `gross>0`, start_date — đọc state SAU self-heal) → thiếu bất kỳ → **422** với message VI nêu rõ field thiếu (vd `Thiếu: Số tháng khấu hao (total_depreciation_months)`).
3. Pass → `generate_schedule(force)` → **200** `{periods, ...}`.

> **RC-04 (Self-Correction 2026-06-03, Round-2 — goal C):** lỗi user báo — asset CŨ (tạo TRƯỚC khi `before_insert` wire SoT) có Category CÓ luật nhưng `asset.total_depreciation_months=0` → bấm "Sinh lịch khấu hao" trả 422 oan. Fix: endpoint **TỰ kế thừa luật** từ Category qua **SoT DUY NHẤT** `inherit_depreciation_rules_from_category` TRƯỚC pre-check → **KHÔNG còn 422 "Thiếu: Số tháng khấu hao"**, sinh được schedule (`periods > 0`).
> - **KHÔNG che lỗi master-data:** Category cũng thiếu luật (`total_depreciation_months=0`) HOẶC asset không có `asset_category` → inherit no-op → **VẪN 422** liệt kê đúng field thiếu (BR-00-20/22).
> - **KHÔNG clobber user:** months/residual user đã nhập tay → inherit no-op (BR-00-19).
> - **Bảo toàn lịch sử:** asset có kỳ Executed → self-heal KHÔNG override months/residual đã chạy (BR-00-21).
> - **Idempotent + audit:** gọi 2 lần → cùng `periods`; `did_inherit=True` → 1 ALE + 1 IMM Audit Trail; no-op → KHÔNG event rác (FR-00-55).
> - **Grep-guard:** `api/imm00.py` — 0 occurrence copy months/residual từ Category ngoài lời gọi SoT.
> - **RC-03 (round-1) vẫn đúng:** asset MỚI tạo qua `before_insert` đã kế thừa sẵn → đường này self-heal no-op (đã đủ luật).

### `preview_depreciation_schedule` (GET)

Params: `gross, residual, method, total_months, frequency, start_date`. Preview rows không lưu DB. Phục vụ form before-commit.

### `run_due_depreciation_now` (POST) — Admin only

Params: `as_of?` (date string). Chạy thủ công job depreciation due. Guard: `_assert_system_admin()` — role `System Manager` hoặc `IMM System Admin`.

### `bulk_regenerate_schedule_by_category` (POST) — Admin only

Nút **"Áp dụng khấu hao theo từng Danh mục"** (`ReferenceDataView.vue`, form Category). Params: `category_name`. Service: `assetcore.services.depreciation.bulk_regenerate_by_category`. RBAC: `_assert_system_admin()` → non-admin **403** (không leak).

**Hành vi (RC-05 — route qua SoT, KHÔNG clobber — Round-4):** với mỗi asset thuộc Category (`docstatus != 2`):
1. Asset có ≥1 kỳ **Executed** → KHÔNG đụng (preserve history) → `skipped_has_history`. Xác định qua **1 query GROUP BY parent** (`executed_parents` prefetch) chạy MỘT LẦN trước loop — KHÔNG `frappe.db.count` per-asset (N+1 đóng, mirror `compute_all` round-3).
2. Else gọi **SoT DUY NHẤT** `inherit_depreciation_rules_from_category(asset)` (thay 4 dòng inline cũ) → đếm `inherited` nếu ≥1 field thay đổi. **No-clobber:** `months/residual/method/frequency` user đã nhập → GIỮ NGUYÊN (BR-00-19/23).
3. Asset `gross<=0` HOẶC Category cũng thiếu luật (`cat.months<=0`) → `skipped_no_rule` (KHÔNG che lỗi master-data — BR-00-20).
4. Else `generate_schedule(force=True)` (asset chưa-Executed → xoá-sinh-lại) → `regenerated`.
5. Audit best-effort: per-asset ALE `depreciation_rules_inherited` (option round-1, KHÔNG migrate) + **1** IMM Audit Trail `System` TỔNG cho lần bulk — KHÔNG chặn payload (CLAUDE.md §5).

**Response 200 (payload 7-key — chuẩn hoá khớp `compute_all`):**
```json
{ "category": "CAT-0659", "total_assets": 0,
  "inherited": 0, "regenerated": 0,
  "skipped_has_history": 0, "skipped_no_rule": 0, "errors": 0 }
```
- `inherited` = số asset được SoT kế thừa ≥1 field. `skipped_no_rule` = asset `gross<=0` hoặc Category chưa cấu hình luật.
- `skipped_has_history` = asset đã có kỳ Executed (bỏ qua bảo toàn lịch sử) → `accumulated/book` bất biến.

**Idempotent:** chạy 2 lần liên tiếp trên cùng dataset → lần 2 `inherited = 0` (đã đủ luật); `accumulated` của asset đã Executed không đổi.

> **Self-Correction (Round-4 / RC-05):** payload cũ 5-key `{ category, total_assets, regenerated, skipped_has_history, errors }` (inline copy → **clobber** field user nhập; thiếu `inherited`/`skipped_no_rule`; N+1 `db.count` per-asset) đã được thay bằng shape 7-key trên + route qua SoT. FE `bulkRegenerateScheduleByCategory()` (06 §V.1) cập nhật type theo shape mới (thêm `inherited` + `skipped_no_rule`).

### `list_assets_depreciation` (GET) — Asset Finance Hub

Params: `page=1, page_size=50, method_filter?, status_filter?, category_filter?, depreciation_filter?`. Trả paginated list assets kèm: `gross_purchase_amount, residual_value, accumulated_depreciation, current_book_value, depreciation_method, total_depreciation_months, depreciation_frequency, configured, pct_depreciated, executed_periods, total_periods`.

> **`current_book_value` enriched qua SoT `effective_book_value` (BR-05-13 / RC-06).** Mỗi dòng (`_depr_enrich_row`) gán `current_book_value = effective_book_value(row)` — KHÔNG `or gross`. Asset KH hết về 0 → field trả **`0.0`** (drill hiện `0đ`), KHÔNG phantom `gross`. Dòng enriched này cũng nuôi `is_fully_depreciated` (cùng book SoT → count==drill khớp).

**`depreciation_filter`** (mới — drill cho ô KPI "Hết khấu hao", BR-05-15):
- `'fully_depreciated'` → danh sách CHỈ chứa asset thỏa SoT `is_fully_depreciated` (`configured ∧ current_book_value ≤ residual_value + 1`). Áp **post-enrich**, AND với `method/status/category` filter sẵn có (không clobber).
- Khi set, `pagination.total` == số phần tử thỏa SoT (đếm trên tập đã lọc, KHÔNG `frappe.db.count` thô) → `items` không lệch `total`.
- Để rỗng → hành vi cũ (không lọc theo trạng thái khấu hao).
- Predicate là SoT DUY NHẤT ở `services/depreciation.py::is_fully_depreciated` — KHÔNG inline lại. Chi tiết: [imm-05/04 §2.5.1](../imm-05/04_Backend_Design.md).

> **INV-DEP-5 (đo trên data-live):** `len(list_assets_depreciation(depreciation_filter='fully_depreciated', page_size=lớn).items)` (de-dup theo `name`) == `get_depreciation_stats().fully_depreciated` — card count == drill rows.

### `get_depreciation_stats` (GET)

Trả tổng hợp tài chính toàn danh mục: `{ total_assets, configured_count, unconfigured_count, fully_depreciated, total_gross, total_accumulated, total_book_value, overall_pct, by_method[], by_category[] }`.

`fully_depreciated` đếm bằng SoT `is_fully_depreciated` (thay biểu thức inline cũ `book <= residual + 1`) — **backward-compat: cùng tập, cùng số**. Các key khác KHÔNG đổi.

> **`total_book_value` & `by_category[].book_value` qua SoT `effective_book_value` (BR-05-13 / RC-06).** Mỗi asset cộng book = `effective_book_value(row)` thay vì `current_book_value or gross`. Asset đã khấu hao **hết** về `0.0` → cộng **`0.0`**, KHÔNG phantom `gross` (trước: over-count = `gross`). Cùng book SoT nuôi `is_fully_depreciated` → INVARIANT: asset `gross>0 ∧ residual=0 ∧ configured ∧ book=0.0` ĐƯỢC đếm `fully_depreciated` (trước bị loại vì book thổi về `gross > residual+1`). Asset `current_book_value IS NULL` (chưa chạy KH) → cộng `gross` (no regression).

### `compute_all_depreciation` (POST) — Admin only

Nút global **"Áp dụng khấu hao cho TẤT CẢ tài sản"** (Asset Finance Hub). RBAC: `_assert_system_admin()` → non-admin **403** (không leak).

**Hành vi (RC-03 — backfill-rồi-sinh, thay vì skip):** với mỗi asset `docstatus != 2`:
1. Nếu có ≥1 kỳ **Executed** → KHÔNG đụng (preserve history) → đếm `skipped_has_history`.
2. Else nếu asset thiếu `method/months` **và** Category có luật → gọi SoT `inherit_depreciation_rules_from_category()` để **backfill TRƯỚC** (đếm `inherited` nếu ≥1 field thay đổi), rồi `generate_schedule(force=False)` (đếm `generated`).
3. Nếu asset thiếu luật **và** Category cũng không có luật → `skipped_no_rule` (không bịa số — BR-00-20).
4. Sau vòng lặp: `run_due_depreciation(None)` cập nhật `accumulated/book` đến `today` → `executed_rows`, `updated_assets`.
5. Sinh lifecycle/audit event cho hành động backfill (1 event tổng hoặc per-asset inherited — BR-00-21, audit trail).

**Response 200:** payload có cấu trúc rõ:
```json
{ "inherited": 0, "generated": 0, "executed_rows": 0,
  "updated_assets": 0, "skipped_has_history": 0, "skipped_no_rule": 0 }
```
- `skipped_no_rule` = asset không có cả luật ở Category.
- `skipped_has_history` = asset đã có kỳ Executed (bỏ qua để bảo toàn lịch sử).

**Idempotent:** chạy 2 lần liên tiếp trên cùng dataset → lần 2 `inherited = 0` (không còn gì để backfill) và KHÔNG tạo trùng schedule / đổi `accumulated` của asset đã Executed.

> **Self-Correction:** payload cũ `{ generated_schedules, skipped, executed_rows, updated_assets }` (gộp mọi lý do skip vào 1 số `skipped`, và **skip** thay vì backfill) đã được thay bằng shape 6-key ở trên. FE `computeAllDepreciation()` (06 §V.1) cập nhật type theo shape mới.

> 3 endpoint admin (`run_due_depreciation_now`, `bulk_regenerate_schedule_by_category`, `compute_all_depreciation`) đều dùng `_assert_system_admin()` guard.

---

## III.19. Asset Downtime Metrics (1 endpoint)

`get_asset_downtime_metrics` — GET, params: `asset_name, year (optional)`.

**Chữ ký LIVE** `get_asset_downtime_metrics(asset_name: str, year: str = "")` @`api/imm00.py:2892-2893` (bare `@frappe.whitelist()` → GET; guest dispatcher-403). Đọc `AC Asset Downtime Log` filter `asset` + `start_time between [year-01-01, year-12-31]` @`:2909-2919` (`year` rỗng → năm hiện-tại @`:2905`), trả `_ok({8-key})` @`:2936-2944`:

| Key | Type | Nghĩa | @source |
|---|---|---|---|
| `asset` | string | echo `asset_name` | `:2937` |
| `year` | integer | năm thống-kê (`int(y)`) | `:2905/2938` |
| `total_hours` | number | tổng giờ dừng (closed + open đến `now`) | `:2939` |
| `breakdown_count` | integer | số lần dừng (`len(rows)`) | `:2940` |
| `mttr_hours` | number | MTTR = `total_hours / breakdown_count` (0 nếu count=0) | `:2941` |
| `by_reason` | object (map `reason → giờ`) | phân-loại giờ dừng theo lý-do (dict động 6 option Select) | `:2922/2931/2942` |
| `current_open` | object \| null | log đang-mở (`{**log, downtime_hours_so_far}`) hoặc `null` | `:2923/2927/2943` |
| `logs` | array | ≤10 log gần nhất (`rows[:10]`, `order_by start_time desc`) | `:2917/2944` |

- Mỗi log (`get_all fields` @`:2915-2916`, grounded doctype `ac_asset_downtime_log.json`): `name, reason` (Select 6-option `reqd`), `start_time` (Datetime `reqd`), `end_time` (nullable — null khi mở), `downtime_hours` (Float read_only nullable), `is_open` (Check 0/1), `reference_doctype` (Link nullable), `reference_name` (Dynamic Link nullable).
- `asset∄` → `_err(_("Không tìm thấy thiết bị"), 404)` @`:2901-2902` (in-handler Error envelope; Mobile-BE → HTTP-200 nhánh Error, xem cross-ref). Read-only — **KHÔNG audit**.

> **📱 Cross-ref Mobile-BE — `get_asset_downtime_metrics` (thống-kê dừng máy, asset-detail sub-tab #2, CR-11b 2026-07-13):** `getAssetDowntimeMetrics` là sub-tab THỨ HAI của CR-11 (sau `getAssetKpi` §III.1 / ADR-038) — tab "Dừng máy" màn hồ-sơ-thiết-bị. **LIVE whitelisted — KHÔNG đụng `.py`.** Contract đầy đủ (`AssetDowntimeMetrics` closed **EXACT 8 prop** VERBATIM return-dict, `required`=cả 8; **`by_reason` = open-map** `additionalProperties:{type:number}` — LẦN ĐẦU open-map number trong success-data schema, **ADR EXCEPTION**; `current_open` = nullable `$ref AssetDowntimeLogOpen` (OpenAPI 3.0.3 `{nullable:true, allOf:[$ref]}`); sub-schema `AssetDowntimeLog` 8-field closed [`is_open` integer enum[0,1] int-vs-bool trap; `reason` plain string đối-xứng by_reason; `start_time/end_time` string no-`format:date-time`] + `AssetDowntimeLogOpen` = Log 8 + `downtime_hours_so_far` number; `logs[]` items `AssetDowntimeLog`; **200 = `oneOf[AssetDowntimeMetricsEnvelope, Error]`** closed-schema Decision-B — `_err(404)` asset∄ → HTTP-200 nhánh Error; slot `{200,401,403}`) đặc tả tại **mobile-contract** [`docs/mobile/04-api-contract.md` §8.41](../mobile/04-api-contract.md) + [`docs/mobile/openapi/assetcore-mobile.openapi.yaml`](../mobile/openapi/assetcore-mobile.openapi.yaml) (`operationId: getAssetDowntimeMetrics`) + [ADR-MOBILE-039](../mobile/ADR-MOBILE-039.md). **Boundaries:** *Always* — curate VERBATIM 8 key theo return-dict · **⚠️ param `asset_name` KHÔNG `name`** (chữ-ký @`:2893`) · `year` typed-query optional (parity CR-05) · Decision-B lỗi nghiệp-vụ = HTTP-200 + Error envelope (KHÔNG raise→4xx). *Never* — đóng `by_reason` thành 6-property fixed (vỡ khi Select đổi; handler build map động) · ép `current_open` non-null (value `None` hợp-lệ khi 0 log-mở) · `start_time/end_time` `format:date-time` (Frappe space-sep ≠ RFC3339) · bọc `{items}`/`{pagination}` top-level (flat object; `logs` là mảng con cap 10). **One-Version Rule:** web SPA `frontend/` dùng cùng endpoint (tab Dừng máy màn hồ-sơ) — 1 contract phục vụ cả web + mobile.

---

## III.20. Asset Audit-Chain Verify (1 endpoint) — Chuỗi kiểm toán bất biến

`verify_chain` — GET, param: `asset` (**required**). Kiểm-tra tính-toàn-vẹn hash-chain SHA-256 của `IMM Audit Trail` cho 1 asset (truy-vết NĐ98 — BR-00-03 / `AC-E010`).

**HAI hàm-nguồn** (return-shape KHÔNG ở handler mà ở builder):
- **Handler** `verify_chain(asset: str)` @`api/imm00.py:1768-1774` (bare `@frappe.whitelist()` → GET; guest dispatcher-403). `asset∄` → `_err(_(_ERR_ASSET_NOT_FOUND), 404)` @`:1771-1772` (in-handler Error envelope; Mobile-BE → HTTP-200 nhánh Error). Else `_ok(verify_audit_chain(asset))` @`:1774`.
- **Builder** `verify_audit_chain(asset) -> dict` @`utils/lifecycle.py:97-114` — **SoT return-shape**: đọc `tabIMM Audit Trail WHERE asset ORDER BY timestamp ASC, creation ASC` @`:98-107`, recompute `_compute_hash(r, prev)` từng hàng @`:110`, so `expected != r.hash_sha256 or (prev and r.prev_hash != prev)` @`:111`.

**2 return-shape (VERBATIM @source):**

| Nhánh | Shape | @source |
|---|---|---|
| **PASS** (chuỗi toàn vẹn) | `{"valid": True, "count": len(rows)}` — 2 key | `:114` |
| **FAIL** (phát hiện gãy) | `{"valid": False, "broken_at": r.name, "index": idx, "count": len(rows)}` — 4 key | `:112` |

- `valid` = **boolean GENUINE** (Python `True`/`False` literal — KHÔNG Frappe Check 0/1). `count` = số record audit đã duyệt (LUÔN present cả 2 nhánh). `broken_at` = mã record `IMM Audit Trail` tại điểm gãy · `index` = vị-trí 0-based trong chuỗi đã sắp `timestamp ASC` — **cả 2 CHỈ present khi `valid=false`**.
- Read-only — **KHÔNG audit** (verify KHÔNG mutate → 0 lifecycle event; nghịch-lý: kiểm chuỗi audit KHÔNG tự thêm mắt-xích).

> **📱 Cross-ref Mobile-BE — `verify_chain` (kiểm-tra toàn-vẹn chuỗi kiểm toán, asset-detail sub-tab #3, CR-11c 2026-07-13):** `getAssetVerifyChain` là sub-tab THỨ BA của CR-11 (sau `getAssetKpi` §III.1/ADR-038 + `getAssetDowntimeMetrics` §III.19/ADR-039) — tab "Chuỗi kiểm toán bất biến" màn hồ-sơ-thiết-bị; bằng-chứng truy-xuất-nguồn-gốc **NĐ98/2021** (BR-00-03). **LIVE whitelisted — KHÔNG đụng `.py`.** Contract đầy đủ (`AssetVerifyChain` closed `additionalProperties:false` **EXACT 4 prop** = HỢP 2 return-shape `{valid:boolean-GENUINE, count:integer, broken_at:string, index:integer}`; **`required` = EXACT 2 `{valid, count}`** = GIAO 2 shape — key có ở MỌI response; **`broken_at`+`index` OPTIONAL** ∉ required + `nullable:true`, **CHỈ present khi `valid=false`** — LẦN ĐẦU success-data schema có property OPTIONAL genuine-absent, mirror ADR-036 optional-emit; **INV-VC-1** prose-only: `broken_at` present ⟺ `index` present ⟺ `valid=false`, OpenAPI 3.0.3 KHÔNG mã-hoá né discriminator/if-then; `AssetVerifyChainEnvelope`; **200 = `oneOf[AssetVerifyChainEnvelope, Error]`** closed-schema Decision-B — `_err(404)` asset∄ @`:1771-1772` → HTTP-200 nhánh Error; slot `{200,401,403}`) đặc tả tại **mobile-contract** [`docs/mobile/04-api-contract.md` §8.42](../mobile/04-api-contract.md) + [`docs/mobile/openapi/assetcore-mobile.openapi.yaml`](../mobile/openapi/assetcore-mobile.openapi.yaml) (`operationId: getAssetVerifyChain`) + [ADR-MOBILE-040](../mobile/ADR-MOBILE-040.md). **Boundaries:** *Always* — curate VERBATIM 2 return-shape @builder `verify_audit_chain` (`required` = GIAO {valid,count}, `properties` = HỢP 4-key) · **⚠️ param `asset` KHÔNG `name`/`asset_name`** (chữ-ký @`:1769`) · `valid` GENUINE boolean (KHÔNG int-enum) · Decision-B lỗi nghiệp-vụ = HTTP-200 + Error envelope (KHÔNG raise→4xx). *Never* — ép `broken_at`/`index` vào `required` (nhánh PASS 2-key → strict codegen deser crash khi `valid=true`) · split `ValidChain|InvalidChain` discriminated oneOf (`valid` boolean → discriminator illegal + phá single-closed) · sinh audit event khi verify (read-only, tự-thay-chuỗi) · grounding chỉ đọc handler (return-shape ở builder `utils/lifecycle.py`). **One-Version Rule:** web SPA `frontend/` dùng cùng endpoint (tab Chuỗi kiểm toán màn hồ-sơ) — 1 contract phục vụ cả web + mobile.

---

## III.11. Scheduler Manual Trigger (3 endpoints — Admin only)

### `trigger_capa_overdue_check`

GET `assetcore.api.imm00.trigger_capa_overdue_check`. Permission: IMM System Admin / System Manager.

**Response 200:** `{ "triggered": "check_capa_overdue" }`

### `trigger_contract_expiry_check`

GET `assetcore.api.imm00.trigger_contract_expiry_check`. Permission: IMM System Admin.

**Response 200:** `{ "triggered": "check_vendor_contract_expiry" }`

### `trigger_registration_expiry_check`

GET `assetcore.api.imm00.trigger_registration_expiry_check`. Permission: IMM System Admin.

**Response 200:** `{ "triggered": "check_registration_expiry" }`

> **Lưu ý:** Các endpoints trigger là GET (không phải POST). Sử dụng `_assert_system_admin()` để check role.

---

## III.20. Inventory API — Spec only

> Inventory CRUD (Warehouse, Spare Part, Stock Movement) chưa có endpoint riêng trong `assetcore.api.imm00`. Các DocTypes `AC Warehouse`, `AC Spare Part`, `AC Spare Part Stock`, `AC Stock Movement` đã có trong codebase. Endpoints inventory sẽ được implement theo spec dưới đây khi cần.

Base path đề xuất: `assetcore.api.inventory.<function>`

Tất cả trả về `_ok(data)` / `_err(msg, code)` envelope chuẩn.

---

## III.21. Notification Preferences (3 endpoints — Notification Framework Wave N1)

Base path: `assetcore.api.notifications.<function>`. Envelope chuẩn `{success, data}`. Per-user — chỉ thao tác trên Notification Settings của chính user đang đăng nhập (System Manager có thể truyền `user`).

### `get_notification_preferences` — Đọc tùy chọn nhận email

`GET` · auth: session. Trả trạng thái toggle email của user hiện tại.

```jsonc
// Response
{ "success": true, "data": { "email_enabled": true } }
```

### `set_email_enabled` — Bật/tắt nhận email

`POST` · auth: session. Body: `{ "enabled": false }`. Set `Notification Settings.enable_email_notifications`.

```jsonc
// Request
{ "enabled": false }
// Response
{ "success": true, "data": { "email_enabled": false } }
```

> In-app (chuông) dùng API Frappe core sẵn có (`frappe.desk.doctype.notification_log.notification_log.get_notification_logs`, mark-as-read) — KHÔNG cần endpoint AssetCore riêng. Badge chuông là component desk/SPA Frappe core.

> **Cross-ref Mobile-BE — `mark_notification_as_read` (read-receipt, FLOW-6):** App mobile KHÔNG dùng được desk/SPA Frappe-core bell — cần endpoint REST riêng. AssetCore đã có sẵn cặp:
> - `api/layout.py:list_notifications()` (`@frappe.whitelist`, GET, paginated `{page, page_size, only_unread}`) — tab chuông + lịch-sử thông-báo (đã-đọc + chưa-đọc). Mobile contract `operationId: listNotifications` (xem `04-api-contract.md` + OpenAPI).
> - `api/layout.py:mark_notification_as_read(name)` (`@frappe.whitelist(methods=['POST'])`, POST) — **WRITE-action ĐẦU TIÊN trên domain Notification Log**: user tap/mở 1 thông-báo (tab chuông hoặc push deep-link flow-6) → set `read=1`. Ownership-guarded (`for_user == session.user` @`layout.py:111-113`); người khác → in-handler cap-403 (Error envelope HTTP-200). Notification∄ → 404 (Error envelope HTTP-200). LIVE whitelisted — **KHÔNG đụng `.py`**.
> - `api/layout.py:mark_all_as_read()` (`@frappe.whitelist(methods=['POST'])`, POST, **0-PARAM**) — **BULK read-receipt** (ĐÓNG NỐT notification-center action-set tab "Thông báo" › nút "Đánh dấu tất cả đã đọc", sau single ở trên): set `read=1` cho MỌI Notification Log chưa-đọc của chính user (`UPDATE … WHERE for_user=session.user AND read=0` @`layout.py:127-131`). Trả `_ok({updated_rows: affected})` @`:134` (`affected = ROW_COUNT()` @`:132`). Scope SQL `WHERE for_user=session.user` ⇒ **KHÔNG lookup-by-name** ⇒ **KHÔNG 404/409**. Guest @`:124-125` → in-handler 401 (Error envelope HTTP-200). LIVE whitelisted — **KHÔNG đụng `.py`**. Mobile contract `operationId: markAllAsRead`.
>
> Contract đầy đủ tại **mobile-contract** [`docs/mobile/openapi/assetcore-mobile.openapi.yaml`](../mobile/openapi/assetcore-mobile.openapi.yaml) (`operationId: markNotificationAsRead`, POST-only) + [`docs/mobile/04-api-contract.md`](../mobile/04-api-contract.md) + **ADR-IMM00-OPENAPI §FLOW-6 read-receipt**:
> - `requestBody` closed `{name}` (oneOf `application/json` + `application/x-www-form-urlencoded` — Frappe RPC `form_dict`); `200 = oneOf[MarkNotificationReadEnvelope, Error]` closed-schema route-by-VALUE `body.success` (0 discriminator); slot `{200,401,403}` (404 đến trên HTTP-200 qua `Error.http_status` enum chứa 404).
> - **`MarkNotificationReadResponse` EXACT 2 prop `{name, read}`** — `read = integer enum[0,1]` (mirror `NotificationListItem.read` SSoT int-vs-bool, KHÔNG boolean → né strict-codegen Dart/Kotlin deser crash). **KHÔNG có field `status`**: Notification Log KHÔNG có `workflow_state` ⇒ KHÔNG reuse mọi `*ActionResponse` lifecycle (đều mang `status`/domain-field) = **C3-split cross-domain**.
>
> **Cross-ref Mobile-BE — `mark_all_as_read` (BULK read-receipt, FLOW-6, Vòng 40):** Contract `operationId: markAllAsRead` tại [`docs/mobile/openapi/assetcore-mobile.openapi.yaml`](../mobile/openapi/assetcore-mobile.openapi.yaml) (POST-only, **KHÔNG requestBody** — `mark_all_as_read()` 0-param @`layout.py:121` ⇒ codegen no-arg POST) + **[`docs/mobile/ADR-MOBILE-018.md`](../mobile/ADR-MOBILE-018.md)** + **ADR-IMM00-OPENAPI §D-OAS-MARKALLREAD**:
> - `200 = oneOf[MarkAllReadEnvelope, Error]` closed-schema route-by-VALUE `body.success` (0 discriminator); slot `{200,401,403}` SINGLE-SHAPE `Forbidden` (guest/no-token dispatcher PermissionError HTTP-403; in-handler guest @`:124-125` → 401 đến trên HTTP-200) — **KHÔNG 404/409** (scope SQL `WHERE for_user=session.user`, no lookup-by-name).
> - **`MarkAllReadResponse` EXACT 1 prop `{updated_rows}`** — `updated_rows = integer` **GENUINE count (0..N)** GROUNDED `_ok({updated_rows: affected})` @`layout.py:134` (`affected = ROW_COUNT()` @`:132`); **KHÔNG enum[0,1]** (phân biệt với `read` int-enum của `NotificationListItem`/`MarkNotificationReadResponse` = cờ Check 2-giá-trị; mirror `AddMeasurementResponse.measurement_count`). **KHÔNG field `status`** (C3-split cross-domain ≠ mọi `*ActionResponse` lẫn `MarkNotificationReadResponse`).

> **Vòng 3 — E3 (Incident created) & E4 (Calibration due): KHÔNG có API endpoint AssetCore mới.** E3 là hook `Incident Report.after_insert`; E4 chạy trong scheduler `imm11.check_calibration_expiry` (daily). Cả hai chỉ phát Notification Log + email — tiêu thụ qua đúng API chuông Frappe core ở trên. FE KHÔNG cần client mới cho 2 event này (badge chuông hiện hữu đã hiển thị).

> **Vòng 4 — HTML email template + deep-link: KHÔNG có API endpoint mới, KHÔNG đổi shape endpoint nào.** Nâng cấp thuần server-side ở `_dispatch` (dựng HTML qua `_render_email`, gửi qua `_safe_sendmail`). 2 endpoint preference ở trên giữ nguyên contract. FE KHÔNG đổi (email render phía server; bell UI không đổi). Spec: `04_Backend_Design.md §III.1b-3`.

### `get_delivery_kpi` — KPI Notification Delivery (vòng 5, System Manager only)

`GET` · auth: session + **role System Manager** (raise `FORBIDDEN` nếu không). Query: `days` (int, mặc định 30, cửa sổ Email Queue). Đo độ phủ thông báo: tỷ lệ email gửi thành công (`delivery_rate`) và tỷ lệ user tắt email (`opt_out_rate`). Chỉ tính email AssetCore (lọc theo `reference_doctype ∈ {AC Asset, Incident Report, PM Work Order, Asset Repair}`). Công thức + ngưỡng màu: `04_Backend_Design.md §III.1b-4`.

```jsonc
// GET .../get_delivery_kpi?days=30  →  Response
{ "success": true, "data": {
    "delivery_rate": 97.5,        // null nếu mẫu rỗng (chia-0 guard)
    "sent": 39, "failed": 1,
    "opt_out_rate": 5.0,          // null nếu total_users=0
    "total_users": 20, "opted_out": 1,
    "window_days": 30,
    "delivery_status": "good",    // good|warn|bad|na → màu KPI card FE
    "opt_out_status": "good"
} }
```

> **Vòng 5 — Audit linkage:** từ vòng 5, `_dispatch` truyền `reference_doctype`/`reference_name` của doc vào `_safe_sendmail` → email AssetCore trở nên truy nguyên trong Email Queue (core). Email gửi trước vòng 5 (ref NULL) bị loại khỏi mẫu KPI — giới hạn đã nêu trong docstring. KHÔNG DocType mới. FE: 1 KPI card tái dùng `KpiCard.vue` (chỉ hiển thị cho System Manager).

---

## III.21b. Mobile OAS Mirror — CR-30 `getNotificationPreferences` + `setEmailEnabled` (Trục B / F3 "Cài đặt nhận thông báo")

> **Vòng 38 (BA / Trục-B mobile OAS) — CONTRACT-ONLY.** Backend `assetcore.api.notifications.{get_notification_preferences, set_email_enabled}` ĐÃ LIVE (§III.21 trên) nhưng **CHƯA curate** vào mobile-contract mirror `docs/mobile/openapi/assetcore-mobile.openapi.yaml` → app mobile chưa có typed-client cho màn **F3 "Tài khoản → Cài đặt nhận thông báo"** (bật/tắt nhận email). Đề mục này đặc tả contract để **BE (Bước 4)** thêm **2 path + 4 schema + 1 param** vào mirror. **0 dòng `.py` / 0 reload / 0 migrate** (backend LIVE; chỉ chạm YAML + test-guard + docs).

### Boundaries (Always / Never)

- **Always:** mọi shape GROUNDED 1:1 backend argspec + envelope `handle()` (không bịa field); 200 = `oneOf[<Envelope>, Error]` **Decision-B route-by-VALUE `body.success`** (KHÔNG discriminator, KHÔNG status-line cho lỗi nghiệp-vụ); reuse tag `notification` (đã tồn tại — 4 op: listNotifications/getUnreadNotifications/markNotificationAsRead/markAllAsRead); cả 2 path vào `_MVP_BUSINESS_PATHS` ⇒ **401∧403 symmetry** (test `test_mvp_path_401_403_symmetry` so SET `len(401-set)==len(403-set)` — thêm path phải cân cả hai vế).
- **Never:** KHÔNG sửa `api/notifications.py` / `services/notifications.py` (LIVE); KHÔNG model cap-403 của `setEmailEnabled` thành **status-line 403** (xem ADR-IMM00-OAS-NOTIFPREF-B — sai precedent); KHÔNG dùng `integer enum[0,1]` cho `email_enabled` (khác `read`/`enabled` của Notification Log — xem ADR-…-A note); KHÔNG đóng (`additionalProperties:false`) schema `NotificationPreferences` (cố ý MỞ — ADR-…-A).

### Grounding (backend → contract) — đọc trực tiếp, KHÔNG bịa

| Nguồn | File:line | Contract dẫn xuất |
|---|---|---|
| `get_notification_preferences(user: str = "")` `@frappe.whitelist()` **bare** | `api/notifications.py:17-18` | GET · opId `getNotificationPreferences` · param `user` (query, optional) · guest→dispatcher-403 |
| getter `return {"email_enabled": bool(is_email_notifications_enabled(target))}` | `services/notifications.py:1278,1285` | `data = NotificationPreferences{email_enabled: boolean}` · **KHÔNG** admin-guard trong getter (đọc pref user khác nếu truyền `user=` — xem ⚠️ backlog dưới) |
| `set_email_enabled(enabled: bool = True, user: str = "")` `@frappe.whitelist(methods=["POST"])` | `api/notifications.py:26-27` | POST-only · opId `setEmailEnabled` · body `{enabled, user?}` |
| setter admin-guard `if target != session.user and not is_admin(): raise ServiceError(FORBIDDEN, …)` | `services/notifications.py:1296-1301` | **in-handler cap-403** (admin→user khác REACHABLE) → `handle()` → HTTP-200 Error-branch (ADR-…-B) |
| setter `return {"email_enabled": bool(enabled)}` | `services/notifications.py:1311-1315` | `SetEmailEnabledEnvelope.data` = echo `NotificationPreferences` SAU cập nhật |
| `handle()` = `_ok(fn())` \| `except ServiceError → _err(…, http_status=e.http_status)` | `utils/api_handler.py:48-51`, `utils/response.py:133-154` | `_err` nhét `http_status` vào **body**, KHÔNG set status-line ⇒ lỗi đến TRÊN **HTTP-200** = Decision-B |

### Path 1 — `GET /api/method/assetcore.api.notifications.get_notification_preferences`

- `tags: [notification]` · `operationId: getNotificationPreferences` · **GET-only**.
- `parameters: [$ref NotificationPrefUser]`.
- `responses`: `'200'` = **INLINE** `oneOf[NotificationPreferencesEnvelope, Error]` (read-path inline mirror `getUnreadNotifications` @yaml:13026) · `'401': $ref Unauthorized401` · `'403': $ref Forbidden` (**SINGLE-SHAPE** dispatcher guest/no-token — getter KHÔNG raise FORBIDDEN ⇒ 403 status-line CHỈ do guest).

### Path 2 — `POST /api/method/assetcore.api.notifications.set_email_enabled`

- `tags: [notification]` · `operationId: setEmailEnabled` · **POST-only** (mirror `@whitelist(methods=['POST'])`).
- `requestBody: required` · content 2 media-type `application/json` + `application/x-www-form-urlencoded` (Frappe RPC `form_dict`) · `$ref SetEmailEnabledRequest`.
- `responses`: `'200'` = **INLINE** `oneOf[SetEmailEnabledEnvelope, Error]` (action-path inline mirror `markNotificationAsRead` @yaml:13080) — **nhánh Error mang cap-403** (`Error.http_status ∋ 403`, `code:FORBIDDEN` khi non-admin truyền `user=` người khác) · `'401': $ref Unauthorized401` · `'403': $ref Forbidden` (SINGLE-SHAPE dispatcher guest/no-token).

### 4 schema (grounded)

1. **`NotificationPreferences`** (payload `data`) — `type: object` · **`additionalProperties: true`** (cố ý MỞ — ADR-…-A) · `properties.email_enabled: {type: boolean}` · `required: [email_enabled]`. Grounded `{"email_enabled": bool(...)}` @`services/notifications.py:1285,1315` — wire = **JSON boolean thật** (service ép `bool(...)`), KHÔNG int 0/1.
2. **`NotificationPreferencesEnvelope`** (get-success) — closed (`additionalProperties:false`) · `success: {type: boolean, enum:[true]}` · `data: {$ref NotificationPreferences}` · `required: [success, data]`.
3. **`SetEmailEnabledEnvelope`** (set-success) — closed · `success: enum[true]` · `data: {$ref NotificationPreferences}` (echo pref SAU cập nhật) · `required: [success, data]`.
4. **`SetEmailEnabledRequest`** (set-body) — closed · `properties.enabled: {type: boolean}` + `properties.user: {type: string}` (optional) · `required: [enabled]`. Grounded `set_email_enabled(enabled: bool = True, user: str = "")` @`api/notifications.py:27`. **Quyết định:** `required:[enabled]` DÙ signature default `True` — contract ép client gửi ý-định-tường-minh (tránh vô-tình bật email khi bỏ trống).

### Param — `NotificationPrefUser`

Component parameter: `name: user` · `in: query` · `required: false` · `schema.type: string` (mirror typed-param CR-05). Mô-tả: System Manager truyền để đọc pref user khác; bỏ trống ⇒ session user hiện tại. ⚠️ **backlog (Cần khảo sát RBAC):** getter `get_notification_preferences` **KHÔNG** admin-guard `user=` (khác setter) → mọi user auth đọc được `email_enabled` của user khác. Contract mirror đúng LIVE-behavior (param tồn tại, getter 0 cap-403); nếu siết → sửa `.py` ở đề mục BE riêng (NGOÀI CR-30 contract-only).

### ADR-IMM00-OAS-NOTIFPREF-A: `NotificationPreferences` MỞ (`additionalProperties: true`)

- **Status**: Accepted · **Date**: 2026-07-14
- **Context**: 3 envelope + request đều closed (convention mirror). Nhưng `NotificationPreferences` là **container tùy-chọn** sẽ nở theo thời gian (push FCM, SMS, in-app…). Đóng cứng ⇒ mỗi lần backend thêm 1 toggle phải sửa contract + regenerate client mọi platform.
- **Decision**: `NotificationPreferences.additionalProperties: **true**` — forward-reserve loại toggle khác (`push_enabled`, `sms_enabled`, `in_app_enabled`…). CHỈ `email_enabled` khai property + required (LIVE hiện chỉ có nó @`:1285`).
- **Alternatives**: (a) closed + bump mỗi lần → churn client; (b) `oneOf` biến-thể → codegen phức tạp. Loại.
- **Consequences**: schema đóng-mở KHÔNG đồng-nhất trong mirror → guard test PHẢI assert `additionalProperties==true` cho RIÊNG `NotificationPreferences` (chống drift ai đó "sửa cho đồng bộ" thành false). 3 envelope quanh nó VẪN closed → route-by-VALUE oneOf (disjoint required-set) KHÔNG bị ảnh hưởng (Error mang `error/code/http_status` ∉ required của Envelope).

### ADR-IMM00-OAS-NOTIFPREF-B: cap-403 của `setEmailEnabled` = in-handler HTTP-200 Error-branch (**Self-Correction** — KHÔNG cancelCalibration)

- **Status**: Accepted · **Date**: 2026-07-14
- **Context**: Đề mục gốc nêu "setEmailEnabled declare 403 … đối xứng precedent CR-CAL-EXT-03 `cancelCalibration` 403-cap-branch". **Sai precedent về CƠ-CHẾ:** 2 endpoint tạo 403 bằng 2 đường KHÁC NHAU:
  - `cancelCalibration` @`api/imm11.py:196-198`: `rbac.require("calibration.cancel")` → `frappe.PermissionError` (raw) **TRƯỚC** `handle()` → propagate dispatcher → **403 status-line THẬT** + body `FrappeRawError`. `'403'`-slot REACHABLE bởi user auth thiếu cap (test `…cancelcal_g_response_slots_403_reachable_single_forbidden`).
  - `setEmailEnabled` @`services/notifications.py:1298`: `raise ServiceError(FORBIDDEN)` **TRONG** service → `handle()` bắt → `_err(http_status=403)` → **HTTP-200** body Error (route-by-VALUE). Cap-403 (admin→user khác) đến TRÊN 200, **KHÔNG** status-line.
- **Decision**: `setEmailEnabled` mirror **`markNotificationAsRead`** (@yaml:13042-13084 — cùng cơ-chế in-handler cap-403 qua ownership-guard), KHÔNG `cancelCalibration`:
  1. `'403'`-slot = **SINGLE-SHAPE `Forbidden`** (CHỈ dispatcher guest/no-token → 403 status-line raw). KHÔNG dual-shape `oneOf[Error, FrappeRawError]` (đó là `ReportIncidentForbidden`, dành path field-tech cap-403 phổ-biến).
  2. cap-403 nghiệp-vụ (non-admin `user=` người khác) NẰM ở **nhánh Error của 200-oneOf** (`Error.http_status ∋ 403`, `code:FORBIDDEN`) — client SHOW-MESSAGE, KHÔNG re-auth.
- **Alternatives**: (a) copy `cancelCalibration` → wire cap-403 thành status-line ⇒ codegen sinh client CHỜ 403-line cho nhánh admin-override, nhưng runtime trả HTTP-200 ⇒ **deser-route SAI**. Loại. (b) dual-shape `ReportIncidentForbidden` → thừa (cap-403 đã ở 200-branch; guest-403 đơn-hình đủ). Loại.
- **Consequences**: DONE-gate spec-contract (LL-BE-42..49): lỗi nghiệp-vụ = in-handler HTTP-200 + Error envelope (KHÔNG raise→HTTP-4xx); phân biệt rõ 2 loại 403 khi đặc tả. Guard `setEmailEnabled` PHẢI: `'403'`-slot == `$ref Forbidden` (single-shape) + 200-oneOf CÓ `Error` (cover cap-403). `getNotificationPreferences` 200-oneOf cũng có `Error` (defensive/uniform) nhưng KHÔNG cap-403 nghiệp-vụ (getter 0 FORBIDDEN).

### Count deltas + guard vars (BE Bước-4 sync theo delta THẬT)

- **Mirror**: path/opId **77 → 79** (+2, tag `notification` reuse) · `c5_paths` +2 (cả 2 path 200-oneOf) · cả 2 ∈ `_MVP_BUSINESS_PATHS` ⇒ 401-set/403-set mỗi vế +2 (symmetry giữ cân) · `getNotificationPreferences` ∈ `_MVP_READ_ENVELOPE` (inline read-oneOf, mirror `getUnreadNotifications`) · KHÔNG ∈ `_MVP_LIST_ENVELOPE` (không phải list `data.items[]`).
- **`test_mobile_oas.py`**: `_EXPECTED_TEST_COUNT` += (số TC 2 class guard mới, ~10-14) · path/opId 77→79 · `c5_paths` · `_MVP_BUSINESS_PATHS` (401/403 symmetry set). 2 class guard đề xuất: `TestMobileNotifPrefGetContract` (path+opId+param+200-oneOf+401/403-slot + `NotificationPreferences.additionalProperties==true` + `email_enabled` boolean-KHÔNG-int + `NotificationPreferencesEnvelope` closed) + `TestMobileSetEmailEnabledContract` (POST-only+requestBody 2 media-type + `SetEmailEnabledRequest` closed `required[enabled]` + `SetEmailEnabledEnvelope` closed echo + 403-slot single-shape Forbidden + 200-oneOf CÓ Error cap-403 + symmetry no-dangling).
- **`test_mobile_docset.py`**: `_GUARD_SUITE_EXPECTED["test_mobile_oas.py"]` += same delta · `_GUARD_SUITE_SUM` += same · `_MOBILE_OAS_TOTAL` += same.
- **Runtime parity** (`TestMobileSpecParityRuntime`): 2 dotted-path resolve + `is_whitelisted` LIVE — `get_notification_preferences` bare `@whitelist`, `set_email_enabled` `@whitelist(methods=['POST'])` (grounded @`api/notifications.py:17,26`).
- **DoD**: `bench --site miyano run-tests` cho `test_mobile_oas` + `test_mobile_docset` = "Ran N OK" THẬT (gồm 2 class mới); mọi mobile-contract test cũ GREEN (0 regression). ADR-MOBILE-049 (YAML curate record) do **BE** author ở Bước-4 (tránh giẫm role + numbering-race). Working tree để USER review — KHÔNG commit.

---

## III.22. Pending Approvals Inbox — CR-32 `get_pending_approvals_inbox` (endpoint gộp "Phiếu chờ tôi duyệt" xuyên module: Nghiệm thu + Điều chuyển + Cấp phát/Xuất kho phụ tùng + Nghiệm thu CM)

> **Vòng 2 (BA / APPROVAL-INBOX-CR32) — endpoint MỚI (KHÁC CR-30/31/34 contract-only): BE viết `.py` TRƯỚC rồi curate mirror VERBATIM theo response THẬT.** Quyết định kiến trúc: [`ADR-IMM00-APPROVAL-INBOX.md`](./ADR-IMM00-APPROVAL-INBOX.md) (A: aggregation @imm00 + cap-SSoT silent-exclude · B: `route` server-computed + allocation WO-drill · C: envelope/`by_module`/KPI-parity · **D (CR-42): nguồn thứ 4 CM 'Pending Inspection' + SoD loại self-closed**). FE spec: [`06_Frontend_Design.md` §III.11](./06_Frontend_Design.md). **0 DocType change ⇒ 0 migrate;** `.py` mới ⇒ live-HTTP cần gunicorn reload (**HARD-STOP user — chỉ ghi chú deploy trong báo cáo**).
>
> **🔺 CR-42 delta (Vòng 2 kế / IMM-00↔IMM-09) — NGUỒN THỨ 4 `imm09` = phiếu CM 'Pending Inspection' chờ nghiệm thu, SoD-scoped, migrate-free.** Bổ sung 1 block nguồn vào `get_pending_approvals_inbox` (service), 1 khóa `imm09` vào `by_module`, enum item mở rộng (`doctype += 'Asset Repair'`, `module += imm09`). Slice **contract (OAS + shape-guard) đóng ở Bước-2 (BA)**; slice **application code (`services/imm00.py` block nguồn-d + helper batch closer `services/imm09.py`) = [BE] Bước-4**. Chi tiết: §"Nguồn thứ 4 — CR-42" bên dưới + [`ADR-IMM00-APPROVAL-INBOX.md` §D](./ADR-IMM00-APPROVAL-INBOX.md).

> **🔺 CR-43 delta (Vòng 2 — hợp đồng TRUNG THỰC khi cắt) — inbox công bố `truncated` / `totals_uncapped` / `excluded_modules` thay vì cắt IM LẶNG ở trần 50/nguồn.** `data` 3→6 khóa (ADDITIVE-OPTIONAL). Slice **contract (OAS + shape-guard `test_mobile_oas` đã verify `Ran 893 OK`) đóng ở Bước-2 (BA)**; slice **application code (`services/imm00.py` compute 3 field + zero-cost conditional COUNT) = [BE] Bước-4**. Chi tiết: §"CR-43 — Hợp đồng TRUNG THỰC khi cắt" bên dưới + [`ADR-IMM00-APPROVAL-INBOX.md` §F](./ADR-IMM00-APPROVAL-INBOX.md).
>
> **🔺 CR-44 delta (Vòng 4 / IMM-00) — FIELD `summary` = tóm tắt VI ≤120 ký tự do SERVER dựng cho MỖI dòng, chống "duyệt mù" vết custody NĐ98. Additive, migrate-free, session-scoped GIỮ.** Item shape 10→**11 khóa** (thêm `summary`, string, LUÔN emit coalesce '', ≤120 ký tự). Slice **contract (OAS `PendingApprovalItem` += `summary` vào props+required, shape-guard `test_mobile_oas`) đóng ở Bước-2 (BA)**; slice **application code (`_inbox_item` kwarg `summary` + `_enrich_inbox_items` +3 batch query + 4 helper `_summarize_*` + `test_imm00_approvals_inbox._ITEM_KEYS` 10→11 + TC nội dung) = [BE] Bước-4**. Chi tiết: §"Field `summary` — CR-44" bên dưới + [`ADR-IMM00-APPROVAL-INBOX.md` §E](./ADR-IMM00-APPROVAL-INBOX.md). **0 param mới (signature `**_ignore` bất biến) · 0 DocType change ⇒ 0 migrate · count==rows GIỮ (summary không đổi số dòng).**

### Endpoint

- **`GET /api/method/assetcore.api.imm00.get_pending_approvals_inbox`**
- Handler `api/imm00.py`: `@frappe.whitelist()` bare (KHÔNG `allow_guest` → guest **dispatcher-403**) · signature `def get_pending_approvals_inbox(**_ignore) -> dict` → `return handle(svc.get_pending_approvals_inbox)`.
  - **`**_ignore` nuốt kwargs lạ (kể cả `user=`) — session-scoped, chống spoof** (precedent `attach_repair_checklist_photo` @`api/imm09.py:59`, `attach_incident_photo` @`api/imm12.py:295`). Service KHÔNG nhận tham số — identity DUY NHẤT = `frappe.session.user`.
- Service `services/imm00.py`: `def get_pending_approvals_inbox() -> dict` (type hints + docstring bắt buộc — CLAUDE.md §15).
- Envelope **Decision-B qua `handle()`** (@`utils/api_handler.py:33`): success → `{"success": true, "data": {...}}`. Endpoint KHÔNG có nhánh lỗi nghiệp vụ (thiếu cap = exclude im lặng, KHÔNG raise) ⇒ 0 in-handler cap-403; **2 loại 403**: chỉ còn dispatcher-403 (guest/no-token).

### Response `data` shape

```jsonc
{
  "items": [                       // sort pending_since ASC, tie-break name ASC (server-side — SSoT)
    {
      "doctype": "Asset Transfer",           // ∈ {"Asset Commissioning","Asset Transfer","IMM Spare Allocation","Asset Repair"} — CR-42 +Asset Repair
      "name": "AT-2026-0001",
      "module": "imm00",                     // ∈ {"imm04","imm00","imm15","imm09"} — khóa máy; nhãn VI do FE render (CR-42 +imm09)
      "title": "Chuyển máy thở sang ICU",    // per-module derivation (bảng dưới)
      "asset": "AST-0001",                   // '' khi chưa có (imm04 pre-registration)
      "asset_name": "Máy thở Bennett 840",   // bulk-enrich AC Asset.asset_name, coalesce ''
      "requested_by": "user@x.vn",
      "requested_by_name": "Nguyễn Văn A",   // bulk-enrich User.full_name, coalesce requested_by
      "pending_since": "2026-07-10 08:30:00",// datetime string — mốc phiếu vào hàng chờ
      "route": "/asset-transfers/AT-2026-0001", // server-computed, LUÔN non-empty (ADR-…-B)
      "summary": "Khoa Hồi sức → Khoa Cấp cứu · Máy thở Bennett 840" // CR-44: tóm tắt VI ≤120, server-built, coalesce ''
    }
  ],
  "total": 3,                       // == len(items) == sum(by_module.values()) — count==rows (LL-BE-49)
  "by_module": {"imm04": 1, "imm00": 1, "imm15": 1, "imm09": 0},  // CR-42: LUÔN đủ 4 khóa, nguồn exclude/rỗng = 0
  "truncated": 0,                   // CR-43: int 0/1 — 1 nếu ∃ nguồn chạm trần (totals_uncapped[m] > by_module[m])
  "totals_uncapped": {"imm04": 1, "imm00": 1, "imm15": 1, "imm09": 0}, // CR-43: tổng UNCAPPED; = by_module khi KHÔNG chạm trần (zero-cost); imm09 = cận-trên PRE-SoD
  "excluded_modules": []            // CR-43: nguồn bị LOẠI vì THIẾU cap ⊆ {imm00,imm15,imm09}; imm04 identity-based KHÔNG bao giờ có
}
```

Mọi giá trị item = **string non-nullable** (coalesce `''` — pattern `_str_or_blank`). Item đúng **11 khóa** (CR-44 +`summary`) — không thêm/bớt. `data` = **6 khóa** (CR-43 +`truncated`/`totals_uncapped`/`excluded_modules`).

### CR-43 — Hợp đồng TRUNG THỰC khi cắt (`truncated` / `totals_uncapped` / `excluded_modules`)

> **Quyết định kiến trúc: [`ADR-IMM00-APPROVAL-INBOX.md §F`](./ADR-IMM00-APPROVAL-INBOX.md).** Inbox cắt MỖI nguồn ở `_INBOX_LIMIT_PER_SOURCE=50` (oldest-first). Cắt IM LẶNG = người duyệt tưởng đã hết → bỏ sót phiếu chờ (vết custody NĐ98). 3 khóa ADDITIVE công bố sự thật cắt. **Slice contract (OAS + shape-guard) đóng ở Bước-2 (BA); application code (`services/imm00.py`) = [BE] Bước-4.**

| Khóa | Kiểu | Ngữ nghĩa |
|---|---|---|
| `truncated` | int ∈ {0,1} | `1` nếu ∃ module `m`: `totals_uncapped[m] > by_module[m]` (≥1 nguồn chạm trần và tổng thật > số hiển thị). **int, KHÔNG bool/None** (parity CR-01). |
| `totals_uncapped` | dict 4 khóa `{imm00,imm04,imm15,imm09}` → int | Tổng UNCAPPED mỗi module. **ZERO-COST:** mặc định = `by_module[m]` (KHÔNG query); CHỈ khi nguồn `len(fetched) >= _INBOX_LIMIT_PER_SOURCE` mới thay bằng **COUNT DB thật** (cùng predicate get_all nguồn đó). `totals_uncapped['imm09']` khi chạm trần = **cận-trên PRE-SoD** (COUNT predicate `{status:'Pending Inspection', docstatus:0}` TRƯỚC bước loại self-closer CR-41). ⚠️ KHÁC `by_module` (count==rows) — **được phép > `len(items)`**. |
| `excluded_modules` | list[str] ⊆ `{imm00,imm15,imm09}` | Nguồn cap-based bị LOẠI vì caller **thiếu cap** (`rbac.can(cap)` False). **`imm04` identity-based KHÔNG bao giờ có mặt.** RỖNG khi đủ quyền mọi nguồn. FE map nhãn nghiệp vụ VI (imm00→Điều chuyển thiết bị · imm15→Cấp phát phụ tùng · imm09→Nghiệm thu sau sửa chữa). |

- **AC2 zero-cost (test đếm query / spy count-fn):** khi 0 nguồn chạm trần ⇒ `truncated==0` ∧ `totals_uncapped[m]==by_module[m]` ∀m ∧ **0 lời gọi COUNT phát thêm**. BE PHẢI cho count đi qua điểm-quan-sát-được (`frappe.db.count(doctype, filters)` hoặc helper `_count_uncapped`) để test monkeypatch xác nhận không-gọi.
- **AC3 chạm trần (test hạ `_INBOX_LIMIT_PER_SOURCE=1`, seed 2 Asset Transfer Pending):** `truncated==1` ∧ `by_module['imm00']==1` ∧ `totals_uncapped['imm00']==2` (COUNT DB cùng predicate).
- **§BE task (application code — [BE] Bước-4, KHÔNG thuộc slice contract BA):** trong `get_pending_approvals_inbox` @`services/imm00.py`: (1) sau mỗi block nguồn cap-based, so `len(rows_fetched)` với `_INBOX_LIMIT_PER_SOURCE` → set `totals_uncapped[m]` = COUNT thật (guard-if) hoặc = `by_module[m]`; (2) `excluded_modules.append(m)` khi `rbac.can(cap)` False (transfer→imm00, allocation→imm15, repair→imm09; imm04 KHÔNG); (3) `truncated = int(any(totals_uncapped[m] > by_module[m] for m))`; (4) count qua điểm-quan-sát để test spy. **Live-HTTP cần gunicorn `--preload` reload (HARD-STOP user).**

### 4 nguồn (CR-32: 3 nguồn · CR-42: +imm09) — điều kiện "chờ" + gate quyền (SSoT cap CÓ SẴN, KHÔNG hardcode role-name — chống RBAC dead-gate)

| module | doctype | Điều kiện "chờ duyệt" | Gate quyền (grounded) | `pending_since` | `title` | `requested_by` |
|---|---|---|---|---|---|---|
| `imm04` | Asset Commissioning | `pending_approver == session.user` **AND** `docstatus != 2` — parity `list_my_pending_approvals` @`services/imm04.py:1820-1838` + `count_pending_approvals` @`services/imm00.py:3003` | **identity-based** (KHÔNG cap — filter chính là scope) | `approval_submitted_at` fallback `creation` | `asset_description` → `master_item` → `name` | `owner` |
| `imm00` | Asset Transfer | `status == 'Pending Approval'` (`_TRANSFER_STATUS_PENDING` @`services/imm00.py:2634`) | `rbac.can(_TRANSFER_APPROVE_CAP)` = `'commissioning.submit'` @`:2604` — CÙNG cap `approve_transfer_request` enforce @`:2719` | `creation` | `reason` (required lúc tạo @`:2574`) → `transfer_type` | `owner` (doctype KHÔNG có field requested_by) |
| `imm15` | IMM Spare Allocation | `allocation_status == 'Requested'` (`AllocationStatus.REQUESTED`) | `rbac.can(_CAP_APPROVE)` = `'inventory.submit'` @`services/imm15.py:96` — CÙNG cap `approve_allocation` enforce @`:291`; **lazy-import trong function body** (Pattern B) | `creation` (`requested_date` là Date-only, thiếu độ chính xác sort) | `work_order_ref` → `name` | `requested_by` fallback `owner` |
| `imm09` **(CR-42)** | Asset Repair | `status == 'Pending Inspection'` (`RepairStatus.PENDING_INSPECTION`) **AND** `docstatus == 0` (WO chưa submit ở bước này — @`docs/imm-09/05 §close_work_order`) **AND** người-đóng-phiếu ≠ `session.user` (**SoD**, loại self-closed — xem BR-00-INBOX-03) | `rbac.can(_imm09._CAP_SUBMIT)` = `'repair.submit'` — **CÙNG cap `confirm_inspection` enforce** @`services/imm09.py:1806`; **lazy-import trong function body** (Pattern B) · ⚠️ BE tạo hằng SSoT `_CAP_SUBMIT` (§BE task) | `modified` (mốc vào Pending Inspection — `close_work_order` là lần save cuối trước nghiệm thu) | `failure_description` → `name` | field `requested_by` (Link User trên Asset Repair) fallback `owner` |

- `asset`/`asset_name`: imm04 = `final_asset`/`asset_description`→`master_item` (phiếu nghiệm thu CHƯA có AC Asset — `asset` thường `''`); imm00/imm15 = field `asset`; **imm09 = field `asset_ref`** (Link AC Asset trên Asset Repair) → gán vào `asset`; tất cả bulk-enrich `AC Asset.asset_name` (**1 query gộp cho toàn items — no N+1**, tái dùng `_enrich_inbox_items` HIỆN CÓ — 0 sửa enrich).
- Thiếu cap nguồn cap-based → **EXCLUDE im lặng** (0 query nguồn đó); 0 nguồn khả dụng → `success: true` + `items: []` + `total: 0` + `by_module` all-0 (**KHÔNG lỗi**). **imm09: user KHÔNG có `repair.submit` → 0 item `module=='imm09'`, KHÔNG lỗi** (đối xứng transfer/allocation).
- Mỗi nguồn giới hạn **50 dòng** (parity limit `list_my_pending_approvals` @`:1828`), lấy **oldest-first TRƯỚC khi cap** — phiếu chờ lâu nhất luôn hiện.
- `route` map (ADR-…-B): `imm04 → /commissioning/{name}` (`router/index.ts:235`) · `imm00 → /asset-transfers/{name}` (`:605`) · `imm15` WO-drill theo `work_order_doctype`: chứa `"PM"` → `/pm/work-orders/{work_order_ref}` (`:319`); `"Asset Repair"`/chứa `"CM"` → `/cm/work-orders/{work_order_ref}` (`:360`); thiếu ref → `/inventory` (`:668`) · **`imm09 → /cm/work-orders/{name}`** (`router/index.ts:360`, deep-link màn CM detail — nút Nghiệm thu ở detail theo `allowed_transitions`).

### Nguồn thứ 4 — CR-42 (SoD scope + batch closer-resolution, migrate-free)

- **SoD (Segregation of Duties) — đối xứng CR-41 vòng 1.** `confirm_inspection` (IMM-09, BR-09-SOD/CR-41) đã CHẶN người tự-đóng-phiếu tự-nghiệm-thu (`closer == session.user` → `FORBIDDEN`, in-handler HTTP-200 + Error envelope; xem [`docs/imm-09/05 §confirm_inspection`](../imm-09/05_API_Specification.md)). Inbox CR-42 **đối xứng ở tầng danh sách**: WO mà chính `session.user` tự đóng **KHÔNG xuất hiện** trong inbox của họ → không tạo dòng "duyệt mù" (click → SoD `FORBIDDEN` dead-end). "Người đóng phiếu" đọc **migrate-free** từ Asset Lifecycle Event `repair_pending_inspection` (`root_doctype='Asset Repair'`, `root_record=name`, `actor` của event mới nhất) — **tái dùng `_resolve_wo_closer`** (`services/imm09.py:1769`, SSoT CR-41).
- **Fail-open (đối xứng CR-41 INV-CM-SOD-2).** Closer không xác định được (không có event `repair_pending_inspection` — legacy) → `_resolve_wo_closer` trả `None` → **VẪN HIỆN** trong inbox (không đủ dữ liệu để chặn ⇒ ưu tiên không bỏ sót phiếu chờ; cùng nguyên tắc fail-open của `confirm_inspection`).
- **No N+1 — closer-resolution batch.** WO 'Pending Inspection' cần resolve closer cho MỌI dòng để lọc SoD. BE **[Bước-4]** thêm helper batch `_resolve_wo_closers(names: list[str]) -> dict[str, str | None]` @`services/imm09.py` = **1 `get_all` Asset Lifecycle Event** (`root_record IN [...]`, `event_type='repair_pending_inspection'`, order `creation desc`, dedup lấy actor mới nhất/WO) → imm00 lazy-import. **Ngưỡng chấp nhận thay thế:** vì queue Pending Inspection nhỏ (cap 50), 1-query/phiếu qua `_resolve_wo_closer` cũng đạt — **NHƯNG batch là khuyến nghị** (O(1) query, xác định bất kể queue). Enrich display (`asset_name`/`requested_by_name`) **BẮT BUỘC batch** qua `_enrich_inbox_items` hiện có — **KHÔNG per-item query enrich trong vòng lặp** (LL-BE-2).
- **Invariant count==rows GIỮ (BR-00-INBOX-02).** WO bị SoD loại → không append vào `items` ngay từ đầu ⇒ `total == len(items) == sum(by_module.values())` vẫn đúng (KHÔNG đếm DB riêng rồi trừ). `by_module` thêm khóa `imm09` (đủ **4 khóa** cố định, 0 khi rỗng/thiếu cap).
- **§BE task (application code — [BE] Bước-4, KHÔNG thuộc slice contract BA):** (1) hằng SSoT `_CAP_SUBMIT = "repair.submit"` @`services/imm09.py` (hiện `repair.submit` hardcode 2 chỗ: `services/imm09.py:1806` + `api/imm09.py:182`) → refactor `confirm_inspection` dùng hằng + imm00 lazy-import (chống hardcode chuỗi cap, đối xứng `_imm15._CAP_APPROVE`); (2) helper batch `_resolve_wo_closers`; (3) block nguồn-d trong `get_pending_approvals_inbox` @`services/imm00.py` (sau block imm15, trước `_enrich_inbox_items`); (4) `by_module` init thêm `"imm09": 0`; (5) TC mới trong `test_imm00_approvals_inbox.py` (§Test plan). **Live-HTTP cần gunicorn `--preload` reload (HARD-STOP user).**

### Field `summary` — CR-44 (tóm tắt VI server-built ≤120 ký tự, chống "duyệt mù")

> **Vấn đề:** `title` chỉ là **1 mảnh đơn** theo module → người duyệt hàng loạt không thấy **nội dung phiếu** ("chuyển từ đâu sang đâu / cấp phát gì bao nhiêu / nghiệm thu bậc mấy") nếu không mở từng detail = **"duyệt mù"**, làm hỏng giá trị audit của chữ ký duyệt trên **vết custody NĐ98**. `summary` bổ sung 1 dòng phụ mô tả **cái đang được duyệt** — advisory (nút Duyệt vẫn ở detail view theo `allowed_transitions`, GATE-8). Quyết định: [`ADR-IMM00-APPROVAL-INBOX.md` §E](./ADR-IMM00-APPROVAL-INBOX.md).

- **Bất biến `summary`:** string **LUÔN emit** (coalesce `''` — KHÔNG null) · độ dài **≤120 ký tự** (server hard-cap: vượt → cắt 119 + `'…'` U+2026 = 120) · thiếu dữ liệu / dangling FK → phần lấy được hoặc `''` (**non-crash, KHÔNG raise**) · **server-built** (SSoT 1 chỗ, client chỉ render).

**Composition per-source (grounded @source — field THẬT, KHÔNG bịa):**

| module | Mẫu `summary` | Nguồn dữ liệu (grounded) | Denorm cần |
|---|---|---|---|
| `imm00` Asset Transfer | `'<src> → <dst> · <asset_name>'` | `src`=`from_department`→`AC Department.department_name` fallback `from_location`→`AC Location.location_name` fallback ''; `dst`=`to_department`/`to_location` tương tự; `asset_name`=enrich sẵn (@`asset_transfer.json`: from/to_department Link AC Department, from/to_location Link AC Location) | **+2 batch**: AC Department.department_name · AC Location.location_name |
| `imm15` IMM Spare Allocation | `'<item_name> ×<qty> <uom>'` + `' …+N'` (N=dòng còn lại) | dòng ĐẦU child `IMM Spare Allocation Item` (order `idx`): `part_name` (đã denorm @child) fallback `spare_part`; `qty`=`qty_requested` (Float, bỏ `.0` đuôi); `uom`=Link `uom` (PK=`uom_name` autoname `field:uom_name` @`ac_uom.json` → dùng thẳng) | **+1 batch**: IMM Spare Allocation Item (`parent IN […]`, order `parent, idx`) group-by-parent |
| `imm04` Asset Commissioning | `'Nghiệm thu ban đầu · bậc <stage_index>/<stage_total>'` | `approval_stage` Select @`asset_commissioning.json` = SSoT 4 bậc **Doc Verify · Facility Check · Baseline Review · Clinical Release** (đã có trong `list_my_pending_approvals` return @`services/imm04.py`); `stage_index`=vị trí 1-based, `stage_total`=`len(tuple)` (**derive, KHÔNG hardcode 4**); stage rỗng/không khớp → bỏ mảnh 'bậc' → `'Nghiệm thu ban đầu'` | 0 query thêm (field trên row nguồn) |
| `imm09` Asset Repair CM | `'<failure rút gọn> · <asset_name>'` | `failure`=`failure_description`→`repair_summary` (đã fetch @builder nguồn-d); cắt free-text để tổng ≤120 **giữ hậu tố** `' · <asset_name>'`; `asset_name`=enrich từ `asset_ref` | 0 query thêm (field trên row nguồn) |

- **Build-site (no-N+1):** summary phụ thuộc denorm (dept/loc name · child lines · enriched `asset_name`) → dựng **trong `_enrich_inbox_items`** SAU khi batch-map build; `imm04` (chỉ cần `approval_stage`, 0 denorm) có thể dựng ngay @builder qua kwarg mới `summary` của `_inbox_item` (default `''`). Raw source fields cho summary carry qua **per-source aux list** (song song `comm_aux`): `transfer_aux` (idx→4 id from/to dept/loc), allocation lookup child theo `item['name']`, `repair_aux` (idx→failure text).
- **Batch denorm CR-44 = +3 query cố định** (độc lập N): (1) **AC Department** gộp mọi from/to dept id → `department_name`; (2) **AC Location** gộp mọi from/to location id → `location_name`; (3) **IMM Spare Allocation Item** (`parent IN [allocation names]`, `parenttype='IMM Spare Allocation'`, order `parent, idx`) group-by-parent. Tổng enrich = **6 query cố định** (3 hiện có + 3 CR-44) bất kể N item / phối nguồn. Dangling FK → map trả None → `_str_or_blank` → '' → summary lấy phần còn lại.

- **§BE task (application code — [BE] Bước-4, KHÔNG thuộc slice contract BA):** (1) `_inbox_item(..., summary: str = "")` — khóa thứ 11, default ''; (2) mở rộng `_enrich_inbox_items` +3 batch query + 4 helper `_summarize_transfer/_summarize_allocation/_summarize_commissioning/_summarize_repair` + hằng tuple `_COMMISSIONING_APPROVAL_STAGES` (SSoT enum) + `_fmt_qty`/`_truncate_120` util; (3) carry aux per-source; (4) hard-cap 120 + coalesce cuối; (5) transfer builder thêm fetch `from_department, from_location, to_department, to_location` (hiện chỉ fetch `reason/transfer_type/…`); (6) `test_imm00_approvals_inbox._ITEM_KEYS` 10→11 (+`summary`) + TC nội dung (§Test plan CR-44). **Live-HTTP cần gunicorn `--preload` reload (HARD-STOP user).**

### Mobile OAS mirror deltas — CR-44 (field `summary`) — **slice BA đóng ở Bước-2** (contract-first, shape-only)

- `PendingApprovalItem.properties` **+= `summary`** (type `string`, description VI: mẫu per-source + ≤120 + coalesce '' + non-crash) · `PendingApprovalItem.required` **+= `summary`** (11 khóa) · `additionalProperties:false` GIỮ.
- Header comment mirror + Item description: "10-key"→"11-key (CR-44 +summary)"; phân biệt `summary` (nội dung phiếu) vs `title` (1 mảnh nhãn ngắn).
- **Guard `test_mobile_oas.py` (shape-only, BA sửa):** hằng `_PENDING_APPROVAL_ITEM_PROPS` += `'summary'` → TC-c assert **11 prop** (all-string, non-nullable, in-required — summary tự động phủ vì loop assert mọi prop). **KHÔNG thêm TC method** ⇒ `_EXPECTED_TEST_COUNT`/`_GUARD_SUITE_*`/`_MOBILE_OAS_TOTAL` **GIỮ NGUYÊN** (chỉ đổi assertion nội TC hiện có). `test_oas_baseline` (path-count) KHÔNG đổi (0 path/whitelist mới). **KHÔNG có test cross-check live-keys ↔ OAS** ⇒ contract-first hợp lệ: shape-guard XANH ngay vòng này, live-true khi BE land `summary` vào `_inbox_item` (đối xứng CR-42).

### Test plan BE CR-44 (bổ sung `test_imm00_approvals_inbox.py` — [BE] Bước-4)

TC nội dung `summary` (sau khi BE land live): (S1) MỖI item có key `summary` type str, `_ITEM_KEYS` 11-key; (S2) transfer: `summary == '<dept nguồn> → <dept đích> · <asset_name>'` (dùng department_name, fallback location_name khi dept rỗng); (S3) allocation multi-line: `'<part_name> ×<qty> <uom> …+N'`, N đúng số dòng còn lại; allocation 1 dòng → KHÔNG có ' …+N'; (S4) commissioning: `'Nghiệm thu ban đầu · bậc <i>/4'` đúng index theo approval_stage; stage rỗng → `'Nghiệm thu ban đầu'`; (S5) repair: `'<failure> · <asset_name>'`, failure quá dài → cắt giữ hậu tố asset_name; (S6) **≤120**: mọi summary `len ≤ 120` (dựng phiếu có dept/part/failure siêu dài → assert ≤120 + kết `'…'`); (S7) **missing-data non-crash**: dept/item/stage null hoặc FK dangling (asset xoá) → summary là str (coalesce '' / partial), KHÔNG raise; (S8) **no-N+1**: dựng ≥2 item MỖI nguồn (transfer+allocation+commissioning+repair) → assert query-count enrich **bị chặn** (≤ hằng, không tăng theo N — dùng `frappe.db.sql`-count hoặc `count_queries` harness); (S9) **session-scoped bất biến**: `inspect.signature(api.get_pending_approvals_inbox)` KHÔNG có param `user` (chỉ `**_ignore`). Targeted run: `bench --site miyano run-tests` module `test_imm00_approvals_inbox` + `test_mobile_oas`. **IMM-10 baseline đỏ pre-existing (STATE Blocker#4) KHÔNG đụng.**

### Business rules

- **BR-00-INBOX-01** — Inbox CHỈ gộp phiếu user có thẩm quyền duyệt theo cap-SSoT của action duyệt tương ứng (bảng trên); thiếu cap → exclude im lặng; 0 cap → empty-success. KHÔNG bao giờ hiện phiếu user không duyệt được (anti dead-link).
- **BR-00-INBOX-02** — Bất biến count==rows: `total == len(items) == sum(by_module.values())` (LL-BE-49; không phát count DB riêng lệch drill). `by_module` = **4 khóa** cố định `{imm04, imm00, imm15, imm09}` sau CR-42.
- **BR-00-INBOX-03 (CR-42, SoD — đối xứng BR-09-SOD/CR-41)** — Nguồn `imm09` (CM 'Pending Inspection') **loại self-closed**: WO mà chính `session.user` là người đóng phiếu (`_resolve_wo_closer(name) == session.user`) KHÔNG hiện trong inbox của họ (tránh dòng "duyệt mù" → click hứng SoD `FORBIDDEN` ở `confirm_inspection`). Closer không xác định (None, legacy — không có event `repair_pending_inspection`) → **fail-open**, vẫn hiện (đối xứng INV-CM-SOD-2). Áp SoD ở tầng list-filter, KHÔNG thay đổi guard `confirm_inspection` (2 tầng phòng thủ độc lập: list ẩn + handler chặn).
- **BR-00-INBOX-04 (CR-44, field `summary` — chống "duyệt mù")** — MỖI item PHẢI có `summary`: string tiếng Việt do SERVER dựng, **LUÔN emit** (coalesce `''` — KHÔNG null), **≤120 ký tự** (hard-cap server + `'…'`), mô tả **cái đang được duyệt** theo nguồn (bảng §"Field `summary` — CR-44"). Thiếu dữ liệu / dangling FK → phần lấy được hoặc `''` (**non-crash, KHÔNG raise**). Denorm batch trong `_enrich_inbox_items` (+3 query cố định, **no-N+1**). `summary` là **advisory** (không thay hành động Duyệt ở detail view — GATE-8) và **không đổi số dòng** (invariant count==rows GIỮ).
- **BR-00-INBOX-05 (CR-43, hợp đồng TRUNG THỰC khi cắt)** — `data` PHẢI công bố `truncated` (int 0/1) + `totals_uncapped` (dict 4 khóa int) + `excluded_modules` (list[str] ⊆ `{imm00,imm15,imm09}`). **ZERO-COST:** `totals_uncapped[m]` mặc định = `by_module[m]` (KHÔNG query), CHỈ COUNT thật khi `len(fetched) >= _INBOX_LIMIT_PER_SOURCE`; ca 0-chạm-trần KHÔNG phát COUNT nào (test spy). `truncated = int(any(totals_uncapped[m] > by_module[m]))`. `excluded_modules` = nguồn cap-based thiếu cap (imm04 identity-based KHÔNG bao giờ có). `totals_uncapped['imm09']` khi chạm trần = **cận-trên PRE-SoD**. **Bất biến count==rows (BR-00-INBOX-02) áp cho `total`/`by_module` — `totals_uncapped` là measure UNCAPPED riêng, ĐƯỢC PHÉP > `len(items)`.** Flag = int (KHÔNG bool/None — parity CR-01). Additive-OPTIONAL trong OAS (`required` GIỮ `[items,total,by_module]`).
- KPI dashboard `pending_commissioning` GIỮ SSoT `count_pending_approvals` (imm04-mine) — inbox = superset by-design (ADR-…-C; BE cập nhật comment @`services/imm00.py:2996-2998`).

### Mobile OAS mirror deltas — CR-42 (nguồn thứ 4 imm09) — **slice BA đóng ở Bước-2** (enum/by_module là SHAPE, curate-first; live-true khi BE land nguồn-d)

> Đây là **contract-first**: BA mở rộng enum/`by_module` trong OAS mirror + shape-guard `test_mobile_oas` NGAY vòng này (đóng slice contract). Header comment mirror ghi "CURATE VERBATIM @backend LIVE" ⇒ **BE PHẢI land block nguồn-d** (§BE task) để response THẬT khớp 4-nguồn; **KHÔNG có test cross-check live-`by_module` ↔ OAS-schema** (guard chỉ assert YAML-shape + signature `**_ignore`) ⇒ shape-guard XANH ngay, không phụ thuộc BE. `test_oas_baseline` (path-count) **KHÔNG đổi** — 0 whitelist/0 path mới (chỉ mở rộng schema đã có).

- `PendingApprovalItem.doctype.enum` **+= `'Asset Repair'`** (3→4 giá trị) · `PendingApprovalItem.module.enum` **+= `imm09`** (3→4).
- `PendingApprovalsInboxData.by_module.properties` **+= `imm09`** (integer, mô tả `imm09 = Chờ nghiệm thu CM`) · `by_module.required` **+= `imm09`** (đủ 4 khóa) · `additionalProperties:false` GIỮ.
- Cập nhật description 3 schema (Item/Data) + path summary: "3 nguồn" → "4 nguồn"; item 10-key GIỮ (0 field mới, chỉ mở enum). 0 schema mới, 0 path mới, 0 tag mới (`approvals` GIỮ 16th).
- **Guard `test_mobile_oas.py` (shape-only, BA sửa):** hằng `_PENDING_APPROVAL_DOCTYPE_ENUM` += `'Asset Repair'`, `_PENDING_APPROVAL_MODULE_ENUM` += `imm09`; TC-f `by_module` set/required/loop 3→4 khóa. **KHÔNG thêm TC method** ⇒ `_EXPECTED_TEST_COUNT`/`_GUARD_SUITE_*`/`_MOBILE_OAS_TOTAL` **GIỮ NGUYÊN** (chỉ đổi assertion nội TC hiện có).

### Mobile OAS mirror deltas — CR-43 (hợp đồng TRUNG THỰC khi cắt) — **slice BA ĐÓNG ở Bước-2** (đã verify `Ran 893 OK`)

> **Contract-first ADDITIVE + guard XANH THẬT (đã chạy).** BA mở rộng `PendingApprovalsInboxData` + shape-guard NGAY vòng này. **0 path/tag/schema mới, 0 whitelist mới** ⇒ `test_oas_baseline`/counter-sync **KHÔNG đổi**; **0 TC-method mới** ⇒ `_EXPECTED_TEST_COUNT`/`_GUARD_SUITE_*`/`_MOBILE_OAS_TOTAL` **GIỮ NGUYÊN**. Response THẬT khớp 6-khóa khi **BE land §BE task** (§CR-43); guard chỉ assert YAML-shape + signature `**_ignore` (KHÔNG cross-check live-keys) ⇒ XANH độc lập BE.

- `PendingApprovalsInboxData.properties` **+= 3 field ADDITIVE-OPTIONAL** (`additionalProperties:false` GIỮ; `required` GIỮ `[items,total,by_module]` byte-identical — backward-compat codegen pin required-set cũ):
  - `truncated` — `integer` `enum:[0,1]` (cờ int 0/1, KHÔNG bool/None — CR-01).
  - `totals_uncapped` — inline object **CLOSED** (đối xứng `by_module`) 4 khóa `{imm00,imm04,imm15,imm09}: integer`, `required` cả 4; mô tả nêu rõ **zero-cost** (= by_module khi không chạm trần) + **imm09 = cận-trên PRE-SoD**.
  - `excluded_modules` — `array<string enum:[imm00,imm15,imm09]>` (imm04 identity-based KHÔNG bao giờ có).
- **Guard `test_mobile_oas.py` (shape-only, BA sửa — đã chạy XANH):** `test_mob_oas_inbox_f` cập nhật `set(dprops.keys())` 3→6 khóa; giữ `required` assertion `[by_module,items,total]` (additive); thêm assertion `truncated` int-enum[0,1] · `totals_uncapped` closed 4-khóa-int · `excluded_modules` array-string-enum. **KHÔNG thêm TC method.**

### Mobile OAS mirror deltas — CR-32 (BE Bước-4 — curate VERBATIM theo response THẬT sau khi `.py` xanh)

- **+1 path** `GET assetcore.api.imm00.get_pending_approvals_inbox` · `operationId: getPendingApprovalsInbox` · **tag `approvals` MỚI (16th)** — inbox xuyên-module, không nhét vào tag 1 domain (precedent mở-tag CR-34 `training` 15th) · 0 parameters (session-scoped; `**_ignore` không surface param nào).
- **3 schema CLOSED** (`additionalProperties: false`) — ⚠️ **SELF-CORRECTION vs đề-mục "2 schema Item/Envelope"**: mirror precedent CR-34 3-tầng Envelope→Data→Item (wire = `handle()`→`_ok` bọc `{success,data}`):
  1. `PendingApprovalItem` — 10 prop string, ALL required, non-nullable (`''` coalesce); `module` enum `[imm04, imm00, imm15]`; `doctype` enum 3 giá trị.
  2. `PendingApprovalsInboxData` — `{items: array<$ref Item>, total: integer, by_module: <inline closed object {imm04,imm00,imm15}: integer, required cả 3>}`, required cả 3 khóa (`by_module` inline — KHÔNG schema riêng).
  3. `PendingApprovalsInboxEnvelope` — `{success: enum[true], data: $ref Data}`, required cả 2.
- `responses`: `'200'` = INLINE `oneOf [PendingApprovalsInboxEnvelope, Error]` Decision-B route-by-VALUE (nhánh Error defensive/uniform — mirror `getNotificationPreferences` CR-30; endpoint 0 lỗi nghiệp vụ) · `'401': $ref Unauthorized401` · `'403': $ref Forbidden` **SINGLE-SHAPE dispatcher-only** (service 0 raise FORBIDDEN — silent-exclude).
- **Membership**: ∈ `_MVP_BUSINESS_PATHS` (401/403 symmetry **79→80**) · ∈ `_MVP_READ_ENVELOPE` (+1; `_MVP_LIST_ENVELOPE` GIỮ 13 — precedent CR-34: `data` có khóa ngoài `items[]`).
- **Counter sync** (⚠️ baselines grounded 2026-07-16 sau CR-34: path/opId **90**, c5/parity **79**, `_EXPECTED_TEST_COUNT` **818**, `_GUARD_SUITE_SUM` **961**, `_MOBILE_OAS_TOTAL` **987**, distinct-tag **15** — **BE grep-verify @source TRƯỚC bump, đa-phiên race**): path/opId 90→91 · c5/parity 79→80 · closed-schema **+= 3** (re-derive @source) · `_EXPECTED` += `get_pending_approvals_inbox → getPendingApprovalsInbox` · distinct-tag 15→16 (`approvals`) · guard class MỚI `TestMobilePendingApprovalsInboxContract` (~10 TC: path/opId/tag + 0-param + 3-schema-closed + item-10-prop-SET== + module/doctype-enum + by_module-3-khóa-required + 200-oneOf-[Env,Error]-0-discriminator + 403-slot-single-Forbidden + ∈read-∉list + symmetry + naming-guard-0-dangling + **runtime spec-parity dotted-path resolve + `is_whitelisted` bare-GET**) · `_EXPECTED_TEST_COUNT`/`_GUARD_SUITE_EXPECTED[test_mobile_oas.py]` += N-TC-THẬT · `_GUARD_SUITE_SUM`/`_MOBILE_OAS_TOTAL` += N.
- ADR-MOBILE-0XX (YAML curate record) do **BE** author Bước-4 (numbering-race — lấy số ADR mobile kế tiếp lúc land).

### Test plan BE (file MỚI `assetcore/tests/imm00/test_imm00_approvals_inbox.py`)

TC tối thiểu CR-32: (1) envelope + `data` 3 khóa + item ĐÚNG 10 khóa; (2) **spoof**: gọi handler kèm `user=<người khác>` → kwargs bị nuốt, kết quả == không kèm (session-scoped); (3) imm04: user là `pending_approver` thấy phiếu / user khác KHÔNG; (4) imm00: có `commissioning.submit` thấy transfer Pending Approval, thiếu → 0 item `module=='imm00'`; (5) imm15: có `inventory.submit` thấy allocation Requested, thiếu → 0 item `module=='imm15'`; (6) 0-cap user → `success:true` + `items:[]` + by_module all-0; (7) sort `pending_since asc` + tie-break `name asc`; (8) BR-00-INBOX-02 invariant; (9) `route` đúng map 3 nguồn (kể cả imm15 fallback `/inventory` khi thiếu ref); (10) guest → `PermissionError`/dispatcher-403.

**TC mới CR-42 (nguồn imm09 — [BE] Bước-4):** (11) user có `repair.submit`: WO 'Pending Inspection' docstatus 0 đóng-bởi-NGƯỜI-KHÁC → hiện 1 item `module=='imm09'` shape 10-key đúng (`doctype='Asset Repair'`, `route='/cm/work-orders/{name}'`, `asset==asset_ref`, `title=failure_description`); (12) **SoD**: WO chính `session.user` tự đóng (event `repair_pending_inspection` actor==user) → **KHÔNG** hiện (BR-00-INBOX-03); (13) **fail-open**: WO thiếu event closer (None) → **VẪN** hiện; (14) **cap-less**: user thiếu `repair.submit` → 0 item `module=='imm09'`, `success:true`, KHÔNG lỗi; (15) `by_module` giờ đủ 4 khóa + invariant `total==len(items)==sum(by_module.values())` GIỮ khi có/không item imm09; (16) no-N+1: WO Pending Inspection ≤50, closer-resolution batch (đo query-count không tăng theo N item). Targeted run: `bench --site miyano run-tests` module `test_imm00_approvals_inbox` + `test_mobile_oas` + `test_imm09` (nếu chạm helper). **IMM-10 baseline đỏ pre-existing (STATE Blocker#4) KHÔNG đụng.**

**TC mới CR-43 (hợp đồng TRUNG THỰC khi cắt — [BE] Bước-4):** (17) **AC1 shape**: `data` có đủ 6 khóa; `truncated`/`totals_uncapped`(4 khóa)/`excluded_modules` LUÔN emit; 3 khóa cũ `items`/`total`/`by_module` GIỮ NGUYÊN shape+giá trị (item 11 khóa, `total==len(items)==sum(by_module.values())`); `excluded_modules ⊆ {imm00,imm15,imm09}`. (18) **AC2 zero-cost**: khi 0 nguồn chạm trần → `truncated==0` ∧ `totals_uncapped[m]==by_module[m]` ∀m ∧ **count-fn KHÔNG được gọi** (monkeypatch/spy `frappe.db.count` hoặc `_count_uncapped` = 0 lời gọi). (19) **AC3 chạm trần**: hạ `_INBOX_LIMIT_PER_SOURCE=1`, seed 2 Asset Transfer `Pending Approval` → `truncated==1` ∧ `by_module['imm00']==1` ∧ `totals_uncapped['imm00']==2`. (20) **excluded**: user thiếu `commissioning.submit`/`inventory.submit`/`repair.submit` → module tương ứng ∈ `excluded_modules` (imm04 KHÔNG bao giờ có mặt kể cả khi user không phải pending_approver). (21) **AC6 int-parity**: `truncated` + mọi `totals_uncapped[m]` là **int** (`isinstance(v,int) and not isinstance(v,bool)`); `total*` ≥ 0. Targeted run: `bench --site miyano run-tests` module `test_imm00_approvals_inbox` + `test_mobile_oas`. **IMM-10 baseline đỏ pre-existing (STATE Blocker#4) KHÔNG đụng.**

### Boundaries (Always / Never)

- **Always:** cap qua hằng SSoT (`_TRANSFER_APPROVE_CAP`/`_CAP_APPROVE`/**`_imm09._CAP_SUBMIT`** lazy-import) · session-scoped `**_ignore` · bulk-enrich no-N+1 (tái dùng `_enrich_inbox_items` + batch closer + **CR-44 +3 batch: AC Department · AC Location · IMM Spare Allocation Item**) · sort server-side · `route` non-empty · `by_module` đủ **4 khóa** · count==rows · **SoD imm09 tái dùng `_resolve_wo_closer` (SSoT CR-41), fail-open khi closer None** · **(CR-44) `summary` server-built ≤120 coalesce '' non-crash, `stage_total` derive từ enum tuple** · **(CR-43) `truncated`/`totals_uncapped`(4 khóa)/`excluded_modules` LUÔN emit; `totals_uncapped[m]` mặc định = `by_module[m]` (zero-cost), COUNT thật CHỈ khi `len(fetched) >= _INBOX_LIMIT_PER_SOURCE`; flag = int 0/1; `imm04` KHÔNG bao giờ ∈ `excluded_modules`**.
- **Never:** honor param `user` · hardcode role-name/chuỗi cap (kể cả `'repair.submit'` trần — dùng `_CAP_SUBMIT`) · raise FORBIDDEN khi thiếu cap nguồn (exclude im lặng) · **fail-CLOSED khi closer None** (phải fail-open) · per-item query enrich/closer trong vòng lặp · nút duyệt inline (GATE-8) · đổi cap route/sidebar `/approvals/pending` · migrate/commit/reload worker (HARD-STOP user) · đụng IMM-10 baseline · **(CR-44) `summary` null/raise khi thiếu data · per-item query denorm cho summary · persist summary thành field DocType · hardcode `stage_total`=4 · thêm param/đổi signature** · **(CR-43) phát COUNT khi nguồn KHÔNG chạm trần (phá zero-cost) · flag kiểu bool/None (int 0/1 bắt buộc) · thêm 3 field CR-43 vào `required` OAS (additive-optional) · buộc `totals_uncapped` khớp count==rows (được phép > len)**.

---

# Phần IV — Endpoint → Business Rule Mapping

| Endpoint | Business Rule áp dụng |
|---|---|
| `create_device_model`, `update_device_model` | BR-00-01, VR-00-03 |
| `transition_status`, `update_asset` | BR-00-02, BR-00-04, BR-00-10 |
| `list_audit_trail`, `get_audit_entry`, `verify_chain` | BR-00-03 |
| `create_asset` (validate), Work Order APIs | BR-00-05 (`validate_asset_for_operations`) |
| `create_supplier`, `update_supplier` | BR-00-06 |
| SLA Policy controller (validate) | BR-00-07 |
| `close_capa_record` | BR-00-08 |
| Scheduler `trigger_capa_overdue_check` | BR-00-09 |
| `create_incident`, `update_incident`, `submit_incident` | VR-00-04, AC-E008, AC-E009 |
| Inventory submit/cancel | BR-INV-01 → BR-INV-08 |
| `get_pending_approvals_inbox` (CR-32/CR-42/CR-44/CR-43, §III.22) | BR-00-INBOX-01, BR-00-INBOX-02, BR-00-INBOX-03 (SoD imm09), BR-00-INBOX-04 (summary CR-44), BR-00-INBOX-05 (truthful truncation CR-43) |
| `list_assignable_users` (AC-CR-80, §III.23) | BR-00-ASSIGN-01 … BR-00-ASSIGN-05 (capability-SSoT + truthful truncation + 400 in-envelope) |

---

## III.23. Picker "người nhận việc" — AC-CR-80 `list_assignable_users` (capability-SSoT + hết cắt IM LẶNG)

> **Vòng 4 (BA / AC-CR-80) — ĐÓNG mobile `CR-75`.** Endpoint **ĐÃ LIVE** ở BE từ 2026-07-22 (`api/user.py:1057`) nhưng **vắng mirror** ⇒ mobile không biết mà dùng, và **vẫn cắt im lặng** ở `limit`.
> Quyết định kiến trúc: [`ADR-IMM00-TRUNCATION-SSOT.md` §7](./ADR-IMM00-TRUNCATION-SSOT.md) — **ADR-IMM00-ASSIGN-01..04** + **INV-ASSIGN-1..8**.
> **Slice contract (OAS mirror + guard shape `test_mobile_oas` 8 TC `cr80_a..h`) ĐÓNG ở Bước-2 (BA).** Slice **application code** (`api/user.py` bồi truncation · `frontend/src/api/user.ts` + `ApproverSelect.vue` render dải) = **[BE]/[FE] Bước-4**.
> **0 DocType change ⇒ 0 migrate.** Sửa `api/*.py` ⇒ live-HTTP cần **USER reload gunicorn** (`--preload`, HARD-STOP) — chấm bằng `run-tests`, KHÔNG curl.

### §III.23.1 Vấn đề nghiệp vụ (vì sao có endpoint riêng thay vì nới `listUsers`)

Field "người nhận việc" xuất hiện ở **6 ngữ cảnh**: KTV sửa chữa (IMM-09), KTV bảo trì định kỳ (IMM-08), KTV hiệu chuẩn (IMM-11), người xử lý sự cố (IMM-12), KTV lắp đặt/nghiệm thu (IMM-04), và các field **chỉ mô tả người** (giám sát, thủ kho, trưởng khoa, người duyệt, leo thang SLA).

Trước AC-CR-80, mobile chỉ có `listUsers(role=…)` **đơn trị** ⇒ buộc chọn giữa:

- **lọc sai**: `role='PM User'` giấu mất `PM Manager`, `Corrective User`, `Vendor Engineer` — màn hình **khẳng định** "không tìm thấy kỹ thuật viên" trong khi chính bộ lọc của app giấu họ;
- **không lọc**: liệt kê cả điều dưỡng/kế toán/quản trị → chọn nhầm → BE từ chối `IMM09-INVALID-TECHNICIAN` (422) **ngay tại giường bệnh**; với hiệu chuẩn (thiết bị loại B/C/D bắt buộc hiệu chuẩn theo NĐ98) còn kéo theo hồ sơ sai chủ thể.

**Nguyên nhân gốc**: role-name **không phải** nguồn sự thật về quyền (anti-pattern *RBAC dead-gate* — đổi tên vai/thêm vai ⇒ gate fail âm thầm). Nguồn sự thật là **capability/DocPerm** — đúng thứ validator dùng.

### §III.23.2 Endpoint

- **`GET /api/method/assetcore.api.user.list_assignable_users`** — `@frappe.whitelist()` (bare, nhận GET), any-authenticated.
- **Mirror mobile**: `operationId: listAssignableUsers`, tag `user` (`docs/mobile/openapi/assetcore-mobile.openapi.yaml`).
- **Actor**: mọi user AssetCore đang mở form có field chọn người (tổ trưởng KTV, điều phối viên, QA duyệt…).
- **Audit trail**: KHÔNG (read-only, không sinh Lifecycle Event).

| Param | Kiểu | Bắt buộc | Default | Ghi chú |
|---|---|---|---|---|
| `context` | string enum | ✅ | — | `user` \| `repair` \| `pm` \| `calibration` \| `incident` \| `commissioning`. Tập enum = `{_ANY_USER_CONTEXT}` ∪ keys(`_ASSIGNABLE_CONTEXTS`) (`api/user.py:1036` + `api/user.py:1038`). |
| `search` | string | ❌ | `''` | LIKE `%q%` trên `full_name` **hoặc** `email` (OR-filter, server-side). |
| `limit` | integer | ❌ | `20` | **Clamp** `max(1, min(int(limit), 100))`. |

**Ngữ nghĩa `context`** (SSoT bảng ánh xạ ở `api/user.py:1038`):

| `context` | Kiểm gì | Dùng cho field nào |
|---|---|---|
| `user` | **Không lọc năng lực** — chỉ cần là user AssetCore | Field **mô tả người**: giám sát, thủ kho, trưởng khoa, người nhận, người duyệt, leo thang SLA |
| `repair` | `has_permission("Asset Repair", "write", user=u)` | `assign_technician.technician` (IMM-09) |
| `pm` | `has_permission("PM Work Order", "write", user=u)` | `assign_pm_technician.technician` (IMM-08) |
| `calibration` | `has_permission("IMM Asset Calibration", "write", user=u)` | `create_calibration.technician` (IMM-11) |
| `incident` | `has_permission("Incident Report", "write", user=u)` | người xử lý sự cố (IMM-12) |
| `commissioning` | `has_permission("Asset Commissioning", "write", user=u)` | KTV lắp đặt / nghiệm thu (IMM-04) |

> **Anti-probe**: endpoint chỉ nhận **tên ngữ cảnh**, KHÔNG nhận `doctype`/`ptype` thô từ client — nếu không, bất kỳ ai cũng dò được ma trận quyền của toàn hệ thống.

### §III.23.3 Response — hình dạng ĐÍCH (AC-CR-80)

```jsonc
// 200 OK
{
  "success": true,
  "data": {
    "items": [
      { "name": "ktv.nguyen@benhvien.vn", "full_name": "Nguyễn Văn Kỹ",
        "email": "ktv.nguyen@benhvien.vn", "user_image": null }
    ],
    "total": 47,      // tổng người ĐƯỢC PHÉP (đếm SAU lọc năng lực), TRƯỚC khi cắt
    "truncated": 1,   // integer 0|1 — KHÔNG boolean
    "limit": 20       // trần ĐÃ CLAMP (không phải số client gửi)
  }
}
```

**ĐỔI HỢP ĐỒNG (breaking, có chủ đích)**: `data` từ **mảng trần** `[…]` → **object** `{items,total,truncated,limit}`.
Lý do chấp nhận breaking: mirror **chưa từng** khai op này (0 client mobile); web-FE là **caller duy nhất** và được sửa CÙNG VÒNG; giữ mảng trần thì không có chỗ nào để nói "còn 27 người nữa" mà không bịa thêm header/khoá song song. Chi tiết + phương án đã loại: ADR-IMM00-ASSIGN-03.

**Lỗi** — `context` ngoài enum:

```jsonc
// HTTP-200 (KHÔNG status-line!) 
{ "success": false, "error": "Ngữ cảnh phân công không hợp lệ: bogus_ctx",
  "code": "VALIDATION_ERROR", "http_status": 400 }
```

- Đây là **lỗi lập trình phía client** (sai `context`), **KHÔNG** phải phiên hết hạn ⇒ FE/mobile hiển thị thông báo, **KHÔNG LOGOUT**. Phân biệt với **dispatcher-401/403 status-line** (guest / hết token) — đó mới là ca re-auth (2 loại 403, xem `ADR-IMM00-LIST-SCOPE §9`).
- Thông điệp **tiếng Việt**, được echo lại giá trị client gửi; **TUYỆT ĐỐI KHÔNG** đưa **giá trị** của `_ASSIGNABLE_CONTEXTS` (tên DocType `Asset Repair`/`PM Work Order`…) hay tên cột/SQL vào message — đó là bề mặt phân quyền.

### §III.23.4 Business rules & invariants

| ID | Luật | Ghi chú |
|---|---|---|
| **BR-00-ASSIGN-01** | Nguồn người = **user AssetCore** (base role `AssetCore System User`, `enabled=1`, `user_type='System User'`, đã duyệt) — KHÔNG phải toàn bộ Frappe User của site dùng chung | `get_ac_users(..., approved_only=True)` |
| **BR-00-ASSIGN-02** | Lọc năng lực bằng **capability/DocPerm**, KHÔNG so tên role | mirror `services/imm09.py:1657 _is_repair_capable` |
| **BR-00-ASSIGN-03** | **Display ⟺ enforcement parity**: tập hiển thị == tập validator chấp nhận (0 dead-pick) | INV-ASSIGN-5/6 |
| **BR-00-ASSIGN-04** | Danh sách bị cắt PHẢI công bố `total`/`truncated`/`limit` qua SSoT `truncation_meta` | INV-ASSIGN-1..4, 7 |
| **BR-00-ASSIGN-05** | `context` lạ ⇒ 400 **in-envelope** trên HTTP-200, VI, 0 leak DocType/SQL | INV-ASSIGN-8 |

Invariants đầy đủ (INV-ASSIGN-1..8): [`ADR-IMM00-TRUNCATION-SSOT.md` §7.3](./ADR-IMM00-TRUNCATION-SSOT.md).

### §III.23.5 Boundaries (Always / Never)

**Always** — mọi field chọn người đi qua endpoint này (web `<ApproverSelect context="…">`, mobile `listAssignableUsers`) · ngữ cảnh mới = **1 khoá** `_ASSIGNABLE_CONTEXTS` **+** enum OAS **cùng vòng** · FE render dải "Đang hiển thị N/M người — gõ tên để tìm thêm" khi `truncated===1`.

**Never** — KHÔNG `SmartSelect doctype="User"` / `frappe.get_all("User")` thô ở FE · KHÔNG nhận doctype thô từ client · KHÔNG lọc theo role-name ở bất kỳ tầng nào · KHÔNG trả `roles`/`imm_roles`/bí mật trong item · KHÔNG nâng `limit` thay cho `search` (trần cứng 100).

### §III.23.6 Delta OAS mirror (đã LANDED ở Bước-2)

| Hạng mục | Trước | Sau |
|---|---|---|
| `paths` | 107 | **108** (`/api/method/assetcore.api.user.list_assignable_users`) |
| `operationId` | 107 unique | **108** unique (`listAssignableUsers`) |
| `components.schemas` | 281 | **283** (`AssignableUserItem`, `AssignableUserListEnvelope`) |
| `components.parameters` | 38 | **38 GIỮ** (3 param khai INLINE) |
| Guard `test_mobile_oas` | 967 | **975** (+8 `cr80_a..h`) |

> Chấm theo **DELTA**, KHÔNG theo số tuyệt đối — baseline luôn có thể đã trôi do phiên khác (STATE blocker #12).

### §III.23.7 Bàn giao (Bước-4)

**[BE]** `assetcore/api/user.py::list_assignable_users` — xem code-shape ở [`04_Backend_Design.md` §V.6](./04_Backend_Design.md).
⚠️ **Cite refresh bắt buộc**: OAS cite `api/user.py:1036 / :1037 / :1047`. Nếu BE thêm import top-level (vd `truncation_meta`) thì **mọi dòng dịch xuống** ⇒ guard `cr80_e` ĐỎ **đúng thiết kế** — BE cập cite theo dòng THẬT trong CÙNG vòng (mẫu AC-CR-79). Muốn tránh, dùng **lazy import trong thân hàm**.
⚠️ **Test BE PHẢI sửa theo shape mới**: `assetcore/tests/imm00/test_imm00_base_role.py::TestListAssignableUsers._names` (`:301`) hiện đọc `res["data"]` như **mảng** ⇒ đổi thành `res["data"]["items"]`; TC-01..07 giữ nguyên ngữ nghĩa. *(Module này KHÔNG có trong danh sách acceptance ban đầu — bổ sung bắt buộc, nếu bỏ sót thì suite ĐỎ.)*

**[FE]** `frontend/src/api/user.ts` + `frontend/src/components/commissioning/ApproverSelect.vue` — xem [`06_Frontend_Design.md` §VIII.3](./06_Frontend_Design.md). `props`/`v-model` của `ApproverSelect` **KHÔNG đổi** ⇒ 51 file đang dùng không phải sửa.

**Test**: [`07_Testing_QA.md` §XVII](./07_Testing_QA.md) — TC-00-ASSIGN-01..12 + FE render test.

---

## III.24. «Bản ghi liên quan» — AC-CR-87 `get_connections` (cây dữ liệu thật: preview + nhãn VI + đường tạo mới)

> **Vòng 1/5 (BA / AC-CR-87).** Endpoint **ĐÃ LIVE** (`api/connections.py::get_connections`) nhưng chỉ trả **badge đếm** ⇒ khối UI trả lời sai câu hỏi nó gợi ra (xem [`02 §IV.39`](./02_Analysis_Design.md)).
> Quyết định kiến trúc + invariants: [`ADR-IMM00-CONNECTIONS-TREE.md`](./ADR-IMM00-CONNECTIONS-TREE.md) (**D1–D10 · INV-CONN-1..14**). Code shape: [`04 §V.7`](./04_Backend_Design.md).
> **KHÔNG có mirror OAS mobile** (verify 2026-07-27: 0 hit `connections` trong `docs/mobile/openapi/assetcore-mobile.openapi.yaml`) ⇒ **không** phát sinh nghĩa vụ curate OAS ở vòng này. Nếu sau này mirror: `capped: bool` **phải** đã gỡ (CR-01 cấm bool cho cờ cắt).
> **0 DocType ⇒ 0 migrate.** Sửa `api/*.py` ⇒ cần USER reload gunicorn (`--preload`) — chấm bằng `run-tests`, KHÔNG curl.

### §III.24.1 Endpoint

- **`GET /api/method/assetcore.api.connections.get_connections`** — `@frappe.whitelist()`, any-authenticated (dispatcher-403 cho guest/no-token; lỗi nghiệp vụ luôn **in-envelope HTTP-200**).
- **Actor**: mọi vai mở màn chi tiết (KTV, tổ trưởng xưởng, trưởng phòng VT-TTBYT, QA, trưởng khoa).
- **Audit trail**: KHÔNG (read-only, không sinh Lifecycle Event).

| Param | Kiểu | Bắt buộc | Default | Ghi chú |
|---|---|---|---|---|
| `doctype` | string | ✅ | — | DocType bản ghi cha. Phải ∈ `_ALLOWED_SOURCE_DOCTYPES` (**12** hub derive từ `*_dashboard.py`) để dựng cây; ngoài allowlist mà **tồn tại** ⇒ `groups: []` (xem §III.24.4) |
| `name` | string | ✅ | — | Mã bản ghi cha |
| `preview_limit` | integer | ❌ | `5` | **Clamp** `max(1, min(int(v), 10))`; parse lỗi ⇒ về `5` (KHÔNG raise — panel phụ trợ không được làm vỡ màn chi tiết). Trần **đã clamp** là số truyền vào `truncation_meta` (INV-TRUNC-LIMIT) |

### §III.24.2 Response — hình dạng ĐÍCH

> ⚠️ **CẬP NHẬT AC-CR-92 (2026-07-28) — ô còn ĐÚNG 9 khoá.** 4 khoá LEGACY `label` (của ô) · `count` · `capped` · `filters` **ĐÃ GỠ**; `capped: bool` thay bằng **`total_capped: int 0|1`**. Hợp đồng đầy đủ + luật đọc + cửa sổ deploy: **§III.24.10** (cuối phần III.24). Khối JSON dưới đây là **hình dạng hiện hành**.

```jsonc
// 200 OK — GET …get_connections?doctype=AC%20Asset&name=AC-ASSET-2026-00001
{
  "success": true,
  "data": {
    "doctype": "AC Asset",
    "name": "AC-ASSET-2026-00001",
    "total": 9,                      // cấp payload = TỔNG CỘNG DỒN `item.total` mọi ô (KHÔNG cùng nghĩa item.total)
    "groups": [
      {
        "label": "Bảo trì & Sửa chữa",         // nhãn NHÓM — đã là tiếng Việt (khai bằng _("…") trong *_dashboard.py)
        "label_vi": "Bảo trì & Sửa chữa",      // mirror để FE có MỘT accessor cho cả nhóm lẫn ô
        "items": [
          {
            "doctype": "PM Work Order",
            "label_vi": "Phiếu bảo trì định kỳ",   // SSoT LABEL_VI ở BE — nhãn DUY NHẤT của ô
            "total": 6,                            // int, số bản ghi user thấy, CHẶN TRẦN 100
            "truncated": 1,                        // int 0|1, KHÔNG bool. 1 ⟺ total > preview_limit  → `items` bị cắt
            "total_capped": 0,                     // int 0|1, KHÔNG bool. 1 ⟺ total là CẬN DƯỚI (≥100) → render "100+"
            "items": [                             // preview THẬT, đúng min(total, preview_limit) dòng
              { "name": "PM-WO-2026-00042", "title": "Bảo trì định kỳ 6 tháng",
                "status": "In Progress", "status_label": "Đang thực hiện", "date": "2026-08-01" },
              { "name": "PM-WO-2026-00031", "title": "Bảo trì định kỳ 6 tháng",
                "status": "Completed", "status_label": "Hoàn thành", "date": "2026-02-01" }
              // … tối đa preview_limit dòng
            ],
            "deep_link_filters": { "asset_ref": "AC-ASSET-2026-00001" },  // mọi value là STRING
            "can_create": true,
            "create_route_hint": "/pm/work-orders/new"                    // "" khi can_create=false
          }
        ]
      }
    ]
  }
}
```

**Bộ khoá theo tầng (hợp đồng đóng — client được phép so sánh TẬP):**

| Tầng | Khoá | Số |
|---|---|---|
| `data` | `doctype` · `name` · `groups` · `total` | 4 |
| `groups[]` | `label` · `label_vi` · `items` | 3 |
| `groups[].items[]` (**ô**) | `doctype` · `label_vi` · `total` · `truncated` · `total_capped` · `items` · `deep_link_filters` · `can_create` · `create_route_hint` | **9** |
| `groups[].items[].items[]` (**dòng preview**) | `name` · `title` · `status` · `status_label` · `date` | 5 |

**Phần tử `items[]`** — 5 khoá, **toàn bộ kiểu `str`, KHÔNG BAO GIỜ `null`**:

| Khoá | Nguồn | Khi thiếu dữ liệu |
|---|---|---|
| `name` | PK | luôn có |
| `title` | `PREVIEW_FIELDS[dt].title` → `Meta.title_field` → `name` | **không bao giờ rỗng** |
| `status` | `PREVIEW_FIELDS[dt].status` — giá trị enum **THÔ** (client so sánh/lọc dùng khoá này) | `""` (doctype không có trường trạng thái) |
| `status_label` | nhãn VI (SSoT BE) | `""` khi `status == ""`; `"Chưa rõ"` khi có giá trị chưa có bản dịch (KHÔNG rò tiếng Anh — LL-FE-53) |
| `date` | `PREVIEW_FIELDS[dt].date` → `modified`, chuẩn hoá `YYYY-MM-DD` | `""` chỉ khi cả hai đều rỗng (thực tế `modified` luôn có) |

**Bảng SSoT chốt sẵn**: `LABEL_VI` (41 doctype) · `PREVIEW_FIELDS` (41) · `CREATE_CONTEXT` (8) — [`ADR-IMM00-CONNECTIONS-TREE.md` §3](./ADR-IMM00-CONNECTIONS-TREE.md).

### §III.24.3 Bất biến hợp đồng (client được phép dựa vào)

| Bất biến | Phát biểu |
|---|---|
| ĐẾM ⟺ DÒNG | `len(items) == min(total, preview_limit)` trên MỌI ô |
| CẮT TRUNG THỰC | `truncated == 1 ⟺ total > preview_limit`; `total_capped == 1 ⇒ total` là **cận dưới** ⇒ UI render `"100+"` (AC-CR-92: khoá cũ `capped` đã gỡ) |
| HAI CỜ TRỰC GIAO | `total_capped == 1 ⇒ truncated == 1`; ca `truncated == 0 ∧ total_capped == 1` **không tồn tại** |
| KIỂU | `type(truncated) is int` ∧ `type(total_capped) is int` ∧ cả hai `∈ {0,1}` ∧ **không** phải `bool`; mọi value `deep_link_filters` là `str` |
| TỔNG CẤP PAYLOAD | `data.total == Σ item.total` trên mọi ô của mọi nhóm |
| ĐƯỜNG ĐI | `total > 0 ⇒ deep_link_filters != {}` |
| NÚT SỐNG | `can_create == false ⟺ create_route_hint == ""` (hai chiều) |
| PHÂN QUYỀN | mọi số/dòng đều chạy dưới `frappe.session.user` ⇒ `count` **bằng** số dòng thấy khi drill (ADR-IMM00-LIST-SCOPE §4b) |

### §III.24.4 Ma trận lỗi (tất cả **in-envelope HTTP-200**)

| Ca | `success` | `code` | Ghi chú |
|---|---|---|---|
| `doctype`/`name` rỗng | `false` | `VALIDATION_ERROR` | GIỮ hành vi cũ |
| `doctype` **không tồn tại** | `false` | `NOT_FOUND` | GIỮ code cũ; message **thống nhất**, KHÔNG echo giá trị người gọi truyền vào |
| `doctype` tồn tại nhưng **∉ allowlist** | **`true`** | — | `groups: []`, `total: 0`. GIỮ hợp đồng cũ (`test_doctype_without_dashboard_returns_empty_groups`); allowlist ở đây **giới hạn đường thực thi**, không đóng oracle — xem đính chính A6 tại [ADR §D6](./ADR-IMM00-CONNECTIONS-TREE.md) |
| Bản ghi **không tồn tại** | `false` | `NOT_FOUND` | **CÙNG message** với ca doctype rác |
| Không có quyền đọc bản ghi cha | `false` | `FORBIDDEN` | GIỮ (test hiện có đòi đúng `FORBIDDEN`) |
| Doctype đích ngoài quyền đọc | — | — | **Ẩn hẳn ô** (không trả nhóm rỗng gây tò mò) — GIỮ hành vi cũ |
| `preview_limit` rác/ngoài biên | `true` | — | clamp về `[1,10]`, KHÔNG lỗi |

> ⚠️ **Đính chính acceptance A6 (BA Self-Correction, QA đọc trước khi chấm):** A6 đòi *"doctype ngoài allowlist và doctype rác trả **cùng một** mã lỗi"*, nhưng A9 đòi 11 test hiện có xanh **không sửa assert** — trong đó `test_doctype_without_dashboard_returns_empty_groups` đòi `AC Asset Category` (ngoài allowlist) trả **success**. Hai điều kiện **loại trừ nhau**. Quyết định: **A9 thắng** (hợp đồng đang chạy), phần A6 giữ được = **thống nhất message** giữa ca doctype-rác và ca bản-ghi-rác. Lý lẽ đầy đủ + rủi ro tồn dư: [ADR §D6](./ADR-IMM00-CONNECTIONS-TREE.md).

### §III.24.5 Tương thích & lịch gỡ

- **ADDITIVE**: 7 khoá mới, 5 khoá legacy giữ **nguyên nghĩa** ⇒ `RelatedRecords.vue` hiện tại chạy **không sửa** (A9/A11).
- **Vòng 2 (FE — AC-CR-88)**: đọc `label_vi` + `items` + `truncated` + `deep_link_filters`; bỏ `{...item.filters}` trong `open()` (URL rác với nhóm `internal_links`). Hợp đồng đọc: §III.24.6 · spec thực thi: [`06 §VIII.4.2`](./06_Frontend_Design.md) · quyết định: [ADR §10](./ADR-IMM00-CONNECTIONS-TREE.md).
- ~~**Vòng 3 (BE+FE cùng lúc)**: gỡ `capped` + `count` + `label`. **Không** gỡ sớm hơn.~~ → **ĐÃ THỰC HIỆN ở AC-CR-92** (hoãn qua vòng 3/4/5 vì deep-link chết là bug sống, xem [ADR §13.6](./ADR-IMM00-CONNECTIONS-TREE.md)), và gỡ **thêm** `filters`; `capped` thay bằng `total_capped: int 0|1`. Hợp đồng mới: **§III.24.10**. ⇒ **Thang tolerant-reader §III.24.6 RETIRED** (ADR §17.7 mục 3) — client hiện hành đọc thẳng khoá mới, chỉ còn **một** dòng phòng thủ cho `total_capped`.

### §III.24.6 Hợp đồng phía client (tolerant reader — chốt ở vòng 2, AC-CR-88) — **RETIRED bởi AC-CR-92**

> ⛔ **RETIRED 2026-07-28 (ADR §17.7 mục 3 — supersede D-FE-3).** Bảng thang fallback dưới đây **giữ lại làm lịch sử**, KHÔNG còn là hợp đồng: 4 khoá legacy đã bị gỡ nên các bậc `total → count`, `label_vi → label`, `deep_link_filters → filters` **không còn đường tới**. Hợp đồng đọc hiện hành + **một** dòng phòng thủ duy nhất (`total_capped` vắng ⇒ coi như `0`): **§III.24.10.3**. Client mới KHÔNG được cài lại các bậc fallback này (giữ chúng = giữ vĩnh viễn hai tên cho một con số).

Endpoint chạy dưới gunicorn `--preload`: giữa lúc BE land và lúc USER reload worker, client **vẫn** nhận shape cũ (5 khoá legacy). Client vì thế phải đọc theo **thang fallback** dưới đây — đây là phần hợp đồng, không phải tuỳ chọn FE:

| Đại lượng | Thang đọc | Khi thiếu hoàn toàn |
|---|---|---|
| Nhãn ô / nhãn nhóm | `label_vi` → `label` → `doctype` | không bao giờ rỗng |
| Dòng preview | `items[]` | `undefined` ⇒ **chế độ legacy**: chỉ nhãn + số, **KHÔNG** bịa dòng, **KHÔNG** dải cắt |
| Tổng của ô | `total` → `count` → `0` | — |
| Cờ cắt | `truncated === 1` → suy ra `shown > 0 ∧ total > shown` | — |
| Chạm trần | `capped === true` ⇒ hiển thị `"{total}+"` (`100+`), **cấm** `total − shown` | `false` |
| Query "xem tất cả" | `deep_link_filters` **dùng nguyên, kể cả `{}`** → (chỉ khi `undefined`) chiếu `filters` giữ **value scalar** | 0 khoá ⇒ **không** dựng link |
| Nút tạo | `can_create === true ∧ create_route_hint !== ''` ∧ route **phân giải được** | ⇒ không render nút |

**Ba luật cứng cho mọi client (web/mobile) tiêu thụ endpoint này:**
1. `deep_link_filters === {}` là **câu trả lời**, không phải thiếu dữ liệu ⇒ **KHÔNG** fallback sang `filters`, **KHÔNG** dẫn người dùng tới danh sách chung (đúng bug người dùng báo 2026-07-27).
2. `status` là **mã kỹ thuật** — chỉ để so sánh/lọc; hiển thị **luôn** dùng `status_label` (LL-FE-53).
3. `capped === true ⇒ total` là **cận dưới** ⇒ mọi phép trừ trên `total` đều là số bịa.

---

### §III.24.7 Vòng 4/5 (AC-CR-90) — `can_create` là GƯƠNG của enforcement + khoá mới `create_prefill`

> Quyết định + invariants: [ADR §12](./ADR-IMM00-CONNECTIONS-TREE.md) (D-CR4-1..10 · INV-CONN4-1..10 · **supersede D8 điều kiện 3+4**) · nghiệp vụ: [`02 §IV.39`](./02_Analysis_Design.md) BR-00-CONN-25..34 · code shape: [`04 §V.8`](./04_Backend_Design.md) · FE: [`06 §VIII.4.6`](./06_Frontend_Design.md).
> **ADDITIVE**: +1 khoá mỗi ô (12 → **13**). 12 khoá cũ **giữ nguyên nghĩa**. Client cũ bỏ qua `create_prefill` vẫn chạy y nguyên (nút tạo dẫn tới màn trống — hành vi vòng 3).
> **KHÔNG có mirror OAS mobile** (verify 2026-07-28: 0 hit `connections` trong `docs/mobile/openapi/assetcore-mobile.openapi.yaml`) ⇒ **0** nghĩa vụ curate OAS; `_EXPECTED_TEST_COUNT` / `_GUARD_SUITE_SUM` **delta 0** (ADR D-CR4-10).

#### §III.24.7.a Khoá thứ 13 — `create_prefill` — **[ĐÃ LAND ⇒ hợp đồng SỐNG, đọc §III.24.11]**

> ✅ **AC-CR-105 (2026-07-30, [ADR §18](./ADR-IMM00-CONNECTIONS-TREE.md) D-CR105-1).** Phần BE của khoá này **ĐÃ LAND**: ô có **ĐÚNG 10 khoá** (9 của AC-CR-92 + `create_prefill`), token `CREATE_CAPABILITY` vào đường thực thi của vị-từ P3. Cảnh báo `[CHƯA CÀI — BE]` của §17 D-CR92-7 **hết hiệu lực** — giữ nguyên văn bên dưới để truy vết (P-DOC-3), nhưng **số khoá đúng là 10, không phải 13**: khoá thứ 13 của §12 được đánh số khi ô còn 12 khoá, sau AC-CR-92 (12 → 9) nó là khoá **thứ 10**.
> ⚠️ **Đọc §III.24.11 TRƯỚC khi viết test**: hình thức bất biến ở mục này (`⟺` chuỗi ba vế) **đã được đính chính** ở ADR §18 D-CR105-2 — dịch nguyên chuỗi `⟺` thành assert sẽ mâu thuẫn với 3 doctype hợp lệ `can_create == true ∧ create_prefill == {}`.

```jsonc
{
  "doctype": "Asset Repair",
  "label_vi": "Phiếu sửa chữa",
  // … 10 khoá cũ …
  "can_create": true,
  "create_route_hint": "/cm/create",
  "create_prefill": { "asset": "AC-ASSET-2026-00042" }   // MỚI — {query_key: giá trị}
}
```

| Khoá | Kiểu | Nghĩa |
|---|---|---|
| `create_prefill` | `dict[str,str]` — **luôn có mặt** | Ngữ cảnh cha để màn tạo điền sẵn. Vòng này luôn **0 hoặc 1** cặp: khoá = query key mà **chính màn tạo đó đọc**, giá trị = **mã bản ghi cha**. `{}` khi không tạo được **hoặc** khi màn tạo không đọc khoá query nào |

**Bất biến (mở rộng "NÚT SỐNG" của §III.24.3 — INV-CONN4-1) — HÌNH THỨC ĐÃ ĐÍNH CHÍNH, ADR §18 D-CR105-2:**

```
(1)  can_create == false   ⟺   create_route_hint == ""          # biconditional THẬT
(2)  can_create == false   ⇒   create_prefill == {}             # ⇔ prefill ≠ {} ⇒ can_create ∧ hint ≠ ""
(3)  can_create == true  ∧  create_prefill == {}   là HỢP LỆ    # 3 lớp ca ở §III.24.11.3
```

trên **toàn bộ** doctype allowlist. Không tồn tại trạng thái "có route mà không có quyền", cũng không tồn tại "có prefill mà nút tắt" (prefill mồ côi = dữ liệu rò ra client không dùng được).
⛔ **KHÔNG** viết chuỗi `⟺` ba vế (`can_create == false ⟺ hint == "" ⟺ prefill == {}`) như bản 2026-07-28: nó bắt buộc `prefill == {} ⇒ can_create == false`, mâu thuẫn với mệnh đề (3) ngay bên dưới — hai TC dịch từ hai câu đó **không thể cùng xanh**, và bên nào đỏ cũng sẽ bị "sửa cho xanh" bằng cách bịa khoá prefill hoặc tắt nút.
⚠️ Chiều ngược **không** đúng theo nghĩa mạnh: `can_create == true` **có thể** đi cùng `create_prefill == {}` — đúng 3 doctype có màn tạo **không đọc khoá query nào** (`Asset Transfer` · `AC Purchase` · `Service Contract`), cộng ca cặp (đích, cha) không có khoá. Nút vẫn sống, chỉ là không điền sẵn.

#### §III.24.7.b `can_create` — 4 vị-từ, mỗi vị-từ một SSoT

```
can_create ⟺ P1 có màn tạo thật (CREATE_CONTEXT)
           ∧ P2 nhóm là liên kết NGƯỢC và Link field khớp ngữ cảnh cha (nhóm internal_links luôn false)
           ∧ P3 capability  — rbac.can(CREATE_CAPABILITY[dt])   (§c)
           ∧ P4 vòng đời    — vị-từ PER-DOCTYPE                  (§d)
```

#### §III.24.7.c P3 — capability là **TOKEN dùng chung 3 tầng** (verify @source 2026-07-28)

| DocType đích | Token | Gate tầng API | `requiredCapabilities` route tạo | `rbac.CAPABILITY_MAP[token]` |
|---|---|---|---|---|
| `PM Work Order` | `pm.create` | `api/imm08.py::create_pm_work_order` | `/pm/work-orders/new` | `("PM Work Order","create")` |
| `Asset Repair` | `repair.create` | `api/imm09.py::create_repair_work_order` | `/cm/create` | `("Asset Repair","create")` |
| `IMM Asset Calibration` | `calibration.create` | `api/imm11.py::create_calibration` ⚠️ **không** phải `create_calibration_schedule` (cùng token, khác hàm) | `/calibration/new` | `("IMM Asset Calibration","create")` |
| `Incident Report` | `corrective.create` | `api/imm12.py` (`_CAP_REPORT`) | `/incidents/new` | `("Incident Report","create")` |
| `AC Purchase` | `purchase.create` | `api/purchase.py::create_purchase` | `/purchases/new` | `("AC Purchase","create")` |

- Doctype **không khai token** (`Asset Document` · `Asset Transfer` · `Service Contract`) ⇒ giữ nguyên `frappe.has_permission(dt,"create")` như vòng 1. Lý do từng ca + backlog: [ADR §12 D-CR4-2 / §12.9](./ADR-IMM00-CONNECTIONS-TREE.md).
- **Cấm** khai token mà `CAPABILITY_MAP[token] != (dt, "create")` — guard INV-CONN4-2 đỏ ngay.

#### §III.24.7.d P4 — vòng đời là vị-từ **PER-DOCTYPE**, chỉ áp khi cha là `AC Asset`

| Ô | Vị-từ advertise (dùng lại của enforcement) | `Active` | `Out of Service` | `Decommissioned` |
|---|---|---|---|---|
| Phiếu bảo trì (PM) | `status ∉ AssetStatus.BLOCKED_FOR_WO` | ✅ | ❌ | ❌ |
| Phiếu sửa chữa | `imm00.is_valid_asset_transition(status, "Under Repair")` | ✅ | **✅** | ❌ |
| Phiếu hiệu chuẩn | `status ∉ AssetStatus.BLOCKED_FOR_WO` | ✅ | ❌ | ❌ |
| Sự cố | `status != "Decommissioned"` | ✅ | **✅** | ❌ |
| 4 doctype còn lại | *(không khai ⇒ không có cổng vòng đời)* | ✅ | ✅ | ✅ |

> Hai ô in đậm là **thay đổi hành vi có chủ đích** so với vòng 1–3 (trước đây bị chặn-tất bởi `BLOCKED_FOR_WO`): thiết bị đang `Out of Service` **phải** tạo được phiếu sửa chữa và báo được sự cố — đó chính là lúc cần hai thứ đó nhất. QA **không** chấm là regression.
> Ô «Sự cố» ở `Decommissioned` chỉ đúng **sau khi** land EC-12-05 ở `services/imm12.py::report_incident` (ADR D-CR4-8 / [`docs/imm-12/02` BR-12-29](../imm-12/02_Analysis_Design.md)). Land hai thứ **cùng vòng**, nếu không oracle §III.24.7.e sẽ đỏ đúng chỗ nó phải đỏ.

#### §III.24.7.e Oracle **advertise ⇔ enforce** (hợp đồng chấm DoD)

`can_create` của ô **bằng** kết quả "gọi THẬT service tạo tương ứng không báo lỗi", với **mọi tiền đề khác giữ hợp lệ**: người gọi có đủ 4 capability · thiết bị vừa tạo, **không** có phiếu sửa chữa đang mở · payload hợp lệ · `is_recalibration = 0`.
**Residual đã ratify:** `create_work_order` còn chặn khi thiết bị đã có phiếu sửa chữa **mở** — ô liên quan **không** phản chiếu (xung đột nhất thời, và mirror nó tốn +1 truy vấn/ô ⇒ phá ZERO-COST). Nút sống, màn tạo trả lỗi nghiệp vụ **có địa chỉ** — ngõ cụt **có biển báo**, xem [ADR §12 D-CR4-6](./ADR-IMM00-CONNECTIONS-TREE.md).

#### §III.24.7.f Hợp đồng phía client cho `create_prefill` (bổ sung §III.24.6)

| Đại lượng | Thang đọc | Khi thiếu |
|---|---|---|
| Prefill nút tạo | `create_prefill` **dùng nguyên, kể cả `{}`** | `undefined` (BE chưa reload) ⇒ coi như `{}` ⇒ điều hướng **chỉ path** (hành vi vòng 3, không bịa khoá) |

**Ba luật cứng bổ sung:**
1. FE điều hướng bằng `router.push({ path, query })` với `query = create_prefill` — **không** ghép chuỗi query bằng tay, **không** đẩy chỉ `path` khi prefill non-empty.
2. `create_prefill === {}` là **câu trả lời** ("không có gì để điền sẵn"), không phải thiếu dữ liệu ⇒ **KHÔNG** fallback sang `deep_link_filters` (khoá của nó là **Link fieldname** dùng lọc *danh sách*, không phải khoá query của *màn tạo* — đính chính D8, ADR §12.7).
3. Luật `resolve-or-hide` giữ nguyên: route không phân giải được ⇒ **ẩn nút**, kể cả khi `can_create === true`.

---
### §III.24.8 AC-CR-94 — hợp đồng **DRILL** của ô: endpoint nào, khoá nào, và bất biến `count == drill`

> Quyết định: [ADR §15](./ADR-IMM00-CONNECTIONS-TREE.md) (D-CR94-1..9 · **INV-CONN-18..22**) · nghiệp vụ: [`02 §IV.39`](./02_Analysis_Design.md) BR-00-CONN-42..49 · FE: [`06 §VIII.9`](./06_Frontend_Design.md) · test: [`07 §XVIII.9`](./07_Testing_QA.md).
> **PAYLOAD `get_connections`: 0 thay đổi** (không khoá mới, không đổi nghĩa, không bớt) — vòng này chỉ **thêm bất biến** và **đóng 1 lỗ ở endpoint drill của lịch hiệu chuẩn**.

**Ô ⇒ endpoint drill (2 ô mới có nút ở vòng này):**

| Ô (`doctype`) | `deep_link_filters` BE phát | Khoá màn đích đọc | Endpoint drill THẬT | Tầng đọc kết quả |
|---|---|---|---|---|
| `PM Schedule` | `{asset_ref: <mã cha>}` | `?asset=` (`/pm/schedules`) | `assetcore.api.imm00.list_pm_schedules(asset=…)` — **không** phải `api.imm08.list_pm_schedules(asset_ref=…)` (2 bề mặt khác nhau, §15.1 #9) | `data.items[]` + `data.total` |
| `IMM Calibration Schedule` | `{asset: <mã cha>}` | `?asset=` (`/calibration/schedules`) | `assetcore.api.imm11.list_calibration_schedules(filters='{"asset":"…"}')` — kênh **`filters` JSON**, **KHÔNG** thêm tham số `asset=` | `data.data[]` + `data.pagination` |

**Bất biến (client + QA được phép dựa vào):**

- **INV-CONN-18 / INV-CONN-19** — dưới **cùng** `frappe.session.user`: `total` của ô == số dòng endpoint drill trả về khi truyền đúng khoá ở bảng trên, **và mọi dòng thuộc đúng bản ghi cha**. Hai vế, không được bỏ vế thứ hai (hai con số bằng nhau vẫn có thể cùng sai).
- **INV-CONN-20** — bộ lọc theo thiết bị **GIAO (AND)** với bộ lọc đang có; `?asset=X&overdue=1` ⊆ cả `?asset=X` và `?overdue=1`.
- **Ô lịch KHÔNG lọc trạng thái** (BR-00-CONN-44): ô đếm **mọi** lịch của thiết bị ⇒ drill **cấm** tự thêm `status`/`pm_type`/`is_active`. Lịch `Paused`/`Suspended`/`is_active=0` **thuộc** cả hai tập.
- **INV-CONN-22** — ô rỗng **vẫn có mặt** trong payload: `total == 0` ∧ `truncated == 0` (int) ∧ `label_vi` khác rỗng và khác tên DocType. Client **không** được suy "ô vắng mặt = ô rỗng".
- **INV-CONN-21 (ENFORCE từ 2026-07-30 — `AC-CR-106`)**: `apply_vendor_scope` **GIAO** (AND) giá trị caller với tập thiết bị được giao thay vì **GÁN** (dòng vi phạm cũ `services/shared/scope.py:174`) ⇒ với **Vendor Engineer**, deep-link 1 thiết bị trả **đúng** thiết bị đó; caller ngoài phạm vi trả **0 dòng** (KHÔNG phải "mọi thiết bị của tôi"). Shape ra luôn `["in", <list>]`, giao rỗng ⇒ `["in", ["__none__"]]`. Đại số đầy đủ 8 shape + boundaries + nơi đặt test: [`ADR-IMM00-LIST-SCOPE §10.4`](./ADR-IMM00-LIST-SCOPE.md) (`ADR-IMM00-LIST-SCOPE-04`). Áp cho **cả 5** call site: `api/imm00.py:413` · `api/imm08.py:39` · `api/imm09.py:36` · `api/imm11.py:30` · `api/imm11.py:83`.

**Sửa lỗi kèm theo (BE, 1 nhánh — `services/imm11.py::_extract_asset_in_scope`):** helper chỉ nhận shape IN-list nên bộ lọc `asset` **vô hướng** bị `pop` rồi **không** tiêm lại ⇒ `list_calibration_schedules(filters='{"asset":"X"}')` trước vòng này trả **toàn bộ** lịch của mọi thiết bị (ảnh hưởng **mọi** caller, không riêng deep-link). Hợp đồng sau khi sửa + ràng buộc chi tiết: [`../imm-11/05 §0.1.6`](../imm-11/05_API_Specification.md).

### §III.24.9 AC-CR-95 — hợp đồng **DRILL** của 4 ô còn lại có hạ tầng sẵn (0 thay đổi BE)

> Quyết định: [ADR §16](./ADR-IMM00-CONNECTIONS-TREE.md) (D-CR95-1..10 · **INV-CONN-23..28**) · nghiệp vụ: [`02 §IV.39`](./02_Analysis_Design.md) BR-00-CONN-50..58 · FE: [`06 §VIII.10`](./06_Frontend_Design.md) · test: [`07 §XVIII.10`](./07_Testing_QA.md).
> **BE: 0 thay đổi** — payload `get_connections` không đổi **và** 4 endpoint drill **đã** nhận đủ khoá từ trước. Vòng này chỉ **thêm bất biến** + **1 file test guard mới**.

**Ô ⇒ endpoint drill (4 ô mới có nút ở vòng này):**

| Ô (`doctype`) | `deep_link_filters` BE phát | Khoá URL màn đích đọc | Endpoint drill THẬT | Khoá gửi BE | Cột DB | Tầng đọc kết quả |
|---|---|---|---|---|---|---|
| `Firmware Change Request` | `{asset_ref: <mã cha>}` | `?asset=` (`/cm/firmware`) | `assetcore.api.imm00.list_firmware_crs(asset=…)` `:2898` | tham số `asset` | `asset_ref` (BE map `:2902`) | `data.items[]` + `data.total` |
| `Asset Commissioning` | `{final_asset: <mã cha>}` | `?asset=` (`/commissioning`) | `assetcore.api.imm04.list_commissioning(filters='{"final_asset":"…"}')` `:24` | `filters.final_asset` | `final_asset` | `data.items[]` + `data.pagination` |
| `Asset Decommission` | `{asset: <mã cha>}` | `?asset=` (`/decommissions`) | `assetcore.api.imm14.list_decommissions(filters='{"asset":"…"}')` `:85` | `filters.asset` | `asset` | `data.data[]` + `data.pagination` |
| `IMM CAPA Record` | `{asset: <mã cha>}` | `?asset=` (`/capas`) | `assetcore.api.imm00.list_capas(asset=…)` `:1870` | tham số `asset` | `asset` | `data.items[]` + `data.pagination` |

**Khoá URL luôn là `asset` trên MỌI màn** (D-CR95-2). Việc dịch `asset → final_asset` là nghĩa vụ của **view** `/commissioning`; việc dịch `asset → asset_ref` là nghĩa vụ của **BE** `list_firmware_crs`. Client **không** được gửi `?final_asset=` lên URL — `LIST_TARGET_ANCHOR` chỉ neo một khoá URL cho "thiết bị".

**Bất biến (client + QA được phép dựa vào):**

- **INV-CONN-23 / 24 / 25** — dưới **cùng** session: `total` của ô == số dòng endpoint drill khi truyền đúng khoá ở bảng trên **và mọi dòng thuộc đúng thiết bị**. Hai vế, không bỏ vế thứ hai.
- **INV-CONN-26 — ngoại lệ có công thức (`Asset Commissioning`)**: `list_commissioning` **tự tiêm** `docstatus != 2` khi caller không truyền `docstatus` (`services/imm04.py:1060`) ⇒ quan hệ đúng là
  `cell.total == len(drill.items) + #{docstatus == 2}`.
  Trên dữ liệu sinh bởi workflow IMM-04, chênh = **0** (không state nào map `doc_status = 2`). Client **không** được "sửa" bằng cách gửi shape toán tử `docstatus: ['in',[0,1,2]]`.
- **4 ô này KHÔNG lọc trạng thái** (BR-00-CONN-54): ô đếm **mọi** bản ghi của thiết bị ⇒ drill **cấm** tự thêm `workflow_state` / `status` / `disposal_method` / `not_closed` / `overdue`. Phiếu `Non Conformance`, CAPA `Closed`, FCR `Rolled Back`, biên bản `Cancelled` **thuộc** cả hai tập.
- **INV-CONN-27 (ENFORCE từ 2026-07-30 — `AC-CR-98`)**: `list_commissioning` **đếm và đọc bằng MỘT engine** `frappe.get_list` (trước đây `frappe.db.count` `services/imm04.py:1076` + `frappe.get_all` `:1079` — cả hai **bỏ qua** `permission_query_conditions` `hooks.py:444` ⇒ trả toàn bảng cho persona bị row-scope = **rò dữ liệu**, không chỉ lệch số). Sau vòng này bất biến được chấm cho **3 persona** (`AssetCore Super Admin` · `Commissioning User` · `Vendor Engineer` + `Commissioning User` — ma trận [`ADR-IMM00-LIST-SCOPE §10.2`](./ADR-IMM00-LIST-SCOPE.md)), **KHÔNG** còn chỉ `Administrator`. Dung sai duy nhất được phép và **phải khai tường minh trong assert**: `cell.total == len(drill.items) + #{docstatus == 2}` (INV-CONN-26) ∧ `cell.total_capped == 0`. Hợp đồng + acceptance: [`ADR-IMM00-LIST-SCOPE §10.5/§10.8`](./ADR-IMM00-LIST-SCOPE.md) (`ADR-IMM00-LIST-SCOPE-05`). ⚠️ `Vendor Engineer` **thuần** (không kèm `Commissioning User`) **không có DocPerm read** trên `Asset Commissioning` ⇒ nhận **HTTP-200 + Error envelope** `FORBIDDEN`, KHÔNG phải danh sách rỗng — test dùng vendor thuần sẽ chấm nhầm nhánh.
- **INV-CONN-28** — 4 khoá **ngoại lai** vẫn được `_safe_deep_link` cho đi qua (`{name:…}` từ hub `Asset Repair`/`Asset Document`/`IMM Asset Calibration`, `{vendor:…}` từ `AC Supplier`, `{master_item:…}` từ `IMM Device Model`, `{linked_incident:…}` từ `Incident Report`). Nghĩa vụ **chặn** thuộc FE `listTarget` (trả `null`), **không** phải siết allowlist BE — siết ở BE sẽ mất luôn ô/preview thay vì chỉ mất nút.

---

### §III.24.10 AC-CR-92 — **BREAKING**: ô **12 → 9 khoá**, `capped: bool` → `total_capped: int 0|1`

> Quyết định: [ADR §17](./ADR-IMM00-CONNECTIONS-TREE.md) (D-CR92-1..9 · **INV-CONN-29..34 · INV-CONNFE9-1..6**) · nghiệp vụ: [`02 §IV.39`](./02_Analysis_Design.md) BR-00-CONN-59..66 · code shape BE: [`04 §V.9`](./04_Backend_Design.md) · FE: [`06 §VIII.12`](./06_Frontend_Design.md) · test: [`07 §XVIII.11`](./07_Testing_QA.md).
> **Loại thay đổi: BREAKING** — vòng đầu tiên của họ Connections **không** additive ⇒ BE + FE đổi **cùng vòng**.
> **KHÔNG có mirror OAS mobile** (verify 2026-07-28: **0 hit** `connections` trong `docs/mobile/openapi/assetcore-mobile.openapi.yaml`) ⇒ **0** nghĩa vụ curate OAS, **0** client ngoài repo bị vỡ; 3 counter guard **delta 0** (`_EXPECTED_TEST_COUNT` 1024 · `_GUARD_SUITE_SUM` 1167 · `_MOBILE_OAS_TOTAL` 1193).

#### §III.24.10.1 Bảng khoá ô — **12 → 9** (delta tường minh)

| Khoá | Trạng thái | Ghi chú |
|---|---|---|
| `doctype` | GIỮ | — |
| `label_vi` | GIỮ | nhãn **duy nhất** của ô sau vòng này |
| `total` | GIỮ | nghĩa không đổi: số bản ghi user thấy, **chặn trần** `CAP = 100` |
| `truncated` | GIỮ | `int` 0\|1 — `items` bị cắt so với `preview_limit` |
| **`total_capped`** | **MỚI** | `int` 0\|1 — **`total` là CẬN DƯỚI** (thay `capped: bool`) |
| `items` | GIỮ | 5 khoá/dòng, `[]` khi ô rỗng (**ô vẫn có mặt** — INV-CONN-22) |
| `deep_link_filters` | GIỮ | **nguồn duy nhất** để dựng deep-link sau khi `filters` bị gỡ |
| `can_create` | GIỮ | — |
| `create_route_hint` | GIỮ | — |
| ~~`label`~~ (của **ô**) | **GỠ** | là `frappe._(doctype)` = tên DocType **tiếng Anh thô** ⇒ render nó là vi phạm LL-FE-53. Nhãn nhóm `label` **GIỮ** (khác chủ thể) |
| ~~`count`~~ | **GỠ** | **cùng con số** với `total`, khác tên ⇒ 3 TC phải canh cho chúng khỏi nói khác nhau |
| ~~`capped`~~ | **GỠ** | `bool` (CR-01 cấm bool cho cờ cắt) **và** tên không nói nó nói về `total` ⇒ thay bằng `total_capped` |
| ~~`filters`~~ | **GỠ** | dạng Frappe (`["in", [...]]` không serialize được); giữ lại chỉ tạo đường **hồi sinh** khoá mà `_safe_deep_link` vừa strip (bug vòng 5, D-CR5-3) |
| `create_prefill` | ~~**CHƯA CÀI**~~ → **ĐÃ LAND** (AC-CR-105, 2026-07-30) | Khoá **thứ 10**: ô nay có **10 khoá**. Hợp đồng sống ở **§III.24.11**; ADR §18 D-CR105-1 |

#### §III.24.10.2 `truncated` vs `total_capped` — hai cờ, hai chủ thể, cùng kiểu `int`

| Cờ | Nói về | Ngưỡng | Client render |
|---|---|---|---|
| `truncated` | danh sách `items` | `preview_limit` (clamp `[1,10]`, mặc định 5) | dải «Đang xem 5/…» |
| `total_capped` | con số `total` | `CONNECTION_COUNT_CAP = 100` | badge «100+» |

| `truncated` | `total_capped` | Ca | Badge | Dải |
|---|---|---|---|---|
| 0 | 0 | ≤ `preview_limit` bản ghi | `7` | *(không)* |
| 1 | 0 | > `preview_limit`, < 100 | `7` | «Đang xem 5/7» |
| 1 | 1 | ≥ 100 | `100+` | «Đang xem 5/100+» |
| 0 | 1 | **KHÔNG THỂ TỒN TẠI** (invariant) | — | — |

- **Predicate BE**: `total_capped = 1 if len(rows) > CAP else 0` — `>` **không** `>=` (dùng `>=` biến "đúng 100" thành "100+" = bịa thêm dữ liệu).
- **Kiểu**: `int` THUẦN. Oracle phải là `type(v) is int` ∧ `not isinstance(v, bool)` (`bool ⊂ int` nên `assertIsInstance(v, int)` **không** bắt được).

#### §III.24.10.3 Ba luật cứng cho mọi client (thay §III.24.6)

1. **Đọc thẳng khoá mới, KHÔNG cài lại bậc fallback**: `total` (không `?? count`), `label_vi` (không `?? label`), `deep_link_filters` (không `?? filters`). Fallback đã bị gỡ có chủ đích — cài lại là hồi sinh đúng lớp bug vòng 5.
2. **Phòng thủ đúng MỘT khoá**: `total_capped` vắng mặt (worker chưa reload) ⇒ coi như `0` ⇒ badge in số trần (`"7"`, **không** `"7+"`). Cài bằng so sánh tường minh `item.total_capped === 1`; **không** rải optional-chaining khắp file.
3. **`total_capped === 1 ⇒ `total` là cận dưới** ⇒ badge phải là `"{total}+"` và **mọi** phép trừ trên `total` (kiểu *"còn 95 chưa hiển thị"*) là **số bịa** — dải cắt luôn dùng khuôn `Đang xem {shown}/{badge}`.

#### §III.24.10.4 Cửa sổ deploy — **thứ tự là ràng buộc** (gunicorn `--preload`)

- **BE reload TRƯỚC, FE build SAU.** Vòng này **không** `npm run build` ⇒ bundle đang chạy vẫn là bản tolerant-reader ⇒ người dùng không bao giờ gặp "client mới đọc BE cũ".
- **Suy giảm đã KHAI TRƯỚC (QA không chấm là regression)**: trong cửa sổ chưa-reload, client **mới** đọc `total` = `undefined` ⇒ mọi ô bị coi là rỗng ⇒ tab nói «Chưa có bản ghi nào liên quan…». Tạm thời · read-only · **tự lành** sau `bench restart`. Đây là giá **có tên** để một con số chỉ còn **một** cái tên.
- **DoD chấm bằng `run-tests` module-isolated** (`timeout` tool ≥ 600000ms), **KHÔNG curl** (LL-DEPLOY-07/08 — HTTP đang trả shape của worker cũ).

---

### §III.24.11 AC-CR-105 — ô **9 → 10 khoá**: `create_prefill` LIVE + capability là TOKEN (hợp đồng SỐNG)

> Quyết định: [ADR §18](./ADR-IMM00-CONNECTIONS-TREE.md) (D-CR105-1..9 · INV-CONN105-1..4 · INV-CONN4-1/2/3/7/10) · nghiệp vụ: [`02 §IV.42`](./02_Analysis_Design.md) FR-00-CONN-06 / BR-00-CONN-67..76 · code shape BE: [`04 §V.10`](./04_Backend_Design.md) · FE: [`06 §VIII.14`](./06_Frontend_Design.md) · test + DoD: [`07 §XXI`](./07_Testing_QA.md).
> **Loại thay đổi: ADDITIVE** (+1 khoá; 9 khoá cũ **0 đổi nghĩa**). Client cũ bỏ qua khoá mới vẫn chạy y nguyên.
> **0 endpoint mới · 0 tham số mới · 0 mirror OAS** (`grep -c connections docs/mobile/openapi/*.yaml` = **0**) ⇒ 3 counter guard **delta 0**.

#### §III.24.11.1 Bảng khoá ô — **9 → 10**

| Khoá | Kiểu | Trạng thái | Nghĩa |
|---|---|---|---|
| `doctype` · `label_vi` · `total` · `truncated` · `total_capped` · `items` · `deep_link_filters` · `can_create` · `create_route_hint` | (§III.24.10.1) | **GIỮ — 0 đổi nghĩa** | — |
| **`create_prefill`** | `dict[str,str]` — **LUÔN CÓ MẶT**, không bao giờ `null` | **MỚI (khoá thứ 10)** | Ngữ cảnh cha để màn tạo điền sẵn. **0 hoặc 1** cặp: khoá = **query key mà chính màn tạo đó đọc** (`route.query.<key>`), value = **mã bản ghi cha**. `{}` là **câu trả lời hợp lệ** |

```jsonc
// Ô «Phiếu sửa chữa» trên tab của một THIẾT BỊ (hub AC Asset)
{
  "doctype": "Asset Repair",
  "label_vi": "Phiếu sửa chữa",
  "total": 3, "truncated": 0, "total_capped": 0,
  "items": [ /* … 5 khoá/dòng … */ ],
  "deep_link_filters": { "asset_ref": "AC-ASSET-2026-00042" },  // Link FIELDNAME — lọc DANH SÁCH
  "can_create": true,
  "create_route_hint": "/cm/create",
  "create_prefill": { "asset": "AC-ASSET-2026-00042" }          // QUERY KEY — điền sẵn MÀN TẠO
}
```

> **Hai khoá, hai không gian tên — đọc kỹ dòng trên**: `deep_link_filters` mang **Link fieldname** (`asset_ref`) để lọc *danh sách*; `create_prefill` mang **khoá URL** (`asset`) để điền sẵn *màn tạo*. Cùng một giá trị, **hai cái tên**, và lẫn chúng đã sinh ra hai bug đắt tiền (§12.7 nhánh *tạo* · §13.1 nhánh *danh sách*).

#### §III.24.11.2 Khoá prefill theo (hub, ô) — SSoT, verify @source 2026-07-30

| Hub (cha) | Ô | Link fieldname (`parents`) | **Khoá prefill** | Màn tạo đọc khoá đó tại |
|---|---|---|---|---|
| `AC Asset` | «Phiếu bảo trì định kỳ» | `asset_ref` | **`asset`** | `/pm/work-orders/new` |
| `AC Asset` | «Phiếu sửa chữa» | `asset_ref` | **`asset`** | `/cm/create` |
| `AC Asset` | «Phiếu hiệu chuẩn» | `asset` | **`asset`** | `/calibration/new` |
| `AC Asset` | «Báo cáo sự cố» | `asset` | **`asset`** | `/incidents/new` |
| `AC Asset` | «Hồ sơ thiết bị» | `asset_ref` | **`asset`** | `/documents/new` |
| `PM Work Order` | «Phiếu sửa chữa» | `source_pm_wo` | **`pm_wo`** | `/cm/create` |
| `Incident Report` | «Phiếu sửa chữa» | `incident_report` | **`incident`** | `/cm/create` |

⛔ **CẤM** làm khoá prefill: `asset_ref` · `source_pm_wo` · `incident_report` · `final_asset` · `critical_asset` (schema BE — màn tạo **không đọc** ⇒ query rác + lời hứa giả).

#### §III.24.11.3 Ba lớp ca `create_prefill == {}` **hợp lệ** (KHÔNG phải bug)

| Ca | Ví dụ | `can_create` | `create_prefill` |
|---|---|---|---|
| Màn tạo không đọc khoá query nào | `Asset Transfer` · `AC Purchase` · `Service Contract` | **có thể `true`** | `{}` |
| Cặp (đích, cha) không có khoá | hub `PM Work Order` → ô «Phiếu hiệu chuẩn» (màn đọc `asset`,`schedule`, **không** `pm_wo`) | **có thể `true`** | `{}` |
| Liên kết **XUÔI** (`internal_links`) | hub `PM Work Order` → ô «Thiết bị»/«Lịch bảo trì định kỳ» | **`false`** | `{}` |

#### §III.24.11.4 P3 — capability là **TOKEN** (thay `has_permission` rời)

`create_capability_allows(dt)` = `rbac.can(CREATE_CAPABILITY[dt])` khi **có** khai; **không khai ⇒ giữ nguyên** `frappe.has_permission(dt, "create")`.

| DocType đích | Token | Gate API (điểm 1) | `requiredCapabilities` route tạo (điểm 2) | `CAPABILITY_MAP[token]` |
|---|---|---|---|---|
| `PM Work Order` | `pm.create` | `api/imm08.py:164` | `/pm/work-orders/new` → `['pm.create']` | `("PM Work Order","create")` |
| `Asset Repair` | `repair.create` | `api/imm09.py:111` | `/cm/create` → `['repair.create']` | `("Asset Repair","create")` |
| `IMM Asset Calibration` | `calibration.create` | `api/imm11.py:104` | `/calibration/new` → `['calibration.create']` | `("IMM Asset Calibration","create")` |
| `Incident Report` | `corrective.create` | `api/imm12.py:60` `_CAP_REPORT` (dùng qua `_can_report():76` trong `report_incident:88`) | `/incidents/new` → `['corrective.create']` | `("Incident Report","create")` |
| `AC Purchase` | `purchase.create` | `api/purchase.py:156` | `/purchases/new` → `['purchase.create']` | `("AC Purchase","create")` |

**3 doctype cố ý KHÔNG khai token** (khai là nói dối, không phải bỏ sót — lý do từng dòng ở ADR §12 D-CR4-2): `Asset Document` (route gác `document.write` ≠ `document.create`) · `Asset Transfer` (route gác `commissioning.create` → **doctype khác**) · `Service Contract` (route gác `data.create` → **doctype khác**).

> **Hành vi trên UI KHÔNG đổi vì mục này**: với cả 5 token, `CAPABILITY_MAP[token] == (dt,"create")` ⇒ `rbac.can(token)` cho **đúng** giá trị `has_permission` đang cho. Giá trị của thay đổi là **ràng buộc + guard** (đổi binding ở bất kỳ tầng nào ⇒ test ĐỎ thay vì trôi im lặng). QA **không** được chấm "không thấy khác gì" là FAIL.

#### §III.24.11.5 Nghĩa vụ client (bổ sung §III.24.10.3)

1. **Đọc `create_prefill` trực tiếp**, coi `{}` là **câu trả lời** ("không có gì để điền sẵn") — **KHÔNG** fallback sang `deep_link_filters` (khoá của nó là Link fieldname, dùng lọc *danh sách*).
2. Điều hướng bằng `router.push({ path, query })` với `query` = prefill **đã lọc** theo `CREATE_PREFILL_QUERY_KEYS[route]`; prefill rỗng sau lọc ⇒ **push trần** `{ path }` (URL **không** mọc dấu `?`).
3. Khoá backend gửi mà route không khai ⇒ **loại im lặng**, không đẩy vào URL, không cảnh báo người dùng (đó là chuyện của tầng khác).
4. **Không** dựng nút chỉ vì có `create_prefill`: điều kiện dựng nút vẫn là `can_create` **∧** route tồn tại **∧** capability của route đích (3 lớp, fail-CLOSED).

#### §III.24.11.6 Cửa sổ deploy (gunicorn `--preload`)

- Khoá ADDITIVE ⇒ **không** có ca "client mới đọc BE cũ" gây vỡ: BE chưa reload ⇒ `create_prefill` **vắng mặt** ⇒ `createTarget` (`?? {}`) ⇒ push trần = **đúng hành vi cũ** (màn tạo trống). Suy giảm tạm thời, tự lành sau `bench restart`.
- DoD chấm bằng `bench --site miyano run-tests` **module-isolated** (`timeout` tool ≥ 600000ms) + `vitest` + `vue-tsc` — **KHÔNG curl** (LL-DEPLOY-07/08: HTTP đang trả shape của worker cũ; đã có bằng chứng cứng 5 khoá vs 9/12 on-disk ở run-3/run-4).

---

## III.25. Tab «Lịch sử» — AC-CR-100: hợp đồng ĐỌC nguồn **đã phân trang** `get_asset_timeline` (0 delta shape, 1 dòng đổi `ORDER BY`)

> **CR**: `AC-CR-100` (đề mục PM gọi «AC-CR-96» — số đã bị chiếm, bảng đối chiếu [ADR §8.0](./ADR-IMM00-TRUNCATION-SSOT.md)). Quyết định: **ADR-IMM00-TRUNCATION-SSOT §8** (D-TL-1..9 · INV-TL-1..11). FR-00-TL-01 / BR-00-TL-01..09 ([02 §IV.40](./02_Analysis_Design.md)). FE: [06 §VIII.11](./06_Frontend_Design.md). Test: [07 §XIX](./07_Testing_QA.md).

### III.25.1 Shape response — **KHÔNG ĐỔI** (0 khoá mới, 0 OAS delta)

```jsonc
// GET assetcore.api.imm00.get_asset_timeline?name=AC-ASSET-…&page=1&page_size=100
{
  "success": true,
  "data": {
    "pagination": { "page": 1, "page_size": 100, "total": 137, "total_pages": 2, "offset": 0 },
    "items": [ /* AssetTimelineEvent × ≤ page_size, mới→cũ */ ]
  }
}
```

- `pagination` = `paginate(total, page, page_size)` (`utils/pagination.py:37`) — `page_size` **đã CLAMP** `[1, 100]` (`_MAX_PAGE_SIZE`, `:11`); `total` = `frappe.db.count("Asset Lifecycle Event", {"asset": name})`; `total_pages = ceil(total / page_size)`, `= 0` khi `total = 0`.
- Mirror mobile **đã đủ** và **KHÔNG đổi** vòng này: `AssetTimelineEnvelope` (`data.required = [pagination, items]`) + `Pagination.required ∋ total` — `docs/mobile/openapi/assetcore-mobile.openapi.yaml:1868-1901`, `:852-880`, op `getAssetTimeline` `:14235`. ⇒ **paths 110 · schemas 290 · parameters 38 GIỮ NGUYÊN**; 3 counter guard (`_EXPECTED_TEST_COUNT` 1024 · `_GUARD_SUITE_SUM` 1167 · `_MOBILE_OAS_TOTAL` 1193) **delta 0**.
- Asset ∄ ⇒ **HTTP-200** + Error envelope `code = 404` (`_err(_(_ERR_ASSET_NOT_FOUND), 404)`, `api/imm00.py:1215`) — **KHÔNG** raise → HTTP-4xx. Asset tồn tại mà chưa có event ⇒ `items = []` + `total = 0` (KHÔNG 404).

### III.25.2 **Đổi duy nhất ở BE**: `ORDER BY` phải TIỀN ĐỊNH (BR-00-TL-08)

| | Trước | Sau |
|---|---|---|
| `_ORDER_EVENT_TS_DESC` (`api/imm00.py:293`) | `"timestamp desc"` | `"timestamp desc, name desc"` |

- **Vì sao bắt buộc**: `Asset Lifecycle Event` trùng `timestamp` là **ca thường** (một `transition_asset_status` có thể emit ≥2 event trong cùng giây; patch/seed emit hàng loạt). Với hàng trùng khoá sắp xếp, MySQL **không đảm bảo** thứ tự nhất quán giữa hai truy vấn `LIMIT/OFFSET` ⇒ trang 2 **lặp** dòng của trang 1 **và BỎ SÓT** dòng khác ⇒ client "tải hết" mà vẫn thiếu — nguy hiểm hơn cắt im lặng, vì người dùng tin là đã đủ.
- `autoname: naming_series:` ⇒ `name` **tăng đơn điệu theo thứ tự ghi** ⇒ tiebreaker vừa tiền định vừa đúng chiều thời gian thật. Precedent: `services/imm10.py:76 order_by="published_date desc, name desc"`.
- **Biên**: đổi **giá trị hằng trên ĐÚNG 1 dòng** ⇒ **0 dịch dòng** trong `api/imm00.py` ⇒ **0 cite-drift** cho guard cite `@api/imm00.py:<line>` (OAS + `test_mobile_oas`). KHÔNG đổi `fields`, `filters`, `limit_start`, `limit_page_length`, batch `actor_name`, normalize `root_*`.
- **Hệ quả vận hành**: vòng này **đụng `.py` prod** ⇒ mở **1 blocker `bench restart` mới** (`gunicorn --preload`). DoD chấm bằng `bench --site miyano run-tests` (fresh-import), **KHÔNG curl** (LL-DEPLOY-07/08). **KHÔNG** `bench migrate` (0 schema delta).

### III.25.3 Nghĩa vụ của **client** (hợp đồng 2 đầu — điều mới của vòng này)

| # | Nghĩa vụ | Vi phạm ⇒ |
|---|---|---|
| C1 | Tiêu thụ `pagination.total` làm **số công bố**; không suy từ `items.length` | cắt IM LẶNG (lần thứ 6 của lớp lỗi này) |
| C2 | Không cast (`as unknown`/`as any`) giá trị trả về của api-client | mất `pagination` khỏi tầm nhìn compiler |
| C3 | Lật trang bằng **`page`**, `page_size` GIỮ `100` (= trần thật) | tưởng xin 200 mà chỉ nhận 100 (INV-TRUNC-LIMIT) |
| C4 | APPEND + dedupe theo `name`; tải hết ⇒ số dòng render `== total` | `count != rows` ở lớp UI |
| C5 | Tách 3 trạng thái *chưa tải / rỗng thật / lỗi* | lỗi mạng hiện thành "thiết bị chưa có lịch sử" |

### III.25.4 Invariants BE chấm được (INV-TL-9/10 — guard `tests/test_imm00.py`)

- **INV-TL-9**: `get_asset_timeline(name, page_size=2)` trên asset có ≥3 ALE ⇒ `pagination.total == frappe.db.count("Asset Lifecycle Event", {"asset": name})` (≥3) ∧ `len(items) == 2` ∧ `total_pages == ceil(total/2)` ∧ `names(page1) ∩ names(page2) = ∅` ∧ `names(page1) ∪ names(page2) ⊆` tập name thật.
- **INV-TL-10** (điều kiện tiên quyết của BR-00-TL-09): `"Asset Lifecycle Event" ∉ frappe.get_hooks("permission_query_conditions")` — chỉ khi đó `frappe.db.count` (raw) ≡ count của `frappe.get_list` (permission-aware). Nếu tương lai thêm PQC cho ALE thì guard **ĐỎ** ⇒ buộc đổi `total` sang engine permission-aware (D6 / INV-ROWSCOPE) thay vì lặng lẽ nói dối.
- **Không** đổi ngữ nghĩa 404/200 · **không** thêm/bớt field · **không** đụng `page_size` default `50` của handler (FE gửi `100` tường minh).

## III.26. Hồ sơ **VẬN HÀNH** của một thiết bị — AC-CR-102: hợp đồng **ĐỌC** 3 endpoint LIVE của IMM-08 / IMM-09 / IMM-12 (**0 delta BE**)

> **Luật vòng này:** ba endpoint **KHÔNG đổi 1 ký tự** — không path, không param, không khoá response, **0 OAS delta**. Mục này là **hợp đồng ĐỌC** (consumer contract) do IMM-00 cần: nó **chép từ chữ ký thật + `fields=[…]` thật trên đĩa**, không suy diễn (`BR-00-OPH-17`, AC12). Spec đầy đủ + quyết định: [`ADR-IMM00-ASSET-OP-HISTORY`](./ADR-IMM00-ASSET-OP-HISTORY.md) §4. Owner-doc của từng endpoint: [`docs/imm-08/05 §9`](../imm-08/05_API_Specification.md) · [`docs/imm-09/05 §3.14`](../imm-09/05_API_Specification.md) · [`docs/imm-12/05 §20`](../imm-12/05_API_Specification.md).

### III.26.1 Ba endpoint (verify từ đĩa 2026-07-30)

| # | Endpoint | Verb | Param | `data` | Đơn vị dòng |
|---|---|---|---|---|---|
| 1 | `assetcore.api.imm08.get_asset_pm_history` (`api/imm08.py:198`) | GET | `asset_ref` **required** · `limit` int **default 10** | `{asset_ref, history[], total, truncated}` | **`PM Task Log`** (10 field) |
| 2 | `assetcore.api.imm09.get_asset_repair_history` (`api/imm09.py:195`) | GET | `asset_ref` **required** · `limit` str default `"10"` | `{asset_ref, history[], total, truncated}` | `Asset Repair` **`docstatus=1`** (9 field) |
| 3 | `assetcore.api.imm12.get_asset_incident_history` (`api/imm12.py:232`) | GET | **`asset`** **required** · `limit` int default 10 | **`{asset, items[], total, truncated}`** | `Incident Report` mọi docstatus (9 field) |

**Ba bẫy hợp đồng mà consumer PHẢI xử lý (đọc sai ⇒ "chưa có dữ liệu" GIẢ):**

1. **Bất đối xứng khoá IMM-12**: rows-key là **`items`** (không phải `history`), asset-key là **`asset`** (không phải `asset_ref`). Cố ý, đã ratify ở `docs/imm-12/05 §20` ⇒ **KHÔNG sửa BE**; store IMM-12 đọc `res.items`.
2. **`limit` đã đồng bộ 3 tab** qua SSoT `clamp_page_size(limit, 10)`: `limit=0` **về 10** (KHÔNG "không giới hạn"), `limit>100` **chặn ở 100**. Hành vi này **đã ratify** (`docs/imm-12/05 §20`) — QA đừng coi là regression.
3. **`total`/`truncated` khai OPTIONAL ở FE là CỐ Ý**: worker `gunicorn --preload` chưa reload có thể trả shape cũ thiếu 2 khoá ⇒ đọc phòng thủ `total ?? rows.length`, `Number(truncated) === 1 ? 1 : 0` (giữ nguyên mã hiện có).

### III.26.2 Envelope + lỗi (đúng DONE-gate spec-contract)

- Cả 3 đi qua `handle(...)` ⇒ thành công `{success: true, data: {...}}`.
- **Lỗi nghiệp vụ = in-handler HTTP-200 + Error envelope** — **KHÔNG** `raise` → HTTP-4xx.
- **Hai loại 403 phải phân biệt**: (a) **dispatcher-403** guest/no-token (ngoài handler); (b) **in-handler 403 trên HTTP-200** — `@rowscoped` đổi `frappe.PermissionError` → Error envelope (`BR-00-ROWSCOPE-403`). Riêng IMM-12 còn chặn `Guest` ở handler ⇒ **401** envelope (`api/imm12.py:234-235`) + `assert_doctype_read_permission('Incident Report')` ở service.
- **Hệ quả FE bắt buộc**: persona **thiếu DocPerm read** (vd `PM User` với `Asset Repair` — xem cải chính `docs/imm-09/05 §3.14`) nhận **403 envelope** ⇒ ~~section phải hiện **trạng thái LỖI** (`BR-00-OPH-13`)~~, **KHÔNG** hiện «Chưa có lần sửa chữa …». Nói "chưa có" khi thực ra "không được xem" là **sai sự thật**.
  > ⚠️ **SUPERSEDED 2026-07-30 bởi `AC-CR-119`** (nửa «trạng thái LỖI» — [ADR §11.5 `D-OPH-24`](./ADR-IMM00-ASSET-OP-HISTORY.md), `BR-00-OPH-35`). 403 ⇒ section hiện **trạng thái KHOÁ** `[op-history-locked]` (**0** «Thử lại», **0** «Xem tất cả», **0** badge số): thiếu quyền **không phải sự cố tạm** ⇒ không có gì để thử lại. Nửa «**KHÔNG** hiện *Chưa có …*» **GIỮ NGUYÊN hiệu lực** (`locked` ≠ `empty`). Vị-từ để FE biết trước là cap SOUND ở **§III.26.7**, **KHÔNG** phải `pm.read`.

### III.26.3 `fields` chính xác (SSoT — FE khai type theo bảng này)

| Nhánh | `fields=[…]` @source | `order_by` | Filter |
|---|---|---|---|
| PM | `name, pm_work_order, pm_type, completion_date, technician, overall_result, is_late, days_late, next_pm_date, summary` (`services/imm08.py:1747-1749`) | `completion_date desc` | `{asset_ref}` |
| CM | `name, repair_type, priority, open_datetime, completion_datetime, mttr_hours, sla_breached, root_cause_category, repair_summary` (`services/imm09.py:2609-2611`) | `open_datetime desc` | `{asset_ref, docstatus: 1}` |
| Sự cố | `name, incident_type, severity, status, reported_at, fault_code, closed_date, linked_capa, rca_record` (`services/imm12.py:1750-1752`) | `_ORDER_REPORTED_AT` | `{asset}` |

Kiểu Frappe → TS (grounded `*.json`): `is_late`/`sla_breached` = **Check** ⇒ `0|1`, đọc bằng `isCheckOn` · `days_late` Int · `mttr_hours` Float · `overall_result` Select `Pass|Pass with Minor Issues|Fail` · `repair_type` Select `Corrective|Breakdown|Warranty Repair` · `severity` Select `Low|Medium|High|Critical` · `pm_work_order` Link → `PM Work Order` (**có thể rỗng** ⇒ `BR-00-OPH-08`) · `pm_type` **Data tự do** (⇒ **không render**, tránh leak EN).

### III.26.4 Bất biến «hai con số» — count(ô connections) ⇄ total(section)

| Nhánh | Quan hệ | Guard |
|---|---|---|
| PM | **độc lập** (`PM Task Log` ≠ `PM Work Order`) | `INV-OPH-15` |
| CM | `section.total ≤ ô.total` (section lọc `docstatus=1`) | `INV-OPH-17` |
| Sự cố | **BẰNG NHAU** (cùng filter `{asset}`, cùng "mọi docstatus") | `INV-OPH-16` |

Đây là phần **thay thế** lý do cấm cũ ở `ADR-IMM00-TRUNCATION-SSOT §8.7`: hai số **hợp lệ đồng thời** vì tiêu đề section khai đúng tập hợp của nó (`BR-00-OPH-03`). Việc ô đếm chưa loại `docstatus==2` là nợ **có tên** `AC-CR-99` — **không** sửa trong vòng này (đụng `.py` prod ⇒ vi phạm AC12).

### III.26.5 Acceptance contract cho [FE] Bước-4 (đo được)

1. `git diff --stat -- 'assetcore/api/*.py' 'assetcore/services/**/*.py'` **không tăng path** so với đầu vòng; thêm file **chỉ** trong `assetcore/tests/`.
2. `0` OAS delta (`docs/mobile/openapi/*.yaml` không đổi) · 3 counter `_EXPECTED_TEST_COUNT` 1024 / `_GUARD_SUITE_SUM` 1167 / `_MOBILE_OAS_TOTAL` 1193 **delta 0** (module test mới không thuộc registry `test_mobile_docset._GUARD_SUITE_EXPECTED` ⇒ delta 0 tự nhiên — **đọc lại từ đĩa** trước khi chấm).
3. Guard BE mới `bench --site miyano run-tests --app assetcore --module assetcore.tests.integration.test_asset_operational_history_contract` **XANH** (timeout tool ≥600000ms) — nội dung: parity `fields` @source ⇄ bảng §III.26.3 + shape-key `history`/`items` + `clamp_page_size` bound + `INV-OPH-16`.
4. **KHÔNG curl** để chấm (LL-DEPLOY-07/08); vòng này **0 blocker reload mới** (không đụng `.py` prod) — nợ `bench restart` của các vòng trước **không** tính cho vòng này.

### III.26.6 `AC-CR-115` — hợp đồng **cắt** của 3 endpoint: `total`/`truncated` nói gì, FE được phép suy ra gì (**0 delta BE**)

> Quyết định + lý do: [`ADR-IMM00-ASSET-OP-HISTORY §10`](./ADR-IMM00-ASSET-OP-HISTORY.md) (`D-OPH-17..20`). Nghiệp vụ: [`02 §IV.43`](./02_Analysis_Design.md) `BR-00-OPH-19..30`. FE: [`06 §VIII.15`](./06_Frontend_Design.md). Test: [`07 §XXII`](./07_Testing_QA.md).
> **Vòng này KHÔNG đổi 1 ký tự** của `api/imm08.py` · `api/imm09.py` · `api/imm12.py` · `services/imm08|09|12.py` · `services/shared/truncation.py`. Chỉ **đặc tả rõ** ngữ nghĩa đã có + **thêm invariant** vào file test đã có.

#### a) Nguồn sinh `total`/`truncated` — đo từ đĩa 2026-07-30

Cả 3 nhánh đi qua **cùng một** SSoT `services/shared/truncation.py::truncation_meta(fetched, limit, count_fn)`:

```python
if fetched < limit:            # chưa chạm trần ⇒ đã lấy hết, KHÔNG phát COUNT (ZERO-COST)
    return fetched, 0
total = int(count_fn())        # chỉ khi NGHI còn dòng
truncated = 1 if total > limit else 0
```

Call-site: `services/imm08.py:1769` · `services/imm09.py:2628` · `services/imm12.py:1760`.

| Khoá | Kiểu | Ngữ nghĩa **chính xác** |
|---|---|---|
| `total` | `int ≥ 0` | Số bản ghi **user này được phép thấy** trên **đúng predicate** của truy vấn rows, **trước** khi áp trần `limit` (D6 của `ADR-IMM00-TRUNCATION-SSOT`). |
| `truncated` | `int ∈ {0,1}` | **Dẫn xuất từ `total > limit`** — tức từ **trần**, KHÔNG từ `len(rows)`. Đây là chỗ cờ và số **có thể rời nhau**. |

#### b) Vì sao FE **không được** render dải theo cờ (căn cứ hợp đồng, không phải thẩm mỹ)

1. `truncated` được tính từ **`limit`** (`total > limit`), còn thứ người dùng **thấy** là **`len(rows)`**. Hai đại lượng chỉ trùng khi `len(rows) == limit` — đúng ở ca thường, **không** đảm bảo bởi hợp đồng nào.
2. `total` do `count_fn()` sinh ở **nhánh mã khác** với truy vấn rows. Một lần sửa filter ở một nhánh mà quên nhánh kia là đủ để `total` và `len(rows)` rời nhau **mà không test nào đỏ** — trừ các invariant ở (c).
3. ⇒ **Hợp đồng dành cho FE**: `hidden = max(0, total − len(rows))`; render dải **⟺ `hidden > 0`**. FE là *tolerant reader*: **bỏ qua** `truncated` khi hai nguồn lệch (`BR-00-OPH-20/21/22`).

#### c) Invariant BE **MỚI** (≥3) — thêm vào `assetcore/tests/integration/test_asset_operational_history_contract.py`, **0 dòng prod đổi**

| ID | Nội dung (áp cho **cả 3** endpoint) | Fixture |
|---|---|---|
| **`INV-OPH-27`** | `total >= len(rows)` **luôn đúng** — không endpoint nào được trả tổng nhỏ hơn số dòng nó vừa trả. | 3 ca: dưới trần · **vừa khít** trần · trên trần |
| **`INV-OPH-28`** | **Cờ khớp số**: `truncated == (1 if total > len(rows) else 0)`. Đây là **mirror BE** của điều kiện render FE — nếu ĐỎ thì cờ và số đã rời nhau ⇒ **bug BE thật**, báo PM/BA, **KHÔNG** sửa `services/*.py` trong vòng này (`BR-00-OPH-30`). | 3 ca như trên |
| **`INV-OPH-29`** | **Số bị che đếm ĐÚNG**: với thiết bị có `limit + k` bản ghi hợp lệ (`k ≥ 1`), `total − len(rows) == k` **chính xác** (không xấp xỉ) ⇒ con số FE trừ ra có nghĩa. | `k = 3`, `limit = 10` |
| **`INV-OPH-30`** | **Rỗng thật**: thiết bị 0 bản ghi ⇒ `rows == [] ∧ total == 0 ∧ truncated == 0` (mirror BE của `BR-00-OPH-23`/AC4). | asset sạch |

> ⚠️ **Vừa khít trần là ca dễ sai nhất**: `fetched == limit ∧ total == limit` ⇒ `truncated = 0` **và** `total == len(rows)` ⇒ **0 dải** (đúng). Nếu ai đó "sửa" `truncation_meta` thành `truncated = 1 if fetched >= limit` thì `INV-OPH-28` **đỏ ngay** — đó là mục đích của nó.

#### d) Không phát sinh nhu cầu reload

Vòng này **0 dòng `.py` prod** ⇒ **0** nhu cầu `bench restart` mới; blocker BLOCKED-RELOAD của các vòng trước **không bị chạm** và **không** tính vào DoD vòng này. Chấm bằng `bench --site miyano run-tests --module assetcore.tests.integration.test_asset_operational_history_contract` (timeout tool **≥600000ms**) — **KHÔNG** `curl` (LL-DEPLOY-07/08).

### III.26.7 `AC-CR-119` — hợp đồng **QUYỀN** của 3 endpoint: cap nào SOUND, 403 đến như thế nào (BE: **+1 cap, +1 bảng, +1 gate tường minh**)

> **Luật vòng này:** hợp đồng **ĐỌC** (path/param/`fields`/`order_by`/khoá response/`limit`) **KHÔNG đổi 1 ký tự** — `0` OAS delta. Đổi duy nhất ở **lớp khai báo quyền**: thêm 1 cap vào SSoT, khai bản đồ nhánh→(cap, DocType) 1 lần, và làm gate role của nhánh Bảo trì **tường minh**. Quyết định đầy đủ: [`ADR-IMM00-ASSET-OP-HISTORY §11`](./ADR-IMM00-ASSET-OP-HISTORY.md).

#### a) Bảng quyền SOUND — 3 nhánh (đo từ đĩa 2026-07-30)

| Nhánh | Endpoint | DocType **truy vấn thật đọc** | Đường gate THẬT | Cap **SOUND** |
|---|---|---|---|---|
| pm | `imm08.get_asset_pm_history` (`api/imm08.py:198` → `services/imm08.py:1744`) | **`PM Task Log`** (`repositories/pm_repo.py:20`) | `PMTaskLogRepo.list(...)` scope mặc định `"user"` → `count_with_or` → `frappe.get_list` (`filters.py:281` (invariant docstring `:249-262`)) ⇒ `PermissionError`. **`AC-CR-119` thêm** `assert_doctype_read_permission("PM Task Log")` **tường minh** trước truy vấn (`D-OPH-27`) | **`pm.read_history`** → `("PM Task Log","read")` — **MỚI** |
| cm | `imm09.get_asset_repair_history` (`api/imm09.py:195` → `services/imm09.py:2601`) | `Asset Repair` (`repair_repo.py:8`) | `RepairRepo.list(scope="system")` → `repositories/base.py:143-144` `assert_doctype_read_permission(cls.DOCTYPE)` | `repair.read` → `("Asset Repair","read")` — **đã có, SOUND** |
| incident | `imm12.get_asset_incident_history` (`api/imm12.py:232` → `services/imm12.py:1709`) | `Incident Report` (`services/imm12.py:44`) | `assert_doctype_read_permission(_DT_INCIDENT)` tường minh (`services/imm12.py:1732`) | `corrective.read` → `("Incident Report","read")` — **đã có, SOUND** |

**Vì sao `pm.read` KHÔNG SOUND cho nhánh pm** (đây là bug gốc của 403-chết): `pm.read` auto-gen từ `_DOMAIN_PRIMARY["PM"] = "PM Work Order"` (`rbac.py:70,100-103`) ⇒ bind **`PM Work Order`**, nhưng endpoint đọc **`PM Task Log`**. Hai DocType, hai bảng DocPerm:

| Role | `PM Work Order`.read | `PM Task Log`.read |
|---|---|---|
| `AssetCore Super Admin` · `PM Manager` · `PM User` · `AssetCore Auditor` | 1 | 1 |
| **`Commissioning Manager`** | **1** (`pm_work_order.json`) | **KHÔNG có dòng** (`pm_task_log.json` chỉ khai 4 role) |

⇒ `rbac.can("pm.read")` = **True** trong khi endpoint trả **403**. Gate FE bằng vị-từ này = mở nhánh rồi ăn 403 (`BR-00-OPH-31`).

#### b) SSoT bản đồ nhánh — khai **ĐÚNG MỘT LẦN**

`assetcore/services/shared/connection_meta.py` (mục 4c, cạnh `CREATE_CAPABILITY` — file này **không** import `frappe` ở mức module, luật ADR §D9):

```python
OP_HISTORY_BRANCH_GATE: dict[str, tuple[str, str]] = {
    "pm":       ("pm.read_history", "PM Task Log"),
    "cm":       ("repair.read",     "Asset Repair"),
    "incident": ("corrective.read", "Incident Report"),
}
```

Khoá là **khoá nhánh của FE** (`SectionKey` — `AssetOperationalHistory.vue:121`) ⇒ bảng BE và mảng `SECTIONS` của FE nói cùng một thứ tiếng. **Guard bắt buộc** (`INV-OPH-32`): ∀ nhánh — `CAPABILITY_MAP[cap][0] == doctype` ∧ `CAPABILITY_MAP[cap][1] == "read"` ⇒ đổi binding cap = **ĐỎ**, không im lặng. FE **chỉ chép 3 chuỗi cap**, **KHÔNG** giữ bảng doctype thứ hai (`BR-00-OPH-33`).

#### c) Hợp đồng 403 — đo bằng **HÀNH VI**, không bằng đọc mã (`BR-00-OPH-32`)

∀ user *u*, ∀ nhánh *b*:

```
rbac.can(cap_b) is True   ⇒  endpoint_b KHÔNG trả FORBIDDEN
rbac.can(cap_b) is False  ⇒  endpoint_b trả ĐÚNG:
                             HTTP 200 + {success:false, code:"FORBIDDEN", http_status:403}
                             message == MSG.AUTH_FORBIDDEN ("Bạn không có quyền thực hiện hành động này.")
```

**KHÔNG** HTTP-500 · **KHÔNG** dispatcher-403 (status-line) · **KHÔNG** list rỗng giả. Biconditional đúng **theo cấu tạo**: `rbac.can(cap)` = `frappe.has_permission(dt, ptype)` (`rbac.py:183-187`) và gate của cả 3 endpoint cũng là `frappe.has_permission(dt,"read")` (`permissions.py:78-79`) — **cùng vị-từ, cùng DocType**.

**Khe hở duy nhất, đã đo và chấp nhận:** `assert_doctype_read_permission` dùng `ptype = "select" if frappe.only_has_select_perm(dt) else "read"` còn `rbac.can` luôn `"read"` ⇒ user *chỉ có* `select` sẽ **cap=False mà endpoint cho phép** ⇒ FE **khoá quá** (fail-closed, **không** rò dữ liệu). Đo trên đĩa: `pm_task_log.json` · `asset_repair.json` · `incident_report.json` có **0** dòng DocPerm mang `select` ⇒ ca này hiện **không tồn tại**; khoá bằng `INV-OPH-36`.

**Không rò nội bộ** (`BR-00-OPH-34`): message là **hằng** từ registry (`utils/messages.py:61,330-336`), và `assert_doctype_read_permission` raise `frappe.PermissionError` chứ **KHÔNG** `frappe.throw` — `frappe.throw` sẽ msgprint đẩy tên DocType vào `_server_messages` (`permissions.py:69-73`).

**Riêng IMM-12** còn chặn `Guest` ngay ở handler ⇒ **401** envelope (`api/imm12.py:234-235`), **trước** cả cap-403. Hai loại phải phân biệt ở FE: 401 ⇒ hết phiên (redirect); 403-in-envelope ⇒ **KHÔNG** logout.

#### d) `CAP_SET_VERSION` — hệ quả bắt buộc, khai TRƯỚC

`len(CAPABILITY_MAP)` **104 → 105**; `CAP_SET_VERSION` **`v104.e46d05d9a66d` → `v105.<digest>`**. Giá trị **PHẢI ĐO** bằng `bench --site miyano execute assetcore.services.shared.rbac._compute_cap_set_version` rồi dùng **đúng giá trị đo được** ở **cả** BE test **và** `frontend/src/stores/auth.ts` — **CẤM gõ hash tay**. Danh sách **13 assert sẽ ĐỎ / 4 file** + 4 điểm cite-drift + 5 điểm cố ý không sửa: [ADR §11.9](./ADR-IMM00-ASSET-OP-HISTORY.md). **CẤM** nới assert cho xanh — guard đang làm đúng việc của nó.

**Cần reload, KHÔNG cần migrate:** 3 file `.py` prod đổi ⇒ `bench restart` (gunicorn `--preload`) + `bench --site miyano clear-cache` (xoá cache caps `ac_caps::*`, TTL 1h — `rbac.py:217`) để `pm.read_history` xuất hiện trong `get_capabilities`. **0** schema/patch/fixture delta ⇒ **KHÔNG** `bench migrate`. Cả hai lệnh **thuộc USER** (HARD-STOP).

#### e) Acceptance contract cho [BE] + [FE] Bước-4 (đo được)

0. **Biên `.py` prod chấm bằng DELTA so với ĐẦU VÒNG** (working tree đã DIRTY từ các vòng trước ⇒ `git diff` tuyệt đối vô nghĩa làm ngưỡng): `assetcore/api/*.py` **không tăng** path; `assetcore/services/**/*.py` tăng **đúng 3** path (`shared/rbac.py` · `shared/connection_meta.py` · `imm08.py`). Chụp `git diff --name-only … | sort` trước/sau rồi `diff`.
1. `assetcore/services/shared/rbac.py` có **đúng 1** cặp khoá-giá-trị mới `"pm.read_history": ("PM Task Log", "read")`; `pm.read` **KHÔNG đổi**; `len(CAPABILITY_MAP) == 105`.
2. `OP_HISTORY_BRANCH_GATE` tồn tại ở `connection_meta.py` với **đúng 3** khoá `pm`/`cm`/`incident` và giá trị đúng bảng (a); `INV-OPH-32` XANH.
3. `services/imm08.py::get_asset_history` có `assert_doctype_read_permission(_DT_PM_TASK_LOG)` **trước** `PMTaskLogRepo.list`; **0** đổi `fields`/`filters`/`order_by`/`page_size`/khoá response ⇒ `test_asset_operational_history_contract` (parity `fields` @source) **giữ XANH không sửa**.
4. Guard BE **mới** `bench --site miyano run-tests --app assetcore --module assetcore.tests.integration.test_asset_op_history_acl` **XANH** (timeout tool **≥600000ms**) — nội dung: `INV-OPH-31..36` (soundness 2 chiều bằng hành vi · parity bảng ↔ `CAPABILITY_MAP` · không-leak · `Commissioning Manager` chứng minh `pm.read` unsound · 0 DocPerm select-only).
5. `0` OAS delta; 3 counter `_EXPECTED_TEST_COUNT` / `_GUARD_SUITE_SUM` / `_MOBILE_OAS_TOTAL` **delta 0** (module test mới không thuộc registry `test_mobile_docset._GUARD_SUITE_EXPECTED` ⇒ delta 0 tự nhiên — **đọc lại từ đĩa** trước khi chấm).
6. **KHÔNG curl** để chấm (LL-DEPLOY-07/08) — vòng này thêm **1** nhu cầu reload vào blocker BLOCKED-RELOAD; mọi kết luận live trước reload là **vô nghĩa**.

---

## DoD — File 05 hoàn chỉnh

### I. Conventions
- [x] Response envelope `{success, data}` — không dùng `{message: {...}}`
- [x] Authentication (Token + Session)
- [x] HTTP status codes
- [x] Business error codes (AC-E001 → AC-E012)
- [x] Pagination
- [x] Filter convention
- [x] Rate limiting

### II. Permission matrix
- [x] 8 roles × tất cả endpoint nhóm

### III. Endpoints (verified vs `api/imm00.py`)
- [x] AC Asset (9 endpoints — list [filter gmdn_code], get, create, update, delete, transition_status, get_asset_timeline, validate_for_operations, get_asset_kpi)
- [x] AC Supplier (5 endpoints — list, get, create, update, delete)
- [x] Location/Dept/Category (9+ endpoints — full CRUD per entity)
- [x] IMM Device Model (5 endpoints — list, get, create, update, delete + upload_device_model_file)
- [x] IMM SLA Policy (5 endpoints — list, get, resolve, create, update, delete)
- [x] IMM Audit Trail (3 endpoints — list_audit_trail, get_audit_entry, verify_chain)
- [x] IMM CAPA Record (5 endpoints — list, get, open_capa, close_capa_record, list_overdue_capas)
- [x] Asset Lifecycle Event (2 endpoints — list_lifecycle_events, get_lifecycle_event)
- [x] Incident Report (6 endpoints — list, get, create, update, submit, delete)
- [x] GMDN Status — đã loại bỏ (lọc thiết bị nay qua `list_assets?gmdn_code=`)
- [x] Scheduler Trigger (3 endpoints — GET, Admin only: trigger_capa_overdue_check, trigger_contract_expiry_check, trigger_registration_expiry_check)
- [x] Asset Transfer (7 endpoints — CRUD + workflow: approve, reject, receive)
- [x] Service Contract (6 endpoints — CRUD + list_asset_contracts)
- [x] PM Schedule (5 endpoints)
- [x] PM Checklist Template (5 endpoints)
- [x] Firmware Change Request (5 endpoints)
- [x] Document Request (5 endpoints)
- [x] Depreciation (9 endpoints — compute, get_schedule, regenerate, preview, run_due_now, bulk_regenerate, list_assets_depreciation [+ `depreciation_filter` BR-05-15], get_depreciation_stats, compute_all_depreciation)
- [x] Asset Downtime Metrics (1 endpoint)

### IV. Business Rule mapping
- [x] Endpoint → BR table
