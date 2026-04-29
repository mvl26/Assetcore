<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// Audit Trail viewer — UX layout aligned với /assets pattern.

import { ref, watch, onMounted, computed } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import { frappeGet } from '@/api/helpers'
import type { ImmAuditTrail, ChainVerifyResult } from '@/types/imm00'
import SmartSelect from '@/components/common/SmartSelect.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import { formatAssetDisplay, translateStatus, getStatusColor, formatDateTime, type AssetDisplay } from '@/utils/formatters'

// ─── Filters ────────────────────────────────────────────────────────────────
const showFilters = ref(false)
const filters = ref({
  asset: '',
  event_type: '',
  search: '',
  page: 1,
})
const PAGE_SIZE = 50

// ─── State ──────────────────────────────────────────────────────────────────
// `display` được tính 1 lần khi fetch — tránh gọi formatAssetDisplay 3×/row mỗi render.
type TrailRow = ImmAuditTrail & { asset?: string; asset_name?: string; display: AssetDisplay }
const trails = ref<TrailRow[]>([])
const loading = ref(false)
const totalCount = ref(0)

const verifying = ref(false)
const verifyResult = ref<ChainVerifyResult | null>(null)

// Detail modal
const selectedTrail = ref<TrailRow | null>(null)
function openDetail(t: TrailRow) { selectedTrail.value = t }
function closeDetail() { selectedTrail.value = null }

const BASE = '/api/method/assetcore.api.imm00'

// ─── Event-type config ──────────────────────────────────────────────────────
// Single source of truth — value/label/color đứng cùng nhau, tránh drift khi thêm event type mới.
const EVENT_TYPES: { value: string; label: string; color: string }[] = [
  { value: 'State Change',  label: 'Đổi trạng thái', color: 'bg-blue-100 text-blue-700' },
  { value: 'CAPA',          label: 'CAPA',           color: 'bg-orange-100 text-orange-700' },
  { value: 'Maintenance',   label: 'Bảo trì',        color: 'bg-yellow-100 text-yellow-700' },
  { value: 'Calibration',   label: 'Hiệu chuẩn',     color: 'bg-purple-100 text-purple-700' },
  { value: 'Document',      label: 'Hồ sơ',          color: 'bg-indigo-100 text-indigo-700' },
  { value: 'Incident',      label: 'Sự cố',          color: 'bg-red-100 text-red-700' },
  { value: 'Audit',         label: 'Kiểm toán',      color: 'bg-gray-100 text-gray-700' },
  { value: 'System',        label: 'Hệ thống',       color: 'bg-slate-100 text-slate-600' },
  { value: 'Transfer',      label: 'Luân chuyển',    color: 'bg-cyan-100 text-cyan-700' },
]
const EVENT_LABEL: Record<string, string> = Object.fromEntries(EVENT_TYPES.map(e => [e.value, e.label]))
const EVENT_COLORS: Record<string, string> = Object.fromEntries(EVENT_TYPES.map(e => [e.value, e.color]))

