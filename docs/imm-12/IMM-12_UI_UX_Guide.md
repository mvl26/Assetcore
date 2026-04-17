# IMM-12 — UI/UX Guide
## Frontend Design, Component Architecture & Client Logic

**Module:** IMM-12
**Version:** 1.0
**Ngày:** 2026-04-17
**Trạng thái:** Draft

---

## 1. Sitemap / Routes

```
/imm-12/                              → SLA Dashboard (default landing)
  ├── /imm-12/incidents               → Incident List (filterable, sortable)
  │     └── /imm-12/incidents/:id     → Incident Detail / Edit Form
  ├── /imm-12/incidents/new           → New Incident Report Form
  ├── /imm-12/rca                     → RCA Record List
  │     └── /imm-12/rca/:id           → RCA Record Detail / Edit Form
  ├── /imm-12/dashboard               → SLA Compliance Dashboard (PTP view)
  └── /imm-12/chronic                 → Chronic Failure Monitor
```

**Route Guard:**
- `/imm-12/dashboard` → requires role `PTP Khối 2` hoặc `Workshop Manager`
- `/imm-12/incidents/new` → requires role `Reporting User` hoặc `Workshop Manager`
- `/imm-12/rca/:id` (edit) → requires role `KTV HTM` hoặc `Workshop Manager`

---

## 2. Component Architecture

```
src/
├── views/imm12/
│   ├── IncidentListView.vue          # Danh sách IR với SLA countdown
│   ├── IncidentFormView.vue          # Form tạo/xem/edit IR
│   ├── SLADashboardView.vue          # Dashboard KPI cho PTP
│   ├── RCAListView.vue               # Danh sách RCA Records
│   ├── RCAFormView.vue               # Form phân tích RCA
│   └── ChronicFailureView.vue        # Monitor chronic failures
│
├── components/imm12/
│   ├── SLACountdownTimer.vue         # Countdown timer với màu động
│   ├── SLAStatusBadge.vue            # Badge On Track / At Risk / Breached
│   ├── PrioritySelector.vue          # P1→P4 selector với màu
│   ├── EscalationBanner.vue          # Banner cảnh báo leo thang
│   ├── IncidentCard.vue              # Card trong list view
│   ├── RCAForm5Why.vue               # 5-Why analysis sub-form
│   ├── ChronicAlertBadge.vue         # Badge "Chronic" trên asset/IR
│   └── SLABreachModal.vue            # Modal khi breach xảy ra realtime
│
└── stores/
    └── imm12.ts                      # Pinia store (xem Section 4)
```

---

## 3. Form Specs

### 3.1 New Incident Report Form (`/imm-12/incidents/new`)

**Header:**
```
┌─────────────────────────────────────────────────────────────────┐
│  BÁO CÁO SỰ CỐ THIẾT BỊ                            [Hủy] [Gửi]│
│  Sự cố sẽ được tiếp nhận và xử lý ngay lập tức                 │
└─────────────────────────────────────────────────────────────────┘
```

**Section 1: Thông tin thiết bị**
```
┌─────────────────────────────────────────────────────────────────┐
│  Thiết bị *          [Search / Dropdown: ACC-ASS-...]           │
│  ─────────────────────────────────────────────────────────────  │
│  Tên thiết bị:       [Auto-filled: Máy thở Drager Evita 800]    │
│  Khoa phòng:         [Auto-filled: ICU – Hồi sức tích cực]      │
│  Vị trí:             [Auto-filled: Phòng 302, Tầng 3]           │
└─────────────────────────────────────────────────────────────────┘
```

**Section 2: Mô tả sự cố**
```
┌─────────────────────────────────────────────────────────────────┐
│  Mã lỗi *            [Select: Fault Code dropdown]              │
│  Triệu chứng *       [Textarea: Mô tả chi tiết những gì bạn     │
│                       thấy / nghe / thiết bị báo...]            │
│  Thiết bị đang       ○ Hoàn toàn không hoạt động               │
│  ở trạng thái *      ○ Hoạt động một phần (có lỗi)             │
│                       ○ Báo alarm nhưng vẫn chạy               │
│  Workaround?         □ Đã chuyển bệnh nhân sang thiết bị khác   │
│  Ảnh đính kèm        [Upload button — drag & drop]              │
└─────────────────────────────────────────────────────────────────┘
```

