// Copyright (c) 2026, AssetCore Team
// API client cho Module IMM-09 — Corrective Maintenance

import { frappeGet, frappePost, type ApiResponse } from './helpers'
import axiosClient from './axios'
import { ApiError, ErrorCode, type ErrorCodeType } from './errors'
import type { AvailableAction } from './imm00'

// Re-export để consumer của IMM-09 (view/store/test) KHÔNG phải với sang api/imm00
// lấy shape dùng chung. KHÔNG khai lại interface — một shape = một khai báo (nguồn:
// `api/imm00.ts`, mirror schema OAS `AvailableAction`; IMM-08 làm y hệt sau AC-CR-77).
export type { AvailableAction }

export interface AssetRepair {
  name: string
  asset_ref: string
  asset_name: string
  asset_category: string
  risk_class: string
  /**
   * CR-51 — phơi TOP-LEVEL từ `get_repair_work_order` = verbatim
   * `AC Asset.risk_classification` ∈ {Low, Medium, High, Critical, ''}. Đây là
   * PHÂN LOẠI RỦI RO THIẾT BỊ (NĐ98) — nhãn hiển thị 'Phân loại rủi ro' map qua
   * SSoT `riskClassificationLabel` (Thấp/Trung bình/Cao/Nghiêm trọng). KHÁC hoàn
   * toàn với `risk_class` (Class I/II/III) ở trên — đó là đầu vào ma trận SLA, KHÔNG
   * render cho người dùng. Asset chưa phân loại → '' (KHÔNG suy diễn, KHÔNG default).
   * Optional (forward-compat: trước khi BE flatten → undefined; view fallback
   * `asset_info.risk_classification` là cùng giá trị nguồn, KHÔNG vỡ).
   */
  risk_classification?: string
  department_name?: string
  location_name?: string
  asset_info?: AssetInfo
  serial_no: string
  repair_type: 'Corrective' | 'Breakdown' | 'Warranty Repair'
  priority: 'Normal' | 'Urgent' | 'Emergency'
  status: 'Open' | 'Assigned' | 'Diagnosing' | 'Pending Parts' | 'In Repair' | 'Pending Inspection' | 'Completed' | 'Cannot Repair' | 'Cancelled'
  open_datetime: string | null
  assigned_datetime: string | null
  completion_datetime: string | null
  assigned_to: string | null
  assigned_to_name?: string | null
  assigned_by: string | null
  mttr_hours: number | null
  sla_target_hours: number | null
  sla_breached: boolean
  /**
   * BR-09-10 / INV-CM-HOLD — đồng hồ SLA/MTTR DỪNG khi WO nằm 'Pending Parts'
   * (chờ phụ tùng hết kho — blocker cung ứng ngoài tầm đội sửa). BE là SoT:
   * `repair_elapsed_hours = (until − open) − parts_hold_hours`. FE chỉ RENDER
   * verbatim (KHÔNG tự tính lại): `mttr_hours` ở trên đã = elapsed-trừ-hold do BE chốt.
   *
   * `parts_hold_hours`   = tổng số giờ WO đã nằm Pending Parts (cộng dồn mọi chu kỳ hold).
   * `parts_hold_started` = mốc VÀO Pending Parts của chu kỳ hold đang mở (null nếu không hold).
   *
   * Cả 2 read-only + optional (forward-compat: trước khi BE enrich → undefined,
   * badge "Chờ phụ tùng — SLA tạm dừng" vẫn render vì gate theo `status`, KHÔNG vỡ).
   */
  parts_hold_hours?: number
  parts_hold_started?: string | null
  /**
   * Live-truth vượt SLA (BR-09-07 LIVE) — BE `list_repair_work_orders` enrich
   * per-row: `bool(sla_breached) || _row_is_live_overdue(open & vượt hạn & cờ chưa stamp)`.
   * Badge/computed đọc `is_sla_breached ?? sla_breached` (live ưu tiên, fallback cờ thô —
   * forward-compat: trước khi BE enrich, undefined → fallback cờ thô, KHÔNG vỡ). Optional.
   */
  is_sla_breached?: boolean
  is_repeat_failure: boolean
  incident_report: string | null
  source_pm_wo: string | null
  diagnosis_notes: string
  root_cause_category: string
  repair_summary: string
  firmware_updated: boolean
  firmware_change_request: string | null
  dept_head_name: string
  total_parts_cost: number
  spare_parts_used: SparePartRow[]
  /**
   * AC-CR-78 / INV-PARTS-1 — SỐ DÒNG vật tư chưa có phiếu xuất kho HỢP LỆ
   * (= số dòng `stock_entry_ok === 0`, gộp cả `MISSING` lẫn `NOT_FOUND`).
   * Invariant BE: `= 0` ⟺ validator BR-09-02 KHÔNG chặn submit ⇒ FE cảnh báo TRƯỚC
   * khi người dùng bấm hoàn tất thay vì để họ ăn 422 tại `on_submit`.
   * Optional (worker chưa reload → undefined → KHÔNG hiện dải cảnh báo, KHÔNG vỡ).
   */
  parts_pending_stock_entry?: number
  repair_checklist: RepairChecklistRow[]
  /**
   * AC-CR-84 — CỔNG ẢNH BẰNG CHỨNG NĐ98 (đóng mobile CR-51, kèm CR-15). Cổng CÓ ÁP DỤNG
   * cho phiếu này hay không: `1` ⟺ `risk_classification` ∈ {High, Critical} (nhóm nguy cơ
   * cao). INTEGER `0|1` — KHÔNG boolean (quirk CR-01 / LL-BE-50: hợp đồng mobile khai
   * integer; codegen Dart/Kotlin parse-fail nếu server phát true/false).
   *
   * ⚠️ Nguồn DUY NHẤT là `risk_classification` (verbatim `AC Asset.risk_classification`),
   * KHÔNG phải `risk_class` (Class I/II/III — đầu vào ma trận SLA; ánh xạ MẤT MÁT: High và
   * Critical cùng ra Class III, thiết bị CHƯA phân loại mặc định Class II). Chính vì suy từ
   * `risk_class` mà cổng ảnh trước đây là CODE CHẾT trên client (LL-BE-58).
   * Chuỗi rỗng '' (chưa phân loại) ⇒ `0` — 'chưa phân loại' KHÔNG suy thành nguy cơ cao.
   *
   * Optional — CỐ Ý (forward-compat, bài học CR-69 / AC-CR-82): worker BE chưa reload ⇒
   * `undefined` ⇒ FE ẩn TOÀN BỘ khối bằng chứng (KHÔNG khẳng định "đã đủ ảnh", cũng KHÔNG
   * suy "không có cổng" — cổng an toàn nằm ở SERVER, client chỉ HIỂN THỊ).
   */
  evidence_photo_required?: 0 | 1
  /**
   * AC-CR-84 / INV-CMEVID-1 — tập `idx` (1-based, CÙNG khoá `repair_checklist[].idx` dùng
   * làm `checklist_item_idx` của `attach_repair_checklist_photo`) các mục nghiệm thu CÒN
   * THIẾU ảnh bằng chứng. Đây là ĐÚNG tập mà `close_work_order` từ chối
   * (`context.missing_idxs` của envelope `IMM09-EVIDENCE-PHOTO-REQUIRED`) — MỘT predicate
   * SSoT, nhiều nơi đọc; FE KHÔNG được đếm lại từ `repair_checklist[].photo` (đó là bản
   * diễn giải thứ hai — chính class-of-bug advertise≠enforce đang đóng).
   * Rỗng `[]` ⟺ cổng ảnh KHÔNG chặn hoàn thành phiếu. Optional cùng lý do forward-compat.
   */
  evidence_photo_missing_idxs?: number[]
  /**
   * AC-CR-84 — MẪU SỐ: số mục nghiệm thu PHẢI có ảnh (= số dòng `repair_checklist` đã lưu
   * khi cổng áp dụng; `0` khi cổng không áp dụng). Tiến độ hiển thị =
   * `evidence_photo_total_required − evidence_photo_missing_idxs.length` / mẫu số này.
   * Optional cùng lý do forward-compat.
   */
  evidence_photo_total_required?: number
  /**
   * SSoT server-driven CTA (GATE-8 / LL-FE-51): danh sách trạng thái-đích hợp lệ
   * kế tiếp mà BE cho phép, do `get_repair_work_order` emit =
   * `_REPAIR_VALID_TRANSITIONS.get(status, [])` (imm09.py:778). FE gate nút workflow
   * bằng `capability && allowed_transitions.includes('<đích>')` — KHÔNG tự suy diễn
   * theo `status === 'X'`. Terminal (Completed/Cannot Repair/Cancelled) → []. Optional
   * (forward-compat: trước khi BE enrich → undefined → 0 nút CTA, KHÔNG vỡ).
   *
   * ⚠️ GIỮ NGUYÊN sau AC-CR-82 (back-compat): `available_actions` là SUPERSET, KHÔNG
   * thay thế — đây vẫn là đường FALLBACK khi worker BE chưa phát `available_actions`.
   */
  allowed_transitions?: string[]
  /**
   * AC-CR-82 — CTA SERVER-DRIVEN cho màn chi tiết phiếu sửa chữa (nửa CM của mobile
   * CR-74; mirror AC-CR-77 nửa PM). ĐÚNG 6 phần tử, thứ tự CỐ ĐỊNH
   * `[assign_technician, submit_diagnosis, request_spare_parts, start_repair,
   * close_work_order, confirm_inspection]` — đủ 6 kể cả ở trạng thái terminal
   * (khi đó `enabled=false` toàn bộ). Mỗi khoá ánh xạ 1-1 tới endpoint CÓ THẬT của
   * `assetcore/api/imm09.py` (`assign_technician:122` · `submit_diagnosis:128` ·
   * `request_spare_parts:142` · `start_repair:136` · `close_work_order:149` ·
   * `confirm_inspection:180`).
   *
   * • `enabled` = `transition_allowed ∩ has_cap ∩ business_gate` do SERVER quyết —
   *   FE KHÔNG nhân bản `can('repair.*') && allowed_transitions.includes(...)` cho 6
   *   khoá này (đó chính là nguồn "nút chết": bấm được nhưng BE từ chối).
   * • `reason` = chuỗi TIẾNG VIỆT server trả, bất biến D9: `enabled === false ⟺
   *   reason !== ""`. FE render NGUYÊN VĂN (tooltip + danh sách chữ) — KHÔNG bịa chuỗi.
   * • `route` = "" (CTA nằm TRONG màn chi tiết — modal/điều hướng nội bộ, không deep-link).
   * • `Cancelled` KHÔNG BAO GIỜ là action (0 endpoint) ⇒ server không phát ⇒ FE không
   *   thể vẽ nút huỷ phiếu; `Cannot Repair` KHÔNG là khoá thứ 7 — dùng CHUNG
   *   `close_work_order` (cùng endpoint, cờ `cannot_repair=1`).
   *
   * Optional — CỐ Ý: worker BE chưa reload (`--preload` staleness) hoặc client cũ vẫn
   * trả shape CŨ ⇒ `undefined` ⇒ view rơi về đường FALLBACK (`allowed_transitions` +
   * capability), KHÔNG nút nào biến mất, KHÔNG màn trắng.
   *
   * Hợp đồng: `docs/imm-09/05_API_Specification.md §15` (ADR-IMM09-CTA-01/02/03).
   */
  available_actions?: AvailableAction[]
}

