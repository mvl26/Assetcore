<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { frappeGet } from '@/api/helpers'

interface Overview {
  generated_at: string
  assets: { total: number; active: number; under_repair: number; calibrating: number; out_of_service: number; decommissioned: number; byt_expiring_30d: number; byt_expired: number }
  commissioning: { pending: number; released: number; hold: number; open_nc: number }
  documents: { total: number; expiring_30d: number; expired: number; requests_open: number }
  pm: { open: number; overdue: number; due_next_7d: number; completed_30d: number }
  cm: { open: number; sla_breached: number; repeat_failure: number; completed_30d: number }
  calibration: { due_30d: number; overdue: number }
  incidents: { open: number; critical_open: number }
  capa: { open: number; overdue: number }
  lifecycle_breakdown: Array<{ state: string; count: number }>
  recent_incidents: Array<{ name: string; asset: string; asset_name?: string; severity: string; status: string; description: string; reported_at: string }>
  recent_pm: Array<{ name: string; asset_ref: string; asset_name?: string; pm_type?: string; status: string; due_date?: string; is_late?: number }>
}

const router = useRouter()
const data = ref<Overview | null>(null)
const loading = ref(false)
const error = ref('')

const LIFECYCLE_LABEL: Record<string, string> = {
  'Commissioned': 'Đã tiếp nhận',
  'Active': 'Đang hoạt động',
  'Under Repair': 'Đang sửa chữa',
  'Calibrating': 'Đang hiệu chuẩn',
  'Out of Service': 'Ngừng hoạt động',
  'Decommissioned': 'Đã thanh lý',
}

const LIFECYCLE_COLOR: Record<string, string> = {
  'Commissioned': '#2563eb',
  'Active': '#059669',
  'Under Repair': '#d97706',
  'Calibrating': '#7c3aed',
  'Out of Service': '#dc2626',
  'Decommissioned': '#64748b',
}

const SEVERITY_LABEL: Record<string, string> = {
  'Low': 'Thấp', 'Medium': 'Trung bình', 'High': 'Cao', 'Critical': 'Nghiêm trọng',
}

const SEVERITY_COLOR: Record<string, string> = {
  'Low': 'bg-green-100 text-green-700',
  'Medium': 'bg-yellow-100 text-yellow-700',
  'High': 'bg-orange-100 text-orange-700',
  'Critical': 'bg-red-100 text-red-700',
}

async function fetchData() {
  loading.value = true
  error.value = ''
  try {
    const res = await frappeGet<Overview>('/api/method/assetcore.api.dashboard.get_overview')
    data.value = res
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Không thể tải dữ liệu tổng quan'
  } finally {
    loading.value = false
  }
}

const maxLifecycle = computed(() => Math.max(1, ...(data.value?.lifecycle_breakdown.map(s => s.count) ?? [1])))

function fmtDate(d?: string) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('vi-VN')
}

function fmtDateTime(d?: string) {
  if (!d) return '—'
  return new Date(d).toLocaleString('vi-VN')
}

onMounted(fetchData)
</script>

