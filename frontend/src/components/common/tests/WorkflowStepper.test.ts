// TDD — SUB-BATCH 3b: workflow stepper cho IMM-11/12 detail.
// Render node theo state machine; nhãn do caller cấp (VI) → no EN leak.
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import WorkflowStepper from '@/components/common/WorkflowStepper.vue'

const incidentSteps = ['Open', 'Acknowledged', 'In Progress', 'Resolved', 'Closed']
const labelFor = (s: string) => ({
  Open: 'Mới mở',
  Acknowledged: 'Đã tiếp nhận',
  'In Progress': 'Đang điều tra',
  Resolved: 'Đã giải quyết',
  Closed: 'Đã đóng',
}[s] ?? s)

describe('WorkflowStepper', () => {
  it('S1: renders one node per step with VI labels (no raw EN enum)', () => {
    const w = mount(WorkflowStepper, { props: { steps: incidentSteps, current: 'In Progress', labelFor } })
    const txt = w.text()
    expect(txt).toContain('Mới mở')
    expect(txt).toContain('Đang điều tra')
    // anti-leak: BE enum strings must not surface
    expect(txt).not.toMatch(/\bOpen\b/)
    expect(txt).not.toMatch(/\bIn Progress\b/)
  })

  it('S2: marks steps before current as done, current as current, rest as todo', () => {
    const w = mount(WorkflowStepper, { props: { steps: incidentSteps, current: 'In Progress', labelFor } })
    const nodes = w.findAll('[data-state]')
    expect(nodes[0].attributes('data-state')).toBe('done')        // Open
    expect(nodes[1].attributes('data-state')).toBe('done')        // Acknowledged
    expect(nodes[2].attributes('data-state')).toBe('current')     // In Progress
    expect(nodes[3].attributes('data-state')).toBe('todo')        // Resolved
    expect(nodes[4].attributes('data-state')).toBe('todo')        // Closed
  })

  it('S3: D3 — Acknowledged is reachable as its own node (not merged into In Progress)', () => {
    const w = mount(WorkflowStepper, { props: { steps: incidentSteps, current: 'Acknowledged', labelFor } })
    const nodes = w.findAll('[data-state]')
    expect(nodes[1].attributes('data-state')).toBe('current')     // Acknowledged is the current step
    expect(nodes[2].attributes('data-state')).toBe('todo')        // In Progress not yet reached
  })

  it('S4: off-path current (e.g. RCA Required) → no crash, last node stays todo', () => {
    const w = mount(WorkflowStepper, { props: { steps: incidentSteps, current: 'RCA Required', labelFor } })
    const nodes = w.findAll('[data-state]')
    expect(nodes).toHaveLength(5)
    expect(nodes[4].attributes('data-state')).toBe('todo')        // Closed not reached
  })
})
