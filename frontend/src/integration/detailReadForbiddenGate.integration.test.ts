// Copyright (c) 2026, AssetCore Team
// TDD — CR-74 (TC-CR74-FE-01 / TC-CR74-FE-02): 4 màn chi tiết nhận **403 in-envelope**.
//
// BỐI CẢNH (P0 trong STATE): KTV MỞ ĐƯỢC phiếu người khác nhưng bấm "đính ảnh" mới
// báo "Không có quyền" — read-vs-write gate lệch. CR-74 đóng phía BE (1 predicate cho
// list ⇔ detail ⇔ mutate); phía FE phải KHÔNG BAO GIỜ chào CTA trên phiếu đã bị từ
// chối đọc (dead-control), và phải hiện MESSAGE THẬT của server.
//
// 3 điều khoá cho CẢ 4 màn (PM · CM · Hiệu chuẩn · Sự cố):
//   (a) message envelope hiện trên DOM (không trang trắng, không 'Lỗi không xác định');
//   (b) KHÔNG logout / KHÔNG router.push('/login') — 403 in-envelope ≠ hết phiên
//       (dispatcher-403/401 mới là hết phiên, do axios interceptor xử lý);
//   (c) 0 CTA render.
// + nhánh 200 vẫn render CTA như cũ ⇒ chứng minh (c) không ẩn nhầm ở phiếu hợp lệ.
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
// Persona ĐỦ MỌI QUYỀN capability — chứng minh nút bị ẩn LÀ DO 403 của bản ghi,
// không phải do thiếu capability (nếu gate bằng capability thì test này vô nghĩa).
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))
const logoutSpy = vi.fn()
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    isSystemAdmin: false,
    user: { name: 'ktv@benhvien.vn' },
    logout: logoutSpy,
  }),
}))

// ── Stores IMM-08 / IMM-09 (PM & CM detail đọc qua store) ────────────────────────
type WO = Record<string, unknown>
const pmWO = ref<WO | null>(null)
const pmError = ref<ApiError | null>(null)
const cmWO = ref<WO | null>(null)
const cmError = ref<ApiError | null>(null)
const pmFetch = vi.fn().mockResolvedValue(undefined)
const cmFetch = vi.fn().mockResolvedValue(undefined)

vi.mock('@/stores/imm08', () => ({
  useImm08Store: () => ({
    get currentWO() { return pmWO.value },
    loading: false,
    get error() { return pmError.value?.message ?? null },
    get lastApiError() { return pmError.value },
    get ratedCount() { return 0 },
    get checklistComplete() { return false },
    get hasMajorFailure() { return false },
    get hasMinorFailure() { return false },
    fetchWorkOrder: pmFetch,
    updateChecklistResult: vi.fn(),
    doSubmitResult: vi.fn(),
    doReportMajorFailure: vi.fn(),
    doReschedule: vi.fn(),
    doAssignTechnician: vi.fn(),
  }),
}))
vi.mock('@/stores/imm09', () => ({
  useImm09Store: () => ({
    get currentWO() { return cmWO.value },
    loading: false,
    get error() { return cmError.value?.message ?? null },
    get lastApiError() { return cmError.value },
    fetchWorkOrder: cmFetch,
    doAssignTechnician: vi.fn(),
    doConfirmInspection: vi.fn(),
    doCloseWorkOrder: vi.fn(),
  }),
}))
vi.mock('@/stores/imm11', () => ({
  useImm11Store: () => ({
    doSendToLab: vi.fn(), doReceiveCertificate: vi.fn(), doCancel: vi.fn(), doSubmit: vi.fn(),
    _captureError: vi.fn(), error: null, lastApiError: null,
  }),
}))