<template>
  <div class="page-container animate-fade-in">
    <!-- Header -->
    <div class="flex items-start justify-between mb-7">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">Tổng quan hệ thống</p>
        <h1 class="font-display text-2xl font-bold text-slate-900 leading-tight">Trung tâm điều hành AssetCore</h1>
        <p class="text-sm text-slate-500 mt-1">Theo dõi toàn bộ vòng đời thiết bị y tế — Tiếp nhận, Bảo trì, Sửa chữa, Hiệu chuẩn</p>
      </div>
      <button class="btn-secondary" :disabled="loading" @click="fetchData">
        <svg class="w-4 h-4" :class="loading ? 'animate-spin-slow' : ''" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        Làm mới
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading && !data" class="card p-10 text-center text-slate-400">Đang tải dữ liệu...</div>

    <!-- Error -->
    <div v-else-if="error && !data" class="alert-error">{{ error }}</div>

    <template v-else-if="data">
      <!-- Critical alerts row -->
      <div v-if="data.incidents.critical_open > 0 || data.cm.sla_breached > 0 || data.pm.overdue > 0 || data.assets.byt_expired > 0" class="grid grid-cols-1 md:grid-cols-4 gap-3 mb-6">
        <button
          v-if="data.incidents.critical_open > 0"
          class="flex items-center gap-3 p-3 rounded-xl border border-red-200 bg-red-50 hover:bg-red-100 transition-colors text-left"
          @click="router.push('/incidents')"
        >
          <div class="w-9 h-9 rounded-lg bg-red-100 flex items-center justify-center shrink-0">🚨</div>
          <div>
            <p class="text-xs text-red-600 font-medium">Sự cố nghiêm trọng</p>
            <p class="text-lg font-bold text-red-700">{{ data.incidents.critical_open }}</p>
          </div>
        </button>
        <button
          v-if="data.cm.sla_breached > 0"
          class="flex items-center gap-3 p-3 rounded-xl border border-orange-200 bg-orange-50 hover:bg-orange-100 transition-colors text-left"
          @click="router.push('/cm/work-orders')"
        >
          <div class="w-9 h-9 rounded-lg bg-orange-100 flex items-center justify-center shrink-0">⚠️</div>
          <div>
            <p class="text-xs text-orange-600 font-medium">WO vi phạm SLA</p>
            <p class="text-lg font-bold text-orange-700">{{ data.cm.sla_breached }}</p>
          </div>
        </button>
        <button
          v-if="data.pm.overdue > 0"
          class="flex items-center gap-3 p-3 rounded-xl border border-amber-200 bg-amber-50 hover:bg-amber-100 transition-colors text-left"
          @click="router.push('/pm/work-orders')"
        >
          <div class="w-9 h-9 rounded-lg bg-amber-100 flex items-center justify-center shrink-0">⏰</div>
          <div>
            <p class="text-xs text-amber-600 font-medium">PM quá hạn</p>
            <p class="text-lg font-bold text-amber-700">{{ data.pm.overdue }}</p>
          </div>
        </button>
        <button
          v-if="data.assets.byt_expired > 0"
          class="flex items-center gap-3 p-3 rounded-xl border border-red-200 bg-red-50 hover:bg-red-100 transition-colors text-left"
          @click="router.push('/assets')"
        >
          <div class="w-9 h-9 rounded-lg bg-red-100 flex items-center justify-center shrink-0">📋</div>
          <div>
            <p class="text-xs text-red-600 font-medium">Hết hạn đăng ký BYT</p>
            <p class="text-lg font-bold text-red-700">{{ data.assets.byt_expired }}</p>
          </div>
        </button>
      </div>

      <!-- Main KPI grid — 4 modules -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <!-- Thiết bị -->
        <button class="card p-5 text-left hover:shadow-md transition-shadow animate-slide-up" @click="router.push('/assets')">
          <div class="flex items-center justify-between mb-3">
            <p class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Thiết bị</p>
            <span class="text-xs text-slate-400">IMM-00</span>
          </div>
          <p class="font-display text-3xl font-bold text-slate-900 mb-2">{{ data.assets.total }}</p>
          <div class="space-y-1 text-xs">
            <div class="flex justify-between"><span class="text-slate-500">Đang hoạt động</span><span class="font-semibold text-green-600">{{ data.assets.active }}</span></div>
            <div class="flex justify-between"><span class="text-slate-500">Đang sửa chữa</span><span class="font-semibold text-amber-600">{{ data.assets.under_repair }}</span></div>
            <div class="flex justify-between"><span class="text-slate-500">Ngừng hoạt động</span><span class="font-semibold text-red-600">{{ data.assets.out_of_service }}</span></div>
          </div>
        </button>

        <!-- Tiếp nhận -->
        <button class="card p-5 text-left hover:shadow-md transition-shadow animate-slide-up" style="animation-delay: 60ms" @click="router.push('/commissioning')">
          <div class="flex items-center justify-between mb-3">
            <p class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Tiếp nhận</p>
            <span class="text-xs text-slate-400">IMM-04</span>
          </div>
          <p class="font-display text-3xl font-bold text-slate-900 mb-2">{{ data.commissioning.pending }}</p>
          <div class="space-y-1 text-xs">
            <div class="flex justify-between"><span class="text-slate-500">Đã phát hành</span><span class="font-semibold text-green-600">{{ data.commissioning.released }}</span></div>
            <div class="flex justify-between"><span class="text-slate-500">Clinical Hold</span><span class="font-semibold text-red-600">{{ data.commissioning.hold }}</span></div>
            <div class="flex justify-between"><span class="text-slate-500">NC chưa xử lý</span><span class="font-semibold text-amber-600">{{ data.commissioning.open_nc }}</span></div>
          </div>
        </button>

        <!-- Bảo trì PM -->
        <button class="card p-5 text-left hover:shadow-md transition-shadow animate-slide-up" style="animation-delay: 120ms" @click="router.push('/pm/dashboard')">
          <div class="flex items-center justify-between mb-3">
            <p class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Bảo trì định kỳ</p>
            <span class="text-xs text-slate-400">IMM-08</span>
          </div>
          <p class="font-display text-3xl font-bold text-slate-900 mb-2">{{ data.pm.open }}</p>
          <div class="space-y-1 text-xs">
            <div class="flex justify-between"><span class="text-slate-500">Đến hạn 7 ngày</span><span class="font-semibold text-amber-600">{{ data.pm.due_next_7d }}</span></div>
            <div class="flex justify-between"><span class="text-slate-500">Quá hạn</span><span class="font-semibold text-red-600">{{ data.pm.overdue }}</span></div>
            <div class="flex justify-between"><span class="text-slate-500">Hoàn thành 30d</span><span class="font-semibold text-green-600">{{ data.pm.completed_30d }}</span></div>
          </div>
        </button>

        <!-- Sửa chữa CM -->
        <button class="card p-5 text-left hover:shadow-md transition-shadow animate-slide-up" style="animation-delay: 180ms" @click="router.push('/cm/dashboard')">
          <div class="flex items-center justify-between mb-3">
            <p class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Sửa chữa</p>
            <span class="text-xs text-slate-400">IMM-09</span>
          </div>
          <p class="font-display text-3xl font-bold text-slate-900 mb-2">{{ data.cm.open }}</p>
          <div class="space-y-1 text-xs">
            <div class="flex justify-between"><span class="text-slate-500">Vi phạm SLA</span><span class="font-semibold text-red-600">{{ data.cm.sla_breached }}</span></div>
            <div class="flex justify-between"><span class="text-slate-500">Tái hỏng</span><span class="font-semibold text-orange-600">{{ data.cm.repeat_failure }}</span></div>
            <div class="flex justify-between"><span class="text-slate-500">Hoàn thành 30d</span><span class="font-semibold text-green-600">{{ data.cm.completed_30d }}</span></div>
          </div>
        </button>
      </div>

      <!-- Secondary KPIs — 4 modules -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <button class="card p-4 text-left hover:shadow-md transition-shadow" @click="router.push('/documents')">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center text-xl">📁</div>
            <div class="flex-1 min-w-0">
              <p class="text-xs text-slate-500">Hồ sơ tài liệu (IMM-05)</p>
              <p class="font-display text-xl font-bold text-slate-900">{{ data.documents.total }}</p>
              <p class="text-xs text-amber-600 mt-0.5" v-if="data.documents.expired">
                {{ data.documents.expired }} hết hạn
              </p>
            </div>
          </div>
        </button>

        <button class="card p-4 text-left hover:shadow-md transition-shadow" @click="router.push('/calibration')">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-lg bg-purple-50 flex items-center justify-center text-xl">📏</div>
            <div class="flex-1 min-w-0">
              <p class="text-xs text-slate-500">Hiệu chuẩn (IMM-11)</p>
              <p class="font-display text-xl font-bold text-slate-900">{{ data.calibration.due_30d + data.calibration.overdue }}</p>
              <p class="text-xs text-red-600 mt-0.5" v-if="data.calibration.overdue">
                {{ data.calibration.overdue }} quá hạn
              </p>
            </div>
          </div>
        </button>

        <button class="card p-4 text-left hover:shadow-md transition-shadow" @click="router.push('/incidents')">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-lg bg-red-50 flex items-center justify-center text-xl">⚠️</div>
            <div class="flex-1 min-w-0">
              <p class="text-xs text-slate-500">Sự cố đang mở</p>
              <p class="font-display text-xl font-bold text-slate-900">{{ data.incidents.open }}</p>
              <p class="text-xs text-red-600 mt-0.5" v-if="data.incidents.critical_open">
                {{ data.incidents.critical_open }} nghiêm trọng
              </p>
            </div>
          </div>
        </button>

        <button class="card p-4 text-left hover:shadow-md transition-shadow" @click="router.push('/capas')">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-lg bg-orange-50 flex items-center justify-center text-xl">📝</div>
            <div class="flex-1 min-w-0">
              <p class="text-xs text-slate-500">CAPA đang mở</p>
              <p class="font-display text-xl font-bold text-slate-900">{{ data.capa.open }}</p>
              <p class="text-xs text-red-600 mt-0.5" v-if="data.capa.overdue">
                {{ data.capa.overdue }} quá hạn
              </p>
            </div>
          </div>
        </button>
      </div>

      <!-- Charts + Recent lists -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <!-- Lifecycle breakdown chart -->
        <div class="card p-5">
          <h3 class="text-sm font-semibold text-slate-800 mb-4">Phân bổ vòng đời thiết bị</h3>
          <div class="space-y-3">
            <div v-for="s in data.lifecycle_breakdown" :key="s.state" class="flex items-center gap-3">
              <div class="w-32 shrink-0 text-xs text-slate-600">{{ LIFECYCLE_LABEL[s.state] || s.state }}</div>
              <div class="flex-1 h-2 rounded-full overflow-hidden bg-slate-100">
                <div
                  class="h-full rounded-full transition-all"
                  :style="{ width: `${(s.count / maxLifecycle) * 100}%`, background: LIFECYCLE_COLOR[s.state] || '#64748b' }"
                />
              </div>
              <span class="text-xs font-semibold text-slate-700 w-8 text-right tabular-nums">{{ s.count }}</span>
            </div>
          </div>
        </div>

        <!-- Recent incidents -->
        <div class="card p-0 overflow-hidden">
          <div class="flex items-center justify-between px-5 py-4 border-b border-slate-100">
            <h3 class="text-sm font-semibold text-slate-800">Sự cố gần đây</h3>
            <button class="text-xs text-blue-600 hover:underline" @click="router.push('/incidents')">Xem tất cả →</button>
          </div>
          <ul v-if="data.recent_incidents.length" class="divide-y divide-slate-100">
            <li
              v-for="ir in data.recent_incidents"
              :key="ir.name"
              class="px-5 py-3 hover:bg-slate-50 cursor-pointer transition-colors"
              @click="router.push(`/incidents/${ir.name}`)"
            >
              <div class="flex items-start justify-between gap-2 mb-1">
                <span class="text-sm font-medium text-slate-800 truncate flex-1">
                  {{ ir.description?.replace(/<[^>]+>/g, '').slice(0, 60) || '—' }}
                </span>
                <span :class="['px-2 py-0.5 rounded text-[10px] font-medium shrink-0', SEVERITY_COLOR[ir.severity] || 'bg-gray-100 text-gray-600']">
                  {{ SEVERITY_LABEL[ir.severity] || ir.severity }}
                </span>
              </div>
              <p class="text-xs text-slate-500 truncate">
                {{ ir.asset_name || ir.asset || '—' }} · {{ fmtDateTime(ir.reported_at) }}
              </p>
            </li>
          </ul>
          <div v-else class="px-5 py-10 text-center text-slate-400 text-sm">Không có sự cố gần đây</div>
        </div>

        <!-- Upcoming PM -->
        <div class="card p-0 overflow-hidden">
          <div class="flex items-center justify-between px-5 py-4 border-b border-slate-100">
            <h3 class="text-sm font-semibold text-slate-800">Bảo trì sắp đến hạn</h3>
            <button class="text-xs text-blue-600 hover:underline" @click="router.push('/pm/work-orders')">Xem tất cả →</button>
          </div>
          <ul v-if="data.recent_pm.length" class="divide-y divide-slate-100">
            <li
              v-for="wo in data.recent_pm"
              :key="wo.name"
              class="px-5 py-3 hover:bg-slate-50 cursor-pointer transition-colors"
              @click="router.push(`/pm/work-orders/${wo.name}`)"
            >
              <div class="flex items-center justify-between gap-2">
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-slate-800 truncate">{{ wo.asset_name || wo.asset_ref }}</p>
                  <p class="text-xs text-slate-400 truncate">{{ wo.name }} · {{ wo.pm_type || 'PM' }}</p>
                </div>
                <div class="text-right shrink-0">
                  <p :class="wo.is_late ? 'text-xs font-semibold text-red-600' : 'text-xs text-slate-600'">
                    {{ fmtDate(wo.due_date) }}
                  </p>
                  <p v-if="wo.is_late" class="text-[10px] text-red-500">Quá hạn</p>
                </div>
              </div>
            </li>
          </ul>
          <div v-else class="px-5 py-10 text-center text-slate-400 text-sm">Không có phiếu PM sắp đến hạn</div>
        </div>
      </div>

      <p class="text-xs text-slate-400 mt-5 text-right">Cập nhật: {{ fmtDateTime(data.generated_at) }}</p>
    </template>
  </div>
</template>
