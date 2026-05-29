# 06 — Thiết kế Frontend (Frontend Design / UI-UX Guide)

| Mục | Giá trị |
|---|---|
| Module | IMM-04 — Lắp đặt, Định danh & Kiểm tra Ban đầu |
| Phạm vi | Per-module |
| Owner | FE Lead + Designer |
| Module accent | `violet-600` (installation / commissioning) |

---

## 1. Sitemap / Route map

> Source of truth: `frontend/src/router/index.ts` (Section 3 — IMM-04 Commissioning)

| Route | Route name | Component thực tế | Mô tả |
|---|---|---|---|
| `/commissioning` | `CommissioningList` | `views/commissioning/CommissioningListView.vue` | Danh sách phiếu nghiệm thu |
| `/commissioning/new` | `CommissioningCreate` | `views/commissioning/CommissioningCreateView.vue` | Tạo phiếu mới |
| `/commissioning/:id` | `CommissioningDetail` | `views/commissioning/CommissioningDetailView.vue` | Chi tiết phiếu |
| `/commissioning/:id/nc` | `CommissioningNC` | `views/commissioning/CommissioningNCView.vue` | Quản lý Non Conformance |
| `/commissioning/:id/timeline` | `CommissioningTimeline` | `views/commissioning/CommissioningTimelineView.vue` | Lịch sử vòng đời |

**Không có:** route riêng cho dashboard (`/imm-04/dashboard`), checklist, handover, hay documents tab — các chức năng này được tích hợp vào `CommissioningDetailView` hoặc chưa implement route riêng.

> **Quyết định implement (2026-05-29):** KPI dashboard KHÔNG tách route riêng `/imm-04/dashboard`. 5 KPI (`get_dashboard_stats`) được render trực tiếp dưới dạng **KPI strip trên đầu list page `/commissioning`** (`CommissioningListView`), tái dùng `WorkOrderKpiStrip` + `KpiCard` — đồng pattern với IMM-08/09. Mỗi KPI clickable → quick-filter danh sách ngay tại chỗ. Chi tiết KPI→API field + click action xem §3.1.

---

## 2. Sidebar nav module

```ts
"imm-04": {
  title: "IMM-04 · Lắp đặt & Nghiệm thu",
  accent: "violet-600",
  items: [
    { icon: "chart-bar",     label: "Tổng quan",           to: "/imm-04/dashboard" },
    { icon: "clipboard-list",label: "Danh sách phiếu",     to: "/imm-04" },
    { icon: "plus-circle",   label: "Tạo phiếu mới",       to: "/imm-04/new" },
    { icon: "clock",         label: "Phiếu quá hạn SLA",   to: "/imm-04?filter=overdue" },
    { icon: "shield-exclaim",label: "Clinical Hold",        to: "/imm-04?filter=clinical_hold" },
  ],
}
```

---

## 3. Thiết kế giao diện

### 3.a. UI Mockup (pre-build)

**Mockup 1 — Dashboard (`/imm-04/dashboard`):**
```
┌──────────────────────────────────────────────────────────────────────┐
│ IMM-04 — Lắp đặt & Nghiệm thu Thiết bị              [+ Tạo phiếu]  │
│ ──────────────────────────────────────────────────────────────────── │
│ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌─────────┐│
│ │ Đang mở   │ │ Clinical  │ │ NC mở     │ │ Release   │ │ Quá hạn ││
│ │   12      │ │ Hold  2   │ │  3        │ │ tháng này │ │   1     ││
│ │           │ │           │ │           │ │    8      │ │         ││
│ └───────────┘ └───────────┘ └───────────┘ └───────────┘ └─────────┘│
│                                                                       │
│ ┌─── Theo trạng thái ───┐  ┌─── 5 phiếu gần đây ─────────────────┐ │
│ │ Identification:  5    │  │ ACC-26-04-001 Identification 18/04   │ │
│ │ Initial Insp:    4    │  │ ACC-26-04-002 Clinical Hold  17/04   │ │
│ │ Clinical Hold:   2    │  │ ...                                   │ │
│ │ Non Conformance: 1    │  └───────────────────────────────────────┘ │
│ └───────────────────────┘                                             │
└──────────────────────────────────────────────────────────────────────┘
```

