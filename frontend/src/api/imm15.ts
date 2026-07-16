// Copyright (c) 2026, AssetCore Team
// IMM-15 — Spare Parts Inventory transaction layer (Allocation / Cycle Count /
// Forecast / Watchlist / Dashboard). Master/movement endpoints stay in
// `@/api/inventory` (LIVE AC backbone).
import { frappeGet, frappePost } from '@/api/helpers'

const BASE = '/api/method/assetcore.api.imm15'

// ─── Types ───────────────────────────────────────────────────────────────────

export type AllocationState =
  | 'Requested' | 'Approved' | 'Picked' | 'Issued' | 'Returned' | 'Cancelled'
export type UrgencyLevel = 'Routine' | 'Urgent' | 'Emergency'
export type CycleCountState = 'Planned' | 'Counting' | 'Reviewed' | 'Posted'
export type ForecastMethod = 'Moving_Avg' | 'PM_Driven' | 'Failure_Rate' | 'Manual'
export type RecommendedAction = 'Hold' | 'Reorder' | 'ReduceMin' | 'Obsolete'

export interface Pagination {
  total: number; page: number; page_size: number; total_pages: number
}

export interface AllocationRow {
  name: string
  work_order_ref?: string
  work_order_doctype?: string
  asset?: string
  asset_name?: string
  warehouse_from?: string
  warehouse_name?: string
  requested_by?: string
  requested_by_name?: string
  requested_date?: string
  urgency: UrgencyLevel
  allocation_status: AllocationState
  total_value?: number
  stock_movement_ref?: string
}

export interface AllocationItem {
  spare_part: string
  part_name?: string
  qty_requested: number
  qty_approved?: number
  qty_issued?: number
  qty_returned?: number
  uom?: string
  batch_no?: string
  serial_no?: string
  unit_value?: number
  line_value?: number
  used_for?: string
  return_condition?: 'Good' | 'Damaged' | 'Used'
}

// Server-driven CTA (GATE-8/LL-FE-51 · CR-WF-15-ALLOC): BE `get_allocation` emit
// `allowed_transitions` = `_allocation_allowed_transitions(allocation_status)` — danh
// sách NEXT-STATE khả dụng theo status + capability. Detail view (backlog, xem dưới)
// gate nút theo `allowed_transitions.includes(<next-state>)`, KHÔNG hardcode
// `allocation_status === '...'`:
//   'Approved'  → nút "Duyệt"         (approveAllocation · Requested → Approved)
//   'Issued'    → nút "Xuất kho"      (issueAllocation   · Requested/Approved → Issued)
//   'Returned'  → nút "Trả phụ tùng"  (returnItems       · Issued → Returned)
//   'Cancelled' → nút "Hủy"           (cancelAllocation  · Requested/Approved/Picked → Cancelled)
// Khác `CycleCountDetail` (action-verb tokens 'Submit'/'Recount'/'Post'): allocation
// dùng NEXT-STATE strings (codomain ⊆ AllocationState) theo hợp đồng
// `_allocation_allowed_transitions`. Terminal (Returned/Cancelled) → []. Nhãn VI của
// từng NEXT-STATE đã có trong STATUS_MAP (utils/formatters.ts) — 0 rò status EN.
export interface AllocationDetail extends AllocationRow {
  items: AllocationItem[]
  notes?: string
  approval_required?: 0 | 1
  approved_by?: string
  approval_date?: string
  stock_movement_return_ref?: string
  audit_flags?: string
  docstatus?: 0 | 1 | 2
  allowed_transitions: AllocationState[]
}

export interface CycleCountRow {
  name: string
  warehouse: string
  warehouse_name?: string
  count_date: string
  count_type: string
  counted_by?: string
  counted_by_name?: string
  verified_by?: string
  verified_by_name?: string
  status: CycleCountState
  variance_count?: number
  variance_value?: number
}

export interface CycleCountItem {
  name?: string
  spare_part: string
  part_name?: string
  uom?: string
  system_qty: number
  counted_qty: number
  variance_qty?: number
  variance_pct?: number
  variance_value?: number
  root_cause?: string
  capa_required?: 0 | 1
  capa_ref?: string
  notes?: string
}

