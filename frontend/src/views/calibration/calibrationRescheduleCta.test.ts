// Copyright (c) 2026, AssetCore Team
// TDD FE — AC-CR-86 «Dời lịch hiệu chuẩn» (IMM-11).
//
// FE-11 (render gate): nút `cta-reschedule-calibration` render THEO HẰNG SSoT
//   `RESCHEDULE_CAL_STATES` (api/imm11.ts — mirror hằng cùng tên ở services/imm11.py),
//   KHÔNG hardcode `status === 'Scheduled'` rải rác. Phiếu `Passed` / `Cancelled` ⇒
//   nút VẮNG (2 ca RIÊNG, không gộp).
// FE-12 (lỗi in-envelope): envelope `{success:false, error, fields:['reason']}` ⇒ modal
//   hiện NGUYÊN VĂN câu tiếng Việt của server + gắn lỗi vào ô «Lý do dời lịch»;
//   KHÔNG phơi chuỗi kỹ thuật (mã lỗi/traceback/tên capability).
// GATE-6c (chống dead-control): param phát đi tới store == đúng lựa chọn trên UI.
//
// Dời lịch KHÔNG phải transition (status GIỮ NGUYÊN) ⇒ cố ý KHÔNG gate bằng
// `allowed_transitions` — fixture dưới đây đặt allowed_transitions=[] để chứng minh
// nút vẫn hiện đúng theo hằng SSoT (và ngược lại không lọt vào bộ nút transition của
// calibrationDetailCtaGating.test.ts).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn() }),
}))
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ success: vi.fn(), warning: vi.fn() }),
}))

let canImpl: (c: string) => boolean = () => true
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: (c: string) => canImpl(c) }),
}))

const storeMock = vi.hoisted(() => ({
  doReschedule: vi.fn(),
  doSendToLab: vi.fn(), doReceiveCertificate: vi.fn(), doCancel: vi.fn(), doSubmit: vi.fn(),
  _captureError: vi.fn(),
  error: null as string | null,
  lastApiError: null as unknown,
}))
vi.mock('@/stores/imm11', () => ({ useImm11Store: () => storeMock }))
vi.mock('@/api/imm05', () => ({ uploadDocumentFile: vi.fn() }))
// importOriginal: GIỮ hằng thật RESCHEDULE_CAL_STATES / isRescheduleCalStatus (SSoT),
// chỉ mock hàm gọi mạng — nếu mock cứng hằng ở đây thì test tự nói dối khi BE đổi tập.
vi.mock('@/api/imm11', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/imm11')>()),
  getCalibration: vi.fn(), updateCalibration: vi.fn(),
}))

import { getCalibration, RESCHEDULE_CAL_STATES } from '@/api/imm11'
import { ApiError, ErrorCode } from '@/api/errors'
import DateInput from '@/components/common/DateInput.vue'
import CalibrationDetailView from './CalibrationDetailView.vue'

const CTA = '[data-testid="cta-reschedule-calibration"]'
const stubs = { DateInput: true, StatusBadge: true, WorkflowStepper: true, RelatedRecords: true }

/** Mọi status của DocType IMM Asset Calibration (khớp union AssetCalibration['status']). */
const ALL_STATUSES = [
  'Scheduled', 'Sent to Lab', 'In Progress', 'Certificate Received',
  'Passed', 'Failed', 'Conditionally Passed', 'Cancelled',
] as const

function cal(over: Record<string, unknown> = {}) {
  return {
    name: 'CAL-2026-00099', asset: 'AC-ASSET-2026-00042', asset_name: 'Máy thở CTA',
    device_model: 'M1', calibration_schedule: null,
    calibration_type: 'In-House', status: 'Scheduled',
    scheduled_date: '2026-08-01', actual_date: null, technician: 'ktv@benhvien.vn',
    technician_name: 'KTV A', assigned_by: null,
    lab_supplier: null, lab_accreditation_number: null, lab_contract_ref: null,
    sent_date: null, sent_by: null, certificate_file: null, certificate_date: null,
    certificate_number: null, next_calibration_date: null, overall_result: null,
    reference_standard_serial: null, traceability_reference: null,
    measurements: [], pm_work_order: null, capa_record: null,
    is_recalibration: 0, calibration_sticker_attached: 0, sticker_photo: null,
    technician_notes: null, amendment_reason: null,
    docstatus: 0,
    allowed_transitions: [],
    ...over,
  }
}

