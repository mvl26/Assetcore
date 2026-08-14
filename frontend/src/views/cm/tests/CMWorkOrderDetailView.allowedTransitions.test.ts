// TDD (FE regression guard) — GATE-8 / LL-FE-51: server-driven CTA cho Repair WO.
//
// Mọi nút chuyển-trạng-thái ở CMWorkOrderDetailView gate theo `allowed_transitions`
// do BE emit (SSoT = _REPAIR_VALID_TRANSITIONS trong services/imm09.py) — KHÔNG
// hardcode `wo.status === 'X'`. FE = (capability && allowedTransitions.includes(target)).
//
// RED trước fix: nút "Không thể sửa chữa" render ở MỌI state non-terminal (gate cũ
// `!['Completed','Cannot Repair','Cancelled'].includes(status)`) → lộ hành động BE
// cấm ở Open/Assigned/Diagnosing/Pending Parts. Sau fix: chỉ render nơi BE cho phép
// transition 'Cannot Repair' (= In Repair theo _REPAIR_VALID_TRANSITIONS).
//
// SSoT map (verified qua bench console, imm09.py:88):
//   Open              → [Assigned, Cancelled]
//   Assigned          → [Diagnosing, Cancelled]
//   Diagnosing        → [In Repair, Pending Parts, Cancelled]
//   Pending Parts     → [In Repair, Cancelled]
//   In Repair         → [Pending Inspection, Cannot Repair, Cancelled]
//   Pending Inspection→ [Completed, In Repair, Cancelled]
//   Completed / Cannot Repair / Cancelled → []  (terminal → 0 CTA)
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn(), fromOk: vi.fn(), confirm: vi.fn() }),
}))

// Capability controllable per test (mặc định: đủ mọi quyền repair).
let canImpl: (c: string) => boolean = () => true
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: (c: string) => canImpl(c) }),
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

import CMWorkOrderDetailView from '@/views/cm/CMWorkOrderDetailView.vue'

// SSoT transition map (mirror _REPAIR_VALID_TRANSITIONS).
const REPAIR_TRANSITIONS: Record<string, string[]> = {
  'Open': ['Assigned', 'Cancelled'],
  'Assigned': ['Diagnosing', 'Cancelled'],
  'Diagnosing': ['In Repair', 'Pending Parts', 'Cancelled'],
  'Pending Parts': ['In Repair', 'Cancelled'],
  'In Repair': ['Pending Inspection', 'Cannot Repair', 'Cancelled'],
  'Pending Inspection': ['Completed', 'In Repair', 'Cancelled'],
  'Completed': [],
  'Cannot Repair': [],
  'Cancelled': [],
}

const ALL_CTA = ['cta-assign', 'cta-diagnose', 'cta-parts', 'cta-complete', 'cta-confirm-inspection', 'cta-cannot-repair']

function makeWO(over: WO = {}): WO {
  const status = (over.status as string) ?? 'Open'
  return {
    name: 'WO-RP-2026-00099', asset_ref: 'AC-ASSET-0099', asset_name: 'Máy thở CTA',
    asset_category: 'Ventilator', risk_class: 'High', serial_no: 'SN-CTA-1',
    repair_type: 'Corrective', priority: 'Urgent', status,
    allowed_transitions: REPAIR_TRANSITIONS[status] ?? [],
    open_datetime: '2026-06-01 08:00:00', assigned_datetime: '2026-06-01 09:00:00',
    completion_datetime: null, assigned_to: 'ktv@hospital.vn', assigned_to_name: 'KTV A',
    mttr_hours: null, sla_target_hours: 72, sla_breached: false, is_repeat_failure: false,
    incident_report: null, source_pm_wo: null, diagnosis_notes: '', root_cause_category: '',
    repair_summary: '', firmware_updated: false, firmware_change_request: null,
    dept_head_name: '', total_parts_cost: 0, spare_parts_used: [], repair_checklist: [],
    ...over,
  }
}

