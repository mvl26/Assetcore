<script setup lang="ts">
// Dashboard — Thủ kho phụ tùng (store). Core Doc §5.7.
import { computed } from 'vue'
import { usePersonaDashboard } from '@/composables/useDashboard'
import { sectionRows } from '@/api/dashboard'
import PersonaDashboardShell from '@/components/dashboard/PersonaDashboardShell.vue'
import ListCard, { type ListColumn } from '@/components/dashboard/ListCard.vue'

const { data, isLoading, error, refetch } = usePersonaDashboard('store')
const kpis = computed(() => data.value?.kpis ?? [])
const sec = computed(() => data.value?.sections)
const belowMin = computed(() => sectionRows(sec.value, 'below_min'))
const pendingAllocations = computed(() => sectionRows(sec.value, 'pending_allocations'))

const lowCols: ListColumn[] = [
  { key: 'spare_part', label: 'Mã PT', type: 'link', nameKey: 'part_name' },
  { key: 'warehouse', label: 'Kho', nameKey: 'warehouse_name' },
  { key: 'qty_on_hand', label: 'Tồn' },
  { key: 'min_stock_level', label: 'Định mức' },
]
const allocCols: ListColumn[] = [
  { key: 'name', label: 'Mã phiếu', type: 'link' },
  { key: 'work_order_ref', label: 'WO' },
  { key: 'requested_by', label: 'Người YC', nameKey: 'requested_by_name' },
  { key: 'allocation_status', label: 'Trạng thái', type: 'status' },
]
</script>

<template>
  <PersonaDashboardShell
    title="Bảng điều khiển — Thủ kho phụ tùng"
    subtitle="Cấp phát phụ tùng · Tồn kho · Kiểm kê chu kỳ"
    :kpis="kpis"
    :loading="isLoading"
    :error="error ? String(error.message ?? error) : null"
    @retry="refetch"
  >
    <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <ListCard title="Phụ tùng dưới định mức" :columns="lowCols" :rows="belowMin" />
      <ListCard title="Phiếu cấp phát chờ xử lý" :columns="allocCols" :rows="pendingAllocations" />
    </div>
  </PersonaDashboardShell>
</template>
