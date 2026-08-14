// TC-UX3-42 (AC-UX-047 · lô 3) — /needs-requests: 4 trạng thái danh sách + «Thử lại».
//
// Bug gốc đo trên đĩa 2026-08-04 (loại α — LỖI GIẢ DẠNG RỖNG THẬT, docs/ui-ux/02 §14.4):
// `NeedsRequestListView.vue:209` (`v-if="store.error"`) là khối ĐỘC LẬP, tách rời khỏi chuỗi
// `v-if="store.loading"` / `v-else-if="…length"` / `v-else` kết thúc ở `:348`. Khi lượt nạp đầu
// hỏng, `stores/imm01.ts:53` set lỗi còn `needsRequests` giữ `[]` ⇒ banner đỏ VÀ câu «Không có
// đề xuất nào phù hợp» cùng render. Kèm mã chết `:260-263` («Không có dữ liệu») nằm TRONG nhánh
// `v-else-if="…length"` nên không bao giờ chạy.
//
// Dải KPI (`:178-206`) cũng in số của lượt hỏng ⇒ phải chuyển vào `#summary` (ẩn ở trạng thái
// lỗi, INV-UX3-27) — số 0 tính từ tập rỗng là tín hiệu giả cùng lớp với false-empty.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { resetRouteMock } from '@/test/vueRouterMock'

enableAutoUnmount(afterEach)

const listNeedsRequestsSpy = vi.fn()
const getDashboardKpisSpy = vi.fn()

vi.mock('@/api/imm01', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  listNeedsRequests: (...a: unknown[]) => listNeedsRequestsSpy(...a),
  getDashboardKpis: (...a: unknown[]) => getDashboardKpisSpy(...a),
}))
// Bảng tham chiếu chỉ phục vụ ô lọc khoa/phòng — không thuộc phạm vi 4 trạng thái; chặn ở lớp
// API để `refData.fetchAll()` không chạm axios thật trong test.
vi.mock('@/api/imm00', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  listLocations: () => Promise.resolve([]),
  listDepartments: () => Promise.resolve([]),
  listAssetCategories: () => Promise.resolve([]),
  listDeviceModels: () => Promise.resolve([]),
  listSlaPolicies: () => Promise.resolve([]),
  listSuppliers: () => Promise.resolve([]),
}))
vi.mock('@/composables/useCapabilities', () => ({ useCapabilities: () => ({ can: () => true }) }))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import NeedsRequestListView from '@/views/needs/NeedsRequestListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const ROWS = [
  {
    name: 'NR-2026-0001', request_type: 'New', requesting_department: 'DEP-001',
    department_name: 'Khoa Hồi sức tích cực', device_model_ref: 'DM-001',
    device_model_name: 'Máy thở Hamilton C1', quantity: 2, priority_class: 'P1',
    tco_5y: 1_200_000_000, workflow_state: 'Submitted', age_days: 12, is_overdue: false,
  },
  {
    name: 'NR-2026-0002', request_type: 'Replacement', requesting_department: 'DEP-002',
    department_name: 'Khoa Chẩn đoán hình ảnh', device_model_ref: 'DM-002',
    device_model_name: 'Máy siêu âm GE Logiq', quantity: 1, priority_class: 'P2',
    tco_5y: 800_000_000, workflow_state: 'Reviewing', age_days: 45, is_overdue: true,
  },
]
const ok = (rows: unknown[]) => ({ items: rows, total: rows.length, page: 1, page_size: 20 })
const KPIS = {
  backlog_over_30d: 3, g01_pass_rate: 82.5, envelope_utilization: 61.4,
  by_state: { Approved: 7 },
}

const stubs = {
  PageHeader: { template: '<div><slot name="actions" /></div>' },
  FilterToggleButton: true,
  StatusBadge: true,
}

