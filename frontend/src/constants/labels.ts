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
