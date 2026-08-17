# 04 — Backend Design — IMM-01 Đánh giá Nhu cầu & Dự toán

> **Wave 2 — Live.** BE service và API đã implement đầy đủ. Tài liệu này phản ánh code thực tế tại `assetcore/services/imm01.py` và `assetcore/api/imm01.py`.

| Mục | Giá trị |
|---|---|
| Module | IMM-01 — Đánh giá nhu cầu và dự toán |
| Cập nhật | 2026-07-14 (thêm §5.4 Workflow-Surface Integrity + ADR-IMM-01-03) |
| Liên kết | [02 Analysis](./02_Analysis_Design.md) · [03 Diagrams](./03_Diagrams.md) · [05 API](./05_API_Specification.md) · [07 Testing §III.4a](./07_Testing_QA.md) |

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

Naming: `NR-.YY.-.MM.-.#####`. Module: `AssetCore`. Submittable. track_changes=1. title_field=`device_model_ref`.

| Section | Field | Fieldtype | Reqd | Default | Options / Link | Ghi chú |
|---|---|---|---|---|---|---|
| **Header** | naming_series | Select | Y | `NR-.YY.-.MM.-.#####` | — | Naming series chuẩn |
| | request_date | Date | Y | Today | — | Service đảm bảo set ở `before_insert_needs_request` nếu trống |
| | request_type | Select | Y | New | `New\nReplacement\nUpgrade\nAdd-on` | Drives VR-01-01/02 |
| | requesting_department | Link | Y | — | `AC Department` | — |
| | clinical_head | Link | N (auto) | — | `User` | `fetch_from = requesting_department.dept_head`; service force-overwrite (`_sync_clinical_head_from_department`) — user KHÔNG được tự nhập |
| | workflow_state | Link | N (auto) | Draft | `Workflow State` | — |
| | priority_class | Select | N (auto) | — | `P1\nP2\nP3\nP4` | Tính bởi `_classify_priority` |
| **Target** | device_category | Link | **Y** | — | `AC Asset Category` | **Bắt buộc** — `_validate_device_target()` raise nếu trống (Wave 2, 2026-05-16) |
| | device_model_ref | Link | **N** | — | `IMM Device Model` | **Tùy chọn** — nếu có, service tự fill `device_category` từ model; Model thường chốt sau ở IMM-02 |
| | quantity | Int | Y | 1 | — | — |
| | target_year | Int | Y | — | — | VR-01-04: ≥ năm hiện tại |
| | weighted_score | Float | N (auto) | — | precision=4 | Auto-compute từ scoring_rows |
| **Justification** | clinical_justification | Long Text | Y | — | — | `reqd:1` ở DocType; **VR-01-03**: phải ≥ 200 ký tự khi rời Draft → Reviewing (Wave 2) |
| | replacement_for_asset | Link | conditional | — | `AC Asset` | `mandatory_depends_on: doc.request_type=='Replacement'` |
| | utilization_pct_12m | Percent | N | — | — | Auto-fetch từ IMM-07 (chưa wire) |
| | downtime_hr_12m | Float | N | — | — | Auto-fetch từ IMM-07 (chưa wire) |
| | compliance_driven | Check | N | 0 | — | Cờ từ IMM-10 (chưa wire) |
| **Scoring** | scoring_rows | Table | N | — | `Needs Priority Scoring` | Đủ 6 criterion keys khi G02 |
| **Budget** | budget_lines | Table | N | — | `Budget Estimate Line` | CAPEX > 0 + OPEX year_offset 1..5 khi G03 |
| | total_capex | Currency | N (auto) | — | — | Σ CAPEX (`_rollup_budget`) |
| | total_opex_5y | Currency | N (auto) | — | — | Σ OPEX |
| | tco_5y | Currency | N (auto) | — | — | total_capex + total_opex_5y |
| **Funding** (permlevel 1) | funding_source | Select | N | — | `NSNN\nTài trợ\nXã hội hóa\nBHYT\nKhác` | Bắt buộc trước Submit (G05) |
| | funding_evidence | Attach | N | — | — | permlevel 1 |
| | board_approver | Link | N | — | `User` | Bắt buộc trước Submit (G05); permlevel 1 |
| | approval_date | Date | N (auto) | — | — | Set ở `before_submit` nếu trống; permlevel 1; read_only |
| | rejection_reason | Long Text | N | — | — | Bắt buộc khi gọi `reject_needs_request`; permlevel 1 |
| **Linkage** | procurement_plan | Link | N (auto) | — | `IMM Procurement Plan` | Set ở `on_submit_procurement_plan` |
| | tech_spec_ref | Data | N | — | — | Placeholder vì IMM-02 DocType riêng — hiện là free-text Data (sẽ chuyển Link khi IMM-02 GA) |
| | amended_from | Link | N | — | `IMM Needs Request` | Standard Frappe amend |

