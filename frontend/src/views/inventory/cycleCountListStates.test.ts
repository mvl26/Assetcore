// TC-UX3-39 (AC-UX-047 · lô 3) — /inventory/cycle-counts: 4 trạng thái danh sách + «Thử lại».
//
// Nợ đo trên đĩa 2026-08-04 (loại γ + ô lỗi DÙNG CHUNG, docs/ui-ux/02 §14.4):
// `:137-140` (banner lỗi) ⇄ `:141-148` (khối rỗng) đã loại trừ nhau, NHƯNG nguồn lỗi là
// `stores/imm15.ts:58` — một ô `error` dùng CHUNG cho cấp phát / xuất nhập / kiểm kê. Một lỗi
// phát sinh ở màn khác vẫn tô đỏ màn này (INV-UX3-28) ⇒ bắt buộc biến thể D: CHỤP lỗi ngay
// sau `await` của lượt nạp kiểm kê rồi trả ô dùng chung về sạch.
//
// `listWarehouses()` chỉ nạp danh mục cho ô lọc — hỏng thì chỉ mất danh mục, KHÔNG được vào
// `:error-message` (đã bọc `try/catch` sẵn ở view).
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { resetRouteMock } from '@/test/vueRouterMock'

enableAutoUnmount(afterEach)

const listCycleCountsSpy = vi.fn()
const listWarehousesSpy = vi.fn()

// ⚠️ HAI module khác nhau (đọc `import` THẬT, đừng tin bảng gợi ý §14.2):
//   · `stores/imm15.ts:13,17` lấy `listCycleCounts` từ `@/api/imm15`
//   · view lấy `listWarehouses` từ `@/api/inventory`
vi.mock('@/api/imm15', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  listCycleCounts: (...a: unknown[]) => listCycleCountsSpy(...a),
}))
vi.mock('@/api/inventory', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  listWarehouses: (...a: unknown[]) => listWarehousesSpy(...a),
}))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import CycleCountListView from './CycleCountListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const ROWS = [
  {
    name: 'CC-2026-0001', warehouse: 'WH-001', warehouse_name: 'Kho vật tư trung tâm',
    count_type: 'Full', count_date: '2026-07-01', variance_count: 2,
    variance_value: 1_500_000, status: 'Posted',
  },
  {
    name: 'CC-2026-0002', warehouse: 'WH-002', warehouse_name: 'Kho khoa Hồi sức',
    count_type: 'Cycle', count_date: '2026-07-15', variance_count: 0,
    variance_value: 0, status: 'Draft',
  },
]
// `stores/imm15.ts:119` đọc `res.data` (KHÔNG phải `res.items`).
const ok = (rows: unknown[]) => ({
  data: rows,
  pagination: { page: 1, page_size: 20, total: rows.length, total_pages: rows.length ? 1 : 0 },
})

const stubs = {
  PageHeader: { template: '<div><slot name="actions" /></div>' },
  FilterToggleButton: true,
  StatusBadge: true,
}

async function mountView() {
  const w = mount(CycleCountListView, { global: { stubs } })
  await flushPromises()
  return w
}
function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/inventory/cycle-counts — 4 trạng thái loại trừ + thử lại (TC-UX3-39)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetRouteMock()
    listCycleCountsSpy.mockReset().mockResolvedValue(ok(ROWS))
    listWarehousesSpy.mockReset().mockResolvedValue({ items: [] })
  })

  it('(a) đang tải ⇒ khung xương, 0 nội dung, 0 nút «Thử lại»', async () => {
    listCycleCountsSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.findAll('table')).toHaveLength(0)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + ĐÚNG 1 «Thử lại», 0 khối rỗng (:134 ⇄ :141)', async () => {
    listCycleCountsSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.text()).not.toContain('Chưa có phiếu kiểm kê nào')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(c) rỗng thật ⇒ ui-empty có câu hướng dẫn tiếng Việt + lối tạo', async () => {
    listCycleCountsSpy.mockResolvedValue(ok([]))
    const w = await mountView()
    expect(state(w)).toBe('empty')
    expect(w.findAll('[data-testid="ui-empty"]')).toHaveLength(1)
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Chưa có phiếu kiểm kê nào')
    expect(w.find('[data-testid="ui-empty-description"]').text()).toBe(
      'Phiếu kiểm kê dùng để đối chiếu tồn kho thực tế với sổ sách theo từng kho.',
    )
    expect(
      w.findAll('button').some((b) => b.text().trim() === 'Tạo phiếu kiểm kê đầu tiên'),
    ).toBe(true)
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(d) có dữ liệu ⇒ đúng N dòng, 0 rỗng/lỗi', async () => {
    const w = await mountView()
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="list-data"]').exists()).toBe(true)
    expect(w.findAll('tbody tr')).toHaveLength(ROWS.length)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(e) «Thử lại» gọi lại đúng hàm nạp 1 lần ⇒ error → content', async () => {
    listCycleCountsSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(listCycleCountsSpy).toHaveBeenCalledTimes(1)
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(listCycleCountsSpy).toHaveBeenCalledTimes(2)
    // danh mục kho là lời gọi PHỤ — KHÔNG ăn theo nút «Thử lại» (INV-UX3-29)
    expect(listWarehousesSpy).toHaveBeenCalledTimes(1)
    expect(state(w)).toBe('content')
  })

  it('(f) loại trừ cấu trúc: đúng 1 shell, đúng 1 trạng thái; bộ lọc còn sống', async () => {
    listCycleCountsSpy.mockRejectedValue(new Error('X'))
    const w = await mountView()
    expect(w.findAll('[data-testid="list-page-shell"]')).toHaveLength(1)
    const present = ['list-loading', 'ui-error', 'ui-empty', 'list-content'].filter((t) =>
      w.find(`[data-testid="${t}"]`).exists(),
    )
    expect(present).toEqual(['ui-error'])
    expect(w.find('[data-testid="list-filters"]').exists()).toBe(true)
    expect(w.findComponent(ListFilterBar).exists()).toBe(true)
  })

  it('(h) lỗi của MÀN KHÁC trong cùng ô `error` không cướp trạng thái (INV-UX3-28)', async () => {
    const w = await mountView()
    expect(state(w)).toBe('content')
    const store = (await import('@/stores/imm15')).useImm15Store()
    // ô dùng chung: lỗi phát sinh từ cấp phát / xuất nhập
    store.error = 'Không tạo được phiếu cấp phát.'
    await flushPromises()
    expect(state(w)).toBe('content')
    expect(w.findAll('tbody tr')).toHaveLength(ROWS.length)
  })

  it('(h2) danh mục kho hỏng ⇒ chỉ mất ô lọc, danh sách vẫn hiện', async () => {
    listWarehousesSpy.mockRejectedValue(new Error('403'))
    const w = await mountView()
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
    expect(w.findAll('tbody tr')).toHaveLength(ROWS.length)
  })
})
