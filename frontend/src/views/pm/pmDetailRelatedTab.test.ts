// Copyright (c) 2026, AssetCore Team
// TDD — TC-CONNTAB-05 + ca A4 (AC-CR-87 vòng 3): «Bản ghi liên quan» thành TAB mount LƯỜI
// ở màn chi tiết phiếu bảo trì định kỳ (IMM-08).
//
// Trước vòng này khối liên quan nối đuôi nội dung chính ⇒ MỌI lần mở phiếu đều bắn
// `get_connections` dù người dùng không cuộn tới. Đo được bằng spy: tab mặc định ⇒ 0 lần
// gọi; bấm tab ⇒ đúng 1 lần. (Cải thiện thuần — hợp đồng BE KHÔNG đổi.)
//
// Ca A4 (không mất dữ liệu): panel chính dùng v-show ⇒ gõ ghi chú kỹ thuật viên, sang tab
// liên quan rồi quay lại thì chữ CÒN NGUYÊN và phiếu KHÔNG bị nạp lại lần 2.
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

// Spy đo mount lười — giữ nguyên các export hằng/helper thật của module.
const getConnections = vi.fn()
vi.mock('@/api/connections', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/connections')>()),
  getConnections: (...a: unknown[]) => getConnections(...a),
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
    doSubmitResult: vi.fn(),
    doReportMajorFailure: vi.fn(),
    doReschedule: vi.fn(),
    doAssignTechnician: vi.fn(),
  }),
}))

import RelatedRecords from '@/components/common/RelatedRecords.vue'
import PMWorkOrderDetailView from './PMWorkOrderDetailView.vue'
import { expectVietnameseTabs } from '@/test/tabLabelParity'

const WO_NAME = 'WO-PM-2026-00042'

function makeWO(over: WO = {}): WO {
  return {
    name: WO_NAME,
    asset_ref: 'AC-ASSET-0042',
    asset_name: 'Máy siêu âm',
    risk_class: 'Medium',
    status: 'In Progress',
    pm_type: 'Preventive',
    wo_type: 'PM',
    due_date: '2026-06-30',
    is_late: false,
    assigned_to: 'ktv@benhvien.vn',
    assigned_to_name: 'KTV A',
    supervisor: '',
    checklist_results: [],
    overall_result: null,
    completion_date: null,
    allowed_transitions: ['Completed'],
    ...over,
  }
}

async function mountDetail() {
  const w = mount(PMWorkOrderDetailView, {
    props: { id: WO_NAME },
    global: { stubs: { RouterLink: true, Transition: false, DateInput: true } },
  })
  await flushPromises()
  return w
}

beforeEach(() => {
  setActivePinia(createPinia())
  getConnections.mockReset()
  getConnections.mockResolvedValue({ doctype: 'PM Work Order', name: WO_NAME, total: 0, groups: [] })
  fetchWorkOrder.mockClear()
  currentWO.value = makeWO()
})

describe('TC-CONNTAB-05 — IMM-08: tab «Bản ghi liên quan» mount lười', () => {
  it('tab mặc định ⇒ 0 lần gọi get_connections ∧ 0 khối liên quan trong DOM', async () => {
    const w = await mountDetail()
    expect(getConnections).toHaveBeenCalledTimes(0)
    expect(w.findAll('[data-testid="related-records"]')).toHaveLength(0)
    expect(w.find('[data-testid="tab-panel-related"]').exists()).toBe(false)
  })

  it('bấm tab liên quan ⇒ ĐÚNG 1 lần gọi ∧ khối xuất hiện ĐÚNG 1 lần, prop đúng cặp', async () => {
    const w = await mountDetail()
    await w.find('[data-testid="tab-related"]').trigger('click')
    await flushPromises()

    expect(getConnections).toHaveBeenCalledTimes(1)
    expect(w.findAll('[data-testid="related-records"]')).toHaveLength(1)

    // Đọc prop THẬT của component (không so chuỗi trong source).
    const rr = w.findComponent(RelatedRecords)
    expect(rr.props('doctype')).toBe('PM Work Order')
    expect(rr.props('name')).toBe(WO_NAME)
  })

  it('tab liên quan active ⇒ thân trang bị ẩn (display:none), không nối đuôi nội dung', async () => {
    const w = await mountDetail()
    const panel = w.find('[data-testid="tab-panel-detail"]')
    expect(panel.attributes('style') || '').not.toContain('display: none')

    await w.find('[data-testid="tab-related"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="tab-panel-detail"]').attributes('style')).toContain('display: none')
  })

  it('nhãn tab 100% tiếng Việt (LL-FE-53)', async () => {
    expectVietnameseTabs(await mountDetail())
  })
})

describe('TC-CONNTAB-05 · ca A4 — đổi tab KHÔNG mất dữ liệu đang nhập, KHÔNG nạp lại phiếu', () => {
  it('gõ ghi chú → sang tab liên quan → quay lại ⇒ giá trị CÒN NGUYÊN', async () => {
    const w = await mountDetail()
    const notes = w.find('#tech-notes')
    await notes.setValue('Đã thay lọc khí, chờ chạy thử 30 phút')

    await w.find('[data-testid="tab-related"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="tab-detail"]').trigger('click')
    await flushPromises()

    expect((w.find('#tech-notes').element as HTMLTextAreaElement).value)
      .toBe('Đã thay lọc khí, chờ chạy thử 30 phút')
  })

  it('đổi tab KHÔNG gọi lại fetchWorkOrder (panel v-show ⇒ không remount)', async () => {
    const w = await mountDetail()
    const callsAfterMount = fetchWorkOrder.mock.calls.length
    expect(callsAfterMount).toBe(1)

    await w.find('[data-testid="tab-related"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="tab-detail"]').trigger('click')
    await flushPromises()

    expect(fetchWorkOrder).toHaveBeenCalledTimes(callsAfterMount)
  })

  it('quay lại tab chi tiết ⇒ panel liên quan bị huỷ (v-if) ⇒ vẫn 1 lần gọi duy nhất', async () => {
    const w = await mountDetail()
    await w.find('[data-testid="tab-related"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="tab-detail"]').trigger('click')
    await flushPromises()

    expect(w.find('[data-testid="tab-panel-related"]').exists()).toBe(false)
    expect(getConnections).toHaveBeenCalledTimes(1)
  })
})
