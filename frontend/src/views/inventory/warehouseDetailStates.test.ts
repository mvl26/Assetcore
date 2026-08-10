// Copyright (c) 2026, AssetCore Team
// TC-UX4-25 + TC-UX4-30 — WarehouseDetailView áp khuôn `DetailPageShell` (lô 1, AC-UX-048).
//
// RED trước fix (`WarehouseDetailView.vue:26`): `catch` của `load()` gán lỗi nạp vào
// `toast`, mà `toast` render trong dải **MÀU XANH thành công** (`bg-emerald-50
// text-emerald-700`). Hệ thống hỏng ⇒ người dùng thấy băng xanh — LỖI GIẢ DẠNG
// THÀNH CÔNG, không nút nạp lại, không phân biệt 404/403/mạng.
//
// Sau fix: `toast` CHỈ còn phản hồi HÀNH ĐỘNG; lỗi nạp đi nhánh `errorKind` của shell.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { ApiError, ErrorCode } from '@/api/errors'

const pushSpy = vi.fn()
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { name: 'WH-KHO-01' } }),
  useRouter: () => ({ push: pushSpy, back: vi.fn() }),
}))

type WarehouseFixture = Record<string, unknown>
const getWarehouse = vi.fn<() => Promise<WarehouseFixture | null>>()
vi.mock('@/api/inventory', () => ({
  getWarehouse: () => getWarehouse(),
  updateWarehouse: vi.fn(),
  deleteWarehouse: vi.fn(),
}))

import WarehouseDetailView from './WarehouseDetailView.vue'

// Mount THẬT khuôn (bẫy §7.5) — chỉ stub picker/PageHeader.
const stubs = {
  PageHeader: {
    props: ['title'],
    template: '<div><h1>{{ title }}</h1><slot /><slot name="actions" /></div>',
  },
  SmartSelect: true,
  ApproverSelect: true,
}

function fixture(over: WarehouseFixture = {}): WarehouseFixture {
  return {
    name: 'WH-KHO-01',
    warehouse_name: 'Kho vật tư trung tâm',
    warehouse_code: 'KHO-TT',
    is_active: 1,
    manager: 'Trần Thủ Kho',
    stock_count: 2,
    total_value: 5000000,
    stock_items: [],
    ...over,
  }
}

function mountView() {
  return mount(WarehouseDetailView, { props: { name: 'WH-KHO-01' }, global: { stubs } })
}

function actionCount(w: ReturnType<typeof mountView>): number {
  const ctas = w.findAll('button').filter((b) =>
    ['Chỉnh sửa', 'Ngừng hoạt động'].includes(b.text().trim()),
  ).length
  return w.findAll('[data-testid="detail-actions"]').length + ctas
}

function reloadButton(w: ReturnType<typeof mountView>) {
  return w.findAll('button').find((b) => b.text().includes('Thử lại'))
}

beforeEach(() => {
  getWarehouse.mockReset()
  pushSpy.mockClear()
})

