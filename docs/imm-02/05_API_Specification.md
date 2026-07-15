# IMM-02 — API Specification

> **Wave 2 — Live.** Tất cả endpoint đã implement tại `assetcore/api/imm02.py` với `@frappe.whitelist()`.

| Mục | Giá trị |
|---|---|
| Module | **IMM-02 — Thông số Kỹ thuật & Phân tích Thị trường** |
| Phiên bản | 1.0.1 |
| Ngày cập nhật | 2026-05-14 |
| Base path | `/api/method/assetcore.api.imm02.<endpoint>` |
| Owner | Tech Lead |
| Liên kết | [04 Backend Design](./04_Backend_Design.md) · [06 Frontend Design](./06_Frontend_Design.md) |

---

# §1 — Conventions

## 1.1 AssetCore Envelope

**Mọi response PHẢI dùng envelope này. KHÔNG dùng bất kỳ format nào khác.**

```json
// Success
{
  "success": true,
  "data": { ... }
}

// Error
{
  "success": false,
  "error": "Thông báo lỗi tiếng Việt cho người dùng",
  "code": "ERROR_CODE_ENUM"
}
```

**HTTP status: luôn 200.** Phân biệt thành công/lỗi qua `success` field. KHÔNG dùng 4xx/5xx.

## 1.2 Authentication

- Frappe session cookie (`sid`) HOẶC API Key + API Secret (header `Authorization: token key:secret`)
- Mọi endpoint yêu cầu đăng nhập. Không có public endpoint trong IMM-02.

## 1.3 Pagination

```json
{
  "success": true,
  "data": {
    "items": [...],
    "total": 120,
    "page": 1,
    "page_size": 20
  }
}
```

## 1.4 Error Handling

```python
# Raise errors via ServiceError — NEVER use frappe.throw directly in API layer
raise ServiceError(ErrorCode.VALIDATION, "Thông báo lỗi tiếng Việt")
raise ServiceError(ErrorCode.BUSINESS_RULE, "G01: Cần ≥ 8 yêu cầu bắt buộc")
raise ServiceError(ErrorCode.BAD_STATE, "Spec đã Locked không thể sửa")
raise ServiceError(ErrorCode.DUPLICATE, "VR-02-01: plan_line đã có Tech Spec active")
```

---

# §2 — Role Constants

```typescript
export const IMM02_ROLES = {
  HTM_ENGINEER:     "IMM HTM Engineer",
  PLANNING_OFFICER: "IMM Planning Officer",
  RISK_OFFICER:     "IMM Risk Officer",
  SYSTEM_ADMIN:     "IMM System Admin",
  DEPT_HEAD:        "IMM Department Head",
  BOARD_APPROVER:   "IMM Board Approver",
} as const;
```

---

# §3 — Endpoints (16 — Thực tế)

**Catalog thực tế (từ `@frappe.whitelist()` decorators trong `assetcore/api/imm02.py`):**

| # | Function | Method | Mô tả |
|---|---|---|---|
| 3.1 | `list_tech_specs` | GET | List + filter Tech Spec (`filters`, `page`, `page_size`) |
| 3.2 | `get_tech_spec` | GET | Chi tiết 1 Tech Spec |
| 3.3 | `create_tech_spec` | POST | Tạo Tech Spec mới (payload JSON) |
| 3.4 | `draft_from_plan` | POST | Tạo Tech Spec drafts từ Procurement Plan (1 spec / NR) |
| 3.5 | `update_tech_spec` | POST | Cập nhật Tech Spec (chỉ khi docstatus=0) |
| 3.6 | `add_requirement` | POST | Thêm 1 row vào child table `requirements` (svc.add_requirement_to_spec) |
| 3.7 | `bulk_import_requirements` | POST | Bulk thêm requirements từ list dict đã parse từ CSV ở FE |
| 3.8 | `transition_workflow` | POST | Áp dụng workflow action lên Tech Spec |
| 3.9 | `get_market_benchmark` | GET | Chi tiết 1 IMM Market Benchmark |
| 3.10 | `get_lock_in_assessment` | GET | Chi tiết 1 IMM Lock-in Risk Assessment |
| 3.11 | `lock_spec` | POST | Pending Approval → Locked (approver + submit) |
| 3.12 | `withdraw_spec` | POST | Withdraw spec (withdrawal_reason bắt buộc) |
| 3.13 | `reissue_spec` | POST | Tạo phiên bản mới từ Withdrawn spec (copy_doc + version bump) |
| 3.14 | `submit_benchmark` | POST | Tạo IMM Market Benchmark cho spec_ref |
| 3.15 | `submit_lock_in_assessment` | POST | Tạo IMM Lock-in Risk Assessment cho spec_ref |
| 3.16 | `dashboard_kpis` | GET | KPI: `by_state`, `avg_lock_in_score`, `backlog_over_30d` |

