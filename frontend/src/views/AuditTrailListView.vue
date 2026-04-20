<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// Audit Trail viewer — UX-first: load default, debounce filter, verify chain on-demand.

import { ref, watch, onMounted } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import { frappeGet } from '@/api/helpers'
import type { ImmAuditTrail, ChainVerifyResult } from '@/types/imm00'
import SmartSelect from '@/components/common/SmartSelect.vue'

// ─── State ──────────────────────────────────────────────────────────────────
const assetFilter = ref('')         // ID tài sản (từ SmartSelect) — optional
const searchQuery = ref('')         // Free-text search
const trails = ref<(ImmAuditTrail & { asset?: string })[]>([])
const loading = ref(false)
const page = ref(1)
const totalCount = ref(0)
const PAGE_SIZE = 50

const verifying = ref(false)
const verifyResult = ref<ChainVerifyResult | null>(null)

const BASE = '/api/method/assetcore.api.imm00'

// ─── Fetch ──────────────────────────────────────────────────────────────────
async function fetchTrails() {
  loading.value = true
  verifyResult.value = null
  try {
    const params: Record<string, string | number> = {
      page: page.value,
      page_size: PAGE_SIZE,
    }
    if (assetFilter.value) params.asset = assetFilter.value
    if (searchQuery.value.trim()) params.q = searchQuery.value.trim()

    const res = await frappeGet<{ items: ImmAuditTrail[]; pagination: { total: number } } | null>(
      `${BASE}.list_audit_trail`, params,
    )
    if (res) {
      trails.value = res.items || []
      totalCount.value = res.pagination?.total || 0
    }
  } catch {
    trails.value = []; totalCount.value = 0
  } finally {
    loading.value = false
  }
}

// Debounced search — gọi sau 300ms user ngừng gõ
const debouncedFetch = useDebounceFn(() => { page.value = 1; fetchTrails() }, 300)

// Watch cả 2 filter — mỗi thay đổi reset page về 1
watch(searchQuery, debouncedFetch)
watch(assetFilter, () => { page.value = 1; fetchTrails() })

// ─── Verify chain (chỉ khả dụng khi chọn 1 asset cụ thể) ─────────────────────
async function verify() {
  if (!assetFilter.value) return
  verifying.value = true
  try {
    const res = await frappeGet<ChainVerifyResult | null>(
      `${BASE}.verify_chain`, { asset: assetFilter.value },
    )
    if (res) verifyResult.value = res
  } finally {
    verifying.value = false
  }
}

// ─── Pagination ─────────────────────────────────────────────────────────────
function prevPage() { if (page.value > 1) { page.value--; fetchTrails() } }
function nextPage() { if (page.value * PAGE_SIZE < totalCount.value) { page.value++; fetchTrails() } }

// ─── Helpers ────────────────────────────────────────────────────────────────
function formatDt(d?: string) {
  if (!d) return '—'
  return new Date(d).toLocaleString('vi-VN')
}

function clearFilters() {
  assetFilter.value = ''
  searchQuery.value = ''
  page.value = 1
  fetchTrails()
}

const EVENT_COLORS: Record<string, string> = {
  'State Change': 'bg-blue-100 text-blue-700',
  'CAPA': 'bg-orange-100 text-orange-700',
  'Maintenance': 'bg-yellow-100 text-yellow-700',
  'Calibration': 'bg-purple-100 text-purple-700',
  'Document': 'bg-indigo-100 text-indigo-700',
  'Incident': 'bg-red-100 text-red-700',
  'Audit': 'bg-gray-100 text-gray-700',
  'System': 'bg-slate-100 text-slate-600',
  'Transfer': 'bg-cyan-100 text-cyan-700',
}

const EVENT_LABEL: Record<string, string> = {
  'State Change': 'Đổi trạng thái',
  'CAPA': 'CAPA',
  'Maintenance': 'Bảo trì',
  'Calibration': 'Hiệu chuẩn',
  'Document': 'Hồ sơ',
  'Incident': 'Sự cố',
  'Audit': 'Audit',
  'System': 'Hệ thống',
  'Transfer': 'Luân chuyển',
}

// Init: load 50 bản ghi mới nhất toàn hệ thống
onMounted(fetchTrails)
</script>

