// TDD (FE regression guard) — BR-08-08 empty-checklist: FE mirror của gate BE
// IMM08_CHECKLIST_EMPTY (services/imm08.py::validate_work_order).
//
// `completionBlockReason` (PMWorkOrderDetailView) PHẢI chặn nút "Hoàn thành bảo trì"
// khi bảng kiểm RỖNG (totalCount === 0 → thiếu bảng kiểm mẫu) với hint RIÊNG, khác
// "chưa chấm hết". Đây là defense-in-depth: SSoT vẫn là gate BE (mọi path save
// status=Completed đều qua validate()), FE chỉ chặn sớm + báo đúng nguyên nhân.
//
// RED trước fix line 64 (nếu bỏ guard totalCount===0): nút vẫn disabled do
// checklistComplete=false nhưng hint sai ("chưa chấm hết") → assertion hint thất bại.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn(), fromOk: vi.fn(), confirm: vi.fn() }),
}))
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() }),
}))
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))

type WO = Record<string, unknown>
const currentWO = ref<WO | null>(null)
const checklistComplete = ref(true)
const ratedCount = ref(0)
const fetchWorkOrder = vi.fn().mockResolvedValue(undefined)
vi.mock('@/stores/imm08', () => ({
  useImm08Store: () => ({
    get currentWO() { return currentWO.value },
    loading: false,
    error: null,
    lastApiError: null,
    get ratedCount() { return ratedCount.value },
    get checklistComplete() { return checklistComplete.value },
    hasMajorFailure: false,
    hasMinorFailure: false,
    fetchWorkOrder,
    doSubmitResult: vi.fn().mockResolvedValue({ success: true }),
    doReportMajorFailure: vi.fn().mockResolvedValue('WO-RP-2026-00500'),
    doReschedule: vi.fn().mockResolvedValue(true),
    doAssignTechnician: vi.fn().mockResolvedValue(true),
    updateChecklistResult: vi.fn(),
  }),
}))

import PMWorkOrderDetailView from '@/views/pm/PMWorkOrderDetailView.vue'

const EMPTY_HINT = 'Chưa có mục bảng kiểm'

function makeWO(over: WO = {}): WO {
  return {
    name: 'WO-PM-2026-00099', asset_ref: 'AC-ASSET-0099', asset_name: 'Máy thở Dräger Evita V500',
    asset_category: 'Ventilator', risk_class: 'Medium', pm_type: 'Routine', wo_type: 'Preventive',
    status: 'In Progress', allowed_transitions: ['Completed', 'Halted–Major Failure', 'Pending–Device Busy', 'Cancelled'],
    due_date: '2026-06-01', scheduled_date: '2026-06-01', completion_date: null,
    assigned_to: 'ktv@hospital.vn', assigned_to_name: 'KTV A', supervisor: null, supervisor_name: null,
    overall_result: null, technician_notes: '', pm_sticker_attached: false, is_late: false,
    duration_minutes: null, source_pm_wo: null, checklist_results: [],
    ...over,
  }
}

async function mountDetail() {
  const w = mount(PMWorkOrderDetailView, {
    props: { id: 'WO-PM-2026-00099' },
    global: {
      stubs: { RouterLink: true, Transition: false, DateInput: true },
      mocks: { $t: (k: string) => k },
    },
  })
  await flushPromises()
  return w
}

beforeEach(() => {
  setActivePinia(createPinia())
  fetchWorkOrder.mockClear()
  currentWO.value = null
  checklistComplete.value = true
  ratedCount.value = 0
})

describe('IMM-08 BR-08-08 — FE chặn "Hoàn thành" khi bảng kiểm RỖNG', () => {
  it('checklist_results=[] → nút "Hoàn thành bảo trì" DISABLED + hint "chưa có mục bảng kiểm"', async () => {
    currentWO.value = makeWO({ checklist_results: [] })
    const w = await mountDetail()
    const btn = w.find('[data-testid="cta-complete"]')
    expect(btn.exists()).toBe(true)
    expect(btn.attributes('disabled')).toBeDefined()
    // Hint PHẢI chỉ đúng nguyên nhân (bảng kiểm rỗng), KHÔNG phải "chưa chấm hết".
    expect(w.text()).toContain(EMPTY_HINT)
  })

  it('≥1 item đã rated + duration>0 + sticker=1 → nút "Hoàn thành" ENABLED, KHÔNG còn empty-hint', async () => {
    checklistComplete.value = true
    ratedCount.value = 1
    currentWO.value = makeWO({
      checklist_results: [
        { idx: 1, description: 'Kiểm tra áp lực khí', measurement_type: 'Pass/Fail', result: 'Pass', measured_value: null, notes: '' },
      ],
    })
    const w = await mountDetail()
    await w.find('#sticker').setValue(true)
    await w.find('#duration-min').setValue('45')
    await flushPromises()
    const btn = w.find('[data-testid="cta-complete"]')
    expect(btn.exists()).toBe(true)
    expect(btn.attributes('disabled')).toBeUndefined()
    expect(w.text()).not.toContain(EMPTY_HINT)
  })
})