> **Endpoints KHÔNG tồn tại** (xuất hiện trong design cũ nhưng chưa implement): `submit_infra_compat`. Infra compat hiện update qua `update_tech_spec` với payload chứa `infra_compat` array.
>
> Note: `add_requirement` (line 195) và `bulk_import_requirements` (line 209) ĐÃ implement trong `assetcore/api/imm02.py`, delegate sang `services/imm02.add_requirement_to_spec` / `bulk_import_requirements_from_csv`. FE wrapper: `addRequirement`, `bulkImportRequirements` trong `frontend/src/api/imm02.ts`.

---

## 3.1 `list_tech_specs` — GET

List Tech Spec với filter.

**Request:**
```
GET ?workflow_state=Draft&device_category=Imaging&page=1&page_size=20&overdue_only=false
```

**Free-text search** (convention chung — xem `docs/template/05_API_Specification.md`
§3.1): FE đính kèm `search` vào dict `filters`, ví dụ
`?filters={"workflow_state":"Draft","search":"Hamilton"}`. BE bóc qua
`pop_search(f, ["name", "version"], link_search={"device_model_ref": ("IMM Device Model", "model_name")})`
— direct LIKE trên `name` + `version`, và resolve `model_name` qua
`IMM Device Model`. Pagination total dùng `count_with_or` để khớp
OR-clause.

> CẤM pass dict `filters` thô (có key `search`) vào `frappe.get_list` —
> sẽ raise `(1054, "Unknown column 'tabIMM Tech Spec.search' in 'WHERE'")`.

**FE placeholder** (`TechSpecListView.vue`):
`"Tìm theo mã hồ sơ, tên model hoặc phiên bản..."` — "tên model" map
sang link_search, "mã hồ sơ" map sang `name`, "phiên bản" map sang
`version`. Sửa cùng PR khi `searchable_fields` / `link_search` thay đổi
(xem `docs/template/06_Frontend_Design.md` §3.c.i).

