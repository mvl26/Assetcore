# 06 — Frontend Design — IMM-01 Đánh giá Nhu cầu & Dự toán

> **Wave 2 — Live.** Vue components, Pinia store và API client đã implement đầy đủ. Tài liệu này phản ánh code thực tế.

| Mục | Giá trị |
|---|---|
| Module | IMM-01 — Đánh giá nhu cầu và dự toán |
| Tech stack | Vue 3 + TypeScript + Pinia + Vue Router + TailwindCSS + TanStack Query |
| Cập nhật | 2026-05-14 |
| Liên kết | [05 API](./05_API_Specification.md) · [04 Backend](./04_Backend_Design.md) |

---

## §I Sitemap (Routes)

**Vue files thực tế:** `frontend/src/views/needs/` (route paths: `/needs-requests`, `/needs-requests/new`, `/needs-requests/:id`, `/procurement-plans`, `/procurement-plans/:id`)

| Route name | File (.vue) | API calls chính | Ghi chú |
|---|---|---|---|
| `NeedsRequestList` | `NeedsRequestListView.vue` | `list_needs_requests`, `dashboard_kpis` | List + filter 4 chiều + KPI grid 4 tiles |
| `NeedsRequestCreate` | `NeedsRequestCreateView.vue` | `create_needs_request` | Form create với SmartSelect cho Department + Device Model + Asset |
| `NeedsRequestDetail` | `NeedsRequestDetailView.vue` | `get_needs_request`, `get_allowed_transitions`, `score_needs_request`, `submit_budget_estimate`, `transition_workflow`, `approve_needs_request`, `reject_needs_request` | 3-tab: Tổng quan / Chấm điểm / Dự toán |
| `ProcurementPlanList` | `ProcurementPlanListView.vue` | `list_procurement_plans` | List + filter theo state / period / year. KPI strip 4 tiles (`<KpiCard>`) tính client-side từ list items — KHÔNG gọi endpoint KPI riêng. Nút "Tạo kế hoạch" gate `useCapabilities().can('needs.create')`. |
| `ProcurementPlanDetail` | `ProcurementPlanDetailView.vue` | `get_procurement_plan`, `set_budget_envelope`, `approve_plan`, `activate_plan`, `close_plan`, `roll_into_plan`, `remove_from_plan` | Chi tiết Plan + lifecycle Draft → Approved → Active → Closed |

> Note: Các view Tech Spec (IMM-02) nằm ở `frontend/src/views/procurement/` và là phạm vi của module IMM-02 — xem `../imm-02/06_Frontend_Design.md`.

---

## §II Component Catalog

### `<NeedsRequestList>` — Danh sách đề xuất nhu cầu

```
┌───────────────────────────────────────────────────────────────────┐
│ Đề xuất nhu cầu thiết bị                              [+ Tạo mới] │
├───────────────────────────────────────────────────────────────────┤
│ Filter: [Trạng thái▾] [Khoa▾] [Loại▾] [Năm▾] [Ưu tiên▾]   🔍     │
├───────────────────────────────────────────────────────────────────┤
│ NR-26-04-00012  Replacement  ICU    Máy thở Bird    [P1] 4.32    │
│   2026-04-25                              Submitted  💰 0₫        │
├───────────────────────────────────────────────────────────────────┤
│ NR-26-04-00011  New          NICU   Lồng ấp          [P2] 3.45    │
│   2026-04-22                              Reviewing  💰 850.000.000₫│
└───────────────────────────────────────────────────────────────────┘
        Hiển thị 1–20 / 87                        < 1 2 3 4 5 >
```

**Props:** `filters?: Partial<NeedsRequestFilter>`
**Emits:** `row-click(name: string)`

Priority class badge màu: P1=đỏ (red-600), P2=cam (orange-500), P3=vàng (yellow-400), P4=xám (gray-400).

---

### `<NeedsRequestDetail>` — Chi tiết 3-tab

