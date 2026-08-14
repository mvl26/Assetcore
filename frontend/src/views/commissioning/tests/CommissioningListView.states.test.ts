// TC-UX3-43 (AC-UX-047 · lô 3) — /commissioning: 4 trạng thái danh sách + «Thử lại».
//
// Nợ đo trên đĩa 2026-08-04 (loại A5 — BA khối rỗng, docs/ui-ux/02 §14.4):
// `:295-329` (rỗng theo ngữ cảnh thiết bị) + `:362-365` (bản thẻ) + `:442-456` (bản bảng).
// Ba nơi trả lời câu «vì sao trống» ⇒ chỉ cần một nơi trôi lệch là hai câu mâu thuẫn cùng màn.
// Sau khi áp khuôn còn ĐÚNG 1 khối rỗng; nội dung của nó ĐỔI THEO NGUYÊN NHÂN (ba nhánh).
//
// `stores/imm04.ts:73` dùng CHUNG ô `error` với ~20 hành động GHI ⇒ bắt buộc biến thể D
// (chụp lỗi sau `await`), nếu không một lần duyệt/huỷ hỏng sẽ xoá trắng bảng (INV-UX3-28).
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { resetRouteMock, setRouteQuery } from '@/test/vueRouterMock'

enableAutoUnmount(afterEach)

const listCommissioningSpy = vi.fn()
const getDashboardStatsSpy = vi.fn()

vi.mock('@/api/imm04', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  listCommissioning: (...a: unknown[]) => listCommissioningSpy(...a),
  getDashboardStats: (...a: unknown[]) => getDashboardStatsSpy(...a),
}))
vi.mock('@/composables/useCapabilities', () => ({ useCapabilities: () => ({ can: () => true }) }))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import CommissioningListView from '@/views/commissioning/CommissioningListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const ASSET = 'AC-ASSET-2026-00042'
const ROWS = [
  {
    name: 'COMM-2026-0001', master_item: 'ITEM-1', master_item_name: 'Máy thở Hamilton C6',
    vendor: 'SUP-1', vendor_name: 'Công ty Thiết bị Y tế An Bình',
    clinical_dept: 'DEP-1', clinical_dept_name: 'Khoa Hồi sức tích cực',
    vendor_serial_no: 'SN-001', workflow_state: 'Draft', final_asset: ASSET,
    modified: '2026-07-28 10:00:00', expected_installation_date: '2026-07-20',
  },
  {
    name: 'COMM-2026-0002', master_item: 'ITEM-2', master_item_name: 'Máy siêu âm GE Logiq',
    vendor: 'SUP-2', vendor_name: 'Công ty Y tế Miền Nam',
    clinical_dept: 'DEP-2', clinical_dept_name: 'Khoa Chẩn đoán hình ảnh',
    vendor_serial_no: 'SN-002', workflow_state: 'Submitted', final_asset: '',
    modified: '2026-07-29 11:00:00', expected_installation_date: '2026-07-25',
  },
]
const ok = (rows: unknown[]) => ({
  items: rows,
  pagination: { page: 1, page_size: 20, total: rows.length, total_pages: rows.length ? 1 : 0 },
})
const STATS = { kpis: { total: 12, draft: 3, in_progress: 4, completed: 5, overdue_sla: 1 } }

const stubs = {
  PageHeader: { template: '<div><slot name="actions" /></div>' },
  FilterToggleButton: true,
  StatusBadge: true,
  RouterLink: { template: '<a><slot /></a>' },
}

