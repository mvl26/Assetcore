<script setup lang="ts">
// Dashboard — Trưởng xưởng kỹ thuật (workshop). Core Doc §5.3.
import { computed } from 'vue'
import { usePersonaDashboard } from '@/composables/useDashboard'
import { sectionRows } from '@/api/dashboard'
import PersonaDashboardShell from '@/components/dashboard/PersonaDashboardShell.vue'
import ListCard, { type ListColumn } from '@/components/dashboard/ListCard.vue'
import { useSectionDrill } from '@/composables/useSectionDrill'

const drill = useSectionDrill()
const { data, isLoading, error, refetch } = usePersonaDashboard('workshop')
const kpis = computed(() => data.value?.kpis ?? [])
const sec = computed(() => data.value?.sections)
const woToAssign = computed(() => sectionRows(sec.value, 'wo_to_assign'))
const techCompetency = computed(() => sectionRows(sec.value, 'tech_competency'))

const woCols: ListColumn[] = [
  { key: 'name', label: 'Mã lệnh công việc', type: 'link' },
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
    subtitle="Phân công công việc · bảo trì định kỳ/sửa chữa/Hiệu chuẩn · Năng lực KTV"
    :kpis="kpis"
    :loading="isLoading"
    :error="error ? String(error.message ?? error) : null"
    @retry="refetch"
  >
    <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <!-- Section wo_to_assign là PM WO (BE _recent 'PM Work Order') → drill PM detail. -->
      <ListCard title="Lệnh công việc cần phân công" :columns="woCols" :rows="woToAssign" :row-to="drill.pmWo" />
      <!-- Năng lực KTV: không có detail view 1-1 cho competency record → giữ tĩnh (non-drill có lý do §9.9). -->
      <ListCard title="Năng lực kỹ thuật viên" :columns="compCols" :rows="techCompetency" />
    </div>
  </PersonaDashboardShell>
</template>
