# 06 — Frontend Design

| Mục | Giá trị |
|---|---|
| Module | IMM-12 — Incident & CAPA Management |
| Phạm vi | Per-module |
| Owner | FE Lead |
| Cập nhật | 2026-05-18 |
| Trạng thái | ✅ Live — Vue components + store + 14 endpoint API đã build |

---

## 1. Sitemap

Routes and component names are based on **actual Vue files** in `frontend/src/views/incident/`.

> Path prefix thực tế = `/incidents/...` (xem `frontend/src/router/index.ts`). Module key `imm12` được map qua regex `/^\/incidents/` → `imm12` cho sidebar.

| Route (actual) | Vue Component (actual filename) | Role Guard | Status |
|---|---|---|---|
| `/incidents` (redirect) | → `/incidents/dashboard` | Any | ✅ Live |
| `/incidents/dashboard` | `views/incident/IMM12DashboardView.vue` | Workshop Lead, QA, Ops Manager | ✅ Live |
| `/incidents/list` | `views/incident/IncidentListView.vue` | Any | ✅ Live |
| `/incidents/new` | `views/incident/IncidentCreateView.vue` | Reporting User, Workshop Lead | ✅ Live |
| `/incidents/:id` | `views/incident/IncidentDetailView.vue` | Any (actions per role) | ✅ Live |
| `/rca` | `views/incident/RCAListView.vue` | Workshop Lead, QA Officer, Compliance Manager | 🆕 3b (mockup `docs/fe/12-incident/rca-list.html`) |
| `/rca/:id` | `views/incident/RCADetailView.vue` | Workshop Lead, QA Officer | ✅ Live |
| `/capa` | `views/incident/CAPAListView.vue` | Any | ✅ Live |
| `/capa/:id` | `views/incident/CAPADetailView.vue` | Any (close: QA Officer only) | ✅ Live |

**Sidebar nav config (`frontend/src/constants/modules.ts`):**
```typescript
{
  id: 'imm12', code: 'IMM-12',
  label: 'Bảo trì khắc phục',
  description: 'Triage sự cố, escalation, RCA, SLA corrective',
  icon: 'shield',
  to: '/incidents/dashboard',
  roles: [...TECH_ROLES, Roles.CLINICAL, Roles.QA, Roles.DEPT_HEAD, Roles.DEPT_DEPUTY],
}
```

---

## 2. Mockups

### 2.1 Incident List (`/incidents/list`)

```text
┌─────────────────────────────────────────────────────────────────┐
│  SỰ CỐ THIẾT BỊ                              [+ Báo cáo sự cố] │
│                                                                  │
│  Severity [All ▼]  Status [Open+InProg ▼]  Asset [...]  [Clear] │
│  ─────────────────────────────────────────────────────────────  │
│  IR Code         Asset               Severity   Status   Aged   │
│  ─────────────────────────────────────────────────────────────  │
│  IR-2026-0042   Máy thở Drager E.  🔴 Critical  In Prog  3h    │
│  IR-2026-0041   Siêu âm GE Vivid   🟠 High      Open     1h    │
│  IR-2026-0040   ECG cấp cứu        🟡 Medium    Resolved  1d   │
│  ─────────────────────────────────────────────────────────────  │
│  67 records                                  [← 1 2 3 4 →]     │
└─────────────────────────────────────────────────────────────────┘
```

**API:** `list_incidents` · **State:** `useImm12Store.incidents` · **Filter defaults:** `status in [Open, Acknowledged, In Progress]` (actual states từ `services/imm12.py`: Open / Acknowledged / In Progress / Resolved / RCA Required / Closed / Cancelled)

#### 2.1.a Workflow stepper + action buttons (D3 — SINGLE SOURCE cho FE)

State machine BE thật (khớp `imm_12_incident_workflow.json` + `_VALID_TRANSITIONS`). Stepper detail render 6 node tuyến chính; `RCA Required` là nhánh; `Cancelled` là terminal phụ.

`Open → Acknowledged → In Progress → Resolved → Closed` (+ `Resolved → RCA Required → Closed`)