**Permissions (từ DocType JSON):**

| Role | Permlevel 0 (Read/Write/Create/Submit/Cancel/Amend/Delete) | Permlevel 1 (Read/Write) |
|---|---|---|
| IMM System Admin | R/W/C/S/Cn/A/D | R/W |
| IMM Clinical User | R/W/C | — |
| IMM HTM Engineer | R/W | — |
| IMM Planning Officer | R/W | — |
| IMM Finance Officer | R/W | R/W |
| IMM Department Head | R/W/S/Cn | R/W |
| IMM Board Approver | R/W/S/Cn | R/W |
| IMM Auditor | R + Report + Export | — |

> Row-level filtering (Clinical User chỉ thấy NR khoa mình) chưa được cài đặt qua `permission_query_conditions` — hiện DocPerm cấp module-wide. Roadmap.

### 2.2 IMM Procurement Plan

Naming: `PP-.YY.-.#####`. Module: `AssetCore`. Submittable. track_changes=1.

| Section | Field | Fieldtype | Reqd | Ghi chú |
|---|---|---|---|---|
| **Header** | naming_series | Select | Y | `PP-.YY.-.#####` |
| | plan_period | Select | Y | `Q1\nQ2\nQ3\nQ4\nAnnual`, default `Annual` |
| | plan_year | Int | Y | — |
| | workflow_state | Link | N (auto) | `Workflow State`, default `Draft`. States: Draft → Approved → Active → Closed |
| | approved_by | Link | N | `User` (set ở `approve_plan`) |
| | approved_date | Date | N (auto) | Set ở `approve_plan` (today) |
| **Envelope** | budget_envelope | Currency | Y | — |
| | allocated_capex | Currency | N (auto) | `_rollup_plan_capex` Σ plan_items.allocated_budget |
| | utilization_pct | Percent | N (auto) | allocated / envelope × 100 |
| **Items** | plan_items | Table | N | `Procurement Plan Line` |
| | amended_from | Link | N | `IMM Procurement Plan` |

**Permissions:**

| Role | Read | Write | Create | Submit | Cancel |
|---|---|---|---|---|---|
| IMM System Admin | Y | Y | Y | Y | Y |
| IMM Planning Officer | Y | Y | Y | — | — |
| IMM Department Head | Y | Y | — | Y | Y |
| IMM Board Approver | Y | — | — | Y | Y |
| IMM Finance Officer | Y | — | — | — | — |
| IMM HTM Engineer | Y | — | — | — | — |
| IMM Auditor | Y + Export + Report | — | — | — | — |

### 2.3 IMM Demand Forecast

Naming: `DF-.YYYY.-.#####`. Module: `AssetCore`. Không submittable. track_changes=1.

| Field | Fieldtype | Reqd | Ghi chú |
|---|---|---|---|
| naming_series | Select | Y | `DF-.YYYY.-.#####` |
| forecast_year | Int | Y | — |
| horizon_years | Int | Y | default 5 |
| device_category | Link | N | `AC Asset Category` |
| generated_at | Datetime | N (auto) | Set ở `generate_demand_forecast` |
| generated_by | Link | N (auto) | `User`, set "Administrator" trong scheduler hiện tại |
| projected_qty | Int | N | Placeholder 0 (TODO: wire IMM-07 + IMM-13) |
| projected_capex | Currency | N | Placeholder 0 |
| accuracy_prev | Percent | N | Đối chiếu kỳ trước (chưa tính tự động) |
| drivers | Table | N | `Forecast Driver` |

### 2.4 Child Table: Needs Priority Scoring

| Field | Fieldtype | Reqd | Ghi chú |
|---|---|---|---|
| criterion | Select | Y | `clinical_impact\nrisk\nutilization_gap\nreplacement_signal\ncompliance_gap\nbudget_fit` |
| score | Int | Y | Thang 1–5 |
| weight_pct | Percent | N (auto) | Tính từ `DEFAULT_PRIORITY_WEIGHTS` × 100; master config "IMM Priority Weight" = placeholder, chưa tạo DocType |
| weighted | Float | N (auto) | `score × weight`, precision=4 |
| evidence | Long Text | N | Lý giải điểm |

### 2.5 Child Table: Budget Estimate Line

