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
  Submitted: 'Đã gửi',
  Cancelled: 'Đã hủy',
  Approved:  'Đã phê duyệt',
  Rejected:  'Bị từ chối',
  Closed:    'Đã đóng',
  Open:      'Đang mở',
  // IMM-16 CAPA lifecycle status (SoT cho CAPAListView + CAPADetailView badge
  // 'Trạng thái'). 'Pending Verification' THIẾU trước đây → consolidation về SSoT
  // sẽ leak raw EN nếu không thêm. Cả 2 biến thể space/underscore (Frappe trả raw).
  'Pending Verification': 'Chờ xác minh',
  Pending_Verification:   'Chờ xác minh',

  // ── IMM-16 Management Review status (SSoT nhãn badge) ──────────────
  // Ground truth BE: `assetcore/hooks.py:97` + `assetcore/tests/test_imm16.py`
  // `_MR_VALID_STATES` = Draft / Held / Minutes Approved / Closed (Draft & Closed
  // đã có ở khối chung phía trên — nên thiếu 2 khoá này rất dễ lọt).
  // Thiếu ⇒ `<StatusBadge :state="mr.status" />` in NGUYÊN tiếng Anh «Held» /
  // «Minutes Approved» ở /compliance/mr và /compliance/mr/<id> (AC-UX-003, LL-FE-53).
  // Nhãn phải TRÙNG TUYỆT ĐỐI `MR_STATUSES` của `ManagementReviewListView.vue` —
  // khoá bằng guard parity `views/compliance/managementReviewStatusLabelParity.test.ts`.
  // Biến thể gạch dưới: Frappe trả raw ở vài đường (khuôn đã có cho Pending_Verification).
  Held:                'Đã họp',
  'Minutes Approved':  'Biên bản đã duyệt',
  Minutes_Approved:    'Biên bản đã duyệt',

  // ── IMM-12 Incident status backstop (R20) ─────────────────────────
  // StatusBadge-path (translateStatus → STATUS_MAP) THIẾU 2 mã này → raw-EN leak
  // ở IncidentListView (2/4 OPEN-state của open_incident_filter). Backstop khớp
  // INCIDENT_STATUS_LABEL (constants/labels.ts = SSoT IMM-12) để dù đi path nào
  // nhãn cũng đúng. KHÔNG thêm 'Open'/'In Progress' ở đây (domain CAPA/priority
  // dùng 'Đang mở'/'Đang thực hiện') → list incident render qua incidentStatusLabel.
  Acknowledged:   'Đã tiếp nhận',
  'RCA Required': 'Cần phân tích nguyên nhân gốc',
  RCA_Required:   'Cần phân tích nguyên nhân gốc',

  // ── IMM-01 Needs Request workflow states ──────────────────────────
  Reviewing:   'Đang rà soát',
  Prioritized: 'Đã chấm ưu tiên',
  Budgeted:    'Đã lập dự toán',

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
  // Đồng bộ với constants/labels.ts + AssetListView (chống drift nhãn donut↔list, LL-FE-3).
  Commissioned:       'Đã đưa vào sử dụng',
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
  'Pending Review': 'Chờ duyệt',
  Pending_Approval:'Chờ phê duyệt',
  'Pending Approval':'Chờ phê duyệt',

  // ── Transfer / Receipt ────────────────────────────────────────────
  Received:  'Đã tiếp nhận',

  // ── IMM-15 Inventory ─────────────────────────────────────────────
  Requested:    'Đã yêu cầu',
  Picked:       'Đã soạn hàng',
  Issued:       'Đã xuất kho',
  Returned:     'Đã hoàn trả',
  Planned:      'Đã lập kế hoạch',
  Counting:     'Đang kiểm đếm',
  Reviewed:     'Đã rà soát',
  Posted:       'Đã ghi nhận',
  // IMM-16 Compliance findings/audits
  'Under Review':    'Đang xem xét',
  Under_Review:      'Đang xem xét',
  'Confirmed NC':    'Đã xác nhận sự không phù hợp',
  Confirmed_NC:      'Đã xác nhận sự không phù hợp',
  'False Positive':  'Cảnh báo nhầm',
  False_Positive:    'Cảnh báo nhầm',
  Resolved:          'Đã khắc phục',
  Waived:            'Đã miễn trừ',
  Reporting:         'Đang lập báo cáo',
  're-opened':       'Đã mở lại',
  'Re-opened':       'Đã mở lại',
  'Re Opened':       'Đã mở lại',
  // IMM-16 CAPA effectiveness_check (xác minh hiệu quả NĐ98/QMS) — SSoT nhãn VI
  Effective:             'Hiệu quả',
  'Partially Effective': 'Hiệu quả một phần',
  Partially_Effective:   'Hiệu quả một phần',
  'Not Effective':       'Không hiệu quả',
  Not_Effective:         'Không hiệu quả',
  // IMM-16 CAPA workflow_state (máy trạng thái, stage) — khớp CAPA_WORKFLOW_LABEL
  // constants/labels.ts. Cần ở đây để StatusBadge (qua translateStatus) render
  // nhãn VI cho badge "Tiến trình" trên CAPADetailView, không leak raw EN
  // ('Investigating'/'Action Plan'/...). 'Open'/'Closed' đã có ở map docstatus.
  Investigating:  'Đang điều tra',
  'Action Plan':  'Lập kế hoạch hành động',
  Implementation: 'Đang thực thi',
  Verification:   'Đang xác minh',

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

  // ── IMM-06 Training & Competency ─────────────────────────────────────
  Transferred:          'Đã chuyển',
  Inactive:             'Không hoạt động',
  Applied:              'Đã áp dụng',
  'Rollback Required':  'Cần khôi phục',
  Rollback_Required:    'Cần khôi phục',
  'Rolled Back':        'Đã khôi phục',
  Rolled_Back:          'Đã khôi phục',
  Confirmed:            'Đã xác nhận',
  Verified:             'Đã xác minh',
  'Pending Signoff':    'Chờ phê duyệt',
  Pending_Signoff:      'Chờ phê duyệt',
  'Pending Assessment': 'Chờ đánh giá',
  Pending_Assessment:   'Chờ đánh giá',
  Expiring:             'Sắp hết hạn',
  Revoked:              'Đã thu hồi',
  Suspended:            'Tạm ngưng',
  // PM Schedule.status (Active/Paused/Suspended) — thiếu 'Paused' ⇒ badge + ô lọc của
  // `/pm/schedules` render THÔ chữ "Paused" (GATE-1). Nhãn khớp form cùng màn.
  Paused:               'Tạm dừng',

  // ── IMM-02 Tech Spec / Vendor Evaluation (Wave 2) ────────────────────
  Benchmarked:          'Đã so sánh thị trường',
  'Risk Assessed':      'Đã đánh giá rủi ro',
  Risk_Assessed:        'Đã đánh giá rủi ro',
  Locked:               'Đã chốt',
  Withdrawn:            'Đã rút',
  'Open RFQ':           'Đang yêu cầu báo giá',
  Open_RFQ:             'Đang yêu cầu báo giá',
  'Quotation Received': 'Đã nhận báo giá',
  Quotation_Received:   'Đã nhận báo giá',
  Evaluated:            'Đã đánh giá',

  // ── IMM-03 Procurement Decision (Wave 2) ─────────────────────────────
  'Method Selected':    'Đã chọn phương án',
  Method_Selected:      'Đã chọn phương án',
  Negotiation:          'Đang thương thảo',
  'Award Recommended':  'Đề xuất trúng thầu',
  Award_Recommended:    'Đề xuất trúng thầu',
  Awarded:              'Đã trao thầu',
  'Contract Signed':    'Đã ký hợp đồng',
  Contract_Signed:      'Đã ký hợp đồng',
  'PO Issued':          'Đã phát hành đơn hàng',
  PO_Issued:            'Đã phát hành đơn hàng',
  Conditional:          'Có điều kiện',
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

