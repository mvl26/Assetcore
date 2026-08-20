# 05 — API Specification

| Mục | Giá trị |
|---|---|
| Module | IMM-`<XX>` |
| Phạm vi | Per-module |
| Owner | BE Lead |
| Base URL | `/api/method/assetcore.api.imm<XX>.<function>` |
| Auth | Frappe session HOẶC `Authorization: token <key>:<secret>` |

> **Mục đích**: Hợp đồng API giữa BE và FE/đối tác. Mọi endpoint @whitelist của module ở đây với schema + error + ví dụ. Drift = bug doc. **Bắt buộc**: tài liệu API phải đủ — FE không cần đọc code BE để biết shape data.

---

## 0. API Catalog — bảng tổng hợp toàn bộ endpoint của module

**Viết gì**: Bảng tổng hợp **MỌI endpoint** của module ở 1 chỗ duy nhất. Đặt đầu file để FE / đối tác scan nhanh. Cột:

| # | Endpoint | Method | Mô tả ngắn | Role | Idempotent | Type request | Type response | Liên kết US |
|---|---|---|---|---|---|---|---|---|
| 1 | `assetcore.api.imm<XX>.create_<entity>` | POST | Tạo `<entity>` mới | Technician | ✗ | `Create<Entity>Request` | `<Entity>` | US-01 |
| 2 | `assetcore.api.imm<XX>.update_<entity>` | POST | Cập nhật `<entity>` | Technician (own) | ✓ | `Update<Entity>Request` | `<Entity>` | US-02 |
| 3 | `assetcore.api.imm<XX>.list_<entity>` | POST | List có filter + pagination | Technician+ | ✓ | `List<Entity>Request` | `Paginated<Entity>` | US-03 |
| 4 | `assetcore.api.imm<XX>.get_<entity>` | POST | Lấy chi tiết 1 `<entity>` | Technician+ | ✓ | `{name: string}` | `<Entity>Detail` | US-04 |
| 5 | `assetcore.api.imm<XX>.<workflow_action>` | POST | Workflow transition | per role | ✗ | `<Action>Request` | `<Entity>` | US-05 |
| 6 | `assetcore.api.imm<XX>.dashboard_summary` | POST | KPI dashboard | Supervisor+ | ✓ | `{period?: string}` | `DashboardSummary` | US-06 |

**Mẹo**:
- Cột "Type" = tên TypeScript interface — phải tồn tại trong `frontend/src/types/imm<XX>.ts`.
- Catalog cập nhật **mỗi khi thêm/đổi/bỏ endpoint** — nếu lệch với `assetcore/api/imm<XX>.py`, CI fail (best-effort grep check).

---

## 1. Quy ước chung
**Viết gì**: Mục con cho:
- **Endpoint pattern + headers** (POST `/api/method/...` + Content-Type + CSRF)
- **Response success format** (xem §1.1 — envelope `{success, data}`)
- **Response lỗi format** (xem §1.2 — envelope `{success, error, code, fields?}`)
- **Error code** (xem §1.3 — actual values trong `services/shared/constants.py:ErrorCode`)
- **Mapping FE/BE error code** (xem §1.4)
- **Type definitions** (xem §1.5 — folder `frontend/src/types/`)
- **Pagination** (page/page_size, mặc định `page=1 page_size=20`, response có `total + total_pages`)
- **Datetime format** (ISO 8601 input + output UTC)

### 1.1. Response success — format chuẩn AssetCore

AssetCore dùng **envelope custom** thay vì Frappe `message` default — wrap qua helper `_ok(data)` trong `assetcore/api/imm<XX>.py`:

```jsonc
{
  "success": true,
  "data": <payload tùy endpoint, có thể là object / array / null>
}
```

FE đọc qua `response.data.data` (axios + Frappe lớp ngoài đã wrap thêm `message`, helper FE tự strip).

**HTTP status**: Frappe luôn trả **HTTP 200** khi service không raise exception ngoài kiểm soát. Phân biệt success/error qua field `success` trong body, KHÔNG qua HTTP code. Trường hợp HTTP ≠ 200 chỉ xảy ra khi:
- 401 → session hết hạn (Frappe interceptor)
- 403 → CSRF fail / role-level guard Frappe
- 500 → unhandled exception (BE phải catch + log + trả `_err` thay vì raise)

