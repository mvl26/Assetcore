// Copyright (c) 2026, AssetCore Team
// TC-UX4-30 — SupplierDetailView áp khuôn `DetailPageShell` (lô 1, AC-UX-048).
//
// RED trước fix: `PageHeader` + 2 nút «Sửa» / «Xóa» render NGOÀI chuỗi trạng thái, và
// nhánh 404 là "ngõ cụt tự chế" — một dòng chữ xám «Không tìm thấy nhà cung cấp.»
// KHÔNG nút quay lại, KHÔNG nạp lại. Tệ hơn: ref `error` DÙNG CHUNG cho cả lượt nạp và
// hành động `remove()`, nên nối thẳng vào shell thì một lần bấm Xóa hỏng sẽ xoá trắng
// cả bản ghi đang xem.
//
// Sau fix: lỗi NẠP dùng ref MỚI; `error` chỉ còn phục vụ `remove()`.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { ApiError, ErrorCode } from '@/api/errors'

const pushSpy = vi.fn()
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'SUP-2026-00012' } }),
  useRouter: () => ({ push: pushSpy, back: vi.fn() }),
}))

type SupplierFixture = Record<string, unknown>
const getSupplier = vi.fn<() => Promise<SupplierFixture | null>>()
vi.mock('@/api/imm00', () => ({
  getSupplier: () => getSupplier(),
  deleteSupplier: vi.fn(),
}))
vi.mock('@/api/purchase', () => ({
  listPurchases: vi.fn().mockResolvedValue({ data: [], total: 0 }),
}))

import SupplierDetailView from './SupplierDetailView.vue'

// Mount THẬT khuôn (bẫy §7.5).
const stubs = {
  PageHeader: {
    props: ['title'],
    template: '<div><h1>{{ title }}</h1><slot /><slot name="actions" /></div>',
  },
}

function fixture(over: SupplierFixture = {}): SupplierFixture {
  return {
    name: 'SUP-2026-00012',
    supplier_name: 'Công ty TNHH Thiết bị Y tế Minh Anh',
    vendor_type: 'Distributor',
    country: 'Việt Nam',
    is_active: 1,
    email_id: 'lienhe@minhanh.vn',
    ...over,
  }
}

function mountView() {
  return mount(SupplierDetailView, { global: { stubs } })
}

function actionCount(w: ReturnType<typeof mountView>): number {
  const ctas = w.findAll('button').filter((b) => ['Sửa', 'Xóa'].includes(b.text().trim())).length
  return w.findAll('[data-testid="detail-actions"]').length + ctas
}

function reloadButton(w: ReturnType<typeof mountView>) {
  return w.findAll('button').find((b) => b.text().includes('Thử lại'))
}

beforeEach(() => {
  getSupplier.mockReset()
  pushSpy.mockClear()
})

describe('SupplierDetailView — 4 trạng thái loại trừ (TC-UX4-30)', () => {
  it('a) ĐANG TẢI ⇒ khung xương, KHÔNG nội dung, KHÔNG panel thao tác', async () => {
    let release: (v: SupplierFixture) => void = () => {}
    getSupplier.mockReturnValue(new Promise<SupplierFixture>((r) => { release = r }))
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('loading')
    expect(w.find('[data-testid="detail-skeleton"]').exists()).toBe(true)
    expect(w.find('[data-testid="detail-content"]').exists()).toBe(false)
    expect(actionCount(w)).toBe(0)
    release(fixture())
    await flushPromises()
  })

  it('b) 404 ⇒ kind=notfound, hiện mã, có nút quay về, 0 «Thử lại», 0 nút Sửa/Xóa', async () => {
    getSupplier.mockRejectedValue(new ApiError('Không tìm thấy', ErrorCode.NOT_FOUND, 404))
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('notfound')
    expect(w.text()).toContain('SUP-2026-00012')
    // tiêu đề vẫn hiện (slot #title null-safe) ⇒ không phải trang trắng.
    expect(w.find('h1').text()).toBe('Chi tiết nhà cung cấp')
    expect(reloadButton(w)).toBeUndefined()
    expect(actionCount(w)).toBe(0)
    const back = w.findAll('button').find((b) => b.text().includes('Về danh sách nhà cung cấp'))
    expect(back).toBeTruthy()
    await back!.trigger('click')
    expect(pushSpy).toHaveBeenCalledWith('/suppliers')
  })

  it('c) 403 ⇒ kind=forbidden, message THẬT, 0 «Thử lại», KHÔNG redirect', async () => {
    getSupplier.mockRejectedValue(
      new ApiError('Bạn không có quyền xem nhà cung cấp này.', ErrorCode.FORBIDDEN, 403),
    )
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('forbidden')
    expect(w.text()).toContain('Bạn không có quyền xem nhà cung cấp này.')
    expect(reloadButton(w)).toBeUndefined()
    expect(actionCount(w)).toBe(0)
    expect(pushSpy).not.toHaveBeenCalled()
  })

  it('d) lỗi MẠNG ⇒ kind=unknown + «Thử lại» ⇒ lần 2 OK thì banner tan, nội dung hiện', async () => {
    getSupplier.mockRejectedValue(new Error('Network Error'))
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('unknown')
    expect(getSupplier).toHaveBeenCalledTimes(1)
    getSupplier.mockResolvedValue(fixture())
    await reloadButton(w)!.trigger('click')
    await flushPromises()
    expect(getSupplier).toHaveBeenCalledTimes(2)
    expect(w.find('[data-testid="detail-load-error"]').exists()).toBe(false)
    expect(w.find('[data-testid="detail-content"]').exists()).toBe(true)
    expect(w.find('[data-testid="detail-actions"]').exists()).toBe(true)
  })

  it('e) nạp trả null ⇒ notfound RIÊNG (thay nhánh 404 tự chế cũ)', async () => {
    getSupplier.mockResolvedValue(null)
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('notfound')
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('notfound')
    expect(actionCount(w)).toBe(0)
  })

  it('f) CONTENT ⇒ nội dung + panel thao tác + 2 CTA Sửa/Xóa', async () => {
    getSupplier.mockResolvedValue(fixture())
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('content')
    expect(w.find('[data-testid="detail-actions"]').exists()).toBe(true)
    expect(w.findAll('button').some((b) => b.text().trim() === 'Sửa')).toBe(true)
    expect(w.findAll('button').some((b) => b.text().trim() === 'Xóa')).toBe(true)
    expect(w.text()).toContain('Công ty TNHH Thiết bị Y tế Minh Anh')
  })
})

describe('TC-UX4-31 — chống tái phát ngõ cụt tự chế (SupplierDetailView)', () => {
  const src = readFileSync(
    resolve(dirname(fileURLToPath(import.meta.url)), 'SupplierDetailView.vue'),
    'utf8',
  )

  it('0 `text-red-500` · 0 `page-container` · 0 nhánh `v-else-if="!…"` (404 tự chế)', () => {
    expect(src.match(/text-red-500/g) ?? []).toEqual([])
    expect(src.match(/page-container/g) ?? []).toEqual([])
    expect(src.match(/v-else-if="!/g) ?? []).toEqual([])
  })

  it('0 nhánh tự quyết trạng thái TẢI', () => {
    expect(src.match(/v-(?:if|else-if)="[^"]*\bloading\b[^"]*"/g) ?? []).toEqual([])
  })
})
