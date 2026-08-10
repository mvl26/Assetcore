// TDD — IMM-14 DecommissionListView render: rows từ listDecommissions hiển thị
// nhãn tiếng Việt (StatusBadge VI + disposal_method + responsible_name), KHÔNG
// leak raw EN workflow_state, KHÔNG rò email; filter đổi → gọi lại đúng tham số;
// click row → điều hướng /assets/:asset.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { routerPushSpy } from '@/test/vueRouterMock'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn(), show: vi.fn() }),
}))

const ROWS = [
  {
    name: 'DECOM-2026-0001', asset: 'AC-ASS-0001',
    asset_name_snapshot: 'Máy thở Hamilton C6', risk_classification_snapshot: 'Critical',
    workflow_state: 'Approved', disposal_method: 'Bán/Trade-in',
    decommissioned_on: '2026-06-20 10:00:00',
    responsible: 'nva@benhvien.test', responsible_name: 'Nguyễn Văn A',
  },
  {
    name: 'DECOM-2026-0002', asset: 'AC-ASS-0002',
    asset_name_snapshot: 'Bơm tiêm điện Terumo', risk_classification_snapshot: 'Medium',
    workflow_state: 'Draft', disposal_method: 'Huỷ',
    decommissioned_on: null,
    responsible: 'ttb@benhvien.test', responsible_name: 'Trần Thị B',
  },
]

const listDecommissionsSpy = vi.fn().mockResolvedValue({
  data: ROWS, pagination: { total: 2, page: 1, page_size: 20, total_pages: 1 },
})
vi.mock('@/api/imm14', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/imm14')>()
  return {
    ...actual,
    listDecommissions: (f: Record<string, unknown>, p: number, ps: number) =>
      listDecommissionsSpy(f, p, ps),
  }
})

import DecommissionListView from './DecommissionListView.vue'

async function mountList() {
  const w = mount(DecommissionListView, {
    global: { stubs: { RouterLink: true, Transition: false } },
  })
  await flushPromises()
  return w
}

beforeEach(() => {
  setActivePinia(createPinia())
  listDecommissionsSpy.mockClear()
  listDecommissionsSpy.mockResolvedValue({
    data: ROWS, pagination: { total: 2, page: 1, page_size: 20, total_pages: 1 },
  })
  routerPushSpy().mockClear()
})

describe('DecommissionListView render', () => {
  it('gọi listDecommissions và render đủ 2 biên bản', async () => {
    const w = await mountList()
    expect(listDecommissionsSpy).toHaveBeenCalled()
    expect(w.text()).toContain('DECOM-2026-0001')
    expect(w.text()).toContain('DECOM-2026-0002')
    // tên thiết bị (snapshot), KHÔNG chỉ mã
    expect(w.text()).toContain('Máy thở Hamilton C6')
    expect(w.text()).toContain('Bơm tiêm điện Terumo')
  })

  it('workflow_state render tiếng Việt domain-specific SSoT, KHÔNG leak raw EN', async () => {
    const w = await mountList()
    const txt = w.text()
    expect(txt).toContain('Đã giải nhiệm')  // Approved (hồ sơ duyệt = thiết bị đã giải nhiệm)
    expect(txt).toContain('Chờ duyệt')       // Draft (hồ sơ chờ duyệt)
    expect(txt).not.toContain('Approved')
    // 'Draft' không được lộ như 1 từ độc lập trong nội dung hiển thị
    expect(txt).not.toMatch(/\bDraft\b/)
  })

  it('hiển thị phương thức xử lý (nhãn VI SSoT) + người chịu trách nhiệm (tên, KHÔNG email)', async () => {
    const w = await mountList()
    const txt = w.text()
    // disposal_method 'Bán/Trade-in' → nhãn VI 'Bán/Thu cũ đổi mới' (dịch phần EN)
    expect(txt).toContain('Bán/Thu cũ đổi mới')
    expect(txt).not.toContain('Trade-in')
    expect(txt).toContain('Huỷ')
    expect(txt).toContain('Nguyễn Văn A')
    expect(txt).toContain('Trần Thị B')
    // KHÔNG rò email của người chịu trách nhiệm
    expect(txt).not.toContain('nva@benhvien.test')
    expect(txt).not.toContain('@')
  })

  it('empty state — data rỗng render empty-state, không lỗi', async () => {
    listDecommissionsSpy.mockResolvedValueOnce({
      data: [], pagination: { total: 0, page: 1, page_size: 20, total_pages: 0 },
    })
    const w = await mountList()
    // AC-UX-047 lô 3 (2026-08-04): màn đã áp `ui/ListPageShell` ⇒ chữ rỗng lấy theo bảng copy
    // SSoT `docs/ui-ux/02 §14.4` và render qua `ui/EmptyState` (một nguồn cho cả 40 màn).
    expect(w.find('[data-testid="ui-empty-title"]').text()).toBe('Chưa có biên bản giải nhiệm nào')
    expect(w.find('[data-testid="ui-error"]').exists()).toBe(false)
  })

  it('filter reload — đổi dropdown Trạng thái → gọi lại listDecommissions kèm filter đúng', async () => {
    const w = await mountList()
    listDecommissionsSpy.mockClear()   // bỏ lần gọi onMounted
    const select = w.find('#decom-state-filter')
    await select.setValue('Approved')
    await flushPromises()
    expect(listDecommissionsSpy).toHaveBeenCalledWith({ workflow_state: 'Approved' }, 1, 20)
  })

  it('filter reload — đổi dropdown Phương thức xử lý → filter disposal_method đúng', async () => {
    const w = await mountList()
    listDecommissionsSpy.mockClear()
    const select = w.find('#decom-method-filter')
    await select.setValue('Huỷ')
    await flushPromises()
    expect(listDecommissionsSpy).toHaveBeenCalledWith({ disposal_method: 'Huỷ' }, 1, 20)
  })

  it('row click → router.push tới /decommissions/:name (biên bản, KHÔNG /assets/:asset)', async () => {
    const w = await mountList()
    const push = routerPushSpy()
    push.mockClear()
    await w.find('tbody tr').trigger('click')
    expect(push).toHaveBeenCalledWith('/decommissions/DECOM-2026-0001')
  })

  it('link phụ "Hồ sơ thiết bị" → router.push tới /assets/:asset (giữ vị trí phụ)', async () => {
    const w = await mountList()
    const push = routerPushSpy()
    push.mockClear()
    const assetLinks = w.findAll('button').filter((b) => b.text() === 'Hồ sơ thiết bị')
    expect(assetLinks.length).toBeGreaterThan(0)
    await assetLinks[0].trigger('click')
    expect(push).toHaveBeenCalledWith('/assets/AC-ASS-0001')
  })
})
