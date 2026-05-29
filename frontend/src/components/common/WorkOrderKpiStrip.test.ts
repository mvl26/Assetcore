// TDD — SUB-BATCH 3a: list-page KPI strip per docs/fe/08-pm & 09-repair mockups.
// Reuses common/KpiCard. No EN status leak — labels are caller-supplied VI strings.
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import WorkOrderKpiStrip from './WorkOrderKpiStrip.vue'

const items = [
  { label: 'Trong tuần', value: 14, color: 'primary' as const, trend: '7 đã phân công' },
  { label: 'Quá hạn', value: 12, color: 'danger' as const },
  { label: 'Hoàn tất tháng', value: 38, color: 'success' as const },
  { label: 'Lỗi nghiêm trọng', value: 3, color: 'warning' as const },
]

describe('WorkOrderKpiStrip', () => {
  it('K1: renders one KpiCard per item', () => {
    const w = mount(WorkOrderKpiStrip, { props: { items } })
    expect(w.findAllComponents({ name: 'KpiCard' })).toHaveLength(4)
  })

  it('K2: renders VI labels + numeric values, no raw English status token', () => {
    const w = mount(WorkOrderKpiStrip, { props: { items } })
    const txt = w.text()
    expect(txt).toContain('Trong tuần')
    expect(txt).toContain('Quá hạn')
    expect(txt).toContain('14')
    expect(txt).toContain('38')
    // anti-leak: no raw BE status enum strings surface here
    expect(txt).not.toMatch(/\b(Open|In Progress|Overdue|Completed|Pending Parts|In Repair)\b/)
  })

  it('K3: empty items → renders nothing (no crash)', () => {
    const w = mount(WorkOrderKpiStrip, { props: { items: [] } })
    expect(w.findAllComponents({ name: 'KpiCard' })).toHaveLength(0)
  })
})
