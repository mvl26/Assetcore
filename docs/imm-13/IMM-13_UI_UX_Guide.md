# IMM-13 — Ngừng sử dụng và Điều chuyển (UI/UX Guide)

| Thuộc tính    | Giá trị                                     |
|---------------|---------------------------------------------|
| Module        | IMM-13 — UI/UX Guide                        |
| Phiên bản     | 2.0.0                                       |
| Ngày cập nhật | 2026-04-24                                  |
| Framework     | Vue 3 · TypeScript · Tailwind CSS · Pinia   |
| Icon Library  | Lucide Vue Next                             |

---

## 1. Screen Map

| # | Màn hình | Route | Component | Mô tả |
|---|---|---|---|---|
| 1 | Suspension List View | `/imm13/suspensions` | `SuspensionListView.vue` | Danh sách phiếu DR với filter/search |
| 2 | Suspension Create View | `/imm13/suspensions/new` | `SuspensionCreateView.vue` | Form tạo mới phiếu DR |
| 3 | Suspension Detail View | `/imm13/suspensions/:id` | `SuspensionDetailView.vue` | Chi tiết + workflow actions |
| 4 | Replacement Review View | `/imm13/suspensions/:id/review` | `ReplacementReviewView.vue` | Màn hình review thay thế thiết bị |
| 5 | Retirement Candidates Dashboard | `/imm13/dashboard` | `RetirementDashboardView.vue` | Dashboard thiết bị cần xem xét ngừng |

---

## 2. Vue Router Configuration

```typescript
// router/imm13.ts
import { RouteRecordRaw } from "vue-router";

const imm13Routes: RouteRecordRaw[] = [
  {
    path: "/imm13/suspensions",
    name: "SuspensionList",
    component: () => import("@/views/imm13/SuspensionListView.vue"),
    meta: {
      title: "Ngừng sử dụng & Điều chuyển",
      module: "IMM-13",
      roles: ["IMM HTM Manager", "IMM Biomed Engineer", "IMM CMMS Admin",
              "IMM QA Officer", "IMM Finance", "IMM VP Block2"],
    },
  },
  {
    path: "/imm13/suspensions/new",
    name: "SuspensionCreate",
    component: () => import("@/views/imm13/SuspensionCreateView.vue"),
    meta: {
      title: "Tạo yêu cầu ngừng sử dụng",
      roles: ["IMM HTM Manager", "IMM CMMS Admin"],
    },
  },
  {
    path: "/imm13/suspensions/:id",
    name: "SuspensionDetail",
    component: () => import("@/views/imm13/SuspensionDetailView.vue"),
    props: true,
    meta: {
      title: "Chi tiết phiếu DR",
      roles: ["IMM HTM Manager", "IMM Biomed Engineer", "IMM CMMS Admin",
              "IMM QA Officer", "IMM Finance", "IMM VP Block2", "IMM Network Manager"],
    },
  },
  {
    path: "/imm13/suspensions/:id/review",
    name: "ReplacementReview",
    component: () => import("@/views/imm13/ReplacementReviewView.vue"),
    props: true,
    meta: {
      title: "Review thay thế thiết bị",
      roles: ["IMM HTM Manager", "IMM Finance", "IMM CMMS Admin"],
    },
  },
  {
    path: "/imm13/dashboard",
    name: "RetirementDashboard",
    component: () => import("@/views/imm13/RetirementDashboardView.vue"),
    meta: {
      title: "Dashboard - Thiết bị cần xem xét ngừng",
      roles: ["IMM HTM Manager", "IMM VP Block2", "IMM CMMS Admin"],
    },
  },
];

export default imm13Routes;
```

---

## 3. Screen 1: Suspension List View

### Wireframe

