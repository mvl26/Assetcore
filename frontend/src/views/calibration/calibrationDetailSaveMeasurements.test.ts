// Copyright (c) 2026, AssetCore Team
// TDD (FE regression guard) — IMM-11: persist phép đo nhập trên web + pass_fail SERVER.
//
// Bug gốc (RED): CalibrationDetailView.save() gửi cả form nhưng BE update_calibration
// lọc theo _UPDATE_ALLOWED (KHÔNG có 'measurements') ⇒ dòng đo KTV nhập BỐC HƠI khi
// reload. Fix FE: save() đính `measurements` (raw-only) vào patch updateCalibration;
// sau Lưu refetch get_calibration để render pass_fail/out_of_tolerance do SERVER tính.
//
// Test khoá 3 bất biến:
//   1. save() gọi updateCalibration KÈM mảng measurements = CHỈ raw field
//      (KHÔNG pass_fail / out_of_tolerance — không tin badge client).
//   2. sau Lưu → refetch get_calibration (load gọi lần 2).
//   3. render pass_fail do SERVER (authoritative) — dòng in-tolerance mà server trả
//      'Fail' vẫn hiển thị 'Không đạt' (KHÔNG dùng preview computeResult client).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn() }),
}))
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ success: vi.fn(), warning: vi.fn() }),
}))
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))
vi.mock('@/stores/imm11', () => ({
  useImm11Store: () => ({
    doSendToLab: vi.fn(), doReceiveCertificate: vi.fn(), doCancel: vi.fn(), doSubmit: vi.fn(),
    _captureError: vi.fn(), error: null, lastApiError: null,
  }),
}))
vi.mock('@/api/imm05', () => ({ uploadDocumentFile: vi.fn() }))
// importOriginal: giữ NGUYÊN các export HẰNG của module (vd RESCHEDULE_CAL_STATES /
// isRescheduleCalStatus — SSoT gate nút dời lịch) và CHỈ mock hàm gọi mạng.
vi.mock('@/api/imm11', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/imm11')>()),
  getCalibration: vi.fn(), updateCalibration: vi.fn(),
}))

import { getCalibration, updateCalibration } from '@/api/imm11'
import CalibrationDetailView from './CalibrationDetailView.vue'

const stubs = { DateInput: true, StatusBadge: true, WorkflowStepper: true }

// status 'In Progress' ⇒ allowed chứa RESULT_STATES ⇒ canEnterResults=true (hiện bảng
// nhập đo + nút "Lưu"). docstatus=0.
function cal(measurements: Record<string, unknown>[]) {
  return {
    name: 'CAL-2026-00088', asset: 'AC-ASSET-2026-00042', asset_name: 'Máy thở',
    device_model: 'M1', calibration_schedule: null,
    calibration_type: 'In-House', status: 'In Progress',
    scheduled_date: '2026-06-01', actual_date: null, technician: 'ktv@benhvien.vn',
    technician_name: 'KTV A', assigned_by: null,
    lab_supplier: null, lab_accreditation_number: null, lab_contract_ref: null,
    sent_date: null, sent_by: null, certificate_file: null, certificate_date: null,
    certificate_number: null, next_calibration_date: null, overall_result: null,
    reference_standard_serial: 'REF-STD-01', traceability_reference: null,
    measurements, pm_work_order: null, capa_record: null,
    is_recalibration: 0, calibration_sticker_attached: 0, sticker_photo: null,
    technician_notes: null, amendment_reason: null,
    docstatus: 0,
    allowed_transitions: ['Passed', 'Failed', 'Conditionally Passed', 'Cancelled'],
  }
}

// Dòng KTV đã nhập (kèm pass_fail/out_of_tolerance client cũ — PHẢI bị strip khi gửi).
const ENTERED = [
  {
    parameter_name: 'Áp lực', unit: 'cmH₂O', nominal_value: 20,
    tolerance_positive: 5, tolerance_negative: 5, measured_value: 20.4,
    pass_fail: 'Pass', out_of_tolerance: 0,
  },
  {
    parameter_name: 'Lưu lượng', unit: 'L/phút', nominal_value: 10,
    tolerance_positive: 10, tolerance_negative: 10, measured_value: 9.5,
    pass_fail: 'Pass', out_of_tolerance: 0,
  },
]