```
[1. Thông tin chung] [2. Chấm điểm ưu tiên] [3. Dự toán]   [Audit ▸]

Workflow stepper:
Draft ▶ Submitted ▶ Reviewing ▶ Prioritized ▶ Budgeted ▶ Pending Approval ▶ Approved
                       ●

Tab 1 — Thông tin chung:
  ┌─ Header ──────────────────────────────────────────────────────┐
  │ NR-26-04-00012 · Replacement · P1 · ICU                       │
  └───────────────────────────────────────────────────────────────┘
  Block "Mục tiêu mua":
    Thiết bị [IMM Device Model lookup]   Số lượng [2]   Năm kế hoạch [2027]
  Block "Lý do lâm sàng":
    clinical_justification (rich text)   [📎 Đính kèm bằng chứng]
  Block "Asset thay thế" (nếu Replacement):
    replacement_for_asset [link]
    Auto-fill: Utilization 12T: 92% · Downtime: 120h
  Action footer (sticky bottom, theo state + role):
    Draft:    [Lưu bản nháp]  [Gửi đề xuất]
    Submitted: [Yêu cầu bổ sung] (HTM Reviewer)
    ...

Tab 2 — Chấm điểm ưu tiên:
  Scoring grid (6 rows, inline editable):
  ┌────────────────┬───────┬────────┬──────────┬─────────────────┐
  │ Tiêu chí       │ Điểm  │ Trọng  │ Weighted │ Lý giải         │
  │                │ (1-5) │ số (%) │          │                 │
  ├────────────────┼───────┼────────┼──────────┼─────────────────┤
  │ Tác động LS    │  [5]  │  25%   │  1.25    │ Cứu sinh ICU    │
  │ Nguy cơ        │  [5]  │  20%   │  1.00    │ Class III       │
  │ Khoảng cách    │  [4]  │  15%   │  0.60    │ Util 92%        │
  │ Tín hiệu thay  │  [5]  │  15%   │  0.75    │ MTBF 40%        │
  │ Tuân thủ       │  [3]  │  15%   │  0.45    │ Phần lớn OK     │
  │ Phù hợp budget │  [3]  │  10%   │  0.30    │ Trong envelope  │
  └────────────────┴───────┴────────┴──────────┴─────────────────┘
  Side panel: Dial 4.35/5.0 + Badge "P1 — Ưu tiên Cao nhất"

Tab 3 — Dự toán:
  Subtab CAPEX:
    [+ Thêm dòng]  [Import Excel]
    Bảng: Loại chi phí | Số lượng | Đơn giá | Thành tiền | Nguồn TK
  Subtab OPEX Year 1 → Year 5:
    Bảng: Loại chi phí | Năm | Số lượng | Đơn giá | Thành tiền
  Sticky summary footer:
    CAPEX: 3.080.000.000₫  |  OPEX 5y: 340.000.000₫  |  TCO: 3.420.000.000₫
    Nguồn vốn: [NSNN▾]  G03 status: ✅  Envelope: 76.8%
```

---

### `<PriorityScoringGrid>` — Lưới chấm điểm 6 tiêu chí

**Props:** `modelValue: ScoringRow[]`, `readonly?: boolean`, `weightConfig?: Record<string, number>`
**Emits:** `update:modelValue`, `compute-score`

Hiển thị 6 dòng với slider 1–5 hoặc dropdown. Computed display: `weighted_score` và `priority_class` badge.

---

### `<BudgetEditor>` — Editor matrix CAPEX + OPEX 5y

**Props:** `modelValue: BudgetLine[]`, `envelopeBudget?: number`, `readonly?: boolean`
**Emits:** `update:modelValue`

Tab CAPEX (default 5 dòng) + Tab OPEX Year 1–5 (6 dòng mỗi năm). Footer sticky hiển thị total_capex, total_opex_5y, tco_5y, envelope utilization %.

---

### `<WorkflowStepper>` — Stepper 8 states

**Props:** `currentState: NeedsRequestState`, `states: WorkflowStepConfig[]`

Hiển thị 8 state theo chiều ngang (compact) hoặc dọc (sidebar). State hiện tại highlighted, states terminal có icon đặc biệt (✅ Approved, ❌ Rejected).

---

### `<LifecycleEventTimeline>` — Audit trail dạng timeline

**Props:** `doctype: string`, `name: string`

Gọi API query `IMM Audit Trail` filter root_doctype + root_record. Hiển thị dạng timeline dọc phải side panel (collapsible).

---

### `<ProcurementPlanDetail>` — Chi tiết kế hoạch mua sắm

