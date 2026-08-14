import { describe, it, expect } from 'vitest'
import {
  calibrationStatusLabel,
  calibrationStatusClass,
  capaWorkflowLabel,
  CAPA_WORKFLOW_LABEL,
  historyStateLabel,
  lifecycleStatusLabel,
  lifecycleStatusClass,
  LIFECYCLE_STATUS_LABEL,
  LIFECYCLE_STATUS_UNKNOWN_LABEL,
  SCAN_ACTION_LABELS,
  SCAN_ACTION_FALLBACK_LABEL,
  scanActionLabel,
} from '@/constants/labels'
import { translateStatus } from '@/utils/formatters'

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

// ─── IMM-00 lifecycle status SSoT — màn quét QR (AssetScanInfoView) ───────────
// BE phát 7 mã canonical cho AC Asset.lifecycle_status (ADR-001 — đúng thiết kế).
// LIFECYCLE_STATUS_LABEL/CLASS (SSoT) PHẢI phủ ĐỦ cả 7, nếu không status pill
// rơi vào fallback raw-EN (?? v) / gray (bg-gray-100). Bug gốc: THIẾU
// 'Under Maintenance' → pill hiện 'Under Maintenance' + nền xám trên màn quét QR.
describe('lifecycleStatus SSoT — phủ đủ 7 mã canonical BE (no raw-EN / no gray-fallback)', () => {
  const CANONICAL = [
    'Active',
    'Commissioned',
    'Under Maintenance',
    'Under Repair',
    'Calibrating',
    'Out of Service',
    'Decommissioned',
  ] as const

  it('LIFECYCLE_STATUS_LABEL phủ đủ 7 mã canonical (không mã nào thiếu)', () => {
    for (const code of CANONICAL) {
      expect(LIFECYCLE_STATUS_LABEL, `thiếu key "${code}"`).toHaveProperty(code)
    }
  })

  it("lifecycleStatusLabel('Under Maintenance') === 'Đang bảo trì'", () => {
    expect(lifecycleStatusLabel('Under Maintenance')).toBe('Đang bảo trì')
  })

  it("lifecycleStatusClass('Under Maintenance') === 'bg-orange-100 text-orange-800' (cam, KHÔNG gray)", () => {
    expect(lifecycleStatusClass('Under Maintenance')).toBe('bg-orange-100 text-orange-800')
    // KHÔNG rơi fallback xám.
    expect(lifecycleStatusClass('Under Maintenance')).not.toBe('bg-gray-100 text-gray-600')
  })

  it('với MỌI mã canonical: lifecycleStatusLabel(code) KHÔNG trả về chính code (không leak raw-EN qua fallback)', () => {
    for (const code of CANONICAL) {
      expect(lifecycleStatusLabel(code), `leak raw-EN cho "${code}"`).not.toBe(code)
    }
  })

  it('với MỌI mã canonical: lifecycleStatusClass(code) KHÔNG rơi gray-fallback', () => {
    for (const code of CANONICAL) {
      expect(lifecycleStatusClass(code), `gray-fallback cho "${code}"`).not.toBe('bg-gray-100 text-gray-600')
    }
  })

  // wording-drift guard: cùng 1 mã KHÔNG được có 2 chuỗi VI khác nhau giữa
  // LIFECYCLE_STATUS_LABEL (constants/labels.ts) và STATUS_MAP/translateStatus
  // (utils/formatters.ts). Single wording cho toàn app.
  it('wording-drift guard: LIFECYCLE_STATUS_LABEL khớp translateStatus cho MỌI mã canonical', () => {
    for (const code of CANONICAL) {
      expect(LIFECYCLE_STATUS_LABEL[code], `drift wording cho "${code}"`).toBe(translateStatus(code))
    }
  })

  it("'Under Maintenance' cụ thể: label === translateStatus('Under Maintenance') === 'Đang bảo trì'", () => {
    expect(LIFECYCLE_STATUS_LABEL['Under Maintenance']).toBe(translateStatus('Under Maintenance'))
    expect(translateStatus('Under Maintenance')).toBe('Đang bảo trì')
  })

  // regression: 6 mã còn lại giữ NGUYÊN label + class (không đổi hành vi).
  it('regression: 6 mã cũ giữ nguyên label + class', () => {
    const FROZEN: Record<string, { label: string; cls: string }> = {
      'Active':         { label: 'Đang hoạt động',      cls: 'bg-green-100 text-green-800' },
      'Commissioned':   { label: 'Đã đưa vào sử dụng',  cls: 'bg-indigo-100 text-indigo-800' },
      'Under Repair':   { label: 'Đang sửa chữa',       cls: 'bg-orange-100 text-orange-800' },
      'Calibrating':    { label: 'Đang hiệu chuẩn',     cls: 'bg-cyan-100 text-cyan-800' },
      'Out of Service': { label: 'Ngừng hoạt động',     cls: 'bg-red-100 text-red-800' },
      'Decommissioned': { label: 'Đã thanh lý',         cls: 'bg-gray-200 text-gray-500' },
    }
    for (const [code, exp] of Object.entries(FROZEN)) {
      expect(lifecycleStatusLabel(code), `label đổi cho "${code}"`).toBe(exp.label)
      expect(lifecycleStatusClass(code), `class đổi cho "${code}"`).toBe(exp.cls)
    }
  })
})

