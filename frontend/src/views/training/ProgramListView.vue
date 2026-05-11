<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useImm06Store } from '@/stores/imm06'
import { useAuthStore } from '@/stores/auth'
import { useApi } from '@/composables/useApi'
import { ROLES_TRAINING_MANAGE } from '@/constants/roles'
import PageHeader from '@/components/common/PageHeader.vue'
import BasePagination from '@/components/common/BasePagination.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'

const router = useRouter()
const store = useImm06Store()
const authStore = useAuthStore()
const api = useApi()

const { programs, programPagination, loading } = storeToRefs(store)

const filterType = ref('')
const filterActive = ref('')
const showFilters = ref(false)

const canManage = computed(() => authStore.hasAnyRole(ROLES_TRAINING_MANAGE))

const TRAINING_TYPES = [
  { value: 'Initial',       label: 'Đào tạo ban đầu' },
  { value: 'Refresher',     label: 'Đào tạo nhắc lại' },
  { value: 'Advanced',      label: 'Đào tạo nâng cao' },
  { value: 'Certification', label: 'Chứng nhận' },
]

const ACTIVE_OPTIONS = [
  { value: '1', label: 'Đang hoạt động' },
  { value: '0', label: 'Không hoạt động' },
]

interface Chip { key: string; label: string }
const activeChips = computed<Chip[]>(() => {
  const chips: Chip[] = []
  if (filterType.value) {
    const t = TRAINING_TYPES.find(x => x.value === filterType.value)
    chips.push({ key: 'type', label: t?.label ?? filterType.value })
  }
  if (filterActive.value !== '') {
    chips.push({ key: 'active', label: filterActive.value === '1' ? 'Đang hoạt động' : 'Không hoạt động' })
  }
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)

function clearChip(key: string) {
  if (key === 'type') filterType.value = ''
  else filterActive.value = ''
  load(1)
}

function resetFilters() {
  filterType.value = ''
  filterActive.value = ''
  load(1)
}

async function load(page = 1) {
  const filters: Record<string, unknown> = {}
  if (filterType.value) filters.training_type = filterType.value
  if (filterActive.value !== '') filters.is_active = Number(filterActive.value)
  await api.run(() => store.fetchPrograms(filters, page))
}

onMounted(() => load())
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <PageHeader
      title="Chương trình đào tạo"
      :subtitle="`Tổng ${programPagination.total} chương trình`"
      :breadcrumb="[{ label: 'IMM-06 · Đào tạo & Năng lực', to: '/training/programs' }, { label: 'Danh sách chương trình' }]"
    >
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
        <button
          v-if="canManage"
          class="btn-primary"
          @click="router.push('/training/programs/new')"
        >
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
      @apply="load(1)"
    >
      <template #fields>
        <div class="form-group">
          <label class="form-label">Loại đào tạo</label>
          <select v-model="filterType" class="form-select" @change="load(1)">
            <option value="">Tất cả loại</option>
            <option v-for="t in TRAINING_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Trạng thái</label>
          <select v-model="filterActive" class="form-select" @change="load(1)">
            <option value="">Tất cả</option>
            <option v-for="o in ACTIVE_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option>
          </select>
        </div>
      </template>
    </ListFilterBar>

    <div class="table-wrapper">
      <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span>Hiển thị <strong class="text-slate-700">{{ programs.length }}</strong> / {{ programPagination.total }} chương trình</span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      <div v-if="loading" class="p-4">
        <SkeletonLoader variant="table" :rows="6" />
      </div>
      <div v-else-if="!programs.length" class="flex flex-col items-center justify-center py-16 text-slate-400">
        <svg class="w-10 h-10 mb-3 text-slate-300" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
        </svg>
        <p class="text-sm font-medium">Chưa có chương trình đào tạo nào</p>
        <button v-if="activeFilterCount > 0" class="text-xs text-blue-500 hover:text-blue-700 underline mt-2" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
      </div>
      <div v-else class="overflow-x-auto">
        <table class="min-w-full divide-y divide-slate-100">
          <thead>
            <tr>
              <th class="table-header">Mã</th>
              <th class="table-header">Tên chương trình</th>
              <th class="table-header">Loại đào tạo</th>
              <th class="table-header">Device Model</th>
              <th class="table-header">Thời lượng</th>
              <th class="table-header">Điểm đạt</th>
              <th class="table-header">Trạng thái</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr
              v-for="p in programs"
              :key="p.name"
              class="hover:bg-slate-50 cursor-pointer transition-colors"
              @click="router.push(`/training/programs/${p.name}`)"
            >
              <td class="table-cell font-mono text-xs text-slate-500">{{ p.name }}</td>
              <td class="table-cell">
                <div class="font-medium text-slate-900 truncate max-w-[240px]">{{ p.program_name }}</div>
                <div v-if="p.is_mandatory_for_operation" class="text-xs text-amber-600 font-medium mt-0.5">Bắt buộc vận hành</div>
              </td>
              <td class="table-cell">
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700">
                  {{ p.training_type === 'Initial' ? 'Ban đầu'
                    : p.training_type === 'Refresher' ? 'Nhắc lại'
                    : p.training_type === 'Advanced' ? 'Nâng cao'
                    : 'Chứng nhận' }}
                </span>
              </td>
              <td class="table-cell text-slate-600 text-sm">{{ p.target_device_model ?? p.target_device_category ?? '—' }}</td>
              <td class="table-cell text-slate-600 text-sm">{{ p.duration_hours }}h</td>
              <td class="table-cell text-slate-600 text-sm">{{ p.passing_score_pct }}%</td>
              <td class="table-cell">
                <StatusBadge :state="p.is_active ? 'Active' : 'Inactive'" />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <BasePagination :pagination="programPagination" @page-change="load" />
  </div>
</template>
