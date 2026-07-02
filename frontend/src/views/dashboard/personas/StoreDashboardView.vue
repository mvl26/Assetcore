<script setup lang="ts">
// Dashboard — Thủ kho phụ tùng (store). Core Doc §5.7.
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { usePersonaDashboard } from '@/composables/useDashboard'
import { sectionRows } from '@/api/dashboard'
import PersonaDashboardShell from '@/components/dashboard/PersonaDashboardShell.vue'
import ListCard, { type ListColumn } from '@/components/dashboard/ListCard.vue'
import { useSectionDrill } from '@/composables/useSectionDrill'

const drill = useSectionDrill()
const { data, isLoading, error, refetch } = usePersonaDashboard('store')
const kpis = computed(() => data.value?.kpis ?? [])
const sec = computed(() => data.value?.sections)
const belowMin = computed(() => sectionRows(sec.value, 'below_min'))
const pendingAllocations = computed(() => sectionRows(sec.value, 'pending_allocations'))

const lowCols: ListColumn[] = [
  { key: 'spare_part', label: 'Mã phụ tùng', type: 'link', nameKey: 'part_name' },
  { key: 'warehouse', label: 'Kho', nameKey: 'warehouse_name' },
  { key: 'qty_on_hand', label: 'Tồn' },
  { key: 'min_stock_level', label: 'Định mức' },
]
const allocCols: ListColumn[] = [
  { key: 'name', label: 'Mã phiếu', type: 'link' },
  { key: 'work_order_ref', label: 'Lệnh công việc' },
  { key: 'requested_by', label: 'Người yêu cầu', nameKey: 'requested_by_name' },
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
    <!-- Lối tắt tác vụ kho — trỏ tới các trang chức năng (không còn dead-link). -->
    <div class="mb-6 flex flex-wrap gap-3">
      <RouterLink
        to="/inventory/cycle-counts"
        class="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 hover:border-emerald-300 hover:text-emerald-700 focus-visible:ring-2 focus-visible:ring-emerald-500"
      >
        <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
        </svg>
        Kiểm kê chu kỳ
      </RouterLink>
      <RouterLink
        to="/stock-movements"
        class="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 hover:border-emerald-300 hover:text-emerald-700 focus-visible:ring-2 focus-visible:ring-emerald-500"
      >
        <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
        </svg>
        Phiếu xuất / nhập kho
      </RouterLink>
    </div>

    <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <ListCard title="Phụ tùng dưới định mức" :columns="lowCols" :rows="belowMin" :row-to="drill.sparePart" />
      <!-- Phiếu cấp phát: drill về CM WO nguồn (work_order_ref) — phiếu không có detail view riêng. -->
      <ListCard
        title="Phiếu cấp phát chờ xử lý"
        :columns="allocCols"
        :rows="pendingAllocations"
        :row-to="(r) => drill.cmWo({ name: r.work_order_ref })"
      />
    </div>
  </PersonaDashboardShell>
</template>
