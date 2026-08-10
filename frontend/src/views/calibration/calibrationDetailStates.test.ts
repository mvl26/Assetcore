// Copyright (c) 2026, AssetCore Team
// TC-UX4-33 (docs/ui-ux/03 §13.6) — CalibrationDetailView áp khuôn `DetailPageShell` (lô 2, nhóm N1).
//
// RED trước fix: view tự dựng chuỗi trạng thái và tự gọi `loadErrorKind` (bản sao thứ N của logic
// phân loại — AC-UX-053); `loading` khởi tạo `false` nên khung 404 NHÁY đúng một nhịp trước lượt
// nạp đầu tiên (INV-UX4-8); thanh tab `DetailTabBar` cục bộ nằm trong nhánh `v-else` tự chế.
// Sau fix: shell sở hữu 4 trạng thái, kind từ SSoT, thanh tab hoisting lên prop (ADR-UX-25).
import { vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { describeDetailStates } from '@/test/detailStatesHarness'

const pushSpy = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushSpy, back: vi.fn() }),
  useRoute: () => ({ params: { id: 'CAL-2026-00001' }, query: {} }),
}))
vi.mock('@/composables/useNotify', () => ({ useNotify: () => ({ show: vi.fn(), fromError: vi.fn() }) }))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ success: vi.fn(), warning: vi.fn() }) }))
vi.mock('@/composables/useCapabilities', () => ({ useCapabilities: () => ({ can: () => true }) }))
vi.mock('@/stores/imm11', () => ({
  useImm11Store: () => ({
    doSendToLab: vi.fn(), doReceiveCertificate: vi.fn(), doCancel: vi.fn(), doSubmit: vi.fn(),
    _captureError: vi.fn(), error: null, lastApiError: null,
  }),
}))
vi.mock('@/api/imm05', () => ({ uploadDocumentFile: vi.fn() }))

const getCalibrationSpy = vi.fn()
vi.mock('@/api/imm11', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/imm11')>()),
  getCalibration: (...a: unknown[]) => getCalibrationSpy(...(a as [])),
  updateCalibration: vi.fn(),
}))

import CalibrationDetailView from './CalibrationDetailView.vue'

const stubs = { DateInput: true, StatusBadge: true, WorkflowStepper: true, RelatedRecords: true, RouterLink: true, FileUploadField: true }

function calFixture() {
  return {
    name: 'CAL-2026-00001', asset: 'AC-ASSET-2026-00001', asset_name: 'Máy thở',
    device_model: 'M1', calibration_schedule: null,
    calibration_type: 'In-House', status: 'Scheduled',
    scheduled_date: '2026-06-01', actual_date: null, technician: 't@x.vn',
    technician_name: 'KTV A', assigned_by: null,
    docstatus: 0, allowed_transitions: ['In Progress', 'Cancelled'],
    measurements: [],
  }
}

describeDetailStates({
  view: 'CalibrationDetailView',
  tc: 'TC-UX4-33',
  mount: () => mount(CalibrationDetailView, { props: { id: 'CAL-2026-00001' }, global: { stubs } }) as never,
  pending: () => getCalibrationSpy.mockReturnValue(new Promise(() => {})),
  fail: (e) => getCalibrationSpy.mockRejectedValue(e),
  // `form` khởi tạo `{}` là TRUTHY ⇒ `:doc` phải là `form.name ? form : null`.
  empty: () => getCalibrationSpy.mockResolvedValue(null),
  ok: () => getCalibrationSpy.mockResolvedValue(calFixture()),
  loadCalls: () => getCalibrationSpy.mock.calls.length,
  reset: () => {
    getCalibrationSpy.mockReset()
    pushSpy.mockClear()
  },
  recordId: 'CAL-2026-00001',
  ctaTestIds: ['cta-reschedule-calibration', 'tab-panel-detail'],
  hasTabs: true,
  routerPush: pushSpy,
})