async function mountView(fixture: Record<string, unknown>) {
  vi.mocked(getCalibration).mockResolvedValue(fixture as never)
  const w = mount(CalibrationDetailView, { props: { id: 'CAL-2026-00099' }, global: { stubs } })
  await flushPromises()
  return w
}
type ViewWrapper = Awaited<ReturnType<typeof mountView>>

/** Mở modal dời lịch + set ngày mới qua DateInput (v-model) — mô phỏng thao tác thật. */
async function openModal(w: ViewWrapper, newDate?: string) {
  await w.find(CTA).trigger('click')
  if (newDate !== undefined) {
    const di = w.findAllComponents(DateInput).find(c => c.props('id') === 'cal-reschedule-date')
    expect(di, 'ô ngày trong modal dời lịch phải tồn tại').toBeTruthy()
    await di!.setValue(newDate)
  }
  return w
}

beforeEach(() => {
  vi.clearAllMocks()
  canImpl = () => true
  storeMock.error = null
  storeMock.lastApiError = null
})

describe('FE-11 — render gate nút «Dời lịch hiệu chuẩn» theo hằng SSoT', () => {
  it('phiếu Scheduled ⇒ DOM CÓ nút cta-reschedule-calibration', async () => {
    const w = await mountView(cal({ status: 'Scheduled' }))
    expect(w.find(CTA).exists()).toBe(true)
    expect(w.find(CTA).text()).toBe('Dời lịch hiệu chuẩn')
  })

  it('phiếu Passed ⇒ DOM KHÔNG chứa nút', async () => {
    const w = await mountView(cal({ status: 'Passed', overall_result: 'Passed', docstatus: 1 }))
    expect(w.find(CTA).exists()).toBe(false)
  })

  it('phiếu Cancelled ⇒ DOM KHÔNG chứa nút', async () => {
    const w = await mountView(cal({ status: 'Cancelled' }))
    expect(w.find(CTA).exists()).toBe(false)
  })

  it('tập status hiện nút KHỚP CHÍNH XÁC RESCHEDULE_CAL_STATES (một nguồn duy nhất)', async () => {
    const shown: string[] = []
    for (const status of ALL_STATUSES) {
      const w = await mountView(cal({ status }))
      if (w.find(CTA).exists()) shown.push(status)
    }
    expect(shown.sort()).toEqual([...RESCHEDULE_CAL_STATES].sort())
  })

  it('phiếu đã submit (docstatus=1) ⇒ ẩn nút dù status thuộc tập cho phép', async () => {
    const w = await mountView(cal({ status: 'In Progress', docstatus: 1 }))
    expect(w.find(CTA).exists()).toBe(false)
  })

  it('thiếu capability calibration.write ⇒ ẩn nút (mirror cap-gate service)', async () => {
    canImpl = (c: string) => c !== 'calibration.write'
    const w = await mountView(cal({ status: 'Scheduled' }))
    expect(w.find(CTA).exists()).toBe(false)
  })
})

describe('AC-CR-86 — modal dời lịch: param phát đi == lựa chọn trên UI (GATE-6c)', () => {
  it('nhập ngày mới + lý do hợp lệ ⇒ store.doReschedule nhận ĐÚNG (id, ngày UI, lý do UI đã trim)', async () => {
    storeMock.doReschedule.mockResolvedValue({
      name: 'CAL-2026-00099', old_date: '2026-08-01', new_date: '2026-08-08', status: 'Scheduled',
    })
    const w = await mountView(cal({ status: 'Scheduled' }))
    await openModal(w, '2026-08-08')
    await w.find('#cal-reschedule-reason').setValue('  Thiết bị đang phục vụ ca bệnh  ')
    await w.find('[data-testid="reschedule-confirm"]').trigger('click')
    await flushPromises()

    expect(storeMock.doReschedule).toHaveBeenCalledTimes(1)
    expect(storeMock.doReschedule).toHaveBeenCalledWith(
      'CAL-2026-00099', '2026-08-08', 'Thiết bị đang phục vụ ca bệnh',
    )
    // Thành công ⇒ đóng modal + refetch phiếu (đọc lại từ server = SSoT)
    expect(w.find('[data-testid="reschedule-confirm"]').exists()).toBe(false)
    expect(vi.mocked(getCalibration).mock.calls.length).toBeGreaterThanOrEqual(2)
  })

  it('lý do < 5 ký tự ⇒ nút xác nhận disabled, KHÔNG gọi API', async () => {
    const w = await mountView(cal({ status: 'Scheduled' }))
    await openModal(w, '2026-08-08')
    await w.find('#cal-reschedule-reason').setValue('abc')
    const btn = w.find('[data-testid="reschedule-confirm"]')
    expect(btn.attributes('disabled')).toBeDefined()
    await btn.trigger('click')
    await flushPromises()
    expect(storeMock.doReschedule).not.toHaveBeenCalled()
  })

  it('ô ngày mới chặn quá khứ bằng min = hôm nay (chống tạo quá-hạn giả)', async () => {
    const w = await mountView(cal({ status: 'Scheduled' }))
    await openModal(w)
    const di = w.findAllComponents(DateInput).find(c => c.props('id') === 'cal-reschedule-date')
    const today = new Date()
    const iso = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
    expect(di!.props('min')).toBe(iso)
  })
})

