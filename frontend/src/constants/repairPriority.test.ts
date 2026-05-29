// Regression guard (SUB-BATCH 3a) — CM list priority filter must match BE
// Asset Repair.priority enum exactly: Normal | Urgent | Emergency.
// Old bug: dropdown used Critical/High/Medium/Low → filter never matched any record.
import { describe, it, expect } from 'vitest'
import { REPAIR_PRIORITY_OPTIONS, priorityLabel } from './labels'

const BE_PRIORITY_ENUM = ['Normal', 'Urgent', 'Emergency']

describe('REPAIR_PRIORITY_OPTIONS — sync với BE enum', () => {
  it('P1: every option value is a valid BE priority', () => {
    for (const opt of REPAIR_PRIORITY_OPTIONS) {
      expect(BE_PRIORITY_ENUM).toContain(opt.value)
    }
  })

  it('P2: covers all 3 BE priority values', () => {
    const vals = REPAIR_PRIORITY_OPTIONS.map((o) => o.value).sort()
    expect(vals).toEqual([...BE_PRIORITY_ENUM].sort())
  })

  it('P3: no legacy invalid values (Critical/High/Medium/Low)', () => {
    const vals = REPAIR_PRIORITY_OPTIONS.map((o) => o.value)
    for (const bad of ['Critical', 'High', 'Medium', 'Low']) {
      expect(vals).not.toContain(bad)
    }
  })

  it('P4: every option has a Vietnamese label (no raw enum leak)', () => {
    for (const opt of REPAIR_PRIORITY_OPTIONS) {
      expect(opt.label).toBeTruthy()
      expect(opt.label).not.toBe(opt.value)
      expect(priorityLabel(opt.value)).toBeTruthy()
    }
  })
})
