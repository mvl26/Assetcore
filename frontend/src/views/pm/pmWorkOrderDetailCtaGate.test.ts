// TDD (FE regression guard) — GATE-8 / LL-FE-51: server-driven CTA cho PM WO.
//
// Mọi nút chuyển-trạng-thái ở PMWorkOrderDetailView gate theo `allowed_transitions`
// do BE emit (SSoT = _PM_VALID_TRANSITIONS trong services/imm08.py) — KHÔNG hardcode
// `wo.status === 'X'`. FE = (capability && allowedTransitions.includes(target)).
//
// Chuỗi trạng-thái-đích khớp EXACT PMStatus (en-dash: 'Halted–Major Failure',
// 'Pending–Device Busy') — verified qua bench console imm08.py.
//
// SSoT map (_PM_VALID_TRANSITIONS):
//   Open                 → [In Progress, Overdue, Cancelled]
//   Overdue              → [In Progress, Cancelled]
//   In Progress          → [Completed, Halted–Major Failure, Pending–Device Busy, Cancelled]
//   Pending–Device Busy  → [In Progress, Cancelled]
//   Halted–Major Failure → [In Progress, Cancelled]
//   Completed / Cancelled → []  (terminal → 0 CTA)
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn(), fromOk: vi.fn(), confirm: vi.fn() }),
}))
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn() }),
}))

// Capability controllable per test (mặc định: đủ mọi quyền pm).
let canImpl: (c: string) => boolean = () => true
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: (c: string) => canImpl(c) }),
}))

type WO = Record<string, unknown>
const currentWO = ref<WO | null>(null)
const hasMajorFailure = ref(false)
const fetchWorkOrder = vi.fn().mockResolvedValue(undefined)
vi.mock('@/stores/imm08', () => ({
  useImm08Store: () => ({
    get currentWO() { return currentWO.value },
    loading: false,
    error: null,
    lastApiError: null,
    get ratedCount() { return 0 },
    get checklistComplete() { return true },
    get hasMajorFailure() { return hasMajorFailure.value },
    get hasMinorFailure() { return false },
    fetchWorkOrder,
    updateChecklistResult: vi.fn(),
    doSubmitResult: vi.fn().mockResolvedValue({ success: true }),
    doReportMajorFailure: vi.fn().mockResolvedValue('WO-RP-1'),
    doReschedule: vi.fn().mockResolvedValue(true),
    doAssignTechnician: vi.fn().mockResolvedValue(true),
  }),
}))

import PMWorkOrderDetailView from './PMWorkOrderDetailView.vue'

// Mirror EXACT của _PM_VALID_TRANSITIONS (imm08.py) — en-dash preserved.
const PM_TRANSITIONS: Record<string, string[]> = {
  'Open': ['In Progress', 'Overdue', 'Cancelled'],
  'Overdue': ['In Progress', 'Cancelled'],
  'In Progress': ['Completed', 'Halted–Major Failure', 'Pending–Device Busy', 'Cancelled'],
  'Pending–Device Busy': ['In Progress', 'Cancelled'],
  'Halted–Major Failure': ['In Progress', 'Cancelled'],
  'Completed': [],
  'Cancelled': [],
}

const ALL_CTA = ['cta-start', 'cta-major', 'cta-complete']

function makeWO(over: WO = {}): WO {
  const status = (over.status as string) ?? 'Open'
  return {
    name: 'WO-PM-2026-00042',
    asset_ref: 'AC-ASSET-0042',
    asset_name: 'Máy siêu âm',
    risk_class: 'Medium',
    status,
    pm_type: 'Preventive',
    wo_type: 'PM',
    due_date: '2026-06-30',
    is_late: false,
    assigned_to: 'ktv@hospital.vn',
    assigned_to_name: 'KTV A',
    supervisor: '',
    checklist_results: [],
    overall_result: null,
    completion_date: null,
    allowed_transitions: PM_TRANSITIONS[status] ?? [],
    ...over,
  }
}