### 1.2. Response error — format chuẩn (BẮT BUỘC)

CẤM trả raw traceback / stacktrace / SQL error / file path. Service raise `ServiceError(code, message)` → API helper `_handle()` bắt và trả qua `_err(message, code)`:

```jsonc
{
  "success": false,
  "error": "Thiết bị đã ngưng sử dụng.",   // tiếng Việt cho FE hiển thị
  "code": "BAD_STATE",                       // identifier từ ErrorCode enum
  "fields": {                                 // (optional) field-level errors cho inline
    "asset": "Thiết bị đã ngưng sử dụng"
  }
}
```

**Pattern code BE**:

```python
# assetcore/services/imm<XX>.py
from assetcore.services.shared.constants import ErrorCode
from assetcore.services.shared.errors import ServiceError

def create_repair(asset_name: str, priority: str) -> dict:
    asset = RepairRepo.get_asset(asset_name)
    if not asset:
        raise ServiceError(ErrorCode.NOT_FOUND, "Không tìm thấy thiết bị")
    if asset.status == "Decommissioned":
        raise ServiceError(ErrorCode.BAD_STATE, "Thiết bị đã ngưng sử dụng")
    # ...

# assetcore/api/imm<XX>.py
@frappe.whitelist(methods=["POST"])
def create_repair(asset: str, priority: str = "Normal") -> dict:
    return _handle(service.create_repair, asset, priority)
```

### 1.3. Error code catalog — actual values (BE)

Định nghĩa trong `assetcore/services/shared/constants.py:ErrorCode`. Đây là **string identifier thuần, KHÔNG prefix**:

| Code | HTTP gợi ý | Khi nào |
|---|---|---|
| `NOT_FOUND` | 404 | Resource không tồn tại |
| `FORBIDDEN` | 403 | Không có quyền (role / User Permission) |
| `UNAUTHORIZED` | 401 | Chưa đăng nhập / session expired |
| `VALIDATION` | 400 | Input validation fail (format, type, length) |
| `BUSINESS_RULE` | 422 | Vi phạm rule nghiệp vụ |
| `CONFLICT` | 409 | Concurrent modify / unique constraint violate |
| `BAD_STATE` | 422 | State machine fail (vd asset decommissioned) |
| `DUPLICATE` | 409 | Đã tồn tại (idempotent / duplicate detection) |
| `INVALID_PARAMS` | 400 | Param malformed (vd JSON parse fail) |
| `RATE_LIMITED` | 429 | Quá ngưỡng request |
| `INTERNAL` | 500 | Lỗi hệ thống unexpected |

> HTTP code chỉ là **gợi ý** — Frappe wrap response và **luôn trả 200** khi service raise `ServiceError` (vì service catch + return `_err`). FE quyết định theo field `code` trong body.

### 1.4. Mapping FE ↔ BE error code (CRITICAL)

FE dùng tên dài hơn để rõ nghĩa, đã có **map sẵn** trong `frontend/src/api/errors.ts`:

| BE (`ErrorCode`) | FE (`ErrorCode`) |
|---|---|
| `VALIDATION` | `VALIDATION_ERROR` |
| `BUSINESS_RULE` | `BUSINESS_RULE_VIOLATION` |
| `NOT_FOUND` | `NOT_FOUND` |
| `FORBIDDEN` | `FORBIDDEN` |
| `UNAUTHORIZED` | `UNAUTHORIZED` |
| `CONFLICT` | `CONFLICT` |
| `BAD_STATE` | `BAD_STATE` |
| `DUPLICATE` | `DUPLICATE` |
| `INVALID_PARAMS` | `INVALID_PARAMS` |
| `RATE_LIMITED` | `RATE_LIMITED` |
| `INTERNAL` | `INTERNAL_ERROR` |
| (HTTP 5xx unmapped) | `NETWORK_ERROR` / `UNKNOWN` |