```
┌─────────────────────────────────────────────────────────────────┐
│ PP-26-001 · Annual 2027 · Approved · Envelope 50.000.000.000₫   │
│ Đã phân bổ: 38.400.000.000₫ (76.8%)   ████████████░░░           │
├─────────────────────────────────────────────────────────────────┤
│ Filter: [Khoa▾] [Quý▾] [Status▾]                                │
│                                                                 │
│ Rank  NR              Khoa   Model          P   Score  Phân bổ  │
│  1    NR-26-04-00012  ICU    Máy thở        P1  4.32  3,08 tỷ   │
│  2    NR-26-04-00007  NICU   Lồng ấp        P1  4.18  1,20 tỷ   │
│  3    NR-26-03-00021  CĐHA   CT 64-slice    P1  4.05 18,50 tỷ   │
│  ...                                                            │
│ [Generate IMM-02 Tech Spec Drafts]   [Export Excel]   [In]      │
└─────────────────────────────────────────────────────────────────┘
```

---

### `<DemandForecastHeatmap>` — Ma trận dự báo + drilldown (planned)

> Component này chưa tách thành Vue file riêng — endpoint `get_demand_forecast` đã sẵn nhưng `projected_qty` / `projected_capex` còn placeholder 0 cho đến khi IMM-07/IMM-13 expose data thực. UI heatmap = roadmap.

```
Device Category × Year (projected_qty)
              2027  2028  2029  2030  2031
Imaging        [5]   [4]   [6]   [5]   [4]
Life Support   [8]  [10]  [12]  [11]  [10]
Lab            [3]   [3]   [2]   [2]   [2]

Màu: xanh lá (0), vàng (5), cam (10), đỏ (15+)

Drivers stacked bar:
  ████████████████░░░░░░░░░░░  Replacement (50%)
  ░░░░░░░░████████░░░░░░░░░░░  Utilization growth (25%)
  ░░░░░░░░░░░░░░░░████████░░░  Service expansion (25%)

Accuracy vs 2026: 87%  [+2% so kỳ trước]
```

---

### `<KPITile>` — Tile dashboard có delta

**Props:** `label: string`, `value: number | string`, `target: number | string`, `delta: number`, `unit?: string`, `trendIcon?: 'up' | 'down' | 'neutral'`

Hiển thị value lớn, target nhỏ bên dưới, delta arrow (xanh lá = tốt, đỏ = cần cải thiện).

---

### ProcurementPlanList — KPI strip (client-side, source-backed)

4 tile (`<KpiCard>`) tính trực tiếp từ `store.plans` (đã có sẵn từ `list_procurement_plans`) — KHÔNG gọi endpoint KPI riêng, KHÔNG bịa số:

| Tile | Nguồn (per item) | Công thức |
|---|---|---|
| Tổng kế hoạch | `plans.length` | đếm |
| Đang hoạt động | `workflow_state === 'Active'` | đếm |
| Tổng ngân sách | `budget_envelope` | sum |
| Tỷ lệ sử dụng TB | `utilization_pct` | trung bình (chỉ tính item có giá trị) |

KPI tiles là **tĩnh** (không click-navigate) — không tạo dead-end. Khi list rỗng: tile hiển thị 0 / 0 ₫ / 0%.

### `<Imm01Dashboard>` — Dashboard KPI (inline, planned standalone)

> Hiện KPI tiles được render INLINE trên `NeedsRequestListView.vue` (4 KPI từ `dashboard_kpis`: `backlog_over_30d`, `by_state`, `g01_pass_rate`, `envelope_utilization`). View dashboard chuyên biệt với 6 tiles + chart = roadmap.

```
[Lead time → Approved]  [G01 pass rate]    [Envelope utilization]
    38 ngày / 45d           96% / 95%           78% / 70–95%
        ↓ tốt                ↑ tốt                  ✅

[Replacement coverage]  [Forecast accuracy]  [Backlog > 30d]
     85% / 80%               87% / 85%           12 phiếu
         ↑ tốt                   ↑ tốt               ↓ cần giảm

Charts:
  - Funnel state count (bar)
  - Stacked bar by dept × priority class
  - Trendline budget envelope vs allocated by quarter
```

---

## §III Pinia Store

File: `frontend/src/stores/imm01.ts` — **Đã implement.** Store ID: `'imm01'`.