**Mockup 2 — List view (`/imm-04`):**
```
┌──────────────────────────────────────────────────────────────────────┐
│ Danh sách Phiếu Nghiệm thu                       [+ Tạo phiếu mới] │
│ ──────────────────────────────────────────────────────────────────── │
│ [Trạng thái ▼]  [Thiết bị ▼]  [Nhà cung cấp ▼]  [🔍 Tìm kiếm...]  │
│                                                                       │
│ ┌──────────────┬──────────────┬──────────────┬──────────────────────┐│
│ │ Mã phiếu    │ Thiết bị     │ Trạng thái   │ Ngày nhận / SLA      ││
│ ├──────────────┼──────────────┼──────────────┼──────────────────────┤│
│ │ ACC-26-04-001│ Máy X-Ray   │ 🟣 Nhận diện │ 18/04 — còn 12 ngày ││
│ │ ACC-26-04-002│ Monitor ICU │ 🔴 Tạm giữ LS│ 17/04 — ⚠️ 33 ngày  ││
│ └──────────────┴──────────────┴──────────────┴──────────────────────┘│
│  ◀ 1 2 3 ▶   Hiển thị 1-20/47                                         │
└──────────────────────────────────────────────────────────────────────┘
```

**Mockup 3 — Detail view (`/imm-04/:id`):**
```
┌──────────────────────────────────────────────────────────────────────┐
│ ← Quay lại      ACC-26-04-00001 — Máy X-Ray Philips                 │
│                                   [🟣 Đang nhận diện]  [Nút action]  │
│ ──────────────────────────────────────────────────────────────────── │
│  [Thông tin] [Hồ sơ (3)] [Đo kiểm] [NC (1)] [Lịch sử] [Bàn giao]   │
│                                                                       │
│  Số phiếu:  ACC-26-04-00001    PO:         PO-2026-00023             │
│  Thiết bị:  Máy X-Ray Philips  Nhà CC:     Philips Healthcare VN     │
│  Khoa:      Khoa CĐHA          Rủi ro:     ● C [Nguy cơ cao]        │
│  Ngày nhận: 18/04/2026         SN NCC:     PHI-SN98765               │
│  Mã nội bộ: BV-CDHA-2026-0001  [In mã QR]                            │
│                                                                       │
│  ⚠️ Thiết bị phân loại C — yêu cầu QA sign-off trước Clinical Release│
└──────────────────────────────────────────────────────────────────────┘
```

