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
| 429 | Too Many Requests | Rate limit (BR-00-29 — 2 endpoint QR resolve; **BR-00-38 — rotate `regenerate_asset_qr_token`, bucket+ngưỡng RIÊNG**) |
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
| `page_size` | int | 20 | 100 | server cap tại 100 |
| `sort` | string | `modified desc` | — | Frappe order_by syntax |

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

Vượt hạn → HTTP 429.

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

**KHÔNG áp rate-limit lên** `get_asset_label_data`, `get_asset_label_data_batch`, `mark_label_printed` (3 endpoint in-nhãn) — chúng đã `asset.write`-gated, low-volume admin (in nhãn hàng loạt là thao tác hợp lệ tần suất cao). Least-surprise: KHÔNG chặn nhầm in-nhãn-hàng-loạt.

> **⚠️ Self-Correction Vòng 27 B (§I.7b — BR-00-38): `regenerate_asset_qr_token` ĐÃ TÁCH KHỎI** danh sách miễn rate-limit trên. Rotate là GHI **bảo mật** (vô hiệu hoá nhãn QR đã in + ghi audit chain), hiếm-tần-suất, có thể bị spam-rotate (DoS nhãn hợp lệ + write-amplification audit). → mang `@rate_limit(limit=AC_QR_REGEN_RATE_LIMIT, seconds=60, ip_based=True)` với hằng RIÊNG `AC_QR_REGEN_RATE_LIMIT = 10` (THẤP hơn resolve=30) + bucket RIÊNG (cmd). 429 NGOÀI/TRƯỚC `rbac.require` → 0 side-effect, no-leak. Chi tiết §III.1 `regenerate_asset_qr_token` + [02 BR-00-38](./02_Analysis_Design.md). FE cặp: FR-00-87/88 (httpStatusToCode 429→RATE_LIMITED + message VI).

> **Rate-limit (req/phút/IP) ≠ batch-size cap (per-request payload) — 2 lớp phòng thủ TRỰC GIAO.** Tuy 2 endpoint nhãn batch (`get_asset_label_data_batch`, `mark_label_printed`) KHÔNG mang `@rate_limit`, chúng VẪN bị **cap kích thước batch** `_MAX_LABEL_BATCH=200` (vòng 22 / BR-00-33): 1 request truyền N (vô hạn) name → batch-read/IDOR + (write) ghi 2 record/asset/transaction → khuếch đại. Cap chặn payload-DoS Y request đơn lẻ; rate-limit chặn brute-force/flood NHIỀU request. Chi tiết spec từng endpoint dưới (§`get_asset_label_data_batch`, §`mark_label_printed`).

**KHÔNG đổi schema/cap/DocType/patch:** vòng này thuần thêm decorator + hằng `AC_QR_RESOLVE_RATE_LIMIT` + test. `CAP_SET_VERSION` GIỮ `v95.3388ee5629c1`. FE KHÔNG đổi (BE-only) — FE cần xử lý 429 gracefully đã nằm trong contract notification chung (xem 06).

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
| transition_status | ✓ | ✓ | ✓ | — | — | ✓ | — | — |
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

> **‡ QR deep-link resolve (`resolve_qr_token`, `get_asset_scan_info`) — rate-limited (Vòng 12 B):** ngoài RBAC/IDOR, 2 endpoint NÀY có `@rate_limit(AC_QR_RESOLVE_RATE_LIMIT=30/60s/IP/endpoint)` chống brute-force token + DoS (entry-point camera điện thoại `/a/<token>` & `/scan/:token`). 429 chạy TRƯỚC RBAC, no-leak parity với 404/403. KHÔNG áp lên 3 endpoint in-nhãn (`get_asset_label_data[_batch]`, `mark_label_printed`) — đã `asset.print`-gated (D6), low-volume. **`regenerate_asset_qr_token` (rotate) CÓ rate-limit RIÊNG** `@rate_limit(AC_QR_REGEN_RATE_LIMIT=10/60s/IP)`, bucket RIÊNG (Vòng 27 B / BR-00-38 — rotate = GHI bảo mật, ngưỡng THẤP hơn resolve). Chi tiết §I.7a/§I.7b.

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
| `search` | str | Tìm theo `asset_name`, `asset_code`, `manufacturer_sn`, **`gmdn_code`** (LIKE substring) |

