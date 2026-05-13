# IMM-02 — Backend Design

> **Wave 2 — Live.** BE service và API đã implement đầy đủ. Tài liệu này phản ánh code thực tế tại `assetcore/services/imm02.py` và `assetcore/api/imm02.py`.

| Mục | Giá trị |
|---|---|
| Module | **IMM-02 — Thông số Kỹ thuật & Phân tích Thị trường** |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-05-08 |
| Owner | Tech Lead |
| Liên kết | [03 Diagrams](./03_Diagrams.md) · [05 API Specification](./05_API_Specification.md) |

---

# Phần I — DocType Catalog

| DocType | Naming | Submittable | track_changes | Module |
|---|---|---|---|---|
| `IMM Tech Spec` | `TS-.YY.-.#####` | Yes | Yes | AssetCore |
| `IMM Market Benchmark` | `MB-.YY.-.#####` | Yes | Yes | AssetCore |
| `IMM Lock-in Risk Assessment` | `LR-.YY.-.#####` | Yes | Yes | AssetCore |
| `Tech Spec Requirement` | (child) | — | — | AssetCore |
| `Benchmark Candidate` | (child) | — | — | AssetCore |
| `Infra Compatibility Item` | (child) | — | — | AssetCore |
| `Lock-in Risk Item` | (child) | — | — | AssetCore |
| `Tech Spec Document` | (child) | — | — | AssetCore |

> Note: `~~Tech Spec Lifecycle Event~~` — KHÔNG tạo. Audit trail dùng `IMM Audit Trail` (root_doctype=IMM Tech Spec).

---

# Phần II — DocType Schemas

## II.1. IMM Tech Spec

Naming: `TS-.YY.-.#####` · Submittable · track_changes=1

| Section | Field | Type | Required | Permlevel | Note |
|---|---|---|---|---|---|
| Header | `spec_id` | Data (auto) | — | 0 | naming |
| | `draft_date` | Date | Y | 0 | auto today |
| | `source_plan` | Link → IMM Procurement Plan | Y | 0 | |
| | `source_plan_line` | Data | Y | 0 | name of plan_item row |
| | `source_needs_request` | Link → IMM Needs Request | Y | 0 | |
| Target | `device_model_ref` | Link → IMM Device Model | Y | 0 | fetch spec_template_ref |
| | `device_category` | Link → Asset Category | N (auto) | 0 | |
| | `quantity` | Int | Y | 0 | |
| | `spec_template_ref` | Link → IMM Spec Template | N | 0 | seed requirements |
| | `parent_spec` | Link → IMM Tech Spec | N | 0 | versioning reissue |
| | `version` | Data | N | 0 | "1.0", "2.0", ... |
| Requirements | `total_mandatory` | Int (auto) | — | 0 | |
| | `total_optional` | Int (auto) | — | 0 | |
| | `requirements` | Table → Tech Spec Requirement | Y | 0 | ≥ 8 mandatory at G01 |
| | `documents` | Table → Tech Spec Document | N | 0 | |
| Benchmark | `benchmark_ref` | Link → IMM Market Benchmark | N | 0 | |
| | `candidate_count` | Int (auto) | — | 0 | ≥ 3 at G02 |
| Infra | `infra_compat` | Table → Infra Compatibility Item | Y | 0 | 6 items at G03 |
| | `infra_status_overall` | Select | — (auto) | 0 | All Compatible / Partial / Need Major Upgrade |
| Lock-in | `lock_in_risk_ref` | Link → IMM Lock-in Risk Assessment | Y | 0 | before G04 |
| | `lock_in_score` | Float (auto) | — | **1** | QA Risk + PTP K1 + VP Block1 + Admin only |
| | `mitigation_plan` | Long Text | Conditional | **1** | required if lock_in_score > threshold |
| Approval | `approver` | Link → User | Conditional | **1** | before Lock |
| | `approval_date` | Date | N | 0 | |
| | `withdrawal_reason` | Long Text | Conditional | 0 | when Withdrawn |
| Workflow | `workflow_state` | Data | Y | 0 | managed by Frappe Workflow |

**Permissions (IMM Tech Spec):**

| Role | Read | Write | Create | Delete | Submit | Amend |
|---|---|---|---|---|---|---|
| IMM HTM Engineer | ✅ | ✅ (Draft/Reviewing) | ✅ | ❌ | ❌ | ❌ |
| IMM Planning Officer | ✅ | ✅ (Benchmark fields) | ❌ | ❌ | ❌ | ❌ |
| IMM Risk Officer | ✅ | ✅ (Infra/Lock-in) | ❌ | ❌ | ❌ | ❌ |
| IMM Department Head | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| IMM Board Approver | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| IMM System Admin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