// ── API (Hiệu chuẩn & Sự cố đọc thẳng qua api client) ────────────────────────────
vi.mock('@/api/imm05', () => ({ uploadDocumentFile: vi.fn() }))
// importOriginal: giữ NGUYÊN các export HẰNG của module (vd RESCHEDULE_CAL_STATES /
// isRescheduleCalStatus — SSoT gate nút dời lịch) và CHỈ mock hàm gọi mạng.
vi.mock('@/api/imm11', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/imm11')>()),
  getCalibration: vi.fn(), updateCalibration: vi.fn(),
}))
vi.mock('@/api/imm00', () => ({ deleteIncident: vi.fn() }))
vi.mock('@/api/imm12', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/imm12')>()
  return {
    ...actual,
    getIncident: vi.fn(),
    acknowledgeIncident: vi.fn(), startWork: vi.fn(), resolveIncident: vi.fn(),
    closeIncident: vi.fn(), cancelIncident: vi.fn(), reopenIncident: vi.fn(),
    requestRca: vi.fn(), createRca: vi.fn(), attachIncidentPhoto: vi.fn(),
  }
})

import { getCalibration } from '@/api/imm11'
import { getIncident } from '@/api/imm12'
import { resetRouteMock, setRouteParams, routerPushSpy } from '@/test/vueRouterMock'
import PMWorkOrderDetailView from '@/views/pm/PMWorkOrderDetailView.vue'
import CMWorkOrderDetailView from '@/views/cm/CMWorkOrderDetailView.vue'
import CalibrationDetailView from '@/views/calibration/CalibrationDetailView.vue'
import IncidentDetailView from '@/views/incident/IncidentDetailView.vue'

/** Message HẰNG của BE khi thiếu quyền đọc (MSG.AUTH_FORBIDDEN qua run_rowscoped). */
const SERVER_MSG = 'Bạn không có quyền thực hiện hành động này.'

function forbidden(): ApiError {
  return new ApiError(SERVER_MSG, {
    code: ErrorCode.FORBIDDEN, httpStatus: 403, messageCode: 'AUTH-403',
    title: 'Không đủ quyền', severity: 'warning',
  })
}

const STUBS = {
  RouterLink: true, Transition: false, DateInput: true, StatusBadge: true,
  WorkflowStepper: true, RelatedRecords: true, ApproverSelect: true, SlaBreachBadge: true,
}

/** Nhãn CTA của từng màn (nhãn VI hiển thị) — 0 nhãn nào được xuất hiện khi 403. */
const PM_CTA_TESTIDS = ['cta-start', 'cta-major', 'cta-complete', 'cta-reschedule', 'cta-resume']
const CM_CTA_TESTIDS = ['cta-assign', 'cta-diagnose', 'cta-parts', 'cta-complete',
  'cta-confirm-inspection', 'cta-cannot-repair']
const CAL_CTA_LABELS = ['Bắt đầu hiệu chuẩn', 'Gửi phòng hiệu chuẩn', 'Nhận chứng chỉ',
  'Gửi duyệt', 'Hủy phiếu', 'Lưu']
const INC_CTA_LABELS = ['Tiếp nhận', 'Bắt đầu xử lý', 'Đánh dấu đã giải quyết', 'Đóng sự cố',
  'Yêu cầu phân tích nguyên nhân gốc', 'Mở lại điều tra', 'Hủy (báo nhầm)', 'Xóa']

function pmFixture(status = 'Open'): WO {
  return {
    name: 'WO-PM-2026-00042', asset_ref: 'AC-ASSET-0042', asset_name: 'Máy siêu âm',
    risk_class: 'Medium', status, pm_type: 'Preventive', wo_type: 'PM',
    due_date: '2026-06-30', is_late: false, assigned_to: 'ktv@benhvien.vn',
    assigned_to_name: 'KTV A', supervisor: '', checklist_results: [],
    overall_result: null, completion_date: null,
    allowed_transitions: ['In Progress', 'Overdue', 'Cancelled'],
  }
}

