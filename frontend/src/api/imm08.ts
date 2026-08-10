// Copyright (c) 2026, AssetCore Team
// API client cho Module IMM-08 — Preventive Maintenance

import { frappeGet, frappePost } from './helpers'
import type { AvailableAction } from './imm00'

// Re-export để consumer của IMM-08 (view/store/test) KHÔNG phải với sang api/imm00
// lấy shape dùng chung. KHÔNG khai lại interface — một shape = một khai báo (nguồn:
// `api/imm00.ts`, mirror schema OAS `AvailableAction`).
export type { AvailableAction }

export interface PMWorkOrder {
  name: string
  asset_ref: string
  asset_name: string
  asset_category: string
  risk_class: string
  pm_type: string
  wo_type: 'Preventive' | 'Corrective'
  status: 'Open' | 'In Progress' | 'Pending–Device Busy' | 'Overdue' | 'Completed' | 'Halted–Major Failure' | 'Cancelled'
  due_date: string | null
  scheduled_date: string | null
  completion_date: string | null
  assigned_to: string | null
  assigned_to_name?: string | null
  supervisor?: string | null
  supervisor_name?: string | null
  overall_result: 'Pass' | 'Pass with Minor Issues' | 'Fail' | null
  technician_notes: string
  pm_sticker_attached: boolean
  is_late: boolean
  /**
   * Live-truth quá hạn (CR-37 · BR-08-11 LIVE) — `get_pm_work_order` enrich detail
   * per-WO CÙNG predicate `_enrich_pm_overdue` của list-item:
   * `is_overdue = (status == Overdue) OR is_pm_overdue(status, due_date, today)`.
   * Banner/computed đọc `is_overdue ?? (status === 'Overdue')` (live ưu tiên,
   * fallback status thô — forward-compat: trước khi BE emit → undefined → fallback,
   * KHÔNG vỡ). Chặn badge Quá-hạn đọc cờ STORED `is_late`/`status` trễ 1 nhịp
   * scheduler (cận an-toàn người bệnh). BÊN CẠNH `is_late` (STORED — hoàn-thành-trễ,
   * quá khứ) — GIỮ nguyên. Optional. Đối xứng `is_sla_breached ?? sla_breached` (imm09).
   */
  is_overdue?: boolean
  duration_minutes: number | null
  source_pm_wo: string | null
  checklist_results: ChecklistResult[]
  /**
   * SSoT server-driven CTA (GATE-8 / LL-FE-51): danh sách trạng thái-đích hợp lệ
   * kế tiếp mà BE cho phép, do `get_pm_work_order` emit =
   * `_PM_VALID_TRANSITIONS.get(status, [])` (imm08.py:652). FE gate nút workflow bằng
   * `capability && allowed_transitions.includes('<đích>')` — KHÔNG tự suy diễn theo
   * `status === 'X'`. Chuỗi đích khớp EXACT PMStatus (en-dash: 'Halted–Major Failure',
   * 'Pending–Device Busy'). Terminal (Completed/Cancelled) → []. Optional (forward-compat).
   *
   * ⚠️ GIỮ NGUYÊN sau AC-CR-77 (back-compat A6): `available_actions` là SUPERSET,
   * KHÔNG thay thế. Đây vẫn là nguồn của các nút KHÔNG nằm trong 4 CTA (vd «Tiếp tục
   * bảo trì») và là đường FALLBACK khi worker BE chưa phát `available_actions`.
   */
  allowed_transitions?: string[]
  /**
   * AC-CR-77 — CTA SERVER-DRIVEN cho màn chi tiết phiếu PM. ĐÚNG 4 phần tử, thứ tự
   * CỐ ĐỊNH `[start_work, submit_result, reschedule, report_major_failure]`; mỗi phần
   * tử ánh xạ 1-1 tới endpoint CÓ THẬT của `assetcore/api/imm08.py`
   * (`assign_technician` · `submit_pm_result` · `reschedule_pm` · `report_major_failure`).
   *
   * • `enabled` = `transition_allowed ∩ has_cap ∩ business_gate` do SERVER quyết —
   *   FE KHÔNG nhân bản `can('pm.*') && allowed_transitions.includes(...)` cho 4 nút
   *   này (đó chính là nguồn "nút chết": bấm được nhưng BE từ chối).
   * • `reason` = chuỗi TIẾNG VIỆT server trả, bất biến D9: `enabled === false ⟺
   *   reason !== ""`. FE render nguyên văn làm tooltip — KHÔNG bịa chuỗi FE.
   * • `route` = "" (CTA mở modal tại chỗ, không điều hướng — khác imm00 scan CTA).
   * • `Cancelled` CÓ trong `_PM_VALID_TRANSITIONS` nhưng KHÔNG có endpoint ⇒ BE
   *   KHÔNG BAO GIỜ phát dưới dạng action (hết CTA ma trên màn chi tiết).
   *
   * Optional — CỐ Ý: worker BE chưa reload (`--preload` staleness) hoặc client cũ vẫn
   * trả shape CŨ ⇒ `undefined` ⇒ view rơi về đường FALLBACK (`allowed_transitions` +
   * capability), KHÔNG nút nào biến mất, KHÔNG màn trắng.
   */
  available_actions?: AvailableAction[]
}