async function mountDetail() {
  const w = mount(PMWorkOrderDetailView, {
    props: { id: 'WO-PM-2026-00042' },
    global: {
      stubs: { RouterLink: true, Transition: false, DateInput: true },
      mocks: { $t: (k: string) => k },
    },
  })
  await flushPromises()
  return w
}

function ctasShown(w: Awaited<ReturnType<typeof mountDetail>>): string[] {
  return ALL_CTA.filter((id) => w.find(`[data-testid="${id}"]`).exists())
}

beforeEach(() => {
  setActivePinia(createPinia())
  fetchWorkOrder.mockClear()
  currentWO.value = null
  hasMajorFailure.value = false
  canImpl = () => true
})

describe('PM CTA gate — "Bắt đầu bảo trì" (→ In Progress) theo allowed_transitions', () => {
  it('Open + assigned_to + allowed gồm "In Progress" → cta-start render', async () => {
    currentWO.value = makeWO({ status: 'Open' })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-start"]').exists()).toBe(true)
  })

  it('Open + assigned_to nhưng allowed BỎ "In Progress" → cta-start ẩn (RED khi hardcode status)', async () => {
    currentWO.value = makeWO({ status: 'Open', allowed_transitions: ['Overdue', 'Cancelled'] })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-start"]').exists()).toBe(false)
  })

  it('Open + CHƯA phân công (assigned_to rỗng) → cta-start ẩn', async () => {
    currentWO.value = makeWO({ status: 'Open', assigned_to: '' })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-start"]').exists()).toBe(false)
  })

  it('Open + THIẾU cap pm.write → cta-start ẩn (gate = cap && includes)', async () => {
    canImpl = (c) => c !== 'pm.write'
    currentWO.value = makeWO({ status: 'Open' })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-start"]').exists()).toBe(false)
  })
})

describe('PM CTA — In Progress: Hoàn thành + Báo lỗi nghiêm trọng', () => {
  it('In Progress + allowed gồm "Completed" → cta-complete render', async () => {
    currentWO.value = makeWO({ status: 'In Progress' })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-complete"]').exists()).toBe(true)
  })

  it('In Progress + allowed gồm "Halted–Major Failure" → cta-major render', async () => {
    currentWO.value = makeWO({ status: 'In Progress' })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-major"]').exists()).toBe(true)
  })

  it('In Progress + allowed BỎ "Halted–Major Failure" → cta-major ẩn (RED khi hardcode)', async () => {
    currentWO.value = makeWO({ status: 'In Progress', allowed_transitions: ['Completed', 'Cancelled'] })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-major"]').exists()).toBe(false)
    // Completed vẫn allowed → cta-complete vẫn render.
    expect(w.find('[data-testid="cta-complete"]').exists()).toBe(true)
  })

  it('In Progress + THIẾU cap pm.write → cta-major ẩn (gate = cap && includes)', async () => {
    canImpl = (c) => c !== 'pm.write'
    currentWO.value = makeWO({ status: 'In Progress' })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-major"]').exists()).toBe(false)
  })

  it('In Progress + đã có lỗi lớn (hasMajorFailure) → cta-complete ẩn', async () => {
    hasMajorFailure.value = true
    currentWO.value = makeWO({ status: 'In Progress' })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-complete"]').exists()).toBe(false)
  })
})

describe('PM CTA — Overdue chỉ cho bắt đầu, không lộ Báo lỗi/Hoàn thành', () => {
  it('Overdue (allowed=[In Progress,Cancelled]) → chỉ cta-start', async () => {
    currentWO.value = makeWO({ status: 'Overdue' })
    const w = await mountDetail()
    expect(ctasShown(w).sort()).toEqual(['cta-start'])
  })
})

describe('PM CTA terminal — allowed=[] → 0 nút CTA', () => {
  it.each(['Completed', 'Cancelled'])('%s → 0 CTA (chỉ nhãn tĩnh)', async (status) => {
    currentWO.value = makeWO({ status })
    const w = await mountDetail()
    expect(ctasShown(w)).toEqual([])
  })
})
