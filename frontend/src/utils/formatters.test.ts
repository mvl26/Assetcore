// TDD — IMM-16 CAPA effectiveness_check i18n (NĐ98/QMS): SSoT nhãn VI + màu compliance.
// Guard chống recurrence pattern A (English enum leak): mọi option BE phải có key trong STATUS_MAP.
import { describe, it, expect } from 'vitest'
import { translateStatus, getStatusColor, translateFrequency, translatePmType, translateDepreciationMethod, translateLifecycleEvent, formatCurrency, formatCurrencyShort } from './formatters'

const COLOR_GREEN  = 'bg-emerald-100 text-emerald-800 border border-emerald-200'
const COLOR_YELLOW = 'bg-yellow-100 text-yellow-800 border border-yellow-200'
const COLOR_RED    = 'bg-red-100 text-red-700 border border-red-200'

// Toàn bộ option của field effectiveness_check trên BE DocType (chuẩn Frappe — giữ English).
const EFFECTIVENESS_OPTIONS = ['Effective', 'Partially Effective', 'Not Effective'] as const

describe('translateStatus — CAPA effectiveness_check (IMM-16)', () => {
  it("translateStatus('Effective') === 'Hiệu quả'", () => {
    expect(translateStatus('Effective')).toBe('Hiệu quả')
  })
  it("translateStatus('Partially Effective') === 'Hiệu quả một phần'", () => {
    expect(translateStatus('Partially Effective')).toBe('Hiệu quả một phần')
  })
  it("translateStatus('Not Effective') === 'Không hiệu quả'", () => {
    expect(translateStatus('Not Effective')).toBe('Không hiệu quả')
  })

  it('không regress fallback: null/empty → —', () => {
    expect(translateStatus(null)).toBe('—')
    expect(translateStatus('')).toBe('—')
  })

  it('không để lộ token tiếng Anh cho mọi option', () => {
    for (const opt of EFFECTIVENESS_OPTIONS) {
      const vi = translateStatus(opt)
      expect(vi).not.toBe(opt)
      expect(vi).not.toMatch(/Effective/i)
    }
  })
})

describe('getStatusColor — CAPA effectiveness (pin màu compliance)', () => {
  it("getStatusColor('Effective') === COLOR_GREEN", () => {
    expect(getStatusColor('Effective')).toBe(COLOR_GREEN)
  })
  it("getStatusColor('Partially Effective') === COLOR_YELLOW", () => {
    expect(getStatusColor('Partially Effective')).toBe(COLOR_YELLOW)
  })
  it("getStatusColor('Not Effective') === COLOR_RED", () => {
    expect(getStatusColor('Not Effective')).toBe(COLOR_RED)
  })
})

describe('Guard anti-recurrence (pattern A): mọi option effectiveness_check có nhãn + màu', () => {
  it('STATUS_MAP phủ hết option — fail nếu BE thêm option mà FE quên map', () => {
    for (const opt of EFFECTIVENESS_OPTIONS) {
      // translateStatus trả raw (hoặc raw-thay-_) khi KHÔNG có key → so sánh phát hiện miss.
      expect(translateStatus(opt), `missing STATUS_MAP key for "${opt}"`).not.toBe(opt)
    }
  })
  it('STATUS_COLOR phủ hết option — fail nếu BE thêm option mà FE quên màu', () => {
    const GRAY = 'bg-slate-100 text-slate-600 border border-slate-200'
    for (const opt of EFFECTIVENESS_OPTIONS) {
      // getStatusColor fallback về GRAY khi miss → màu compliance phải khác GRAY.
      expect(getStatusColor(opt), `missing STATUS_COLOR for "${opt}"`).not.toBe(GRAY)
    }
  })
})