export interface ChecklistResult {
  idx: number
  checklist_item_idx: number
  description: string
  measurement_type: 'Pass/Fail' | 'Numeric' | 'Text'
  unit: string
  result: 'Pass' | 'Fail–Minor' | 'Fail–Major' | 'N/A' | null
  measured_value: number | null
  notes: string
  photo: string | null
}

export interface PMCalendarEvent {
  name: string
  asset_ref: string
  asset_name: string
  pm_type: string
  due_date: string
  status: string
  assigned_to: string | null
  is_late: boolean
}

export interface PMDashboardStats {
  kpis: {
    // Phạm-vi-tháng (INV-PM-KPI-3): null khi total_scheduled==0 (chưa có lịch PM
    // trong tháng) → FE render '—' thay vì 0% gây hiểu nhầm "không tuân thủ".
    compliance_rate_pct: number | null
    total_scheduled: number
    completed_on_time: number
    // Overdue ∧ due_date ∈ tháng đang xem — subset của total_scheduled, đối-soát
    // được với strip tháng (INV-PM-KPI-1).
    overdue_in_month: number
    // WO trong tháng chưa hoàn thành & chưa quá hạn (Open/In Progress).
    pending_in_month: number
    // Toàn-hệ-thống (INV-PM-KPI-2 / RC-10): count global status==Overdue, khớp
    // launcher widget + drill ?overdue=1. KHÔNG bó trong tháng.
    overdue: number
    avg_days_late: number
  }
  trend_6months: Array<{
    month: string
    total: number
    on_time: number
    rate: number
  }>
}

export interface PMListResponse {
  data: PMWorkOrder[]
  pagination: { page: number; page_size: number; total: number; total_pages: number }
}

const BASE = '/api/method/assetcore.api.imm08'

export function listPMWorkOrders(
  filters = {}, page = 1, pageSize = 20, search?: string,
): Promise<PMListResponse> {
  const params: Record<string, unknown> = {
    filters: JSON.stringify(filters),
    page,
    page_size: pageSize,
  }
  // CR-18: tìm kiếm free-text server-side (mã phiếu / mã thiết bị / tên thiết bị).
  // CHỈ gửi khi non-empty ⇒ absent = baseline byte-identical (BE bỏ qua search rỗng).
  if (search && search.trim()) params.search = search.trim()
  return frappeGet<PMListResponse>(`${BASE}.list_pm_work_orders`, params)
}

export function getPMWorkOrder(name: string): Promise<PMWorkOrder> {
  return frappeGet<PMWorkOrder>(`${BASE}.get_pm_work_order`, { name })
}

export function assignTechnician(
  name: string,
  technician: string,
  scheduledDate?: string,
): Promise<{ name: string; status: string }> {
  return frappePost<{ name: string; status: string }>(
    `${BASE}.assign_technician`,
    { name, technician, scheduled_date: scheduledDate },
  )
}

export async function submitPMResult(payload: {
  name: string
  checklist_results: ChecklistResult[]
  overall_result: string
  technician_notes: string
  pm_sticker_attached: boolean
  duration_minutes: number
}): Promise<{ name: string; new_status: string; is_late: boolean; next_pm_date: string; cm_wo_created: string | null }> {
  return frappePost<{ name: string; new_status: string; is_late: boolean; next_pm_date: string; cm_wo_created: string | null }>(
    `${BASE}.submit_pm_result`,
    {
      ...payload,
      checklist_results: JSON.stringify(payload.checklist_results),
      pm_sticker_attached: payload.pm_sticker_attached ? 1 : 0,
    },
  )
}

// Envelope khớp BE ReportMajorFailureResponse (services/imm08.py report_major_failure) —
// 4-key EXACT. `new_status` là PMStatus kỹ-thuật ('Halted–Major Failure') → KHÔNG render thô;
// view re-fetch WO rồi map qua STATUS_LABEL. Giữ ở type cho parity contract (FE từng đọc 3-key).
export interface ReportMajorFailureResult {
  pm_wo: string
  new_status: PMWorkOrder['status']
  cm_wo_created: string
  asset_status: string
}

export function reportMajorFailure(
  pmWoName: string,
  failureDescription: string,
): Promise<ReportMajorFailureResult> {
  // BE đã VERB-FLIP @frappe.whitelist(methods=["POST"]) — frappePost giữ tương thích (GET sẽ 405).
  return frappePost<ReportMajorFailureResult>(
    `${BASE}.report_major_failure`,
    { pm_wo_name: pmWoName, failure_description: failureDescription },
  )
}

export function getPMCalendar(
  year: number,
  month: number,
  assetRef?: string,
): Promise<{
  month: string
  events: PMCalendarEvent[]
  summary: { total: number; completed: number; overdue: number; pending: number }
}> {
  return frappeGet<{
    month: string
    events: PMCalendarEvent[]
    summary: { total: number; completed: number; overdue: number; pending: number }
  }>(`${BASE}.get_pm_calendar`, { year, month, asset_ref: assetRef })
}