// Server-driven CTA (GATE-8/LL-FE-51): BE phát danh sách action verb khả dụng
// theo status + capability. FE gate nút theo đây, KHÔNG hardcode status===.
//   'Submit'  → submitCycleCount   (Planned/Counting → Reviewed)
//   'Recount' → recountCycleCount  (Reviewed → Counting — gửi về đếm lại)
//   'Post'    → postCycleCount     (Reviewed → Posted)
export type CycleCountAction = 'Submit' | 'Recount' | 'Post'

export interface CycleCountDetail extends CycleCountRow {
  items: CycleCountItem[]
  posted_movement_ref?: string
  adjustment_ref?: string
  capa_created?: number
  notes?: string
  docstatus?: 0 | 1 | 2
  allowed_transitions: CycleCountAction[]
}

export interface ForecastRow {
  name: string
  forecast_period: string
  period_start?: string
  period_end?: string
  method: ForecastMethod
  workflow_state?: string
  generated_by?: string
  generated_by_name?: string
  approved_by?: string
  approved_by_name?: string
  docstatus?: 0 | 1 | 2
}

export interface WatchlistRow {
  name: string
  watchlist_name?: string
  critical_asset: string
  critical_asset_name?: string
  spare_part: string
  part_name?: string
  warehouse: string
  warehouse_name?: string
  min_required_on_hand: number
  active?: 0 | 1
  last_breach_date?: string
  breach_count_30d?: number
}

export interface KpiValue { value: number; target?: number; target_min?: number; target_max?: number; status: 'green' | 'yellow' | 'red' }

export interface DashboardStats {
  period: string
  stock_turnover_year: KpiValue
  days_on_hand_avg: KpiValue
  stockout_incidents_30d: KpiValue
  critical_breach_hours_30d: KpiValue
  cycle_count_accuracy_pct: KpiValue
  forecast_mape_pct: KpiValue
  emergency_override_count_30d: KpiValue
  low_stock_alerts: number
  pending_allocations: number
  pending_cycle_counts: number
}

export interface LowStockAlert {
  spare_part: string
  part_name?: string
  warehouse: string
  warehouse_name?: string
  qty_on_hand: number
  min_stock_level: number
  imm_part_class?: string
  is_in_watchlist?: boolean
}

interface ListEnvelope<T> { data: T[]; pagination: Pagination }

// ─── Allocations ─────────────────────────────────────────────────────────────

export const listAllocations = (params: Record<string, unknown> = {}) =>
  frappeGet<ListEnvelope<AllocationRow>>(`${BASE}.list_allocations`, params)

export const getAllocation = (name: string) =>
  frappeGet<AllocationDetail>(`${BASE}.get_allocation`, { name })

export const createAllocation = (payload: {
  work_order_ref?: string
  asset?: string
  warehouse?: string
  urgency?: UrgencyLevel
  items: AllocationItem[]
}) =>
  frappePost<{ name: string; workflow_state: AllocationState }>(
    `${BASE}.create_allocation`,
    {
      work_order_ref: payload.work_order_ref ?? '',
      asset: payload.asset ?? '',
      warehouse: payload.warehouse ?? '',
      urgency: payload.urgency ?? 'Routine',
      items: JSON.stringify(payload.items),
    },
  )

export const approveAllocation = (allocation: string) =>
  frappePost<{ name: string; workflow_state: AllocationState }>(
    `${BASE}.approve_allocation`, { allocation },
  )

export const issueAllocation = (allocation: string) =>
  frappePost<{ name: string; workflow_state: AllocationState; stock_movement_ref?: string }>(
    `${BASE}.issue_allocation`, { allocation },
  )

export const returnItems = (
  allocation: string,
  items: Array<{ spare_part: string; qty_returned: number; return_condition?: string }>,
) =>
  frappePost<{ name: string; workflow_state: AllocationState; stock_movement_return_ref?: string }>(
    `${BASE}.return_items`, { allocation, items: JSON.stringify(items) },
  )

// ─── Cycle Counts ─────────────────────────────────────────────────────────────

export const listCycleCounts = (params: Record<string, unknown> = {}) =>
  frappeGet<ListEnvelope<CycleCountRow>>(`${BASE}.list_cycle_counts`, params)

