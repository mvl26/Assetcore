# IMM-09 — Frontend Design

| Thuộc tính | Giá trị |
|---|---|
| Module | **IMM-09 — Corrective Maintenance / Repair** |
| Phiên bản tài liệu | 1.0 |
| Ngày cập nhật | 2026-05-08 |
| Trạng thái | Chuẩn hóa từ IMM-09_UI_UX_Guide.md |
| Stack | Vue 3 + TypeScript + Pinia + TanStack Vue Query + TailwindCSS |

---

## §I Sitemap & Routes

```
/imm-09/                        → CMDashboard   (Workshop Manager / PTP)
/imm-09/list                    → CMList        (Danh sách WO, filter, tìm kiếm)
/imm-09/create                  → CMCreate      (Tạo WO mới)
/imm-09/:name                   → CMDetail      (Chi tiết WO, action theo status)
/imm-09/:name/diagnose          → CMDiagnose    (Form chẩn đoán, status = Diagnosing)
/imm-09/:name/parts             → CMParts       (Quản lý vật tư, Pending Parts / In Repair)
/imm-09/:name/checklist         → CMChecklist   (Nghiệm thu sau sửa, Pending Inspection)
/imm-09/reports/mttr            → CMMttr        (MTTR Dashboard)
```

### Route Guards

```typescript
// router/imm09.ts — component paths match actual file locations in views/cm/
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/imm-09',
    component: () => import('@/views/cm/CMDashboardView.vue'),
    meta: { roles: ['Workshop Manager', 'PTP Khối 2', 'CMMS Admin'] },
  },
  {
    path: '/imm-09/list',
    component: () => import('@/views/cm/CMWorkOrderListView.vue'),
    meta: { roles: ['Workshop Manager', 'KTV HTM', 'PTP Khối 2', 'CMMS Admin'] },
  },
  {
    path: '/imm-09/create',
    component: () => import('@/views/cm/CMCreateView.vue'),
    meta: { roles: ['Workshop Manager', 'CMMS Admin'] },
  },
  {
    path: '/imm-09/:name',
    component: () => import('@/views/cm/CMWorkOrderDetailView.vue'),
    meta: { roles: ['Workshop Manager', 'KTV HTM', 'Trưởng khoa', 'PTP Khối 2', 'CMMS Admin'] },
  },
  {
    path: '/imm-09/:name/diagnose',
    component: () => import('@/views/cm/CMDiagnoseView.vue'),
    meta: { roles: ['KTV HTM', 'Workshop Manager', 'CMMS Admin'] },
  },
  {
    path: '/imm-09/:name/parts',
    component: () => import('@/views/cm/CMPartsView.vue'),
    meta: { roles: ['KTV HTM', 'Workshop Manager', 'Kho vật tư', 'CMMS Admin'] },
  },
  {
    path: '/imm-09/:name/checklist',
    component: () => import('@/views/cm/CMChecklistView.vue'),
    meta: { roles: ['KTV HTM', 'Workshop Manager', 'CMMS Admin'] },
  },
  {
    path: '/imm-09/reports/mttr',
    component: () => import('@/views/cm/CMMttrView.vue'),
    meta: { roles: ['Workshop Manager', 'PTP Khối 2', 'CMMS Admin'] },
  },
]

export default routes
```

### Sidebar Navigation

```typescript
// sidebar config (accent = rose-600 — màu cảnh báo phân biệt với PM)
{
  label: 'Sửa chữa (IMM-09)',
  icon: 'wrench',
  accent: 'rose-600',
  children: [
    { label: 'Dashboard', path: '/imm-09' },
    { label: 'Danh sách WO', path: '/imm-09/list' },
    { label: 'Tạo phiếu mới', path: '/imm-09/create', roles: ['Workshop Manager', 'CMMS Admin'] },
    { label: 'Báo cáo MTTR', path: '/imm-09/reports/mttr', roles: ['Workshop Manager', 'PTP Khối 2', 'CMMS Admin'] },
  ],
}
```

---

## §II Mockups

### CMCreate — Tạo Phiếu Sửa Chữa

```
┌─────────────────────────────────────────────────────────────────┐
│  Tạo Phiếu Sửa Chữa                                 [Hủy] [Tạo]│
├─────────────────────────────────────────────────────────────────┤
│  Thông tin thiết bị                                             │
│  ┌────────────────────────────┐  ┌──────────────────────────┐  │
│  │ Thiết bị *                 │  │ Số Serial               │  │
│  │ [Link Search: Asset    ▼] │  │ [Auto-fill, read-only]  │  │
│  └────────────────────────────┘  └──────────────────────────┘  │
│  ┌────────────────────────────┐  ┌──────────────────────────┐  │
│  │ Phân loại nguy cơ          │  │ Khoa / Phòng            │  │
│  │ [Auto-fill: Class III]     │  │ [Auto-fill from Asset]  │  │
│  └────────────────────────────┘  └──────────────────────────┘  │
│  ── AssetInfoCard: model, manufacturer, warranty status ──      │
│                                                                 │
│  Nguồn sửa chữa (tùy chọn — BR-09-01 đã nới)                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  ○ Sự cố (Incident):  [IR-2026-XXXXX         ▼ Search] │   │
│  │  ○ Phiếu PM dừng:     [PM-WO-2026-XXXXX      ▼ Search] │   │
│  │  ○ Độc lập (Standalone) — không gắn nguồn               │   │
│  └─────────────────────────────────────────────────────────┘   │
│  Ghi chú: từ patch BR-09-01, repair có thể tạo độc lập           │
│  (standalone) không cần Incident/PM. Nguồn chỉ optional.         │
│                                                                 │
│  Loại & Ưu tiên                                                 │
│  ┌────────────────────────────┐  ┌──────────────────────────┐  │
│  │ Loại sửa chữa *            │  │ Ưu tiên *               │  │
│  │ [Corrective         ▼]    │  │ [Normal            ▼]   │  │
│  └────────────────────────────┘  └──────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Mô tả sự cố ban đầu *                                   │   │
│  │ [Text area — mô tả triệu chứng hỏng hóc]               │   │
│  └─────────────────────────────────────────────────────────┘   │
│  [⚠ Banner repeat failure nếu thiết bị hỏng trong 30 ngày]    │
└─────────────────────────────────────────────────────────────────┘
```

### CMDetail — Chi tiết WO (layout 60/40)

```
┌─────────────────────────────────────────────────────────────────┐
│  WO-CM-2026-00042  [RepairStatusBadge: IN REPAIR]               │
│  Máy thở Drager Evita V800 — ICU 3                              │
├───────────────────────────────────┬─────────────────────────────┤
│  LEFT (60%)                       │  RIGHT (40%)                │
│                                   │                             │
│  [AssetInfoCard]                  │  [RepairSlaIndicator]       │
│  Model, Serial, Risk Class        │  Đã trôi: 6h 23m / 24h SLA│
│  Khoa phòng, Vị trí              │  [████████░░] 67%           │
│                                   │  ⏸ [SlaPausedBadge khi      │
│                                   │   status=Pending Parts]:     │
│                                   │  "Chờ phụ tùng — SLA tạm  │
│                                   │   dừng" (amber, BR-09-10)    │
│                                   │                             │
│  [RepairSourceBadge]              │  [DurationTimer]            │
│  📋 IR-2026-00123                 │  ⏱ 06:23:15                │
│                                   │                             │
│  [RepairRepeatFailureBanner]      │  Kỹ thuật viên: Nguyễn V.A │
│  (nếu is_repeat_failure = true)   │  Phân công: 14/04 08:30     │
│                                   │                             │
│  Chẩn đoán                        │  Vật tư: 3 mục / 1.25Mđ    │
│  ┌──────────────────────────────┐ │  Checklist: 0 / 5 Pass     │
│  │ Nguyên nhân: Điện            │ │                             │
│  │ Mô tả: Tụ điện board nguồn  │ │  [RepairActionBar]          │
│  │ bị cháy                      │ │  [Cập nhật chẩn đoán]      │
│  └──────────────────────────────┘ │  [Quản lý vật tư]          │
│                                   │  [Bắt đầu sửa chữa]       │
│  [RepairStatusTimeline]           │                             │
│  ● Open — 14/04 07:15             │                             │
│  ● Assigned — 14/04 08:30         │                             │
│  ● In Repair — 14/04 10:00 ←      │                             │
│  [LifecycleEventLog — collapsible]│                             │
└───────────────────────────────────┴─────────────────────────────┘
```

### CMDiagnose — Form Chẩn Đoán

```
┌─────────────────────────────────────────────────────────────────┐
│  Chẩn đoán — WO-CM-2026-00042         [Hủy] [Lưu chẩn đoán]   │
├─────────────────────────────────────────────────────────────────┤
│  Nguyên nhân gốc rễ *                                           │
│  [Electrical ▼]  [Mechanical ▼]  [Software ▼]                   │
│  [User Error ▼]  [Wear and Tear ▼]  [Unknown ▼]                 │
│                                                                 │
│  Mô tả chi tiết chẩn đoán *                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ [Rich text area — mô tả kỹ thuật, bộ phận bị hỏng]    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Ảnh thiết bị hỏng                                              │
│  [📷 Upload ảnh]  [img1.jpg ×]  [img2.jpg ×]                   │
│                                                                 │
│  Yêu cầu vật tư?                                               │
│  [○ Không cần vật tư → tiếp tục sửa chữa ngay]               │
│  [● Cần vật tư    → chuyển Pending Parts   ]                  │
│                                                                 │
│  Cập nhật Firmware trong lần sửa này?                          │
│  [☐ Có — sẽ yêu cầu tạo Firmware Change Request]             │
│                                                                 │
│  Dự kiến hoàn thành: [Date picker] [Time picker]               │
└─────────────────────────────────────────────────────────────────┘
```

### CMParts — Quản Lý Vật Tư