describe('WarehouseDetailView — 4 trạng thái loại trừ (TC-UX4-25)', () => {
  it('a) ĐANG TẢI ⇒ khung xương, KHÔNG nội dung, KHÔNG panel thao tác', async () => {
    let release: (v: WarehouseFixture) => void = () => {}
    getWarehouse.mockReturnValue(new Promise<WarehouseFixture>((r) => { release = r }))
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('loading')
    expect(w.find('[data-testid="detail-skeleton"]').exists()).toBe(true)
    expect(actionCount(w)).toBe(0)
    release(fixture())
    await flushPromises()
  })

  it('b) 404 ⇒ kind=notfound, hiện mã kho, 0 «Thử lại», có nút về danh sách', async () => {
    getWarehouse.mockRejectedValue(new ApiError('Không tìm thấy', ErrorCode.NOT_FOUND, 404))
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('notfound')
    expect(w.text()).toContain('WH-KHO-01')
    expect(reloadButton(w)).toBeUndefined()
    expect(actionCount(w)).toBe(0)
    const back = w.findAll('button').find((b) => b.text().includes('Về danh sách kho'))
    expect(back).toBeTruthy()
    await back!.trigger('click')
    expect(pushSpy).toHaveBeenCalledWith('/warehouses')
  })

  it('c) 403 ⇒ kind=forbidden, message THẬT, 0 «Thử lại», KHÔNG redirect', async () => {
    getWarehouse.mockRejectedValue(
      new ApiError('Bạn không có quyền xem kho này.', ErrorCode.FORBIDDEN, 403),
    )
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('forbidden')
    expect(w.text()).toContain('Bạn không có quyền xem kho này.')
    expect(reloadButton(w)).toBeUndefined()
    expect(pushSpy).not.toHaveBeenCalled()
  })

  it('d) lỗi MẠNG ⇒ kind=unknown + «Thử lại» ⇒ lần 2 thành công thì banner tan, nội dung hiện', async () => {
    getWarehouse.mockRejectedValue(new Error('Network Error'))
    const w = mountView()
    await flushPromises()
    expect(w.find('[data-testid="detail-load-error"]').attributes('data-kind')).toBe('unknown')
    expect(getWarehouse).toHaveBeenCalledTimes(1)
    getWarehouse.mockResolvedValue(fixture())
    await reloadButton(w)!.trigger('click')
    await flushPromises()
    expect(getWarehouse).toHaveBeenCalledTimes(2)
    expect(w.find('[data-testid="detail-load-error"]').exists()).toBe(false)
    expect(w.find('[data-testid="detail-content"]').exists()).toBe(true)
    expect(w.find('[data-testid="detail-actions"]').exists()).toBe(true)
  })

  it('e) nạp trả null ⇒ notfound RIÊNG, 0 panel thao tác', async () => {
    getWarehouse.mockResolvedValue(null)
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('notfound')
    expect(actionCount(w)).toBe(0)
  })

  it('f) CONTENT ⇒ nội dung + panel thao tác + 2 CTA của kho đang hoạt động', async () => {
    getWarehouse.mockResolvedValue(fixture())
    const w = mountView()
    await flushPromises()
    expect(w.attributes('data-state')).toBe('content')
    expect(w.find('[data-testid="detail-actions"]').exists()).toBe(true)
    expect(w.findAll('button').some((b) => b.text().trim() === 'Ngừng hoạt động')).toBe(true)
    expect(w.text()).toContain('Kho vật tư trung tâm')
  })
})

describe('TC-UX4-30 — lỗi KHÔNG được giả dạng thành công (dải xanh emerald)', () => {
  it('getWarehouse reject ⇒ 0 phần tử dải-thành-công chứa chữ «Lỗi»; thông báo nằm trong [data-state="error"]', async () => {
    getWarehouse.mockRejectedValue(new ApiError('Máy chủ không phản hồi', ErrorCode.INTERNAL, 500))
    const w = mountView()
    await flushPromises()

    const successBanners = w.findAll('[class*="bg-emerald-50"]').filter((el) => el.text().includes('Lỗi'))
    expect(successBanners.map((el) => el.text()), 'lỗi nạp vẫn đang render trong dải MÀU XANH thành công').toEqual([])

    const shell = w.find('[data-state="error"]')
    expect(shell.exists()).toBe(true)
    expect(shell.find('[data-testid="detail-load-error"]').text()).toContain('Máy chủ không phản hồi')
  })

  it('chuỗi tự chế «Lỗi tải kho» đã biến mất khỏi mã nguồn (server quyết câu chữ)', () => {
    const src = readFileSync(
      resolve(dirname(fileURLToPath(import.meta.url)), 'WarehouseDetailView.vue'),
      'utf8',
    )
    expect(src.match(/Lỗi tải kho/g) ?? []).toEqual([])
    expect(src.match(/text-red-500/g) ?? []).toEqual([])
    expect(src.match(/page-container/g) ?? []).toEqual([])
    expect(src.match(/v-else-if="!/g) ?? []).toEqual([])
    expect(src.match(/v-(?:if|else-if)="[^"]*\bloading\b[^"]*"/g) ?? []).toEqual([])
  })
})