**Section 3: Tác động lâm sàng (hiển thị nếu thiết bị class III hoặc life-support)**
```
┌─────────────────────────────────────────────────────────────────┐
│  ⚠️  THIẾT BỊ HỖ TRỢ SỰ SỐNG — BẮT BUỘC ĐIỀN                 │
│  Tác động lâm sàng * [Textarea: Hiện có bệnh nhân nào đang     │
│                        phụ thuộc vào thiết bị này không?        │
│                        Biện pháp bảo vệ bệnh nhân đã áp dụng?] │
└─────────────────────────────────────────────────────────────────┘
```

**Footer:**
```
[HỦY]                                    [GỬI BÁO CÁO →]
```

---

### 3.2 Incident Detail / Edit Form (`/imm-12/incidents/:id`)

**Header — IR Identifier & SLA Status**
```
┌─────────────────────────────────────────────────────────────────┐
│  IR-2026-00042                    ● IN PROGRESS        [Actions▼]│
│  Máy thở Drager Evita 800 — ICU                                 │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  🔴 P1 CRITICAL    SLA: RESOLUTION                       │    │
│  │  ████████████████░░░░░░░░░  [2h 15m còn lại]            │    │
│  │  Hạn: 16:00 hôm nay — 24/7 SLA                         │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

**Tabs: [Thông tin] [SLA Timeline] [Sửa chữa] [RCA] [Lịch sử]**

**Tab: Thông tin**
```
┌─────────────────────────────────────────────────────────────────┐
│  Thiết bị:      ACC-ASS-2026-00012 — Máy thở Drager Evita 800   │
│  Mã lỗi:        VENT_ALARM_HIGH                                  │
│  Mô tả:         Máy báo alarm liên tục, áp suất đường thở...    │
│  Báo cáo bởi:   nurse1@hospital.vn — 08:12 17/04/2026           │
│  Tiếp nhận bởi: manager@hospital.vn — 08:35 17/04/2026          │
│  ─────────────────────────────────────────────────────────────  │
│  Ưu tiên:       [P1 Critical ▼]  (chỉ Manager mới đổi được)    │
│  KTV phụ trách: [ktv1@hospital.vn ▼]                            │
│  Work Order:    [AR-2026-00089 — In Progress]  [→ Xem WO]       │
└─────────────────────────────────────────────────────────────────┘
```

**Tab: SLA Timeline**
```
┌─────────────────────────────────────────────────────────────────┐
│  Timeline SLA                                                    │
│                                                                  │
│  08:12  ●  IR Created           [SLA Response: 30 phút]         │
│         │                                                        │
│  08:35  ●  Acknowledged (23 phút) ✅ WITHIN SLA                 │
│         │                                                        │
│  ——     ●  [SLA Resolution: 4 giờ = 12:12]                      │
│         │                                                        │
│  Now ►  ●  In Progress — 9h 58m elapsed ⚠️ BREACHED             │
│                                                                  │
│  SLA Breach Log:                                                 │
│  • Resolution breach ghi lúc 12:12 — overage: 5h 46m           │
│    Escalation gửi: BGĐ, PTP Khối 2                             │
└─────────────────────────────────────────────────────────────────┘
```

---

### 3.3 SLA Dashboard (`/imm-12/dashboard`)

```
┌─────────────────────────────────────────────────────────────────┐
│  SLA COMPLIANCE DASHBOARD                    Tháng 04/2026 [▼]  │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │  P1      │ │  P2      │ │  P3      │ │  P4      │           │
│  │  100%    │ │  87.5%   │ │  94.2%   │ │  98.1%   │           │
│  │ 5/5 OK   │ │ 7/8 OK   │ │ 49/52 OK │ │ 52/53 OK │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│                                                                  │
│  MTTA (Mean Time to Acknowledge)        MTTR (Mean Time to Resolve)
│  ┌──────────────────────┐               ┌──────────────────────┐ │
│  │ P1: 18 phút ✅       │               │ P1: 3.2 giờ ✅       │ │
│  │ P2: 1h 42m ✅        │               │ P2: 7.8 giờ ✅       │ │
│  │ P3: 3h 15m ✅        │               │ P3: 19.3 giờ ✅      │ │
│  └──────────────────────┘               └──────────────────────┘ │
│                                                                  │
│  OPEN INCIDENTS (7)                                             │
│  ┌─────┬────────────────────────┬──────────┬─────────────────┐  │
│  │ P1  │ Máy thở ICU P301       │ BREACHED │ 5h 46m over SLA │  │
│  │ P2  │ Siêu âm Tim mạch       │ AT RISK  │ 1h 20m còn lại  │  │
│  │ P3  │ ECG Cấp cứu            │ ON TRACK │ 8h 15m còn lại  │  │
│  └─────┴────────────────────────┴──────────┴─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Pinia Store — `useImm12Store`