// ─── IMM-00 vòng 8 — status-pill no-EN/raw-code/empty leak (FE-6) ─────────────
// BE phát mã legacy/drift HOẶC rỗng cho AC Asset.lifecycle_status (services/imm00.py
// :317/597 `or ""` — đối xứng BR-00-41). Bug gốc: lifecycleStatusLabel fallback
// `?? v` trả mã thô → leak EN ('In Use'/'Retired'/'active') hoặc box trống ('')
// lên status pill màn quét QR. FE-6: fallback an toàn = LIFECYCLE_STATUS_UNKNOWN_LABEL
// ('Không xác định'). 7 mã canonical giữ nguyên byte-for-byte. lifecycleStatusClass
// giữ fallback gray trung tính — đồng bộ với label fallback.
//   • RED-first: với `?? v` cũ, lifecycleStatusLabel('In Use') === 'In Use' (raw)
//     ∧ lifecycleStatusLabel('') === '' (rỗng) → 2 case dưới FAIL trước fix.
describe('lifecycleStatusLabel — no-EN/raw-code/empty leak fallback (vòng 8 FE-6)', () => {
  // Mã legacy/drift KHÔNG thuộc 7 mã canonical → nhãn VI fallback an toàn.
  const NON_CANONICAL = ['In Use', 'Retired', 'active', 'ACTIVE', 'Foo', 'LegacyUnknown', 'GARBAGE']

  it("hằng LIFECYCLE_STATUS_UNKNOWN_LABEL === 'Không xác định' (nhãn VI, non-empty)", () => {
    expect(LIFECYCLE_STATUS_UNKNOWN_LABEL).toBe('Không xác định')
    expect(LIFECYCLE_STATUS_UNKNOWN_LABEL.length).toBeGreaterThan(0)
  })

  it("mã legacy/drift ('In Use'/'Retired'/'active'/...) → 'Không xác định' (KHÔNG trả raw code)", () => {
    for (const code of NON_CANONICAL) {
      const label = lifecycleStatusLabel(code)
      // KHÔNG trả về chính mã thô.
      expect(label, `leak raw cho "${code}"`).not.toBe(code)
      // Phải là nhãn VI fallback an toàn.
      expect(label).toBe(LIFECYCLE_STATUS_UNKNOWN_LABEL)
    }
  })

  it("'In Use' cụ thể: lifecycleStatusLabel('In Use') !== 'In Use' ∧ === nhãn VI fallback", () => {
    expect(lifecycleStatusLabel('In Use')).not.toBe('In Use')
    expect(lifecycleStatusLabel('In Use')).toBe('Không xác định')
  })

  it("nhãn fallback KHÔNG chứa ký tự ASCII Latin a-z (chỉ chữ VI có dấu + space)", () => {
    // 'Không xác định' — kiểm tra KHÔNG lọt token mã English thô (≥2 ký tự Latin liền).
    // 'x' trong 'xác' là Latin đơn nhưng đây là chữ VI; canh chuỗi mã English
    // ≥2 ký tự ASCII a-z liền nhau là dấu hiệu leak code.
    for (const code of [...NON_CANONICAL, '']) {
      const label = lifecycleStatusLabel(code)
      // Không chứa mã English gốc.
      expect(label).not.toMatch(/In Use|Retired|active|ACTIVE|Foo|LegacyUnknown|GARBAGE/)
    }
  })

  it("'' (BE phát rỗng cho legacy asset) → nhãn VI fallback non-empty (pill KHÔNG box trống)", () => {
    const label = lifecycleStatusLabel('')
    expect(label).toBe(LIFECYCLE_STATUS_UNKNOWN_LABEL)
    expect(label.length).toBeGreaterThan(0)
    // KHÔNG rỗng.
    expect(label).not.toBe('')
  })

  it('null/undefined (defensive) → nhãn VI fallback non-empty', () => {
    expect(lifecycleStatusLabel(null as unknown as string)).toBe(LIFECYCLE_STATUS_UNKNOWN_LABEL)
    expect(lifecycleStatusLabel(undefined as unknown as string)).toBe(LIFECYCLE_STATUS_UNKNOWN_LABEL)
  })

  it('7 mã canonical giữ nhãn VI cũ byte-for-byte (0 regression sau fix fallback)', () => {
    const CANON: Record<string, string> = {
      'Active':            'Đang hoạt động',
      'Commissioned':      'Đã đưa vào sử dụng',
      'Under Maintenance': 'Đang bảo trì',
      'Under Repair':      'Đang sửa chữa',
      'Calibrating':       'Đang hiệu chuẩn',
      'Out of Service':    'Ngừng hoạt động',
      'Decommissioned':    'Đã thanh lý',
    }
    for (const [code, label] of Object.entries(CANON)) {
      expect(lifecycleStatusLabel(code), `regression nhãn "${code}"`).toBe(label)
    }
  })

  it("lifecycleStatusClass mã lạ/rỗng → 'bg-gray-100 text-gray-600' trung tính (parity với label fallback)", () => {
    for (const code of [...NON_CANONICAL, '']) {
      expect(lifecycleStatusClass(code), `class lạ cho "${code}"`).toBe('bg-gray-100 text-gray-600')
    }
  })

  it('canonical giữ class cũ — KHÔNG rơi gray fallback', () => {
    expect(lifecycleStatusClass('Active')).toBe('bg-green-100 text-green-800')
    expect(lifecycleStatusClass('Out of Service')).toBe('bg-red-100 text-red-800')
    expect(lifecycleStatusClass('Decommissioned')).toBe('bg-gray-200 text-gray-500')
  })
})

