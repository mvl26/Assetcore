// Copyright (c) 2026, AssetCore Team
// IMM-12 — Incident workflow API client

import { frappeGet, frappePost, type ApiResponse } from './helpers'
import axiosClient from './axios'
import { ApiError, ErrorCode, type ErrorCodeType } from './errors'

const BASE = '/api/method/assetcore.api.imm12'

// Số ảnh hiện trường tối đa cho 1 phiếu sự cố — KHỚP MAX_INCIDENT_PHOTOS ở BE
// (services/imm12.py) + app mobile (CR-17/G6). Đổi 1 nơi phải đổi cả 3.
export const MAX_INCIDENT_PHOTOS = 5

// Ảnh hiện trường (bằng chứng NĐ98) đính vào phiếu sự cố — mirror payload BE
// attach_incident_photo (Decision-B data) + phần tử scene_photos ở get_incident_detail.
export interface ScenePhoto {
  file_url: string
  file_name: string
}

export interface IncidentDetail {
  name: string
  asset: string
  asset_name?: string
  incident_type: string
  severity: 'Low' | 'Medium' | 'High' | 'Critical'
  // Khớp _STATUS_* trong services/imm12.py (ground truth).
  status: 'Open' | 'Acknowledged' | 'In Progress' | 'RCA Required' | 'Resolved' | 'Closed' | 'Cancelled'
  description: string
  immediate_action?: string
  resolution_notes?: string
  root_cause_summary?: string
  reported_by?: string
  reported_at?: string
  patient_affected?: number
  patient_impact_description?: string
  reported_to_byt?: number
  byt_report_date?: string
  linked_repair_wo?: string
  linked_capa?: string
  closed_date?: string
  docstatus?: number
  allowed_transitions?: string[]
  fault_code?: string
  workaround_applied?: number
  rca_required?: number
  rca_record?: string
  chronic_failure_flag?: number
  clinical_impact?: string
  // BR-12-09: cờ vi phạm SLA THÔ (stamped-by-scheduler, bền DB). GIỮ cho write-path
  // + escalation idempotent (BR-12-08/09). KHÔNG dùng trực tiếp để render badge —
  // undercount trong cửa-sổ-trễ-scheduler (quá hạn nhưng cờ chưa stamp = 0).
  response_breached?: number
  resolution_breached?: number
  // BR-12-13: cờ vi phạm SLA DERIVED LIVE từ BE (_row_is_breached) = (cờ-thô=1) OR
  // (đang-mở ∧ quá-hạn). FE badge ĐỌC field này thay cờ thô → hiện cho incident
  // currently-overdue-open kể cả khi cờ DB còn 0. Badge live == tile (cùng SoT
  // sla_breach_filter ở get_incident_stats). optional: forward-compat khi BE chưa ship.
  is_response_breached?: number
  is_resolution_breached?: number
  // Hạn SLA (đối xứng IncidentListItem). CHỈ để hiển thị thông tin nếu cần —
  // TUYỆT ĐỐI KHÔNG dùng để tự tính breach ở client (overdue_server_flag SSoT:
  // breach chỉ đọc is_*_breached / *_breached derived server-side).
  response_due_at?: string
  resolution_due_at?: string
  rca?: { name: string; status: string; root_cause?: string }
  // Ảnh hiện trường đã đính (bằng chứng NĐ98) — parity chi tiết mobile + web.
  // BE get_incident_detail luôn trả list (rỗng khi chưa có ảnh). optional: forward-compat
  // khi BE chưa ship endpoint đính ảnh → section render empty-state.
  scene_photos?: ScenePhoto[]
}

