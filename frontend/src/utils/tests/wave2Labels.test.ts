import { describe, it, expect } from 'vitest'
import { stateLabel } from '@/utils/wave2Labels'

// Regression VÒNG 15 (Software Factory): audit i18n stepper.
// WorkflowStepper-style steppers ở 4 DetailView Wave-2 (Needs, Decision,
// TechSpec, VendorEval) đều render `stateLabel(s)` cho từng workflow state.
// Bug class đã thấy ở Calibration (V14): labelFor thiếu state → rò rỉ chữ
// tiếng Anh. Test này KHOÁ: mọi workflow state của 4 stepper PHẢI được
// localize (stateLabel KHÔNG trả về nguyên văn mã EN).
//
// Nếu ai thêm state mới vào 1 stepper mà quên thêm vào STATE_LABELS →
// test này fail → chặn leak trước khi vào UI.

// Union các workflow state thực tế truyền vào stepper (đối chiếu trực tiếp với
// WORKFLOW_STATES/WORKFLOW_STEPS trong từng *DetailView.vue tại V15).
const STEPPER_STATES = {
  needs: ['Draft', 'Submitted', 'Reviewing', 'Prioritized', 'Budgeted', 'Pending Approval', 'Approved'],
  decision: ['Draft', 'Method Selected', 'Negotiation', 'Award Recommended', 'Pending Approval', 'Awarded', 'Contract Signed', 'PO Issued'],
  techspec: ['Draft', 'Reviewing', 'Benchmarked', 'Risk Assessed', 'Pending Approval', 'Locked'],
  vendoreval: ['Draft', 'Open RFQ', 'Quotation Received', 'Evaluated'],
} as const

describe('wave2Labels.stateLabel — stepper i18n coverage (no EN leak)', () => {
  const allStates = [
    ...new Set(Object.values(STEPPER_STATES).flat()),
  ]

  it.each(allStates)('localizes "%s" (không trả nguyên văn mã EN)', (state) => {
    const label = stateLabel(state)
    expect(label).not.toBe(state)
    expect(label.length).toBeGreaterThan(0)
  })

  it('spot-check một vài nhãn VN chuẩn', () => {
    expect(stateLabel('Pending Approval')).toBe('Chờ phê duyệt')
    expect(stateLabel('Draft')).toBe('Nháp')
    expect(stateLabel('Awarded')).toBe('Đã trao thầu')
  })

  it('empty/undefined → chuỗi rỗng (graceful)', () => {
    expect(stateLabel('')).toBe('')
    expect(stateLabel(undefined)).toBe('')
  })

  it('state lạ → fallback chính nó (không crash)', () => {
    expect(stateLabel('_NonExistentState')).toBe('_NonExistentState')
  })
})