**Mockup 4 — Form tạo phiếu mới (`/imm-04/new`):**
```
┌──────────────────────────────────────────────────────────────────────┐
│ Tạo Phiếu Nghiệm thu Mới                         [Hủy] [Lưu Draft] │
│ ──────────────────────────────────────────────────────────────────── │
│ Đơn Mua Hàng*: [🔍 Tìm PO...        ▼]                              │
│   → Sau khi chọn PO, tự động điền: Thiết bị, Nhà cung cấp          │
│                                                                       │
│ Thiết bị*:     [Auto-fill từ PO    ▼]  Phân loại rủi ro: [C ●]     │
│ Nhà cung cấp*: [Auto-fill từ PO    ▼]  Thiết bị bức xạ:  ☑         │
│ Khoa lắp đặt*: [🔍 Khoa CĐHA       ▼]                               │
│ Ngày lắp (dự kiến)*: [📅 20/04/2026  ]                               │
│                                                                       │
│  ⚠️ Thiết bị phân loại C/D/Radiation cần có Giấy phép trước Release  │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.b. UI Screenshot (post-build)

Lưu ảnh tại `docs/imm-04/screenshots/`:
- `01_dashboard.png` — Dashboard KPI
- `02_list.png` — Danh sách phiếu
- `03_detail_identification.png` — Chi tiết state Identification
- `04_checklist.png` — Trang đo kiểm baseline
- `05_clinical_hold_alert.png` — Alert Clinical Hold

### 3.c. Trang chi tiết theo archetype

#### 3.1. KPI strip (trên đầu list page `/commissioning`)

> Bám `docs/res/design/design-frontend.md §3.1` và `docs/fe/04-commissioning/commissioning-list.html`. Render qua `WorkOrderKpiStrip` + `KpiCard` (pattern IMM-08/09), KHÔNG route riêng.

**KPI cards (display summary — đồng pattern IMM-08/09, dùng chung `WorkOrderKpiStrip` không clickable):**
| KPI | API field | Màu | Ghi chú |
|---|---|---|---|
| Phiếu đang mở | `kpis.pending_count` | primary | Tổng phiếu non-terminal |
| Clinical Hold | `kpis.hold_count` | warning | |
| NC mở | `kpis.open_nc_count` | danger | |
| Release tháng này | `kpis.released_this_month` | success | |
| Quá hạn SLA | `kpis.overdue_sla` | neutral | |

> Quyết định reuse: dùng `WorkOrderKpiStrip` (display-only, giống IMM-08/09) thay vì tự build card clickable — tránh sửa shared component đang dùng ở module khác. **Click-to-quick-filter là enhancement tương lai** (cần thêm param `overdue` ở list endpoint cho KPI "Quá hạn SLA" + thống nhất UX), ghi backlog, KHÔNG implement vòng này để giữ scope đóng kín.
>
> Mapping kpis→strip items: hàm thuần `commissioningKpiItems()` (`views/commissioning/commissioningKpi.ts`, có vitest `commissioningKpi.test.ts`).

**API gọi:** `get_dashboard_stats` (store `fetchDashboardStats`) — fetch song song với `fetchList` trong `onMounted`.
**State:** strip ẩn khi chưa có dữ liệu (`v-if="items.length"`). KPI fetch **non-blocking**: dùng `dashboardError` riêng, KHÔNG đụng `error`/`loading` của list (KPI lỗi không che list skeleton/banner).

#### 3.2. List (`/imm-04`)

**Filter bar:**
| Filter | Type | Default |
|---|---|---|
| Trạng thái | MultiSelect | Tất cả |
| Thiết bị | LinkSearch `Item` | — |
| Nhà cung cấp | LinkSearch `Supplier` | — |
| Tìm kiếm | text | — |

**Cột bảng:**
| Cột | Render |
|---|---|
| Mã phiếu | Link đến detail |
| Thiết bị | `master_item` tên tự nhiên + mã nhỏ |
| Trạng thái | `<StatusBadge>` màu per-state |
| Ngày nhận | date + SLA countdown nếu >30 ngày |
| NCC | vendor name |

**Action:** Click row → navigate detail | Nút `+ Tạo phiếu mới`

#### 3.3. Detail (`/imm-04/:id`)

**Header:** tên thiết bị (lớn) + mã phiếu (nhỏ, mono) + `<StatusBadge>` + `<ActionBar>`

**Tabs:** Thông tin · Hồ sơ · Đo kiểm · NC · Lịch sử · Bàn giao

**Tab Thông tin:** Form editable theo state (chỉ edit được ở state ≤ Identification)

**Tab Đo kiểm:** Inline table checklist — kết quả Pass/Fail/N/A per row. Nút "Nộp kết quả" (enable khi 100% rows có result).

**Tab Lịch sử:** Timeline `<AssetLifecycleTimeline>` — read-only, immutable.

**API gọi:** `get_form_context` — cache detail key `['imm04', 'detail', name]`

#### 3.4. Form tạo mới (`/imm-04/new`)

**Sections:** Đơn Mua Hàng → Thông tin Thiết bị → Khoa & Thời gian → Lưu

**State:** Loading spinner khi submit. Disable nút khi form có lỗi.

---

## 4. Component custom của module

| Component | Mục đích | Props chính |
|---|---|---|
| `StatusBadge.vue` | Hiển thị trạng thái phiếu với màu | `status: CommissioningStatus, size?: 'sm'\|'md'\|'lg'` |
| `ActionBar.vue` | Nút hành động theo state + role | `status, userRole[], hasOpenNc, allDocsReceived, allChecklistPass` |
| `BarcodeScanner.vue` | Scan QR/barcode camera hoặc USB HID | `mode: 'camera'\|'usb-hid', expectedFormat?` |
| `RiskClassBadge.vue` | Badge màu đỏ nếu C/D/Radiation | `riskClass: string` |
| `AssetLifecycleTimeline.vue` | Timeline lifecycle events immutable | `events: AssetLifecycleEvent[]` |
| `ClinicalHoldAlert.vue` | Alert Clinical Hold với danh sách doc thiếu | `riskClass, qaOfficer, missingLicenses[]` |
| `BaselineChecklistTable.vue` | Table đo kiểm inline editable | `items: CommissioningChecklist[], readonly: boolean` |

Đặt trong `frontend/src/components/imm04/`. Component dùng ≥ 2 module → promote ra `components/common/`.

---

## 5. Pinia store

> Source of truth: `frontend/src/stores/imm04.ts`

**File thực tế:** `frontend/src/stores/imm04.ts` (renamed từ `commissioning.ts` để align convention `immXX.ts`).

Store được export bằng `useCommissioningStore` (giữ tên symbol để giảm churn — xem các views: `CommissioningListView.vue`, `CommissioningCreateView.vue`, `CommissioningDetailView.vue`, components `CommissioningForm.vue`, `AssetDashboard.vue`).

Store dùng Composition API pattern (`defineStore('commissioning', () => {...})`).

**API calls:** Import từ `@/api/imm04` — tất cả function theo naming convention camelCase: `getFormContext`, `listCommissioning`, `transitionState`, `saveCommissioning`, `createCommissioning`, v.v.

---

## 6. Vue Query keys

```ts
// frontend/src/api/imm04.ts
export const imm04Keys = {
  dashboard: ['imm04', 'dashboard'] as const,
  list: (filters: ListFilters) => ['imm04', 'list', filters] as const,
  detail: (name: string) => ['imm04', 'detail', name] as const,
  snCheck: (sn: string) => ['imm04', 'sn-check', sn] as const,
}
```

**Invalidate sau mutation:**
```ts
// Sau submit_commissioning:
queryClient.invalidateQueries({ queryKey: ['imm04', 'list'] })
queryClient.invalidateQueries({ queryKey: ['imm04', 'detail', name] })
queryClient.invalidateQueries({ queryKey: ['imm04', 'dashboard'] })
```

---

## 6b. API call pattern — useApi().run()

```ts
// CommissioningDetailPage.vue
import { useApi } from '@/composables/useApi'
import { submitCommissioning } from '@/api/imm04'

