// Copyright (c) 2026, AssetCore Team
// TDD (FE regression guard) — BR-12-02 / RCA-gate SSoT cho IncidentDetailView (IMM-12).
//
// Đề mục: nút "Đóng sự cố" GATE theo yêu cầu RCA LIVE. FE đọc cờ `rca_required`
// DERIVE-LIVE do BE tính lại theo severity (get_incident) + `rca.status` — KHÔNG so
// severity thô client-side, KHÔNG đọc cờ stored stale. Gate FE mirror EXACT gate BE
// close_incident (services/imm12.py:711): rca_required=1 ∧ rca chưa 'Completed' ⇒ chặn.
//
// Đồng thời khoá contract BE→FE: close_incident trả VALIDATION → notify.fromError,
// KHÔNG success toast + KHÔNG reload giả (không refetch get_incident).
//
// Test dùng logic THẬT của component (real store/composable) — chỉ mock ranh giới
// transport (@/api/imm12) + notify boundary; KHÔNG mock trả tay success.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import type { IncidentDetail } from '@/api/imm12'
import { ApiError, ErrorCode } from '@/api/errors'
import { MSG } from '@/locales/messages'

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'INC-2026-00099' } }),
  useRouter: () => ({ push: vi.fn() }),
}))

const getIncidentSpy = vi.fn<() => Promise<IncidentDetail>>()
const closeIncidentSpy = vi.fn()
vi.mock('@/api/imm12', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/imm12')>()
  return {
    ...actual,
    getIncident: () => getIncidentSpy(),
    acknowledgeIncident: vi.fn(),
    startWork: vi.fn(),
    resolveIncident: vi.fn(),
    closeIncident: (...args: unknown[]) => closeIncidentSpy(...args),
    cancelIncident: vi.fn(),
    reopenIncident: vi.fn(),
    requestRca: vi.fn(),
    createRca: vi.fn(),
    attachIncidentPhoto: vi.fn(),
  }
})
vi.mock('@/api/imm00', () => ({ deleteIncident: vi.fn() }))

const toastSuccess = vi.fn()
const toastError = vi.fn()
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ success: toastSuccess, error: toastError, warning: vi.fn() }),
}))

const fromErrorSpy = vi.fn()
const notifyShowSpy = vi.fn()
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: notifyShowSpy, fromError: fromErrorSpy, fromOk: vi.fn(), confirm: vi.fn() }),
}))

// Đủ mọi quyền incident (incident.close) + corrective — gate chỉ còn phụ thuộc RCA.
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({ isSystemAdmin: false, user: { name: 'qa@benhvien.vn' } }),
}))

import IncidentDetailView from '@/views/incident/IncidentDetailView.vue'

// Fixture Resolved (đủ điều kiện chào nút Đóng theo allowed_transitions) — override
// severity / rca_required / rca để lái gate. rca_required là cờ DERIVE-LIVE của BE.
function incident(over: Partial<IncidentDetail> = {}): IncidentDetail {
  return {
    name: 'INC-2026-00099',
    asset: 'AC-ASSET-2026-00042',
    asset_name: 'Máy thở CTA',
    incident_type: 'Failure',
    severity: 'Critical',
    status: 'Resolved',
    description: 'Thiết bị dừng đột ngột',
    reported_by: 'reporter@benhvien.vn',
    reported_at: '2026-06-01 08:00:00',
    allowed_transitions: ['Closed', 'RCA Required', 'In Progress'],
    scene_photos: [],
    ...over,
  } as IncidentDetail
}

const stubs = { ApproverSelect: true, WorkflowStepper: true, SlaBreachBadge: true }

async function mountView(fixture: IncidentDetail) {
  getIncidentSpy.mockResolvedValue(fixture)
  const w = mount(IncidentDetailView, { global: { stubs } })
  await flushPromises()
  return w
}
type ViewWrapper = Awaited<ReturnType<typeof mountView>>

/** Nút "Đóng sự cố" ở header (duy nhất khi modal đóng). */
function headerCloseBtn(w: ViewWrapper) {
  return w.findAll('button').find((b) => b.text().trim() === 'Đóng sự cố')
}

beforeEach(() => {
  getIncidentSpy.mockReset()
  closeIncidentSpy.mockReset()
  toastSuccess.mockReset()
  toastError.mockReset()
  fromErrorSpy.mockReset()
  notifyShowSpy.mockReset()
})

