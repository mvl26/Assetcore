// TC-UX3-31 (AC-UX-047 · lô 2) — /tech-specs: 4 trạng thái danh sách + «Thử lại».
//
// Bug gốc đo trên đĩa 2026-08-04: banner `.alert-error` hiện SONG SONG với khối rỗng
// «Không có hồ sơ kỹ thuật phù hợp» (không loại trừ nhau) và banner đó bind thẳng
// `store.error` — ô dùng CHUNG với `fetchKpis` (`stores/imm02.ts:45`) ⇒ một lần nạp
// chỉ-số hỏng cũng dựng banner lỗi lên trên danh sách vẫn đang có dữ liệu. Không có
// nút thử lại ở đâu cả.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { resetRouteMock } from '@/test/vueRouterMock'

enableAutoUnmount(afterEach)

const listTechSpecsSpy = vi.fn()
const getDashboardKpisSpy = vi.fn()
// `importOriginal` + ghi đè ĐÚNG hàm nạp: `stores/imm02.ts` dùng `import * as api` nên
// module phải giữ đủ mọi export; liệt kê tay sẽ trôi lệch khi lớp API thêm hàm mới.
vi.mock('@/api/imm02', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  listTechSpecs: (...a: unknown[]) => listTechSpecsSpy(...a),
  getDashboardKpis: (...a: unknown[]) => getDashboardKpisSpy(...a),
}))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import TechSpecListView from '@/views/tech-specs/TechSpecListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const ROWS = [
  { name: 'TS-2026-0001', spec_code: 'TS-MAY-THO-01', device_model_ref: 'DM-0001',
    device_model_name: 'Hamilton C1', version: 'v1', workflow_state: 'Draft', lock_in_score: 2.1 },
  { name: 'TS-2026-0002', spec_code: 'TS-SIEU-AM-01', device_model_ref: 'DM-0002',
    device_model_name: 'GE Logiq', version: 'v2', workflow_state: 'Locked', lock_in_score: 3.9 },
]
const ok = (rows: unknown[]) => ({ items: rows, total: rows.length, page: 1, page_size: 20 })
const KPIS = { by_state: { Locked: 1 }, backlog_over_30d: 0, avg_lock_in_score: 2.5 }

const stubs = { PageHeader: true, FilterToggleButton: true, KpiCard: true }

async function mountView() {
  const w = mount(TechSpecListView, { global: { stubs } })
  await flushPromises()
  return w
}
function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/tech-specs — 4 trạng thái loại trừ + thử lại (TC-UX3-31)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetRouteMock()
    listTechSpecsSpy.mockReset().mockResolvedValue(ok(ROWS))
    getDashboardKpisSpy.mockReset().mockResolvedValue(KPIS)
  })

  it('(a) đang tải ⇒ khung xương, 0 nội dung, 0 nút «Thử lại»', async () => {
    listTechSpecsSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.findAll('table')).toHaveLength(0)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + ĐÚNG 1 «Thử lại», KHÔNG còn banner alert-error song song', async () => {
    listTechSpecsSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.findAll('.alert-error')).toHaveLength(0)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.text()).not.toContain('Không có hồ sơ kỹ thuật phù hợp')
    expect(w.text()).toContain('Máy chủ trả về 500.')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(c) rỗng thật ⇒ ui-empty có câu hướng dẫn tiếng Việt, 0 nút «Thử lại»', async () => {
    listTechSpecsSpy.mockResolvedValue(ok([]))
    const w = await mountView()
    expect(state(w)).toBe('empty')
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Chưa có hồ sơ kỹ thuật nào')
    expect(w.find('[data-testid="ui-empty-description"]').text())
      .toBe('Hãy tạo hồ sơ kỹ thuật mới hoặc xoá bộ lọc để xem tất cả.')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(d) có dữ liệu ⇒ đúng N dòng trong list-data', async () => {
    const w = await mountView()
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="list-data"]').exists()).toBe(true)
    expect(w.findAll('tbody tr')).toHaveLength(ROWS.length)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(e) «Thử lại» gọi lại đúng hàm nạp 1 lần; lời gọi chỉ-số KHÔNG tăng', async () => {
    listTechSpecsSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(listTechSpecsSpy).toHaveBeenCalledTimes(1)
    const kpiCallsBefore = getDashboardKpisSpy.mock.calls.length
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(listTechSpecsSpy).toHaveBeenCalledTimes(2)
    expect(getDashboardKpisSpy).toHaveBeenCalledTimes(kpiCallsBefore) // INV-UX3-21
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(f) loại trừ cấu trúc: đúng 1 shell, đúng 1 trạng thái; bộ lọc còn sống', async () => {
    listTechSpecsSpy.mockRejectedValue(new Error('X'))
    const w = await mountView()
    expect(w.findAll('[data-testid="list-page-shell"]')).toHaveLength(1)
    const present = ['list-loading', 'ui-error', 'ui-empty', 'list-content']
      .filter((t) => w.find(`[data-testid="${t}"]`).exists())
    expect(present).toEqual(['ui-error'])
    expect(w.find('[data-testid="list-filters"]').exists()).toBe(true)
    expect(w.findComponent(ListFilterBar).exists()).toBe(true)
  })

  it('(f2) lỗi nạp CHỈ-SỐ không cướp trạng thái danh sách (INV-UX3-20)', async () => {
    // `fetchKpis` dùng CHUNG ô `store.error` với `fetchList` (stores/imm02.ts:45).
    // Bind thẳng ô đó ⇒ chỉ-số hỏng sẽ xoá trắng danh sách đang hiển thị.
    getDashboardKpisSpy.mockRejectedValue(new Error('Chỉ số hỏng.'))
    const w = await mountView()
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
    expect(w.findAll('tbody tr')).toHaveLength(ROWS.length)
  })
})
