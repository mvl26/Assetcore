# IMM-02 — API Interface

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-02 — Tech Spec & Market Analysis |
| Phiên bản | 0.1.0 |
| Ngày cập nhật | 2026-04-29 |
| Trạng thái | DRAFT |
| Base path | `/api/method/assetcore.api.imm02.<endpoint>` |

---

## 1. Conventions

> **⚠ Đọc kèm `docs/WAVE2_ALIGNMENT.md`** — envelope + error code align Wave 1.

- Auth Frappe session / API key.
- Helper: `from assetcore.utils.helpers import _ok, _err`; `from assetcore.services.shared import ErrorCode, ServiceError`.
- Envelope: `{success: true, data}` / `{success: false, error, code}`.
- Error code thuộc enum `ErrorCode` (`VALIDATION`, `INVALID_PARAMS`, `BUSINESS_RULE`, `BAD_STATE`, `CONFLICT`, `DUPLICATE`, `NOT_FOUND`, `FORBIDDEN`, `UNAUTHORIZED`, `INTERNAL`). Mã VR/Gate (`VR-02-xx`, `G01–G04`) chỉ xuất hiện trong `error` message + log.
- Audit trail ghi qua `IMM Audit Trail` (không có `Tech Spec Lifecycle Event` riêng).

---

## 2. Endpoint catalog (14)

| # | Endpoint | Method | Role | Mục đích |
|---|---|---|---|---|
| 1 | `list_tech_specs` | GET | All IMM roles | Filter spec |
| 2 | `get_tech_spec` | GET | All IMM roles | Detail |
| 3 | `draft_from_plan` | POST | KH-TC, HTM Engineer | Tạo Tech Spec từ plan_item |
| 4 | `update_tech_spec` | POST | HTM Engineer (Draft/Reviewing) | Edit |
| 5 | `add_requirement` | POST | HTM Engineer | Thêm 1 requirement |
| 6 | `bulk_import_requirements` | POST | HTM Engineer | Excel import |
| 7 | `submit_benchmark` | POST | KH-TC Officer | Save Market Benchmark |
| 8 | `submit_infra_compat` | POST | QA Risk / CNTT | Submit 6 mục Infra |
| 9 | `submit_lock_in_assessment` | POST | QA Risk Team | Submit Lock-in |
| 10 | `transition_workflow` | POST | role-by-state | Chạy 1 transition |
| 11 | `lock_spec` | POST | VP Block1 | Pending Approval → Locked |
| 12 | `withdraw_spec` | POST | VP Block1 / PTP Khối 1 | Locked → Withdrawn |
| 13 | `reissue_spec` | POST | HTM Engineer | Withdrawn → Draft (new version) |
| 14 | `dashboard_kpis` | GET | KH-TC, PTP Khối 1 | KPI |

---

## 3. Endpoint specs

### 3.1 `list_tech_specs`

```
GET ?workflow_state=Draft&device_category=Imaging&page=1&page_size=20
```

Response: items với name, device_model_ref, version, candidate_count, lock_in_score (nếu có quyền permlevel 1), workflow_state.

### 3.2 `draft_from_plan`

```json
POST {
  "plan": "PP-26-001",
  "plan_lines": ["PP-26-001#L1","PP-26-001#L2"]
}
```

Response: `{ "created": ["TS-26-00045","TS-26-00046"] }`.

### 3.3 `add_requirement`

