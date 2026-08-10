<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useCapabilities } from '@/composables/useCapabilities'
import { listPurchases } from '@/api/purchase'
import type { Purchase } from '@/api/purchase'
import SmartSelect from '@/components/common/SmartSelect.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import ListPageShell from '@/components/ui/ListPageShell.vue'

const router = useRouter()
const { can } = useCapabilities()

const rows = ref<Purchase[]>([])
const total = ref(0)
const loading = ref(false)
// AC-UX-041 — trước đây `load()` KHÔNG có `catch`: API 500 để rows=[] ⇒ màn in
// «Chưa có đơn hàng nào» (lỗi giả dạng rỗng). Nay lỗi có trạng thái riêng.
const errorMessage = ref<string | null>(null)
const page = ref(1)
const PAGE_SIZE = 30
const showFilters = ref(false)

const statusFilter = ref('')
const supplierFilter = ref('')
const supplierName = ref('')

const STATUSES = [
  { value: 'Draft',     label: 'Nháp' },
  { value: 'Submitted', label: 'Đã duyệt' },
  { value: 'Received',  label: 'Đã nhận hàng' },
  { value: 'Cancelled', label: 'Đã huỷ' },
]

const STATUS_CLASS: Record<string, string> = {
  Draft:     'bg-slate-100 text-slate-600',
  Submitted: 'bg-blue-50 text-blue-700',
  Received:  'bg-emerald-50 text-emerald-700',
  Cancelled: 'bg-red-50 text-red-700',
}

