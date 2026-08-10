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
  generateInternalQr as apiGenerateQr,
  submitBaselineChecklist as apiSubmitChecklist,
  clearClinicalHold as apiClearHold,
  approveClinicalRelease as apiApproveRelease,
  getDashboardStats as apiGetDashboardStats,
  closeNonConformance as apiCloseNC,
  deleteCommissioning as apiDelete,
  cancelCommissioning as apiCancel,
  getPoDetails as apiGetPoDetails,
} from '@/api/imm04'
import type { BaselineResultInput, BaselineOverallResult } from '@/api/imm04'
import { frappeGet } from '@/api/helpers'
import { ApiError, toApiError } from '@/api/errors'
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
  DocumentRecord,
  BaselineTest,
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
  return { is_unique: res?.is_unique ?? true, existing_commissioning: res?.existing_commissioning }
}

export const useCommissioningStore = defineStore('commissioning', () => {
  const auth = useAuthStore()

  // ─── State ──────────────────────────────────────────────────────────────────
  const list = ref<CommissioningListItem[]>([])
  const currentDoc = ref<CommissioningDoc | null>(null)
  const loading = ref(false)
  const listLoading = ref(false)
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
    if (currentDoc.value.workflow_state !== 'Clinical Release') return false
    return auth.canSubmit
  })

  /** Số NC đang Open */
  const openNcCount = computed(() => _openNcCount.value)
  const hasOpenNc = computed(() => _openNcCount.value > 0)

  /** Tất cả tài liệu bắt buộc đã nhận chưa */
  const allDocumentsReceived = computed(() => {
    if (!currentDoc.value?.commissioning_documents?.length) return false
    return currentDoc.value.commissioning_documents
      .filter((d: DocumentRecord) => d.is_mandatory)
      .every((d: DocumentRecord) => d.status === 'Received' || d.status === 'Waived')
  })

  /** Số tài liệu bắt buộc còn chờ */
  const pendingDocCount = computed(() => {
    if (!currentDoc.value?.commissioning_documents) return 0
    return currentDoc.value.commissioning_documents.filter(
      (d: DocumentRecord) => d.is_mandatory && d.status !== 'Received' && d.status !== 'Waived',
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
    return currentDoc.value.baseline_tests.filter((t: BaselineTest) => t.test_result === 'Fail').length
  })

  // ─── Actions ────────────────────────────────────────────────────────────────

  /** Ghi nhận lỗi: vừa set string (legacy banner) vừa giữ ApiError (notify). */
  function _captureError(e: unknown): void {
    const err = toApiError(e)
    lastApiError.value = err
    error.value = err.message
  }

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
      _captureError(e)
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
        currentDoc.value = res
      } else {
        error.value = `Không tìm thấy phiếu ${name}`
      }
    } catch (e) {
      _captureError(e)
    } finally {
      loading.value = false
    }
  }

  /**
   * Thực hiện workflow transition.
   *
   * `boardApprover` (CR-54 §1): người ký BGĐ truyền kèm cho action dẫn tới
   * 'Clinical Release' → BE set trong cùng transition (1 call), gỡ deadlock
   * gate G06. Không truyền / rỗng → hành vi caller cũ y hệt (BE bỏ qua param
   * với action không phát hành). Lỗi cấu trúc (IMM04-GATE-G06-APPROVER thiếu
   * người ký · FORBIDDEN 4-eyes) đi qua `_captureError` → `lastApiError` để
   * view render bằng `notify.fromError`, KHÔNG để 417 thô rơi ra.
   */
  async function transitionState(name: string, action: string, boardApprover?: string): Promise<boolean> {
    loading.value = true
    error.value = null

    try {
      const res = await apiTransition(name, action, boardApprover)
      if (res) {
        // Reload chi tiết sau khi transition thành công
        await fetchDetail(name)
        return true
      } else {
        error.value = `Không thể thực hiện hành động '${action}'`
        return false
      }
    } catch (e) {
      _captureError(e)
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
      _captureError(e)
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
      _captureError(e)
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
      _captureError(e)
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
      _captureError(e)
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
      _captureError(e)
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
    lastApiError.value = null
  }

  /** Reset store về trạng thái ban đầu */
  function reset(): void {
    list.value = []
    currentDoc.value = null
    loading.value = false
    listLoading.value = false
    error.value = null
    lastApiError.value = null
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
      _captureError(e)
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
      _captureError(e)
      return false
    } finally {
      loading.value = false
    }
  }

  /** BUG-009: Sinh QR nội bộ thủ công (idempotent). */
  async function generateInternalQr(name: string): Promise<string | null> {
    loading.value = true
    error.value = null
    try {
      const res = await apiGenerateQr(name)
      if (res && res.internal_tag_qr) {
        await fetchDetail(name)
        return res.internal_tag_qr
      }
      error.value = 'Không thể sinh mã QR'
      return null
    } catch (e) {
      _captureError(e)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Nộp kết quả baseline (gate Nghiệm thu ban đầu / Kiểm tra lại).
   * Trả `testsRecorded` = số dòng THỰC server ghi test_result (silent-completion lens):
   * View chỉ được coi là ĐÃ GHI khi `ok && testsRecorded > 0`, KHÔNG tin HTTP-200 trần.
   * `overallResult` là SSoT của SERVER ('Pass' | 'Fail'): phép đo KHÔNG ĐẠT vẫn được
   * LƯU (CR-54 §2) nên `ok=true` KHÔNG đồng nghĩa "đạt" — view phải đọc `overallResult`
   * + `failedParameters` để hiển thị đúng, KHÔNG suy diễn từ HTTP-200.
   */
  async function submitBaselineChecklist(
    name: string,
    results: BaselineResultInput[],
  ): Promise<{
    ok: boolean
    testsRecorded: number
    overallResult: BaselineOverallResult | ''
    failedParameters: string[]
    clinicalHoldRequired?: boolean
  }> {
    loading.value = true
    error.value = null
    try {
      const res = await apiSubmitChecklist(name, results)
      if (res !== undefined && res !== null) {
        await fetchDetail(name)
        return {
          ok: true,
          testsRecorded: typeof res.tests_recorded === 'number' ? res.tests_recorded : 0,
          overallResult: res.overall_result ?? '',
          failedParameters: Array.isArray(res.failed_parameters) ? res.failed_parameters : [],
          clinicalHoldRequired: res.clinical_hold_required,
        }
      }
      error.value = 'Không thể nộp kết quả'
      return { ok: false, testsRecorded: 0, overallResult: '', failedParameters: [] }
    } catch (e) {
      _captureError(e)
      return { ok: false, testsRecorded: 0, overallResult: '', failedParameters: [] }
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
      _captureError(e)
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
      _captureError(e)
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
  const dashboardError = ref<string | null>(null)

  // KPI strip lives on the list page (Core Doc docs/imm-04/06_Frontend_Design.md §3.1).
  // It must be non-blocking: do NOT touch the shared `loading`/`error` refs, otherwise a
  // KPI failure would hijack the list's loading skeleton / error banner. Uses its own
  // dashboardError ref and swallows the failure (KPI strip simply renders nothing).
  async function fetchDashboardStats(): Promise<void> {
    dashboardError.value = null
    try {
      const res = await apiGetDashboardStats()
      if (res) dashboardStats.value = res
      else dashboardError.value = 'Không tải được dashboard'
    } catch (e: unknown) {
      dashboardError.value = e instanceof Error ? e.message : String(e)
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
      ncList.value = res ?? []
      _openNcCount.value = ncList.value.filter(n => n.resolution_status === 'Open').length
    } catch (e) {
      _captureError(e)
    } finally {
      loading.value = false
    }
  }

  async function doCloseNonConformance(ncName: string, rootCause: string, correctiveAction: string): Promise<boolean> {
    try {
      await apiCloseNC(ncName, rootCause, correctiveAction)
      return true
    } catch (e) {
      _captureError(e)
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
        '/api/method/assetcore.api.imm04.get_lifecycle_timeline',
        { name: commissioningId },
      )
      timeline.value = res?.events ?? []
    } catch (e) {
      _captureError(e)
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
    lastApiError,
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
    generateInternalQr,
    submitBaselineChecklist,
    clearClinicalHold,
    approveClinicalRelease,
    setOpenNcCount,
    dashboardStats, dashboardError, fetchDashboardStats,
    ncList, fetchNonConformances, doCloseNonConformance,
    timeline, fetchTimeline,
  }
})
