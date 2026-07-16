// Copyright (c) 2026, AssetCore Team
// Từ điển nhãn tiếng Việt dùng chung cho toàn bộ UI.
// Các giá trị khóa khớp với enum trong backend (giữ nguyên để gửi lên API),
// nhưng hiển thị ra UI luôn phải dùng hàm tLabel() từ file này.

// ─── Trạng thái Work Order (IMM-08 / IMM-09) ──────────────────────────────────
export const WO_STATUS_LABELS: Record<string, string> = {
  Open: 'Mới',
  Assigned: 'Đã phân công',
  'In Progress': 'Đang thực hiện',
  In_Progress: 'Đang thực hiện',
  Scheduled: 'Đã lên lịch',
  'Pending–Device Busy': 'Tạm dừng — Thiết bị đang dùng',
  Pending_Parts: 'Chờ linh kiện',
  Diagnosing: 'Đang chẩn đoán',
  In_Repair: 'Đang sửa chữa',
  Pending_Inspection: 'Chờ kiểm tra',
  Overdue: 'Quá hạn',
  Completed: 'Hoàn thành',
  'Halted–Major Failure': 'Tạm dừng — Lỗi nghiêm trọng',
  Cancelled: 'Đã hủy',
  Cannot_Repair: 'Không sửa được',
}

// ─── Trạng thái phiếu nghiệm thu IMM-04 ───────────────────────────────────────
export const COMMISSIONING_STATE_LABELS: Record<string, string> = {
  Draft: 'Nháp',
  Draft_Reception: 'Nháp tiếp nhận',
  'Draft Reception': 'Nháp tiếp nhận',
  Reception: 'Tiếp nhận',
  Pending_Doc_Verify: 'Chờ kiểm tra hồ sơ',
  'Pending Doc Verify': 'Chờ kiểm tra hồ sơ',
  Site_Preparation: 'Chuẩn bị hiện trường',
  'Site Preparation': 'Chuẩn bị hiện trường',
  To_Be_Installed: 'Chờ lắp đặt',
  'To Be Installed': 'Chờ lắp đặt',
  Installing: 'Đang lắp đặt',
  Identification: 'Nhận dạng',
  Initial_Inspection: 'Kiểm tra ban đầu',
  'Initial Inspection': 'Kiểm tra ban đầu',
  Baseline_Safety: 'Kiểm tra an toàn',
  'Baseline Safety': 'Kiểm tra an toàn',
  Pending_Release: 'Chờ phê duyệt',
  'Pending Release': 'Chờ phê duyệt',
  Clinical_Hold: 'Tạm giữ lâm sàng',
  'Clinical Hold': 'Tạm giữ lâm sàng',
  Clinical_Release: 'Phát hành lâm sàng',
  'Clinical Release': 'Phát hành lâm sàng',
  Commissioned: 'Đã đưa vào sử dụng',
  Return_To_Vendor: 'Trả nhà cung cấp',
  'Return To Vendor': 'Trả nhà cung cấp',
  Re_Inspection: 'Kiểm tra lại',
  'Re Inspection': 'Kiểm tra lại',
  Radiation_Hold: 'Tạm giữ phóng xạ',
  'Radiation Hold': 'Tạm giữ phóng xạ',
  Non_Conformance: 'Không phù hợp',
  'Non Conformance': 'Không phù hợp',
}

// ─── Trạng thái tài liệu IMM-05 ────────────────────────────────────────────────
export const DOC_STATUS_LABELS: Record<string, string> = {
  Active: 'Hiệu lực',
  Draft: 'Nháp',
  'Pending Review': 'Chờ duyệt',
  Pending_Approval: 'Chờ phê duyệt',
  Expired: 'Hết hạn',
  Expiring_Soon: 'Sắp hết hạn',
  Archived: 'Lưu trữ',
  Rejected: 'Từ chối',
  Exempt: 'Miễn đăng ký',
}

// ─── Trạng thái tài sản (AC Asset lifecycle_status) ───────────────────────────
export const ASSET_STATUS_LABELS: Record<string, string> = {
  Draft: 'Nháp',
  Commissioned: 'Đã đưa vào sử dụng',
  Active: 'Đang hoạt động',
  'Under Maintenance': 'Đang bảo trì',
  Under_Maintenance: 'Đang bảo trì',
  'Under Repair': 'Đang sửa chữa',
  Under_Repair: 'Đang sửa chữa',
  Calibrating: 'Đang hiệu chuẩn',
  'Out of Service': 'Ngừng sử dụng',
  Out_of_Service: 'Ngừng sử dụng',
  Decommissioned: 'Đã thanh lý',
}

// ─── Trạng thái hiệu chuẩn (IMM-11) ───────────────────────────────────────────
export const CALIBRATION_STATUS_LABELS: Record<string, string> = {
  Scheduled: 'Đã lên lịch',
  'Sent to Lab': 'Đã gửi phòng hiệu chuẩn',
  Sent_to_Lab: 'Đã gửi phòng hiệu chuẩn',
  'In Progress': 'Đang thực hiện',
  In_Progress: 'Đang thực hiện',
  'Certificate Received': 'Đã nhận chứng nhận',
  Certificate_Received: 'Đã nhận chứng nhận',
  Passed: 'Đạt',
  Failed: 'Không đạt',
  'Conditionally Passed': 'Đạt có điều kiện',
  Cancelled: 'Đã hủy',
}

// ─── Mức độ ưu tiên / nghiêm trọng ────────────────────────────────────────────
export const PRIORITY_LABELS: Record<string, string> = {
  Low: 'Thấp',
  Medium: 'Trung bình',
  Normal: 'Bình thường',
  High: 'Cao',
  Urgent: 'Khẩn',
  Critical: 'Khẩn cấp',
  Emergency: 'Cấp cứu',
}

