<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCapabilities } from '@/composables/useCapabilities'
import { listDeviceModels, deleteDeviceModel } from '@/api/imm00'
import type { ImmDeviceModel } from '@/types/imm00'
import { useImportWizard } from '@/composables/useImportWizard'
import { useToast } from '@/composables/useToast'
import ImportWizardModal from '@/components/import/ImportWizardModal.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import { medicalDeviceClassLabel } from '@/constants/labels'

const router = useRouter()
const { can } = useCapabilities()
const toast = useToast()
const models = ref<ImmDeviceModel[]>([])
const loading = ref(false)
const error = ref('')
const totalCount = ref(0)
const PAGE_SIZE = 30
const showFilters = ref(false)

const filters = ref<{ search: string; medical_device_class: string; manufacturer: string; page: number }>({
  search: '',
  medical_device_class: '',
  manufacturer: '',
  page: 1,
})

const CLASS_OPTIONS = ['Class I', 'Class II', 'Class III']
const CLASS_LABEL: Record<string, string> = {
  'Class I': 'Loại I — Rủi ro thấp',
  'Class II': 'Loại II — Rủi ro trung bình',
  'Class III': 'Loại III — Rủi ro cao',
}
const CLASS_COLOR: Record<string, string> = {
  'Class I': 'bg-green-100 text-green-700',
  'Class II': 'bg-yellow-100 text-yellow-700',
  'Class III': 'bg-red-100 text-red-700',
}

// Lightbox preview
const previewUrl = ref('')
const previewName = ref('')
function openPreview(url: string, label: string, e: Event) {
  e.stopPropagation()
  previewUrl.value = url
  previewName.value = label
}
function closePreview() { previewUrl.value = ''; previewName.value = '' }
function onImgError(e: Event) { (e.target as HTMLImageElement).dataset.failed = '1' }

interface FilterChip { key: 'search' | 'medical_device_class' | 'manufacturer'; label: string }
const activeChips = computed<FilterChip[]>(() => {
  const chips: FilterChip[] = []
  if (filters.value.medical_device_class) {
    chips.push({ key: 'medical_device_class', label: CLASS_LABEL[filters.value.medical_device_class] || filters.value.medical_device_class })
  }
  if (filters.value.manufacturer) chips.push({ key: 'manufacturer', label: `Hãng: ${filters.value.manufacturer}` })
  if (filters.value.search.trim()) chips.push({ key: 'search', label: `"${filters.value.search.trim()}"` })
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await listDeviceModels(filters.value.page, PAGE_SIZE, filters.value.search) as unknown as
      { items: ImmDeviceModel[]; pagination: { total: number } }
    let items = res?.items || []
    if (filters.value.medical_device_class) {
      items = items.filter(m => m.medical_device_class === filters.value.medical_device_class)
    }
    if (filters.value.manufacturer) {
      const q = filters.value.manufacturer.toLowerCase()
      items = items.filter(m => (m.manufacturer || '').toLowerCase().includes(q))
    }
    models.value = items
    totalCount.value = res?.pagination?.total || 0
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Lỗi tải dữ liệu'
  } finally {
    loading.value = false
  }
}

function applyFilters() { filters.value.page = 1; load() }
function quickFilter(key: 'medical_device_class' | 'manufacturer', value: string) {
  if (!value || filters.value[key] === value) return
  filters.value[key] = value
  filters.value.page = 1
  showFilters.value = false
  load()
}
function clearChip(key: string) {
  (filters.value as Record<string, unknown>)[key] = ''
  applyFilters()
}
function resetFilters() {
  filters.value = { search: '', medical_device_class: '', manufacturer: '', page: 1 }
  load()
}
function prevPage() { if (filters.value.page > 1) { filters.value.page--; load() } }
function nextPage() { if (filters.value.page * PAGE_SIZE < totalCount.value) { filters.value.page++; load() } }

async function remove(name: string, ev: Event) {
  ev.stopPropagation()
  if (!confirm(`Xóa Model thiết bị "${name}"?`)) return
  try { await deleteDeviceModel(name); await load() }
  catch (e: unknown) { toast.error((e as Error).message || 'Không thể xóa — có thể đang được tham chiếu') }
}

onMounted(load)

// ── Import / Export ──────────────────────────────────────────────────────────

const importWizard = useImportWizard('IMM Device Model', () => load())
const openImport = importWizard.open
const doExport = importWizard.doExport

