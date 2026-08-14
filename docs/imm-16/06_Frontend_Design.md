# 06 — Frontend Design — IMM-16 Compliance Monitoring & CAPA

| Mục | Giá trị |
|---|---|
| Module | IMM-16 — Compliance Monitoring & CAPA |
| Phiên bản | 0.5.0 |
| Ngày cập nhật | 2026-05-18 |
| Owner | FE Lead |
| Liên kết | [05 API](./05_API_Specification.md) · [04 Backend](./04_Backend_Design.md) |
| Stack | Vue 3 + TypeScript + Pinia + Vue Router + TailwindCSS + TanStack Query |

> ✅ Implemented — Wave 2. 9 view dưới `frontend/src/views/compliance/` đã LIVE (confirmed 2026-05-18). Bảng route ở §I đã sync với `frontend/src/router/index.ts` — path domain (`/compliance/*`, `/capas`, `/audit-trail`), không phải prefix `/imm16/*`.

---

# Phần I — Sitemap & Routes

Route catalog đã sync với `frontend/src/router/index.ts` (verified 2026-05-18):

| # | View | Route | meta.requiredRoles |
|---|---|---|---|
| 1 | `ComplianceHeatmapView.vue` | `/compliance/heatmap` | `ROLES_COMPLIANCE_VIEW` |
| 2 | `ComplianceRuleListView.vue` | `/compliance/rules` | `ROLES_COMPLIANCE_MANAGE` |
| 3 | `ComplianceRuleDetailView.vue` | `/compliance/rules/:id` | `ROLES_COMPLIANCE_MANAGE` |
| 4 | `FindingListView.vue` | `/compliance/findings` | `ROLES_COMPLIANCE_VIEW` |
| 5 | `FindingDetailView.vue` | `/compliance/findings/:id` | `ROLES_COMPLIANCE_VIEW` |
| 6 | `InternalAuditListView.vue` | `/compliance/audits` | `ROLES_COMPLIANCE_VIEW` |
| 7 | `InternalAuditDetailView.vue` | `/compliance/audits/:id` | `ROLES_COMPLIANCE_VIEW` |
| 8 | `ScorecardView.vue` | `/compliance/scorecard` | `ROLES_COMPLIANCE_VIEW` |
| 9 | `ManagementReviewListView.vue` | `/compliance/mr` | `ROLES_COMPLIANCE_MANAGE` |
| 10 | `ManagementReviewDetailView.vue` | `/compliance/mr/:id` | `ROLES_COMPLIANCE_MANAGE` |
| 11 | `CapaListView.vue` (incident folder) | `/capas` | `ROLES_COMPLIANCE_VIEW` |
| 12 | `CapaDetailView.vue` (incident folder) | `/capas/:id` | `ROLES_CAPA_CLOSE` |
| 13 | `AuditTrailListView.vue` | `/audit-trail` | `ROLES_AUDIT_READ` |

> Confirmed 2026-05-18: Views thực tế trong `frontend/src/views/compliance/`: `ComplianceHeatmapView.vue`, `ComplianceRuleDetailView.vue`, `ComplianceRuleListView.vue`, `FindingDetailView.vue`, `FindingListView.vue`, `InternalAuditDetailView.vue`, `InternalAuditListView.vue`, `ManagementReviewDetailView.vue`, `ManagementReviewListView.vue`, `ScorecardView.vue` (10 views). CAPA views tại `frontend/src/views/incident/CAPADetailView.vue` + `CAPAListView.vue` (không phải `audit` folder như spec cũ).

> Tất cả 11 route đặt `meta.moduleId: 'imm16'`. Sidebar mapping: regex `[/^\/capas/, 'imm16']`, `[/^\/audit-trail/, 'imm16']`, `[/^\/compliance/, 'imm16']` trong `router/index.ts`.
>
> Wave-2 design decision: chia thành 3 nhóm path — `/compliance/*` (Rule/Finding/Audit/Scorecard/MR), `/capas` (CAPA board + detail — share với IMM-12 trigger), `/audit-trail` (read-only hash chain). Compliance Dashboard tiles render inside heatmap/scorecard view, KHÔNG có route riêng `/compliance/dashboard`. Wireframe §II.1 dưới đây giữ làm spec tham chiếu cho UI redesign sprint kế.

**Modals (không có route riêng):**
- `WaiveFindingModal.vue` — trigger từ Finding Detail
- `EffectivenessCheckModal.vue` — trigger từ CAPA Detail

---

# Phần II — Component Catalog

## II.1. ComplianceDashboard.vue

**Route:** `/compliance/heatmap` (dashboard composed in `ComplianceHeatmapView.vue`; standalone `/compliance/dashboard` chưa wire — xem _REPORT.md §TODO)

**ASCII Wireframe:**

```
┌──────────────────────────────────────────────────────────────────────────┐
│ IMM-16 Compliance & CAPA Dashboard                       [Tháng 4/2026 ▼]│
│ ──────────────────────────────────────────────────────────────────────── │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │
│ │ Compliance  │ │ Findings    │ │ CAPA        │ │ Mgmt Review │        │
│ │ Score       │ │ Open        │ │ Open/Overdue│ │ Quý này     │        │
│ │  87.5%      │ │   24        │ │  18 / 5     │ │ Pending     │        │
│ │  ▲ +2.3 pp  │ │ 3 Critical  │ │ 1 Crit Ovr  │ │ Hạn 30/06  │        │
│ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘        │
│                                                                          │
│ ┌─── Trend 12 tháng (line) ─────────┐ ┌──── Top Module Yếu ──────────┐  │
│ │ 90 ┤    ╭──╮                      │ │  IMM-11  ████████  72%       │  │
│ │    │   ╱    ╰──╮                  │ │  IMM-15  █████████ 78%       │  │
│ │ 80 ┤  ╱         ╰──╮    ╭───      │ │  IMM-08  ███████   82%       │  │
│ │    │ ╱             ╰───╯          │ │  IMM-09  ████████  85%       │  │
│ │ 70 ┴────────────────────────────  │ │                              │  │
│ └───────────────────────────────────┘ └──────────────────────────────┘  │
│                                                                          │
│ ┌─── CAPA Aging ───────────┐ ┌─── Findings gần đây ─────────────────┐   │
│ │  0-7d:   ██  6           │ │ FND-2026-0042  IMM-08  ICU  High ⏱   │   │
│ │  8-30d:  ███ 8           │ │ FND-2026-0041  IMM-11  CT   Crit ⏱   │   │
│ │  31-60d: ██  3           │ │ FND-2026-0040  IMM-05  OR   Med  ⏱   │   │
│ │  >60d:   █   1           │ └──────────────────────────────────────┘   │
│ └──────────────────────────┘                                             │
│ [Xem Heatmap →]  [Xem CAPA Board →]  [Xem Audit list →]                  │
└──────────────────────────────────────────────────────────────────────────┘
```

