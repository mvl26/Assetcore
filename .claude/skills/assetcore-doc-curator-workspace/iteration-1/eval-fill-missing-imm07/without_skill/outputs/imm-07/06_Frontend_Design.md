# 06 — Frontend Design

| Mục | Giá trị |
|---|---|
| Module | IMM-07 — Theo dõi hiệu suất |
| Phạm vi | Per-module |
| Owner | FE Lead |
| Liên kết | 02 Analysis · 05 API |

> Stack: Vue 3 + TypeScript + Pinia + Vue Router + TailwindCSS + TanStack Vue Query.

---

## 1. Sitemap & Routes

| Route | Component | Quyền | Mục đích |
|---|---|---|---|
| `/imm-07` | `views/imm07/PerformanceCockpit.vue` | IMM07 User | Cockpit tổng quan |
| `/imm-07/asset/:name` | `views/imm07/AssetDrillDown.vue` | IMM07 User | Drill-down 1 asset |
| `/imm-07/signals` | `views/imm07/ReplacementSignalList.vue` | IMM07 User | Danh sách signal |
| `/imm-07/signals/:name` | `views/imm07/ReplacementSignalDetail.vue` | IMM07 Manager | Chi tiết + ack/suppress |
| `/imm-07/threshold-config` | `views/imm07/ThresholdConfigForm.vue` | IMM07 Manager | Cấu hình ngưỡng |
| `/imm-07/audit` | `views/imm07/AuditChainVerify.vue` | Auditor | Verify chain |

Đăng ký router trong `frontend/src/router/index.ts` với `meta.requiresRole`.

---

## 2. Component map

```
views/imm07/
├── PerformanceCockpit.vue          # cockpit tổng — heatmap + KPI cards + signal panel
├── AssetDrillDown.vue              # timeline event + KPI history + WO list
├── ReplacementSignalList.vue       # bảng filter signal
├── ReplacementSignalDetail.vue     # chi tiết + nút ack/suppress
├── ThresholdConfigForm.vue         # CRUD threshold config
├── AuditChainVerify.vue            # verify chain + show broken_at
└── components/
    ├── KpiCard.vue                 # 1 KPI single value + trend mini-chart
    ├── KpiHeatmap.vue              # asset × ngày, color theo availability
    ├── KpiTrendChart.vue           # line chart 30d
    ├── SignalBadge.vue             # badge state (Open/Ack/Suppressed/Closed)
    ├── EventTimeline.vue           # vertical timeline event
    └── DataQualityChip.vue         # chip Ok/Stale/Empty/Anomaly
```

---

## 3. Pinia store — `frontend/src/stores/imm07.ts`

```ts
export const useImm07Store = defineStore('imm07', () => {
  // UI state (KHÔNG phải server data — TanStack Query lo)
  const filters = ref<KpiFilters>({ site: null, department: null, model: null, dateRange: '7d' })
  const selectedAsset = ref<string | null>(null)

  function resetFilters() { /* ... */ }

  return { filters, selectedAsset, resetFilters }
})
```

> **Quy tắc**: server data dùng TanStack Vue Query (`useQuery`/`useMutation`); chỉ UI state mới vào Pinia.

---

## 4. API client — `frontend/src/api/imm07.ts`

```ts
import { useApi } from '@/composables/useApi'
import type { KpiSnapshot, ReplacementSignal, KpiThresholdConfig, ListResult } from '@/types/imm07'

export const imm07Api = {
  listKpiSnapshots: (filters: object, page = 1, page_size = 50) =>
    useApi().run<ListResult<KpiSnapshot>>('assetcore.api.imm07.list_kpi_snapshots', {
      filters: JSON.stringify(filters), page, page_size
    }),

  getKpiSnapshot: (name: string) =>
    useApi().run<KpiSnapshot>('assetcore.api.imm07.get_kpi_snapshot', { name }),

  listReplacementSignals: (filters: object, page = 1, page_size = 50) =>
    useApi().run<ListResult<ReplacementSignal>>('assetcore.api.imm07.list_replacement_signals', {
      filters: JSON.stringify(filters), page, page_size
    }),

  acknowledgeSignal: (name: string, note = '') =>
    useApi().run<ReplacementSignal>('assetcore.api.imm07.acknowledge_signal', { name, note }, 'POST'),

  suppressSignal: (name: string, reason: string) =>
    useApi().run<ReplacementSignal>('assetcore.api.imm07.suppress_signal', { name, reason }, 'POST'),

  verifyChain: (asset: string) =>
    useApi().run<{ valid: boolean; broken_at: string | null }>('assetcore.api.imm07.verify_chain', { asset }, 'POST'),

  getThresholdConfig: (asset_class: string) =>
    useApi().run<KpiThresholdConfig>('assetcore.api.imm07.get_threshold_config', { asset_class }),

  updateThresholdConfig: (payload: KpiThresholdConfig) =>
    useApi().run<KpiThresholdConfig>('assetcore.api.imm07.update_threshold_config', { payload: JSON.stringify(payload) }, 'POST'),
}
```