/**
 * Snapshot thông tin tài sản kèm trong detail (`get_repair_work_order` → `asset_info`).
 * `lifecycle_status` = trạng thái vòng đời THỰC của AC Asset tại thời điểm fetch
 * (SoT do nhiều process quản: repair / calibration-fail / incident / decommission).
 * BR-09-09 / INV-09-RESTORE-1: sau khi đóng WO, `complete_repair` CHỈ đưa asset về
 * 'Active' khi trước đó là 'Under Repair' — nếu asset đang giữ hold governance khác
 * (vd 'Out of Service' do calib-fail/CAPA) thì WO=Completed NHƯNG asset KHÔNG về Active.
 * → FE PHẢI bind badge/banner theo giá trị THỰC này, KHÔNG hardcode 'Active'.
 */
export interface AssetInfo {
  asset_name?: string
  asset_category?: string
  lifecycle_status?: string
  risk_classification?: string
  manufacturer_sn?: string
  department?: string
  location?: string
  [key: string]: unknown
}

export interface SparePartRow {
  idx: number
  item_code: string
  item_name: string
  /** Mã nhà sản xuất — field `spare_parts_used.manufacturer_part_no` (BE có thể chưa trả). */
  manufacturer_part_no?: string
  qty: number
  uom: string
  unit_cost: number
  total_cost: number
  stock_entry_ref: string
  notes: string
  /**
   * CR-73(a) — KHOÁ THẬT `AC Spare Part` mang theo từ gợi ý (KHÔNG có field tương ứng
   * trong child DocType `spare_parts_used` ⇒ chỉ tồn tại trong phiên làm việc FE).
   * `request_spare_parts` đọc khoá này để tra `AC Spare Part Stock` → tạo allocation;
   * thiếu nó BE lùi về `item_code` (= mã NSX) ⇒ "allocation câm".
   */
  spare_part?: string
  /**
   * AC-CR-78 / INV-PARTS-1 — trạng thái THẬT của phiếu xuất kho gắn với dòng vật tư,
   * do BE derive bằng CÙNG helper SSoT với validator BR-09-02
   * (`services/imm09.py::validate_spare_parts_stock_entries`):
   *   • `'OK'`        — `stock_entry_ref` trỏ `AC Stock Movement` CÓ THẬT.
   *   • `'MISSING'`   — `stock_entry_ref` rỗng (chưa xuất kho).
   *   • `'NOT_FOUND'` — có mã nhưng bản ghi KHÔNG tồn tại (ref treo/dangling).
   *
   * FE KHÔNG tự suy diễn: từ phía client ref treo nhìn y hệt ref hợp lệ ⇒ trước vòng này
   * dòng treo hiển thị như HỢP LỆ (badge xanh giả) trong khi `on_submit` vẫn chặn 422.
   * Optional (forward-compat: worker chưa reload → undefined → view giữ nguyên hành vi cũ).
   */
  stock_entry_status?: 'OK' | 'MISSING' | 'NOT_FOUND'
  /**
   * AC-CR-78 — dạng số của `stock_entry_status` (`1` ⟺ `'OK'`). INTEGER 0|1 theo quirk
   * CR-01 của hợp đồng mobile (KHÔNG boolean). Optional cùng lý do forward-compat.
   */
  stock_entry_ok?: 0 | 1
}

