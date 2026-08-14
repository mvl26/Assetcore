// AC-UX-062 — test RENDER cho adoption lô 1: lỗi CHẶN hiện INLINE, hộp thoại KHÔNG đóng,
// KHÔNG xếp chồng hộp thoại thứ hai, KHÔNG nhân đôi ra toast (docs/ui-ux/05 §3/§5).
//
// Phủ 3 màn của lô 1, đủ CẢ HAI đường cài đặt:
//   • Đường A (`BaseModal` + prop `error`): CycleCountDetailView · NeedsRequestDetailView
//   • Đường B (overlay lai + `<ModalInlineError>`): CalibrationScheduleListView
//
// `useToast` và `useModal` bị thay bằng spy để chứng minh «một kênh duy nhất»: sau lỗi
// chặn, số lần toast/modal.alert mang cùng nội dung == 0.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref, nextTick } from 'vue'
import { ApiError, ErrorCode } from '@/api/errors'
import {
  vueRouterMockFactory, resetRouteMock, setRouteParams,
} from '@/test/vueRouterMock'

vi.mock('vue-router', () => vueRouterMockFactory())

// storeToRefs → identity: store mock đã cấp sẵn ref.
vi.mock('pinia', async (importOriginal) => {
  const actual = await importOriginal<typeof import('pinia')>()
  return { ...actual, storeToRefs: (s: unknown) => s }
})

// ── Kênh thông báo: spy để đếm (useApi/useNotify thật vẫn chạy qua đây) ──────────
const toastShow = vi.fn()
const toastError = vi.fn()
const toastSuccess = vi.fn()
const toastWarning = vi.fn()
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    toasts: { value: [] },
    show: toastShow, error: toastError, success: toastSuccess,
    warning: toastWarning, info: vi.fn(), dismiss: vi.fn(),
  }),
}))

const modalAlert = vi.fn()
vi.mock('@/composables/useModal', () => ({
  useModal: () => ({ alert: modalAlert, confirm: vi.fn().mockResolvedValue(true) }),
}))

/** Mọi lần gọi kênh thông báo — dùng để chứng minh 0 lần cho lỗi chặn. */
function notifyCalls(): unknown[][] {
  return [
    ...toastShow.mock.calls, ...toastError.mock.calls, ...toastSuccess.mock.calls,
    ...toastWarning.mock.calls, ...modalAlert.mock.calls,
  ]
}

function bizError(message: string, status = 417): ApiError {
  return new ApiError(message, { code: ErrorCode.BUSINESS_RULE, httpStatus: status })
}

// ── IMM-15 · Kiểm kê tồn kho ─────────────────────────────────────────────────────
const ccDetail = ref<Record<string, unknown> | null>(null)
const ccLoading = ref(false)
const ccError = ref<string | null>(null)
const ccLastApiError = ref<ApiError | null>(null)
const fetchCycleCount = vi.fn().mockResolvedValue(undefined)
vi.mock('@/stores/imm15', () => ({
  useImm15Store: () => ({
    cycleCountDetail: ccDetail,
    cycleCountDetailLoading: ccLoading,
    error: ccError,
    lastApiError: ccLastApiError,
    fetchCycleCount,
  }),
}))

const postCycleCount = vi.fn()
const recountCycleCount = vi.fn()
vi.mock('@/api/imm15', () => ({
  postCycleCount: (...a: unknown[]) => postCycleCount(...a),
  recountCycleCount: (...a: unknown[]) => recountCycleCount(...a),
  submitCycleCount: vi.fn().mockResolvedValue({}),
}))