| Field | Fieldtype | Reqd | Ghi chú |
|---|---|---|---|
| budget_section | Select | Y | CAPEX\nOPEX |
| line_type | Select | Y | Device\nInstall\nTraining\nInfra\nAccessory\nPM\nCalibration\nSpare\nConsumable\nSoftware\nInsurance\nOther |
| year_offset | Int | N | 0 = năm mua; 1–5 = OPEX years; G03 validate có đủ year_offset 1..5 trong service |
| qty | Float | N | Số lượng (service dùng `or 0` khi tính amount) |
| unit_cost | Currency | Y | — |
| amount | Currency | N (auto) | qty × unit_cost — tính bởi `_rollup_budget` |
| benchmark_source | Data | N | Tham chiếu thị trường |
| notes | Small Text | N | — |

### 2.6 Child Table: Procurement Plan Line

| Field | Fieldtype | Reqd | Ghi chú |
|---|---|---|---|
| needs_request | Link | Y | `IMM Needs Request` |
| priority_rank | Int | N (auto) | Sort by `weighted_score` desc trong `_rollup_plan_capex` |
| weighted_score | Float | N (auto) | Copy từ NR khi `roll_into_plan` |
| allocated_budget | Currency | Y | — |
| target_quarter | Select | N | `Q1\nQ2\nQ3\nQ4` |
| status | Select | N | `Pending Spec\nIn Spec\nIn Procurement\nAwarded\nCancelled`, default `Pending Spec` |

### 2.7 Child Table: Forecast Driver

| Field | Fieldtype | Reqd | Ghi chú |
|---|---|---|---|
| driver_type | Select | Y | `replacement\nutilization_growth\nservice_expansion\ncompliance\nstrategic` |
| weight_pct | Percent | N | — |
| projected_value | Float | N | — |
| source_module | Data | N | VD: `IMM-07`, `IMM-13`, `IMM-10`, `Manual` |

---

## §III Service Layer

File: `assetcore/services/imm01.py` — **Đã implement đầy đủ.**

### Lifecycle hooks (gọi từ controller)

| Hook | Function | Mô tả |
|---|---|---|
| `before_insert` | `before_insert_needs_request(doc)` | Set `request_date = today()`, auto-fetch `clinical_head` từ AC Department, auto-fetch replacement metrics nếu type=Replacement/Upgrade |
| `validate` | `validate_needs_request(doc)` | Gọi tuần tự: `_sync_clinical_head_from_department` → `_validate_device_target` → `_vr04_target_year` → `_vr01_unique_active_request_per_asset` → `_vr02_replacement_requires_decom_plan` → VR-01-05, priority score, budget rollup, check gates |
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
| VR-01-00 | `_validate_device_target` | `device_category` bắt buộc; nếu `device_model_ref` có → auto-fill `device_category` từ model. Raise `ServiceError(VALIDATION)` nếu `device_category` vẫn trống. (Wave 2) |
| VR-01-01 | `_vr01_unique_active_request_per_asset` | 1 Asset chỉ có 1 active Replacement NR (docstatus<1, state not in Approved/Rejected) |
| VR-01-02 | `_vr02_replacement_requires_decom_plan` | Replacement → kiểm tra `AC Asset.imm_lifecycle_status` ∈ {Decommissioned, Pending Decommission}. Hiện **soft warn (msgprint orange)**, KHÔNG block; sẽ đổi thành ServiceError khi IMM-13 LIVE |
| VR-01-03 | `_validate_gate_g01` → inline | **`clinical_justification` ≥ 200 ký tự** khi rời Draft → Reviewing (Wave 2, 2026-05-16). Hằng số `_VR0103_MIN_CHARS = 200`. |
| VR-01-04 | `_vr04_target_year` | `target_year ≥ current_year`; raise `ServiceError(VALIDATION)` |
| VR-01-05 | `_vr05_score_consistency` | `abs(weighted_score - Σ scoring_rows.weighted) < 0.01` |

> VR-01-03 **đã được enforce** trong `_validate_gate_g01` kể từ Wave 2 (commit `41fabd8`). VR-01-06 (audit trail bất biến) vẫn tại DocPerm cấp `IMM Audit Trail`.

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
| G01 | target state = "Reviewing" (kiểm tra trong `validate_needs_request` → `_check_workflow_gates`) | `utilization_pct_12m is not None` bắt buộc khi `request_type ∈ {Replacement, Upgrade}` |
| G02 | target state = "Prioritized" | Đủ 6/6 criterion keys: `clinical_impact, risk, utilization_gap, replacement_signal, compliance_gap, budget_fit` |
| G03 | target state = "Budgeted" | `total_capex > 0` + OPEX có đủ `year_offset` 1,2,3,4,5 |
| G04 | target state = "Budgeted" | Soft check: hiện chỉ return (placeholder). Envelope rollup thực hiện ở `_rollup_plan_capex` (Procurement Plan side) |
| G05 | `before_submit_needs_request` | `funding_source` + `board_approver` bắt buộc |

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
| `check_pending_request_overdue()` | Daily | NR ở Submitted/Reviewing (docstatus=0) > 30 ngày → gọi `notifications.notify_needs_overdue(rows)` (E7): escalation **digest** in-app + email tới role `Needs Manager` (SSoT `notify_roles.NEEDS_STALE_ESCALATION`). Giữ early-return `if not rows` (0 phiếu → 0 thông báo). Xem ADR-IMM-01-01 + BR-01-11. |
| `budget_envelope_alert()` | Weekly | Plan vượt 80% envelope → log warning |