**Response:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "name": "TS-26-00045",
        "spec_id": "TS-26-00045",
        "device_model_ref": "Hamilton C6",
        "device_category": "Life Support",
        "version": "1.0",
        "workflow_state": "Risk Assessed",
        "total_mandatory": 12,
        "candidate_count": 3,
        "lock_in_score": 3.2,
        "source_plan": "PP-26-001",
        "creation": "2026-04-15",
        "modified": "2026-05-01"
      }
    ],
    "total": 67,
    "page": 1,
    "page_size": 20
  }
}
```

> Note: `lock_in_score` chỉ trả về nếu user có permlevel 1 (QA Risk / VP Block1 / CMMS Admin).

## 3.2 `get_tech_spec` — GET

Lấy chi tiết 1 Tech Spec.

**Request:**
```
GET ?name=TS-26-00045
```

**Response:**
```json
{
  "success": true,
  "data": {
    "name": "TS-26-00045",
    "spec_id": "TS-26-00045",
    "draft_date": "2026-04-15",
    "source_plan": "PP-26-001",
    "source_plan_line": "PP-26-001#L3",
    "source_needs_request": "NR-26-04-00012",
    "device_model_ref": "Hamilton C6",
    "quantity": 2,
    "version": "1.0",
    "parent_spec": null,
    "workflow_state": "Risk Assessed",
    "total_mandatory": 12,
    "total_optional": 5,
    "requirements": [
      {
        "seq": 1,
        "group": "Performance",
        "parameter": "Tidal Volume",
        "value_or_range": "20–2000 mL",
        "unit": "mL",
        "is_mandatory": 1,
        "weight": 8,
        "test_method": "IEC 60601-2-12 bench test"
      }
    ],
    "benchmark_ref": "MB-26-00021",
    "candidate_count": 3,
    "infra_compat": [
      {
        "domain": "Electrical",
        "compatibility_status": "Compatible",
        "current_state": "220V/50Hz",
        "required_state": "220V/50Hz"
      }
    ],
    "lock_in_risk_ref": "LR-26-00009",
    "infra_status_overall": "Partial",
    "allowed_transitions": ["lock", "withdraw"],
    "can_lock": 1,
    "can_withdraw": 1,
    "can_reissue": 0
  }
}
```

**Server-driven CTA gating (GATE-8 / LL-FE-51 — vòng 6).** `get_tech_spec` bổ sung 4 field derive server-side (BR-02-08/09, ADR-IMM02-01) để FE gate nút "Chốt / Rút / Phát hành lại" mà KHÔNG suy từ `workflow_state`:

| Field | Kiểu | Nguồn derive |
|---|---|---|
| `allowed_transitions` | `string[]` | `_SPEC_CTA_TRANSITIONS.get(workflow_state, [])` — hint hiển thị role-agnostic. Mặc định `[]` khi state lạ/`None`. |
| `can_lock` | `0\|1` | `int("lock" in allowed_transitions and rbac.can("spec.submit"))` |
| `can_withdraw` | `0\|1` | `int("withdraw" in allowed_transitions and rbac.can("spec.submit"))` |
| `can_reissue` | `0\|1` | `int("reissue" in allowed_transitions and rbac.can("spec.create"))` |

Ma trận cờ theo state (giả định user có capability):

| workflow_state | allowed_transitions | can_lock | can_withdraw | can_reissue |
|---|---|---|---|---|
| `Pending Approval` | `["lock","withdraw"]` | 1 | 1 | 0 |
| `Locked` | `["withdraw"]` | 0 | 1 | 0 |
| `Withdrawn` | `["reissue"]` | 0 | 0 | 1 |
| Draft / Reviewing / Benchmarked / Risk Assessed | `[]` | 0 | 0 | 0 |

> **INVARIANT (map ⊆ guard):** cờ advertise ⊆ tập guard `lock_spec`/`withdraw_spec`/`reissue_spec` thực cho phép. `allowed_transitions` chỉ là hint, KHÔNG nới lỏng guard. User thiếu capability → cờ = 0 (nút ẩn) VÀ endpoint trả `FORBIDDEN` nếu bị gọi trực tiếp.

**Server-driven CTA cho 6 transition trung gian (CR-WF-02-SPEC — vòng 24, BR-02-10, ADR-IMM02-02).** `get_tech_spec` bổ sung field `allowed_actions` để FE render nút chuyển-trạng-thái trung gian (Gửi rà soát / Yêu cầu chỉnh spec / Hoàn tất benchmark / Đánh giá rủi ro xong / Trình duyệt spec / Yêu cầu chỉnh risk):

| Field | Kiểu | Nguồn derive |
|---|---|---|
| `allowed_actions` | `string[]` | `spec_allowed_actions(workflow_state, frappe.get_roles(user))` — danh sách **nhãn ACTION** (VI) đã LỌC theo role. Mặc định `[]` khi state lạ/terminal (Locked/Withdrawn). |

> ⚠️ `allowed_actions` (nhãn ACTION, vòng 24) ≠ `allowed_transitions` (next-STATE hint của vòng 6). **2 key khác semantic**, cùng tồn tại — KHÔNG collide.

Ví dụ đo được (theo state × role):

| workflow_state | roles user | `allowed_actions` |
|---|---|---|
| `Draft` | `Spec User` | `["Gửi rà soát"]` |
| `Reviewing` | `Needs Manager` | `["Yêu cầu chỉnh spec","Hoàn tất benchmark"]` |
| `Reviewing` | `Spec User` | `["Yêu cầu chỉnh spec"]` |
| `Pending Approval` | `Procurement Manager` | `["Yêu cầu chỉnh risk"]` (+ can_lock/can_withdraw riêng) |
| `Locked` / `Withdrawn` | bất kỳ | `[]` |

> **INVARIANT (advertise ⟺ reachable):** roles trong SSoT `_SPEC_VALID_TRANSITIONS` == `allowed` gom-vai của `imm_02_spec_workflow.json` (reconcile test). `transition_workflow` áp qua `apply_workflow` native → mỗi action ∈ `allowed_actions` khi apply KHÔNG raise permission + đổi đúng `next_state`; user thiếu role → action vắng khỏi list. (Nhánh business-gate G01–G04 vẫn có thể reject `BUSINESS_RULE` — UX đúng.)

## 3.3 `create_tech_spec` — POST

Tạo Tech Spec mới (payload tự do — gọi `frappe.get_doc`).

**Request:**
```json
{
  "payload": {
    "source_plan": "PP-26-001",
    "source_plan_line": "PP-26-001#L3",
    "source_needs_request": "NR-26-04-00012",
    "device_model_ref": "Hamilton C6",
    "quantity": 2
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "name": "TS-26-00045",
    "workflow_state": "Draft",
    "version": "1.0"
  }
}
```

## 3.4 `draft_from_plan` — POST

Tạo Tech Spec draft từ Procurement Plan Lines.

**Request:**
```json
{
  "plan": "PP-26-001",
  "plan_lines": ["PP-26-001#L1", "PP-26-001#L2", "PP-26-001#L3"]
}
```

**Response (thực tế — chỉ `created` array; lines đã có spec bị skip silently):**
```json
{
  "success": true,
  "data": {
    "created": ["TS-26-00045", "TS-26-00046", "TS-26-00047"]
  }
}
```

> Note: Không có `"skipped"` hay `"errors"` key trong response thực tế. Lines đã có spec active bị bỏ qua thầm lặng (check `frappe.db.exists` trước khi tạo). FE cần so sánh `created.length` với số line_names được yêu cầu để biết có skip không.

## 3.5 `update_tech_spec` — POST

Cập nhật header fields (chỉ khi Draft hoặc Reviewing).

**Request:**
```json
{
  "name": "TS-26-00045",
  "payload": {
    "quantity": 3,
    "spec_template_ref": "TMPL-Life-Support-01"
  }
}
```

> Note: param tên là `payload` (KHÔNG phải `data`) — khớp với `_update_tech_spec(name, payload)`. Child tables `requirements`, `documents`, `infra_compat` trong payload sẽ được replace hoàn toàn (set rỗng rồi append).

**Response (thực tế — không có `updated_fields`):**
```json
{
  "success": true,
  "data": {
    "name": "TS-26-00045",
    "workflow_state": "Draft"
  }
}
```

## 3.6 `add_requirement` — POST

Thêm 1 requirement vào Tech Spec. **Params thực tế: `spec`, `requirement` (JSON object).**

**Request:**
```json
{
  "spec": "TS-26-00045",
  "requirement": {
    "group": "Performance",
    "parameter": "Tidal Volume",
    "value_or_range": "20–2000 mL",
    "unit": "mL",
    "is_mandatory": 1,
    "weight": 8,
    "test_method": "IEC 60601-2-12 bench test"
  }
}
```

**Response (thực tế):**
```json
{
  "success": true,
  "data": {
    "name": "TS-26-00045",
    "requirement_idx": 9,
    "total_mandatory": 9,
    "total_optional": 3
  }
}
```

## 3.7 `bulk_import_requirements` — POST

Bulk thêm requirements từ list dict (đã parse từ CSV/Excel ở FE). **Params thực tế: `spec`, `rows` (JSON array of objects).**

**Request:**
```json
{
  "spec": "TS-26-00045",
  "rows": [
    {"group": "Performance", "parameter": "Tidal Volume", "value_or_range": "20–2000 mL", "is_mandatory": 1, "test_method": "IEC 60601-2-12"},
    {"group": "Safety", "parameter": "Alarm Priority", "value_or_range": "P1/P2/P3", "is_mandatory": 1, "test_method": "Manual verify"}
  ]
}
```

**Response (thực tế):**
```json
{
  "success": true,
  "data": {
    "name": "TS-26-00045",
    "imported": 2,
    "total_mandatory": 12,
    "total_optional": 13
  }
}
```

## 3.8 `transition_workflow` — POST

Thực thi 1 workflow transition trung gian (áp qua `apply_workflow` **native** — Frappe enforce đúng `allowed` role của transition). `action` phải ∈ `allowed_actions` mà `get_tech_spec` trả về (server-driven CTA — vòng 24).

**Request:**
```json
{
  "name": "TS-26-00045",
  "action": "Gửi rà soát"
}
```

**Response (thực tế):**
```json
{
  "success": true,
  "data": {
    "name": "TS-26-00045",
    "workflow_state": "Reviewing",
    "docstatus": 0
  }
}
```

**2 loại 403 (DONE-gate spec-contract — CR-WF-02-SPEC):**

| Loại | Điều kiện | Hình thức trả |
|---|---|---|
| **dispatcher-403** | guest / no-token (endpoint bare `@whitelist(methods=["POST"])`, KHÔNG `allow_guest`) | Frappe từ chối TRƯỚC handler (HTTP 403 status-line) |
| **in-handler cap-403** | user login thiếu role của cạnh → `apply_workflow` raise `PermissionError` | `_handle` bắt → `_err(str(e), FORBIDDEN)` = **HTTP-200 + Error envelope** (KHÔNG raise→HTTP-4xx) |

> `action` không hợp lệ từ state hiện tại → `apply_workflow` raise `ValidationError` → `_err(..., VALIDATION)` (HTTP-200). Gate nghiệp vụ (G01–G04) fail → `BUSINESS_RULE` (HTTP-200). Cả hai giữ envelope in-handler.

## 3.9 `get_market_benchmark` — GET

Lấy chi tiết 1 IMM Market Benchmark.

**Request:**
```
GET ?name=MB-26-00021
```

**Response:**
```json
{
  "success": true,
  "data": {
    "name": "MB-26-00021",
    "spec_ref": "TS-26-00045",
    "benchmark_date": "2026-05-01",
    "recommended_candidate": "Hamilton Medical C6",
    "weighting_scheme": "{\"price\":30,\"spec\":40,\"support\":20,\"brand\":10}",
    "candidates": [ ... ]
  }
}
```

## 3.10 `get_lock_in_assessment` — GET

Lấy chi tiết 1 IMM Lock-in Risk Assessment.

**Request:**
```
GET ?name=LR-26-00009
```

**Response:**
```json
{
  "success": true,
  "data": {
    "name": "LR-26-00009",
    "spec_ref": "TS-26-00045",
    "assessment_date": "2026-05-02",
    "lock_in_score": 3.05,
    "threshold_used": 2.5,
    "items": [ ... ],
    "mitigation_plan": "..."
  }
}
```

> Note: `lock_in_score`, `threshold_used`, `mitigation_plan`, `mitigation_evidence` ở permlevel 1.

## 3.11 `lock_spec` — POST

Submit Tech Spec (Pending Approval → Locked). **Params thực tế: `name`, `approver` (bắt buộc), `remarks` (optional).**

**Guard (thứ tự capability → state — BR-02-09, ADR-IMM02-01):**
1. `rbac.can("spec.submit")` sai → `ServiceError(FORBIDDEN)` (in-handler cap-403 → **HTTP-200 + Error envelope**, KHÔNG raise→HTTP-4xx).
2. `workflow_state != "Pending Approval"` → `BAD_STATE`.

> Trước vòng 6: chỉ có bước (2). Mọi user login (kể cả không quyền) pass state rồi `doc.submit()` → Lock thành công. Từ vòng 6: bước (1) chặn trước. Phân biệt với **dispatcher-403** (guest / thiếu token) — trả ở tầng dispatcher trước khi vào handler; guard này là **in-handler cap-403** (envelope `success:false`, code `FORBIDDEN`).

**Request:**
```json
{
  "name": "TS-26-00045",
  "approver": "vp.block1@hospital.vn",
  "remarks": "Duyệt theo biên bản họp 2026-05-08"
}
```

**Response (thực tế):**
```json
{
  "success": true,
  "data": {
    "name": "TS-26-00045",
    "workflow_state": "Locked"
  }
}
```

## 3.12 `withdraw_spec` — POST

Rút hồ sơ. **Param thực tế: `withdrawal_reason` (không phải `reason`).**

**Guard (thứ tự capability → state — BR-02-09):** `rbac.can("spec.submit")` sai → `FORBIDDEN` (in-handler cap-403, HTTP-200 + envelope); rồi `workflow_state not in ("Pending Approval","Locked")` → `BAD_STATE`; `withdrawal_reason` rỗng → `VALIDATION`.

**Request:**
```json
{
  "name": "TS-26-00045",
  "withdrawal_reason": "Cần cập nhật thông số do thay đổi phiên bản thiết bị mới"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "name": "TS-26-00045",
    "workflow_state": "Withdrawn"
  }
}
```

## 3.13 `reissue_spec` — POST

Tái phát hành phiên bản mới từ spec đã Withdrawn. **Param thực tế: `from_spec` (không phải `name`).**

**Guard (thứ tự capability → state — BR-02-09):** `rbac.can("spec.create")` sai → `FORBIDDEN` (in-handler cap-403, HTTP-200 + envelope); rồi `workflow_state != "Withdrawn"` → `BAD_STATE`. (Quyền vật lý = *create* vì `copy_doc` + `insert` bản Draft mới.)

**Request:**
```json
{
  "from_spec": "TS-26-00045"
}
```

**Response (thực tế):**
```json
{
  "success": true,
  "data": {
    "name": "TS-26-00048",
    "version": "2.0",
    "parent_spec": "TS-26-00045"
  }
}
```

## 3.14 `submit_benchmark` — POST

Tạo IMM Market Benchmark cho Tech Spec. **Tên param thực tế: `spec_ref`, `candidates` (JSON array), `weighting_scheme` (JSON object).**

**Request:**
```json
{
  "spec_ref": "TS-26-00045",
  "weighting_scheme": {"price": 30, "spec": 40, "support": 20, "brand": 10},
  "candidates": [
      {
        "manufacturer": "Hamilton Medical",
        "model": "C6",
        "country": "Switzerland",
        "spec_match_pct": 95.5,
        "price_estimate": 450000000,
        "price_source": "Vendor Quote",
        "support_tier": "Tier1",
        "local_partner": "MedViet JSC",
        "in_avl": 1
      },
      {
        "manufacturer": "Dräger",
        "model": "Evita V600",
        "country": "Germany",
        "spec_match_pct": 88.0,
        "price_estimate": 480000000,
        "price_source": "Vendor Quote",
        "support_tier": "Tier1",
        "local_partner": "Draeger Vietnam",
        "in_avl": 1
      },
      {
        "manufacturer": "Mindray",
        "model": "SV600",
        "country": "China",
        "spec_match_pct": 80.0,
        "price_estimate": 290000000,
        "price_source": "Public Tender",
        "support_tier": "Tier2",
        "local_partner": "Mindray VN",
        "in_avl": 0
      }
  ]
}
```

**Response (thực tế):**
```json
{
  "success": true,
  "data": {
    "name": "MB-26-00021",
    "recommended": "Hamilton Medical C6"
  }
}
```

> Note: `recommended` field (không phải `recommended_candidate`) — từ `_submit_benchmark` return `{"name": mb.name, "recommended": mb.recommended_candidate}`.

## 3.15 `submit_lock_in_assessment` — POST

Submit đánh giá lock-in risk. **Tên param thực tế: `spec_ref`, `items` (JSON array), `threshold` (optional float), `mitigation_plan`, `mitigation_evidence`.**

**Request:**
```json
{
  "spec_ref": "TS-26-00045",
  "threshold": 2.5,
  "mitigation_plan": "1. Yêu cầu Hamilton API export HL7/FHIR\n2. Đàm phán giá circuit 5 năm",
  "mitigation_evidence": "",
  "items": [
    {"dimension": "Protocol Standard", "score": 4},
    {"dimension": "Consumable Source", "score": 3},
    {"dimension": "Software License", "score": 2},
    {"dimension": "Parts Source", "score": 3},
    {"dimension": "Service Tooling", "score": 2}
  ]
}
```

**Response (thực tế):**
```json
{
  "success": true,
  "data": {
    "name": "LR-26-00009",
    "lock_in_score": 3.05,
    "threshold": 2.5
  }
}
```

## 3.16 `dashboard_kpis` — GET

Dashboard KPI cho IMM-02. **Không có query params (endpoint không nhận args).**

**Request:**
```
GET /api/method/assetcore.api.imm02.dashboard_kpis
```

**Response (thực tế — từ `_dashboard_kpis()` trong api/imm02.py):**
```json
{
  "success": true,
  "data": {
    "by_state": {
      "Draft": 8,
      "Reviewing": 5,
      "Benchmarked": 7,
      "Risk Assessed": 4,
      "Pending Approval": 3,
      "Locked": 13,
      "Withdrawn": 2
    },
    "avg_lock_in_score": 2.3,
    "backlog_over_30d": 3
  }
}
```

> Note: Response chỉ có 3 fields. `total_specs`, `lead_time_avg_days`, `rework_rate_pct`, `pct_spec_reuse_template`, `pct_with_3plus_benchmark` là KPI thiết kế — chưa implement trong `dashboard_kpis`.

---

# §4 — Error Catalog

| Code | Mô tả | Khi nào |
|---|---|---|
| `DUPLICATE` | VR-02-01: plan_line đã có Tech Spec active | draft_from_plan với plan_line trùng |
| `VALIDATION` | VR-02-02: không có mandatory requirement | validate thiếu mandatory |
| `VALIDATION` | VR-02-03: mandatory thiếu test_method | validate test_method |
| `VALIDATION` | VR-02-04: benchmark < 3 candidates | validate benchmark |
| `VALIDATION` | VR-02-05: infra_compat chưa đủ 6 domains | validate infra |
| `BUSINESS_RULE` | G01: cần ≥ 8 mandatory + 100% test_method | transition Draft→Reviewing |
| `BUSINESS_RULE` | G02: benchmark cần ≥ 3 candidate | transition Reviewing→Benchmarked |
| `BUSINESS_RULE` | G03: infra 6/6 domains | transition Benchmarked→Risk Assessed |
| `BUSINESS_RULE` | G04: lock-in cao, thiếu mitigation | lock_spec |
| `BAD_STATE` | Spec Locked không thể sửa | update_tech_spec khi Locked |
| `BAD_STATE` | Chỉ Withdrawn spec mới reissue được | reissue_spec |
| `BAD_STATE` | Chỉ Locked/Pending Approval mới Withdraw | withdraw_spec |
| `NOT_FOUND` | Tech Spec không tồn tại | get_tech_spec |
| `FORBIDDEN` | Không đủ quyền (permlevel 1) | xem lock_in_score |
| `FORBIDDEN` | Thiếu capability `spec.submit` (BR-02-09) — in-handler cap-403, HTTP-200 + envelope | lock_spec / withdraw_spec |
| `FORBIDDEN` | Thiếu capability `spec.create` (BR-02-09) | reissue_spec |
| `FORBIDDEN` | User login thiếu role của transition (`apply_workflow`→`PermissionError`) — in-handler cap-403, HTTP-200 + envelope | transition_workflow |
| `VALIDATION` | `action` không hợp lệ từ state hiện tại | transition_workflow |
| `BUSINESS_RULE` | Gate G01–G04 fail khi chuyển state | transition_workflow |
| `INTERNAL` | Lỗi hệ thống không xác định | mọi trường hợp unexpected |

---

# §5 — TypeScript Types

File: `frontend/src/types/imm02.ts` — **Đã implement. Xem file thực tế để biết full schema.**

> **Lưu ý về type names thực tế:** `frontend/src/types/imm02.ts` dùng tên:
> - `TechSpecListItem` (list row), `TechSpecDoc` (detail document)
> - `DashboardKpis` (dashboard KPIs — KHÔNG phải `Imm02KPIs`)
> - `SpecState` (workflow state union — KHÔNG phải `TechSpecState`)
> Các types dưới đây là design spec — ground truth xem file thực tế.

```typescript
// Design spec types — ground truth: frontend/src/types/imm02.ts