```
┌─────────────────────────────────────────────────────────────────┐
│  Vật tư sửa chữa — WO-CM-2026-00042              [Lưu vật tư]  │
├─────────────────────────────────────────────────────────────────┤
│  Tìm vật tư: [🔍 Tìm theo mã hoặc tên...                    ]  │
│                                                                 │
│  ┌────┬────────────┬─────────────┬────┬─────┬──────────┬───┐   │
│  │ #  │ Mã vật tư  │ Tên         │ SL │ ĐVT │ Đơn giá  │ × │   │
│  ├────┼────────────┼─────────────┼────┼─────┼──────────┼───┤   │
│  │ 1  │ CAP-100UF  │ Tụ 100uF   │ 2  │ Cái │ 25,000đ  │ × │   │
│  │    │ Phiếu XK: [STE-2026-00456        ] ✓ Hợp lệ   │   │   │
│  ├────┼────────────┼─────────────┼────┼─────┼──────────┼───┤   │
│  │ 2  │ FUSE-5A    │ Cầu chì 5A │ 1  │ Cái │ 15,000đ  │ × │   │
│  │    │ Phiếu XK: [                      ] ⚠ Chưa điền │   │   │
│  └────┴────────────┴─────────────┴────┴─────┴──────────┴───┘   │
│  [+ Thêm vật tư]                                               │
│                                                                 │
│  Tổng chi phí vật tư:                           40,000 VNĐ     │
│  ⚠ Tất cả vật tư phải có phiếu xuất kho (BR-09-02)            │
└─────────────────────────────────────────────────────────────────┘
```

### CMChecklist — Nghiệm Thu Sau Sửa Chữa

```
┌─────────────────────────────────────────────────────────────────┐
│  Nghiệm thu — WO-CM-2026-00042                                  │
│  [ChecklistProgressBar: 3 / 5 mục Pass  ████████░░░░]          │
├─────────────────────────────────────────────────────────────────┤
│  #1 Electrical — Kiểm tra điện áp đầu vào         [Pass ✓]    │
│     Yêu cầu: 220V ± 5%   │ Đo được: [218V         ]           │
│     [📷 Ảnh bằng chứng]  ⚠ Cần ảnh (Class C/D)   [thumb ✓]   │
│                                                                 │
│  #2 Electrical — Kiểm tra cầu chì thay thế        [Pass ✓]    │
│     Yêu cầu: 5A           │ Đo được: [5A           ]           │
│     [📷 Ảnh bằng chứng]                                        │
│                                                                 │
│  #3 Safety — Kiểm tra rò điện vỏ thiết bị         [Fail ✗]    │
│     ⚠ Kết quả Fail — không thể hoàn thành         (highlight đỏ)│
│     Ghi chú: [                                             ]   │
│                                                                 │
│  #4 Performance — Test chức năng tạo áp            [─ Chưa]   │
│     [Pass] [Fail] [N/A]    │ Đo được: [             ]          │
│                                                                 │
│  #5 Performance — Test báo động                    [─ Chưa]   │
│     [Pass] [Fail] [N/A]    │ Đo được: [             ]          │
│                                                                 │
│  Xác nhận trưởng khoa phòng                                     │
│  Họ tên: [                      ]  Chức danh: [             ] │
│                                                                 │
│  [Hoàn thành sửa chữa]  ← disabled cho đến khi 100% Pass      │
└─────────────────────────────────────────────────────────────────┘
```

**UX flow — đính ảnh bằng chứng theo mục checklist (BR-09-15/16, mobile CR-15/G6):**
- Mỗi hàng checklist có **1 control upload ảnh** (nút "📷 Ảnh bằng chứng"), gọi `POST attach_repair_checklist_photo` **multipart** với `work_order_name`, `checklist_item_idx` (= **Frappe child `idx`** của hàng, 1-based), `file`. Sau success (`{file_url, file_name, checklist_item_idx}`) → hiển thị **thumbnail** từ `repair_checklist[idx].photo` (đã có sẵn trong `get_repair_work_order` — KHÔNG cần refetch toàn phiếu ngoài invalidate cache TanStack).
- **Gate hiển thị control:** chỉ KTV được giao (`assigned_to`) hoặc role có `repair.write` (mirror gate nút action theo `allowed_transitions`, KHÔNG hardcode `status===`); WO ở trạng thái đang thực hiện (không terminal). Class C/D (`risk_class`) → badge "⚠ Cần ảnh" nhắc bằng chứng NĐ98.
- **Max 1 ảnh/mục** (single Attach — server chặn ảnh thứ 2 → `"Mỗi mục checklist chỉ đính 1 ảnh"`); `photo` field hiện ảnh đã đính làm thumbnail. Bộ nhiều-ảnh/mục = `[ROADMAP]` (cần chuyển `photo` → child table nếu nghiệp vụ đòi >1 ảnh).
- **Xử lý lỗi Decision-B:** đọc `error.code` + `error.fields.file` từ envelope HTTP-200 → hiển thị message VN dưới control upload (VALIDATION: thiếu file/sai định dạng/quá 10 MB/đã có ảnh; FORBIDDEN: "Không có quyền đính ảnh…"). KHÔNG dựa status-line (lỗi nghiệp vụ đến HTTP-200).

### CMList — Danh Sách WO

```
┌─────────────────────────────────────────────────────────────────┐
│  Danh sách Phiếu Sửa Chữa             [+ Tạo WO] [↓ Export]   │
├────────────┬─────────────────┬──────────┬──────────┬───────────┤
│  [Status▼] │ [Dept▼]         │ [Kỹ thuật viên▼] │ [Prior▼] │ [🔍]│
├────────────┴─────────────────┴──────────────────┴──────────┴────┤
│ Số WO          │ Thiết bị      │ Status        │ Kỹ thuật viên │ SLA │ │
├────────────────┼───────────────┼───────────────┼────────┼──────┤ │
│ WO-CM-2026-042 │ Máy thở ICU3  │ 🔴 In Repair  │ Anh    │  67% │ │
│ WO-CM-2026-041 │ Monitor P305  │ 🟡 P.Parts    │ Bình   │  40% │ │
│ WO-CM-2026-040 │ Defib Ward2   │ 🟢 Completed  │ Cường  │ 100% │ │
│ WO-CM-2026-039 │ Infusion P2   │ 🔵 Open       │ —      │  10% │ │
├────────────────┴───────────────┴───────────────┴────────┴──────┘ │
│  Trang 1/3        [← Trước] [1] [2] [3] [Tiếp →]               │
└─────────────────────────────────────────────────────────────────┘
```

**Status badge colors (Tailwind):**

| Status | Class |
|---|---|
| Open | `bg-blue-100 text-blue-700` |
| Assigned | `bg-blue-600 text-white` |
| Diagnosing | `bg-purple-100 text-purple-700` |
| Pending Parts | `bg-amber-100 text-amber-700` |
| In Repair | `bg-orange-100 text-orange-700` |
| Pending Inspection | `bg-sky-100 text-sky-700` |
| Completed | `bg-green-100 text-green-700` |
| Cannot Repair | `bg-red-600 text-white` |
| Cancelled | `bg-gray-100 text-gray-500` |

### CMMttr — MTTR Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│  MTTR Dashboard — Tháng 4/2026         [Xuất PDF] [Xuất Excel] │
├─────────────────────────────────────────────────────────────────┤
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────┐  │
│  │ MTTR TB    │  │ First Fix  │  │ Backlog    │  │ CP/Sửa  │  │
│  │ 18.5 giờ  │  │ 87.5%      │  │ 12 WO      │  │ 450Kđ   │  │
│  │ ↓2.1h T3  │  │ ↑3% vs T3 │  │ 3 khẩn     │  │         │  │
│  └────────────┘  └────────────┘  └────────────┘  └──────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  [MttrTrendChart — Line chart 6 tháng]                         │
│   T11=22h  T12=19h  T1=25h  T2=21h  T3=20.6h  T4=18.5h        │
│   ── SLA target Class III: 24h ──                              │
├─────────────────────────────────────────────────────────────────┤
│  [BacklogBarChart — Backlog theo Khoa/Phòng]                   │
│  ICU:   ████████ 4    OR:  ████ 2    Radiology: ██ 1           │
├─────────────────────────────────────────────────────────────────┤
│  [FtfrGaugeChart — First-Time Fix Rate: 87.5%  🟢 > mục tiêu] │
└─────────────────────────────────────────────────────────────────┘
```

---

## §III Components

### Component Tree

```
views/cm/                              ← thư mục thực tế
├── CMDashboardView.vue        — KPI cards + backlog + SLA alerts
├── CMWorkOrderListView.vue    — Danh sách WO có filter + phân trang + tìm kiếm SERVER (CR-18)
├── CMCreateView.vue           — Tạo WO mới
├── CMWorkOrderDetailView.vue  — Hub chính, routing theo status
├── CMDiagnoseView.vue         — Form chẩn đoán
├── CMPartsView.vue            — Quản lý vật tư
├── CMChecklistView.vue        — Form nghiệm thu
└── CMMttrView.vue             — MTTR dashboard + charts

components/repair/
├── RepairStatusBadge.vue         — Badge màu theo status
├── RepairStatusTimeline.vue      — Timeline lịch sử trạng thái
├── RepairActionBar.vue           — Nút hành động thay đổi theo status
├── RepairSlaIndicator.vue        — Progress bar SLA + màu động (xám khi Pending Parts, BR-09-10)
├── SlaPausedBadge.vue            — Badge "Chờ phụ tùng — SLA tạm dừng" khi Pending Parts (BR-09-10)
├── RepairSummaryCard.vue         — Card tóm tắt WO
├── RepairSourceBadge.vue         — Badge IR / PM WO nguồn
└── RepairRepeatFailureBanner.vue — Banner cảnh báo tái hỏng

components/parts/
├── SparePartsTable.vue         — Bảng vật tư + thêm/xóa
├── PartSearchCombobox.vue      — Tìm kiếm Item, debounce 300ms
└── StockEntryLinkField.vue     — Link phiếu xuất kho + validate real-time

components/checklist/
├── ChecklistForm.vue           — Form điền từng mục
├── ChecklistProgressBar.vue    — Progress X/Y Pass
└── ChecklistResultBadge.vue    — Badge Pass / Fail / N/A

components/firmware/
├── FirmwareFcrCard.vue         — Hiển thị FCR linked
└── FirmwareFcrCreate.vue       — Form tạo FCR mới

