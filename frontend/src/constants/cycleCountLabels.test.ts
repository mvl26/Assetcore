// TDD — IMM-15 Cycle Count nhãn tiếng Việt SSoT: đủ 4 state + 4 count_type,
// không thiếu key, và KHỚP StatusBadge SSoT (formatters.translateStatus) cho state.
import { describe, it, expect } from 'vitest'
import {
  CYCLE_COUNT_STATE_LABELS, CYCLE_COUNT_TYPE_LABELS,
  CYCLE_COUNT_STATE_OPTIONS, CYCLE_COUNT_TYPE_OPTIONS,
  cycleCountStateLabel, cycleCountTypeLabel,
} from './cycleCountLabels'
import { translateStatus } from '@/utils/formatters'

const STATES = ['Planned', 'Counting', 'Reviewed', 'Posted']
const TYPES = ['Full', 'ABC_A_Monthly', 'Cycle', 'Spot']

describe('CYCLE_COUNT_STATE_LABELS', () => {
  it('phủ đủ 4 trạng thái, không thiếu key', () => {
    for (const s of STATES) {
      expect(CYCLE_COUNT_STATE_LABELS[s], `thiếu state: ${s}`).toBeTruthy()
    }
    expect(Object.keys(CYCLE_COUNT_STATE_LABELS).sort()).toEqual([...STATES].sort())
  })

  it('mỗi nhãn là tiếng Việt (không leak nguyên văn key tiếng Anh)', () => {
    for (const s of STATES) {
      expect(cycleCountStateLabel(s)).not.toBe(s)
    }
  })

  it('KHỚP StatusBadge SSoT (formatters.translateStatus) — chống drift', () => {
    for (const s of STATES) {
      expect(cycleCountStateLabel(s)).toBe(translateStatus(s))
    }
  })
})

describe('CYCLE_COUNT_TYPE_LABELS', () => {
  it('phủ đủ 4 loại kiểm kê, không thiếu key', () => {
    for (const t of TYPES) {
      expect(CYCLE_COUNT_TYPE_LABELS[t], `thiếu count_type: ${t}`).toBeTruthy()
    }
    expect(Object.keys(CYCLE_COUNT_TYPE_LABELS).sort()).toEqual([...TYPES].sort())
  })

  it('mỗi nhãn là tiếng Việt (không leak key tiếng Anh)', () => {
    for (const t of TYPES) {
      expect(cycleCountTypeLabel(t)).not.toBe(t)
    }
  })

  it('option list = value(enum gốc) + label(tiếng Việt)', () => {
    expect(CYCLE_COUNT_STATE_OPTIONS.map(o => o.value).sort()).toEqual([...STATES].sort())
    expect(CYCLE_COUNT_TYPE_OPTIONS.map(o => o.value).sort()).toEqual([...TYPES].sort())
  })
})

describe('fallback an toàn', () => {
  it('giá trị lạ → trả nguyên văn (không crash), rỗng → ""', () => {
    expect(cycleCountStateLabel('Weird')).toBe('Weird')
    expect(cycleCountStateLabel('')).toBe('')
    expect(cycleCountTypeLabel(undefined)).toBe('')
  })
})
