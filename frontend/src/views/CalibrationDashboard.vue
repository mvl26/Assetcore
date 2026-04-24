<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// IMM-11 Calibration Dashboard — theo docs/imm-11/IMM-11_UI_UX_Guide.md §3.3
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { frappeGet } from '@/api/helpers'
import { useImm11Store } from '@/stores/imm11'

const store = useImm11Store()

const router = useRouter()

interface CalAssetRow {
  name: string
  asset_name: string
  device_model: string
  next_calibration_date: string
  location: string
}

interface CapaRow {
  name: string
  asset: string
  source_ref: string
  severity: string
  opened_date: string
  due_date: string
  status: string
  lookback_status: string
}

interface DashboardKpis {
  compliance_pct: number
  total_scheduled: number
  completed: number
  oot_pct: number
  oot_count: number
  measurements_total: number
  capa_open: number
  avg_days_to_cert: number
  overdue_count: number
  due_soon_count: number
  failed: number
}

interface DashboardData {
  kpis: DashboardKpis
  overdue_assets: CalAssetRow[]
  due_soon_assets: CalAssetRow[]
  capa_open_list: CapaRow[]
  period: { year: number; month: number; start: string; end: string }
}

const loading = ref(false)
const err = ref('')
const data = ref<DashboardData | null>(null)

const BASE = '/api/method/assetcore.api.imm11'

async function load() {
  loading.value = true; err.value = ''
  try {
    const res = await frappeGet<DashboardData>(`${BASE}.get_calibration_dashboard`)
    data.value = res
    // Sync due items vào store để các view khác có thể dùng
    await store.fetchDue()
  } catch (e: unknown) {
    err.value = (e as Error).message || 'Không tải được dashboard'
  } finally { loading.value = false }
}

function daysUntil(d: string | null): number {
  if (!d) return 0
  const diffMs = new Date(d).getTime() - Date.now()
  return Math.ceil(diffMs / (1000 * 60 * 60 * 24))
}

function formatDate(d: string) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('vi-VN')
}

const periodLabel = computed(() => {
  if (!data.value) return ''
  const p = data.value.period
  return `Tháng ${String(p.month).padStart(2, '0')}/${p.year}`
})

onMounted(load)
</script>