function cmFixture(status = 'Open'): WO {
  return {
    name: 'WO-RP-2026-00099', asset_ref: 'AC-ASSET-0099', asset_name: 'Máy thở CTA',
    asset_category: 'Ventilator', risk_class: 'High', serial_no: 'SN-CTA-1',
    repair_type: 'Corrective', priority: 'Urgent', status,
    allowed_transitions: ['Assigned', 'Cancelled'],
    open_datetime: '2026-06-01 08:00:00', assigned_datetime: null, completion_datetime: null,
    assigned_to: '', assigned_to_name: '', mttr_hours: null, sla_target_hours: 72,
    sla_breached: false, is_repeat_failure: false, incident_report: null, source_pm_wo: null,
    diagnosis_notes: '', root_cause_category: '', repair_summary: '', firmware_updated: false,
    firmware_change_request: null, dept_head_name: '', total_parts_cost: 0,
    spare_parts_used: [], repair_checklist: [],
  }
}

function calFixture() {
  return {
    name: 'CAL-2026-00077', asset: 'AC-ASSET-2026-00042', asset_name: 'Máy thở CTA',
    device_model: 'M1', calibration_schedule: null, calibration_type: 'In-House',
    status: 'Scheduled', scheduled_date: '2026-06-01', actual_date: null,
    technician: 'ktv@benhvien.vn', docstatus: 0, overall_result: null, measurements: [],
    allowed_transitions: ['In Progress', 'Sent to Lab', 'Cancelled'],
  }
}

function incFixture() {
  return {
    name: 'INC-2026-00077', asset: 'AC-ASSET-0077', asset_name: 'Máy thở CTA',
    incident_type: 'Device Failure', severity: 'Medium', status: 'Open',
    description: 'Máy báo lỗi khi khởi động', reported_by: 'dd@benhvien.vn',
    reported_at: '2026-06-01 08:00:00', patient_affected: 0, rca_required: 0,
    scene_photos: [], allowed_transitions: ['Acknowledged', 'Cancelled'],
  }
}

beforeEach(() => {
  setActivePinia(createPinia())
  resetRouteMock()
  setRouteParams({ id: 'INC-2026-00077' })
  logoutSpy.mockClear()
  pmWO.value = null; pmError.value = null; pmFetch.mockClear()
  cmWO.value = null; cmError.value = null; cmFetch.mockClear()
  vi.mocked(getCalibration).mockReset()
  vi.mocked(getIncident).mockReset()
})

/** Không màn nào được đá người dùng về trang đăng nhập khi 403 in-envelope. */
function expectNoLogout(): void {
  expect(logoutSpy).not.toHaveBeenCalled()
  const pushed = routerPushSpy().mock.calls.map((c) => JSON.stringify(c[0]))
  expect(pushed.filter((p) => p.includes('login'))).toEqual([])
}

async function mountPm() {
  const w = mount(PMWorkOrderDetailView, {
    props: { id: 'WO-PM-2026-00042' }, global: { stubs: STUBS },
  })
  await flushPromises()
  return w
}
async function mountCm() {
  const w = mount(CMWorkOrderDetailView, {
    props: { id: 'WO-RP-2026-00099' }, global: { stubs: STUBS },
  })
  await flushPromises()
  return w
}
async function mountCal() {
  const w = mount(CalibrationDetailView, {
    props: { id: 'CAL-2026-00077' }, global: { stubs: STUBS },
  })
  await flushPromises()
  return w
}
async function mountInc() {
  const w = mount(IncidentDetailView, { global: { stubs: STUBS } })
  await flushPromises()
  return w
}

