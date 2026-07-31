<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// IMM-14 · Giải nhiệm thiết bị (End-of-Life) — danh sách "Biên bản giải nhiệm".
//
// Tra cứu/báo cáo hồ sơ Asset Decommission (WHO HTM §3.8 / NĐ98). Read-only:
// mọi thao tác tạo/duyệt hồ sơ nằm ở AssetDetailView (modal giải nhiệm). Ở đây
// chỉ liệt kê + lọc + điều hướng về hồ sơ thiết bị.
//
// 4-layer: view → useApi → api/imm14.listDecommissions → frappeGet. KHÔNG gọi
// axios/DB trực tiếp. Nhãn 100% tiếng Việt; trạng thái + phương thức xử lý qua SSoT
// domain-specific (decommissionStateLabel/disposalMethodLabel — Draft="Chờ duyệt",
// Approved="Đã giải nhiệm") — KHÔNG leak raw EN; người chịu trách nhiệm hiển thị
// full_name (BE enrich responsible_name), KHÔNG rò email (LL-FE-53).
// Drill hàng → biên bản (/decommissions/:name); link hồ sơ thiết bị ở cột phụ.
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useApi } from '@/composables/useApi'
import {
  listDecommissions,
  type DecommissionRow,
  type DecommissionListFilters,
  type DecommissionPagination,
} from '@/api/imm14'
import type { DisposalMethod, DecommissionState } from '@/api/imm14'
import PageHeader from '@/components/common/PageHeader.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import { formatDate } from '@/utils/formatters'
import {
  disposalMethodLabel,
  decommissionStateLabel,
  decommissionStateClass,
} from '@/constants/labels'

const router = useRouter()
const route = useRoute()
const api = useApi()

const PAGE_SIZE = 20
const page = ref(1)

// Bộ lọc — value = enum kỹ thuật khớp EXACT BE; label = tiếng Việt qua SSoT
// decommissionStateLabel (Chờ duyệt/Đã giải nhiệm/Đã hủy — domain-specific).
const STATE_OPTIONS: { value: DecommissionState; label: string }[] = [
  { value: 'Draft', label: decommissionStateLabel('Draft') },
  { value: 'Approved', label: decommissionStateLabel('Approved') },
  { value: 'Cancelled', label: decommissionStateLabel('Cancelled') },
]
// disposal_method: value = enum kỹ thuật DocType (GIỮ NGUYÊN, gửi BE); label VI
// qua SSoT disposalMethodLabel (dịch phần EN Donation/Trade-in — LL-FE-53).
const DISPOSAL_OPTIONS: DisposalMethod[] = [
  'Huỷ', 'Điều chuyển/Donation', 'Bán/Trade-in', 'Lưu trữ',
]

const stateFilter = ref<DecommissionState | ''>('')
const methodFilter = ref<DisposalMethod | ''>('')
// AC-CR-95 — deep-link «Xem tất cả» từ tab «Bản ghi liên quan» của một thiết bị:
// `/decommissions?asset=<mã>`. `asset` là khoá màn ĐÍCH đọc (khớp
// `DOCTYPE_LIST_TARGET['Asset Decommission'].queryKey`) và đã nằm trong whitelist BE
// `services/imm14._DECOM_FILTER_KEYS`. Seed NGAY tại khai báo — `onMounted(load)` đọc ref
// nên lần nạp ĐẦU đã lọc, không nạp-toàn-viện-rồi-lọc-lại.
const assetFilter = ref<string>((route.query.asset as string) || '')

const rows = ref<DecommissionRow[]>([])
const pagination = ref<DecommissionPagination>({
  page: 1, page_size: PAGE_SIZE, total: 0, total_pages: 0,
})
const errorMsg = ref<string | null>(null)

const total = computed(() => pagination.value.total)
const activeFilterCount = computed(
  () => (stateFilter.value ? 1 : 0) + (methodFilter.value ? 1 : 0) + (assetFilter.value ? 1 : 0),
)
// Nhãn chip thiết bị: tên snapshot đọc được của dòng khớp mã, lùi về MÃ khi chưa có dòng
// nào. KHÔNG in fieldname ra giao diện (LL-FE-53).
const assetChipLabel = computed(() => {
  const code = assetFilter.value
  if (!code) return ''
  return rows.value.find(r => r.asset === code)?.asset_name_snapshot || code
})