## II.2. IMM Market Benchmark

Naming: `MB-.YY.-.#####` · Submittable

| Field | Type | Required | Note |
|---|---|---|---|
| `spec_ref` | Link → IMM Tech Spec | Y | |
| `benchmark_date` | Date | Y | |
| `recommended_candidate` | Data | N (auto) | row name of top candidate |
| `weighting_scheme` | JSON | N | `{price:30, spec:40, support:20, brand:10}` |
| `candidates` | Table → Benchmark Candidate | Y | ≥ 3 candidates |

**Permissions (IMM Market Benchmark):**

| Role | Read | Write | Create | Submit |
|---|---|---|---|---|
| IMM HTM Engineer | ✅ | ✅ | ✅ | ❌ |
| IMM Planning Officer | ✅ | ✅ | ✅ | ✅ |
| IMM Department Head | ✅ | ❌ | ❌ | ❌ |
| IMM System Admin | ✅ | ✅ | ✅ | ✅ |

## II.3. IMM Lock-in Risk Assessment

Naming: `LR-.YY.-.#####` · Submittable

| Field | Type | Required | Permlevel | Note |
|---|---|---|---|---|
| `spec_ref` | Link → IMM Tech Spec | Y | 0 | |
| `assessment_date` | Date | Y | 0 | |
| `lock_in_score` | Float (auto) | — | **1** | weighted sum |
| `threshold_used` | Float | N | **1** | snapshot from master |
| `items` | Table → Lock-in Risk Item | Y | 0 | 5 dimensions |
| `mitigation_plan` | Long Text | Conditional | **1** | required if score > threshold |
| `mitigation_evidence` | Attach | Conditional | **1** | |

**Permissions (IMM Lock-in Risk Assessment):**

| Role | Read | Write | Create | Submit |
|---|---|---|---|---|
| IMM Risk Officer | ✅ | ✅ | ✅ | ✅ |
| IMM HTM Engineer | ✅ (permlevel 0 only) | ❌ | ❌ | ❌ |
| IMM Department Head | ✅ | ❌ | ❌ | ❌ |
| IMM Board Approver | ✅ (all permlevels) | ❌ | ❌ | ❌ |
| IMM System Admin | ✅ | ✅ | ✅ | ✅ |

## II.4. Child Tables

### Tech Spec Requirement

| Field | Type | Note |
|---|---|---|
| `seq` | Int | auto-increment |
| `group` | Select | Performance / Safety / Connectivity / Power / Mechanical / Software / Service / Compliance |
| `parameter` | Data | e.g. "Tidal Volume" |
| `value_or_range` | Data | e.g. "20–2000 mL" |
| `unit` | Data | mL |
| `is_mandatory` | Check | |
| `weight` | Int | 1–10 |
| `test_method` | Small Text | required if is_mandatory=1 (VR-02-03) |
| `evidence` | Attach | datasheet |
| `remark` | Small Text | |

### Benchmark Candidate

| Field | Type | Note |
|---|---|---|
| `manufacturer` | Data | |
| `model` | Data | |
| `country` | Data | |
| `spec_match_pct` | Percent | auto-computed |
| `price_estimate` | Currency | |
| `price_source` | Select | Vendor Quote / Public Tender / Web / Other |
| `support_tier` | Select | Tier1 / Tier2 / Tier3 |
| `local_partner` | Data | |
| `in_avl` | Check | link to IMM-03 AVL |
| `recommendation_score` | Float | auto-computed |
| `notes` | Small Text | |

### Infra Compatibility Item

| Field | Type | Note |
|---|---|---|
| `domain` | Select | Electrical / Medical Gas / Network/IT / HIS-PACS-LIS / HVAC / Space-Layout |
| `current_state` | Small Text | |
| `required_state` | Small Text | |
| `compatibility_status` | Select | Compatible / Need Upgrade / Need Major Upgrade / N/A |
| `upgrade_owner` | Link → User | |
| `upgrade_eta` | Date | |
| `upgrade_cost_estimate` | Currency | |
| `evidence` | Attach | |

### Lock-in Risk Item

| Field | Type | Note |
|---|---|---|
| `dimension` | Select | Protocol Standard / Consumable Source / Software License / Parts Source / Service Tooling |
| `score` | Int | 1–5 |
| `weight_pct` | Percent | auto from DEFAULT_WEIGHTS |
| `weighted` | Float | auto = score × weight_pct |
| `rationale` | Small Text | |
| `mitigation` | Small Text | |

### Tech Spec Document

