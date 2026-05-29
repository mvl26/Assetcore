<script setup lang="ts">
// Dashboard — Quản trị viên IT (admin). Core Doc §5.1.
import { computed } from 'vue'
import { usePersonaDashboard } from '@/composables/useDashboard'
import { sectionRows } from '@/api/dashboard'
import PersonaDashboardShell from '@/components/dashboard/PersonaDashboardShell.vue'
import ListCard, { type ListColumn } from '@/components/dashboard/ListCard.vue'
import TimelineCard from '@/components/dashboard/TimelineCard.vue'

const { data, isLoading, error, refetch } = usePersonaDashboard('admin')
const kpis = computed(() => data.value?.kpis ?? [])
const sec = computed(() => data.value?.sections)
const usersPending = computed(() => sectionRows(sec.value, 'users_pending'))
const auditRecent = computed(() => sectionRows(sec.value, 'audit_recent'))

const userCols: ListColumn[] = [
  { key: 'name', label: 'Email', nameKey: 'full_name' },
  { key: 'full_name', label: 'Họ tên' },
  { key: 'creation', label: 'Ngày tạo', type: 'date' },
]
</script>

<template>
  <PersonaDashboardShell
    title="Bảng điều khiển — Quản trị viên IT"
    subtitle="Người dùng · Phân quyền · Master data · Audit chain"
    :kpis="kpis"
    :loading="isLoading"
    :error="error ? String(error.message ?? error) : null"
    @retry="refetch"
  >
    <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <ListCard title="Người dùng chờ phê duyệt" :columns="userCols" :rows="usersPending" />
      <TimelineCard title="Hoạt động gần đây" :rows="auditRecent" />
    </div>
  </PersonaDashboardShell>
</template>