export interface TechSpec {
  name: string;
  spec_id: string;
  draft_date: string;
  source_plan: string;
  source_plan_line: string;
  source_needs_request: string;
  device_model_ref: string;
  device_category: string;
  quantity: number;
  version: string;
  parent_spec: string | null;
  workflow_state: TechSpecState;
  total_mandatory: number;
  total_optional: number;
  requirements: TechSpecRequirement[];
  benchmark_ref: string | null;
  candidate_count: number;
  infra_compat: InfraCompatItem[];
  infra_status_overall: InfraOverallStatus;
  lock_in_risk_ref: string | null;
  lock_in_score?: number; // permlevel 1 — only visible to authorized roles
  mitigation_plan?: string;
  approval_date: string | null;
  withdrawal_reason?: string;
  documents: TechSpecDocument[];
  // Server-driven CTA gating (vòng 6 — chỉ có trên get_tech_spec detail):
  allowed_transitions?: string[]; // hint next-STATE (Locked/Withdrawn/Draft), default [] khi thiếu
  can_lock?: 0 | 1;               // FE coerce Boolean() → v-if nút "Chốt hồ sơ"
  can_withdraw?: 0 | 1;           // → v-if nút "Rút hồ sơ"
  can_reissue?: 0 | 1;            // → v-if nút "Phát hành lại"
  // CR-WF-02-SPEC (vòng 24): nhãn ACTION trung gian đã lọc role → FE render 1 nút/action.
  allowed_actions?: string[];     // default [] khi state lạ/terminal; ≠ allowed_transitions (next-state)
}

