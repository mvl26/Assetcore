// Copyright (c) 2026, AssetCore Team
// TC-UX4-31 — DecisionDetailView áp khuôn `DetailPageShell` (lô 1, AC-UX-048).
//
// RED trước fix: `onMounted` await TRẦN `store.fetchDecision`, mà store `throw e` lại
// sau khi set `error` ⇒ unhandled rejection; màn rơi vào nhánh cuối «Không có dữ liệu»
// — một dòng chữ xám không phân biệt được mã sai / thiếu quyền / mất mạng, KHÔNG nút
// nạp lại, KHÔNG đường quay lại. Thanh nút workflow lại nằm trong nhánh có-dữ-liệu nên
// trông "đúng" ở màn hỏng chỉ vì `currentDecision` là state DÙNG CHUNG chưa reset (§7.15).
//
// Sau fix: view tự `try/catch`, phân loại kind THẬT, dọn `currentDecision` về null.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { createPinia, setActivePinia } from 'pinia'
import { ApiError, ErrorCode } from '@/api/errors'

// View chỉ dùng `useRoute`; điều hướng đi qua `$router` của template (KHÔNG thêm
// `useRouter()` — `decisionAvlEligibilityBadge.test.ts` chỉ cấp `mocks: { $router }`).
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'PD-2026-00001' } }),
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
}))

vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({
    show: vi.fn(), fromError: vi.fn(), fromOk: vi.fn(), confirm: vi.fn().mockResolvedValue(true),
  }),
}))

type DecisionFixture = Record<string, unknown>
const getDecision = vi.fn<() => Promise<DecisionFixture | null>>()
vi.mock('@/api/imm03', () => ({
  getDecision: () => getDecision(),
  getEvaluation: vi.fn().mockResolvedValue({ candidates: [], has_top_tie: false, tied_candidates: '' }),
  awardDecision: vi.fn(),
  recordContract: vi.fn(),
  transitionDecisionWorkflow: vi.fn(),
}))

import DecisionDetailView from '@/views/procurement/DecisionDetailView.vue'

// Mount THẬT khuôn (bẫy §7.5).
const stubs = {
  CurrencyInput: true,
  DateInput: true,
  ApproverSelect: true,
  FileUploadField: true,
  teleport: true,
}

const backSpy = vi.fn()

function fixture(over: DecisionFixture = {}): DecisionFixture {
  return {
    name: 'PD-2026-00001',
    spec_ref: 'TS-2026-0001',
    evaluation_ref: 'VE-2026-0001',
    workflow_state: 'Draft',
    creation: '2026-06-01',
    allowed_transitions: ['Chọn phương án'],
    ...over,
  }
}

function mountView() {
  return mount(DecisionDetailView, {
    props: { id: 'PD-2026-00001' },
    global: { stubs, mocks: { $router: { back: backSpy, push: vi.fn() } } },
  })
}

function actionCount(w: ReturnType<typeof mountView>): number {
  return (
    w.findAll('[data-testid="detail-actions"]').length
    + w.findAll('[data-testid="workflow-action"]').length
    + w.findAll('[data-testid="cta-award"]').length
    + w.findAll('[data-testid="cta-record-contract"]').length
  )
}

function reloadButton(w: ReturnType<typeof mountView>) {
  return w.findAll('button').find((b) => b.text().includes('Thử lại'))
}

beforeEach(() => {
  setActivePinia(createPinia())
  getDecision.mockReset()
  backSpy.mockClear()
})

