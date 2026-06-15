// TDD — F7 (P2): PersonaDashboardShell KPI grid bước tablet md → tablet 768-1023px
// KHÔNG phí khoảng trắng / KHÔNG vỡ. Áp đồng bộ skeleton-loop + KPI thật (cùng container).
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import type { PersonaKpi } from '@/api/dashboard'
import PersonaDashboardShell from './PersonaDashboardShell.vue'

const kpis: PersonaKpi[] = [
  { key: 'a', label: 'KPI A', value: 1 } as unknown as PersonaKpi,
  { key: 'b', label: 'KPI B', value: 2 } as unknown as PersonaKpi,
  { key: 'c', label: 'KPI C', value: 3 } as unknown as PersonaKpi,
  { key: 'd', label: 'KPI D', value: 4 } as unknown as PersonaKpi,
]

const stubs = { PageHeader: true, KpiCard: true }

describe('F7 — PersonaDashboardShell KPI grid tablet (md)', () => {
  it('grid container có bước md:grid-cols-* + base 1-col + xl:grid-cols-4', () => {
    const w = mount(PersonaDashboardShell, {
      props: { title: 'T', kpis, loading: false },
      global: { stubs },
    })
    const grid = w.find('.grid')
    expect(grid.exists()).toBe(true)
    const cls = grid.attributes('class') || ''
    expect(cls).toContain('grid-cols-1')
    expect(/md:grid-cols-\d/.test(cls)).toBe(true)
    expect(cls).toContain('xl:grid-cols-4')
  })

  it('render 4 KPI card khi có data (không vỡ)', () => {
    const w = mount(PersonaDashboardShell, {
      props: { title: 'T', kpis, loading: false },
      global: { stubs },
    })
    expect(w.findAllComponents({ name: 'KpiCard' }).length).toBe(4)
  })

  it('skeleton-loop dùng CÙNG container grid (4 skeleton khi loading rỗng)', () => {
    const w = mount(PersonaDashboardShell, {
      props: { title: 'T', kpis: [], loading: true },
      global: { stubs },
    })
    const grid = w.find('.grid')
    const cls = grid.attributes('class') || ''
    expect(/md:grid-cols-\d/.test(cls)).toBe(true)
    // 4 skeleton placeholder
    expect(grid.findAll('.animate-pulse').length).toBe(4)
  })
})