/**
 * CR-73(a) — GỢI Ý phụ tùng trả về từ `search_spare_parts` (13 khoá, ADDITIVE).
 *
 * KIỂU RIÊNG, KHÔNG nhồi 3 khoá mới vào `SparePartRow`: `SparePartRow` là dòng
 * `spare_parts_used` của phiếu (`CMPartsView` dựng bằng spread) — thêm field bắt buộc
 * vào đó sẽ vỡ mọi nơi dựng row. Xem `docs/imm-09/06_Frontend_Design.md`
 * §SparePartSuggestion + `05_API_Specification.md §3.13-bis`.
 *
 * 3 khoá nhận dạng (BE cam kết LUÔN có mặt, kiểu string, `""` khi không resolve —
 * KHÔNG `null`, KHÔNG thiếu khoá):
 *  - `device_model`      PK `IMM Device Model` — khử gợi-ý-trùng-chữ giữa 2 model.
 *  - `device_model_name` `model_name` để HIỂN THỊ (fallback = `device_model`).
 *  - `spare_part`        PK `AC Spare Part` — khoá THẬT để `request_spare_parts`
 *                        tra `AC Spare Part Stock` → tạo allocation (hết "allocation câm").
 *                        `""` ⇒ phụ tùng chưa có trong danh mục kho ⇒ KHÔNG chọn được.
 */