components/shared/
├── AssetInfoCard.vue           — Thông tin thiết bị (model, serial, risk class)
├── DurationTimer.vue           — Đồng hồ thời gian sửa chữa realtime
└── LifecycleEventLog.vue       — Danh sách Asset Lifecycle Event

components/charts/
├── MttrTrendChart.vue          — Line chart MTTR theo tháng
├── BacklogBarChart.vue         — Bar chart backlog theo dept
└── FtfrGaugeChart.vue          — Gauge chart First-Time Fix Rate
```

> 🆕 **CR-18 (tìm kiếm free-text phía SERVER — BR-09-LISTSEARCH/BR-09-17):** ô "Tìm phiếu" trên `CMWorkOrderListView.vue` chuyển sang refetch SERVER (đối xứng PM `PMWorkOrderListView`).
> - **Trước (search-trap):** `search` ref client; `filteredWOs` computed (`CMWorkOrderListView.vue:146-153`) lọc `store.workOrders` (CHỈ trang đang tải) theo `name`/`asset_name` `toLowerCase().includes` ⇒ phiếu trang 2+ KHÔNG hiện dù khớp.
> - **Sau:** `search` ref → **debounce 300ms** → truyền `search` như tham số riêng cho `store.fetchWorkOrders(buildFilters(), 1, search.value.trim())` → `listRepairWorkOrders(filters, page, pageSize, search)` (discrete query-param). Đổi `search` → **reset `page=1`** + refetch SERVER. **GỠ** `filteredWOs` (render thẳng `store.workOrders`); GỠ mọi `filteredWOs.length`/`?? filteredWOs.length` (subtitle "Tổng {total}" + "Hiển thị N" + empty-state) → dùng `store.pagination.total` / `store.workOrders.length`. **GIỮ** chip `search` (`activeChips` key `'search'`; xóa chip → clear `search` + refetch). Placeholder giữ "Tìm theo mã lệnh, tên thiết bị...".
> - **Kết quả phủ MỌI trang:** BE OR-LIKE `name`/`asset_code`/`asset_name` toàn tập; FE KHÔNG lọc lại. File: `frontend/src/views/cm/CMWorkOrderListView.vue`, `frontend/src/api/imm09.ts` (`listRepairWorkOrders` +`search`), `frontend/src/stores/imm09.ts` (`fetchWorkOrders` forward `search`).

### Component Archetype Detail

| Component | Props | Events | Mô tả |
|---|---|---|---|
| `RepairStatusBadge` | `status: RepairStatus` | — | Pill badge màu Tailwind |
| `RepairStatusTimeline` | `transitions: AleRecord[]` | — | Vertical timeline từ ALE |
| `RepairActionBar` | `status`, `roles`, `disabled` | `action(event)` | Nút hành động theo ACTION_MAP |
| `RepairSlaIndicator` | `slaPercent`, `targetHours` | — | Progress bar màu động (green/yellow/orange/red) |
| `DurationTimer` | `openDatetime`, `status` | — | Đồng hồ realtime, dừng khi terminal state |
| `PartSearchCombobox` | `query` | `select(item)` | Combobox với debounce 300ms |
| `StockEntryLinkField` | `value`, `valid` | `change(ref)` | Input + validate icon ✓ / ⚠ |
| `ChecklistProgressBar` | `passed`, `total` | — | Thanh tiến trình Pass / total |

---

## §IV Pinia Store

File: `frontend/src/stores/imm09.ts` — dùng direct API function imports (không dùng `api.run(string)`).

```typescript
// stores/imm09.ts — tên state/action chính xác
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  listRepairWorkOrders, getRepairWorkOrder, assignTechnician,
  submitDiagnosis, closeWorkOrder, getRepairKPIs, getAssetRepairHistory,
  requestSpareParts, startRepair, getMttrReport, createRepairWorkOrder,
  searchSpareParts,
  type AssetRepair, type RepairKPIs, type MttrReport, type SparePartRow,
} from '@/api/imm09'

export const useImm09Store = defineStore('imm09', () => {
  // ── State ─────────────────────────────────────────────────────
  const workOrders  = ref<AssetRepair[]>([])    // tên thực tế: workOrders (không phải woList)
  const currentWO   = ref<AssetRepair | null>(null)
  const kpis        = ref<RepairKPIs | null>(null)
  const repairHistory = ref<any[]>([])
  const mttrReport  = ref<MttrReport | null>(null)
  const loading     = ref(false)                // tên thực tế: loading (không phải isLoading)
  const error       = ref<string | null>(null)
  const pagination  = ref({ page: 1, total: 0, total_pages: 0, page_size: 20 })

  // ── Computed ──────────────────────────────────────────────────
  const openWOs = computed(() => workOrders.value.filter(w => w.status === 'Open'))
  // BR-09-07 LIVE: live-truth ?? cờ thô — KHÔNG chỉ cờ stale stamped-by-scheduler.
  // BE list_work_orders enrich `is_sla_breached` (open & vượt hạn & cờ chưa stamp).
  const breachedWOs = computed(() => workOrders.value.filter(w => w.is_sla_breached ?? w.sla_breached))
  const checklistComplete = computed(() => {
    if (!currentWO.value) return false
    return currentWO.value.repair_checklist.every(r => r.result !== null)
  })

  // ── Schema-contract delta (BR-09-07 LIVE) ─────────────────────
  // `api/imm09.ts` interface AssetRepair: THÊM optional field
  //   is_sla_breached?: boolean   // BE list_work_orders derive live (bool(sla_breached) || _row_is_live_overdue)
  // Giữ `sla_breached: boolean` (cờ thô vẫn trả). Badge/computed đọc `is_sla_breached ?? sla_breached`
  // (live ưu tiên; fallback cờ thô khi endpoint chưa enrich — forward/backward compat).

  // ── Schema-contract delta (BR-09-10 clock-stop) ───────────────
  // `api/imm09.ts` interface AssetRepair: THÊM optional field
  //   parts_hold_hours?: number   // tổng giờ WO nằm Pending Parts (BE cộng dồn)
  //   sla_paused?: boolean        // BE derive (status === 'Pending Parts') — SLA đang tạm dừng
  // mttr_hours BE gửi ĐÃ là clock-stop (= (completion−open) − parts_hold_hours).
  // FE render mttr_hours VERBATIM — TUYỆT ĐỐI KHÔNG tự tính lại từ open/completion
  //   (transport-agnostic; tránh divergence card vs BE). SlaPausedBadge đọc
  //   `sla_paused ?? (status === 'Pending Parts')` (fallback nếu endpoint chưa enrich).

  // ── Actions (tên chính xác) ───────────────────────────────────
  async function fetchWorkOrders(filters = {}, page = 1): Promise<void>
  async function fetchWorkOrder(name: string): Promise<void>
  function updateChecklistResult(idx: number, updates: Partial<AssetRepair['repair_checklist'][0]>): void
  async function doAssignTechnician(name: string, technician: string, priority?: string): Promise<boolean>
  async function doSubmitDiagnosis(diagnosisNotes: string, needsParts: boolean): Promise<boolean>
  async function doCloseWorkOrder(payload: Parameters<typeof closeWorkOrder>[0]): Promise<boolean>
  async function fetchKPIs(year?: number, month?: number): Promise<void>
  async function fetchRepairHistory(assetRef: string): Promise<void>
  async function fetchMttrReport(year: number, month: number): Promise<void>
  async function doSaveParts(woName: string, parts: SparePartRow[]): Promise<boolean>
  async function doStartRepair(woName: string): Promise<boolean>
  async function doCreateRepairWorkOrder(payload: Parameters<typeof createRepairWorkOrder>[0]): Promise<string | null>
  function doSearchSpareParts(query: string): Promise<SparePartRow[]>

  return {
    workOrders, currentWO, kpis, repairHistory, mttrReport, loading, error, pagination,
    openWOs, breachedWOs, checklistComplete,
    fetchWorkOrders, fetchWorkOrder, updateChecklistResult,
    doAssignTechnician, doSubmitDiagnosis, doCloseWorkOrder,
    fetchKPIs, fetchRepairHistory, fetchMttrReport, doSaveParts, doStartRepair,
    doCreateRepairWorkOrder, doSearchSpareParts,
  }
})
```

---

## §V Vue Query Keys & Invalidation

```typescript
// queryKeys/imm09.ts
export const imm09Keys = {
  all:              () => ['imm09'] as const,
  woList:           (filters = {}) => ['imm09', 'list', filters] as const,
  woDetail:         (name: string) => ['imm09', 'detail', name] as const,
  kpis:             (year: number, month: number) => ['imm09', 'kpis', year, month] as const,
  mttr:             (year: number, month: number) => ['imm09', 'mttr', year, month] as const,
  repairHistory:    (assetRef: string) => ['imm09', 'history', assetRef] as const,
}
```

**Invalidation rules:**

| Action | Invalidate |
|---|---|
| `create_repair_work_order` | `woList` |
| `assign_technician` | `woDetail(name)`, `woList` |
| `submit_diagnosis` | `woDetail(name)` |
| `request_spare_parts` | `woDetail(name)` |
| `start_repair` | `woDetail(name)` |
| `close_work_order` | `woDetail(name)`, `woList`, `kpis(*)`, `mttr(*)`, `repairHistory(asset_ref)` |

---

## §VI Client Logic

### DurationTimer — Đồng hồ realtime

```typescript
// components/shared/DurationTimer.vue
import { ref, onMounted, onUnmounted, computed } from 'vue'

const TERMINAL_STATUSES = ['Completed', 'Cannot Repair', 'Cancelled']

const props = defineProps<{ openDatetime: string; status: string }>()
const elapsed = ref(0)
let timer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  const start = new Date(props.openDatetime).getTime()
  const update = () => { elapsed.value = Math.floor((Date.now() - start) / 1000) }
  update()
  if (!TERMINAL_STATUSES.includes(props.status)) {
    timer = setInterval(update, 1000)
  }
})
onUnmounted(() => { if (timer) clearInterval(timer) })

