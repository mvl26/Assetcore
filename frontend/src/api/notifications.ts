// Copyright (c) 2026, AssetCore Team
//
// Notification Framework (Wave N1) — API client cho per-user email toggle.
// Spec: docs/imm-00/05_API_Specification.md §III.21
// Mirrors BE: assetcore.api.notifications.{get_notification_preferences, set_email_enabled}
//
// In-app (chuông) dùng Frappe core desk Notification Log — không có client riêng ở đây.
import { frappeGet, frappePost } from './helpers'

const BASE = '/api/method/assetcore.api.notifications'

/** Tùy chọn thông báo của user — khớp BE envelope data. */
export interface NotificationPreferences {
  email_enabled: boolean
}

/** GET get_notification_preferences. frappeGet đã unwrap envelope → trả T trực tiếp. */
export function getNotificationPreferences(): Promise<NotificationPreferences> {
  return frappeGet(`${BASE}.get_notification_preferences`)
}

/** POST set_email_enabled — bật/tắt nhận email cho user hiện tại. */
export function setEmailEnabled(enabled: boolean): Promise<NotificationPreferences> {
  return frappePost(`${BASE}.set_email_enabled`, { enabled })
}

/** Ngưỡng màu KPI (khớp BE _delivery_status / _opt_out_status). */
export type KpiStatus = 'good' | 'warn' | 'bad' | 'na'

/**
 * KPI độ phủ thông báo (System Manager only) — khớp BE envelope data.
 * Spec: docs/imm-00/04_Backend_Design.md §III.1b-4.
 */
export interface DeliveryKpi {
  delivery_rate: number | null // null = mẫu rỗng (chia-0 guard)
  sent: number
  failed: number
  opt_out_rate: number | null // null = không có user
  total_users: number
  opted_out: number
  window_days: number
  delivery_status: KpiStatus
  opt_out_status: KpiStatus
}

/** GET get_delivery_kpi — KPI delivery rate + opt-out rate (cửa sổ `days` ngày). */
export function getDeliveryKpi(days = 30): Promise<DeliveryKpi> {
  return frappeGet(`${BASE}.get_delivery_kpi`, { days })
}