| Field | Type | Note |
|---|---|---|
| `doc_type` | Select | Datasheet / HSMT Excerpt / Technical Drawing / Standard Reference / Other |
| `file_attachment` | Attach | |
| `version` | Data | |
| `issued_date` | Date | |

---

# Phần III — Service Layer

File: `assetcore/services/imm02.py` — **Đã implement đầy đủ.**

## III.1 Tech Spec lifecycle hooks

| Hook | Function | Mô tả |
|---|---|---|
| `before_insert` | `before_insert_tech_spec(doc)` | Set `draft_date = today()`, `version = "1.0"`, auto-fetch `device_category` từ IMM Device Model |
| `validate` | `validate_tech_spec(doc)` | Chạy VR-02-01..VR-02-05, rollup requirement counts, rollup infra_status_overall, check gates theo state |
| `before_submit` | `before_submit_tech_spec(doc)` | Validate G04 (lock-in check), set approval_date |
| `on_submit` | `on_submit_tech_spec(doc)` | Update Procurement Plan line status → "In Procurement", publish realtime `imm02_spec_locked` |

## III.2 Validation rules (VR)

| VR | Function | Logic |
|---|---|---|
| VR-02-01 | `_vr01_unique_per_plan_line` | 1 source_needs_request ↔ 1 Active Tech Spec (docstatus<1, state≠Withdrawn) |
| VR-02-02 | `_vr02_mandatory_min_count` | `requirements` phải có ≥ 1 dòng `is_mandatory=1` (chỉ enforce khi không rỗng) |
| VR-02-03 | `_vr03_test_method_present` | Mọi mandatory requirement phải có `test_method` không rỗng |
| VR-02-05 | `_vr05_infra_completeness` | 6/6 infra domains có `compatibility_status` (chỉ enforce khi state = Risk Assessed / Pending Approval / Locked) |

## III.3 Gates

| Gate | Function | Kích hoạt khi | Logic |
|---|---|---|---|
| G01 | `_validate_gate_g01` | state = "Reviewing" | ≥ 8 mandatory requirements, 100% có test_method |
| G02 | `_validate_gate_g02` | state = "Benchmarked" | `candidate_count ≥ 3` (từ `benchmark_ref` hoặc `doc.candidate_count`) |
| G03 | `_validate_gate_g03` | state = "Risk Assessed" | 6/6 infra domains có status |
| G04 | `_validate_gate_g04` | `before_submit` | `lock_in_score ≤ threshold` HOẶC có `mitigation_plan` + `mitigation_evidence` |

## III.4 Rollup functions

| Function | Mô tả |
|---|---|
| `_rollup_requirement_counts(doc)` | Tính `total_mandatory`, `total_optional`, auto-increment `seq` |
| `_rollup_infra_status(doc)` | Tính `infra_status_overall`: "All Compatible" / "Partial" / "Need Major Upgrade" |

## III.5 Market Benchmark

Function `validate_market_benchmark(doc)`:
- Parse `weighting_scheme` JSON (default: `{price:30, spec:40, support:20, brand:10}`)
- Tính `recommendation_score` cho mỗi candidate
- Chọn `recommended_candidate` = top scorer
- Sync `benchmark_ref` và `candidate_count` vào Tech Spec parent

Scoring formula: `score = spec*(w_spec/100) + price*(w_price/100) + support*(w_support/100) + brand*(w_brand/100)` × 5

## III.6 Lock-in Risk Assessment

Function `validate_lock_in_assessment(doc)`:
- Tính `lock_in_score = Σ (item.score × weight)` với DEFAULT_WEIGHTS:

| Dimension | Weight |
|---|---|
| `Protocol Standard` | 0.30 |
| `Consumable Source` | 0.20 |
| `Software License` | 0.20 |
| `Parts Source` | 0.15 |
| `Service Tooling` | 0.15 |

- Sync `lock_in_risk_ref`, `lock_in_score`, `mitigation_plan`, `mitigation_evidence` vào Tech Spec parent

## III.7 Versioning functions (via API layer)

| Function | Mô tả |
|---|---|
| `_reissue_spec(from_spec)` (trong `api/imm02.py`) | Copy doc, set `parent_spec`, bump version ("1.0"→"2.0"), reset approval/withdrawal fields, insert mới ở Draft |
| `_withdraw_spec(name, reason)` (trong `api/imm02.py`) | Validate state in [Pending Approval, Locked], set `withdrawal_reason`, submit nếu docstatus=0 |

## III.8 Schedulers

| Function | Tần suất | Logic |
|---|---|---|
| `check_overdue_drafts()` | Daily | Spec docstatus=0, state in [Draft, Reviewing, Benchmarked], > 30 ngày → log |
| `benchmark_freshness_alert()` | Weekly | Benchmark > 6 tháng (benchmark_date) → log |

