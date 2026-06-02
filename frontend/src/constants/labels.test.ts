import { describe, it, expect } from 'vitest'
import { calibrationStatusLabel, capaWorkflowLabel, CAPA_WORKFLOW_LABEL, historyStateLabel } from './labels'

// Regression VÒNG 14: WorkflowStepper trên CalibrationDetailView dùng
// `calibrationStatusLabel` làm labelFor. Bug gốc: hàm này trỏ vào map
// CALIBRATION_STATUS_LABEL (asset calibration health: Calibrated/Due Soon/...)
// THIẾU các workflow-state của phiếu hiệu chuẩn (Scheduled/Sent to Lab/
// Certificate Received/Passed/Conditionally Passed/Cancelled) → stepper rò rỉ
// chữ tiếng Anh "Scheduled"/"Passed". Test này khoá việc mọi workflow-state
// đều được localize (không trả về nguyên văn tiếng Anh).

describe('calibrationStatusLabel — workflow-state coverage (stepper i18n)', () => {
  const WORKFLOW_STATES = [
    'Scheduled',
    'Sent to Lab',
    'In Progress',
    'Certificate Received',
    'Passed',
    'Failed',
    'Conditionally Passed',
    'Cancelled',
  ]

  it.each(WORKFLOW_STATES)('localizes workflow state "%s" (no EN leak)', (state) => {
    const label = calibrationStatusLabel(state)
    // Phải khác chính nó (đã dịch) và không chứa ký tự ASCII-only nguyên văn EN.
    expect(label).not.toBe(state)
    // Nhãn VN phải có ký tự tiếng Việt hoặc khác hoàn toàn chuỗi EN gốc.
    expect(label.length).toBeGreaterThan(0)
  })

  it('Scheduled → "Đã lên lịch"', () => {
    expect(calibrationStatusLabel('Scheduled')).toBe('Đã lên lịch')
  })

  it('Passed → "Đạt"', () => {
    expect(calibrationStatusLabel('Passed')).toBe('Đạt')
  })

  it('Conditionally Passed → "Đạt có điều kiện"', () => {
    expect(calibrationStatusLabel('Conditionally Passed')).toBe('Đạt có điều kiện')
  })

  it('unknown value falls back to itself (graceful)', () => {
    expect(calibrationStatusLabel('SomeUnknownState')).toBe('SomeUnknownState')
  })
})

// Regression R17: CAPADetailView confirm-modal hiển thị `pendingTransition.target`
// (workflow_state máy trạng thái) NGUYÊN VĂN tiếng Anh "Investigating"/"Action
// Plan"... → rò rỉ. CAPA_STATUS_LABEL chỉ phủ `status` (Open/In Progress/Closed/
// Overdue), KHÔNG phủ 7 workflow_state. Test này khoá: mọi workflow_state CAPA
// đều có label tiếng Việt (khớp CapaWorkflowState trong api/imm16.ts).
describe('capaWorkflowLabel — workflow-state coverage (confirm modal + stepper i18n)', () => {
  const CAPA_WF_STATES = [
    'Open', 'Investigating', 'Action Plan', 'Implementation',
    'Verification', 'Closed', 'Re-opened',
  ]
  it('every CAPA workflow_state maps to VI, no raw English token', () => {
    for (const s of CAPA_WF_STATES) {
      expect(CAPA_WORKFLOW_LABEL).toHaveProperty(s)
      const label = capaWorkflowLabel(s)
      expect(label).toBeTruthy()
      expect(label).not.toMatch(/\b(Open|Investigating|Action Plan|Implementation|Verification|Closed|Re-opened)\b/)
    }
  })
  it('Investigating → "Đang điều tra"', () => {
    expect(capaWorkflowLabel('Investigating')).toBe('Đang điều tra')
  })
  it('unknown value falls back to itself (graceful)', () => {
    expect(capaWorkflowLabel('WeirdState')).toBe('WeirdState')
  })
})

// R24: RecordHistory dùng chung hiển thị from→to state cho nhiều doctype.
// Bug gốc: render raw `e.from_status → e.to_status` → rò "→ Open" tiếng Anh.
// historyStateLabel(refDoctype, value) phải localize theo đúng doctype.
describe('historyStateLabel — doctype-aware state i18n (RecordHistory)', () => {
  it('Incident Report "Open" → "Mới mở"', () => {
    expect(historyStateLabel('Incident Report', 'Open')).toBe('Mới mở')
  })
  it('IMM RCA Record "Completed" → "Đã hoàn tất"', () => {
    expect(historyStateLabel('IMM RCA Record', 'Completed')).toBe('Đã hoàn tất')
  })
  it('Asset Commissioning "Clinical Hold" → "Tạm giữ lâm sàng"', () => {
    expect(historyStateLabel('Asset Commissioning', 'Clinical Hold')).toBe('Tạm giữ lâm sàng')
  })
  it('empty value → "—"', () => {
    expect(historyStateLabel('Incident Report', '')).toBe('—')
    expect(historyStateLabel('Incident Report', null)).toBe('—')
  })
  it('unknown doctype + unknown value falls back to de-underscored code', () => {
    expect(historyStateLabel('Weird Doctype', 'Some_Unknown_Code')).toBe('Some Unknown Code')
  })
})
