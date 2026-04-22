<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAssetStore, useRefDataStore } from '@/stores/imm00'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import type { LifecycleStatus, AssetListParams } from '@/types/imm00'

const router = useRouter()
const store = useAssetStore()
const refData = useRefDataStore()

const filters = ref<AssetListParams>({
  lifecycle_status: '',
  department: '',
  location: '',
  asset_category: '',
  gmdn_status: '',
  search: '',
  page: 1,
  page_size: 20,
})

const LIFECYCLE_STATUSES: { value: LifecycleStatus | ''; label: string }[] = [
  { value: '', label: 'Tất cả trạng thái' },
  { value: 'Commissioned', label: 'Đã đưa vào sử dụng' },
  { value: 'Active', label: 'Đang hoạt động' },
  { value: 'Under Repair', label: 'Đang sửa chữa' },
  { value: 'Calibrating', label: 'Đang hiệu chuẩn' },
  { value: 'Out of Service', label: 'Ngừng hoạt động' },
  { value: 'Decommissioned', label: 'Đã thanh lý' },
]

const statusColor: Record<string, string> = {
  'Active': 'bg-green-100 text-green-800',
  'Commissioned': 'bg-blue-100 text-blue-800',
  'Under Repair': 'bg-yellow-100 text-yellow-800',
  'Calibrating': 'bg-purple-100 text-purple-800',
  'Out of Service': 'bg-red-100 text-red-800',
  'Decommissioned': 'bg-gray-200 text-gray-500',
}

const lifecycleLabel: Record<string, string> = {
  'Active': 'Đang hoạt động',
  'Commissioned': 'Đã tiếp nhận',
  'Under Repair': 'Đang sửa chữa',
  'Calibrating': 'Đang hiệu chuẩn',
  'Out of Service': 'Ngừng hoạt động',
  'Decommissioned': 'Đã thanh lý',
}

const cleanParams = computed<AssetListParams>(() => {
  const p: AssetListParams = { page: filters.value.page, page_size: filters.value.page_size }
  if (filters.value.lifecycle_status) p.lifecycle_status = filters.value.lifecycle_status
  if (filters.value.department) p.department = filters.value.department
  if (filters.value.location) p.location = filters.value.location
  if (filters.value.asset_category) p.asset_category = filters.value.asset_category
  if (filters.value.gmdn_status) p.gmdn_status = filters.value.gmdn_status
  if (filters.value.search?.trim()) p.search = filters.value.search.trim()
  return p
})

function applyFilters() {
  filters.value.page = 1
  store.fetchList(cleanParams.value)
}

function resetFilters() {
  filters.value = { lifecycle_status: '', department: '', location: '', asset_category: '', gmdn_status: '', search: '', page: 1, page_size: 20 }
  store.fetchList({})
}

function goToPage(page: number) {
  filters.value.page = page
  store.fetchList({ ...cleanParams.value, page })
}

function formatDate(d?: string) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('vi-VN')
}

function isPmOverdue(date?: string) {
  if (!date) return false
  return new Date(date) < new Date()
}

onMounted(async () => {
  await Promise.all([store.fetchList(), refData.fetchAll()])
})
</script>

