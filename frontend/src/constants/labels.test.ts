import { describe, it, expect } from 'vitest'
import {
  calibrationStatusLabel,
  calibrationStatusClass,
  capaWorkflowLabel,
  CAPA_WORKFLOW_LABEL,
  historyStateLabel,
} from './labels'

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

// ─── RECON (IMM-11 §4.1.3) — asset calibration cache badge SSoT ───────────────
// check_calibration_expiry full-set reconcile ghi 5 literal vào
// AC Asset.calibration_status: On Schedule / Due Soon / Overdue / Calibration
// Failed / Not Required (+ reset neutral ''). AssetDetailView + AssetListView
// render badge qua calibrationStatusLabel/Class. Phải localize ĐỦ — đặc biệt:
//   - 'Calibration Failed' (terminal, BR-11-11) → 'Không đạt hiệu chuẩn' verbatim
//   - 'On Schedule' (rollup normal) KHÔNG được rò raw EN
//   - '' và 'Not Required' (stale-clear neutral, BR-11-10) → nhãn sạch, KHÔNG
//     'Quá hạn'/'Overdue' trên thiết bị hết active schedule.
describe('calibrationStatusLabel — asset calibration cache badge (RECON SSoT)', () => {
  it("'Calibration Failed' → 'Không đạt hiệu chuẩn' (verbatim, terminal)", () => {
    expect(calibrationStatusLabel('Calibration Failed')).toBe('Không đạt hiệu chuẩn')
  })
  it("'On Schedule' localized (no raw EN leak)", () => {
    const label = calibrationStatusLabel('On Schedule')
    expect(label).not.toBe('On Schedule')
    expect(label).not.toMatch(/On Schedule/)
    expect(label.length).toBeGreaterThan(0)
  })
  it("'Overdue' → 'Quá hạn'", () => {
    expect(calibrationStatusLabel('Overdue')).toBe('Quá hạn')
  })
  it("'Due Soon' → 'Sắp đến hạn'", () => {
    expect(calibrationStatusLabel('Due Soon')).toBe('Sắp đến hạn')
  })
  it("neutral reset ('' / 'Not Required') KHÔNG render 'Quá hạn' (stale-clear)", () => {
    // '' → empty/dash; 'Not Required' → 'Không yêu cầu'. KHÔNG được là 'Quá hạn'.
    expect(calibrationStatusLabel('')).not.toBe('Quá hạn')
    expect(calibrationStatusLabel('Not Required')).toBe('Không yêu cầu')
    expect(calibrationStatusLabel('Not Required')).not.toMatch(/Overdue|Quá hạn/)
  })
  it('mọi literal cache hợp lệ KHÔNG rò raw EN token', () => {
    const CACHE_LITERALS = ['On Schedule', 'Due Soon', 'Overdue', 'Calibration Failed', 'Not Required']
    const enLeak = /\b(On Schedule|Due Soon|Overdue|Calibration Failed|Not Required)\b/
    for (const v of CACHE_LITERALS) {
      expect(calibrationStatusLabel(v), `leak EN cho "${v}"`).not.toMatch(enLeak)
    }
  })
  it('class map có entry cho mọi literal cache (không gray-fallback ngầm)', () => {
    for (const v of ['On Schedule', 'Due Soon', 'Overdue', 'Calibration Failed', 'Not Required']) {
      expect(calibrationStatusClass(v), `thiếu class cho "${v}"`).toBeTruthy()
    }
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

// IMM-11 TDD-RECON FE: AC Asset.calibration_status rollup-cache write-path
// (services.shared.constants.CalibrationStatus). Badge trên AssetDetailView/
// AssetListView render qua calibrationStatusLabel/Class SSoT. Khoá:
//  - reset trung tính ('Not Required' + '' rỗng) → KHÔNG bao giờ ra "Quá hạn"/leak EN.
//  - terminal 'Calibration Failed' → "Không đạt hiệu chuẩn" nguyên văn (preserve khi OoS).
//  - rollup 'On Schedule' (BE ghi On Schedule, KHÔNG phải 'Calibrated') không leak EN.
describe('assetCalibrationBadge — AC Asset.calibration_status SSoT (no raw-EN leak)', () => {
  const BE_STATUSES = ['On Schedule', 'Due Soon', 'Overdue', 'Calibration Failed', 'Not Required']

  it('mọi giá trị BE write-path đều có nhãn VI, không lọt token tiếng Anh', () => {
    for (const s of BE_STATUSES) {
      const label = calibrationStatusLabel(s)
      expect(label).toBeTruthy()
      expect(label).not.toBe(s) // đã được dịch, không nguyên văn EN
      expect(label).not.toMatch(/\b(On Schedule|Due Soon|Overdue|Calibration Failed|Not Required)\b/)
    }
  })

  it("neutral reset: 'Not Required' và '' KHÔNG render 'Quá hạn' và sạch tiếng Anh", () => {
    expect(calibrationStatusLabel('Not Required')).toBe('Không yêu cầu')
    expect(calibrationStatusLabel('Not Required')).not.toBe('Quá hạn')
    // '' (neutral reset của reconciliation) → render rỗng, không leak EN, không "Quá hạn"
    expect(calibrationStatusLabel('')).toBe('')
    expect(calibrationStatusLabel('')).not.toMatch(/Overdue|Quá hạn/)
  })

  it("terminal 'Calibration Failed' → 'Không đạt hiệu chuẩn' (verbatim)", () => {
    expect(calibrationStatusLabel('Calibration Failed')).toBe('Không đạt hiệu chuẩn')
    expect(calibrationStatusClass('Calibration Failed')).toContain('red')
  })

  it("'On Schedule' (BE rollup) → nhãn VI, không leak 'On Schedule'", () => {
    expect(calibrationStatusLabel('On Schedule')).toBe('Đúng lịch hiệu chuẩn')
  })

  it('class luôn có giá trị (kể cả unknown) — badge không vỡ', () => {
    expect(calibrationStatusClass('Not Required')).toBeTruthy()
    expect(calibrationStatusClass('')).toBe('bg-gray-100 text-gray-600')
  })
})
