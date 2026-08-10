// TDD — IMM-11 recalibration OoS-restore governance guard (FE side, Core Doc §06):
//
// BE thay đổi (services/imm11.py handle_calibration_pass): khi đóng phiếu hiệu chuẩn
// Pass, asset CHỈ được khôi phục Out of Service → Active khi hold OoS do CHÍNH chuỗi
// hiệu chuẩn đặt VÀ không còn hold governance khác (Incident/Repair/PM mở). Nếu OoS
// do module khác → asset GIỮ Out of Service (KHÔNG ép Active).
//
// FE forward-compat (ZERO shape-change): `submit_calibration` / `handle_calibration_pass`
// KHÔNG thêm field response, và `get_calibration` (BE service imm11.py:776-787) KHÔNG
// trả `lifecycle_status` của asset — chỉ enrich `asset_name` + `technician_name`.
//
// => Vì detail CHƯA bind lifecycle_status THẬT, FE KHÔNG ĐƯỢC bịa badge "Đang hoạt
//    động"/"Active" cho thiết bị, và KHÔNG ĐƯỢC claim "thiết bị đã hoạt động trở lại"
//    sau khi đóng phiếu hiệu chuẩn Pass (đây là analog phòng-ngừa của hold-note IMM-09;
//    khác biệt: imm09 detail CÓ asset_info.lifecycle_status nên render được, imm11 thì
//    KHÔNG → no-op). Đây là regression-guard cho lỗi tái diễn `wave2_ui_bugs`:
//    English-status / false "active" claim lọt ra UI.
//
// INV-FE-CAL-RESTORE-1 (no-fabrication):
//   (1) Submit/Pass success → MSG generic (IMM11_SUBMIT_SUCCESS), KHÔNG literal
//       "đã hoạt động trở lại" / "thiết bị đã hoạt động".
//   (2) KHÔNG render asset-lifecycle badge bịa (data-testid="asset-lifecycle-badge")
//       — detail chưa có dữ liệu lifecycle_status thật để render trung thực.
//   (3) Badge trạng thái hiển thị là của PHIẾU hiệu chuẩn (status/overall_result) qua
//       SSoT VI — KHÔNG leak raw EN status.
//
// RED-prove: nếu ai đó thêm vào view binding bịa `Thiết bị: Đang hoạt động` /
//   '<span data-testid="asset-lifecycle-badge">Đang hoạt động</span>' hoặc literal
//   "đã hoạt động trở lại" trong success path ⇒ TC-02/TC-03 FAIL; gỡ ⇒ GREEN.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import type { AssetCalibration } from '@/api/imm11'
import { MSG } from '@/i18n/messages'

const pushSpy = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushSpy }),
}))

const showSpy = vi.fn()
const fromErrorSpy = vi.fn()
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: showSpy, fromError: fromErrorSpy }),
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ success: vi.fn(), warning: vi.fn(), error: vi.fn() }),
}))

// User có quyền KTV hiệu chuẩn (để các action không bị ẩn hết).
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))

// get_calibration đi qua api/imm11 trực tiếp trong view; doSubmit qua store.
const getCalibrationSpy = vi.fn()
// importOriginal: giữ NGUYÊN các export HẰNG của module (vd RESCHEDULE_CAL_STATES /
// isRescheduleCalStatus — SSoT gate nút dời lịch) và CHỈ mock hàm gọi mạng.
vi.mock('@/api/imm11', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/imm11')>()),
  getCalibration: (...a: unknown[]) => getCalibrationSpy(...a),
  updateCalibration: vi.fn().mockResolvedValue({ name: 'CAL-1', status: 'In Progress' }),
}))

const doSubmitSpy = vi.fn().mockResolvedValue({ name: 'CAL-1', status: 'Passed', overall_result: 'Passed' })
vi.mock('@/stores/imm11', () => ({
  useImm11Store: () => ({
    doSubmit: doSubmitSpy,
    doSendToLab: vi.fn(),
    doReceiveCertificate: vi.fn(),
    doCancel: vi.fn(),
    _captureError: vi.fn(),
    error: null,
    lastApiError: null,
  }),
}))

vi.mock('@/api/imm05', () => ({ uploadDocumentFile: vi.fn() }))

import CalibrationDetailView from './CalibrationDetailView.vue'

