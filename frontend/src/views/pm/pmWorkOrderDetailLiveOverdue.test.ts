// TDD (FE regression guard) — CR-37 · BR-08-11 LIVE: banner "Bảo trì quá hạn" +
// red-highlight due_date ở PMWorkOrderDetailView đọc cờ SERVER LIVE `is_overdue`
// (do get_pm_work_order enrich, CÙNG predicate _enrich_pm_overdue của list-item),
// KHÔNG hardcode `status === 'Overdue'` / cờ STORED `is_late`.
//
// PHÂN KỲ LIVE vs STORED (cửa-sổ-trễ-scheduler): 1 PM WO đã vượt due_date nhưng
// cron nightly chưa stamp status→Overdue ⇒ status vẫn 'In Progress', is_late=0.
// BE derive is_overdue=true LIVE. Banner PHẢI hiện — nếu FE đọc STORED status/is_late
// thì banner ẩn (badge trễ 1 nhịp scheduler = cận an-toàn người bệnh).
//
// RED-prove: revert binding `isOverdue` về `wo.value?.status === 'Overdue'` ⇒
// case (1) FAIL (banner ẩn dù is_overdue=true). Đối xứng cmSlaBreachedDivergence
// case (C).
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
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))

type WO = Record<string, unknown>
const currentWO = ref<WO | null>(null)
const fetchWorkOrder = vi.fn().mockResolvedValue(undefined)
vi.mock('@/stores/imm08', () => ({
  useImm08Store: () => ({
    get currentWO() { return currentWO.value },
    loading: false,
    error: null,
    lastApiError: null,
    get ratedCount() { return 0 },
    get checklistComplete() { return true },
    get hasMajorFailure() { return false },
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

function makeWO(over: WO = {}): WO {
  return {
    name: 'WO-PM-2026-00042',
    asset_ref: 'AC-ASSET-0042',
    asset_name: 'Máy siêu âm',
    risk_class: 'Medium',
    status: 'In Progress',
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
    allowed_transitions: ['Completed', 'Halted–Major Failure', 'Pending–Device Busy', 'Cancelled'],
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

// due_date span nằm ở info-grid: span kề "Đến hạn:" — bắt bằng class text-red-600.
function dueDateIsRed(w: Awaited<ReturnType<typeof mountDetail>>): boolean {
  return w.findAll('span').some(
    (s) => s.text().includes('2026-06-30') && s.classes().includes('text-red-600'))
}

beforeEach(() => {
  setActivePinia(createPinia())
  fetchWorkOrder.mockClear()
  currentWO.value = null
})

describe('PM detail — banner "Bảo trì quá hạn" theo cờ LIVE is_overdue (CR-37)', () => {
  it('(1) is_overdue=true NHƯNG status="In Progress", is_late=0 → banner RENDER (LIVE ≠ STORED)', async () => {
    // Phân kỳ LIVE vs STORED: scheduler chưa stamp Overdue, chưa hoàn thành.
    currentWO.value = makeWO({ status: 'In Progress', is_overdue: true, is_late: false })
    const w = await mountDetail()
    // RED-prove: nếu binding còn `status === 'Overdue'` → banner ẩn ⇒ FAIL.
    expect(w.text()).toContain('Bảo trì quá hạn')
    expect(dueDateIsRed(w)).toBe(true)
  })

  it('(2) is_overdue=false, status="In Progress" → banner ẩn (không phantom)', async () => {
    currentWO.value = makeWO({ status: 'In Progress', is_overdue: false, is_late: false })
    const w = await mountDetail()
    expect(w.text()).not.toContain('Bảo trì quá hạn')
    expect(dueDateIsRed(w)).toBe(false)
  })

  it('(3) fallback forward-compat: is_overdue undefined + status="Overdue" → banner RENDER', async () => {
    // BE chưa emit is_overdue (undefined) → đọc fallback status === "Overdue".
    currentWO.value = makeWO({ status: 'Overdue', is_late: false })
    delete (currentWO.value as WO).is_overdue
    const w = await mountDetail()
    expect(w.text()).toContain('Bảo trì quá hạn')
  })

  it('(4) fallback: is_overdue undefined + status="In Progress" → banner ẩn', async () => {
    currentWO.value = makeWO({ status: 'In Progress', is_late: false })
    delete (currentWO.value as WO).is_overdue
    const w = await mountDetail()
    expect(w.text()).not.toContain('Bảo trì quá hạn')
  })

  it('(5) due_date đỏ giữ tín hiệu lịch sử: is_overdue=false nhưng is_late=1 (hoàn-thành-trễ)', async () => {
    // WO đã Completed trễ: is_overdue=false (terminal) nhưng is_late=1 → due_date vẫn đỏ.
    currentWO.value = makeWO({ status: 'Completed', is_overdue: false, is_late: true, completion_date: '2026-07-05' })
    const w = await mountDetail()
    expect(dueDateIsRed(w)).toBe(true)
    // Nhưng KHÔNG hiện banner "đang quá hạn" (phiếu đã đóng).
    expect(w.text()).not.toContain('Bảo trì quá hạn')
  })
})
