import { computed } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { frappeGet } from '@/api/helpers'
import type { AcAssetListItem, PaginatedResponse } from '@/types/imm00'

const BASE = '/api/method/assetcore.api.imm00'

export function useAssets(filters: Record<string, unknown> = {}, pageSize = 20) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['assets', filters, pageSize],
    queryFn: () =>
      frappeGet<PaginatedResponse<AcAssetListItem>>(`${BASE}.list_assets`, {
        filters: JSON.stringify(filters),
        page_size: pageSize,
      }),
  })

  return {
    assets: computed(() => data.value?.items ?? []),
    total: computed(() => data.value?.pagination?.total ?? 0),
    isLoading,
    error,
    refetch,
  }
}
