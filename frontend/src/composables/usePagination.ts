import { ref, computed } from 'vue'
import type { PaginationMeta } from '@/types/common'

export function usePagination(initialPageSize = 20) {
  const pagination = ref<PaginationMeta>({
    page: 1,
    page_size: initialPageSize,
    total: 0,
    total_pages: 0,
  })

  const hasNextPage = computed(() => pagination.value.page < pagination.value.total_pages)
  const hasPrevPage = computed(() => pagination.value.page > 1)

  function setPage(page: number) {
    pagination.value.page = page
  }

  function setPagination(meta: PaginationMeta) {
    pagination.value = meta
  }

  return { pagination, hasNextPage, hasPrevPage, setPage, setPagination }
}
