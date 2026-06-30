<script setup lang="ts">
// Dashboard — Cán bộ QA / Kiểm toán (qa). Core Doc §5.8.
import { computed } from 'vue'
import { usePersonaDashboard } from '@/composables/useDashboard'
import { sectionRows } from '@/api/dashboard'
import PersonaDashboardShell from '@/components/dashboard/PersonaDashboardShell.vue'
import ListCard, { type ListColumn } from '@/components/dashboard/ListCard.vue'
import { useSectionDrill } from '@/composables/useSectionDrill'

const drill = useSectionDrill()
const { data, isLoading, error, refetch } = usePersonaDashboard('qa')
const kpis = computed(() => data.value?.kpis ?? [])
const sec = computed(() => data.value?.sections)
const capaTodo = computed(() => sectionRows(sec.value, 'capa_todo'))
const complianceFindings = computed(() => sectionRows(sec.value, 'compliance_findings'))
const internalAudits = computed(() => sectionRows(sec.value, 'internal_audits'))

const capaCols: ListColumn[] = [
  { key: 'name', label: 'Mã CAPA', type: 'link' },
  { key: 'source_ref', label: 'Nguồn' },
  { key: 'severity', label: 'Mức độ', type: 'severity' },
  { key: 'status', label: 'Trạng thái', type: 'status' },
]
const findingCols: ListColumn[] = [
  { key: 'name', label: 'Mã', type: 'link' },
  { key: 'asset', label: 'Thiết bị', nameKey: 'asset_name' },
  { key: 'severity', label: 'Mức độ', type: 'severity' },
  { key: 'status', label: 'Trạng thái', type: 'status' },
]
const auditCols: ListColumn[] = [
  { key: 'audit_code', label: 'Mã kiểm toán' },
  { key: 'audit_type', label: 'Loại' },
  { key: 'lead_auditor', label: 'Chủ trì', nameKey: 'lead_auditor_name' },
  { key: 'status', label: 'Trạng thái', type: 'status' },
]
</script>

<template>
  <PersonaDashboardShell
    title="Bảng điều khiển — Cán bộ QA / Kiểm toán"
    subtitle="Sự cố · RCA · CAPA · Kiểm toán · Tuân thủ"
    :kpis="kpis"
    :loading="isLoading"
    :error="error ? String(error.message ?? error) : null"
    @retry="refetch"
  >
    <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <ListCard title="CAPA cần xử lý" :columns="capaCols" :rows="capaTodo" :row-to="drill.capa" />
      <ListCard title="Vi phạm tuân thủ" :columns="findingCols" :rows="complianceFindings" :row-to="drill.incident" />
    </div>
    <ListCard title="Kiểm toán nội bộ" :columns="auditCols" :rows="internalAudits" :row-to="drill.audit" />
  </PersonaDashboardShell>
</template>