export type TechSpecState =
  | "Draft"
  | "Reviewing"
  | "Benchmarked"
  | "Risk Assessed"
  | "Pending Approval"
  | "Locked"
  | "Withdrawn";

export type InfraOverallStatus =
  | "All Compatible"
  | "Partial"
  | "Need Major Upgrade";

export interface TechSpecRequirement {
  name: string;
  seq: number;
  group: RequirementGroup;
  parameter: string;
  value_or_range: string;
  unit: string;
  is_mandatory: 0 | 1;
  weight: number;
  test_method: string;
  evidence?: string;
  remark?: string;
}

export type RequirementGroup =
  | "Performance"
  | "Safety"
  | "Connectivity"
  | "Power"
  | "Mechanical"
  | "Software"
  | "Service"
  | "Compliance";

export interface BenchmarkCandidate {
  name: string;
  manufacturer: string;
  model: string;
  country: string;
  spec_match_pct: number;
  price_estimate: number;
  price_source: string;
  support_tier: "Tier1" | "Tier2" | "Tier3";
  local_partner: string;
  in_avl: 0 | 1;
  recommendation_score: number;
  notes?: string;
}

export interface MarketBenchmark {
  name: string;
  spec_ref: string;
  benchmark_date: string;
  recommended_candidate: string;
  weighting_scheme: BenchmarkWeights;
  candidates: BenchmarkCandidate[];
}