```
┌─────────────────────────────────────────────────────────────────────────┐
│  [≡] IMM-13  Ngừng sử dụng & Điều chuyển          [👤 user] [🔔 3]     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────┐ ┌───────────────┐ ┌────────────────┐ ┌───────────┐ │
│  │  12 Đã hoàn   │ │  5 Đang xử lý │ │  2 Chờ phê     │ │  [+] Tạo  │ │
│  │  tất (YTD)    │ │               │ │  duyệt         │ │  yêu cầu  │ │
│  └───────────────┘ └───────────────┘ └────────────────┘ └───────────┘ │
│                                                                         │
│  ┌──────────────────────────────┐  [Trạng thái ▼]  [Lý do ▼]  [Năm ▼]│
│  │ 🔍 Tìm thiết bị / Mã phiếu  │                                       │
│  └──────────────────────────────┘                                       │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Mã phiếu  │ Thiết bị           │ Lý do       │ Rủi ro │ Status │   │
│  ├───────────┼────────────────────┼─────────────┼────────┼────────┤   │
│  │DR-26-04-  │ ECG-2019-003       │ End of Life │ [Low]  │[Draft] │   │
│  │00001      │ ECG 12-lead Nihon  │             │        │        │   │
│  ├───────────┼────────────────────┼─────────────┼────────┼────────┤   │
│  │DR-26-04-  │ VENT-2018-007      │ Beyond Eco  │[High]  │[Tech   │   │
│  │00002      │ Máy thở Hamilton   │ Repair      │        │Review] │   │
│  ├───────────┼────────────────────┼─────────────┼────────┼────────┤   │
│  │DR-26-03-  │ MRI-2015-001       │ Obsolete    │[Medium]│[Trans- │   │
│  │00012      │ MRI 1.5T Siemens   │             │        │ferred] │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                          [< 1 2 3 >]  Tổng: 47 phiếu  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Status Badge Colors

| State | Tailwind Classes | Mô tả hiển thị |
|---|---|---|
| `Draft` | `bg-slate-100 text-slate-600` | Nháp |
| `Pending Tech Review` | `bg-blue-100 text-blue-700` | Chờ đánh giá KT |
| `Under Replacement Review` | `bg-violet-100 text-violet-700` | Review thay thế |
| `Approved for Transfer` | `bg-cyan-100 text-cyan-700` | Đã duyệt điều chuyển |
| `Transfer In Progress` | `bg-orange-100 text-orange-700` | Đang điều chuyển |
| `Transferred` | `bg-teal-100 text-teal-700` | Đã điều chuyển |
| `Pending Decommission` | `bg-amber-100 text-amber-700` | Chờ duyệt ngừng |
| `Completed` | `bg-slate-200 text-slate-500` | Hoàn tất |
| `Cancelled` | `bg-red-100 text-red-600` | Đã hủy |

### Residual Risk Badge Colors

| Level | Tailwind Classes |
|---|---|
| `Low` | `bg-green-100 text-green-700` |
| `Medium` | `bg-yellow-100 text-yellow-700` |
| `High` | `bg-orange-100 text-orange-700` |
| `Critical` | `bg-red-100 text-red-700 font-bold` |

### Component Spec: SuspensionListView.vue

```vue
<template>
  <div class="px-6 py-4 max-w-screen-xl mx-auto">
    <!-- Header + Action -->
    <PageHeader title="Ngừng sử dụng & Điều chuyển" icon="PowerOff">
      <RouterLink to="/imm13/suspensions/new">
        <BaseButton variant="primary">+ Tạo yêu cầu</BaseButton>
      </RouterLink>
    </PageHeader>

    <!-- KPI Summary Bar -->
    <KpiBar :metrics="store.summaryMetrics" class="mb-6" />

    <!-- Filters -->
    <FilterBar v-model="filters" :options="filterOptions" />

    <!-- Table -->
    <DataTable
      :columns="tableColumns"
      :rows="store.suspensionList"
      :loading="store.loading"
      :total="store.total"
      v-model:page="filters.page"
      @row-click="navigateToDetail"
    >
      <template #status="{ value }">
        <StatusBadge :status="value" :map="suspensionStatusMap" />
      </template>
      <template #residual_risk_level="{ value }">
        <RiskBadge :level="value" />
      </template>
    </DataTable>
  </div>
