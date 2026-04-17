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
} from '@/api/imm05'
import type {
  AssetDocumentItem,
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

  const pagination = ref<Pagination>({
    page: 1,
    page_size: 20,
    total: 0,
    total_pages: 0,
  })
  const currentFilters = ref<DocumentFilters>({})

  // Asset detail view
  const assetDocuments = ref<Record<string, AssetDocumentItem[]>>({})
  const assetCompletenessPct = ref(0)
  const assetDocumentStatus = ref('')
  const missingRequired = ref<string[]>([])

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
    documents.value.filter(d => d.workflow_state === 'Pending_Review')
  )

  const expiredDocs = computed(() =>
    documents.value.filter(d => d.workflow_state === 'Expired')
  )

  const kpis = computed(() => dashboardStats.value?.kpis ?? null)

  const openRequests = computed(() =>
    documentRequests.value.filter(r => r.status === 'Open' || r.status === 'Overdue')
  )

  // ─── Actions ────────────────────────────────────────────────────────────────

  async function fetchDocuments(filters: DocumentFilters = {}, page = 1) {
    loading.value = true
    error.value = null
    currentFilters.value = filters
    try {
      const res = await listDocuments(filters, page, pagination.value.page_size)
      if (res.success) {
        documents.value = res.data.items
        pagination.value = res.data.pagination
      } else {
        error.value = res.error ?? 'Lỗi không xác định'
      }
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Lỗi kết nối'
    } finally {
      loading.value = false
    }
  }

  async function fetchAssetDocuments(asset: string) {
    loading.value = true
    error.value = null
    try {
      const res = await getAssetDocuments(asset)
      if (res.success) {
        assetDocuments.value = res.data.documents
        assetCompletenessPct.value = res.data.completeness_pct
        assetDocumentStatus.value = res.data.document_status
        missingRequired.value = res.data.missing_required
      } else {
        error.value = res.error ?? 'Không tải được hồ sơ'
      }
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Lỗi kết nối'
    } finally {
      loading.value = false
    }
  }

  async function fetchDashboardStats() {
    dashboardLoading.value = true
    error.value = null
    try {
      const res = await getDashboardStats()
      if (res.success) {
        dashboardStats.value = res.data
      }
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Lỗi kết nối'
    } finally {
      dashboardLoading.value = false
    }
  }

  async function approveDocument(name: string): Promise<boolean> {
    try {
      const res = await apiApprove(name)
      if (res.success) {
        // Cập nhật local state
        const doc = documents.value.find(d => d.name === name)
        if (doc) doc.workflow_state = 'Active'
        return true
      }
      error.value = res.error ?? 'Approve thất bại'
      return false
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Lỗi kết nối'
      return false
    }
  }

  async function rejectDocument(name: string, reason: string): Promise<boolean> {
    try {
      const res = await apiReject(name, reason)
      if (res.success) {
        const doc = documents.value.find(d => d.name === name)
        if (doc) doc.workflow_state = 'Rejected'
        return true
      }
      error.value = res.error ?? 'Reject thất bại'
      return false
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Lỗi kết nối'
      return false
    }
  }

  async function createRequest(payload: Parameters<typeof apiCreateRequest>[0]): Promise<string | null> {
    try {
      const res = await apiCreateRequest(payload)
      if (res.success) return res.data.name
      error.value = res.error ?? 'Tạo yêu cầu thất bại'
      return null
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Lỗi kết nối'
      return null
    }
  }

  async function fetchDocumentRequests(assetRef = '', status = '') {
    try {
      const res = await getDocumentRequests(assetRef, status)
      if (res.success) documentRequests.value = res.data.items
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Lỗi kết nối'
    }
  }

  async function fetchExpiringDocuments(days = 30) {
    try {
      const res = await getExpiringDocuments(days)
      if (res.success) expiringDocs.value = res.data.items
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Lỗi kết nối'
    }
  }

  // Single document detail
  const currentDocument = ref<AssetDocumentDetail | null>(null)

  async function fetchDocument(name: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const res = await apiGetDocument(name)
      if (res.success) {
        currentDocument.value = res.data
      } else {
        error.value = res.error ?? 'Không tải được tài liệu'
      }
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Lỗi kết nối'
    } finally {
      loading.value = false
    }
  }

  async function updateDocument(name: string, data: Partial<AssetDocumentDetail>) {
    loading.value = true
    error.value = null
    try {
      const res = await apiUpdateDocument(name, data)
      if (res.success && currentDocument.value?.name === name) {
        currentDocument.value = { ...currentDocument.value, ...data }
      }
      return res
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Lỗi kết nối'
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
      error.value = e instanceof Error ? e.message : 'Lỗi kết nối'
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
  }

  return {
    // state
    documents, loading, error, pagination, currentFilters,
    assetDocuments, assetCompletenessPct, assetDocumentStatus, missingRequired,
    dashboardStats, dashboardLoading, documentRequests, expiringDocs,
    currentDocument,
    // getters
    totalDocuments, pendingReviewDocs, expiredDocs, kpis, openRequests,
    // actions
    fetchDocuments, fetchAssetDocuments, fetchDashboardStats,
    approveDocument, rejectDocument, createRequest,
    fetchDocumentRequests, fetchExpiringDocuments,
    fetchDocument, updateDocument, createDocument,
    changePage, clearError,
  }
})