// IMM-09 Asset Repair.priority — KHỚP DocType enum (asset_repair.json: Normal|Urgent|Emergency).
// Single source of truth cho filter dropdown CM list. KHÔNG dùng Critical/High/Medium/Low
// (giá trị cũ sai → filter không bao giờ khớp record). Thứ tự ưu tiên giảm dần.
export const REPAIR_PRIORITY_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
  { value: 'Emergency', label: 'Cấp cứu' },
  { value: 'Urgent', label: 'Khẩn' },
  { value: 'Normal', label: 'Bình thường' },
]

export const SEVERITY_LABELS: Record<string, string> = {
  Minor: 'Nhỏ',
  Major: 'Nghiêm trọng',
  Critical: 'Khẩn cấp',
}

// ─── Loại sửa chữa / nguyên nhân hỏng ─────────────────────────────────────────
export const REPAIR_TYPE_LABELS: Record<string, string> = {
  Corrective: 'Sửa chữa khắc phục',
  Emergency: 'Cấp cứu',
  'Warranty Repair': 'Bảo hành',
  Warranty_Repair: 'Bảo hành',
}

export const ROOT_CAUSE_LABELS: Record<string, string> = {
  Electrical: 'Lỗi điện',
  Mechanical: 'Lỗi cơ khí',
  Software: 'Lỗi phần mềm',
  'User Error': 'Lỗi người dùng',
  User_Error: 'Lỗi người dùng',
  'Wear and Tear': 'Hao mòn',
  Wear_and_Tear: 'Hao mòn',
  Unknown: 'Chưa xác định',
}

// ─── Loại NC (Non-Conformance) ────────────────────────────────────────────────
export const NC_TYPE_LABELS: Record<string, string> = {
  DOA: 'Hỏng ngay khi nhận',
  'DOA (Dead on Arrival)': 'Hỏng ngay khi nhận',
  Missing_Accessory: 'Thiếu phụ kiện',
  Physical_Damage: 'Hỏng vật lý',
  Technical_Fault: 'Lỗi kỹ thuật',
  Missing_Document: 'Thiếu tài liệu',
  Other: 'Khác',
}

// ─── Trạng thái phê duyệt tài khoản ───────────────────────────────────────────
export const APPROVAL_STATUS_LABELS: Record<string, string> = {
  Pending: 'Chờ phê duyệt',
  Approved: 'Đã phê duyệt',
  Rejected: 'Từ chối',
}

// ─── Trạng thái CAPA ──────────────────────────────────────────────────────────
export const CAPA_STATUS_LABELS: Record<string, string> = {
  Draft: 'Nháp',
  Open: 'Đang mở',
  'In Progress': 'Đang xử lý',
  In_Progress: 'Đang xử lý',
  Pending_Approval: 'Chờ phê duyệt',
  Closed: 'Đã đóng',
  Cancelled: 'Đã hủy',
}

// ─── Trạng thái hợp đồng dịch vụ ─────────────────────────────────────────────
export const CONTRACT_STATUS_LABELS: Record<string, string> = {
  Draft: 'Nháp',
  Submitted: 'Đã gửi',
  Active: 'Đang hiệu lực',
  Expired: 'Hết hạn',
  Terminated: 'Đã chấm dứt',
  Cancelled: 'Đã hủy',
}

// ─── Helper tra cứu chung ─────────────────────────────────────────────────────
/**
 * Tra cứu nhãn tiếng Việt cho một giá trị enum.
 * Nếu không có nhãn phù hợp, trả về chuỗi gốc (đã bỏ dấu gạch dưới).
 */
export function tLabel(dict: Record<string, string>, value?: string | null): string {
  if (!value) return '—'
  return dict[value] ?? value.replaceAll('_', ' ')
}

// ═══════════════════════════════════════════════════════════════════════════
// Per-domain helpers + class maps (merged from utils/labels.ts)
// ═══════════════════════════════════════════════════════════════════════════
// ─── Frappe docstatus ─────────────────────────────────────────────────────────
export const DOC_STATUS_LABEL: Record<number, string> = {
  0: 'Bản nháp',
  1: 'Đã chốt',
  2: 'Đã hủy',
}
export const DOC_STATUS_CLASS: Record<number, string> = {
  0: 'bg-gray-100 text-gray-600',
  1: 'bg-blue-100 text-blue-800',
  2: 'bg-red-100 text-red-600 line-through',
}
export function docStatusLabel(v: number) { return DOC_STATUS_LABEL[v] ?? String(v) }
export function docStatusClass(v: number) { return DOC_STATUS_CLASS[v] ?? 'bg-gray-100 text-gray-600' }