---

# Phần IV — Controller Hooks

## IV.1. DocType files (thực tế)

| DocType | Controller file |
|---|---|
| `IMM Tech Spec` | `assetcore/assetcore/doctype/imm_tech_spec/imm_tech_spec.py` |
| `IMM Market Benchmark` | `assetcore/assetcore/doctype/imm_market_benchmark/imm_market_benchmark.py` |
| `IMM Lock-in Risk Assessment` | `assetcore/assetcore/doctype/imm_lock_in_risk_assessment/imm_lock_in_risk_assessment.py` |

Child table DocTypes (folder names):
- `tech_spec_requirement/`
- `tech_spec_document/`
- `benchmark_candidate/`
- `lock_in_risk_item/`

## IV.2. Hooks pattern

Controller gọi service theo pattern chuẩn AssetCore 3-tier:
- `IMM Tech Spec`: `before_insert` → `before_insert_tech_spec`, `validate` → `validate_tech_spec`, `before_submit` → `before_submit_tech_spec`, `on_submit` → `on_submit_tech_spec`
- `IMM Market Benchmark`: `validate` → `validate_market_benchmark`
- `IMM Lock-in Risk Assessment`: `validate` → `validate_lock_in_assessment`

---

# Phần V — Workflow Definition

## V.1. States (7)

| State | doc_status | Style | Allow Edit | Gate |
|---|---|---|---|---|
| `Draft` | 0 | success | HTM Engineer | — |
| `Reviewing` | 0 | warning | HTM Engineer / CMMS Admin | G01 (để vào) |
| `Benchmarked` | 0 | success | KH-TC Officer | G02 (để vào) |
| `Risk Assessed` | 0 | warning | QA Risk Team | G03 (để vào) |
| `Pending Approval` | 0 | warning | PTP Khối 1 | — |
| `Locked` | 1 | success | (read-only) | G04 (terminal +) |
| `Withdrawn` | 2 | danger | — | terminal − |

## V.2. Transitions (8)

| From | To | Action (Vietnamese) | Allowed Role | Gate |
|---|---|---|---|---|
| Draft | Reviewing | Gửi rà soát | IMM HTM Engineer | G01 |
| Reviewing | Draft | Yêu cầu chỉnh sửa | IMM HTM Engineer / IMM Planning Officer | — |
| Reviewing | Benchmarked | Hoàn tất benchmark | IMM Planning Officer | G02 |
| Benchmarked | Risk Assessed | Hoàn tất đánh giá rủi ro | IMM Risk Officer | G03 |
| Risk Assessed | Pending Approval | Trình duyệt | IMM Department Head | — |
| Pending Approval | Locked | Phê duyệt | IMM Board Approver | G04 |
| Pending Approval | Withdrawn | Rút hồ sơ | IMM Board Approver / IMM Department Head | — |
| Pending Approval | Risk Assessed | Yêu cầu đánh giá lại rủi ro | IMM Board Approver | — |

---

# Phần VI — Schedulers

| Job | Function | Tần suất | Cron | Logic |
|---|---|---|---|---|
| `check_overdue_drafts` | `assetcore.services.imm02.check_overdue_drafts` | Daily | — | Spec docstatus=0, > 30d Draft/Reviewing/Benchmarked → log |
| `benchmark_freshness_alert` | `assetcore.services.imm02.benchmark_freshness_alert` | Weekly | — | Benchmark > 6 tháng → log |

---

# Phần VII — Database Indexes

```sql
-- ⚠️ Pending implementation — Wave 2

-- IMM Tech Spec: filter by state + plan
CREATE INDEX idx_ts_state_plan
  ON `tabIMM Tech Spec` (workflow_state, source_plan);

-- IMM Tech Spec: versioning lookup
CREATE INDEX idx_ts_parent
  ON `tabIMM Tech Spec` (parent_spec);

-- IMM Tech Spec: device model lookup
CREATE INDEX idx_ts_device_model
  ON `tabIMM Tech Spec` (device_model_ref, workflow_state);

-- IMM Market Benchmark: spec lookup
CREATE INDEX idx_mb_spec
  ON `tabIMM Market Benchmark` (spec_ref);

-- IMM Lock-in Risk Assessment: spec lookup
CREATE INDEX idx_lr_spec
  ON `tabIMM Lock-in Risk Assessment` (spec_ref);

-- Tech Spec Requirement: filter mandatory
CREATE INDEX idx_tsr_mandatory
  ON `tabTech Spec Requirement` (parent, is_mandatory);
```
