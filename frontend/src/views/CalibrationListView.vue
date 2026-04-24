<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useImm11Store } from '@/stores/imm11'
import { formatAssetDisplay, translateStatus, getStatusColor, formatDate } from '@/utils/formatters'

const router = useRouter()
const route = useRoute()
const store = useImm11Store()

const items = computed(() => store.calibrations)
const pagination = computed(() => store.pagination)
const kpis = computed(() => store.kpis?.kpis ?? null)
const loading = computed(() => store.loading)
const filterStatus = ref('')
const assetFilter = ref<string>((route.query.asset as string) || '')
const showFilters = ref(false)

const CAL_STATUSES = [
  { value: 'Scheduled',            label: 'Đã lên lịch' },
  { value: 'Sent to Lab',          label: 'Đã gửi phòng HC' },
  { value: 'In Progress',          label: 'Đang thực hiện' },
  { value: 'Certificate Received', label: 'Đã nhận chứng nhận' },
  { value: 'Passed',               label: 'Đạt' },
  { value: 'Failed',               label: 'Không đạt' },
  { value: 'Conditionally Passed', label: 'Đạt có điều kiện' },
  { value: 'Cancelled',            label: 'Đã hủy' },
]

interface Chip { key: 'status' | 'asset'; label: string }
const activeChips = computed<Chip[]>(() => {
  const chips: Chip[] = []
  if (filterStatus.value) {
    const s = CAL_STATUSES.find(x => x.value === filterStatus.value)
    chips.push({ key: 'status', label: s?.label ?? filterStatus.value })
  }
  if (assetFilter.value) chips.push({ key: 'asset', label: `TB: ${assetFilter.value}` })
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)

function clearChip(key: Chip['key']) {
  if (key === 'status') filterStatus.value = ''
  else assetFilter.value = ''
  load(1)
}

function resetFilters() {
  filterStatus.value = ''
  assetFilter.value = ''
  load(1)
}

function quickFilter(_key: 'status', value: string) {
  if (!value) return
  filterStatus.value = value
  showFilters.value = false
  load(1)
}

async function load(page = 1) {
  await store.fetchList({
    page, page_size: 20,
    status: filterStatus.value || undefined,
    asset: assetFilter.value || undefined,
  })
}

async function loadKpis() {
  await store.fetchKpis()
}

function isOverdue(date: string | null) {
  return date && new Date(date) < new Date()
}

watch(() => route.query.asset, (val) => {
  assetFilter.value = (val as string) || ''
  load(1)
})

onMounted(() => { load(); loadKpis() })
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">

    <!-- Header -->
    <div class="flex items-start justify-between">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-11</p>
        <h1 class="text-2xl font-bold text-slate-900">Hiệu chuẩn thiết bị</h1>
        <p class="text-sm text-slate-500 mt-1">
          Tổng <strong class="text-slate-700">{{ pagination.total ?? items.length }}</strong> phiếu
        </p>
      </div>
      <div class="flex items-center gap-2 shrink-0">
        <button
          class="relative flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg border transition-colors"
          :class="showFilters
            ? 'bg-brand-50 border-brand-300 text-brand-700'
            : 'bg-white border-slate-300 text-slate-600 hover:border-slate-400'"
          @click="showFilters = !showFilters"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3 4h18M7 8h10M11 12h2M9 16h6" />
          </svg>
          Bộ lọc
          <span v-if="activeFilterCount > 0"
            class="inline-flex items-center justify-center w-4 h-4 text-[10px] font-bold rounded-full bg-blue-500 text-white">
            {{ activeFilterCount }}
          </span>
          <svg class="w-3.5 h-3.5 transition-transform duration-200" :class="showFilters ? 'rotate-180' : ''"
               fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        <button class="btn-ghost text-sm shrink-0" @click="router.push('/calibration/schedules')">Lịch hiệu chuẩn</button>
        <button class="btn-primary text-sm shrink-0" @click="router.push('/calibration/new')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Tạo phiếu
        </button>
      </div>
    </div>

    <!-- Active chips -->
    <Transition
      enter-active-class="transition-all duration-200 ease-out"
      enter-from-class="opacity-0 -translate-y-1"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition-all duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div v-if="activeChips.length > 0 && !showFilters" class="flex flex-wrap items-center gap-2">
        <span class="text-xs text-slate-400 font-medium">Đang lọc:</span>
        <button v-for="chip in activeChips" :key="chip.key"
          class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 transition-colors"
          @click="clearChip(chip.key)"
        >
          {{ chip.label }}
          <svg class="w-3 h-3 opacity-60" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        <button class="text-xs text-slate-400 hover:text-red-500 underline underline-offset-2" @click="resetFilters">
          Xóa tất cả
        </button>
      </div>
    </Transition>

    <!-- Collapsible filter panel -->
    <Transition
      enter-active-class="transition-all duration-200 ease-out overflow-hidden"
      enter-from-class="opacity-0 max-h-0"
      enter-to-class="opacity-100 max-h-40"
      leave-active-class="transition-all duration-150 ease-in overflow-hidden"
      leave-from-class="opacity-100 max-h-40"
      leave-to-class="opacity-0 max-h-0"
    >
      <div v-show="showFilters" class="card p-4 space-y-3">
        <div class="flex flex-wrap gap-3">
          <select v-model="filterStatus" class="form-select text-sm w-56" @change="load(1)">
            <option value="">Tất cả trạng thái</option>
            <option v-for="s in CAL_STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
          <input v-model="assetFilter" placeholder="Mã AC Asset..." class="form-input text-sm w-52" @keyup.enter="load(1)" />
          <button class="btn-ghost text-sm" @click="resetFilters">Đặt lại</button>
        </div>
        <div v-if="activeChips.length > 0" class="flex flex-wrap items-center gap-2 pt-3 border-t border-slate-100">
          <span class="text-xs text-slate-400 font-medium">Đang lọc:</span>
          <button v-for="chip in activeChips" :key="chip.key"
            class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 transition-colors"
            @click="clearChip(chip.key)"
          >
            {{ chip.label }}
            <svg class="w-3 h-3 opacity-60" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    </Transition>

    <!-- KPI Cards -->
    <div v-if="kpis" class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      <div class="card p-3 text-center">
        <p class="text-xs text-slate-400 mb-1">Tháng này</p>
        <p class="text-2xl font-bold text-slate-700">{{ kpis.total_this_month }}</p>
      </div>
      <div class="card p-3 text-center">
        <p class="text-xs text-slate-400 mb-1">Đã qua</p>
        <p class="text-2xl font-bold text-green-600">{{ kpis.completed }}</p>
      </div>
      <div class="card p-3 text-center">
        <p class="text-xs text-slate-400 mb-1">Thất bại</p>
        <p class="text-2xl font-bold text-red-600">{{ kpis.failed }}</p>
      </div>
      <div class="card p-3 text-center">
        <p class="text-xs text-slate-400 mb-1">Pass rate</p>
        <p class="text-2xl font-bold text-blue-600">{{ kpis.pass_rate_pct }}%</p>
      </div>
      <div class="card p-3 text-center">
        <p class="text-xs text-slate-400 mb-1">Quá hạn</p>
        <p class="text-2xl font-bold text-red-500">{{ kpis.overdue_assets }}</p>
      </div>
      <div class="card p-3 text-center">
        <p class="text-xs text-slate-400 mb-1">Sắp đến hạn</p>
        <p class="text-2xl font-bold text-yellow-600">{{ kpis.due_soon_assets }}</p>
      </div>
    </div>

    <!-- Table -->
    <div class="card overflow-hidden">
      <!-- Info row -->
      <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span>Hiển thị <strong class="text-slate-700">{{ items.length }}</strong> / {{ pagination.total }} phiếu</span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>
      <div v-if="loading" class="p-8 text-center text-slate-400">Đang tải...</div>
      <div v-else-if="!items.length" class="flex flex-col items-center justify-center py-16 text-slate-400">
        <p class="text-sm font-medium">Chưa có phiếu hiệu chuẩn nào</p>
        <button v-if="activeFilterCount > 0" class="text-xs text-blue-500 hover:text-blue-700 underline mt-2" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
      </div>
      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 border-b border-slate-200">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Mã</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Thiết bị</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Loại</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Trạng thái</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Ngày dự kiến</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Kết quả</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Ngày cal tiếp</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="c in items" :key="c.name"
              class="hover:bg-slate-50 cursor-pointer transition-all hover:translate-x-0.5"
              @click="router.push(`/calibration/${c.name}`)"
            >
              <td class="px-4 py-3 font-mono text-xs text-slate-400">{{ c.name }}</td>
              <td class="px-4 py-3">
                <div class="font-medium text-slate-900 truncate max-w-[240px]">
                  {{ formatAssetDisplay(c.asset_name, c.asset).main }}
                </div>
                <div v-if="formatAssetDisplay(c.asset_name, c.asset).hasBoth"
                     class="text-xs text-slate-400 font-mono">
                  {{ formatAssetDisplay(c.asset_name, c.asset).sub }}
                </div>
              </td>
              <td class="px-4 py-3 text-slate-600">{{ c.calibration_type }}</td>
              <td class="px-4 py-3">
                <button
                  :class="['inline-block px-2 py-0.5 rounded-full text-xs font-medium transition-all hover:ring-2 hover:ring-offset-1 hover:ring-current/50', getStatusColor(c.status)]"
                  :title="`Lọc: ${translateStatus(c.status)}`"
                  @click.stop="quickFilter('status', c.status)"
                >{{ translateStatus(c.status) }}</button>
              </td>
              <td class="px-4 py-3 text-slate-600">{{ formatDate(c.scheduled_date) }}</td>
              <td class="px-4 py-3">
                <span v-if="c.overall_result"
                      :class="['inline-block px-2 py-0.5 rounded-full text-xs font-semibold', getStatusColor(c.overall_result)]">
                  {{ translateStatus(c.overall_result) }}
                </span>
                <span v-else class="text-slate-300">—</span>
              </td>
              <td class="px-4 py-3 text-xs"
                  :class="isOverdue(c.next_calibration_date) ? 'text-red-600 font-semibold' : 'text-slate-500'">
                {{ formatDate(c.next_calibration_date) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="pagination.total_pages > 1" class="flex justify-center gap-2">
      <button :disabled="pagination.page <= 1" class="btn-ghost text-sm" @click="load(pagination.page - 1)">← Trước</button>
      <span class="text-sm text-slate-500 self-center">{{ pagination.page }}/{{ pagination.total_pages }}</span>
      <button :disabled="pagination.page >= pagination.total_pages" class="btn-ghost text-sm" @click="load(pagination.page + 1)">Sau →</button>
    </div>
  </div>
</template>