// ─── TDD-1 — CAPA lifecycle status SSoT (IMM-16 CAPAListView/CAPADetailView) ────
// 'Pending Verification' THIẾU trong STATUS_MAP trước consolidation → translateStatus
// trả raw EN ('Pending Verification') = leak. Thêm map → 'Chờ xác minh'.
// Đồng thời chốt nhãn canonical cho 5 mã CAPA status (chống drift list↔detail↔dashboard).
const CAPA_STATUS_OPTIONS = ['Open', 'In Progress', 'Pending Verification', 'Closed', 'Overdue'] as const
const CAPA_STATUS_EXPECTED: Record<string, string> = {
  Open: 'Đang mở',                          // KHÔNG 'Mới mở'
  'In Progress': 'Đang thực hiện',          // KHÔNG 'Đang xử lý'
  'Pending Verification': 'Chờ xác minh',
  Closed: 'Đã đóng',
  Overdue: 'Quá hạn',
}

describe('translateStatus — CAPA lifecycle status SSoT (TDD-1)', () => {
  it("translateStatus('Pending Verification') === 'Chờ xác minh' (thêm map mới)", () => {
    expect(translateStatus('Pending Verification')).toBe('Chờ xác minh')
  })
  it("alias 'Pending_Verification' (Frappe raw underscore) === 'Chờ xác minh'", () => {
    expect(translateStatus('Pending_Verification')).toBe('Chờ xác minh')
  })
  it('nhãn canonical đúng cho cả 5 mã CAPA status (không drift)', () => {
    for (const code of CAPA_STATUS_OPTIONS) {
      expect(translateStatus(code), `nhãn sai cho "${code}"`).toBe(CAPA_STATUS_EXPECTED[code])
    }
  })
  it('không leak raw EN token cho mọi mã CAPA status', () => {
    const leak = /\b(Open|In Progress|Pending Verification|Closed|Overdue)\b/
    for (const code of CAPA_STATUS_OPTIONS) {
      expect(translateStatus(code)).not.toMatch(leak)
    }
  })
})

// ─── TDD-1b — CAPA severity SSoT (Critical='Khẩn cấp', Major='Nghiêm trọng') ────
describe('translateStatus — CAPA severity SSoT (TDD-1b, chống LL-FE-30 drift)', () => {
  it("Critical → 'Khẩn cấp' (KHÔNG 'Nghiêm trọng')", () => {
    expect(translateStatus('Critical')).toBe('Khẩn cấp')
  })
  it("Major → 'Nghiêm trọng' (KHÔNG 'Quan trọng')", () => {
    expect(translateStatus('Major')).toBe('Nghiêm trọng')
  })
  it("Minor → 'Nhỏ'", () => {
    expect(translateStatus('Minor')).toBe('Nhỏ')
  })
})

// ─── TDD — IMM-12 incident status STATUS_MAP coverage (Acknowledged / RCA Required) ──
// ROOT CAUSE round-20: StatusBadge-path (translateStatus → STATUS_MAP) THIẾU key
// 'Acknowledged' + 'RCA Required' → raw-EN leak ở IncidentListView (2/4 OPEN-state
// của open_incident_filter, surface khi drill ?severity=Critical&open=1). Thêm key
// + biến thể underscore (Frappe trả raw) để dù đi path nào nhãn VI cũng đúng.
// LƯU Ý SSoT: nhãn ở đây PHẢI khớp INCIDENT_STATUS_LABEL (constants/labels.ts) là
// canonical cho domain IMM-12 — list/detail/donut cùng 1 text.
const INCIDENT_STATUS_MISSING = ['Acknowledged', 'RCA Required'] as const
const INCIDENT_STATUS_MAP_EXPECTED: Record<string, string> = {
  Acknowledged: 'Đã tiếp nhận',   // khớp INCIDENT_STATUS_LABEL
  'RCA Required': 'Cần phân tích nguyên nhân gốc',       // khớp INCIDENT_STATUS_LABEL
}

