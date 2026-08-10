// Copyright (c) 2026, AssetCore Team
// API calls cho Module IMM-05 — Asset Document Repository

import { uploadAttachment } from './files'
import { frappeGet, frappePost } from './helpers'

const BASE = '/api/method/assetcore.api.imm05'

// ─────────────────────────────────────────────────────────────────────────────
// FILE UPLOAD — dùng Frappe core File DocType
// ─────────────────────────────────────────────────────────────────────────────

export interface FrappeFileUploadResult {
  file_url: string
  name: string
  file_name: string
  is_private: number
}

/**
 * Upload tệp cho một hồ sơ AssetCore — shim mỏng quanh `api/files.ts`.
 *
 * TRƯỚC 2026-07-22 hàm này POST thẳng `/api/method/upload_file`:
 *  - không gate được quyền theo nghiệp vụ;
 *  - `isPrivate:false` ⇒ hồ sơ tuân thủ thành tệp CÔNG KHAI đoán được URL;
 *  - hardcode `doctype: 'Asset Document'` cho MỌI caller ⇒ phiếu hiệu chuẩn gắn
 *    tệp vào một Asset Document không tồn tại ⇒ không ai đọc lại được.
 * Nay uỷ quyền cho endpoint gate quyền; caller PHẢI khai đúng doctype/fieldname.
 */
export async function uploadDocumentFile(
  file: File,
  opts: { doctype?: string; fieldname?: string; docname?: string } = {},
): Promise<FrappeFileUploadResult> {
  const res = await uploadAttachment(file, {
    doctype: opts.doctype || 'Asset Document',
    fieldname: opts.fieldname || 'file_attachment',
    docname: opts.docname,
  })
  return { ...res, is_private: res.is_private ?? 1 }
}

// ─────────────────────────────────────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────────────────────────────────────

export interface Pagination {
  page: number
  page_size: number
  total: number
  total_pages: number
}

export interface AssetDocumentItem {
  name: string
  asset_ref: string
  asset_name?: string
  doc_category: string
  doc_type_detail: string
  doc_number: string
  version: string
  workflow_state: string
  expiry_date: string | null
  days_until_expiry: number | null
  visibility: 'Public' | 'Internal_Only'
  is_exempt: 0 | 1
  modified: string
}

export interface AssetDocumentDetail extends AssetDocumentItem {
  model_ref: string | null
  issued_date: string
  issuing_authority: string | null
  file_attachment: string
  approved_by: string | null
  approval_date: string | null
  rejection_reason: string | null
  change_summary: string | null
  is_expired: 0 | 1
  source_commissioning: string | null
  source_module: string | null
  exempt_reason: string | null
  exempt_proof: string | null
  notes: string | null
  /**
   * Server-driven CTA (GATE-8 / LL-FE-51): tập next-state hợp lệ do BE trả
   * (_DOC_VALID_TRANSITIONS trong services/imm05.py, SoT = fixture
   * 'IMM-05 Document Workflow'). FE gate nút chuyển trạng thái theo tập này,
   * KHÔNG hardcode workflow_state === 'X'. Vắng mặt → coi như [] (không nút).
   */
  allowed_transitions?: string[]
  /** 1 nếu user hiện tại có capability doc.approve (gate Phê duyệt/Từ chối/Lưu trữ). */
  can_approve?: number
}

// ─── Hồ sơ pháp lý theo THIẾT BỊ (`get_asset_documents` — CR-75) ──────────────

/** Enum SSoT do BE `_compute_document_status()` phát (ĐÚNG 5 giá trị). */
export type AssetDossierStatus =
  | 'Compliant'
  | 'Compliant (Exempt)'
  | 'Expiring_Soon'
  | 'Non-Compliant'
  | 'Incomplete'

/**
 * Dòng tài liệu bên trong `documents[category][]`.
 *
 * KHÔNG extend `AssetDocumentItem`: `get_asset_documents` chỉ select 12 cột (không
 * có `asset_ref` / `asset_name` / `modified`) — extend sẽ khiến type nói dối.
 */
export interface AssetDossierDocItem {
  name: string
  doc_category: string
  doc_type_detail: string
  doc_number?: string
  version?: string
  workflow_state: string
  expiry_date: string | null
  /** Dẫn xuất SERVER lúc đọc (BR-05-21) — FE KHÔNG so ngày bằng đồng hồ máy. */
  days_until_expiry: number | null
  /**
   * 0|1 — server dẫn xuất theo predicate SSoT `expired_filter()`
   * (`expiry_date` is set ∧ `< today` ∧ state ∉ {Archived, Rejected}).
   * Vắng mặt = BE chưa deploy CR-75 ⇒ coi như "chưa biết", KHÔNG tự suy ra.
   */
  is_expired?: 0 | 1
  visibility?: 'Public' | 'Internal_Only'
  is_exempt?: 0 | 1
  approved_by?: string | null
  approval_date?: string | null