**Notification helpers (E7 — trong `services/notifications.py`, framework IMM-00):**

| Function | Signature | Vai trò |
|---|---|---|
| `notify_needs_overdue` | `(overdue_rows: list[dict]) -> None` | Entry E7 do `check_pending_request_overdue` gọi. Resolve recipient qua `_needs_stale_recipients()`; dựng subject + message digest (tổng số phiếu + breakdown theo `requesting_department`, tiếng Việt đầy đủ); lọc recipient đã nhận digest hôm nay (`_needs_digest_already_sent`); `_dispatch` cho phần còn lại. 0 phiếu → không được gọi (early-return ở scheduler); 0 recipient → log warning, không dispatch. |
| `_needs_stale_recipients` | `() -> list[str]` | Union `get_users_with_role(r)` cho mọi `r ∈ notify_roles.NEEDS_STALE_ESCALATION`; loại Administrator + rỗng + dedupe. Rỗng → `frappe.logger("imm01").warning(...)` (anti dead-gate) + trả `[]`. |
| `_needs_digest_already_sent` | `(user: str) -> bool` | True nếu đã có Notification Log `for_user=user` + subject chứa marker NR-quá-hạn + `DATE(creation)=CURDATE()` (dedup 1 digest/recipient/ngày, Frappe-first — pattern `_warning_already_sent`). |

> **SSoT `notify_roles`**: thêm `NEEDS_STALE_ESCALATION: list[str] = ["Needs Manager"]` (map persona *PTP Khối 1 / Quản lý Nhu cầu* → role thật) và cộng vào `ALL_NOTIFY_ROLES` để guard `test_notify_roles_exist` phủ. KHÔNG literal role-name ở call-site.

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

Có **2 workflow** trong `assetcore/assetcore/workflow/`:
- `IMM-01 Needs Workflow` — 8 states, áp dụng cho `IMM Needs Request`, dùng `frappe.model.workflow.apply_workflow` qua endpoint `transition_workflow`.
- `IMM-01 Plan Workflow` — 4 states, áp dụng cho `IMM Procurement Plan`. **KHÔNG dùng `apply_workflow`**: state transitions được quản lý bằng các dedicated endpoint (`approve_plan`, `activate_plan`, `close_plan`) trong `api/imm01.py` — chúng set `workflow_state` trực tiếp + `doc.save()` (không submit/docstatus change).

### 5.1 Needs Workflow — States (fixture `imm_01_needs_workflow.json`)

| State | doc_status | allow_edit role | Gate kích hoạt |
|---|---|---|---|
| Draft | 0 | IMM Clinical User | — |
| Submitted | 0 | IMM HTM Engineer | — |
| Reviewing | 0 | IMM HTM Engineer | G01 (validate khi vào state) |
| Prioritized | 0 | IMM Planning Officer | G02 |
| Budgeted | 0 | IMM Finance Officer | G03 + G04 (soft) |
| Pending Approval | 0 | IMM Department Head | — |
| Approved | 1 | IMM System Admin | G05 (ở `before_submit`) |
| Rejected | 1 | IMM System Admin | — |

### 5.2 Needs Workflow — Transitions (trích lược từ fixture)

| From → To | Action | Allowed Role(s) | Gate |
|---|---|---|---|
| Draft → Submitted | Gửi đề xuất | IMM Clinical User · IMM Department Head · IMM System Admin | — |
| Submitted → Reviewing | Tiếp nhận rà soát | IMM HTM Engineer · IMM Planning Officer | G01 |
| Submitted → Draft | Yêu cầu bổ sung | IMM HTM Engineer | — |
| Reviewing → Prioritized | Hoàn tất chấm điểm | IMM Planning Officer | G02 |
| Reviewing → Rejected | Bác sớm | IMM Department Head | — |
| Prioritized → Budgeted | Lập dự toán xong | IMM Finance Officer | G03 |
| Budgeted → Pending Approval | Trình BGĐ | Needs Manager · Super Admin | — |
| Pending Approval → Approved | **Phê duyệt** | **Procurement Manager · AssetCore Super Admin · System Manager** | doc.submit() + audit |
| Pending Approval → Rejected | **Bác đề xuất** | **Procurement Manager · AssetCore Super Admin · System Manager** | rejection_reason required (endpoint) |
| Pending Approval → Budgeted | Yêu cầu chỉnh dự toán | Procurement Manager · AssetCore Super Admin · System Manager | — |

