# 04 — Backend Design — IMM-01 Đánh giá Nhu cầu & Dự toán

> **Wave 2 — Live.** BE service và API đã implement đầy đủ. Tài liệu này phản ánh code thực tế tại `assetcore/services/imm01.py` và `assetcore/api/imm01.py`.

| Mục | Giá trị |
|---|---|
| Module | IMM-01 — Đánh giá nhu cầu và dự toán |
| Liên kết | [02 Analysis](./02_Analysis_Design.md) · [03 Diagrams](./03_Diagrams.md) · [05 API](./05_API_Specification.md) |

---

## §I DocType Catalog

| DocType | Naming Series | Submittable | track_changes | Mục đích |
|---|---|---|---|---|
| `IMM Needs Request` | `NR-.YY.-.MM.-.#####` | Yes | Yes | Phiếu đề xuất nhu cầu thiết bị — nguồn nhập chính |
| `IMM Procurement Plan` | `PP-.YY.-.#####` | Yes | Yes | Gói đầu tư tổng hợp đã duyệt theo quý/năm |
| `IMM Demand Forecast` | `DF-.YYYY.-.#####` | No | No | Dự báo nhu cầu 3–5 năm auto-generated |
| `Needs Priority Scoring` | (child) | — | — | Lưới điểm 6 tiêu chí cho IMM Needs Request |
| `Budget Estimate Line` | (child) | — | — | Chi tiết dự toán CAPEX + OPEX 5y |
| `Procurement Plan Line` | (child) | — | — | 1 Needs Request trong Procurement Plan |
| `Forecast Driver` | (child) | — | — | Hệ số dự báo nhu cầu |

---

## §II DocType Schemas

### 2.1 IMM Needs Request

Naming: `NR-.YY.-.MM.-.#####`. Module: `AssetCore`. Submittable. track_changes=1.

| Section | Field | Fieldtype | Reqd | Default | Options / Link | Ghi chú |
|---|---|---|---|---|---|---|
| **Header** | request_id | Data | Y (auto) | — | — | Read-only naming |
| | request_date | Date | Y | today | — | Set in before_insert |
| | request_type | Select | Y | New | New\nReplacement\nUpgrade\nAdd-on | Drives VR-01-02 |
| | requesting_department | Link | Y | user dept | Department | — |
| | clinical_head | Link | Y | dept head | User | Auto-fetch |
| | workflow_state | Data | Y (auto) | Draft | — | Frappe workflow |
| **Target** | device_model_ref | Link | Y | — | IMM Device Model | Phải Active |
| | device_category | Link | N | fetch | Asset Category | Auto từ model |
| | quantity | Int | Y | 1 | — | min=1 |
| | target_year | Int | Y | year+1 | — | ≥ current year (VR-04) |
| | priority_class | Select | N (auto) | — | P1\nP2\nP3\nP4 | Auto từ weighted_score |
| **Justification** | clinical_justification | Long Text | Y | — | — | ≥ 200 chars (VR-03) |
| | replacement_for_asset | Link | C* | — | Asset | Bắt buộc khi type=Replacement |
| | utilization_pct_12m | Float | C | — | — | Auto-fetch từ IMM-07 |
| | downtime_hr_12m | Float | C | — | — | Auto-fetch từ IMM-07 |
| | compliance_driven | Check | N | 0 | — | Cờ từ IMM-10 |
| **Scoring** | weighted_score | Float | N (auto) | 0 | — | Auto-compute từ scoring_rows |
| | scoring_rows | Table | C | — | Needs Priority Scoring | 6 rows mandatory ở G02 |
| **Budget** | total_capex | Currency | N (auto) | — | — | Σ budget_lines (CAPEX) |
| | total_opex_5y | Currency | N (auto) | — | — | Σ budget_lines (OPEX) |
| | tco_5y | Currency | N (auto) | — | — | total_capex + total_opex_5y |
| | budget_lines | Table | C | — | Budget Estimate Line | ≥ 1 CAPEX + 5 OPEX years (G03) |
| | funding_source | Select | C | — | NSNN\nTài trợ\nXã hội hóa\nBHYT\nKhác | Bắt buộc trước Approved (G05) |
| | funding_evidence | Attach | N | — | — | Tài liệu cam kết nguồn vốn |
| **Approval** | board_approver | Link | C | — | User | Bắt buộc trước Approved (G05); permlevel 1 |
| | approval_date | Date | N (auto) | — | — | Set on_submit |
| | rejection_reason | Long Text | C | — | — | Bắt buộc khi Reject |
| **Linkage** | procurement_plan | Link | N | — | IMM Procurement Plan | Set khi gom vào plan |
| | tech_spec_ref | Link | N | — | IMM Tech Spec | Set khi IMM-02 generate |