async function load() {
  errorMsg.value = null
  const filters: DecommissionListFilters = {}
  if (stateFilter.value) filters.workflow_state = stateFilter.value
  if (methodFilter.value) filters.disposal_method = methodFilter.value
  if (assetFilter.value) filters.asset = assetFilter.value
  const res = await api.run(
    () => listDecommissions(filters, page.value, PAGE_SIZE),
    { silentSuccess: true, silentError: true },
  )
  if (res) {
    rows.value = res.data
    pagination.value = res.pagination
  } else {
    // useApi nuốt toast (silentError) — tự surface banner + retry (tri-branch).
    errorMsg.value = api.lastError.value?.message
      ?? 'Không tải được danh sách biên bản giải nhiệm.'
  }
}

/**
 * Rút khoá `asset` khỏi URL; trả `true` khi thật sự đã điều hướng (xem chú thích cùng
 * tên ở `views/incident/CAPAListView.vue`): URL là SSoT của bộ lọc thiết bị, URL đổi thì
 * watcher/remount đã nạp lại — dọn thêm ref ở call-site = request y hệt lần thứ hai.
 */
function dropAssetQuery(): boolean {
  if (!route.query.asset) return false
  const query = { ...route.query }
  delete query.asset
  router.replace({ query })
  return true
}

function clearAssetFilter() {
  if (dropAssetQuery()) return
  assetFilter.value = ''
}

function resetFilters() {
  stateFilter.value = ''
  methodFilter.value = ''
  clearAssetFilter()
}

watch([stateFilter, methodFilter, assetFilter], () => {
  page.value = 1
  load()
})

// Drill lần 2 CÙNG route (bấm «Xem tất cả» ở thiết bị KHÁC) không remount component ⇒
// đồng bộ query → ref; watcher trên đảm nhiệm reset trang + nạp lại.
watch(() => route.query.asset, (v) => {
  assetFilter.value = (v as string) || ''
})

function prevPage() {
  if (page.value > 1) { page.value--; load() }
}
function nextPage() {
  if (page.value * PAGE_SIZE < total.value) { page.value++; load() }
}