</template>
```

---

## 4. Screen 2: Suspension Create View

### Wireframe

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ← Quay lại         Tạo yêu cầu ngừng sử dụng / điều chuyển           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ── Thông tin thiết bị ─────────────────────────────────────────────── │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │ Thiết bị *           [SmartSelect: search assets...]           │    │
│  │ ──────────────────────────────────────────────────────────     │    │
│  │ Model: ECG-1550  │  Vị trí: Khoa Tim mạch  │  Tuổi: 7.2 năm  │    │
│  │ Tổng chi phí BT: 45,000,000 VNĐ  │  Failures 12m: 3 lần      │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  Lý do ngừng *        [Select ▼ End of Life                     ]      │
│  Chi tiết lý do *     [Textarea: Máy ECG 7 năm, mainboard...    ]      │
│  Tình trạng thiết bị  (○) Poor  (●) Non-functional  (○) Partly  (○)   │
│                                                                         │
│  ── Tuân thủ & An toàn ────────────────────────────────────────────── │
│  Nguy hại sinh học    [Toggle ○]   Cần xóa dữ liệu   [Toggle ○]       │
│  Cần giấy phép PL     [Toggle ○]                                        │
│                                                                         │
│  ── Ghi chú ─────────────────────────────────────────────────────────  │
│  Nguồn trigger        [DR triggered từ IMM-12 / WO-CM-26-00089  ]      │
│                                                                         │
│  ─────────────────────────────────────────────────────────────────     │
│          [Hủy]                [Lưu nháp]    [Tạo & Gửi đánh giá KT]   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Form Sections

**Section 1 — Thông tin thiết bị:**
- `asset`: SmartSelect → sau khi chọn, auto-load asset card (model, vị trí, tuổi, tổng chi phí BT, failure count 12m từ API `get_asset_suspension_eligibility`)
- Nếu asset có WO mở → hiện cảnh báo inline màu đỏ: "Còn X Work Order mở — không thể tạo DR"
- `suspension_reason`: Select dropdown
- `reason_details`: Textarea (min 20 ký tự)
- `condition_at_suspension`: Radio group

**Section 2 — Tuân thủ & An toàn:**
- `biological_hazard`: Toggle — nếu ON → show `bio_hazard_clearance` Textarea (required)
- `data_destruction_required`: Toggle — nếu ON → show info box nhắc nhở confirm sau
- `regulatory_clearance_required`: Toggle — nếu ON → show File Upload (required)

**Section 3 — Nguồn trigger (Optional):**
- `initiated_from_module`: Data field (auto-fill nếu navigate từ WO)
- `initiated_from_record`: Data field (auto-fill)

**Action Buttons:**
- `[Hủy]` → navigate `/imm13/suspensions`
- `[Lưu nháp]` → `POST create_suspension_request` (Draft state)
- `[Tạo & Gửi đánh giá KT]` → create + auto-transition to Pending Tech Review

---

## 5. Screen 3: Suspension Detail View

### Wireframe

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ← Quay lại    DR-26-04-00001            [Đã hoàn tất] [In phiếu]      │
│  ECG 12-lead Nihon Kohden ECG-1550  ·  Khoa Tim mạch  ·  7.2 năm       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  [Chi tiết phiếu]  [Checklist (7/7)]  [Lịch sử vòng đời]              │
│                                                                         │
│  ── Tab 1: Chi tiết phiếu ─────────────────────────────────────────── │
│                                                                         │
│  ┌─ Thông tin cơ bản ──────┐  ┌─ Đánh giá kỹ thuật ────────────────┐  │
│  │ Lý do: End of Life      │  │ KS đánh giá: biomed@bv.vn          │  │
│  │ Tình trạng: Non-func.   │  │ Ngày: 22/04/2026                   │  │
│  │ Rủi ro: [Low]           │  │ Rủi ro còn lại: [Low]              │  │
│  │ Tuổi TL ước tính: 0 T   │  │ Ghi chú: Mainboard cháy...         │  │
│  └─────────────────────────┘  └────────────────────────────────────┘  │
│                                                                         │
│  ┌─ Quyết định ────────────────────────────────────────────────────┐   │
│  │ Outcome: Retire  │  Cần thay thế: No  │  Book Value: 20,000,000 │   │
│  │ Ghi chú: Trigger IMM-14 để đóng hồ sơ                          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ── Workflow Action Panel (thay đổi theo state) ─────────────────────  │
│  [STATE: Pending Tech Review]                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Đánh giá kỹ thuật                                               │   │
│  │ Kỹ sư đánh giá *  [biomed@bv.vn          ]                      │   │
│  │ Tình trạng KT *   [Non-functional ▼      ]                      │   │
│  │ Residual Risk *   [Low ▼                 ]                      │   │
│  │ Ghi chú KT *      [Textarea...            ]                     │   │
│  │ Rủi ro còn lại *  [Textarea...            ]                     │   │
│  │ Tuổi TL còn lại   [0] tháng                                     │   │
│  │                                                                 │   │
│  │      [Từ chối - Có thể sửa]         [Hoàn thành đánh giá KT]  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Tab Structure

**Tab 1 — Chi tiết phiếu:**
- Info cards: Thông tin cơ bản | Đánh giá KT | Outcome & Replacement
- Workflow Action Panel (thay đổi theo state hiện tại)
- Compliance flags: Bio-hazard badge, Data destruction badge

**Tab 2 — Checklist:**
- Bảng checklist với checkbox `completed`, `responsible`, `due_date`, `notes`
- Progress bar: "5/7 hoàn thành"
- Button "Đánh dấu hoàn thành" cho từng item

**Tab 3 — Lịch sử vòng đời:**
- Vertical timeline với ALE events
- Mỗi event: icon (màu theo type) + timestamp + actor + from_status → to_status + notes

### Action Panels per State

| State | Panel hiển thị |
|---|---|
| `Draft` | Button: [Gửi đánh giá kỹ thuật] |
| `Pending Tech Review` | Form: reviewer, condition, residual_risk, notes + [Từ chối] [Hoàn thành] |
| `Under Replacement Review` | Link → `/imm13/suspensions/:id/review` |
| `Approved for Transfer` | Button: [Bắt đầu điều chuyển] (cho Network Manager) |
| `Transfer In Progress` | Checklist progress + Button: [Hoàn thành điều chuyển] |
| `Transferred` | Read-only + [Xem record IMM-14 →] (nếu có) |
| `Pending Decommission` | Approval form (cho VP) + [Phê duyệt] [Từ chối]; Submit button (cho CMMS Admin) |
| `Completed` | Read-only + [Xem IMM-14 →] |
| `Cancelled` | Read-only, hiện rejection_reason |

---

## 6. Screen 4: Replacement Review View

### Wireframe

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ← Chi tiết phiếu    Review Thay thế — DR-26-04-00001                  │
│  ECG 12-lead Nihon Kohden  ·  7.2 năm  ·  Rủi ro: [Low]               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ── Thông tin kỹ thuật (readonly) ─────────────────────────────────── │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │ Tình trạng: Non-functional  │  Residual Risk: Low              │    │
│  │ Tuổi TL còn lại: 0 tháng   │  Tổng chi phí BT: 45,000,000    │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ── Phân tích Thay thế ─────────────────────────────────────────────  │
│  Cần thay thế?        (○) Có   (○) Không   (●) Hoãn lại              │
│  [Nếu Có] Model thay thế    [SmartSelect: Device Model...     ]        │
│  [Nếu Có] Chi phí ước tính  [                    0 VNĐ       ]        │
│  [Nếu Có] Timeline          [Q3 2026                          ]        │
│                                                                         │
│  ── Phân tích Tài chính ────────────────────────────────────────────  │
│  Giá trị sổ sách HT         [           20,000,000 VNĐ       ]        │
│  Tỷ lệ BT/Giá mua           [22.5%  (auto-calculated)        ]        │
│  Luận chứng kinh tế          [Textarea: Chi phí thay thế...   ]        │
│                                                                         │
│  ── Quyết định Cuối ────────────────────────────────────────────────  │
│  Outcome *                                                              │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  (○) Điều chuyển    →  [Location ▼] [Người nhận *]          │      │
│  │  (○) Tạm ngừng      →  Giữ kho, chờ quyết định              │      │
│  │  (●) Ngừng hẳn      →  Trigger IMM-14 sau khi phê duyệt     │      │
│  └──────────────────────────────────────────────────────────────┘      │
│  Ghi chú quyết định          [Textarea...                      ]        │
│                                                                         │
│  ─────────────────────────────────────────────────────────────────     │
│                       [Hủy bỏ]           [Lưu quyết định]              │
└─────────────────────────────────────────────────────────────────────────┘
```

