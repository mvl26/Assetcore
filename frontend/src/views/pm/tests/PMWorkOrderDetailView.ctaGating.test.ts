// TDD (FE regression guard) — GATE-8 / LL-FE-51: server-driven CTA cho PM WO.
//
// Nút chuyển-trạng-thái ở PMWorkOrderDetailView gate theo `allowed_transitions` do
// BE emit (SSoT = _PM_VALID_TRANSITIONS trong services/imm08.py) — KHÔNG hardcode
// `wo.status === 'X'`. FE = (capability && allowedTransitions.includes(target)).
// Capability khớp EXACT rbac.require (api/imm08.py): start/major = pm.write;
// complete = pm.submit; reschedule = pm.reschedule. Chuỗi đích khớp EXACT PMStatus
// (en-dash: 'Halted–Major Failure', 'Pending–Device Busy').
//
// SSoT map (verified qua bench console, imm08.py:81):
//   Open                 → [In Progress, Overdue, Cancelled]
//   Overdue              → [In Progress, Cancelled]
//   In Progress          → [Completed, Halted–Major Failure, Pending–Device Busy, Cancelled]
//   Pending–Device Busy  → [In Progress, Cancelled]
//   Halted–Major Failure → [In Progress, Cancelled]
//   Completed / Cancelled→ []  (terminal → 0 CTA)
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
    ratedCount: 0,
    checklistComplete: true,
    get hasMajorFailure() { return hasMajorFailure.value },
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

const PM_TRANSITIONS: Record<string, string[]> = {
  'Open': ['In Progress', 'Overdue', 'Cancelled'],
  'Overdue': ['In Progress', 'Cancelled'],
  'In Progress': ['Completed', 'Halted–Major Failure', 'Pending–Device Busy', 'Cancelled'],
  'Pending–Device Busy': ['In Progress', 'Cancelled'],
  'Halted–Major Failure': ['In Progress', 'Cancelled'],
  'Completed': [],
  'Cancelled': [],
}

const ALL_CTA = ['cta-start', 'cta-major', 'cta-complete', 'cta-reschedule', 'cta-resume']

function makeWO(over: WO = {}): WO {
  const status = (over.status as string) ?? 'Open'
  return {
    name: 'WO-PM-2026-00099', asset_ref: 'AC-ASSET-0099', asset_name: 'Máy thở PM',
    asset_category: 'Ventilator', risk_class: 'High', pm_type: 'Routine', wo_type: 'Preventive',
    status, allowed_transitions: PM_TRANSITIONS[status] ?? [],
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

describe('IMM-08 CTA server-driven — bắt đầu bảo trì gate theo allowed_transitions', () => {
  it('Open + assigned_to + allowed gồm "In Progress" → nút "Bắt đầu bảo trì" hiển thị', async () => {
    currentWO.value = makeWO({ status: 'Open' })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-start"]').exists()).toBe(true)
  })

  it('Open nhưng allowed KHÔNG có "In Progress" → nút bắt đầu ẩn (RED khi còn hardcode status===Open)', async () => {
    // Chứng minh gate ăn theo allowed_transitions, KHÔNG theo status literal.
    currentWO.value = makeWO({ status: 'Open', allowed_transitions: ['Overdue', 'Cancelled'] })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-start"]').exists()).toBe(false)
  })

  it('Open + allowed gồm "In Progress" nhưng CHƯA gán KTV → nút bắt đầu ẩn (guard assigned_to)', async () => {
    currentWO.value = makeWO({ status: 'Open', assigned_to: null })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-start"]').exists()).toBe(false)
  })
})

describe('IMM-08 CTA — In Progress: hoàn thành + báo lỗi lớn theo allowed', () => {
  it('In Progress + allowed gồm "Completed" → nút "Hoàn thành bảo trì" hiển thị', async () => {
    currentWO.value = makeWO({ status: 'In Progress' })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-complete"]').exists()).toBe(true)
  })

  it('In Progress + allowed gồm "Halted–Major Failure" → nút "Báo lỗi nghiêm trọng" hiển thị', async () => {
    currentWO.value = makeWO({ status: 'In Progress' })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-major"]').exists()).toBe(true)
  })

  it('In Progress + có lỗi lớn (hasMajorFailure) → nút hoàn thành ẩn, chỉ còn báo lỗi lớn', async () => {
    hasMajorFailure.value = true
    currentWO.value = makeWO({ status: 'In Progress' })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-complete"]').exists()).toBe(false)
    expect(w.find('[data-testid="cta-major"]').exists()).toBe(true)
  })
})

describe('IMM-08 CTA matrix — tập nút KHỚP allowed_transitions (mọi quyền, đã gán KTV)', () => {
  const EXPECTED: Record<string, string[]> = {
    'Open': ['cta-start'],
    'Overdue': ['cta-start', 'cta-reschedule', 'cta-resume'],
    'In Progress': ['cta-major', 'cta-complete'],
    'Pending–Device Busy': ['cta-start'],
    'Halted–Major Failure': ['cta-start'],
  }
  for (const [status, expected] of Object.entries(EXPECTED)) {
    it(`${status} → CTA = [${expected.join(', ')}]`, async () => {
      currentWO.value = makeWO({ status })
      const w = await mountDetail()
      expect(ctasShown(w).sort()).toEqual([...expected].sort())
    })
  }
})

describe('IMM-08 CTA terminal — allowed=[] → 0 nút CTA', () => {
  it.each(['Completed', 'Cancelled'])('%s → 0 CTA', async (status) => {
    currentWO.value = makeWO({ status })
    const w = await mountDetail()
    expect(ctasShown(w)).toEqual([])
  })
})

describe('IMM-08 CTA capability — gate = (cap && includes)', () => {
  it('In Progress nhưng THIẾU pm.write → nút báo lỗi lớn ẩn dù allowed gồm Halted–Major Failure', async () => {
    canImpl = (c: string) => c !== 'pm.write'
    currentWO.value = makeWO({ status: 'In Progress' })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-major"]').exists()).toBe(false)
  })

  it('Open THIẾU pm.write → nút bắt đầu ẩn dù allowed gồm In Progress + đã gán KTV', async () => {
    canImpl = (c: string) => c !== 'pm.write'
    currentWO.value = makeWO({ status: 'Open' })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-start"]').exists()).toBe(false)
  })
})
