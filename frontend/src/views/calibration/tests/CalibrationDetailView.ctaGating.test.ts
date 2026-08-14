// Copyright (c) 2026, AssetCore Team
// TDD (FE regression guard) — GATE-8 / LL-FE-51: server-driven CTA cho Calibration (IMM-11).
// Pattern: cm/cmWorkOrderCtaGating.test.ts (WF-ADMIN-E2E — FE guard bổ sung).
//
// Mọi nút CHUYỂN-TRẠNG-THÁI ở CalibrationDetailView render DUY NHẤT từ
// `allowed_transitions` do BE emit (SSoT = _CAL_VALID_TRANSITIONS, services/imm11.py:58
// → get_calibration). allowed_transitions=[] ⇒ 0 nút transition DÙ status khớp nhánh
// hardcode cũ (RED 2026-06-29: hardcode `status === 'Scheduled'` lộ "Gửi duyệt" +
// bảng nhập đo sai pha — đã fix, test này KHÓA chống tái phát).
// `status ===` / `docstatus`/`calibration_type` CHỈ được giữ cho display/edit-mode UX:
//   • "Lưu" (save draft) gate `!isSubmitted && canExecuteCal` — KHÔNG phải transition.
//   • isExternal thu hẹp "Gửi phòng hiệu chuẩn" (state machine chung 2 luồng).
//   • stepper/badge theo status = display thuần.
//
// SSoT map (mirror _CAL_VALID_TRANSITIONS — key = status, value = target states):
//   Scheduled            → [In Progress, Sent to Lab, Cancelled]
//   In Progress          → [Passed, Failed, Conditionally Passed, Cancelled]
//   Sent to Lab          → [Certificate Received]
//   Certificate Received → [Passed, Failed, Conditionally Passed]
//   Failed               → [Conditionally Passed]   (luồng sửa đổi sau submit)
//   Passed / Conditionally Passed / Cancelled → []  (terminal → 0 CTA)
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn() }),
}))
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ success: vi.fn(), warning: vi.fn() }),
}))

// Capability controllable per test (mặc định: đủ mọi quyền calibration).
let canImpl: (c: string) => boolean = () => true
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: (c: string) => canImpl(c) }),
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

import { getCalibration } from '@/api/imm11'
import CalibrationDetailView from '@/views/calibration/CalibrationDetailView.vue'

// SSoT transition map (mirror _CAL_VALID_TRANSITIONS trong services/imm11.py).
const CAL_TRANSITIONS: Record<string, string[]> = {
  'Scheduled': ['In Progress', 'Sent to Lab', 'Cancelled'],
  'In Progress': ['Passed', 'Failed', 'Conditionally Passed', 'Cancelled'],
  'Sent to Lab': ['Certificate Received'],
  'Certificate Received': ['Passed', 'Failed', 'Conditionally Passed'],
  'Failed': ['Conditionally Passed'],
  'Passed': [],
  'Conditionally Passed': [],
  'Cancelled': [],
}

// 5 nút CTA transition (nhãn VI hiển thị → target state). KHÔNG gồm "Lưu"
// (save draft — edit-mode UX theo docstatus) và "Quay lại" (điều hướng).
const TRANSITION_CTA = [
  'Bắt đầu hiệu chuẩn', // → In Progress
  'Gửi phòng hiệu chuẩn', // → Sent to Lab (chỉ External)
  'Nhận chứng chỉ', // → Certificate Received
  'Gửi duyệt', // → Passed / Failed / Conditionally Passed (nhập kết quả + submit)
  'Hủy phiếu', // → Cancelled
] as const

const stubs = { DateInput: true, StatusBadge: true, WorkflowStepper: true }

function cal(over: Record<string, unknown> = {}) {
  const status = (over.status as string) ?? 'Scheduled'
  return {
    name: 'CAL-2026-00077', asset: 'AC-ASSET-2026-00042', asset_name: 'Máy thở CTA',
    device_model: 'M1', calibration_schedule: null,
    calibration_type: 'In-House', status,
    scheduled_date: '2026-06-01', actual_date: null, technician: 'ktv@benhvien.vn',
    technician_name: 'KTV A', assigned_by: null,
    lab_supplier: null, lab_accreditation_number: null, lab_contract_ref: null,
    sent_date: null, sent_by: null, certificate_file: null, certificate_date: null,
    certificate_number: null, next_calibration_date: null, overall_result: null,
    reference_standard_serial: null, traceability_reference: null,
    measurements: [], pm_work_order: null, capa_record: null,
    is_recalibration: 0, calibration_sticker_attached: 0, sticker_photo: null,
    technician_notes: null, amendment_reason: null,
    docstatus: 0,
    allowed_transitions: CAL_TRANSITIONS[status] ?? [],
    ...over,
  }
}

async function mountView(fixture: Record<string, unknown>) {
  vi.mocked(getCalibration).mockResolvedValue(fixture as never)
  const w = mount(CalibrationDetailView, { props: { id: 'CAL-2026-00077' }, global: { stubs } })
  await flushPromises()
  return w
}
type ViewWrapper = Awaited<ReturnType<typeof mountView>>