describe('DecisionDetailView — 4 trạng thái loại trừ (TC-UX4-31)', () => {
  it('a) ĐANG TẢI ⇒ khung xương, KHÔNG nội dung, KHÔNG panel thao tác', async () => {
    let release: (v: DecisionFixture) => void = () => {}
    getDecision.mockReturnValue(new Promise<DecisionFixture>((r) => { release = r }))
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('loading')
    expect(w.find('[data-testid="detail-skeleton"]').exists()).toBe(true)
    expect(w.find('[data-testid="detail-content"]').exists()).toBe(false)
    expect(actionCount(w)).toBe(0)
    release(fixture())
    await flushPromises()
  })

  it('b) 404 ⇒ kind=notfound + tiêu đề vẫn hiện mã, 0 «Thử lại», 0 nút workflow', async () => {
    getDecision.mockRejectedValue(new ApiError('Không tìm thấy', ErrorCode.NOT_FOUND, 404))
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('notfound')
    expect(w.find('h1').text()).toBe('PD-2026-00001')
    expect(reloadButton(w)).toBeUndefined()
    expect(actionCount(w)).toBe(0)
    const back = w.findAll('button').find((b) => b.text().includes('Về danh sách quyết định mua sắm'))
    expect(back).toBeTruthy()
    await back!.trigger('click')
    expect(backSpy).toHaveBeenCalled()
  })

  it('c) 403 ⇒ kind=forbidden, message THẬT, 0 «Thử lại», 0 nút workflow', async () => {
    getDecision.mockRejectedValue(
      new ApiError('Bạn không có quyền xem quyết định này.', ErrorCode.FORBIDDEN, 403),
    )
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('forbidden')
    expect(w.text()).toContain('Bạn không có quyền xem quyết định này.')
    expect(reloadButton(w)).toBeUndefined()
    expect(actionCount(w)).toBe(0)
  })

  it('d) lỗi MẠNG ⇒ kind=unknown + «Thử lại» ⇒ lần 2 OK thì banner tan, nút workflow trở lại', async () => {
    getDecision.mockRejectedValue(new Error('Network Error'))
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('unknown')
    expect(getDecision).toHaveBeenCalledTimes(1)
    getDecision.mockResolvedValue(fixture())
    await reloadButton(w)!.trigger('click')
    await flushPromises()
    expect(getDecision).toHaveBeenCalledTimes(2)
    expect(w.find('[data-testid="detail-load-error"]').exists()).toBe(false)
    expect(w.find('[data-testid="detail-content"]').exists()).toBe(true)
    expect(w.find('[data-testid="detail-actions"]').exists()).toBe(true)
  })

  it('e) nạp trả null ⇒ notfound RIÊNG (thay dòng «Không có dữ liệu» cũ)', async () => {
    getDecision.mockResolvedValue(null)
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('notfound')
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('notfound')
    expect(actionCount(w)).toBe(0)
  })

  it('f) CONTENT ⇒ nội dung + panel thao tác + nút workflow đúng allowed_transitions', async () => {
    getDecision.mockResolvedValue(fixture({ allowed_transitions: ['Chọn phương án'] }))
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('content')
    expect(w.find('[data-testid="detail-actions"]').exists()).toBe(true)
    const actions = w.findAll('[data-testid="workflow-action"]').map((b) => b.attributes('data-action'))
    expect(actions).toEqual(['Chọn phương án'])
    expect(w.text()).toContain('TS-2026-0001')
  })

  it('g) §7.15 — mở bản ghi khác bị lỗi KHÔNG nháy dữ liệu bản ghi trước', async () => {
    getDecision.mockResolvedValue(fixture())
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('content')
    getDecision.mockRejectedValue(new ApiError('Không tìm thấy', ErrorCode.NOT_FOUND, 404))
    // Điều hướng sang mã khác = gọi lại chính hàm nạp (retry dùng chung đường đi).
    const load = (w.vm as unknown as { load?: () => Promise<void> }).load
    expect(load, 'view phải phơi hàm nạp qua setup state để retry dùng lại').toBeTypeOf('function')
    await load!()
    await flushPromises()
    expect(getDecision).toHaveBeenCalledTimes(2)
    // `store.currentDecision` được dọn về null trong catch ⇒ không nháy dữ liệu cũ.
    expect(w.find('[data-testid="detail-content"]').exists()).toBe(false)
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('notfound')
  })
})

describe('TC-UX4-31 — chống tái phát ngõ cụt tự chế (DecisionDetailView)', () => {
  const src = readFileSync(
    resolve(dirname(fileURLToPath(import.meta.url)), '..', 'DecisionDetailView.vue'),
    'utf8',
  )

  it('0 `text-red-500` · 0 `page-container` · 0 nhánh `v-else-if="!…"`', () => {
    expect(src.match(/text-red-500/g) ?? []).toEqual([])
    expect(src.match(/page-container/g) ?? []).toEqual([])
    expect(src.match(/v-else-if="!/g) ?? []).toEqual([])
  })

  it('0 nhánh tự quyết trạng thái TẢI, và §7.14 vẫn giữ (0 `workflow_state ===`)', () => {
    expect(src.match(/v-(?:if|else-if)="[^"]*\bloading\b[^"]*"/g) ?? []).toEqual([])
    expect(src.match(/workflow_state\s*===/g) ?? []).toEqual([])
    expect(src.match(/TRANSITIONS_BY_STATE/g) ?? []).toEqual([])
  })
})