> **Note (2026-05-19):** Tham số lọc theo trạng thái sử dụng GMDN (cũ) đã bị loại bỏ cùng field tương ứng. Trục lọc/quản lý thiết bị nay là `gmdn_code`. Tham chiếu: [docs/res/analysis/gmdn-asset-category-analysis.md](../res/analysis/gmdn-asset-category-analysis.md) §6.

> **INVARIANT count==drill (BR-00-17 — Vòng 31):** `list_assets(byt_status='expiring')` `pagination.total` == KPI `get_overview().assets.byt_expiring_30d`; `list_assets(byt_status='expired')` `pagination.total` == `get_overview().assets.byt_expired`, byte-for-byte trên CÙNG dataset + CÙNG vendor scope (cả 2 read-path gọi SoT `byt_expiry_filter`). FE tile NĐ98 click → `/assets?byt_status=expiring\|expired`; header "Tổng N" của list == giá trị tile vừa click. KHÔNG inline literal window — xem [04 Backend §III.1a](../imm-00/04_Backend_Design.md).

> **Reserved test-prefix exclusion (BR-00-35 — Vòng 25 B, áp NGẦM mọi request):** `list_assets` **luôn** loại asset rác test/security-audit qua SSoT `reserved_test_prefix_sql()` — KHÔNG trả row nào có `asset_name` bắt đầu `_` (`_Test*`/`_Probe*`) HOẶC `name` bắt đầu `SI-` (security-injection probe). Không có param điều khiển (mặc định bật, áp cho TẤT CẢ caller). Escape-safe (`ESCAPE '\\'` tường minh → `_` đầu chuỗi là LITERAL). 3 nguồn count (`pagination.total` non-search, search-count, `get_overview().assets.total`) áp **CÙNG** predicate ⟹ **INVARIANT `total == len(items)`** khi cùng filter (parity IMM-06/12). 0 false-positive: asset hợp lệ (`Máy thở`, `TS-2025-USG-001`, `AC-ASSET-…`, `Model_X` có `_` ở GIỮA) hiện đầy đủ. FE list/count **tự hưởng lợi, KHÔNG đổi component**. Xem [04 Backend §II.1.13-TESTPREFIX](../imm-00/04_Backend_Design.md). (Helper đã ship dùng bộ 3 tên `reserved_prefix_sql`/`reserved_prefix_filter`/`reserved_asset_names` — `reserved_test_prefix_sql` ở đây là tham chiếu đồng nghĩa, KHÔNG rename code.)

> **Compose AND với vendor-scope (BR-00-35 mục 6 / FR-00-84 — Self-Correction Vòng 26 B, RC-LIST-VENDORCLOBBER):** reserved-exclusion áp ORM filter trên field **`name`** (`{"name": ["not in", reserved]}` qua `reserved_prefix_filter()`). `apply_vendor_scope` (AUTH-01) cho **Vendor Engineer** cũng áp predicate trên field `name` (`{"name": ["in", assigned]}`). Hai predicate cùng field ⟹ **KHÔNG** merge bằng `dict.update` (sẽ ghi đè key `name` → mất vendor-scope = HIGH regression). `list_assets` compose AND qua **filter-list form** (hai dòng `name` riêng biệt, ANDed) → predicate hiệu dụng `name ∈ (assigned ∖ reserved)`: Vendor Engineer chỉ thấy asset **được giao việc** VÀ đã loại reserved-prefix; scope RỖNG (`["__none__"]`) → 0 row (KHÔNG fallback toàn bộ). INVARIANT `total == len(items)` giữ ở cả 3 nguồn count cho MỌI persona (Administrator/bypass + Vendor Engineer). Helper SSoT KHÔNG đổi tên. 2 endpoint `list_assets_depreciation`/`get_depreciation_stats` KHÔNG gọi `apply_vendor_scope` → giữ `filters.update(reserved_prefix_filter())` an toàn (no-regress). Xem [04 §II.1.13-TESTPREFIX RC-LIST-VENDORCLOBBER](../imm-00/04_Backend_Design.md) + [02 FR-00-84](../imm-00/02_Analysis_Design.md).

---

