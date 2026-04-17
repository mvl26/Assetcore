<script setup lang="ts">
import { onMounted, ref, computed, watch } from 'vue'
import { useImm08Store } from '@/stores/imm08'
import { useRouter } from 'vue-router'

const store = useImm08Store()
const router = useRouter()
const statusFilter = ref('')
const search = ref('')
const dateFrom = ref('')
const dateTo = ref('')

onMounted(() => store.fetchWorkOrders())

watch([statusFilter, dateFrom, dateTo], () => {
  const f: Record<string, any> = {}
  if (statusFilter.value) f.status = statusFilter.value
  if (dateFrom.value) f.due_date = ['>=', dateFrom.value]
  if (dateTo.value) f.due_date = ['<=', dateTo.value]
  store.fetchWorkOrders(f)
})

function statusBadgeClass(status: string) {
  const map: Record<string, string> = {
    'Open': 'bg-blue-100 text-blue-700',
    'In Progress': 'bg-indigo-100 text-indigo-700',
    'Overdue': 'bg-red-100 text-red-700',
    'Completed': 'bg-green-100 text-green-700',
    'Halted–Major Failure': 'bg-red-200 text-red-900 font-semibold',
    'Pending–Device Busy': 'bg-orange-100 text-orange-700',
    'Cancelled': 'bg-gray-100 text-gray-400',
  }
  return map[status] ?? 'bg-gray-100 text-gray-600'
}

const filteredWOs = computed(() => {
  if (!search.value) return store.workOrders
  const q = search.value.toLowerCase()
  return store.workOrders.filter(w =>
    w.name.toLowerCase().includes(q) ||
    (w.asset_name || '').toLowerCase().includes(q) ||
    (w.asset_ref || '').toLowerCase().includes(q)
  )
})
</script>

<template>
  <div class="page-container animate-fade-in">

    <!-- Header -->
    <div class="flex items-start justify-between mb-6">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-08</p>
        <h1 class="text-2xl font-bold text-slate-900">Phiếu Bảo trì PM</h1>
        <p class="text-sm text-slate-500 mt-1">
          Tổng <strong class="text-slate-700">{{ store.pagination.total ?? filteredWOs.length }}</strong> phiếu
        </p>
      </div>
      <button class="btn-primary shrink-0" @click="router.push('/pm/work-orders/new')">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
        </svg>
        Tạo PM thủ công
      </button>
    </div>

    <!-- Filters -->
    <div class="card mb-6">
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="form-group">
          <label for="filter-search" class="form-label">Tìm kiếm</label>
          <input id="filter-search" v-model="search" placeholder="Mã WO, thiết bị..." class="form-input" />
        </div>
        <div class="form-group">
          <label for="filter-status" class="form-label">Trạng thái</label>
          <select id="filter-status" v-model="statusFilter" class="form-select">
            <option value="">Tất cả</option>
            <option value="Open">Open</option>
            <option value="In Progress">In Progress</option>
            <option value="Overdue">Overdue</option>
            <option value="Completed">Completed</option>
            <option value="Halted–Major Failure">Halted</option>
          </select>
        </div>
        <div class="form-group">
          <label for="filter-date-from" class="form-label">Từ ngày</label>
          <input id="filter-date-from" v-model="dateFrom" type="date" class="form-input" />
        </div>
        <div class="form-group">
          <label for="filter-date-to" class="form-label">Đến ngày</label>
          <input id="filter-date-to" v-model="dateTo" type="date" class="form-input" />
        </div>
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
            <th class="table-header">Loại PM</th>
            <th class="table-header">Đến hạn</th>
            <th class="table-header">KTV</th>
            <th class="table-header">Trạng thái</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-50">
          <tr
            v-for="wo in filteredWOs"
            :key="wo.name"
            class="hover:bg-slate-50 cursor-pointer transition-all hover:translate-x-0.5"
            @click="router.push(`/pm/work-orders/${wo.name}`)"
          >
            <td class="table-cell font-mono text-xs text-blue-600">{{ wo.name }}</td>
            <td class="table-cell">
              <div class="font-medium text-slate-900">{{ wo.asset_name || wo.asset_ref }}</div>
              <div class="text-xs text-slate-400">{{ wo.asset_ref }}</div>
            </td>
            <td class="table-cell text-slate-500 text-xs">{{ wo.pm_type }}</td>
            <td class="table-cell">
              <span :class="wo.is_late ? 'text-red-600 font-semibold' : 'text-slate-600'">
                {{ wo.due_date }}
              </span>
            </td>
            <td class="table-cell text-xs text-slate-500">{{ wo.assigned_to || '—' }}</td>
            <td class="table-cell">
              <span :class="['px-2 py-1 rounded-full text-xs font-medium', statusBadgeClass(wo.status)]">
                {{ wo.status }}
              </span>
            </td>
          </tr>

          <!-- Empty state -->
          <tr v-if="filteredWOs.length === 0">
            <td colspan="6" class="py-16 text-center">
              <div class="flex flex-col items-center gap-3 text-slate-400">
                <svg class="w-12 h-12 text-slate-200" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
                </svg>
                <p class="text-sm font-medium text-slate-500">Không tìm thấy phiếu bảo trì</p>
                <p class="text-xs text-slate-400">Thử thay đổi bộ lọc hoặc từ khóa tìm kiếm</p>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div v-if="store.pagination.total_pages > 1" class="flex items-center justify-between mt-4">
      <span class="text-sm text-slate-500">Trang {{ store.pagination.page }}/{{ store.pagination.total_pages }}</span>
      <div class="flex gap-1">
        <button
          v-for="p in store.pagination.total_pages"
          :key="p"
          :class="['px-3 py-1 rounded text-sm border transition-colors', p === store.pagination.page ? 'bg-blue-600 text-white border-blue-600' : 'border-slate-300 hover:bg-slate-50']"
          @click="store.fetchWorkOrders({}, p)"
        >{{ p }}</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Fade transition for table rows on filter change */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
