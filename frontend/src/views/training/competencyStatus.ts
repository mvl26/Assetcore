// Copyright (c) 2026, AssetCore Team
// SSoT trình bày trạng thái năng lực (IMM-06) — BR-06-14 predicate LIVE.
//
// Bối cảnh (count-vs-drill divergence): scheduler chỉ stamp workflow_state='Expiring'
// đúng mốc 90/60/30 ngày và 'Expired' khi quá hạn (có thể lỡ phiên). → một năng lực
// có expiry_date < today nhưng workflow_state vẫn 'Active' (scheduler lỡ auto_expire)
// sẽ hiển thị nhãn "Đang hoạt động"/"Hiệu lực" SAI LỆCH — operator quá hạn trông như
// vẫn đủ năng lực (rủi ro NĐ98). BE đã chuyển KPI/drill sang SoT date-derived; FE
// badge cũng phải phái sinh nhãn LIVE thay vì tin cờ workflow_state thuần.
//
// Quy tắc:
//   • days_until_expiry < 0  → 'Đã hết hạn'  (date-derived, override cờ Active/Expiring)
//   • days_until_expiry trong [0, 60] và state ∈ {Active, Expiring} → 'Sắp hết hạn'
//   • còn lại → nhãn theo workflow_state qua translateStatus (SSoT global formatters)
// KHÔNG hardcode 'Đang hiệu lực' cho năng lực có expiry_date < today.

import { translateStatus } from '@/utils/formatters'
import type { Imm06DashboardStats } from '@/api/imm06'

/** KHỚP BE EXPIRY_WINDOW_DAYS (services/imm06.py) — cửa sổ "Sắp hết hạn". */
export const EXPIRY_WINDOW_DAYS = 60

/**
 * Tile KPI năng lực cho TrainingDashboard — bind VERBATIM giá trị BE (transport-agnostic).
 *
 * BR-06-14: BE đổi NGUỒN ĐẾM (workflow_state thuần → SoT date-derived); FE chỉ render
 * giá trị BE gửi, KHÔNG tự tính lại count. Tile 'Sắp hết hạn' = competencies.expiring,
 * tile 'Đã hết hạn' = competencies.expired — đọc thẳng, không suy diễn.
 */
export interface CompetencyExpiryTile {
  key: 'expiring' | 'expired'
  label: string
  value: number
}

/** Đọc verbatim 2 tile từ dashboard stats — KHÔNG tính lại ở FE. */
export function competencyExpiryTiles(stats: Imm06DashboardStats): CompetencyExpiryTile[] {
  const c = stats.competencies
  return [
    { key: 'expiring', label: 'Sắp hết hạn', value: c.expiring },
    { key: 'expired', label: 'Đã hết hạn', value: c.expired },
  ]
}

/** Trạng thái không bao giờ bị derive theo ngày (đã rời khỏi hiệu lực một cách chủ động). */
const TERMINAL_OR_INACTIVE = new Set(['Revoked', 'Suspended', 'Pending Assessment'])

/**
 * Nhãn trạng thái năng lực phái sinh LIVE (tiếng Việt, không leak EN).
 *
 * @param workflowState  workflow_state thô từ BE (Active/Expiring/Expired/Revoked/...).
 * @param daysUntilExpiry  days_until_expiry (số ngày tới hạn; <0 = đã quá hạn; null = không có hạn).
 * @returns nhãn tiếng Việt qua SSoT.
 */
export function competencyEffectiveStatusLabel(
  workflowState: string,
  daysUntilExpiry: number | null | undefined,
): string {
  // Revoked/Suspended/Pending: giữ nguyên nghĩa workflow (không suy theo ngày).
  if (TERMINAL_OR_INACTIVE.has(workflowState)) {
    return translateStatus(workflowState)
  }
  if (typeof daysUntilExpiry === 'number') {
    if (daysUntilExpiry < 0) return translateStatus('Expired')          // 'Hết hạn'
    if (daysUntilExpiry <= EXPIRY_WINDOW_DAYS) return translateStatus('Expiring') // 'Sắp hết hạn'
  }
  return translateStatus(workflowState)
}

/**
 * workflow_state HIỆU LỰC để truyền vào StatusBadge (giữ màu đúng theo getStatusColor).
 *
 * Trả về state key (EN) phái sinh để badge map cả label lẫn màu nhất quán:
 *   • quá hạn (days<0) → 'Expired' (đỏ) dù cờ còn Active.
 *   • sắp hết hạn (0..60, Active/Expiring) → 'Expiring' (cam).
 *   • còn lại → workflow_state gốc.
 */
export function competencyEffectiveState(
  workflowState: string,
  daysUntilExpiry: number | null | undefined,
): string {
  if (TERMINAL_OR_INACTIVE.has(workflowState)) return workflowState
  if (typeof daysUntilExpiry === 'number') {
    if (daysUntilExpiry < 0) return 'Expired'
    if (daysUntilExpiry <= EXPIRY_WINDOW_DAYS && (workflowState === 'Active' || workflowState === 'Expiring')) {
      return 'Expiring'
    }
  }
  return workflowState
}