**Permissions (permlevel 0 default; permlevel 1: funding_source, funding_evidence, board_approver):**

| Role | Read | Write | Create | Submit | Cancel | Permlevel 1 W |
|---|---|---|---|---|---|---|
| IMM Clinical User | own dept | own dept (Draft) | Y | — | — | — |
| IMM HTM Engineer | All | Reviewing | — | — | — | — |
| IMM Planning Officer | All | Prioritized | — | — | — | — |
| IMM Finance Officer | All | Budgeted | — | — | — | Y |
| IMM Department Head | All | Pending Approval | — | Y | Y | Y |
| IMM Board Approver | All | — | — | Y | Y | Y |
| IMM System Admin | All | All | Y | Y | Y | Y |

### 2.2 IMM Procurement Plan

Naming: `PP-.YY.-.#####`. Module: `AssetCore`. Submittable. track_changes=1.

| Section | Field | Fieldtype | Reqd | Ghi chú |
|---|---|---|---|---|
| **Header** | plan_period | Select | Y | Q1\nQ2\nQ3\nQ4\nAnnual |
| | plan_year | Int | Y | — |
| | budget_envelope | Currency | Y | Tổng cap được duyệt cho kỳ |
| | allocated_capex | Currency | N (auto) | Σ allocated_budget của plan_items |
| | utilization_pct | Percent | N (auto) | allocated / envelope |
| | workflow_state | Data | — | Draft\nApproved\nActive\nClosed |
| **Items** | plan_items | Table | Y | Procurement Plan Line |
| **Approval** | approved_by | Link | C | User |
| | approved_date | Date | N | Auto set on_submit |

**Permissions:**

| Role | Read | Write | Create | Submit |
|---|---|---|---|---|
| IMM Planning Officer | Y | Y | Y | — |
| IMM Department Head | Y | Y | — | Y |
| IMM Board Approver | Y | — | — | Y |
| IMM System Admin | Y | Y | Y | Y |

### 2.3 IMM Demand Forecast

Naming: `DF-.YYYY.-.#####`. Module: `AssetCore`. Read-only (không submittable).

| Field | Fieldtype | Reqd | Ghi chú |
|---|---|---|---|
| forecast_year | Int | Y | Năm bắt đầu dự báo |
| horizon_years | Int | Y | 3 hoặc 5 |
| device_category | Link | N | Asset Category; null = toàn danh mục |
| projected_qty | Int | N (auto) | Tổng số thiết bị dự kiến |
| projected_capex | Currency | N (auto) | Tổng CAPEX dự kiến |
| accuracy_prev | Percent | N | Đối chiếu kỳ trước |
| drivers | Table | Y | Forecast Driver |
| generated_at | Datetime | Y (auto) | Auto timestamp |
| generated_by | Link | Y (auto) | scheduler user |

### 2.4 Child Table: Needs Priority Scoring

| Field | Fieldtype | Reqd | Ghi chú |
|---|---|---|---|
| criterion | Select | Y | clinical_impact\nrisk\nutilization_gap\nreplacement_signal\ncompliance_gap\nbudget_fit |
| score | Int | Y | 1–5 |
| weight_pct | Percent | N (auto) | Fetch từ master config |
| weighted | Float | N (auto) | score × weight |
| evidence | Long Text | N | Lý giải điểm |

### 2.5 Child Table: Budget Estimate Line

| Field | Fieldtype | Reqd | Ghi chú |
|---|---|---|---|
| budget_section | Select | Y | CAPEX\nOPEX |
| line_type | Select | Y | Device\nInstall\nTraining\nInfra\nAccessory\nPM\nCalibration\nSpare\nConsumable\nSoftware\nInsurance\nOther |
| year_offset | Int | Y | 0 = năm mua; 1–5 = OPEX years |
| qty | Float | Y | — |
| unit_cost | Currency | Y | — |
| amount | Currency | N (auto) | qty × unit_cost |
| benchmark_source | Data | N | Tham chiếu thị trường |
| notes | Small Text | N | — |

### 2.6 Child Table: Procurement Plan Line

| Field | Fieldtype | Reqd | Ghi chú |
|---|---|---|---|
| needs_request | Link | Y | IMM Needs Request |
| priority_rank | Int | N (auto) | Sort by weighted_score desc |
| allocated_budget | Currency | Y | — |
| target_quarter | Select | N | Q1\nQ2\nQ3\nQ4 |
| status | Select | N | Pending Spec\nIn Spec\nIn Procurement\nAwarded\nCancelled |