// ── IMM-01 · Đề xuất nhu cầu ─────────────────────────────────────────────────────
const nrDoc = ref<Record<string, unknown> | null>(null)
const nrPlans = ref<Record<string, unknown>[]>([])
const nrLoading = ref(false)
const nrError = ref<string | null>(null)
const nrApprove = vi.fn()
const nrReject = vi.fn()
vi.mock('@/stores/imm01', () => ({
  useImm01Store: () => ({
    currentDoc: nrDoc, plans: nrPlans, loading: nrLoading, error: nrError,
    approve: (...a: unknown[]) => nrApprove(...a),
    reject: (...a: unknown[]) => nrReject(...a),
    transition: vi.fn().mockResolvedValue({}),
    score: vi.fn().mockResolvedValue({}),
    fetchOne: vi.fn().mockResolvedValue(undefined),
    fetchPlans: vi.fn().mockResolvedValue(undefined),
  }),
}))
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({ hasRole: () => true, isSystemAdmin: true }),
}))
vi.mock('@/api/imm01', () => ({
  getAllowedTransitions: vi.fn().mockResolvedValue({ transitions: [] }),
  rollIntoPlan: vi.fn().mockResolvedValue({}),
}))

// ── IMM-11 · Lịch hiệu chuẩn ─────────────────────────────────────────────────────
const createCalibrationSchedule = vi.fn()
vi.mock('@/api/imm11', () => ({
  listCalibrationSchedules: vi.fn().mockResolvedValue({ data: [], pagination: { total: 0, total_pages: 0 } }),
  createCalibrationSchedule: (...a: unknown[]) => createCalibrationSchedule(...a),
  updateCalibrationSchedule: vi.fn(),
  deleteCalibrationSchedule: vi.fn(),
}))
const calError = ref<string | null>(null)
const calLastApiError = ref<ApiError | null>(null)
vi.mock('@/stores/imm11', () => ({
  useImm11Store: () => ({
    error: calError,
    lastApiError: calLastApiError,
    _captureError: (e: unknown) => {
      calLastApiError.value = e as ApiError
      calError.value = (e as ApiError)?.message ?? null
    },
  }),
}))

import CycleCountDetailView from '@/views/inventory/CycleCountDetailView.vue'
import NeedsRequestDetailView from '@/views/needs/NeedsRequestDetailView.vue'
import CalibrationScheduleListView from '@/views/calibration/CalibrationScheduleListView.vue'

/** KHÔNG stub BaseModal / ModalInlineError — chính chúng là thứ đang được chấm. */
const stubs = {
  teleport: true,
  PageHeader: { template: '<div><slot /><slot name="actions" /></div>' },
  ListFilterBar: { template: '<div><slot name="fields" /></div>' },
  FilterToggleButton: true,
  BasePagination: true,
  SkeletonLoader: true,
  StatusBadge: true,
  WorkflowStepper: true,
  DetailLoadError: true,
  ApproverSelect: { template: '<input class="approver-stub" />' },
  SmartSelect: { template: '<input class="smart-stub" />' },
  DateInput: { template: '<input class="date-stub" />' },
  CurrencyInput: { template: '<input class="currency-stub" />' },
}

beforeEach(() => {
  resetRouteMock()
  toastShow.mockClear(); toastError.mockClear()
  toastSuccess.mockClear(); toastWarning.mockClear(); modalAlert.mockClear()
  postCycleCount.mockReset(); recountCycleCount.mockReset()
  nrApprove.mockReset(); nrReject.mockReset(); createCalibrationSchedule.mockReset()
  calError.value = null; calLastApiError.value = null
})