async function mountDetail() {
  const w = mount(CMWorkOrderDetailView, {
    props: { id: 'WO-RP-2026-00099' },
    global: { stubs: { RouterLink: true, Transition: false }, mocks: { $t: (k: string) => k } },
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
  canImpl = () => true
})

describe('IMM-09 CTA server-driven — bug divergence RED "Không thể sửa chữa"', () => {
  it('Open (allowed=[Assigned,Cancelled]) → nút "Không thể sửa chữa" KHÔNG render', async () => {
    currentWO.value = makeWO({ status: 'Open' })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-cannot-repair"]').exists()).toBe(false)
    // Chỉ có Phân công KTV ở Open.
    expect(w.find('[data-testid="cta-assign"]').exists()).toBe(true)
  })

  it.each(['Open', 'Assigned', 'Diagnosing', 'Pending Parts'])(
    '%s → "Không thể sửa chữa" ẩn (BE cấm transition Cannot Repair)', async (status) => {
      currentWO.value = makeWO({ status })
      const w = await mountDetail()
      expect(w.find('[data-testid="cta-cannot-repair"]').exists()).toBe(false)
    })

  it('In Repair (allowed gồm Cannot Repair) → nút "Không thể sửa chữa" hiển thị', async () => {
    currentWO.value = makeWO({ status: 'In Repair' })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-cannot-repair"]').exists()).toBe(true)
  })
})

describe('IMM-09 CTA matrix — tập nút KHỚP allowed_transitions (mọi quyền)', () => {
  const EXPECTED: Record<string, string[]> = {
    'Open': ['cta-assign'],
    'Assigned': ['cta-diagnose'],
    'Diagnosing': ['cta-diagnose', 'cta-parts'],
    'Pending Parts': ['cta-parts'],
    'In Repair': ['cta-complete', 'cta-cannot-repair'],
    // Pending Inspection: allowed=[Completed, In Repair, Cancelled]. Hành động chính
    // = xác nhận nghiệm thu (Completed). 'In Repair' ở đây là đường TRẢ VỀ (nghiệm
    // thu-fail) → KHÔNG lộ lại vật tư/chẩn đoán (phân biệt bằng có 'Completed').
    // 'Cannot Repair' KHÔNG có trong allowed BE nên ẩn (xem open issue reconciliation).
    'Pending Inspection': ['cta-confirm-inspection'],
  }
  for (const [status, expected] of Object.entries(EXPECTED)) {
    it(`${status} → CTA = [${expected.join(', ')}]`, async () => {
      currentWO.value = makeWO({ status })
      const w = await mountDetail()
      expect(ctasShown(w).sort()).toEqual([...expected].sort())
    })
  }
})

describe('IMM-09 CTA terminal — allowed=[] → 0 nút CTA', () => {
  it.each(['Completed', 'Cannot Repair', 'Cancelled'])('%s → 0 CTA (chỉ nhãn tĩnh)', async (status) => {
    currentWO.value = makeWO({ status })
    const w = await mountDetail()
    expect(ctasShown(w)).toEqual([])
  })
})

describe('IMM-09 CTA capability — gate = (cap && includes)', () => {
  it('Pending Inspection nhưng THIẾU repair.submit → "Xác nhận nghiệm thu" ẩn + 0 CTA dù allowed gồm Completed', async () => {
    canImpl = (c: string) => c !== 'repair.submit' // có repair.create, thiếu repair.submit
    currentWO.value = makeWO({ status: 'Pending Inspection' })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-confirm-inspection"]').exists()).toBe(false)
    // Pending Inspection không lộ vật tư/chẩn đoán (đường trả về) → 0 CTA khi thiếu quyền nghiệm thu.
    expect(ctasShown(w)).toEqual([])
  })

  it('Pending Inspection ĐỦ repair.submit → "Xác nhận nghiệm thu" hiển thị', async () => {
    currentWO.value = makeWO({ status: 'Pending Inspection' })
    const w = await mountDetail()
    expect(w.find('[data-testid="cta-confirm-inspection"]').exists()).toBe(true)
  })

  it('THIẾU mọi quyền repair (non-terminal) → 0 CTA + hint vai trò', async () => {
    canImpl = () => false
    currentWO.value = makeWO({ status: 'In Repair' })
    const w = await mountDetail()
    expect(ctasShown(w)).toEqual([])
    expect(w.text()).toContain('Không có hành động khả dụng cho vai trò hiện tại')
  })
})