### Conditional Fields

- `replacement_needed = "Yes"` → show: Model thay thế (SmartSelect), Chi phí ước tính, Timeline
- `outcome = "Transfer"` → show: Location (required, Link → Location), Người nhận (required, Link → User)
- `current_book_value > 500000000` → show warning banner: "Giá trị > 500M VNĐ — cần phê duyệt VP Block2"
- `residual_risk_level in ["High", "Critical"]` → show info banner: "Rủi ro cao — Replacement Review bắt buộc (BR-13-07)"

---

## 7. Screen 5: Retirement Candidates Dashboard

### Wireframe

```
┌─────────────────────────────────────────────────────────────────────────┐
│  [≡] IMM-13  Dashboard — Thiết bị cần xem xét ngừng sử dụng            │
│                                                       [Năm 2026 ▼]     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐  │
│  │      5       │ │     12       │ │      4       │ │    31.2      │  │
│  │ Retirement   │ │ Suspended    │ │ Transferred  │ │ Avg Days     │  │
│  │ Candidates   │ │ YTD          │ │ YTD          │ │ to Complete  │  │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘  │
│                                                                         │
│  ── Retirement Candidates ─────────────────────────────────────────── │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │ Thiết bị           │ Tuổi  │ BT/Giá │ Failures│ Risk  │ Action  │ │
│  ├────────────────────┼───────┼────────┼─────────┼───────┼─────────┤ │
│  │ VENT-2018-007      │ 8.1y  │  81.8% │    7    │ [92]  │[+Tạo DR]│ │
│  │ Máy thở Hamilton   │[████] │ [████] │         │       │         │ │
│  ├────────────────────┼───────┼────────┼─────────┼───────┼─────────┤ │
│  │ USG-2017-012       │ 9.0y  │  65.3% │    4    │ [78]  │[+Tạo DR]│ │
│  │ Siêu âm GE Logiq   │[████] │ [███]  │         │       │         │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ── Biểu đồ ───────────────────────────────────────────────────────── │
│  ┌────────────────────────────┐  ┌─────────────────────────────────┐  │
│  │ Ngừng theo Lý do (Bar)     │  │ Phân bổ Residual Risk (Pie)     │  │
│  │                            │  │                                 │  │
│  │ End of Life    ██████ 6    │  │  Low ████ 58%                  │  │
│  │ BER            ████   3   │  │  Med ██   25%                  │  │
│  │ Regulatory     ██     2   │  │  High█     17%                 │  │
│  └────────────────────────────┘  └─────────────────────────────────┘  │
│                                                                         │
│  ┌────────────────────────────┐  ┌─────────────────────────────────┐  │
│  │ Điều chuyển theo Đích      │  │ KRI Alerts                      │  │
│  │ (Horizontal Bar)           │  │                                 │  │
│  │ Khoa Cấp cứu    ██ 2      │  │ ⚠ 1 phiếu > 500M chưa duyệt   │  │
│  │ Phòng khám A    █  1      │  │   > 14 ngày                    │  │
│  │ TTYT Tân Phú    █  1      │  │ ✓ 0 Bio-hazard mở              │  │
│  └────────────────────────────┘  └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Risk Score Calculation (display)

Risk Score (0-100) = tổng hợp:
- Age percent × 0.3
- Maintenance cost ratio × 0.3
- Failure count (normalized) × 0.2
- Downtime percent × 0.2

Màu Risk Score:
- 0-49: `text-green-600`
- 50-74: `text-yellow-600`
- 75-89: `text-orange-600`
- 90-100: `text-red-700 font-bold`

---

## 8. Pinia Store: `useImm13Store.ts`

```typescript
// stores/imm13.ts
import { defineStore } from "pinia";