**Components:** `KpiCard`, `TrendLineChart`, `ModuleRankingBar`, `CapaAgingChart`, `FindingRecentTable`

**KPI Cards:**

| KPI | API field | Click action |
|---|---|---|
| Compliance Score | `kpis.overall_compliance_pct` | Mở Scorecard tháng hiện tại |
| Findings Open | `kpis.findings_open` | Filter list status=Open/Under Review |
| CAPA Open/Overdue | `kpis.capa_open` / `capa_overdue` | Mở CAPA Kanban |
| Mgmt Review | `kpis.mr_quarterly_status` | Mở MR quý hiện tại |

## II.2. ComplianceHeatmap.vue

**Route:** `/compliance/heatmap` (`@/views/compliance/ComplianceHeatmapView.vue`)

**ASCII Wireframe:**

```
┌────────────────────────────────────────────────────────────────────┐
│ Compliance Heatmap — Tháng 4/2026             [Period ▼] [Export]  │
│ ────────────────────────────────────────────────────────────────── │
│              ICU    OR    ER    CT    Int.Med  Pediatric           │
│  IMM-04   │  92  │ 88  │ 85  │ 90  │  95    │  91  │              │
│  IMM-05   │  95  │ 92  │ 88  │ 90  │  97    │  94  │              │
│  IMM-06   │  88  │ 85  │ 80  │ 82  │  90    │  87  │              │
│  IMM-08   │  92  │ 78★ │ 85  │ 70★ │  88    │  82  │              │
│  IMM-09   │  85  │ 80  │ 78  │ 75★ │  90    │  88  │              │
│  IMM-11   │  78★ │ 72★ │ 80  │ 65★ │  85    │  80  │              │
│  IMM-12   │  88  │ 82  │ 85  │ 78★ │  92    │  88  │              │
│  IMM-15   │  90  │ 85  │ 82  │ 85  │  92    │  88  │              │
│                                                                    │
│  Legend: ≥90 xanh   80-89 vàng   70-79 cam   <70 đỏ   ★=Critical  │
│  Click cell → drill-down list_findings filtered                    │
└────────────────────────────────────────────────────────────────────┘
```

**Color scale:**

| Score | Màu | TailwindCSS class |
|---|---|---|
| ≥ 90 | Xanh | `bg-green-500` |
| 80-89 | Vàng | `bg-yellow-400` |
| 70-79 | Cam | `bg-orange-500` |
| < 70 | Đỏ | `bg-red-500` |

Hover cell → tooltip `{module, dept, score%, findings_count}`.
Click cell → navigate `/compliance/findings?filters={source_module, responsible_dept, period}`.

## II.3. CAPA Kanban Board (CapaKanbanView.vue)

**Route:** `/capas` (`@/views/capa/CapaListView.vue`; kanban variant chưa wire)

**ASCII Wireframe:**

```
┌──────────────────────────────────────────────────────────────────────────┐
│ CAPA Board                                  [+ Tạo CAPA mới]  [Filter]   │
│ ──────────────────────────────────────────────────────────────────────── │
│ ┌────────┐ ┌────────────┐ ┌───────────┐ ┌─────────────┐ ┌──────────┐   │
│ │  Open  │ │Investigating│ │Action Plan│ │Implementation│ │Verific. │   │
│ │  (3)   │ │   (5)      │ │   (4)     │ │    (8)       │ │  (2)    │   │
│ ├────────┤ ├────────────┤ ├───────────┤ ├─────────────┤ ├──────────┤   │
│ │CAPA-.. │ │ CAPA-..    │ │ CAPA-..   │ │ CAPA-..     │ │CAPA-..  │   │
│ │ Crit   │ │  High      │ │  Med      │ │  High       │ │ Crit    │   │
│ │ ICU    │ │ ICU dept   │ │ OR dept   │ │ Steps: 3/5  │ │Eff.due: │   │
│ │ Due:5d │ │ Due:3d ⏱   │ │ Due:12d   │ │ Owner: ...  │ │ 7d      │   │
│ └────────┘ └────────────┘ └───────────┘ └─────────────┘ └──────────┘   │
│                                                                          │
│ ─── Closed (12) ─── (collapse)    ─── Re-opened (1) ─── (collapse)      │
└──────────────────────────────────────────────────────────────────────────┘
```

Drag & drop: gọi `advance_capa_state` (server-side VR-05/06/07/12). Fail → toast lỗi + revert card.

## II.4. CAPA Detail (CapaDetailView.vue)

> **FE contract Vòng 13 (RC-CAPA-ESC) — ZERO required shape-change.** Escalation tiered là side-effect **server-side** của cron `check_capa_due` — KHÔNG có action FE, KHÔNG có button "escalate" trên UI. Field mới `escalation_level` (Int, read-only) tự lộ trong `get_capa` response (`api/imm16.ts` type `CapaDetail.escalation_level?: number`). **Hiển thị tuỳ chọn (không bắt buộc round này):** tab "Lịch sử" đã render IMM Audit Trail nên tier escalation hiện qua audit event `CAPA` ("CAPA … leo thang Level-N") — KHÔNG cần widget riêng. Nếu sau này muốn badge "Đã leo thang Level-N" ở header → bind `escalation_level` (1→"Level-1", 2→"Level-2", 0/null→ẩn) — KHÔNG bịa nhãn khi field rỗng. KHÔNG leak EN/raw "escalation_level".