describe('translateStatus — IMM-12 incident status STATUS_MAP (TDD round-20)', () => {
  it("translateStatus('Acknowledged') === 'Đã tiếp nhận' (thêm map mới)", () => {
    expect(translateStatus('Acknowledged')).toBe('Đã tiếp nhận')
  })
  it("translateStatus('RCA Required') === 'Cần phân tích nguyên nhân gốc' (thêm map mới)", () => {
    expect(translateStatus('RCA Required')).toBe('Cần phân tích nguyên nhân gốc')
  })
  it("alias underscore 'RCA_Required' === 'Cần phân tích nguyên nhân gốc'", () => {
    expect(translateStatus('RCA_Required')).toBe('Cần phân tích nguyên nhân gốc')
  })
  it('nhãn STATUS_MAP khớp INCIDENT_STATUS_LABEL (1 SSoT, không drift)', () => {
    for (const code of INCIDENT_STATUS_MISSING) {
      expect(translateStatus(code), `nhãn sai cho "${code}"`).toBe(INCIDENT_STATUS_MAP_EXPECTED[code])
    }
  })
  it('KHÔNG leak raw EN token cho Acknowledged / RCA Required', () => {
    const leak = /\b(Acknowledged|RCA Required)\b/
    for (const code of INCIDENT_STATUS_MISSING) {
      expect(translateStatus(code)).not.toMatch(leak)
    }
  })
})

// ─── translateFrequency (SSoT — IMM-16 Compliance Rule + IMM-05 AC Asset khấu hao) ──
// Localize raw English frequency labels qua DUY NHẤT 1 map FREQUENCY_MAP.

// BE ground truth (DocType JSON options — chuẩn Frappe, giữ English ở value):
//   imm_compliance_rule.evaluation_frequency
const COMPLIANCE_FREQ_OPTIONS = ['Realtime', 'Hourly', 'Daily', 'Weekly', 'Monthly', 'Quarterly'] as const
//   ac_asset.depreciation_frequency
const ASSET_DEPR_FREQ_OPTIONS = ['Monthly', 'Quarterly', 'Yearly'] as const

describe('translateFrequency — nhãn tần suất VI', () => {
  it("translateFrequency('Realtime') === 'Thời gian thực'", () => {
    expect(translateFrequency('Realtime')).toBe('Thời gian thực')
  })
  it("translateFrequency('Hourly') === 'Hàng giờ'", () => {
    expect(translateFrequency('Hourly')).toBe('Hàng giờ')
  })
  it("translateFrequency('Daily') === 'Hàng ngày'", () => {
    expect(translateFrequency('Daily')).toBe('Hàng ngày')
  })
  it("translateFrequency('Weekly') === 'Hàng tuần'", () => {
    expect(translateFrequency('Weekly')).toBe('Hàng tuần')
  })
  it("translateFrequency('Monthly') === 'Hàng tháng'", () => {
    expect(translateFrequency('Monthly')).toBe('Hàng tháng')
  })
  it("translateFrequency('Quarterly') === 'Hàng quý'", () => {
    expect(translateFrequency('Quarterly')).toBe('Hàng quý')
  })
  it("translateFrequency('Yearly') === 'Hàng năm'", () => {
    expect(translateFrequency('Yearly')).toBe('Hàng năm')
  })
})

describe('translateFrequency — fallback null/empty/unknown (không crash)', () => {
  it("null → '—'", () => {
    expect(translateFrequency(null)).toBe('—')
  })
  it("'' → '—'", () => {
    expect(translateFrequency('')).toBe('—')
  })
  it("undefined → '—'", () => {
    expect(translateFrequency(undefined)).toBe('—')
  })
  it("giá trị lạ 'XYZ-unknown' → trả nguyên (không crash, không bịa nhãn)", () => {
    expect(translateFrequency('XYZ-unknown')).toBe('XYZ-unknown')
  })
})

describe('Guard anti-recurrence (pattern A i18n leak): FREQUENCY_MAP phủ ĐỦ option BE', () => {
  it('mọi option Compliance Rule có nhãn VI khác chuỗi gốc tiếng Anh', () => {
    for (const opt of COMPLIANCE_FREQ_OPTIONS) {
      const vi = translateFrequency(opt)
      // miss key → translateFrequency trả nguyên opt → fail (phát hiện FE quên map).
      expect(vi, `missing FREQUENCY_MAP key for compliance "${opt}"`).not.toBe(opt)
    }
  })
  it('mọi option AC Asset depreciation có nhãn VI khác chuỗi gốc tiếng Anh', () => {
    for (const opt of ASSET_DEPR_FREQ_OPTIONS) {
      const vi = translateFrequency(opt)
      expect(vi, `missing FREQUENCY_MAP key for depreciation "${opt}"`).not.toBe(opt)
    }
  })
  it('nhãn VI không lộ token tiếng Anh (Daily/Weekly/Monthly/...)', () => {
    const leakTokens = /\b(Realtime|Hourly|Daily|Weekly|Monthly|Quarterly|Yearly)\b/
    for (const opt of [...COMPLIANCE_FREQ_OPTIONS, ...ASSET_DEPR_FREQ_OPTIONS]) {
      expect(translateFrequency(opt)).not.toMatch(leakTokens)
    }
  })
})

