<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// IMM-00 — Panel "Khấu hao theo danh mục" (quản lý tập trung theo Danh mục tài sản).
// Gom mỗi Danh mục → tổng nguyên giá / lũy kế / còn lại / số TS / độ phủ cấu hình,
// biểu đồ cột chồng (lũy kế vs còn lại), drill xuống tài sản + áp dụng luật khấu hao.
import { ref, computed, onMounted } from 'vue'
import {
  getDepreciationByCategory, bulkRegenerateScheduleByCategory,
  type DepreciationCategoryRow, type DepreciationByCategoryResult,
  type BulkRegenerateResult,
} from '@/api/imm00'
import { formatCurrencyShort as vndShort } from '@/utils/formatters'

const emit = defineEmits<{
  // Drill: parent chuyển sang danh sách thiết bị + lọc theo danh mục này.
  (e: 'drill', payload: { categoryId: string; category: string }): void
  // Đã áp dụng luật khấu hao cho 1 danh mục → parent refresh KPI tổng.
  (e: 'applied'): void
}>()

const rows = ref<DepreciationCategoryRow[]>([])
const totals = ref<DepreciationByCategoryResult['totals'] | null>(null)
const loading = ref(false)
const applying = ref<string | null>(null)
const applyResult = ref<(BulkRegenerateResult & { _category: string }) | null>(null)
const toast = ref('')
const toastOk = ref(true)

async function load() {
  loading.value = true
  try {
    const res = await getDepreciationByCategory()
    rows.value = res?.categories || []
    totals.value = res?.totals || null
  } finally {
    loading.value = false
  }
}

// Biểu đồ cột chồng: chuẩn hoá theo nguyên giá LỚN NHẤT để so trực quan giữa danh mục.
const maxGross = computed(() =>
  Math.max(...rows.value.map(r => r.total_gross), 1),
)
function widthPct(v: number) {
  return `${Math.min(100, Math.round((v / maxGross.value) * 100))}%`
}
// Trong 1 thanh: tỉ lệ phần lũy kế vs còn lại (theo nguyên giá của chính danh mục).
function accPct(r: DepreciationCategoryRow) {
  return r.total_gross > 0 ? Math.round((r.total_accumulated / r.total_gross) * 100) : 0
}

function drill(r: DepreciationCategoryRow) {
  emit('drill', { categoryId: r.category_id, category: r.category })
}

async function applyRules(r: DepreciationCategoryRow) {
  if (!r.category_id) return
  applying.value = r.category_id
  try {
    const res = await bulkRegenerateScheduleByCategory(r.category_id)
    applyResult.value = { ...res, _category: r.category }
    showToast(
      `Áp dụng luật cho "${r.category}": kế thừa ${res.inherited} · sinh ${res.regenerated} lịch · ` +
      `giữ lịch sử ${res.skipped_has_history} · thiếu luật ${res.skipped_no_rule}`,
      res.errors === 0,
    )
    await load()
    emit('applied')
  } catch (e: unknown) {
    showToast((e as Error).message || 'Lỗi áp dụng luật khấu hao', false)
  } finally {
    applying.value = null
  }
}

function showToast(msg: string, ok: boolean) {
  toast.value = msg
  toastOk.value = ok
  setTimeout(() => { toast.value = '' }, 4500)
}

onMounted(load)
defineExpose({ reload: load })
</script>