**Route:** `/capas/:id`

Tab navigation: `[Tóm tắt] [Phân tích] [Action Steps] [Verification] [Lịch sử]`

```
┌────────────────────────────────────────────────────────────────┐
│ CAPA: CAPA-2026-00007              [Re-open] [Save] [Advance ▼]│
│ State: Implementation    Risk: Critical                        │
│ ────────────────────────────────────────────────────────────── │
│ [Tóm tắt] [Phân tích] [Action Steps] [Verification] [Lịch sử] │
│                                                                │
│ ┌─ Tóm tắt ────────────────────────────────────────────────┐  │
│ │ Source: FND-2026-0042 → PM compliance ICU 78% < 90%       │  │
│ │ Asset: AC-ASSET-2026-0001   Dept: ICU                     │  │
│ │ Action Owner: nguyenvana   Due: 2026-05-20  Reopen: 0     │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                │
│ ┌─ Action Steps ───────────────────────────────────────────┐  │
│ │ # │ Mô tả               │ Owner      │ Plan   │ Status   │  │
│ │ 1 │ Tuyển thêm KTV       │ hr@hosp.vn │ 05-15  │ Done ✓  │  │
│ │ 2 │ Lên lịch PM lại      │ nguyenvana │ 05-25  │ InProg  │  │
│ │ 3 │ Cross-train KTV      │ nguyenvana │ 06-10  │ Pending │  │
│ │                                        [+ Thêm step]     │  │
│ └────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

## II.5. WaiveFindingModal.vue

```
┌──────────────────────────────────────────────────┐
│ Miễn áp dụng Finding (Waive)                [✕]  │
│ ──────────────────────────────────────────────── │
│ Finding:     FND-2026-00042 (locked)             │
│ Rule:        R-IMM08-PM-COMP-90                  │
│ Severity:    High                                │
│                                                  │
│ Lý do miễn*: [textarea — tối thiểu 50 ký tự]    │
│                                                  │
│ Bằng chứng*: [Chọn file...]                      │
│                                                  │
│ Hết hiệu lực*: [2026-12-31]                      │
│   (sau ngày này, finding tự re-open)             │
│                                                  │
│ Lưu ý: Chỉ VP Block2 được waive (BR-16-06)       │
│   Hành động này ghi audit trail.                 │
│                                                  │
│             [Hủy]  [Xác nhận Waive]              │
└──────────────────────────────────────────────────┘
```

VR-04: reason ≥ 50 chars, evidence required, expiry > today.

## II.6. EffectivenessCheckModal.vue

```
┌──────────────────────────────────────────────────┐
│ Kiểm tra Hiệu quả (Effectiveness Check)      [✕] │
│ ──────────────────────────────────────────────── │
│ CAPA: CAPA-2026-00007 (locked)                   │
│ Verification period: 2026-06-01 → 2026-07-01     │
│                                                  │
│ Kết quả*:                                        │
│   ⦿ Effective    — Root cause đã loại bỏ         │
│   ○ Not Effective — Vấn đề tái phát              │
│                                                  │
│ Bằng chứng*: [Chọn file evidence...]             │
│                                                  │
│ Ghi chú:     [textarea]                          │
│                                                  │
│ Nếu Not Effective: CAPA Re-open (Investigating)  │
│   và reopen_count += 1 (BR-16-03)               │
│                                                  │
│          [Hủy]  [Xác nhận]                       │
└──────────────────────────────────────────────────┘
```

## II.7. Scorecard Detail (ScorecardDetailView.vue)

```
┌──────────────────────────────────────────────────────────────────────┐
│ Scorecard: SCR-2026-04-0001              Status: Draft              │
│ Period: April 2026   Scope: Hospital                                │
│ ──────────────────────────────────────────────────────────────────── │
│ Score: 83.33%  ▲ +2.3pp   (chỉ tính trên finding ĐÃ phân định)      │
│ Compliant: 90   Non-comp: 18   Pending: 12   CAPA open: 18          │
│ -- FE chỉ ĐỌC score_pct/compliant_count/non_compliant_count/        │
│    pending_count từ API; KHÔNG inline-compute (BR-16-11). Pending    │
│    hiển thị read-only, KHÔNG cộng vào mẫu số score. --               │
│                                                                      │
│ ┌─ By Module ─────────────────────────────────┐                      │
│ │ IMM-04  ████████████████ 95%               │                      │
│ │ IMM-11  ████████         72% ⚠              │                      │
│ └─────────────────────────────────────────────┘                      │
│                                                                      │
│ ┌─ By Department ─────────────────────────────┐                      │
│ │ ICU  ████████████████ 92%                  │                      │
│ │ CT   ████████         74% ⚠                │                      │
│ └─────────────────────────────────────────────┘                      │
│                                                                      │
│ Quý 1/2026 Management Review: Done (12/04)                          │
│ [Reviewer Sign-off] [Publish Scorecard] [Export PDF]                │
│                                                                      │
│ -- Sau publish: banner "Đã publish ngày {date}. Tạo Restate mới." --│
└──────────────────────────────────────────────────────────────────────┘
```

---

## II.8. Compliance Pre-flight Gate Banner (cross-module — consumed by IMM-08/09)

> 🆕 Vòng 16. Component này KHÔNG có view/route riêng — nó là **inline banner** nhúng vào form tạo Work Order của module gọi (Wave 1: `PMWorkOrderCreateView.vue` — IMM-08). IMM-16 sở hữu CONTRACT (data + i18n + parity), module gọi sở hữu placement.

**Mục đích:** Cảnh báo SỚM (pre-flight) — khi user chọn asset có Critical CAPA mở, hiện banner NGAY (không đợi submit mới `frappe.throw`). Đọc CÙNG SoT với `gate_wo_submit` (BR-16-09).

**Data source:** client `imm16.ts::checkAssetComplianceStatus(asset)` → canonical endpoint `assetcore.api.imm16.check_asset_compliance_status` (GET, line 512-513). Trả `ComplianceGateResult` (`api/imm16.ts:213`):

```ts
interface ComplianceGateResult {
  blocked: boolean
  asset?: string
  reasons: GateReason[]          // GateReason = { type:'CAPA_CRITICAL_OPEN', ref, status, workflow_state, message }
  active_findings_count: number
  active_capas_count: number
  blocking_findings: string[]
}
```

**ASCII Wireframe (vị trí: NGAY SAU panel assetMeta, TRƯỚC khi soạn xong form):**

```
┌─ assetMeta panel (Tên / Model / Vị trí / Trạng thái) ────────────────┐
└──────────────────────────────────────────────────────────────────────┘
  ▼ (chỉ render khi result.blocked === true)