interface SuspensionRequest {
  name: string;
  asset: string;
  asset_name: string;
  workflow_state: string;
  suspension_reason: string;
  residual_risk_level: string;
  outcome: string | null;
  approved: boolean;
  creation: string;
  days_open: number;
}

interface RetirementCandidate {
  asset: string;
  asset_name: string;
  location: string;
  age_years: number;
  maintenance_cost_ratio: number;
  failure_count_12m: number;
  risk_score: number;
  recommended_action: string;
}

interface DashboardMetrics {
  suspended_ytd: number;
  transferred_ytd: number;
  retirement_candidates_count: number;
  avg_days_to_complete: number;
  pending_approval_count: number;
  kri_alerts: KriAlert[];
}

export const useImm13Store = defineStore("imm13", {
  state: () => ({
    // List View
    suspensionList: [] as SuspensionRequest[],
    total: 0,
    loading: false,
    filters: {
      workflow_state: "",
      suspension_reason: "",
      asset: "",
      year: new Date().getFullYear(),
      page: 1,
      page_size: 20,
    },

    // Detail View
    currentDr: null as SuspensionRequest | null,
    detailLoading: false,

    // Dashboard
    dashboardMetrics: null as DashboardMetrics | null,
    retirementCandidates: [] as RetirementCandidate[],

    // Asset Eligibility
    eligibilityCache: {} as Record<string, any>,
  }),

  getters: {
    summaryMetrics: (state) => ({
      suspended_ytd: state.dashboardMetrics?.suspended_ytd ?? 0,
      transferred_ytd: state.dashboardMetrics?.transferred_ytd ?? 0,
      pending_approval: state.dashboardMetrics?.pending_approval_count ?? 0,
    }),

    isCurrentDrEditable: (state) =>
      state.currentDr?.workflow_state !== "Completed" &&
      state.currentDr?.workflow_state !== "Transferred" &&
      state.currentDr?.workflow_state !== "Cancelled",

    pendingItems: (state) =>
      state.suspensionList.filter((dr) =>
        ["Pending Tech Review", "Under Replacement Review", "Pending Decommission"]
          .includes(dr.workflow_state)
      ),
  },

  actions: {
    async fetchSuspensionList() {
      this.loading = true;
      try {
        const res = await api.get("assetcore.api.imm13.get_suspension_list", this.filters);
        this.suspensionList = res.data.rows;
        this.total = res.data.total;
      } finally {
        this.loading = false;
      }
    },

    async fetchDetail(name: string) {
      this.detailLoading = true;
      try {
        const res = await api.get("assetcore.api.imm13.get_suspension_request", { name });
        this.currentDr = res.data;
      } finally {
        this.detailLoading = false;
      }
    },

    async createSuspensionRequest(payload: Partial<SuspensionRequest>) {
      const res = await api.post("assetcore.api.imm13.create_suspension_request", payload);
      return res.data;
    },

    async submitTechnicalReview(payload: {
      name: string; reviewer: string; review_notes: string;
      residual_risk_level: string; residual_risk_notes: string;
      condition_assessment: string; estimated_remaining_life: number;
      approved: boolean; rejection_reason?: string;
    }) {
      const res = await api.post("assetcore.api.imm13.submit_technical_review", payload);
      await this.fetchDetail(payload.name);
      return res.data;
    },

    async submitReplacementReview(payload: object) {
      const res = await api.post("assetcore.api.imm13.submit_replacement_review", payload);
      await this.fetchDetail((payload as any).name);
      return res.data;
    },

    async approveSuspension(payload: object) {
      const res = await api.post("assetcore.api.imm13.approve_suspension", payload);
      await this.fetchDetail((payload as any).name);
      return res.data;
    },

    async executeTransfer(payload: object) {
      const res = await api.post("assetcore.api.imm13.execute_transfer", payload);
      await this.fetchDetail((payload as any).name);
      return res.data;
    },

    async completeSuspension(payload: object) {
      const res = await api.post("assetcore.api.imm13.complete_suspension", payload);
      await this.fetchDetail((payload as any).name);
      return res.data;
    },

    async cancelSuspensionRequest(payload: { name: string; rejection_reason: string }) {
      const res = await api.post("assetcore.api.imm13.cancel_suspension_request", payload);
      await this.fetchSuspensionList();
      return res.data;
    },

    async fetchDashboardMetrics(year?: number) {
      const res = await api.get("assetcore.api.imm13.get_dashboard_metrics", { year });
      this.dashboardMetrics = res.data;
    },

    async fetchRetirementCandidates() {
      const res = await api.get("assetcore.api.imm13.get_retirement_candidates", {});
      this.retirementCandidates = res.data.candidates;
    },

    async checkAssetEligibility(assetName: string) {
      if (this.eligibilityCache[assetName]) return this.eligibilityCache[assetName];
      const res = await api.get("assetcore.api.imm13.get_suspension_list", { asset: assetName });
      this.eligibilityCache[assetName] = res.data;
      return res.data;
    },
  },
});
```

---

## 9. Shared Components

### StatusBadge.vue

```vue
<template>
  <span :class="badgeClass" class="px-2 py-0.5 rounded-full text-xs font-medium">
    {{ label }}
  </span>