// ─── Frequency translation (SSoT) ───────────────────────────────────────────
// Nhãn tần suất đánh giá / khấu hao — DUY NHẤT 1 map cho toàn FE (chống drift &
// English-enum leak, anti-pattern A). Phủ ĐỦ option BE ground truth:
//   • Compliance Rule.evaluation_frequency: Realtime/Hourly/Daily/Weekly/Monthly/Quarterly
//   • AC Asset.depreciation_frequency:      Monthly/Quarterly/Yearly
// LƯU Ý: pm_type (Quarterly/Semi-Annual/Annual/Ad-hoc) là LOẠI PM — domain
// khác, có SSoT riêng translatePmType / PM_TYPE_MAP bên dưới (KHÔNG gộp vào
// đây). Các key Semi-Annual/Annual/Ad-hoc trong FREQUENCY_MAP chỉ phục vụ field
// *frequency* dùng chung, không phải pm_type.
const FREQUENCY_MAP: Record<string, string> = {
  Realtime:      'Thời gian thực',
  Hourly:        'Hàng giờ',
  Daily:         'Hàng ngày',
  Weekly:        'Hàng tuần',
  Monthly:       'Hàng tháng',
  Quarterly:     'Hàng quý',
  Yearly:        'Hàng năm',
  'Semi-Annual': 'Nửa năm',
  Annual:        'Hàng năm',
  'Ad-hoc':      'Theo yêu cầu',
}

