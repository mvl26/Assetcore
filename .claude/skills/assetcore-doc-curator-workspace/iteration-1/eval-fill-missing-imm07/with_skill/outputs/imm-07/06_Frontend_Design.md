# 06 — Thiết kế Frontend (Frontend Design / UI-UX Guide)

| Mục | Giá trị |
|---|---|
| Module | IMM-07 — Theo dõi hiệu suất |
| Phạm vi | Sitemap + Component + Cascade + Validation + Cockpit |
| Owner | FE Lead + UX |
| Liên kết | [02 Analysis](./02_Analysis_Design.md) · [05 API](./05_API_Specification.md) |

> Stack: Vue 3 + TypeScript + Pinia + Vue Router + TailwindCSS + TanStack Query (theo `.claude/skills/assetcore-fe-module/SKILL.md`).

---

## 1. Sitemap / Route map

| Route | Component | Auth | Mô tả |
|---|---|---|---|
| `/imm07/cockpit` | `CockpitView.vue` | Trưởng phòng, WS Lead | Dashboard hiệu suất tổng |
| `/imm07/snapshots` | `SnapshotListView.vue` | Trưởng phòng, WS Lead, KTV | Bảng snapshot có filter |
| `/imm07/snapshots/:asset/:period` | `SnapshotDetailView.vue` | Như trên | Detail + drill-down |
| `/imm07/signals` | `SignalListView.vue` | Trưởng phòng, WS Lead | Bảng replacement signal |
| `/imm07/signals/:name` | `SignalDetailView.vue` | Trưởng phòng | Detail + transition |
| `/imm07/config/kpi` | `KPIDefinitionView.vue` | CNTT Admin | CRUD KPI definition |
| `/imm07/config/threshold` | `ThresholdView.vue` | WS Lead, Trưởng phòng | Threshold workflow |

## 2. Sidebar nav module

```
Theo dõi hiệu suất (IMM-07)
├── Cockpit
├── Snapshot KPI
├── Tín hiệu thay thế
└── Cấu hình
    ├── KPI definition
    └── Ngưỡng thay thế
```

Hiển thị badge số signal Open ở mục "Tín hiệu thay thế".

## 3. Thiết kế giao diện — 2 cấp

### 3.a. UI Mockup (pre-build)

*(UX upload mockup vào `docs/imm-07/mockup/` — `*(BA bổ sung trong sprint kế tiếp)*`.)*

### 3.b. UI Screenshot (post-build)

*(Sau khi build — `*(Sprint Wave 3)*`.)*

## 3.c. Trang chi tiết theo archetype

### 3.1. Dashboard Cockpit (`/imm07/cockpit`)

Archetype: **Cockpit / KPI Dashboard**.