export interface RCADetail {
  name: string
  incident_report: string
  asset?: string
  status: 'RCA Required' | 'RCA In Progress' | 'Completed' | 'Cancelled'
  rca_method?: string
  trigger_type?: string
  assigned_to?: string
  due_date?: string
  incident_count?: number
  root_cause?: string
  corrective_action_summary?: string
  preventive_action_summary?: string
  contributing_factors?: string
  rca_notes?: string
  linked_capa?: string
  completed_by?: string
  completed_date?: string
  incident_severity?: string
  five_why_steps?: Array<{ why_number: number; why_question: string; why_answer: string }>
  // GATE-8/LL-FE-51: CTA workflow SERVER-DRIVEN. BE get_rca emit
  // allowed_transitions = _RCA_VALID_TRANSITIONS.get(status, []) (đích hợp lệ theo
  // status hiện tại) + can_manage_rca (int 0/1 theo capability corrective) — parity
  // get_work_order (imm09). FE gate nút = (can_manage_rca && allowed_transitions
  // .includes('<đích>')), KHÔNG hardcode `status === 'X'`. optional: forward-compat
  // khi BE chưa ship → view fallback allowed=[]·canManage=false (0 CTA an toàn).
  allowed_transitions?: string[]
  can_manage_rca?: 0 | 1
}

export interface ChronicFailure {
  asset: string
  asset_name?: string
  fault_code: string
  count: number
  incident_count?: number
  last_reported?: string
}

// Khớp services/imm12.py::get_incident_stats (ground truth).
export interface IncidentStats {
  total: number
  open: number
  // BR-12-11 (round-21): tổng incident ở MỌI state mở của SoT open_incident_filter()
  // {Open, Acknowledged, In Progress, RCA Required} — KHÁC `open` (chỉ status=='Open').
  // optional: forward-compat khi BE chưa ship; card "Đang mở" fallback 0.
  open_total?: number
  investigating: number
  resolved: number
  closed: number
  cancelled: number
  critical: number
  high: number
  // Open-set severity (KPI strip worklist): == _count(open_incident_filter() ∧
  // {severity}) — loại Closed/Cancelled/Resolved. optional: forward-compat khi BE
  // chưa ship → strip fallback `?? 0`. KHÁC critical/high global (mọi status).
  critical_open?: number
  high_open?: number
  rca_pending: number
  // BR-12-12: SỐ NHÓM (asset,fault_code) đang lặp lại LIVE trong cửa sổ 90 ngày
  // (== len(get_chronic_failures()) qua chronic_failure_count() ở BE), KHÔNG đếm cờ
  // stale chronic_failure_flag. Shape giữ `number` — chỉ NGỮ NGHĨA đổi (live thay stale).
  // Invariant get_dashboard(): stats.chronic == len(chronic_failures) (cùng SoT).
  chronic: number
  // BR-12-09: số incident có cờ vi phạm SLA (cùng predicate cờ với badge ở list).
  sla_response_breached: number
  sla_resolution_breached: number
}

export interface RcaListItem {
  name: string
  incident_report?: string
  asset?: string
  asset_name?: string
  rca_method?: string
  trigger_type?: string
  status: string
  assigned_to?: string
  assigned_to_name?: string
  due_date?: string
  linked_capa?: string
  completed_date?: string
}

export function listIncidents(params: {
  status?: string
  severity?: string
  asset?: string
  // open=1 áp SoT open_incident_filter() (incident đang mở) cho drill-down từ
  // dashboard donut/card → count == số dòng list. status đơn lẻ ưu tiên hơn open.
  open?: 0 | 1
  page?: number
  page_size?: number
} = {}) {
  return frappeGet<{ pagination: { total: number; page: number; page_size: number; total_pages: number }; items: IncidentDetail[] }>(
    `${BASE}.list_incidents`, params as Record<string, unknown>,
  )
}

export function getIncident(name: string) {
  return frappeGet<IncidentDetail>(`${BASE}.get_incident`, { name })
}