</template>

<script setup lang="ts">
const props = defineProps<{ status: string; map: Record<string, { label: string; class: string }> }>();
const item = computed(() => props.map[props.status] ?? { label: props.status, class: "bg-gray-100 text-gray-600" });
const badgeClass = computed(() => item.value.class);
const label = computed(() => item.value.label);
</script>
```

### WorkflowActions.vue

```vue
<!-- Renders action buttons based on current workflow_state and user role -->
<template>
  <div class="border-t pt-4 mt-4">
    <component :is="actionComponent" :dr="dr" @action-completed="emit('refresh')" />
  </div>
</template>
```

### BaseModal.vue (dùng cho confirm dialogs)

```vue
<template>
  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div class="bg-white rounded-xl shadow-xl p-6 max-w-md w-full mx-4">
        <slot />
        <div class="flex gap-3 mt-6 justify-end">
          <BaseButton variant="ghost" @click="emit('cancel')">Hủy</BaseButton>
          <BaseButton variant="danger" @click="emit('confirm')">{{ confirmLabel }}</BaseButton>
        </div>
      </div>
    </div>
  </Teleport>
</template>
```

---

## 10. API Calls Map

| User Action | Store Action | API Endpoint |
|---|---|---|
| Chọn asset trong form | `checkAssetEligibility(asset)` | `get_suspension_list` |
| Lưu nháp | `createSuspensionRequest(payload)` | `create_suspension_request` |
| Gửi đánh giá KT | `createSuspensionRequest + transition` | `create_suspension_request` |
| Hoàn thành đánh giá KT | `submitTechnicalReview(payload)` | `submit_technical_review` |
| Từ chối KT | `submitTechnicalReview({approved: false})` | `submit_technical_review` |
| Lưu Replacement Review | `submitReplacementReview(payload)` | `submit_replacement_review` |
| VP Phê duyệt | `approveSuspension(payload)` | `approve_suspension` |
| VP Từ chối | `approveSuspension({approved: false})` | `approve_suspension` |
| Bắt đầu điều chuyển | `executeTransfer({action: "start"})` | `execute_transfer` |
| Hoàn thành điều chuyển | `executeTransfer({action: "complete"})` | `execute_transfer` |
| Submit ngừng sử dụng | `completeSuspension(payload)` | `complete_suspension` |
| Hủy phiếu | `cancelSuspensionRequest(payload)` | `cancel_suspension_request` |
| Load dashboard | `fetchDashboardMetrics(year)` | `get_dashboard_metrics` |
| Load retirement list | `fetchRetirementCandidates()` | `get_retirement_candidates` |
| Lịch sử điều chuyển | direct API call | `get_transfer_history` |

---

## 11. UX Flows

### 11.1 Happy Path — Ngừng sử dụng (Retire)

```
HTM Manager
  → /imm13/suspensions/new
  → Chọn asset (xem card thông tin)
  → Điền form + Lưu nháp → Toast: "Phiếu DR-26-04-00001 đã tạo"
  → Gửi đánh giá KT → Redirect: /imm13/suspensions/DR-26-04-00001