async function mountView() {
  const w = mount(CommissioningListView, { global: { stubs } })
  await flushPromises()
  return w
}
function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/commissioning — 4 trạng thái loại trừ + thử lại (TC-UX3-43)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetRouteMock()
    listCommissioningSpy.mockReset().mockResolvedValue(ok(ROWS))
    getDashboardStatsSpy.mockReset().mockResolvedValue(STATS)
  })

  it('(a) đang tải ⇒ khung xương, 0 nội dung, 0 nút «Thử lại»', async () => {
    listCommissioningSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.findAll('table')).toHaveLength(0)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + ĐÚNG 1 «Thử lại», 0 khối rỗng', async () => {
    listCommissioningSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.findAll('.alert-error')).toHaveLength(0)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.find('[data-testid="list-empty-scoped"]').exists()).toBe(false)
    expect(w.text()).not.toContain('Không tìm thấy phiếu nào phù hợp')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(c) rỗng thật ⇒ ĐÚNG 1 khối rỗng (trước có 3), câu hướng dẫn tiếng Việt', async () => {
    listCommissioningSpy.mockResolvedValue(ok([]))
    const w = await mountView()
    expect(state(w)).toBe('empty')
    expect(w.findAll('[data-testid="ui-empty"]')).toHaveLength(1)
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Chưa có phiếu nghiệm thu lắp đặt nào')
    expect(w.find('[data-testid="ui-empty-description"]').text()).toBe(
      'Phiếu nghiệm thu lắp đặt được lập khi nhà cung cấp bàn giao thiết bị tại khoa.',
    )
    expect(w.find('[data-testid="list-empty-scoped"]').exists()).toBe(false)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(i) rỗng DO LỌC theo thiết bị ⇒ câu KHÁC «rỗng thật» + lối xoá lọc (A9)', async () => {
    setRouteQuery({ asset: ASSET })
    listCommissioningSpy.mockResolvedValue(ok([]))
    const w = await mountView()
    expect(state(w)).toBe('empty')
    // vẫn ĐÚNG 1 khối rỗng — chỉ NỘI DUNG đổi theo nguyên nhân
    expect(w.findAll('[data-testid="ui-empty"]')).toHaveLength(1)
    const title = w.find('[data-testid="ui-empty-title"]').text()
    expect(title).toContain('Không có phiếu nghiệm thu lắp đặt nào của thiết bị')
    expect(title).toContain(ASSET)
    expect(title).not.toBe('Chưa có phiếu nghiệm thu lắp đặt nào')
    // lối thoát bắt buộc — testid bị commissioningScopedEmpty.test.ts khoá, giữ nguyên tên
    const scoped = w.find('[data-testid="list-empty-scoped"]')
    expect(scoped.exists()).toBe(true)
    expect(
      w.findAll('button').some((b) => b.text().trim() === 'Xoá bộ lọc thiết bị'),
      'rỗng theo ngữ cảnh mà không có lối bỏ lọc = màn trống không lối ra',
    ).toBe(true)
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
    listCommissioningSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(listCommissioningSpy).toHaveBeenCalledTimes(1)
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(listCommissioningSpy).toHaveBeenCalledTimes(2)
    expect(getDashboardStatsSpy).toHaveBeenCalledTimes(1)
    expect(state(w)).toBe('content')
  })

  it('(f) loại trừ cấu trúc: đúng 1 shell, đúng 1 trạng thái; bộ lọc còn sống', async () => {
    listCommissioningSpy.mockRejectedValue(new Error('X'))
    const w = await mountView()
    expect(w.findAll('[data-testid="list-page-shell"]')).toHaveLength(1)
    const present = ['list-loading', 'ui-error', 'ui-empty', 'list-content'].filter((t) =>
      w.find(`[data-testid="${t}"]`).exists(),
    )
    expect(present).toEqual(['ui-error'])
    expect(w.find('[data-testid="list-filters"]').exists()).toBe(true)
    expect(w.findComponent(ListFilterBar).exists()).toBe(true)
  })

  it('(g) thẻ chỉ số im lặng khi lỗi, hiện khi có dữ liệu (INV-UX3-27)', async () => {
    listCommissioningSpy.mockRejectedValue(new Error('Hỏng.'))
    const bad = await mountView()
    expect(bad.find('[data-testid="list-summary"]').exists()).toBe(false)

    listCommissioningSpy.mockResolvedValue(ok(ROWS))
    const good = await mountView()
    expect(state(good)).toBe('content')
    expect(good.find('[data-testid="list-summary"]').exists()).toBe(true)
  })

  it('(h) lỗi HÀNH ĐỘNG GHI không cướp trạng thái danh sách (INV-UX3-28)', async () => {
    const w = await mountView()
    expect(state(w)).toBe('content')
    const store = (await import('@/stores/imm04')).useCommissioningStore()
    // ô `error` dùng chung với ~20 đường ghi — một lần duyệt hỏng KHÔNG được xoá bảng
    store.error = 'Không duyệt được phiếu.'
    await flushPromises()
    expect(state(w)).toBe('content')
    expect(w.findAll('tbody tr')).toHaveLength(ROWS.length)
  })
})
