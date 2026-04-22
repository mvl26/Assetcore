// Copyright (c) 2026, AssetCore Team
// Bộ công cụ format dữ liệu dùng chung — dùng ở MỌI component cần hiển thị
// tên thiết bị, trạng thái, hoặc badge màu.
//
// Cách dùng tiêu chuẩn trong template:
//   <div class="font-medium text-gray-900">{{ formatAssetDisplay(item.asset_name, item.asset).main }}</div>
//   <div class="text-xs text-gray-500 font-mono">{{ formatAssetDisplay(item.asset_name, item.asset).sub }}</div>
//
//   <span :class="['px-2 py-0.5 rounded-full text-xs font-medium', getStatusColor(item.status)]">
//     {{ translateStatus(item.status) }}
//   </span>

// ─── Asset display ──────────────────────────────────────────────────────────

export interface AssetDisplay {
  main: string   // dòng chính (tên)
  sub: string    // dòng phụ (mã)
  hasBoth: boolean
}

/** "Tên chính — Mã phụ". Nếu không có tên → main = id, sub = ''. */
export function formatAssetDisplay(
  assetName?: string | null,
  assetId?: string | null,
): AssetDisplay {
  const name = (assetName || '').trim()
  const id   = (assetId   || '').trim()
  if (name && id && name !== id) return { main: name, sub: id,  hasBoth: true }
  if (name) return { main: name, sub: '', hasBoth: false }
  return { main: id || '—', sub: '', hasBoth: false }
}

/** Chuỗi gộp 1 dòng — hữu ích cho title/tooltip. */
export function assetLabel(assetName?: string | null, assetId?: string | null): string {
  const d = formatAssetDisplay(assetName, assetId)
  return d.hasBoth ? `${d.main} (${d.sub})` : d.main
}

// ─── Status translation ─────────────────────────────────────────────────────
// Map tổng hợp cho mọi status xuất hiện ở Frappe: cả docstatus (Draft/Submitted/Cancelled)
// lẫn status field của các doctype (PM/CM/Commissioning/Calibration/...).

const STATUS_MAP: Record<string, string> = {
  // ── Docstatus & workflow chung ─────────────────────────────────────
  Draft:     'Bản nháp',
  Pending:   'Chờ xử lý',
  Submitted: 'Đã duyệt',
  Cancelled: 'Đã hủy',
  Approved:  'Đã phê duyệt',
  Rejected:  'Bị từ chối',
  Closed:    'Đã đóng',
  Open:      'Đang mở',

  // ── Work Order / Repair ───────────────────────────────────────────
  'In Progress':         'Đang thực hiện',
  In_Progress:           'Đang thực hiện',
  Completed:             'Hoàn thành',
  Assigned:              'Đã phân công',
  Diagnosing:            'Đang chẩn đoán',
  'Pending Parts':       'Chờ linh kiện',
  Pending_Parts:         'Chờ linh kiện',
  'In Repair':           'Đang sửa chữa',
  In_Repair:             'Đang sửa chữa',
  'Pending Inspection':  'Chờ nghiệm thu',
  Pending_Inspection:    'Chờ nghiệm thu',
  'Cannot Repair':       'Không thể sửa',
  Cannot_Repair:         'Không thể sửa',
  Overdue:               'Quá hạn',
  Scheduled:             'Đã lên lịch',
  'Pending–Device Busy': 'Tạm dừng — thiết bị đang dùng',
  'Halted–Major Failure':'Tạm dừng — lỗi nghiêm trọng',

  // ── Asset lifecycle ────────────────────────────────────────────────
  Active:             'Đang hoạt động',
  'Under Repair':     'Đang sửa chữa',
  'Under Maintenance':'Đang bảo trì',
  Calibrating:        'Đang hiệu chuẩn',
  'Out of Service':   'Ngừng hoạt động',
  Commissioned:       'Mới tiếp nhận',
  Decommissioned:     'Đã thanh lý',

  // ── Commissioning (IMM-04) ────────────────────────────────────────
  'Pending Doc Verify':  'Chờ kiểm tra hồ sơ',
  'To Be Installed':     'Chờ lắp đặt',
  Installing:            'Đang lắp đặt',
  Identification:        'Nhận dạng',
  'Initial Inspection':  'Kiểm tra ban đầu',
  'Clinical Hold':       'Tạm giữ lâm sàng',
  'Re Inspection':       'Kiểm tra lại',
  'Clinical Release':    'Phát hành lâm sàng',
  'Return To Vendor':    'Trả nhà cung cấp',
  'Non Conformance':     'Không phù hợp',

  // ── Calibration ───────────────────────────────────────────────────
  'Sent to Lab':         'Đã gửi phòng hiệu chuẩn',
  Sent_to_Lab:           'Đã gửi phòng hiệu chuẩn',
  'Certificate Received':'Đã nhận chứng nhận',
  Certificate_Received:  'Đã nhận chứng nhận',
  Passed:                'Đạt',
  Failed:                'Không đạt',
  'Conditionally Passed':'Đạt có điều kiện',

  // ── Document (IMM-05) ─────────────────────────────────────────────
  Expired:         'Hết hạn',
  Expiring_Soon:   'Sắp hết hạn',
  'Expiring Soon': 'Sắp hết hạn',
  Archived:        'Lưu trữ',
  Exempt:          'Miễn đăng ký',
  Pending_Review:  'Chờ duyệt',
  Pending_Approval:'Chờ phê duyệt',
  'Pending Approval':'Chờ phê duyệt',

  // ── Transfer / Receipt ────────────────────────────────────────────
  Received:  'Đã tiếp nhận',

  // ── Priority / Severity ───────────────────────────────────────────
  Low:       'Thấp',
  Medium:    'Trung bình',
  Normal:    'Bình thường',
  High:      'Cao',
  Urgent:    'Khẩn',
  Critical:  'Khẩn cấp',
  Emergency: 'Cấp cứu',
  Minor:     'Nhỏ',
  Major:     'Nghiêm trọng',
}