// ─── Active filter chips ────────────────────────────────────────────────────
interface FilterChip { key: 'asset' | 'event_type' | 'search'; label: string }
const activeChips = computed<FilterChip[]>(() => {
  const chips: FilterChip[] = []
  if (filters.value.asset) chips.push({ key: 'asset', label: `Thiết bị: ${filters.value.asset}` })
  if (filters.value.event_type) chips.push({ key: 'event_type', label: EVENT_LABEL[filters.value.event_type] || filters.value.event_type })
  if (filters.value.search.trim()) chips.push({ key: 'search', label: `"${filters.value.search.trim()}"` })
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)

// ─── Fetch ──────────────────────────────────────────────────────────────────
async function fetchTrails() {
  loading.value = true
  verifyResult.value = null
  try {
    const params: Record<string, string | number> = {
      page: filters.value.page,
      page_size: PAGE_SIZE,
    }
    if (filters.value.asset) params.asset = filters.value.asset
    if (filters.value.event_type) params.event_type = filters.value.event_type
    if (filters.value.search.trim()) params.q = filters.value.search.trim()

    const res = await frappeGet<{ items: ImmAuditTrail[]; pagination: { total: number } } | null>(
      `${BASE}.list_audit_trail`, params,
    )
    if (res) {
      const items = (res.items || []) as (ImmAuditTrail & { asset?: string; asset_name?: string })[]
      trails.value = items.map(t => ({ ...t, display: formatAssetDisplay(t.asset_name, t.asset) }))
      totalCount.value = res.pagination?.total || 0
    }
  } catch {
    trails.value = []; totalCount.value = 0
  } finally {
    loading.value = false
  }
}

const debouncedFetch = useDebounceFn(() => { filters.value.page = 1; fetchTrails() }, 300)
watch(() => filters.value.search, debouncedFetch)
watch(() => filters.value.asset, () => { filters.value.page = 1; fetchTrails() })
watch(() => filters.value.event_type, () => { filters.value.page = 1; fetchTrails() })

function applyFilters() { filters.value.page = 1; fetchTrails() }
function quickFilter(key: 'asset' | 'event_type', value: string) {
  if (!value || filters.value[key] === value) return
  filters.value[key] = value
  filters.value.page = 1
  showFilters.value = false
  fetchTrails()
}
function clearChip(key: FilterChip['key']) {
  filters.value[key] = ''
  applyFilters()
}
function resetFilters() {
  filters.value = { asset: '', event_type: '', search: '', page: 1 }
  fetchTrails()
}

async function verify() {
  if (!filters.value.asset) return
  verifying.value = true
  try {
    const res = await frappeGet<ChainVerifyResult | null>(`${BASE}.verify_chain`, { asset: filters.value.asset })
    if (res) verifyResult.value = res
  } finally { verifying.value = false }
}

function prevPage() { if (filters.value.page > 1) { filters.value.page--; fetchTrails() } }
function nextPage() { if (filters.value.page * PAGE_SIZE < totalCount.value) { filters.value.page++; fetchTrails() } }

onMounted(fetchTrails)
</script>

<template>
  <div class="page-container animate-fade-in">
    <!-- Header + filter toggle -->
    <div class="flex items-start justify-between mb-4">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Nhật ký kiểm toán</h1>
        <p class="text-sm text-slate-500 mt-1">
          Tổng <strong class="text-slate-700">{{ totalCount }}</strong> bản ghi
          <span class="text-slate-400"> · Lịch sử không thể sửa đổi (SHA-256)</span>
        </p>
      </div>
      <div class="flex items-center gap-2 shrink-0">
        <button
          class="relative flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg border transition-colors"
          :class="showFilters
            ? 'bg-brand-50 border-brand-300 text-brand-700'
            : 'bg-white border-slate-300 text-slate-600 hover:border-slate-400 hover:text-slate-800'"
          @click="showFilters = !showFilters"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3 4h18M7 8h10M11 12h2M9 16h6" />
          </svg>
          Bộ lọc
          <span
            v-if="activeFilterCount > 0"
            class="inline-flex items-center justify-center w-4 h-4 text-[10px] font-bold rounded-full"
            :class="showFilters ? 'bg-brand-600 text-white' : 'bg-blue-500 text-white'"
          >{{ activeFilterCount }}</span>
          <svg
            class="w-3.5 h-3.5 transition-transform duration-200"
            :class="showFilters ? 'rotate-180' : ''"
            fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        <button
          :disabled="verifying || !filters.asset"
          :title="!filters.asset ? 'Chọn 1 thiết bị để xác minh chuỗi' : ''"
          class="bg-purple-600 hover:bg-purple-700 disabled:opacity-40 text-white px-4 py-2 rounded-lg text-sm font-medium shrink-0"
          @click="verify"
        >
          {{ verifying ? 'Đang kiểm tra...' : '🔐 Xác minh chuỗi hash' }}
        </button>
      </div>
    </div>

    <!-- Active filter chips — luôn hiển thị khi có filter & panel đóng -->
    <Transition
      enter-active-class="transition-all duration-200 ease-out"
      enter-from-class="opacity-0 -translate-y-1"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition-all duration-150 ease-in"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 -translate-y-1"
    >
      <div v-if="activeChips.length > 0 && !showFilters" class="flex flex-wrap items-center gap-2 mb-4">
        <span class="text-xs text-slate-400 font-medium">Đang lọc:</span>
        <button
          v-for="chip in activeChips" :key="chip.key"
          class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 transition-colors"
          @click="clearChip(chip.key)"
        >
          {{ chip.label }}
          <svg class="w-3 h-3 opacity-60" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        <button class="text-xs text-slate-400 hover:text-red-500 underline underline-offset-2" @click="resetFilters">Xóa tất cả</button>
      </div>
    </Transition>

    <!-- Collapsible filter panel -->
    <Transition
      enter-active-class="transition-all duration-200 ease-out overflow-hidden"
      enter-from-class="opacity-0 max-h-0"
      enter-to-class="opacity-100 max-h-96"
      leave-active-class="transition-all duration-150 ease-in overflow-hidden"
      leave-from-class="opacity-100 max-h-96"
      leave-to-class="opacity-0 max-h-0"
    >
      <div v-show="showFilters" class="card mb-5 p-4">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
          <div>
            <p class="block text-xs font-medium text-slate-600 mb-1">Lọc theo thiết bị</p>
            <SmartSelect
              v-model="filters.asset"
              doctype="AC Asset"
              placeholder="Chọn thiết bị (để trống = tất cả)"
            />
          </div>
          <div>
            <p class="block text-xs font-medium text-slate-600 mb-1">Loại sự kiện</p>
            <select v-model="filters.event_type" class="form-select w-full text-sm">
              <option value="">Tất cả loại sự kiện</option>
              <option v-for="e in EVENT_TYPES" :key="e.value" :value="e.value">{{ e.label }}</option>
            </select>
          </div>
        </div>
        <div class="flex gap-2">
          <input
            v-model="filters.search"
            placeholder="Tìm theo người thực hiện, mã, nội dung thay đổi..."
            class="form-input flex-1 text-sm"
            @keyup.enter="applyFilters"
          />
          <button class="btn-primary text-sm" @click="applyFilters">Tìm</button>
          <button class="btn-ghost text-sm" @click="resetFilters">Đặt lại</button>
        </div>

        <!-- Chips trong panel -->
        <div v-if="activeChips.length > 0" class="flex flex-wrap items-center gap-2 mt-3 pt-3 border-t border-slate-100">
          <span class="text-xs text-slate-400 font-medium">Đang lọc:</span>
          <button
            v-for="chip in activeChips" :key="chip.key"
            class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 transition-colors"
            @click="clearChip(chip.key)"
          >
            {{ chip.label }}
            <svg class="w-3 h-3 opacity-60" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
          <button class="text-xs text-slate-400 hover:text-red-500 underline underline-offset-2" @click="resetFilters">Xóa tất cả</button>
        </div>
      </div>
    </Transition>

    <!-- Chain verify result -->
    <div
      v-if="verifyResult"
      :class="['rounded-xl border p-4 text-sm font-medium flex items-center gap-2 mb-4',
               verifyResult.valid ? 'bg-green-50 border-green-300 text-green-700' : 'bg-red-50 border-red-300 text-red-700']"
    >
      <span>{{ verifyResult.valid ? '✅ Chuỗi hash hợp lệ' : '❌ Chuỗi hash bị phá vỡ' }}</span>
      <span class="text-xs font-normal">({{ verifyResult.count }} bản ghi)</span>
      <span v-if="!verifyResult.valid && verifyResult.broken_at" class="text-xs ml-2">tại: {{ verifyResult.broken_at }}</span>
    </div>

    <!-- Table -->
    <div class="card overflow-hidden">
      <div class="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50/60">
        <span class="text-xs text-slate-500">
          <span v-if="activeFilterCount > 0">
            Kết quả lọc: <strong class="text-slate-700">{{ totalCount }}</strong> bản ghi
          </span>
          <span v-else>
            Hiển thị <strong class="text-slate-700">{{ trails.length }}</strong> / {{ totalCount }} bản ghi
          </span>
        </span>
        <button v-if="activeFilterCount > 0" class="text-xs text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      <div v-if="loading && !trails.length" class="p-6">
        <SkeletonLoader v-for="i in 5" :key="i" class="h-10 mb-3" />
      </div>
      <div v-else-if="trails.length === 0" class="flex flex-col items-center justify-center py-16 text-slate-400">
        <svg class="w-12 h-12 mb-3 opacity-40" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
        <p class="text-sm">Không có bản ghi audit nào phù hợp</p>
        <button v-if="activeFilterCount > 0" class="mt-3 text-xs text-blue-500 hover:text-blue-700 underline" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
      </div>
      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 border-b border-slate-200">
            <tr>
              <th class="px-4 py-3 text-left font-semibold text-slate-600">Thời gian</th>
              <th class="px-4 py-3 text-left font-semibold text-slate-600">Thiết bị</th>
              <th class="px-4 py-3 text-left font-semibold text-slate-600">Sự kiện</th>
              <th class="px-4 py-3 text-left font-semibold text-slate-600">Trạng thái</th>
              <th class="px-4 py-3 text-left font-semibold text-slate-600">Người thực hiện</th>
              <th class="px-4 py-3 text-left font-semibold text-slate-600">Tóm tắt</th>
              <th class="px-4 py-3 text-left font-semibold text-slate-600">Mã hash</th>
              <th class="px-4 py-3 text-right"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr
              v-for="t in trails" :key="t.name"
              class="hover:bg-slate-50 cursor-pointer transition-colors"
              @click="openDetail(t)"
            >
              <td class="px-4 py-3 text-slate-600 whitespace-nowrap">
                {{ formatDateTime(t.timestamp ?? t.event_timestamp) }}
              </td>
              <!-- Thiết bị (click để filter) -->
              <td class="px-4 py-3 max-w-[260px]">
                <template v-if="t.asset">
                  <button
                    class="font-medium text-slate-900 truncate text-left hover:text-blue-600 hover:underline decoration-dotted underline-offset-2"
                    :title="`Lọc: ${t.display.main}`"
                    @click.stop="quickFilter('asset', t.asset!)"
                  >{{ t.display.main }}</button>
                  <div
                    v-if="t.display.hasBoth"
                    class="text-[10px] leading-tight text-slate-400 font-mono truncate mt-0.5"
                    :title="t.display.sub"
                  >{{ t.display.sub }}</div>
                </template>
                <span v-else class="text-slate-400">—</span>
              </td>
              <!-- Sự kiện (click để filter) -->
              <td class="px-4 py-3">
                <button
                  :class="['text-xs px-2 py-1 rounded-full font-medium transition-all hover:ring-2 hover:ring-offset-1 hover:ring-current/50', EVENT_COLORS[t.event_type] || 'bg-gray-100 text-gray-600']"
                  :title="`Lọc: ${EVENT_LABEL[t.event_type] || t.event_type}`"
                  @click.stop="quickFilter('event_type', t.event_type)"
                >{{ EVENT_LABEL[t.event_type] || t.event_type }}</button>
              </td>
              <td class="px-4 py-3 text-xs">
                <div v-if="t.from_status || t.to_status" class="flex items-center gap-1.5">
                  <span v-if="t.from_status" :class="['inline-block px-1.5 py-0.5 rounded font-medium', getStatusColor(t.from_status)]">
                    {{ translateStatus(t.from_status) }}
                  </span>
                  <span v-else class="text-slate-400">—</span>
                  <svg class="w-3 h-3 text-slate-400 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M17 8l4 4m0 0l-4 4m4-4H3" />
                  </svg>
                  <span v-if="t.to_status" :class="['inline-block px-1.5 py-0.5 rounded font-medium', getStatusColor(t.to_status)]">
                    {{ translateStatus(t.to_status) }}
                  </span>
                  <span v-else class="text-slate-400">—</span>
                </div>
                <span v-else class="text-slate-400">—</span>
              </td>
              <td class="px-4 py-3 text-slate-600">{{ t.actor || '—' }}</td>
              <td class="px-4 py-3 text-slate-500 max-w-xs truncate" :title="t.change_summary">{{ t.change_summary || '—' }}</td>
              <td class="px-4 py-3 font-mono text-xs text-slate-400">{{ t.hash ? t.hash.slice(0, 10) + '…' : '—' }}</td>
              <td class="px-4 py-3 text-right">
                <button class="text-xs text-blue-600 hover:text-blue-800 font-medium whitespace-nowrap" @click.stop="openDetail(t)">
                  Xem chi tiết →
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div v-if="totalCount > PAGE_SIZE" class="flex items-center justify-between px-4 py-3 border-t border-slate-100 text-sm text-slate-500">
        <span>{{ (filters.page - 1) * PAGE_SIZE + 1 }}–{{ Math.min(filters.page * PAGE_SIZE, totalCount) }} / {{ totalCount }}</span>
        <div class="flex gap-2">
          <button :disabled="filters.page === 1" class="px-3 py-1 rounded border border-slate-300 disabled:opacity-40 hover:bg-slate-50" @click="prevPage">‹ Trước</button>
          <button :disabled="filters.page * PAGE_SIZE >= totalCount" class="px-3 py-1 rounded border border-slate-300 disabled:opacity-40 hover:bg-slate-50" @click="nextPage">Sau ›</button>
        </div>
      </div>
    </div>

    <!-- Detail modal — giữ nguyên -->
    <div
      v-if="selectedTrail"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      @click.self="closeDetail"
    >
      <div class="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        <div class="flex items-center justify-between px-5 py-4 border-b border-gray-200">
          <div>
            <h2 class="text-base font-semibold text-gray-800">Chi tiết bản ghi kiểm toán</h2>
            <p class="text-xs text-slate-500 font-mono mt-0.5">{{ selectedTrail.name }}</p>
          </div>
          <button class="p-1.5 text-slate-400 hover:text-slate-700 rounded hover:bg-gray-100" title="Đóng" @click="closeDetail">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="px-5 py-4 overflow-y-auto space-y-4 text-sm">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <p class="text-xs font-medium text-slate-500 mb-1">Thời gian</p>
              <p class="text-gray-800">{{ formatDateTime(selectedTrail.timestamp ?? selectedTrail.event_timestamp) }}</p>
            </div>
            <div>
              <p class="text-xs font-medium text-slate-500 mb-1">Người thực hiện</p>
              <p class="text-gray-800">{{ selectedTrail.actor || '—' }}</p>
            </div>
            <div>
              <p class="text-xs font-medium text-slate-500 mb-1">Loại sự kiện</p>
              <span :class="['inline-block text-xs px-2 py-1 rounded-full font-medium', EVENT_COLORS[selectedTrail.event_type] || 'bg-gray-100 text-gray-600']">
                {{ EVENT_LABEL[selectedTrail.event_type] || selectedTrail.event_type }}
              </span>
            </div>
            <div class="min-w-0">
              <p class="text-xs font-medium text-slate-500 mb-1">Thiết bị</p>
              <template v-if="selectedTrail.asset">
                <p class="text-gray-800 font-medium truncate" :title="selectedTrail.display.main">
                  {{ selectedTrail.display.main }}
                </p>
                <p
                  v-if="selectedTrail.display.hasBoth"
                  class="text-[11px] text-gray-400 font-mono truncate mt-0.5"
                  :title="selectedTrail.display.sub"
                >{{ selectedTrail.display.sub }}</p>
              </template>
              <p v-else class="text-gray-400">—</p>
            </div>
          </div>

          <div v-if="selectedTrail.from_status || selectedTrail.to_status">
            <p class="text-xs font-medium text-slate-500 mb-1">Chuyển trạng thái</p>
            <div class="flex items-center gap-2">
              <span v-if="selectedTrail.from_status" :class="['inline-block px-2 py-0.5 rounded text-xs font-medium', getStatusColor(selectedTrail.from_status)]">
                {{ translateStatus(selectedTrail.from_status) }}
              </span>
              <span v-else class="text-gray-400 text-xs">(không có)</span>
              <svg class="w-4 h-4 text-gray-400 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M17 8l4 4m0 0l-4 4m4-4H3" />
              </svg>
              <span v-if="selectedTrail.to_status" :class="['inline-block px-2 py-0.5 rounded text-xs font-medium', getStatusColor(selectedTrail.to_status)]">
                {{ translateStatus(selectedTrail.to_status) }}
              </span>
              <span v-else class="text-gray-400 text-xs">(không có)</span>
            </div>
          </div>

          <div>
            <p class="text-xs font-medium text-slate-500 mb-1">Tóm tắt thay đổi</p>
            <p class="text-gray-800 whitespace-pre-wrap bg-gray-50 border border-gray-200 rounded-lg p-3">
              {{ selectedTrail.change_summary || '(không có nội dung)' }}
            </p>
          </div>

          <div v-if="selectedTrail.ref_doctype || selectedTrail.ref_name">
            <p class="text-xs font-medium text-slate-500 mb-1">Bản ghi tham chiếu</p>
            <p class="text-gray-800 font-mono text-xs">
              {{ selectedTrail.ref_doctype }}<span v-if="selectedTrail.ref_name"> / {{ selectedTrail.ref_name }}</span>
            </p>
          </div>

          <div v-if="selectedTrail.hash">
            <p class="text-xs font-medium text-slate-500 mb-1">Mã hash (SHA-256)</p>
            <p class="font-mono text-xs text-gray-700 bg-gray-50 border border-gray-200 rounded-lg p-2 break-all">
              {{ selectedTrail.hash }}
            </p>
          </div>
        </div>

        <div class="flex justify-end px-5 py-3 border-t border-gray-200 bg-gray-50">
          <button class="px-4 py-1.5 rounded-lg text-sm font-medium bg-gray-200 hover:bg-gray-300 text-gray-700" @click="closeDetail">Đóng</button>
        </div>
      </div>
    </div>
  </div>
</template>