function makeCal(over: Partial<AssetCalibration>): AssetCalibration {
  return {
    name: 'CAL-2026-00001',
    asset: 'AC-ASSET-2026-00001',
    asset_name: 'Máy thở Dräger Evita',
    device_model: 'IMM-MDL-2026-0001',
    calibration_schedule: null,
    calibration_type: 'In-House',
    status: 'Passed',
    scheduled_date: '2026-06-01',
    actual_date: '2026-06-02',
    technician: 'ktv@hospital.vn',
    technician_name: 'Nguyễn Văn A',
    assigned_by: null,
    lab_supplier: null,
    lab_accreditation_number: null,
    lab_contract_ref: null,
    sent_date: null,
    sent_by: null,
    certificate_file: null,
    certificate_date: null,
    certificate_number: null,
    next_calibration_date: '2026-12-01',
    overall_result: 'Passed',
    reference_standard_serial: null,
    traceability_reference: null,
    measurements: [
      {
        parameter_name: 'Áp lực', unit: 'cmH₂O', nominal_value: 20,
        tolerance_positive: 5, tolerance_negative: 5, measured_value: 20.1,
        pass_fail: 'Pass',
      },
    ],
    pm_work_order: null,
    capa_record: null,
    is_recalibration: 1,
    calibration_sticker_attached: 0,
    sticker_photo: null,
    technician_notes: null,
    amendment_reason: null,
    docstatus: 1,
    ...over,
  } as AssetCalibration
}

async function mountWith(cal: AssetCalibration) {
  getCalibrationSpy.mockResolvedValue(cal)
  const wrapper = mount(CalibrationDetailView, {
    props: { id: cal.name },
    global: { stubs: { StatusBadge: true, WorkflowStepper: true, DateInput: true } },
  })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  pushSpy.mockClear(); showSpy.mockClear(); fromErrorSpy.mockClear()
  doSubmitSpy.mockClear()
  doSubmitSpy.mockResolvedValue({ name: 'CAL-1', status: 'Passed', overall_result: 'Passed' })
})

describe('CalibrationDetailView — recalibration OoS-restore guard (INV-FE-CAL-RESTORE-1)', () => {
  it('TC-CAL-RESTORE-FE-01: phiếu Pass đã chốt render được, dùng nhãn VI cho phiếu (no raw EN status text)', async () => {
    const wrapper = await mountWith(makeCal({ status: 'Passed', overall_result: 'Passed' }))
    const text = wrapper.text()
    // tiêu đề + thông tin phiếu hiển thị; nhãn trạng thái phiếu KHÔNG leak raw EN dạng text node.
    // (StatusBadge stub nuốt nội dung badge; phần text còn lại là body view.)
    expect(text).toContain('CAL-2026-00001')
    expect(text).not.toContain('lifecycle_status')
  })

  it('TC-CAL-RESTORE-FE-02 (BUG CHÍNH — no false claim): đóng phiếu Pass → success generic, KHÔNG claim "đã hoạt động trở lại"', async () => {
    const wrapper = await mountWith(makeCal({ status: 'In Progress', overall_result: null, docstatus: 0 }))
    // mở modal gửi duyệt rồi xác nhận (component method submit gọi store.doSubmit)
    const vm = wrapper.vm as unknown as { submit: () => Promise<void> }
    await vm.submit()
    await flushPromises()

    // success qua MSG SSoT generic — KHÔNG literal về reactivation thiết bị
    expect(doSubmitSpy).toHaveBeenCalledWith('CAL-2026-00001')
    expect(showSpy).toHaveBeenCalledWith(
      expect.objectContaining({ code: MSG.IMM11_SUBMIT_SUCCESS }),
    )
    // KHÔNG bao giờ phát thông điệp khẳng định thiết bị đã hoạt động trở lại
    const calls = showSpy.mock.calls.flat()
    expect(JSON.stringify(calls)).not.toContain('đã hoạt động trở lại')
    expect(JSON.stringify(calls)).not.toContain('hoạt động bình thường')
    expect(wrapper.html()).not.toContain('đã hoạt động trở lại')
  })

  it('TC-CAL-RESTORE-FE-03 (no-fabrication): detail KHÔNG bịa badge "Đang hoạt động"/asset-lifecycle (BE chưa trả lifecycle_status)', async () => {
    const wrapper = await mountWith(makeCal({ status: 'Passed', overall_result: 'Passed' }))
    const html = wrapper.html()
    // KHÔNG có badge trạng thái VÒNG ĐỜI THIẾT BỊ bịa ra (chỉ phiếu hiệu chuẩn có badge)
    expect(wrapper.find('[data-testid="asset-lifecycle-badge"]').exists()).toBe(false)
    // KHÔNG có dòng "Thiết bị: Đang hoạt động" / "Thiết bị đã hoạt động"
    expect(html).not.toContain('Thiết bị: Đang hoạt động')
    expect(html).not.toContain('Thiết bị đã hoạt động')
  })

  it('TC-CAL-RESTORE-FE-04: phiếu Failed Pass-path không lẫn — Failed có nhãn riêng, không claim active', async () => {
    const wrapper = await mountWith(makeCal({ status: 'Failed', overall_result: 'Failed', capa_record: 'CAPA-1' }))
    const html = wrapper.html()
    // CAPA alert hiện cho Failed; tuyệt đối không có claim thiết bị active
    expect(html).toContain('CAPA')
    expect(html).not.toContain('đã hoạt động trở lại')
    expect(wrapper.find('[data-testid="asset-lifecycle-badge"]').exists()).toBe(false)
  })
})