### `get_asset` — Chi tiết Asset

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.get_asset` |
| Capability | `asset.read` (read-only — xem 04 §III.1c-1; KHÔNG đổi) |

**Request:** `?name=AC-ASSET-2026-00001`

**Response 200** — đầy đủ HTM fields (asset_name, udi_code, gmdn_code, byt_reg_no, byt_reg_expiry, lifecycle_status, risk_classification, next_pm_date, next_calibration_date, commissioning_date, …) + display-name enrich (`category_name`, `department_name`, `location_name`, `supplier_name`, `device_model_name`, `responsible_technician_name`).

> **No-raw-token (CHỐT Vòng 24 B — ADR-001 §D4.1 / BR-00-34, rule 9 mở rộng):** payload build qua `frappe.get_doc("AC Asset", name).as_dict()` PHẢI **STRIP** field `qr_token` (`data.pop("qr_token", None)` SAU `as_dict()`, TRƯỚC enrich/`_ok`) → response **KHÔNG BAO GIỜ** còn key `qr_token`. `qr_token` là **khóa tra cứu MỜ** (opaque), enumeration-safe (D1) — token thô KHÔNG rời BE qua đường ĐỌC asset. **Acceptance:** `assert 'qr_token' not in data`. **Mọi field khác GIỮ NGUYÊN** (FE `AssetDetailView` render đầy đủ — KHÔNG re-whitelist, chỉ pop 1 key). Deep-link/in nhãn KHÔNG qua `get_asset` — dùng `get_asset_label_data` (`qr_url` dựng server-side qua `_build_qr_url`) / `regenerate_asset_qr_token`. RBAC/IDOR/404 GIỮ NGUYÊN (`assert_vendor_can_access` 403 + 404 `AC-E001`). Parity đồng nhất: `get_asset_timeline` (đọc Asset Lifecycle Event — KHÔNG có `qr_token`), `get_asset_kpi` (build dict KPI tường minh — KHÔNG `as_dict()`), `resolve_qr_token`/`get_asset_scan_info`/`get_asset_label_data[_batch]` (đã whitelist tường minh). **Guard chống tái phát:** test Grep/AST khẳng định 0 endpoint trả `get_doc(_DT_ASSET, …).as_dict()` thiếu strip `qr_token` (chống regress khi thêm endpoint asset-read mới) — xem [07 §Guard no-raw-token](./07_Testing_QA.md). **KHÔNG schema-delta** (`CAP_SET_VERSION` GIỮ `v95.3388ee5629c1`); FE KHÔNG đổi (BE-only — 0 FE đọc field `data.qr_token` từ payload đọc-asset; `grep -rn qr_token frontend/src` chỉ ra endpoint-name/comment/URL-flow, KHÔNG consumer payload).

**Errors:** 404 (`AC-E001`), 401, 403.

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
| Token KHÔNG tồn tại | **404** `AC-E001` | KHÔNG 500, message generic — enumeration/leak-safe |
| User KHÔNG có `asset.read` | **403** PermissionError | `require("asset.read")` |
| Vendor user, asset NGOÀI scope | **403** (`ErrorCode.FORBIDDEN`) | `assert_vendor_can_access("AC Asset", name)` — IDOR guard, KHÔNG trả data |

**Audit:** KHÔNG ghi audit/lifecycle khi resolve (read-only lookup — chốt ADR-001 D4, tránh spam chain mỗi lần quét).

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

Resolve thứ tự: nếu có `token` → `frappe.db.get_value("AC Asset",{"qr_token":token},"name")`; nếu không → dùng `name`. Cả hai rỗng/không khớp → 404 leak-safe.

**Response 200:**
```json
{ "success": true, "data": {
  "name": "AC-ASSET-2026-00001",
  "asset_code": "BV-A-001",
  "asset_name": "Máy thở Bennett 980 — HSTC G03",
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

| Trường | Nguồn | Ghi chú |
|---|---|---|
| `name`, `asset_code`, `asset_name` | `AC Asset` | định danh cốt lõi |
| `device_model_name` | `IMM Device Model.model_name` (1 `get_value` qua FK `device_model`) | "" nếu chưa gán model |
| `location_name` | `AC Location.location_name` (1 `get_value` qua FK `location`) | "" nếu chưa gán vị trí |
| `lifecycle_status` | `AC Asset.lifecycle_status` (mã EN canonical) | để FE chọn class pill; **KHÔNG hiển thị thô** |
| `lifecycle_status_label` | **SSoT VI** `services/shared/labels.py::LIFECYCLE_STATUS_LABEL_VI` (xem 04 §III.1c-6) | nhãn hiển thị VI, fallback = mã gốc nếu thiếu key |
| `last_maintenance` | **1 truy vấn** `Asset Lifecycle Event` filter `asset=name`, `event_type IN (pm_completed, repair_completed, calibration_passed)`, `ORDER BY timestamp DESC LIMIT 1` | `null` nếu chưa có sự kiện bảo trì nào (KHÔNG load toàn timeline — chống N+1) |
| `last_maintenance.event_type` | mã enum thô (vd `pm_completed`) | |
| `last_maintenance.event_type_label` | SSoT VI `LIFECYCLE_EVENT_LABEL_VI` | nhãn loại sự kiện tiếng Việt |
| `last_maintenance.date` | `timestamp` của event (format `YYYY-MM-DD`) | ngày bảo trì gần nhất |
| `next_pm_date` | `AC Asset.next_pm_date` (denormalized field — KHÔNG truy PM Schedule) | `null` nếu không có |
| `pm_overdue` | **DERIVE SERVER-SIDE** (BR-00-36): `True` ⟺ `next_pm_date` không rỗng ∧ `getdate(next_pm_date) < getdate(nowdate())` ∧ `lifecycle_status ∉ {Out of Service, Decommissioned}` | `bool` — SSoT quá-hạn ở BE (timezone-safe). NULL/hôm-nay/tương-lai/ngừng-dùng → `false`. FE CHỈ render cờ, KHÔNG so ngày bằng client clock. Xem 04 §II.1.8c-PMOVERDUE. |
| `next_calibration_date` | `AC Asset.next_calibration_date` (denormalized field đã có — KHÔNG truy Calibration Schedule) | `null` nếu không có (Vòng 28 B / BR-00-37) |
| `calibration_overdue` | **DERIVE SERVER-SIDE** (BR-00-37): `True` ⟺ `next_calibration_date` không rỗng ∧ `getdate(next_calibration_date) < getdate(nowdate())` ∧ `lifecycle_status ∉ {Out of Service, Decommissioned}` | `bool` — SSoT quá-hạn hiệu chuẩn ở BE (timezone-safe). NULL/hôm-nay/tương-lai/ngừng-dùng → `false`. FE CHỈ render cờ, KHÔNG so ngày bằng client clock. Xem 04 §II.1.8e-CALOVERDUE. |

**KHÔNG trả (field nhạy cảm — A6 acceptance):** `gross_purchase_amount`, `current_book_value`, `accumulated_depreciation`, `depreciation_schedule`, audit hash chain, `supplier` / internal supplier code, `byt_reg_no` chi tiết. Payload là **whitelist tường minh** (chỉ build các field liệt kê ở trên — KHÔNG `frappe.get_doc().as_dict()` rồi pop).

| Trường hợp | Mã | Ghi chú |
|---|---|---|
| token/name hợp lệ + có quyền | 200 | payload mobile cốt lõi ở trên |
| token/name KHÔNG tồn tại / rỗng / sai định dạng | **404** `AC-E001` | KHÔNG 500, KHÔNG phân biệt sai-định-dạng vs không-tồn-tại — leak-safe |
| User KHÔNG có `asset.read` | **403** PermissionError | `rbac.require("asset.read")` (gate TRƯỚC mọi DB read) |
| Vendor user, asset NGOÀI scope | **403** (`ErrorCode.FORBIDDEN`) | `assert_vendor_can_access("AC Asset", name)` sau khi resolve được name |

**Thứ tự gate (BẮT BUỘC):** `rbac.require("asset.read")` → resolve name (token|name) → `name` rỗng/không khớp → 404 → `assert_vendor_can_access("AC Asset", name)` (403 IDOR) → build payload. Gate cap chạy TRƯỚC resolve để guest không phân biệt được token tồn tại hay không.

**Audit (CHỐT A6 — đồng nhất quyết định A2/D4):** `get_asset_scan_info` là **READ-ONLY** → **KHÔNG emit lifecycle event, KHÔNG ghi IMM Audit Trail** (mỗi lần quét QR KHÔNG được sinh record — chống spam audit chain). KHÔNG gọi `ensure_asset_qr_token` (không sinh token ở luồng đọc; token đã có từ A1/backfill D5).

**KHÔNG N+1:** tối đa 4 `get_value`/`get_all` cố định bất kể dữ liệu: (1) resolve name, (2) AC Asset row đa-field, (3) device_model→model_name + location→location_name (2 get_value), (4) 1 `get_all` ALE `LIMIT 1`. KHÔNG loop, KHÔNG load timeline.

---

### `get_asset_label_data` — Dữ liệu in nhãn QR theo 1 asset (ADR-001 A3 / D3)

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.get_asset_label_data` |
| Auth | **AUTH-REQUIRED** (`@frappe.whitelist()`, KHÔNG `allow_guest`) — NĐ98 |
| Capability | **`asset.print`** (gate `rbac.require("asset.print")` đầu hàm) — **D6 (EXECUTED Vòng 3) đổi từ `asset.write`**: in nhãn = quyền PRINT (DocPerm print=1 sẵn cho persona vận hành), KHÔNG còn `asset.write` (chỉ Super Admin). `asset.print`→(AC Asset,"print"). `CAP_SET_VERSION` = `v97.c30c69b8974d`. |

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

| Trường hợp | Mã | Ghi chú |
|---|---|---|
| Asset hợp lệ + có quyền | 200 | trả payload tem (qr_url tuyệt đối, không rỗng) |
| Asset KHÔNG tồn tại | **404** `AC-E001` | KHÔNG 500, message generic — leak-safe, KHÔNG đoán được id nội bộ |
| User KHÔNG có `asset.print` (Guest / role không-print) | **403** PermissionError | `require("asset.print")` — KHÔNG quyền in (least-privilege D6) |
| User có `asset.print` (print=1 — KTV/QL vật tư/Super Admin) | tiếp tục (200 nếu hợp lệ) | gate PRINT pass |
| Vendor user, asset NGOÀI scope | **403** (`ErrorCode.FORBIDDEN`) | `assert_vendor_can_access("AC Asset", name)` — IDOR guard GIỮ NGUYÊN, KHÔNG trả data |

**Audit (CHỐT A3 — D3):** `get_asset_label_data` là **READ-ONLY về sự kiện in** → **KHÔNG emit `label_printed`, KHÔNG ghi IMM Audit Trail** (preview nhãn ≠ in nhãn; tránh spam audit chain — KTV mở màn in nhiều lần). Ngoại lệ DUY NHẤT: nếu asset chưa có token, `ensure_asset_qr_token` emit `qr_generated` 1 lần (sự kiện sinh-token A1, không phải print event). Sự kiện in chỉ ghi ở `mark_label_printed`.

---

### `get_asset_label_data_batch` — Dữ liệu in nhãn QR hàng loạt (ADR-001 A3 / D3)

| Method | GET |
|---|---|
| Path | `assetcore.api.imm00.get_asset_label_data_batch` |
| Auth | **AUTH-REQUIRED** — NĐ98 |
| Capability | **`asset.print`** (gate `rbac.require("asset.print")` đầu hàm) — **D6 (EXECUTED Vòng 3) đổi từ `asset.write`** (least-privilege; in hàng loạt = quyền PRINT). `CAP_SET_VERSION` = `v97.c30c69b8974d`. User KHÔNG print → **403**. |

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

**Thứ tự gate (BẮT BUỘC — KHÔNG đổi precedent):** `rbac.require("asset.print")` (403 nếu KHÔNG print) → **CAP-CHECK `len(names) > _MAX_LABEL_BATCH` → 413** → vòng `frappe.db.exists` + `assert_vendor_can_access` mỗi asset (403 IDOR; entry `AC-E001` cho missing tại đúng index) → `build_asset_label_data_batch`. 2 endpoint nhãn batch KHÔNG có `@rate_limit` (BR-00-29 mục 6); nếu vòng sau thêm thì 429 đứng TRƯỚC `rbac.require` (NGOÀI thân hàm).

**Audit:** Như `get_asset_label_data` — READ-ONLY về sự kiện in, KHÔNG emit `label_printed`/audit (chỉ token-backfill emit `qr_generated` nếu cần).

---

### `mark_label_printed` — Ghi sự kiện in nhãn QR (ADR-001 A3 / D3)

| Method | POST |
|---|---|
| Path | `assetcore.api.imm00.mark_label_printed` |
| Auth | **AUTH-REQUIRED** — NĐ98 |
| Capability | **`asset.print`** (gate `rbac.require("asset.print")` đầu hàm) — **D6 (EXECUTED Vòng 3) đổi từ `asset.write`**: ghi `label_printed`+audit là HỆ QUẢ của hành-động-IN ⇒ gate đúng quyền PRINT (DocPerm print=1 sẵn cho persona vận hành). `CAP_SET_VERSION` = `v97.c30c69b8974d` (cap mới `asset.print`/`asset.qr.rotate`). |

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

**Thứ tự gate (BẮT BUỘC — CHỐT vòng 22 / BR-00-33):** `rbac.require("asset.print")` (403 nếu KHÔNG print) → **CAP-CHECK `len(names) > _MAX_LABEL_BATCH` → 413** (hằng SSoT `services/imm00.py::_MAX_LABEL_BATCH = 200`, KHÔNG literal lặp) → validate tồn tại MỌI asset (404 nếu ≥1 thiếu) → `assert_vendor_can_access` MỖI asset (403 IDOR) → ghi event. Gate PRINT chạy ĐẦU TIÊN → user không-print KHÔNG dò được asset nào tồn tại; cap-check chạy SAU PRINT → KHÔNG lộ ngưỡng cho khách. `mark_label_printed` ghi 2 record/asset trong 1 transaction → cap chặn khuếch đại write/audit-chain (payload-DoS, KHÁC rate-limit BR-00-29).

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
| Permission | IMM Department Head / Operations Manager (validated bởi service layer) |

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

**Errors:** 404 (asset not found), 422 (invalid transition — BR-00-02), 422 (NEG-09: chặn thanh lý khi asset đang `Under Maintenance/Under Repair/Calibrating`).

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

GET `assetcore.api.imm00.list_locations` — Params: `parent` (optional). Trả flat list với fields: `name, location_name, location_code, parent_location, is_group, clinical_area_type, infection_control_level, power_backup_available, dept_head, contact_phone, notes` (+ enrich `dept_head_name` từ User.full_name).

> **Đổi schema (2026-05-19):** 3 trường liên hệ cũ (`emergency_contact`, `dept_head`, `technical_contact`) được gộp còn 2: `dept_head` (Link → User, label "Người phụ trách") + `contact_phone` (Data, `fetch_from: dept_head.phone`, label "Số liên hệ"). Migrate qua patch `v3_1.007_ac_location_simplify_contacts`. Xem README §Changelog.

### `get_location`

GET `assetcore.api.imm00.get_location?name=...`

### `create_location`

POST. Body: `location_name` (required) + optional fields.

### `update_location`

POST. Body: `{ "name": "...", ...fields }`

### `delete_location`

POST. Body: `{ "name": "..." }` — block nếu có asset đang link.

### `list_departments`

GET `assetcore.api.imm00.list_departments` — Params: `parent` (optional).

### `get_department` / `create_department` / `update_department` / `delete_department`

Pattern tương tự locations.

### `list_asset_categories`

GET `assetcore.api.imm00.list_asset_categories` — Flat list. Fields: `name, category_name, gmdn_code, description, default_pm_required, default_pm_interval_days, default_calibration_required, default_calibration_interval_days, default_depreciation_method, total_depreciation_months, depreciation_frequency, default_residual_value_pct, has_radiation, is_active`.

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

### `get_transfer_full` / `update_transfer`

GET chi tiết + POST update (chỉ khi Pending Approval).

---

## III.13. Service Contract (5 endpoints)

`list_service_contracts`, `get_service_contract`, `create_service_contract`, `update_service_contract`, `delete_service_contract` + `list_asset_contracts` (GET contracts của 1 asset).

---

## III.14. PM Schedule (5 endpoints)

`list_pm_schedules`, `get_pm_schedule`, `create_pm_schedule`, `update_pm_schedule`, `delete_pm_schedule`. Served bởi `assetcore.api.imm00`.

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
