<script setup lang="ts">
// Dashboard — Kỹ thuật viên (tech). Core Doc §5.4.
import { computed } from 'vue'
import { usePersonaDashboard } from '@/composables/useDashboard'
import { sectionRows } from '@/api/dashboard'
import PersonaDashboardShell from '@/components/dashboard/PersonaDashboardShell.vue'
import ListCard, { type ListColumn } from '@/components/dashboard/ListCard.vue'

const { data, isLoading, error, refetch } = usePersonaDashboard('tech')
const kpis = computed(() => data.value?.kpis ?? [])
const sec = computed(() => data.value?.sections)
const myWoToday = computed(() => sectionRows(sec.value, 'my_wo_today'))
const myCm = computed(() => sectionRows(sec.value, 'my_cm'))
const mySpareRequests = computed(() => sectionRows(sec.value, 'my_spare_requests'))

const pmCols: ListColumn[] = [
  { key: 'name', label: 'Mã WO', type: 'link' },
  { key: 'asset_ref', label: 'Thiết bị', nameKey: 'asset_name' },
  { key: 'due_date', label: 'Hạn', type: 'date' },
  { key: 'status', label: 'Trạng thái', type: 'status' },
]
const cmCols: ListColumn[] = [
  { key: 'name', label: 'Mã WO', type: 'link' },
  { key: 'asset_ref', label: 'Thiết bị', nameKey: 'asset_name' },
  { key: 'priority', label: 'Ưu tiên' },
  { key: 'status', label: 'Trạng thái', type: 'status' },
]
const reqCols: ListColumn[] = [
  { key: 'name', label: 'Mã phiếu', type: 'link' },
  { key: 'work_order_ref', label: 'WO' },
  { key: 'allocation_status', label: 'Trạng thái', type: 'status' },
]
</script>

<template>
  <PersonaDashboardShell
    title="Bảng điều khiển — Kỹ thuật viên"
    subtitle="Lệnh công việc của tôi"
    :kpis="kpis"
    :loading="isLoading"
    :error="error ? String(error.message ?? error) : null"
    @retry="refetch"
  >
    <ListCard title="PM của tôi hôm nay" :columns="pmCols" :rows="myWoToday" />
    <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <ListCard title="CM của tôi" :columns="cmCols" :rows="myCm" />
      <ListCard title="Phụ tùng đã yêu cầu" :columns="reqCols" :rows="mySpareRequests" />
    </div>
  </PersonaDashboardShell>
</template>