/**
 * Trả nhãn Tiếng Việt cho 1 giá trị tần suất.
 * - null / '' → '—'
 * - key lạ → trả nguyên `v` (không crash, không bịa nhãn).
 */
export function translateFrequency(v?: string | null): string {
  if (!v) return '—'
  return FREQUENCY_MAP[v] ?? v
}

// ─── PM type translation (SSoT) ─────────────────────────────────────────────
// pm_type là LOẠI bảo trì định kỳ (domain RIÊNG với frequency — xem ghi chú
// FREQUENCY_MAP). Trước đây 2 view (PmScheduleListView + PmTemplateListView) tự
// khai map cục bộ GIỐNG HỆT nhau → drift risk. Gom về DUY NHẤT 1 map ở đây.
// BE ground truth: PM Schedule / PM Checklist Template.pm_type
//   = Quarterly\nSemi-Annual\nAnnual\nAd-hoc
// Nhãn canonical PM domain: 'Ad-hoc' → 'Đột xuất' (KHÁC field frequency dùng
// 'Theo yêu cầu' — domain khác, giữ nguyên khác biệt có chủ đích).
const PM_TYPE_MAP: Record<string, string> = {
  Quarterly:     'Hàng quý',
  'Semi-Annual': 'Nửa năm',
  Annual:        'Hàng năm',
  'Ad-hoc':      'Đột xuất',
}

/**
 * Trả nhãn Tiếng Việt cho 1 loại PM (pm_type).
 * - null / '' → '—'
 * - key lạ → trả nguyên `v` (không crash, không bịa nhãn).
 */
export function translatePmType(v?: string | null): string {
  if (!v) return '—'
  return PM_TYPE_MAP[v] ?? v
}

// ─── Depreciation method translation (SSoT) ─────────────────────────────────
// Phương pháp khấu hao tài sản (IMM-00 master data → AC Asset / Device Model /
// Asset Category). DUY NHẤT 1 map cho toàn FE — chống English-enum leak
// (anti-pattern A) và drift nhãn giữa các view (DepreciationView, AssetDetail,
// AssetDepreciationSchedule, DeviceModelForm, ReferenceData).
// BE ground truth: AC Asset.depreciation_method / Asset Category.default_depreciation_method
//   = Straight Line / Double Declining / Units of Production (+ 'None'/null = chưa đặt).
const DEPRECIATION_METHOD_MAP: Record<string, string> = {
  'Straight Line':       'Đường thẳng',
  'Double Declining':    'Số dư giảm dần',
  'Units of Production': 'Theo sản lượng',
}