Layout:
- Top: 6 KPI tile (availability, utilization, MTBF, MTTR, downtime, # signal Open) — số lớn + delta tuần.
- Middle: 2 chart — Trend availability 30 ngày · Top 10 asset downtime.
- Bottom: Bảng signal Open mới nhất (≤ 10 dòng).

Data source: `cockpit_summary` (cache 5 phút), `list_signals?state=Open&page_size=10`.

### 3.2. List view (`/imm07/snapshots`, `/imm07/signals`)

Archetype: **List + Filter + Pagination**.

Filter: Department (cascade từ Site), Asset class, Period range, Quality (snapshot), Severity (signal).

### 3.3. Detail view (`/imm07/snapshots/:asset/:period`)

Archetype: **Detail with drill-down**.

Tabs: KPI values · Source records · Audit chain.

Nút "Re-compute" (chỉ WS Lead/Admin).

## 4. Component custom của module

| Component | Mô tả |
|---|---|
| `KPITile.vue` | Tile số lớn + delta + sparkline |
| `DrillDownDrawer.vue` | Drawer hiện list source record |
| `SignalTransitionButton.vue` | Action button theo state |
| `HashChainBadge.vue` | Badge xanh/đỏ trạng thái chain verify |
| `DataQualityBadge.vue` | Badge complete/incomplete |

## 5. Pinia store

```ts
// stores/imm07.ts
export const useImm07Store = defineStore('imm07', {
  state: () => ({
    cockpit: null as CockpitSummary | null,
    snapshots: [] as PerformanceSnapshot[],
    signals: [] as ReplacementSignal[],
  }),
  actions: {
    async fetchCockpit(scope: string) { /* useApi().run('imm07.cockpit_summary', { scope }) */ },
    async transitionSignal(name: string, action: string, note: string) { /* ... */ },
  },
});
```

## 6. Vue Query keys

| Key | Endpoint |
|---|---|
| `['imm07', 'cockpit', scope]` | `cockpit_summary` |
| `['imm07', 'snapshots', filters]` | `list_snapshots` |
| `['imm07', 'snapshot', asset, period]` | `get_snapshot` |
| `['imm07', 'signals', filters]` | `list_signals` |
| `['imm07', 'drill', asset, period, kpi]` | `drill_down` |

## 6b. API call pattern — useApi().run()

```ts
const { data, error, isLoading } = useQuery({
  queryKey: ['imm07', 'cockpit', scope],
  queryFn: () => useApi().run('assetcore.api.imm07.cockpit_summary', { scope }),
});
```

## 6c. TypeScript types — folder structure

```
frontend/src/types/imm07.ts
frontend/src/api/imm07.ts
frontend/src/stores/imm07.ts
frontend/src/views/imm07/
  CockpitView.vue
  SnapshotListView.vue
  SnapshotDetailView.vue
  SignalListView.vue
  SignalDetailView.vue
  KPIDefinitionView.vue
  ThresholdView.vue
```

## 7. Quy tắc ngôn ngữ FE

### 7.a. Nguyên tắc cứng

- Tiếng Việt là chính. Code term tiếng Anh (KPI, MTBF, MTTR) giữ nguyên.
- Không dùng tiếng Anh cho action button — vd "Đánh dấu False Positive" chứ không phải "Mark FP".

### 7.b. Pattern hiển thị thực thể

- Asset: hiển thị `<asset_name> — <model>` (vd `AC-ASSET-0001 — Siemens Magnetom`).
- Snapshot: `<KPI code>: <value><unit> (<period>)`.
- Signal: `<asset> · <severity> · <state>`.

### 7.c. Bảng từ ngữ chuẩn hóa

| EN | VI |
|---|---|
| Availability | Mức sẵn sàng |
| Utilization | Mức sử dụng |
| Downtime | Thời gian dừng |
| Replacement signal | Tín hiệu thay thế |
| Drill-down | Truy nguyên |
| Hash chain | Chuỗi xác thực |
| Snapshot | Snapshot (giữ — phổ biến) |

## 7d. Linked / Cascade fields

### 7d.a. Khi nào cần cascade

- Filter cockpit: Site → Department → Asset Class.
- KPI definition form: Category → applies_to_asset_class (reset khi đổi Category).

### 7d.b. Hành vi chuẩn

Khi user đổi field cha:
1. Reset field con về null.
2. Disable field con khi cha rỗng.
3. Re-fetch options con.
4. Show loading skeleton.

### 7d.c. Pattern code

```ts
watch(() => filters.department, () => {
  filters.asset_class = null;  // reset
});
```

## 7e. Input tight — chống nhập sai

### 7e.a. Ưu tiên picker thay free-text

- Asset: AssetPicker component.
- Period: DatePicker (range).
- Severity: SegmentedControl (low/medium/high).

### 7e.b. Validation realtime

- KPI formula expr: validate syntax client-side trước khi submit.
- Threshold value: numeric, > 0.

### 7e.c. Mask + format input

- Date: DD/MM/YYYY display, ISO submit.
- Float: 2 decimal display.

### 7e.d. Confirm modal cho hành động không undo

- "Mark False Positive" → confirm.
- "Re-compute" → confirm + ghi lý do bắt buộc.

## 8. Empty / Error / Loading copy

- Empty cockpit: "Chưa có dữ liệu KPI cho khoảng thời gian này. Đợi cron đêm hoặc liên hệ CNTT."
- Error 403: "Bạn không có quyền xem dữ liệu khoa khác."
- Error chain broken: "Phát hiện lỗi xác thực dữ liệu. Đã thông báo Tổ HC-QLCL."
- Loading: skeleton card 6 KPI tile.

## 9. Accessibility checklist module

- WCAG 2.1 AA contrast (≥ 4.5:1).
- Keyboard nav cho mọi action.
- Focus visible.
- ARIA label cho KPI tile + chart.
- Screen reader: KPI value đọc được kèm đơn vị.

## 10. Print spec (nếu có)

Báo cáo BYT — print A4 portrait, 6 KPI tile + 1 chart trend + danh sách signal Open. Header: site name + period. Footer: hash chain status.
