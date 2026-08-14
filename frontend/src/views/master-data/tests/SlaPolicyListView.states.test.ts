// TC-UX3-20 (AC-UX-047 · lô 1) — /sla-policies: 4 trạng thái danh sách + «Thử lại».
//
// Bug gốc đo trên đĩa 2026-08-03: `load()` (`SlaPolicyListView.vue:99`) có `try … finally`
// nhưng **0 `catch`** ⇒ API hỏng ⇒ in «Chưa có chính sách cam kết mức dịch vụ.». Biến `err`
// thuộc HỘP THOẠI lưu (`:151`) — KHÔNG nối vào danh sách (INV-UX3-13).
// Bẫy riêng: `filteredPolicies` là lọc CLIENT ⇒ `is-empty` bám mảng ĐANG HIỂN THỊ.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { mount, flushPromises, enableAutoUnmount } from '@vue/test-utils'
import { resetRouteMock } from '@/test/vueRouterMock'

enableAutoUnmount(afterEach)

const listSlaPoliciesSpy = vi.fn()
vi.mock('@/api/imm00', () => ({
  listSlaPolicies: (...a: unknown[]) => listSlaPoliciesSpy(...a),
  getSlaPolicy: vi.fn(),
  createSlaPolicy: vi.fn(),
  updateSlaPolicy: vi.fn(),
  deleteSlaPolicy: vi.fn(),
}))
vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

import SlaPolicyListView from '@/views/master-data/SlaPolicyListView.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const ROWS = [
  { name: 'SLA-0001', policy_name: 'Khẩn cấp — thiết bị hồi sức', priority: 'P1', risk_class: 'Critical',
    response_time_minutes: 30, resolution_time_hours: 4, is_active: 1, is_default: 0 },
  { name: 'SLA-0002', policy_name: 'Tiêu chuẩn', priority: 'P3', risk_class: 'Medium',
    response_time_minutes: 240, resolution_time_hours: 24, is_active: 1, is_default: 1 },
]

const stubs = { PageHeader: true, FilterToggleButton: true, ApproverSelect: true, DateInput: true }

async function mountView() {
  const w = mount(SlaPolicyListView, { global: { stubs } })
  await flushPromises()
  return w
}

function state(w: ReturnType<typeof mount>) {
  return w.find('[data-testid="list-page-shell"]').attributes('data-state')
}
function retryControls(w: ReturnType<typeof mount>) {
  return w.findAll('button').filter((b) => (b.attributes('aria-label') ?? b.text()).trim() === 'Thử lại')
}

describe('/sla-policies — 4 trạng thái loại trừ + thử lại (TC-UX3-20)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    resetRouteMock()
    listSlaPoliciesSpy.mockReset().mockResolvedValue(ROWS)
  })

  it('(a) đang tải ⇒ khung xương, 0 nội dung, 0 nút «Thử lại»', async () => {
    listSlaPoliciesSpy.mockReturnValue(new Promise(() => {}))
    const w = await mountView()
    expect(state(w)).toBe('loading')
    expect(w.find('[data-testid="list-skeleton"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(retryControls(w)).toHaveLength(0)
  })

  it('(b) lỗi ⇒ ui-error + đúng 1 «Thử lại», KHÔNG còn chuỗi rỗng cũ', async () => {
    listSlaPoliciesSpy.mockRejectedValue(new Error('Máy chủ trả về 500.'))
    const w = await mountView()
    expect(state(w)).toBe('error')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(true)
    expect(w.findAll('[data-testid="list-content"]')).toHaveLength(0)
    expect(w.text()).not.toContain('Chưa có')
    expect(retryControls(w)).toHaveLength(1)
  })

  it('(c) rỗng thật ⇒ ui-empty có câu hướng dẫn tiếng Việt, 0 nút «Thử lại»', async () => {
    listSlaPoliciesSpy.mockResolvedValue([])
    const w = await mountView()
    expect(state(w)).toBe('empty')
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Chưa có chính sách cam kết mức dịch vụ')
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
    listSlaPoliciesSpy.mockRejectedValueOnce(new Error('Mất kết nối.'))
    const w = await mountView()
    expect(listSlaPoliciesSpy).toHaveBeenCalledTimes(1)
    await retryControls(w)[0].trigger('click')
    await flushPromises()
    expect(listSlaPoliciesSpy).toHaveBeenCalledTimes(2)
    expect(state(w)).toBe('content')
  })

  it('(f) loại trừ cấu trúc: đúng 1 shell, đúng 1 trạng thái; bộ lọc còn sống', async () => {
    listSlaPoliciesSpy.mockRejectedValue(new Error('X'))
    const w = await mountView()
    expect(w.findAll('[data-testid="list-page-shell"]')).toHaveLength(1)
    const present = ['list-loading', 'ui-error', 'ui-empty', 'list-content']
      .filter((t) => w.find(`[data-testid="${t}"]`).exists())
    expect(present).toEqual(['ui-error'])
    expect(w.findComponent(ListFilterBar).exists()).toBe(true)
  })
})
