<script setup lang="ts">
import { onMounted, ref, computed, watch } from 'vue'
import { useImm09Store } from '@/stores/imm09'
import { useRouter } from 'vue-router'

const store = useImm09Store()
const router = useRouter()
const statusFilter = ref('')
const search = ref('')

onMounted(() => store.fetchWorkOrders())
watch(statusFilter, (val) => store.fetchWorkOrders(val ? { status: val } : {}))

function statusBadgeClass(status: string) {
  const map: Record<string, string> = {
    'Open': 'bg-blue-100 text-blue-700',
    'Assigned': 'bg-indigo-100 text-indigo-700',
    'Diagnosing': 'bg-yellow-100 text-yellow-700',
    'Pending Parts': 'bg-orange-100 text-orange-700',
    'In Repair': 'bg-purple-100 text-purple-700',
    'Pending Inspection': 'bg-cyan-100 text-cyan-700',
    'Completed': 'bg-green-100 text-green-700',
    'Cannot Repair': 'bg-red-200 text-red-800',
    'Cancelled': 'bg-gray-100 text-gray-500',
  }
  return map[status] ?? 'bg-gray-100 text-gray-600'
}

function priorityClass(priority: string) {
  if (priority === 'Emergency') return 'text-red-600 font-bold'
  if (priority === 'Urgent') return 'text-orange-600 font-medium'
  return 'text-gray-600'
}

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
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-09</p>
        <h1 class="text-2xl font-bold text-slate-900">Danh sách CM Work Order</h1>
        <p class="text-sm text-slate-500 mt-1">
          Tổng <strong class="text-slate-700">{{ store.pagination.total ?? filteredWOs.length }}</strong> phiếu
        </p>
      </div>
      <button class="btn-primary shrink-0" @click="router.push('/cm/create')">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
        </svg>
        Tạo WO mới
      </button>
    </div>

    <!-- Filters -->
    <div class="card mb-6">
      <div class="flex gap-3">
        <input
          v-model="search"
          placeholder="Tìm theo mã WO, thiết bị..."
          class="form-input flex-1"
        />
        <select v-model="statusFilter" class="form-select w-52">
          <option value="">Tất cả trạng thái</option>
          <option value="Open">Open</option>
          <option value="Assigned">Assigned</option>
          <option value="Diagnosing">Diagnosing</option>
          <option value="Pending Parts">Pending Parts</option>
          <option value="In Repair">In Repair</option>
          <option value="Completed">Completed</option>
          <option value="Cannot Repair">Cannot Repair</option>
        </select>
      </div>
    </div>

    <!-- Loading skeleton -->
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
            <th class="table-header">Mã WO</th>
            <th class="table-header">Thiết bị</th>
            <th class="table-header">Loại / Ưu tiên</th>
            <th class="table-header">Mở lúc</th>
            <th class="table-header">KTV</th>
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
              <div class="font-mono text-xs text-blue-600">{{ wo.name }}</div>
              <div v-if="wo.sla_breached" class="text-xs text-red-600 font-medium">SLA vi phạm</div>
              <div v-if="wo.is_repeat_failure" class="text-xs text-orange-500">Tái hỏng</div>
            </td>
            <td class="table-cell">
              <div class="font-medium text-slate-900">{{ wo.asset_name || wo.asset_ref }}</div>
              <div class="text-xs text-slate-400">{{ wo.risk_class }}</div>
            </td>
            <td class="table-cell">
              <div class="text-slate-600 text-xs">{{ wo.repair_type }}</div>
              <div :class="['text-xs', priorityClass(wo.priority)]">{{ wo.priority }}</div>
            </td>
            <td class="table-cell text-xs text-slate-500">{{ wo.open_datetime?.slice(0, 16) }}</td>
            <td class="table-cell text-xs text-slate-500">{{ wo.assigned_to || '—' }}</td>
            <td class="table-cell text-xs">
              <span v-if="wo.mttr_hours" :class="wo.sla_breached ? 'text-red-600 font-medium' : 'text-slate-500'">
                {{ wo.mttr_hours }}h
              </span>
              <span v-else class="text-slate-400">—</span>
            </td>
            <td class="table-cell">
              <span :class="['px-2 py-1 rounded-full text-xs font-medium', statusBadgeClass(wo.status)]">
                {{ wo.status }}
              </span>
            </td>
          </tr>
          <tr v-if="filteredWOs.length === 0">
            <td colspan="7" class="text-center text-slate-400 py-12">Không có dữ liệu</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div v-if="store.pagination.total_pages > 1" class="flex justify-center mt-4 gap-2">
      <button
        v-for="p in store.pagination.total_pages"
        :key="p"
        :class="['px-3 py-1 rounded text-sm border transition-colors', p === store.pagination.page ? 'bg-blue-600 text-white border-blue-600' : 'border-slate-300 hover:bg-slate-50']"
        @click="store.fetchWorkOrders({}, p)"
      >{{ p }}</button>
    </div>
  </div>
</template>