<template>
  <div>
    <Transition name="fade">
      <div
        v-if="toast"
        :class="['mb-4 px-4 py-3 rounded-lg text-sm font-medium', toastOk ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-red-50 text-red-700 border border-red-200']">
        {{ toast }}
      </div>
    </Transition>

    <!-- Biểu đồ cột chồng: lũy kế (hổ phách) vs còn lại (ngọc lục) theo danh mục -->
    <div v-if="rows.length" class="card p-5 mb-4">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-sm font-semibold text-slate-700">Giá trị theo danh mục</h3>
        <div class="flex items-center gap-4 text-xs">
          <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-sm bg-amber-500" />Đã khấu hao</span>
          <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-sm bg-emerald-500" />Còn lại</span>
        </div>
      </div>
      <div class="space-y-3">
        <div v-for="r in rows" :key="r.category_id || r.category" data-testid="depr-cat-bar">
          <div class="flex justify-between text-xs mb-1">
            <span class="text-slate-600 truncate max-w-[220px]" :title="r.category">{{ r.category }}</span>
            <span class="font-medium text-slate-700 shrink-0 ml-1">{{ vndShort(r.total_gross) }}</span>
          </div>
          <div class="h-3 bg-slate-100 rounded-full overflow-hidden" :style="`width:${widthPct(r.total_gross)}`">
            <div class="flex h-full">
              <div class="h-full bg-amber-500" :style="`width:${accPct(r)}%`" />
              <div class="h-full bg-emerald-500" :style="`width:${100 - accPct(r)}%`" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Bảng quản lý theo danh mục -->
    <div class="card overflow-hidden">
      <div v-if="loading && !rows.length" class="text-center text-slate-400 py-12">Đang tải...</div>
      <div v-else-if="!rows.length" class="text-center text-slate-400 py-12 text-sm">Không có dữ liệu.</div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 border-b border-slate-100">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-semibold text-slate-500">Danh mục</th>
              <th class="px-4 py-3 text-right text-xs font-semibold text-slate-500">Số thiết bị</th>
              <th class="px-4 py-3 text-right text-xs font-semibold text-slate-500 hidden md:table-cell">Đã cấu hình</th>
              <th class="px-4 py-3 text-right text-xs font-semibold text-slate-500">Nguyên giá</th>
              <th class="px-4 py-3 text-right text-xs font-semibold text-slate-500 hidden md:table-cell">Khấu hao lũy kế</th>
              <th class="px-4 py-3 text-right text-xs font-semibold text-slate-500">Giá trị còn lại</th>
              <th class="px-4 py-3 text-left text-xs font-semibold text-slate-500">Tiến độ khấu hao</th>
              <th class="px-4 py-3" />
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-50">
            <tr v-for="r in rows" :key="r.category_id || r.category" data-testid="depr-cat-row" class="hover:bg-slate-50/70">
              <td class="px-4 py-3">
                <p class="font-medium text-slate-800">{{ r.category }}</p>
                <p v-if="r.fully_depreciated" class="text-[11px] text-slate-400">
                  {{ r.fully_depreciated }} thiết bị hết khấu hao
                </p>
              </td>
              <td class="px-4 py-3 text-right font-medium text-slate-700">{{ r.asset_count }}</td>
              <td class="px-4 py-3 text-right text-slate-500 hidden md:table-cell">
                {{ r.configured_count }}<span class="text-slate-300">/{{ r.asset_count }}</span>
              </td>
              <td class="px-4 py-3 text-right font-medium text-slate-700">{{ vndShort(r.total_gross) }}</td>
              <td class="px-4 py-3 text-right text-amber-600 hidden md:table-cell">{{ vndShort(r.total_accumulated) }}</td>
              <td class="px-4 py-3 text-right font-semibold text-emerald-700">{{ vndShort(r.total_book_value) }}</td>
              <td class="px-4 py-3">
                <div class="min-w-[120px] flex items-center gap-2">
                  <div class="flex-1 h-1.5 bg-slate-100 rounded-full">
                    <div class="h-1.5 rounded-full bg-amber-500" :style="`width:${Math.min(100, r.pct_depreciated)}%`" />
                  </div>
                  <span class="text-xs text-slate-500 w-10 shrink-0">{{ r.pct_depreciated }}%</span>
                </div>
              </td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-3 justify-end">
                  <button
                    type="button"
                    data-testid="depr-cat-drill"
                    class="text-xs text-slate-500 hover:text-blue-600 font-medium transition-colors"
                    @click="drill(r)">
                    Xem thiết bị
                  </button>
                  <button
                    v-if="r.category_id"
                    type="button"
                    data-testid="depr-cat-apply"
                    class="text-xs text-blue-600 hover:text-blue-800 font-medium disabled:opacity-40"
                    :disabled="applying === r.category_id"
                    @click="applyRules(r)">
                    {{ applying === r.category_id ? 'Đang áp dụng...' : 'Áp dụng luật' }}
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
          <tfoot v-if="totals" class="bg-slate-50 border-t border-slate-200">
            <tr class="font-semibold text-slate-700">
              <td class="px-4 py-3">Tổng cộng</td>
              <td class="px-4 py-3 text-right">{{ totals.total_assets }}</td>
              <td class="px-4 py-3 hidden md:table-cell" />
              <td class="px-4 py-3 text-right">{{ vndShort(totals.total_gross) }}</td>
              <td class="px-4 py-3 text-right text-amber-600 hidden md:table-cell">{{ vndShort(totals.total_accumulated) }}</td>
              <td class="px-4 py-3 text-right text-emerald-700">{{ vndShort(totals.total_book_value) }}</td>
              <td class="px-4 py-3 text-left text-xs text-slate-500">{{ totals.overall_pct }}% đã khấu hao</td>
              <td class="px-4 py-3" />
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
