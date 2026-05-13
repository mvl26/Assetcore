// Copyright (c) 2026, AssetCore Team — IMM-15 Spare Parts Inventory store.
//
// Wraps `@/api/imm15` transactions (Allocation / Cycle Count / Forecast /
// Watchlist / Dashboard / Low-Stock). LIVE master endpoints (Spare Part,
// Warehouse, Stock Movement) stay in `@/api/inventory` and remain consumed
// directly by master/inventory views — IMM-15 store only owns the
// transaction-layer state.
import { ref } from 'vue'
import { defineStore } from 'pinia'
import {
  listAllocations, getAllocation, createAllocation,
  approveAllocation, issueAllocation, returnItems,
  listCycleCounts, createCycleCount, submitCycleCount, postCycleCount,
  listSpareForecasts, generateSpareForecast, approveForecast,
  listWatchlist, addToWatchlist,
  getDashboardStats, getLowStockAlerts,
} from '@/api/imm15'
import type {
  AllocationRow, AllocationDetail, AllocationItem,
  CycleCountRow, ForecastRow, WatchlistRow,
  DashboardStats, LowStockAlert, ForecastMethod,
  Pagination, UrgencyLevel,
} from '@/api/imm15'

const DEFAULT_PAGINATION: Pagination = { total: 0, page: 1, page_size: 20, total_pages: 1 }

