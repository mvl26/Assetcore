// Copyright (c) 2026, AssetCore Team
// Pinia store: commissioning list, current doc, state management

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  listCommissioning,
  getFormContext,
  transitionState as apiTransition,
  submitCommissioning as apiSubmit,
  saveCommissioning as apiSave,
  createCommissioning as apiCreate,
  checkSnUnique as apiCheckSn,
  reportNonConformance as apiReportNC,
  assignIdentification as apiAssignId,
  submitBaselineChecklist as apiSubmitChecklist,
  clearClinicalHold as apiClearHold,
  approveClinicalRelease as apiApproveRelease,
} from '@/api/imm04'
import { useAuthStore } from './auth'
import type {
  CommissioningDoc,
  CommissioningListItem,
  CommissioningFilters,
  Pagination,
  WorkflowTransition,
} from '@/types/imm04'

/** Kiểm tra Serial Number có trùng không — pure API call, không cần store state */
export async function checkSnUnique(
  sn: string,
  excludeName = '',
): Promise<{ is_unique: boolean; existing_commissioning?: string }> {
  const res = await apiCheckSn(sn, excludeName)
  return res.data ?? { is_unique: true }
}

export const useCommissioningStore = defineStore('commissioning', () => {
  const auth = useAuthStore()

  // ─── State ──────────────────────────────────────────────────────────────────
  const list = ref<CommissioningListItem[]>([])
  const currentDoc = ref<CommissioningDoc | null>(null)
  const loading = ref(false)
  const listLoading = ref(false)
  const error = ref<string | null>(null)
  const pagination = ref<Pagination>({
    page: 1,
    page_size: 20,
    total: 0,
    total_pages: 0,
  })
  const currentFilters = ref<CommissioningFilters>({})
  const _openNcCount = ref(0)

  // ─── Getters ────────────────────────────────────────────────────────────────

  /** Phiếu đã Submit (docstatus=1) — không chỉnh sửa được */
  const isLocked = computed(() => {
    return (currentDoc.value?.docstatus ?? 0) === 1
  })

  /** Danh sách actions được phép dựa trên role + state */
  const allowedActions = computed<WorkflowTransition[]>(() => {
    if (!currentDoc.value) return []
    if (isLocked.value) return []
    return currentDoc.value.allowed_transitions ?? []
  })

  /** Phiếu có lỗi DOA không */
  const hasDOAIncident = computed(() => Boolean(currentDoc.value?.doa_incident))

  /** Thiết bị bức xạ */
  const isRadiationDevice = computed(() => Boolean(currentDoc.value?.is_radiation_device))

  /** Baseline tests có pass tất cả không */
  const allBaselinesPassed = computed(() => {
    if (!currentDoc.value?.baseline_tests?.length) return false
    return currentDoc.value.baseline_tests.every((t) => t.test_result === 'Pass')
  })

  /** User hiện tại có thể Submit phiếu này không */
  const canSubmitDoc = computed(() => {
    if (!currentDoc.value) return false
    if (isLocked.value) return false
    if (currentDoc.value.workflow_state !== 'Clinical_Release') return false
    return auth.canSubmit
  })

  /** Số NC đang Open */
  const openNcCount = computed(() => _openNcCount.value)
  const hasOpenNc = computed(() => _openNcCount.value > 0)

  /** Tất cả tài liệu bắt buộc đã nhận chưa */
  const allDocumentsReceived = computed(() => {
    if (!currentDoc.value?.commissioning_documents?.length) return false
    return currentDoc.value.commissioning_documents
      .filter((d: any) => d.is_mandatory)
      .every((d: any) => d.status === 'Received' || d.status === 'Waived')
  })

  /** Số tài liệu bắt buộc còn chờ */
  const pendingDocCount = computed(() => {
    if (!currentDoc.value?.commissioning_documents) return 0
    return currentDoc.value.commissioning_documents.filter(
      (d: any) => d.is_mandatory && d.status !== 'Received' && d.status !== 'Waived',
    ).length
  })

  /** Thiết bị nguy cơ cao (C/D/Radiation) */
  const isHighRisk = computed(() =>
    currentDoc.value?.risk_class != null &&
    ['C', 'D', 'Radiation'].includes(currentDoc.value.risk_class),
  )

  /** Số baseline test Fail */
  const failedChecklistCount = computed(() => {
    if (!currentDoc.value?.baseline_tests) return 0
    return currentDoc.value.baseline_tests.filter((t: any) => t.test_result === 'Fail').length
  })

  // ─── Actions ────────────────────────────────────────────────────────────────

  /** Tải danh sách phiếu với filter và phân trang */
  async function fetchList(
    filters: CommissioningFilters = {},
    page = 1,
    pageSize = 20,
  ): Promise<void> {
    listLoading.value = true
    error.value = null
    currentFilters.value = filters

    try {
      const res = await listCommissioning(filters, page, pageSize)
      if (res.success && res.data) {
        list.value = res.data.items
        pagination.value = res.data.pagination
      } else {
        error.value = res.error ?? 'Không thể tải danh sách phiếu'
        list.value = []
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
      list.value = []
    } finally {
      listLoading.value = false
    }
  }

  /** Tải chi tiết một phiếu */
  async function fetchDetail(name: string): Promise<void> {
    loading.value = true
    error.value = null
    currentDoc.value = null

    try {
      const res = await getFormContext(name)
      if (res.success && res.data) {
        currentDoc.value = res.data
      } else {
        error.value = res.error ?? `Không tìm thấy phiếu ${name}`
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
    } finally {
      loading.value = false
    }
  }

  /** Thực hiện workflow transition */
  async function transitionState(name: string, action: string): Promise<boolean> {
    loading.value = true
    error.value = null

    try {
      const res = await apiTransition(name, action)
      if (res.success && res.data) {
        // Reload chi tiết sau khi transition thành công
        await fetchDetail(name)
        return true
      } else {
        error.value = res.error ?? `Không thể thực hiện hành động '${action}'`
        return false
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
      return false
    } finally {
      loading.value = false
    }
  }

  /** Submit phiếu commissioning */
  async function submitDoc(name: string): Promise<boolean> {
    loading.value = true
    error.value = null

    try {
      const res = await apiSubmit(name)
      if (res.success && res.data) {
        // Reload sau khi Submit
        await fetchDetail(name)
        return true
      } else {
        error.value = res.error ?? 'Không thể Submit phiếu'
        return false
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
      return false
    } finally {
      loading.value = false
    }
  }

  /** Lưu thay đổi inline trên phiếu */
  async function saveDoc(name: string, fields: Record<string, unknown>): Promise<boolean> {
    loading.value = true
    error.value = null

    try {
      const res = await apiSave(name, fields)
      if (res.success) {
        await fetchDetail(name)
        return true
      } else {
        error.value = res.error ?? 'Không thể lưu phiếu'
        return false
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
      return false
    } finally {
      loading.value = false
    }
  }

  /** Tạo phiếu mới */
  async function createDoc(data: Record<string, unknown>): Promise<string | null> {
    loading.value = true
    error.value = null

    try {
      const res = await apiCreate(data)
      if (res.success && res.data) {
        return res.data.name
      } else {
        error.value = res.error ?? 'Không thể tạo phiếu'
        return null
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
      return null
    } finally {
      loading.value = false
    }
  }

  /** Reload trang hiện tại với filter giữ nguyên */
  async function refreshList(): Promise<void> {
    await fetchList(currentFilters.value, pagination.value.page, pagination.value.page_size)
  }

  /** Xóa error */
  function clearError(): void {
    error.value = null
  }

  /** Reset store về trạng thái ban đầu */
  function reset(): void {
    list.value = []
    currentDoc.value = null
    loading.value = false
    listLoading.value = false
    error.value = null
    pagination.value = { page: 1, page_size: 20, total: 0, total_pages: 0 }
    currentFilters.value = {}
    _openNcCount.value = 0
  }

  /** Tạo NC mới */
  async function reportNonConformance(
    name: string,
    ncData: { nc_type: string; severity: string; description: string },
  ): Promise<boolean> {
    loading.value = true
    error.value = null
    try {
      const res = await apiReportNC(name, ncData)
      if (res.success) {
        _openNcCount.value += 1
        return true
      }
      error.value = res.error ?? 'Không thể tạo NC'
      return false
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
      return false
    } finally {
      loading.value = false
    }
  }

  /** Gán định danh thiết bị */
  async function assignIdentification(
    name: string,
    vendorSn: string,
    internalTag = '',
    mohCode = '',
  ): Promise<boolean> {
    loading.value = true
    error.value = null
    try {
      const res = await apiAssignId(name, vendorSn, internalTag, mohCode)
      if (res.success) {
        await fetchDetail(name)
        return true
      }
      error.value = res.error ?? 'Không thể gán định danh'
      return false
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
      return false
    } finally {
      loading.value = false
    }
  }

  /** Nộp kết quả baseline */
  async function submitBaselineChecklist(
    name: string,
    results: Array<{ parameter: string; result: string; measured_val?: number; fail_note?: string }>,
  ): Promise<{ ok: boolean; clinicalHoldRequired?: boolean }> {
    loading.value = true
    error.value = null
    try {
      const res = await apiSubmitChecklist(name, results)
      if (res.success) {
        await fetchDetail(name)
        return { ok: true, clinicalHoldRequired: res.data?.clinical_hold_required }
      }
      error.value = res.error ?? 'Không thể nộp kết quả'
      return { ok: false }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
      return { ok: false }
    } finally {
      loading.value = false
    }
  }

  /** Gỡ Clinical Hold */
  async function clearClinicalHold(name: string, licenseNo = ''): Promise<boolean> {
    loading.value = true
    error.value = null
    try {
      const res = await apiClearHold(name, licenseNo)
      if (res.success) {
        await fetchDetail(name)
        return true
      }
      error.value = res.error ?? 'Không thể gỡ Clinical Hold'
      return false
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
      return false
    } finally {
      loading.value = false
    }
  }

  /** Board phê duyệt Clinical Release */
  async function approveClinicalRelease(
    name: string,
    boardApprover: string,
    remarks = '',
  ): Promise<boolean> {
    loading.value = true
    error.value = null
    try {
      const res = await apiApproveRelease(name, boardApprover, remarks)
      if (res.success) {
        await fetchDetail(name)
        return true
      }
      error.value = res.error ?? 'Không thể phê duyệt Release'
      return false
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
      return false
    } finally {
      loading.value = false
    }
  }

  /** Cập nhật open NC count (gọi sau khi load NC list) */
  function setOpenNcCount(count: number): void {
    _openNcCount.value = count
  }

  return {
    // State
    list,
    currentDoc,
    loading,
    listLoading,
    error,
    pagination,
    currentFilters,
    // Getters
    isLocked,
    allowedActions,
    hasDOAIncident,
    isRadiationDevice,
    allBaselinesPassed,
    canSubmitDoc,
    openNcCount,
    hasOpenNc,
    allDocumentsReceived,
    pendingDocCount,
    isHighRisk,
    failedChecklistCount,
    // Actions
    fetchList,
    fetchDetail,
    transitionState,
    submitDoc,
    saveDoc,
    createDoc,
    refreshList,
    clearError,
    reset,
    reportNonConformance,
    assignIdentification,
    submitBaselineChecklist,
    clearClinicalHold,
    approveClinicalRelease,
    setOpenNcCount,
  }
})
