<script setup lang="ts">
// Dashboard — Trưởng xưởng kỹ thuật (workshop). Core Doc §5.3.
import { computed } from 'vue'
import { usePersonaDashboard } from '@/composables/useDashboard'
import { sectionRows } from '@/api/dashboard'
import PersonaDashboardShell from '@/components/dashboard/PersonaDashboardShell.vue'
import ListCard, { type ListColumn } from '@/components/dashboard/ListCard.vue'

const { data, isLoading, error, refetch } = usePersonaDashboard('workshop')
const kpis = computed(() => data.value?.kpis ?? [])
const sec = computed(() => data.value?.sections)
const woToAssign = computed(() => sectionRows(sec.value, 'wo_to_assign'))
const techCompetency = computed(() => sectionRows(sec.value, 'tech_competency'))

const woCols: ListColumn[] = [
  { key: 'name', label: 'Mã WO', type: 'link' },
  { key: 'asset_ref', label: 'Thiết bị', nameKey: 'asset_name' },
  { key: 'pm_type', label: 'Loại' },
  { key: 'status', label: 'Trạng thái', type: 'status' },
]
const compCols: ListColumn[] = [
  { key: 'user', label: 'KTV' },
  { key: 'device_model', label: 'Thiết bị', nameKey: 'device_model_name' },
  { key: 'competency_level', label: 'Mức' },
  { key: 'workflow_state', label: 'Trạng thái', type: 'status' },
]
</script>

<template>
  <PersonaDashboardShell
    title="Bảng điều khiển — Trưởng xưởng kỹ thuật"
    subtitle="Phân công công việc · PM/CM/Calibration · Năng lực KTV"
    :kpis="kpis"
    :loading="isLoading"
    :error="error ? String(error.message ?? error) : null"
    @retry="refetch"
  >
    <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <ListCard title="Lệnh công việc cần phân công" :columns="woCols" :rows="woToAssign" />
      <ListCard title="Năng lực kỹ thuật viên" :columns="compCols" :rows="techCompetency" />
    </div>
  </PersonaDashboardShell>
</template>
