// Copyright (c) 2026, AssetCore Team
// Pinia store: IMM-05 Document Repository state management

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  listDocuments,
  getAssetDocuments,
  getDashboardStats,
  approveDocument as apiApprove,
  rejectDocument as apiReject,
  createDocumentRequest as apiCreateRequest,
  getDocumentRequests,
  getExpiringDocuments,
  getDocument as apiGetDocument,
  updateDocument as apiUpdateDocument,
  createDocument as apiCreateDocument,
  getDocumentHistory as apiGetDocumentHistory,
} from '@/api/imm05'
import { ApiError, toApiError } from '@/api/errors'
import type {
  AssetDocumentItem,
  AssetDossierDocItem,
  AssetDocumentDetail,
  DocumentFilters,
  Pagination,
  DashboardStats,
  DocumentRequest,
} from '@/api/imm05'

export const useImm05Store = defineStore('imm05', () => {

  // ─── State ──────────────────────────────────────────────────────────────────

  const documents = ref<AssetDocumentItem[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  // Notification framework (Sprint 2026-05-29 vòng 5): giữ ApiError đã hydrate
  // (message_code/severity/title/action_hint) để view gọi notify.fromError().
  const lastApiError = ref<ApiError | null>(null)

  const pagination = ref<Pagination>({
    page: 1,
    page_size: 20,
    total: 0,
    total_pages: 0,
  })
  const currentFilters = ref<DocumentFilters>({})

  // Asset detail view — hồ sơ pháp lý theo thiết bị (CR-75)
  const assetDocuments = ref<Record<string, AssetDossierDocItem[]>>({})
  const assetCompletenessPct = ref(0)
  const assetDocumentStatus = ref('')
  const missingRequired = ref<string[]>([])
  /**
   * Khoá máy-đọc `is_compliant` (0|1) — `null` = CHƯA BIẾT (chưa tải xong hoặc BE
   * chưa deploy CR-75). Consumer phải phân biệt `null` với `0`: "chưa biết" KHÔNG
   * được vẽ thành "không tuân thủ" (nháy đỏ giả).
   */
  const assetIsCompliant = ref<number | null>(null)
  /** Loại bắt buộc CÓ bản Active nhưng ĐÃ QUÁ HẠN — cần GIA HẠN (≠ bổ sung mới). */
  const assetExpiredRequired = ref<string[]>([])
  /** Còn hiệu lực nhưng hết hạn ≤ 30 ngày — cảnh báo, KHÔNG chặn. */
  const assetExpiringRequired = ref<string[]>([])
  /** Mẫu số / tử số mức đầy đủ; `null` = BE chưa cấp (không bịa 0). */
  const assetRequiredTotal = ref<number | null>(null)
  const assetRequiredSatisfied = ref<number | null>(null)
  /** Số tài liệu bị ẩn khỏi `documents` do phân quyền (BR-05-20). */
  const assetHiddenCount = ref(0)

  // Dashboard
  const dashboardStats = ref<DashboardStats | null>(null)
  const dashboardLoading = ref(false)

  // Document requests
  const documentRequests = ref<DocumentRequest[]>([])

  // Expiring docs
  const expiringDocs = ref<AssetDocumentItem[]>([])


  // ─── Getters ────────────────────────────────────────────────────────────────

  const totalDocuments = computed(() => pagination.value.total)

  const pendingReviewDocs = computed(() =>
    documents.value.filter(d => d.workflow_state === 'Pending Review')
  )

  const expiredDocs = computed(() =>
    documents.value.filter(d => d.workflow_state === 'Expired')
  )

  const kpis = computed(() => dashboardStats.value?.kpis ?? null)

  const openRequests = computed(() =>
    documentRequests.value.filter(r => r.status === 'Open' || r.status === 'Overdue')
  )

  // ─── Actions ────────────────────────────────────────────────────────────────

  /** Ghi nhận lỗi: vừa set string (legacy banner) vừa giữ ApiError (notify). */
  function _captureError(e: unknown): void {
    const err = toApiError(e)
    lastApiError.value = err
    error.value = err.message
  }

  async function fetchDocuments(filters: DocumentFilters = {}, page = 1) {
    loading.value = true
    error.value = null
    currentFilters.value = filters
    try {
      const res = await listDocuments(filters, page, pagination.value.page_size)
      if (res?.items) {
        documents.value = res.items
        if (res.pagination) pagination.value = res.pagination
      }
    } catch (e: unknown) {
      _captureError(e)
    } finally {
      loading.value = false
    }
  }

  async function fetchAssetDocuments(asset: string) {
    loading.value = true
    error.value = null
    try {
      const res = await getAssetDocuments(asset)
      if (res) {
        // Gán VÔ ĐIỀU KIỆN: payload thiếu `documents` mà giữ lại danh sách của
        // thiết bị xem trước đó = hiển thị hồ sơ (và tệp) của SAI thiết bị.
        assetDocuments.value = res.documents ?? {}
        if (res.completeness_pct != null) assetCompletenessPct.value = res.completeness_pct
        if (res.document_status) assetDocumentStatus.value = res.document_status
        if (res.missing_required) missingRequired.value = res.missing_required
        // Khoá CR-75: gán VÔ ĐIỀU KIỆN (kể cả khi vắng) để không giữ giá trị của
        // thiết bị vừa xem trước đó — dữ liệu cũ của asset khác là nói dối.
        assetIsCompliant.value =
          typeof res.is_compliant === 'number' ? res.is_compliant : null
        assetExpiredRequired.value = res.expired_required ?? []
        assetExpiringRequired.value = res.expiring_required ?? []
        assetRequiredTotal.value =
          typeof res.required_total === 'number' ? res.required_total : null
        assetRequiredSatisfied.value =
          typeof res.required_satisfied === 'number' ? res.required_satisfied : null
        assetHiddenCount.value = res.hidden_count ?? 0
      }
    } catch (e: unknown) {
      _captureError(e)
    } finally {
      loading.value = false
    }
  }

  async function fetchDashboardStats() {
    dashboardLoading.value = true
    error.value = null
    try {
      dashboardStats.value = await getDashboardStats()
    } catch (e: unknown) {
      _captureError(e)
    } finally {
      dashboardLoading.value = false
    }
  }

  async function approveDocument(name: string): Promise<boolean> {
    try {
      await apiApprove(name)
      const doc = documents.value.find(d => d.name === name)
      if (doc) doc.workflow_state = 'Active'
      return true
    } catch (e: unknown) {
      _captureError(e)
      return false
    }
  }

  async function rejectDocument(name: string, reason: string): Promise<boolean> {
    try {
      await apiReject(name, reason)
      const doc = documents.value.find(d => d.name === name)
      if (doc) doc.workflow_state = 'Rejected'
      return true
    } catch (e: unknown) {
      _captureError(e)
      return false
    }
  }

  async function createRequest(payload: Parameters<typeof apiCreateRequest>[0]): Promise<string | null> {
    try {
      const res = await apiCreateRequest(payload)
      return res?.name || null
    } catch (e: unknown) {
      _captureError(e)
      return null
    }
  }

  async function fetchDocumentRequests(assetRef = '', status = '') {
    try {
      const res = await getDocumentRequests(assetRef, status)
      if (res?.items) documentRequests.value = res.items
    } catch (e: unknown) {
      _captureError(e)
    }
  }

  async function fetchExpiringDocuments(days = 30) {
    try {
      const res = await getExpiringDocuments(days)
      if (res?.items) expiringDocs.value = res.items
    } catch (e: unknown) {
      _captureError(e)
    }
  }

  // Single document detail
  const currentDocument = ref<AssetDocumentDetail | null>(null)

  async function fetchDocument(name: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const res = await apiGetDocument(name)
      if (res) currentDocument.value = res
    } catch (e: unknown) {
      _captureError(e)
    } finally {
      loading.value = false
    }
  }

  async function updateDocument(name: string, data: Partial<AssetDocumentDetail>) {
    loading.value = true
    error.value = null
    try {
      const res = await apiUpdateDocument(name, data)
      if (currentDocument.value?.name === name) {
        currentDocument.value = { ...currentDocument.value, ...data }
      }
      return { success: true, data: res }
    } catch (e: unknown) {
      _captureError(e)
      return null
    } finally {
      loading.value = false
    }
  }

  async function createDocument(data: Partial<AssetDocumentDetail>) {
    loading.value = true
    error.value = null
    try {
      return await apiCreateDocument(data)
    } catch (e: unknown) {
      _captureError(e)
      return null
    } finally {
      loading.value = false
    }
  }

  function changePage(page: number) {
    fetchDocuments(currentFilters.value, page)
  }

  function clearError() {
    error.value = null
    lastApiError.value = null
  }

  function fetchDocumentHistory(name: string) {
    return apiGetDocumentHistory(name)
      .then(res => res)
      .catch(() => null)
  }

  return {
    // state
    documents, loading, error, lastApiError, pagination, currentFilters,
    assetDocuments, assetCompletenessPct, assetDocumentStatus, missingRequired,
    assetIsCompliant, assetExpiredRequired, assetExpiringRequired,
    assetRequiredTotal, assetRequiredSatisfied, assetHiddenCount,
    dashboardStats, dashboardLoading, documentRequests, expiringDocs,
    currentDocument,
    // getters
    totalDocuments, pendingReviewDocs, expiredDocs, kpis, openRequests,
    // actions
    fetchDocuments, fetchAssetDocuments, fetchDashboardStats,
    approveDocument, rejectDocument, createRequest,
    fetchDocumentRequests, fetchExpiringDocuments,
    fetchDocument, updateDocument, createDocument,
    fetchDocumentHistory,
    changePage, clearError,
  }
})
