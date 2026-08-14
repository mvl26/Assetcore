// Copyright (c) 2026, AssetCore Team
// TC-UX4-29 — FindingDetailView áp khuôn `DetailPageShell` (lô 1, AC-UX-048).
//
// RED trước fix (`FindingDetailView.vue:33`): `catch` NUỐT lỗi vào `console.error(e)`
// ⇒ người dùng nhận TRANG TRẮNG hoàn toàn (không thông báo, không nạp lại, không quay
// lại) cho mọi loại lỗi nạp; 6 CTA vòng đời nằm trong `PageHeader #actions` NGOÀI chuỗi
// trạng thái nên vẫn hiện trên bản ghi hỏng.
//
// Sau fix: 3 nhánh lỗi kind-aware + CTA trong slot `#actions` ⇒ tắt bằng CẤU TRÚC.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { createPinia, setActivePinia } from 'pinia'
import { ApiError, ErrorCode } from '@/api/errors'

const pushSpy = vi.fn()
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'FND-2026-00001' } }),
  useRouter: () => ({ push: pushSpy, back: vi.fn() }),
}))

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ loading: { value: false }, run: (fn: () => Promise<unknown>) => fn() }),
}))
vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))
vi.mock('@/stores/imm16', () => ({
  useImm16Store: () => ({
    actionStartReview: vi.fn(),
    actionConfirmFinding: vi.fn(),
    actionMarkFalsePositive: vi.fn(),
    actionWaiveFinding: vi.fn(),
    actionLinkToCapa: vi.fn(),
    actionCreateCapaFromFinding: vi.fn(),
  }),
}))

type FindingFixture = Record<string, unknown>
const getFinding = vi.fn<() => Promise<FindingFixture | null>>()
vi.mock('@/api/imm16', () => ({ getFinding: () => getFinding() }))

import FindingDetailView from '@/views/compliance/FindingDetailView.vue'

// Mount THẬT khuôn (bẫy §7.5) — SkeletonLoader cũng KHÔNG stub.
const stubs = {
  PageHeader: {
    props: ['title'],
    template: '<div><h1>{{ title }}</h1><slot /><slot name="actions" /></div>',
  },
  StatusBadge: true,
  BaseModal: true,
  DateInput: true,
  RecordHistory: true,
}

function fixture(over: FindingFixture = {}): FindingFixture {
  return {
    name: 'FND-2026-00001',
    rule: 'R-IMM08-PM-90',
    rule_name: 'Tỷ lệ bảo trì định kỳ đạt 90%',
    severity: 'Major',
    status: 'Open',
    detected_date: '2026-01-01',
    evaluation_date: '2026-01-02',
    allowed_transitions: ['Under Review'],
    can_create_capa: false,
    ...over,
  }
}

function mountView() {
  return mount(FindingDetailView, { props: { id: 'FND-2026-00001' }, global: { stubs } })
}

function actionCount(w: ReturnType<typeof mountView>): number {
  return (
    w.findAll('[data-testid="detail-actions"]').length
    + w.findAll('[data-testid="cta-start-review"]').length
    + w.findAll('[data-testid="cta-confirm"]').length
    + w.findAll('[data-testid="cta-mark-false"]').length
    + w.findAll('[data-testid="cta-waive"]').length
    + w.findAll('[data-testid="cta-create-capa"]').length
    + w.findAll('[data-testid="cta-link-capa"]').length
  )
}

function reloadButton(w: ReturnType<typeof mountView>) {
  return w.findAll('button').find((b) => b.text().includes('Thử lại'))
}

beforeEach(() => {
  setActivePinia(createPinia())
  getFinding.mockReset()
  pushSpy.mockClear()
})

