// Copyright (c) 2026, AssetCore Team — IMM-12 Incident store
import { ref } from 'vue'
import { defineStore } from 'pinia'
import {
  listIncidents,
  getDashboard,
  getIncidentStats,
} from '@/api/imm12'
import type { IncidentDetail, DashboardData, DashboardStats } from '@/api/imm12'

const DEFAULT_PAGINATION = { total: 0, page: 1, page_size: 20, total_pages: 1, offset: 0 }

export const useImm12Store = defineStore('imm12', () => {
  const incidents = ref<IncidentDetail[]>([])
  const pagination = ref({ ...DEFAULT_PAGINATION })
  const loading = ref(false)
  const error = ref<string | null>(null)

  const dashboard = ref<DashboardData | null>(null)
  const dashboardLoading = ref(false)
  const dashboardError = ref<string | null>(null)

  const stats = ref<DashboardStats | null>(null)

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
      const res = await listIncidents(params) as unknown as {
        items: IncidentDetail[]
        pagination: typeof pagination.value
      }
      if (res?.items) {
        incidents.value = res.items
        pagination.value = res.pagination
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
      const res = await getDashboard() as unknown as DashboardData
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
      const res = await getIncidentStats() as unknown as DashboardStats
      stats.value = res
    } catch {
      // non-blocking
    }
  }

  return {
    incidents, pagination, loading, error,
    dashboard, dashboardLoading, dashboardError,
    stats,
    fetchList, fetchDashboard, fetchStats,
  }
})
