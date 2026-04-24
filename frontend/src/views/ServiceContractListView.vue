<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { frappeGet } from '@/api/helpers'
import type { ServiceContract } from '@/types/imm00'

type ServiceContractRow = ServiceContract & { supplier_name?: string }

const router = useRouter()

const contracts = ref<ServiceContractRow[]>([])
const contractType = ref('')
const loading = ref(false)
const error = ref('')
const page = ref(1)
const totalCount = ref(0)
const showFilters = ref(false)
const PAGE_SIZE = 30

const BASE = '/api/method/assetcore.api.imm00'

const CONTRACT_TYPES = ['Preventive Maintenance', 'Calibration', 'Repair', 'Full Service', 'Warranty Extension']

const CONTRACT_TYPE_LABEL: Record<string, string> = {
  'Preventive Maintenance': 'Bảo trì định kỳ',
  'Calibration': 'Hiệu chuẩn',
  'Repair': 'Sửa chữa',
  'Full Service': 'Trọn gói',
  'Warranty Extension': 'Gia hạn bảo hành',
}

const TYPE_COLORS: Record<string, string> = {
  'Preventive Maintenance': 'bg-blue-100 text-blue-700',
  'Calibration': 'bg-purple-100 text-purple-700',
  'Repair': 'bg-yellow-100 text-yellow-700',
  'Full Service': 'bg-green-100 text-green-700',
  'Warranty Extension': 'bg-gray-100 text-gray-600',
}

interface Chip { key: 'contractType'; label: string }
const activeChips = computed<Chip[]>(() => {
  const chips: Chip[] = []
  if (contractType.value) {
    chips.push({ key: 'contractType', label: CONTRACT_TYPE_LABEL[contractType.value] || contractType.value })
  }
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)

function clearChip(key: Chip['key']) {
  if (key === 'contractType') contractType.value = ''
  page.value = 1
  load()
}

function resetFilters() {
  contractType.value = ''
  page.value = 1
  load()
}

function quickFilter(type: string) {
  if (!type) return
  contractType.value = type
  showFilters.value = false
  page.value = 1
  load()
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await frappeGet<{ items: ServiceContractRow[]; pagination: { total: number } } | null>(
      `${BASE}.list_service_contracts`,
      {
        page: page.value,
        page_size: PAGE_SIZE,
        ...(contractType.value ? { contract_type: contractType.value } : {}),
      },
    )
    if (res) {
      contracts.value = res.items || []
      totalCount.value = res.pagination?.total || 0
    }
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Không thể tải danh sách hợp đồng. Vui lòng thử lại.'
  } finally {
    loading.value = false
  }
}

function prevPage() { if (page.value > 1) { page.value--; load() } }
function nextPage() { if (page.value * PAGE_SIZE < totalCount.value) { page.value++; load() } }

function formatDate(d?: string) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('vi-VN')
}

function daysUntilExpiry(d?: string) {
  if (!d) return null
  return Math.ceil((new Date(d).getTime() - Date.now()) / 86400000)
}

function expiryClass(d?: string) {
  const days = daysUntilExpiry(d)
  if (days === null) return 'text-gray-400'
  if (days < 30) return 'text-red-600 font-medium'
  if (days < 90) return 'text-yellow-600 font-medium'
  return 'text-gray-600'
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">

    <!-- Header -->
    <div class="flex items-start justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Hợp đồng dịch vụ</h1>
        <p class="text-sm text-slate-500 mt-1">Tổng <strong class="text-slate-700">{{ totalCount }}</strong> hợp đồng</p>
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
        <button class="btn-primary shrink-0" @click="router.push('/service-contracts/new')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Tạo mới
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
        <div class="flex flex-wrap gap-3 items-center">
          <div class="flex items-center gap-2">
            <label for="sc-type-filter" class="text-sm text-slate-600 shrink-0">Loại HĐ:</label>
            <select id="sc-type-filter" v-model="contractType" class="form-select text-sm" @change="() => { page = 1; load() }">
              <option value="">Tất cả loại</option>
              <option v-for="t in CONTRACT_TYPES" :key="t" :value="t">{{ CONTRACT_TYPE_LABEL[t] || t }}</option>
            </select>
          </div>
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

    <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm flex items-center justify-between">
      <span>⚠ {{ error }}</span>
      <button class="text-xs underline text-red-700 hover:text-red-900" @click="load">Thử lại</button>
    </div>

    <div class="card overflow-hidden">
      <!-- Info row -->
      <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span>Hiển thị <strong class="text-slate-700">{{ contracts.length }}</strong> / {{ totalCount }} hợp đồng</span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      <div v-if="loading" class="text-center text-slate-400 py-12">Đang tải...</div>
      <div v-else-if="contracts.length === 0 && !error" class="flex flex-col items-center justify-center py-16 text-slate-400">
        <p class="text-sm">Chưa có hợp đồng dịch vụ nào.</p>
        <button v-if="activeFilterCount > 0" class="text-xs text-blue-500 hover:text-blue-700 underline mt-2" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
      </div>
      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 border-b border-slate-200">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Mã HĐ</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Tên hợp đồng</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">NCC</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Loại</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Bắt đầu</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Hết hạn</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">SLA (giờ)</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="c in contracts" :key="c.name"
              class="hover:bg-slate-50 cursor-pointer transition-all hover:translate-x-0.5"
              @click="router.push(`/service-contracts/${c.name}`)"
            >
              <td class="px-4 py-3 font-mono text-xs text-slate-400">{{ c.name }}</td>
              <td class="px-4 py-3 font-medium text-slate-800">{{ c.contract_title }}</td>
              <td class="px-4 py-3">
                <div class="text-slate-700">{{ c.supplier_name || c.supplier || '—' }}</div>
                <div v-if="c.supplier && c.supplier_name" class="text-xs text-slate-400 font-mono">{{ c.supplier }}</div>
              </td>
              <td class="px-4 py-3">
                <button
                  :class="['text-xs px-2 py-1 rounded-full font-medium transition-all hover:ring-2 hover:ring-offset-1 hover:ring-current/50', TYPE_COLORS[c.contract_type] || 'bg-gray-100 text-gray-600']"
                  :title="`Lọc: ${CONTRACT_TYPE_LABEL[c.contract_type] || c.contract_type}`"
                  @click.stop="quickFilter(c.contract_type)"
                >{{ CONTRACT_TYPE_LABEL[c.contract_type] || c.contract_type }}</button>
              </td>
              <td class="px-4 py-3 text-slate-500">{{ formatDate(c.contract_start) }}</td>
              <td class="px-4 py-3" :class="expiryClass(c.contract_end)">{{ formatDate(c.contract_end) }}</td>
              <td class="px-4 py-3 text-slate-500">{{ c.sla_response_hours ?? '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="totalCount > PAGE_SIZE" class="flex items-center justify-between px-4 py-3 border-t border-slate-100 text-sm text-slate-500">
        <span>{{ (page - 1) * PAGE_SIZE + 1 }}–{{ Math.min(page * PAGE_SIZE, totalCount) }} / {{ totalCount }}</span>
        <div class="flex gap-2">
          <button @click="prevPage" :disabled="page === 1" class="px-3 py-1 rounded border border-slate-300 disabled:opacity-40 hover:bg-slate-50">‹</button>
          <button @click="nextPage" :disabled="page * PAGE_SIZE >= totalCount" class="px-3 py-1 rounded border border-slate-300 disabled:opacity-40 hover:bg-slate-50">›</button>
        </div>
      </div>
    </div>
  </div>
</template>
