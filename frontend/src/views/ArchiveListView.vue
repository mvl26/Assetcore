<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useImm14Store } from '@/stores/imm14'
import { useRouter } from 'vue-router'

const store = useImm14Store()
const router = useRouter()

const statusFilter = ref('')
const assetFilter = ref('')

const STATUSES = [
  { value: 'Draft', label: 'Nháp' },
  { value: 'Compiling', label: 'Đang tổng hợp' },
  { value: 'Pending Verification', label: 'Chờ xác minh' },
  { value: 'Pending Approval', label: 'Chờ phê duyệt' },
  { value: 'Finalized', label: 'Đã phê duyệt' },
  { value: 'Archived', label: 'Đã lưu trữ' },
]

function statusBadgeClass(status: string): string {
  const map: Record<string, string> = {
    'Draft': 'bg-blue-100 text-blue-700',
    'Compiling': 'bg-blue-100 text-blue-700',
    'Pending Verification': 'bg-yellow-100 text-yellow-700',
    'Pending Approval': 'bg-yellow-100 text-yellow-700',
    'Finalized': 'bg-orange-100 text-orange-700',
    'Archived': 'bg-green-100 text-green-700',
  }
  return map[status] ?? 'bg-slate-100 text-slate-600'
}

function applyFilters() {
  store.fetchArchives(statusFilter.value, assetFilter.value)
}

function resetFilters() {
  statusFilter.value = ''
  assetFilter.value = ''
  store.fetchArchives()
}

const totalPages = computed(() => Math.ceil(store.pagination.total / store.pagination.page_size))

onMounted(() => store.fetchArchives())
</script>

<template>
  <div class="page-container animate-fade-in">
    <!-- Header -->
    <div class="flex items-start justify-between mb-5">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-14 · Lưu trữ hồ sơ</p>
        <h1 class="text-2xl font-bold text-slate-900">Hồ sơ Lưu trữ Thiết bị</h1>
        <p class="text-sm text-slate-500 mt-1">
          Tổng <strong class="text-slate-700">{{ store.pagination.total }}</strong> hồ sơ
        </p>
      </div>
    </div>

    <!-- Filter bar -->
    <div class="card mb-5 p-4">
      <div class="flex flex-wrap gap-3">
        <input
          v-model="assetFilter"
          placeholder="Tìm theo mã thiết bị..."
          class="form-input flex-1 min-w-48"
          @keyup.enter="applyFilters"
        />
        <select v-model="statusFilter" class="form-select w-52">
          <option value="">Tất cả trạng thái</option>
          <option v-for="s in STATUSES" :key="s.value" :value="s.value">{{ s.label }}</option>
        </select>
        <button class="btn-primary px-4" @click="applyFilters">Tìm kiếm</button>
        <button class="btn-ghost" @click="resetFilters">Đặt lại</button>
      </div>
    </div>

    <!-- Loading skeleton -->
    <div v-if="store.loading" class="card">
      <div v-for="i in 5" :key="i" class="flex gap-4 py-3 border-b border-slate-100 last:border-0 animate-pulse px-4">
        <div class="h-4 bg-slate-100 rounded w-32" />
        <div class="h-4 bg-slate-100 rounded flex-1" />
        <div class="h-4 bg-slate-100 rounded w-24" />
        <div class="h-4 bg-slate-100 rounded w-24" />
        <div class="h-4 bg-slate-100 rounded w-20" />
      </div>
    </div>

    <!-- Table -->
    <div v-else class="table-wrapper">
      <table class="min-w-full divide-y divide-slate-100">
        <thead>
          <tr>
            <th class="table-header">Mã hồ sơ</th>
            <th class="table-header">Thiết bị</th>
            <th class="table-header">Ngày lưu trữ</th>
            <th class="table-header">Hết hạn</th>
            <th class="table-header">Trạng thái</th>
            <th class="table-header">Số tài liệu</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-50">
          <tr
            v-for="rec in store.archives"
            :key="rec.name"
            class="hover:bg-slate-50 cursor-pointer transition-colors"
            @click="router.push(`/archive/${rec.name}`)"
          >
            <td class="table-cell">
              <div class="font-mono text-sm font-semibold text-blue-700">{{ rec.name }}</div>
              <div v-if="rec.decommission_request" class="text-xs text-slate-400 mt-0.5">
                DR: {{ rec.decommission_request }}
              </div>
            </td>
            <td class="table-cell">
              <div class="font-medium text-slate-900">{{ rec.asset_name || rec.asset }}</div>
              <div class="text-xs text-slate-400 font-mono mt-0.5">{{ rec.asset }}</div>
            </td>
            <td class="table-cell text-sm text-slate-600">{{ rec.archive_date || '—' }}</td>
            <td class="table-cell text-sm text-slate-600">{{ rec.release_date || '—' }}</td>
            <td class="table-cell">
              <span :class="['px-2.5 py-1 rounded-full text-xs font-medium', statusBadgeClass(rec.status)]">
                {{ STATUSES.find(s => s.value === rec.status)?.label ?? rec.status }}
              </span>
            </td>
            <td class="table-cell text-sm text-slate-700 text-center">{{ rec.total_documents_archived ?? 0 }}</td>
          </tr>
          <tr v-if="store.archives.length === 0">
            <td colspan="6" class="py-16 text-center text-slate-400">
              <p class="text-sm font-medium">Không tìm thấy hồ sơ nào</p>
              <button class="text-xs text-blue-500 hover:text-blue-700 underline mt-2" @click="resetFilters">
                Xóa bộ lọc
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div v-if="totalPages > 1" class="flex justify-center mt-5 gap-1">
      <button
        v-for="p in totalPages"
        :key="p"
        :class="['px-3 py-1.5 rounded-lg text-sm border transition-colors font-medium',
          p === store.pagination.page
            ? 'bg-blue-600 text-white border-blue-600'
            : 'border-slate-300 text-slate-600 hover:bg-slate-50']"
        @click="store.fetchArchives(statusFilter, assetFilter, p)"
      >{{ p }}</button>
    </div>
  </div>
</template>
