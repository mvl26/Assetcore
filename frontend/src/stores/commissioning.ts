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
  getDashboardStats as apiGetDashboardStats,
  closeNonConformance as apiCloseNC,
  deleteCommissioning as apiDelete,
  cancelCommissioning as apiCancel,
  getPoDetails as apiGetPoDetails,
} from '@/api/imm04'
import { frappeGet } from '@/api/helpers'
import { useAuthStore } from './auth'
import type {
  CommissioningDoc,
  CommissioningListItem,
  CommissioningFilters,
  Pagination,
  WorkflowTransition,
  DashboardStats,
  NonConformance,
  LifecycleEvent,
  PoDetails,
  DeviceModelDetails,
} from '@/types/imm04'

// ─── Module-level helpers (no store state needed) ─────────────────────────────

export function fetchPoDetails(poName: string): Promise<PoDetails | null> {
  return apiGetPoDetails(poName).then(res => res ?? null).catch(() => null)
}

export function fetchDeviceModelDetails(modelName: string): Promise<DeviceModelDetails | null> {
  return frappeGet<DeviceModelDetails>('/api/method/assetcore.api.imm00.get_device_model', { name: modelName })
    .catch(() => null) as Promise<DeviceModelDetails | null>
}

/** Kiểm tra Serial Number có trùng không — pure API call, không cần store state */
export async function checkSnUnique(
  sn: string,
  excludeName = '',
): Promise<{ is_unique: boolean; existing_commissioning?: string }> {
  const res = await apiCheckSn(sn, excludeName)
  const r = res as unknown as { is_unique?: boolean; existing_commissioning?: string } | null
  return { is_unique: r?.is_unique ?? true, existing_commissioning: r?.existing_commissioning }
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
      if (res) {
        list.value = res.items
        pagination.value = res.pagination
      } else {
        error.value = 'Không thể tải danh sách phiếu'
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
      if (res) {
        currentDoc.value = res as unknown as typeof currentDoc.value
      } else {
        error.value = `Không tìm thấy phiếu ${name}`
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
      if (res) {
        // Reload chi tiết sau khi transition thành công
        await fetchDetail(name)
        return true
      } else {
        error.value = `Không thể thực hiện hành động '${action}'`
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
      if (res) {
        // Reload sau khi Submit
        await fetchDetail(name)
        return true
      } else {
        error.value = 'Không thể Submit phiếu'
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
      if (res !== undefined && res !== null) {
        await fetchDetail(name)
        return true
      } else {
        error.value = 'Không thể lưu phiếu'
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
      if (res) {
        return res.name
      } else {
        error.value = 'Không thể tạo phiếu'
        return null
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi không xác định'
      return null
    } finally {
      loading.value = false
    }
  }

  /** Xóa phiếu (chỉ Draft — docstatus=0) */
  async function deleteDoc(name: string): Promise<boolean> {
    loading.value = true
    error.value = null
    try {
      await apiDelete(name)
      return true
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Không thể xóa phiếu'
      return false
    } finally {
      loading.value = false
    }
  }

  /** Hủy phiếu đã Submit (docstatus 1→2) — chỉ IMM Operations Manager / IMM Workshop Lead */
  async function cancelDoc(name: string): Promise<boolean> {
    loading.value = true
    error.value = null
    try {
      await apiCancel(name)
      await fetchDetail(name)
      return true
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Không thể hủy phiếu'
      return false
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
      if (res !== undefined && res !== null) {
        _openNcCount.value += 1
        return true
      }
      error.value = 'Không thể tạo NC'
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
      if (res !== undefined && res !== null) {
        await fetchDetail(name)
        return true
      }
      error.value = 'Không thể gán định danh'
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
    results: Array<{ parameter: string; test_result: string; measured_val?: number; fail_note?: string }>,
  ): Promise<{ ok: boolean; clinicalHoldRequired?: boolean }> {
    loading.value = true
    error.value = null
    try {
      const res = await apiSubmitChecklist(name, results)
      if (res !== undefined && res !== null) {
        await fetchDetail(name)
        return { ok: true, clinicalHoldRequired: res?.clinical_hold_required }
      }
      error.value = 'Không thể nộp kết quả'
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
      if (res !== undefined && res !== null) {
        await fetchDetail(name)
        return true
      }
      error.value = 'Không thể gỡ Clinical Hold'
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
      if (res !== undefined && res !== null) {
        await fetchDetail(name)
        return true
      }
      error.value = 'Không thể phê duyệt Release'
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

  // ─── Dashboard ──────────────────────────────────────────────────────────────

  const dashboardStats = ref<DashboardStats | null>(null)

  async function fetchDashboardStats(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const res = await apiGetDashboardStats()
      if (res) dashboardStats.value = res as unknown as typeof dashboardStats.value
      else error.value = 'Không tải được dashboard'
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi kết nối'
    } finally {
      loading.value = false
    }
  }

  // ─── Non Conformance list ────────────────────────────────────────────────────

  const ncList = ref<NonConformance[]>([])

  async function fetchNonConformances(commissioningId: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const res = await frappeGet<NonConformance[]>(
        '/api/method/assetcore.api.imm04.list_non_conformances',
        { commissioning: commissioningId },
      )
      ncList.value = (res as unknown as NonConformance[]) ?? []
      _openNcCount.value = ncList.value.filter(n => n.resolution_status === 'Open').length
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi kết nối'
    } finally {
      loading.value = false
    }
  }

  async function doCloseNonConformance(ncName: string, rootCause: string, correctiveAction: string): Promise<boolean> {
    try {
      await apiCloseNC(ncName, rootCause, correctiveAction)
      return true
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi kết nối'
      return false
    }
  }

  // ─── Timeline ───────────────────────────────────────────────────────────────

  const timeline = ref<LifecycleEvent[]>([])

  async function fetchTimeline(commissioningId: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const res = await frappeGet<{ events: LifecycleEvent[] }>(
        'assetcore.api.imm04.get_lifecycle_timeline',
        { name: commissioningId },
      )
      timeline.value = (res as any)?.events ?? []
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Lỗi kết nối'
    } finally {
      loading.value = false
    }
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
    deleteDoc,
    cancelDoc,
    refreshList,
    clearError,
    reset,
    reportNonConformance,
    assignIdentification,
    submitBaselineChecklist,
    clearClinicalHold,
    approveClinicalRelease,
    setOpenNcCount,
    dashboardStats, fetchDashboardStats,
    ncList, fetchNonConformances, doCloseNonConformance,
    timeline, fetchTimeline,
  }
})