// ─── AC Asset lifecycle ───────────────────────────────────────────────────────
export const LIFECYCLE_STATUS_LABEL: Record<string, string> = {
  // Đồng bộ wording với formatters.translateStatus + AssetListView (chống drift).
  // Phủ ĐỦ 7 mã canonical BE phát cho AC Asset.lifecycle_status (ADR-001):
  // Active / Commissioned / Under Maintenance / Under Repair / Calibrating /
  // Out of Service / Decommissioned — không mã nào rơi fallback raw-EN trên màn quét QR.
  'Commissioned':       'Đã đưa vào sử dụng',
  'Active':             'Đang hoạt động',
  'Under Maintenance':  'Đang bảo trì',   // khớp formatters.STATUS_MAP:96 (single wording)
  'Under Repair':       'Đang sửa chữa',
  'Calibrating':        'Đang hiệu chuẩn',
  'Out of Service':     'Ngừng hoạt động',
  'Decommissioned':     'Đã thanh lý',
}
export const LIFECYCLE_STATUS_CLASS: Record<string, string> = {
  'Commissioned':       'bg-indigo-100 text-indigo-800',
  'Active':             'bg-green-100 text-green-800',
  'Under Maintenance':  'bg-orange-100 text-orange-800',   // cam — đồng bộ COLOR_ORANGE (formatters STATUS_COLORS:399) & 'Under Repair'
  'Under Repair':       'bg-orange-100 text-orange-800',
  'Calibrating':        'bg-cyan-100 text-cyan-800',
  'Out of Service':     'bg-red-100 text-red-800',
  'Decommissioned':     'bg-gray-200 text-gray-500',
}
// Nhãn VI fallback an toàn cho lifecycle_status KHÔNG thuộc 7 mã canonical HOẶC
// rỗng/null/undefined. CONTRACT no-EN/raw-code-leak: BE phát mã legacy/drift
// ('In Use'/'Retired'/'active') hoặc rỗng (services/imm00.py:317/597 `or ""`,
// đối xứng BR-00-41) → status pill màn quét QR KHÔNG bao giờ rò mã English/code
// thô hay box trống. Wording phải đồng bộ với BE `_lifecycle_vi` (chống drift
// tương lai); class fallback gray trung tính của lifecycleStatusClass parity với
// nhãn này (FR-00-93 + BR-00-42 · 06 §status-pill-safe II.3e-PILLNOLEAK).
export const LIFECYCLE_STATUS_UNKNOWN_LABEL = 'Không xác định'
// Fallback an toàn no-EN/raw-code/empty leak: mã ∉ 7 canonical HOẶC rỗng/null/
// undefined → 'Không xác định' (KHÔNG `?? v` trả mã thô). Dùng `||` (KHÔNG `??`)
// để `''` BE phát cho legacy asset cũng rơi fallback, không hiện pill box trống.
export function lifecycleStatusLabel(v: string) { return LIFECYCLE_STATUS_LABEL[v] || LIFECYCLE_STATUS_UNKNOWN_LABEL }
export function lifecycleStatusClass(v: string) { return LIFECYCLE_STATUS_CLASS[v] ?? 'bg-gray-100 text-gray-600' }

// ─── Hành động màn quét QR (R1 — ADR-IMM00-QR-SCAN-ACTION §D1) ────────────────
// SSoT nhãn VI cho 4 CTA màn quét QR (AssetScanInfoView). Key = action.key BE
// emit trong available_actions (build_asset_scan_info → _scan_action_specs). FE
// render nhãn TỪ map này (KHÔNG hardcode nhãn trong .vue) — no-drift parity với
// label BE (_SCAN_ACTION_SPECS imm00.py: 'Báo hỏng'/'Yêu cầu bảo trì'/
// 'Yêu cầu sửa chữa'/'Hiệu chuẩn'). BE vẫn là nguồn enabled/reason/route; map
// này CHỈ là nhãn hiển thị, khoá wording VI một chỗ.
export const SCAN_ACTION_LABELS: Record<string, string> = {
  report_failure:      'Báo hỏng',
  request_pm:          'Yêu cầu bảo trì',
  request_cm:          'Yêu cầu sửa chữa',
  request_calibration: 'Hiệu chuẩn',
}
// Nhãn VI fallback an toàn cho action key LẠ/drift (BE thêm action mới chưa map ở
// FE — vd 'request_inspection'). no-raw-key-leak (parity vòng 8/17): KHÔNG `?? key`
// (rò mã thô lên màn quét QR / aria-label). Wording trung tính — KHÔNG khẳng định
// loại thao tác chưa biết. Bất biến: scanActionLabel KHÔNG bao giờ trả lại key thô.
export const SCAN_ACTION_FALLBACK_LABEL = 'Thao tác khác'
export function scanActionLabel(key: string) {
  return SCAN_ACTION_LABELS[key] ?? SCAN_ACTION_FALLBACK_LABEL
}

// ─── Số ĐK lưu hành Bộ Y tế — drill NĐ98 (BR-00-17) ───────────────────────────
// SSoT nhãn tiếng Việt cho 2 bucket byt_status. KHÔNG hardcode chuỗi rải rác
// (chống drift tile↔chip). Key khớp param BE list_assets(byt_status) + drill query.
//   BYT_EXPIRY_LABEL      — nhãn đầy đủ cho tile dashboard admin (label_vi).
//   BYT_EXPIRY_CHIP_LABEL — nhãn rút gọn cho chip filter AssetListView.
export const BYT_EXPIRY_LABEL: Record<'expiring' | 'expired', string> = {
  expiring: 'ĐK Bộ Y tế sắp hết hạn (30 ngày)',
  expired:  'ĐK Bộ Y tế đã hết hạn',
}
export const BYT_EXPIRY_CHIP_LABEL: Record<'expiring' | 'expired', string> = {
  expiring: 'ĐK BYT sắp hết hạn',
  expired:  'ĐK BYT đã hết hạn',
}
export function bytExpiryLabel(v?: string | null): string {
  if (v === 'expiring' || v === 'expired') return BYT_EXPIRY_LABEL[v]
  return v ?? '—'
}