// ─── translatePmType (SSoT — PM Schedule + PM Checklist Template.pm_type) ─────
// Gộp 2 map cục bộ trùng lặp (PmScheduleListView + PmTemplateListView) về 1 SSoT.
// BE ground truth: PM Schedule / PM Checklist Template.pm_type
const PM_TYPE_OPTIONS = ['Quarterly', 'Semi-Annual', 'Annual', 'Ad-hoc'] as const

describe('translatePmType — nhãn loại PM VI', () => {
  it("'Quarterly' → 'Hàng quý'",     () => expect(translatePmType('Quarterly')).toBe('Hàng quý'))
  it("'Semi-Annual' → 'Nửa năm'",    () => expect(translatePmType('Semi-Annual')).toBe('Nửa năm'))
  it("'Annual' → 'Hàng năm'",        () => expect(translatePmType('Annual')).toBe('Hàng năm'))
  it("'Ad-hoc' → 'Đột xuất' (nhãn canonical PM, KHÁC frequency 'Theo yêu cầu')",
    () => expect(translatePmType('Ad-hoc')).toBe('Đột xuất'))
})

describe('translatePmType — fallback null/empty/unknown (không crash)', () => {
  it("null → '—'",      () => expect(translatePmType(null)).toBe('—'))
  it("'' → '—'",        () => expect(translatePmType('')).toBe('—'))
  it("undefined → '—'", () => expect(translatePmType(undefined)).toBe('—'))
  it("key lạ → trả nguyên (không bịa nhãn)",
    () => expect(translatePmType('ZZZ')).toBe('ZZZ'))
})

describe('Guard anti-recurrence (pattern A i18n leak): PM_TYPE_MAP phủ ĐỦ option BE', () => {
  it('mọi option pm_type có nhãn VI khác chuỗi gốc tiếng Anh', () => {
    for (const opt of PM_TYPE_OPTIONS) {
      expect(translatePmType(opt), `missing PM_TYPE_MAP key for "${opt}"`).not.toBe(opt)
    }
  })
  it('nhãn VI không lộ token pm_type tiếng Anh', () => {
    const leak = /\b(Quarterly|Semi-Annual|Annual|Ad-hoc)\b/
    for (const opt of PM_TYPE_OPTIONS) {
      expect(translatePmType(opt)).not.toMatch(leak)
    }
  })
})

// ─── translateDepreciationMethod (SSoT — IMM-00/05 AC Asset + Device Model + Category) ──
// Localize raw English depreciation_method qua DUY NHẤT 1 helper.
// BE ground truth (DocType JSON options — chuẩn Frappe, giữ English ở value):
//   ac_asset.depreciation_method / ac_asset_category.default_depreciation_method
const DEPR_METHOD_OPTIONS = ['Straight Line', 'Double Declining', 'Units of Production'] as const

describe('translateDepreciationMethod — nhãn phương pháp khấu hao VI', () => {
  it("'Straight Line' → 'Đường thẳng'",
    () => expect(translateDepreciationMethod('Straight Line')).toBe('Đường thẳng'))
  it("'Double Declining' → 'Số dư giảm dần'",
    () => expect(translateDepreciationMethod('Double Declining')).toBe('Số dư giảm dần'))
  it("'Units of Production' → 'Theo sản lượng'",
    () => expect(translateDepreciationMethod('Units of Production')).toBe('Theo sản lượng'))
})