const api = useApi()
const formErrors = reactive<Record<string, string>>({})

async function onSubmitCommissioning() {
  const result = await api.run(
    () => submitCommissioning({ name: props.id }),
    {
      successMessage: 'Phiếu đã Submit. Tài sản đã được tạo.',
      onFieldError: (fields) => Object.assign(formErrors, fields),
    }
  )
  if (result) {
    // result = response.data (đã unwrap envelope)
    router.push(`/assets/${result.final_asset}`)
  }
}
```

---

## 6c. TypeScript types

```
frontend/src/types/
├── common.ts          # Paginated<T>, ApiResponse<T>, ApiError
├── imm04.ts           # CommissioningStatus, AssetCommissioning, CommissioningChecklist, ...
└── inventory.ts       # Asset cross-module
```

Type mirror BE DTO 1-1: `CommissioningStatus` values khớp `workflow_state` trong DB.

---

## 7. Quy tắc ngôn ngữ FE

### 7.a. Nguyên tắc cứng
- 100% tiếng Việt mọi label, button, message, toast, error inline
- Mã phiếu (ACC-...) hiển thị nhỏ bên dưới tên tự nhiên, font-mono, `text-xs text-slate-500`
- State value tiếng Anh (`Clinical Release`) map qua i18n → tiếng Việt trên UI

### 7.b. Entity display pattern

```
┌────────────────────────────────────────┐
│ Máy X-quang Philips DigitalDiagnost    │ ← tên tự nhiên (font-semibold)
│ ACC-26-04-00001 · ITM-XRAY-001         │ ← mã (text-xs text-slate-500 font-mono)
└────────────────────────────────────────┘
```

### 7.c. Bảng từ ngữ chuẩn hóa

| Khái niệm | Tiếng Việt | Tránh từ |
|---|---|---|
| Asset Commissioning | Phiếu Nghiệm thu | Commissioning, Commission |
| Clinical Release | Phát hành lâm sàng | Release, Published |
| Clinical Hold | Tạm giữ lâm sàng | Hold, Suspended |
| Non Conformance | Không phù hợp | NC, Lỗi |
| Baseline test | Đo kiểm an toàn điện | Test, Kiểm tra |
| DOA | Hỏng ngay khi nhận | Dead-on-Arrival |
| Board approver | Người phê duyệt BGĐ | Approver |
| Biên bản bàn giao | Biên bản bàn giao | Handover document |

---

## 7d. Linked / Cascade fields

### 7d.a. Quan hệ phụ thuộc
- `po_reference` → auto-fill `vendor`, `master_item`, `risk_class`
- `master_item` → auto-fill `risk_class`, `is_radiation_device`
- `risk_class ∈ {C, D, Radiation}` → hiện field `qa_officer`, row License trong documents
- `is_radiation_device=1` → hiện field `radiation_license_no`

### 7d.b. Hành vi chuẩn
- Field cha thay đổi → field con reset + reload options
- Khi `po_reference` rỗng → `master_item` disabled + placeholder "Chọn PO trước"

### 7d.c. Pattern code

```ts
// CommissioningFormPage.vue
const poReference = ref<string | null>(null)
const masterItem = ref<string | null>(null)
const riskClass = ref<string | null>(null)

