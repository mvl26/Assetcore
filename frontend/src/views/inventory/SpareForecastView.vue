<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — IMM-15 Spare Forecast list view.
import { onMounted, ref } from 'vue'
import { useImm15Store } from '@/stores/imm15'
import PageHeader from '@/components/common/PageHeader.vue'

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
    toast.value = `Đã tạo forecast ${res.name} (${res.items_count} dòng)`
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
    <PageHeader title="Dự báo phụ tùng" subtitle="IMM-15 — Spare Part Forecast (Moving Avg)">
      <template #actions>
        <div class="flex items-center gap-2">
          <label class="text-sm text-slate-600">Horizon</label>
          <input v-model.number="horizon" type="number" min="1" max="12" class="w-16 px-2 py-1 border rounded text-sm" />
          <span class="text-sm text-slate-600">tháng</span>
          <button class="btn-primary" :disabled="generating" @click="generate">
            {{ generating ? 'Đang tạo...' : 'Tạo forecast mới' }}
          </button>
        </div>
      </template>
    </PageHeader>

    <div v-if="toast" class="mb-3 p-3 bg-blue-50 text-blue-800 rounded text-sm">{{ toast }}</div>

    <div class="card overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-slate-50">
          <tr>
            <th class="px-3 py-2 text-left">Mã</th>
            <th class="px-3 py-2 text-left">Kỳ</th>
            <th class="px-3 py-2 text-left">Phương pháp</th>
            <th class="px-3 py-2 text-left">Trạng thái</th>
            <th class="px-3 py-2 text-left">Người tạo</th>
            <th class="px-3 py-2 text-left">Người duyệt</th>
            <th class="px-3 py-2"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="store.forecastsLoading">
            <td colspan="7" class="px-3 py-6 text-center text-slate-500">Đang tải...</td>
          </tr>
          <tr v-else-if="!store.forecasts.length">
            <td colspan="7" class="px-3 py-8 text-center text-slate-500">
              Chưa có forecast. Nhấn "Tạo forecast mới" để bắt đầu.
            </td>
          </tr>
          <tr v-for="f in store.forecasts" :key="f.name" class="border-t hover:bg-slate-50">
            <td class="px-3 py-2 font-mono text-xs">{{ f.name }}</td>
            <td class="px-3 py-2">{{ f.forecast_period }}</td>
            <td class="px-3 py-2">{{ f.method }}</td>
            <td class="px-3 py-2">
              <span class="badge" :class="f.workflow_state === 'Approved' ? 'badge-success' : 'badge-warning'">
                {{ f.workflow_state || 'Draft' }}
              </span>
            </td>
            <td class="px-3 py-2">{{ f.generated_by_name || f.generated_by || '—' }}</td>
            <td class="px-3 py-2">{{ f.approved_by_name || f.approved_by || '—' }}</td>
            <td class="px-3 py-2 text-right">
              <button v-if="(f.workflow_state || 'Draft') === 'Draft'"
                      class="btn-secondary text-xs"
                      :disabled="approving === f.name"
                      @click="approve(f.name)">
                {{ approving === f.name ? '...' : 'Duyệt' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.badge { display: inline-block; padding: 0.125rem 0.5rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 500 }
.badge-success { background: #dcfce7; color: #166534 }
.badge-warning { background: #fef3c7; color: #92400e }
</style>
