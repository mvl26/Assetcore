// Copyright (c) 2026, AssetCore Team
// TDD vòng 4 — ManagementReviewDetailView áp khuôn `DetailPageShell`.
//
// Nợ đóng ở đây: CTA vòng đời trước nằm trong `#actions` của PageHeader — vùng đó
// nằm NGOÀI chuỗi trạng thái nên panel thao tác có thể hiện cạnh khung chi tiết rỗng.
// Sau fix, `#actions` là slot của shell ⇒ chỉ tồn tại ở trạng thái có-dữ-liệu.
// `no-actions-hint` cũng vậy: hint "bạn không có quyền chuyển trạng thái" mà hiện
// trên một bản ghi 404 là thông tin SAI.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import type { VueWrapper } from '@vue/test-utils'
import { ApiError, ErrorCode } from '@/api/errors'
import type { ManagementReview } from '@/api/imm16'

const pushSpy = vi.fn()
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'MR-2099-Q1' } }),
  useRouter: () => ({ push: pushSpy, back: vi.fn() }),
}))

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ loading: { value: false }, run: (fn: () => Promise<unknown>) => fn() }),
}))

const getManagementReviewSpy = vi.fn()
vi.mock('@/api/imm16', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/imm16')>()
  return { ...actual, getManagementReview: () => getManagementReviewSpy() }
})

vi.mock('@/stores/imm16', () => ({
  useImm16Store: () => ({
    actionAdvanceMr: vi.fn().mockResolvedValue({ status: 'Held' }),
    actionFinalizeReview: vi.fn().mockResolvedValue({ status: 'Closed' }),
    actionUpdateReview: vi.fn(),
  }),
}))

import ManagementReviewDetailView from './ManagementReviewDetailView.vue'

const stubs = {
  BaseModal: { template: '<div><slot /><slot name="footer" /></div>' },
  RecordHistory: { template: '<div />', methods: { reload() {} } },
  RouterLink: true,
}

function baseMr(over: Partial<ManagementReview> = {}): ManagementReview {
  return {
    name: 'MR-2099-Q1',
    quarter: 'Q1-2099',
    review_date: '2099-01-15',
    chair: 'Administrator',
    status: 'Draft',
    workflow_state: 'Draft',
    ...over,
  } as ManagementReview
}

function mountView() {
  return mount(ManagementReviewDetailView, { global: { stubs } })
}

function reloadButton(w: VueWrapper) {
  return w.findAll('button').find((b) => b.text().includes(['Thử', 'lại'].join(' ')))
}

beforeEach(() => {
  getManagementReviewSpy.mockReset()
  pushSpy.mockClear()
})

describe('ManagementReviewDetailView — 4 trạng thái loại trừ (TC-UX4-23)', () => {
  it('a) đang nạp ⇒ khung xương, 0 panel thao tác, 0 hint', async () => {
    getManagementReviewSpy.mockReturnValue(new Promise(() => {}))
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('loading')
    expect(w.find('[data-testid="detail-skeleton"]').exists()).toBe(true)
    expect(w.find('[data-testid="detail-actions"]').exists()).toBe(false)
    expect(w.find('[data-testid="no-actions-hint"]').exists()).toBe(false)
  })

  it('b) lỗi 500 ⇒ kind=unknown + nút nạp lại; 0 CTA, 0 hint', async () => {
    getManagementReviewSpy.mockRejectedValue(
      new ApiError('Máy chủ gặp sự cố', ErrorCode.INTERNAL, 500),
    )
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('unknown')
    expect(w.text()).toContain('Máy chủ gặp sự cố')
    expect(reloadButton(w)).toBeTruthy()
    expect(w.find('[data-testid="cta-advance"]').exists()).toBe(false)
    expect(w.find('[data-testid="cta-close"]').exists()).toBe(false)
    expect(w.find('[data-testid="no-actions-hint"]').exists()).toBe(false)
  })

  it('b2) bấm nạp lại ⇒ gọi lại lần 2 rồi ra nội dung thật', async () => {
    getManagementReviewSpy.mockRejectedValue(new ApiError('Lỗi', ErrorCode.INTERNAL, 500))
    const w = mountView()
    await flushPromises()
    getManagementReviewSpy.mockResolvedValue(baseMr())
    await reloadButton(w)!.trigger('click')
    await flushPromises()
    expect(getManagementReviewSpy).toHaveBeenCalledTimes(2)
    expect(w.attributes('data-state')).toBe('content')
  })

  it('c) 403 in-envelope ⇒ kind=forbidden, 0 nút nạp lại, KHÔNG điều hướng', async () => {
    getManagementReviewSpy.mockRejectedValue(
      new ApiError('Bạn không có quyền xem cuộc soát xét này.', ErrorCode.FORBIDDEN, 403),
    )
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('forbidden')
    expect(reloadButton(w)).toBeUndefined()
    expect(pushSpy).not.toHaveBeenCalled()
  })

  it('d) 404 ⇒ kind=notfound + nút quay về danh sách soát xét', async () => {
    getManagementReviewSpy.mockRejectedValue(
      new ApiError('Không tìm thấy', ErrorCode.NOT_FOUND, 404),
    )
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('notfound')
    expect(reloadButton(w)).toBeUndefined()
    const back = w.findAll('button').find((b) => b.text().includes('Về danh sách soát xét'))
    await back!.trigger('click')
    expect(pushSpy).toHaveBeenCalledWith('/compliance/mr')
  })

  it('e) nạp trả null ⇒ nhánh notfound (không khung rỗng)', async () => {
    getManagementReviewSpy.mockResolvedValue(null)
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('notfound')
    expect(w.find('[data-testid="detail-content"]').exists()).toBe(false)
  })

  it('f) nạp OK + allowed=[Held] + can_advance ⇒ content + cta-advance (hành vi cũ)', async () => {
    getManagementReviewSpy.mockResolvedValue(
      baseMr({ allowed_transitions: ['Held'], can_advance: true }),
    )
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('content')
    expect(w.find('[data-testid="cta-advance"]').exists()).toBe(true)
    expect(w.find('[data-testid="detail-actions"]').exists()).toBe(true)
  })
})

describe('ManagementReviewDetailView — no-actions-hint CHỈ ở content (A5)', () => {
  it('content + 0 transition ⇒ hint HIỆN (giải thích vì sao không có nút)', async () => {
    getManagementReviewSpy.mockResolvedValue(
      baseMr({ allowed_transitions: ['Held'], can_advance: false }),
    )
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="no-actions-hint"]').exists()).toBe(true)
  })

  for (const [label, err] of [
    ['unknown', new ApiError('Lỗi mạng', ErrorCode.NETWORK_ERROR, 0)],
    ['forbidden', new ApiError('Không có quyền', ErrorCode.FORBIDDEN, 403)],
    ['notfound', new ApiError('Không tìm thấy', ErrorCode.NOT_FOUND, 404)],
  ] as const) {
    it(`trạng thái ${label} ⇒ hint KHÔNG xuất hiện (thông tin sai trên bản ghi hỏng)`, async () => {
      getManagementReviewSpy.mockRejectedValue(err)
      const w = mountView()
      await flushPromises()
      expect(w.find('[data-testid="no-actions-hint"]').exists()).toBe(false)
      expect(w.find('[data-testid="detail-actions"]').exists()).toBe(false)
    })
  }
})
