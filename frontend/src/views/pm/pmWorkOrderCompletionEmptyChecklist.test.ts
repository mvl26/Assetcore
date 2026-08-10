// TDD (FE-1 · BR-08-08 chống nghiệm-thu-giả PM) — PMWorkOrderDetailView completion CTA.
//
// Khi bảng kiểm RỖNG (checklist_results=[] — WO tạo qua path template-less, thiếu bảng
// kiểm mẫu) thì KHÔNG có bằng chứng công việc ⇒ CTA "Hoàn thành bảo trì" phải DISABLED
// + hiển thị hint VI RIÊNG ('Chưa có mục bảng kiểm — không thể nghiệm thu PM'), KHÁC
// thông điệp "chưa chấm hết". Mirror FE của gate BE IMM08_CHECKLIST_EMPTY.
//
// Counter-case: có ≥1 mục đã chấm + đủ thời gian + đã gắn tem → CTA ENABLED (không chặn
// oan). Gate = server-driven CTA (allowed_transitions gồm 'Completed') + điều kiện
// nghiệm-thu (checklist/quyền/tem/thời-lượng) chi phối disabled.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())
const notifyShow = vi.fn()
const notifyFromError = vi.fn()
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: notifyShow, fromError: notifyFromError, fromOk: vi.fn(), confirm: vi.fn() }),
}))
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn() }),
}))
// Đủ mọi quyền pm (cap true) — cô lập biến số quyền để test nhánh checklist.
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))

type Row = {
  idx: number; checklist_item_idx: number; description: string
  measurement_type: string; unit: string; result: string | null
  measured_value: number | null; notes: string; photo: string | null
}
type WO = Record<string, unknown>

const currentWO = ref<WO | null>(null)
const doSubmitResult = vi.fn().mockResolvedValue({ success: true, newStatus: 'Completed' })
const fetchWorkOrder = vi.fn().mockResolvedValue(undefined)

const RATED = ['Pass', 'Fail–Minor', 'Fail–Major', 'N/A']
const rows = (): Row[] => (currentWO.value?.checklist_results as Row[] | undefined) ?? []
const isRated = (r: Row) => r.result != null && RATED.includes(r.result)

// Store mock: getter DẪN XUẤT từ currentWO ⇒ phản ánh THẬT empty-vs-filled (không hardcode).
vi.mock('@/stores/imm08', () => ({
  useImm08Store: () => ({
    get currentWO() { return currentWO.value },
    loading: false,
    error: null,
    lastApiError: null,
    get ratedCount() { return rows().filter(isRated).length },
    get checklistComplete() { const i = rows(); return i.length > 0 && i.every(isRated) },
    get hasMajorFailure() { return rows().some((r) => r.result === 'Fail–Major') },
    get hasMinorFailure() { return rows().some((r) => r.result === 'Fail–Minor') },
    fetchWorkOrder,
    updateChecklistResult: vi.fn(),
    doSubmitResult,
    doReportMajorFailure: vi.fn(),
    doReschedule: vi.fn(),
    doAssignTechnician: vi.fn(),
  }),
}))

import PMWorkOrderDetailView from './PMWorkOrderDetailView.vue'

const EMPTY_HINT = 'Chưa có mục bảng kiểm — không thể nghiệm thu PM'

function makeWO(over: WO = {}): WO {
  return {
    name: 'WO-PM-2026-00099',
    asset_ref: 'AC-ASSET-0099',
    asset_name: 'Máy thở',
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
    // In Progress → BE cho phép chuyển 'Completed' ⇒ nút "Hoàn thành" render (disabled
    // theo điều kiện nghiệm-thu). Mirror _PM_VALID_TRANSITIONS.
    allowed_transitions: ['Completed', 'Halted–Major Failure', 'Pending–Device Busy', 'Cancelled'],
    ...over,
  }
}

function ratedRow(idx: number): Row {
  return {
    idx, checklist_item_idx: idx, description: `Mục ${idx}`,
    measurement_type: 'Pass/Fail', unit: '', result: 'Pass',
    measured_value: null, notes: '', photo: null,
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
  currentWO.value = null
  notifyShow.mockClear()
  notifyFromError.mockClear()
  doSubmitResult.mockClear()
  fetchWorkOrder.mockClear()
})

describe('FE-1 — PM completion CTA khi bảng kiểm RỖNG (BR-08-08)', () => {
  it('checklist_results=[] → cta-complete RENDER nhưng DISABLED', async () => {
    currentWO.value = makeWO({ checklist_results: [] })
    const w = await mountDetail()
    const cta = w.find('[data-testid="cta-complete"]')
    expect(cta.exists()).toBe(true)
    expect(cta.attributes('disabled')).toBeDefined()
  })

  it('checklist_results=[] → hiển thị hint VI RIÊNG cho bảng kiểm rỗng', async () => {
    currentWO.value = makeWO({ checklist_results: [] })
    const w = await mountDetail()
    expect(w.text()).toContain(EMPTY_HINT)
    // KHÔNG dùng nhầm thông điệp "chưa chấm hết" cho trường hợp rỗng.
    expect(w.text()).not.toContain('Phải chấm kết quả cho tất cả mục checklist')
  })

  it('checklist_results=[] → bấm cta-complete KHÔNG mở modal + KHÔNG gọi doSubmitResult', async () => {
    currentWO.value = makeWO({ checklist_results: [] })
    const w = await mountDetail()
    await w.find('[data-testid="cta-complete"]').trigger('click')
    await flushPromises()
    // Modal xác nhận (h3 'Xác nhận hoàn thành bảo trì') KHÔNG mở.
    expect(w.text()).not.toContain('Xác nhận hoàn thành bảo trì')
    expect(doSubmitResult).not.toHaveBeenCalled()
  })

  it('≥1 mục đã chấm + đủ thời gian + đã gắn tem → cta-complete ENABLED + ẩn hint rỗng', async () => {
    currentWO.value = makeWO({ checklist_results: [ratedRow(1)] })
    const w = await mountDetail()
    // Điền form nghiệm-thu (local ref của view): thời gian > 0 + tem.
    await w.find('#duration-min').setValue(45)
    await w.find('#sticker').setValue(true)
    await flushPromises()
    const cta = w.find('[data-testid="cta-complete"]')
    expect(cta.exists()).toBe(true)
    expect(cta.attributes('disabled')).toBeUndefined()
    expect(w.text()).not.toContain(EMPTY_HINT)
  })
})
