<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — IMM-15 Spare Forecast list view.
import { onMounted, ref } from 'vue'
import { useImm15Store } from '@/stores/imm15'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'

const store = useImm15Store()
const generating = ref(false)
const approving = ref<string | null>(null)
const horizon = ref(3)
const toast = ref('')

async function load() { await store.fetchForecasts({ page: 1, page_size: 50 }) }

async function generate() {
  generating.value = true
  try {
    const res = await store.generateForecastAction(horizon.value, 'Moving_Avg')
    toast.value = `Đã tạo dự báo ${res.name} (${res.items_count} dòng)`
    await load()
  } catch (e: unknown) {
    toast.value = e instanceof Error ? e.message : String(e)
  } finally {
    generating.value = false
    setTimeout(() => (toast.value = ''), 4000)
  }
}

async function approve(name: string) {
  approving.value = name
  try {
    const res = await store.approveForecastAction(name)
    toast.value = `Đã duyệt: ${res.reorder_recommendations} mục đề xuất đặt hàng`
    await load()
  } catch (e: unknown) {
    toast.value = e instanceof Error ? e.message : String(e)
  } finally {
    approving.value = null
    setTimeout(() => (toast.value = ''), 4000)
  }
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in">
    <PageHeader
      title="Dự báo nhu cầu phụ tùng"
      subtitle="IMM-15 · Tồn kho phụ tùng — Dự báo bằng phương pháp trung bình động"
      :breadcrumb="[{ label: 'IMM-15 · Tồn kho phụ tùng', to: '/inventory/dashboard' }, { label: 'Dự báo' }]"
    >
      <template #actions>
        <div class="flex items-center gap-2">
          <label class="text-sm text-slate-600" for="forecast-horizon">Khoảng dự báo</label>
          <input id="forecast-horizon" v-model.number="horizon" type="number" min="1" max="12" class="w-20 form-input py-1.5 px-2 text-sm" />
          <span class="text-sm text-slate-500">tháng</span>
          <button class="btn-primary" :disabled="generating" @click="generate">
            {{ generating ? 'Đang tạo…' : 'Tạo dự báo' }}
          </button>
        </div>
      </template>
    </PageHeader>

    <div v-if="toast" class="mb-4 px-4 py-3 rounded-lg bg-emerald-50 text-emerald-700 text-sm border border-emerald-100">{{ toast }}</div>

    <div class="card overflow-hidden p-0">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 border-b border-slate-200">
            <tr>
              <th class="table-header">Mã dự báo</th>
              <th class="table-header">Kỳ</th>
              <th class="table-header">Phương pháp</th>
              <th class="table-header">Trạng thái</th>
              <th class="table-header">Người tạo</th>
              <th class="table-header">Người duyệt</th>
              <th class="table-header text-right">Thao tác</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-if="store.forecastsLoading">
              <td colspan="7" class="px-4 py-10 text-center text-slate-400">Đang tải…</td>
            </tr>
            <tr v-else-if="!store.forecasts.length">
              <td colspan="7" class="px-4 py-12 text-center">
                <p class="text-sm text-slate-500">Chưa có dự báo nào.</p>
                <p class="text-xs text-slate-400 mt-1">Nhấn "Tạo dự báo" để bắt đầu phân tích.</p>
              </td>
            </tr>
            <tr v-for="f in store.forecasts" :key="f.name" class="hover:bg-slate-50 transition-colors">
              <td class="px-4 py-3 font-mono text-xs text-brand-700 font-semibold">{{ f.name }}</td>
              <td class="px-4 py-3 text-slate-700">{{ f.forecast_period }}</td>
              <td class="px-4 py-3 text-slate-700">{{ f.method }}</td>
              <td class="px-4 py-3">
                <StatusBadge :state="f.workflow_state || 'Draft'" />
              </td>
              <td class="px-4 py-3 text-slate-700">{{ f.generated_by_name || f.generated_by || '—' }}</td>
              <td class="px-4 py-3 text-slate-700">{{ f.approved_by_name || f.approved_by || '—' }}</td>
              <td class="px-4 py-3 text-right">
                <button
                  v-if="(f.workflow_state || 'Draft') === 'Draft'"
                  class="btn-secondary text-xs py-1.5 px-3"
                  :disabled="approving === f.name"
                  @click="approve(f.name)"
                >
                  {{ approving === f.name ? 'Đang duyệt…' : 'Phê duyệt' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
