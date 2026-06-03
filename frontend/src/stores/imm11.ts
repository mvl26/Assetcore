// Copyright (c) 2026, AssetCore Team — IMM-11 Calibration store
import { ref } from 'vue'
import { defineStore } from 'pinia'
import {
  listCalibrations,
  listCalibrationSchedules,
  getCalibrationKpis,
  getDueCalibrations,
  createCalibration,
  submitCalibration,
  cancelCalibration,
  sendToLab,
  receiveCertificate,
} from '@/api/imm11'
import type { AssetCalibration, CalibrationSchedule, CalibrationKpis, DueCalibrationItem } from '@/api/imm11'
import { ApiError, toApiError } from '@/api/errors'

const DEFAULT_PAGINATION = { total: 0, page: 1, page_size: 20, total_pages: 1 }

export const useImm11Store = defineStore('imm11', () => {
  const calibrations = ref<AssetCalibration[]>([])
  const pagination = ref({ ...DEFAULT_PAGINATION })
  const loading = ref(false)
  const error = ref<string | null>(null)
  // Notification framework (Sprint 2026-05-29 vòng 4): giữ ApiError đã hydrate
  // (message_code/severity/title/action_hint) để view gọi notify.fromError().
  const lastApiError = ref<ApiError | null>(null)

  const schedules = ref<CalibrationSchedule[]>([])
  const schedulesLoading = ref(false)

  const kpis = ref<CalibrationKpis | null>(null)
  const kpisLoading = ref(false)

  const dueItems = ref<DueCalibrationItem[]>([])

  /** Ghi nhận lỗi: vừa set string (legacy banner) vừa giữ ApiError (notify). */
  function _captureError(e: unknown): void {
    const err = toApiError(e)
    lastApiError.value = err
    error.value = err.message
  }

  async function fetchList(params: {
    page?: number
    page_size?: number
    status?: string
    asset?: string
    calibration_type?: string
    overall_result?: string
  } = {}) {
    loading.value = true
    error.value = null
    try {
      const f: Record<string, unknown> = {}
      if (params.status) f.status = params.status
      if (params.asset) f.asset = params.asset
      if (params.calibration_type) f.calibration_type = params.calibration_type
      if (params.overall_result) f.overall_result = params.overall_result
      const res = await listCalibrations(
        f,
        params.page ?? 1,
        params.page_size ?? 20,
      )
      calibrations.value = res.data ?? []
      if (res.pagination) pagination.value = res.pagination as typeof pagination.value
    } catch (e: unknown) {
      _captureError(e)
    } finally {
      loading.value = false
    }
  }

  async function fetchSchedules(filters = {}) {
    schedulesLoading.value = true
    try {
      const res = await listCalibrationSchedules(filters, 1, 100)
      schedules.value = res.data ?? []
    } catch (e: unknown) {
      _captureError(e)
    } finally {
      schedulesLoading.value = false
    }
  }

  async function fetchKpis(year?: number, month?: number) {
    kpisLoading.value = true
    try {
      kpis.value = await getCalibrationKpis(year, month)
    } catch (e: unknown) {
      _captureError(e)
    } finally {
      kpisLoading.value = false
    }
  }

  async function fetchDue() {
    try {
      const res = await getDueCalibrations()
      dueItems.value = res.items ?? []
    } catch { /* non-blocking */ }
  }

  // ─── Mutating actions: trả về data khi OK, null khi fail (giữ lastApiError) ──

  async function doCreate(payload: Parameters<typeof createCalibration>[0]) {
    try {
      return await createCalibration(payload)
    } catch (e: unknown) {
      _captureError(e)
      return null
    }
  }

  async function doSubmit(name: string) {
    try {
      return await submitCalibration(name)
    } catch (e: unknown) {
      _captureError(e)
      return null
    }
  }

  async function doCancel(name: string, reason: string) {
    try {
      return await cancelCalibration(name, reason)
    } catch (e: unknown) {
      _captureError(e)
      return null
    }
  }

  async function doSendToLab(name: string, payload: Parameters<typeof sendToLab>[1]) {
    try {
      return await sendToLab(name, payload)
    } catch (e: unknown) {
      _captureError(e)
      return null
    }
  }

  async function doReceiveCertificate(name: string, payload: Parameters<typeof receiveCertificate>[1]) {
    try {
      return await receiveCertificate(name, payload)
    } catch (e: unknown) {
      _captureError(e)
      return null
    }
  }

  return {
    calibrations, pagination, loading, error, lastApiError,
    schedules, schedulesLoading,
    kpis, kpisLoading,
    dueItems,
    fetchList, fetchSchedules, fetchKpis, fetchDue,
    doCreate, doSubmit, doCancel, doSendToLab, doReceiveCertificate,
    _captureError,
  }
})
