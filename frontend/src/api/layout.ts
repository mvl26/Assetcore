// AssetCore — Layout API client (notifications + user context + logout)
import { frappeGet, frappePost } from './helpers'

export interface NotificationItem {
  name: string
  subject: string
  content: string
  document_type: string | null
  document_name: string | null
  type: string
  from_user: string | null
  read: 0 | 1
  creation: string
}

export interface UnreadResponse {
  count: number
  items: NotificationItem[]
}

export interface UserContext {
  user: string
  full_name: string
  user_image: string | null
  phone: string | null
  role_profile_name: string | null
  roles: string[]
  imm_roles: string[]
  job_title: string | null
  employee_code: string | null
  department: string | null
  department_name: string | null
  is_profile_completed: boolean
  has_ac_profile: boolean
  has_employee_link: boolean
}

const BASE = '/api/method/assetcore.api.layout'

export function getUnreadNotifications(limit = 20): Promise<UnreadResponse> {
  return frappeGet(`${BASE}.get_unread_notifications`, { limit })
}

export interface ListNotifResponse {
  pagination: { total: number; page: number; page_size: number; total_pages: number; offset: number }
  items: NotificationItem[]
}

/** Paginated list — bao gồm cả đã đọc; dùng cho tab "Tất cả". */
export function listNotifications(
  page = 1,
  pageSize = 20,
  onlyUnread = false,
): Promise<ListNotifResponse> {
  return frappeGet(`${BASE}.list_notifications`, {
    page, page_size: pageSize, only_unread: onlyUnread ? 1 : 0,
  })
}

export function markNotificationAsRead(name: string): Promise<{ name: string; read: 1 }> {
  return frappePost(`${BASE}.mark_notification_as_read`, { name })
}

export function markAllAsRead(): Promise<{ updated_rows: number }> {
  return frappePost(`${BASE}.mark_all_as_read`, {})
}

export function getUserContext(): Promise<UserContext> {
  return frappeGet(`${BASE}.get_user_context`)
}

export function logoutUser(): Promise<{ logged_out?: boolean; already_logged_out?: boolean }> {
  return frappePost(`${BASE}.logout_user`, {})
}

// ─── Cross-DocType route resolver ────────────────────────────────────────────
//
// Dựa vào document_type của Notification Log → trả về path FE tương ứng.
// Nếu DocType không có view FE → trả null (caller fallback /dashboard).

const DOCTYPE_TO_ROUTE: Record<string, (name: string) => string> = {
  'AC Asset': (n) => `/assets/${encodeURIComponent(n)}`,
  'Asset Document': (n) => `/documents/view/${encodeURIComponent(n)}`,
  'Asset Commissioning': (n) => `/commissioning/${encodeURIComponent(n)}`,
  'PM Work Order': (n) => `/pm/work-orders/${encodeURIComponent(n)}`,
  'Asset Repair': (n) => `/cm/work-orders/${encodeURIComponent(n)}`,
  'CM Work Order': (n) => `/cm/work-orders/${encodeURIComponent(n)}`,
  'Incident Report': (n) => `/incidents/${encodeURIComponent(n)}`,
  'IMM CAPA Record': (n) => `/capas/${encodeURIComponent(n)}`,
  'Asset Transfer': (n) => `/asset-transfers/${encodeURIComponent(n)}`,
  'Service Contract': (n) => `/service-contracts/${encodeURIComponent(n)}`,
  'IMM Asset Calibration': (n) => `/calibration/${encodeURIComponent(n)}`,
  'IMM Calibration': (n) => `/calibration/${encodeURIComponent(n)}`,
  'IMM Calibration Schedule': () => `/calibration/schedules`,
  'Calibration Result': (n) => `/calibration/${encodeURIComponent(n)}`,
  'IMM RCA Record': (n) => `/rca/${encodeURIComponent(n)}`,
  'Asset QA Non Conformance': (n) => `/commissioning/${encodeURIComponent(n)}/nc`,
  'IMM Device Model': (n) => `/device-models/${encodeURIComponent(n)}`,
  'AC Supplier': (n) => `/suppliers/${encodeURIComponent(n)}`,
  'IMM Needs Request': (n) => `/needs-requests/${encodeURIComponent(n)}`,
  'Document Request': () => `/documents/requests`,
  'Firmware Change Request': () => `/cm/firmware`,
}

// Điểm đến cấp DANH SÁCH khi thông báo là digest span nhiều record (document_name
// rỗng) → deep-link 1 doc vô nghĩa. Vd escalation "phiếu nhu cầu quá hạn"
// (notify_needs_overdue) gộp nhiều NR → mở list đã lọc sẵn phiếu quá hạn.
const DOCTYPE_TO_LIST_ROUTE: Record<string, string> = {
  'IMM Needs Request': '/needs-requests?overdue=1',
}

export function resolveNotificationRoute(
  docType: string | null | undefined,
  docName: string | null | undefined,
): string | null {
  if (!docType) return null
  // Digest (không có document_name cụ thể) → điểm đến danh sách nếu doctype có map.
  if (!docName) return DOCTYPE_TO_LIST_ROUTE[docType] ?? null
  const builder = DOCTYPE_TO_ROUTE[docType]
  return builder ? builder(docName) : null
}

// ─── Nhãn tiếng Việt cho document_type (hiển thị trên chuông/thông báo) ──────────
//
// Tránh lộ mã DocType thô tiếng Anh ('IMM Needs Request') ra UI người dùng cuối
// (LL-FE-46 · ui_copy_language_policy LL-FE-53). Doctype chưa map → trả nguyên văn.

const DOCTYPE_LABEL_VI: Record<string, string> = {
  'AC Asset': 'Thiết bị',
  'Asset Document': 'Hồ sơ tài liệu',
  'Asset Commissioning': 'Nghiệm thu',
  'PM Work Order': 'Lệnh bảo trì',
  'Asset Repair': 'Phiếu sửa chữa',
  'CM Work Order': 'Phiếu sửa chữa',
  'Incident Report': 'Sự cố',
  'IMM CAPA Record': 'Hành động khắc phục/phòng ngừa',
  'Asset Transfer': 'Điều chuyển tài sản',
  'Service Contract': 'Hợp đồng dịch vụ',
  'IMM Asset Calibration': 'Hiệu chuẩn',
  'IMM Calibration': 'Hiệu chuẩn',
  'IMM Calibration Schedule': 'Lịch hiệu chuẩn',
  'Calibration Result': 'Kết quả hiệu chuẩn',
  'IMM RCA Record': 'Phân tích nguyên nhân gốc',
  'Asset QA Non Conformance': 'Điểm không phù hợp',
  'IMM Device Model': 'Model thiết bị',
  'AC Supplier': 'Nhà cung cấp',
  'Document Request': 'Yêu cầu tài liệu',
  'Firmware Change Request': 'Yêu cầu đổi firmware',
  'IMM Needs Request': 'Phiếu nhu cầu',
}

export function docTypeLabel(docType: string | null | undefined): string {
  if (!docType) return ''
  return DOCTYPE_LABEL_VI[docType] ?? docType
}