> ⚠️ Các nhãn role "IMM Board Approver" / "IMM Department Head" / "IMM Clinical User" ở bảng trên (các dòng chưa in đậm) là **nhãn nghiệp vụ cũ** — role thật trong `fixtures/workflow.json` là role chuẩn AssetCore (`Needs Manager`, `Spec Manager`, `Procurement Manager`, `Corrective User`, `AssetCore Super Admin`, `System Manager`). SSoT role↔transition = `07_Testing_QA.md` §III.4 (Integration — Workflow transitions) + `fixtures/workflow.json`. Ba dòng `Pending Approval` đã được cập nhật đúng role thật (load-bearing cho ADR-IMM-01-02).

> **Approve/Reject (`approve_needs_request` / `reject_needs_request`)** — set `board_approver`/`rejection_reason` + `workflow_state` (Approved/Rejected) + `doc.submit()` trong 1 endpoint (KHÔNG qua `apply_workflow`). Cơ chế enforce role: `doc.submit()` chạy `frappe.model.document.validate_workflow` → nếu user KHÔNG có role trong `allowed` của transition, Frappe ném `WorkflowPermissionError` (subclass `ValidationError`, kèm HTML `<strong>`). Handler PHẢI bọc `doc.submit()` bắt `WorkflowPermissionError` → `ServiceError(FORBIDDEN)` **thông điệp VI sạch, KHÔNG leak `<strong>`** (đối xứng `_save_plan_workflow_transition` đã dùng cho Plan). Xem §5.2a + ADR-IMM-01-02 (`02_Analysis_Design.md` §IV.2b).

### 5.2a Server-driven CTA gating cho Needs Request (GATE-8 / LL-FE-51)

Đối xứng với Procurement Plan (`_plan_allowed_transition_actions`):

- **BE — helper `_nr_allowed_transition_actions(doc) -> list[str]`**: gọi `frappe.model.workflow.get_transitions(doc)` (đã lọc theo state hiện tại + role của user gọi), dedupe theo `action`, trả list action-string. Bọc `try/except Exception → []` (degrade graceful: user chỉ có base role `AssetCore System User` không đọc được doc → 0 nút thay vì vỡ payload bằng 403/500 — `get_transitions` read-only, KHÔNG nuốt lỗi ghi/DB).
- **`get_needs_request` (`_get_needs_request`)** thêm field `allowed_transitions = _nr_allowed_transition_actions(doc)` vào payload `data` → FE gate nút **không cần call thứ 2** (`get_allowed_transitions` giữ nguyên cho các nút generic khác nếu FE muốn, nhưng approve/reject gate theo field embed → không flash ẩn/hiện nút lúc render đầu).
- **Invariant**: với NR ở `Pending Approval`, user role `Procurement Manager` (KHÔNG kèm role khác) → `allowed_transitions` chứa `"Phê duyệt"`, `"Bác đề xuất"`, `"Yêu cầu chỉnh dự toán"`. User KHÔNG có role duyệt (vd chỉ `Needs Manager`) → 2 action này KHÔNG có trong list ⇒ FE ẩn nút (không false-permissive).

**Boundary — 2 loại 403 (DONE-gate spec-contract):**
- **dispatcher-403** (guest / no-token): Frappe từ chối trước khi vào handler — KHÔNG phải envelope.
- **in-handler cap-403**: approve/reject bởi user thiếu role duyệt → handler trả **HTTP-200 + Error envelope** `{success:false, code:"FORBIDDEN"}` (in-handler show-msg), KHÔNG raise→HTTP-4xx. FE render message VI, giữ nguyên state.

### 5.3 Plan Workflow — States (fixture `imm_01_plan_workflow.json`)

| State | doc_status | Endpoint chuyển state |
|---|---|---|
| Draft | 0 | (create) |
| Approved | 1 | `approve_plan` (set workflow_state + approved_by + approved_date, save) |
| Active | 1 | `activate_plan` |
| Closed | 1 | `close_plan` |

> Plan workflow fixture cũng có action "Phê duyệt kế hoạch", "Kích hoạt", "Đóng kế hoạch" — nhưng **code sử dụng dedicated endpoints**, không `apply_workflow`. Fixture giữ để Frappe UI Workflow Dashboard nhận diện states.

### 5.4 INVARIANT — Workflow-Surface Integrity (CR-WF-01-SURFACE · silent-CTA-loss guard)

