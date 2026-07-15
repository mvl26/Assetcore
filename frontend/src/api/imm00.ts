// Copyright (c) 2026, AssetCore Team
// API client cho IMM-00 — AC Asset foundation module
//
// NOTE: frappeGet/frappePost đã unwrap Frappe envelope ({ message: { success, data } })
// và throw ApiError khi success === false. Các hàm ở đây trả thẳng kiểu dữ liệu T,
// KHÔNG wrap thêm ApiResponse<T>.

import { frappeGet, frappePost } from './helpers'
import api from './axios'
import { ApiError, ErrorCode, httpStatusToCode, type ErrorCodeType } from './errors'
import type {
  AcAsset, AcAssetListItem, AcSupplier, AcLocation, AcDepartment,
  AcAssetCategory, ImmDeviceModel, ImmSlaPolicy, ImmAuditTrail,
  ImmCapaRecord, AssetLifecycleEvent, IncidentReport,
  AssetListParams, PaginatedResponse, AssetKpi, ChainVerifyResult,
  AssetTransfer,
} from '@/types/imm00'

const BASE = '/api/method/assetcore.api.imm00'

// ─── AC Asset ─────────────────────────────────────────────────────────────────

export function listAssets(params: AssetListParams = {}): Promise<PaginatedResponse<AcAssetListItem>> {
  return frappeGet(`${BASE}.list_assets`, params as Record<string, unknown>)
}

export function getAsset(name: string): Promise<AcAsset> {
  return frappeGet(`${BASE}.get_asset`, { name })
}

// ─── Asset action meta (panel NẠC — màn tạo WO: CM / Hiệu chuẩn / PM) ───────────
// Payload least-privilege (NĐ98 data-minimization) cho panel meta thiết bị 5-dòng.
// CHỈ 6 field — KHÔNG kế thừa AcAsset (full doc rò gross_purchase_amount /
// accumulated_depreciation / current_book_value / purchase_cost / salvage_value /
// qr_token / audit-chain). Đóng over-fetch tài chính ở đường QR scan-action: 3 màn
// tạo WO gọi getAssetActionMeta THAY getAsset cho panel. `name` là khóa nội bộ; FE
// render asset_name / device_model_name / location_name / lifecycle_status /
// risk_classification. Mirror BE `assetcore.api.imm00.get_asset_action_meta` 1-1.
export interface AssetActionMeta {
  name: string
  asset_name?: string
  device_model_name?: string
  lifecycle_status?: string
  risk_classification?: string
  location_name?: string
}

/**
 * Nạp meta NẠC cho panel thiết bị ở màn tạo WO (CM/Hiệu chuẩn/PM).
 * Mirror BE `assetcore.api.imm00.get_asset_action_meta` (naming contract — path =
 * tên function BE). Cùng 3 lớp bảo mật như getAsset: 404 (name rỗng/không tồn tại)
 * / 403 (vendor-IDOR / thiếu DocPerm read) → ApiError; caller bắt → assetMeta=null
 * (panel ẩn, KHÔNG vỡ trang, KHÔNG leak raw exc/email/qr_token).
 */
export function getAssetActionMeta(name: string): Promise<AssetActionMeta> {
  return frappeGet(`${BASE}.get_asset_action_meta`, { name })
}

export function createAsset(data: Partial<AcAsset>): Promise<{ name: string }> {
  return frappePost(`${BASE}.create_asset`, data as Record<string, unknown>)
}

export function updateAsset(name: string, data: Partial<AcAsset>): Promise<{ name: string }> {
  return frappePost(`${BASE}.update_asset`, { name, ...data } as Record<string, unknown>)
}

export function transitionStatus(name: string, to_status: string, reason = ''): Promise<{ name: string; lifecycle_status: string }> {
  return frappePost(`${BASE}.transition_status`, { name, to_status, reason })
}

export function getAssetTimeline(name: string, page = 1, page_size = 50): Promise<PaginatedResponse<AssetLifecycleEvent>> {
  return frappeGet(`${BASE}.get_asset_timeline`, { name, page, page_size })
}

export function getAssetKpi(name: string): Promise<AssetKpi> {
  return frappeGet(`${BASE}.get_asset_kpi`, { name })
}

export function validateForOperations(name: string): Promise<{ valid: boolean; reason?: string }> {
  return frappeGet(`${BASE}.validate_for_operations`, { name })
}

// ─── QR deep-link (A2 — ADR-001 D4) ────────────────────────────────────────────
// Payload tối thiểu trả từ resolve_qr_token — A2 CHỈ resolve + định danh; màn info
// đầy đủ là /assets/:id (A6/V7). Khớp 1-1 với service BE resolve_qr_token.
export interface QrResolvePayload {
  name: string
  asset_code: string
  lifecycle_status: string
  device_model_name: string
  location_name: string
}

/**
 * Tra mã QR deep-link (/a/<token>) → định danh asset.
 * Mirror BE `assetcore.api.imm00.resolve_qr_token` (naming contract).
 * Lỗi: 403 (thiếu asset.read) / 404 (token sai/không tồn tại) → ApiError, view
 * QrResolveView bắt và render màn lỗi VI (KHÔNG redirect).
 */
export function resolveQrToken(token: string): Promise<QrResolvePayload> {
  return frappeGet(`${BASE}.resolve_qr_token`, { token })
}