export const getCycleCount = (name: string) =>
  frappeGet<CycleCountDetail>(`${BASE}.get_cycle_count`, { name })

export const createCycleCount = (payload: {
  warehouse: string
  spare_parts: string[]
  count_type?: string
  count_date?: string
}) =>
  frappePost<{ name: string; workflow_state: CycleCountState; items_count: number }>(
    `${BASE}.create_cycle_count`,
    {
      warehouse: payload.warehouse,
      spare_parts: JSON.stringify(payload.spare_parts),
      count_type: payload.count_type ?? 'Cycle',
      count_date: payload.count_date ?? '',
    },
  )

export const submitCycleCount = (
  count_name: string,
  counted_items: Array<{ spare_part: string; counted_qty: number; root_cause?: string }>,
) =>
  frappePost<{ name: string; workflow_state: CycleCountState; variance_count: number }>(
    `${BASE}.submit_cycle_count`,
    { count_name, counted_items: JSON.stringify(counted_items) },
  )

export const postCycleCount = (cycle_count: string, verified_by = '', notes = '') =>
  frappePost<{ name: string; workflow_state: CycleCountState; adjustment_ref: string; capa_created: number }>(
    `${BASE}.post_cycle_count`,
    { cycle_count, verified_by, notes },
  )

// Sửa đếm lại — gửi phiếu đã rà soát về Đang kiểm đếm (Reviewed → Counting).
// Envelope Decision-B parity postCycleCount; `reason` bắt buộc (BE cũng validate
// → IMM15_RECOUNT_REASON_REQUIRED). Cap `inventory.submit` (parity Post).
export const recountCycleCount = (name: string, reason: string) =>
  frappePost<{ name: string; workflow_state: CycleCountState }>(
    `${BASE}.recount_cycle_count`,
    { count_name: name, reason },
  )

// ─── Forecast ─────────────────────────────────────────────────────────────────

export const listSpareForecasts = (params: Record<string, unknown> = {}) =>
  frappeGet<ListEnvelope<ForecastRow>>(`${BASE}.list_spare_forecasts`, params)

export const generateSpareForecast = (horizon_months = 3, method: ForecastMethod = 'Moving_Avg', forecast_period = '') =>
  frappePost<{ name: string; forecast_period: string; workflow_state: string; items_count: number }>(
    `${BASE}.generate_spare_forecast`,
    { horizon_months, method, forecast_period },
  )

export const approveForecast = (forecast: string) =>
  frappePost<{ name: string; workflow_state: string; reorder_recommendations: number }>(
    `${BASE}.approve_forecast`, { forecast },
  )

// ─── Watchlist ────────────────────────────────────────────────────────────────

export const listWatchlist = (params: Record<string, unknown> = {}) =>
  frappeGet<ListEnvelope<WatchlistRow>>(`${BASE}.list_watchlist`, params)

export const addToWatchlist = (payload: {
  watchlist_name: string
  critical_asset: string
  spare_part: string
  min_required_on_hand: number
  warehouse: string
}) =>
  frappePost<{ name: string; active: boolean }>(`${BASE}.add_to_watchlist`, payload as unknown as Record<string, unknown>)

// ─── Availability / Dashboard ────────────────────────────────────────────────

export const checkPartAvailability = (
  warehouse: string,
  items: Array<{ spare_part: string; qty: number }>,
  include_alternatives = 0,
) =>
  frappeGet<{
    warehouse: string
    results: Array<{ spare_part: string; part_name?: string; qty_on_hand: number; available_qty: number; qty_needed: number; sufficient: boolean; imm_part_class?: string }>
    all_sufficient: boolean
  }>(`${BASE}.check_part_availability`, {
    warehouse, items: JSON.stringify(items), include_alternatives,
  })

export const getDashboardStats = (period = '') =>
  frappeGet<DashboardStats>(`${BASE}.get_dashboard_stats`, { period })

export const getLowStockAlerts = (warehouse = '') =>
  frappeGet<{ alerts: LowStockAlert[]; total: number }>(`${BASE}.get_low_stock_alerts`, { warehouse })
