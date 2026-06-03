<script setup lang="ts">
// Dashboard — Quản trị viên IT (admin). Core Doc §5.1 + §9.4.9.
// R2/R3: section rows drill về source (user-profile / incident). R4: hub tiles.
import { computed } from 'vue'
import { usePersonaDashboard } from '@/composables/useDashboard'
import { sectionRows } from '@/api/dashboard'
import { canAccessDrill } from '@/router/routeAccess'
import { useCapabilities } from '@/composables/useCapabilities'
import PersonaDashboardShell from '@/components/dashboard/PersonaDashboardShell.vue'
import ListCard, { type ListColumn } from '@/components/dashboard/ListCard.vue'
import TimelineCard from '@/components/dashboard/TimelineCard.vue'
import AdminShortcutTiles from '@/components/dashboard/AdminShortcutTiles.vue'

const { data, isLoading, error, refetch } = usePersonaDashboard('admin')
const { can } = useCapabilities()
const kpis = computed(() => data.value?.kpis ?? [])
const sec = computed(() => data.value?.sections)
const usersPending = computed(() => sectionRows(sec.value, 'users_pending'))
const auditRecent = computed(() => sectionRows(sec.value, 'audit_recent'))

const userCols: ListColumn[] = [
  { key: 'name', label: 'Email', nameKey: 'full_name' },
  { key: 'full_name', label: 'Họ tên' },
  { key: 'creation', label: 'Ngày tạo', type: 'date' },
]

// §9.7 row-drill — gate canAccessDrill (admin pass; persona khác thiếu cap → tĩnh).
// User row → hồ sơ người dùng IMM. Audit/activity row → incident source (root_record).
function userRowTo(r: Record<string, unknown>) {
  const u = r.name ? String(r.name) : ''
  if (!u || !canAccessDrill('/user-profiles', can)) return null
  return { path: `/user-profiles/${encodeURIComponent(u)}` }
}
function activityRowTo(r: Record<string, unknown>) {
  // §10 root_record: feed "Hoạt động gần đây" = recent incidents → mở incident
  // DETAIL (record nguồn thật) thay vì list. name = mã sự cố (INC-xxx).
  const name = r.name ? String(r.name) : ''
  if (!name || !canAccessDrill('/incidents/list', can)) return null
  return { path: `/incidents/${encodeURIComponent(name)}` }
}
</script>

<template>
  <PersonaDashboardShell
    title="Bảng điều khiển — Quản trị viên IT"
    subtitle="Quản trị người dùng, phân quyền, dữ liệu gốc và chuỗi kiểm toán"
    :kpis="kpis"
    :loading="isLoading"
    :error="error ? String(error.message ?? error) : null"
    @retry="refetch"
  >
    <!-- R4 §9.8: lối tắt quản trị (nav tiles thật, thay subtitle trang trí cũ) -->
    <AdminShortcutTiles />

    <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <ListCard
        title="Người dùng chờ phê duyệt"
        :columns="userCols"
        :rows="usersPending"
        :row-to="userRowTo"
      />
      <TimelineCard title="Hoạt động gần đây" :rows="auditRecent" :row-to="activityRowTo" />
    </div>
  </PersonaDashboardShell>
</template>