┌─ ⚠ Banner cảnh báo  role="alert" aria-live="assertive" severity=warning ┐
│ Thiết bị có CAPA Critical đang mở — không thể tạo lệnh cho đến khi đóng. │
│ • CAPA-2026-00007 — Quá hạn        (status thật, dịch qua SSoT)          │
│ • CAPA-2026-00012 — Đang xử lý                                          │
└────────────────────────────────────────────────────────────────────────┘
```

**Behavior contract:**

| Điều kiện | UI |
|---|---|
| `result.blocked === true` | Banner HIỆN (severity=warning, `role="alert"`, `aria-live="assertive"`); liệt kê `reasons[]` verbatim: `{ref} — {translateStatus(status)}`; nút "Tạo lệnh" disable HOẶC giữ reactive-throw nhưng banner đã cảnh báo |
| `result.blocked === false` | Banner ẩn, nút bình thường |
| `asset_ref` rỗng | Banner ẩn (không fetch) |
| Fetch lỗi / 403 | **Fail-safe ẩn** banner — KHÔNG blank trang (try-catch / allSettled); không chặn form |

**Wiring rules (BẮT BUỘC):**
- Fetch CHỈ khi `asset_ref` đổi → reuse `watch(() => form.value.asset_ref, loadAssetMeta)` hiện có; gọi `checkAssetComplianceStatus` bên trong `loadAssetMeta` (cùng nhịp load assetMeta), gói try-catch/allSettled.
- **KHÔNG inline-compute membership ở FE** — chỉ render `result.blocked` + `result.reasons[]` từ BE (parity với `gate_wo_submit`).
- **i18n SSoT:** dịch `reason.status` qua `formatters.translateStatus` (DUY NHẤT 1 map). 0 English leak: `'Overdue'→'Quá hạn'` (formatters.ts:78), `'In Progress'→…`, etc. Nhãn `'Critical'/'Khẩn cấp'` lấy từ SSoT (formatters.ts:170), KHÔNG hardcode literal Anh.
- State: thêm `gateResult = ref<ComplianceGateResult | null>(null)`; computed `gateBlocked = computed(() => gateResult.value?.blocked === true)`. Có thể AND vào `canSubmit` để disable nút khi blocked.

**Parity acceptance:** `gateResult.value.blocked` (FE) === `blocked` do service `check_asset_compliance_status` trả === điều kiện `gate_wo_submit` dùng để `frappe.throw` lúc submit. Banner = cảnh báo sớm cho CÙNG quyết định block, không phải nguồn quyết định độc lập.

---

# Phần III — Pinia Store

> ✅ IMPLEMENTED — Wave 2. Store thực tế: `frontend/src/stores/imm16.ts` (không suffix `Store`).

```typescript
// frontend/src/stores/imm16.ts
import { defineStore } from 'pinia'
import { useApi } from '@/composables/useApi'
import type {
  ComplianceFinding,
  ComplianceScorecard,
  CapaRecord,
  DashboardStats,
  ComplianceHeatmap,
} from '@/types/imm16'