Biomed Engineer
  → Nhận notification email
  → Mở phiếu → Tab Chi tiết → Action panel: Đánh giá KT
  → Điền reviewer, residual risk, notes → Hoàn thành → Toast: "Chuyển sang Review thay thế"
HTM Manager
  → Mở /imm13/suspensions/:id/review
  → Chọn outcome = Retire → Lưu quyết định → Redirect detail
VP Block2
  → Nhận notification → Mở phiếu → Action panel: Phê duyệt
  → Điền approval_notes → Phê duyệt → Toast: "Đã phê duyệt"
CMMS Admin
  → Hoàn thành checklist → Submit phiếu
  → Toast: "Ngừng sử dụng hoàn tất. IMM-14 đã mở: AAR-26-04-00001"
  → Link hiện: [Xem IMM-14 →]
```

### 11.2 Happy Path — Điều chuyển

```
HTM Manager → Tạo DR → [Outcome = Transfer] → Điền location + receiving_officer
  → State: Approved for Transfer → Notification → Network Manager
Network Manager → Mở phiếu → [Bắt đầu điều chuyển]
  → State: Transfer In Progress → Hoàn thành checklist
  → [Hoàn thành điều chuyển]
CMMS Admin → Submit → State: Transferred
  → Asset.location cập nhật → Asset.status = Transferred