<template>
  <div class="page-container space-y-5">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-11</p>
        <h1 class="text-2xl font-bold text-slate-900">Bảng điều khiển Hiệu chuẩn</h1>
      </div>
      <div class="flex items-center gap-3">
        <span class="text-sm text-slate-500">{{ periodLabel }}</span>
        <button class="btn-ghost text-sm" @click="load">↻ Làm mới</button>
        <button class="btn-primary text-sm" @click="router.push('/calibration/new')">+ Tạo phiếu</button>
      </div>
    </div>

    <div v-if="err" class="alert-error">{{ err }}</div>
    <div v-if="loading && !data" class="card p-10 text-center text-slate-400">Đang tải...</div>

    <template v-else-if="data">
      <!-- KPI Row — 4 cards per UI/UX spec -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        <!-- Tỷ lệ tuân thủ -->
        <div class="card p-4">
          <p class="text-xs text-slate-400 uppercase tracking-wider mb-1">Tỷ lệ tuân thủ</p>
          <p class="text-3xl font-bold"
             :class="data.kpis.compliance_pct >= 95 ? 'text-green-600' : data.kpis.compliance_pct >= 80 ? 'text-yellow-600' : 'text-red-600'">
            {{ data.kpis.compliance_pct }}%
          </p>
          <div class="mt-2 h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div class="h-full rounded-full transition-all"
              :style="`width: ${data.kpis.compliance_pct}%`"
              :class="data.kpis.compliance_pct >= 95 ? 'bg-green-500' : data.kpis.compliance_pct >= 80 ? 'bg-yellow-500' : 'bg-red-500'"></div>
          </div>
          <p class="text-xs text-slate-500 mt-2">{{ data.kpis.completed }}/{{ data.kpis.total_scheduled }} đúng hạn</p>
        </div>

        <!-- OOT Rate -->
        <div class="card p-4">
          <p class="text-xs text-slate-400 uppercase tracking-wider mb-1">Out-of-Tolerance</p>
          <p class="text-3xl font-bold"
             :class="data.kpis.oot_pct < 5 ? 'text-green-600' : 'text-red-600'">
            {{ data.kpis.oot_pct }}%
          </p>
          <p class="text-xs text-slate-500 mt-4">
            {{ data.kpis.oot_count }}/{{ data.kpis.measurements_total || 0 }} tham số Fail
          </p>
        </div>

        <!-- CAPA Open -->
        <div class="card p-4">
          <p class="text-xs text-slate-400 uppercase tracking-wider mb-1">CAPA Open</p>
          <p class="text-3xl font-bold" :class="data.kpis.capa_open > 0 ? 'text-orange-600' : 'text-green-600'">
            {{ data.kpis.capa_open }}
          </p>
          <p v-if="data.kpis.capa_open > 0" class="text-xs text-orange-600 mt-4 font-medium">⚠ cần xử lý</p>
          <p v-else class="text-xs text-slate-500 mt-4">không có</p>
        </div>

        <!-- Avg Days to Cert -->
        <div class="card p-4">
          <p class="text-xs text-slate-400 uppercase tracking-wider mb-1">Avg Days → Cert</p>
          <p class="text-3xl font-bold text-blue-600">{{ data.kpis.avg_days_to_cert }}</p>
          <p class="text-xs text-slate-500 mt-4">gửi → nhận (external)</p>
        </div>
      </div>

      <!-- Assets Due 30d: Overdue + Due Soon -->
      <div class="card overflow-hidden">
        <div class="flex items-center justify-between px-5 py-3 bg-slate-50 border-b">
          <h2 class="text-base font-semibold text-slate-800">Thiết bị đến hạn trong 30 ngày</h2>
          <button class="text-sm text-blue-600 hover:text-blue-700" @click="router.push('/calibration/schedules')">
            Xem tất cả →
          </button>
        </div>
        <div class="divide-y divide-slate-100">
          <!-- Overdue section -->
          <div class="px-5 py-4">
            <div class="flex items-center gap-2 mb-3">
              <span class="inline-block w-2 h-2 rounded-full bg-red-500"></span>
              <span class="text-sm font-semibold text-red-700">
                Overdue ({{ data.kpis.overdue_count }})
              </span>
            </div>
            <div v-if="!data.overdue_assets.length" class="text-sm text-slate-400 italic ml-4">
              Không có thiết bị quá hạn.
            </div>
            <div v-else class="space-y-2">
              <div v-for="a in data.overdue_assets" :key="a.name"
                class="flex items-center justify-between p-2.5 rounded-lg border border-red-100 bg-red-50/50 hover:bg-red-50 transition-colors">
                <div class="flex items-center gap-3 min-w-0">
                  <button class="font-mono text-xs text-red-600 font-semibold hover:underline shrink-0"
                    @click="router.push(`/assets/${a.name}`)">{{ a.name }}</button>
                  <div class="min-w-0">
                    <p class="text-sm font-medium text-slate-800 truncate">{{ a.asset_name }}</p>
                    <p class="text-xs text-slate-500 truncate">
                      {{ a.device_model }}{{ a.location ? ` · ${a.location}` : '' }}
                    </p>
                  </div>
                </div>
                <div class="flex items-center gap-3 shrink-0">
                  <span class="text-xs text-red-700 font-semibold">
                    Quá hạn {{ Math.abs(daysUntil(a.next_calibration_date)) }} ngày
                  </span>
                  <button class="btn-primary text-xs py-1 px-2.5"
                    @click="router.push(`/calibration/new?asset=${a.name}`)">
                    Tạo CAL
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Due Soon section -->
          <div class="px-5 py-4">
            <div class="flex items-center gap-2 mb-3">
              <span class="inline-block w-2 h-2 rounded-full bg-yellow-500"></span>
              <span class="text-sm font-semibold text-yellow-700">
                Due Soon ({{ data.kpis.due_soon_count }})
              </span>
            </div>
            <div v-if="!data.due_soon_assets.length" class="text-sm text-slate-400 italic ml-4">
              Không có thiết bị sắp đến hạn.
            </div>
            <div v-else class="space-y-2">
              <div v-for="a in data.due_soon_assets" :key="a.name"
                class="flex items-center justify-between p-2.5 rounded-lg border border-yellow-100 bg-yellow-50/40 hover:bg-yellow-50 transition-colors">
                <div class="flex items-center gap-3 min-w-0">
                  <button class="font-mono text-xs text-yellow-700 font-semibold hover:underline shrink-0"
                    @click="router.push(`/assets/${a.name}`)">{{ a.name }}</button>
                  <div class="min-w-0">
                    <p class="text-sm font-medium text-slate-800 truncate">{{ a.asset_name }}</p>
                    <p class="text-xs text-slate-500 truncate">
                      {{ a.device_model }}{{ a.location ? ` · ${a.location}` : '' }}
                    </p>
                  </div>
                </div>
                <div class="flex items-center gap-3 shrink-0">
                  <span class="text-xs text-yellow-700 font-medium">
                    Còn {{ daysUntil(a.next_calibration_date) }} ngày
                  </span>
                  <button class="btn-ghost text-xs py-1 px-2.5 border border-yellow-300"
                    @click="router.push(`/calibration/new?asset=${a.name}`)">
                    Tạo CAL
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- CAPA Open -->
      <div class="card overflow-hidden">
        <div class="flex items-center justify-between px-5 py-3 bg-slate-50 border-b">
          <h2 class="text-base font-semibold text-slate-800">CAPA Đang Mở</h2>
          <button class="text-sm text-blue-600 hover:text-blue-700" @click="router.push('/capas')">
            Xem tất cả →
          </button>
        </div>
        <div class="p-5">
          <div v-if="!data.capa_open_list.length" class="text-sm text-slate-400 italic">
            Không có CAPA đang mở từ Calibration.
          </div>
          <div v-else class="space-y-2">
            <div v-for="c in data.capa_open_list" :key="c.name"
              class="flex items-center justify-between p-2.5 rounded-lg border border-slate-200 hover:bg-slate-50 cursor-pointer transition-colors"
              @click="router.push(`/capas/${c.name}`)">
              <div class="flex items-center gap-3 min-w-0">
                <span class="font-mono text-xs text-slate-500 shrink-0">{{ c.name }}</span>
                <div class="min-w-0">
                  <p class="text-sm font-medium text-slate-800 truncate">
                    {{ c.asset }} — {{ c.source_ref }}
                  </p>
                  <div class="flex items-center gap-2 mt-0.5">
                    <span class="text-xs px-1.5 py-0.5 rounded"
                      :class="c.severity === 'Major' || c.severity === 'Critical'
                              ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'">
                      {{ c.severity }}
                    </span>
                    <span v-if="c.lookback_status === 'In Progress' || c.lookback_status === 'Pending'"
                      class="text-xs px-1.5 py-0.5 rounded bg-orange-100 text-orange-700 font-medium">
                      Lookback {{ c.lookback_status }}
                    </span>
                    <span class="text-xs text-slate-500">
                      Due {{ formatDate(c.due_date) }}
                    </span>
                  </div>
                </div>
              </div>
              <button class="btn-ghost text-xs shrink-0" @click.stop="router.push(`/capas/${c.name}`)">
                QA Review →
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
