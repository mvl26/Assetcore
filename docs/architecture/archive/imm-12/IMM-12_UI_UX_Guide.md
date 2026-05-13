# IMM-12 — UI/UX Guide

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-12 — Incident & CAPA Management |
| Phiên bản | 1.0.0 |
| Ngày cập nhật | 2026-04-18 |
| Trạng thái | **DRAFT — ⚠️ Mockup only** (FE chưa build, spec hướng dẫn implement) |
| Tác giả | AssetCore Team |

---

## 0. Tổng quan

Tài liệu này mô tả toàn bộ giao diện người dùng cho IMM-12 (Incident + CAPA + RCA), bao gồm:

- 6 màn hình chính (Incident List/Form, CAPA List/Form, RCA Form, Dashboard)
- Component reuse từ IMM-00 (UI shell, design system, app shell)
- Pinia store (Vue 3 Composition API)
- Permission-aware actions

**Trạng thái implementation: ⚠️ Mockup only — chưa có Vue component nào được build cho IMM-12.**

Tham chiếu chuẩn UI/UX của AssetCore: `docs/imm-00/IMM-00_UI_UX_Guide.md` §1–§4 (nguyên tắc UX, design system, app shell).

---

## 1. Sitemap / Routes

```text
/imm-12/                        → redirect /imm-12/incidents
  ├── /imm-12/incidents         → Incident List (filterable)        ⚠️ Mockup
  │     ├── /imm-12/incidents/new       → New Incident Form         ⚠️ Mockup
  │     └── /imm-12/incidents/:name     → Incident Detail/Edit      ⚠️ Mockup
  ├── /imm-12/capa              → CAPA List                         ⚠️ Mockup
  │     ├── /imm-12/capa/new            → New CAPA (manual)         ⚠️ Mockup
  │     └── /imm-12/capa/:name          → CAPA Detail/Close form    ⚠️ Mockup
  ├── /imm-12/rca               → RCA Record List                   ⚠️ Mockup
  │     └── /imm-12/rca/:name           → RCA Detail/5-Why form     ⚠️ Mockup
  ├── /imm-12/chronic           → Chronic Failure Monitor           ⚠️ Mockup
  └── /imm-12/dashboard         → KPI Dashboard                     ⚠️ Mockup
```

**Route Guard (route meta):**

| Route | Required Role |
|---|---|
| `/imm-12/incidents/new` | Reporting User, Workshop Lead |
| `/imm-12/incidents/:name` (edit actions) | Workshop Lead, QA Officer |
| `/imm-12/capa/:name` (close action) | QA Officer |
| `/imm-12/rca/:name` (submit) | Workshop Lead, QA Officer |
| `/imm-12/dashboard` | Workshop Lead, QA Officer, Ops Manager, Department Head |

---

## 2. Component Architecture (đề xuất)

```text
src/
├── views/imm12/
│   ├── IncidentListView.vue            ⚠️ Mockup
│   ├── IncidentFormView.vue            ⚠️ Mockup
│   ├── CAPAListView.vue                ⚠️ Mockup
│   ├── CAPAFormView.vue                ⚠️ Mockup (Close form for QA)
│   ├── RCAListView.vue                 ⚠️ Mockup
│   ├── RCAFormView.vue                 ⚠️ Mockup (5-Why / Fishbone)
│   ├── ChronicFailureView.vue          ⚠️ Mockup
│   └── Imm12DashboardView.vue          ⚠️ Mockup
│
├── components/imm12/
│   ├── SeverityBadge.vue               (Minor/Major/Critical color badge)
│   ├── IncidentStatusBadge.vue         (Open/Acknowledged/.../Closed)
│   ├── CAPAStatusBadge.vue             (Open/InProgress/PV/Closed/Overdue)
│   ├── ClinicalImpactWarning.vue       (banner khi Critical)
│   ├── RCAFiveWhyEditor.vue            (5 input rows)
│   ├── ChronicAlertBadge.vue           (badge "Chronic" trên IR/Asset)
│   ├── CAPACloseDialog.vue             (form với corrective + preventive + evidence)
│   └── IncidentTimeline.vue            (audit trail visualization)
│
└── stores/
    └── imm12.ts                        (Pinia — see §4)
```

