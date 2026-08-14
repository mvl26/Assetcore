// TDD render-test (FE, transport-agnostic) — BR-09-10 / INV-CM-HOLD.
//
// Đồng hồ SLA/MTTR DỪNG khi WO nằm 'Pending Parts' (chờ phụ tùng hết kho —
// blocker cung ứng ngoài tầm đội sửa). BE là SoT: `repair_elapsed_hours =
// (until − open) − parts_hold_hours`; `mttr_hours` BE gửi đã = elapsed-trừ-hold.
//
// FE chỉ trình bày — KHÔNG tự tính lại. Test này PIN 3 nửa contract FE:
//
//  (A) Detail view ở status 'Pending Parts' → render badge VI
//      'Chờ phụ tùng — cam kết dịch vụ tạm dừng' với role=alert + aria-live (giải thích đồng
//      hồ đang dừng), KHÔNG hiện live-timer/progress chạy gây hiểu nhầm trễ SLA.
//      RED-prove: gỡ nhánh `isOnPartsHold` ⇒ badge biến mất ⇒ test FAIL.
//
//  (B) MTTR render VERBATIM giá trị BE gửi ∀ {40, 80} — FE không nhân/chia/đổi.
//      (40 = elapsed-trừ-hold đúng; 80 = wall-clock cũ — FE render bất kỳ số BE
//      gửi y nguyên, transport-agnostic.)
//
//  (C) No-leak-EN: badge/giao diện CM ở Pending Parts KHÔNG lộ chuỗi tiếng Anh
//      ('Pending Parts', 'SLA paused', 'parts hold'…) hay raw status code.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { setActivePinia, createPinia } from 'pinia'

// ─── Mock router (detail view dùng useRouter().push) ──────────────────────────
// ROOT-CAUSE test-isolation fix: dùng shared full-shape factory (useRoute query
// LIVE từ globalThis, KHÔNG static {} → khi mock này "thắng" registry-race và leak
// sang file list (CMWorkOrderListView đọc route.query) thì query vẫn đúng theo
// test set, hết "route.query undefined / query rỗng" cross-file). Xem
// src/test/vueRouterMock.ts.
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

// ─── Mock notify (không liên quan render badge, chỉ để view mount sạch) ───────
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn(), fromOk: vi.fn(), confirm: vi.fn() }),
}))

// ─── Mock store imm09: currentWO mutable theo từng test ───────────────────────
type WO = Record<string, unknown>
const currentWO = ref<WO | null>(null)
const fetchWorkOrder = vi.fn().mockResolvedValue(undefined)

vi.mock('@/stores/imm09', () => ({
  useImm09Store: () => ({
    get currentWO() { return currentWO.value },
    loading: false,
    error: null,
    lastApiError: null,
    fetchWorkOrder,
    doAssignTechnician: vi.fn().mockResolvedValue(true),
    doConfirmInspection: vi.fn().mockResolvedValue(true),
    doCloseWorkOrder: vi.fn().mockResolvedValue(true),
  }),
}))

import CMWorkOrderDetailView from '@/views/cm/CMWorkOrderDetailView.vue'

// Base WO factory — chỉ field cần để view render; override theo test.
function makeWO(over: WO = {}): WO {
  return {
    name: 'WO-RP-2026-00099',
    asset_ref: 'AC-ASSET-0099',
    asset_name: 'Máy thở Hold',
    asset_category: 'Ventilator',
    risk_class: 'High',
    serial_no: 'SN-HOLD-1',
    repair_type: 'Corrective',
    priority: 'Urgent',
    status: 'Pending Parts',
    open_datetime: '2026-06-01 08:00:00',
    assigned_datetime: '2026-06-01 09:00:00',
    completion_datetime: null,
    assigned_to: 'ktv@hospital.vn',
    assigned_to_name: 'KTV A',
    mttr_hours: null,
    sla_target_hours: 72,
    sla_breached: false,
    is_repeat_failure: false,
    incident_report: null,
    source_pm_wo: null,
    diagnosis_notes: '',
    root_cause_category: '',
    repair_summary: '',
    firmware_updated: false,
    firmware_change_request: null,
    dept_head_name: '',
    total_parts_cost: 0,
    spare_parts_used: [],
    repair_checklist: [],
    ...over,
  }
}

async function mountDetail() {
  const w = mount(CMWorkOrderDetailView, {
    props: { id: 'WO-RP-2026-00099' },
    global: {
      stubs: { RouterLink: true, Transition: false },
      mocks: { $t: (k: string) => k },
    },
  })
  await flushPromises()
  return w
}

