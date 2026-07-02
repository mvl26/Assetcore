<script setup lang="ts">
// Dashboard — Kỹ thuật viên (tech). Core Doc §5.4.
import { computed } from 'vue'
import { usePersonaDashboard } from '@/composables/useDashboard'
import { sectionRows } from '@/api/dashboard'
import PersonaDashboardShell from '@/components/dashboard/PersonaDashboardShell.vue'
import ListCard, { type ListColumn } from '@/components/dashboard/ListCard.vue'
import { useSectionDrill } from '@/composables/useSectionDrill'

const drill = useSectionDrill()
const { data, isLoading, error, refetch } = usePersonaDashboard('tech')
const kpis = computed(() => data.value?.kpis ?? [])
const sec = computed(() => data.value?.sections)
const myWoToday = computed(() => sectionRows(sec.value, 'my_wo_today'))
const myCm = computed(() => sectionRows(sec.value, 'my_cm'))
const mySpareRequests = computed(() => sectionRows(sec.value, 'my_spare_requests'))

const pmCols: ListColumn[] = [
  { key: 'name', label: 'Mã lệnh công việc', type: 'link' },
  { key: 'asset_ref', label: 'Thiết bị', nameKey: 'asset_name' },
  { key: 'due_date', label: 'Hạn', type: 'date' },
  { key: 'status', label: 'Trạng thái', type: 'status' },
]
const cmCols: ListColumn[] = [
  { key: 'name', label: 'Mã lệnh công việc', type: 'link' },
  { key: 'asset_ref', label: 'Thiết bị', nameKey: 'asset_name' },
  { key: 'priority', label: 'Ưu tiên' },
  { key: 'status', label: 'Trạng thái', type: 'status' },
]
const reqCols: ListColumn[] = [
  { key: 'name', label: 'Mã phiếu', type: 'link' },
  { key: 'work_order_ref', label: 'Lệnh công việc' },
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
    <ListCard title="Bảo trì định kỳ của tôi hôm nay" :columns="pmCols" :rows="myWoToday" :row-to="drill.pmWo" />
    <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <ListCard title="Sửa chữa của tôi" :columns="cmCols" :rows="myCm" :row-to="drill.cmWo" />
      <!-- Phiếu cấp phát PT: drill về CM WO nguồn (work_order_ref) thay vì phiếu (không có detail view riêng). -->
      <ListCard
        title="Phụ tùng đã yêu cầu"
        :columns="reqCols"
        :rows="mySpareRequests"
        :row-to="(r) => drill.cmWo({ name: r.work_order_ref })"
      />
    </div>
  </PersonaDashboardShell>
</template>