Khi thêm code mới: bắt buộc cập nhật **cả 2 đầu** + bảng mapping này. Sai lệch = `httpStatusToCode()` fallback sai.

FE classify error tier qua property `ApiError.isBusinessError` / `isSystemError`:
- **Business error** (`VALIDATION_ERROR`, `BUSINESS_RULE_VIOLATION`, `CONFLICT`) → toast warning vàng + inline `fields`
- **Permission error** (`FORBIDDEN`, `UNAUTHORIZED`) → toast warning + redirect login nếu 401
- **System error** (`INTERNAL_ERROR`, `NETWORK_ERROR`, `UNKNOWN`) → toast error đỏ + log Sentry

### 1.5. Type definitions (BẮT BUỘC chuẩn hóa 2 đầu)

FE đã có folder `frontend/src/types/` với 1 file/module: `auth.ts`, `common.ts`, `imm00.ts` … `imm09.ts`, `inventory.ts`. Mỗi endpoint phải có TS interface tương ứng cho Request + Response.

**Pattern actual**:

```ts
// frontend/src/types/imm<XX>.ts
export type RepairStatus =
  | 'Open' | 'Assigned' | 'Diagnosing'
  | 'Repairing' | 'Completed' | 'Pending Approval'
  | 'Closed' | 'Cancelled';

export interface AssetRepair {
  name: string;
  asset_ref: string;          // snake_case khớp BE field
  asset_label: string;        // denormalized cho display
  priority: 'Normal' | 'Urgent' | 'Emergency';
  workflow_state: RepairStatus;
  sla_due_at: string;          // ISO 8601 UTC
  // ...
}

// Pagination response chuẩn — khớp với pagination.py BE
export interface Paginated<T> {
  data: T[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  offset?: number;
}
```

`common.ts` chứa shared types: `Paginated<T>`, `ApiError`, `ApiResponse<T>`. Module-specific types ở file riêng.

BE mirror trong `assetcore/services/shared/dto.py` (TypedDict / dataclass). Sai lệch = bug — review PR check 2 đầu khớp.

## 2. Endpoint
**Viết gì**: Mỗi endpoint 1 sub-section dùng template §99.
**Mẹo**: Mọi service public function (04 §4) phải có 1 endpoint ở đây.

## 3. List / Query endpoints
**Viết gì**: Quy ước —
- List đơn giản dùng `frappe.client.get_list` (FE gọi thẳng)
- List có business filter viết endpoint riêng `list_<gì>`
- Trả thêm field denormalized (vd `asset_label`, `assignee_full_name`) để FE không phải gọi extra

### 3.1. Free-text `search` filter — CONVENTION (BẮT BUỘC)

**Sự cố tham chiếu (2026-05-20)**: `/needs-requests` lỗi
`(1054, "Unknown column 'tabIMM Needs Request.search' in 'WHERE'")` khi
người dùng gõ mã NR vào ô tìm kiếm. Nguyên nhân: FE đẩy `search` vào dict
`filters`, BE pass thẳng vào `frappe.get_list` → MariaDB tưởng `search`
là cột. Để tránh lặp lại:

**Hợp đồng BE/FE**:

- FE list view luôn gửi free-text search trong **cùng** dict `filters` —
  key cố định là `"search"` (không đổi tên thành `q`, `query`, `keyword`
  trừ khi mọi 2 đầu cùng đổi). Lý do: đồng nhất với pattern
  `NeedsRequestListView.vue:71`, dùng lại được component `ListFilterBar`.
- BE list endpoint **bắt buộc** dùng helper
  `assetcore.services.shared.filters.pop_search()` để tách `search` khỏi
  `filters` trước khi pass vào `frappe.get_list`. KHÔNG được pass dict
  filter thô.
- Mỗi list endpoint phải khai báo `searchable_fields` — danh sách 2-4
  field hợp lý để OR-LIKE (luôn gồm `name` + 1-2 field định danh nghiệp
  vụ, vd `device_model_ref`, `plan_period`, `supplier`). Liệt kê field
  trong API spec.