// ─── QR scan info (A6 — màn THÔNG TIN thiết bị mobile-first) ────────────────────
// Payload màn info read-only khi quét QR (deep-link landing). Mở rộng A2 với
// asset_name + bảo trì gần nhất + next_pm_date. lifecycle_status là MÃ CANONICAL
// (FE dịch nhãn VI qua SSoT lifecycleStatusLabel — KHÔNG leak mã EN thô ra UI).
// Khớp 1-1 với service BE build_asset_scan_info. KHÔNG field nhạy cảm (giá mua,
// khấu hao, audit chain, supplier code).
export interface RecentMaintenance {
  event_type: string
  date: string | null
}
// R1 QR-SCAN-ACTION (ADR-IMM00-QR-SCAN-ACTION §D2) — 1 phần tử của available_actions.
// Mirror CHÍNH XÁC shape BE `_build_available_actions` (services/imm00.py): derive
// SERVER-SIDE = has_cap ∩ lifecycle_allows. FE CHỈ render (KHÔNG hardcode action,
// KHÔNG tự tính enabled/reason).
//   • key     — định danh action (report_failure | request_pm | request_cm |
//               request_calibration). FE dịch nhãn VI qua SCAN_ACTION_LABELS (SSoT).
//   • label   — nhãn VI BE phát (fallback khi key chưa có trong SSoT FE).
//   • route   — TÊN route (vue-router name), KHÔNG path thô. FE dựng URL qua
//               router.resolve({ name, query }) — KHÔNG ghép query-string thủ công,
//               KHÔNG kèm qr_token.
//   • enabled — true ⟺ có quyền ∧ lifecycle cho phép. false → nút disabled + reason.
//   • reason  — chuỗi VI giải thích vì sao disabled (CHỈ khi enabled=false). Ưu tiên
//               lifecycle > capability (BE đã quyết — FE chỉ render).
export interface ScanAction {
  key: string
  label: string
  route: string
  enabled: boolean
  reason: string
}
export interface AssetScanInfo {
  name: string
  asset_code: string
  asset_name: string
  // D5 (ADR-IMM00-QR-SCAN-ACTION — NĐ98): Số serial NSX = định danh truy xuất hợp
  // lệ. BE coalesce '' khi rỗng (parity asset_code/asset_name — KHÔNG None). KTV
  // xác nhận ĐÚNG thiết bị vật lý trước khi báo hỏng/tạo WO.
  manufacturer_sn: string
  // Vòng 38 (risk_classification — phân loại rủi ro): enum EN AC Asset
  // 'Low/Medium/High/Critical' (read-only, fetch_from device_model). BE GIỮ raw
  // enum làm SSoT (KHÔNG dịch); FE map sang VI qua riskClassificationLabel +
  // nhãn 'Chưa phân loại' khi rỗng. BE coalesce '' khi rỗng (parity manufacturer_sn
  // — KHÔNG None). KHÔNG nhầm với risk_class (A/B/C/D — WHO/NĐ98 letter class).
  risk_classification: string
  device_model_name: string
  location_name: string
  lifecycle_status: string
  recent_maintenance: RecentMaintenance | null
  next_pm_date: string | null
  // Cờ PM quá hạn derive SERVER-SIDE (timezone-safe) — FE CHỈ render, KHÔNG so
  // ngày bằng client clock. true ⟺ next_pm_date quá khứ ∧ thiết bị còn dùng.
  pm_overdue: boolean
  // Chiều HIỆU CHUẨN (FR-00-86 / BR-00-37) — song song next_pm_date/pm_overdue.
  next_calibration_date: string | null
  // Cờ HIỆU CHUẨN quá hạn derive SERVER-SIDE (timezone-safe) — FE CHỈ render cờ,
  // KHÔNG so next_calibration_date với client clock. true ⟺ next_calibration_date
  // quá khứ ∧ thiết bị còn dùng (∉ Out of Service/Decommissioned).
  calibration_overdue: boolean
  // Vòng 48 (trạng thái BẢO HÀNH): warranty_expiry_date = str|None 'YYYY-MM-DD'
  // (qua _date_str_or_none — parity next_pm_date/next_calibration_date; rỗng/None →
  // null). KTV biết "còn/hết bảo hành" TRƯỚC khi báo hỏng/tạo CM (affordance chi
  // phí sửa chữa). FE map nhãn VI presence-aware (KHÔNG leak datetime thô/phi-ISO).
  warranty_expiry_date: string | null
  // Cờ HẾT BẢO HÀNH derive SERVER-SIDE (timezone-safe) qua _is_warranty_expired —
  // STRICT < ngày server, KHÔNG client clock. ĐỘC LẬP lifecycle (KHÁC pm/cal
  // overdue: bảo hành = sự kiện HỢP ĐỒNG — Out-of-Service/Decommissioned VẪN có
  // thể còn/hết bảo hành). true ⟺ warranty_expiry_date quá khứ. FE CHỈ render cờ.
  warranty_expired: boolean
  // R1 QR-SCAN-ACTION (D2) — 4 CTA màn quét derive SERVER-SIDE. FE v-for render
  // MỌI phần tử (kể cả enabled=false → nút disabled + reason; KHÔNG ẩn nút chết).
  available_actions: ScanAction[]
}

/**
 * Lấy payload màn thông tin thiết bị mobile-first khi quét QR (A6).
 * Mirror BE `assetcore.api.imm00.get_asset_scan_info` (naming contract — path =
 * tên function BE). Resolve theo `token` (deep-link QR) HOẶC `name` (điều hướng
 * nội bộ). Lỗi: 403 (thiếu asset.read / IDOR vendor) / 404 (token|name sai) →
 * ApiError; AssetScanInfoView bắt và render màn lỗi VI (KHÔNG trang trắng).
 */
export function getAssetScanInfo(params: { token?: string; name?: string }): Promise<AssetScanInfo> {
  return frappeGet(`${BASE}.get_asset_scan_info`, params as Record<string, unknown>)
}

// ─── QR label print (A4 — ADR-001 D3) ──────────────────────────────────────────
// Payload nhãn QR cấp tài sản (8 field). Khớp 1-1 với service BE
// build_asset_label_data — qr_url là chuỗi tuyệt đối /a/<token>, FE encode TRỰC
// TIẾP vào QR ảnh (KHÔNG tự build URL, KHÔNG mã hoá chuỗi tag commissioning).
// ADR-IMM00-QR-SCAN-ACTION D5: tách bạch Mã tài sản (asset_code) ↔ Số serial NSX
// (manufacturer_sn) + Tên tài sản (asset_name) — định danh truy xuất NĐ98 trên tem.
export interface AssetLabelData {
  name: string
  asset_code: string
  asset_name: string
  manufacturer_sn: string
  device_model_name: string
  location_name: string
  lifecycle_status: string
  qr_url: string
}