// ─── Calibration status ───────────────────────────────────────────────────────
// AC Asset.calibration_status (rollup-cache) — KHỚP byte-for-byte với BE
// services.shared.constants.CalibrationStatus: On Schedule / Due Soon / Overdue /
// Calibration Failed / Not Required (+ '' neutral reset → render rỗng, không leak EN).
export const CALIBRATION_STATUS_LABEL: Record<string, string> = {
  'Calibrated':         'Đã hiệu chuẩn',
  'On Schedule':        'Đúng lịch hiệu chuẩn',
  'Due Soon':           'Sắp đến hạn',
  'Overdue':            'Quá hạn',
  'Not Required':       'Không yêu cầu',
  'In Progress':        'Đang hiệu chuẩn',
  'Failed':             'Không đạt',
  'Calibration Failed': 'Không đạt hiệu chuẩn',
}
export const CALIBRATION_STATUS_CLASS: Record<string, string> = {
  'Calibrated':         'bg-green-100 text-green-800',
  'On Schedule':        'bg-green-100 text-green-800',
  'Due Soon':           'bg-yellow-100 text-yellow-800',
  'Overdue':            'bg-red-100 text-red-800',
  'Not Required':       'bg-gray-100 text-gray-500',
  'In Progress':        'bg-blue-100 text-blue-800',
  'Failed':             'bg-red-200 text-red-900 font-semibold',
  'Calibration Failed': 'bg-red-200 text-red-900 font-semibold',
}
export function calibrationStatusLabel(v: string) {
  // Ưu tiên workflow-state của phiếu hiệu chuẩn (Scheduled/Sent to Lab/Passed/...)
  // — đây là tập state mà WorkflowStepper truyền vào. Fallback sang map sức khoẻ
  // hiệu chuẩn của tài sản (Calibrated/Due Soon/Overdue/...) rồi mới về nguyên văn.
  return CALIBRATION_STATUS_LABELS[v] ?? CALIBRATION_STATUS_LABEL[v] ?? v
}
export function calibrationStatusClass(v: string) { return CALIBRATION_STATUS_CLASS[v] ?? 'bg-gray-100 text-gray-600' }

// ─── Medical device class ─────────────────────────────────────────────────────
export const MEDICAL_DEVICE_CLASS_LABEL: Record<string, string> = {
  'Class I':   'Loại I — Rủi ro thấp',
  'Class II':  'Loại II — Rủi ro trung bình',
  'Class III': 'Loại III — Rủi ro cao',
}
export function medicalDeviceClassLabel(v: string) { return MEDICAL_DEVICE_CLASS_LABEL[v] ?? v }

// ─── Incident severity ────────────────────────────────────────────────────────
export const INCIDENT_SEVERITY_LABEL: Record<string, string> = {
  'Low':      'Thấp',
  'Medium':   'Trung bình',
  'High':     'Cao',
  'Critical': 'Nghiêm trọng',
}
export const INCIDENT_SEVERITY_CLASS: Record<string, string> = {
  'Low':      'bg-gray-100 text-gray-600',
  'Medium':   'bg-yellow-100 text-yellow-800',
  'High':     'bg-orange-100 text-orange-800',
  'Critical': 'bg-red-200 text-red-900 font-semibold',
}
export function incidentSeverityLabel(v: string) { return INCIDENT_SEVERITY_LABEL[v] ?? v }
export function incidentSeverityClass(v: string) { return INCIDENT_SEVERITY_CLASS[v] ?? 'bg-gray-100 text-gray-600' }

// ─── Risk classification (AC Asset.risk_classification — Low/Medium/High/Critical) ──
// SSoT nhãn VI cho enum EN 'Low/Medium/High/Critical' của AC Asset (read-only,
// fetch_from device_model). BE GIỮ raw enum làm SSoT contract (KHÔNG dịch) → FE map
// sang VI tại đây. KHÔNG nhầm với risk_class (A/B/C/D — WHO/NĐ98 letter class của
// asset_commissioning/asset_repair) — đó là field KHÁC.
//
// riskClassificationLabel(v): giá trị NGOÀI 4 enum (drift/legacy) → nhãn VI an toàn
// 'Khác' (KHÔNG leak chuỗi EN thô). Trường hợp RỖNG ('' / whitespace / null) caller
// XỬ LÝ TRƯỚC → 'Chưa phân loại' (helper này CHỈ map giá trị ĐÃ-CÓ-MẶT; rỗng đi tới
// 'Khác' nếu lọt vào đây, nhưng caller chuẩn không truyền rỗng).
export const RISK_CLASSIFICATION_LABEL: Record<string, string> = {
  'Low':      'Thấp',
  'Medium':   'Trung bình',
  'High':     'Cao',
  'Critical': 'Nghiêm trọng',
}
export function riskClassificationLabel(v: string) { return RISK_CLASSIFICATION_LABEL[v] ?? 'Khác' }

// ─── Phân loại rủi ro CAO (urgency) — SSoT tập enum high-risk (vòng 47) ───────
// Tập con enum risk_classification được coi là "rủi ro cao" → mang affordance
// cảnh báo trực quan ở UI (vd dòng 'Phân loại rủi ro' màn quét QR). Derive THUẦN
// presentation bằng enum-equality trên giá trị server đã .trim() — KHÔNG so
// client-clock, KHÔNG nghiệp vụ FE (parity nguyên tắc overdue SSoT vòng 21).
// Khoá literal 'High'/'Critical' MỘT chỗ — KHÔNG rải rác trong .vue (parity
// SSoT RISK_CLASSIFICATION_LABEL). NHÃN hiển thị vẫn qua RISK_CLASSIFICATION_LABEL
// (riskText 'Cao'/'Nghiêm trọng') — tập này CHỈ phân loại urgency, KHÔNG render.
export const HIGH_RISK_CLASSIFICATIONS: ReadonlySet<string> = new Set(['High', 'Critical'])
// isHighRiskClassification(v): enum-equality sau .trim() (defensive whitespace từ
// payload stale/drift). rỗng / null / undefined / ngoài-4-enum (Low/Medium hoặc
// drift) → false (no false-alarm). CHỈ 'High'/'Critical' (đã trim) → true.
export function isHighRiskClassification(v?: string | null): boolean {
  return HIGH_RISK_CLASSIFICATIONS.has((v ?? '').trim())
}