- Pagination phải dùng `count_with_or(doctype, filters, or_filters)`
  (cùng module) thay vì `frappe.db.count` — nếu không `total` sẽ lệch
  với số rows thực sự match OR-clause.

**Skeleton BE** (copy + sửa):

```python
from assetcore.services.shared.filters import pop_search, count_with_or

_DT = "IMM <Entity>"
_SEARCHABLE_FIELDS = ["name", "<biz_field_1>", "<biz_field_2>"]
# Khi placeholder hứa tìm theo TÊN của 1 Link field (vd "tên model"),
# parent chỉ lưu link ID → resolve qua display_field của doctype liên kết.
_LINK_SEARCH = {
    # "<link_field_on_parent>": ("<Linked DocType>", "<display_field>"),
    "device_model_ref": ("IMM Device Model", "model_name"),
}

@frappe.whitelist()
def list_<entity>(filters: str = "{}", page: int = 1, page_size: int = 20) -> dict:
    f = _parse_json(filters)
    f, or_filters = pop_search(f, _SEARCHABLE_FIELDS, link_search=_LINK_SEARCH)
    start = (max(1, int(page)) - 1) * int(page_size)
    items = frappe.get_list(
        _DT, filters=f or None, or_filters=or_filters,
        fields=[...], order_by="...", start=start, page_length=int(page_size),
    )
    total = count_with_or(_DT, f or None, or_filters)
    return _ok({"items": items, "total": total, "page": page, "page_size": page_size})
```

#### 3.1.a. Khi nào dùng `link_search`?

Trục quyết định = placeholder FE nói gì:

| Placeholder hứa | Cách viết | Lý do |
|---|---|---|
| "mã model" / "mã NCC" / "mã hồ sơ" | `searchable_fields=["device_model_ref"]` (LIKE thẳng trên link ID) | Field trên parent đã chứa giá trị user gõ |
| "tên model" / "tên NCC" / "tên thiết bị" | `link_search={"device_model_ref": ("IMM Device Model", "model_name")}` | Tên hiển thị KHÔNG có trên parent — phải resolve qua doctype liên kết |
| Cả mã và tên | gom cả 2 — direct LIKE trên link ID + link_search → user gõ kiểu nào cũng ra | Convenience cho power user |

**Cảnh báo perf**: `link_search` thực hiện 1 round-trip lookup trên doctype
liên kết, giới hạn 500 match (`_LINK_LOOKUP_LIMIT` trong `filters.py`).
Nếu doctype liên kết > 100k rows → cân nhắc denormalize display field
vào parent (vd thêm `device_model_name` trên IMM Needs Request) thay vì
dựa vào link_search.

**Smoke test bắt buộc** mỗi list endpoint mới:

```bash
curl -X GET '<base>/list_<entity>?filters=%7B%22search%22%3A%22XYZ%22%7D' \
  -H 'Authorization: token <key>:<secret>'
# Phải trả {success: true, data: {items: [...], total: N, ...}} — không SQL error.
```

Test regression chung: `assetcore/tests/integration/test_list_search_filter.py`.

**Đồng bộ FE placeholder (BẮT BUỘC)**: Khi khai báo `searchable_fields` hoặc
thay đổi nó, **đồng thời** sửa `search-placeholder` của list view tương ứng
để liệt kê đúng các nhãn business của field đó. Xem file 06 §3.c.i. Lý do:
placeholder hứa "Tìm theo X" nhưng BE không có X = bug UX (user mất niềm tin
khi gõ X không ra kết quả). Quy ước này phát sinh từ sự cố 2026-05-20 trên
`/needs-requests`.

## 4. Webhook / Event (nếu có)
**Viết gì**: Bảng `Event · Trigger · Payload · Receiver`. Chỉ khi module phát event ngoài.

## 5. Versioning
**Viết gì**: API hiện tại = v1 (không prefix). Breaking change → suffix `_v2` + deprecate v1 1 release. Bảng deprecated.

## 6. Rate limit
**Viết gì**: Bảng `Endpoint · Limit · Lý do`. Ví dụ: create endpoint 60/min/user, list endpoint 600/min/user.