// Batch item: payload hợp lệ HOẶC ô lỗi {name, error} (AC-E001 = asset không tồn tại).
// BE giữ ĐÚNG thứ tự input → index ổn định cho FE render.
export interface BatchLabelErrorItem {
  name: string
  error: string
}
export type BatchLabelItem = AssetLabelData | BatchLabelErrorItem

/** Type guard — phân biệt ô lỗi với payload nhãn hợp lệ. */
export function isBatchLabelError(item: BatchLabelItem): item is BatchLabelErrorItem {
  return 'error' in item && typeof (item as BatchLabelErrorItem).error === 'string'
}

/**
 * Lấy dữ liệu in nhãn QR cho 1 asset (READ-ONLY — KHÔNG ghi label_printed).
 * Mirror BE `assetcore.api.imm00.get_asset_label_data` (naming contract).
 * Gate asset.print ở BE (D6 phương án B) → user không có quyền in nhận 403.
 */
export function getAssetLabelData(asset: string): Promise<AssetLabelData> {
  return frappeGet(`${BASE}.get_asset_label_data`, { asset })
}

/**
 * Lấy dữ liệu in nhãn QR hàng loạt — 1 LẦN gọi (chống N+1), giữ ĐÚNG thứ tự.
 * Mirror BE `assetcore.api.imm00.get_asset_label_data_batch`.
 * List-param convention: JSON.stringify (BE parse_json khi nhận chuỗi) — GET
 * repeat-key không tin cậy qua form_dict.
 */
export function getAssetLabelDataBatch(assets: string[]): Promise<BatchLabelItem[]> {
  return frappeGet(`${BASE}.get_asset_label_data_batch`, { assets: JSON.stringify(assets) })
}

/**
 * Ghi sự kiện in nhãn (label_printed + audit) cho MỖI asset — gọi SAU khi in thật.
 * Mirror BE `assetcore.api.imm00.mark_label_printed` (POST). preview KHÔNG gọi.
 * POST body JSON → gửi mảng NATIVE (BE parse_json bỏ qua list, dùng thẳng) — KHÔNG
 * stringify (khác GET batch: GET cần JSON-string vì form_dict repeat-key không tin cậy).
 */
export function markLabelPrinted(assets: string[]): Promise<{ printed: string[]; event_count: number }> {
  return frappePost(`${BASE}.mark_label_printed`, { assets })
}

// ─── QR label PDF — đa khổ tem (ADR-IMM00-LABEL-PDF — phương án A) ───────────────
// Khổ tem SSoT (mirror BE services/imm00.py:_LABEL_PRESETS + DEFAULT_LABEL_PRESET).
// Server render HTML → PDF ĐÚNG khổ tem nhiệt đã chọn (MỖI nhãn = 1 trang), FE tải
// Blob → iframe ẩn → iframe.print() → ra ĐÚNG khổ (KHÔNG còn @page CSS giả-lập sai-khổ).
//
// Whitelist 3 preset PDF hợp lệ — KEY KHỚP CHÍNH XÁC (phân biệt hoa thường) với BE
// `_LABEL_PRESETS`. preset ngoài 3 key này → BE trả 422 (FE chặn trước qua dropdown).
// 'tem-60x100' là MẶC ĐỊNH (USER có máy in tem 6×10cm portrait).
export const LABEL_PDF_PRESETS = [
  { key: 'tem-60x100', label: 'Tem 60×100mm' },
  { key: 'tem-70x40', label: 'Tem 70×40mm' },
  { key: 'tem-50x30', label: 'Tem 50×30mm' },
] as const

export type LabelPdfPreset = (typeof LABEL_PDF_PRESETS)[number]['key']

/** Preset PDF mặc định = 'tem-60x100' (mirror BE DEFAULT_LABEL_PRESET). */
export const LABEL_PDF_PRESET: LabelPdfPreset = 'tem-60x100'

/** Nhãn VI của 1 preset PDF (fallback rỗng nếu key lạ). */
export function labelPdfPresetLabel(preset: string): string {
  return LABEL_PDF_PRESETS.find((p) => p.key === preset)?.label ?? ''
}

// Shape error envelope BE phát trên HTTP-200 (Frappe whitelist bọc dưới `message`).
// print_asset_labels_pdf trả: THÀNH CÔNG = Content-Type application/pdf (bytes);
// LỖI nghiệp vụ (cap-403/preset-422/empty-422/batch-413/IDOR-403) = _err JSON
// HTTP-200 → KHÔNG đưa Blob-JSON cho iframe (tránh in JSON thô ra giấy).
interface PdfErrorEnvelope {
  success?: boolean
  error?: string
  code?: string
  http_status?: number
  fields?: Record<string, string>
}

// Đọc text từ Blob — ưu tiên Blob.text() (browser + jsdom mới); fallback FileReader
// (jsdom cũ KHÔNG có Blob.text()). Đảm bảo error-envelope parse được ở mọi env.
async function blobText(blob: Blob): Promise<string> {
  if (typeof blob.text === 'function') return blob.text()
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result ?? ''))
    reader.onerror = () => reject(reader.error)
    reader.readAsText(blob)
  })
}

/**
 * Sinh PDF nhãn QR khổ tem nhiệt (đa khổ — `preset`) cho `assets` (mỗi asset = 1
 * trang). Mirror BE `assetcore.api.imm00.print_asset_labels_pdf` (naming contract —
 * path = tên function BE). Gửi `assets` dạng JSON-string (BE parse_json — parity
 * getAssetLabelDataBatch) + `preset` (1 trong 3 key whitelist LABEL_PDF_PRESETS;
 * mặc định 'tem-60x100'). preset NGOÀI whitelist → BE trả 422.
 *
 * Dùng axios `api` TRỰC TIẾP (KHÔNG frappeGet/frappePost — chúng unwrap JSON
 * envelope, làm hỏng Blob nhị phân). Giữ withCredentials + CSRF (interceptor
 * request đính `X-Frappe-CSRF-Token`). responseType:'blob'.
 *
 * BE trả 2 dạng trên HTTP-200:
 *   (a) THÀNH CÔNG = Content-Type application/pdf → resolve Blob.
 *   (b) LỖI nghiệp vụ = Error JSON envelope (application/json, success:false,
 *       code/http_status) → đọc blob.text() → JSON.parse → ném ApiError (message
 *       VI từ envelope). KHÔNG resolve Blob-JSON (tránh iframe in ra JSON thô).
 */
