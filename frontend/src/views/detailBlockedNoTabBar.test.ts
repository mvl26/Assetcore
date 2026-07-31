// Copyright (c) 2026, AssetCore Team
// TDD — TC-CONNTAB-11 (AC-CR-87 vòng 3): phiếu bị CHẶN ĐỌC (403 in-envelope) ⇒ 4 màn
// workflow KHÔNG render thanh tab.
//
// Vì sao tách file riêng: `detailReadForbiddenGate.test.ts` (CR-74) là hợp đồng "0 CTA khi
// 403" và phải chạy XANH KHÔNG SỬA MỘT ASSERT NÀO. Điều kiện mới của vòng này — thanh tab
// cũng là affordance, nên cũng KHÔNG được render khi phiếu chưa/không đọc được — được
// khoá ở đây để không đụng vào hợp đồng cũ.
//
// Bẫy tránh: nếu ai đó đưa thanh tab ra NGOÀI nhánh `v-if` bản ghi (cho "gọn"), người dùng
// bị từ chối đọc sẽ thấy 2 nút tab bấm-không-ra-gì — đúng loại dead-control mà CR-74 đóng.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import { setActivePinia, createPinia } from 'pinia'
import { ApiError, ErrorCode } from '@/api/errors'

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
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({ isSystemAdmin: false, user: { name: 'ktv@benhvien.vn' }, logout: vi.fn() }),
}))

const getConnections = vi.fn()
vi.mock('@/api/connections', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/connections')>()),
  getConnections: (...a: unknown[]) => getConnections(...a),
}))

type WO = Record<string, unknown>
const pmError = ref<ApiError | null>(null)
const cmError = ref<ApiError | null>(null)
vi.mock('@/stores/imm08', () => ({
  useImm08Store: () => ({
    currentWO: null as WO | null, loading: false,
    get error() { return pmError.value?.message ?? null },
    get lastApiError() { return pmError.value },
    ratedCount: 0, checklistComplete: false, hasMajorFailure: false, hasMinorFailure: false,
    fetchWorkOrder: vi.fn().mockResolvedValue(undefined),
    updateChecklistResult: vi.fn(), doSubmitResult: vi.fn(), doReportMajorFailure: vi.fn(),
    doReschedule: vi.fn(), doAssignTechnician: vi.fn(),
  }),
}))
vi.mock('@/stores/imm09', () => ({
  useImm09Store: () => ({
    currentWO: null as WO | null, loading: false,
    get error() { return cmError.value?.message ?? null },
    get lastApiError() { return cmError.value },
    fetchWorkOrder: vi.fn().mockResolvedValue(undefined),
    doAssignTechnician: vi.fn(), doConfirmInspection: vi.fn(), doCloseWorkOrder: vi.fn(),
  }),
}))
vi.mock('@/stores/imm11', () => ({
  useImm11Store: () => ({
    doSendToLab: vi.fn(), doReceiveCertificate: vi.fn(), doCancel: vi.fn(), doSubmit: vi.fn(),
    doReschedule: vi.fn(), _captureError: vi.fn(), error: null, lastApiError: null,
  }),
}))
vi.mock('@/api/imm05', () => ({ uploadDocumentFile: vi.fn() }))
vi.mock('@/api/imm11', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/imm11')>()),
  getCalibration: vi.fn(), updateCalibration: vi.fn(),
}))
vi.mock('@/api/imm00', () => ({ deleteIncident: vi.fn() }))
vi.mock('@/api/imm12', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/imm12')>()
  return {
    ...actual,
    getIncident: vi.fn(), acknowledgeIncident: vi.fn(), startWork: vi.fn(),
    resolveIncident: vi.fn(), closeIncident: vi.fn(), cancelIncident: vi.fn(),
    reopenIncident: vi.fn(), requestRca: vi.fn(), createRca: vi.fn(), attachIncidentPhoto: vi.fn(),
  }
})

import { getCalibration } from '@/api/imm11'
import { getIncident } from '@/api/imm12'
import { resetRouteMock, setRouteParams } from '@/test/vueRouterMock'
import PMWorkOrderDetailView from './pm/PMWorkOrderDetailView.vue'
import CMWorkOrderDetailView from './cm/CMWorkOrderDetailView.vue'
import CalibrationDetailView from './calibration/CalibrationDetailView.vue'
import IncidentDetailView from './incident/IncidentDetailView.vue'

const STUBS = {
  RouterLink: true, Transition: false, DateInput: true, StatusBadge: true,
  WorkflowStepper: true, ApproverSelect: true, SlaBreachBadge: true,
}

function forbidden(): ApiError {
  return new ApiError('Bạn không có quyền thực hiện hành động này.', {
    code: ErrorCode.FORBIDDEN, httpStatus: 403, messageCode: 'AUTH-403',
    title: 'Không đủ quyền', severity: 'warning',
  })
}

beforeEach(() => {
  setActivePinia(createPinia())
  resetRouteMock()
  setRouteParams({ id: 'INC-2026-00077' })
  getConnections.mockReset()
  pmError.value = forbidden()
  cmError.value = forbidden()
  vi.mocked(getCalibration).mockReset()
  vi.mocked(getCalibration).mockRejectedValue(forbidden())
  vi.mocked(getIncident).mockReset()
  vi.mocked(getIncident).mockRejectedValue(forbidden())
})

/** Bị chặn đọc ⇒ 0 nút tab, 0 khối liên quan, 0 request đồ thị liên kết. */
async function expectNoTabAffordance(w: { findAll: (s: string) => unknown[] }) {
  expect(w.findAll('[role="tab"]')).toHaveLength(0)
  expect(w.findAll('[data-testid="related-records"]')).toHaveLength(0)
  expect(getConnections).toHaveBeenCalledTimes(0)
}

describe('TC-CONNTAB-11 — 403 in-envelope: KHÔNG có thanh tab chết ở 4 màn workflow', () => {
  it('IMM-08 phiếu bảo trì định kỳ', async () => {
    const w = mount(PMWorkOrderDetailView, { props: { id: 'WO-PM-1' }, global: { stubs: STUBS } })
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').exists()).toBe(true)
    await expectNoTabAffordance(w)
  })

  it('IMM-09 lệnh sửa chữa', async () => {
    const w = mount(CMWorkOrderDetailView, { props: { id: 'WO-RP-1' }, global: { stubs: STUBS } })
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').exists()).toBe(true)
    await expectNoTabAffordance(w)
  })

  it('IMM-11 phiếu hiệu chuẩn', async () => {
    const w = mount(CalibrationDetailView, { props: { id: 'CAL-1' }, global: { stubs: STUBS } })
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').exists()).toBe(true)
    await expectNoTabAffordance(w)
  })

  it('IMM-12 phiếu sự cố', async () => {
    const w = mount(IncidentDetailView, { global: { stubs: STUBS } })
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').exists()).toBe(true)
    await expectNoTabAffordance(w)
  })
})