<template>
  <div class="page-container animate-fade-in">
    <!-- Header -->
    <div class="flex items-start justify-between mb-7">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-00</p>
        <h1 class="text-2xl font-bold text-slate-900">Danh sách Thiết bị</h1>
        <p class="text-sm text-slate-500 mt-1">
          Tổng <strong class="text-slate-700">{{ store.pagination.total }}</strong> thiết bị
        </p>
      </div>
      <button class="btn-primary shrink-0" @click="router.push('/assets/new')">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
        </svg>
        Thêm thiết bị
      </button>
    </div>

    <!-- Filters -->
    <div class="card mb-5 p-4">
      <div class="grid grid-cols-2 md:grid-cols-5 gap-3 mb-3">
        <select v-model="filters.lifecycle_status" class="form-select text-sm">
          <option v-for="s in LIFECYCLE_STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
        </select>
        <select v-model="filters.asset_category" class="form-select text-sm">
          <option value="">Tất cả danh mục</option>
          <option v-for="c in refData.categories" :key="c.name" :value="c.name">{{ c.category_name }}</option>
        </select>
        <select v-model="filters.department" class="form-select text-sm">
          <option value="">Tất cả khoa/phòng</option>
          <option v-for="d in refData.departments" :key="d.name" :value="d.name">{{ d.department_name }}</option>
        </select>
        <select v-model="filters.location" class="form-select text-sm">
          <option value="">Tất cả vị trí</option>
          <option v-for="l in refData.locations" :key="l.name" :value="l.name">{{ l.location_name }}</option>
        </select>
        <select v-model="filters.gmdn_status" class="form-select text-sm" @change="applyFilters">
          <option value="">Trạng thái GMDN</option>
          <option value="In Use">Đang sử dụng</option>
          <option value="Not Use">Không sử dụng</option>
        </select>
      </div>
      <div class="flex gap-2">
        <input
          v-model="filters.search"
          placeholder="Tìm theo tên, mã, serial..."
          class="form-input flex-1 text-sm"
          @keyup.enter="applyFilters"
        />
        <button class="btn-primary text-sm" @click="applyFilters">Lọc</button>
        <button class="btn-ghost text-sm" @click="resetFilters">Đặt lại</button>
      </div>
    </div>

    <!-- Error -->
    <div v-if="store.error" class="alert-error mb-4">{{ store.error }}</div>

    <!-- Table -->
    <div class="card overflow-hidden">
      <div v-if="store.loading" class="p-6">
        <SkeletonLoader v-for="i in 5" :key="i" class="h-10 mb-3" />
      </div>
      <div v-else-if="store.assets.length" class="overflow-x-auto"><table class="w-full text-sm">
        <thead class="bg-slate-50 border-b border-slate-200">
          <tr>
            <th class="text-left px-4 py-3 font-semibold text-slate-600">Tên / Mã</th>
            <th class="text-left px-4 py-3 font-semibold text-slate-600">Danh mục</th>
            <th class="text-left px-4 py-3 font-semibold text-slate-600">Trạng thái</th>
            <th class="text-left px-4 py-3 font-semibold text-slate-600">GMDN</th>
            <th class="text-left px-4 py-3 font-semibold text-slate-600">Khoa/Phòng</th>
            <th class="text-left px-4 py-3 font-semibold text-slate-600">Bảo trì tiếp theo</th>
            <th class="text-left px-4 py-3 font-semibold text-slate-600">BYT hết hạn</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr
            v-for="asset in store.assets"
            :key="asset.name"
            class="hover:bg-slate-50 cursor-pointer transition-colors"
            @click="router.push(`/assets/${asset.name}`)"
          >
            <td class="px-4 py-3">
              <p class="font-medium text-slate-900">{{ asset.asset_name }}</p>
              <p class="text-xs text-slate-400">{{ asset.name }}</p>
            </td>
            <td class="px-4 py-3">
              <div class="text-slate-700">{{ asset.category_name || asset.asset_category || '—' }}</div>
              <div v-if="asset.asset_category && asset.category_name" class="text-xs text-slate-400">{{ asset.asset_category }}</div>
            </td>
            <td class="px-4 py-3">
              <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium" :class="statusColor[asset.lifecycle_status] || 'bg-gray-100 text-gray-600'">
                {{ lifecycleLabel[asset.lifecycle_status] || asset.lifecycle_status }}
              </span>
            </td>
            <td class="px-4 py-3">
              <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                    :class="(asset.gmdn_status || 'Not Use') === 'In Use' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'">
                {{ (asset.gmdn_status || 'Not Use') === 'In Use' ? 'Đang sử dụng' : 'Không sử dụng' }}
              </span>
            </td>
            <td class="px-4 py-3">
              <div class="text-slate-700">{{ asset.department_name || asset.department || '—' }}</div>
              <div v-if="asset.department && asset.department_name" class="text-xs text-slate-400">{{ asset.department }}</div>
            </td>
            <td class="px-4 py-3">
              <span :class="isPmOverdue(asset.next_pm_date) ? 'text-red-600 font-semibold' : 'text-slate-600'">
                {{ formatDate(asset.next_pm_date) }}
              </span>
            </td>
            <td class="px-4 py-3">
              <span :class="isPmOverdue(asset.byt_reg_expiry) ? 'text-red-600 font-semibold' : 'text-slate-600'">
                {{ formatDate(asset.byt_reg_expiry) }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
      </div>
      <div v-else class="flex flex-col items-center justify-center py-16 text-slate-400">
        <svg class="w-12 h-12 mb-3 opacity-40" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M20 7H4a2 2 0 00-2 2v9a2 2 0 002 2h16a2 2 0 002-2V9a2 2 0 00-2-2z" />
        </svg>
        <p class="text-sm">Không có thiết bị nào</p>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="store.pagination.total_pages > 1" class="flex justify-between items-center mt-4 text-sm text-slate-600">
      <span>Trang {{ store.pagination.page }} / {{ store.pagination.total_pages }}</span>
      <div class="flex gap-2">
        <button
          class="btn-ghost text-xs"
          :disabled="store.pagination.page <= 1"
          @click="goToPage(store.pagination.page - 1)"
        >← Trước</button>
        <button
          class="btn-ghost text-xs"
          :disabled="store.pagination.page >= store.pagination.total_pages"
          @click="goToPage(store.pagination.page + 1)"
        >Sau →</button>
      </div>
    </div>
  </div>
</template>