// ─── Vi phạm SLA sự cố (IMM-12, BR-12-09) ─────────────────────────────────────
// Khớp field BE Incident Report.response_breached / resolution_breached (0|1).
// SSoT cho nhãn tiếng Việt — KHÔNG hardcode trong component, KHÔNG leak "breached".
export const SLA_BREACH_LABEL = {
  response:   'Vi phạm cam kết mức dịch vụ tiếp nhận',
  resolution: 'Vi phạm cam kết mức dịch vụ xử lý',
} as const
export const SLA_BREACH_BADGE_CLASS = 'bg-red-100 text-red-700 ring-1 ring-red-200'

// Nhãn trạng thái SLA cho màn Chi tiết (section 'Tình trạng SLA') — mỗi dòng
// Phản hồi/Xử lý hiển thị 1 badge trạng thái theo cờ DERIVED của BE (0|1). Text
// đầy đủ tiếng Việt (KHÔNG chỉ phân biệt bằng màu — WCAG 2.1 AA).
export const SLA_STATUS_LABEL = {
  breached: 'Quá hạn',
  within:   'Trong hạn',
} as const
export const SLA_WITHIN_BADGE_CLASS = 'bg-emerald-100 text-emerald-700 ring-1 ring-emerald-200'

// ─── Incident type (khớp INCIDENT_TYPES trong IncidentCreateView + BE) ─────────
export const INCIDENT_TYPE_LABEL: Record<string, string> = {
  'Failure':      'Hỏng hóc',
  'Safety Event': 'Sự kiện an toàn',
  'Near Miss':    'Suýt xảy ra',
  'Malfunction':  'Hoạt động sai',
}
export function incidentTypeLabel(v: string) { return INCIDENT_TYPE_LABEL[v] ?? v }

// ─── Incident status (khớp _STATUS_* trong services/imm12.py) ──────────────────
export const INCIDENT_STATUS_LABEL: Record<string, string> = {
  'Open':         'Mới mở',
  'Acknowledged': 'Đã tiếp nhận',
  'In Progress':  'Đang điều tra',
  'RCA Required': 'Cần phân tích nguyên nhân gốc',
  'Resolved':     'Đã giải quyết',
  'Closed':       'Đã đóng',
  'Cancelled':    'Đã hủy',
}
export const INCIDENT_STATUS_CLASS: Record<string, string> = {
  'Open':         'bg-blue-100 text-blue-700',
  'Acknowledged': 'bg-blue-100 text-blue-800',
  'In Progress':  'bg-yellow-100 text-yellow-800',
  'RCA Required': 'bg-orange-100 text-orange-800',
  'Resolved':     'bg-purple-100 text-purple-700',
  'Closed':       'bg-green-100 text-green-700',
  'Cancelled':    'bg-slate-100 text-slate-500',
}
export function incidentStatusLabel(v: string) { return INCIDENT_STATUS_LABEL[v] ?? v }
export function incidentStatusClass(v: string) { return INCIDENT_STATUS_CLASS[v] ?? 'bg-slate-100 text-slate-600' }

// SSoT nhãn filter ảo "incident đang mở" (open=1, SoT BE open_incident_filter:
// status IN Open/Acknowledged/In Progress/RCA Required). KHÔNG hardcode literal
// 'Đang mở' rải rác — chip drill-down + dashboard cùng dùng nhãn này.
export const INCIDENT_OPEN_FILTER_LABEL = 'Đang mở'

// ─── RCA status (khớp _RCA_* trong services/imm12.py) ─────────────────────────
export const RCA_STATUS_LABEL: Record<string, string> = {
  'RCA Required':    'Cần phân tích',
  'RCA In Progress': 'Đang phân tích',
  'Completed':       'Đã hoàn tất',
  'Cancelled':       'Đã hủy',
}
export const RCA_STATUS_CLASS: Record<string, string> = {
  'RCA Required':    'bg-red-100 text-red-700',
  'RCA In Progress': 'bg-yellow-100 text-yellow-800',
  'Completed':       'bg-green-100 text-green-700',
  'Cancelled':       'bg-slate-100 text-slate-500',
}
export function rcaStatusLabel(v: string) { return RCA_STATUS_LABEL[v] ?? v }
export function rcaStatusClass(v: string) { return RCA_STATUS_CLASS[v] ?? 'bg-slate-100 text-slate-600' }

// RCA trigger_type (BE: "Major Incident"/"Critical Incident"/"Chronic Failure"/"Manual")
export const RCA_TRIGGER_LABEL: Record<string, string> = {
  'Critical Incident': 'Sự cố nghiêm trọng',
  'Major Incident':    'Sự cố mức cao',
  'Chronic Failure':   'Lỗi lặp lại (mãn tính)',
  'Manual':            'Thủ công',
}
export function rcaTriggerLabel(v: string) { return RCA_TRIGGER_LABEL[v] ?? v }

// ─── CAPA status ──────────────────────────────────────────────────────────────
export const CAPA_STATUS_LABEL: Record<string, string> = {
  'Open':                'Đang mở',
  'In Progress':         'Đang xử lý',
  'Pending Verification':'Chờ xác minh',
  'Closed':              'Đã đóng',
  'Overdue':             'Quá hạn',
}
export const CAPA_STATUS_CLASS: Record<string, string> = {
  'Open':                'bg-blue-100 text-blue-800',
  'In Progress':         'bg-indigo-100 text-indigo-800',
  'Pending Verification':'bg-yellow-100 text-yellow-800',
  'Closed':              'bg-green-100 text-green-800',
  'Overdue':             'bg-red-100 text-red-800',
}
export function capaStatusLabel(v: string) { return CAPA_STATUS_LABEL[v] ?? v }
export function capaStatusClass(v: string) { return CAPA_STATUS_CLASS[v] ?? 'bg-gray-100 text-gray-600' }