describe('BR-12-02 gate nút "Đóng sự cố" — đọc cờ RCA LIVE, KHÔNG so severity thô', () => {
  it('Critical + rca_required=1 + CHƯA có rca_record → nút Đóng DISABLED + hint VI', async () => {
    const w = await mountView(incident({ severity: 'Critical', rca_required: 1 }))
    const btn = headerCloseBtn(w)
    expect(btn).toBeTruthy()
    expect(btn!.attributes('disabled')).toBeDefined()
    expect(w.text()).toContain('bắt buộc có RCA Hoàn thành trước khi đóng (BR-12-02)')
    // aria-describedby trỏ hint (WCAG)
    expect(btn!.attributes('aria-describedby')).toBe('close-rca-hint')
    // badge "Cần RCA" hiện
    expect(w.text()).toContain('Cần RCA')
  })

  it('Critical + rca_record nhưng RCA status != Completed (Đang phân tích) → DISABLED + hint', async () => {
    const w = await mountView(incident({
      severity: 'Critical', rca_required: 1, rca_record: 'RCA-2026-0007',
      rca: { name: 'RCA-2026-0007', status: 'RCA In Progress' },
    }))
    const btn = headerCloseBtn(w)
    expect(btn!.attributes('disabled')).toBeDefined()
    expect(w.text()).toContain('(BR-12-02)')
  })

  it('Critical + RCA status == Completed → nút Đóng ENABLED, KHÔNG hint, KHÔNG badge', async () => {
    const w = await mountView(incident({
      severity: 'Critical', rca_required: 1, rca_record: 'RCA-2026-0007',
      rca: { name: 'RCA-2026-0007', status: 'Completed' },
    }))
    const btn = headerCloseBtn(w)
    expect(btn!.attributes('disabled')).toBeUndefined()
    expect(w.text()).not.toContain('(BR-12-02)')
    expect(w.text()).not.toContain('Cần RCA')
  })

  it('Non-regression: Medium thực (rca_required=0) → ENABLED, KHÔNG hint', async () => {
    const w = await mountView(incident({ severity: 'Medium', rca_required: 0 }))
    const btn = headerCloseBtn(w)
    expect(btn!.attributes('disabled')).toBeUndefined()
    expect(w.text()).not.toContain('(BR-12-02)')
    expect(w.text()).not.toContain('Cần RCA')
  })

  it('SSoT escalation: severity hiển thị Medium NHƯNG rca_required=1 (BE derive-live) → DISABLED + badge (đọc cờ LIVE, không cờ severity thô)', async () => {
    // Chứng minh FE gate theo rca_required (derive-live) chứ KHÔNG so `severity === High/Critical`
    // ở client — phiếu escalated cờ live=1 dù nhãn severity truyền vào là 'Medium'.
    const w = await mountView(incident({ severity: 'Medium', rca_required: 1 }))
    const btn = headerCloseBtn(w)
    expect(btn!.attributes('disabled')).toBeDefined()
    expect(w.text()).toContain('Cần RCA')
    expect(w.text()).toContain('(BR-12-02)')
  })
})

describe('BR-12-02 contract BE→FE — close_incident VALIDATION → notify.fromError, no success, no reload', () => {
  it('close_incident reject ApiError(IMM12_CLOSE_RCA_INCOMPLETE) → notify.fromError; KHÔNG success toast; KHÔNG refetch', async () => {
    // Gate FE mở (Critical + RCA Completed) để mở được modal xác nhận; BE vẫn từ chối
    // (mô phỏng re-derive/race) → doClose phải notify.fromError, không reload giả.
    const w = await mountView(incident({
      severity: 'Critical', rca_required: 1, rca_record: 'RCA-2026-0007',
      rca: { name: 'RCA-2026-0007', status: 'Completed' },
    }))
    expect(getIncidentSpy).toHaveBeenCalledTimes(1)   // load ban đầu

    const err = new ApiError('Không thể đóng sự cố mức Critical khi phân tích nguyên nhân gốc chưa hoàn thành.', {
      code: ErrorCode.VALIDATION_ERROR,
      httpStatus: 422,
      messageCode: MSG.IMM12_CLOSE_RCA_INCOMPLETE,
      context: { severity: 'Critical', rca: 'RCA-2026-0007' },
      severity: 'critical',
    })
    closeIncidentSpy.mockRejectedValue(err)

    // Mở modal xác nhận rồi bấm "Đóng sự cố" trong modal.
    await headerCloseBtn(w)!.trigger('click')
    await nextTick()
    const modal = w.find('.fixed.inset-0')
    expect(modal.exists()).toBe(true)
    const confirmBtn = modal.findAll('button').find((b) => b.text().trim() === 'Đóng sự cố')
    expect(confirmBtn).toBeTruthy()
    await confirmBtn!.trigger('click')
    await flushPromises()

    // Contract: notify.fromError nhận đúng ApiError; KHÔNG success toast; KHÔNG reload giả.
    expect(closeIncidentSpy).toHaveBeenCalledTimes(1)
    expect(fromErrorSpy).toHaveBeenCalledTimes(1)
    const passed = fromErrorSpy.mock.calls[0][0] as ApiError
    expect(passed).toBeInstanceOf(ApiError)
    expect(passed.messageCode).toBe(MSG.IMM12_CLOSE_RCA_INCOMPLETE)
    expect(toastSuccess).not.toHaveBeenCalled()
    // KHÔNG refetch get_incident sau lỗi (vẫn 1 lần = load ban đầu).
    expect(getIncidentSpy).toHaveBeenCalledTimes(1)
  })
})