export interface SparePartSuggestion {
  idx: number
  item_code: string
  item_name: string
  manufacturer_part_no: string
  qty: number
  uom: string
  unit_cost: number
  total_cost: number
  stock_entry_ref: string
  notes: string
  device_model: string
  device_model_name: string
  spare_part: string
}

/**
 * Dòng YÊU CẦU phụ tùng gửi lên `request_spare_parts` (BE đọc `spare_part` /
 * `item_code` / `qty` — `services/imm09.py::request_spare_parts`). Tách khỏi
 * `SparePartRow` để không phải bịa `uom`/`unit_cost`/`idx` cho một yêu cầu.
 */
export interface SparePartRequestLine {
  /** PK `AC Spare Part` — khoá tra kho. Rỗng ⇒ BE fallback `item_code`. */
  spare_part: string
  item_code?: string
  qty: number
  stock_entry_ref?: string
  notes?: string
}

export interface RepairChecklistRow {
  idx: number
  test_description: string
  test_category: string
  expected_value: string
  measured_value: string
  result: 'Pass' | 'Fail' | 'N/A' | null
  notes: string
  /**
   * Ảnh bằng chứng cho MỘT mục checklist sửa chữa (NĐ98 Class C/D — mobile CR-15/G6).
   * Field DocType `repair_checklist.photo` (Attach ĐƠN) ⇒ tối đa 1 ảnh/mục
   * (MAX_REPAIR_CHECKLIST_PHOTOS=1 ở services/imm09.py). `null`/`''` khi chưa đính.
   * BE `get_repair_work_order` trả field này qua as_dict; consumer render thumbnail.
   */
  photo?: string | null
}

