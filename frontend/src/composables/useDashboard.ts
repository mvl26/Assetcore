import { useQuery } from '@tanstack/vue-query'
import { computed, unref, type MaybeRefOrGetter } from 'vue'
import { frappeGet } from '@/api/helpers'
import { getPersonaDashboard } from '@/api/dashboard'
import type { PersonaCode } from '@/constants/personas'

const BASE_DASHBOARD = '/api/method/assetcore.api.dashboard'
const BASE_IMM08 = '/api/method/assetcore.api.imm08'
const BASE_IMM09 = '/api/method/assetcore.api.imm09'

/**
 * Persona dashboard query (Core Doc §2). queryKey theo persona → đổi persona
 * tự refetch (reactive). Chỉ chạy khi có persona hợp lệ (enabled).
 */
export function usePersonaDashboard(persona: MaybeRefOrGetter<PersonaCode | string | null>) {
  const code = computed(() => {
    const v = typeof persona === 'function' ? persona() : unref(persona)
    return v ?? ''
  })
  return useQuery({
    queryKey: ['persona-dashboard', code],
    queryFn: () => getPersonaDashboard(code.value),
    enabled: computed(() => !!code.value),
    staleTime: 2 * 60 * 1000,
  })
}

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
