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
      const res = await listDocuments(filters, page, pagination.value.page_size) as unknown as { items?: typeof documents.value; pagination?: typeof pagination.value } | null
      if (res?.items) {
        documents.value = res.items
        if (res.pagination) pagination.value = res.pagination
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
      const res = await getAssetDocuments(asset) as unknown as {
        documents?: typeof assetDocuments.value; completeness_pct?: number;
        document_status?: string; missing_required?: typeof missingRequired.value
      } | null
      if (res) {
        if (res.documents) assetDocuments.value = res.documents
        if (res.completeness_pct != null) assetCompletenessPct.value = res.completeness_pct
        if (res.document_status) assetDocumentStatus.value = res.document_status
        if (res.missing_required) missingRequired.value = res.missing_required
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
      const res = await getDashboardStats() as unknown as typeof dashboardStats.value
      if (res) dashboardStats.value = res
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Lỗi kết nối'
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
      error.value = e instanceof Error ? e.message : 'Approve thất bại'
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
      error.value = e instanceof Error ? e.message : 'Reject thất bại'
      return false
    }
  }

  async function createRequest(payload: Parameters<typeof apiCreateRequest>[0]): Promise<string | null> {
    try {
      const res = await apiCreateRequest(payload) as unknown as { name?: string }
      return res?.name || null
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Tạo yêu cầu thất bại'
      return null
    }
  }

  async function fetchDocumentRequests(assetRef = '', status = '') {
    try {
      const res = await getDocumentRequests(assetRef, status) as unknown as { items?: typeof documentRequests.value } | null
      if (res?.items) documentRequests.value = res.items
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Lỗi kết nối'
    }
  }

  async function fetchExpiringDocuments(days = 30) {
    try {
      const res = await getExpiringDocuments(days) as unknown as { items?: typeof expiringDocs.value } | null
      if (res?.items) expiringDocs.value = res.items
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
      const res = await apiGetDocument(name) as unknown as AssetDocumentDetail | null
      if (res) currentDocument.value = res
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Không tải được tài liệu'
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

  function fetchDocumentHistory(name: string) {
    return apiGetDocumentHistory(name)
      .then(res => res)
      .catch(() => null)
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
    fetchDocumentHistory,
    changePage, clearError,
  }
})
