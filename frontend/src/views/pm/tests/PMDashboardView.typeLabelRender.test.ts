// GATE-1 guard IMM-08 — `pm_type` là enum BE (Quarterly / Semi-Annual / Annual /
// Ad-hoc, xem pm_schedule.json `options`) và PHẢI render qua `pmTypeLabel()`.
//
// RED trước fix (2026-07-25): PMDashboardView (thẻ "Sắp đến hạn") và PMCalendarView
// (panel chi tiết sự kiện) in thẳng `{{ wo.pm_type }}` / `{{ selectedEvent.pm_type }}`
// trong khi PMWorkOrderListView đã việt-hoá → đúng lớp bug Wave-2 "list đúng,
// dashboard/detail quên map" (GATE-1 scope mở rộng sang DetailView + dashboard card).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { resetRouteMock } from '@/test/vueRouterMock'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

/** due_date trong cửa sổ "sắp đến hạn" (hôm nay → +7 ngày) mà view lọc. */
function inThreeDays(): string {
  const d = new Date()
  d.setDate(d.getDate() + 3)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const storeState = {
  workOrders: [
    {
      name: 'WO-PM-2026-00001',
      status: 'Open',
      asset_ref: 'AC-ASSET-2026-1',
      asset_name: 'Máy thở Bennett',
      pm_type: 'Semi-Annual',
      due_date: inThreeDays(),
    },
  ],
  overdueWOs: [] as unknown[],
  dashboardStats: null as unknown,
}

vi.mock('@/stores/imm08', () => ({
  useImm08Store: () => ({
    get workOrders() { return storeState.workOrders },
    get overdueWOs() { return storeState.overdueWOs },
    get dashboardStats() { return storeState.dashboardStats },
    loading: false,
    error: null,
    fetchDashboardStats: vi.fn().mockResolvedValue(undefined),
    fetchWorkOrders: vi.fn().mockResolvedValue(undefined),
  }),
}))

import PMDashboardView from '@/views/pm/PMDashboardView.vue'

const stubs = { PageHeader: true, SkeletonLoader: true, RouterLink: true }

describe('PMDashboardView — pm_type hiển thị tiếng Việt (GATE-1)', () => {
  beforeEach(() => { resetRouteMock() })

  it('thẻ "Sắp đến hạn" render nhãn VI, KHÔNG lộ enum tiếng Anh', async () => {
    const w = mount(PMDashboardView, { global: { stubs } })
    await flushPromises()
    const text = w.text()

    expect(text).toContain('Nửa năm')
    expect(text).not.toContain('Semi-Annual')
  })
})