export interface RepairKPIs {
  kpis: {
    total_completed: number
    mttr_avg_hours: number
    sla_compliance_pct: number
    repeat_failure_count: number
    open_wos: number
  }
  root_cause_breakdown: Array<{ category: string; count: number }>
}

export interface RepairListResponse {
  data: AssetRepair[]
  pagination: { page: number; page_size: number; total: number; total_pages: number }
}

export interface MttrReport {
  mttr_avg: number
  first_fix_rate: number
  backlog_count: number
  cost_per_repair: number
  mttr_trend: Array<{ month: string; value: number }>
  backlog_by_dept: Array<{ dept: string; count: number }>
}

const BASE = '/api/method/assetcore.api.imm09'

export function listRepairWorkOrders(
  filters = {}, page = 1, pageSize = 20, search?: string,
): Promise<RepairListResponse> {
  const params: Record<string, unknown> = {
    filters: JSON.stringify(filters),
    page,
    page_size: pageSize,
  }
  // CR-18: tìm kiếm free-text server-side (mã phiếu / mã thiết bị / tên thiết bị).
  // CHỈ gửi khi non-empty ⇒ absent = baseline byte-identical (BE bỏ qua search rỗng).
  if (search && search.trim()) params.search = search.trim()
  return frappeGet<RepairListResponse>(`${BASE}.list_repair_work_orders`, params)
}

export function getRepairWorkOrder(name: string): Promise<AssetRepair> {
  return frappeGet<AssetRepair>(`${BASE}.get_repair_work_order`, { name })
}

export function assignTechnician(
  name: string,
  technician: string,
  priority?: string,
): Promise<{ name: string; status: string; assigned_to: string }> {
  return frappePost<{ name: string; status: string; assigned_to: string }>(
    `${BASE}.assign_technician`,
    { name, technician, priority },
  )
}

export function submitDiagnosis(
  name: string,
  diagnosisNotes: string,
  needsParts: boolean,
): Promise<{ name: string; status: string }> {
  return frappePost<{ name: string; status: string }>(
    `${BASE}.submit_diagnosis`,
    { name, diagnosis_notes: diagnosisNotes, needs_parts: needsParts ? 1 : 0 },
  )
}