### 2.7 Child Table: Forecast Driver

| Field | Fieldtype | Reqd | Ghi chú |
|---|---|---|---|
| driver_type | Select | Y | replacement\nutilization_growth\nservice_expansion\ncompliance\nstrategic |
| weight_pct | Percent | Y | — |
| projected_value | Float | Y | — |
| source_module | Data | N | IMM-07 / IMM-13 / IMM-10 |

---

## §III Service Layer

File: `assetcore/services/imm01.py` — **Đã implement đầy đủ.**

### Lifecycle hooks (gọi từ controller)

| Hook | Function | Mô tả |
|---|---|---|
| `before_insert` | `before_insert_needs_request(doc)` | Set `request_date = today()`, auto-fetch `clinical_head` từ AC Department, auto-fetch replacement metrics nếu type=Replacement/Upgrade |
| `validate` | `validate_needs_request(doc)` | Chạy VR-01-01..VR-05, tính priority score, rollup budget, check gates theo state |
| `before_submit` | `before_submit_needs_request(doc)` | Validate G05 (board_approver + funding_source), set approval_date |
| `on_submit` | `on_submit_needs_request(doc)` | Ghi IMM Audit Trail (event_type=System) nếu có replacement_for_asset |
| `on_cancel` | `on_cancel_needs_request(doc)` | Ghi IMM Audit Trail Cancelled |

### Audit trail

Function `write_audit_trail(doc, event_type, from_status, to_status, notes)`:
- Chỉ ghi khi phiếu có `replacement_for_asset` (pre-asset stage dùng Frappe Version track_changes).
- Tạo record `IMM Audit Trail` với `event_type = "System"`.

### Validation rules (VR)

| VR | Function | Logic |
|---|---|---|
| VR-01-01 | `_vr01_unique_active_request_per_asset` | 1 Asset chỉ có 1 active Replacement NR (docstatus<1, state not in Approved/Rejected) |
| VR-01-02 | `_vr02_replacement_requires_decom_plan` | Replacement → soft warn nếu asset không ở Pending Decommission/Decommissioned (IMM-13 chưa LIVE) |
| VR-01-04 | `_vr04_target_year` | `target_year ≥ current_year` |
| VR-01-05 | `_vr05_score_consistency` | `abs(weighted_score - Σ scoring_rows.weighted) < 0.01` |

### Priority scoring

Function `_compute_priority_score(doc)`:
- Trọng số mặc định (6 tiêu chí, tổng = 1.0):

| Criterion | Weight |
|---|---|
| `clinical_impact` | 0.25 |
| `risk` | 0.20 |
| `utilization_gap` | 0.15 |
| `replacement_signal` | 0.15 |
| `compliance_gap` | 0.15 |
| `budget_fit` | 0.10 |

- `priority_class`: P1 ≥ 4.0, P2 ≥ 3.0, P3 ≥ 2.0, P4 > 0.

### Budget rollup

Function `_rollup_budget(doc)`:
- Tính `total_capex = Σ budget_lines[section=CAPEX].amount`
- Tính `total_opex_5y = Σ budget_lines[section=OPEX].amount`
- `tco_5y = total_capex + total_opex_5y`

### Gates

| Gate | Kích hoạt khi | Logic |
|---|---|---|
| G01 | state = "Reviewing" | `utilization_pct_12m` bắt buộc với Replacement/Upgrade |
| G02 | state = "Prioritized" | Đủ 6/6 scoring rows (đủ 6 criterion keys) |
| G03 | state = "Budgeted" | `total_capex > 0` + OPEX có đủ year_offset 1..5 |
| G04 | state = "Budgeted" | Soft check (envelope validation cross-doc) — hiện chỉ sanity check |
| G05 | before_submit | `funding_source` + `board_approver` bắt buộc |

### Procurement Plan functions

| Function | Mô tả |
|---|---|
| `validate_procurement_plan(doc)` | Rollup `allocated_capex`, tính `utilization_pct`, rank plan_items by weighted_score desc |
| `on_submit_procurement_plan(doc)` | Cập nhật link `procurement_plan` trên NR, ghi audit trail |
| `roll_into_plan(plan_year, plan_period, needs_requests)` | Gom Approved NR vào Plan (tạo mới hoặc append); chỉ chấp nhận NR docstatus=1, state=Approved |

### Schedulers

