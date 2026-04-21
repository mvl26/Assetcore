<script setup lang="ts">
import { onMounted, ref, computed, watch } from 'vue'
import { useImm09Store } from '@/stores/imm09'
import { useRouter } from 'vue-router'
import { priorityLabel, priorityClass, repairTypeLabel } from '@/utils/labels'
import { formatAssetDisplay, translateStatus, getStatusColor, formatDateTime } from '@/utils/formatters'

const store = useImm09Store()
const router = useRouter()
const statusFilter = ref('')
const search = ref('')

const CM_STATUSES = [
  { value: 'Open',               label: 'Tiếp nhận' },
  { value: 'Assigned',           label: 'Đã phân công' },
  { value: 'Diagnosing',         label: 'Đang chẩn đoán' },
  { value: 'Pending Parts',      label: 'Chờ vật tư' },
  { value: 'In Repair',          label: 'Đang sửa chữa' },
  { value: 'Pending Inspection', label: 'Chờ nghiệm thu' },
  { value: 'Completed',          label: 'Hoàn thành' },
  { value: 'Cannot Repair',      label: 'Không thể sửa' },
  { value: 'Cancelled',          label: 'Đã hủy' },
]

onMounted(() => store.fetchWorkOrders())
watch(statusFilter, (val) => store.fetchWorkOrders(val ? { status: val } : {}))

const filteredWOs = computed(() => {
  if (!search.value) return store.workOrders
  const q = search.value.toLowerCase()
  return store.workOrders.filter(w =>
    w.name.toLowerCase().includes(q) || (w.asset_name || '').toLowerCase().includes(q)
  )
})
</script>

<template>
  <div class="page-container animate-fade-in">

    <!-- Header -->
    <div class="flex items-start justify-between mb-6">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-09 · Sửa chữa CM</p>
        <h1 class="text-2xl font-bold text-slate-900">Danh sách Lệnh Sửa chữa</h1>
        <p class="text-sm text-slate-500 mt-1">
          Tổng <strong class="text-slate-700">{{ store.pagination.total ?? filteredWOs.length }}</strong> lệnh
        </p>
      </div>
      <button class="btn-primary shrink-0" @click="router.push('/cm/create')">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
        </svg>
        Tạo lệnh mới
      </button>
    </div>

    <!-- Filters -->
    <div class="card mb-6">
      <div class="flex gap-3">
        <input
          v-model="search"
          placeholder="Tìm theo mã lệnh, tên thiết bị..."
          class="form-input flex-1"
        />
        <select v-model="statusFilter" class="form-select w-52">
          <option value="">Tất cả trạng thái</option>
          <option v-for="s in CM_STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
        </select>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="store.loading" class="card">
      <div v-for="i in 6" :key="i" class="flex gap-4 py-3 border-b border-slate-100 last:border-0 animate-pulse">
        <div class="h-4 bg-slate-100 rounded w-28" />
        <div class="h-4 bg-slate-100 rounded flex-1" />
        <div class="h-4 bg-slate-100 rounded w-20" />
        <div class="h-4 bg-slate-100 rounded w-24" />
      </div>
    </div>

    <!-- Table -->
    <div v-else class="table-wrapper">
      <table class="min-w-full divide-y divide-slate-100">
        <thead>
          <tr>
            <th class="table-header">Mã lệnh</th>
            <th class="table-header">Thiết bị</th>
            <th class="table-header">Loại / Ưu tiên</th>
            <th class="table-header">Ngày tiếp nhận</th>
            <th class="table-header">Kỹ thuật viên</th>
            <th class="table-header">MTTR</th>
            <th class="table-header">Trạng thái</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-50">
          <tr
            v-for="wo in filteredWOs"
            :key="wo.name"
            class="hover:bg-slate-50 cursor-pointer transition-colors"
            @click="router.push(`/cm/work-orders/${wo.name}`)"
          >
            <td class="table-cell">
              <div class="font-mono text-sm font-semibold text-blue-700">{{ wo.name }}</div>
              <div v-if="wo.sla_breached" class="text-xs text-red-600 font-medium mt-0.5">⚠ SLA vi phạm</div>
              <div v-if="wo.is_repeat_failure" class="text-xs text-orange-500 mt-0.5">↺ Tái hỏng</div>
            </td>
            <td class="table-cell">
              <!-- UX chuẩn: Tên chính — Mã phụ -->
              <div class="font-medium text-slate-900">
                {{ formatAssetDisplay(wo.asset_name, wo.asset_ref).main }}
              </div>
              <div v-if="formatAssetDisplay(wo.asset_name, wo.asset_ref).hasBoth"
                   class="text-xs text-slate-400 font-mono mt-0.5">
                {{ formatAssetDisplay(wo.asset_name, wo.asset_ref).sub }}
              </div>
            </td>
            <td class="table-cell">
              <div class="text-sm text-slate-700">{{ repairTypeLabel(wo.repair_type) }}</div>
              <span :class="['inline-block mt-1 px-2 py-0.5 rounded-full text-xs font-medium', priorityClass(wo.priority)]">
                {{ priorityLabel(wo.priority) }}
              </span>
            </td>
            <td class="table-cell text-sm text-slate-600">{{ formatDateTime(wo.open_datetime) }}</td>
            <td class="table-cell">
              <div class="text-slate-700 text-sm">{{ wo.assigned_to_name || wo.assigned_to || '—' }}</div>
              <div v-if="wo.assigned_to && wo.assigned_to_name" class="text-xs text-slate-400">{{ wo.assigned_to }}</div>
            </td>
            <td class="table-cell">
              <span v-if="wo.mttr_hours" :class="wo.sla_breached ? 'text-red-600 font-semibold' : 'text-slate-600'">
                {{ wo.mttr_hours }}h
              </span>
              <span v-else class="text-slate-400">—</span>
            </td>
            <td class="table-cell">
              <!-- Badge trạng thái dùng formatters chung -->
              <span :class="['inline-block px-2.5 py-1 rounded-full text-xs font-medium', getStatusColor(wo.status)]">
                {{ translateStatus(wo.status) }}
              </span>
            </td>
          </tr>
          <tr v-if="filteredWOs.length === 0">
            <td colspan="7" class="py-16 text-center text-slate-400">
              <p class="text-sm font-medium">Không tìm thấy lệnh sửa chữa nào</p>
              <p class="text-xs mt-1">Thử thay đổi bộ lọc hoặc từ khóa tìm kiếm</p>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div v-if="store.pagination.total_pages > 1" class="flex justify-center mt-5 gap-1">
      <button
        v-for="p in store.pagination.total_pages"
        :key="p"
        :class="['px-3 py-1.5 rounded-lg text-sm border transition-colors font-medium',
          p === store.pagination.page
            ? 'bg-blue-600 text-white border-blue-600'
            : 'border-slate-300 text-slate-600 hover:bg-slate-50']"
        @click="store.fetchWorkOrders({}, p)"
      >{{ p }}</button>
    </div>
  </div>
</template>
