// Copyright (c) 2026, AssetCore Team
// Pinia Store cho Module IMM-09

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  listRepairWorkOrders, getRepairWorkOrder, assignTechnician,
  submitDiagnosis, closeWorkOrder, getRepairKPIs, getAssetRepairHistory,
  requestSpareParts, startRepair, getMttrReport,
  type AssetRepair, type RepairKPIs, type MttrReport, type SparePartRow,
} from '@/api/imm09'

export const useImm09Store = defineStore('imm09', () => {
  const workOrders = ref<AssetRepair[]>([])
  const currentWO = ref<AssetRepair | null>(null)
  const kpis = ref<RepairKPIs | null>(null)
  const repairHistory = ref<any[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const pagination = ref({ page: 1, total: 0, total_pages: 0, page_size: 20 })

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
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function fetchWorkOrder(name: string) {
    loading.value = true
    error.value = null
    try {
      currentWO.value = await getRepairWorkOrder(name)
    } catch (e: any) {
      error.value = e.message
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
    } catch (e: any) {
      error.value = e.message
      return false
    }
  }

  async function doSubmitDiagnosis(diagnosisNotes: string, needsParts: boolean): Promise<boolean> {
    if (!currentWO.value) return false
    try {
      await submitDiagnosis(currentWO.value.name, diagnosisNotes, needsParts)
      await fetchWorkOrder(currentWO.value.name)
      return true
    } catch (e: any) {
      error.value = e.message
      return false
    }
  }

  async function doCloseWorkOrder(payload: Parameters<typeof closeWorkOrder>[0]): Promise<boolean> {
    try {
      await closeWorkOrder(payload)
      await fetchWorkOrder(payload.name)
      return true
    } catch (e: any) {
      error.value = e.message
      return false
    }
  }

  async function fetchKPIs(year?: number, month?: number) {
    try {
      kpis.value = await getRepairKPIs(year, month)
    } catch (e: any) {
      error.value = e.message
    }
  }

  async function fetchRepairHistory(assetRef: string) {
    try {
      const res = await getAssetRepairHistory(assetRef) as any
      repairHistory.value = res.history
    } catch (e: any) {
      error.value = e.message
    }
  }

  const mttrReport = ref<MttrReport | null>(null)

  async function fetchMttrReport(year: number, month: number) {
    try {
      mttrReport.value = await getMttrReport(year, month)
    } catch (e: any) {
      error.value = e.message
    }
  }

  async function doSaveParts(woName: string, parts: SparePartRow[]): Promise<boolean> {
    try {
      await requestSpareParts(woName, parts)
      await fetchWorkOrder(woName)
      return true
    } catch (e: any) {
      error.value = e.message
      return false
    }
  }

  async function doStartRepair(woName: string): Promise<boolean> {
    try {
      await startRepair(woName)
      await fetchWorkOrder(woName)
      return true
    } catch (e: any) {
      error.value = e.message
      return false
    }
  }

  return {
    workOrders, currentWO, kpis, repairHistory, mttrReport, loading, error, pagination,
    openWOs, breachedWOs, checklistComplete,
    fetchWorkOrders, fetchWorkOrder, updateChecklistResult,
    doAssignTechnician, doSubmitDiagnosis, doCloseWorkOrder,
    fetchKPIs, fetchRepairHistory, fetchMttrReport, doSaveParts, doStartRepair,
  }
})