---

## 3. Screen Specs

> Mọi mockup dưới đây là **ASCII reference cho FE implement** — chưa có component thực tế.

### 3.1 Incident List (`/imm-12/incidents`) — ⚠️ Mockup only

```text
┌─────────────────────────────────────────────────────────────────┐
│  SỰ CỐ THIẾT BỊ                              [+ Báo cáo sự cố] │
│                                                                  │
│  Filter: Severity [All ▼] · Status [Open+InProg ▼] · Asset [..] │
│  ─────────────────────────────────────────────────────────────  │
│  IR Code         Asset                Severity  Status   Aged   │
│  ─────────────────────────────────────────────────────────────  │
│  IR-2026-0042   Máy thở Drager E.   🔴 Critical In Prog  3h    │
│  IR-2026-0041   Siêu âm GE Vivid    🟠 Major    Open    1h    │
│  IR-2026-0040   ECG cấp cứu         🟡 Minor    Resolved 1d    │
│  ─────────────────────────────────────────────────────────────  │
│  Showing 1–20 of 67                              [Prev 1 2 Next]│
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 New Incident Form (`/imm-12/incidents/new`) — ⚠️ Mockup only

```text
┌─────────────────────────────────────────────────────────────────┐
│  BÁO CÁO SỰ CỐ THIẾT BỊ                         [Hủy] [Gửi]    │
│                                                                  │
│  Section 1: Thông tin thiết bị                                  │
│  Thiết bị *      [Search AC Asset ▼]                            │
│  Khoa phòng      [Auto: ICU – Hồi sức tích cực]                 │
│  Vị trí          [Auto: Phòng 302, Tầng 3]                      │
│                                                                  │
│  Section 2: Mô tả sự cố                                         │
│  Mã lỗi *        [Select fault_code ▼]                          │
│  Mức độ *        ◉ Minor   ○ Major   ○ Critical                 │
│  Mô tả *         [Textarea]                                     │
│  Workaround?     ☑ Đã chuyển bệnh nhân sang thiết bị khác       │
│  Ảnh đính kèm    [Upload — drag & drop]                         │
│                                                                  │
│  Section 3: Tác động lâm sàng (chỉ hiện khi Critical)           │
│  ⚠️ THIẾT BỊ HỖ TRỢ SỰ SỐNG — BẮT BUỘC ĐIỀN                    │
│  Tác động *      [Textarea — clinical_impact, BR-12-01]         │
└─────────────────────────────────────────────────────────────────┘
```

**Validation FE (mirror BR-12-01):**

```typescript
if (form.severity === "Critical" && !form.clinical_impact) {
  showError("Sự cố Critical bắt buộc mô tả tác động lâm sàng");
  return;
}
```

### 3.3 Incident Detail (`/imm-12/incidents/:name`) — ⚠️ Mockup only

```text
┌─────────────────────────────────────────────────────────────────┐
│  IR-2026-0042                  ● IN PROGRESS      [Actions ▼]  │
│  Máy thở Drager Evita 800 — ICU                  🔴 CRITICAL    │
│                                                                  │
│  Tabs: [Thông tin] [Timeline/Audit] [Repair WO] [RCA] [CAPA]    │
│  ─────────────────────────────────────────────────────────────  │
│                                                                  │
│  Tab: Thông tin                                                 │
│    Asset:        ACC-ASSET-2026-0012                           │
│    Mã lỗi:       VENT_ALARM_HIGH                               │
│    Mức độ:       🔴 Critical                                    │
│    Báo cáo bởi:  nurse1@hospital.vn — 08:12 18/04/2026         │
│    Tiếp nhận:    workshop_lead@hospital.vn — 08:35 18/04/2026  │
│    KTV phụ trách:[Select ▼]                                     │
│    Tác động:     "Bệnh nhân phụ thuộc, đã chuẩn bị bóng ambu"  │
│                                                                  │
│  Actions (theo role + status):                                  │
│    [Acknowledge]  [Assign KTV]  [Mark Resolved]  [Cancel]       │
└─────────────────────────────────────────────────────────────────┘
```

### 3.4 RCA Form (`/imm-12/rca/:name`) — ⚠️ Mockup only

```text
┌─────────────────────────────────────────────────────────────────┐
│  RCA-2026-0012                ● RCA IN PROGRESS  [Submit RCA]   │
│  Asset: Máy thở Drager Evita 800                                │
│  Trigger: P1 Incident (IR-2026-0042)                            │
│  Hạn: 25/04/2026 (còn 7 ngày)                                   │
│                                                                  │
│  Phương pháp RCA *  ◉ 5-Why  ○ Fishbone  ○ Other                │
│                                                                  │
│  ─── 5-Why Analysis ────────────────────────────────────────    │
│  Why 1: Tại sao alarm? → [Sensor sai số]                        │
│  Why 2: Tại sao sai số? → [Drift do nhiệt độ]                   │
│  Why 3: Tại sao nhiệt độ cao? → [HVAC không ổn định]            │
│  Why 4: Tại sao HVAC không ổn? → [Maintenance HVAC trễ]         │
│  Why 5: Tại sao trễ? → [Không có schedule trong CMMS]           │
│                                                                  │
│  Nguyên nhân gốc *  [Sensor degraded do nhiệt độ ICU vượt 28°C] │
│  Yếu tố đóng góp    [HVAC không ổn định 3 tháng qua]            │
│                                                                  │
│  Đề xuất CAPA (auto chuyển sang IMM CAPA Record sau Submit):    │
│  Corrective       [Thay sensor + calibrate]                     │
│  Preventive       [PM HVAC tích hợp vào CMMS, interval 1 tháng] │
│                                                                  │
│  ⓘ Submit sẽ tự động tạo CAPA Record qua imm00.create_capa()    │
└─────────────────────────────────────────────────────────────────┘
```

### 3.5 CAPA List (`/imm-12/capa`) — ⚠️ Mockup only

```text
┌─────────────────────────────────────────────────────────────────┐
│  CAPA RECORDS                                  [+ Tạo CAPA]    │
│                                                                  │
│  Filter: Status [Open+InProg ▼] · Severity [All ▼] · Asset [...]│
│  ─────────────────────────────────────────────────────────────  │
│  CAPA Code        Asset            Severity   Status     Due    │
│  ─────────────────────────────────────────────────────────────  │
│  CAPA-2026-0023  Máy thở Drager  🔴 Critical In Progress 12/05 │
│  CAPA-2026-0022  Siêu âm GE      🟠 Major    Pending Ver 30/04 │
│  CAPA-2026-0021  ECG cấp cứu     🟡 Minor    Overdue ⚠️  10/04 │
│  ─────────────────────────────────────────────────────────────  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.6 CAPA Close Form (`/imm-12/capa/:name`) — ⚠️ Mockup only

