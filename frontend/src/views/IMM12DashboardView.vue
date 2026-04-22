<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — IMM-12 Incident Dashboard
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useImm12Store } from '@/stores/useImm12Store'

const router = useRouter()
const store = useImm12Store()

// Safe accessors với fallback rỗng
const activeIncidents = computed(() => store.dashboard?.active_incidents ?? [])
const openRcas = computed(() => store.dashboard?.open_rcas ?? [])
const chronicFailures = computed(() => store.dashboard?.chronic_failures ?? [])
const stats = computed(() => store.dashboard?.stats)

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
  Cancelled: 'bg-gray-100 text-gray-500',
}

const RCA_STATUS_COLOR: Record<string, string> = {
  'RCA Required': 'bg-red-100 text-red-700',
  'RCA In Progress': 'bg-yellow-100 text-yellow-800',
  Completed: 'bg-green-100 text-green-700',
  Cancelled: 'bg-gray-100 text-gray-500',
}

function formatDateTime(d?: string) {
  if (!d) return '—'
  return new Date(d).toLocaleString('vi-VN')
}

function formatDate(d?: string) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('vi-VN')
}

function isOverdue(due?: string) {
  if (!due) return false
  return new Date(due) < new Date()
}

onMounted(() => store.fetchDashboard())
</script>

