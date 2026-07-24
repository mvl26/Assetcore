// TDD (FE regression guard) — CR-37 · BR-09-07 LIVE, INV parity list↔detail:
// badge "Cam kết dịch vụ vi phạm" ở CMWorkOrderDetailView đọc cờ SERVER LIVE
// `is_sla_breached ?? sla_breached` (do get_work_order enrich, CÙNG predicate
// _enrich_sla_breach của list), KHÔNG chỉ cờ STORED `sla_breached`.
//
// PHÂN KỲ LIVE vs STORED (cửa-sổ-trễ-scheduler): Asset Repair open, elapsed đã vượt
// sla_target_hours nhưng scheduler chưa stamp sla_breached=0. BE derive
// is_sla_breached=true LIVE. Badge PHẢI hiện — nếu FE đọc chỉ STORED sla_breached thì
// badge ẩn (trễ 1 nhịp scheduler = cận an-toàn người bệnh). Đối xứng list CM
// (cmSlaBreachedDivergence case (C)).
//
// RED-prove: revert binding badge về chỉ `wo?.sla_breached` ⇒ case (1) FAIL
// (badge ẩn dù is_sla_breached=true & cờ thô=0).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn(), fromOk: vi.fn(), confirm: vi.fn() }),
}))
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))

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

import CMWorkOrderDetailView from './CMWorkOrderDetailView.vue'

const BADGE = '[data-testid="cm-sla-breach-badge"]'

function makeWO(over: WO = {}): WO {
  return {
    name: 'WO-RP-2026-01001', asset_ref: 'AC-ASSET-1001', asset_name: 'Máy thở Live-Overdue',
    asset_category: 'Ventilator', risk_class: 'High', serial_no: 'SN-LIVE-1',
    repair_type: 'Corrective', priority: 'Urgent', status: 'In Repair',
    allowed_transitions: ['Pending Inspection', 'Cannot Repair', 'Cancelled'],
    open_datetime: '2026-05-01 08:00:00', assigned_datetime: '2026-05-01 09:00:00',
    completion_datetime: null, assigned_to: 'ktv@hospital.vn', assigned_to_name: 'KTV A',
    mttr_hours: null, sla_target_hours: 72, sla_breached: false, is_repeat_failure: false,
    incident_report: null, source_pm_wo: null, diagnosis_notes: '', root_cause_category: '',
    repair_summary: '', firmware_updated: false, firmware_change_request: null,
    dept_head_name: '', total_parts_cost: 0, spare_parts_used: [], repair_checklist: [],
    asset_info: { lifecycle_status: 'Under Repair' },
    ...over,
  }
}

async function mountDetail() {
  const w = mount(CMWorkOrderDetailView, {
    props: { id: 'WO-RP-2026-01001' },
    global: { stubs: { RouterLink: true, Transition: false }, mocks: { $t: (k: string) => k } },
  })
  await flushPromises()
  return w
}

beforeEach(() => {
  setActivePinia(createPinia())
  fetchWorkOrder.mockClear()
  currentWO.value = null
})

describe('CM detail — badge "Cam kết dịch vụ vi phạm" theo cờ LIVE is_sla_breached (CR-37)', () => {
  it('(1) is_sla_breached=true NHƯNG sla_breached=0 (open-overdue) → badge RENDER (LIVE ≠ STORED)', async () => {
    currentWO.value = makeWO({ status: 'In Repair', sla_breached: false, is_sla_breached: true })
    const w = await mountDetail()
    // RED-prove: nếu binding còn chỉ `wo?.sla_breached` → badge ẩn ⇒ FAIL.
    expect(w.find(BADGE).exists()).toBe(true)
    expect(w.text()).toContain('Cam kết dịch vụ vi phạm')
  })

  it('(2) is_sla_breached=false, sla_breached=0 (open in-hạn) → badge ẩn (no phantom)', async () => {
    currentWO.value = makeWO({ status: 'Open', sla_breached: false, is_sla_breached: false })
    const w = await mountDetail()
    expect(w.find(BADGE).exists()).toBe(false)
  })

  it('(3) fallback forward-compat: is_sla_breached undefined + sla_breached=1 → badge RENDER', async () => {
    currentWO.value = makeWO({ status: 'Completed', sla_breached: true, mttr_hours: 96 })
    delete (currentWO.value as WO).is_sla_breached
    const w = await mountDetail()
    expect(w.find(BADGE).exists()).toBe(true)
  })

  it('(4) fallback: is_sla_breached undefined + sla_breached=0 → badge ẩn', async () => {
    currentWO.value = makeWO({ status: 'In Repair', sla_breached: false })
    delete (currentWO.value as WO).is_sla_breached
    const w = await mountDetail()
    expect(w.find(BADGE).exists()).toBe(false)
  })

  it('(5) SLA indicator (WO đã đóng) đọc LIVE: is_sla_breached=true → "✗ Vi phạm cam kết dịch vụ"', async () => {
    currentWO.value = makeWO({ status: 'Completed', sla_breached: true, is_sla_breached: true, mttr_hours: 96, completion_datetime: '2026-05-10 08:00:00' })
    const w = await mountDetail()
    expect(w.text()).toContain('✗ Vi phạm cam kết dịch vụ')
    expect(w.text()).not.toContain('✓ Đạt cam kết dịch vụ')
  })
})