QA Officer view (chỉ QA Officer thấy nút "Close CAPA"):

```text
┌─────────────────────────────────────────────────────────────────┐
│  CAPA-2026-0023                ● PENDING VERIFICATION           │
│                                                                  │
│  Source:           RCA Record RCA-2026-0012 → IR-2026-0042      │
│  Asset:            Máy thở Drager Evita 800                     │
│  Severity:         🔴 Critical                                  │
│  Due Date:         12/05/2026                                   │
│                                                                  │
│  Root Cause *      [Sensor degraded do nhiệt độ ICU vượt 28°C]  │
│  Corrective *      [Thay sensor + calibrate]                    │
│  Preventive *      [PM HVAC tích hợp vào CMMS]                  │
│  Evidence          [calibration_cert.pdf] [+]                   │
│                                                                  │
│  ⓘ BR-00-08: cả 3 field root_cause + corrective + preventive    │
│     bắt buộc trước khi đóng CAPA.                               │
│                                                                  │
│  [Save]                              [Close CAPA →] (QA only)   │
└─────────────────────────────────────────────────────────────────┘
```

### 3.7 Dashboard (`/imm-12/dashboard`) — ⚠️ Mockup only

```text
┌─────────────────────────────────────────────────────────────────┐
│  IMM-12 KPI DASHBOARD                       Tháng 04/2026 [▼]   │
│                                                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │ Critical IRs │ │ RCA On-Time  │ │ CAPA On-Time │             │
│  │     5        │ │    93%  ✅    │ │   88%  ⚠️    │             │
│  └──────────────┘ └──────────────┘ └──────────────┘             │
│                                                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │ Chronic      │ │ MTTR (avg)   │ │ Open Incidents│            │
│  │    2  ⚠️     │ │  4.2 hours   │ │     12       │             │
│  └──────────────┘ └──────────────┘ └──────────────┘             │
│                                                                  │
│  Top 5 Asset có nhiều incident nhất 90 ngày:                    │
│   1. Máy siêu âm GE Vivid       — 5 IR  ⚠️ chronic              │
│   2. Máy thở Drager Evita        — 3 IR                          │
│   ...                                                            │
│                                                                  │
│  CAPA Closure Trend (6 tháng):                                  │
│   [bar chart placeholder]                                       │
└─────────────────────────────────────────────────────────────────┘
```

