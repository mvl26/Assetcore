// GATE-1 guard — CMDashboardView: "Phân tích nguyên nhân hỏng" render enum
// `root_cause_breakdown[].category` (Mechanical/Electrical/User Error/Unknown…)
// PHẢI đi qua `rootCauseLabel()`; enum tiếng Anh KHÔNG được lọt ra UI.
//
// RED trước fix (2026-07-25, vòng INV-ROWSCOPE): dashboard hiển thị thẳng
// `{{ rc.category }}` trong khi list/detail đã việt-hoá → cùng lớp bug Wave-2
// "list đúng, dashboard-card quên map" (LL-FE-30 / GATE-1 scope mở rộng sang
// DetailView + dashboard card). Value gốc GIỮ NGUYÊN làm `:key` (LL-FE-52).
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { resetRouteMock } from '@/test/vueRouterMock'

vi.mock('vue-router', async () => (await import('@/test/vueRouterMock')).vueRouterMockFactory())

vi.mock('@/api/imm09', () => ({
  getMttrReport: vi.fn().mockResolvedValue({
    mttr_avg_hours: 0, total_completed: 0, sla_compliance_pct: 0,
  }),
}))

const storeState = {
  kpis: {
    kpis: {
      open_wos: 0, total_completed: 0, mttr_avg_hours: 0,
      sla_compliance_pct: 0, repeat_failure_count: 0,
    },
    root_cause_breakdown: [
      { category: 'Mechanical', count: 5 },
      { category: 'User Error', count: 3 },
      { category: 'Unknown', count: 1 },
    ],
  },
}

vi.mock('@/stores/imm09', () => ({
  useImm09Store: () => ({
    get kpis() { return storeState.kpis },
    workOrders: [],
    loading: false,
    error: null,
    fetchKPIs: vi.fn().mockResolvedValue(undefined),
    fetchWorkOrders: vi.fn().mockResolvedValue(undefined),
  }),
}))

import CMDashboardView from '@/views/cm/CMDashboardView.vue'

const stubs = {
  PageHeader: true, SkeletonLoader: true, StatusBadge: true, RouterLink: true,
}

describe('CMDashboardView — nguyên nhân gốc hiển thị tiếng Việt (GATE-1)', () => {
  beforeEach(() => { resetRouteMock() })

  it('render nhãn tiếng Việt, KHÔNG lộ enum tiếng Anh', async () => {
    const w = mount(CMDashboardView, { global: { stubs } })
    await flushPromises()
    const text = w.text()

    expect(text).toContain('Cơ học')
    expect(text).toContain('Lỗi người dùng')
    expect(text).toContain('Chưa xác định')

    expect(text).not.toContain('Mechanical')
    expect(text).not.toContain('User Error')
    expect(text).not.toContain('Unknown')
  })
})
