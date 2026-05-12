<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { listWarehouses, createWarehouse, updateWarehouse, deleteWarehouse } from '@/api/inventory'
import type { Warehouse } from '@/types/inventory'
import SmartSelect from '@/components/common/SmartSelect.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'

const router = useRouter()
const rows = ref<Warehouse[]>([])
const loading = ref(false)
const showFilters = ref(false)
const showForm = ref(false)
const editing = ref<Warehouse | null>(null)
const saving = ref(false)
const toast = ref('')

const statusFilter = ref<'all' | 'active' | 'inactive'>('all')

const form = ref<Partial<Warehouse>>({
  warehouse_code: '', warehouse_name: '', department: '', location: '', manager: '',
  is_active: 1, notes: '',
})

interface Chip { key: 'status'; label: string }
const activeChips = computed<Chip[]>(() => {
  const chips: Chip[] = []
  if (statusFilter.value === 'active') chips.push({ key: 'status', label: 'Đang hoạt động' })
  else if (statusFilter.value === 'inactive') chips.push({ key: 'status', label: 'Đã ngừng' })
  return chips
})
const activeFilterCount = computed(() => activeChips.value.length)

const filteredRows = computed(() => {
  if (statusFilter.value === 'active') return rows.value.filter(w => w.is_active)
  if (statusFilter.value === 'inactive') return rows.value.filter(w => !w.is_active)
  return rows.value
})

function clearChip(key: string) {
  if (key === 'status') statusFilter.value = 'all'
}

function resetFilters() {
  statusFilter.value = 'all'
}

function quickFilter(active: boolean) {
  statusFilter.value = active ? 'active' : 'inactive'
  showFilters.value = false
}

async function load() {
  loading.value = true
  try {
    const r = await listWarehouses({ active_only: 0, page_size: 100 })
    rows.value = r?.items || []
  } finally { loading.value = false }
}

function openCreate() {
  editing.value = null
  form.value = { warehouse_code: '', warehouse_name: '', department: '', location: '', manager: '', is_active: 1, notes: '' }
  showForm.value = true
}

function openEdit(w: Warehouse) {
  editing.value = w
  form.value = { ...w }
  showForm.value = true
}

async function submit() {
  if (!form.value.warehouse_code || !form.value.warehouse_name) {
    toast.value = 'Mã và tên kho là bắt buộc'
    return
  }
  saving.value = true
  try {
    if (editing.value) await updateWarehouse(editing.value.name, form.value)
    else await createWarehouse(form.value)
    showForm.value = false
    toast.value = editing.value ? 'Cập nhật thành công' : 'Tạo kho thành công'
    await load()
    setTimeout(() => { toast.value = '' }, 3000)
  } catch (e: unknown) {
    toast.value = (e as Error).message || 'Lỗi lưu'
  } finally { saving.value = false }
}

async function doDelete(w: Warehouse) {
  if (!confirm(`Ngừng hoạt động kho "${w.warehouse_name}"? Kho phải không còn tồn kho.`)) return
  try {
    await deleteWarehouse(w.name)
    toast.value = `Đã ngừng kho ${w.warehouse_name}`
    await load()
    setTimeout(() => { toast.value = '' }, 3000)
  } catch (e: unknown) {
    toast.value = (e as Error).message || 'Lỗi ngừng kho'
  }
}