watch(poReference, async (newPo) => {
  masterItem.value = null
  riskClass.value = null
  if (!newPo) return
  const details = await getPoDetails({ po_name: newPo })
  if (details) {
    vendor.value = details.supplier
    // pre-fill item nếu chỉ có 1
    if (details.items.length === 1) masterItem.value = details.items[0].item_code
  }
})

watch(masterItem, async (item) => {
  if (!item) return
  const itemDoc = await fetchItemDetails(item)
  riskClass.value = itemDoc?.custom_risk_class ?? null
  isRadiation.value = itemDoc?.custom_is_radiation ?? false
})
```

---

## 7e. Input tight

### 7e.a. Ưu tiên picker
| Loại input | Dùng |
|---|---|
| Ngày | `<DateInput>` mask `dd/mm/yyyy` |
| PO, Item, Supplier | `<LinkSearch>` autocomplete |
| Risk class | `<RadioChip>` A / B / C / D / Radiation |
| Kết quả đo kiểm | `<RadioChip>` Pass / Fail / N/A |
| Số đo (mA, Ω…) | number input + unit SmartSelect |

### 7e.b. Validation realtime
- Serial Number: `check_sn_unique` on-blur, debounce 300ms
- Required fields: inline error khi blur
- Nút "Nộp kết quả đo kiểm" disabled khi còn row chưa có result

### 7e.c. Confirm modal
- Submit phiếu (Clinical Release → docstatus=1): confirm modal với checkbox "Tôi xác nhận hành động này"
- Cancel phiếu: confirm modal với tóm tắt hành động
- Return To Vendor: confirm modal danger (đỏ)

---

## 8. Empty / Error / Loading copy

| Tình huống | Copy |
|---|---|
| Danh sách phiếu rỗng | "Chưa có phiếu nào. Tạo phiếu đầu tiên từ PO." |
| Không có quyền xem | "Bạn không có quyền xem trang này. Liên hệ CMMS Admin." |
| Đang tải | Skeleton 5 dòng bảng |
| Lỗi server | "Có lỗi xảy ra. Vui lòng thử lại hoặc liên hệ hỗ trợ." |
| Submit thành công | "Phiếu đã Submit. Tài sản [asset_id] đã được tạo." |
| Concurrent error | "Phiếu vừa được cập nhật bởi người dùng khác. Tải lại để xem thay đổi mới nhất." |
| Clinical Hold alert | "Thiết bị [risk_class] phải có giấy phép BYT trước khi đưa vào lâm sàng (NĐ142/2020)." |
| Baseline có Fail | "Các tiêu chí sau không đạt: [list]. Phiếu phải chuyển về Tái kiểm tra." |

---

## 9. Accessibility checklist module

- `<ActionBar>` buttons có `aria-label` đầy đủ tiếng Việt
- `<StatusBadge>` có `role="status"` + `aria-label="Trạng thái: {tên tiếng Việt}"`
- `<BarcodeScanner>` có `aria-live="polite"` cho kết quả scan
- Form fields có `<label>` liên kết `for` + `id`
- Clinical Hold alert: `role="alert"` để screen reader đọc ngay
- Keyboard navigation: Tab order hợp lý (PO → Item → NCC → Khoa → Ngày)
- Color contrast WCAG AA: Risk class badge đỏ đảm bảo contrast ≥ 4.5:1

---

## 10. Print spec

Trang cần in: **Biên bản Bàn giao** (sau khi phiếu ở Clinical Release).

- Generate server-side qua Frappe Print Format `Biên bản Bàn giao`
- ⚠️ TODO: Print Format chưa được config — `generate_handover_pdf` trả URL nhưng PDF có thể fail
- Layout: 1 cột, A4, ẩn navigation chrome
- Nội dung: thông tin phiếu, SN, QR, danh sách hồ sơ, kết quả đo kiểm, chữ ký BGĐ

---

## DoD — File 06 hoàn chỉnh

- [x] Sitemap đủ mọi route module
- [x] UI Mockup ≥ 4 màn hình chính
- [x] Sidebar nav config
- [x] Mỗi archetype có table columns / form section / state mapping
- [x] Component custom liệt kê với props
- [x] Type definitions mirror BE (file 05 §1.5)
- [x] State phân lớp: server data → Vue Query, UI state → Pinia
- [x] Vue Query keys + invalidate rule
- [x] Quy tắc ngôn ngữ FE: 100% tiếng Việt + entity display pattern
- [x] Bảng từ ngữ chuẩn hóa
- [x] Cascade fields: po_reference → item → risk_class
- [x] Input tight: picker + validation realtime + confirm modal
- [x] Empty / Error / Loading copy đủ
- [x] Accessibility checklist module
- [x] Print spec
