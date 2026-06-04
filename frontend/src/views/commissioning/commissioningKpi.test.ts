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

// ─────────────────────────────────────────────────────────────────────────────
// TC-FE-04-KPI-01 — Vòng 16: re-anchor 'Bàn giao tháng này' về commissioning_date
// (BE đổi `released_this_month` từ anchor `modified` → `commissioning_date`).
// Bằng chứng FE FORWARD-COMPAT / TRANSPORT-AGNOSTIC: thẻ 'Bàn giao tháng này' bind
// `kpis.released_this_month` VERBATIM — FE KHÔNG biết & KHÔNG cần biết BE đếm theo
// anchor nào. Zero shape-change: field giữ type number, nhãn VI bất biến,
// filterState='Clinical Release' bất biến, không leak EN. Nếu BE đổi anchor mà card
// vẫn render đúng giá trị BE gửi + giữ filter → SoT-aligned card==drill 'Clinical Release'.
// (Drill list theo cửa sổ tháng = backlog ngoài scope round — xem STATE.)
// ─────────────────────────────────────────────────────────────────────────────
describe('commissioningKpiItems — TC-FE-04-KPI-01 re-anchor regression', () => {
  const CARD_IDX = 3 // 'Bàn giao tháng này' nằm ở index 3 (sau pending/hold/nc).

  it('card "Bàn giao tháng này" binds released_this_month verbatim (anchor-agnostic)', () => {
    // BE đổi anchor modified→commissioning_date ⇒ con số khác đi (vd phiếu Released
    // tháng trước bị edit tháng này KHÔNG còn bị đếm). FE chỉ render value BE gửi.
    for (const n of [0, 1, 8, 42]) {
      const items = commissioningKpiItems({ ...kpis, released_this_month: n })
      const card = items[CARD_IDX]
      expect(card.value).toBe(n) // pass-through tuyệt đối — không tự tính lại ở FE
      expect(card.label).toBe('Bàn giao tháng này') // nhãn VI bất biến
      expect(card.filterState).toBe('Clinical Release') // drill tới state Released
      expect(card.color).toBe('success')
    }
  })

  it('zero shape-change: card value giữ type number, không leak EN/raw status', () => {
    const items = commissioningKpiItems({ ...kpis, released_this_month: 5 })
    const card = items[CARD_IDX]
    expect(typeof card.value).toBe('number') // type number bất biến (imm04.ts:207)
    // nhãn hiển thị tuyệt đối không lộ token tiếng Anh 'Released'/'Clinical Release'.
    expect(card.label).not.toMatch(/\b(Released|Release|Clinical|Commission(ing|ed)?|modified|Active|Pending)\b/i)
  })

  it('re-anchor KHÔNG đụng các thẻ khác (only released_this_month thay đổi)', () => {
    const base = commissioningKpiItems(kpis)
    const reanchored = commissioningKpiItems({ ...kpis, released_this_month: 999 })
    // mọi thẻ ngoài index 3 phải y hệt (label/value/filterState) → đổi anchor cô lập.
    for (let i = 0; i < base.length; i++) {
      if (i === CARD_IDX) continue
      expect(reanchored[i].label).toBe(base[i].label)
      expect(reanchored[i].value).toBe(base[i].value)
      expect(reanchored[i].filterState).toBe(base[i].filterState)
    }
    expect(reanchored[CARD_IDX].value).toBe(999)
  })
})
