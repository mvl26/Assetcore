// Copyright (c) 2026, AssetCore Team
// TC-UX4-28 — FirmwareCrDetailView áp khuôn `DetailPageShell` (lô 1, AC-UX-048).
//
// RED trước fix: mọi lỗi nạp gộp vào MỘT chuỗi phẳng `err` rồi in ra một băng đỏ
// KHÔNG có nút nạp lại và KHÔNG có đường quay lại ⇒ 404 (mã sai), 403 (thiếu quyền)
// và mất mạng nhận CÙNG một câu chữ; người dùng hết đường đi tiếp.
//
// Sau fix: phân loại kind THẬT (notfound / forbidden / unknown) + lối thoát chuẩn của
// `DetailLoadError`; cụm CTA (Khôi phục / Phê duyệt / Đã triển khai) vào slot `#actions`.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { ApiError, ErrorCode } from '@/api/errors'

const pushSpy = vi.fn()
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'FCR-2026-00003' } }),
  useRouter: () => ({ push: pushSpy, back: vi.fn() }),
}))

vi.mock('@/composables/useApi', () => ({
  useApi: () => ({ loading: { value: false }, run: (fn: () => Promise<unknown>) => fn() }),
}))
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ show: vi.fn(), fromError: vi.fn(), confirm: vi.fn().mockResolvedValue(true) }),
}))

type FcrFixture = Record<string, unknown>
const getFirmwareCr = vi.fn<() => Promise<FcrFixture | null>>()
vi.mock('@/api/imm00', () => ({
  getFirmwareCr: () => getFirmwareCr(),
  transitionFirmwareCr: vi.fn(),
}))

import FirmwareCrDetailView from '@/views/document/FirmwareCrDetailView.vue'

// Mount THẬT khuôn (bẫy §7.5).
const stubs = {
  PageHeader: {
    props: ['title'],
    template: '<div><h1>{{ title }}</h1><slot /><slot name="actions" /></div>',
  },
  StatusBadge: true,
  BaseModal: { template: '<div><slot /><slot name="footer" /></div>' },
}

function fixture(over: FcrFixture = {}): FcrFixture {
  return {
    name: 'FCR-2026-00003',
    status: 'Draft',
    asset_ref: 'ACC-ASS-0001',
    asset_name: 'Máy thở Hamilton C3',
    version_before: '1.2.0',
    version_after: '1.3.1',
    allowed_transitions: ['Approved'],
    can_approve: true,
    ...over,
  }
}

function mountView() {
  return mount(FirmwareCrDetailView, { props: { id: 'FCR-2026-00003' }, global: { stubs } })
}

function actionCount(w: ReturnType<typeof mountView>): number {
  return (
    w.findAll('[data-testid="detail-actions"]').length
    + w.findAll('[data-testid="cta-approve"]').length
    + w.findAll('[data-testid="cta-deploy"]').length
    + w.findAll('[data-testid="cta-rollback"]').length
    + w.findAll('[data-testid="no-actions-hint"]').length
  )
}

function reloadButton(w: ReturnType<typeof mountView>) {
  return w.findAll('button').find((b) => b.text().includes('Thử lại'))
}

beforeEach(() => {
  getFirmwareCr.mockReset()
  pushSpy.mockClear()
})

describe('FirmwareCrDetailView — 4 trạng thái loại trừ (TC-UX4-28)', () => {
  it('a) ĐANG TẢI ⇒ khung xương, KHÔNG nội dung, KHÔNG panel thao tác', async () => {
    let release: (v: FcrFixture) => void = () => {}
    getFirmwareCr.mockReturnValue(new Promise<FcrFixture>((r) => { release = r }))
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('loading')
    expect(w.find('[data-testid="detail-skeleton"]').exists()).toBe(true)
    expect(actionCount(w)).toBe(0)
    release(fixture())
    await flushPromises()
  })

  it('b) 404 ⇒ kind=notfound + tiêu đề vẫn hiện mã, 0 «Thử lại», 0 CTA', async () => {
    getFirmwareCr.mockRejectedValue(new ApiError('Không tìm thấy', ErrorCode.NOT_FOUND, 404))
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('notfound')
    expect(w.find('h1').text()).toContain('FCR-2026-00003')
    expect(reloadButton(w)).toBeUndefined()
    expect(actionCount(w)).toBe(0)
    const back = w.findAll('button').find((b) => b.text().includes('Về danh sách yêu cầu thay đổi firmware'))
    expect(back).toBeTruthy()
    await back!.trigger('click')
    expect(pushSpy).toHaveBeenCalledWith('/cm/firmware')
  })

  it('c) 403 ⇒ kind=forbidden, message THẬT, 0 «Thử lại», KHÔNG redirect', async () => {
    getFirmwareCr.mockRejectedValue(
      new ApiError('Bạn không có quyền xem yêu cầu này.', ErrorCode.FORBIDDEN, 403),
    )
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('forbidden')
    expect(w.text()).toContain('Bạn không có quyền xem yêu cầu này.')
    expect(reloadButton(w)).toBeUndefined()
    expect(actionCount(w)).toBe(0)
    expect(pushSpy).not.toHaveBeenCalled()
  })

  it('d) lỗi MẠNG ⇒ kind=unknown + «Thử lại» ⇒ lần 2 OK thì banner tan, CTA trở lại', async () => {
    getFirmwareCr.mockRejectedValue(new Error('Network Error'))
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('unknown')
    expect(getFirmwareCr).toHaveBeenCalledTimes(1)
    getFirmwareCr.mockResolvedValue(fixture())
    await reloadButton(w)!.trigger('click')
    await flushPromises()
    expect(getFirmwareCr).toHaveBeenCalledTimes(2)
    expect(w.find('[data-testid="detail-load-error"]').exists()).toBe(false)
    expect(w.find('[data-testid="detail-content"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-approve"]').exists()).toBe(true)
  })

  it('e) nạp trả null ⇒ notfound RIÊNG, 0 panel thao tác', async () => {
    getFirmwareCr.mockResolvedValue(null)
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('notfound')
    expect(actionCount(w)).toBe(0)
  })

  it('f) CONTENT ⇒ nội dung + panel thao tác + CTA gate theo allowed_transitions (GATE-8)', async () => {
    getFirmwareCr.mockResolvedValue(fixture({ allowed_transitions: ['Applied'], can_approve: false }))
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('content')
    expect(w.find('[data-testid="detail-actions"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-deploy"]').exists()).toBe(true)
    expect(w.find('[data-testid="cta-approve"]').exists()).toBe(false)
  })
})

describe('TC-UX4-31 — chống tái phát ngõ cụt tự chế (FirmwareCrDetailView)', () => {
  const src = readFileSync(
    resolve(dirname(fileURLToPath(import.meta.url)), '..', 'FirmwareCrDetailView.vue'),
    'utf8',
  )

  it('1 chỗ `text-red-500` đã đổi sang token `text-danger-500` (dấu sao GIỮ NGUYÊN)', () => {
    expect(src.match(/text-red-500/g) ?? []).toEqual([])
    expect((src.match(/text-danger-500/g) ?? []).length).toBe(1)
  })

  it('0 `page-container` · 0 nhánh `v-else-if="!…"` · 0 nhánh tự quyết trạng thái TẢI', () => {
    expect(src.match(/page-container/g) ?? []).toEqual([])
    expect(src.match(/v-else-if="!/g) ?? []).toEqual([])
    expect(src.match(/v-(?:if|else-if)="[^"]*\bloading\b[^"]*"/g) ?? []).toEqual([])
  })
})
