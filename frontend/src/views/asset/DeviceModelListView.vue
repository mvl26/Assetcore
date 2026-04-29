<script setup lang="ts">
import { useToast } from '@/composables/useToast'
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listDeviceModels, deleteDeviceModel } from '@/api/imm00'
import type { ImmDeviceModel } from '@/types/imm00'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
const toast = useToast()

const router = useRouter()
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
function clearChip(key: FilterChip['key']) {
  filters.value[key] = ''
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
</script>

<template>
  <div class="page-container animate-fade-in">
    <!-- Header -->
    <div class="flex items-start justify-between mb-4">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Model thiết bị</h1>
        <p class="text-sm text-slate-500 mt-1">
          Tổng <strong class="text-slate-700">{{ totalCount }}</strong> model
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
        <button class="btn-primary shrink-0" @click="router.push('/device-models/new')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Thêm model thiết bị
        </button>
      </div>
    </div>

    <!-- Active chips -->
    <Transition
      enter-active-class="transition-all duration-200 ease-out"
      enter-from-class="opacity-0 -translate-y-1"
      enter-to-class="opacity-100 translate-y-0"
    >
      <div v-if="activeChips.length > 0 && !showFilters" class="flex flex-wrap items-center gap-2 mb-4">
        <span class="text-xs text-slate-400 font-medium">Đang lọc:</span>
        <button
          v-for="chip in activeChips" :key="chip.key"
          class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100"
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

    <!-- Filter panel -->
    <Transition
      enter-active-class="transition-all duration-200 ease-out overflow-hidden"
      enter-from-class="opacity-0 max-h-0"
      enter-to-class="opacity-100 max-h-96"
      leave-active-class="transition-all duration-150 ease-in overflow-hidden"
      leave-from-class="opacity-100 max-h-96"
      leave-to-class="opacity-0 max-h-0"
    >
      <div v-show="showFilters" class="card mb-5 p-4">
        <div class="grid grid-cols-2 md:grid-cols-3 gap-3 mb-3">
          <select v-model="filters.medical_device_class" class="form-select text-sm" @change="applyFilters">
            <option value="">Tất cả phân loại</option>
            <option v-for="c in CLASS_OPTIONS" :key="c" :value="c">{{ CLASS_LABEL[c] }}</option>
          </select>
          <input
            v-model="filters.manufacturer"
            placeholder="Hãng sản xuất..."
            class="form-input text-sm"
            @keyup.enter="applyFilters"
          />
        </div>
        <div class="flex gap-2">
          <input
            v-model="filters.search"
            placeholder="Tìm theo mã, tên, phiên bản, GMDN, EMDN..."
            class="form-input flex-1 text-sm"
            @keyup.enter="applyFilters"
          />
          <button class="btn-primary text-sm" @click="applyFilters">Tìm</button>
          <button class="btn-ghost text-sm" @click="resetFilters">Đặt lại</button>
        </div>
      </div>
    </Transition>

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
      <div v-else class="overflow-x-auto">
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
                <p v-if="m.asset_category" class="text-[10px] text-slate-400 font-normal mt-0.5">{{ m.asset_category }}</p>
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
                >{{ m.medical_device_class }}</button>
                <span v-else class="text-slate-400">—</span>
              </td>
              <td class="px-4 py-3 text-slate-500 font-mono text-xs">{{ m.gmdn_code || '—' }}</td>
              <td class="px-4 py-3 text-right space-x-2 whitespace-nowrap">
                <button class="text-blue-600 hover:text-blue-800 text-xs font-medium" @click.stop="router.push(`/device-models/${m.name}`)">Sửa</button>
                <button class="text-red-600 hover:text-red-800 text-xs font-medium" @click="(ev) => remove(m.name, ev)">Xóa</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="totalCount > PAGE_SIZE" class="flex items-center justify-between px-4 py-3 border-t border-slate-100 text-sm text-slate-500">
        <span>{{ (filters.page - 1) * PAGE_SIZE + 1 }}–{{ Math.min(filters.page * PAGE_SIZE, totalCount) }} / {{ totalCount }}</span>
        <div class="flex gap-2">
          <button :disabled="filters.page === 1" class="px-3 py-1 rounded border border-slate-300 disabled:opacity-40 hover:bg-slate-50" @click="prevPage">‹ Trước</button>
          <button :disabled="filters.page * PAGE_SIZE >= totalCount" class="px-3 py-1 rounded border border-slate-300 disabled:opacity-40 hover:bg-slate-50" @click="nextPage">Sau ›</button>
        </div>
      </div>
    </div>

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