export function closeWorkOrder(payload: {
  name: string
  repair_summary: string
  root_cause_category: string
  dept_head_name: string
  checklist_results: RepairChecklistRow[]
  cannot_repair?: boolean
  cannot_repair_reason?: string
  // CR-24 idempotency (parity IMM-08 submit_pm_result / IMM-11 record_result):
  // khoá do client sinh, chỉ điều khiển dedup ở BE (mobile write-outbox re-drain +
  // web desk double-submit). BE unwrap → replay success-envelope thay vì 422-giả khi
  // WO đã sang Pending Inspection. Bỏ trống ⇒ hành vi legacy (không dedup). Field body
  // `client_request_id` khớp signature BE api/imm09.close_work_order; KHÔNG lọt vào doc.
  client_request_id?: string
}): Promise<{ name: string; status: string; mttr_hours: number; sla_breached: boolean }> {
  return frappePost<{ name: string; status: string; mttr_hours: number; sla_breached: boolean }>(
    `${BASE}.close_work_order`,
    {
      ...payload,
      checklist_results: JSON.stringify(payload.checklist_results),
      cannot_repair: payload.cannot_repair ? 1 : 0,
    },
  )
}

export function confirmInspection(
  name: string,
): Promise<{ name: string; status: string; mttr_hours: number; sla_breached: boolean }> {
  return frappePost<{ name: string; status: string; mttr_hours: number; sla_breached: boolean }>(
    `${BASE}.confirm_inspection`,
    { name },
  )
}

export function getRepairKPIs(year?: number, month?: number): Promise<RepairKPIs> {
  return frappeGet<RepairKPIs>(`${BASE}.get_repair_kpis`, { year, month })
}

/**
 * Lịch sử sửa chữa của 1 thiết bị (cắt cứng theo `limit`, KHÔNG phân trang).
 *
 * Hợp đồng cắt danh sách TRUNG THỰC (CR-69, SSoT `services/shared/truncation.py`):
 * `total` = COUNT DB thật trên ĐÚNG filter-set `{asset_ref, docstatus: 1}`
 * @`Asset Repair` TRƯỚC khi cắt — CÙNG predicate với truy vấn lấy rows, nên phiếu
 * nháp (`docstatus = 0`) KHÔNG được tính vào `total`. `truncated` = int 0/1 (parity
 * CR-01 — KHÔNG bool) = `len(history) >= limit ∧ total > limit`; vừa khít trần
 * (`total === limit`) ⇒ `0`.
 *
 * ⚠️ Cả hai OPTIONAL — worker BE chưa reload (`--preload` staleness) trả shape CŨ
 * thiếu 2 khoá → caller PHẢI đọc phòng thủ (`total ?? history.length`,
 * `truncated ?? 0`), KHÔNG khai non-optional rồi để `undefined` lọt runtime.
 * `asset_ref`/`history` GIỮ NGUYÊN (ADDITIVE, 0 breaking).
 */
export function getAssetRepairHistory(
  assetRef: string,
  limit = 10,
): Promise<{ asset_ref: string; history: AssetRepair[]; total?: number; truncated?: 0 | 1 }> {
  return frappeGet<{ asset_ref: string; history: AssetRepair[]; total?: number; truncated?: 0 | 1 }>(
    `${BASE}.get_asset_repair_history`,
    { asset_ref: assetRef, limit },
  )
}

export function createRepairWorkOrder(payload: {
  asset_ref: string
  repair_type: string
  priority: string
  failure_description: string
  /** Ảnh mô tả lỗi (file URL sau khi upload) — optional */
  fault_image?: string
  /** BR-09-01 đã nới — incident/PM giờ optional (standalone repair) */
  incident_report?: string
  source_pm_wo?: string
  sla_target_hours?: number
}): Promise<{ name: string; status: string; sla_target_hours: number }> {
  return frappePost<{ name: string; status: string; sla_target_hours: number }>(
    `${BASE}.create_repair_work_order`,
    payload,
  )
}

export function startRepair(name: string): Promise<{ name: string; status: string }> {
  return frappePost<{ name: string; status: string }>(
    `${BASE}.start_repair`,
    { name },
  )
}

export function requestSpareParts(
  name: string,
  parts: SparePartRequestLine[] | SparePartRow[],
): Promise<{ name: string; status?: string; updated: number; allocation?: string | null }> {
  return frappePost<{ name: string; status?: string; updated: number; allocation?: string | null }>(
    `${BASE}.request_spare_parts`,
    { name, parts: JSON.stringify(parts) },
  )
}

