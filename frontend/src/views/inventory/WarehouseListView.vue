<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { listWarehouses, createWarehouse, updateWarehouse, deleteWarehouse } from '@/api/inventory'
import type { Warehouse } from '@/types/inventory'
import SmartSelect from '@/components/common/SmartSelect.vue'
import ApproverSelect from '@/components/commissioning/ApproverSelect.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import FilterToggleButton from '@/components/common/FilterToggleButton.vue'
import ListFilterBar from '@/components/common/ListFilterBar.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import ListPageShell from '@/components/ui/ListPageShell.vue'

const router = useRouter()
const rows = ref<Warehouse[]>([])
const loading = ref(false)
// AC-UX-047 (lô 1) — lỗi của LƯỢT NẠP danh sách (trước đây `load()` không có `catch`
// ⇒ API hỏng in «Chưa có kho phù hợp»). Lỗi lưu/ngừng-kho đi lối `toast` riêng.
const loadError = ref<string | null>(null)
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

const emptyTitle = computed(() =>
  activeFilterCount.value > 0 ? 'Không có kho nào phù hợp' : 'Chưa có kho nào')
const EMPTY_HINT = 'Hãy tạo kho mới hoặc xoá bộ lọc để xem tất cả.'

async function load() {
  loading.value = true
  loadError.value = null                       // INV-UX3-4 — xoá lỗi ĐẦU lượt
  try {
    const r = await listWarehouses({ active_only: 0, page_size: 100 })
    rows.value = r?.items || []
  } catch (e: unknown) {
    loadError.value = e instanceof Error ? e.message : String(e)
    rows.value = []                            // INV-UX3-5
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
  <!-- AC-UX-047 (lô 1) — khuôn 4 trạng thái loại trừ (ui/ListPageShell). -->
  <ListPageShell
    :loading="loading"
    :error-message="loadError"
    :is-empty="!filteredRows.length"
    :empty-title="emptyTitle"
    :empty-hint="EMPTY_HINT"
    @retry="load">
    <template #header>
      <PageHeader
        title="Danh sách kho"
        :subtitle="`IMM-15 · Tồn kho phụ tùng — Tổng ${rows.length} kho`"
        :breadcrumb="[{ label: 'IMM-15 · Tồn kho phụ tùng', to: '/inventory/dashboard' }, { label: 'Kho' }]"
      >
        <template #actions>
          <FilterToggleButton v-model="showFilters" :count="activeFilterCount" />
          <button class="btn-primary shrink-0" @click="openCreate">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            Tạo kho
          </button>
        </template>
      </PageHeader>
      <!-- Dải phản hồi lưu/ngừng-kho sống ở CẢ 4 trạng thái (INV-UX3-17). -->
      <div v-if="toast" class="mb-4 px-4 py-3 rounded-lg bg-emerald-50 text-emerald-700 text-sm">{{ toast }}</div>
    </template>

    <template #filters>
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
    </template>

    <template #skeleton>
      <SkeletonLoader variant="table" :rows="6" />
    </template>

    <template #empty-action>
      <button v-if="activeFilterCount > 0" class="text-xs text-brand-600 hover:text-brand-700 font-medium underline" @click="resetFilters">
        Xóa bộ lọc để xem tất cả
      </button>
      <button v-else class="btn-primary" @click="openCreate">Tạo kho đầu tiên</button>
    </template>

    <template #toolbar>
      <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100 bg-slate-50/60 text-xs text-slate-500">
        <span>Hiển thị <strong class="text-slate-700">{{ filteredRows.length }}</strong> / {{ rows.length }} kho</span>
        <button v-if="activeFilterCount > 0" class="text-red-500 hover:text-red-700 font-medium" @click="resetFilters">Xóa tất cả</button>
      </div>
    </template>

    <!-- Mobile cards (< sm) -->
        <div class="mobile-card-list sm:hidden">
          <div
            v-for="w in filteredRows"
            :key="w.name"
            class="mobile-card"
            @click="router.push(`/warehouses/${w.name}`)"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="font-mono text-sm font-semibold text-brand-700">{{ w.warehouse_code || w.name }}</span>
              <button
                class="text-xs px-2 py-0.5 rounded-full"
                :class="w.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'"
                @click.stop="quickFilter(!!w.is_active)"
              >{{ w.is_active ? 'Hoạt động' : 'Ngừng' }}</button>
            </div>
            <p class="text-sm font-medium text-slate-900 truncate">{{ w.warehouse_name }}</p>
            <div class="flex flex-wrap items-center gap-x-2 gap-y-1 mt-1.5 text-xs text-slate-500">
              <span>{{ w.department_name || w.department || '—' }}</span>
              <span class="text-slate-300">·</span>
              <span>{{ w.stock_count || 0 }} mã hàng</span>
              <span class="text-slate-300">·</span>
              <span class="text-emerald-700 font-medium">{{ vnd(w.total_value) }}</span>
            </div>
            <div class="flex justify-end gap-3 mt-2 pt-2 border-t border-slate-100" @click.stop>
              <button class="text-xs text-brand-600 font-medium" @click="openEdit(w)">Chỉnh sửa</button>
              <button v-if="w.is_active" class="text-xs text-red-600 font-medium" @click="doDelete(w)">Ngừng</button>
            </div>
          </div>
        </div>

        <!-- Desktop table (sm+) -->
        <div class="hidden sm:block overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="bg-slate-50 border-b border-slate-100">
              <tr>
                <th class="table-header">Mã kho</th>
                <th class="table-header">Tên kho</th>
                <th class="table-header hidden md:table-cell">Khoa quản lý</th>
                <th class="table-header hidden lg:table-cell">Người phụ trách</th>
                <th class="table-header text-right">Số mã hàng</th>
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
                <td class="px-4 py-3 font-mono text-xs text-brand-700">{{ w.warehouse_code || w.name }}</td>
                <td class="px-4 py-3 font-medium text-slate-900">{{ w.warehouse_name }}</td>
                <td class="px-4 py-3 text-xs text-slate-500 hidden md:table-cell">{{ w.department_name || w.department || '—' }}</td>
                <td class="px-4 py-3 text-xs text-slate-500 hidden lg:table-cell">
                  <template v-if="w.manager">
                    <p class="text-slate-700">{{ w.manager_name || w.manager }}</p>
                    <p v-if="w.manager_name && w.manager_name !== w.manager" class="text-[10px] text-slate-400">{{ w.manager }}</p>
                  </template>
                  <span v-else>—</span>
                </td>
                <td class="px-4 py-3 text-right text-sm">{{ w.stock_count || 0 }}</td>
                <td class="px-4 py-3 text-right text-sm font-medium text-emerald-700">{{ vnd(w.total_value) }}</td>
                <td class="px-4 py-3 text-center">
                  <button
                    class="text-xs px-2 py-0.5 rounded-full transition-all hover:ring-2 hover:ring-offset-1 hover:ring-current/50"
                    :class="w.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'"
                    :title="`Lọc: ${w.is_active ? 'Hoạt động' : 'Ngừng'}`"
                    @click.stop="quickFilter(!!w.is_active)"
                  >{{ w.is_active ? 'Hoạt động' : 'Ngừng' }}</button>
                </td>
                <td class="px-4 py-3 text-right">
                  <div class="flex justify-end gap-3">
                    <button class="text-xs text-brand-600 hover:text-brand-700 font-medium" @click.stop="openEdit(w)">Chỉnh sửa</button>
                    <button v-if="w.is_active" class="text-xs text-red-600 hover:text-red-700 font-medium" @click.stop="doDelete(w)">Ngừng</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
  </ListPageShell>

  <!-- Hộp thoại đặt NGOÀI khuôn: mở được ở CẢ 4 trạng thái (INV-UX3-17). -->
  <Transition name="fade">
      <div
v-if="showForm" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
           @click.self="showForm = false">
        <div class="bg-white rounded-xl w-full max-w-xl shadow-modal border border-slate-200">
          <div class="flex items-center justify-between px-6 py-4 border-b border-slate-200">
            <h2 class="font-semibold text-slate-900">{{ editing ? 'Chỉnh sửa kho' : 'Tạo kho' }}</h2>
            <button class="p-1.5 rounded-md text-slate-400 hover:bg-slate-100" aria-label="Đóng" @click="showForm = false">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.7" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
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
                <ApproverSelect id="wh-manager" v-model="form.manager" context="user" placeholder="Chọn người dùng..." />
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
              {{ saving ? 'Đang lưu…' : (editing ? 'Lưu thay đổi' : 'Tạo kho') }}
            </button>
          </div>
        </div>
      </div>
  </Transition>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
