<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCapaStore } from '@/stores/imm00'
import type { CapaStatus } from '@/types/imm00'

const router = useRouter()

const store = useCapaStore()

const statusFilter = ref<CapaStatus | ''>('')
const STATUSES: { value: CapaStatus | ''; label: string }[] = [
  { value: '', label: 'Tất cả' },
  { value: 'Open', label: 'Mở' },
  { value: 'In Progress', label: 'Đang xử lý' },
  { value: 'Pending Verification', label: 'Chờ xác minh' },
  { value: 'Closed', label: 'Đã đóng' },
  { value: 'Overdue', label: 'Quá hạn' },
]

const statusColor: Record<string, string> = {
  'Open': 'bg-blue-100 text-blue-700',
  'In Progress': 'bg-yellow-100 text-yellow-700',
  'Pending Verification': 'bg-purple-100 text-purple-700',
  'Closed': 'bg-green-100 text-green-700',
  'Overdue': 'bg-red-100 text-red-700',
}

const statusLabel: Record<string, string> = {
  'Open': 'Mới mở',
  'In Progress': 'Đang xử lý',
  'Pending Verification': 'Chờ xác nhận',
  'Closed': 'Đã đóng',
  'Overdue': 'Quá hạn',
}

const severityLabel: Record<string, string> = {
  'Critical': 'Nghiêm trọng',
  'Major': 'Quan trọng',
  'Minor': 'Nhỏ',
}

function formatDate(d?: string) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('vi-VN')
}

function isOverdue(date?: string) {
  if (!date) return false
  return new Date(date) < new Date()
}

function applyFilter() {
  store.fetchList({ status: statusFilter.value || undefined })
}

function goToPage(page: number) {
  store.fetchList({ status: statusFilter.value || undefined, page })
}

onMounted(() => store.fetchList())
</script>

<template>
  <div class="page-container animate-fade-in">
    <div class="flex items-start justify-between mb-6">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-00</p>
        <h1 class="text-2xl font-bold text-slate-900">CAPA Records</h1>
        <p class="text-sm text-slate-500 mt-1">Tổng <strong>{{ store.pagination.total }}</strong> CAPA</p>
      </div>
    </div>

    <!-- Filter -->
    <div class="card p-4 mb-4 flex gap-3 items-center">
      <label for="capa-status-filter" class="text-sm text-slate-600">Trạng thái:</label>
      <select id="capa-status-filter" v-model="statusFilter" class="form-select text-sm" @change="applyFilter">
        <option v-for="s in STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
      </select>
    </div>

    <div v-if="store.error" class="alert-error mb-4">{{ store.error }}</div>

    <div class="card overflow-hidden">
      <div v-if="store.loading" class="p-6 text-center text-slate-400 text-sm">Đang tải...</div>
      <div v-else-if="store.capas.length" class="overflow-x-auto"><table class="w-full text-sm">
        <thead class="bg-slate-50 border-b border-slate-200">
          <tr>
            <th class="text-left px-4 py-3 font-semibold text-slate-600">Mã CAPA</th>
            <th class="text-left px-4 py-3 font-semibold text-slate-600">Thiết bị</th>
            <th class="text-left px-4 py-3 font-semibold text-slate-600">Mức độ</th>
            <th class="text-left px-4 py-3 font-semibold text-slate-600">Trạng thái</th>
            <th class="text-left px-4 py-3 font-semibold text-slate-600">Hạn xử lý</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr v-for="capa in store.capas" :key="capa.name" class="hover:bg-slate-50 cursor-pointer" @click="router.push(`/capas/${capa.name}`)">
            <td class="px-4 py-3">
              <p class="font-mono text-xs text-slate-700">{{ capa.name }}</p>
              <p v-if="capa.title" class="text-xs text-slate-400 mt-0.5">{{ capa.title }}</p>
            </td>
            <td class="px-4 py-3">
              <div class="text-slate-700 text-sm">{{ capa.asset_name || capa.asset || '—' }}</div>
              <div v-if="capa.asset && capa.asset_name" class="text-xs text-slate-400 font-mono">{{ capa.asset }}</div>
            </td>
            <td class="px-4 py-3">
              <span class="text-xs font-medium" :class="{ 'text-red-600': capa.severity === 'Critical', 'text-yellow-600': capa.severity === 'Major', 'text-slate-600': capa.severity === 'Minor' }">
                {{ severityLabel[capa.severity] || capa.severity }}
              </span>
            </td>
            <td class="px-4 py-3">
              <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium" :class="statusColor[capa.status] || 'bg-gray-100 text-gray-600'">
                {{ statusLabel[capa.status] || capa.status }}
              </span>
            </td>
            <td class="px-4 py-3">
              <span :class="isOverdue(capa.due_date) && capa.status !== 'Closed' ? 'text-red-600 font-semibold' : 'text-slate-600'" class="text-xs">
                {{ formatDate(capa.due_date) }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
      </div>
      <div v-else class="flex flex-col items-center justify-center py-16 text-slate-400">
        <p class="text-sm">Không có CAPA nào</p>
      </div>
    </div>

    <div v-if="store.pagination.total_pages > 1" class="flex justify-between items-center mt-4 text-sm text-slate-600">
      <span>Trang {{ store.pagination.page }} / {{ store.pagination.total_pages }}</span>
      <div class="flex gap-2">
        <button class="btn-ghost text-xs" :disabled="store.pagination.page <= 1" @click="goToPage(store.pagination.page - 1)">← Trước</button>
        <button class="btn-ghost text-xs" :disabled="store.pagination.page >= store.pagination.total_pages" @click="goToPage(store.pagination.page + 1)">Sau →</button>
      </div>
    </div>
  </div>
</template>