/** Trả nhãn Tiếng Việt cho 1 status. Fallback: bỏ dấu gạch dưới. */
export function translateStatus(status?: string | null): string {
  if (!status) return '—'
  return STATUS_MAP[status] ?? status.replaceAll('_', ' ')
}

/** Dịch docstatus số → Tiếng Việt. */
export function translateDocstatus(docstatus: 0 | 1 | 2): string {
  return docstatus === 1 ? 'Đã duyệt' : docstatus === 2 ? 'Đã hủy' : 'Bản nháp'
}

// ─── Status color (Tailwind classes) ────────────────────────────────────────
// Key rule:
//   🟢 xanh lá  — ổn / hoàn thành / đạt
//   🔵 xanh dương— đang xử lý / tiến triển
//   🟡 vàng     — chờ / cảnh báo nhẹ
//   🟠 cam      — cảnh báo / ưu tiên cao
//   🔴 đỏ       — lỗi / quá hạn / huỷ
//   ⚪ xám      — mặc định / nháp

const COLOR_GREEN  = 'bg-emerald-100 text-emerald-800 border border-emerald-200'
const COLOR_BLUE   = 'bg-blue-100 text-blue-800 border border-blue-200'
const COLOR_YELLOW = 'bg-yellow-100 text-yellow-800 border border-yellow-200'
const COLOR_ORANGE = 'bg-orange-100 text-orange-800 border border-orange-200'
const COLOR_RED    = 'bg-red-100 text-red-700 border border-red-200'
const COLOR_PURPLE = 'bg-purple-100 text-purple-700 border border-purple-200'
const COLOR_GRAY   = 'bg-slate-100 text-slate-600 border border-slate-200'

const STATUS_COLOR: Record<string, string> = {
  // xanh lá — hoàn thành / đạt
  Submitted: COLOR_GREEN,  Approved: COLOR_GREEN,     Completed: COLOR_GREEN,
  Active: COLOR_GREEN,     Passed: COLOR_GREEN,       'Clinical Release': COLOR_GREEN,
  Received: COLOR_GREEN,   'Certificate Received': COLOR_GREEN,
  // xanh dương — đang xử lý
  'In Progress': COLOR_BLUE, In_Progress: COLOR_BLUE, Diagnosing: COLOR_BLUE,
  'In Repair': COLOR_BLUE,  In_Repair: COLOR_BLUE,    Installing: COLOR_BLUE,
  Commissioned: COLOR_BLUE, 'Initial Inspection': COLOR_BLUE, 'Sent to Lab': COLOR_BLUE,
  Assigned: COLOR_BLUE,
  // vàng — chờ
  Pending: COLOR_YELLOW,   'Pending Approval': COLOR_YELLOW,
  Pending_Approval: COLOR_YELLOW, Pending_Review: COLOR_YELLOW,
  'Pending Doc Verify': COLOR_YELLOW, 'Pending Inspection': COLOR_YELLOW,
  Pending_Inspection: COLOR_YELLOW, 'Pending Parts': COLOR_YELLOW, Pending_Parts: COLOR_YELLOW,
  Scheduled: COLOR_YELLOW, 'Expiring Soon': COLOR_YELLOW, Expiring_Soon: COLOR_YELLOW,
  Open: COLOR_YELLOW,
  // cam — cảnh báo
  'Under Maintenance': COLOR_ORANGE, 'Clinical Hold': COLOR_ORANGE,
  'Re Inspection': COLOR_ORANGE, 'Conditionally Passed': COLOR_ORANGE,
  // đỏ — lỗi / hủy / quá hạn
  Cancelled: COLOR_RED, Rejected: COLOR_RED, Failed: COLOR_RED,
  Overdue: COLOR_RED, Expired: COLOR_RED, 'Out of Service': COLOR_RED,
  'Under Repair': COLOR_RED, 'Cannot Repair': COLOR_RED, Cannot_Repair: COLOR_RED,
  'Halted–Major Failure': COLOR_RED, 'Pending–Device Busy': COLOR_ORANGE,
  'Non Conformance': COLOR_RED, 'Return To Vendor': COLOR_RED,
  // tím — calibration
  Calibrating: COLOR_PURPLE,
  // xám — mặc định
  Draft: COLOR_GRAY, Closed: COLOR_GRAY, Archived: COLOR_GRAY,
  Decommissioned: COLOR_GRAY, Exempt: COLOR_GRAY,
}

/** Trả về chuỗi class Tailwind để làm badge. Fallback: xám. */
export function getStatusColor(status?: string | null): string {
  if (!status) return COLOR_GRAY
  return STATUS_COLOR[status] ?? COLOR_GRAY
}

// ─── Misc formatters ────────────────────────────────────────────────────────

/** dd/MM/yyyy HH:mm */
export function formatDateTime(d?: string | null): string {
  if (!d) return '—'
  const dt = new Date(d)
  if (Number.isNaN(dt.getTime())) return d
  return dt.toLocaleString('vi-VN')
}

/** dd/MM/yyyy */
export function formatDate(d?: string | null): string {
  if (!d) return '—'
  const dt = new Date(d)
  if (Number.isNaN(dt.getTime())) return d
  return dt.toLocaleDateString('vi-VN')
}

/** 1,234,567 đ */
export function formatCurrency(v?: number | null): string {
  if (v == null) return '0 đ'
  return new Intl.NumberFormat('vi-VN', {
    style: 'currency', currency: 'VND', maximumFractionDigits: 0,
  }).format(v)
}