/**
 * Đính 1 ảnh hiện trường (bằng chứng NĐ98) vào phiếu sự cố qua multipart/form-data.
 * Mirror pattern upload của imm00.ts::uploadDeviceModelFile — POST FormData thẳng vào
 * endpoint AssetCore whitelisted (KHÔNG /api/method/upload_file trần) để BE gate quyền
 * (reporter HOẶC incident.write, IDOR-guard AUTH-10) + sinh Lifecycle Event 'incident_photo_attached'.
 *
 * Server-authoritative:
 *  - success:true → { file_url, file_name } của File private vừa sinh.
 *  - success:false → throw ApiError giữ `code` (FORBIDDEN/VALIDATION) + `fields.file`
 *    (thông điệp VN, vd 'Tối đa 5 ảnh') để view render lỗi inline dưới control.
 *
 * IDEMPOTENCY-PHOTO-CR24 (B-rel-3, parity report_incident): `clientRequestId` là
 * key idempotency do client sinh (field body `client_request_id`, khớp signature BE
 * attach_incident_photo). Cùng key + cùng incident + cùng session → BE dedupe: trả
 * File ĐÃ đính (name/file_url khớp lần 1), KHÔNG insert mới — đóng cửa sổ
 * attachment-dup khi retry sau lỗi mạng. Rỗng/absent → behavior at-least-once cũ
 * (mỗi lần gọi tạo File mới). Call-site sinh key 1 lần per-file (crypto.randomUUID)
 * và GIỮ NGUYÊN key khi retry cùng file.
 */