  // ─── Tệp đính kèm THẬT (AC-CR-81) ──────────────────────────────────────────
  // BE batch-resolve `file_attachment` → DocType `File` (1 query/payload). Link
  // MỒ CÔI (URL không còn File doc) ⇒ `has_file=0` ∧ `file_url=''`: endpoint
  // KHÔNG phát link chết. 5 khoá luôn có mặt sau khi BE deploy; để `?:` vì bản
  // BE cũ chưa có ⇒ consumer degrade an toàn (KHÔNG kết luận "chưa đính kèm").
  /** URL tệp đã XÁC MINH tồn tại; `''` = không có tệp. KHÔNG hiển thị thô ra UI. */
  file_url?: string
  /** Tên tệp đọc-được (hiển thị thay cho URL); `''` = không có tệp. */
  file_name?: string
  /** Kích thước tệp tính bằng byte; `0` = không có tệp / chưa biết. */
  file_size?: number
  /** 0|1 — tệp nằm trong vùng riêng tư (cần đăng nhập để mở). KHÔNG boolean (CR-01). */
  is_private?: 0 | 1
  /**
   * 0|1 — khoá QUYẾT ĐỊNH duy nhất để gate nút mở tệp. `1` ⟺ `file_attachment`
   * non-empty ∧ File doc còn tồn tại. VẮNG MẶT = BE chưa deploy ⇒ "chưa biết".
   */
  has_file?: 0 | 1
}

/**
 * Hợp đồng `get_asset_documents` (docs/imm-05/05_API_Specification.md §2.7).
 *
 * Các khoá CR-75 để `?:` cho tới khi BE lên bản mới: consumer phải degrade an
 * toàn (chưa biết ⇒ KHÔNG kết luận "không tuân thủ"), KHÔNG được `as unknown as`.
 */
export interface AssetDossier {
  asset: string
  /** Mẫu số: số loại bắt buộc ÁP DỤNG cho nhóm thiết bị (BR-05-17). */
  required_total?: number
  /** Tử số: loại có ≥1 bản Active CÒN HIỆU LỰC (BR-05-18). */
  required_satisfied?: number
  /** 0..100 = round(satisfied / total × 100); `required_total === 0` ⇒ 100. */
  completeness_pct: number
  /** Enum SSoT; hợp đồng CŨ (trước CR-75) còn phát `'Complete'`/`'Incomplete'`. */
  document_status: AssetDossierStatus | string
  /** Khoá MÁY-ĐỌC 0|1 — consumer gate theo khoá này, KHÔNG so chuỗi. */
  is_compliant?: 0 | 1
  /** Loại bắt buộc chưa có bản Active nào ⇒ hành động "bổ sung mới". */
  missing_required: string[]
  /** Loại bắt buộc CÓ bản Active nhưng ĐÃ QUÁ HẠN ⇒ hành động "gia hạn". */
  expired_required?: string[]
  /** Còn hiệu lực nhưng hết hạn trong ≤ 30 ngày (cảnh báo, KHÔNG chặn). */
  expiring_required?: string[]
  /** Số tài liệu bị ẩn khỏi `documents` do phân quyền (BR-05-20). */
  hidden_count?: number
  /** Grouped OBJECT theo `doc_category` (KHÔNG phải mảng). */
  documents: Record<string, AssetDossierDocItem[]>
}

export interface DocumentFilters {
  doc_category?: string
  /** Plain match (`'Active'`) or Frappe operator tuple (`['not in', ['Archived','Rejected']]`). */
  workflow_state?: string | [string, unknown]
  asset_ref?: string
  visibility?: string
  /** Frappe operator tuple, e.g. `['<', '2026-05-29']` or `['between', [from, to]]`. */
  expiry_date?: unknown
  /**
   * Semantic marker (NOT a DB field) — BR-05-16. `'expired'` asks the BE to apply
   * the SoT predicate `expiry_date < today AND state NOT IN (Archived,Rejected)`.
   * `list_documents` pops + translates it; never sent as a raw filter dict.
   */
  expiry_status?: 'expired'
  [key: string]: unknown
}

export interface DocumentRequest {
  name: string
  asset_ref: string
  doc_type_required: string
  doc_category: string
  assigned_to: string
  due_date: string
  status: 'Open' | 'In_Progress' | 'Overdue' | 'Fulfilled' | 'Cancelled'
  priority: 'Low' | 'Medium' | 'High' | 'Critical'
  escalation_sent: 0 | 1
  source_type: string
  fulfilled_by: string | null
}

export interface DashboardStats {
  kpis: {
    total_active: number
    expiring_90d: number
    expired_not_renewed: number
    assets_missing_docs: number
  }
  expiry_timeline: Array<{
    name: string
    asset_ref: string
    doc_type_detail: string
    expiry_date: string
    days_until_expiry: number
  }>
  compliance_by_dept: Array<{
    dept: string
    total_assets: number
    compliant: number
    pct: number
  }>
}

// ─────────────────────────────────────────────────────────────────────────────
// 1. LIST DOCUMENTS
// ─────────────────────────────────────────────────────────────────────────────

