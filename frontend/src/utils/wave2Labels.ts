// Copyright (c) 2026, AssetCore Team
// Bản dịch tiếng Việt cho các nhãn dùng chung của Khối 1 (Hoạch định & Mua sắm).
// FE chỉ hiển thị tiếng Việt; BE / DocType vẫn lưu giá trị enum gốc.

// ─── Trạng thái quy trình (workflow state) ────────────────────────────────────

const STATE_LABELS: Record<string, string> = {
  // Đề xuất nhu cầu
  'Draft':            'Nháp',
  'Submitted':        'Đã gửi',
  'Reviewing':        'Đang rà soát',
  'Prioritized':      'Đã chấm ưu tiên',
  'Budgeted':         'Đã lập dự toán',
  'Pending Approval': 'Chờ phê duyệt',
  'Approved':         'Đã duyệt',
  'Rejected':         'Đã bác',
  // Kế hoạch mua sắm
  'Active':           'Đang hiệu lực',
  'Closed':           'Đã đóng',
  // Hồ sơ kỹ thuật
  'Benchmarked':      'Đã so sánh thị trường',
  'Risk Assessed':    'Đã đánh giá rủi ro',
  'Locked':           'Đã chốt',
  'Withdrawn':        'Đã rút',
  // Đánh giá nhà cung cấp
  'Open RFQ':            'Đang yêu cầu báo giá',
  'Quotation Received':  'Đã nhận báo giá',
  'Evaluated':           'Đã đánh giá',
  'Cancelled':           'Đã hủy',
  // Quyết định mua sắm
  'Method Selected':   'Đã chọn phương án',
  'Negotiation':       'Đang thương thảo',
  'Award Recommended': 'Đề xuất trúng thầu',
  'Awarded':           'Đã trao thầu',
  'Contract Signed':   'Đã ký hợp đồng',
  'PO Issued':         'Đã phát hành đơn hàng',
  // Danh mục nhà cung cấp duyệt
  'Conditional': 'Có điều kiện',
  'Suspended':   'Tạm đình chỉ',
  'Expired':     'Hết hạn',
}

export function stateLabel(state?: string): string {
  if (!state) return ''
  return STATE_LABELS[state] || state
}

// CSS slug — lowercase, không dấu, gạch ngang
export function stateSlug(state?: string): string {
  return (state || '').toLowerCase().replaceAll(/\s+/g, '-')
}

// ─── Loại đề xuất nhu cầu ────────────────────────────────────────────────────

export function requestTypeLabel(t?: string): string {
  return ({
    'New':         'Mua mới',
    'Replacement': 'Thay thế',
    'Upgrade':     'Nâng cấp',
    'Add-on':      'Bổ sung',
  } as Record<string, string>)[t || ''] || (t || '')
}

// ─── Mức ưu tiên ──────────────────────────────────────────────────────────────

export function priorityLabel(p?: string): string {
  return ({
    'P1': 'Rất cao (P1)',
    'P2': 'Cao (P2)',
    'P3': 'Trung bình (P3)',
    'P4': 'Thấp (P4)',
  } as Record<string, string>)[p || ''] || (p || '')
}

// Chỉ ký hiệu ngắn dùng trong badge
export function priorityBadge(p?: string): string {
  return ({
    'P1': 'Rất cao',
    'P2': 'Cao',
    'P3': 'Trung bình',
    'P4': 'Thấp',
  } as Record<string, string>)[p || ''] || (p || '')
}

// ─── Tiêu chí chấm điểm (Needs Request) ───────────────────────────────────────

export function criterionLabel(c?: string): string {
  return ({
    'clinical_impact':    'Tác động lâm sàng',
    'risk':               'Mức độ rủi ro',
    'utilization_gap':    'Mức độ sử dụng',
    'replacement_signal': 'Tín hiệu cần thay thế',
    'compliance_gap':     'Khoảng trống tuân thủ',
    'budget_fit':         'Mức phù hợp ngân sách',
  } as Record<string, string>)[c || ''] || (c || '')
}

// ─── Nhóm yêu cầu kỹ thuật ────────────────────────────────────────────────────

export function requirementGroupLabel(g?: string): string {
  return ({
    'Performance':  'Hiệu năng',
    'Safety':       'An toàn',
    'Connectivity': 'Kết nối',
    'Power':        'Nguồn điện',
    'Mechanical':   'Cơ khí',
    'Software':     'Phần mềm',
    'Service':      'Dịch vụ – bảo hành',
    'Compliance':   'Tuân thủ',
  } as Record<string, string>)[g || ''] || (g || '')
}

// ─── Hạng mục tương thích hạ tầng ─────────────────────────────────────────────

export function infraDomainLabel(d?: string): string {
  return ({
    'Electrical':   'Hệ thống điện',
    'Medical Gas':  'Khí y tế',
    'Network/IT':   'Mạng & CNTT',
    'HIS-PACS-LIS': 'HIS / PACS / LIS',
    'HVAC':         'Điều hòa thông gió',
    'Space-Layout': 'Không gian – mặt bằng',
  } as Record<string, string>)[d || ''] || (d || '')
}

export function infraStatusLabel(s?: string): string {
  return ({
    'Compatible':         'Tương thích',
    'Need Upgrade':       'Cần nâng cấp',
    'Need Major Upgrade': 'Cần cải tạo lớn',
    'N/A':                'Không áp dụng',
    'All Compatible':     'Tương thích toàn bộ',
    'Partial':            'Tương thích một phần',
  } as Record<string, string>)[s || ''] || (s || '')
}

// ─── Chiều phụ thuộc nhà cung cấp (lock-in) ──────────────────────────────────

export function lockInDimensionLabel(d?: string): string {
  return ({
    'Protocol Standard': 'Chuẩn giao thức',
    'Consumable Source': 'Nguồn vật tư tiêu hao',
    'Software License':  'Giấy phép phần mềm',
    'Parts Source':      'Nguồn linh kiện',
    'Service Tooling':   'Công cụ kỹ thuật',
  } as Record<string, string>)[d || ''] || (d || '')
}

// ─── Trạng thái dòng kế hoạch mua sắm ────────────────────────────────────────

export function planLineStatusLabel(s?: string): string {
  return ({
    'Pending Spec':   'Chờ lập hồ sơ kỹ thuật',
    'In Spec':        'Đang lập hồ sơ kỹ thuật',
    'In Procurement': 'Đang mua sắm',
    'Awarded':        'Đã trao thầu',
    'Cancelled':      'Đã hủy',
  } as Record<string, string>)[s || ''] || (s || '')
}

// ─── Tiền tệ + ngày tháng tiếng Việt ──────────────────────────────────────────

export function formatVnd(v?: number | null): string {
  if (v == null) return '—'
  return new Intl.NumberFormat('vi-VN', {
    style: 'currency', currency: 'VND', maximumFractionDigits: 0,
  }).format(v)
}

export function formatVnDate(d?: string | null): string {
  if (!d) return '—'
  try { return new Date(d).toLocaleDateString('vi-VN') } catch { return d }
}
