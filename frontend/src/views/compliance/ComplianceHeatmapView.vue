<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team — IMM-16
// Compliance Heatmap — Module × Department.
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useImm16Store } from '@/stores/imm16'
import PageHeader from '@/components/common/PageHeader.vue'
import SkeletonLoader from '@/components/common/SkeletonLoader.vue'

const router = useRouter()
const store = useImm16Store()

const heatmap = computed(() => store.heatmap)
const loading = ref(false)

const selectedYear = ref<number>(new Date().getFullYear())
const selectedMonth = ref<number>(new Date().getMonth() + 1)

async function load() {
  loading.value = true
  try { await store.fetchHeatmap(selectedYear.value, selectedMonth.value) }
  finally { loading.value = false }
}

function getCell(module: string, dept: string) {
  if (!heatmap.value) return null
  return heatmap.value.matrix.find(c => c.module === module && c.dept === dept) ?? null
}

function moduleLabel(m: string) {
  return heatmap.value?.module_labels?.[m] || m
}
function deptLabel(d: string) {
  return heatmap.value?.department_labels?.[d] || d
}

function cellColor(score: number | undefined | null): string {
  if (score == null) return 'bg-slate-100 text-slate-400'
  if (score >= 90) return 'bg-emerald-600 text-white'
  if (score >= 80) return 'bg-amber-500 text-white'
  if (score >= 70) return 'bg-amber-600 text-white'
  return 'bg-red-600 text-white'
}

function onCellClick(module: string, dept: string) {
  router.push({
    path: '/compliance/findings',
    query: {
      source_module: module,
      responsible_dept: dept,
      period_year: String(selectedYear.value),
      period_month: String(selectedMonth.value),
    },
  })
}

onMounted(load)
</script>

<template>
  <div class="page-container animate-fade-in space-y-5">
    <PageHeader
      title="Bản đồ nhiệt tuân thủ"
      :subtitle="`IMM-16 · Theo dõi tuân thủ — Module × Khoa, kỳ ${String(selectedMonth).padStart(2, '0')}/${selectedYear}`"
      :breadcrumb="[{ label: 'IMM-16 · Theo dõi tuân thủ', to: '/compliance/scorecard' }, { label: 'Bản đồ nhiệt' }]"
    >
      <template #actions>
        <div class="flex items-center gap-2">
          <input v-model.number="selectedYear" type="number" class="form-input text-sm w-24" min="2020" max="2100" />
          <select v-model.number="selectedMonth" class="form-select text-sm">
            <option v-for="m in 12" :key="m" :value="m">Tháng {{ m }}</option>
          </select>
          <button class="btn-primary text-sm" @click="load">Tải dữ liệu</button>
        </div>
      </template>
    </PageHeader>

    <!-- Legend -->
    <div class="card p-4 flex flex-wrap items-center gap-4 text-xs text-slate-600">
      <span class="font-medium text-slate-500">Chú thích:</span>
      <span class="flex items-center gap-1.5"><span class="w-4 h-4 rounded bg-emerald-600 inline-block" /> ≥ 90 (đạt)</span>
      <span class="flex items-center gap-1.5"><span class="w-4 h-4 rounded bg-amber-500 inline-block" /> 80 – 89</span>
      <span class="flex items-center gap-1.5"><span class="w-4 h-4 rounded bg-amber-600 inline-block" /> 70 – 79</span>
      <span class="flex items-center gap-1.5"><span class="w-4 h-4 rounded bg-red-600 inline-block" /> &lt; 70 (kém)</span>
      <span class="ml-auto text-slate-400">Nhấp vào ô để xem các phát hiện liên quan.</span>
    </div>

    <!-- Matrix -->
    <div class="card p-4 overflow-x-auto">
      <div v-if="loading"><SkeletonLoader variant="table" :rows="6" /></div>
      <div v-else-if="!heatmap || !heatmap.modules.length" class="py-12 text-center">
        <p class="text-sm text-slate-500">Chưa có dữ liệu tuân thủ cho kỳ này.</p>
        <p class="text-xs text-slate-400 mt-1">Chọn kỳ khác hoặc đợi đánh giá tuân thủ chạy.</p>
      </div>
      <table v-else class="min-w-full border-separate" style="border-spacing: 4px">
        <thead>
          <tr>
            <th class="text-left t-eyebrow px-2 py-2 sticky left-0 bg-white">Module</th>
            <th
              v-for="dept in heatmap.departments" :key="dept"
              class="text-xs font-medium text-slate-600 px-2 py-2 whitespace-nowrap"
            >
              {{ deptLabel(dept) }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="module in heatmap.modules" :key="module">
            <td class="text-sm font-medium text-slate-800 px-2 py-1 whitespace-nowrap sticky left-0 bg-white">{{ moduleLabel(module) }}</td>
            <td v-for="dept in heatmap.departments" :key="dept">
              <button
                v-if="getCell(module, dept)"
                :class="['w-full min-w-[64px] h-12 rounded font-semibold text-sm tabular-nums transition-all hover:scale-105 hover:shadow-card-hover',
                         cellColor(getCell(module, dept)?.score)]"
                :title="`${moduleLabel(module)} · ${deptLabel(dept)}: ${getCell(module, dept)?.score}% — ${getCell(module, dept)?.findings_count} phát hiện`"
                @click="onCellClick(module, dept)"
              >
                <span>{{ getCell(module, dept)?.score }}</span>
                <span v-if="(getCell(module, dept)?.findings_count ?? 0) > 0" class="text-[10px] block opacity-90">
                  ({{ getCell(module, dept)?.findings_count }})
                </span>
              </button>
              <div v-else class="w-full min-w-[64px] h-12 rounded bg-slate-50 flex items-center justify-center text-slate-300 text-xs">—</div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
