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

function cellColor(score: number | undefined | null): string {
  if (score == null) return 'bg-slate-100 text-slate-400'
  if (score >= 90) return 'bg-emerald-500 text-white'
  if (score >= 80) return 'bg-yellow-400 text-slate-900'
  if (score >= 70) return 'bg-orange-500 text-white'
  return 'bg-red-500 text-white'
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
      :subtitle="`Module × Khoa/Phòng — kỳ ${String(selectedMonth).padStart(2, '0')}/${selectedYear}`"
      :breadcrumb="[{ label: 'IMM-16 · Tuân thủ' }, { label: 'Bản đồ nhiệt' }]"
    >
      <template #actions>
        <div class="flex items-center gap-2">
          <input v-model.number="selectedYear" type="number" class="form-input text-sm w-24" min="2020" max="2100" />
          <select v-model.number="selectedMonth" class="form-select text-sm">
            <option v-for="m in 12" :key="m" :value="m">Tháng {{ m }}</option>
          </select>
          <button class="btn-primary text-sm" @click="load">Tải</button>
        </div>
      </template>
    </PageHeader>

    <!-- Legend -->
    <div class="card p-4 flex flex-wrap items-center gap-4 text-xs text-slate-600">
      <span class="font-medium text-slate-500">Chú thích:</span>
      <span class="flex items-center gap-1.5"><span class="w-4 h-4 rounded bg-emerald-500 inline-block"></span> ≥ 90 (đạt)</span>
      <span class="flex items-center gap-1.5"><span class="w-4 h-4 rounded bg-yellow-400 inline-block"></span> 80 – 89</span>
      <span class="flex items-center gap-1.5"><span class="w-4 h-4 rounded bg-orange-500 inline-block"></span> 70 – 79</span>
      <span class="flex items-center gap-1.5"><span class="w-4 h-4 rounded bg-red-500 inline-block"></span> &lt; 70 (kém)</span>
      <span class="ml-auto text-slate-400">Click ô để xem các phát hiện liên quan</span>
    </div>

    <!-- Matrix -->
    <div class="card p-4 overflow-x-auto">
      <div v-if="loading"><SkeletonLoader variant="table" :rows="6" /></div>
      <div v-else-if="!heatmap || !heatmap.modules.length" class="py-12 text-center text-slate-400 text-sm">
        Không có dữ liệu cho kỳ này.
      </div>
      <table v-else class="min-w-full border-separate" style="border-spacing: 4px">
        <thead>
          <tr>
            <th class="text-left text-xs font-medium text-slate-500 px-2 py-2 sticky left-0 bg-white">Module</th>
            <th v-for="dept in heatmap.departments" :key="dept"
                class="text-xs font-medium text-slate-600 px-2 py-2 whitespace-nowrap">
              {{ dept }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="module in heatmap.modules" :key="module">
            <td class="text-sm font-medium text-slate-700 px-2 py-1 whitespace-nowrap sticky left-0 bg-white">{{ module }}</td>
            <td v-for="dept in heatmap.departments" :key="dept">
              <button
                v-if="getCell(module, dept)"
                :class="['w-full min-w-[64px] h-12 rounded font-semibold text-sm tabular-nums transition-all hover:scale-105 hover:shadow-md',
                         cellColor(getCell(module, dept)?.score)]"
                :title="`${module} · ${dept}: ${getCell(module, dept)?.score}% — ${getCell(module, dept)?.findings_count} findings`"
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
