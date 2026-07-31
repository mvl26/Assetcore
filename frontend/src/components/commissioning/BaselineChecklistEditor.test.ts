// Copyright (c) 2026, AssetCore Team — BaselineChecklistEditor (IMM-04, silent-completion lens)
//
// REAL-STORE test (2026-07-20): BỎ `vi.mock('@/stores/imm04')` — nguồn FALSE-GREEN. Trước đây
// store bị mock nên nhánh map `ok`/`testsRecorded` + capture `lastApiError` của store KHÔNG
// bao giờ chạy → 200-trần / VALIDATION chỉ "trông có vẻ" đúng. Nay mock CHỈ tầng api
// (`@/api/imm04`) → luồng THỰC đi qua `useCommissioningStore().submitBaselineChecklist` → api,
// nên store phải THỰC:
//   • resolve BE-shape {tests_recorded, overall_result} → map camelCase + ok=true.
//   • reject ApiError(VALIDATION 422) → `_captureError` set `lastApiError` (hydrated) + ok=false.
// Gate đóng:
//   • tests_recorded=3 → render 'Đã ghi 3 phép đo' + toast success + emit submitted.
//   • tests_recorded=0 kèm success (200 trần) → KHÔNG toast success, render hint, KHÔNG notify
//     (defense-in-depth: server "thành công" mà 0 phép đo VẪN không celebrate).
//   • BE VALIDATION (ok=false) → render hint + notify.fromError(store.lastApiError THỰC captured).
//   • baseline_tests rỗng → technician THÊM được dòng (seed-child gap).
//   • GATE-6c dead-control: test_result chọn trên UI == payload gửi tới api (qua real store).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia, type Pinia } from 'pinia'
import { ApiError, ErrorCode } from '@/api/errors'
import type { BaselineOverallResult, BaselineSubmitResult } from '@/api/imm04'
import type { BaselineTest } from '@/types/imm04'

// ─── Mock CHỈ tầng api (real store) ───────────────────────────────────────────
// Full named-export set để thoả import của store; test chỉ điều khiển
// `submitBaselineChecklist` (boundary under test) + `getFormContext` (store re-fetch
// doc sau submit thành công).
vi.mock('@/api/imm04', () => ({
  getFormContext: vi.fn(),
  listCommissioning: vi.fn(),
  transitionState: vi.fn(),
  submitCommissioning: vi.fn(),
  saveCommissioning: vi.fn(),
  createCommissioning: vi.fn(),
  checkSnUnique: vi.fn(),
  reportNonConformance: vi.fn(),
  assignIdentification: vi.fn(),
  generateInternalQr: vi.fn(),
  submitBaselineChecklist: vi.fn(),
  clearClinicalHold: vi.fn(),
  approveClinicalRelease: vi.fn(),
  getDashboardStats: vi.fn(),
  closeNonConformance: vi.fn(),
  deleteCommissioning: vi.fn(),
  cancelCommissioning: vi.fn(),
  getPoDetails: vi.fn(),
}))
// Store cũng import `frappeGet` trực tiếp (timeline/NC) — mock để không kéo axios thật.
vi.mock('@/api/helpers', () => ({ frappeGet: vi.fn(), frappePost: vi.fn() }))

const toastSuccessSpy = vi.fn()
const toastWarningSpy = vi.fn()
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    success: toastSuccessSpy, error: vi.fn(), warning: toastWarningSpy, info: vi.fn(), show: vi.fn(),
  }),
}))

const fromErrorSpy = vi.fn()
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ fromError: fromErrorSpy, show: vi.fn(), fromOk: vi.fn(), confirm: vi.fn() }),
}))

import * as api from '@/api/imm04'
import { useCommissioningStore } from '@/stores/imm04'
import BaselineChecklistEditor from './BaselineChecklistEditor.vue'

function makeTest(over: Partial<BaselineTest> = {}): BaselineTest {
  return {
    idx: 1, parameter: 'Dòng rò điện vỏ máy', measured_val: '', unit: 'mA',
    test_result: '', fail_note: '', is_critical: 0, ...over,
  }
}

const SEL = {
  submit: '[data-testid="submit-baseline"]',
  addRow: '[data-testid="add-baseline-row"]',
  success: '[data-testid="baseline-success"]',
  fail: '[data-testid="baseline-fail"]',
  hint: '[data-testid="baseline-hint"]',
  row: '[data-testid="baseline-row"]',
}

let pinia: Pinia

function mountEditor(tests: BaselineTest[]) {
  return mount(BaselineChecklistEditor, {
    props: { commissioning: 'AC-COMM-2026-0001', tests },
    global: { plugins: [pinia] },
  })
}

