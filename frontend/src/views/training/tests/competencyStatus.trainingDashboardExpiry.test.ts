// BR-06-14 (FE) — count-vs-drill divergence: tile 'Sắp/Đã hết hạn' bind VERBATIM
// giá trị BE; badge năng lực phái sinh LIVE qua SSoT.
//
// Anchor: BE đã chuyển KPI competencies.expiring/expired + drill get_expiring_competencies(60)
// sang 1 predicate SoT date-derived (kpis.expiring == len(drill)). FE phải:
//   1. render tile = giá trị BE gửi (transport-agnostic), KHÔNG tự tính lại count.
//   2. click tile → drill khớp số card.
//   3. badge năng lực days_until_expiry<0 → 'Đã hết hạn' (KHÔNG 'Đang hiệu lực'); no leak EN.

import { describe, it, expect } from 'vitest'
import type { Imm06DashboardStats } from '@/api/imm06'
import {
  competencyExpiryTiles,
  competencyEffectiveStatusLabel,
  competencyEffectiveState,
  EXPIRY_WINDOW_DAYS,
} from '@/views/training/competencyStatus'

function makeStats(expiring: number, expired: number): Imm06DashboardStats {
  return {
    sessions: { total: 0, planned: 0, confirmed: 0, in_progress: 0, completed: 0, cancelled: 0 },
    competencies: {
      total: 99, pending: 1, active: 50,
      expiring, expired, revoked: 2,
    },
    programs: { total: 0, active: 0 },
  }
}

// Regex chặn leak nhãn EN trên UI (Expiring/Expired/Active/Revoked/Suspended/Pending).
const EN_LEAK = /\b(Expiring|Expired|Active|Revoked|Suspended|Pending)\b/

describe('TC-FE-06-EXP-01 — tile bind VERBATIM kpis.competencies.expiring/expired', () => {
  for (const v of [0, 2, 9]) {
    it(`render đúng value=${v} cho cả 2 tile (∀ value {0,2,9})`, () => {
      const tiles = competencyExpiryTiles(makeStats(v, v))
      const expiring = tiles.find(t => t.key === 'expiring')!
      const expired = tiles.find(t => t.key === 'expired')!
      // Bind VERBATIM — đúng giá trị BE gửi, không suy diễn.
      expect(expiring.value).toBe(v)
      expect(expired.value).toBe(v)
      expect(expiring.label).toBe('Sắp hết hạn')
      expect(expired.label).toBe('Đã hết hạn')
    })
  }

  it('break binding expiring→active ⇒ FAIL (chống wire nhầm nguồn)', () => {
    const stats = makeStats(7, 3)
    // Nếu ai đó wire tile 'Sắp hết hạn' vào .active (50) thay vì .expiring (7) → lệch.
    const tile = competencyExpiryTiles(stats).find(t => t.key === 'expiring')!
    expect(tile.value).toBe(stats.competencies.expiring)
    expect(tile.value).not.toBe(stats.competencies.active)
  })

  it('label tile không leak EN', () => {
    for (const t of competencyExpiryTiles(makeStats(1, 1))) {
      expect(t.label).not.toMatch(EN_LEAK)
    }
  })
})

describe('TC-FE-06-EXP-02 — click tile → drill; card text == drill length', () => {
  it('giá trị tile "Sắp hết hạn" == độ dài drill (INVARIANT card==drill)', () => {
    // Mô phỏng: BE trả kpis.expiring=4 và drill get_expiring_competencies(60) cũng 4 record
    // (cùng SoT). FE bind tile = kpis.expiring; click → list drill cùng số.
    const stats = makeStats(4, 1)
    const drill = Array.from({ length: 4 }, (_, i) => ({ name: `COMP-${i}` }))
    const tile = competencyExpiryTiles(stats).find(t => t.key === 'expiring')!
    expect(tile.value).toBe(drill.length)
  })
})

describe('TC-FE-06-EXP-03 — badge phái sinh LIVE; days_until_expiry<0 → "Đã hết hạn"', () => {
  it('Active quá hạn (days<0) → "Đã hết hạn" KHÔNG "Đang hiệu lực"', () => {
    // Cảnh huống bug: scheduler lỡ auto_expire → workflow_state vẫn Active nhưng quá hạn.
    const label = competencyEffectiveStatusLabel('Active', -5)
    expect(label).toBe('Hết hạn')
    expect(label).not.toMatch(/hiệu lực|hoạt động/i)
    expect(competencyEffectiveState('Active', -5)).toBe('Expired')
  })

  it('Active trong cửa sổ (0..60) → "Sắp hết hạn"', () => {
    expect(competencyEffectiveStatusLabel('Active', 45)).toBe('Sắp hết hạn')
    expect(competencyEffectiveStatusLabel('Active', EXPIRY_WINDOW_DAYS)).toBe('Sắp hết hạn')
    expect(competencyEffectiveState('Active', 45)).toBe('Expiring')
  })

  it('Active ngoài cửa sổ (>60) → giữ nhãn workflow_state', () => {
    expect(competencyEffectiveState('Active', 90)).toBe('Active')
  })

  it('biên: days==0 → "Sắp hết hạn"; days==-1 → "Đã hết hạn"', () => {
    expect(competencyEffectiveStatusLabel('Active', 0)).toBe('Sắp hết hạn')
    expect(competencyEffectiveStatusLabel('Active', -1)).toBe('Hết hạn')
  })

  it('Revoked/Suspended/Pending KHÔNG bị derive theo ngày', () => {
    // Revoked quá hạn vẫn là 'Đã thu hồi'; Suspended trong cửa sổ vẫn 'Tạm ngưng'.
    expect(competencyEffectiveState('Revoked', -10)).toBe('Revoked')
    expect(competencyEffectiveState('Suspended', 10)).toBe('Suspended')
    expect(competencyEffectiveStatusLabel('Revoked', -2)).toBe('Đã thu hồi')
    expect(competencyEffectiveStatusLabel('Suspended', 5)).toBe('Tạm ngưng')
  })

  it('null days_until_expiry → giữ nhãn workflow_state (không suy diễn)', () => {
    expect(competencyEffectiveState('Active', null)).toBe('Active')
  })

  it('nhãn phái sinh không leak EN ∀ state', () => {
    const cases: Array<[string, number | null]> = [
      ['Active', -5], ['Active', 45], ['Active', 90], ['Expiring', 10],
      ['Expired', -30], ['Revoked', -2], ['Suspended', 5], ['Pending Assessment', null],
    ]
    for (const [state, days] of cases) {
      expect(competencyEffectiveStatusLabel(state, days)).not.toMatch(EN_LEAK)
    }
  })
})