```typescript
// src/stores/imm12.ts
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type {
  IncidentReport,
  RCARecord,
  SLADashboard,
  ChronicFailure,
  SLAStatus,
} from "@/types/imm12";

export const useImm12Store = defineStore("imm12", () => {
  // ─── State ───────────────────────────────────────────────────────
  const incidents = ref<IncidentReport[]>([]);
  const activeIncident = ref<IncidentReport | null>(null);
  const rcaList = ref<RCARecord[]>([]);
  const activeRCA = ref<RCARecord | null>(null);
  const dashboard = ref<SLADashboard | null>(null);
  const chronicFailures = ref<ChronicFailure[]>([]);

  const loading = ref(false);
  const error = ref<string | null>(null);

  // SLA countdown timer state — keyed by IR name
  const slaCountdowns = ref<Record<string, number>>({});  // seconds remaining
  let countdownInterval: ReturnType<typeof setInterval> | null = null;

  // ─── Computed ─────────────────────────────────────────────────────
  const openIncidents = computed(() =>
    incidents.value.filter((ir) => !["Closed", "Cancelled"].includes(ir.status))
  );

  const p1Incidents = computed(() =>
    openIncidents.value.filter((ir) => ir.priority === "P1 Critical")
  );

  const breachedIncidents = computed(() =>
    openIncidents.value.filter((ir) => ir.sla_status === "Breached")
  );

  const atRiskIncidents = computed(() =>
    openIncidents.value.filter((ir) => ir.sla_status === "At Risk")
  );

  const hasCriticalAlerts = computed(
    () => p1Incidents.value.length > 0 || breachedIncidents.value.length > 0
  );

  // ─── SLA Helpers ──────────────────────────────────────────────────
  const SLA_LIMITS: Record<string, { response: number; resolution: number }> = {
    "P1 Critical": { response: 0.5 * 3600, resolution: 4 * 3600 },
    "P2 High":     { response: 2 * 3600,   resolution: 8 * 3600 },
    "P3 Medium":   { response: 4 * 3600,   resolution: 24 * 3600 },
    "P4 Low":      { response: 8 * 3600,   resolution: 72 * 3600 },
  };

  function getSLASecondsRemaining(ir: IncidentReport): number {
    const limits = SLA_LIMITS[ir.priority];
    if (!limits) return 0;

    const createdAt = new Date(ir.created_at).getTime();
    const now = Date.now();
    const elapsed = (now - createdAt) / 1000;  // seconds

    // If already resolved: use resolution SLA
    // If not yet acknowledged: use response SLA (tighter)
    const limitKey =
      ir.status === "New" || ir.status === "Acknowledged"
        ? "response"
        : "resolution";

    const limit = ir.status === "Acknowledged"
      ? limits.resolution  // after ack, track resolution
      : limits[limitKey];

    return Math.max(0, limit - elapsed);
  }

  function getSLAColor(ir: IncidentReport): "red" | "orange" | "yellow" | "green" {
    const priority = ir.priority;
    if (ir.sla_status === "Breached") return "red";
    if (ir.sla_status === "At Risk") {
      return priority === "P1 Critical" ? "red" : "orange";
    }
    if (priority === "P1 Critical") return "red";
    if (priority === "P2 High") return "orange";
    if (priority === "P3 Medium") return "yellow";
    return "green";
  }

  function formatCountdown(seconds: number): string {
    if (seconds <= 0) return "BREACHED";
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    if (h > 0) return `${h}h ${m}m còn lại`;
    if (m > 0) return `${m}m ${s}s còn lại`;
    return `${s}s còn lại`;
  }

  // ─── Actions ──────────────────────────────────────────────────────
  async function fetchIncidents(filters: Record<string, unknown> = {}): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      const res = await fetch(
        `/api/method/assetcore.api.imm12.get_incident_list?filters=${JSON.stringify(filters)}`
      );
      const data = await res.json();
      if (data.message?.success) {
        incidents.value = data.message.data;
        _initSLACountdowns();
      } else {
        throw new Error(data.message?.error || "Không thể tải danh sách sự cố");
      }
    } catch (e) {
      error.value = (e as Error).message;
    } finally {
      loading.value = false;
    }
  }

  async function fetchIncident(name: string): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      const res = await fetch(
        `/api/method/assetcore.api.imm12.get_incident?name=${name}`
      );
      const data = await res.json();
      if (data.message?.success) {
        activeIncident.value = data.message.data;
      } else {
        throw new Error(data.message?.error || "Không thể tải sự cố");
      }
    } catch (e) {
      error.value = (e as Error).message;
    } finally {
      loading.value = false;
    }
  }

  async function createIncident(payload: Partial<IncidentReport>): Promise<string> {
    loading.value = true;
    error.value = null;
    try {
      const res = await fetch("/api/method/assetcore.api.imm12.create_incident", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Frappe-CSRF-Token": getCsrfToken() },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.message?.success) {
        await fetchIncidents();
        return data.message.data.name;
      }
      throw new Error(data.message?.error || "Không thể tạo sự cố");
    } catch (e) {
      error.value = (e as Error).message;
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function acknowledgeIncident(name: string, priority: string): Promise<void> {
    loading.value = true;
    try {
      const res = await fetch("/api/method/assetcore.api.imm12.acknowledge_incident", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Frappe-CSRF-Token": getCsrfToken() },
        body: JSON.stringify({ name, priority }),
      });
      const data = await res.json();
      if (!data.message?.success) {
        throw new Error(data.message?.error || "Không thể tiếp nhận sự cố");
      }
      await fetchIncident(name);
    } finally {
      loading.value = false;
    }
  }

  async function resolveIncident(name: string, resolution_notes: string): Promise<void> {
    loading.value = true;
    try {
      const res = await fetch("/api/method/assetcore.api.imm12.resolve_incident", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Frappe-CSRF-Token": getCsrfToken() },
        body: JSON.stringify({ name, resolution_notes }),
      });
      const data = await res.json();
      if (!data.message?.success) {
        throw new Error(data.message?.error || "Không thể đánh dấu đã giải quyết");
      }
      await fetchIncident(name);
    } finally {
      loading.value = false;
    }
  }

  async function fetchSLADashboard(year: number, month: number): Promise<void> {
    loading.value = true;
    try {
      const res = await fetch(
        `/api/method/assetcore.api.imm12.get_sla_dashboard?year=${year}&month=${month}`
      );
      const data = await res.json();
      if (data.message?.success) {
        dashboard.value = data.message.data;
      }
    } finally {
      loading.value = false;
    }
  }

  async function fetchChronicFailures(): Promise<void> {
    loading.value = true;
    try {
      const res = await fetch(
        "/api/method/assetcore.api.imm12.get_chronic_failures"
      );
      const data = await res.json();
      if (data.message?.success) {
        chronicFailures.value = data.message.data;
      }
    } finally {
      loading.value = false;
    }
  }

  // ─── Internal: SLA Countdown Timer ────────────────────────────────
  function _initSLACountdowns(): void {
    if (countdownInterval) clearInterval(countdownInterval);

    _recalcCountdowns();
    countdownInterval = setInterval(_recalcCountdowns, 1000);
  }

  function _recalcCountdowns(): void {
    const openIRs = incidents.value.filter(
      (ir) => !["Closed", "Cancelled", "Resolved"].includes(ir.status)
    );
    for (const ir of openIRs) {
      slaCountdowns.value[ir.name] = getSLASecondsRemaining(ir);
    }
  }

  function stopCountdowns(): void {
    if (countdownInterval) {
      clearInterval(countdownInterval);
      countdownInterval = null;
    }
  }

  // ─── Utility ──────────────────────────────────────────────────────
  function getCsrfToken(): string {
    return (window as Record<string, unknown>).csrf_token as string || "";
  }

  return {
    // State
    incidents,
    activeIncident,
    rcaList,
    activeRCA,
    dashboard,
    chronicFailures,
    loading,
    error,
    slaCountdowns,

    // Computed
    openIncidents,
    p1Incidents,
    breachedIncidents,
    atRiskIncidents,
    hasCriticalAlerts,

    // Helpers
    getSLASecondsRemaining,
    getSLAColor,
    formatCountdown,

    // Actions
    fetchIncidents,
    fetchIncident,
    createIncident,
    acknowledgeIncident,
    resolveIncident,
    fetchSLADashboard,
    fetchChronicFailures,
    stopCountdowns,
  };
});
```