### 3.8 Chronic Failure Monitor (`/imm-12/chronic`) — ⚠️ Mockup only

```text
┌─────────────────────────────────────────────────────────────────┐
│  CHRONIC FAILURES (90 ngày qua)                                 │
│  ─────────────────────────────────────────────────────────────  │
│  Asset             Fault Code        Count  RCA       Due       │
│  ─────────────────────────────────────────────────────────────  │
│  Siêu âm GE Vivid  PROBE_DISCONNECT   3   RCA-0007   01/05    │
│  Monitor Phillips  BATTERY_LOW         3   RCA-0008   02/05    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Pinia Store — `useImm12Store` (đề xuất, ⚠️ Pending)

```typescript
// src/stores/imm12.ts (⚠️ Pending implementation)
import { defineStore } from "pinia";
import { ref, computed } from "vue";

export const useImm12Store = defineStore("imm12", () => {
  // ─── State ───────────────────────────────────────────
  const incidents = ref<IncidentReport[]>([]);
  const activeIncident = ref<IncidentReport | null>(null);
  const capaList = ref<CAPARecord[]>([]);
  const activeCAPA = ref<CAPARecord | null>(null);
  const rcaList = ref<RCARecord[]>([]);
  const activeRCA = ref<RCARecord | null>(null);
  const chronicFailures = ref<ChronicFailure[]>([]);
  const dashboard = ref<DashboardKPI | null>(null);

  const loading = ref(false);
  const error = ref<string | null>(null);

  // ─── Computed ────────────────────────────────────────
  const openIncidents = computed(() =>
    incidents.value.filter((ir) => !["Closed","Cancelled"].includes(ir.status))
  );
  const criticalIncidents = computed(() =>
    openIncidents.value.filter((ir) => ir.severity === "Critical")
  );
  const overdueCAPAs = computed(() =>
    capaList.value.filter((c) => c.status === "Overdue")
  );

  // ─── Actions ─────────────────────────────────────────
  async function reportIncident(payload: NewIncidentPayload): Promise<string> {
    return await callApi(
      "assetcore.api.imm12.report_incident", "POST", payload
    );
  }
  async function acknowledgeIncident(name: string, assignedTo: string) { ... }
  async function resolveIncident(name: string, notes: string) { ... }
  async function closeIncident(name: string) { ... }

  // CAPA — calls IMM-00 endpoints (LIVE)
  async function createCAPA(payload: CreateCAPAPayload): Promise<string> {
    return await callApi(
      "assetcore.api.imm00.create_capa", "POST", payload
    );
  }
  async function closeCAPA(payload: CloseCAPAPayload): Promise<void> {
    await callApi("assetcore.api.imm00.close_capa", "POST", payload);
  }

  // RCA
  async function submitRCA(payload: SubmitRCAPayload): Promise<string> {
    return await callApi(
      "assetcore.api.imm12.submit_rca", "POST", payload
    );
  }

  return {
    incidents, activeIncident, capaList, activeCAPA,
    rcaList, activeRCA, chronicFailures, dashboard,
    loading, error,
    openIncidents, criticalIncidents, overdueCAPAs,
    reportIncident, acknowledgeIncident, resolveIncident,
    closeIncident, createCAPA, closeCAPA, submitRCA,
  };
});
```

---

## 5. Design System

Áp dụng đầy đủ design tokens IMM-00 (xem `IMM-00_UI_UX_Guide.md` §2). Bổ sung tokens IMM-12:

### 5.1 Severity color tokens

| Severity | Background | Border / Text | Icon |
|---|---|---|---|
| Minor | `#fefce8` (yellow-50) | `#ca8a04` (yellow-600) | ⓘ |
| Major | `#fff7ed` (orange-50) | `#ea580c` (orange-600) | ⚠️ |
| Critical | `#fef2f2` (red-50) | `#dc2626` (red-600) | 🔴 |

