// Copyright (c) 2026, AssetCore Team
//
// IMM-11 — CalibrationDetailView: nút workflow gate theo SSoT `allowed_transitions`
// (BE _CAL_VALID_TRANSITIONS, imm11.py). Khoá hành vi "mỗi trạng thái CHỈ lộ đúng
// hành động-kế hợp lệ" + chống regression bug "quá nhiều nút / trộn luồng
// In-House↔External" (Gửi duyệt disabled-tooltip lộ ở Scheduled; bảng nhập tham số
// đo + Hủy phiếu lộ sai pha). Capability để TRUE để cô lập chiều allowed_transitions.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))
vi.mock('@/composables/useCapabilities', () => ({ useCapabilities: () => ({ can: () => true }) }))
vi.mock('@/composables/useNotify', () => ({ useNotify: () => ({ show: vi.fn(), fromError: vi.fn() }) }))
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ success: vi.fn(), warning: vi.fn() }) }))
vi.mock('@/stores/imm11', () => ({
  useImm11Store: () => ({
    doSendToLab: vi.fn(), doReceiveCertificate: vi.fn(), doCancel: vi.fn(), doSubmit: vi.fn(),
    _captureError: vi.fn(), error: null, lastApiError: null,
  }),
}))
vi.mock('@/api/imm05', () => ({ uploadDocumentFile: vi.fn() }))
vi.mock('@/api/imm11', () => ({ getCalibration: vi.fn(), updateCalibration: vi.fn() }))

import { getCalibration } from '@/api/imm11'
import CalibrationDetailView from './CalibrationDetailView.vue'

const stubs = { DateInput: true, StatusBadge: true, WorkflowStepper: true }

function cal(overrides: Record<string, unknown> = {}) {
  return {
    name: 'CAL-2026-00001', asset: 'AC-ASSET-2026-00001', asset_name: 'Máy thở',
    device_model: 'M1', calibration_schedule: null,
    calibration_type: 'In-House', status: 'Scheduled',
    scheduled_date: '2026-06-01', actual_date: null, technician: 't@x.vn',
    technician_name: 'KTV A', assigned_by: null,
    lab_supplier: null, lab_accreditation_number: null, lab_contract_ref: null,
    sent_date: null, sent_by: null, certificate_file: null, certificate_date: null,
    certificate_number: null, next_calibration_date: null, overall_result: null,
    reference_standard_serial: null, traceability_reference: null,
    measurements: [], pm_work_order: null, capa_record: null,
    is_recalibration: 0, calibration_sticker_attached: 0, sticker_photo: null,
    technician_notes: null, amendment_reason: null,
    docstatus: 0, allowed_transitions: [] as string[],
    ...overrides,
  }
}

async function render(fixture: Record<string, unknown>) {
  vi.mocked(getCalibration).mockResolvedValue(fixture as never)
  const w = mount(CalibrationDetailView, { props: { id: 'CAL-2026-00001' }, global: { stubs } })
  await flushPromises()
  return w
}

function hasBtn(w: Awaited<ReturnType<typeof render>>, txt: string) {
  return w.findAll('button').some(b => b.text().includes(txt))
}

const START = 'Bắt đầu hiệu chuẩn'
const SEND_LAB = 'Gửi phòng hiệu chuẩn'
const RECV_CERT = 'Nhận chứng chỉ'
const CANCEL = 'Hủy phiếu'
const SUBMIT = 'Gửi duyệt'
const SAVE = 'Lưu'
const ADD_MEASURE = '+ Thêm tham số'

