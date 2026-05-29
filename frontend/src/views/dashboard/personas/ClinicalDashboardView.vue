<script setup lang="ts">
// Dashboard — Trưởng khoa lâm sàng (clinical). Core Doc §5.5.
import { computed } from 'vue'
import { usePersonaDashboard } from '@/composables/useDashboard'
import { sectionRows } from '@/api/dashboard'
import PersonaDashboardShell from '@/components/dashboard/PersonaDashboardShell.vue'
import ListCard, { type ListColumn } from '@/components/dashboard/ListCard.vue'

const { data, isLoading, error, refetch } = usePersonaDashboard('clinical')
const kpis = computed(() => data.value?.kpis ?? [])
const sec = computed(() => data.value?.sections)
const department = computed(() => {
  const d = sec.value?.department
  return typeof d === 'string' ? d : ''
})
const deptIncidents = computed(() => sectionRows(sec.value, 'dept_incidents'))
const deptNeeds = computed(() => sectionRows(sec.value, 'dept_needs'))

const incCols: ListColumn[] = [
  { key: 'name', label: 'Mã', type: 'link' },
  { key: 'asset', label: 'Thiết bị', nameKey: 'asset_name' },
  { key: 'severity', label: 'Mức độ', type: 'severity' },
  { key: 'status', label: 'Trạng thái', type: 'status' },
]
const nrCols: ListColumn[] = [
  { key: 'name', label: 'Mã NR', type: 'link' },
  { key: 'device_model_ref', label: 'Thiết bị đề xuất' },
  { key: 'priority_class', label: 'Ưu tiên' },
  { key: 'workflow_state', label: 'Trạng thái', type: 'status' },
]
</script>

<template>
  <PersonaDashboardShell
    title="Bảng điều khiển — Trưởng khoa lâm sàng"
    :subtitle="department ? `Khoa: ${department}` : 'Sự cố · Đề xuất nhu cầu · Nghiệm thu thiết bị'"
    :kpis="kpis"
    :loading="isLoading"
    :error="error ? String(error.message ?? error) : null"
    @retry="refetch"
  >
    <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <ListCard title="Sự cố thiết bị khoa" :columns="incCols" :rows="deptIncidents" />
      <ListCard title="Đề xuất nhu cầu của khoa" :columns="nrCols" :rows="deptNeeds" />
    </div>
  </PersonaDashboardShell>
</template>