const IMPORT_NOTICE = [
  'Tên model + Nhà sản xuất là khóa duy nhất — không nhập trùng cặp.',
  'Danh mục tài sản phải đã được nhập sẵn (xem Dữ liệu tham chiếu).',
  'Mã GMDN nên tra cứu trước để khớp tiêu chuẩn quốc tế.',
]
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader title="Model thiết bị" :subtitle="`Tổng ${totalCount} model`">
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
        <button v-if="can('data.create')" class="btn-primary" @click="router.push('/device-models/new')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Thêm model thiết bị
        </button>
      </template>
    </PageHeader>

    <ListFilterBar
      :show="showFilters"
      :chips="activeChips"
      v-model:search="filters.search"
      search-placeholder="Tìm theo mã, tên, hãng, phiên bản hoặc mã GMDN..."
      @reset="resetFilters"
      @clear-chip="clearChip"
      @apply="applyFilters"
    >
      <template #fields>
        <div class="form-group">
          <label class="form-label">Phân loại</label>
          <select v-model="filters.medical_device_class" class="form-select" @change="applyFilters">
            <option value="">Tất cả phân loại</option>
            <option v-for="c in CLASS_OPTIONS" :key="c" :value="c">{{ CLASS_LABEL[c] }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Hãng sản xuất</label>
          <input v-model="filters.manufacturer" placeholder="Hãng sản xuất..." class="form-input" @keyup.enter="applyFilters" />
        </div>
      </template>
    </ListFilterBar>

    <div v-if="error" class="alert-error mb-4">{{ error }}</div>

    <!-- Table -->
    <div class="card overflow-hidden">
      <div class="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50/60">
        <span class="text-xs text-slate-500">
          <span v-if="activeFilterCount > 0">
            Kết quả lọc: <strong class="text-slate-700">{{ models.length }}</strong> model
          </span>
          <span v-else>
            Hiển thị <strong class="text-slate-700">{{ models.length }}</strong> / {{ totalCount }} model
          </span>
        </span>
        <button v-if="activeFilterCount > 0" class="text-xs text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      <div v-if="loading" class="p-6">
        <SkeletonLoader v-for="i in 5" :key="i" class="h-12 mb-3" />
      </div>
      <div v-else-if="models.length === 0" class="flex flex-col items-center justify-center py-16 text-slate-400">
        <p class="text-sm">Không tìm thấy model thiết bị nào.</p>
        <button v-if="activeFilterCount > 0" class="mt-3 text-xs text-blue-500 hover:text-blue-700 underline" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
      </div>
      <template v-else>
        <!-- Mobile cards -->
        <div class="mobile-card-list sm:hidden">
          <div
            v-for="m in models"
            :key="m.name"
            class="mobile-card"
            @click="router.push(`/device-models/${m.name}`)"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="font-mono text-sm font-semibold text-brand-700">{{ m.name }}</span>
              <span
                v-if="m.medical_device_class"
                :class="['text-xs px-2 py-0.5 rounded-full font-medium', CLASS_COLOR[m.medical_device_class] || 'bg-gray-100 text-gray-600']"
              >{{ medicalDeviceClassLabel(m.medical_device_class) }}</span>
            </div>
            <p class="text-sm font-medium text-slate-900 truncate">{{ m.model_name }}</p>
            <div class="flex flex-wrap gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
              <span v-if="m.manufacturer">{{ m.manufacturer }}</span>
              <span v-if="m.gmdn_code">· {{ m.gmdn_code }}</span>
            </div>
          </div>
        </div>

        <!-- Desktop table -->
        <div class="hidden sm:block overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 border-b border-slate-200">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 w-12"></th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Mã</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Tên model</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Hãng sản xuất</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Phiên bản</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">Phân loại</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-slate-500">GMDN</th>
              <th class="px-4 py-3 text-right"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="m in models" :key="m.name" class="hover:bg-slate-50 cursor-pointer transition-colors" @click="router.push(`/device-models/${m.name}`)">
              <td class="px-4 py-3">
                <button
                  v-if="m.model_image" type="button"
                  class="block w-12 h-12 rounded-lg border border-slate-200 bg-slate-50 overflow-hidden hover:ring-2 hover:ring-blue-400 transition"
                  :title="`Xem ảnh — ${m.model_name}`"
                  @click="openPreview(m.model_image as string, m.model_name || m.name, $event)"
                >
                  <img :src="m.model_image" alt="" loading="lazy" class="w-full h-full object-cover data-[failed=1]:hidden" @error="onImgError" />
                </button>
                <div v-else class="w-12 h-12 rounded-lg border border-dashed border-slate-200 bg-slate-50/60 flex items-center justify-center text-slate-300">
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5z" />
                  </svg>
                </div>
              </td>
              <td class="px-4 py-3 font-mono text-xs text-slate-500">{{ m.name }}</td>
              <td class="px-4 py-3 font-medium text-slate-800">
                {{ m.model_name }}
                <p v-if="m.asset_category" class="text-[10px] text-slate-400 font-normal mt-0.5">{{ (m as any).asset_category_name || (m as any).category_name || m.asset_category }}</p>
              </td>
              <td class="px-4 py-3">
                <button
                  v-if="m.manufacturer"
                  class="text-left text-slate-700 hover:text-blue-600 hover:underline decoration-dotted underline-offset-2"
                  @click.stop="quickFilter('manufacturer', m.manufacturer!)"
                >{{ m.manufacturer }}</button>
                <span v-else class="text-slate-400">—</span>
              </td>
              <td class="px-4 py-3 text-slate-500">{{ m.model_version || '—' }}</td>
              <td class="px-4 py-3">
                <button
                  v-if="m.medical_device_class"
                  :class="['text-xs px-2 py-1 rounded-full font-medium transition-all hover:ring-2 hover:ring-offset-1 hover:ring-current/50', CLASS_COLOR[m.medical_device_class] || 'bg-gray-100 text-gray-600']"
                  :title="`Lọc: ${CLASS_LABEL[m.medical_device_class] || m.medical_device_class}`"
                  @click.stop="quickFilter('medical_device_class', m.medical_device_class!)"
                >{{ medicalDeviceClassLabel(m.medical_device_class) }}</button>
                <span v-else class="text-slate-400">—</span>
              </td>
              <td class="px-4 py-3 text-slate-500 font-mono text-xs">{{ m.gmdn_code || '—' }}</td>
              <td class="px-4 py-3 text-right space-x-2 whitespace-nowrap">
                <!-- CR-RBAC-PARITY: nút Sửa/Xóa chỉ cho data.write; user chỉ-đọc vẫn
                     click-toàn-hàng để XEM read-only (/device-models/:id data.read). -->
                <button v-if="can('data.write')" class="text-blue-600 hover:text-blue-800 text-xs font-medium" @click.stop="router.push(`/device-models/${m.name}`)">Sửa</button>
                <button v-if="can('data.write')" class="text-red-600 hover:text-red-800 text-xs font-medium" @click="(ev) => remove(m.name, ev)">Xóa</button>
              </td>
            </tr>
          </tbody>
        </table>
        </div>
      </template>

      <div v-if="totalCount > PAGE_SIZE" class="flex items-center justify-between px-4 py-3 border-t border-slate-100 text-sm text-slate-500">
        <span>{{ (filters.page - 1) * PAGE_SIZE + 1 }}–{{ Math.min(filters.page * PAGE_SIZE, totalCount) }} / {{ totalCount }}</span>
        <div class="flex gap-2">
          <button :disabled="filters.page === 1" class="px-3 py-1 rounded border border-slate-300 disabled:opacity-40 hover:bg-slate-50" @click="prevPage">‹ Trước</button>
          <button :disabled="filters.page * PAGE_SIZE >= totalCount" class="px-3 py-1 rounded border border-slate-300 disabled:opacity-40 hover:bg-slate-50" @click="nextPage">Sau ›</button>
        </div>
      </div>
    </div>

    <ImportWizardModal :ctx="importWizard" title="Nhập Model thiết bị" unit="model" :notice="IMPORT_NOTICE" />

    <!-- Lightbox preview -->
    <div
      v-if="previewUrl"
      class="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-6 cursor-zoom-out"
      @click="closePreview"
      @keydown.esc="closePreview"
    >
      <div class="relative max-w-5xl max-h-[90vh] flex flex-col items-center" @click.stop>
        <img :src="previewUrl" :alt="previewName" class="max-w-full max-h-[80vh] object-contain rounded-lg shadow-2xl bg-white" />
        <div class="mt-3 flex items-center gap-3 text-white text-sm">
          <span class="font-medium">{{ previewName }}</span>
          <a :href="previewUrl" target="_blank" rel="noopener" class="text-blue-200 hover:text-white underline-offset-4 hover:underline">Mở tab mới</a>
          <button type="button" class="ml-2 px-3 py-1 rounded-md bg-white/10 hover:bg-white/20 border border-white/20" @click="closePreview">Đóng (Esc)</button>
        </div>
      </div>
    </div>
  </div>
</template>
