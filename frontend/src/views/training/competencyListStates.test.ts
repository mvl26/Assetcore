// TC-UX3-46 (AC-UX-047 · lô 3) — /imm06/competencies: 4 trạng thái danh sách + «Thử lại».
//
// Nợ đo trên đĩa 2026-08-04 (loại γ + A5 — docs/ui-ux/02 §14.4): `:215-218` banner lỗi +
// `:219-236` khối rỗng + **mã chết `:267-269`** trong nhánh có-dữ-liệu.
//
// BẪY RIÊNG của nhóm IMM-06 (02 §14.2): `load()` bọc `api.run(() => store.fetchXxx(...))`.
// `useApi.run` CHỈ bắt exception, mà `stores/imm06.ts` đã `catch` rồi ⇒ `api.lastError` LUÔN
// null khi danh sách hỏng. Đọc lỗi từ `api.lastError` = luôn thấy "không lỗi" ⇒ bắt buộc
// biến thể D: chụp `store.error` (ô DÙNG CHUNG cho 3 danh sách + mọi hành động ghi).
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { resetRouteMock } from '@/test/vueRouterMock'

enableAutoUnmount(afterEach)

const listCompetenciesSpy = vi.fn()

vi.mock('@/api/imm06', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  listCompetencies: (...a: unknown[]) => listCompetenciesSpy(...a),
}))
vi.mock('@/composables/useCapabilities', () => ({ useCapabilities: () => ({ can: () => true }) }))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import CompetencyListView from './CompetencyListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const ROWS = [
  { name: 'UC-2026-0001', user: 'ktv1@benhvien.vn', user_full_name: 'Nguyễn Văn A',
    device_model: 'DM-001', device_model_name: 'Máy thở Hamilton C1', competency_level: 'Operator',
    achieved_date: '2026-01-10', expiry_date: '2027-01-10', days_until_expiry: 180,
    is_expired: 0, workflow_state: 'Approved' },
  { name: 'UC-2026-0002', user: 'ktv2@benhvien.vn', user_full_name: 'Trần Thị B',
    device_model: 'DM-002', device_model_name: 'Máy siêu âm GE Logiq', competency_level: 'Advanced',
    achieved_date: '2025-06-01', expiry_date: '2026-06-01', days_until_expiry: -30,
    is_expired: 1, workflow_state: 'Expired' },
]
// `stores/imm06.ts` đọc `res.data` + `res.pagination`.
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
  const w = mount(CompetencyListView, { global: { stubs } })
  await flushPromises()
  return w
}
function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/imm06/competencies — 4 trạng thái loại trừ + thử lại (TC-UX3-46)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetRouteMock()
    listCompetenciesSpy.mockReset().mockResolvedValue(ok(ROWS))
  })

  it('(a) đang tải ⇒ khung xương, 0 nội dung, 0 nút «Thử lại»', async () => {
    listCompetenciesSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.findAll('table')).toHaveLength(0)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + ĐÚNG 1 «Thử lại», 0 khối rỗng', async () => {
    listCompetenciesSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.text()).not.toContain('Chưa có bản ghi năng lực nào')
    expect(w.text()).not.toContain('Không có dữ liệu')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(c) rỗng thật ⇒ ĐÚNG 1 khối rỗng, câu hướng dẫn tiếng Việt', async () => {
    listCompetenciesSpy.mockResolvedValue(ok([]))
    const w = await mountView()
    expect(state(w)).toBe('empty')
    expect(w.findAll('[data-testid="ui-empty"]')).toHaveLength(1)
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Chưa có bản ghi năng lực nào')
    expect(w.find('[data-testid="ui-empty-description"]').text()).toBe(
      'Bản ghi năng lực sinh ra khi người dùng hoàn thành buổi đào tạo và đạt điểm yêu cầu.',
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
    listCompetenciesSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(listCompetenciesSpy).toHaveBeenCalledTimes(1)
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(listCompetenciesSpy).toHaveBeenCalledTimes(2)
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(f) loại trừ cấu trúc: đúng 1 shell, đúng 1 trạng thái; bộ lọc còn sống', async () => {
    listCompetenciesSpy.mockRejectedValue(new Error('X'))
    const w = await mountView()
    expect(w.findAll('[data-testid="list-page-shell"]')).toHaveLength(1)
    const present = ['list-loading', 'ui-error', 'ui-empty', 'list-content'].filter((t) =>
      w.find(`[data-testid="${t}"]`).exists(),
    )
    expect(present).toEqual(['ui-error'])
    expect(w.find('[data-testid="list-filters"]').exists()).toBe(true)
    expect(w.findComponent(ListFilterBar).exists()).toBe(true)
  })

  it('(h) lỗi HÀNH ĐỘNG GHI dùng chung ô `error` không cướp trạng thái (INV-UX3-28)', async () => {
    const w = await mountView()
    expect(state(w)).toBe('content')
    const store = (await import('@/stores/imm06')).useImm06Store()
    store.error = 'Không lưu được bản ghi.'
    await flushPromises()
    expect(state(w)).toBe('content')
    expect(w.findAll('tbody tr')).toHaveLength(ROWS.length)
  })
})