```

### 11.3 Error States

| Lỗi | UI Hiển thị |
|---|---|
| Asset có WO mở | Inline error banner đỏ ngay dưới SmartSelect |
| Bio-hazard thiếu clearance | Field `bio_hazard_clearance` border đỏ + error text |
| Residual risk missing | Toast error khi bấm Hoàn thành |
| Data destruction chưa confirm | Dialog xác nhận trước khi submit |
| API lỗi 403 | Toast: "Bạn không có quyền thực hiện thao tác này." |
| API lỗi 500 | Toast: "Lỗi hệ thống. Vui lòng thử lại hoặc liên hệ CMMS Admin." |

### 11.4 Loading States

- List view: skeleton rows (5 hàng)
- Detail view: skeleton cards + skeleton action panel
- Submit/action buttons: loading spinner thay thế text, disabled khi đang gọi API
- Dashboard: skeleton charts

---

## 12. Icons (Lucide Vue Next)

| Ngữ cảnh | Icon |
|---|---|
| Module header | `PowerOff` |
| Tạo phiếu | `PlusCircle` |
| Đánh giá KT | `Stethoscope` |
| Residual risk Low | `ShieldCheck` |
| Residual risk High | `ShieldAlert` |
| Bio-hazard | `AlertTriangle` |
| Data destruction | `ShieldOff` |
| Regulatory | `FileCheck2` |
| Transfer | `ArrowRightLeft` |
| Checklist | `ClipboardList` |
| Timeline / History | `History` |
| Dashboard | `BarChart2` |
| Retirement candidate | `Flag` |
| Completed / OK | `CheckCircle` |
| Cancelled / Error | `XCircle` |
| Pending | `Clock` |
| Link to IMM-14 | `Archive` |

---

## 13. Responsive Breakpoints

| Breakpoint | Layout |
|---|---|
| `xl` (≥ 1280px) | Form 3-column grid; Table full columns; Dashboard 2x2 chart grid |
| `lg` (≥ 1024px) | Form 2-column; Table hide secondary columns |
| `md` (≥ 768px) | Form 2-column; Table scroll horizontal |
| `sm` (< 768px) | Form single column; Table card view; Sticky action bar bottom |

### Mobile-specific

- Sticky bottom action bar với primary action button
- Swipeable tabs trong Detail View
- Collapsible sections trong Create View
- Pull-to-refresh trong List View

---

*End of UI/UX Guide v2.0.0 — IMM-13 Ngừng sử dụng và Điều chuyển*
