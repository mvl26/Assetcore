<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { frappeGet, frappePost } from '@/api/helpers'
import type { AssetTransfer } from '@/types/imm00'
import { formatAssetDisplay, translateStatus, getStatusColor, formatDate } from '@/utils/formatters'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const router = useRouter()
const route = useRoute()

const transfers = ref<AssetTransfer[]>([])
const loading = ref(false)
const page = ref(1)
const totalCount = ref(0)
const PAGE_SIZE = 30
const error = ref('')
const assetFilter = ref<string>((route.query.asset as string) || '')
const typeFilter = ref('')
const statusFilter = ref('')
const showFilters = ref(false)

const BASE = '/api/method/assetcore.api.imm00'

const TRANSFER_TYPES = [
  { value: 'Internal', label: 'Nội bộ' },
  { value: 'Loan',     label: 'Cho mượn' },
  { value: 'External', label: 'Bên ngoài' },
  { value: 'Return',   label: 'Hoàn trả' },
]

const TRANSFER_STATUSES = [
  { value: 'Pending Approval', label: 'Chờ phê duyệt' },
  { value: 'Approved',         label: 'Đã phê duyệt' },
  { value: 'Rejected',         label: 'Từ chối' },
  { value: 'Received',         label: 'Đã nhận' },
  { value: 'Cancelled',        label: 'Đã hủy' },
]

const TYPE_COLORS: Record<string, string> = {
  Internal: 'bg-blue-100 text-blue-700',
  Loan:     'bg-yellow-100 text-yellow-700',
  External: 'bg-purple-100 text-purple-700',
  Return:   'bg-green-100 text-green-700',
}

const TYPE_LABELS: Record<string, string> = {
  Internal: 'Nội bộ',
  Loan:     'Cho mượn',
  External: 'Bên ngoài',
  Return:   'Hoàn trả',
}