export function listDocuments(
  filters: DocumentFilters = {},
  page = 1,
  pageSize = 20,
) {
  return frappeGet<{ items: AssetDocumentItem[]; pagination: Pagination }>(
    `${BASE}.list_documents`,
    { filters: JSON.stringify(filters), page, page_size: pageSize },
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// 2. GET DOCUMENT
// ─────────────────────────────────────────────────────────────────────────────

export function getDocument(name: string) {
  return frappeGet<AssetDocumentDetail>(`${BASE}.get_document`, { name })
}

// ─────────────────────────────────────────────────────────────────────────────
// 3. CREATE DOCUMENT
// ─────────────────────────────────────────────────────────────────────────────

export function createDocument(docData: Partial<AssetDocumentDetail>) {
  return frappePost<{ name: string; workflow_state: string }>(
    `${BASE}.create_document`,
    { doc_data: JSON.stringify(docData) },
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// 3b. SUBMIT FOR REVIEW (Draft → Pending Review)
// ─────────────────────────────────────────────────────────────────────────────

export function submitForReview(name: string) {
  return frappePost<{ name: string; new_state: string }>(
    `${BASE}.submit_for_review`,
    { name },
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// 4. UPDATE DOCUMENT
// ─────────────────────────────────────────────────────────────────────────────

export function updateDocument(name: string, docData: Partial<AssetDocumentDetail>) {
  return frappePost<{ name: string; modified: string }>(
    `${BASE}.update_document`,
    { name, doc_data: JSON.stringify(docData) },
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// 5. APPROVE / 6. REJECT
// ─────────────────────────────────────────────────────────────────────────────

export function approveDocument(name: string) {
  return frappePost<{ name: string; new_state: string }>(
    `${BASE}.approve_document`,
    { name },
  )
}

export function rejectDocument(name: string, rejectionReason: string) {
  return frappePost<{ name: string; new_state: string }>(
    `${BASE}.reject_document`,
    { name, rejection_reason: rejectionReason },
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// 6b. ARCHIVE DOCUMENT (Active → Archived "Lưu trữ" / Draft → Archived "Hủy bỏ")
// NĐ98 Điều 41: tài liệu không bị xóa — chỉ lưu trữ (giữ 10 năm).
// ─────────────────────────────────────────────────────────────────────────────

export function archiveDocument(name: string, reason = '') {
  return frappePost<{ name: string; new_state: string }>(
    `${BASE}.archive_document`,
    { name, reason },
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// 7. GET ASSET DOCUMENTS (grouped)
// ─────────────────────────────────────────────────────────────────────────────

export function getAssetDocuments(asset: string) {
  return frappeGet<AssetDossier>(`${BASE}.get_asset_documents`, { asset })
}

// ─────────────────────────────────────────────────────────────────────────────
// 8. DASHBOARD STATS
// ─────────────────────────────────────────────────────────────────────────────

export function getDashboardStats() {
  return frappeGet<DashboardStats>(`${BASE}.get_dashboard_stats`)
}

// ─────────────────────────────────────────────────────────────────────────────
// 9. EXPIRING DOCUMENTS
// ─────────────────────────────────────────────────────────────────────────────

export function getExpiringDocuments(days = 90) {
  return frappeGet<{ days: number; count: number; items: AssetDocumentItem[] }>(
    `${BASE}.get_expiring_documents`,
    { days },
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// 11. DOCUMENT HISTORY
// ─────────────────────────────────────────────────────────────────────────────

export function getDocumentHistory(name: string) {
  return frappeGet<{
    name: string
    history: Array<{
      timestamp: string
      user: string
      action: string
      from_state: string | null
      to_state: string | null
      changes: Array<{ field: string; old: unknown; new: unknown }>
    }>
  }>(`${BASE}.get_document_history`, { name })
}

// ─────────────────────────────────────────────────────────────────────────────
// 12. CREATE DOCUMENT REQUEST
// ─────────────────────────────────────────────────────────────────────────────

export function createDocumentRequest(payload: {
  asset_ref: string
  doc_type_required: string
  doc_category?: string
  assigned_to?: string
  due_date?: string
  priority?: string
  request_note?: string
  source_type?: string
}) {
  return frappePost<{ name: string; status: string }>(
    `${BASE}.create_document_request`,
    payload,
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// 13. GET DOCUMENT REQUESTS
// ─────────────────────────────────────────────────────────────────────────────

export function getDocumentRequests(assetRef = '', status = '') {
  return frappeGet<{ count: number; items: DocumentRequest[] }>(
    `${BASE}.get_document_requests`,
    { asset_ref: assetRef, status },
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// 14. MARK EXEMPT
// ─────────────────────────────────────────────────────────────────────────────

export function markExempt(payload: {
  asset_ref: string
  doc_type_detail: string
  exempt_reason: string
  exempt_proof: string
}) {
  return frappePost<{
    document_name: string
    is_exempt: boolean
    new_asset_document_status: string
  }>(`${BASE}.mark_exempt`, payload)
}