| Status hiện tại | Nút hiển thị (label VN) | Action API | Transition | Role allowed |
|---|---|---|---|---|
| Open | "Tiếp nhận" | `acknowledge_incident` | Open → **Acknowledged** | Corrective Manager |
| Open | "Hủy sự cố" | `cancel_incident` | Open → Cancelled | System Manager |
| Acknowledged | "Bắt đầu xử lý" | `start_work` | Acknowledged → **In Progress** | Corrective User |
| Acknowledged | "Hủy sự cố" | `cancel_incident` | Acknowledged → Cancelled | System Manager |
| In Progress | "Đánh dấu đã giải quyết" | `resolve_incident` | In Progress → Resolved | Corrective User |
| In Progress | "Hủy sự cố" | `cancel_incident` | In Progress → Cancelled | System Manager |
| Resolved | "Yêu cầu RCA" | `create_rca` | Resolved → RCA Required | Compliance Manager |
| Resolved | "Đóng sự cố" | `close_incident` | Resolved → Closed | System Manager / Workshop Lead / QA Officer |
| RCA Required | "Mở RCA" (link) → đóng sau khi RCA Completed | `close_incident` (gated BR-12-02) | RCA Required → Closed | System Manager |

> **D3 chốt (Self-Correction BE):** `acknowledge_incident()` PHẢI set `Open → Acknowledged` (KHÔNG nhảy thẳng In Progress). Thêm action `start_work()` cho `Acknowledged → In Progress`. FE stepper align mô hình 2 bước này. Đây là root-cause fix, KHÔNG vá ở FE.
> BR-12-02: High/Critical hoặc Chronic → nút "Đóng sự cố" ở RCA Required bị block đến khi RCA `Completed`.

### 2.2 New Incident Form (`/incidents/list/new`)