### 5.2 Status badge tokens

| Status | Color | Icon |
|---|---|---|
| Open | gray | ◯ |
| Acknowledged | blue | ◐ |
| In Progress | orange | ◑ |
| Resolved | green | ◕ |
| Closed | dark gray | ● |
| Cancelled | red strikethrough | ✕ |
| RCA Required | purple | 🔍 |

### 5.3 CAPA status

| Status | Color |
|---|---|
| Open | gray |
| In Progress | blue |
| Pending Verification | orange |
| Closed | green |
| Overdue | red (pulsing) |

---

## 6. Role-based UI

| Role | Visible Actions |
|---|---|
| Reporting User | Create Incident · View own dept incidents |
| Workshop Lead | Acknowledge · Assign KTV · Resolve · Create RCA · Submit RCA |
| QA Officer | Submit/Close CAPA · View Audit Trail · View Dashboard · Verify chain |
| Department Head | View incidents · View Dashboard · Receive escalation alerts |
| Ops Manager | Read-only all · Export reports · View Dashboard |
| System Admin | All actions + manual scheduler trigger |

UI implementation note: dùng `v-if="hasRole('IMM QA Officer')"` (Pinia user store) để show/hide action buttons.

---

## 7. States & Feedback

| State | Visualization |
|---|---|
| Loading | Skeleton placeholder (full table skeleton, không spinner) |
| Empty | Illustration + CTA "Báo cáo sự cố đầu tiên" |
| Error (network) | Toast đỏ + retry button |
| Error (validation) | Inline field error + scroll to first error |
| Success (create) | Toast xanh + redirect đến detail view |
| Success (close CAPA) | Modal confirmation "CAPA đã đóng — audit logged" |
| Critical alert | Banner đỏ pulsing trên top app shell |

---

## 8. Tech Stack FE

(reuse từ IMM-00 §10)

- Vue 3 Composition API + TypeScript strict
- Pinia (store)
- Vue Router 4
- Tailwind CSS + AssetCore design tokens
- Axios (qua wrapper `utils/api.ts`)
- Vitest (unit) · Playwright (E2E)

---

## 9. Accessibility

- Color contrast WCAG AA (severity badges có icon đi kèm — không chỉ dùng màu)
- Keyboard navigation cho mọi action
- Screen reader labels: `aria-label="Báo cáo sự cố mới"`
- Focus trap cho modals (CAPA Close, Cancel Confirm)

---

## 10. Liên quan tài liệu khác

- `IMM-00_UI_UX_Guide.md` — design system, app shell, navigation
- `IMM-12_Functional_Specs.md` — User Stories, Validation Rules
- `IMM-12_API_Interface.md` — endpoints để FE call
- `IMM-12_UAT_Script.md` — UAT test cases (FE flow)

---

## 11. Trạng thái implementation

| Hạng mục | Trạng thái |
|---|---|
| Vue components (8 views + 8 components) | ⚠️ Mockup only |
| Pinia store `useImm12Store` | ⚠️ Pending |
| Route + guard | ⚠️ Pending |
| Design tokens (severity, status) | ⚠️ Pending — chờ approve UX team |
| E2E Playwright tests | ⚠️ Pending |