export const useImm16Store = defineStore('imm16', {
  state: () => ({
    // Dashboard
    dashboardStats: null as DashboardStats | null,
    dashboardLoading: false,

    // Findings
    findings: [] as ComplianceFinding[],
    findingsPagination: { page: 1, page_size: 20, total: 0, total_pages: 0 },
    findingsLoading: false,
    activeFilters: {} as Record<string, string>,

    // CAPA
    capaByState: {} as Record<string, CapaRecord[]>,
    capaLoading: false,

    // Scorecard
    currentScorecard: null as ComplianceScorecard | null,
    scorecards: [] as ComplianceScorecard[],

    // Heatmap
    heatmap: null as ComplianceHeatmap | null,

    // Realtime
    realtimeSubscribed: false,
  }),

  actions: {
    async fetchDashboardStats() {
      const { run } = useApi()
      this.dashboardLoading = true
      try {
        const res = await run<DashboardStats>('assetcore.api.imm16.get_dashboard_stats')
        if (res.success) this.dashboardStats = res.data
      } finally {
        this.dashboardLoading = false
      }
    },

    async fetchFindings(filters = {}, page = 1) {
      const { run } = useApi()
      this.findingsLoading = true
      this.activeFilters = filters
      try {
        const res = await run<{ items: ComplianceFinding[]; pagination: any }>(
          'assetcore.api.imm16.list_findings',
          { filters: JSON.stringify(filters), page, page_size: 20 }
        )
        if (res.success) {
          this.findings = res.data.items
          this.findingsPagination = res.data.pagination
        }
      } finally {
        this.findingsLoading = false
      }
    },

    async confirmFinding(name: string, notes: string) {
      const { run } = useApi()
      const res = await run('assetcore.api.imm16.confirm_finding', { name, notes })
      if (res.success) {
        await this.fetchFindings(this.activeFilters)
      }
      return res
    },

    async waiveFinding(payload: {
      name: string
      waiver_reason: string
      waiver_evidence: string
      waiver_expiry: string
    }) {
      const { run } = useApi()
      return run('assetcore.api.imm16.waive_finding', payload)
    },

    async advanceCapaState(name: string, target_state: string, payload = {}) {
      const { run } = useApi()
      return run('assetcore.api.imm16.advance_capa_state', {
        name,
        target_state,
        payload: JSON.stringify(payload),
      })
    },

    async publishScorecard(name: string) {
      const { run } = useApi()
      return run('assetcore.api.imm16.publish_scorecard', { name })
    },

    async fetchHeatmap(year: number, month: number) {
      const { run } = useApi()
      const res = await run<ComplianceHeatmap>(
        'assetcore.api.imm16.get_compliance_heatmap',
        { period_year: year, period_month: month }
      )
      if (res.success) this.heatmap = res.data
      return res
    },

    subscribeRealtime() {
      if (this.realtimeSubscribed) return
      // Frappe realtime
      window.frappe?.realtime?.on('imm16:finding_created', () => {
        this.fetchFindings(this.activeFilters)
      })
      window.frappe?.realtime?.on('imm16:capa_state_changed', () => {
        this.fetchCapaBoard()
      })
      window.frappe?.realtime?.on('imm16:scorecard_published', () => {
        this.fetchDashboardStats()
      })
      this.realtimeSubscribed = true
    },

    async fetchCapaBoard() {
      // group CAPA by workflow_state for Kanban
      const { run } = useApi()
      const res = await run('assetcore.api.imm00.list_capas', {
        page_size: 200,
      })
      if (res.success) {
        const grouped: Record<string, CapaRecord[]> = {}
        for (const capa of res.data.data) {
          const state = capa.workflow_state || 'Open'
          if (!grouped[state]) grouped[state] = []
          grouped[state].push(capa)
        }
        this.capaByState = grouped
      }
    },
  },

  getters: {
    criticalOpenFindings: (state) =>
      state.findings.filter(f => f.severity === 'Critical' && f.status === 'Open'),
    overdueCapa: (state) =>
      Object.values(state.capaByState).flat().filter(
        c => new Date(c.due_date ?? '') < new Date() &&
             !['Closed'].includes(c.status)
      ),
  },
})
```

---

# Phần IV — i18n Table

| Key | Tiếng Việt | Tiếng Anh (fallback) |
|---|---|---|
| `imm16.dashboard.title` | Tuân thủ & CAPA Dashboard | Compliance & CAPA Dashboard |
| `imm16.finding.status.open` | Mở | Open |
| `imm16.finding.status.under_review` | Đang xem xét | Under Review |
| `imm16.finding.status.confirmed_nc` | Đã xác nhận NC | Confirmed NC |
| `imm16.finding.status.false_positive` | Sai | False Positive |
| `imm16.finding.status.waived` | Đã miễn | Waived |
| `imm16.finding.status.resolved` | Đã giải quyết | Resolved |
| `imm16.finding.status.closed` | Đóng | Closed |
| `imm16.capa.state.open` | Mở | Open |
| `imm16.capa.state.investigating` | Điều tra | Investigating |
| `imm16.capa.state.action_plan` | Kế hoạch hành động | Action Plan |
| `imm16.capa.state.implementation` | Thực thi | Implementation |
| `imm16.capa.state.verification` | Xác minh | Verification |
| `imm16.capa.state.closed` | Đóng | Closed |
| `imm16.capa.state.reopened` | Mở lại | Re-opened |
| `imm16.severity.low` | Thấp | Low |
| `imm16.severity.medium` | Trung bình | Medium |
| `imm16.severity.high` | Cao | High |
| `imm16.severity.critical` | Nghiêm trọng | Critical |
| `imm16.mr.status.done` | Đã hoàn tất | Done |
| `imm16.mr.status.pending` | Sẽ tổ chức | Pending |
| `imm16.mr.status.overdue` | Quá hạn | Overdue |
| `imm16.error.vr04` | Waiver thiếu lý do/evidence/expiry hợp lệ | Waiver missing reason/evidence/expiry |
| `imm16.error.vr07` | Không thể Close khi effectiveness chưa Effective | Cannot close without Effective result |
| `imm16.error.vr08` | Còn Major NC chưa mở CAPA | Major NC without CAPA link |
| `imm16.error.vr09` | Scorecard đã publish, không thể sửa | Scorecard is published and immutable |
| `imm16.error.vr10` | Quý trước chưa có Management Review | Previous quarter missing Management Review |
| `imm16.error.forbidden` | Bạn không có quyền thực hiện hành động này | You do not have permission for this action |

---

## II.9. FindingDetailView.vue — Server-driven CTA gating (GATE-8 / LL-FE-51)

> **Vấn đề gốc (dead-gate):** 5 CTA trước đây gate bằng so `finding.status ===` / `.includes([...])` client-side → desync khỏi SoT `FindingStatus` (vd `canConfirm = ['Open','Under Review']` loại Confirmed NC trong khi BE `ACTIVE` gồm Confirmed NC; `canWaive` cho cả Resolved). Chuyển sang hint server (`allowed_transitions` + `can_create_capa` từ `get_finding` — §III.B.1 backend). Đối xứng PmWorkOrderDetail (II·imm08), IncidentDetail (imm12), RepairDetail (imm09).

**Nguồn quyền + hint:**
```ts
const { can } = useCapabilities()
const at = computed(() => finding.value?.allowed_transitions ?? [])   // fallback an toàn
const canWrite = computed(() => can('compliance.write'))
```

**Mỗi CTA = `canWrite && (allowed_transitions.includes(<đích>) | can_create_capa)`** — KHÔNG còn `finding.status ===`:

| CTA | computed | Điều kiện |
|---|---|---|
| Bắt đầu xem xét *(round 14)* | `canStartReview` | `canWrite && at.includes('Under Review')` → click gọi `start_review` (store `actionStartReview`) |
| Xác nhận sự không phù hợp | `canConfirm` | `canWrite && at.includes('Confirmed NC')` |
| Đánh dấu sai | `canMarkFalse` | `canWrite && at.includes('False Positive')` *(tách khỏi `canConfirm` cũ — trước dùng chung gate)* |
| Miễn áp dụng | `canWaive` | `canWrite && at.includes('Waived')` |
| Tạo CAPA | `canCreateCapa` | `canWrite && (finding.can_create_capa === true)` |
| Liên kết CAPA | `canLinkCapa` | `canWrite && (finding.can_create_capa === true)` *(gỡ inline `status==='Confirmed NC' && !capa_ref` ở template)* |

**Đổi hành vi hiển thị (do SoT siết lại — có chủ đích):**
- **Open (round 14):** `at=['Under Review','Confirmed NC','False Positive','Waived']` → +CTA "Bắt đầu xem xét" (hiện). `canConfirm/canMarkFalse/canWaive` KHÔNG regress: 3 nút cũ vẫn hiện; nút mới chỉ THÊM. `FindingDetailView.ctaGating.test.ts` xanh không đổi (fixtures hardcode KHÔNG có `'Under Review'` ⇒ nút mới ẩn trong test cũ; NÊN thêm 1 case mới assert `canStartReview` hiện khi `at.includes('Under Review')`).
- Under Review: `at=['Confirmed NC','False Positive','Waived']` → "Bắt đầu xem xét" **ẩn** (đã trong review); 3 CTA phân định hiện.
- Confirmed NC: `at=['Waived']` → Xác nhận/Đánh dấu-sai **ẩn** (khớp `canConfirm` cũ); Miễn áp dụng **hiện** (khớp `canWaive` cũ); CAPA route qua `can_create_capa`.
- Resolved: `at=[]` → Miễn áp dụng **ẩn** (trước `canWaive` cho hiện — waive 1 finding đã Resolved là vô nghĩa; nay đóng).
- Terminal (False Positive/Waived/Closed): 0 CTA — như cũ.

**Ràng buộc:**
- Gỡ TOÀN BỘ `finding.status ===` / `['...'].includes(finding.status)` khỏi `<script>` + `<template>` (kể cả dòng inline nút Liên kết CAPA).
- Thiếu `compliance.write` → mọi CTA ẩn (không chỉ disable) — nhất quán permission-driven UI.
- `allowed_transitions`/`can_create_capa` vắng (worker cũ) → `?? []` / `?? false` → CTA ẩn, KHÔNG crash.
- **(round 14)** Wire: `api/imm16.ts` += `startReview(name, reviewer_note)` (POST `assetcore.api.imm16.start_review`); store `imm16.ts` += `actionStartReview`; sau transition refetch `get_finding` (Open→Under Review ẩn nút "Bắt đầu xem xét", hiện 3 CTA phân định). Nhãn nút "Bắt đầu xem xét" (tiếng Việt đầy đủ, LL-FE-53).
- KHÔNG leak EN/raw status; nhãn nút giữ tiếng Việt hiện có.

## II.10. InternalAuditDetailView.vue — Server-driven CTA gating (GATE-8 / LL-FE-51)

> **Vấn đề gốc (dead-gate):** 3 CTA vòng đời (Bắt đầu / Hoàn tất bảng kiểm→Báo cáo / Đóng) gate bằng so `audit.status ===` client-side → desync + không phản ánh quyền server. Chuyển sang hint server (`allowed_transitions` action-key + 2 cờ `can_operate`/`can_close` từ `get_audit` — §III.C.1 backend / ADR-IMM-16-02). Đối xứng FindingDetail (II.9), PmWorkOrderDetail (imm08), IncidentDetail (imm12), RepairDetail (imm09).

**Nguồn quyền + hint:**
```ts
const at = computed(() => audit.value?.allowed_transitions ?? [])   // fallback an toàn
const canOperate = computed(() => audit.value?.can_operate === true) // compliance.write (server-derived)
const canClose   = computed(() => audit.value?.can_close === true)   // compliance.submit (server-derived)
```

**Mỗi CTA = `<cờ> && at.includes('<action-key>')`** — KHÔNG còn `audit.status ===`:

| CTA | computed | Điều kiện | Endpoint |
|---|---|---|---|
| Bắt đầu | `canStart` | `canOperate && at.includes('start')` — **CHỈ ở Planned** | `startAudit` |
| Editor bảng kiểm + Hoàn tất bảng kiểm | `canCompleteChecklist` | `canOperate && at.includes('complete_checklist')` — **CHỈ ở In Progress** | `completeAuditChecklist` |
| Đóng | `canCloseCta` | `canClose && at.includes('close')` — **CHỈ ở Reporting, KHÔNG In Progress** | `closeAudit` |

**Ràng buộc (`InternalAuditDetailView.vue` + `stores/imm16.ts` + `api/imm16.ts`):**
- `api/imm16.ts` `InternalAudit` += `allowed_transitions?: string[]` + `can_operate?: boolean` + `can_close?: boolean`.
- Gỡ TOÀN BỘ `audit.status ===` / `['...'].includes(audit.status)` khỏi `<script>` + `<template>` (nút chỉ dùng cờ + `at`). `status` chỉ còn cho badge/stepper.
- `allowed_transitions` rỗng HOẶC thiếu cờ → **0 CTA** (ẩn, không disable). Worker cũ (3 field vắng) → `?? []`/`?? false` → CTA ẩn, KHÔNG crash.
- Nút Đóng gate bằng `can_close` (submit) — KHÔNG hiện ở In Progress dù `can_operate=true`.
- Sau mỗi transition: refetch `get_audit` để `allowed_transitions`/cờ cập nhật (Planned→In Progress ẩn Bắt đầu, hiện editor bảng kiểm…). Error map interceptor VN, KHÔNG echo traceback.
- KHÔNG leak EN/raw status; nhãn nút giữ tiếng Việt.
- Test: `InternalAuditDetailView.ctaGate.test.ts` — matrix `status × {can_operate, can_close}` + anti-dead-control click→`startAudit`/`completeAuditChecklist`/`closeAudit` + degrade an toàn khi thiếu `allowed_transitions`.

## II.11. CAPADetailView.vue — Server-driven CTA gating (GATE-8 / LL-FE-51)

> **Vấn đề gốc (dead-gate):** 6 CTA vòng đời gate bằng client-map hardcode `TRANSITIONS: Record<string, Transition[]>` (lines 34-41) + `isVerification = wfState === 'Verification'` → QMS/QTV thấy/bấm action lệch quyền, desync khi workflow `IMM-16 CAPA Workflow` đổi cạnh. Chuyển sang hint server (`allowed_transitions` = tên workflow_state-đích + cờ `can_advance` từ `get_capa` — §III.D.1 backend / ADR-IMM-16-03). Đối xứng FindingDetail (II.9), InternalAuditDetail (II.10), PmWorkOrderDetail (imm08), IncidentDetail (imm12), RepairDetail (imm09).

**Nguồn quyền + hint:**
```ts
const at = computed(() => capa.value?.allowed_transitions ?? [])   // fallback an toàn
const canAdvance = computed(() => capa.value?.can_advance === true) // compliance.write (server-derived)
const isClosed = computed(() => (capa.value?.workflow_state || 'Open') === 'Closed')
```

**Mỗi CTA = `canAdvance && at.includes('<workflow_state-đích>')`** — KHÔNG còn `TRANSITIONS[wfState]` / `isVerification`. Dùng **nút rời tường minh** (mirror Finding/Audit), nhãn CTA hardcode VN trong `<template>` (KHÔNG map client edge):

| CTA | Điều kiện | Endpoint |
|---|---|---|
| Bắt đầu điều tra | `canAdvance && at.includes('Investigating')` — ở Open **và** Re-opened | `advanceCapaState(name, 'Investigating')` |
| Lập kế hoạch hành động | `canAdvance && at.includes('Action Plan')` (mở modal payload VR-05 method + VR-12 due_date) | `advanceCapaState(name, 'Action Plan', payload)` |
| Bắt đầu thực thi | `canAdvance && at.includes('Implementation')` | `advanceCapaState(name, 'Implementation')` |
| Chuyển sang xác minh | `canAdvance && at.includes('Verification')` | `advanceCapaState(name, 'Verification')` |
| Đóng CAPA | `canAdvance && at.includes('Closed')` (cổng Verification) → mở modal hiệu quả, `result='Effective'` | **`performEffectivenessCheck`** |
| Mở lại do chưa hiệu quả | `canAdvance && at.includes('Re-opened')` (cổng Verification) → modal hiệu quả, `result='Not Effective'` | **`performEffectivenessCheck`** |

**Ràng buộc (`CAPADetailView.vue` + `stores/imm16.ts` + `api/imm16.ts`):**
- `api/imm16.ts` `CapaDetail` (extends `CapaRecord`) += `allowed_transitions?: string[]` + `can_advance?: boolean`.
- **XOÁ HOÀN TOÀN** `interface Transition` + `const TRANSITIONS: Record<string, Transition[]>` (lines 34-41) + `const transitions` + `const isVerification`. `wfState`/`workflow_state` chỉ còn cho badge/stepper + `isClosed`. `startTransition(target: CapaWorkflowState)` nhận thẳng target (nút rời truyền literal), KHÔNG tra client-map.
- 2 nút hiệu quả **Đóng/Mở lại** gate bằng `at.includes('Closed')` / `at.includes('Re-opened')` — **thay** `v-if="isVerification"` hardcode. Vẫn gọi `performEffectivenessCheck` (thu `result` Effective/Not Effective → BE `Closed`/`Re-opened`).
- `allowed_transitions` rỗng HOẶC thiếu cờ → **0 CTA** (ẩn, không disable). Worker cũ (2 field vắng) → `?? []`/`?? false` → CTA ẩn, KHÔNG crash.
- **Hint khi rỗng:** `!isClosed && at.length === 0` → dòng gợi ý VN. Phân nhánh: `!canAdvance` → "Bạn không đủ quyền thao tác (cần quyền cập nhật tuân thủ)"; ngược lại (có quyền nhưng state không còn cạnh) → "Không có thao tác khả dụng ở trạng thái hiện tại". Ở `isClosed` → badge "CAPA đã đóng — {ngày}" (giữ nguyên).
- Sau mỗi transition / effectiveness: refetch `get_capa` → `allowed_transitions`/`can_advance` cập nhật. Error map interceptor VN, KHÔNG echo traceback.
- Nhãn CTA đầy đủ tiếng Việt (LL-FE-53); KHÔNG leak `workflow_state` raw/EN ra UI (badge dùng `capaWorkflowLabel`).
- Test: `CAPADetailView.ctaGate.test.ts` — matrix `workflow_state × can_advance` + anti-dead-control click→`advanceCapaState(name,'Investigating'/'Action Plan'/'Implementation'/'Verification')` & Đóng/Mở lại→`performEffectivenessCheck` + degrade an toàn khi thiếu `allowed_transitions`/`can_advance`.

## II.12. ManagementReviewDetailView.vue — Server-driven CTA gating (GATE-8 / LL-FE-51)

> **Vấn đề gốc (dead-gate / dead-control):** 3 CTA vòng đời gate bằng **client-map hardcode** `NEXT_LABEL: Record<string,{label,target}>` (lines 29-36) + `canClose = status === 'Minutes Approved'` → MỌI user xem-được (kể cả read-only) thấy/bấm nút rồi BE `FORBIDDEN` 403 (client-map KHÔNG biết caller có `compliance.submit`), desync khi `_MR_TRANSITIONS`/workflow đổi cạnh. Đây là workflow IMM-16 **thứ 4/4 — cái DUY NHẤT chưa server-driven**. Chuyển sang hint server (`allowed_transitions` = tên status-đích + 2 cờ `can_advance`/`can_close` từ `get_management_review` — §III.F.1 backend / ADR-IMM-16-04). Đối xứng CAPADetail (II.11), InternalAuditDetail (II.10), FindingDetail (II.9), PmWorkOrderDetail (imm08), IncidentDetail (imm12), RepairDetail (imm09).

**Nguồn quyền + hint:**
```ts
const at = computed(() => mr.value?.allowed_transitions ?? [])     // fallback an toàn
const canAdvance = computed(() => mr.value?.can_advance === true)  // compliance.submit (server-derived)
const canCloseFlag = computed(() => mr.value?.can_close === true)  // compliance.submit (server-derived)
const isClosed = computed(() => (mr.value?.status || 'Draft') === 'Closed')
```

**Mỗi CTA = cờ quyền tương ứng && `at.includes('<status-đích>')`** — KHÔNG còn `NEXT_LABEL[status]` / `nextStep` / `canClose = status === 'Minutes Approved'`. Dùng **nút rời tường minh** (mirror CAPA/Audit), nhãn CTA hardcode VN trong `<template>` khớp EXACT workflow `IMM-16 Management Review Workflow`:

| CTA (nhãn khớp workflow) | Điều kiện | Endpoint |
|---|---|---|
| Đánh dấu Đã họp | `canAdvance && at.includes('Held')` | `advanceMrState(name, 'Held')` |
| Phê duyệt Biên bản | `canAdvance && at.includes('Minutes Approved')` | `advanceMrState(name, 'Minutes Approved')` |
| Đóng và xuất biên bản | `canCloseFlag && at.includes('Closed')` (mở modal minutes_doc + ≥1 output action) | `finalizeManagementReview(name, minutes_doc, actions)` |

**Ràng buộc (`ManagementReviewDetailView.vue` + `stores/imm16.ts` + `api/imm16.ts`):**
- `api/imm16.ts` `ManagementReview` += `allowed_transitions?: string[]` + `can_advance?: boolean` + `can_close?: boolean`.
- **XOÁ HOÀN TOÀN** `const NEXT_LABEL: Record<string, { label; target }>` (lines 29-36) + `const nextStep` + `const canClose = computed(() => status.value === 'Minutes Approved')`. `status` chỉ còn cho badge/stepper + `isClosed` + `editable`. Nút chuyển-cạnh truyền literal target (`'Held'`/`'Minutes Approved'`) trực tiếp vào `advance(target)`, KHÔNG tra client-map.
- `allowed_transitions` rỗng HOẶC thiếu cờ → **0 CTA** (ẩn, không disable). Worker cũ / BE lỗi (3 field vắng) → `?? []`/`?? false` → CTA ẩn, KHÔNG dead-control, KHÔNG crash.
- **Hint khi rỗng:** `!isClosed && at.length === 0` → dòng gợi ý VN. Phân nhánh: `!canAdvance && !canCloseFlag` → "Bạn không đủ quyền thao tác (cần quyền phê duyệt tuân thủ)"; ngược lại → "Không có thao tác khả dụng ở trạng thái hiện tại". Ở `isClosed` → giữ badge trạng thái "Đã đóng".
- Sau mỗi transition / finalize: refetch `get_management_review` (`refreshAll`) → `allowed_transitions`/2 cờ cập nhật (Draft→Held ẩn "Đánh dấu Đã họp", hiện "Phê duyệt Biên bản"…). Error map interceptor VN, KHÔNG echo traceback.
- Nhãn CTA đầy đủ tiếng Việt (LL-FE-53); KHÔNG leak `status`/`workflow_state` raw/EN ra UI (badge dùng nhãn VI qua `StatusBadge`).
- Test: `ManagementReviewDetailView.ctaGate.test.ts` — matrix `status × {can_advance, can_close}` + anti-dead-control click→`advanceMrState(name,'Held'/'Minutes Approved')` & Đóng→`finalizeManagementReview` + degrade an toàn khi thiếu `allowed_transitions`/2 cờ + user không quyền → 0 CTA.

## UX Patterns chung

### Toast / Notification

| Loại | Màu TailwindCSS | Nội dung mẫu |
|---|---|---|
| Success | `bg-green-100 text-green-800` | "CAPA đã chuyển sang Implementation" |
| Warning | `bg-yellow-100 text-yellow-800` | "CAPA Critical này đã quá hạn 3 ngày" |
| Error | `bg-red-100 text-red-800` | error từ `response.error` tiếng Việt |

### Permission-driven UI

| UI Element | Ẩn khi |
|---|---|
| `+ Tạo Rule` | role NOT IN {Tổ HC-QLCL, CMMS Admin} |
| Button [Waive] | role NOT IN {VP Block2, CMMS Admin} |
| Button [Confirm NC] / [Mark FP] | role NOT IN {Tổ HC-QLCL, Internal Auditor} |
| Button [Publish Scorecard] | role NOT IN {Tổ HC-QLCL, VP Block2, CMMS Admin} |
| Button [Finalize MR] | role NOT IN {VP Block2, CMMS Admin} |
| Button [Close Audit] | role NOT IN {Tổ HC-QLCL, VP Block2, CMMS Admin} |
| Button [Effectiveness Check] | role NOT IN {Tổ HC-QLCL, CMMS Admin} |

### Responsive

- Desktop ≥ 1280px: Full layout, Kanban columns đủ
- Tablet 768-1279px: Heatmap scroll horizontal, Kanban scroll horizontal
- Mobile < 768px: Dashboard cards stack vertical; Heatmap chuyển list view; Kanban chuyển list

### Realtime Updates

Subscribe `frappe.realtime.on('imm16:finding_created', ...)` trên Dashboard + Finding List. Subscribe `imm16:capa_state_changed` cho Kanban auto-move card. Subscribe `imm16:scorecard_published` cho Dashboard refresh.
