// Copyright (c) 2026, AssetCore Team
// Pinia store cho trang HTM Command Center (/dashboard).
// Gom toàn bộ KPI + biểu đồ + danh sách cảnh báo vào 1 lần gọi API
// (assetcore.api.dashboard.get_dashboard_data).

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { frappeGet } from '@/api/helpers'

const ENDPOINT = '/api/method/assetcore.api.dashboard.get_dashboard_data'
const CACHE_TTL_MS = 60 * 1000

export interface KpiMetrics {
  total_assets: number
  under_repair: number
  under_maintenance: number
  pending_commissioning: number
}

export interface StatusChart {
  labels: string[]
  series: number[]
  colors: string[]
}

export interface UpcomingItem {
  asset: string
  asset_name: string
  department: string | null
  department_name: string | null
  due_date: string
  kind: 'PM' | 'Hiệu chuẩn'
  detail: string | null
  days_until: number | null
}

export interface ActiveRepair {
  name: string
  asset: string
  asset_name: string | null
  department: string | null
  department_name: string | null
  status: string
  priority: string
  open_datetime: string
  downtime_days: number
}

export interface DashboardData {
  generated_at: string
  kpi_metrics: KpiMetrics
  asset_status_chart: StatusChart
  upcoming_maintenance: UpcomingItem[]
  active_repairs: ActiveRepair[]
}

export const useDashboardStore = defineStore('dashboard', () => {
  const data = ref<DashboardData | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const loadedAt = ref(0)

  function isFresh(): boolean {
    return data.value != null && (Date.now() - loadedAt.value) < CACHE_TTL_MS
  }

  async function load(opts: { force?: boolean } = {}): Promise<void> {
    if (!opts.force && isFresh()) return
    loading.value = true
    error.value = null
    try {
      data.value = await frappeGet<DashboardData>(ENDPOINT)
      loadedAt.value = Date.now()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Không tải được dashboard'
    } finally {
      loading.value = false
    }
  }

  function invalidate() {
    loadedAt.value = 0
  }

  return { data, loading, error, load, invalidate }
})