// Drill mặc định của hàng → biên bản giải nhiệm (chi tiết + duyệt hồ sơ draft mồ
// côi). Link tới hồ sơ thiết bị giữ ở vị trí phụ (cột riêng).
function goRecord(row: DecommissionRow) {
  router.push(`/decommissions/${row.name}`)
}
function goAsset(row: DecommissionRow) {
  router.push(`/assets/${row.asset}`)
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader
      title="Biên bản giải nhiệm"
      :subtitle="`IMM-14 · Giải nhiệm thiết bị — Tổng ${total} biên bản`"
      :breadcrumb="[{ label: 'IMM-14 · Giải nhiệm thiết bị' }, { label: 'Biên bản giải nhiệm' }]"
    />

    <!-- Dải chip «đang lọc» (AC-CR-95): deep-link «Xem tất cả» phải NÓI nó đang lọc gì và
         cho một đường ra. Danh sách lọc câm bị người dùng đọc thành "mất dữ liệu".
         Khuôn chip mượn từ ListFilterBar/PmScheduleListView cho nhất quán thị giác. -->
    <div v-if="assetFilter" class="flex flex-wrap items-center gap-2 mb-4">
      <span class="text-xs text-slate-400 font-medium">Đang lọc:</span>
      <button
        class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 transition-colors focus-visible:ring-2 focus-visible:ring-emerald-500"
        :aria-label="`Bỏ lọc theo thiết bị ${assetChipLabel}`"
        @click="clearAssetFilter"
      >
        Thiết bị: {{ assetChipLabel }}
        <svg class="w-3 h-3 opacity-60" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- Bộ lọc luôn hiển thị (đơn giản, không sau nút toggle) -->
    <div class="card p-4 mb-4">
      <div class="flex flex-wrap items-end gap-4">
        <div class="form-group">
          <label class="form-label" for="decom-state-filter">Trạng thái</label>
          <select id="decom-state-filter" v-model="stateFilter" class="form-select text-sm">
            <option value="">Tất cả</option>
            <option v-for="o in STATE_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label" for="decom-method-filter">Phương thức xử lý</label>
          <select id="decom-method-filter" v-model="methodFilter" class="form-select text-sm">
            <option value="">Tất cả</option>
            <option v-for="m in DISPOSAL_OPTIONS" :key="m" :value="m">{{ disposalMethodLabel(m) }}</option>
          </select>
        </div>
        <button
          v-if="activeFilterCount > 0"
          class="btn-secondary text-sm focus-visible:ring-2 focus-visible:ring-emerald-500"
          @click="resetFilters"
        >
          Xóa bộ lọc
        </button>
      </div>
    </div>

    <div class="card overflow-hidden">
      <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span>Hiển thị <strong class="text-slate-700">{{ rows.length }}</strong> / {{ total }} biên bản</span>
      </div>

      <!-- Tri-branch: loading / error / (empty|data) -->
      <div v-if="api.loading.value && !rows.length" class="p-6">
        <SkeletonLoader variant="table" :rows="6" />
      </div>
      <div v-else-if="errorMsg" class="flex flex-col items-center justify-center py-16 gap-3">
        <p class="text-sm text-red-600">{{ errorMsg }}</p>
        <button
          class="btn-secondary focus-visible:ring-2 focus-visible:ring-emerald-500"
          @click="load"
        >Thử lại</button>
      </div>
      <div v-else-if="rows.length === 0" class="flex flex-col items-center justify-center py-16 gap-2">
        <p class="text-sm text-slate-500">Chưa có biên bản giải nhiệm phù hợp.</p>
        <button
          v-if="activeFilterCount > 0"
          class="text-xs text-brand-600 hover:text-brand-700 font-medium underline focus-visible:ring-2 focus-visible:ring-emerald-500"
          @click="resetFilters"
        >Xóa bộ lọc để xem tất cả</button>
        <template v-else>
          <p class="text-xs text-slate-400">Biên bản giải nhiệm được lập từ hồ sơ thiết bị (nút "Giải nhiệm").</p>
          <button
            class="btn-secondary mt-1 text-sm focus-visible:ring-2 focus-visible:ring-emerald-500"
            @click="router.push('/assets')"
          >Đến danh sách thiết bị</button>
        </template>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 border-b border-slate-100">
            <tr>
              <th class="table-header">Số hồ sơ</th>
              <th class="table-header">Thiết bị</th>
              <th class="table-header hidden md:table-cell">Phương thức xử lý</th>
              <th class="table-header text-center">Trạng thái</th>
              <th class="table-header hidden lg:table-cell">Ngày giải nhiệm</th>
              <th class="table-header hidden md:table-cell">Người chịu trách nhiệm</th>
              <th class="table-header text-center">Thiết bị</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-50">
            <tr
              v-for="r in rows" :key="r.name"
              class="hover:bg-slate-50/70 cursor-pointer transition-all hover:translate-x-0.5 focus-within:bg-slate-50"
              @click="goRecord(r)"
            >
              <td class="px-4 py-3 font-mono text-xs text-brand-700 font-semibold">
                <button
                  class="hover:underline focus-visible:ring-2 focus-visible:ring-emerald-500 rounded"
                  :aria-label="`Mở biên bản giải nhiệm ${r.name}`"
                  @click.stop="goRecord(r)"
                >{{ r.name }}</button>
              </td>
              <td class="px-4 py-3 text-slate-700">{{ r.asset_name_snapshot || r.asset }}</td>
              <td class="px-4 py-3 text-slate-600 hidden md:table-cell">{{ disposalMethodLabel(r.disposal_method) }}</td>
              <td class="px-4 py-3 text-center">
                <span
                  class="inline-flex items-center font-medium rounded-full px-2.5 py-0.5 text-[11px] leading-none whitespace-nowrap"
                  :class="decommissionStateClass(r.workflow_state)"
                >{{ decommissionStateLabel(r.workflow_state) }}</span>
              </td>
              <td class="px-4 py-3 text-xs text-slate-500 hidden lg:table-cell">{{ formatDate(r.decommissioned_on) }}</td>
              <td class="px-4 py-3 text-slate-600 hidden md:table-cell">{{ r.responsible_name || '—' }}</td>
              <td class="px-4 py-3 text-center">
                <button
                  class="text-xs text-brand-600 hover:text-brand-700 underline focus-visible:ring-2 focus-visible:ring-emerald-500 rounded"
                  :aria-label="`Mở hồ sơ thiết bị của biên bản ${r.name}`"
                  @click.stop="goAsset(r)"
                >Hồ sơ thiết bị</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="total > PAGE_SIZE" class="flex items-center justify-between px-4 py-3 border-t border-slate-100 text-sm text-slate-500">
        <span>{{ (page - 1) * PAGE_SIZE + 1 }}–{{ Math.min(page * PAGE_SIZE, total) }} / {{ total }}</span>
        <div class="flex gap-2">
          <button
            :disabled="page === 1"
            class="px-3 py-1 rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-emerald-500"
            @click="prevPage"
          >Trước</button>
          <button
            :disabled="page * PAGE_SIZE >= total"
            class="px-3 py-1 rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-emerald-500"
            @click="nextPage"
          >Sau</button>
        </div>
      </div>
    </div>
  </div>
</template>