**Bối cảnh (silent-CTA-loss).** IMM-01 có **2 surface** server-driven CTA gating (khác IMM-04 chỉ 1): `_nr_allowed_transition_actions(doc)` (`api/imm01.py:187`, embed vào payload `get_needs_request` @:225) và `_plan_allowed_transition_actions(doc)` (`api/imm01.py:476`, embed vào payload `get_procurement_plan` @:510). Cả hai gọi `frappe.model.workflow.get_transitions(doc)` trong khối `try … except Exception: return []`:

```python
# api/imm01.py:29-30 (ground truth — CR này KHÔNG được sửa)
_DT_NR = "IMM Needs Request"        # == workflow.document_type (Needs)
_DT_PP = "IMM Procurement Plan"     # == workflow.document_type (Plan)

# api/imm01.py:187-217 / :476-506 (đối xứng)
def _nr_allowed_transition_actions(doc) -> list[str]:
    from frappe.model.workflow import get_transitions
    try:
        transitions = get_transitions(doc) or []   # ← resolve theo document_type
    except Exception:
        return []                                   # ← silent CTA loss
    ...  # dedupe theo action → list[str]
```

**Cơ chế resolve (KHÁC IMM-04 — grounded `frappe/model/workflow.py`).** Surface IMM-01 **KHÔNG** hardcode hằng-lookup `get_doc("Workflow", "<literal>")` như IMM-04. `get_transitions(doc)` → `get_workflow(doc.doctype)` → `get_workflow_name(doctype)` = `frappe.db.get_value("Workflow", {"document_type": doctype, "is_active": 1}, "name")` (cached `frappe.cache.hget("workflow", doctype)`). Tức resolution đi qua **`document_type` + `is_active` → đúng 1 active workflow name**, KHÔNG qua tên literal.

**Lỗ hổng.** Nếu ai đó (a) **rename** Workflow của doctype (đổi `name` trong `imm_01_needs_workflow.json` / `imm_01_plan_workflow.json` / `fixtures/workflow.json`), (b) **deactivate** (`is_active=0`) hoặc **xoá** active workflow, (c) tạo **duplicate** active workflow cho cùng `document_type` (⇒ `get_value` trả 1 name tuỳ ý/không tất định), hoặc (d) drift hằng `_DT_NR`/`_DT_PP` khỏi `document_type` thật → `get_workflow_name` trả `None`/sai → `get_workflow` raise → surface `except Exception: return []` **CÂM** → **toàn bộ CTA duyệt đề xuất/kế hoạch biến mất, KHÔNG test nào bắt**. Guard toàn cục `test_workflow_admin_override` (5-class) **KHÔNG bắt**: nó `glob` file JSON theo `name` để kiểm admin-role trên mọi cạnh — **không biết IMM-01 resolve workflow theo `document_type`** ⇒ rename/deactivate/duplicate lọt câm.

**Invariants (regression-lock ở TẦNG MODULE — bổ sung, KHÔNG thay guard toàn cục):**

| ID | Invariant | Ground |
|---|---|---|
| **INV-01-SURFACE-A** (workflow-resolution: document_type → đúng 1 active named workflow) | Với **mỗi** cặp `(hằng service, tên kỳ vọng)`: `_DT_NR='IMM Needs Request'` → resolve **đúng 1** active Workflow tên `IMM-01 Needs Workflow`; `_DT_PP='IMM Procurement Plan'` → **đúng 1** active tên `IMM-01 Plan Workflow`. **Oracle độc lập**: parse `fixtures/workflow.json` + 2 per-module JSON — mỗi `document_type` có **chính xác 1** entry `is_active==1`, `name`==kỳ vọng, `document_type`==hằng service. **Live**: `frappe.model.workflow.get_workflow_name(dt)` == tên kỳ vọng. **Service-const** (`inspect` `assetcore.api.imm01`): `_DT_NR`/`_DT_PP` không drift. **RED** nếu rename/xoá/deactivate/duplicate active workflow của doctype. | `api/imm01.py:29-30` · `imm_01_needs_workflow.json` · `imm_01_plan_workflow.json` · `fixtures/workflow.json` |
| **INV-01-SURFACE-B** (live-wiring — NON-EMPTY cho user có role transition) | NR ở `Draft` + user CÓ role Draft-out (∈ `{AssetCore Super Admin, Corrective User, Needs Manager, System Manager}` — **KHÔNG** Procurement Manager, role đó chỉ ở cạnh `Pending Approval`) → `_nr_allowed_transition_actions(doc)` **NON-EMPTY** và == tập action (dedupe) từ `frappe.model.workflow.get_transitions(doc)` dưới cùng user (Draft-out action = `Gửi đề xuất`), **KHÔNG** permanent `[]`. **Đối xứng**: Plan ở `Draft` + user CÓ role (∈ `{AssetCore Super Admin, Commissioning Manager, Procurement Manager, System Manager}`) → `_plan_allowed_transition_actions(doc)` NON-EMPTY, chứa `Phê duyệt kế hoạch`, == get_transitions set. | `api/imm01.py:187,476` ⇄ `get_transitions` |
| **INV-01-SURFACE-C** (phân-định degrade: graceful ≠ broken) | User **CHỈ** base role `AssetCore System User` (không role transition) → **cả 2 surface** trả `[]` **GRACEFUL** (KHÔNG raise, payload `get_needs_request`/`get_procurement_plan` còn nguyên các field khác). Phân biệt **empty-do-thiếu-quyền** (chấp nhận) ≠ **empty-do-workflow-vỡ** (bug): nếu workflow vỡ thì **INV-01-SURFACE-A FAIL trước** (resolution) → không nhầm 2 nguyên nhân. | filter `t.allowed in user_roles` (get_transitions) |

