// TC-UX3-36 (AC-UX-047 · lô 3) — /cm/work-orders: 4 trạng thái danh sách + «Thử lại».
//
// Nợ đo trên đĩa 2026-08-04 (loại A5 — HAI nguồn chữ rỗng, docs/ui-ux/02 §14.4):
// `CMWorkOrderListView.vue:303-309` (bản thẻ) và `:376-383` (bản bảng) cùng in «Không tìm thấy
// lệnh sửa chữa nào» ⇒ hai nơi phải sửa mỗi khi đổi câu chữ, và chỉ cần một nơi trôi lệch là
// người dùng thấy hai trải nghiệm cho cùng một trạng thái. Sau khi áp khuôn còn ĐÚNG 1 nguồn.
//
// `stores/imm09.ts:160 fetchKPIs` ghi vào CÙNG ô `error` với lượt nạp danh sách ⇒ view phải
// CHỤP lỗi của riêng lượt nạp (biến thể D — 02 §13.2), không bind thẳng `store.error`.
// `store.filterError` là CẢNH BÁO bộ lọc (bảng giữ dữ liệu) ⇒ KHÔNG vào `:error-message`.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { resetRouteMock } from '@/test/vueRouterMock'

enableAutoUnmount(afterEach)

const listRepairWorkOrdersSpy = vi.fn()
const getRepairKPIsSpy = vi.fn()

vi.mock('@/api/imm09', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  listRepairWorkOrders: (...a: unknown[]) => listRepairWorkOrdersSpy(...a),
  getRepairKPIs: (...a: unknown[]) => getRepairKPIsSpy(...a),
}))
vi.mock('@/composables/useCapabilities', () => ({ useCapabilities: () => ({ can: () => true }) }))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import CMWorkOrderListView from './CMWorkOrderListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const ROWS = [
  {
    name: 'WO-RP-2026-00001', asset_ref: 'AC-ASSET-2026-00001', asset_name: 'Máy thở Hamilton C1',
    repair_type: 'Corrective', priority: 'High', open_datetime: '2026-07-01 08:00:00',
    assigned_to: 'ktv1@benhvien.vn', assigned_to_name: 'Nguyễn Văn A', mttr_hours: 6,
    status: 'In Progress', sla_breached: 0, is_repeat_failure: 0,
    department_name: 'Khoa Hồi sức tích cực', location_name: 'Tầng 3',
  },
  {
    name: 'WO-RP-2026-00002', asset_ref: 'AC-ASSET-2026-00002', asset_name: 'Máy siêu âm GE Logiq',
    repair_type: 'Corrective', priority: 'Medium', open_datetime: '2026-07-02 09:00:00',
    assigned_to: '', assigned_to_name: '', mttr_hours: 0,
    status: 'Open', sla_breached: 0, is_repeat_failure: 1,
    department_name: '', location_name: '',
  },
]
const ok = (rows: unknown[]) => ({
  data: rows,
  pagination: { page: 1, total: rows.length, total_pages: 1, page_size: 20 },
})
const KPIS = {
  kpis: {
    open_wos: 4, total_completed: 18, mttr_avg_hours: 5.5,
    sla_compliance_pct: 92, repeat_failure_count: 1,
  },
}

const stubs = {
  PageHeader: { template: '<div><slot name="actions" /></div>' },
  FilterToggleButton: true,
}

async function mountView() {
  const w = mount(CMWorkOrderListView, { global: { stubs } })
  await flushPromises()
  return w
}
function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/cm/work-orders — 4 trạng thái loại trừ + thử lại (TC-UX3-36)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetRouteMock()
    listRepairWorkOrdersSpy.mockReset().mockResolvedValue(ok(ROWS))
    getRepairKPIsSpy.mockReset().mockResolvedValue(KPIS)
  })

  it('(a) đang tải ⇒ khung xương, 0 nội dung, 0 nút «Thử lại»', async () => {
    listRepairWorkOrdersSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.findAll('table')).toHaveLength(0)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + ĐÚNG 1 «Thử lại», 0 khối rỗng', async () => {
    listRepairWorkOrdersSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.findAll('.alert-error')).toHaveLength(0)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.text()).not.toContain('Không tìm thấy lệnh sửa chữa nào')
    expect(w.text()).toContain('Máy chủ trả về 500.')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(c) rỗng thật ⇒ ĐÚNG 1 khối rỗng (trước có 2), câu hướng dẫn tiếng Việt', async () => {
    listRepairWorkOrdersSpy.mockResolvedValue(ok([]))
    const w = await mountView()
    expect(state(w)).toBe('empty')
    // A5 — bằng chứng đã gộp: trước đây `:303` (thẻ) + `:376` (bảng) cùng render
    expect(w.findAll('[data-testid="ui-empty"]')).toHaveLength(1)
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Chưa có lệnh sửa chữa nào')
    expect(w.find('[data-testid="ui-empty-description"]').text()).toBe(
      'Lệnh sửa chữa được mở từ sự cố hoặc tạo trực tiếp khi thiết bị hỏng.',
    )
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
    listRepairWorkOrdersSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(listRepairWorkOrdersSpy).toHaveBeenCalledTimes(1)
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(listRepairWorkOrdersSpy).toHaveBeenCalledTimes(2)
    expect(getRepairKPIsSpy).toHaveBeenCalledTimes(1)
    expect(state(w)).toBe('content')
  })

  it('(f) loại trừ cấu trúc: đúng 1 shell, đúng 1 trạng thái; bộ lọc còn sống', async () => {
    listRepairWorkOrdersSpy.mockRejectedValue(new Error('X'))
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
    listRepairWorkOrdersSpy.mockRejectedValue(new Error('Hỏng.'))
    const bad = await mountView()
    expect(bad.find('[data-testid="list-summary"]').exists()).toBe(false)
    expect(bad.text()).not.toContain('Đang mở')

    listRepairWorkOrdersSpy.mockResolvedValue(ok(ROWS))
    const good = await mountView()
    expect(state(good)).toBe('content')
    expect(good.find('[data-testid="list-summary"]').exists()).toBe(true)
    expect(good.text()).toContain('Đang mở')
  })

  it('(h) cảnh báo bộ lọc ≠ lỗi nạp: bảng GIỮ dữ liệu (INV-UX3-28)', async () => {
    const w = await mountView()
    expect(state(w)).toBe('content')
    const store = (await import('@/stores/imm09')).useImm09Store()
    store.filterError = 'Khoá lọc không hợp lệ: foo.'
    await flushPromises()
    expect(state(w)).toBe('content')
    expect(w.find('[data-test="cm-filter-error"]').exists()).toBe(true)
    expect(w.findAll('tbody tr')).toHaveLength(ROWS.length)
  })

  it('(h2) lỗi của thẻ chỉ số không cướp trạng thái danh sách (INV-UX3-28)', async () => {
    getRepairKPIsSpy.mockRejectedValue(new Error('Chỉ số hỏng.'))
    const w = await mountView()
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
    expect(w.findAll('tbody tr')).toHaveLength(ROWS.length)
  })
})