---

## 5. Client Logic

### 5.1 SLA Countdown Timer Component

```vue
<!-- src/components/imm12/SLACountdownTimer.vue -->
<template>
  <div
    class="sla-countdown"
    :class="[`sla-countdown--${colorClass}`, { 'sla-countdown--pulsing': isPulsing }]"
  >
    <div class="sla-countdown__label">
      {{ timerLabel }}
    </div>
    <div class="sla-countdown__time">
      {{ displayTime }}
    </div>
    <div class="sla-countdown__bar">
      <div
        class="sla-countdown__bar-fill"
        :style="{ width: `${progressPercent}%` }"
      />
    </div>
    <div class="sla-countdown__deadline">
      Hạn: {{ deadlineFormatted }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useImm12Store } from "@/stores/imm12";
import type { IncidentReport } from "@/types/imm12";

const props = defineProps<{
  incident: IncidentReport;
}>();

const store = useImm12Store();

const secondsRemaining = computed(
  () => store.slaCountdowns[props.incident.name] ?? 0
);

const colorClass = computed(() => store.getSLAColor(props.incident));

const isPulsing = computed(
  () =>
    props.incident.sla_status === "Breached" ||
    (props.incident.priority === "P1 Critical" &&
      props.incident.sla_status === "At Risk")
);

const displayTime = computed(() => store.formatCountdown(secondsRemaining.value));

const timerLabel = computed(() => {
  if (props.incident.status === "New") return "SLA RESPONSE";
  return "SLA RESOLUTION";
});

const SLA_LIMITS: Record<string, number> = {
  "P1 Critical": 4 * 3600,
  "P2 High": 8 * 3600,
  "P3 Medium": 24 * 3600,
  "P4 Low": 72 * 3600,
};

const totalSLASeconds = computed(
  () => SLA_LIMITS[props.incident.priority] || 24 * 3600
);

const progressPercent = computed(() => {
  const elapsed = totalSLASeconds.value - secondsRemaining.value;
  return Math.min(100, Math.round((elapsed / totalSLASeconds.value) * 100));
});

const deadlineFormatted = computed(() => {
  const createdAt = new Date(props.incident.created_at);
  const deadline = new Date(
    createdAt.getTime() + totalSLASeconds.value * 1000
  );
  return deadline.toLocaleString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "2-digit",
  });
});
</script>

<style scoped>
.sla-countdown {
  padding: 12px 16px;
  border-radius: 8px;
  border: 2px solid currentColor;
}

.sla-countdown--green  { color: #16a34a; background: #f0fdf4; }
.sla-countdown--yellow { color: #ca8a04; background: #fefce8; }
.sla-countdown--orange { color: #ea580c; background: #fff7ed; }
.sla-countdown--red    { color: #dc2626; background: #fef2f2; }

.sla-countdown--pulsing {
  animation: pulse-border 1s ease-in-out infinite;
}

@keyframes pulse-border {
  0%, 100% { border-color: currentColor; }
  50%       { border-color: transparent; }
}

.sla-countdown__time {
  font-size: 1.5rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.sla-countdown__bar {
  height: 6px;
  background: #e5e7eb;
  border-radius: 9999px;
  margin: 8px 0;
  overflow: hidden;
}

.sla-countdown__bar-fill {
  height: 100%;
  background: currentColor;
  border-radius: 9999px;
  transition: width 1s linear;
}
</style>
```