export async function printAssetLabelsPdf(
  assets: string[],
  preset: LabelPdfPreset = LABEL_PDF_PRESET,
): Promise<Blob> {
  const response = await api.post<Blob>(
    `${BASE}.print_asset_labels_pdf`,
    { assets: JSON.stringify(assets), preset },
    { responseType: 'blob' },
  )
  const blob = response.data
  const contentType = String(response.headers['content-type'] ?? '').toLowerCase()

  // THÀNH CÔNG: Content-Type application/pdf → trả Blob nguyên vẹn cho iframe.
  if (contentType.includes('application/pdf')) return blob

  // LỖI nghiệp vụ (HTTP-200 + JSON envelope): đọc text → parse → ApiError VI.
  // Frappe bọc return value whitelist dưới `message`; _err shape {success,error,code,http_status}.
  const text = await blobText(blob)
  let env: PdfErrorEnvelope = {}
  try {
    const parsed = JSON.parse(text) as { message?: PdfErrorEnvelope } & PdfErrorEnvelope
    env = (parsed.message ?? parsed) as PdfErrorEnvelope
  } catch {
    // Không parse được JSON → lỗi không xác định (KHÔNG echo raw text → tránh leak EN).
    throw new ApiError('Không thể tạo PDF nhãn QR. Vui lòng thử lại.', ErrorCode.UNKNOWN, 0)
  }
  const httpStatus = typeof env.http_status === 'number' ? env.http_status : 0
  const code: ErrorCodeType = (env.code as ErrorCodeType | undefined)
    ?? (httpStatus ? httpStatusToCode(httpStatus) : ErrorCode.UNKNOWN)
  throw new ApiError(
    env.error || 'Không thể tạo PDF nhãn QR. Vui lòng thử lại.',
    { code, httpStatus, fields: env.fields },
  )
}

// ─── QR token rotate (B — hardening) ────────────────────────────────────────────
// Cấp lại (rotate) qr_token bị lộ: vô hiệu hoá MỌI nhãn QR đã in (token cũ KHÔNG
// còn resolve) + cấp token mới. KHÁC getAssetLabelData (gate asset.print): đây là
// thao tác GHI → gate asset.qr.rotate ở BE (D6 phương án B — tách cap rotate khỏi
// in). Trả qr_url MỚI để refresh nhãn/print — KHÔNG surface token thô (ADR-001
// §D4 rule 9: no-raw-token, FE chỉ cần qr_url).
export interface RegenerateQrResult {
  name: string
  qr_url: string
}

/**
 * Cấp lại (rotate) mã QR cho 1 asset — vô hiệu hoá nhãn cũ + token mới (POST).
 * Mirror BE `assetcore.api.imm00.regenerate_asset_qr_token` (naming contract).
 * Gate asset.qr.rotate ở BE → user chỉ print/đọc nhận 403; vendor ngoài scope 403
 * (IDOR); asset không tồn tại 404 → ApiError, view bắt và notify VI (KHÔNG white-screen).
 */
export function regenerateAssetQrToken(asset: string): Promise<RegenerateQrResult> {
  return frappePost(`${BASE}.regenerate_asset_qr_token`, { asset })
}

// ─── AC Supplier ──────────────────────────────────────────────────────────────

export function listSuppliers(page = 1, page_size = 50, search = ''): Promise<PaginatedResponse<AcSupplier>> {
  return frappeGet(`${BASE}.list_suppliers`, { page, page_size, search })
}

// ─── Reference data ───────────────────────────────────────────────────────────

export function listLocations(parent = ''): Promise<AcLocation[]> {
  return frappeGet(`${BASE}.list_locations`, { parent })
}

export function listDepartments(parent = ''): Promise<AcDepartment[]> {
  return frappeGet(`${BASE}.list_departments`, { parent })
}

export function listAssetCategories(): Promise<AcAssetCategory[]> {
  return frappeGet(`${BASE}.list_asset_categories`)
}

export function listDeviceModels(page = 1, page_size = 50, search = ''): Promise<PaginatedResponse<ImmDeviceModel>> {
  return frappeGet(`${BASE}.list_device_models`, { page, page_size, search })
}

export function listSlaPolicies(): Promise<ImmSlaPolicy[]> {
  return frappeGet(`${BASE}.list_sla_policies`)
}

// ─── IMM Audit Trail ──────────────────────────────────────────────────────────

export function listAuditTrail(asset: string, page = 1, page_size = 50): Promise<PaginatedResponse<ImmAuditTrail>> {
  return frappeGet(`${BASE}.list_audit_trail`, { asset, page, page_size })
}

export function verifyChain(asset: string): Promise<ChainVerifyResult> {
  return frappeGet(`${BASE}.verify_chain`, { asset })
}

// ─── IMM CAPA Record ──────────────────────────────────────────────────────────

export function listCapas(params: { page?: number; page_size?: number; status?: string; asset?: string; not_closed?: number; overdue?: number } = {}): Promise<PaginatedResponse<ImmCapaRecord>> {
  return frappeGet(`${BASE}.list_capas`, params as Record<string, unknown>)
}

export function getCapaOverdue(page = 1, page_size = 20): Promise<PaginatedResponse<ImmCapaRecord>> {
  return frappeGet(`${BASE}.list_overdue_capas`, { page, page_size })
}

export function openCapa(data: {
  asset: string; severity: string; description: string; responsible: string;
  source_type?: string; source_ref?: string; due_days?: number
}): Promise<{ name: string }> {
  return frappePost(`${BASE}.open_capa`, data as Record<string, unknown>)
}

