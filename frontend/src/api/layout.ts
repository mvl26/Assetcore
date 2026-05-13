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
  'Document Request': () => `/documents/requests`,
  'Firmware Change Request': () => `/cm/firmware`,
}

export function resolveNotificationRoute(
  docType: string | null | undefined,
  docName: string | null | undefined,
): string | null {
  if (!docType || !docName) return null
  const builder = DOCTYPE_TO_ROUTE[docType]
  return builder ? builder(docName) : null
}