describe('IMM-09 BR-09-10 — badge "Chờ phụ tùng — cam kết dịch vụ tạm dừng" (detail view)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    fetchWorkOrder.mockClear()
    currentWO.value = null
  })

  it('(A) status Pending Parts → render badge VI + role=alert + aria-live', async () => {
    currentWO.value = makeWO({ status: 'Pending Parts' })
    const w = await mountDetail()
    const banner = w.find('[data-testid="parts-hold-banner"]')
    expect(banner.exists()).toBe(true)
    expect(banner.text()).toContain('Chờ phụ tùng — cam kết dịch vụ tạm dừng')
    // a11y: thông báo trạng thái cho screen-reader.
    expect(banner.attributes('role')).toBe('alert')
    expect(banner.attributes('aria-live')).toBe('polite')
  })

  it('(A) status Pending Parts → KHÔNG hiện live-timer/progress chạy (tránh hiểu nhầm trễ)', async () => {
    currentWO.value = makeWO({ status: 'Pending Parts' })
    const w = await mountDetail()
    // Nhánh live-timer ('Đã trôi: …') chỉ render cho active != hold.
    expect(w.text()).not.toContain('Đã trôi:')
  })

  it('(A) status In Repair (không hold) → KHÔNG render badge hold; CÓ live-timer', async () => {
    currentWO.value = makeWO({ status: 'In Repair' })
    const w = await mountDetail()
    expect(w.find('[data-testid="parts-hold-banner"]').exists()).toBe(false)
    expect(w.text()).toContain('Đã trôi:')
  })
})

describe('IMM-09 BR-09-10 — MTTR render VERBATIM (transport-agnostic) ∀ {40, 80}', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    fetchWorkOrder.mockClear()
    currentWO.value = null
  })

  // WO đã đóng (Completed): card SLA hiện mttr_hours BE gửi y nguyên.
  // 40 = elapsed-trừ-hold (đúng theo BR-09-10); 80 = wall-clock cũ.
  // FE render BẤT KỲ số nào BE gửi — không tự tính lại.
  for (const mttr of [40, 80]) {
    it(`(B) Completed mttr_hours=${mttr} → hiển thị "${mttr}h" verbatim`, async () => {
      currentWO.value = makeWO({
        status: 'Completed',
        completion_datetime: '2026-06-04 12:00:00',
        mttr_hours: mttr,
        sla_target_hours: 72,
        sla_breached: mttr > 72,
        // parts_hold_hours optional read-only — FE KHÔNG dùng để tính, chỉ chứng minh
        // type chấp nhận field (forward-compat). 40 ⇒ hold=40 (80−40); 80 ⇒ hold=0.
        parts_hold_hours: 80 - mttr,
        parts_hold_started: null,
      })
      const w = await mountDetail()
      expect(w.text()).toContain(`${mttr}h`)
    })
  }

  it('(B) FE KHÔNG suy ra mttr từ wall-clock: mttr=40 dù open→completion cách 80h', async () => {
    // open 08:00 04/06 → completion 16:00 07/06 ≈ 80h wall-clock. BE gửi mttr=40
    // (đã trừ 40h hold). FE render 40h — KHÔNG render 80h (nếu FE tự tính sẽ ra 80).
    currentWO.value = makeWO({
      status: 'Completed',
      open_datetime: '2026-06-04 08:00:00',
      completion_datetime: '2026-06-07 16:00:00',
      mttr_hours: 40,
      sla_target_hours: 72,
      sla_breached: false,
      parts_hold_hours: 40,
    })
    const w = await mountDetail()
    expect(w.text()).toContain('40h')
    // Không được lộ con số wall-clock 80h ở card SLA (FE không tự tính).
    expect(w.text()).not.toContain('80h')
  })
})

describe('IMM-09 BR-09-10 — no-leak-EN (Pending Parts không lộ tiếng Anh/raw code)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    fetchWorkOrder.mockClear()
    currentWO.value = null
  })

  it('(C) status Pending Parts → KHÔNG lộ chuỗi EN/raw status trong UI', async () => {
    currentWO.value = makeWO({ status: 'Pending Parts' })
    const w = await mountDetail()
    const text = w.text()
    // Status đã dịch sang VI ('Chờ vật tư' qua cmStatusLabel) → raw 'Pending Parts'
    // (giữ nguyên 2 từ) KHÔNG được lọt ra UI.
    expect(text).not.toMatch(/\bPending Parts\b/)
    // Không leak biến thể EN của tính năng clock-stop.
    expect(text).not.toMatch(/SLA paused/i)
    expect(text).not.toMatch(/parts hold/i)
    expect(text).not.toMatch(/clock[- ]?stop/i)
    // Badge VI phải có mặt (đối chứng tích cực).
    expect(text).toContain('Chờ phụ tùng — cam kết dịch vụ tạm dừng')
  })
})
