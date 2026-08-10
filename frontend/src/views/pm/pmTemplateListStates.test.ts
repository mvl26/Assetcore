// TC-UX3-18 (AC-UX-047 · lô 1) — /pm/templates: 4 trạng thái danh sách + «Thử lại».
//
// Bug gốc đo trên đĩa 2026-08-03: `load()` (`PmTemplateListView.vue:82`) có `try … finally`
// nhưng **0 `catch`** ⇒ API hỏng ⇒ in «Chưa có template.». Biến `err` sẵn có thuộc HỘP THOẠI
// (`:144`), KHÔNG được nối vào danh sách (INV-UX3-13).
// Bẫy riêng: `listPmTemplates()` trả `{ data, pagination }` — KHÔNG phải `items`.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { resetRouteMock } from '@/test/vueRouterMock'

enableAutoUnmount(afterEach)

const listPmTemplatesSpy = vi.fn()
vi.mock('@/api/imm00', () => ({
  listPmTemplates: (...a: unknown[]) => listPmTemplatesSpy(...a),
  getPmTemplate: vi.fn(),
  createPmTemplate: vi.fn(),
  updatePmTemplate: vi.fn(),
  deletePmTemplate: vi.fn(),
  applyPmTemplateToCategory: vi.fn(),
}))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import PmTemplateListView from './PmTemplateListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const ROWS = [
  { name: 'PMT-0001', template_name: 'Bảo trì máy thở', display_template_name: 'Bảo trì máy thở',
    asset_category: 'CAT-0001', category_name: 'Máy thở', pm_type: 'Quarterly', version: '1.0', effective_date: '2026-01-01' },
  { name: 'PMT-0002', template_name: 'Bảo trì monitor', display_template_name: 'Bảo trì monitor',
    asset_category: 'CAT-0002', category_name: 'Monitor', pm_type: 'Annual', version: '2.0', effective_date: '2026-02-01' },
]

const stubs = { PageHeader: true, FilterToggleButton: true, SmartSelect: true, DateInput: true }

async function mountView() {
  const w = mount(PmTemplateListView, { global: { stubs } })
  await flushPromises()
  return w
}

function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/pm/templates — 4 trạng thái loại trừ + thử lại (TC-UX3-18)', () => {
  beforeEach(() => {
    resetRouteMock()
    listPmTemplatesSpy.mockReset().mockResolvedValue({ data: ROWS, pagination: { total: ROWS.length } })
  })

  it('(a) đang tải ⇒ khung xương, 0 nội dung, 0 nút «Thử lại»', async () => {
    listPmTemplatesSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + đúng 1 «Thử lại», KHÔNG còn chuỗi rỗng cũ', async () => {
    listPmTemplatesSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.text()).not.toContain('Chưa có')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(c) rỗng thật ⇒ ui-empty có câu hướng dẫn tiếng Việt, 0 nút «Thử lại»', async () => {
    listPmTemplatesSpy.mockResolvedValue({ data: [], pagination: { total: 0 } })
    const w = await mountView()
    expect(state(w)).toBe('empty')
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Chưa có mẫu bảo trì nào')
    expect(w.find('[data-testid="ui-empty-description"]').exists()).toBe(true)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(d) có dữ liệu ⇒ đúng N dòng trong list-data', async () => {
    const w = await mountView()
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="list-data"]').exists()).toBe(true)
    expect(w.findAll('tbody tr')).toHaveLength(ROWS.length)
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(e) «Thử lại» gọi lại đúng hàm nạp 1 lần ⇒ error → content', async () => {
    listPmTemplatesSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(listPmTemplatesSpy).toHaveBeenCalledTimes(1)
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(listPmTemplatesSpy).toHaveBeenCalledTimes(2)
    expect(state(w)).toBe('content')
  })

  it('(f) loại trừ cấu trúc: đúng 1 shell, đúng 1 trạng thái; bộ lọc còn sống', async () => {
    listPmTemplatesSpy.mockRejectedValue(new Error('X'))
    const w = await mountView()
    expect(w.findAll('[data-testid="list-page-shell"]')).toHaveLength(1)
    const present = ['list-loading', 'ui-error', 'ui-empty', 'list-content']
      .filter((t) => w.find(`[data-testid="${t}"]`).exists())
    expect(present).toEqual(['ui-error'])
    expect(w.findComponent(ListFilterBar).exists()).toBe(true)
  })
})