const display = computed(() => {
  const h = Math.floor(elapsed.value / 3600)
  const m = Math.floor((elapsed.value % 3600) / 60)
  const s = elapsed.value % 60
  return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`
})
```

### RepairActionBar — Action mapping theo status

> ⚠️ **SUPERSEDED bởi «CMWorkOrderDetail — 6 CTA server-driven» (AC-CR-82, 2026-07-27) — giữ lại làm dấu vết lịch sử, KHÔNG implement theo.** `ACTION_MAP` dưới đây gate bằng **tên vai trò** (`roles: ['KTV HTM']`) và **hardcode `status → button`** — đúng 2 anti-pattern mà GATE-8/LL-FE-51 cấm (RBAC dead-gate + drift 2 nơi). Nguồn sự thật mới = `available_actions[]` do server phát.

```typescript
// ACTION_MAP: RepairStatus → list of action buttons
import type { RepairStatus } from '@/types/imm09'

interface ActionButton {
  label: string
  event: string
  roles: string[]
  variant?: 'primary' | 'danger'
}

const ACTION_MAP: Record<RepairStatus, ActionButton[]> = {
  'Open':               [{ label: 'Phân công kỹ thuật viên', event: 'assign',          roles: ['Workshop Manager'] }],
  'Assigned':           [{ label: 'Bắt đầu chẩn đoán',     event: 'diagnose',         roles: ['KTV HTM'] }],
  'Diagnosing':         [{ label: 'Lưu chẩn đoán',          event: 'save_diagnosis',   roles: ['KTV HTM'] }],
  'Pending Parts':      [{ label: 'Xác nhận đã có vật tư', event: 'parts_received',   roles: ['KTV HTM', 'Workshop Manager'] }],
  'In Repair': [
    { label: 'Hoàn thành sửa chữa', event: 'finish_repair', roles: ['KTV HTM'] },
    { label: 'Không thể sửa',       event: 'cannot_repair',  roles: ['KTV HTM', 'Workshop Manager'], variant: 'danger' },
  ],
  'Pending Inspection': [{ label: 'Nộp kết quả nghiệm thu', event: 'submit_checklist', roles: ['KTV HTM'] }],
  'Completed':          [],
  'Cannot Repair':      [],
  'Cancelled':          [],
}
```

### CMWorkOrderDetail — 6 CTA server-driven TỪ `available_actions[]` (AC-CR-82, GATE-8 · LL-FE-51) 🔴 SPEC (FE Bước-4)

**Nguồn dữ liệu.** `get_repair_work_order` trả `available_actions`: mảng **đúng 6** phần tử, thứ tự cố định `[assign_technician, submit_diagnosis, request_spare_parts, start_repair, close_work_order, confirm_inspection]`, shape `{key, label, route, enabled, reason}` (`route` luôn `""` — CTA nằm **trong** màn, KHÔNG deep-link). `enabled`/`reason` do **SERVER** quyết (hợp đồng [`05 §15`](./05_API_Specification.md)) — FE **chỉ render**.

**Mirror 1:1 `PMWorkOrderDetailView.vue`** (AC-CR-77 đã LIVE): tái dùng **nguyên** khuôn `serverActions` / `isServerDriven` / `actionEnabled` / `actionReason` / `blockedActions` — **không** phát minh khuôn thứ hai.

```typescript
// frontend/src/views/cm/CMWorkOrderDetailView.vue
const serverActions = computed<AvailableAction[] | null>(() => {
  const list = wo.value?.available_actions
  return Array.isArray(list) && list.length > 0 ? list : null
})
const isServerDriven = computed(() => serverActions.value !== null)
```

**Bảng nối nút ↔ khoá server (7 nút / 6 khoá — `Cannot Repair` KHÔNG phải khoá thứ 7):**

| `data-testid` | `key` server | Hành vi khi bấm | Ghi chú |
|---|---|---|---|
| `cta-assign` | `assign_technician` | mở modal phân công | giữ nguyên |
| `cta-diagnose` | `submit_diagnosis` | `navigateDiagnose()` | nhãn lấy **từ `label` server** — bỏ `diagnoseLabel` client (hết suy "Bắt đầu" vs "Cập nhật" từ `allowed_transitions`) |
| `cta-parts` | `request_spare_parts` | `navigateParts()` | |
| **`cta-start-repair`** | `start_repair` | `store.doStartRepair(id)` | **NÚT MỚI** — đóng dead-end D-CM-3 (endpoint `api/imm09.py:136` LIVE nhưng màn Chi tiết chưa có đường vào; trước đây chỉ tới được từ `CMPartsView.vue:122`) |
| `cta-complete` | `close_work_order` | `navigateChecklist()` | |
| `cta-cannot-repair` | `close_work_order` | mở modal "không thể sửa" | **DÙNG CHUNG khoá** (cùng endpoint, cờ `cannot_repair=1`) ⇒ enable/disable **theo cùng** action object |
| `cta-confirm-inspection` | `confirm_inspection` | `doConfirmInspection()` | tooltip mang `reason` SoD khi bị khoá |

**Quy tắc render (Always):**

| | |
|---|---|
| Map action | `const actionMap = computed(() => Object.fromEntries((serverActions.value ?? []).map(a => [a.key, a])))` |
| Bật/tắt | `:disabled="!actionEnabled(a) || actionBusy(a)"` — **KHÔNG** tự tính lại từ `status`/`allowed_transitions` khi đã có `available_actions` |
| Lý do | `:title="actionReason(a) || undefined"` + `:aria-label` + danh sách `blockedActions` dạng **chữ** (`🔒 <label>: <reason>`) — nút `disabled` không nhận focus nên screen-reader không đọc được `title` |
| Nhãn | lấy **từ `label` server** (đã là tiếng Việt đầy đủ) — FE **KHÔNG** bịa chuỗi, KHÔNG dịch lại, KHÔNG hiển thị mã trạng thái thô |
| Terminal | `Completed`/`Cannot Repair`/`Cancelled` ⇒ cả 6 `enabled=false`: **ẩn cụm CTA**, giữ nhãn tĩnh hiện có ("Đã hoàn thành" / "Không thể sửa chữa" / "Đã huỷ") — tránh 6 nút xám vô nghĩa |
| **Fallback bắt buộc** | payload **thiếu** `available_actions` (BE chưa reload / client cũ) ⇒ rơi về **đúng logic hiện tại** (`can(...) && allowedTransitions.includes(...)`, `CMWorkOrderDetailView.vue:113-138`) — **KHÔNG nút nào biến mất**, KHÔNG màn trắng |
| Trục cục bộ | chỉ được **SIẾT thêm** bằng điều kiện SERVER KHÔNG THẤY (form chưa lưu) — **KHÔNG nới** |

**Test bắt buộc — `frontend/src/views/cm/cmDetailCtaGating.test.ts` (mirror `sessionDetailCtaGating.test.ts`):**

| TC | Kỳ vọng |
|---|---|
| `FE-CMCTA-1` | `available_actions` có `assign_technician.enabled=false` + `reason` ⇒ nút `cta-assign` **hiện**, `disabled`, `title` == `reason` (đọc từ **DOM**, không từ store) |
| `FE-CMCTA-2` | **INVARIANT A9** — với 9 payload (mỗi status 1 payload): **không** `data-testid^="cta-"` nào ở trạng thái enabled mà `key` tương ứng ∉ tập `available_actions` có `enabled=true` |
| `FE-CMCTA-3` | `start_repair.enabled=true` ⇒ `cta-start-repair` **hiện & bấm được**; click gọi `store.doStartRepair` **đúng 1 lần** |
| `FE-CMCTA-4` | payload **KHÔNG** có `available_actions` ⇒ 6 nút cũ vẫn render theo đường fallback (0 nút biến mất) |
| `FE-CMCTA-5` | `available_actions` **không** chứa key `cancel`/`cannot_repair` ⇒ màn **không** render nút hủy phiếu; `cta-cannot-repair` bám `close_work_order` |
| `FE-CMCTA-6` | status terminal (`Completed`) ⇒ 0 nút CTA render, nhãn tĩnh "Đã hoàn thành" hiện |
| `FE-CMCTA-7` | `confirm_inspection.enabled=false` + reason SoD ⇒ chuỗi reason xuất hiện **dạng chữ** trong DOM (không chỉ tooltip) |

**Never (FE):** ❌ tự tính lại `enabled` từ `status`/`allowed_transitions` khi đã có `available_actions` · ❌ ẩn nút disabled (mất thông tin lý do) · ❌ gate bằng **tên vai trò** · ❌ hardcode nhãn/tooltip tiếng Anh hoặc mã trạng thái thô · ❌ render nút hủy phiếu (server không phát ⇒ FE không được vẽ).

### FirmwareCrDetailView — gate nút theo `allowed_transitions` + `can_approve` (BR-09-20, GATE-8 · LL-FE-51)

> 🔴 **Self-Correction (Vòng 10):** `FirmwareCrDetailView.vue` HIỆN TẠI (a) đổi status bằng `updateFirmwareCr(name, {status:'Approved'})` (CRUD chung — lỗ bảo mật: Repair User tự Approve, KHÔNG audit) và (b) gate nút bằng hardcode `fcr.status === 'Draft' || 'Pending Approval'` / `fcr.status === 'Approved'` (dead-gate). **Sửa:** gọi endpoint transition riêng + gate 100% nút theo `allowed_transitions` + `can_approve` server-derived. **0 hardcode `fcr.status==='X'`** trên NÚT (badge/step-indicator/text hiển thị status = display-only, được phép).

```typescript
// api/imm00.ts — FirmwareCR type += 2 field server-derived + 4 transition fn
export interface FirmwareCR {
  name: string; asset_ref: string; status: string
  version_before: string; version_after: string; /* ... */
  allowed_transitions?: string[]   // đã LỌC theo capability caller (server)
  can_approve?: 0 | 1               // rbac.can("firmware.approve")
}
export const submitFirmwareCr   = (name: string) => frappePost(`${BASE.i9}.submit_firmware_cr`,   { name })
export const approveFirmwareCr  = (name: string) => frappePost(`${BASE.i9}.approve_firmware_cr`,  { name })
export const deployFirmwareCr   = (name: string) => frappePost(`${BASE.i9}.deploy_firmware_cr`,   { name })
export const rollbackFirmwareCr = (name: string, rollback_reason: string) =>
  frappePost(`${BASE.i9}.rollback_firmware_cr`, { name, rollback_reason })
```

```vue
<!-- FirmwareCrDetailView.vue — CTA gate 100% server-driven -->
<script setup lang="ts">
const at = computed(() => fcr.value?.allowed_transitions ?? [])
const canApprove = computed(() => fcr.value?.can_approve === 1)
const showSubmit   = computed(() => at.value.includes('Pending Approval'))  // Gửi duyệt
const showApprove  = computed(() => at.value.includes('Approved') && canApprove.value)
const showDeploy   = computed(() => at.value.includes('Applied'))           // Triển khai
const showRollback = computed(() => at.value.includes('Rolled Back'))       // Hoàn tác (mở modal nhập lý do)
// KHÔNG còn approve() gọi updateFirmwareCr({status}); mỗi nút gọi endpoint transition riêng,
// sau đó await load() để nhận allowed_transitions/can_approve mới.
</script>
```

- **Ánh xạ nút ↔ cạnh:** Gửi duyệt→`submitFirmwareCr` · Duyệt→`approveFirmwareCr` · Triển khai→`deployFirmwareCr` · Hoàn tác→`rollbackFirmwareCr(reason)` (bắt buộc modal nhập `rollback_reason`).
- **Repair User** xem FCR Pending Approval: server trả `allowed_transitions=[]`, `can_approve=0` ⇒ KHÔNG nút Duyệt. Nếu vẫn POST (spoof) → BE trả `FORBIDDEN` HTTP-200 → toast VN inline (KHÔNG echo traceback — LL-FE-Finding-C).
- **Manager/Super Admin:** `allowed_transitions=['Approved']`, `can_approve=1` ⇒ hiện nút Duyệt.
- Step-indicator/`StatusBadge` GIỮ đọc `fcr.status` (display-only — KHÔNG phải gate nút). Test FE `FirmwareCrDetail.test.ts`: grep 0 `fcr.status ===` trong khối `<template>` nút hành động; render nút đúng theo `allowed_transitions` fixture.

### PartSearchCombobox — Debounce search

```typescript
// components/parts/PartSearchCombobox.vue
import { useDebounceFn } from '@vueuse/core'
import { useApi } from '@/composables/useApi'

const api = useApi()
const searchResults = ref<{ item_code: string; item_name: string; qty_in_stock: number; unit_cost: number }[]>([])

const searchParts = useDebounceFn(async (query: string) => {
  if (query.length < 2) return
  const res = await api.run('assetcore.api.imm09.search_spare_parts', { query, limit: 20 })
  searchResults.value = res.data
}, 300)
```

### SparePartSuggestion — hợp đồng gợi ý phụ tùng 13 khoá + bỏ cast bịa (CR-73a, 2026-07-25)

> 🔴 SPEC CHỐT 2026-07-25 ([BA] Bước-2) — FE thực thi ở **Bước-4**. Nguồn: [`05_API_Specification.md §3.13-bis`](./05_API_Specification.md) + BR-09-21 + ADR-IMM09-SPARE-01.
> ⚠️ Snippet `PartSearchCombobox` phía trên là **mockup cũ** — khoá `qty_in_stock` **KHÔNG tồn tại** trong response. Giữ để truy vết, KHÔNG dùng làm hợp đồng.

**Kiểu (SSoT `frontend/src/api/imm09.ts`):** thêm `SparePartSuggestion` **13 khoá** (xem `05 §6`). **KHÔNG** nhồi 3 field mới vào `SparePartRow` — `SparePartRow` là row `spare_parts_used` của phiếu (`CMPartsView.addPart` dựng bằng spread), thêm field bắt buộc vào đó sẽ vỡ mọi nơi dựng row. `searchSpareParts()` đổi kiểu trả về `Promise<SparePartRow[]>` → `Promise<SparePartSuggestion[]>`.

**Bug đang có (E3) — `CMCreateView.vue:206-218`:**

```typescript
// ❌ HIỆN TẠI — ép kiểu sang shape KHÔNG TỒN TẠI ({name, part_name, stock_qty})
const rows = await searchSpareParts(q) as unknown as Array<{ name: string; part_name: string; stock_qty?: number }>
…
function addPart(p: { name: string; part_name: string }) {
  preRequestParts.value.push({ spare_part: p.name, qty: 1 })   // p.name === undefined
}
```

`p.name` luôn `undefined` ⇒ `preRequestParts` chứa `{spare_part: undefined}` ⇒ `request_spare_parts` lọc bỏ dòng đó (`if (p.get("spare_part") or p.get("item_code"))`) ⇒ **yêu cầu phụ tùng biến mất im lặng**, người dùng không nhận cảnh báo nào.

**Hợp đồng sau CR-73a:**

| Ràng buộc | Chi tiết |
|---|---|
| **0 cast** | `grep -c "as unknown as" quanh searchSpareParts` = **0**. Kiểu đến thẳng từ `SparePartSuggestion`. `vue-tsc --noEmit` XANH. |
| **Khoá chọn** | `addPart(p: SparePartSuggestion)` đẩy `{ spare_part: p.spare_part, qty: 1 }` — **`p.spare_part`**, KHÔNG `p.name`. |
| **Chống trùng** | Khoá de-dup = **`p.spare_part`** khi non-empty; khi `spare_part === ''` de-dup theo cặp **`(device_model, item_code)`** (2 model cùng tên phụ tùng ⇒ 2 dòng hợp lệ, KHÔNG được coi là trùng). |
| **Gợi ý không resolve** | `spare_part === ''` ⇒ **KHÔNG được đẩy vào `preRequestParts`** (dòng đó chắc chắn không tạo được allocation). Hiển thị dòng ở trạng thái *disabled* + nhãn ngắn "Chưa có trong danh mục kho" thay vì im lặng bỏ qua. |
| **Hiển thị 1 dòng gợi ý** | 3 phần, đủ để phân biệt: **tên tiếng Việt** (`item_name`) · **mã NSX** (`manufacturer_part_no`, ẩn nếu rỗng) · **tên model thiết bị** (`device_model_name`; fallback `device_model` nếu rỗng). Chữ hiển thị **tiếng Việt đầy đủ** — không để lộ mã kỹ thuật thô làm nhãn chính. |
| **Áp cho cả 2 view** | `CMCreateView.vue` (pre-request lúc tạo phiếu) **và** `CMPartsView.vue` (thêm vật tư vào phiếu đang mở — hiện nhận `SparePartRow`, phải đổi sang `SparePartSuggestion` rồi map sang row phiếu). |

**Never:** ép kiểu để "cho qua" `vue-tsc` · lọc/suy đoán `spare_part` phía client (khoá do BE cấp) · hiển thị `device_model` (PK thô) làm nhãn chính · dùng `item_code` làm khoá de-dup khi có `spare_part`.

### RepairSlaIndicator — Màu progress bar động

```typescript
// Màu progress bar thay đổi theo mức độ SLA
const slaBarColor = computed(() => {
  // BR-09-10: WO đang Pending Parts → SLA TẠM DỪNG (clock-stop). KHÔNG bôi đỏ
  // "vi phạm" vì đồng hồ đứng yên — hiển thị xám trung tính + badge tạm dừng.
  if (wo.sla_paused ?? wo.status === 'Pending Parts') return 'bg-slate-300'
  if (slaPercent.value >= 100) return 'bg-red-500'    // Đã vi phạm
  if (slaPercent.value >= 75)  return 'bg-orange-500' // Nguy hiểm
  if (slaPercent.value >= 50)  return 'bg-yellow-400' // Cảnh báo
  return 'bg-green-500'                               // Bình thường
})
```

### SlaPausedBadge — Badge "Chờ phụ tùng — SLA tạm dừng" (BR-09-10)

```typescript
// components/repair/SlaPausedBadge.vue — hiện ở CMDetail (RIGHT) + CMList row
// khi WO ở Pending Parts. Văn bản VI cứng, KHÔNG leak EN.
const showPausedBadge = computed(() => props.wo.sla_paused ?? props.wo.status === 'Pending Parts')
// Render: <span class="bg-amber-100 text-amber-700 ...">⏸ Chờ phụ tùng — SLA tạm dừng</span>
```

> **MTTR render — verbatim (BR-09-10):** mọi nơi hiển thị MTTR (CMDetail, CMList, CMMttr dashboard, card KPI) đọc `wo.mttr_hours` BE gửi TRỰC TIẾP (đã clock-stop). KHÔNG có FE-side `(completion − open)/3600`. `DurationTimer` (đồng hồ wall-clock realtime) chỉ là chỉ báo trực quan thời gian đã trôi — KHÔNG dùng để quyết breach/MTTR (đó là việc của BE qua `is_sla_breached`/`repair_elapsed_hours`).
>
> **No-leak EN + vue-tsc 0:** badge + label tiếng Việt; `parts_hold_hours`/`sla_paused` khai báo optional trong `interface AssetRepair` (`api/imm09.ts`) ⇒ `vue-tsc --noEmit` prod = 0 lỗi.

### Source Field Validation — CMCreate form

> **BR-09-01 (đã nới — 2026-05):** Nguồn sửa chữa (`incident_report` / `source_pm_wo`)
> giờ **optional**. Cho phép tạo phiếu sửa chữa độc lập (standalone) khi KTV phát hiện
> hỏng hóc không qua Incident/PM. KHÔNG còn block submit khi thiếu nguồn.
> Form chỉ validate `asset_ref`, `repair_type`, `priority`, `failure_description` là bắt buộc.

```typescript
// Nguồn KHÔNG còn bắt buộc. Nếu user chọn radio "Sự cố"/"PM" thì
// field tương ứng mới required; chọn "Độc lập" → bỏ trống cả hai.
const validateSource = (): boolean => {
  if (sourceMode.value === 'incident' && !form.value.incident_report) {
    sourceError.value = 'Vui lòng chọn Sự cố nguồn'
    return false
  }
  if (sourceMode.value === 'pm' && !form.value.source_pm_wo) {
    sourceError.value = 'Vui lòng chọn Phiếu PM nguồn'
    return false
  }
  sourceError.value = null
  return true   // sourceMode === 'standalone' luôn hợp lệ
}
```

### ListTotal — "Tổng" đọc TỪ `pagination.total`, KHÔNG fallback client-count (INV-ROWSCOPE-FE, 2026-07-25)

> **SSoT:** [`ADR-IMM00-LIST-SCOPE.md` §8.8](../imm-00/ADR-IMM00-LIST-SCOPE.md) · BE contract: `BR-09-LISTSCOPE` (`05_API_Specification.md` §3.1).

**Hiện trạng (bug):** `frontend/src/views/cm/CMWorkOrderListView.vue:165`

```vue
:subtitle="`Tổng ${store.pagination.total ?? store.workOrders.length} lệnh`"   <!-- ❌ -->
```

**Chốt:**

| Nhãn | Nguồn | Ngữ nghĩa |
|---|---|---|
| **"Tổng N lệnh"** (PageHeader subtitle, dòng 165) | `store.pagination.total ?? 0` | **Tổng TOÀN TẬP mọi trang** — SSoT là server (`pagination.total`) |
| **"Hiển thị X lệnh"** (mobile-card dòng ~227, desktop-table dòng ~286) | `store.workOrders.length` — **GIỮ NGUYÊN** | Số dòng **trang hiện tại** |

**Vì sao bỏ fallback `?? store.workOrders.length`** — đây là **fallback nói dối**, hỏng 2 đường:

1. **Sai về phân trang:** `page_size = 20`, 137 phiếu, BE lỗi/chưa nạp `pagination` ⇒ header báo "Tổng 20" (số dòng trang 1) như thể là tổng toàn tập.
2. **Che chính bug row-scope:** trước fix INV-ROWSCOPE, BE trả `total = 2` (đã scope) nhưng 40 rows (chưa scope). Fallback không kích hoạt (total có giá trị) nên header đúng "Tổng 2" — trong khi bảng 40 dòng. Nếu FE quay lại dùng `.length` thì header thành "Tổng 40" ⇒ **bug BE bị che hoàn toàn**, không ai phát hiện rò dữ liệu.

`?? 0` là **fail-visible**: chưa nạp/lỗi ⇒ "Tổng 0" — hiển nhiên sai, người dùng và QA thấy ngay, thay vì một con số hợp lý-giả.

**Guard vitest (BẮT BUỘC — chống fallback quay lại):** `frontend/src/views/cm/` — cùng nhóm với `cmSlaBreachedDivergence.test.ts`.

| TC | Setup | Assert |
|---|---|---|
| FE-RS-01 | `pagination.total = 2`, `workOrders.length = 40` | header chứa `Tổng 2`, **KHÔNG** chứa `Tổng 40` |
| FE-RS-02 | `pagination` chưa nạp (`total` undefined), `workOrders.length = 5` | header chứa `Tổng 0` (KHÔNG `Tổng 5`) |
| FE-RS-03 | như FE-RS-01 | vùng info-row vẫn chứa `Hiển thị 40` (**không** đổi nhầm "Hiển thị" sang `total`) |

> **Áp cho các list view khác:** cùng quy tắc "Tổng = server / Hiển thị = trang" áp cho `PMWorkOrderListView`, `CalibrationListView`, `AssetListView`… — vòng này CHỈ sửa `CMWorkOrderListView` (đề mục), rà phần còn lại = **[BACKLOG-P2]**.

---

### AssetHistoryTruncation — 3 tab lịch sử thiết bị đọc `total`/`truncated` (CR-69, 2026-07-25)

> **SSoT:** BE `assetcore/services/shared/truncation.py::truncation_meta` · CR ledger [`05_API_Specification.md` §10.4](05_API_Specification.md) · OAS mirror `docs/mobile/openapi/assetcore-mobile.openapi.yaml` (3 envelope `AssetPmHistoryEnvelope` / `AssetRepairHistoryEnvelope` / `AssetIncidentHistoryEnvelope`).

**Bối cảnh.** 3 endpoint lịch sử của màn hồ sơ vận hành thiết bị đều cắt cứng theo `limit` (mặc định 10) và **KHÔNG phân trang**. Trước CR-69 chúng cắt **IM LẶNG** — client không có cách nào biết còn phiếu chưa hiển thị. CR-69 bổ sung 2 khoá ADDITIVE cho cả 3.

| Endpoint | rows-key | asset-key | `total` đếm trên |
|---|---|---|---|
| `imm08.get_asset_pm_history` | `history` | `asset_ref` | `PM Task Log` `{asset_ref}` |
| `imm09.get_asset_repair_history` | `history` | `asset_ref` | `Asset Repair` `{asset_ref, docstatus: 1}` |
| `imm12.get_asset_incident_history` | `items` | `asset` | `Incident Report` `{asset}` |

**Hợp đồng FE (đã ship vòng này — chưa dựng UI):**

1. **Kiểu khai OPTIONAL, KHÔNG non-optional.** `total?: number` + `truncated?: 0 | 1` trong `api/imm08.ts` · `api/imm09.ts` · `api/imm12.ts`. Lý do: worker gunicorn `--preload` chưa reload vẫn trả shape CŨ thiếu 2 khoá — khai non-optional là **tái lập đúng lỗi mà CR-69 đi dẹp** (`api/imm08.ts` từng khai `total: number` trong khi BE chưa bao giờ trả ⇒ `undefined` runtime, `vue-tsc` im lặng).
2. **Đọc phòng thủ ở store.** `total ?? rows.length`, `Number(truncated) === 1 ? 1 : 0`. Dùng `Number(...)` chứ **KHÔNG** `=== 1`: nếu BE lỡ regress sang `bool`, `true === 1` là `false` ⇒ dải cảnh báo biến mất âm thầm (bẫy int-vs-bool CR-01).
3. **State đã bộc lộ:** `useImm08Store` → `pmHistoryTotal` / `pmHistoryTruncated`; `useImm09Store` → `repairHistoryTotal` / `repairHistoryTruncated`. IMM-12 chưa có store → view tương lai đọc thẳng API client.

**Quy tắc CÂU CHỮ cho vòng sau (khi dựng dải cảnh báo) — LL-FE-53, tiếng Việt đầy đủ, i18n SSoT:**

| Tình huống | Copy ĐƯỢC dùng | Copy CẤM |
|---|---|---|
| `truncated === 1` | "Đang xem 10 lần gần nhất" · "Chỉ hiển thị 10 bản ghi gần nhất — thiết bị còn lịch sử cũ hơn" | ❌ "Thiết bị đã sửa 10 lần" · ❌ "Toàn bộ lịch sử sửa chữa" · ❌ bất kỳ khẳng định TỔNG nào suy ra từ `rows.length` |
| `truncated === 0` | Được nêu con số: "Tổng 3 lần sửa chữa" (`truncated === 0 ⇒ total === rows.length`, bất biến BE) | ❌ Hiện dải cảnh báo cắt (báo cắt oan khi vừa khít trần) |
| 2 khoá vắng (worker cũ) | Im lặng — KHÔNG banner, KHÔNG con số tổng | ❌ Crash · ❌ suy diễn "đã cắt" |

> ⚠️ **Vì sao cấm khẳng định số lần sửa khi `truncated === 1`:** con số đó đi vào quyết định lâm sàng/thanh lý (thiết bị hỏng lặp lại theo NĐ98). Nói "đã sửa 10 lần" trong khi thực tế 40 lần là **nói dối có hậu quả**, không phải lỗi hiển thị.

**Phạm vi vòng này (CỐ Ý không mở rộng):** chưa `.vue` nào render 3 tab lịch sử ⇒ **KHÔNG dựng UI mới** (tránh scope creep). Guard vitest: `frontend/src/stores/assetHistoryTruncation.test.ts` (11 TC — đủ khoá / thiếu khoá / vừa khít trần / regress bool / naming-contract imm12).

---

### SparePartsStockEntry — cột "Phiếu xuất kho" 3 trạng thái + dải cảnh báo (AC-CR-78, 2026-07-27)

> **SSoT hợp đồng:** [`05_API_Specification.md §13`](05_API_Specification.md) · predicate BE
> [`04_Backend_Design.md §3.8`](04_Backend_Design.md) (ADR-IMM09-PARTS-01/02/03).
> **Đóng CÙNG VÒNG với BE (A8)** — không để lại "state chết" như CR-69.

**Bối cảnh (lỗi đang sống).** `frontend/src/views/cm/CMWorkOrderDetailView.vue:376` render:

```vue
<span v-if="p.stock_entry_ref" class="text-emerald-700 …">{{ p.stock_entry_ref }}</span>
<span v-else class="text-red-600 text-xs">Chưa có</span>
```

⇒ chỉ 2 nhánh. Một `stock_entry_ref` **treo** (trỏ `AC Stock Movement` đã xoá / gõ sai) hiển thị **mã
màu XANH y hệt phiếu hợp lệ** — trong khi validator BR-09-02 sẽ **chặn submit**. Người dùng thấy "đủ
chứng từ", bấm hoàn tất, rồi ăn 422 không hiểu vì sao. Đây là **badge XANH GIẢ**, đúng class-of-bug
display ⇔ enforcement.

#### 1. Kiểu — khai OPTIONAL (bài học CR-69 §AssetHistoryTruncation)

`frontend/src/api/imm09.ts`:

| Kiểu | Khoá thêm | Bắt buộc |
|---|---|---|
| `SparePartRow` | `stock_entry_status?: 'OK' \| 'MISSING' \| 'NOT_FOUND'` · `stock_entry_ok?: 0 \| 1` | **optional** — worker gunicorn `--preload` chưa reload vẫn trả shape CŨ |
| `RepairWorkOrder` | `parts_pending_stock_entry?: number` | **optional** — cùng lý do |

- Đặt cạnh `SparePartRow` hiện có; **KHÔNG** nhồi vào `SparePartSuggestion` (kiểu của `searchSpareParts`,
  vòng đời khác — CR-73a đã tách có chủ đích).
- Đọc phòng thủ: `Number(p.stock_entry_ok) === 1`, `Number(wo.parts_pending_stock_entry) > 0` —
  **KHÔNG** `=== 1` trần trên giá trị có thể là bool (bẫy int-vs-bool CR-01).

#### 2. Cột "Phiếu xuất kho" — 3 nhánh, tiếng Việt ĐẦY ĐỦ (LL-FE-53)

| `stock_entry_status` | Hiển thị | Kiểu chữ |
|---|---|---|
| `OK` | **mã phiếu** (`{{ p.stock_entry_ref }}`) | mono, xanh (emerald) |
| `MISSING` | **"Chưa có phiếu xuất kho"** | amber/đỏ nhạt |
| `NOT_FOUND` | **"Phiếu xuất kho không tồn tại"** + mã treo hiện nhỏ bên dưới (`{{ p.stock_entry_ref }}`, gạch ngang) | đỏ đậm + icon cảnh báo |
| `undefined` (worker cũ) | fallback hành vi CŨ: `p.stock_entry_ref ? mã : "Chưa có phiếu xuất kho"` | như trước — **KHÔNG crash, KHÔNG suy diễn "không tồn tại"** |

- **Header cột đổi** `Phiếu XK` → **`Phiếu xuất kho`** (LL-FE-53: viết đủ tiếng Việt, không viết tắt tự chế).
- Nhánh `MISSING` giữ nguyên ngữ nghĩa cũ nhưng **đủ chữ**: "Chưa có" → "Chưa có phiếu xuất kho".
- ❌ **CẤM** suy diễn lại trạng thái từ `stock_entry_ref` khi BE đã trả `stock_entry_status`
  (đó là viết lại predicate lần 2 — INV-PARTS-1).

#### 3. Dải cảnh báo trên khối "Vật tư sử dụng"

Hiện khi `Number(wo.parts_pending_stock_entry) > 0`:

> ⚠️ **Còn {N} dòng vật tư chưa có phiếu xuất kho hợp lệ — chưa thể hoàn tất phiếu.**

| Điều kiện | Hành vi |
|---|---|
| `parts_pending_stock_entry > 0` | Hiện dải cảnh báo (amber), nêu **đúng N** (KHÔNG tự đếm lại ở FE) |
| `parts_pending_stock_entry === 0` | Không dải cảnh báo |
| `undefined` (worker cũ) | **Im lặng** — KHÔNG banner, KHÔNG suy diễn |
| `spare_parts_used.length === 0` | Khối "Vật tư sử dụng" giữ nguyên `v-if` hiện có (không hiện khối rỗng); banner không áp dụng |

- Copy CẤM: ❌ "Thiếu chứng từ" (mơ hồ) · ❌ "Invalid stock entry" (leak EN) · ❌ "Lỗi dữ liệu".
- ⚠️ Dải cảnh báo là **cảnh báo**, KHÔNG phải khoá nút: gate nút workflow vẫn theo
  `allowed_transitions` (GATE-8 / LL-FE-51) — **KHÔNG** thêm điều kiện `parts_pending_stock_entry`
  vào điều kiện hiển thị nút (server là nơi chặn; FE chỉ báo trước).

#### 4. Test RENDER bắt buộc (chống "state chết" như CR-69)

`frontend/src/views/cm/CMWorkOrderDetailView.sparePartsStockEntry.test.ts` — mount THẬT
(mirror `CMWorkOrderDetailView.riskClassification.test.ts`: mock `vue-router` / `useNotify` /
`useCapabilities` / store `imm09`), assert trên **text đã render**, KHÔNG assert store/type:

| TC | Dữ liệu | Kỳ vọng |
|---|---|---|
| `FE-CM-PARTS-01` | 1 dòng `stock_entry_status: 'OK'`, ref `SM-2026-00042` | text chứa `SM-2026-00042`; KHÔNG chứa "Chưa có phiếu xuất kho"/"không tồn tại" |
| `FE-CM-PARTS-02` | `MISSING` | text chứa **"Chưa có phiếu xuất kho"** |
| `FE-CM-PARTS-03` | `NOT_FOUND`, ref `SM-2026-99999` | text chứa **"Phiếu xuất kho không tồn tại"** (và mã treo vẫn hiện để tra) — **chống revert**: nếu ai đó quay lại `v-if="p.stock_entry_ref"` thì TC này ĐỎ |
| `FE-CM-PARTS-04` | 3 dòng mix + `parts_pending_stock_entry: 2` | dải cảnh báo hiện, text chứa **"Còn 2 dòng vật tư chưa có phiếu xuất kho hợp lệ"** |
| `FE-CM-PARTS-05` | `parts_pending_stock_entry: 0` | **KHÔNG** dải cảnh báo |
| `FE-CM-PARTS-06` | thiếu cả 3 khoá mới (worker cũ) | fallback 2 nhánh cũ, **0 banner**, không crash |
| `FE-CM-PARTS-07` | header bảng | text chứa **"Phiếu xuất kho"** (không còn "Phiếu XK") |

**DoD FE:** `vue-tsc --noEmit` 0 lỗi · `vitest run` xanh · ❌ **KHÔNG** `npm run build`
(ghi thẳng `assetcore/public/frontend` + `emptyOutDir` = deploy live trong khi BE còn stale — LL-DEPLOY-09).

---

### CMEvidencePhoto — trạng thái ẢNH BẰNG CHỨNG NĐ98 trên màn Chi tiết CM (AC-CR-84, 2026-07-27) 🔴 SPEC (FE Bước-4)

> **SSoT hợp đồng:** [`05_API_Specification.md §16`](05_API_Specification.md) · recipe BE
> [`04_Backend_Design.md §3.10`](04_Backend_Design.md) · ADR-IMM09-EVIDENCE-01..05.
> **Đóng CÙNG VÒNG với BE (A8)** — BE chặn mà FE không hiển thị = người dùng ăn lỗi ở bước cuối.

**Bối cảnh (lỗi đang sống).** Web FE đã có predicate ĐÚNG nguồn — `isHighRiskClassification`
(`frontend/src/constants/labels.ts:430-445`, đọc `risk_classification` ∈ {High, Critical}) — nhưng chỉ
dùng để **tô màu** dòng "Phân loại rủi ro"; **0 chỗ** liên hệ nó với ảnh checklist. Client mobile thì có
gate nhưng nuôi bằng `risk_class` (Class I/II/III) nên gate **không bao giờ** bật (mobile CR-51). Sau
AC-CR-84 server mới là nơi chặn — FE **không** được tự phát minh predicate thứ hai, chỉ **đọc** 3 khoá.

#### 1. Kiểu — khai OPTIONAL (bài học CR-69 · AC-CR-82)

`frontend/src/api/imm09.ts` — bồi vào `AssetRepair` (KHÔNG mint interface mới):

```ts
  /** [AC-CR-84] 1 ⟺ thiết bị nguy cơ cao ⇒ cổng ảnh bằng chứng NĐ98 ÁP DỤNG. int 0|1 (KHÔNG boolean). */
  evidence_photo_required?: number
  /** [AC-CR-84] idx (1-based) các mục checklist còn THIẾU ảnh — ĐÚNG tập server từ chối (INV-CMEVID-1). */
  evidence_photo_missing_idxs?: number[]
  /** [AC-CR-84] Mẫu số: số mục PHẢI có ảnh (0 khi cổng không áp dụng). */
  evidence_photo_total_required?: number
```

⚠️ **Vắng khoá (worker cũ) ⇒ KHÔNG được suy "không có cổng"** — đó chính là hình thái bug CR-51. Quy tắc
render: 3 khoá **cùng vắng** ⇒ **ẩn toàn bộ khối bằng chứng** (không khẳng định gì), **KHÔNG** hiện
"Đã đủ ảnh". Nút hoàn thành vẫn theo `available_actions` (server đã hạ `enabled` nếu thiếu).

#### 2. Hiển thị — 3 chỗ, tất cả đều là **tấm gương** của server

| # | Vị trí | Nội dung (tiếng Việt đầy đủ) |
|---|---|---|
| **U1** | Dải trên bảng checklist (chỉ khi `evidence_photo_required === 1`) | Đủ ảnh: *"Bằng chứng NĐ98: đã có ảnh 6/6 mục"* (nền xanh). Thiếu: *"Bằng chứng NĐ98: còn 2/6 mục chưa có ảnh — cần đính đủ trước khi hoàn thành sửa chữa"* (nền hổ phách) |
| **U2** | Từng dòng checklist thuộc `evidence_photo_missing_idxs` | Chip *"Chưa có ảnh"* + nút **"Đính ảnh"** gọi `attachRepairChecklistPhoto(name, row.idx, file)` — dùng `FileUploadField` (GATE-9: **ô upload**, KHÔNG ô gõ đường dẫn) |
| **U3** | Tooltip nút "Hoàn thành sửa chữa" khi `enabled === false` | Hiển thị **`reason` từ server** nguyên văn — **KHÔNG** tự chế câu; nút disabled do `available_actions`, không do FE tự tính |

**Nguồn số liệu duy nhất:** `N = total_required − missing_idxs.length`. **KHÔNG** đếm lại từ
`repair_checklist[].photo` phía client (sinh bản diễn giải thứ hai — đúng class-of-bug đang đóng).

#### 3. Xử lý lỗi khi bấm "Hoàn thành sửa chữa"

Envelope `IMM09-EVIDENCE-PHOTO-REQUIRED` (HTTP-**200**, `success:false`) ⇒ interceptor hiện có đã dựng
`ApiError`; FE cần thêm: (a) toast dùng `message` từ registry (đã regen sang `i18n/messages.ts`);
(b) neo `fields.repair_checklist` **dưới bảng checklist**; (c) **refetch** phiếu để `missing_idxs` cập
nhật (người dùng có thể vừa đính ảnh ở tab khác); (d) **KHÔNG** logout, **KHÔNG** coi là lỗi hệ thống.

#### 4. Test FE bắt buộc (CÙNG VÒNG — RENDER thật, không chỉ type-check)

| TC | Fixture | Kỳ vọng |
|---|---|---|
| `FE-CM-EVID-01` | `required:1, total:6, missing:[2,5]` | DOM chứa **"còn 2/6 mục chưa có ảnh"**; đúng **2** chip "Chưa có ảnh" ở dòng idx 2 và 5 |
| `FE-CM-EVID-02` | `required:1, total:6, missing:[]` | DOM chứa **"đã có ảnh 6/6 mục"**; **0** chip "Chưa có ảnh" |
| `FE-CM-EVID-03` | `required:0` (thiết bị Low/`""`) | **KHÔNG** render khối bằng chứng (0 dải, 0 chip) |
| `FE-CM-EVID-04` | 3 khoá **vắng** (worker cũ) | **KHÔNG** render khối; **KHÔNG** crash; **KHÔNG** hiện "Đã đủ ảnh" |
| `FE-CM-EVID-05` | `available_actions[close_work_order] = {enabled:false, reason:"Thiết bị nguy cơ cao — …"}` | Nút "Hoàn thành sửa chữa" **disabled** + tooltip == `reason` **nguyên văn** (chống chế câu) |
| `FE-CM-EVID-06` | mock lỗi `IMM09-EVIDENCE-PHOTO-REQUIRED` khi bấm hoàn thành | Thông điệp VI hiện **dưới bảng checklist**; **0** chuỗi tiếng Anh/mã lỗi thô trong DOM; store gọi refetch |
| `FE-CM-EVID-07` | i18n sweep khối mới | DOM **0** ký tự của `High`/`Critical`/`Pending Inspection` (INV-CMEVID-8 · LL-FE-53) |

**DoD FE:** `vue-tsc --noEmit` 0 lỗi · `npm run test` xanh · ❌ **KHÔNG** `npm run build`
(ghi thẳng `assetcore/public/frontend` + `emptyOutDir` = deploy live — LL-DEPLOY-09).

---

## §VII i18n — Từ Ngữ Chuẩn Hóa Tiếng Việt

### Bảng thuật ngữ UI

| Tiếng Anh (code) | Tiếng Việt hiển thị |
|---|---|
| Work Order | Phiếu Sửa Chữa |
| Asset | Thiết bị |
| Repair Type | Loại sửa chữa |
| Priority | Ưu tiên |
| Assigned To | Kỹ thuật viên thực hiện |
| Diagnosis Notes | Nội dung chẩn đoán |
| Root Cause Category | Phân loại nguyên nhân |
| Spare Parts | Vật tư / Linh kiện |
| Stock Entry Ref | Phiếu xuất kho |
| Checklist | Danh sách kiểm tra |
| Repair Summary | Tóm tắt kết quả sửa chữa |
| Dept Head Name | Trưởng khoa phòng xác nhận |
| MTTR | MTTR (Thời gian sửa chữa trung bình) |
| SLA Breached | Vi phạm SLA |
| SLA Paused (Pending Parts) | Chờ phụ tùng — SLA tạm dừng (BR-09-10) |
| Parts Hold Hours | Thời gian chờ phụ tùng (giờ) |
| Cannot Repair | Không thể sửa chữa |
| Firmware Change Request | Yêu cầu cập nhật firmware |
| Repeat Failure | Tái hỏng hóc |
| First-Time Fix Rate | Tỷ lệ sửa thành công lần đầu |

### Status label map

| status | Nhãn tiếng Việt |
|---|---|
| Open | Mới mở |
| Assigned | Đã phân công |
| Diagnosing | Đang chẩn đoán |
| Pending Parts | Chờ vật tư |
| In Repair | Đang sửa chữa |
| Pending Inspection | Chờ nghiệm thu |
| Completed | Hoàn thành |
| Cannot Repair | Không thể sửa |
| Cancelled | Đã hủy |

### Reconcile với mockup `docs/fe/09-repair/` (BE = source of truth)

> Mockup HTML `docs/fe/09-repair/` dùng nhãn marketing (**Reported, Acknowledged,
> Diagnosed, Closed**) KHÔNG khớp `RepairStatus` enum thật trong `services/imm09.py`.
> **BE thắng.** FE map theo BE enum, KHÔNG copy nhãn mockup làm `value`.

| Mockup label | RepairStatus thật (BE) | Nhãn VI render |
|---|---|---|
| "Reported" / "Mở · Chờ phân công" | `Open` | Mới mở |
| "Acknowledged" / "Đã phân công" | `Assigned` | Đã phân công |
| "Diagnosed" / "Đã chẩn đoán" | `Diagnosing` | Đang chẩn đoán |
| "Waiting Parts" / "Chờ phụ tùng" | `Pending Parts` | Chờ vật tư |
| "In Progress" / "Đang xử lý" | `In Repair` | Đang sửa chữa |
| "Pending Inspection" / "Chờ nghiệm thu" | `Pending Inspection` | Chờ nghiệm thu |
| "Closed - Completed" / "Hoàn tất" | `Completed` | Hoàn thành |
| "Closed - Cannot Repair" | `Cannot Repair` | Không thể sửa |

**Workflow button → state matrix (CM Detail)** — đồng bộ với `ACTION_MAP` §VI:
nút chỉ hiện khi state khớp. Action terminal (`Completed`/`Cannot Repair`/`Cancelled`)
không có nút. Chi tiết transitions: `assignTechnician → submitDiagnosis →
[requestSpareParts] → startRepair → closeWorkOrder → confirmInspection`.

### Cascade Fields

| Khi chọn | Tự điền |
|---|---|
| `asset_ref` | `serial_no`, `risk_class`, `asset_category`, `location` |
| `incident_report` | Điền sẵn `failure_description` từ IR |
| `risk_class` × `priority` | Hiển thị SLA target dự kiến |
| `needs_parts = 1` | Chuyển hướng sang `/imm-09/:name/parts` sau khi lưu chẩn đoán |

---

### FilterKeyError — banner lỗi bộ lọc **KHÔNG thay thế bảng** (AC-CR-79, 2026-07-27) 🔴 SPEC

> Hợp đồng BE: [`05_API_Specification.md §14`](./05_API_Specification.md) · khuôn FE canonical:
> [`../imm-08/06 §7e`](../imm-08/06_Frontend_Design.md). Ở đây chỉ ghi phần KHÁC của IMM-09.

**Khác IMM-08:** `CMWorkOrderListView.vue::buildFilters()` (`:104-115`) gửi **6 khoá đều HỢP LỆ**
(`status`, `priority`, `asset_ref`, `sla_breached`, `is_repeat_failure`, `open` — probe đối chứng `OK`,
`05 §14.1`) ⇒ **KHÔNG sửa `buildFilters()`**. Chỉ còn 1 việc:

| # | Chỗ | Sửa |
|---|---|---|
| **F1** | `views/cm/CMWorkOrderListView.vue:219` | `v-else-if="store.error"` đang **thay thế** khối bảng ⇒ đổi sang **banner cộng-thêm** khi `store.workOrders.length > 0`; khối lỗi chiếm-chỗ chỉ khi chưa có dữ liệu. Cấu trúc y hệt `../imm-08/06 §7e.3`. |

**Bảo tồn (KHÔNG được "sửa"):** `stores/imm09.ts:65-67` — `catch` chỉ `_captureError`, **không** xoá
`workOrders`. Message hiển thị lấy **nguyên văn từ BE** (`store.error`). **KHÔNG logout** (400 ≠ 401).
**0 lỗi console**.

**Test RENDER bắt buộc** — `frontend/src/views/cm/cmFilterKeyError.test.ts`:

| TC | Kịch bản | Assert |
|---|---|---|
| FE-CMFK-1 | `workOrders` = 3 dòng → `fetchWorkOrders` reject `ApiError(msg,'INVALID_PARAMS',400)` | 3 dòng **vẫn render** + banner chứa `msg` |
| FE-CMFK-2 | như trên | không logout/redirect · `console.error` spy = 0 |
| FE-CMFK-3 | `workOrders` rỗng + lỗi | khối lỗi hiện + nút "Thử lại", không crash |
| FE-CMFK-4 | `buildFilters()` với đủ 6 điều khiển | tập khoá trả ra ⊆ `_ALLOWED_FILTER_KEYS` của IMM-09 (chống hồi quy "FE bịa khoá" như F2 bên IMM-08) |

---

## §VIII Empty / Error / Loading States

| Trạng thái | Component | Bản sao UI |
|---|---|---|
| Danh sách rỗng | CMList | "Không có phiếu sửa chữa nào. Nhấn '+ Tạo WO' để tạo mới." |
| Lỗi load WO | CMDetail | "Không thể tải phiếu sửa chữa. Vui lòng thử lại." + nút Thử lại |
| Đang tải | Tất cả | Skeleton loading card (Tailwind `animate-pulse`) |
| Thiết bị không tìm thấy | CMCreate asset field | "Thiết bị không tồn tại trong hệ thống" |
| WO đã có cho thiết bị | CMCreate submit | Toast "Thiết bị đang có phiếu sửa chữa mở: [link WO]" |
| Checklist chưa 100% Pass | CMChecklist | Button "Hoàn thành" disabled, tooltip "Còn X mục chưa Pass" |
| SLA vi phạm | CMDetail, CMList | Badge đỏ `SLA vi phạm` theo `wo.is_sla_breached ?? wo.sla_breached` (live-truth, BR-09-07 LIVE) — mobile `CMWorkOrderListView.vue:261` + desktop `:301`. KHÔNG mangle nhãn VI, KHÔNG leak raw status/EN. `RepairSlaIndicator` màu đỏ khi live ?? cờ. |

---

## §IX Accessibility

- Tất cả interactive element phải có `aria-label` hoặc `aria-labelledby` (tiếng Việt)
- Status badge: dùng `role="status"` + `aria-live="polite"` cho realtime update (DurationTimer, SLA)
- Keyboard navigation: Tab order theo thứ tự tự nhiên trong form
- Focus management: Sau khi submit chẩn đoán → focus vào `RepairActionBar` của bước tiếp theo
- Color contrast: Badge text/background phải đạt WCAG AA (4.5:1)

---

## §X Responsive Matrix

| Breakpoint | CMList | CMDetail | CMCreate |
|---|---|---|---|
| `sm` (< 640px) | 1 cột, ẩn SLA % | Stack dọc, ẩn timeline | Full width inputs |
| `md` (640–1024px) | 2 cột + filter | 2 cột 60/40 | 2 cột grid |
| `lg` (> 1024px) | Bảng đầy đủ | 2 cột + sidebar action | 2 cột + preview |

---

*End of IMM-09 Frontend Design v1.0 — Corrective Maintenance.*
