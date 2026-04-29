<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// Inventory Dashboard — tổng quan kho vật tư
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getInventoryOverview } from '@/api/inventory'
import type { InventoryOverview } from '@/types/inventory'

const router = useRouter()
const overview = ref<InventoryOverview | null>(null)
const loading = ref(false)

async function load() {
  loading.value = true
  try { overview.value = await getInventoryOverview() }
  finally { loading.value = false }
}

function vnd(v?: number) {
  if (v == null) return '—'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(v)
}
function vndShort(v?: number) {
  if (v == null) return '—'
  if (Math.abs(v) >= 1e9) return (v / 1e9).toFixed(1) + ' tỷ'
  if (Math.abs(v) >= 1e6) return (v / 1e6).toFixed(0) + ' tr'
  return vnd(v)
}

const MOVEMENT_LABELS: Record<string, string> = {
  Receipt: 'Nhập', Issue: 'Xuất', Transfer: 'Chuyển', Adjustment: 'Điều chỉnh',
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in">
    <!-- Header -->
    <div class="flex items-start justify-between mb-6">
      <div>
        <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">Inventory</p>
        <h1 class="text-2xl font-bold text-slate-900">Tổng quan kho</h1>
        <p class="text-sm text-slate-500 mt-1">Danh mục phụ tùng, tồn kho, và giao dịch kho toàn hệ thống</p>
      </div>
      <div class="flex gap-2">
        <button class="btn-secondary" @click="router.push('/stock-movements/new')">+ Phiếu mới</button>
        <button class="btn-primary" @click="router.push('/spare-parts')">Danh mục phụ tùng</button>
      </div>
    </div>

    <div v-if="loading && !overview" class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <div v-for="i in 4" :key="i" class="card p-5 h-24 animate-pulse bg-slate-100" />
    </div>

    <div v-else-if="overview">
      <!-- KPI Cards -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div class="card p-5 hover:shadow-md cursor-pointer transition-shadow" @click="router.push('/spare-parts')">
          <p class="text-xs font-medium text-slate-500 mb-1">Phụ tùng đang hoạt động</p>
          <p class="text-2xl font-bold text-slate-900">{{ overview.total_parts }}</p>
          <p class="text-xs text-slate-400 mt-1">đang quản lý trong catalog</p>
        </div>
        <div class="card p-5 hover:shadow-md cursor-pointer transition-shadow" @click="router.push('/warehouses')">
          <p class="text-xs font-medium text-slate-500 mb-1">IMM Storekeeper</p>
          <p class="text-2xl font-bold text-slate-900">{{ overview.total_warehouses }}</p>
          <p class="text-xs text-slate-400 mt-1">đang hoạt động</p>
        </div>
        <div class="card p-5 hover:shadow-md cursor-pointer transition-shadow" @click="router.push('/stock')">
          <p class="text-xs font-medium text-slate-500 mb-1">Tổng giá trị tồn</p>
          <p class="text-2xl font-bold text-emerald-600">{{ vndShort(overview.total_value) }}</p>
          <p class="text-xs text-slate-400 mt-1">theo đơn giá catalog</p>
        </div>
        <div
class="card p-5 hover:shadow-md cursor-pointer transition-shadow"
             :class="overview.low_stock_count > 0 ? 'ring-2 ring-red-200' : ''"
             @click="router.push('/stock?low=1')">
          <p class="text-xs font-medium text-slate-500 mb-1">Cảnh báo tồn thấp</p>
          <p class="text-2xl font-bold" :class="overview.low_stock_count > 0 ? 'text-red-600' : 'text-slate-900'">
            {{ overview.low_stock_count }}
          </p>
          <p class="text-xs text-slate-400 mt-1">phụ tùng dưới mức min</p>
        </div>
      </div>

      <!-- Grid: Low stock + Movements 30d -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-6">
        <!-- Low stock alerts -->
        <div class="card p-5">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-sm font-semibold text-slate-700">Phụ tùng tồn thấp</h3>
            <button class="text-xs text-blue-600 hover:text-blue-800" @click="router.push('/stock?low=1')">
              Xem tất cả →
            </button>
          </div>
          <div
v-if="overview.low_stock_items.length === 0"
               class="text-center py-8 text-sm text-slate-400">
            Không có phụ tùng nào dưới mức min
          </div>
          <div v-else class="space-y-2.5">
            <div
v-for="item in overview.low_stock_items" :key="item.spare_part"
                 class="flex items-center justify-between p-3 bg-red-50 rounded-lg border border-red-100 cursor-pointer hover:bg-red-100"
                 @click="router.push(`/spare-parts/${item.spare_part}`)">
              <div>
                <p class="text-sm font-medium text-slate-800">{{ item.part_name }}</p>
                <p class="text-xs text-slate-500 font-mono">{{ item.spare_part }}</p>
              </div>
              <div class="text-right">
                <p class="text-sm font-bold text-red-700">{{ item.total_qty }} / {{ item.min_stock_level }}</p>
                <p class="text-[10px] text-red-500">thiếu {{ item.min_stock_level - item.total_qty }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Movements 30 days -->
        <div class="card p-5">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-sm font-semibold text-slate-700">Giao dịch 30 ngày gần nhất</h3>
            <button class="text-xs text-blue-600 hover:text-blue-800" @click="router.push('/stock-movements')">
              Xem tất cả →
            </button>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div
v-for="(cnt, type) in overview.movement_30d" :key="type"
                 class="p-4 bg-slate-50 rounded-lg">
              <p class="text-xs text-slate-500">{{ MOVEMENT_LABELS[type as string] || type }}</p>
              <p class="text-2xl font-bold text-slate-900 mt-1">{{ cnt }}</p>
              <p class="text-[10px] text-slate-400">phiếu</p>
            </div>
          </div>
          <div
v-if="Object.keys(overview.movement_30d).length === 0"
               class="text-center py-8 text-sm text-slate-400">
            Chưa có giao dịch nào trong 30 ngày
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