export interface BenchmarkWeights {
  price: number;
  spec: number;
  support: number;
  brand: number;
}

export interface InfraCompatItem {
  name: string;
  domain: InfraDomain;
  current_state: string;
  required_state: string;
  compatibility_status: CompatStatus;
  upgrade_owner?: string;
  upgrade_eta?: string;
  upgrade_cost_estimate?: number;
  evidence?: string;
}

export type InfraDomain =
  | "Electrical"
  | "Medical Gas"
  | "Network/IT"
  | "HIS-PACS-LIS"
  | "HVAC"
  | "Space-Layout";

export type CompatStatus =
  | "Compatible"
  | "Need Upgrade"
  | "Need Major Upgrade"
  | "N/A";

export interface LockInRiskItem {
  name: string;
  dimension: LockInDimension;
  score: 1 | 2 | 3 | 4 | 5;
  weight_pct: number;
  weighted: number;
  rationale: string;
  mitigation?: string;
}

export type LockInDimension =
  | "Protocol Standard"
  | "Consumable Source"
  | "Software License"
  | "Parts Source"
  | "Service Tooling";

export interface LockInRiskAssessment {
  name: string;
  spec_ref: string;
  assessment_date: string;
  lock_in_score: number;
  threshold_used: number;
  items: LockInRiskItem[];
  mitigation_plan?: string;
  mitigation_evidence?: string;
}

export interface TechSpecDocument {
  name: string;
  doc_type: string;
  file_attachment: string;
  version: string;
  issued_date: string;
}

export interface Imm02KPIs {
  total_specs: number;
  by_state: Record<TechSpecState, number>;
  lead_time_avg_days: number;
  pct_with_3plus_benchmark: number;
  avg_lock_in_score: number;
  rework_rate_pct: number;
  pct_spec_reuse_template: number;
  overdue_draft_count: number;
  updated_at: string;
}
```

---

# §6 — Realtime Events

| Event | Khi nào | Payload | Subscriber |
|---|---|---|---|
| `imm02_spec_locked` | Tech Spec on_submit (Locked) | `{spec: name, device_model_ref, source_plan, candidate_count}` | IMM-03 listener: seed Vendor Evaluation |
| `imm02_spec_withdrawn` | withdraw_spec() | `{spec: name, reason, original_version}` | PTP K1 notification |
| `imm02_draft_overdue` | scheduler daily | `{overdue_specs: [name,...], days_overdue_avg: N}` | PTP K1 + HTM Engineer |
