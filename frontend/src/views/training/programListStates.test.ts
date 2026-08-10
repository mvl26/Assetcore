// TC-UX3-44 (AC-UX-047 · lô 3) — /imm06/programs: 4 trạng thái danh sách + «Thử lại».
//
// Nợ đo trên đĩa 2026-08-04 (loại γ + A5 — docs/ui-ux/02 §14.4): `:133-136` banner lỗi +
// `:137-145` khối rỗng + **mã chết `:168-170`** («Không có dữ liệu») nằm TRONG nhánh có-dữ-liệu
// nên không bao giờ chạy. Ba nơi cùng nói về "trống" ⇒ gộp về EmptyState của khuôn.
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

const listProgramsSpy = vi.fn()

vi.mock('@/api/imm06', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  listPrograms: (...a: unknown[]) => listProgramsSpy(...a),
}))
vi.mock('@/composables/useCapabilities', () => ({ useCapabilities: () => ({ can: () => true }) }))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import ProgramListView from './ProgramListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const ROWS = [
  { name: 'TP-2026-0001', program_name: 'Vận hành máy thở cơ bản', training_type: 'Initial',
    target_device_model: 'DM-001', target_device_model_name: 'Máy thở Hamilton C1',
    duration_hours: 8, passing_score_pct: 80, is_active: 1 },
  { name: 'TP-2026-0002', program_name: 'An toàn điện thiết bị y tế', training_type: 'Refresher',
    target_device_model: '', target_device_model_name: '', target_device_category: 'Chẩn đoán',
    duration_hours: 4, passing_score_pct: 70, is_active: 0 },
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
  const w = mount(ProgramListView, { global: { stubs } })
  await flushPromises()
  return w
}
function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/imm06/programs — 4 trạng thái loại trừ + thử lại (TC-UX3-44)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetRouteMock()
    listProgramsSpy.mockReset().mockResolvedValue(ok(ROWS))
  })

  it('(a) đang tải ⇒ khung xương, 0 nội dung, 0 nút «Thử lại»', async () => {
    listProgramsSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.findAll('table')).toHaveLength(0)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + ĐÚNG 1 «Thử lại», 0 khối rỗng', async () => {
    listProgramsSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.text()).not.toContain('Chưa có chương trình đào tạo nào')
    expect(w.text()).not.toContain('Không có dữ liệu')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(c) rỗng thật ⇒ ĐÚNG 1 khối rỗng, câu hướng dẫn tiếng Việt', async () => {
    listProgramsSpy.mockResolvedValue(ok([]))
    const w = await mountView()
    expect(state(w)).toBe('empty')
    expect(w.findAll('[data-testid="ui-empty"]')).toHaveLength(1)
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Chưa có chương trình đào tạo nào')
    expect(w.find('[data-testid="ui-empty-description"]').text()).toBe(
      'Chương trình đào tạo là khuôn nội dung; buổi đào tạo được mở theo chương trình.',
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
    listProgramsSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(listProgramsSpy).toHaveBeenCalledTimes(1)
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(listProgramsSpy).toHaveBeenCalledTimes(2)
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(f) loại trừ cấu trúc: đúng 1 shell, đúng 1 trạng thái; bộ lọc còn sống', async () => {
    listProgramsSpy.mockRejectedValue(new Error('X'))
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
