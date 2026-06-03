<script setup lang="ts">
// Dashboard — Cán bộ hồ sơ (doc). Core Doc §5.6.
import { computed } from 'vue'
import { usePersonaDashboard } from '@/composables/useDashboard'
import { sectionRows } from '@/api/dashboard'
import PersonaDashboardShell from '@/components/dashboard/PersonaDashboardShell.vue'
import ListCard, { type ListColumn } from '@/components/dashboard/ListCard.vue'
import { useSectionDrill } from '@/composables/useSectionDrill'

const drill = useSectionDrill()
const { data, isLoading, error, refetch } = usePersonaDashboard('doc')
const kpis = computed(() => data.value?.kpis ?? [])
const sec = computed(() => data.value?.sections)
const docsExpiring = computed(() => sectionRows(sec.value, 'docs_expiring'))
const commissioningQueue = computed(() => sectionRows(sec.value, 'commissioning_queue'))

const docCols: ListColumn[] = [
  { key: 'name', label: 'Mã', type: 'link' },
  { key: 'doc_category', label: 'Loại tài liệu' },
  { key: 'asset_ref', label: 'Thiết bị', nameKey: 'asset_name' },
  { key: 'expiry_date', label: 'Hết hạn', type: 'date' },
]
const commCols: ListColumn[] = [
  { key: 'name', label: 'Mã', type: 'link' },
  { key: 'asset', label: 'Thiết bị', nameKey: 'asset_name' },
  { key: 'workflow_state', label: 'Trạng thái', type: 'status' },
]
</script>

<template>
  <PersonaDashboardShell
    title="Bảng điều khiển — Cán bộ hồ sơ"
    subtitle="Tài liệu thiết bị · Lắp đặt & nghiệm thu · Đăng ký BYT"
    :kpis="kpis"
    :loading="isLoading"
    :error="error ? String(error.message ?? error) : null"
    @retry="refetch"
  >
    <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <ListCard title="Tài liệu sắp hết hạn (90 ngày)" :columns="docCols" :rows="docsExpiring" :row-to="drill.document" />
      <ListCard title="Nghiệm thu chờ xử lý" :columns="commCols" :rows="commissioningQueue" :row-to="drill.commissioning" />
    </div>
  </PersonaDashboardShell>
</template>