export function getMttrReport(year: number, month: number): Promise<MttrReport> {
  return frappeGet<MttrReport>(`${BASE}.get_mttr_report`, { year, month })
}

export async function searchSpareParts(query: string): Promise<SparePartSuggestion[]> {
  const res = await frappeGet<SparePartSuggestion[]>(`${BASE}.search_spare_parts`, { query })
  return res ?? []
}

// Số ảnh bằng chứng tối đa cho MỖI mục checklist — KHỚP MAX_REPAIR_CHECKLIST_PHOTOS ở
// BE (services/imm09.py = 1, field Attach ĐƠN) + app mobile (CR-15/G6). Đổi 1 nơi đổi cả 3.
export const MAX_REPAIR_CHECKLIST_PHOTOS = 1

// Kết quả BE attach_repair_checklist_photo (Decision-B data) — mirror payload service.
export interface RepairChecklistPhotoResult {
  file_url: string
  file_name: string
  checklist_item_idx: number
}

/**
 * Đính 1 ảnh bằng chứng (NĐ98 Class C/D) cho MỘT mục checklist nghiệm thu sửa chữa qua
 * multipart/form-data. ĐỐI XỨNG imm12.attachIncidentPhoto (KHÁC module/doctype/
 * discriminator — Frappe child `idx`). POST FormData thẳng vào endpoint AssetCore
 * whitelisted (KHÔNG /api/method/upload_file trần) để BE gate quyền (assignee HOẶC
 * repair.write) + validate + link File private + sinh Lifecycle 'repair_checklist_photo_attached'.
 *
 * Server-authoritative:
 *  - success:true → { file_url, file_name, checklist_item_idx } của File vừa sinh.
 *  - Decision-B lỗi { success:false, code, error, fields? } → throw ApiError giữ `code`
 *    + `fields.file` (thông điệp VN, vd 'Chỉ chấp nhận ảnh JPG hoặc PNG') để view render
 *    lỗi inline dưới control.
 *  - Bất kỳ shape KHÁC (5xx / body lỗi thô Frappe) → thông điệp máy chủ chung (Finding C):
 *    TUYỆT ĐỐI KHÔNG echo exc/traceback thô ra UI.
 */
export async function attachRepairChecklistPhoto(
  workOrderName: string,
  checklistItemIdx: number,
  file: File,
): Promise<RepairChecklistPhotoResult> {
  const form = new FormData()
  form.append('work_order_name', workOrderName)
  form.append('checklist_item_idx', String(checklistItemIdx))
  form.append('file', file, file.name)
  // axios v1 tự set Content-Type multipart + boundary khi data là FormData; khai báo
  // 'multipart/form-data' để override default 'application/json' của instance.
  const res = await axiosClient.post<{ message: ApiResponse<RepairChecklistPhotoResult> & Record<string, unknown> }>(
    `${BASE}.attach_repair_checklist_photo`,
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
  const env = res.data?.message
  // Decision-B envelope lỗi HỢP LỆ = { success:false, code, error, fields? } (_err LUÔN
  // kèm `code` string) → thông điệp VN đã curate ở BE, an toàn echo + render inline.
  if (env && env.success === false && typeof env.code === 'string') {
    throw new ApiError((env.error as string) || 'Không thể đính ảnh bằng chứng', {
      code: env.code as ErrorCodeType,
      httpStatus: (env.http_status as number | undefined) ?? 0,
      fields: env.fields as Record<string, string> | undefined,
    })
  }
  // Finding C: shape KHÔNG phải Decision-B success → thông điệp máy chủ chung, KHÔNG echo
  // env.error/exc/traceback thô (500 thật đã bị interceptor axios chặn trước khi tới đây).
  if (!env || env.success !== true || !env.data?.file_url) {
    throw new ApiError('Có lỗi máy chủ, vui lòng thử lại.', {
      code: ErrorCode.INTERNAL_ERROR,
      httpStatus: 500,
    })
  }
  return env.data
}