| Function | Tần suất | Logic |
|---|---|---|
| `generate_demand_forecast()` | Monthly | Tạo `IMM Demand Forecast` skeleton cho mỗi AC Asset Category (placeholder — wire với IMM-07/IMM-13 sau) |
| `check_pending_request_overdue()` | Daily | NR ở Submitted/Reviewing > 30 ngày → log (email TODO) |
| `budget_envelope_alert()` | Weekly | Plan vượt 80% envelope → log warning |

---

## §IV Controller Hooks

File: `assetcore/assetcore/doctype/imm_needs_request/imm_needs_request.py` — **Đã implement.**

Controller gọi thẳng vào service layer theo pattern chuẩn AssetCore:
- `before_insert` → `before_insert_needs_request(self)`
- `validate` → `validate_needs_request(self)`
- `before_submit` → `before_submit_needs_request(self)`
- `on_submit` → `on_submit_needs_request(self)`
- `on_cancel` → `on_cancel_needs_request(self)`

DocType folder: `assetcore/assetcore/doctype/imm_needs_request/`
Child table DocType: `needs_priority_scoring` (folder `needs_priority_scoring/`)

---

## §V Workflow

### 5.1 States

| State | doc_status | Badge type | Allow Edit | Gate |
|---|---|---|---|---|
| Draft | 0 | Success | IMM Clinical User | — |
| Submitted | 0 | Warning | IMM HTM Engineer, IMM Planning Officer | G01 |
| Reviewing | 0 | Warning | IMM HTM Engineer | — |
| Prioritized | 0 | Success | IMM Finance Officer | G02 |
| Budgeted | 0 | Success | IMM Department Head | G03 + G04 |
| Pending Approval | 0 | Warning | IMM Board Approver | — |
| Approved | 1 | Success | (read-only) | G05 (terminal positive) |
| Rejected | 1 | Danger | (read-only) | terminal negative |

### 5.2 Transition Matrix

| From → To | Action (vi) | Allowed Role | Gate |
|---|---|---|---|
| Draft → Submitted | Gửi đề xuất | IMM Clinical User | G01 check |
| Submitted → Reviewing | Tiếp nhận rà soát | IMM HTM Engineer, IMM Planning Officer | — |
| Submitted → Draft | Yêu cầu bổ sung | IMM HTM Engineer | — |
| Reviewing → Prioritized | Hoàn tất chấm điểm | IMM Planning Officer | G02 |
| Reviewing → Rejected | Bác đề xuất (sớm) | IMM Department Head | — |
| Prioritized → Budgeted | Lập dự toán xong | IMM Finance Officer | G03 + G04 |
| Budgeted → Pending Approval | Trình BGĐ | IMM Department Head | — |
| Pending Approval → Approved | Phê duyệt | IMM Board Approver | G05 |
| Pending Approval → Rejected | Từ chối | IMM Board Approver | rejection_reason required |
| Pending Approval → Budgeted | Yêu cầu chỉnh dự toán | IMM Board Approver | — |

---

## §VI Schedulers

| Job | File | Tần suất | Mô tả | Recipient |
|---|---|---|---|---|
| `check_pending_request_overdue` | `assetcore/services/imm01.py` | Daily | NR ở Submitted/Reviewing > 30 ngày → log (email TODO) | PTP Khối 1, KH-TC Officer |
| `budget_envelope_alert` | `assetcore/services/imm01.py` | Weekly | Plan vượt 80% envelope → log warning | PTP Khối 1, TCKT Head |
| `generate_demand_forecast` | `assetcore/services/imm01.py` | Monthly | Tạo `IMM Demand Forecast` skeleton / device_category (wire IMM-07/13 sau) | KH-TC Officer |

---

## §VII Database Indexes

| Index | DocType | SQL |
|---|---|---|
| `idx_nr_state_dept` | `IMM Needs Request` | `CREATE INDEX idx_nr_state_dept ON \`tabIMM Needs Request\` (workflow_state, requesting_department);` |
| `idx_nr_replacement` | `IMM Needs Request` | `CREATE INDEX idx_nr_replacement ON \`tabIMM Needs Request\` (replacement_for_asset);` |
| `idx_nr_plan` | `IMM Needs Request` | `CREATE INDEX idx_nr_plan ON \`tabIMM Needs Request\` (procurement_plan);` |
| `idx_pp_year_period` | `IMM Procurement Plan` | `CREATE INDEX idx_pp_year_period ON \`tabIMM Procurement Plan\` (plan_year, plan_period);` |
| `idx_df_year_cat` | `IMM Demand Forecast` | `CREATE INDEX idx_df_year_cat ON \`tabIMM Demand Forecast\` (forecast_year, device_category);` |
