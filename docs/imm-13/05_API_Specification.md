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

*(File này là **interface contract** — khi BE scaffold xong, cập nhật shape JSON schema cụ thể vào §2, ErrorCode chính thức vào §3, và đánh dấu trạng thái "Live" trong [README](./README.md).)*
