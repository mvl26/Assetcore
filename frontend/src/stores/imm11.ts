// Copyright (c) 2026, AssetCore Team — IMM-11 Calibration store
import { ref } from 'vue'
import { defineStore } from 'pinia'
import {
  listCalibrations,
  listCalibrationSchedules,
  getCalibrationKpis,
  getDueCalibrations,
} from '@/api/imm11'
import type { AssetCalibration, CalibrationSchedule, CalibrationKpis, DueCalibrationItem } from '@/api/imm11'

const DEFAULT_PAGINATION = { total: 0, page: 1, page_size: 20, total_pages: 1 }

export const useImm11Store = defineStore('imm11', () => {
  const calibrations = ref<AssetCalibration[]>([])
  const pagination = ref({ ...DEFAULT_PAGINATION })
  const loading = ref(false)
  const error = ref<string | null>(null)

  const schedules = ref<CalibrationSchedule[]>([])
  const schedulesLoading = ref(false)

  const kpis = ref<CalibrationKpis | null>(null)
  const kpisLoading = ref(false)

  const dueItems = ref<DueCalibrationItem[]>([])

  async function fetchList(params: {
    page?: number
    page_size?: number
    status?: string
    asset?: string
  } = {}) {
    loading.value = true
    error.value = null
    try {
      const res = await listCalibrations(
        { status: params.status, asset: params.asset },
        params.page ?? 1,
        params.page_size ?? 20,
      ) as unknown as { data: AssetCalibration[]; pagination: typeof pagination.value }
      calibrations.value = res.data ?? []
      if (res.pagination) pagination.value = res.pagination
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      loading.value = false
    }
  }

  async function fetchSchedules(filters = {}) {
    schedulesLoading.value = true
    try {
      const res = await listCalibrationSchedules(filters, 1, 100) as unknown as { data: CalibrationSchedule[] }
      schedules.value = res.data ?? []
    } finally {
      schedulesLoading.value = false
    }
  }

  async function fetchKpis(year?: number, month?: number) {
    kpisLoading.value = true
    try {
      const res = await getCalibrationKpis(year, month) as unknown as CalibrationKpis
      kpis.value = res
    } finally {
      kpisLoading.value = false
    }
  }

  async function fetchDue() {
    try {
      const res = await getDueCalibrations() as unknown as { items: DueCalibrationItem[] }
      dueItems.value = res.items ?? []
    } catch { /* non-blocking */ }
  }

  return {
    calibrations, pagination, loading, error,
    schedules, schedulesLoading,
    kpis, kpisLoading,
    dueItems,
    fetchList, fetchSchedules, fetchKpis, fetchDue,
  }
})
