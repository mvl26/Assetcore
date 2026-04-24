<script setup lang="ts">
import { computed } from 'vue'
import type { VendorEvaluationItem } from '@/api/imm03'

const props = defineProps<{
  items: VendorEvaluationItem[]
  editable: boolean
  recommended_vendor?: string
}>()

const emit = defineEmits<{
  'update:items': [items: VendorEvaluationItem[]]
}>()

function calcScore(item: VendorEvaluationItem): number {
  return Math.round(
    (item.technical_score * 0.4 + item.financial_score * 0.3 + item.profile_score * 0.2 + item.risk_score * 0.1) * 100,
  ) / 100
}

function calcBand(score: number): string {
  if (score >= 8) return 'A'
  if (score >= 6) return 'B'
  if (score >= 4) return 'C'
  return 'D'
}

const enrichedItems = computed(() =>
  props.items.map(item => ({
    ...item,
    total_score: calcScore(item),
    score_band: calcBand(calcScore(item)),
  })),
)

const maxScore = computed(() =>
  enrichedItems.value.reduce((max, item) => Math.max(max, item.total_score ?? 0), 0),
)

function bandColor(band: string): string {
  switch (band) {
    case 'A': return 'bg-emerald-100 text-emerald-700'
    case 'B': return 'bg-blue-100 text-blue-700'
    case 'C': return 'bg-amber-100 text-amber-700'
    default:  return 'bg-red-100 text-red-700'
  }
}

function updateField(index: number, field: keyof VendorEvaluationItem, value: unknown) {
  const updated = props.items.map((item, i) => {
    if (i !== index) return item
    const next = { ...item, [field]: value }
    next.total_score = calcScore(next)
    next.score_band  = calcBand(next.total_score)
    return next
  })
  emit('update:items', updated)
}

function isTopScorer(item: VendorEvaluationItem & { total_score: number }): boolean {
  return item.total_score === maxScore.value && maxScore.value > 0
}
</script>

