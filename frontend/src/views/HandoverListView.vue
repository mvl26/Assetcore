<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useImm06Store } from '@/stores/imm06'
import StatusBadge from '@/components/common/StatusBadge.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'
import { formatDate } from '@/utils/docUtils'

const router = useRouter()
const store  = useImm06Store()

const filters = ref({ status: '', dept: '', asset: '' })

const STATUS_OPTIONS = [
  { value: '',                   label: 'Tất cả trạng thái' },
  { value: 'Draft',              label: 'Nháp' },
  { value: 'Training Scheduled', label: 'Đã lên lịch đào tạo' },
  { value: 'Training Completed', label: 'Đào tạo hoàn thành' },
  { value: 'Handover Pending',   label: 'Chờ bàn giao' },
  { value: 'Handed Over',        label: 'Đã bàn giao' },
  { value: 'Cancelled',          label: 'Đã hủy' },
]

function applyFilters() {
  store.fetchList({
    status: filters.value.status || undefined,
    dept:   filters.value.dept   || undefined,
    asset:  filters.value.asset  || undefined,
    page: 1,
  })
}

function resetFilters() {
  filters.value = { status: '', dept: '', asset: '' }
  store.fetchList({ page: 1 })
}

function goPage(p: number) {
  store.fetchList({
    status: filters.value.status || undefined,
    dept:   filters.value.dept   || undefined,
    asset:  filters.value.asset  || undefined,
    page: p,
  })
}

onMounted(async () => {
  store.fetchStats()
  store.fetchList({ page: 1 })
})
</script>

<template>
  <div class="page-container animate-fade-in">

    <!-- Header -->
    <div class="flex items-start justify-between mb-7">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-06</p>
        <h1 class="text-2xl font-bold text-slate-900">Bàn giao & Đào tạo</h1>
        <p class="text-sm text-slate-500 mt-1">Quản lý phiếu bàn giao thiết bị cho khoa lâm sàng và lịch đào tạo</p>
      </div>
      <router-link to="/handover/create" class="btn-primary shrink-0">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
        </svg>
        Tạo phiếu mới
      </router-link>
    </div>

    <!-- Stats bar -->
    <div v-if="store.stats" class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
      <div class="card animate-slide-up" style="animation-delay:0ms">
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">Chờ bàn giao</p>
        <p class="text-2xl font-bold text-amber-600">{{ store.stats.total_pending_handover }}</p>
      </div>
      <div class="card animate-slide-up" style="animation-delay:30ms">
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">Đã BG tháng này</p>
        <p class="text-2xl font-bold text-emerald-600">{{ store.stats.completed_this_month }}</p>
      </div>
      <div class="card animate-slide-up" style="animation-delay:60ms">
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">Đang đào tạo</p>
        <p class="text-2xl font-bold text-blue-600">{{ store.stats.training_scheduled }}</p>
      </div>
      <div class="card animate-slide-up" style="animation-delay:90ms">
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">Tỉ lệ đạt ĐT</p>
        <p class="text-2xl font-bold text-slate-900">{{ store.stats.training_pass_rate }}%</p>
      </div>
    </div>

    <!-- Filters -->
    <div class="card mb-6 animate-slide-up" style="animation-delay:100ms">
      <div class="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div class="form-group">
          <label class="form-label">Trạng thái</label>
          <select v-model="filters.status" class="form-select">
            <option v-for="s in STATUS_OPTIONS" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Khoa nhận</label>
          <input v-model="filters.dept" type="text" class="form-input" placeholder="Mã khoa" @keyup.enter="applyFilters" />
        </div>
        <div class="form-group">
          <label class="form-label">Mã thiết bị</label>
          <input v-model="filters.asset" type="text" class="form-input" placeholder="ACC-..." @keyup.enter="applyFilters" />
        </div>
        <div class="flex items-end gap-2">
          <button class="btn-primary" :disabled="store.loading" @click="applyFilters">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            Tìm kiếm
          </button>
          <button class="btn-ghost text-slate-500" @click="resetFilters">Xóa lọc</button>
        </div>
      </div>
    </div>

    <!-- Loading -->
    <SkeletonLoader v-if="store.loading" variant="table" :rows="6" />

    <!-- Error -->
    <div v-else-if="store.error" class="alert-error">
      <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span class="flex-1">{{ store.error }}</span>
      <button class="text-xs font-semibold underline" @click="applyFilters">Thử lại</button>
    </div>

    <!-- Table -->
    <template v-else>
      <div class="table-wrapper animate-slide-up" style="animation-delay:120ms">
        <table class="min-w-full divide-y divide-slate-100">
          <thead>
            <tr>
              <th class="table-header">Mã phiếu</th>
              <th class="table-header">Thiết bị</th>
              <th class="table-header">Khoa nhận</th>
              <th class="table-header">Ngày BG</th>
              <th class="table-header">Loại</th>
              <th class="table-header">Trạng thái</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-slate-100">
            <tr
              v-for="(item, i) in store.hrList"
              :key="item.name"
              class="table-row cursor-pointer animate-fade-in"
              :style="`animation-delay:${i * 25}ms`"
              @click="router.push(`/handover/${item.name}`)"
            >
              <td class="table-cell">
                <span class="font-mono text-[12px] font-semibold text-brand-600">{{ item.name }}</span>
              </td>
              <td class="table-cell">
                <span class="font-mono text-xs text-slate-700">{{ item.asset }}</span>
              </td>
              <td class="table-cell text-sm text-slate-700">{{ item.clinical_dept }}</td>
              <td class="table-cell text-sm text-slate-600">{{ formatDate(item.handover_date) }}</td>
              <td class="table-cell">
                <span class="text-xs font-medium text-slate-600">{{ item.handover_type }}</span>
              </td>
              <td class="px-5 py-3.5"><StatusBadge :state="item.status" /></td>
            </tr>
            <tr v-if="!store.hrList.length">
              <td colspan="6" class="px-5 py-16 text-center">
                <div class="flex flex-col items-center gap-3 text-slate-400">
                  <svg class="w-10 h-10 opacity-25" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <p class="text-sm">Không tìm thấy phiếu bàn giao nào.</p>
                  <router-link to="/handover/create" class="btn-primary text-xs">Tạo phiếu đầu tiên</router-link>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div v-if="store.hrTotalPages > 1"
           class="flex items-center justify-between mt-4 pt-4 border-t border-slate-100">
        <p class="text-xs text-slate-400">
          Trang {{ store.hrPage }}/{{ store.hrTotalPages }} · {{ store.hrTotal }} phiếu
        </p>
        <div class="flex gap-1">
          <button
            class="px-3 py-1.5 rounded-lg text-xs font-semibold border border-slate-200 text-slate-600
                   hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
            :disabled="store.hrPage <= 1"
            @click="goPage(store.hrPage - 1)"
          >‹</button>
          <button
            v-for="p in store.hrTotalPages"
            :key="p"
            class="px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors"
            :class="p === store.hrPage
              ? 'bg-brand-600 text-white border border-brand-600'
              : 'border border-slate-200 text-slate-600 hover:bg-slate-50'"
            @click="goPage(p)"
          >{{ p }}</button>
          <button
            class="px-3 py-1.5 rounded-lg text-xs font-semibold border border-slate-200 text-slate-600
                   hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
            :disabled="store.hrPage >= store.hrTotalPages"
            @click="goPage(store.hrPage + 1)"
          >›</button>
        </div>
      </div>
    </template>
  </div>
</template>