describe('CalibrationDetailView — nút workflow theo SSoT allowed_transitions', () => {
  beforeEach(() => vi.clearAllMocks())

  it('Scheduled / Nội bộ → Bắt đầu + Hủy + Lưu; KHÔNG Gửi-lab, KHÔNG Gửi duyệt, KHÔNG nhập đo', async () => {
    const w = await render(cal({
      calibration_type: 'In-House', status: 'Scheduled',
      allowed_transitions: ['In Progress', 'Sent to Lab', 'Cancelled'],
    }))
    expect(hasBtn(w, START)).toBe(true)
    expect(hasBtn(w, CANCEL)).toBe(true)
    expect(hasBtn(w, SAVE)).toBe(true)
    expect(hasBtn(w, SEND_LAB)).toBe(false)   // nội bộ → không gửi lab
    expect(hasBtn(w, SUBMIT)).toBe(false)     // KEY: hết "Gửi duyệt" disabled ở Scheduled
    expect(hasBtn(w, ADD_MEASURE)).toBe(false)
  })

  it('Scheduled / Bên ngoài → Bắt đầu + Gửi-lab + Hủy + Lưu; KHÔNG Gửi duyệt', async () => {
    const w = await render(cal({
      calibration_type: 'External', status: 'Scheduled',
      allowed_transitions: ['In Progress', 'Sent to Lab', 'Cancelled'],
    }))
    expect(hasBtn(w, START)).toBe(true)
    expect(hasBtn(w, SEND_LAB)).toBe(true)
    expect(hasBtn(w, CANCEL)).toBe(true)
    expect(hasBtn(w, SAVE)).toBe(true)
    expect(hasBtn(w, SUBMIT)).toBe(false)     // KEY
    expect(hasBtn(w, RECV_CERT)).toBe(false)
  })

  it('In Progress → Gửi duyệt + Hủy + Lưu + nhập tham số đo; KHÔNG Bắt đầu/Gửi-lab', async () => {
    const w = await render(cal({
      calibration_type: 'In-House', status: 'In Progress',
      allowed_transitions: ['Passed', 'Failed', 'Conditionally Passed', 'Cancelled'],
    }))
    expect(hasBtn(w, SUBMIT)).toBe(true)      // KEY: chỉ pha thực hiện mới gửi duyệt
    expect(hasBtn(w, ADD_MEASURE)).toBe(true)
    expect(hasBtn(w, CANCEL)).toBe(true)
    expect(hasBtn(w, SAVE)).toBe(true)
    expect(hasBtn(w, START)).toBe(false)
    expect(hasBtn(w, SEND_LAB)).toBe(false)
  })

  it('Sent to Lab → chỉ Nhận chứng chỉ + Lưu; KHÔNG Hủy (state machine không cho)', async () => {
    const w = await render(cal({
      calibration_type: 'External', status: 'Sent to Lab',
      allowed_transitions: ['Certificate Received'],
    }))
    expect(hasBtn(w, RECV_CERT)).toBe(true)
    expect(hasBtn(w, SAVE)).toBe(true)
    expect(hasBtn(w, CANCEL)).toBe(false)     // KEY: Sent to Lab → [Certificate Received] only
    expect(hasBtn(w, SEND_LAB)).toBe(false)
    expect(hasBtn(w, SUBMIT)).toBe(false)
    expect(hasBtn(w, ADD_MEASURE)).toBe(false)
  })

  it('Certificate Received → Gửi duyệt + nhập tham số đo + Lưu; KHÔNG Nhận chứng chỉ/Hủy', async () => {
    const w = await render(cal({
      calibration_type: 'External', status: 'Certificate Received',
      allowed_transitions: ['Passed', 'Failed', 'Conditionally Passed'],
    }))
    expect(hasBtn(w, SUBMIT)).toBe(true)      // KEY
    expect(hasBtn(w, ADD_MEASURE)).toBe(true)
    expect(hasBtn(w, SAVE)).toBe(true)
    expect(hasBtn(w, RECV_CERT)).toBe(false)
    expect(hasBtn(w, CANCEL)).toBe(false)     // Cert Received → không có Cancelled
  })

  it('Đã gửi duyệt (Passed, docstatus=1) → read-only: KHÔNG Lưu/Gửi duyệt/nhập đo', async () => {
    const w = await render(cal({
      status: 'Passed', overall_result: 'Passed', docstatus: 1, allowed_transitions: [],
    }))
    expect(hasBtn(w, SAVE)).toBe(false)
    expect(hasBtn(w, SUBMIT)).toBe(false)
    expect(hasBtn(w, ADD_MEASURE)).toBe(false)
    expect(hasBtn(w, START)).toBe(false)
    expect(hasBtn(w, CANCEL)).toBe(false)
  })

  it('Failed đã submit (docstatus=1, allowed=[Conditionally Passed]) → KHÔNG nhập đo/Gửi duyệt (guard !isSubmitted)', async () => {
    // Edge: phiếu Failed sau submit vẫn còn allowed=[Conditionally Passed] (luồng sửa
    // đổi Compliance Manager). canEnterResults PHẢI false vì isSubmitted — nếu chỉ
    // dựa allowed_transitions.includes('Conditionally Passed') sẽ lộ nhầm bảng nhập đo.
    const w = await render(cal({
      status: 'Failed', overall_result: 'Failed', docstatus: 1,
      allowed_transitions: ['Conditionally Passed'],
    }))
    expect(hasBtn(w, SUBMIT)).toBe(false)     // KEY edge guard
    expect(hasBtn(w, ADD_MEASURE)).toBe(false)
    expect(hasBtn(w, SAVE)).toBe(false)
  })
})