**RED-before demo (chứng minh guard cắn — BẮT BUỘC):** (a) rename `name` kỳ vọng trong **bản-sao** JSON / temp workflow doctype `is_active` HOẶC (b) monkeypatch `frappe.model.workflow.get_transitions` → `raise` → **INV-A/B FAIL**; restore → **GREEN**. SURFACE-C giữ `[]` graceful trong CẢ 2 trạng thái (workflow lành + session base-role) — đó chính là mục "phân-định": empty base-role ≠ empty-vỡ.

**Cross-ref (KHÔNG chép lại).** Bất biến "**mọi cạnh workflow có `AssetCore Super Admin`**" (kiểu INV-04-WF-2) **đã** được `test_workflow_admin_override` (5-class global) cover cho MỌI workflow gồm cả 2 workflow IMM-01 (đã verify 10/10 cạnh Needs + 3/3 cạnh Plan có Super Admin, 2026-07-14). Guard SURFACE này **CHỈ** khoá resolution + live-wiring + degrade — **cross-ref**, KHÔNG re-assert every-edge-super-admin (khác chủ ý với IMM-04 §3.1 INV-04-WF-2).

**Delta vs IMM-04 (R29 mirror — 3 khác biệt chủ ý):**
1. IMM-04 service dùng **hằng-lookup literal** `get_doc("Workflow","IMM-04 Workflow")` → guard couple string-literal ⇄ fixture (INV-04-WF-1/TC-2). IMM-01 **không có literal** → resolve theo `document_type`+`is_active` → INV-01-SURFACE-A couple `_DT_NR`/`_DT_PP` ⇄ `document_type` ⇄ **đúng-1-active-name**.
2. IMM-01 có **2 surface** (NR + Plan) → mọi INV **đối xứng ×2**; IMM-04 chỉ 1 surface.
3. IMM-01 **KHÔNG** re-assert every-edge-super-admin (đã global) — IMM-04 INV-04-WF-2 có.

**Boundaries.**
- **Always:** guard là **test-only** (class mới trong `assetcore.tests.imm01.test_imm01`), **0 chạm runtime `.py`** → 0 gunicorn `--preload` reload / 0 `bench migrate`. Oracle độc lập (parse-file JSON + `inspect` hằng service) + assert THẬT trên workflow **live** (DB, `get_workflow_name`) + emit **cả 2 surface** live. Full suite `test_imm01` GREEN, không regression; đọc dòng cuối `Ran N OK` (không false-green).
- **Never:** KHÔNG "sửa" hành vi `except Exception: return []` trong `api/imm01.py` ở CR này (giữ nguyên `:187-217`, `:476-506`). KHÔNG nới lộ quyền / hardcode để test xanh giả. KHÔNG dựa `test_workflow_admin_override` để phủ lỗ này. KHÔNG re-assert every-edge-super-admin. KHÔNG git commit/push (HARD-STOP USER — working tree UNCOMMITTED).
- **[ROADMAP] observability (tách khỏi core — HARD-STOP USER):** thay `except Exception: return []` câm bằng `frappe.log_error(...)` trước return để lỗi **quan-sát-được** là **thay đổi runtime** → cần reload worker → **KHÔNG auto-apply** trong CR test-only này. Ghi backlog, chờ USER quyết.

### ADR-IMM-01-03: Guard workflow-surface module-local theo **resolution-by-document_type** (không hằng-lookup literal như IMM-04)