export function getCapa(name: string): Promise<ImmCapaRecord> {
  return frappeGet(`${BASE}.get_capa`, { name })
}

/**
 * Đóng CAPA (path LEGACY — `assetcore.api.imm00.close_capa_record`).
 *
 * CỔNG HIỆU QUẢ (VR-06/VR-07 — SoT `services/imm00.assert_capa_effectiveness_gate`):
 * BE BẮT BUỘC `effectiveness_check === 'Effective'` mới đóng. Nếu thiếu/None hoặc
 * khác 'Effective' → BE trả envelope `{ success:false, code:'VALIDATION', error:'VR-06/07: …' }`
 * (ServiceError FIN-007 ↦ HTTP 422). `frappePost` PHÁT HIỆN `success===false` và **throw
 * `ApiError`** (KHÔNG nuốt thành công) — caller bắt buộc `await` trong try/catch hoặc qua
 * `api.run()`/`notify.fromError()` để hiển thị message VI BE trả, KHÔNG báo 'Đã đóng'.
 *
 * Path đóng "chuẩn" qua xác minh hiệu quả là `imm16.advance_capa_state` /
 * `perform_effectiveness_check` (UI: CAPADetailView Verification) — đã gate sẵn.
 * Hàm này giữ cho integration/legacy; phải KHỚP signature BE.
 */
export function closeCapaRecord(name: string, data: {
  root_cause: string
  corrective_action: string
  preventive_action: string
  effectiveness_check?: string
}): Promise<{ name: string; status: string }> {
  return frappePost(`${BASE}.close_capa_record`, { name, ...data })
}

// ─── Incident Report ──────────────────────────────────────────────────────────

export function listIncidents(params: { page?: number; page_size?: number; status?: string; severity?: string; asset?: string } = {}): Promise<PaginatedResponse<IncidentReport>> {
  return frappeGet(`${BASE}.list_incidents`, params as Record<string, unknown>)
}

export function createIncident(data: Partial<IncidentReport>): Promise<{ name: string }> {
  return frappePost(`${BASE}.create_incident`, data as Record<string, unknown>)
}

export function getIncident(name: string): Promise<IncidentReport> {
  return frappeGet(`${BASE}.get_incident`, { name })
}

export function updateIncident(name: string, data: Partial<IncidentReport>): Promise<{ name: string }> {
  return frappePost(`${BASE}.update_incident`, { name, ...data } as Record<string, unknown>)
}

export function submitIncident(name: string): Promise<{ name: string; docstatus: number }> {
  return frappePost(`${BASE}.submit_incident`, { name })
}

export function deleteIncident(name: string): Promise<{ name: string; deleted: boolean }> {
  return frappePost(`${BASE}.delete_incident`, { name })
}

// ─── AC Supplier CRUD ────────────────────────────────────────────────────────

export function getSupplier(name: string): Promise<AcSupplier> {
  return frappeGet(`${BASE}.get_supplier`, { name })
}

export function createSupplier(data: Partial<AcSupplier>): Promise<{ name: string }> {
  return frappePost(`${BASE}.create_supplier`, data as Record<string, unknown>)
}

export function updateSupplier(name: string, data: Partial<AcSupplier>): Promise<{ name: string }> {
  return frappePost(`${BASE}.update_supplier`, { name, ...data } as Record<string, unknown>)
}

export function deleteSupplier(name: string): Promise<{ name: string; deleted: boolean }> {
  return frappePost(`${BASE}.delete_supplier`, { name })
}

// ─── IMM Device Model CRUD ───────────────────────────────────────────────────

export function getDeviceModel(name: string): Promise<ImmDeviceModel> {
  return frappeGet(`${BASE}.get_device_model`, { name })
}

export function createDeviceModel(data: Partial<ImmDeviceModel>): Promise<{ name: string }> {
  return frappePost(`${BASE}.create_device_model`, data as Record<string, unknown>)
}

export function updateDeviceModel(name: string, data: Partial<ImmDeviceModel>): Promise<{ name: string }> {
  return frappePost(`${BASE}.update_device_model`, { name, ...data } as Record<string, unknown>)
}

export function deleteDeviceModel(name: string): Promise<{ name: string; deleted: boolean }> {
  return frappePost(`${BASE}.delete_device_model`, { name })
}

// ─── AC Location / Department / Category CRUD ───────────────────────────────

export function getLocation(name: string): Promise<AcLocation> {
  return frappeGet(`${BASE}.get_location`, { name })
}

export function getDepartment(name: string): Promise<AcDepartment> {
  return frappeGet(`${BASE}.get_department`, { name })
}

export function getAssetCategory(name: string): Promise<AcAssetCategory> {
  return frappeGet(`${BASE}.get_asset_category`, { name })
}

export function createLocation(data: Partial<AcLocation>): Promise<{ name: string }> {
  return frappePost(`${BASE}.create_location`, data as Record<string, unknown>)
}

export function updateLocation(name: string, data: Partial<AcLocation>): Promise<{ name: string }> {
  return frappePost(`${BASE}.update_location`, { name, ...data } as Record<string, unknown>)
}

export function deleteLocation(name: string): Promise<{ name: string; deleted: boolean }> {
  return frappePost(`${BASE}.delete_location`, { name })
}

export function createDepartment(data: Partial<AcDepartment>): Promise<{ name: string }> {
  return frappePost(`${BASE}.create_department`, data as Record<string, unknown>)
}

export function updateDepartment(name: string, data: Partial<AcDepartment>): Promise<{ name: string }> {
  return frappePost(`${BASE}.update_department`, { name, ...data } as Record<string, unknown>)
}

export function deleteDepartment(name: string): Promise<{ name: string; deleted: boolean }> {
  return frappePost(`${BASE}.delete_department`, { name })
}

export function createAssetCategory(data: Partial<AcAssetCategory>): Promise<{ name: string }> {
  return frappePost(`${BASE}.create_asset_category`, data as Record<string, unknown>)
}

export function updateAssetCategory(name: string, data: Partial<AcAssetCategory>): Promise<{ name: string }> {
  return frappePost(`${BASE}.update_asset_category`, { name, ...data } as Record<string, unknown>)
}

