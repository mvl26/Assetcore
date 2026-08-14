// Copyright (c) 2026, AssetCore Team
// TC-UX4-24 — StockMovementDetailView áp khuôn `DetailPageShell` (lô 1, AC-UX-048).
//
// RED trước fix: `load()` KHÔNG có `catch` ⇒ ApiError nổi lên thành unhandled
// rejection, view rơi vào nhánh `v-else-if="doc"` false ⇒ **trang trắng câm**:
// không thông báo, không nút nạp lại, không đường quay lại. Đồng thời `loading`
// khởi tạo `false` ⇒ nháy trạng thái rỗng một nhịp trước lượt nạp đầu.
//
// Sau fix: 4 trạng thái LOẠI TRỪ do shell quyết bằng CẤU TRÚC + phân loại kind
// THẬT (404 / 403 / mạng) + panel thao tác TẮT ngoài trạng thái có-dữ-liệu.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { ApiError, ErrorCode } from '@/api/errors'
import type { StockMovement } from '@/types/inventory'

const pushSpy = vi.fn()
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { name: 'SM-2026-00001' } }),
  useRouter: () => ({ push: pushSpy, back: vi.fn() }),
}))

const getStockMovement = vi.fn<() => Promise<StockMovement | null>>()
vi.mock('@/api/inventory', () => ({
  getStockMovement: () => getStockMovement(),
  submitStockMovement: vi.fn(),
  cancelStockMovement: vi.fn(),
  deleteStockMovement: vi.fn(),
}))

import StockMovementDetailView from '@/views/inventory/StockMovementDetailView.vue'

// KHÔNG stub DetailPageShell / DetailLoadError / SkeletonLoader — mount THẬT (bẫy §7.5):
// stub khuôn làm mọi assert về `detail-actions` / `detail-content` XANH GIẢ.
const stubs = {
  PageHeader: { template: '<div><slot /><slot name="actions" /></div>' },
  StatusBadge: true,
}

function fixture(over: Partial<StockMovement> = {}): StockMovement {
  return {
    name: 'SM-2026-00001',
    movement_type: 'Receipt',
    status: 'Draft',
    docstatus: 0,
    movement_date: '2026-01-05 08:00:00',
    requested_by: 'kho@benhvien.vn',
    requested_by_name: 'Nguyễn Văn Kho',
    total_value: 1200000,
    items: [],
    ...over,
  } as unknown as StockMovement
}

function mountView() {
  return mount(StockMovementDetailView, { props: { name: 'SM-2026-00001' }, global: { stubs } })
}

/** Panel thao tác + CTA cụ thể — 2 lớp assert (§12.6). */
function actionCount(w: ReturnType<typeof mountView>): number {
  const ctas = w.findAll('button').filter((b) =>
    ['Duyệt phiếu', 'Huỷ phiếu', 'Chỉnh sửa', 'Xoá'].includes(b.text().trim()),
  ).length
  return w.findAll('[data-testid="detail-actions"]').length + ctas
}

function reloadButton(w: ReturnType<typeof mountView>) {
  return w.findAll('button').find((b) => b.text().includes('Thử lại'))
}

beforeEach(() => {
  getStockMovement.mockReset()
  pushSpy.mockClear()
})