/** BE-shape phản hồi từ submit_baseline_checklist (snake_case) — store map sang camelCase. */
function beResult(
  tests_recorded: number,
  overall_result: BaselineOverallResult,
  failed_parameters: string[] = [],
): BaselineSubmitResult {
  return {
    name: 'AC-COMM-2026-0001',
    overall_result,
    tests_recorded,
    clinical_hold_required: false,
    failed_parameters,
  }
}

beforeEach(() => {
  pinia = createPinia()
  setActivePinia(pinia)
  vi.clearAllMocks()
  // Submit thành công ⇒ store gọi fetchDetail → getFormContext; resolve doc tối thiểu.
  vi.mocked(api.getFormContext).mockResolvedValue(
    { name: 'AC-COMM-2026-0001' } as unknown as Awaited<ReturnType<typeof api.getFormContext>>,
  )
})

describe('BaselineChecklistEditor — silent-completion gate (real store)', () => {
  it('tests_recorded=3 → render "Đã ghi 3 phép đo", toast success, emit submitted; KHÔNG notify lỗi', async () => {
    vi.mocked(api.submitBaselineChecklist).mockResolvedValue(beResult(3, 'Pass'))
    const wrapper = mountEditor([makeTest({ test_result: 'Pass' })])

    await wrapper.find(SEL.submit).trigger('click')
    await flushPromises()

    expect(wrapper.find(SEL.success).exists()).toBe(true)
    expect(wrapper.find(SEL.success).text()).toContain('Đã ghi 3 phép đo')
    expect(wrapper.find(SEL.hint).exists()).toBe(false)
    expect(toastSuccessSpy).toHaveBeenCalledWith('Đã ghi 3 phép đo')
    expect(fromErrorSpy).not.toHaveBeenCalled()
    expect(wrapper.emitted('submitted')?.[0]?.[0]).toMatchObject({ testsRecorded: 3 })
  })

  it('tests_recorded=0 kèm success (200 trần) → KHÔNG toast success + render hint + KHÔNG notify (defense-in-depth)', async () => {
    // Server "thành công" (thậm chí khai overall_result='Pass') nhưng ghi 0 phép đo →
    // store ok=true, testsRecorded=0. Component PHẢI KHÔNG celebrate (không toast/banner
    // success) và KHÔNG notify lỗi (ok=true).
    vi.mocked(api.submitBaselineChecklist).mockResolvedValue(beResult(0, 'Pass'))
    const wrapper = mountEditor([makeTest({ test_result: 'Pass' })])

    await wrapper.find(SEL.submit).trigger('click')
    await flushPromises()

    expect(wrapper.find(SEL.success).exists()).toBe(false)
    expect(toastSuccessSpy).not.toHaveBeenCalled()
    expect(wrapper.find(SEL.hint).exists()).toBe(true)
    expect(wrapper.find(SEL.hint).text()).toContain('Chưa có phép đo baseline nào — thêm dòng trước khi nộp')
    expect(fromErrorSpy).not.toHaveBeenCalled()
    expect(wrapper.emitted('submitted')).toBeUndefined()
  })

  it('BE VALIDATION (422, 0 phép đo) → real store capture lastApiError; render hint + notify.fromError(store.lastApiError)', async () => {
    const BR_0404 = new ApiError(
      'BR-04-04: Nghiệm thu Initial Inspection chỉ Pass khi có ≥1 phép đo baseline thực (0 phép đo ghi nhận).',
      { code: ErrorCode.VALIDATION, httpStatus: 422, severity: 'warning', title: 'Thiếu phép đo baseline' },
    )
    vi.mocked(api.submitBaselineChecklist).mockRejectedValue(BR_0404)
    const store = useCommissioningStore() // cùng singleton mà component dùng (chung pinia)

    const wrapper = mountEditor([makeTest({ test_result: 'Pass' })])
    await wrapper.find(SEL.submit).trigger('click')
    await flushPromises()

    expect(wrapper.find(SEL.success).exists()).toBe(false)
    expect(toastSuccessSpy).not.toHaveBeenCalled()
    expect(wrapper.find(SEL.hint).exists()).toBe(true)
    expect(wrapper.find(SEL.hint).text()).toContain('Chưa có phép đo baseline nào — thêm dòng trước khi nộp')
    // False-green fix: store THỰC capture ServiceError (không còn hardcode); component surface đúng nó.
    expect(store.lastApiError).toBe(BR_0404)
    expect(store.lastApiError?.code).toBe(ErrorCode.VALIDATION)
    expect(fromErrorSpy).toHaveBeenCalledWith(store.lastApiError)
    expect(wrapper.emitted('submitted')).toBeUndefined()
  })

  // ── CR-54 §2 — phép đo KHÔNG ĐẠT vẫn LƯU được (TDD-7) ──────────────────────
  it('overall_result="Fail" → banner nói KHÔNG ĐẠT + nêu đích danh thông số, KHÔNG banner/toast đạt', async () => {
    vi.mocked(api.submitBaselineChecklist).mockResolvedValue(
      beResult(3, 'Fail', ['Dòng rò điện vỏ máy']),
    )
    const wrapper = mountEditor([makeTest({ test_result: 'Fail', fail_note: 'Vượt ngưỡng' })])

    await wrapper.find(SEL.submit).trigger('click')
    await flushPromises()

    const fail = wrapper.find(SEL.fail)
    expect(fail.exists(), 'phải render banner kết quả không đạt').toBe(true)
    const text = fail.text()
    expect(text).toContain('KHÔNG ĐẠT')
    expect(text).toContain('Dòng rò điện vỏ máy')
    expect(text).toContain('Kiểm tra lại')
    // KHÔNG chữ nào khẳng định đạt / thành công (false-pass với người dùng)
    expect(text).not.toContain('Đạt')
    expect(text).not.toContain('thành công')
    // KHÔNG lộ enum thô ra giao diện (LL-FE-52/53)
    expect(text).not.toContain('Fail')
    expect(text).not.toContain('Pass')

    expect(wrapper.find(SEL.success).exists()).toBe(false)
    expect(wrapper.find(SEL.hint).exists()).toBe(false)
    expect(toastSuccessSpy).not.toHaveBeenCalled()
    expect(toastWarningSpy).toHaveBeenCalledTimes(1)
    expect(fromErrorSpy).not.toHaveBeenCalled()
    // Phiếu ĐÃ lưu ⇒ vẫn báo cho view cha refresh, kèm SSoT kết quả tổng.
    expect(wrapper.emitted('submitted')?.[0]?.[0]).toMatchObject({
      testsRecorded: 3,
      overallResult: 'Fail',
      failedParameters: ['Dòng rò điện vỏ máy'],
    })
  })

  it('overall_result="Pass" → banner đạt (không rơi nhầm sang nhánh không đạt)', async () => {
    vi.mocked(api.submitBaselineChecklist).mockResolvedValue(beResult(2, 'Pass'))
    const wrapper = mountEditor([makeTest({ test_result: 'Pass' })])

    await wrapper.find(SEL.submit).trigger('click')
    await flushPromises()

    expect(wrapper.find(SEL.success).exists()).toBe(true)
    expect(wrapper.find(SEL.success).text()).toContain('Đã ghi 2 phép đo')
    expect(wrapper.find(SEL.fail).exists()).toBe(false)
    expect(toastWarningSpy).not.toHaveBeenCalled()
    expect(wrapper.emitted('submitted')?.[0]?.[0]).toMatchObject({ overallResult: 'Pass' })
  })

  it('baseline_tests rỗng → nút Nộp disabled; thêm dòng + nhập kết quả → enabled', async () => {
    const wrapper = mountEditor([])
    // 0 dòng + 0 kết quả → disabled
    expect(wrapper.find(SEL.submit).attributes('disabled')).toBeDefined()
    expect(wrapper.findAll(SEL.row).length).toBe(0)

    await wrapper.find(SEL.addRow).trigger('click')
    expect(wrapper.findAll(SEL.row).length).toBe(1)
    // dòng mới nhưng chưa có kết quả → vẫn disabled
    expect(wrapper.find(SEL.submit).attributes('disabled')).toBeDefined()

    await wrapper.find(`${SEL.row} input[data-testid="row-parameter"]`).setValue('Dòng rò điện')
    await wrapper.find(`${SEL.row} select[data-testid="row-result"]`).setValue('Pass')
    expect(wrapper.find(SEL.submit).attributes('disabled')).toBeUndefined()
  })

  it('GATE-6c dead-control: test_result chọn trên UI == payload gửi tới api (qua real store)', async () => {
    vi.mocked(api.submitBaselineChecklist).mockResolvedValue(beResult(1, 'Pass'))
    const wrapper = mountEditor([])
    await wrapper.find(SEL.addRow).trigger('click')
    await wrapper.find(`${SEL.row} input[data-testid="row-parameter"]`).setValue('Dòng rò điện')
    await wrapper.find(`${SEL.row} input[data-testid="row-measured"]`).setValue('0.1')
    await wrapper.find(`${SEL.row} select[data-testid="row-result"]`).setValue('Pass')

    await wrapper.find(SEL.submit).trigger('click')
    await flushPromises()

    // Real store propagate results NGUYÊN VẸN xuống api (không hardcode call-site).
    expect(api.submitBaselineChecklist).toHaveBeenCalledWith('AC-COMM-2026-0001', [
      { parameter: 'Dòng rò điện', measured_val: '0.1', test_result: 'Pass', fail_note: '' },
    ])
  })
})
