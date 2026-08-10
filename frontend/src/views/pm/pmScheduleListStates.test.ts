// TC-UX3-41 (AC-UX-047 · lô 3) — /pm/schedules: 4 trạng thái danh sách + «Thử lại».
//
// Nợ đo trên đĩa 2026-08-04 (loại γ — docs/ui-ux/02 §14.4): màn này là mẫu TỐT NHẤT trong 12
// màn (đã có `loadError` riêng, đã loại trừ đúng), nhưng vẫn tự cài lại máy trạng thái bằng
// chuỗi `v-if/v-else-if` cục bộ ⇒ nút «Thử lại» là `btn-primary` tự chế, khác nhãn SSoT của
// `ui/ErrorState`, và câu rỗng nằm ngoài SSoT copy. Áp khuôn để 1 nơi giữ hợp đồng.
//
// Ràng buộc riêng: `err` (`:99`) là lỗi HỘP THOẠI tạo/sửa, `loadError` (`:101`) là lỗi NẠP —
// phải giữ TÁCH BẠCH; ép `err` KHÔNG được lật `data-state` sang `error` (INV-UX3-28).
// Lời gọi tham chiếu phụ đã là `Promise.allSettled` (LL-FE-45) ⇒ 403 một nhánh không được
// làm mất bảng.
//
// ⚠️ `listPmSchedules` nằm ở `@/api/imm00` (KHÔNG phải `@/api/imm08` như bảng gợi ý §14.2) —
// đọc `import` thật của view trước khi mock (bẫy «No export named …» của lô 2).
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { resetRouteMock } from '@/test/vueRouterMock'

enableAutoUnmount(afterEach)

const listPmSchedulesSpy = vi.fn()
const deletePmScheduleSpy = vi.fn()

vi.mock('@/api/imm00', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  listPmSchedules: (...a: unknown[]) => listPmSchedulesSpy(...a),
  deletePmSchedule: (...a: unknown[]) => deletePmScheduleSpy(...a),
}))
// Danh mục tham chiếu + danh bạ KTV chỉ phục vụ nhãn/hộp thoại — chặn ở lớp kho trạng thái
// để chúng không chạm axios và không lẫn vào spy nạp danh sách.
vi.mock('@/stores/masterData', () => ({
  useMasterDataStore: () => ({ fetchDoctype: vi.fn().mockResolvedValue([]), options: () => [] }),
}))
vi.mock('@/stores/acUsers', () => ({
  useAcUserStore: () => ({ prefetch: vi.fn().mockResolvedValue([]), label: (id?: string) => id ?? '—' }),
}))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import PmScheduleListView from './PmScheduleListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import { useAuthStore } from '@/stores/auth'

const ROWS = [
  {
    name: 'PMS-2026-0001', asset_ref: 'AC-ASSET-2026-00001', asset_name: 'Máy thở Hamilton C1',
    asset_code: 'AC-ASSET-2026-00001', pm_type: 'Quarterly', pm_interval_days: 90,
    next_due_date: '2026-09-01', status: 'Active', responsible_technician: 'ktv1@benhvien.vn',
  },
  {
    name: 'PMS-2026-0002', asset_ref: 'AC-ASSET-2026-00002', asset_name: 'Máy siêu âm GE Logiq',
    asset_code: 'AC-ASSET-2026-00002', pm_type: 'Annual', pm_interval_days: 365,
    next_due_date: '2026-07-01', status: 'Active', responsible_technician: '',
  },
]
// BE trả envelope PHẲNG `{ items, total }` (KHÔNG `{ data, pagination }`).
const ok = (rows: unknown[]) => ({ items: rows, total: rows.length })

const stubs = {
  PageHeader: { template: '<div><slot name="actions" /></div>' },
  FilterToggleButton: true,
  SmartSelect: true,
  ApproverSelect: true,
  DateInput: true,
}