describe('translateDepreciationMethod — fallback None/null/empty/unknown (không crash)', () => {
  it("'None' → '—' (không khấu hao)", () => expect(translateDepreciationMethod('None')).toBe('—'))
  it("null → '—'",                    () => expect(translateDepreciationMethod(null)).toBe('—'))
  it("'' → '—'",                      () => expect(translateDepreciationMethod('')).toBe('—'))
  it("undefined → '—'",               () => expect(translateDepreciationMethod(undefined)).toBe('—'))
  it("key lạ 'Sum-of-Years' → trả nguyên (không bịa nhãn, không crash)",
    () => expect(translateDepreciationMethod('Sum-of-Years')).toBe('Sum-of-Years'))
})

describe('Guard anti-recurrence (pattern A i18n leak): mọi option khấu hao có nhãn VI', () => {
  it('mọi option depreciation_method có nhãn VI khác chuỗi gốc tiếng Anh', () => {
    for (const opt of DEPR_METHOD_OPTIONS) {
      expect(translateDepreciationMethod(opt), `missing DEPRECIATION_METHOD_MAP key for "${opt}"`).not.toBe(opt)
    }
  })
  it('nhãn VI không lộ token khấu hao tiếng Anh', () => {
    const leak = /\b(Straight Line|Double Declining|Units of Production)\b/
    for (const opt of DEPR_METHOD_OPTIONS) {
      expect(translateDepreciationMethod(opt)).not.toMatch(leak)
    }
  })
})

// ─── TDD IMM-00 vòng 17 — translateLifecycleEvent no-leak fallback ──────────────
// HARD-CONSTRAINT (no-leak): màn quét QR (AssetScanInfoView:229) +
// timeline (AssetDetailView:816) render recent_maintenance.event_type / event.event_type
// QUA translateLifecycleEvent. Mã LẠ (drift/legacy/enum mới chưa map) TUYỆT ĐỐI
// KHÔNG được rò raw-code/English ra UI → nhánh unknown phải trả nhãn VI an toàn 'Khác',
// KHÔNG trả nguyên input. Nhãn ĐÃ BIẾT giữ nguyên (regression-safe).
const SAFE_UNKNOWN_LABEL = 'Khác'

// 5 mã canonical bảo trì khớp BE services/imm00.py::_MAINTENANCE_EVENT_TYPES → nhãn VI cũ.
const MAINTENANCE_EVENT_VI: Record<string, string> = {
  pm_completed:        'Hoàn tất bảo trì',
  repair_completed:    'Hoàn tất sửa chữa',
  calibration_passed:  'Hiệu chuẩn đạt',
  pm_started:          'Bắt đầu bảo trì',
  calibration_started: 'Bắt đầu hiệu chuẩn',
}

// Snapshot 18 key→label của LIFECYCLE_EVENT_MAP (chống đổi nhầm nhãn đã biết).
const LIFECYCLE_VI_SNAPSHOT: Record<string, string> = {
  commissioned:                 'Đưa vào sử dụng',
  activated:                    'Kích hoạt',
  restored:                     'Khôi phục hoạt động',
  out_of_service:               'Ngừng hoạt động',
  pm_started:                   'Bắt đầu bảo trì',
  pm_completed:                 'Hoàn tất bảo trì',
  repair_opened:                'Mở phiếu sửa chữa',
  repair_completed:             'Hoàn tất sửa chữa',
  calibration_started:          'Bắt đầu hiệu chuẩn',
  calibration_passed:           'Hiệu chuẩn đạt',
  calibration_failed:           'Hiệu chuẩn không đạt',
  incident_reported:            'Ghi nhận sự cố',
  decommissioned:               'Thanh lý',
  transferred:                  'Luân chuyển',
  registered:                   'Đăng ký thiết bị',
  depreciated:                  'Trích khấu hao',
  depreciation_rules_inherited: 'Kế thừa quy tắc khấu hao',
  depreciation_stopped:         'Dừng khấu hao',
}

const UNKNOWN_DRIFT_CODES = [
  'pm_aborted', 'SOME_DRIFT', 'restored_v2', 'khong_co_trong_enum',
  'PM_COMPLETED', 'qr_generated', 'label_printed', 'State Change', 'unknown',
]