interface Chip { key: 'type' | 'status' | 'asset'; label: string }
const activeChips = computed<Chip[]>(() => {
  const chips: Chip[] = []
  if (typeFilter.value) {
    const t = TRANSFER_TYPES.find(x => x.value === typeFilter.value)
    chips.push({ key: 'type', label: t?.label ?? typeFilter.value })
  }
  if (statusFilter.value) {
    const s = TRANSFER_STATUSES.find(x => x.value === statusFilter.value)
    chips.push({ key: 'status', label: s?.label ?? statusFilter.value })
  }
  if (assetFilter.value) chips.push({ key: 'asset', label: `Thiết bị: ${assetFilter.value}` })
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)

function clearChip(key: string) {
  if (key === 'type') typeFilter.value = ''
  else if (key === 'status') statusFilter.value = ''
  else assetFilter.value = ''
  page.value = 1
  load()
}

function resetFilters() {
  typeFilter.value = ''
  statusFilter.value = ''
  assetFilter.value = ''
  page.value = 1
  load()
}

function quickFilter(key: 'type' | 'status', value: string) {
  if (!value) return
  if (key === 'type') typeFilter.value = value
  else statusFilter.value = value
  showFilters.value = false
  page.value = 1
  load()
}

async function load() {
  loading.value = true
  const params: Record<string, unknown> = { page: page.value, page_size: PAGE_SIZE }
  if (assetFilter.value) params.asset = assetFilter.value
  if (typeFilter.value) params.transfer_type = typeFilter.value
  if (statusFilter.value) params.status = statusFilter.value
  const res = await frappeGet<{ items: AssetTransfer[]; pagination: { total: number } } | null>(
    `${BASE}.list_transfers`, params,
  )
  loading.value = false
  if (res) {
    transfers.value = res.items || []
    totalCount.value = res.pagination?.total || 0
  }
}

function prevPage() { if (page.value > 1) { page.value--; load() } }
function nextPage() { if (page.value * PAGE_SIZE < totalCount.value) { page.value++; load() } }

async function remove(name: string) {
  if (!confirm(`Xóa chuyển giao ${name}?\n\nThao tác sẽ cancel nếu đã submit.`)) return
  try {
    await frappePost<void>(`${BASE}.delete_transfer`, { name })
    await load()
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Xóa thất bại'
  }
}

watch(() => route.query.asset, (val) => {
  assetFilter.value = (val as string) || ''
  page.value = 1
  load()
})

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <PageHeader title="Chuyển giao thiết bị" :subtitle="`Tổng ${totalCount} lượt chuyển`">
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
        <button class="btn-primary shrink-0" @click="router.push('/asset-transfers/new')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Tạo mới
        </button>
      </template>
    </PageHeader>

    <ListFilterBar
      :show="showFilters"
      :chips="activeChips"
      :show-search="false"
      @reset="resetFilters"
      @clear-chip="clearChip"
      @apply="() => { page = 1; load() }"
    >
      <template #fields>
        <div class="form-group">
          <label for="at-type-filter" class="form-label">Loại</label>
          <select id="at-type-filter" v-model="typeFilter" class="form-select text-sm" @change="() => { page = 1; load() }">
            <option value="">Tất cả loại</option>
            <option v-for="t in TRANSFER_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
          </select>
        </div>
        <div class="form-group">
          <label for="at-status-filter" class="form-label">Trạng thái</label>
          <select id="at-status-filter" v-model="statusFilter" class="form-select text-sm" @change="() => { page = 1; load() }">
            <option value="">Tất cả</option>
            <option v-for="s in TRANSFER_STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>
        <div class="form-group">
          <label for="at-asset-filter" class="form-label">Thiết bị</label>
          <input id="at-asset-filter" v-model="assetFilter" placeholder="Mã AC Asset..." class="form-input text-sm" @keyup.enter="() => { page = 1; load() }" />
        </div>
      </template>
    </ListFilterBar>

    <div v-if="error" class="bg-red-50 border border-red-300 text-red-700 px-3 py-2 rounded-lg text-sm">{{ error }}</div>

    <div class="card overflow-hidden">
      <!-- Info row -->
      <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span>Hiển thị <strong class="text-slate-700">{{ transfers.length }}</strong> / {{ totalCount }} lượt chuyển</span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      <div v-if="loading" class="text-center text-slate-400 py-12">Đang tải...</div>
      <div v-else-if="transfers.length === 0" class="flex flex-col items-center justify-center py-16 text-slate-400">
        <p class="text-sm">Không có dữ liệu chuyển giao.</p>
        <button v-if="activeFilterCount > 0" class="text-xs text-blue-500 hover:text-blue-700 underline mt-2" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
      </div>
      <template v-else>
        <!-- Mobile cards (< sm) -->
        <div class="mobile-card-list sm:hidden">
          <div
            v-for="t in transfers"
            :key="t.name"
            class="mobile-card"
            @click="router.push(`/asset-transfers/${t.name}`)"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="font-mono text-sm font-semibold text-brand-700">{{ t.name }}</span>
              <button
                :class="['px-2.5 py-0.5 rounded-full text-xs font-medium', getStatusColor(t.status)]"
                @click.stop="quickFilter('status', t.status ?? '')"
              >{{ translateStatus(t.status) }}</button>
            </div>
            <p class="text-sm font-medium text-slate-900 truncate">{{ formatAssetDisplay(t.asset_name, t.asset).main }}</p>
            <div class="flex flex-wrap items-center gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
              <button
                :class="['px-1.5 py-0.5 rounded-full text-[11px] font-medium', TYPE_COLORS[t.transfer_type] || 'bg-slate-100 text-slate-600']"
                @click.stop="quickFilter('type', t.transfer_type)"
              >{{ TYPE_LABELS[t.transfer_type] || t.transfer_type }}</button>
              <span class="text-slate-300">·</span>
              <span>{{ formatDate(t.transfer_date) }}</span>
              <span v-if="t.to_location" class="text-slate-300">·</span>
              <span v-if="t.to_location">→ {{ t.to_location }}</span>
            </div>
          </div>
          <div v-if="transfers.length === 0" class="py-12 text-center text-slate-400">
            <p class="text-sm font-medium">Không có dữ liệu</p>
          </div>
        </div>

        <!-- Desktop table (sm+) -->
        <div class="hidden sm:block overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="bg-slate-50 border-b border-slate-200">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Mã phiếu</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Ngày</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Thiết bị</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Loại</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Trạng thái</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Từ</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Đến</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Lý do</th>
                <th class="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr
                v-for="t in transfers" :key="t.name"
                class="hover:bg-slate-50 cursor-pointer transition-all hover:translate-x-0.5"
                @click="router.push(`/asset-transfers/${t.name}`)"
              >
                <td class="px-4 py-3 font-mono text-xs text-slate-400">{{ t.name }}</td>
                <td class="px-4 py-3 text-slate-600 whitespace-nowrap">{{ formatDate(t.transfer_date) }}</td>
                <td class="px-4 py-3">
                  <div class="font-medium text-slate-900 truncate max-w-[220px]">
                    {{ formatAssetDisplay(t.asset_name, t.asset).main }}
                  </div>
                  <div
                    v-if="formatAssetDisplay(t.asset_name, t.asset).hasBoth"
                    class="text-xs text-slate-400 font-mono">
                    {{ formatAssetDisplay(t.asset_name, t.asset).sub }}
                  </div>
                </td>
                <td class="px-4 py-3">
                  <button
                    :class="['text-xs px-2 py-1 rounded-full font-medium transition-all hover:ring-2 hover:ring-offset-1 hover:ring-current/50', TYPE_COLORS[t.transfer_type] || 'bg-slate-100 text-slate-600']"
                    :title="`Lọc: ${TYPE_LABELS[t.transfer_type] || t.transfer_type}`"
                    @click.stop="quickFilter('type', t.transfer_type)"
                  >{{ TYPE_LABELS[t.transfer_type] || t.transfer_type }}</button>
                </td>
                <td class="px-4 py-3">
                  <button
                    :class="['inline-block px-2 py-0.5 rounded-full text-xs font-medium transition-all hover:ring-2 hover:ring-offset-1 hover:ring-current/50', getStatusColor(t.status)]"
                    :title="`Lọc: ${translateStatus(t.status)}`"
                    @click.stop="quickFilter('status', t.status ?? '')"
                  >{{ translateStatus(t.status) }}</button>
                </td>
                <td class="px-4 py-3 text-slate-500 text-xs">{{ t.from_location || '—' }}</td>
                <td class="px-4 py-3 text-slate-500 text-xs">{{ t.to_location }}</td>
                <td class="px-4 py-3 text-slate-500 max-w-xs truncate">{{ t.reason }}</td>
                <td class="px-4 py-3 text-right" @click.stop>
                  <button class="text-xs text-red-600 hover:text-red-800" @click="remove(t.name)">Xóa</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>

      <div v-if="totalCount > PAGE_SIZE" class="flex items-center justify-between px-4 py-3 border-t border-slate-100 text-sm text-slate-500">
        <span>{{ (page - 1) * PAGE_SIZE + 1 }}–{{ Math.min(page * PAGE_SIZE, totalCount) }} / {{ totalCount }}</span>
        <div class="flex gap-2">
          <button :disabled="page === 1" class="px-3 py-1 rounded border border-slate-300 disabled:opacity-40 hover:bg-slate-50" @click="prevPage">‹</button>
          <button :disabled="page * PAGE_SIZE >= totalCount" class="px-3 py-1 rounded border border-slate-300 disabled:opacity-40 hover:bg-slate-50" @click="nextPage">›</button>
        </div>
      </div>
    </div>
  </div>
</template>