async function mountView() {
  const w = mount(PmScheduleListView, { global: { stubs } })
  await flushPromises()
  return w
}
function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/pm/schedules — 4 trạng thái loại trừ + thử lại (TC-UX3-41)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetRouteMock()
    listPmSchedulesSpy.mockReset().mockResolvedValue(ok(ROWS))
    deletePmScheduleSpy.mockReset().mockResolvedValue({})
    useAuthStore().capabilities = ['pm.create']
  })

  it('(a) đang tải ⇒ khung xương, 0 nội dung, 0 nút «Thử lại»', async () => {
    listPmSchedulesSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.findAll('table')).toHaveLength(0)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + ĐÚNG 1 «Thử lại», 0 khối rỗng', async () => {
    listPmSchedulesSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.text()).not.toContain('Chưa có lịch bảo trì định kỳ nào')
    expect(w.text()).not.toContain('Không có lịch bảo trì định kỳ nào phù hợp')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(c) rỗng thật ⇒ ui-empty có câu hướng dẫn tiếng Việt + lối tạo', async () => {
    listPmSchedulesSpy.mockResolvedValue(ok([]))
    const w = await mountView()
    expect(state(w)).toBe('empty')
    expect(w.findAll('[data-testid="ui-empty"]')).toHaveLength(1)
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Chưa có lịch bảo trì định kỳ nào')
    expect(w.find('[data-testid="ui-empty-description"]').text()).toBe(
      'Lịch bảo trì định kỳ quyết định khi nào phiếu bảo trì được sinh cho từng thiết bị.',
    )
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
    expect(retryControls(w)).toHaveLength(0)
    // giữ nguyên affordance quyền: nút tạo ở khối rỗng vẫn gắn `:disabled="!canCreatePm"`
    const createBtn = w.findAll('button').find((b) => b.text().includes('Thêm lịch bảo trì định kỳ'))
    expect(createBtn).toBeTruthy()
  })

  it('(d) có dữ liệu ⇒ đúng N dòng, nhóm quá hạn vẫn tô màu, 0 rỗng/lỗi', async () => {
    const w = await mountView()
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="list-data"]').exists()).toBe(true)
    expect(w.findAll('tbody tr')).toHaveLength(ROWS.length)
    // phân nhóm «quá hạn» giữ nguyên: ngày quá hạn tô đỏ đậm (overdueColor)
    expect(w.html()).toContain('text-red-600 font-semibold')
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(e) «Thử lại» gọi lại đúng hàm nạp 1 lần ⇒ error → content', async () => {
    listPmSchedulesSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(listPmSchedulesSpy).toHaveBeenCalledTimes(1)
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(listPmSchedulesSpy).toHaveBeenCalledTimes(2)
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(f) loại trừ cấu trúc: đúng 1 shell, đúng 1 trạng thái; bộ lọc còn sống', async () => {
    listPmSchedulesSpy.mockRejectedValue(new Error('X'))
    const w = await mountView()
    expect(w.findAll('[data-testid="list-page-shell"]')).toHaveLength(1)
    const present = ['list-loading', 'ui-error', 'ui-empty', 'list-content'].filter((t) =>
      w.find(`[data-testid="${t}"]`).exists(),
    )
    expect(present).toEqual(['ui-error'])
    expect(w.find('[data-testid="list-filters"]').exists()).toBe(true)
    expect(w.findComponent(ListFilterBar).exists()).toBe(true)
  })

  it('(h) lỗi HỘP THOẠI không cướp trạng thái danh sách (INV-UX3-28)', async () => {
    const w = await mountView()
    expect(state(w)).toBe('content')
    // `err` là lỗi của biểu mẫu tạo/sửa — KHÔNG được nối vào `:error-message`
    ;(w.vm as unknown as { err: string }).err = 'Chu kỳ (ngày) phải lớn hơn hoặc bằng 0.'
    await flushPromises()
    expect(state(w)).toBe('content')
    expect(w.findAll('tbody tr')).toHaveLength(ROWS.length)
  })
})
