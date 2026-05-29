// Copyright (c) 2026, AssetCore Team
// Pinia Store cho Module IMM-09

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  listRepairWorkOrders, getRepairWorkOrder, assignTechnician,
  submitDiagnosis, closeWorkOrder, confirmInspection, getRepairKPIs, getAssetRepairHistory,
  requestSpareParts, startRepair, getMttrReport, createRepairWorkOrder,
  searchSpareParts,
  type AssetRepair, type RepairKPIs, type MttrReport, type SparePartRow,
} from '@/api/imm09'
import { ApiError, toApiError } from '@/api/errors'

export const useImm09Store = defineStore('imm09', () => {
  const workOrders = ref<AssetRepair[]>([])
  const currentWO = ref<AssetRepair | null>(null)
  const kpis = ref<RepairKPIs | null>(null)
  const repairHistory = ref<AssetRepair[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  // Notification framework (Sprint 2026-05-29): giữ nguyên ApiError đã hydrate
  // (message_code/severity/title/action_hint) để view gọi notify.fromError().
  // `error` string vẫn giữ cho backward-compat (inline banner cũ).
  const lastApiError = ref<ApiError | null>(null)
  const pagination = ref({ page: 1, total: 0, total_pages: 0, page_size: 20 })

  /** Ghi nhận lỗi: vừa set string (legacy) vừa giữ ApiError (notify). */
  function _captureError(e: unknown): void {
    const err = toApiError(e)
    lastApiError.value = err
    error.value = err.message
  }

  const openWOs = computed(() => workOrders.value.filter(w => w.status === 'Open'))
  const breachedWOs = computed(() => workOrders.value.filter(w => w.sla_breached))
  const checklistComplete = computed(() => {
    if (!currentWO.value) return false
    return currentWO.value.repair_checklist.every(r => r.result !== null)
  })

  async function fetchWorkOrders(filters = {}, page = 1) {
    loading.value = true
    error.value = null
    try {
      const res = await listRepairWorkOrders(filters, page)
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
      currentWO.value = await getRepairWorkOrder(name)
    } catch (e: unknown) {
      _captureError(e)
    } finally {
      loading.value = false
    }
  }

  function updateChecklistResult(idx: number, updates: Partial<AssetRepair['repair_checklist'][0]>) {
    if (!currentWO.value) return
    const item = currentWO.value.repair_checklist.find(r => r.idx === idx)
    if (item) Object.assign(item, updates)
  }

  async function doAssignTechnician(name: string, technician: string, priority?: string): Promise<boolean> {
    try {
      await assignTechnician(name, technician, priority)
      await fetchWorkOrder(name)
      return true
    } catch (e: unknown) {
      _captureError(e)
      return false
    }
  }

  async function doSubmitDiagnosis(diagnosisNotes: string, needsParts: boolean): Promise<boolean> {
    if (!currentWO.value) return false
    try {
      await submitDiagnosis(currentWO.value.name, diagnosisNotes, needsParts)
      await fetchWorkOrder(currentWO.value.name)
      return true
    } catch (e: unknown) {
      _captureError(e)
      return false
    }
  }

  async function doCloseWorkOrder(payload: Parameters<typeof closeWorkOrder>[0]): Promise<boolean> {
    try {
      await closeWorkOrder(payload)
      await fetchWorkOrder(payload.name)
      return true
    } catch (e: unknown) {
      _captureError(e)
      return false
    }
  }

  async function doConfirmInspection(woName: string): Promise<boolean> {
    try {
      await confirmInspection(woName)
      await fetchWorkOrder(woName)
      return true
    } catch (e: unknown) {
      _captureError(e)
      return false
    }
  }

  async function fetchKPIs(year?: number, month?: number) {
    try {
      kpis.value = await getRepairKPIs(year, month)
    } catch (e: unknown) {
      _captureError(e)
    }
  }

  async function fetchRepairHistory(assetRef: string) {
    try {
      const res = await getAssetRepairHistory(assetRef)
      repairHistory.value = res.history
    } catch (e: unknown) {
      _captureError(e)
    }
  }

  const mttrReport = ref<MttrReport | null>(null)

  async function fetchMttrReport(year: number, month: number) {
    try {
      mttrReport.value = await getMttrReport(year, month)
    } catch (e: unknown) {
      _captureError(e)
    }
  }

  async function doSaveParts(woName: string, parts: SparePartRow[]): Promise<boolean> {
    try {
      await requestSpareParts(woName, parts)
      await fetchWorkOrder(woName)
      return true
    } catch (e: unknown) {
      _captureError(e)
      return false
    }
  }

  async function doStartRepair(woName: string): Promise<boolean> {
    try {
      await startRepair(woName)
      await fetchWorkOrder(woName)
      return true
    } catch (e: unknown) {
      _captureError(e)
      return false
    }
  }

  async function doCreateRepairWorkOrder(payload: Parameters<typeof createRepairWorkOrder>[0]): Promise<string | null> {
    try {
      const res = await createRepairWorkOrder(payload)
      return res.name
    } catch (e: unknown) {
      _captureError(e)
      return null
    }
  }

  function doSearchSpareParts(query: string): Promise<SparePartRow[]> {
    return searchSpareParts(query).catch(() => [])
  }

  return {
    workOrders, currentWO, kpis, repairHistory, mttrReport, loading, error, lastApiError, pagination,
    openWOs, breachedWOs, checklistComplete,
    fetchWorkOrders, fetchWorkOrder, updateChecklistResult,
    doAssignTechnician, doSubmitDiagnosis, doCloseWorkOrder, doConfirmInspection,
    fetchKPIs, fetchRepairHistory, fetchMttrReport, doSaveParts, doStartRepair,
    doCreateRepairWorkOrder, doSearchSpareParts,
  }
})
