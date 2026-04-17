/** Bảng nhãn tiếng Việt cho các giá trị lưu trong DB (tiếng Anh) */

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
