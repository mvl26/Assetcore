<script setup lang="ts">
/**
 * UomConverter — Công cụ quy đổi đơn vị tính cho phụ tùng.
 *
 * Usage:
 *   <UomConverter :spare-part="partName" />
 *
 * Hiển thị toàn bộ bảng quy đổi + form tính nhanh:
 *   Nhập số lượng + chọn from/to UOM → kết quả quy đổi ngay lập tức.
 */
import { ref, watch, computed } from 'vue'
import { frappeGet } from '@/api/helpers'

interface ConversionRow {
  uom: string
  conversion_factor: number
  is_stock_uom?: boolean
  is_purchase_uom?: boolean
  is_issue_uom?: boolean
}

interface UomInfo {
  spare_part: string
  part_name: string
  stock_uom: string
  purchase_uom: string
  conversions: ConversionRow[]
}

const props = defineProps<{ sparePart: string }>()

const info     = ref<UomInfo | null>(null)
const loading  = ref(false)
const fromQty  = ref<number>(1)
const fromUom  = ref('')
const toUom    = ref('')

const BASE = '/api/method/assetcore.api.inventory'

async function load() {
  if (!props.sparePart) return
  loading.value = true
  try {
    const res = await frappeGet<UomInfo>(`${BASE}.get_uom_info`, { spare_part: props.sparePart })
    if (res) {
      info.value  = res
      fromUom.value = res.stock_uom
      toUom.value   = res.purchase_uom !== res.stock_uom ? res.purchase_uom : (res.conversions[1]?.uom ?? res.stock_uom)
    }
  } finally {
    loading.value = false
  }
}

watch(() => props.sparePart, load, { immediate: true })

// Tính kết quả quy đổi từ bảng local (không cần gọi API thêm)
const result = computed<{ qty: number; factor: number } | null>(() => {
  if (!info.value || !fromUom.value || !toUom.value) return null
  const rows = info.value.conversions

  const factorOf = (uom: string): number => {
    if (uom === info.value!.stock_uom) return 1
    return rows.find(r => r.uom === uom)?.conversion_factor ?? 0
  }

  const fFrom = factorOf(fromUom.value)   // 1 fromUom = fFrom stock_uom
  const fTo   = factorOf(toUom.value)     // 1 toUom   = fTo   stock_uom

  if (!fFrom || !fTo) return null

  const factor = fFrom / fTo              // 1 fromUom = factor toUom
  return { qty: (fromQty.value || 0) * factor, factor }
})

function swap() {
  ;[fromUom.value, toUom.value] = [toUom.value, fromUom.value]
}

function fmtNum(n: number): string {
  return Number.isInteger(n) ? n.toLocaleString('vi-VN') : n.toLocaleString('vi-VN', { maximumFractionDigits: 6 })
}
</script>

<template>
  <div v-if="loading" class="animate-pulse space-y-2 p-4">
    <div class="h-4 bg-slate-100 rounded w-40" />
    <div class="h-4 bg-slate-100 rounded w-56" />
  </div>

  <div v-else-if="!info" class="text-xs text-slate-400 italic p-2">
    Chọn phụ tùng để xem quy đổi đơn vị
  </div>

  <div v-else class="space-y-4">
<!-- Bảng quy đổi -->
    <div>
      <p class="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
        Bảng quy đổi — {{ info.part_name }}
      </p>
      <div class="rounded-xl border border-slate-200 overflow-hidden">
        <table class="w-full text-sm">
          <thead class="bg-slate-50">
            <tr>
              <th class="px-3 py-2 text-left text-xs font-semibold text-slate-500">Đơn vị</th>
              <th class="px-3 py-2 text-right text-xs font-semibold text-slate-500">= (stock)</th>
              <th class="px-3 py-2 text-left text-xs font-semibold text-slate-500">Vai trò</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr
v-for="row in info.conversions" :key="row.uom"
                :class="row.is_stock_uom ? 'bg-blue-50/60' : 'hover:bg-slate-50'"
                class="transition-colors">
              <td class="px-3 py-2 font-semibold text-slate-800">
                {{ row.uom }}
                <span
v-if="row.is_stock_uom"
                      class="ml-1.5 text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded font-medium">
                  Cơ bản
                </span>
              </td>
              <td class="px-3 py-2 text-right font-mono text-slate-700">
                {{ fmtNum(row.conversion_factor) }} {{ info.stock_uom }}
              </td>
              <td class="px-3 py-2">
                <div class="flex gap-1 flex-wrap">
                  <span
v-if="row.is_purchase_uom"
                        class="text-[10px] bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded">Mua</span>
                  <span
v-if="row.is_issue_uom"
                        class="text-[10px] bg-orange-100 text-orange-700 px-1.5 py-0.5 rounded">Xuất</span>
                </div>
              </td>
            </tr>
            <tr v-if="info.conversions.length <= 1">
              <td colspan="3" class="px-3 py-3 text-xs text-slate-400 italic text-center">
                Chưa có quy đổi — chỉ có đơn vị cơ bản
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Công cụ tính nhanh -->
    <div class="rounded-xl border border-slate-200 bg-slate-50/60 p-4 space-y-3">
      <p class="text-xs font-semibold text-slate-500 uppercase tracking-wide">Tính nhanh</p>

      <div class="flex items-center gap-2 flex-wrap">
        <!-- Số lượng -->
        <input
          v-model.number="fromQty"
          type="number"
          min="0"
          step="any"
          class="w-24 border border-slate-300 rounded-lg px-3 py-1.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-400"
        />

        <!-- From UOM -->
        <select
          v-model="fromUom"
          class="border border-slate-300 rounded-lg px-2 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
        >
          <option v-for="row in info.conversions" :key="row.uom" :value="row.uom">
            {{ row.uom }}
          </option>
        </select>

        <!-- Swap button -->
        <button
          class="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-100 transition-colors text-slate-500"
          title="Đổi chiều"
          @click="swap"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path
stroke-linecap="round" stroke-linejoin="round"
                  d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 3M21 7.5H7.5" />
          </svg>
        </button>

        <!-- To UOM -->
        <select
          v-model="toUom"
          class="border border-slate-300 rounded-lg px-2 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
        >
          <option v-for="row in info.conversions" :key="row.uom" :value="row.uom">
            {{ row.uom }}
          </option>
        </select>
      </div>

      <!-- Result -->
      <div
v-if="result && fromUom !== toUom"
           class="flex items-baseline gap-2 bg-white rounded-lg border border-blue-200 px-4 py-3">
        <span class="text-lg font-bold text-blue-700 tabular-nums">{{ fmtNum(result.qty) }}</span>
        <span class="text-sm font-medium text-slate-700">{{ toUom }}</span>
        <span class="text-xs text-slate-400 ml-auto">
          (hệ số: 1 {{ fromUom }} = {{ fmtNum(result.factor) }} {{ toUom }})
        </span>
      </div>
      <div
v-else-if="fromUom === toUom"
           class="text-xs text-slate-400 italic">
        Chọn 2 đơn vị khác nhau để tính quy đổi
      </div>
      <div
v-else-if="!result"
           class="text-xs text-red-500">
        Không tìm thấy hệ số quy đổi giữa {{ fromUom }} và {{ toUom }}
      </div>
    </div>
</div>
</template>
