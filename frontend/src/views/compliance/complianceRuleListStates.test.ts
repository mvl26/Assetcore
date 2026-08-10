// TC-UX3-27 (AC-UX-047 · lô 2) — /compliance/rules: 4 trạng thái danh sách + «Thử lại».
//
// Bug gốc đo trên đĩa 2026-08-04: `load()` không có ĐƯỜNG BÁO LỖI nào — `stores/imm16.ts`
// nuốt lỗi vào ô `error` dùng CHUNG cho 5 danh sách và KHÔNG dọn ô đó ở đầu lượt. View
// chỉ có 2 nhánh (`loading` / `!items.length`) ⇒ API hỏng rơi thẳng vào khối rỗng
// «Chưa có quy tắc tuân thủ phù hợp.» — *lỗi giả dạng rỗng*, không đường thử lại.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { resetRouteMock } from '@/test/vueRouterMock'

enableAutoUnmount(afterEach)

const listRulesSpy = vi.fn()
const createRuleSpy = vi.fn()
// `importOriginal` + ghi đè ĐÚNG hàm nạp: `stores/imm16.ts` import tĩnh 28 hàm từ module
// này, liệt kê tay sẽ trôi lệch ngay khi lớp API thêm hàm mới ("No export named …").
vi.mock('@/api/imm16', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  listRules: (...a: unknown[]) => listRulesSpy(...a),
  createRule: (...a: unknown[]) => createRuleSpy(...a),
}))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import ComplianceRuleListView from './ComplianceRuleListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const ROWS = [
  { name: 'CR-0001', rule_code: 'CR-CAL-EXPIRED', rule_name: 'Hiệu chuẩn quá hạn',
    category: 'Calibration', severity: 'High', frequency: 'Monthly', is_active: 1 },
  { name: 'CR-0002', rule_code: 'CR-PM-OVERDUE', rule_name: 'Bảo trì định kỳ quá hạn',
    category: 'PM', severity: 'Medium', frequency: 'Weekly', is_active: 1 },
]
const ok = (rows: unknown[]) => ({ items: rows, pagination: { total: rows.length, page: 1, page_size: 20, total_pages: 1 } })

const stubs = { PageHeader: true, FilterToggleButton: true, BaseModal: true }

async function mountView() {
  const w = mount(ComplianceRuleListView, { global: { stubs } })
  await flushPromises()
  return w
}
function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/compliance/rules — 4 trạng thái loại trừ + thử lại (TC-UX3-27)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetRouteMock()
    listRulesSpy.mockReset().mockResolvedValue(ok(ROWS))
    createRuleSpy.mockReset().mockResolvedValue({ name: 'CR-0003' })
  })

  it('(a) đang tải ⇒ khung xương, 0 nội dung, 0 nút «Thử lại»', async () => {
    listRulesSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.findAll('table')).toHaveLength(0)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + ĐÚNG 1 «Thử lại», KHÔNG còn câu rỗng cũ', async () => {
    listRulesSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.findAll('.alert-error')).toHaveLength(0)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.find('[data-testid="ui-empty"]').exists()).toBe(false)
    expect(w.text()).not.toContain('Chưa có quy tắc tuân thủ phù hợp')
    expect(w.text()).toContain('Máy chủ trả về 500.')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(c) rỗng thật ⇒ ui-empty có câu hướng dẫn tiếng Việt, 0 nút «Thử lại»', async () => {
    listRulesSpy.mockResolvedValue(ok([]))
    const w = await mountView()
    expect(state(w)).toBe('empty')
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Chưa có quy tắc tuân thủ nào')
    expect(w.find('[data-testid="ui-empty-description"]').text())
      .toBe('Hãy tạo quy tắc mới hoặc xoá bộ lọc để xem tất cả.')
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

  it('(e) «Thử lại» gọi lại đúng hàm nạp 1 lần ⇒ error → content', async () => {
    listRulesSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(listRulesSpy).toHaveBeenCalledTimes(1)
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(listRulesSpy).toHaveBeenCalledTimes(2)
    expect(createRuleSpy).not.toHaveBeenCalled()
    expect(state(w)).toBe('content')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('(f) loại trừ cấu trúc: đúng 1 shell, đúng 1 trạng thái; bộ lọc còn sống', async () => {
    listRulesSpy.mockRejectedValue(new Error('X'))
    const w = await mountView()
    expect(w.findAll('[data-testid="list-page-shell"]')).toHaveLength(1)
    const present = ['list-loading', 'ui-error', 'ui-empty', 'list-content']
      .filter((t) => w.find(`[data-testid="${t}"]`).exists())
    expect(present).toEqual(['ui-error'])
    expect(w.find('[data-testid="list-filters"]').exists()).toBe(true)
    expect(w.findComponent(ListFilterBar).exists()).toBe(true)
  })

  it('(g) lỗi KHÔNG dính giữa 2 lượt nạp: ô `error` dùng chung được dọn đầu lượt', async () => {
    // stores/imm16.ts dùng CHUNG 1 ref `error` cho rules/findings/audits/mr và không tự
    // dọn ⇒ nếu view không clear đầu lượt, lỗi màn trước rò sang màn sau (INV-UX3-4).
    listRulesSpy.mockRejectedValueOnce(new Error('Lỗi lượt trước.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    listRulesSpy.mockResolvedValue(ok(ROWS))
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(state(w)).toBe('content')
    expect(w.text()).not.toContain('Lỗi lượt trước.')
  })
})