**State:**

| Field | Type | Mô tả |
|---|---|---|
| `needsRequests` | `NeedsRequestListItem[]` | Danh sách trang hiện tại |
| `total` | `number` | Tổng số bản ghi |
| `page` / `pageSize` | `number` | Pagination state |
| `filters` | `NeedsRequestFilters` | Filters đang active |
| `loading` | `boolean` | Loading flag |
| `error` | `string \| null` | Error message |
| `currentDoc` | `NeedsRequestDoc \| null` | Detail document đang xem |
| `plans` | `ProcurementPlanListItem[]` | Procurement Plans list |
| `kpis` | `DashboardKpis \| null` | Dashboard KPIs |

**Actions (tên thực tế):**

| Action | Gọi API |
|---|---|
| `fetchNeedsRequests(filters, page, pageSize)` | `list_needs_requests` |
| `fetchOne(name)` | `get_needs_request` |
| `create(payload)` | `create_needs_request` |
| `update(name, payload)` | `update_needs_request` |
| `score(name, rows)` | `score_needs_request` |
| `submitBudget(name, lines, funding_source, evidence)` | `submit_budget_estimate` |
| `transition(name, action)` | `transition_workflow` |
| `approve(name, board_approver, remarks)` | `approve_needs_request` |
| `reject(name, rejection_reason)` | `reject_needs_request` |
| `fetchPlans(filters, page, pageSize)` | `list_procurement_plans` |
| `fetchKpis()` | `dashboard_kpis` |

> `getAllowedTransitions(name)` được gọi trực tiếp từ `NeedsRequestDetailView.vue` (không qua store) để refresh danh sách nút **generic** sau mỗi transition. **CTA Phê duyệt / Bác đề xuất KHÔNG dùng call này** — gate theo field `allowed_transitions` embed sẵn trong payload `get_needs_request` (xem §III.a).

### §III.a Server-driven CTA gating — Phê duyệt / Bác đề xuất (GATE-8 / LL-FE-51)

**Vấn đề (dead-gate):** `NeedsRequestDetailView.vue` hiện gate 2 nút Phê duyệt/Bác đề xuất bằng
`isBoardApprover = hasAnyRole([DEPT_HEAD, OPS_MANAGER]) || isSystemAdmin`. Nhưng workflow
`Pending Approval → Approved/Rejected` chỉ cho **`Procurement Manager` · `AssetCore Super Admin` · `System Manager`**
(SSoT `fixtures/workflow.json`). Hai tập role LỆCH nhau ⇒:
- `Procurement Manager` (người duyệt thật) KHÔNG khớp `isBoardApprover` → **không thấy nút** (bug).
- `Dept Head`/`Ops Manager` khớp `isBoardApprover` → **thấy nút nhưng bấm bị 403** (false-permissive).

**Fix — gate theo `allowed_transitions` do BE emit (đối xứng `ProcurementPlanDetailView.canDo`):**

```ts
// currentDoc.allowed_transitions: string[]  (từ get_needs_request payload)
const canApprove = computed(() => (currentDoc.value?.allowed_transitions ?? []).includes('Phê duyệt'))
const canReject  = computed(() => (currentDoc.value?.allowed_transitions ?? []).includes('Bác đề xuất'))
```

**Ràng buộc (Boundaries):**
- **Always**: nút Phê duyệt render khi `canApprove`, nút Bác đề xuất render khi `canReject`; `allowed_transitions` lấy từ payload `get_needs_request` (không call thứ 2 → không flash); action-string khớp **EXACT** workflow.json (`'Phê duyệt'`, `'Bác đề xuất'`); `?? []` phòng khi BE chưa reload (payload thiếu field → 0 nút, KHÔNG crash).
- **Never**: tham chiếu `isBoardApprover` / role-list (`Roles.DEPT_HEAD`, `Roles.OPS_MANAGER`) HAY literal `workflow_state === 'Pending Approval'` để gate 2 CTA này (grep `NeedsRequestDetailView.vue` phải SẠCH cả `isBoardApprover` lẫn `'Pending Approval'` cho 2 nút). `canApproveReject` cũ bị thay bằng `canApprove`/`canReject`.
- **Regression**: type `NeedsRequestDoc` (`types/imm01.ts`) thêm `allowed_transitions?: string[]`; FE vitest `needsRequestDetailCtaGating.test.ts` (đối xứng `procurementPlanCtaGating.test.ts`) phủ 3 case: allowed chứa action → nút hiện; allowed `[]` → nút ẩn; payload thiếu field → 0 nút, không crash.

