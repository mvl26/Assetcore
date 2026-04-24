<script setup lang="ts">
import { onMounted } from 'vue'
import { useImm13Store } from '@/stores/imm13'
import { useRouter } from 'vue-router'

const store = useImm13Store()
const router = useRouter()

onMounted(() => {
  store.fetchMetrics()
  store.fetchRetirementCandidates()
})
</script>

<template>
  <div class="page-container animate-fade-in">
    <!-- Header -->
    <div class="flex items-start justify-between mb-6">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-13 · Dashboard</p>
        <h1 class="text-2xl font-bold text-slate-900">Tổng quan Ngừng sử dụng & Điều chuyển</h1>
      </div>
      <button class="btn-primary shrink-0" @click="router.push('/decommission/create')">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
        </svg>
        Tạo phiếu
      </button>
    </div>

    <!-- KPI Cards -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <div class="bg-white rounded-xl shadow-sm border p-5">
        <div class="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1">Đã ngừng (YTD)</div>
        <div class="text-3xl font-bold text-slate-900">{{ store.metrics?.suspended_ytd ?? '—' }}</div>
        <div class="text-xs text-slate-500 mt-1">Thiết bị tạm ngừng / thanh lý</div>
      </div>
      <div class="bg-white rounded-xl shadow-sm border p-5">
        <div class="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1">Đã điều chuyển (YTD)</div>
        <div class="text-3xl font-bold text-emerald-600">{{ store.metrics?.transferred_ytd ?? '—' }}</div>
        <div class="text-xs text-slate-500 mt-1">Thiết bị điều chuyển đơn vị</div>
      </div>
      <div class="bg-white rounded-xl shadow-sm border p-5">
        <div class="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1">Chờ phê duyệt</div>
        <div class="text-3xl font-bold text-red-600">{{ store.metrics?.pending_approval_count ?? '—' }}</div>
        <div class="text-xs text-slate-500 mt-1">Phiếu chờ HTM Manager duyệt</div>
      </div>
      <div class="bg-white rounded-xl shadow-sm border p-5">
        <div class="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1">Ứng viên thanh lý</div>
        <div class="text-3xl font-bold text-orange-500">{{ store.metrics?.retirement_candidates_count ?? '—' }}</div>
        <div class="text-xs text-slate-500 mt-1">Thiết bị được đề xuất thanh lý</div>
      </div>
    </div>

    <!-- Open by state -->
    <div v-if="store.metrics?.open_by_state && Object.keys(store.metrics.open_by_state).length" class="bg-white rounded-xl shadow-sm border p-5 mb-8">
      <h2 class="font-semibold text-slate-700 mb-3 text-sm uppercase tracking-wide">Phiếu đang mở theo trạng thái</h2>
      <div class="flex flex-wrap gap-3">
        <div
          v-for="(count, state) in store.metrics.open_by_state"
          :key="state"
          class="flex items-center gap-2 px-3 py-2 bg-slate-50 rounded-lg border text-sm"
        >
          <span class="font-semibold text-slate-900">{{ count }}</span>
          <span class="text-slate-600">{{ state }}</span>
        </div>
      </div>
    </div>

    <!-- Retirement Candidates table -->
    <div class="bg-white rounded-xl shadow-sm border overflow-hidden">
      <div class="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
        <h2 class="font-semibold text-slate-900">Ứng viên Thanh lý</h2>
        <button class="text-sm text-blue-600 hover:text-blue-800" @click="router.push('/decommission')">
          Xem tất cả phiếu →
        </button>
      </div>

      <div v-if="store.retirementCandidates.length === 0" class="py-10 text-center text-slate-400">
        <p class="text-sm">Không có thiết bị nào được đề xuất thanh lý</p>
      </div>

      <table v-else class="min-w-full divide-y divide-slate-100">
        <thead>
          <tr>
            <th class="table-header">Thiết bị</th>
            <th class="table-header">Trạng thái</th>
            <th class="table-header">Lý do đề xuất</th>
            <th class="table-header">Ngày đề xuất</th>
            <th class="table-header">Thao tác</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-50">
          <tr v-for="c in store.retirementCandidates" :key="c.name" class="hover:bg-slate-50">
            <td class="table-cell">
              <div class="font-medium text-slate-900">{{ c.asset_name || c.name }}</div>
              <div class="text-xs text-slate-400 font-mono">{{ c.name }}</div>
            </td>
            <td class="table-cell">
              <span class="px-2 py-0.5 rounded-full text-xs bg-orange-100 text-orange-700 font-medium">{{ c.status }}</span>
            </td>
            <td class="table-cell text-sm text-slate-600">{{ c.retirement_flag_reason || '—' }}</td>
            <td class="table-cell text-sm text-slate-500">{{ c.retirement_flagged_date?.slice(0, 10) || '—' }}</td>
            <td class="table-cell">
              <button
                class="text-sm text-blue-600 hover:text-blue-800 font-medium"
                @click="router.push('/decommission/create')"
              >
                Tạo phiếu
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