/**
 * Trả nhãn Tiếng Việt cho 1 phương pháp khấu hao.
 * - null / '' / undefined / 'None' → '—' (chưa đặt / không khấu hao).
 * - key lạ → trả nguyên `v` (không crash, không bịa nhãn).
 */
export function translateDepreciationMethod(v?: string | null): string {
  if (!v || v === 'None') return '—'
  return DEPRECIATION_METHOD_MAP[v] ?? v
}

// ─── Asset Lifecycle Event type translation (SSoT) ──────────────────────────
// Nhãn VI cho `event_type` của Asset Lifecycle Event (IMM-00 trục vòng đời).
// DUY NHẤT 1 map cho toàn FE — chống raw-EN leak (anti-pattern A) ở dòng thời
// gian AssetDetailView (tab "Lịch sử"). Trước đây view render `event.event_type`
// THÔ → lộ mã 'restored'/'activated'/'commissioned'/... bằng tiếng Anh.
// BE ground truth: Asset Lifecycle Event.event_type (18 option) — KHỚP đủ enum
//   asset_lifecycle_event.json. Phân biệt rõ:
//   • 'activated'  = kích hoạt sau repair/calib/PM/commission → 'Kích hoạt'
//   • 'restored'   = khôi phục sau tạm ngừng (Out of Service → Active) → 'Khôi phục hoạt động'
//   (INV-ALE-RESTORE: 1 transition OoS→Active chỉ sinh 1 event 'restored', VI rõ nghĩa).
const LIFECYCLE_EVENT_MAP: Record<string, string> = {
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

// Nhãn an toàn cho event_type KHÔNG thuộc LIFECYCLE_EVENT_MAP (mã legacy/drift/
// lạ — vd 'pm_aborted', 'restored_v2', 'SOME_DRIFT'). KHÔNG bao giờ trả raw code:
// consumer là MÀN HÌNH QUÉT QR (AssetScanInfoView.vue:229, recent_maintenance.
// event_type) + DÒNG THỜI GIAN (AssetDetailView.vue:816) — cả 2 đi qua SSoT này
// (KHÔNG fork helper riêng cho scan-info). Hard-constraint no-leak: nếu fallback
// trả nguyên `v` thì mã English/snake_case rò ra UI → vi phạm. 'Khác' là nhãn
// VI cố định, an toàn cho mọi mã chưa biết.
const UNKNOWN_LIFECYCLE_EVENT_LABEL = 'Khác'

/**
 * Trả nhãn Tiếng Việt cho 1 loại sự kiện vòng đời (Asset Lifecycle Event.event_type).
 * - null / '' / undefined → '—' (giữ nguyên hành vi rỗng).
 * - key đã biết → nhãn VI tương ứng trong LIFECYCLE_EVENT_MAP.
 * - key lạ (legacy/drift/không thuộc map) → UNKNOWN_LIFECYCLE_EVENT_LABEL ('Khác').
 *   KHÔNG trả nguyên `v` — chống raw-code leak ở màn quét QR & dòng thời gian.
 * Bất biến đo được: với mọi input string không thuộc map, kết quả KHÔNG chứa '_'
 * và KHÔNG bằng chính `v` (no-leak qua mọi đường).
 */
export function translateLifecycleEvent(v?: string | null): string {
  if (!v) return '—'
  return LIFECYCLE_EVENT_MAP[v] ?? UNKNOWN_LIFECYCLE_EVENT_LABEL
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
  Submitted: COLOR_BLUE,   Approved: COLOR_GREEN,     Completed: COLOR_GREEN,
  Active: COLOR_GREEN,     Passed: COLOR_GREEN,       'Clinical Release': COLOR_GREEN,
  Received: COLOR_GREEN,   'Certificate Received': COLOR_GREEN,
  // IMM-12 incident status backstop (R20) — màu khớp INCIDENT_STATUS_CLASS.
  Acknowledged: COLOR_BLUE,
  'RCA Required': COLOR_ORANGE, RCA_Required: COLOR_ORANGE,
  // xanh dương — đang xử lý
  'In Progress': COLOR_BLUE, In_Progress: COLOR_BLUE, Diagnosing: COLOR_BLUE,
  'In Repair': COLOR_BLUE,  In_Repair: COLOR_BLUE,    Installing: COLOR_BLUE,
  Commissioned: COLOR_BLUE, 'Initial Inspection': COLOR_BLUE, 'Sent to Lab': COLOR_BLUE,
  Assigned: COLOR_BLUE,
  Reviewing: COLOR_BLUE,
  Prioritized: COLOR_BLUE,   Budgeted: COLOR_BLUE,
  // IMM-16 Soát xét lãnh đạo (AC-UX-003): vòng đời Bản nháp → Đã họp → Biên bản đã
  // duyệt → Đã đóng. Gán màu CHỦ Ý, không để rơi về COLOR_GRAY mặc định — «đã họp» là
  // đang xử lý (cùng tông In Progress), «biên bản đã duyệt» là mốc đã duyệt (tông
  // Approved). Draft/Closed giữ COLOR_GRAY sẵn có ở khối xám phía dưới.
  Held: COLOR_BLUE,
  'Minutes Approved': COLOR_GREEN, Minutes_Approved: COLOR_GREEN,
  // vàng — chờ
  Pending: COLOR_YELLOW,   'Pending Approval': COLOR_YELLOW,
  Pending_Approval: COLOR_YELLOW, Pending_Review: COLOR_YELLOW, 'Pending Review': COLOR_YELLOW,
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

  // ── IMM-15 Inventory ───────────────────────────────────────────────
  Requested:  COLOR_YELLOW,
  Picked:     COLOR_BLUE,
  Issued:     COLOR_GREEN,
  Returned:   COLOR_GRAY,
  Planned:    COLOR_YELLOW,
  Counting:   COLOR_BLUE,
  Reviewed:   COLOR_BLUE,
  Posted:     COLOR_GREEN,

  // ── IMM-16 Compliance ──────────────────────────────────────────────
  // CAPA lifecycle status 'Pending Verification' — tím (chờ xác minh hiệu quả),
  // khớp màu local cũ ở CAPAListView trước khi gỡ về SSoT.
  'Pending Verification': COLOR_PURPLE,
  Pending_Verification:   COLOR_PURPLE,
  'Under Review':   COLOR_BLUE,
  Under_Review:     COLOR_BLUE,
  'Confirmed NC':   COLOR_RED,
  Confirmed_NC:     COLOR_RED,
  'False Positive': COLOR_GRAY,
  False_Positive:   COLOR_GRAY,
  Resolved:         COLOR_GREEN,
  Waived:           COLOR_GRAY,
  Reporting:        COLOR_BLUE,
  're-opened':      COLOR_ORANGE,
  'Re-opened':      COLOR_ORANGE,
  'Re Opened':      COLOR_ORANGE,
  // IMM-16 CAPA effectiveness_check — màu compliance pin: Effective=xanh, Partial=vàng, NotEff=đỏ
  Effective:             COLOR_GREEN,
  'Partially Effective': COLOR_YELLOW,
  Partially_Effective:   COLOR_YELLOW,
  'Not Effective':       COLOR_RED,
  Not_Effective:         COLOR_RED,
  // IMM-16 CAPA workflow_state (stage) — màu cho badge "Tiến trình" CAPADetailView.
  Investigating:  COLOR_BLUE,
  'Action Plan':  COLOR_BLUE,
  Implementation: COLOR_BLUE,
  Verification:   COLOR_PURPLE,

  // ── IMM-06 Training & Competency ─────────────────────────────────────
  Transferred:        COLOR_GRAY,
  Inactive:           COLOR_GRAY,
  Applied:            COLOR_BLUE,
  'Rolled Back':      COLOR_RED,
  Rolled_Back:        COLOR_RED,
  Confirmed:          COLOR_BLUE,
  Verified:           COLOR_GREEN,
  'Pending Signoff':  COLOR_YELLOW,
  Pending_Signoff:    COLOR_YELLOW,
  'Pending Assessment': COLOR_BLUE,
  Pending_Assessment: COLOR_BLUE,
  Expiring:           COLOR_ORANGE,
  Revoked:            COLOR_RED,
  Suspended:          COLOR_ORANGE,
  Paused:             COLOR_YELLOW,

  // ── IMM-02 Tech Spec / Vendor Evaluation (Wave 2) ─────────────────────
  Benchmarked:         COLOR_BLUE,
  'Risk Assessed':     COLOR_BLUE,
  Risk_Assessed:       COLOR_BLUE,
  Locked:              COLOR_GREEN,
  Withdrawn:           COLOR_GRAY,
  'Open RFQ':          COLOR_BLUE,
  Open_RFQ:            COLOR_BLUE,
  'Quotation Received':COLOR_BLUE,
  Quotation_Received:  COLOR_BLUE,
  Evaluated:           COLOR_GREEN,

  // ── IMM-03 Procurement Decision (Wave 2) ──────────────────────────────
  'Method Selected':   COLOR_BLUE,
  Method_Selected:     COLOR_BLUE,
  Negotiation:         COLOR_BLUE,
  'Award Recommended': COLOR_BLUE,
  Award_Recommended:   COLOR_BLUE,
  Awarded:             COLOR_GREEN,
  'Contract Signed':   COLOR_GREEN,
  Contract_Signed:     COLOR_GREEN,
  'PO Issued':         COLOR_GREEN,
  PO_Issued:           COLOR_GREEN,
  Conditional:         COLOR_YELLOW,
}

// ─── Relative time (Vietnamese) ─────────────────────────────────────────────
/** "30s trước", "12 phút trước", "3 giờ trước", "2 ngày trước". */
export function formatRelativeTime(d?: string | null): string {
  if (!d) return '—'
  const dt = new Date(d)
  if (Number.isNaN(dt.getTime())) return d
  const diff = Math.max(0, (Date.now() - dt.getTime()) / 1000)
  if (diff < 60) return `${Math.floor(diff)}s trước`
  if (diff < 3600) return `${Math.floor(diff / 60)} phút trước`
  if (diff < 86400) return `${Math.floor(diff / 3600)} giờ trước`
  if (diff < 86400 * 30) return `${Math.floor(diff / 86400)} ngày trước`
  return formatDate(d)
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

/** Frappe Check fields (`tinyint`) đến từ JSON có thể là 0/1, '0'/'1', false/true, null. */
export function isCheckOn(v: unknown): boolean {
  return v === 1 || v === true || v === '1' || v === 'true'
}

/** 1,234,567 đ */
export function formatCurrency(v?: number | null): string {
  if (v == null) return '0 đ'
  return new Intl.NumberFormat('vi-VN', {
    style: 'currency', currency: 'VND', maximumFractionDigits: 0,
  }).format(v)
}

/**
 * L-16 — SSoT money rút gọn cho dashboard/bảng (DepreciationView,
 * InventoryDashboardView). Gom inline `vndShort` trùng lặp về 1 chỗ.
 *  - null/undefined → '—'
 *  - |v| ≥ 1 tỷ      → "x.x tỷ"
 *  - |v| ≥ 1 triệu   → "x tr"
 *  - còn lại         → full VND (đồng bộ formatCurrency).
 */
export function formatCurrencyShort(v?: number | null): string {
  if (v == null) return '—'
  if (Math.abs(v) >= 1e9) return (v / 1e9).toFixed(1) + ' tỷ'
  if (Math.abs(v) >= 1e6) return (v / 1e6).toFixed(0) + ' tr'
  return new Intl.NumberFormat('vi-VN', {
    style: 'currency', currency: 'VND', maximumFractionDigits: 0,
  }).format(v)
}

// ─── Money INPUT grouping (dấu phân nhóm hàng nghìn — kiểu Việt Nam) ──────────
// Dùng bởi CurrencyInput.vue / useThousandsInput: hiển thị số tiền có dấu phân
// nhóm hàng nghìn KIỂU VIỆT NAM (dấu chấm: 1.000.000) ngay khi user gõ, nhưng
// v-model giữ number SẠCH để submit thẳng cho BE (Currency). Tách 2 hàm THUẦN
// (testable, không phụ thuộc Vue) khỏi component.
//
// Nhóm thủ công bằng `_THOUSAND_SEP` (KHÔNG dùng Intl locale) để output TẤT
// ĐỊNH, không lệ thuộc ICU môi trường (Intl 'vi-VN' có thể fallback ',' nếu
// thiếu ICU). Đổi sang dấu phẩy chỉ cần sửa 1 hằng số này.
const _THOUSAND_SEP = '.'
const _GROUP_RE = /\B(?=(\d{3})+(?!\d))/g

/**
 * Số/chuỗi → chuỗi đã nhóm hàng nghìn (KHÔNG ký hiệu ₫). Chỉ phần nguyên (VND).
 * - null / undefined / '' → '' (ô trống).
 * - chuỗi có sẵn nhóm/ký hiệu → chuẩn hoá lại (bỏ ký tự không-số rồi nhóm).
 * - không parse được → ''.
 */
export function formatThousands(v: number | string | null | undefined): string {
  if (v === null || v === undefined || v === '') return ''
  const n = typeof v === 'number' ? v : parseThousands(v)
  if (n === null || Number.isNaN(n)) return ''
  return Math.trunc(Math.abs(n)).toString().replace(_GROUP_RE, _THOUSAND_SEP)
}

/**
 * Chuỗi đã nhóm ("1.234.567" / "1.234.567 ₫") → number nguyên SẠCH.
 * - Bỏ MỌI ký tự không phải chữ số (dấu chấm phân nhóm, khoảng trắng, ₫).
 * - rỗng / không có chữ số / null → null (phân biệt "để trống" với số 0).
 */
export function parseThousands(s: string | number | null | undefined): number | null {
  if (s === null || s === undefined) return null
  const digits = String(s).replace(/\D/g, '')
  if (digits === '') return null
  return Number(digits)
}

/**
 * SSoT percent formatter. null/undefined → 'em-dash' (KHÔNG '0%') — dùng cho KPI
 * không-có-mẫu (vd compliance khi total_scheduled==0) để tránh hiểu nhầm
 * "không tuân thủ". Có giá trị → `<v>%` (1 chữ số thập phân do BE đã round).
 */
export function formatPercent(v?: number | null): string {
  if (v == null) return '—'
  return `${v}%`
}

/**
 * SSoT kích thước tệp (bytes → chuỗi đọc-được kiểu Việt Nam) — AC-CR-81.
 *
 * - Dấu THẬP PHÂN là dấu PHẨY ("1,2 MB") theo quy ước VI; phần nguyên tròn thì
 *   bỏ hẳn phần thập phân ("1 KB", KHÔNG "1,0 KB").
 * - Đơn vị giữ ký hiệu chuẩn `B/KB/MB/GB` (LL-FE-53: ký hiệu đơn vị được GIỮ);
 *   KHÔNG in chữ "bytes" (chuỗi tiếng Anh).
 * - `0` / null / undefined / rác (âm, NaN, Infinity) → `''` để nơi gọi tự chọn
 *   cách nói ("Chưa đính kèm tệp"), thay vì rò "0 B"/"NaN" ra UI.
 */
export function formatFileSize(bytes?: number | null): string {
  if (bytes == null) return ''
  const n = Number(bytes)
  if (!Number.isFinite(n) || n <= 0) return ''
  const UNITS = ['B', 'KB', 'MB', 'GB', 'TB'] as const
  let value = n
  let unit = 0
  while (value >= 1024 && unit < UNITS.length - 1) {
    value /= 1024
    unit += 1
  }
  // B là số nguyên (không có "0,5 B"); các bậc trên lấy 1 chữ số thập phân.
  const rounded = unit === 0 ? Math.round(value) : Math.round(value * 10) / 10
  return `${String(rounded).replace('.', ',')} ${UNITS[unit]}`
}
