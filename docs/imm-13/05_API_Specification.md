# 05 — API Specification (IMM-13)

| Mục | Giá trị |
|---|---|
| Module | IMM-13 — Ngừng sử dụng và điều chuyển |
| Trạng thái | **Skeleton** — endpoint name + verb + mô tả; request/response shape chốt khi BE scaffold (Sprint Wave 3) |
| Liên kết | [04 Backend](./04_Backend_Design.md) · [`CONVENTIONS.md §3`](../../.claude/skills/CONVENTIONS.md) |

---

## §0 — Response Envelope chuẩn

Tuân thủ `CONVENTIONS.md §3`. Mọi endpoint trả 1 trong 2 envelope:

**Success:**
```json
{ "success": true, "data": { ... } }
```

**Error:**
```json
{ "success": false, "error": "<message tiếng Việt>", "code": "IMM13_<ENUM>" }
```

ErrorCode chính thức theo `assetcore/services/shared/constants.py:ErrorCode`. Namespace IMM-13 sẽ thêm trong Sprint Wave 3 (xem [02 §IV.5](./02_Analysis_Design.md#iv5-edge-cases--errors)).

---

## §1 — Endpoint catalog

| # | Method | Path (Frappe whitelist) | Auth | Mô tả ngắn | UC ref |
|---|---|---|---|---|---|
| 1 | POST | `assetcore.api.imm13.create_stand_down_request` | session + role `IMM HTM Engineer` | Khởi tạo đề xuất stand-down | UC-01 |
| 2 | POST | `assetcore.api.imm13.create_reassignment` | session + role `IMM HTM Engineer` | Khởi tạo đề xuất điều chuyển | UC-02 |
| 3 | POST | `assetcore.api.imm13.confirm_reassignment` | session + role `IMM Department Head` | Trưởng khoa xác nhận (source/target) | UC-02 |
| 4 | POST | `assetcore.api.imm13.approve_reassignment` | session + role `IMM Operations Manager` | PTP Khối 2 duyệt; trigger commit | UC-02 |
| 5 | POST | `assetcore.api.imm13.reject_reassignment` | session + role manager/dept | Từ chối + lý do | UC-02 |
| 6 | POST | `assetcore.api.imm13.create_replacement_review` | session + role `IMM HTM Engineer` | Tạo bảng cost vs risk | UC-03 |
| 7 | PUT | `assetcore.api.imm13.fill_replacement_cost` | session + role `IMM Finance Officer` | TCKT điền cost | UC-03 |
| 8 | POST | `assetcore.api.imm13.submit_residual_risk` | session + role `IMM QA Officer` | QMS Officer ký residual risk | UC-04 |
| 9 | POST | `assetcore.api.imm13.approve_retire_proposal` | session + role `IMM Operations Manager` | Duyệt retire + emit event sang IMM-14 | UC-05 |
| 10 | GET | `assetcore.api.imm13.list_reassignments` | session | List có filter (state/asset/facility/date) | – |
| 11 | GET | `assetcore.api.imm13.list_replacement_reviews` | session | List có filter | – |
| 12 | GET | `assetcore.api.imm13.get_reassignment_detail` | session | Detail 1 đề xuất + chuỗi e-sign | UC-09 |
| 13 | GET | `assetcore.api.imm13.get_audit_chain` | session + role `IMM Auditor` | Audit hash chain 1 hồ sơ | UC-09 |
| 14 | GET | `assetcore.api.imm13.dashboard_metrics` | session + role manager/auditor | KPI metrics module | – |

*(Đếm endpoint dự kiến: 14. Có thể giảm/tăng khi scaffold thực tế — số chính thức cập nhật vào file này khi sprint 3 xong.)*

---

## §2 — Endpoint detail (skeleton)

Mỗi endpoint dưới đây có **request/response shape sẽ chốt ở Sprint Wave 3** *(sau khi BE scaffold)*. Hiện tại liệt kê **input bắt buộc tối thiểu** + **output kỳ vọng** để FE có thể bắt đầu mock.

### 1. POST `create_stand_down_request`

- **Input bắt buộc**: `asset` (str), `reason` (str — bắt buộc), `evidence_files` (list[str], optional).
- **Output**: `{ "name": "<RAS-...>", "state": "Pending Dept Confirm Source" }`.
- **Errors**: `IMM13_REASON_REQUIRED`, `IMM13_ASSET_BUSY_PM`, `IMM13_ASSET_BUSY_REPAIR`, `IMM13_ASSET_HAS_CLINICAL_BOOKING`.

### 2. POST `create_reassignment`

- **Input**: `asset`, `target_facility`, `target_department`, `target_room`, `target_location`, `reason`.
- **Output**: `{ "name": "<RAS-...>", "state": "Pending Dept Confirm Source", "needs_recommissioning": bool }`.
- **Errors**: `IMM13_COMPETENCY_GAP`, `IMM13_INVALID_TARGET_LOCATION`, `IMM13_CONCURRENT_UPDATE`.

### 3. POST `confirm_reassignment`

- **Input**: `name`, `role` (∈ {`source`, `target`}), `note` (optional).
- **Output**: `{ "name", "state": "Pending Dept Confirm Target" | "Pending Approval" }`.

### 4. POST `approve_reassignment`

- **Input**: `name`, `signature_password` (re-auth), `note` (optional).
- **Output**: `{ "name", "state": "Approved", "asset_location_updated": true, "lifecycle_event": "<LE-...>" }`.
- **Errors**: `IMM13_ESIGN_INVALID`, `IMM13_HANDOFF_IMM14_FAIL` (nếu là retire pass-through).

### 5. POST `reject_reassignment`
- **Input**: `name`, `reason`. **Output**: state Rejected.

### 6. POST `create_replacement_review`
- **Input**: `asset`. **Output**: `{ "name": "<RPV-...>" }`.

### 7. PUT `fill_replacement_cost`
- **Input**: `name`, `residual_value`, `replacement_cost`, `cost_items[]`. **Output**: state `Pending Risk Assessment`.

### 8. POST `submit_residual_risk`
- **Input**: `review`, `items` (list ≥ 3, mỗi item có `risk`, `likelihood`, `impact`, `mitigation`), `signature_password`.
- **Output**: `{ "name": "<RSK-...>", "state": "Signed", "signature_hash": "<sha256>" }`.
- **Errors**: `IMM13_RISK_ITEMS_INSUFFICIENT`, `IMM13_MITIGATION_REQUIRED`, `IMM13_ESIGN_INVALID`.

### 9. POST `approve_retire_proposal`
- **Input**: `review`, `signature_password`.
- **Output**: `{ "review", "state": "Approved", "imm14_handoff_id": "<...>" }`.

### 10–14. List / Detail / Dashboard
- Standard list filters (`state`, `asset`, `facility`, `date_from`, `date_to`, pagination `limit`/`start`).
- Detail trả về object chính + bảng e-sign chain + Lifecycle Event liên quan.
- Dashboard trả về 5 KPI ở [02 §I.5](./02_Analysis_Design.md#i5-kpi-mục-tiêu).

*(Request/response shape chính thức — JSON schema — sinh khi BE scaffold.)*

---

## §3 — ErrorCode catalog (dự kiến namespace `IMM13_*`)

Theo `services/shared/constants.py:ErrorCode`. Các code dùng trong module:

| Code | HTTP-equivalent | Khi nào |
|---|---|---|
| `IMM13_REASON_REQUIRED` | 400 | Stand-down thiếu lý do |
| `IMM13_ASSET_BUSY_PM` | 409 | Asset đang Under Maintenance |
| `IMM13_ASSET_BUSY_REPAIR` | 409 | Asset đang Under Repair |
| `IMM13_ASSET_HAS_CLINICAL_BOOKING` | 409 | Có booking lâm sàng |
| `IMM13_COMPETENCY_GAP` | 422 | Khoa đích không có competency |
| `IMM13_INVALID_TARGET_LOCATION` | 400 | Target location không tồn tại / sai cơ sở |
| `IMM13_CONCURRENT_UPDATE` | 409 | Lock tranh chấp |
| `IMM13_TIMEOUT_DEPT_CONFIRM` | 408 | Trưởng khoa quá hạn 14 ngày |
| `IMM13_RISK_ITEMS_INSUFFICIENT` | 422 | < 3 risk item |
| `IMM13_MITIGATION_REQUIRED` | 422 | Mitigation rỗng |
| `IMM13_ESIGN_INVALID` | 401 | Re-auth thất bại |
| `IMM13_HANDOFF_IMM14_FAIL` | 502 | IMM-14 listener fail |
| `IMM13_REVIEW_COST_MISSING` | 422 | Replacement Review thiếu cost |
| `IMM13_REASSIGN_REJECTED` | 410 | Đã bị reject (auto cancel sau timeout) |

*(Code chính thức confirm khi commit `constants.py:ErrorCode` — Sprint Wave 3.)*

---

## §4 — Authentication & Authorization

- Authentication: Frappe session cookie + `X-Frappe-CSRF-Token`.
- Authorization: kiểm tra ở 3 lớp (`@frappe.whitelist(allow_guest=False)` → role check trong service → DocPerm check trong DocType controller).
- E-sign endpoint (4, 8, 9): bắt buộc re-auth password trong cùng request.
- Audit: mọi mutation gọi `log_audit_event` với hash chain SHA-256.

---

## §5 — Versioning & Backward compat

- Module IMM-13 release lần đầu ở **AssetCore v3.x** (Đợt 3).
- Endpoint phá vỡ tương thích phải bump version path → `assetcore.api.imm13_v2.*`.
- Skeleton hiện tại = `v1` (mặc định).

---

## §6 — Dependencies tới module khác

| Endpoint | Phụ thuộc | Loại |
|---|---|---|
| `create_stand_down_request` | `AC Asset` registry, `Lifecycle Event` | Read + Write |
| `approve_reassignment` (commit) | `AC Asset.location`, IMM-04 (re-commissioning) | Atomic write + optional trigger |
| `approve_retire_proposal` | IMM-14 listener | Emit event |
| `fill_replacement_cost` | ERPNext Asset (giá trị còn lại) | Read |

---

---

## §7 — Mobile Read Surface (Đợt-2) — **Asset Transfer (LIVE @ imm00)**

> ⚠️ **Phân-biệt namespace (quan trọng — chống nhầm):** §1–§6 ở trên đặc-tả luồng **Reassignment (RAS-...)** Đợt-3 *chưa scaffold* (`assetcore.api.imm13.*`). Tuy nhiên cơ-chế điều-chuyển **ĐANG LIVE** lại nằm ở **`assetcore.api.imm00.*`** trên DocType **`Asset Transfer`** (naming `AT-.YYYY.-.####`), KHÔNG phải `imm13.reassignment`. §7 này đặc-tả 2 endpoint **READ LIVE** đã wire vào **mobile contract** (`docs/mobile/openapi/assetcore-mobile.openapi.yaml`) — quyết định kiến-trúc: [`ADR-MOBILE-021`](../mobile/ADR-MOBILE-021.md).

**Boundaries (lens spec):**
- **Always:** trỏ path THẬT `assetcore.api.imm00.list_transfers`/`get_transfer` (LIVE @`api/imm00.py:2047-2085`); enum `status`/`transfer_type` lấy SSoT từ `asset_transfer.json` (KHÔNG bịa); read-only ⇒ KHÔNG sinh Lifecycle Event (event sinh ở mutation `approve`/`receive`).
- **Never:** gộp 2 endpoint này vào namespace `imm13.*` (path không tồn tại → 404 runtime); khai `listTransfers` 200 là `oneOf [Env, Error]` (handler KHÔNG `try/except` ⇒ 0 nhánh `_err`); khai `TransferDetail` closed (`as_dict()` mang field meta Frappe → validate-fail).

### §7.1 — DocType `Asset Transfer` (nguồn dữ liệu)

| Mục | Giá-trị (verify `asset_transfer.json`) |
|---|---|
| Naming | `AT-.YYYY.-.####` |
| `is_submittable` | 0 (KHÔNG docstatus-flow) · `track_changes` 1 |
| `status` (Select, read_only, default `Pending Approval`) | `Pending Approval` · `Approved` · `Rejected` · `Received` · `Cancelled` (`:89`) |
| `transfer_type` (Select) | `Internal` · `Loan` · `External` · `Return` (`:77`) |

### §7.2 — Endpoint READ (đã wire mobile)

| # | Method | Path (Frappe whitelist) | opId (mobile) | Auth | 200 shape | Slot |
|---|---|---|---|---|---|---|
| R1 | GET | `assetcore.api.imm00.list_transfers` | `listTransfers` | bare `@whitelist` (session) | **SINGLE** `TransferListEnvelope` | `{200,401,403}` |
| R2 | GET | `assetcore.api.imm00.get_transfer` | `getTransfer` | bare `@whitelist` (session) | **oneOf** `[TransferDetailEnvelope, Error]` | `{200,401,403}` |

**R1 `list_transfers`** (`api/imm00.py:2047-2077`)
- **Input** (4 param DISCRETE query-string): `asset?` (str — Link AC Asset) · `status?` (str — ∈ enum §7.1) · `page?` (int, default 1) · `page_size?` (int, default 20).
- **Output** `_ok({"pagination": <Pagination 5-key>, "items": [<TransferListItem>]})` — rows-key `data.items[]` (mirror IncidentListEnvelope). `order_by transfer_date desc`.
- **SINGLE-shape** (KHÔNG `oneOf Error`): handler KHÔNG `try/except` ⇒ 0 nhánh `_err` in-handler; malformed `page` → 500 NGOÀI 3-shape.
- **`TransferListItem`** closed (`additionalProperties:false`), `required [name]`, **17 field** GROUNDED `fields=[...]`@`:2062-2065` + `asset_name` enrich@`:2070-2076`: `name, asset, asset_name, transfer_date(date), transfer_type(enum), status(enum), from_location, to_location, from_department, to_department, from_custodian, to_custodian, reason, approved_by, approval_date(date), received_by, received_date(date)`. **0 boolean** → 0 int-enum trap.

**R2 `get_transfer`** (`api/imm00.py:2080-2085`)
- **Input**: `name` (str, query, **required**).
- **Output**: `404 _err(IMM transfer NOT_FOUND)` @`:2084` (Error trên **HTTP-200** quirk) **hoặc** `_ok(doc.as_dict())` @`:2085`.
- **oneOf** `[TransferDetailEnvelope, Error]` closed route-by-VALUE `body.success` (Decision-B 0-discriminator). `Error.http_status ⊇ {404}`.
- **`TransferDetail`** **OPEN** (`additionalProperties:true`) = `doc.as_dict()` — superset-by-property của `TransferListItem` + field detail-only (`naming_series, expected_return_date, notes, rejected_by, rejection_reason, handover_notes, amended_from`) + field meta Frappe qua `additionalProperties`. `required [name]`. (Envelope đóng; Detail mở — mirror `IncidentDetail` §3.2.)

### §7.3 — Slot 401/403 (DONE-gate spec-contract)

Cả 2 bare `@whitelist` (KHÔNG `allow_guest`, KHÔNG `methods=['POST']`):
- **401** = `Unauthorized401` (FrappeRawError, bearer hết-hạn → session=Guest, status-line THẬT) → app refresh/re-auth.
- **403** = `Forbidden` SINGLE-SHAPE (FrappeRawError, **dispatcher-403** guest/no-token — KHÔNG có nhánh in-handler cap-403 ở 2 read này) → app re-auth.
- **Lỗi nghiệp-vụ** (R2 404) = **in-handler HTTP-200 + Error envelope** (KHÔNG raise→4xx).
- **INV count==rows**: `list_transfers` `db.count(filters)` @`:2057` == `len(get_list(filters))` @`:2059` (cùng `filters` dict; Asset Transfer KHÔNG có `permission_query_conditions` riêng).

*(Đặc-tả write-action điều-chuyển — `approveTransfer`/`rejectTransfer`/`receiveTransfer` POST @`imm00.py:2543/2552/2561`, LIVE — là **[ROADMAP]** vòng kế: ADR-MOBILE-021 §BACKLOG.)*

---

*(File này là **interface contract** — §1–§6 = RAS Đợt-3 skeleton (cập nhật shape khi BE scaffold); §7 = Asset Transfer read-surface LIVE đã wire mobile. Trạng-thái "Live" của từng phần đánh dấu trong [README](./README.md).)*
