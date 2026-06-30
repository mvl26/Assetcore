<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { frappeGet } from '@/api/helpers'
import type { ServiceContract } from '@/types/imm00'
import { useImportWizard } from '@/composables/useImportWizard'
import ImportWizardModal from '@/components/import/ImportWizardModal.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'

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

function clearChip(key: string) {
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

// ── Import / Export ──────────────────────────────────────────────────────────

const importWizard = useImportWizard('Service Contract', () => load())
const openImport = importWizard.open
const doExport = importWizard.doExport

const IMPORT_NOTICE = [
  'Mã hợp đồng phải duy nhất.',
  'Nhà cung cấp phải đã tồn tại — tên hoặc mã hệ thống đều được.',
  'Ngày bắt đầu / kết thúc dạng YYYY-MM-DD.',
]
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <PageHeader
      title="Hợp đồng dịch vụ"
      :subtitle="`Tổng ${totalCount} hợp đồng`"
    >
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
        <button
          class="px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 text-gray-600 flex items-center gap-1.5"
          title="Tải dữ liệu hiện tại về Excel"
          @click="doExport"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Xuất Excel
        </button>
        <button
          class="px-3 py-2 text-sm border border-emerald-300 rounded-lg hover:bg-emerald-50 text-emerald-700 flex items-center gap-1.5"
          @click="openImport"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
          </svg>
          Nhập Excel
        </button>
        <button class="btn-primary shrink-0" @click="router.push('/service-contracts/new')">
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
          <label class="form-label">Loại hợp đồng</label>
          <select v-model="contractType" class="form-select text-sm" @change="() => { page = 1; load() }">
            <option value="">Tất cả loại</option>
            <option v-for="t in CONTRACT_TYPES" :key="t" :value="t">{{ CONTRACT_TYPE_LABEL[t] || t }}</option>
          </select>
        </div>
      </template>
    </ListFilterBar>

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

      <div v-if="loading" class="p-6">
        <SkeletonLoader variant="table" :rows="6" />
      </div>
      <div v-else-if="contracts.length === 0 && !error" class="flex flex-col items-center justify-center py-16 text-slate-400">
        <p class="text-sm">Chưa có hợp đồng dịch vụ nào.</p>
        <button v-if="activeFilterCount > 0" class="text-xs text-blue-500 hover:text-blue-700 underline mt-2" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
      </div>
      <template v-else>
        <!-- Mobile cards -->
        <div class="mobile-card-list sm:hidden">
          <div
            v-for="c in contracts"
            :key="c.name"
            class="mobile-card"
            @click="router.push(`/service-contracts/${c.name}`)"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="font-mono text-sm font-semibold text-brand-700">{{ c.name }}</span>
              <span
                :class="['text-xs px-2 py-0.5 rounded-full font-medium', TYPE_COLORS[c.contract_type] || 'bg-gray-100 text-gray-600']"
              >{{ CONTRACT_TYPE_LABEL[c.contract_type] || c.contract_type }}</span>
            </div>
            <p class="text-sm font-medium text-slate-900 truncate">{{ c.contract_title }}</p>
            <div class="flex flex-wrap gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
              <span>{{ c.supplier_name || c.supplier || '—' }}</span>
              <span>· Hết hạn: <span :class="expiryClass(c.contract_end)">{{ formatDate(c.contract_end) }}</span></span>
            </div>
          </div>
        </div>

        <!-- Desktop table -->
        <div class="hidden sm:block overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 border-b border-slate-200">
            <tr>
              <th class="table-header">Mã HĐ</th>
              <th class="table-header">Tên hợp đồng</th>
              <th class="table-header">Nhà cung cấp</th>
              <th class="table-header">Loại</th>
              <th class="table-header">Bắt đầu</th>
              <th class="table-header">Hết hạn</th>
              <th class="table-header">SLA (giờ)</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr
v-for="c in contracts" :key="c.name"
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
                >
{{ CONTRACT_TYPE_LABEL[c.contract_type] || c.contract_type }}
</button>
              </td>
              <td class="px-4 py-3 text-slate-500">{{ formatDate(c.contract_start) }}</td>
              <td class="px-4 py-3" :class="expiryClass(c.contract_end)">{{ formatDate(c.contract_end) }}</td>
              <td class="px-4 py-3 text-slate-500">{{ c.sla_response_hours ?? '—' }}</td>
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
    <ImportWizardModal :ctx="importWizard" title="Nhập hợp đồng" unit="hợp đồng" :notice="IMPORT_NOTICE" />
  </div>
</template>