export const useImm15Store = defineStore('imm15', () => {
  // Allocations
  const allocations = ref<AllocationRow[]>([])
  const allocationsPagination = ref<Pagination>({ ...DEFAULT_PAGINATION })
  const allocationsLoading = ref(false)
  const allocationDetail = ref<AllocationDetail | null>(null)

  // Cycle Counts
  const cycleCounts = ref<CycleCountRow[]>([])
  const cycleCountsPagination = ref<Pagination>({ ...DEFAULT_PAGINATION })
  const cycleCountsLoading = ref(false)

  // Forecasts
  const forecasts = ref<ForecastRow[]>([])
  const forecastsPagination = ref<Pagination>({ ...DEFAULT_PAGINATION })
  const forecastsLoading = ref(false)

  // Watchlist
  const watchlist = ref<WatchlistRow[]>([])
  const watchlistPagination = ref<Pagination>({ ...DEFAULT_PAGINATION })
  const watchlistLoading = ref(false)

  // Dashboard / Alerts
  const dashboard = ref<DashboardStats | null>(null)
  const lowStockAlerts = ref<LowStockAlert[]>([])
  const dashboardLoading = ref(false)

  const error = ref<string | null>(null)

  function _setErr(e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  }

  // ─── Allocations ──────────────────────────────────────────────────────────
  async function fetchAllocations(params: Record<string, unknown> = {}) {
    allocationsLoading.value = true
    error.value = null
    try {
      const res = await listAllocations(params)
      allocations.value = res.data ?? []
      if (res.pagination) allocationsPagination.value = res.pagination
    } catch (e: unknown) { _setErr(e) }
    finally { allocationsLoading.value = false }
  }

  async function fetchAllocationDetail(name: string) {
    try {
      allocationDetail.value = await getAllocation(name)
    } catch (e: unknown) { _setErr(e); allocationDetail.value = null }
  }

  async function submitNewAllocation(payload: {
    work_order_ref?: string; asset?: string; warehouse?: string;
    urgency?: UrgencyLevel; items: AllocationItem[]
  }) {
    const res = await createAllocation(payload)
    await fetchAllocations()
    return res
  }

  async function approveAllocationAction(name: string) {
    const res = await approveAllocation(name)
    await fetchAllocations()
    return res
  }

  async function issueAllocationAction(name: string) {
    const res = await issueAllocation(name)
    await fetchAllocations()
    return res
  }

  async function returnItemsAction(name: string, items: Array<{ spare_part: string; qty_returned: number; return_condition?: string }>) {
    const res = await returnItems(name, items)
    await fetchAllocations()
    return res
  }

  // ─── Cycle Counts ─────────────────────────────────────────────────────────
  async function fetchCycleCounts(params: Record<string, unknown> = {}) {
    cycleCountsLoading.value = true
    error.value = null
    try {
      const res = await listCycleCounts(params)
      cycleCounts.value = res.data ?? []
      if (res.pagination) cycleCountsPagination.value = res.pagination
    } catch (e: unknown) { _setErr(e) }
    finally { cycleCountsLoading.value = false }
  }

  async function createCycleCountAction(payload: {
    warehouse: string; spare_parts: string[]; count_type?: string; count_date?: string
  }) {
    const res = await createCycleCount(payload)
    await fetchCycleCounts()
    return res
  }

  async function submitCycleCountAction(
    name: string,
    counted: Array<{ spare_part: string; counted_qty: number; root_cause?: string }>,
  ) {
    const res = await submitCycleCount(name, counted)
    await fetchCycleCounts()
    return res
  }

  async function postCycleCountAction(name: string, verified_by = '', notes = '') {
    const res = await postCycleCount(name, verified_by, notes)
    await fetchCycleCounts()
    return res
  }

  // ─── Forecasts ────────────────────────────────────────────────────────────
  async function fetchForecasts(params: Record<string, unknown> = {}) {
    forecastsLoading.value = true
    error.value = null
    try {
      const res = await listSpareForecasts(params)
      forecasts.value = res.data ?? []
      if (res.pagination) forecastsPagination.value = res.pagination
    } catch (e: unknown) { _setErr(e) }
    finally { forecastsLoading.value = false }
  }

  async function generateForecastAction(horizon = 3, method: ForecastMethod = 'Moving_Avg', period = '') {
    const res = await generateSpareForecast(horizon, method, period)
    await fetchForecasts()
    return res
  }

  async function approveForecastAction(name: string) {
    const res = await approveForecast(name)
    await fetchForecasts()
    return res
  }

  // ─── Watchlist ────────────────────────────────────────────────────────────
  async function fetchWatchlist(params: Record<string, unknown> = {}) {
    watchlistLoading.value = true
    error.value = null
    try {
      const res = await listWatchlist(params)
      watchlist.value = res.data ?? []
      if (res.pagination) watchlistPagination.value = res.pagination
    } catch (e: unknown) { _setErr(e) }
    finally { watchlistLoading.value = false }
  }

  async function addWatchlistAction(payload: {
    watchlist_name: string; critical_asset: string; spare_part: string;
    min_required_on_hand: number; warehouse: string
  }) {
    const res = await addToWatchlist(payload)
    await fetchWatchlist()
    return res
  }

  // ─── Dashboard / Alerts ───────────────────────────────────────────────────
  async function fetchDashboard(period = '') {
    dashboardLoading.value = true
    error.value = null
    try {
      dashboard.value = await getDashboardStats(period)
    } catch (e: unknown) { _setErr(e) }
    finally { dashboardLoading.value = false }
  }

  async function fetchLowStockAlerts(warehouse = '') {
    try {
      const res = await getLowStockAlerts(warehouse)
      lowStockAlerts.value = res.alerts ?? []
    } catch (e: unknown) { _setErr(e) }
  }

  return {
    // state
    allocations, allocationsPagination, allocationsLoading, allocationDetail,
    cycleCounts, cycleCountsPagination, cycleCountsLoading,
    forecasts, forecastsPagination, forecastsLoading,
    watchlist, watchlistPagination, watchlistLoading,
    dashboard, lowStockAlerts, dashboardLoading,
    error,
    // actions
    fetchAllocations, fetchAllocationDetail, submitNewAllocation,
    approveAllocationAction, issueAllocationAction, returnItemsAction,
    fetchCycleCounts, createCycleCountAction, submitCycleCountAction, postCycleCountAction,
    fetchForecasts, generateForecastAction, approveForecastAction,
    fetchWatchlist, addWatchlistAction,
    fetchDashboard, fetchLowStockAlerts,
  }
})
