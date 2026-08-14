// TDD — SUB-BATCH 3a: list-page KPI strip per docs/fe/08-pm & 09-repair mockups.
// Reuses common/KpiCard. No EN status leak — labels are caller-supplied VI strings.
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import WorkOrderKpiStrip from '@/components/common/WorkOrderKpiStrip.vue'

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

  it('K4: clickable item → button + emit kpi-click(index); non-clickable stays static (no break IMM-08/09)', async () => {
    const mixed = [
      { label: 'Tĩnh', value: 1, color: 'primary' as const },
      { label: 'Quá hạn SLA', value: 4, color: 'warning' as const, clickable: true },
    ]
    const w = mount(WorkOrderKpiStrip, { props: { items: mixed } })
    // Chỉ 1 button (thẻ clickable); thẻ tĩnh không phải button.
    const clickables = w.findAll('[data-testid="wo-kpi-clickable"]')
    expect(clickables).toHaveLength(1)
    await clickables[0].trigger('click')
    expect(w.emitted('kpi-click')?.[0]).toEqual([1])
  })
})
