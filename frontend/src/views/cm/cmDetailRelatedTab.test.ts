// Copyright (c) 2026, AssetCore Team
// TDD — TC-CONNTAB-06 (AC-CR-87 vòng 3): «Bản ghi liên quan» thành TAB mount LƯỜI ở màn
// chi tiết lệnh sửa chữa (IMM-09).
//
// Ngoài hợp đồng chung (0 request trước khi mở tab), màn này khoá thêm một bẫy riêng:
// modal «Phân công kỹ thuật viên» / «Không thể sửa chữa» PHẢI nằm NGOÀI hai panel — nếu
// lọt vào panel chính (v-show) thì `display:none` sẽ nuốt luôn modal khi người dùng đang
// ở tab liên quan, và người dùng bấm nút xong… không thấy gì.
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

const getConnections = vi.fn()
vi.mock('@/api/connections', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/connections')>()),
  getConnections: (...a: unknown[]) => getConnections(...a),
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

import RelatedRecords from '@/components/common/RelatedRecords.vue'
import CMWorkOrderDetailView from './CMWorkOrderDetailView.vue'
import { expectVietnameseTabs } from '@/test/tabLabelParity'

const WO_NAME = 'WO-RP-2026-00099'

function makeWO(over: WO = {}): WO {
  return {
    name: WO_NAME, asset_ref: 'AC-ASSET-0099', asset_name: 'Máy thở CTA',
    asset_category: 'Ventilator', risk_class: 'High', serial_no: 'SN-CTA-1',
    repair_type: 'Corrective', priority: 'Urgent', status: 'Open',
    allowed_transitions: ['Assigned', 'Cancelled'],
    open_datetime: '2026-06-01 08:00:00', assigned_datetime: null, completion_datetime: null,
    assigned_to: '', assigned_to_name: '', mttr_hours: null, sla_target_hours: 72,
    sla_breached: false, is_repeat_failure: false, incident_report: null, source_pm_wo: null,
    diagnosis_notes: '', root_cause_category: '', repair_summary: '', firmware_updated: false,
    firmware_change_request: null, dept_head_name: '', total_parts_cost: 0,
    spare_parts_used: [], repair_checklist: [],
    ...over,
  }
}

async function mountDetail() {
  const w = mount(CMWorkOrderDetailView, {
    props: { id: WO_NAME },
    global: {
      stubs: { RouterLink: true, Transition: false, ApproverSelect: true },
      mocks: { $t: (k: string) => k },
    },
  })
  await flushPromises()
  return w
}

beforeEach(() => {
  setActivePinia(createPinia())
  getConnections.mockReset()
  getConnections.mockResolvedValue({ doctype: 'Asset Repair', name: WO_NAME, total: 0, groups: [] })
  fetchWorkOrder.mockClear()
  currentWO.value = makeWO()
})

describe('TC-CONNTAB-06 — IMM-09: tab «Bản ghi liên quan» mount lười', () => {
  it('tab mặc định ⇒ 0 lần gọi get_connections ∧ 0 khối liên quan trong DOM', async () => {
    const w = await mountDetail()
    expect(getConnections).toHaveBeenCalledTimes(0)
    expect(w.findAll('[data-testid="related-records"]')).toHaveLength(0)
  })

  it('bấm tab liên quan ⇒ ĐÚNG 1 lần gọi ∧ khối xuất hiện ĐÚNG 1 lần, prop đúng cặp', async () => {
    const w = await mountDetail()
    await w.find('[data-testid="tab-related"]').trigger('click')
    await flushPromises()

    expect(getConnections).toHaveBeenCalledTimes(1)
    expect(w.findAll('[data-testid="related-records"]')).toHaveLength(1)

    const rr = w.findComponent(RelatedRecords)
    expect(rr.props('doctype')).toBe('Asset Repair')
    expect(rr.props('name')).toBe(WO_NAME)
  })

  it('tab liên quan active ⇒ [data-testid="tab-panel-detail"] có display:none', async () => {
    const w = await mountDetail()
    await w.find('[data-testid="tab-related"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="tab-panel-detail"]').attributes('style')).toContain('display: none')
  })

  it('nhãn tab 100% tiếng Việt (LL-FE-53)', async () => {
    expectVietnameseTabs(await mountDetail())
  })
})

describe('TC-CONNTAB-06 · bẫy T4 — modal KHÔNG bị panel v-show nuốt', () => {
  it('mở modal phân công rồi sang tab liên quan ⇒ modal vẫn hiện, nằm NGOÀI panel chính', async () => {
    const w = await mountDetail()
    await w.find('[data-testid="cta-assign"]').trigger('click')
    await flushPromises()

    const modal = w.find('.fixed.inset-0')
    expect(modal.exists()).toBe(true)

    await w.find('[data-testid="tab-related"]').trigger('click')
    await flushPromises()

    const modalAfter = w.find('.fixed.inset-0')
    expect(modalAfter.exists()).toBe(true)
    // Modal KHÔNG được là con của panel chính (panel đang display:none).
    const detailPanel = w.find('[data-testid="tab-panel-detail"]').element
    expect(detailPanel.contains(modalAfter.element)).toBe(false)
    expect(w.text()).toContain('Phân công kỹ thuật viên')
  })
})