---

### 5.2 Escalation Banner Component

```vue
<!-- src/components/imm12/EscalationBanner.vue -->
<template>
  <Transition name="slide-down">
    <div
      v-if="show"
      class="escalation-banner"
      :class="`escalation-banner--${severity}`"
      role="alert"
      aria-live="assertive"
    >
      <div class="escalation-banner__icon">
        <span v-if="severity === 'critical'">🚨</span>
        <span v-else-if="severity === 'high'">⚠️</span>
        <span v-else>ℹ️</span>
      </div>
      <div class="escalation-banner__content">
        <strong>{{ title }}</strong>
        <p>{{ message }}</p>
        <div v-if="linkedIR" class="escalation-banner__link">
          <router-link :to="`/imm-12/incidents/${linkedIR}`">
            Xem sự cố {{ linkedIR }} →
          </router-link>
        </div>
      </div>
      <button
        class="escalation-banner__dismiss"
        @click="$emit('dismiss')"
        aria-label="Đóng thông báo"
      >
        ✕
      </button>
    </div>
  </Transition>
</template>

<script setup lang="ts">
defineProps<{
  show: boolean;
  severity: "critical" | "high" | "medium";
  title: string;
  message: string;
  linkedIR?: string;
}>();

defineEmits<{
  (e: "dismiss"): void;
}>();
</script>

<style scoped>
.escalation-banner {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px 20px;
  border-radius: 8px;
  border-left: 4px solid;
  margin-bottom: 16px;
}

.escalation-banner--critical {
  background: #fef2f2;
  border-color: #dc2626;
  color: #991b1b;
}

.escalation-banner--high {
  background: #fff7ed;
  border-color: #ea580c;
  color: #9a3412;
}

.escalation-banner--medium {
  background: #fefce8;
  border-color: #ca8a04;
  color: #854d0e;
}

.escalation-banner__dismiss {
  margin-left: auto;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  color: currentColor;
  opacity: 0.6;
}

.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.3s ease;
}
.slide-down-enter-from,
.slide-down-leave-to {
  transform: translateY(-20px);
  opacity: 0;
}
</style>
```