- **Status:** Accepted · **Date:** 2026-07-14
- **Context:** `test_workflow_admin_override` (5-class global) `glob` file JSON theo `name` — không biết IMM-01 resolve workflow **thế nào**. 2 surface NR/Plan resolve theo `document_type`+`is_active` (Frappe `get_workflow_name`) trong `try/except Exception: return []`. Rename / xoá / deactivate / **duplicate** active workflow của doctype, hoặc drift hằng `_DT_NR`/`_DT_PP` → `get_workflow_name`→`None`/sai → `get_workflow` raise → surface nuốt→`[]` **CÂM** → mất toàn bộ CTA duyệt đề xuất/kế hoạch, 0 test bắt. KHÁC IMM-04: IMM-01 **không** có hằng-lookup literal nên không thể couple string-literal ⇄ fixture.
- **Decision:** thêm guard **module-local** `TestImm01WorkflowSurfaceIntegrity` (tên gợi ý) trong `test_imm01` khoá **INV-01-SURFACE-A/B/C** — couple `_DT_NR`/`_DT_PP` ⇄ `document_type` ⇄ **đúng-1-active-named-workflow** (live `get_workflow_name` + parse-file oracle) ⇄ emit **2 surface** live. Đổi bất kỳ đầu (rename/deactivate/duplicate workflow, drift `_DT_*`) → guard FAIL (RED-before/GREEN-after).
- **Alternatives (loại):** (1) mở rộng `test_workflow_admin_override` đọc resolution per-module — loại: guard toàn cục phải app-agnostic (multi-app site), không nhét logic per-module. (2) đổi surface sang hằng-lookup literal như IMM-04 để dễ freeze — loại: đổi runtime `.py` (reload/HARD-STOP) + mất tính linh hoạt resolve-by-doctype của Frappe. (3) `log_error` thay `return []` — loại khỏi core CR (runtime change → HARD-STOP USER), giữ `[ROADMAP]`. (4) re-assert every-edge-super-admin trong guard này — loại: trùng lặp `test_workflow_admin_override`, dùng **cross-ref** thay vì chép.
- **Consequences:** +1 test class `TestImm01WorkflowSurfaceIntegrity` (đối xứng ×2 surface, ~6–8 TC); 0 runtime change; lỗ rename/deactivate/duplicate/drift `_DT_*`/silent-`return[]` khoá ở tầng module cho **cả 2** surface NR+Plan. Trade-off: guard hardcode kỳ-vọng `IMM-01 Needs Workflow`/`IMM-01 Plan Workflow` — chấp nhận vì đó là **hợp đồng cần freeze**; đổi tên workflow chính đáng phải đồng thời cập nhật guard + doc (fail nhắc).

---

## §VI Schedulers

| Job | File | Tần suất | Mô tả | Recipient |
|---|---|---|---|---|
| `check_pending_request_overdue` | `assetcore/services/imm01.py` | Daily | NR ở Submitted/Reviewing > 30 ngày → escalation digest in-app + email (E7 `notify_needs_overdue`), idempotent 1/recipient/ngày | **Needs Manager** (SSoT `notify_roles.NEEDS_STALE_ESCALATION`) |
| `budget_envelope_alert` | `assetcore/services/imm01.py` | Weekly | Plan vượt 80% envelope → log warning | PTP Khối 1, TCKT Head |
| `generate_demand_forecast` | `assetcore/services/imm01.py` | Monthly | Tạo `IMM Demand Forecast` skeleton / device_category (wire IMM-07/13 sau) | KH-TC Officer |

---

## §VII Database Indexes

> Hiện tại Frappe tự tạo index trên các Link field qua MySQL standard. **Chưa có custom index** được khai báo qua Property Setter hoặc patch SQL trong codebase. Các index dưới đây là **roadmap** đã được khuyến nghị theo NFR-01-09 (10k NR < 2s).

| Index (roadmap) | DocType | SQL |
|---|---|---|
| `idx_nr_state_dept` | `IMM Needs Request` | `CREATE INDEX idx_nr_state_dept ON \`tabIMM Needs Request\` (workflow_state, requesting_department);` |
| `idx_nr_replacement` | `IMM Needs Request` | `CREATE INDEX idx_nr_replacement ON \`tabIMM Needs Request\` (replacement_for_asset);` |
| `idx_nr_plan` | `IMM Needs Request` | `CREATE INDEX idx_nr_plan ON \`tabIMM Needs Request\` (procurement_plan);` |
| `idx_pp_year_period` | `IMM Procurement Plan` | `CREATE INDEX idx_pp_year_period ON \`tabIMM Procurement Plan\` (plan_year, plan_period);` |
| `idx_df_year_cat` | `IMM Demand Forecast` | `CREATE INDEX idx_df_year_cat ON \`tabIMM Demand Forecast\` (forecast_year, device_category);` |