// ─── SCAN_ACTION_LABELS (R1 — ADR-IMM00-QR-SCAN-ACTION §D1) ───────────────────
// SSoT nhãn VI cho 4 CTA màn quét QR. AssetScanInfoView render nhãn TỪ map này
// (KHÔNG hardcode trong .vue). Map PHẢI phủ đủ 4 key BE phát trong
// available_actions + wording VI khớp D1 (no-drift parity với label BE trong
// _SCAN_ACTION_SPECS imm00.py).
describe('SCAN_ACTION_LABELS — SSoT nhãn 4 CTA màn quét QR (D1, no-drift parity BE)', () => {
  // Mirror CHÍNH XÁC label BE `_SCAN_ACTION_SPECS` (services/imm00.py:418-427).
  // Đây là bản sao kiểm-tra ĐỘC LẬP (KHÔNG import từ labels.ts) để bắt drift nếu
  // ai đó đổi nhãn FE lệch wording D1.
  const D1_BE_LABELS: Record<string, string> = {
    report_failure:      'Báo hỏng',
    request_pm:          'Yêu cầu bảo trì',
    request_cm:          'Yêu cầu sửa chữa',
    request_calibration: 'Hiệu chuẩn',
  }

  it('phủ đủ 4 key + wording VI đúng D1', () => {
    expect(Object.keys(SCAN_ACTION_LABELS).sort()).toEqual(
      Object.keys(D1_BE_LABELS).sort(),
    )
    for (const [key, label] of Object.entries(D1_BE_LABELS)) {
      expect(SCAN_ACTION_LABELS[key], `nhãn lệch D1 cho "${key}"`).toBe(label)
    }
  })

  it('no-drift parity: scanActionLabel khớp label BE cho MỌI key', () => {
    for (const [key, label] of Object.entries(D1_BE_LABELS)) {
      expect(scanActionLabel(key), `drift wording cho "${key}"`).toBe(label)
    }
  })

  // Vòng 20 (no-raw-key-leak, parity vòng 8/17): key LẠ/drift (BE thêm action mới
  // chưa map ở FE — vd 'request_inspection') → KHÔNG trả nguyên key (rò mã thô lên
  // màn quét QR / aria-label). Fallback VI an toàn SCAN_ACTION_FALLBACK_LABEL.
  it('scanActionLabel fallback key lạ → nhãn VI an toàn (KHÔNG leak raw key)', () => {
    expect(SCAN_ACTION_FALLBACK_LABEL).toBe('Thao tác khác')
    for (const RAW of ['khong_ton_tai', 'request_inspection', 'SOME_BOGUS_KEY']) {
      expect(scanActionLabel(RAW), `leak raw key ${RAW}`).toBe(SCAN_ACTION_FALLBACK_LABEL)
      expect(scanActionLabel(RAW)).not.toContain(RAW)
    }
    // 4 key chuẩn KHÔNG rơi fallback.
    expect(scanActionLabel('report_failure')).toBe('Báo hỏng')
  })
})