---

### 5.3 Priority Color Coding System

```typescript
// src/utils/imm12.ts

export const PRIORITY_CONFIG = {
  "P1 Critical": {
    color: "red",
    bgClass: "bg-red-50",
    borderClass: "border-red-500",
    textClass: "text-red-700",
    badgeClass: "badge-red",
    label: "P1 — Khẩn cấp",
    icon: "🔴",
  },
  "P2 High": {
    color: "orange",
    bgClass: "bg-orange-50",
    borderClass: "border-orange-500",
    textClass: "text-orange-700",
    badgeClass: "badge-orange",
    label: "P2 — Cao",
    icon: "🟠",
  },
  "P3 Medium": {
    color: "yellow",
    bgClass: "bg-yellow-50",
    borderClass: "border-yellow-500",
    textClass: "text-yellow-700",
    badgeClass: "badge-yellow",
    label: "P3 — Trung bình",
    icon: "🟡",
  },
  "P4 Low": {
    color: "green",
    bgClass: "bg-green-50",
    borderClass: "border-green-500",
    textClass: "text-green-700",
    badgeClass: "badge-green",
    label: "P4 — Thấp",
    icon: "🟢",
  },
} as const;

export const SLA_STATUS_CONFIG = {
  "On Track": { class: "status-green", label: "Đúng hạn" },
  "At Risk":  { class: "status-orange", label: "Nguy cơ vi phạm" },
  "Breached": { class: "status-red",    label: "VI PHẠM SLA" },
} as const;
```

---

### 5.4 Real-time Escalation Modal (P1 Breach)

```typescript
// src/composables/useEscalationAlert.ts
import { ref, onMounted, onUnmounted } from "vue";
import { useImm12Store } from "@/stores/imm12";

export function useEscalationAlert() {
  const store = useImm12Store();
  const showModal = ref(false);
  const alertedIRs = ref<Set<string>>(new Set());
  let pollInterval: ReturnType<typeof setInterval> | null = null;

  function checkForNewBreaches(): void {
    const breached = store.breachedIncidents;
    for (const ir of breached) {
      if (!alertedIRs.value.has(ir.name)) {
        alertedIRs.value.add(ir.name);
        if (ir.priority === "P1 Critical") {
          triggerP1Modal(ir);
        }
      }
    }
  }

  function triggerP1Modal(ir: typeof store.breachedIncidents[0]): void {
    // Show blocking modal for P1 breach — cannot dismiss without action
    showModal.value = true;
    // Play alert sound
    const audio = new Audio("/assets/assetcore/sounds/alert-critical.mp3");
    audio.play().catch(() => {});
  }

  onMounted(() => {
    pollInterval = setInterval(checkForNewBreaches, 30_000); // every 30s
  });

  onUnmounted(() => {
    if (pollInterval) clearInterval(pollInterval);
  });

  return { showModal };
}
```