describe('translateLifecycleEvent — 5 mã bảo trì BE giữ nhãn VI cũ', () => {
  for (const [code, label] of Object.entries(MAINTENANCE_EVENT_VI)) {
    it(`'${code}' → '${label}'`, () => {
      expect(translateLifecycleEvent(code)).toBe(label)
    })
  }
})

describe('translateLifecycleEvent — mã lạ KHÔNG rò raw-code, trả nhãn an toàn', () => {
  it("'pm_aborted'/'SOME_DRIFT'/'restored_v2' → 'Khác' (≠ input)", () => {
    for (const code of ['pm_aborted', 'SOME_DRIFT', 'restored_v2']) {
      expect(translateLifecycleEvent(code)).not.toBe(code)
      expect(translateLifecycleEvent(code)).toBe(SAFE_UNKNOWN_LABEL)
    }
  })
})

describe('translateLifecycleEvent — invariant no-leak với mọi mã lạ', () => {
  it("không kết quả nào chứa '_' và không kết quả nào bằng input", () => {
    for (const code of UNKNOWN_DRIFT_CODES) {
      const out = translateLifecycleEvent(code)
      expect(out, `rò '_' qua "${code}" → "${out}"`).not.toContain('_')
      expect(out, `rò chính input "${code}"`).not.toBe(code)
    }
  })
})

describe('translateLifecycleEvent — regression 18 key map giữ nguyên nhãn', () => {
  for (const [code, label] of Object.entries(LIFECYCLE_VI_SNAPSHOT)) {
    it(`'${code}' → '${label}'`, () => {
      expect(translateLifecycleEvent(code)).toBe(label)
    })
  }
  it('toàn bộ nhãn đã biết KHÔNG chứa snake_case EN', () => {
    for (const code of Object.keys(LIFECYCLE_VI_SNAPSHOT)) {
      expect(/[a-z]_[a-z]/.test(translateLifecycleEvent(code)), `nhãn còn snake_case: ${code}`).toBe(false)
    }
  })
})

describe('translateLifecycleEvent — rỗng giữ nguyên hành vi', () => {
  it("null / '' / undefined → '—'", () => {
    expect(translateLifecycleEvent(null)).toBe('—')
    expect(translateLifecycleEvent('')).toBe('—')
    expect(translateLifecycleEvent(undefined)).toBe('—')
  })
})

// ─── L-16 (audit BaoCao_RaSoat_17062026) — SSoT compact-currency tr/tỷ ──────
// Trước: DepreciationView + InventoryDashboardView mỗi nơi tự định nghĩa
// `vndShort` (trùng lặp). Gom về 1 hàm thuần (testable) — hành vi PHẢI khớp
// inline cũ: '—' cho null · "x.x tỷ" (≥1e9) · "x tr" (≥1e6) · full VND khác.
describe('formatCurrencyShort — L-16 SSoT compact VND (tr/tỷ)', () => {
  it('≥ 1 tỷ → "x.x tỷ" (1 chữ số thập phân)', () => {
    expect(formatCurrencyShort(2_500_000_000)).toBe('2.5 tỷ')
    expect(formatCurrencyShort(1_000_000_000)).toBe('1.0 tỷ')
  })
  it('≥ 1 triệu (< tỷ) → "x tr" (làm tròn nguyên)', () => {
    expect(formatCurrencyShort(5_000_000)).toBe('5 tr')
    expect(formatCurrencyShort(1_000_000)).toBe('1 tr')
  })
  it('< 1 triệu → full VND, đồng bộ formatCurrency (không phụ thuộc ICU symbol)', () => {
    expect(formatCurrencyShort(500_000)).toBe(formatCurrency(500_000))
    expect(formatCurrencyShort(0)).toBe(formatCurrency(0))
  })
  it('null/undefined → "—" (giữ hành vi inline cũ)', () => {
    expect(formatCurrencyShort(null)).toBe('—')
    expect(formatCurrencyShort(undefined)).toBe('—')
  })
  it('số âm vẫn rút gọn theo độ lớn |v|', () => {
    expect(formatCurrencyShort(-1_500_000_000)).toBe('-1.5 tỷ')
  })
})
