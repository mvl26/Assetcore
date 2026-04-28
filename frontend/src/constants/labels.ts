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
  Pending_Review: 'Chờ duyệt',
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
  'Commissioned':    'Đã tiếp nhận',
  'Active':          'Đang hoạt động',
  'Under Repair':    'Đang sửa chữa',
  'Calibrating':     'Đang hiệu chuẩn',
  'Out of Service':  'Ngừng hoạt động',
  'Decommissioned':  'Đã thanh lý',
}
export const LIFECYCLE_STATUS_CLASS: Record<string, string> = {
  'Commissioned':    'bg-indigo-100 text-indigo-800',
  'Active':          'bg-green-100 text-green-800',
  'Under Repair':    'bg-orange-100 text-orange-800',
  'Calibrating':     'bg-cyan-100 text-cyan-800',
  'Out of Service':  'bg-red-100 text-red-800',
  'Decommissioned':  'bg-gray-200 text-gray-500',
}
export function lifecycleStatusLabel(v: string) { return LIFECYCLE_STATUS_LABEL[v] ?? v }
export function lifecycleStatusClass(v: string) { return LIFECYCLE_STATUS_CLASS[v] ?? 'bg-gray-100 text-gray-600' }

// ─── Calibration status ───────────────────────────────────────────────────────
export const CALIBRATION_STATUS_LABEL: Record<string, string> = {
  'Calibrated':      'Đã hiệu chuẩn',
  'Due Soon':        'Sắp đến hạn',
  'Overdue':         'Quá hạn',
  'Not Required':    'Không yêu cầu',
  'In Progress':     'Đang hiệu chuẩn',
  'Failed':          'Không đạt',
}
export const CALIBRATION_STATUS_CLASS: Record<string, string> = {
  'Calibrated':      'bg-green-100 text-green-800',
  'Due Soon':        'bg-yellow-100 text-yellow-800',
  'Overdue':         'bg-red-100 text-red-800',
  'Not Required':    'bg-gray-100 text-gray-500',
  'In Progress':     'bg-blue-100 text-blue-800',
  'Failed':          'bg-red-200 text-red-900 font-semibold',
}
export function calibrationStatusLabel(v: string) { return CALIBRATION_STATUS_LABEL[v] ?? v }
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
  'DOA':         'Hỏng khi nhận (DOA)',
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

// ─── Generic helpers (must stay after all maps) ───────────────────────────────
export function formatStatus(v: string | undefined | null): string {
  if (!v) return '—'
  const maps = [
    CM_STATUS_LABEL, PM_STATUS_LABEL, PRIORITY_LABEL, RESULT_LABEL,
    REPAIR_TYPE_LABEL, ROOT_CAUSE_LABEL,
    LIFECYCLE_STATUS_LABEL, CALIBRATION_STATUS_LABEL,
    INCIDENT_SEVERITY_LABEL, CAPA_STATUS_LABEL,
    TRANSFER_TYPE_LABEL, CONTRACT_TYPE_LABEL, MEDICAL_DEVICE_CLASS_LABEL,
  ]
  for (const map of maps) {
    if (v in map) return map[v]
  }
  return v
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
