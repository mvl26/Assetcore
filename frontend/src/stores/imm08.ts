// Copyright (c) 2026, AssetCore Team
// Pinia Store cho Module IMM-08

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  listPMWorkOrders, getPMWorkOrder, assignTechnician,
  submitPMResult, reportMajorFailure, getPMCalendar,
  getPMDashboardStats, reschedulePM, getAssetPMHistory,
  type PMWorkOrder, type PMCalendarEvent, type PMDashboardStats,
} from '@/api/imm08'
import { ApiError, toApiError } from '@/api/errors'

export const useImm08Store = defineStore('imm08', () => {
  // --- State ---
  const workOrders = ref<PMWorkOrder[]>([])
  const currentWO = ref<PMWorkOrder | null>(null)
  const calendarEvents = ref<PMCalendarEvent[]>([])
  const calendarSummary = ref({ total: 0, completed: 0, overdue: 0, pending: 0 })
  const dashboardStats = ref<PMDashboardStats | null>(null)
  const pmHistory = ref<PMWorkOrder[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  // Notification framework (Sprint 2026-05-29 vòng 3): giữ ApiError đã hydrate
  // (message_code/severity/title/action_hint) để view gọi notify.fromError().
  const lastApiError = ref<ApiError | null>(null)
  const pagination = ref({ page: 1, total: 0, total_pages: 0, page_size: 20 })

  /** Ghi nhận lỗi: vừa set string (legacy banner) vừa giữ ApiError (notify). */
  function _captureError(e: unknown): void {
    const err = toApiError(e)
    lastApiError.value = err
    error.value = err.message
  }

  // --- Getters ---
  const overdueWOs = computed(() => workOrders.value.filter(w => w.status === 'Overdue'))
  const openWOs = computed(() => workOrders.value.filter(w => w.status === 'Open'))
  // Một mục được coi là "đã chấm" khi có kết quả hợp lệ (Đạt/Không đạt/N/A),
  // KHÔNG tính chuỗi rỗng/null/undefined (BR-08-08).
  const RATED_RESULTS = ['Pass', 'Fail–Minor', 'Fail–Major', 'N/A']
  const isRated = (r: { result: string | null }) =>
    r.result != null && RATED_RESULTS.includes(r.result)
  const ratedCount = computed(() =>
    currentWO.value?.checklist_results.filter(isRated).length ?? 0
  )
  const checklistComplete = computed(() => {
    if (!currentWO.value) return false
    const items = currentWO.value.checklist_results
    return items.length > 0 && items.every(isRated)
  })
  const hasMinorFailure = computed(() =>
    currentWO.value?.checklist_results.some(r => r.result === 'Fail–Minor') ?? false
  )
  const hasMajorFailure = computed(() =>
    currentWO.value?.checklist_results.some(r => r.result === 'Fail–Major') ?? false
  )

  // --- Actions ---
  async function fetchWorkOrders(filters = {}, page = 1) {
    loading.value = true
    error.value = null
    try {
      const res = await listPMWorkOrders(filters, page)
      workOrders.value = res.data
      pagination.value = res.pagination
    } catch (e: unknown) {
      _captureError(e)
    } finally {
      loading.value = false
    }
  }

  async function fetchWorkOrder(name: string) {
    loading.value = true
    error.value = null
    try {
      currentWO.value = await getPMWorkOrder(name)
    } catch (e: unknown) {
      _captureError(e)
    } finally {
      loading.value = false
    }
  }

  function updateChecklistResult(idx: number, updates: Partial<PMWorkOrder['checklist_results'][0]>) {
    if (!currentWO.value) return
    const item = currentWO.value.checklist_results.find(r => r.idx === idx)
    if (item) Object.assign(item, updates)
  }

  async function doAssignTechnician(name: string, technician: string, scheduledDate?: string): Promise<boolean> {
    try {
      await assignTechnician(name, technician, scheduledDate)
      await fetchWorkOrder(name)
      return true
    } catch (e: unknown) {
      _captureError(e)
      return false
    }
  }

  async function doSubmitResult(summary: string, stickerAttached: boolean, durationMin: number): Promise<{ success: boolean; cmWoCreated?: string | null }> {
    if (!currentWO.value) return { success: false }
    try {
      const res = await submitPMResult({
        name: currentWO.value.name,
        checklist_results: currentWO.value.checklist_results,
        overall_result: hasMajorFailure.value ? 'Fail' : hasMinorFailure.value ? 'Pass with Minor Issues' : 'Pass',
        technician_notes: summary,
        pm_sticker_attached: stickerAttached,
        duration_minutes: durationMin,
      })
      await fetchWorkOrder(currentWO.value.name)
      return { success: true, cmWoCreated: res.cm_wo_created }
    } catch (e: unknown) {
      _captureError(e)
      return { success: false }
    }
  }

  async function doReportMajorFailure(description: string): Promise<string | null> {
    if (!currentWO.value) return null
    try {
      const res = await reportMajorFailure(currentWO.value.name, description)
      await fetchWorkOrder(currentWO.value.name)
      return res.cm_wo_created
    } catch (e: unknown) {
      _captureError(e)
      return null
    }
  }

  async function fetchCalendar(year: number, month: number) {
    loading.value = true
    try {
      const res = await getPMCalendar(year, month)
      calendarEvents.value = res.events
      calendarSummary.value = res.summary
    } catch (e: unknown) {
      _captureError(e)
    } finally {
      loading.value = false
    }
  }

  async function fetchDashboardStats(year?: number, month?: number) {
    loading.value = true
    try {
      dashboardStats.value = await getPMDashboardStats(year, month)
    } catch (e: unknown) {
      _captureError(e)
    } finally {
      loading.value = false
    }
  }

  async function doReschedule(name: string, newDate: string, reason: string): Promise<boolean> {
    try {
      await reschedulePM(name, newDate, reason)
      await fetchWorkOrders()
      return true
    } catch (e: unknown) {
      _captureError(e)
      return false
    }
  }

  async function fetchPMHistory(assetRef: string) {
    try {
      const res = await getAssetPMHistory(assetRef)
      pmHistory.value = res.history
    } catch (e: unknown) {
      _captureError(e)
    }
  }

  return {
    workOrders, currentWO, calendarEvents, calendarSummary, dashboardStats,
    pmHistory, loading, error, lastApiError, pagination,
    overdueWOs, openWOs, checklistComplete, ratedCount, hasMinorFailure, hasMajorFailure,
    fetchWorkOrders, fetchWorkOrder, updateChecklistResult,
    doAssignTechnician, doSubmitResult, doReportMajorFailure,
    fetchCalendar, fetchDashboardStats, doReschedule, fetchPMHistory,
  }
})