// Dòng SERVER trả sau reload — Áp lực trong ±5% (preview client = 'Pass') NHƯNG server
// tính 'Fail' ⇒ chứng minh render dùng giá trị SERVER, KHÔNG preview computeResult.
const RELOADED = [
  {
    parameter_name: 'Áp lực', unit: 'cmH₂O', nominal_value: 20,
    tolerance_positive: 5, tolerance_negative: 5, measured_value: 20.4,
    pass_fail: 'Fail', out_of_tolerance: 1,
  },
  {
    parameter_name: 'Lưu lượng', unit: 'L/phút', nominal_value: 10,
    tolerance_positive: 10, tolerance_negative: 10, measured_value: 9.5,
    pass_fail: 'Pass', out_of_tolerance: 0,
  },
]

const RAW_KEYS = [
  'measured_value', 'nominal_value', 'parameter_name',
  'tolerance_negative', 'tolerance_positive', 'unit',
]

async function mountAndSave() {
  vi.mocked(getCalibration)
    .mockResolvedValueOnce(cal(ENTERED) as never)   // mount
    .mockResolvedValueOnce(cal(RELOADED) as never)  // refetch sau Lưu
  vi.mocked(updateCalibration).mockResolvedValue({ name: 'CAL-2026-00088', status: 'In Progress' } as never)
  const w = mount(CalibrationDetailView, { props: { id: 'CAL-2026-00088' }, global: { stubs } })
  await flushPromises()
  const saveBtn = w.findAll('button').find((b) => b.text().trim() === 'Lưu')
  await saveBtn!.trigger('click')
  await flushPromises()
  return w
}

beforeEach(() => vi.clearAllMocks())

describe('IMM-11 save measurements — persist + raw-only + server pass_fail', () => {
  it('save() gọi updateCalibration KÈM mảng measurements 2 dòng (không mất dữ liệu)', async () => {
    await mountAndSave()
    expect(updateCalibration).toHaveBeenCalledTimes(1)
    const patch = vi.mocked(updateCalibration).mock.calls[0][1]
    expect(Array.isArray(patch.measurements)).toBe(true)
    expect(patch.measurements).toHaveLength(2)
    expect(patch.measurements![0].parameter_name).toBe('Áp lực')
    expect(patch.measurements![1].parameter_name).toBe('Lưu lượng')
  })

  it('measurements gửi đi CHỈ raw field — KHÔNG pass_fail / out_of_tolerance client', async () => {
    await mountAndSave()
    const patch = vi.mocked(updateCalibration).mock.calls[0][1]
    for (const m of patch.measurements!) {
      expect(Object.keys(m).sort()).toEqual(RAW_KEYS)
      expect(m).not.toHaveProperty('pass_fail')
      expect(m).not.toHaveProperty('out_of_tolerance')
    }
  })

  it('sau Lưu → refetch get_calibration (load lần 2) để lấy kết quả server', async () => {
    await mountAndSave()
    // 1 lần mount + 1 lần reload sau save.
    expect(getCalibration).toHaveBeenCalledTimes(2)
  })

  it('render pass_fail do SERVER (authoritative) — dòng in-tolerance server Fail vẫn "Không đạt"', async () => {
    const w = await mountAndSave()
    const labels = w.findAll('span')
      .map((s) => s.text().trim())
      .filter((t) => t === 'Đạt' || t === 'Không đạt')
    // Áp lực: server 'Fail' (dù measured 20.4 nằm trong ±5% ⇒ preview client sẽ 'Pass').
    // Lưu lượng: server 'Pass'. Thứ tự theo dòng.
    expect(labels).toEqual(['Không đạt', 'Đạt'])
  })

  it('reload giữ ĐÚNG 2 dòng đo (không bốc hơi) — 2 ô nhập measured_value', async () => {
    const w = await mountAndSave()
    expect(w.findAll('input[step="any"]')).toHaveLength(2)
  })
})