async function mountView() {
  const w = mount(NeedsRequestListView, { global: { stubs } })
  await flushPromises()
  return w
}
function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/needs-requests — 4 trạng thái loại trừ + thử lại (TC-UX3-42)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetRouteMock()
    listNeedsRequestsSpy.mockReset().mockResolvedValue(ok(ROWS))
    getDashboardKpisSpy.mockReset().mockResolvedValue(KPIS)
  })

  it('(a) đang tải ⇒ khung xương, 0 nội dung, 0 nút «Thử lại»', async () => {
    listNeedsRequestsSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.findAll('table')).toHaveLength(0)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + ĐÚNG 1 «Thử lại», 0 khối rỗng', async () => {
    listNeedsRequestsSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.findAll('.alert-error')).toHaveLength(0)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.text()).toContain('Máy chủ trả về 500.')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(j) TC RED — lỗi KHÔNG được kèm câu rỗng «Không có đề xuất nào phù hợp»', async () => {
    // Bằng chứng lỗi THẬT trên đĩa: banner `:209` và khối rỗng `:348` cùng render.
    listNeedsRequestsSpy.mockRejectedValue(new Error('Mất kết nối máy chủ.'))
    const w = await mountView()
    expect(w.text()).not.toContain('Không có đề xuất nào phù hợp')
    expect(w.text()).not.toContain('Chưa có đề xuất nhu cầu nào')
    // mã chết `:261` — câu này không được tồn tại ở BẤT KỲ trạng thái nào
    expect(w.text()).not.toContain('Không có dữ liệu')
    expect(w.findAll('table')).toHaveLength(0)
  })

  it('(c) rỗng thật ⇒ ui-empty có câu hướng dẫn tiếng Việt, 0 nút «Thử lại»', async () => {
    listNeedsRequestsSpy.mockResolvedValue(ok([]))
    const w = await mountView()
    expect(state(w)).toBe('empty')
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Chưa có đề xuất nhu cầu nào')
    expect(w.find('[data-testid="ui-empty-description"]').text()).toBe(
      'Đề xuất nhu cầu là bước đầu của vòng đời thiết bị — khoa/phòng lập, phòng vật tư thẩm định.',
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
    listNeedsRequestsSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(listNeedsRequestsSpy).toHaveBeenCalledTimes(1)
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(listNeedsRequestsSpy).toHaveBeenCalledTimes(2)
    // lời gọi PHỤ (chỉ số hiệu suất) KHÔNG ăn theo nút «Thử lại» (INV-UX3-29)
    expect(getDashboardKpisSpy).toHaveBeenCalledTimes(1)
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(f) loại trừ cấu trúc: đúng 1 shell, đúng 1 trạng thái; bộ lọc còn sống', async () => {
    listNeedsRequestsSpy.mockRejectedValue(new Error('X'))
    const w = await mountView()
    expect(w.findAll('[data-testid="list-page-shell"]')).toHaveLength(1)
    const present = ['list-loading', 'ui-error', 'ui-empty', 'list-content'].filter((t) =>
      w.find(`[data-testid="${t}"]`).exists(),
    )
    expect(present).toEqual(['ui-error'])
    expect(w.find('[data-testid="list-filters"]').exists()).toBe(true)
    expect(w.findComponent(ListFilterBar).exists()).toBe(true)
  })

  it('(g) thẻ chỉ số im lặng khi lỗi, in đúng số khi có dữ liệu (INV-UX3-27)', async () => {
    listNeedsRequestsSpy.mockRejectedValue(new Error('Hỏng.'))
    const bad = await mountView()
    expect(bad.find('[data-testid="list-summary"]').exists()).toBe(false)
    expect(bad.text()).not.toContain('Phiếu tồn quá 30 ngày')

    listNeedsRequestsSpy.mockResolvedValue(ok(ROWS))
    const good = await mountView()
    expect(state(good)).toBe('content')
    expect(good.find('[data-testid="list-summary"]').exists()).toBe(true)
    expect(good.text()).toContain('Phiếu tồn quá 30 ngày')
  })

  it('(h) lỗi của lời gọi PHỤ (chỉ số) không cướp trạng thái danh sách (INV-UX3-28)', async () => {
    // `stores/imm01.ts:118` fetchKpis ghi vào CÙNG ô `error` với danh sách ⇒ nếu view bind
    // thẳng ô đó, một lần nạp chỉ số hỏng sẽ xoá trắng danh sách đang hiển thị.
    getDashboardKpisSpy.mockRejectedValue(new Error('Chỉ số hỏng.'))
    const w = await mountView()
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
    expect(w.findAll('tbody tr')).toHaveLength(ROWS.length)
  })
})