describe('FE-12 — lỗi in-envelope hiển thị nguyên văn VI + gắn đúng ô', () => {
  const VI_MSG = 'Lý do dời lịch phải có ít nhất 5 ký tự.'

  async function failWith(err: ApiError, fixture = cal({ status: 'Scheduled' })) {
    storeMock.doReschedule.mockImplementation(async () => {
      storeMock.error = err.message
      storeMock.lastApiError = err
      return null
    })
    const w = await mountView(fixture)
    await openModal(w, '2026-08-08')
    await w.find('#cal-reschedule-reason').setValue('Lý do hợp lệ đủ dài')
    await w.find('[data-testid="reschedule-confirm"]').trigger('click')
    await flushPromises()
    return w
  }

  it('fields dạng LIST ["reason"] ⇒ câu VI nguyên văn gắn vào ô «Lý do dời lịch»', async () => {
    const err = new ApiError(VI_MSG, {
      code: ErrorCode.VALIDATION_ERROR, httpStatus: 422,
      fields: ['reason'] as unknown as Record<string, string>,
    })
    const w = await failWith(err)
    expect(w.find('[data-testid="reschedule-error-reason"]').text()).toBe(VI_MSG)
    expect(w.find('[data-testid="reschedule-error"]').text()).toBe(VI_MSG)
    // modal KHÔNG đóng khi lỗi (giữ nguyên nội dung user đã nhập)
    expect(w.find('[data-testid="reschedule-confirm"]').exists()).toBe(true)
    // ô ngày KHÔNG bị gắn lỗi oan
    expect(w.find('[data-testid="reschedule-error-new_date"]').exists()).toBe(false)
    // a11y: lỗi gắn vào ô qua aria-describedby + aria-invalid
    const reason = w.find('#cal-reschedule-reason')
    expect(reason.attributes('aria-invalid')).toBe('true')
    expect(reason.attributes('aria-describedby')).toBe('cal-reschedule-reason-err')
  })

  it('fields dạng DICT {new_date: msg} ⇒ gắn vào ô «Ngày hiệu chuẩn mới»', async () => {
    const msg = 'Ngày hiệu chuẩn mới không được nằm trong quá khứ.'
    const err = new ApiError(msg, {
      code: ErrorCode.VALIDATION_ERROR, httpStatus: 422, fields: { new_date: msg },
    })
    const w = await failWith(err)
    expect(w.find('[data-testid="reschedule-error-new_date"]').text()).toBe(msg)
    expect(w.find('[data-testid="reschedule-error-reason"]').exists()).toBe(false)
  })

  it('lỗi BAD_STATE / FORBIDDEN ⇒ hiện câu VI, KHÔNG phơi mã kỹ thuật hay tên capability', async () => {
    const msg = 'Không thể dời lịch phiếu đã hoàn tất hoặc đã hủy.'
    const w = await failWith(new ApiError(msg, { code: ErrorCode.BAD_STATE, httpStatus: 409 }))
    const banner = w.find('[data-testid="reschedule-error"]')
    expect(banner.text()).toBe(msg)
    const dom = w.html()
    for (const leak of ['BAD_STATE', 'FORBIDDEN', 'Traceback', 'calibration.write', 'ServiceError']) {
      expect(dom).not.toContain(leak)
    }
  })
})