export async function attachIncidentPhoto(
  incidentName: string,
  file: File,
  clientRequestId = '',
): Promise<ScenePhoto> {
  const form = new FormData()
  form.append('incident_name', incidentName)
  form.append('file', file, file.name)
  // AC3 backward-compat: chỉ gửi field khi có key — rỗng thì FormData KHÔNG có
  // field client_request_id (BE giữ nguyên nhánh at-least-once cũ).
  if (clientRequestId) form.append('client_request_id', clientRequestId)
  // axios v1 tự set Content-Type multipart + boundary khi data là FormData; khai báo
  // 'multipart/form-data' để override default 'application/json' của instance.
  const res = await axiosClient.post<{ message: ApiResponse<ScenePhoto> & Record<string, unknown> }>(
    `${BASE}.attach_incident_photo`,
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
  const env = res.data?.message
  // Decision-B envelope lỗi HỢP LỆ = { success:false, code, error, fields? } (utils/
  // response._err LUÔN kèm `code` string) → thông điệp VN đã curate ở BE (vd 'Tối đa 5
  // ảnh') an toàn để echo + render inline dưới control.
  if (env && env.success === false && typeof env.code === 'string') {
    throw new ApiError((env.error as string) || 'Không thể đính ảnh hiện trường', {
      code: env.code as ErrorCodeType,
      httpStatus: (env.http_status as number | undefined) ?? 0,
      fields: env.fields as Record<string, string> | undefined,
    })
  }
  // Finding C (2026-07-09): bất kỳ shape KHÔNG phải Decision-B success (thiếu env /
  // success!=true / thiếu file_url / body lỗi thô Frappe {exc/exception}) → thông điệp
  // máy chủ chung. TUYỆT ĐỐI KHÔNG echo env.error/exc/traceback thô ra UI. (500 thật đã
  // bị interceptor axios chặn thành ApiError chung trước khi tới đây.)
  if (!env || env.success !== true || !env.data?.file_url) {
    throw new ApiError('Có lỗi máy chủ, vui lòng thử lại.', {
      code: ErrorCode.INTERNAL_ERROR,
      httpStatus: 500,
    })
  }
  return env.data
}

export function acknowledgeIncident(name: string, notes = '', assigned_to = '') {
  return frappePost<{ name: string; status: string }>(
    `${BASE}.acknowledge_incident`, { name, notes, assigned_to },
  )
}

// D3: Acknowledged → In Progress ("Bắt đầu xử lý")
export function startWork(name: string, notes = '') {
  return frappePost<{ name: string; status: string }>(
    `${BASE}.start_work`, { name, notes },
  )
}

export function resolveIncident(name: string, resolution_notes: string, root_cause = '') {
  return frappePost<{ name: string; status: string; linked_capa?: string }>(
    `${BASE}.resolve_incident`, { name, resolution_notes, root_cause },
  )
}

export function closeIncident(name: string, verification_notes = '') {
  return frappePost<{ name: string; status: string; closed_date?: string }>(
    `${BASE}.close_incident`, { name, verification_notes },
  )
}

export function getIncidentStats() {
  return frappeGet<IncidentStats>(`${BASE}.get_incident_stats`)
}

export interface ReportIncidentPayload {
  asset: string
  incident_type: string
  severity: string
  description: string
  fault_code?: string
  workaround_applied?: number
  clinical_impact?: string
  patient_affected?: number
  patient_impact_description?: string
  immediate_action?: string
  linked_repair_wo?: string
  /** L-19: thời điểm sự cố THỰC SỰ xảy ra (có thể trước lúc báo). Rỗng → BE
   *  fallback = reported_at (now); ở tương lai → BE chặn (IMM12_OCCURRED_DATETIME_FUTURE). */
  occurred_datetime?: string
  /** Nguồn gốc báo sự cố — provenance audit (mirror BE contract):
   *  'qr-scan' khi điều hướng từ màn quét QR, 'manual' (mặc định) khi tạo thủ công. */
  source?: 'manual' | 'qr-scan'
}

export function reportIncident(data: ReportIncidentPayload) {
  return frappePost<{ name: string; status: string; severity: string }>(
    `${BASE}.report_incident`, data as unknown as Record<string, unknown>,
  )
}

export function cancelIncident(name: string, reason: string) {
  return frappePost<{ name: string; status: string }>(
    `${BASE}.cancel_incident`, { name, reason },
  )
}

// BR-12-23 / CR-WF-12 — "Mở lại điều tra": Resolved → In Progress. Mirror BE
// reopen_incident(name, reason) (naming contract; POST envelope Decision-B, parity
// cancelIncident). `reason` BẮT BUỘC — BE nthrow IMM12_REOPEN_REASON_REQUIRED (422)
// khi rỗng, IMM12_BAD_STATE (409) khi status ≠ Resolved. Cap incident.close (parity
// Close). FE gate CTA bằng allowed_transitions.includes('In Progress') (server-driven,
// GATE-8/LL-FE-51) — KHÔNG hardcode role-name/status.
export function reopenIncident(name: string, reason: string) {
  return frappePost<{ name: string; status: string }>(
    `${BASE}.reopen_incident`, { name, reason },
  )
}

export function createRca(incident_name: string, rca_method = '5-Why') {
  return frappePost<{ name: string; status: string }>(
    `${BASE}.create_rca`, { incident_name, rca_method },
  )
}

// CR-WF-12-RCA-ENTRY — "Yêu cầu phân tích nguyên nhân gốc": Resolved → RCA Required.
// Surface CTA cho cạnh workflow THẬT `Resolved → RCA Required` (action 'Yêu cầu RCA',
// ∈ _VALID_TRANSITIONS[Resolved]) đang advertise trong allowed_transitions nhưng
// trước đây KHÔNG có driver → dead-CTA. Mirror BE request_rca(name, rca_reason)
// (naming contract; POST envelope Decision-B, parity reopenIncident/createRca): BE
// apply_workflow(action='Yêu cầu RCA') sync status='RCA Required' + tạo/link RCA
// Record (reuse create_rca, idempotent) + audit IMM Audit Trail (Resolved→RCA
// Required, reason). Precondition status != 'Resolved' → 422 (message VN đã curate ở
// BE). Cap-gate == workflow 'Yêu cầu RCA' role-set {Compliance Manager, System
// Manager, AssetCore Super Admin}; thiếu quyền → 403 (KHÔNG leak raw cap). FE gate
// CTA bằng (can(corrective.write) ∧ status==='Resolved' ∧ allowed_transitions
// .includes('RCA Required')) — server-driven (GATE-8/LL-FE-51), KHÔNG hardcode
// role-name. Response echo rca_record để view có thể điều hướng nếu cần.
export function requestRca(name: string, rcaReason = '') {
  return frappePost<{ name: string; status: string; rca_record?: string }>(
    `${BASE}.request_rca`, { name, rca_reason: rcaReason },
  )
}

export function getRca(name: string) {
  return frappeGet<RCADetail>(`${BASE}.get_rca`, { name })
}

export function listRcas(params: {
  method?: string
  status?: string
  asset?: string
  page?: number
  page_size?: number
} = {}) {
  return frappeGet<{ pagination: { total: number; page: number; page_size: number; total_pages: number }; items: RcaListItem[] }>(
    `${BASE}.list_rcas`, params as Record<string, unknown>,
  )
}

export interface SubmitRcaPayload {
  name: string
  root_cause: string
  corrective_action: string
  preventive_action?: string
  five_why_steps?: Array<{ why_number: number; why_question: string; why_answer: string }>
  rca_notes?: string
}

export function submitRca(data: SubmitRcaPayload) {
  const { five_why_steps, ...rest } = data
  return frappePost<{ name: string; status: string; linked_capa?: string }>(
    `${BASE}.submit_rca`,
    { ...rest, five_why_steps: JSON.stringify(five_why_steps ?? []) } as unknown as Record<string, unknown>,
  )
}

// GATE-8/LL-FE-51 — 2 transition mới (server-driven CTA). Đi qua frappePost →
// axios interceptor sẵn có (401/403 redirect, ApiError giữ message VN đã curate ở
// BE). TUYỆT ĐỐI KHÔNG echo traceback: view chỉ đọc ApiError.message.

/** RCA Required → RCA In Progress ("Bắt đầu phân tích"). Mirror BE start_rca(name). */
export function startRca(name: string) {
  return frappePost<{ name: string; status: string }>(
    `${BASE}.start_rca`, { name },
  )
}

/** RCA Required|RCA In Progress → Cancelled ("Hủy RCA"). Mirror BE cancel_rca(name, reason). */
export function cancelRca(name: string, reason = '') {
  return frappePost<{ name: string; status: string }>(
    `${BASE}.cancel_rca`, { name, reason },
  )
}

export function getAssetIncidentHistory(asset: string, limit = 10) {
  return frappeGet<{ asset: string; items: IncidentDetail[] }>(
    `${BASE}.get_asset_incident_history`, { asset, limit },
  )
}

export function getChronicFailures() {
  return frappeGet<{ items: ChronicFailure[] }>(`${BASE}.get_chronic_failures`)
}

export interface DashboardStats {
  total: number
  open: number
  // BR-12-11 (round-21): xem IncidentStats.open_total. get_dashboard().stats ==
  // get_incident_stats() nên cùng shape.
  open_total?: number
  investigating: number
  resolved: number
  closed: number
  cancelled: number
  critical: number
  high: number
  // Open-set severity — xem IncidentStats.critical_open. get_dashboard().stats ==
  // get_incident_stats() nên cùng shape (strip có thể đọc từ dashboard payload).
  critical_open?: number
  high_open?: number
  rca_pending: number
  // BR-12-12: xem IncidentStats.chronic — số nhóm chronic LIVE 90d (chronic_failure_count).
  // get_dashboard().stats == get_incident_stats() ⇒ stats.chronic == len(chronic_failures).
  chronic: number
  // BR-12-09: số incident vi phạm SLA (get_dashboard.stats = get_incident_stats).
  sla_response_breached: number
  sla_resolution_breached: number
}

export interface DashboardData {
  stats: DashboardStats
  active_incidents: IncidentDetail[]
  open_rcas: RCADetail[]
  chronic_failures: ChronicFailure[]
}

export function getDashboard() {
  return frappeGet<DashboardData>(`${BASE}.get_dashboard`)
}