// ─── CAPA workflow_state (máy trạng thái — khớp CapaWorkflowState api/imm16.ts +
//     _CAPA_TRANSITIONS services/imm16.py). Khác CAPA_STATUS_LABEL (chỉ phủ
//     status tổng hợp). Dùng cho confirm-modal + stepper trên CAPADetailView. ──
export const CAPA_WORKFLOW_LABEL: Record<string, string> = {
  'Open':           'Đang mở',
  'Investigating':  'Đang điều tra',
  'Action Plan':    'Lập kế hoạch hành động',
  'Implementation': 'Đang thực thi',
  'Verification':   'Đang xác minh',
  'Closed':         'Đã đóng',
  'Re-opened':      'Mở lại',
}
export function capaWorkflowLabel(v: string) { return CAPA_WORKFLOW_LABEL[v] ?? v }

// ─── Transfer type ────────────────────────────────────────────────────────────
export const TRANSFER_TYPE_LABEL: Record<string, string> = {
  'Internal': 'Điều chuyển nội bộ',
  'Loan':     'Cho mượn',
  'External': 'Điều chuyển ngoài',
  'Return':   'Hoàn trả',
}
export function transferTypeLabel(v: string) { return TRANSFER_TYPE_LABEL[v] ?? v }

// ─── Service contract type ────────────────────────────────────────────────────
export const CONTRACT_TYPE_LABEL: Record<string, string> = {
  'Preventive Maintenance': 'Bảo trì định kỳ',
  'Calibration':            'Hiệu chuẩn',
  'Repair':                 'Sửa chữa',
  'Full Service':           'Toàn diện',
  'Warranty Extension':     'Gia hạn bảo hành',
}
export function contractTypeLabel(v: string) { return CONTRACT_TYPE_LABEL[v] ?? v }

// ─── CM Work Order ────────────────────────────────────────────────────────────
export const CM_STATUS_LABEL: Record<string, string> = {
  'Open':               'Tiếp nhận',
  'Assigned':           'Đã phân công',
  'Diagnosing':         'Đang chẩn đoán',
  'Pending Parts':      'Chờ vật tư',
  'In Repair':          'Đang sửa chữa',
  'Pending Inspection': 'Chờ nghiệm thu',
  'Completed':          'Hoàn thành',
  'Cannot Repair':      'Không thể sửa',
  'Cancelled':          'Đã hủy',
}

export const CM_STATUS_CLASS: Record<string, string> = {
  'Open':               'bg-blue-100 text-blue-800',
  'Assigned':           'bg-indigo-100 text-indigo-800',
  'Diagnosing':         'bg-violet-100 text-violet-800',
  'Pending Parts':      'bg-orange-100 text-orange-800',
  'In Repair':          'bg-purple-100 text-purple-800',
  'Pending Inspection': 'bg-cyan-100 text-cyan-800',
  'Completed':          'bg-green-100 text-green-800',
  'Cannot Repair':      'bg-red-200 text-red-900 font-semibold',
  'Cancelled':          'bg-gray-100 text-gray-500',
}

// ─── PM Work Order ────────────────────────────────────────────────────────────
export const PM_STATUS_LABEL: Record<string, string> = {
  'Open':                'Mở',
  'In Progress':         'Đang thực hiện',
  'Overdue':             'Quá hạn',
  'Completed':           'Hoàn thành',
  'Halted–Major Failure':'Dừng — Lỗi nặng',
  'Pending–Device Busy': 'Chờ — Thiết bị bận',
  'Cancelled':           'Đã hủy',
}

export const PM_STATUS_CLASS: Record<string, string> = {
  'Open':                'bg-blue-100 text-blue-800',
  'In Progress':         'bg-indigo-100 text-indigo-800',
  'Overdue':             'bg-red-100 text-red-800',
  'Completed':           'bg-green-100 text-green-800',
  'Halted–Major Failure':'bg-red-200 text-red-900 font-semibold',
  'Pending–Device Busy': 'bg-orange-100 text-orange-800',
  'Cancelled':           'bg-gray-100 text-gray-500',
}

// ─── Priority ─────────────────────────────────────────────────────────────────
export const PRIORITY_LABEL: Record<string, string> = {
  'Emergency': 'Khẩn cấp',
  'Urgent':    'Gấp',
  'High':      'Cao',
  'Medium':    'Trung bình',
  'Low':       'Thấp',
  'Routine':   'Định kỳ',
  'Normal':    'Bình thường',
}

export const PRIORITY_CLASS: Record<string, string> = {
  'Emergency': 'bg-red-100 text-red-800 font-semibold',
  'Urgent':    'bg-orange-100 text-orange-800 font-medium',
  'High':      'bg-amber-100 text-amber-800',
  'Medium':    'bg-yellow-100 text-yellow-800',
  'Low':       'bg-gray-100 text-gray-600',
  'Routine':   'bg-green-100 text-green-700',
  'Normal':    'bg-gray-100 text-gray-600',
}

// ─── Checklist Results ────────────────────────────────────────────────────────
export const RESULT_LABEL: Record<string, string> = {
  'Pass':       'Đạt',
  'Fail':       'Không đạt',
  'Fail–Minor': 'Không đạt — Nhẹ',
  'Fail–Major': 'Không đạt — Nặng',
  'N/A':        'Không áp dụng',
}