export function deleteAssetCategory(name: string): Promise<{ name: string; deleted: boolean }> {
  return frappePost(`${BASE}.delete_asset_category`, { name })
}

// ─── IMM SLA Policy CRUD ─────────────────────────────────────────────────────

export function getSlaPolicy(name: string): Promise<ImmSlaPolicy> {
  return frappeGet(`${BASE}.get_sla_policy`, { name })
}

export function createSlaPolicy(data: Partial<ImmSlaPolicy>): Promise<{ name: string }> {
  return frappePost(`${BASE}.create_sla_policy`, data as Record<string, unknown>)
}

export function updateSlaPolicy(name: string, data: Partial<ImmSlaPolicy>): Promise<{ name: string }> {
  return frappePost(`${BASE}.update_sla_policy`, { name, ...data } as Record<string, unknown>)
}

export function deleteSlaPolicy(name: string): Promise<{ name: string; deleted: boolean }> {
  return frappePost(`${BASE}.delete_sla_policy`, { name })
}

// ─── AC Asset delete ─────────────────────────────────────────────────────────

export function deleteAsset(name: string): Promise<{ name: string; deleted: boolean }> {
  return frappePost(`${BASE}.delete_asset`, { name })
}

// ─── Depreciation: List + Stats (Asset Finance Hub) ─────────────────────────

export interface AssetDepreciationRow {
  name: string
  asset_name: string
  asset_category?: string
  department?: string
  location?: string
  purchase_date?: string
  in_service_date?: string
  depreciation_start_date?: string
  gross_purchase_amount?: number
  residual_value?: number
  depreciation_method?: string
  total_depreciation_months?: number
  depreciation_frequency?: string
  accumulated_depreciation?: number
  current_book_value?: number
  lifecycle_status?: string
  configured: boolean
  pct_depreciated: number
  executed_periods: number
  total_periods: number
}

export interface DepreciationStats {
  total_assets: number
  configured_count: number
  unconfigured_count: number
  fully_depreciated: number
  total_gross: number
  total_accumulated: number
  total_book_value: number
  overall_pct: number
  by_method: { method: string; count: number }[]
  by_category: { category: string; book_value: number }[]
}

export interface DepreciationComputeResult {
  name: string
  accumulated: number
  book_value: number
  method: string
  pct_depreciated: number
}

export interface ListAssetsDepreciationParams {
  page?: number
  page_size?: number
  method_filter?: string
  status_filter?: string
  category_filter?: string
  /** Virtual filter (vd 'fully_depreciated') — BE áp SoT is_fully_depreciated SAU enrich.
   *  KHÔNG nhồi value này vào status_filter/lifecycle_status (leak sai field BE). */
  depreciation_filter?: string
}

export function listAssetsDepreciation(params: ListAssetsDepreciationParams = {}): Promise<{ items: AssetDepreciationRow[]; pagination: { page: number; page_size: number; total: number } }> {
  return frappeGet(`${BASE}.list_assets_depreciation`, params as Record<string, unknown>)
}

export function getDepreciationStats(): Promise<DepreciationStats> {
  return frappeGet(`${BASE}.get_depreciation_stats`)
}

export function computeDepreciation(name: string): Promise<DepreciationComputeResult> {
  return frappePost(`${BASE}.compute_depreciation`, { name })
}

export interface ComputeAllDepreciationResult {
  /** Số tài sản được backfill luật khấu hao từ Category. */
  inherited: number
  /** Số schedule mới được sinh. */
  generated: number
  /** Số dòng schedule được thực thi (đến hạn). */
  executed_rows: number
  /** Số tài sản được cập nhật accumulated/book value. */
  updated_assets: number
  /** Bỏ qua vì đã có kỳ Executed (giữ lịch sử). */
  skipped_has_history: number
  /** Bỏ qua vì không có luật ở cả Category (lỗi cấu hình thật). */
  skipped_no_rule: number
}

export function computeAllDepreciation(): Promise<ComputeAllDepreciationResult> {
  return frappePost(`${BASE}.compute_all_depreciation`)
}

// ─── Depreciation gom theo Danh mục (quản lý tập trung) ──────────────────────

/** Một dòng tổng hợp khấu hao cho 1 Danh mục tài sản. */
export interface DepreciationCategoryRow {
  /** Docname AC Asset Category ('' cho nhóm 'Chưa phân loại'). */
  category_id: string
  /** Tên hiển thị danh mục (category_name) hoặc 'Chưa phân loại'. */
  category: string
  asset_count: number
  configured_count: number
  fully_depreciated: number
  total_gross: number
  total_accumulated: number
  total_book_value: number
  pct_depreciated: number
}

export interface DepreciationByCategoryResult {
  categories: DepreciationCategoryRow[]
  totals: {
    total_assets: number
    total_gross: number
    total_accumulated: number
    total_book_value: number
    overall_pct: number
  }
}

export function getDepreciationByCategory(): Promise<DepreciationByCategoryResult> {
  return frappeGet(`${BASE}.get_depreciation_by_category`)
}

// ─── Asset Transfer CRUD ─────────────────────────────────────────────────────

// Detail phiếu luân chuyển. BE (get_transfer_full / get_transfer) enrich thêm 6
// denorm *_name (from/to × location/department/custodian) qua SSoT _enrich,
// coalesce '' — consumer hiển thị *_name, KHÔNG render Link-id thô. Trả kèm
// AssetTransfer để 6 *_name có type; giữ Record<string, unknown> cho field còn lại.
export function getTransferFull(name: string): Promise<AssetTransfer & Record<string, unknown>> {
  return frappeGet(`${BASE}.get_transfer_full`, { name })
}

export function updateTransfer(name: string, data: Record<string, unknown>): Promise<{ name: string }> {
  return frappePost(`${BASE}.update_transfer`, { name, ...data })
}

export function approveTransfer(name: string): Promise<{ name: string; approved_by: string }> {
  return frappePost(`${BASE}.approve_transfer`, { name })
}