---

## §IV i18n Table

### Trạng thái workflow

| key | Tiếng Việt |
|---|---|
| `state.Draft` | Bản nháp |
| `state.Submitted` | Đã gửi |
| `state.Reviewing` | Đang rà soát |
| `state.Prioritized` | Đã chấm điểm |
| `state.Budgeted` | Đã dự toán |
| `state.Pending Approval` | Chờ phê duyệt |
| `state.Approved` | Đã duyệt |
| `state.Rejected` | Đã bác |

### Nhãn action button

| key | Tiếng Việt |
|---|---|
| `action.submit` | Gửi đề xuất |
| `action.return` | Yêu cầu bổ sung |
| `action.score_done` | Hoàn tất chấm điểm |
| `action.reject_early` | Bác đề xuất (sớm) |
| `action.budget_done` | Lập dự toán xong |
| `action.submit_to_board` | Trình BGĐ |
| `action.approve` | Phê duyệt |
| `action.reject` | Từ chối |
| `action.revise_budget` | Yêu cầu chỉnh dự toán |
| `action.roll_into_plan` | Gom vào Kế hoạch |
| `action.generate_specs` | Tạo Tech Spec Drafts |

### Nhãn tiêu chí chấm điểm

| key | Tiếng Việt |
|---|---|
| `criterion.clinical_impact` | Tác động lâm sàng |
| `criterion.risk` | Nguy cơ bệnh nhân / nhân viên |
| `criterion.utilization_gap` | Khoảng cách sử dụng |
| `criterion.replacement_signal` | Tín hiệu thay thế |
| `criterion.compliance_gap` | Khoảng cách tuân thủ |
| `criterion.budget_fit` | Phù hợp ngân sách |

### Priority class

| key | Tiếng Việt | Màu |
|---|---|---|
| `priority.P1` | P1 — Ưu tiên Cao nhất | Đỏ |
| `priority.P2` | P2 — Ưu tiên Cao | Cam |
| `priority.P3` | P3 — Ưu tiên Vừa | Vàng |
| `priority.P4` | P4 — Ưu tiên Thấp | Xám |

### Loại đề xuất

| key | Tiếng Việt |
|---|---|
| `type.New` | Mua mới |
| `type.Replacement` | Thay thế |
| `type.Upgrade` | Nâng cấp |
| `type.Add-on` | Bổ sung |

### Nguồn vốn

| key | Tiếng Việt |
|---|---|
| `funding.NSNN` | Ngân sách Nhà nước |
| `funding.Tài trợ` | Tài trợ |
| `funding.Xã hội hóa` | Xã hội hoá |
| `funding.BHYT` | BHYT |
| `funding.Khác` | Khác |

### Error messages (UI toast)

| Error code | Thông báo người dùng |
|---|---|
| `VR-01-01` | Thiết bị đã có đề xuất thay thế đang hoạt động |
| `VR-01-02` | Đề xuất thay thế cần có Kế hoạch Thanh lý IMM-13 ở trạng thái Đang xử lý/Đã duyệt |
| `VR-01-03` | Lý do lâm sàng phải có ít nhất 200 ký tự |
| `VR-01-04` | Năm kế hoạch không được nhỏ hơn năm hiện tại |
| `G01` | Cần dữ liệu sử dụng 12 tháng cho đề xuất Thay thế / Nâng cấp |
| `G02` | Cần đủ 6 tiêu chí chấm điểm trước khi chuyển Đã chấm điểm |
| `G03` | Dự toán phải bao gồm cả CAPEX và OPEX 5 năm |
| `G04` | Tổng dự toán vượt ngân sách được phân bổ |
| `G05` | Cần xác nhận người phê duyệt và nguồn vốn trước khi trình BGĐ |
| `FORBIDDEN` | Bạn không có quyền thực hiện thao tác này |
| `NOT_FOUND` | Phiếu không tồn tại hoặc đã bị xóa |
| `BAD_STATE` | Thao tác không khả dụng ở trạng thái hiện tại |
