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
// BE D-BE-9: dept_configured=false → user chưa gắn khoa → fail-closed, không
// hiển thị data toàn viện. undefined (payload cũ) coi như đã cấu hình (back-compat).
const deptConfigured = computed(() => sec.value?.dept_configured !== false)
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
    <div
      v-if="!deptConfigured"
      class="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800"
    >
      <p class="font-semibold">Tài khoản của bạn chưa được gắn khoa/phòng.</p>
      <p class="mt-1 text-amber-700">
        Bảng điều khiển lâm sàng hiển thị sự cố và đề xuất theo khoa. Vì tài khoản chưa
        liên kết khoa/phòng, hệ thống không thể giới hạn dữ liệu theo khoa nên tạm ẩn các
        danh sách này. Vui lòng liên hệ quản trị viên để cập nhật khoa/phòng cho tài khoản.
      </p>
    </div>
    <div v-else class="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <ListCard title="Sự cố thiết bị khoa" :columns="incCols" :rows="deptIncidents" />
      <ListCard title="Đề xuất nhu cầu của khoa" :columns="nrCols" :rows="deptNeeds" />
    </div>
  </PersonaDashboardShell>
</template>
