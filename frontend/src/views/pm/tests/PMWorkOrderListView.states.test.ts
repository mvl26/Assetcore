// TC-UX3-40 (AC-UX-047 · lô 3) — /pm/work-orders: 4 trạng thái danh sách + «Thử lại».
//
// Nợ đo trên đĩa 2026-08-04 (loại A5 — HAI nguồn chữ rỗng, docs/ui-ux/02 §14.4):
// `PMWorkOrderListView.vue:324-326` (bản thẻ) và `:383-393` (bản bảng) cùng trả lời một câu
// hỏi «không có phiếu nào» bằng hai nội dung KHÁC nhau — bản bảng có thêm dòng gợi ý mà bản
// thẻ không có ⇒ hai trải nghiệm cho cùng một trạng thái. Sau khi áp khuôn còn ĐÚNG 1 nguồn.
//
// Ràng buộc riêng của màn: `stores/imm08.ts:205 fetchDashboardStats` ghi vào CÙNG ô `error`
// VÀ CÙNG cờ `loading` với lượt nạp danh sách ⇒ nếu bind thẳng `store.error`/`store.loading`
// thì một lượt nạp chỉ số hỏng sẽ xoá trắng bảng đang xem (INV-UX3-28). Vì vậy view giữ
// `listLoading`/`loadError` riêng và CHỤP lỗi ngay sau `await` (biến thể D — 02 §13.2).
//
// KHÔNG assert hành vi thẻ chỉ số ngoài yêu cầu «im lặng khi lỗi» — phần còn lại thuộc vòng sau.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { resetRouteMock } from '@/test/vueRouterMock'

enableAutoUnmount(afterEach)

const listPMWorkOrdersSpy = vi.fn()
const getPMDashboardStatsSpy = vi.fn()

vi.mock('@/api/imm08', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  listPMWorkOrders: (...a: unknown[]) => listPMWorkOrdersSpy(...a),
  getPMDashboardStats: (...a: unknown[]) => getPMDashboardStatsSpy(...a),
}))
vi.mock('@/composables/useCapabilities', () => ({ useCapabilities: () => ({ can: () => true }) }))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import PMWorkOrderListView from '@/views/pm/PMWorkOrderListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const ROWS = [
  {
    name: 'WO-PM-2026-00001', asset_ref: 'AC-ASSET-2026-00001', asset_name: 'Máy thở Hamilton C1',
    pm_type: 'Routine', due_date: '2026-08-20', assigned_to: 'ktv1@benhvien.vn',
    assigned_to_name: 'Nguyễn Văn A', status: 'Open', is_late: false,
  },
  {
    name: 'WO-PM-2026-00002', asset_ref: 'AC-ASSET-2026-00002', asset_name: 'Máy siêu âm GE Logiq',
    pm_type: 'Routine', due_date: '2026-07-01', assigned_to: '', assigned_to_name: '',
    status: 'Overdue', is_late: true,
  },
]
const ok = (rows: unknown[]) => ({
  data: rows,
  pagination: { page: 1, total: rows.length, total_pages: 1, page_size: 20 },
})
const STATS = {
  kpis: {
    total_scheduled: 42, overdue_in_month: 3, overdue: 5,
    completed_on_time: 30, avg_days_late: 2, compliance_rate_pct: 88,
  },
}

const stubs = {
  PageHeader: { template: '<div><slot name="actions" /></div>' },
  FilterToggleButton: true,
  DateInput: true,
}

async function mountView() {
  const w = mount(PMWorkOrderListView, { global: { stubs } })
  await flushPromises()
  return w
}
function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/pm/work-orders — 4 trạng thái loại trừ + thử lại (TC-UX3-40)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetRouteMock()
    listPMWorkOrdersSpy.mockReset().mockResolvedValue(ok(ROWS))
    getPMDashboardStatsSpy.mockReset().mockResolvedValue(STATS)
  })

  it('(a) đang tải ⇒ khung xương, 0 nội dung, 0 nút «Thử lại»', async () => {
    listPMWorkOrdersSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.findAll('table')).toHaveLength(0)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + ĐÚNG 1 «Thử lại», khối danh sách KHÔNG hiện rỗng', async () => {
    listPMWorkOrdersSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.findAll('.alert-error')).toHaveLength(0)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.text()).not.toContain('Không tìm thấy phiếu bảo trì')
    expect(w.text()).toContain('Máy chủ trả về 500.')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(c) rỗng thật ⇒ ĐÚNG 1 khối rỗng, câu hướng dẫn tiếng Việt', async () => {
    listPMWorkOrdersSpy.mockResolvedValue(ok([]))
    const w = await mountView()
    expect(state(w)).toBe('empty')
    expect(w.findAll('[data-testid="ui-empty"]')).toHaveLength(1)
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Chưa có phiếu bảo trì định kỳ nào')
    expect(w.find('[data-testid="ui-empty-description"]').text()).toBe(
      'Phiếu bảo trì định kỳ được sinh từ lịch bảo trì hoặc tạo thủ công cho một thiết bị.',
    )
    // A5: hai câu rỗng cũ (bản thẻ `:324` và bản bảng `:383`) không được sống sót
    expect(w.text()).not.toContain('Thử thay đổi bộ lọc hoặc từ khóa tìm kiếm')
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
    listPMWorkOrdersSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(listPMWorkOrdersSpy).toHaveBeenCalledTimes(1)
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(listPMWorkOrdersSpy).toHaveBeenCalledTimes(2)
    // lời gọi PHỤ (thẻ chỉ số) KHÔNG ăn theo nút «Thử lại» (INV-UX3-29)
    expect(getPMDashboardStatsSpy).toHaveBeenCalledTimes(1)
    expect(state(w)).toBe('content')
  })

  it('(f) loại trừ cấu trúc: đúng 1 shell, đúng 1 trạng thái; bộ lọc còn sống', async () => {
    listPMWorkOrdersSpy.mockRejectedValue(new Error('X'))
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
    listPMWorkOrdersSpy.mockRejectedValue(new Error('Hỏng.'))
    const bad = await mountView()
    expect(bad.find('[data-testid="list-summary"]').exists()).toBe(false)
    expect(bad.text()).not.toContain('Tổng lịch tháng')

    listPMWorkOrdersSpy.mockResolvedValue(ok(ROWS))
    const good = await mountView()
    expect(state(good)).toBe('content')
    expect(good.find('[data-testid="list-summary"]').exists()).toBe(true)
    expect(good.text()).toContain('Tổng lịch tháng')
  })

  it('(h) cảnh báo bộ lọc ≠ lỗi nạp: bảng GIỮ dữ liệu (INV-UX3-28)', async () => {
    const w = await mountView()
    expect(state(w)).toBe('content')
    const store = (await import('@/stores/imm08')).useImm08Store()
    store.filterError = 'Khoá lọc không hợp lệ: due_date_from.'
    await flushPromises()
    expect(state(w)).toBe('content')
    expect(w.find('[data-test="pm-filter-error"]').exists()).toBe(true)
    expect(w.findAll('tbody tr')).toHaveLength(ROWS.length)
  })

  it('(h2) lỗi của thẻ chỉ số không cướp trạng thái danh sách (INV-UX3-28)', async () => {
    getPMDashboardStatsSpy.mockRejectedValue(new Error('Chỉ số hỏng.'))
    const w = await mountView()
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
    expect(w.findAll('tbody tr')).toHaveLength(ROWS.length)
  })
})