```json
POST {
  "name": "TS-26-00045",
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

### 3.4 `bulk_import_requirements`

```json
POST {
  "name": "TS-26-00045",
  "rows": [...]
}
```

### 3.5 `submit_benchmark`

```json
POST {
  "spec_ref": "TS-26-00045",
  "weighting_scheme": {"price":30,"spec":40,"support":20,"brand":10},
  "candidates": [
    {"manufacturer":"Hamilton","model":"C6","spec_match_pct":92,"price_estimate":2100000000,"support_tier":"Tier1","local_partner":"Vinamed","in_avl":1},
    {"manufacturer":"Dräger","model":"V500","spec_match_pct":88,"price_estimate":1900000000,"support_tier":"Tier1"},
    {"manufacturer":"Mindray","model":"SV600","spec_match_pct":85,"price_estimate":1400000000,"support_tier":"Tier2"}
  ]
}
```

Response: `{ "name":"MB-26-00078", "recommended_candidate":"Hamilton C6", "scores":[...] }`

### 3.6 `submit_infra_compat`

```json
POST {
  "name": "TS-26-00045",
  "items": [
    {"domain":"Electrical","compatibility_status":"Compatible","current_state":"380V/3P sẵn"},
    {"domain":"Medical Gas","compatibility_status":"Need Upgrade","upgrade_cost_estimate":50000000,"upgrade_eta":"2026-09-30"},
    {"domain":"Network/IT","compatibility_status":"Compatible"},
    {"domain":"HIS-PACS-LIS","compatibility_status":"Compatible"},
    {"domain":"HVAC","compatibility_status":"N/A"},
    {"domain":"Space-Layout","compatibility_status":"Need Upgrade"}
  ]
}
```

Effect: nếu có "Need Upgrade", trả về task IMM-04 prep auto-tạo `{ "imm04_prep_tasks": [...] }`.

### 3.7 `submit_lock_in_assessment`

```json
POST {
  "spec_ref": "TS-26-00045",
  "items": [
    {"dimension":"Protocol Standard","score":2,"rationale":"DICOM + HL7 hỗ trợ"},
    {"dimension":"Consumable Source","score":4,"rationale":"Cartridge sole-source 1 năm"},
    {"dimension":"Software License","score":3,"rationale":"License gắn S/N"},
    {"dimension":"Parts Source","score":3,"rationale":"OEM parts only"},
    {"dimension":"Service Tooling","score":4,"rationale":"Tool độc quyền OEM"}
  ],
  "mitigation_plan": "Hợp đồng 5 năm consumable + thoả thuận parts escrow",
  "mitigation_evidence": "/files/mitigation-evidence-LR-78.pdf"
}
```

Response: `{ "lock_in_score": 3.20, "threshold": 2.5, "passes_g4": true }` (do có mitigation plan).

### 3.8 `lock_spec`

```json
POST { "name": "TS-26-00045", "approver": "vp.block1@hospital.vn", "remarks": "..." }
```

Pre: Pending Approval, G04 pass. Effect: docstatus=1; publish_realtime `imm02_spec_locked`.

### 3.9 `withdraw_spec`

```json
POST { "name":"TS-26-00045", "withdrawal_reason":"Phát hiện sai test method, cần reissue" }
```

### 3.10 `reissue_spec`

```json
POST { "from_spec":"TS-26-00045" }
```

Response: `{ "name":"TS-26-00046", "version":"2.0", "parent_spec":"TS-26-00045" }`.

### 3.11 `transition_workflow`

```json
POST { "name":"TS-26-00045", "action":"Hoàn tất benchmark" }
```

### 3.12 `dashboard_kpis`

```
GET ?period=2026-Q2
```

Response 6 KPI (mục 10 Module Overview).

---

## 4. Realtime events

| Event | Payload | Subscriber |
|---|---|---|
| `imm02_spec_locked` | `{name, source_plan, source_plan_line, device_model_ref}` | IMM-03 vendor eval seeder |
| `imm02_spec_withdrawn` | `{name, reason}` | IMM-03 cancel pending eval |
| `imm02_infra_upgrade_required` | `{name, items[]}` | IMM-04 prep task creator |

---

## 5. Error catalog

`code` luôn là enum `ErrorCode`; mã VR/Gate chỉ xuất hiện trong `error` message.

| Tình huống | code | HTTP | Ví dụ `error` |
|---|---|---|---|
| Trùng Active Tech Spec cho plan_line | `DUPLICATE` | 409 | "VR-02-01: plan_line đã có Tech Spec Active" |
| Thiếu mandatory requirement | `VALIDATION` | 400 | "VR-02-02: Cần ≥ 1 mandatory requirement" |
| Mandatory requirement thiếu test_method | `VALIDATION` | 400 | "VR-02-03: Mandatory requirement phải có test_method" |
| Benchmark < 3 candidate | `BUSINESS_RULE` | 422 | "VR-02-04: Cần ≥ 3 benchmark candidate" |
| Infra compat thiếu mục | `VALIDATION` | 400 | "VR-02-05: Infra compat phải có 6/6 mục" |
| Cấm sửa lifecycle | `BUSINESS_RULE` | 422 | "VR-02-06: Audit trail bất biến" |
| G01–G04 Gate fail | `BUSINESS_RULE` | 422 | "G04: Lock-in score vượt ngưỡng — cần mitigation_plan + evidence" |
| Transition workflow sai | `BAD_STATE` | 409 | "Transition không hợp lệ với state hiện tại" |
| Không đủ quyền (permlevel lock-in) | `FORBIDDEN` | 403 | "Trường lock_in_score chỉ hiển thị với IMM Risk Officer / IMM Board Approver" |

---

## 6. OpenAPI excerpt

```yaml
openapi: 3.0.3
info: { title: AssetCore IMM-02 API, version: 0.1.0 }
paths:
  /assetcore.api.imm02.lock_spec:
    post:
      requestBody:
        content:
          application/json:
            schema:
              type: object
              required: [name, approver]
              properties:
                name: { type: string }
                approver: { type: string }
                remarks: { type: string }
```

*End of API Interface v0.1.0 — IMM-02*
