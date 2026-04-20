<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — IMM-12 Incident List
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useIncidentStore } from '@/stores/imm00'
import type { IncidentSeverity } from '@/types/imm00'

const router = useRouter()
const store = useIncidentStore()

const severityFilter = ref<IncidentSeverity | ''>('')
const statusFilter = ref('')

const SEVERITIES = [
  { value: '', label: 'Tất cả mức độ' },
  { value: 'Low', label: 'Thấp' },
  { value: 'Medium', label: 'Trung bình' },
  { value: 'High', label: 'Cao' },
  { value: 'Critical', label: 'Nghiêm trọng' },
]

const STATUSES = [
  { value: '', label: 'Tất cả trạng thái' },
  { value: 'Open', label: 'Mới mở' },
  { value: 'Under Investigation', label: 'Đang điều tra' },
  { value: 'Resolved', label: 'Đã giải quyết' },
  { value: 'Closed', label: 'Đã đóng' },
]

const SEV_COLOR: Record<string, string> = {
  Low: 'bg-green-100 text-green-700',
  Medium: 'bg-yellow-100 text-yellow-700',
  High: 'bg-orange-100 text-orange-700',
  Critical: 'bg-red-100 text-red-700',
}

const STATUS_COLOR: Record<string, string> = {
  Open: 'bg-blue-100 text-blue-700',
  'Under Investigation': 'bg-yellow-100 text-yellow-800',
  Resolved: 'bg-purple-100 text-purple-700',
  Closed: 'bg-green-100 text-green-700',
}

const STATUS_LABEL: Record<string, string> = {
  Open: 'Mới mở',
  'Under Investigation': 'Đang điều tra',
  Resolved: 'Đã giải quyết',
  Closed: 'Đã đóng',
}

function formatDateTime(d?: string) {
  if (!d) return '—'
  return new Date(d).toLocaleString('vi-VN')
}

function applyFilter() {
  store.fetchList({
    severity: severityFilter.value || undefined,
    status: statusFilter.value || undefined,
  })
}

function goToPage(page: number) {
  store.fetchList({
    severity: severityFilter.value || undefined,
    status: statusFilter.value || undefined,
    page,
  })
}

onMounted(() => store.fetchList())
</script>

<template>
  <div class="page-container animate-fade-in">
    <div class="flex items-start justify-between mb-6">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-12</p>
        <h1 class="text-2xl font-bold text-slate-900">Sự cố thiết bị</h1>
        <p class="text-sm text-slate-500 mt-1">Tổng <strong>{{ store.pagination.total }}</strong> sự cố</p>
      </div>
      <button class="btn-primary shrink-0" @click="router.push('/incidents/new')">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
        </svg>
        Báo cáo sự cố
      </button>
    </div>

    <!-- Filters -->
    <div class="card p-4 mb-4 flex flex-wrap gap-3 items-center">
      <div class="flex items-center gap-2">
        <label for="sev-filter" class="text-sm text-slate-600 shrink-0">Mức độ:</label>
        <select id="sev-filter" v-model="severityFilter" class="form-select text-sm" @change="applyFilter">
          <option v-for="s in SEVERITIES" :key="s.value" :value="s.value">{{ s.label }}</option>
        </select>
      </div>
      <div class="flex items-center gap-2">
        <label for="status-filter" class="text-sm text-slate-600 shrink-0">Trạng thái:</label>
        <select id="status-filter" v-model="statusFilter" class="form-select text-sm" @change="applyFilter">
          <option v-for="s in STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
        </select>
      </div>
    </div>

    <div v-if="store.error" class="alert-error mb-4">{{ store.error }}</div>

    <div class="card overflow-hidden">
      <div v-if="store.loading" class="p-6 text-center text-slate-400 text-sm">Đang tải...</div>
      <div v-else-if="store.incidents.length" class="overflow-x-auto"><table class="w-full text-sm">
        <thead class="bg-slate-50 border-b border-slate-200">
          <tr>
            <th class="text-left px-4 py-3 font-semibold text-slate-600">Sự cố</th>
            <th class="text-left px-4 py-3 font-semibold text-slate-600">Thiết bị</th>
            <th class="text-left px-4 py-3 font-semibold text-slate-600">Mức độ</th>
            <th class="text-left px-4 py-3 font-semibold text-slate-600">Trạng thái</th>
            <th class="text-left px-4 py-3 font-semibold text-slate-600">Thời gian</th>
            <th class="text-left px-4 py-3 font-semibold text-slate-600">BN</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr
            v-for="ir in store.incidents"
            :key="ir.name"
            class="hover:bg-slate-50 cursor-pointer"
            @click="router.push(`/incidents/${ir.name}`)"
          >
            <td class="px-4 py-3">
              <p class="font-medium text-slate-800 truncate max-w-xs">
                {{ ir.description?.replace(/<[^>]+>/g, '').slice(0, 70) || '—' }}
              </p>
              <p class="font-mono text-xs text-slate-400">{{ ir.name }}</p>
            </td>
            <td class="px-4 py-3">
              <div class="text-slate-700">{{ ir.asset_name || ir.asset || '—' }}</div>
              <div v-if="ir.asset && ir.asset_name" class="text-xs text-slate-400 font-mono">{{ ir.asset }}</div>
            </td>
            <td class="px-4 py-3">
              <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                    :class="SEV_COLOR[ir.severity] || 'bg-gray-100 text-gray-600'">
                {{ ir.severity }}
              </span>
            </td>
            <td class="px-4 py-3">
              <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                    :class="(ir.status && STATUS_COLOR[ir.status]) || 'bg-gray-100 text-gray-600'">
                {{ (ir.status && STATUS_LABEL[ir.status]) || ir.status || '—' }}
              </span>
            </td>
            <td class="px-4 py-3 text-slate-500 text-xs whitespace-nowrap">
              {{ formatDateTime(ir.reported_at) }}
            </td>
            <td class="px-4 py-3">
              <span v-if="ir.patient_affected" class="text-xs font-semibold text-red-600">Có</span>
              <span v-else class="text-xs text-slate-400">—</span>
            </td>
          </tr>
        </tbody>
      </table>
      </div>
      <div v-else class="flex flex-col items-center justify-center py-16 text-slate-400">
        <p class="text-sm">Không có sự cố nào được báo cáo</p>
        <button class="btn-ghost text-xs mt-3" @click="router.push('/incidents/new')">+ Báo cáo sự cố đầu tiên</button>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="store.pagination.total_pages > 1" class="flex justify-between items-center mt-4 text-sm text-slate-600">
      <span>Trang {{ store.pagination.page }} / {{ store.pagination.total_pages }}</span>
      <div class="flex gap-2">
        <button class="btn-ghost text-xs" :disabled="store.pagination.page <= 1"
                @click="goToPage(store.pagination.page - 1)">← Trước</button>
        <button class="btn-ghost text-xs" :disabled="store.pagination.page >= store.pagination.total_pages"
                @click="goToPage(store.pagination.page + 1)">Sau →</button>
      </div>
    </div>
  </div>
</template>