// ─── PM Schedule CRUD ────────────────────────────────────────────────────────

export interface PmSchedule {
  name: string
  asset_ref: string
  asset_name?: string
  asset_code?: string
  pm_type?: string
  status?: string
  pm_interval_days?: number
  checklist_template?: string
  responsible_technician?: string
  last_pm_date?: string
  next_due_date?: string
  alert_days_before?: number
  notes?: string
}

// BE list_pm_schedules trả envelope phẳng { items, total, page, page_size } (qua
// _ok → frappeGet unwrap data). KHÔNG phải { data, pagination } — type cũ sai shape
// khiến view đọc d.data/d.pagination = undefined ⇒ list LUÔN rỗng. Sửa đúng shape.
export interface PmScheduleListResponse {
  items: PmSchedule[]
  total: number
  page: number
  page_size: number
}

export function listPmSchedules(params: { page?: number; page_size?: number; asset?: string; status?: string; pm_type?: string; search?: string } = {}): Promise<PmScheduleListResponse> {
  return frappeGet(`${BASE}.list_pm_schedules`, params as Record<string, unknown>)
}

export function getPmSchedule(name: string): Promise<PmSchedule> {
  return frappeGet(`${BASE}.get_pm_schedule`, { name })
}

export function createPmSchedule(data: Partial<PmSchedule>): Promise<{ name: string }> {
  return frappePost(`${BASE}.create_pm_schedule`, data as Record<string, unknown>)
}

export function updatePmSchedule(name: string, data: Partial<PmSchedule>): Promise<{ name: string }> {
  return frappePost(`${BASE}.update_pm_schedule`, { name, ...data } as Record<string, unknown>)
}

export function deletePmSchedule(name: string): Promise<{ name: string; deleted: boolean }> {
  return frappePost(`${BASE}.delete_pm_schedule`, { name })
}

// ─── PM Checklist Template CRUD ──────────────────────────────────────────────

export interface PmChecklistItem {
  description: string
  measurement_type?: 'Pass/Fail' | 'Numeric' | 'Text'
  unit?: string
  expected_min?: number | null
  expected_max?: number | null
  is_critical?: 0 | 1 | boolean
  reference_section?: string
}

export interface PmTemplate {
  name: string
  template_name: string
  asset_category?: string
  /** Display name của asset_category (do BE enrich từ AC Asset Category.category_name). */
  category_name?: string
  /** Display name của template (BE thay slug trailing trong template_name bằng category_name). */
  display_template_name?: string
  pm_type?: string
  version?: string
  effective_date?: string
  approved_by?: string
  checklist_items?: PmChecklistItem[]
}

// Endpoints are served by assetcore.api.imm08 (service-based — handles checklist_items JSON)
const _PM_TPL_BASE = '/api/method/assetcore.api.imm08'

export function listPmTemplates(page = 1, page_size = 50): Promise<{ data: PmTemplate[]; pagination: { total: number; page: number; page_size: number } }> {
  return frappeGet(`${_PM_TPL_BASE}.list_pm_templates`, { page, page_size })
}

export function getPmTemplate(name: string): Promise<PmTemplate> {
  return frappeGet(`${_PM_TPL_BASE}.get_pm_template`, { name })
}

export function createPmTemplate(data: Partial<PmTemplate>): Promise<{ name: string }> {
  return frappePost(`${_PM_TPL_BASE}.create_pm_template`, data as Record<string, unknown>)
}

export function updatePmTemplate(name: string, data: Partial<PmTemplate>): Promise<{ name: string }> {
  return frappePost(`${_PM_TPL_BASE}.update_pm_template`, { name, ...data } as Record<string, unknown>)
}

export function deletePmTemplate(name: string): Promise<{ name: string; deleted: boolean }> {
  return frappePost(`${_PM_TPL_BASE}.delete_pm_template`, { name })
}

export interface ApplyPmTemplateResult {
  template: string
  asset_category: string
  total_assets: number
  created: number
  skipped_existing: number
  errors: number
}

export function applyPmTemplateToCategory(templateName: string): Promise<ApplyPmTemplateResult> {
  return frappePost(`${_PM_TPL_BASE}.apply_pm_template_to_category`, { template_name: templateName })
}

// ─── Firmware Change Request CRUD ────────────────────────────────────────────

export interface FirmwareCR {
  name: string
  asset_ref: string
  asset_name?: string
  asset_repair_wo?: string
  version_before?: string
  version_after?: string
  change_notes?: string
  source_reference?: string
  status?: string
  approved_by?: string
  approved_by_name?: string
  approved_datetime?: string
  applied_datetime?: string
  rollback_reason?: string
  // Server-driven CTA (GATE-8 / LL-FE-51). BE derive từ _FCR_VALID_TRANSITIONS
  // đã LỌC theo capability caller; `can_approve` = cờ riêng cho cạnh duyệt.
  // Consumer (web + mobile) CHỈ render nút theo 2 field này, KHÔNG suy từ `status`.
  allowed_transitions?: string[]
  can_approve?: boolean
}

/** Hành động chuyển-trạng-thái FCR có kiểm soát (transition endpoint). */
export type FirmwareCrAction = 'approve' | 'deploy' | 'rollback'

export function listFirmwareCrs(params: { page?: number; page_size?: number; status?: string; asset?: string; search?: string } = {}): Promise<{ items: FirmwareCR[]; total: number }> {
  return frappeGet(`${BASE}.list_firmware_crs`, params as Record<string, unknown>)
}

export function getFirmwareCr(name: string): Promise<FirmwareCR> {
  return frappeGet(`${BASE}.get_firmware_cr`, { name })
}

export function createFirmwareCr(data: Partial<FirmwareCR>): Promise<{ name: string }> {
  return frappePost(`${BASE}.create_firmware_cr`, data as Record<string, unknown>)
}

// ⚠️ update_firmware_cr = CRUD chung (mô tả/notes). KHÔNG dùng để đổi `status` —
// BE reject/bỏ qua kwarg status. Đổi trạng thái PHẢI qua transitionFirmwareCr.
export function updateFirmwareCr(name: string, data: Partial<FirmwareCR>): Promise<{ name: string }> {
  return frappePost(`${BASE}.update_firmware_cr`, { name, ...data } as Record<string, unknown>)
}