describe('StockMovementDetailView — 4 trạng thái loại trừ (TC-UX4-24)', () => {
  it('a) ĐANG TẢI ⇒ khung xương, KHÔNG nội dung, KHÔNG panel thao tác', async () => {
    let release: (v: StockMovement) => void = () => {}
    getStockMovement.mockReturnValue(new Promise<StockMovement>((r) => { release = r }))
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('loading')
    expect(w.find('[data-testid="detail-skeleton"]').exists()).toBe(true)
    expect(w.find('[data-testid="detail-content"]').exists()).toBe(false)
    expect(actionCount(w)).toBe(0)
    release(fixture())
    await flushPromises()
  })

  it('b) 404 in-envelope ⇒ kind=notfound, hiện mã đã gõ, 0 «Thử lại», 0 panel thao tác', async () => {
    getStockMovement.mockRejectedValue(new ApiError('Không tìm thấy', ErrorCode.NOT_FOUND, 404))
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('error')
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('notfound')
    expect(w.text()).toContain('SM-2026-00001')
    expect(reloadButton(w)).toBeUndefined()
    expect(actionCount(w)).toBe(0)
    const back = w.findAll('button').find((b) => b.text().includes('Về danh sách phiếu kho'))
    expect(back).toBeTruthy()
    await back!.trigger('click')
    expect(pushSpy).toHaveBeenCalledWith('/stock-movements')
  })

  it('c) 403 in-envelope ⇒ kind=forbidden, message THẬT, 0 «Thử lại», KHÔNG redirect', async () => {
    getStockMovement.mockRejectedValue(
      new ApiError('Bạn không có quyền xem phiếu kho này.', ErrorCode.FORBIDDEN, 403),
    )
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('forbidden')
    expect(w.text()).toContain('Bạn không có quyền xem phiếu kho này.')
    expect(reloadButton(w)).toBeUndefined()
    expect(actionCount(w)).toBe(0)
    expect(pushSpy).not.toHaveBeenCalled()
  })

  it('d) lỗi MẠNG ⇒ kind=unknown + «Thử lại» gọi lại hàm nạp (lần 2)', async () => {
    getStockMovement.mockRejectedValue(new Error('Network Error'))
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('unknown')
    expect(getStockMovement).toHaveBeenCalledTimes(1)
    getStockMovement.mockResolvedValue(fixture())
    await reloadButton(w)!.trigger('click')
    await flushPromises()
    expect(getStockMovement).toHaveBeenCalledTimes(2)
    // INV-UX4-7 — lỗi bị xoá ở ĐẦU lượt ⇒ banner biến mất và nội dung hiện.
    expect(w.find('[data-testid="detail-load-error"]').exists()).toBe(false)
    expect(w.find('[data-testid="detail-content"]').exists()).toBe(true)
    expect(w.find('[data-testid="detail-actions"]').exists()).toBe(true)
  })

  it('e) nạp trả null ⇒ nhánh notfound RIÊNG (không phải khung «—»)', async () => {
    getStockMovement.mockResolvedValue(null)
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('notfound')
    expect(w.find('[data-testid="detail-content"]').exists()).toBe(false)
    expect(actionCount(w)).toBe(0)
  })

  it('f) CONTENT ⇒ nội dung + panel thao tác + CTA vòng đời của phiếu nháp', async () => {
    getStockMovement.mockResolvedValue(fixture({ docstatus: 0 } as Partial<StockMovement>))
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('content')
    expect(w.find('[data-testid="detail-content"]').exists()).toBe(true)
    expect(w.find('[data-testid="detail-actions"]').exists()).toBe(true)
    expect(w.findAll('button').some((b) => b.text().trim() === 'Duyệt phiếu')).toBe(true)
    expect(w.find('[data-testid="detail-load-error"]').exists()).toBe(false)
  })
})

describe('TC-UX4-31 — chống tái phát ngõ cụt tự chế (StockMovementDetailView)', () => {
  const src = readFileSync(
    resolve(dirname(fileURLToPath(import.meta.url)), '..', 'StockMovementDetailView.vue'),
    'utf8',
  )

  it('0 `text-red-500` · 0 `page-container` · 0 nhánh `v-else-if="!…"`', () => {
    expect(src.match(/text-red-500/g) ?? []).toEqual([])
    expect(src.match(/page-container/g) ?? []).toEqual([])
    expect(src.match(/v-else-if="!/g) ?? []).toEqual([])
  })

  it('0 nhánh v-if/v-else-if tự quyết trạng thái TẢI (shell quyết bằng prop)', () => {
    expect(src.match(/v-(?:if|else-if)="[^"]*\bloading\b[^"]*"/g) ?? []).toEqual([])
  })
})
