// Copyright (c) 2026, AssetCore Team
// TDD — TC-CONNTAB-07 (AC-CR-87 vòng 3): «Bản ghi liên quan» thành TAB mount LƯỜI ở màn
// chi tiết phiếu hiệu chuẩn (IMM-11).
//
// Bẫy riêng của màn này: khối liên quan nhận `props.id` (mã trên URL) chứ KHÔNG phải
// `form.name`. Fixture dưới đây cố ý đặt `name` KHÁC `id` để bắt lỗi nhầm biến — nếu ai
// đó "dọn dẹp" thành `form.name`, test ĐỎ ngay.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn() }),
}))
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() }),
}))
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))
vi.mock('@/stores/imm11', () => ({
  useImm11Store: () => ({
    doSendToLab: vi.fn(), doReceiveCertificate: vi.fn(), doCancel: vi.fn(),
    doSubmit: vi.fn(), doReschedule: vi.fn(),
    _captureError: vi.fn(), error: null, lastApiError: null,
  }),
}))
vi.mock('@/api/imm05', () => ({ uploadDocumentFile: vi.fn() }))
vi.mock('@/api/imm11', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/imm11')>()),
  getCalibration: vi.fn(), updateCalibration: vi.fn(),
}))

const getConnections = vi.fn()
vi.mock('@/api/connections', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/connections')>()),
  getConnections: (...a: unknown[]) => getConnections(...a),
}))

import { getCalibration } from '@/api/imm11'
import RelatedRecords from '@/components/common/RelatedRecords.vue'
import CalibrationDetailView from '@/views/calibration/CalibrationDetailView.vue'
import { expectVietnameseTabs } from '@/test/tabLabelParity'

/** Mã trên URL — CỐ Ý khác `name` trong payload để bắt nhầm biến. */
const ROUTE_ID = 'CAL-2026-00077'

function calFixture() {
  return {
    name: 'CAL-KHAC-BIET-0001', asset: 'AC-ASSET-2026-00042', asset_name: 'Máy thở CTA',
    device_model: 'M1', calibration_schedule: null, calibration_type: 'In-House',
    status: 'Scheduled', scheduled_date: '2026-08-01', actual_date: null,
    technician: 'ktv@benhvien.vn', technician_name: 'KTV A',
    docstatus: 0, overall_result: null, measurements: [],
    allowed_transitions: ['In Progress', 'Sent to Lab', 'Cancelled'],
  }
}

async function mountDetail() {
  const w = mount(CalibrationDetailView, {
    props: { id: ROUTE_ID },
    global: { stubs: { DateInput: true, StatusBadge: true, WorkflowStepper: true } },
  })
  await flushPromises()
  return w
}

beforeEach(() => {
  getConnections.mockReset()
  getConnections.mockResolvedValue({
    doctype: 'IMM Asset Calibration', name: ROUTE_ID, total: 0, groups: [],
  })
  vi.mocked(getCalibration).mockReset()
  vi.mocked(getCalibration).mockResolvedValue(calFixture() as never)
})

describe('TC-CONNTAB-07 — IMM-11: tab «Bản ghi liên quan» mount lười', () => {
  it('tab mặc định ⇒ 0 lần gọi get_connections ∧ 0 khối liên quan trong DOM', async () => {
    const w = await mountDetail()
    expect(getConnections).toHaveBeenCalledTimes(0)
    expect(w.findAll('[data-testid="related-records"]')).toHaveLength(0)
  })

  it('bấm tab liên quan ⇒ ĐÚNG 1 lần gọi ∧ prop = (IMM Asset Calibration, props.id)', async () => {
    const w = await mountDetail()
    await w.find('[data-testid="tab-related"]').trigger('click')
    await flushPromises()

    expect(getConnections).toHaveBeenCalledTimes(1)
    expect(w.findAll('[data-testid="related-records"]')).toHaveLength(1)

    const rr = w.findComponent(RelatedRecords)
    expect(rr.props('doctype')).toBe('IMM Asset Calibration')
    expect(rr.props('name')).toBe(ROUTE_ID)
  })

  it('tab liên quan active ⇒ [data-testid="tab-panel-detail"] có display:none', async () => {
    const w = await mountDetail()
    await w.find('[data-testid="tab-related"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="tab-panel-detail"]').attributes('style')).toContain('display: none')
  })

  it('đổi tab KHÔNG nạp lại phiếu (getCalibration vẫn 1 lần)', async () => {
    const w = await mountDetail()
    expect(vi.mocked(getCalibration)).toHaveBeenCalledTimes(1)
    await w.find('[data-testid="tab-related"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="tab-detail"]').trigger('click')
    await flushPromises()
    expect(vi.mocked(getCalibration)).toHaveBeenCalledTimes(1)
  })

  it('nhãn tab 100% tiếng Việt (LL-FE-53)', async () => {
    expectVietnameseTabs(await mountDetail())
  })
})
