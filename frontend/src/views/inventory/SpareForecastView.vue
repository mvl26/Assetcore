<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — IMM-15 Spare Forecast list view.
import { onMounted, ref } from 'vue'
import { useImm15Store } from '@/stores/imm15'
import { useNotify } from '@/composables/useNotify'
import { MSG } from '@/locales/messages'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'

const store = useImm15Store()
const notify = useNotify()
const generating = ref(false)
const approving = ref<string | null>(null)
const horizon = ref(3)

async function load() { await store.fetchForecasts({ page: 1, page_size: 50 }) }

async function generate() {
  generating.value = true
  try {
    const res = await store.generateForecastAction(horizon.value, 'Moving_Avg')
    notify.show({ code: MSG.UI_SAVE_SUCCESS, ctx: { entity: `dự báo ${res.name} (${res.items_count} dòng)` } })
  } catch (e: unknown) {
    notify.fromError(e)
  } finally {
    generating.value = false
  }
}

// Duyệt dự báo — lái theo state THỰC server trả (store.approveForecastAction chỉ
// trả kết quả khi workflow_state === 'Approved'; ngược lại null + set lastApiError).
// KHÔNG toast thành-công-giả: chỉ báo thành công khi có kết quả, còn lại surface
// message server (notify contract). Row đã được store refetch từ state THỰC.
async function approve(name: string) {
  approving.value = name
  const res = await store.approveForecastAction(name)
  approving.value = null
  if (res) {
    notify.show({ code: MSG.UI_SAVE_SUCCESS, ctx: { entity: `dự báo ${res.name}` } })
  } else {
    notify.fromError(store.lastApiError)
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
            <tr v-else-if="store.error">
              <td colspan="7" class="px-4 py-10 text-center">
                <p class="text-sm text-rose-600" data-testid="forecast-list-error">{{ store.error }}</p>
                <button class="btn-secondary text-xs py-1.5 px-3 mt-3" @click="load">Thử lại</button>
              </td>
            </tr>
            <tr v-else-if="!store.forecasts.length">
              <td colspan="7" class="px-4 py-12 text-center">
                <p class="text-sm text-slate-500">Chưa có dự báo nào.</p>
                <p class="text-xs text-slate-400 mt-1">Nhấn "Tạo dự báo" để bắt đầu phân tích.</p>
              </td>
            </tr>
            <tr
              v-for="f in store.forecasts"
              :key="f.name"
              :data-testid="`forecast-row-${f.name}`"
              class="hover:bg-slate-50 transition-colors"
            >
              <td class="px-4 py-3 font-mono text-xs text-brand-700 font-semibold">{{ f.name }}</td>
              <td class="px-4 py-3 text-slate-700">{{ f.forecast_period }}</td>
              <td class="px-4 py-3 text-slate-700">{{ f.method }}</td>
              <td class="px-4 py-3" :data-testid="`forecast-status-${f.name}`">
                <StatusBadge :state="f.workflow_state || 'Draft'" />
              </td>
              <td class="px-4 py-3 text-slate-700">{{ f.generated_by_name || f.generated_by || '—' }}</td>
              <td class="px-4 py-3 text-slate-700">{{ f.approved_by_name || f.approved_by || '—' }}</td>
              <td class="px-4 py-3 text-right">
                <!-- Gate CTA 'Duyệt' chỉ hiện cho dòng Bản nháp (ẩn khi đã duyệt) —
                     tránh round-trip BAD_STATE. -->
                <button
                  v-if="(f.workflow_state || 'Draft') === 'Draft'"
                  :data-testid="`forecast-approve-${f.name}`"
                  :aria-label="`Duyệt dự báo ${f.name}`"
                  class="btn-secondary text-xs py-1.5 px-3 focus-visible:ring-2 focus-visible:ring-emerald-500"
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