<template>
  <div class="p-6 space-y-5">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold text-gray-800">Audit Trail</h1>
        <p class="text-xs text-slate-500 mt-0.5">
          Lịch sử sự kiện không thể sửa đổi (SHA-256 hash chain)
        </p>
      </div>
      <span class="text-sm text-slate-500">{{ totalCount }} bản ghi</span>
    </div>

    <!-- Filters: Asset picker + Smart search + Verify -->
    <div class="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
        <!-- Asset filter (SmartSelect — click để chọn, không cần gõ mã) -->
        <div>
          <label for="audit-asset-filter" class="block text-xs font-medium text-slate-600 mb-1">
            Lọc theo thiết bị
          </label>
          <SmartSelect
            id="audit-asset-filter"
            v-model="assetFilter"
            doctype="AC Asset"
            placeholder="Chọn thiết bị (để trống = xem tất cả)"
          />
        </div>

        <!-- Free-text search — debounced -->
        <div class="md:col-span-2">
          <label for="audit-search-input" class="block text-xs font-medium text-slate-600 mb-1">
            Tìm kiếm nhanh
            <span class="text-slate-400 font-normal">(actor, mã, nội dung thay đổi)</span>
          </label>
          <div class="relative">
            <input
              id="audit-search-input"
              v-model="searchQuery"
              type="text"
              placeholder="Gõ để lọc ngay lập tức..."
              class="w-full border border-gray-300 rounded-lg pl-9 pr-8 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
            <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400"
                 fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <button
              v-if="searchQuery"
              class="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600"
              title="Xóa tìm kiếm"
              @click="searchQuery = ''"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      <!-- Action row -->
      <div class="flex items-center gap-2 flex-wrap">
        <button
          v-if="assetFilter || searchQuery"
          class="text-xs text-slate-500 hover:text-slate-700 underline"
          @click="clearFilters"
        >Xóa bộ lọc</button>
        <div class="flex-1"></div>
        <button
          :disabled="verifying || !assetFilter"
          :title="!assetFilter ? 'Chọn 1 thiết bị để verify chain' : ''"
          class="bg-purple-600 hover:bg-purple-700 disabled:opacity-40 text-white px-4 py-1.5 rounded-lg text-sm font-medium"
          @click="verify"
        >{{ verifying ? 'Đang kiểm tra...' : '🔐 Verify Chain' }}</button>
      </div>
    </div>

    <!-- Chain result -->
    <div v-if="verifyResult" :class="['rounded-xl border p-4 text-sm font-medium flex items-center gap-2',
      verifyResult.valid ? 'bg-green-50 border-green-300 text-green-700' : 'bg-red-50 border-red-300 text-red-700']">
      <span>{{ verifyResult.valid ? '✅ Hash chain hợp lệ' : '❌ Hash chain bị phá vỡ' }}</span>
      <span class="text-xs font-normal">({{ verifyResult.count }} records)</span>
      <span v-if="!verifyResult.valid && verifyResult.broken_at" class="text-xs ml-2">
        tại: {{ verifyResult.broken_at }}
      </span>
    </div>

    <!-- Table -->
    <div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div v-if="loading && !trails.length" class="text-center text-gray-400 py-12">Đang tải...</div>
      <div v-else-if="trails.length === 0" class="text-center text-gray-400 py-12 text-sm">
        Không có bản ghi audit nào.
      </div>
      <div v-else class="overflow-x-auto"><table class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-200">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Thời gian</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Thiết bị</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Sự kiện</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Trạng thái</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Actor</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Tóm tắt</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500">Hash</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="t in trails" :key="t.name" class="hover:bg-gray-50">
            <td class="px-4 py-3 text-gray-600 whitespace-nowrap">{{ formatDt(t.timestamp ?? t.event_timestamp) }}</td>
            <td class="px-4 py-3 font-mono text-xs text-slate-500">{{ t.asset || '—' }}</td>
            <td class="px-4 py-3">
              <span :class="['text-xs px-2 py-1 rounded-full font-medium', EVENT_COLORS[t.event_type] || 'bg-gray-100 text-gray-600']">
                {{ EVENT_LABEL[t.event_type] || t.event_type }}
              </span>
            </td>
            <td class="px-4 py-3 text-gray-500 text-xs">
              <span v-if="t.from_status || t.to_status">{{ t.from_status || '—' }} → {{ t.to_status || '—' }}</span>
              <span v-else>—</span>
            </td>
            <td class="px-4 py-3 text-gray-600">{{ t.actor }}</td>
            <td class="px-4 py-3 text-gray-500 max-w-xs truncate" :title="t.change_summary">{{ t.change_summary }}</td>
            <td class="px-4 py-3 font-mono text-xs text-gray-400">{{ t.hash ? t.hash.slice(0, 10) + '…' : '—' }}</td>
          </tr>
        </tbody>
      </table>
      </div>

      <!-- Pagination -->
      <div v-if="totalCount > PAGE_SIZE" class="flex items-center justify-between px-4 py-3 border-t border-gray-100 text-sm text-gray-500">
        <span>{{ (page - 1) * PAGE_SIZE + 1 }}–{{ Math.min(page * PAGE_SIZE, totalCount) }} / {{ totalCount }}</span>
        <div class="flex gap-2">
          <button :disabled="page === 1"
                  class="px-3 py-1 rounded border border-gray-300 disabled:opacity-40 hover:bg-gray-50"
                  @click="prevPage">‹</button>
          <button :disabled="page * PAGE_SIZE >= totalCount"
                  class="px-3 py-1 rounded border border-gray-300 disabled:opacity-40 hover:bg-gray-50"
                  @click="nextPage">›</button>
        </div>
      </div>
    </div>
  </div>
</template>