<template>
  <div class="page-container animate-fade-in">
    <!-- Header -->
    <div class="flex items-start justify-between mb-6">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-12</p>
        <h1 class="text-2xl font-bold text-slate-900">Tổng quan Sự cố & RCA</h1>
        <p class="text-sm text-slate-500 mt-1">Giám sát sự cố thiết bị, RCA và hỏng hóc mãn tính</p>
      </div>
      <div class="flex gap-2 shrink-0">
        <button class="btn-ghost text-sm" @click="router.push('/incidents/list')">Danh sách</button>
        <button class="btn-primary text-sm" @click="router.push('/incidents/new')">+ Báo cáo sự cố</button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="store.dashboardLoading" class="p-12 text-center text-slate-400">Đang tải...</div>

    <!-- Error -->
    <div v-else-if="store.dashboardError" class="alert-error mb-4">{{ store.dashboardError }}</div>

    <!-- Content — chỉ render khi có stats -->
    <template v-else-if="stats">
      <!-- KPI cards -->
      <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4 mb-6">
        <div class="card p-4 text-center cursor-pointer hover:shadow-md transition-shadow"
             @click="router.push('/incidents/list')">
          <p class="text-3xl font-bold text-blue-600">{{ stats.open ?? 0 }}</p>
          <p class="text-xs text-slate-500 mt-1">Mới mở</p>
        </div>
        <div class="card p-4 text-center cursor-pointer hover:shadow-md transition-shadow"
             @click="router.push('/incidents/list')">
          <p class="text-3xl font-bold text-yellow-600">{{ stats.investigating ?? 0 }}</p>
          <p class="text-xs text-slate-500 mt-1">Đang điều tra</p>
        </div>
        <div class="card p-4 text-center border-l-4 border-red-400">
          <p class="text-3xl font-bold text-red-600">{{ stats.critical ?? 0 }}</p>
          <p class="text-xs text-slate-500 mt-1">Critical</p>
        </div>
        <div class="card p-4 text-center border-l-4 border-orange-400">
          <p class="text-3xl font-bold text-orange-600">{{ stats.rca_pending ?? 0 }}</p>
          <p class="text-xs text-slate-500 mt-1">Chờ RCA</p>
        </div>
        <div class="card p-4 text-center border-l-4 border-purple-400">
          <p class="text-3xl font-bold text-purple-600">{{ stats.chronic ?? 0 }}</p>
          <p class="text-xs text-slate-500 mt-1">Mãn tính</p>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Active incidents -->
        <div class="card overflow-hidden">
          <div class="px-4 py-3 border-b border-slate-100 flex justify-between items-center">
            <h2 class="font-semibold text-slate-800 text-sm">Sự cố đang xử lý</h2>
            <button class="text-xs text-blue-600 hover:underline" @click="router.push('/incidents/list')">Xem tất cả</button>
          </div>
          <template v-if="activeIncidents.length">
            <div class="divide-y divide-slate-50">
              <div
                v-for="ir in activeIncidents"
                :key="ir.name"
                class="px-4 py-3 hover:bg-slate-50 cursor-pointer flex items-start gap-3"
                @click="router.push(`/incidents/${ir.name}`)"
              >
                <span class="mt-0.5 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium shrink-0"
                      :class="SEV_COLOR[ir.severity] || 'bg-gray-100 text-gray-600'">
                  {{ ir.severity }}
                </span>
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-slate-800 truncate">{{ ir.asset_name || ir.asset }}</p>
                  <p class="text-xs text-slate-500 truncate">{{ ir.fault_code || '—' }}</p>
                </div>
                <div class="text-right shrink-0">
                  <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                        :class="STATUS_COLOR[ir.status] || 'bg-gray-100 text-gray-600'">
                    {{ ir.status }}
                  </span>
                  <p class="text-xs text-slate-400 mt-1">{{ formatDateTime(ir.reported_at) }}</p>
                </div>
              </div>
            </div>
          </template>
          <div v-else class="p-6 text-center text-slate-400 text-sm">Không có sự cố đang xử lý</div>
        </div>

        <!-- Open RCAs -->
        <div class="card overflow-hidden">
          <div class="px-4 py-3 border-b border-slate-100 flex justify-between items-center">
            <h2 class="font-semibold text-slate-800 text-sm">RCA đang mở</h2>
            <span class="text-xs text-slate-400">{{ openRcas.length }} hồ sơ</span>
          </div>
          <template v-if="openRcas.length">
            <div class="divide-y divide-slate-50">
              <div
                v-for="rca in openRcas"
                :key="rca.name"
                class="px-4 py-3 hover:bg-slate-50 cursor-pointer flex items-start gap-3"
                @click="router.push(`/rca/${rca.name}`)"
              >
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-slate-800 font-mono">{{ rca.name }}</p>
                  <p class="text-xs text-slate-500 truncate">{{ rca.asset || rca.incident_report || '—' }}</p>
                  <p v-if="rca.trigger_type" class="text-xs text-slate-400 mt-0.5">{{ rca.trigger_type }}</p>
                </div>
                <div class="text-right shrink-0">
                  <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                        :class="RCA_STATUS_COLOR[rca.status] || 'bg-gray-100 text-gray-600'">
                    {{ rca.status }}
                  </span>
                  <p class="text-xs mt-1"
                     :class="isOverdue(rca.due_date) ? 'text-red-500 font-semibold' : 'text-slate-400'">
                    Hạn: {{ formatDate(rca.due_date) }}
                  </p>
                </div>
              </div>
            </div>
          </template>
          <div v-else class="p-6 text-center text-slate-400 text-sm">Không có RCA đang mở</div>
        </div>

        <!-- Chronic failures -->
        <div class="card overflow-hidden lg:col-span-2">
          <div class="px-4 py-3 border-b border-slate-100">
            <h2 class="font-semibold text-slate-800 text-sm">Hỏng hóc mãn tính (Top 5 — 90 ngày)</h2>
          </div>
          <template v-if="chronicFailures.length">
            <div class="overflow-x-auto">
              <table class="w-full text-sm">
                <thead class="bg-slate-50 border-b border-slate-200">
                  <tr>
                    <th class="text-left px-4 py-2 font-semibold text-slate-600 text-xs">Thiết bị</th>
                    <th class="text-left px-4 py-2 font-semibold text-slate-600 text-xs">Fault Code</th>
                    <th class="text-center px-4 py-2 font-semibold text-slate-600 text-xs">Số lần</th>
                    <th class="text-left px-4 py-2 font-semibold text-slate-600 text-xs">Lần gần nhất</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100">
                  <tr
                    v-for="cf in chronicFailures"
                    :key="`${cf.asset}-${cf.fault_code}`"
                    class="hover:bg-slate-50 cursor-pointer"
                    @click="router.push(`/incidents/list`)"
                  >
                    <td class="px-4 py-2 font-medium text-slate-800">{{ cf.asset_name || cf.asset }}</td>
                    <td class="px-4 py-2 font-mono text-xs text-slate-600">{{ cf.fault_code }}</td>
                    <td class="px-4 py-2 text-center">
                      <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-red-100 text-red-700">
                        {{ cf.count || '≥3' }}
                      </span>
                    </td>
                    <td class="px-4 py-2 text-xs text-slate-500">{{ formatDateTime(cf.last_reported) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>
          <div v-else class="p-6 text-center text-slate-400 text-sm">Không phát hiện hỏng hóc mãn tính</div>
        </div>
      </div>
    </template>

    <!-- Empty state khi không loading, không lỗi, nhưng dashboard chưa có -->
    <div v-else class="p-12 text-center text-slate-400 text-sm">
      <p>Không tải được dữ liệu tổng quan.</p>
      <button class="btn-ghost text-xs mt-3" @click="store.fetchDashboard()">Thử lại</button>
    </div>
  </div>
</template>