export const RESULT_CLASS: Record<string, string> = {
  'Pass':       'bg-green-100 text-green-800',
  'Fail':       'bg-red-100 text-red-800',
  'Fail–Minor': 'bg-yellow-100 text-yellow-800',
  'Fail–Major': 'bg-red-200 text-red-900 font-semibold',
  'N/A':        'bg-gray-100 text-gray-500',
}

// ─── Repair Type ──────────────────────────────────────────────────────────────
export const REPAIR_TYPE_LABEL: Record<string, string> = {
  'Corrective':  'Sửa chữa khắc phục',
  'Preventive':  'Phòng ngừa',
  'Emergency':   'Sửa chữa khẩn cấp',
  'Breakdown':   'Hỏng hóc',
  'DOA':         'Hỏng khi nhận',
}

// ─── Root Cause ───────────────────────────────────────────────────────────────
export const ROOT_CAUSE_LABEL: Record<string, string> = {
  'Mechanical':  'Cơ học',
  'Electrical':  'Điện',
  'Software':    'Phần mềm',
  'User Error':  'Lỗi người dùng',
  'Wear and Tear': 'Hao mòn',
  'Unknown':     'Chưa xác định',
  'Other':       'Khác',
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
export function cmStatusLabel(v: string)  { return CM_STATUS_LABEL[v]  ?? v }
export function cmStatusClass(v: string)  { return CM_STATUS_CLASS[v]  ?? 'bg-gray-100 text-gray-600' }
export function pmStatusLabel(v: string)  { return PM_STATUS_LABEL[v]  ?? v }
export function pmStatusClass(v: string)  { return PM_STATUS_CLASS[v]  ?? 'bg-gray-100 text-gray-600' }
export function priorityLabel(v: string)  { return PRIORITY_LABEL[v]   ?? v }
export function priorityClass(v: string)  { return PRIORITY_CLASS[v]   ?? 'bg-gray-100 text-gray-600' }
export function resultLabel(v: string)    { return RESULT_LABEL[v]     ?? v }
export function resultClass(v: string)    { return RESULT_CLASS[v]     ?? 'bg-gray-100 text-gray-600' }
export function repairTypeLabel(v: string){ return REPAIR_TYPE_LABEL[v]?? v }
export function rootCauseLabel(v: string) { return ROOT_CAUSE_LABEL[v] ?? v }

// ═══ Enum hiển thị thô → nhãn VI (wiring binding; value gốc giữ nguyên) ═══════
// Kết quả tổng thể PM / hiệu chuẩn / đánh giá — gộp mọi biến thể value BE phát.
export const OVERALL_RESULT_LABEL: Record<string, string> = {
  'Pass': 'Đạt',
  'Passed': 'Đạt',
  'Pass with Minor Issues': 'Đạt (lỗi nhỏ)',
  'Conditional': 'Có điều kiện',
  'Conditionally Passed': 'Đạt có điều kiện',
  'Fail': 'Không đạt',
  'Failed': 'Không đạt',
}
export function overallResultLabel(v?: string | null) { return v ? (OVERALL_RESULT_LABEL[v] ?? v) : '—' }

// Loại PM (pm_schedule / pm_work_order.pm_type).
export const PM_TYPE_LABEL: Record<string, string> = {
  'Quarterly': 'Hàng quý',
  'Semi-Annual': 'Nửa năm',
  'Annual': 'Hàng năm',
  'Ad-hoc': 'Đột xuất',
}
export function pmTypeLabel(v?: string | null) { return v ? (PM_TYPE_LABEL[v] ?? v) : '—' }

// Loại lệnh công việc PM (pm_work_order.wo_type).
export const WO_TYPE_LABEL: Record<string, string> = {
  'Preventive': 'Bảo trì định kỳ',
  'Corrective': 'Sửa chữa',
}
export function woTypeLabel(v?: string | null) { return v ? (WO_TYPE_LABEL[v] ?? v) : '—' }

// Hình thức hiệu chuẩn (imm_asset_calibration.calibration_type).
export const CALIBRATION_TYPE_LABEL: Record<string, string> = {
  'External': 'Bên ngoài',
  'In-House': 'Nội bộ',
}
export function calibrationTypeLabel(v?: string | null) { return v ? (CALIBRATION_TYPE_LABEL[v] ?? v) : '—' }

// Trạng thái AVL nhà cung cấp (imm_avl_status).
export const AVL_STATUS_LABEL: Record<string, string> = {
  'Approved': 'Đã duyệt',
  'Conditional': 'Có điều kiện',
  'Suspended': 'Tạm đình chỉ',
  'Expired': 'Hết hạn',
  'Not Applicable': 'Không áp dụng',
}
export function avlStatusLabel(v?: string | null) { return v ? (AVL_STATUS_LABEL[v] ?? v) : '—' }

// Loại bản ghi nguồn phiếu điều chuyển kho (ac_stock_movement.reference_type = tên doctype).
export const STOCK_REFERENCE_TYPE_LABEL: Record<string, string> = {
  'Asset Repair': 'Phiếu sửa chữa',
  'PM Work Order': 'Lệnh bảo trì',
  'AC Purchase': 'Đơn mua hàng',
  'Manual': 'Thủ công',
}
export function stockReferenceTypeLabel(v?: string | null) { return v ? (STOCK_REFERENCE_TYPE_LABEL[v] ?? v) : '—' }

// Loại không phù hợp QA (asset_qa_non_conformance.nc_type) — KHÁC NC_TYPE_LABELS (IMM-04).
export const QA_NC_TYPE_LABEL: Record<string, string> = {
  'DOA': 'Hỏng khi nhận',
  'Missing': 'Thiếu hàng',
  'Crash': 'Hư hỏng vật lý',
  'Technical': 'Lỗi kỹ thuật',
  'Documentation': 'Thiếu hồ sơ',
  'Other': 'Khác',
}
export function qaNcTypeLabel(v?: string | null) { return v ? (QA_NC_TYPE_LABEL[v] ?? v) : '—' }

// ─── Generic helpers (must stay after all maps) ───────────────────────────────
export function formatStatus(v: string | undefined | null): string {
  if (!v) return '—'
  const maps = [
    CM_STATUS_LABEL, PM_STATUS_LABEL, PRIORITY_LABEL, RESULT_LABEL,
    REPAIR_TYPE_LABEL, ROOT_CAUSE_LABEL,
    LIFECYCLE_STATUS_LABEL, CALIBRATION_STATUS_LABEL,
    INCIDENT_SEVERITY_LABEL, CAPA_STATUS_LABEL,
    TRANSFER_TYPE_LABEL, CONTRACT_TYPE_LABEL, MEDICAL_DEVICE_CLASS_LABEL,
    // R24: phủ thêm các state máy chưa có trong formatStatus (chống raw "Open"
    // leak ở RecordHistory dùng chung).
    INCIDENT_STATUS_LABEL, RCA_STATUS_LABEL, CAPA_WORKFLOW_LABEL,
    COMMISSIONING_STATE_LABELS, DOC_STATUS_LABELS, WO_STATUS_LABELS,
  ]
  for (const map of maps) {
    if (v in map) return map[v]
  }
  // Fallback: bỏ gạch dưới (Pending_Doc_Verify -> Pending Doc Verify) thay vì
  // trả nguyên văn raw code.
  return v.replaceAll('_', ' ')
}

// ─── R24: doctype-aware label resolver cho audit-trail/history dùng chung ─────
// RecordHistory hiển thị from_status → to_status cho NHIỀU doctype. Map theo
// ref_doctype để chọn đúng từ điển; fallback formatStatus() rồi raw-debar.
const _HISTORY_STATE_MAP: Record<string, Record<string, string>> = {
  'Incident Report':       INCIDENT_STATUS_LABEL,
  'IMM RCA Record':        RCA_STATUS_LABEL,
  'IMM CAPA Record':       CAPA_WORKFLOW_LABEL,
  'Asset Commissioning':   COMMISSIONING_STATE_LABELS,
  'PM Work Order':         PM_STATUS_LABEL,
  'Asset Repair':          CM_STATUS_LABEL,
  'IMM Asset Calibration': CALIBRATION_STATUS_LABELS,
}
export function historyStateLabel(refDoctype: string | undefined | null, v?: string | null): string {
  if (!v) return '—'
  const map = refDoctype ? _HISTORY_STATE_MAP[refDoctype] : undefined
  if (map && v in map) return map[v]
  return formatStatus(v)
}

export function formatStatusClass(v: string | undefined | null): string {
  if (!v) return 'bg-gray-100 text-gray-500'
  const classMaps: Array<Record<string, string>> = [
    CM_STATUS_CLASS, PM_STATUS_CLASS, PRIORITY_CLASS, RESULT_CLASS,
    LIFECYCLE_STATUS_CLASS, CALIBRATION_STATUS_CLASS, INCIDENT_SEVERITY_CLASS,
    CAPA_STATUS_CLASS,
  ]
  for (const map of classMaps) {
    if (v in map) return map[v]
  }
  return 'bg-gray-100 text-gray-600'
}

// ─── IMM-14 · Giải nhiệm thiết bị (Asset Decommission) — SSoT nhãn hiển thị ───
// Chỉ ĐỔI LỚP HIỂN THỊ; VALUE gửi BE (disposal_method / workflow_state) GIỮ NGUYÊN
// (LL-FE-52/53 — display layer only). disposal_method: dịch phần EN lẫn trong enum
// DocType (Donation/Trade-in) sang tiếng Việt, GIỮ phần đã VN (Huỷ, Lưu trữ).
export const DISPOSAL_METHOD_LABEL: Record<string, string> = {
  'Huỷ': 'Huỷ',
  'Điều chuyển/Donation': 'Điều chuyển/Hiến tặng',
  'Bán/Trade-in': 'Bán/Thu cũ đổi mới',
  'Lưu trữ': 'Lưu trữ',
}
export function disposalMethodLabel(v?: string | null): string {
  if (!v) return '—'
  return DISPOSAL_METHOD_LABEL[v] ?? v
}

// Trạng thái hồ sơ giải nhiệm — nhãn domain-specific (KHÁC translateStatus toàn
// cục: Draft = "Chờ duyệt" chứ không "Bản nháp"; Approved = "Đã giải nhiệm" vì hồ
// sơ duyệt xong nghĩa là thiết bị đã giải nhiệm). Value giữ Draft/Approved/Cancelled.
export const DECOMMISSION_STATE_LABEL: Record<string, string> = {
  Draft: 'Chờ duyệt',
  Approved: 'Đã giải nhiệm',
  Cancelled: 'Đã hủy',
}
export const DECOMMISSION_STATE_CLASS: Record<string, string> = {
  Draft: 'bg-amber-100 text-amber-700',
  Approved: 'bg-gray-200 text-gray-600',
  Cancelled: 'bg-red-100 text-red-700',
}
export function decommissionStateLabel(v?: string | null): string {
  if (!v) return '—'
  return DECOMMISSION_STATE_LABEL[v] ?? v
}
export function decommissionStateClass(v?: string | null): string {
  if (!v) return 'bg-gray-100 text-gray-500'
  return DECOMMISSION_STATE_CLASS[v] ?? 'bg-gray-100 text-gray-600'
}