---

## 5. UX flows

### 5.1. Performance Cockpit

```
┌──────────────────────────────────────────────────────────────┐
│ Cockpit Hiệu suất — Site: [BV ABC ▼]   7d ▼   Refresh ↻    │
├──────────────────────────────────────────────────────────────┤
│ [ Sẵn sàng 95.3% ]  [ Khả dụng 62%  ]  [ MTBF 1840h ]       │
│ [ MTTR 18h       ]  [ PM compliance 91% ]  [ Signal mới: 3 ] │
├──────────────────────────────────────────────────────────────┤
│  Heatmap (asset × ngày)                                      │
│  ▢▢▢█▢▢▢  AST-001                                            │
│  ▢▢███▢▢  AST-002 ← click drill-down                         │
│  ...                                                          │
├──────────────────────────────────────────────────────────────┤
│ Replacement Signals (Open: 3)                                 │
│ │ AST-014 │ MTBF thấp + tuổi 8y │ 2026-05-09 │ [Acknowledge]│
└──────────────────────────────────────────────────────────────┘
```

### 5.2. Asset drill-down

- Header: tên asset + chip status + chip data_quality
- Tab 1: KPI 30d trend chart (Availability + MTBF)
- Tab 2: Event timeline (commissioned → PM → Repair → Calibration)
- Tab 3: Linked work orders (link cross-module IMM-08/09/11/12)
- Tab 4: Signal history

### 5.3. Cascade fields

| Field cha | Field con | Hành vi |
|---|---|---|
| `site` | `department` | Reset + reload danh sách khoa khi đổi site |
| `department` | `model` | Reset + reload model có trong khoa |
| `model` | `asset` | Reset + reload asset list |
| `asset_class` (threshold form) | – | Validate `mtbf_hours_min` không âm; disable submit khi invalid |

> Bám 01 §IV.3.b — cascade reset bắt buộc.

### 5.4. Tight validation

- Date range picker thay free-text
- Số nguyên cho `min_repair_count_12m`, `cooldown_days` — input có min/max
- Submit button disabled khi form invalid
- Confirm modal cho `Suppress signal` (action không undo dễ)

---

## 6. Quy tắc ngôn ngữ FE

- UI hiển thị **100% tiếng Việt**; mã code (vd `RPLS-2026-00001`) chỉ ở dòng phụ size nhỏ
- i18n key tại `frontend/src/locales/vi/imm07.json`:

```json
{
  "imm07.cockpit.title": "Cockpit Hiệu suất",
  "imm07.kpi.availability": "Tỷ lệ sẵn sàng",
  "imm07.kpi.utilization": "Tỷ lệ khả dụng",
  "imm07.kpi.mtbf": "MTBF (giờ)",
  "imm07.kpi.mttr": "MTTR (giờ)",
  "imm07.signal.state.Open": "Chờ xử lý",
  "imm07.signal.state.Acknowledged": "Đã ghi nhận",
  "imm07.signal.state.Suppressed": "Đã chặn (false-positive)",
  "imm07.signal.state.Closed": "Đã đóng",
  "imm07.action.acknowledge": "Ghi nhận",
  "imm07.action.suppress": "Đánh dấu false-positive",
  "imm07.action.verify_chain": "Kiểm tra hash chain",
  "imm07.data_quality.Ok": "Đầy đủ",
  "imm07.data_quality.Stale": "Trễ dữ liệu",
  "imm07.data_quality.Empty": "Không có dữ liệu",
  "imm07.data_quality.Anomaly": "Bất thường"
}
```

---

## 7. Error handling

- Mọi call dùng `useApi().run()` → tự bind toast + error mapping ErrorCode → message tiếng Việt
- `NOT_FOUND` → toast info "Không tìm thấy ..."
- `FORBIDDEN` → redirect `/403` + toast
- `BAD_STATE` (acknowledge khi không Open) → modal warning + reload
- `VALIDATION` → highlight field trong form (`fields` map)

---

## 8. Performance

- TanStack Query cache: KPI list TTL 60s, threshold config TTL 10 phút
- Heatmap: virtual scroll khi > 100 row asset
- Chart lib: `chart.js` lazy import (`defineAsyncComponent`)
- FCP target ≤ 1.5s; cockpit data render ≤ 2s

---

## 9. Accessibility

- WCAG 2.1 AA: contrast ratio ≥ 4.5
- Keyboard nav cho mọi action button
- Focus visible (Tailwind `focus-visible:ring`)
- Heatmap có alt text cho từng cell (asset + ngày + KPI)

---

## DoD — File 06

- [x] Sitemap + 6 route
- [x] Component tree rõ
- [x] Store Pinia (UI state) + TanStack Query (server data)
- [x] API client mirror file 05
- [x] Cascade fields declare
- [x] Tight validation rule
- [x] i18n key + tiếng Việt 100% UI
- [x] Error handling map ErrorCode
- [x] Performance target
- [ ] Mockup chi tiết Figma `[FE Lead bổ sung]`
- [ ] Reviewed bởi FE Lead + UX Designer