/**
 * Chuyển trạng thái FCR qua endpoint có kiểm soát SERVER-side (capability-role +
 * valid-transition guard + audit trail Lifecycle Event). Mirror BE
 * `assetcore.api.imm00.transition_firmware_cr`. `reason` chỉ dùng cho action
 * 'rollback' (lý do khôi phục — audit NĐ98). Trả FCR đã cập nhật (kèm
 * allowed_transitions/can_approve mới).
 */
export function transitionFirmwareCr(
  name: string,
  action: FirmwareCrAction,
  reason?: string,
): Promise<FirmwareCR> {
  const payload: Record<string, unknown> = { name, action }
  if (reason) payload.reason = reason
  return frappePost(`${BASE}.transition_firmware_cr`, payload)
}

export function deleteFirmwareCr(name: string): Promise<{ name: string; deleted: boolean }> {
  return frappePost(`${BASE}.delete_firmware_cr`, { name })
}

// ─── Document Request CRUD ───────────────────────────────────────────────────

export interface DocumentRequest {
  name: string
  asset_ref: string
  asset_name?: string
  doc_type_required: string
  doc_category?: string
  status?: string
  priority?: string
  assigned_to?: string
  due_date?: string
  source_type?: string
  request_note?: string
  fulfilled_by?: string
}

export function listDocumentRequests(params: { page?: number; page_size?: number; status?: string; asset?: string; priority?: string; search?: string } = {}): Promise<{ items: DocumentRequest[]; total: number }> {
  return frappeGet(`${BASE}.list_document_requests`, params as Record<string, unknown>)
}

export function getDocumentRequest(name: string): Promise<DocumentRequest> {
  return frappeGet(`${BASE}.get_document_request`, { name })
}

export function createDocumentRequest(data: Partial<DocumentRequest>): Promise<{ name: string }> {
  return frappePost(`${BASE}.create_document_request`, data as Record<string, unknown>)
}

export function updateDocumentRequest(name: string, data: Partial<DocumentRequest>): Promise<{ name: string }> {
  return frappePost(`${BASE}.update_document_request`, { name, ...data } as Record<string, unknown>)
}

export function deleteDocumentRequest(name: string): Promise<{ name: string; deleted: boolean }> {
  return frappePost(`${BASE}.delete_document_request`, { name })
}

// ─── Depreciation Schedule (Phase 2) ─────────────────────────────────────────

export interface DepreciationScheduleRow {
  name: string
  period_number: number
  scheduled_date: string
  depreciation_amount: number
  accumulated_amount: number
  remaining_value: number
  status: 'Pending' | 'Executed' | 'Cancelled'
  executed_on?: string
  journal_entry?: string
}

export interface DepreciationScheduleResponse {
  asset: string
  asset_info: {
    gross_purchase_amount?: number
    residual_value?: number
    accumulated_depreciation?: number
    current_book_value?: number
    depreciation_method?: string
    total_depreciation_months?: number
    depreciation_frequency?: string
    depreciation_start_date?: string
    in_service_date?: string
  }
  rows: DepreciationScheduleRow[]
  summary: {
    total_periods: number
    executed_periods: number
    pending_periods: number
    total_depreciated: number
  }
}

export async function getDepreciationSchedule(asset_name: string) {
  return frappeGet<DepreciationScheduleResponse>(
    `${BASE}.get_depreciation_schedule`, { asset_name },
  )
}

export async function regenerateDepreciationSchedule(asset_name: string, force: 0 | 1 = 1) {
  return frappePost<{ asset: string; periods: number; total_depreciable?: number; skipped?: boolean; reason?: string }>(
    `${BASE}.regenerate_depreciation_schedule`, { asset_name, force },
  )
}

export interface DepreciationPreviewRow {
  period_number: number
  scheduled_date: string
  depreciation_amount: number
  accumulated_amount: number
  remaining_value: number
}

export async function previewDepreciationSchedule(params: {
  gross: number
  residual: number
  method: string
  total_months: number
  frequency: string
  start_date: string
}) {
  return frappeGet<DepreciationPreviewRow[]>(
    `${BASE}.preview_depreciation_schedule`, params as Record<string, unknown>,
  )
}

export async function runDueDepreciationNow(as_of?: string) {
  return frappePost<{ executed_rows: number; updated_assets: number }>(
    `${BASE}.run_due_depreciation_now`, { as_of: as_of || '' },
  )
}

// ─── Device Model file upload ────────────────────────────────────────────────

export interface DeviceModelFileUploadResult {
  name: string
  file_url: string
  file_name: string
  fieldname: string
}

export async function uploadDeviceModelFile(
  file: File,
  fieldname: 'model_image' | 'catalog_file',
  model_name = '',
): Promise<DeviceModelFileUploadResult> {
  const form = new FormData()
  form.append('file', file, file.name)
  form.append('fieldname', fieldname)
  if (model_name) form.append('model_name', model_name)
  // axios v1 auto-fills the multipart boundary when Content-Type is 'multipart/form-data'
  // and data is a FormData instance — overriding the instance default of 'application/json'.
  const { default: api } = await import('./axios')
  const res = await api.post<{ message: { success: boolean; data: DeviceModelFileUploadResult; error?: string } }>(
    `${BASE}.upload_device_model_file`, form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
  const env = res.data?.message
  if (!env?.success || !env.data?.file_url) {
    throw new Error(env?.error || 'Upload thất bại')
  }
  return env.data
}

export interface BulkRegenerateResult {
  category: string
  total_assets: number
  inherited: number
  regenerated: number
  skipped_has_history: number
  skipped_no_rule: number
  errors: number
}

export async function bulkRegenerateScheduleByCategory(
  category_name: string,
): Promise<BulkRegenerateResult> {
  return frappePost<BulkRegenerateResult>(
    `${BASE}.bulk_regenerate_schedule_by_category`, { category_name })
}
