import { useQuery } from '@tanstack/vue-query'
import { frappeGet } from '@/api/helpers'

const BASE_DASHBOARD = '/api/method/assetcore.api.dashboard'
const BASE_IMM08 = '/api/method/assetcore.api.imm08'
const BASE_IMM09 = '/api/method/assetcore.api.imm09'

export function useOverviewDashboard() {
  return useQuery({
    queryKey: ['dashboard', 'overview'],
    queryFn: () => frappeGet(`${BASE_DASHBOARD}.get_overview`),
    staleTime: 2 * 60 * 1000, // refresh every 2 min for dashboard
  })
}

export function usePMDashboard(year: number, month: number) {
  return useQuery({
    queryKey: ['pm', 'dashboard', year, month],
    queryFn: () => frappeGet(`${BASE_IMM08}.get_pm_dashboard_stats`, { year, month }),
    staleTime: 2 * 60 * 1000,
  })
}

export function useCMDashboard(year: number, month: number) {
  return useQuery({
    queryKey: ['cm', 'kpis', year, month],
    queryFn: () => frappeGet(`${BASE_IMM09}.get_repair_kpis`, { year, month }),
    staleTime: 2 * 60 * 1000,
  })
}
