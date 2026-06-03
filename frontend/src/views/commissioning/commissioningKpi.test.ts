// TDD — IMM-04 list-page KPI strip mapping (docs/imm-04/06_Frontend_Design.md §3.1,
// docs/fe/04-commissioning/commissioning-list.html). Pure function: kpis → WoKpiItem[].
// VI labels caller-supplied (no EN status leak); clickable KPIs carry a `filterState`.
import { describe, it, expect } from 'vitest'
import { commissioningKpiItems } from './commissioningKpi'
import type { KpiStats } from '@/types/imm04'

const kpis: KpiStats = {
  pending_count: 12,
  hold_count: 2,
  open_nc_count: 3,
  released_this_month: 8,
  overdue_sla: 1,
}

describe('commissioningKpiItems', () => {
  it('K1: null kpis → empty array (no crash)', () => {
    expect(commissioningKpiItems(null)).toEqual([])
    expect(commissioningKpiItems(undefined)).toEqual([])
  })

  it('K2: maps all 5 KPIs in spec order', () => {
    const items = commissioningKpiItems(kpis)
    expect(items).toHaveLength(5)
    expect(items.map(i => i.value)).toEqual([12, 2, 3, 8, 1])
  })

  it('K3: VI labels only — no raw English workflow-state token in labels', () => {
    // Core Doc §3.1 đính chính 2026-06-02: nhãn KPI phải tiếng Việt theo bảng
    // i18n; workflow_state gốc tiếng Anh chỉ dùng làm filterState, không ra label.
    const labels = commissioningKpiItems(kpis).map(i => i.label).join(' ')
    expect(labels).toContain('Phiếu đang mở')
    expect(labels).toContain('Tạm giữ lâm sàng') // Clinical Hold → VI
    expect(labels).toContain('NC mở')
    expect(labels).toContain('Bàn giao tháng này') // Clinical Release → VI
    expect(labels).toContain('Quá hạn SLA')
    expect(labels).not.toMatch(/\b(Open|In Progress|Completed|Pending|Released|Clinical Hold|Clinical Release|Release)\b/)
  })

  it('K4: state KPIs carry filterState; overdue card drills via overdueFilter (BR-04-10)', () => {
    const items = commissioningKpiItems(kpis)
    // pending → reset (empty string clears the workflow_state filter)
    expect(items[0].filterState).toBe('')
    expect(items[1].filterState).toBe('Clinical Hold')
    expect(items[2].filterState).toBe('Non Conformance')
    expect(items[3].filterState).toBe('Clinical Release')
    // overdue: virtual filter `overdue=1` (KHÔNG dùng workflow_state) → clickable, không còn display-only
    expect(items[4].filterState).toBeUndefined()
    expect(items[4].overdueFilter).toBe(true)
    expect(items[4].clickable).toBe(true)
  })

  it('K5: semantic colors per severity; overdue is warning (actionable, not neutral)', () => {
    const items = commissioningKpiItems(kpis)
    expect(items[0].color).toBe('primary')
    expect(items[1].color).toBe('warning')
    expect(items[2].color).toBe('danger')
    expect(items[3].color).toBe('success')
    // vòng 32: neutral → warning vì thẻ chuyển sang clickable drill
    expect(items[4].color).toBe('warning')
  })
})