```text
┌─────────────────────────────────────────────────────────────────┐
│  BÁO CÁO SỰ CỐ THIẾT BỊ                          [Hủy] [Gửi]  │
│                                                                  │
│  Section 1: Thiết bị                                            │
│  Thiết bị *          [Search AC Asset ▼]                        │
│  Khoa phòng          [Auto-fill from Asset]                     │
│                                                                  │
│  Section 2: Mô tả sự cố                                         │
│  Mã lỗi *            [Select fault_code ▼]                      │
│  Mức độ *            ◉ Thấp  ○ TB  ○ Cao  ○ Nghiêm trọng        │
│  (value enum BE: Low / Medium / High / Critical — KHÔNG Minor/Major) │
│  Mô tả sự cố *       [Textarea 5 rows]                          │
│  Workaround?         ☑ Đã chuyển bệnh nhân sang thiết bị khác  │
│  Ảnh đính kèm        [Upload — drag & drop]                     │
│                                                                  │
│  Section 3: Tác động lâm sàng (hiển thị khi severity=Critical) │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ ⚠️ THIẾT BỊ HỖ TRỢ SỰ SỐNG — BẮT BUỘC ĐIỀN              │ │
│  │ Tác động lâm sàng *  [Textarea — clinical_impact]         │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Incident Detail (`/incidents/list/:name`)

```text
┌─────────────────────────────────────────────────────────────────┐
│  IR-2026-0042              ● RCA REQUIRED        [Actions ▼]    │
│  Máy thở Drager Evita 800 — ICU               🔴 CRITICAL       │
│                                                                  │
│  Tabs: [Thông tin] [Timeline] [Repair WO] [RCA] [CAPA]          │
│  ─────────────────────────────────────────────────────────────  │
│  Tab: Thông tin                                                  │
│    Asset: ACC-ASSET-2026-0012                                   │
│    Mã lỗi: VENT_ALARM_HIGH                                      │
│    Báo cáo bởi: nurse1@hospital.vn — 08:12 18/04/2026          │
│    Tiếp nhận: workshop_lead@hospital.vn — 08:35 18/04/2026     │
│    KTV phụ trách: ktv.nguyen@hospital.vn                        │
│    Tác động: "Bệnh nhân phụ thuộc, đã chuẩn bị bóng ambu"      │
│                                                                  │
│  Actions (Workshop Lead, status=RCA Required):                  │
│    [Mở RCA-2026-0012]                                           │
│                                                                  │
│  Tab: Timeline (IncidentTimeline component)                     │
│    08:12 Open    | nurse1     | Incident created                │
│    08:35 Ack.    | wl.lead    | Assigned to KTV Nguyễn          │
│    11:45 Resolved| wl.lead    | Sensor replaced + calibrate     │
│    11:46 RCA Req | System     | Auto-triggered (Critical)       │
└─────────────────────────────────────────────────────────────────┘
```

### 2.4 RCA Form (`/rca/:id`)

```text
┌─────────────────────────────────────────────────────────────────┐
│  RCA-2026-0012           ● RCA IN PROGRESS     [Submit RCA →]   │
│  Asset: Máy thở Drager Evita 800 — Trigger: Critical Incident   │
│  Hạn: 25/04/2026 (còn 7 ngày)                                   │
│                                                                  │
│  Phương pháp *   ◉ 5-Why   ○ Fishbone   ○ Other                 │
│                                                                  │
│  ─── RCAFiveWhyEditor component ──────────────────────────────  │
│  Why 1: Tại sao alarm P_HIGH?  → [Sensor sai số]               │
│  Why 2: Tại sao sensor sai số? → [Drift do nhiệt độ]            │
│  Why 3: Tại sao nhiệt độ cao?  → [HVAC không ổn định]           │
│  Why 4: Tại sao HVAC không ổn? → [Maintenance HVAC trễ]         │
│  Why 5: Tại sao maintenance trễ? → [Không có schedule trong CMMS│
│  ──────────────────────────────────────────────────────────────  │
│  Nguyên nhân gốc *  [Sensor degraded do nhiệt độ ICU vượt 28°C] │
│  Yếu tố đóng góp    [HVAC không ổn định 3 tháng qua]            │
│  Corrective         [Thay sensor + calibrate]                   │
│  Preventive         [PM HVAC tích hợp vào CMMS, 1 tháng/lần]   │
│                                                                  │
│  ⓘ Submit sẽ tự động tạo CAPA Record qua imm00.create_capa()    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Components

> Views implemented: `IncidentListView.vue`, `IncidentCreateView.vue`, `IncidentDetailView.vue`, `RCADetailView.vue`, `CAPAListView.vue`, `CAPADetailView.vue`, `IMM12DashboardView.vue`.

| Component | Props | Mô tả |
|---|---|---|
| `SeverityBadge.vue` | `severity: "Low"\|"Medium"\|"High"\|"Critical"` | Color badge với icon (DocType `Incident Report.severity` có 4 mức Low/Medium/High/Critical) |
| `IncidentStatusBadge.vue` | `status: string` | Actual states: Open / Acknowledged / In Progress / Resolved / RCA Required / Closed / Cancelled |
| `CAPAStatusBadge.vue` | `status: string` | CAPA status badge |
| `RCAFiveWhyEditor.vue` | `modelValue: FiveWhyStep[]` | Steps use `{why_number, why_question, why_answer}` (actual field names) |
| `CAPACloseDialog.vue` | `capaName: string`, `@close` | Modal close CAPA |
| `IncidentTimeline.vue` | `incidentName: string` | Audit trail timeline |
| `ClinicalImpactWarning.vue` | `severity: string` | Banner for Critical severity |
| `SlaBreachBadge.vue` (MỚI — BR-12-09) | `responseBreached?: 0\|1`, `resolutionBreached?: 0\|1` | Badge đỏ "Vi phạm SLA" — đọc TRỰC TIẾP từ field cờ `response_breached`/`resolution_breached`. Render 1 badge / 1 loại breached=1; không cờ nào set → render gì cả (`v-if`). Nhãn tiếng Việt qua SSoT, KHÔNG leak "breached"/English. |

### 3.1 SLA breach badge — i18n SSoT (BR-12-09)

> **Anti-leak (memory wave2_ui_bugs / formatters SSoT):** KHÔNG hiển thị chuỗi BE thô `response_breached`/`resolution_breached`/`breached`. Thêm SSoT vào `frontend/src/constants/labels.ts` (KHÔNG hardcode trong component):

```typescript
// labels.ts — SLA breach (IMM-12, khớp Incident Report.response_breached / resolution_breached)
export const SLA_BREACH_LABEL = {
  response:   'Vi phạm SLA tiếp nhận',
  resolution: 'Vi phạm SLA xử lý',
} as const
export const SLA_BREACH_BADGE_CLASS = 'bg-red-100 text-red-700 ring-1 ring-red-200'
```

**Nơi hiển thị (cả 2 — verify count khớp, không divergence):**
- `IncidentListView.vue` — cột/chip cạnh severity: nếu `ir.response_breached` → badge "Vi phạm SLA tiếp nhận"; nếu `ir.resolution_breached` → badge "Vi phạm SLA xử lý" (có thể hiện cả 2). Cần BE `list_incidents` trả 2 field (xem `05_API §12 DELTA`).
- `IMM12DashboardView.vue` — thêm 2 stat card đọc `store.dashboard.stats.sla_response_breached` / `sla_resolution_breached` (nhãn "Vi phạm SLA tiếp nhận" / "Vi phạm SLA xử lý"). Card click-through (drilldown) lọc list theo cờ tương ứng nếu store hỗ trợ filter.

**Divergence guard (FE test):** số trên 2 stat card = số incident có cờ tương ứng trong list (cùng nguồn `Incident Report.response_breached`/`resolution_breached`). Vitest assert label render từ `SLA_BREACH_LABEL` (không chứa substring "breach"/"breached" tiếng Anh trong DOM). `vue-tsc` xanh.

### 2.5 Card "Đang mở" — SoT open-set + drill (BR-12-11) — DELTA vòng 21

`IMM12DashboardView.vue` card đầu tiên (hiện bind `stats.open` + nhãn 'Mới mở' + bare `/incidents/list`) PHẢI đổi để khớp SoT BE `open_incident_filter()`:

| Thuộc tính | TRƯỚC (sai) | SAU (BR-12-11) |
|---|---|---|
| Binding count | `stats.open ?? 0` | `stats.open_total ?? 0` (count cả Acknowledged + RCA Required, không chỉ Open) |
| Nhãn card | literal `'Mới mở'` | `INCIDENT_OPEN_FILTER_LABEL` (= 'Đang mở', SSoT `constants/labels.ts:327` round-18) — KHÔNG hardcode literal mới |
| Drill `@click` | `router.push('/incidents/list')` | `router.push('/incidents/list?open=1')` (hoặc object `{ path:'/incidents/list', query:{ open:'1' } }`) |
| "Xem tất cả" của "Sự cố đang xử lý" | `router.push('/incidents/list')` | `router.push('/incidents/list?open=1')` |

**Invariant (FE test BẮT BUỘC):** card count (`stats.open_total`) == số dòng list sau khi drill `/incidents/list?open=1` (list loại Closed/Cancelled/Resolved). Vì `active_incidents` BE đã dùng cùng `open_incident_filter()`, số dòng "Sự cố đang xử lý" (≤10) cũng phản ánh đúng open-set.

**Phân biệt 2 khái niệm nhãn (KHÔNG nhầm):**
- `incidentStatusLabel('Open')` = 'Mới mở' — nhãn **trạng thái từng-state** (giữ nguyên, dùng cho badge per-row + WorkflowStepper). KHÔNG đổi.
- `INCIDENT_OPEN_FILTER_LABEL` = 'Đang mở' — nhãn **filter ảo open-set** (card open_total + chip drill). Đây là cái card "Đang mở" dùng.

**Type delta (`api/imm12.ts`):** thêm `open_total: number` vào cả `interface IncidentStats` (line 75) và `interface DashboardStats` (line 229) — khớp BE service `get_incident_stats()` trả `open_total`. Backward-compat: GIỮ `open` + `investigating` (consumer khác còn đọc).

### 2.6 KPI strip severity = open-set (BR-12-11b) — DELTA vòng 29

KPI strip `IncidentListView.vue` `kpiItems` (computed, line ~50-64) — 4 tile trên filter bar. 2 tile severity hiện bind count GLOBAL mọi-status (`stats.critical` / `stats.high`) ⇒ **mâu thuẫn thị giác strip-vs-table** khi user drill `?open=1` hoặc `?severity=High` (bảng chỉ open-set, strip vẫn đếm cả Closed/Cancelled/Resolved). Phải bind theo SoT open-set BE (`stats.critical_open` / `stats.high_open`):

| Tile | TRƯỚC (sai) | SAU (BR-12-11b) |
|---|---|---|
| 'Sự cố nghiêm trọng' | `stats.critical` (global) | binding `stats.critical_open ?? 0` (open-set); nhãn → **'Sự cố nghiêm trọng đang mở'** |
| 'Sự cố mức cao' | `stats.high` (global) | binding `stats.high_open ?? 0` (open-set); nhãn → **'Sự cố mức cao đang mở'** |
| 'Lặp lại (Chronic)' | `stats.chronic` | KHÔNG đổi |
| 'Đã đóng' | `stats.closed` | KHÔNG đổi |

- Strip KHÔNG còn đọc `stats.critical` / `stats.high` global (2 key đó GIỮ ở type cho donut/consumer cũ, nhưng strip không bind).
- Nhãn làm rõ ngữ nghĩa **open-set** → tránh user hiểu nhầm là tổng toàn cục. (Nếu dự án có SSoT label store, ưu tiên hằng số thay literal — nhưng strip này dùng literal cục bộ trong `kpiItems`, theo pattern hiện hữu của 4 tile.)

**Invariant (FE test BẮT BUỘC):** trên `/incidents/list?open=1` (data live: 1 Critical-open + 2 High-open trong open-set), tile 'Sự cố nghiêm trọng đang mở' == số dòng Critical trong bảng == 1; tile 'Sự cố mức cao đang mở' == số dòng High == 2. KHÔNG còn 0/0 (bug alias chết cũ) hay số global gồm Closed. Vitest assert: tile value đọc `critical_open`/`high_open`, KHÔNG `critical`/`high`.

**Type delta (`api/imm12.ts`):** thêm `critical_open?: number` + `high_open?: number` vào `interface IncidentStats` (+ `DashboardStats` cho parity vì `get_dashboard().stats == get_incident_stats()`). Optional (forward-compat, strip fallback `?? 0`). GIỮ `critical` + `high` global.

**Design tokens — Severity (4 mức theo DocType):**
```typescript
// tokens/severity.ts
export const severityTokens = {
  Low:      { bg: "bg-slate-50",   border: "border-slate-500",  text: "text-slate-700",  icon: "·"  },
  Medium:   { bg: "bg-yellow-50",  border: "border-yellow-600", text: "text-yellow-700", icon: "i"  },
  High:     { bg: "bg-orange-50",  border: "border-orange-600", text: "text-orange-700", icon: "!"  },
  Critical: { bg: "bg-red-50",     border: "border-red-600",    text: "text-red-700",    icon: "!!" },
} as const
```

**Design tokens — Status badge (khớp `_VALID_TRANSITIONS` trong `services/imm12.py`):**
```typescript
export const incidentStatusTokens = {
  Open:           { color: "gray",   icon: "o" },
  Acknowledged:   { color: "blue",   icon: ">" },
  "In Progress":  { color: "indigo", icon: "~" },
  Resolved:       { color: "green",  icon: "v" },
  "RCA Required": { color: "amber",  icon: "?" },
  Closed:         { color: "slate",  icon: "x" },
  Cancelled:      { color: "red",    icon: "-" },
} as const
```

---

## 4. Pinia Store — `useImm12Store`

> ✅ Store đã hiện hữu tại `frontend/src/stores/imm12.ts`. Các view trong `views/incident/` cũng có thể gọi trực tiếp `api/imm12.ts` qua composable khi không cần state chia sẻ. Skeleton dưới đây phản ánh interface store.
>
> **DELTA type (BR-12-09):** `types/imm12.ts::IncidentReport` thêm `response_breached?: 0|1` + `resolution_breached?: 0|1` (khớp field BE `list_incidents`/`get_incident_detail`). Dashboard `stats` type thêm `sla_response_breached: number` + `sla_resolution_breached: number`.
>
> **DELTA type (BR-12-11, vòng 21):** `api/imm12.ts::IncidentStats` + `DashboardStats` thêm `open_total: number` (count SoT `open_incident_filter()`). Card "Đang mở" bind `stats.open_total`; KHÔNG xoá `open`/`investigating`.
>
> **DELTA type (BR-12-11b, vòng 29):** `api/imm12.ts::IncidentStats` + `DashboardStats` thêm `critical_open?: number` + `high_open?: number` (count SoT `open_incident_filter()∧severity`). KPI strip `IncidentListView.vue` tile severity bind `stats.critical_open ?? 0` / `stats.high_open ?? 0` + nhãn 'đang mở'; KHÔNG xoá `critical`/`high` global. Xem §2.6.

```typescript
// src/stores/imm12.ts  (actual file — interface tham khảo)
import { defineStore } from "pinia"
import { ref, computed } from "vue"
import type { IncidentReport, CAPARecord, RCARecord, ChronicFailure } from "@/types/imm12"

export const useImm12Store = defineStore("imm12", () => {
  // ─── State ───────────────────────────────────────────────
  const incidents       = ref<IncidentReport[]>([])
  const activeIncident  = ref<IncidentReport | null>(null)
  const capaList        = ref<CAPARecord[]>([])
  const rcaList         = ref<RCARecord[]>([])
  const activeRCA       = ref<RCARecord | null>(null)
  const chronicFailures = ref<ChronicFailure[]>([])
  const loading         = ref(false)
  const error           = ref<string | null>(null)

  // ─── Computed ────────────────────────────────────────────
  const openIncidents = computed(() =>
    incidents.value.filter((ir) => !["Closed", "Cancelled"].includes(ir.status))
  )
  const criticalIncidents = computed(() =>
    openIncidents.value.filter((ir) => ir.severity === "Critical")
  )
  const overdueCAPAs = computed(() =>
    capaList.value.filter((c) => c.status === "Overdue")
  )

  // ─── Actions ─────────────────────────────────────────────
  async function reportIncident(payload: NewIncidentPayload): Promise<string> {
    loading.value = true
    const res = await useApi().run("assetcore.api.imm12.report_incident", payload)
    incidents.value.unshift(res.data)
    loading.value = false
    return res.data.name
  }

  async function acknowledgeIncident(name: string, assignedTo: string, notes = "") {
    const res = await useApi().run("assetcore.api.imm12.acknowledge_incident",
      { name, assigned_to: assignedTo, notes })
    _patchIncident(name, res.data)
  }

  async function resolveIncident(name: string, resolutionNotes: string) {
    const res = await useApi().run("assetcore.api.imm12.resolve_incident",
      { name, resolution_notes: resolutionNotes })
    _patchIncident(name, res.data)
    return res.data  // may include rca_record
  }

  async function closeIncident(name: string) {
    const res = await useApi().run("assetcore.api.imm12.close_incident", { name })
    _patchIncident(name, res.data)
  }

  async function submitRCA(payload: SubmitRCAPayload): Promise<string> {
    const res = await useApi().run("assetcore.api.imm12.submit_rca", payload)
    return res.data.linked_capa
  }

  // CAPA — uses IMM-00 LIVE endpoints
  async function closeCAPA(payload: CloseCAPAPayload) {
    await useApi().run("assetcore.api.imm00.close_capa", payload)
    const idx = capaList.value.findIndex((c) => c.name === payload.capa_name)
    if (idx !== -1) capaList.value[idx].status = "Closed"
  }

  function _patchIncident(name: string, data: Partial<IncidentReport>) {
    const idx = incidents.value.findIndex((ir) => ir.name === name)
    if (idx !== -1) Object.assign(incidents.value[idx], data)
    if (activeIncident.value?.name === name) Object.assign(activeIncident.value, data)
  }

  return {
    incidents, activeIncident, capaList, rcaList, activeRCA,
    chronicFailures, loading, error,
    openIncidents, criticalIncidents, overdueCAPAs,
    reportIncident, acknowledgeIncident, resolveIncident,
    closeIncident, submitRCA, closeCAPA,
  }
}, { persist: false })
```

---

## 5. Vue Query Keys

```typescript
// src/api/queryKeys.ts
export const imm12Keys = {
  all:            ["imm12"] as const,
  incidents:      () => [...imm12Keys.all, "incidents"] as const,
  incident:       (name: string) => [...imm12Keys.incidents(), name] as const,
  rca:            () => [...imm12Keys.all, "rca"] as const,
  rcaDetail:      (name: string) => [...imm12Keys.rca(), name] as const,
  capa:           () => [...imm12Keys.all, "capa"] as const,
  capaDetail:     (name: string) => [...imm12Keys.capa(), name] as const,
  chronic:        () => [...imm12Keys.all, "chronic"] as const,
  dashboard:      (year: number, month: number) =>
                    [...imm12Keys.all, "dashboard", year, month] as const,
}
```

**Invalidate rules:**
| Action | Invalidate |
|---|---|
| `reportIncident` | `imm12Keys.incidents()` |
| `acknowledgeIncident`, `resolveIncident`, `closeIncident` | `imm12Keys.incident(name)` + `imm12Keys.incidents()` |
| `submitRCA` | `imm12Keys.rcaDetail(name)` + `imm12Keys.capa()` + `imm12Keys.incident(ir)` |
| `closeCAPA` | `imm12Keys.capaDetail(name)` + `imm12Keys.capa()` |

---

## 6. API Pattern

**File:** `frontend/src/api/imm12.ts` ✅ LIVE — base URL `/api/method/assetcore.api.imm12`

**Exported functions (actual):**
- `listIncidents(params)` → `{pagination, items: IncidentDetail[]}`
- `getIncident(name)` → `IncidentDetail`
- `acknowledgeIncident(name, notes, assigned_to)` → `{name, status}`
- `resolveIncident(name, resolution_notes, root_cause)` → `{name, status, linked_capa?}`
- `closeIncident(name, verification_notes)` → `{name, status, closed_date?}`
- `getIncidentStats()` → `IncidentStats`
- `reportIncident(data: ReportIncidentPayload)` → `{name, status, severity}`
- `cancelIncident(name, reason)` → `{name, status}`
- `createRca(incident_name, rca_method)` → `{name, status}`
- `getRca(name)` → `RCADetail`
- `submitRca(data: SubmitRcaPayload)` → `{name, status, linked_capa?}` (serializes `five_why_steps` to JSON string)
- `getAssetIncidentHistory(asset, limit)` → `{asset, items}`
- `getChronicFailures()` → `{items: ChronicFailure[]}`
- `getDashboard()` → `DashboardData`

**Corrected cascade watch (actual field `incident_type`, not `fault_description`):**
```typescript
// IncidentCreateView.vue
watch(() => form.severity, (val) => {
  if (val !== "Critical") {
    form.clinical_impact = ""
  }
  showClinicalImpact.value = val === "Critical"
})
```

---

## 7. Copy & Feedback

| State | Component | Copy tiếng Việt |
|---|---|---|
| Empty (Incident List) | IncidentListView | "Chưa có sự cố nào được ghi nhận." · CTA: "Báo cáo sự cố" |
| Empty (CAPA List) | CAPAListView | "Không có CAPA nào đang mở." |
| Empty (Chronic) | ChronicFailureView | "Không phát hiện lỗi mãn tính trong 90 ngày qua." |
| Loading | All lists | Skeleton placeholder (table rows) |
| Error (network) | All | Toast đỏ "Không thể tải dữ liệu. Vui lòng thử lại." + [Retry] |
| Error (BUSINESS_RULE: BR-12-01) | IncidentFormView | Inline: "Sự cố Critical bắt buộc mô tả tác động lâm sàng" |
| Error (BAD_STATE: BR-12-02) | IncidentDetailView | Modal: "Không thể đóng sự cố khi RCA chưa hoàn thành. Mở RCA-2026-0012 →" |
| Success (create IR) | IncidentFormView | Toast xanh "Sự cố đã ghi nhận" + redirect → `/incidents/list/:name` |
| Success (close CAPA) | CAPAFormView | Modal "CAPA đã đóng — audit đã ghi nhận." |
| Critical alert | App shell banner | 🔴 "Sự cố Critical đang mở: [IR-2026-0042] — Máy thở Drager E. — ICU" |

---

## 8. Accessibility

- Severity badges: icon + text label (không chỉ màu) — WCAG AA contrast
- `aria-label` cho action buttons: `aria-label="Tiếp nhận sự cố IR-2026-0042"`
- Focus trap trong `CAPACloseDialog` và Cancel Confirm modal
- `role="alert"` cho Critical banner (screen reader announces immediately)
- Keyboard navigation: Tab qua mọi action; Enter submit form; Esc đóng modal

---

## DoD — File 06 hoàn chỉnh

- [x] Sitemap (8 routes) — actual Vue files: IncidentListView · IncidentCreateView · IncidentDetailView · RCADetailView · CAPAListView · CAPADetailView · IMM12DashboardView
- [x] Sidebar nav TypeScript config
- [x] 4 ASCII mockups (List · New Form · Detail · RCA Form)
- [x] Component table (7 components với props — corrected actual state names)
- [x] Design tokens: severity (4 levels: Low/Medium/High/Critical) + status badge (5 actual states)
- [x] Pinia store `useImm12Store` (design spec — verify if store actually implemented separately)
- [x] Vue Query keys + invalidate rules
- [x] ✅ API client `api/imm12.ts` with 14 exported functions
- [x] Corrected cascade watch (incident_type field, not fault_description)
- [x] Copy / feedback table (8 states)
- [x] Accessibility checklist
- [ ] Playwright E2E tests
- [ ] Reviewed bởi FE Lead + UX