// ─────────────────────────────────────────────────────────────────────────────────
describe('TC-UX062-09 — CycleCountDetailView (đường A): 417 khi ghi nhận điều chỉnh', () => {
  const MSG_417 = 'Người xác nhận phải khác người kiểm kê.'

  function seedDetail() {
    ccDetail.value = {
      name: 'CC-2026-00001', status: 'Reviewed',
      warehouse: 'WH-01', warehouse_name: 'Kho trung tâm',
      count_type: 'Full', count_date: '2026-08-01',
      counted_by: 'ktv@bv.vn', counted_by_name: 'KTV Nguyễn Văn A',
      verified_by: '', verified_by_name: '',
      allowed_transitions: ['Post', 'Recount'],
      items: [], variance_count: 0, variance_value: 0, capa_created: 0,
    }
    ccError.value = null
    ccLastApiError.value = null
  }

  async function openPostModalAndFail() {
    seedDetail()
    setRouteParams({ name: 'CC-2026-00001' })
    postCycleCount.mockRejectedValue(bizError(MSG_417))
    const w = mount(CycleCountDetailView, { global: { stubs } })
    await flushPromises()
    await w.find('[data-testid="cta-post"]').trigger('click')
    await nextTick()
    const confirm = w.findAll('button').find((b) => b.text().includes('Xác nhận ghi nhận'))!
    await confirm.trigger('click')
    await flushPromises()
    return w
  }

  it('hộp thoại CÒN MỞ + có modal-error mang đúng câu lỗi', async () => {
    const w = await openPostModalAndFail()
    expect(w.find('[data-testid="modal-card"]').exists()).toBe(true)
    const box = w.find('[data-testid="modal-error"]')
    expect(box.exists()).toBe(true)
    expect(box.attributes('role')).toBe('alert')
    expect(box.text()).toContain(MSG_417)
    w.unmount()
  })

  it('A3 — KHÔNG xếp chồng: đúng 1 modal-card, 0 lần useModal.alert', async () => {
    const w = await openPostModalAndFail()
    expect(w.findAll('[data-testid="modal-card"]')).toHaveLength(1)
    expect(modalAlert).not.toHaveBeenCalled()
    w.unmount()
  })

  it('TC-UX062-11 — KHÔNG trùng kênh: 0 toast mang cùng nội dung', async () => {
    const w = await openPostModalAndFail()
    const withSameMsg = notifyCalls().filter((c) => JSON.stringify(c).includes(MSG_417))
    expect(withSameMsg).toHaveLength(0)
    w.unmount()
  })

  it('TC-UX062-12 — đóng rồi mở lại: KHÔNG dính lỗi lượt trước', async () => {
    const w = await openPostModalAndFail()
    expect(w.find('[data-testid="modal-error"]').exists()).toBe(true)
    await w.find('[data-testid="modal-close"]').trigger('click')
    await nextTick()
    expect(w.find('[data-testid="modal-card"]').exists()).toBe(false)
    await w.find('[data-testid="cta-post"]').trigger('click')
    await nextTick()
    expect(w.find('[data-testid="modal-card"]').exists()).toBe(true)
    expect(w.find('[data-testid="modal-error"]').exists()).toBe(false)
    w.unmount()
  })

  it('hộp thoại «Sửa đếm lại» cũng giữ lỗi inline và không tự đóng', async () => {
    seedDetail()
    setRouteParams({ name: 'CC-2026-00001' })
    recountCycleCount.mockRejectedValue(bizError('Phiếu đã ghi nhận, không thể đếm lại.'))
    const w = mount(CycleCountDetailView, { global: { stubs } })
    await flushPromises()
    await w.find('[data-testid="cta-recount"]').trigger('click')
    await nextTick()
    await w.find('[data-testid="recount-reason"]').setValue('Kiểm đếm lại kệ A3')
    await w.find('[data-testid="cta-recount-confirm"]').trigger('click')
    await flushPromises()
    expect(w.findAll('[data-testid="modal-card"]')).toHaveLength(1)
    expect(w.find('[data-testid="modal-error"]').text()).toContain('không thể đếm lại')
    w.unmount()
  })
})

