<script setup lang="ts">
import { onMounted } from 'vue'
import { useImm14Store } from '@/stores/imm14'
import { useRouter } from 'vue-router'

const store = useImm14Store()
const router = useRouter()

onMounted(() => store.fetchDashboardStats())
</script>

<template>
  <div class="page-container animate-fade-in">
    <!-- Header -->
    <div class="flex items-start justify-between mb-6">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">IMM-14 · Dashboard</p>
        <h1 class="text-2xl font-bold text-slate-900">Tổng quan Lưu trữ Hồ sơ</h1>
      </div>
      <button class="btn-primary shrink-0" @click="router.push('/archive')">
        Xem danh sách hồ sơ
      </button>
    </div>

    <!-- KPI Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
      <div class="bg-white rounded-xl shadow-sm border p-5">
        <div class="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1">Đã lưu trữ (YTD)</div>
        <div class="text-3xl font-bold text-green-600">{{ store.dashboardStats?.archived_ytd ?? '—' }}</div>
        <div class="text-xs text-slate-500 mt-1">Hồ sơ thiết bị được lưu trữ trong năm</div>
      </div>
      <div class="bg-white rounded-xl shadow-sm border p-5">
        <div class="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1">Chờ xác minh</div>
        <div class="text-3xl font-bold text-yellow-600">{{ store.dashboardStats?.pending_verification ?? '—' }}</div>
        <div class="text-xs text-slate-500 mt-1">Hồ sơ đang chờ QA xác minh</div>
      </div>
      <div class="bg-white rounded-xl shadow-sm border p-5">
        <div class="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1">Tổng đã lưu trữ</div>
        <div class="text-3xl font-bold text-slate-900">{{ store.dashboardStats?.total_archived_all_time ?? '—' }}</div>
        <div class="text-xs text-slate-500 mt-1">Toàn bộ hồ sơ thiết bị đã lưu trữ</div>
      </div>
    </div>

    <!-- Quick links -->
    <div class="bg-white rounded-xl shadow-sm border p-6">
      <h2 class="font-semibold text-slate-900 mb-4 text-sm uppercase tracking-wide">Hành động nhanh</h2>
      <div class="flex flex-wrap gap-3">
        <button
          class="px-4 py-2.5 bg-blue-50 text-blue-700 rounded-lg text-sm font-medium hover:bg-blue-100 transition-colors border border-blue-200"
          @click="router.push('/archive?status=Compiling')"
        >
          Hồ sơ đang tổng hợp
        </button>
        <button
          class="px-4 py-2.5 bg-yellow-50 text-yellow-700 rounded-lg text-sm font-medium hover:bg-yellow-100 transition-colors border border-yellow-200"
          @click="router.push('/archive?status=Pending+Verification')"
        >
          Chờ xác minh QA
        </button>
        <button
          class="px-4 py-2.5 bg-orange-50 text-orange-700 rounded-lg text-sm font-medium hover:bg-orange-100 transition-colors border border-orange-200"
          @click="router.push('/archive?status=Pending+Approval')"
        >
          Chờ phê duyệt HTM
        </button>
        <button
          class="px-4 py-2.5 bg-green-50 text-green-700 rounded-lg text-sm font-medium hover:bg-green-100 transition-colors border border-green-200"
          @click="router.push('/archive?status=Archived')"
        >
          Hồ sơ đã lưu trữ
        </button>
      </div>
    </div>

    <div v-if="store.error" class="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
      {{ store.error }}
    </div>
  </div>
</template>