## 7. Smoke test playbook
**Viết gì**: 3-5 lệnh curl sau deploy verify endpoint chính chạy.

---

## 99. Template per endpoint (copy + sửa)

```markdown
### N. <function_name> — <Mô tả>

| Mục | Giá trị |
|---|---|
| Method | POST (mutation) / GET (read thuần) |
| Path | /api/method/assetcore.api.imm<XX>.<function> |
| Role | <vd: IMM-XX Technician hoặc Supervisor> |
| Idempotent | Yes / No |
| Type Request | <Tên TS interface — định nghĩa trong frontend/src/types/imm<XX>.ts> |
| Type Response | <Tên TS interface — như trên> |
| Liên kết US | US-<NN> |

**Request**:
\`\`\`jsonc
{
  "field1": "string",     // type, required, validation
  "field2": "enum"        // {Normal | Urgent | Emergency}, default Normal
}
\`\`\`

| Trường | Type | Required | Validation |
|---|---|---|---|
| `field1` | string | ✓ | <rule> |
| `field2` | enum | ✗ | one of {...} |

**Response success** (HTTP 200, envelope `_ok`):
\`\`\`jsonc
{
  "success": true,
  "data": {
    "name": "WO-CM-2026-00128",
    "workflow_state": "Open",
    "sla_due_at": "2026-05-07T16:32:00Z"
  }
}
\`\`\`

**Response error** (HTTP 200 với `success=false`, envelope `_err`):
\`\`\`jsonc
{
  "success": false,
  "error": "<message tiếng Việt>",
  "code": "<ErrorCode>",
  "fields": { "<field_name>": "<msg cho inline error>" }   // optional
}
\`\`\`

**Errors có thể**:
| Code (BE) | Code (FE map) | Khi nào |
|---|---|---|
| `VALIDATION` | `VALIDATION_ERROR` | <input invalid> |
| `BAD_STATE` | `BAD_STATE` | <state machine fail> |
| `BUSINESS_RULE` | `BUSINESS_RULE_VIOLATION` | <rule nghiệp vụ> |
| `FORBIDDEN` | `FORBIDDEN` | <không quyền> |
| `NOT_FOUND` | `NOT_FOUND` | <resource không tồn tại> |

**Side effects**:
- <record sinh / state change / notify / lifecycle event>

**Curl ví dụ**:
\`\`\`bash
curl -X POST '<base>/<function>' \\
  -H 'Authorization: token <key>:<secret>' \\
  -H 'Content-Type: application/json' \\
  -d '{"field1":"...","field2":"..."}'
\`\`\`
```

---

## DoD — File 05 hoàn chỉnh

- [ ] **API Catalog (§0)** liệt kê 100% endpoint module — đối chiếu file `assetcore/api/imm<XX>.py`
- [ ] Mọi service public function (04 §4) có 1 endpoint trong catalog
- [ ] **Type definitions (§1.4)** đầy đủ trong `frontend/src/types/imm<XX>.ts` — request + response + error
- [ ] BE DTO (dataclass / TypedDict) mirror với FE types
- [ ] Mỗi endpoint có request schema (field + type + required + validation)
- [ ] Mỗi endpoint có response schema + ví dụ JSON
- [ ] **Error response chuẩn** (§1.2) — không raw text, có `_error_code` + `message` tiếng Việt + `field` nếu inline
- [ ] **HTTP code chuẩn** (§1.2) — 200/204/400/401/403/404/409/417/422/500
- [ ] Error codes liệt kê đủ (đối chiếu 02 §IV.5 + ErrorCode enum)
- [ ] Side effects nêu rõ (record sinh, state change, notify)
- [ ] ≥ 1 curl ví dụ chạy được mỗi endpoint chính
- [ ] Pagination + datetime convention nhất quán
- [ ] **List endpoint có free-text search** (§3.1) — dùng `pop_search` + `count_with_or`, khai báo `searchable_fields`, không pass `filters` thô vào `frappe.get_list`
- [ ] Webhook (nếu có) có payload schema
- [ ] Reviewed bởi BE Lead + FE Lead