// ─────────────────────────────────────────────────────────────────────────────────
describe('TC-UX062-10 — NeedsRequestDetailView (đường A): 422 khi phê duyệt', () => {
  const MSG_422 = 'Người duyệt không thuộc Ban Giám đốc.'

  function seedDoc() {
    nrDoc.value = {
      name: 'NR-2026-00007',
      workflow_state: 'Pending Approval',
      allowed_transitions: ['Phê duyệt', 'Bác đề xuất'],
      request_type: 'Device',
      scoring_rows: [], budget_lines: [], funding_source: 'NSNN',
      procurement_plan: null,
    }
    nrError.value = null
    nrLoading.value = false
  }

  async function openApproveAndFail() {
    seedDoc()
    nrApprove.mockRejectedValue(bizError(MSG_422, 422))
    const w = mount(NeedsRequestDetailView, {
      props: { id: 'NR-2026-00007' }, global: { stubs },
    })
    await flushPromises()
    const openBtn = w.findAll('button').find((b) => b.text().includes('Phê duyệt ✓'))!
    await openBtn.trigger('click')
    await nextTick()
    // ApproverSelect bị stub ⇒ set thẳng model qua component con của view.
    const modal = w.findComponent({ name: 'BaseModal' })
    expect(modal.exists()).toBe(true)
    return w
  }

  it('hộp thoại «Phê duyệt đề xuất nhu cầu» CÒN MỞ + lỗi hiện inline', async () => {
    const w = await openApproveAndFail()
    // Nhập người duyệt + ghi chú (giá trị phải CÒN NGUYÊN sau khi lỗi).
    const vm = w.vm as unknown as { approverInput: string; approveRemarks: string }
    vm.approverInput = 'giamdoc@benhvien.vn'
    vm.approveRemarks = 'Đồng ý theo biên bản họp.'
    await nextTick()
    const confirm = w.findAll('button').find((b) => b.text().includes('Xác nhận phê duyệt'))!
    await confirm.trigger('click')
    await flushPromises()

    expect(w.findAll('[data-testid="modal-card"]')).toHaveLength(1)
    const box = w.find('[data-testid="modal-error"]')
    expect(box.exists()).toBe(true)
    expect(box.text()).toContain(MSG_422)
    // Dữ liệu người dùng đã nhập KHÔNG bị xoá.
    expect(vm.approverInput).toBe('giamdoc@benhvien.vn')
    expect(vm.approveRemarks).toBe('Đồng ý theo biên bản họp.')
    // Một kênh duy nhất.
    expect(notifyCalls().filter((c) => JSON.stringify(c).includes(MSG_422))).toHaveLength(0)
    expect(modalAlert).not.toHaveBeenCalled()
    w.unmount()
  })

  it('hộp thoại «Bác đề xuất» cũng giữ lý do đã nhập khi lỗi', async () => {
    seedDoc()
    const MSG = 'Đề xuất đã được duyệt, không thể bác.'
    nrReject.mockRejectedValue(bizError(MSG, 422))
    const w = mount(NeedsRequestDetailView, {
      props: { id: 'NR-2026-00007' }, global: { stubs },
    })
    await flushPromises()
    await w.findAll('button').find((b) => b.text().includes('Bác đề xuất'))!.trigger('click')
    await nextTick()
    const vm = w.vm as unknown as { rejectReasonInput: string }
    vm.rejectReasonInput = 'Chưa đủ hồ sơ.'
    await nextTick()
    await w.findAll('button').find((b) => b.text().includes('Xác nhận bác đề xuất'))!.trigger('click')
    await flushPromises()

    expect(w.findAll('[data-testid="modal-card"]')).toHaveLength(1)
    expect(w.find('[data-testid="modal-error"]').text()).toContain(MSG)
    expect(vm.rejectReasonInput).toBe('Chưa đủ hồ sơ.')
    w.unmount()
  })
})

// ─────────────────────────────────────────────────────────────────────────────────
describe('CalibrationScheduleListView (đường B): lỗi lưu lịch hiện inline trong overlay', () => {
  const MSG = 'Thiết bị đã có lịch hiệu chuẩn đang hoạt động.'

  it('form CÒN MỞ + ModalInlineError hiện lỗi + 0 toast trùng nội dung', async () => {
    createCalibrationSchedule.mockRejectedValue(bizError(MSG))
    const w = mount(CalibrationScheduleListView, { global: { stubs } })
    await flushPromises()
    await w.findAll('button').find((b) => b.text().includes('Thêm lịch'))!.trigger('click')
    await nextTick()
    const save = w.findAll('button').find((b) => b.text().trim() === 'Lưu')!
    await save.trigger('click')
    await flushPromises()

    const box = w.find('[data-testid="modal-error"]')
    expect(box.exists()).toBe(true)
    expect(box.attributes('role')).toBe('alert')
    expect(box.attributes('aria-live')).toBe('assertive')
    expect(box.text()).toContain(MSG)
    // Overlay form vẫn mở (nút Lưu còn đó) ⇒ nhánh lỗi KHÔNG đóng hộp thoại.
    expect(w.findAll('button').some((b) => b.text().trim() === 'Lưu')).toBe(true)
    expect(notifyCalls().filter((c) => JSON.stringify(c).includes(MSG))).toHaveLength(0)
    w.unmount()
  })
})
