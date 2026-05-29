// Copyright (c) 2026, AssetCore Team — IMM-12 Incident store
import { ref } from 'vue'
import { defineStore } from 'pinia'
import {
  listIncidents,
  getDashboard,
  getIncidentStats,
  startWork as apiStartWork,
  listRcas,
} from '@/api/imm12'
import type { IncidentDetail, DashboardData, DashboardStats, IncidentStats, RcaListItem } from '@/api/imm12'

const DEFAULT_PAGINATION = { total: 0, page: 1, page_size: 20, total_pages: 1, offset: 0 }

export const useImm12Store = defineStore('imm12', () => {
  const incidents = ref<IncidentDetail[]>([])
  const pagination = ref({ ...DEFAULT_PAGINATION })
  const loading = ref(false)
  const error = ref<string | null>(null)

  const dashboard = ref<DashboardData | null>(null)
  const dashboardLoading = ref(false)
  const dashboardError = ref<string | null>(null)

  const stats = ref<DashboardStats | IncidentStats | null>(null)

  const rcaListItems = ref<RcaListItem[]>([])
  const rcaPagination = ref({ ...DEFAULT_PAGINATION })
  const rcaLoading = ref(false)
  const rcaError = ref<string | null>(null)

  async function fetchList(params: {
    page?: number
    page_size?: number
    status?: string
    severity?: string
    asset?: string
  } = {}) {
    loading.value = true
    error.value = null
    try {
      const res = await listIncidents(params)
      if (res?.items) {
        incidents.value = res.items
        pagination.value = res.pagination as typeof pagination.value
      }
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      loading.value = false
    }
  }

  async function fetchDashboard() {
    dashboardLoading.value = true
    dashboardError.value = null
    try {
      const res = await getDashboard()
      dashboard.value = res
      if (res?.stats) stats.value = res.stats
    } catch (e: unknown) {
      dashboardError.value = e instanceof Error ? e.message : String(e)
    } finally {
      dashboardLoading.value = false
    }
  }

  async function fetchStats() {
    try {
      stats.value = await getIncidentStats()
    } catch {
      // non-blocking
    }
  }

  async function startWork(name: string, notes = '') {
    return apiStartWork(name, notes)
  }

  async function fetchRcas(params: {
    page?: number
    page_size?: number
    method?: string
    status?: string
    asset?: string
  } = {}) {
    rcaLoading.value = true
    rcaError.value = null
    try {
      const res = await listRcas(params)
      if (res?.items) {
        rcaListItems.value = res.items
        rcaPagination.value = res.pagination as typeof rcaPagination.value
      }
    } catch (e: unknown) {
      rcaError.value = e instanceof Error ? e.message : String(e)
    } finally {
      rcaLoading.value = false
    }
  }

  return {
    incidents, pagination, loading, error,
    dashboard, dashboardLoading, dashboardError,
    stats,
    rcaListItems, rcaPagination, rcaLoading, rcaError,
    fetchList, fetchDashboard, fetchStats, startWork, fetchRcas,
  }
})