function ctasShown(w: ViewWrapper): string[] {
  const texts = w.findAll('button').map((b) => b.text().trim())
  return TRANSITION_CTA.filter((label) => texts.includes(label))
}
function hasBtn(w: ViewWrapper, txt: string) {
  return w.findAll('button').some((b) => b.text().trim() === txt)
}

beforeEach(() => {
  vi.clearAllMocks()
  canImpl = () => true
})

describe('IMM-11 CTA server-driven — TC-FE-2: allowed_transitions là driver duy nhất', () => {
  it('Scheduled + allowed=["In Progress"] → render ĐÚNG 1 nút transition = "Bắt đầu hiệu chuẩn"', async () => {
    const w = await mountView(cal({ status: 'Scheduled', allowed_transitions: ['In Progress'] }))
    expect(ctasShown(w)).toEqual(['Bắt đầu hiệu chuẩn'])
  })

  it.each(Object.keys(CAL_TRANSITIONS))(
    '%s + allowed=[] → 0 nút transition DÙ status khớp nhánh hardcode cũ',
    async (status) => {
      const w = await mountView(cal({ status, allowed_transitions: [] }))
      expect(ctasShown(w)).toEqual([])
    },
  )

  it('External + Scheduled + allowed=[] → 0 nút transition (kể cả "Gửi phòng hiệu chuẩn")', async () => {
    const w = await mountView(cal({
      calibration_type: 'External', status: 'Scheduled', allowed_transitions: [],
    }))
    expect(ctasShown(w)).toEqual([])
  })

  it('ranh giới display/edit-mode: Scheduled + allowed=[] vẫn còn "Lưu" (docstatus=0, KHÔNG phải transition)', async () => {
    const w = await mountView(cal({ status: 'Scheduled', allowed_transitions: [] }))
    expect(hasBtn(w, 'Lưu')).toBe(true) // edit-mode UX được phép giữ theo docstatus
    expect(ctasShown(w)).toEqual([]) // nhưng 0 nút transition
  })
})

describe('IMM-11 CTA matrix — tập nút KHỚP allowed_transitions per status (đủ mọi quyền)', () => {
  type Case = { status: string; type?: string; docstatus?: number; expected: string[] }
  const CASES: Case[] = [
    // In-House: 'Sent to Lab' có trong allowed nhưng isExternal=false → ẩn "Gửi phòng hiệu chuẩn".
    { status: 'Scheduled', expected: ['Bắt đầu hiệu chuẩn', 'Hủy phiếu'] },
    { status: 'Scheduled', type: 'External', expected: ['Bắt đầu hiệu chuẩn', 'Gửi phòng hiệu chuẩn', 'Hủy phiếu'] },
    { status: 'In Progress', expected: ['Gửi duyệt', 'Hủy phiếu'] },
    { status: 'Sent to Lab', type: 'External', expected: ['Nhận chứng chỉ'] },
    { status: 'Certificate Received', type: 'External', expected: ['Gửi duyệt'] },
    { status: 'Passed', docstatus: 1, expected: [] },
    { status: 'Conditionally Passed', docstatus: 1, expected: [] },
    { status: 'Cancelled', expected: [] },
  ]
  for (const c of CASES) {
    it(`${c.status}${c.type ? ` (${c.type})` : ''} → CTA = [${c.expected.join(', ')}]`, async () => {
      const w = await mountView(cal({
        status: c.status,
        calibration_type: c.type ?? 'In-House',
        docstatus: c.docstatus ?? 0,
        overall_result: c.docstatus === 1 ? c.status : null,
      }))
      expect(ctasShown(w).sort()).toEqual([...c.expected].sort())
    })
  }

  it('edge Failed đã submit (allowed=[Conditionally Passed]) → 0 CTA: guard !isSubmitted chặn "Gửi duyệt" dù allowed chứa result-state', async () => {
    const w = await mountView(cal({
      status: 'Failed', overall_result: 'Failed', docstatus: 1,
      allowed_transitions: ['Conditionally Passed'],
    }))
    expect(ctasShown(w)).toEqual([])
    expect(hasBtn(w, 'Lưu')).toBe(false) // submitted → read-only toàn phần
  })
})

describe('IMM-11 CTA capability — gate = (cap && includes), thiếu cap ⇒ ẩn', () => {
  it('Scheduled thiếu calibration.cancel + calibration.submit → "Hủy phiếu" ẩn, "Bắt đầu hiệu chuẩn" (calibration.write) vẫn hiện', async () => {
    canImpl = (c: string) => c === 'calibration.write'
    const w = await mountView(cal({ status: 'Scheduled' }))
    expect(ctasShown(w)).toEqual(['Bắt đầu hiệu chuẩn'])
  })

  it('THIẾU mọi capability → 0 nút transition dù allowed_transitions đầy đủ + hiện hint quyền', async () => {
    canImpl = () => false
    const w = await mountView(cal({ status: 'Scheduled' }))
    expect(ctasShown(w)).toEqual([])
    expect(w.text()).toContain('Bạn không có quyền thực hiện hành động trên phiếu này.')
  })
})