export function getPMDashboardStats(year?: number, month?: number): Promise<PMDashboardStats> {
  return frappeGet<PMDashboardStats>(`${BASE}.get_pm_dashboard_stats`, { year, month })
}

export function reschedulePM(
  name: string,
  newDate: string,
  reason: string,
): Promise<{ name: string; old_date: string; new_date: string }> {
  return frappePost<{ name: string; old_date: string; new_date: string }>(
    `${BASE}.reschedule_pm`,
    { name, new_date: newDate, reason },
  )
}

/**
 * Một dòng lịch sử bảo trì của thiết bị — mirror ĐÚNG `fields=[...]` mà BE
 * `services/imm08.py::get_asset_history` chọn trên **`PM Task Log`** (10 field).
 *
 * ⚠️ KHÔNG phải `PMWorkOrder` (kiểu cũ khai sai, AC-CR-102): đây là bản ghi
 * NHẬT KÝ TÁC VỤ, có `pm_work_order`/`technician`/`days_late`/`next_pm_date`/
 * `summary` mà `PMWorkOrder` KHÔNG có, và KHÔNG có `status`/`asset_name`/
 * `checklist_results`/`due_date` mà `PMWorkOrder` hứa. Khai `PMWorkOrder[]` là
 * hứa thừa ⇒ view đọc `row.status` compile XANH rồi `undefined` lúc chạy.
 *
 * `PM Task Log` KHÔNG có màn chi tiết ⇒ liên kết dòng phải dựng từ
 * **`pm_work_order`** (doctype `PM Work Order`), TUYỆT ĐỐI không từ `name`.
 * `pm_work_order` có thể rỗng (Link nullable) ⇒ caller render text tĩnh.
 *
 * `is_late` là Check ⇒ int 0/1 (KHÔNG bool) — đọc `Number(is_late) === 1`.
 * `technician` là Link `User` và BE KHÔNG kèm `technician_name` ⇒ **KHÔNG render
 * thô** (rò mã/email người dùng — GATE-2); chờ BE bổ sung companion field.
 */
export interface PMTaskLogHistoryItem {
  /** Mã bản ghi `PM Task Log` — dùng làm `:key`, KHÔNG dùng dựng URL chi tiết. */
  name: string
  /** Mã `PM Work Order` nguồn — SSoT để mở đúng bản ghi. Rỗng/null = không có link. */
  pm_work_order: string | null
  pm_type: string | null
  completion_date: string | null
  /** Link `User` — KHÔNG render thô (thiếu `technician_name` companion). */
  technician: string | null
  /** Select `Pass` / `Pass with Minor Issues` / `Fail` — render qua `overallResultLabel`. */
  overall_result: string | null
  /** Check → 0/1. */
  is_late: 0 | 1
  days_late: number | null
  next_pm_date: string | null
  summary: string | null
}

/**
 * Lịch sử bảo trì định kỳ của 1 thiết bị (cắt cứng theo `limit`, KHÔNG phân trang).
 *
 * Hợp đồng cắt danh sách TRUNG THỰC (CR-69, cùng SSoT `services/shared/truncation.py`
 * với CR-43/46/47): `total` = COUNT DB thật trên ĐÚNG filter-set `{asset_ref}`
 * @`PM Task Log` TRƯỚC khi cắt; `truncated` = int 0/1 (parity CR-01 — KHÔNG bool,
 * KHÔNG None; tránh trap int-vs-bool khi codegen Dart/Kotlin) = `len(history) >= limit
 * ∧ total > limit`. Vừa khít trần (`total == limit`) ⇒ `truncated === 0` (không báo
 * cắt oan).
 *
 * ⚠️ Cả hai OPTIONAL — CỐ Ý. Trước CR-69 kiểu này khai `total: number` NON-optional
 * trong khi BE CHƯA BAO GIỜ trả khoá đó ⇒ `undefined` lúc chạy mà TS không cảnh báo
 * (chính class-of-bug mà CR-69 dẹp). Worker BE chưa reload (`--preload` staleness)
 * vẫn trả shape CŨ thiếu 2 khoá → caller PHẢI đọc phòng thủ
 * (`total ?? history.length`, `truncated ?? 0`). `asset_ref`/`history` GIỮ NGUYÊN.
 */
export function getAssetPMHistory(
  assetRef: string,
  limit = 10,
): Promise<{ asset_ref: string; history: PMTaskLogHistoryItem[]; total?: number; truncated?: 0 | 1 }> {
  return frappeGet<{ asset_ref: string; history: PMTaskLogHistoryItem[]; total?: number; truncated?: 0 | 1 }>(
    `${BASE}.get_asset_pm_history`,
    { asset_ref: assetRef, limit },
  )
}

export async function createAdhocPMWorkOrder(data: {
  asset_ref: string
  pm_schedule: string
  due_date: string
  assigned_to?: string
  supervisor?: string
  technician_notes?: string
}): Promise<{ name: string }> {
  return frappePost<{ name: string }>(`${BASE}.create_pm_work_order`, data as Record<string, unknown>)
}