function vnd(v?: number) {
  if (!v) return '0 đ'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(v)
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader
      title="Danh sách kho"
      :subtitle="`Tổng ${rows.length} kho`"
    >
      <template #actions>
        <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
        <button class="btn-primary shrink-0" @click="openCreate">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Tạo kho mới
        </button>
      </template>
    </PageHeader>

    <div v-if="toast" class="mb-4 px-4 py-3 rounded-lg bg-emerald-50 text-emerald-700 text-sm">{{ toast }}</div>

    <ListFilterBar
      :show="showFilters"
      :chips="activeChips"
      :show-search="false"
      @reset="resetFilters"
      @clear-chip="clearChip"
      @apply="() => {}"
    >
      <template #fields>
        <div class="form-group">
          <label class="form-label">Trạng thái</label>
          <select v-model="statusFilter" class="form-select text-sm">
            <option value="all">Tất cả</option>
            <option value="active">Đang hoạt động</option>
            <option value="inactive">Đã ngừng</option>
          </select>
        </div>
      </template>
    </ListFilterBar>

    <div class="card overflow-hidden">
      <!-- Info row -->
      <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span>Hiển thị <strong class="text-slate-700">{{ filteredRows.length }}</strong> / {{ rows.length }} kho</span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>

      <div v-if="loading" class="p-6">
        <SkeletonLoader variant="table" :rows="6" />
      </div>
      <div v-else-if="filteredRows.length === 0" class="flex flex-col items-center justify-center py-16 text-slate-400">
        <p class="text-sm">Chưa có kho nào.</p>
        <button v-if="activeFilterCount > 0" class="text-xs text-blue-500 hover:text-blue-700 underline mt-2" @click="resetFilters">
          Xóa bộ lọc để xem tất cả
        </button>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 border-b border-slate-100">
            <tr>
              <th class="table-header">Mã kho</th>
              <th class="table-header">Tên kho</th>
              <th class="table-header hidden md:table-cell">Khoa quản lý</th>
              <th class="table-header hidden lg:table-cell">Người phụ trách</th>
              <th class="table-header text-right">Số SKU</th>
              <th class="table-header text-right">Giá trị tồn</th>
              <th class="table-header text-center">Trạng thái</th>
              <th class="px-4 py-3" />
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-50">
            <tr
v-for="w in filteredRows" :key="w.name"
              class="hover:bg-slate-50/70 cursor-pointer transition-all hover:translate-x-0.5"
              @click="router.push(`/warehouses/${w.name}`)"
            >
              <td class="px-4 py-3 font-mono text-xs text-slate-600">{{ w.warehouse_code || w.name }}</td>
              <td class="px-4 py-3 font-medium text-slate-800">{{ w.warehouse_name }}</td>
              <td class="px-4 py-3 text-xs text-slate-500 hidden md:table-cell">{{ w.department_name || w.department || '—' }}</td>
              <td class="px-4 py-3 text-xs text-slate-500 hidden lg:table-cell">{{ w.manager || '—' }}</td>
              <td class="px-4 py-3 text-right text-sm">{{ w.stock_count || 0 }}</td>
              <td class="px-4 py-3 text-right text-sm font-medium text-emerald-700">{{ vnd(w.total_value) }}</td>
              <td class="px-4 py-3 text-center">
                <button
                  class="text-xs px-2 py-0.5 rounded-full transition-all hover:ring-2 hover:ring-offset-1 hover:ring-current/50"
                  :class="w.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'"
                  :title="`Lọc: ${w.is_active ? 'Hoạt động' : 'Ngừng'}`"
                  @click.stop="quickFilter(!!w.is_active)"
                >
{{ w.is_active ? 'Hoạt động' : 'Ngừng' }}
</button>
              </td>
              <td class="px-4 py-3 text-right">
                <div class="flex justify-end gap-3">
                  <button class="text-xs text-blue-600 hover:text-blue-800 font-medium" @click.stop="openEdit(w)">Sửa</button>
                  <button v-if="w.is_active" class="text-xs text-red-500 hover:text-red-700 font-medium" @click.stop="doDelete(w)">Ngừng</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Modal form -->
    <Transition name="fade">
      <div
v-if="showForm" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
           @click.self="showForm = false">
        <div class="bg-white rounded-2xl w-full max-w-xl shadow-2xl">
          <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100">
            <h2 class="font-semibold text-slate-800">{{ editing ? 'Sửa kho' : 'Tạo kho mới' }}</h2>
            <button class="p-1.5 rounded-md text-slate-400 hover:bg-slate-100" @click="showForm = false">✕</button>
          </div>
          <div class="p-6 space-y-4">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label for="wh-code" class="form-label">Mã kho *</label>
                <input
id="wh-code" v-model="form.warehouse_code" type="text" class="form-input w-full"
                       placeholder="WH-XXX" :disabled="!!editing" />
              </div>
              <div>
                <label for="wh-name" class="form-label">Tên kho *</label>
                <input id="wh-name" v-model="form.warehouse_name" type="text" class="form-input w-full" />
              </div>
              <div>
                <label for="wh-location" class="form-label">Vị trí vật lý</label>
                <SmartSelect id="wh-location" v-model="form.location" doctype="AC Location" placeholder="Chọn vị trí..." />
              </div>
              <div>
                <label for="wh-dept" class="form-label">Khoa quản lý</label>
                <SmartSelect id="wh-dept" v-model="form.department" doctype="AC Department" placeholder="Chọn khoa..." />
              </div>
              <div>
                <label for="wh-manager" class="form-label">Người phụ trách</label>
                <SmartSelect id="wh-manager" v-model="form.manager" doctype="User" placeholder="Chọn user..." />
              </div>
              <div class="flex items-center gap-3 pt-6">
                <input
id="wh-active" v-model="form.is_active" type="checkbox" :true-value="1" :false-value="0"
                       class="h-4 w-4 text-blue-600 rounded" />
                <label for="wh-active" class="text-sm text-slate-700">Đang hoạt động</label>
              </div>
            </div>
            <div>
              <label for="wh-notes" class="form-label">Ghi chú</label>
              <textarea id="wh-notes" v-model="form.notes" rows="2" class="form-input w-full" />
            </div>
          </div>
          <div class="flex gap-3 justify-end px-6 py-4 border-t border-slate-100">
            <button class="btn-ghost" @click="showForm = false">Huỷ</button>
            <button class="btn-primary" :disabled="saving" @click="submit">
              {{ saving ? 'Đang lưu...' : (editing ? 'Cập nhật' : 'Tạo kho') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