<template>
  <div class="overflow-x-auto">
    <table class="min-w-full text-sm">
      <thead>
        <tr class="border-b border-slate-200">
          <th class="table-header text-left">Nhà cung cấp</th>
          <th class="table-header text-right">Báo giá</th>
          <th class="table-header text-center">KT<br><span class="text-[10px] font-normal text-slate-400">(×0.4)</span></th>
          <th class="table-header text-center">TC<br><span class="text-[10px] font-normal text-slate-400">(×0.3)</span></th>
          <th class="table-header text-center">NL<br><span class="text-[10px] font-normal text-slate-400">(×0.2)</span></th>
          <th class="table-header text-center">RR<br><span class="text-[10px] font-normal text-slate-400">(×0.1)</span></th>
          <th class="table-header text-center">Tổng</th>
          <th class="table-header text-center">Band</th>
          <th class="table-header text-center">ND98</th>
          <th class="table-header text-center">TS</th>
          <th v-if="editable" class="table-header" />
        </tr>
      </thead>
      <tbody class="divide-y divide-slate-100">
        <tr
          v-for="(item, i) in enrichedItems"
          :key="item.vendor || i"
          :class="[
            'transition-colors',
            isTopScorer(item) ? 'bg-emerald-50' : 'hover:bg-slate-50',
            recommended_vendor && item.vendor === recommended_vendor ? 'ring-1 ring-inset ring-emerald-300' : '',
          ]"
        >
          <!-- Vendor name -->
          <td class="table-cell font-medium text-slate-800">
            <div class="flex items-center gap-1.5">
              <span v-if="recommended_vendor && item.vendor === recommended_vendor"
                    class="text-amber-500" title="NCC được đề xuất">★</span>
              <span v-else-if="isTopScorer(item)"
                    class="text-emerald-500" title="Điểm cao nhất">★</span>
              {{ item.vendor_name || item.vendor }}
            </div>
          </td>

          <!-- Quoted price -->
          <td class="table-cell text-right text-slate-600 text-xs">
            <template v-if="editable">
              <input
                type="number"
                min="0"
                step="1000000"
                class="form-input text-right text-xs py-1 w-28"
                :value="item.quoted_price ?? ''"
                @input="updateField(i, 'quoted_price', ($event.target as HTMLInputElement).valueAsNumber || null)"
              />
            </template>
            <template v-else>
              {{ item.quoted_price
                  ? new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 }).format(item.quoted_price)
                  : '—' }}
            </template>
          </td>

          <!-- Technical score -->
          <td class="table-cell text-center">
            <input
              v-if="editable"
              type="number" min="0" max="10" step="0.1"
              class="form-input text-center text-sm py-1 w-16"
              :value="item.technical_score"
              @input="updateField(i, 'technical_score', Math.min(10, Math.max(0, Number(($event.target as HTMLInputElement).value))))"
            />
            <span v-else class="font-mono font-semibold">{{ item.technical_score }}</span>
          </td>

          <!-- Financial score -->
          <td class="table-cell text-center">
            <input
              v-if="editable"
              type="number" min="0" max="10" step="0.1"
              class="form-input text-center text-sm py-1 w-16"
              :value="item.financial_score"
              @input="updateField(i, 'financial_score', Math.min(10, Math.max(0, Number(($event.target as HTMLInputElement).value))))"
            />
            <span v-else class="font-mono font-semibold">{{ item.financial_score }}</span>
          </td>

          <!-- Profile score -->
          <td class="table-cell text-center">
            <input
              v-if="editable"
              type="number" min="0" max="10" step="0.1"
              class="form-input text-center text-sm py-1 w-16"
              :value="item.profile_score"
              @input="updateField(i, 'profile_score', Math.min(10, Math.max(0, Number(($event.target as HTMLInputElement).value))))"
            />
            <span v-else class="font-mono font-semibold">{{ item.profile_score }}</span>
          </td>

          <!-- Risk score -->
          <td class="table-cell text-center">
            <input
              v-if="editable"
              type="number" min="0" max="10" step="0.1"
              class="form-input text-center text-sm py-1 w-16"
              :value="item.risk_score"
              @input="updateField(i, 'risk_score', Math.min(10, Math.max(0, Number(($event.target as HTMLInputElement).value))))"
            />
            <span v-else class="font-mono font-semibold">{{ item.risk_score }}</span>
          </td>

          <!-- Total score -->
          <td class="table-cell text-center">
            <span class="font-bold text-slate-900 tabular-nums">{{ item.total_score?.toFixed(2) }}</span>
          </td>

          <!-- Band -->
          <td class="table-cell text-center">
            <span class="inline-flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold"
                  :class="bandColor(item.score_band ?? 'D')">
              {{ item.score_band }}
            </span>
          </td>

          <!-- ND98 registration -->
          <td class="table-cell text-center">
            <template v-if="editable">
              <input
                type="checkbox"
                class="w-4 h-4 rounded accent-brand-600 cursor-pointer"
                :checked="item.has_nd98_registration === 1"
                @change="updateField(i, 'has_nd98_registration', ($event.target as HTMLInputElement).checked ? 1 : 0)"
              />
            </template>
            <template v-else>
              <svg v-if="item.has_nd98_registration" class="w-4 h-4 text-emerald-500 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7" />
              </svg>
              <span v-else class="text-slate-300 text-sm">—</span>
            </template>
          </td>

          <!-- Compliant with TS -->
          <td class="table-cell text-center">
            <template v-if="editable">
              <input
                type="checkbox"
                class="w-4 h-4 rounded accent-brand-600 cursor-pointer"
                :checked="item.compliant_with_ts === 1"
                @change="updateField(i, 'compliant_with_ts', ($event.target as HTMLInputElement).checked ? 1 : 0)"
              />
            </template>
            <template v-else>
              <svg v-if="item.compliant_with_ts" class="w-4 h-4 text-emerald-500 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7" />
              </svg>
              <span v-else class="text-slate-300 text-sm">—</span>
            </template>
          </td>

          <!-- Remove row (edit mode only) -->
          <td v-if="editable" class="table-cell">
            <button
              type="button"
              class="text-slate-300 hover:text-red-500 transition-colors"
              title="Xóa hàng"
              @click="emit('update:items', props.items.filter((_, idx) => idx !== i))"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </td>
        </tr>

        <!-- Empty state -->
        <tr v-if="items.length === 0">
          <td :colspan="editable ? 11 : 10" class="px-4 py-10 text-center text-sm text-slate-400 italic">
            Chưa có nhà cung cấp nào. Thêm ít nhất 2 nhà cung cấp để đánh giá.
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