describe('FindingDetailView — 4 trạng thái loại trừ (TC-UX4-29)', () => {
  it('a) ĐANG TẢI ⇒ khung xương form 6 dòng, KHÔNG nội dung, KHÔNG panel thao tác', async () => {
    let release: (v: FindingFixture) => void = () => {}
    getFinding.mockReturnValue(new Promise<FindingFixture>((r) => { release = r }))
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('loading')
    expect(w.find('[data-testid="detail-skeleton"]').exists()).toBe(true)
    expect(w.find('[data-testid="detail-content"]').exists()).toBe(false)
    expect(actionCount(w)).toBe(0)
    release(fixture())
    await flushPromises()
  })

  it('b) 404 ⇒ kind=notfound, hiện mã phát hiện, 0 «Thử lại», 0 CTA', async () => {
    getFinding.mockRejectedValue(new ApiError('Không tìm thấy', ErrorCode.NOT_FOUND, 404))
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('notfound')
    expect(w.text()).toContain('FND-2026-00001')
    expect(reloadButton(w)).toBeUndefined()
    expect(actionCount(w)).toBe(0)
    const back = w.findAll('button').find((b) => b.text().includes('Về danh sách phát hiện'))
    expect(back).toBeTruthy()
    await back!.trigger('click')
    expect(pushSpy).toHaveBeenCalledWith('/compliance/findings')
  })

  it('c) 403 ⇒ kind=forbidden, message THẬT, 0 «Thử lại», KHÔNG redirect', async () => {
    getFinding.mockRejectedValue(
      new ApiError('Bạn không có quyền xem phát hiện này.', ErrorCode.FORBIDDEN, 403),
    )
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('forbidden')
    expect(w.text()).toContain('Bạn không có quyền xem phát hiện này.')
    expect(reloadButton(w)).toBeUndefined()
    expect(actionCount(w)).toBe(0)
    expect(pushSpy).not.toHaveBeenCalled()
  })

  it('d) lỗi MẠNG ⇒ kind=unknown + «Thử lại» ⇒ lần 2 OK thì banner tan, CTA trở lại', async () => {
    getFinding.mockRejectedValue(new Error('Network Error'))
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('unknown')
    expect(getFinding).toHaveBeenCalledTimes(1)
    getFinding.mockResolvedValue(fixture())
    await reloadButton(w)!.trigger('click')
    await flushPromises()
    expect(getFinding).toHaveBeenCalledTimes(2)
    expect(w.find('[data-testid="detail-load-error"]').exists()).toBe(false)
    expect(w.find('[data-testid="detail-content"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-start-review"]').exists()).toBe(true)
  })

  it('e) nạp trả null ⇒ notfound RIÊNG, 0 panel thao tác', async () => {
    getFinding.mockResolvedValue(null)
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('notfound')
    expect(actionCount(w)).toBe(0)
  })

  it('f) CONTENT ⇒ nội dung + panel thao tác + CTA gate theo allowed_transitions', async () => {
    getFinding.mockResolvedValue(
      fixture({ allowed_transitions: ['Confirmed NC', 'False Positive'], status: 'Under Review' }),
    )
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('content')
    expect(w.find('[data-testid="detail-actions"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-confirm"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-mark-false"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-start-review"]').exists()).toBe(false)
  })
})

describe('TC-UX4-31 — chống tái phát ngõ cụt tự chế (FindingDetailView)', () => {
  const src = readFileSync(
    resolve(dirname(fileURLToPath(import.meta.url)), '..', 'FindingDetailView.vue'),
    'utf8',
  )

  it('0 `text-red-500` · 0 `page-container` · 0 nhánh `v-else-if="!…"`', () => {
    expect(src.match(/text-red-500/g) ?? []).toEqual([])
    expect(src.match(/page-container/g) ?? []).toEqual([])
    expect(src.match(/v-else-if="!/g) ?? []).toEqual([])
  })

  it('0 nhánh tự quyết trạng thái TẢI và 0 `console.error` nuốt lỗi nạp', () => {
    expect(src.match(/v-(?:if|else-if)="[^"]*\bloading\b[^"]*"/g) ?? []).toEqual([])
    expect(src.match(/console\.error/g) ?? []).toEqual([])
  })
})