interface Chip { key: 'status' | 'supplier'; label: string }
const activeChips = computed<Chip[]>(() => {
  const chips: Chip[] = []
  if (statusFilter.value) {
    const s = STATUSES.find(x => x.value === statusFilter.value)
    chips.push({ key: 'status', label: s?.label ?? statusFilter.value })
  }
  if (supplierFilter.value) chips.push({ key: 'supplier', label: `Nhà cung cấp: ${supplierName.value || supplierFilter.value}` })
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)

function clearChip(key: string) {
  if (key === 'status') statusFilter.value = ''
  else { supplierFilter.value = ''; supplierName.value = '' }
  page.value = 1; load()
}

function resetFilters() {
  statusFilter.value = ''
  supplierFilter.value = ''
  supplierName.value = ''
  page.value = 1; load()
}

function onSupplierSelect(item: unknown) {
  supplierName.value = (item as { label: string }).label
  page.value = 1; load()
}
function onSupplierClear() { supplierName.value = ''; page.value = 1; load() }

function quickFilter(value: string) {
  if (!value) return
  statusFilter.value = value
  showFilters.value = false
  page.value = 1; load()
}

async function load() {
  loading.value = true
  errorMessage.value = null          // INV-UX3-4 — xoá lỗi ĐẦU lượt nạp
  try {
    const res = await listPurchases({
      page: page.value,
      page_size: PAGE_SIZE,
      status: statusFilter.value || undefined,
      supplier: supplierFilter.value || undefined,
    })
    rows.value = res.data
    total.value = res.total
  } catch (e: unknown) {
    errorMessage.value = e instanceof Error ? e.message : String(e)
    rows.value = []                  // INV-UX3-5 — không giữ số cũ dưới dải lỗi
    total.value = 0
  } finally {
    loading.value = false            // INV-UX3-3 — luôn hạ cờ
  }
}

function vnd(v?: number) {
  if (!v) return '—'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(v)
}
function formatDate(d?: string) { return d ? new Date(d).toLocaleDateString('vi-VN') : '—' }

onMounted(load)
</script>

<template>
  <!--
    AC-UX-041 — khuôn 4 trạng thái loại trừ (ui/ListPageShell). Chữ rỗng là literal
    TĨNH ngay trên thẻ shell (không đưa vào computed — bộ dò ui-audit-inventory soi
    cụm rỗng + từ hướng dẫn trong cửa sổ ±12 dòng của template).
  -->
  <ListPageShell
    :loading="loading"
    :error-message="errorMessage"
    :is-empty="!rows.length"
    empty-title="Chưa có đơn hàng nào"
    empty-hint="Hãy tạo đơn hàng mới hoặc xoá bộ lọc để xem tất cả."
    @retry="load"
  >
    <template #header>
      <PageHeader
        title="Đơn mua hàng"
        :subtitle="`Tổng ${total} đơn hàng`"
      >
        <template #actions>
          <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
          <button v-if="can('purchase.create')" class="btn-primary shrink-0" @click="router.push('/purchases/new')">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            Tạo đơn hàng
          </button>
        </template>
      </PageHeader>
    </template>

    <template #filters>
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
            <label class="form-label" for="po-filter-status">Trạng thái</label>
            <select id="po-filter-status" v-model="statusFilter" class="form-select text-sm" @change="() => { page = 1; load() }">
              <option value="">Tất cả</option>
              <option v-for="s in STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Nhà cung cấp</label>
            <SmartSelect
              v-model="supplierFilter" doctype="AC Supplier" placeholder="Tất cả nhà cung cấp..."
              @select="onSupplierSelect"
              @clear="onSupplierClear"
            />
          </div>
        </template>
      </ListFilterBar>
    </template>

    <template #skeleton>
      <SkeletonLoader variant="table" :rows="6" />
    </template>

    <template #empty-action>
      <button v-if="activeFilterCount > 0" class="btn-ghost text-sm" @click="resetFilters">
        Xóa bộ lọc để xem tất cả
      </button>
    </template>

    <template #toolbar>
      <!-- Info row -->
      <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span>Hiển thị <strong class="text-slate-700">{{ rows.length }}</strong> / {{ total }} đơn hàng</span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>
    </template>

    <!-- Mobile cards -->
        <div class="mobile-card-list sm:hidden">
          <div
            v-for="r in rows"
            :key="r.name"
            class="mobile-card"
            @click="router.push(`/purchases/${r.name}`)"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="font-mono text-sm font-semibold text-brand-700">{{ r.name }}</span>
              <span
                class="text-xs px-2 py-0.5 rounded-full font-medium"
                :class="STATUS_CLASS[r.status] || 'bg-slate-100 text-slate-600'"
              >{{ STATUSES.find(s => s.value === r.status)?.label || r.status }}</span>
            </div>
            <p class="text-sm font-medium text-slate-900 truncate">{{ r.supplier_name || r.supplier }}</p>
            <div class="flex flex-wrap gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
              <span>{{ formatDate(r.purchase_date) }}</span>
              <span>· {{ vnd(r.total_value) }}</span>
            </div>
          </div>
        </div>

        <!-- Desktop table -->
        <table class="hidden sm:table w-full text-sm">
        <thead class="bg-slate-50 border-b border-slate-200">
          <tr class="text-xs text-slate-500 font-medium">
            <th class="px-4 py-3 text-left">Mã đơn</th>
            <th class="px-4 py-3 text-left">Ngày đặt</th>
            <th class="px-4 py-3 text-left">Nhà cung cấp</th>
            <th class="px-4 py-3 text-left">Số hóa đơn</th>
            <th class="px-4 py-3 text-center">Phân loại</th>
            <th class="px-4 py-3 text-right">Tổng giá trị</th>
            <th class="px-4 py-3 text-center">Trạng thái</th>
          </tr>
        </thead>
        <tbody>
          <tr
v-for="r in rows" :key="r.name"
            class="border-b border-slate-50 hover:bg-slate-50 cursor-pointer transition-all hover:translate-x-0.5"
            @click="router.push(`/purchases/${r.name}`)"
          >
            <td class="px-4 py-3 font-mono text-xs text-slate-600">{{ r.name }}</td>
            <td class="px-4 py-3 text-slate-700">{{ formatDate(r.purchase_date) }}</td>
            <td class="px-4 py-3 font-medium text-slate-800">{{ r.supplier_name || r.supplier }}</td>
            <td class="px-4 py-3 font-mono text-xs text-slate-500">{{ r.invoice_no || '—' }}</td>
            <td class="px-4 py-3 text-center whitespace-nowrap">
              <span
                v-if="(r.device_count || 0) > 0"
                class="inline-block text-xs px-2 py-0.5 rounded-full font-medium bg-indigo-100 text-indigo-700 mr-1"
                :title="`${r.device_count} thiết bị → phiếu tiếp nhận (IMM-04)`"
              >🩺 {{ r.device_count }}</span>
              <span
                v-if="(r.part_count || 0) > 0"
                class="inline-block text-xs px-2 py-0.5 rounded-full font-medium bg-emerald-100 text-emerald-700"
                :title="`${r.part_count} phụ tùng → phiếu nhập kho`"
              >🔧 {{ r.part_count }}</span>
              <span v-if="!(r.device_count || r.part_count)" class="text-slate-300">—</span>
            </td>
            <td class="px-4 py-3 text-right font-semibold text-slate-800">{{ vnd(r.total_value) }}</td>
            <td class="px-4 py-3 text-center">
              <button
                class="text-xs px-2.5 py-1 rounded-full font-medium transition-all hover:ring-2 hover:ring-offset-1 hover:ring-current/50"
                :class="STATUS_CLASS[r.status] || 'bg-slate-100 text-slate-600'"
                :title="`Lọc: ${STATUSES.find(s => s.value === r.status)?.label || r.status}`"
                @click.stop="quickFilter(r.status)"
              >
{{ STATUSES.find(s => s.value === r.status)?.label || r.status }}
</button>
            </td>
          </tr>
        </tbody>
      </table>

    <template #pagination>
      <div v-if="total > PAGE_SIZE" class="px-4 py-3 border-t border-slate-100 flex items-center justify-between text-sm text-slate-500">
        <span>{{ (page - 1) * PAGE_SIZE + 1 }}–{{ Math.min(page * PAGE_SIZE, total) }} / {{ total }}</span>
        <div class="flex gap-2">
          <button class="btn-ghost text-xs" :disabled="page === 1" @click="page--; load()">← Trước</button>
          <span class="px-2 py-1 text-xs">Trang {{ page }}</span>
          <button class="btn-ghost text-xs" :disabled="page * PAGE_SIZE >= total" @click="page++; load()">Sau →</button>
        </div>
      </div>
    </template>
  </ListPageShell>
</template>
