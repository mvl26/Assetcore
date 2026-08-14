// Copyright (c) 2026, AssetCore Team
// TC-UX4-26 — SparePartDetailView áp khuôn `DetailPageShell` (lô 1, AC-UX-048).
//
// RED trước fix: `load()` KHÔNG có `catch` (Promise.all 2 nguồn) ⇒ unhandled rejection,
// view kẹt ở nhánh `v-else-if="part"` false ⇒ TRANG TRẮNG; hai nút vòng đời «Chỉnh sửa»
// / «Ngừng sử dụng» nằm trong `PageHeader #actions` NGOÀI chuỗi trạng thái ⇒ vẫn bấm
// được trên phụ tùng không tồn tại.
//
// Sau fix: CTA nằm trong slot `#actions` của shell ⇒ tắt bằng CẤU TRÚC ở error/notfound.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { ApiError, ErrorCode } from '@/api/errors'

const pushSpy = vi.fn()
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { name: 'SP-0001' } }),
  useRouter: () => ({ push: pushSpy, back: vi.fn() }),
}))

vi.mock('@/composables/useCapabilities', () => ({
  useCapabilities: () => ({ can: () => true }),
}))

type PartFixture = Record<string, unknown>
const getSparePart = vi.fn<() => Promise<PartFixture | null>>()
vi.mock('@/api/inventory', () => ({
  getSparePart: () => getSparePart(),
  updateSparePart: vi.fn(),
  deleteSparePart: vi.fn(),
}))
vi.mock('@/api/purchase', () => ({
  getPartPurchases: vi.fn().mockResolvedValue([]),
}))

import SparePartDetailView from '@/views/inventory/SparePartDetailView.vue'

// Mount THẬT khuôn (bẫy §7.5).
const stubs = {
  PageHeader: {
    props: ['title'],
    template: '<div><h1>{{ title }}</h1><slot /><slot name="actions" /></div>',
  },
  SmartSelect: true,
  CurrencyInput: true,
  UomConverter: true,
}

function fixture(over: PartFixture = {}): PartFixture {
  return {
    name: 'SP-0001',
    part_code: 'PT-BOM-01',
    part_name: 'Bơm nhu động',
    stock_uom: 'Cái',
    unit_cost: 250000,
    min_stock_level: 2,
    max_stock_level: 10,
    manufacturer: 'Fresenius',
    is_active: 1,
    total_stock: 6,
    stock_by_warehouse: [],
    recent_movements: [],
    ...over,
  }
}

function mountView() {
  return mount(SparePartDetailView, { props: { name: 'SP-0001' }, global: { stubs } })
}

function actionCount(w: ReturnType<typeof mountView>): number {
  const ctas = w.findAll('button').filter((b) =>
    ['Chỉnh sửa', 'Ngừng sử dụng'].includes(b.text().trim()),
  ).length
  return w.findAll('[data-testid="detail-actions"]').length + ctas
}

function reloadButton(w: ReturnType<typeof mountView>) {
  return w.findAll('button').find((b) => b.text().includes('Thử lại'))
}

beforeEach(() => {
  getSparePart.mockReset()
  pushSpy.mockClear()
})

describe('SparePartDetailView — 4 trạng thái loại trừ (TC-UX4-26)', () => {
  it('a) ĐANG TẢI ⇒ khung xương, KHÔNG nội dung, KHÔNG panel thao tác', async () => {
    let release: (v: PartFixture) => void = () => {}
    getSparePart.mockReturnValue(new Promise<PartFixture>((r) => { release = r }))
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('loading')
    expect(w.find('[data-testid="detail-skeleton"]').exists()).toBe(true)
    expect(actionCount(w)).toBe(0)
    release(fixture())
    await flushPromises()
  })

  it('b) 404 ⇒ kind=notfound, hiện mã phụ tùng, 0 «Thử lại», 0 panel thao tác', async () => {
    getSparePart.mockRejectedValue(new ApiError('Không tìm thấy', ErrorCode.NOT_FOUND, 404))
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('notfound')
    expect(w.text()).toContain('SP-0001')
    expect(reloadButton(w)).toBeUndefined()
    expect(actionCount(w)).toBe(0)
    const back = w.findAll('button').find((b) => b.text().includes('Về danh mục phụ tùng'))
    expect(back).toBeTruthy()
    await back!.trigger('click')
    expect(pushSpy).toHaveBeenCalledWith('/spare-parts')
  })

  it('c) 403 ⇒ kind=forbidden, message THẬT, 0 «Thử lại», KHÔNG redirect', async () => {
    getSparePart.mockRejectedValue(
      new ApiError('Bạn không có quyền xem phụ tùng này.', ErrorCode.FORBIDDEN, 403),
    )
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('forbidden')
    expect(w.text()).toContain('Bạn không có quyền xem phụ tùng này.')
    expect(reloadButton(w)).toBeUndefined()
    expect(actionCount(w)).toBe(0)
    expect(pushSpy).not.toHaveBeenCalled()
  })

  it('d) lỗi MẠNG ⇒ kind=unknown + «Thử lại» ⇒ lần 2 OK thì banner tan, nội dung hiện', async () => {
    getSparePart.mockRejectedValue(new Error('Network Error'))
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('unknown')
    expect(getSparePart).toHaveBeenCalledTimes(1)
    getSparePart.mockResolvedValue(fixture())
    await reloadButton(w)!.trigger('click')
    await flushPromises()
    expect(getSparePart).toHaveBeenCalledTimes(2)
    expect(w.find('[data-testid="detail-load-error"]').exists()).toBe(false)
    expect(w.find('[data-testid="detail-content"]').exists()).toBe(true)
    expect(w.find('[data-testid="detail-actions"]').exists()).toBe(true)
  })

  it('e) nạp trả null ⇒ notfound RIÊNG, 0 panel thao tác', async () => {
    getSparePart.mockResolvedValue(null)
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('notfound')
    expect(actionCount(w)).toBe(0)
  })

  it('f) CONTENT ⇒ nội dung + panel thao tác + CTA «Ngừng sử dụng»', async () => {
    getSparePart.mockResolvedValue(fixture())
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('content')
    expect(w.find('[data-testid="detail-actions"]').exists()).toBe(true)
    expect(w.findAll('button').some((b) => b.text().trim() === 'Ngừng sử dụng')).toBe(true)
    expect(w.text()).toContain('Bơm nhu động')
  })
})

describe('TC-UX4-31 — chống tái phát ngõ cụt tự chế (SparePartDetailView)', () => {
  const src = readFileSync(
    resolve(dirname(fileURLToPath(import.meta.url)), '..', 'SparePartDetailView.vue'),
    'utf8',
  )

  it('0 `text-red-500` · 0 `page-container` · 0 nhánh `v-else-if="!…"`', () => {
    expect(src.match(/text-red-500/g) ?? []).toEqual([])
    expect(src.match(/page-container/g) ?? []).toEqual([])
    expect(src.match(/v-else-if="!/g) ?? []).toEqual([])
  })

  it('0 nhánh v-if/v-else-if tự quyết trạng thái TẢI', () => {
    expect(src.match(/v-(?:if|else-if)="[^"]*\bloading\b[^"]*"/g) ?? []).toEqual([])
  })
})