describe('CR-74 · TC-CR74-FE-01 — 403 in-envelope: message thật + 0 CTA + KHÔNG logout', () => {
  it('IMM-08 phiếu bảo trì định kỳ', async () => {
    pmError.value = forbidden()
    const w = await mountPm()

    const box = w.find('[data-testid="detail-load-error"]')
    expect(box.exists()).toBe(true)
    expect(box.attributes('data-kind')).toBe('forbidden')
    expect(w.text()).toContain(SERVER_MSG)
    expect(w.text()).not.toContain('Lỗi không xác định')
    for (const id of PM_CTA_TESTIDS) expect(w.find(`[data-testid="${id}"]`).exists()).toBe(false)
    // Thử lại vô nghĩa với 403 ⇒ không được chào.
    expect(w.text()).not.toContain('Thử lại')
    expectNoLogout()
  })

  it('IMM-09 lệnh sửa chữa (đóng P0 read-vs-write: 0 CTA ⇒ không có đường bấm rồi mới báo lỗi)', async () => {
    cmError.value = forbidden()
    const w = await mountCm()

    const box = w.find('[data-testid="detail-load-error"]')
    expect(box.exists()).toBe(true)
    expect(box.attributes('data-kind')).toBe('forbidden')
    expect(w.text()).toContain(SERVER_MSG)
    for (const id of CM_CTA_TESTIDS) expect(w.find(`[data-testid="${id}"]`).exists()).toBe(false)
    expectNoLogout()
  })

  it('IMM-11 phiếu hiệu chuẩn', async () => {
    vi.mocked(getCalibration).mockRejectedValue(forbidden())
    const w = await mountCal()

    const box = w.find('[data-testid="detail-load-error"]')
    expect(box.exists()).toBe(true)
    expect(box.attributes('data-kind')).toBe('forbidden')
    expect(w.text()).toContain(SERVER_MSG)
    const labels = w.findAll('button').map((b) => b.text())
    for (const l of CAL_CTA_LABELS) expect(labels).not.toContain(l)
    expectNoLogout()
  })

  it('IMM-12 phiếu sự cố (kể cả nút "Đính ảnh hiện trường" chỉ gate theo capability)', async () => {
    vi.mocked(getIncident).mockRejectedValue(forbidden())
    const w = await mountInc()

    const box = w.find('[data-testid="detail-load-error"]')
    expect(box.exists()).toBe(true)
    expect(box.attributes('data-kind')).toBe('forbidden')
    expect(w.text()).toContain(SERVER_MSG)
    const labels = w.findAll('button').map((b) => b.text())
    for (const l of INC_CTA_LABELS) expect(labels).not.toContain(l)
    expect(w.find('[aria-label="Đính ảnh hiện trường (JPG hoặc PNG)"]').exists()).toBe(false)
    expect(w.find('input[type="file"]').exists()).toBe(false)
    expectNoLogout()
  })
})

describe('CR-74 · TC-CR74-FE-02 — 200 hợp lệ: CTA render như cũ (không ẩn nhầm)', () => {
  it('IMM-08: phiếu Open + allowed_transitions ⇒ có CTA "Bắt đầu bảo trì"', async () => {
    pmWO.value = pmFixture('Open')
    const w = await mountPm()
    expect(w.find('[data-testid="detail-load-error"]').exists()).toBe(false)
    expect(w.find('[data-testid="cta-start"]').exists()).toBe(true)
  })

  it('IMM-09: phiếu Open + allowed_transitions ⇒ có CTA "Phân công kỹ thuật viên"', async () => {
    cmWO.value = cmFixture('Open')
    const w = await mountCm()
    expect(w.find('[data-testid="detail-load-error"]').exists()).toBe(false)
    expect(w.find('[data-testid="cta-assign"]').exists()).toBe(true)
  })

  it('IMM-11: phiếu Scheduled ⇒ có CTA "Bắt đầu hiệu chuẩn"', async () => {
    vi.mocked(getCalibration).mockResolvedValue(calFixture() as never)
    const w = await mountCal()
    expect(w.find('[data-testid="detail-load-error"]').exists()).toBe(false)
    expect(w.findAll('button').map((b) => b.text())).toContain('Bắt đầu hiệu chuẩn')
  })

  it('IMM-12: phiếu Open ⇒ có CTA "Tiếp nhận" + nút đính ảnh', async () => {
    vi.mocked(getIncident).mockResolvedValue(incFixture() as never)
    const w = await mountInc()
    expect(w.find('[data-testid="detail-load-error"]').exists()).toBe(false)
    expect(w.findAll('button').map((b) => b.text())).toContain('Tiếp nhận')
    expect(w.find('[aria-label="Đính ảnh hiện trường (JPG hoặc PNG)"]').exists()).toBe(true)
  })
})
